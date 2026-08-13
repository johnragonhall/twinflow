"""The REST surface the dashboard reads through.

One contract, versioned with the event schemas it carries, so the dashboard and
any other reader see the same shapes. The compatibility table C6 records which
recorded runs and configs a release still loads.

Requirement R32 is why this package exists before the dashboard needs it:
building the dashboard against internal calls and inserting an API later
rewrites every dashboard test. `twinflow.dashboard` therefore reads this surface
over HTTP and never imports it, and boundary rule A1.2 is what holds the two
apart rather than a review convention.
"""

from __future__ import annotations

from twinflow.api.app import (
    API_PREFIX,
    APPLY_TIER,
    CONFIG_APPLY_TOOL,
    NOT_INSTALLED,
    UNVERSIONED_PATHS,
    ConfigProposal,
    create_api,
    openapi_document,
)
from twinflow.api.cursor import Cursor, CursorError, decode_cursor, encode_cursor
from twinflow.api.metrics import (
    EXPRESSION_REQUIREMENT,
    MetricDefinition,
    MetricRegistry,
)
from twinflow.api.pagination import (
    DEFAULT_PAGE_SIZE,
    MAX_PAGE_SIZE,
    EventPage,
    page_of,
)
from twinflow.api.problems import (
    DEFAULT_PROBLEM_BASE_URL,
    PROBLEM_MEDIA_TYPE,
    PROBLEMS,
    Problem,
    ProblemError,
    problem_document,
)

#: Read by tool.hatch.version, so this is the only place the version is written.
__version__ = "0.1.0"

__all__ = [
    "API_PREFIX",
    "APPLY_TIER",
    "CONFIG_APPLY_TOOL",
    "DEFAULT_PAGE_SIZE",
    "DEFAULT_PROBLEM_BASE_URL",
    "EXPRESSION_REQUIREMENT",
    "MAX_PAGE_SIZE",
    "NOT_INSTALLED",
    "PROBLEMS",
    "PROBLEM_MEDIA_TYPE",
    "UNVERSIONED_PATHS",
    "ConfigProposal",
    "Cursor",
    "CursorError",
    "EventPage",
    "MetricDefinition",
    "MetricRegistry",
    "Problem",
    "ProblemError",
    "__version__",
    "create_api",
    "decode_cursor",
    "encode_cursor",
    "openapi_document",
    "page_of",
    "problem_document",
]
