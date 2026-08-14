"""The append-only log, the per-run config snapshot, and the batch table.

Requirement E4a. Three separate claims are pinned here and none of them stands
in for another:

    the log is append-only and dense       gate VAL-GATE-ENV-001, doctrine D-07
    the snapshot carries no provenance     doctrine D-01
    the batch table names the envelope     decision D2, requirement ARCH-3

The ENV-001 half is asserted with the same functions the gate runs, imported
from twinflow-schemas, so the historian is checked by the gate's own code
rather than by a second reading of the rule.
"""

from __future__ import annotations

import dataclasses
import json
from datetime import UTC, datetime
from pathlib import Path

import pytest

from twinflow.kernel import SimClock, SimInstant
from twinflow.schemas import Envelope, check_log_invariants, in_total_order, log_hash
from twinflow.storage import (
    EVENT_TABLE,
    STORED_BYTES_MEASURED_ON,
    STORED_BYTES_METRIC,
    STORED_BYTES_PER_READING,
    ConfigSnapshot,
    Historian,
    HistorianError,
    SnapshotProvenance,
    provenance_leaks,
    rows_for,
)

REPO_ROOT = Path(__file__).resolve().parents[3]
ENVELOPE_SCHEMA = REPO_ROOT / "schemas" / "envelope" / "v1.json"
FOUNDATIONS = REPO_ROOT / "docs" / "design" / "foundations.md"

RUN_ID = "run_01jabcdefghijklmnopqrstuvw"


def snapshot(**overrides) -> ConfigSnapshot:
    fields = {
        "run_id": RUN_ID,
        "seed": 42,
        "replication_index": 0,
        "mode": "simulation",
        "config_hash": "b" * 64,
        "schema_snapshot_hash": "c" * 64,
        "faults_hash": "d" * 64,
        "profile": "profiles/midmarket_3pl.yaml",
        "scenario": "SCN-F1",
        "tick_hz": 1_000_000,
        "horizon_ticks": 86_400_000_000,
        "warmup_ticks": 0,
    }
    fields.update(overrides)
    return ConfigSnapshot(**fields)


def event(
    *,
    seq: int,
    sim_ts: int,
    producer: str = "sim",
    run_id: str = RUN_ID,
    subject: str = "twinflow.telemetry.sensor_reading",
    event_id: str | None = None,
) -> Envelope:
    return Envelope(
        specversion="1.0",
        id=event_id or f"{producer}-{seq}",
        source="/twinflow/storage/historian",
        type=subject,
        time=datetime(2026, 1, 1, tzinfo=UTC),
        datacontenttype="application/json",
        subject=subject,
        dataschema="twinflow:schemas/telemetry/sensor_reading/v1.json",
        twinflowsimts=str(sim_ts),
        twinflowrunid=run_id,
        twinflowproducerid=producer,
        twinflowseq=str(seq),
        data={"value": seq},
    )


def open_historian(*, at: int = 10_000) -> tuple[Historian, SimClock]:
    clock = SimClock()
    clock.advance_to(SimInstant(at))
    return Historian(clock=clock, snapshot=snapshot()), clock


# ------------------------------------------------------------- append-only log


def test_the_log_keeps_append_order_and_hands_back_something_immutable():
    historian, _ = open_historian()
    historian.append(event(seq=0, sim_ts=0))
    historian.append(event(seq=1, sim_ts=5))

    recorded = historian.events()
    assert isinstance(recorded, tuple)
    assert [int(e.twinflowseq) for e in recorded] == [0, 1]
    assert len(historian) == 2


def test_a_gap_in_one_producers_sequence_is_refused_at_the_seam():
    historian, _ = open_historian()
    historian.append(event(seq=0, sim_ts=0))

    with pytest.raises(HistorianError) as caught:
        historian.append(event(seq=2, sim_ts=1))
    assert caught.value.code == "TF-S011"
    assert len(historian) == 1


def test_each_producer_carries_its_own_dense_sequence():
    """Doctrine D-07: dense per (run_id, producer_id), never globally."""
    historian, _ = open_historian()
    historian.append(event(seq=0, sim_ts=0, producer="sim"))
    historian.append(event(seq=0, sim_ts=0, producer="agent"))
    historian.append(event(seq=1, sim_ts=1, producer="sim"))

    assert historian.violations() == []


def test_a_duplicate_event_id_is_refused():
    historian, _ = open_historian()
    historian.append(event(seq=0, sim_ts=0, event_id="e-1"))

    with pytest.raises(HistorianError) as caught:
        historian.append(event(seq=1, sim_ts=1, event_id="e-1"))
    assert caught.value.code == "TF-S012"


def test_an_event_from_another_run_is_refused():
    historian, _ = open_historian()

    with pytest.raises(HistorianError) as caught:
        historian.append(event(seq=0, sim_ts=0, run_id="run_other"))
    assert caught.value.code == "TF-S010"


def test_an_event_stamped_after_the_clock_is_refused():
    historian, clock = open_historian(at=100)

    with pytest.raises(HistorianError) as caught:
        historian.append(event(seq=0, sim_ts=101))
    assert caught.value.code == "TF-S014"
    assert clock.now() == 100


def test_a_reading_buffered_across_an_outage_keeps_its_own_sim_ts():
    """The store-and-forward case: the reading is old, the arrival is not."""
    clock = SimClock()
    clock.advance_to(SimInstant(50))
    historian = Historian(clock=clock, snapshot=snapshot())
    historian.append(event(seq=0, sim_ts=50, event_id="live"))

    clock.advance_to(SimInstant(900))
    historian.append(event(seq=1, sim_ts=60, event_id="buffered"))

    assert historian.received_at("buffered") == 900
    assert [e.id for e in historian.backfilled()] == ["buffered"]
    assert historian.events()[1].twinflowsimts == "60"


def test_the_log_satisfies_the_env_001_invariants_the_gate_runs():
    historian, clock = open_historian(at=0)
    for index in range(5):
        clock.advance_to(SimInstant(index))
        historian.append(event(seq=index, sim_ts=index))

    assert check_log_invariants(historian.events()) == []
    assert historian.violations() == []


def test_the_hash_is_the_schemas_log_hash_and_not_a_second_definition():
    historian, _ = open_historian()
    historian.append(event(seq=0, sim_ts=0))
    historian.append(event(seq=1, sim_ts=1))

    assert historian.hash() == log_hash(historian.events())


def test_replay_is_the_canonical_total_order():
    historian, _ = open_historian()
    historian.append(event(seq=0, sim_ts=9, producer="sim"))
    historian.append(event(seq=0, sim_ts=1, producer="agent"))

    assert historian.replay() == tuple(in_total_order(historian.events()))
    assert [e.id for e in historian.replay()] == ["agent-0", "sim-0"]


def test_read_filters_by_instant_and_by_subject():
    historian, _ = open_historian()
    historian.append(event(seq=0, sim_ts=1, subject="twinflow.telemetry.sensor_reading"))
    historian.append(event(seq=1, sim_ts=7, subject="twinflow.telemetry.sensor_reading"))
    historian.append(event(seq=2, sim_ts=9, subject="twinflow.kernel.run_started"))

    later = historian.read(since=SimInstant(7))
    assert [e.id for e in later] == ["sim-1", "sim-2"]

    telemetry = historian.read(subjects=("twinflow.telemetry.sensor_reading",))
    assert [e.id for e in telemetry] == ["sim-0", "sim-1"]


# ------------------------------------------------- D-01, the snapshot carve-out


def test_the_snapshot_carries_no_wall_clock_and_no_machine_identity():
    assert provenance_leaks(snapshot()) == []


def test_the_carve_out_check_fires_on_the_sidecar_it_was_written_for():
    """A check that never fires is not a check, so this proves it does."""
    sidecar = SnapshotProvenance(
        run_id=RUN_ID,
        started_wall_utc=datetime(2026, 1, 1, tzinfo=UTC),
        finished_wall_utc=None,
        host="build-07",
        packages=(("twinflow-storage", "0.1.0"),),
        event_count=0,
        event_log_hash=None,
    )
    assert provenance_leaks(sidecar) == [
        "finished_wall_utc",
        "host",
        "packages",
        "started_wall_utc",
    ]


def test_a_field_naming_a_platform_is_reported_by_name():
    @dataclasses.dataclass(frozen=True)
    class Leaky:
        run_id: str
        platform_arch: str

    assert provenance_leaks(Leaky(run_id=RUN_ID, platform_arch="arm64")) == ["platform_arch"]


def test_the_snapshot_payload_is_the_hashed_core_and_nothing_else():
    payload = snapshot().payload()
    declared = {field.name for field in dataclasses.fields(ConfigSnapshot)}

    assert set(payload) == declared
    assert provenance_leaks(snapshot()) == []
    assert json.dumps(payload, sort_keys=True)


def test_every_snapshot_field_changes_the_snapshot_hash():
    """A field outside the hash is a field two different runs can disagree on."""
    baseline = snapshot()
    changed = {
        "run_id": "run_02jabcdefghijklmnopqrstuvw",
        "seed": 43,
        "replication_index": 1,
        "mode": "production",
        "config_hash": "e" * 64,
        "schema_snapshot_hash": "f" * 64,
        "faults_hash": "0" * 64,
        "profile": "profiles/starter_dc.yaml",
        "scenario": None,
        "tick_hz": 1_000,
        "horizon_ticks": 1,
        "warmup_ticks": 7,
    }
    assert set(changed) == {field.name for field in dataclasses.fields(ConfigSnapshot)}

    for name, value in sorted(changed.items()):
        assert snapshot(**{name: value}).snapshot_hash() != baseline.snapshot_hash(), name


def test_an_unknown_run_mode_is_refused():
    with pytest.raises(HistorianError) as caught:
        snapshot(mode="dry-run")
    assert caught.value.code == "TF-S022"


def test_sealing_puts_the_wall_clock_in_the_sidecar_and_leaves_the_log_alone():
    historian, _ = open_historian()
    historian.append(event(seq=0, sim_ts=0))
    before = historian.hash()

    sidecar = historian.seal(
        started_wall_utc=datetime(2026, 1, 1, tzinfo=UTC),
        finished_wall_utc=datetime(2026, 1, 2, tzinfo=UTC),
        host="build-07",
        packages={"twinflow-storage": "0.1.0"},
    )

    assert historian.hash() == before
    assert sidecar.event_log_hash == before
    assert sidecar.event_count == 1
    assert provenance_leaks(sidecar) != []


def test_appending_after_the_seal_is_refused():
    historian, _ = open_historian()
    historian.seal(
        started_wall_utc=datetime(2026, 1, 1, tzinfo=UTC),
        finished_wall_utc=datetime(2026, 1, 2, tzinfo=UTC),
        host="build-07",
        packages={},
    )

    with pytest.raises(HistorianError) as caught:
        historian.append(event(seq=0, sim_ts=0))
    assert caught.value.code == "TF-S015"


# ------------------------------------------- ARCH-3, the batch path table format


def test_every_batch_column_is_an_envelope_attribute():
    """One spelling. A column the envelope does not declare has no source."""
    declared = set(Envelope.model_fields)
    assert {column.name for column in EVENT_TABLE.columns} <= declared


def test_the_batch_table_carries_every_ordering_field_the_replay_needs():
    assert EVENT_TABLE.sort_by == ("twinflowsimts", "twinflowproducerid", "twinflowseq")
    for name in EVENT_TABLE.sort_by:
        assert name in {column.name for column in EVENT_TABLE.columns}


@pytest.mark.skipif(not ENVELOPE_SCHEMA.is_file(), reason="installed without the repository")
def test_the_partition_column_is_the_one_the_envelope_schema_declares():
    published = json.loads(ENVELOPE_SCHEMA.read_text(encoding="utf-8"))
    assert EVENT_TABLE.partition_by == (published["x-twinflow-partition-key"],)


def test_the_table_is_delta_written_by_delta_rs_and_read_by_duckdb():
    """Decision D2: Delta is the table format, DuckDB is the query engine."""
    assert EVENT_TABLE.table_format == "delta"
    assert EVENT_TABLE.writer == "delta-rs"
    assert EVENT_TABLE.reader == "duckdb"
    assert (EVENT_TABLE.compression, EVENT_TABLE.compression_level) == ("zstd", 3)


def test_the_batch_rows_arrive_in_the_total_order_whatever_the_append_order():
    historian, _ = open_historian()
    historian.append(event(seq=0, sim_ts=9, producer="sim"))
    historian.append(event(seq=0, sim_ts=1, producer="agent"))

    rows = rows_for(historian.events())
    assert [row["id"] for row in rows] == ["agent-0", "sim-0"]
    assert [row["twinflowsimts"] for row in rows] == [1, 9]


def test_the_two_decimal_string_attributes_are_stored_as_integers():
    """A table whose sort key is a string sorts 10 before 2."""
    historian, _ = open_historian()
    historian.append(event(seq=0, sim_ts=2))

    row = rows_for(historian.events())[0]
    assert isinstance(row["twinflowsimts"], int)
    assert isinstance(row["twinflowseq"], int)
    assert isinstance(row["data"], str)


def test_a_row_carries_exactly_the_declared_columns():
    historian, _ = open_historian()
    historian.append(event(seq=0, sim_ts=0))

    row = rows_for(historian.events())[0]
    assert set(row) == {column.name for column in EVENT_TABLE.columns}


# ------------------------------------------------------------- the owed number


def test_the_stored_bytes_metric_is_unmeasured_and_says_so():
    assert STORED_BYTES_METRIC == "historian_stored_bytes_per_sensor_reading"
    assert STORED_BYTES_PER_READING is None
    assert STORED_BYTES_MEASURED_ON is None


@pytest.mark.skipif(not FOUNDATIONS.is_file(), reason="installed without the repository")
def test_the_code_and_the_marker_agree_about_whether_the_number_exists():
    """The constant here and the marker in the design page say the same thing.

    The tag the marker names is read out of the document rather than written
    here. Which release owes the number is a scheduling decision that moves with
    the work package that measures it, and a copy of it in this test would make
    that move a test failure instead of a plan edit. What this asserts is the
    part that must never drift: an unmeasured constant and an unfilled marker,
    or a measured one and a filled marker, and never one of each.
    """
    import re

    text = FOUNDATIONS.read_text(encoding="utf-8")
    marker = re.search(
        rf"<!--METRIC:{re.escape(STORED_BYTES_METRIC)}@v[0-9.]+-->(.*?)<!--/METRIC-->", text
    )

    assert marker is not None, f"{STORED_BYTES_METRIC} has no marker in {FOUNDATIONS.name}"
    assert (marker.group(1) == "TBD") == (STORED_BYTES_PER_READING is None)


def test_the_hash_is_held_between_calls_and_released_by_append():
    """`hash` orders and serializes the whole log, and `GET /runs` asks once per
    run on every request, so the value is held rather than recomputed.

    An append-only log makes the hash a function of state that exactly one
    method changes. This asserts both halves: asking twice gives one answer, and
    the answer moves when the log does. Without the second half the value would
    be a cache that goes stale silently, which is worse than recomputing it.
    """
    historian, _ = open_historian()
    for index in range(8):
        historian.append(event(seq=index, sim_ts=index))

    first = historian.hash()
    assert historian.hash() == first

    historian.append(event(seq=8, sim_ts=8))

    assert historian.hash() != first
    assert historian.hash() == log_hash(historian.events())
