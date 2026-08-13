"""Where the historian sits, and what it is allowed to call a series.

Requirement RA-c is one row of the layer map in ARCHITECTURE.md section 4:
the historian is ISA-95 L2, Purdue L3 published into L3.5, and it is the L2
system of record for time-series. A row in a table is prose. Prose drifts from
code with nothing failing at the moment it drifts, so the row is a value here
and tests/test_naming.py reads the table back and compares.

Being the system of record has one mechanical consequence, and it is the reason
this module exists rather than a comment: a series has exactly one name. That
name is the UNS topic of ARCHITECTURE.md section 5, six levels, generated from
config. A second spelling of one series is two answers to "what happened at
this equipment", and a system of record that gives two answers is a cache.

The grammar those names obey is not restated here. `UnsPath` and its six-level
rules live in twinflow.config, which owns the facility model that section 5
makes the namespace a projection of. This package once carried its own copy and
twinflow.sensors carried another, which is two definitions of one contract and
therefore a drift waiting for the first tightening. What is left here is the
part that is genuinely the historian's: which layer it answers at, and the
series key it mints from a path something else validated.
"""

from __future__ import annotations

from dataclasses import dataclass

from twinflow.config import NamingError, UnsPath

#: The levels the Purdue model defines, plus the DMZ. A placement outside this
#: set is a typo, and a typo in a layer map is a wrong architecture diagram.
PURDUE_LEVELS = ("L0", "L1", "L2", "L3", "L3.5", "L4")


@dataclass(frozen=True)
class LayerPlacement:
    """One row of the ISA-95 and Purdue layer map.

    `published_into` is separate from `purdue` because the historian's row
    carries both: it runs at L3 and its data crosses into the DMZ at L3.5. A
    single field would have to hold "L3, published into L3.5" as a string, and
    a consumer asking which level this component runs at would have to parse
    English to find out.
    """

    component: str
    isa95: str
    purdue: str
    published_into: str | None
    counterpart: str
    system_of_record_for: str | None

    def __post_init__(self) -> None:
        for name in ("isa95", "purdue", "published_into"):
            value = getattr(self, name)
            if value is None:
                continue
            if value not in PURDUE_LEVELS:
                raise NamingError(
                    "TF-S006",
                    f"{self.component} declares {name}={value!r}, which is not one of "
                    f"{', '.join(PURDUE_LEVELS)}",
                )


#: Requirement RA-c, as a value. ARCHITECTURE.md section 4 is the source, and
#: test_the_historian_placement_matches_the_layer_map_row reads it back.
HISTORIAN = LayerPlacement(
    component="Historian",
    isa95="L2",
    purdue="L3",
    published_into="L3.5",
    counterpart="Plant historian, the L2 system of record for time-series",
    system_of_record_for="time-series",
)


@dataclass(frozen=True)
class SeriesName:
    """One time series, and the layer the historian answers for it at.

    The placement rides on the name rather than sitting in a document, so a
    consumer holding a series knows which system of record produced it without
    consulting one.
    """

    key: str
    topic: UnsPath
    placement: LayerPlacement

    @property
    def parameter(self) -> str:
        return self.topic.parameter

    @property
    def published_into(self) -> str | None:
        return self.placement.published_into


def series_for(topic: UnsPath) -> SeriesName:
    """The historian's name for one topic.

    A pure function of the six levels. Two callers holding the same topic get
    the same series, which is what "system of record" has to mean before it
    means anything else.
    """
    return SeriesName(key=topic.topic, topic=topic, placement=HISTORIAN)
