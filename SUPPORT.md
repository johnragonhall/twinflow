---
title: Support
description: Where to put a question about twinflow, what falls inside and outside scope, and what answer one unpaid maintainer can give.
topic_type: reference
audience: users
---

# Support

twinflow is a public portfolio project, built and maintained by one person on
personal time. Questions are welcome. Read this first, so you know where to put
yours and what comes back.

## Where to ask

| You want to                                                          | Go here                                                                                                         |
| -------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------- |
| Ask how something works, or why it is designed that way              | [Discussions](https://github.com/johnragonhall/twinflow/discussions)                                            |
| Report something that behaves differently from the docs or the tests | [Open a bug report](https://github.com/johnragonhall/twinflow/issues/new?template=bug_report.yml)               |
| Propose a capability or a change to an existing module               | [Open a feature request](https://github.com/johnragonhall/twinflow/issues/new?template=feature_request.yml)     |
| Add or amend a numbered roadmap milestone                            | [Open a roadmap milestone](https://github.com/johnragonhall/twinflow/issues/new?template=roadmap_milestone.yml) |
| Report a security vulnerability                                      | Do not file it here. Follow [SECURITY.md](SECURITY.md).                                                         |
| Contribute code                                                      | Read [CONTRIBUTING.md](CONTRIBUTING.md), then sign [CLA.md](CLA.md)                                             |
| Ask about a commercial license, a warranty, or an indemnity          | Read [LICENSING.md](LICENSING.md), then open a discussion                                                       |

Blank issues are turned off in `.github/ISSUE_TEMPLATE/config.yml`. The forms
exist for one reason. A report carrying a seed, a config fragment, and a
version is usually reproducible in one command. A report without them usually
is not.

## Before you ask

Search the open and closed issues, and the discussions. Roadmap milestones are
filed as issues, so a capability that looks missing is often already sequenced
with its dependencies recorded.

Read [ROADMAP.md](ROADMAP.md). Much of what this repository describes is
planned rather than built. A number the repository has not measured yet sits
inside a metric marker in the source text, and
`scripts/checks/metric-marker-gate.sh` counts the unfilled ones.

Include your run seed. On one platform, with one pinned dependency set, the
same run seed and the same config produce a byte-identical event log. That is
gate `VAL-GATE-DET-001` in [ROADMAP.md](ROADMAP.md). Across platforms the
weaker gate `VAL-GATE-DET-002` applies, which asserts equal values inside a
recorded tolerance rather than equal bytes. Either way the seed is the single
most useful line in a bug report.

## What is in scope

- Defects in twinflow itself. That covers the twin, the device fleet and sensor
  catalog, the broker, the UNS path, and the historian. It also covers the Lean
  Six Sigma engine, process mining, the agent and its accuracy stack, the
  dashboard, and the packaging.
- Questions about the design and the reasoning behind it, including the
  statistical choices.
- A reference value that looks wrong. That is a bug report and a welcome one.
  Name the published source you are checking against, with its edition and the
  page or table.
- Questions about modeling your own operation in `facility.yaml`.
- Questions about installing one package on its own, without the rest of the
  system.
- Portability problems on an operating system and Python version the CI matrix
  covers. `.github/workflows/ci.yml` is the list of record.

## What is out of scope

- General Lean Six Sigma, statistics, or supply chain consulting. How this
  repository builds a method is in scope. How to run an improvement program at
  your employer is not.
- Debugging your own fork, your own model, or your own data pipeline, where
  twinflow is not the thing misbehaving.
- Commercial support, service-level agreements, and guaranteed response times.
  Apache-2.0 disclaims warranties in section 7 and limits liability in section
  8. Section 9 is what lets a separate commercial agreement carry such terms,
  and [LICENSING.md](LICENSING.md) covers that path.
- Anything needing real, client, employer, or proprietary data. Every dataset
  here is synthetic and stays that way. Do not paste anything confidential into
  a public thread.

## What to expect

This is not a funded project and it has no support rota.

- Issues are read, usually within a few days. Being read is not the same as
  being fixed.
- A bug report carrying a seed, a config fragment, and a version gets looked at
  first, because it can be reproduced without a conversation.
- Feature requests are recorded on the roadmap rather than accepted or
  rejected. Nothing is deleted from the roadmap, and items are reordered. A
  request may sit for a long time behind its dependencies. That is the normal
  outcome, not a rejection.
- Security reports are handled on the timeline in [SECURITY.md](SECURITY.md),
  ahead of everything else here.
- Work happens in phases. During a phase the attention goes to that phase, and
  issues outside it wait.

A thread that goes quiet for a couple of weeks is fine to bump politely.

## Security

Do not report vulnerabilities through issues or discussions. Use the private
channel in [SECURITY.md](SECURITY.md). The threat model for the MCP and REST
surface is there too, including the boundary of the SQL and Python sandbox the <!-- docs-lint-ok STE-TERM-SYN the remote attack surface, not the verb "raise" -->
agent runs inside.
