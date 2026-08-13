"""Behavior of the receiving and putaway station model.

Every test here names the observation that fails it, per doctrine D-12. A test
whose assertion holds for every possible implementation measures nothing, so
each one below is paired with the wrong implementation it rules out.
"""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from twinflow.rng import generator_for
from twinflow.schemas import check_log_invariants, log_hash
from twinflow.twin.station import (
    PALLET_TRANSITIONS,
    RECEIVING_STREAM,
    SERVICE_STREAM,
    DistributionSpec,
    IllegalTransitionError,
    PalletArrival,
    PalletState,
    StationLineSpec,
    StationSpec,
    StationState,
    check_transition,
    run_station_line,
)

EPOCH = datetime(2026, 1, 1, tzinfo=UTC)

#: 1 ms ticks. Small enough that a rounding defect moves a tick, large enough
#: that the numbers in these tests stay readable.
TICK_HZ = 1_000


def _arrivals(count: int, *, gap_ticks: int = 0, qty_units: int = 10) -> tuple[PalletArrival, ...]:
    return tuple(
        PalletArrival(
            pallet_id=f"plt-{index:04d}",
            sku_id="sku-0001",
            qty_units=qty_units,
            release_tick=index * gap_ticks,
        )
        for index in range(count)
    )


def _line(
    *,
    pallets: int = 4,
    gap_ticks: int = 0,
    receiving_capacity: int = 1,
    putaway_capacity: int = 1,
    staging_capacity: int = 8,
    receiving_scale_s: float = 30.0,
    putaway_scale_s: float = 45.0,
) -> StationLineSpec:
    return StationLineSpec(
        line_id="p1-receiving-line",
        tick_hz=TICK_HZ,
        epoch=EPOCH,
        receiving=StationSpec(
            station_id="recv-01",
            kind="receiving",
            zone_id="dock-a",
            capacity=receiving_capacity,
            service_time=DistributionSpec(family="lognormal", scale_s=receiving_scale_s, shape=0.4),
        ),
        putaway=StationSpec(
            station_id="put-01",
            kind="putaway",
            zone_id="storage-a",
            capacity=putaway_capacity,
            service_time=DistributionSpec(family="gamma", scale_s=putaway_scale_s, shape=2.0),
        ),
        staging_capacity=staging_capacity,
        arrivals=_arrivals(pallets, gap_ticks=gap_ticks),
    )


def _payloads(run, event_type: str) -> list[dict]:
    return [event.data for event in run.events if event.type == event_type]


def _intervals(run, activity: str) -> list[tuple[int, int]]:
    """Service intervals in ticks for one activity, from the tape alone."""
    started: dict[str, int] = {}
    spans: list[tuple[int, int]] = []
    for event in run.events:
        if event.data.get("activity") != activity:
            continue
        case_id = event.data["case_id"]
        if event.type == "twinflow.twin.activity_started":
            started[case_id] = int(event.twinflowsimts)
        elif event.type == "twinflow.twin.activity_completed":
            spans.append((started.pop(case_id), int(event.twinflowsimts)))
    return spans


def _overlaps(spans: list[tuple[int, int]]) -> int:
    """Pairs of spans that share at least one tick of open interior."""
    count = 0
    for index, (start, end) in enumerate(spans):
        for other_start, other_end in spans[index + 1 :]:
            if start < other_end and other_start < end:
                count += 1
    return count


def test_a_pallet_walks_the_declared_state_machine() -> None:
    """Fails on a model that stores a pallet it never unloaded.

    The activity spine is the process-mining contract of 4.1, so a run that
    reports a putaway with no matching unload is a run whose event log cannot
    be replayed as a case.
    """
    run = run_station_line(_line(pallets=3), seed=11)

    for arrival in _line(pallets=3).arrivals:
        activities = [
            event.data["activity"]
            for event in run.events
            if event.data.get("case_id") == arrival.pallet_id
            and event.type in ("twinflow.twin.activity_started", "twinflow.twin.activity_completed")
        ]
        assert activities == ["unload", "unload", "putaway", "putaway"], arrival.pallet_id


def test_an_undeclared_pallet_transition_raises() -> None:
    """Fails on a model that logs an illegal transition instead of raising.

    Section 3.2: the state machine is a declared table and an illegal
    transition raises. A model that tolerates UNLOADING to STORED has silently
    dropped the staging leg from the value stream.
    """
    check_transition(PalletState.UNLOADING, PalletState.STAGED)
    with pytest.raises(IllegalTransitionError):
        check_transition(PalletState.UNLOADING, PalletState.STORED)


def test_the_transition_table_is_a_connected_path_from_expected_to_stored() -> None:
    """Fails on a table with an unreachable state or a dangling edge."""
    reachable = [PalletState.EXPECTED]
    for state in reachable:
        for source, target in PALLET_TRANSITIONS:
            if source == state and target not in reachable:
                reachable.append(target)
    assert PalletState.STORED in reachable
    assert sorted(reachable) == sorted(PalletState)


def test_the_log_satisfies_the_envelope_invariants() -> None:
    """VAL-GATE-ENV-001 in miniature. Fails on a gapped or duplicated sequence."""
    run = run_station_line(_line(pallets=5), seed=3)

    assert run.events
    assert check_log_invariants(run.events) == []


def test_the_same_seed_reproduces_the_same_log() -> None:
    """VAL-GATE-DET-001 in miniature. Fails on any unnamed source of randomness."""
    left = run_station_line(_line(pallets=6), seed=99)
    right = run_station_line(_line(pallets=6), seed=99)

    assert log_hash(left.events) == log_hash(right.events)


def test_a_different_seed_produces_a_different_log() -> None:
    """The falsifier for the test above.

    A model that ignored its seed, or one whose service time was a constant,
    would pass the reproduction test and fail this one. Without this test the
    determinism claim is satisfied by returning an empty list.

    The run id is pinned to one value on both sides deliberately. Left to its
    default it carries the seed, so every event id would differ and the hashes
    would part company for a model that never drew anything. Holding it fixed
    is what makes this test measure the draws rather than the naming.
    """
    left = run_station_line(_line(pallets=6), seed=99, run_id="fixed")
    right = run_station_line(_line(pallets=6), seed=100, run_id="fixed")

    assert log_hash(left.events) != log_hash(right.events)


def test_each_pallet_draws_its_own_service_time() -> None:
    """Requirement 1 asks for realistic variability, so it has to be present.

    The registry derives a generator from the stream name on every handout, so
    a model that calls it once per draw restarts the stream and hands every
    pallet the same number. That model reproduces byte for byte, passes every
    determinism test here, and simulates a line with no variability at all.
    """
    run = run_station_line(_line(pallets=8, gap_ticks=1_000), seed=23)

    for activity in ("unload", "putaway"):
        durations = [
            payload["duration_ticks"]
            for payload in _payloads(run, "twinflow.twin.activity_completed")
            if payload["activity"] == activity
        ]
        assert len(durations) == 8
        assert len(set(durations)) > 1, f"{activity} durations never varied: {durations}"


def test_capacity_bounds_the_number_of_pallets_in_service() -> None:
    """Fails on a model that ignores Station.capacity.

    Six pallets released at one instant into a single-server station cannot
    overlap in service. The same six into a two-server station must.
    """
    single = run_station_line(_line(pallets=6, receiving_capacity=1), seed=5)
    double = run_station_line(_line(pallets=6, receiving_capacity=2), seed=5)

    assert _overlaps(_intervals(single, "unload")) == 0
    assert _overlaps(_intervals(double, "unload")) > 0


def test_a_full_staging_buffer_blocks_the_upstream_station() -> None:
    """Section 3.1: a full buffer blocks upstream, recorded as its own state.

    Fails on a model with an unbounded buffer, which is the modeling error that
    makes a simulated line outrun the real one it stands for.
    """
    tight = run_station_line(
        _line(pallets=8, staging_capacity=1, receiving_scale_s=5.0, putaway_scale_s=120.0),
        seed=17,
    )
    roomy = run_station_line(
        _line(pallets=8, staging_capacity=64, receiving_scale_s=5.0, putaway_scale_s=120.0),
        seed=17,
    )

    def blocked_spells(run) -> int:
        return sum(
            1
            for spell in run.traces["recv-01"]
            if spell.state is StationState.IDLE_BLOCKED and spell.duration_ticks > 0
        )

    assert blocked_spells(tight) > 0
    assert blocked_spells(roomy) == 0
    assert tight.max_staged_pallets <= 1


def test_the_run_declares_every_stream_it_draws_from() -> None:
    """C1: a draw with no declared stream is randomness nobody can reproduce."""
    run = run_station_line(_line(pallets=2), seed=1)

    built = _payloads(run, "twinflow.twin.model_built")
    assert len(built) == 1
    assert built[0]["stream_names"] == [RECEIVING_STREAM, SERVICE_STREAM]


def test_event_time_is_the_declared_epoch_plus_sim_offset() -> None:
    """D-02: no wall clock reaches an event payload.

    Fails on an implementation that stamps events from the system clock, which
    is the defect that makes two runs of one seed differ in every timestamp.
    """
    run = run_station_line(_line(pallets=2), seed=2)

    first = run.events[0]
    assert first.time == EPOCH
    assert int(first.twinflowsimts) == 0
    for event in run.events:
        offset_s = int(event.twinflowsimts) / TICK_HZ
        assert (event.time - EPOCH).total_seconds() == pytest.approx(offset_s)


def test_the_run_id_is_a_function_of_its_inputs() -> None:
    """Fails on a generated run id, which makes every run hash differently."""
    assert run_station_line(_line(), seed=8).run_id == run_station_line(_line(), seed=8).run_id
    assert run_station_line(_line(), seed=8).run_id != run_station_line(_line(), seed=9).run_id


def test_service_durations_are_whole_ticks_and_agree_with_the_tape() -> None:
    """Section 5.2: distributions round once, at the point of scheduling.

    Fails on a model that carries a float duration into the schedule, which is
    how two platforms end up one tick apart on the same seed.
    """
    run = run_station_line(_line(pallets=4), seed=4)

    for payload in _payloads(run, "twinflow.twin.activity_completed"):
        assert isinstance(payload["duration_ticks"], int)
        assert payload["duration_ticks"] >= 0

    for activity in ("unload", "putaway"):
        completions = [
            payload
            for payload in _payloads(run, "twinflow.twin.activity_completed")
            if payload["activity"] == activity
        ]
        spans = _intervals(run, activity)
        assert [payload["duration_ticks"] for payload in completions] == [
            end - start for start, end in spans
        ]


def test_the_sampler_applies_no_clamp_and_no_cap() -> None:
    """ARCHITECTURE.md section 3: no sigma cap, no tail clipping, no clamp.

    The strongest available check is identity against the untouched numpy
    transform: a truncation at any finite number of standard deviations, or a
    floor at any positive value, changes at least one of these 20000 draws.
    """
    spec = DistributionSpec(family="lognormal", scale_s=30.0, shape=1.4)
    theirs = generator_for("twin.receiving.unload_duration", base_seed=77)
    mine = generator_for("twin.receiving.unload_duration", base_seed=77)

    drawn = [spec.sample_s(mine) for _ in range(20_000)]
    expected = [30.0 * float(theirs.lognormal(0.0, 1.4)) for _ in range(20_000)]

    assert drawn == expected
    # And the tail is really there: a 5-sigma lognormal draw is 1000x its
    # median, and a capped implementation cannot produce one.
    assert max(drawn) > 30.0 * 20.0


def test_a_distribution_missing_its_shape_is_a_config_error() -> None:
    """Section 3: every distribution is named in config with its parameters.

    Fails on an implementation that substitutes a default shape, which is a
    parameter the config never declared and no reader can inspect.
    """
    with pytest.raises(ValueError, match="shape"):
        DistributionSpec(family="gamma", scale_s=10.0)
    with pytest.raises(ValueError, match="shape"):
        DistributionSpec(family="exponential", scale_s=10.0, shape=2.0)


def test_a_line_refuses_two_stations_with_one_id() -> None:
    """Section 3.1: every cross-reference id resolves, and ids are unique.

    Two stations sharing an id share a stream name and a state trace, so the
    run would report one station's utilization for both.
    """
    station = StationSpec(
        station_id="same-01",
        kind="receiving",
        zone_id="dock-a",
        capacity=1,
        service_time=DistributionSpec(family="exponential", scale_s=10.0),
    )
    with pytest.raises(ValueError, match="distinct"):
        StationLineSpec(
            line_id="clash",
            tick_hz=TICK_HZ,
            epoch=EPOCH,
            receiving=station,
            putaway=station.model_copy(update={"kind": "putaway"}),
            staging_capacity=4,
            arrivals=_arrivals(1),
        )


def test_arrivals_out_of_order_are_refused() -> None:
    """Section 5.13: arrivals are exogenous and replayed verbatim.

    Sorting them silently would make a mis-authored trace produce a plausible
    run, and the authoring error would never surface.
    """
    with pytest.raises(ValueError, match="release_tick"):
        StationLineSpec(
            line_id="unsorted",
            tick_hz=TICK_HZ,
            epoch=EPOCH,
            receiving=StationSpec(
                station_id="recv-01",
                kind="receiving",
                zone_id="dock-a",
                capacity=1,
                service_time=DistributionSpec(family="exponential", scale_s=10.0),
            ),
            putaway=StationSpec(
                station_id="put-01",
                kind="putaway",
                zone_id="storage-a",
                capacity=1,
                service_time=DistributionSpec(family="exponential", scale_s=10.0),
            ),
            staging_capacity=4,
            arrivals=(
                PalletArrival(pallet_id="plt-1", sku_id="s", qty_units=1, release_tick=50),
                PalletArrival(pallet_id="plt-0", sku_id="s", qty_units=1, release_tick=10),
            ),
        )
