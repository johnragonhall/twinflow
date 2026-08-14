"""The Sparkplug B wire codec, against specification 6.4.1.

Three tiers, and each one catches something the others cannot.

The golden byte strings are worked out from the wire rules and the field
numbers the specification prints, rather than captured from this encoder's own
output. A recorded expectation passes on an encoder that is wrong in a stable
way, which is the one failure a codec cannot afford.

The round trips cover the tree this package actually publishes, properties and
aliasing included.

The cross-check drives Google's protobuf runtime over a descriptor built in
code from the same field numbers. It is the only test here that can catch a
misreading shared by the encoder and its own golden bytes, and it skips rather
than fails when protobuf is absent, because nothing in `src/` needs it.

None of this is a conformance claim. VAL-GATE-SPARK-001 names the Eclipse
Technology Compatibility Kit as its arbiter and that suite has not run here.
"""

from __future__ import annotations

import pytest

from twinflow.sensors import DataType, Metric, Payload, Quality
from twinflow.sensors.wire import (
    WireError,
    decode_metric,
    decode_payload,
    encode_metric,
    encode_payload,
    to_signed,
    to_unsigned,
)

# --------------------------------------------------------------- golden bytes


def test_a_payload_lays_its_fields_out_where_the_schema_puts_them():
    """`Payload.timestamp` is field 1 and `seq` is field 3, both uint64 varints.
    Field 1 varint is tag 0x08, field 3 varint is tag 0x18."""
    assert encode_payload(Payload(timestamp=1, metrics=(), seq=0)) == b"\x08\x01\x18\x00"


def test_a_metric_lays_its_fields_out_where_the_schema_puts_them():
    """name 1, alias 2, datatype 4, and an Int32 value in int_value at 10."""
    encoded = encode_metric(Metric(value=7, alias=1, name="a", datatype=DataType.Int32))

    assert encoded == (
        b"\x0a\x01a"  # field 1, length 1, "a"
        b"\x10\x01"  # field 2, varint 1
        b"\x20\x03"  # field 4, varint 3, which is Int32
        b"\x50\x07"  # field 10, varint 7
    )


def test_a_metric_sits_inside_the_payload_at_field_two():
    inner = encode_metric(Metric(value=7, alias=1, datatype=DataType.Int32))
    encoded = encode_payload(
        Payload(timestamp=1, metrics=(Metric(value=7, alias=1, datatype=DataType.Int32),))
    )

    assert encoded == b"\x08\x01" + b"\x12" + bytes([len(inner)]) + inner


def test_a_float_rides_in_field_twelve_as_little_endian_fixed32():
    # Field 12, wire type 5, is (12 << 3) | 5 == 0x65.
    encoded = encode_metric(Metric(value=1.0, alias=1, datatype=DataType.Float))

    assert encoded.endswith(b"\x65\x00\x00\x80\x3f")


def test_a_double_rides_in_field_thirteen_as_little_endian_fixed64():
    # Field 13, wire type 1, is (13 << 3) | 1 == 0x69.
    encoded = encode_metric(Metric(value=1.0, alias=1, datatype=DataType.Double))

    assert encoded.endswith(b"\x69\x00\x00\x00\x00\x00\x00\xf0\x3f")


# -------------------------------------------------------------- signed values


@pytest.mark.parametrize(
    ("value", "bits", "unsigned"),
    [
        (-1, 32, 0xFFFFFFFF),
        (-1, 64, 0xFFFFFFFFFFFFFFFF),
        (-2147483648, 32, 0x80000000),
        (0, 32, 0),
    ],
)
def test_a_signed_value_is_two_s_complement_in_its_width(value: int, bits: int, unsigned: int):
    """Zigzag belongs to sint32 and sint64, which this schema does not use.
    Applying it would emit numbers no conforming consumer decodes."""
    assert to_unsigned(value, bits) == unsigned
    assert to_signed(unsigned, bits) == value


@pytest.mark.parametrize(
    ("datatype", "value"),
    [
        (DataType.Int8, -128),
        (DataType.Int16, -32768),
        (DataType.Int32, -2147483648),
        (DataType.Int32, -1),
        (DataType.Int64, -9223372036854775808),
    ],
)
def test_a_negative_reading_survives_the_round_trip(datatype: DataType, value: int):
    """The trap. Int32 travels in a uint32 field, so a temperature below zero
    written without the conversion arrives as roughly 4.29 billion."""
    metric = Metric(value=value, alias=1, datatype=datatype)

    assert decode_metric(encode_metric(metric)).value == value


def test_a_negative_value_in_an_unsigned_datatype_is_refused():
    with pytest.raises(WireError, match="unsigned"):
        encode_metric(Metric(value=-1, alias=1, datatype=DataType.UInt32))


# ------------------------------------------------------------------- aliasing


def test_an_aliased_data_metric_carries_the_alias_and_the_value_and_no_name():
    """The rule that makes aliasing worth doing, and the one a reimplementation
    most often gets wrong by echoing the name on every message."""
    restored = decode_metric(encode_metric(Metric(value=21.5, alias=7, datatype=DataType.Float)))

    assert restored.name is None
    assert restored.alias == 7
    assert restored.value == pytest.approx(21.5)


def test_a_birth_metric_carries_its_name_and_its_properties():
    metric = Metric(
        value=21.5,
        alias=1,
        name="Temperature",
        datatype=DataType.Float,
        properties={"engUnit": "degC", "Quality": Quality.GOOD, "engLow": -40.0},
    )

    restored = decode_metric(encode_metric(metric))

    assert restored.name == "Temperature"
    assert restored.properties["engUnit"] == "degC"
    assert restored.properties["Quality"] == int(Quality.GOOD)
    assert restored.properties["engLow"] == pytest.approx(-40.0)


def test_properties_are_written_in_sorted_key_order():
    """A consumer zips the two repeated fields by position, and doctrine D-03
    forbids an iteration order reaching a value a second process reproduces. A
    dict's insertion order is exactly such an order."""
    one = encode_metric(
        Metric(value=1, alias=1, datatype=DataType.Int32, properties={"b": "2", "a": "1"})
    )
    other = encode_metric(
        Metric(value=1, alias=1, datatype=DataType.Int32, properties={"a": "1", "b": "2"})
    )

    assert one == other


def test_a_property_type_with_no_mapping_is_refused_rather_than_guessed():
    with pytest.raises(WireError, match="no datatype here"):
        encode_metric(
            Metric(value=1, alias=1, datatype=DataType.Int32, properties={"odd": object()})
        )


# ---------------------------------------------------------------------- nulls


def test_a_metric_with_no_value_declares_itself_null():
    """The specification is explicit that a null is stated rather than implied
    by a zero a consumer would read as a reading."""
    encoded = encode_metric(Metric(value=None, alias=1, datatype=DataType.Float))

    # Field 7, varint, is tag 0x38.
    assert b"\x38\x01" in encoded
    assert decode_metric(encoded).value is None


# ------------------------------------------------------------- field ordering


def test_the_value_is_read_even_when_the_datatype_arrives_after_it():
    """A producer may emit fields in any order, and how a value is read depends
    on the datatype. A decoder reading the value where it found it would get a
    signed metric wrong whenever field 4 came late."""
    encoded = encode_metric(Metric(value=-5, alias=1, datatype=DataType.Int32))
    datatype_field = b"\x20\x03"
    reordered = encoded.replace(datatype_field, b"") + datatype_field

    assert decode_metric(reordered).value == -5


# ------------------------------------------------------------- unknown fields


def test_a_payload_carrying_an_unknown_field_still_decodes():
    """`Payload` declares `extensions 6 to max`, so a newer producer may send
    field 6, and refusing it would reject a payload the specification calls
    valid."""
    extended = encode_payload(Payload(timestamp=1, metrics=(), seq=2)) + b"\x30\x2a"

    restored = decode_payload(extended)

    assert restored.timestamp == 1
    assert restored.seq == 2


def test_bytes_that_are_not_a_payload_are_refused():
    with pytest.raises(WireError):
        decode_payload(b"\xff\xff\xff\xff")


def test_a_metric_with_no_datatype_is_refused_by_name():
    """The schema puts the datatype at field 4 on every metric, aliased ones
    included, so a metric without one cannot be written at all."""
    with pytest.raises(WireError, match="no datatype"):
        encode_metric(Metric(value=1, alias=1))


# --------------------------------------------------------------- whole payload


def test_a_full_payload_round_trips():
    payload = Payload(
        timestamp=1700000000000,
        seq=42,
        metrics=(
            Metric(value=21.5, alias=1, name="Temperature", datatype=DataType.Float),
            Metric(value=-5, alias=2, name="Offset", datatype=DataType.Int64),
            Metric(value="line-01", alias=3, name="Line", datatype=DataType.String),
            Metric(value=True, alias=4, name="Running", datatype=DataType.Boolean),
        ),
    )

    restored = decode_payload(encode_payload(payload))

    assert restored.timestamp == 1700000000000
    assert restored.seq == 42
    assert [m.name for m in restored.metrics] == ["Temperature", "Offset", "Line", "Running"]
    assert [m.value for m in restored.metrics][1:] == [-5, "line-01", True]


# ------------------------------------------------- cross-check, protobuf runtime


def _payload_class():
    """A descriptor built from the field numbers specification 6.4.1 prints.

    Built in code rather than compiled from the Eclipse `.proto`, so that file
    stays unread here as it does in `src/`.
    """
    from typing import Any, cast

    from google.protobuf import descriptor_pb2, descriptor_pool, message_factory

    # The pb2 modules are generated at import time, so their members exist at
    # runtime and not in any stub. Cast rather than suppress line by line: the
    # dynamism is the whole module's, not four attributes'.
    generated = cast(Any, descriptor_pb2)
    field_proto = generated.FieldDescriptorProto
    file_proto = generated.FileDescriptorProto()
    file_proto.name = "twinflow_sparkplug_crosscheck.proto"
    file_proto.package = "crosscheck"
    file_proto.syntax = "proto2"

    metric = file_proto.message_type.add()
    metric.name = "Metric"
    for name, number, kind in (
        ("name", 1, field_proto.TYPE_STRING),
        ("alias", 2, field_proto.TYPE_UINT64),
        ("timestamp", 3, field_proto.TYPE_UINT64),
        ("datatype", 4, field_proto.TYPE_UINT32),
        ("is_null", 7, field_proto.TYPE_BOOL),
        ("int_value", 10, field_proto.TYPE_UINT32),
        ("long_value", 11, field_proto.TYPE_UINT64),
        ("float_value", 12, field_proto.TYPE_FLOAT),
        ("double_value", 13, field_proto.TYPE_DOUBLE),
        ("boolean_value", 14, field_proto.TYPE_BOOL),
        ("string_value", 15, field_proto.TYPE_STRING),
    ):
        field = metric.field.add()
        field.name, field.number = name, number
        field.label, field.type = field_proto.LABEL_OPTIONAL, kind

    payload = file_proto.message_type.add()
    payload.name = "Payload"
    for name, number, kind in (
        ("timestamp", 1, field_proto.TYPE_UINT64),
        ("seq", 3, field_proto.TYPE_UINT64),
    ):
        field = payload.field.add()
        field.name, field.number = name, number
        field.label, field.type = field_proto.LABEL_OPTIONAL, kind
    metrics = payload.field.add()
    metrics.name, metrics.number = "metrics", 2
    metrics.label, metrics.type = field_proto.LABEL_REPEATED, field_proto.TYPE_MESSAGE
    metrics.type_name = ".crosscheck.Metric"

    pool = cast(Any, descriptor_pool).DescriptorPool()
    pool.Add(file_proto)
    return message_factory.GetMessageClass(pool.FindMessageTypeByName("crosscheck.Payload"))


@pytest.fixture
def sample() -> Payload:
    return Payload(
        timestamp=1700000000000,
        seq=42,
        metrics=(
            Metric(value=21.5, alias=1, name="Temperature", datatype=DataType.Float),
            Metric(value=-5, alias=2, name="Offset", datatype=DataType.Int32),
            Metric(value=-9223372036854775808, alias=3, name="Big", datatype=DataType.Int64),
            Metric(value="line-01", alias=4, name="Line", datatype=DataType.String),
            Metric(value=True, alias=5, name="Running", datatype=DataType.Boolean),
        ),
    )


def test_protobuf_consumes_every_byte_this_codec_writes(sample: Payload):
    """`ParseFromString` returns how much it consumed. Anything short of the
    whole buffer means a field is framed wrongly, even when every value that
    did parse came out right."""
    pytest.importorskip("google.protobuf", reason="a development-only cross-check")
    wire = encode_payload(sample)

    parsed = _payload_class()()

    assert parsed.ParseFromString(wire) == len(wire)


def test_protobuf_reads_a_negative_value_as_the_two_s_complement(sample: Payload):
    """The signed claim, checked by something other than this codec. protobuf
    declares these fields unsigned, so it reports the raw stored number."""
    pytest.importorskip("google.protobuf", reason="a development-only cross-check")
    parsed = _payload_class()()
    parsed.ParseFromString(encode_payload(sample))

    assert parsed.metrics[1].int_value == (-5 & 0xFFFFFFFF)
    assert parsed.metrics[2].long_value == (-9223372036854775808 & 0xFFFFFFFFFFFFFFFF)


def test_this_codec_reads_what_protobuf_writes(sample: Payload):
    """The other direction. An encoder can be self-consistent and unreadable,
    and so can a decoder."""
    pytest.importorskip("google.protobuf", reason="a development-only cross-check")
    parsed = _payload_class()()
    parsed.ParseFromString(encode_payload(sample))

    restored = decode_payload(parsed.SerializeToString())

    assert restored.timestamp == 1700000000000
    assert [m.value for m in restored.metrics][1:4] == [-5, -9223372036854775808, "line-01"]
