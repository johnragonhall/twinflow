"""Cursor pagination over a log, which is invariant INV-K16 as code.

Foundations section 5.13: "Because the event log is append-only and read in that
order, paging never skips or duplicates an item that existed when the cursor was
created." That property is not a consequence of the HTTP layer. It is a
consequence of two decisions made here, and both are the kind that look like
style until a client loses a row.

First, the page is cut by comparing keys rather than by counting rows. An offset
into a filtered list is a different row every time the filter changes, and a
client that widens its page size mid-walk with an offset cursor re-reads or skips
exactly the difference.

Second, ordering happens before the cut and never after. Sorting a page rather
than the log gives a body that looks ordered and a walk that is not.
"""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from dataclasses import dataclass

from twinflow.api.cursor import Cursor
from twinflow.schemas import Envelope, in_total_order

#: The page size ceiling. Chosen here rather than taken from a source: it is the
#: point past which a single response stops fitting a dashboard's first paint,
#: and it is a config knob the moment anyone measures a better one.
MAX_PAGE_SIZE = 10_000

DEFAULT_PAGE_SIZE = 100


@dataclass(frozen=True)
class EventPage:
    """One page, plus the position a client resumes from.

    `next_cursor` is `None` exactly when the log is exhausted, and never merely
    because the page came back short. A short page with a cursor would loop a
    client forever; a full page with no cursor would truncate the walk with
    nothing failing.
    """

    events: tuple[Envelope, ...]
    next_cursor: Cursor | None


def page_of(
    events: Iterable[Envelope],
    *,
    after: Cursor | None = None,
    limit: int = DEFAULT_PAGE_SIZE,
    subjects: Sequence[str] | None = None,
    sim_ts_from: int | None = None,
    sim_ts_to: int | None = None,
) -> EventPage:
    """One page of the log, in the canonical order, strictly after `after`.

    Both sim-time bounds are inclusive, matching `Historian.read`, because a
    reader asking for "the window around instant 40" writes the same two numbers
    they read off a chart and would otherwise lose the events at the edges.
    """
    if limit < 1 or limit > MAX_PAGE_SIZE:
        raise ValueError(f"limit must be between 1 and {MAX_PAGE_SIZE}, got {limit}")

    wanted = None if subjects is None else frozenset(subjects)
    selected = [
        event
        for event in in_total_order(events)
        if (wanted is None or event.subject in wanted)
        and (sim_ts_from is None or int(event.twinflowsimts) >= sim_ts_from)
        and (sim_ts_to is None or int(event.twinflowsimts) <= sim_ts_to)
    ]

    if after is not None:
        boundary = after.key()
        selected = [event for event in selected if Envelope.total_order_key(event) > boundary]

    page = tuple(selected[:limit])
    exhausted = len(selected) <= limit
    return EventPage(
        events=page,
        next_cursor=None if exhausted or not page else Cursor.from_event(page[-1]),
    )
