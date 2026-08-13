"""The aggregate: four files read together, and every rule that spans them.

Nothing here raises on the first problem. Every check appends a finding and the
caller prints the whole set, because a validator that stops at the first error
tells a contributor about one of the eight things they got wrong and lets them
find the other seven one CI run at a time.

The rules are grouped by the file they read, and each carries a rule id. The id
is stable; the wording is not.
"""

from __future__ import annotations

import tomllib
from dataclasses import dataclass, field
from pathlib import Path

from pydantic import ValidationError as PydanticError

from twinflow_roadmap import dag, yamlio
from twinflow_roadmap.errors import Finding, RoadmapError
from twinflow_roadmap.model import (
    PHASE_IDS,
    SPLIT_LABEL,
    Coverage,
    Gate,
    Phase,
    Requirement,
    Split,
    WorkPackage,
    semver,
)

REQUIREMENTS_FILE = "requirements.yaml"
SPLITS_FILE = "splits.yaml"
GATES_FILE = "gates.yaml"
ROADMAP_FILE = "roadmap.yaml"


def _pydantic_findings(
    error: PydanticError, rule: str, path: str, line: int | None
) -> list[Finding]:
    """One finding per model error, naming the field rather than the whole object."""
    findings = []
    for detail in error.errors():
        location = ".".join(str(part) for part in detail["loc"]) or "(root)"
        findings.append(Finding(rule, f"{location}: {detail['msg']}", path, line))
    return findings


@dataclass
class Roadmap:
    """Everything the four files hold, plus where each entry came from."""

    root: Path
    requirements: dict[str, Requirement] = field(default_factory=dict)
    splits: dict[str, Split] = field(default_factory=dict)
    gates: dict[str, Gate] = field(default_factory=dict)
    phases: list[Phase] = field(default_factory=list)
    work_packages: list[WorkPackage] = field(default_factory=list)
    #: Findings raised while reading, before any cross-file rule runs.
    load_findings: list[Finding] = field(default_factory=list)
    #: Identifier to the line it is declared on, for findings raised later.
    lines: dict[tuple[str, str], int | None] = field(default_factory=dict)

    # -- loading -----------------------------------------------------------

    @classmethod
    def load(cls, root: Path) -> Roadmap:
        """Read the four files. A file that cannot be parsed at all raises."""
        roadmap = cls(root=root)
        roadmap._load_requirements()
        roadmap._load_splits()
        roadmap._load_gates()
        roadmap._load_roadmap()
        return roadmap

    def _load_requirements(self) -> None:
        document = yamlio.read(self.root / REQUIREMENTS_FILE)
        entries = document.get("requirements") or []
        for index, entry in enumerate(entries):
            line = yamlio.line_of(entries, index)
            self.lines[(REQUIREMENTS_FILE, str(entry.get("id")))] = line
            try:
                requirement = Requirement(**yamlio.plain(entry))
            except PydanticError as error:
                self.load_findings += _pydantic_findings(
                    error, "REQ-SHAPE", REQUIREMENTS_FILE, line
                )
                continue
            if requirement.id in self.requirements:
                self.load_findings.append(
                    Finding(
                        "REQ-DUP",
                        f"requirement id {requirement.id} appears twice; ids are unique "
                        f"across the register",
                        REQUIREMENTS_FILE,
                        line,
                        (requirement.id,),
                    )
                )
                continue
            self.requirements[requirement.id] = requirement

    def _load_splits(self) -> None:
        document = yamlio.read(self.root / SPLITS_FILE)
        entries = document.get("splits") or {}
        for label, entry in entries.items():
            line = yamlio.line_of(entries, label)
            self.lines[(SPLITS_FILE, label)] = line
            try:
                self.splits[label] = Split(**yamlio.plain(entry))
            except PydanticError as error:
                self.load_findings += _pydantic_findings(error, "SPL-SHAPE", SPLITS_FILE, line)

    def _load_gates(self) -> None:
        document = yamlio.read(self.root / GATES_FILE)
        entries = document.get("gates") or {}
        for gate_id, entry in entries.items():
            line = yamlio.line_of(entries, gate_id)
            self.lines[(GATES_FILE, gate_id)] = line
            try:
                self.gates[gate_id] = Gate(id=gate_id, **yamlio.plain(entry))
            except PydanticError as error:
                self.load_findings += _pydantic_findings(error, "GATE-SHAPE", GATES_FILE, line)

    def _load_roadmap(self) -> None:
        document = yamlio.read(self.root / ROADMAP_FILE)

        for index, entry in enumerate(document.get("phases") or []):
            line = yamlio.line_of(document.get("phases"), index)
            self.lines[(ROADMAP_FILE, str(entry.get("id")))] = line
            # exit_gates is derived from the gate registry. Refusing it here,
            # rather than ignoring it, is what stops the phase table and the
            # registry acquiring two sources and drifting apart.
            if "exit_gates" in entry:
                self.load_findings.append(
                    Finding(
                        "PHASE-EXITGATES",
                        f"phase {entry.get('id')} authors exit_gates; that list is derived "
                        f"from gates.yaml. Delete the key",
                        ROADMAP_FILE,
                        yamlio.line_of(entry, "exit_gates"),
                        (str(entry.get("id")),),
                    )
                )
                entry = {k: v for k, v in entry.items() if k != "exit_gates"}
            try:
                self.phases.append(Phase(**yamlio.plain(entry)))
            except PydanticError as error:
                self.load_findings += _pydantic_findings(error, "PHASE-SHAPE", ROADMAP_FILE, line)

        packages = document.get("work_packages") or []
        for index, entry in enumerate(packages):
            line = yamlio.line_of(packages, index)
            self.lines[(ROADMAP_FILE, str(entry.get("id")))] = line
            covers = entry.get("covers") or []
            bare = [item for item in covers if not isinstance(item, dict)]
            if bare:
                self.load_findings.append(
                    Finding(
                        "WP-COVER-STRING",
                        f"{entry.get('id')} covers names {bare[0]!r} as a bare string; a "
                        f"coverage entry is a mapping, because a string cannot carry partial",
                        ROADMAP_FILE,
                        yamlio.line_of(entry, "covers"),
                        (str(entry.get("id")),),
                    )
                )
                entry = {**entry, "covers": [item for item in covers if isinstance(item, dict)]}
            try:
                self.work_packages.append(WorkPackage(**yamlio.plain(entry)))
            except PydanticError as error:
                self.load_findings += _pydantic_findings(error, "WP-SHAPE", ROADMAP_FILE, line)

    # -- derived views -----------------------------------------------------

    @property
    def phase_order(self) -> list[str]:
        return [phase.id for phase in self.phases]

    def phase_index(self, phase_id: str) -> int:
        try:
            return self.phase_order.index(phase_id)
        except ValueError:
            return -1

    @property
    def open_phase(self) -> str | None:
        """The earliest phase holding a work package that is not done.

        Derived rather than configured. A phase pointer in a file is a pointer
        somebody forgets to move, and the whole point of the current-and-next
        rules is that they follow the build.
        """
        for phase_id in self.phase_order:
            for package in self.work_packages:
                if package.phase == phase_id and package.status != "done":
                    return phase_id
        return self.phase_order[-1] if self.phase_order else None

    @property
    def next_phase(self) -> str | None:
        current = self.open_phase
        if current is None:
            return None
        index = self.phase_index(current)
        if index < 0 or index + 1 >= len(self.phase_order):
            return None
        return self.phase_order[index + 1]

    def exit_gates(self, phase_id: str) -> list[str]:
        """Every gate whose first phase is this one, plus every standing gate
        already in force. Derived from the registry and never authored."""
        index = self.phase_index(phase_id)
        gates = []
        for gate_id, gate in sorted(self.gates.items()):
            first = self.phase_index(gate.first_phase)
            if gate.first_phase == phase_id or (gate.standing and 0 <= first <= index):
                gates.append(gate_id)
        return gates

    def workspace_bricks(self) -> set[str]:
        """The distribution names the uv workspace actually holds."""
        names = set()
        for parent in ("packages", "tools"):
            directory = self.root / parent
            if not directory.is_dir():
                continue
            for manifest in sorted(directory.glob("*/pyproject.toml")):
                data = tomllib.loads(manifest.read_text(encoding="utf-8"))
                name = data.get("project", {}).get("name")
                if name:
                    names.add(name)
        return names

    def _line(self, file: str, identifier: str) -> int | None:
        return self.lines.get((file, identifier))

    # -- validation --------------------------------------------------------

    def validate(self) -> list[Finding]:
        """Every rule that spans the four files, in file order."""
        findings = list(self.load_findings)
        findings += self._validate_phases()
        findings += self._validate_splits()
        findings += self._validate_gates()
        findings += self._validate_work_packages()
        return findings

    def _validate_phases(self) -> list[Finding]:
        findings: list[Finding] = []
        seen: set[str] = set()
        previous_tag: tuple[int, int, int] | None = None

        for phase in self.phases:
            line = self._line(ROADMAP_FILE, phase.id)
            if phase.id not in PHASE_IDS:
                findings.append(
                    Finding(
                        "PHASE-ID",
                        f"{phase.id} is not a declared phase id. The set is closed, so that a "
                        f"requirement id cannot pass as a phase id; adding a phase is an edit "
                        f"to PHASE_IDS in model.py",
                        ROADMAP_FILE,
                        line,
                        (phase.id,),
                    )
                )
            if phase.id in seen:
                findings.append(
                    Finding("PHASE-DUP", f"phase id {phase.id} appears twice", ROADMAP_FILE, line)
                )
            seen.add(phase.id)

            for dependency in phase.depends_on_phases:
                if dependency not in {other.id for other in self.phases}:
                    findings.append(
                        Finding(
                            "PHASE-DEP",
                            f"{phase.id} depends on phase {dependency}, which no phase declares",
                            ROADMAP_FILE,
                            line,
                            (phase.id, dependency),
                        )
                    )
            for requirement in phase.requires_requirements:
                if requirement in {other.id for other in self.phases}:
                    findings.append(
                        Finding(
                            "PHASE-REQ",
                            f"{phase.id} requires {requirement}, which is a phase id. This "
                            f"field names requirements; phases go in depends_on_phases",
                            ROADMAP_FILE,
                            line,
                            (phase.id, requirement),
                        )
                    )
                elif requirement not in self.requirements:
                    findings.append(
                        Finding(
                            "PHASE-REQ",
                            f"{phase.id} requires {requirement}, which the requirement "
                            f"register does not carry",
                            ROADMAP_FILE,
                            line,
                            (phase.id, requirement),
                        )
                    )

            parsed = semver(phase.release_tag)
            if parsed is None:
                findings.append(
                    Finding(
                        "PHASE-TAG",
                        f"{phase.id} carries release tag {phase.release_tag}, which is not "
                        f"semver of the form vMAJOR.MINOR.PATCH",
                        ROADMAP_FILE,
                        line,
                        (phase.id,),
                    )
                )
            elif previous_tag is not None and parsed <= previous_tag:
                findings.append(
                    Finding(
                        "PHASE-ORDER",
                        f"{phase.id} carries {phase.release_tag}, which does not increase on "
                        f"the phase before it. Release tags rise with the phase order",
                        ROADMAP_FILE,
                        line,
                        (phase.id,),
                    )
                )
            if parsed is not None:
                previous_tag = parsed

        # A phase holding no work package is a release with nothing in it.
        held = {package.phase for package in self.work_packages}
        for phase in self.phases:
            if phase.id not in held:
                findings.append(
                    Finding(
                        "PHASE-EMPTY",
                        f"phase {phase.id} holds no work package",
                        ROADMAP_FILE,
                        self._line(ROADMAP_FILE, phase.id),
                        (phase.id,),
                    )
                )

        findings += self._cycle_findings(
            {phase.id: list(phase.depends_on_phases) for phase in self.phases},
            "PHASE-CYCLE",
            ROADMAP_FILE,
            "phase",
        )
        return findings

    def _validate_splits(self) -> list[Finding]:
        findings: list[Finding] = []
        package_ids = {package.id for package in self.work_packages}
        for label, split in self.splits.items():
            line = self._line(SPLITS_FILE, label)
            requirement = self.requirements.get(split.requirement)
            if requirement is None:
                findings.append(
                    Finding(
                        "SPL-REQ",
                        f"split {label} names requirement {split.requirement}, which the "
                        f"register does not carry",
                        SPLITS_FILE,
                        line,
                        (label,),
                    )
                )
            elif not requirement.splittable:
                findings.append(
                    Finding(
                        "SPL-SPLITTABLE",
                        f"split {label} names {split.requirement}, which is not marked "
                        f"splittable. Mark it, or drop the split",
                        SPLITS_FILE,
                        line,
                        (label,),
                    )
                )
            match = SPLIT_LABEL.match(label)
            if match is None or match.group(1) != split.requirement:
                findings.append(
                    Finding(
                        "SPL-LABEL",
                        f"split label {label} does not read as {split.requirement} plus one "
                        f"letter, so a coverage note naming it cannot be checked",
                        SPLITS_FILE,
                        line,
                        (label,),
                    )
                )
            if split.work_package not in package_ids:
                findings.append(
                    Finding(
                        "SPL-WP",
                        f"split {label} names work package {split.work_package}, which "
                        f"roadmap.yaml does not carry",
                        SPLITS_FILE,
                        line,
                        (label, split.work_package),
                    )
                )

        # Every label reaches a work package. A label nothing covers is a half
        # of a split that nobody is building, which is the failure the split
        # register exists to make visible.
        covered = {
            (cover.note or "").split(" ")[0]
            for package in self.work_packages
            for cover in package.covers
        }
        for label in self.splits:
            if label not in covered:
                findings.append(
                    Finding(
                        "SPL-UNUSED",
                        f"no work package covers split {label}. Name it in the note of the "
                        f"coverage entry that lands it",
                        SPLITS_FILE,
                        self._line(SPLITS_FILE, label),
                        (label,),
                    )
                )
        return findings

    def _validate_gates(self) -> list[Finding]:
        findings: list[Finding] = []
        referenced: dict[str, list[WorkPackage]] = {}
        for package in self.work_packages:
            for gate_id in package.gates:
                referenced.setdefault(gate_id, []).append(package)

        for gate_id, gate in self.gates.items():
            line = self._line(GATES_FILE, gate_id)
            if self.phase_index(gate.first_phase) < 0:
                findings.append(
                    Finding(
                        "GATE-PHASE",
                        f"{gate_id} is first enforced at {gate.first_phase}, which no phase "
                        f"declares",
                        GATES_FILE,
                        line,
                        (gate_id,),
                    )
                )
            missing = [name for name in gate.required_fields() if not getattr(gate, name, None)]
            if missing:
                findings.append(
                    Finding(
                        "GATE-FIELDS",
                        f"{gate_id} is at status {gate.status} of kind {gate.kind} and carries "
                        f"no {', '.join(missing)}. A gate of that kind owes those fields",
                        GATES_FILE,
                        line,
                        (gate_id,),
                    )
                )
            if gate.status == "implemented":
                if not gate.test_path:
                    findings.append(
                        Finding(
                            "GATE-TEST",
                            f"{gate_id} is implemented and names no test_path",
                            GATES_FILE,
                            line,
                            (gate_id,),
                        )
                    )
                elif not (self.root / gate.test_path).exists():
                    findings.append(
                        Finding(
                            "GATE-TEST",
                            f"{gate_id} names test_path {gate.test_path}, which is not on "
                            f"disk. Either the test moved or the status is ahead of the work",
                            GATES_FILE,
                            line,
                            (gate_id,),
                        )
                    )
            if not gate.standing and gate_id not in referenced:
                findings.append(
                    Finding(
                        "GATE-ORPHAN",
                        f"{gate_id} is neither standing nor referenced by a work package, so "
                        f"nothing ever runs it",
                        GATES_FILE,
                        line,
                        (gate_id,),
                    )
                )

        # The mechanism that forces a subsystem to specify its gates one phase
        # ahead of implementing them. Without it, a phase opens with gates that
        # say nothing, and the phase-exit suite passes by being empty.
        soon = {self.open_phase, self.next_phase} - {None}
        for gate_id, packages in referenced.items():
            gate = self.gates.get(gate_id)
            if gate is None:
                for package in packages:
                    findings.append(
                        Finding(
                            "WP-GATE",
                            f"{package.id} references {gate_id}, which the gate registry does "
                            f"not carry",
                            ROADMAP_FILE,
                            self._line(ROADMAP_FILE, package.id),
                            (package.id, gate_id),
                        )
                    )
                continue
            if gate.status != "declared":
                continue
            for package in packages:
                if package.phase in soon:
                    findings.append(
                        Finding(
                            "GATE-EARLY",
                            f"{gate_id} is still declared and {package.id} in phase "
                            f"{package.phase} references it. A gate reached by the open phase "
                            f"or the next one carries its assertion and its falsifier",
                            GATES_FILE,
                            self._line(GATES_FILE, gate_id),
                            (gate_id, package.id),
                        )
                    )
        return findings

    def _validate_work_packages(self) -> list[Finding]:
        findings: list[Finding] = []
        by_id: dict[str, WorkPackage] = {}
        phase_ids = {phase.id for phase in self.phases}
        bricks = self.workspace_bricks()
        soon = {self.open_phase, self.next_phase} - {None}

        for package in self.work_packages:
            line = self._line(ROADMAP_FILE, package.id)
            if package.id in by_id:
                findings.append(
                    Finding(
                        "WP-DUP",
                        f"work package id {package.id} appears twice",
                        ROADMAP_FILE,
                        line,
                        (package.id,),
                    )
                )
            by_id[package.id] = package

            parsed = package.parsed_id
            if parsed is None:
                findings.append(
                    Finding(
                        "WP-ID",
                        f"{package.id} does not read as WP-<phase>-<nn> with a two-digit ordinal",
                        ROADMAP_FILE,
                        line,
                        (package.id,),
                    )
                )
            elif parsed[0] != package.phase:
                findings.append(
                    Finding(
                        "WP-PHASE",
                        f"{package.id} sits in phase {package.phase}, and its id says {parsed[0]}",
                        ROADMAP_FILE,
                        line,
                        (package.id,),
                    )
                )
            if package.phase not in phase_ids:
                findings.append(
                    Finding(
                        "WP-PHASE",
                        f"{package.id} names phase {package.phase}, which no phase declares",
                        ROADMAP_FILE,
                        line,
                        (package.id,),
                    )
                )

            findings += self._validate_covers(package, line)

            if package.status == "reordered":
                if not package.moved_to:
                    findings.append(
                        Finding(
                            "WP-REORDERED",
                            f"{package.id} is reordered and names no moved_to phase",
                            ROADMAP_FILE,
                            line,
                            (package.id,),
                        )
                    )
                if not package.reason or len(package.reason) < 20:
                    findings.append(
                        Finding(
                            "WP-REORDERED",
                            f"{package.id} is reordered and carries no reason of at least 20 "
                            f"characters. Reordering is recorded, not silent",
                            ROADMAP_FILE,
                            line,
                            (package.id,),
                        )
                    )

            # Deliverables are owed by the open phase and the next one. Naming
            # a module path for a phase eight releases out would be invention,
            # and invention in a plan reads as fact later.
            if package.phase in soon and not package.deliverables:
                findings.append(
                    Finding(
                        "WP-DELIVERABLE",
                        f"{package.id} is in phase {package.phase} and names no deliverable. "
                        f"The open phase and the next one name theirs",
                        ROADMAP_FILE,
                        line,
                        (package.id,),
                    )
                )

            # The brick is checked once the work has landed. Before then it
            # names a package the roadmap has not built yet, which is the
            # normal case rather than an error.
            if (
                package.status in ("done", "in_progress")
                and package.brick
                and package.brick not in bricks
            ):
                findings.append(
                    Finding(
                        "WP-BRICK",
                        f"{package.id} is {package.status} and lands in {package.brick}, "
                        f"which is not a package in this workspace",
                        ROADMAP_FILE,
                        line,
                        (package.id, package.brick),
                    )
                )

        for package in self.work_packages:
            line = self._line(ROADMAP_FILE, package.id)
            for dependency in package.depends_on:
                other = by_id.get(dependency)
                if other is None:
                    findings.append(
                        Finding(
                            "WP-DEP",
                            f"{package.id} depends on {dependency}, which roadmap.yaml does "
                            f"not carry",
                            ROADMAP_FILE,
                            line,
                            (package.id, dependency),
                        )
                    )
                    continue
                here, there = self.phase_index(package.phase), self.phase_index(other.phase)
                if there > here:
                    findings.append(
                        Finding(
                            "WP-PHASE-ORDER",
                            f"{package.id} in {package.phase} depends on {dependency} in "
                            f"{other.phase}, which ships later",
                            ROADMAP_FILE,
                            line,
                            (package.id, dependency),
                        )
                    )
                elif there == here and other.wave >= package.wave:
                    findings.append(
                        Finding(
                            "WP-WAVE",
                            f"{package.id} at wave {package.wave} depends on {dependency} at "
                            f"wave {other.wave} in the same phase. Equal waves run in "
                            f"parallel, so a dependency needs a lower wave",
                            ROADMAP_FILE,
                            line,
                            (package.id, dependency),
                        )
                    )

        findings += self._cycle_findings(
            {package.id: list(package.depends_on) for package in self.work_packages},
            "WP-CYCLE",
            ROADMAP_FILE,
            "work package",
        )
        return findings

    def _validate_covers(self, package: WorkPackage, line: int | None) -> list[Finding]:
        findings: list[Finding] = []
        for cover in package.covers:
            if cover.id in self.splits:
                findings.append(
                    Finding(
                        "WP-COVER-SPLIT",
                        f"{package.id} covers {cover.id}, which is a split label. A coverage "
                        f"entry names the source requirement and puts the label in the note",
                        ROADMAP_FILE,
                        line,
                        (package.id, cover.id),
                    )
                )
                continue
            if cover.id not in self.requirements:
                findings.append(
                    Finding(
                        "WP-COVER-ID",
                        f"{package.id} covers {cover.id}, which the requirement register does "
                        f"not carry",
                        ROADMAP_FILE,
                        line,
                        (package.id, cover.id),
                    )
                )
                continue
            if cover.partial and not cover.note:
                findings.append(
                    Finding(
                        "WP-COVER-NOTE",
                        f"{package.id} covers {cover.id} partially with no note. A partial "
                        f"coverage says which part it lands",
                        ROADMAP_FILE,
                        line,
                        (package.id, cover.id),
                    )
                )
            label = (cover.note or "").split(" ")[0]
            if label in self.splits and self.splits[label].requirement != cover.id:
                findings.append(
                    Finding(
                        "WP-COVER-NOTE",
                        f"{package.id} covers {cover.id} under label {label}, which belongs "
                        f"to {self.splits[label].requirement}",
                        ROADMAP_FILE,
                        line,
                        (package.id, cover.id, label),
                    )
                )
        return findings

    def _cycle_findings(
        self, edges: dict[str, list[str]], rule: str, path: str, noun: str
    ) -> list[Finding]:
        return [
            Finding(
                rule,
                f"{noun} dependency cycle: {' -> '.join([*cycle, cycle[0]])}",
                path,
                self._line(path, cycle[0]),
                cycle,
            )
            for cycle in dag.cycles(edges)
        ]

    # -- ordering ----------------------------------------------------------

    def topological_waves(self) -> list[list[WorkPackage]]:
        """Work packages grouped into layers that may run together.

        Anything left when nothing is ready sits on a cycle, and validate names
        it. This returns the layers it could order so a caller sees the shape
        either way.
        """
        by_id = {package.id: package for package in self.work_packages}
        edges = {package.id: list(package.depends_on) for package in self.work_packages}
        return [[by_id[identifier] for identifier in layer] for layer in dag.waves(edges)]


def load(root: Path | None = None) -> Roadmap:
    """Load from a repository root, defaulting to the one this file sits in."""
    if root is None:
        root = Path(__file__).resolve().parents[4]
    return Roadmap.load(root)


__all__ = ["Roadmap", "RoadmapError", "load", "Coverage", "Gate", "Phase", "WorkPackage"]
