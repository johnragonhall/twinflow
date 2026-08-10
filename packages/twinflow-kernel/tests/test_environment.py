"""The environment driver seam (E40), which ships in P0 with a null driver."""

from dataclasses import FrozenInstanceError

import pytest

from twinflow.kernel import (
    CALM,
    EnvironmentDriver,
    EnvironmentRegistry,
    EnvironmentState,
    NullEnvironmentDriver,
    SimInstant,
)


def test_the_null_driver_is_calm_at_every_instant():
    driver = NullEnvironmentDriver()
    assert driver.state_at(SimInstant(0)) == CALM
    assert driver.state_at(SimInstant(10**12)) == CALM


def test_the_null_driver_satisfies_the_port():
    """A later driver is swapped in without a caller changing."""
    assert isinstance(NullEnvironmentDriver(), EnvironmentDriver)


def test_a_registry_with_no_driver_is_null_and_says_so():
    """A result computed under calm weather must not read as one that survived a storm."""
    registry = EnvironmentRegistry()
    assert registry.is_null()
    assert registry.state_at(SimInstant(5)) == CALM


def test_a_registry_with_a_driver_is_not_null():
    class Stormy:
        @property
        def name(self):
            return "stormy"

        def state_at(self, instant):
            del instant
            return EnvironmentState(severity=0.8, visibility=0.3, traction=0.4)

    registry = EnvironmentRegistry(Stormy())
    assert not registry.is_null()
    assert registry.state_at(SimInstant(1)).severity == 0.8


def test_a_driver_answers_the_same_instant_the_same_way():
    """A hook may be evaluated more than once while a scheduler explores a decision."""
    driver = NullEnvironmentDriver()
    assert driver.state_at(SimInstant(42)) == driver.state_at(SimInstant(42))


def test_hooks_are_declared_and_registration_is_append_only():
    registry = EnvironmentRegistry()
    registry.register_hook("twin.yard.slip_risk", "yard moves slow on a wet surface")
    with pytest.raises(ValueError, match="already registered"):
        registry.register_hook("twin.yard.slip_risk", "a second description")


def test_declared_hooks_sort_rather_than_follow_registration_order():
    """D-03. This reaches a run manifest, so import order must not decide it."""
    registry = EnvironmentRegistry()
    registry.register_hook("transport.lane.transit_time", "rain slows a lane")
    registry.register_hook("demand.orders.rate", "weather moves demand")
    registry.register_hook("facility.hvac.load", "temperature moves load")

    assert registry.declared_hooks() == (
        "demand.orders.rate",
        "facility.hvac.load",
        "transport.lane.transit_time",
    )


def test_a_hook_name_outside_the_grammar_is_refused():
    registry = EnvironmentRegistry()
    for bad in ("", "Twin.Yard", "twin yard", "twin/yard"):
        with pytest.raises(ValueError, match="hook name"):
            registry.register_hook(bad, "whatever")


@pytest.mark.parametrize("field", ["severity", "visibility", "traction"])
def test_a_state_fraction_outside_zero_to_one_is_refused(field):
    """A hook multiplies a rate by these, so a value outside the range is a
    silent scaling error rather than a loud one.
    """
    with pytest.raises(ValueError, match=field):
        EnvironmentState(**{field: 1.5})


def test_calm_is_the_neutral_element():
    """A caller written against the seam behaves the same with no driver installed."""
    assert CALM.severity == 0.0
    assert CALM.visibility == 1.0
    assert CALM.traction == 1.0
    assert CALM.temperature_offset == 0.0


@pytest.mark.parametrize("field", ["severity", "visibility", "traction", "temperature_offset"])
def test_a_state_is_immutable(field):
    """CALM is a module-level singleton, so a caller mutating it would change
    the neutral value every other caller reads.

    The field name comes from the parameter rather than a literal. A literal
    assignment is a static error the type checker rejects before the test runs,
    and a literal setattr is a lint finding; a name the tools cannot resolve
    statically is both legal and a wider assertion.
    """
    with pytest.raises(FrozenInstanceError):
        setattr(CALM, field, 0.5)
