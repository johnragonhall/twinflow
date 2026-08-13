"""The physical invariants of the station model, asserted rather than clamped.

ARCHITECTURE.md section 3 is explicit that a physical impossibility is a
property-based test assertion and never a runtime clamp, because a clamp hides
a modeling error by producing plausible output from a wrong distribution. Each
test below is one row of that table, narrowed to what a receiving and putaway
line can violate.

The invariant ids come from docs/design/twin-core.md: INV-TWIN-01 material
conservation, INV-TWIN-06 one location per pallet, INV-TWIN-09 exact state
trace closure in integer arithmetic.
"""

from __future__ import annotations

from datetime import UTC, datetime

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from twinflow.schemas import log_hash
from twinflow.twin.station import (
    DistributionSpec,
    PalletArrival,
    StationLineSpec,
    StationRun,
    StationSpec,
    run_station_line,
)

pytestmark = pytest.mark.property

EPOCH = datetime(2026, 1, 1, tzinfo=UTC)


@st.composite
def service_times(draw: st.DrawFn) -> DistributionSpec:
    """Every family the model offers, each with the parameters it declares.

    Exponential carries no shape, and the spec refuses one, so the strategy
    cannot hand it one either.
    """
    family = draw(st.sampled_from(("lognormal", "gamma", "weibull", "exponential")))
    scale_s = draw(st.floats(min_value=0.5, max_value=90.0))
    if family == "exponential":
        return DistributionSpec(family=family, scale_s=scale_s)
    return DistributionSpec(
        family=family,
        scale_s=scale_s,
        shape=draw(st.floats(min_value=0.6, max_value=3.0)),
    )


@st.composite
def lines(draw: st.DrawFn) -> StationLineSpec:
    """A small but genuinely varied receiving and putaway line.

    The pallet count stays small because 200 examples of a discrete-event run
    have to fit inside the unit tier's budget, and the invariants below are
    violated by two pallets as readily as by two hundred.
    """
    tick_hz = draw(st.sampled_from((1_000, 1_000_000)))
    pallet_count = draw(st.integers(min_value=1, max_value=8))
    gaps = draw(
        st.lists(
            st.integers(min_value=0, max_value=20),
            min_size=pallet_count,
            max_size=pallet_count,
        )
    )
    release = 0
    arrivals = []
    for index, gap in enumerate(gaps):
        release += gap * tick_hz
        arrivals.append(
            PalletArrival(
                pallet_id=f"plt-{index:04d}",
                sku_id="sku-0001",
                qty_units=draw(st.integers(min_value=1, max_value=60)),
                release_tick=release,
            )
        )

    return StationLineSpec(
        line_id="prop-line",
        tick_hz=tick_hz,
        epoch=EPOCH,
        receiving=StationSpec(
            station_id="recv-01",
            kind="receiving",
            zone_id="dock-a",
            capacity=draw(st.integers(min_value=1, max_value=3)),
            service_time=draw(service_times()),
        ),
        putaway=StationSpec(
            station_id="put-01",
            kind="putaway",
            zone_id="storage-a",
            capacity=draw(st.integers(min_value=1, max_value=3)),
            service_time=draw(service_times()),
        ),
        staging_capacity=draw(st.integers(min_value=1, max_value=4)),
        arrivals=tuple(arrivals),
    )


def _ledger_walk(run: StationRun) -> list[tuple[int, int, int]]:
    """Received, put away, and reported in-system at every WIP boundary.

    Derived from the tape rather than read off a field the model wrote, so a
    model that keeps a wrong counter and reports it consistently still fails.
    """
    received = 0
    put_away = 0
    walk: list[tuple[int, int, int]] = []
    for event in run.events:
        if event.type == "twinflow.twin.pallet_created":
            received += event.data["qty_units"]
        elif (
            event.type == "twinflow.twin.activity_completed" and event.data["activity"] == "putaway"
        ):
            put_away += event.data["attrs"]["qty_units"]
        elif event.type == "twinflow.twin.wip_sampled":
            walk.append((received, put_away, event.data["units"]))
    return walk


@settings(max_examples=200, deadline=None)
@given(spec=lines(), seed=st.integers(min_value=0, max_value=2**32 - 1))
def test_mass_is_conserved_at_every_event_boundary(spec: StationLineSpec, seed: int) -> None:
    """INV-TWIN-01. Units received equal units in system plus units put away.

    Scrap is zero here because this line has no scrap source: there is no
    silent disposal, so a shortfall is a modeling defect rather than a rounding
    allowance.
    """
    run = run_station_line(spec, seed=seed)

    for received, put_away, in_system in _ledger_walk(run):
        assert received == in_system + put_away

    assert run.ledger.units_scrapped == 0
    assert run.ledger.is_balanced
    assert run.ledger.units_received == sum(arrival.qty_units for arrival in spec.arrivals)


@settings(max_examples=200, deadline=None)
@given(spec=lines(), seed=st.integers(min_value=0, max_value=2**32 - 1))
def test_the_event_clock_is_monotone(spec: StationLineSpec, seed: int) -> None:
    """A tape whose sim timestamps go backwards reorders under replay."""
    run = run_station_line(spec, seed=seed)

    stamps = [int(event.twinflowsimts) for event in run.events]
    assert stamps == sorted(stamps)
    assert stamps[0] == 0
    assert stamps[-1] <= run.end_tick


@settings(max_examples=200, deadline=None)
@given(spec=lines(), seed=st.integers(min_value=0, max_value=2**32 - 1))
def test_queues_are_non_negative_and_never_exceed_the_declared_buffer(
    spec: StationLineSpec, seed: int
) -> None:
    """A queue that can go negative has lost a unit somewhere upstream."""
    run = run_station_line(spec, seed=seed)

    for event in run.events:
        if event.type != "twinflow.twin.wip_sampled":
            continue
        assert event.data["queue_units"] >= 0
        assert event.data["units"] >= 0

    assert 0 <= run.max_staged_pallets <= spec.staging_capacity


@settings(max_examples=200, deadline=None)
@given(spec=lines(), seed=st.integers(min_value=0, max_value=2**32 - 1))
def test_the_resource_state_trace_closes_the_window_exactly(
    spec: StationLineSpec, seed: int
) -> None:
    """INV-TWIN-09, in integer ticks rather than floats.

    Utilization, OEE, and the six big losses are all read off this trace, so a
    gap or an overlap in it is a wrong denominator in every one of them.
    """
    run = run_station_line(spec, seed=seed)

    for station_id in (spec.receiving.station_id, spec.putaway.station_id):
        spells = run.traces[station_id]
        assert spells[0].start_tick == 0
        assert spells[-1].end_tick == run.end_tick
        for earlier, later in zip(spells, spells[1:], strict=False):
            assert earlier.end_tick == later.start_tick
        assert sum(spell.duration_ticks for spell in spells) == run.end_tick


@settings(max_examples=200, deadline=None)
@given(spec=lines(), seed=st.integers(min_value=0, max_value=2**32 - 1))
def test_one_seed_reproduces_one_tape(spec: StationLineSpec, seed: int) -> None:
    """Doctrine D-05 tier one, over the whole generated space rather than one case."""
    left = run_station_line(spec, seed=seed)
    right = run_station_line(spec, seed=seed)

    assert log_hash(left.events) == log_hash(right.events)
    assert left.end_tick == right.end_tick


@settings(max_examples=200, deadline=None)
@given(spec=lines(), seed=st.integers(min_value=0, max_value=2**32 - 1))
def test_every_pallet_is_created_once_and_stored_once(spec: StationLineSpec, seed: int) -> None:
    """INV-TWIN-06 reduced to a two-station line: one location at a time.

    A pallet that reaches STORED twice has been counted twice in throughput,
    and a pallet that never reaches it has vanished from the ledger.
    """
    run = run_station_line(spec, seed=seed)

    created = [
        event.data["pallet_id"]
        for event in run.events
        if event.type == "twinflow.twin.pallet_created"
    ]
    stored = [
        event.data["case_id"]
        for event in run.events
        if event.type == "twinflow.twin.activity_completed" and event.data["activity"] == "putaway"
    ]

    assert created == [arrival.pallet_id for arrival in spec.arrivals]
    assert sorted(stored) == sorted(created)
