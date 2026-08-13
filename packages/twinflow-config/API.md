---
title: twinflow-config API
description: Every public symbol twinflow-config owns, which boundary rule A1.4 requires each package to list.
topic_type: reference
audience: contributors
---

# twinflow-config API

Boundary rule A1.4 gives every public symbol exactly one owning package. These
are the names this package owns.

| Symbol                | Kind     | What it is                                                             |
|-----------------------|----------|------------------------------------------------------------------------|
| `load_facility`       | function | Validate one facility profile and return it with every diagnostic      |
| `ConfigError`         | class    | Raised when a profile carries an error, holding the rendered report    |
| `Diagnostic`          | class    | One finding: code, message, line, column, severity, suggestion, notes  |
| `Severity`            | enum     | `ERROR` or `WARNING`                                                   |
| `nearest`             | function | The closest candidate to a misspelling, or nothing when none is close  |
| `parse`               | function | Stage 1, round-trip YAML load that keeps line and column               |
| `validate_schema`     | function | Stage 3, JSON Schema with pointers mapped back to line and column      |
| `check_references`    | function | Stage 6, every reference resolves and names a nearby candidate         |
| `check_plausibility`  | function | Stage 7, legal configs that look like mistakes                         |
| `FACILITY_SCHEMA`     | constant | The published facility contract this loader validates against          |
| `load_metrics`        | function | Validate a metric registry and return it with every diagnostic         |
| `check_metric_rules`  | function | The TF-C15x rules: duplicate id, bad grammar, deprecation with no date |
| `resolve_spec_limits` | function | TF-C103, naming the nearest declared id when a key dangles             |
| `METRICS_SCHEMA`      | constant | The published metric registry contract                                 |
| `METRIC_ID`           | constant | The three-part identifier grammar                                      |
| `__version__`         | constant | The distribution version, read by the build so the two cannot disagree |

## Error codes

| Code      | Severity | Meaning                                          |
|-----------|----------|--------------------------------------------------|
| `TF-C001` | error    | The file does not parse                          |
| `TF-C011` | error    | A required key is absent                         |
| `TF-C012` | error    | An unknown key, with the nearest valid key named |
| `TF-C013` | error    | A value fails its declared shape                 |
| `TF-C101` | error    | A flow names a station nothing declares          |
| `TF-C106` | error    | A station names a zone nothing declares          |
| `TF-C301` | warning  | A station has zero capacity                      |

## Not here yet

Unit resolution arrives with pint, and overlay merging with the CLI that passes
`--overlay`. Foundations 5.6 names both. Neither has a consumer yet, and a
stage with no consumer is a stage nobody tested.

## Re-exports

None.
