"""The pagination cursor: the canonical total order, and nothing else.

Foundations section 5.13 makes the cursor an opaque base64 of
`(twinflowsimts, twinflowproducerid, twinflowseq)`, which is the total order of
invariant E4. All three components are present because doctrine D-07 makes the
sequence dense only per producer: a cursor of `(sim_ts, seq)` cannot separate two
producers that emitted at the same tick, so it either skips one of them or
serves it twice, and which one depends on dictionary order.

Opaque is a promise to the client, not to this module. The encoding is base64url
of canonical JSON so that a cursor is stable across processes and across
releases: a pickled tuple or a `repr` would change shape under a Python upgrade
and silently invalidate every cursor a client had stored.
"""

from __future__ import annotations

import base64
import binascii
import json
from dataclasses import dataclass

from twinflow.schemas import PRODUCER_IDS, Envelope, canonical_json


class CursorError(ValueError):
    """A cursor this server did not mint, or one it can no longer read.

    Refusing is the only safe answer. A malformed cursor treated as "start from
    the beginning" hands a client the first page while it believes it received
    the fourth, and the duplicate rows look like a producer defect.
    """


@dataclass(frozen=True, order=False)
class Cursor:
    """One position in the canonical replay order of one log."""

    sim_ts: int
    producer_id: str
    seq: int

    def __post_init__(self) -> None:
        if self.sim_ts < 0:
            raise CursorError(f"a sim instant is never negative, got {self.sim_ts}")
        if self.seq < 0:
            raise CursorError(f"a sequence is never negative, got {self.seq}")
        if self.producer_id not in PRODUCER_IDS:
            raise CursorError(
                f"producer {self.producer_id!r} is not one of the roles invariant E3 allows "
                f"to publish: {', '.join(sorted(PRODUCER_IDS))}"
            )

    @classmethod
    def from_event(cls, event: Envelope) -> Cursor:
        return cls(
            sim_ts=int(event.twinflowsimts),
            producer_id=event.twinflowproducerid,
            seq=int(event.twinflowseq),
        )

    def key(self) -> tuple[int, bytes, int]:
        """The same key `Envelope.total_order_key` returns, built from a cursor.

        The producer is compared as bytes because invariant E4 compares it that
        way. Comparing it as text here and as bytes there would put two orders
        in one system, and they agree on ASCII and part company on anything
        else.
        """
        return (self.sim_ts, self.producer_id.encode("utf-8"), self.seq)


def encode_cursor(cursor: Cursor) -> str:
    """Base64url of canonical JSON, unpadded.

    Sorted keys and no separator whitespace, so one position has exactly one
    encoding. Two spellings of one cursor would defeat any client that used it
    as a cache key. The padding is stripped because `=` is legal in a query
    string but survives a round trip through too few proxies to be worth it.
    """
    payload = canonical_json({"p": cursor.producer_id, "s": cursor.seq, "t": cursor.sim_ts})
    return base64.urlsafe_b64encode(payload.encode("utf-8")).decode("ascii").rstrip("=")


def decode_cursor(text: str) -> Cursor:
    """Read a cursor back, or refuse it.

    Every failure below is the same answer to the client, a `TF-A043`, because
    telling a caller which part of an opaque token was wrong invites it to
    construct one, and a client-built cursor is a client that has taken a
    dependency on an encoding this module is free to change.
    """
    if not text:
        raise CursorError("an empty cursor is not a position")
    padded = text + "=" * (-len(text) % 4)
    try:
        raw = base64.urlsafe_b64decode(padded.encode("ascii"))
    except (binascii.Error, UnicodeEncodeError, ValueError) as exc:
        raise CursorError(f"cursor {text!r} is not base64url") from exc
    try:
        payload = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise CursorError(f"cursor {text!r} does not decode to JSON") from exc
    if not isinstance(payload, dict) or set(payload) != {"p", "s", "t"}:
        raise CursorError(f"cursor {text!r} does not carry exactly the three parts of the key")
    # `bool` is a subclass of `int`, so a JSON `true` would pass an isinstance
    # check for the sequence and then compare as 1. Excluding it explicitly is
    # the difference between refusing that cursor and serving the wrong page.
    counters = (payload["s"], payload["t"])
    well_typed = isinstance(payload["p"], str) and all(
        isinstance(value, int) and not isinstance(value, bool) for value in counters
    )
    if not well_typed:
        raise CursorError(f"cursor {text!r} carries the wrong types")
    return Cursor(sim_ts=payload["t"], producer_id=payload["p"], seq=payload["s"])
