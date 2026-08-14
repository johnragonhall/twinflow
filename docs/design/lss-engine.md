---
title: LSS engine
description: SPC, capability, MSA, hypothesis testing, findings, alarms, process mining, value stream maps, SIPOC and swimlane views, what-if ranking, and the validation registry.
topic_type: reference
audience: contributors
---

# LSS engine

Status: design spec section, implementation contract. Written for TDD. Every capability named
here has a named test or a named gate. Every statistic named here has a registry record that
states its reference class, its tolerance, and the result that would falsify it.

---

## 1. Scope

### 1.1 Requirements covered in full

Component 5. The source describes it as "a standalone, separately importable package inside the
repo, pitched as 'the Lean Six Sigma toolkit as code'. It runs continuously against both the real
telemetry stream and the twin's predictions." Both halves of that last sentence are covered. The
observed stream and the predicted stream are separate, first-class chart streams, and the
difference between them is a third stream with its own charts and its own findings.

| Source text                                                                                                                                                                                                                                                                                                              | Covered in    |
|--------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|---------------|
| "It runs continuously against both the real telemetry stream and the twin's predictions"                                                                                                                                                                                                                                 | 3.2, 5.2, 5.8 |
| "SPC control charts as code: I-MR, X-bar/R, p-chart selection by data type, with Western Electric and Nelson rule evaluation producing typed violations (rule number, severity, evidence window)"                                                                                                                        | 5.1, 5.3, 5.4 |
| "Process capability: Cp, Cpk, Pp, Ppk against spec limits defined in config, with sigma level and DPMO"                                                                                                                                                                                                                  | 5.5           |
| "Measurement system analysis: a Gage R and R study runnable against the simulated sensors (the sim can generate repeated measures with known operator/part variance, so the engine's answer has a ground truth to be tested against)"                                                                                    | 5.6           |
| "Hypothesis testing for improvement validation ... t-test, Mann-Whitney, ANOVA, with an assumption checker choosing between them ... reports effect size and confidence"                                                                                                                                                 | 5.7           |
| "Rule findings feed one stream: SPC violations, capability shortfalls, MSA failures, SOP violations from CV, fleet health alerts, and twin-divergence all become uniform 'findings' with severity, evidence, and a suggested next tool (the way a Black Belt would chain tools)"                                         | 4.2, 5.9      |
| "Validation requirement, non-negotiable: verify the engine's outputs against published reference examples ... and say in the README that every statistic is validated against published references"<!-- docs-lint-ok STE-TERM-WORD verbatim quotation of the source requirement text -->                                 | 7.5, 7.6      |
| "Process mining, Celonis-style, on the system's own event log ... discovery, conformance checking, variant analysis, rework-loop detection, and cycle-time contribution per activity ... conformance is checked against a KNOWN ground-truth process, so the repo can measure how well mining recovers the real process" | 5.11          |
| "Auto-generated value stream map: a current-state VSM ... and a future-state VSM generated from any accepted what-if"                                                                                                                                                                                                    | 5.12          |
| "Auto-generated 'capability report': one command produces a Minitab-style HTML report for any time window"                                                                                                                                                                                                               | 5.13          |

Reference-architecture fidelity paragraph, clause (d). "Include alarm management the way SCADA
vendors mean it: alarm prioritization and rationalization so the findings stream cannot flood
(dedupe, severity ranking, shelving), since alarm floods are a known real-world failure and
handling them shows operator empathy." Covered in 5.10.

Engineering craft items this section owns or co-owns:

| Item | What this section owes it                                                                                                                                                       | Where     |
|------|---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|-----------|
| C1   | Every statistic, finding id, chart render, and report byte is a deterministic function of (run seed, config, input window)                                                      | 5.14, 7.4 |
| C3   | Authors the finding, finding state change, alarm, alarm metrics, test result, contribution table, process model, divergence spec, value stream map, and validation gate schemas | 4         |
| C4   | Unit, property, seeded end-to-end, and gate tiers, with golden-file comparison of the report and the value stream map                                                           | 7         |
| C5   | Line-numbered, suggestion-bearing config errors and a `validate-config` command for every file this section reads                                                               | 6.7       |
| C12  | Severity carries a shape token and a text label in the schema, and every consumer that renders severity has a contract test                                                     | 4.2, 7.1  |
| A1   | Five independently installable bricks, each with its own README, tests, and distribution path                                                                                   | 2         |

### 1.2 Doctrine rulings applied here

`docs/design/DOCTRINE.md` binds. Where this section once disagreed with a ruling, the ruling won
and the text below is the changed text.

| Ruling | Applied where                   | Effect                                                                                                                      |
|--------|---------------------------------|-----------------------------------------------------------------------------------------------------------------------------|
| D-01   | 4.2, 5.9.2, 5.14                | `run_id` is a content address over the manifest hashed core. No wall-clock value reaches a finding, a hash, or a sort key   |
| D-02   | 5.14                            | These packages read no wall clock at all. The four legal readers are all outside them                                       |
| D-03   | 5.14, 7.2                       | No `set` iteration reaches an output, a hash, or a control decision. Alignment frontier order is total and stated           |
| D-04   | 5.11.3, 5.14                    | The A star alignment search is bounded by a deterministic node budget, never by wall time                                   |
| D-05   | 5.14, 7.4, VG-DET-01, VG-DET-02 | Two determinism tiers. Byte-identical on a pinned platform. Value-equivalent across platforms with a measured tolerance     |
| D-07   | 4.1, 4.8                        | Every event this section publishes carries `producer_id`, and the canonical total order is `(sim_ts, producer_id, seq)`     |
| D-09   | 2.6                             | One owning package per public symbol. The import graph is acyclic and CI walks it                                           |
| D-10   | 2.1, 2.3, 5.13                  | The report's charts render from a dependency-free emitter, so the headline artifact needs no heavy extra                    |
| D-11   | 7.5                             | Every gate names a reference class, a tolerance no tighter than its source, a noise floor where stochastic, and a falsifier |
| D-12   | 7.5.2, VG-ALM-02, VG-DET-02     | Every gate states the observation that fails it. A gate that no state of the world can fail is deleted and replaced         |
| D-13   | 7.7                             | Every tier's budget is derived from recorded per-gate cost, and a budget test asserts the arithmetic                        |
| D-14   | 2.4, 5.11, 7.5.9, OQ-1          | twinflow implements its own process mining under Apache-2.0. PM4Py is a development-only oracle, never a runtime dependency |

### 1.3 Requirements this section supplies the machinery for

The workflow is owned elsewhere. This section defines the API and the gate; the named section
consumes it.

| Requirement                                                                 | What it consumes                                                                        |
|-----------------------------------------------------------------------------|-----------------------------------------------------------------------------------------|
| 1, twin OEE, takt, cycle time, bottleneck                                   | `twinflow_lss.spc`, cross-checked against the mined waiting-time contribution of 5.11.5 |
| 3, PdM trend detection and time-to-threshold                                | `twinflow_lss.trend`, gated by VG-TRD-01, VG-TRD-02, VG-TRD-03                          |
| 4, CV SOP violations and RFID-versus-CV disagreement                        | The finding constructor of 5.9, and attribute agreement analysis, 5.6.6                 |
| 6, twin divergence                                                          | The `DivergenceSpec` contract of 4.6 and the residual charts of 5.2                     |
| 6a, forecast bias on a control chart                                        | `twinflow_lss.spc` on forecast error                                                    |
| 6a2, supplier scorecards on control charts                                  | `twinflow_lss.spc`                                                                      |
| 6a4, return reason-code Pareto                                              | `twinflow_lss.charts.pareto`, gated by VG-CHT-01                                        |
| 6a9, in-line SPC per production stage and golden-batch scoring              | `twinflow_lss.spc` and `twinflow_lss.batch`, gated by VG-BAT-01                         |
| 6a11, CAPA statistical effectiveness and Z1.4-class acceptance sampling     | `twinflow_lss.hypothesis` and `twinflow_lss.sampling`, gated by VG-SAM-01 and VG-SAM-02 |
| 6a13, price variance common cause against special cause                     | `twinflow_lss.spc`                                                                      |
| 6a14, workforce leading indicators on control charts                        | `twinflow_lss.spc`                                                                      |
| 6a15, MTTD, MTTR, and DORA metrics on control charts                        | `twinflow_lss.spc`                                                                      |
| 6a16, forecast value-added                                                  | `twinflow_lss.hypothesis`                                                               |
| 6a17, variance common cause against special cause before anyone explains it | `twinflow_lss.spc`                                                                      |
| 7, agent tools                                                              | The tool surface of 2.7                                                                 |
| 9, README headline claim                                                    | The generated claim block of 7.6                                                        |
| E5, autonomy tiers                                                          | Shelve, acknowledge, and re-baseline are audited decisions, 5.10.5                      |
| E7, idle-energy waste as an eighth-waste finding                            | The waste taxonomy of 5.12.2                                                            |
| E8, SOP clause citation                                                     | `Finding.sop_refs`                                                                      |
| E24, generative SOPs from alarm rationalization                             | The rationalization records of 5.10.2                                                   |
| E26(b), governed semantic metric layer                                      | Every chart's `metric` resolves in the metric registry, 6.6                             |
| E26(f), grounding checker                                                   | Every finding's evidence carries a `query_result_id`, 4.2                               |
| E27, E30, E31, E43, E45                                                     | The hypothesis layer and the chart layer, unchanged                                     |
| E1, hosted replay demo                                                      | The static on-disk formats of 4.8                                                       |

### 1.4 Explicitly out of scope for this section

Producers of findings that are not statistical (CV inference, fleet health scoring, twin sync)
live in their own sections and depend only on `twinflow-contracts` and `twinflow-findings`. The
QMS workflow (NCR and CAPA lifecycle) is 6a11. OEE computation is component 1. The parameter
values that decide when a twin divergence matters belong to component 6; the contract those
values fill in is authored here, in 4.6. This section owns the mathematics, the finding contract,
the alarm layer, and the validation registry.

### 1.5 Additions beyond the source

Two capabilities are additions dated 2026-08-13, and are not source
requirements: the SIPOC and swimlane views of 5.15, and the what-if ranking of 5.16. The
register of CON-6 is unchanged, because that file holds source atoms only. The additions close
the two automatable gaps left on the Ahire and Jensen project map once component 5 is built.
Each one reuses machinery this section already specifies, renders through `twinflow-artifact`,
and carries its own gates in 7.5.9. Nothing in 1.1 changes: source coverage is stated against
the source, and an addition neither widens it nor dilutes it.

---

## 2. Packages

Five bricks. Package names, distribution names, and import names are given because A1 requires a
reader to install one alone. A CI job installs each brick by itself into a clean environment and
imports it, so the take-one-brick claim is tested rather than asserted (D-10).

### 2.1 `twinflow-artifact` (import `twinflow_artifact`)

The deterministic artifact emitters. No third-party dependency at all, standard library only.

```
pip install twinflow-artifact
```

Public API:

```python
# twinflow_artifact.svg
SvgCanvas(width, height, theme)          # fixed-pitch layout primitives, no layout engine
  .rect(...) .line(...) .path(...) .text(...) .group(title, desc, role)
  .to_str() -> str                       # sorted attributes, fixed float formatting
LINE_CHART, HISTOGRAM, PARETO_BARS, LADDER   # chart primitives for the report and the map

# twinflow_artifact.html
render(template_name, context) -> str    # string templating, no external template engine

# twinflow_artifact.normalize
ARTIFACT_FILTER_VERSION: str
normalize_svg(text) -> str               # drops generator comments, canonicalises float text
normalize_html(text) -> str              # drops the generated-at comment block only
```

Why this is its own brick: the capability report is "the artifact a hiring manager actually
opens", and D-10 forbids putting the headline artifact behind a heavy optional extra. Every chart
in the report and every value stream map renders through this emitter, which has no font
resolution step, no hash salt, no embedded timestamp, and no layout randomness. Byte stability is
a property of the emitter rather than a property of a plotting library's configuration.

`normalize_svg` and `normalize_html` exist for one reason and are named so that reason cannot be
forgotten: the byte-identity gates run the filter first, the filter is checked in, versioned, and
unit-tested, and `ARTIFACT_FILTER_VERSION` is part of the config hash. A filter that could hide a
real difference is itself a defect, so `test_normalize_is_not_lossy` asserts that the filter
changes nothing except the two comment forms it declares.

### 2.2 `twinflow-findings` (import `twinflow_findings`)

The finding contract runtime and the alarm layer. This is the brick a producer installs when it
raises findings and computes no statistics.

```
pip install twinflow-findings
```

Runtime dependencies: `twinflow-contracts`, `twinflow-artifact`, `pydantic>=2`, `ruamel.yaml`.
Optional extras: `[delta]` adds `deltalake` for the Delta Lake sink.

Public API:

```python
# twinflow_findings.model
Finding, Severity, FindingKind, FindingState, EvidenceWindow, SubjectRef
FindingStateChange

# twinflow_findings.construct
FindingFactory(policy: FindingPolicy, sinks: list[FindingSink], clock: Clock)
  .raise_finding(kind, subject, evidence, detected_sim_time, ...) -> Finding

# twinflow_findings.policy
FindingPolicy.load(rationalization_path, floors, next_tool_policy_path) -> FindingPolicy
next_tool_for(finding, policy) -> list[ToolSuggestion]

# twinflow_findings.sink
FindingSink (protocol) | JsonlFindingSink | DeltaFindingSink | InMemoryFindingSink

# twinflow_findings.alarms
AlarmManager(cfg, policy, clock)
  .ingest(finding) -> AlarmDecision
  .shelve(alarm_id, reason, until_sim_time, actor) -> ShelveRecord
  .acknowledge(alarm_id, actor) -> AckRecord
  .active(now) -> list[Alarm]
  .metrics(window) -> AlarmSystemMetrics
OperatorConsole, ConsoleAssignment
```

This brick exists because of a contradiction the earlier draft carried. The stream's guarantees
(one constructor, one rationalization table, one severity floor, one id rule) belong to every
producer, and most producers are not statistical. The CV auditor, the fleet health scorer, and the
twin sync connector all raise findings, and none of them installs scipy to do it. Putting the
constructor in the statistics brick would have made "nothing depends on twinflow-lss at runtime"
false the moment the second producer landed. D-09 gives each public symbol exactly one owning
package, and this is the owner for every name in the list above.

A vision-only installation reaches the alarm manager the same way every other producer does:
`pip install twinflow-findings`, load the policy files the facility config names, and construct
one `AlarmManager`. The statistics brick builds its own factory from the same policy and the same
sinks, so a process running both shares one manager passed in by the composition root rather than
creating a second.

### 2.3 `twinflow-lss` (import `twinflow_lss`)

The Lean Six Sigma toolkit as code. This is the brick a quality manager installs when they want
only SPC-as-code.

```
pip install twinflow-lss
```

Runtime dependencies: `numpy`, `scipy`, `pyarrow`, `pydantic>=2`, `ruamel.yaml`,
`twinflow-contracts`, `twinflow-findings`, `twinflow-artifact`. No dependency on the twin, the
broker, the historian implementation, or any other twinflow package. Optional extras: `[duckdb]`
adds a DuckDB reader for the historian's Delta tables; `[matplotlib]` adds an alternative chart
renderer whose output is excluded from the byte-identity gates and is never the default.

Public API surface, the only names covered by the semver policy in C9. Every callable in the
`spc`, `capability`, `msa`, `hypothesis`, `trend`, `charts`, `batch`, `sampling`, `ranking`, and
`divergence` modules carries a `@val_gate(...)` decorator naming at least one registry record;
7.5.4 states the CI test that makes that unavoidable.

```python
# twinflow_lss.spc
select_chart(data_type, subgroup_size, opportunity, defect_kind, stream) -> ChartSpec
ControlChart(spec: ChartSpec, limits: LimitPolicy)          # batch and online
  .fit(series) -> ChartFit                                   # phase I
  .evaluate(series, fit) -> list[Violation]                  # phase II
  .update(point) -> list[Violation]                          # online
RULE_SETS: Mapping[str, RuleSet]                             # western_electric, nelson
CONSTANTS.d2(n) | .d3(n) | .c4(n) | .A2(n) | .A3(n) | .B3(n) | .B4(n) | .D3(n) | .D4(n)
PairedSeries, ResidualSeries                                 # observed against predicted
residuals(paired: PairedSeries, method) -> ResidualSeries

# twinflow_lss.capability
capability(sample, spec: SpecLimits, cfg: CapabilityConfig) -> CapabilityResult
sigma_level(dpmo, shift) -> float
dpmo(z_bench) -> float

# twinflow_lss.msa
gage_rr(study: GageStudy, cfg: MsaConfig) -> GageRRResult
attribute_agreement(study: AttributeStudy) -> AttributeAgreementResult
bias_study(...) -> BiasResult
linearity_study(...) -> LinearityResult
stability_study(...) -> StabilityResult

# twinflow_lss.hypothesis
compare(a, b, cfg: HypothesisConfig) -> TestResult      # 2 groups, test auto-selected
compare_many(groups, cfg) -> TestResult                 # k groups
equivalence(a, b, margin, cfg) -> TestResult            # TOST
check_assumptions(samples, cfg, crn_integrity) -> AssumptionReport
adjust(results, method) -> list[TestResult]             # BH or Bonferroni

# twinflow_lss.trend
fit_trend(series, model) -> TrendFit                    # linear, exponential, weibull_hazard
time_to_threshold(fit, threshold) -> Interval           # point estimate, prediction interval

# twinflow_lss.charts
pareto(counts) -> ParetoResult
histogram(sample, spec, rule) -> HistogramResult        # sturges, freedman_diaconis, scott

# twinflow_lss.batch
golden_batch_score(profile, golden, cfg) -> BatchScore   # phase 3i

# twinflow_lss.sampling
z14_plan(lot_size, aql, inspection_level, severity) -> SamplingPlan   # phase 6a11
oc_curve(plan) -> OcCurve
switching(state, history) -> SwitchingDecision

# twinflow_lss.ranking
rank_whatifs(candidates, cfg: RankingConfig) -> WhatIfRanking         # 5.16, phase P3d

# twinflow_lss.divergence
evaluate_divergence(paired: PairedSeries, spec: DivergenceSpec) -> DivergenceResult

# twinflow_lss.report
build_report(window, sources, cfg) -> ReportBundle        # HTML, JSON, assets

# twinflow_lss.validation
REGISTRY: ValGateRegistry
run_gates(phase=None, gate_id=None) -> ValidationRun
val_gate(*gate_ids)                                       # decorator, see 7.5.4
```

Kernel bindings, the deterministic-simulation seam from the locked architecture decisions: the
package never imports `time`, `datetime.now`, `random`, or a socket. It takes a `Clock` and
stream handles in its constructors. Random draws come from `twinflow-rng` through the
name-addressed registry that `docs/design/variability-and-faults.md` section A specifies; this
package never constructs a bit generator. The CI lint that bans wall clock and global RNG outside
the kernel package applies here with no escape-hatch annotations granted (D-02).

CLI, installed as console scripts so the brick is usable without the rest of the repo:

```
twinflow-lss validate-config <path>
twinflow-lss chart --config facility.yaml --chart-id dock3_scan_cycle_time --data events.parquet
twinflow-lss capability --metric station.scan.cycle_time_s --from <t> --to <t>
twinflow-lss gagerr --study study.csv --error-term interaction
twinflow-lss report --from <t> --to <t> --out artifacts/capability-report.html
twinflow-lss validate run [--phase P2] [--gate VG-SPC-06]
twinflow-lss validate report --format md > docs/VALIDATION.md
```

### 2.4 `twinflow-procmine` (import `twinflow_procmine`)

The process mining kit named in A1, written here under Apache-2.0 (D-14). Discovery, conformance,
variant analysis, rework detection, cycle-time contribution, and the discovery recovery benchmark.

```
pip install twinflow-procmine
```

Runtime dependencies: `numpy`, `pyarrow`, `pydantic>=2`, `twinflow-contracts`,
`twinflow-findings`. There is one engine and it ships in this package. PM4Py is not a runtime
dependency, not an optional extra, and never imported by anything this project distributes or
serves. The reason is licensing and D-14 settles it: PM4Py 2.7.23.3 and pm4pyminimal 2.7.23.3 are
AGPL-3.0, read from the package index JSON API on 2026-08-09. Section 13 of that license triggers
on network interaction, and this project serves a dashboard, an MCP server, and an HTTP API.
Importing either would place the whole work under AGPL and end the dual license.

PM4Py appears in exactly one place: a development-only test group, `[oracle]`, installed by the
CI job that runs VG-PM-03 and by nothing else. That job compares this package's fitness and
precision against PM4Py's on the same log and publishes any disagreement. Its output is a
comparison table, not a distributed artifact. OQ-1 records the legal read the owner still owes
that arrangement.

Public API:

```python
# twinflow_procmine.log
EventLog.from_historian(reader, case_notion, window) -> EventLog
EventLog.to_xes(path) / .to_ocel(path)                  # IEEE 1849-2023 XES, OCEL 2.0
CaseNotion: Literal["pallet","lot","order","return","device","batch"]

# twinflow_procmine.discovery
discover(log, miner: Miner, params) -> ProcessModel      # dfg, heuristics, inductive, alpha
Miner protocol

# twinflow_procmine.conformance
token_replay(log, model) -> ReplayResult
align(log, model, sampling: TraceSampling, budget: SearchBudget) -> AlignmentResult
precision(log, model) -> float
deviations(alignment) -> list[Deviation]

# twinflow_procmine.variants
variants(log) -> VariantTable
compare_variants(log, a, b, metric, test_fn) -> TestResult

# twinflow_procmine.rework
rework(log) -> ReworkResult                              # self-loops, k-loops, FPY

# twinflow_procmine.performance
activity_contribution(log) -> ContributionTable          # service against waiting, per activity
handover_matrix(log) -> HandoverMatrix

# twinflow_procmine.benchmark
recovery_benchmark(ground_truth: ProcessModel, log, miners, noise_levels) -> RecoveryTable
footprint(model) -> FootprintMatrix
footprint_f1(a: FootprintMatrix, b: FootprintMatrix) -> float
```

`compare_variants` takes the hypothesis test as a callable rather than importing it. The caller
passes `twinflow_lss.hypothesis.compare` when both bricks are installed. That keeps the dependency
direction one-way and keeps the `TestResult` crossing the boundary as its published schema (4.5)
rather than as a foreign class.

### 2.5 `twinflow-vsm` (import `twinflow_vsm`)

Current-state and future-state value stream maps, plus the SIPOC and swimlane views of 5.15, as
generated artifacts.

```
pip install twinflow-vsm
```

Runtime dependencies: `twinflow-procmine`, `twinflow-contracts`, `twinflow-artifact`,
`pydantic>=2`. Rendering goes through `twinflow_artifact.svg`, a fixed-layout emitter rather than
a layout engine, so the output hash is stable.

```python
# twinflow_vsm
build_current_state(contribution, twin_metrics, classification, cfg) -> ValueStreamMap
build_future_state(current: ValueStreamMap, whatif: WhatIfResult, cfg) -> ValueStreamMap
diff(current, future) -> VsmDiff
render_svg(vsm) -> str
render_table(vsm) -> str          # text equivalent, always written, C12
build_sipoc(model, contribution, topology, cfg) -> Sipoc       # 5.15.1
build_swimlane(log, model, cfg) -> Swimlane                    # 5.15.2
render_sipoc_svg(s) -> str
render_sipoc_table(s) -> str      # text equivalent, always written, C12
render_swimlane_svg(s) -> str
render_swimlane_table(s) -> str   # text equivalent, always written, C12
```

### 2.6 Dependency direction and layering

```
twinflow-contracts        twinflow-artifact
  (schemas + generated      (deterministic svg and html,
   pydantic bindings)        standard library only)
        ^   ^                     ^   ^
        |   |                     |   |
        |   +---- twinflow-findings ---+
        |               ^        ^
        |               |        |
  twinflow-procmine <---+        +---> twinflow-lss
        ^
        |
   twinflow-vsm ----> twinflow-artifact
```

No package imports another's internals. Nothing depends on `twinflow-lss` at runtime, which is
what makes the "adopt just SPC-as-code" promise real, and the promise now holds for the finding
contract too, because that moved down into `twinflow-findings`.

D-09 is enforced rather than described. `test_import_graph_is_acyclic` walks the declared
dependency graph and every module's imports and fails on a cycle.
`test_every_public_name_is_defined_here` asserts that each name in a package's `__all__` is
defined in that package rather than re-exported from a neighbor.
`test_declared_dependencies_cover_every_import` asserts that each import resolves to a
distribution listed in that package's `pyproject.toml`, which is the check that catches a public
API needing a package it does not depend on.

Schemas are authored in `/schemas` and owned by this section in CODEOWNERS. Generated Python
bindings ship in `twinflow-contracts`. That split is deliberate and it is what keeps a producer
from installing scipy to describe a finding.

### 2.7 Agent tool surface exposed from this section

Registered with the agent's tool registry (component 7) and the MCP server (E2). Every one is
schema-constrained per E26(d) and returns a `query_result_id` per E26(f). 5.9.4 states who mints
that id in each phase.

| Tool                                                             | Returns                                                                                                                      |
|------------------------------------------------------------------|------------------------------------------------------------------------------------------------------------------------------|
| `get_findings(window, severity_min, kinds, subject, state)`      | list of `Finding`                                                                                                            |
| `explain_finding(finding_id)`                                    | the finding, its evidence window, the chart that renders it, its rationalization record, and its `suggested_next_tool` chain |
| `run_capability_report(window, metrics, profile)`                | path to the generated HTML plus the machine-readable JSON                                                                    |
| `run_spc(metric, window, chart, rules, stream)`                  | `ChartFit` plus violations                                                                                                   |
| `run_gage_rr(device_class, parts, operators, replicates, seed)`  | `GageRRResult`                                                                                                               |
| `run_hypothesis_test(metric, baseline_window, treatment_window)` | `TestResult` including the assumption trace                                                                                  |
| `get_divergence(metric, window)`                                 | `DivergenceResult` plus the residual chart fit                                                                               |
| `get_vsm(state, window)`                                         | `ValueStreamMap` JSON plus SVG path                                                                                          |
| `run_conformance(case_notion, window)`                           | fitness, precision, deviation list                                                                                           |
| `get_variants(case_notion, window, top_n)`                       | `VariantTable`                                                                                                               |
| `shelve_alarm(alarm_id, reason, duration_s)`                     | `ShelveRecord`, needs autonomy tier L2 or above (E5)                                                                         |
| `get_sipoc(window)`                                              | `Sipoc` JSON plus SVG path (5.15)                                                                                            |
| `get_swimlane(case_notion, window)`                              | `Swimlane` JSON plus SVG path (5.15)                                                                                         |
| `rank_whatifs(whatif_ids, profile)`                              | `WhatIfRanking`: the Pugh table, the stoplight class per candidate, and the `TestResult` ids behind each score (5.16)        |

---

## 3. Domain model

### 3.1 SPC entities

`ChartSpec`, immutable and config-derived:

| Field          | Type                                              | Notes                                                                  |
|----------------|---------------------------------------------------|------------------------------------------------------------------------|
| `chart_id`     | `str`                                             | unique within a facility config; used in finding subjects              |
| `metric`       | `MetricId`                                        | must resolve in the metric registry; config validation fails otherwise |
| `subject`      | `UnsPath` or `DeviceId` or `StationId` or `LotId` | what the chart is about                                                |
| `stream`       | enum                                              | `observed`, `predicted`, `residual`; see 3.2 and 5.2                   |
| `chart_type`   | enum                                              | `i_mr`, `xbar_r`, `xbar_s`, `p`, `np`, `c`, `u`, `ewma`, `cusum`, `t2` |
| `data_type`    | enum                                              | `continuous`, `binary`, `count`                                        |
| `subgroup`     | `SubgroupSpec`                                    | strategy (`fixed_n`, `time_window`, `natural`), `n`, `window_s`        |
| `params`       | dict                                              | `{lambda, L}` for EWMA; `{k, h}` for CUSUM; `{alpha}` for T-squared    |
| `rule_sets`    | list[str]                                         | subset of `western_electric`, `nelson`                                 |
| `severity_map` | `dict[RuleId, Severity]`                          | per-rule severity, constrained by 5.10.4                               |

Invariants. `chart_type` is compatible with `data_type`, so a `p` chart cannot carry
`data_type=continuous`. `subgroup.n >= 2` for `xbar_r` and `xbar_s`, and `== 1` for `i_mr`.
`xbar_r` needs `2 <= n <= 8` and `xbar_s` needs `n >= 9`; the boundary is config-overridable and
the default follows the range over which the published factor table is tabulated (5.3).
`0 < lambda <= 1`. `chart_id` is unique. `stream = residual` needs a `PairedSeries` source and a
`DivergenceSpec`, and config validation rejects it otherwise.

`ChartFit`, a phase I result, persisted so phase II is reproducible. Fields: `chart_id`,
`stream`, `center_line`, `sigma_hat`, `sigma_method`, `ucl`, `lcl`, `zone_boundaries` (the one
and two sigma lines), `n_subgroups`, `baseline_window` (sim-time start and end), `estimator`
(`rbar_d2`, `sbar_c4`, `mr_d2`, `pooled_sd`), `clamped` (true when LCL was clamped to zero),
`zone_validity` (false when the normal-approximation zones are unusable), `fit_id` (deterministic
hash), `config_hash`, `run_id`.

Invariants. `ucl > center_line > lcl` except where a clamp applies, and a clamp is always
recorded rather than silently applied. `sigma_hat > 0`. For `p`, `c`, and `u` charts with varying
subgroup size the limits are per point, and `ucl` and `lcl` carry arrays of the same length as
the series.

`Violation`, the typed violation the source asks for:

| Field                 | Type                                                                      |
|-----------------------|---------------------------------------------------------------------------|
| `rule_set`            | `"western_electric"` or `"nelson"`                                        |
| `rule_number`         | `int`, WE 1 to 4, Nelson 1 to 8                                           |
| `rule_id`             | `str`, for example `"nelson.3"`                                           |
| `chart_id`, `fit_id`  | `str`                                                                     |
| `severity`            | `Severity`                                                                |
| `evidence_window`     | `EvidenceWindow`                                                          |
| `direction`           | `"above"`, `"below"`, `"both"`, `"trend_up"`, `"trend_down"`, `"none"`    |
| `points`              | list of `(index, sim_time, value, sigma_units)`                           |
| `limits_at_detection` | the `ucl`, `lcl`, and `center_line` in force                              |
| `open`                | `bool`, true while the online evaluator is still extending this violation |

`EvidenceWindow`: `start_index`, `end_index`, `start_sim_time`, `end_sim_time`, `n_points`,
`query_result_id`. There is no wall-clock field. The sim-time to wall-time mapping that C2 asks
for is recorded once per run in the provenance sidecar, `manifest.json`, and a reader joins to it
through `run_id` (D-01). An inline wall-clock epoch in every record would make the findings file
different on every run of the same seed, which is exactly what C1 forbids.

### 3.2 Paired and residual series

The source sentence "It runs continuously against both the real telemetry stream and the twin's
predictions" needs a type that holds both, and a rule for what happens when they disagree.

`PairedSeries`: `metric`, `subject`, `case_key` (the join key, usually `(subject, sim_time_bin)`
or a pallet id), `observed` (values with sim times), `predicted` (values with sim times),
`prediction_horizon_s` (how far ahead the twin's value was produced), `n_paired`,
`n_observed_unmatched`, `n_predicted_unmatched`, `join_method`
(`exact_sim_time`, `nearest_within_tolerance`, `case_key`), `join_tolerance_s`.

Invariant: the join is a function, so no observed point pairs with two predicted points. The
unmatched counts are always reported, because a pairing that quietly drops half the observations
would make every downstream residual statistic wrong in a direction nobody could see.

`ResidualSeries`: `metric`, `subject`, `method` (`difference`, `ratio`, `standardized`,
`pit` for the probability integral transform), `values`, `sim_times`, `n`, `source_paired_id`.

- `difference` is `observed - predicted`, and its unit is the metric's own unit.
- `ratio` is `observed / predicted`, defined only where `predicted != 0`, with the excluded count
  reported.
- `standardized` divides the difference by the twin's own predictive standard deviation when the
  twin publishes one, so the residual is dimensionless and comparable across metrics.
- `pit` maps each observation through the twin's predictive distribution function. Under a
  correctly calibrated twin the result is uniform on the unit interval, which turns calibration
  into a distributional question the assumption checker already knows how to ask.

A residual chart is an ordinary control chart whose `stream` is `residual`. That is the whole
mechanism: no new rule engine, no new limit theory, no second code path. A twin that tracks
reality produces residuals that are stable and centerd on zero, and every Western Electric and
Nelson rule then means what it usually means. 5.8 states what a firing on that chart becomes.

### 3.3 Capability entities

`SpecLimits`: `metric`, `lsl` (nullable), `usl` (nullable), `target` (nullable), `unit`,
`derivation` (free text recording where the limit came from, for example "takt at 720 pallets per
shift" or "customer promise, 6pm cutoff"). Invariant: at least one of `lsl` and `usl` is present;
if both, `lsl < usl`; if `target`, then `lsl <= target <= usl`.

The `derivation` field is not decoration. A warehouse cycle time has no engineering spec limit the
way a machined bore does, and a reviewer will ask where the USL came from. The report prints it
next to every Cpk.

`CapabilityResult`: `cp`, `cpk`, `cpu`, `cpl`, `cpm`, `pp`, `ppk`, `ppu`, `ppl`, `sigma_within`,
`sigma_overall`, `sigma_within_method`, `mean`, `n`, `z_bench_within`, `z_bench_overall`,
`sigma_level_z_within`, `sigma_level_z_overall`, `sigma_level_shifted`, `sigma_shift_applied`,
`dpmo_observed`, `dpmo_expected_within`, `dpmo_expected_overall`, each split into `below_lsl`,
`above_usl`, and `total`, `cpk_ci` (lower, upper, level), `normality` (`AssumptionReport`),
`transform` (`none`, `box_cox(lambda)`, `johnson(...)`, `percentile(dist)`), `stability`
(`StabilityVerdict`), `stability_rules` (the rule ids that decided it), `spec` (the `SpecLimits`
used).

The three sigma-level fields replace a pair that had the Six Sigma shift convention backwards.
`sigma_level_z_within` is the unshifted short-term Z. `sigma_level_z_overall` is the unshifted
long-term Z. `sigma_level_shifted` is `z_bench_overall + sigma_shift`, and it is the number the
quoted "six sigma" figure refers to: in the canonical identity a long-term Z of 4.5 is quoted as
a nominal six sigma because `4.5 + 1.5 = 6`. Labeling the shifted number "long term" inverted
that, and VG-CAP-03 validates the identity, so the field names and the gate now agree.

Invariants. `cpk <= cp` always. `cpk == cp` if and only if the mean sits at the spec midpoint, to
tolerance. `cp / pp` and `sigma_overall / sigma_within` agree to a relative tolerance of 1e-12,
which is an IEEE 754 statement about two quotients rather than an exact-equality claim.
`dpmo_expected_*` is monotone decreasing in the corresponding `z_bench`.

### 3.4 MSA entities

`GageStudy`: `parts` (list of ids), `operators` (list of ids), `replicates` (int), `measurements`
(part, operator, replicate, value), `tolerance` (from `SpecLimits` or explicit),
`process_variation` (optional historical sigma, used for the `%StudyVar` denominator),
`ground_truth` (optional `VarianceComponents`, populated only when the study came from a
generator that injected known components).

Invariants: the design is crossed and balanced by default, so every operator measures every part
`replicates` times; an unbalanced design is accepted, sets `result.design = "unbalanced"`, and
disables the average-and-range method, which assumes balance.

`GageRRResult`: `ev`, `av`, `interaction_sd`, `grr`, `pv`, `tv` (all as standard deviations),
`tv_from_total_ss` (the total standard deviation computed from the total sum of squares, kept
separately so closure is a real check), `variance_components` (as variances, with
`%contribution`), `variance_component_ci` (a two-sided interval per component by the modified
large-sample method, with the method name recorded), `study_var` (each component times
`study_var_multiplier`), `pct_study_var`, `pct_tolerance`, `study_var_multiplier`, `ndc`,
`anova_table` (source, DF, SS, MS, F, p), `error_term`, `interaction_pooled`, `method`, `verdict`
(`acceptable`, `marginal`, `unacceptable`), `negative_components_clamped` (list),
`variance_closure_residual` (relative), `variance_closure_defect` (nullable).

Invariants, stated so they can fail. `tv_from_total_ss` is computed from the total sum of squares
independently of the component sum, so closure is a check rather than a tautology. When
`negative_components_clamped` is empty, the relative residual
`abs(tv_from_total_ss^2 - (ev^2 + av^2 + interaction^2 + pv^2)) / tv_from_total_ss^2` is at most
1e-10; that bound comes from double-precision accumulation over the ANOVA sums of squares and is
a software tolerance, not a claim against a published value. When a component was clamped, the
identity does not hold and the residual is reported as `variance_closure_defect` rather than
hidden. Every component is non-negative. The result is invariant under permutation of operator
labels and of part labels.

### 3.5 Hypothesis entities

`AssumptionReport`: `normality` (per group: test name, statistic, p, verdict), `equal_variance`
(test, statistic, p, verdict), `independence` (lag-1 autocorrelation, batch-means diagnostics,
verdict), `paired` (bool), `pairing_evidence` (the `crn_integrity` record when the samples came
from two scenario arms; see 5.7.1), `n_per_group`, `outliers` (count and indices by a stated
rule), `decision_trace` (the ordered list of checks and their outcomes).

`TestResult`: `test` (name), `family` (`parametric`, `nonparametric`, `equivalence`),
`why_selected` (the `AssumptionReport` plus the selection rule id that fired), `statistic`, `df`,
`p_value`, `p_adjusted`, `adjustment_method`, `family_size`, `alpha`, `effect_size` (name, value,
CI), `estimate_ci` (CI on the difference in the metric's own units), `mde` (minimum detectable
effect at the achieved n and power target), `practically_significant` (bool, against the config's
`min_meaningful_difference`), `decision` (`reject`, `fail_to_reject`, `equivalent`,
`inconclusive`), `verdict_sentence` (a plain-language string the agent quotes verbatim rather
than paraphrasing), `n_effective` (after batch means), `query_result_id`.

Invariant: `practically_significant` is computed independently of `p_value`, and the four
combinations are all reachable and all rendered distinctly. A significant result below the
practical threshold reads "statistically significant, not practically significant", which is the
sentence a simulation with 200,000 samples forces an honest engine to be able to say.

### 3.6 Finding, alarm, and console entities

4.2 carries the wire schema. Domain invariants:

A `Finding` is immutable once raised. State changes (`ACTIVE` to `SHELVED`) are separate
`FindingStateChange` events referencing `finding_id`. The historian is append-only (6a11's
audit-trail integrity requirement), so nothing is mutated in place.

`finding_id` is `blake2b(kind, subject, rule_id, evidence_window.start_sim_time, run_id)`
truncated to 16 hex characters. It is stable across re-runs of the same run seed and different
across seeds, because `run_id` is a content address over the manifest hashed core, which carries
the run seed. It carries no wall-clock component, which is what makes the byte-identity gate
possible at all (D-01). `test_run_id_has_no_time_derived_component` asserts the property directly
by running the same scenario twice and comparing ids, and
`test_finding_id_changes_with_seed` asserts the other direction.

Every `Finding` carries a `rationalization_id`. A finding kind with no rationalization record
cannot be raised; the factory raises and CI catches it (VG-ALM-01).

Severity floors: a finding whose kind is in a floored class (`safety`, `security`) cannot be
raised below its floor, and the alarm manager cannot present it below its floor even in flood
mode. This implements the source's "safety findings outrank throughput findings by definition".

`Alarm`: `alarm_id`, `rationalization_id`, `priority` (matrix-derived, never hand-set),
`presented_rank` (see 5.10.4), `console_id`, `first_sim_time`, `last_sim_time`,
`occurrence_count`, `state`, `finding_ids` (every finding collapsed into it), `suppressed_by`
(parent alarm id when causal suppression applied), `shelve` (nullable `ShelveRecord`),
`stale_since` (nullable).

`OperatorConsole`: `console_id`, `name`, `subject_patterns` (ordered list of UNS globs),
`staffed_shifts` (the shift pattern that says how many operator hours the console carries in a
window), `default` (bool). Exactly one console is marked default and it catches every subject no
pattern claims.

`ConsoleAssignment` is the pure function that maps a finding to a console: the first
`subject_patterns` entry that matches, in declared order, else the default console. Declared
order rather than best match, because a matching rule a reader can trace beats one they have to
simulate. This entity exists because the EEMUA alarm rate metrics are per operator and per
console, and a rate with no denominator is not a metric. 5.10.6 states the denominator.

### 3.7 Process mining entities

`EventLog`: columnar (Arrow) with mandatory columns `case_id`, `activity`, `sim_time`,
`lifecycle` (`start` or `complete`, the XES `lifecycle:transition` attribute as defined in IEEE
1849-2023), `resource`, plus arbitrary case and event attributes. `case_notion` is recorded on
the log.

`ProcessModel`: a Petri net (places, transitions, arcs, initial and final marking) with an
optional process-tree and BPMN view. `source` is `"ground_truth"` or
`"discovered(miner, params)"`. Its published schema is 4.5, because it crosses a package boundary
in both directions: component 1 exports it and this section consumes it.

`Deviation`: `case_id`, `position`, `type` (`log_move` for an activity the model does not permit,
`model_move` for a required activity that did not happen, `silent_move`), `activity`, `cost`,
`sim_time`.

`ContributionTable`: per activity, `service_time` (busy), `waiting_time` (queued), `sojourn_time`,
`n_occurrences`, `share_of_lead_time`, `rework_share`, `rank`. Invariant:
`sum(sojourn_time_share)` equals 1.0 to a relative tolerance of 1e-9 over a complete case set.

### 3.8 Value stream map entities

`ValueStreamMap`: `state` (`current` or `future`), `window`, `takt_time_s`, `stations` (ordered),
`inventory_triangles` (between consecutive stations: `units`, `days_of_supply`, computed
`wait_time_s`), `information_flows`, `ladder` (per station: `va_time_s`, `bva_time_s`,
`nva_time_s`, waste type per non-value-added segment), `lead_time_s`, `process_time_s`,
`process_cycle_efficiency`, `kaizen_bursts` (future state only), `provenance` (which mined table,
which twin metrics, which run seed).

`VsmStation`: `name`, `cycle_time_s` (mean and distribution summary), `changeover_time_s`,
`uptime_pct`, `available_time_s`, `operators`, `batch_size`, `first_pass_yield`, `scrap_pct`,
`shifts`.

Invariants: `process_time_s == sum(va_time_s)`; `lead_time_s == sum(va + bva + nva) +
sum(triangle.wait_time_s)`, each to a relative tolerance of 1e-9;
`process_cycle_efficiency == process_time_s / lead_time_s` and lies in `[0, 1]`; Little's Law
holds at steady state within the Monte Carlo interval that VG-VSM-02 measures.

### 3.9 SIPOC, swimlane, and ranking entities

Additions beyond the source, 1.5.

`Sipoc`: `steps` (ordered, the mined model rolled up per `vsm/sipoc.yaml`), `suppliers`,
`inputs`, `outputs`, `customers` (each a list of `{name, provenance}`, where `provenance` is
`mined` or `declared`), `window`, `case_notion`, `provenance` (model id, config hash, run seed).

`Swimlane`: `lanes` (resource pools in declared order), `nodes` (`activity`, `lane`,
`occurrence_share`), `edges` (mined control flow), `handoffs` (per lane pair, the count of edges
crossing it), `window`, `provenance`.

`WhatIfRanking`: `datum` (the current state), `criteria` (ordered metric ids), `rows` (per
candidate: `whatif_id`, per-criterion score in `{-1, 0, +1}`, `net_score`, `cost_class`,
`stoplight`, `test_result_ids`), `order`, `provenance`.

Invariants: `net_score` equals the sum of the row's criterion scores; `order` sorts by
`net_score` descending with ties broken by `whatif_id` ascending; every `test_result_ids` entry
resolves to a `TestResult` of 3.5; every `Sipoc` cell and every `Swimlane` node carries a
provenance the renderer prints.

---

## 4. Events

Everything crossing a package boundary is a versioned schema in `/schemas` (C3), additive-only
within a major version, with producer and consumer contract tests in CI.

### 4.1 The envelope

Every event this section publishes carries the common envelope that D-07 settles before Phase 0
freezes schemas: `run_id`, `producer_id`, `seq`, `sim_ts`, `schema_version`. The sequence number
is dense per `(run_id, producer_id)`, not globally, because the garage tier already runs several
containers plus the Rust device agent and no single global allocator exists. The canonical total
order over any set of events from one run is `(sim_ts, producer_id, seq)`, and every reader in
this section uses it: the JSONL sink sort key (4.8), the replay reader, and the pagination cursor
of `get_findings`.

`producer_id` values this section mints: `lss.spc`, `lss.capability`, `lss.msa`, `lss.hypothesis`,
`lss.divergence`, `lss.alarms`, `procmine.conformance`, `procmine.rework`, `vsm`.

### 4.2 `finding/v1` (published)

The uniform stream. Produced here and by the CV auditor, fleet health, twin sync, the forecast
monitor, the security layer, and the model drift monitor. Consumed by the alarm manager, the
dashboard, the agent, the QMS (6a11), the CMMS (6b), and the replay viewer (E1).

```json
{
  "$id": "https://twinflow.dev/schemas/finding/v1.json",
  "schema_version": "1.0.0",
  "run_id": "run-9c41e0b7a5d3f218",
  "producer_id": "lss.spc",
  "seq": 412,
  "sim_ts": 20260809.0,
  "finding_id": "9f3a1c22b8e04d17",
  "config_hash": "sha256:...",
  "kind": "SPC_RULE_VIOLATION",
  "subject": {
    "type": "uns_path",
    "value": "twinflow/site-a/receiving/line-1/portal-3",
    "isa95_level": 1,
    "aliases": { "device_id": "rfid-p3", "station_id": "scan" }
  },
  "detected_sim_time": 20260809.0,
  "evidence_window": {
    "start_sim_time": 20260800.0,
    "end_sim_time": 20260809.0,
    "start_index": 412,
    "end_index": 420,
    "n_points": 9,
    "query_result_id": "qr-7c1e0004"
  },
  "severity": {
    "level": "HIGH",
    "ordinal": 3,
    "shape": "triangle",
    "label": "High"
  },
  "confidence": 0.98,
  "rationalization_id": "RAT-SPC-001",
  "console_id": "CON-RECEIVING",
  "evidence": {
    "kind": "spc_violation",
    "stream": "observed",
    "rule_set": "nelson",
    "rule_number": 3,
    "metric": "station.scan.cycle_time_s",
    "chart_id": "dock3_scan_cycle_time",
    "fit_id": "fit-7c1e",
    "statistic": 6,
    "limits": { "cl": 8.1, "ucl": 11.4, "lcl": 4.8, "sigma": 1.1 },
    "points": [[412, 20260800.0, 8.4], ["..."]],
    "chart_spec_ref": "charts/dock3_scan_cycle_time.json"
  },
  "suggested_next_tool": [
    {
      "tool": "run_gage_rr",
      "args": { "device_class": "rfid_portal" },
      "reason": "check the measurement system before acting on the process"
    },
    {
      "tool": "get_pdm_trend",
      "args": { "device_id": "rfid-p3" },
      "reason": "a monotone trend on a device metric is a degradation signature"
    }
  ],
  "links": {
    "duplicate_of": null,
    "caused_by": null,
    "supersedes": null,
    "children": []
  },
  "sop_refs": [],
  "state": "NEW"
}
```

Field notes that matter to implementers:

`severity.shape` and `severity.label` carry the non-color channels C12 asks for, so a consumer
never has to derive one from the level. A schema field cannot by itself stop a consumer rendering
color only, so the claim is backed by a test rather than by assertion: every artifact this
section produces is checked by `test_severity_renders_shape_and_label`, which parses the generated
HTML and SVG and asserts that each severity present in the window appears with its declared shape
token and its text label, and the dashboard section carries the matching contract test against the
same fixture.

`evidence.query_result_id` is the hook E26(f)'s grounding checker uses. Any number the agent
states must trace to a logged query result id, and a finding is a query result.

`severity.ordinal` makes ranking total and stable across schema evolution; `level` is the human
name.

`kind` is a closed enum in v1, and new members are an additive change under C3's rule, so
consumers treat an unknown kind as `INFO` with passthrough rather than erroring. That behavior is
contract-tested.

There is no wall-clock field anywhere in the record. The sim-to-wall mapping lives once per run in
`manifest.json` (D-01).

Finding kinds in v1: `SPC_RULE_VIOLATION`, `SPC_CHART_UNFITTABLE`, `CAPABILITY_SHORTFALL`,
`CAPABILITY_UNPROVEN`, `CAPABILITY_ON_UNSTABLE_PROCESS`, `CAPABILITY_NONNORMAL_UNTRANSFORMABLE`,
`MSA_UNACCEPTABLE`, `MSA_MARGINAL`, `MSA_NDC_INSUFFICIENT`, `MSA_BIAS_SIGNIFICANT`,
`MSA_LINEARITY_SIGNIFICANT`, `MSA_VARIANCE_CLOSURE_DEFECT`, `HYPOTHESIS_NO_IMPROVEMENT`,
`HYPOTHESIS_ASSUMPTION_VIOLATED`, `HYPOTHESIS_UNDERPOWERED`, `HYPOTHESIS_PAIRING_LOST`,
`CONFORMANCE_DEVIATION`, `REWORK_LOOP`, `VARIANT_DIVERGENCE`, `BOTTLENECK_DISAGREEMENT`,
`VSM_NVA_EXCESS`, `ALARM_FLOOD`, `ALARM_CHATTERING`, `ALARM_STALE`, `SOP_VIOLATION` (from 4),
`FLEET_HEALTH_DEGRADED` (from 3), `TWIN_DIVERGENCE` (from 6), `TWIN_CALIBRATION_DRIFT` (from 6),
`FORECAST_BIAS_DRIFT` (from 6a), `MODEL_DRIFT` (from E43). Later phases add kinds additively.

### 4.3 `finding_state_change/v1` (published)

`{envelope, finding_id, alarm_id, from_state, to_state, actor {type: human|agent|system, id},
reason, sim_time, autonomy_tier, decision_register_ref}`. Consumed by the decision register (E21),
the audit trail (6a11), and the dashboard.

`autonomy_tier` and `decision_register_ref` are present from v1 even though E21's register is a
Phase 6 deliverable, because adding an envelope-level field after Phase 0 is a major version bump
on every subject. Before the register exists, `autonomy_tier` carries the tier the local config
grants and `decision_register_ref` is null; 5.10.5 states the phase behavior and 8 records the
resequencing.

### 4.4 `alarm/v1` and `alarm_metrics/v1` (published)

`alarm/v1` carries the `Alarm` entity of 3.6. `alarm_metrics/v1` carries the alarm rate metrics of
5.10.6 on a fixed cadence, per console, so they can themselves go on control charts. Its record is
`{envelope, console_id, window_start_sim_time, window_end_sim_time, operator_hours,
annunciated_count, rate_per_operator_hour, peak_in_10min, flood_minutes, chattering_index,
stale_count, top_contributor_share, shelved_count, mean_shelve_duration_s}`.

### 4.5 Cross-package result schemas

Section 4 opens with "everything crossing a package boundary is a versioned schema", and three
types crossed one without a schema in the earlier draft. They are authored here and land at P0
with `finding/v1`.

| Schema                                | Producer                                                                    | Consumer                                                                                        | Why it crosses                                                                 |
|---------------------------------------|-----------------------------------------------------------------------------|-------------------------------------------------------------------------------------------------|--------------------------------------------------------------------------------|
| `/schemas/test_result/v1.json`        | `twinflow-lss`                                                              | `twinflow-procmine` variant comparison, `twinflow-vsm` future-state diff, the agent, the report | `compare_variants` returns one and the future-state map attaches one           |
| `/schemas/contribution_table/v1.json` | `twinflow-procmine`                                                         | `twinflow-vsm`, the report, the agent                                                           | `build_current_state` takes one                                                |
| `/schemas/process_model/v1.json`      | component 1 (`export_reference_model`) and `twinflow-procmine` (`discover`) | `twinflow-procmine` conformance, the report                                                     | the ground-truth model is produced outside this section and consumed inside it |

Each carries the envelope of 4.1 when published as an event and the same field set when passed
in-process, and the generated pydantic binding ships in `twinflow-contracts`. Round-trip contract
tests assert that the in-process object and the serialized form agree.

The what-if ranking of 5.16 adds a fourth: `/schemas/whatif_ranking/v1.json`, produced by
`twinflow-lss` and consumed by the report and the agent. It is authored with 5.16 and lands at
P3d. The subject is new, so authoring it after P0 bumps nothing that shipped.

### 4.6 `divergence_spec/v1` (published)

The twin-divergence contract. The source assigns twin divergence to this section's findings
stream, and component 6 decides the parameter values. Deferring the whole idea to component 6
left a named-but-empty enum member, so the contract is authored here and component 6 fills it in.

```json
{
  "$id": "https://twinflow.dev/schemas/divergence_spec/v1.json",
  "schema_version": "1.0.0",
  "spec_id": "DIV-THROUGHPUT-001",
  "metric": "line.throughput_pph",
  "subject": "twinflow/site-a/receiving/line-1",
  "pairing": {
    "join_method": "nearest_within_tolerance",
    "join_tolerance_s": 30.0,
    "prediction_horizon_s": 900.0,
    "min_paired_points": 100
  },
  "residual_method": "standardized",
  "detector": {
    "kind": "residual_chart",
    "chart_type": "ewma",
    "params": { "lambda": 0.2, "L": 2.7 },
    "rule_sets": ["nelson"],
    "stability_rules": ["nelson.1", "nelson.2"]
  },
  "magnitude": {
    "min_absolute_difference": 12.0,
    "unit": "pallets/h",
    "min_relative_difference": 0.05,
    "min_consecutive_points": 3
  },
  "calibration": {
    "pit_uniformity_test": "anderson_darling",
    "alpha": 0.01
  },
  "finding_kind_on_shift": "TWIN_DIVERGENCE",
  "finding_kind_on_calibration_failure": "TWIN_CALIBRATION_DRIFT",
  "owner": "component-6"
}
```

Every field except the numbers under `magnitude` and `calibration` has a default this section
supplies. Component 6 owns the numbers because only it knows what size of divergence matters for a
given metric. OQ-13 no longer asks what divergence is; it asks component 6 to fill in the values
and states what happens until it does: the spec is absent, the residual charts still run, and the
finding is raised on the chart rule alone with `magnitude` unenforced and that fact recorded on
the finding.

### 4.7 Consumed events

| Event                | From                     | Used for                                                                                   |
|----------------------|--------------------------|--------------------------------------------------------------------------------------------|
| `telemetry/v1`       | component 2 sensor fleet | the observed series behind every control chart                                             |
| `twin_prediction/v1` | component 1 twin         | the predicted series behind every residual chart                                           |
| `process_event/v1`   | component 1 twin         | the process mining event log: `case_id`, `activity`, `lifecycle`, `resource`, `sim_time`   |
| `twin_metric/v1`     | component 1              | cycle time, changeover, uptime, WIP for the value stream map stations                      |
| `whatif_result/v1`   | component 7 and E9       | baseline and treatment sample references, plus the accepted delta for the future-state map |
| `gage_study/v1`      | component 2              | generated repeated measures with `ground_truth` variance components                        |
| `spec_limits/v1`     | config loader            | `SpecLimits` per metric                                                                    |
| `sop_document/v1`    | E8                       | clause ids for `Finding.sop_refs`                                                          |
| `crn_integrity/v1`   | the scenario runner      | per-stream draw counts for both arms, which decides paired against unpaired (5.7.1)        |

`telemetry/v1` carries the resolved metric name. Sparkplug B metric aliases are resolved by the
device fleet's decoder before publication, and the alias travels only as provenance on the record.
The chart layer never sees an alias, which is why a birth certificate arriving late cannot change
which chart a reading lands on.

### 4.8 On-disk formats

Two writers behind one `FindingSink` protocol, because E1's replay demo must work from static
files served by GitHub Pages with no server.

`JsonlFindingSink` writes newline-delimited JSON, one finding per line, sorted by the canonical
total order `(sim_ts, producer_id, seq)` of 4.1, so the file is byte-stable under C1. It is
gzipped for the replay viewer with `mtime=0` and no filename field in the gzip header, because the
default gzip header carries a modification time and the source filename and both would make the
compressed file differ between two runs whose uncompressed bytes are identical. VG-DET-01 asserts
byte stability of the compressed file, not only of the JSONL.

`DeltaFindingSink` writes a Delta Lake table through `deltalake`, partitioned by
`(run_id, date_bucket)`, queried through DuckDB over Arrow. This is the historian path. It ships
behind the `[delta]` extra of `twinflow-findings`; the shipped default configuration writes
`sinks: [jsonl]` only, so a default install never fails at the first raised finding on a missing
dependency.

Both sinks are written from the same in-memory records in the same order, and a test asserts the
two representations round-trip to identical `Finding` objects.

---

## 5. Behavior

### 5.1 Chart selection by data type

`select_chart` is a pure function implementing the decision tree, returning a `ChartSpec` and a
`rationale` string the agent can quote.

```
continuous?
  yes -> subgroup size n
           n == 1              -> i_mr
           2 <= n <= 8         -> xbar_r
           n >= 9              -> xbar_s
         (plus ewma or cusum when cfg.small_shift_detection is on, run alongside, not instead)
  no  -> counting defectives (a unit is good or bad) or defects (a unit can have several)?
           defectives -> constant subgroup size?  yes -> np    no -> p
           defects    -> constant opportunity?    yes -> c     no -> u
```

Multivariate metrics (a correlated sensor group on one asset) route to `t2`. The boundaries are
config-overridable through `spc.selection.xbar_s_min_n`, and the defaults follow the range over
which the published factor table is tabulated (5.3).

`chart: auto` in config invokes this function at load. `chart: <explicit>` skips it, and the
loader raises a warning-level config diagnostic when the explicit choice contradicts the tree,
with the tree's reasoning in the message. Overriding is allowed; overriding silently is not.

The `stream` argument is orthogonal to the tree. The same tree runs for an observed series, a
predicted series, and a residual series, and only the default estimator differs (5.2).

### 5.2 Three streams: observed, predicted, residual

The source's "runs continuously against both the real telemetry stream and the twin's
predictions" is implemented as three chart streams over the same machinery.

| Stream      | Source event                   | What a rule firing means                                                  | Default finding kind                                    |
|-------------|--------------------------------|---------------------------------------------------------------------------|---------------------------------------------------------|
| `observed`  | `telemetry/v1`                 | the process changed                                                       | `SPC_RULE_VIOLATION`                                    |
| `predicted` | `twin_prediction/v1`           | the model's own output changed, which is a model event, not a plant event | `SPC_RULE_VIOLATION` with `evidence.stream = predicted` |
| `residual`  | the difference of the two, 3.2 | the model and the plant have parted company                               | `TWIN_DIVERGENCE`                                       |

Charting the predicted stream on its own looks redundant until the twin is recalibrated mid-run.
A step in the predicted series with no matching step in the observed series is a recalibration
artifact, and separating the two streams is what lets the report say which of the three things
moved.

Pairing runs before residuals. `PairedSeries` is built by `join_method`, and the three unmatched
counts are carried on the result and printed in the report. A pairing that matched fewer than
`pairing.min_paired_points` points does not produce a residual chart at all; it raises
`SPC_CHART_UNFITTABLE` with the reason `insufficient_paired_points`, because a residual chart
fitted on 12 points is a number with the shape of evidence and none of the substance.

Residual charts default to `i_mr` with the `mr_d2` estimator, because residuals arrive one per
paired point and have no natural subgroup. When the twin publishes a predictive standard
deviation, `residual_method: standardized` is the default and the chart's center line is expected
at zero with unit sigma, which makes the limits interpretable without a fit.

Phase I on a residual chart uses a declared calibration window in which the twin is known to be
tracking, named in config as `divergence.baseline_window`. Fitting residual limits on a window
that already contains a divergence would fold the defect into the yardstick.

### 5.3 Limits, estimators, and phase I against phase II

Sigma estimators, all implemented, selected by config:

| Estimator   | Formula                                 | Default for                                      |
|-------------|-----------------------------------------|--------------------------------------------------|
| `mr_d2`     | `MRbar / d2(2)`                         | I-MR and residual charts                         |
| `rbar_d2`   | `Rbar / d2(n)`                          | X-bar and R                                      |
| `sbar_c4`   | `Sbar / c4(n)`                          | X-bar and s                                      |
| `pooled_sd` | `sqrt(sum((n_i-1) s_i^2) / sum(n_i-1))` | capability's within estimate when subgroups vary |

`CONSTANTS` are computed analytically at import time and cross-checked against the transcribed
published table (VG-SPC-01, VG-SPC-02):

- `c4(n) = sqrt(2/(n-1)) * Gamma(n/2) / Gamma((n-1)/2)`, which is the closed form the
  NIST/SEMATECH e-Handbook prints in section 6.3.2.
- `d2(n) = integral over R of [1 - (1 - Phi(x))^n - Phi(x)^n] dx`, evaluated by adaptive
  quadrature.
- `d3(n)` from `sqrt(E[R^2] - d2^2)` with `E[R^2]` from the corresponding double integral.
- `A2 = 3/(d2 sqrt(n))`, `A3 = 3/(c4 sqrt(n))`, `D3 = max(0, 1 - 3 d3/d2)`, `D4 = 1 + 3 d3/d2`,
  `B3 = max(0, 1 - 3 sqrt(1-c4^2)/c4)`, `B4 = 1 + 3 sqrt(1-c4^2)/c4`.

Computing them rather than only transcribing them makes the published table a check rather than
the source of truth, and the two agreeing is itself evidence. 7.5.5 states exactly which
constants and which values of n a published table covers, because that turned out to be a smaller
set than the earlier draft claimed.

`LimitPolicy`:

- `frozen` fits once on a baseline window and then monitors. This is the default, and the only
  policy under which rule firings mean what SPC theory says they mean.
- `rolling(window)` refits over a trailing window. It is available, and the fit records
  `theory_caveat: "rolling limits chase the process; rule ARLs do not apply"`, which the report
  prints.
- `rebaseline_on_change` refits when an accepted what-if changes the config (E5). The refit emits
  a `finding_state_change` with `reason: "process change accepted, limits re-baselined"` so the
  audit trail shows exactly when the yardstick moved. Findings raised before the re-baseline are
  never retro-suppressed.

Phase I needs a minimum baseline: `spc.baseline.min_subgroups`, default 25 subgroups, or
`min_points_individuals`, default 100 for I-MR. Below it the engine refuses and raises
`SPC_CHART_UNFITTABLE` rather than fitting limits nobody can trust.

### 5.4 Rule evaluation

Two rule sets, both fully implemented, selectable per chart and combinable.

Western Electric, from Western Electric Company, _Statistical Quality Control Handbook_, 1956,
restated in the NIST/SEMATECH e-Handbook section 6.3.2:

| Rule | Statement                                                    |
|------|--------------------------------------------------------------|
| WE1  | one point beyond 3 sigma                                     |
| WE2  | two of three consecutive points beyond 2 sigma, same side    |
| WE3  | four of five consecutive points beyond 1 sigma, same side    |
| WE4  | eight consecutive points on the same side of the center line |

Nelson, from Nelson, "The Shewhart Control Chart: Tests for Special Causes", _Journal of Quality
Technology_ 16(4), 1984:

| Rule | Statement                                                             |
|------|-----------------------------------------------------------------------|
| N1   | one point beyond 3 sigma                                              |
| N2   | nine points in a row on the same side of the center line              |
| N3   | six points in a row, all increasing or all decreasing                 |
| N4   | fourteen points in a row alternating up and down                      |
| N5   | two of three consecutive points beyond 2 sigma, same side             |
| N6   | four of five consecutive points beyond 1 sigma, same side             |
| N7   | fifteen points in a row within 1 sigma, either side                   |
| N8   | eight points in a row beyond 1 sigma, both sides, none within 1 sigma |

Implementation notes:

Rules are windowed scanners over the sigma-zone encoding of each point. The zone encoding is
computed once (the `-3, -2, -1, 0, +1, +2, +3` bucket plus the signed sigma distance), and every
rule reads the encoding rather than the raw values. That is what makes P-SPC-01's scale and
location equivariance hold by construction.

Overlapping firings of the same rule merge into one `Violation` with the union evidence window
when they share any point, so a sustained shift produces one violation that grows rather than one
violation per point. Findings-level dedupe (5.10.3) is a second, independent layer.

Ties on constant series: N3 (six increasing or decreasing) treats equal consecutive values as
breaking the run, and N4 (alternating) treats equal values as breaking the alternation. Both
choices are documented and unit-tested because implementations disagree here and a reviewer may
check.

Online state, stated precisely because the earlier draft claimed something the merge rule makes
impossible. Each rule keeps two things: a bounded ring buffer of at most 15 zone codes, which is
the longest window any rule of either set inspects, and, per rule, at most one `OpenViolation`
record holding `(start_index, start_sim_time, n_points, running_min, running_max,
running_extreme_sigma, last_contributing_index)`. `update(point)` does O(1) work and touches
O(active rules) state, which is bounded by 12. It does not hold O(1) memory in the number of
points, and it never did: a 400-point sustained run on one side of the center line has a
400-point union evidence window, and 15 zone codes cannot represent one. What the record holds is
the window's endpoints and its running extremes, which is all the union window needs. The claim
this section makes is that the online and batch paths produce the same violations, including the
same union windows, on the same series (P-NUM-01, P-SPC-06), and P-SPC-07 tests it on a
10,000-point sustained shift specifically because that is the case the bounded buffer cannot
handle by itself.

An `OpenViolation` closes when the rule's condition fails on a new point, at which point the
`Violation` is finalised with `open: false` and handed to the finding factory. A violation still
open at the end of a batch or at the end of a run is finalised with `open: true` recorded, so a
reader can tell "the shift ended" from "the data ended".

Attribute charts use the same rules against their own sigma zones, with the caveat that the
normal-approximation zones are poor at low `np`. The fit records `zone_validity: false` when
`n * pbar < 5`, and rules 2, 3, 5, 6, 7, and 8 are suppressed with the reason recorded.

Each `Violation` becomes exactly one `Finding`.

### 5.5 Capability

Order of operations, enforced:

1. Stability first. When `capability.require_stability` is true (the default), the metric's SPC
   chart runs over the same window. The stability criterion is named by rule id rather than by
   rule number, because rule 2 means different things in the two sets and the same data would
   otherwise produce different verdicts under different rule sets with no config key controlling
   it. The default is `capability.stability_rules: [we.1, we.2, nelson.1, nelson.2]`, the union
   of the two single-point and short-run rules. A firing of any listed rule means the process is
   not in control and the capability numbers describe nothing. The engine still computes them,
   marks `stability.verdict = "unstable"`, records `stability_rules`, and raises
   `CAPABILITY_ON_UNSTABLE_PROCESS` at HIGH severity. The report prints the indices struck through
   with the reason. This is the discipline the requirement implies by putting SPC before
   capability in the bullet list.
2. Measurement system next. When a `GageRRResult` exists for the metric's device class and
   `%StudyVar > msa.thresholds.grr_pct_marginal`, the capability result is annotated
   `confidence_degraded_by: <MSA finding id>` and its confidence drops. A Cpk computed through a
   gauge that eats 35 percent of the tolerance is a measurement artifact, and the engine says so.
3. Normality. Anderson-Darling by default (`capability.normality.test`). On failure the
   configured `on_fail` path runs: Box-Cox with lambda searched over a declared grid and reported,
   the Johnson transform, or the percentile method against a fitted distribution
   (`Cp = (USL - LSL) / (X_99.865 - X_0.135)`). The chosen path is always in the result and always
   printed. When no path succeeds, the engine raises `CAPABILITY_NONNORMAL_UNTRANSFORMABLE` and
   reports only the observed PPM, which needs no distributional assumption.
4. Indices.
   - `Cp = (USL - LSL) / (6 sigma_within)`
   - `CPU = (USL - mu) / (3 sigma_within)`, `CPL = (mu - LSL) / (3 sigma_within)`,
     `Cpk = min(CPU, CPL)`
   - `Cpm = (USL - LSL) / (6 sqrt(sigma_within^2 + (mu - T)^2))` when a target exists, which is
     the form the e-Handbook prints in section 6.1.6
   - `Pp`, `PPU`, `PPL`, and `Ppk` identically with `sigma_overall`, the sample standard deviation
     with `n-1`
   - A one-sided spec yields only the corresponding index, and `Cp` is null rather than silently
     computed from a fabricated second limit
5. Sigma level and DPMO. `z_bench = Phi^-1(1 - (p_below + p_above))`, where the tail probabilities
   come from the fitted, possibly transformed, distribution. Reported three ways so no convention
   argument can land: `z_bench_within` and `z_bench_overall` unshifted;
   `sigma_level_z_within = z_bench_within`; `sigma_level_z_overall = z_bench_overall`; and
   `sigma_level_shifted = z_bench_overall + capability.sigma_shift` (default 1.5) with
   `sigma_shift_applied` recorded. `dpmo = (1 - Phi(z)) * 1e6` for the corresponding tails. The
   report prints the PPM table with rows `< LSL`, `> USL`, and `Total` and columns `Observed`,
   `Expected Within`, and `Expected Overall`. The caption states which sigma-level convention the
   figure above it uses, in words, every time.
6. Confidence interval on Cpk. Bissell's approximation,
   `Cpk +/- z_{1-alpha/2} sqrt(1/(9n) + Cpk^2 / (2(n-1)))`, attributed to Bissell, "How reliable
   is your capability index?", _Applied Statistics_ 39(3), 1990. Always reported. A point Cpk from
   n=30 with no interval is the most common way capability studies mislead.
7. Findings, in three bands rather than two, so the ambiguous middle is never silently green.
   Capability is declared only when the lower confidence bound of Cpk is at or above
   `capability.cpk_target`. When the lower bound is below the target and the upper bound is at or
   above it, the engine raises `CAPABILITY_UNPROVEN`: the study cannot demonstrate capability at
   this sample size, and the finding carries the n that would. When the upper bound falls below
   the target, the engine raises `CAPABILITY_SHORTFALL`: the process is incapable with high
   confidence, and severity scales with the gap. Judging capability against the lower bound is the
   convention AIAG-style capability practice uses; the upper bound is retained as the threshold
   for the stronger finding rather than as the only trigger.

### 5.6 Measurement system analysis

The source's key sentence: "the sim can generate repeated measures with known operator/part
variance, so the engine's answer has a ground truth to be tested against".

Two producers of a `gage_study/v1` record exist, and separating them removes a forward dependency
that would otherwise have made a P2 gate depend on a P3 deliverable.
`twinflow_lss.testing.gage_study_generator` is a statistical fixture generator that lives in this
brick, takes injected `sigma_part`, `sigma_operator`, `sigma_interaction`, and
`sigma_repeatability` plus a named stream, and produces a balanced crossed study. It has no
sensor model in it, so it lands at P2 with the rest of the MSA layer and VG-MSA-08 runs against it
from the start. Component 2's sensor catalog produces the second one, a study drawn through a real
device's read process with its declared failure modes, and VG-MSA-08 re-runs against that at P3
without changing the gate's assertion.

#### 5.6.1 ANOVA method

Crossed design, parts random, operators random. Sums of squares for Part, Operator,
Part by Operator, and Repeatability (Error), with the standard balanced-design formulas.

Two F-test error terms, both implemented:

- `error_term: "repeatability"` divides the Part and Operator mean squares by MS(Repeatability).
- `error_term: "interaction"` divides them by MS(Part by Operator).

Both are gated against their own published output, VG-MSA-01 and VG-MSA-02. Config selects the
default and the report prints which was used. Getting this wrong is the most common Gage R and R
implementation error, and having both is the reason the engine can claim correctness rather than
assert it.

Interaction pooling: when `p(interaction) > msa.interaction_pool_alpha` (default 0.25), the
interaction is pooled into the error term and the model refits. `interaction_pooled` is recorded
(VG-MSA-04).

Variance components: `sigma^2_repeatability = MS_error`;
`sigma^2_interaction = (MS_int - MS_error) / r`;
`sigma^2_operator = (MS_op - MS_int) / (n_parts * r)`;
`sigma^2_part = (MS_part - MS_int) / (n_ops * r)`, with `MS_error` substituted for `MS_int` when
pooled. Negative estimates clamp to zero, the clamp is listed in `negative_components_clamped`,
and the report shows it.

Reporting: `EV = sigma_repeatability`, `AV = sqrt(sigma^2_operator + sigma^2_interaction)`,
`GRR = sqrt(EV^2 + AV^2)`, `PV = sigma_part`, and `TV = sqrt(GRR^2 + PV^2)`.
`tv_from_total_ss` is computed separately from the total sum of squares so that 3.4's closure
invariant is a real check.

`%Contribution` is computed on variances. `%StudyVar` is computed on standard deviations times
`msa.study_var_multiplier`. `%Tolerance = study_var_multiplier * GRR / (USL - LSL)`, using the
same multiplier, because a study run at 5.15 that reported `%StudyVar` on one basis and
`%Tolerance` on another produced two numbers a reader would compare and that are not comparable. `ndc =
trunc(1.41 * PV / GRR)`.

The 10 and 30 percent verdict thresholds are defined against the 6.0 basis. Selecting
`study_var_multiplier: 5.15` rescales them by `5.15 / 6.0` and the report prints both the raw and
the rescaled threshold, or, when `msa.rescale_thresholds` is false, the loader raises a
config diagnostic naming the mismatch. Silently comparing a 5.15-basis percentage against a
6.0-basis threshold is not an available behavior.

Verdict: `%StudyVar < 10` acceptable, 10 to 30 marginal, above 30 unacceptable; `ndc >= 5`
needed. Findings: `MSA_UNACCEPTABLE` at CRITICAL, because it invalidates every downstream
statistic on that metric; `MSA_MARGINAL` at MEDIUM; `MSA_NDC_INSUFFICIENT` at HIGH;
`MSA_VARIANCE_CLOSURE_DEFECT` at HIGH when a clamp broke closure.

Confidence intervals on the variance components are computed by the modified large-sample method
and carried in `variance_component_ci`, with the method name on the result. They exist because
P-MSA-03 compares a replicated study's components against the original study's intervals, and a
property that references a field the schema does not carry is not a property.

#### 5.6.2 Average and range method

The X-bar and R method with `K1`, `K2`, and `K3` constants, for the balanced case only.
`EV = Rbar_bar * K1`, `AV = sqrt((Xdiff * K2)^2 - EV^2 / (n_parts * r))` clamped at zero, and
`PV = Rp * K3`. It is implemented because the published worked examples use it and because it is
what a plant's paper form computes, so a reviewer with field experience will look for it
(VG-MSA-03).

#### 5.6.3 Bias

Compare the mean of repeated measurements of a reference part against its known reference value.
Report bias, its t statistic and p, the confidence interval on bias, and `%Bias` of process
variation. Raise `MSA_BIAS_SIGNIFICANT` when the interval excludes zero. This maps directly to
the sensor catalog's calibration-loss failure mode.

#### 5.6.4 Linearity

Regress bias against reference value across at least five reference parts spanning the operating
range. Report slope, intercept, their t tests, `%Linearity = abs(slope) * process_variation`, and
the fitted band. Raise `MSA_LINEARITY_SIGNIFICANT` when the slope is significant. The regression
itself is gated by VG-NUM-03, so linearity inherits a certified numerical core.

#### 5.6.5 Stability

An X-bar and R chart on repeated measurements of a master part over time. This is 5.1's machinery
pointed at a reference standard, and it is how sensor drift becomes an MSA finding rather than a
process finding. It maps to the catalog's drift and stuck-at signatures.

#### 5.6.6 Attribute agreement analysis

For pass and fail judgements, which is what the CV auditor produces (component 4).
Within-appraiser agreement, between-appraiser agreement, each appraiser against the known
standard, and all appraisers against the standard, with Cohen's kappa for two raters and Fleiss'
kappa for more than two, each with a confidence interval. The 0.7 and 0.4 kappa thresholds are
quoted from the AIAG measurement systems analysis manual and attributed in the report caption,
not stated as bare fact. This is what lets the source's "sensor disagreement itself becomes an
audit finding" be quantified rather than asserted.

### 5.7 Hypothesis testing for improvement validation

Triggered when a what-if is applied (component 7), when an S&OE corrective action lands (E15),
when a CAPA claims effectiveness (6a11), and on demand through `run_hypothesis_test`.

#### 5.7.1 The assumption checker

Ordered, and the order is the `decision_trace`:

1. Paired or independent. Two samples are paired when they come from two arms of one scenario
   comparison and every stream present in both arms drew the same number of values. That
   condition is not inferred here; it arrives as the `crn_integrity` record that
   `docs/design/variability-and-faults.md` section A.5 specifies, which carries the per-stream
   draw count for each arm. The checker applies a paired test only when every shared stream's
   counts match, and applies the independent-samples test otherwise. When pairing is lost, the
   checker records why in the `decision_trace` and raises `HYPOTHESIS_PAIRING_LOST` at LOW
   severity, because a comparison that silently degrades from paired to unpaired loses power that
   the reader would otherwise attribute to the change under test. This is the single most likely
   way the paired-comparison claim would have degraded without anyone noticing, and it is why the
   record is a consumed event (4.7) rather than an assumption.
2. Independence within a sample. Simulation output is serially correlated, so a naive t test on
   200,000 consecutive cycle times has a badly inflated type I error. The checker computes lag-1
   autocorrelation and, when `abs(rho) > hypothesis.independence.rho_threshold` (default 0.1),
   switches to the batch means method: partition into at least `min_batches` batches (default
   30), check batch independence, and run the test on batch means with
   `n_effective = n_batches`. Reference: Law, _Simulation Modeling and Analysis_, 5th edition,
   chapter 9. This is the most important correctness decision in the hypothesis layer and
   VG-HYP-23 gates it.
3. Normality. Anderson-Darling per group by default, Shapiro-Wilk available, at
   `hypothesis.alpha_assumption` (default 0.05). Applied to batch means when batching is active,
   where the central limit theorem usually makes it pass, which is one of the reasons batching is
   right.
4. Equal variance. Levene (Brown-Forsythe, median-centerd) by default, Bartlett available.
5. Outliers. Reported by a stated rule (median plus or minus 3 MAD) and never removed
   automatically. A flagged outlier appears in the result and in the report.

#### 5.7.2 Test selection

| Situation                                     | Test                                                                                  |
|-----------------------------------------------|---------------------------------------------------------------------------------------|
| 2 groups, paired, normal                      | paired t                                                                              |
| 2 groups, paired, non-normal                  | Wilcoxon signed-rank                                                                  |
| 2 groups, independent, normal, equal variance | pooled two-sample t, only when `hypothesis.prefer_welch` is false                     |
| 2 groups, independent, normal                 | Welch's t, the default, because equal variance is not assumed unless asked            |
| 2 groups, independent, non-normal             | Mann-Whitney U, exact for small n, normal approximation with tie correction otherwise |
| k > 2 groups, normal, equal variance          | one-way ANOVA, Tukey HSD post-hoc                                                     |
| k > 2 groups, normal, unequal variance        | Welch's ANOVA, Games-Howell post-hoc                                                  |
| k > 2 groups, non-normal                      | Kruskal-Wallis, Dunn post-hoc with BH adjustment                                      |
| k > 2 groups, heavy-tailed or many ties       | Mood's median test                                                                    |
| proportions, 2 groups                         | two-proportion z, Fisher exact when any expected cell is below 5                      |
| proportions, k groups                         | chi-square test of independence                                                       |
| "the change did not make it worse"            | TOST equivalence against `hypothesis.equivalence_margin`                              |

The selected rule id is in `why_selected`, so `explain_finding` can answer "why a Mann-Whitney and
not a t test" with the test statistics that drove the choice.

#### 5.7.3 Effect size, intervals, and power

Cohen's d with the Hedges' g small-sample correction `J = 1 - 3/(4m - 1)`, with the exact gamma
form used in the implementation and the approximation checked against it, and the interval from
the non-central t distribution.

Rank-biserial correlation for Mann-Whitney and Cliff's delta, with intervals by seeded bootstrap.
The bootstrap draws from the named stream `lss.hypothesis.bootstrap`, so it is deterministic under
C1 and adding it cannot shift any other number (D-03, and section A.2 rule 1 of the variability
section).

Eta-squared and omega-squared for ANOVA.

A confidence interval on the difference in the metric's own units, which is the number an
operations leader acts on.

Observed, post-hoc power is deliberately not reported. The result instead carries the minimum
detectable effect at the achieved `n_effective`, alpha, and a target power of 0.80, plus the
prospective n needed for the configured minimum meaningful difference. The rationale, cited in the
docs, is Hoenig and Heisey, "The Abuse of Power", _The American Statistician_ 55(1), 2001. A
reviewer who knows this literature will notice.

#### 5.7.4 Practical significance

Every metric may declare `min_meaningful_difference` in config. `practically_significant` is
computed by comparing the confidence interval on the difference against that threshold. All four
quadrants render distinctly:

| Statistically significant | Practically significant                            | Verdict sentence                                                                                           |
|---------------------------|----------------------------------------------------|------------------------------------------------------------------------------------------------------------|
| yes                       | yes                                                | "Throughput increased by 41 pallets/shift (95% CI 33 to 49), above the 20 pallet threshold."               |
| yes                       | no                                                 | "The 3 pallet/shift increase is statistically significant but below the 20 pallet threshold that matters." |
| no                        | inconclusive, the interval spans the threshold     | "The data cannot distinguish a meaningful change from none; 4,000 more cases would be needed."             |
| no                        | equivalent, the interval lies inside the threshold | "The change is statistically equivalent to no change within the 20 pallet margin."                         |

The last row needs TOST, which is why equivalence testing is not optional. Without it the engine
can never say "this change did not hurt anything", only "we failed to prove it did", and those are
different sentences.

#### 5.7.5 Multiplicity

`compare_scenarios` (component 7) ranks several candidate changes. Testing eight scenarios at
alpha 0.05 gives a 34 percent chance of at least one false positive under the global null, which
is `1 - 0.95^8`. `adjust(results, "bh")` applies Benjamini-Hochberg FDR control, attributed to
Benjamini and Hochberg, _Journal of the Royal Statistical Society Series B_ 57(1), 1995, across
the family and reports `p_adjusted` alongside `p_value`, with `adjustment_method` and
`family_size` recorded. `adjust(results, "bonferroni")` is the alternative and is gated by the
same record. The investment-roadmap table the agent produces uses adjusted p-values.

### 5.8 Twin divergence

The residual charts of 5.2 plus the `DivergenceSpec` of 4.6 make twin divergence a computed
finding rather than a named enum member.

`evaluate_divergence(paired, spec)` runs four checks in order and stops at the first that fires:

1. Pairing sufficiency. Fewer than `spec.pairing.min_paired_points` paired points raises
   `SPC_CHART_UNFITTABLE` and stops.
2. Calibration. The probability integral transform residuals are tested for uniformity by the
   configured test at `spec.calibration.alpha`. A failure means the twin's predictive
   distribution is mis-shaped even where its central tendency is right, and raises
   `TWIN_CALIBRATION_DRIFT`.
3. Shift. The residual control chart is evaluated under `spec.detector`. A firing of any listed
   rule is a candidate divergence.
4. Magnitude. A candidate becomes `TWIN_DIVERGENCE` only when the mean residual over the firing
   window exceeds both `magnitude.min_absolute_difference` and
   `magnitude.min_relative_difference`, over at least `magnitude.min_consecutive_points`. Without
   the magnitude filter a well-fitted twin raises a divergence finding every 371 points by
   construction, which is the false-alarm rate the rule was designed to have.

When component 6 has not yet supplied a spec for a metric, checks 1 and 3 still run against the
defaults, check 4 is skipped, and the finding records `magnitude_enforced: false` so nobody reads
an unfiltered chart firing as a validated divergence.

The finding's suggested next tool chain starts at `get_fleet_health`, because the first question
about a divergence is whether the data is wrong before the model is.

---

### 5.9 The uniform findings stream

#### 5.9.1 One constructor, and where it lives

Every producer calls `FindingFactory.raise_finding`, which lives in `twinflow-findings` (2.2) so
that a producer with no statistics can call it. The factory:

1. Validates against `/schemas/finding/v1.json`.
2. Resolves `rationalization_id` from the rationalization table and refuses when absent.
3. Applies the severity floor for the finding's class.
4. Resolves the console through `ConsoleAssignment`.
5. Computes the deterministic `finding_id`.
6. Attaches `suggested_next_tool` from the policy file.
7. Writes to the configured sinks in the order they are declared.
8. Hands the finding to the `AlarmManager`.

#### 5.9.2 Identity

`finding_id` is computed as 3.6 states. The only input that could carry time is `run_id`, and
`run_id` is minted by the kernel as a content address over the manifest hashed core, which D-01
defines as the run seed, the resolved config hash, the schema snapshot hash, the scenario id, the
mode, the tick rate, the horizon, the warmup, and the fault schedule hash. Wall-clock start,
git provenance, package versions, host, and platform live in the provenance sidecar and are not
in the hash. Two runs of the same seed and config seconds apart mint the same `run_id`,
the same finding ids, the same sort order, and the same bytes.

#### 5.9.3 Suggested next tool

The chaining policy is data, not code: `findings/next_tool_policy.yaml`, schema-validated, one
entry per finding kind with optional predicates on evidence fields. It encodes how a Black Belt
chains tools, and being able to point at the file and say "this is the chaining logic, it is
reviewable" is worth more than clever code. The default chains:

| Finding kind                             | Chain                                                                                                                                    |
|------------------------------------------|------------------------------------------------------------------------------------------------------------------------------------------|
| `SPC_RULE_VIOLATION` on a device metric  | `run_gage_rr`, then `get_pdm_trend`, then `run_whatif`                                                                                   |
| `SPC_RULE_VIOLATION` on a process metric | `get_variants`, then `run_conformance`, then `get_bottleneck`                                                                            |
| `CAPABILITY_SHORTFALL`                   | `run_spc`, then `run_gage_rr`, then `get_vsm`                                                                                            |
| `CAPABILITY_UNPROVEN`                    | `run_capability_report` with the prospective n, then stop                                                                                |
| `CAPABILITY_ON_UNSTABLE_PROCESS`         | `run_spc`, then stop; capability questions are not answerable yet                                                                        |
| `MSA_UNACCEPTABLE`                       | `create_work_order` for calibration, and mark every open capability and SPC finding on that metric `confidence_degraded_by` this finding |
| `CONFORMANCE_DEVIATION`                  | `get_variants`, then `activity_contribution`, then `get_vsm`                                                                             |
| `REWORK_LOOP`                            | `activity_contribution`, then `run_whatif`                                                                                               |
| `TWIN_DIVERGENCE`                        | `get_fleet_health`, then `run_conformance`                                                                                               |
| `TWIN_CALIBRATION_DRIFT`                 | `get_divergence`, then `run_recalibration`                                                                                               |
| `FORECAST_BIAS_DRIFT`                    | `run_spc` on forecast error, then `compare_variants` by demand segment                                                                   |
| `SOP_VIOLATION`                          | `cite_sop_clause` (E8), then `run_gage_rr` on the CV channel's attribute agreement                                                       |
| `HYPOTHESIS_PAIRING_LOST`                | `get_crn_integrity`, then `run_hypothesis_test` with the unpaired result marked                                                          |

The MSA chain deserves emphasis. When the measurement system fails, the engine walks the open
findings on that metric and degrades their confidence rather than deleting them. Scenario S-LSS-02
tests that behavior, and it is the clearest demonstration in the repo that the engine reasons
like a practitioner rather than a rule evaluator.

#### 5.9.4 Where `query_result_id` comes from

Every finding's evidence carries a `query_result_id` from P1 onward, and E26(f)'s grounding
checker is a Phase 6 deliverable. The id is not waiting on that checker. It is minted by the
query-result recorder in `twinflow-contracts`, which lands at P1 with the first finding, as
`qr-` plus the first 8 hex characters of `blake2b(run_id, producer_id, query_text_or_call_site,
window_start, window_end)`. It is deterministic and content-addressed on the same terms
as every other id here. Phase 6 adds the checker that walks agent answers and asserts every stated
number resolves to a recorded id; it does not add the id. 8 records this as a pulled-forward
dependency.

### 5.10 Alarm management

Designed against ANSI/ISA-18.2, "Management of Alarm Systems for the Process Industries",
published by the International Society of Automation, whose ISA18 committee, "Instrument Signals
and Alarms", covers "the general development, design, installation, and management of alarm
systems in the process industries" (isa.org, retrieved 2026-08-09), and against EEMUA Publication
191, "Alarm systems - a guide to design, management and procurement", first published 1999 and now
in its Fourth Edition (eemua.org, retrieved 2026-08-09). Naming these two documents is the point:
alarm management has a standard, and following it is what the reference architecture paragraph
means by "the way SCADA vendors mean it".

Both documents are sold rather than published openly, and neither body text has been read by this
repository's author. Every number this section takes from them is attributed in place
and carried as a configured default rather than as a validated constant, and OQ-4 records the
verification that remains outstanding. No gate asserts a benchmark value from either document.

#### 5.10.1 Lifecycle

`NEW -> ACTIVE -> {SHELVED, ACKNOWLEDGED} -> RESOLVED -> CLOSED`, with `SUPPRESSED_BY_DESIGN` as a
parallel state and `EXPIRED` for stale entries. Every transition publishes `finding_state_change/v1`
with the actor and the reason. Nothing is deleted.

#### 5.10.2 Rationalization

`alarms/rationalization.yaml`, one record per finding kind, optionally per kind plus subject
class:

```yaml
- id: RAT-SPC-001
  finding_kind: SPC_RULE_VIOLATION
  applies_to: { subject_type: device, metric_class: temperature }
  actionable: true
  consequence: "unplanned conveyor stop, about 45 min line down"
  consequence_category: production # safety | environment | security | production | quality | cost
  time_to_respond_s: 3600
  operator_response: "check the bearing temperature trend, raise a CMMS work order when the trend crosses the alarm limit inside 14 days"
  priority: HIGH # DERIVED, see 5.10.4; a mismatch with the matrix fails CI
  max_finding_severity: HIGH # the ceiling any chart severity_map may set for this kind
  suppression_parents: [DEVICE_OFFLINE, BROKER_UNREACHABLE]
  dedupe_window_s: 900
  shelve_max_s: 28800
  sop_refs: ["SOP-MAINT-004#3.2"]
  owner: "maintenance"
  reviewed_sim_date: "2026-03-01"
  moc_ref: "issue-142"
```

VG-ALM-01, no alarm without a rationalization record: a test enumerates every `FindingKind` member
reachable in code and asserts a matching record exists, that `priority` equals the matrix-derived
value, that `operator_response` is non-empty, and that every chart `severity_map` entry for that
kind is within one ordinal of `max_finding_severity`. A finding kind added without rationalization
fails the build. This is the mechanism that keeps the stream from becoming noise, and it is a
genuinely uncommon thing to find in a repository.

#### 5.10.3 Deduplication

Findings with the same `(kind, subject, rule_id)` inside `dedupe_window_s` collapse into one
`Alarm` with `occurrence_count`, `first_sim_time`, and `last_sim_time`. The individual findings
are still written to the sink; dedupe changes what is presented, never what is recorded. That
invariant, P-ALM-01, is what makes the audit trail survive the alarm layer.

#### 5.10.4 Severity, priority, and the presented rank

Three numbers exist and the earlier draft had no rule for reconciling them. The rule is stated
here.

`Finding.severity` is the finding-level ordinal. It comes from the chart's `severity_map` where
one applies, and from the finding kind's default otherwise. It describes how bad this particular
observation is.

`Alarm.priority` is derived from an ISA-18.2 style matrix of consequence category against time to
respond, declared in `alarms/priority_matrix.yaml`. It describes how bad this kind of event is for
this kind of subject, and it is never hand-assigned.

| Consequence and time to respond | under 5 min | 5 to 30 min | 30 min to 4 h | over 4 h |
|---------------------------------|-------------|-------------|---------------|----------|
| safety or environment           | CRITICAL    | CRITICAL    | HIGH          | HIGH     |
| security                        | CRITICAL    | HIGH        | HIGH          | MEDIUM   |
| quality, customer-affecting     | CRITICAL    | HIGH        | MEDIUM        | LOW      |
| production                      | HIGH        | HIGH        | MEDIUM        | LOW      |
| cost only                       | MEDIUM      | MEDIUM      | LOW           | LOW      |

`Alarm.presented_rank` is `max(severity, priority, floor)` on the shared ordinal scale, and it is
the only one the operator view orders by. Taking the maximum means a chart may raise the rank
of a specific observation above its kind's baseline and may never lower it below.

The `priority` field in the rationalization record is a redundant assertion that CI checks against
the matrix, which catches drift between what someone intended and what the matrix says. A
`severity_map` entry more than one ordinal below its kind's matrix priority is a config validation
error naming both values, so the two mechanisms cannot silently disagree.

Severity floors override downward pressure: a `safety` class finding is never presented below
CRITICAL and a `security` class finding never below HIGH, regardless of dedupe, flood mode, or
shelving state (P-ALM-03).

#### 5.10.5 Chattering, shelving, and suppression

Chattering. ISA-18.2 defines a chattering alarm as one that repeatedly transitions
active-clear-active in a short period. Detection: at least `chatter.transitions` (default 3)
transitions within `chatter.window_s` (default 60). Mitigation: an on-delay, so the condition must
persist `on_delay_s` before annunciating; an off-delay, so the alarm holds `off_delay_s` after
clearing; and a deadband on the underlying metric. A detected chatterer raises `ALARM_CHATTERING`
against itself, which is the engine telling its own operator that its own configuration is wrong.

Shelving. `shelve(alarm_id, reason, until_sim_time, actor)` needs a non-empty reason, caps
duration at `shelve_max_s` (default 8 hours of sim time), and schedules an auto-unshelve on the
sim clock. A shelved alarm that would re-fire at a higher presented rank than when it was shelved
auto-unshelves immediately. Shelved alarms remain queryable and count in the metrics.

The shelve record names the autonomy tier that authorized it and carries a decision register
reference. E5's tier model and E21's register are Phase 6 deliverables and alarm management in
full is P2, so the behavior is phased and the phasing is stated rather than assumed. From P2 the
`autonomy_tier` field carries the tier the local config grants the actor, the tier check runs
against that config, and `decision_register_ref` is null. From P6 the register mints the reference
and the same field carries it. No schema changes at the boundary, which is the reason the field
exists from v1 (4.3).

Suppression by design. `suppression_parents` declares causal relationships: when
`BROKER_UNREACHABLE` is active, the forty `DEVICE_OFFLINE` findings it causes are marked
`SUPPRESSED_BY_DESIGN` with `links.caused_by` set to the parent alarm. The operator sees one alarm
and a count, which is the whole point of the exercise.

Stale alarms. An alarm active longer than `alarms.stale_after_s` (default 24 hours of sim time)
raises `ALARM_STALE`. Stale alarms are the standing evidence that a rationalization record is
wrong.

#### 5.10.6 Flood detection and alarm system metrics

The metrics in this subsection are per operator and per console, so they need a denominator. It is
defined here rather than implied. `operator_hours` for a console over a window is the sum, over
the shifts that overlap the window, of `staffed_operators * overlapping_sim_seconds / 3600`, taken
from the console's `staffed_shifts` in config. A console with no staffed shift in the window has
zero operator hours, and every per-operator rate over that window is reported as null rather than
as a division by zero. `annunciated alarms per operator hour` is the annunciated count divided by
`operator_hours`.

The flood detector runs on a rolling `alarms.flood.window_s` window per console. Entering flood
raises `ALARM_FLOOD`, itself a rationalized finding, switches the presented list to
`collapse_to_priority` mode showing the top N by presented rank with a count of the rest, and
records the flood start. Leaving flood records the duration, the peak rate, and the top
contributors.

Alarm system metrics, published as `alarm_metrics/v1` on a fixed cadence per console and put on
control charts by this same engine:

| Metric                                       | Definition here                                          | Benchmark source                                              |
|----------------------------------------------|----------------------------------------------------------|---------------------------------------------------------------|
| annunciated alarms per operator hour         | annunciated count over `operator_hours`                  | EEMUA 191, value configured, attributed in the report caption |
| percent of time in flood                     | flood minutes over window minutes                        | EEMUA 191, value configured, attributed                       |
| peak alarms in 10 minutes                    | maximum over rolling 10 minute sim windows               | EEMUA 191, value configured, attributed                       |
| chattering alarm index                       | count of alarms meeting 5.10.5's chatter test            | ISA-18.2 definition, attributed                               |
| stale alarm count                            | alarms active beyond `stale_after_s`                     | ISA-18.2, target configured, attributed                       |
| top 10 contributor share                     | share of annunciations from the ten most frequent alarms | ISA-18.2, target configured, attributed                       |
| shelved alarm count and mean shelve duration | from the shelve records                                  | ISA-18.2, attributed                                          |

The benchmark column names where each target comes from and the configured value carries the
attribution into the report. VG-ALM-02 checks the arithmetic of every metric against hand-computed
values on a constructed alarm log with a declared console and a declared shift pattern; it does
not check any benchmark value, because this repository has not read either standard's body text.
OQ-4 states what would change that.

Putting the alarm system's own metrics on control charts is a small recursion with a real payoff:
the engine that judges the plant is judged by the same instrument, and the report shows it.

### 5.11 Process mining

#### 5.11.1 Log construction

`EventLog.from_historian(reader, case_notion, window)` reads `process_event/v1` from the historian
and pivots it into a case-centric log. `case_notion` defaults to `pallet`, which is the source's
"every pallet/lot is a case".

The twin publishes `start` and `complete` lifecycle events for every activity with the seizing
resource, which is what makes 5.11.5's service-against-waiting decomposition possible. Logs where
only `complete` exists fall back to inter-event differences and record
`timing_fidelity: "complete_only"`, so no downstream number silently overstates its precision.

Object-centric logs. Once orders (6a3), returns (6a4), and cross-dock (6a5) exist, one physical
pallet participates in several object types at once and a flat case notion produces the classic
convergence and divergence distortions: a receiving event shared by 30 pallets is duplicated 30
times, and a picking event spanning several orders is arbitrarily assigned. The kit writes
both a flat log per selected case notion, for the README demo and for classical miners, and
an OCEL 2.0 log carrying all object types that exist. OCEL 2.0 is the object-centric event log
format published by the Chair of Process and Data Science at RWTH Aachen University
(ocel-standard.org, retrieved 2026-08-09).

`emit_ocel` defaults to false until 6a5 lands, and config validation rejects a `case_notion` whose
producer does not yet exist with the message "case notion 'order' needs 6a3; available notions
here are pallet, lot, device, batch". The OCEL writer itself lands at P3c and is tested on the
object types that exist then. The recovery benchmark's flattening rows for order, return, and
cross-dock print as "not yet generated" rather than as numbers, so the published table never
carries a distortion figure for a flow the twin cannot yet produce.

#### 5.11.2 Discovery

Miners, all behind one `Miner` protocol so the algorithm choice is swappable and comparable:

| Miner                                       | Purpose                                                                                                                         |
|---------------------------------------------|---------------------------------------------------------------------------------------------------------------------------------|
| Directly-follows graph                      | the baseline everyone starts from, and the input to the frequency and performance views                                         |
| Alpha                                       | the historical baseline, included because its known failure modes on loops and skips are useful teaching material in the report |
| Heuristics miner                            | noise-tolerant, dependency threshold configurable                                                                               |
| Inductive miner, IMf with a noise threshold | the default, and the one that guarantees a sound model, which matters because conformance on an unsound model is meaningless    |

There is one engine and it ships in `twinflow-procmine` under Apache-2.0 (D-14). There is no
engine configuration key, because a default that resolved from whatever happened to be installed
made the discovered model, the deviation list, and every `CONFORMANCE_DEVIATION` finding depend on
the environment rather than on the seed and the config. `twinflow_procmine.__version__` is folded
into the config hash, so the run manifest proves which implementation produced the numbers.

#### 5.11.3 Conformance against known ground truth

The twin exports its designed process as a Petri net through
`export_reference_model(case_notion) -> ProcessModel`. Component 1 implements the export, the type
and its schema are authored here (4.5) and ship in `twinflow-contracts`, and this section consumes
it. Conformance is checked against that, not against a discovered model. This is the source's
differentiator: "conformance is checked against a KNOWN ground-truth process".

The property and gate tiers do not import the twin. They read a checked-in exported reference
model and a checked-in recorded run under `tests/fixtures/reference/`, regenerated by an explicit
`just record-fixtures` job that runs in the container tier where the twin is installed. That is
the same recorded-response pattern D-04 names for any component that cannot be brought inside the
deterministic boundary, and it is what keeps the phase-closing gate tier free of a runtime
dependency the layering forbids at import time.

Token-based replay produces produced, consumed, missing, and remaining tokens, trace fitness, and
log fitness. It is fast, runs on the full log, and drives the live findings.

Alignments compute optimal alignment cost by A star search over the synchronous product net, with
the standard cost function of 1 per log move, 1 per model move on a visible transition, and 0 on a
silent transition, giving per-trace fitness and an exact list of `Deviation` records with
positions.

Two things about that search are stated because leaving either implicit breaks a claim elsewhere.
First, the frontier order is total: nodes are ordered by `(f_cost, g_cost, activity_index,
transition_id)`, where `transition_id` is the model's declared transition ordering, so an
alignment of equal cost is chosen the same way on every machine and in every process. Without it,
VG-PM-01's "exactly K deviations at exactly those positions" would be false whenever two optimal
alignments exist, which is common. Second, the search is bounded by a deterministic node budget,
`SearchBudget.max_expanded_nodes`, never by wall-clock seconds (D-04). A trace that exhausts the
budget is recorded as `alignment_status: "budget_exhausted"` with the budget value, and its
fitness is reported as an interval rather than a point. Bounding by time would make the tape
depend on machine speed.

Alignments are exponential in the worst case, so `TraceSampling` computes alignments for every
distinct variant plus a seeded sample of instances per variant, with the sample size and the
stream name recorded on the result. The sampling stream is `procmine.alignment.sampling`, so the
sampled set is identical across runs of the same seed.

Precision in the ETC-align style, generalization, and simplicity are reported alongside fitness so
nobody reads a fitness of 1.0 from a flower model as success.

Each `Deviation` that survives a configurable frequency floor becomes a `CONFORMANCE_DEVIATION`
finding whose evidence carries the case id, the position, the activity, and the alignment fragment.

#### 5.11.4 Variant analysis and rework

Variants are the distinct activity sequences with frequency, share, mean and median throughput
time, and the cumulative curve that shows how much of the volume the happy path carries.

Variant comparison. `compare_variants(log, a, b, metric, test_fn)` routes into the caller-supplied
hypothesis test, which is `twinflow_lss.hypothesis.compare` when both bricks are installed, so
"variant B is slower than variant A" arrives with a test name, an effect size, a confidence
interval, and a practical-significance verdict. Two bricks, one sentence, and it is the clearest
demonstration of why the LSS engine and the mining kit belong in one repository.

Rework. Self-loops (`A -> A`) and length-k loops are detected on the directly-follows graph and
confirmed at the trace level. The result carries the rework rate per activity, the number of
rework passes per case, and first-pass yield derived as the share of cases with zero rework
passes, which ties to 6a9's first-pass yield and, once 6a17 lands, to a cost per rework pass from
activity-based costing. Loops above the config frequency floor become `REWORK_LOOP` findings.

#### 5.11.5 Cycle-time contribution per activity

For each activity: `service_time` from resource seized to released, `waiting_time` from case ready
to resource seized, `sojourn_time = service + waiting`, occurrences per case, and
`share_of_lead_time`. Waiting time is attributed to the resource that was busy, so the table
answers "what is the constraint" and not merely "what is slow".

The twin independently names a bottleneck from resource utilization (component 1). The mined
waiting-time ranking is a second, independent estimate. When the two disagree by more than
`procmine.bottleneck_disagreement_threshold`, that disagreement is itself a finding,
`BOTTLENECK_DISAGREEMENT`. Two methods agreeing is evidence; two methods disagreeing is a lead.
Either way it is more honest than one number with no cross-check.

#### 5.11.6 The discovery recovery benchmark

The capability no Celonis customer has: the true model is known, so the repository can measure how
well mining recovers it.

`recovery_benchmark(ground_truth, log, miners, noise_levels)` produces a published table:

| Dimension   | Values                                                                           |
|-------------|----------------------------------------------------------------------------------|
| miner       | alpha, heuristics, inductive at several noise thresholds, directly-follows graph |
| log noise   | 0, 1, 5, 10, and 20 percent injected deviations of known type                    |
| case notion | the notions whose producers exist, plus the OCEL flattening variants for those   |
| log size    | 1k, 10k, 100k cases                                                              |

Metrics per cell:

Footprint F1. The causal footprint matrix, with the four relations between activity pairs as
defined in van der Aalst, _Process Mining: Data Science in Action_, 2nd edition, chapter 6, is
computed for the discovered and the ground-truth model, compared cell by cell, and scored as macro
F1.

Cross-fitness. Replay the ground-truth-generated log on the discovered model, and replay a log
generated from the discovered model on the ground-truth model. Both directions, because one alone
hides underfitting.

Edit distance over the process tree where both models have one.

Precision and generalization against the ground-truth log.

At zero noise with a complete log, the inductive miner must recover footprint F1 of exactly 1.0
(VG-PM-02). Everything else is published as a curve rather than as pass or fail, because the
interesting result is the shape of the degradation and pretending otherwise would be dishonest.
The table goes in the README and in the capability report appendix.

### 5.12 Value stream maps

#### 5.12.1 Current state

Inputs: the `ContributionTable` from 5.11.5, `twin_metric/v1` for changeover, uptime, operators,
batch size, and yield, WIP levels from the twin's queue observations, and the activity
classification file. Nothing is entered by hand, which is what makes it "a Lean deliverable that
consultants hand-draw, produced by software from live data".

Per station: cycle time as mean, median, and distribution summary, because a map with only a mean
hides the variation the whole exercise exists to attack; changeover time; uptime percent;
available time per shift; operator count; batch size; first-pass yield; scrap percent.

Between stations: inventory triangles with units on hand and days of supply, and the implied wait
time, `units / demand rate`.

Above the boxes: information flows from the ERP stub (6b) and the schedule, drawn as the arrows a
Lean practitioner expects.

Below the boxes: the timeline ladder. The upper step is value-added time, the lower step is
non-value-added time, and the sums give process time and lead time. Process cycle efficiency is
`process_time / lead_time`, printed as a percentage.

#### 5.12.2 Value classification and waste

`vsm/activity_classification.yaml`, one entry per activity:

```yaml
- activity: scan_inbound
  classification: business_value_added # value_added | business_value_added | non_value_added
  rationale: "needed for lot genealogy and customer traceability, does not transform the product"
  three_question_test:
    { customer_pays: false, transforms: false, right_first_time: true }
- activity: stage_wait
  classification: non_value_added
  waste_type: waiting # 8 wastes
```

Waste types: transport, inventory, motion, waiting, overproduction, overprocessing, defects, and
unused talent, plus `idle_energy` as the extension E7 asks for. Each non-value-added activity
whose share of lead time exceeds `vsm.nva_finding_threshold` raises a `VSM_NVA_EXCESS` finding
carrying its waste type, which puts Lean waste into the same stream as everything else.

The classification is config rather than code, because whether a scan is business-value-added is a
judgement call a reader may legitimately disagree with, and the file is where they argue with it.

#### 5.12.3 Future state

Generated from an accepted what-if (`whatif_result/v1`), never hand-drawn:

1. Apply the what-if's config delta.
2. Re-run the twin on the same run seed and replication index. Common random numbers make the
   comparison paired when the arms draw the same values from every shared stream, and the runner's
   `crn_integrity` record says whether they did (5.7.1). A change that alters the number of draws
   is still run and still compared; the comparison is reported as unpaired and the loss of power
   is named.
3. Rebuild the contribution table and the map.
4. `diff(current, future)` produces which stations changed cycle time, which inventory triangles
   shrank, the new lead time, the new process cycle efficiency, and the delta on each.
5. Annotate kaizen bursts on the changed elements, one per applied change, labeled with the change
   description.
6. Attach the statistical verdict. Every claimed improvement in the diff carries the `TestResult`
   from 5.7 for that metric, as its published schema (4.5): test name, p-value adjusted where a
   family exists, effect size with interval, and the practical-significance verdict. A future-state
   map whose numbers carry confidence intervals is a document no consultant currently produces.

#### 5.12.4 Rendering

`render_svg` uses `twinflow_artifact.svg` with a fixed layout algorithm: stations on a horizontal
band at fixed pitch, triangles between them, ladder below, information flows above. No
force-directed layout, no randomness, no external layout library, so the output is byte-stable
under C1 and asserted by hash (VG-VSM-03).

`render_table` writes a Markdown table with every number in the map, always alongside the SVG.
This is the C12 text equivalent and it is also what makes the map diffable in a pull request.

The SVG carries `<title>` and `<desc>` on every group, `role="img"`, and a linked
`aria-describedby` pointing at the table, so the accessibility requirement is met at the artifact
level rather than only in the dashboard.

`vsm.json` is the machine-readable form and the golden-file target.

### 5.13 The capability report

One command, per the source: "one command produces a Minitab-style HTML report for any time
window".

```
just report FROM=<sim-time> TO=<sim-time> PROFILE=<facility profile>
# expands to
twinflow-lss report --from <t> --to <t> --profile mid-market-3pl --out artifacts/capability-report.html
```

A single self-contained HTML file: inline CSS, inline SVG charts, no external assets, no build
step, matching component 8's constraint and making the file safe to attach to an email or to serve
from GitHub Pages for E1.

Every chart renders through `twinflow_artifact.svg`. The default install produces the complete
report with no optional extra, which is what D-10 asks for and what the source's "the artifact a
hiring manager actually opens" needs. There is no font resolution step, no hash salt, and no
embedded timestamp, so the determinism problem the earlier draft solved by configuring matplotlib
does not arise on the default path. The `[matplotlib]` extra offers an alternative renderer for
readers who want one; its output is excluded from the byte-identity gate and the report records
which renderer produced it.

Sections, in Minitab's order because the layout is the recognition cue:

1. Header: process name, metric, window in sim time with the run's wall-clock mapping read from
   the provenance sidecar, spec limits with their `derivation` text, sample size, run seed, config
   hash, twinflow version, and the gate run id that was green when the report was produced.
2. Capability histogram: the sample with LSL, USL, and target lines, the fitted within-curve and
   overall-curve overlaid, and the transformation used where there was one.
3. Capability indices table: Cp, CPL, CPU, Cpk, and Cpm on the left as within or potential; Pp,
   PPL, PPU, and Ppk on the right as overall; each with its confidence interval.
4. Performance table: PPM or DPMO rows `< LSL`, `> USL`, and `Total`, columns `Observed`,
   `Expected Within`, and `Expected Overall`, plus the sigma levels with the shift convention
   named in the caption.
5. Control charts: the metric's charts for the window, one per stream present, with violations
   marked by rule number and a legend giving the rule text rather than only the number.
6. Assumption panel: normality test and statistic, transformation, stability verdict with the rule
   ids that decided it, and the MSA summary for the measurement system behind the metric, with an
   explicit banner when the capability numbers are degraded by an unstable process or an
   unacceptable gauge.
7. Findings for the window: a table grouped by presented rank, each row linking to its evidence and
   its suggested next tool chain.
8. Alarm system health: the 5.10.6 metrics per console against their configured benchmarks, with
   each benchmark's source named in the caption.
9. Twin divergence: the residual chart, the calibration test result, and the divergence findings
   for the window.
10. Process mining summary: fitness, precision, top variants, rework rate, activity contribution
    ranking.
11. Value stream map: the current-state SVG inline plus the text-equivalent table, and the
    future-state diff where one exists for the window.
12. Validation appendix: the gate table with every gate's id, statistic, reference class,
    reference, and status, plus the generated claim block of 7.6 and the list of any deferred
    gates named in full.
13. SIPOC and swimlane views: each SVG inline plus its text-equivalent table (5.15).
14. What-if ranking: the Pugh table with the stoplight class per candidate, each score linking
    to its `TestResult` (5.16).

Sections 10 and 11 need `twinflow-procmine` and `twinflow-vsm`, which land at P3c, and section 9
needs the divergence spec, which lands with component 6. Section 13 lands at P3c with
`twinflow-vsm`, and section 14 at P3d with the ranking module. The report does not silently omit
a section it cannot produce. `report.include` defaults exclude `procmine`, `vsm`,
`sipoc_swimlane`, `ranking`, and `divergence` until their phase, and any section named in
`report.include` but unavailable renders as a named placeholder block reading "not available in
this build: twinflow-procmine is not installed". The golden file stays stable across phases and a
missing section is visible rather than inferred.

Accessibility (C12): semantic headings, every chart followed by its data table, severity encoded
by shape and label in addition to color, a color-blind-safe palette, and a print stylesheet.
`test_severity_renders_shape_and_label` (4.2) runs against the generated file.

### 5.14 Determinism and the simulation seam

Concrete obligations this section carries under the locked dual-mode architecture.

Constructors take a `Clock` and named stream handles. No module-level RNG, no `time.time()`, no
`datetime.now()`. D-02 lists the four places a wall clock may be read, and none of them is in
these five packages: the provenance sidecar writer, the paced-clock pacer, the observability
exporter, and operator-facing log lines all sit outside. The CI lint applies here with no escape
hatches granted.

Every stochastic operation (bootstrap intervals, alignment trace sampling, Monte Carlo coverage
checks, permutation tests) draws from a named stream through `twinflow-rng`, so adding a bootstrap
in one place cannot shift the numbers in another. Stream names used by this section:
`lss.hypothesis.bootstrap`, `lss.hypothesis.permutation`, `lss.capability.coverage`,
`lss.msa.study_generator`, `procmine.alignment.sampling`, `procmine.benchmark.noise`. Each is
declared in the stream registry, and section F.4 of the variability section's stream-append test
is the standing proof that adding one does not move the others.

Iteration order is deterministic everywhere (D-03). No collection whose iteration order can reach
an event, a hash, or a control decision is a `set`. Where a set is the right semantic type it is
iterated as `sorted(s)` with the reason in a comment. Dictionaries are insertion-ordered in the
supported Python versions and are permitted, and any dictionary built from a set or from
concurrent inserts is sorted before use. Ties in ranking break on a stable secondary key, usually
`finding_id`. The A star frontier order of 5.11.3 is the one place where this rule has a
consequence a reader would otherwise miss.

Floating-point reproducibility. There are no multi-threaded reductions in the statistical core.
BLAS thread count is pinned to 1 at process start for every run rather than only for the gate job,
because C1 applies to every run and a production run on a machine with a different thread count
could otherwise produce different low-order bits from the run the gates certified. The pinned
value is recorded in the provenance sidecar. Summations use pairwise or Neumaier compensation
where the certified numerical gates demand it.

The online and batch paths agree to a relative tolerance of 1e-12 (P-NUM-01), which forces
Welford-style incremental variance rather than the naive sum of squares that the NumAcc4 dataset
exists to punish.

The determinism claim is two-tier and the README states both rather than the stronger one alone
(D-05).

| Tier             | Guarantee                                                             | Gate                                                                                                                                          |
|------------------|-----------------------------------------------------------------------|-----------------------------------------------------------------------------------------------------------------------------------------------|
| Byte-identical   | Same run seed, same config, same platform, same pinned dependency set | VG-DET-01, hash equality on findings JSONL, its gzip, the report, the map SVG, and the map JSON, each after the declared normalization filter |
| Value-equivalent | Same run seed and config across platforms                             | VG-DET-02, identical business events, continuous fields agreeing within a tolerance derived from measured divergence                          |

VG-DET-02 reports the observed maximum divergence rather than asserting a number chosen in
advance. When the observed divergence exceeds the recorded tolerance, the gate fails and names
which of the two explanations applies: the tolerance was wrong, or a real defect exists. The
tolerance lives in `validation/cross_platform_tolerance.json` with the platform pair, the date, and
the run that produced it.

The reason the weaker cross-platform claim is the honest one: the distributions sample floats and
round to ticks, which makes the tape sensitive to one-unit-in-last-place differences in `log`,
`exp`, and `erfinv` across platforms and SIMD dispatch. A cross-platform byte-identity claim
cannot be supported and is not made.

### 5.15 SIPOC and swimlane views

Addition beyond the source, 1.5. Two more drawings that consultants hand-draw in the Define phase, generated
here from data the engine already has. Both live in `twinflow-vsm`, both render through
`twinflow_artifact.svg` with a fixed layout, and every rule of 5.14 binds them.

#### 5.15.1 SIPOC

`build_sipoc(model, contribution, topology, cfg) -> Sipoc`, entities in 3.9.

The process column is mined, never hand-drawn. The discovered model of 5.11.2 is rolled up to
high-level steps through `vsm/sipoc.yaml`, a map from activity to step. The map is config for the
same reason the activity classification of 5.12.2 is config: the roll-up is a judgment call a
reader may argue with, and the file is where they argue. A SIPOC wants few steps, and how few is
the map author's call.

The input and output columns derive from the twin's station graph where a material flow is
recorded, and from `vsm/sipoc.yaml` where one is not. The supplier and customer columns are
declared in the same file, sourced from the ERP stub's supplier list (6b) and the demand model.
Every cell carries `provenance: mined` or `provenance: declared`, so a reader sees which columns
the data earned and which the config asserted. A SIPOC that hides that difference would
overclaim, and overclaiming is what the validation registry exists to prevent.

#### 5.15.2 Swimlane

`build_swimlane(log, model, cfg) -> Swimlane`, entities in 3.9.

Lanes are the twin's resource pools, in the declared pool order. Each activity sits in the lane
of the resource that executed it in the event log, read from the `resource` column of 3.7. Edges
follow the mined control flow. An edge whose source and target lanes differ is a handoff, and
the handoff count per lane pair prints on the map, because handoffs are where a Lean reader
looks first. An activity executed by more than one pool in the window is drawn once per pool
with its occurrence share, never merged, so the map cannot hide a split responsibility.

#### 5.15.3 Rendering and placement

`render_sipoc_svg`, `render_swimlane_svg`, and their table twins follow 5.12.4 exactly: fixed
pitch, no layout engine, byte-stable output, `<title>` and `<desc>` on every group, and a
Markdown table beside every SVG (C12). `sipoc.json` and `swimlane.json` are the golden-file
targets. The capability report gains section 13 behind `report.include`, excluded by default
until P3c under the placeholder rule of 5.13.

Neither view invents data. The SIPOC's declared cells come from config, the swimlane's lanes
come from the twin, and both artifacts name the mined model id, the config hash, and the run
seed in `provenance` (D-01). Gates: VG-SIP-01, VG-SWM-01, VG-SWM-02.

### 5.16 What-if ranking

Addition beyond the source, 1.5. The Improve-phase step between many candidate what-ifs and the one
future-state map of 5.12.3: a Pugh matrix with the current state as the datum, and a stoplight
class per candidate. `rank_whatifs` lives in `twinflow_lss.ranking` and returns a
`WhatIfRanking` (3.9), published as `/schemas/whatif_ranking/v1.json`. Candidates arrive as
`whatif_result/v1` (4.7), one per competing change, each carrying the baseline and treatment
sample references the hypothesis layer reads.

#### 5.16.1 Scoring

The datum is the current state. The criteria are metric ids from `ranking/criteria.yaml`, each
resolving in the metric registry (6.6) and each carrying a practical-significance margin under
rule 7 of 6.7. Per candidate and criterion, the score is `+1` when the candidate's `TestResult`
shows an improvement that is both statistically and practically significant, `-1` when it shows
a worsening under the same two bars, and `0` otherwise, including every case where the
assumption checker refused the test. The family for the 5.7.5 adjustment is every
candidate-criterion pair in the call, so shopping ten what-ifs does not buy ten uncorrected
chances at significance.

The score is a function of `TestResult` verdicts the hypothesis layer already produces, so the
ranking adds no new statistics and no new ways to be wrong about significance. There are no
weights. A weighted sum invites tuning the weights until a favorite wins; an unweighted Pugh
count keeps the argument in the criteria list, which is config a reviewer can read.

#### 5.16.2 Stoplight class

The stoplight is the classroom device from the Ahire and Jensen map, kept because it
communicates: impact against cost on one card. The impact band derives from the net score
(`positive`, `zero`, `negative`). The cost class is declared per what-if in its config (`low`,
`medium`, `high`), because cost is an input a simulation cannot measure. `ranking/criteria.yaml`
declares the full matrix from `(impact_band, cost_class)` to `green`, `yellow`, or `red`, and
rule 18 of 6.7 refuses a matrix with a hole. A candidate with no criterion scoring `+1` can
never classify `green`, whatever its declared cost (VG-RNK-03).

#### 5.16.3 Order and determinism

`order` sorts by `net_score` descending, ties broken by `whatif_id` ascending, stated here so
the tie-break is a contract rather than an accident (D-03). The ranking is a pure function of
its inputs and the config hash, reads no wall clock (D-01), and is content-addressed the way
findings are (5.9.2). The report gains section 14 behind `report.include`, excluded by default
until P3d. The agent tool is `rank_whatifs` (2.7), and the ranking a reader sees is the ranking
the gates checked, because both come from the same callable under `@val_gate` (7.5.4). Gates:
VG-RNK-01, VG-RNK-02, VG-RNK-03.

---

## 6. Configuration

### 6.1 `facility.yaml`, `lss:` block

```yaml
lss:
  spc:
    default_rule_sets: [western_electric, nelson] # list[enum], non-empty
    selection:
      xbar_s_min_n: 9 # int, 2..25
    baseline:
      min_subgroups: 25 # int >= 10
      min_points_individuals: 100 # int >= 30
    limit_policy: frozen # frozen | rolling | rebaseline_on_change
    rolling_window_subgroups: 50 # int, needed only when limit_policy == rolling
    small_shift_detection: true # bool, adds an EWMA companion chart
    charts:
      - chart_id: dock3_scan_cycle_time # str, unique, ^[a-z0-9_]+$
        metric: station.scan.cycle_time_s # MetricId, must resolve in the metric registry
        subject: "twinflow/site-a/receiving/line-1/portal-3"
        stream: observed # observed | predicted | residual
        chart: auto # auto | i_mr | xbar_r | xbar_s | p | np | c | u | ewma | cusum | t2
        data_type: continuous # continuous | binary | count
        subgroup: { strategy: time_window, window_s: 900, n: 5 }
        ewma: { lambda: 0.2, L: 2.7 } # 0 < lambda <= 1 ; L > 0
        cusum: { k: 0.5, h: 5.0 } # k, h > 0
        rule_sets: [nelson]
        severity_map: { "nelson.1": HIGH, "nelson.2": MEDIUM }
  capability:
    sigma_within_method: rbar_d2 # rbar_d2 | sbar_c4 | mr_d2 | pooled_sd
    sigma_shift: 1.5 # float >= 0, applied only to sigma_level_shifted
    cpk_target: 1.33 # float > 0
    ppk_target: 1.33
    min_n: 30 # int >= 10
    require_stability: true # bool
    stability_rules: [we.1, we.2, nelson.1, nelson.2] # rule ids, non-empty
    normality: { test: anderson_darling, alpha: 0.05, on_fail: box_cox }
    ci_level: 0.95 # 0 < x < 1
  msa:
    method: anova # anova | average_range
    error_term: interaction # interaction | repeatability
    interaction_pool_alpha: 0.25 # 0 < x < 1
    study_var_multiplier: 6.0 # 6.0 | 5.15
    rescale_thresholds: true # bool, see 5.6.1
    variance_component_ci: modified_large_sample # method name recorded on the result
    thresholds: { grr_pct_acceptable: 10, grr_pct_marginal: 30, ndc_min: 5 }
  hypothesis:
    alpha: 0.05
    alpha_assumption: 0.05
    prefer_welch: true
    normality_test: anderson_darling # anderson_darling | shapiro_wilk
    equal_variance_test: levene # levene | bartlett
    independence:
      { check: true, method: batch_means, rho_threshold: 0.1, min_batches: 30 }
    multiplicity: bh # bh | bonferroni | none
    report_observed_power: false # must be false, see 5.7.3
    power_target: 0.80
    practical_significance:
      station.scan.cycle_time_s: { min_meaningful_difference: 0.5, unit: s }
      line.throughput_pph: { min_meaningful_difference: 20.0, unit: pallets/h }
    equivalence_margin:
      line.throughput_pph: 20.0
  divergence:
    specs: divergence/specs.yaml # path, one DivergenceSpec per metric
    baseline_window: { start_sim_time: 0.0, end_sim_time: 172800.0 }
    default_residual_method: standardized # difference | ratio | standardized | pit
  findings:
    sinks: [jsonl] # delta needs the [delta] extra of twinflow-findings
    jsonl_path: artifacts/findings/{run_id}.jsonl.gz
    gzip: { mtime: 0, write_filename: false } # both required for byte stability
    next_tool_policy: findings/next_tool_policy.yaml
    severity_floors: { safety: CRITICAL, security: HIGH }
  alarms:
    rationalization: alarms/rationalization.yaml
    priority_matrix: alarms/priority_matrix.yaml
    consoles: alarms/consoles.yaml
    dedupe_window_s: 900
    stale_after_s: 86400
    chatter: { transitions: 3, window_s: 60, on_delay_s: 5, off_delay_s: 30 }
    shelving:
      { max_duration_s: 28800, require_reason: true, auto_unshelve: true }
    flood:
      {
        window_s: 600,
        threshold: 10,
        target_avg: 1,
        mode: collapse_to_priority,
        top_n: 10,
        benchmark_source: "EEMUA 191, edition and clause to be confirmed, OQ-4",
      }
  report:
    template: minitab_like
    renderer: artifact # artifact | matplotlib
    output_dir: artifacts/
    include:
      [histogram, indices, ppm, charts, assumptions, findings, alarms, validation]
    include_when_available: [divergence, procmine, vsm]
specs:
  station.scan.cycle_time_s:
    lsl: null
    usl: 12.0
    target: 8.0
    unit: s
    derivation: "takt at 720 pallets per 8h shift plus 20 percent allowance"
```

### 6.2 `alarms/consoles.yaml`

```yaml
consoles:
  - console_id: CON-RECEIVING
    name: "Receiving and dock"
    subject_patterns:
      - "twinflow/site-a/receiving/**"
      - "twinflow/site-a/yard/**"
    staffed_shifts:
      - { days: [mon, tue, wed, thu, fri], start: "06:00", end: "14:00", operators: 2 }
      - { days: [mon, tue, wed, thu, fri], start: "14:00", end: "22:00", operators: 1 }
    default: false
  - console_id: CON-PLANT
    name: "Plant-wide"
    subject_patterns: ["**"]
    staffed_shifts:
      - { days: [mon, tue, wed, thu, fri, sat, sun], start: "00:00", end: "24:00", operators: 1 }
    default: true
```

Exactly one console carries `default: true`, and config validation fails when zero or more than
one does. Shift times are sim-calendar times resolved through the run's sim clock, never through a
wall clock.

### 6.3 `procmine:` block

```yaml
procmine:
  case_notion: pallet # pallet | lot | order | return | device | batch
  emit_ocel: false # true once 6a5 lands, see 5.11.1
  miner: inductive # dfg | alpha | heuristics | inductive
  inductive: { noise_threshold: 0.2 } # 0 <= x <= 1
  heuristics: { dependency_threshold: 0.5, and_threshold: 0.65 }
  conformance:
    method: [token_replay, alignment]
    alignment_sampling:
      { per_variant: 20, max_traces: 5000, stream: procmine.alignment.sampling }
    alignment_budget: { max_expanded_nodes: 2000000 } # deterministic, never seconds
    deviation_frequency_floor: 0.01
  rework: { min_loop_frequency: 0.005 }
  bottleneck_disagreement_threshold: 0.15
  benchmark:
    noise_levels: [0.0, 0.01, 0.05, 0.10, 0.20]
    log_sizes: [1000, 10000, 100000]
    noise_stream: procmine.benchmark.noise
```

### 6.4 `vsm:` block

```yaml
vsm:
  classification: vsm/activity_classification.yaml
  nva_finding_threshold: 0.10 # share of lead time
  demand_rate_source: twin # twin | forecast
  shift_available_time_s: 27000
  render: { pitch_px: 220, ladder_height_px: 80, theme: print_safe }
  sipoc: vsm/sipoc.yaml # roll-up map plus declared columns, 5.15.1
  swimlane: { lane_source: resource_pool } # 5.15.2
```

### 6.5 Standalone files

| File                                       | Schema                                            | Notes                                                 |
|--------------------------------------------|---------------------------------------------------|-------------------------------------------------------|
| `alarms/rationalization.yaml`              | `/schemas/config/rationalization.v1.json`         | one record per finding kind; CI enforces completeness |
| `alarms/priority_matrix.yaml`              | `/schemas/config/priority_matrix.v1.json`         | consequence by time-to-respond grid                   |
| `alarms/consoles.yaml`                     | `/schemas/config/consoles.v1.json`                | console patterns and staffed shifts                   |
| `findings/next_tool_policy.yaml`           | `/schemas/config/next_tool_policy.v1.json`        | tool chains with optional evidence predicates         |
| `vsm/activity_classification.yaml`         | `/schemas/config/activity_classification.v1.json` | value-added classification plus waste type            |
| `vsm/sipoc.yaml`                           | `/schemas/config/sipoc.v1.json`                   | the step roll-up map plus declared SIPOC columns      |
| `ranking/criteria.yaml`                    | `/schemas/config/ranking_criteria.v1.json`        | criteria, cost classes, and the stoplight matrix      |
| `divergence/specs.yaml`                    | `/schemas/divergence_spec/v1.json`                | one spec per monitored metric                         |
| `validation/valgates.yaml`                 | `/schemas/valgate/v1.json`                        | the gate registry                                     |
| `validation/budget.json`                   | `/schemas/config/gate_budget.v1.json`             | recorded per-gate cost, see 7.7                       |
| `validation/cross_platform_tolerance.json` | `/schemas/config/xplat_tolerance.v1.json`         | measured divergence per platform pair                 |

### 6.6 The metric registry, and why it lands at P0

Every `spc.charts[].metric` must resolve to a metric id. The governed semantic metric layer of
E26(b) is a Phase 6 deliverable, and the chart loader enforces this rule from P2, so the earlier
draft's rule was unsatisfiable the first time it ran.

The rule is kept and the dependency is resequenced. The layer splits in two. The metric registry
is a flat, versioned list of metric ids with unit, data type, and owning subsystem, authored in
`metrics/registry.yaml` and landing at P0 with the other contracts. The governed semantic layer of
E26(b), which adds lineage, certified definitions, and the query surface, is built on that
registry at P6 and adds no new identifier. From P2 the chart loader resolves against the registry
and fails on an unknown metric id, which is the rule as written, running against something that
exists. 8 records the resequencing.

### 6.7 Cross-file validation rules

Beyond per-field types, the loader enforces:

1. Every `spc.charts[].metric` resolves in the metric registry (6.6).
2. Every metric with an `spc.charts` entry that also appears in `capability` has `specs` limits.
3. Every `FindingKind` reachable in code has a rationalization record (VG-ALM-01).
4. Every rationalization record's `priority` equals the matrix-derived priority.
5. No `severity_map` entry is more than one ordinal below its kind's matrix priority, and none
   exceeds the record's `max_finding_severity` (5.10.4).
6. Every activity in the twin's station graph has a classification entry.
7. `hypothesis.practical_significance` covers every metric used in a what-if comparison.
8. `chart_id` values are unique across the file.
9. `report_observed_power` is `false`; setting it true is a validation error carrying the Hoenig
   and Heisey citation in the message.
10. `capability.stability_rules` is non-empty and every entry is a rule id in a rule set the
    metric's chart enables.
11. Exactly one console is `default: true`, and every console pattern is a valid UNS glob.
12. A chart with `stream: residual` names a metric that has a `DivergenceSpec` or inherits the
    default, and names a `divergence.baseline_window`.
13. `case_notion` names a notion whose producer exists in the current phase (5.11.1).
14. `findings.sinks` includes `delta` only when `deltalake` is importable, and the error names the
    extra to install.
15. `study_var_multiplier` is 5.15 only when `rescale_thresholds` is true, else the diagnostic of
    5.6.1 fires.
16. Every activity in `vsm/sipoc.yaml`'s roll-up map exists in the twin's station graph, and
    every station-graph activity maps to exactly one SIPOC step.
17. Every criterion in `ranking/criteria.yaml` resolves in the metric registry and has an entry
    in `hypothesis.practical_significance` (rule 7).
18. The stoplight matrix in `ranking/criteria.yaml` covers every `(impact_band, cost_class)`
    pair exactly once.

### 6.8 Error reporting (C5)

Config is parsed with `ruamel.yaml` in round-trip mode so every node keeps its line and column.
Validation errors are formatted as:

```
facility.yaml:41:9: error: lss.spc.charts[2].chart: "xbar-r" is not a valid chart type
    valid values: auto, i_mr, xbar_r, xbar_s, p, np, c, u, ewma, cusum, t2
    did you mean: xbar_r
    see: docs/CONFIGURING.md#control-charts

facility.yaml:47:11: error: lss.spc.charts[3]: chart "xbar_r" needs 2 <= subgroup.n <= 8, got 12
    the selection tree would choose xbar_s for n=12
    set spc.selection.xbar_s_min_n to override the boundary

facility.yaml:88:5: error: lss.msa.study_var_multiplier is 5.15 with rescale_thresholds false
    the 10 and 30 percent verdict thresholds are defined on the 6.0 basis
    set rescale_thresholds: true, or set study_var_multiplier: 6.0
```

Suggestions come from `difflib.get_close_matches` over the valid key or value set. All errors in a
file are collected and reported together, never one per run. `twinflow-lss validate-config` exits
non-zero on any error and is wired into `just validate` and the pre-commit hook. A `--dry-run`
mode loads every config, builds every chart spec, resolves every metric, and reports what would
run without touching the historian.

---

## 7. Testing

Five tiers with runtime budgets (C4). All tiers run on `just test`; CI runs them as separate jobs
with path filtering (C10). 7.7 derives each budget from recorded cost rather than asserting one.

### 7.1 Unit tests

Per-function tests over hand-computed fixtures. The ones that are easy to get wrong, and are
explicitly required for that reason:

- Each of the 12 rules, 4 Western Electric and 8 Nelson, has a minimal firing fixture and a
  minimal near-miss fixture that comes one point short of firing.
- Tie handling in N3 and N4 on constant and equal-adjacent series.
- `OpenViolation` lifecycle: a violation that opens, extends over 400 points, and closes has one
  evidence window covering all 400, and one still open at the end of the series is finalised with
  `open: true`.
- Variable-subgroup p-chart limits are per point rather than a single band.
- LCL clamping to zero on R, s, p, c, and u charts, with `clamped` set.
- One-sided spec limits produce `cp = None` rather than a fabricated value.
- Unbalanced Gage R and R rejects the average-and-range method with a clear error.
- Negative variance component clamping is reported, and `variance_closure_defect` is populated.
- `%Tolerance` and `%StudyVar` use the same multiplier, and selecting 5.15 rescales the verdict
  thresholds.
- Chart selection tree: one case per leaf, including the multivariate route and each stream.
- Pairing: an observed point never pairs with two predicted points, and the three unmatched counts
  are reported.
- `ConsoleAssignment` resolves in declared pattern order and falls through to the default console.
- `operator_hours` over a window with no staffed shift is zero and the per-operator rate is null.
- `test_severity_renders_shape_and_label` on a generated report fixture.
- `test_normalize_is_not_lossy` on the artifact filter.
- Config error formatting: line, column, suggestion, and doc link present.

### 7.2 Property-based invariants

Named invariants, each a `@given` test with a seeded, reproducible `derandomize` profile in CI.

| Id       | Invariant                                                                                                                                                                                                                                           |
|----------|-----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| P-NUM-01 | Online and batch agreement: for any finite series, the streaming mean, variance, EWMA, and control limits equal the batch computation to a relative tolerance of 1e-12                                                                              |
| P-SPC-01 | Affine equivariance: for `a > 0` and any `b`, the chart fitted on `a*x + b` has limits `a*L + b` and the identical set of violations                                                                                                                |
| P-SPC-02 | Rule-1 invariance under permutation, for order-independent estimators only: with `sbar_c4` or `pooled_sd` on fixed subgroups, the set of point values flagged by rule 1 does not change when the series is permuted                                 |
| P-SPC-03 | Rule-1 invariance under permutation given a frozen fit: for any estimator, including `mr_d2`, permuting the series after the `ChartFit` is frozen leaves the set of flagged values unchanged                                                        |
| P-SPC-04 | Limit monotonicity: multiplying a series' deviations from its mean by `k > 1` never narrows the control limits for the same estimator                                                                                                               |
| P-SPC-05 | Limit ordering: `ucl > cl > lcl` for every chart, or a clamp is recorded                                                                                                                                                                            |
| P-SPC-06 | Constants monotonicity: `d2(n)` and `c4(n)` are strictly increasing in `n` over 2 to 25, and `c4(n) < 1` with `c4(n)` approaching 1                                                                                                                 |
| P-SPC-07 | Merged violations: overlapping firings of the same rule produce one violation whose evidence window is the union, the union covers every constituent point, and the online and batch paths produce the same union on a 10,000-point sustained shift |
| P-CAP-01 | `cpk <= cp`, with equality if and only if the mean equals the spec midpoint, to tolerance                                                                                                                                                           |
| P-CAP-02 | Ratio identity: `cp / pp` and `sigma_overall / sigma_within` agree to a relative tolerance of 1e-12                                                                                                                                                 |
| P-CAP-03 | Unit invariance: scaling the sample, the spec limits, and the target by the same positive factor leaves every index unchanged to a relative tolerance of 1e-12                                                                                      |
| P-CAP-04 | `dpmo_expected` is monotone decreasing in `z_bench`                                                                                                                                                                                                 |
| P-CAP-05 | Band exclusivity: exactly one of capable, `CAPABILITY_UNPROVEN`, and `CAPABILITY_SHORTFALL` holds for any interval and target                                                                                                                       |
| P-MSA-01 | Variance closure: with no clamped component, the relative closure residual against `tv_from_total_ss` is at most 1e-10; with a clamped component, `variance_closure_defect` is populated and the finding is raised                                  |
| P-MSA-02 | Label invariance: permuting operator or part labels leaves every component unchanged                                                                                                                                                                |
| P-MSA-03 | Replication stability: duplicating the entire study leaves each component inside its original `variance_component_ci`                                                                                                                               |
| P-HYP-01 | Selection determinism: identical data, config, and `crn_integrity` always select the identical test                                                                                                                                                 |
| P-HYP-02 | One-sided shift monotonicity: adding `delta > 0` to every value in one group never increases the one-sided p-value in the shift direction                                                                                                           |
| P-HYP-03 | Two-sided shape: the two-sided p-value of a location test is quasi-convex in `delta`                                                                                                                                                                |
| P-HYP-04 | Rank invariance: Mann-Whitney's p-value does not change under any strictly increasing transform of all values                                                                                                                                       |
| P-HYP-05 | Paired consistency: the paired t on `(a, b)` equals the one-sample t on `a - b` to a relative tolerance of 1e-12                                                                                                                                    |
| P-HYP-06 | Order symmetry: swapping group order negates the effect size and leaves abs(statistic) and the two-sided p unchanged                                                                                                                                |
| P-HYP-07 | Pairing honesty: when `crn_integrity` reports unequal draw counts on any shared stream, the selected test is an independent-samples test and `HYPOTHESIS_PAIRING_LOST` is raised                                                                    |
| P-DIV-01 | Residual centering: a paired series whose predicted equals its observed produces residuals that are exactly zero under `difference` and exactly one under `ratio`                                                                                   |
| P-DIV-02 | Magnitude gate: with `magnitude` set above the injected shift, no `TWIN_DIVERGENCE` is raised even when the residual chart fires                                                                                                                    |
| P-FND-01 | Id stability: identical `(kind, subject, rule_id, window start, run_id)` yields an identical `finding_id`, and any change yields a different one                                                                                                    |
| P-FND-02 | Round-trip: `Finding` to JSON to `Finding` is the identity and the JSON validates against the schema                                                                                                                                                |
| P-ALM-01 | Conservation: emitted equals surfaced plus deduped plus suppressed plus shelved, and every raised finding is retrievable from the sink regardless of alarm state                                                                                    |
| P-ALM-02 | Shelve bound: no alarm remains shelved past `max_duration_s` of sim time, and auto-unshelve fires at the exact deadline                                                                                                                             |
| P-ALM-03 | Floor: no finding in a floored class is ever presented below its floor, in any alarm mode                                                                                                                                                           |
| P-ALM-04 | Rank composition: `presented_rank` equals `max(severity, priority, floor)` for every alarm                                                                                                                                                          |
| P-PM-01  | Contribution conservation: per-activity sojourn shares sum to 1.0 to a relative tolerance of 1e-9 over a complete case set                                                                                                                          |
| P-PM-02  | Variant partition: variants partition the case set exactly, with no case in two variants and none missing                                                                                                                                           |
| P-PM-03  | Clean-log fitness: the checked-in fixture log generated with deviations disabled replays on the checked-in exported reference model with fitness exactly 1.0                                                                                        |
| P-PM-04  | Alignment determinism: two runs of the same alignment on the same trace return the same deviation positions, and the frontier order is total                                                                                                        |
| P-VSM-01 | Ladder conservation: value-added plus business-value-added plus non-value-added plus triangle waits equals `lead_time` to a relative tolerance of 1e-9                                                                                              |
| P-VSM-02 | `0 <= process_cycle_efficiency <= 1`                                                                                                                                                                                                                |
| P-VSM-03 | Little's Law: at steady state, WIP and `throughput * lead_time` agree within the interval VG-VSM-02 measures                                                                                                                                        |
| P-REP-01 | Report determinism: the same window, run seed, and config produce byte-identical HTML and SVG after the declared normalization filter, on the same platform and pinned dependency set                                                               |

P-SPC-02 was restricted and P-SPC-03 added because the earlier single property was false for the
first chart the source names. The moving-range mean is not invariant under permutation, so
permuting an I-MR series changes MRbar, hence sigma, hence the limits, hence the flagged set. The
invariant that matters in phase II is the one P-SPC-03 states: with the fit frozen, which is what
`frozen` limit policy means, rule 1 depends only on the multiset of values.

P-HYP-02 was restricted for the same reason. Adding a constant to one group moves its mean toward
the other group's when it started below, so the two-sided p-value rises until the means cross and
falls after. The one-sided statement is true and computable; the two-sided shape statement is
P-HYP-03.

### 7.3 Seeded end-to-end scenarios

Each runs the sim in simulation mode with a fixed run seed and asserts an outcome chain rather
than a single number.

S-LSS-01, bearing drift. Inject a linear temperature drift on conveyor motor 2 at sim-time T.
Assert that the EWMA companion chart fires before the Shewhart chart, that Nelson rule 3 fires
within the expected point range, that the finding's evidence window covers the drift onset, that
the alarm manager collapses the 40 repeats into one alarm with `occurrence_count == 41`, that the
`suggested_next_tool` chain leads to `get_pdm_trend`, and that the CMMS work order (6b) carries
the twin-quantified cost of deferral.

S-LSS-02, the gauge eats the tolerance. Configure an RFID portal with inflated repeatability
variance. Assert that capability drops, that the Gage R and R reports `%StudyVar` above 30 and
raises `MSA_UNACCEPTABLE` at CRITICAL, that every open capability and SPC finding on that metric
gains `confidence_degraded_by` pointing at the MSA finding, and that the report prints the
degradation banner rather than the Cpk alone. This scenario is the section's headline behavior.
Its gage study comes from `twinflow_lss.testing.gage_study_generator` at P2 and from component 2's
sensor catalog at P3, and the assertions are identical in both.

S-LSS-03, the what-if verdict. Run baseline and "second scan portal at dock 3" on the same run
seed and replication index. Assert that the `crn_integrity` record reports equal draw counts on
every shared stream, that the assumption checker selects a paired test on that evidence, that batch means
engages because lag-1 autocorrelation exceeds the threshold, that the selected test matches the
recorded expectation, that the effect-size interval excludes zero, and that a deliberately tiny
variant of the same change is reported as "statistically significant, not practically
significant".

S-LSS-04, pairing lost. Run baseline and "arrival rate up 15 percent", which changes how many
arrivals occur, and with it how many values the arrival streams draw. Assert that
`crn_integrity` reports unequal counts, that the checker selects the independent-samples test,
that `HYPOTHESIS_PAIRING_LOST` is raised, and that the report names the loss of power rather than
attributing the wider interval to the change under test.

S-LSS-05, alarm flood. Kill the broker mid-run so 200 findings arrive in three minutes of sim
time. Assert that flood mode engages within one detector window, that `ALARM_FLOOD` is raised for
the affected console, that `BROKER_UNREACHABLE` suppresses the child `DEVICE_OFFLINE` findings by
design, that every finding is still present in the JSONL sink, and that the post-flood
`alarm_metrics/v1` control chart shows the excursion as a rule-1 violation.

S-LSS-06, safety floor under flood. During the S-LSS-05 flood, inject one safety-class finding.
Assert that it is presented at CRITICAL, at the top of the collapsed list, and is never deduped
away.

S-DIV-01, twin divergence. Apply a step change to the plant that the twin's config does not carry,
so the twin keeps predicting the pre-change behavior. Assert that the observed chart and the predicted
chart both stay in control on their own terms, that the residual chart fires, that the magnitude
filter passes, that `TWIN_DIVERGENCE` is raised with the residual evidence, and that the chain
leads to `get_fleet_health` first. Then repeat with the magnitude threshold set above the injected
step and assert no finding is raised, which is the half of the test that can fail for the right
reason.

S-DIV-02, calibration drift without a mean shift. Inflate the plant's variance while leaving its
mean where the twin predicts. Assert that the difference residuals stay centerd, that the
probability integral transform residuals fail the uniformity test, and that
`TWIN_CALIBRATION_DRIFT` is raised rather than `TWIN_DIVERGENCE`.

S-PM-01, rework recovery. Inject 5 percent rework at the scan station. Assert that the inductive
miner recovers the loop, that conformance flags exactly the injected traces, that the estimated
rework rate lands within 0.5 percentage points of the injected rate, and that the map's
non-value-added ladder grows by the measured rework time.

S-PM-02, bottleneck cross-check. Configure a case where resource utilization and mined waiting
time disagree, a station with high utilization but low queueing because of upstream starvation.
Assert that `BOTTLENECK_DISAGREEMENT` fires and that both estimates appear in the evidence.

S-VSM-01, future state. Accept a what-if, regenerate the map, and assert that the diff names
exactly the changed stations, that the process cycle efficiency improvement carries a p-value and
an interval, and that the golden SVG and JSON match.

Golden files under `tests/golden/`: `capability-report.html`, `vsm-current.svg`,
`vsm-current.json`, `findings.jsonl`, `findings.jsonl.gz`, `validation-report.md`. Each is compared
after the declared normalization filter of 2.1, and the filter version is printed in the failure
message so a golden mismatch never gets blamed on the wrong thing. Regeneration is an explicit
`just golden-update` and the diff is reviewed in the pull request.

### 7.4 Determinism tests (C1)

VG-DET-01, byte-identical on a pinned platform. Run the full S-LSS-03 scenario twice in one
process and once in a fresh process with a different `PYTHONHASHSEED`. Assert byte-identical
findings JSONL, byte-identical gzip of that JSONL, byte-identical capability report, map SVG, map
JSON, and validation report, each after the normalization filter. Falsified by any byte
difference, and the failure message names which artifact and the first differing offset.

VG-DET-02, value-equivalent across platforms. Run the same scenario on the three platforms the CI
matrix covers, compare business events for exact equality, and compare continuous fields against
the recorded tolerance in `validation/cross_platform_tolerance.json`. The gate prints the observed
maximum divergence every run, and fails when it exceeds the recorded tolerance. It is falsified by
any business-event difference at all, and by a continuous-field divergence above the recorded
number.

Two supporting assertions run in the same job. The run manifest lists every named stream the run
used, and adding a bootstrap in the hypothesis layer changes no number produced by the mining
layer. `test_run_started_carries_no_wall_clock_or_platform_field` asserts D-01's carve-out
directly, so it cannot regress silently.

---

### 7.5 The validation gate registry

This is the section's defining feature and the mechanism behind the README claim.

#### 7.5.1 What a gate record is

A declarative record in `validation/valgates.yaml`, schema `/schemas/valgate/v1.json`:

```yaml
- id: VG-SPC-08
  statistic: "EWMA control chart center line and control limits"
  implementation: "twinflow_lss.spc.ControlChart(chart_type='ewma')"
  reference:
    class: published_reference
    name: "NIST/SEMATECH e-Handbook of Statistical Methods"
    locator: "Section 6.3.2.4, EWMA Control Charts, worked example"
    edition: "2012 update"
    url: "https://www.itl.nist.gov/div898/handbook/pmc/section3/pmc324.htm"
    license: "public domain, US Government work"
    retrieved_date: "2026-08-09"
    retrieved_by_author: true
    published_precision: "4 decimal places"
    transcription_sha256: "sha256:..." # of the checked-in reference values file
  data: validation/data/nist_ewma_example.csv
  expected: validation/expected/VG-SPC-08.json
  tolerance: { kind: absolute, value: 5.0e-5, basis: "half a unit in the last printed digit" }
  noise_floor: null # deterministic gate
  falsifier: "any expected value differs by more than the tolerance"
  test_node: "tests/validation/test_spc_gates.py::test_vg_spc_08"
  phase: P2
  status: PENDING # PENDING | IMPLEMENTED | PASSING | FAILING
  deferral: null
```

Six fields carry the weight, and each answers one of D-11's five conditions plus the confidence
rule.

`reference.class` is one of six values, and the generated claim block partitions on it:

| Class                        | Meaning                                                                                                                    | Counts toward the published-reference claim |
|------------------------------|----------------------------------------------------------------------------------------------------------------------------|---------------------------------------------|
| `published_reference`        | the expected numbers are printed in a named external publication                                                           | yes                                         |
| `published_formula`          | the definition is printed in a named external publication and the expected numbers follow from evaluating it independently | no, counted separately                      |
| `closed_form`                | the expected value is an exact mathematical result, with a named external publication for the result itself                | no, counted separately                      |
| `ground_truth_recovery`      | the expected value is the simulator's injected truth                                                                       | no, counted separately                      |
| `independent_implementation` | the comparison is against a third-party implementation's output                                                            | no, counted separately                      |
| `software_invariant`         | the assertion is about behavior, not about a statistic                                                                     | no, excluded entirely                       |

`reference.retrieved_by_author` records whether the person who wrote the record has read the source
text. It is false for every paid or paywalled publication this repository cites. A gate whose
reference has `retrieved_by_author: false` cannot leave `PENDING`, because its expected values
have not been transcribed from anything, and `just phase-gate` blocks the phase until they have.
That converts "we will look it up later" from a comment into a build failure.

`published_precision` records how many digits the source prints. `tolerance` may never be tighter
than that, and `test_valgate_tolerance_respects_published_precision` asserts the relation
mechanically for every `published_reference` record, so a hand-entered 1e-9 against a
three-decimal table fails CI rather than passing quietly.

`noise_floor` is required and non-null for every gate whose assertion is over a stochastic
quantity. It records the measured standard error and how it was measured. The tolerance must be
wider than it, and `test_valgate_noise_floor_is_below_tolerance` asserts that too.

`falsifier` is a sentence naming the observation that fails the gate. It is required, and a gate
whose falsifier is empty fails schema validation. A criterion that passes about half the time
under the null is not a gate (D-12).

`transcription_sha256` exists because a published reference can move or change edition. The gate
carries a checksum of the transcribed values file, so an edit to the expected numbers is visible
in review and cannot be slipped in to make a failing test pass.

#### 7.5.2 The rule

A phase cannot close until every gate assigned to that phase is `PASSING`. `just phase-gate P2`
exits non-zero when any P2 gate is `PENDING`, `IMPLEMENTED` but not passing, or `FAILING`.

There is no `WAIVED` status, because a status that both fails the phase gate and claims to defer
the gate does neither. Deferral is a rewrite rather than a status. `just defer-gate VG-X --to P3
--reason "..."` moves the gate's `phase` field to the later phase, sets `status` back to `PENDING`,
and records `deferral: {from_phase, to_phase, reason, opened_on_sim_date, issue_ref}`. P2's gate
list shrinks by one and P3's grows by one, the gate still exists, and the no-cut rule holds. Every
deferral is printed by name in the generated `VALIDATION.md` and in the report's validation
appendix, so the public claim can never be stronger than the evidence. A deferral with an empty
reason or no issue reference is rejected.

New statistics register their gate before their implementation merges.

#### 7.5.3 Numerical core: NIST Statistical Reference Datasets

The Statistical Reference Datasets are NIST Standard Reference Database 140
(<https://www.itl.nist.gov/div898/strd/>, DOI 10.18434/T43G6C, retrieved 2026-08-09), a US
Government work in the public domain. They carry 58 datasets across four collections, counted from
the four published index pages: 9 univariate summary statistics, 11 analysis of variance, 11 linear
least squares, and 27 nonlinear least squares. Certified values are printed to 15 significant
digits, which is why the log relative error is clamped at 15.

Agreement is scored with the log relative error,
`LRE = -log10(abs(computed - certified) / abs(certified))`, clamped to 15. The metric is
attributed to McCullough, "Assessing the Reliability of Statistical Software: Part I",
_The American Statistician_ 52(4), 1998, rather than to NIST, which publishes the certified values
and the difficulty levels but not this score.

| Gate      | Statistic                                                                                                    | Datasets                                                                    | Assertion                                                                                                                                                                                                                                                                  |
|-----------|--------------------------------------------------------------------------------------------------------------|-----------------------------------------------------------------------------|----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| VG-NUM-01 | mean, standard deviation, lag-1 autocorrelation                                                              | PiDigits, Lottery, Lew, Mavro, Michelso, NumAcc1, NumAcc2, NumAcc3, NumAcc4 | `LRE >= 13` on NumAcc1; `LRE >= 10` on NumAcc2 and NumAcc3; `LRE >= 8` on NumAcc4, whose difficulty level the source prints as Higher. A companion test shows the naive one-pass sum of squares failing NumAcc4 and the Welford path passing, and publishes the comparison |
| VG-NUM-02 | one-way ANOVA sums of squares, mean squares, F                                                               | SiRstv, AtmWtAg, SmLs01 through SmLs09                                      | `LRE >= 8` on the hardest set; `LRE >= 11` on the sets the source marks Lower difficulty                                                                                                                                                                                   |
| VG-NUM-03 | linear and polynomial regression coefficients, their standard errors, residual standard deviation, R-squared | Norris, Pontius, NoInt1, NoInt2, Filip, Longley, Wampler1 through Wampler5  | `LRE >= 7` on Filip, degree 10, which the source marks Higher difficulty, via SVD or QR; `LRE >= 10` elsewhere. The published table also shows the normal-equations path failing Filip, which is the honest way to make the point that the solver choice matters           |
| VG-NUM-04 | nonlinear least squares parameters and residual sum of squares, from the certified start values              | all 27 nonlinear sets                                                       | `LRE >= 4` from Start 1 and `LRE >= 7` from Start 2, per dataset, published as a table rather than as a single pass or fail, because some solvers legitimately fail from Start 1; see OQ-11                                                                                |

All four records carry `reference.class: published_reference`, because the certified values are
printed in the collection itself. Falsifier for each: any dataset whose log relative error falls
below its stated floor.

VG-NUM-03 and VG-NUM-04 license the regression core that `twinflow_lss.trend` and the linearity
study of 5.6.4 sit on. They do not by themselves license a prediction-interval
coverage claim, which is why VG-TRD-03 exists separately.

#### 7.5.4 Making "no statistic without a gate" mechanical

The rule "a pull request adding a public statistical function with no gate record fails CI" needs
a definition of "public statistical function" a machine can apply. It has one.

Every public callable in `twinflow_lss.spc`, `.capability`, `.msa`, `.hypothesis`, `.trend`,
`.charts`, `.batch`, `.sampling`, and `.divergence` carries the `@val_gate("VG-...")` decorator,
which records the gate ids on the function object and registers them at import time.

`test_every_public_statistic_has_a_gate` (VG-SCH-02) walks each module's `__all__`, filters to
callables, and asserts three things: the callable carries at least one gate id, every id it names
exists in `validation/valgates.yaml`, and every gate in the registry is named by at least one
callable or by a named test node. The first assertion catches a new function with no gate. The
third catches an orphan gate left behind by a deleted function. The test reads `__all__` rather
than the module namespace, so a helper that is not part of the public API is not caught by
accident.

`test_val_gate_ids_resolve` runs in the fast tier so the feedback is immediate, and the same
assertion runs again in the gate tier against the full registry.

#### 7.5.5 SPC gates

The e-Handbook is public domain and, unlike the Statistical Reference Datasets, it contains worked
SPC examples. Which sections contain a worked example, and which contain only formulas, is stated
per gate, because the difference decides the reference class.

| Gate      | Statistic                                                                                         | Reference                                                                                                                                                                                        | Class               | Tolerance and falsifier                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                     |
|-----------|---------------------------------------------------------------------------------------------------|--------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|---------------------|-----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| VG-SPC-01 | factors `A2`, `D3`, `D4` for n = 2 to 10                                                          | e-Handbook 6.3.2.1, "Factors for Calculating Limits for X-bar and R Charts", printed to 3 decimals                                                                                               | published_reference | analytic value rounded to 3 decimals equals the printed value, equivalently an absolute difference of at most 5e-4. Falsified by any of the 27 tabulated values differing in the third decimal                                                                                                                                                                                                                                                                                                                              |
| VG-SPC-02 | factors `d2`, `d3`, `c4`, `A3`, `B3`, `B4` for n = 2 to 25, and `A2`, `D3`, `D4` for n = 11 to 25 | the two analytic routes to each constant, with `c4`'s closed form as the e-Handbook prints it in 6.3.2                                                                                           | closed_form         | the quadrature route and the closed-form route agree to a relative tolerance of 1e-10. Falsified by any n where they do not. See OQ-3: no external table this repository has read covers these constants at these n                                                                                                                                                                                                                                                                                                         |
| VG-SPC-03 | individuals and moving-range chart center line and limits                                         | e-Handbook 6.3.2.2 worked example, flow rate, 10 batches, printed center line 50.81, UCL 55.8041, LCL 45.8159                                                                                    | published_reference | absolute difference at most 5e-5, half a unit in the last printed digit. Falsified by any of the three values differing in the fourth decimal                                                                                                                                                                                                                                                                                                                                                                               |
| VG-SPC-04 | X-bar and R, X-bar and s, and u chart limits                                                      | the e-Handbook factor definitions of 6.3.2 and 6.3.2.1, evaluated independently                                                                                                                  | published_formula   | limits computed from the factors and limits computed from the sigma estimate agree to a relative tolerance of 1e-12 on a constructed balanced dataset. Falsified by disagreement at that tolerance, or by a factor that does not match VG-SPC-01                                                                                                                                                                                                                                                                            |
| VG-SPC-05 | c chart center line and limits                                                                    | e-Handbook 6.3.3.1, Counts Control Charts, worked example with `cbar = 16`, UCL 28, LCL 4                                                                                                        | published_reference | exact integer match on all three. Falsified by any difference                                                                                                                                                                                                                                                                                                                                                                                                                                                               |
| VG-SPC-06 | p chart with constant subgroup size                                                               | e-Handbook 6.3.3.2, Proportions Control Charts, worked example, 30 wafers of 50 chips                                                                                                            | published_reference | absolute difference at most half a unit in the last printed digit of each published value. Falsified by any difference beyond that                                                                                                                                                                                                                                                                                                                                                                                          |
| VG-SPC-07 | p chart with varying subgroup size, per-point limits                                              | the constant-n case as the boundary                                                                                                                                                              | closed_form         | with every `n_i` equal, the per-point limits equal the constant-n limits to a relative tolerance of 1e-12, and each per-point limit equals the closed form at its own `n_i`. Falsified by a single-band result, or by disagreement at the boundary. See OQ-3                                                                                                                                                                                                                                                                |
| VG-SPC-08 | EWMA chart center line and limits                                                                 | e-Handbook 6.3.2.4 worked example, UCL 52.5884, LCL 47.4115                                                                                                                                      | published_reference | absolute difference at most 5e-5. Falsified by either limit differing in the fourth decimal                                                                                                                                                                                                                                                                                                                                                                                                                                 |
| VG-SPC-09 | tabular CUSUM and V-mask                                                                          | e-Handbook 6.3.2.3 worked example, `h = 4.1959`, `k = 0.3175`                                                                                                                                    | published_reference | absolute difference at most 5e-5 on the design parameters and on every tabulated cumulative sum. Falsified by any difference beyond that                                                                                                                                                                                                                                                                                                                                                                                    |
| VG-SPC-10 | Hotelling T-squared phase I and phase II upper control limits                                     | e-Handbook 6.5.4.3.1 and 6.5.4.3.2, which print the closed-form limits; the F quantiles come from the e-Handbook's upper critical values of the F distribution, 1.3.6.7.3, printed to 3 decimals | published_formula   | the implemented limit equals the published formula evaluated at the tabulated F quantile to a relative tolerance of 1e-9, and the F quantile matches the printed table to 5e-4. Falsified by either comparison                                                                                                                                                                                                                                                                                                              |
| VG-SPC-11 | rule firing fixtures and the single-rule in-control average run length                            | constructed fixtures for firing and near-miss, plus the e-Handbook 6.3.2.1 statement that for a normal distribution `p = 0.0027` and the ARL is about 371                                        | published_reference | every fixture fires exactly where hand-verified; and the measured ARL0 over 10 to the 6 seeded in-control points has a 95 percent interval containing 371. Noise floor: the null run length is geometric with `p = 0.0027`, so its standard deviation is `sqrt(1-p)/p`, about 370, and over the roughly 2,700 completed runs in 10 to the 6 points the standard error of the mean is about 7.1 and the 95 percent half-width about 14. Falsified when a fixture fires in the wrong place, or when the interval excludes 371 |
| VG-SPC-12 | combined Western Electric in-control average run length                                           | Champ and Woodall, "Exact Results for Shewhart Control Charts with Supplementary Runs Rules", _Technometrics_ 29(4), 1987                                                                        | published_reference | the measured ARL0's 95 percent interval contains the published exact value for the four combined rules. The reference has `retrieved_by_author: false`, so the gate stays `PENDING` until the value is transcribed from the paper and its checksum recorded. Falsified when the interval excludes the transcribed value                                                                                                                                                                                                     |

VG-SPC-11 and VG-SPC-12 are the two gates that prove the rules are not merely implemented but
implemented correctly together, which is where implementations usually diverge.

#### 7.5.6 Capability, MSA, trend, and chart gates

| Gate      | Statistic                                                                                                                     | Reference                                                                                                                                                                                                                                                                                                                             | Class                 | Tolerance and falsifier                                                                                                                                                                                                                                                                                                                                                                                                                                  |
|-----------|-------------------------------------------------------------------------------------------------------------------------------|---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|-----------------------|----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| VG-CAP-01 | Cp, Cpk, Cpu, Cpl, and the k factor                                                                                           | e-Handbook 6.1.6 Capability Index Example: USL 20, LSL 8, mean 16, s 2, giving Cp 1.0, k 0.3333, Cpk 0.6667, Cpu 0.6667, Cpl 1.3333                                                                                                                                                                                                   | published_reference   | absolute difference at most 5e-5, half a unit in the last printed digit. Falsified by any of the five values differing in the fourth decimal                                                                                                                                                                                                                                                                                                             |
| VG-CAP-02 | Pp, Ppk, and the observed against expected PPM table                                                                          | the same worked example re-run with the overall sigma estimate, where Pp and Ppk are Cp and Cpk by construction                                                                                                                                                                                                                       | closed_form           | Pp and Ppk computed from `sigma_overall` equal Cp and Cpk computed from the same number to a relative tolerance of 1e-12, and the PPM table rows sum to the total row exactly. Falsified by either. See OQ-5: no published Pp and Ppk worked example has been retrieved, so this gate does not count toward the published-reference claim                                                                                                                |
| VG-CAP-03 | sigma level and DPMO conversion                                                                                               | the standard normal distribution function, and the canonical identity that a long-term Z of 4.5 is quoted as a nominal six sigma after the 1.5 shift                                                                                                                                                                                  | closed_form           | `dpmo(4.5)` equals `(1 - Phi(4.5)) * 1e6`, which is 3.3977 to 4 decimals, to a relative tolerance of 1e-9, and `sigma_level_shifted` equals `z_bench_overall + 1.5` exactly. Falsified by either, and by the field-naming check that `sigma_level_shifted` and not `sigma_level_z_overall` carries the shift                                                                                                                                             |
| VG-CAP-04 | Box-Cox lambda recovery and the Johnson transform                                                                             | Box and Cox, "An Analysis of Transformations", _Journal of the Royal Statistical Society Series B_ 26(2), 1964; Johnson, "Systems of Frequency Curves Generated by Methods of Translation", _Biometrika_ 36(1/2), 1949                                                                                                                | closed_form           | data generated by applying a known inverse transform with parameter `lambda_0` recovers `lambda_0` within the profile-likelihood interval the fit reports, over 200 seeded replicates. Noise floor: the measured standard deviation of the recovered lambda, printed each run. Falsified when the interval fails to cover `lambda_0` more often than the nominal rate allows                                                                             |
| VG-CAP-05 | non-normal capability by the percentile method                                                                                | a Weibull with known shape and scale, whose 0.135 and 99.865 percentiles are closed form                                                                                                                                                                                                                                              | closed_form           | the computed percentiles match the closed form to a relative tolerance of 1e-9. Falsified by any difference beyond it. The method itself is attributed to the ISO 22514 series in the report caption; the standard has not been retrieved by this repository's author                                                                                                                                                                                    |
| VG-CAP-06 | Cpk confidence interval coverage                                                                                              | Bissell, "How reliable is your capability index?", _Applied Statistics_ 39(3), 1990                                                                                                                                                                                                                                                   | published_formula     | Monte Carlo coverage over 20,000 seeded samples at `n >= 50` and nominal 0.95 lies in [0.93, 0.97]. Noise floor: the standard error of a proportion at 0.95 over 20,000 samples is 0.0015, so the band is about 20 standard errors wide, and it is that wide to accommodate the approximation's own bias rather than the simulation noise. Falsified when the measured coverage lies outside the band                                                    |
| VG-CAP-07 | Cpm                                                                                                                           | e-Handbook 6.1.6 prints the Cpm formula and no numeric example                                                                                                                                                                                                                                                                        | published_formula     | with the mean at the target, Cpm equals Cp to a relative tolerance of 1e-12, and with the mean off target Cpm is strictly less than Cp. Falsified by either. See OQ-5                                                                                                                                                                                                                                                                                    |
| VG-MSA-01 | ANOVA Gage R and R with `error_term = repeatability`: EV, AV, GRR, PV, TV, percent contribution, percent study variation, ndc | AIAG _Measurement Systems Analysis_, product code MSA-4 (aiag.org, retrieved 2026-08-09), worked example, page cited in the record                                                                                                                                                                                                    | published_reference   | exact to the manual's printed precision, recorded in `published_precision`. `retrieved_by_author: false`, so the gate stays `PENDING` until the numbers are transcribed. Falsified by any value differing at the printed precision                                                                                                                                                                                                                       |
| VG-MSA-02 | ANOVA Gage R and R with `error_term = interaction` on the same data                                                           | the published output for the same dataset from a second source, named in the record                                                                                                                                                                                                                                                   | published_reference   | as VG-MSA-01. `retrieved_by_author: false`. See OQ-2 on which second source is used and how it is stored                                                                                                                                                                                                                                                                                                                                                 |
| VG-MSA-03 | average and range method with K1, K2, K3                                                                                      | AIAG MSA-4 worked example                                                                                                                                                                                                                                                                                                             | published_reference   | as VG-MSA-01. `retrieved_by_author: false`                                                                                                                                                                                                                                                                                                                                                                                                               |
| VG-MSA-04 | interaction pooling at alpha 0.25 reproduces the manual's pooled table                                                        | AIAG MSA-4                                                                                                                                                                                                                                                                                                                            | published_reference   | as VG-MSA-01. `retrieved_by_author: false`                                                                                                                                                                                                                                                                                                                                                                                                               |
| VG-MSA-05 | variance closure and clamp reporting                                                                                          | the ANOVA identity between the total sum of squares and the component sums                                                                                                                                                                                                                                                            | closed_form           | with no clamped component, the relative closure residual against `tv_from_total_ss` is at most 1e-10; with a clamped component, closure fails, `variance_closure_defect` carries the residual, and `MSA_VARIANCE_CLOSURE_DEFECT` is raised. Falsified by a residual above the tolerance with no clamp, or by a clamp with no defect record                                                                                                               |
| VG-MSA-06 | attribute agreement, Cohen's and Fleiss' kappa                                                                                | Cohen, "A Coefficient of Agreement for Nominal Scales", _Educational and Psychological Measurement_ 20(1), 1960; Fleiss, "Measuring Nominal Scale Agreement Among Many Raters", _Psychological Bulletin_ 76(5), 1971                                                                                                                  | published_reference   | exact to each paper's printed precision on its own worked example. `retrieved_by_author: false` for both. Falsified by any difference at that precision                                                                                                                                                                                                                                                                                                  |
| VG-MSA-07 | bias and linearity study                                                                                                      | AIAG MSA-4 gage linearity example                                                                                                                                                                                                                                                                                                     | published_reference   | as VG-MSA-01. `retrieved_by_author: false`. The regression itself is separately gated by VG-NUM-03                                                                                                                                                                                                                                                                                                                                                       |
| VG-MSA-08 | ground-truth variance recovery                                                                                                | the components injected by `twinflow_lss.testing.gage_study_generator` at P2, and by component 2's sensor catalog at P3                                                                                                                                                                                                               | ground_truth_recovery | over 200 seeded studies of 10 parts by 3 operators by 3 replicates, the 95 percent interval of the mean recovered `sigma^2_repeatability`, `sigma^2_operator`, and `sigma^2_part` each covers the injected value. Noise floor: the measured standard error of each component's mean across the 200 studies, printed every run, with no assumed value. Falsified when any interval excludes its injected truth                                            |
| VG-TRD-01 | linear and exponential trend fits                                                                                             | the certified linear least squares datasets of VG-NUM-03                                                                                                                                                                                                                                                                              | published_reference   | as VG-NUM-03. Falsified by any dataset below its LRE floor                                                                                                                                                                                                                                                                                                                                                                                               |
| VG-TRD-02 | Weibull-hazard trend fit                                                                                                      | data generated from a Weibull with known shape and scale                                                                                                                                                                                                                                                                              | closed_form           | over 200 seeded replicates the profile-likelihood interval covers the generating parameters. Noise floor: measured standard error of each recovered parameter, printed each run. Falsified when coverage is materially below nominal at the measured noise floor                                                                                                                                                                                         |
| VG-TRD-03 | time-to-threshold prediction interval coverage                                                                                | the prediction interval for a fitted linear model, whose closed form is given in Draper and Smith, _Applied Regression Analysis_, 3rd edition, chapter 3                                                                                                                                                                              | closed_form           | Monte Carlo coverage over 20,000 seeded samples at nominal 0.90 lies in [0.885, 0.915]. Noise floor: the standard error of a proportion at 0.90 over 20,000 samples is 0.0021, so the band is about 7 standard errors wide. Falsified when the measured coverage lies outside the band. `retrieved_by_author: false` on the textbook; the closed form is also checked against the residual algebra, so the gate can run before the citation is confirmed |
| VG-CHT-01 | Pareto ordering and cumulative share                                                                                          | none; this is an ordering and summation assertion                                                                                                                                                                                                                                                                                     | software_invariant    | categories sort by descending count with ties broken by category name, the cumulative share is monotone non-decreasing, and the final cumulative share is 1.0 to a relative tolerance of 1e-12. Falsified by any of the three                                                                                                                                                                                                                            |
| VG-CHT-02 | histogram bin-count rules                                                                                                     | Sturges, "The Choice of a Class Interval", _Journal of the American Statistical Association_ 21(153), 1926; Freedman and Diaconis, "On the Histogram as a Density Estimator", _Zeitschrift fur Wahrscheinlichkeitstheorie und verwandte Gebiete_ 57(4), 1981; Scott, "On Optimal and Data-Based Histograms", _Biometrika_ 66(3), 1979 | published_formula     | each rule's bin width or bin count matches its published formula evaluated on a constructed sample to a relative tolerance of 1e-12. Falsified by any rule differing. `retrieved_by_author: false` on all three papers; the formulas are checked against each other's published relation on a normal sample                                                                                                                                              |
| VG-BAT-01 | golden-batch score                                                                                                            | a batch profile generated with a known deviation from the golden profile                                                                                                                                                                                                                                                              | ground_truth_recovery | the score ranks the injected deviations in the injected order and the perfect-match case scores exactly 1.0. Falsified by a ranking inversion or by a perfect match scoring anything else                                                                                                                                                                                                                                                                |

#### 7.5.7 Hypothesis gates

| Gate      | Statistic                                                                | Reference                                                                                                                                                                                                                                 | Class               | Tolerance and falsifier                                                                                                                                                                                                                                                                                                                                                                                                                          |
|-----------|--------------------------------------------------------------------------|-------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|---------------------|--------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| VG-HYP-01 | pooled two-sample t                                                      | e-Handbook 1.3.5.3, AUTO83B.DAT: `T = -12.62059`, two-tailed critical value 1.9673, one-tailed 1.6495                                                                                                                                     | published_reference | absolute difference at most 5e-6 on T and 5e-5 on each critical value. Falsified by any difference beyond that. The page prints no p-value, so the p-value path is checked by VG-HYP-02 and by the closed-form relation to the critical values                                                                                                                                                                                                   |
| VG-HYP-02 | Welch's t and the Welch-Satterthwaite degrees of freedom                 | e-Handbook 7.3.1 worked example: means 36.0909 and 32.2222, standard deviations 4.9082 and 2.5386, `t = 2.2694`, `nu = 15.5`                                                                                                              | published_reference | absolute difference at most 5e-5 on t and 5e-2 on nu, each half a unit in the last printed digit. Falsified by either                                                                                                                                                                                                                                                                                                                            |
| VG-HYP-03 | one-way ANOVA                                                            | the certified ANOVA datasets of VG-NUM-02                                                                                                                                                                                                 | published_reference | as VG-NUM-02                                                                                                                                                                                                                                                                                                                                                                                                                                     |
| VG-HYP-04 | Wilcoxon signed-rank, exact and normal approximation with tie correction | brute-force enumeration of the exact null distribution for `n <= 12`; Wilcoxon, "Individual Comparisons by Ranking Methods", _Biometrics Bulletin_ 1(6), 1945                                                                             | closed_form         | exact match against the enumerated distribution at every attainable statistic value. Falsified by any mismatch                                                                                                                                                                                                                                                                                                                                   |
| VG-HYP-05 | Mann-Whitney U, exact and normal approximation with tie correction       | brute-force enumeration of the exact null distribution for `n1 + n2 <= 14`; Mann and Whitney, "On a Test of Whether one of Two Random Variables is Stochastically Larger than the Other", _Annals of Mathematical Statistics_ 18(1), 1947 | closed_form         | exact match against the enumerated distribution. Falsified by any mismatch                                                                                                                                                                                                                                                                                                                                                                       |
| VG-HYP-06 | Levene, Brown-Forsythe form                                              | e-Handbook 1.3.5.10, GEAR.DAT: `W = 1.705910`, F critical value 1.9855                                                                                                                                                                    | published_reference | absolute difference at most 5e-7 on W and 5e-5 on the critical value. Falsified by either                                                                                                                                                                                                                                                                                                                                                        |
| VG-HYP-07 | Bartlett                                                                 | e-Handbook 1.3.5.7, GEAR.DAT: `T = 20.78580`, chi-square critical value 16.919                                                                                                                                                            | published_reference | absolute difference at most 5e-6 on T and 5e-4 on the critical value. Falsified by either                                                                                                                                                                                                                                                                                                                                                        |
| VG-HYP-08 | Anderson-Darling                                                         | e-Handbook 1.3.5.14: adjusted `A2 = 0.2576` on Y1 and `A2 = 5.8492` on Y2                                                                                                                                                                 | published_reference | absolute difference at most 5e-5 on each adjusted statistic, and the record names which adjustment constant is used, because the page warns that different constants give different critical values. Falsified by either statistic differing in the fourth decimal, or by an unnamed adjustment constant                                                                                                                                         |
| VG-HYP-09 | Shapiro-Wilk                                                             | Royston, "Remark AS R94: A Remark on Algorithm AS 181", _Applied Statistics_ 44(4), 1995, test values                                                                                                                                     | published_reference | exact to the paper's printed precision. `retrieved_by_author: false`, so the gate stays `PENDING` until the test values are transcribed. Falsified by any difference at that precision                                                                                                                                                                                                                                                           |
| VG-HYP-10 | Kruskal-Wallis with tie correction                                       | brute-force enumeration for small n; Kruskal and Wallis, "Use of Ranks in One-Criterion Variance Analysis", _Journal of the American Statistical Association_ 47(260), 1952                                                               | closed_form         | exact match against the enumerated null distribution for `N <= 12`. Falsified by any mismatch                                                                                                                                                                                                                                                                                                                                                    |
| VG-HYP-11 | Welch's ANOVA                                                            | Welch, "On the Comparison of Several Mean Values: An Alternative Approach", _Biometrika_ 38(3/4), 1951                                                                                                                                    | published_formula   | with equal group sizes and equal group variances, Welch's F equals the classical one-way F to a relative tolerance of 1e-12, and with two groups its square root equals Welch's t. Falsified by either                                                                                                                                                                                                                                           |
| VG-HYP-12 | Tukey HSD                                                                | the studentized range identity `q(2, df) = sqrt(2) * t(df)`                                                                                                                                                                               | closed_form         | for two groups the HSD interval equals the pooled two-sample t interval at the same alpha to a relative tolerance of 1e-10. Falsified by any difference. See OQ-6: no published studentized range table has been retrieved for `k > 2`                                                                                                                                                                                                           |
| VG-HYP-13 | Games-Howell                                                             | the reduction identities                                                                                                                                                                                                                  | closed_form         | with two groups the Games-Howell interval equals the Welch t interval, and with equal variances and equal group sizes it agrees with Tukey HSD to a relative tolerance of 1e-8. Falsified by either                                                                                                                                                                                                                                              |
| VG-HYP-14 | Mood's median test                                                       | the 2 by k contingency chi-square it reduces to                                                                                                                                                                                           | closed_form         | the statistic equals the chi-square computed directly from the constructed table to a relative tolerance of 1e-12, and for a 2 by 2 table with small counts it agrees in decision with Fisher exact. Falsified by either                                                                                                                                                                                                                         |
| VG-HYP-15 | two-proportion z and Fisher exact                                        | the hypergeometric enumeration, and the identity `z^2 = chi-square` without continuity correction                                                                                                                                         | closed_form         | Fisher exact matches the enumerated hypergeometric tail exactly, and `z^2` equals the uncorrected chi-square to a relative tolerance of 1e-12. Falsified by either                                                                                                                                                                                                                                                                               |
| VG-HYP-16 | chi-square test of independence                                          | the same identity extended to an r by c table, and the closed-form chi-square distribution function                                                                                                                                       | closed_form         | the statistic equals the direct sum over cells to a relative tolerance of 1e-12, and the p-value equals the closed-form upper tail to 1e-10. Falsified by either                                                                                                                                                                                                                                                                                 |
| VG-HYP-17 | Bonferroni adjustment                                                    | the definition                                                                                                                                                                                                                            | closed_form         | `p_adjusted = min(1, m * p)` exactly for every input, and the familywise error rate over 10,000 seeded families of true nulls is at most alpha within Monte Carlo error. Noise floor: the standard error of a proportion at alpha over 10,000 families, printed each run. Falsified by an arithmetic mismatch, or by a measured rate above alpha by more than two standard errors                                                                |
| VG-HYP-18 | Benjamini-Hochberg FDR control                                           | Benjamini and Hochberg, "Controlling the False Discovery Rate", _Journal of the Royal Statistical Society Series B_ 57(1), 1995                                                                                                           | closed_form         | over 10,000 seeded families with known true nulls, the realized false discovery rate is at most `q` plus two standard errors. Noise floor: the measured standard error of the realized rate across the families, printed each run. Falsified when the realized rate exceeds that bound                                                                                                                                                           |
| VG-HYP-19 | Cohen's d, Hedges' g, and interval coverage                              | Hedges and Olkin, _Statistical Methods for Meta-Analysis_, 1985                                                                                                                                                                           | published_reference | the exact gamma form of `J` agrees with `1 - 3/(4m - 1)` to a relative tolerance of 1e-3 at `m >= 10`, which is the approximation's own accuracy rather than a machine tolerance, and the non-central t interval covers at [0.93, 0.97] over 20,000 seeded samples at nominal 0.95. Noise floor: 0.0015, as VG-CAP-06. `retrieved_by_author: false`. Falsified by either                                                                         |
| VG-HYP-20 | Cliff's delta and rank-biserial correlation                              | the algebraic identities `rank_biserial = 1 - 2U/(n1 n2)` and `cliffs_delta = 2U/(n1 n2) - 1`; Cliff, "Dominance Statistics: Ordinal Analyzes to Answer Ordinal Questions", _Psychological Bulletin_ 114(3), 1993                         | closed_form         | both identities hold to a relative tolerance of 1e-12 for every generated sample. Falsified by either                                                                                                                                                                                                                                                                                                                                            |
| VG-HYP-21 | eta-squared and omega-squared                                            | the ANOVA table identities                                                                                                                                                                                                                | closed_form         | both equal their definitions computed from the certified ANOVA sums of squares of VG-NUM-02 to a relative tolerance of 1e-12, and omega-squared is at most eta-squared. Falsified by either                                                                                                                                                                                                                                                      |
| VG-HYP-22 | TOST equivalence                                                         | Schuirmann, "A Comparison of the Two One-Sided Tests Procedure and the Power Approach", _Journal of Pharmacokinetics and Biopharmaceutics_ 15(6), 1987                                                                                    | published_formula   | the type I error at the equivalence boundary over 20,000 seeded datasets lies within two standard errors of alpha. Noise floor: the standard error of a proportion at alpha over 20,000 datasets, printed each run. Falsified when it lies outside                                                                                                                                                                                               |
| VG-HYP-23 | autocorrelation handling and batch means                                 | the AR(1) variance inflation factor `(1 + rho) / (1 - rho)`, a closed-form result stated in Law, _Simulation Modeling and Analysis_, 5th edition, chapter 9                                                                               | closed_form         | on seeded AR(1) data with `rho = 0.6` the naive t test's realized type I error matches the predicted inflation within two standard errors, and the batch-means test's realized type I error lies within two standard errors of alpha. Noise floor: the standard error of each realized rate, printed each run. Falsified when either comparison lies outside its band. This gate is what licenses every hypothesis test run on simulation output |
| VG-SAM-01 | single sampling plan selection and OC curve                              | e-Handbook 6.2.3, "How do you Choose a Single Sampling Plan?", and e-Handbook 6.2.3.1, "Choosing a Sampling Plan: MIL Standard 105D"                                                                                                      | published_reference | plan parameters match the published example exactly, and OC curve points match the closed-form binomial or hypergeometric value to a relative tolerance of 1e-9. Falsified by either                                                                                                                                                                                                                                                             |
| VG-SAM-02 | Z1.4-class switching rules                                               | ANSI/ASQ Z1.4, clause cited in the record                                                                                                                                                                                                 | published_reference | the switching state machine reproduces the standard's transitions on the worked sequence in the standard. `retrieved_by_author: false`, so the gate stays `PENDING`. Falsified by any transition differing                                                                                                                                                                                                                                       |

#### 7.5.8 Assumption-checker calibration

The earlier draft carried a gate that checked the assumption checker against "the checker's own
selection policy", which is a circular reference. It is replaced by a check with a real external
anchor and a real falsifier.

VG-HYP-24, class `closed_form`. Over 20,000 seeded null datasets drawn from a normal generator, a
lognormal generator, and a Student-t generator with 3 degrees of freedom, the realized rejection
rate of the auto-selected test lies within two standard errors of alpha for every generator. The
external anchor is the definition of a test's size: under the null the rejection rate is alpha,
which is what each named test's own published derivation asserts. The noise floor is the standard
error of a proportion at alpha over 20,000 datasets, about 0.0015 at alpha 0.05, printed each run.
It is falsified when any generator's realized rate lies outside the band, and the failure message
names the generator and the test the checker selected, so a calibration failure points at the
selection rule rather than at "the checker".

#### 7.5.9 Process mining, value stream map, SIPOC and swimlane, ranking, alarm, divergence, determinism, and schema gates

| Gate      | Statistic                                             | Reference                                                                                                                                   | Class                      | Tolerance and falsifier                                                                                                                                                                                                                                                                                                                                                                                                                           |
|-----------|-------------------------------------------------------|---------------------------------------------------------------------------------------------------------------------------------------------|----------------------------|---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| VG-PM-01  | conformance against ground truth                      | the checked-in exported reference model and a log with K injected deviations of known type and position                                     | ground_truth_recovery      | a deviation-free log achieves alignment fitness exactly 1.0, and a log with K injected deviations reports exactly K deviations at exactly those positions under the total frontier order of 5.11.3. Falsified by a different count, a different position, or a fitness below 1.0 on the clean log                                                                                                                                                 |
| VG-PM-02  | discovery recovery, clean case                        | the twin's exported reference model                                                                                                         | ground_truth_recovery      | the inductive miner on a complete, noise-free log recovers footprint F1 of exactly 1.0. Falsified by any cell of the footprint matrix differing                                                                                                                                                                                                                                                                                                   |
| VG-PM-03  | engine agreement                                      | PM4Py's output on the same log, run in the development-only `[oracle]` CI job and never distributed or served (D-14)                        | independent_implementation | this package's fitness and precision agree with PM4Py's to a relative tolerance of 1e-9, and a disagreement is reported with both values and the log that produced it. Falsified by disagreement beyond the tolerance. This class does not count toward the published-reference claim, because agreement between two implementations is not a publication                                                                                         |
| VG-PM-04  | alignment cost                                        | hand-constructed nets with hand-computed optimal alignment cost, published in the test file with the derivation                             | closed_form                | exact match on cost, and the returned alignment is the one the total frontier order selects. Falsified by a different cost, or by two runs returning different alignments of equal cost                                                                                                                                                                                                                                                           |
| VG-PM-05  | cycle-time contribution                               | the twin's instrumented per-station sojourn times, from the checked-in recorded run                                                         | ground_truth_recovery      | contributions sum to lead time to a relative tolerance of 1e-9, and each activity's mined sojourn agrees with the recorded value to a relative tolerance of 1e-9, because both are computed from the same recorded events rather than estimated. Falsified by either                                                                                                                                                                              |
| VG-PM-06  | rework detection                                      | injected loops of known count and length                                                                                                    | ground_truth_recovery      | exact recovery of loop count and loop length, and the estimated rework rate lies within its measured Monte Carlo interval of the injected rate over 100 seeded replicates. Noise floor: the measured standard error of the rate across replicates, printed each run. Falsified by a wrong count or length, or by an interval excluding truth                                                                                                      |
| VG-PM-07  | OCEL flattening distortion                            | the twin's known object structure                                                                                                           | ground_truth_recovery      | for each flattening, the reported convergence and divergence counts equal the counts derived from the known object structure exactly. Rows for object types whose producer does not yet exist print as "not yet generated" and assert nothing. Falsified by a count differing, or by a row printing a number for a flow that does not exist                                                                                                       |
| VG-VSM-01 | current-state lead time and process cycle efficiency  | the twin's ground-truth value-added and total time accounting, from the checked-in recorded run                                             | ground_truth_recovery      | lead time agrees to a relative tolerance of 1e-9 and process cycle efficiency to 1e-9, because both derive from the same recorded events. Falsified by either                                                                                                                                                                                                                                                                                     |
| VG-VSM-02 | Little's Law                                          | Little, "A Proof for the Queuing Formula L = lambda W", _Operations Research_ 9(3), 1961                                                    | published_reference        | at steady state, WIP and `throughput * lead_time` agree within the 95 percent interval measured over 30 seeded replications of the recorded scenario. Noise floor: the measured standard error of the ratio across the 30 replications, printed each run. `retrieved_by_author: false` on the paper; the theorem statement is standard and the gate's assertion is the equality it states. Falsified when the interval excludes 1.0 for the ratio |
| VG-VSM-03 | render determinism                                    | none; this is a behavior assertion                                                                                                          | software_invariant         | byte-identical SVG and JSON across processes for the same input after the normalization filter. Falsified by any byte difference                                                                                                                                                                                                                                                                                                                  |
| VG-SIP-01 | SIPOC recovery and provenance                         | the twin's station graph, the checked-in mined model, and `vsm/sipoc.yaml`                                                                  | ground_truth_recovery      | every step equals the roll-up of the mined model exactly, every derived input and output equals the station graph's material flow exactly, every declared cell equals the config, and every cell carries a provenance. Falsified by any cell differing, or by a cell missing its provenance                                                                                                                                                       |
| VG-SWM-01 | lane assignment and handoff count                     | the recorded event log's `resource` column                                                                                                  | ground_truth_recovery      | every node sits in the lane of the resource that executed it, and each lane-pair handoff count equals the count derived from the log exactly. Falsified by a misplaced node or a differing count                                                                                                                                                                                                                                                  |
| VG-SWM-02 | render determinism                                    | none; this is a behavior assertion                                                                                                          | software_invariant         | byte-identical SVG and JSON across processes for the same input after the normalization filter, as VG-VSM-03. Falsified by any byte difference                                                                                                                                                                                                                                                                                                    |
| VG-RNK-01 | Pugh arithmetic and order                             | hand-constructed candidate sets with hand-computed scores and order, published in the test file with the derivation                         | closed_form                | exact match on every score, every net score, and the full order, including the `whatif_id` tie-break. Falsified by any cell, sum, or position differing                                                                                                                                                                                                                                                                                           |
| VG-RNK-02 | stoplight classification                              | the declared matrix in `ranking/criteria.yaml` and constructed cases on each side of every band boundary                                    | software_invariant         | every constructed case classifies exactly as the matrix declares. Falsified by any case landing in a different class                                                                                                                                                                                                                                                                                                                              |
| VG-RNK-03 | no green without practical significance               | none; this is a behavior assertion                                                                                                          | software_invariant         | a candidate with no criterion scoring `+1` never classifies `green`, whatever its cost class and whatever the matrix says. Falsified by one that does                                                                                                                                                                                                                                                                                             |
| VG-ALM-01 | rationalization completeness and priority consistency | none; this is a completeness assertion over the repository's own configuration                                                              | software_invariant         | every reachable `FindingKind` has a record, every record's declared priority equals the matrix-derived priority, every `operator_response` is non-empty, and no `severity_map` entry violates 5.10.4. Falsified by any missing record, any priority mismatch, any empty response, or any out-of-range severity map entry                                                                                                                          |
| VG-ALM-02 | alarm metric arithmetic                               | a constructed alarm log with a declared console and a declared shift pattern, with hand-computed expected values published in the test file | software_invariant         | every metric of 5.10.6 matches its hand-computed value exactly, `operator_hours` matches the shift arithmetic exactly, and a window with no staffed shift reports null rather than a division by zero. This gate asserts nothing about any benchmark value from either alarm standard; see OQ-4. Falsified by any metric differing, or by a null-denominator window producing a number                                                            |
| VG-ALM-03 | no-loss invariant                                     | none; this is a behavior assertion                                                                                                          | software_invariant         | every finding raised during a constructed flood is retrievable from the sink regardless of dedupe, suppression, or shelving. Falsified by a single finding missing from the sink                                                                                                                                                                                                                                                                  |
| VG-ALM-04 | console assignment                                    | none; this is a routing assertion                                                                                                           | software_invariant         | every finding routes to the first matching console pattern in declared order, and a subject matching no pattern routes to the default console. Falsified by a route that does not match the declared order                                                                                                                                                                                                                                        |
| VG-DIV-01 | divergence detection                                  | an injected step change the twin's config does not carry                                                                                    | ground_truth_recovery      | `TWIN_DIVERGENCE` is raised within the detector's expected point range of the injected step, and no divergence is raised when the magnitude threshold is set above the injected step. Falsified by a miss, by a firing outside the range, or by a firing the magnitude filter was set to block                                                                                                                                                    |
| VG-DIV-02 | calibration detection                                 | an injected variance inflation with the mean held where the twin predicts                                                                   | ground_truth_recovery      | the probability integral transform residuals fail the uniformity test and `TWIN_CALIBRATION_DRIFT` is raised, while the difference residuals stay centerd and `TWIN_DIVERGENCE` is not raised. Falsified by the wrong finding kind, or by neither                                                                                                                                                                                                 |
| VG-DET-01 | byte-identical determinism on a pinned platform       | none; this is a behavior assertion                                                                                                          | software_invariant         | as 7.4. Falsified by any byte difference in any listed artifact                                                                                                                                                                                                                                                                                                                                                                                   |
| VG-DET-02 | value-equivalent determinism across platforms         | none; this is a behavior assertion                                                                                                          | software_invariant         | as 7.4. Falsified by any business-event difference, or by a continuous-field divergence above the recorded tolerance                                                                                                                                                                                                                                                                                                                              |
| VG-SCH-01 | schema conformance and additive-only evolution        | none; this is a contract assertion                                                                                                          | software_invariant         | every published finding validates against `/schemas/finding/v1.json`, every published event carries the envelope of 4.1, and a schema-diff test fails any non-additive change within a major version. Falsified by a validation failure or a non-additive diff                                                                                                                                                                                    |
| VG-SCH-02 | registry coverage of the public API                   | none; this is a coverage assertion                                                                                                          | software_invariant         | as 7.5.4: every public statistical callable names a gate, every named gate exists, and every gate is named. Falsified by an unnamed callable, a dangling id, or an orphan gate                                                                                                                                                                                                                                                                    |

### 7.6 Reporting and the README claim

`twinflow-lss validate report` generates `docs/VALIDATION.md` containing every gate with its id,
statistic, reference class, reference (name, locator, edition, license, retrieval date, and
whether the author retrieved it), tolerance, noise floor, falsifier, status, and CI run id.

The README's claim block is generated from the registry, not typed. The generator partitions on
`reference.class` and prints one line per class, so it cannot report a publication where there is
none:

```
Validation, generated from validation/valgates.yaml on every CI run:
  83 registered gates.
  31 checked against published reference values (NIST Statistical Reference Datasets,
     the NIST/SEMATECH e-Handbook, named journal results, and cited quality manuals).
   7 checked against published formulas evaluated independently.
  24 checked against closed-form mathematical results.
  10 checked against the simulation's known injected ground truth.
   1 checked against an independent third-party implementation.
  10 software invariants: determinism, schema conformance, and no-loss behavior.
  See docs/VALIDATION.md for every gate, its reference, and the result that would falsify it.
```

The earlier draft's single sentence, "N of N statistical outputs are validated against published
reference values", was false for at least twelve of its own gates, and the claim that "the claim
can never overstate the evidence because no human writes it" was false too, because a generator
that reads one field and prints one number overstates exactly as reliably as a human would. The
generator now reads `reference.class`, `reference.name` is a required non-null field, and
`test_claim_block_partitions_on_reference_class` asserts that the printed counts sum to the
registry size and that no gate whose class is not `published_reference` is counted in the first
line.

When any gate is deferred, the block gains a line naming each deferral, its origin phase, its new
phase, and its reason. When any gate is `PENDING` because its reference has
`retrieved_by_author: false`, the block gains a line naming those gates and stating that their
expected values have not yet been transcribed from the source.

A CI badge reflects the gate suite's status independently of the ordinary test suite, so
"validated" and "green build" stay distinguishable signals.

### 7.7 Reference data licensing (C11, and the repository's IP hygiene rule)

The NIST Statistical Reference Datasets and the NIST/SEMATECH e-Handbook are US Government works
in the public domain; their datasets and worked values are checked into `validation/data/` with
provenance headers.

Worked-example datasets from paid quality manuals are small factual tables. They are transcribed
with a full citation to the edition and page, and the manual itself is never redistributed. The
same rule governs any vendor documentation example: small datasets, cited by document and page,
never bulk-redistributed. OQ-7 asks whether the owner wants a stricter policy.

No GPL-licensed package's data files are vendored. Where a cross-check against such a package is
wanted, only the scalar expected values are stored, with the citation. OQ-2 covers the one case
this section has.

Every file under `validation/data/` carries a `PROVENANCE.md` line with source, license, and
retrieval date, and the license-compatibility CI job (C11) reads it.

### 7.8 Runtime budgets

D-13 requires a budget derived from measured cost rather than asserted. Each gate's measured
wall-clock cost is recorded in `validation/budget.json` by the CI job that runs it, keyed by gate
id and runner class, with the date and the commit.

`test_tier_budget_arithmetic` sums the recorded costs per tier and asserts the sum is at or below
the tier's declared budget with 20 percent headroom. A gate whose measured cost grows past its
recorded value by more than 50 percent fails the same test and names itself, so a scenario that
grows past its job budget fails as a defect rather than as a timeout.

| Tier                | Declared budget       | Composition                                                                                                                                             |
|---------------------|-----------------------|---------------------------------------------------------------------------------------------------------------------------------------------------------|
| unit                | 60 s                  | 7.1                                                                                                                                                     |
| property            | 180 s                 | 7.2, with a `derandomize` profile in CI and `max_examples` tuned per test                                                                               |
| gate, deterministic | 180 s                 | every gate whose `noise_floor` is null                                                                                                                  |
| gate, Monte Carlo   | 900 s, its own CI job | VG-SPC-11, VG-CAP-04, VG-CAP-06, VG-HYP-17, VG-HYP-18, VG-HYP-19, VG-HYP-22, VG-HYP-23, VG-HYP-24, VG-MSA-08, VG-PM-06, VG-TRD-02, VG-TRD-03, VG-VSM-02 |
| end-to-end          | 600 s                 | 7.3, with alignment sampling capped by `procmine.conformance.alignment_sampling` and the alignment node budget                                          |

Splitting the gate tier in two is the change that makes the arithmetic work. The earlier draft put
14 Monte Carlo gates, including 30 full twin replications and several 20,000-sample coverage runs,
inside a 300 second budget it had no basis for. The Monte Carlo gates now run as their own job with
their own recorded cost, and VG-VSM-02's 30 replications read the checked-in recorded run rather
than executing the twin 30 times, which is what brings it inside any budget at all.

---

## 8. Phase placement

### 8.1 The sequence

| Piece                                                                                                                                                                                                                  | Phase                | Why here                                                                                                                                                                                                                                                        |
|------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|----------------------|-----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| `/schemas/finding/v1.json`, `/schemas/valgate/v1.json`, `/schemas/config/lss.v1.json`, and the common envelope fields of 4.1                                                                                           | P0                   | C3 contracts cannot be retrofitted, and D-07 settles the envelope before schemas freeze. Every producer in every later phase publishes findings; the shape must exist before the first one does                                                                 |
| `/schemas/test_result/v1.json`, `/schemas/contribution_table/v1.json`, `/schemas/process_model/v1.json`, `/schemas/divergence_spec/v1.json`                                                                            | P0                   | Each crosses a package boundary. Authoring them later would mean a major version bump on a subject that already shipped                                                                                                                                         |
| `metrics/registry.yaml`, the flat metric id registry of 6.6                                                                                                                                                            | P0                   | The chart loader enforces metric resolution from P2, so the thing it resolves against has to exist by then. Pulled forward from E26(b)                                                                                                                          |
| Gate registry skeleton, `twinflow-lss validate` CLI, `just phase-gate`, `just defer-gate`, CI wiring                                                                                                                   | P0                   | The rule "no statistic merges without a gate" works only when the registry predates the first statistic. Building it later means back-filling gates, which is how validation claims become theater                                                              |
| `Clock` binding, the `twinflow-rng` stream declarations of 5.14, the no-wall-clock lint applied to these packages                                                                                                      | P0                   | C1 and C2. Retrofitting determinism into a statistics package is a rewrite                                                                                                                                                                                      |
| Package skeletons for the five bricks with independent `pyproject.toml`, README, and CI job, plus the install-alone job of 2                                                                                           | P0                   | A1 and C10. Splitting a monolith later never produces clean boundaries                                                                                                                                                                                          |
| `twinflow-artifact` in full: SVG emitter, HTML renderer, normalization filter                                                                                                                                          | P0                   | Every later artifact renders through it, and its byte-stability property is what VG-DET-01 asserts                                                                                                                                                              |
| `twinflow-findings` in full: factory, policy loader, floors, id computation, sinks, console assignment                                                                                                                 | P1                   | The walking skeleton needs one finding to travel end to end, device to broker to historian to engine to agent to dashboard                                                                                                                                      |
| The query-result recorder in `twinflow-contracts` that mints `query_result_id` (5.9.4)                                                                                                                                 | P1                   | Every finding from P1 carries the field. Pulled forward from E26(f), which adds the checker at P6 and not the id                                                                                                                                                |
| One I-MR chart on one metric, `get_findings` agent tool                                                                                                                                                                | P1                   | One chart proves the path without widening                                                                                                                                                                                                                      |
| Full SPC: all chart types, both rule sets, constants, limit policies, online and batch, all three streams                                                                                                              | P2                   | The source names the LSS engine as Phase 2 and SPC is its base. Everything else in the engine cites SPC                                                                                                                                                         |
| Capability, MSA (all five studies plus attribute agreement), `twinflow_lss.testing.gage_study_generator`, hypothesis layer, Pareto, histogram                                                                          | P2                   | Same phase, and each depends on SPC: capability needs stability, MSA stability needs a chart, hypothesis needs the assumption machinery capability's normality check also uses. The study generator lands here so VG-MSA-08 does not wait on the sensor catalog |
| Alarm management in full, `alarms/consoles.yaml`, `findings/next_tool_policy.yaml`                                                                                                                                     | P2                   | The stream must be rationalized before phase 3 multiplies the producers. Adding alarm management after 60 sensor types are publishing is how real projects end up with alarm floods                                                                             |
| Capability report, sections 1 to 8 and 12                                                                                                                                                                              | P2                   | The source calls it "the artifact a hiring manager actually opens", and E1 pulls forward to just after P2 needing a static artifact to show                                                                                                                     |
| Gates VG-NUM-01 to 04, VG-SPC-01 to 12, VG-CAP-01 to 07, VG-MSA-01 to 08, VG-HYP-01 to 24, VG-CHT-01 to 02, VG-ALM-01 to 04, VG-DET-01 to 02, VG-SCH-01 to 02                                                          | P2                   | P2 cannot close until all of these pass. This is the phase-gate rule's first real test, and the gates whose reference has `retrieved_by_author: false` are the first real test of 7.5.1's `PENDING` rule                                                        |
| Findings stream consumed by the E1 replay viewer; JSONL sink hardened for static hosting with the gzip header rule of 4.8                                                                                              | just after P2        | Per the agreed resequencing, E1 pulls forward. It needs an event log plus a static viewer, and the findings JSONL plus the capability report are exactly that                                                                                                   |
| `twinflow_lss.trend`, time-to-threshold intervals, VG-TRD-01 to 03, `FLEET_HEALTH_DEGRADED` adopting the stream                                                                                                        | P3                   | Predictive maintenance is P3 and consumes the regression core certified in P2 by VG-NUM-03 and VG-NUM-04                                                                                                                                                        |
| VG-MSA-08 re-run against component 2's sensor catalog study producer                                                                                                                                                   | P3                   | Same gate, second source. The assertion does not change                                                                                                                                                                                                         |
| Supplier scorecards on control charts, return reason-code Pareto, forecast bias control chart                                                                                                                          | P3d, P3e, P3f        | Each is a new chart configuration on an existing engine, landing with the subsystem that generates the data. No engine change, which is the payoff for building the chart layer as config                                                                       |
| `twinflow-procmine` in full, plus VG-PM-01 to 07 and `just record-fixtures`                                                                                                                                            | P3c                  | The author's phase order puts process mining and value stream maps at 3c. It needs a rich event log, which arrives once 3b's automation and 3c's flows exist                                                                                                    |
| The discovery recovery benchmark and its published table                                                                                                                                                               | P3c                  | Needs the ground-truth model export from component 1 and a log with enough structure for the miners to get wrong                                                                                                                                                |
| `twinflow-vsm`, current state, VG-VSM-01 to 03                                                                                                                                                                         | P3c                  | Consumes the contribution table directly                                                                                                                                                                                                                        |
| Capability report sections 10 and 11 switch from placeholder to content                                                                                                                                                | P3c                  | The placeholder mechanism of 5.13 means the golden file is stable across the switch                                                                                                                                                                             |
| Future-state map with statistical verdicts attached                                                                                                                                                                    | P3c, extended at P3d | The current state must exist first; the what-if plumbing that generates future states matures with the planning layer                                                                                                                                           |
| `twinflow_lss.batch` golden-batch scoring, in-line SPC at production stages, VG-BAT-01                                                                                                                                 | P3i                  | Upstream production is P3i and is the only consumer                                                                                                                                                                                                             |
| `twinflow_lss.divergence`, residual charts wired to component 6's specs, VG-DIV-01 to 02, report section 9                                                                                                             | with component 6     | The contract and the residual machinery ship at P2; the parameter values arrive with the twin sync connector. Until then, 4.6 states the behavior                                                                                                               |
| `twinflow_lss.sampling` (Z1.4 plans, OC curves, switching rules), VG-SAM-01 to 02                                                                                                                                      | 6a11                 | The QMS layer owns the acceptance-sampling workflow; the engine supplies the mathematics when that layer lands                                                                                                                                                  |
| Attribute agreement analysis pointed at the CV auditor; `SOP_VIOLATION` adopting the stream                                                                                                                            | P4                   | CV auditing is P4. The attribute MSA code ships in P2 but its first real subject arrives here                                                                                                                                                                   |
| CAPA statistical effectiveness verification                                                                                                                                                                            | 6a11                 | The QMS workflow owns the lifecycle; this is the hook                                                                                                                                                                                                           |
| Variance common cause against special cause on general ledger variances                                                                                                                                                | 6a17                 | The finance layer's drill-down is the consumer; the SPC engine is unchanged                                                                                                                                                                                     |
| OCEL writer default flips to true, benchmark flattening rows populate                                                                                                                                                  | 6a5                  | 5.11.1 states why: an OCEL log for object types that do not exist would publish a distortion figure for a flow the twin cannot produce                                                                                                                          |
| Report polish, validation badge, README generated claim block                                                                                                                                                          | P5                   | P5 is polish and the README headline                                                                                                                                                                                                                            |
| E21 decision register binds `decision_register_ref`; E5 binds `autonomy_tier` to the tier model                                                                                                                        | P6                   | The fields exist from v1 (4.3) and carry local values from P2, so binding the register is a value change rather than a schema change                                                                                                                            |
| E26(b) governed semantic layer built on the P0 metric registry; E26(f) grounding checker walks agent answers                                                                                                           | P6                   | Neither adds an identifier. Both add governance over identifiers that already exist                                                                                                                                                                             |
| Model drift control charts (E43), conformal coverage chart (E31), causal layer consuming the hypothesis engine (E30), AI cost per question on a control chart (E45), SOP generation from rationalization records (E24) | P6                   | Each is an E-tier consumer of an engine that already exists                                                                                                                                                                                                     |
| SIPOC and swimlane views in `twinflow-vsm`, `vsm/sipoc.yaml`, VG-SIP-01, VG-SWM-01 to 02, report section 13                                                                                                            | P3c                  | Addition beyond the source, 1.5. Both read the mined model and the recorded log that land at P3c, and both render through the P0 emitter                                                                                                                        |
| `twinflow_lss.ranking`, `/schemas/whatif_ranking/v1.json`, `ranking/criteria.yaml`, VG-RNK-01 to 03, report section 14                                                                                                 | P3d                  | Addition beyond the source, 1.5. A ranking needs at least two competing what-ifs, and the what-if plumbing matures with the planning layer at P3d                                                                                                               |

### 8.2 Resequencing this section asked for, and what it costs

Five dependencies pointed forward in time. None was dropped; each was resolved by moving a
narrow slice earlier or by restating the capability so it does not need the later thing yet.

| Dependency                                                             | Was                                                      | Now                                                                                                              | Cost                                                          |
|------------------------------------------------------------------------|----------------------------------------------------------|------------------------------------------------------------------------------------------------------------------|---------------------------------------------------------------|
| Chart metric resolution against E26(b)                                 | rule enforced at P2, layer at P6                         | flat metric registry at P0, governed layer still at P6                                                           | one YAML file and its schema at P0                            |
| `query_result_id` on every finding                                     | field required at P1, minter at P6                       | content-addressed recorder in `twinflow-contracts` at P1                                                         | about 30 lines and a test                                     |
| Shelve records referencing E5 and E21                                  | both P6, alarm layer P2                                  | fields present from v1, local tier check from P2, register binds at P6                                           | none; the field was always going to be needed                 |
| VG-MSA-08 and S-LSS-02 needing component 2's gage study producer       | gate at P2, producer at P3                               | a statistical fixture generator in this brick at P2, the catalog producer re-runs the same gate at P3            | one generator with no sensor model in it                      |
| VG-VSM-02, VG-PM-05, and P-PM-03 needing the twin inside the gate tier | gate tier importing the twin, which the layering forbids | checked-in recorded run and exported reference model, regenerated by `just record-fixtures` in the container job | fixture files in the repository and a job that refreshes them |

The last one is the load-bearing change. It removes a runtime dependency from the tier that closes
a phase, it makes the gate reproducible on a machine that cannot run the twin, and it is the same
recorded-response pattern D-04 names for any component that cannot be brought inside the
deterministic boundary.

The through-line: everything later phases depend on being right (the finding contract, the
envelope, the determinism seam, the gate registry, the alarm rationalization discipline, the
metric registry) is in P0, P1, or P2, and everything after that is a new configuration or a new
consumer rather than a change to the engine.

---

## 9. Open questions

These are genuine ambiguities in the source, genuine conflicts between locked decisions, or
statistics whose external reference this repository has not yet read. None has been resolved by
invention, and none of them is a capability that was dropped.

OQ-1. The PM4Py development oracle needs a legal read. D-14 settles the runtime question: PM4Py
and pm4pyminimal are AGPL-3.0 at version 2.7.23.3, read from the package index JSON API on
2026-08-09, so neither is a runtime dependency and `twinflow-procmine` implements its own miners
under Apache-2.0. What remains open is the narrower arrangement in 2.4: PM4Py installed in a
development-only CI job, imported by a comparison test, never distributed and never served, so
that VG-PM-03 has an independent implementation to disagree with. That is the ordinary reading of
AGPL section 13, which reaches users interacting over a network with a modified version, and this
job serves nobody. The owner must confirm that reading before release, and must decide whether the
comparison table published from that job counts as distribution of PM4Py's output.

OQ-2. Where the second Gage R and R reference output lives. VG-MSA-02 needs published output for
the interaction error term on the same dataset VG-MSA-01 uses. The R `SixSigma` package is GPL-2,
so its data files cannot be vendored into an Apache-2.0 repository. Two options: transcribe the
AIAG worked-example dataset independently, since it is a small factual table cited by edition and
page, and store only the expected numbers from the second source as scalar expectations with
citations; or drop the second cross-check and rely on one manual's appendix alone. This section
assumes the first. Confirm.

OQ-3. Several control chart constants have no external table this repository has read. The
NIST/SEMATECH e-Handbook publishes `A2`, `D3`, and `D4` for n = 2 to 10, to three decimals, in
section 6.3.2.1 (retrieved 2026-08-09). It publishes no table for `d2`, `d3`, `c4`, `A3`, `B3`, or
`B4`, and no values beyond n = 10. It also carries no worked numeric example for X-bar and R or
X-bar and s limits, and its p chart example uses a constant subgroup size. VG-SPC-02, VG-SPC-04,
and VG-SPC-07 are closed-form or published-formula gates rather than published-reference
gates, and the published-reference count in 7.6 reflects that. A published table covering the full
constant set at n = 2 to 25 exists in the AIAG statistical process control manual and in ASTM and
ISO documents, all sold rather than published openly. The open question is whether the owner wants
to buy one, transcribe the table with its citation, and promote these three gates to
`published_reference`, or leave them as they are with this paragraph as the explanation.

OQ-4. The alarm standards' benchmark values are cited but not verified. EEMUA Publication 191 is
real, is titled "Alarm systems - a guide to design, management and procurement", was first
published in 1999, and is currently in its Fourth Edition, all read from the publisher's product
page on 2026-08-09. ANSI/ISA-18.2 is real and its ISA18 committee scope was read from isa.org on
the same date. Neither body text has been read here, so the widely quoted numbers this section
carries as configured defaults, the flood threshold of 10 alarms in 10 minutes, the manageable
long-run average, and the target share for the top ten contributors, are attributed rather than
asserted, and no gate checks any of them. VG-ALM-02 checks the arithmetic and the denominator, not
the benchmark. The open question is whether the owner buys both documents, transcribes the
benchmark table with its edition and clause, and promotes those numbers from configured defaults
to cited constants. Until then the report caption reads "target from EEMUA 191, edition and clause
to be confirmed", which is honest and slightly embarrassing, which is the correct combination.

OQ-5. No published Pp, Ppk, or Cpm worked example has been retrieved. The e-Handbook's capability
example in section 6.1.6 gives Cp, Cpk, Cpu, Cpl, and the k factor, all of which VG-CAP-01 checks
against printed values. It gives the Cpm formula and no numeric example, and it gives no Pp or Ppk
example at all. VG-CAP-02 and VG-CAP-07 are closed-form gates against the identities
that must hold. A vendor documentation capability example would supply the missing numbers. The
open question is which document, cited by page, and whether the owner accepts the reference-data
policy of 7.7 for it.

OQ-6. No published studentized range table has been retrieved. VG-HYP-12 checks Tukey HSD through
the two-group identity `q(2, df) = sqrt(2) * t(df)`, which is exact and falsifiable but covers
only `k = 2`. Published tables of the studentized range exist in the statistical literature. The
open question is which one to cite and transcribe so the gate covers `k > 2` against printed
values rather than against an identity.

OQ-7. Reference-material policy wording. The brief says "encode the small datasets and cite; do
not bulk-redistribute" for vendor documentation examples. `VALIDATION.md` needs one explicit
policy paragraph a reader can check the repository against. Does the owner want a stricter version,
expected values only with no dataset transcription at all and the test reading a locally provided
file, which is safer but makes those gates unrunnable by a stranger; or the current version, which
keeps `git clone && just validate` working for everyone?

OQ-8. Chart types beyond the three the source names. The source names "I-MR, X-bar/R, p-chart
selection by data type". This section also implements X-bar and s, needed for subgroup sizes of 9
or more where the range approach loses efficiency, a point the e-Handbook makes explicitly in
6.3.2.1; np, c, and u, needed by 6a2's defect PPM and 6a4's reason codes; EWMA and CUSUM, needed
by the locked anomaly-detection decision, which names an EWMA statistical baseline; and Hotelling
T-squared, needed by the corrected source map's mention of multivariate control. Confirm these
belong in the same brick rather than in a separate advanced-SPC package.

OQ-9. Which sigma-level convention leads the README. The source says "sigma level and DPMO"
without stating whether the 1.5 sigma shift is applied. This section reports `z_bench` unshifted,
the within and overall sigma levels unshifted, and `sigma_level_shifted` with the shift, all
recorded, with `sigma_shift: 1.5` as the default. The field naming now matches the convention
VG-CAP-03 validates, so this is a presentation question rather than a correctness one: which of
the three numbers leads a README headline, and does the caption spell out the convention every
time or only once?

OQ-10. Default case notion once the flows multiply. The source says "every pallet/lot is a case".
Once orders (6a3), returns (6a4), cross-dock (6a5), and e-commerce (6a6) exist, a pallet
participates in several object types and any flat case notion distorts the log. This section
writes OCEL 2.0 alongside flat logs and measures the distortion, and the README demo needs one
default flat case notion. Pallet, or order? Pallet matches the source text; order matches what a
process mining audience expects to see.

OQ-11. Does a published-but-unmet certified threshold count as validated? Several nonlinear
Statistical Reference Datasets are built so that reasonable solvers fail from Start 1. Reporting a
per-dataset log relative error table is the honest treatment and is what the collection is for,
and it is not a binary pass. This section treats VG-NUM-04 as passing when every dataset meets its
stated per-dataset floor and the full table is published. Confirm that satisfies the
non-negotiable validation requirement, or whether every dataset must meet a single uniform
threshold.

OQ-12. Multivariate control at 60 to 80 sensor types. A Hotelling T-squared chart needs a stable
covariance estimate, and the dimension grows with the sensor catalog. This section scopes T-squared
to per-equipment sensor groups with an optional PCA reduction and a stated maximum dimension. The
owner may want a different boundary, or may want multivariate monitoring handled entirely by the
anomaly-detection layer rather than by the SPC layer, in which case the two need an explicit
division of labor so the same drift is not reported twice.

OQ-13. The divergence spec's parameter values. 4.6 authors the `DivergenceSpec` contract, 5.2
builds the residual charts, 5.8 states the four-step evaluation, and VG-DIV-01 and VG-DIV-02 gate
it. What component 6 still owes is the numbers: which metrics are monitored, what absolute and
relative magnitude matters for each, and what prediction horizon the twin publishes them at.
Until those arrive, the magnitude filter is skipped and every divergence finding records
`magnitude_enforced: false`, so nobody reads an unfiltered chart firing as a validated divergence.
This is a values question with a stated default behavior, not an undefined capability.

OQ-14. Cpk or Ppk for the capability finding. The two answer different questions, potential
against actual, and vendor convention differs by audience. This section computes both and lets
`capability.cpk_target` and `ppk_target` each trigger the three-band logic of 5.5 step 7
independently. Which one names the finding in the README's example, and which appears in the
headline number?

OQ-15. Where do spec limits come from for a warehouse metric? The source says "against spec limits
defined in config", and a receiving line has no engineering tolerance the way a machined part does.
This section makes `SpecLimits.derivation` a required free-text field and prints it beside every
index, so the number is at least defensible. The open question is whether the repository also
ships a derived spec-limit mode, with the upper limit taken from takt, from the customer
promise time in 6a12, or from a percentile of a golden period, which would make the capability
claim stronger and adds a policy decision the owner may want to make explicitly.

OQ-16. Rationalization authority in a single-maintainer public repository. ISA-18.2 assumes a
cross-functional rationalization team. Proposed substitute: CODEOWNERS on
`alarms/rationalization.yaml` plus a management-of-change issue template that every change to a
record must reference through `moc_ref`, which also feeds 6a15's change management. Confirm that
this is the right level of ceremony for a public repository, or whether a lighter arrangement
is right.

OQ-17. Design of experiments. The source's hypothesis-testing bullet covers comparison of before
and after, not experimental design. A Black Belt toolkit conventionally includes factorial
screening and response surface methods, and E9's optimization engine partly overlaps them. Nothing
about design of experiments appears in the source, so nothing has been invented here. When the
owner wants it, it is a roadmap milestone with a natural home in this brick and a natural
validation reference in the e-Handbook's chapter 5 worked examples, sequenced after E9 so the two
do not duplicate search machinery.

OQ-18. Is the operator console model the right shape? 3.6 and 6.2 introduce consoles with staffed
shifts because the alarm rate metrics are per operator and a rate needs a denominator. That is the
minimum needed to make VG-ALM-02 computable. It is also a small model of a staffing decision that
6a14's workforce layer will model properly. The open question is whether the console's
`staffed_shifts` stays a static config block here or becomes a view over 6a14's roster once
that lands, which would make the alarm rate respond to absenteeism the way it does in a real
building.
