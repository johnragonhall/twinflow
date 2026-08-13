"""The agent tool surface, schema-constrained (requirement 7, E26d, ARCH-5).

docs/design/ai-layer.md sections 3.3 and 5.2 own the shape here: a `ToolSpec`
carries an args model, a result model, a minimum autonomy tier, a declared
side-effect class, and a simulation budget where it runs experiments. This
module ships that registry and the first of the nine tools, `query_metric`.

What E26d actually requires
---------------------------
The accuracy stack's structured-output layer says a malformed tool call is
impossible by construction, not merely discouraged. Three things make that true
here rather than aspirational.

    1. Constructing a `ToolCall` is the validation. There is no second path that
       stores raw arguments and checks them later, so an unvalidated call is not
       a state this module can be in.
    2. `ToolRegistry.register` refuses an args model that tolerates unknown keys.
       Without that, a misspelled argument would be silently dropped and the
       tool would answer a question nobody asked, which is the failure mode the
       layer exists to remove.
    3. `ToolRegistry.register` refuses a result model with no `result_ids`, so
       every number a tool produces has somewhere to enter the ledger. A result
       that cannot be cited cannot be grounded.

ARCH-5, and why Pydantic AI is not imported (ADR-0002)
------------------------------------------------------
ARCHITECTURE.md decision D9 selects Pydantic AI for the provider abstraction and
the validation-retry structured-output guarantee, and D10 pairs it with a local
Ollama path so the demo runs with no API key. This module implements the
structured-output guarantee on pydantic alone, behind the named seam
`StructuredOutputAdapter`, and the later half of the agent runtime swaps the
implementation without touching the tool surface. The reason is a license
constraint rather than a preference, and it was measured rather than assumed.

Resolving pydantic-ai 2.27.0 against the Python Package Index on 2026-08-13
yields 100 distributions, and resolving the bare `pydantic-ai-slim` still yields
20. Both trees contain `certifi`, which is MPL-2.0 and reaches the tree through
httpx as a run-time dependency. The allowlist in CONTRIBUTING.md carries two
MPL-2.0 rows, and the one that applies reads "Shipped at run time | Refused",
because the file-level condition would travel to anyone who installs a twinflow
package. `VAL-GATE-SEC-001` names that allowlist. The full tree adds four more
SPDX ids with no row at all. Adopting the framework is therefore a decision for
the allowlist, not for this work package, and it is reported upward rather than
taken here.

The seam is real and the guarantee is real without it. `PydanticStructuredOutput`
performs the same validate-then-retry loop D9 describes, and
`twinflow.agent.local_model.OllamaStructuredOutput` fills the same seam with the
constrained decoding D10 asks for, on the standard library alone. ADR-0002
records the decision, what it costs, and what would reopen it.

Determinism. Nothing here reads a clock, draws a random number, or iterates an
unordered collection: `names()` and `allowed()` sort, and the argument digest is
computed over canonical JSON with sorted keys, so the value recorded in
`agent.tool.invoked` is a function of the arguments alone.
"""

from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Callable
from decimal import Decimal
from enum import StrEnum
from pathlib import Path
from typing import Any, Literal, Protocol, Self, TypeVar, final, runtime_checkable

from pydantic import BaseModel, ConfigDict, Field, ValidationError, model_validator

from twinflow.agent.autonomy import AutonomyTier, TierRefused
from twinflow.config import METRIC_ID, load_metrics, nearest

ModelT = TypeVar("ModelT", bound=BaseModel)

#: The one tool this work package ships. The other eight of section 5.2 arrive
#: with the subsystems that produce their numbers.
QUERY_METRIC = "query_metric"

#: A tool name is a python-ish identifier because it is also an MCP tool name and
#: a REST path segment, and those three spellings have to be one string.
TOOL_NAME = re.compile(r"^[a-z][a-z0-9_]*$")

#: `sim_budget` names a budget key in the facility config rather than carrying a
#: Budget value. `Budget` is owned by twinflow-governance, and redeclaring it
#: here would give one concept two definitions (D-09). The ledger resolves the
#: key; the spec only says which budget applies.
BUDGET_KEY = re.compile(r"^per_[a-z][a-z0-9_]*$")


class ToolError(Exception):
    """A tool refused to run. Contributes nothing to the ledger, per section 5.2."""


class ToolSpecError(Exception):
    """A tool was declared in a way the registry cannot make safe."""


class SideEffect(StrEnum):
    """What a call changes outside the run. Not the same axis as authority."""

    NONE = "none"
    SIMULATE = "simulate"
    WRITE_CONFIG = "write_config"


class CostClass(StrEnum):
    """Roughly what a call costs. Used by the router, never by the gate."""

    CHEAP = "cheap"
    SIM = "sim"
    HEAVY = "heavy"


class ToolSpec(BaseModel):
    """One tool's contract, with the section 3.3 invariants enforced on it.

    Authority and resource cost are separate axes and this model keeps them
    separate. `tier` answers who may change the world; `sim_budget` answers what
    an experiment may consume. Running a simulation changes nothing outside the
    run, so it is L1 with a budget rather than L2 with none.
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    name: str = Field(pattern=TOOL_NAME.pattern)
    args_model: type[BaseModel]
    result_model: type[BaseModel]
    tier: AutonomyTier
    side_effects: SideEffect
    cost_class: CostClass
    sim_budget: str | None = Field(default=None, pattern=BUDGET_KEY.pattern)
    deadline_sim_s: int = Field(ge=1)
    description: str = Field(min_length=1)
    since_version: str = Field(pattern=r"^\d+\.\d+\.\d+$")

    @model_validator(mode="after")
    def _side_effects_agree_with_tier_and_budget(self) -> Self:
        """The three invariants of section 3.3, stated as one refusal each."""
        if self.side_effects is SideEffect.WRITE_CONFIG:
            if self.tier is not AutonomyTier.L3:
                raise ValueError(
                    f"{self.name!r} writes config, so it is L3. A write reachable below "
                    f"L3 is the gate E5 asks for, absent"
                )
            if self.sim_budget is not None:
                raise ValueError(f"{self.name!r} writes config and runs no experiment")
        elif self.side_effects is SideEffect.SIMULATE:
            if self.tier is not AutonomyTier.L1:
                raise ValueError(
                    f"{self.name!r} runs an experiment against a copy of the config, which "
                    f"changes nothing in the world. Gating it on authority is a category "
                    f"error, and it would put the headline demo behind a flag the shipped "
                    f"config turns off"
                )
            if self.sim_budget is None:
                raise ValueError(
                    f"{self.name!r} consumes compute, which is a budget question. A simulate "
                    f"tool with no sim_budget cannot be denied on exhaustion"
                )
        elif self.tier is not AutonomyTier.L1 or self.sim_budget is not None:
            raise ValueError(
                f"{self.name!r} has no side effects, so it is L1 and carries no sim_budget"
            )
        return self


@final
class ToolCall:
    """A tool name bound to arguments that have already validated.

    Not a pydantic model, and that is the point. A model could be constructed
    with an `args` value of the wrong type and would need a validator to notice.
    Here the constructor is the validation: `ToolCall(spec, raw)` either returns
    a call whose arguments match the spec or raises `ValidationError`. There is
    no third outcome, which is what E26d means by impossible by construction.
    """

    __slots__ = ("_args", "_args_sha256", "_spec")

    def __init__(self, spec: ToolSpec, raw_args: object) -> None:
        args = spec.args_model.model_validate(raw_args)
        object.__setattr__(self, "_spec", spec)
        object.__setattr__(self, "_args", args)
        object.__setattr__(self, "_args_sha256", _canonical_sha256(args))

    def __setattr__(self, name: str, value: object) -> None:
        raise AttributeError(
            f"a ToolCall is settled at construction; {name!r} cannot be reassigned"
        )

    @property
    def spec(self) -> ToolSpec:
        return self._spec

    @property
    def tool(self) -> str:
        return self._spec.name

    @property
    def tier(self) -> AutonomyTier:
        """The minimum tier this call needs, read from the spec rather than
        supplied by the caller."""
        return self._spec.tier

    @property
    def args(self) -> BaseModel:
        return self._args

    @property
    def args_sha256(self) -> str:
        """The digest `agent.tool.invoked` carries. A function of the validated
        arguments, so two spellings of one call hash the same."""
        return self._args_sha256

    def __repr__(self) -> str:
        return f"ToolCall({self.tool!r}, args_sha256={self._args_sha256[:12]}...)"


@final
class ToolResult:
    """What a tool returned, validated against the result model it declared.

    A tool that returns a schema-invalid result contributes nothing to the
    ledger (section 5.2), and this is where that is decided.
    """

    __slots__ = ("_call", "_value")

    def __init__(self, call: ToolCall, raw_result: object) -> None:
        value = call.spec.result_model.model_validate(raw_result)
        object.__setattr__(self, "_call", call)
        object.__setattr__(self, "_value", value)

    def __setattr__(self, name: str, value: object) -> None:
        raise AttributeError(f"a ToolResult is settled at construction; {name!r} is read only")

    @property
    def call(self) -> ToolCall:
        return self._call

    @property
    def value(self) -> Any:
        return self._value

    @property
    def result_ids(self) -> tuple[str, ...]:
        """The ledger entries this result contributed."""
        return tuple(self._value.result_ids)


@runtime_checkable
class StructuredOutputAdapter(Protocol):
    """The ARCH-5 seam: turn an untrusted emission into a validated model.

    One method, because one method is what D9 buys. A Pydantic AI agent with an
    `output_type`, and a locally constrained decoder under D10, both satisfy this
    shape, so swapping the implementation is a constructor argument rather than a
    change to any tool.
    """

    def structured(
        self,
        model: type[ModelT],
        emit: Callable[[str | None], object],
        *,
        max_retries: int,
    ) -> ModelT:
        """Return a validated instance of `model`, or raise. Never anything else.

        `emit` is called with None first and with the validation error text on
        each retry, which is the repair signal D9's validation-retry depends on.
        """
        ...


class PydanticStructuredOutput:
    """The shipped adapter. Validate, and on failure re-emit with the error.

    This is D9's validation-retry without D9's dependency. It is deliberately
    small: the whole loop is visible in one screen, which is what ARCH-5 means by
    thin and inspectable.
    """

    def structured(
        self,
        model: type[ModelT],
        emit: Callable[[str | None], object],
        *,
        max_retries: int = 2,
    ) -> ModelT:
        if max_retries < 0:
            raise ValueError("max_retries cannot be negative")
        feedback: str | None = None
        for attempt in range(max_retries + 1):
            try:
                return model.model_validate(emit(feedback))
            except ValidationError as error:
                # Raising the last failure rather than returning a partial value
                # is the guarantee. An adapter that degraded to "best effort" on
                # the final attempt would undo every refusal above it, so the
                # exhausted branch re-raises rather than falling out of the loop.
                if attempt == max_retries:
                    raise
                feedback = _repair_prompt(model, error)
        raise AssertionError("unreachable: the loop returns or raises on every attempt")


class ToolRegistry:
    """The one registry MCP, REST, and the agent runtime all read (A6).

    `json_schemas` is the single source of truth for the tool descriptions three
    surfaces publish. Two hand-maintained copies would eventually disagree, and
    the one that disagreed would be the one an external client trusted.
    """

    def __init__(self) -> None:
        self._specs: dict[str, ToolSpec] = {}
        self._fns: dict[str, Callable[[Any], Any]] = {}

    def register(self, spec: ToolSpec, fn: Callable[[Any], Any]) -> None:
        """Add one tool, refusing any declaration that would weaken E26d."""
        if spec.name in self._specs:
            raise ToolSpecError(
                f"{spec.name!r} is already registered. One name is one contract, so a "
                f"second registration would make which one answers depend on import order"
            )
        if spec.args_model.model_config.get("extra") != "forbid":
            raise ToolSpecError(
                f"{spec.name!r} declares an args model that tolerates unknown keys. A "
                f"misspelled argument would be dropped and the tool would answer a "
                f'different question, so extra="forbid" is required rather than advised'
            )
        if "result_ids" not in spec.result_model.model_fields:
            raise ToolSpecError(
                f"{spec.name!r} declares a result model with no result_ids. Every result "
                f"model carries them so its numbers enter the ledger, and a number that "
                f"cannot be cited cannot be grounded"
            )
        self._specs[spec.name] = spec
        self._fns[spec.name] = fn

    def spec(self, name: str) -> ToolSpec:
        try:
            return self._specs[name]
        except KeyError:
            hint = nearest(name, sorted(self._specs))
            raise ToolError(
                f"no tool named {name!r}" + (f". Did you mean {hint!r}?" if hint else "")
            ) from None

    def names(self) -> tuple[str, ...]:
        """Every registered tool, sorted (D-03)."""
        return tuple(sorted(self._specs))

    def allowed(self, tier: AutonomyTier) -> tuple[str, ...]:
        """The tools a session at this tier may call, sorted."""
        return tuple(sorted(n for n, s in self._specs.items() if tier.permits(s.tier)))

    def json_schemas(self) -> dict[str, dict[str, Any]]:
        """The published contract per tool: args schema, result schema, metadata."""
        return {
            name: {
                "args": spec.args_model.model_json_schema(),
                "result": spec.result_model.model_json_schema(),
                "tier": str(spec.tier),
                "side_effects": str(spec.side_effects),
                "cost_class": str(spec.cost_class),
                "sim_budget": spec.sim_budget,
                "deadline_sim_s": spec.deadline_sim_s,
                "description": spec.description,
                "since_version": spec.since_version,
            }
            for name, spec in sorted(self._specs.items())
        }

    def bind(self, name: str, raw_args: object) -> ToolCall:
        """Validate arguments against the named tool. The ordinary entry point."""
        return ToolCall(self.spec(name), raw_args)

    def bind_structured(
        self,
        name: str,
        emit: Callable[[str | None], object],
        *,
        adapter: StructuredOutputAdapter,
        max_retries: int = 2,
    ) -> ToolCall:
        """Bind a call from a model emission, retrying on a schema failure.

        The entry point a planner uses. It returns the same `ToolCall` the
        deterministic path returns, so nothing downstream can tell whether the
        arguments came from a model or from a test fixture.
        """
        spec = self.spec(name)
        return ToolCall(spec, adapter.structured(spec.args_model, emit, max_retries=max_retries))

    def invoke(self, call: ToolCall, *, tier: AutonomyTier) -> ToolResult:
        """Run one validated call at one held tier.

        The tier check is here as well as in `AutonomySession.authorize` on
        purpose: the session owns scope and expiry, and this owns the floor, so a
        caller that reached the registry without a session still cannot run an
        L3 tool from an L1 context.
        """
        if not tier.permits(call.tier):
            raise TierRefused(f"{call.tool} needs {call.tier} and the caller holds {tier}")
        return ToolResult(call, self._fns[call.tool](call.args))


# --------------------------------------------------------------------------
# query_metric, the first of the nine tools
# --------------------------------------------------------------------------


class MetricFilter(BaseModel):
    """One predicate over a declared dimension."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    dimension: str = Field(pattern=r"^[a-z][a-z0-9_]*$")
    op: Literal["eq", "ne", "lt", "lte", "gt", "gte", "in"]
    value: str | int | float | tuple[str, ...]


class TimeWindow(BaseModel):
    """A half-open window in sim ticks.

    Sim ticks rather than timestamps, per foundations invariant T1. A wall-clock
    window would make the same question return different rows on a machine whose
    clock had drifted.
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    start_sim_ticks: int = Field(ge=0)
    end_sim_ticks: int = Field(ge=0)

    @model_validator(mode="after")
    def _the_window_moves_forward(self) -> Self:
        if self.end_sim_ticks <= self.start_sim_ticks:
            raise ValueError(
                f"window ends at {self.end_sim_ticks} and starts at {self.start_sim_ticks}"
            )
        return self


class MetricSelection(BaseModel):
    """The args model of `query_metric`, as section 5.2 names it."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    metric: str = Field(pattern=METRIC_ID.pattern)
    time_window: TimeWindow
    dimensions: tuple[str, ...] = ()
    filters: tuple[MetricFilter, ...] = ()
    grain: str | None = None
    limit: int = Field(default=100, ge=1, le=5000)


class MetricDefinitionEcho(BaseModel):
    """The governed definition, echoed from the registry rather than restated.

    Echoing matters: an answer that quoted a unit the registry does not carry
    would be ungroundable, and the mismatch would surface as a wrong number
    rather than as an error.
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    id: str
    title: str
    unit: str
    grain: tuple[str, ...]
    direction: Literal["higher_is_better", "lower_is_better", "target_is_best"]
    precision: int
    owner: str
    since: str
    status: str


class MetricQueryResult(BaseModel):
    """The result model of `query_metric`.

    It follows the "result fields that outrun their producers" rule of section
    5.2. The expression evaluator belongs to the semantics layer, which lands
    later, so the value is absent and the record says which requirement supplies
    it. `test_kpi_delta_coverage` asks that such a field never resolve to a
    missing key and never to a zero, and the validator below is what makes a
    measured zero standing in for a missing number unrepresentable.
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    metric: MetricDefinitionEcho
    status: Literal["measured", "awaiting_subsystem"]
    required_by: str | None
    value: Decimal | None
    dimensions: tuple[str, ...] = ()
    rows_scanned: int = Field(default=0, ge=0)
    result_ids: tuple[str, ...] = ()

    @model_validator(mode="after")
    def _the_two_states_are_exclusive(self) -> Self:
        if self.status == "measured":
            if self.value is None:
                raise ValueError("a measured result carries a value")
            if self.required_by is not None:
                raise ValueError("a measured result waits on nothing")
        else:
            if self.value is not None:
                raise ValueError(
                    "a result awaiting a subsystem carries no value. A zero here would "
                    "read as a measurement"
                )
            if self.required_by is None:
                raise ValueError("a result awaiting a subsystem names the requirement it waits on")
        return self


def query_metric(
    selection: MetricSelection,
    *,
    metrics_path: str | Path,
    schemas_root: Path | None = None,
) -> MetricQueryResult:
    """Resolve one metric against the governed registry (E26b).

    This tool reads the metrics layer rather than computing a number inline, and
    the difference is the whole requirement. An id the registry does not declare
    is a refusal with a suggestion, not an empty result set; a dimension outside
    the declared grain is a refusal, not a slice nobody governs.
    """
    document, _diagnostics = load_metrics(metrics_path, schemas_root=schemas_root)
    return _resolve(selection, document)


def _resolve(selection: MetricSelection, document: Any) -> MetricQueryResult:
    declared = [m for m in (document.get("metrics") or []) if m.get("id")]
    by_id = {str(m["id"]): m for m in declared}

    metric = by_id.get(selection.metric)
    if metric is None:
        hint = nearest(selection.metric, sorted(by_id))
        raise ToolError(
            f"metric {selection.metric!r} is not declared in the registry"
            + (f". Did you mean {hint!r}?" if hint else "")
        )

    grain = tuple(str(g) for g in metric.get("grain") or ())
    outside = tuple(d for d in selection.dimensions if d not in grain)
    if outside:
        raise ToolError(
            f"metric {selection.metric!r} declares grain {grain} and cannot be sliced by "
            f"{outside}. The grain is the governed answer to what this may be sliced by"
        )
    if selection.grain is not None and selection.grain not in grain:
        raise ToolError(
            f"metric {selection.metric!r} has no grain {selection.grain!r}, only {grain}"
        )

    return MetricQueryResult(
        metric=MetricDefinitionEcho(
            id=str(metric["id"]),
            title=str(metric["title"]),
            unit=str(metric["unit"]),
            grain=grain,
            direction=str(metric["direction"]),  # type: ignore[arg-type]
            precision=int(metric["precision"]),
            owner=str(metric["owner"]),
            since=str(metric["since"]),
            status=str(metric.get("status") or "active"),
        ),
        status="awaiting_subsystem",
        required_by="E26",
        value=None,
        dimensions=selection.dimensions,
        rows_scanned=0,
        result_ids=(),
    )


QUERY_METRIC_SPEC = ToolSpec(
    name=QUERY_METRIC,
    args_model=MetricSelection,
    result_model=MetricQueryResult,
    tier=AutonomyTier.L1,
    side_effects=SideEffect.NONE,
    cost_class=CostClass.CHEAP,
    sim_budget=None,
    deadline_sim_s=30,
    description=(
        "Resolve one governed metric over a sim-time window. Reads the metrics "
        "registry; computes nothing inline."
    ),
    since_version="0.1.0",
)


def build_default_registry(
    *, metrics_path: str | Path, schemas_root: Path | None = None
) -> ToolRegistry:
    """The registry the agent runtime, MCP, and REST all start from.

    The registry is loaded once and closed over rather than read per call, so a
    hundred tool calls in one session parse the file once and every call in that
    session sees one version of the governed layer.
    """
    document, _diagnostics = load_metrics(metrics_path, schemas_root=schemas_root)
    registry = ToolRegistry()
    registry.register(QUERY_METRIC_SPEC, lambda args: _resolve(args, document))
    return registry


# --------------------------------------------------------------------------
# internals
# --------------------------------------------------------------------------


def _canonical_sha256(model: BaseModel) -> str:
    """A digest over canonical JSON: sorted keys, no incidental whitespace.

    Sorted rather than declaration-ordered so the value survives a field being
    reordered in the model, which is a change no recorded run should notice.
    """
    payload = json.dumps(
        model.model_dump(mode="json"), sort_keys=True, separators=(",", ":"), ensure_ascii=False
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _repair_prompt(model: type[BaseModel], error: ValidationError) -> str:
    """The feedback an emitter gets after a schema failure.

    It names the fields rather than pasting the whole schema, because the retry
    exists to fix a specific miss and a full schema restates what the emitter
    already had.
    """
    problems = "; ".join(
        f"{'.'.join(str(p) for p in item['loc']) or '<root>'}: {item['msg']}"
        for item in error.errors()
    )
    return f"{model.__name__} rejected that emission: {problems}. Emit {model.__name__} again."
