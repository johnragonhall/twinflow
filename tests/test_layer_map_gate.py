"""VAL-GATE-TIER-001, the RA-a layer map held to its own completeness rule.

The gate reads: every package in the uv workspace appears in the layer map with
its ISA-95 level, its Purdue level, its compute tier, and its latency budget
filled. One unfilled cell, or one package with no row, falsifies it.

Two things are worth asserting separately, and this file does both. That the
shipped map is complete is the gate. That the checker can say otherwise is the
evidence the gate is a gate at all, because a completeness check written against
a document that already passes is a check nobody has watched refuse anything
(doctrine D-12).

The third assertion is the one that catches the quiet regression. Every case in
the checker's own selftest corpus is parametrized here by rule id, so a rule
that stops firing names itself in the failure rather than disappearing into an
aggregate that still reports green.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
GATE = REPO_ROOT / "scripts" / "checks" / "layer-map-gate.py"


def _load():
    """Import the checker by path, because its filename is not an identifier."""
    spec = importlib.util.spec_from_file_location("layer_map_gate", GATE)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


gate = _load()


def test_the_shipped_map_is_complete():
    """The gate itself, run the way the phase-exit runner runs it."""
    assert gate.main([]) == 0


def test_the_selftest_passes():
    """Each rule fires against a map that breaks it, and a complete map stays
    quiet. A checker that only ever saw a passing document proves nothing."""
    assert gate.selftest() == 0


@pytest.mark.parametrize(
    ("rule", "description", "source"),
    gate.SELFTEST_CASES,
    ids=[f"{rule}-{description}" for rule, description, _ in gate.SELFTEST_CASES],
)
def test_each_broken_map_fires_its_rule(rule, description, source):
    """Named per case, so a rule that goes quiet says which one it was."""
    fired = {finding.rule for finding in gate.check_map(source, gate.SELFTEST_MEMBERS, "<test>")}
    assert rule in fired, f"nothing fired for {description}"


def test_a_complete_map_fires_nothing():
    """The other half of the selftest, asserted here so a checker that reported
    every document as broken would fail rather than look strict."""
    complete = gate._fixture([gate._KERNEL, gate._RNG])
    assert gate.check_map(complete, gate.SELFTEST_MEMBERS, "<test>") == []


def test_every_workspace_member_is_asked_for_a_row():
    """The member list is read from the root pyproject globs rather than from a
    hand-kept list, so a package added under packages/ owes a row the day it
    lands. This is the assertion that would fail on the next new brick."""
    members = gate.workspace_members(REPO_ROOT / "pyproject.toml")
    assert "twinflow-roadmap" in members, (
        "a member that lives outside packages/ is still a member, which is the "
        "rule workspace-members-gate.py already settled"
    )
    for package in (REPO_ROOT / "packages").iterdir():
        if (package / "pyproject.toml").is_file():
            assert package.name in members, f"{package.name} is a member with no row owed"


def test_a_map_missing_a_member_is_refused():
    """The falsifier's first clause, stated directly rather than only through
    the selftest corpus."""
    only_one = gate._fixture([gate._KERNEL])
    findings = gate.check_map(only_one, gate.SELFTEST_MEMBERS, "<test>")
    assert any("twinflow-rng" in finding.message for finding in findings)


def test_a_map_with_an_unfilled_cell_is_refused():
    """The falsifier's second clause."""
    blanked = gate._fixture([gate._KERNEL, gate._with(gate._RNG, 4, "TBD")])
    assert gate.check_map(blanked, gate.SELFTEST_MEMBERS, "<test>") != []
