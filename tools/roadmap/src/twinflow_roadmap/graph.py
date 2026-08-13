"""The phase graph, rendered and re-parsed.

ROADMAP.md carries a Mermaid diagram of the phase order. A diagram maintained by
hand beside a machine-readable file is a diagram that drifts, and a drifted
dependency graph is worse than none: a reader trusts the picture.

So the picture is checked rather than trusted. `graph-lint` renders the graph
from roadmap.yaml, re-parses the block committed in ROADMAP.md, and asserts four
things about the pair:

  1. Both name the same phases. A phase missing from the picture is a release a
     reader cannot see.
  2. The solid edges are the release order, in order.
  3. Every dotted edge is backed by a real dependency: either a phase the target
     declares in depends_on_phases, or a requirement the target requires that is
     placed in the source phase. Soundness, not completeness: the diagram is
     allowed to draw the crossing dependencies that matter and leave the rest to
     the phase entries, but it is not allowed to draw one that does not exist.
  4. The whole graph is acyclic, self-loops included.

Phases are matched to nodes by release tag rather than by node key or by label
text, because five phases carry a node key and a label that name the milestone
inside them rather than the phase id. The tag is unique per phase and appears in
every label, which makes it the one field that cannot be ambiguous.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

from twinflow_roadmap import dag
from twinflow_roadmap.errors import Finding
from twinflow_roadmap.roadmap import Roadmap

#: `P3d["P3d Planning and E12 v0.7.0"]`
NODE = re.compile(r'^\s*([A-Za-z0-9_]+)\["([^"]+)"\]\s*$')
#: `A --> B`, and `A -. label .-> B`, with chains of either.
SOLID_EDGE = re.compile(r"-->")
DOTTED_EDGE = re.compile(r"-\.(.*?)\.->")
TAG = re.compile(r"v\d+\.\d+\.\d+")

MERMAID_BLOCK = re.compile(r"```mermaid\n(.*?)```", re.DOTALL)


@dataclass
class ParsedGraph:
    nodes: dict[str, str] = field(default_factory=dict)
    solid: list[tuple[str, str]] = field(default_factory=list)
    dotted: list[tuple[str, str, str]] = field(default_factory=list)


def render_mermaid(roadmap: Roadmap) -> str:
    """The phase graph as roadmap.yaml holds it.

    Solid edges are the release order and dotted edges are the dependencies that
    cross it, which is the same convention ROADMAP.md states above its diagram.
    """
    lines = ["graph TD"]
    for phase in roadmap.phases:
        lines.append(f'  {_key(phase.id)}["{phase.id} {phase.name} {phase.release_tag}"]')
    lines.append("")
    order = roadmap.phase_order
    for earlier, later in zip(order, order[1:], strict=False):
        lines.append(f"  {_key(earlier)} --> {_key(later)}")
    for phase in roadmap.phases:
        index = roadmap.phase_index(phase.id)
        for dependency in phase.depends_on_phases:
            if roadmap.phase_index(dependency) == index - 1:
                continue  # already drawn as the release order
            lines.append(f"  {_key(dependency)} -. crosses the release order .-> {_key(phase.id)}")
    return "\n".join(lines) + "\n"


def _key(phase_id: str) -> str:
    """A Mermaid node key. Mermaid rejects a key opening with a digit."""
    return phase_id.replace("-", "_") if phase_id[0].isalpha() else f"P{phase_id}"


def parse_mermaid(text: str) -> ParsedGraph:
    """Read a rendered graph back, so a claim about it can be checked."""
    graph = ParsedGraph()
    for line in text.splitlines():
        node = NODE.match(line)
        if node:
            graph.nodes[node.group(1)] = node.group(2)
            continue
        stripped = line.strip()
        if not stripped or stripped.startswith(("graph", "%%")):
            continue
        dotted = DOTTED_EDGE.search(stripped)
        if dotted:
            left, right = DOTTED_EDGE.split(stripped)[0], DOTTED_EDGE.split(stripped)[-1]
            graph.dotted.append((left.strip(), right.strip(), dotted.group(1).strip()))
            continue
        if SOLID_EDGE.search(stripped):
            chain = [part.strip() for part in SOLID_EDGE.split(stripped)]
            for earlier, later in zip(chain, chain[1:], strict=False):
                graph.solid.append((earlier, later))
    return graph


def extract_block(markdown: str) -> str | None:
    """The first Mermaid block in a document, or None."""
    match = MERMAID_BLOCK.search(markdown)
    return match.group(1) if match else None


def graph_lint(roadmap: Roadmap, document: Path) -> list[Finding]:
    """Check the committed diagram against roadmap.yaml."""
    findings: list[Finding] = []
    relative = document.name
    if not document.is_file():
        return [Finding("GRAPH-MISSING", f"{relative} is not on disk", relative)]

    block = extract_block(document.read_text(encoding="utf-8"))
    if block is None:
        return [
            Finding(
                "GRAPH-MISSING",
                f"{relative} carries no mermaid block, so the phase graph is unchecked",
                relative,
            )
        ]

    parsed = parse_mermaid(block)

    # Match nodes to phases by the release tag in the label.
    by_tag = {phase.release_tag: phase.id for phase in roadmap.phases}
    node_phase: dict[str, str] = {}
    for key, label in parsed.nodes.items():
        tags = TAG.findall(label)
        if len(tags) != 1 or tags[0] not in by_tag:
            findings.append(
                Finding(
                    "GRAPH-NODE",
                    f"node {key} is labeled {label!r} and names no release tag that "
                    f"roadmap.yaml declares, so it cannot be matched to a phase",
                    relative,
                    ids=(key,),
                )
            )
            continue
        node_phase[key] = by_tag[tags[0]]

    drawn = set(node_phase.values())
    for phase in roadmap.phases:
        if phase.id not in drawn:
            findings.append(
                Finding(
                    "GRAPH-NODE",
                    f"phase {phase.id} ({phase.release_tag}) has no node in the diagram",
                    relative,
                    ids=(phase.id,),
                )
            )

    solid = [
        (node_phase[left], node_phase[right])
        for left, right in parsed.solid
        if left in node_phase and right in node_phase
    ]
    expected = list(zip(roadmap.phase_order, roadmap.phase_order[1:], strict=False))
    if solid != expected:
        missing = [edge for edge in expected if edge not in solid]
        extra = [edge for edge in solid if edge not in expected]
        detail = []
        if missing:
            detail.append("missing " + ", ".join(f"{a} to {b}" for a, b in missing[:4]))
        if extra:
            detail.append("extra " + ", ".join(f"{a} to {b}" for a, b in extra[:4]))
        if not detail:
            detail.append("the same edges in a different order")
        findings.append(
            Finding(
                "GRAPH-ORDER",
                f"the solid edges are not the release order: {'; '.join(detail)}",
                relative,
            )
        )

    for left, right, label in parsed.dotted:
        if left not in node_phase or right not in node_phase:
            findings.append(
                Finding(
                    "GRAPH-EDGE",
                    f"dotted edge {left} to {right} names a node the diagram does not declare",
                    relative,
                )
            )
            continue
        source, target = node_phase[left], node_phase[right]
        if not _backed(roadmap, source, target):
            findings.append(
                Finding(
                    "GRAPH-EDGE",
                    f"the diagram draws {source} to {target} ({label}), and {target} neither "
                    f"depends on that phase nor requires a requirement placed in it",
                    relative,
                    ids=(source, target),
                )
            )

    edges: dict[str, list[str]] = {phase.id: [] for phase in roadmap.phases}
    for source, target in solid:
        edges[source].append(target)
    for left, right, _label in parsed.dotted:
        if left in node_phase and right in node_phase:
            edges[node_phase[left]].append(node_phase[right])
    findings += _cycles(edges, relative)
    return findings


def _backed(roadmap: Roadmap, source: str, target: str) -> bool:
    """Is there a real dependency behind this drawn edge?"""
    phase = next((p for p in roadmap.phases if p.id == target), None)
    if phase is None:
        return False
    if source in phase.depends_on_phases:
        return True
    placed = {
        cover.id
        for package in roadmap.work_packages
        if package.phase == source
        for cover in package.covers
    }
    return any(requirement in placed for requirement in phase.requires_requirements)


def _cycles(edges: dict[str, list[str]], path: str) -> list[Finding]:
    return [
        Finding(
            "GRAPH-CYCLE",
            f"the diagram is not acyclic: {' -> '.join([*cycle, cycle[0]])}",
            path,
            ids=cycle,
        )
        for cycle in dag.cycles(edges)
    ]
