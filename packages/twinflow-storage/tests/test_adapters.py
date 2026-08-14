"""A run written to a directory and read back, and every way that can go wrong.

The load-bearing test is the round trip: what comes back hashes to what went
out. Everything below it is a corruption the reader has to refuse, because a
run directory is a file on a volume that anything with write access can edit,
and `twinflow-api` publishes `log_hash` off whatever it loaded.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

import pytest

from twinflow.kernel import SimClock, SimInstant
from twinflow.schemas import Envelope
from twinflow.storage import (
    ARRIVALS_FILE,
    EVENTS_FILE,
    PROVENANCE_FILE,
    SNAPSHOT_FILE,
    ArchiveError,
    ConfigSnapshot,
    Historian,
    discover_runs,
    read_run,
    write_run,
)

RUN_ID = "run_01jabcdefghijklmnopqrstuvw"


def make_snapshot(run_id: str = RUN_ID) -> ConfigSnapshot:
    return ConfigSnapshot(
        run_id=run_id,
        seed=42,
        replication_index=0,
        mode="simulation",
        config_hash="b" * 64,
        schema_snapshot_hash="c" * 64,
        faults_hash="d" * 64,
        profile="profiles/micro_fulfillment.yaml",
        scenario="SCN-F1",
        tick_hz=1_000_000,
        horizon_ticks=86_400_000_000,
        warmup_ticks=0,
    )


def make_event(*, run_id: str, seq: int, sim_ts: int) -> Envelope:
    return Envelope(
        specversion="1.0",
        id=f"sim-{seq}",
        source="/twinflow/storage/adapters",
        type="twinflow.telemetry.sensor_reading",
        time=datetime(2026, 1, 1, tzinfo=UTC),
        datacontenttype="application/json",
        subject="twinflow.telemetry.sensor_reading",
        dataschema="twinflow:schemas/telemetry/sensor_reading/v1.json",
        twinflowsimts=str(sim_ts),
        twinflowrunid=run_id,
        twinflowproducerid="sim",
        twinflowseq=str(seq),
        data={"value": seq},
    )


def build(run_id: str = RUN_ID, *, arrivals: tuple[int, ...] = (0, 5, 12)) -> Historian:
    """A historian holding three events, the last two arriving late."""
    clock = SimClock()
    historian = Historian(clock=clock, snapshot=make_snapshot(run_id))
    for index, arrival in enumerate(arrivals):
        clock.advance_to(SimInstant(arrival))
        historian.append(make_event(run_id=run_id, seq=index, sim_ts=index))
    return historian


def seal(historian: Historian):
    return historian.seal(
        started_wall_utc=datetime(2026, 1, 1, tzinfo=UTC),
        finished_wall_utc=datetime(2026, 1, 1, 0, 5, tzinfo=UTC),
        host="reference-runner",
        packages={"twinflow-storage": "0.1.0"},
    )


@pytest.fixture
def written(tmp_path: Path) -> Path:
    historian = build()
    provenance = seal(historian)
    return write_run(historian, provenance, tmp_path)


# ------------------------------------------------------------------ round trip


def test_a_run_reads_back_to_the_hash_it_was_written_with(written: Path):
    """The claim everything else rests on. `twinflow-api` publishes this number
    on its runs route, and a hash that changed across a round trip would be a
    number describing a log nobody has."""
    original = build()
    seal(original)

    restored = read_run(written)

    assert restored.hash() == original.hash()


def test_the_snapshot_reads_back_field_for_field(written: Path):
    restored = read_run(written)

    assert restored.snapshot == make_snapshot(RUN_ID)
    assert restored.snapshot.snapshot_hash() == make_snapshot(RUN_ID).snapshot_hash()


def test_arrival_instants_survive_the_round_trip(written: Path):
    """Sim time is when a reading happened and arrival is when it reached the
    historian. A reader that let the replay clock stamp fresh arrivals would
    report every buffered reading as on time, turning a recorded site-link
    outage into a clean run."""
    restored = read_run(written)

    arrivals = [int(restored.received_at(event.id)) for event in restored.events()]
    assert arrivals == [0, 5, 12]


def test_the_backfilled_set_survives_with_them(written: Path):
    original = build()
    seal(original)

    restored = read_run(written)

    assert [event.id for event in restored.backfilled()] == [
        event.id for event in original.backfilled()
    ]


def test_a_read_run_comes_back_sealed(written: Path):
    """An unsealed one would accept an append, and the sidecar beside it already
    records a hash that the append would invalidate."""
    assert read_run(written).sealed


def test_the_events_file_carries_the_log_and_nothing_else(written: Path):
    """Doctrine D-01 on disk. Folding the host or the arrival instants in here
    would put machine identity inside the hashed material."""
    first = json.loads((written / EVENTS_FILE).read_text(encoding="utf-8").splitlines()[0])

    assert "host" not in first
    assert "at" not in first


# ---------------------------------------------------------------- the refusals


def test_an_unsealed_run_is_refused(tmp_path: Path):
    historian = build()
    provenance = seal(build())

    with pytest.raises(ArchiveError, match="not sealed"):
        write_run(historian, provenance, tmp_path)


def test_a_sidecar_for_another_run_is_refused(tmp_path: Path):
    historian = build()
    seal(historian)
    other = build("run_01other000000000000000000")

    with pytest.raises(ArchiveError, match="names run"):
        write_run(historian, seal(other), tmp_path)


@pytest.mark.parametrize("name", [SNAPSHOT_FILE, EVENTS_FILE, ARRIVALS_FILE, PROVENANCE_FILE])
def test_a_missing_file_is_refused_by_name(written: Path, name: str):
    """A half-written run is not a short run, and loading one would serve a
    truncated log as though it were complete."""
    (written / name).unlink()

    with pytest.raises(ArchiveError, match=name):
        read_run(written)


def test_an_edited_log_fails_the_hash_check(written: Path):
    """The reason the check exists. A run directory is a file on a volume, and
    anything with write access can change it between the write and the read."""
    lines = (written / EVENTS_FILE).read_text(encoding="utf-8").splitlines()
    (written / EVENTS_FILE).write_text("\n".join(lines[:-1]) + "\n", encoding="utf-8")

    with pytest.raises(ArchiveError, match="edited or truncated"):
        read_run(written)


def test_a_missing_arrival_is_refused_rather_than_invented(written: Path):
    lines = (written / ARRIVALS_FILE).read_text(encoding="utf-8").splitlines()
    (written / ARRIVALS_FILE).write_text("\n".join(lines[:-1]) + "\n", encoding="utf-8")

    with pytest.raises(ArchiveError, match="no arrival"):
        read_run(written)


def test_an_event_count_that_disagrees_is_refused(written: Path):
    sidecar = json.loads((written / PROVENANCE_FILE).read_text(encoding="utf-8"))
    sidecar["event_count"] = 99
    (written / PROVENANCE_FILE).write_text(json.dumps(sidecar), encoding="utf-8")

    with pytest.raises(ArchiveError, match="replays 3 events"):
        read_run(written)


# ----------------------------------------------------------------- discovery


def test_discovery_returns_every_run_keyed_by_id(tmp_path: Path):
    for run_id in (RUN_ID, "run_01other000000000000000000"):
        historian = build(run_id)
        write_run(historian, seal(historian), tmp_path)

    found = discover_runs(tmp_path)

    assert sorted(found) == sorted([RUN_ID, "run_01other000000000000000000"])


def test_discovery_over_a_root_that_does_not_exist_is_empty(tmp_path: Path):
    """An `api` container starting before anything has been recorded is the
    ordinary first run of the tier, and `/readyz` is what reports it."""
    assert discover_runs(tmp_path / "absent") == {}


def test_discovery_reads_directories_in_sorted_order(tmp_path: Path):
    """Doctrine D-03. Two processes over one root build the same mapping in the
    same order, so a listing route pages the same way on both."""
    for run_id in ("run_01c", "run_01a", "run_01b"):
        historian = build(run_id)
        write_run(historian, seal(historian), tmp_path)

    assert list(discover_runs(tmp_path)) == ["run_01a", "run_01b", "run_01c"]


def test_a_stray_file_beside_the_runs_is_ignored(tmp_path: Path):
    historian = build()
    write_run(historian, seal(historian), tmp_path)
    (tmp_path / "README.txt").write_text("notes", encoding="utf-8")

    assert list(discover_runs(tmp_path)) == [RUN_ID]


def test_the_api_can_serve_what_discovery_returns(tmp_path: Path):
    """The end the work package is for: a run that outlives its process, loaded
    into the shape `create_api` takes."""
    historian = build()
    write_run(historian, seal(historian), tmp_path)

    runs = discover_runs(tmp_path)

    assert isinstance(runs[RUN_ID], Historian)
    assert isinstance(runs[RUN_ID].snapshot, ConfigSnapshot)
    assert len(runs[RUN_ID]) == 3
