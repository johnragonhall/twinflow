"""One receiving station and one putaway station, as a discrete-event model.

WHAT THIS MODULE OWNS
---------------------
Requirement 1 asks for a discrete-event model of receiving and putaway with
realistic variability. This module is the station half of that: pallets arrive
on an exogenous trace, claim a receiving server, occupy a bounded staging
buffer, claim a putaway server, and reach storage. The implementation contract
is docs/design/twin-core.md, and the parts it implements are 3.1 (Station and
its capacity and buffer fields), 3.2 (the pallet state machine, INV-TWIN-01
material conservation), 3.3 (the resource state trace and INV-TWIN-09), 4.1
(the published subjects), 5.1 (the model in one paragraph), and the streams,
integer clock, and rounding rule of 5.2.

The metric engine of 5.4, the bottleneck detector of 5.5, dock doors, scan
points, conveyance, and sortation are named in the same document and are not
here. They land with their own work packages, and this module leaves the tape
they read rather than computing their answers early.

WHY SIMPY
---------
Decision D1 in ARCHITECTURE.md pins SimPy 4 as the discrete-event framework:
"a process-based discrete-event simulation framework based on standard Python"
whose "processes are defined by Python generator functions". Both halves are
load-bearing here. The process style is what lets one pallet's journey read as
one function, and the standard-Python constraint is what lets the same virtual
clock schedule the twin and the software under test, which is the whole reason
section 2 of ARCHITECTURE.md calls the deterministic scheduler a property of a
dependency the project needed anyway.

WHY THE CLOCK AND THE GENERATOR ARE ARGUMENTS
---------------------------------------------
Nothing here reads a wall clock or constructs a bit generator. Time comes from
the injected clock port and randomness comes from the twinflow.rng registry by
stream name, which is what doctrine D-02 and milestone C1 require and what
scripts/checks/nondeterminism-gate.sh enforces. A generator is taken once per
stream at build time rather than once per pallet, because the registry derives
a fresh generator from the stream name on every handout and taking one per
pallet would restart the stream and hand every pallet the same draw.

WHAT THIS MODULE DELIBERATELY DOES NOT DO
------------------------------------------
It does not clamp. ARCHITECTURE.md section 3 forbids a sigma cap, tail
clipping, and any clamp of a sampled value back into range, because a clamp
hides a wrong distribution behind plausible output. Every family offered here
already has the support a duration has, which is strictly positive and
right-skewed, so there is nothing to clamp. The physical invariants are
asserted in tests/test_station_invariants.py rather than enforced at runtime,
which is the same rule stated from the other side.

A KNOWN GAP, STATED RATHER THAN HIDDEN
---------------------------------------
Section 5.2 specifies `DeterministicEnv`, a kernel-owned simpy.Environment
subclass whose heap key is (time, priority_class, producer_id, seq), so that
several producers scheduling at one tick order canonically. That class is a
kernel deliverable and has not landed. This line has exactly one producer, so
SimPy's own (time, priority, insertion counter) key already gives one order per
seed, and the tape is checked against the D-07 total order on every run. When
the kernel ships the subclass, `_Line` takes it and the tie-break stops being
an in-process property.
"""

from __future__ import annotations

import hashlib
from collections.abc import Generator
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import StrEnum
from typing import Any, Literal, Protocol

import numpy as np
import simpy
from pydantic import BaseModel, ConfigDict, Field

from twinflow.kernel import DEFAULT_TICK_HZ, SimClock, SimInstant, TickResolution
from twinflow.rng import StreamRegistry
from twinflow.schemas import Envelope, ProducerId

#: The source URI every event here carries, per envelope section 3.4:
#: /twinflow/<package>/<component>.
SOURCE = "/twinflow/twin/station"

#: The envelope schema these events validate against. The per-subject payload
#: schemas under /schemas/twin/ are generated from their models and publish
#: with the schema-registry work package, so this names the envelope only.
DATA_SCHEMA = "twinflow:schemas/envelope/v1.json"

#: The process role publishing this tape. A closed set, from invariant E3.
PRODUCER: ProducerId = "sim"

#: Unload service time per pallet, from the stream table in 5.2. It carries no
#: placeholder because the table names it once for the receiving activity
#: rather than once per station.
RECEIVING_STREAM = "twin.receiving.unload_duration"

#: Station service time, from the same table. The placeholder is filled with
#: the station id, so adding a station perturbs no existing station's draws.
SERVICE_STREAM = "twin.station.{station_id}.service"

#: Lower-case, digits, and hyphens, matching schemas/config/facility/v1.json.
#: An id reaches a stream name and an event payload, so the character set is
#: fixed here rather than left to a profile author.
IDENTIFIER = r"^[a-z0-9][a-z0-9-]{0,63}$"


class IllegalTransitionError(ValueError):
    """A pallet was asked to move between states the machine does not connect."""


class PalletState(StrEnum):
    """The subset of section 3.2 a receiving and putaway line can reach.

    SCANNED, IN_CONVEYANCE, and SORTED sit between STAGED and AWAITING_PUTAWAY
    in the full machine. They need a scan point, a conveyor, and a sorter, none
    of which this line has, so the table below joins STAGED to
    AWAITING_PUTAWAY directly and the later work packages reopen the segment.
    """

    EXPECTED = "EXPECTED"
    ON_TRUCK = "ON_TRUCK"
    UNLOADING = "UNLOADING"
    STAGED = "STAGED"
    AWAITING_PUTAWAY = "AWAITING_PUTAWAY"
    STORED = "STORED"


#: The declared transition table of section 3.2. A tuple of pairs rather than a
#: mapping of sets, applying D-03: nothing whose iteration order can reach a
#: control decision is a set.
PALLET_TRANSITIONS: tuple[tuple[PalletState, PalletState], ...] = (
    (PalletState.EXPECTED, PalletState.ON_TRUCK),
    (PalletState.ON_TRUCK, PalletState.UNLOADING),
    (PalletState.UNLOADING, PalletState.STAGED),
    # The collapsed conveyance segment described in PalletState.
    (PalletState.STAGED, PalletState.AWAITING_PUTAWAY),
    (PalletState.AWAITING_PUTAWAY, PalletState.STORED),
)


def check_transition(from_state: PalletState, to_state: PalletState) -> None:
    """Raise unless the machine connects these two states.

    Section 3.2 says an illegal transition raises rather than logs. A logged
    one produces a tape that reads as a real run and a value stream with a leg
    missing, which is the failure a reader cannot see.
    """
    for source, target in PALLET_TRANSITIONS:
        if source is from_state and target is to_state:
            return
    raise IllegalTransitionError(
        f"{from_state} does not connect to {to_state}; the declared table is "
        f"{[f'{source}->{target}' for source, target in PALLET_TRANSITIONS]}"
    )


class StationState(StrEnum):
    """The subset of the section 3.3 resource states this line can occupy.

    The precedence when a multi-server station is partly blocked is declared
    here and applied in one place: blocked beats running, and running beats
    idle. A station holding a finished pallet it cannot hand on is constrained
    by its downstream neighbor, and reporting it as running would credit the
    downstream constraint to this station's utilization.
    """

    IDLE_BLOCKED = "IDLE_BLOCKED"
    IDLE_NO_WORK = "IDLE_NO_WORK"
    IDLE_STARVED = "IDLE_STARVED"
    RUNNING = "RUNNING"


@dataclass(frozen=True)
class StateSpell:
    """One uninterrupted spell of a resource in one state, in integer ticks."""

    state: StationState
    start_tick: int
    end_tick: int

    @property
    def duration_ticks(self) -> int:
        return self.end_tick - self.start_tick


@dataclass(frozen=True)
class MaterialLedger:
    """The INV-TWIN-01 conservation ledger at the end of a run.

    Scrap is a declared column rather than an omitted one, because section 3.2
    forbids silent disposal: a unit that leaves the system without a scrap
    event is a defect, and a ledger with no scrap column could not say so.
    """

    units_received: int
    units_in_system: int
    units_putaway: int
    units_scrapped: int

    @property
    def is_balanced(self) -> bool:
        return self.units_received == (
            self.units_in_system + self.units_putaway + self.units_scrapped
        )


class DistributionSpec(BaseModel):
    """A named distribution and its parameters, per ARCHITECTURE.md section 3.

    Every family here has support on the strictly positive reals, which is the
    correct support for a duration: a service time is never zero or negative
    and its long right tail is where the disruptive events live. So no member
    of this class clamps, truncates, or caps anything.

    `scale_s` is the family's scale in seconds. For lognormal it is the median,
    because the draw is `scale_s * exp(shape * Z)`; naming it the mean would be
    wrong by a factor of `exp(shape**2 / 2)` and config authors would not see
    the difference until the takt was wrong.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    family: Literal["exponential", "gamma", "lognormal", "weibull"]
    scale_s: float = Field(gt=0)
    #: Dimensionless. Required by every family except exponential, which has
    #: none, and refused there rather than ignored: a parameter the sampler
    #: silently drops is a parameter the config author believes is in force.
    shape: float | None = Field(default=None, gt=0)

    def model_post_init(self, _context: object) -> None:
        if self.family == "exponential" and self.shape is not None:
            raise ValueError(
                "the exponential family takes no shape parameter; drop shape or "
                "choose gamma or weibull, which have one"
            )
        if self.family != "exponential" and self.shape is None:
            raise ValueError(
                f"the {self.family} family needs a shape parameter, and there is no "
                "default worth guessing: section 3 requires every distribution to be "
                "named in config with its parameters"
            )

    def sample_s(self, generator: np.random.Generator) -> float:
        """One draw in seconds, untouched between numpy and the caller."""
        if self.family == "exponential":
            return float(generator.exponential(self.scale_s))

        # Every remaining family carries a shape: `model_post_init` refuses one
        # that does not, so reading it into a local carries that construction
        # rule into the sampler rather than asserting it a second time.
        shape = self.shape
        if shape is None:  # pragma: no cover - refused at construction
            raise ValueError(f"the {self.family} family needs a shape parameter")

        if self.family == "gamma":
            return float(generator.gamma(shape, self.scale_s))
        if self.family == "lognormal":
            return self.scale_s * float(generator.lognormal(0.0, shape))
        return self.scale_s * float(generator.weibull(shape))


class PalletArrival(BaseModel):
    """One line of the exogenous arrival trace.

    Arrival time is exogenous, per 3.2 and 5.13, and this line takes it as
    declared data rather than sampling it. The truck and dock-door model that
    produces the trace in a full facility is a later work package, and a stream
    invented here to stand in for it would be randomness the 5.2 table never
    declared.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    pallet_id: str = Field(pattern=IDENTIFIER)
    sku_id: str = Field(pattern=IDENTIFIER)
    qty_units: int = Field(ge=1)
    release_tick: int = Field(ge=0)


class StationSpec(BaseModel):
    """One station, per section 3.1, narrowed to the fields this line uses."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    station_id: str = Field(pattern=IDENTIFIER)
    #: From the station-type enum of schemas/config/facility/v1.json. It also
    #: selects the idle classification: a receiving station with nothing to do
    #: has no work, while a putaway station with nothing to do is starved by
    #: its upstream neighbor, and the six-big-losses attribution needs the two
    #: told apart.
    kind: Literal["receiving", "putaway"]
    zone_id: str = Field(pattern=IDENTIFIER)
    capacity: int = Field(ge=1)
    service_time: DistributionSpec

    @property
    def idle_state(self) -> StationState:
        if self.kind == "receiving":
            return StationState.IDLE_NO_WORK
        return StationState.IDLE_STARVED


class StationLineSpec(BaseModel):
    """The whole modeled line: two stations and the buffer between them."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    line_id: str = Field(pattern=IDENTIFIER)
    tick_hz: int = DEFAULT_TICK_HZ
    #: The sim epoch. Required rather than defaulted to the current instant,
    #: because a default read from the wall clock would put a fresh value into
    #: every event and no two runs of one seed would ever hash the same.
    epoch: datetime
    receiving: StationSpec
    putaway: StationSpec
    #: Pallets, not units. Section 3.1 keeps capacity and buffer capacity
    #: separate because a full buffer blocks the upstream station, and that
    #: blocking is recorded as its own state so the loss can be attributed.
    staging_capacity: int = Field(ge=1)
    arrivals: tuple[PalletArrival, ...] = Field(min_length=1)

    def model_post_init(self, _context: object) -> None:
        if self.tick_hz not in TickResolution:
            raise ValueError(f"tick_hz must be one of {TickResolution}, got {self.tick_hz}")
        if self.receiving.kind != "receiving":
            raise ValueError(f"the receiving station is of kind {self.receiving.kind!r}")
        if self.putaway.kind != "putaway":
            raise ValueError(f"the putaway station is of kind {self.putaway.kind!r}")
        if self.receiving.station_id == self.putaway.station_id:
            raise ValueError(
                f"the two stations need distinct ids, and both are "
                f"{self.receiving.station_id!r}: they would share a stream name and a "
                "state trace, so one station's utilization would be reported for both"
            )
        seen: dict[str, int] = {}
        previous = -1
        for index, arrival in enumerate(self.arrivals):
            if arrival.pallet_id in seen:
                raise ValueError(
                    f"pallet id {arrival.pallet_id!r} appears at "
                    f"arrivals[{seen[arrival.pallet_id]}] and arrivals[{index}]; "
                    "the pallet id is the process-mining case id"
                )
            seen[arrival.pallet_id] = index
            if arrival.release_tick < previous:
                raise ValueError(
                    f"arrivals[{index}] has release_tick {arrival.release_tick}, before "
                    f"its predecessor's {previous}. The trace is exogenous and is replayed "
                    "verbatim, so sorting it here would let a mis-authored trace produce a "
                    "plausible run and never surface the authoring error"
                )
            previous = arrival.release_tick

    @property
    def facility_hash(self) -> str:
        """A hash of the modeled line, for a reader diffing two runs.

        It covers the configuration and not the package version, per 4.1: a
        release that changes no behavior must not invalidate a golden hash.
        """
        return hashlib.blake2b(
            self.model_dump_json().encode("utf-8"), digest_size=16, person=b"twinflow-twin"
        ).hexdigest()


class SimulationClock(Protocol):
    """The kernel Clock port, plus the one method a scheduler needs.

    `twinflow.kernel.Clock` reads sim time. A component that also drives the
    schedule has to move it, and `SimClock.advance_to` is that method. The port
    is refined here rather than in the kernel because the kernel's own
    scheduler seam lands with `DeterministicEnv` in 5.2, and widening a
    published protocol ahead of its implementation is how a name nobody has
    tested reaches the contract.
    """

    @property
    def tick_hz(self) -> int:
        """Ticks per simulated second, one of TickResolution."""
        ...

    def now(self) -> SimInstant:
        """The current instant, non-decreasing within a run."""
        ...

    def advance_to(self, instant: SimInstant) -> None:
        """Move the clock forward, or leave it where it is. Never backwards."""
        ...


@dataclass(frozen=True)
class StationRun:
    """One execution of the line: the tape it wrote and the state it ended in."""

    run_id: str
    seed: int
    facility_hash: str
    tick_hz: int
    end_tick: int
    events: tuple[Envelope, ...]
    ledger: MaterialLedger
    #: Per station, the full partition of [0, end_tick] into state spells.
    #: INV-TWIN-09 says the durations sum to the window exactly, in integer
    #: arithmetic, which is what makes a utilization denominator checkable.
    traces: dict[str, tuple[StateSpell, ...]]
    max_staged_pallets: int


class _Tape:
    """The append-only writer of this run's events.

    Sequence numbers are dense per producer and the event id is derived from
    the run and the sequence, per D-07 and invariant E2. A generated id would
    put a fresh value into every event and make VAL-GATE-DET-001 impossible to
    pass rather than easy to fail.
    """

    def __init__(self, *, run_id: str, epoch: datetime, clock: SimulationClock) -> None:
        self._run_id = run_id
        self._epoch = epoch
        self._clock = clock
        self._seq = 0
        self.events: list[Envelope] = []

    def emit(self, event_type: str, subject: str | None, data: dict) -> None:
        ticks = int(self._clock.now())
        self.events.append(
            Envelope(
                specversion="1.0",
                id=f"{self._run_id}-{PRODUCER}-{self._seq}",
                source=SOURCE,
                type=event_type,
                time=self._epoch + timedelta(seconds=ticks / self._clock.tick_hz),
                datacontenttype="application/json",
                dataschema=DATA_SCHEMA,
                subject=subject,
                twinflowsimts=str(ticks),
                twinflowrunid=self._run_id,
                twinflowproducerid=PRODUCER,
                twinflowseq=str(self._seq),
                data=data,
            )
        )
        self._seq += 1


class _StationRuntime:
    """Live state for one station: its server counts and its state trace."""

    def __init__(self, spec: StationSpec) -> None:
        self.spec = spec
        self.busy = 0
        self.blocked = 0
        self.state = spec.idle_state
        self.spell_start = 0
        self.spells: list[StateSpell] = []

    def observed(self) -> StationState:
        if self.blocked:
            return StationState.IDLE_BLOCKED
        if self.busy:
            return StationState.RUNNING
        return self.spec.idle_state


class _Line:
    """The SimPy model of one receiving and putaway line."""

    def __init__(
        self,
        spec: StationLineSpec,
        *,
        seed: int,
        replication_index: int,
        run_id: str,
        clock: SimulationClock,
    ) -> None:
        self.spec = spec
        self.seed = seed
        self.clock = clock
        self.run_id = run_id
        self.env = simpy.Environment()

        self.streams = StreamRegistry(base_seed=seed, replication_index=replication_index)
        self.streams.register(RECEIVING_STREAM)
        self.streams.register(SERVICE_STREAM)
        # One generator per stream, taken once. See the module docstring.
        self.generators = {
            spec.receiving.station_id: self.streams.get(RECEIVING_STREAM),
            spec.putaway.station_id: self.streams.get(
                SERVICE_STREAM, station_id=spec.putaway.station_id
            ),
        }

        self.tape = _Tape(run_id=run_id, epoch=spec.epoch, clock=clock)
        self.receiving = _StationRuntime(spec.receiving)
        self.putaway = _StationRuntime(spec.putaway)
        self.unload_servers = simpy.Resource(self.env, capacity=spec.receiving.capacity)
        self.staging = simpy.Store(self.env, capacity=spec.staging_capacity)

        self.pallets = {arrival.pallet_id: arrival for arrival in spec.arrivals}
        self.pallet_state = {arrival.pallet_id: PalletState.EXPECTED for arrival in spec.arrivals}
        self.units_received = 0
        self.units_in_system = 0
        self.units_putaway = 0
        self.units_staged = 0
        self.max_staged_pallets = 0

    # Time, tape, and state bookkeeping.

    def _at_now(self) -> int:
        """Bring the injected clock up to the scheduler and report the tick."""
        now = int(self.env.now)
        self.clock.advance_to(SimInstant(now))
        return now

    def _emit(self, event_type: str, subject: str | None, data: dict) -> None:
        self._at_now()
        self.tape.emit(event_type, subject, data)

    def _transition(self, pallet_id: str, to_state: PalletState) -> None:
        check_transition(self.pallet_state[pallet_id], to_state)
        self.pallet_state[pallet_id] = to_state

    def _refresh(self, station: _StationRuntime) -> None:
        """Close the current spell and open the next one, when the state moved."""
        now = self._at_now()
        observed = station.observed()
        if observed is station.state:
            return
        spell = StateSpell(state=station.state, start_tick=station.spell_start, end_tick=now)
        station.spells.append(spell)
        self._emit(
            "twinflow.twin.resource_state",
            station.spec.station_id,
            {
                "resource_id": station.spec.station_id,
                "state": str(observed),
                "previous_state": str(spell.state),
                "duration_ticks": spell.duration_ticks,
                "duration_s": spell.duration_ticks / self.spec.tick_hz,
                # The six-big-losses classification needs
                # metrics.minor_stop_threshold_s, which belongs to the metric
                # engine of 5.4. Naming the field and leaving it null is how
                # the consumer stays able to fill it without a schema change.
                "loss_class": None,
            },
        )
        station.state = observed
        station.spell_start = now

    def _sample_wip(self) -> None:
        """Time-weighted WIP is integrated from these, so one lands per change.

        The sample is attributed to the putaway station because the staging
        buffer is its inbound buffer, which is the resource whose queue the
        number describes.
        """
        self._emit(
            "twinflow.twin.wip_sampled",
            self.spec.putaway.station_id,
            {
                "zone_id": self.spec.putaway.zone_id,
                "station_id": self.spec.putaway.station_id,
                "units": self.units_in_system,
                "queue_units": self.units_staged,
            },
        )

    def _service_ticks(self, station: _StationRuntime) -> int:
        """One service draw, rounded once, at the point of scheduling.

        Section 5.2 puts the rounding here and nowhere else, under half-to-even,
        which is what Python's round() does. Rounding once is what makes the
        INV-TWIN-09 trace close exactly in integer arithmetic.
        """
        seconds = station.spec.service_time.sample_s(self.generators[station.spec.station_id])
        return round(seconds * self.spec.tick_hz)

    def _activity(
        self, event_type: str, pallet_id: str, station: _StationRuntime, **extra: object
    ) -> None:
        payload: dict = {
            "case_id": pallet_id,
            "activity": "unload" if station.spec.kind == "receiving" else "putaway",
            "resource_id": station.spec.station_id,
            "station_id": station.spec.station_id,
            "operator_id": None,
            "attrs": {"qty_units": self.pallets[pallet_id].qty_units},
        }
        payload.update(extra)
        self._emit(event_type, pallet_id, payload)

    # -- the two SimPy processes -------------------------------------------

    def _pallet_process(self, arrival: PalletArrival) -> Generator[simpy.Event, None, None]:
        """One pallet from the inbound trailer to the staging buffer."""
        if arrival.release_tick > 0:
            yield self.env.timeout(arrival.release_tick)

        self._transition(arrival.pallet_id, PalletState.ON_TRUCK)
        self.units_received += arrival.qty_units
        self.units_in_system += arrival.qty_units
        self._emit(
            "twinflow.twin.pallet_created",
            arrival.pallet_id,
            {
                "pallet_id": arrival.pallet_id,
                "sku_id": arrival.sku_id,
                "qty_units": arrival.qty_units,
                "state": str(PalletState.ON_TRUCK),
            },
        )
        self._sample_wip()

        with self.unload_servers.request() as slot:
            yield slot
            self.receiving.busy += 1
            self._refresh(self.receiving)
            self._transition(arrival.pallet_id, PalletState.UNLOADING)
            self._activity("twinflow.twin.activity_started", arrival.pallet_id, self.receiving)

            ticks = self._service_ticks(self.receiving)
            yield self.env.timeout(ticks)

            self._activity(
                "twinflow.twin.activity_completed",
                arrival.pallet_id,
                self.receiving,
                duration_ticks=ticks,
                duration_s=ticks / self.spec.tick_hz,
                outcome="ok",
            )

            # Blocking after service. The server is still held, so a full
            # staging buffer stops receiving rather than growing an unbounded
            # queue, and the spell is recorded as IDLE_BLOCKED so the loss is
            # attributed to the downstream constraint that caused it.
            handover = self.staging.put(arrival.pallet_id)
            self.receiving.busy -= 1
            if not handover.triggered:
                self.receiving.blocked += 1
                self._refresh(self.receiving)
                yield handover
                self.receiving.blocked -= 1
            else:
                yield handover

            self._transition(arrival.pallet_id, PalletState.STAGED)
            self.units_staged += arrival.qty_units
            self.max_staged_pallets = max(self.max_staged_pallets, len(self.staging.items))
            self._refresh(self.receiving)
            self._sample_wip()

    # The send type is what simpy pushes back into the generator, which is the
    # value of whichever event was yielded: a pallet id from `staging.get()`
    # and nothing from `env.timeout`. Declaring it `None` describes only the
    # timeout, and then the pallet id reads as `None` at the one line that
    # binds it.
    def _putaway_server(self) -> Generator[simpy.Event, Any, None]:
        """One putaway server, pulling the staging buffer first in, first out."""
        while True:
            pallet_id = yield self.staging.get()
            arrival = self.pallets[pallet_id]

            self.units_staged -= arrival.qty_units
            self._transition(pallet_id, PalletState.AWAITING_PUTAWAY)
            self.putaway.busy += 1
            self._refresh(self.putaway)
            self._activity("twinflow.twin.activity_started", pallet_id, self.putaway)

            ticks = self._service_ticks(self.putaway)
            yield self.env.timeout(ticks)

            self._transition(pallet_id, PalletState.STORED)
            self.units_in_system -= arrival.qty_units
            self.units_putaway += arrival.qty_units
            self.putaway.busy -= 1
            self._activity(
                "twinflow.twin.activity_completed",
                pallet_id,
                self.putaway,
                duration_ticks=ticks,
                duration_s=ticks / self.spec.tick_hz,
                outcome="ok",
            )
            self._refresh(self.putaway)
            self._sample_wip()

    # -- the run ------------------------------------------------------------

    def run(self, *, horizon_ticks: int | None) -> StationRun:
        self._emit(
            "twinflow.twin.model_built",
            None,
            {
                "facility_hash": self.spec.facility_hash,
                "station_count": 2,
                "resource_count": self.spec.receiving.capacity + self.spec.putaway.capacity,
                "stream_names": list(self.streams.declared_names()),
                "tick_hz": self.spec.tick_hz,
                "staging_capacity": self.spec.staging_capacity,
            },
        )

        for arrival in self.spec.arrivals:
            self.env.process(self._pallet_process(arrival))
        for _ in range(self.spec.putaway.capacity):
            self.env.process(self._putaway_server())

        self.env.run(until=horizon_ticks)

        end_tick = int(self.env.now)
        self.clock.advance_to(SimInstant(end_tick))
        traces: dict[str, tuple[StateSpell, ...]] = {}
        for station in (self.receiving, self.putaway):
            station.spells.append(
                StateSpell(state=station.state, start_tick=station.spell_start, end_tick=end_tick)
            )
            traces[station.spec.station_id] = tuple(station.spells)

        return StationRun(
            run_id=self.run_id,
            seed=self.seed,
            facility_hash=self.spec.facility_hash,
            tick_hz=self.spec.tick_hz,
            end_tick=end_tick,
            events=tuple(self.tape.events),
            ledger=MaterialLedger(
                units_received=self.units_received,
                units_in_system=self.units_in_system,
                units_putaway=self.units_putaway,
                # No scrap source is modeled on this line, so the column is
                # zero by construction rather than by omission.
                units_scrapped=0,
            ),
            traces=traces,
            max_staged_pallets=self.max_staged_pallets,
        )


def run_station_line(
    spec: StationLineSpec,
    *,
    seed: int,
    replication_index: int = 0,
    horizon_ticks: int | None = None,
    clock: SimulationClock | None = None,
    run_id: str | None = None,
) -> StationRun:
    """Run one receiving and putaway line and return its tape and end state.

    The run id defaults to the line id and the seed, so it is a function of the
    inputs. The clock defaults to a fresh SimClock at the line's tick rate;
    passing one is how a caller running several models on one timeline keeps
    them on the same clock.
    """
    identity = run_id if run_id is not None else f"{spec.line_id}-{seed}"
    timekeeper: SimulationClock = clock if clock is not None else SimClock(tick_hz=spec.tick_hz)
    if timekeeper.tick_hz != spec.tick_hz:
        raise ValueError(
            f"the clock runs at {timekeeper.tick_hz} ticks per second and the line is "
            f"declared at {spec.tick_hz}; one of the two would record the wrong duration"
        )
    line = _Line(
        spec,
        seed=seed,
        replication_index=replication_index,
        run_id=identity,
        clock=timekeeper,
    )
    return line.run(horizon_ticks=horizon_ticks)
