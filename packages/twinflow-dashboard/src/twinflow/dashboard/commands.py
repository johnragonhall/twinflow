"""`POST /api/command`, the only write path from the browser.

`docs/design/dashboard-replay.md` section 4.2 fixes the transport: POST with the
envelope as JSON, in live mode only, answering `202` plus the assigned
`(producer_id, seq)` or `422` with the schema validation error. Not a WebSocket,
because commands are rare, are idempotent by `command_id`, and a POST stays
auditable and testable with curl.

Two determinism decisions travel with it. The `command_id` is assigned by the
browser as `c-%04d` from a per-session counter rather than as a random token, so
a retry is idempotent without anything random reaching the log. And the envelope
carries `sim_time` and no wall-clock field: requirement C1 needs the log to be
byte-identical from a seed, and a wall-clock stamp inside it makes that false by
construction. The operator-facing audit strip still shows a human-readable time,
which the server writes to the provenance sidecar per doctrine D-01 and joins on
`command_id` at render time.

Contract test `CT-UI-3` says the `kind` enum in `ui.command.v1`, the server's
dispatch table, and the browser's command builders all carry the same set. Two of
those three live in this repository today and the test compares them. The schema
is owed, and README.md records that.
"""

from __future__ import annotations

import re
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime, timedelta

from twinflow.schemas import Envelope

#: The subject the command envelope is published under.
COMMAND_SUBJECT = "ui.command.v1"

#: Invariant E3 closes the producer set, and the browser publishes as this role.
COMMAND_PRODUCER = "dashboard"

COMMAND_SOURCE = "/twinflow/dashboard/commands"

COMMAND_DATASCHEMA = "twinflow:schemas/ui/command/v1.json"

#: `c-%04d` from a per-session counter, per section 4.2. At least four digits so
#: the shape is stable, and open-ended above so a long session does not wrap
#: into ids it has already used.
COMMAND_ID_PATTERN = re.compile(r"^c-\d{4,}$")


@dataclass(frozen=True)
class CommandKind:
    """One row of the dispatch table of section 4.2."""

    name: str
    required: tuple[str, ...]
    optional: tuple[str, ...]
    mode: str
    handled_by: str
    audited: bool


#: The table of section 4.2, sorted by name so the set is stable in every
#: rendering of it. `mode` is which mode the command exists in at all: a live
#: command issued in replay is refused by the browser with a labeled message and
#: never sent, and a replay command arriving here is refused with the same
#: reasoning from the other side.
COMMAND_KINDS: tuple[CommandKind, ...] = (
    CommandKind("ack_finding", ("finding_id",), (), "live", "server", True),
    CommandKind("approve_whatif", ("request_id",), ("note",), "live", "server", True),
    CommandKind("ask_agent", ("text",), ("context",), "live", "server", True),
    CommandKind("pause", (), (), "both", "server", True),
    CommandKind("reject_whatif", ("request_id",), ("note",), "live", "server", True),
    CommandKind("resume", (), (), "both", "server", True),
    CommandKind("seek", ("sim_time",), (), "replay", "browser", False),
    CommandKind("set_pref", ("key", "value"), (), "both", "browser", False),
    CommandKind("set_speed", ("speed",), (), "both", "server", True),
    CommandKind("shelve_alarm", ("key", "duration_s", "reason"), (), "live", "server", True),
    CommandKind("step", ("steps",), (), "both", "both", True),
    CommandKind("unshelve_alarm", ("key",), (), "live", "server", True),
)

COMMAND_NAMES: tuple[str, ...] = tuple(kind.name for kind in COMMAND_KINDS)

#: The kinds this server accepts over POST. `browser`-handled commands never
#: cross the wire: `set_pref` writes to localStorage and `seek` moves a playhead
#: in a viewer that has no server. Accepting them here would record a preference
#: change into an append-only log that requirement C1 compares byte for byte.
SERVER_HANDLED: tuple[str, ...] = tuple(
    kind.name for kind in COMMAND_KINDS if kind.handled_by in ("server", "both")
)


class CommandError(ValueError):
    """A command this server will not record, carrying every reason at once.

    Every reason rather than the first, because a browser that fixes one field
    and resubmits to learn the next is a round trip per mistake, and the write
    path is the one surface where a retry loop is also an audit-log entry.
    """

    def __init__(self, reasons: tuple[str, ...]) -> None:
        super().__init__("; ".join(reasons))
        self.reasons = reasons


@dataclass(frozen=True)
class AcceptedCommand:
    """What the browser gets back: the position this command took in the log."""

    command_id: str
    kind: str
    producer_id: str
    seq: int
    sim_time: int
    audited: bool


def kind_named(name: str) -> CommandKind | None:
    for kind in COMMAND_KINDS:
        if kind.name == name:
            return kind
    return None


def validate_command(payload: Mapping[str, object], *, mode: str) -> CommandKind:
    """Check one command against the dispatch table, or refuse it with reasons."""
    reasons: list[str] = []

    command_id = payload.get("command_id")
    if not isinstance(command_id, str) or not COMMAND_ID_PATTERN.match(command_id):
        reasons.append(
            "command_id must match c-%04d, which is what makes a retry idempotent without "
            "a random identifier"
        )

    name = payload.get("kind")
    kind = kind_named(name) if isinstance(name, str) else None
    if kind is None:
        reasons.append(f"kind {name!r} is not one of {', '.join(COMMAND_NAMES)}")
        raise CommandError(tuple(reasons))

    if kind.name not in SERVER_HANDLED:
        reasons.append(
            f"{kind.name} is handled by the browser and is never posted; recording it would "
            f"put a client-side preference into the append-only log"
        )
    if kind.mode not in ("both", mode):
        reasons.append(
            f"{kind.name} exists in {kind.mode} mode and this server runs in {mode} mode"
        )

    data = payload.get("data")
    if not isinstance(data, Mapping):
        reasons.append("data must be an object, even when the command carries no fields")
        raise CommandError(tuple(reasons))

    allowed = set(kind.required) | set(kind.optional)
    missing = sorted(set(kind.required) - set(data))
    unexpected = sorted(set(data) - allowed)
    if missing:
        reasons.append(f"{kind.name} needs {', '.join(missing)}")
    if unexpected:
        reasons.append(f"{kind.name} does not carry {', '.join(unexpected)}")

    if kind.name == "shelve_alarm" and not str(data.get("reason", "")).strip():
        reasons.append(
            "shelve_alarm needs a non-empty reason; section 7.4 makes the reason mandatory "
            "because a shelf with no reason is an alarm nobody has to answer for"
        )

    if reasons:
        raise CommandError(tuple(reasons))
    return kind


class CommandLog:
    """Assigns each accepted command its position in the append-only log.

    The sequence is dense per producer, which is doctrine D-07 and what
    `Historian.append` refuses a gap in. Holding the counter here rather than
    reading it back from a store is deliberate: a counter derived from a query
    would skip after a refused command and the historian would reject the next
    one.
    """

    def __init__(self, *, run_id: str, epoch: datetime, tick_hz: int) -> None:
        self._run_id = run_id
        self._epoch = epoch
        self._tick_hz = tick_hz
        self._seq = 0
        self._by_command_id: dict[str, AcceptedCommand] = {}

    @property
    def seq(self) -> int:
        return self._seq

    def record(
        self, payload: Mapping[str, object], *, kind: CommandKind, sim_time: int
    ) -> tuple[AcceptedCommand, Envelope | None]:
        """Give this command its `(producer_id, seq)` and mint its envelope.

        Replaying a `command_id` returns the original position rather than
        taking a second one. Section 4.2 calls commands idempotent by
        `command_id`, and a retry after a dropped response is the ordinary case
        rather than the exceptional one.

        The envelope is `None` on a replay, because the event it would carry is
        already on the log. Its id, its producer, and its sequence are all
        derived from the position, so a second copy repeats an id the log holds
        and violates the dense-sequence invariant of D-07. The caller publishes
        exactly what this returns, so the absence is the instruction.
        """
        command_id = str(payload["command_id"])
        existing = self._by_command_id.get(command_id)
        if existing is not None:
            return existing, None

        accepted = AcceptedCommand(
            command_id=command_id,
            kind=kind.name,
            producer_id=COMMAND_PRODUCER,
            seq=self._seq,
            sim_time=sim_time,
            audited=kind.audited,
        )
        self._seq += 1
        self._by_command_id[command_id] = accepted
        return accepted, self._envelope(payload, accepted=accepted)

    def _envelope(self, payload: Mapping[str, object], *, accepted: AcceptedCommand) -> Envelope:
        """The CloudEvents envelope for one command.

        The `time` attribute is the sim epoch plus sim time rather than a wall
        reading. CloudEvents requires the attribute; doctrine D-02 forbids the
        reading; deriving it from the declared epoch satisfies both and keeps
        two runs of one seed byte-identical.
        """
        return Envelope(
            specversion="1.0",
            id=f"{self._run_id}-{COMMAND_PRODUCER}-{accepted.seq}",
            source=COMMAND_SOURCE,
            type=COMMAND_SUBJECT,
            time=self._epoch + timedelta(seconds=accepted.sim_time / self._tick_hz),
            datacontenttype="application/json",
            subject=COMMAND_SUBJECT,
            dataschema=COMMAND_DATASCHEMA,
            twinflowsimts=str(accepted.sim_time),
            twinflowrunid=self._run_id,
            twinflowproducerid=COMMAND_PRODUCER,
            twinflowseq=str(accepted.seq),
            data={
                "command_id": accepted.command_id,
                "kind": accepted.kind,
                "sim_time": accepted.sim_time,
                "data": dict(payload.get("data", {})),  # type: ignore[arg-type]
            },
        )
