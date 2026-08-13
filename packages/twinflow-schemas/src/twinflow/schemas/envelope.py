"""The event envelope.

Settled before any schema is published, because doctrine D-07 makes adding a
field a major version bump on every subject.

The envelope is CloudEvents 1.0.2. That specification requires an attribute
name to be lower-case ASCII letters or digits with no separators, and requires
extension attributes to follow the same rule, which is why the twinflow
attributes read twinflowsimts rather than twinflow_sim_ts. The field list and
the field semantics belong to docs/design/foundations.md section 3.4, and this
module restates nothing that file already fixes.

Every constraint here is declarative rather than a validator function, and that
is load-bearing. schemas/envelope/v1.json is generated from this model, and a
constraint held in a field_validator is invisible to that generation: the
published schema would accept values this model rejects, and a consumer
validating against the published file would disagree with the producer.
"""

from __future__ import annotations

from datetime import datetime
from typing import Annotated, Literal, get_args

from pydantic import BaseModel, ConfigDict, Field

#: The closed set of process roles that may publish an event, from invariant E3.
#: A new role is a line in schemas/registry.yaml rather than a free string,
#: because the role is inside the deterministic event id of invariant E2 and a
#: free value would put an unreviewed string into every hash.
ProducerId = Literal["sim", "api", "dashboard", "agent", "device-agent", "cli"]

#: Derived from the Literal above rather than written twice.
PRODUCER_IDS: tuple[str, ...] = get_args(ProducerId)

#: A decimal string: no sign, no fractional part, and no leading zero unless the
#: value is zero itself. Two spellings of one number would sort as two values in
#: the total order.
DECIMAL_PATTERN = r"^(0|[1-9][0-9]*)$"

#: Section 3.4 fixes the source as a URI-reference of the form
#: /twinflow/<package>/<component>.
SOURCE_PATTERN = r"^/twinflow/[a-z0-9][a-z0-9_-]*(/[a-z0-9][a-z0-9_-]*)+$"

#: CloudEvents 1.0.2 says an attribute name SHOULD NOT exceed 20 characters.
#: That is a recommendation; only the character set is a MUST. twinflow adopts
#: it as a hard rule anyway, because a name that survives one protocol hop and
#: not the next costs more than a short name does. The longest name this
#: envelope carries is twinflowcausationid, at 19.
MAX_ATTRIBUTE_NAME_LENGTH = 20

#: 40 characters holds any uint64 with room to spare: 2**64 is 20 digits.
DecimalString = Annotated[str, Field(min_length=1, max_length=40, pattern=DECIMAL_PATTERN)]

SourceUri = Annotated[str, Field(pattern=SOURCE_PATTERN)]


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
    source: SourceUri
    type: str
    time: datetime
    datacontenttype: Literal["application/json"]
    subject: str | None = None
    dataschema: str

    # twinflow extension attributes.
    twinflowsimts: DecimalString
    twinflowrunid: str
    twinflowproducerid: ProducerId = Field(
        description=(
            "Which process role published this. The sequence is dense per "
            "producer, never globally, because several containers and the Rust "
            "agent all append to one log and no global counter has an allocator."
        )
    )
    twinflowseq: DecimalString
    twinflowcausationid: str | None = None
    twinflowcorrid: str | None = None

    # Attributes owned by CloudEvents extensions rather than by twinflow. A
    # twinflow-prefixed name here would be invisible to every off-the-shelf
    # CloudEvents tool, and interoperability is what the envelope is for.
    partitionkey: str | None = None
    traceparent: str | None = None
    tracestate: str | None = None

    data: dict

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
