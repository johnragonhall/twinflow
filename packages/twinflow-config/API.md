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
| --------------------- | -------- | ---------------------------------------------------------------------- |
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

## The unified namespace

ARCHITECTURE.md section 5 makes the namespace "a projection of the facility
model, not a parallel truth". This package owns the facility model, so it owns
the grammar. Every renderer sits above this layer and imports it: the publish
side in `twinflow.sensors`, the historian in `twinflow.storage`.

| Symbol            | Kind     | What it is                                                           |
| ----------------- | -------- | -------------------------------------------------------------------- |
| `UnsPath`         | class    | One six-level ISA-95 address. Frozen, validated at construction      |
| `NamingError`     | class    | A refused name, a `ValueError` carrying the `TF-S0xx` code           |
| `IDENTIFIER`      | constant | The compiled pattern the first five levels are validated against     |
| `PARAMETER`       | constant | The compiled pattern the parameter level is validated against        |
| `LEVEL_NAMES`     | constant | The six level names, in topic order                                  |
| `TOPIC_LEVELS`    | constant | `6`                                                                  |
| `TOPIC_SEPARATOR` | constant | `"/"`, the MQTT level separator                                      |
| `WILDCARDS`       | constant | `("+", "#")`, legal in a subscription and never in a published topic |

`UnsPath` validates at construction rather than at publish or write time. That
is what makes every rendering safe at once: a level that passed cannot carry
`+`, `#`, `/`, a space, a newline, or the `:` a Sparkplug Group ID joins the
first three levels with, so the topic string, the subscription, the Sparkplug
identifiers, and the historian series key are all derived from something
already checked.

Builders, in the order to reach for them:

- `UnsPath.from_facility(mapping)` yields every declared topic in sorted order.
  This is how topics are meant to be produced: generated from config, never
  typed. The argument is a plain mapping of the namespace shape, not the
  document `load_facility` returns, because `config/facility/v1.json` does not
  carry the ISA-95 tree yet.
- `UnsPath.from_prefix(prefix, parameter)` for a device that already knows its
  own five identifier levels.
- `UnsPath.parse(topic)` reads a published topic back. It exists for round-trip
  proofs and for consumers holding a topic string, not as a license to type one.

Renderings: `.topic` and `.levels` are properties, `.subscription(depth)` is
the one place a wildcard is produced, and `.with_equipment` / `.with_parameter`
return a new path. `UnsPath.is_identifier` and `UnsPath.is_parameter` are the
predicates behind the two patterns.

One deliberate narrowing: `docs/design/sensor-catalog.md` D.1 permits the
parameter level to carry further slashes, which makes a topic deeper than six
levels. ARCHITECTURE.md section 5 fixes device telemetry at exactly six and both
concrete P1 topics are single-segment, so this grammar takes the stricter
reading. A nested parameter is a change to `PARAMETER` and to that document
together, rather than a depth that silently varies by device.

## Error codes

| Code      | Severity | Meaning                                          |
| --------- | -------- | ------------------------------------------------ |
| `TF-C001` | error    | The file does not parse                          |
| `TF-C011` | error    | A required key is absent                         |
| `TF-C012` | error    | An unknown key, with the nearest valid key named |
| `TF-C013` | error    | A value fails its declared shape                 |
| `TF-C101` | error    | A flow names a station nothing declares          |
| `TF-C106` | error    | A station names a zone nothing declares          |
| `TF-C301` | warning  | A station has zero capacity                      |

The namespace codes are the `TF-S0xx` block. They keep the numbering they had
in `twinflow.storage`, where the six-level rules used to live, so an operator
runbook that names one still names the same refusal.

| Code      | Refused                                                         |
| --------- | --------------------------------------------------------------- |
| `TF-S001` | An empty level, or a level that is not a string                 |
| `TF-S002` | A wildcard in a level, which belongs in a subscription instead  |
| `TF-S003` | An identifier outside lowercase kebab-case within 32 characters |
| `TF-S004` | A parameter outside lowercase snake_case within 64 characters   |
| `TF-S005` | A topic that is not exactly six levels                          |
| `TF-S007` | A subscription depth outside 1 to 6                             |
| `TF-S008` | A prefix that is not the five identifier levels                 |

`TF-S006` is not here. It belongs to `LayerPlacement` in `twinflow.storage`,
which is a Purdue layer refusal rather than a namespace one.

## Not here yet

Unit resolution arrives with pint, and overlay merging with the CLI that passes
`--overlay`. Foundations 5.6 names both. Neither has a consumer yet, and a
stage with no consumer is a stage nobody tested.

## Re-exports

None.
