"""The frame every transport carries, and the in-memory bus of simulation mode.

Section 2 of ARCHITECTURE.md gives the NETWORK seam two implementations and
calls the pair the defining architectural decision of the repository. This
module is the simulation half, and ADR-0003 records why it lives in the kernel.

WHY THIS IS NOT AN MQTT BROKER

It delivers frames to matching subscribers, in order, and nothing else. There is
no retained-message store, no queued session for a disconnected subscriber, and
no quality-of-service redelivery. Those are broker behaviors, and a half-built
broker here would let a test pass against a redelivery rule that Mosquitto
implements differently. `qos` and `retain` ride on the frame because the
production adapter has to put them on the wire, and this adapter records that it
saw them rather than acting on them.

The fault-injection layer section 2 names is not here either. The fault catalog
arrives at P3 with `docs/design/iot-fleet.md` section 5.24, and inventing
partitions and reordering ahead of the catalog that defines them would fix the
shape of a fault before the document that names it. `deliveries` exists so that
layer has something to wrap: it is the record of what was delivered to whom, in
order, which is the observable a reordering fault would perturb.

WHY DELIVERY IS SYNCHRONOUS

`publish` calls every matching handler before it returns. That makes delivery
order a function of subscription order and publish order alone, so two runs of
one seed deliver identically and the event log they produce hashes the same,
which is what VAL-GATE-DET-001 asserts. An asynchronous queue drained by the
scheduler would be closer to the real thing and would put delivery order under
the scheduler's tie-breaking, which is a second thing to have to make
deterministic for no gain at this tier.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field

#: The MQTT wildcard matching exactly one topic level.
SINGLE_LEVEL = "+"

#: The MQTT wildcard matching the remaining levels. Legal only as the last one.
MULTI_LEVEL = "#"

_SEPARATOR = "/"


class NetworkError(RuntimeError):
    """A transport call made in a state that cannot carry it out."""


@dataclass(frozen=True, slots=True)
class Frame:
    """One message on the wire, in either mode.

    Named `Frame` rather than `Message` because boundary rule A1.4 gives one
    public name exactly one owning package, and `twinflow.sensors` already
    publishes `Message` for a Sparkplug payload. A Sparkplug message becomes a
    frame at the seam; the two are different objects and the names say so.

    The payload is `bytes`. A transport that took a model would have to know how
    to serialize it, and the serialization of a Sparkplug payload belongs to the
    package that owns the format.
    """

    topic: str
    payload: bytes
    qos: int = 0
    retain: bool = False

    def __post_init__(self) -> None:
        if not self.topic:
            raise ValueError("a frame carries a topic, and the empty string is not one")
        if SINGLE_LEVEL in self.topic or MULTI_LEVEL in self.topic:
            raise ValueError(
                f"a publish topic carries no wildcard, got {self.topic!r}. "
                f"Wildcards belong to a subscription filter, and a broker that "
                f"accepted one here would deliver to a name nobody can subscribe to"
            )
        if self.qos not in (0, 1, 2):
            raise ValueError(f"qos is 0, 1, or 2, got {self.qos}")


@dataclass(frozen=True, slots=True)
class Delivery:
    """One frame, handed to one subscription. The bus's observable record."""

    filter: str
    frame: Frame


def filter_levels(topic_filter: str) -> tuple[str, ...]:
    """Split a topic filter into levels, refusing a malformed one.

    Separated from matching so a subscription is validated when it is made
    rather than when the first frame arrives. That is the rule `UnsPath`
    follows: a value that passed cannot be malformed at any of the places it is
    later read.
    """
    if not topic_filter:
        raise ValueError("a topic filter is not the empty string")

    levels = tuple(topic_filter.split(_SEPARATOR))
    if MULTI_LEVEL in levels and levels[-1] != MULTI_LEVEL:
        raise ValueError(
            f"{MULTI_LEVEL} is legal only as the last level of a filter, got {topic_filter!r}"
        )
    return levels


def topic_matches(topic_filter: str, topic: str) -> bool:
    """Whether an MQTT topic filter matches a topic name.

    The rules are the ones the MQTT specification fixes for topic filters: `+`
    matches exactly one level, `#` matches zero or more remaining levels and is
    legal only as the final level, and a filter with neither matches only its
    own name.

    The zero-or-more clause is the one that surprises a reader: `a/#` matches
    `a` as well as `a/b`, because `#` includes the parent level. That is why the
    multi-level branch below returns True on a filter one level longer than the
    topic.
    """
    levels = filter_levels(topic_filter)
    topic_levels = topic.split(_SEPARATOR)

    for index, level in enumerate(levels):
        if level == MULTI_LEVEL:
            # `a/#` matches `a` itself, so the parent level counts as a match.
            return index <= len(topic_levels)
        if index >= len(topic_levels):
            return False
        if level != SINGLE_LEVEL and level != topic_levels[index]:
            return False

    return len(levels) == len(topic_levels)


@dataclass
class _Subscription:
    filter: str
    handler: Callable[[Frame], None]


class InMemoryBus:
    """The simulation-mode `Network`, shared by every party in one run.

    One bus stands in for the broker, and each party takes a `BusClient` from
    it. That split is what lets a test assert that a device's will is published
    when its client drops: the will is held by the bus, not by the client that
    registered it.
    """

    def __init__(self) -> None:
        #: Subscriptions in the order they were made. A list rather than a dict
        #: keyed by filter, because two parties may subscribe to one filter and
        #: both are entitled to delivery, per doctrine D-03.
        self._subscriptions: list[_Subscription] = []
        self._connected: list[str] = []
        self._wills: dict[str, Frame] = {}
        self._deliveries: list[Delivery] = []

    @property
    def deliveries(self) -> tuple[Delivery, ...]:
        """Every delivery this bus made, in order."""
        return tuple(self._deliveries)

    @property
    def connected(self) -> tuple[str, ...]:
        """The identities currently joined, in the order they joined."""
        return tuple(self._connected)

    def client(self) -> BusClient:
        """A `Network` over this bus."""
        return BusClient(self)

    # ---------------------------------------------------------------- internals

    def _join(self, identity: str, will: Frame | None) -> None:
        if identity in self._connected:
            raise NetworkError(
                f"{identity!r} is already connected. Two sessions under one identity is the "
                f"defect INV-SPB-1 exists to catch, and a bus that allowed it would let a "
                f"test pass against a fleet a broker would refuse"
            )
        self._connected.append(identity)
        if will is not None:
            self._wills[identity] = will

    def _leave(self, identity: str, *, graceful: bool) -> None:
        if identity not in self._connected:
            return
        self._connected.remove(identity)
        will = self._wills.pop(identity, None)
        if will is not None and not graceful:
            self._deliver(will)

    def _subscribe(self, topic_filter: str, handler: Callable[[Frame], None]) -> None:
        # Validated here rather than at first delivery: a filter that passed
        # cannot be malformed at the place it is later read.
        filter_levels(topic_filter)
        self._subscriptions.append(_Subscription(filter=topic_filter, handler=handler))

    def _deliver(self, frame: Frame) -> None:
        for subscription in self._subscriptions:
            if topic_matches(subscription.filter, frame.topic):
                self._deliveries.append(Delivery(filter=subscription.filter, frame=frame))
                subscription.handler(frame)


@dataclass
class BusClient:
    """One party's `Network` over an `InMemoryBus`."""

    bus: InMemoryBus
    identity: str | None = field(default=None, init=False)

    def connect(self, identity: str, *, will: Frame | None = None) -> None:
        if self.identity is not None:
            raise NetworkError(f"this client is already connected as {self.identity!r}")
        self.bus._join(identity, will)
        self.identity = identity

    def publish(self, frame: Frame) -> None:
        if self.identity is None:
            raise NetworkError(
                "publish before connect. A broker drops a publish on an unestablished "
                "session, and a bus that accepted it would hide the ordering defect"
            )
        self.bus._deliver(frame)

    def subscribe(self, topic_filter: str, handler: Callable[[Frame], None]) -> None:
        if self.identity is None:
            raise NetworkError("subscribe before connect")
        self.bus._subscribe(topic_filter, handler)

    def disconnect(self) -> None:
        if self.identity is None:
            return
        self.bus._leave(self.identity, graceful=True)
        self.identity = None

    def drop(self) -> None:
        """End the session without a disconnect, so the will is published.

        Not part of the `Network` port. A link loss is something that happens to
        a client rather than something it calls, and the production adapter has
        no equivalent: there the broker notices. This is how a simulation-mode
        test reaches the same observable.
        """
        if self.identity is None:
            return
        self.bus._leave(self.identity, graceful=False)
        self.identity = None
