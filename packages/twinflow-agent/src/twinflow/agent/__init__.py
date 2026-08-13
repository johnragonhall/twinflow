"""The agent tool surface, and the autonomy tier every call carries.

Every tool is schema-constrained, so a call that does not validate is refused
before it reaches the twin rather than after (E26d). Every change is attributed
to the authority it was made under, and a session never raises that authority on
its own (E5a).

Two modules, one each for the two halves:

    tools.py         the registry, the ToolSpec contract, the structured-output
                     seam, and query_metric, the first of the nine tools
    autonomy.py      the tier, the grant, the tool-permission gate, and the
                     governance events the dashboard renders
    local_model.py   the local model path: constrained decoding through Ollama
                     on the standard library alone (D10, ADR-0002)

P2 adds get_findings, run_whatif, run_capability_report, and explain_finding,
each grounded in an execution trace and checked by the grounding checker before
an answer is published.
"""

from __future__ import annotations

from twinflow.agent.autonomy import (
    CHANGE_ATTRIBUTED,
    ELEVATION_DECIDED,
    ELEVATION_EXPIRED,
    ELEVATION_REQUESTED,
    ActorId,
    AuditLog,
    AutonomyError,
    AutonomyGrant,
    AutonomySession,
    AutonomyTier,
    ChangeAttribution,
    ElevationDecided,
    ElevationExpired,
    ElevationRequested,
    SimClockPort,
    TierRefused,
)
from twinflow.agent.local_model import (
    DEFAULT_OLLAMA_BASE_URL,
    DEFAULT_OLLAMA_MODEL,
    ConstraintNotHonored,
    JsonHttpTransport,
    OllamaError,
    OllamaStructuredOutput,
    OllamaUnavailable,
    UrllibJsonTransport,
)
from twinflow.agent.tools import (
    QUERY_METRIC,
    QUERY_METRIC_SPEC,
    CostClass,
    MetricDefinitionEcho,
    MetricFilter,
    MetricQueryResult,
    MetricSelection,
    PydanticStructuredOutput,
    SideEffect,
    StructuredOutputAdapter,
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

#: Read by tool.hatch.version, so this is the only place the version is written.
__version__ = "0.1.0"

__all__ = [
    "ActorId",
    "AuditLog",
    "AutonomyError",
    "AutonomyGrant",
    "AutonomySession",
    "AutonomyTier",
    "CHANGE_ATTRIBUTED",
    "ChangeAttribution",
    "ConstraintNotHonored",
    "CostClass",
    "DEFAULT_OLLAMA_BASE_URL",
    "DEFAULT_OLLAMA_MODEL",
    "ELEVATION_DECIDED",
    "ELEVATION_EXPIRED",
    "ELEVATION_REQUESTED",
    "ElevationDecided",
    "ElevationExpired",
    "ElevationRequested",
    "JsonHttpTransport",
    "MetricDefinitionEcho",
    "MetricFilter",
    "MetricQueryResult",
    "MetricSelection",
    "OllamaError",
    "OllamaStructuredOutput",
    "OllamaUnavailable",
    "PydanticStructuredOutput",
    "QUERY_METRIC",
    "QUERY_METRIC_SPEC",
    "SideEffect",
    "SimClockPort",
    "StructuredOutputAdapter",
    "TierRefused",
    "TimeWindow",
    "ToolCall",
    "ToolError",
    "ToolRegistry",
    "ToolResult",
    "ToolSpec",
    "ToolSpecError",
    "UrllibJsonTransport",
    "__version__",
    "build_default_registry",
    "query_metric",
]
