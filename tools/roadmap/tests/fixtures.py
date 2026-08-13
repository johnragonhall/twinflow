"""A minimal four-file roadmap, and the knobs a negative test turns.

Every rule test builds its own tiny repository rather than editing the shipped
one. A test that mutates the real files passes or fails depending on what the
build has reached that week, which is the opposite of what a rule test is for.
"""

from __future__ import annotations

import textwrap
from pathlib import Path

REQUIREMENTS = """\
version: 1
requirements:
  - id: "E4"
    tier: bleeding_edge
    title: "Event-sourced replay and counterfactuals"
    splittable: true
  - id: "C1"
    tier: craft
    title: "Determinism: one run seed, splittable child seeds"
  - id: "C2"
    tier: craft
    title: "Sim time against wall clock"
"""

SPLITS = """\
version: 1
splits:
  E4a:
    requirement: "E4"
    work_package: "WP-P0-01"
    title: "The historian contract"
  E4b:
    requirement: "E4"
    work_package: "WP-P1-01"
    title: "Counterfactual replay"
"""

GATES = """\
version: 1
gates:
  VAL-GATE-DET-001:
    kind: invariant
    status: specified
    first_phase: P0
    standing: true
    owner_section: "docs/design/foundations.md"
    assertion: "Two runs at one seed produce byte-identical logs."
    falsified_by: "One differing byte."
  VAL-GATE-LATER-001:
    kind: invariant
    status: declared
    first_phase: P2
    standing: false
    owner_section: "docs/design/foundations.md"
"""

ROADMAP = """\
version: 1

phases:
  - id: P0
    name: "Contracts"
    delivers: "The contracts."
    depends_on_phases: []
    requires_requirements: []
    release_tag: v0.1.0
  - id: P1
    name: "Walking skeleton"
    delivers: "One station end to end."
    depends_on_phases: [P0]
    requires_requirements: []
    release_tag: v0.2.0
  - id: P2
    name: "The judge"
    delivers: "The engine that judges."
    depends_on_phases: [P1]
    requires_requirements: []
    release_tag: v0.3.0

work_packages:
  - id: WP-P0-01
    title: "Record an append-only event log"
    phase: P0
    wave: 1
    covers:
      - { id: "E4", partial: true, note: "E4a the historian contract" }
      - { id: "C1", partial: false }
    depends_on: []
    deliverables: ["packages/twinflow-storage/src/twinflow/storage/historian.py"]
    gates:
      - VAL-GATE-DET-001
    brick: null
    release: v0.1.0
    status: planned
  - id: WP-P1-01
    title: "Replay counterfactually"
    phase: P1
    wave: 1
    covers:
      - { id: "E4", partial: false, note: "E4b counterfactual replay" }
    depends_on: [WP-P0-01]
    deliverables: ["packages/twinflow-storage/src/twinflow/storage/replay.py"]
    gates: []
    brick: null
    release: v0.2.0
    status: planned
  - id: WP-P2-01
    title: "Judge the telemetry"
    phase: P2
    wave: 1
    covers:
      - { id: "C2", partial: false }
    depends_on: []
    deliverables: []
    gates:
      - VAL-GATE-LATER-001
    brick: null
    release: v0.3.0
    status: planned
"""

SYNC = """\
repo: owner/twinflow
project_number: 1
milestone_title_template: "{phase_id} {name} ({release_tag})"
issue_title_template: "[{phase_id}] {id} {title}"
banned_labels: [wontfix]
create_sub_issues_over: 5
dry_run_default: true
allowed_apply_contexts: [release-workflow]
"""


def write_fixture(
    root: Path,
    *,
    requirements: str = REQUIREMENTS,
    splits: str = SPLITS,
    gates: str = GATES,
    roadmap: str = ROADMAP,
    sync: str = SYNC,
) -> Path:
    (root / "requirements.yaml").write_text(requirements, encoding="utf-8")
    (root / "splits.yaml").write_text(splits, encoding="utf-8")
    (root / "gates.yaml").write_text(gates, encoding="utf-8")
    (root / "roadmap.yaml").write_text(roadmap, encoding="utf-8")
    (root / ".roadmap-sync.yaml").write_text(sync, encoding="utf-8")
    return root


def work_package(body: str) -> str:
    """Append one work package to the fixture roadmap."""
    return ROADMAP + textwrap.dedent(body)


def rules(findings) -> set[str]:
    return {finding.rule for finding in findings}
