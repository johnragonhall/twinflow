#!/usr/bin/env python
"""VAL-GATE-DOC-001: the documentation a reader meets first is checkable.

Four clauses, and each is read by a checker rather than by a person. Three hold
at every tag: every relative link resolves, the prose gate reports no error, and
every filled metric marker resolves to a committed artifact naming the tool, the
seed, and the run that produced it.

The fourth arrives with its input. `docs/design/roadmap.md` section 5.3 asks
that the first three lines of the README carry the E1 replay URL and exactly one
metric marker resolving to the release event's `headline_metric`. E1 is the
hosted replay bundle, which `VAL-GATE-E1-001` starts asserting at v0.3.0, so
before that tag there is no URL to carry and no seeded headline number to
resolve. Passing `--release` turns the clause on at the tag its input arrives
at, the same way `metric-marker-gate.sh` reads a marker's own tag.

The docs site build belongs to `VAL-GATE-DOCSITE-001` from v0.4.0, per the same
section. `just docs-build` runs it on every documentation change regardless, so
the build is checked here by neither omission nor duplication.
"""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
README = REPO_ROOT / "README.md"

#: The tag the E1 replay bundle first exists at, from `VAL-GATE-E1-001`.
E1_TAG = (0, 3, 0)

#: The checks that hold at every tag. Each is a gate of its own with its own
#: selftest, called rather than reimplemented, so one rule keeps one home.
COMPOSED: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("links", ("uv", "run", "--no-sync", "python", "scripts/checks/link-gate.py")),
    ("prose", ("uv", "run", "--no-sync", "python", "scripts/checks/prose-gate.py", "--all")),
    ("measured claims", ("uv", "run", "--no-sync", "python", "tools/check_measured_claims.py")),
)

MARKER = re.compile(r"<!--METRIC:([A-Za-z0-9_]+)@v([0-9]+\.[0-9]+\.[0-9]+)-->")


def version_tuple(text: str) -> tuple[int, int, int]:
    """A dotted version as three integers, compared field by field.

    A string comparison puts v0.10.0 before v0.9.0 and would arm a clause early.
    """
    parts = text.lstrip("v").split(".")
    if len(parts) != 3 or not all(part.isdigit() for part in parts):
        raise ValueError(f"{text!r} is not MAJOR.MINOR.PATCH")
    return (int(parts[0]), int(parts[1]), int(parts[2]))


def readme_findings(head: str, *, release: tuple[int, int, int] | None) -> list[str]:
    """Every reason the README's opening does not carry what the tag owes.

    `head` is the first three lines. Before the E1 tag nothing is owed, so an
    opening with no marker and no bundle link passes rather than failing for an
    artifact that does not exist.
    """
    if release is None or release < E1_TAG:
        return []

    findings: list[str] = []
    if "/replay/" not in head:
        findings.append(
            "the first three lines of README.md carry no E1 replay URL, which "
            "roadmap.md 5.3 asks a reader to reach before anything else"
        )
    markers = MARKER.findall(head)
    if len(markers) != 1:
        findings.append(
            f"the first three lines of README.md carry {len(markers)} metric markers, "
            f"and the release event carries exactly one headline metric"
        )
    return findings


def run_composed() -> list[str]:
    """Every composed check that reports a finding, named."""
    failures: list[str] = []
    for name, command in COMPOSED:
        result = subprocess.run(  # noqa: S603 - fixed argv, no shell
            command,
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
        if result.returncode != 0:
            detail = (result.stdout + result.stderr).strip().splitlines()
            tail = detail[-1] if detail else "no output"
            failures.append(f"the {name} check reports a finding: {tail}")
    return failures


SELFTEST_CASES: tuple[tuple[str, str, tuple[int, int, int] | None, bool], ...] = (
    ("before the E1 tag nothing is owed", "# twinflow\n\nA digital twin.\n", (0, 2, 0), False),
    ("before any tag nothing is owed", "# twinflow\n\nA digital twin.\n", None, False),
    (
        "at the E1 tag a missing replay URL is refused",
        "# twinflow\n\nA digital twin. <!--METRIC:x@v0.3.0-->1<!--/METRIC-->\n",
        (0, 3, 0),
        True,
    ),
    (
        "at the E1 tag a missing marker is refused",
        "# twinflow\n\nA twin, with a [replay](https://example.test/replay/).\n",
        (0, 3, 0),
        True,
    ),
    (
        "at the E1 tag two markers are refused",
        "# twinflow\n\n[replay](/replay/) <!--METRIC:a@v0.3.0-->1<!--/METRIC-->"
        "<!--METRIC:b@v0.3.0-->2<!--/METRIC-->\n",
        (0, 3, 0),
        True,
    ),
    (
        "at the E1 tag one marker beside the URL passes",
        "# twinflow\n\n[replay](/replay/) <!--METRIC:a@v0.3.0-->1<!--/METRIC-->\n",
        (0, 3, 0),
        False,
    ),
    (
        "a later tag still owes both",
        "# twinflow\n\nA digital twin.\n",
        (1, 0, 0),
        True,
    ),
)


def selftest() -> int:
    """Prove the tag-qualified clause fires when its input exists and not before.

    Doctrine D-12: a clause nobody has watched refuse anything may be passing
    because it cannot.
    """
    failures = 0
    for name, head, release, should_find in SELFTEST_CASES:
        findings = readme_findings(head, release=release)
        if bool(findings) != should_find:
            verb = "expected a finding" if should_find else "expected none"
            print(f"[docs-gate] SELFTEST FAIL: {name}: {verb}, got {findings}")
            failures += 1
    if failures:
        return 1
    print(f"[docs-gate] selftest: {len(SELFTEST_CASES)} cases, every refusal fires")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--release", help="the tag being cut, which arms the tag-qualified clause")
    parser.add_argument("--selftest", action="store_true", help="prove the refusals fire")
    args = parser.parse_args(argv)

    if args.selftest:
        return selftest()

    release = None
    if args.release:
        try:
            release = version_tuple(args.release)
        except ValueError as exc:
            print(f"[docs-gate] {exc}")
            return 1

    findings = run_composed()
    head = "\n".join(README.read_text(encoding="utf-8").splitlines()[:3])
    findings += readme_findings(head, release=release)

    if findings:
        for finding in findings:
            print(f"[docs-gate] {finding}")
        return 1
    owed = (
        "including the opening README clause"
        if release and release >= E1_TAG
        else ("the opening README clause arrives with E1 at v0.3.0")
    )
    print(f"[docs-gate] links, prose, and measured claims all clean; {owed}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
