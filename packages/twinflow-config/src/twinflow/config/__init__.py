"""Config loading and validation (C5), the facility contract (A2), and the UNS.

A config error here is a message an author can act on: a code, the line and
column in the file they edited, and a suggestion. Gate CFG-001 asserts that
every invalid fixture produces all three.

The unified namespace grammar of ARCHITECTURE.md section 5 lives here too,
because that section makes the namespace "a projection of the facility model,
not a parallel truth" and this package owns the facility model. Both renderers
sit above this layer and import the grammar: twinflow.sensors publishes on it
and twinflow.storage stores under it. Neither owns a second spelling of it.
"""

from __future__ import annotations

from twinflow.config._impl.errors import Diagnostic, Severity, nearest
from twinflow.config._impl.loader import (
    FACILITY_SCHEMA,
    ConfigError,
    check_plausibility,
    check_references,
    load_facility,
    parse,
    validate_schema,
)
from twinflow.config._impl.metrics import (
    METRIC_ID,
    METRICS_SCHEMA,
    check_metric_rules,
    load_metrics,
    resolve_spec_limits,
)
from twinflow.config._impl.uns import (
    IDENTIFIER,
    LEVEL_NAMES,
    PARAMETER,
    TOPIC_LEVELS,
    TOPIC_SEPARATOR,
    WILDCARDS,
    NamingError,
    UnsPath,
)

#: Read by tool.hatch.version, so this is the only place the version is written.
__version__ = "0.1.0"

__all__ = [
    "FACILITY_SCHEMA",
    "IDENTIFIER",
    "LEVEL_NAMES",
    "METRICS_SCHEMA",
    "METRIC_ID",
    "PARAMETER",
    "TOPIC_LEVELS",
    "TOPIC_SEPARATOR",
    "WILDCARDS",
    "ConfigError",
    "Diagnostic",
    "NamingError",
    "Severity",
    "UnsPath",
    "__version__",
    "check_metric_rules",
    "check_plausibility",
    "check_references",
    "load_facility",
    "load_metrics",
    "nearest",
    "parse",
    "resolve_spec_limits",
    "validate_schema",
]
