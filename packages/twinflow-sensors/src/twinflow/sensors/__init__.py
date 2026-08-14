"""Simulated field devices and the payloads they publish onto the UNS.

WP-P1-02 opens one RFID portal and one temperature sensor, and WP-P1-03 gives
them Sparkplug B payloads with metric aliasing under gate VAL-GATE-SPARK-001.
The sensor catalog grows by adding entries rather than by adding modules, so
this surface stays small as the device count rises.

Three modules, split by what each one is responsible for being right about.
`sparkplug` owns the session, the alias table, the sequence, and the Sparkplug
addressing of an ISA-95 point. `portal` and `temperature` own the two P1
devices. Nothing here imports a domain sibling: twinflow.sensors sits in the
domain layer and the layered contract forbids the edge, so the devices publish
value objects and something above wires them to a transport.

The six-level addressing itself is not here. `UnsPath` and its grammar live in
twinflow.config, which owns the facility model that ARCHITECTURE.md section 5
makes the namespace a projection of. This package builds topics with it and
never restates it, so the publish side and the historian cannot drift.
"""

from __future__ import annotations

from twinflow.sensors.conformance import (
    ASSERTIONS,
    SPEC_ASSERTION_COUNT,
    SPEC_VERSION,
    Assertion,
    AssertionResult,
    ConformanceReport,
    Coverage,
    Exclusion,
    Level,
    Profile,
    assertions_for,
    edge_node_coverage,
    exclusions_by_reason,
    format_report,
    in_scope_assertions,
    run_edge_node_conformance,
)
from twinflow.sensors.portal import (
    EPC,
    EPC_LENGTH,
    TYPICAL_RSSI_BAND_DBM,
    EpcPrefixFilter,
    InventoryAccumulator,
    PortalFault,
    PortalReader,
    PortalTelemetry,
    ReadAggregate,
    ReaderConfig,
    TagRead,
    beta_scaled,
    diagnose_portal,
)
from twinflow.sensors.sparkplug import (
    BDSEQ_METRIC,
    GROUP_DELIMITER,
    MIRROR_QOS,
    MIRROR_RETAIN,
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
    MirrorRecord,
    Payload,
    QosRow,
    Quality,
    SparkplugIds,
    WillRegistration,
    mirror_topic_for,
    qos_and_retain_for,
    state_topic_for,
    topic_for,
)
from twinflow.sensors.temperature import (
    ABSOLUTE_ZERO_C,
    DERIVED_PARAMETER,
    RAW_PARAMETER,
    PlausibilityBand,
    PlausibilityViolation,
    TemperatureReading,
    TemperatureSensor,
    TemperatureSensorConfig,
)

#: Read by tool.hatch.version, so this is the only place the version is written.
__version__ = "0.1.0"

__all__ = [
    "ABSOLUTE_ZERO_C",
    "ASSERTIONS",
    "Assertion",
    "AssertionResult",
    "BDSEQ_METRIC",
    "ConformanceReport",
    "Coverage",
    "DERIVED_PARAMETER",
    "DataType",
    "EPC",
    "EPC_LENGTH",
    "EdgeNodeSession",
    "EpcPrefixFilter",
    "Exclusion",
    "GROUP_DELIMITER",
    "InventoryAccumulator",
    "Level",
    "MIRROR_QOS",
    "MIRROR_RETAIN",
    "Message",
    "MessageType",
    "Metric",
    "MetricSpec",
    "MirrorRecord",
    "NAMESPACE",
    "Payload",
    "PlausibilityBand",
    "PlausibilityViolation",
    "PortalFault",
    "PortalReader",
    "PortalTelemetry",
    "Profile",
    "QOS_BY_TOPIC_CLASS",
    "QosRow",
    "Quality",
    "RAW_PARAMETER",
    "REBIRTH_METRIC",
    "ReadAggregate",
    "ReaderConfig",
    "SEQUENCE_MODULUS",
    "SPEC_ASSERTION_COUNT",
    "SPEC_VERSION",
    "SparkplugIds",
    "TYPICAL_RSSI_BAND_DBM",
    "TagRead",
    "TemperatureReading",
    "TemperatureSensor",
    "TemperatureSensorConfig",
    "WillRegistration",
    "__version__",
    "assertions_for",
    "beta_scaled",
    "diagnose_portal",
    "edge_node_coverage",
    "exclusions_by_reason",
    "format_report",
    "in_scope_assertions",
    "mirror_topic_for",
    "qos_and_retain_for",
    "run_edge_node_conformance",
    "state_topic_for",
    "topic_for",
]
