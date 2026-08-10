"""The D-02 pacer: the one clock in this package that reads wall time.

Time compression is what makes a simulated day watchable. The safety argument
is narrow and worth stating exactly: pacing delays the loop *between* events
and never reorders them, so the emitted log is identical at every speed. What
changes is when an event is emitted in wall time, never which event is emitted
or in what order.

The monotonic reading is the pacer's own, taken when pacing starts and held
here. It never reaches an event payload, the hashed tape, or a branch. The
wall_clock_anchor in the hashed core carries no monotonic field at all (M5).
"""

from __future__ import annotations

import time

from twinflow.kernel._impl.time import Duration, SimInstant

#: Section 5.3. The lower bound is what a human operator can ask for at the
#: dashboard, where a demo at one hundredth of real time is legitimate. It is
#: not what a property test or a determinism gate may use: the property
#: strategy clamps its own lower bound so a run cannot select a speed whose
#: worst case exceeds its job budget.
MIN_SPEED = 0.01
MAX_SPEED = 100_000.0

#: The speed meaning "do not pace at all".
ASAP = "asap"

_NANOSECONDS_PER_SECOND = 1_000_000_000


class PacedClock:
    """Wraps a clock and blocks between events so sim time tracks wall time.

    Delegates every reading to the wrapped clock, so it is the same sim time
    seen through a pacer rather than a second source of truth.
    """

    def __init__(self, inner, *, speed: float | str = ASAP, run_start: SimInstant | None = None):
        self._inner = inner
        self._speed = self._validate(speed)
        self._run_start = int(run_start if run_start is not None else inner.now())
        # twinflow: allow-nondeterminism(TFD001) the D-02 pacer, ADR-0002.
        # Monotonic rather than wall: this measures elapsed real time for
        # blocking only, and a clock adjustment mid-run must not move it.
        self._pacer_start_monotonic_ns = time.monotonic_ns()

    @staticmethod
    def _validate(speed: float | str) -> float | str:
        if speed == ASAP:
            return ASAP
        if not isinstance(speed, (int, float)) or isinstance(speed, bool):
            raise ValueError(f"speed is a float or {ASAP!r}, got {speed!r}")
        if not MIN_SPEED <= float(speed) <= MAX_SPEED:
            raise ValueError(f"TF-A031: speed {speed} is outside [{MIN_SPEED}, {MAX_SPEED}]")
        return float(speed)

    @property
    def speed(self) -> float | str:
        return self._speed

    @property
    def tick_hz(self) -> int:
        return self._inner.tick_hz

    def now(self) -> SimInstant:
        return self._inner.now()

    def timeout(self, duration: Duration) -> SimInstant:
        return self._inner.timeout(duration)

    def target_wall_ns(self, instant: SimInstant) -> int | None:
        """The monotonic deadline this instant should be emitted at.

        None when pacing is off, which is what `asap` means. Separated from the
        blocking call so the arithmetic of section 5.3 can be tested without a
        test that has to sleep.
        """
        if self._speed == ASAP:
            return None
        return self._pacer_start_monotonic_ns + (
            (int(instant) - self._run_start)
            * _NANOSECONDS_PER_SECOND
            // (self._inner.tick_hz * self._speed)
        )

    def advance_to(self, instant: SimInstant) -> None:
        """Advance the wrapped clock, blocking first when pacing is on.

        The block happens before the advance, so an event is never emitted
        early and then paced afterwards.
        """
        target = self.target_wall_ns(instant)
        if target is not None:
            # twinflow: allow-nondeterminism(TFD001) the D-02 pacer, ADR-0002.
            while time.monotonic_ns() < target:
                remaining_ns = target - time.monotonic_ns()
                if remaining_ns <= 0:
                    break
                time.sleep(remaining_ns / _NANOSECONDS_PER_SECOND)
        self._inner.advance_to(instant)
