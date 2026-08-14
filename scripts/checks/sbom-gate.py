#!/usr/bin/env python
"""Assert the published SBOM describes this project.

An SBOM is well formed and valid whatever environment it was taken from, so
"the document parses" says nothing about whether it lists the software this
release ships. This gate reads the stronger property: every distribution in the
runtime closure appears as a component, and the SBOM generator's own closure
does not.

The reference is `uv.lock`, read through `uv export`, rather than a list kept
here. A second list of what twinflow depends on drifts from the lock the first
time a dependency moves, and a gate reading a stale list passes for the wrong
reason.
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from collections.abc import Iterable
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]

#: Distributions belonging to the SBOM generator. Their presence means the
#: document describes the tool rather than the project. `lxml` is deliberately
#: absent: it is a plausible future dependency here, and refusing it would fail
#: for a reason unrelated to what this gate reads.
GENERATOR_MARKERS: frozenset[str] = frozenset(
    {"cyclonedx-python-lib", "cyclonedx-bom", "py-serializable", "license-expression"}
)

#: The runtime closure, read out of the lock. A dependency that moves moves in
#: one place.
EXPORT_COMMAND: tuple[str, ...] = (
    "uv",
    "export",
    "--frozen",
    "--no-dev",
    "--all-packages",
    "--format",
    "requirements-txt",
    "--no-hashes",
    "--no-emit-workspace",
)


class GateError(Exception):
    """A refusal this gate reports with its reason."""


def normalize(name: str) -> str:
    """PEP 503 name normalization, so `typing_extensions` and
    `typing-extensions` are one name.

    PEP 503 replaces *runs* of `-`, `_`, and `.` with a single `-`. Mapping each
    character on its own leaves `typing__extensions` as `typing--extensions`,
    which compares unequal to the lock's spelling and reports a shipped
    distribution as absent from the SBOM.
    """
    return re.sub(r"[-_.]+", "-", name.strip().lower())


def components_in(document: dict) -> set[str]:
    """Every component name the SBOM declares, normalized."""
    return {normalize(component["name"]) for component in document.get("components", [])}


def runtime_closure() -> set[str]:
    """What this project ships, according to the lock."""
    result = subprocess.run(  # noqa: S603 - a fixed argv, no shell
        EXPORT_COMMAND,
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    if result.returncode != 0:
        raise GateError(
            f"`uv export` failed, so there is nothing to compare against:\n{result.stderr}"
        )
    names: set[str] = set()
    for raw in result.stdout.splitlines():
        line = raw.strip()
        if not line or line.startswith(("#", "-")):
            continue
        for separator in ("==", " @ ", ">=", "~="):
            if separator in line:
                names.add(normalize(line.split(separator, 1)[0]))
                break
    return names


def check_sbom(document: dict, expected: Iterable[str]) -> list[str]:
    """Every reason this SBOM does not describe this project."""
    findings: list[str] = []
    present = components_in(document)

    if not present:
        return ["the SBOM declares no components at all"]

    missing = sorted(set(expected) - present)
    if missing:
        findings.append(
            f"{len(missing)} shipped distributions are absent from the SBOM, "
            f"starting with {', '.join(missing[:5])}. An SBOM that omits what ships "
            f"is an SBOM of something else"
        )

    generators = sorted(present & GENERATOR_MARKERS)
    if generators:
        findings.append(
            f"the SBOM names the generator's own dependencies ({', '.join(generators)}), "
            f"so it describes the tool rather than this project"
        )
    return findings


#: Each case is (name, document, expected closure, whether a finding is due).
SELFTEST_CASES: tuple[tuple[str, dict, tuple[str, ...], bool], ...] = (
    (
        "an SBOM naming everything shipped passes",
        {"components": [{"name": "numpy"}, {"name": "pydantic"}, {"name": "twinflow-twin"}]},
        ("numpy", "pydantic", "twinflow-twin"),
        False,
    ),
    (
        "an SBOM of the generator is refused",
        {"components": [{"name": "cyclonedx-python-lib"}, {"name": "lxml"}]},
        ("numpy", "pydantic"),
        True,
    ),
    (
        "one missing shipped dependency is refused",
        {"components": [{"name": "numpy"}]},
        ("numpy", "pydantic"),
        True,
    ),
    (
        "an underscore spelling is the same name",
        {"components": [{"name": "typing_extensions"}]},
        ("typing-extensions",),
        False,
    ),
    (
        "a run of separators collapses to one, as PEP 503 says",
        {"components": [{"name": "typing__extensions"}, {"name": "zope.interface"}]},
        ("typing-extensions", "zope-interface"),
        False,
    ),
    (
        "an empty component list is refused",
        {"components": []},
        ("numpy",),
        True,
    ),
)


def selftest() -> int:
    """Prove the gate reports a finding for each defect it claims to read.

    Doctrine D-12: a test that cannot fail is not a test, and neither is a gate.
    """
    failures = 0
    for name, document, expected, should_find in SELFTEST_CASES:
        findings = check_sbom(document, expected)
        if bool(findings) != should_find:
            verb = "expected a finding" if should_find else "expected none"
            print(f"[sbom-gate] SELFTEST FAIL: {name}: {verb}, got {findings}")
            failures += 1
    if failures:
        return 1
    print(f"[sbom-gate] selftest: {len(SELFTEST_CASES)} cases, every refusal fires")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("sbom", nargs="?", type=Path, help="the CycloneDX JSON document to check")
    parser.add_argument("--selftest", action="store_true", help="prove the refusals fire")
    args = parser.parse_args(argv)

    if args.selftest:
        return selftest()
    if args.sbom is None:
        parser.error("a path to the SBOM is required unless --selftest is given")

    try:
        document = json.loads(args.sbom.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        print(f"[sbom-gate] {args.sbom} is not a readable JSON document: {exc}")
        return 1

    try:
        expected = runtime_closure()
    except GateError as exc:
        print(f"[sbom-gate] {exc}")
        return 1

    findings = check_sbom(document, expected)
    if findings:
        for finding in findings:
            print(f"[sbom-gate] {finding}")
        return 1
    print(
        f"[sbom-gate] {args.sbom.name} describes this project: "
        f"all {len(expected)} shipped distributions present"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
