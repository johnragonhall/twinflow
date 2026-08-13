---
title: twinflow-agent
description: The agent tool surface, schema-constrained, and the autonomy tier every call carries.
topic_type: concept
audience: contributors
---

# twinflow-agent

The agent tool surface, schema-constrained, and the autonomy tier every call
carries.

Two things live here, and they are separable on purpose. `twinflow.agent.tools`
is the registry that MCP, REST, and the agent runtime all read, so a tool is
described once rather than three times. `twinflow.agent.autonomy` is the tier a
session holds, the grant that raises it, and the audit event that attributes a
change to the authority it was made under.

```bash
pip install twinflow-agent
```

Installing it brings pydantic, `twinflow-schemas`, and `twinflow-config`. It does
not bring an agent framework, a model provider, a web server, or a database.

## What it does

```python
from twinflow.agent import AutonomyTier, build_default_registry

registry = build_default_registry(metrics_path="profiles/starter_dc.metrics.yaml")

call = registry.bind(
    "query_metric",
    {
        "metric": "twin.throughput.units_per_hour",
        "time_window": {"start_sim_ticks": 0, "end_sim_ticks": 3_600_000_000},
    },
)
result = registry.invoke(call, tier=AutonomyTier.L1)

print(result.value.metric.unit)  # 1/hour, read from the governed registry
print(result.value.status)  # awaiting_subsystem
print(result.value.required_by)  # E26
```

The result says `awaiting_subsystem` rather than returning a number, because the
expression evaluator belongs to the semantics layer and that lands later. This is
the rule the AI layer sets for any field that outruns its producer: name the
requirement you are waiting on, and never stand a zero in for a missing
measurement. A reader of the answer can see what is absent and why.

## A malformed tool call is not a thing you can build

The structured-output layer of the accuracy stack asks that a bad call be
impossible rather than discouraged. Three properties carry that here.

Constructing a `ToolCall` is the validation. There is no path that stores raw
arguments and checks them later, so an unvalidated call is not a state this
package can be in.

```python
registry.bind("query_metric", {"metric": "Throughput", "limitt": 5})
# pydantic.ValidationError: metric does not match the governed grammar,
# and limitt is not a field
```

Registration refuses an args model that tolerates unknown keys. Without that a
misspelled argument would be dropped in silence and the tool would answer a
question nobody asked. Registration also refuses a result model with no
`result_ids`, because a number that cannot enter the ledger cannot be cited, and
a number that cannot be cited cannot be grounded.

## A session never raises its own authority

L1 advises, L2 recommends with human approval, L3 applies inside guardrails. A
session starts at the configured default tier and stays there until a human
approves a scoped, expiring grant.

The interesting code is refusal code. `AutonomySession` exposes exactly one
method that raises the tier, and it takes an `AutonomyGrant`, which cannot be
constructed without a human approver who is not the requester. An agent that has
been talked into applying a change has nothing to call: the value it would need
to pass does not validate.

```python
AutonomyGrant(
    granted_tier=AutonomyTier.L3,
    requested_by=ActorId(kind="agent", id="ops-copilot"),
    approver=ActorId(kind="agent", id="ops-copilot"),
    ...,
)
# pydantic.ValidationError: an elevation to L3 needs a human approver
```

A grant names tools and never a wildcard, so one approval to apply a
recommendation does not also approve every other write tool in the registry. It
expires at whichever of its two limits arrives first, a question count or a sim
time, and there is no renewal path that skips a fresh approval.

Every step emits an event carrying the standard envelope: the elevation request
that the dashboard renders as an approval seam, the decision, the expiry, and the
change attribution. A change made above L1 that names no approver cannot be
represented, so the audit trail cannot contain an elevated change with nobody
attached to it.

## Determinism

Nothing here reads a wall clock, draws a random number, or mints a uuid. The
clock is an injected port, declared as a structural protocol so this package does
not depend on the kernel to have one. The network is an injected port for the
same reason, so a simulation run drives a recorded transport rather than a
daemon, and no connection opens unless a caller asked for one. The wall-clock field on each event is
derived from the sim tick and the run epoch rather than observed, and the
argument digest is computed over canonical JSON with sorted keys, so the same
call always hashes the same.

## The local model path, with no API key

`OllamaStructuredOutput` fills the same seam against a local Ollama daemon. The
model's JSON Schema is posted as the `format` parameter, so the sampler is
constrained at decode time, and the answer is validated against the same model
afterward. The second check is not redundant: it catches a daemon that ignored
the first.

```python
from twinflow.agent import OllamaStructuredOutput, build_default_registry

registry = build_default_registry(metrics_path="profiles/starter_dc.metrics.yaml")

call = registry.bind_structured(
    "query_metric",
    lambda feedback: feedback or "Throughput over the first hour, please.",
    adapter=OllamaStructuredOutput(model_name="llama3.1"),
)
```

That call brings no new dependency. Ollama listens on loopback, and a request to
loopback verifies no certificate, so `urllib.request` from the standard library
is enough and no certificate authority bundle is involved.

There is no unconstrained fallback. A daemon that is not running raises
`OllamaUnavailable` naming the command to start it, and a schema failure is
retried with the validation error rather than answered without the schema. A
structured-output guarantee that degrades quietly is worse than none, because
every refusal above it was built on the assumption that it holds.

## On the agent framework

The repository's architecture decisions select Pydantic AI for the provider
abstraction and its structured-output guarantee, paired with a local Ollama path
so the demo runs with no API key. This package implements both halves itself:
the guarantee on pydantic alone behind the `StructuredOutputAdapter` seam, and
the local path on the standard library.

The reason is a license constraint that was measured rather than assumed.
Resolving `pydantic-ai` 2.27.0 yields 100 distributions and the bare
`pydantic-ai-slim` yields 20, and both trees carry `certifi`, which is MPL-2.0 and
arrives through httpx at run time. The contributing guide's allowlist refuses
MPL-2.0 shipped at run time, because the file-level condition would travel to
anyone who installs a twinflow package. ADR-0002 records the decision, what it
costs, and the condition under which it would be revisited.

## License

Apache-2.0. See [LICENSE](LICENSE) and [NOTICE](NOTICE).
