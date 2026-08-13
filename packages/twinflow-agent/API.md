---
title: twinflow-agent API
description: Every public symbol twinflow-agent owns, which boundary rule A1.4 requires each package to list.
topic_type: reference
audience: contributors
---

# twinflow-agent API

Boundary rule A1.4 gives every public symbol exactly one owning package. These
are the names this package owns.

## The tool surface

| Symbol                     | Kind      | What it is                                                                   |
| -------------------------- | --------- | ---------------------------------------------------------------------------- |
| `ToolRegistry`             | class     | The one registry MCP, REST, and the agent runtime read                       |
| `ToolSpec`                 | model     | One tool's contract, with the tier and side-effect invariants enforced on it |
| `ToolCall`                 | class     | A tool bound to arguments that validated at construction                     |
| `ToolResult`               | class     | What a tool returned, validated against the result model it declared         |
| `SideEffect`               | enum      | `none`, `simulate`, `write_config`                                           |
| `CostClass`                | enum      | `cheap`, `sim`, `heavy`                                                      |
| `ToolError`                | exception | A tool refused to run, so it contributes nothing to the ledger               |
| `ToolSpecError`            | exception | A tool was declared in a way the registry cannot make safe                   |
| `StructuredOutputAdapter`  | protocol  | The seam a constrained decoder or an agent framework fills                   |
| `PydanticStructuredOutput` | class     | The shipped adapter: validate, and on failure re-emit with the error         |
| `build_default_registry`   | function  | The registry the runtime starts from, with the metrics layer loaded once     |
| `QUERY_METRIC`             | constant  | `"query_metric"`, the name of the tool this release ships                    |
| `QUERY_METRIC_SPEC`        | constant  | Its `ToolSpec`                                                               |

## The local model path

Constrained decoding against a local Ollama daemon, on the standard library
alone. ADR-0002 records why this is written here rather than imported.

| Symbol                    | Kind      | What it is                                                                         |
| ------------------------- | --------- | ---------------------------------------------------------------------------------- |
| `OllamaStructuredOutput`  | class     | The D10 adapter: post the schema as `format`, then validate the answer again       |
| `JsonHttpTransport`       | protocol  | The injected port, so a test drives a fake and a run replays a recording           |
| `UrllibJsonTransport`     | class     | The real transport, `urllib.request` only, so the path costs no distribution       |
| `OllamaError`             | exception | The local model could not answer, and nothing partial came back with it            |
| `OllamaUnavailable`       | exception | The daemon is not reachable. Raised once, never retried, never caught              |
| `ConstraintNotHonored`    | exception | The answer was not a JSON document, so `format` did not take effect                |
| `DEFAULT_OLLAMA_BASE_URL` | constant  | `"http://localhost:11434"`, loopback, which is why no certificate bundle is needed |
| `DEFAULT_OLLAMA_MODEL`    | constant  | `"llama3.1"`, the model the quickstart pulls                                       |

The callback differs from the pydantic adapter's, on purpose.
`PydanticStructuredOutput` asks its callback for the emission. The model call
happens outside it. `OllamaStructuredOutput` owns the model call. The schema
has to reach the request for the constraint to exist, so this adapter asks its
callback for the prompt. A callback returning anything but a string raises
`TypeError` naming both adapters.

## query_metric

| Symbol                 | Kind     | What it is                                                               |
| ---------------------- | -------- | ------------------------------------------------------------------------ |
| `query_metric`         | function | Resolve one metric against the governed registry                         |
| `MetricSelection`      | model    | Its args: metric id, sim-time window, dimensions, filters, grain, limit  |
| `MetricQueryResult`    | model    | Its result, carrying either a measurement or the requirement it waits on |
| `MetricDefinitionEcho` | model    | The governed definition, echoed from the registry rather than restated   |
| `MetricFilter`         | model    | One predicate over a declared dimension                                  |
| `TimeWindow`           | model    | A half-open window in sim ticks                                          |

## Autonomy

| Symbol            | Kind      | What it is                                                                |
| ----------------- | --------- | ------------------------------------------------------------------------- |
| `AutonomyTier`    | enum      | `L1`, `L2`, `L3`, with `permits` for the gate comparison                  |
| `AutonomySession` | class     | One session's tier, and the only door through which it changes            |
| `AutonomyGrant`   | model     | A scoped, expiring elevation approved by a human who is not the requester |
| `ActorId`         | model     | Who asked or approved, with `kind` as a field a validator can read        |
| `AuditLog`        | class     | The envelope writer that owns this producer's sequence                    |
| `SimClockPort`    | protocol  | The clock, declared here so this package need not import the kernel       |
| `AutonomyError`   | exception | A tier rule was broken                                                    |
| `TierRefused`     | exception | The gate refused a call the session has no authority to make              |

## Governance events

| Symbol                | Kind     | What it is                                                             |
| --------------------- | -------- | ---------------------------------------------------------------------- |
| `ElevationRequested`  | model    | Payload of `governance.autonomy.elevation.requested`                   |
| `ElevationDecided`    | model    | Payload of `governance.autonomy.elevation.decided`                     |
| `ElevationExpired`    | model    | Payload of `governance.autonomy.elevation.expired`                     |
| `ChangeAttribution`   | model    | Payload of `governance.change.attributed`, the E5 audit event          |
| `ELEVATION_REQUESTED` | constant | The CloudEvents type string for the request                            |
| `ELEVATION_DECIDED`   | constant | The CloudEvents type string for the decision                           |
| `ELEVATION_EXPIRED`   | constant | The CloudEvents type string for the expiry                             |
| `CHANGE_ATTRIBUTED`   | constant | The CloudEvents type string for the change attribution                 |
| `__version__`         | constant | The distribution version, read by the build so the two cannot disagree |

## Not owned here

`Budget` belongs to twinflow-governance, so `ToolSpec.sim_budget` names a budget
key in the facility config rather than carrying a budget value. `Envelope`
belongs to twinflow-schemas. `MetricDef` and the metric registry file belong to
twinflow-config, and `MetricDefinitionEcho` is a projection of one, never a
second definition of it.
