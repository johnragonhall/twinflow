---
title: Decision records
description: The three decision registers this repository keeps, which one owns which kind of choice, and the numbering rule that keeps their ids apart.
topic_type: reference
audience: contributors, and readers evaluating the project
---

# Decision records

This repository records architecturally significant decisions in three
registers. Each one owns a different kind of choice, and a decision belongs to
exactly one of them.

A reader who wants the reasoning behind a tool choice goes to the technology
decision record. A reader who wants a rule that binds every design section goes
to the doctrine. A reader who wants a decision made after v0.1.0 that fits
neither goes to the numbered records in this directory.

## Contents

1. [The three registers](#1-the-three-registers)
2. [The numbering rule](#2-the-numbering-rule)
3. [When a decision needs a record](#3-when-a-decision-needs-a-record)
4. [Lifecycle](#4-lifecycle)
5. [Index of numbered records](#5-index-of-numbered-records)
6. [Cross-index: technology decisions](#6-cross-index-technology-decisions)
7. [Cross-index: doctrine rulings](#7-cross-index-doctrine-rulings)

## 1. The three registers

| Register                   | Id form           | Lives in                                                                                            | Owns                                                                                            |
| -------------------------- | ----------------- | --------------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------- |
| Technology decision record | `D1` to `D16`     | Section 1 of [ARCHITECTURE.md](https://github.com/johnragonhall/twinflow/blob/main/ARCHITECTURE.md) | The choice of a library, protocol, format, or license, with its alternatives                    |
| Cross-cutting doctrine     | `D-01` to `D-14`  | [DOCTRINE.md](../design/DOCTRINE.md)                                                                | A rule that binds every design section, written because three or more invented their own answer |
| Numbered decision records  | `ADR-0001` onward | This directory                                                                                      | Any other architecturally significant decision taken after v0.1.0                               |

The first two are tables and rulings inside larger documents, and they stay
there. Moving them would break every citation in the fourteen design sections
and in the roadmap, and it would put a second copy of each decision in the tree,
which section 6 of [ENGINEERING.md](https://github.com/johnragonhall/twinflow/blob/main/ENGINEERING.md)
forbids.

## 2. The numbering rule

`D1` and `D-01` are different decisions. The hyphen is the only thing that
tells them apart, and that is fragile enough to state as a rule rather than
leave as a convention.

Cite a decision by its register and its id together. Write "decision D1" or
"technology decision D1" for the first register, and "doctrine D-01" or "ruling
D-01" for the second. A bare `D1` in prose is ambiguous to a reader who has met
only one of the two registers.

New records take `ADR-NNNN`, which collides with neither. Numbers are assigned
in order and are never reused, including for a record that is later superseded.

The two existing registers keep their ids. Renumbering them is the alternative,
and it costs every citation across fourteen design sections, the roadmap, the
gate registry, and the commit history, in exchange for removing one hyphen of
ambiguity. Section 1 of ROADMAP.md fixes the rule that an id never changes, and
that rule is worth more than the tidier namespace.

## 3. When a decision needs a record

Write a record when the decision is hard to reverse and a later reader will ask
why. Three tests, and any one of them is enough:

1. Undoing it would invalidate runs already recorded, published schemas, or a
   released package API.
2. It rules out an approach a competent engineer would otherwise reach for.
3. It creates an obligation somebody has to keep, such as a license term, a
   compatibility promise, or a gate that must keep passing.

A decision failing all three is an implementation choice. It belongs in the code
and its comment, not here.

Which register takes it: a library, protocol, format, or license choice goes to
the technology decision record. A rule that more than one design section must
obey goes to the doctrine. Everything else gets an `ADR-NNNN` here.

## 4. Lifecycle

A record has one of four statuses.

| Status       | Meaning                                                                       |
| ------------ | ----------------------------------------------------------------------------- |
| `proposed`   | Written and open for argument. Not yet binding                                |
| `accepted`   | Binding. The decision is in force                                             |
| `superseded` | A later record replaced it. The header names which one                        |
| `deprecated` | No longer in force, and nothing replaced it. The header says what happens now |

An accepted record is not edited afterward. The text is what somebody decided,
with what they knew at the time, and rewriting it destroys the only evidence of
that. A decision that changes gets a new record whose header names the one it
supersedes, and the superseded record gains a status line and a pointer forward.
Nothing is deleted, which is the same rule the roadmap runs on.

## 5. Index of numbered records

| Record                                                                     | Title                                                               | Status   | Date       |
| -------------------------------------------------------------------------- | ------------------------------------------------------------------- | -------- | ---------- |
| [ADR-0001](0001-record-architecture-decisions.md)                          | Record architecture decisions                                       | accepted | 2026-08-13 |
| [ADR-0002](0002-implement-the-agent-seam-rather-than-adopt-pydantic-ai.md) | twinflow implements the agent seam rather than adopting Pydantic AI | accepted | 2026-08-13 |

Use [template.md](template.md) to write a new one.

## 6. Cross-index: technology decisions

Sixteen decisions, each with its rejected alternatives and its reason, in
section 1 of ARCHITECTURE.md. Eleven carry a longer note under the table.

One of them has since been amended by a numbered record. Decision D9 named
Pydantic AI, and ADR-0002 records why the run-time license allowlist refuses it
and what twinflow ships instead. The technology decision keeps its id and its
text, per section 2, and the row below points at the record that amends it.

| Id    | Decision                                 | Choice                                                                                                                   |
| ----- | ---------------------------------------- | ------------------------------------------------------------------------------------------------------------------------ |
| `D1`  | Discrete-event simulation kernel         | SimPy, so the project owns the RNG                                                                                       |
| `D2`  | Batch table format and query engine      | delta-rs writing Delta Lake, DuckDB querying through Arrow, no Spark                                                     |
| `D3`  | MQTT broker, garage tier                 | Eclipse Mosquitto                                                                                                        |
| `D4`  | MQTT broker, growth and enterprise tiers | EMQX                                                                                                                     |
| `D5`  | MQTT broker, edge-gateway tier           | NanoMQ                                                                                                                   |
| `D6`  | Device payload format                    | Eclipse Sparkplug B v3.0.0                                                                                               |
| `D7`  | Anomaly detection                        | Statistical baseline first, a learned model only when it beats it                                                        |
| `D8`  | Process mining                           | `twinflow-procmine`, written here, because PM4Py is AGPL-3.0                                                             |
| `D9`  | Agent framework                          | Pydantic AI, refused on its license tree. See [ADR-0002](0002-implement-the-agent-seam-rather-than-adopt-pydantic-ai.md) |
| `D10` | Local model path                         | Ollama with constrained decoding, so the demo needs no API key                                                           |
| `D11` | Forecasting                              | A statsforecast baseline arena, with challengers entered later                                                           |
| `D12` | Optimization                             | Optuna, native `GPSampler` and MOTPE                                                                                     |
| `D13` | Causal inference                         | DoWhy for the workflow, EconML for the estimators                                                                        |
| `D14` | Outbound license                         | Apache-2.0, plus a commercial option, plus `CLA.md`                                                                      |
| `D15` | Inbound dependency licenses              | Permissive only, and CI fails the build outside the allowlist                                                            |
| `D16` | RNG bit generator                        | `SeedSequence` with BLAKE2b spawn keys, feeding `PCG64DXSM`                                                              |

## 7. Cross-index: doctrine rulings

Fourteen rulings in [DOCTRINE.md](../design/DOCTRINE.md). Each exists because
the same defect appeared in three or more design sections, which means each
section had invented its own answer. Where a section disagrees with a ruling,
the ruling wins and the section changes.

| Id     | Ruling                                                                    |
| ------ | ------------------------------------------------------------------------- |
| `D-01` | The event log hash covers a hashed core, not the whole manifest           |
| `D-02` | Wall-clock reads are legal in exactly four places                         |
| `D-03` | Iteration order is explicit everywhere                                    |
| `D-04` | Solvers and learned models are deterministic or they are outside the tape |
| `D-05` | The determinism claim is scoped honestly, at two tiers                    |
| `D-06` | The Rust device agent has an RNG contract                                 |
| `D-07` | The event envelope is settled before Phase 0 freezes schemas              |
| `D-08` | Two ports, not one                                                        |
| `D-09` | One owner per public symbol, and layering is declared                     |
| `D-10` | Heavy dependencies are optional extras                                    |
| `D-11` | Validation gates carry real external evidence                             |
| `D-12` | A test that cannot fail is not a test                                     |
| `D-13` | Timing tests are scoped to fit their budget                               |
| `D-14` | twinflow implements its own process mining                                |
