#!/usr/bin/env python3
"""Release gate REL-001, run before a tag is cut.

    python scripts/checks/release-gate.py            check the unreleased state
    python scripts/checks/release-gate.py 0.2.0      check that tag

Three things have to hold before a version is tagged:

  1 CHANGELOG.md carries a section for the tag, per Keep a Changelog 1.1.0.
  2 The bump matches the C9 policy. A breaking change to a package API, a REST
    or MCP contract, an event schema, or facility.yaml is a MAJOR; a new
    capability is a MINOR; anything else is a PATCH.
  3 No metric marker is still unfilled. A release that publishes TBD where a
    number belongs is a release that publishes a number nobody measured.

The third is the one that catches a real habit. During the build an unfilled
marker is normal and the marker gate reports it without failing. At a tag it
becomes fatal, because that is the moment the claim reaches somebody who cannot
check it.
"""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
CHANGELOG = REPO_ROOT / "CHANGELOG.md"

SEMVER = re.compile(r"^(?P<major>\d+)\.(?P<minor>\d+)\.(?P<patch>\d+)$")

#: Keep a Changelog 1.1.0 headings. A section under any other name is a section
#: no reader of that specification expects to find.
KNOWN_HEADINGS = {"Added", "Changed", "Deprecated", "Removed", "Fixed", "Security"}

#: Headings whose presence forces at least a MINOR, and the ones that force a
#: MAJOR. "Removed" is the interesting row: removing a published symbol, a
#: schema field, or a config key breaks whoever depended on it.
MINOR_HEADINGS = {"Added", "Deprecated"}
MAJOR_HEADINGS = {"Removed"}


def released_versions() -> list[str]:
    """Every version CHANGELOG.md carries a section for, newest first."""
    text = CHANGELOG.read_text(encoding="utf-8")
    return re.findall(r"^## \[(\d+\.\d+\.\d+)\]", text, re.MULTILINE)


def section_for(version: str) -> str | None:
    """The body of one version's section, or None when it has none."""
    text = CHANGELOG.read_text(encoding="utf-8")
    match = re.search(
        rf"^## \[{re.escape(version)}\].*?$(?P<body>.*?)(?=^## \[|\Z)",
        text,
        re.MULTILINE | re.DOTALL,
    )
    return match.group("body") if match else None


def unreleased_section() -> str:
    text = CHANGELOG.read_text(encoding="utf-8")
    match = re.search(
        r"^## \[Unreleased\].*?$(?P<body>.*?)(?=^## \[|\Z)", text, re.MULTILINE | re.DOTALL
    )
    return match.group("body") if match else ""


def headings_in(body: str) -> set[str]:
    return set(re.findall(r"^### (\w+)", body, re.MULTILINE)) & KNOWN_HEADINGS


def required_bump(headings: set[str]) -> str:
    if headings & MAJOR_HEADINGS:
        return "major"
    if headings & MINOR_HEADINGS:
        return "minor"
    return "patch"


def actual_bump(previous: str, proposed: str) -> str | None:
    old, new = SEMVER.match(previous), SEMVER.match(proposed)
    if not old or not new:
        return None
    if int(new["major"]) > int(old["major"]):
        return "major"
    if int(new["major"]) == int(old["major"]) and int(new["minor"]) > int(old["minor"]):
        return "minor"
    if (
        int(new["major"]) == int(old["major"])
        and int(new["minor"]) == int(old["minor"])
        and int(new["patch"]) > int(old["patch"])
    ):
        return "patch"
    return None


_RANK = {"patch": 0, "minor": 1, "major": 2}


def markers_owed(version: str) -> list[str]:
    """Metric markers this release promised and did not fill.

    Delegated to scripts/checks/metric-marker-gate.sh rather than scanned here.
    That gate owns the marker grammar, including the arming tag that says which
    release owes a number, and a second scan in this file answered a different
    question from the first: it read the documentation standard, which states
    the convention and is exempt, and it knew nothing about arming tags.
    """
    gate = REPO_ROOT / "scripts" / "checks" / "metric-marker-gate.sh"
    if not gate.is_file():
        return []
    result = subprocess.run(
        ["sh", str(gate), "--release", version],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    if result.returncode == 0:
        return []
    return [
        line.strip()
        for line in result.stdout.splitlines()
        if "UNFILLED" in line or "CONFLICT" in line or "MALFORMED" in line
    ]


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "version",
        nargs="?",
        help="the version about to be tagged. Without one, only the unreleased state is checked.",
    )
    args = parser.parse_args(argv)

    findings: list[str] = []

    if not CHANGELOG.is_file():
        sys.stderr.write("no CHANGELOG.md\n")
        return 1

    body = unreleased_section() if args.version is None else section_for(args.version)

    if args.version is not None:
        if not SEMVER.match(args.version):
            findings.append(f"{args.version!r} is not a semantic version")
        if body is None:
            findings.append(
                f"CHANGELOG.md carries no section for {args.version}. "
                f"Keep a Changelog 1.1.0 gives every release one"
            )
            body = ""

        released = released_versions()
        previous = next((v for v in released if v != args.version), None)
        if previous and SEMVER.match(args.version):
            needed = required_bump(headings_in(body))
            actual = actual_bump(previous, args.version)
            if actual is None:
                findings.append(f"{args.version} does not move forward from {previous}")
            elif _RANK[actual] < _RANK[needed]:
                headings = ", ".join(sorted(headings_in(body))) or "none"
                findings.append(
                    f"{args.version} is a {actual} bump from {previous}, but the section "
                    f"carries {headings}, which the C9 policy makes a {needed}"
                )

        findings += markers_owed(args.version)

    if body is not None and body.strip():
        unknown = set(re.findall(r"^### (\w+)", body, re.MULTILINE)) - KNOWN_HEADINGS
        for heading in sorted(unknown):
            findings.append(
                f"section heading {heading!r} is not one Keep a Changelog 1.1.0 names: "
                f"{', '.join(sorted(KNOWN_HEADINGS))}"
            )

    if findings:
        sys.stderr.write("\n\033[31mBLOCKED: release gate [REL-001]\033[0m\n")
        for finding in findings:
            sys.stderr.write(f"  {finding}\n")
        return 1

    target = args.version or "the unreleased section"
    print(f"[release] {target} satisfies REL-001")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
