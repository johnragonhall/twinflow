"""Event envelope and shared value types.

This package is a leaf. It imports nothing from the workspace, which is what
lets a consumer install one brick without pulling the rest.
"""

from __future__ import annotations

from twinflow.schemas.compat import OPEN_ENUM, OPEN_RANGE, compare_schemas
from twinflow.schemas.envelope import (
    MAX_ATTRIBUTE_NAME_LENGTH,
    PRODUCER_IDS,
    DecimalString,
    Envelope,
    ProducerId,
    SourceUri,
)

#: Read by tool.hatch.version, so this is the only place the version is written.
__version__ = "0.1.0"

__all__ = [
    "MAX_ATTRIBUTE_NAME_LENGTH",
    "OPEN_ENUM",
    "OPEN_RANGE",
    "PRODUCER_IDS",
    "DecimalString",
    "Envelope",
    "ProducerId",
    "SourceUri",
    "__version__",
    "compare_schemas",
]
