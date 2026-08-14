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
import json

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

    # Read back as JSON rather than searched for substrings. "10" and "7" both
    # appear in the encoding of a cursor that swapped sim_ts and seq, so a
    # containment check cannot tell that cursor from this one.
    assert json.loads(raw) == {"p": "device-agent", "s": 7, "t": 10}


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
        # Refused by the JSON step rather than the base64 one: the decoder
        # discards characters outside the alphabet, so "!!" is dropped and what
        # is left decodes to bytes that are not JSON.
        "not-base64-!!",
        base64.urlsafe_b64encode(b"[]").decode("ascii"),
        base64.urlsafe_b64encode(b'{"t":1,"p":"sim"}').decode("ascii"),
        base64.urlsafe_b64encode(b'{"t":-1,"p":"sim","s":0}').decode("ascii"),
        # A negative sequence, which is the other half of the counter guard. The
        # row above it only exercises the sim instant.
        base64.urlsafe_b64encode(b'{"t":0,"p":"sim","s":-1}').decode("ascii"),
        base64.urlsafe_b64encode(b'{"t":1,"p":"nobody","s":0}').decode("ascii"),
        # A JSON `true`. bool subclasses int, so a plain isinstance check admits
        # it and it then compares as the sequence 1: the trap cursor.py names.
        base64.urlsafe_b64encode(b'{"p":"sim","s":true,"t":0}').decode("ascii"),
        # The counters as text. A cursor carrying "0" sorts against integers by
        # raising, not by comparing, so this has to be refused before it is used.
        base64.urlsafe_b64encode(b'{"p":"sim","s":"0","t":0}').decode("ascii"),
    ],
)
def test_a_cursor_that_did_not_come_from_this_server_is_refused(text: str):
    """A refused cursor is a 400, and a silently accepted one is a wrong page."""
    with pytest.raises(CursorError):
        decode_cursor(text)


@pytest.mark.parametrize("text", ["a!!!", "café"])
def test_a_token_that_is_not_base64url_is_refused_at_the_decoding_step(text: str):
    """The base64 step, reached and named.

    Reaching it takes more than punctuation: `urlsafe_b64decode` discards
    characters outside the alphabet, so most junk arrives at the JSON step
    instead. What reaches this step is a token whose alphabet characters cannot
    form whole base64 quanta, and one carrying a byte outside ASCII.

    The message is asserted because the refusal is what the branch is for. A
    decoder that swallowed the failure and carried on with a substitute payload
    would still refuse these two, one step later and for the wrong reason.
    """
    with pytest.raises(CursorError, match="is not base64url"):
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
