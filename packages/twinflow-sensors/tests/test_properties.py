"""Hypothesis properties over the four sharp edges of these two work packages.

Each property names the observation that fails it, per doctrine D-12. The
sequence wrap, the alias table established by DBIRTH, the exclusion of the
metric name from an aliased data message, and the refusal of an empty EPC
prefix are all decidable from a written rule rather than from this repository
agreeing with itself.
"""

from __future__ import annotations

import string

import pytest
from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st

from twinflow.config import UnsPath
from twinflow.kernel import SimClock, SimInstant
from twinflow.sensors import (
    DataType,
    EdgeNodeSession,
    EpcPrefixFilter,
    InventoryAccumulator,
    Message,
    MessageType,
    MetricSpec,
    SparkplugIds,
    TagRead,
)

pytestmark = pytest.mark.property

HEX = string.hexdigits[:16].upper()

metric_names = st.text(
    alphabet=st.sampled_from(string.ascii_lowercase + string.digits + "_"), min_size=1, max_size=12
).filter(lambda name: name[0] in string.ascii_lowercase)

epcs = st.text(alphabet=st.sampled_from(HEX), min_size=24, max_size=24)

#: The grammar twinflow.config admits, not a looser approximation of it. A
#: strategy that generated `dc01-` would be generating names the namespace
#: refuses, and the property would be proving something about nothing.
identifiers = st.from_regex(r"\A[a-z0-9]{1,4}(-[a-z0-9]{1,4}){0,2}\Z", fullmatch=True)
parameters = st.from_regex(r"\A[a-z][a-z0-9]{0,3}(_[a-z0-9]{1,4}){0,2}\Z", fullmatch=True)


def session_with(names: list[str]) -> EdgeNodeSession:
    return EdgeNodeSession(
        group_id="twinflow:dc-01:receiving",
        edge_node_id="inbound-line-01",
        clock=SimClock(tick_hz=1_000),
        node_metrics=(MetricSpec(name="sf_dropped_records", datatype=DataType.UInt64, unit="1"),),
        devices={
            "portal-03": tuple(
                MetricSpec(name=name, datatype=DataType.Float, unit="1") for name in names
            )
        },
    )


# --------------------------------------------------------------- sequence wrap


def seq_of(message: Message) -> int:
    """The payload's sequence number.

    `Payload.seq` is optional because the specification leaves it off some
    message types, so reading it as an `int` here asserts that a birth or a
    data message carries one rather than assuming it.
    """
    seq = message.payload.seq
    assert seq is not None, f"a {message.payload!r} carries a sequence number"
    return seq


@settings(max_examples=200, deadline=None)
@given(publishes=st.integers(min_value=0, max_value=1_200))
def test_seq_stays_in_the_byte_the_specification_gives_it(publishes):
    session = session_with(["read_rate"])
    session.connect()
    seen = [seq_of(session.node_birth()), seq_of(session.device_birth("portal-03"))]
    for _ in range(publishes):
        seen.append(seq_of(session.device_data("portal-03", {"read_rate": 0.9})))
    assert all(0 <= value <= 255 for value in seen)


@settings(max_examples=200, deadline=None)
@given(publishes=st.integers(min_value=1, max_value=1_200))
def test_consecutive_seq_values_differ_by_exactly_one_modulo_256(publishes):
    session = session_with(["read_rate"])
    session.connect()
    seen = [seq_of(session.node_birth()), seq_of(session.device_birth("portal-03"))]
    for _ in range(publishes):
        seen.append(seq_of(session.device_data("portal-03", {"read_rate": 0.9})))
    steps = {(b - a) % 256 for a, b in zip(seen[:-1], seen[1:], strict=True)}
    assert steps == {1}


@settings(max_examples=200, deadline=None)
@given(before=st.integers(min_value=0, max_value=600))
def test_a_rebirth_always_restarts_the_session_at_seq_zero(before):
    session = session_with(["read_rate"])
    session.connect()
    session.node_birth()
    session.device_birth("portal-03")
    for _ in range(before):
        session.device_data("portal-03", {"read_rate": 0.9})
    assert session.rebirth()[0].payload.seq == 0


# ----------------------------------------------------------------- alias table


@settings(max_examples=200, deadline=None)
@given(names=st.lists(metric_names, min_size=1, max_size=12, unique=True))
def test_dbirth_establishes_an_alias_for_every_metric_a_device_will_ever_publish(names):
    session = session_with(names)
    session.connect()
    session.node_birth()
    dbirth = session.device_birth("portal-03")
    # `Metric.name` is optional because a DDATA metric may address itself by
    # alias alone. A DBIRTH is the message that establishes those aliases, so
    # every metric in one names itself, and that is asserted before the names
    # are compared rather than assumed by the comparison.
    published = [metric.name for metric in dbirth.payload.metrics]
    assert all(name is not None for name in published)
    assert sorted(name for name in published if name is not None) == sorted(names)
    assert all(metric.alias is not None for metric in dbirth.payload.metrics)
    assert all(metric.datatype is not None for metric in dbirth.payload.metrics)


@settings(max_examples=200, deadline=None)
@given(names=st.lists(metric_names, min_size=1, max_size=12, unique=True))
def test_no_alias_is_reused_and_none_is_zero(names):
    session = session_with(names)
    session.connect()
    aliases = list(session.alias_table().values())
    assert len(set(aliases)) == len(aliases)
    assert all(alias >= 1 for alias in aliases)


@settings(max_examples=200, deadline=None, suppress_health_check=[HealthCheck.too_slow])
@given(names=st.lists(metric_names, min_size=1, max_size=12, unique=True), data=st.data())
def test_a_declaration_order_never_reaches_the_alias_table(names, data):
    shuffled = data.draw(st.permutations(names))
    assert session_declared(names).alias_table() == session_declared(list(shuffled)).alias_table()


def session_declared(names: list[str]) -> EdgeNodeSession:
    session = session_with(names)
    session.connect()
    return session


# ------------------------------------------------- the name excluded from data


@settings(max_examples=200, deadline=None)
@given(names=st.lists(metric_names, min_size=1, max_size=8, unique=True), data=st.data())
def test_an_aliased_data_message_never_carries_the_metric_name(names, data):
    changed = data.draw(st.lists(st.sampled_from(names), min_size=1, max_size=8, unique=True))
    session = session_with(names)
    session.connect()
    session.node_birth()
    session.device_birth("portal-03")
    ddata = session.device_data("portal-03", dict.fromkeys(changed, 1.0))
    assert ddata.message_type is MessageType.DDATA
    assert all(metric.name is None for metric in ddata.payload.metrics)
    assert all(metric.alias is not None for metric in ddata.payload.metrics)
    assert {metric.alias for metric in ddata.payload.metrics} == {
        session.alias_table()[("portal-03", name)] for name in changed
    }


@settings(max_examples=200, deadline=None)
@given(
    names=st.lists(metric_names, min_size=1, max_size=8, unique=True),
    stranger=metric_names,
)
def test_a_metric_no_dbirth_declared_can_never_be_published(names, stranger):
    session = session_with(names)
    session.connect()
    session.node_birth()
    session.device_birth("portal-03")
    if stranger in names:
        session.device_data("portal-03", {stranger: 1.0})
        return
    with pytest.raises(KeyError):
        session.device_data("portal-03", {stranger: 1.0})


# ---------------------------------------------------------------- the EPC filter


@settings(max_examples=200, deadline=None)
@given(prefix=st.text(alphabet=st.sampled_from(HEX), min_size=1, max_size=24), epc=epcs)
def test_a_non_empty_prefix_admits_exactly_the_epcs_that_start_with_it(prefix, epc):
    assert EpcPrefixFilter(prefix).matches(epc) is epc.startswith(prefix)


@settings(max_examples=200, deadline=None)
@given(whitespace=st.text(alphabet=" \t\r\n", max_size=6))
def test_no_spelling_of_an_empty_prefix_is_accepted(whitespace):
    with pytest.raises(ValueError, match="empty"):
        EpcPrefixFilter(whitespace)


# ---------------------------------------------------------------- accumulation


@settings(max_examples=200, deadline=None)
@given(
    reads=st.lists(
        st.tuples(
            epcs, st.integers(min_value=1, max_value=4), st.integers(min_value=1, max_value=9)
        ),
        min_size=1,
        max_size=40,
    ),
    cap=st.integers(min_value=1, max_value=8),
)
def test_the_accumulator_never_tracks_more_epcs_than_its_cap(reads, cap):
    acc = InventoryAccumulator(max_epcs=cap)
    for epc, antenna, count in reads:
        acc.offer(
            TagRead(
                epc=epc,
                sim_ts=SimInstant(0),
                antenna_port=antenna,
                rssi_dbm=-55,
                phase_deg=0.0,
                read_count=count,
            )
        )
    assert len({aggregate.epc for aggregate in acc.aggregates()}) <= cap


@settings(max_examples=200, deadline=None)
@given(
    reads=st.lists(
        st.tuples(
            st.integers(min_value=-70, max_value=-40), st.integers(min_value=1, max_value=400)
        ),
        min_size=1,
        max_size=30,
    )
)
def test_the_weighted_mean_stays_between_the_extremes_it_reports(reads):
    acc = InventoryAccumulator(max_epcs=4)
    for rssi, count in reads:
        acc.offer(
            TagRead(
                epc="E" * 24,
                sim_ts=SimInstant(0),
                antenna_port=1,
                rssi_dbm=rssi,
                phase_deg=0.0,
                read_count=count,
            )
        )
    aggregate = acc.aggregates()[0]
    assert aggregate.rssi_min_dbm <= aggregate.rssi_mean_dbm <= aggregate.rssi_max_dbm
    assert aggregate.read_count == sum(count for _, count in reads)


# ------------------------------------------------------------------- UNS paths


@settings(max_examples=200, deadline=None)
@given(
    enterprise=identifiers,
    site=identifiers,
    area=identifiers,
    line=identifiers,
    equipment=identifiers,
    parameter=parameters,
)
def test_a_uns_path_round_trips_through_its_topic_and_its_sparkplug_identifiers(
    enterprise, site, area, line, equipment, parameter
):
    path = UnsPath(
        enterprise=enterprise,
        site=site,
        area=area,
        line=line,
        equipment=equipment,
        parameter=parameter,
    )
    assert UnsPath.parse(path.topic) == path
    ids = SparkplugIds.for_path(path)
    assert ids.to_uns_path(path.parameter) == path
    assert not ({"+", "#", "/"} & set(ids.group_id))
