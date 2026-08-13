---
title: twinflow-twin
description: The discrete-event process twin of receiving and putaway, built on SimPy and driven by an injected clock and named random streams.
topic_type: concept
audience: contributors
---

# twinflow-twin

A warehouse line as a discrete-event model. Pallets arrive on a declared trace,
claim a receiving server, wait in a bounded staging buffer, claim a putaway
server, and reach storage. Every state change of every pallet and every station
lands on an event tape, and nothing else in this package reads the model's
internals.

## Install

```bash
pip install twinflow-twin
```

## Use

```python
from datetime import UTC, datetime

from twinflow.twin import (
    DistributionSpec,
    PalletArrival,
    StationLineSpec,
    StationSpec,
    run_station_line,
)

line = StationLineSpec(
    line_id="micro-fulfillment",
    tick_hz=1_000,
    epoch=datetime(2026, 1, 1, tzinfo=UTC),
    receiving=StationSpec(
        station_id="recv-01",
        kind="receiving",
        zone_id="dock-a",
        capacity=2,
        service_time=DistributionSpec(family="lognormal", scale_s=210.0, shape=0.4),
    ),
    putaway=StationSpec(
        station_id="put-01",
        kind="putaway",
        zone_id="storage-a",
        capacity=3,
        service_time=DistributionSpec(family="gamma", scale_s=95.0, shape=2.0),
    ),
    staging_capacity=12,
    arrivals=(
        PalletArrival(pallet_id="plt-0001", sku_id="sku-0001", qty_units=48, release_tick=0),
        PalletArrival(pallet_id="plt-0002", sku_id="sku-0002", qty_units=36, release_tick=90_000),
    ),
)

run = run_station_line(line, seed=42)
print(run.end_tick, run.ledger.is_balanced, len(run.events))
```

## Why SimPy

Decision D1 in `ARCHITECTURE.md` pins SimPy as the discrete-event framework: a
process-based simulation library over standard Python, whose processes are
Python generator functions. One pallet's journey reads as one function, which
is why the blocking rule below is four lines rather than a state machine
nobody wants to review.

The second half of that decision matters more. SimPy's core is a virtual clock
over a deterministic event queue, so the same scheduler that runs the modeled
factory also runs the software under test. The deterministic simulation testing
of `ARCHITECTURE.md` section 2 arrives as a property of a dependency this
project needed anyway.

## Determinism

Nothing here reads a wall clock or builds a bit generator. Time comes from the
injected clock port in `twinflow-kernel`, and randomness comes from
`twinflow-rng` by stream name. This package draws from two streams and declares
both, so a reader can find every source of randomness in one place:

| Stream                              | Quantity                |
| ----------------------------------- | ----------------------- |
| `twin.receiving.unload_duration`    | Unload time per pallet  |
| `twin.station.{station_id}.service` | Putaway time per pallet |

A generator is taken once per stream when the model is built, never once per
draw. The registry derives a generator from the stream name on every handout,
so a model that called it per draw would restart the stream and hand every
pallet the same number. That model reproduces byte for byte and simulates a
line with no variability at all, so the determinism gate cannot see it.
`test_each_pallet_draws_its_own_service_time` is the assertion that can.

Service times are sampled as floats and rounded once, at the point of
scheduling, half to even. Rounding in one place is what lets the resource state
trace close its window exactly in integer arithmetic.

## No clamping

Every distribution family offered here already has the support a duration has,
which is strictly positive and right-skewed. So there is no sigma cap, no tail
clipping, and no clamp of a sampled value back into range, per
`ARCHITECTURE.md` section 3. A four-hour unload is a real event in a real
building and this model produces it at its real rate.

Physical impossibilities are caught by property tests rather than prevented by
runtime guards. Material conservation, a monotone event clock, non-negative
queues, and exact state-trace closure each have a Hypothesis test in
`tests/test_station_invariants.py`. A clamp would hide a wrong distribution
behind plausible output, and an assertion names it.

## What this package does not do yet

The metric engine, the bottleneck detector, and the value-stream summary of
`docs/design/twin-core.md` read the tape this package writes and land with
their own work packages. Dock doors, scan points, conveyance, and sortation sit
between staging and putaway in the full model, and the pallet state machine
here joins those two states directly until they arrive.

The public symbols are listed in [API.md](API.md).
