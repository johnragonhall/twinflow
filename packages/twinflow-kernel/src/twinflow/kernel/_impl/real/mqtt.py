"""The production `Network`: an MQTT client over TLS, per ADR-0003.

`paho-mqtt` sits behind the `mqtt` extra, so importing `twinflow.kernel`
resolves nothing and a reader running a scenario in simulation mode never opens
a socket. The import below is at module scope on purpose: this module is not
imported by the package, so paying for it here costs a caller who asked for it
by name and nobody else.

WHAT THIS ADAPTER IS RESPONSIBLE FOR BEING RIGHT ABOUT

Three things, and each one is a place a plausible implementation goes wrong.

The will. A Sparkplug NDEATH is registered at connect time and published by the
broker when the connection ends without a DISCONNECT packet. `will_set` has to
be called before `connect`, because paho sends the will in the CONNECT packet
and a will registered afterwards reaches the broker on the next connect rather
than this one. `disconnect` sends the packet, which is what tells the broker to
discard the will rather than publish it.

Re-subscription. A broker that restarts loses the subscriptions of a clean
session, and paho reconnects underneath the caller without telling it. So the
subscription list is held here and replayed from `on_connect`, which fires on
every connect including the automatic ones. An adapter that subscribed once at
call time goes quiet after the first broker restart, and nothing raises.

Routing. The broker filters server-side, but one client holding several
subscriptions receives every match on one callback. `topic_matches` decides
which handlers a frame reaches, so a caller sees the same fan-out the in-memory
bus gives it. Handlers run in subscription order, from a list, per doctrine
D-03.

WHAT IT DOES NOT CLAIM

No integration test runs against a broker here. The units below are driven
through an injected client double, which proves the ordering, the routing, and
the refusals, and proves nothing about how Mosquitto answers. ADR-0003 states
that the two adapters agree by construction rather than by a shared conformance
suite, and this docstring is the same admission at the place a reader meets the
code.
"""

from __future__ import annotations

import ssl
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol

import paho.mqtt.client as paho

from twinflow.kernel._impl.network import Frame, NetworkError, filter_levels, topic_matches

#: paho's own name for "the connection succeeded". Compared rather than assumed
#: so a non-zero reason code fails loudly instead of leaving a client that
#: reports itself connected and delivers nothing.
_CONNECTION_ACCEPTED = 0


@dataclass(frozen=True, slots=True)
class TlsFiles:
    """The three files an mTLS identity is made of.

    Rule 5 of the garage tier is identity rather than location: the broker reads
    the common name off `certfile` and applies its access control list to that
    name. So the identity passed to `connect` and the identity on this
    certificate are the same claim made twice, and a mismatch is a
    misconfiguration the broker refuses rather than something this adapter can
    paper over.
    """

    ca_certs: Path
    certfile: Path
    keyfile: Path

    def __post_init__(self) -> None:
        for label in ("ca_certs", "certfile", "keyfile"):
            path = getattr(self, label)
            if not path.exists():
                raise NetworkError(
                    f"{label} names {path}, which does not exist. "
                    f"deploy/garage/make-certs.sh writes the three files, and the "
                    f"directory stays untracked because a committed private key is a "
                    f"compromised private key"
                )


class _Client(Protocol):
    """The slice of paho's client this adapter drives.

    Declared so the tests can inject a double without a broker, and so a reader
    can see the surface being depended on rather than the whole client.
    """

    #: paho delivers through assigned callbacks rather than through overridden
    #: methods, so these are attributes of the protocol rather than methods.
    on_connect: Any
    on_message: Any

    def will_set(self, topic: str, payload: bytes, qos: int, retain: bool) -> Any: ...
    def tls_set_context(self, context: ssl.SSLContext) -> Any: ...
    def connect(self, host: str, port: int, keepalive: int) -> Any: ...
    def subscribe(self, topic: str, qos: int) -> Any: ...
    def publish(self, topic: str, payload: bytes, qos: int, retain: bool) -> Any: ...
    def disconnect(self) -> Any: ...
    def loop_start(self) -> Any: ...
    def loop_stop(self) -> Any: ...


@dataclass
class _Subscription:
    filter: str
    qos: int
    handler: Callable[[Frame], None]


def tls_context(tls: TlsFiles) -> ssl.SSLContext:
    """A context that verifies the broker and presents this identity.

    `create_default_context` rather than a hand-built one: it turns on hostname
    checking and certificate verification and selects the protocol versions the
    interpreter considers current, so a later CPython tightens this call
    without an edit here. The two assignments after it are not redundant; they
    state the two properties this connection cannot do without, so a future
    refactor that reaches for a different constructor fails the test rather
    than quietly accepting any certificate the network offers.

    Loading the trust anchor here rather than at first connect is what makes a
    file that is not a certificate an error at startup, where the operator who
    just ran the certificate script is still watching.
    """
    context = ssl.create_default_context(purpose=ssl.Purpose.SERVER_AUTH, cafile=str(tls.ca_certs))
    context.verify_mode = ssl.CERT_REQUIRED
    context.check_hostname = True
    context.load_cert_chain(certfile=str(tls.certfile), keyfile=str(tls.keyfile))
    return context


def _default_client(identity: str) -> _Client:
    # twinflow: allow-nondeterminism(TFD003) reason="paho-mqtt is the production
    # transport" owner="@jack" expires="2027-01-01"
    # adr="docs/adr/0003-the-network-port-and-its-mqtt-adapter.md"
    return paho.Client(  # type: ignore[return-value]
        callback_api_version=paho.CallbackAPIVersion.VERSION2,
        client_id=identity,
        protocol=paho.MQTTv5,
        clean_session=None,
    )


class MqttNetwork:
    """A `Network` over one MQTT client session.

    One session per instance. INV-SPB-1 says no two sessions in a run share an
    edge node id, and one client holding one identity is how that is kept true
    at this layer.
    """

    def __init__(
        self,
        *,
        host: str,
        port: int,
        tls: TlsFiles,
        keepalive_seconds: int = 60,
        client_factory: Callable[[str], _Client] = _default_client,
        context_factory: Callable[[TlsFiles], ssl.SSLContext] = tls_context,
    ) -> None:
        self._host = host
        self._port = port
        self._tls = tls
        self._keepalive = keepalive_seconds
        self._client_factory = client_factory
        self._context_factory = context_factory
        self._client: _Client | None = None
        self._identity: str | None = None
        #: Held here rather than left with the broker, so `on_connect` can
        #: replay them after a reconnect nobody above this line was told about.
        self._subscriptions: list[_Subscription] = []

    # ------------------------------------------------------------------- port

    def connect(self, identity: str, *, will: Frame | None = None) -> None:
        if self._client is not None:
            raise NetworkError(f"this session is already connected as {self._identity!r}")

        client = self._client_factory(identity)

        if will is not None:
            # Before connect. paho sends the will inside the CONNECT packet, and
            # one registered afterwards would arrive on the next connect rather
            # than this one, leaving this session with no death certificate.
            client.will_set(will.topic, will.payload, will.qos, will.retain)

        client.tls_set_context(self._context_factory(self._tls))

        # Assigned before connect, because paho fires `on_connect` from the
        # network loop and a callback attached afterwards can miss the first one.
        client.on_connect = self._on_connect
        client.on_message = self._on_message

        client.connect(self._host, self._port, self._keepalive)
        client.loop_start()

        self._client = client
        self._identity = identity

    def publish(self, frame: Frame) -> None:
        client = self._require_connected("publish")
        client.publish(frame.topic, frame.payload, frame.qos, frame.retain)

    def subscribe(
        self, topic_filter: str, handler: Callable[[Frame], None], *, qos: int = 0
    ) -> None:
        client = self._require_connected("subscribe")
        filter_levels(topic_filter)
        self._subscriptions.append(_Subscription(filter=topic_filter, qos=qos, handler=handler))
        client.subscribe(topic_filter, qos)

    def disconnect(self) -> None:
        if self._client is None:
            return
        # The order matters. `disconnect` sends the packet that tells the broker
        # to discard the will; stopping the loop first would leave the packet
        # unsent and the broker would publish a death that did not happen.
        self._client.disconnect()
        self._client.loop_stop()
        self._client = None
        self._identity = None

    # -------------------------------------------------------------- internals

    def _require_connected(self, call: str) -> _Client:
        if self._client is None:
            raise NetworkError(
                f"{call} before connect. A broker drops it on an unestablished session, "
                f"so raising here is the difference between a visible defect and a "
                f"message nobody receives"
            )
        return self._client

    def _on_connect(
        self, client: _Client, _userdata: Any, _flags: Any, reason: Any, *_: Any
    ) -> None:
        """Replay every subscription, on this connect and on every reconnect."""
        if int(reason) != _CONNECTION_ACCEPTED:
            raise NetworkError(
                f"the broker refused the connection with reason {reason}. A client that "
                f"treated this as connected would publish into a session that does not exist"
            )
        for subscription in self._subscriptions:
            client.subscribe(subscription.filter, subscription.qos)

    def _on_message(self, _client: _Client, _userdata: Any, message: Any) -> None:
        """Fan one delivery out to every subscription whose filter matches."""
        frame = Frame(
            topic=message.topic,
            payload=bytes(message.payload),
            qos=int(message.qos),
            retain=bool(message.retain),
        )
        for subscription in self._subscriptions:
            if topic_matches(subscription.filter, frame.topic):
                subscription.handler(frame)
