"""Config loading and validation (C5), and the facility contract (A2).

A config error here is a message an author can act on: a code, the line and
column in the file they edited, and a suggestion. Gate CFG-001 asserts that
every invalid fixture produces all three.
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

#: Read by tool.hatch.version, so this is the only place the version is written.
__version__ = "0.1.0"

__all__ = [
    "FACILITY_SCHEMA",
    "ConfigError",
    "Diagnostic",
    "Severity",
    "__version__",
    "check_plausibility",
    "check_references",
    "load_facility",
    "nearest",
    "parse",
    "validate_schema",
]
