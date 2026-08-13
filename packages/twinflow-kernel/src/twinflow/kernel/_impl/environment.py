"""The environment driver seam (E40), shipping with a null driver.

One correlated weather state moves demand, lane transit, yard operations, HVAC
load, and slip risk together. That makes it one shared state and one RNG child
stream rather than five independent draws, which is a determinism concern and
therefore a Phase 0 one.

The seam ships now and the process arrives much later. That order is deliberate:
each phase in between registers its own sensitivity hook against a registry that
already exists, so the phase that finally supplies a real driver wires it to
hooks nobody has to go back and add. Building the process first would mean every
later phase edits the weather code instead of declaring what it is sensitive to.

Until then `NullEnvironmentDriver` answers every state with its neutral value,
so a caller written against the seam behaves identically whether or not a driver
is installed.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Protocol, runtime_checkable

from twinflow.kernel._impl.time import SimInstant

#: Dotted lowercase, matching the subsystem the hook belongs to. Written as a
#: pattern rather than an isalnum() check, which accepts uppercase and would let
#: two spellings of one hook name into a run manifest.
_HOOK_NAME = re.compile(r"^[a-z][a-z0-9_]*(\.[a-z][a-z0-9_]*)*$")


@dataclass(frozen=True)
class EnvironmentState:
    """The exogenous state at one instant.

    Every field is a normalized scalar rather than a physical quantity. A hook
    multiplies a rate or shifts a duration by these, and normalizing here means
    a hook never needs to know whether the driver behind it models millimetres
    of rain or a storm category.
    """

    #: 0.0 is calm and 1.0 is the worst condition the driver models.
    severity: float = 0.0
    #: Fraction of normal visibility, 1.0 being clear.
    visibility: float = 1.0
    #: Fraction of normal surface grip, 1.0 being dry.
    traction: float = 1.0
    #: Degrees above or below the seasonal norm, as a normalized offset.
    temperature_offset: float = 0.0

    def __post_init__(self) -> None:
        for name in ("severity", "visibility", "traction"):
            value = getattr(self, name)
            if not 0.0 <= value <= 1.0:
                raise ValueError(f"{name} is a fraction in [0, 1], got {value}")


#: What every caller sees when no driver is installed.
CALM = EnvironmentState()


@runtime_checkable
class EnvironmentDriver(Protocol):
    """Supplies the exogenous state for one run."""

    @property
    def name(self) -> str: ...

    def state_at(self, instant: SimInstant) -> EnvironmentState:
        """The state at this instant.

        Deterministic in the instant: the same run asked twice for the same
        instant gets the same answer, because a hook may be evaluated more than
        once while a scheduler explores a decision.
        """
        ...


class NullEnvironmentDriver:
    """The P0 driver. Calm at every instant, and never random."""

    @property
    def name(self) -> str:
        return "null"

    def state_at(self, instant: SimInstant) -> EnvironmentState:
        del instant
        return CALM


class EnvironmentRegistry:
    """Holds the driver for a run and the sensitivity hooks declared against it.

    A hook is registered by name so a run manifest can record which subsystems
    were sensitive to the environment, which is what makes a divergence between
    two runs traceable to one hook rather than to the weather as a whole.
    """

    def __init__(self, driver: EnvironmentDriver | None = None) -> None:
        self._driver: EnvironmentDriver = driver or NullEnvironmentDriver()
        # A dict rather than a set: doctrine D-03 bans a collection whose
        # iteration order can reach a hash, and declared_hooks() reaches one.
        self._hooks: dict[str, str] = {}

    @property
    def driver(self) -> EnvironmentDriver:
        return self._driver

    def register_hook(self, name: str, description: str) -> None:
        """Declare that a subsystem responds to the environment.

        Append-only for the same reason the stream registry is: a name recorded
        in a run manifest has to keep meaning what it meant.
        """
        if not _HOOK_NAME.match(name or ""):
            raise ValueError(
                f"hook name {name!r} is dotted lowercase alphanumerics, "
                f"matching the subsystem it belongs to"
            )
        if name in self._hooks:
            raise ValueError(f"hook {name!r} is already registered; registration is append-only")
        self._hooks[name] = description

    def declared_hooks(self) -> tuple[str, ...]:
        """Every declared hook, sorted.

        Sorted rather than in registration order, because this reaches the run
        manifest and D-03 forbids an order that depends on import sequence.
        """
        return tuple(sorted(self._hooks))

    def state_at(self, instant: SimInstant) -> EnvironmentState:
        return self._driver.state_at(instant)

    def is_null(self) -> bool:
        """Whether this run had no real driver.

        A run manifest records this, so a result computed under calm weather is
        never mistaken for one that survived a storm.
        """
        return isinstance(self._driver, NullEnvironmentDriver)
