"""The device entry point: the session it opens, and what it refuses.

`main` is not called with a real broker anywhere here. The tests drive the
functions underneath it against the in-memory `Network` the kernel ships, which
is the whole point of there being a port: the same session order can be played
without a socket.
"""

from __future__ import annotations

import pytest

from twinflow.kernel import Frame, InMemoryBus, SimClock
from twinflow.sensors import MessageType, decode_payload
from twinflow.sensors.__main__ import (
    DEVICE_METRICS,
    ConfigurationError,
    announce,
    build_parser,
    build_session,
    equipment_from,
    farewell,
    parse_broker,
    to_frame,
    will_frame,
)

EQUIPMENT = "temp-01"
GROUP_ID = "dc-01:receiving:inbound-line-01"


@pytest.fixture
def bus() -> InMemoryBus:
    return InMemoryBus()


@pytest.fixture
def received(bus: InMemoryBus) -> list[Frame]:
    listener = bus.client()
    listener.connect("historian")
    seen: list[Frame] = []
    listener.subscribe("#", seen.append)
    return seen


def played(bus: InMemoryBus, equipment: str = EQUIPMENT):
    session = build_session(equipment, group_id=GROUP_ID, clock=SimClock())
    network = bus.client()
    announce(session, network, equipment)
    return session, network


# ------------------------------------------------------------------ the session


def test_the_births_reach_a_subscriber_in_specification_order(
    bus: InMemoryBus, received: list[Frame]
):
    """NBIRTH before DBIRTH. A device birth arriving first describes a device
    below a node the subscriber has never heard of."""
    played(bus)

    kinds = [frame.topic.split("/")[2] for frame in received]
    assert kinds == [MessageType.NBIRTH, MessageType.DBIRTH]


def test_the_will_is_registered_before_anything_is_published(bus: InMemoryBus):
    """The will rides inside the CONNECT packet. One registered after the birth
    is a will the broker never publishes for the failure it covers."""
    session = build_session(EQUIPMENT, group_id=GROUP_ID, clock=SimClock())
    network = bus.client()

    will = session.connect()
    network.connect(EQUIPMENT, will=will_frame(will))

    assert bus.deliveries == ()
    assert MessageType.NDEATH in will.message.topic


def test_a_dropped_device_publishes_its_death(bus: InMemoryBus, received: list[Frame]):
    session = build_session(EQUIPMENT, group_id=GROUP_ID, clock=SimClock())
    network = bus.client()
    announce(session, network, EQUIPMENT)
    received.clear()

    network.drop()

    assert [frame.topic.split("/")[2] for frame in received] == [MessageType.NDEATH]


def test_a_clean_stop_publishes_the_device_death_and_no_will(
    bus: InMemoryBus, received: list[Frame]
):
    """A container stopped on purpose must not announce a node death. A fleet
    view built on the will would report an outage on every deliberate restart."""
    session, network = played(bus)
    received.clear()

    farewell(session, network, EQUIPMENT)

    kinds = [frame.topic.split("/")[2] for frame in received]
    assert kinds == [MessageType.DDEATH]


def test_no_data_message_is_published(bus: InMemoryBus, received: list[Frame]):
    """Deliberate. A DDATA carries a reading and this container has no source of
    one: the signal model and the publish cadence are both the P3 sensor
    catalog. A placeholder would be recorded by the historian as though a device
    had observed it."""
    played(bus)

    assert MessageType.DDATA not in [frame.topic.split("/")[2] for frame in received]


# ------------------------------------------------------------------ the payload


def test_the_birth_carries_the_channel_a_consumer_needs(bus: InMemoryBus, received: list[Frame]):
    """A birth is worth reading because it declares what the channel is and
    what its values will mean."""
    played(bus)
    dbirth = decode_payload(received[-1].payload)

    names = [metric.name for metric in dbirth.metrics]
    assert "temperature_c" in names
    metric = next(m for m in dbirth.metrics if m.name == "temperature_c")
    assert metric.properties["engUnit"] == "degC"
    assert metric.alias is not None


def test_every_declared_device_has_at_least_one_metric():
    """A device with no metrics births a declaration of nothing, which a
    consumer reads as a device with no channels."""
    for equipment, metrics in DEVICE_METRICS.items():
        assert metrics, equipment


def test_a_frame_carries_the_messages_own_delivery_flags(bus: InMemoryBus):
    session = build_session(EQUIPMENT, group_id=GROUP_ID, clock=SimClock())
    session.connect()
    message = session.node_birth()

    frame = to_frame(message)

    assert (frame.qos, frame.retain) == (message.qos, message.retain)
    assert frame.topic == message.topic


# ----------------------------------------------------------------- the refusals


def test_an_unknown_device_is_refused_by_name():
    with pytest.raises(ConfigurationError, match="portal-03"):
        build_session("conveyor-99", group_id=GROUP_ID, clock=SimClock())


def test_a_missing_equipment_setting_is_refused():
    args = build_parser().parse_args([])
    args.equipment = None

    with pytest.raises(ConfigurationError, match="TWINFLOW_EQUIPMENT"):
        equipment_from(args)


@pytest.mark.parametrize("url", ["mqtt://broker:1883", "http://broker:8883", "broker:8883"])
def test_a_broker_address_that_is_not_mqtts_is_refused(url: str):
    """Rule 5 is identity rather than location, and an identity presented over a
    plain listener is one anyone on the segment can read and replay."""
    with pytest.raises(ConfigurationError):
        parse_broker(url)


def test_a_broker_address_with_no_port_is_refused():
    with pytest.raises(ConfigurationError, match="no host and port"):
        parse_broker("mqtts://broker")


def test_the_broker_address_parses_to_a_host_and_a_port():
    assert parse_broker("mqtts://broker:8883") == ("broker", 8883)


def test_the_environment_supplies_the_defaults(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("TWINFLOW_EQUIPMENT", "portal-03")
    monkeypatch.setenv("TWINFLOW_BROKER_URL", "mqtts://elsewhere:9883")

    args = build_parser().parse_args([])

    assert args.equipment == "portal-03"
    assert parse_broker(args.broker_url) == ("elsewhere", 9883)
