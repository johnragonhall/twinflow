"""The NETWORK seam: the filter grammar, delivery order, and the will.

Three groups. `topic_matches` is checked against the rules the MQTT
specification fixes for topic filters, including the clause that a reader gets
wrong. The bus is checked for the property VAL-GATE-DET-001 rests on: delivery
order is a function of subscription order and publish order, and nothing else.
The will is checked from both ends, because a will published on a clean
disconnect is worse than no will at all: it announces a death that did not
happen.
"""

from __future__ import annotations

import pytest

from twinflow.kernel import (
    Frame,
    InMemoryBus,
    Network,
    NetworkError,
    filter_levels,
    topic_matches,
)

TOPIC = "twinflow/dc-01/receiving/inbound-line-01/portal-03/tag_read"


# ------------------------------------------------------------------- the frame


def test_a_frame_refuses_an_empty_topic():
    with pytest.raises(ValueError, match="carries a topic"):
        Frame(topic="", payload=b"")


@pytest.mark.parametrize("topic", ["a/+/c", "a/#", "+", "#"])
def test_a_publish_topic_carries_no_wildcard(topic: str):
    """A broker that accepted one would deliver to a name nobody can subscribe
    to, because a filter matching a literal `+` cannot be written."""
    with pytest.raises(ValueError, match="no wildcard"):
        Frame(topic=topic, payload=b"")


@pytest.mark.parametrize("qos", [-1, 3, 99])
def test_qos_outside_the_three_levels_is_refused(qos: int):
    with pytest.raises(ValueError, match="qos is 0, 1, or 2"):
        Frame(topic="a", payload=b"", qos=qos)


# ---------------------------------------------------------- the filter grammar


@pytest.mark.parametrize(
    ("topic_filter", "topic"),
    [
        ("a/b/c", "a/b/c"),
        ("a/+/c", "a/b/c"),
        ("+/+/+", "a/b/c"),
        ("a/#", "a/b/c"),
        ("a/#", "a/b"),
        ("#", "a/b/c"),
        ("a/+/#", "a/b/c/d"),
    ],
)
def test_a_filter_matches_what_the_specification_says_it_matches(topic_filter: str, topic: str):
    assert topic_matches(topic_filter, topic)


@pytest.mark.parametrize(
    ("topic_filter", "topic"),
    [
        ("a/b/c", "a/b"),
        ("a/b", "a/b/c"),
        ("a/+", "a/b/c"),
        ("a/+/c", "a/b/d"),
        ("b/#", "a/b/c"),
    ],
)
def test_a_filter_matches_nothing_else(topic_filter: str, topic: str):
    assert not topic_matches(topic_filter, topic)


def test_the_multi_level_wildcard_matches_its_own_parent():
    """The clause a reader gets wrong. `#` matches zero or more levels, so
    `a/#` matches `a` itself and not only its children. A bus that missed this
    would silently drop the birth message published at a node's own topic."""
    assert topic_matches("a/#", "a")


def test_the_multi_level_wildcard_is_refused_anywhere_but_last():
    with pytest.raises(ValueError, match="only as the last level"):
        filter_levels("a/#/c")


def test_an_empty_filter_is_refused():
    with pytest.raises(ValueError, match="not the empty string"):
        filter_levels("")


def test_a_malformed_filter_is_refused_at_subscribe():
    """Rather than at first delivery, so the traceback names the caller that
    wrote the filter instead of whoever happened to publish next."""
    client = InMemoryBus().client()
    client.connect("historian")

    with pytest.raises(ValueError, match="only as the last level"):
        client.subscribe("a/#/c", lambda _: None)


# --------------------------------------------------------------- delivery order


def test_the_bus_satisfies_the_port():
    """`Network` is a runtime-checkable Protocol, so this asserts the four calls
    are present rather than that a base class was inherited."""
    assert isinstance(InMemoryBus().client(), Network)


def test_two_subscribers_are_called_in_subscription_order():
    """The property the determinism gate rests on. Order comes from a list, per
    doctrine D-03, so two runs of one seed deliver identically."""
    bus = InMemoryBus()
    reader, writer = bus.client(), bus.client()
    reader.connect("historian")
    writer.connect("portal-03")

    called: list[str] = []
    reader.subscribe("#", lambda _: called.append("first"))
    reader.subscribe("#", lambda _: called.append("second"))

    writer.publish(Frame(topic=TOPIC, payload=b"{}"))

    assert called == ["first", "second"]


def test_one_filter_subscribed_twice_delivers_twice():
    """Two parties may subscribe to one filter and both are entitled to
    delivery, which a dict keyed by filter would collapse to one."""
    bus = InMemoryBus()
    writer = bus.client()
    writer.connect("portal-03")
    for index in range(2):
        listener = bus.client()
        listener.connect(f"listener-{index}")
        listener.subscribe("twinflow/#", lambda _: None)

    writer.publish(Frame(topic=TOPIC, payload=b"{}"))

    assert len(bus.deliveries) == 2


def test_a_frame_reaches_only_the_matching_subscription():
    bus = InMemoryBus()
    writer, reader = bus.client(), bus.client()
    writer.connect("portal-03")
    reader.connect("historian")
    received: list[Frame] = []
    reader.subscribe("twinflow/dc-01/receiving/#", received.append)
    reader.subscribe("twinflow/dc-02/#", received.append)

    writer.publish(Frame(topic=TOPIC, payload=b"{}"))

    assert [frame.topic for frame in received] == [TOPIC]


def test_the_delivery_record_names_the_filter_that_matched():
    """The observable a reordering fault would perturb. The fault catalog
    arrives at P3, and this is what it will have to wrap."""
    bus = InMemoryBus()
    writer, reader = bus.client(), bus.client()
    writer.connect("portal-03")
    reader.connect("historian")
    reader.subscribe("twinflow/#", lambda _: None)

    writer.publish(Frame(topic=TOPIC, payload=b"{}", qos=1))

    assert [(d.filter, d.frame.topic, d.frame.qos) for d in bus.deliveries] == [
        ("twinflow/#", TOPIC, 1)
    ]


def test_qos_and_retain_ride_on_the_frame_without_being_acted_on():
    """This bus is not a broker. It records that it saw them, because the
    production adapter has to put them on the wire, and a half-built retained
    store here would let a test pass against a rule Mosquitto implements
    differently."""
    bus = InMemoryBus()
    writer = bus.client()
    writer.connect("portal-03")
    writer.publish(Frame(topic=TOPIC, payload=b"{}", retain=True))

    late = bus.client()
    late.connect("historian")
    received: list[Frame] = []
    late.subscribe("#", received.append)

    assert received == []


# ------------------------------------------------------------------ connection


def test_publish_before_connect_is_refused():
    client = InMemoryBus().client()

    with pytest.raises(NetworkError, match="publish before connect"):
        client.publish(Frame(topic=TOPIC, payload=b""))


def test_two_sessions_under_one_identity_are_refused():
    """INV-SPB-1: no two MQTT client sessions in a run share an edge node id. A
    bus that allowed it would let a test pass against a fleet a broker with an
    access control list per identity would refuse."""
    bus = InMemoryBus()
    first, second = bus.client(), bus.client()
    first.connect("portal-03")

    with pytest.raises(NetworkError, match="already connected"):
        second.connect("portal-03")


def test_an_identity_frees_up_after_a_disconnect():
    bus = InMemoryBus()
    first, second = bus.client(), bus.client()
    first.connect("portal-03")
    first.disconnect()

    second.connect("portal-03")

    assert bus.connected == ("portal-03",)


# ------------------------------------------------------------------------ will


def test_a_dropped_connection_publishes_the_will():
    """A Sparkplug NDEATH cannot be sent any other way: a node that has lost its
    link cannot announce that it has."""
    bus = InMemoryBus()
    device, reader = bus.client(), bus.client()
    reader.connect("historian")
    received: list[Frame] = []
    reader.subscribe("#", received.append)
    device.connect("portal-03", will=Frame(topic="spBv1.0/dc-01/NDEATH/portal-03", payload=b"\x00"))

    device.drop()

    assert [frame.topic for frame in received] == ["spBv1.0/dc-01/NDEATH/portal-03"]


def test_a_clean_disconnect_publishes_no_will():
    """The half that matters more. A will published on a graceful disconnect
    announces a death that did not happen, and a fleet health view built on it
    reports an outage every time a device is restarted on purpose."""
    bus = InMemoryBus()
    device, reader = bus.client(), bus.client()
    reader.connect("historian")
    received: list[Frame] = []
    reader.subscribe("#", received.append)
    device.connect("portal-03", will=Frame(topic="spBv1.0/dc-01/NDEATH/portal-03", payload=b"\x00"))

    device.disconnect()

    assert received == []


def test_a_will_is_not_published_twice():
    """A drop after a disconnect is a no-op, so a supervisor that calls both on
    a shutdown path does not announce a death after a clean exit."""
    bus = InMemoryBus()
    device, reader = bus.client(), bus.client()
    reader.connect("historian")
    received: list[Frame] = []
    reader.subscribe("#", received.append)
    device.connect("portal-03", will=Frame(topic="spBv1.0/dc-01/NDEATH/portal-03", payload=b"\x00"))

    device.disconnect()
    device.drop()

    assert received == []
