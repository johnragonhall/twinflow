---
title: Reading guide
description: Three routes through this repository, sized to fifteen minutes, one hour, and a full contributor onboarding, with the commands that check each claim.
topic_type: task
audience: readers evaluating the project, and contributors
---

# Reading guide

This repository holds more planning than code, on purpose, and the planning
files are large. ROADMAP.md and ARCHITECTURE.md together run past two hundred
kilobytes. Reading them front to back is the wrong first move.

Pick the route that matches the time you have.

## Contents

1. [Before you start: what is built](#1-before-you-start-what-is-built)
2. [Route A: fifteen minutes](#2-route-a-fifteen-minutes)
3. [Route B: one hour](#3-route-b-one-hour)
4. [Route C: contributing](#4-route-c-contributing)
5. [Go straight to the part you care about](#5-go-straight-to-the-part-you-care-about)
6. [Check the claims yourself](#6-check-the-claims-yourself)
7. [What is not here](#7-what-is-not-here)

## 1. Before you start: what is built

Phase P0 is the contract phase. It ships no product. It fixes the decisions a
later phase cannot change without invalidating every run already recorded.

| Question                        | Answer today                                                                                                          |
| ------------------------------- | --------------------------------------------------------------------------------------------------------------------- |
| What is tagged                  | v0.1.0, the P0 contracts release                                                                                      |
| What installs                   | `twinflow-schemas`, `twinflow-rng`, `twinflow-kernel`, `twinflow-config`, and the `twinflow-roadmap` tool, each alone |
| What runs                       | A determinism scenario, `SCN-F1`, which writes an event log and matches its own hash across two runs                  |
| What does not exist             | The station model, the device fleet, the statistical engine, the agent, and the dashboard                             |
| Gates in force at the P0 exit   | Twelve, all of them implemented and runnable                                                                          |
| Gates declared for later phases | 138 in total, each carrying the phase it starts at                                                                    |

A reader who wants a running warehouse will not find one. A reader who wants to
see how someone sets up a system so that its later numbers can be trusted is in
the right place.

## 2. Route A: fifteen minutes

This route answers one question: is the engineering here serious, or is it a
large plan with nothing underneath it.

1. Read [README.md](https://github.com/johnragonhall/twinflow#readme), and stop
   at the section named "Determinism, and what it does not mean". That section
   states a strong property and then removes the three overclaims it invites.
2. Read the metric marker comment block near the top of the same file. Every
   quantitative result sits inside a marker, every marker reads `TBD`, and a
   release cannot be tagged while it owes one. Nothing in this repository states
   a number it has not measured.
3. Open [DOCTRINE.md](design/DOCTRINE.md) and read ruling D-01 only. It is one
   page. It catches a defect that would have made the headline determinism
   claim fail on the first event of every log, and it fixes it by splitting the
   run manifest.
4. Open [gates.md](gates.md) and read the three-status table at the top. A gate
   must be declared one phase before the subsystem that satisfies it is built.
5. Skim section 5 of
   [ROADMAP.md](https://github.com/johnragonhall/twinflow/blob/main/ROADMAP.md),
   the resequencing record. It logs every change to the build order with the
   clause that forced it, because nothing is ever deleted from the plan.

If those five leave you unconvinced, the rest will not change your mind. If they
land, take Route B.

## 3. Route B: one hour

This route is for an engineer judging depth. Read in this order.

1. Section 1 of
   [ARCHITECTURE.md](https://github.com/johnragonhall/twinflow/blob/main/ARCHITECTURE.md),
   the technology decision record. Sixteen decisions, each with its rejected
   alternatives and the reason. Read the D16 note last: it explains why the
   random number generator is not numpy's default, and it is the one decision
   that argued its way to its own numeric ceiling.
2. Sections 2 and 4 of the same file: the dual-mode determinism argument, and
   the ISA-95 and Purdue layer map that gives every component a real-world
   counterpart.
3. All of [DOCTRINE.md](design/DOCTRINE.md). Fourteen rulings, each written
   because the same defect appeared in three or more design sections.
4. [foundations.md](design/foundations.md), which is the section the shipped
   packages were built from.
5. The code, in this order: `packages/twinflow-rng/src/twinflow/rng/derive.py`,
   then its tests, then `packages/twinflow-schemas/src/twinflow/schemas/envelope.py`.
   The RNG derivation is content-addressed, so a stream's identity comes from
   its name and not from the order it was requested in.
6. `justfile`, which is the whole task surface. CI calls the same recipes, so a
   green local run and a green CI run mean the same thing.

## 4. Route C: contributing

Read
[CONTRIBUTING.md](https://github.com/johnragonhall/twinflow/blob/main/CONTRIBUTING.md)
first, then these four in any order:

| Document                                                                             | Why you need it                                                  |
| ------------------------------------------------------------------------------------ | ---------------------------------------------------------------- |
| [ENGINEERING.md](https://github.com/johnragonhall/twinflow/blob/main/ENGINEERING.md) | The working method, and the rules a change is judged against     |
| [testing-strategy.md](testing-strategy.md)                                           | Which tier a new test belongs in, and what makes a test count    |
| [code-review.md](code-review.md)                                                     | What a reviewer checks, and what blocks a merge                  |
| [DOCUMENTATION-STANDARD.md](DOCUMENTATION-STANDARD.md)                               | The writing rules, and which of them CI enforces without a human |

Then run `just check` before you write anything, so you know what green looks
like on your machine.

## 5. Go straight to the part you care about

| If your interest is                      | Read                                                                                                              |
| ---------------------------------------- | ----------------------------------------------------------------------------------------------------------------- |
| Reproducible simulation                  | ARCHITECTURE.md section 2, doctrine D-01 to D-05, and `packages/twinflow-rng/`                                    |
| Industrial protocols and the plant floor | ARCHITECTURE.md sections 4 to 7, and [iot-fleet.md](design/iot-fleet.md)                                          |
| Statistics and quality engineering       | [lss-engine.md](design/lss-engine.md), and the validation table in README.md                                      |
| LLM accuracy and grounding               | [ai-layer.md](design/ai-layer.md), and the seven-layer list in README.md                                          |
| Repository and release engineering       | [repo-craft.md](design/repo-craft.md), the `justfile`, and `scripts/checks/`                                      |
| Software licensing in practice           | Decision D14, doctrine D-14, and [LICENSING.md](https://github.com/johnragonhall/twinflow/blob/main/LICENSING.md) |
| Technical writing under a standard       | [DOCUMENTATION-STANDARD.md](DOCUMENTATION-STANDARD.md) and `scripts/checks/prose-gate.py`                         |
| Terms you do not recognize               | [glossary.md](glossary.md)                                                                                        |

## 6. Check the claims yourself

Nothing on this page asks for trust. Each command below tests a claim made
above, and each one runs from a clean clone.

```bash
uv sync                  # install the workspace
just check               # lint, typecheck, and the fast test tier
just determinism         # the two-run hash match, plus the RNG known-answer corpus
just roadmap             # validate the plan, prove coverage, lint the dependency graph
just lint                # every gate that needs no container
```

`just roadmap coverage` is the one worth watching. It proves that every
milestone id recorded in the plan is placed in a phase. An id with no phase is a
silent cut, and this project keeps no cut list.

`just determinism` runs `SCN-F1` twice and compares the two event logs byte for
byte. One differing byte fails it.

## 7. What is not here

The repository states its own limits in README.md. The four that matter most to
a reader judging the work:

All data is synthetic. Every reading, event, order, and lot is generated by this
repository, and nothing here is evidence about any real facility.

No measured performance numbers exist. The scaling curve, the eval accuracy, and
the quickstart timing are all unfilled markers, and they stay unfilled until a
recorded run produces them.

No real control hardware is in the default path. The OT layer is simulated, and
an OPC UA bridge is a roadmap milestone rather than a current capability.

The statistical engine is validated, not certified. Checking outputs against
published reference values is reproducible evidence on the covered cases. It
does not make the software fit for regulated measurement or release decisions.
