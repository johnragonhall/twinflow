"""The metric registry envelope (E26b, envelope half).

The split is envelope here, semantics elsewhere. This module owns the file, its
schema, the identifier grammar, and the validation rules. The expression
language and the evaluator belong to the AI layer.

The identifier space exists from Phase 0 for a sequencing reason rather than a
topical one: stage 6 of the config pipeline resolves spec_limits keys into
metric ids, so those ids have to be resolvable long before any expression
computes. Nothing about the file changes shape when the evaluator arrives, which
is what lets spec limits be authored against ids that compute two phases later.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from twinflow.config._impl.errors import Diagnostic, nearest
from twinflow.config._impl.loader import (
    ConfigError,
    _line_col,
    _raise,
    _schemas_root,
    parse,
    validate_schema,
)

METRICS_SCHEMA = "config/metrics/v1.json"

#: <domain>.<area>.<name>, lowercase snake_case within each part.
METRIC_ID = re.compile(r"^[a-z][a-z0-9_]*(\.[a-z][a-z0-9_]*){2}$")


def load_metrics(
    path: str | Path, *, schemas_root: Path | None = None
) -> tuple[Any, list[Diagnostic]]:
    """Validate a metric registry and return it with every diagnostic."""
    path = Path(path)
    text = path.read_text(encoding="utf-8")
    display = path.as_posix()

    document, diagnostics = parse(text, display)
    if document is None:
        _raise(diagnostics, text)

    schema = json.loads((_schemas_root(schemas_root) / METRICS_SCHEMA).read_text(encoding="utf-8"))
    diagnostics += validate_schema(document, schema, display)
    diagnostics += check_metric_rules(document, display)

    if any(d.severity == "error" for d in diagnostics):
        _raise(diagnostics, text)
    return document, diagnostics


def check_metric_rules(document: Any, path: str) -> list[Diagnostic]:
    """The TF-C15x rules of foundations 5.15."""
    diagnostics: list[Diagnostic] = []
    seen: dict[str, int] = {}

    for index, metric in enumerate(document.get("metrics") or []):
        metric_id = metric.get("id")

        if metric_id is not None and not METRIC_ID.match(str(metric_id)):
            line, column = _line_col(metric, "id")
            diagnostics.append(
                Diagnostic(
                    code="TF-C153",
                    message=f"metric id {metric_id!r} does not match the grammar",
                    path=path,
                    line=line,
                    column=column,
                    suggestion="use <domain>.<area>.<name>, lowercase and snake_case",
                    notes=("for example twin.throughput.units_per_hour",),
                )
            )

        if metric_id in seen:
            line, column = _line_col(metric, "id")
            diagnostics.append(
                Diagnostic(
                    code="TF-C150",
                    message=f"metric id {metric_id!r} is defined twice",
                    path=path,
                    line=line,
                    column=column,
                    suggestion=(
                        "an id names one quantity for good. Give the redefinition a new id "
                        "and deprecate this one"
                    ),
                )
            )
        elif metric_id is not None:
            seen[metric_id] = index

        if metric.get("status") == "deprecated" and not metric.get("deprecated_in"):
            line, column = _line_col(metric, "status")
            diagnostics.append(
                Diagnostic(
                    code="TF-C155",
                    message=f"metric {metric_id!r} is deprecated with no deprecated_in",
                    path=path,
                    line=line,
                    column=column,
                    suggestion="name the release that deprecated it",
                )
            )

    return diagnostics


def resolve_spec_limits(
    spec_limits: dict[str, Any], registry: Any, path: str, *, node: Any = None
) -> list[Diagnostic]:
    """TF-C103. Every spec_limits key names a metric the registry declares.

    This is the reason the identifier space is a Phase 0 artifact: a spec limit
    authored now against an id that computes two phases from now still has to
    resolve now, or the typo surfaces at a demo rather than at CI.
    """
    declared = [metric.get("id") for metric in registry.get("metrics") or []]
    diagnostics: list[Diagnostic] = []

    for key in spec_limits:
        if key in declared:
            continue
        line, column = _line_col(node if node is not None else spec_limits, key)
        hint = nearest(key, [d for d in declared if d])
        diagnostics.append(
            Diagnostic(
                code="TF-C103",
                message=f"spec limit names metric {key!r}, which the registry does not declare",
                path=path,
                line=line,
                column=column,
                suggestion=(f"did you mean {hint!r}?" if hint else "declare it in metrics.yaml"),
                notes=(f"declared metrics: {', '.join(d for d in declared if d)}",),
            )
        )
    return diagnostics


__all__ = [
    "METRICS_SCHEMA",
    "METRIC_ID",
    "ConfigError",
    "check_metric_rules",
    "load_metrics",
    "resolve_spec_limits",
]
