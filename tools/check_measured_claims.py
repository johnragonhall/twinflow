#!/usr/bin/env python3
"""Every number in the docs came from a committed artifact, or the build fails.

    uv run --no-sync python tools/check_measured_claims.py
    uv run --no-sync python tools/check_measured_claims.py --release 0.2.0
    uv run --no-sync python tools/check_measured_claims.py --selftest

Behind `just check-measured-claims`, which `just lint` runs.

THE RULE
--------
A metric marker in the docs

    <!--METRIC:name@v0.2.0-->12.5<!--/METRIC-->

resolves to `artifacts/measured/name.json`, a committed record written by a
measurement tool, and the marker carries exactly the value that record carries.
A marker holding a number with no such record behind it is a hand-typed value,
and this checker exists to make that state impossible to commit.

Foundations 5.4 states the rule for prose: a claim with a number carries the run
id that produced it. Section 5.6 states it for operator-facing output, where the
historian sizing warning reads `x-twinflow-stored-bytes` off a subject schema and
prints the run beside it. Both are the same rule, so both are checked here.

HOW IT DIFFERS FROM THE MARKER GATE
-----------------------------------
`scripts/checks/metric-marker-gate.sh` asks whether a marker is still TBD and
whether the release being cut owes it. That is a question about coverage. This
asks whether a marker that is NOT TBD is telling the truth, which is a question
about provenance, and it is the harder half: an unfilled marker is visibly
unfinished, while a filled one carries no sign of where its number came from.
The two run together and neither subsumes the other.

THE SIX REFUSALS
----------------
    unfilled       a marker the release being cut owes is still TBD (--release only)
    no-artifact    a filled marker with no artifacts/measured/<name>.json
    value-drift    a filled marker whose number differs from its artifact
    unattributed   an artifact missing the seed, the run id, the unit, or the tool
    no-producer    an artifact naming a tool that is not in the tree
    stored-bytes   an x-twinflow-stored-bytes keyword with no run id beside it

`--selftest` constructs the state each refusal is supposed to catch and asserts
that it fires, and constructs a well-formed tree and asserts that it passes.
Doctrine D-12: every test states the observation that would fail it, and a
checker that refuses everything proves no more than one that refuses nothing. The
pass case is what separates the two, so it is part of the selftest rather than
left to the caller to notice.

EXIT CODES
----------
    0  every claim resolves
    1  at least one refusal fired
    2  a bad argument
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]

#: Where a measurement tool writes its record, relative to the tree root.
ARTIFACT_DIR = Path("artifacts") / "measured"

#: The marker grammar, identical to the one metric-marker-gate.sh reads. The
#: value is anything but a `<`, so an unterminated marker fails to match here
#: and is reported by that gate as a tag imbalance rather than silently by both.
MARKER = re.compile(
    r"<!--METRIC:(?P<name>[A-Za-z0-9_]+)(?:@(?P<arms>v[0-9]+\.[0-9]+\.[0-9]+))?-->"
    r"(?P<value>[^<]*)"
    r"<!--/METRIC-->"
)

#: The values that mean "no number yet". Same set the shell gate treats as
#: unfilled, so one marker cannot be unfilled to one checker and filled to the
#: other.
UNFILLED = {"TBD", "tbd", "", "?", "N/A"}

#: What an artifact has to carry before a number in it may be quoted. Each one
#: is half of "reproduce this": without the tool nobody knows what to run,
#: without the seed and the run id nobody can tell whether they got the same
#: answer, and without the unit the number is not a quantity.
REQUIRED_ARTIFACT_FIELDS = ("value", "unit", "seed", "run_id", "tool")

#: This file states the marker convention and therefore must contain a marker
#: that is not a claim. The shell gate and prose-gate.py carve it out for the
#: same reason.
EXCLUDED_DOCS = {"docs/DOCUMENTATION-STANDARD.md"}


@dataclass(frozen=True)
class Finding:
    """One refusal, with the file that has to change to clear it."""

    rule: str
    where: str
    detail: str

    def __str__(self) -> str:
        return f"{self.rule:13} {self.where}: {self.detail}"


def markdown_files(root: Path) -> list[Path]:
    """Every Markdown file the tree owns, tracked or merely not ignored.

    Untracked-but-not-ignored files are included for the reason the shell gate
    gives: without them a young repository scans almost nothing and reports a
    pass, which is worse than reporting a failure.
    """
    try:
        done = subprocess.run(  # noqa: S603
            ["git", "ls-files", "--cached", "--others", "--exclude-standard", "*.md"],  # noqa: S607
            cwd=root,
            capture_output=True,
            text=True,
            check=False,
        )
        listed = [line for line in done.stdout.splitlines() if line.strip()]
    except OSError:
        listed = []

    if not listed:
        listed = [str(path.relative_to(root)).replace("\\", "/") for path in root.rglob("*.md")]

    files = []
    for name in sorted(set(listed)):
        posix = name.replace("\\", "/")
        if posix in EXCLUDED_DOCS or posix.startswith(("site/", ".git/")):
            continue
        path = root / posix
        if path.is_file():
            files.append(path)
    return files


def version_reached(arms: str, cutting: str) -> bool:
    """Is the tag a marker names at or before the one being cut?

    Compared field by field. A string comparison puts v0.10.0 before v0.9.0 and
    would arm a marker two releases early, which is the same trap the shell gate
    spends an awk function avoiding.
    """
    left = [int(part) for part in arms.lstrip("v").split(".")]
    right = [int(part) for part in cutting.lstrip("v").split(".")]
    return left <= right


def read_artifact(root: Path, name: str) -> tuple[dict[str, Any] | None, str]:
    """The measurement record for a metric, or why there is none."""
    path = root / ARTIFACT_DIR / f"{name}.json"
    if not path.is_file():
        return None, f"{ARTIFACT_DIR.as_posix()}/{name}.json does not exist"
    try:
        record = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        return None, f"{path} could not be read as JSON: {error}"
    if not isinstance(record, dict):
        return None, f"{path} holds {type(record).__name__}, not an object"
    return record, ""


def check_marker(
    root: Path, path: Path, name: str, arms: str | None, value: str, cutting: str | None
) -> list[Finding]:
    """One marker, against the artifact it claims to have come from."""
    where = f"{path.relative_to(root).as_posix()}:{name}"
    text = value.strip()

    if text in UNFILLED:
        # Coverage is the marker gate's question, and it is only a failure at a
        # tag. Without --release this checker says nothing about an unfilled
        # marker, so `just lint` on a branch does not fail over a number that
        # three releases from now will owe.
        if cutting is not None and (arms is None or version_reached(arms, cutting)):
            owed = arms or "every release"
            return [
                Finding(
                    "unfilled",
                    where,
                    f"still {text or 'empty'} and owed at {owed}. Measure it and commit the "
                    f"artifact, remove the claim, or name the tag it arrives at",
                )
            ]
        return []

    record, why = read_artifact(root, name)
    if record is None:
        return [
            Finding(
                "no-artifact",
                where,
                f"carries {text!r} and {why}. A number in the docs is read out of a committed "
                f"record or it was typed by a person, and there is no third case",
            )
        ]

    findings: list[Finding] = []
    absent = [field for field in REQUIRED_ARTIFACT_FIELDS if record.get(field) is None]
    if absent:
        findings.append(
            Finding(
                "unattributed",
                where,
                f"its artifact is missing {', '.join(absent)}. A value without its seed, run id, "
                f"unit, and producing tool cannot be reproduced, so it is a claim rather than a "
                f"measurement",
            )
        )
        return findings

    tool = str(record["tool"])
    if not (root / tool).is_file():
        findings.append(
            Finding(
                "no-producer",
                where,
                f"its artifact names tool {tool!r}, which is not in the tree. The record has to "
                f"lead back to something a reader can run",
            )
        )

    try:
        claimed = Decimal(text)
        recorded = Decimal(str(record["value"]))
    except InvalidOperation:
        findings.append(
            Finding(
                "value-drift",
                where,
                f"the marker holds {text!r} and the artifact holds {record['value']!r}, and at "
                f"least one of the two is not a number",
            )
        )
        return findings

    if claimed != recorded:
        findings.append(
            Finding(
                "value-drift",
                where,
                f"the marker holds {text} and {ARTIFACT_DIR.as_posix()}/{name}.json holds "
                f"{record['value']} from run {record['run_id']}. One number, one home",
            )
        )
    return findings


def check_stored_bytes(root: Path) -> list[Finding]:
    """`x-twinflow-stored-bytes` carries its run id, per foundations 5.6.

    The keyword is documented in schemas/x-keywords.md as "measured stored bytes
    per row for a subject, with the run id it was measured on". The run id is
    half the keyword, so a value published without it fails here rather than
    reaching an operator's warning as a bare number.
    """
    findings: list[Finding] = []
    schemas = root / "schemas"
    if not schemas.is_dir():
        return findings

    for path in sorted(schemas.rglob("*.json")):
        try:
            document = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        for holder, value in _walk_keyword(document, "x-twinflow-stored-bytes"):
            where = path.relative_to(root).as_posix()
            if isinstance(value, dict) and value.get("run_id") and value.get("bytes") is not None:
                continue
            findings.append(
                Finding(
                    "stored-bytes",
                    where,
                    f"x-twinflow-stored-bytes on {holder} is {value!r}. It carries an object with "
                    f"a bytes value and the run_id it was measured on, or it is absent and the "
                    f"sizing warning degrades to the reading count",
                )
            )
    return findings


def _walk_keyword(node: Any, keyword: str, trail: str = "$") -> list[tuple[str, Any]]:
    """Every occurrence of a keyword in a JSON document, with its path."""
    found: list[tuple[str, Any]] = []
    if isinstance(node, dict):
        for key, value in node.items():
            if key == keyword:
                found.append((trail, value))
            else:
                found.extend(_walk_keyword(value, keyword, f"{trail}.{key}"))
    elif isinstance(node, list):
        for index, value in enumerate(node):
            found.extend(_walk_keyword(value, keyword, f"{trail}[{index}]"))
    return found


def check(root: Path, cutting: str | None) -> list[Finding]:
    """Every refusal, over one tree."""
    findings: list[Finding] = []
    for path in markdown_files(root):
        text = path.read_text(encoding="utf-8", errors="replace")
        for match in MARKER.finditer(text):
            findings.extend(
                check_marker(
                    root,
                    path,
                    match.group("name"),
                    match.group("arms"),
                    match.group("value"),
                    cutting,
                )
            )
    findings.extend(check_stored_bytes(root))
    return findings


# --------------------------------------------------------------------------
# Selftest
# --------------------------------------------------------------------------

_GOOD_ARTIFACT = {
    "metric": "widget_rate",
    "value": 12.5,
    "unit": "widget/second",
    "seed": 7,
    "run_id": "run_deadbeef",
    "tool": "tools/measure_row_bytes.py",
}


def _tree(root: Path, marker: str, artifact: dict[str, Any] | None) -> None:
    (root / "docs").mkdir(parents=True, exist_ok=True)
    (root / "docs" / "claim.md").write_text(f"The rate is {marker}.\n", encoding="utf-8")
    if artifact is not None:
        target = root / ARTIFACT_DIR
        target.mkdir(parents=True, exist_ok=True)
        (target / "widget_rate.json").write_text(json.dumps(artifact), encoding="utf-8")
        tool = root / str(artifact.get("tool") or "tools/placeholder.py")
        if artifact.get("tool") != "MISSING":
            tool.parent.mkdir(parents=True, exist_ok=True)
            tool.write_text("# stand-in for the producing tool\n", encoding="utf-8")


def selftest() -> int:
    """Each refusal fires on the state it names, and a clean tree passes."""
    import tempfile

    filled = "<!--METRIC:widget_rate@v0.1.0-->12.5<!--/METRIC-->"
    drifted = "<!--METRIC:widget_rate@v0.1.0-->99.0<!--/METRIC-->"
    unfilled = "<!--METRIC:widget_rate@v0.1.0-->TBD<!--/METRIC-->"

    no_seed = dict(_GOOD_ARTIFACT, seed=None)
    no_tool = dict(_GOOD_ARTIFACT, tool="MISSING")

    cases: list[tuple[str, str, dict[str, Any] | None, str | None, str | None]] = [
        # label, marker, artifact, release being cut, rule that must fire
        ("a filled marker with no artifact", filled, None, None, "no-artifact"),
        ("a marker that disagrees with its artifact", drifted, _GOOD_ARTIFACT, None, "value-drift"),
        ("an artifact with no seed", filled, no_seed, None, "unattributed"),
        ("an artifact naming a tool not in the tree", filled, no_tool, None, "no-producer"),
        ("an unfilled marker the release owes", unfilled, None, "0.1.0", "unfilled"),
        ("an unfilled marker a later release owes", unfilled, None, "0.0.1", None),
        ("an unfilled marker with no release being cut", unfilled, None, None, None),
        ("a marker that resolves", filled, _GOOD_ARTIFACT, "0.1.0", None),
    ]

    failures: list[str] = []
    for label, marker, artifact, cutting, expected in cases:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            _tree(root, marker, artifact)
            fired = {finding.rule for finding in check(root, cutting)}
            if expected is None:
                if fired:
                    failures.append(f"{label}: expected no refusal, got {sorted(fired)}")
            elif expected not in fired:
                failures.append(f"{label}: expected {expected}, got {sorted(fired) or 'nothing'}")

    # The stored-bytes rule reads schemas rather than docs, so it gets its own
    # pair: one keyword without a run id, and one with.
    for label, value, expected in (
        ("a stored-bytes keyword with no run id", 214, "stored-bytes"),
        ("a stored-bytes keyword with a bare object", {"bytes": 214}, "stored-bytes"),
        ("a stored-bytes keyword with its run", {"bytes": 214, "run_id": "run_x"}, None),
    ):
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            schema = root / "schemas" / "telemetry"
            schema.mkdir(parents=True)
            (schema / "v1.json").write_text(
                json.dumps({"x-twinflow-stored-bytes": value}), encoding="utf-8"
            )
            fired = {finding.rule for finding in check(root, None)}
            if expected is None and fired:
                failures.append(f"{label}: expected no refusal, got {sorted(fired)}")
            if expected is not None and expected not in fired:
                failures.append(f"{label}: expected {expected}, got {sorted(fired) or 'nothing'}")

    if failures:
        print("SELFTEST FAILED", file=sys.stderr)
        for line in failures:
            print(f"  {line}", file=sys.stderr)
        return 1

    print(f"selftest: {len(cases) + 3} cases, every refusal fires and every clean tree passes")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--release",
        default=None,
        help="the version being cut; without it every unfilled marker is owed",
    )
    parser.add_argument("--root", type=Path, default=REPO_ROOT)
    parser.add_argument("--selftest", action="store_true", help="prove each refusal fires")
    args = parser.parse_args(argv)

    if args.selftest:
        return selftest()

    if args.release is not None and not re.fullmatch(r"v?\d+\.\d+\.\d+", args.release):
        parser.error(f"--release takes a three-part version, got {args.release!r}")

    findings = check(args.root.resolve(), args.release)
    if findings:
        print(f"FAIL {len(findings)} measured-claim refusal(s)\n", file=sys.stderr)
        for finding in findings:
            print(f"  {finding}", file=sys.stderr)
        print(
            "\nA number in this repository is read out of a committed artifact that a "
            "named tool produced from a named seed and run, or it is not published.",
            file=sys.stderr,
        )
        return 1

    print("PASS every measured claim resolves to a committed artifact")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
