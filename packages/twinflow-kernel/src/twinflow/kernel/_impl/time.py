"""Sim time: integer ticks, and the conversion a config loader uses.

Foundations section 3.1 fixes the invariants this module implements. The one
worth restating is T1: sim time is an integer on every application-visible
surface. A float duration in a port signature or an event payload is how two
runs that should agree end up disagreeing in the last bits.
"""

from __future__ import annotations

from decimal import ROUND_HALF_UP, Decimal
from typing import NewType

#: Ticks per simulated second. Three values, because each one has declared
#: overflow arithmetic in T4 and T5 and a fourth would not.
TickResolution: tuple[int, int, int] = (1_000, 1_000_000, 1_000_000_000)

DEFAULT_TICK_HZ = 1_000_000

#: T4. The loader rejects a horizon beyond this as TF-C031.
MAX_SIM_YEARS = 100

#: T5. Above 2**53 ticks two distinct tick values map to the same float64, and
#: SimEventLoop.time() is a float shim that asyncio compares internally. Past
#: this bound a scheduler cannot tell two scheduled instants apart, so the
#: loader rejects the run as TF-C032 rather than let it coalesce two events.
MAX_HORIZON_TICKS = 2**53 - 1

#: Non-negative integer ticks since the sim epoch (T2).
SimInstant = NewType("SimInstant", int)

#: Signed integer ticks. A duration may be negative; an instant may not.
Duration = NewType("Duration", int)


def duration_from_seconds(seconds: float | int | str, *, tick_hz: int) -> Duration:
    """Convert a wall-style duration to ticks, rounding half up away from zero.

    Config authors write "4.5 min" and T1 requires the loader to record the
    exact tick value. The rounding rule is stated because Python's built-in
    round() does not follow it: round() is banker's rounding, so round(0.5) is
    0 and round(2.5) is 2. A value landing exactly halfway on a tick boundary
    would then convert differently depending on whether the tick index happened
    to be even, which is a rule no config author could predict.

    Decimal is used rather than float arithmetic so the halfway case is decided
    on the written value rather than on its binary approximation.
    """
    if tick_hz not in TickResolution:
        raise ValueError(f"tick_hz must be one of {TickResolution}, got {tick_hz}")
    ticks = Decimal(str(seconds)) * Decimal(tick_hz)
    return Duration(int(ticks.quantize(Decimal(1), rounding=ROUND_HALF_UP)))


class SimClock:
    """Integer tick time for one run.

    The clock is advanced by the scheduler and read by everything else. It
    holds no wall-clock reading at all: doctrine D-02 allows a wall clock in
    exactly four places and this is not one of them.
    """

    def __init__(self, *, tick_hz: int = DEFAULT_TICK_HZ) -> None:
        if tick_hz not in TickResolution:
            raise ValueError(f"tick_hz must be one of {TickResolution}, got {tick_hz}")
        self._tick_hz = tick_hz
        self._now = SimInstant(0)

    @property
    def tick_hz(self) -> int:
        return self._tick_hz

    def now(self) -> SimInstant:
        """The current instant. Non-decreasing within a run (T3, INV-K1)."""
        return self._now

    def timeout(self, duration: Duration) -> SimInstant:
        """The instant a timeout of this duration expires.

        The only timeout primitive, per section 5.3, so a broker keepalive of
        60 seconds is 60 sim seconds and compresses with everything else.
        asyncio.wait_for is banned by TFD014 because it reads loop.time() and
        would not compress at all.
        """
        expiry = int(self._now) + int(duration)
        if expiry < 0:
            raise ValueError(f"a timeout of {duration} at {self._now} expires before the epoch")
        return SimInstant(expiry)

    def advance_to(self, instant: SimInstant) -> None:
        """Move the clock forward, or leave it where it is.

        Equal is allowed because two events at one instant are ordered by the
        envelope's (sim_ts, producer, seq) key rather than by the clock.
        Backwards is refused: a clock that can go backwards reorders a recorded
        log with nothing failing at the time it happens.
        """
        if instant < 0:
            raise ValueError(f"a SimInstant is never negative, got {instant}")
        if instant < self._now:
            raise ValueError(
                f"a clock never runs backwards: asked for {instant} while at {self._now}"
            )
        self._now = instant
