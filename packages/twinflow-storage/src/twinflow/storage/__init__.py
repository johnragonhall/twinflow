"""The append-only historian, and the naming that makes it the L2 record.

WP-P1-05 names the historian and fixes its place in the Purdue layer map;
WP-P1-06 records the event log with a per-run config snapshot, which is what
lets a run be replayed rather than described.
"""

from __future__ import annotations

from twinflow.storage.adapters import (
    ARRIVALS_FILE,
    EVENTS_FILE,
    PROVENANCE_FILE,
    SNAPSHOT_FILE,
    ArchiveError,
    discover_runs,
    read_run,
    write_run,
)
from twinflow.storage.historian import (
    EVENT_TABLE,
    PROVENANCE_MARKERS,
    STORED_BYTES_MEASURED_ON,
    STORED_BYTES_METRIC,
    STORED_BYTES_PER_READING,
    Column,
    ConfigSnapshot,
    Historian,
    HistorianError,
    SnapshotProvenance,
    TableFormat,
    provenance_leaks,
    rows_for,
)

# The UNS grammar is not on this surface and is not re-exported either.
# `UnsPath`, `NamingError`, and the level constants are owned by twinflow.config,
# which owns the facility model the namespace projects, and boundary rule A1.4
# gives a public symbol exactly one owning package. A caller building a topic
# imports it from there and hands it to `series_for`, so there is one spelling
# of a series name in the workspace rather than one per consumer.
from twinflow.storage.naming import (
    HISTORIAN,
    PURDUE_LEVELS,
    LayerPlacement,
    SeriesName,
    series_for,
)

#: Read by tool.hatch.version, so this is the only place the version is written.
__version__ = "0.1.0"

__all__ = [
    "ARRIVALS_FILE",
    "ArchiveError",
    "Column",
    "ConfigSnapshot",
    "EVENTS_FILE",
    "EVENT_TABLE",
    "HISTORIAN",
    "Historian",
    "HistorianError",
    "LayerPlacement",
    "PROVENANCE_FILE",
    "PROVENANCE_MARKERS",
    "PURDUE_LEVELS",
    "SNAPSHOT_FILE",
    "STORED_BYTES_MEASURED_ON",
    "STORED_BYTES_METRIC",
    "STORED_BYTES_PER_READING",
    "SeriesName",
    "SnapshotProvenance",
    "TableFormat",
    "__version__",
    "discover_runs",
    "provenance_leaks",
    "read_run",
    "rows_for",
    "series_for",
    "write_run",
]
