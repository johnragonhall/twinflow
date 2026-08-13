"""Property invariants (C4 tier two).

Each is named as the invariant rather than as the test, and each generates its
own inputs, which is what separates this tier from the rule tests beside it.

The append-only pair is the clearest case for why both tiers exist. The history
test walks the real commits and proves that no edit so far broke the rule. This
one generates pairs of versions and proves the checker is right about edits
nobody has made yet. Neither claim implies the other.
"""

from __future__ import annotations

import tempfile
from pathlib import Path

import pytest
from fixtures import ROADMAP, write_fixture
from hypothesis import HealthCheck, assume, given, settings
from hypothesis import strategies as st

from twinflow_roadmap import dag
from twinflow_roadmap.append_only import check_append_only
from twinflow_roadmap.coverage import check_coverage
from twinflow_roadmap.roadmap import Roadmap

pytestmark = pytest.mark.property

NODES = ["a", "b", "c", "d", "e"]

graphs = st.dictionaries(
    keys=st.sampled_from(NODES),
    values=st.lists(st.sampled_from(NODES), max_size=4, unique=True),
    min_size=1,
    max_size=5,
)

quotes = st.text(min_size=1, max_size=12)
identifiers = st.text(alphabet="ABCDE123", min_size=1, max_size=3)


def _register(draw_ids, quoted):
    return {
        identifier: (
            {"id": identifier, "quote": quoted[identifier]}
            if identifier in quoted
            else {"id": identifier}
        )
        for identifier in draw_ids
    }


@given(graphs)
def test_cycle_detection_and_the_kahn_sort_give_the_same_answer(edges):
    """Two algorithms, one question.

    `cycles` is a depth-first walk and `is_acyclic` is a Kahn sort. They share
    no code, so a generated graph where they disagree is a defect in one of
    them, and that is worth more than one implementation nobody can check.
    """
    assert bool(dag.cycles(edges)) == (not dag.is_acyclic(edges))


@given(graphs)
def test_every_reported_cycle_really_closes(edges):
    for cycle in dag.cycles(edges):
        for earlier, later in zip(cycle, [*cycle[1:], cycle[0]], strict=True):
            assert later in edges.get(earlier, []), (cycle, earlier, later)


@given(graphs)
def test_the_layering_never_puts_a_dependency_after_its_dependant(edges):
    layers = dag.waves(edges)
    position = {node: index for index, layer in enumerate(layers) for node in layer}
    for node, targets in edges.items():
        for target in targets:
            if node in position and target in position:
                assert position[target] < position[node], (node, target)


@given(
    st.lists(identifiers, min_size=1, max_size=6, unique=True),
    st.lists(identifiers, max_size=4, unique=True),
    st.dictionaries(identifiers, quotes, max_size=6),
)
def test_the_append_only_checker_accepts_every_addition(existing, added, quoted):
    """Adding entries is always legal, however many and whatever they say."""
    before = _register(existing, quoted)
    after = _register([*existing, *(item for item in added if item not in existing)], quoted)
    assert check_append_only(before, after) == []


@given(
    st.lists(identifiers, min_size=2, max_size=6, unique=True),
    st.dictionaries(identifiers, quotes, max_size=6),
    st.data(),
)
def test_the_append_only_checker_rejects_every_deletion(existing, quoted, data):
    before = _register(existing, quoted)
    dropped = data.draw(st.sampled_from(existing))
    after = {key: value for key, value in before.items() if key != dropped}
    findings = check_append_only(before, after)
    assert findings, f"removing {dropped} was accepted"
    assert any(dropped in finding.ids for finding in findings)


@given(
    st.lists(identifiers, min_size=1, max_size=6, unique=True),
    quotes,
    quotes,
    st.data(),
)
def test_the_append_only_checker_rejects_every_reworded_clause(existing, was, now, data):
    assume(was != now)
    target = data.draw(st.sampled_from(existing))
    before = {identifier: {"id": identifier, "quote": was} for identifier in existing}
    after = dict(before)
    after[target] = {"id": target, "quote": now}
    findings = check_append_only(before, after)
    assert [finding.rule for finding in findings] == ["APPEND-QUOTE"]
    assert target in findings[0].ids


@settings(max_examples=25, suppress_health_check=[HealthCheck.too_slow], deadline=None)
@given(
    st.lists(
        st.tuples(st.integers(0, 3), st.integers(0, 9), st.integers(0, 9)), min_size=3, max_size=3
    )
)
def test_release_tags_rise_with_the_phase_order(triples):
    """A tag that does not increase along the phase order fails the load.

    Generated rather than enumerated, because the interesting cases are the
    near misses: v0.9.0 after v0.10.0 reads as an increase to anyone comparing
    strings, and is not one.
    """
    tags = [f"v{major}.{minor}.{patch}" for major, minor, patch in triples]
    roadmap_text = ROADMAP
    for old, new in zip(["v0.1.0", "v0.2.0", "v0.3.0"], tags, strict=True):
        roadmap_text = roadmap_text.replace(f"release_tag: {old}", f"release_tag: {new}")

    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory)
        write_fixture(root, roadmap=roadmap_text)
        findings = Roadmap.load(root).validate()

    rising = all(earlier < later for earlier, later in zip(triples, triples[1:], strict=False))
    reported = any(finding.rule == "PHASE-ORDER" for finding in findings)
    assert reported == (not rising), (tags, [str(f) for f in findings])


@settings(max_examples=25, suppress_health_check=[HealthCheck.too_slow], deadline=None)
@given(st.lists(st.booleans(), min_size=2, max_size=2))
def test_exactly_one_covering_work_package_carries_partial_false(flags):
    """The invariant the coverage proof reads.

    E4 is covered twice in the fixture. Whatever the two flags say, the report
    is clean only when the first is partial and the second is not: two false
    flags means two work packages each believe they finish the requirement, and
    none means nobody does.
    """
    first, second = flags
    roadmap_text = ROADMAP.replace(
        '- { id: "E4", partial: true, note: "E4a the historian contract" }',
        f'- {{ id: "E4", partial: {str(first).lower()}, note: "E4a the historian contract" }}',
    ).replace(
        '- { id: "E4", partial: false, note: "E4b counterfactual replay" }',
        f'- {{ id: "E4", partial: {str(second).lower()}, note: "E4b counterfactual replay" }}',
    )

    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory)
        write_fixture(root, roadmap=roadmap_text)
        report = check_coverage(Roadmap.load(root))

    assert report.ok == (first is True and second is False)
