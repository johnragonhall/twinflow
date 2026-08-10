"""The time invariants of foundations section 3.1, asserted rather than reviewed."""

import pytest

from twinflow.kernel import (
    MAX_HORIZON_TICKS,
    MAX_SIM_YEARS,
    Duration,
    SimClock,
    SimInstant,
    TickResolution,
    duration_from_seconds,
)


def test_tick_resolutions_are_the_three_the_spec_names():
    """T4. A resolution outside these three has no declared overflow arithmetic."""
    assert TickResolution == (1_000, 1_000_000, 1_000_000_000)


def test_default_tick_hz_is_microseconds():
    """T4. One microsecond covers 292000 years in a signed 64-bit integer."""
    clock = SimClock()
    assert clock.tick_hz == 1_000_000


def test_sim_time_starts_at_the_epoch():
    """T2. The sim epoch is tick 0."""
    assert SimClock().now() == SimInstant(0)


def test_clock_rejects_a_resolution_outside_the_declared_three():
    with pytest.raises(ValueError, match="tick_hz"):
        SimClock(tick_hz=500)


def test_now_is_non_decreasing(recwarn):
    """T3 and INV-K1. A clock that can go backwards reorders a recorded log."""
    clock = SimClock()
    clock.advance_to(SimInstant(10))
    assert clock.now() == 10
    with pytest.raises(ValueError, match="backwards"):
        clock.advance_to(SimInstant(9))
    assert clock.now() == 10


def test_advance_to_accepts_the_same_instant():
    """Two events at one instant are ordered by the envelope, not by the clock."""
    clock = SimClock()
    clock.advance_to(SimInstant(10))
    clock.advance_to(SimInstant(10))
    assert clock.now() == 10


def test_sim_instant_is_never_negative():
    """T2."""
    clock = SimClock()
    with pytest.raises(ValueError, match="negative"):
        clock.advance_to(SimInstant(-1))


def test_duration_conversion_rounds_half_up_away_from_zero():
    """T1. The loader converts "4.5 min" to ticks with round-half-up away from zero.

    Python's round() is banker's rounding, so round(0.5) is 0 and round(2.5) is
    2. A config author writing a value that lands exactly halfway on a tick
    boundary would get a different duration depending on whether the tick index
    happened to be even, which is a rule nobody can predict from the config.
    """
    assert duration_from_seconds(0.0000005, tick_hz=1_000_000) == Duration(1)
    assert duration_from_seconds(0.0000015, tick_hz=1_000_000) == Duration(2)
    assert duration_from_seconds(0.0000025, tick_hz=1_000_000) == Duration(3)
    assert duration_from_seconds(-0.0000005, tick_hz=1_000_000) == Duration(-1)


def test_duration_conversion_is_exact_for_a_representable_value():
    assert duration_from_seconds(4.5 * 60, tick_hz=1_000_000) == Duration(270_000_000)


def test_duration_is_signed_but_sim_instant_is_not():
    """T1 and T2. A duration may be negative; a point in time may not."""
    assert duration_from_seconds(-1.0, tick_hz=1_000) == Duration(-1_000)


def test_horizon_bound_is_the_float64_tick_limit():
    """T5. Above 2**53 ticks two distinct instants map to one float64.

    SimEventLoop.time() is the single float shim, and asyncio compares those
    floats internally. Past this bound it stops being able to tell two
    scheduled instants apart, so the loader rejects the run rather than let a
    scheduler silently coalesce two events.
    """
    assert MAX_HORIZON_TICKS == 2**53 - 1


def test_max_sim_years_is_the_t4_cap():
    """T4. The loader rejects a horizon beyond 100 sim years as TF-C031."""
    assert MAX_SIM_YEARS == 100
