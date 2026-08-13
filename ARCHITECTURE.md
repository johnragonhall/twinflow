---
title: Architecture
description: The decision record, dual-mode deterministic simulation design, stochastic model, ISA-95 layer map, namespace, compute placement, and network segmentation.
topic_type: concept
audience: contributors
---

# Architecture

This document covers seven things: the technology decision record, the dual-mode deterministic simulation design, the stochastic model, the ISA-95 and Purdue layer map, the unified namespace, compute placement, and network segmentation. Component behavior, roadmap sequencing, and adoption guidance live in other documents.

Every external fact in this document was checked against the primary text of its source, and the source is named at the point the claim is made. A claim here that names no source is a defect.

---

## 1. Technology decision record

Every row is a decision that has been made. The reason column is the answer given when the choice is challenged.

### Locked dependencies

Version and license were read from the Python Package Index on 2026-08-09, one JSON document per package.

| Package         | Version  | License    | Decision |
|-----------------|----------|------------|----------|
| `simpy`         | 4.1.2    | MIT        | D1       |
| `deltalake`     | 1.6.2    | Apache-2.0 | D2       |
| `duckdb`        | 1.5.5    | MIT        | D2       |
| `pydantic-ai`   | 2.27.0   | MIT        | D9       |
| `outlines`      | 1.3.3    | Apache-2.0 | D10      |
| `statsforecast` | 2.1.1    | Apache-2.0 | D11      |
| `optuna`        | 4.9.0    | MIT        | D12      |
| `dowhy`         | 0.14     | MIT        | D13      |
| `econml`        | 0.17.0   | MIT        | D13      |
| `pm4py`         | 2.7.23.3 | AGPL-3.0   | D8       |
| `salabim`       | 26.0.8   | MIT        | D1       |
| `hypothesis`    | 6.165.2  | MPL-2.0    | D15      |

`pm4py` is listed because it is rejected as a runtime dependency, not because it ships. `salabim` is listed as the considered alternative. Nothing is claimed here about `paho-mqtt`, `pyarrow`, `numpy`, or `scipy`, because their package metadata was not retrieved.

### Decisions

| #   | Decision                                 | Choice                                                                                                                                                                                          | Alternatives considered                                                           | Reason                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                         |
|-----|------------------------------------------|-------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|-----------------------------------------------------------------------------------|------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| D1  | Discrete-event simulation kernel         | SimPy 4.1.2                                                                                                                                                                                     | salabim, Ciw, Mesa, a hand-written event loop, commercial DES tools               | SimPy is "a process-based discrete-event simulation framework based on standard Python" whose processes "are defined by Python generator functions", per its own documentation. salabim is maintained, ships "real time 2D- and 3D-animation", monitors, and a yieldless mode. Its animation layer is redundant here, because a browser dashboard is already a requirement. SimPy's core is an event queue and a virtual clock, so the project owns the RNG, and the determinism requirement depends on owning it. See the D1 note.                                                            |
| D2  | Batch table format and query engine      | delta-rs, through the `deltalake` package, writing Delta Lake tables; DuckDB querying through Apache Arrow                                                                                      | PySpark plus Delta, plain Parquet, Apache Iceberg via `pyiceberg`, Postgres alone | The delta-rs README states that "Delta Lake is an open-source storage format that runs on top of existing data lakes" and is "compatible with processing engines like Apache Spark". Delta is the table format, DuckDB is the query engine, and Arrow is the handoff. delta-rs publishes the format as a Rust crate and a pip-installable Python package, so the quickstart has no Spark step and no cluster. See the D2 note.                                                                                                                                                                 |
| D3  | MQTT broker, garage tier                 | Eclipse Mosquitto                                                                                                                                                                               | EMQX everywhere, NanoMQ everywhere                                                | The Mosquitto project describes its broker as lightweight, covering "the MQTT protocol versions 5.0, 3.1.1 and 3.1". It is present in every distribution and every plant cupboard. The garage tier target is a laptop running one compose file.                                                                                                                                                                                                                                                                                                                                                |
| D4  | MQTT broker, growth and enterprise tiers | EMQX                                                                                                                                                                                            | HiveMQ, VerneMQ, RabbitMQ MQTT plugin, Kafka                                      | EMQX documentation states that "EMQX offers built-in support for Sparkplug B", with `spb_encode`, `spb_decode`, and alias mapping in the rule engine. EMQX documentation also describes broker-to-broker bridging and per-client certificate ACLs, which is what a second facility mirroring into the same namespace needs; that pair is a vendor claim this project has not yet measured.                                                                                                                                                                                                     |
| D5  | MQTT broker, edge-gateway tier           | NanoMQ                                                                                                                                                                                          | Mosquitto at the edge, no edge broker at all                                      | NanoMQ describes itself as "an Ultra-lightweight MQTT Broker for IoT Edge", which is the constrained gateway hardware this tier runs on. The bridge-and-buffer role, holding store-and-forward state across a site-link outage and replaying north on reconnect, is a NanoMQ documentation claim that the outage test measures rather than assumes. See the D3-D5 note.                                                                                                                                                                                                                        |
| D6  | Device payload format                    | Eclipse Sparkplug B v3.0.0                                                                                                                                                                      | Ad hoc JSON, bare Protobuf, JSON Schema over MQTT, OPC UA PubSub                  | Version 3.0.0, dated 2022-11-16 on its cover page, is the current specification, and the Eclipse revision history records no later version. It defines the session lifecycle the rest of the system relies on: NBIRTH and DBIRTH declare the full metric model, NDATA and DDATA report by exception, NDEATH via the MQTT Last Will marks a node stale rather than silently frozen. It runs over "MQTT v3.1.1 and MQTT v5.0". Every normative statement carries a `tck-id`, so compliance is testable rather than asserted.                                                                     |
| D7  | Anomaly detection                        | Control chart and EWMA statistical baseline first, Isolation Forest as the ML baseline, a learned model only when it beats both on labeled synthetic incidents, comparison published either way | Autoencoder, LSTM or transformer detector first                                   | The simulation supplies ground-truth labels, so the comparison is decidable here and the ML claim is falsifiable. Pinet and colleagues report of eight public multivariate benchmarks that "no cross-channel rupture occurs without an accompanying univariate deviation", and that a channel-dependent detector "brings no measurable gain" (arXiv:2606.02670, abstract). That is a reason to make a multivariate model earn its place. See the D7 note.                                                                                                                                      |
| D8  | Process mining                           | `twinflow-procmine`, written in this repository under Apache-2.0                                                                                                                                | PM4Py, ProM on the JVM, commercial process mining platforms                       | PM4Py 2.7.23.3 is AGPL-3.0. Section 13 of that license reaches every user "interacting with it remotely through a computer network", and this project serves a dashboard, an MCP server, and an HTTP API. Importing PM4Py would place the whole work under AGPL and break the Apache-2.0 plus commercial dual license. Doctrine ruling D-14 settles it. See the D8 note.                                                                                                                                                                                                                       |
| D9  | Agent framework                          | Pydantic AI 2.27.0                                                                                                                                                                              | LangChain or LangGraph, LlamaIndex, Semantic Kernel, raw provider SDK calls       | One interface across Anthropic, OpenAI, Gemini, and Ollama with a one-line model switch, and schema-guaranteed structured output with validation-retry. The structured-output guarantee is not a convenience here. It directly implements a required layer of the accuracy stack. Deliberately not LangChain: the requirement is a thin implementation a reader can inspect end to end. See the D9 note.                                                                                                                                                                                       |
| D10 | Local model path                         | Ollama with Outlines or XGrammar constrained decoding                                                                                                                                           | Hosted model only, llama.cpp directly                                             | The demo has to run with no API key and no cloud account. Constrained decoding gives the same schema guarantee locally that hosted providers give through their structured-output APIs, so the accuracy stack does not degrade when the key is absent.                                                                                                                                                                                                                                                                                                                                         |
| D11 | Forecasting                              | statsforecast (AutoARIMA, ETS, Theta) as the baseline arena, Chronos-2 and TimesFM entered later as challengers, conformal prediction for intervals                                             | Prophet, a deep model first, a foundation model first                             | Benchmarks published in 2026 disagree about when a foundation model beats a classical baseline. QuitoBench reports "a context-length crossover where deep learning models lead at short context" but "foundation models dominate at long context" (arXiv:2603.26017, abstract). A grid load-forecasting benchmark reports that Chronos-2 "demonstrates competitive zero-shot performance on two datasets but fails to accurately capture special events" (arXiv:2607.15705, abstract). A project that cannot read a winner out of the literature runs the comparison itself. See the D11 note. |
| D12 | Optimization                             | Optuna, native `GPSampler` for single-objective, MOTPE for multi-objective                                                                                                                      | scikit-optimize, Hyperopt, Ax and BoTorch, Nevergrad                              | `GPSampler` is documented as a "Sampler using Gaussian process-based Bayesian optimization", and it is native, so there is no second Bayesian dependency. What-if ranking is genuinely multi-objective across throughput, cost, energy, and operator impact, which is what MOTPE is for. Study persistence and pruning make long searches resumable.                                                                                                                                                                                                                                           |
| D13 | Causal inference                         | DoWhy for the model-identify-estimate-refute workflow, EconML for the estimators                                                                                                                | CausalML alone, hand-rolled regression adjustment, causal discovery only          | DoWhy documents a "separation between identification and estimation" and "a refutation and falsification API that can test causal assumptions for any estimation method". The four-step workflow forces the identifying assumptions to be written down, and the refutation step is what keeps the causal claim honest. EconML supplies heterogeneous treatment effect estimators through the same interface.                                                                                                                                                                                   |
| D14 | Outbound license                         | Apache-2.0, plus a separately negotiated commercial license, plus a contributor agreement in `CLA.md`                                                                                           | MIT, BSD-3-Clause, MPL-2.0, GPL-3.0, Apache-2.0 alone with no commercial option   | Section 4(b) makes a modified file "carry prominent notices stating that You changed the files", which is attribution that survives a fork. MIT has no equivalent. Section 3 grants an explicit patent license, and the MIT text contains no patent grant, so a downstream adopter's legal review closes one more question. Apache-2.0 is OSI approved. The commercial option only works when one party can relicense the whole work, which is why `CLA.md` exists. See the D14 note.                                                                                                          |
| D15 | Inbound dependency licenses              | Permissive only: MIT, BSD-2-Clause, BSD-3-Clause, ISC, Apache-2.0, Python-2.0                                                                                                                   | Case-by-case review, a boundary argument for copyleft, no stated policy           | `CONTRIBUTING.md` carries the table and CI fails the build on any resolved dependency outside it. GPL-2.0, GPL-3.0, and AGPL-3.0 are refused, because each pulls the whole work under copyleft and breaks both licensing options. That table is what forces D8. The table has no MPL-2.0 row, so the MPL-2.0 `hypothesis` dependency needs a recorded decision before it lands.                                                                                                                                                                                                                |
| D16 | RNG bit generator                        | numpy `SeedSequence` with content-addressed BLAKE2b spawn keys, feeding `PCG64DXSM` bit generators                                                                                              | `PCG64`, `SeedSequence.spawn(n)`, `jumped(k)` streams, Philox, SFC64              | numpy documents that a pair of `PCG64` streams whose lower 58 state bits agree fails the PractRand battery when interleaved, that a seeded increment gives no protection against that weakness, and that thousands of parallel streams are comfortable while millions are the point to consider `PCG64DXSM`. This project declares a ceiling of 750,000 streams, where the computed expectation is 9.8e-7 colliding pairs: small, and the only number in the design that argued for its own ceiling. `PCG64DXSM` seeds through the same routine, so only generation changes. See the D16 note. |

### D1 note: why not salabim

salabim is a reasonable library and the rejection is not about quality. Two specific reasons apply here. The animation layer, which is its most cited advantage, is redundant: the repo requires a browser dashboard driven by live state, so a desktop 2D and 3D animation window adds a second rendering path that nothing consumes. The second reason matters more. Determinism requires one seed governing every stochastic stream, split into named per-subsystem child streams, so that the same seed and config produce identical event logs under the scope stated in section 2. That is easiest when the simulation kernel does not own a random number generator of its own to be seeded, drawn from, or reseeded behind the project's back. SimPy's core is an event queue and a virtual clock and nothing else, so the RNG is entirely project-owned.

### D2 note: Delta without Spark

The requirement was a Delta Lake table on the batch path. The naive reading of that is PySpark, which drags in a JVM, a session, and a start-up cost that breaks the five-minute quickstart. delta-rs writes Delta tables, including the `_delta_log` transaction log, from a pip-installable Rust-backed Python package. DuckDB then reads them through Arrow with no copy. The split is deliberate: Delta is a table format, not a query engine, and treating it as both is the mistake. At the enterprise tier the same tables are readable by Spark, Databricks, or anything else that speaks the Delta protocol, which is the point of using the real format rather than Parquet plus a convention.

### D3-D5 note: three brokers, three roles

These are three different jobs, not three ways to do one job.

| Role                                        | Broker    | What it does                                                                                                          | What it does not do                    |
|---------------------------------------------|-----------|-----------------------------------------------------------------------------------------------------------------------|----------------------------------------|
| Embedded broker for the smallest deployment | Mosquitto | One process, one node, no clustering, no bridge topology                                                              | Multi-site, cluster failover           |
| Site and enterprise UNS broker              | EMQX      | Sparkplug-aware routing, per-client certificate ACLs, broker-to-broker bridging for multi-site federation, clustering | Run on a gateway with 256 MB of RAM    |
| Edge gateway broker                         | NanoMQ    | Local pub/sub for one area, store-and-forward buffer across a site-link outage, bridge north to the site broker       | Serve as the enterprise namespace root |

A reader who has run a plant will recognize this as the normal topology: a small broker per area doing buffering and protocol work, a real broker at site, and something minimal for a bench setup.

### D7 note: the baseline is the experiment

The anomaly layer publishes a comparison table on every release. It covers the statistical baseline, Isolation Forest, and any learned model, scored on the labeled synthetic incident catalog. Detection latency and false alarm rate sit alongside precision and recall. If the baseline wins, the table says so and the baseline ships.

The simulation supplies ground truth labels, which is the reason this comparison is possible here and is not possible on most real telemetry.

### D8 note: why the miner is written here

PM4Py 2.7.23.3 and `pm4pyminimal` 2.7.23.3 are both AGPL-3.0, read from their package metadata. AGPL-3.0 section 13 obliges a modified version to offer its Corresponding Source to "all users interacting with it remotely through a computer network". This project serves a dashboard, an MCP server, and an HTTP API, so that condition is met by design rather than by accident. Under the dependency policy in D15, AGPL-3.0 is refused.

`twinflow-procmine` therefore implements the directly-follows graph, the inductive miner, token-based replay, alignment-based conformance as A star search over the synchronous product net, variant analysis, rework-loop detection, and per-activity cycle-time contribution.

Doctrine ruling D-14 records why this is an upgrade rather than a substitute. The twin is the designed reference model, so conformance is measured against a known ground-truth process and the repository can report how well discovery recovers it. No external library closes that loop, because no external library owns the reference model. PM4Py stays available as a development-only validation oracle, compared against in CI without being distributed or served, which gives the conformance gates a real external reference under doctrine ruling D-11. That arrangement needs the owner's own legal read before release.

### D9 note: not LangChain, and not Pydantic AI either

Pydantic AI was chosen for two properties, and both are load-bearing. The provider abstraction lets the same agent run against a hosted frontier model or a local Ollama model by changing one string, which is what makes the no-API-key demo the same code path as the hosted demo rather than a stub. The structured-output guarantee, with validation-retry on schema failure, implements the accuracy stack layer that requires every tool call to be schema-constrained, so malformed requests are impossible by construction. LangChain would supply abstractions the project does not need, over a surface a reader cannot inspect quickly, and the stated requirement is a thin implementation that survives being read.

This repository does not use the framework, and the note says so where a reader meets the decision. Resolving `pydantic-ai` 2.27.0 puts `certifi` in the run-time tree through httpx. That distribution is MPL-2.0, which the allowlist named by D15 refuses for anything shipped at run time. So `twinflow-agent` ships the `StructuredOutputAdapter` seam itself, with a pydantic implementation carrying the validation-retry loop above and an Ollama implementation carrying D10's constrained decoding on the standard library alone. See [ADR-0002](docs/adr/0002-implement-the-agent-seam-rather-than-adopt-pydantic-ai.md), which records the resolved evidence, what is lost with the multi-provider switch, and the two changes that would reopen it. This row keeps its id and its text, per section 2 of the decision record index.

### D11 note: the arena, not the ranking

The forecasting layer does not import a winner from a benchmark paper. It runs statsforecast baselines and any challenger over the same backtest windows on this project's own series, and publishes the table. The two 2026 benchmarks quoted in D11 disagree with each other by domain and by context length, which is the argument for running the comparison locally rather than the argument for a particular model. Conformal wrapping gives calibrated intervals the inventory optimizer can consume regardless of which model wins.

### D14 note: why Apache-2.0 and not MIT

MIT and Apache-2.0 permit the same things. They differ in what a redistributor owes back. MIT asks that the copyright line travels with the code and nothing more, so a fork can rename the project, drop the author, ship, and still comply. Apache-2.0 section 4(b) makes every modified file say it was changed, and section 4(d) carries the `NOTICE` content into every redistribution. On a repository whose whole purpose is to be read and attributed, that is the difference between attribution that survives a fork and attribution that does not.

The second reason is patents. Section 3 grants "a perpetual, worldwide, non-exclusive, no-charge, royalty-free, irrevocable" patent license from every contributor to every user, and its defensive clause ends that license for anyone who sues over it. The MIT text grants no patent rights at all, which leaves an open question in front of a downstream adopter's counsel that Apache-2.0 closes. Apache-2.0 is also OSI approved, so choosing it costs nothing in adoption friction while a less common license would.

The commercial option is why `CLA.md` exists. A dual license only holds when one party can relicense the whole work. A contribution arriving under Apache-2.0 alone cannot be shipped in a commercially licensed copy, so the second option would break the first time an outside pull request merged. `CLA.md` grants the maintainer that relicensing right while leaving the contributor holding their own copyright. [LICENSING.md](LICENSING.md) states both options and what each one costs the reader.

### D16 note: not numpy's default, and why that is the point

`PCG64` is numpy's default bit generator, and it was this project's first choice for exactly that reason: it is the construction a reader of numpy code already knows. That argument lost.

The numpy reference guide page "Upgrading PCG64 with PCG64DXSM" states the weakness in its own words. Two `PCG64` streams that share their lower 58 state bits will, when interleaved, fail the PractRand battery "after drawing a few gigabytes of data", and the birthday calculation for a 58-bit collision reaches high probability at about `2^29` streams. The page also removes the mitigation a reader would reach for first: numpy seeds both the state and the increment, and the developers had believed a seeded increment would give extra protection, but "this is not true", because for any given pair of increments the colliding space of states is the same size. The page's guidance is that a few thousand parallel streams are comfortable and that millions are the point to consider `PCG64DXSM`. This project's declared stream ceiling is 750,000, which sits between those two ranges, so the choice had to be made rather than inherited.

The switch removes one thing and buys nothing else. `PCG64DXSM` replaces the XSL-RR output function with the DXSM one, which the same page describes as a "xorshift-multiply" construction with "much better avalanche properties". With that function in place, a collision needs two streams close in the 128-bit state space and the 127-bit increment space at once, which the page calls "less likely than the negligible chance of colliding in the 128-bit internal SeedSequence pool". numpy publishes no birthday number for `PCG64DXSM`, and this document does not invent one. `docs/design/variability-and-faults.md` section A.1a computes both bounds and records the missing one as an open question.

Two practical facts made the change cheap on 2026-08-09 and would have made it expensive later. numpy seeds `PCG64DXSM` through the same routine it uses for `PCG64`, so the seeded state and increment are bit-identical and only generation differs, which keeps the cross-language derivation intact. And no known-answer corpus existed yet. The first golden artifact in the repository is the RNG corpus in Phase 0a, and the Rust device agent is tested against that same file in Phase 1, so every day after the freeze adds a file to regenerate and, later, a second language to coordinate.

---

## 2. Dual-mode deterministic simulation testing

This is the defining architectural decision in the repo. One codebase runs two ways.

|                                 | Production mode                                               | Simulation mode                                               |
|---------------------------------|---------------------------------------------------------------|---------------------------------------------------------------|
| Process model                   | Roughly 25 containers across Purdue-segmented docker networks | One process                                                   |
| Scheduler                       | OS threads and event loops, real concurrency                  | Deterministic single-threaded scheduler                       |
| Clock                           | System monotonic clock, real sleeps                           | Virtual clock, time advances only when the queue does         |
| Transport                       | MQTT over TCP to EMQX, mTLS from an internal CA               | In-memory message bus                                         |
| Storage                         | Postgres plus Delta tables on disk                            | In-memory or temp-directory store with deterministic ordering |
| Failures                        | Container kills, link faults, broker restarts                 | Injected partitions, latency, reordering, duplicate delivery  |
| Telemetry                       | OpenTelemetry traces, metrics, logs                           | Same instrumentation, recorded to the run log                 |
| Packaging                       | docker compose at growth tier, Helm chart at enterprise tier  | `pytest`                                                      |
| Wall time for a simulated shift | 8 hours                                                       | Seconds                                                       |

The application code does not know which mode it is in. Every subsystem is written against four interfaces, and those four interfaces are the seam.

| Seam    | Interface surface                                       | Production implementation                        | Simulation implementation                  |
|---------|---------------------------------------------------------|--------------------------------------------------|--------------------------------------------|
| CLOCK   | `now()`, `sleep(d)`, `timer(d, cb)`, `deadline(d)`      | System monotonic clock, real sleeps, real timers | SimPy environment time and `env.timeout`   |
| RNG     | `child(name)`, distribution draws                       | Splittable generator seeded from the run seed    | Identical implementation, identical seed   |
| NETWORK | `connect()`, `publish()`, `subscribe()`, `disconnect()` | MQTT client over TCP with TLS                    | In-memory bus with a fault-injection layer |
| STORAGE | `append()`, `read()`, `checkpoint()`, `restore()`       | Postgres and Delta                               | Deterministically ordered in-memory store  |

The RNG is the one seam whose implementation does not change between modes. That is intentional. The seed, and therefore the stochastic behavior of the modeled factory, is identical in production and simulation mode. Only the clock, the network, and the storage swap.

### What determinism guarantees, and what it does not

Doctrine ruling D-05 scopes the guarantee in two tiers, and this document states both rather than the stronger one alone.

| Tier             | Guarantee                                                         | Gate                                                                                                   |
|------------------|-------------------------------------------------------------------|--------------------------------------------------------------------------------------------------------|
| Byte-identical   | Same seed, same config, same platform, same pinned dependency set | Event log hashes are equal, or the build fails                                                         |
| Value-equivalent | Same seed and config across platforms                             | Business events identical; continuous fields agree within a tolerance derived from measured divergence |

Distributions sample floats and round to ticks, and `log`, `exp`, and `erfinv` differ by a unit in the last place across platforms and SIMD dispatch. A cross-platform byte-identity claim cannot be supported, so this document does not make one. The cross-platform gate reports the observed maximum divergence instead of asserting a number chosen in advance. When the divergence exceeds the tolerance, either the tolerance was wrong or a real defect exists, and the gate names which.

### Prior art

This is deterministic simulation testing. FoundationDB documents the pattern as "a deterministic simulation of an entire FoundationDB cluster within a single-threaded process", where determinism "allows perfect repeatability of a simulated run". TigerBeetle's documentation describes its VOPR as "a simulated environment where an entire cluster, running real code, is subjected to all kinds of network, storage and process faults, at 1000x speed". WarpStream published "Deterministic Simulation Testing for Our Entire SaaS" about its own service. Resonate calls the technique "a cornerstone of our mission to build correct and reliable distributed systems". Antithesis sells it as a service.

The claim being made here is not novelty. It is that the pattern is applied correctly, and that this system is an unusually good fit for it.

### Why it is unusually cheap here

Most projects adopting deterministic simulation testing have to build the deterministic scheduler and the virtual clock first, and that is the expensive part. This project is installing a discrete-event simulation library regardless, because the twin is a discrete-event simulation. SimPy's core is already a virtual-clock event loop with a deterministic event queue. The deterministic scheduler arrives as a property of a dependency the project needs anyway.

The tagline: the twin simulates the factory, and the same kernel simulates the software running it.

### What this buys

| Capability                    | Consequence                                                                                                                                                                                           |
|-------------------------------|-------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| A failing test is a seed      | A bug report is a seed plus a config. On the same platform and pinned dependency set it reproduces byte-identically, and elsewhere it reproduces the same business events within the stated tolerance |
| Faults are first-class inputs | Network partitions, message reordering, and duplicate delivery are test parameters, not rare production accidents                                                                                     |
| Time is free                  | A week of simulated operation runs in seconds, so rare interleavings are reachable                                                                                                                    |
| One fault catalog             | The same catalog drives the in-memory transport in simulation mode and the container-level chaos runner in production mode                                                                            |
| CI can assert determinism     | Repeated runs of the same seed on one platform hash to the same event log, or the build fails                                                                                                         |

### The risk, stated honestly

Determinism is a property of the whole process, and one violation destroys it silently. A stray `time.time()` call, an unseeded `random` draw, an iteration over a set, a raw socket opened outside the kernel package, or a `uuid4()` in an event ID all produce a system that looks correct and quietly stops being reproducible. The failure mode is not a crash. It is a hash mismatch weeks later, in a test that used to pass.

Mitigation is three-layered.

| Layer        | Mechanism                                                                                                                                                                                                                                                                                                               |
|--------------|-------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| Prevention   | A CI lint that bans a symbol list outside the kernel package: `time.time`, `time.monotonic`, `datetime.now`, `datetime.utcnow`, `random.*`, module-level `numpy.random` functions, `uuid.uuid4`, `os.urandom`, `socket`, `threading`, `asyncio.sleep`, and unordered iteration over sets in code paths that emit events |
| Escape hatch | An explicit annotation comment carrying a reason, which the lint accepts and which shows up in a report, so the exceptions stay countable                                                                                                                                                                               |
| Backstop     | A repeated-run hash check in CI: the same seed and config run twice on one platform, event logs hashed, mismatch fails the build                                                                                                                                                                                        |

The lint prevents the common cases. The hash check catches everything the lint does not know about, including nondeterminism arriving through a dependency upgrade.

### Critical clarification

Readers misread this section, so it is stated directly.

**Deterministic means the same seed reproduces the same run. It does not mean the modeled factory is predictable.**

The factory carries heavy, realistic variability. Trucks arrive late, motors drift, reads fail, operators tire, and suppliers ship short. Tails are not clipped. A given seed reproduces a given sequence of surprises exactly. It does not remove the surprises. Determinism is a property of the software under test, not of the process being modeled. The two are independent, and confusing them is the most common misreading of this design.

### Production mode topology, indicative

| Segment | Containers | Contents                                                                                                                                                                  |
|---------|------------|---------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| OT      | ~12        | Simulated device groups, one Rust device agent, two NanoMQ edge gateways, the OT broker                                                                                   |
| DMZ     | ~4         | Historian, twin sync connector, schema registry, internal certificate authority                                                                                           |
| IT      | ~10        | LSS engine, process mining worker, forecasting and optimization worker, agent service, MCP server, REST API, dashboard, Postgres, OpenTelemetry collector, metrics viewer |

---

## 3. Stochastic model

Distributions are chosen so that their support is already the correct support for the quantity being modeled. The system never samples a distribution whose support is wrong and then clamps the result back into range. Clamping is a symptom that the wrong distribution was chosen.

| Quantity class       | Examples                                                                                               | Distribution family                                           | Why the support is right                                                                                                                                                                                                                                 |
|----------------------|--------------------------------------------------------------------------------------------------------|---------------------------------------------------------------|----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| Durations            | Unload time, station cycle time, changeover, transit time, time to repair, triage and disposition time | Lognormal, gamma, or Weibull                                  | Strictly positive, right-skewed, genuinely heavy-tailed. Duration data in industrial processes does not sit symmetrically around a mean, and the long right tail is where the disruptive events live. Weibull where a hazard-rate interpretation applies |
| Bounded ratios       | Battery state of charge, RFID read rate, fill rate, first-pass yield, on-time-in-full rate             | Beta, scaled to the quantity's range                          | Support is exactly `[0, 1]` before scaling, so a rate can approach its bound without ever crossing it and without a clamp                                                                                                                                |
| Counts               | Truck arrivals per hour, defects per lot, near-misses per shift, contacts per service failure          | Poisson, or negative binomial where the data is overdispersed | Non-negative integers by construction. Negative binomial where variance exceeds the mean, which is the usual case for defect and incident counts                                                                                                         |
| Categorical outcomes | Return reason code, disposition grade, fault mode selection                                            | Categorical, weights from config                              | Enumerated support taken directly from the catalog                                                                                                                                                                                                       |

Three rules follow.

1. **No sigma cap.** There is no truncation at plus or minus any number of standard deviations, anywhere in the codebase.
2. **No tail clipping.** Rare extreme values are generated and retained. A four-hour unload is a real event in a real building, and the system produces it at its real rate.
3. **Every distribution is named in config with its parameters.** `facility.yaml` and the sensor catalog carry the family and parameters for each stochastic quantity, so the model is inspectable without reading code.

### Invariants are assertions, not clamps

Physical impossibilities are enforced as property-based test assertions, never as runtime clamps.

| Invariant                                              | Enforced as                                       |
|--------------------------------------------------------|---------------------------------------------------|
| Battery state of charge stays within `[0, 1]`          | Property test over the charge and discharge model |
| Mass is conserved across every station and flow        | Property test over the material ledger            |
| The event clock is monotone                            | Property test over the emitted event log          |
| Genealogy closes: every unit traces to an origin lot   | Property test over the genealogy graph            |
| Queue lengths and inventory positions are non-negative | Property test over subsystem state                |
| Financial ledger balances                              | Property test over GL postings                    |

A runtime clamp would hide a modeling error by producing plausible output from a wrong distribution. An assertion surfaces it. If a battery model can generate a state of charge above 1, the correct fix is the distribution or the charge dynamics, not a `min(1.0, x)` on the way out. CI fails loudly and the failure names the subsystem.

### Why this matters for the statistical engine

The Lean Six Sigma engine judges this data with control charts. Its hard problem is distinguishing a rare common-cause tail event from a genuine special cause. That is the actual difficult problem in statistical process control, and it is the reason experienced practitioners argue about out-of-control rules.

Clipping the tails would make that problem artificially easy. A process with no tail beyond three sigma produces almost no false alarms. Any rule then looks good, and the engine's reported performance would measure the simplifying assumption rather than the engine.

Special causes are therefore injected separately, from a labeled fault catalog, and are not part of the common-cause distributions. The catalog records what was injected, when, into which subsystem, and with what magnitude. That gives ground truth for scoring detectors.

| Score             | Definition against the catalog                                                                                |
|-------------------|---------------------------------------------------------------------------------------------------------------|
| True positive     | A finding raised inside the injected event's window, attributed to the right subsystem                        |
| False positive    | A finding raised with no injected event in scope, which is the rare common-cause tail read as a special cause |
| False negative    | An injected event with no corresponding finding                                                               |
| Detection latency | Time from injection to finding, in sim-time                                                                   |

This is the reason the tails stay. Without them, the false positive rate is not a real measurement.

---

## 4. ISA-95 and Purdue layer map

ANSI/ISA-95 is a paid standard and its text is not reproduced here. The table below states the level meanings this repository uses, so the component map reads without a reference open. The mapping is a design decision, not a quotation.

| Level | ISA-95                                                         | Purdue                                         |
|-------|----------------------------------------------------------------|------------------------------------------------|
| 0     | The physical process                                           | The physical process                           |
| 1     | Sensing and actuation, PLC analog                              | Basic control: sensors, actuators, controllers |
| 2     | Monitoring and supervisory control, SCADA and historian analog | Area supervisory control: HMI, SCADA           |
| 3     | Manufacturing operations management, MES and analytics analog  | Site operations: MES, historian, scheduling    |
| 3.5   | Not an ISA-95 level                                            | Industrial DMZ: the mediated boundary          |
| 4     | Business planning and logistics, business and agent layer      | Business logistics: ERP, planning              |

Every component, its levels, and the class of production system it stands in for.

| Component                                                                                | ISA-95                                           | Purdue                  | Real-world counterpart                                                                |
|------------------------------------------------------------------------------------------|--------------------------------------------------|-------------------------|---------------------------------------------------------------------------------------|
| Twin process model: docks, stations, conveyors, ASRS, AMR fleet, factory lines           | L0                                               | L0                      | The physical process itself. As software, an AnyLogic-class discrete-event simulation |
| Simulated sensor devices, Python                                                         | L1                                               | L1                      | Field instrumentation and transmitters                                                |
| Rust device agent                                                                        | L1                                               | L1                      | Embedded firmware on a microcontroller-class device                                   |
| Actuator and interlock logic                                                             | L1                                               | L1                      | PLC and safety relay logic                                                            |
| Edge gateway, NanoMQ plus local inference                                                | L2                                               | L2                      | Industrial edge gateway and protocol converter                                        |
| OPC UA to MQTT bridge                                                                    | L2                                               | L2                      | Protocol gateway in front of legacy control equipment                                 |
| UNS broker, Mosquitto or EMQX                                                            | L2                                               | L2 and L3.5             | EMQX or HiveMQ-class UNS broker                                                       |
| Historian                                                                                | L2                                               | L3, published into L3.5 | Plant historian, the L2 system of record for time-series                              |
| Supervisory view and alarm management: prioritization, rationalization, dedupe, shelving | L2                                               | L2                      | Ignition-class SCADA and its alarm subsystem                                          |
| Device registry and fleet health scoring                                                 | L2 to L3                                         | L3                      | IoT device management platform                                                        |
| OTA campaign and provisioning service                                                    | L3                                               | L3                      | Device lifecycle management platform                                                  |
| Twin sync connector, bi-directional                                                      | L3                                               | L3.5                    | Digital twin synchronization layer                                                    |
| Lean Six Sigma engine: SPC, capability, MSA, hypothesis testing                          | L3                                               | L3                      | Statistical quality software, plus the quality module of an MES                       |
| Process mining kit                                                                       | L3                                               | L3 to L4                | Process mining platform                                                               |
| Production scheduling and dispatch                                                       | L3                                               | L3                      | MES and finite-capacity scheduler                                                     |
| Maintenance work order queue                                                             | L3                                               | L3                      | APM and CMMS platform                                                                 |
| Quality management: NCR, CAPA, acceptance sampling, CoA                                  | L3                                               | L3 to L4                | eQMS platform                                                                         |
| Lot genealogy and traceability ledger                                                    | L3                                               | L3                      | Track-and-trace and LIMS genealogy                                                    |
| Computer vision auditor                                                                  | L2 to L3                                         | L2                      | Machine vision inspection system                                                      |
| Warehouse execution: pick, pack, ship, returns                                           | L3                                               | L3                      | WMS and WES                                                                           |
| Planning layer: forecasting, inventory optimization, MEIO                                | L4                                               | L4                      | Advanced planning system                                                              |
| ERP stub: ASN, expected receipts, orders                                                 | L4                                               | L4                      | D365-class ERP                                                                        |
| Financial twin and general ledger                                                        | L4                                               | L4                      | ERP finance module                                                                    |
| Procurement and sourcing                                                                 | L4                                               | L4                      | Source-to-pay suite                                                                   |
| Transportation network and freight analytics                                             | L4                                               | L4                      | TMS                                                                                   |
| AI agent and MCP server                                                                  | L4                                               | L4                      | Control tower and operations copilot                                                  |
| Dashboard                                                                                | L2 for live line state, L4 for findings and KPIs | L2 and L4               | HMI for the line view, BI for the analytics view                                      |
| Schema registry                                                                          | Cross-cutting                                    | Cross-cutting           | UDT and namespace model in a UNS platform                                             |
| OpenTelemetry stack                                                                      | Cross-cutting, L3                                | L3                      | APM and infrastructure monitoring                                                     |
| Internal certificate authority                                                           | Cross-cutting                                    | L3.5                    | PKI for device identity                                                               |

Two entries are deliberately split across levels. The dashboard is two products in one page: an L2 supervisory view of the running line, and an L4 analytics view of findings and KPIs. The broker appears at L2 and L3.5 because it is both the area-level message bus and the mediated crossing point, which is how a real UNS broker is deployed.

---

## 5. Unified namespace

Every telemetry topic follows an ISA-95 hierarchy. Level names are generated from `facility.yaml`, never typed by hand, so the namespace and the modeled facility cannot drift apart.

```
{enterprise}/{site}/{area}/{line}/{equipment}/{parameter}
```

| Level      | Meaning                           | Example values                                                      |
|------------|-----------------------------------|---------------------------------------------------------------------|
| enterprise | The organization                  | `twinflow`                                                          |
| site       | Physical facility                 | `dc-01`, `plant-01`                                                 |
| area       | Functional zone within the site   | `receiving`, `storage`, `outbound`, `returns`, `mixing`             |
| line       | Work cell or flow within the area | `inbound-line-01`, `asrs-aisle-04`, `pack-line-02`, `batch-line-01` |
| equipment  | The addressable asset             | `portal-03`, `conveyor-02`, `crane-01`, `amr-014`, `mixer-02`       |
| parameter  | The measured or derived quantity  | `read_rate`, `motor_temp_c`, `vibration_rms`, `soc`, `viscosity_cp` |

Concrete topics:

```
twinflow/dc-01/receiving/inbound-line-01/portal-03/read_rate
twinflow/dc-01/receiving/inbound-line-01/conveyor-02/motor_temp_c
twinflow/dc-01/receiving/dock-doors/door-07/state
twinflow/dc-01/storage/asrs-aisle-04/crane-01/cycle_time_s
twinflow/dc-01/storage/amr-fleet/amr-014/battery_soc
twinflow/dc-01/outbound/pack-line-02/scale-07/weight_kg
twinflow/plant-01/mixing/batch-line-01/mixer-02/viscosity_cp
```

Naming rules, enforced by the schema registry at publish time:

| Rule                                                             | Reason                                                                                                         |
|------------------------------------------------------------------|----------------------------------------------------------------------------------------------------------------|
| Lowercase, kebab-case for identifiers, snake_case for parameters | One convention, so subscriptions are writable from memory                                                      |
| No spaces, no wildcards, no empty levels in published topics     | Wildcards belong in subscriptions only                                                                         |
| Exactly six levels for device telemetry                          | A fixed depth means an area-level subscription is `twinflow/dc-01/receiving/#` and always means the same thing |
| Units carried in the parameter name where ambiguity is possible  | `motor_temp_c` cannot be misread as Fahrenheit                                                                 |
| Topic strings generated from config                              | The namespace is a projection of the facility model, not a parallel truth                                      |

### How Sparkplug B maps onto it

Sparkplug B defines its own topic namespace and the device payloads use it. The ISA-95 hierarchy above is preserved inside that namespace rather than being replaced by it.

The specification fixes the topic form. It reads: "All MQTT clients using the Sparkplug specification MUST use the following topic namespace structure: `namespace/group_id/message_type/edge_node_id/[device_id]`", with the namespace element for Sparkplug B set to the constant `spBv1.0`.

```
spBv1.0/{group_id}/{message_type}/{edge_node_id}/{device_id}
```

| UNS level              | Sparkplug placement                                                                                       | Example                    |
|------------------------|-----------------------------------------------------------------------------------------------------------|----------------------------|
| enterprise, site, area | Encoded in `group_id`, joined with `:` because the specification reserves `+`, `/`, and `#` in a Group ID | `twinflow:dc-01:receiving` |
| line                   | The edge node serving that line, so `edge_node_id`                                                        | `inbound-line-01`          |
| equipment              | `device_id`                                                                                               | `portal-03`                |
| parameter              | The Sparkplug metric name inside the payload, which may itself carry `/` for folder structure             | `read_rate`                |

Resulting topics for one portal:

```
spBv1.0/twinflow:dc-01:receiving/DBIRTH/inbound-line-01/portal-03
spBv1.0/twinflow:dc-01:receiving/DDATA/inbound-line-01/portal-03
spBv1.0/twinflow:dc-01:receiving/DDEATH/inbound-line-01/portal-03
spBv1.0/twinflow:dc-01:receiving/NBIRTH/inbound-line-01
spBv1.0/twinflow:dc-01:receiving/NDEATH/inbound-line-01
```

Lifecycle and payload behavior, as the v3.0.0 specification defines it:

| Message         | When                                             | Contents                                                    | Notes                                                                                                                                   |
|-----------------|--------------------------------------------------|-------------------------------------------------------------|-----------------------------------------------------------------------------------------------------------------------------------------|
| NBIRTH          | Edge node connects                               | Full metric list for the node, `bdSeq`, node metrics        | Published with retain false. The birth certificate is the model, so a subscriber does not need retained data to learn the namespace     |
| DBIRTH          | Each device announces                            | Full metric list with names, datatypes, and integer aliases | Establishes the alias table used by every subsequent DDATA                                                                              |
| NDATA and DDATA | Report by exception                              | Changed metrics only, referenced by alias                   | Aliases are optional in the specification. This fleet uses them, and where they are used the metric name is excluded from data messages |
| NDEATH          | Registered as the MQTT Last Will at connect time | `bdSeq` matching the NBIRTH                                 | The broker publishes it if the node drops, so a stale node is marked dead rather than appearing frozen                                  |
| DDEATH          | Device goes offline while the node stays up      | Device identity                                             | Distinguishes a dead sensor from a dead gateway                                                                                         |
| STATE           | Primary host application                         | Online or offline                                           | Published with the retain flag set to true, per the v3.0.0 specification                                                                |
| NCMD and DCMD   | Commands to node or device                       | Writable metrics                                            | The path an accepted what-if takes when it flows back to the fleet                                                                      |

`bdSeq` correlates an NBIRTH with its NDEATH. A separate sequence number rides on every NBIRTH, DBIRTH, NDATA, and DDATA, starts at 0 on NBIRTH, and wraps back to zero after 255. Together they make gap detection possible: a subscriber that sees a sequence discontinuity knows it missed messages and can request a rebirth with a `Node Control/Rebirth` command. This is the mechanism the store-and-forward resilience test exercises when the broker is killed mid-demo.

### Why both namespaces exist

Sparkplug is the canonical device payload format. A bridge also republishes a flattened JSON view on the plain ISA-95 topic path for consumers that do not speak Sparkplug: the dashboard, generic MQTT clients, and anyone exploring the namespace with a command-line subscriber. The Sparkplug side is authoritative, the JSON mirror is derived, and the mirror is generated from the same metric model so the two cannot disagree. This mirrors the common plant deployment where a Sparkplug-native fleet coexists with tooling that expects readable topics.

---

## 6. Compute placement

Compute placement is an explicit architectural decision, not a consequence of where code happened to be easy to run. Four tiers, each with a stated latency budget.

| Tier | Location               | Physical analog                     | Latency budget                                         | Runs                                                                                                                                                                                                       |
|------|------------------------|-------------------------------------|--------------------------------------------------------|------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| 0    | On-device              | Sensor or embedded controller       | Microseconds to a few milliseconds                     | Sampling, unit conversion, deadband and threshold filtering, debounce, stuck-at self-check, single-signal interlock trip                                                                                   |
| 1    | Edge gateway, per area | Gateway appliance on the OT segment | Safety checks under 100 ms, anomaly flagging under 1 s | Protocol translation, Sparkplug encoding, store-and-forward buffering, area aggregation, local anomaly inference, multi-signal safety checks, CV frame inference, the plant-distilled small language model |
| 2    | Site                   | Server room, DMZ and site network   | Seconds to minutes                                     | Historian, twin sync, LSS engine, alarm rationalization, process mining, work order generation, dashboard, site what-ifs                                                                                   |
| 3    | Network                | Central or hosted                   | Minutes to hours, no interactive budget                | Demand forecasting, multi-echelon inventory optimization, network design, Optuna studies, surrogate model training, hosted LLM agent                                                                       |

### Latency budgets

| Decision class            | Budget             | Enforced at | Consequence of missing it                                             |
|---------------------------|--------------------|-------------|-----------------------------------------------------------------------|
| Safety interlock          | Under 100 ms       | Tier 0 or 1 | Someone gets hurt. This decision may never depend on a link to tier 2 |
| Machine protection trip   | Under 100 ms       | Tier 0 or 1 | Equipment damage                                                      |
| Anomaly flag              | Under 1 s          | Tier 1      | Detection latency shows up in the mean-time-to-detect metric          |
| Operator dashboard update | Under 2 s          | Tier 2      | Operator loses trust in the display                                   |
| Finding to work order     | Seconds to minutes | Tier 2      | Acceptable; the work order is queued, not actioned instantly          |
| What-if experiment        | Minutes            | Tier 2 or 3 | Acceptable; the user is asking a planning question                    |
| Planning and optimization | Hours              | Tier 3      | Acceptable; the cycle is weekly or monthly                            |

The placement rule follows from the budgets: a function may run at a lower tier than its budget requires, never at a higher one. A safety check may be pushed down to tier 0 when the signal is available there. It may never be pulled up to tier 2. A tier-2 placement makes the decision depend on a network link, and a link that is up 99.9% of the time is not an acceptable dependency for a 100 ms safety decision.

### Function placement, annotated

| Function                                                    | Tier | Why that tier                                                                                                                |
|-------------------------------------------------------------|------|------------------------------------------------------------------------------------------------------------------------------|
| Deadband and threshold filter                               | 0    | Cuts message volume at the source. Nothing upstream needs the suppressed samples                                             |
| Debounce on dock door and e-stop signals                    | 0    | The bounce is a device-level artifact and should not reach the namespace                                                     |
| Sensor stuck-at self-check                                  | 0    | The device is the only place that knows its own raw reading before filtering                                                 |
| Single-signal interlock                                     | 0    | Under 100 ms with no network involved at all                                                                                 |
| Multi-signal safety check, such as AMR-worker proximity     | 1    | Needs signals from more than one device, so it belongs at the first point where those signals meet, and still clears 100 ms  |
| Protocol translation, OPC UA to MQTT and Sparkplug encoding | 1    | The gateway is the boundary between fieldbus protocols and the namespace                                                     |
| Store-and-forward buffer                                    | 1    | The buffer has to survive the failure it exists for, which is the site link                                                  |
| Area-level aggregation                                      | 1    | Bandwidth saved is measured here: events per second in versus out, bytes per insight                                         |
| EWMA and control-chart anomaly scoring on device streams    | 1    | Under 1 s, and it must keep working when the line is disconnected from site                                                  |
| Isolation Forest scoring                                    | 1    | Same budget, same disconnection requirement. Training happens at tier 3, scoring runs at tier 1                              |
| CV frame inference                                          | 1    | Frames are large. Inferring at the edge sends findings north instead of video                                                |
| Plant-distilled small language model                        | 1    | Air-gapped operator questions answered without leaving the OT segment                                                        |
| Historian writes and queries                                | 2    | The L2 system of record for time-series, sized for the site                                                                  |
| Twin sync and recalibration                                 | 2    | Needs the full site state, tolerates seconds of latency                                                                      |
| SPC charts, capability studies, MSA                         | 2    | Operates on windows of historian data, not on individual samples                                                             |
| Alarm rationalization, dedupe, shelving                     | 2    | Needs the whole findings stream to decide what is redundant                                                                  |
| Process mining and VSM generation                           | 2    | Runs over the completed event log for a period                                                                               |
| Model training for PdM and anomaly detectors                | 3    | Compute-heavy, offline, no latency requirement. Models are pushed down to tier 1 for scoring                                 |
| Forecasting and backtests                                   | 3    | Planning horizon is days to months                                                                                           |
| Multi-echelon inventory optimization                        | 3    | Needs the whole network, not one site                                                                                        |
| Optuna what-if search                                       | 3    | Thousands of simulation runs                                                                                                 |
| Hosted LLM agent                                            | 3    | Latency measured in seconds is acceptable for a planning question, and the hosted model is outside the OT boundary by design |

### Degradation

The tier structure is testable, and the test is the point. When the site link drops, tier 1 keeps its area running: local anomaly models keep scoring, safety checks keep firing, and the store-and-forward buffer accumulates. When the link returns, buffered data replays into the historian with its original sim-time timestamps. Nothing is lost, and the only capability unavailable during the outage is the tier-3 planning layer, which had no latency budget in the first place.

---

## 7. Purdue network segmentation in docker compose

The compose topology implements the Purdue Model rather than describing it. Three docker networks.

| Network | Docker configuration | Members                                                                                                                                                   | Reachability                                                                                               |
|---------|----------------------|-----------------------------------------------------------------------------------------------------------------------------------------------------------|------------------------------------------------------------------------------------------------------------|
| `ot`    | `internal: true`     | Simulated device containers, the Rust device agent, NanoMQ edge gateways, the OT broker                                                                   | No gateway to the host or to the internet. Devices cannot initiate outbound connections beyond the segment |
| `dmz`   | Standard bridge      | The OT broker's north interface, historian, twin sync connector, schema registry, internal CA                                                             | The mediated zone. The only place where OT-originated data becomes available to IT                         |
| `it`    | Standard bridge      | LSS engine, process mining worker, forecasting and optimization worker, agent service, MCP server, REST API, dashboard, Postgres, OpenTelemetry collector | No route to `ot`                                                                                           |

Compose documents the `internal` attribute this way: "By default, Compose provides external connectivity to networks. `internal`, when set to `true`, lets you create an externally isolated network." That one line is what the OT segment rests on.

```yaml
networks:
  ot:
    internal: true
  dmz:
  it:

services:
  device-portal-03:
    networks: [ot]
  edge-gateway-receiving:
    networks: [ot]
  broker:
    networks: [ot, dmz] # the only container attached to ot plus anything else
  historian:
    networks: [dmz, it]
  twin-sync:
    networks: [dmz, it]
  agent:
    networks: [it]
  dashboard:
    networks: [it]
```

The rules, stated precisely so they can be tested:

| Rule                   | Statement                                                                                                                                                                                                                                            |
|------------------------|------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| Single crossing point  | The broker is the only container attached to `ot` and any other network. Every byte leaving OT leaves through it                                                                                                                                     |
| No IT to device path   | No device container is attached to `it`, and no container on `it` can resolve or reach a device container. There is no route                                                                                                                         |
| DMZ mediates           | Containers on `dmz` are attached to `dmz` and `it`, never to `ot`. IT systems talk to the DMZ, and the DMZ talks to the broker                                                                                                                       |
| OT does not reach out  | `ot` is declared `internal: true`, so devices have no default gateway. Nothing on the OT segment initiates a connection to the internet, which is the same constraint that makes the air-gapped edge language model necessary rather than decorative |
| Identity, not location | Devices authenticate to the broker with mTLS client certificates from the internal CA. Broker ACLs restrict each device to publishing only under its own UNS prefix, so a compromised device cannot impersonate another area                         |

These are asserted in CI, not just documented:

| Assertion                                                              | Method                                 |
|------------------------------------------------------------------------|----------------------------------------|
| No service lists both `ot` and `it`                                    | Static check on the compose file       |
| Only the broker lists `ot` plus another network                        | Static check on the compose file       |
| A container on `it` cannot open a TCP connection to a device container | Runtime check in the integration suite |
| Every device publish is rejected outside its own topic prefix          | Runtime check against the broker ACL   |

Traffic crossing the boundary is logged and baselined, so an anomalous cross-zone flow becomes a finding in the same stream as a bearing trend or an SPC violation. That is what makes the OT security drills exercisable rather than hypothetical.

### Tier variations

| Deployment tier | Segmentation                                                                                                                                                                    |
|-----------------|---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| Garage          | `dmz` collapses into `it`. The `ot` and `it` split is retained, because the boundary is the architectural claim and dropping it would make the smallest tier a different system |
| Growth          | All three networks as shown, EMQX at the broker, Postgres on `it`                                                                                                               |
| Enterprise      | Helm chart with NetworkPolicy objects expressing the same three zones, and namespace separation per zone. The same rules, expressed in Kubernetes primitives                    |

The compose topology is the reference. Every other tier is that topology expressed in a different substrate, which is the same claim the dual-mode design makes about the application code.
