---
title: ADR-0002 twinflow implements the agent seam rather than adopting Pydantic AI
description: Keeps the run-time license allowlist intact by writing twinflow's own structured-output seam and local model path instead of adopting Pydantic AI.
topic_type: concept
audience: contributors
---

# ADR-0002 twinflow implements the agent seam rather than adopting Pydantic AI

## Status

`accepted`, 2026-08-13.

## Context

Requirement `ARCH-5` asks for an agent framework that is thin and inspectable,
with a local model option. Two technology decisions answer it. Decision D9
selects Pydantic AI 2.27.0, for one interface across Anthropic, OpenAI, Gemini,
and Ollama, and for a structured-output guarantee with validation-retry.
Decision D10 pairs it with Ollama and constrained decoding, so the demo runs
with no API key and the accuracy stack does not weaken when the key is absent.

Decision D15 sets the inbound license policy: permissive only, and CI fails the
build outside the allowlist in CONTRIBUTING.md. That allowlist carries two
MPL-2.0 rows. Development only is accepted, because a test dependency is never
shipped. Shipped at run time is refused, and the stated reason is that the
file-level condition would travel to a user who installs a twinflow package.
Release gate `VAL-GATE-SEC-001` names the same allowlist.

Resolving the framework against the Python Package Index on 2026-08-13 gives
the numbers this decision turns on. `pydantic-ai` 2.27.0 resolves to 100
distributions. The narrower `pydantic-ai-slim` still resolves to 20. Both trees
contain `certifi`, which arrives through `httpx` as a run-time dependency, and
`certifi` declares `License: MPL-2.0` in its own package metadata. The full tree
also carries `Unlicense`, `CNRI-Python`, `MIT-0`, and `MPL-2.0 AND MIT`, and
none of those four has an allowlist row at all.

So the allowlist refuses the framework as resolved. The refusal is on a
certificate authority bundle rather than on anything the agent layer uses, which
is the awkward part of this record and the reason the argument against it below
is worth reading.

One fact makes writing the local path affordable. Ollama listens on the loopback
interface, and a request to loopback verifies no certificate, so it needs no
certificate authority bundle and therefore no `certifi`. Ollama's `/api/chat`
accepts a `format` parameter holding a JSON Schema and constrains the sampler to
it at decode time, which is the constrained decoding D10 asks for. The Python
standard library posts that request without a third-party distribution.

## Decision

twinflow implements `ARCH-5` itself, behind one named seam. `twinflow.agent.tools`
declares `StructuredOutputAdapter`, a single-method protocol that turns an
untrusted emission into a validated pydantic model or raises.

Two implementations fill it. `PydanticStructuredOutput` carries decision D9's
validate-then-retry loop on pydantic alone. `OllamaStructuredOutput` lives in
`twinflow.agent.local_model`. It posts the model's JSON Schema as the `format`
parameter of Ollama's `/api/chat`, using `urllib.request` from the Python 3.12
standard library, then validates the answer against the same model. No agent
framework and no HTTP client distribution enters the run-time tree.

The second validation is deliberate duplication. The decode-time constraint is a
promise made by a server this project does not control, and a build whose grammar
compiler drops `pattern` returns a document that is shaped correctly and still
wrong. There is no code path that omits the schema from a request, and no path
that answers a schema failure by asking again without the constraint.

## Alternatives considered

| Alternative                                                         | Why it lost                                                                                                                                                                          |
| ------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| Adopt `pydantic-ai` 2.27.0 as decision D9 names it                  | 100 distributions, four SPDX ids with no allowlist row, and `certifi` under MPL-2.0 shipped at run time, which the allowlist refuses                                                 |
| Adopt the narrower `pydantic-ai-slim`                               | 20 distributions rather than 100, and it still reaches `certifi` through `httpx` at run time, so the refused row still applies                                                       |
| Widen the allowlist to accept MPL-2.0 at run time                   | It is a policy change the allowlist owner takes on evidence, not one a work package takes to unblock itself, and gate `VAL-GATE-SEC-001` would then pass a class nobody re-examined  |
| Vendor Pydantic AI and remove `httpx`                               | The provider clients are `httpx`, so removing it removes the multi-provider switch that was the reason to adopt the framework, and it adds a fork to maintain                        |
| Use `urllib3` for the local request instead of the standard library | It has no required dependencies, so it would pass the allowlist. It buys nothing on loopback that `urllib.request` does not already do, and every distribution is a surface to watch |
| Ask the local model for JSON in the prompt, with no `format`        | That is a request rather than a guarantee, so the structured-output layer of the accuracy stack would weaken exactly when the API key is absent, which decision D10 forbids          |
| Adopt LangChain or LangGraph instead                                | Decision D9 already rejected it on inspectability, and its dependency tree is larger, so the license question returns in a worse form                                                |
| Ship the hosted path only, and no local model                       | Decision D10 requires a demo that runs with no API key and no cloud account                                                                                                          |

## Consequences

What this buys. The run-time license allowlist stays as written, and gate
`VAL-GATE-SEC-001` passes on a tree that contains no MPL-2.0 distribution. The
whole local model path is one module a reader can inspect end to end, which is
closer to `ARCH-5`'s "thin and inspectable" than 100 distributions would be.
The local path adds zero distributions, so `pip install twinflow-agent` still
brings pydantic and two workspace leaves. The seam is named and tested, so
adopting a framework later is a constructor argument rather than a rewrite.

What it costs, and this is the part that earns the record its place. The
multi-provider switch is not shipped. Decision D9 wanted one interface across
Anthropic, OpenAI, Gemini, and Ollama with a one-line model change, and what
exists is one local implementation behind a seam. Adding a hosted provider means
writing that client here, and a hosted provider does verify a certificate, so
the `certifi` question returns for that path alone. Everything a framework
maintains is now this project's to maintain: retries, timeouts, streaming, the
tool-call protocol, message history, and each provider's deviations from its own
documentation. That is a real recurring cost against a saved dependency.

The obligation this creates. `UrllibJsonTransport` is a real network adapter, and
`scripts/checks/nondeterminism-gate.sh` names the kernel package as the one
legitimate home for a real adapter. It sits in `twinflow-agent` because that gate
matches text rather than behavior and does not see `urllib.request`, not because
the rule does not apply. Moving it to the kernel package, and adding
`urllib.request.urlopen` to the gate's banned list at the same time, is work this
record books rather than leaves implicit. Until then the shape is held by design:
the transport is injected and never constructed implicitly, so a simulation run
drives a recording.

The strongest argument against this decision. Most serious Python projects ship
`certifi` unmodified. MPL-2.0 section 3.3 permits distributing a Larger Work
under other terms, provided the covered files stay under the MPL. The bundle
would ship unmodified, so the source-availability condition of section 3.2 is
discharged by pointing at the upstream distribution. Nothing about a twinflow
package would become file-level copyleft. On that reading the allowlist row is
stricter than the license requires, and this record spends a real capability,
plus a maintenance stream, to buy a compliance margin that may be unnecessary.

The reply is not that the reading is wrong. It is that the allowlist is a
written policy with a release gate behind it, and a work package is not where a
license policy is reinterpreted to unblock itself. The reading deserves to be
settled on the record by the allowlist owner, which is what the revisit
condition names.

Either of two changes reopens this decision. The first is an allowlist decision
on unmodified certificate authority trust stores, taken deliberately and written
into CONTRIBUTING.md, which would remove the only objection to decision D9. The
second is Pydantic AI dropping `httpx` from its run-time dependencies, or
offering an extra that does, which would remove the objection without any policy
change. Neither had happened on the date of this record, and this record is
superseded rather than edited when one does.

## Validation

The license allowlist gate is the mechanical check. It fails the build on a
distribution outside the allowlist, so a later commit that adds Pydantic AI
without also changing the policy fails rather than lands quietly. Release gate
`VAL-GATE-SEC-001` names the same allowlist.

Three tests in `packages/twinflow-agent/tests/test_local_model.py` hold the parts
a license gate cannot see. `test_the_local_path_costs_no_third_party_dependency`
parses the module and asserts that every import resolves to the standard library
or to pydantic. An `httpx` import would fail there rather than pass unnoticed.
`test_no_attempt_falls_back_to_an_unconstrained_call` asserts that the schema is
present in every request including retries.
`test_a_missing_daemon_is_not_retried_and_is_never_swallowed` asserts that a
connection failure leaves the loop immediately.

One thing nothing holds. The nondeterminism gate does not currently see
`urllib.request`, so the placement of `UrllibJsonTransport` outside the kernel
package is held by review rather than by a check. That is stated here because an
unenforced decision drifts, and the fix is booked in the consequences above.
