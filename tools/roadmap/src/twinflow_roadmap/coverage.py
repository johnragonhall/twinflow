"""The coverage proof.

"Nothing is ever cut" is the claim this file makes checkable. Every id in the
requirement register is placed in at least one work package, exactly one of the
covering work packages carries `partial: false`, and that one is the last in
build order. An id with no coverage entry is a silent cut, and this project has
no cut list.

The report prints two counts per tier rather than one, because one number was
ambiguous. The bleeding-edge tier holds 47 E-items other than E26, plus E26(a)
through E26(g), which is 54 placed identifiers covering 48 numbered source
entries. Printing only one of those two invites a reader to conclude the other.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from twinflow_roadmap.errors import Finding
from twinflow_roadmap.roadmap import ROADMAP_FILE, Roadmap


@dataclass(frozen=True)
class TierCount:
    tier: str
    #: Requirement ids in this tier, which is what the source numbers.
    requirements: int
    #: Identifiers actually placed. Higher than `requirements` where the source
    #: itself carries lettered sub-items, as E26 does.
    placed_identifiers: int


@dataclass
class CoverageReport:
    tiers: list[TierCount] = field(default_factory=list)
    unplaced: list[str] = field(default_factory=list)
    findings: list[Finding] = field(default_factory=list)
    #: Requirement id to the work packages covering it, in build order.
    placements: dict[str, list[str]] = field(default_factory=dict)
    #: Split labels reached by a coverage note.
    labels_covered: int = 0
    labels_total: int = 0

    @property
    def ok(self) -> bool:
        return not self.unplaced and not self.findings

    def render(self) -> str:
        lines = [
            f"{'tier':<16}{'requirement ids':>17}{'placed identifiers':>21}",
            f"{'-' * 16}{'-' * 17:>17}{'-' * 21:>21}",
        ]
        for count in self.tiers:
            lines.append(f"{count.tier:<16}{count.requirements:>17}{count.placed_identifiers:>21}")
        totals_requirements = sum(count.requirements for count in self.tiers)
        totals_placed = sum(count.placed_identifiers for count in self.tiers)
        lines.append(f"{'total':<16}{totals_requirements:>17}{totals_placed:>21}")
        lines.append("")
        lines.append(
            f"work packages: {sum(len(v) for v in self.placements.values())} coverage entries "
            f"over {len(self.placements)} requirement ids"
        )
        lines.append(f"split labels covered: {self.labels_covered} of {self.labels_total}")
        if self.unplaced:
            lines.append("")
            lines.append(f"unplaced requirement ids ({len(self.unplaced)}):")
            lines += [f"  {identifier}" for identifier in self.unplaced]
        else:
            lines.append("unplaced requirement ids: 0")
        return "\n".join(lines)


def check_coverage(roadmap: Roadmap) -> CoverageReport:
    """Prove every requirement is placed, and that the partial flags close."""
    report = CoverageReport()

    order = {package.id: index for index, package in enumerate(roadmap.work_packages)}
    for package in roadmap.work_packages:
        for cover in package.covers:
            report.placements.setdefault(cover.id, []).append(package.id)

    report.unplaced = sorted(
        identifier for identifier in roadmap.requirements if identifier not in report.placements
    )
    for identifier in report.unplaced:
        report.findings.append(
            Finding(
                "COV-UNPLACED",
                f"{identifier} is in the requirement register and no work package covers it. "
                f"Place it, or record the move in the resequencing register",
                ROADMAP_FILE,
                None,
                (identifier,),
            )
        )

    # Exactly one covering work package carries partial: false, and it is the
    # last one in build order. Two false flags means two work packages each
    # believe they finish the requirement; none means nobody does.
    for identifier, package_ids in report.placements.items():
        entries = []
        for package in roadmap.work_packages:
            for cover in package.covers:
                if cover.id == identifier:
                    entries.append((order[package.id], package.id, cover))
        entries.sort()
        finals = [entry for entry in entries if not entry[2].partial]
        if len(finals) != 1:
            report.findings.append(
                Finding(
                    "COV-PARTIAL",
                    f"{identifier} is covered by {len(entries)} work packages and "
                    f"{len(finals)} of them carry partial: false. Exactly one does, and it is "
                    f"the last one",
                    ROADMAP_FILE,
                    None,
                    (identifier, *package_ids),
                )
            )
        elif finals[0][1] != entries[-1][1]:
            report.findings.append(
                Finding(
                    "COV-LAST",
                    f"{identifier} carries partial: false on {finals[0][1]}, and "
                    f"{entries[-1][1]} covers it later. The last coverage entry is the "
                    f"complete one",
                    ROADMAP_FILE,
                    None,
                    (identifier, finals[0][1], entries[-1][1]),
                )
            )

    covered_labels = {
        (cover.note or "").split(" ")[0]
        for package in roadmap.work_packages
        for cover in package.covers
    }
    report.labels_total = len(roadmap.splits)
    report.labels_covered = len(covered_labels & set(roadmap.splits))

    tiers: dict[str, list[str]] = {}
    for identifier, requirement in roadmap.requirements.items():
        tiers.setdefault(requirement.tier, []).append(identifier)
    for tier in sorted(tiers):
        placed = 0
        for identifier in tiers[tier]:
            sub_items = roadmap.requirements[identifier].source_sub_items
            placed += len(sub_items) if sub_items else 1
        report.tiers.append(TierCount(tier, len(tiers[tier]), placed))

    return report


def missing_quotes(roadmap: Roadmap) -> list[str]:
    """Requirement ids carrying no verbatim clause.

    Reported rather than failed. The source document is not in this repository,
    so a quote arrives when somebody transcribes it, and the append-only check
    is what stops one changing afterwards.
    """
    return sorted(
        identifier
        for identifier, requirement in roadmap.requirements.items()
        if not requirement.quote
    )
