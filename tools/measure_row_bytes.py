#!/usr/bin/env python3
"""Measure `historian_stored_bytes_per_sensor_reading` on a seeded scenario.

    uv run --no-sync python tools/measure_row_bytes.py
    uv run --no-sync python tools/measure_row_bytes.py --seed 20260813 --readings 20000
    uv run --no-sync python tools/measure_row_bytes.py --json

Behind `just measure-row-bytes`, and the producer of the artifact
`tools/check_measured_claims.py` resolves the metric marker through.

WHAT THE NUMBER MEANS
---------------------
Stored bytes in the historian divided by sensor readings recorded. Foundations
section 5.6 fixes every part of that definition: the subject is
`twinflow.telemetry.sensor_reading`, the container is the shipped batch table of
`twinflow.storage.EVENT_TABLE`, and the codec is zstd at level 3. The operator
message the number feeds prints it beside the run id it was measured on, and the
same section says why: an unattributed round number in operator-facing output is
the same defect as an unattributed round number in the README.

So this tool reports the value, the unit, the seed, and the run id together, or
it reports nothing at all. There is no mode in which it prints a number without
the run behind it.

WHAT IT REFUSES, AND WHY THAT IS THE POINT
------------------------------------------
Two preconditions of that definition are absent from this tree today, and both
are checked here rather than assumed:

  1. `twinflow.telemetry.sensor_reading` is not in `schemas/registry.yaml`. The
     bytes a row costs are the bytes of its payload, so measuring against a
     payload shape that no published schema fixes measures this tool's guess at
     the subject rather than the subject. The registry example in foundations
     section 5.5 puts that subject at `since_phase: 3`, which is v0.4.0.

  2. The writer the batch format names is not importable. `EVENT_TABLE` declares
     `writer="delta-rs"` and `compression="zstd"` at level 3; `deltalake`,
     `duckdb`, and `pyarrow` are the `delta` extra of foundations section 2.7,
     and the base install deliberately does not carry them. Parquet byte counts
     are an artifact of the encoder: row-group sizing, dictionary decisions,
     page headers, and column statistics all move them. A number produced by a
     hand-rolled encoder would not be a measurement of the shipped format, it
     would be a measurement of the encoder written to produce it.

Python 3.14 carries zstd in `compression.zstd`, and that does not rescue case 2.
The workspace floor is 3.12, the codec is only half of a container format, and a
row-oriented compression of the same rows is a different quantity from a Parquet
column chunk under the same codec.

Everything upstream of the writer runs anyway, on every invocation. The seeded
scenario is built, the events are appended to a real `twinflow.storage.Historian`
through its refusals, the log invariants of VAL-GATE-ENV-001 are checked, the
rows are produced in the canonical total order by `rows_for`, and the run id and
the log hash are computed. A refusal therefore names exactly what is missing and
proves that nothing else is, which is more useful than a refusal at import time
and much more useful than an estimate.

DETERMINISM
-----------
At a fixed seed the run id, the log hash, and the row bytes are fixed. The run
id is derived from the run's inputs rather than drawn, the raw readings come
from `twinflow.rng` under a registered stream name, and the clock is a
`SimClock`, which holds no wall-clock reading at all. `tests/test_measure_row_bytes.py`
asserts the fixed point rather than describing it.

EXIT CODES
----------
    0  measured; the artifact was written
    2  a bad argument
    3  cannot measure; the missing preconditions are named on stderr
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from dataclasses import dataclass
from datetime import UTC, datetime
from importlib.util import find_spec
from pathlib import Path
from typing import Any

import yaml

from twinflow.kernel import SimClock, SimInstant
from twinflow.rng import StreamRegistry
from twinflow.schemas import Envelope
from twinflow.sensors import (
    PlausibilityBand,
    TemperatureSensor,
    TemperatureSensorConfig,
)
from twinflow.storage import (
    EVENT_TABLE,
    STORED_BYTES_METRIC,
    ConfigSnapshot,
    Historian,
    rows_for,
)

REPO_ROOT = Path(__file__).resolve().parents[1]
REGISTRY = REPO_ROOT / "schemas" / "registry.yaml"
ARTIFACT_DIR = REPO_ROOT / "artifacts" / "measured"

#: The subject whose rows are counted. Foundations 5.6 names it, and this tool
#: refuses rather than substitutes when the registry does not carry it.
SUBJECT = "twinflow.telemetry.sensor_reading"

#: The registry key that subject would occupy, in the path form registry.yaml
#: uses for its subjects.
REGISTRY_KEY = "telemetry/sensor_reading"

#: The distributions the shipped batch writer needs. Named from EVENT_TABLE's
#: own declaration rather than typed twice: `writer="delta-rs"` ships as
#: `deltalake`, and it reads and writes Arrow, which is `pyarrow`.
WRITER_MODULES = ("deltalake", "pyarrow")

#: The measurement scenario. A fixed identifier so two runs of this tool are
#: comparable and a third run under a changed scenario is visibly not.
SCENARIO = "SCN-ROWBYTES-1"

#: Arbitrary, and fixed. Which value it is does not matter; that it never moves
#: without the artifact and the marker moving with it is the whole contract.
DEFAULT_SEED = 20260813

#: Enough rows that a Parquet row group is not dominated by its own footer, and
#: few enough that the scenario stays inside the unit tier's 90 seconds when it
#: is exercised by a test. Overridable, and the value used is recorded in the
#: artifact, because bytes per row is not independent of row count.
DEFAULT_READINGS = 20_000

#: One device, addressed the way ARCHITECTURE.md section 5 addresses it.
UNS_PREFIX = ("dc-01", "receiving", "inbound-line-01", "conveyor-02")
DEVICE_ID = "CNV-02"
STREAM = "sensors.temperature.motor_temp_c.{device_id}"

#: The sim epoch, declared rather than read from a clock. A default read from a
#: wall clock puts a different value into two runs of one seed.
EPOCH = datetime(2026, 1, 1, tzinfo=UTC)

#: One reading per simulated second at the default microsecond tick.
TICKS_PER_READING = 1_000_000

#: A wide band, per the rule PlausibilityBand states: wide enough to contain
#: every alarm the twin might raise, because it separates a broken sensor from a
#: motor in trouble rather than from a warm one.
BAND = PlausibilityBand(low_c=-40.0, high_c=200.0)
EWMA_ALPHA = 0.2

#: The plant the readings are drawn around, in degrees Celsius. A mean and a
#: spread rather than a physical model: this scenario exists to produce a fixed
#: population of rows, and the row size is what is being measured, not the motor.
MEAN_C = 62.0
SIGMA_C = 4.0


class Unmeasurable(Exception):
    """A precondition of the measurement is absent, so no number exists yet.

    Carries the run when there is one. Everything upstream of the writer
    succeeded, and the refusal is far more useful for saying so than for saying
    only that it failed.
    """

    def __init__(self, missing: list[str], run: Run | None = None) -> None:
        super().__init__("; ".join(missing))
        self.missing = missing
        self.run = run


@dataclass(frozen=True)
class Run:
    """One seeded scenario, recorded and ordered, up to the writer."""

    run_id: str
    seed: int
    readings: int
    events: int
    log_hash: str
    rows: tuple[dict[str, Any], ...]


def run_id_for(*, seed: int, readings: int, subject: str) -> str:
    """A run id that is a function of the run's inputs.

    Derived rather than drawn, for the reason M1 gives for the real one: two
    invocations of one seed are one run and must carry one id, and an id drawn
    from entropy makes every re-measurement look like a new observation of a
    number that did not move.
    """
    canonical = json.dumps(
        {
            "scenario": SCENARIO,
            "seed": seed,
            "readings": readings,
            "subject": subject,
            "table": EVENT_TABLE.table,
            "compression": f"{EVENT_TABLE.compression}:{EVENT_TABLE.compression_level}",
        },
        sort_keys=True,
        separators=(",", ":"),
    )
    digest = hashlib.blake2b(
        canonical.encode("utf-8"), digest_size=16, person=b"twinflow-run"
    ).hexdigest()
    return f"run_{digest}"


def snapshot_for(*, run_id: str, seed: int, readings: int) -> ConfigSnapshot:
    """The hashed core of doctrine D-01 for this measurement run.

    Every field is an input. None is an observation of the machine, which is
    what makes the row count comparable between two runs on two platforms.
    """
    return ConfigSnapshot(
        run_id=run_id,
        seed=seed,
        replication_index=0,
        mode="simulation",
        config_hash=hashlib.blake2b(
            SCENARIO.encode("utf-8"), digest_size=32, person=b"twinflow-conf"
        ).hexdigest(),
        schema_snapshot_hash=hashlib.blake2b(
            EVENT_TABLE.table.encode("utf-8"), digest_size=32, person=b"twinflow-schm"
        ).hexdigest(),
        faults_hash=hashlib.blake2b(b"", digest_size=32, person=b"twinflow-flts").hexdigest(),
        profile="profiles/micro_fulfillment.yaml",
        scenario=SCENARIO,
        tick_hz=1_000_000,
        horizon_ticks=readings * TICKS_PER_READING,
        warmup_ticks=0,
    )


def payload_for(topic: str, values: dict[str, Any], quality: str) -> dict[str, Any]:
    """The reading as an event payload.

    This shape is the tool's own and is NOT a published contract, which is
    precisely why `missing_preconditions` refuses while the subject is absent
    from the registry. It exists so the scenario upstream of the writer runs in
    full and the refusal is specific.
    """
    return {"topic": topic, "quality": quality, "values": values}


def build_run(*, seed: int, readings: int) -> Run:
    """Record one seeded scenario through the real historian.

    The events go through `Historian.append`, so the sequence density, the
    duplicate refusal, and the clock-ordering refusal all apply. A measurement
    taken over a list of dictionaries would be a measurement of rows the
    historian would have rejected.
    """
    if readings < 1:
        raise ValueError(f"readings must be at least 1, got {readings}")

    run_id = run_id_for(seed=seed, readings=readings, subject=SUBJECT)
    clock = SimClock(tick_hz=1_000_000)
    historian = Historian(
        clock=clock, snapshot=snapshot_for(seed=seed, readings=readings, run_id=run_id)
    )

    registry = StreamRegistry(base_seed=seed)
    registry.register(STREAM)
    generator = registry.get(STREAM, device_id=DEVICE_ID)
    raw = generator.normal(loc=MEAN_C, scale=SIGMA_C, size=readings)

    sensor = TemperatureSensor(
        config=TemperatureSensorConfig(plausibility=BAND, ewma_alpha=EWMA_ALPHA),
        uns_prefix=UNS_PREFIX,
    )
    topic_root = "/".join(UNS_PREFIX)

    for index in range(readings):
        instant = SimInstant(index * TICKS_PER_READING)
        clock.advance_to(instant)
        reading = sensor.read(float(raw[index]), now=instant)
        historian.append(
            Envelope(
                specversion="1.0",
                id=f"{run_id}-device-agent-{index}",
                source="/twinflow/sensors/temperature",
                type=SUBJECT,
                # Derived from sim_ts through the anchor, per section 3.4. Not a
                # wall-clock read: EPOCH is declared above and the offset is the
                # tick count, so this column is a function of the tape.
                time=EPOCH,
                datacontenttype="application/json",
                subject=SUBJECT,
                dataschema=f"twinflow:schemas/{REGISTRY_KEY}/v1.json",
                twinflowsimts=str(int(instant)),
                twinflowrunid=run_id,
                twinflowproducerid="device-agent",
                twinflowseq=str(index),
                data=payload_for(
                    f"{topic_root}/motor_temp_c", reading.metric_values(), reading.quality
                ),
            )
        )

    violations = historian.violations()
    if violations:
        raise RuntimeError(
            f"the measurement scenario produced {len(violations)} log invariant violation(s), "
            f"so its rows are not a log this historian would hand back: {violations[:3]}"
        )

    return Run(
        run_id=run_id,
        seed=seed,
        readings=readings,
        events=len(historian),
        log_hash=historian.hash(),
        rows=rows_for(historian.replay()),
    )


def registered_subjects() -> set[str]:
    """The subject keys `schemas/registry.yaml` publishes."""
    if not REGISTRY.is_file():
        return set()
    document = yaml.safe_load(REGISTRY.read_text(encoding="utf-8")) or {}
    return set(document.get("subjects") or {})


def missing_preconditions() -> list[str]:
    """What stands between this tree and the number, each one checkable.

    Both entries flip on their own when the tree grows what they name. Neither
    is a note a person has to remember to delete, which is the failure mode a
    hand-maintained blocker list has.
    """
    missing: list[str] = []

    if REGISTRY_KEY not in registered_subjects():
        missing.append(
            f"subject {SUBJECT} is not published: schemas/registry.yaml carries no "
            f"{REGISTRY_KEY!r} entry, so the payload whose bytes would be counted is "
            f"fixed by nothing. Foundations 5.5 places that subject at since_phase 3, "
            f"which roadmap.yaml maps to v0.4.0"
        )

    absent = [name for name in WRITER_MODULES if find_spec(name) is None]
    if absent:
        missing.append(
            f"the shipped batch writer is not importable: EVENT_TABLE declares "
            f"writer={EVENT_TABLE.writer!r} at {EVENT_TABLE.compression} level "
            f"{EVENT_TABLE.compression_level}, and {', '.join(absent)} "
            f"{'are' if len(absent) > 1 else 'is'} absent. They are the `delta` extra of "
            f"foundations 2.7, which twinflow-storage does not declare and uv.lock does "
            f"not carry. Parquet byte counts belong to the encoder that produced them, so "
            f"a substitute encoder measures itself"
        )

    return missing


def stored_bytes(run: Run) -> int:
    """The bytes the shipped batch format costs for this run's rows.

    Unreachable until `missing_preconditions` is empty, and it stays unwritten
    until then on purpose. Writing a plausible body here now is exactly the
    defect this whole tool exists to prevent, one level of indirection down.
    """
    raise Unmeasurable(missing_preconditions() or ["the batch writer is present but unwired"])


def measure(*, seed: int, readings: int) -> dict[str, Any]:
    """The full measurement, or a refusal naming what is absent."""
    run = build_run(seed=seed, readings=readings)
    missing = missing_preconditions()
    if missing:
        raise Unmeasurable(missing, run)

    total = stored_bytes(run)
    return {
        "metric": STORED_BYTES_METRIC,
        "value": total / run.readings,
        "unit": "byte/reading",
        "seed": run.seed,
        "run_id": run.run_id,
        "tool": "tools/measure_row_bytes.py",
        "scenario": SCENARIO,
        "subject": SUBJECT,
        "table_format": EVENT_TABLE.table_format,
        "writer": EVENT_TABLE.writer,
        "compression": EVENT_TABLE.compression,
        "compression_level": EVENT_TABLE.compression_level,
        "readings": run.readings,
        "events": run.events,
        "stored_bytes_total": total,
        "log_hash": run.log_hash,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--seed", type=int, default=DEFAULT_SEED)
    parser.add_argument("--readings", type=int, default=DEFAULT_READINGS)
    parser.add_argument(
        "--out",
        type=Path,
        default=ARTIFACT_DIR / f"{STORED_BYTES_METRIC}.json",
        help="where the measurement artifact is written on success",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="print the record, or the refusal, as JSON on stdout",
    )
    args = parser.parse_args(argv)

    if args.readings < 1:
        parser.error(f"--readings must be at least 1, got {args.readings}")
    if args.seed < 0:
        parser.error(f"--seed must not be negative, got {args.seed}")

    try:
        record = measure(seed=args.seed, readings=args.readings)
    except Unmeasurable as refusal:
        run = refusal.run or build_run(seed=args.seed, readings=args.readings)
        report = {
            "metric": STORED_BYTES_METRIC,
            "measured": False,
            "value": None,
            "seed": run.seed,
            "run_id": run.run_id,
            "readings": run.readings,
            "events": run.events,
            "log_hash": run.log_hash,
            "missing": refusal.missing,
        }
        if args.json:
            print(json.dumps(report, indent=2, sort_keys=True))
        else:
            print(f"scenario {SCENARIO} recorded {run.events} events at seed {run.seed}")
            print(f"run id {run.run_id}")
            print(f"log hash {run.log_hash}")
            print(f"rows in the canonical total order: {len(run.rows)}")
        print(
            f"\nCANNOT MEASURE {STORED_BYTES_METRIC}. "
            f"{len(refusal.missing)} precondition(s) absent:",
            file=sys.stderr,
        )
        for index, item in enumerate(refusal.missing, start=1):
            print(f"  {index}. {item}", file=sys.stderr)
        print(
            "\nNo value is written and no artifact is produced. The marker in "
            "docs/design/foundations.md stays TBD until every line above is gone, "
            "because a number here that nothing produced is the one defect this "
            "repository refuses outright.",
            file=sys.stderr,
        )
        return 3

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(record, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    if args.json:
        print(json.dumps(record, indent=2, sort_keys=True))
    else:
        print(f"{record['metric']} = {record['value']} {record['unit']}")
        print(f"seed {record['seed']}, run id {record['run_id']}")
        print(f"wrote {args.out.relative_to(REPO_ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
