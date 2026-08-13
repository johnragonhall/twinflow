"""The conveyor motor temperature sensor, the second P1 device.

WP-P1-02. It publishes on
`twinflow/dc-01/receiving/inbound-line-01/conveyor-02/motor_temp_c`, the second
of the two concrete topics ARCHITECTURE.md section 5 prints.

Three rules carry this device, and the third is the one worth arguing about.

The raw reading is published BESIDE anything derived from it. A consumer that
receives only a smoothed value cannot recover the samples, cannot compute its
own control limits, and cannot see the single-sample excursion that a filter
with any memory at all will hide.

The unit lives in the parameter name. `motor_temp_c` cannot be misread as
Fahrenheit, and the alternative is a units field that travels separately from
the number and is dropped by the first tool in the chain that does not model it.

A reading outside the sensor's physical plausibility band is REFUSED rather
than clamped into it. Clamping is the change that makes a fault signature
disappear while every chart still looks healthy: a thermocouple whose junction
has failed open reads hundreds of degrees out, and the clamped version of that
reading is a value indistinguishable from a warm motor.

Refused, precisely, means this: the raw value is published unmodified, because
docs/design/variability-and-faults.md B.10 is explicit that a reading is never
clipped to the physical range and that the out-of-range value IS the fault
signature a detector has to catch. What is refused is its use. The reading is
marked bad, it produces no derived value, and it never enters the state the
derived value is computed from. So a detector reading the raw stream sees the
excursion, and a KPI reading the derived stream is not quietly poisoned by it.
Discarding the reading and clamping the reading are two different mistakes and
this avoids both.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any

from twinflow.config import UnsPath
from twinflow.kernel import SimInstant

#: Absolute zero in degrees Celsius. A plausibility band whose floor is below
#: this is not a wide band, it is a typo, and it would admit readings no
#: thermometer can produce.
ABSOLUTE_ZERO_C = -273.15

#: The raw parameter and the derived one, both carrying their unit. Written
#: once here so the birth certificate and the publish path cannot disagree
#: about which metrics this device owns.
RAW_PARAMETER = "motor_temp_c"
DERIVED_PARAMETER = "motor_temp_ewma_c"


@dataclass(frozen=True, slots=True)
class PlausibilityBand:
    """The range outside which a reading is not a measurement of this quantity.

    Not the same thing as an alarm limit and not the same thing as the
    engineering range. A motor above its alarm limit is a real motor in
    trouble; a motor at -270 C is a broken sensor. Only the second belongs
    here, which is why the band is wide enough to contain every alarm the twin
    might raise.
    """

    low_c: float
    high_c: float

    def __post_init__(self) -> None:
        if self.low_c >= self.high_c:
            raise ValueError(
                f"low_c {self.low_c} is at or above high_c {self.high_c}; a "
                "plausibility band with no interior refuses every reading"
            )
        if self.low_c < ABSOLUTE_ZERO_C:
            raise ValueError(
                f"low_c {self.low_c} is below absolute zero at {ABSOLUTE_ZERO_C} C, "
                "so the band admits readings no thermometer can produce"
            )

    def contains(self, value_c: float) -> bool:
        """Closed on both ends: a reading exactly at a bound is plausible."""
        return self.low_c <= value_c <= self.high_c

    def violated_bound(self, value_c: float) -> str | None:
        if value_c < self.low_c:
            return "low_c"
        if value_c > self.high_c:
            return "high_c"
        return None


@dataclass(frozen=True, slots=True)
class PlausibilityViolation:
    """Which bound a reading left, and by how much.

    Carries the observed value as well as the limit, because an operator's
    first question about an implausible reading is how far out it was: a degree
    past the bound is a calibration drift and three hundred is an open circuit.
    """

    bound: str
    limit_c: float
    observed_c: float


@dataclass(frozen=True, slots=True)
class TemperatureSensorConfig:
    """The sensor's plausibility band and its smoothing constant."""

    plausibility: PlausibilityBand
    ewma_alpha: float

    def __post_init__(self) -> None:
        if not 0.0 < self.ewma_alpha <= 1.0:
            raise ValueError(
                f"ewma_alpha {self.ewma_alpha} is outside (0, 1]; at zero the filter "
                "never moves and above one it overshoots every step"
            )


@dataclass(frozen=True, slots=True)
class TemperatureReading:
    """One reading, raw and derived together.

    `derived_c` is None when the raw reading was refused. None rather than the
    previous value, because republishing the last good number under a new
    timestamp is how a frozen sensor comes to look like a stable process.
    """

    device_ts: SimInstant
    raw_c: float
    plausible: bool
    derived_c: float | None = None
    violation: PlausibilityViolation | None = None

    @property
    def quality(self) -> str:
        """The plain-text quality the JSON mirror carries."""
        return "good" if self.plausible else "bad"

    def metric_values(self) -> dict[str, Any]:
        """The parameter-to-value mapping this reading publishes.

        The raw value is always present, including when it was refused: that
        value is the fault signature, and omitting it would leave a detector
        with nothing to detect. The derived value is absent when there is none,
        rather than defaulted to zero or carried over.
        """
        values: dict[str, Any] = {RAW_PARAMETER: self.raw_c}
        if self.derived_c is not None:
            values[DERIVED_PARAMETER] = self.derived_c
        return dict(sorted(values.items()))


class TemperatureSensor:
    """One motor temperature channel on one piece of equipment.

    Holds exactly one piece of state, the EWMA, and refuses to let an
    implausible reading into it. The clock is passed per call rather than held,
    so this class has no route to a wall clock at all.
    """

    def __init__(
        self,
        *,
        config: TemperatureSensorConfig,
        uns_prefix: Sequence[str] | None = None,
    ) -> None:
        self._config = config
        self._uns_prefix = tuple(uns_prefix) if uns_prefix is not None else None
        self._ewma: float | None = None

    @property
    def config(self) -> TemperatureSensorConfig:
        return self._config

    @property
    def ewma_c(self) -> float | None:
        """The current smoothed value, or None before the first good reading."""
        return self._ewma

    def read(self, raw_c: float, *, now: SimInstant) -> TemperatureReading:
        """Take one raw reading and decide what may be derived from it."""
        band = self._config.plausibility
        bound = band.violated_bound(raw_c)
        if bound is not None:
            return TemperatureReading(
                device_ts=now,
                raw_c=raw_c,
                plausible=False,
                derived_c=None,
                violation=PlausibilityViolation(
                    bound=bound,
                    limit_c=getattr(band, bound),
                    observed_c=raw_c,
                ),
            )

        if self._ewma is None:
            # The first reading seeds the filter rather than being smoothed
            # toward a starting value nobody measured. Seeding at zero would
            # make the first minute of every run a ramp that looks like a
            # warming motor.
            self._ewma = raw_c
        else:
            alpha = self._config.ewma_alpha
            self._ewma = alpha * raw_c + (1.0 - alpha) * self._ewma

        return TemperatureReading(device_ts=now, raw_c=raw_c, plausible=True, derived_c=self._ewma)

    def publish(self, raw_c: float, *, now: SimInstant) -> tuple[tuple[UnsPath, Any], ...]:
        """Render one reading as (topic, value) pairs on the six-level namespace."""
        if self._uns_prefix is None:
            raise RuntimeError(
                "this sensor was built with no UNS prefix, so it has no address to "
                "publish on; hand it the five identifier levels of its equipment"
            )
        reading = self.read(raw_c, now=now)
        return tuple(
            (UnsPath.from_prefix(self._uns_prefix, parameter), value)
            for parameter, value in reading.metric_values().items()
        )

    @staticmethod
    def metric_parameters() -> tuple[str, str]:
        """Every parameter this sensor may ever publish.

        The DBIRTH needs the complete list, because a metric absent from a
        birth certificate may never appear in a data message, and the derived
        parameter is absent from most individual readings.
        """
        return (DERIVED_PARAMETER, RAW_PARAMETER)
