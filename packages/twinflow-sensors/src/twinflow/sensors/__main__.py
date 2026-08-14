"""The process entry point behind the two device services of the garage tier.

    python -m twinflow.sensors --equipment temp-01

`deploy/garage/docker-compose.yaml` names this command once per device and
passes its settings as environment, so every flag reads its default from one.

WHAT THIS PROCESS PUBLISHES, AND WHAT IT DOES NOT

It plays the session opening the specification lays down and then holds it: the
will registered inside the CONNECT packet, NBIRTH, one DBIRTH for the device
below this node, and on a clean stop the DDEATH and a DISCONNECT. Everything
there is fully specified and this package already models it.

It publishes no DDATA, and that absence is deliberate rather than unfinished.
A data message carries a reading, and this container has no source of one. The
`SignalModel` that produces a channel's value and the `publish_policy` that sets
its cadence are both the sensor catalog of `docs/design/iot-fleet.md` sections
5.2 and 5.3, which arrives at P3. The kernel's environment driver is not a
substitute: it reports a normalized offset from a seasonal norm rather than a
temperature, and the only driver on disk is the null one, so a reading derived
from it would be a constant dressed as a measurement.

Publishing a placeholder would be worse than publishing nothing. A consumer
cannot tell an invented reading from a real one, and the historian would record
it as though a device had observed it.

WHAT THE BIRTHS ARE WORTH ON THEIR OWN

They are what proves the two runtime halves the compose header names. A device
that reaches the broker has crossed the OT segment through the only crossing
point there is, and a device the broker accepts has presented a certificate
whose common name matches its access control list entry. Rule 2 and rule 5 are
runtime claims, and a birth is the smallest true message that tests them.

WHY THE LAYERING STILL HOLDS

`twinflow.sensors` publishes value objects and imports no transport. This module
is a process entry point rather than part of that surface, and the transport it
reaches for is `twinflow.kernel`'s `Network` port, which sits below this package
rather than beside it. The device models and the Sparkplug session stay
transport-free, and everything here that knows about a socket is in this file.
"""

from __future__ import annotations

import argparse
import os
import signal
import threading
from pathlib import Path
from types import FrameType

from twinflow.kernel import Frame, Network, SimClock
from twinflow.kernel.mqtt import MqttNetwork, TlsFiles
from twinflow.sensors.sparkplug import (
    DataType,
    EdgeNodeSession,
    Message,
    MetricSpec,
    WillRegistration,
)
from twinflow.sensors.wire import encode_payload

#: The metrics each P1 device declares at birth. Two devices, one channel each,
#: which is what WP-P1-02 opened: an RFID portal and a temperature sensor. The
#: engineering range and the unit are what make a birth worth reading; a
#: consumer learns the channel exists and what its values will mean.
DEVICE_METRICS: dict[str, tuple[MetricSpec, ...]] = {
    "portal-03": (
        MetricSpec(
            name="read_rate",
            datatype=DataType.Float,
            unit="1",
            eng_low=0.0,
            eng_high=1.0,
            description="Fraction of expected tags read on the last pass",
        ),
    ),
    "temp-01": (
        MetricSpec(
            name="temperature_c",
            datatype=DataType.Float,
            unit="degC",
            eng_low=-40.0,
            eng_high=85.0,
            description="Ambient temperature at the receiving station",
        ),
    ),
}

DEFAULT_GROUP_ID = "dc-01:receiving:inbound-line-01"
DEFAULT_CERT_DIR = "/etc/twinflow/certs"
DEFAULT_BROKER_URL = "mqtts://broker:8883"


class ConfigurationError(ValueError):
    """A setting this process cannot start without, named rather than guessed."""


def to_frame(message: Message) -> Frame:
    """One Sparkplug message as a transport frame.

    The seam between the two packages. `Message` carries the topic and the
    delivery flags the specification fixes, and `Frame` is what the `Network`
    port takes. The payload is encoded here because the wire format belongs to
    `twinflow.sensors` and the transport does not know what it carries.
    """
    return Frame(
        topic=message.topic,
        payload=encode_payload(message.payload),
        qos=message.qos,
        retain=message.retain,
    )


def will_frame(will: WillRegistration) -> Frame:
    """The NDEATH, with the will's own delivery flags rather than the message's."""
    return Frame(
        topic=will.message.topic,
        payload=encode_payload(will.message.payload),
        qos=will.qos,
        retain=will.retain,
    )


def build_session(equipment: str, *, group_id: str, clock: SimClock) -> EdgeNodeSession:
    """The edge node for one device, with that device below it."""
    if equipment not in DEVICE_METRICS:
        raise ConfigurationError(
            f"--equipment is one of {sorted(DEVICE_METRICS)}, got {equipment!r}. A device "
            f"this process has no metrics for would publish a birth declaring nothing, and "
            f"a consumer would read that as a device with no channels rather than as a "
            f"misconfiguration"
        )
    return EdgeNodeSession(
        group_id=group_id,
        edge_node_id=equipment,
        clock=clock,
        devices={equipment: DEVICE_METRICS[equipment]},
    )


def announce(session: EdgeNodeSession, network: Network, equipment: str) -> None:
    """Connect with the will registered, then publish the births, in that order.

    The order is the specification's. `connect` composes the will, and the will
    has to reach the broker inside the CONNECT packet, so it is registered
    before this session publishes anything at all.
    """
    will = session.connect()
    network.connect(equipment, will=will_frame(will))
    network.publish(to_frame(session.node_birth()))
    network.publish(to_frame(session.device_birth(equipment)))


def farewell(session: EdgeNodeSession, network: Network, equipment: str) -> None:
    """Publish the device death and disconnect cleanly.

    A device that exits without this leaves its death to the broker's will
    delivery, which reports an outage for a container that was stopped on
    purpose.
    """
    network.publish(to_frame(session.device_death(equipment)))
    network.disconnect()


def parse_broker(url: str) -> tuple[str, int]:
    """The host and port of an `mqtts://host:port` broker address.

    Only `mqtts` is accepted. Rule 5 of the garage tier is identity rather than
    location, and an identity presented over a plain listener is one anyone on
    the segment can read and replay.
    """
    scheme, _, rest = url.partition("://")
    if scheme != "mqtts":
        raise ConfigurationError(
            f"--broker-url is an mqtts address, got {url!r}. The broker demands a client "
            f"certificate on both listeners, and a plain mqtt connection would present "
            f"this device's identity in the clear"
        )
    host, _, port = rest.partition(":")
    if not host or not port.isdigit():
        raise ConfigurationError(f"--broker-url names no host and port: {url!r}")
    return host, int(port)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="twinflow.sensors", description="Publish one device's births onto the UNS."
    )
    parser.add_argument(
        "--equipment",
        default=os.environ.get("TWINFLOW_EQUIPMENT"),
        help="the device this process publishes for",
    )
    parser.add_argument(
        "--group-id",
        default=os.environ.get("TWINFLOW_GROUP_ID", DEFAULT_GROUP_ID),
        help="the Sparkplug group id, which is the ISA-95 address above the device",
    )
    parser.add_argument(
        "--broker-url",
        default=os.environ.get("TWINFLOW_BROKER_URL", DEFAULT_BROKER_URL),
        help="the broker to publish through",
    )
    parser.add_argument(
        "--cert-dir",
        default=os.environ.get("TWINFLOW_CERT_DIR", DEFAULT_CERT_DIR),
        help="the directory holding ca.pem, cert.pem, and key.pem for this identity",
    )
    parser.add_argument(
        "--births-only",
        action="store_true",
        help="publish the births and exit, rather than holding the session open",
    )
    return parser


def equipment_from(args: argparse.Namespace) -> str:
    if not args.equipment:
        raise ConfigurationError(
            "--equipment is required, or TWINFLOW_EQUIPMENT in the environment. This "
            f"process publishes for one device and the set is {sorted(DEVICE_METRICS)}"
        )
    return args.equipment


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    equipment = equipment_from(args)
    host, port = parse_broker(args.broker_url)

    certs = Path(args.cert_dir)
    network = MqttNetwork(
        host=host,
        port=port,
        tls=TlsFiles(
            ca_certs=certs / "ca.pem", certfile=certs / "cert.pem", keyfile=certs / "key.pem"
        ),
    )

    session = build_session(equipment, group_id=args.group_id, clock=SimClock())
    announce(session, network, equipment)

    if not args.births_only:
        # Held open rather than looped. The session is the thing this process
        # exists to hold: the broker's view of the device is alive for exactly
        # as long as this connection is, and the NDEATH is what a subscriber
        # sees the moment it is not.
        stopping = threading.Event()

        def stop(_signum: int, _frame: FrameType | None) -> None:
            stopping.set()

        for received in (signal.SIGTERM, signal.SIGINT):
            signal.signal(received, stop)
        stopping.wait()

    farewell(session, network, equipment)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
