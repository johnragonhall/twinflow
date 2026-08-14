"""The port protocols every other package takes as a parameter.

A port is a Protocol rather than a base class so an adapter never inherits from
the kernel. That is what lets a package depend on the shape of a clock without
depending on which clock it was handed, which is the whole DST seam.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import TYPE_CHECKING, Protocol, runtime_checkable

from twinflow.kernel._impl.time import Duration, SimInstant

if TYPE_CHECKING:
    from twinflow.kernel._impl.network import Frame


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


@runtime_checkable
class Network(Protocol):
    """Publishes and receives frames. Knows nothing about which mode it is in.

    The four calls are the ones section 2 of ARCHITECTURE.md gives the NETWORK
    seam. ADR-0003 records why the port lives here and what sits behind it in
    each mode: an in-memory bus in simulation, an MQTT client over TLS in
    production.

    The surface is deliberately narrower than MQTT. There is no session
    resumption, no inflight window, and no packet identifier, because a caller
    that reasoned about any of them would be reasoning about one adapter rather
    than about the seam. What a Sparkplug edge node genuinely needs at connect
    time is here: an identity, and a will the broker publishes on its behalf if
    the connection drops without a disconnect.
    """

    def connect(self, identity: str, *, will: Frame | None = None) -> None:
        """Join the transport under this identity, registering a will.

        `identity` is the client identifier, and it is what an access control
        list is written against. Rule 5 of the garage tier is identity rather
        than location, so the adapter that reaches a broker presents a
        certificate whose common name is this string.

        `will` is published by the broker if this connection ends without a
        `disconnect`. A Sparkplug NDEATH is a will and cannot be sent any other
        way: a node that has already lost its link cannot announce that it has.
        """
        ...

    def publish(self, frame: Frame) -> None:
        """Send one frame. Raises `NetworkError` when not connected."""
        ...

    def subscribe(self, topic_filter: str, handler: Callable[[Frame], None]) -> None:
        """Deliver every matching frame to this handler.

        `topic_filter` is an MQTT filter: `+` matches one level and `#` matches
        the rest. Handlers are called in subscription order, which is a list and
        never a set, per doctrine D-03.
        """
        ...

    def disconnect(self) -> None:
        """Leave the transport cleanly, so the will is not published."""
        ...
