"""The shipped roadmap, checked as data rather than read as prose.

This is the test `VAL-GATE-RMAP-001` names. It asserts on the four files this
repository actually ships, so a work package that lands without a coverage entry
fails here rather than being noticed by a reader a year later.

The tier counts are asserted as numbers on purpose. A silent drop shows up as a
count mismatch, and a missing line in a table nobody reads shows up as nothing.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest
from ruamel.yaml import YAML

import twinflow_roadmap
from twinflow_roadmap.append_only import check_append_only
from twinflow_roadmap.coverage import check_coverage
from twinflow_roadmap.drift import check_drift
from twinflow_roadmap.graph import graph_lint, parse_mermaid, render_mermaid
from twinflow_roadmap.roadmap import Roadmap

REPO_ROOT = Path(__file__).resolve().parents[3]


@pytest.fixture(scope="module")
def roadmap() -> Roadmap:
    return Roadmap.load(REPO_ROOT)


def test_the_shipped_roadmap_validates(roadmap):
    findings = roadmap.validate()
    assert findings == [], "\n".join(str(finding) for finding in findings)


def test_the_open_phase_and_the_next_one_are_derived_not_configured(roadmap):
    """A phase pointer in a file is a pointer somebody forgets to move.

    Asserted as the property rather than as this month's answer. Naming the
    phase here would put the pointer back, one file over, and the assertion
    would then need editing at every phase exit, which is the failure the
    derivation exists to remove.
    """
    order = roadmap.phase_order
    open_phase = roadmap.open_phase
    assert open_phase in order

    before = order[: order.index(open_phase)]
    landed = [p for p in roadmap.work_packages if p.phase in before and p.status != "done"]
    assert landed == [], [package.id for package in landed]

    assert any(
        package.phase == open_phase and package.status != "done"
        for package in roadmap.work_packages
    ), f"{open_phase} is open and holds nothing unfinished"

    assert roadmap.next_phase == order[order.index(open_phase) + 1]


def test_every_requirement_is_placed(roadmap):
    report = check_coverage(roadmap)
    assert report.unplaced == []
    assert report.findings == []


def test_the_tier_counts(roadmap):
    """The counts the coverage proof publishes, asserted one by one.

    Two numbers per tier, because a single number is ambiguous. The bleeding-edge tier
    holds 47 E-items other than E26, plus E26(a) through E26(g), which is 54
    placed identifiers covering 48 numbered source entries.

    The craft tier holds 13 and not the 12 the source numbers: C13, the
    contributor agreement check, joined the plan under change 5 of the
    resequencing record, because CLA.md, CONTRIBUTING.md, and the pull request
    template each describe a check that no workflow performed.
    """
    counts = {tier.tier: tier for tier in check_coverage(roadmap).tiers}
    assert counts["component"].requirements == 30
    assert counts["bleeding_edge"].requirements == 48
    assert counts["bleeding_edge"].placed_identifiers == 54
    assert counts["craft"].requirements == 13
    assert counts["adoption"].requirements == 6
    assert counts["reference_arch"].requirements == 6
    assert counts["constraint"].requirements == 16
    assert sum(tier.requirements for tier in counts.values()) == len(roadmap.requirements)


def test_every_split_label_reaches_a_work_package(roadmap):
    report = check_coverage(roadmap)
    assert report.labels_covered == report.labels_total == len(roadmap.splits)


def test_the_gate_registry_declares_every_phase_gate_at_phase_zero(roadmap):
    """Declaring the whole set early is what forces one phase of lead time."""
    assert len(roadmap.gates) > 100
    for gate_id, gate in roadmap.gates.items():
        assert roadmap.phase_index(gate.first_phase) >= 0, gate_id


def test_the_gates_the_open_phase_exits_on(roadmap):
    exit_gates = set(roadmap.exit_gates("P0"))
    for gate_id in (
        "VAL-GATE-DET-001",
        "VAL-GATE-DET-002",
        "VAL-GATE-ENV-001",
        "VAL-GATE-SCH-001",
        "VAL-GATE-CFG-001",
        "VAL-GATE-SEC-001",
        "VAL-GATE-REL-001",
        "VAL-GATE-RMAP-001",
    ):
        assert gate_id in exit_gates, gate_id
    # A gate that starts later is not a P0 exit gate, standing or not.
    assert "VAL-GATE-QS-001" not in exit_gates
    assert "VAL-GATE-QS-001" in set(roadmap.exit_gates("P1"))


def test_a_standing_gate_re_runs_at_every_later_phase(roadmap):
    """The whole point of standing: it is introduced once and never retired."""
    assert "VAL-GATE-DET-001" in set(roadmap.exit_gates("P6-W6"))


def test_the_phase_diagram_in_the_readme_matches_the_data(roadmap):
    findings = graph_lint(roadmap, REPO_ROOT / "ROADMAP.md")
    assert findings == [], "\n".join(str(finding) for finding in findings)


def test_the_rendered_graph_round_trips(roadmap):
    """Render, re-parse, and get the same phases and the same release order."""
    parsed = parse_mermaid(render_mermaid(roadmap))
    assert len(parsed.nodes) == len(roadmap.phases)
    assert len(parsed.solid) == len(roadmap.phases) - 1


def test_rendering_is_deterministic(roadmap):
    assert render_mermaid(roadmap) == render_mermaid(roadmap)


def test_drift_passes_offline(roadmap):
    """CI runs this on a checkout with no tracker credentials."""
    report = check_drift(roadmap, offline=True)
    assert report.findings == [], "\n".join(str(finding) for finding in report.findings)
    assert report.skipped, "an offline run says what it did not check"


def test_the_topological_order_covers_every_work_package(roadmap):
    waves = roadmap.topological_waves()
    ordered = [package.id for wave in waves for package in wave]
    assert sorted(ordered) == sorted(package.id for package in roadmap.work_packages)


def test_the_public_surface_is_importable():
    for name in twinflow_roadmap.__all__:
        assert hasattr(twinflow_roadmap, name), name


def _git(*args: str) -> str | None:
    try:
        completed = subprocess.run(  # noqa: S603
            ["git", *args],  # noqa: S607
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            check=False,
        )
    except OSError:
        return None
    return completed.stdout if completed.returncode == 0 else None


def test_requirements_are_append_only_over_the_real_git_history():
    """No entry removed and no quote altered between consecutive commits.

    A deterministic walk of one corpus, so it proves nothing about commits
    nobody has made yet. The property beside it covers those, and both call the
    same checker so neither can pass against a rule the other does not enforce.
    """
    log = _git("log", "--format=%H", "--", "requirements.yaml")
    if log is None:
        pytest.skip("git is not available here")
    commits = log.split()
    if len(commits) < 2:
        pytest.skip("requirements.yaml has one commit, so there is no pair to compare")

    parser = YAML(typ="safe")

    def entries(commit: str) -> dict[str, dict]:
        document = parser.load(_git("show", f"{commit}:requirements.yaml")) or {}
        return {entry["id"]: entry for entry in document.get("requirements") or []}

    # git log lists newest first, so walk it backwards to read the history in
    # the order it happened.
    findings = []
    for newer, older in zip(commits, commits[1:], strict=False):
        findings += check_append_only(entries(older), entries(newer), revision=newer[:8])
    assert findings == [], "; ".join(str(finding) for finding in findings)
