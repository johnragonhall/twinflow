"""The Sparkplug B wire codec: a `Payload` as the bytes a publish carries.

API.md recorded this as owed, and recorded a reason that no longer holds: that
encoding needs the EPL-2.0 `sparkplug_b.proto` vendored under `schemas/`. It
does not. The Sparkplug specification version 3.0.0 prints the entire schema in
section 6.4.1, "Google Protocol Buffer Schema", and every field number below is
read from there. Nothing is generated from or derived from the `.proto` the
Eclipse Tahu project distributes, so the copyleft question that file raises
never arises and `twinflow-sensors` keeps its no-dependency claim.

Two things that claim is worth being exact about. The specification prints the
schema, so this is an implementation of a published normative document rather
than a reconstruction by anyone who had never seen one. And the field numbers
themselves are facts stated in that document; what is this project's own is the
code expressing them.

WHY THE MODEL IS NOT REDECLARED HERE

`Payload`, `Metric`, and `DataType` are `sparkplug.py`'s, and this module
imports them. Boundary rule A1.4 gives one public name exactly one owning
package and doctrine D-09 gives one owner per public symbol, so a codec
carrying its own parallel `Metric` would be a second definition of the same
idea that drifts from the first the day either one changes.

THREE PLACES A PAYLOAD CODEC GOES WRONG

Signed values are two's complement, not zigzag. The schema stores `Int8`,
`Int16`, and `Int32` in a `uint32` field and `Int64` in a `uint64`, so a
negative value is its two's complement in that width. Zigzag belongs to
`sint32` and `sint64`, which the schema does not use, and applying it would
publish a reading of minus five as roughly 4.29 billion.

Unknown fields are skipped, never refused. The schema declares `extensions` on
almost every message, so a conforming producer may send field numbers this
codec has never heard of, and raising on one would reject a payload the
specification calls valid.

A null metric declares itself and carries no value. `is_null` is a field rather
than a sentinel, which is the specification being explicit that a null is
stated rather than implied by a zero a consumer would read as a reading.

WHAT THIS IS NOT

Not a conformance claim. VAL-GATE-SPARK-001 names the Eclipse Technology
Compatibility Kit as its arbiter and that suite has not been run against this
code. The tests assert the encoding against the wire rules, against the field
numbers the specification prints, and against Google's protobuf runtime; none
of that is evidence of interoperability with a particular host application.
"""

from __future__ import annotations

import struct
from typing import Any

from twinflow.sensors.sparkplug import DataType, Metric, Payload, Quality

#: The four protobuf wire types this codec emits, plus the two deprecated group
#: markers, which are recognized only so `_skip` can traverse a message that
#: carries one rather than mis-frame everything after it.
_VARINT = 0
_FIXED64 = 1
_LENGTH_DELIMITED = 2
_START_GROUP = 3
_END_GROUP = 4
_FIXED32 = 5

#: A varint is capped at ten bytes, which is what 64 bits takes at seven bits
#: per byte. A longer run is a corrupt stream rather than a large number.
_MAX_VARINT_BYTES = 10

#: `Payload` fields, specification 6.4.1.
_PAYLOAD_TIMESTAMP = 1
_PAYLOAD_METRICS = 2
_PAYLOAD_SEQ = 3
_PAYLOAD_UUID = 4
_PAYLOAD_BODY = 5

#: `Payload.Metric` fields, specification 6.4.1.
_METRIC_NAME = 1
_METRIC_ALIAS = 2
_METRIC_TIMESTAMP = 3
_METRIC_DATATYPE = 4
_METRIC_IS_NULL = 7
_METRIC_PROPERTIES = 9

#: The `Metric` value oneof, fields 10 to 19.
_INT_VALUE = 10
_LONG_VALUE = 11
_FLOAT_VALUE = 12
_DOUBLE_VALUE = 13
_BOOLEAN_VALUE = 14
_STRING_VALUE = 15
_BYTES_VALUE = 16

#: `Payload.PropertySet` fields, and the `PropertyValue` oneof at 3 to 11. A
#: different numbering from `Metric`, kept separate rather than shared because
#: the overlap is a coincidence of shape rather than one rule.
_PROPERTY_KEYS = 1
_PROPERTY_VALUES = 2
_PROPERTY_TYPE = 1
_PROPERTY_IS_NULL = 2
_PROPERTY_INT = 3
_PROPERTY_LONG = 4
_PROPERTY_FLOAT = 5
_PROPERTY_DOUBLE = 6
_PROPERTY_BOOLEAN = 7
_PROPERTY_STRING = 8

#: The datatypes the schema stores signed inside an unsigned field, with the
#: width the two's complement is taken in.
_SIGNED_WIDTH: dict[DataType, int] = {
    DataType.Int8: 32,
    DataType.Int16: 32,
    DataType.Int32: 32,
    DataType.Int64: 64,
}

#: Which value field carries each datatype. The arrays ride in `bytes_value`
#: packed little-endian rather than in a repeated field of their own.
_VALUE_FIELD: dict[DataType, int] = {
    DataType.Int8: _INT_VALUE,
    DataType.Int16: _INT_VALUE,
    DataType.Int32: _INT_VALUE,
    DataType.UInt8: _INT_VALUE,
    DataType.UInt16: _INT_VALUE,
    DataType.UInt32: _INT_VALUE,
    DataType.Int64: _LONG_VALUE,
    DataType.UInt64: _LONG_VALUE,
    DataType.DateTime: _LONG_VALUE,
    DataType.Float: _FLOAT_VALUE,
    DataType.Double: _DOUBLE_VALUE,
    DataType.Boolean: _BOOLEAN_VALUE,
    DataType.String: _STRING_VALUE,
    DataType.Text: _STRING_VALUE,
    DataType.UUID: _STRING_VALUE,
    DataType.Bytes: _BYTES_VALUE,
    DataType.File: _BYTES_VALUE,
    **{
        datatype: _BYTES_VALUE
        for datatype in (
            DataType.Int8Array,
            DataType.Int16Array,
            DataType.Int32Array,
            DataType.Int64Array,
            DataType.UInt8Array,
            DataType.UInt16Array,
            DataType.UInt32Array,
            DataType.UInt64Array,
            DataType.FloatArray,
            DataType.DoubleArray,
            DataType.BooleanArray,
            DataType.StringArray,
            DataType.DateTimeArray,
        )
    },
}


class WireError(ValueError):
    """A payload that cannot be written, or bytes that are not one."""


# --------------------------------------------------------------------- signing


def to_unsigned(value: int, bits: int) -> int:
    """A signed value as its two's complement in `bits` width."""
    return value & ((1 << bits) - 1)


def to_signed(value: int, bits: int) -> int:
    """The inverse, for a field the schema declares signed."""
    value &= (1 << bits) - 1
    return value - (1 << bits) if value >= 1 << (bits - 1) else value


# -------------------------------------------------------------------- encoding


def _varint(value: int) -> bytes:
    if value < 0:
        raise WireError(f"a varint is unsigned, got {value}")
    if value > 0xFFFFFFFFFFFFFFFF:
        raise WireError(f"{value} does not fit in 64 bits")
    out = bytearray()
    while True:
        byte = value & 0x7F
        value >>= 7
        if value:
            out.append(byte | 0x80)
        else:
            out.append(byte)
            return bytes(out)


def _tag(field_number: int, wire_type: int) -> bytes:
    return _varint((field_number << 3) | wire_type)


def _uint(field_number: int, value: int) -> bytes:
    return _tag(field_number, _VARINT) + _varint(value)


def _bool(field_number: int, value: bool) -> bytes:
    return _tag(field_number, _VARINT) + _varint(1 if value else 0)


def _delimited(field_number: int, value: bytes) -> bytes:
    return _tag(field_number, _LENGTH_DELIMITED) + _varint(len(value)) + value


def _string(field_number: int, value: str) -> bytes:
    return _delimited(field_number, value.encode("utf-8"))


# -------------------------------------------------------------------- decoding


class _Reader:
    """A cursor over one message, bounded so a nested message cannot overrun."""

    __slots__ = ("_data", "_offset", "_end")

    def __init__(self, data: bytes, offset: int = 0, end: int | None = None) -> None:
        self._data = data
        self._offset = offset
        self._end = len(data) if end is None else end

    @property
    def offset(self) -> int:
        return self._offset

    def at_end(self) -> bool:
        return self._offset >= self._end

    def varint(self) -> int:
        value = 0
        shift = 0
        for _ in range(_MAX_VARINT_BYTES):
            if self._offset >= self._end:
                raise WireError("the buffer ended in the middle of a varint")
            byte = self._data[self._offset]
            self._offset += 1
            value |= (byte & 0x7F) << shift
            if not byte & 0x80:
                return value
            shift += 7
        raise WireError("a varint ran past 64 bits, which is a corrupt stream")

    def tag(self) -> tuple[int, int]:
        raw = self.varint()
        number = raw >> 3
        if number == 0:
            raise WireError("field number 0 is not a legal tag")
        return number, raw & 0x07

    def take(self, length: int) -> bytes:
        stop = self._offset + length
        if stop > self._end:
            raise WireError(f"a field claims {length} bytes and fewer remain")
        chunk = self._data[self._offset : stop]
        self._offset = stop
        return chunk

    def blob(self) -> bytes:
        return self.take(self.varint())

    def text(self) -> str:
        return self.blob().decode("utf-8")

    def skip(self, wire_type: int) -> None:
        """Step over a field this decoder has no use for.

        Required rather than optional: the schema declares `extensions` on
        almost every message, so refusing an unknown field would reject a
        payload the specification calls valid.
        """
        if wire_type == _VARINT:
            self.varint()
        elif wire_type == _FIXED64:
            self.take(8)
        elif wire_type == _LENGTH_DELIMITED:
            self.take(self.varint())
        elif wire_type == _FIXED32:
            self.take(4)
        elif wire_type == _START_GROUP:
            self._skip_group()
        elif wire_type == _END_GROUP:
            raise WireError("an end-group tag with no start-group before it")
        else:
            raise WireError(f"wire type {wire_type} is not one the format defines")

    def _skip_group(self) -> None:
        depth = 1
        while depth:
            if self.at_end():
                raise WireError("the buffer ended inside a group")
            _, wire_type = self.tag()
            if wire_type == _START_GROUP:
                depth += 1
            elif wire_type == _END_GROUP:
                depth -= 1
            else:
                self.skip(wire_type)


# ------------------------------------------------------------------ properties


def _property_datatype(value: Any) -> DataType:
    """The datatype a property value is written under.

    `MetricSpec.properties()` hands back plain Python values, so the datatype is
    inferred here rather than declared. Every case is listed and anything else
    is refused: guessing would publish a property a consumer reads as a
    different type than the producer meant.

    `Quality` is checked before `int` because it is an `IntEnum`, and `bool`
    before `int` for the same reason in the other direction.
    """
    if isinstance(value, Quality):
        return DataType.Int32
    if isinstance(value, bool):
        return DataType.Boolean
    if isinstance(value, int):
        return DataType.Int64
    if isinstance(value, float):
        return DataType.Double
    if isinstance(value, str):
        return DataType.String
    raise WireError(
        f"a metric property of type {type(value).__name__} has no datatype here. "
        f"Inferring one would publish a property a consumer reads as something "
        f"other than what the producer meant"
    )


def _encode_property_value(value: Any) -> bytes:
    datatype = _property_datatype(value)
    out = bytearray(_uint(_PROPERTY_TYPE, int(datatype)))
    if datatype is DataType.Boolean:
        out += _bool(_PROPERTY_BOOLEAN, bool(value))
    elif datatype is DataType.Int32:
        out += _uint(_PROPERTY_INT, to_unsigned(int(value), 32))
    elif datatype is DataType.Int64:
        out += _uint(_PROPERTY_LONG, to_unsigned(int(value), 64))
    elif datatype is DataType.Double:
        out += _tag(_PROPERTY_DOUBLE, _FIXED64) + struct.pack("<d", float(value))
    else:
        out += _string(_PROPERTY_STRING, str(value))
    return bytes(out)


def _encode_properties(properties: Any) -> bytes:
    """A property set: parallel repeated keys and values.

    Sorted by key, because a consumer zips the two repeated fields by position
    and doctrine D-03 forbids an iteration order that reaches a value a second
    process has to reproduce. A dict's insertion order is exactly such an order.
    """
    items = sorted(properties.items())
    out = bytearray()
    for key, _ in items:
        out += _string(_PROPERTY_KEYS, key)
    for _, value in items:
        out += _delimited(_PROPERTY_VALUES, _encode_property_value(value))
    return bytes(out)


def _decode_property_value(data: bytes) -> Any:
    reader = _Reader(data)
    datatype = DataType.Unknown
    value: Any = None
    while not reader.at_end():
        number, wire_type = reader.tag()
        if number == _PROPERTY_TYPE:
            datatype = DataType(reader.varint())
        elif number == _PROPERTY_IS_NULL:
            reader.varint()
        elif number == _PROPERTY_INT:
            value = to_signed(reader.varint(), 32)
        elif number == _PROPERTY_LONG:
            raw = reader.varint()
            value = to_signed(raw, 64) if datatype in _SIGNED_WIDTH else raw
        elif number == _PROPERTY_FLOAT:
            value = struct.unpack("<f", reader.take(4))[0]
        elif number == _PROPERTY_DOUBLE:
            value = struct.unpack("<d", reader.take(8))[0]
        elif number == _PROPERTY_BOOLEAN:
            value = reader.varint() != 0
        elif number == _PROPERTY_STRING:
            value = reader.text()
        else:
            reader.skip(wire_type)
    return value


def _decode_properties(data: bytes) -> dict[str, Any]:
    keys: list[str] = []
    values: list[Any] = []
    reader = _Reader(data)
    while not reader.at_end():
        number, wire_type = reader.tag()
        if number == _PROPERTY_KEYS:
            keys.append(reader.text())
        elif number == _PROPERTY_VALUES:
            values.append(_decode_property_value(reader.blob()))
        else:
            reader.skip(wire_type)
    return dict(zip(keys, values, strict=False))


# --------------------------------------------------------------------- metrics


def _encode_value(field_number: int, datatype: DataType, value: Any) -> bytes:
    if field_number in (_INT_VALUE, _LONG_VALUE):
        if isinstance(value, bool) or not isinstance(value, int):
            raise WireError(
                f"datatype {datatype.name} is carried in an integer field and the value "
                f"is {type(value).__name__}"
            )
        width = _SIGNED_WIDTH.get(datatype)
        if width is not None:
            return _uint(field_number, to_unsigned(value, width))
        if value < 0:
            raise WireError(
                f"datatype {datatype.name} is unsigned and the value is {value}; writing "
                f"it would publish a very large positive number"
            )
        return _uint(field_number, value)
    if field_number == _FLOAT_VALUE:
        return _tag(field_number, _FIXED32) + struct.pack("<f", float(value))
    if field_number == _DOUBLE_VALUE:
        return _tag(field_number, _FIXED64) + struct.pack("<d", float(value))
    if field_number == _BOOLEAN_VALUE:
        return _bool(field_number, bool(value))
    if field_number == _STRING_VALUE:
        if not isinstance(value, str):
            raise WireError(f"datatype {datatype.name} needs a str")
        return _string(field_number, value)
    if not isinstance(value, (bytes, bytearray)):
        raise WireError(f"datatype {datatype.name} needs bytes")
    return _delimited(field_number, bytes(value))


def encode_metric(metric: Metric) -> bytes:
    """One `Metric` as the bytes it occupies inside a payload."""
    if metric.datatype is None:
        raise WireError(
            f"metric {metric.name or metric.alias!r} carries no datatype, and the schema "
            f"puts it at field 4 on every metric including an aliased one"
        )
    out = bytearray()
    if metric.name is not None:
        out += _string(_METRIC_NAME, metric.name)
    if metric.alias is not None:
        out += _uint(_METRIC_ALIAS, metric.alias)
    if metric.timestamp is not None:
        out += _uint(_METRIC_TIMESTAMP, metric.timestamp)
    out += _uint(_METRIC_DATATYPE, int(metric.datatype))
    if metric.properties:
        out += _delimited(_METRIC_PROPERTIES, _encode_properties(metric.properties))

    if metric.value is None:
        # The specification is explicit that a null is stated rather than
        # implied, so the flag is written and no value goes beside it.
        out += _bool(_METRIC_IS_NULL, True)
        return bytes(out)

    field_number = _VALUE_FIELD.get(metric.datatype)
    if field_number is None:
        raise WireError(
            f"datatype {metric.datatype.name} has no value field in the Metric oneof, so "
            f"this metric would travel with no value at all"
        )
    out += _encode_value(field_number, metric.datatype, metric.value)
    return bytes(out)


def decode_metric(data: bytes) -> Metric:
    """The `Metric` those bytes carry."""
    name: str | None = None
    alias: int | None = None
    timestamp: int | None = None
    datatype = DataType.Unknown
    is_null = False
    properties: dict[str, Any] = {}
    pending: tuple[int, int] | None = None

    reader = _Reader(data)
    while not reader.at_end():
        number, wire_type = reader.tag()
        if number == _METRIC_NAME:
            name = reader.text()
        elif number == _METRIC_ALIAS:
            alias = reader.varint()
        elif number == _METRIC_TIMESTAMP:
            timestamp = reader.varint()
        elif number == _METRIC_DATATYPE:
            datatype = DataType(reader.varint())
        elif number == _METRIC_IS_NULL:
            is_null = reader.varint() != 0
        elif number == _METRIC_PROPERTIES:
            properties = _decode_properties(reader.blob())
        elif _INT_VALUE <= number <= 19:
            # Read after the loop: how a value is interpreted depends on the
            # datatype at field 4, which a producer may emit after it.
            pending = (number, reader.offset)
            reader.skip(wire_type)
        else:
            reader.skip(wire_type)

    value: Any = None
    if pending is not None and not is_null:
        value = _decode_value(pending[0], datatype, _Reader(data, pending[1]))

    return Metric(
        value=value,
        alias=alias,
        name=name,
        datatype=datatype,
        timestamp=timestamp,
        properties=properties,
    )


def _decode_value(field_number: int, datatype: DataType, reader: _Reader) -> Any:
    if field_number in (_INT_VALUE, _LONG_VALUE):
        raw = reader.varint()
        width = _SIGNED_WIDTH.get(datatype)
        return to_signed(raw, width) if width is not None else raw
    if field_number == _FLOAT_VALUE:
        return struct.unpack("<f", reader.take(4))[0]
    if field_number == _DOUBLE_VALUE:
        return struct.unpack("<d", reader.take(8))[0]
    if field_number == _BOOLEAN_VALUE:
        return reader.varint() != 0
    if field_number == _STRING_VALUE:
        return reader.text()
    return reader.blob()


# -------------------------------------------------------------------- payloads


def encode_payload(payload: Payload) -> bytes:
    """One `Payload` as the bytes an MQTT publish carries."""
    out = bytearray(_uint(_PAYLOAD_TIMESTAMP, payload.timestamp))
    for metric in payload.metrics:
        out += _delimited(_PAYLOAD_METRICS, encode_metric(metric))
    if payload.seq is not None:
        out += _uint(_PAYLOAD_SEQ, payload.seq)
    return bytes(out)


def decode_payload(data: bytes) -> Payload:
    """The `Payload` those bytes carry, or `WireError` if they carry none."""
    timestamp = 0
    seq: int | None = None
    metrics: list[Metric] = []

    reader = _Reader(data)
    while not reader.at_end():
        number, wire_type = reader.tag()
        if number == _PAYLOAD_TIMESTAMP:
            timestamp = reader.varint()
        elif number == _PAYLOAD_METRICS:
            metrics.append(decode_metric(reader.blob()))
        elif number == _PAYLOAD_SEQ:
            seq = reader.varint()
        elif number in (_PAYLOAD_UUID, _PAYLOAD_BODY):
            # Read and dropped rather than skipped blindly, so a malformed one
            # still fails here rather than at whatever reads the payload next.
            reader.blob()
        else:
            reader.skip(wire_type)

    return Payload(timestamp=timestamp, metrics=tuple(metrics), seq=seq)


__all__ = [
    "WireError",
    "decode_metric",
    "decode_payload",
    "encode_metric",
    "encode_payload",
    "to_signed",
    "to_unsigned",
]
