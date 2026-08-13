"""Sparkplug B v3.0.0 session state: birth certificates, aliases, and sequence.

Gate VAL-GATE-SPARK-001 owns this module. Its arbiter is the Eclipse Sparkplug
Technology Compatibility Kit, edge-node profile, which is a Java suite this
repository cannot run in a Python unit tier. So this module implements the
session model the specification fixes and leaves the wire encoding to the
vendored payload definition that gate still owes. See API.md for exactly what
is claimed and what is not, because doctrine D-11 rule 1 says this repository
is never a reference for itself and the honest boundary belongs in writing.

The normative statements implemented here are the ones ARCHITECTURE.md section
5.1 and docs/design/iot-fleet.md 5.4 restate from the specification:

- the topic form `spBv1.0/{group_id}/{message_type}/{edge_node_id}/[device_id]`
- NBIRTH carrying every node metric with datatype and alias, and `bdSeq`
- DBIRTH establishing the alias table every later DDATA references
- NDATA and DDATA reporting by exception, by alias, with the NAME EXCLUDED
- NDEATH registered as the MQTT will AT CONNECT, carrying the session `bdSeq`
- DDEATH for a device lost below a live edge node
- `seq` starting at 0 on NBIRTH and wrapping back to zero after 255

Three of those are the ones a reimplementation gets wrong, so each has a test
that states the observation that fails it: the wrap at 255, the exclusion of
the name from an aliased data message, and a metric appearing in DDATA that no
DBIRTH declared.

The Sparkplug addressing of an ISA-95 path lives here rather than beside the
grammar in twinflow.config. The six-level grammar is shared with the historian
and belongs in the package that owns the facility model, but the mapping onto
`group_id`, `edge_node_id`, and `device_id` is one protocol's reading of that
address and has exactly one caller, which is this module. Pushing it down would
make the config layer carry a wire protocol it never speaks.

One departure from docs/design/sensor-catalog.md D.3.4 is deliberate and is
narrower rather than wider. That section observes, correctly, that the
specification does not require a session to start at `seq` 0, so a CONSUMER
must not assume it. iot-fleet 5.4 step 4 then fixes twinflow's own edge nodes
at `seq = 0`, which is a producer choice this module makes and a consumer
written against this module still may not rely on.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from enum import IntEnum, StrEnum
from typing import Any

from twinflow.config import UnsPath
from twinflow.kernel import Clock

#: The namespace element the specification fixes for Sparkplug B. A constant,
#: not a setting: a client that changes it is not speaking Sparkplug B.
NAMESPACE = "spBv1.0"

#: The Sparkplug Group ID joins the first three ISA-95 levels. ARCHITECTURE
#: section 5.1: the specification reserves `+`, `/`, and `#` inside a Group ID,
#: and a colon is the delimiter that survives all three. The identifier pattern
#: in twinflow.config admits none of the four, which is what makes the join
#: reversible rather than merely conventional.
GROUP_DELIMITER = ":"

#: `seq` and `bdSeq` are both one byte wide, so both wrap at the same modulus.
SEQUENCE_MODULUS = 256

#: Alias 0 is never assigned, so a zero alias is always a bug and is detectable
#: as one. A repository rule rather than a specification rule, per
#: docs/design/sensor-catalog.md D.3.3 step 3.
FIRST_ALIAS = 1

#: The rebirth command a subscriber sends after seeing a `seq` discontinuity.
REBIRTH_METRIC = "Node Control/Rebirth"

#: The metric that correlates an NBIRTH with its NDEATH.
BDSEQ_METRIC = "bdSeq"


class MessageType(StrEnum):
    """The Sparkplug message types, spelled as they appear in the topic."""

    NBIRTH = "NBIRTH"
    NDATA = "NDATA"
    NDEATH = "NDEATH"
    DBIRTH = "DBIRTH"
    DDATA = "DDATA"
    DDEATH = "DDEATH"
    NCMD = "NCMD"
    DCMD = "DCMD"
    STATE = "STATE"


#: The message types addressed to a device rather than to the edge node. A
#: device topic carries a fifth element and a node topic does not, and getting
#: that wrong publishes a device reading where a node reading is expected.
DEVICE_MESSAGE_TYPES = frozenset(
    {MessageType.DBIRTH, MessageType.DDATA, MessageType.DDEATH, MessageType.DCMD}
)


class DataType(IntEnum):
    """The `DataType` enumeration of the Sparkplug payload definition.

    The values are those docs/design/sensor-catalog.md D.3.2 records from the
    specification's payload definition: 1 to 14 for the scalars, 15 UUID,
    16 DataSet, 17 Bytes, 18 File, 19 Template, 20 PropertySet,
    21 PropertySetList, and 22 to 34 for the arrays, of which FloatArray is 30.

    That section also asks for this table to be GENERATED from the vendored
    `.proto` rather than written by hand, with `test_datatype_enum_matches_
    generated_table` failing when the two disagree. The `.proto` lands under
    `schemas/iot/sparkplug/` with the codec, which this work package does not
    own, so the table is transcribed here and the generation is one of the
    things VAL-GATE-SPARK-001 still owes. It is recorded in API.md rather than
    left as a comment nobody reads.
    """

    Unknown = 0
    Int8 = 1
    Int16 = 2
    Int32 = 3
    Int64 = 4
    UInt8 = 5
    UInt16 = 6
    UInt32 = 7
    UInt64 = 8
    Float = 9
    Double = 10
    Boolean = 11
    String = 12
    DateTime = 13
    Text = 14
    UUID = 15
    DataSet = 16
    Bytes = 17
    File = 18
    Template = 19
    PropertySet = 20
    PropertySetList = 21
    Int8Array = 22
    Int16Array = 23
    Int32Array = 24
    Int64Array = 25
    UInt8Array = 26
    UInt16Array = 27
    UInt32Array = 28
    UInt64Array = 29
    FloatArray = 30
    DoubleArray = 31
    BooleanArray = 32
    StringArray = 33
    DateTimeArray = 34


class Quality(IntEnum):
    """The three quality codes the `Quality` metric property may carry.

    Written on every metric rather than only when quality is not GOOD. The
    property is optional in the specification, which means an absent property
    and a GOOD property are indistinguishable to a consumer trying to decide
    whether the producer knows about quality at all.
    """

    BAD = 0
    GOOD = 192
    STALE = 500


#: The plain-text spelling the JSON mirror uses, so a generic MQTT client does
#: not have to know the numeric codes.
QUALITY_NAMES = {Quality.BAD: "bad", Quality.GOOD: "good", Quality.STALE: "stale"}


@dataclass(frozen=True, slots=True)
class QosRow:
    """One row of the QoS and retain matrix of iot-fleet 5.4.

    `rule_ids` names the normative rule ids the value is read from, and `basis`
    is written only where there is no rule id to name. INV-QOS-2 asserts that
    every row with no rule id carries a written basis, which is what stops a
    future reader mistaking a repository choice for a specification
    requirement.
    """

    qos: int
    retain: bool
    rule_ids: tuple[str, ...] = ()
    basis: str = ""


#: Read from iot-fleet 5.4, which reads each value from the specification text
#: and names the rule id it came from. DDEATH is the one row v3.0.0 states no
#: QoS or retain rule for, so it carries a basis instead of a rule id.
QOS_BY_TOPIC_CLASS: Mapping[MessageType, QosRow] = {
    MessageType.NBIRTH: QosRow(
        0, False, ("tck-id-payloads-nbirth-qos", "tck-id-payloads-nbirth-retain")
    ),
    MessageType.DBIRTH: QosRow(
        0, False, ("tck-id-payloads-dbirth-qos", "tck-id-payloads-dbirth-retain")
    ),
    MessageType.NDATA: QosRow(
        0, False, ("tck-id-payloads-ndata-qos", "tck-id-payloads-ndata-retain")
    ),
    MessageType.DDATA: QosRow(
        0, False, ("tck-id-payloads-ddata-qos", "tck-id-payloads-ddata-retain")
    ),
    MessageType.NCMD: QosRow(0, False, ("tck-id-payloads-ncmd-qos", "tck-id-payloads-ncmd-retain")),
    MessageType.DCMD: QosRow(0, False, ("tck-id-payloads-dcmd-qos", "tck-id-payloads-dcmd-retain")),
    MessageType.DDEATH: QosRow(
        0,
        False,
        (),
        basis=(
            "repo choice, no v3.0.0 rule: the rule-id set carries QoS and retain "
            "rules for every sibling message and none for DDEATH, and absence of a "
            "rule is not permission to leave the value undeclared, so DDEATH "
            "matches its sibling device messages"
        ),
    ),
    MessageType.NDEATH: QosRow(
        1,
        False,
        (
            "tck-id-payloads-ndeath-will-message-qos",
            "tck-id-payloads-ndeath-will-message-retain",
        ),
    ),
    MessageType.STATE: QosRow(
        1, True, ("tck-id-host-topic-phid-birth-qos", "tck-id-host-topic-phid-birth-retain")
    ),
}

#: The mirror is not a Sparkplug topic, so its row is a repository choice and
#: sits outside the matrix above. Retained, because a subscriber arriving late
#: needs the last value; QoS 1, because the mirror is the only view a generic
#: client has and a dropped update leaves a wrong retained value in place.
MIRROR_QOS = 1
MIRROR_RETAIN = True


def qos_and_retain_for(message_type: MessageType) -> tuple[int, bool]:
    """The QoS and retain flag for one topic class."""
    row = QOS_BY_TOPIC_CLASS[message_type]
    return (row.qos, row.retain)


@dataclass(frozen=True, slots=True)
class SparkplugIds:
    """The three identifiers a Sparkplug topic is addressed by.

    Round-trips with UnsPath in both directions, which is what makes the claim
    in ARCHITECTURE section 5.1 checkable rather than asserted: the full ISA-95
    path is recoverable from the three identifiers.
    """

    group_id: str
    edge_node_id: str
    device_id: str

    def to_uns_path(self, parameter: str) -> UnsPath:
        """Recover the ISA-95 path, given back the parameter the topic dropped.

        The levels are handed to UnsPath rather than checked here. The grammar
        has one home, and a second reading of it in this module would be the
        drift that consolidating it removed.
        """
        levels = self.group_id.split(GROUP_DELIMITER)
        if len(levels) != 3:
            raise ValueError(
                f"group_id {self.group_id!r} does not split into three ISA-95 levels on "
                f"{GROUP_DELIMITER!r}; enterprise, site, and area are joined into it"
            )
        enterprise, site, area = levels
        return UnsPath(
            enterprise=enterprise,
            site=site,
            area=area,
            line=self.edge_node_id,
            equipment=self.device_id,
            parameter=parameter,
        )

    @classmethod
    def for_path(cls, path: UnsPath) -> SparkplugIds:
        """The Sparkplug addressing of one ISA-95 point."""
        return cls(
            group_id=GROUP_DELIMITER.join((path.enterprise, path.site, path.area)),
            edge_node_id=path.line,
            device_id=path.equipment,
        )


def topic_for(ids: SparkplugIds, message_type: MessageType, *, device_id: str | None = None) -> str:
    """Render one Sparkplug topic.

    The device id is refused on a node message and required on a device
    message, rather than quietly appended or quietly omitted. A node message
    that grew a fifth element addresses a device that does not exist, and a
    device message that lost one addresses the node instead.
    """
    if message_type is MessageType.STATE:
        raise ValueError(
            "STATE is addressed by host application id, not by edge node; "
            "use state_topic_for(host_id)"
        )
    is_device_message = message_type in DEVICE_MESSAGE_TYPES
    if is_device_message and device_id is None:
        raise ValueError(f"{message_type} addresses a device, so it needs a device_id")
    if not is_device_message and device_id is not None:
        raise ValueError(
            f"{message_type} addresses the edge node, so it takes no device_id; got {device_id!r}"
        )
    parts = [NAMESPACE, ids.group_id, str(message_type), ids.edge_node_id]
    if device_id is not None:
        parts.append(device_id)
    return "/".join(parts)


def state_topic_for(host_id: str) -> str:
    """The primary host application's STATE topic.

    Its own function because STATE is the one message type whose topic does not
    carry a group id or an edge node id at all.
    """
    if not host_id:
        raise ValueError("a STATE topic needs a host application id")
    return f"{NAMESPACE}/{MessageType.STATE}/{host_id}"


def mirror_topic_for(path: UnsPath) -> str:
    """The plain ISA-95 topic the JSON mirror is published on.

    A named function rather than a call to `.topic` at each site, because the
    mirror rendering is a contract of its own: ARCHITECTURE section 5.1 makes
    the Sparkplug side authoritative and the mirror derived, and a future root
    prefix belongs here rather than in every publisher.
    """
    return path.topic


@dataclass(frozen=True, slots=True)
class MetricSpec:
    """One metric a device declares at birth and may publish thereafter.

    The engineering range is optional because not every quantity has one, and
    an absent range is written as absent rather than as a zero that a consumer
    would read as a real limit.
    """

    name: str
    datatype: DataType
    unit: str
    eng_low: float | None = None
    eng_high: float | None = None
    description: str = ""

    def __post_init__(self) -> None:
        if not self.name:
            raise ValueError("a metric needs a name")
        if self.eng_low is not None and self.eng_high is not None and self.eng_low >= self.eng_high:
            raise ValueError(
                f"metric {self.name!r} has eng_low {self.eng_low} at or above "
                f"eng_high {self.eng_high}"
            )

    def properties(self) -> dict[str, Any]:
        """The property set carried on this metric at birth.

        Absent is not zero: an engineering limit that was never declared is
        left out of the property set rather than published as 0.0, which a
        consumer would read as a real floor.
        """
        properties: dict[str, Any] = {"engUnit": self.unit, "Quality": Quality.GOOD}
        if self.eng_low is not None:
            properties["engLow"] = self.eng_low
        if self.eng_high is not None:
            properties["engHigh"] = self.eng_high
        if self.description:
            properties["description"] = self.description
        return properties


@dataclass(frozen=True, slots=True)
class Metric:
    """One metric inside a payload.

    At birth a metric carries its name, its datatype, its alias, and its
    property set. In an aliased data message it carries the alias and the value
    and NOTHING ELSE, which is the rule that makes aliasing worth doing and the
    one a reimplementation most often gets wrong.
    """

    value: Any
    alias: int | None = None
    name: str | None = None
    datatype: DataType | None = None
    timestamp: int | None = None
    properties: Mapping[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class Payload:
    """A Sparkplug payload, before it reaches a wire format.

    `seq` is None on NDEATH alone, because the will is composed at CONNECT
    before the session has spent a sequence number, and any value written there
    would be one the session never actually reached.
    """

    timestamp: int
    metrics: tuple[Metric, ...]
    seq: int | None = None


@dataclass(frozen=True, slots=True)
class Message:
    """One payload with the topic and delivery flags it is published under."""

    topic: str
    message_type: MessageType
    payload: Payload
    qos: int
    retain: bool


@dataclass(frozen=True, slots=True)
class WillRegistration:
    """The NDEATH the client registers as its MQTT Last Will at CONNECT.

    A separate type from Message because the delivery flags are the will's own
    and because registering it is a step of the CONNECT packet rather than a
    publish. iot-fleet 5.4 puts it at step 2, before the CONNECT itself, and
    the ordering is the whole point: a will registered after the birth is a
    will the broker never publishes for the failure it exists to cover.
    """

    message: Message
    qos: int
    retain: bool


@dataclass(frozen=True, slots=True)
class MirrorRecord:
    """One flattened JSON record on the plain ISA-95 path.

    Derived from the same metric model as the Sparkplug payload it came from,
    which is what makes ARCHITECTURE section 5.1's claim that the two cannot
    disagree structural rather than a promise.
    """

    topic: str
    payload: Mapping[str, Any]
    qos: int = MIRROR_QOS
    retain: bool = MIRROR_RETAIN


#: An alias table is keyed by (device_id, metric_name), with None standing for
#: the edge node itself. A flat name would collide the moment two devices on
#: one node publish a metric with the same name, which is the normal case.
AliasKey = tuple[str | None, str]


class EdgeNodeSession:
    """One MQTT client session for one edge node and the devices below it.

    One session per edge node, not one per device. iot-fleet 4.1 makes the edge
    node a process and the device a logical child, so two devices on one line
    are two Sparkplug devices under one client session rather than two clients
    both claiming the line.

    The clock is injected. A device model is exactly where a wall-clock stamp
    sneaks into a payload, and doctrine D-02 allows a wall clock in four places
    of which a telemetry payload is not one.
    """

    def __init__(
        self,
        *,
        group_id: str,
        edge_node_id: str,
        clock: Clock,
        node_metrics: Sequence[MetricSpec] = (),
        devices: Mapping[str, Sequence[MetricSpec]] | None = None,
    ) -> None:
        self._ids_group = group_id
        self._edge_node_id = edge_node_id
        self._clock = clock
        self._node_metrics = tuple(node_metrics)
        # A dict, not a set, and every derived order below is sorted. D-03
        # bans an iteration order that can reach a value a second process has
        # to reproduce, and the alias table is exactly such a value.
        self._devices: dict[str, tuple[MetricSpec, ...]] = {
            device_id: tuple(specs) for device_id, specs in sorted((devices or {}).items())
        }
        self._specs: dict[AliasKey, MetricSpec] = {}
        self._aliases: dict[AliasKey, int] = {}
        self._connected = False
        self._bdseq = -1
        self._seq = 0
        self._born: set[str] = set()
        self._node_born = False
        self.node_birth_count = 0
        self._assign_aliases()

    # ------------------------------------------------------------- the aliases

    def _assign_aliases(self) -> None:
        """Assign every alias on the edge node, from a byte-wise sort.

        Uniqueness is across the edge node's ENTIRE metric set, node metrics
        and every device's metrics together, because that is the scope the
        specification gives an alias. Per-device numbering would collide the
        moment a consumer indexed by alias alone.

        The sort is explicit and is over the UTF-8 encoding, per
        docs/design/sensor-catalog.md D.3.3 step 2. A set walked in hash order
        would give a second process a different table for the same catalog,
        and INV-CAT-7 is the check that observes it.
        """
        specs: dict[AliasKey, MetricSpec] = {}
        for spec in (*self._node_metrics, *_CONTROL_METRICS):
            specs[(None, spec.name)] = spec
        for device_id, device_specs in self._devices.items():
            for spec in device_specs:
                specs[(device_id, spec.name)] = spec
        self._specs = specs
        ordered = sorted(specs, key=lambda key: ((key[0] or "").encode(), key[1].encode()))
        self._aliases = {key: index for index, key in enumerate(ordered, start=FIRST_ALIAS)}

    def alias_table(self) -> dict[AliasKey, int]:
        """The alias every metric on this edge node is referenced by."""
        return dict(self._aliases)

    # ------------------------------------------------------------- the session

    @property
    def is_connected(self) -> bool:
        return self._connected

    def connect(self) -> WillRegistration:
        """Open a session and return the NDEATH to register as the will.

        The order of iot-fleet 5.4 is followed exactly: `bdSeq` increments
        first, the NDEATH carrying it is registered as the will second, and
        the NBIRTH carrying the same `bdSeq` comes only after the CONNECT. A
        `bdSeq` chosen after the birth would correlate an NBIRTH with an NDEATH
        from a different session, which is the correlation the field exists for.
        """
        self._bdseq = (self._bdseq + 1) % SEQUENCE_MODULUS
        self._connected = True
        self._node_born = False
        self._born = set()
        self._seq = 0
        return WillRegistration(
            message=Message(
                topic=topic_for(self.ids, MessageType.NDEATH),
                message_type=MessageType.NDEATH,
                payload=Payload(
                    timestamp=self._now(),
                    # No seq. The will is composed here, before the session has
                    # spent one, so any value would be a number it never used.
                    seq=None,
                    metrics=(
                        Metric(
                            name=BDSEQ_METRIC,
                            alias=self._aliases[(None, BDSEQ_METRIC)],
                            datatype=DataType.UInt64,
                            value=self._bdseq,
                            timestamp=self._now(),
                        ),
                    ),
                ),
                qos=QOS_BY_TOPIC_CLASS[MessageType.NDEATH].qos,
                retain=QOS_BY_TOPIC_CLASS[MessageType.NDEATH].retain,
            ),
            qos=QOS_BY_TOPIC_CLASS[MessageType.NDEATH].qos,
            retain=QOS_BY_TOPIC_CLASS[MessageType.NDEATH].retain,
        )

    @property
    def ids(self) -> SparkplugIds:
        """The node's identifiers, with the device id left for the caller."""
        return SparkplugIds(group_id=self._ids_group, edge_node_id=self._edge_node_id, device_id="")

    def _now(self) -> int:
        return int(self._clock.now())

    def _next_seq(self) -> int:
        """Hand out the next sequence number and wrap it back to zero after 255.

        The modulus is applied on the way out rather than on the way in, so the
        counter never holds a value outside the byte the specification gives it.
        A subscriber uses the discontinuity to detect that it missed messages,
        so an unwrapped counter would read as a permanent gap.
        """
        value = self._seq
        self._seq = (self._seq + 1) % SEQUENCE_MODULUS
        return value

    def _require_connected(self) -> None:
        if not self._connected:
            raise RuntimeError(
                "this session has not been opened; call connect() first so the "
                "NDEATH will is registered before anything is published"
            )

    # -------------------------------------------------------------- the births

    def node_birth(self) -> Message:
        """Publish NBIRTH: every node metric, with datatype and alias.

        `seq` is 0, per iot-fleet 5.4 step 4. The birth certificate is the
        model, so a subscriber learns the whole namespace from it rather than
        from retained data, which is why the retain flag is false.
        """
        self._require_connected()
        metrics = tuple(
            self._birth_metric(None, spec)
            for spec in sorted(
                (*self._node_metrics, *_CONTROL_METRICS), key=lambda spec: spec.name.encode()
            )
        )
        self._node_born = True
        self.node_birth_count += 1
        return self._message(MessageType.NBIRTH, metrics, device_id=None)

    def device_birth(self, device_id: str) -> Message:
        """Publish DBIRTH: every metric this device will EVER publish.

        Every, not every changed one. A metric absent from DBIRTH may never
        appear in DDATA, so a device that discovers a channel later has to be
        reborn rather than quietly widen its stream.
        """
        self._require_connected()
        if not self._node_born:
            raise RuntimeError(
                f"device {device_id!r} cannot birth before its edge node does; "
                "NBIRTH establishes the session the DBIRTH belongs to"
            )
        specs = self._device_specs(device_id)
        metrics = tuple(
            self._birth_metric(device_id, spec)
            for spec in sorted(specs, key=lambda spec: spec.name.encode())
        )
        self._born.add(device_id)
        return self._message(MessageType.DBIRTH, metrics, device_id=device_id)

    def _birth_metric(self, device_id: str | None, spec: MetricSpec) -> Metric:
        return Metric(
            name=spec.name,
            alias=self._aliases[(device_id, spec.name)],
            datatype=spec.datatype,
            value=self._birth_value(device_id, spec),
            timestamp=self._now(),
            properties=spec.properties(),
        )

    def _birth_value(self, device_id: str | None, spec: MetricSpec) -> Any:
        if device_id is None and spec.name == BDSEQ_METRIC:
            return self._bdseq
        if device_id is None and spec.name == REBIRTH_METRIC:
            return False
        return None

    # ---------------------------------------------------------------- the data

    def node_data(self, changed: Mapping[str, Any]) -> Message:
        """Publish NDATA: changed node metrics, by alias, name excluded."""
        self._require_connected()
        if not self._node_born:
            raise RuntimeError("NDATA before NBIRTH: the alias table is not established yet")
        return self._message(MessageType.NDATA, self._data_metrics(None, changed), device_id=None)

    def device_data(self, device_id: str, changed: Mapping[str, Any]) -> Message:
        """Publish DDATA: changed device metrics, by alias, name excluded.

        Report by exception: only what the caller hands over is published, and
        an unchanged metric is simply absent rather than republished.
        """
        self._require_connected()
        if device_id not in self._born:
            raise RuntimeError(
                f"device {device_id!r} has published no DBIRTH in this session, so a "
                "consumer has no alias table to resolve this message against"
            )
        return self._message(
            MessageType.DDATA, self._data_metrics(device_id, changed), device_id=device_id
        )

    def _data_metrics(
        self, device_id: str | None, changed: Mapping[str, Any]
    ) -> tuple[Metric, ...]:
        metrics = []
        # Sorted, so two processes publishing the same change set produce the
        # same payload. A mapping's insertion order is the caller's, and the
        # caller is a device model whose order can vary between runs.
        for name in sorted(changed):
            key = (device_id, name)
            if key not in self._aliases:
                owner = device_id or self._edge_node_id
                raise KeyError(
                    f"metric {name!r} was absent from the birth certificate of "
                    f"{owner!r}, and a metric absent from a birth may never appear "
                    "in a data message; rebirth with it declared instead"
                )
            metrics.append(
                Metric(
                    # The name is EXCLUDED. Where aliases are used the alias is
                    # the reference, and carrying both would let a consumer
                    # resolve two different metrics from one message.
                    name=None,
                    alias=self._aliases[key],
                    value=changed[name],
                    timestamp=self._now(),
                )
            )
        return tuple(metrics)

    # -------------------------------------------------------------- the deaths

    def device_death(self, device_id: str) -> Message:
        """Publish DDEATH: this device is gone while the edge node stays up.

        The device loses its birth, so it cannot publish data again until it is
        reborn. That is what distinguishes a dead sensor from a dead gateway.
        """
        self._require_connected()
        self._device_specs(device_id)
        self._born.discard(device_id)
        return self._message(MessageType.DDEATH, (), device_id=device_id)

    # ------------------------------------------------------------- the rebirth

    def rebirth(self) -> tuple[Message, ...]:
        """Republish NBIRTH and every DBIRTH with `seq` reset to zero.

        The `bdSeq` is the live session's and does not move: a rebirth is not a
        new session, and incrementing it here would orphan the NDEATH already
        registered as the will.

        Aliases may be reassigned across a birth boundary, so a consumer that
        caches them across one is broken. This implementation reassigns from
        the same sorted input and therefore produces the same table, which is a
        property of the assignment rule rather than a guarantee a consumer may
        lean on.
        """
        self._require_connected()
        self._seq = 0
        self._born = set()
        self._assign_aliases()
        messages = [self.node_birth()]
        messages.extend(self.device_birth(device_id) for device_id in sorted(self._devices))
        return tuple(messages)

    def handle_node_command(self, command: Mapping[str, Any]) -> tuple[Message, ...]:
        """Consume an NCMD. `Node Control/Rebirth = true` is the one that acts.

        A false value is not a rebirth. That distinction matters because a host
        republishing its command set would otherwise restart every session on
        the segment.
        """
        if command.get(REBIRTH_METRIC) is True:
            return self.rebirth()
        return ()

    # --------------------------------------------------------------- the mirror

    def mirror_records(self, message: Message) -> tuple[MirrorRecord, ...]:
        """Derive the flattened JSON mirror from a Sparkplug message.

        Derived, never parallel. The mirror resolves each alias back through
        the same table the data message referenced, which is the mechanism
        ARCHITECTURE section 5.1 relies on when it says the two namespaces
        cannot disagree: there is one metric model and two renderings of it.
        """
        by_alias = {alias: key for key, alias in self._aliases.items()}
        records = []
        for metric in message.payload.metrics:
            if metric.alias is None:
                continue
            device_id, name = by_alias[metric.alias]
            if device_id is None:
                # A node metric has no equipment level, so it has no six-level
                # ISA-95 address. Omitted rather than published on an invented
                # one, because an invented level is a topic nobody can subscribe
                # to twice with the same meaning.
                continue
            spec = self._specs[(device_id, name)]
            records.append(
                MirrorRecord(
                    topic=mirror_topic_for(self._path_for(device_id, name)),
                    payload={
                        "value": metric.value,
                        "unit": spec.unit,
                        "quality": QUALITY_NAMES[Quality.GOOD],
                        "device_ts": metric.timestamp,
                        "device_id": device_id,
                        "edge_node_id": self._edge_node_id,
                        "seq": message.payload.seq,
                    },
                )
            )
        return tuple(records)

    def mirror_tombstones(self, device_id: str) -> tuple[MirrorRecord, ...]:
        """Overwrite this device's retained mirror topics on DDEATH.

        A stale retained value that outlives its device is the classic UNS
        failure: every dashboard keeps showing the last good reading of a
        sensor that has been dead for a week. Republishing with a null value
        and bad quality is the mitigation, and it has to be retained itself or
        the stale value comes straight back for the next subscriber.
        """
        records = []
        for spec in sorted(self._device_specs(device_id), key=lambda spec: spec.name.encode()):
            records.append(
                MirrorRecord(
                    topic=mirror_topic_for(self._path_for(device_id, spec.name)),
                    payload={
                        "value": None,
                        "unit": spec.unit,
                        "quality": QUALITY_NAMES[Quality.BAD],
                        "device_ts": self._now(),
                        "device_id": device_id,
                        "edge_node_id": self._edge_node_id,
                        "seq": None,
                    },
                )
            )
        return tuple(records)

    def _path_for(self, device_id: str, parameter: str):
        return SparkplugIds(
            group_id=self._ids_group,
            edge_node_id=self._edge_node_id,
            device_id=device_id,
        ).to_uns_path(parameter)

    # --------------------------------------------------------------- internals

    def _device_specs(self, device_id: str) -> tuple[MetricSpec, ...]:
        if device_id not in self._devices:
            raise KeyError(
                f"{device_id!r} is not a device of edge node {self._edge_node_id!r}; "
                f"it hosts {sorted(self._devices)}"
            )
        return self._devices[device_id]

    def _message(
        self, message_type: MessageType, metrics: tuple[Metric, ...], *, device_id: str | None
    ) -> Message:
        row = QOS_BY_TOPIC_CLASS[message_type]
        return Message(
            topic=topic_for(self.ids, message_type, device_id=device_id),
            message_type=message_type,
            payload=Payload(timestamp=self._now(), seq=self._next_seq(), metrics=metrics),
            qos=row.qos,
            retain=row.retain,
        )


#: The two metrics every edge node carries regardless of what it measures.
#: `bdSeq` correlates the birth with its death and `Node Control/Rebirth` is
#: the command a subscriber sends after seeing a sequence discontinuity, so an
#: edge node without them is one no host can recover.
_CONTROL_METRICS: tuple[MetricSpec, ...] = (
    MetricSpec(
        name=BDSEQ_METRIC,
        datatype=DataType.UInt64,
        unit="1",
        description="Birth-death sequence correlating this NBIRTH with its NDEATH.",
    ),
    MetricSpec(
        name=REBIRTH_METRIC,
        datatype=DataType.Boolean,
        unit="1",
        description="Writable. Set true through NCMD to force a rebirth.",
    ),
)
