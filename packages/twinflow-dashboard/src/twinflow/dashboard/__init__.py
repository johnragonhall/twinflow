"""The dashboard, and the accessibility floor it is held to.

Gate VAL-GATE-A11Y-001 is the floor rather than a goal: zero critical and zero
serious axe-core violations, the demo path completable by keyboard alone, and
severity encoded by shape and text rather than by color alone.

Only three of those four clauses are checkable from a Python test tier, and
`twinflow.dashboard.accessibility` says which is which rather than leaving a
reader to assume the gate is fully covered. Doctrine D-11 makes external
evidence the thing a validation gate rests on, and a hand-written subset of axe
rules written by the same hand that wrote the markup is not that.
"""

from __future__ import annotations

from twinflow.dashboard.accessibility import (
    A11Y_GATE_ID,
    DEMO_PATH,
    FOCUS_ORDER,
    MIN_TARGET_PX,
    MOTION_TOKEN_PREFIX,
    REDUCED_MOTION_ATTRIBUTE,
    REDUCED_MOTION_QUERY,
    WCAG_REFERENCE,
    WCAG_REFERENCE_URL,
    DemoStep,
)
from twinflow.dashboard.app import (
    CSP_TEMPLATE,
    INDEX_FILENAME,
    create_app,
    index_html,
    serve,
    viewer_asset_root,
)
from twinflow.dashboard.commands import (
    COMMAND_KINDS,
    COMMAND_NAMES,
    COMMAND_PRODUCER,
    COMMAND_SUBJECT,
    SERVER_HANDLED,
    AcceptedCommand,
    CommandError,
    CommandKind,
    CommandLog,
    validate_command,
)
from twinflow.dashboard.config import DashboardConfig
from twinflow.dashboard.severity import (
    BANDED_CLASSES,
    FINDING_CLASSES,
    MIN_GLYPH_PX,
    SEVERITIES,
    SEVERITY_CHANNELS,
    SEVERITY_NAMES,
    FindingClass,
    SeverityLevel,
    finding_class_for,
    finding_sort_key,
    severity_for,
)

#: Read by tool.hatch.version, so this is the only place the version is written.
__version__ = "0.1.0"

__all__ = [
    "A11Y_GATE_ID",
    "BANDED_CLASSES",
    "COMMAND_KINDS",
    "COMMAND_NAMES",
    "COMMAND_PRODUCER",
    "COMMAND_SUBJECT",
    "CSP_TEMPLATE",
    "DEMO_PATH",
    "FINDING_CLASSES",
    "FOCUS_ORDER",
    "INDEX_FILENAME",
    "MIN_GLYPH_PX",
    "MIN_TARGET_PX",
    "MOTION_TOKEN_PREFIX",
    "REDUCED_MOTION_ATTRIBUTE",
    "REDUCED_MOTION_QUERY",
    "SERVER_HANDLED",
    "SEVERITIES",
    "SEVERITY_CHANNELS",
    "SEVERITY_NAMES",
    "WCAG_REFERENCE",
    "WCAG_REFERENCE_URL",
    "AcceptedCommand",
    "CommandError",
    "CommandKind",
    "CommandLog",
    "DashboardConfig",
    "DemoStep",
    "FindingClass",
    "SeverityLevel",
    "__version__",
    "create_app",
    "finding_class_for",
    "finding_sort_key",
    "index_html",
    "serve",
    "severity_for",
    "validate_command",
    "viewer_asset_root",
]
