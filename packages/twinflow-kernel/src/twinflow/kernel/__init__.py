"""The DST seam: the ports every other package takes as parameters.

Phase 0 lands the clock half of that seam, which milestone C2 names. The
remaining ports arrive with the phases that need them, because a port with no
implementation and no consumer is a name nobody has tested.

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
from twinflow.kernel._impl.paced import PacedClock
from twinflow.kernel._impl.ports import Clock
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
    "CALM",
    "DEFAULT_TICK_HZ",
    "MAX_HORIZON_TICKS",
    "MAX_SIM_YEARS",
    "Clock",
    "Duration",
    "EnvironmentDriver",
    "EnvironmentRegistry",
    "EnvironmentState",
    "NullEnvironmentDriver",
    "PacedClock",
    "SimClock",
    "SimInstant",
    "TickResolution",
    "__version__",
    "duration_from_seconds",
]
