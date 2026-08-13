"""The unified namespace grammar, once, where the facility model already lives.

ARCHITECTURE.md section 5 is normative: a telemetry topic is
`{enterprise}/{site}/{area}/{line}/{equipment}/{parameter}`, six levels, and
"the namespace is a projection of the facility model, not a parallel truth".
That sentence is why the grammar sits in twinflow.config rather than beside
either of the packages that render it. The publish side (twinflow.sensors) and
the storage side (twinflow.storage) each grew their own copy of these rules,
and two definitions of one six-level contract disagree on the first day one of
them is tightened. The layer order puts config below both, so both import the
one definition rather than owning a spelling of it.

Validation happens at construction rather than at publish or at write time.
That is what makes every rendering safe at once: a level that passed the
pattern cannot carry a wildcard, a separator, a space, or the colon the
Sparkplug Group ID uses to rejoin the first three levels, so the topic string,
the subscription, the Sparkplug identifiers, and the historian series key are
all derived from something already checked. A check at each rendering site is
one call site away from being forgotten.

Where the two merged grammars disagreed, the stricter reading won, because a
name has to be publishable and storable at once and the union of the two
refusals is the only rule that keeps both true. So `dc01-` and `read__rate` are
refused, as the storage side always refused them, and a level is bounded in
length, as the publish side always bounded it.

Deliberately narrower than docs/design/sensor-catalog.md D.1 in one place. That
section lets the parameter level carry further slashes so a channel can nest,
which makes a published topic more than six levels deep. ARCHITECTURE section 5
fixes device telemetry at exactly six, and the two concrete P1 topics it prints
are single-segment. This module takes the stricter reading, so a nested
parameter is a change to this pattern and to that document together rather than
a topic depth that varies by device.
"""

from __future__ import annotations

import re
from collections.abc import Iterator, Mapping, Sequence
from dataclasses import dataclass, replace
from typing import Any

#: Six, from ARCHITECTURE.md section 5: a fixed depth is what makes an
#: area-level subscription mean the same thing everywhere.
TOPIC_LEVELS = 6

#: The MQTT level separator. A level that contained one would silently add a
#: level, so the patterns below exclude it.
TOPIC_SEPARATOR = "/"

#: The MQTT wildcards. Legal in a subscription, never in a published topic.
WILDCARDS = ("+", "#")

#: The six levels, in topic order. The first five are identifiers and the last
#: is the parameter, which is the only asymmetry in the grammar.
LEVEL_NAMES = ("enterprise", "site", "area", "line", "equipment", "parameter")

#: Lowercase kebab-case, for the first five levels. The bound is a lookahead
#: rather than a second check so one pattern is the whole rule: an identifier
#: that passes this is short enough to publish and shaped correctly, and
#: `is_identifier` cannot disagree with the constructor.
#:
#: `\A` and `\Z` rather than `^` and `$`, because `$` also matches before a
#: trailing newline, and a level ending in one renders a topic with a line
#: break inside it that no subscriber can type.
IDENTIFIER = re.compile(r"\A(?=.{1,32}\Z)[a-z0-9]+(-[a-z0-9]+)*\Z")

#: Lowercase snake_case starting with a letter, for the parameter level. Kept
#: separate from the identifier pattern rather than widened into it, because a
#: level that accepts both conventions accepts `motor-temp-c` and `motor_temp_c`
#: as two addresses for one quantity. Units ride inside the name where a bare
#: quantity would be ambiguous, so `motor_temp_c` is an ordinary parameter
#: rather than a special case.
PARAMETER = re.compile(r"\A(?=.{1,64}\Z)[a-z][a-z0-9]*(_[a-z0-9]+)*\Z")


class NamingError(ValueError):
    """A name the namespace refuses, with the code the operator sees.

    A ValueError subclass, so a caller that only wants to know the name was bad
    catches what it would have caught anyway, and a caller that reports to an
    operator reads `.code`.
    """

    def __init__(self, code: str, message: str) -> None:
        super().__init__(f"{code} {message}")
        self.code = code


@dataclass(frozen=True, slots=True)
class UnsPath:
    """One six-level ISA-95 telemetry address.

    Constructing this from six config-derived values is the only way to a topic
    string. The alternative, an f-string at the call site, is how a namespace
    and the facility it describes drift apart: nothing fails, and six months
    later two dashboards disagree about which conveyor is which.
    """

    enterprise: str
    site: str
    area: str
    line: str
    equipment: str
    parameter: str

    def __post_init__(self) -> None:
        for name in LEVEL_NAMES[:-1]:
            _check_identifier(name, getattr(self, name))
        _check_parameter(self.parameter)

    # ------------------------------------------------------------- predicates

    @staticmethod
    def is_identifier(value: object) -> bool:
        """True when this is a legal value for the first five levels."""
        return isinstance(value, str) and IDENTIFIER.match(value) is not None

    @staticmethod
    def is_parameter(value: object) -> bool:
        """True when this is a legal value for the parameter level."""
        return isinstance(value, str) and PARAMETER.match(value) is not None

    # ------------------------------------------------------------- renderings

    @property
    def levels(self) -> tuple[str, str, str, str, str, str]:
        """The six levels in topic order."""
        return (
            self.enterprise,
            self.site,
            self.area,
            self.line,
            self.equipment,
            self.parameter,
        )

    @property
    def topic(self) -> str:
        """The published topic string, which every other rendering derives from."""
        return TOPIC_SEPARATOR.join(self.levels)

    def subscription(self, depth: int) -> str:
        """The subscription covering everything under the first `depth` levels.

        This is the one place a wildcard is produced, which is the section 5
        rule stated as an API rather than as a warning: a caller who wants
        every parameter in an area asks for it here, and a caller who wants a
        published topic cannot get a wildcard by accident.
        """
        if not 1 <= depth <= TOPIC_LEVELS:
            raise NamingError(
                "TF-S007",
                f"a subscription covers 1 to {TOPIC_LEVELS} levels, not {depth}",
            )
        if depth == TOPIC_LEVELS:
            return self.topic
        return TOPIC_SEPARATOR.join([*self.levels[:depth], "#"])

    # --------------------------------------------------------------- builders

    def with_equipment(self, equipment: str) -> UnsPath:
        return replace(self, equipment=equipment)

    def with_parameter(self, parameter: str) -> UnsPath:
        return replace(self, parameter=parameter)

    @classmethod
    def parse(cls, text: str) -> UnsPath:
        """Read a published topic back into the value object.

        The reverse of `topic`, and the two are asserted to round trip over
        generated names rather than over the examples in the documents. It is
        not a license to type topics: the builders below are how a producer
        gets one.
        """
        levels = text.split(TOPIC_SEPARATOR)
        if len(levels) != TOPIC_LEVELS:
            raise NamingError(
                "TF-S005",
                f"a device telemetry topic has exactly {TOPIC_LEVELS} levels, so an "
                f"area subscription always means the same thing, and {text!r} has "
                f"{len(levels)}",
            )
        return cls(*levels)

    @classmethod
    def from_prefix(cls, prefix: Sequence[str], parameter: str) -> UnsPath:
        """Build from the five identifier levels a device already knows.

        A device holds its own placement for the life of a run, so it carries
        the prefix and names only the parameter per point.
        """
        identifier_levels = LEVEL_NAMES[:-1]
        if len(prefix) != len(identifier_levels):
            raise NamingError(
                "TF-S008",
                f"a UNS prefix names {identifier_levels}, so it has "
                f"{len(identifier_levels)} levels; got {len(prefix)}: {tuple(prefix)!r}",
            )
        return cls(*prefix, parameter)

    @classmethod
    def from_facility(cls, facility: Mapping[str, Any]) -> Iterator[UnsPath]:
        """Generate every telemetry topic a facility mapping declares.

        ARCHITECTURE section 5: topic strings are generated from config, never
        typed by hand, so the namespace is a projection of the modeled facility
        rather than a parallel truth that drifts from it.

        The argument is a plain Mapping of the namespace shape rather than the
        document `load_facility` returns. The facility contract at
        `schemas/config/facility/v1.json` does not yet carry the ISA-95 tree, so
        naming that loader here would claim a projection that does not exist
        yet. Taking the shape also keeps this builder testable without a config
        file, and keeps a schema revision from reaching the grammar.

        Yields in sorted topic order. Sorting is not cosmetic: this iterator
        feeds the Sparkplug alias assignment above it, and doctrine D-03
        forbids a mapping's iteration order from reaching a value a second
        process has to reproduce.
        """
        paths: list[UnsPath] = []
        enterprise = _required(facility, "enterprise")
        site = _required(facility, "site")
        for area in facility.get("areas", ()):
            area_id = _required(area, "id", level="area")
            for line in area.get("lines", ()):
                line_id = _required(line, "id", level="line")
                for equipment in line.get("equipment", ()):
                    equipment_id = _required(equipment, "id", level="equipment")
                    for parameter in equipment.get("parameters", ()):
                        paths.append(
                            cls(
                                enterprise=enterprise,
                                site=site,
                                area=area_id,
                                line=line_id,
                                equipment=equipment_id,
                                parameter=parameter,
                            )
                        )
        yield from sorted(paths, key=lambda path: path.topic)


def _required(mapping: Mapping[str, Any], key: str, *, level: str | None = None) -> str:
    """Read one level out of the facility mapping, naming the level that failed.

    A missing key and an empty value are the same defect here, because both
    render an empty topic level, and an empty level is the failure the naming
    rules exist to prevent.
    """
    name = level or key
    value = mapping.get(key)
    if not value:
        raise NamingError(
            "TF-S001",
            f"the facility mapping declares no {name}; an absent or empty level "
            "would render a topic with an empty segment",
        )
    _check_identifier(name, value)
    return str(value)


def _check_identifier(level: str, value: object) -> None:
    _check_present(level, value)
    _check_no_wildcard(level, value)
    if not UnsPath.is_identifier(value):
        raise NamingError(
            "TF-S003",
            f"{level} {value!r} is not lowercase kebab-case within 32 characters; "
            f"identifiers look like dc-01 or inbound-line-01",
        )


def _check_parameter(value: object) -> None:
    _check_present("parameter", value)
    _check_no_wildcard("parameter", value)
    if not UnsPath.is_parameter(value):
        raise NamingError(
            "TF-S004",
            f"parameter {value!r} is not lowercase snake_case within 64 characters; "
            f"parameters look like read_rate or motor_temp_c, with the unit in the "
            f"name where it is ambiguous",
        )


def _check_present(level: str, value: object) -> None:
    if not isinstance(value, str):
        raise NamingError(
            "TF-S001", f"{level} {value!r} is not a string, so it names no topic level"
        )
    if value == "":
        raise NamingError(
            "TF-S001", f"{level} {value!r} is empty; a published topic has no empty level"
        )


def _check_no_wildcard(level: str, value: object) -> None:
    if isinstance(value, str) and any(card in value for card in WILDCARDS):
        raise NamingError(
            "TF-S002",
            f"{level} {value!r} carries a wildcard; wildcards belong in a subscription, "
            f"which is what UnsPath.subscription is for",
        )
