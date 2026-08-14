"""VAL-GATE-DOC-001, and the property that makes a tag-qualified clause honest.

Three of the gate's clauses hold at every tag. The fourth asks the README's
opening to carry the E1 replay URL and one metric marker, and E1 is a bundle
`VAL-GATE-E1-001` starts asserting at v0.3.0. A clause asserted before its input
exists fails for a reason that is not a defect; a clause that never arms is a
clause nobody watched refuse anything. So the tests below assert both edges: it
stays quiet before the tag and refuses at it.

Every case in the checker's selftest corpus is parametrized here by name, so a
refusal that stops firing names itself rather than disappearing into an
aggregate that still reports green.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
GATE = REPO_ROOT / "scripts" / "checks" / "docs-gate.py"


def _load():
    """Import the checker by path, because its filename is not an identifier."""
    spec = importlib.util.spec_from_file_location("docs_gate", GATE)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


gate = _load()


@pytest.mark.parametrize(
    ("name", "head", "release", "should_find"),
    gate.SELFTEST_CASES,
    ids=[case[0] for case in gate.SELFTEST_CASES],
)
def test_each_selftest_case_lands_the_way_it_says(
    name: str, head: str, release: tuple[int, int, int] | None, should_find: bool
):
    assert bool(gate.readme_findings(head, release=release)) is should_find


def test_the_selftest_runs_clean():
    assert gate.main(["--selftest"]) == 0


def test_the_clause_stays_quiet_before_its_input_exists():
    """At v0.2.0 there is no replay bundle and no seeded headline number, so an
    opening carrying neither is complete rather than deficient."""
    assert gate.readme_findings("# twinflow\n\nA digital twin.\n", release=(0, 2, 0)) == []


def test_the_clause_refuses_at_the_tag_its_input_arrives_at():
    """The control for the test above. A clause that stayed quiet forever would
    pass it while asserting nothing at any tag."""
    findings = gate.readme_findings("# twinflow\n\nA digital twin.\n", release=(0, 3, 0))

    assert len(findings) == 2
    assert any("replay URL" in finding for finding in findings)
    assert any("metric markers" in finding for finding in findings)


def test_a_version_is_compared_field_by_field():
    """A string comparison puts v0.10.0 before v0.9.0, which would arm the
    clause a release early."""
    assert gate.version_tuple("0.9.0") < gate.version_tuple("0.10.0")
    assert gate.version_tuple("v1.2.3") == (1, 2, 3)
    for bad in ("1.2", "1.2.3.4", "one.two.three", ""):
        with pytest.raises(ValueError):
            gate.version_tuple(bad)


def test_the_shipped_tree_passes_the_tag_being_cut():
    """The gate itself, run the way the release ritual runs it."""
    assert gate.main(["--release", "0.2.0"]) == 0
