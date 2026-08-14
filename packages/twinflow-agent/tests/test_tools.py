"""Requirement 7 (one tool) and E26d, the structured-output layer.

The claim under test is narrow and strong: a malformed tool call cannot be
represented. Every assertion here is an attempt to build one, so the suite fails
the moment the surface starts merely discouraging bad calls instead of refusing
them.
"""

from __future__ import annotations

from decimal import Decimal

import pytest
from pydantic import BaseModel, ConfigDict, ValidationError

from twinflow.agent.autonomy import AutonomyTier, TierRefused
from twinflow.agent.tools import (
    QUERY_METRIC,
    CostClass,
    MetricSelection,
    PydanticStructuredOutput,
    SideEffect,
    TimeWindow,
    ToolCall,
    ToolError,
    ToolRegistry,
    ToolResult,
    ToolSpec,
    ToolSpecError,
    build_default_registry,
    query_metric,
)

METRICS = "profiles/starter_dc.metrics.yaml"


def selection(**overrides: object) -> MetricSelection:
    kwargs: dict[str, object] = {
        "metric": "twin.throughput.units_per_hour",
        "time_window": TimeWindow(start_sim_ticks=0, end_sim_ticks=3_600_000_000),
    }
    kwargs.update(overrides)
    return MetricSelection(**kwargs)  # type: ignore[arg-type]


@pytest.fixture
def registry(repo_root):
    return build_default_registry(metrics_path=repo_root / METRICS)


# --------------------------------------------------------------------------
# E26d. A malformed call is unrepresentable.
# --------------------------------------------------------------------------


def test_an_unknown_argument_is_refused_rather_than_ignored(registry):
    """extra="forbid" is the difference between a typo that changes the answer
    and a typo that fails."""
    with pytest.raises(ValidationError):
        registry.bind(
            QUERY_METRIC,
            {
                "metric": "twin.throughput.units_per_hour",
                "time_window": {"start_sim_ticks": 0, "end_sim_ticks": 10},
                "limitt": 5,
            },
        )


def test_a_missing_required_argument_is_refused(registry):
    with pytest.raises(ValidationError):
        registry.bind(QUERY_METRIC, {"metric": "twin.throughput.units_per_hour"})


def test_an_argument_of_the_wrong_type_is_refused(registry):
    with pytest.raises(ValidationError):
        registry.bind(
            QUERY_METRIC,
            {
                "metric": "twin.throughput.units_per_hour",
                "time_window": {"start_sim_ticks": 0, "end_sim_ticks": 10},
                "limit": "all of them",
            },
        )


def test_a_metric_id_outside_the_governed_grammar_is_refused(registry):
    with pytest.raises(ValidationError):
        registry.bind(
            QUERY_METRIC,
            {
                "metric": "Throughput",
                "time_window": {"start_sim_ticks": 0, "end_sim_ticks": 10},
            },
        )


def test_a_tool_call_cannot_be_built_around_an_unvalidated_payload():
    """Constructing a ToolCall is the validation. There is no second path that
    stores raw arguments and checks them later."""
    spec = ToolSpec.model_validate(
        {
            "name": "query_metric",
            "args_model": MetricSelection,
            "result_model": _Result,
            "tier": AutonomyTier.L1,
            "side_effects": SideEffect.NONE,
            "cost_class": CostClass.CHEAP,
            "sim_budget": None,
            "deadline_sim_s": 30,
            "description": "d",
            "since_version": "0.1.0",
        }
    )
    with pytest.raises(ValidationError):
        ToolCall(spec, {"metric": "nope"})


def test_a_tool_call_is_immutable_once_built(registry):
    call = registry.bind(QUERY_METRIC, selection())
    with pytest.raises(AttributeError):
        call.args = None  # type: ignore[misc]


def test_the_argument_digest_is_a_function_of_the_validated_arguments(registry):
    """agent.tool.invoked carries args_sha256, so two spellings of one call have
    to hash the same and two different calls must not."""
    a = registry.bind(QUERY_METRIC, selection())
    b = registry.bind(
        QUERY_METRIC,
        {
            "time_window": {"start_sim_ticks": 0, "end_sim_ticks": 3_600_000_000},
            "metric": "twin.throughput.units_per_hour",
        },
    )
    c = registry.bind(QUERY_METRIC, selection(limit=7))
    assert a.args_sha256 == b.args_sha256
    assert a.args_sha256 != c.args_sha256
    assert len(a.args_sha256) == 64


def test_a_result_that_does_not_match_the_declared_model_is_refused(registry):
    call = registry.bind(QUERY_METRIC, selection())
    with pytest.raises(ValidationError):
        ToolResult(call, {"metric": "not a metric definition"})


# --------------------------------------------------------------------------
# The ARCH-5 seam
# --------------------------------------------------------------------------


def test_the_structured_adapter_retries_a_malformed_emission_and_returns_a_validated_model():
    """D9's validation-retry, on the seam Pydantic AI or a constrained decoder
    fills later. The first emission is malformed; the second is not."""
    emissions = [
        {"metric": "not a metric id"},
        {
            "metric": "twin.throughput.units_per_hour",
            "time_window": {"start_sim_ticks": 0, "end_sim_ticks": 10},
        },
    ]
    seen: list[str | None] = []

    def emit(feedback: str | None) -> object:
        seen.append(feedback)
        return emissions[len(seen) - 1]

    out = PydanticStructuredOutput().structured(MetricSelection, emit, max_retries=2)

    assert isinstance(out, MetricSelection)
    assert seen[0] is None
    assert seen[1] is not None and "metric" in seen[1]


def test_the_structured_adapter_gives_up_rather_than_returning_something_unvalidated():
    def emit(_feedback: str | None) -> object:
        return {"metric": "still wrong"}

    with pytest.raises(ValidationError):
        PydanticStructuredOutput().structured(MetricSelection, emit, max_retries=2)


def test_binding_through_the_adapter_yields_a_validated_call(registry):
    emissions = [
        {"metric": "wrong"},
        {
            "metric": "twin.throughput.units_per_hour",
            "time_window": {"start_sim_ticks": 0, "end_sim_ticks": 10},
        },
    ]
    calls = iter(emissions)
    call = registry.bind_structured(
        QUERY_METRIC,
        lambda _feedback: next(calls),
        adapter=PydanticStructuredOutput(),
        max_retries=2,
    )
    assert isinstance(call, ToolCall)
    assert call.args.metric == "twin.throughput.units_per_hour"


# --------------------------------------------------------------------------
# ToolSpec invariants, section 3.3
# --------------------------------------------------------------------------


class _Result(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    result_ids: tuple[str, ...] = ()


class _Loose(BaseModel):
    """An args model that tolerates unknown keys, which is the defect the
    registry refuses at registration."""

    model_config = ConfigDict(extra="ignore")
    metric: str = ""


def _spec(**overrides: object) -> ToolSpec:
    kwargs: dict[str, object] = {
        "name": "some_tool",
        "args_model": MetricSelection,
        "result_model": _Result,
        "tier": AutonomyTier.L1,
        "side_effects": SideEffect.NONE,
        "cost_class": CostClass.CHEAP,
        "sim_budget": None,
        "deadline_sim_s": 30,
        "description": "d",
        "since_version": "0.1.0",
    }
    kwargs.update(overrides)
    return ToolSpec.model_validate(kwargs)


def test_a_write_config_tool_below_l3_is_refused():
    with pytest.raises(ValidationError):
        _spec(side_effects=SideEffect.WRITE_CONFIG, tier=AutonomyTier.L1)


def test_a_simulate_tool_without_a_sim_budget_is_refused():
    with pytest.raises(ValidationError):
        _spec(side_effects=SideEffect.SIMULATE, sim_budget=None, cost_class=CostClass.SIM)


def test_a_simulate_tool_above_l1_is_refused():
    """Authority and resource cost are separate axes. Gating an experiment on
    authority is the category error section 5.2 names."""
    with pytest.raises(ValidationError):
        _spec(
            side_effects=SideEffect.SIMULATE,
            sim_budget="per_whatif",
            cost_class=CostClass.SIM,
            tier=AutonomyTier.L2,
        )


def test_a_side_effect_free_tool_carrying_a_sim_budget_is_refused():
    with pytest.raises(ValidationError):
        _spec(side_effects=SideEffect.NONE, sim_budget="per_whatif")


def test_a_write_config_tool_at_l3_with_no_sim_budget_is_accepted():
    spec = _spec(
        name="apply_change",
        side_effects=SideEffect.WRITE_CONFIG,
        tier=AutonomyTier.L3,
        sim_budget=None,
    )
    assert spec.tier == AutonomyTier.L3


def test_registration_refuses_an_args_model_that_tolerates_unknown_keys():
    """Without this, "impossible by construction" degrades to "discouraged"."""
    r = ToolRegistry()
    with pytest.raises(ToolSpecError):
        r.register(_spec(args_model=_Loose), lambda args: _Result())


def test_registration_refuses_a_result_model_that_cannot_reach_the_ledger():
    """Section 5.2: every result model carries result_ids so its numbers enter
    the ledger."""

    class _NoIds(BaseModel):
        model_config = ConfigDict(extra="forbid")

    r = ToolRegistry()
    with pytest.raises(ToolSpecError):
        r.register(_spec(result_model=_NoIds), lambda args: _NoIds())


def test_registering_one_name_twice_is_refused():
    r = ToolRegistry()
    r.register(_spec(), lambda args: _Result())
    with pytest.raises(ToolSpecError):
        r.register(_spec(), lambda args: _Result())


# --------------------------------------------------------------------------
# The registry as the single source of truth for MCP and REST
# --------------------------------------------------------------------------


def test_the_registry_publishes_one_json_schema_per_tool(registry):
    schemas = registry.json_schemas()
    assert QUERY_METRIC in schemas
    assert schemas[QUERY_METRIC]["args"]["additionalProperties"] is False
    assert "result_ids" in schemas[QUERY_METRIC]["result"]["properties"]


def test_the_names_and_the_allowed_list_are_sorted(registry):
    """Doctrine D-03. An iteration order that varies reaches a prompt, and a
    prompt reaches a recorded transcript."""
    registry.register(
        _spec(name="apply_change", side_effects=SideEffect.WRITE_CONFIG, tier=AutonomyTier.L3),
        lambda args: _Result(),
    )
    assert list(registry.names()) == sorted(registry.names())
    assert list(registry.allowed(AutonomyTier.L1)) == [QUERY_METRIC]
    assert list(registry.allowed(AutonomyTier.L3)) == sorted(["apply_change", QUERY_METRIC])


def test_the_shipped_default_tier_reaches_the_shipped_tool(registry):
    """Section 3.3, last invariant: a tier change that hides the headline tool
    is a defect, not a configuration choice."""
    assert QUERY_METRIC in registry.allowed(AutonomyTier.L1)


def test_invoking_above_the_granted_tier_is_refused(registry):
    registry.register(
        _spec(name="apply_change", side_effects=SideEffect.WRITE_CONFIG, tier=AutonomyTier.L3),
        lambda args: _Result(),
    )
    call = registry.bind("apply_change", selection())
    with pytest.raises(TierRefused):
        registry.invoke(call, tier=AutonomyTier.L1)


# --------------------------------------------------------------------------
# query_metric reads the governed metrics layer
# --------------------------------------------------------------------------


def test_query_metric_echoes_the_governed_definition_rather_than_inventing_one(repo_root):
    result = query_metric(selection(), metrics_path=repo_root / METRICS)
    assert result.metric.id == "twin.throughput.units_per_hour"
    assert result.metric.unit == "1/hour"
    assert result.metric.direction == "higher_is_better"
    assert result.metric.owner == "twinflow-twin"


def test_query_metric_refuses_a_metric_the_registry_does_not_declare(repo_root):
    with pytest.raises(ToolError) as excinfo:
        query_metric(
            selection(metric="twin.throughput.units_per_hr"), metrics_path=repo_root / METRICS
        )
    assert "twin.throughput.units_per_hour" in str(excinfo.value)


def test_query_metric_refuses_a_dimension_outside_the_declared_grain(repo_root):
    """The grain is the governed answer to "what may this be sliced by". A tool
    that sliced by anything would be computing a number inline."""
    with pytest.raises(ToolError):
        query_metric(selection(dimensions=("color",)), metrics_path=repo_root / METRICS)


def test_query_metric_states_the_subsystem_it_is_waiting_on_rather_than_returning_zero(repo_root):
    """Section 5.2, "result fields that outrun their producers". The evaluator
    lands with the semantics layer, so the value is absent and says why."""
    result = query_metric(selection(), metrics_path=repo_root / METRICS)
    assert result.status == "awaiting_subsystem"
    assert result.value is None
    assert result.required_by == "E26"


def test_a_measured_result_without_a_value_is_unrepresentable(repo_root):
    """The two states are exclusive, so no reader ever sees a measured zero
    standing in for a missing number."""
    result = query_metric(selection(), metrics_path=repo_root / METRICS)
    shape = type(result)

    # measured, but with nothing measured.
    with pytest.raises(ValidationError):
        shape.model_validate({**result.model_dump(), "status": "measured"})

    # waiting on a subsystem, yet carrying a number anyway.
    with pytest.raises(ValidationError):
        shape.model_validate(
            {**result.model_dump(), "status": "awaiting_subsystem", "value": Decimal(1)}
        )


def test_query_metric_runs_through_the_registry_end_to_end(registry):
    call = registry.bind(QUERY_METRIC, selection())
    result = registry.invoke(call, tier=AutonomyTier.L1)
    assert result.value.metric.id == "twin.throughput.units_per_hour"
    assert result.value.result_ids == ()


def test_a_tool_call_hashes_over_the_same_canonical_bytes_as_the_rest_of_the_system():
    """One system with two canonical forms has none.

    `twinflow-schemas` computes the determinism hash with `json.dumps` at its
    default `ensure_ascii`, and the historian, the cursor, and the ETag all
    follow it. A tool call carrying a non-ASCII argument has to reach the same
    bytes, or the same value hashes two ways depending on which subsystem asked.
    """
    import hashlib
    import json

    from twinflow.agent.tools import _canonical_sha256

    class Args(BaseModel):
        note: str

    args = Args(note="café µm")
    expected = hashlib.sha256(
        json.dumps({"note": "café µm"}, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()

    assert _canonical_sha256(args) == expected
