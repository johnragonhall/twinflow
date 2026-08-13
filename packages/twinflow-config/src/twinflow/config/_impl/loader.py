"""The config validation pipeline (C5).

Each stage reports all of its findings before the next stage runs. That is the
whole ergonomic point: an author who fixes one error and reruns to find the next
one gives up long before an author who is handed the list.

Stages implemented here are parse, schema validation, cross-reference
resolution, and plausibility. Unit resolution arrives with pint and the
requirement that consumes it, and overlay merging arrives with the CLI that
passes --overlay; both are named in foundations 5.6 and neither has a consumer
yet, so neither is guessed at here.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import jsonschema
from ruamel.yaml import YAML
from ruamel.yaml.error import MarkedYAMLError

from twinflow.config._impl.errors import Diagnostic, Severity, nearest

#: The published facility contract. The loader validates against this file
#: rather than against a second copy expressed in Python, so the schema an
#: author reads and the schema the loader enforces are one artifact.
FACILITY_SCHEMA = "config/facility/v1.json"


class ConfigError(Exception):
    """Raised when a config carries at least one error-severity diagnostic."""

    def __init__(self, diagnostics: list[Diagnostic], rendered: str) -> None:
        super().__init__(rendered)
        self.diagnostics = diagnostics
        self.rendered = rendered


def _schemas_root(explicit: Path | None) -> Path:
    if explicit is not None:
        return explicit
    # packages/twinflow-config/src/twinflow/config/_impl/loader.py -> repo root
    return Path(__file__).resolve().parents[6] / "schemas"


def _line_col(node: Any, key: str | None = None) -> tuple[int, int]:
    """The 1-based line and column ruamel recorded for a node or one of its keys.

    ruamel keeps this on round-trip loaded containers, which is the only reason
    a schema error can point at the line the author edited rather than at a
    JSON pointer.
    """
    lc = getattr(node, "lc", None)
    if lc is None:
        return (1, 1)
    if key is not None:
        try:
            line, col = lc.key(key)
            return (line + 1, col + 1)
        except (KeyError, TypeError, AttributeError):
            pass
    return (int(lc.line) + 1, int(lc.col) + 1)


def _resolve(document: Any, pointer: list) -> Any:
    node = document
    for part in pointer:
        try:
            node = node[part]
        except (KeyError, IndexError, TypeError):
            return node
    return node


def parse(text: str, path: str) -> tuple[Any, list[Diagnostic]]:
    """Stage 1. Round-trip load, so every later stage has line and column."""
    yaml = YAML(typ="rt")
    try:
        return yaml.load(text), []
    except MarkedYAMLError as exc:
        mark = exc.problem_mark
        return None, [
            Diagnostic(
                code="TF-C001",
                message=f"cannot parse this file: {exc.problem}",
                path=path,
                line=(mark.line + 1) if mark else 1,
                column=(mark.column + 1) if mark else 1,
                suggestion="fix the YAML syntax here",
            )
        ]


def validate_schema(document: Any, schema: dict, path: str) -> list[Diagnostic]:
    """Stage 3. JSON Schema, with every error mapped back to line and column."""
    validator_class = jsonschema.validators.validator_for(schema)
    validator = validator_class(schema)
    diagnostics: list[Diagnostic] = []

    for error in sorted(validator.iter_errors(document), key=lambda e: list(e.absolute_path)):
        pointer = list(error.absolute_path)
        parent = _resolve(document, pointer[:-1]) if pointer else document
        key = pointer[-1] if pointer else None

        if error.validator == "additionalProperties":
            # A subschema is a mapping or a bare boolean under 2020-12. Only the
            # mapping form carries properties, and only that form reaches here.
            subschema = error.schema if isinstance(error.schema, dict) else {}
            declared = subschema.get("properties", {})
            unknown = sorted(set(error.instance) - set(declared))
            allowed = sorted(declared)
            node = _resolve(document, pointer)
            for name in unknown:
                line, column = _line_col(node, name)
                hint = nearest(name, allowed)
                diagnostics.append(
                    Diagnostic(
                        code="TF-C012",
                        message=f"unknown key {name!r}",
                        path=path,
                        line=line,
                        column=column,
                        suggestion=(
                            f"did you mean {hint!r}?"
                            if hint
                            else "remove it, or check the spelling"
                        ),
                        notes=(f"valid keys here: {', '.join(allowed)}",),
                    )
                )
            continue

        if error.validator == "required":
            node = _resolve(document, pointer)
            line, column = _line_col(node)
            missing = error.message.split("'")[1] if "'" in error.message else "a required key"
            diagnostics.append(
                Diagnostic(
                    code="TF-C011",
                    message=f"missing required key {missing!r}",
                    path=path,
                    line=line,
                    column=column,
                    suggestion=f"add {missing!r} here",
                )
            )
            continue

        line, column = _line_col(parent, key if isinstance(key, str) else None)
        if not isinstance(key, str):
            line, column = _line_col(_resolve(document, pointer))

        diagnostics.append(
            Diagnostic(
                code="TF-C013",
                message=error.message,
                path=path,
                line=line,
                column=column,
                suggestion=_suggest_for(error),
            )
        )

    return diagnostics


def _suggest_for(error: jsonschema.ValidationError) -> str:
    if error.validator == "enum":
        return f"use one of: {', '.join(repr(v) for v in error.validator_value)}"
    if error.validator == "pattern":
        return f"the value has to match {error.validator_value}"
    if error.validator == "type":
        return f"this has to be a {error.validator_value}"
    if error.validator in {"minimum", "exclusiveMinimum"}:
        return f"the value has to be at least {error.validator_value}"
    if error.validator in {"maximum", "exclusiveMaximum"}:
        return f"the value has to be at most {error.validator_value}"
    if error.validator == "minItems":
        return f"list at least {error.validator_value} of these"
    return "check this value against the facility schema"


def check_references(document: Any, path: str) -> list[Diagnostic]:
    """Stage 6. Every reference resolves, and each names a nearby candidate.

    Only the domains a Phase 0 artifact owns are resolved here. A reference into
    a domain no installed package owns is a different diagnostic (TF-C130), and
    it arrives with the entry-point registry that knows which domains exist.
    """
    diagnostics: list[Diagnostic] = []
    layout = document.get("layout") or {}
    station_ids = [station.get("id") for station in layout.get("stations") or []]
    zone_ids = [zone.get("id") for zone in layout.get("zones") or []]

    for station in layout.get("stations") or []:
        zone = station.get("zone")
        if zone is not None and zone not in zone_ids:
            line, column = _line_col(station, "zone")
            hint = nearest(zone, [z for z in zone_ids if z])
            diagnostics.append(
                Diagnostic(
                    code="TF-C106",
                    message=(
                        f"station {station.get('id')!r} names zone {zone!r}, which no zone declares"
                    ),
                    path=path,
                    line=line,
                    column=column,
                    suggestion=(
                        f"did you mean {hint!r}?" if hint else "declare it under layout.zones"
                    ),
                    notes=(f"declared zones: {', '.join(z for z in zone_ids if z)}",),
                )
            )

    for flow in document.get("flows") or []:
        station_id = flow.get("station_id")
        if station_id is not None and station_id not in station_ids:
            line, column = _line_col(flow, "station_id")
            hint = nearest(station_id, [s for s in station_ids if s])
            diagnostics.append(
                Diagnostic(
                    code="TF-C101",
                    message=(
                        f"flow {flow.get('id')!r} names station {station_id!r}, "
                        f"which no station declares"
                    ),
                    path=path,
                    line=line,
                    column=column,
                    suggestion=(
                        f"did you mean {hint!r}?" if hint else "declare it under layout.stations"
                    ),
                    notes=(f"declared stations: {', '.join(s for s in station_ids if s)}",),
                )
            )

    return diagnostics


def check_plausibility(document: Any, path: str) -> list[Diagnostic]:
    """Stage 7. Warnings, never errors: a legal config that looks like a mistake."""
    diagnostics: list[Diagnostic] = []
    layout = document.get("layout") or {}

    for station in layout.get("stations") or []:
        if station.get("capacity") == 0:
            line, column = _line_col(station, "capacity")
            diagnostics.append(
                Diagnostic(
                    code="TF-C301",
                    message=(
                        f"station {station.get('id')!r} has zero capacity, so no work passes it"
                    ),
                    path=path,
                    line=line,
                    column=column,
                    severity=Severity.WARNING,
                    suggestion="set a capacity of at least 1, or remove the station",
                )
            )

    return diagnostics


def load_facility(
    path: str | Path, *, schemas_root: Path | None = None, strict: bool = False
) -> tuple[Any, list[Diagnostic]]:
    """Validate one facility profile and return it with every diagnostic.

    Raises ConfigError when anything is error severity, or when `strict` is set
    and anything at all was reported.
    """
    path = Path(path)
    text = path.read_text(encoding="utf-8")
    display = path.as_posix()

    document, diagnostics = parse(text, display)
    if document is None:
        _raise(diagnostics, text)

    schema = json.loads((_schemas_root(schemas_root) / FACILITY_SCHEMA).read_text(encoding="utf-8"))
    diagnostics += validate_schema(document, schema, display)

    # Cross-references only run on a document that matched its shape. Resolving
    # a reference inside a document that failed schema validation produces
    # cascading noise about keys the author already knows are wrong.
    if not any(d.severity is Severity.ERROR for d in diagnostics):
        diagnostics += check_references(document, display)
    diagnostics += check_plausibility(document, display)

    if any(d.severity is Severity.ERROR for d in diagnostics) or (strict and diagnostics):
        _raise(diagnostics, text)

    return document, diagnostics


def _raise(diagnostics: list[Diagnostic], text: str) -> None:
    lines = text.splitlines()
    rendered = "\n\n".join(d.render(lines) for d in diagnostics)
    raise ConfigError(diagnostics, rendered)
