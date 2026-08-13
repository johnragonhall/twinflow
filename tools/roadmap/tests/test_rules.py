"""One test per rule, each against a fixture that breaks exactly that rule.

Every test asserts on a rule id rather than on message wording, so a clearer
message is not a broken test. Several also assert what the message names, where
naming the wrong thing is the failure: a cycle report that names one of three
work packages sends a contributor to the wrong edge.
"""

from __future__ import annotations

import typing

import pytest
from fixtures import GATES, REQUIREMENTS, ROADMAP, rules, write_fixture

from twinflow_roadmap.model import WorkPackageStatus
from twinflow_roadmap.roadmap import Roadmap


def load(tmp_path, **overrides) -> Roadmap:
    write_fixture(tmp_path, **overrides)
    return Roadmap.load(tmp_path)


def test_the_fixture_roadmap_validates_clean(tmp_path):
    assert load(tmp_path).validate() == []


def test_status_enum_has_no_cancellation_value():
    """`canceled` is absent by construction, not by convention.

    Nothing is removed from this plan, so the type that could express removal
    does not exist. Adding one is an edit to model.py and a reviewed diff.
    """
    assert set(typing.get_args(WorkPackageStatus)) == {
        "planned",
        "in_progress",
        "done",
        "reordered",
    }


def test_cycle_detection_names_every_work_package_in_the_cycle(tmp_path):
    broken = ROADMAP.replace(
        "    depends_on: [WP-P0-01]", "    depends_on: [WP-P0-01, WP-P2-01]"
    ).replace(
        """  - id: WP-P2-01
    title: "Judge the telemetry"
    phase: P2
    wave: 1
    covers:
      - { id: "C2", partial: false }
    depends_on: []""",
        """  - id: WP-P2-01
    title: "Judge the telemetry"
    phase: P2
    wave: 1
    covers:
      - { id: "C2", partial: false }
    depends_on: [WP-P1-01]""",
    )
    findings = load(tmp_path, roadmap=broken).validate()
    cycles = [finding for finding in findings if finding.rule == "WP-CYCLE"]
    assert len(cycles) == 1
    assert set(cycles[0].ids) == {"WP-P1-01", "WP-P2-01"}


def test_phase_order_violation_names_both_work_packages(tmp_path):
    broken = ROADMAP.replace("    depends_on: []\n    deliverables: []", "    depends_on: []")
    broken = broken.replace(
        """  - id: WP-P0-01
    title: "Record an append-only event log"
    phase: P0
    wave: 1""",
        """  - id: WP-P0-01
    title: "Record an append-only event log"
    phase: P0
    wave: 1
    depends_on_note: ignored""",
    )
    # A P0 work package depending on a P1 one: the dependency ships later.
    broken = ROADMAP.replace(
        """    depends_on: []
    deliverables: ["packages/twinflow-storage/src/twinflow/storage/historian.py"]""",
        """    depends_on: [WP-P1-01]
    deliverables: ["packages/twinflow-storage/src/twinflow/storage/historian.py"]""",
    )
    findings = load(tmp_path, roadmap=broken).validate()
    offenders = [finding for finding in findings if finding.rule == "WP-PHASE-ORDER"]
    assert len(offenders) == 1
    assert set(offenders[0].ids) == {"WP-P0-01", "WP-P1-01"}


def test_wave_order_violation(tmp_path):
    """Equal waves run in parallel, so a dependency between them cannot hold."""
    broken = (
        ROADMAP
        + """\
  - id: WP-P2-02
    title: "A second P2 package at the same wave"
    phase: P2
    wave: 1
    covers: []
    depends_on: [WP-P2-01]
    deliverables: []
    gates: []
    brick: null
    release: v0.3.0
    status: planned
"""
    )
    assert "WP-WAVE" in rules(load(tmp_path, roadmap=broken).validate())


def test_unknown_requirement_reference_names_the_id_and_the_work_package(tmp_path):
    broken = ROADMAP.replace('{ id: "C2", partial: false }', '{ id: "C99", partial: false }')
    findings = load(tmp_path, roadmap=broken).validate()
    offenders = [finding for finding in findings if finding.rule == "WP-COVER-ID"]
    assert len(offenders) == 1
    assert set(offenders[0].ids) == {"WP-P2-01", "C99"}


def test_covers_rejects_a_bare_string(tmp_path):
    broken = ROADMAP.replace('      - { id: "C2", partial: false }', "      - C2")
    findings = load(tmp_path, roadmap=broken).validate()
    assert "WP-COVER-STRING" in rules(findings)


def test_partial_coverage_requires_a_note(tmp_path):
    broken = ROADMAP.replace(
        '- { id: "E4", partial: true, note: "E4a the historian contract" }',
        '- { id: "E4", partial: true }',
    )
    assert "WP-COVER-NOTE" in rules(load(tmp_path, roadmap=broken).validate())


def test_a_split_label_is_not_a_requirement_id(tmp_path):
    broken = ROADMAP.replace(
        '- { id: "E4", partial: true, note: "E4a the historian contract" }',
        '- { id: "E4a", partial: true, note: "the historian contract" }',
    )
    assert "WP-COVER-SPLIT" in rules(load(tmp_path, roadmap=broken).validate())


def test_a_note_naming_another_requirements_label_is_refused(tmp_path):
    broken = ROADMAP.replace(
        '- { id: "C2", partial: false }',
        '- { id: "C2", partial: false, note: "E4b counterfactual replay" }',
    )
    findings = load(tmp_path, roadmap=broken).validate()
    assert "WP-COVER-NOTE" in rules(findings)


def test_an_unused_split_label_fails(tmp_path):
    broken = ROADMAP.replace('note: "E4b counterfactual replay"', 'note: "the second half"')
    assert "SPL-UNUSED" in rules(load(tmp_path, roadmap=broken).validate())


def test_a_split_on_a_requirement_that_is_not_splittable(tmp_path):
    broken = REQUIREMENTS.replace("    splittable: true\n", "")
    assert "SPL-SPLITTABLE" in rules(load(tmp_path, requirements=broken).validate())


def test_reordered_requires_a_destination_and_a_reason(tmp_path):
    broken = ROADMAP.replace(
        """    release: v0.3.0
    status: planned""",
        """    release: v0.3.0
    status: reordered""",
    )
    findings = [
        finding
        for finding in load(tmp_path, roadmap=broken).validate()
        if finding.rule == "WP-REORDERED"
    ]
    assert len(findings) == 2


def test_exit_gates_cannot_be_authored(tmp_path):
    broken = ROADMAP.replace(
        """    release_tag: v0.1.0""",
        """    release_tag: v0.1.0
    exit_gates: [VAL-GATE-DET-001]""",
    )
    assert "PHASE-EXITGATES" in rules(load(tmp_path, roadmap=broken).validate())


def test_a_phase_id_never_reads_as_a_requirement_id(tmp_path):
    broken = (
        ROADMAP.replace("  - id: P2\n", "  - id: E19\n")
        .replace(
            "    depends_on_phases: [P1]\n    requires_requirements: []\n    release_tag: v0.3.0",
            "    depends_on_phases: [P1]\n    requires_requirements: []\n    release_tag: v0.3.0",
        )
        .replace("    phase: P2", "    phase: E19")
        .replace("WP-P2-01", "WP-E19-01")
    )
    findings = load(tmp_path, roadmap=broken).validate()
    assert "PHASE-ID" in rules(findings)


def test_requires_requirements_refuses_a_phase_id(tmp_path):
    broken = ROADMAP.replace(
        """    depends_on_phases: [P0]
    requires_requirements: []""",
        """    depends_on_phases: [P0]
    requires_requirements: [P0]""",
    )
    findings = [
        finding
        for finding in load(tmp_path, roadmap=broken).validate()
        if finding.rule == "PHASE-REQ"
    ]
    assert len(findings) == 1
    assert "is a phase id" in findings[0].message


def test_release_tags_rise_with_the_phase_order(tmp_path):
    broken = ROADMAP.replace("    release_tag: v0.3.0", "    release_tag: v0.1.5")
    assert "PHASE-ORDER" in rules(load(tmp_path, roadmap=broken).validate())


def test_a_validation_gate_with_no_reference_is_refused(tmp_path):
    broken = GATES.replace(
        """  VAL-GATE-DET-001:
    kind: invariant""",
        """  VAL-GATE-DET-001:
    kind: validation""",
    )
    findings = [
        finding
        for finding in load(tmp_path, gates=broken).validate()
        if finding.rule == "GATE-FIELDS"
    ]
    assert len(findings) == 1
    assert "reference" in findings[0].message


def test_a_ground_truth_gate_with_no_null_model_is_refused(tmp_path):
    broken = GATES.replace(
        """  VAL-GATE-DET-001:
    kind: invariant""",
        """  VAL-GATE-DET-001:
    kind: ground_truth""",
    )
    findings = [
        finding
        for finding in load(tmp_path, gates=broken).validate()
        if finding.rule == "GATE-FIELDS"
    ]
    assert len(findings) == 1
    assert "null_model" in findings[0].message


def test_a_declared_gate_needs_no_assertion_and_no_test_path(tmp_path):
    """A gate declared at Phase 0 has no test on disk, and that is the point.

    Declaring the whole registry early is what forces a subsystem to specify its
    gates one phase ahead. A checker demanding an assertion at declaration would
    make the mechanism impossible to satisfy.
    """
    assert "GATE-FIELDS" not in rules(load(tmp_path).validate())


def test_an_implemented_gate_whose_test_is_missing_fails(tmp_path):
    broken = GATES.replace(
        """    status: specified""",
        """    status: implemented
    test_path: "tests/test_nothing_here.py\"""",
    )
    findings = [
        finding
        for finding in load(tmp_path, gates=broken).validate()
        if finding.rule == "GATE-TEST"
    ]
    assert len(findings) == 1


def test_a_gate_reached_by_the_next_phase_must_be_specified(tmp_path):
    """The mechanism that forces a gate to be specified one phase ahead."""
    broken = ROADMAP.replace(
        """    deliverables: ["packages/twinflow-storage/src/twinflow/storage/replay.py"]
    gates: []""",
        """    deliverables: ["packages/twinflow-storage/src/twinflow/storage/replay.py"]
    gates:
      - VAL-GATE-LATER-001""",
    )
    findings = [
        finding
        for finding in load(tmp_path, roadmap=broken).validate()
        if finding.rule == "GATE-EARLY"
    ]
    assert len(findings) == 1
    assert set(findings[0].ids) == {"VAL-GATE-LATER-001", "WP-P1-01"}


def test_a_gate_nothing_runs_is_refused(tmp_path):
    broken = ROADMAP.replace(
        """    gates:
      - VAL-GATE-LATER-001""",
        """    gates: []""",
    )
    findings = [
        finding
        for finding in load(tmp_path, roadmap=broken).validate()
        if finding.rule == "GATE-ORPHAN"
    ]
    assert len(findings) == 1


def test_a_phase_with_no_work_package_is_refused(tmp_path):
    broken = "\n".join(line for line in ROADMAP.splitlines() if "WP-P2-01" not in line)
    broken = ROADMAP.split("  - id: WP-P2-01")[0]
    findings = load(tmp_path, roadmap=broken).validate()
    assert "PHASE-EMPTY" in rules(findings)


def test_an_unknown_key_in_a_work_package_is_refused(tmp_path):
    """extra=forbid, because a misspelled partal: true loads as an absent flag."""
    broken = ROADMAP.replace(
        "    wave: 1\n    covers:\n", "    wave: 1\n    partal: true\n    covers:\n", 1
    )
    assert "WP-SHAPE" in rules(load(tmp_path, roadmap=broken).validate())


@pytest.mark.parametrize(
    ("identifier", "expected"),
    [
        ("WP-P6-W6-01", ("P6-W6", 1)),
        ("WP-P0-17", ("P0", 17)),
        ("WP-6a10-02", ("6a10", 2)),
        ("WP-P6-W6-1", None),
        ("WP--01", None),
    ],
)
def test_the_work_package_id_grammar(identifier, expected):
    from twinflow_roadmap.model import WORK_PACKAGE_ID

    match = WORK_PACKAGE_ID.match(identifier)
    if expected is None:
        assert match is None
    else:
        assert match is not None
        assert (match.group(1), int(match.group(2))) == expected


def test_findings_print_the_file_the_line_and_the_rule(tmp_path):
    broken = ROADMAP.replace('{ id: "C2", partial: false }', '{ id: "C99", partial: false }')
    finding = next(
        item for item in load(tmp_path, roadmap=broken).validate() if item.rule == "WP-COVER-ID"
    )
    printed = str(finding)
    assert printed.startswith("roadmap.yaml:")
    assert "[WP-COVER-ID]" in printed
    assert finding.line is not None
