---
title: twinflow-twin API
description: Every public symbol twinflow-twin owns, listed as boundary rule A1.4 asks, so each name has exactly one owning package.
topic_type: reference
audience: contributors
---

# twinflow-twin API

Boundary rule A1.4 gives every public symbol exactly one owning package. These
are the names this package owns.

| Symbol                   | Kind     | What it is                                                             |
| ------------------------ | -------- | ---------------------------------------------------------------------- |
| `run_station_line`       | function | Run one receiving and putaway line and return its tape and end state   |
| `StationLineSpec`        | class    | The modeled line: two stations, the buffer between them, the arrivals  |
| `StationSpec`            | class    | One station: id, kind, zone, capacity, and service-time distribution   |
| `DistributionSpec`       | class    | A named distribution family and its parameters, scaled in seconds      |
| `PalletArrival`          | class    | One line of the exogenous arrival trace                                |
| `StationRun`             | class    | One execution: tape, ledger, state traces, end tick, and facility hash |
| `MaterialLedger`         | class    | The INV-TWIN-01 conservation ledger at the end of a run                |
| `StateSpell`             | class    | One uninterrupted spell of a resource in one state, in integer ticks   |
| `PalletState`            | enum     | The pallet states a receiving and putaway line can reach               |
| `StationState`           | enum     | The resource states a station on this line can occupy                  |
| `SimulationClock`        | protocol | The kernel clock port plus the advance method a scheduler needs        |
| `IllegalTransitionError` | class    | Raised when a pallet moves between states the table does not connect   |
| `check_transition`       | function | Raise unless the declared table connects two pallet states             |
| `PALLET_TRANSITIONS`     | constant | The declared pallet transition table of design section 3.2             |
| `RECEIVING_STREAM`       | constant | `twin.receiving.unload_duration`, the unload service stream            |
| `SERVICE_STREAM`         | constant | `twin.station.{station_id}.service`, the station service stream        |
| `__version__`            | constant | The distribution version, read by the build so the two cannot disagree |

Every id field on these models matches the identifier pattern of
`schemas/config/facility/v1.json`, which is lower-case letters, digits, and
hyphens. The pattern itself stays private to `twinflow.twin.station`, because
boundary rule A1.4 gives one public name one owning package and this one is
owned elsewhere.

## What a run writes

`run_station_line` returns a `StationRun` and writes no file. The tape is a
tuple of `twinflow.schemas.Envelope`, in emission order, which is also the
canonical `(sim_ts, producer_id, seq)` order of doctrine D-07.

| Subject                            | Carries                                                      |
| ---------------------------------- | ------------------------------------------------------------ |
| `twinflow.twin.model_built`        | Facility hash, station count, resource count, stream names   |
| `twinflow.twin.pallet_created`     | Pallet id, SKU, quantity, and the state it entered           |
| `twinflow.twin.activity_started`   | Case id, activity, resource, and the pallet quantity         |
| `twinflow.twin.activity_completed` | The same, plus the service duration in ticks and in seconds  |
| `twinflow.twin.resource_state`     | The spell that closed, its length, and the state that opened |
| `twinflow.twin.wip_sampled`        | Units in system and units queued in the staging buffer       |

One sample of `wip_sampled` lands on every change rather than on a timer, so a
reader integrates the step function exactly instead of polling it.

## Behavior worth knowing

`DistributionSpec` refuses a gamma, lognormal, or Weibull family with no shape
parameter, and refuses an exponential family that carries one. A sampler that
silently dropped a declared parameter would run a model the config author
cannot read back.

`StationLineSpec` refuses two stations with one id, a repeated pallet id, and
an arrival trace out of order. The trace is exogenous and is replayed verbatim,
so sorting it here would let a mis-authored trace produce a plausible run.

A full staging buffer blocks the receiving station rather than growing an
unbounded queue. The blocked spell is recorded as `IDLE_BLOCKED`, a distinct
state from `RUNNING`. A six-big-losses reader can then attribute the loss to
the downstream constraint that caused it.

`StationRun.traces` holds one spell list per station, and the spells partition
`[0, end_tick]` with no gap and no overlap. That closure is INV-TWIN-09, it
holds in integer ticks rather than floats, and it is what makes a utilization
denominator checkable.

`run_station_line` takes an optional `clock` and an optional `run_id`. The
default run id is the line id and the seed, so it is a function of the inputs.
A generated id would put a fresh value into every event, and no two runs of one
seed would ever hash the same.

## Re-exports

None.
