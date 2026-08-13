"""The conveyor motor temperature sensor.

Three rules carry this device: the raw reading is published beside anything
derived from it, the unit lives in the parameter name, and a reading outside
the sensor's physical plausibility band is refused rather than clamped into it.
The last one is the one worth a test, because clamping is the change that makes
a fault signature vanish while every chart still looks healthy.
"""

from __future__ import annotations

import pytest

from twinflow.kernel import SimInstant
from twinflow.sensors import (
    PlausibilityBand,
    TemperatureSensor,
    TemperatureSensorConfig,
)

PT100 = TemperatureSensorConfig(
    plausibility=PlausibilityBand(low_c=-50.0, high_c=250.0),
    ewma_alpha=0.25,
)


def sensor(uns_prefix=("twinflow", "dc-01", "receiving", "inbound-line-01", "conveyor-02")):
    return TemperatureSensor(config=PT100, uns_prefix=uns_prefix)


# --------------------------------------------------------------- the raw value


def test_the_raw_reading_is_published_beside_the_derived_one():
    device = sensor()
    device.read(71.4, now=SimInstant(0))
    reading = device.read(73.0, now=SimInstant(1_000))
    published = reading.metric_values()
    assert published["motor_temp_c"] == pytest.approx(73.0)
    assert published["motor_temp_ewma_c"] == pytest.approx(0.25 * 73.0 + 0.75 * 71.4)


def test_every_published_parameter_carries_its_unit_in_its_name():
    device = sensor()
    reading = device.read(71.4, now=SimInstant(0))
    assert all(name.endswith("_c") for name in reading.metric_values())


def test_the_first_reading_seeds_the_derived_value_rather_than_inventing_a_history():
    reading = sensor().read(71.4, now=SimInstant(0))
    assert reading.metric_values()["motor_temp_ewma_c"] == pytest.approx(71.4)


# ------------------------------------------------------------- the plausibility


@pytest.mark.parametrize("value", [-270.0, 900.0])
def test_an_implausible_reading_is_refused_rather_than_clamped_into_the_band(value):
    device = sensor()
    reading = device.read(value, now=SimInstant(0))
    assert reading.raw_c == pytest.approx(value), "the raw value is never rewritten"
    assert reading.plausible is False
    assert reading.quality == "bad"


def test_a_refused_reading_produces_no_derived_value_and_publishes_none():
    device = sensor()
    device.read(71.4, now=SimInstant(0))
    reading = device.read(-270.0, now=SimInstant(1_000))
    published = reading.metric_values()
    assert published["motor_temp_c"] == pytest.approx(-270.0)
    assert "motor_temp_ewma_c" not in published


def test_a_refused_reading_never_enters_the_derived_state():
    device = sensor()
    device.read(71.4, now=SimInstant(0))
    device.read(-270.0, now=SimInstant(1_000))
    reading = device.read(71.4, now=SimInstant(2_000))
    assert reading.metric_values()["motor_temp_ewma_c"] == pytest.approx(71.4)


def test_the_band_edges_are_inside_the_band():
    device = sensor()
    assert device.read(-50.0, now=SimInstant(0)).plausible is True
    assert device.read(250.0, now=SimInstant(1_000)).plausible is True


def test_an_inverted_plausibility_band_is_refused():
    with pytest.raises(ValueError, match="low_c"):
        PlausibilityBand(low_c=250.0, high_c=-50.0)


def test_a_band_below_absolute_zero_is_refused():
    with pytest.raises(ValueError, match="absolute zero"):
        PlausibilityBand(low_c=-300.0, high_c=50.0)


def test_a_violation_is_reported_with_the_bound_it_left():
    device = sensor()
    violation = device.read(900.0, now=SimInstant(0)).violation
    assert violation is not None
    assert violation.bound == "high_c"
    assert violation.limit_c == pytest.approx(250.0)
    assert violation.observed_c == pytest.approx(900.0)


def test_an_ewma_alpha_outside_the_unit_interval_is_refused():
    with pytest.raises(ValueError, match="ewma_alpha"):
        TemperatureSensorConfig(
            plausibility=PlausibilityBand(low_c=-50.0, high_c=250.0), ewma_alpha=1.5
        )


# ----------------------------------------------------------------- the topics


def test_the_sensor_publishes_the_conveyor_topic_architecture_section_5_prints():
    device = sensor()
    device.read(71.4, now=SimInstant(0))
    topics = [path.topic for path, _ in device.publish(71.9, now=SimInstant(1_000))]
    assert "twinflow/dc-01/receiving/inbound-line-01/conveyor-02/motor_temp_c" in topics
    assert all(topic.count("/") == 5 for topic in topics)


def test_the_sensor_reads_the_injected_clock_rather_than_a_wall_clock():
    device = sensor()
    reading = device.read(71.4, now=SimInstant(9_876))
    assert reading.device_ts == 9_876
