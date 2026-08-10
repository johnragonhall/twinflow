"""Event envelope and shared value types.

This package is a leaf. It imports nothing from the workspace, which is what
lets a consumer install one brick without pulling the rest.
"""

from __future__ import annotations

from twinflow.schemas.envelope import (
    MAX_ATTRIBUTE_NAME_LENGTH,
    PRODUCER_IDS,
    DecimalString,
    Envelope,
)

#: Read by tool.hatch.version, so this is the only place the version is written.
__version__ = "0.1.0"

__all__ = [
    "MAX_ATTRIBUTE_NAME_LENGTH",
    "PRODUCER_IDS",
    "DecimalString",
    "Envelope",
    "__version__",
]
