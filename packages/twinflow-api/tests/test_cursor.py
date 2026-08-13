"""The cursor is the whole of the pagination promise, so it is tested alone.

Foundations section 5.13 says the cursor is an opaque base64 of
`(twinflowsimts, twinflowproducerid, twinflowseq)`, the canonical total order of
invariant E4 and no other order, and that paging never skips or duplicates an
item that existed when the cursor was created (INV-K16).

Three components rather than two, because doctrine D-07 makes the sequence dense
only per producer. The tape in conftest has two producers emitting at the same
sim instant, which is the shape that tells a correct cursor from one that
dropped the producer component.
"""

from __future__ import annotations

import base64

import pytest

from twinflow.api import Cursor, CursorError, decode_cursor, encode_cursor

from .conftest import TAPE, build_historian


def test_a_cursor_round_trips_through_its_opaque_encoding():
    cursor = Cursor(sim_ts=10, producer_id="device-agent", seq=7)

    assert decode_cursor(encode_cursor(cursor)) == cursor


def test_the_encoding_is_base64_and_carries_all_three_components():
    """Opaque to a client, but it has to actually hold the whole key.

    Decoding it here is not a client's job. It is how this test tells a cursor
    that carries the key from one that carries a list index.
    """
    cursor = Cursor(sim_ts=10, producer_id="device-agent", seq=7)

    raw = base64.urlsafe_b64decode(encode_cursor(cursor) + "==").decode("utf-8")

    assert "10" in raw
    assert "device-agent" in raw
    assert "7" in raw


def test_two_events_at_one_instant_from_two_producers_get_different_cursors():
    events = build_historian().replay()
    at_ten = [event for event in events if int(event.twinflowsimts) == 10]
    assert len({event.twinflowproducerid for event in at_ten}) == 2

    encoded = {encode_cursor(Cursor.from_event(event)) for event in at_ten}

    assert len(encoded) == len(at_ten)


def test_the_cursor_sorts_the_way_the_envelope_says_the_log_replays():
    events = build_historian().replay()

    from_cursor = [Cursor.from_event(event).key() for event in events]
    from_envelope = [type(event).total_order_key(event) for event in events]

    assert from_cursor == from_envelope


def test_a_seq_of_ten_sorts_after_a_seq_of_two():
    """The decimal fields are strings on the envelope, and "10" < "2" as text."""
    two = Cursor(sim_ts=0, producer_id="sim", seq=2)
    ten = Cursor(sim_ts=0, producer_id="sim", seq=10)

    assert two.key() < ten.key()


@pytest.mark.parametrize(
    "text",
    [
        "",
        "not-base64-!!",
        base64.urlsafe_b64encode(b"[]").decode("ascii"),
        base64.urlsafe_b64encode(b'{"t":1,"p":"sim"}').decode("ascii"),
        base64.urlsafe_b64encode(b'{"t":-1,"p":"sim","s":0}').decode("ascii"),
        base64.urlsafe_b64encode(b'{"t":1,"p":"nobody","s":0}').decode("ascii"),
    ],
)
def test_a_cursor_that_did_not_come_from_this_server_is_refused(text: str):
    """A refused cursor is a 400, and a silently accepted one is a wrong page."""
    with pytest.raises(CursorError):
        decode_cursor(text)


def test_the_producer_component_is_checked_against_the_closed_set():
    """Invariant E3 closes the producer set, so a cursor naming a role that
    cannot publish was not minted here and must not be honored."""
    forged = base64.urlsafe_b64encode(b'{"p":"attacker","s":0,"t":0}').decode("ascii").rstrip("=")

    with pytest.raises(CursorError):
        decode_cursor(forged)


def test_every_event_in_the_tape_gets_a_distinct_cursor():
    events = build_historian().replay()
    assert len(events) == len(TAPE)

    assert len({encode_cursor(Cursor.from_event(event)) for event in events}) == len(TAPE)
