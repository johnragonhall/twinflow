#!/usr/bin/env python3
"""Layer map gate, VAL-GATE-TIER-001.

The gate registry states the assertion this script implements:

    Every package in the uv workspace appears in the RA-a layer map with its
    ISA-95 level, its Purdue level, its compute tier, and its latency budget
    filled.

and what falsifies it:

    One unfilled cell in the layer map, or one package with no row.

WHICH PACKAGES

Read from tool.uv.workspace.members in the root pyproject.toml, resolved to
project.name, which is the same set and the same route scripts/checks/workspace-members-gate.py
takes. That gate records why the route matters: "A member that lives somewhere
else is still a member: twinflow-roadmap sits under tools/ because it is not
part of the twinflow namespace, and a gate scoped to packages/ lets it ship with
no LICENSE." The assertion above says workspace, not `packages/`, so a tooling
member owes a row like every other member. Its row says it is outside the layer
model, which is a statement a reader can act on. A silent exclusion is not.

WHICH TABLE

The one after the `<!-- layer-map:packages -->` anchor in the document. The map
carries more than one table, and a gate that grabs the first table it finds
breaks the day somebody adds a table above it.

WHY A METRIC MARKER IS REFUSED IN THE FOUR CHECKED COLUMNS

A latency budget is a design decision, and it is knowable the moment the package
is placed at a tier. A measurement is a different quantity and it belongs behind
a marker in prose, where the metric marker gate can count it. A marker in the
budget column would be a package with no declared budget wearing the costume of
one, and the gate's own word is "filled".

Usage:

    python scripts/checks/layer-map-gate.py             check the shipped map
    python scripts/checks/layer-map-gate.py PATH        check a named map
    python scripts/checks/layer-map-gate.py --selftest  prove each finding fires

Needs no third-party module: tomllib is in the standard library from 3.11.
"""

from __future__ import annotations

import argparse
import contextlib
import io
import re
import sys
import tomllib
from pathlib import Path

for _stream in (sys.stdout, sys.stderr):
    if isinstance(_stream, io.TextIOWrapper):
        # reconfigure raises on an encoding this platform lacks.
        with contextlib.suppress(ValueError):
            _stream.reconfigure(encoding="utf-8")

REPO_ROOT = Path(__file__).resolve().parents[2]
ROOT_PYPROJECT = REPO_ROOT / "pyproject.toml"
LAYER_MAP = REPO_ROOT / "docs" / "reference" / "layer-map.md"

RED = "\033[31m"
GREEN = "\033[32m"
RESET = "\033[0m"

#: The comment that marks the machine-checked table.
ANCHOR = "<!-- layer-map:packages -->"

#: The column that names the package, and the four the gate requires filled.
KEY_COLUMN = "Package"
REQUIRED_COLUMNS = ("ISA-95", "Purdue", "Compute tier", "Latency budget")

#: A cell holding one of these says nothing, whatever it looks like in a render.
PLACEHOLDERS = frozenset({"", "-", "--", "---", "?", "n/a", "na", "none", "tbd", "todo", "..."})

#: `<!--METRIC:name@v1.1.0-->TBD<!--/METRIC-->`, in the form
#: scripts/checks/metric-marker-gate.sh defines.
METRIC_MARKER = re.compile(r"<!--METRIC:[A-Za-z0-9_]+(?:@v[0-9]+\.[0-9]+\.[0-9]+)?-->")


class Finding:
    """One thing wrong with the map, and where."""

    __slots__ = ("rule", "where", "message")

    def __init__(self, rule: str, where: str, message: str) -> None:
        self.rule = rule
        self.where = where
        self.message = message

    def render(self) -> str:
        return f"  [{self.rule}] {self.where}\n      {self.message}"


def workspace_members(root_pyproject: Path) -> list[str]:
    """Every distribution the workspace claims, by project.name.

    The globs are read rather than assumed, so a member added outside
    `packages/` is a member here too.
    """
    root = tomllib.loads(root_pyproject.read_text(encoding="utf-8"))
    globs = root.get("tool", {}).get("uv", {}).get("workspace", {}).get("members", [])
    repo_root = root_pyproject.parent

    names: list[str] = []
    for pattern in globs:
        for path in sorted(repo_root.glob(pattern)):
            manifest = path / "pyproject.toml"
            if not (path.is_dir() and manifest.is_file()):
                continue
            name = (
                tomllib.loads(manifest.read_text(encoding="utf-8")).get("project", {}).get("name")
            )
            if name:
                names.append(str(name))
    return sorted(set(names))


def _split_row(line: str) -> list[str]:
    """The cells of one markdown table row, without the outer pipes."""
    stripped = line.strip()
    if stripped.startswith("|"):
        stripped = stripped[1:]
    if stripped.endswith("|"):
        stripped = stripped[:-1]
    return [cell.strip() for cell in stripped.split("|")]


def _is_alignment_row(cells: list[str]) -> bool:
    return bool(cells) and all(re.fullmatch(r":?-{3,}:?", cell) for cell in cells)


def parse_anchored_table(text: str) -> tuple[list[str], list[list[str]], list[Finding]]:
    """The header and body of the table that follows the anchor.

    Returns empty lists beside a finding when the anchor or the table is
    missing, so the caller reports one clear cause rather than a cascade.
    """
    if ANCHOR not in text:
        return (
            [],
            [],
            [
                Finding(
                    "MAP-1",
                    LAYER_MAP.name,
                    f"no {ANCHOR} anchor, so nothing says which table the gate reads",
                )
            ],
        )

    after = text.split(ANCHOR, 1)[1].splitlines()
    header: list[str] = []
    rows: list[list[str]] = []
    seen_alignment = False

    for line in after:
        stripped = line.strip()
        if not stripped.startswith("|"):
            if header:
                break
            continue
        cells = _split_row(line)
        if not header:
            header = cells
            continue
        if not seen_alignment and _is_alignment_row(cells):
            seen_alignment = True
            continue
        rows.append(cells)

    if not header:
        return ([], [], [Finding("MAP-1", LAYER_MAP.name, "the anchor is followed by no table")])
    if not seen_alignment:
        return (
            header,
            [],
            [Finding("MAP-1", LAYER_MAP.name, "the table after the anchor has no alignment row")],
        )
    return header, rows, []


def check_map(text: str, members: list[str], where: str) -> list[Finding]:
    """Every finding the gate has against one layer map."""
    header, rows, findings = parse_anchored_table(text)
    if findings:
        return findings

    missing_columns = [column for column in (KEY_COLUMN, *REQUIRED_COLUMNS) if column not in header]
    if missing_columns:
        return [
            Finding(
                "MAP-2",
                where,
                f"the table is missing the column(s) {', '.join(missing_columns)}. "
                f"It carries: {', '.join(header)}",
            )
        ]

    key_index = header.index(KEY_COLUMN)
    indexes = {column: header.index(column) for column in REQUIRED_COLUMNS}

    documented: dict[str, list[str]] = {}
    for number, cells in enumerate(rows, start=1):
        if len(cells) != len(header):
            findings.append(
                Finding(
                    "MAP-2",
                    f"{where}  row {number}",
                    f"has {len(cells)} cells against {len(header)} columns",
                )
            )
            continue
        # The package cell is written as `twinflow-rng` in the document, because
        # a reader copies it into an install command.
        name = cells[key_index].strip().strip("`")
        if not name:
            findings.append(Finding("MAP-2", f"{where}  row {number}", "names no package"))
            continue
        if name in documented:
            findings.append(
                Finding("MAP-3", f"{where}  row {number}", f"{name} already has a row above")
            )
            continue
        documented[name] = cells

    for name in members:
        if name not in documented:
            findings.append(
                Finding(
                    "TIER-1",
                    where,
                    f"{name} is a workspace member with no row. Every package in the "
                    f"workspace appears in the layer map",
                )
            )

    for name in sorted(documented):
        if name not in members:
            findings.append(
                Finding(
                    "MAP-3",
                    where,
                    f"{name} has a row and is not a workspace member. Either the member "
                    f"went away and the row stayed, or the row misspells it",
                )
            )

    for name in sorted(documented):
        if name not in members:
            continue
        cells = documented[name]
        for column in REQUIRED_COLUMNS:
            value = cells[indexes[column]].strip().strip("`")
            if value.lower() in PLACEHOLDERS:
                findings.append(
                    Finding(
                        "TIER-1",
                        f"{where}  {name}",
                        f"the {column} cell is unfilled. One unfilled cell falsifies "
                        f"VAL-GATE-TIER-001",
                    )
                )
            elif METRIC_MARKER.search(value):
                findings.append(
                    Finding(
                        "TIER-2",
                        f"{where}  {name}",
                        f"the {column} cell holds a metric marker. A budget is a decision "
                        f"and is knowable now; a measurement belongs in prose, where the "
                        f"metric marker gate counts it",
                    )
                )

    return findings


SELFTEST_MEMBERS = ["twinflow-kernel", "twinflow-rng"]

#: The fixture rows, short enough that a case reads as the one thing it breaks.
_HEADER = ["Package", "ISA-95", "Purdue", "Compute tier", "Latency budget"]
_KERNEL = ["`twinflow-kernel`", "Cross-cutting", "Cross-cutting", "0 to 3", "The caller's"]
_RNG = ["`twinflow-rng`", "Cross-cutting", "Cross-cutting", "0 to 3", "The caller's"]


def _fixture(rows: list[list[str]], header: list[str] | None = None) -> str:
    """A minimal document carrying the anchor and one table."""
    columns = header or _HEADER
    lines = [
        "intro prose",
        "",
        ANCHOR,
        "",
        "| " + " | ".join(columns) + " |",
        "|" + "|".join("---" for _ in columns) + "|",
    ]
    lines += ["| " + " | ".join(row) + " |" for row in rows]
    lines += ["", "closing prose"]
    return "\n".join(lines)


def _with(row: list[str], index: int, value: str) -> list[str]:
    changed = list(row)
    changed[index] = value
    return changed


_MARKER_CELL = "<!--METRIC:x@v1.1.0-->TBD<!--/METRIC-->"

SELFTEST_CASES: tuple[tuple[str, str, str], ...] = (
    ("TIER-1", "a workspace member with no row", _fixture([_KERNEL])),
    (
        "TIER-1",
        "an unfilled latency budget",
        _fixture([_KERNEL, _with(_RNG, 4, "TBD")]),
    ),
    (
        "TIER-1",
        "an unfilled Purdue level written as a dash",
        _fixture([_KERNEL, _with(_RNG, 2, "-")]),
    ),
    (
        "TIER-2",
        "a metric marker standing in for a budget",
        _fixture([_KERNEL, _with(_RNG, 4, _MARKER_CELL)]),
    ),
    ("MAP-1", "a document with no anchor", _fixture([_KERNEL, _RNG]).replace(ANCHOR, "")),
    (
        "MAP-2",
        "a renamed required column",
        _fixture([_KERNEL, _RNG], _with(_HEADER, 4, "Latency")),
    ),
    (
        "MAP-3",
        "a row for a package the workspace does not hold",
        _fixture([_KERNEL, _RNG, _with(_RNG, 0, "`twinflow-ghost`")]),
    ),
)

#: The map every case above is a mutation of. It has to stay quiet.
_GOOD_MAP = _fixture([_KERNEL, _RNG])


def selftest() -> int:
    """Prove each finding fires, and that a complete map stays quiet.

    A gate nobody has seen fail may be passing because it cannot fail. Each case
    breaks one thing, and the case fails when the rule it breaks stays quiet.
    """
    failures: list[str] = []

    for rule, description, source in SELFTEST_CASES:
        fired = {finding.rule for finding in check_map(source, SELFTEST_MEMBERS, "<selftest>")}
        if rule not in fired:
            saw = ", ".join(sorted(fired)) or "nothing"
            failures.append(f"{rule} did not fire on: {description} (fired: {saw})")

    noise = check_map(_GOOD_MAP, SELFTEST_MEMBERS, "<selftest>")
    if noise:
        failures.append(
            "a complete map reported: " + ", ".join(f"{f.rule} {f.message}" for f in noise)
        )

    if failures:
        sys.stderr.write(f"\n{RED}BLOCKED: layer map selftest [VAL-GATE-TIER-001]{RESET}\n")
        for failure in failures:
            sys.stderr.write(f"  {failure}\n")
        return 1

    print(
        f"{GREEN}[layer-map] selftest: {len(SELFTEST_CASES)} findings fire, "
        f"and a complete map stays quiet{RESET}"
    )
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("path", nargs="?", help="the layer map to check")
    parser.add_argument("--selftest", action="store_true", help="prove each finding fires")
    args = parser.parse_args(argv)

    if args.selftest:
        return selftest()

    if not ROOT_PYPROJECT.is_file():
        sys.stderr.write(f"BLOCKED: no {ROOT_PYPROJECT}\n")
        return 1

    members = workspace_members(ROOT_PYPROJECT)
    if not members:
        sys.stderr.write(
            f"\n{RED}BLOCKED: the workspace claims no members [VAL-GATE-TIER-001]{RESET}\n"
            "  With no members this gate compares the map against nothing and passes.\n"
        )
        return 1

    path = Path(args.path).resolve() if args.path else LAYER_MAP
    where = path.relative_to(REPO_ROOT).as_posix() if path.is_relative_to(REPO_ROOT) else str(path)

    if not path.is_file():
        sys.stderr.write(
            f"\n{RED}BLOCKED: there is no layer map [VAL-GATE-TIER-001]{RESET}\n"
            f"  [TIER-1] {where}\n"
            f"      RA-a says the layer map is published and asserted in CI. This file does\n"
            f"      not exist, so all {len(members)} workspace members are unmapped.\n"
        )
        return 1

    findings = check_map(path.read_text(encoding="utf-8"), members, where)

    if findings:
        sys.stderr.write(
            f"\n{RED}BLOCKED: the layer map is incomplete [VAL-GATE-TIER-001]{RESET}\n"
        )
        for finding in findings:
            sys.stderr.write(finding.render() + "\n")
        sys.stderr.write(
            "\nThe gate registry states it: every package in the uv workspace appears in the\n"
            "RA-a layer map with its ISA-95 level, its Purdue level, its compute tier, and\n"
            "its latency budget filled.\n"
        )
        return 1

    print(
        f"[layer-map] {len(members)} workspace members, each with a row carrying "
        f"{', '.join(REQUIRED_COLUMNS)}"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
