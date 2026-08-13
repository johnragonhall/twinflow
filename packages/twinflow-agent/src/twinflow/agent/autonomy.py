"""Autonomy tier metadata, and the audit event that attributes a change (E5a).

docs/design/ai-layer.md section 3.4 states the tier-transition contract this
module implements, and the shape of it is the whole point: a session starts at
`autonomy.default_tier` and never rises on its own. So the interesting code here
is refusal code. `AutonomySession` exposes no method that raises the effective
tier except `approve`, and `approve` takes an `AutonomyGrant`, which cannot be
constructed without a human approver who is not the requester. An agent that has
been talked into applying a change therefore has nothing to call: the value it
would need to pass does not validate.

Three properties are enforced at construction rather than checked at use, which
is what makes them hold for callers this module has never seen.

    the approver is human            an agent in that field is a ValidationError
    the approver is not the requester   self-approval is self-elevation renamed
    the scope names tools, never a wildcard

Two more are enforced by the session, because they depend on deployment state
the grant cannot see: an L3 grant needs `autonomy.allow_write_tools`, and a
grant may not outlive the `autonomy.elevation.*` limits in the facility config.
Section 3.4 says there is no renewal path that skips a fresh approval, so a
grant that expires later than the config allows is refused rather than clamped.

Determinism. Every event this module emits carries the D-07 envelope, and
`VAL-GATE-ENV-001` runs over any log containing one, so the sequence is dense
per (run, producer) and the ordering key is a function of the run. The clock is
an injected port and the wall-clock `time` attribute is derived from the sim
tick and the run epoch, per envelope invariant E1 and doctrine D-02. Nothing
here reads a real clock, draws a random number, or mints a uuid.
"""

from __future__ import annotations

import re
from datetime import datetime, timedelta
from enum import StrEnum
from typing import Literal, Protocol, Self, runtime_checkable

from pydantic import BaseModel, ConfigDict, Field, model_validator

from twinflow.schemas import Envelope

#: The three governance events of section 4.1, and the change-attribution event
#: E5 requires. The `twinflow.` prefix is the CloudEvents `type` convention
#: foundations 3.4 fixes; the rest of each name is the subject as the AI layer's
#: event table spells it.
ELEVATION_REQUESTED = "twinflow.governance.autonomy.elevation.requested"
ELEVATION_DECIDED = "twinflow.governance.autonomy.elevation.decided"
ELEVATION_EXPIRED = "twinflow.governance.autonomy.elevation.expired"
CHANGE_ATTRIBUTED = "twinflow.governance.change.attributed"

#: URI-reference of the form /twinflow/<package>/<component>, per foundations 3.4.
SOURCE = "/twinflow/agent/autonomy"

#: One of the closed set in the envelope's ProducerId. The agent is a process
#: role, so its sequence is dense within itself and not across the fleet.
PRODUCER = "agent"

#: A tool is named, never matched. `require_named_scope` in the facility config
#: says a grant lists tools rather than a pattern, and this grammar is what makes
#: "*" fail rather than match everything.
TOOL_NAME = r"^[a-z][a-z0-9_]*$"

_SHA256 = r"^[0-9a-f]{64}$"


class AutonomyError(Exception):
    """A tier rule was broken. Never raised for an ordinary refusal to answer."""


class TierRefused(AutonomyError):
    """The gate refused a call the session does not have the authority to make."""


class AutonomyTier(StrEnum):
    """L1 advises, L2 recommends with human approval, L3 applies inside guardrails.

    Authority only. What an experiment may consume is a budget question and lives
    on `ToolSpec.sim_budget`, which is why running a simulation is L1.
    """

    L1 = "L1"
    L2 = "L2"
    L3 = "L3"

    @property
    def rank(self) -> int:
        return int(self.value[1:])

    def permits(self, required: AutonomyTier) -> bool:
        """Whether a session holding this tier may make a call needing `required`."""
        return self.rank >= required.rank


class ActorId(BaseModel):
    """Who asked or approved.

    `kind` is not decoration. The tier-transition contract turns on the approver
    being a human, so the human-ness has to be a field a validator can read
    rather than a convention about how ids are spelled.
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    kind: Literal["human", "agent"]
    id: str = Field(min_length=1, max_length=128)


class AutonomyGrant(BaseModel):
    """A scoped, expiring elevation approved by a human.

    Every field the tier-transition contract names, and three validators that
    make the contract hold at construction. A caller cannot hold an invalid grant
    long enough to pass it to anything.
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    grant_id: str = Field(min_length=1)
    session_id: str = Field(min_length=1)

    #: L1 is the floor rather than an elevation. Granting it would be a no-op
    #: that reads like an approval in the audit log, so the type excludes it.
    granted_tier: Literal[AutonomyTier.L2, AutonomyTier.L3]

    requested_by: ActorId
    approver: ActorId
    scope: tuple[str, ...] = Field(min_length=1)
    reason: str = Field(min_length=1)
    expires_after_questions: int = Field(ge=1)
    expires_at_sim_time: int = Field(ge=0)
    decision_id: str = Field(min_length=1)

    @model_validator(mode="after")
    def _the_approver_is_a_human_who_is_not_the_requester(self) -> Self:
        """Section 3.4: the approver is a human at L2 and L3.

        The second half of the rule is the one that gets forgotten. An approver
        equal to the requester is self-approval, which is self-elevation with a
        friendlier name, and it stays refused even when both actors are human.
        """
        if self.approver.kind != "human":
            raise ValueError(
                f"an elevation to {self.granted_tier} needs a human approver, "
                f"and {self.approver.id!r} is an agent"
            )
        if self.approver == self.requested_by:
            raise ValueError(
                f"{self.approver.id!r} cannot approve their own request for "
                f"{self.granted_tier}: an approval is a second party or it is nothing"
            )
        return self

    @model_validator(mode="after")
    def _the_scope_names_tools(self) -> Self:
        """`require_named_scope`. A wildcard is not a narrow grant with a short
        spelling; it is every tool, including the ones added after the approval."""
        for tool in self.scope:
            if not re.match(TOOL_NAME, tool):
                raise ValueError(
                    f"scope entry {tool!r} is not a tool name. A grant lists tools, "
                    f"never a pattern, so a tool added later is outside every grant "
                    f"approved before it existed"
                )
        if len(set(self.scope)) != len(self.scope):
            raise ValueError(f"scope names a tool twice: {self.scope}")
        return self


@runtime_checkable
class SimClockPort(Protocol):
    """The clock this module reads, declared here rather than imported.

    A structural protocol keeps twinflow-agent off twinflow-kernel, which is the
    second of the two channels section 2 allows for cross-package coupling.
    `twinflow.kernel.SimClock` satisfies it without knowing this file exists.
    """

    @property
    def tick_hz(self) -> int: ...

    def now(self) -> int: ...


class ElevationRequested(BaseModel):
    """Payload of governance.autonomy.elevation.requested (section 4.1).

    This is the approval seam the dashboard and the MCP client both render, so
    it carries what a human needs to decide and nothing they would have to look
    up somewhere else.
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    session_id: str
    question_id: str
    tool: str
    current_tier: AutonomyTier
    needed_tier: AutonomyTier
    requested_by: ActorId
    reason: str


class ElevationDecided(BaseModel):
    """Payload of governance.autonomy.elevation.decided.

    A refusal is a decision. It carries a null grant rather than being absent
    from the log, so a reader counting approvals against requests finds the
    difference accounted for.
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    session_id: str
    grant_id: str | None
    granted_tier: AutonomyTier | None
    approver: ActorId
    scope: tuple[str, ...]
    expires_after_questions: int | None
    expires_at_sim_time: int | None
    decision_id: str | None
    reason: str

    @model_validator(mode="after")
    def _a_grant_is_present_or_absent_whole(self) -> Self:
        granted = self.grant_id is not None
        companions = (
            self.granted_tier is not None,
            self.expires_after_questions is not None,
            self.expires_at_sim_time is not None,
            self.decision_id is not None,
        )
        if any(companions) != granted or (granted and not all(companions)):
            raise ValueError(
                "a decision carries a whole grant or no grant. A half-populated "
                "record is a refusal that reads as an approval"
            )
        return self


class ElevationExpired(BaseModel):
    """Payload of governance.autonomy.elevation.expired."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    session_id: str
    grant_id: str
    trigger: Literal["question_count", "sim_time", "revoked"]


class ChangeAttribution(BaseModel):
    """The change-attribution audit event E5 requires.

    One record answers who changed what, under whose authority, and against
    which approval. The validator is the reason the record is worth keeping: a
    change above L1 that names no approver cannot be represented, so the trail
    cannot contain an elevated change with nobody attached to it.
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    session_id: str
    question_id: str | None
    tool: str
    target: str
    actor: ActorId
    authority_tier: AutonomyTier
    grant_id: str | None
    approver: ActorId | None
    decision_id: str | None
    before_sha256: str = Field(pattern=_SHA256)
    after_sha256: str = Field(pattern=_SHA256)
    reason: str = Field(min_length=1)

    @model_validator(mode="after")
    def _an_elevated_change_names_the_human_behind_it(self) -> Self:
        if self.authority_tier == AutonomyTier.L1:
            return self
        if self.grant_id is None or self.approver is None or self.decision_id is None:
            raise ValueError(
                f"a change at {self.authority_tier} carries the grant, the approver, "
                f"and the decision it was made under. Attribution that stops at the "
                f"tier is not attribution"
            )
        if self.approver.kind != "human":
            raise ValueError(f"{self.approver.id!r} is an agent and cannot be an approver")
        return self


class AuditLog:
    """The envelope writer for this producer.

    It owns the sequence, which is what makes the log dense per (run, producer)
    rather than dense per process by luck. `VAL-GATE-ENV-001` runs over any log
    carrying these events, so the counter lives in one object rather than in
    each caller.
    """

    def __init__(self, *, run_id: str, clock: SimClockPort, epoch: datetime) -> None:
        self._run_id = run_id
        self._clock = clock
        self._epoch = epoch
        self._seq = 0
        self._events: list[Envelope] = []

    @property
    def events(self) -> tuple[Envelope, ...]:
        """Everything emitted so far, in emission order."""
        return tuple(self._events)

    def emit(
        self,
        event_type: str,
        payload: BaseModel,
        *,
        subject: str | None = None,
        causation_id: str | None = None,
        correlation_id: str | None = None,
    ) -> Envelope:
        """Wrap one payload in the D-07 envelope and append it.

        `time` is derived rather than observed, per envelope invariant E1: it is
        the run epoch plus the sim tick. A wall-clock read here would put a
        machine-dependent value into a log two runs are required to agree on.

        The id is `<run>-<producer>-<seq>`, matching the one deterministic id
        already shipped in twinflow.kernel. Envelope invariant E2 specifies a
        Crockford base32 content hash instead, and this module will import that
        generator when foundations ships it rather than growing a second copy of
        an algorithm foundations owns (D-09).
        """
        ticks = self._clock.now()
        envelope = Envelope(
            specversion="1.0",
            id=f"{self._run_id}-{PRODUCER}-{self._seq}",
            source=SOURCE,
            type=event_type,
            time=self._epoch + timedelta(seconds=ticks / self._clock.tick_hz),
            datacontenttype="application/json",
            dataschema="twinflow:schemas/envelope/v1.json",
            subject=subject,
            twinflowsimts=str(ticks),
            twinflowrunid=self._run_id,
            twinflowproducerid=PRODUCER,
            twinflowseq=str(self._seq),
            twinflowcausationid=causation_id,
            twinflowcorrid=correlation_id,
            data=payload.model_dump(mode="json"),
        )
        self._events.append(envelope)
        self._seq += 1
        return envelope


class AutonomySession:
    """One session's tier, and the only door through which it changes.

    The public surface is deliberately small. `request_elevation` emits an event
    and returns; it does not elevate. `approve` is the single method that raises
    the tier, and every argument it accepts has already been validated into an
    `AutonomyGrant` that a self-elevating caller cannot construct.
    """

    def __init__(
        self,
        *,
        session_id: str,
        audit: AuditLog,
        clock: SimClockPort,
        default_tier: AutonomyTier = AutonomyTier.L1,
        allow_write_tools: bool = False,
        max_grant_questions: int = 20,
        max_grant_sim_seconds: int = 3600,
    ) -> None:
        self.session_id = session_id
        self._audit = audit
        self._clock = clock
        self._default_tier = default_tier
        self._allow_write_tools = allow_write_tools
        self._max_grant_questions = max_grant_questions
        self._max_grant_sim_seconds = max_grant_sim_seconds
        self._grant: AutonomyGrant | None = None
        self._questions_since_grant = 0

    @property
    def default_tier(self) -> AutonomyTier:
        return self._default_tier

    @property
    def grant(self) -> AutonomyGrant | None:
        """The live grant, or None. Reading it settles any pending expiry first."""
        self._expire_if_stale()
        return self._grant

    @property
    def effective_tier(self) -> AutonomyTier:
        """The tier this session holds right now, ignoring scope.

        `allowed_tier_for` is the one the gate uses. This one answers "has the
        session been elevated at all", which is what a status line renders.
        """
        self._expire_if_stale()
        return self._default_tier if self._grant is None else self._grant.granted_tier

    def allowed_tier_for(self, tool: str) -> AutonomyTier:
        """The tier this session holds for one named tool.

        A grant is scoped, so a tool it does not name sits at the default tier
        even while the grant is live. Without this, one approval to apply a
        recommendation would also approve every other write tool in the registry.
        """
        self._expire_if_stale()
        if self._grant is None or tool not in self._grant.scope:
            return self._default_tier
        return self._grant.granted_tier

    def authorize(self, tool: str, required_tier: AutonomyTier) -> AutonomyTier:
        """The tool-permission gate E5 names. Returns the held tier or refuses."""
        held = self.allowed_tier_for(tool)
        if not held.permits(required_tier):
            raise TierRefused(
                f"{tool} needs {required_tier} and this session holds {held}. "
                f"An elevation is requested and approved by a human; it is not "
                f"reached by asking again"
            )
        return held

    def request_elevation(
        self,
        *,
        tool: str,
        needed_tier: AutonomyTier,
        question_id: str,
        requested_by: ActorId,
        reason: str,
    ) -> Envelope:
        """Emit the approval seam. Changes nothing about this session's tier.

        Returning the envelope rather than a grant is the design: a request that
        could yield authority would make the refusal path optional.
        """
        return self._audit.emit(
            ELEVATION_REQUESTED,
            ElevationRequested(
                session_id=self.session_id,
                question_id=question_id,
                tool=tool,
                current_tier=self.effective_tier,
                needed_tier=needed_tier,
                requested_by=requested_by,
                reason=reason,
            ),
        )

    def approve(self, grant: AutonomyGrant) -> Envelope:
        """Install a human-approved grant. The only method that raises the tier.

        The grant already proved it has a human approver who is not the
        requester. What is checked here is the deployment state a grant cannot
        see: which session it belongs to, whether writes are enabled at all, and
        whether it would outlive the configured elevation limits.
        """
        self._expire_if_stale()

        if grant.session_id != self.session_id:
            raise AutonomyError(
                f"grant {grant.grant_id!r} was approved for session "
                f"{grant.session_id!r} and cannot elevate {self.session_id!r}"
            )
        if self._grant is not None:
            raise AutonomyError(
                f"session {self.session_id!r} already holds grant {self._grant.grant_id!r}. "
                f"One live grant per session keeps the effective tier a function of one "
                f"record rather than of the order two were approved in"
            )
        if grant.granted_tier == AutonomyTier.L3 and not self._allow_write_tools:
            raise AutonomyError(
                "an L3 grant also needs autonomy.allow_write_tools in the facility "
                "config, so an operator cannot approve a write the deployment forbids"
            )
        if grant.expires_after_questions > self._max_grant_questions:
            raise AutonomyError(
                f"grant expires after {grant.expires_after_questions} questions, past the "
                f"configured limit of {self._max_grant_questions}"
            )
        horizon = self._max_grant_sim_seconds * self._clock.tick_hz
        if grant.expires_at_sim_time > self._clock.now() + horizon:
            raise AutonomyError(
                f"grant expires at sim time {grant.expires_at_sim_time}, past the configured "
                f"age of {self._max_grant_sim_seconds} sim seconds. There is no renewal path "
                f"that skips a fresh approval, so this is refused rather than clamped"
            )

        self._grant = grant
        self._questions_since_grant = 0
        return self._audit.emit(
            ELEVATION_DECIDED,
            ElevationDecided(
                session_id=self.session_id,
                grant_id=grant.grant_id,
                granted_tier=grant.granted_tier,
                approver=grant.approver,
                scope=grant.scope,
                expires_after_questions=grant.expires_after_questions,
                expires_at_sim_time=grant.expires_at_sim_time,
                decision_id=grant.decision_id,
                reason=grant.reason,
            ),
        )

    def refuse(self, grant: AutonomyGrant, *, approver: ActorId, reason: str) -> Envelope:
        """Record a human declining an elevation. Leaves the tier where it was."""
        if approver.kind != "human":
            raise AutonomyError(f"{approver.id!r} is an agent and cannot decide an elevation")
        return self._audit.emit(
            ELEVATION_DECIDED,
            ElevationDecided(
                session_id=self.session_id,
                grant_id=None,
                granted_tier=None,
                approver=approver,
                scope=(),
                expires_after_questions=None,
                expires_at_sim_time=None,
                decision_id=None,
                reason=reason,
            ),
        )

    def revoke(self) -> Envelope | None:
        """Return the session to its default tier before either limit arrives."""
        return self._retire("revoked")

    def note_question(self) -> Envelope | None:
        """Count one question against the live grant, expiring it at the limit."""
        self._expire_if_stale()
        if self._grant is None:
            return None
        self._questions_since_grant += 1
        if self._questions_since_grant >= self._grant.expires_after_questions:
            return self._retire("question_count")
        return None

    def attribute_change(
        self,
        *,
        tool: str,
        target: str,
        actor: ActorId,
        before_sha256: str,
        after_sha256: str,
        reason: str,
        question_id: str | None = None,
        required_tier: AutonomyTier | None = None,
    ) -> Envelope:
        """Record one change against the authority it was actually made under.

        The tier is read from this session, never taken from the caller. A tool
        that could name its own authority in the audit trail would make the
        trail worth nothing, since the one thing a reader needs from it is the
        part the actor cannot choose.
        """
        if required_tier is not None:
            self.authorize(tool, required_tier)
        held = self.allowed_tier_for(tool)
        elevated = held != self._default_tier and self._grant is not None
        return self._audit.emit(
            CHANGE_ATTRIBUTED,
            ChangeAttribution(
                session_id=self.session_id,
                question_id=question_id,
                tool=tool,
                target=target,
                actor=actor,
                authority_tier=held,
                grant_id=self._grant.grant_id if elevated else None,
                approver=self._grant.approver if elevated else None,
                decision_id=self._grant.decision_id if elevated else None,
                before_sha256=before_sha256,
                after_sha256=after_sha256,
                reason=reason,
            ),
        )

    # -- internals ---------------------------------------------------------

    def _expire_if_stale(self) -> None:
        """Retire a grant whose sim-time limit has passed.

        Expiry is evaluated on read rather than driven by a timer, because a
        timer is a second clock and the point of the injected port is that there
        is only one.
        """
        if self._grant is not None and self._clock.now() >= self._grant.expires_at_sim_time:
            self._retire("sim_time")

    def _retire(self, trigger: Literal["question_count", "sim_time", "revoked"]) -> Envelope | None:
        if self._grant is None:
            return None
        grant = self._grant
        self._grant = None
        self._questions_since_grant = 0
        return self._audit.emit(
            ELEVATION_EXPIRED,
            ElevationExpired(session_id=self.session_id, grant_id=grant.grant_id, trigger=trigger),
        )
