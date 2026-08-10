"""Generate the cross-language known-answer corpus of section A.7.

    uv run python tools/gen_rng_kat.py            write the corpus
    uv run python tools/gen_rng_kat.py --check    regenerate in memory and diff

The corpus records what numpy does rather than what the specification says
numpy does, which is why a disagreement between the two is itself a finding
rather than a reason to edit the document.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from twinflow.rng import generator_for

FIXTURE = Path(__file__).resolve().parents[1] / "tests" / "fixtures" / "rng_kat.json"

DRAWS_PER_CASE = 16
BASE_SEEDS = (0, 42, 2**64 - 1)
REPLICATION_INDEXES = (0, 1)

AMR_IDS = ("AMR-001", "AMR-014", "AMR-047", "AMR-128", "AMR-501", "AMR-999")
SENSOR_IDS = (
    "CNV-02-VIB-01",
    "CNV-07-TMP-03",
    "DOK-01-PRS-02",
    "AMR-014-CUR-01",
    "PLT-03-VIB-09",
)
WORKER_IDS = ("W-0001", "W-0231", "W-1024", "W-4096")
FAULT_IDS = (
    "F-MECH-BEARING",
    "F-CONV-JAM",
    "F-NET-PARTITION",
    "F-DEV-CLOCKDRIFT",
    "F-SENS-DRIFT",
)

# Form 1 of the A.2 grammar, <domain>.<subsystem>.<quantity>, plus the one
# stream that materialises the fault schedule.
FIXED_STREAMS = (
    "twin.receiving.unload_duration",
    "twin.receiving.scan_duration",
    "twin.receiving.dock_wait",
    "twin.putaway.travel_duration",
    "twin.picking.pick_duration",
    "twin.packing.pack_duration",
    "twin.shipping.load_duration",
    "twin.qa.inspection_duration",
    "sensor.vibration.noise",
    "sensor.temperature.noise",
    "sensor.current.noise",
    "sensor.pressure.noise",
    "supply.inbound.truck_interarrival",
    "supply.supplier.otif_outcome",
    "demand.orders.line_count",
    "schedule.faults",
)


def stream_names() -> tuple[str, ...]:
    """The 64 names, in a fixed order, spanning every grammar form of A.2."""
    names: list[str] = list(FIXED_STREAMS)

    # Form 2, <domain>.<subsystem>.<entity_id>.<quantity>.
    names.extend(f"twin.amr.{amr_id}.task_travel" for amr_id in AMR_IDS)
    names.extend(f"sensor.vibration.{sensor_id}.noise" for sensor_id in SENSOR_IDS)
    names.extend(f"device.agent.{sensor_id}.publish_jitter" for sensor_id in SENSOR_IDS)

    # Form 3, provision.<domain>.<entity_id>.<attribute>.
    names.extend(f"provision.workforce.{worker_id}.productivity_effect" for worker_id in WORKER_IDS)
    names.extend(f"provision.fleet.{amr_id}.drift_rate" for amr_id in AMR_IDS)
    names.extend(f"provision.sensor.{sensor_id}.manufacturing_offset" for sensor_id in SENSOR_IDS)
    names.append("provision.supply.SUP-001.true_otif")

    # Form 4, fault.<fault_id>.<instance_id>.<quantity>.
    names.extend(f"fault.{fault_id}.0001.progression" for fault_id in FAULT_IDS)
    names.extend(f"fault.{fault_id}.0002.onset" for fault_id in FAULT_IDS)
    names.extend(f"fault.{fault_id}.0003.magnitude" for fault_id in FAULT_IDS)
    names.append("fault.F-MECH-BEARING.0004.duration")

    if len(names) != 64:
        raise SystemExit(f"expected 64 stream names, built {len(names)}")
    if len(set(names)) != 64:
        raise SystemExit("the 64 stream names are not distinct")
    return tuple(names)


def build() -> dict:
    cases = []
    for stream in stream_names():
        for base_seed in BASE_SEEDS:
            for replication_index in REPLICATION_INDEXES:
                raw_gen = generator_for(
                    stream, base_seed=base_seed, replication_index=replication_index
                )
                double_gen = generator_for(
                    stream, base_seed=base_seed, replication_index=replication_index
                )
                cases.append(
                    {
                        "stream": stream,
                        "base_seed": base_seed,
                        "replication_index": replication_index,
                        # Decimal strings: a JSON number above 2**53 is not
                        # exact in every parser this file has to survive.
                        "raw_uint64": [
                            str(int(raw_gen.bit_generator.random_raw()))
                            for _ in range(DRAWS_PER_CASE)
                        ],
                        # JSON numbers, written by Python's shortest
                        # round-trip repr, which any IEEE-754 parser reads
                        # back to the same bits.
                        "doubles": [double_gen.random() for _ in range(DRAWS_PER_CASE)],
                    }
                )

    return {
        "format": 1,
        "generated_by": "tools/gen_rng_kat.py",
        "derivation": "docs/design/variability-and-faults.md section A.7",
        "person": "twinflow-rng",
        "digest_size": 16,
        "bit_generator": "PCG64DXSM",
        "draws_per_case": DRAWS_PER_CASE,
        "cases": cases,
    }


def render(corpus: dict) -> str:
    return json.dumps(corpus, indent=2, sort_keys=True) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--check",
        action="store_true",
        help="regenerate in memory and fail when it differs from the file",
    )
    args = parser.parse_args()

    rendered = render(build())

    if args.check:
        if not FIXTURE.is_file():
            print(f"missing corpus at {FIXTURE}", file=sys.stderr)
            return 1
        on_disk = FIXTURE.read_text(encoding="utf-8")
        if on_disk != rendered:
            print(
                f"{FIXTURE} does not match a fresh generation. Either the "
                "derivation moved or numpy did, and both need a decision.",
                file=sys.stderr,
            )
            return 1
        print(f"{FIXTURE} matches a fresh generation")
        return 0

    FIXTURE.parent.mkdir(parents=True, exist_ok=True)
    FIXTURE.write_text(rendered, encoding="utf-8")
    print(f"wrote {FIXTURE}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
