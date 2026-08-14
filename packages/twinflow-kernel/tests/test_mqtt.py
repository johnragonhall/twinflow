"""The production adapter, driven through a client double.

No broker runs here, and the tests say so rather than implying otherwise. What
they can prove is the part this adapter is responsible for being right about:
the will reaches the client before the CONNECT, subscriptions are replayed on
every reconnect, one delivery fans out to every matching handler, and a refused
connection raises instead of leaving a client that reports itself connected.

How Mosquitto answers is not asserted anywhere in this repository, and ADR-0003
records that the two adapters agree by construction rather than by a shared
conformance suite.
"""

from __future__ import annotations

import ssl
from pathlib import Path
from typing import Any

import pytest

from twinflow.kernel import Frame, Network, NetworkError
from twinflow.kernel.mqtt import MqttNetwork, TlsFiles, tls_context

WILL = Frame(topic="spBv1.0/dc-01/NDEATH/portal-03", payload=b"\x00", qos=1)
TOPIC = "twinflow/dc-01/receiving/inbound-line-01/portal-03/tag_read"


class FakeMessage:
    def __init__(self, topic: str, payload: bytes, qos: int = 0, retain: bool = False) -> None:
        self.topic = topic
        self.payload = payload
        self.qos = qos
        self.retain = retain


class FakeClient:
    """Records the calls the adapter makes, in the order it makes them."""

    def __init__(self, identity: str) -> None:
        self.identity = identity
        self.calls: list[str] = []
        self.published: list[tuple[str, bytes, int, bool]] = []
        self.subscribed: list[tuple[str, int]] = []
        self.will: tuple[str, bytes, int, bool] | None = None
        self.context: ssl.SSLContext | None = None
        self.on_connect: Any = None
        self.on_message: Any = None

    def will_set(self, topic: str, payload: bytes, qos: int, retain: bool) -> None:
        self.calls.append("will_set")
        self.will = (topic, payload, qos, retain)

    def tls_set_context(self, context: ssl.SSLContext) -> None:
        self.calls.append("tls_set_context")
        self.context = context

    def connect(self, host: str, port: int, keepalive: int) -> None:
        self.calls.append("connect")

    def subscribe(self, topic: str, qos: int) -> None:
        self.calls.append("subscribe")
        self.subscribed.append((topic, qos))

    def publish(self, topic: str, payload: bytes, qos: int, retain: bool) -> None:
        self.calls.append("publish")
        self.published.append((topic, payload, qos, retain))

    def disconnect(self) -> None:
        self.calls.append("disconnect")

    def loop_start(self) -> None:
        self.calls.append("loop_start")

    def loop_stop(self) -> None:
        self.calls.append("loop_stop")


@pytest.fixture
def certs(tmp_path: Path) -> TlsFiles:
    files = {}
    for label in ("ca_certs", "certfile", "keyfile"):
        path = tmp_path / f"{label}.pem"
        path.write_text("not a real certificate", encoding="utf-8")
        files[label] = path
    return TlsFiles(**files)


@pytest.fixture
def clients() -> list[FakeClient]:
    return []


@pytest.fixture
def network(certs: TlsFiles, clients: list[FakeClient]) -> MqttNetwork:
    """An adapter over a client double and a context the fixture certificates
    can actually build.

    The context is injected because the fixture writes files that are not
    certificates, and OpenSSL is right to refuse them. That refusal is asserted
    on its own below, against the real builder, which is the stronger test:
    it proves the trust anchor is loaded rather than accepted on faith.
    """

    def factory(identity: str) -> Any:
        client = FakeClient(identity)
        clients.append(client)
        return client

    return MqttNetwork(
        host="broker",
        port=8883,
        tls=certs,
        client_factory=factory,
        context_factory=lambda _: ssl.create_default_context(),
    )


# ------------------------------------------------------------------- the files


def test_a_missing_certificate_names_the_file_and_the_script(tmp_path: Path):
    """The directory stays untracked, so an absent file is the ordinary first
    run rather than a corrupted checkout, and the error says what to run."""
    present = tmp_path / "ca.pem"
    present.write_text("x", encoding="utf-8")

    with pytest.raises(NetworkError, match="make-certs.sh"):
        TlsFiles(ca_certs=present, certfile=present, keyfile=tmp_path / "absent.pem")


# -------------------------------------------------------------------- the will


def test_the_will_is_registered_before_the_connect(network: MqttNetwork, clients: list[FakeClient]):
    """paho sends the will inside the CONNECT packet. One registered afterwards
    would arrive on the next connect, leaving this session with no death
    certificate at all."""
    network.connect("portal-03", will=WILL)

    calls = clients[0].calls
    assert calls.index("will_set") < calls.index("connect")
    assert clients[0].will == (WILL.topic, WILL.payload, WILL.qos, WILL.retain)


def test_no_will_is_registered_when_none_is_given(network: MqttNetwork, clients: list[FakeClient]):
    network.connect("portal-03")

    assert clients[0].will is None
    assert "will_set" not in clients[0].calls


def test_disconnect_sends_the_packet_before_stopping_the_loop(
    network: MqttNetwork, clients: list[FakeClient]
):
    """The order is what tells the broker to discard the will. Stopping the loop
    first would leave the DISCONNECT unsent, and the broker would publish a
    death that did not happen."""
    network.connect("portal-03", will=WILL)

    network.disconnect()

    calls = clients[0].calls
    assert calls.index("disconnect") < calls.index("loop_stop")


# ------------------------------------------------------------------- the session


def test_the_adapter_satisfies_the_port(network: MqttNetwork):
    assert isinstance(network, Network)


def test_the_client_carries_the_identity_the_broker_reads(
    network: MqttNetwork, clients: list[FakeClient]
):
    network.connect("portal-03")

    assert clients[0].identity == "portal-03"


def test_a_second_connect_on_one_session_is_refused(network: MqttNetwork):
    """One session per instance, which is INV-SPB-1 at this layer."""
    network.connect("portal-03")

    with pytest.raises(NetworkError, match="already connected"):
        network.connect("portal-03")


def test_publish_before_connect_is_refused(network: MqttNetwork):
    with pytest.raises(NetworkError, match="publish before connect"):
        network.publish(Frame(topic=TOPIC, payload=b"{}"))


def test_subscribe_before_connect_is_refused(network: MqttNetwork):
    with pytest.raises(NetworkError, match="subscribe before connect"):
        network.subscribe(TOPIC, lambda _: None)


def test_a_malformed_filter_is_refused_at_subscribe(network: MqttNetwork):
    network.connect("portal-03")

    with pytest.raises(ValueError, match="only as the last level"):
        network.subscribe("a/#/c", lambda _: None)


def test_a_connect_can_be_made_again_after_a_disconnect(
    network: MqttNetwork, clients: list[FakeClient]
):
    network.connect("portal-03")
    network.disconnect()

    network.connect("portal-03")

    assert len(clients) == 2


def test_a_context_is_installed_before_the_connect(network: MqttNetwork, clients: list[FakeClient]):
    """A client that connected first and set TLS afterwards would have sent the
    CONNECT in the clear."""
    network.connect("portal-03")

    calls = clients[0].calls
    assert calls.index("tls_set_context") < calls.index("connect")


def test_the_real_builder_refuses_a_file_that_is_not_a_certificate(certs: TlsFiles):
    """The fixture files are text, and this is the real builder rejecting them.

    It is the assertion that matters most here: it proves the trust anchor is
    loaded at startup rather than accepted on faith, so a mis-issued or empty
    CA file fails while the operator who just ran the certificate script is
    still watching, instead of at the first connection."""
    with pytest.raises(ssl.SSLError):
        tls_context(certs)


# ------------------------------------------------------------------- reconnect


def test_every_subscription_is_replayed_on_each_connect(
    network: MqttNetwork, clients: list[FakeClient]
):
    """A broker restart loses the subscriptions of a clean session, and paho
    reconnects underneath the caller without saying so. An adapter that
    subscribed once at call time goes quiet after the first restart, with
    nothing raising."""
    network.connect("portal-03")
    network.subscribe("twinflow/#", lambda _: None)
    network.subscribe("spBv1.0/#", lambda _: None, qos=1)
    client = clients[0]
    client.subscribed.clear()

    client.on_connect(client, None, None, 0)

    assert client.subscribed == [("twinflow/#", 0), ("spBv1.0/#", 1)]


def test_a_refused_connection_raises(network: MqttNetwork, clients: list[FakeClient]):
    """A client that treated a non-zero reason code as connected would publish
    into a session that does not exist, and every message would be dropped with
    nothing reporting it."""
    network.connect("portal-03")
    client = clients[0]

    with pytest.raises(NetworkError, match="refused the connection"):
        client.on_connect(client, None, None, 5)


# --------------------------------------------------------------------- routing


def test_one_delivery_reaches_every_matching_subscription(
    network: MqttNetwork, clients: list[FakeClient]
):
    """The broker filters server-side, but one client holding several
    subscriptions receives every match on one callback. Without local routing a
    caller would see a different fan-out here than on the in-memory bus."""
    network.connect("historian")
    seen: list[str] = []
    network.subscribe("twinflow/#", lambda _: seen.append("wide"))
    network.subscribe("twinflow/dc-01/receiving/#", lambda _: seen.append("narrow"))
    network.subscribe("twinflow/dc-02/#", lambda _: seen.append("elsewhere"))
    client = clients[0]

    client.on_message(client, None, FakeMessage(TOPIC, b"{}"))

    assert seen == ["wide", "narrow"]


def test_the_frame_carries_what_arrived_on_the_wire(
    network: MqttNetwork, clients: list[FakeClient]
):
    network.connect("historian")
    received: list[Frame] = []
    network.subscribe("#", received.append)
    client = clients[0]

    client.on_message(client, None, FakeMessage(TOPIC, b"payload", qos=2, retain=True))

    assert received == [Frame(topic=TOPIC, payload=b"payload", qos=2, retain=True)]


def test_publish_passes_the_frame_through_unchanged(
    network: MqttNetwork, clients: list[FakeClient]
):
    network.connect("portal-03")

    network.publish(Frame(topic=TOPIC, payload=b"{}", qos=1, retain=True))

    assert clients[0].published == [(TOPIC, b"{}", 1, True)]
