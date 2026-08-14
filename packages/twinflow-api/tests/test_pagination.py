"""`page_of` called as a library function, which is where its refusals live.

The route declares `limit` as `Query(ge=1, le=MAX_PAGE_SIZE)`, so FastAPI
answers 422 before a bad value reaches this function and no request can exercise
the check inside it. That check is not redundant: `twinflow.api.page_of` is a
published name, the dashboard's server-side paging and any batch reader call it
with no HTTP hop in between, and a caller that reaches it directly has nothing
in front of it. So the range is asserted against the function.

`test_pagination_properties.py` holds the INV-K16 walk over generated logs. This
file holds the boundaries, which a property test spanning valid limits by
construction never visits.
"""

from __future__ import annotations

import pytest

from twinflow.api import MAX_PAGE_SIZE, page_of

from .conftest import TAPE, build_historian


@pytest.mark.parametrize("limit", [0, -1, MAX_PAGE_SIZE + 1])
def test_a_limit_outside_the_declared_range_is_refused_by_the_library_call(limit: int):
    """A limit of zero pages forever and a limit past the ceiling is the
    unbounded read the ceiling exists to prevent. Neither is a page."""
    events = build_historian().events()

    with pytest.raises(ValueError, match="limit must be between"):
        page_of(events, limit=limit)


def test_both_ends_of_the_declared_range_are_served():
    """The control. A check that refused every limit would satisfy the test
    above and page nothing at all."""
    events = build_historian().events()

    assert len(page_of(events, limit=1).events) == 1
    assert len(page_of(events, limit=MAX_PAGE_SIZE).events) == len(TAPE)
