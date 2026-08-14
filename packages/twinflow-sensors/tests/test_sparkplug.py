"""Sparkplug B session rules, each one stated as an observation that fails it.

Gate VAL-GATE-SPARK-001 owns the external half of this claim and the Eclipse
Technology Compatibility Kit is its arbiter. What runs here is the half this
repository can falsify in a Python unit tier: the normative statements
ARCHITECTURE.md section 5.1 and docs/design/iot-fleet.md 5.4 restate from the
v3.0.0 specification. No test here compares the encoder against the encoder,
because doctrine D-11 rule 1 says this repository is never a reference for
itself.
"""

from __future__ import annotations

import pytest

from twinflow.config import UnsPath
from twinflow.kernel import SimClock, SimInstant
from twinflow.sensors import (
    NAMESPACE,
    QOS_BY_TOPIC_CLASS,
    REBIRTH_METRIC,
    DataType,
    EdgeNodeSession,
    MessageType,
    MetricSpec,
    Quality,
    SparkplugIds,
    qos_and_retain_for,
    state_topic_for,
    topic_for,
)

PORTAL_PATH = UnsPath.parse("twinflow/dc-01/receiving/inbound-line-01/portal-03/read_rate")
CONVEYOR_PATH = UnsPath.parse("twinflow/dc-01/receiving/inbound-line-01/conveyor-02/motor_temp_c")
IDS = SparkplugIds.for_path(PORTAL_PATH)

PORTAL_METRICS = (
    MetricSpec(name="read_rate", datatype=DataType.Float, unit="1", eng_low=0.0, eng_high=1.0),
    MetricSpec(name="unique_epcs", datatype=DataType.UInt32, unit="1"),
    MetricSpec(name="ant_vswr", datatype=DataType.Float, unit="1", eng_low=1.0, eng_high=10.0),
)

CONVEYOR_METRICS = (
    MetricSpec(name="motor_temp_c", datatype=DataType.Float, unit="Cel"),
    MetricSpec(name="motor_temp_ewma_c", datatype=DataType.Float, unit="Cel"),
)

NODE_METRICS = (MetricSpec(name="sf_dropped_records", datatype=DataType.UInt64, unit="1"),)


def make_session(clock: SimClock | None = None) -> EdgeNodeSession:
    return EdgeNodeSession(
        group_id=IDS.group_id,
        edge_node_id=IDS.edge_node_id,
        clock=clock or SimClock(tick_hz=1_000),
        node_metrics=NODE_METRICS,
        devices={"portal-03": PORTAL_METRICS, "conveyor-02": CONVEYOR_METRICS},
    )


# --------------------------------------------------------------------- topics


def test_the_namespace_element_is_the_constant_the_specification_fixes():
    assert NAMESPACE == "spBv1.0"


def test_node_topics_carry_four_elements_and_device_topics_five():
    assert (
        topic_for(IDS, MessageType.NBIRTH)
        == "spBv1.0/twinflow:dc-01:receiving/NBIRTH/inbound-line-01"
    )
    assert (
        topic_for(IDS, MessageType.DBIRTH, device_id="portal-03")
        == "spBv1.0/twinflow:dc-01:receiving/DBIRTH/inbound-line-01/portal-03"
    )


@pytest.mark.parametrize(
    "message_type", [MessageType.NBIRTH, MessageType.NDATA, MessageType.NDEATH]
)
def test_a_node_message_refuses_a_device_id(message_type):
    with pytest.raises(ValueError, match="device"):
        topic_for(IDS, message_type, device_id="portal-03")


@pytest.mark.parametrize(
    "message_type", [MessageType.DBIRTH, MessageType.DDATA, MessageType.DDEATH]
)
def test_a_device_message_requires_a_device_id(message_type):
    with pytest.raises(ValueError, match="device"):
        topic_for(IDS, message_type)


def test_the_host_state_topic_has_its_own_shape():
    assert state_topic_for("twinflow-primary") == "spBv1.0/STATE/twinflow-primary"


# ----------------------------------------------------------------- birth rules


def test_nbirth_carries_seq_zero_every_node_metric_and_the_session_bdseq():
    session = make_session()
    session.connect()
    nbirth = session.node_birth()

    assert nbirth.message_type is MessageType.NBIRTH
    assert nbirth.payload.seq == 0
    names = [metric.name for metric in nbirth.payload.metrics]
    assert "sf_dropped_records" in names
    assert "bdSeq" in names
    assert "Node Control/Rebirth" in names
    assert all(metric.alias is not None for metric in nbirth.payload.metrics)
    assert all(metric.datatype is not None for metric in nbirth.payload.metrics)


def test_dbirth_carries_every_metric_with_name_datatype_and_an_integer_alias():
    session = make_session()
    session.connect()
    session.node_birth()
    dbirth = session.device_birth("portal-03")

    assert dbirth.message_type is MessageType.DBIRTH
    assert [metric.name for metric in dbirth.payload.metrics] == [
        "ant_vswr",
        "read_rate",
        "unique_epcs",
    ]
    for metric in dbirth.payload.metrics:
        assert isinstance(metric.alias, int)
        assert metric.datatype is not None
        assert metric.properties["Quality"] == Quality.GOOD


def test_alias_zero_is_never_assigned():
    session = make_session()
    session.connect()
    aliases = session.alias_table()
    assert 0 not in aliases.values()
    assert min(aliases.values()) == 1


def test_an_alias_is_unique_across_the_whole_edge_node_not_only_one_device():
    session = make_session()
    session.connect()
    aliases = session.alias_table()
    assert len(set(aliases.values())) == len(aliases)
    portal = {alias for key, alias in aliases.items() if key[0] == "portal-03"}
    conveyor = {alias for key, alias in aliases.items() if key[0] == "conveyor-02"}
    assert portal.isdisjoint(conveyor)


def test_the_alias_table_is_assigned_from_a_byte_wise_sort_not_from_hash_order():
    """D-03: a set walked in hash order gives a second process a different table."""
    first = make_session()
    first.connect()
    second = EdgeNodeSession(
        group_id=IDS.group_id,
        edge_node_id=IDS.edge_node_id,
        clock=SimClock(tick_hz=1_000),
        node_metrics=NODE_METRICS,
        # The same metrics, declared in the opposite order.
        devices={"conveyor-02": CONVEYOR_METRICS[::-1], "portal-03": PORTAL_METRICS[::-1]},
    )
    second.connect()
    assert first.alias_table() == second.alias_table()


# ------------------------------------------------------------------ data rules


def test_ddata_references_by_alias_and_excludes_the_metric_name():
    session = make_session()
    session.connect()
    session.node_birth()
    session.device_birth("portal-03")
    ddata = session.device_data("portal-03", {"read_rate": 0.987})

    assert ddata.message_type is MessageType.DDATA
    assert len(ddata.payload.metrics) == 1
    metric = ddata.payload.metrics[0]
    assert metric.name is None
    assert metric.alias == session.alias_table()[("portal-03", "read_rate")]
    assert metric.value == pytest.approx(0.987)


def test_ddata_reports_by_exception_and_carries_only_the_metrics_handed_to_it():
    session = make_session()
    session.connect()
    session.node_birth()
    session.device_birth("portal-03")
    ddata = session.device_data("portal-03", {"unique_epcs": 41})
    assert [metric.alias for metric in ddata.payload.metrics] == [
        session.alias_table()[("portal-03", "unique_epcs")]
    ]


def test_ndata_carries_node_metrics_by_alias_with_the_name_excluded():
    session = make_session()
    session.connect()
    session.node_birth()
    ndata = session.node_data({"sf_dropped_records": 7})
    assert ndata.message_type is MessageType.NDATA
    assert ndata.payload.metrics[0].name is None
    assert ndata.payload.metrics[0].alias == session.alias_table()[(None, "sf_dropped_records")]


def test_a_metric_absent_from_dbirth_may_never_appear_in_ddata():
    session = make_session()
    session.connect()
    session.node_birth()
    session.device_birth("portal-03")
    with pytest.raises(KeyError, match="never appear"):
        session.device_data("portal-03", {"invented_metric": 1.0})


def test_a_device_that_has_not_birthed_cannot_publish_data():
    session = make_session()
    session.connect()
    session.node_birth()
    with pytest.raises(RuntimeError, match="DBIRTH"):
        session.device_data("portal-03", {"read_rate": 0.9})


# ------------------------------------------------------------------- sequence


def test_seq_increments_by_one_across_births_and_data():
    session = make_session()
    session.connect()
    observed = [session.node_birth().payload.seq]
    observed.append(session.device_birth("portal-03").payload.seq)
    observed.append(session.device_birth("conveyor-02").payload.seq)
    observed.append(session.device_data("portal-03", {"read_rate": 0.9}).payload.seq)
    assert observed == [0, 1, 2, 3]


def test_seq_wraps_back_to_zero_after_255():
    session = make_session()
    session.connect()
    session.node_birth()
    session.device_birth("portal-03")
    seen = [session.device_data("portal-03", {"read_rate": 0.9}).payload.seq for _ in range(300)]
    # The session had already spent seq 0 and seq 1 on the two births.
    assert seen[:3] == [2, 3, 4]
    assert seen[253] == 255
    assert seen[254] == 0
    assert max(seen) == 255
    assert min(seen) == 0


def test_ndeath_carries_no_sequence_number():
    """The will is composed at CONNECT, before the session has spent a seq."""
    session = make_session()
    will = session.connect()
    assert will.message.payload.seq is None


# --------------------------------------------------------------------- bdSeq


def test_ndeath_is_registered_as_the_will_at_connect_time_before_nbirth():
    session = make_session()
    will = session.connect()
    assert will.message.message_type is MessageType.NDEATH
    assert will.qos == 1
    assert will.retain is False
    assert session.node_birth_count == 0


def test_the_will_bdseq_matches_the_nbirth_bdseq_of_the_same_session():
    session = make_session()
    will = session.connect()
    nbirth = session.node_birth()
    will_bdseq = next(m.value for m in will.message.payload.metrics if m.name == "bdSeq")
    birth_bdseq = next(m.value for m in nbirth.payload.metrics if m.name == "bdSeq")
    assert will_bdseq == birth_bdseq


def test_bdseq_increments_per_session_and_wraps_after_255():
    session = make_session()
    seen = []
    for _ in range(258):
        will = session.connect()
        seen.append(next(m.value for m in will.message.payload.metrics if m.name == "bdSeq"))
    assert seen[:3] == [0, 1, 2]
    assert seen[255] == 255
    assert seen[256] == 0


def test_publishing_before_connect_is_refused():
    session = make_session()
    with pytest.raises(RuntimeError, match="connect"):
        session.node_birth()


# --------------------------------------------------------------------- rebirth


def test_a_rebirth_resets_seq_to_zero_and_republishes_the_node_and_every_device():
    session = make_session()
    session.connect()
    session.node_birth()
    session.device_birth("portal-03")
    session.device_data("portal-03", {"read_rate": 0.9})

    messages = session.rebirth()
    assert [message.message_type for message in messages] == [
        MessageType.NBIRTH,
        MessageType.DBIRTH,
        MessageType.DBIRTH,
    ]
    assert [message.payload.seq for message in messages] == [0, 1, 2]


def test_a_rebirth_keeps_the_bdseq_of_the_live_session():
    session = make_session()
    will = session.connect()
    before = next(m.value for m in will.message.payload.metrics if m.name == "bdSeq")
    nbirth = session.rebirth()[0]
    after = next(m.value for m in nbirth.payload.metrics if m.name == "bdSeq")
    assert before == after


def test_a_node_control_rebirth_command_is_what_triggers_it():
    session = make_session()
    session.connect()
    session.node_birth()
    assert session.handle_node_command({"Node Control/Rebirth": False}) == ()
    assert len(session.handle_node_command({"Node Control/Rebirth": True})) == 3


# ------------------------------------------------------------- QoS and retain


@pytest.mark.parametrize(
    ("message_type", "qos", "retain"),
    [
        (MessageType.NBIRTH, 0, False),
        (MessageType.DBIRTH, 0, False),
        (MessageType.NDATA, 0, False),
        (MessageType.DDATA, 0, False),
        (MessageType.NCMD, 0, False),
        (MessageType.DCMD, 0, False),
        (MessageType.DDEATH, 0, False),
        (MessageType.STATE, 1, True),
    ],
)
def test_qos_and_retain_match_the_table_iot_fleet_5_4_reads_from_the_specification(
    message_type, qos, retain
):
    assert qos_and_retain_for(message_type) == (qos, retain)


def test_the_ndeath_will_is_the_row_that_departs_from_its_siblings():
    session = make_session()
    will = session.connect()
    assert (will.qos, will.retain) == (1, False)


def test_every_row_with_no_specification_rule_id_carries_a_written_basis():
    """INV-QOS-2: a repo choice may not be mistaken for a specification rule."""
    for message_type, row in QOS_BY_TOPIC_CLASS.items():
        if row.rule_ids == ():
            assert "repo choice" in row.basis, message_type
        else:
            assert row.basis == "", message_type


# ---------------------------------------------------------------- UNS mirror


def test_the_json_mirror_is_derived_from_the_same_metric_model():
    """ARCHITECTURE section 5.1: the two namespaces cannot disagree."""
    clock = SimClock(tick_hz=1_000)
    session = make_session(clock)
    session.connect()
    session.node_birth()
    session.device_birth("portal-03")
    clock.advance_to(SimInstant(4_500))
    ddata = session.device_data("portal-03", {"read_rate": 0.987})

    mirror = session.mirror_records(ddata)
    assert len(mirror) == 1
    record = mirror[0]
    assert record.topic == "twinflow/dc-01/receiving/inbound-line-01/portal-03/read_rate"
    assert record.payload["value"] == pytest.approx(0.987)
    assert record.payload["unit"] == "1"
    assert record.payload["quality"] == "good"
    assert record.payload["device_ts"] == 4_500
    assert record.qos == 1
    assert record.retain is True


def test_the_mirror_resolves_an_alias_the_way_a_subscriber_must():
    session = make_session()
    session.connect()
    session.node_birth()
    session.device_birth("conveyor-02")
    ddata = session.device_data("conveyor-02", {"motor_temp_c": 71.4})
    assert ddata.payload.metrics[0].name is None
    assert session.mirror_records(ddata)[0].topic.endswith("/conveyor-02/motor_temp_c")


def test_a_ddeath_republishes_the_retained_mirror_as_bad_with_a_null_value():
    session = make_session()
    session.connect()
    session.node_birth()
    session.device_birth("portal-03")
    tombstones = session.mirror_tombstones("portal-03")
    assert {record.payload["quality"] for record in tombstones} == {"bad"}
    assert {record.payload["value"] for record in tombstones} == {None}
    assert all(record.retain for record in tombstones)


def test_ddeath_marks_the_device_dead_while_the_node_stays_up():
    session = make_session()
    session.connect()
    session.node_birth()
    session.device_birth("portal-03")
    session.device_death("portal-03")
    assert session.is_connected is True
    with pytest.raises(RuntimeError, match="DBIRTH"):
        session.device_data("portal-03", {"read_rate": 0.9})


# ------------------------------------------------------------------ datatypes


def test_the_datatype_enum_carries_the_values_the_payload_definition_fixes():
    assert (DataType.UInt32, DataType.UInt64, DataType.Float, DataType.Double) == (7, 8, 9, 10)
    assert (DataType.Boolean, DataType.String, DataType.DateTime) == (11, 12, 13)
    assert (DataType.DataSet, DataType.Template) == (16, 19)
    assert (DataType.FloatArray, DataType.DoubleArray) == (30, 31)


def test_quality_carries_the_three_codes_and_nothing_else():
    assert (Quality.BAD, Quality.GOOD, Quality.STALE) == (0, 192, 500)


# ---------------------------------------------------- the ISA-95 mapping (5.1)


def test_sparkplug_ids_join_the_first_three_levels_with_a_colon():
    assert SparkplugIds.for_path(PORTAL_PATH) == SparkplugIds(
        group_id="twinflow:dc-01:receiving",
        edge_node_id="inbound-line-01",
        device_id="portal-03",
    )


def test_the_isa95_path_is_recoverable_from_the_three_sparkplug_identifiers():
    ids = SparkplugIds.for_path(CONVEYOR_PATH)
    assert ids.to_uns_path(CONVEYOR_PATH.parameter) == CONVEYOR_PATH


def test_a_group_id_never_carries_a_character_the_specification_reserves():
    for reserved in ("+", "/", "#"):
        assert reserved not in IDS.group_id


def test_sparkplug_ids_refuse_a_group_id_that_is_not_three_colon_joined_levels():
    with pytest.raises(ValueError, match="three"):
        SparkplugIds(
            group_id="twinflow:dc-01", edge_node_id="inbound-line-01", device_id="portal-03"
        ).to_uns_path("read_rate")


# ------------------------------------------- an identifier cannot change a topic

# Every one of these values is joined into an MQTT topic with `/`. A level
# carrying `/`, `+`, or `#` addresses a topic other than the one the caller
# named, or subscribes where it meant to publish. `for_path` derives these from
# a validated UnsPath; the direct constructor is the one SparkplugEdgeNode
# takes, so it makes the same promise.


@pytest.mark.parametrize(
    ("group_id", "edge_node_id", "device_id"),
    [
        ("a:b:c", "node/+", "device"),
        ("a:b:c", "node", "device/#/x"),
        ("a:b:c", "node", "+"),
        ("a/b:c", "node", "device"),
        ("a:b:c#", "node", "device"),
        ("a:b", "node", "device"),
        ("a:b:c:d", "node", "device"),
        ("a:b:c", "Node", "device"),
        ("a:b:c", "node id", "device"),
        ("a:b:c", "", "device"),
    ],
)
def test_an_identifier_that_would_change_the_topic_is_refused(
    group_id: str, edge_node_id: str, device_id: str
):
    with pytest.raises(ValueError):
        SparkplugIds(group_id=group_id, edge_node_id=edge_node_id, device_id=device_id)


def test_the_addressing_of_a_real_point_still_constructs():
    """The control. A refusal that caught every value would pass the ten cases
    above and make the module unusable."""
    ids = SparkplugIds(
        group_id="twinflow:dc-01:receiving",
        edge_node_id="inbound-line-01",
        device_id="conveyor-02",
    )

    assert ids.to_uns_path("motor_temp_c").topic.count("/") == 5


def test_an_empty_device_id_addresses_the_node_itself():
    """A node message carries no fifth topic element, which is what an empty
    device id means here. Refusing it would refuse every NBIRTH."""
    assert SparkplugIds(group_id="a-1:b-1:c-1", edge_node_id="n-1", device_id="").device_id == ""


def test_a_device_id_passed_straight_to_topic_for_is_held_to_the_grammar():
    """The override reaches the topic without passing through SparkplugIds."""
    ids = SparkplugIds(group_id="a-1:b-1:c-1", edge_node_id="n-1", device_id="")

    with pytest.raises(ValueError):
        topic_for(ids, MessageType.DDATA, device_id="d-1/#")


def test_a_state_topic_will_not_carry_a_wildcard():
    with pytest.raises(ValueError):
        state_topic_for("host/#")
    assert state_topic_for("primary-host").endswith("primary-host")


@pytest.mark.parametrize("name", ["a/b#", "temp+", "#", "Device Temp/#"])
def test_a_metric_name_will_not_carry_an_mqtt_wildcard(name: str):
    """A metric name keys the alias table and reaches the payload, so a wildcard
    there is a collision waiting for the first subscriber that filters on it."""
    with pytest.raises(ValueError):
        MetricSpec(name=name, datatype=DataType.Double, unit="degC")


def test_a_metric_name_may_still_carry_a_slash():
    """A metric name is not an ISA-95 identifier. The specification's own
    `Node Control/Rebirth` carries a slash, so the rule here is narrower."""
    assert (
        MetricSpec(name=REBIRTH_METRIC, datatype=DataType.Boolean, unit="").name == REBIRTH_METRIC
    )
