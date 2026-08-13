"""INV-K16 as a property: a cursor walk sees the log exactly once, in order.

Foundations section 5.13 states the guarantee as "paging never skips or
duplicates an item that existed when the cursor was created". That is a claim
over every page size and every log, and an example test at page size 3 proves it
for page size 3.

The generated log is not arbitrary. It obeys invariant E4 and doctrine D-07:
sequence dense per producer, no two events sharing a producer and a sequence.
Generating a log that no producer could ever emit would test the pagination of a
tape the system cannot produce.
"""

from __future__ import annotations

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from twinflow.api import Cursor, page_of
from twinflow.schemas import Envelope, in_total_order

from .conftest import make_event

pytestmark = pytest.mark.property

PRODUCERS = ("sim", "device-agent", "agent")
SUBJECTS = ("twinflow.twin.wip_sampled", "twinflow.telemetry.sensor_reading")


@st.composite
def logs(draw: st.DrawFn) -> tuple[Envelope, ...]:
    """A log obeying E4 and D-07: dense per-producer sequence, no duplicates."""
    count = draw(st.integers(min_value=0, max_value=40))
    next_seq = dict.fromkeys(PRODUCERS, 0)
    events: list[Envelope] = []
    for _ in range(count):
        producer = draw(st.sampled_from(PRODUCERS))
        sim_ts = draw(st.integers(min_value=0, max_value=12))
        subject = draw(st.sampled_from(SUBJECTS))
        events.append(
            make_event(
                producer=producer,
                sim_ts=sim_ts,
                seq=next_seq[producer],
                subject=subject,
            )
        )
        next_seq[producer] += 1
    return tuple(events)


def _walk(events: tuple[Envelope, ...], limit: int) -> list[Envelope]:
    """Page through the whole log the way a client does, cursor by cursor."""
    seen: list[Envelope] = []
    after: Cursor | None = None
    for _ in range(len(events) + 2):
        page = page_of(events, after=after, limit=limit)
        seen.extend(page.events)
        if page.next_cursor is None:
            return seen
        after = page.next_cursor
    raise AssertionError("the walk did not terminate within one page per event plus two")


@settings(max_examples=200, deadline=None)
@given(events=logs(), limit=st.integers(min_value=1, max_value=8))
def test_a_cursor_walk_visits_every_event_exactly_once_in_canonical_order(
    events: tuple[Envelope, ...], limit: int
) -> None:
    walked = _walk(events, limit)

    expected = list(in_total_order(events))
    assert [event.id for event in walked] == [event.id for event in expected]


@settings(max_examples=200, deadline=None)
@given(events=logs(), limit=st.integers(min_value=1, max_value=8))
def test_no_page_is_longer_than_the_limit_and_only_the_last_one_is_short(
    events: tuple[Envelope, ...], limit: int
) -> None:
    after: Cursor | None = None
    for _ in range(len(events) + 2):
        page = page_of(events, after=after, limit=limit)
        assert len(page.events) <= limit
        if page.next_cursor is None:
            break
        assert len(page.events) == limit, "a short page must be the last page"
        after = page.next_cursor
    else:
        raise AssertionError("the walk did not terminate; the cursor is not advancing")


@settings(max_examples=200, deadline=None)
@given(events=logs(), limit=st.integers(min_value=1, max_value=8))
def test_a_subject_filter_changes_which_events_are_seen_and_never_their_order(
    events: tuple[Envelope, ...], limit: int
) -> None:
    wanted = (SUBJECTS[0],)

    seen: list[Envelope] = []
    after: Cursor | None = None
    for _ in range(len(events) + 2):
        page = page_of(events, after=after, limit=limit, subjects=wanted)
        seen.extend(page.events)
        if page.next_cursor is None:
            break
        after = page.next_cursor
    else:
        raise AssertionError("the walk did not terminate; the cursor is not advancing")

    expected = [event for event in in_total_order(events) if event.subject in wanted]
    assert [event.id for event in seen] == [event.id for event in expected]


@settings(max_examples=200, deadline=None)
@given(events=logs(), lower=st.integers(min_value=0, max_value=12))
def test_a_sim_time_window_is_inclusive_at_both_ends(
    events: tuple[Envelope, ...], lower: int
) -> None:
    upper = lower + 3

    page = page_of(events, after=None, limit=1000, sim_ts_from=lower, sim_ts_to=upper)

    inside = [
        event for event in in_total_order(events) if lower <= int(event.twinflowsimts) <= upper
    ]
    assert [event.id for event in page.events] == [event.id for event in inside]


@settings(max_examples=200, deadline=None)
@given(events=logs())
def test_a_cursor_taken_at_one_page_size_is_honored_at_another(
    events: tuple[Envelope, ...],
) -> None:
    """A client that changes its page size mid-walk must not skip or repeat.

    An offset cursor passes every test above and fails this one, which is why
    foundations section 5.13 refuses offset pagination rather than merely
    preferring cursors.
    """
    first = page_of(events, after=None, limit=3)
    if first.next_cursor is None:
        return

    rest = page_of(events, after=first.next_cursor, limit=1000)

    expected = list(in_total_order(events))
    assert [event.id for event in first.events] + [event.id for event in rest.events] == [
        event.id for event in expected
    ]
