---
title: Glossary
description: Every domain term this repository uses, grouped by field, with the meaning that binds here and the document that owns it.
topic_type: reference
audience: readers evaluating the project, and contributors
---

# Glossary

This repository draws on four fields that rarely share a reader: discrete-event
simulation, industrial control, Lean Six Sigma, and applied machine learning. A
sentence in [ARCHITECTURE.md](https://github.com/johnragonhall/twinflow/blob/main/ARCHITECTURE.md)
can carry a term from each. This page is the single place where each one is
defined.

Two kinds of entry appear below, and the difference matters.

An entry marked **local** is defined by this repository. Where a term has a
looser meaning in the wider industry, the meaning here is the narrow one, and
`docs/style/ste-terms.yml` holds the machine-checked form of that rule. The
prose gate rejects a declared synonym in a task or reference topic.

An entry marked **external** names a term owned by a standard or by an
established body of practice. This page states the sense in which the term is
used here. It does not quote the standard, and it is not a substitute for
reading it. Section 11 names the sources this repository validates its statistics
against. It is not a source list for every external term on this page.

## Contents

1. [Simulation and determinism](#1-simulation-and-determinism)
2. [Industrial control and the plant floor](#2-industrial-control-and-the-plant-floor)
3. [Telemetry and messaging](#3-telemetry-and-messaging)
4. [Lean Six Sigma and statistics](#4-lean-six-sigma-and-statistics)
5. [Warehouse and distribution operations](#5-warehouse-and-distribution-operations)
6. [Planning, inventory, and supply](#6-planning-inventory-and-supply)
7. [Process mining](#7-process-mining)
8. [The agent and its accuracy stack](#8-the-agent-and-its-accuracy-stack)
9. [Repository craft](#9-repository-craft)
10. [Declared verbs](#10-declared-verbs)
11. [External sources](#11-external-sources)

## 1. Simulation and determinism

| Term                      | Kind     | Meaning here                                                                                                                                                                                        |
| ------------------------- | -------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| twin                      | local    | The synchronized model of the operation. Three couplings make it a twin: it recalibrates from telemetry, its divergence from reality is itself a finding, and accepted changes flow back as config. |
| digital shadow            | external | A model fed by telemetry that sends nothing back. This repository builds a twin, not a shadow, and the README states the difference.                                                                |
| discrete-event simulation | external | A model that advances time by jumping to the next scheduled event, rather than by fixed increments. SimPy is the kernel, per decision D1.                                                           |
| sim clock                 | local    | The virtual clock service every timestamp derives from. Code outside the kernel package reads an injected `Clock`, never a wall clock.                                                              |
| paced clock               | local    | A mode that emits events in wall-clock time at a chosen rate, for watching a run. Pacing changes when an event appears, never which event or in what order.                                         |
| wall clock                | local    | Real time. Doctrine D-02 permits reading it in exactly four places, and in none of them does the value reach an event payload, the hashed tape, or control flow.                                    |
| run seed                  | local    | The single integer governing every stochastic stream in a run.                                                                                                                                      |
| child seed                | local    | A per-subsystem stream derived from the run seed by a content-addressed derivation, so a stream's identity comes from its name and not from a draw order.                                           |
| tape                      | local    | The ordered event log a run produces. Two runs that agree byte for byte have the same tape.                                                                                                         |
| event log                 | local    | The `events.ndjson` file a run writes. One event per line, in the canonical total order.                                                                                                            |
| run manifest              | local    | The record of what produced a run. Doctrine D-01 splits it into a hashed core and a provenance sidecar.                                                                                             |
| hashed core               | local    | The manifest fields that enter the log hash: seed, config hash, schema snapshot hash, scenario id, mode, tick rate, horizon, warmup, and fault schedule hash.                                       |
| provenance sidecar        | local    | The manifest fields deliberately kept out of the hash, written to `manifest.json`. It holds wall-clock start and finish, git provenance, platform, and package versions.                            |
| what-if                   | local    | A twin experiment that applies a config change and measures the delta against a baseline run.                                                                                                       |
| counterfactual            | local    | A replay of a recorded run through a changed config. Distinct from a what-if, which starts fresh.                                                                                                   |
| warmup                    | local    | The leading span of a run excluded from statistics, so measurements are not taken while the model is still filling.                                                                                 |
| horizon                   | local    | The simulated duration of a run.                                                                                                                                                                    |
| scenario                  | local    | A named, versioned run definition. `SCN-F1` is the determinism scenario the two-run hash match is asserted on.                                                                                      |
| fault injection           | local    | Introducing a fault from the labeled fault catalog into a run. The catalog supplies the ground-truth labels the detection comparison in D7 is scored against.                                       |
| special cause             | local    | Variation from an assignable source, injected from the fault catalog.                                                                                                                               |
| common cause              | local    | The inherent variation of a stable process. Telling a rare common-cause tail from a genuine special cause is the judgment the statistical engine exists to make.                                    |

Determinism here is scoped by doctrine D-05, which names two tiers. Tier one is
byte-identical logs on one platform at one pinned dependency set. Tier two is
identical business events across platforms, with continuous fields agreeing
inside a measured tolerance. Neither tier claims the operation is predictable.
Reproducing a run and forecasting the next hour are different properties.

## 2. Industrial control and the plant floor

| Term         | Kind     | Meaning here                                                                                                                                                                 |
| ------------ | -------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| ISA-95       | external | The standard for integrating enterprise and control systems. Its level model, from L0 sensors to L4 business systems, gives the topic hierarchy every device publishes into. |
| Purdue Model | external | The reference network segmentation for industrial control, layering L0 to L5. Section 7 of ARCHITECTURE.md puts it in the compose topology, not only in a diagram.           |
| ISA-88       | external | The batch control standard. It supplies the recipe model used by the upstream factory at phase P3i.                                                                          |
| IEC 62443    | external | The industrial automation and control systems security series. It supplies the zone and conduit model at phase 6a15.                                                         |
| OT           | external | Operational technology. The plant-floor segment: devices, gateways, and the broker they publish to.                                                                          |
| IT           | external | Information technology. The enterprise segment: the historian, the statistical engine, the agent, and the dashboard.                                                         |
| bridge       | local    | The single crossing point between the OT and IT segments. Milestone RA-b lands the test asserting no device container is reachable from the IT segment.                      |
| edge gateway | local    | The device that collects local telemetry, buffers it across a link outage, and publishes north to the site broker.                                                           |
| PLC          | external | Programmable logic controller. The default path models one rather than talking to one, and the README says so.                                                               |
| OPC UA       | external | The OPC Unified Architecture protocol for industrial data exchange. A bridge is a roadmap milestone at P5, not a current capability.                                         |

## 3. Telemetry and messaging

| Term                | Kind     | Meaning here                                                                                                                                                                                   |
| ------------------- | -------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| UNS                 | local    | The unified namespace: the ISA-95 topic hierarchy every device publishes into, and the single place the current state of the operation is readable.                                            |
| MQTT                | external | The publish and subscribe messaging protocol the fleet runs over. Three brokers fill three roles, per decisions D3 to D5.                                                                      |
| Sparkplug B         | external | The Eclipse specification, at version 3.0.0, that fixes the payload format and the session lifecycle over MQTT. Every normative statement in it carries a `tck-id`, so compliance is testable. |
| birth certificate   | local    | The Sparkplug NBIRTH or DBIRTH message declaring a node or device online, and declaring its full metric model.                                                                                 |
| death certificate   | local    | The Sparkplug NDEATH or DDEATH message. NDEATH arrives through the MQTT Last Will, which marks a node stale rather than leaving it silently frozen.                                            |
| report by exception | external | Publishing a metric only when it changes, rather than on every cycle. NDATA and DDATA carry these updates after the birth certificate has declared the model.                                  |
| metric aliasing     | external | Replacing a metric name with a short integer after the birth certificate has bound the two, which cuts payload size on every later message.                                                    |
| store and forward   | local    | Buffering telemetry during an outage and replaying it on reconnect.                                                                                                                            |
| historian           | local    | The L2 time-series system of record. It is append-only and event-sourced, so a recorded run can be replayed rather than only summarized.                                                       |
| device twin         | local    | The desired and reported state pair held for each device.                                                                                                                                      |
| EPCIS               | external | The GS1 standard for supply chain event data. Its 2.0 event vocabulary lands at phase P3, and it answers what, when, where, and why for a traceable object.                                    |

## 4. Lean Six Sigma and statistics

| Term                   | Kind     | Meaning here                                                                                                                                            |
| ---------------------- | -------- | ------------------------------------------------------------------------------------------------------------------------------------------------------- |
| takt                   | local    | Available time divided by customer demand. The rate the operation must run at to meet demand.                                                           |
| cycle time             | external | The time one unit takes to pass through a step.                                                                                                         |
| WIP                    | external | Work in process. The count of units inside the system and not yet finished.                                                                             |
| OEE                    | external | Overall equipment effectiveness, the product of availability, performance, and quality.                                                                 |
| bottleneck             | external | The resource whose capacity sets the throughput of the whole line.                                                                                      |
| SPC                    | external | Statistical process control. Judging a process by whether its variation is stable, rather than by whether a single reading is inside a specification.   |
| control chart          | external | A time-ordered plot with control limits derived from the process itself, not from the specification.                                                    |
| Western Electric rules | external | A published set of control chart patterns that identify an out-of-control signal. The engine emits the rule number, not a generic alarm.                |
| Nelson rules           | external | A second published pattern set covering the same job, with different sensitivities.                                                                     |
| violation              | local    | A control chart rule breach, identified by rule number.                                                                                                 |
| finding                | local    | A typed judgment the statistical engine raises, carrying a severity and its evidence window. Never called an alert, an insight, or an observation.      |
| process capability     | external | How well a stable process fits inside its specification limits. Cp and Cpk describe short-term capability, Pp and Ppk the long-term form.               |
| Gage R and R           | external | Gage repeatability and reproducibility. It separates variation coming from the measurement system from variation coming from the process.               |
| MSA                    | external | Measurement system analysis, the family Gage R and R belongs to. It asks whether the measurement can be trusted before the process is judged.           |
| repeatability          | external | Variation seen when one operator measures the same part twice.                                                                                          |
| reproducibility        | external | Variation seen between operators measuring the same part.                                                                                               |
| ANOVA                  | external | Analysis of variance. It splits total variation into named sources, and it is the method behind the Gage R and R error terms.                           |
| assumption checker     | local    | The component that tests the preconditions of a hypothesis test before the test runs, so a p-value is not reported for a test whose assumptions failed. |
| value stream map       | external | The Lean drawing of material and information flow across a process, with the waiting time between steps made visible.                                   |
| SMED                   | external | Single-minute exchange of die. The method for cutting changeover time.                                                                                  |
| COPQ                   | external | Cost of poor quality. The money a defect costs once scrap, rework, and warranty are counted.                                                            |
| capability report      | local    | The generated HTML report for a time window, naming the Gage R and R convention it used.                                                                |

The Gage R and R F-test needs a stated convention, because the published ones
disagree about the error term for the operator effect. The README records the
split as the CRAN documentation for the R SixSigma package states it. This
repository builds both error terms, tests each against its own published
example, and names the convention in every generated report.

## 5. Warehouse and distribution operations

| Term          | Kind     | Meaning here                                                                                                                            |
| ------------- | -------- | --------------------------------------------------------------------------------------------------------------------------------------- |
| receiving     | local    | Taking material off an inbound vehicle and recording it. The first station modeled, at phase P1.                                        |
| putaway       | local    | Moving received material to its storage location. One word, no hyphen.                                                                  |
| slotting      | local    | Assigning a SKU to a storage location.                                                                                                  |
| cross-dock    | local    | Moving inbound material to an outbound door without storing it.                                                                         |
| AMR           | local    | Autonomous mobile robot.                                                                                                                |
| ASRS          | external | Automated storage and retrieval system.                                                                                                 |
| sortation     | external | The automated diverting of units to lanes by destination.                                                                               |
| palletizer    | external | The cell that builds a pallet from incoming cases.                                                                                      |
| cartonization | external | Choosing which carton sizes an order packs into.                                                                                        |
| perfect order | local    | An order complete, on time, damage free, and correctly invoiced.                                                                        |
| OTIF          | external | On time in full. The share of orders delivered complete and on schedule.                                                                |
| fill rate     | external | The share of demand met from stock on hand.                                                                                             |
| RFID portal   | local    | A fixed reader at a doorway that reads tags as material passes. RF physics and read-zone modeling land at phase P3.                     |
| read zone     | local    | The physical volume in which a portal can read a tag. Modeling it is what makes a missed read a modeled event rather than a random one. |

## 6. Planning, inventory, and supply

| Term                     | Kind     | Meaning here                                                                                                                                                                       |
| ------------------------ | -------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| S&OP                     | external | Sales and operations planning. The monthly cycle that reconciles demand, supply, and finance into one plan.                                                                        |
| SIOP                     | external | Sales, inventory, and operations planning. The same cycle, named to keep inventory explicit.                                                                                       |
| S&OE                     | external | Sales and operations execution. The weekly tick that handles what the monthly plan did not foresee.                                                                                |
| ATP                      | external | Available to promise. Whether stock exists to commit to an order.                                                                                                                  |
| CTP                      | external | Capable to promise. Whether capacity exists to make and deliver it.                                                                                                                |
| ABC and XYZ segmentation | external | Two rankings of the same catalog. ABC ranks items by value contribution, so control effort follows the money. XYZ ranks them by demand variability, which is a different question. |
| MEIO                     | external | Multi-echelon inventory optimization. Deciding where in a network safety stock sits, rather than setting each site alone.                                                          |
| newsvendor               | external | The single-period stocking model that balances the cost of too much against the cost of too little.                                                                                |
| guaranteed service time  | external | The service-time framing of multi-echelon stock placement.                                                                                                                         |
| risk pooling             | external | Holding stock centrally so variability across locations partly cancels.                                                                                                            |
| conformal prediction     | external | A method that turns a point forecast into an interval with a stated coverage guarantee. It is what makes a forecast consumable by an optimizer.                                    |
| forecasting arena        | local    | The harness that runs every forecasting model over the same backtest windows on this project's own series, and publishes the table. It imports no winner from a benchmark paper.   |

## 7. Process mining

`twinflow-procmine` is written in this repository under Apache-2.0, because
PM4Py is AGPL-3.0 and section 13 of that license reaches a network-served work.
Doctrine ruling D-14 settles it, and decision D8 records the reasoning.

| Term                       | Kind     | Meaning here                                                                                                                                                                             |
| -------------------------- | -------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| process discovery          | external | Deriving a process model from an event log.                                                                                                                                              |
| directly-follows graph     | external | The graph of which activity follows which, and how often. The simplest discovered model, and the input to richer ones.                                                                   |
| inductive miner            | external | A discovery algorithm that splits the log recursively and returns a model with sound structure by construction.                                                                          |
| conformance checking       | external | Measuring how far a real log departs from a reference model.                                                                                                                             |
| token-based replay         | external | Conformance measured by pushing the log through a Petri net and counting the tokens missing or left behind.                                                                              |
| alignment                  | external | Conformance measured by finding the cheapest correspondence between a trace and a model run. Computed here as A star search over the synchronous product net.                            |
| variant analysis           | external | Grouping traces by their activity sequence, so the common paths and the rare ones separate.                                                                                              |
| rework loop                | local    | A repeated activity in a trace that indicates work redone rather than work advanced.                                                                                                     |
| ground-truth process model | local    | The twin's own designed process. Because this repository owns the reference model, discovery can be scored on how well it recovers a known answer. No external library closes that loop. |

## 8. The agent and its accuracy stack

The target is that the agent never states a number it did not get from an
execution. Seven layers enforce it, and the README lists all seven.

| Term                         | Kind     | Meaning here                                                                                                                                                      |
| ---------------------------- | -------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| execution-grounded answer    | local    | A quantitative answer produced by running generated SQL or Python against the historian in a sandbox, and reporting the execution result.                         |
| governed semantic metric     | local    | A metric defined once in YAML with exact SQL, so the model picks a metric rather than writing its own aggregation.                                                |
| execution-based verification | local    | Running every generated query before the answer ships, and feeding errors, empty results, and out-of-range magnitudes back for bounded retries.                   |
| constrained decoding         | external | Restricting token generation so the output must match a schema. It gives the local model path the same structural guarantee a hosted structured-output API gives. |
| self-consistency             | local    | Sampling several query programs for a hard question and executing all of them. The modal result answers, and no majority marks the question.                      |
| grounding checker            | local    | The component that refuses to ship a sentence carrying a number matching no logged query result id.                                                               |
| calibrated abstention        | local    | Saying the twin lacks the data to answer reliably, below a threshold set by calibration rather than by taste.                                                     |
| eval suite                   | local    | The versioned set of operational questions with known answers that the agent is scored against.                                                                   |
| MCP                          | external | The Model Context Protocol. The server, its threat model, and its red-team suite land at phase P3.                                                                |

Layers three to seven ship as `twinflow-accuracy`, which installs with no LLM
SDK. A team that already has an agent can take the grounding checker alone.

## 9. Repository craft

| Term                | Kind  | Meaning here                                                                                                                                                     |
| ------------------- | ----- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| brick               | local | A package that installs alone and drags in nothing else. `test_brick_isolated.py` in each package asserts it.                                                    |
| milestone           | local | One idea, with an id that never changes and is never removed. Reordering is allowed and recorded. Deletion is not.                                               |
| work package        | local | The unit of delivery inside a phase, tracked in `roadmap.yaml` with a status.                                                                                    |
| phase               | local | A group of work packages ending at one tagged release. One minor version per phase.                                                                              |
| VAL-GATE            | local | A validation gate. A named assertion, its falsifier, and the command that runs it.                                                                               |
| standing gate       | local | A gate that re-runs at every later phase exit, not only at the phase that introduced it.                                                                         |
| gate status         | local | One of `declared`, `specified`, or `implemented`. The required field set widens with each, so a subsystem must declare its gates one phase before building them. |
| doctrine ruling     | local | A binding cross-cutting decision in DOCTRINE.md, cited as `D-01` and up, that every design section obeys. Where a section disagrees, the ruling wins.            |
| technology decision | local | A recorded choice of tool or approach in section 1 of ARCHITECTURE.md, cited as `D1` and up. Distinct from a doctrine ruling despite the similar id.             |
| decision register   | local | One of the three places a decision lives. [adr/index.md](adr/index.md) is the index of record and holds the id range each register uses.                         |
| metric marker       | local | An HTML comment pair holding a quantitative result. `TBD` means unmeasured, and a release cannot be tagged while it owes a marker.                               |
| known-answer test   | local | A test that checks generated values against a frozen corpus, so a change in the generator is caught rather than absorbed.                                        |
| property-based test | local | A test that asserts an invariant over generated inputs, rather than over one example. Hypothesis is the tool.                                                    |
| phase-exit runner   | local | The command that runs every gate in force at a phase. A gate in that set which is not `implemented` fails the run rather than being skipped.                     |

## 10. Declared verbs

`docs/style/ste-terms.yml` declares six verbs and the nouns above. One
verb carries one meaning, and the prose gate rejects the listed synonym for it in
a task or reference topic.

| Verb        | Means here                                          | Not                                         |
| ----------- | --------------------------------------------------- | ------------------------------------------- |
| publish     | Send a message to a UNS topic                       | emit, push, send out, broadcast             |
| replay      | Re-execute a recorded event log                     | rerun, playback, re-simulate                |
| recalibrate | Adjust twin parameters from observed telemetry      | retune, adjust, sync up                     |
| inject      | Introduce a fault from the fault catalog into a run | trigger, simulate a failure, cause          |
| raise       | Create a finding                                    | fire, throw, generate an alert, surface     |
| seed        | Initialize a stochastic stream from a seed value    | initialize randomness, set the random state |

## 11. External sources

Each row names a source this repository validates a statistic against, and what
that source covers. Nothing on this page quotes those documents, and several of
them are sold rather than published.

| Source                                                                                  | Covers                                                                                                                           |
| --------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------- |
| ISA-95, ISA-88, and IEC 62443, from the International Society of Automation and the IEC | The level model, the batch recipe model, and the industrial security zone model                                                  |
| The Purdue Enterprise Reference Architecture                                            | The network layering L0 to L5                                                                                                    |
| Eclipse Sparkplug B, version 3.0.0                                                      | The payload format, the session lifecycle, and the `tck-id` compliance statements                                                |
| GS1 EPCIS 2.0                                                                           | The supply chain event vocabulary                                                                                                |
| NIST Statistical Reference Datasets                                                     | Certified values for univariate statistics, ANOVA, and regression                                                                |
| NIST/SEMATECH e-Handbook of Statistical Methods, chapter 6                              | Control charts, process capability, and acceptance sampling                                                                      |
| The CRAN documentation for the R SixSigma package                                       | The two published Gage R and R F-test error terms                                                                                |
| The AIAG Measurement Systems Analysis manual                                            | The measurement analysis conventions. Sold rather than published, and reported here only as the SixSigma documentation states it |

For how this repository decides what a source can be cited for, read doctrine
ruling D-11 on validation evidence.
