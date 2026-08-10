"""The port protocols every other package takes as a parameter.

A port is a Protocol rather than a base class so an adapter never inherits from
the kernel. That is what lets a package depend on the shape of a clock without
depending on which clock it was handed, which is the whole DST seam.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from twinflow.kernel._impl.time import Duration, SimInstant


@runtime_checkable
class Clock(Protocol):
    """Reads sim time. Never wall time.

    Doctrine D-02 allows a wall clock in exactly four places, and none of them
    is behind this port. A component that wants to know how long something took
    subtracts two SimInstants.
    """

    @property
    def tick_hz(self) -> int:
        """Ticks per simulated second, one of TickResolution."""
        ...

    def now(self) -> SimInstant:
        """The current instant, non-decreasing within a run (INV-K1)."""
        ...

    def timeout(self, duration: Duration) -> SimInstant:
        """The instant a timeout of this duration expires.

        The only timeout primitive, per section 5.3. A broker keepalive of 60
        seconds is 60 sim seconds and compresses with everything else, where
        asyncio.wait_for would read loop.time() and not compress at all.
        """
        ...
