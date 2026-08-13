"""SCN-F1: the smallest process that can fail DET-001.

A determinism claim needs something to be deterministic about. This module is
that something: a toy process that draws randomness, reads the sim clock,
iterates collections, and emits an ordered event log, because those four are
how a run stops being reproducible.

WHY THE RUNNER LIVES IN THE KERNEL
-----------------------------------
The determinism contract is a kernel contract: the clock, the ordering, and the
seam every draw goes through are all here. `twinflow.cli` is declared in the
layer table under apps and arrives with P1, and when it does it calls `run`
below as a library rather than reimplementing it. The `__main__` beside this
module is a thin argparse over the same function, so the check script has an
entry point today without a package that has nothing else in it yet.

WHAT MAKES THE OUTPUT REPRODUCIBLE
-----------------------------------
Four rules, each covering one of the four failure modes:

  the clock     integer ticks from zero, advanced explicitly, never read from
                the wall clock. The `time` on every event is the scenario's
                fixed epoch plus the sim offset.
  the draws     every draw comes from a name-addressed stream, so a station's
                numbers do not move when another station is added before it.
  the order     stations run in declaration order, and events carry a dense
                per-producer sequence, so the total order is a function of the
                log rather than of the scheduler.
  the encoding  floats reach the payload as Python floats and are serialized by
                the envelope's own JSON dump, which emits the shortest decimal
                that round-trips. That fixes what the hash covers. It does not
                make cross-platform arithmetic identical, which is why D-05 has
                a second tier and why the comparison tool separates business
                fields from continuous ones.
"""

from __future__ import annotations

from datetime import datetime, timedelta
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field

from twinflow.kernel._impl.time import (
    DEFAULT_TICK_HZ,
    SimClock,
    SimInstant,
    TickResolution,
)
from twinflow.rng.registry import StreamRegistry
from twinflow.schemas.envelope import Envelope

#: The source URI every event in this scenario carries, per envelope section
#: 3.4: /twinflow/<package>/<component>.
SOURCE = "/twinflow/kernel/scenario"

#: The envelope schema this scenario's events validate against.
DATA_SCHEMA = "twinflow:schemas/envelope/v1.json"

#: The stream name grammar wants lowercase dotted segments, at least two of
#: them, and a placeholder segment is how one name serves every station.
SERVICE_STREAM = "scenario.{station}.service"


class Station(BaseModel):
    """One station, and the work that arrives at it."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    id: str = Field(min_length=1, pattern=r"^[a-z][a-z0-9_-]*$")
    arrivals: int = Field(ge=1, le=10_000)
    service_mean_s: float = Field(gt=0)
    #: Half-width of the service-time spread. A spread rather than a standard
    #: deviation, because a uniform draw over a named interval reproduces across
    #: numpy versions in a way a normal draw's algorithm does not.
    service_spread_s: float = Field(ge=0)


class Scenario(BaseModel):
    """One scenario file."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    id: str = Field(min_length=1)
    title: str = Field(min_length=1)
    description: str | None = None
    tick_hz: int = DEFAULT_TICK_HZ
    epoch: datetime
    seed: int = Field(ge=0)
    stations: list[Station] = Field(min_length=1)

    def model_post_init(self, _context: object) -> None:
        if self.tick_hz not in TickResolution:
            raise ValueError(f"tick_hz must be one of {TickResolution}, got {self.tick_hz}")


def load_scenario(path: Path) -> Scenario:
    """Read a scenario file.

    The YAML parser is imported here rather than at module scope because it is
    an extra rather than a dependency: foundations 2.2 holds the core install to
    pydantic and numpy, and a parser at module scope would put a third name in
    every install of this brick.
    """
    try:
        import yaml
    except ModuleNotFoundError as error:  # pragma: no cover - install-shape path
        raise ModuleNotFoundError(
            "reading a scenario file needs a YAML parser, which is an extra rather "
            "than a dependency of this brick. Install it with "
            "`pip install twinflow-kernel[scenario]`."
        ) from error

    # model_validate rather than keyword unpacking: the file is untyped data,
    # and pydantic reports which key is wrong rather than raising TypeError
    # about an unexpected argument.
    return Scenario.model_validate(yaml.safe_load(path.read_text(encoding="utf-8")))


def run_scenario(
    scenario: Scenario, *, seed: int | None = None, run_id: str | None = None
) -> list[Envelope]:
    """Run one scenario and return its event log.

    The run id defaults to the scenario id and the seed, so it is a function of
    the inputs. A generated id would put a fresh value into every event, no two
    runs would hash the same, and the gate would be impossible to pass rather
    than easy to fail.
    """
    base_seed = scenario.seed if seed is None else seed
    identity = run_id or f"{scenario.id.lower()}-{base_seed}"

    clock = SimClock(tick_hz=scenario.tick_hz)
    streams = StreamRegistry(base_seed=base_seed)
    streams.register(SERVICE_STREAM)

    events: list[Envelope] = []
    sequence = 0

    def emit(event_type: str, subject: str | None, data: dict) -> None:
        nonlocal sequence
        ticks = int(clock.now())
        events.append(
            Envelope(
                specversion="1.0",
                # Deterministic and unique without a counter shared between
                # producers: the sequence is already dense per producer, so the
                # run and the sequence identify the event.
                id=f"{identity}-sim-{sequence}",
                source=SOURCE,
                type=event_type,
                time=scenario.epoch + timedelta(seconds=ticks / scenario.tick_hz),
                datacontenttype="application/json",
                dataschema=DATA_SCHEMA,
                subject=subject,
                twinflowsimts=str(ticks),
                twinflowrunid=identity,
                twinflowproducerid="sim",
                twinflowseq=str(sequence),
                data=data,
            )
        )
        sequence += 1

    emit(
        "twinflow.sim.run.started.v1",
        None,
        {
            "scenario_id": scenario.id,
            "seed": base_seed,
            "tick_hz": scenario.tick_hz,
            "station_count": len(scenario.stations),
        },
    )

    for station in scenario.stations:
        generator = streams.get(SERVICE_STREAM, station=station.id)
        low = station.service_mean_s - station.service_spread_s
        high = station.service_mean_s + station.service_spread_s

        for index in range(station.arrivals):
            item_id = f"{station.id}-{index:04d}"
            emit(
                "twinflow.sim.item.arrived.v1",
                item_id,
                {"station_id": station.id, "item_id": item_id, "arrival_index": index},
            )

            # One draw per arrival, from this station's own stream. float()
            # because the payload carries a Python float rather than a numpy
            # scalar, and the two serialize differently.
            service_s = float(generator.uniform(low, high))
            # The business fact is the tick the item departs on, which is an
            # integer and identical on every platform. The seconds are the
            # continuous field, and D-05 tier two is about exactly that
            # distinction.
            service_ticks = round(service_s * scenario.tick_hz)
            clock.advance_to(SimInstant(int(clock.now()) + service_ticks))

            emit(
                "twinflow.sim.item.departed.v1",
                item_id,
                {
                    "station_id": station.id,
                    "item_id": item_id,
                    "arrival_index": index,
                    "service_ticks": service_ticks,
                    "service_s": service_s,
                },
            )

    emit(
        "twinflow.sim.run.finished.v1",
        None,
        {
            "scenario_id": scenario.id,
            "event_count": sequence + 1,
            "final_tick": int(clock.now()),
            "streams": list(streams.declared_names()),
        },
    )

    return events
