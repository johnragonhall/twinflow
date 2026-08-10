"""The event envelope.

Settled before any schema is published, because doctrine D-07 makes adding a
field a major version bump on every subject.

The envelope is CloudEvents 1.0.2. That specification requires an attribute
name to be lower-case ASCII letters or digits with no separators, and requires
extension attributes to follow the same rule, which is why the twinflow
attributes read twinflowsimts rather than twinflow_sim_ts. The field list and
the field semantics belong to docs/design/foundations.md section 3.4, and this
module restates nothing that file already fixes.
"""

from __future__ import annotations

import re
from datetime import datetime
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

# A decimal string: no sign, no fractional part, and no leading zero unless the
# value is zero itself.
_DECIMAL = re.compile(r"^(0|[1-9][0-9]*)$")

# Section 3.4 fixes the source as a URI-reference of the form
# /twinflow/<package>/<component>.
_SOURCE = re.compile(r"^/twinflow/[a-z0-9][a-z0-9_-]*(/[a-z0-9][a-z0-9_-]*)+$")

#: The closed set of process roles that may emit an event, from invariant E3.
#: A new role is a line in schemas/registry.yaml rather than a free string,
#: because the role is inside the deterministic event id of invariant E2 and a
#: free value would put an unreviewed string into every hash.
PRODUCER_IDS = ("sim", "api", "dashboard", "agent", "device-agent", "cli")

#: CloudEvents 1.0.2 says an attribute name SHOULD NOT exceed 20 characters.
#: That is a recommendation; only the character set is a MUST. twinflow adopts
#: it as a hard rule anyway, because a name that survives one protocol hop and
#: not the next costs more than a short name does. The longest name this
#: envelope carries is twinflowcausationid, at 19.
MAX_ATTRIBUTE_NAME_LENGTH = 20

DecimalString = Annotated[str, Field(min_length=1, max_length=40)]


class Envelope(BaseModel):
    """Envelope carried by every event on every transport.

    twinflowsimts and twinflowseq are decimal strings rather than integers.
    CloudEvents fixes its Integer type at 32 bits signed, and both quantities
    pass that in normal use: one simulated day at the default tick rate is
    8.64e10 ticks, and a single sensor scenario produces 5.184e9 readings.
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    # CloudEvents 1.0.2 context attributes.
    specversion: Literal["1.0"]
    id: str
    source: str
    type: str
    time: datetime
    datacontenttype: Literal["application/json"]
    subject: str | None = None
    dataschema: str

    # twinflow extension attributes.
    twinflowsimts: DecimalString
    twinflowrunid: str
    twinflowproducerid: str = Field(
        description=(
            "Which process role emitted this. The sequence is dense per "
            "producer, never globally, because several containers and the Rust "
            "agent all append to one log and no global counter has an allocator."
        )
    )
    twinflowseq: DecimalString
    twinflowcausationid: str | None = None
    twinflowcorrid: str | None = None

    # Attributes owned by CloudEvents extensions rather than by twinflow. A
    # twinflow-prefixed name here would be invisible to every off-the-shelf
    # CloudEvents tool, which is the interoperability the envelope was adopted
    # for.
    partitionkey: str | None = None
    traceparent: str | None = None
    tracestate: str | None = None

    data: dict

    @field_validator("twinflowsimts", "twinflowseq")
    @classmethod
    def _decimal_only(cls, value: str) -> str:
        if not _DECIMAL.match(value):
            raise ValueError(
                f"must be a non-negative decimal string with no leading zero, got {value!r}"
            )
        return value

    @field_validator("twinflowproducerid")
    @classmethod
    def _producer_is_a_declared_role(cls, value: str) -> str:
        if value not in PRODUCER_IDS:
            raise ValueError(
                f"{value!r} is not a declared producer role; one of {list(PRODUCER_IDS)}"
            )
        return value

    @field_validator("source")
    @classmethod
    def _source_is_a_twinflow_uri_reference(cls, value: str) -> str:
        if not _SOURCE.match(value):
            raise ValueError(f"source must read /twinflow/<package>/<component>, got {value!r}")
        return value

    @staticmethod
    def total_order_key(envelope: Envelope) -> tuple[int, bytes, int]:
        """The canonical total order, per doctrine D-07 and invariant E4.

        Ordering is (twinflowsimts, twinflowproducerid, twinflowseq). The two
        decimal fields convert to int here so they sort numerically: as
        strings, "10" sorts before "2". The producer id converts to bytes
        because E4 compares it as a byte string, and a role added later outside
        ASCII would otherwise reorder recorded logs silently.

        A reader replays in this order. A single process draws in scheduling
        order, which is a different thing, and confusing the two produces a
        reader that works on one container and reorders on a fleet.
        """
        return (
            int(envelope.twinflowsimts),
            envelope.twinflowproducerid.encode("utf-8"),
            int(envelope.twinflowseq),
        )
