"""The naming properties, over generated names rather than chosen ones.

A round trip that holds for the seven topics printed in ARCHITECTURE.md
section 5 tells you those seven were typed correctly. It does not tell you the
grammar is a grammar. These say it over anything the rules admit, and over
anything they refuse.

They moved here with the grammar they cover. They were written against the
storage copy of the six-level rules, and a property that only ever ran against
one of two copies is a property that could not have caught the two disagreeing.
"""

from __future__ import annotations

import pytest
from hypothesis import assume, given, settings
from hypothesis import strategies as st

from twinflow.config import NamingError, UnsPath

pytestmark = pytest.mark.property

LOWER = "abcdefghijklmnopqrstuvwxyz"
ALNUM = LOWER + "0123456789"

#: Lowercase kebab-case, which is the first five levels.
identifiers = st.lists(st.text(alphabet=ALNUM, min_size=1, max_size=6), min_size=1, max_size=3).map(
    "-".join
)

#: Lowercase snake_case starting with a letter, which is the sixth level.
parameters = st.builds(
    lambda head, tail: "_".join([head, *tail]) if tail else head,
    st.text(alphabet=LOWER, min_size=1, max_size=1).flatmap(
        lambda first: st.text(alphabet=ALNUM, min_size=0, max_size=6).map(lambda rest: first + rest)
    ),
    st.lists(st.text(alphabet=ALNUM, min_size=1, max_size=6), min_size=0, max_size=2),
)

topics = st.builds(
    UnsPath,
    enterprise=identifiers,
    site=identifiers,
    area=identifiers,
    line=identifiers,
    equipment=identifiers,
    parameter=parameters,
)

#: Anything at all, which is what a topic level meets in the wild.
anything = st.text(min_size=0, max_size=12)


@settings(max_examples=200, deadline=None)
@given(topic=topics)
def test_a_generated_topic_always_round_trips(topic):
    assert UnsPath.parse(topic.topic) == topic


@settings(max_examples=200, deadline=None)
@given(topic=topics)
def test_a_generated_topic_carries_no_separator_inside_a_level(topic):
    assert topic.topic.count("/") == 5


@settings(max_examples=200, deadline=None)
@given(bad=anything)
def test_an_identifier_outside_the_grammar_is_always_refused(bad):
    assume(not UnsPath.is_identifier(bad))
    with pytest.raises(NamingError):
        UnsPath(
            enterprise="twinflow",
            site=bad,
            area="receiving",
            line="inbound-line-01",
            equipment="portal-03",
            parameter="read_rate",
        )


@settings(max_examples=200, deadline=None)
@given(bad=anything)
def test_a_parameter_outside_the_grammar_is_always_refused(bad):
    assume(not UnsPath.is_parameter(bad))
    with pytest.raises(NamingError):
        UnsPath(
            enterprise="twinflow",
            site="dc-01",
            area="receiving",
            line="inbound-line-01",
            equipment="portal-03",
            parameter=bad,
        )


@settings(max_examples=200, deadline=None)
@given(topic=topics, depth=st.integers(min_value=1, max_value=6))
def test_a_subscription_prefix_always_matches_the_topic_it_came_from(topic, depth):
    subscription = topic.subscription(depth)
    if depth == 6:
        assert subscription == topic.topic
    else:
        assert subscription.endswith("/#")
        assert topic.topic.startswith(subscription[:-1])
