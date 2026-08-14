"""The DST seam: the ports every other package takes as parameters.

Phase 0 lands the clock half of that seam, which milestone C2 names. P1 adds
the network half, because the garage tier needs a transport it can run on and
ADR-0003 places the port here. The remaining two arrive with the phases that
need them, because a port with no implementation and no consumer is a name
nobody has tested.

Everything under twinflow.kernel._impl is private, and boundary rule A1.1 is
what keeps it that way.
"""

from __future__ import annotations

from twinflow.kernel._impl.environment import (
    CALM,
    EnvironmentDriver,
    EnvironmentRegistry,
    EnvironmentState,
    NullEnvironmentDriver,
)
from twinflow.kernel._impl.network import (
    MULTI_LEVEL,
    SINGLE_LEVEL,
    BusClient,
    Delivery,
    Frame,
    InMemoryBus,
    NetworkError,
    filter_levels,
    topic_matches,
)
from twinflow.kernel._impl.paced import PacedClock
from twinflow.kernel._impl.ports import Clock, Network
from twinflow.kernel._impl.scenario import (
    Scenario,
    Station,
    load_scenario,
    run_scenario,
)
from twinflow.kernel._impl.time import (
    DEFAULT_TICK_HZ,
    MAX_HORIZON_TICKS,
    MAX_SIM_YEARS,
    Duration,
    SimClock,
    SimInstant,
    TickResolution,
    duration_from_seconds,
)

#: Read by tool.hatch.version, so this is the only place the version is written.
__version__ = "0.1.0"

__all__ = [
    "BusClient",
    "CALM",
    "Clock",
    "DEFAULT_TICK_HZ",
    "Delivery",
    "Duration",
    "EnvironmentDriver",
    "EnvironmentRegistry",
    "EnvironmentState",
    "Frame",
    "InMemoryBus",
    "MAX_HORIZON_TICKS",
    "MAX_SIM_YEARS",
    "MULTI_LEVEL",
    "Network",
    "NetworkError",
    "NullEnvironmentDriver",
    "PacedClock",
    "SINGLE_LEVEL",
    "Scenario",
    "SimClock",
    "SimInstant",
    "Station",
    "TickResolution",
    "__version__",
    "duration_from_seconds",
    "filter_levels",
    "load_scenario",
    "run_scenario",
    "topic_matches",
]
