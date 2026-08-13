"""The discrete-event process twin of receiving and putaway.

Phase 1 lands the station model that requirement 1 asks for, which is the
smallest thing that can carry a value stream: pallets arrive, are unloaded,
wait in a bounded buffer, and are put away, and every state change of every
pallet and every resource reaches the tape. The metric engine, the bottleneck
detector, and the value-stream summary read that tape and arrive with their own
work packages, because a metric with no run to measure is a formula nobody has
checked.
"""

from __future__ import annotations

from twinflow.twin.station import (
    PALLET_TRANSITIONS,
    RECEIVING_STREAM,
    SERVICE_STREAM,
    DistributionSpec,
    IllegalTransitionError,
    MaterialLedger,
    PalletArrival,
    PalletState,
    SimulationClock,
    StateSpell,
    StationLineSpec,
    StationRun,
    StationSpec,
    StationState,
    check_transition,
    run_station_line,
)

#: Read by tool.hatch.version, so this is the only place the version is written.
__version__ = "0.1.0"

__all__ = [
    "DistributionSpec",
    "IllegalTransitionError",
    "MaterialLedger",
    "PALLET_TRANSITIONS",
    "PalletArrival",
    "PalletState",
    "RECEIVING_STREAM",
    "SERVICE_STREAM",
    "SimulationClock",
    "StateSpell",
    "StationLineSpec",
    "StationRun",
    "StationSpec",
    "StationState",
    "__version__",
    "check_transition",
    "run_station_line",
]
