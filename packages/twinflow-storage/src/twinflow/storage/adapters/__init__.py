"""Storage adapters: the implementations that touch a filesystem.

`docs/design/foundations.md` declares this path in `adapter_paths` with the
reason "storage adapters", which exempts it from the determinism lint. The
directory is its own package for that reason: a path, a directory listing, and
an `open` are legal here and are the kind of thing the lint is watching for one
level up.

`files` is the whole surface at P1. It writes a sealed run to a directory and
reads it back, which is what turns `Historian` from an object that dies with its
process into a record `twinflow-api` can serve. The Delta table of decision D2
sits behind the `delta` extra and arrives with the phase that queries it; a run
directory of JSON Lines is what a five-minute quickstart can afford to read.
"""

from __future__ import annotations

from twinflow.storage.adapters.files import (
    ARRIVALS_FILE,
    EVENTS_FILE,
    PROVENANCE_FILE,
    SNAPSHOT_FILE,
    ArchiveError,
    discover_runs,
    read_run,
    write_run,
)

__all__ = [
    "ARRIVALS_FILE",
    "EVENTS_FILE",
    "PROVENANCE_FILE",
    "SNAPSHOT_FILE",
    "ArchiveError",
    "discover_runs",
    "read_run",
    "write_run",
]
