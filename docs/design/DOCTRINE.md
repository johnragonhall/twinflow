---
title: Cross-cutting doctrine
description: Binding rulings on determinism, the event envelope, ports, packaging, validation evidence, and process mining that every spec section must follow.
topic_type: reference
audience: contributors
---

# Cross-cutting doctrine

An adversarial review of the fourteen design sections found 242 contradictions, 69 dropped
requirements, 120 untestable claims, and 22 determinism leaks. Most were local. The ones
below were not: the same defect appeared in three or more sections, which means each
section had invented its own answer.

This page holds the single answer. Every ruling has an id. Where a section disagrees with a
ruling, the ruling wins and the section changes. Cite the id in the section that applies it.

## D-01 The event log hash covers a hashed core, not the whole manifest

**Problem.** `RunManifest` carries `started_wall_utc`, git provenance, and a platform
fingerprint, and it sits inside `run_started`, the first event in the log. The log hash
so covers wall-clock and machine identity. Two runs seconds apart can never match,
so C1's byte-identical guarantee fails on its own first event, and the cross-platform gate
fails by construction.

**Ruling.** Split the manifest.

| Part               | Contents                                                                                                    | In the hash |
|--------------------|-------------------------------------------------------------------------------------------------------------|-------------|
| Hashed core        | seed, config hash, schema snapshot hash, scenario id, mode, tick rate, horizon, warmup, fault schedule hash | Yes         |
| Provenance sidecar | started_wall_utc, finished_wall_utc, git sha and dirty flag, platform, package versions, host               | No          |

`run_started` carries the hashed core only. The sidecar is written to `manifest.json` beside
`events.ndjson`. A unit test named `test_run_started_carries_no_wall_clock_or_platform_field`
asserts the carve-out so it cannot regress silently.

## D-02 Wall-clock reads are legal in exactly four places

**Problem.** Wall-clock values reach event payloads and control flow across at least four
sections. `PacedClock` reads the real monotonic clock from inside simulation mode.

**Ruling.** A wall clock may be read only by: the provenance sidecar writer (D-01), the
paced-clock pacer, the observability exporter, and operator-facing log lines. In all four,
the value never enters an event payload, never enters the hashed tape, and never steers
control flow.

The paced clock is the one apparent exception and it is not one. Pacing changes when an
event is emitted in wall time. It never changes which event is emitted or in what order.
`test_pacing_does_not_change_the_tape` asserts a paced run and an unpaced run produce
identical logs.

Everything else reads `Clock`, which is injected. The nondeterminism gate in
`scripts/checks/nondeterminism-gate.sh` enforces this outside the kernel package.

## D-03 Iteration order is explicit everywhere

**Problem.** Several domain fields are typed as Python sets of strings and iterated. Set
iteration order depends on hash randomization, so the tape changes between processes.

**Ruling.** No collection whose iteration order can reach an event, a hash, or a control
decision is a `set`. Use a sorted sequence, or sort at the iteration site with an explicit
key. Where a set is the right semantic type, iterate as `sorted(s)` and say why in a
comment. Dict iteration is insertion-ordered in the supported Python versions and is
permitted, but any dict built from a set or from concurrent inserts is sorted before use.
CI runs the determinism scenario twice with different `PYTHONHASHSEED` values and compares
hashes.

## D-04 Solvers and learned models are deterministic or they are outside the tape

**Problem.** A CP-SAT solve is bounded by wall-clock seconds and its output steers the
simulation. Reinforcement-learning dispatch runs torch inference inside the simulation loop
with no seeding contract. Both make the tape depend on machine speed.

**Ruling.** Any component whose output steers the simulation is bounded deterministically,
never by wall time. Constraint solvers are bounded by a deterministic budget (OR-Tools
exposes one) and by an iteration or branch cap, with a fixed worker count of one and a
fixed random seed. Learned models run with a pinned model artifact hash, a fixed seed, fixed
thread count, and deterministic kernels; inference happens through the `Inference` port so
simulation mode can bind a recorded-response adapter.

Where determinism cannot be achieved for a component, that component does not steer the
simulation. It becomes an advisory output recorded in the sidecar, and the tape records the
decision it produced rather than recomputing it on replay.

## D-05 The determinism claim is scoped honestly

**Problem.** Distributions sample floats and round to ticks, which makes the tape sensitive
to one-unit-in-last-place differences in `log`, `exp`, and `erfinv` across platforms and
SIMD dispatch. A cross-platform byte-identity claim cannot be supported.

**Ruling.** Two tiers, and the README states both rather than the stronger one alone.

| Tier             | Guarantee                                                         | Gate                                                                                                                       |
|------------------|-------------------------------------------------------------------|----------------------------------------------------------------------------------------------------------------------------|
| Byte-identical   | Same seed, same config, same platform, same pinned dependency set | Hash equality                                                                                                              |
| Value-equivalent | Same seed and config across platforms                             | Business events identical; continuous fields agree within a stated tolerance derived from measured divergence, not assumed |

The cross-platform gate reports the observed maximum divergence rather than asserting a
number chosen in advance. If it exceeds the tolerance, the tolerance was wrong or a real
defect exists, and the gate names which.

## D-06 The Rust device agent has an RNG contract

**Problem.** C1 guarantees one seed governs every stochastic stream, and the Rust agent had
no RNG contract at all, which is a hole at the boundary the project is proudest of.

**Ruling.** The agent derives its stream from the run seed and its device id using the same
name-addressed derivation the Python side uses, specified byte for byte in
`docs/design/variability-and-faults.md`. A cross-language conformance test asserts that the
Python and Rust implementations produce identical draws for the same stream name and seed.
The derivation is specified in terms of a named hash function and a named bit generator, not
in terms of whichever library either language happens to use.

## D-07 The event envelope, settled before Phase 0 freezes schemas

**Problem.** The envelope asserts a sequence number dense across all producers. Garage tier
already runs several containers plus the Rust agent, and the enterprise log is partitioned.
A single global counter has no allocator and cannot have one.

**Ruling.** The envelope carries `producer_id`. The sequence number is dense per
`(run_id, producer_id)`. The canonical total order is `(sim_ts, producer_id, seq)`.

This is decided now because adding an envelope field after Phase 0 is a major version bump
on every schema subject. The pagination cursor and the replay reader both use the total
order above.

## D-08 Two ports, not one

**Problem.** The `Network` port is MQTT-shaped: retained messages, quality of service, last
will and testament, wildcard subscription. Sparkplug B v3.0.0 death certificates ride on
last will and testament. The enterprise tier bound this port to a partitioned log, which
provides none of those.

**Ruling.** Separate the ports.

| Port       | Shape                                            | Adapters                                |
|------------|--------------------------------------------------|-----------------------------------------|
| `Network`  | MQTT: retain, QoS, last will, wildcard subscribe | InMemory, Mosquitto, EMQX, NanoMQ       |
| `EventBus` | Subject-addressed fan-out, no retain, no will    | InMemory, partitioned log at enterprise |

The device fleet and Sparkplug always use `Network`. Analytics fan-out uses `EventBus`. At
enterprise tier the broker bridges MQTT at the operational edge into the partitioned log at
the information layer, which is what real segmented architectures do. The adapter
conformance suite splits accordingly.

## D-09 One owner per public symbol, and layering is declared

**Problem.** Two packages each declared ownership of the same two classes. One package's
declared dependencies could not support its declared public API. A circular dependency
existed between two others.

**Ruling.** Every public symbol has exactly one owning package. Other packages import it;
they do not redeclare it. Shared value types that would otherwise force a heavy dependency
downward live in the leaf schema package and are re-exported. A CI test walks the import
graph and fails on a cycle, and a second test asserts every name in each package's `__all__`
is defined in that package.

## D-10 Heavy dependencies are optional extras

**Problem.** A port signature required a columnar library while the kernel claimed its core
install was two packages and nothing else, which breaks the take-one-brick promise.

**Ruling.** The kernel core install stays minimal. Any port whose signature would drag a
heavy dependency uses a protocol typed against a narrow structural interface, with the
concrete type imported only under `TYPE_CHECKING`. Heavy adapters ship as extras. A CI job
installs each package alone in a clean environment and imports it, so the claim that a brick
installs alone is tested rather than asserted.

## D-11 Validation gates carry real external evidence

**Problem.** Four gates cited this repository as their own published reference. One asserted
agreement to nine decimal places against a value printed to three in a manual. One had a
tolerance roughly twenty five times narrower than the Monte Carlo noise of its own
experiment. One used a placebo criterion that is a coin flip under the null hypothesis.

**Ruling.** Every gate satisfies all five conditions.

1. It names a specific external published reference, with edition and locator. This
   repository is never a reference for itself.
2. Its tolerance is never tighter than the precision of the published value it checks. A
   value printed to three decimals is checked to three decimals.
3. A gate over a stochastic quantity states its noise floor and sets its tolerance above it.
   The noise floor is measured, not assumed.
4. A gate states what result would falsify it. A criterion that passes about half the time
   under the null is not a gate.
5. A statistic with no valid external reference is recorded as an open question. It is never
   recorded as a passing gate.

Confidence tiers apply. A claim verified from primary text ships plainly. A claim from a
single secondary source ships with in-text attribution. An unverified claim never ships as
fact.

## D-12 A test that cannot fail is not a test

**Problem.** The proof that deployment tiers differ only by configuration compared two
runtimes that the binding rules make identical, so it asserted a tautology. A required
metrics test was written so that no state of the world could fail it.

**Ruling.** `simulation.mode` selects the port family. `deployment.adapters` selects within
the production family and is rejected at config validation when the mode is simulation. The
tier-portability proof runs the same scenario in production mode against two real adapter
stacks and compares business events under a documented normalization, which makes it an
integration test that belongs in the container job.

More generally, every test states the observation that would fail it. A test whose failure
condition cannot be described is deleted and replaced.

## D-13 Timing tests are scoped to fit their budget

**Problem.** Two determinism tests cannot fit the budgets the same document sets. One needs
about 29 minutes inside a 6 minute job.

**Ruling.** Paced-clock behavior is proved on a short scenario of about 60 simulated
seconds, not on a full simulated day. Property tests over the speed multiplier clamp the
lower bound so the worst case fits the job budget, and the clamp lives in the generator, not
only in the config validator. A budget test asserts the arithmetic, so a scenario that grows
past its job budget fails as a defect rather than as a timeout.

## D-14 twinflow implements its own process mining

**Problem.** PM4Py, the recommended engine, is AGPL-3.0, as is `pm4pyminimal` (verified
against the package index, version 2.7.23.3). Section 13 of that license triggers on network
interaction, and this project serves a dashboard, an MCP server, and an HTTP API. Importing
it would place the whole work under AGPL. That contradicts the Apache-2.0 and commercial
dual license, and it bans the repository at the employers it exists to reach.

**Ruling.** `twinflow-procmine` is written here, under Apache-2.0. It implements the
directly-follows graph, the inductive miner, token-based replay, alignment-based conformance
as A star search over the synchronous product net, variant analysis, rework-loop detection,
and per-activity cycle-time contribution.

This is an upgrade, not a substitute. The project already required something no external
library provides: the twin is the designed reference model, so conformance is measured
against a known ground-truth process and the repository can report how well discovery
recovers it. Owning the miner closes that loop. It also produces a permissively licensed
process mining package, which does not currently exist in this ecosystem, and that feeds the
adoption story with something the ecosystem actually lacks.

PM4Py remains available as a development-only validation oracle, compared against in CI
without being distributed or served, which gives the conformance gates a real external
reference under D-11. That arrangement needs the owner's own legal read before release.

No other locked dependency has this problem. SimPy is MIT, deltalake is Apache-2.0, DuckDB
is MIT, statsforecast is Apache-2.0, Optuna is MIT, and DoWhy is MIT.

## Sections that must change

| Ruling | Sections affected                                                |
|--------|------------------------------------------------------------------|
| D-01   | foundations                                                      |
| D-02   | foundations, twin-core, ai-layer, iot-fleet                      |
| D-03   | foundations, twin-core, planning-supply, back-office             |
| D-04   | twin-core, planning-supply, ai-layer                             |
| D-05   | foundations, repo-craft, dashboard-replay, roadmap               |
| D-06   | iot-fleet, foundations                                           |
| D-07   | foundations, iot-fleet, and every section that declares an event |
| D-08   | foundations, iot-fleet                                           |
| D-09   | foundations, ai-layer, human-sustain                             |
| D-10   | foundations, repo-craft                                          |
| D-11   | lss-engine, ai-layer, production-quality, human-sustain, roadmap |
| D-12   | foundations, ai-layer, repo-craft                                |
| D-13   | foundations, repo-craft                                          |
| D-14   | lss-engine, roadmap, repo-craft                                  |
