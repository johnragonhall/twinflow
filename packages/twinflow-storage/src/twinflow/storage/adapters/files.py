"""A sealed run, written to a directory and read back into a `Historian`.

Requirement E4a asks for an append-only log with a per-run config snapshot. The
log existed and lived in memory, so every run died with the process that made
it and `twinflow-api` had nothing to serve. This module is the read-back half.

THE LAYOUT, AND WHY IT IS FOUR FILES RATHER THAN ONE

    <root>/<run_id>/snapshot.json     the hashed core of doctrine D-01
    <root>/<run_id>/events.jsonl      the log, canonical, in appended order
    <root>/<run_id>/arrivals.jsonl    when each event reached the historian
    <root>/<run_id>/provenance.json   the sidecar: wall time, host, hash, count

The split is doctrine D-01 on disk. `events.jsonl` carries the bytes the log
hash covers and nothing else, so a reader can hash the file and get the number
the sidecar claims. Folding the arrival instants or the host into it would put
machine identity inside the hashed material, which is the exact failure D-01
ruled on.

Arrivals are separate rather than absent because they are not derivable. Sim
time is when a reading happened and arrival is when it reached the historian,
and `backfilled()` is the difference between the two. A read-back that let the
replay clock stamp fresh arrivals would report every buffered reading as having
arrived on time, turning a recorded site-link outage into a clean run.

WHAT READING VERIFIES

Both hashes, every time. The log is re-hashed after replay and compared to the
sidecar, and the snapshot is re-hashed and compared to its own. A run directory
that has been edited, truncated, or half-written fails to load rather than
serving a log whose hash nobody checked. `twinflow-api` publishes `log_hash` on
its runs route, and a number served from a file rather than from the events
underneath it is a number that means nothing.
"""

from __future__ import annotations

import dataclasses
import json
from collections.abc import Iterator, Mapping
from datetime import datetime
from pathlib import Path

from twinflow.kernel import SimClock, SimInstant
from twinflow.schemas import Envelope
from twinflow.storage.historian import ConfigSnapshot, Historian, SnapshotProvenance

#: The four names inside a run directory. Constants rather than literals at the
#: call sites, so a reader grepping for the layout finds one place.
SNAPSHOT_FILE = "snapshot.json"
EVENTS_FILE = "events.jsonl"
ARRIVALS_FILE = "arrivals.jsonl"
PROVENANCE_FILE = "provenance.json"


class ArchiveError(RuntimeError):
    """A run directory that cannot be trusted to be the run it claims to be."""


def _canonical(payload: Mapping[str, object]) -> str:
    """Sorted keys and tight separators, so the bytes are a function of values.

    The same rule `log_hash` and `snapshot_hash` follow, and the same one
    `twinflow.kernel.__main__` writes its log with. A formatting change is not
    a change of inputs and must not read as one.
    """
    return json.dumps(payload, sort_keys=True, separators=(",", ":"))


def write_run(historian: Historian, provenance: SnapshotProvenance, root: Path) -> Path:
    """Write one sealed run under `root`, returning its directory.

    The historian is required to be sealed. An unsealed run is still being
    appended to, and its sidecar would record a hash and a count that the next
    append invalidates, which is the failure `seal` exists to prevent.
    """
    if not historian.sealed:
        raise ArchiveError(
            f"run {historian.snapshot.run_id} is not sealed. Its hash and event count "
            f"are still moving, and a sidecar written now would describe a log that no "
            f"longer exists by the time anybody reads it"
        )
    if provenance.run_id != historian.snapshot.run_id:
        raise ArchiveError(
            f"the sidecar names run {provenance.run_id!r} and the historian records "
            f"{historian.snapshot.run_id!r}"
        )

    directory = root / historian.snapshot.run_id
    directory.mkdir(parents=True, exist_ok=True)

    (directory / SNAPSHOT_FILE).write_text(
        _canonical(historian.snapshot.payload()), encoding="utf-8"
    )

    events = historian.events()
    (directory / EVENTS_FILE).write_text(
        "".join(
            f"{_canonical(event.model_dump(mode='json', exclude_none=True))}\n" for event in events
        ),
        encoding="utf-8",
    )
    (directory / ARRIVALS_FILE).write_text(
        "".join(
            f"{_canonical({'id': event.id, 'at': int(historian.received_at(event.id))})}\n"
            for event in events
        ),
        encoding="utf-8",
    )

    sidecar = dataclasses.asdict(provenance)
    sidecar["packages"] = [list(pair) for pair in provenance.packages]
    for field in ("started_wall_utc", "finished_wall_utc"):
        value = sidecar[field]
        sidecar[field] = value.isoformat() if isinstance(value, datetime) else None
    (directory / PROVENANCE_FILE).write_text(_canonical(sidecar), encoding="utf-8")

    return directory


def read_run(directory: Path) -> Historian:
    """Read one run directory back into a sealed `Historian`.

    The clock is built here rather than taken as an argument, and it is driven
    to each event's recorded arrival before that event is appended. That is what
    reproduces `received_at` and therefore `backfilled`. A caller's clock would
    have to be rewound to the start of the run to do the same job, and a clock
    that runs backwards is the thing `SimClock` refuses.
    """
    for name in (SNAPSHOT_FILE, EVENTS_FILE, ARRIVALS_FILE, PROVENANCE_FILE):
        if not (directory / name).exists():
            raise ArchiveError(
                f"{directory} carries no {name}. A run directory is the four files "
                f"together, and a partial one is a half-written run rather than a short one"
            )

    snapshot = ConfigSnapshot(**json.loads((directory / SNAPSHOT_FILE).read_text(encoding="utf-8")))
    sidecar = json.loads((directory / PROVENANCE_FILE).read_text(encoding="utf-8"))

    events = [Envelope.model_validate(json.loads(line)) for line in _lines(directory / EVENTS_FILE)]
    arrivals = {
        record["id"]: int(record["at"])
        for record in (json.loads(line) for line in _lines(directory / ARRIVALS_FILE))
    }

    missing = [event.id for event in events if event.id not in arrivals]
    if missing:
        raise ArchiveError(
            f"{directory} records no arrival for {len(missing)} events, the first being "
            f"{missing[0]!r}. Sim time and arrival time are different facts, and inventing "
            f"the second would report a buffered reading as having arrived on time"
        )

    clock = SimClock(tick_hz=snapshot.tick_hz)
    historian = Historian(clock=clock, snapshot=snapshot)
    for event in events:
        clock.advance_to(SimInstant(arrivals[event.id]))
        historian.append(event)

    historian.seal(
        started_wall_utc=_instant(sidecar.get("started_wall_utc")),
        finished_wall_utc=_instant(sidecar.get("finished_wall_utc")),
        host=str(sidecar.get("host", "")),
        packages=dict(tuple(pair) for pair in sidecar.get("packages", ())),
    )

    _verify(directory, historian, sidecar)
    return historian


def discover_runs(root: Path) -> dict[str, Historian]:
    """Every run directory under `root`, keyed by run id.

    A root that does not exist is an empty mapping rather than an error: an
    `api` container starting before anything has been recorded is the ordinary
    first run of the tier, and `/readyz` is what reports it.

    Directories are read in sorted order, per doctrine D-03, so two processes
    over one root build the same mapping in the same order.
    """
    if not root.is_dir():
        return {}
    return {
        directory.name: read_run(directory)
        for directory in sorted(root.iterdir())
        if directory.is_dir()
    }


def _lines(path: Path) -> Iterator[str]:
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            yield line


def _instant(value: object) -> datetime | None:
    return datetime.fromisoformat(value) if isinstance(value, str) else None


def _verify(directory: Path, historian: Historian, sidecar: Mapping[str, object]) -> None:
    """Both hashes and the count, against what the sidecar claims.

    Checked after the replay rather than over the file bytes, because what
    matters is that the events this historian now holds are the events whose
    hash was recorded. A file-level check would pass on a log that failed to
    parse back into the same envelopes.
    """
    recorded_hash = sidecar.get("event_log_hash")
    if recorded_hash is not None and historian.hash() != recorded_hash:
        raise ArchiveError(
            f"{directory} replays to log hash {historian.hash()} and its sidecar records "
            f"{recorded_hash}. The run has been edited or truncated, and serving it would "
            f"publish a hash that describes a log nobody has"
        )

    recorded_count = sidecar.get("event_count")
    if isinstance(recorded_count, int) and len(historian) != recorded_count:
        raise ArchiveError(
            f"{directory} replays {len(historian)} events and its sidecar records {recorded_count}"
        )

    snapshot_file = json.loads((directory / SNAPSHOT_FILE).read_text(encoding="utf-8"))
    if snapshot_file != historian.snapshot.payload():
        raise ArchiveError(f"{directory} carries a snapshot that does not round-trip")
