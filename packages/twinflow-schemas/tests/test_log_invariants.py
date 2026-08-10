"""Gates ENV-001 and DET-001, stated over a log rather than over one event."""

from __future__ import annotations

from twinflow.schemas import Envelope, check_log_invariants, compare_runs, in_total_order, log_hash


def _event(*, seq, producer="sim", sim_ts="0", event_id=None, type_="twinflow.twin.scanned"):
    return Envelope(
        specversion="1.0",
        id=event_id or f"{producer}-{seq}",
        source="/twinflow/sim/receiving",
        type=type_,
        time="2026-08-09T00:00:00Z",
        datacontenttype="application/json",
        dataschema="twinflow:schemas/twin/scanned/v1.0.json",
        twinflowsimts=sim_ts,
        twinflowrunid="run_01",
        twinflowproducerid=producer,
        twinflowseq=str(seq),
        data={},
    )


def _run(count=4, producer="sim"):
    return [_event(seq=i, sim_ts=str(i * 10), producer=producer) for i in range(count)]


def test_a_clean_log_has_no_violations():
    assert check_log_invariants(_run()) == []


def test_an_empty_log_is_valid():
    """A run that produced nothing produced nothing.

    Reporting that as a violation would fire the gate on every scenario that
    has not started yet.
    """
    assert check_log_invariants([]) == []


def test_a_gap_in_the_sequence_fails():
    """An event dropped between producer and log."""
    events = [_event(seq=0, sim_ts="0"), _event(seq=2, sim_ts="20")]
    rules = {v.rule for v in check_log_invariants(events)}
    assert "ENV-001-not-dense" in rules


def test_a_repeated_sequence_number_fails():
    events = [
        _event(seq=0, sim_ts="0", event_id="a"),
        _event(seq=1, sim_ts="10", event_id="b"),
        _event(seq=1, sim_ts="20", event_id="c"),
    ]
    rules = {v.rule for v in check_log_invariants(events)}
    assert "ENV-001-not-dense" in rules


def test_a_duplicate_event_id_fails():
    """A replay would count the event twice."""
    events = [
        _event(seq=0, sim_ts="0", event_id="same"),
        _event(seq=1, sim_ts="10", event_id="same"),
    ]
    violations = check_log_invariants(events)
    assert "ENV-001-duplicate-id" in {v.rule for v in violations}


def test_a_tie_in_the_ordering_key_fails():
    """Two events claiming one position leave the order undefined.

    Two readers replaying the same log can then disagree about what happened,
    which is the failure the total order exists to prevent.
    """
    events = [
        _event(seq=0, sim_ts="10", producer="sim", event_id="a"),
        _event(seq=0, sim_ts="10", producer="sim", event_id="b"),
    ]
    assert "ENV-001-tie" in {v.rule for v in check_log_invariants(events)}


def test_two_producers_each_carry_their_own_dense_sequence():
    """D-07. The sequence is dense per producer, never globally.

    A global counter has no allocator once several containers append to one log.
    """
    events = _run(3, producer="sim") + [
        _event(seq=i, sim_ts=str(i * 10 + 5), producer="agent") for i in range(3)
    ]
    assert check_log_invariants(events) == []


def test_the_total_order_is_sim_time_then_producer_then_sequence():
    events = [
        _event(seq=1, sim_ts="10", producer="sim", event_id="a"),
        _event(seq=0, sim_ts="10", producer="agent", event_id="b"),
        _event(seq=0, sim_ts="5", producer="sim", event_id="c"),
    ]
    assert [e.id for e in in_total_order(events)] == ["c", "b", "a"]


# --- DET-001 -----------------------------------------------------------------


def test_two_identical_runs_hash_the_same():
    assert log_hash(_run()) == log_hash(_run())


def test_the_hash_does_not_depend_on_the_order_events_arrive_in():
    """The hash is over the canonical order, so a reader that collected events
    in a different order still recognises the same run.
    """
    forward = _run()
    assert log_hash(forward) == log_hash(list(reversed(forward)))


def test_a_changed_payload_changes_the_hash():
    changed = _run()
    changed[2] = _event(seq=2, sim_ts="20", type_="twinflow.twin.diverted")
    assert log_hash(changed) != log_hash(_run())


def test_identical_runs_compare_with_no_findings():
    assert compare_runs(_run(), _run()) == []


def test_a_divergence_names_where_rather_than_only_that():
    """ "The logs differ" is not something anybody can act on."""
    changed = _run()
    changed[2] = _event(seq=2, sim_ts="20", type_="twinflow.twin.diverted")
    findings = compare_runs(_run(), changed)
    assert findings
    assert "position 2" in findings[0]
    assert "twinflow.twin.diverted" in findings[0]


def test_a_run_that_lost_an_event_reports_the_count():
    findings = compare_runs(_run(4), _run(3))
    assert any("event count differs" in f for f in findings)
