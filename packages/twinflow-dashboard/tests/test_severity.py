"""The severity model and the two orderings it owns.

`docs/design/ui-direction.md` section 6.3 is the source: the class rank is a
presentation ordering and never a severity rewrite, and a medium safety finding
sorts above a critical quality finding. Both halves of that sentence are
asserted, because the first without the second is a rule nobody applied and the
second without the first is a producer's severity being quietly rewritten.
"""

from __future__ import annotations

import pytest

from twinflow.dashboard import (
    BANDED_CLASSES,
    FINDING_CLASSES,
    SEVERITIES,
    SEVERITY_CHANNELS,
    finding_class_for,
    finding_sort_key,
    severity_for,
)


def test_the_ladder_descends_in_side_count_as_it_descends_in_severity():
    """Section 6.1: more sides means more severe, which is what makes the
    encoding learnable rather than memorized."""
    ranks = [level.rank for level in SEVERITIES]
    sides = [level.sides for level in SEVERITIES]

    assert ranks == sorted(ranks)
    assert sides == sorted(sides, reverse=True)
    assert len(set(sides)) == len(sides)
    assert min(sides) >= 3, "a polygon needs three sides"


def test_the_four_channels_are_all_named():
    assert SEVERITY_CHANNELS == ("text", "shape", "color", "position")


def test_every_severity_has_a_distinct_label_and_token():
    labels = [level.label for level in SEVERITIES]
    tokens = [level.token for level in SEVERITIES]

    assert len(set(labels)) == len(labels)
    assert len(set(tokens)) == len(tokens)


def test_every_class_rank_is_distinct_and_ascends_from_safety():
    ranks = [finding_class.rank for finding_class in FINDING_CLASSES]

    assert ranks == sorted(ranks)
    assert len(set(ranks)) == len(ranks)
    assert FINDING_CLASSES[0].name == "safety"


def test_no_kind_belongs_to_two_classes():
    """A kind in two classes would sort into two places depending on which row
    the lookup reached first."""
    kinds = [kind for finding_class in FINDING_CLASSES for kind in finding_class.kinds]

    assert len(set(kinds)) == len(kinds)


def test_a_medium_safety_finding_sorts_above_a_critical_quality_finding():
    """The inversion section 6.3 asks for, and the reason the class word renders
    beside the severity word: the ordering is explained on screen."""
    safety = finding_sort_key(
        kind="safety", severity="medium", chattering=False, last_sim_time=1, finding_id="f-2"
    )
    quality = finding_sort_key(
        kind="spc_violation",
        severity="critical",
        chattering=False,
        last_sim_time=9,
        finding_id="f-1",
    )

    assert safety < quality


def test_the_class_rank_never_rewrites_the_severity():
    """`P-CLASS-ORDER` in the design's section 14. The severity the producer
    emitted is what renders, whatever the class does to the ordering."""
    for finding_class in FINDING_CLASSES:
        for kind in finding_class.kinds:
            key = finding_sort_key(
                kind=kind,
                severity="high",
                chattering=False,
                last_sim_time=0,
                finding_id="f",
            )
            assert key[1] == severity_for("high").rank


def test_a_chattering_finding_sorts_below_its_quiet_twin():
    quiet = finding_sort_key(
        kind="fleet_health", severity="high", chattering=False, last_sim_time=5, finding_id="f"
    )
    chattering = finding_sort_key(
        kind="fleet_health", severity="high", chattering=True, last_sim_time=5, finding_id="f"
    )

    assert quiet < chattering


def test_the_more_recent_of_two_equal_findings_sorts_first():
    older = finding_sort_key(
        kind="other", severity="low", chattering=False, last_sim_time=1, finding_id="f"
    )
    newer = finding_sort_key(
        kind="other", severity="low", chattering=False, last_sim_time=99, finding_id="f"
    )

    assert newer < older


def test_the_sort_key_is_total_so_the_list_does_not_reshuffle():
    """Two findings agreeing on every other component would otherwise sort by
    delivery order, and the list would move under the reader for no reason."""
    first = finding_sort_key(
        kind="other", severity="low", chattering=False, last_sim_time=1, finding_id="f-1"
    )
    second = finding_sort_key(
        kind="other", severity="low", chattering=False, last_sim_time=1, finding_id="f-2"
    )

    assert first < second


def test_an_unmapped_kind_falls_to_other_rather_than_taking_the_panel_down():
    """A kind added to the schema in a later phase renders with a lower rank.
    `CT-UI-2` is what notices the gap, and it belongs in CI."""
    assert finding_class_for("a_kind_from_phase_nine").name == "other"


def test_the_banded_classes_are_the_two_that_get_the_exemption():
    """Section 6.3: only safety and security render in the band that is exempt
    from every reduction of section 7."""
    assert BANDED_CLASSES == ("safety", "security")
    for name in BANDED_CLASSES:
        assert finding_class_for(name).name == name


def test_an_unknown_severity_is_refused_by_name():
    """A severity present in the schema and absent here would render as an
    unstyled blank, which is the failure CT-UI-2 exists to catch."""
    with pytest.raises(KeyError, match="critcal"):
        severity_for("critcal")
