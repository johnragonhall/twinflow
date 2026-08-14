---
title: Security policy
description: How to report a vulnerability privately, which versions get fixes, and where the trust boundary sits around the MCP and REST surfaces.
topic_type: concept
audience: contributors
---

# Security policy

This project simulates CVE handling and vulnerability triage as part of its
domain model. A project that models that work and carries no security policy of
its own has not taken the subject seriously, so this page states the real one.

## Reporting a vulnerability

Do not open a public issue for a security finding.

Use GitHub private vulnerability reporting. Open
<https://github.com/johnragonhall/twinflow/security/advisories> and choose
"Report a vulnerability". That channel is private between you and the
maintainer. It opens a draft advisory, which the maintainer publishes when the
fix ships, and the published advisory is then the public record.

Private reporting is a per-repository setting. If the
button is missing, open a public issue containing only the sentence "I have a
security report" and no technical detail. The maintainer will open a private
channel from there.

Include in the report:

- The affected component and the commit or release tag you tested.
- The steps to reproduce, or a proof of concept.
- Your reading of the impact, and what an attacker gets.
- Whether you have told anyone else, and any disclosure date you have in mind.

Expect a first reply within 7 days. If a report is confirmed, the fix and the
advisory go out together, and you are credited by whatever name you ask for.

## Supported versions

| Version         | Status                                        |
|-----------------|-----------------------------------------------|
| `main`          | Supported. Fixes land here first.             |
| Latest `v*` tag | Supported. Fixes are back-ported from `main`. |
| Older `v*` tags | Not supported. Upgrade to the latest tag.     |

This is a portfolio and reference project, not a product with a support
contract. Nobody is on call for it. The policy above says what the maintainer
does, not what anyone is entitled to.

## Threat model

The system exposes two remote surfaces: an MCP server for agent clients and a
REST API for dashboards and scripts. Both sit in front of the same analytics
layer, which holds a DuckDB catalog over Delta tables and a sandboxed Python
evaluator for user-supplied expressions.

The assumed attacker is an authenticated client that has gone rogue: a
compromised agent, a stolen API token, or a prompt-injected model calling tools
on its operator's behalf. The design assumes such a client sends the worst
input it can construct.

### What a client can reach

- The named MCP tools and REST routes, with their declared schemas.
- Read-only SQL against a fixed set of views. Queries run through a parameter
  binder against a connection opened read-only, with no DDL, no attach, no
  copy, and no filesystem functions.
- The Python evaluator, for scoring expressions over a result set. It runs with
  no imports, no builtins beyond a fixed arithmetic set, no network, no
  filesystem, a wall-clock deadline, and a memory ceiling.
- Its own scenario data, scoped by the token it presented.

### What a client cannot reach

- The host filesystem. Neither surface takes a path from the client, and the
  DuckDB connection has filesystem access disabled.
- The process environment, secrets, or the storage credentials behind the Delta
  tables.
- The write path. Ingest and simulation writes come from the kernel, never from
  a request handler.
- Another scenario's data, or another token's history.
- The device fleet. The MQTT and device-agent paths are not reachable from the
  MCP or REST surface, in either direction.

### The sandbox boundary in one sentence

SQL and Python from a client are treated as data, parsed and bound rather than
concatenated, and evaluated inside an interpreter with the dangerous
capabilities removed rather than filtered by pattern matching.

A denylist of forbidden strings is not a boundary, because it fails open on
every construction nobody thought of. If a change here starts to read like a
list of banned words, the change is wrong.

## What the repository does to keep itself honest

- Secrets never live in the tree. `scripts/ci-local.sh --full` and
  `scripts/ci-local.sh --security` run `gitleaks` and `trufflehog` over the
  tree. Both steps print a skip line and pass when the tool is not installed,
  so a clean local run is evidence only when the tool was present.
- SQL is always parameterized. String-interpolated SQL is a review blocker,
  not a style preference.
- The determinism gates keep a request handler from reading a wall clock or
  opening a socket, which also removes a class of side channel and a class of
  test flake.
- The same two local modes run `pip-audit` and `cargo audit`, under the same
  skip-when-absent rule.

Two of those live only on a developer machine today. The hosted workflows in
`.github/workflows/` run the lint and policy gates and the test matrix, and
they run no secret scan and no dependency audit. Milestone C11 in `ROADMAP.md`
sequences the hosted form, and release gate `VAL-GATE-SEC-001` is what makes a
clean audit and an attached SBOM a condition of tagging.

## Known gaps

Tracked openly so nobody mistakes them for solved:

- Authentication and multi-tenant scoping are described above as the design
  contract. Read the code before trusting either.
- The Python evaluator has no formal proof of confinement. It is a restricted
  interpreter, not a virtual machine, and it is scoped to arithmetic over a
  result set for that reason.
- There is no rate limit on the MCP surface yet, so an authenticated client can
  still exhaust CPU with expensive queries.
