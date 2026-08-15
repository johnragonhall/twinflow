"""The append-only event log, the run's config snapshot, and the batch table.

Requirement E4a. Three contracts live here because they are one mechanism:
a run is replayable when its log is complete and ordered, when the inputs that
produced it are recorded beside it, and when the table it lands in preserves
both.

**The log.** Doctrine D-07 fixes the shape: every event carries a producer, the
sequence is dense per (run_id, producer_id), and (sim_ts, producer_id, seq) is
a total order over the log. Gate VAL-GATE-ENV-001 asserts that after the fact.
`append` asserts it at the seam instead, and it does so by calling the same
functions the gate calls, imported from twinflow-schemas. A second reading of
the rule, written here, is a second rule that can disagree with the first.

**The snapshot.** Doctrine D-01 split the run manifest because wall-clock time
and machine identity in the first event made a byte-identical log impossible by
construction. `ConfigSnapshot` is the hashed core and carries neither.
`SnapshotProvenance` is the sidecar and carries both. `provenance_leaks` is the
carve-out as a runtime check rather than a review habit, and it refuses a
snapshot that grows a field it must not have.

**The batch table.** Decision D2, requirement ARCH-3. Delta is the table
format and DuckDB is the query engine, and treating one as both is the mistake
that decision exists to avoid. This module declares the format and produces the
rows; `deltalake` and `duckdb` themselves sit behind the `delta` extra of
foundations section 2.7, so the base install stays a pure-Python brick and the
five-minute quickstart of VAL-GATE-QS-001 does not spend its budget on a Rust
wheel a reader of the contract never calls.

The clock arrives as an injected port. A historian is exactly where a wall
clock gets read by accident, and a wall-clock read here would put the machine
into the arrival record of every event.
"""

from __future__ import annotations

import dataclasses
import hashlib
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime

from twinflow.kernel import Clock, SimInstant
from twinflow.schemas import (
    Envelope,
    LogViolation,
    canonical_bytes,
    canonical_json,
    check_log_invariants,
    in_total_order,
    log_hash,
)

#: The two run modes of foundations 3.3. Named here rather than imported
#: because the kernel's RunMode arrives with the runtime builder, and two
#: definitions of one name is exactly what boundary rule A1.4 forbids.
_RUN_MODES = ("production", "simulation")

#: Field-name fragments that mark a value as provenance under doctrine D-01.
#: Matched as substrings, so platform_arch and anchor_monotonic_wall are caught
#: as readily as host. A datetime-valued field is caught by its type as well,
#: which covers a wall-clock field whose name says nothing.
PROVENANCE_MARKERS = frozenset(
    {"wall", "host", "platform", "machine", "git", "package", "version", "user"}
)

#: The metric marker that carries the historian's measured row size. It is a
#: marker rather than a governed metric id: the registry grammar of foundations
#: 5.15 is <domain>.<area>.<name>, and this name has no dots.
STORED_BYTES_METRIC = "historian_stored_bytes_per_sensor_reading"

#: Unmeasured, so None rather than a plausible integer. Foundations 5.6 makes
#: this the rule for operator-facing output: the volume warning degrades to the
#: reading count plus "historian volume not yet measured" rather than printing
#: an unattributed round number. `just measure-row-bytes` fills both constants
#: and the marker in the same commit, and nothing may fill one of the three.
STORED_BYTES_PER_READING: int | None = None

#: The run id the number above was measured on, per the same rule. A byte
#: figure with no run behind it is a guess wearing a unit.
STORED_BYTES_MEASURED_ON: str | None = None


class HistorianError(ValueError):
    """Something the historian refuses to record, with the operator's code."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(f"{code} {message}")
        self.code = code


def provenance_leaks(record: object) -> list[str]:
    """The fields of a dataclass that doctrine D-01 keeps out of the hash.

    Returned sorted and by name, because "this object carries provenance" is
    not something a caller can act on. The field name is.
    """
    if not dataclasses.is_dataclass(record) or isinstance(record, type):
        raise TypeError(f"provenance_leaks reads a dataclass instance, got {type(record).__name__}")

    leaks: list[str] = []
    markers = sorted(PROVENANCE_MARKERS)
    for field in dataclasses.fields(record):
        lowered = field.name.lower()
        named_as_provenance = any(marker in lowered for marker in markers)
        if named_as_provenance or isinstance(getattr(record, field.name), datetime):
            leaks.append(field.name)
    return sorted(leaks)


@dataclass(frozen=True)
class ConfigSnapshot:
    """The per-run config snapshot, hashed and carried inside the log.

    Every field here is an input the run was started with. None of them is an
    observation of the machine that ran it, which is what makes two runs of one
    config on two machines comparable at all.
    """

    run_id: str
    seed: int
    replication_index: int
    mode: str
    config_hash: str
    schema_snapshot_hash: str
    faults_hash: str
    profile: str
    scenario: str | None
    tick_hz: int
    horizon_ticks: int
    warmup_ticks: int

    def __post_init__(self) -> None:
        if self.mode not in _RUN_MODES:
            raise HistorianError(
                "TF-S022",
                f"run mode {self.mode!r} is not one of {', '.join(_RUN_MODES)}",
            )
        leaks = provenance_leaks(self)
        if leaks:
            raise HistorianError(
                "TF-S020",
                f"the hashed core carries provenance fields {leaks}; doctrine D-01 puts "
                f"wall-clock time and machine identity in the sidecar, because a log hash "
                f"covering either can never match between two runs",
            )

    def payload(self) -> dict[str, object]:
        """The snapshot as the first event carries it: the core and nothing else."""
        return {field.name: getattr(self, field.name) for field in dataclasses.fields(self)}

    def snapshot_hash(self) -> str:
        """A digest over every field, so no input is silently outside it.

        Canonical JSON with sorted keys rather than the object's repr, for the
        reason log_hash gives: a formatting change is not a change of inputs
        and must not read as one.
        """
        return hashlib.blake2b(
            canonical_bytes(self.payload()), digest_size=32, person=b"twinflow-snap"
        ).hexdigest()


@dataclass(frozen=True)
class SnapshotProvenance:
    """The sidecar of doctrine D-01. Written beside the log, never inside it.

    The wall-clock instants arrive as arguments. Reading them is one of the
    four places doctrine D-02 permits a wall clock, and that place is the
    caller writing the sidecar, not this package.
    """

    run_id: str
    started_wall_utc: datetime | None
    finished_wall_utc: datetime | None
    host: str
    packages: tuple[tuple[str, str], ...]
    event_count: int
    event_log_hash: str | None


@dataclass(frozen=True)
class Column:
    """One column of the batch table, and where its value comes from."""

    name: str
    arrow_type: str
    nullable: bool
    note: str


@dataclass(frozen=True)
class TableFormat:
    """The batch path table, declared without importing the writer.

    Typing the format as data rather than as a `deltalake` call is what lets a
    reader install this brick alone and still see what the table looks like,
    and it is the D-10 rule applied to a table: no signature here names a type
    from a heavy dependency.
    """

    table: str
    table_format: str
    writer: str
    reader: str
    columns: tuple[Column, ...]
    partition_by: tuple[str, ...]
    sort_by: tuple[str, ...]
    compression: str
    compression_level: int


#: The event log's Delta table. Column names are the envelope's own attribute
#: names, so a reader of the table and a reader of the log see one set of
#: names. specversion and datacontenttype are the two envelope attributes with
#: no column: both are single-valued constants fixed by the model, and a column
#: that holds one value in every row costs bytes to say nothing.
EVENT_TABLE = TableFormat(
    table="event_log",
    table_format="delta",
    # Decision D2: delta-rs writes the table and its _delta_log, DuckDB reads
    # it back through Arrow. Delta is the format, DuckDB is the engine.
    writer="delta-rs",
    reader="duckdb",
    columns=(
        Column("twinflowrunid", "string", False, "the partition key of the envelope schema"),
        Column("twinflowsimts", "int64", False, "sim ticks; int64 because a string sorts 10 first"),
        Column("twinflowproducerid", "string", False, "the closed producer set of invariant E3"),
        Column("twinflowseq", "int64", False, "dense per producer, int64 for the same reason"),
        Column("id", "string", False, "the deterministic event id of invariant E2"),
        Column("type", "string", False, "the subject's event type"),
        Column("source", "string", False, "/twinflow/<package>/<component>"),
        Column("subject", "string", True, "the registry subject, absent on some events"),
        Column("dataschema", "string", False, "the schema version this row was written under"),
        Column("time", "timestamp[us, tz=UTC]", False, "CloudEvents wall time, never sorted on"),
        Column("twinflowcausationid", "string", True, "the event that caused this one"),
        Column("twinflowcorrid", "string", True, "the correlation id"),
        Column("partitionkey", "string", True, "CloudEvents Partitioning extension"),
        Column("traceparent", "string", True, "CloudEvents Distributed Tracing extension"),
        Column("tracestate", "string", True, "CloudEvents Distributed Tracing extension"),
        Column("data", "string", False, "the payload as canonical JSON"),
    ),
    # foundations 3.4 quotes the CloudEvents Partitioning extension on grouping
    # events with a causal relationship, and schemas/envelope/v1.json declares
    # twinflowrunid as x-twinflow-partition-key. One partition per run is also
    # what makes a run deletable without touching another run's files.
    partition_by=("twinflowrunid",),
    # Invariant E4's total order, in its order. A Delta table sorted on
    # anything else hands a replay the events in an order the log never had.
    sort_by=("twinflowsimts", "twinflowproducerid", "twinflowseq"),
    # foundations 5.6 measures the stored row size under zstd level 3, so the
    # measurement and the writer have to name the same codec and level.
    compression="zstd",
    compression_level=3,
)

#: Envelope attributes that are decimal strings in the log and integers in the
#: table. The envelope carries them as strings because CloudEvents fixes its
#: Integer type at 32 bits signed and both counters leave that range.
_INTEGER_COLUMNS = ("twinflowsimts", "twinflowseq")


def rows_for(events: Iterable[Envelope]) -> tuple[dict[str, object], ...]:
    """The batch rows for a log, in the canonical total order.

    Ordering here rather than at the call site is deliberate. A writer that
    appends in arrival order produces a Delta file whose row order differs
    between two runs that agree on every event, and a reader comparing two
    tables byte for byte would call that a difference in behavior.
    """
    return tuple(_row_for(event) for event in in_total_order(events))


def _row_for(event: Envelope) -> dict[str, object]:
    row: dict[str, object] = {}
    for column in EVENT_TABLE.columns:
        if column.name == "data":
            row[column.name] = canonical_json(event.data)
        elif column.name in _INTEGER_COLUMNS:
            row[column.name] = int(getattr(event, column.name))
        else:
            row[column.name] = getattr(event, column.name)
    return row


class Historian:
    """The L2 system of record for one run's events.

    Append-only in the strict sense: there is no update, no delete, and no
    reordering. `events` hands back what was appended in the order it was
    appended, and `replay` hands back the same events in the total order of
    invariant E4. Both are needed and neither substitutes for the other: the
    first is what happened at this process, the second is what happened.

    Sim time and arrival time are recorded separately. A device that buffered
    readings across a site-link outage replays them with their original
    sim-time timestamps, so an arrival later than the reading is the normal
    case rather than a fault, and `backfilled` is how a reader tells the two
    apart without guessing.

    This surface is synchronous. The kernel's `EventLog` port of foundations
    3.6 is async, and the adapter that satisfies it wraps this core; it lands
    with the port rather than ahead of it, because a port with no consumer is
    a name nobody has tested.
    """

    def __init__(self, *, clock: Clock, snapshot: ConfigSnapshot) -> None:
        self._clock = clock
        self._snapshot = snapshot
        self._events: list[Envelope] = []
        #: The tier-one hash of the log as it currently stands, or None when
        #: the log has changed since it was last computed. `append` is the only
        #: thing that changes the log, so it is the only thing that clears this.
        self._hash: str | None = None
        self._received: dict[str, SimInstant] = {}
        self._next_seq: dict[str, int] = {}
        self._sealed = False

    @property
    def snapshot(self) -> ConfigSnapshot:
        return self._snapshot

    @property
    def sealed(self) -> bool:
        return self._sealed

    def __len__(self) -> int:
        return len(self._events)

    def append(self, event: Envelope) -> None:
        """Record one event, or refuse it and record nothing.

        Every refusal below is a defect that a later reader could not repair.
        A gap cannot be filled once the run has ended, a duplicate cannot be
        told from a genuine retry, and an event stamped after the clock has no
        position in a replay. Refusing at the seam is the only point where the
        producer is still around to be fixed.
        """
        if self._sealed:
            raise HistorianError(
                "TF-S015",
                f"run {self._snapshot.run_id} is sealed; its provenance sidecar already "
                f"records the log hash, and an append now would invalidate it",
            )

        if event.twinflowrunid != self._snapshot.run_id:
            raise HistorianError(
                "TF-S010",
                f"event {event.id!r} belongs to run {event.twinflowrunid!r}, and this "
                f"historian records run {self._snapshot.run_id!r}",
            )

        sim_ts = int(event.twinflowsimts)
        now = self._clock.now()
        if sim_ts > int(now):
            raise HistorianError(
                "TF-S014",
                f"event {event.id!r} is stamped at sim instant {sim_ts}, which is after the "
                f"clock reading {int(now)}; a reading from the future has no position in a replay",
            )

        if event.id in self._received:
            raise HistorianError(
                "TF-S012",
                f"event id {event.id!r} is already recorded; a replay would count it twice",
            )

        producer = event.twinflowproducerid
        expected = self._next_seq.get(producer, 0)
        sequence = int(event.twinflowseq)
        if sequence != expected:
            raise HistorianError(
                "TF-S011",
                f"producer {producer!r} is at sequence {expected} for run "
                f"{self._snapshot.run_id}, and event {event.id!r} claims {sequence}; "
                f"doctrine D-07 makes the sequence dense per (run_id, producer_id)",
            )

        self._events.append(event)
        self._hash = None
        self._received[event.id] = now
        self._next_seq[producer] = expected + 1

    def events(self) -> tuple[Envelope, ...]:
        """What was appended, in the order it was appended."""
        return tuple(self._events)

    def replay(self) -> tuple[Envelope, ...]:
        """The log in the canonical order of invariant E4."""
        return tuple(in_total_order(self._events))

    def read(
        self,
        *,
        since: SimInstant | None = None,
        subjects: Sequence[str] | None = None,
    ) -> tuple[Envelope, ...]:
        """The events at or after `since` on any of `subjects`, in total order.

        Both filters are inclusive of their boundary and neither reorders
        anything, which is what makes paging over this stable: a cursor taken
        at one instant sees the same events in the same places on a later call.
        """
        wanted = None if subjects is None else tuple(subjects)
        selected = [
            event
            for event in self._events
            if (since is None or int(event.twinflowsimts) >= int(since))
            and (wanted is None or event.subject in wanted)
        ]
        return tuple(in_total_order(selected))

    def received_at(self, event_id: str) -> SimInstant:
        """The sim instant this event reached the historian."""
        if event_id not in self._received:
            raise HistorianError("TF-S013", f"no event {event_id!r} in run {self._snapshot.run_id}")
        return self._received[event_id]

    def backfilled(self) -> tuple[Envelope, ...]:
        """Events that arrived later than they happened.

        The store-and-forward case of the tier structure: a buffered reading
        keeps its original sim-time timestamp, so the gap between the two is
        the evidence that a link was down rather than a defect in the reading.
        """
        return tuple(
            event
            for event in self._events
            if int(self._received[event.id]) > int(event.twinflowsimts)
        )

    def violations(self) -> list[LogViolation]:
        """Gate VAL-GATE-ENV-001, run against this log by the gate's own code."""
        return check_log_invariants(self._events)

    def hash(self) -> str:
        """The tier-one determinism hash of doctrine D-05, over this log.

        Held until `append` changes the log. The hash orders and serializes
        every event, so it costs the whole log each time it is asked for, and
        the API asks once per run on every request to `GET /runs`. An
        append-only log makes the value a function of state that exactly one
        method changes, which is what makes holding it safe rather than a
        cache with an invalidation problem.
        """
        if self._hash is None:
            self._hash = log_hash(self._events)
        return self._hash

    def seal(
        self,
        *,
        started_wall_utc: datetime | None,
        finished_wall_utc: datetime | None,
        host: str,
        packages: Mapping[str, str],
    ) -> SnapshotProvenance:
        """Close the log and return the sidecar to write beside it.

        The hash and the event count land in the sidecar, never in the log. A
        log carrying its own hash is a log whose hash changes when it records
        it, which is the same failure doctrine D-01 ruled on for wall time.
        """
        self._sealed = True
        return SnapshotProvenance(
            run_id=self._snapshot.run_id,
            started_wall_utc=started_wall_utc,
            finished_wall_utc=finished_wall_utc,
            host=host,
            packages=tuple(sorted(packages.items())),
            event_count=len(self._events),
            event_log_hash=self.hash(),
        )
