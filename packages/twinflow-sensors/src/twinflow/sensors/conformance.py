"""The Sparkplug B v3.0.0 assertion table and the runner that executes it.

Gate VAL-GATE-SPARK-001 names the Eclipse Sparkplug Technology Compatibility
Kit, edge-node profile, as its arbiter. That kit is a Java suite under EPL-2.0
and this repository is Apache-2.0, so neither its source nor its normative
prose may enter here. What may enter is the set of published assertion
identifiers and the technical requirements they denote, which are facts rather
than expression. Every `statement` below is written here from the requirement
rather than copied from the specification, and every identifier is one the
v3.0.0 specification anchors with a `tck-testable` role.

The table is the honest denominator. It carries all 299 anchored assertions of
v3.0.0, not only the ones this package satisfies, and each row records three
independent facts: which conformance profile the assertion constrains, whether
this repository is in scope for it, and, when it is not, the reason. A high
pass count over a table pruned to what already works would say nothing, so the
pruning is recorded instead of performed.

`profile` and `scope` are orthogonal. An assertion can constrain a Host
Application and still be in scope here, because `QOS_BY_TOPIC_CLASS` declares
delivery flags for topic classes this package never publishes on. The
edge-node coverage numbers `coverage()` reports read `profile` alone.

The specification's own anchor and its displayed label disagree for four
assertions. The anchor is the identifier used here, because the anchor is what
a cross-reference resolves against.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass
from enum import StrEnum

from twinflow.kernel import Clock, SimClock
from twinflow.sensors.sparkplug import (
    BDSEQ_METRIC,
    NAMESPACE,
    QOS_BY_TOPIC_CLASS,
    REBIRTH_METRIC,
    SEQUENCE_MODULUS,
    DataType,
    EdgeNodeSession,
    Message,
    MessageType,
    Metric,
    MetricSpec,
    Quality,
    SparkplugIds,
    WillRegistration,
    topic_for,
)

#: The specification edition every identifier here is read from.
SPEC_VERSION = "3.0.0"

#: Assertions the v3.0.0 specification anchors with a `tck-testable` role. The
#: table below carries exactly this many rows, which is what makes the coverage
#: denominator checkable rather than asserted.
SPEC_ASSERTION_COUNT = 299


class Profile(StrEnum):
    """The conformance profile an assertion constrains.

    v3.0.0 names four target applications and marks no assertion with the one
    it belongs to, so the profile here is read from the actor each assertion's
    sentence constrains: the client that publishes the message, or the server
    that stores it. The compatibility kit's own grouping is a Java artifact and
    is not consulted, so this column is a reading and is open to correction.
    """

    EDGE_NODE = "edge-node"
    HOST_APPLICATION = "host-application"
    MQTT_SERVER = "mqtt-server"


class Level(StrEnum):
    """The requirement level the assertion's sentence carries."""

    MUST = "MUST"
    SHOULD = "SHOULD"
    MAY = "MAY"


class Exclusion(StrEnum):
    """Why an assertion is out of scope for this repository.

    Every value names a capability this package lacks, rather than a judgement
    that the assertion does not matter. An excluded assertion is an unmet
    requirement, not a satisfied one.
    """

    ENCODING = "protobuf wire encoding, which this package does not implement"
    TEMPLATES = (
        "Template, DataSet, and PropertySet wire structures, which this package does not model"
    )
    TRANSPORT = "a live MQTT client and broker, which sits above the domain layer"
    DEPLOYMENT = "uniqueness across a whole infrastructure, which one session cannot observe"
    PRIMARY_HOST = (
        "Primary Host coordination and multi-server failover, which this package does not model"
    )
    OTHER_PROFILE = (
        "the behavior of a Host Application or an MQTT Server, which this package is not"
    )


@dataclass(frozen=True, slots=True)
class Assertion:
    """One published assertion identifier and this repository's position on it."""

    assertion_id: str
    profile: Profile
    level: Level
    statement: str
    exclusion: Exclusion | None

    @property
    def in_scope(self) -> bool:
        """Whether this repository answers for this assertion."""
        return self.exclusion is None


_EDGE = Profile.EDGE_NODE
_HOST = Profile.HOST_APPLICATION
_SERVER = Profile.MQTT_SERVER
_MUST = Level.MUST
_SHOULD = Level.SHOULD
_MAY = Level.MAY
_ENC = Exclusion.ENCODING
_TPL = Exclusion.TEMPLATES
_TRN = Exclusion.TRANSPORT
_DEP = Exclusion.DEPLOYMENT
_PHI = Exclusion.PRIMARY_HOST
_OTH = Exclusion.OTHER_PROFILE

#: `(identifier, profile, level, exclusion, statement)`, in specification order.
#: A `None` exclusion means this repository answers for the assertion, and the
#: runner below carries a check for it.
_ROWS: tuple[tuple[str, Profile, Level, Exclusion | None, str], ...] = (
    # ---------------------------------------------------------- 1 Introduction
    (
        "tck-id-intro-sparkplug-host-state",
        _HOST,
        _MUST,
        _OTH,
        "A Host Application announces its own online and offline status with STATE messages.",
    ),
    (
        "tck-id-intro-group-id-string",
        _EDGE,
        _MUST,
        None,
        "The Group ID is a UTF-8 string carried as a level of the Sparkplug topic.",
    ),
    (
        "tck-id-intro-group-id-chars",
        _EDGE,
        _MUST,
        None,
        "The Group ID holds only characters MQTT permits inside a topic string.",
    ),
    (
        "tck-id-intro-edge-node-id-string",
        _EDGE,
        _MUST,
        None,
        "The Edge Node ID is a UTF-8 string carried as a level of the Sparkplug topic.",
    ),
    (
        "tck-id-intro-edge-node-id-chars",
        _EDGE,
        _MUST,
        None,
        "The Edge Node ID holds only characters MQTT permits inside a topic string.",
    ),
    (
        "tck-id-intro-device-id-string",
        _EDGE,
        _MUST,
        None,
        "The Device ID is a UTF-8 string carried as a level of the Sparkplug topic.",
    ),
    (
        "tck-id-intro-device-id-chars",
        _EDGE,
        _MUST,
        None,
        "The Device ID holds only characters MQTT permits inside a topic string.",
    ),
    (
        "tck-id-intro-edge-node-id-uniqueness",
        _EDGE,
        _MUST,
        _DEP,
        "The Edge Node Descriptor is unique among every edge node of the infrastructure.",
    ),
    # ------------------------------------------------------------ 2 Principles
    (
        "tck-id-principles-rbe-recommended",
        _EDGE,
        _SHOULD,
        None,
        "An edge node reports by exception rather than on a timer.",
    ),
    (
        "tck-id-principles-birth-certificates-order",
        _EDGE,
        _MUST,
        None,
        "A birth certificate is the first message an edge node or a host publishes.",
    ),
    (
        "tck-id-principles-persistence-clean-session-311",
        _EDGE,
        _MUST,
        _TRN,
        "Over MQTT 3.1.1 the edge node's CONNECT sets the clean-session flag.",
    ),
    (
        "tck-id-principles-persistence-clean-session-50",
        _EDGE,
        _MUST,
        _TRN,
        "Over MQTT 5.0 the edge node's CONNECT sets clean start and a zero session expiry.",
    ),
    # ------------------------------------------------------------ 3 Components
    (
        "tck-id-components-ph-state",
        _HOST,
        _MUST,
        _OTH,
        "A Host Application uses STATE to say whether it is online at any moment.",
    ),
    # ---------------------------------------------------------------- 4 Topics
    (
        "tck-id-topic-structure",
        _EDGE,
        _MUST,
        None,
        "Every Sparkplug client addresses messages with the fixed topic namespace structure.",
    ),
    (
        "tck-id-topic-structure-namespace-a",
        _EDGE,
        _MUST,
        None,
        "The namespace level of a Sparkplug B topic is the constant spBv1.0.",
    ),
    (
        "tck-id-topic-structure-namespace-valid-group-id",
        _EDGE,
        _MUST,
        None,
        "The Group ID is a UTF-8 string that excludes plus, forward slash, and hash.",
    ),
    (
        "tck-id-topic-structure-namespace-unique-edge-node-descriptor",
        _EDGE,
        _MUST,
        _DEP,
        "No two edge nodes in the infrastructure share a group and edge-node id pair.",
    ),
    (
        "tck-id-topic-structure-namespace-valid-edge-node-id",
        _EDGE,
        _MUST,
        None,
        "The Edge Node ID is a UTF-8 string that excludes plus, forward slash, and hash.",
    ),
    (
        "tck-id-topic-structure-namespace-valid-device-id",
        _EDGE,
        _MUST,
        None,
        "The Device ID is a UTF-8 string that excludes plus, forward slash, and hash.",
    ),
    (
        "tck-id-topic-structure-namespace-unique-device-id",
        _EDGE,
        _MUST,
        None,
        "No two devices reported by one edge node share a Device ID.",
    ),
    (
        "tck-id-topic-structure-namespace-duplicate-device-id-across-edge-node",
        _EDGE,
        _MAY,
        _DEP,
        "Two different edge nodes may report devices under the same Device ID.",
    ),
    (
        "tck-id-topic-structure-namespace-device-id-associated-message-types",
        _EDGE,
        _MUST,
        None,
        "A DBIRTH, DDEATH, DDATA, or DCMD topic carries a device id level.",
    ),
    (
        "tck-id-topic-structure-namespace-device-id-non-associated-message-types",
        _EDGE,
        _MUST,
        None,
        "An NBIRTH, NDEATH, NDATA, NCMD, or STATE topic carries no device id level.",
    ),
    (
        "tck-id-topics-nbirth-topic",
        _EDGE,
        _MUST,
        None,
        "An NBIRTH is addressed as namespace, group id, NBIRTH, edge node id.",
    ),
    (
        "tck-id-topics-nbirth-mqtt",
        _EDGE,
        _MUST,
        None,
        "An NBIRTH goes out at QoS 0 with the retain flag clear.",
    ),
    (
        "tck-id-topics-nbirth-seq-num",
        _EDGE,
        _MUST,
        None,
        "An NBIRTH payload carries a sequence number whose value is zero.",
    ),
    (
        "tck-id-topics-nbirth-timestamp",
        _EDGE,
        _MUST,
        None,
        "An NBIRTH carries the instant the edge node sent it.",
    ),
    (
        "tck-id-topics-nbirth-metric-reqs",
        _EDGE,
        _MUST,
        None,
        "An NBIRTH declares every metric the edge node will ever report.",
    ),
    (
        "tck-id-topics-nbirth-metrics",
        _EDGE,
        _MUST,
        None,
        "Each NBIRTH metric carries at least a name, a datatype, and a value.",
    ),
    (
        "tck-id-topics-nbirth-templates",
        _EDGE,
        _MUST,
        _TPL,
        "Template definitions used anywhere below this edge node appear in its NBIRTH.",
    ),
    (
        "tck-id-topics-nbirth-bdseq-included",
        _EDGE,
        _MUST,
        None,
        "An NBIRTH payload carries a bdSeq metric.",
    ),
    (
        "tck-id-topics-nbirth-bdseq-matching",
        _EDGE,
        _MUST,
        None,
        "The NBIRTH bdSeq equals the bdSeq in the will registered at the same CONNECT.",
    ),
    (
        "tck-id-topics-nbirth-bdseq-increment",
        _EDGE,
        _MUST,
        None,
        "bdSeq opens at zero and advances by one for each new CONNECT.",
    ),
    (
        "tck-id-topics-nbirth-rebirth-metric",
        _EDGE,
        _MUST,
        None,
        "An NBIRTH carries a boolean Node Control/Rebirth metric whose value is false.",
    ),
    (
        "tck-id-topics-ndata-topic",
        _EDGE,
        _MUST,
        None,
        "An NDATA is addressed as namespace, group id, NDATA, edge node id.",
    ),
    (
        "tck-id-topics-ndata-mqtt",
        _EDGE,
        _MUST,
        None,
        "An NDATA goes out at QoS 0 with the retain flag clear.",
    ),
    (
        "tck-id-topics-ndata-seq-num",
        _EDGE,
        _MUST,
        None,
        "An NDATA sequence number is one above the edge node's previous message.",
    ),
    (
        "tck-id-topics-ndata-timestamp",
        _EDGE,
        _MUST,
        None,
        "An NDATA carries the instant the edge node sent it.",
    ),
    (
        "tck-id-topics-ndata-payload",
        _EDGE,
        _MUST,
        None,
        "An NDATA carries the node metrics that changed since the last NBIRTH or NDATA.",
    ),
    (
        "tck-id-topics-ndeath-topic",
        _EDGE,
        _MUST,
        None,
        "An NDEATH is addressed as namespace, group id, NDEATH, edge node id.",
    ),
    (
        "tck-id-topics-ndeath-payload",
        _EDGE,
        _MUST,
        None,
        "An NDEATH payload carries the bdSeq metric and nothing else.",
    ),
    (
        "tck-id-topics-ndeath-seq",
        _EDGE,
        _MUST,
        None,
        "An NDEATH payload carries no sequence number.",
    ),
    (
        "tck-id-topics-ncmd-topic",
        _EDGE,
        _MUST,
        None,
        "An NCMD is addressed as namespace, group id, NCMD, edge node id.",
    ),
    (
        "tck-id-topics-ncmd-mqtt",
        _HOST,
        _MUST,
        None,
        "An NCMD goes out at QoS 0 with the retain flag clear.",
    ),
    (
        "tck-id-topics-ncmd-timestamp",
        _HOST,
        _MUST,
        _OTH,
        "An NCMD carries the instant the host's client sent it.",
    ),
    (
        "tck-id-topics-ncmd-payload",
        _HOST,
        _MUST,
        _OTH,
        "An NCMD carries the metrics to be written on the edge node.",
    ),
    (
        "tck-id-topics-dbirth-topic",
        _EDGE,
        _MUST,
        None,
        "A DBIRTH is addressed as namespace, group id, DBIRTH, edge node id, device id.",
    ),
    (
        "tck-id-topics-dbirth-mqtt",
        _EDGE,
        _MUST,
        None,
        "A DBIRTH goes out at QoS 0 with the retain flag clear.",
    ),
    (
        "tck-id-topics-dbirth-seq",
        _EDGE,
        _MUST,
        None,
        "A DBIRTH sequence number is one above the edge node's previous message.",
    ),
    (
        "tck-id-topics-dbirth-timestamp",
        _EDGE,
        _MUST,
        None,
        "A DBIRTH carries the instant the edge node sent it.",
    ),
    (
        "tck-id-topics-dbirth-metric-reqs",
        _EDGE,
        _MUST,
        None,
        "A DBIRTH declares every metric this device will ever report.",
    ),
    (
        "tck-id-topics-dbirth-metrics",
        _EDGE,
        _MUST,
        None,
        "Each DBIRTH metric carries at least a name, a datatype, and a value.",
    ),
    (
        "tck-id-topics-ddata-topic",
        _EDGE,
        _MUST,
        None,
        "A DDATA is addressed as namespace, group id, DDATA, edge node id, device id.",
    ),
    (
        "tck-id-topics-ddata-mqtt",
        _EDGE,
        _MUST,
        None,
        "A DDATA goes out at QoS 0 with the retain flag clear.",
    ),
    (
        "tck-id-topics-ddata-seq-num",
        _EDGE,
        _MUST,
        None,
        "A DDATA sequence number is one above the edge node's previous message.",
    ),
    (
        "tck-id-topics-ddata-timestamp",
        _EDGE,
        _MUST,
        None,
        "A DDATA carries the instant the edge node sent it.",
    ),
    (
        "tck-id-topics-ddata-payload",
        _EDGE,
        _MUST,
        None,
        "A DDATA carries the device metrics that changed since the last DBIRTH or DDATA.",
    ),
    (
        "tck-id-topics-ddeath-topic",
        _EDGE,
        _MUST,
        None,
        "A DDEATH is addressed as namespace, group id, DDEATH, edge node id, device id.",
    ),
    (
        "tck-id-topics-ddeath-mqtt",
        _EDGE,
        _MUST,
        None,
        "A DDEATH goes out at QoS 0 with the retain flag clear.",
    ),
    (
        "tck-id-topics-ddeath-seq-num",
        _EDGE,
        _MUST,
        None,
        "A DDEATH sequence number is one above the edge node's previous message.",
    ),
    (
        "tck-id-topics-dcmd-topic",
        _EDGE,
        _MUST,
        None,
        "A DCMD is addressed as namespace, group id, DCMD, edge node id, device id.",
    ),
    (
        "tck-id-topics-dcmd-mqtt",
        _HOST,
        _MUST,
        None,
        "A DCMD goes out at QoS 0 with the retain flag clear.",
    ),
    (
        "tck-id-topics-dcmd-timestamp",
        _HOST,
        _MUST,
        _OTH,
        "A DCMD carries the instant the host's client sent it.",
    ),
    (
        "tck-id-topics-dcmd-payload",
        _HOST,
        _MUST,
        _OTH,
        "A DCMD carries the metrics to be written on the device.",
    ),
    (
        "tck-id-host-topic-phid-birth-message",
        _HOST,
        _MUST,
        _OTH,
        "The first message a Host Application publishes is its birth certificate.",
    ),
    (
        "tck-id-host-topic-phid-birth-qos",
        _HOST,
        _MUST,
        None,
        "The Host Application birth certificate goes out at QoS 1.",
    ),
    (
        "tck-id-host-topic-phid-birth-retain",
        _HOST,
        _MUST,
        None,
        "The Host Application birth certificate goes out with the retain flag set.",
    ),
    (
        "tck-id-host-topic-phid-birth-topic",
        _HOST,
        _MUST,
        _OTH,
        "The Host Application birth is addressed as spBv1.0, STATE, host id.",
    ),
    (
        "tck-id-host-topic-phid-birth-sub-required",
        _HOST,
        _MUST,
        _OTH,
        "A Host Application subscribes to its own STATE topic and the namespace on connect.",
    ),
    (
        "tck-id-host-topic-phid-birth-required",
        _HOST,
        _MUST,
        _OTH,
        "A Host Application publishes its birth once those subscriptions are in place.",
    ),
    (
        "tck-id-host-topic-phid-birth-payload",
        _HOST,
        _MUST,
        _OTH,
        "The Host Application birth payload is JSON carrying an online flag and a timestamp.",
    ),
    (
        "tck-id-host-topic-phid-birth-payload-timestamp",
        _HOST,
        _MUST,
        _OTH,
        "The birth timestamp repeats the one in the will of the preceding CONNECT.",
    ),
    (
        "tck-id-host-topic-phid-death-qos",
        _HOST,
        _MUST,
        _OTH,
        "The Host Application death certificate goes out at QoS 1.",
    ),
    (
        "tck-id-host-topic-phid-death-retain",
        _HOST,
        _MUST,
        _OTH,
        "The Host Application death certificate goes out with the retain flag set.",
    ),
    (
        "tck-id-host-topic-phid-death-topic",
        _HOST,
        _MUST,
        _OTH,
        "The Host Application death is addressed as spBv1.0, STATE, host id.",
    ),
    (
        "tck-id-host-topic-phid-death-required",
        _HOST,
        _MUST,
        _OTH,
        "A Host Application registers a will in its CONNECT.",
    ),
    (
        "tck-id-host-topic-phid-death-payload",
        _HOST,
        _MUST,
        _OTH,
        "The STATE death payload is JSON carrying a false online flag and a timestamp.",
    ),
    (
        "tck-id-host-topic-phid-death-payload-timestamp-connect",
        _HOST,
        _MUST,
        _OTH,
        "The will's death timestamp is the UTC instant of the CONNECT that registered it.",
    ),
    (
        "tck-id-host-topic-phid-death-payload-timestamp-disconnect-clean",
        _HOST,
        _MUST,
        _OTH,
        "A host disconnecting with a DISCONNECT packet publishes its death first.",
    ),
    (
        "tck-id-host-topic-phid-death-payload-timestamp-disconnect-with-no-disconnect-packet",
        _HOST,
        _MUST,
        _OTH,
        "A host dropping the connection without a DISCONNECT publishes its death first.",
    ),
    # -------------------------------------------------- 5 Operational Behavior
    (
        "tck-id-case-sensitivity-sparkplug-ids",
        _EDGE,
        _SHOULD,
        None,
        "Two Sparkplug ids on one edge node do not differ only by letter case.",
    ),
    (
        "tck-id-case-sensitivity-metric-names",
        _EDGE,
        _SHOULD,
        None,
        "Two metric names published by one edge node do not differ only by letter case.",
    ),
    (
        "tck-id-message-flow-phid-sparkplug-clean-session-311",
        _HOST,
        _MUST,
        _OTH,
        "A Host Application on MQTT 3.1.1 sets the clean-session flag in its CONNECT.",
    ),
    (
        "tck-id-message-flow-phid-sparkplug-clean-session-50",
        _HOST,
        _MUST,
        _OTH,
        "A Host Application on MQTT 5.0 sets clean start and a zero session expiry.",
    ),
    (
        "tck-id-message-flow-phid-sparkplug-subscription",
        _HOST,
        _MUST,
        _OTH,
        "A Host Application subscribes before publishing its own STATE message.",
    ),
    (
        "tck-id-message-flow-phid-sparkplug-state-publish",
        _HOST,
        _MUST,
        _OTH,
        "A Host Application publishes STATE once its session and subscriptions are up.",
    ),
    (
        "tck-id-message-flow-phid-sparkplug-state-publish-payload",
        _HOST,
        _MUST,
        _OTH,
        "The Host Application STATE birth payload is JSON with an online flag and a timestamp.",
    ),
    (
        "tck-id-message-flow-phid-sparkplug-state-publish-payload-timestamp",
        _HOST,
        _MUST,
        _OTH,
        "That STATE birth timestamp repeats the one from the preceding CONNECT will.",
    ),
    (
        "tck-id-message-flow-hid-sparkplug-state-message-delivered",
        _HOST,
        _MUST,
        _OTH,
        "A Host Application seeing a false online flag on its own id republishes its birth.",
    ),
    (
        "tck-id-message-flow-edge-node-ncmd-subscribe",
        _EDGE,
        _MUST,
        _TRN,
        "An edge node subscribes to its own NCMD topic.",
    ),
    (
        "tck-id-message-flow-edge-node-birth-publish-connect",
        _EDGE,
        _MUST,
        None,
        "An edge node establishes its MQTT session before publishing any birth.",
    ),
    (
        "tck-id-message-flow-edge-node-birth-publish-will-message",
        _EDGE,
        _MUST,
        None,
        "An edge node's CONNECT carries a will message.",
    ),
    (
        "tck-id-message-flow-edge-node-birth-publish-will-message-topic",
        _EDGE,
        _MUST,
        None,
        "The will is addressed as spBv1.0, group id, NDEATH, edge node id.",
    ),
    (
        "tck-id-message-flow-edge-node-birth-publish-will-message-payload",
        _EDGE,
        _MUST,
        _ENC,
        "The will payload is a Sparkplug protobuf-encoded payload.",
    ),
    (
        "tck-id-message-flow-edge-node-birth-publish-will-message-payload-bdSeq",
        _EDGE,
        _MUST,
        None,
        "The will carries a bdSeq metric of datatype Int64, one above the previous CONNECT and "
        "returning to zero after 255.",
    ),
    (
        "tck-id-message-flow-edge-node-birth-publish-will-message-qos",
        _EDGE,
        _MUST,
        None,
        "The will is registered at QoS 1.",
    ),
    (
        "tck-id-message-flow-edge-node-birth-publish-will-message-will-retained",
        _EDGE,
        _MUST,
        None,
        "The will is registered with the retain flag clear.",
    ),
    (
        "tck-id-message-flow-edge-node-birth-publish-phid-wait",
        _EDGE,
        _MUST,
        _PHI,
        "An edge node configured for a Primary Host waits for it to be online before birthing.",
    ),
    (
        "tck-id-message-flow-edge-node-birth-publish-phid-wait-id",
        _EDGE,
        _MUST,
        _PHI,
        "Such an edge node matches the host id in the STATE topic against its configured one.",
    ),
    (
        "tck-id-message-flow-edge-node-birth-publish-phid-wait-online",
        _EDGE,
        _MUST,
        _PHI,
        "Such an edge node requires a true online flag in the STATE payload.",
    ),
    (
        "tck-id-message-flow-edge-node-birth-publish-phid-wait-timestamp",
        _EDGE,
        _MUST,
        _PHI,
        "Such an edge node requires the STATE timestamp not to move backwards.",
    ),
    (
        "tck-id-message-flow-edge-node-birth-publish-nbirth-topic",
        _EDGE,
        _MUST,
        None,
        "The NBIRTH is addressed as spBv1.0, group id, NBIRTH, edge node id.",
    ),
    (
        "tck-id-message-flow-edge-node-birth-publish-nbirth-payload",
        _EDGE,
        _MUST,
        _ENC,
        "The NBIRTH payload is a Sparkplug protobuf-encoded payload.",
    ),
    (
        "tck-id-message-flow-edge-node-birth-publish-nbirth-payload-bdSeq",
        _EDGE,
        _MUST,
        None,
        "The NBIRTH carries a bdSeq metric of datatype Int64 holding the CONNECT's value.",
    ),
    (
        "tck-id-message-flow-edge-node-birth-publish-nbirth-qos",
        _EDGE,
        _MUST,
        None,
        "The NBIRTH is published at QoS 0.",
    ),
    (
        "tck-id-message-flow-edge-node-birth-publish-nbirth-retained",
        _EDGE,
        _MUST,
        None,
        "The NBIRTH is published with the retain flag clear.",
    ),
    (
        "tck-id-message-flow-edge-node-birth-publish-nbirth-payload-seq",
        _EDGE,
        _MUST,
        None,
        "The NBIRTH payload carries a sequence number inside the byte range zero to 255.",
    ),
    (
        "tck-id-message-flow-edge-node-birth-publish-phid-offline",
        _EDGE,
        _MUST,
        _PHI,
        "An edge node watching a Primary Host reacts to a STATE message by its timestamp.",
    ),
    (
        "tck-id-operational-behavior-edge-node-intentional-disconnect-ndeath",
        _EDGE,
        _MUST,
        None,
        "An edge node closing its own connection publishes an NDEATH before it goes.",
    ),
    (
        "tck-id-operational-behavior-edge-node-intentional-disconnect-packet",
        _EDGE,
        _MAY,
        _TRN,
        "A DISCONNECT packet may follow that NDEATH.",
    ),
    (
        "tck-id-operational-behavior-edge-node-termination-host-action-ndeath-node-offline",
        _HOST,
        _MUST,
        _OTH,
        "A host receiving an NDEATH marks that edge node offline at its own UTC time.",
    ),
    (
        "tck-id-operational-behavior-edge-node-termination-host-action-ndeath-node-tags-stale",
        _HOST,
        _MUST,
        _OTH,
        "A host receiving an NDEATH marks that node's birthed metrics stale.",
    ),
    (
        "tck-id-operational-behavior-edge-node-termination-host-action-ndeath-devices-offline",
        _HOST,
        _MUST,
        _OTH,
        "A host receiving an NDEATH marks that node's devices offline.",
    ),
    (
        "tck-id-operational-behavior-edge-node-termination-host-action-ndeath-devices-tags-stale",
        _HOST,
        _MUST,
        _OTH,
        "A host receiving an NDEATH marks those devices' birthed metrics stale.",
    ),
    (
        "tck-id-operational-behavior-edge-node-termination-host-offline",
        _EDGE,
        _MUST,
        _PHI,
        "An edge node leaves the server when its Primary Host reports itself offline.",
    ),
    (
        "tck-id-operational-behavior-edge-node-termination-host-offline-reconnect",
        _EDGE,
        _MUST,
        _PHI,
        "Having left for that reason, the edge node tries the next server in its list.",
    ),
    (
        "tck-id-operational-behavior-edge-node-termination-host-offline-timestamp",
        _EDGE,
        _MUST,
        _PHI,
        "An edge node ignores an offline STATE message whose timestamp is stale.",
    ),
    (
        "tck-id-message-flow-device-dcmd-subscribe",
        _EDGE,
        _MUST,
        _TRN,
        "A device that accepts writes has its edge node subscribe to the device's DCMD topic.",
    ),
    (
        "tck-id-message-flow-device-birth-publish-nbirth-wait",
        _EDGE,
        _MUST,
        None,
        "A DBIRTH follows an NBIRTH sent in the same session.",
    ),
    (
        "tck-id-message-flow-device-birth-publish-dbirth-topic",
        _EDGE,
        _MUST,
        None,
        "The DBIRTH is addressed as spBv1.0, group id, DBIRTH, edge node id, device id.",
    ),
    (
        "tck-id-message-flow-device-birth-publish-dbirth-match-edge-node-topic",
        _EDGE,
        _MUST,
        None,
        "The DBIRTH topic repeats the group id and edge node id of the preceding NBIRTH.",
    ),
    (
        "tck-id-message-flow-device-birth-publish-dbirth-payload",
        _EDGE,
        _MUST,
        _ENC,
        "The DBIRTH payload is a Sparkplug protobuf-encoded payload.",
    ),
    (
        "tck-id-message-flow-device-birth-publish-dbirth-qos",
        _EDGE,
        _MUST,
        None,
        "The DBIRTH is published at QoS 0.",
    ),
    (
        "tck-id-message-flow-device-birth-publish-dbirth-retained",
        _EDGE,
        _MUST,
        None,
        "The DBIRTH is published with the retain flag clear.",
    ),
    (
        "tck-id-message-flow-device-birth-publish-dbirth-payload-seq",
        _EDGE,
        _MUST,
        None,
        "The DBIRTH sequence number is inside the byte range and one above the previous message.",
    ),
    (
        "tck-id-operational-behavior-device-ddeath",
        _EDGE,
        _MUST,
        None,
        "An edge node that loses a device publishes a DDEATH on the device's behalf.",
    ),
    (
        "tck-id-operational-behavior-edge-node-termination-host-action-ddeath-devices-offline",
        _HOST,
        _MUST,
        _OTH,
        "A host receiving a DDEATH marks that device offline at the payload timestamp.",
    ),
    (
        "tck-id-operational-behavior-edge-node-termination-host-action-ddeath-devices-tags-stale",
        _HOST,
        _MUST,
        _OTH,
        "A host receiving a DDEATH marks that device's birthed metrics stale.",
    ),
    (
        "tck-id-operational-behavior-host-reordering-param",
        _HOST,
        _SHOULD,
        _OTH,
        "A Host Application offers a configurable reorder timeout.",
    ),
    (
        "tck-id-operational-behavior-host-reordering-start",
        _HOST,
        _MUST,
        _OTH,
        "A host with that timeout starts a timer on an out-of-order sequence number.",
    ),
    (
        "tck-id-operational-behavior-host-reordering-rebirth",
        _HOST,
        _MUST,
        _OTH,
        "A host whose reorder timer expires requests a rebirth.",
    ),
    (
        "tck-id-operational-behavior-host-reordering-success",
        _HOST,
        _MUST,
        _OTH,
        "A host that receives the missing messages in time cancels the timer.",
    ),
    (
        "tck-id-operational-behavior-primary-application-state-with-multiple-servers-state-subs",
        _HOST,
        _MUST,
        _OTH,
        "A Primary Host across several servers publishes its STATE birth on each of them.",
    ),
    (
        "tck-id-operational-behavior-primary-application-state-with-multiple-servers-state",
        _HOST,
        _MUST,
        _OTH,
        "A Primary Host republishes its STATE birth on every new session with a server.",
    ),
    (
        "tck-id-operational-behavior-primary-application-state-with-multiple-servers-single-server",
        _EDGE,
        _MUST,
        _PHI,
        "An edge node holds a connection to at most one server at a time.",
    ),
    (
        "tck-id-operational-behavior-primary-application-state-with-multiple-servers-walk",
        _EDGE,
        _MUST,
        _PHI,
        "An edge node whose Primary Host goes offline moves to the next available server.",
    ),
    (
        "tck-id-operational-behavior-edge-node-birth-sequence-wait",
        _EDGE,
        _MUST,
        _PHI,
        "An edge node holds its birth sequence until it sees an online STATE message.",
    ),
    (
        "tck-id-operational-behavior-host-application-host-id",
        _HOST,
        _MUST,
        _OTH,
        "The Sparkplug host id is unique across the infrastructure.",
    ),
    (
        "tck-id-operational-behavior-host-application-connect-will",
        _HOST,
        _MUST,
        _OTH,
        "A Host Application's CONNECT carries a will message.",
    ),
    (
        "tck-id-operational-behavior-host-application-connect-will-topic",
        _HOST,
        _MUST,
        _OTH,
        "That will is addressed as spBv1.0, STATE, host id.",
    ),
    (
        "tck-id-operational-behavior-host-application-connect-will-payload",
        _HOST,
        _MUST,
        _OTH,
        "That will payload is JSON with a false online flag and a timestamp.",
    ),
    (
        "tck-id-operational-behavior-host-application-connect-will-qos",
        _HOST,
        _MUST,
        _OTH,
        "That will is registered at QoS 1.",
    ),
    (
        "tck-id-operational-behavior-host-application-connect-will-retained",
        _HOST,
        _MUST,
        _OTH,
        "That will is registered with the retain flag set.",
    ),
    (
        "tck-id-operational-behavior-host-application-connect-birth",
        _HOST,
        _MUST,
        _OTH,
        "A Host Application publishes its birth immediately after connecting.",
    ),
    (
        "tck-id-operational-behavior-host-application-connect-birth-topic",
        _HOST,
        _MUST,
        _OTH,
        "That birth is addressed as spBv1.0, STATE, host id.",
    ),
    (
        "tck-id-operational-behavior-host-application-connect-birth-payload",
        _HOST,
        _MUST,
        _OTH,
        "That birth payload is JSON with a true online flag and a timestamp.",
    ),
    (
        "tck-id-operational-behavior-host-application-connect-birth-qos",
        _HOST,
        _MUST,
        _OTH,
        "That birth is published at QoS 1.",
    ),
    (
        "tck-id-operational-behavior-host-application-connect-birth-retained",
        _HOST,
        _MUST,
        _OTH,
        "That birth is published with the retain flag set.",
    ),
    (
        "tck-id-operational-behavior-host-application-multi-server-timestamp",
        _HOST,
        _MUST,
        _OTH,
        "A Host Application tracks a STATE timestamp per server.",
    ),
    (
        "tck-id-operational-behavior-host-application-termination",
        _HOST,
        _MUST,
        _OTH,
        "A Host Application closing its own connection publishes a death message.",
    ),
    (
        "tck-id-operational-behavior-host-application-death-topic",
        _HOST,
        _MUST,
        _OTH,
        "That death is addressed as spBv1.0, STATE, host id.",
    ),
    (
        "tck-id-operational-behavior-host-application-death-payload",
        _HOST,
        _MUST,
        _OTH,
        "That death payload is JSON with a false online flag and a timestamp.",
    ),
    (
        "tck-id-operational-behavior-host-application-death-qos",
        _HOST,
        _MUST,
        _OTH,
        "That death is published at QoS 1.",
    ),
    (
        "tck-id-operational-behavior-host-application-death-retained",
        _HOST,
        _MUST,
        _OTH,
        "That death is published with the retain flag set.",
    ),
    (
        "tck-id-operational-behavior-host-application-disconnect-intentional",
        _HOST,
        _MAY,
        _OTH,
        "A DISCONNECT packet may follow that death message.",
    ),
    (
        "tck-id-operational-behavior-data-publish-nbirth",
        _EDGE,
        _MUST,
        None,
        "An NBIRTH declares every node metric the session will ever publish.",
    ),
    (
        "tck-id-operational-behavior-data-publish-nbirth-values",
        _EDGE,
        _MUST,
        _ENC,
        "An NBIRTH metric holds its current value, or is flagged null with no value present.",
    ),
    (
        "tck-id-operational-behavior-data-publish-nbirth-change",
        _EDGE,
        _SHOULD,
        None,
        "An NDATA goes out only when a node metric changes.",
    ),
    (
        "tck-id-operational-behavior-data-publish-nbirth-order",
        _EDGE,
        _MUST,
        None,
        "Non-historical metric values in an NBIRTH or NDATA appear in chronological order.",
    ),
    (
        "tck-id-operational-behavior-data-publish-dbirth",
        _EDGE,
        _MUST,
        None,
        "A DBIRTH declares every metric that device will ever publish in the session.",
    ),
    (
        "tck-id-operational-behavior-data-publish-dbirth-values",
        _EDGE,
        _MUST,
        _ENC,
        "A DBIRTH metric holds its current value, or is flagged null with no value present.",
    ),
    (
        "tck-id-operational-behavior-data-publish-dbirth-change",
        _EDGE,
        _SHOULD,
        None,
        "A DDATA goes out only when a device metric changes.",
    ),
    (
        "tck-id-operational-behavior-data-publish-dbirth-order",
        _EDGE,
        _MUST,
        None,
        "Non-historical metric values in a DBIRTH or DDATA appear in chronological order.",
    ),
    (
        "tck-id-operational-behavior-data-commands-rebirth-name",
        _EDGE,
        _MUST,
        None,
        "An NBIRTH carries a metric named Node Control/Rebirth.",
    ),
    (
        "tck-id-operational-behavior-data-commands-rebirth-name-aliases",
        _EDGE,
        _MUST,
        None,
        "An edge node using aliases gives the Node Control/Rebirth metric no alias in its NBIRTH.",
    ),
    (
        "tck-id-operational-behavior-data-commands-rebirth-datatype",
        _EDGE,
        _MUST,
        None,
        "The NBIRTH's Node Control/Rebirth metric has the Boolean datatype.",
    ),
    (
        "tck-id-operational-behavior-data-commands-rebirth-value",
        _EDGE,
        _MUST,
        None,
        "The NBIRTH's Node Control/Rebirth metric holds the value false.",
    ),
    (
        "tck-id-operational-behavior-data-commands-ncmd-rebirth-verb",
        _HOST,
        _MUST,
        _OTH,
        "A rebirth request travels as an NCMD.",
    ),
    (
        "tck-id-operational-behavior-data-commands-ncmd-rebirth-name",
        _HOST,
        _MUST,
        None,
        "A rebirth request names the metric Node Control/Rebirth.",
    ),
    (
        "tck-id-operational-behavior-data-commands-ncmd-rebirth-value",
        _HOST,
        _MUST,
        None,
        "A rebirth request carries the value true.",
    ),
    (
        "tck-id-operational-behavior-data-commands-rebirth-action-1",
        _EDGE,
        _MUST,
        None,
        "An edge node given a rebirth request stops sending data messages at once.",
    ),
    (
        "tck-id-operational-behavior-data-commands-rebirth-action-2",
        _EDGE,
        _MUST,
        None,
        "It then sends a complete birth sequence: the NBIRTH and every DBIRTH.",
    ),
    (
        "tck-id-operational-behavior-data-commands-rebirth-action-3",
        _EDGE,
        _MUST,
        None,
        "That NBIRTH repeats the bdSeq value from the will of the current CONNECT.",
    ),
    (
        "tck-id-operational-behavior-data-commands-ncmd-verb",
        _HOST,
        _MUST,
        _OTH,
        "A node-level command travels as an NCMD.",
    ),
    (
        "tck-id-operational-behavior-data-commands-ncmd-metric-name",
        _HOST,
        _SHOULD,
        _OTH,
        "An NCMD names a metric the node's NBIRTH declared.",
    ),
    (
        "tck-id-operational-behavior-data-commands-ncmd-metric-value",
        _HOST,
        _MUST,
        _OTH,
        "An NCMD carries a value compatible with the metric it writes.",
    ),
    (
        "tck-id-operational-behavior-data-commands-dcmd-verb",
        _HOST,
        _MUST,
        _OTH,
        "A device-level command travels as a DCMD.",
    ),
    (
        "tck-id-operational-behavior-data-commands-dcmd-metric-name",
        _HOST,
        _SHOULD,
        _OTH,
        "A DCMD names a metric the device's DBIRTH declared.",
    ),
    (
        "tck-id-operational-behavior-data-commands-dcmd-metric-value",
        _HOST,
        _MUST,
        _OTH,
        "A DCMD carries a value compatible with the metric it writes.",
    ),
    # -------------------------------------------------------------- 6 Payloads
    (
        "tck-id-payloads-timestamp-in-UTC",
        _EDGE,
        _MUST,
        None,
        "The payload timestamp is a UTC reading.",
    ),
    (
        "tck-id-payloads-sequence-num-always-included",
        _EDGE,
        _MUST,
        None,
        "Every message from an edge node except an NDEATH carries a sequence number.",
    ),
    (
        "tck-id-payloads-sequence-num-req-nbirth",
        _EDGE,
        _MUST,
        None,
        "An NBIRTH sequence number lies inside the byte range zero to 255.",
    ),
    (
        "tck-id-payloads-sequence-num-incrementing",
        _EDGE,
        _MUST,
        None,
        "Sequence numbers after an NBIRTH rise by one and return to zero after 255.",
    ),
    (
        "tck-id-payloads-name-requirement",
        _EDGE,
        _MUST,
        None,
        "A metric carries its name unless the edge node is using aliases.",
    ),
    (
        "tck-id-payloads-alias-uniqueness",
        _EDGE,
        _MUST,
        None,
        "An alias given at birth is unique across the edge node's whole metric set.",
    ),
    (
        "tck-id-payloads-alias-birth-requirement",
        _EDGE,
        _MUST,
        None,
        "An NBIRTH or DBIRTH metric carries both its name and its alias.",
    ),
    (
        "tck-id-payloads-alias-data-cmd-requirement",
        _EDGE,
        _MUST,
        None,
        "An NDATA, DDATA, NCMD, or DCMD metric carries only the alias, with the name left out.",
    ),
    (
        "tck-id-payloads-name-birth-data-requirement",
        _EDGE,
        _MUST,
        None,
        "Every metric in an NBIRTH, DBIRTH, NDATA, or DDATA carries a timestamp.",
    ),
    (
        "tck-id-payloads-name-cmd-requirement",
        _HOST,
        _MAY,
        _OTH,
        "A metric in an NCMD or DCMD may carry a timestamp.",
    ),
    (
        "tck-id-payloads-metric-timestamp-in-UTC",
        _EDGE,
        _MUST,
        None,
        "The metric timestamp is a UTC reading.",
    ),
    (
        "tck-id-payloads-metric-datatype-value-type",
        _EDGE,
        _MUST,
        _ENC,
        "The datatype field is encoded as an unsigned 32-bit integer.",
    ),
    (
        "tck-id-payloads-metric-datatype-value",
        _EDGE,
        _MUST,
        None,
        "The datatype is one of the values the payload definition enumerates.",
    ),
    (
        "tck-id-payloads-metric-datatype-req",
        _EDGE,
        _MUST,
        None,
        "Each metric in an NBIRTH or DBIRTH carries its datatype.",
    ),
    (
        "tck-id-payloads-metric-datatype-not-req",
        _EDGE,
        _SHOULD,
        None,
        "A metric in an NDATA, NCMD, DDATA, or DCMD leaves the datatype out.",
    ),
    (
        "tck-id-payloads-propertyset-keys-array-size",
        _EDGE,
        _MUST,
        _ENC,
        "A PropertySet holds as many keys as it holds values.",
    ),
    (
        "tck-id-payloads-propertyset-values-array-size",
        _EDGE,
        _MUST,
        _ENC,
        "A PropertySet holds as many values as it holds keys.",
    ),
    (
        "tck-id-payloads-metric-propertyvalue-type-type",
        _EDGE,
        _MUST,
        _ENC,
        "A property value's type field is encoded as an unsigned 32-bit integer.",
    ),
    (
        "tck-id-payloads-metric-propertyvalue-type-value",
        _EDGE,
        _MUST,
        _ENC,
        "A property value's type is one of the enumerated datatypes.",
    ),
    (
        "tck-id-payloads-metric-propertyvalue-type-req",
        _EDGE,
        _MUST,
        _ENC,
        "A property value definition in an NBIRTH or DBIRTH carries its type.",
    ),
    (
        "tck-id-payloads-propertyset-quality-value-type",
        _EDGE,
        _MUST,
        _ENC,
        "The Quality property's type field is the signed 32-bit integer code.",
    ),
    (
        "tck-id-payloads-propertyset-quality-value-value",
        _EDGE,
        _MUST,
        None,
        "The Quality property holds one of the codes 0, 192, or 500.",
    ),
    (
        "tck-id-payloads-dataset-column-size",
        _EDGE,
        _MUST,
        _TPL,
        "A DataSet's column count is an unsigned 64-bit integer.",
    ),
    (
        "tck-id-payloads-dataset-column-num-headers",
        _EDGE,
        _MUST,
        _TPL,
        "A DataSet holds as many column headers as it holds types.",
    ),
    (
        "tck-id-payloads-dataset-types-def",
        _EDGE,
        _MUST,
        _TPL,
        "A DataSet's types are unsigned 32-bit integers naming the column datatypes.",
    ),
    (
        "tck-id-payloads-dataset-types-num",
        _EDGE,
        _MUST,
        _TPL,
        "A DataSet holds as many types as it holds columns.",
    ),
    (
        "tck-id-payloads-dataset-types-type",
        _EDGE,
        _MUST,
        _TPL,
        "Each DataSet type entry is an unsigned 32-bit integer.",
    ),
    (
        "tck-id-payloads-dataset-types-value",
        _EDGE,
        _MUST,
        _TPL,
        "Each DataSet type entry is one of the enumerated datatypes.",
    ),
    (
        "tck-id-payloads-dataset-parameter-type-req",
        _EDGE,
        _MUST,
        _TPL,
        "Every DataSet carries its types array.",
    ),
    (
        "tck-id-payloads-template-dataset-value",
        _EDGE,
        _MUST,
        _TPL,
        "A template DataSet value uses one of the permitted protobuf scalar types.",
    ),
    (
        "tck-id-payloads-template-definition-nbirth-only",
        _EDGE,
        _MUST,
        _TPL,
        "Template definitions appear only in NBIRTH messages.",
    ),
    (
        "tck-id-payloads-template-definition-is-definition",
        _EDGE,
        _MUST,
        _TPL,
        "A template definition sets its is-definition flag true.",
    ),
    (
        "tck-id-payloads-template-definition-ref",
        _EDGE,
        _MUST,
        _TPL,
        "A template definition leaves the template reference field out.",
    ),
    (
        "tck-id-payloads-template-definition-members",
        _EDGE,
        _MUST,
        _TPL,
        "A template definition lists every member its instances will ever carry.",
    ),
    (
        "tck-id-payloads-template-definition-nbirth",
        _EDGE,
        _MUST,
        _TPL,
        "Every template instance published has its definition in the NBIRTH.",
    ),
    (
        "tck-id-payloads-template-definition-parameters",
        _EDGE,
        _MUST,
        _TPL,
        "A template definition lists every parameter its instances will carry.",
    ),
    (
        "tck-id-payloads-template-definition-parameters-default",
        _EDGE,
        _MAY,
        _TPL,
        "A template definition may give default values for its parameters.",
    ),
    (
        "tck-id-payloads-template-instance-is-definition",
        _EDGE,
        _MUST,
        _TPL,
        "A template instance sets its is-definition flag false.",
    ),
    (
        "tck-id-payloads-template-instance-ref",
        _EDGE,
        _MUST,
        _TPL,
        "A template instance names the definition it refers to.",
    ),
    (
        "tck-id-payloads-template-instance-members",
        _EDGE,
        _MUST,
        _TPL,
        "A template instance carries only members its definition declared.",
    ),
    (
        "tck-id-payloads-template-instance-members-birth",
        _EDGE,
        _MUST,
        _TPL,
        "A template instance in a birth carries every member of its definition.",
    ),
    (
        "tck-id-payloads-template-instance-members-data",
        _EDGE,
        _MAY,
        _TPL,
        "A template instance in a data message may carry a subset of members.",
    ),
    (
        "tck-id-payloads-template-instance-parameters",
        _EDGE,
        _MAY,
        _TPL,
        "A template instance may carry values for its definition's parameters.",
    ),
    (
        "tck-id-payloads-template-version",
        _EDGE,
        _MUST,
        _TPL,
        "A template version, when present, is a UTF-8 string.",
    ),
    (
        "tck-id-payloads-template-ref-definition",
        _EDGE,
        _MUST,
        _TPL,
        "The template reference is absent on a definition.",
    ),
    (
        "tck-id-payloads-template-ref-instance",
        _EDGE,
        _MUST,
        _TPL,
        "The template reference on an instance is the definition's name.",
    ),
    (
        "tck-id-payloads-template-is-definition",
        _EDGE,
        _MUST,
        _TPL,
        "Every template definition and instance carries the is-definition flag.",
    ),
    (
        "tck-id-payloads-template-is-definition-definition",
        _EDGE,
        _MUST,
        _TPL,
        "The is-definition flag is true on a definition.",
    ),
    (
        "tck-id-payloads-template-is-definition-instance",
        _EDGE,
        _MUST,
        _TPL,
        "The is-definition flag is false on an instance.",
    ),
    (
        "tck-id-payloads-template-parameter-name-required",
        _EDGE,
        _MUST,
        _TPL,
        "Every template parameter definition carries a name.",
    ),
    (
        "tck-id-payloads-template-parameter-name-type",
        _EDGE,
        _MUST,
        _TPL,
        "A template parameter name is a UTF-8 string.",
    ),
    (
        "tck-id-payloads-template-parameter-value-type",
        _EDGE,
        _MUST,
        _TPL,
        "A template parameter's type field is an unsigned 32-bit integer.",
    ),
    (
        "tck-id-payloads-template-parameter-type-value",
        _EDGE,
        _MUST,
        _TPL,
        "A template parameter's type is one of the enumerated datatypes.",
    ),
    (
        "tck-id-payloads-template-parameter-type-req",
        _EDGE,
        _MUST,
        _TPL,
        "A template parameter definition in a birth carries its type.",
    ),
    (
        "tck-id-payloads-template-parameter-value",
        _EDGE,
        _MUST,
        _TPL,
        "A template parameter value uses one of the permitted protobuf scalar types.",
    ),
    (
        "tck-id-payloads-nbirth-timestamp",
        _EDGE,
        _MUST,
        None,
        "An NBIRTH payload carries the instant it was published.",
    ),
    (
        "tck-id-payloads-nbirth-edge-node-descriptor",
        _EDGE,
        _MUST,
        _DEP,
        "Every Edge Node Descriptor in the infrastructure is unique.",
    ),
    (
        "tck-id-payloads-nbirth-seq",
        _EDGE,
        _MUST,
        None,
        "An NBIRTH carries a sequence number inside the byte range zero to 255.",
    ),
    ("tck-id-payloads-nbirth-bdseq", _EDGE, _MUST, None, "An NBIRTH carries a bdSeq metric."),
    (
        "tck-id-payloads-nbirth-bdseq-repeat",
        _EDGE,
        _MUST,
        None,
        "The NBIRTH bdSeq repeats the value sent in the preceding CONNECT will.",
    ),
    (
        "tck-id-payloads-nbirth-rebirth-req",
        _EDGE,
        _MUST,
        None,
        "An NBIRTH carries a Node Control/Rebirth metric holding false.",
    ),
    ("tck-id-payloads-nbirth-qos", _EDGE, _MUST, None, "An NBIRTH is published at QoS 0."),
    (
        "tck-id-payloads-nbirth-retain",
        _EDGE,
        _MUST,
        None,
        "An NBIRTH is published with the retain flag clear.",
    ),
    (
        "tck-id-payloads-dbirth-timestamp",
        _EDGE,
        _MUST,
        None,
        "A DBIRTH payload carries the instant it was published.",
    ),
    ("tck-id-payloads-dbirth-seq", _EDGE, _MUST, None, "A DBIRTH carries a sequence number."),
    (
        "tck-id-payloads-dbirth-seq-inc",
        _EDGE,
        _MUST,
        None,
        "A DBIRTH sequence number is one above the previous, returning to zero after 255.",
    ),
    (
        "tck-id-payloads-dbirth-order",
        _EDGE,
        _MUST,
        None,
        "Every DBIRTH follows the NBIRTH and precedes any NDATA or DDATA.",
    ),
    ("tck-id-payloads-dbirth-qos", _EDGE, _MUST, None, "A DBIRTH is published at QoS 0."),
    (
        "tck-id-payloads-dbirth-retain",
        _EDGE,
        _MUST,
        None,
        "A DBIRTH is published with the retain flag clear.",
    ),
    (
        "tck-id-payloads-ndata-timestamp",
        _EDGE,
        _MUST,
        None,
        "An NDATA payload carries the instant it was published.",
    ),
    ("tck-id-payloads-ndata-seq", _EDGE, _MUST, None, "An NDATA carries a sequence number."),
    (
        "tck-id-payloads-ndata-seq-inc",
        _EDGE,
        _MUST,
        None,
        "An NDATA sequence number is one above the previous, returning to zero after 255.",
    ),
    (
        "tck-id-payloads-ndata-order",
        _EDGE,
        _MUST,
        None,
        "No NDATA leaves the edge node until the NBIRTH and every DBIRTH have gone out.",
    ),
    ("tck-id-payloads-ndata-qos", _EDGE, _MUST, None, "An NDATA is published at QoS 0."),
    (
        "tck-id-payloads-ndata-retain",
        _EDGE,
        _MUST,
        None,
        "An NDATA is published with the retain flag clear.",
    ),
    (
        "tck-id-payloads-ddata-timestamp",
        _EDGE,
        _MUST,
        None,
        "A DDATA payload carries the instant it was published.",
    ),
    ("tck-id-payloads-ddata-seq", _EDGE, _MUST, None, "A DDATA carries a sequence number."),
    (
        "tck-id-payloads-ddata-seq-inc",
        _EDGE,
        _MUST,
        None,
        "A DDATA sequence number is one above the previous, returning to zero after 255.",
    ),
    (
        "tck-id-payloads-ddata-order",
        _EDGE,
        _MUST,
        None,
        "No DDATA leaves the edge node until the NBIRTH and every DBIRTH have gone out.",
    ),
    ("tck-id-payloads-ddata-qos", _EDGE, _MUST, None, "A DDATA is published at QoS 0."),
    (
        "tck-id-payloads-ddata-retain",
        _EDGE,
        _MUST,
        None,
        "A DDATA is published with the retain flag clear.",
    ),
    (
        "tck-id-payloads-ncmd-timestamp",
        _HOST,
        _MUST,
        _OTH,
        "An NCMD payload carries the instant it was published.",
    ),
    ("tck-id-payloads-ncmd-seq", _HOST, _MUST, _OTH, "An NCMD carries no sequence number."),
    ("tck-id-payloads-ncmd-qos", _HOST, _MUST, None, "An NCMD is published at QoS 0."),
    (
        "tck-id-payloads-ncmd-retain",
        _HOST,
        _MUST,
        None,
        "An NCMD is published with the retain flag clear.",
    ),
    (
        "tck-id-payloads-dcmd-timestamp",
        _HOST,
        _MUST,
        _OTH,
        "A DCMD payload carries the instant it was published.",
    ),
    ("tck-id-payloads-dcmd-seq", _HOST, _MUST, _OTH, "A DCMD carries no sequence number."),
    ("tck-id-payloads-dcmd-qos", _HOST, _MUST, None, "A DCMD is published at QoS 0."),
    (
        "tck-id-payloads-dcmd-retain",
        _HOST,
        _MUST,
        None,
        "A DCMD is published with the retain flag clear.",
    ),
    ("tck-id-payloads-ndeath-seq", _EDGE, _MUST, None, "An NDEATH carries no sequence number."),
    (
        "tck-id-payloads-ndeath-will-message",
        _EDGE,
        _MUST,
        None,
        "The NDEATH is the will registered in the CONNECT packet.",
    ),
    (
        "tck-id-payloads-ndeath-will-message-qos",
        _EDGE,
        _MUST,
        None,
        "The NDEATH will is registered at QoS 1.",
    ),
    (
        "tck-id-payloads-ndeath-will-message-retain",
        _EDGE,
        _MUST,
        None,
        "The NDEATH will is registered with the retain flag clear.",
    ),
    (
        "tck-id-payloads-ndeath-bdseq",
        _EDGE,
        _MUST,
        None,
        "The NDEATH bdSeq is the value the matching NBIRTH will carry.",
    ),
    (
        "tck-id-payloads-ndeath-will-message-publisher",
        _EDGE,
        _SHOULD,
        None,
        "An edge node publishes an NDEATH itself before disconnecting on purpose.",
    ),
    (
        "tck-id-payloads-ndeath-will-message-publisher-disconnect-mqtt311",
        _EDGE,
        _MUST,
        _TRN,
        "On MQTT 3.1.1 that NDEATH precedes the DISCONNECT packet.",
    ),
    (
        "tck-id-payloads-ndeath-will-message-publisher-disconnect-mqtt50",
        _EDGE,
        _MUST,
        _TRN,
        "On MQTT 5.0 the DISCONNECT carries the disconnect-with-will reason code.",
    ),
    (
        "tck-id-payloads-ddeath-timestamp",
        _EDGE,
        _MUST,
        None,
        "A DDEATH payload carries the instant it was published.",
    ),
    ("tck-id-payloads-ddeath-seq", _EDGE, _MUST, None, "A DDEATH carries a sequence number."),
    (
        "tck-id-payloads-ddeath-seq-inc",
        _EDGE,
        _MUST,
        None,
        "A DDEATH sequence number is one above the previous, returning to zero after 255.",
    ),
    (
        "tck-id-payloads-ddeath-seq-number",
        _EDGE,
        _MUST,
        None,
        "The DDEATH sequence number lets a host order it against the rest of the stream.",
    ),
    (
        "tck-id-payloads-state-will-message",
        _HOST,
        _MUST,
        _OTH,
        "A Host Application registers its STATE will in the CONNECT packet.",
    ),
    (
        "tck-id-payloads-state-will-message-qos",
        _HOST,
        _MUST,
        _OTH,
        "That STATE will is registered at QoS 1.",
    ),
    (
        "tck-id-payloads-state-will-message-retain",
        _HOST,
        _MUST,
        _OTH,
        "That STATE will is registered with the retain flag set.",
    ),
    (
        "tck-id-payloads-state-will-message-payload",
        _HOST,
        _MUST,
        _OTH,
        "That STATE will payload is JSON with a false online flag and a timestamp.",
    ),
    (
        "tck-id-payloads-state-subscribe",
        _HOST,
        _MUST,
        _OTH,
        "A Host Application subscribes to its own STATE topic after connecting.",
    ),
    (
        "tck-id-payloads-state-birth",
        _HOST,
        _MUST,
        _OTH,
        "A Host Application then publishes its STATE birth on that topic.",
    ),
    (
        "tck-id-payloads-state-birth-payload",
        _HOST,
        _MUST,
        _OTH,
        "That STATE birth payload is JSON with a true online flag and a timestamp.",
    ),
    # ---------------------------------------------------------- 10 Conformance
    (
        "tck-id-conformance-primary-host",
        _HOST,
        _MUST,
        _OTH,
        "A Host Application publishes STATE messages as its birth and death certificates.",
    ),
    (
        "tck-id-conformance-mqtt-qos0",
        _SERVER,
        _MUST,
        _OTH,
        "A conformant server supports publish and subscribe at QoS 0.",
    ),
    (
        "tck-id-conformance-mqtt-qos1",
        _SERVER,
        _MUST,
        _OTH,
        "A conformant server supports publish and subscribe at QoS 1.",
    ),
    (
        "tck-id-conformance-mqtt-will-messages",
        _SERVER,
        _MUST,
        _OTH,
        "A conformant server supports will messages with retain and QoS 1.",
    ),
    (
        "tck-id-conformance-mqtt-retained",
        _SERVER,
        _MUST,
        _OTH,
        "A conformant server supports the retain flag in full.",
    ),
    (
        "tck-id-conformance-mqtt-aware-basic",
        _SERVER,
        _MUST,
        _OTH,
        "A Sparkplug Aware server meets everything a conformant server meets.",
    ),
    (
        "tck-id-conformance-mqtt-aware-store",
        _SERVER,
        _MUST,
        _OTH,
        "A Sparkplug Aware server stores the NBIRTH and DBIRTH messages passing through it.",
    ),
    (
        "tck-id-conformance-mqtt-aware-nbirth-mqtt-topic",
        _SERVER,
        _MUST,
        _OTH,
        "It republishes each NBIRTH under the sparkplug certificates topic.",
    ),
    (
        "tck-id-conformance-mqtt-aware-nbirth-mqtt-retain",
        _SERVER,
        _MUST,
        _OTH,
        "It republishes that NBIRTH with the retain flag set.",
    ),
    (
        "tck-id-conformance-mqtt-aware-dbirth-mqtt-topic",
        _SERVER,
        _MUST,
        _OTH,
        "It republishes each DBIRTH under the sparkplug certificates topic.",
    ),
    (
        "tck-id-conformance-mqtt-aware-dbirth-mqtt-retain",
        _SERVER,
        _MUST,
        _OTH,
        "It republishes that DBIRTH with the retain flag set.",
    ),
    (
        "tck-id-conformance-mqtt-aware-ndeath-timestamp",
        _SERVER,
        _MAY,
        _OTH,
        "It may restamp an NDEATH, and then uses the UTC instant of delivery.",
    ),
)

#: Every assertion, keyed by the identifier the specification anchors it with.
ASSERTIONS: Mapping[str, Assertion] = {
    row[0]: Assertion(
        assertion_id=row[0], profile=row[1], level=row[2], statement=row[4], exclusion=row[3]
    )
    for row in _ROWS
}


def assertions_for(profile: Profile) -> tuple[Assertion, ...]:
    """Every assertion constraining one conformance profile."""
    return tuple(a for a in ASSERTIONS.values() if a.profile is profile)


def in_scope_assertions() -> tuple[Assertion, ...]:
    """Every assertion this repository answers for, whatever its profile."""
    return tuple(a for a in ASSERTIONS.values() if a.in_scope)


def exclusions_by_reason(profile: Profile) -> Mapping[Exclusion, tuple[str, ...]]:
    """The out-of-scope identifiers of one profile, grouped by the reason."""
    grouped: dict[Exclusion, list[str]] = {}
    for assertion in assertions_for(profile):
        if assertion.exclusion is not None:
            grouped.setdefault(assertion.exclusion, []).append(assertion.assertion_id)
    return {reason: tuple(ids) for reason, ids in grouped.items()}


# ----------------------------------------------------------------- the fixture

#: The edge node the runner exercises. Two devices, because several assertions
#: are about one device's stream relative to another's and a single-device node
#: satisfies them by accident.
_GROUP_ID = "twinflow:dc-01:receiving"
_EDGE_NODE_ID = "inbound-line-01"
_PORTAL = "portal-03"
_CONVEYOR = "conveyor-02"

_NODE_METRICS: tuple[MetricSpec, ...] = (
    MetricSpec(name="sf_dropped_records", datatype=DataType.UInt64, unit="1"),
)
_DEVICE_METRICS: Mapping[str, tuple[MetricSpec, ...]] = {
    _PORTAL: (
        MetricSpec(name="read_rate", datatype=DataType.Float, unit="1", eng_low=0.0, eng_high=1.0),
        MetricSpec(name="unique_epcs", datatype=DataType.UInt32, unit="1"),
    ),
    _CONVEYOR: (MetricSpec(name="motor_temp_c", datatype=DataType.Double, unit="Cel"),),
}

#: Epoch milliseconds at 2020-01-01T00:00:00Z. A payload timestamp at or above
#: this reads as a UTC wall-clock instant; one below it does not, which is how
#: the two UTC assertions are decided without a second time source.
_UTC_FLOOR_MS = 1_577_836_800_000


class _CheckFailed(Exception):
    """One assertion's observation came out the wrong way."""


def _require(condition: bool, detail: str) -> None:
    """Fail the assertion under check unless the observation holds."""
    if not condition:
        raise _CheckFailed(detail)


def _refuses(call: Callable[[], object]) -> bool:
    """Whether the session refuses a call rather than performing it."""
    try:
        call()
    except (ValueError, RuntimeError, KeyError):
        return True
    return False


@dataclass(frozen=True, slots=True)
class _Trace:
    """One conformant session, played through, with every message kept.

    The runner reads its observations from this rather than from the session's
    internals, because an assertion is about what an edge node puts on the
    wire and a check that reaches into private state would pass for a device
    that publishes something else entirely.
    """

    clock: Clock
    session: EdgeNodeSession
    will: WillRegistration
    nbirth: Message
    dbirths: Mapping[str, Message]
    ndata: Message
    ddata: Message
    ddeath: Message
    rebirth: tuple[Message, ...]

    def metric(self, message: Message, name: str) -> Metric:
        """One named metric of a birth message."""
        for candidate in message.payload.metrics:
            if candidate.name == name:
                return candidate
        raise _CheckFailed(f"{message.message_type} carries no metric named {name!r}")

    def fresh(self) -> EdgeNodeSession:
        """A second session, for probing an ordering the trace does not take."""
        return _new_session(self.clock)

    def fresh_born(self) -> EdgeNodeSession:
        """A second session carried through its whole birth sequence."""
        session = self.fresh()
        session.connect()
        session.node_birth()
        for device in sorted(_DEVICE_METRICS):
            session.device_birth(device)
        return session


def _new_session(clock: Clock) -> EdgeNodeSession:
    """The edge node under test."""
    return EdgeNodeSession(
        group_id=_GROUP_ID,
        edge_node_id=_EDGE_NODE_ID,
        clock=clock,
        node_metrics=_NODE_METRICS,
        devices=_DEVICE_METRICS,
    )


def _play(clock: Clock) -> _Trace:
    """Run one session through the order the specification lays down."""
    session = _new_session(clock)
    will = session.connect()
    nbirth = session.node_birth()
    dbirths = {device: session.device_birth(device) for device in (_CONVEYOR, _PORTAL)}
    ndata = session.node_data({"sf_dropped_records": 3})
    ddata = session.device_data(_PORTAL, {"read_rate": 0.94})
    ddeath = session.device_death(_CONVEYOR)
    rebirth = session.handle_node_command({REBIRTH_METRIC: True})
    return _Trace(
        clock=clock,
        session=session,
        will=will,
        nbirth=nbirth,
        dbirths=dbirths,
        ndata=ndata,
        ddata=ddata,
        ddeath=ddeath,
        rebirth=rebirth,
    )


#: A check reads a played session and returns what it observed, or raises
#: `_CheckFailed` carrying the observation that falsified the assertion.
Check = Callable[[_Trace], str]


# ------------------------------------------------------------- check factories


def _declared_delivery(message_type: MessageType, qos: int, retain: bool) -> Check:
    """The declared delivery flags of one topic class match the assertion."""

    def check(_trace: _Trace) -> str:
        row = QOS_BY_TOPIC_CLASS[message_type]
        _require(
            (row.qos, row.retain) == (qos, retain),
            f"{message_type} is declared at QoS {row.qos} retain {row.retain}",
        )
        return f"{message_type} declared at QoS {row.qos} retain {row.retain}"

    return check


def _published_delivery(
    pick: Callable[[_Trace], Message], qos: int | None, retain: bool | None
) -> Check:
    """The delivery flags a produced message actually carries."""

    def check(trace: _Trace) -> str:
        message = pick(trace)
        if qos is not None:
            _require(message.qos == qos, f"published at QoS {message.qos}")
        if retain is not None:
            _require(message.retain == retain, f"published with retain {message.retain}")
        return f"published at QoS {message.qos} retain {message.retain}"

    return check


def _topic_is(pick: Callable[[_Trace], Message], expected: str) -> Check:
    """A produced message is addressed exactly as the assertion spells it."""

    def check(trace: _Trace) -> str:
        topic = pick(trace).topic
        _require(topic == expected, f"addressed {topic!r}, not {expected!r}")
        return f"addressed {topic!r}"

    return check


def _payload_timestamp(pick: Callable[[_Trace], Message]) -> Check:
    """A produced message carries a payload timestamp."""

    def check(trace: _Trace) -> str:
        message = pick(trace)
        _require(message.payload.timestamp is not None, "payload carries no timestamp")
        return f"payload timestamp {message.payload.timestamp}"

    return check


def _seq_present(pick: Callable[[_Trace], Message]) -> Check:
    """A produced message carries a sequence number inside the byte range."""

    def check(trace: _Trace) -> str:
        seq = pick(trace).payload.seq
        _require(seq is not None, "payload carries no sequence number")
        assert seq is not None
        _require(0 <= seq < SEQUENCE_MODULUS, f"sequence number {seq} is outside the byte range")
        return f"sequence number {seq}"

    return check


def _seq_follows(pick: Callable[[_Trace], Message], previous: Callable[[_Trace], Message]) -> Check:
    """One message's sequence number is the next one after another's."""

    def check(trace: _Trace) -> str:
        earlier, later = previous(trace).payload.seq, pick(trace).payload.seq
        assert earlier is not None and later is not None
        expected = (earlier + 1) % SEQUENCE_MODULUS
        _require(later == expected, f"sequence went {earlier} then {later}, not {expected}")
        return f"sequence went {earlier} then {later}"

    return check


def _refuses_reserved(build: Callable[[str], object]) -> Check:
    """An identifier holding an MQTT wildcard or separator is refused."""

    def check(_trace: _Trace) -> str:
        for reserved in ("+", "#", "/"):
            _require(
                _refuses(lambda value=f"bad{reserved}id": build(value)),
                f"an identifier holding {reserved!r} reached a topic",
            )
        return "identifiers holding '+', '#', or '/' are refused"

    return check


def _identifier_reaches_topic(
    pick: Callable[[_Trace], Message], level: int, expected: str
) -> Check:
    """An identifier arrives at its topic level as the UTF-8 string it was.

    Stronger than asking whether the value is a `str`, which every Python
    string is. The observation is that the identifier the caller handed over
    is the one a subscriber reads back off the wire, unchanged.
    """

    def check(trace: _Trace) -> str:
        parts = pick(trace).topic.split("/")
        _require(len(parts) > level, f"the topic carries no level {level}")
        value = parts[level]
        _require(value == expected, f"topic level {level} reads {value!r}, not {expected!r}")
        _require(
            isinstance(value, str) and value.encode("utf-8").decode("utf-8") == value,
            f"{value!r} does not round-trip through UTF-8",
        )
        return f"{value!r} reaches topic level {level} unchanged"

    return check


def _every_metric(
    pick: Callable[[_Trace], Message], holds: Callable[[Metric], bool], detail: str
) -> Check:
    """Every metric of one message satisfies a property."""

    def check(trace: _Trace) -> str:
        message = pick(trace)
        for metric in message.payload.metrics:
            _require(holds(metric), f"{message.message_type} has a metric where {detail}")
        return f"every {message.message_type} metric holds: {detail}"

    return check


def _only_changed(publish: Callable[[EdgeNodeSession], Message], expected: int) -> Check:
    """A data message carries only what the caller reported as changed."""

    def check(trace: _Trace) -> str:
        message = publish(trace.fresh_born())
        count = len(message.payload.metrics)
        _require(count == expected, f"{count} metrics published for {expected} changed")
        return f"{count} metrics published for {expected} changed"

    return check


def _undeclared_refused(publish: Callable[[EdgeNodeSession], object]) -> Check:
    """A metric no birth certificate declared cannot reach a data message."""

    def check(trace: _Trace) -> str:
        _require(
            _refuses(lambda: publish(trace.fresh_born())), "an undeclared metric was published"
        )
        return "an undeclared metric is refused"

    return check


def _data_before_all_births(publish: Callable[[EdgeNodeSession], object]) -> Check:
    """Data cannot leave while a device of this edge node has not birthed."""

    def check(trace: _Trace) -> str:
        session = trace.fresh()
        session.connect()
        session.node_birth()
        session.device_birth(_PORTAL)
        _require(
            _refuses(lambda: publish(session)),
            f"data was published while {_CONVEYOR!r} had sent no DBIRTH",
        )
        return "data is refused until every device has birthed"

    return check


def _utc_timestamp(read: Callable[[_Trace], int]) -> Check:
    """A timestamp that reaches the wire is a UTC wall-clock reading."""

    def check(trace: _Trace) -> str:
        value = read(trace)
        _require(
            value >= _UTC_FLOOR_MS,
            f"timestamp {value} is below the year 2020 in epoch milliseconds, so it is a "
            "simulation instant rather than a UTC reading",
        )
        return f"timestamp {value} reads as UTC epoch milliseconds"

    return check


def _bdseq_datatype(pick: Callable[[_Trace], Message]) -> Check:
    """The bdSeq metric carries the datatype the assertion names."""

    def check(trace: _Trace) -> str:
        metric = trace.metric(pick(trace), BDSEQ_METRIC)
        _require(
            metric.datatype is DataType.Int64,
            f"bdSeq carries datatype {metric.datatype!r} rather than Int64",
        )
        return "bdSeq carries datatype Int64"

    return check


# -------------------------------------------------------------- the selections

_IDS = SparkplugIds(group_id=_GROUP_ID, edge_node_id=_EDGE_NODE_ID, device_id="")
_NODE_TOPIC = f"{NAMESPACE}/{_GROUP_ID}"


def _nbirth(trace: _Trace) -> Message:
    return trace.nbirth


def _dbirth(trace: _Trace) -> Message:
    return trace.dbirths[_PORTAL]


def _dbirth_first(trace: _Trace) -> Message:
    return trace.dbirths[_CONVEYOR]


def _ndata(trace: _Trace) -> Message:
    return trace.ndata


def _ddata(trace: _Trace) -> Message:
    return trace.ddata


def _ddeath(trace: _Trace) -> Message:
    return trace.ddeath


def _will(trace: _Trace) -> Message:
    return trace.will.message


# ------------------------------------------------------------- the named checks


def _check_topic_structure(trace: _Trace) -> str:
    """A node topic is four levels and a device topic is five."""
    node = trace.nbirth.topic.split("/")
    device = trace.dbirths[_PORTAL].topic.split("/")
    _require(len(node) == 4, f"a node topic came out with {len(node)} levels")
    _require(len(device) == 5, f"a device topic came out with {len(device)} levels")
    _require(node[0] == device[0] == NAMESPACE, "the first level is not the namespace")
    return "node topics are four levels and device topics are five"


def _check_namespace(trace: _Trace) -> str:
    """The namespace level is the Sparkplug B constant."""
    _require(NAMESPACE == "spBv1.0", f"the namespace constant is {NAMESPACE!r}")
    _require(
        trace.nbirth.topic.startswith(f"{NAMESPACE}/"), "a topic does not open with the namespace"
    )
    return f"the namespace level is {NAMESPACE!r}"


def _check_device_id_required(_trace: _Trace) -> str:
    """A device message type refuses to render without a device id."""
    for message_type in (
        MessageType.DBIRTH,
        MessageType.DDEATH,
        MessageType.DDATA,
        MessageType.DCMD,
    ):
        _require(
            _refuses(lambda mt=message_type: topic_for(_IDS, mt)),
            f"{message_type} rendered a topic with no device id",
        )
        rendered = topic_for(_IDS, message_type, device_id=_PORTAL)
        _require(rendered.endswith(f"/{_PORTAL}"), f"{message_type} dropped the device id")
    return "DBIRTH, DDEATH, DDATA, and DCMD carry a device id level"


def _check_device_id_refused(_trace: _Trace) -> str:
    """A node message type refuses a device id it has no level for."""
    for message_type in (
        MessageType.NBIRTH,
        MessageType.NDEATH,
        MessageType.NDATA,
        MessageType.NCMD,
    ):
        _require(
            _refuses(lambda mt=message_type: topic_for(_IDS, mt, device_id=_PORTAL)),
            f"{message_type} rendered a topic carrying a device id",
        )
    _require(
        _refuses(lambda: topic_for(_IDS, MessageType.STATE)),
        "STATE rendered on an edge node topic",
    )
    return "NBIRTH, NDEATH, NDATA, NCMD, and STATE carry no device id level"


def _check_unique_device_id(trace: _Trace) -> str:
    """Two devices of one edge node are addressed apart."""
    topics = {device: message.topic for device, message in trace.dbirths.items()}
    _require(len(set(topics.values())) == len(topics), "two devices share a DBIRTH topic")
    return f"{len(topics)} devices are addressed apart"


def _check_ncmd_topic(_trace: _Trace) -> str:
    """The NCMD topic is the node form."""
    expected = f"{_NODE_TOPIC}/NCMD/{_EDGE_NODE_ID}"
    rendered = topic_for(_IDS, MessageType.NCMD)
    _require(rendered == expected, f"NCMD addressed {rendered!r}, not {expected!r}")
    return f"NCMD addressed {rendered!r}"


def _check_dcmd_topic(_trace: _Trace) -> str:
    """The DCMD topic is the device form."""
    expected = f"{_NODE_TOPIC}/DCMD/{_EDGE_NODE_ID}/{_PORTAL}"
    rendered = topic_for(_IDS, MessageType.DCMD, device_id=_PORTAL)
    _require(rendered == expected, f"DCMD addressed {rendered!r}, not {expected!r}")
    return f"DCMD addressed {rendered!r}"


def _check_dbirth_matches_node(trace: _Trace) -> str:
    """A DBIRTH repeats the group and edge node of the NBIRTH before it."""
    node = trace.nbirth.topic.split("/")
    device = trace.dbirths[_PORTAL].topic.split("/")
    _require(device[1] == node[1], "the DBIRTH group id differs from the NBIRTH's")
    _require(device[3] == node[3], "the DBIRTH edge node id differs from the NBIRTH's")
    return f"the DBIRTH repeats group {node[1]!r} and edge node {node[3]!r}"


def _check_nbirth_seq_zero(trace: _Trace) -> str:
    """The NBIRTH opens the sequence at zero."""
    seq = trace.nbirth.payload.seq
    _require(seq == 0, f"the NBIRTH carries sequence number {seq}")
    return "the NBIRTH carries sequence number 0"


def _check_seq_always_present(trace: _Trace) -> str:
    """Every message except the NDEATH carries a sequence number."""
    for message in (
        trace.nbirth,
        *trace.dbirths.values(),
        trace.ndata,
        trace.ddata,
        trace.ddeath,
    ):
        _require(
            message.payload.seq is not None, f"{message.message_type} carries no sequence number"
        )
    _require(trace.will.message.payload.seq is None, "the NDEATH carries a sequence number")
    return "every message except the NDEATH carries a sequence number"


def _check_seq_wraps(trace: _Trace) -> str:
    """The sequence rises by one and returns to zero after 255."""
    session = trace.fresh_born()
    seen = [session.node_data({"sf_dropped_records": step}).payload.seq for step in range(300)]
    previous = seen[0]
    assert previous is not None
    for value in seen[1:]:
        assert value is not None
        _require(
            value == (previous + 1) % SEQUENCE_MODULUS,
            f"the sequence went {previous} then {value}",
        )
        previous = value
    _require(0 in seen and 255 in seen, "the sequence never reached the wrap")
    return "the sequence rises by one and returns to zero after 255"


def _check_ndeath_payload(trace: _Trace) -> str:
    """The NDEATH carries the bdSeq metric alone."""
    metrics = trace.will.message.payload.metrics
    _require(len(metrics) == 1, f"the NDEATH carries {len(metrics)} metrics")
    _require(metrics[0].name == BDSEQ_METRIC, f"the NDEATH metric is {metrics[0].name!r}")
    return "the NDEATH carries only the bdSeq metric"


def _check_ndeath_seq_absent(trace: _Trace) -> str:
    """The NDEATH carries no sequence number."""
    seq = trace.will.message.payload.seq
    _require(seq is None, f"the NDEATH carries sequence number {seq}")
    return "the NDEATH carries no sequence number"


def _check_will_is_ndeath(trace: _Trace) -> str:
    """Opening the session hands back an NDEATH to register as the will."""
    _require(
        trace.will.message.message_type is MessageType.NDEATH,
        f"the will is a {trace.will.message.message_type}",
    )
    return "the will registered at CONNECT is an NDEATH"


def _check_will_qos(trace: _Trace) -> str:
    """The will is registered at QoS 1."""
    _require(trace.will.qos == 1, f"the will is registered at QoS {trace.will.qos}")
    return "the will is registered at QoS 1"


def _check_will_retain(trace: _Trace) -> str:
    """The will is registered with the retain flag clear."""
    _require(trace.will.retain is False, f"the will is registered with retain {trace.will.retain}")
    return "the will is registered with the retain flag clear"


def _check_bdseq_present(trace: _Trace) -> str:
    """The NBIRTH carries a bdSeq metric."""
    trace.metric(trace.nbirth, BDSEQ_METRIC)
    return "the NBIRTH carries a bdSeq metric"


def _check_bdseq_matches_will(trace: _Trace) -> str:
    """The NBIRTH bdSeq repeats the will's."""
    born = trace.metric(trace.nbirth, BDSEQ_METRIC).value
    willed = trace.metric(trace.will.message, BDSEQ_METRIC).value
    _require(born == willed, f"the NBIRTH carries bdSeq {born} and the will carries {willed}")
    return f"the NBIRTH and the will both carry bdSeq {born}"


def _check_bdseq_increments(trace: _Trace) -> str:
    """bdSeq opens at zero and advances by one for each session."""
    session = trace.fresh()
    seen = []
    for _ in range(SEQUENCE_MODULUS + 2):
        will = session.connect()
        seen.append(next(m.value for m in will.message.payload.metrics if m.name == BDSEQ_METRIC))
    _require(seen[0] == 0, f"the first session opened bdSeq at {seen[0]}")
    for index in range(1, len(seen)):
        _require(
            seen[index] == (seen[index - 1] + 1) % SEQUENCE_MODULUS,
            f"bdSeq went {seen[index - 1]} then {seen[index]}",
        )
    return "bdSeq opens at zero, advances by one, and returns to zero after 255"


def _check_rebirth_metric_present(trace: _Trace) -> str:
    """The NBIRTH declares the rebirth command metric."""
    trace.metric(trace.nbirth, REBIRTH_METRIC)
    return f"the NBIRTH declares {REBIRTH_METRIC!r}"


def _check_rebirth_metric_datatype(trace: _Trace) -> str:
    """The rebirth command metric is a boolean."""
    metric = trace.metric(trace.nbirth, REBIRTH_METRIC)
    _require(metric.datatype is DataType.Boolean, f"its datatype is {metric.datatype!r}")
    return f"{REBIRTH_METRIC!r} carries the Boolean datatype"


def _check_rebirth_metric_value(trace: _Trace) -> str:
    """The rebirth command metric is born false."""
    metric = trace.metric(trace.nbirth, REBIRTH_METRIC)
    _require(metric.value is False, f"its birth value is {metric.value!r}")
    return f"{REBIRTH_METRIC!r} is born holding false"


def _check_rebirth_metric_unaliased(trace: _Trace) -> str:
    """The rebirth command metric is born without an alias."""
    metric = trace.metric(trace.nbirth, REBIRTH_METRIC)
    _require(
        metric.alias is None,
        f"the NBIRTH gives {REBIRTH_METRIC!r} alias {metric.alias} while the edge "
        "node uses aliases",
    )
    return f"{REBIRTH_METRIC!r} is born with no alias"


def _check_birth_metrics_named_and_aliased(trace: _Trace) -> str:
    """Birth metrics carry both a name and an alias.

    The rebirth command metric is left out of the sweep, because a separate
    assertion takes it out of the alias table for an edge node that aliases.
    """
    for message in (trace.nbirth, *trace.dbirths.values()):
        for metric in message.payload.metrics:
            if metric.name == REBIRTH_METRIC:
                continue
            _require(metric.name is not None, f"a {message.message_type} metric carries no name")
            _require(
                metric.alias is not None,
                f"{message.message_type} metric {metric.name!r} carries no alias",
            )
    return "birth metrics carry both a name and an alias"


def _check_data_metrics_aliased_only(trace: _Trace) -> str:
    """Data metrics carry the alias and leave the name out."""
    for message in (trace.ndata, trace.ddata):
        for metric in message.payload.metrics:
            _require(metric.alias is not None, f"a {message.message_type} metric carries no alias")
            _require(
                metric.name is None,
                f"a {message.message_type} metric still carries the name {metric.name!r}",
            )
    return "data metrics carry only the alias"


def _check_alias_uniqueness(trace: _Trace) -> str:
    """Aliases are unique across the whole edge node."""
    table = trace.session.alias_table()
    aliases = list(table.values())
    _require(len(set(aliases)) == len(aliases), "two metrics of this edge node share an alias")
    _require(all(alias >= 1 for alias in aliases), "an alias of zero was assigned")
    return f"{len(aliases)} metrics hold {len(set(aliases))} distinct aliases"


def _check_metric_timestamps(trace: _Trace) -> str:
    """Every metric of a birth or data message carries a timestamp."""
    for message in (trace.nbirth, *trace.dbirths.values(), trace.ndata, trace.ddata):
        for metric in message.payload.metrics:
            _require(
                metric.timestamp is not None,
                f"a {message.message_type} metric carries no timestamp",
            )
    return "every birth and data metric carries a timestamp"


def _check_datatype_enumerated(trace: _Trace) -> str:
    """Every birth datatype is one the payload definition enumerates."""
    for message in (trace.nbirth, *trace.dbirths.values()):
        for metric in message.payload.metrics:
            _require(
                isinstance(metric.datatype, DataType),
                f"a {message.message_type} metric carries datatype {metric.datatype!r}",
            )
    return "every birth datatype is an enumerated value"


def _check_quality_codes(trace: _Trace) -> str:
    """The quality property holds one of the three defined codes."""
    codes = {int(quality) for quality in Quality}
    _require(codes == {0, 192, 500}, f"the quality codes are {sorted(codes)}")
    for metric in trace.nbirth.payload.metrics:
        quality = metric.properties.get("Quality")
        if quality is not None:
            _require(int(quality) in codes, f"a metric carries quality {quality!r}")
    return "quality codes are 0, 192, and 500"


def _check_chronological(
    pick: Callable[[_Trace], Message], follow: Callable[[_Trace], Message]
) -> Check:
    """Metric timestamps within a payload do not move backwards."""

    def check(trace: _Trace) -> str:
        for message in (pick(trace), follow(trace)):
            stamps = [m.timestamp for m in message.payload.metrics if m.timestamp is not None]
            for earlier, later in zip(stamps, stamps[1:], strict=False):
                _require(
                    later >= earlier,
                    f"a {message.message_type} metric list runs {earlier} then {later}",
                )
        return "metric timestamps within a payload do not move backwards"

    return check


def _check_connect_first(trace: _Trace) -> str:
    """Nothing is published before the session is opened."""
    _require(_refuses(trace.fresh().node_birth), "an NBIRTH was published before CONNECT")
    return "publishing before CONNECT is refused"


def _check_will_returned(trace: _Trace) -> str:
    """Opening the session hands back a will to register."""
    session = trace.fresh()
    registration = session.connect()
    _require(isinstance(registration, WillRegistration), "CONNECT returned no will registration")
    return "CONNECT hands back a will registration"


def _check_birth_first(trace: _Trace) -> str:
    """A data message before the birth certificate is refused."""
    session = trace.fresh()
    session.connect()
    _require(
        _refuses(lambda: session.node_data({"sf_dropped_records": 1})),
        "NDATA was published before the NBIRTH",
    )
    return "a data message before the birth certificate is refused"


def _check_dbirth_after_nbirth(trace: _Trace) -> str:
    """A DBIRTH before its NBIRTH is refused."""
    session = trace.fresh()
    session.connect()
    _require(
        _refuses(lambda: session.device_birth(_PORTAL)), "a DBIRTH was published before the NBIRTH"
    )
    return "a DBIRTH before the NBIRTH is refused"


def _check_ddeath(trace: _Trace) -> str:
    """Losing a device produces a DDEATH addressed to it."""
    _require(
        trace.ddeath.message_type is MessageType.DDEATH,
        f"losing a device produced a {trace.ddeath.message_type}",
    )
    _require(
        trace.ddeath.topic.endswith(f"/{_CONVEYOR}"), f"the DDEATH addressed {trace.ddeath.topic!r}"
    )
    return "losing a device produces a DDEATH on the device's topic"


def _check_rebirth_stops_data(trace: _Trace) -> str:
    """A rebirth request produces no data message."""
    kinds = [message.message_type for message in trace.rebirth]
    for kind in kinds:
        _require(
            kind not in (MessageType.NDATA, MessageType.DDATA),
            f"the rebirth sequence carries a {kind}",
        )
    return f"the rebirth sequence carries only {sorted({str(k) for k in kinds})}"


def _check_rebirth_sequence(trace: _Trace) -> str:
    """A rebirth request produces the NBIRTH and every DBIRTH."""
    _require(bool(trace.rebirth), "the rebirth request produced nothing")
    _require(
        trace.rebirth[0].message_type is MessageType.NBIRTH,
        f"the rebirth opened with a {trace.rebirth[0].message_type}",
    )
    reborn = {m.topic.rsplit("/", 1)[-1] for m in trace.rebirth[1:]}
    _require(
        reborn == set(_DEVICE_METRICS),
        f"the rebirth carried DBIRTHs for {sorted(reborn)}",
    )
    return "a rebirth produces the NBIRTH and a DBIRTH for every device"


def _check_rebirth_keeps_bdseq(trace: _Trace) -> str:
    """A rebirth keeps the session's bdSeq."""
    willed = trace.metric(trace.will.message, BDSEQ_METRIC).value
    reborn = trace.metric(trace.rebirth[0], BDSEQ_METRIC).value
    _require(reborn == willed, f"the rebirth NBIRTH carries bdSeq {reborn}, the will {willed}")
    return f"the rebirth NBIRTH keeps bdSeq {reborn}"


def _check_rebirth_request_name(trace: _Trace) -> str:
    """Only the rebirth command metric triggers a rebirth."""
    session = trace.fresh_born()
    _require(
        session.handle_node_command({"Node Control/Something Else": True}) == (),
        "a command under another name triggered a rebirth",
    )
    _require(
        bool(session.handle_node_command({REBIRTH_METRIC: True})),
        f"a command named {REBIRTH_METRIC!r} triggered nothing",
    )
    return f"a rebirth is triggered by {REBIRTH_METRIC!r} alone"


def _check_rebirth_request_value(trace: _Trace) -> str:
    """Only a true value triggers a rebirth."""
    session = trace.fresh_born()
    _require(
        session.handle_node_command({REBIRTH_METRIC: False}) == (),
        "a false rebirth command triggered a rebirth",
    )
    _require(
        bool(session.handle_node_command({REBIRTH_METRIC: True})),
        "a true rebirth command triggered nothing",
    )
    return "a rebirth is triggered by a true value alone"


def _check_intentional_disconnect(trace: _Trace) -> str:
    """Closing the session produces an NDEATH to publish."""
    session = trace.fresh_born()
    close = getattr(session, "disconnect", None)
    _require(
        callable(close),
        "the session offers no close that publishes an NDEATH, so an edge node shutting down "
        "on purpose leaves its death to the broker's will delivery",
    )
    assert close is not None
    message = close()
    _require(
        isinstance(message, Message) and message.message_type is MessageType.NDEATH,
        "closing the session produced no NDEATH",
    )
    return "closing the session produces an NDEATH"


def _check_case_distinct_ids(_trace: _Trace) -> str:
    """An identifier that differs from another only by case cannot exist."""
    _require(
        _refuses(
            lambda: SparkplugIds(
                group_id="Twinflow:dc-01:receiving", edge_node_id="a", device_id=""
            )
        ),
        "an identifier carrying an uppercase letter reached a topic",
    )
    _require(
        _refuses(lambda: SparkplugIds(group_id=_GROUP_ID, edge_node_id="Line-01", device_id="")),
        "an edge node id carrying an uppercase letter reached a topic",
    )
    return "identifiers are lowercase, so two cannot differ only by case"


def _check_case_distinct_metric_names(trace: _Trace) -> str:
    """Two metric names differing only by case cannot both be published."""
    colliding = (
        MetricSpec(name="Read_Rate", datatype=DataType.Float, unit="1"),
        MetricSpec(name="read_rate", datatype=DataType.Float, unit="1"),
    )
    try:
        built = EdgeNodeSession(
            group_id=_GROUP_ID,
            edge_node_id=_EDGE_NODE_ID,
            clock=trace.clock,
            node_metrics=(),
            devices={_PORTAL: colliding},
        )
    except (ValueError, RuntimeError):
        return "metric names that differ only by case are refused"
    names = {name for _device, name in built.alias_table()}
    _require(
        len({name.lower() for name in names}) == len(names),
        "the session accepted two metric names that differ only by case",
    )
    return "metric names that differ only by case are refused"


#: One executable check per in-scope assertion. An assertion with no check
#: cannot be reported as passing, which `tests/test_conformance.py` enforces.
_CHECKS: Mapping[str, Check] = {
    # -------------------------------------------------------- identifiers
    "tck-id-intro-group-id-string": _identifier_reaches_topic(_nbirth, 1, _GROUP_ID),
    "tck-id-intro-edge-node-id-string": _identifier_reaches_topic(_nbirth, 3, _EDGE_NODE_ID),
    "tck-id-intro-device-id-string": _identifier_reaches_topic(_dbirth, 4, _PORTAL),
    "tck-id-intro-group-id-chars": _refuses_reserved(
        lambda value: SparkplugIds(
            group_id=f"{value}:dc-01:receiving", edge_node_id="a", device_id=""
        )
    ),
    "tck-id-intro-edge-node-id-chars": _refuses_reserved(
        lambda value: SparkplugIds(group_id=_GROUP_ID, edge_node_id=value, device_id="")
    ),
    "tck-id-intro-device-id-chars": _refuses_reserved(
        lambda value: SparkplugIds(group_id=_GROUP_ID, edge_node_id=_EDGE_NODE_ID, device_id=value)
    ),
    "tck-id-topic-structure-namespace-valid-group-id": _refuses_reserved(
        lambda value: SparkplugIds(
            group_id=f"{value}:dc-01:receiving", edge_node_id="a", device_id=""
        )
    ),
    "tck-id-topic-structure-namespace-valid-edge-node-id": _refuses_reserved(
        lambda value: SparkplugIds(group_id=_GROUP_ID, edge_node_id=value, device_id="")
    ),
    "tck-id-topic-structure-namespace-valid-device-id": _refuses_reserved(
        lambda value: SparkplugIds(group_id=_GROUP_ID, edge_node_id=_EDGE_NODE_ID, device_id=value)
    ),
    "tck-id-topic-structure-namespace-unique-device-id": _check_unique_device_id,
    "tck-id-case-sensitivity-sparkplug-ids": _check_case_distinct_ids,
    "tck-id-case-sensitivity-metric-names": _check_case_distinct_metric_names,
    # ------------------------------------------------------------- topics
    "tck-id-topic-structure": _check_topic_structure,
    "tck-id-topic-structure-namespace-a": _check_namespace,
    "tck-id-topic-structure-namespace-device-id-associated-message-types": (
        _check_device_id_required
    ),
    "tck-id-topic-structure-namespace-device-id-non-associated-message-types": (
        _check_device_id_refused
    ),
    "tck-id-topics-nbirth-topic": _topic_is(_nbirth, f"{_NODE_TOPIC}/NBIRTH/{_EDGE_NODE_ID}"),
    "tck-id-topics-ndata-topic": _topic_is(_ndata, f"{_NODE_TOPIC}/NDATA/{_EDGE_NODE_ID}"),
    "tck-id-topics-ndeath-topic": _topic_is(_will, f"{_NODE_TOPIC}/NDEATH/{_EDGE_NODE_ID}"),
    "tck-id-topics-ncmd-topic": _check_ncmd_topic,
    "tck-id-topics-dbirth-topic": _topic_is(
        _dbirth, f"{_NODE_TOPIC}/DBIRTH/{_EDGE_NODE_ID}/{_PORTAL}"
    ),
    "tck-id-topics-ddata-topic": _topic_is(
        _ddata, f"{_NODE_TOPIC}/DDATA/{_EDGE_NODE_ID}/{_PORTAL}"
    ),
    "tck-id-topics-ddeath-topic": _topic_is(
        _ddeath, f"{_NODE_TOPIC}/DDEATH/{_EDGE_NODE_ID}/{_CONVEYOR}"
    ),
    "tck-id-topics-dcmd-topic": _check_dcmd_topic,
    "tck-id-message-flow-edge-node-birth-publish-nbirth-topic": _topic_is(
        _nbirth, f"{_NODE_TOPIC}/NBIRTH/{_EDGE_NODE_ID}"
    ),
    "tck-id-message-flow-edge-node-birth-publish-will-message-topic": _topic_is(
        _will, f"{_NODE_TOPIC}/NDEATH/{_EDGE_NODE_ID}"
    ),
    "tck-id-message-flow-device-birth-publish-dbirth-topic": _topic_is(
        _dbirth, f"{_NODE_TOPIC}/DBIRTH/{_EDGE_NODE_ID}/{_PORTAL}"
    ),
    "tck-id-message-flow-device-birth-publish-dbirth-match-edge-node-topic": (
        _check_dbirth_matches_node
    ),
    # ------------------------------------------------------ delivery flags
    "tck-id-topics-nbirth-mqtt": _published_delivery(_nbirth, 0, False),
    "tck-id-topics-ndata-mqtt": _published_delivery(_ndata, 0, False),
    "tck-id-topics-dbirth-mqtt": _published_delivery(_dbirth, 0, False),
    "tck-id-topics-ddata-mqtt": _published_delivery(_ddata, 0, False),
    "tck-id-topics-ddeath-mqtt": _published_delivery(_ddeath, 0, False),
    "tck-id-topics-ncmd-mqtt": _declared_delivery(MessageType.NCMD, 0, False),
    "tck-id-topics-dcmd-mqtt": _declared_delivery(MessageType.DCMD, 0, False),
    "tck-id-payloads-nbirth-qos": _published_delivery(_nbirth, 0, None),
    "tck-id-payloads-nbirth-retain": _published_delivery(_nbirth, None, False),
    "tck-id-payloads-dbirth-qos": _published_delivery(_dbirth, 0, None),
    "tck-id-payloads-dbirth-retain": _published_delivery(_dbirth, None, False),
    "tck-id-payloads-ndata-qos": _published_delivery(_ndata, 0, None),
    "tck-id-payloads-ndata-retain": _published_delivery(_ndata, None, False),
    "tck-id-payloads-ddata-qos": _published_delivery(_ddata, 0, None),
    "tck-id-payloads-ddata-retain": _published_delivery(_ddata, None, False),
    "tck-id-payloads-ncmd-qos": _declared_delivery(MessageType.NCMD, 0, False),
    "tck-id-payloads-ncmd-retain": _declared_delivery(MessageType.NCMD, 0, False),
    "tck-id-payloads-dcmd-qos": _declared_delivery(MessageType.DCMD, 0, False),
    "tck-id-payloads-dcmd-retain": _declared_delivery(MessageType.DCMD, 0, False),
    "tck-id-message-flow-edge-node-birth-publish-nbirth-qos": _published_delivery(_nbirth, 0, None),
    "tck-id-message-flow-edge-node-birth-publish-nbirth-retained": _published_delivery(
        _nbirth, None, False
    ),
    "tck-id-message-flow-device-birth-publish-dbirth-qos": _published_delivery(_dbirth, 0, None),
    "tck-id-message-flow-device-birth-publish-dbirth-retained": _published_delivery(
        _dbirth, None, False
    ),
    "tck-id-payloads-ndeath-will-message-qos": _check_will_qos,
    "tck-id-payloads-ndeath-will-message-retain": _check_will_retain,
    "tck-id-message-flow-edge-node-birth-publish-will-message-qos": _check_will_qos,
    "tck-id-message-flow-edge-node-birth-publish-will-message-will-retained": _check_will_retain,
    "tck-id-host-topic-phid-birth-qos": _declared_delivery(MessageType.STATE, 1, True),
    "tck-id-host-topic-phid-birth-retain": _declared_delivery(MessageType.STATE, 1, True),
    # --------------------------------------------------------- the sequence
    "tck-id-topics-nbirth-seq-num": _check_nbirth_seq_zero,
    "tck-id-payloads-sequence-num-always-included": _check_seq_always_present,
    "tck-id-payloads-sequence-num-req-nbirth": _seq_present(_nbirth),
    "tck-id-payloads-sequence-num-incrementing": _check_seq_wraps,
    "tck-id-payloads-nbirth-seq": _seq_present(_nbirth),
    "tck-id-message-flow-edge-node-birth-publish-nbirth-payload-seq": _seq_present(_nbirth),
    "tck-id-topics-dbirth-seq": _seq_follows(_dbirth_first, _nbirth),
    "tck-id-payloads-dbirth-seq": _seq_present(_dbirth),
    "tck-id-payloads-dbirth-seq-inc": _seq_follows(_dbirth_first, _nbirth),
    "tck-id-message-flow-device-birth-publish-dbirth-payload-seq": _seq_follows(
        _dbirth_first, _nbirth
    ),
    "tck-id-topics-ndata-seq-num": _seq_follows(_ndata, _dbirth),
    "tck-id-payloads-ndata-seq": _seq_present(_ndata),
    "tck-id-payloads-ndata-seq-inc": _seq_follows(_ndata, _dbirth),
    "tck-id-topics-ddata-seq-num": _seq_follows(_ddata, _ndata),
    "tck-id-payloads-ddata-seq": _seq_present(_ddata),
    "tck-id-payloads-ddata-seq-inc": _seq_follows(_ddata, _ndata),
    "tck-id-topics-ddeath-seq-num": _seq_follows(_ddeath, _ddata),
    "tck-id-payloads-ddeath-seq": _seq_present(_ddeath),
    "tck-id-payloads-ddeath-seq-inc": _seq_follows(_ddeath, _ddata),
    "tck-id-payloads-ddeath-seq-number": _seq_present(_ddeath),
    "tck-id-topics-ndeath-seq": _check_ndeath_seq_absent,
    "tck-id-payloads-ndeath-seq": _check_ndeath_seq_absent,
    # ------------------------------------------------------------- the will
    "tck-id-message-flow-edge-node-birth-publish-connect": _check_connect_first,
    "tck-id-message-flow-edge-node-birth-publish-will-message": _check_will_returned,
    "tck-id-payloads-ndeath-will-message": _check_will_is_ndeath,
    "tck-id-topics-ndeath-payload": _check_ndeath_payload,
    "tck-id-payloads-ndeath-bdseq": _check_bdseq_matches_will,
    "tck-id-payloads-ndeath-will-message-publisher": _check_intentional_disconnect,
    "tck-id-operational-behavior-edge-node-intentional-disconnect-ndeath": (
        _check_intentional_disconnect
    ),
    # ------------------------------------------------------------- the bdSeq
    "tck-id-topics-nbirth-bdseq-included": _check_bdseq_present,
    "tck-id-payloads-nbirth-bdseq": _check_bdseq_present,
    "tck-id-topics-nbirth-bdseq-matching": _check_bdseq_matches_will,
    "tck-id-payloads-nbirth-bdseq-repeat": _check_bdseq_matches_will,
    "tck-id-topics-nbirth-bdseq-increment": _check_bdseq_increments,
    "tck-id-message-flow-edge-node-birth-publish-will-message-payload-bdSeq": _bdseq_datatype(
        _will
    ),
    "tck-id-message-flow-edge-node-birth-publish-nbirth-payload-bdSeq": _bdseq_datatype(_nbirth),
    # ----------------------------------------------------------- the metrics
    "tck-id-topics-nbirth-metrics": _every_metric(
        _nbirth,
        lambda m: m.name is not None and m.datatype is not None,
        "a metric carries a name and a datatype",
    ),
    "tck-id-topics-dbirth-metrics": _every_metric(
        _dbirth,
        lambda m: m.name is not None and m.datatype is not None,
        "a metric carries a name and a datatype",
    ),
    "tck-id-payloads-name-requirement": _every_metric(
        _nbirth, lambda m: m.name is not None, "a metric carries its name"
    ),
    "tck-id-payloads-alias-birth-requirement": _check_birth_metrics_named_and_aliased,
    "tck-id-payloads-alias-data-cmd-requirement": _check_data_metrics_aliased_only,
    "tck-id-payloads-alias-uniqueness": _check_alias_uniqueness,
    "tck-id-payloads-name-birth-data-requirement": _check_metric_timestamps,
    "tck-id-payloads-metric-datatype-req": _every_metric(
        _dbirth, lambda m: m.datatype is not None, "a metric carries its datatype"
    ),
    "tck-id-payloads-metric-datatype-not-req": _every_metric(
        _ddata, lambda m: m.datatype is None, "a metric leaves the datatype out"
    ),
    "tck-id-payloads-metric-datatype-value": _check_datatype_enumerated,
    "tck-id-payloads-propertyset-quality-value-value": _check_quality_codes,
    "tck-id-topics-nbirth-metric-reqs": _undeclared_refused(
        lambda s: s.node_data({"never_declared": 1})
    ),
    "tck-id-topics-dbirth-metric-reqs": _undeclared_refused(
        lambda s: s.device_data(_PORTAL, {"never_declared": 1})
    ),
    "tck-id-operational-behavior-data-publish-nbirth": _undeclared_refused(
        lambda s: s.node_data({"never_declared": 1})
    ),
    "tck-id-operational-behavior-data-publish-dbirth": _undeclared_refused(
        lambda s: s.device_data(_PORTAL, {"never_declared": 1})
    ),
    "tck-id-topics-nbirth-rebirth-metric": _check_rebirth_metric_present,
    "tck-id-payloads-nbirth-rebirth-req": _check_rebirth_metric_value,
    "tck-id-operational-behavior-data-commands-rebirth-name": _check_rebirth_metric_present,
    "tck-id-operational-behavior-data-commands-rebirth-datatype": _check_rebirth_metric_datatype,
    "tck-id-operational-behavior-data-commands-rebirth-value": _check_rebirth_metric_value,
    "tck-id-operational-behavior-data-commands-rebirth-name-aliases": (
        _check_rebirth_metric_unaliased
    ),
    # ------------------------------------------------------------ timestamps
    "tck-id-topics-nbirth-timestamp": _payload_timestamp(_nbirth),
    "tck-id-topics-dbirth-timestamp": _payload_timestamp(_dbirth),
    "tck-id-topics-ndata-timestamp": _payload_timestamp(_ndata),
    "tck-id-topics-ddata-timestamp": _payload_timestamp(_ddata),
    "tck-id-payloads-nbirth-timestamp": _payload_timestamp(_nbirth),
    "tck-id-payloads-dbirth-timestamp": _payload_timestamp(_dbirth),
    "tck-id-payloads-ndata-timestamp": _payload_timestamp(_ndata),
    "tck-id-payloads-ddata-timestamp": _payload_timestamp(_ddata),
    "tck-id-payloads-ddeath-timestamp": _payload_timestamp(_ddeath),
    "tck-id-payloads-timestamp-in-UTC": _utc_timestamp(lambda t: t.nbirth.payload.timestamp),
    "tck-id-payloads-metric-timestamp-in-UTC": _utc_timestamp(
        lambda t: t.metric(t.nbirth, BDSEQ_METRIC).timestamp or 0
    ),
    # -------------------------------------------------------------- ordering
    "tck-id-principles-birth-certificates-order": _check_birth_first,
    "tck-id-message-flow-device-birth-publish-nbirth-wait": _check_dbirth_after_nbirth,
    "tck-id-payloads-dbirth-order": _data_before_all_births(
        lambda s: s.device_data(_PORTAL, {"read_rate": 0.5})
    ),
    "tck-id-payloads-ndata-order": _data_before_all_births(
        lambda s: s.node_data({"sf_dropped_records": 1})
    ),
    "tck-id-payloads-ddata-order": _data_before_all_births(
        lambda s: s.device_data(_PORTAL, {"read_rate": 0.5})
    ),
    "tck-id-operational-behavior-data-publish-nbirth-order": _check_chronological(_nbirth, _ndata),
    "tck-id-operational-behavior-data-publish-dbirth-order": _check_chronological(_dbirth, _ddata),
    # --------------------------------------------------- report by exception
    "tck-id-principles-rbe-recommended": _only_changed(
        lambda s: s.device_data(_PORTAL, {"read_rate": 0.5}), 1
    ),
    "tck-id-topics-ndata-payload": _only_changed(
        lambda s: s.node_data({"sf_dropped_records": 1}), 1
    ),
    "tck-id-topics-ddata-payload": _only_changed(
        lambda s: s.device_data(_PORTAL, {"read_rate": 0.5}), 1
    ),
    "tck-id-operational-behavior-data-publish-nbirth-change": _only_changed(
        lambda s: s.node_data({"sf_dropped_records": 1}), 1
    ),
    "tck-id-operational-behavior-data-publish-dbirth-change": _only_changed(
        lambda s: s.device_data(_PORTAL, {"read_rate": 0.5}), 1
    ),
    # -------------------------------------------------------------- lifecycle
    "tck-id-operational-behavior-device-ddeath": _check_ddeath,
    "tck-id-operational-behavior-data-commands-rebirth-action-1": _check_rebirth_stops_data,
    "tck-id-operational-behavior-data-commands-rebirth-action-2": _check_rebirth_sequence,
    "tck-id-operational-behavior-data-commands-rebirth-action-3": _check_rebirth_keeps_bdseq,
    "tck-id-operational-behavior-data-commands-ncmd-rebirth-name": _check_rebirth_request_name,
    "tck-id-operational-behavior-data-commands-ncmd-rebirth-value": _check_rebirth_request_value,
}


# ------------------------------------------------------------------ the report


@dataclass(frozen=True, slots=True)
class AssertionResult:
    """What the runner observed for one assertion."""

    assertion_id: str
    passed: bool
    observation: str


@dataclass(frozen=True, slots=True)
class Coverage:
    """The honest denominator, and what sits under it.

    `edge_node_total` is every assertion of the edge-node profile, whether or
    not this repository can answer it. `passed` is never reported without it.
    """

    spec_version: str
    spec_total: int
    edge_node_total: int
    edge_node_in_scope: int
    in_scope_total: int
    passed: int
    failed: int
    out_of_scope: Mapping[Exclusion, int]

    @property
    def edge_node_out_of_scope(self) -> int:
        """Edge-node assertions this repository cannot answer."""
        return self.edge_node_total - self.edge_node_in_scope


@dataclass(frozen=True, slots=True)
class ConformanceReport:
    """Every in-scope assertion's result, and the coverage around them."""

    results: tuple[AssertionResult, ...]
    coverage: Coverage

    @property
    def failures(self) -> tuple[AssertionResult, ...]:
        """The assertions the edge node did not satisfy."""
        return tuple(result for result in self.results if not result.passed)

    @property
    def conformant(self) -> bool:
        """Whether every in-scope assertion held.

        True here is not a conformance claim. It says the in-scope subset held,
        and the subset is smaller than the edge-node profile by exactly
        `coverage.edge_node_out_of_scope` assertions.
        """
        return not self.failures


def run_edge_node_conformance(clock: Clock | None = None) -> ConformanceReport:
    """Play one edge-node session and rule on every in-scope assertion.

    The clock is injected so a caller can decide what the payload timestamps
    are read from. The default is the simulation clock this package's devices
    run on, which is what makes the two UTC assertions come out the way they
    do rather than being excluded quietly.
    """
    trace = _play(clock if clock is not None else SimClock())
    results = []
    for assertion_id in sorted(_CHECKS):
        try:
            observation = _CHECKS[assertion_id](trace)
        except _CheckFailed as failure:
            results.append(AssertionResult(assertion_id, False, str(failure)))
        except Exception as error:  # noqa: BLE001
            # An edge node that raises where the assertion expects a message
            # has not satisfied the assertion, so the error is the observation
            # rather than a crash that hides the other 142 results.
            results.append(AssertionResult(assertion_id, False, f"{type(error).__name__}: {error}"))
        else:
            results.append(AssertionResult(assertion_id, True, observation))
    return ConformanceReport(results=tuple(results), coverage=edge_node_coverage(tuple(results)))


def edge_node_coverage(results: tuple[AssertionResult, ...] = ()) -> Coverage:
    """The coverage statement, with or without a run behind it."""
    edge = assertions_for(Profile.EDGE_NODE)
    by_reason: dict[Exclusion, int] = {}
    for assertion in ASSERTIONS.values():
        if assertion.exclusion is not None:
            by_reason[assertion.exclusion] = by_reason.get(assertion.exclusion, 0) + 1
    return Coverage(
        spec_version=SPEC_VERSION,
        spec_total=SPEC_ASSERTION_COUNT,
        edge_node_total=len(edge),
        edge_node_in_scope=sum(1 for a in edge if a.in_scope),
        in_scope_total=len(in_scope_assertions()),
        passed=sum(1 for r in results if r.passed),
        failed=sum(1 for r in results if not r.passed),
        out_of_scope=by_reason,
    )


def format_report(report: ConformanceReport) -> str:
    """The report as lines, failures first, with the coverage beneath them."""
    cover = report.coverage
    lines = [
        f"Sparkplug B v{cover.spec_version} edge-node conformance",
        f"  specification assertions        {cover.spec_total}",
        f"  edge-node profile               {cover.edge_node_total}",
        f"  edge-node in scope here         {cover.edge_node_in_scope}",
        f"  edge-node out of scope here     {cover.edge_node_out_of_scope}",
        f"  checks run (all profiles)       {cover.in_scope_total}",
        f"  passed                          {cover.passed}",
        f"  failed                          {cover.failed}",
        "",
    ]
    for result in report.failures:
        lines.append(f"FAIL {result.assertion_id}")
        lines.append(f"     {result.observation}")
    lines.append("")
    lines.append("out of scope, by reason:")
    for reason, count in sorted(cover.out_of_scope.items(), key=lambda item: -item[1]):
        lines.append(f"  {count:3d}  {reason.value}")
    return "\n".join(lines)


def _main() -> int:
    """Print the report and exit non-zero when an in-scope assertion fails.

    The entry point a gate command calls, so the wiring is one line and the
    exit code is the gate's verdict rather than something a reader of the
    output has to decide.
    """
    report = run_edge_node_conformance()
    print(format_report(report))
    return 0 if report.conformant else 1


if __name__ == "__main__":
    raise SystemExit(_main())
