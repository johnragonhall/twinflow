"""The D-02 pacer, and the one property that makes time compression safe."""

import pytest

from twinflow.kernel import PacedClock, SimClock, SimInstant
from twinflow.kernel._impl.paced import ASAP, MAX_SPEED, MIN_SPEED


def _tape(clock, instants):
    """The log a run would emit: what was emitted, and in what order."""
    emitted = []
    for instant in instants:
        clock.advance_to(SimInstant(instant))
        emitted.append((int(clock.now()), f"event_at_{instant}"))
    return emitted


def test_pacing_does_not_change_the_tape():
    """The whole safety argument for time compression, asserted.

    Pacing delays the loop between events and never reorders them. A paced run
    and an unpaced run emit identical logs; only the wall time at which each
    line appears differs. DET-4 is the CI gate over this same property.

    The speed is high enough that the test does not spend real time waiting:
    the property is about equality of the two tapes, not about how long the
    paced arm took.
    """
    instants = [0, 10, 10, 25, 1_000, 1_000_000]

    unpaced = _tape(SimClock(), instants)
    paced = _tape(PacedClock(SimClock(), speed=100_000.0), instants)

    assert paced == unpaced


def test_asap_does_no_pacing_at_all():
    clock = PacedClock(SimClock(), speed=ASAP)
    assert clock.target_wall_ns(SimInstant(10**9)) is None


def test_target_wall_time_follows_the_section_5_3_arithmetic():
    """The pacer formula, restated independently of the implementation.

    target = pacer_start + (t1 - run_start) * 1e9 // (tick_hz * speed)
    """
    inner = SimClock(tick_hz=1_000_000)
    clock = PacedClock(inner, speed=2.0)
    start = clock._pacer_start_monotonic_ns

    # One simulated second at speed 2 should land half a real second later.
    target = clock.target_wall_ns(SimInstant(1_000_000))
    assert target is not None, "a finite speed always has a deadline"
    assert target == start + (1_000_000 * 1_000_000_000) // (1_000_000 * 2.0)
    assert target - start == 500_000_000


def test_a_higher_speed_is_a_nearer_deadline():
    """Compression means the same sim instant is due sooner in wall time."""
    slow = PacedClock(SimClock(), speed=1.0)
    fast = PacedClock(SimClock(), speed=1_000.0)

    slow_target = slow.target_wall_ns(SimInstant(10**6))
    fast_target = fast.target_wall_ns(SimInstant(10**6))
    assert slow_target is not None and fast_target is not None

    slow_delta = slow_target - slow._pacer_start_monotonic_ns
    fast_delta = fast_target - fast._pacer_start_monotonic_ns

    assert fast_delta < slow_delta


def test_speed_outside_the_declared_range_is_refused():
    """TF-A031. The range is what an operator may ask for at the dashboard."""
    for bad in (0.0, MIN_SPEED / 2, MAX_SPEED * 2, -1.0):
        with pytest.raises(ValueError, match="TF-A031"):
            PacedClock(SimClock(), speed=bad)


def test_speed_bounds_are_the_ones_section_5_3_publishes():
    assert MIN_SPEED == 0.01
    assert MAX_SPEED == 100_000


def test_a_non_numeric_speed_is_refused():
    with pytest.raises(ValueError, match="float"):
        PacedClock(SimClock(), speed="fast")


def test_paced_clock_reads_through_to_the_wrapped_clock():
    """A pacer is a view of one clock, never a second source of sim time."""
    inner = SimClock(tick_hz=1_000)
    clock = PacedClock(inner, speed=ASAP)

    assert clock.tick_hz == 1_000
    inner.advance_to(SimInstant(42))
    assert clock.now() == 42
