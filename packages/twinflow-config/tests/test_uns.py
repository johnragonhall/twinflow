"""The UNS contract of ARCHITECTURE.md section 5, asserted rather than assumed.

Every rule in that section's naming table gets an observation that fails it.
The concrete P1 topics printed in that section are used as fixtures, so a change
to either the document or the value object shows up here.

This file is the union of two suites that used to sit in twinflow-sensors and
twinflow-storage, one per rendering of the same six levels. Both sets of
fixtures are kept rather than reconciled to one, because they were written
against different failure modes: the publish side probed the characters a topic
string cannot survive, and the storage side probed the shapes a kebab-case or
snake_case rule admits by accident. The union is the grammar.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import pytest

from twinflow.config import TOPIC_LEVELS, NamingError, UnsPath

#: Two of the concrete P1 topics printed in ARCHITECTURE.md section 5.
PORTAL_TOPIC = "twinflow/dc-01/receiving/inbound-line-01/portal-03/read_rate"
CONVEYOR_TOPIC = "twinflow/dc-01/receiving/inbound-line-01/conveyor-02/motor_temp_c"

REPO_ROOT = Path(__file__).resolve().parents[3]
ARCHITECTURE = REPO_ROOT / "ARCHITECTURE.md"

PORTAL = UnsPath(
    enterprise="twinflow",
    site="dc-01",
    area="receiving",
    line="inbound-line-01",
    equipment="portal-03",
    parameter="read_rate",
)


def _with_equipment(bad: str) -> UnsPath:
    return UnsPath(
        enterprise="twinflow",
        site="dc-01",
        area="receiving",
        line="inbound-line-01",
        equipment=bad,
        parameter="read_rate",
    )


def _from_config(**levels: Any) -> UnsPath:
    """The six levels as a config file supplies them.

    A YAML scalar arrives as whatever the parser made of it, so the values are
    as wide here as they are at the boundary this models. Every level a
    hand-written call site passes is a `str`, and the helpers below say so.
    """
    return UnsPath(**levels)


def _with_site(bad: str) -> UnsPath:
    return UnsPath(
        enterprise="twinflow",
        site=bad,
        area="receiving",
        line="inbound-line-01",
        equipment="portal-03",
        parameter="read_rate",
    )


def _with_parameter(bad: str) -> UnsPath:
    return UnsPath(
        enterprise="twinflow",
        site="dc-01",
        area="receiving",
        line="inbound-line-01",
        equipment="portal-03",
        parameter=bad,
    )


# ------------------------------------------------------------ the six levels


def test_the_two_published_p1_topics_render_exactly():
    conveyor = PORTAL.with_equipment("conveyor-02").with_parameter("motor_temp_c")
    assert PORTAL.topic == PORTAL_TOPIC
    assert conveyor.topic == CONVEYOR_TOPIC


def test_a_device_telemetry_topic_has_exactly_six_levels():
    path = UnsPath.parse(PORTAL_TOPIC)
    assert path.topic.count("/") == 5
    assert path.levels == (
        "twinflow",
        "dc-01",
        "receiving",
        "inbound-line-01",
        "portal-03",
        "read_rate",
    )


def test_a_topic_has_exactly_six_levels():
    assert TOPIC_LEVELS == 6
    assert len(PORTAL.levels) == TOPIC_LEVELS
    assert PORTAL.topic == PORTAL_TOPIC


def test_parse_round_trips_every_level():
    assert UnsPath.parse(CONVEYOR_TOPIC).topic == CONVEYOR_TOPIC


def test_a_published_topic_round_trips_through_the_parser():
    assert UnsPath.parse(PORTAL.topic) == PORTAL


@pytest.mark.parametrize("topic", ["a/b/c/d/e", "a/b/c/d/e/f/g"])
def test_parse_refuses_a_topic_that_is_not_six_levels(topic):
    with pytest.raises(ValueError, match="exactly 6 levels"):
        UnsPath.parse(topic)


@pytest.mark.parametrize(
    "text",
    [
        "twinflow/dc-01/receiving/inbound-line-01/portal-03",
        "twinflow/dc-01/receiving/inbound-line-01/portal-03/read_rate/extra",
        "twinflow",
        "",
    ],
)
def test_a_topic_with_the_wrong_depth_is_refused(text):
    with pytest.raises(NamingError) as caught:
        UnsPath.parse(text)
    assert caught.value.code == "TF-S005"


# ------------------------------------------------------------- the refusals


@pytest.mark.parametrize(
    "bad",
    ["", "Portal-03", "portal 03", "portal/03", "portal+03", "portal#03", "-portal", "portal_03"],
)
def test_an_identifier_level_refuses_anything_outside_lowercase_kebab_case(bad):
    """The refusal names the level and the value, whichever rule caught it."""
    with pytest.raises(ValueError) as excinfo:
        _with_equipment(bad)
    assert "equipment" in str(excinfo.value)
    assert repr(bad) in str(excinfo.value)


@pytest.mark.parametrize("bad", ["DC-01", "dc 01", "dc_01", "-dc01", "dc01-"])
def test_an_identifier_that_is_not_lowercase_kebab_case_is_refused(bad):
    with pytest.raises(NamingError) as caught:
        _with_site(bad)
    assert caught.value.code == "TF-S003"


@pytest.mark.parametrize("bad", ["", "Read_Rate", "read rate", "read-rate", "read/rate", "_rate"])
def test_a_parameter_refuses_anything_outside_snake_case(bad):
    with pytest.raises(ValueError, match="parameter"):
        _with_parameter(bad)


@pytest.mark.parametrize("bad", ["Read_Rate", "read rate", "read-rate", "1read", "read__rate"])
def test_a_parameter_that_is_not_lowercase_snake_case_is_refused(bad):
    with pytest.raises(NamingError) as caught:
        _with_parameter(bad)
    assert caught.value.code == "TF-S004"


def test_a_wildcard_never_reaches_a_published_topic():
    for wildcard in ("+", "#"):
        with pytest.raises(ValueError):
            _with_site(wildcard)


@pytest.mark.parametrize("wildcard", ["+", "#"])
def test_a_wildcard_level_is_refused_with_the_code_that_names_it(wildcard):
    with pytest.raises(NamingError) as caught:
        UnsPath(
            enterprise="twinflow",
            site="dc-01",
            area=wildcard,
            line="inbound-line-01",
            equipment="portal-03",
            parameter="read_rate",
        )
    assert caught.value.code == "TF-S002"


def test_an_empty_level_is_refused():
    with pytest.raises(NamingError) as caught:
        UnsPath.parse("twinflow/dc-01//inbound-line-01/portal-03/read_rate")
    assert caught.value.code == "TF-S001"


def test_a_level_that_is_not_a_string_names_no_level():
    """A YAML author writing `site: 01` hands this an int, not a string."""
    with pytest.raises(NamingError) as caught:
        _from_config(
            enterprise="twinflow",
            site=1,
            area="receiving",
            line="inbound-line-01",
            equipment="portal-03",
            parameter="read_rate",
        )
    assert caught.value.code == "TF-S001"


def test_a_level_ending_in_a_newline_is_refused():
    """`$` also matches before a trailing newline, and `\\Z` is why this fails.

    Both merged patterns anchored with `$`, so a level carrying a trailing
    newline passed both of them and rendered a topic with a line break inside
    it. The consolidated grammar anchors with `\\Z`, and this is the
    observation that fails if it goes back.
    """
    with pytest.raises(NamingError) as caught:
        _with_equipment("portal-03\n")
    assert caught.value.code == "TF-S003"
    with pytest.raises(NamingError) as caught:
        _with_parameter("read_rate\n")
    assert caught.value.code == "TF-S004"


def test_a_level_longer_than_the_bound_is_refused():
    """The publish side always bounded a level; the storage side never did.

    The union of two refusals is the rule, so the bound survives the merge.
    """
    with pytest.raises(NamingError) as caught:
        _with_equipment("a" * 33)
    assert caught.value.code == "TF-S003"
    with pytest.raises(NamingError) as caught:
        _with_parameter("a" * 65)
    assert caught.value.code == "TF-S004"
    assert _with_equipment("a" * 32).equipment == "a" * 32


def test_a_unit_bearing_parameter_is_a_parameter_like_any_other():
    """`motor_temp_c` is the section 5 example, and the grammar has to hold it."""
    topic = UnsPath.parse(CONVEYOR_TOPIC)
    assert topic.parameter == "motor_temp_c"


# ------------------------------------------------------- generated, not typed


def test_topics_are_built_from_a_config_mapping_rather_than_typed():
    """ARCHITECTURE section 5: topic strings are generated from config."""
    facility = {
        "enterprise": "twinflow",
        "site": "dc-01",
        "areas": [
            {
                "id": "receiving",
                "lines": [
                    {
                        "id": "inbound-line-01",
                        "equipment": [
                            {"id": "portal-03", "parameters": ["read_rate", "unique_epcs"]},
                            {"id": "conveyor-02", "parameters": ["motor_temp_c"]},
                        ],
                    }
                ],
            }
        ],
    }
    topics = [path.topic for path in UnsPath.from_facility(facility)]
    assert topics == [
        CONVEYOR_TOPIC,
        PORTAL_TOPIC,
        "twinflow/dc-01/receiving/inbound-line-01/portal-03/unique_epcs",
    ]


def test_from_facility_refuses_a_mapping_that_would_leave_a_level_empty():
    facility = {
        "enterprise": "twinflow",
        "site": "dc-01",
        "areas": [{"id": "receiving", "lines": [{"id": "", "equipment": []}]}],
    }
    with pytest.raises(NamingError, match="line"):
        list(UnsPath.from_facility(facility))


def test_a_prefix_that_is_not_the_five_identifier_levels_is_refused():
    """A device carries its own placement, so a short prefix is a wrong address."""
    with pytest.raises(NamingError) as caught:
        UnsPath.from_prefix(("twinflow", "dc-01", "receiving"), "read_rate")
    assert caught.value.code == "TF-S008"
    assert UnsPath.from_prefix(
        ("twinflow", "dc-01", "receiving", "inbound-line-01", "portal-03"), "read_rate"
    ) == UnsPath.parse(PORTAL_TOPIC)


# ------------------------------------------------------ wildcards, where legal


def test_a_subscription_is_where_a_wildcard_belongs():
    assert PORTAL.subscription(3) == "twinflow/dc-01/receiving/#"
    assert PORTAL.subscription(1) == "twinflow/#"
    assert PORTAL.subscription(6) == PORTAL.topic


@pytest.mark.parametrize("depth", [0, 7, -1])
def test_a_subscription_depth_outside_the_six_levels_is_refused(depth):
    with pytest.raises(NamingError) as caught:
        PORTAL.subscription(depth)
    assert caught.value.code == "TF-S007"


# --------------------------------------------------------------- the documents


@pytest.mark.skipif(not ARCHITECTURE.is_file(), reason="installed without the repository")
def test_the_shipped_examples_all_parse():
    """Section 5 prints concrete topics. Each one is a case this parser owes."""
    text = ARCHITECTURE.read_text(encoding="utf-8")
    examples = re.findall(r"^twinflow/[a-z0-9/_-]+$", text, flags=re.MULTILINE)

    assert len(examples) >= 7, "section 5 lists concrete topics; none were found"
    for example in examples:
        assert UnsPath.parse(example).topic == example
