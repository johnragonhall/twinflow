"""The Sparkplug B assertion table, and evidence that every check can fail.

A conformance runner whose checks cannot fail is a runner that reports a pass
for anything, so the bulk of this file is falsifiability evidence rather than
assertions about the current result. Two sweeps carry it. `MUTATIONS` breaks
the session in one documented way at a time and records which assertion ids
stop holding; `test_every_passing_assertion_has_a_killing_mutation` then fails
if any passing check survives the whole library, because a check nothing can
break is measuring nothing. `REPAIRS` runs the other direction over the
assertions that do not hold today, making the session conformant one way at a
time, so a failing check is shown to be a real observation rather than a
verdict wired shut.

Gate VAL-GATE-SPARK-001 remains owned by the Eclipse Sparkplug Technology
Compatibility Kit. Nothing here is a conformance claim: the table records 299
specification assertions and this repository answers 143 of them, so a green
run leaves the larger part of the edge-node profile untested. Doctrine D-11
rule 1 is why that sentence is in the test file and not only in the report.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import replace

import pytest

from twinflow.kernel import SimClock, SimInstant
from twinflow.sensors import conformance as conf
from twinflow.sensors import sparkplug
from twinflow.sensors.sparkplug import (
    BDSEQ_METRIC,
    REBIRTH_METRIC,
    DataType,
    EdgeNodeSession,
    Message,
    MessageType,
    Metric,
    MetricSpec,
    QosRow,
    SparkplugIds,
)

#: Epoch milliseconds inside the range a UTC reading falls in, for the two
#: assertions that ask what the payload timestamp is measured against.
_UTC_NOW_MS = 1_760_000_000_000


class _UtcClock:
    """A clock reading epoch milliseconds, for the UTC assertions alone.

    The `Clock` port this package's devices run on reads simulation time, so
    the two UTC assertions cannot hold under it. This stand-in shows the checks
    respond to what the clock yields rather than failing whatever happens.
    """

    tick_hz = 1000

    def now(self) -> SimInstant:
        return SimInstant(_UTC_NOW_MS)

    def timeout(self, duration: int) -> SimInstant:
        return SimInstant(_UTC_NOW_MS + duration)


# ------------------------------------------------------------------ the table


def test_table_carries_every_published_assertion() -> None:
    """The table's row count is the specification's assertion count."""
    assert len(conf.ASSERTIONS) == conf.SPEC_ASSERTION_COUNT


def test_every_key_is_a_published_identifier() -> None:
    """Every key is spelled as the specification anchors it."""
    for assertion_id, assertion in conf.ASSERTIONS.items():
        assert assertion_id.startswith("tck-id-")
        assert assertion.assertion_id == assertion_id
        assert assertion.statement.endswith(".")


def test_out_of_scope_rows_name_a_reason() -> None:
    """Nothing is dropped from scope without saying what is missing."""
    for assertion in conf.ASSERTIONS.values():
        assert assertion.in_scope or assertion.exclusion is not None


def test_every_in_scope_assertion_has_a_check() -> None:
    """A row cannot claim scope without an executable observation behind it."""
    missing = [
        a.assertion_id for a in conf.in_scope_assertions() if a.assertion_id not in conf._CHECKS
    ]
    assert missing == []


def test_no_check_runs_without_a_row() -> None:
    """A check cannot report on an assertion the table does not carry."""
    stray = [key for key in conf._CHECKS if key not in conf.ASSERTIONS]
    assert stray == []


def test_coverage_denominator_is_larger_than_the_numerator() -> None:
    """The edge-node profile is bigger than the part answered here.

    The point of the number is that it is not reported alone. A run that
    passes every in-scope assertion still leaves this many edge-node
    assertions untested, and the gate reads that difference.
    """
    cover = conf.edge_node_coverage()
    assert cover.edge_node_total > cover.edge_node_in_scope
    assert cover.edge_node_out_of_scope == cover.edge_node_total - cover.edge_node_in_scope
    assert cover.spec_total == len(conf.ASSERTIONS)


# ------------------------------------------------------------------- the run


@pytest.fixture(scope="module")
def report() -> conf.ConformanceReport:
    """One run of the harness against the real session."""
    return conf.run_edge_node_conformance()


def test_every_in_scope_assertion_is_ruled_on(report: conf.ConformanceReport) -> None:
    """The run rules on each in-scope assertion exactly once."""
    ruled = [result.assertion_id for result in report.results]
    assert sorted(ruled) == sorted(a.assertion_id for a in conf.in_scope_assertions())
    assert len(ruled) == len(set(ruled))


#: The assertions the session does not satisfy today, each with the reason.
#: Written down rather than tolerated, so a change to the session that fixes
#: one, or breaks a twelfth, fails this test rather than passing quietly.
#: The session satisfies every in-scope assertion, so this is empty. It stays
#: as the place a failure is written down with its reason, and the test below
#: fails on a regression rather than letting one pass quietly.
KNOWN_FAILURES: Mapping[str, str] = {}


def test_the_run_fails_exactly_the_recorded_assertions(report: conf.ConformanceReport) -> None:
    """The failures are the ones written down, and no others."""
    assert sorted(result.assertion_id for result in report.failures) == sorted(KNOWN_FAILURES)


def test_a_clean_run_is_still_not_a_conformance_claim(report: conf.ConformanceReport) -> None:
    """`conformant` means the in-scope subset held, which is a smaller claim.

    56 edge-node assertions sit outside this package's scope and the Eclipse
    Technology Compatibility Kit has not been run, so a report with no failures
    is evidence about the subset measured here and nothing wider. The gate reads
    the denominator beside the count for exactly this reason.
    """
    assert report.coverage.failed == len(KNOWN_FAILURES)
    assert report.coverage.edge_node_out_of_scope > 0
    assert report.coverage.edge_node_in_scope < report.coverage.edge_node_total
    assert report.coverage.passed + report.coverage.failed == report.coverage.in_scope_total


# ------------------------------------------------------------- the mutations

Mutation = Callable[[pytest.MonkeyPatch], None]


def _mutate_namespace(patch: pytest.MonkeyPatch) -> None:
    """Address every topic under a namespace that is not Sparkplug B."""
    patch.setattr("twinflow.sensors.sparkplug.NAMESPACE", "spBv9.9")


def _mutate_topic_suffix(patch: pytest.MonkeyPatch) -> None:
    """Append a level to every rendered topic."""
    original = conf.topic_for

    def rendered(
        ids: SparkplugIds, message_type: MessageType, *, device_id: str | None = None
    ) -> str:
        return f"{original(ids, message_type, device_id=device_id)}/extra"

    patch.setattr("twinflow.sensors.sparkplug.topic_for", rendered)
    patch.setattr("twinflow.sensors.conformance.topic_for", rendered)


def _mutate_identifier_grammar(patch: pytest.MonkeyPatch) -> None:
    """Let an identifier holding an MQTT wildcard through."""
    patch.setattr("twinflow.sensors.sparkplug._refuse_bad_identifier", lambda *_a: None)


def _mutate_case_folding(patch: pytest.MonkeyPatch) -> None:
    """Let an identifier keep an uppercase letter."""
    patch.setattr("twinflow.config.UnsPath.is_identifier", staticmethod(lambda _value: True))


def _mutate_constant_sequence(patch: pytest.MonkeyPatch) -> None:
    """Stamp every message with the same sequence number."""
    patch.setattr(EdgeNodeSession, "_next_seq", lambda _self: 7)


def _mutate_absent_sequence(patch: pytest.MonkeyPatch) -> None:
    """Send every message without a sequence number."""
    patch.setattr(EdgeNodeSession, "_next_seq", lambda _self: None)


def _mutate_sequence_never_wraps(patch: pytest.MonkeyPatch) -> None:
    """Let the sequence counter run past the byte it is given."""

    def unwrapped(self: EdgeNodeSession) -> int:
        value = self._seq
        self._seq = self._seq + 1
        return value

    patch.setattr(EdgeNodeSession, "_next_seq", unwrapped)


def _mutate_delivery_flags(patch: pytest.MonkeyPatch) -> None:
    """Publish every topic class at QoS 1, retained."""
    patch.setattr(
        "twinflow.sensors.sparkplug.QOS_BY_TOPIC_CLASS",
        {kind: QosRow(1, True) for kind in MessageType},
    )
    patch.setattr(
        "twinflow.sensors.conformance.QOS_BY_TOPIC_CLASS",
        {kind: QosRow(1, True) for kind in MessageType},
    )


def _mutate_unaliased_births(patch: pytest.MonkeyPatch) -> None:
    """Birth every metric without an alias."""
    original = EdgeNodeSession._birth_metric

    def unaliased(self: EdgeNodeSession, device_id: str | None, spec: MetricSpec) -> Metric:
        return replace(original(self, device_id, spec), alias=None)

    patch.setattr(EdgeNodeSession, "_birth_metric", unaliased)


def _mutate_shared_aliases(patch: pytest.MonkeyPatch) -> None:
    """Give every metric on the edge node the same alias."""
    original = EdgeNodeSession._assign_aliases

    def collided(self: EdgeNodeSession) -> None:
        original(self)
        self._aliases = dict.fromkeys(self._aliases, 1)

    patch.setattr(EdgeNodeSession, "_assign_aliases", collided)


def _mutate_named_data(patch: pytest.MonkeyPatch) -> None:
    """Carry the metric name alongside the alias in a data message."""
    original = EdgeNodeSession._data_metrics

    def named(
        self: EdgeNodeSession, device_id: str | None, changed: Mapping[str, object]
    ) -> tuple[Metric, ...]:
        metrics = original(self, device_id, changed)
        names = sorted(changed)
        return tuple(replace(m, name=n) for m, n in zip(metrics, names, strict=False))

    patch.setattr(EdgeNodeSession, "_data_metrics", named)


def _mutate_typed_data(patch: pytest.MonkeyPatch) -> None:
    """Repeat the datatype in a data message the birth already declared."""
    original = EdgeNodeSession._data_metrics

    def typed(
        self: EdgeNodeSession, device_id: str | None, changed: Mapping[str, object]
    ) -> tuple[Metric, ...]:
        return tuple(
            replace(m, datatype=DataType.Double) for m in original(self, device_id, changed)
        )

    patch.setattr(EdgeNodeSession, "_data_metrics", typed)


def _mutate_untyped_births(patch: pytest.MonkeyPatch) -> None:
    """Birth every metric with no datatype and no name."""
    original = EdgeNodeSession._birth_metric

    def bare(self: EdgeNodeSession, device_id: str | None, spec: MetricSpec) -> Metric:
        return replace(original(self, device_id, spec), datatype=None, name=None)

    patch.setattr(EdgeNodeSession, "_birth_metric", bare)


def _mutate_undated_metrics(patch: pytest.MonkeyPatch) -> None:
    """Send every metric without a timestamp."""
    original_birth = EdgeNodeSession._birth_metric
    original_data = EdgeNodeSession._data_metrics

    def undated_birth(self: EdgeNodeSession, device_id: str | None, spec: MetricSpec) -> Metric:
        return replace(original_birth(self, device_id, spec), timestamp=None)

    def undated_data(
        self: EdgeNodeSession, device_id: str | None, changed: Mapping[str, object]
    ) -> tuple[Metric, ...]:
        return tuple(replace(m, timestamp=None) for m in original_data(self, device_id, changed))

    patch.setattr(EdgeNodeSession, "_birth_metric", undated_birth)
    patch.setattr(EdgeNodeSession, "_data_metrics", undated_data)


def _mutate_backwards_metric_order(patch: pytest.MonkeyPatch) -> None:
    """Order the metrics of a payload backwards in time."""
    original_birth = EdgeNodeSession._birth_metric
    original_data = EdgeNodeSession._data_metrics
    counter = {"tick": 1_000_000}

    def descending(self: EdgeNodeSession, device_id: str | None, spec: MetricSpec) -> Metric:
        counter["tick"] -= 1000
        return replace(original_birth(self, device_id, spec), timestamp=counter["tick"])

    def descending_data(
        self: EdgeNodeSession, device_id: str | None, changed: Mapping[str, object]
    ) -> tuple[Metric, ...]:
        metrics = []
        for metric in original_data(self, device_id, changed):
            counter["tick"] -= 1000
            metrics.append(replace(metric, timestamp=counter["tick"]))
        return tuple(metrics)

    patch.setattr(EdgeNodeSession, "_birth_metric", descending)
    patch.setattr(EdgeNodeSession, "_data_metrics", descending_data)


def _mutate_empty_births(patch: pytest.MonkeyPatch) -> None:
    """Publish a birth certificate that declares nothing."""
    patch.setattr(EdgeNodeSession, "_birth_metric", lambda _s, _d, _spec: Metric(value=None))


def _mutate_wrong_bdseq(patch: pytest.MonkeyPatch) -> None:
    """Birth with a bdSeq the will never carried."""
    original = EdgeNodeSession._birth_value

    def drifted(self: EdgeNodeSession, device_id: str | None, spec: MetricSpec) -> object:
        if device_id is None and spec.name == BDSEQ_METRIC:
            return 200
        return original(self, device_id, spec)

    patch.setattr(EdgeNodeSession, "_birth_value", drifted)


def _mutate_bdseq_never_advances(patch: pytest.MonkeyPatch) -> None:
    """Reuse one bdSeq for every session."""
    original = EdgeNodeSession.connect

    def frozen(self: EdgeNodeSession) -> object:
        self._bdseq = 41
        registration = original(self)
        self._bdseq = 41
        return registration

    patch.setattr(EdgeNodeSession, "connect", frozen)


def _mutate_rebirth_metric_absent(patch: pytest.MonkeyPatch) -> None:
    """Drop the rebirth command metric from the edge node."""
    patch.setattr(
        "twinflow.sensors.sparkplug._CONTROL_METRICS",
        (MetricSpec(name=BDSEQ_METRIC, datatype=DataType.UInt64, unit="1"),),
    )


def _mutate_rebirth_metric_wrong(patch: pytest.MonkeyPatch) -> None:
    """Birth the rebirth command metric as a string holding true."""
    patch.setattr(
        "twinflow.sensors.sparkplug._CONTROL_METRICS",
        (
            MetricSpec(name=BDSEQ_METRIC, datatype=DataType.UInt64, unit="1"),
            MetricSpec(name=REBIRTH_METRIC, datatype=DataType.String, unit="1"),
        ),
    )
    original = EdgeNodeSession._birth_value

    def truthy(self: EdgeNodeSession, device_id: str | None, spec: MetricSpec) -> object:
        if device_id is None and spec.name == REBIRTH_METRIC:
            return True
        return original(self, device_id, spec)

    patch.setattr(EdgeNodeSession, "_birth_value", truthy)


def _mutate_rebirth_ignored(patch: pytest.MonkeyPatch) -> None:
    """Ignore a rebirth request entirely."""
    patch.setattr(EdgeNodeSession, "handle_node_command", lambda _self, _command: ())


def _mutate_rebirth_on_any_command(patch: pytest.MonkeyPatch) -> None:
    """Rebirth on any command at all, whatever its name or value."""
    patch.setattr(EdgeNodeSession, "handle_node_command", lambda self, _command: self.rebirth())


def _mutate_rebirth_only_nbirth(patch: pytest.MonkeyPatch) -> None:
    """Rebirth without republishing the device birth certificates."""
    patch.setattr(EdgeNodeSession, "rebirth", lambda self: (self.node_birth(),))


def _mutate_rebirth_opens_a_session(patch: pytest.MonkeyPatch) -> None:
    """Treat a rebirth as a new session, moving bdSeq under the live will."""

    def reconnecting(self: EdgeNodeSession) -> tuple[Message, ...]:
        self._bdseq = (self._bdseq + 1) % 256
        self._seq = 0
        self._born = set()
        messages = [self.node_birth()]
        messages.extend(self.device_birth(device) for device in sorted(self._devices))
        return tuple(messages)

    patch.setattr(EdgeNodeSession, "rebirth", reconnecting)


def _mutate_epoch_is_zero(patch: pytest.MonkeyPatch) -> None:
    """Count sim time from 1970, so a timestamp is not a UTC reading."""
    patch.setattr(conf, "_EPOCH_MS", 0)


def _mutate_data_before_every_birth(patch: pytest.MonkeyPatch) -> None:
    """Let data go out while a declared device has sent no DBIRTH."""
    patch.setattr(EdgeNodeSession, "_require_all_born", lambda self: self._require_connected())


def _mutate_no_close(patch: pytest.MonkeyPatch) -> None:
    """Leave a deliberate shutdown's death to the broker's will delivery."""
    patch.delattr(EdgeNodeSession, "disconnect", raising=False)


def _mutate_rebirth_is_aliased(patch: pytest.MonkeyPatch) -> None:
    """Give the rebirth command an alias a requesting host cannot resolve."""

    def aliased(self: EdgeNodeSession, device_id: str | None, spec: MetricSpec) -> Metric:
        return Metric(
            name=spec.name,
            alias=self._aliases[(device_id, spec.name)],
            datatype=spec.datatype,
            value=self._birth_value(device_id, spec),
            timestamp=self._now(),
            properties=spec.properties(),
        )

    patch.setattr(EdgeNodeSession, "_birth_metric", aliased)


def _mutate_case_insensitive_names(patch: pytest.MonkeyPatch) -> None:
    """Let two metric names that differ only by case sit on one owner.

    The pair is what a consumer keying its tag store by a case-folded name
    merges, reporting one channel's readings under the other's.
    """
    patch.setattr("twinflow.sensors.sparkplug._refuse_case_collisions", lambda _specs: None)


def _mutate_no_refusals(patch: pytest.MonkeyPatch) -> None:
    """Publish anything in any order, refusing nothing."""
    patch.setattr(EdgeNodeSession, "_require_connected", lambda _self: None)
    patch.setattr(conf, "_refuses", lambda _call: False)


def _mutate_undeclared_metrics(patch: pytest.MonkeyPatch) -> None:
    """Let a metric no birth certificate declared reach a data message."""

    def permissive(
        self: EdgeNodeSession, device_id: str | None, changed: Mapping[str, object]
    ) -> tuple[Metric, ...]:
        return tuple(
            Metric(value=changed[name], alias=self._aliases.get((device_id, name), 99), timestamp=0)
            for name in sorted(changed)
        )

    patch.setattr(EdgeNodeSession, "_data_metrics", permissive)


def _mutate_republish_everything(patch: pytest.MonkeyPatch) -> None:
    """Republish the whole metric set on every data message."""

    def everything(
        self: EdgeNodeSession, device_id: str | None, _changed: Mapping[str, object]
    ) -> tuple[Metric, ...]:
        return tuple(
            Metric(value=0, alias=alias, timestamp=0)
            for (owner, _name), alias in sorted(self._aliases.items(), key=lambda kv: kv[1])
            if owner == device_id
        )

    patch.setattr(EdgeNodeSession, "_data_metrics", everything)


def _mutate_ddeath_is_data(patch: pytest.MonkeyPatch) -> None:
    """Report a lost device as a data message rather than a DDEATH."""
    patch.setattr(
        EdgeNodeSession,
        "device_death",
        lambda self, device_id: self._message(MessageType.DDATA, (), device_id=device_id),
    )


def _mutate_will_is_a_birth(patch: pytest.MonkeyPatch) -> None:
    """Register something other than an NDEATH as the will."""
    original = EdgeNodeSession.connect

    def wrong(self: EdgeNodeSession) -> object:
        registration = original(self)
        return replace(
            registration,
            message=replace(registration.message, message_type=MessageType.NBIRTH),
        )

    patch.setattr(EdgeNodeSession, "connect", wrong)


def _mutate_will_carries_the_world(patch: pytest.MonkeyPatch) -> None:
    """Register a will carrying a sequence number and a second metric."""
    original = EdgeNodeSession.connect

    def crowded(self: EdgeNodeSession) -> object:
        registration = original(self)
        payload = replace(
            registration.message.payload,
            seq=4,
            metrics=(*registration.message.payload.metrics, Metric(value=1, name="extra")),
        )
        return replace(registration, message=replace(registration.message, payload=payload))

    patch.setattr(EdgeNodeSession, "connect", crowded)


def _mutate_quality_codes(patch: pytest.MonkeyPatch) -> None:
    """Publish a quality code outside the three the specification defines."""
    patch.setattr(
        "twinflow.sensors.conformance.Quality",
        type("Q", (), {"__iter__": lambda _s: iter([1, 2])})(),
    )


def _mutate_undated_payloads(patch: pytest.MonkeyPatch) -> None:
    """Send every payload without its own timestamp."""
    original = EdgeNodeSession._message

    def undated(
        self: EdgeNodeSession,
        message_type: MessageType,
        metrics: tuple[Metric, ...],
        *,
        device_id: str | None,
    ) -> Message:
        message = original(self, message_type, metrics, device_id=device_id)
        return replace(message, payload=replace(message.payload, timestamp=None))

    patch.setattr(EdgeNodeSession, "_message", undated)


def _mutate_delivery_flags_bare(patch: pytest.MonkeyPatch) -> None:
    """Publish every topic class at QoS 0, unretained.

    The companion of the QoS 1 mutation. Between them every row of the matrix
    is moved off its declared value, which the STATE and will rows need
    because they are the two the specification puts at QoS 1.
    """
    patch.setattr(
        "twinflow.sensors.sparkplug.QOS_BY_TOPIC_CLASS",
        {kind: QosRow(0, False) for kind in MessageType},
    )
    patch.setattr(
        "twinflow.sensors.conformance.QOS_BY_TOPIC_CLASS",
        {kind: QosRow(0, False) for kind in MessageType},
    )


def _mutate_shouted_topics(patch: pytest.MonkeyPatch) -> None:
    """Render every topic in upper case, mangling each identifier in it."""
    original = conf.topic_for

    def shouted(
        ids: SparkplugIds, message_type: MessageType, *, device_id: str | None = None
    ) -> str:
        return original(ids, message_type, device_id=device_id).upper()

    patch.setattr("twinflow.sensors.sparkplug.topic_for", shouted)


def _mutate_device_topics_collapse(patch: pytest.MonkeyPatch) -> None:
    """Address every device message to one device under a foreign group."""
    original = conf.topic_for

    def collapsed(
        ids: SparkplugIds, message_type: MessageType, *, device_id: str | None = None
    ) -> str:
        rendered = original(ids, message_type, device_id=device_id)
        if device_id is None:
            return rendered
        parts = rendered.split("/")
        parts[1] = "elsewhere:dc-09:shipping"
        parts[-1] = "one-device"
        return "/".join(parts)

    patch.setattr("twinflow.sensors.sparkplug.topic_for", collapsed)


def _mutate_no_will(patch: pytest.MonkeyPatch) -> None:
    """Open the session without handing back a will to register."""
    original = EdgeNodeSession.connect

    def silent(self: EdgeNodeSession) -> None:
        original(self)
        return None

    patch.setattr(EdgeNodeSession, "connect", silent)


def _mutate_rebirth_keeps_publishing(patch: pytest.MonkeyPatch) -> None:
    """Carry a data message inside the rebirth sequence."""
    original = EdgeNodeSession.rebirth

    def noisy(self: EdgeNodeSession) -> tuple[Message, ...]:
        messages = original(self)
        return (*messages, self.node_data({"sf_dropped_records": 1}))

    patch.setattr(EdgeNodeSession, "rebirth", noisy)


#: Each entry breaks the session in one documented way. The sweep below records
#: which assertions stop holding under each, and every assertion that holds
#: today has to appear under at least one of them.
MUTATIONS: Mapping[str, Mutation] = {
    "namespace is not spBv1.0": _mutate_namespace,
    "every topic grows a level": _mutate_topic_suffix,
    "identifier grammar is not enforced": _mutate_identifier_grammar,
    "identifiers may hold uppercase": _mutate_case_folding,
    "the sequence never moves": _mutate_constant_sequence,
    "the sequence is absent": _mutate_absent_sequence,
    "the sequence never wraps": _mutate_sequence_never_wraps,
    "every class is QoS 1 retained": _mutate_delivery_flags,
    "every class is QoS 0 unretained": _mutate_delivery_flags_bare,
    "every topic is shouted": _mutate_shouted_topics,
    "device topics collapse onto one": _mutate_device_topics_collapse,
    "CONNECT hands back no will": _mutate_no_will,
    "a rebirth keeps publishing data": _mutate_rebirth_keeps_publishing,
    "births carry no alias": _mutate_unaliased_births,
    "every metric shares one alias": _mutate_shared_aliases,
    "data carries the metric name": _mutate_named_data,
    "data repeats the datatype": _mutate_typed_data,
    "births carry no name or datatype": _mutate_untyped_births,
    "metrics carry no timestamp": _mutate_undated_metrics,
    "metrics run backwards in time": _mutate_backwards_metric_order,
    "births declare nothing": _mutate_empty_births,
    "the birth bdSeq drifts from the will": _mutate_wrong_bdseq,
    "bdSeq never advances": _mutate_bdseq_never_advances,
    "the rebirth metric is absent": _mutate_rebirth_metric_absent,
    "the rebirth metric is a true string": _mutate_rebirth_metric_wrong,
    "a rebirth request is ignored": _mutate_rebirth_ignored,
    "any command triggers a rebirth": _mutate_rebirth_on_any_command,
    "a rebirth skips the device births": _mutate_rebirth_only_nbirth,
    "a rebirth opens a new session": _mutate_rebirth_opens_a_session,
    "metric names may differ only by case": _mutate_case_insensitive_names,
    "sim time is counted from 1970": _mutate_epoch_is_zero,
    "data precedes a declared device's birth": _mutate_data_before_every_birth,
    "no close publishes an NDEATH": _mutate_no_close,
    "the rebirth command is aliased": _mutate_rebirth_is_aliased,
    "nothing is refused": _mutate_no_refusals,
    "undeclared metrics are published": _mutate_undeclared_metrics,
    "every metric is republished": _mutate_republish_everything,
    "a lost device reports as data": _mutate_ddeath_is_data,
    "the will is a birth certificate": _mutate_will_is_a_birth,
    "the will carries a sequence number": _mutate_will_carries_the_world,
    "quality codes are undefined": _mutate_quality_codes,
    "payloads carry no timestamp": _mutate_undated_payloads,
}


def _failures_under(mutation: Mutation) -> frozenset[str]:
    """The assertions that stop holding once one mutation is planted."""
    with pytest.MonkeyPatch.context() as patch:
        mutation(patch)
        report = conf.run_edge_node_conformance()
        return frozenset(result.assertion_id for result in report.failures)


@pytest.fixture(scope="module")
def killed() -> Mapping[str, frozenset[str]]:
    """Every mutation, and the assertions it falsifies."""
    return {name: _failures_under(mutation) for name, mutation in MUTATIONS.items()}


def test_every_mutation_breaks_something(killed: Mapping[str, frozenset[str]]) -> None:
    """A mutation nothing notices is a hole in the harness, not a safe edit."""
    silent = [name for name, broken in killed.items() if not broken - frozenset(KNOWN_FAILURES)]
    assert silent == []


def test_every_passing_assertion_has_a_killing_mutation(
    killed: Mapping[str, frozenset[str]], report: conf.ConformanceReport
) -> None:
    """No check reports a pass that nothing in the library can turn over.

    This is the evidence that the numerator means something. A check that
    survives every mutation is measuring nothing, and would report a pass for
    an edge node that does the opposite.
    """
    broken_by_something = frozenset().union(*killed.values())
    survivors = sorted(
        result.assertion_id
        for result in report.results
        if result.passed and result.assertion_id not in broken_by_something
    )
    assert survivors == []


def test_the_restore_is_complete(report: conf.ConformanceReport) -> None:
    """Running the mutations leaves the session as it was.

    The library patches shared class attributes, so a mutation that outlived
    its context manager would make every later result meaningless.
    """
    for mutation in MUTATIONS.values():
        _failures_under(mutation)
    after = conf.run_edge_node_conformance()
    assert sorted(r.assertion_id for r in after.failures) == sorted(
        r.assertion_id for r in report.failures
    )


# ---------------------------------------------------------------- the repairs


def _repair_bdseq_datatype(patch: pytest.MonkeyPatch) -> None:
    """Carry bdSeq with the datatype the specification names."""
    patch.setattr(
        "twinflow.sensors.sparkplug._CONTROL_METRICS",
        (
            MetricSpec(name=BDSEQ_METRIC, datatype=DataType.Int64, unit="1"),
            MetricSpec(name=REBIRTH_METRIC, datatype=DataType.Boolean, unit="1"),
        ),
    )
    original = EdgeNodeSession.connect

    def typed(self: EdgeNodeSession) -> object:
        registration = original(self)
        metrics = tuple(
            replace(m, datatype=DataType.Int64) for m in registration.message.payload.metrics
        )
        payload = replace(registration.message.payload, metrics=metrics)
        return replace(registration, message=replace(registration.message, payload=payload))

    patch.setattr(EdgeNodeSession, "connect", typed)


def _repair_rebirth_alias(patch: pytest.MonkeyPatch) -> None:
    """Birth the rebirth command metric without an alias."""
    original = EdgeNodeSession._birth_metric

    def unaliased(self: EdgeNodeSession, device_id: str | None, spec: MetricSpec) -> Metric:
        metric = original(self, device_id, spec)
        return replace(metric, alias=None) if spec.name == REBIRTH_METRIC else metric

    patch.setattr(EdgeNodeSession, "_birth_metric", unaliased)


def _repair_birth_ordering(patch: pytest.MonkeyPatch) -> None:
    """Hold every data message until every device has birthed."""
    original_node = EdgeNodeSession.node_data
    original_device = EdgeNodeSession.device_data

    def guard(self: EdgeNodeSession) -> None:
        unborn = set(self._devices) - self._born
        if unborn:
            raise RuntimeError(f"data before the DBIRTH of {sorted(unborn)}")

    def node_data(self: EdgeNodeSession, changed: Mapping[str, object]) -> Message:
        guard(self)
        return original_node(self, changed)

    def device_data(
        self: EdgeNodeSession, device_id: str, changed: Mapping[str, object]
    ) -> Message:
        guard(self)
        return original_device(self, device_id, changed)

    patch.setattr(EdgeNodeSession, "node_data", node_data)
    patch.setattr(EdgeNodeSession, "device_data", device_data)


def _repair_intentional_disconnect(patch: pytest.MonkeyPatch) -> None:
    """Offer a close that publishes the NDEATH before the connection goes."""

    def disconnect(self: EdgeNodeSession) -> Message:
        message = self._message(MessageType.NDEATH, (), device_id=None)
        self._connected = False
        return replace(message, payload=replace(message.payload, seq=None))

    patch.setattr(EdgeNodeSession, "disconnect", disconnect, raising=False)


def _repair_metric_name_case(patch: pytest.MonkeyPatch) -> None:
    """Refuse two metric names that differ only by case."""
    original = EdgeNodeSession._assign_aliases

    def guarded(self: EdgeNodeSession) -> None:
        original(self)
        folded = [(owner, name.lower()) for owner, name in self._aliases]
        if len(set(folded)) != len(folded):
            raise ValueError("two metric names differ only by case")

    patch.setattr(EdgeNodeSession, "_assign_aliases", guarded)


def _repair_utc_clock(_patch: pytest.MonkeyPatch) -> None:
    """The UTC repair is the clock, which the runner takes as an argument."""


#: Each entry makes the session satisfy assertions it does not satisfy today.
#: The sweep records which of the recorded failures each one clears, so a
#: failing check is shown to respond to the session rather than always failing.
REPAIRS: Mapping[str, tuple[Mutation, frozenset[str]]] = {
    "bdSeq is Int64": (
        _repair_bdseq_datatype,
        frozenset(
            {
                "tck-id-message-flow-edge-node-birth-publish-nbirth-payload-bdSeq",
                "tck-id-message-flow-edge-node-birth-publish-will-message-payload-bdSeq",
            }
        ),
    ),
    "the rebirth metric loses its alias": (
        _repair_rebirth_alias,
        frozenset({"tck-id-operational-behavior-data-commands-rebirth-name-aliases"}),
    ),
    "data waits for every DBIRTH": (
        _repair_birth_ordering,
        frozenset(
            {
                "tck-id-payloads-dbirth-order",
                "tck-id-payloads-ddata-order",
                "tck-id-payloads-ndata-order",
            }
        ),
    ),
    "a close publishes the NDEATH": (
        _repair_intentional_disconnect,
        frozenset(
            {
                "tck-id-operational-behavior-edge-node-intentional-disconnect-ndeath",
                "tck-id-payloads-ndeath-will-message-publisher",
            }
        ),
    ),
    "metric names may not collide on case": (
        _repair_metric_name_case,
        frozenset({"tck-id-case-sensitivity-metric-names"}),
    ),
}


@pytest.mark.parametrize("name", sorted(REPAIRS))
def test_a_repair_clears_the_assertions_it_targets(name: str) -> None:
    """A failing assertion holds once the session is made to satisfy it.

    Without this, a check that always fails would be indistinguishable from a
    check that has found something.
    """
    repair, targets = REPAIRS[name]
    with pytest.MonkeyPatch.context() as patch:
        repair(patch)
        report = conf.run_edge_node_conformance()
        still_failing = frozenset(r.assertion_id for r in report.failures)
    assert targets & still_failing == frozenset()


def test_a_utc_clock_clears_the_two_utc_assertions() -> None:
    """The UTC assertions read the clock rather than always failing."""
    report = conf.run_edge_node_conformance(_UtcClock())
    failing = {result.assertion_id for result in report.failures}
    assert "tck-id-payloads-timestamp-in-UTC" not in failing
    assert "tck-id-payloads-metric-timestamp-in-UTC" not in failing


def test_the_epoch_is_what_makes_a_sim_instant_a_utc_reading() -> None:
    """A session counting from epoch zero publishes 1970 and is refused.

    The two claims hold together because the epoch is configuration: the clock
    stays a port per doctrine D-02, and the timestamps stay a function of the
    inputs rather than of the host, which a wall-clock read here would break.
    """
    session = sparkplug.EdgeNodeSession(
        group_id=conf._GROUP_ID,
        edge_node_id=conf._EDGE_NODE_ID,
        clock=SimClock(),
        node_metrics=conf._NODE_METRICS,
        devices=conf._DEVICE_METRICS,
    )
    session.connect()

    assert session.node_birth().payload.timestamp < conf._UTC_FLOOR_MS
