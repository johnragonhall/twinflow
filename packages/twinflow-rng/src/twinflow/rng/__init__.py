"""The one place a bit generator is constructed."""

from __future__ import annotations

from twinflow.rng.derive import derive_spawn_key, generator_for
from twinflow.rng.registry import STREAM_COUNT_CEILING, StreamRegistry

#: Read by tool.hatch.version, so this is the only place the version is written.
__version__ = "0.1.0"

#: Bumped when the stream catalog gains, loses, or renames a stream. A recorded
#: run carries this, so a replay can refuse a corpus it cannot reproduce.
STREAM_CATALOG_VERSION = "0.1.0"

__all__ = [
    "STREAM_CATALOG_VERSION",
    "STREAM_COUNT_CEILING",
    "StreamRegistry",
    "__version__",
    "derive_spawn_key",
    "generator_for",
]
