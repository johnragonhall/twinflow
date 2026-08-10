---
title: Human and sustainable
description: Implementation contract for the operator model, ergonomics, safety, rostering, energy, the embedded-carbon ledger and the ESG report.
topic_type: reference
audience: contributors
---

# Human and sustainable: worker safety, ergonomics, Industry 5.0 pillars, carbon and ESG

This section specifies the human layer and the sustainability layer of twinflow. It covers the
operator as a first-class twin resource, ergonomic scoring of every manual task, the fatigue loop
that ties safety to quality, safety event generation and rate tracking, constraint-solved labor
rostering, energy accounting, the embedded-carbon ledger, and the one-command ESG report.

Three rules govern everything below.

First, every number this section produces comes from a published method with a named source and a
test that reproduces that source's own worked example. Where no published source exists for a
coefficient, the coefficient is declared as a model parameter in a model card and is subjected to a
sensitivity analysis, never presented as validated. Where no published source exists for a whole
gate, the gate becomes an open question in section 9 rather than a passing test (D-11).

Second, the human and energy consequences of a change are structural fields on the what-if answer,
not optional commentary, so an implementer cannot ship an answer that omits them.

Third, every claim in this section carries a confidence tier. A claim verified from primary text
ships plainly. A claim resting on a single secondary source ships with the source named in the
sentence that makes the claim. An unverified claim is written as an open question in section 9 and never as
fact. Where a publisher's host refused retrieval, the refusal is stated at the point of use rather
than papered over. Two refusals are recorded up front, because they bound what section 5.3 and section 7.4 can
assert: on 2026-08-09 `cdc.gov` returned HTTP 403 to automated retrieval of DHHS (NIOSH)
Publication 94-110, and `academic.oup.com` returned HTTP 403 to the Folkard and Tucker (2003)
article body.

## Doctrine rulings applied

| Ruling | Where it lands here                                                                                                                    |
| ------ | -------------------------------------------------------------------------------------------------------------------------------------- |
| D-02   | Section 4 envelope, section 3.15, section 5.8, section 5.28: no wall-clock value enters a payload, a hash, or a control decision       |
| D-03   | Section 3.7 `PpeState`, section 3.1 `SkillMatrix`, section 5.22 genealogy walk: no set iteration reaches an event or a hash            |
| D-04   | Section 5.17 and section 6.5: CP-SAT runs one worker, a fixed seed, a deterministic budget, and a branch cap                           |
| D-05   | Section 3.14 INV-ROST-05, section 5.28, section 7.7: byte-identity is claimed on a pinned platform, value-equivalence across platforms |
| D-09   | Section 2 ownership table, section 2.7 protocol registry, section 5.7 `ErgonomicScore`                                                 |
| D-10   | Section 2 extras, section 2.6 historian protocol                                                                                       |
| D-11   | Section 7.4 to section 7.7: every gate names an external reference, a tolerance, a noise floor, and a falsifier                        |

---

## 1. Scope

### 1.1 Numbered requirements covered in full

| Req      | What the source demands                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                               | Where it lands here                                                                                                       |
| -------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------- |
| **6a10** | Ergonomic profile per manual task (load weight, lift height, reach, twist, frequency); NIOSH lifting equation; RULA/REBA-class assessment; computed per-station injury-risk index; per-operator cumulative physical load across a shift; fatigue feeding back into the simulation as rising error and slowdown rates so safety and quality close the loop; near-miss detection from AMR-worker proximity sensor events; Heinrich-pyramid incident generation from near-miss frequency; TRIR-style rate tracking; near-miss Paretos by location and cause from the LSS engine; PPE and posture spot-checks via the CV channel labeled synthetic; ergonomic what-ifs in ROI language (a powered lift aid at station 2, operator rotation every 2 hours) | Section 2.2, section 2.3, section 3.2-3.7, section 4.1, section 5.1-5.9, section 6.1-6.3, section 7.2-7.7                 |
| **E6**   | Operators as first-class twin resources with shift patterns, workload and a cross-training matrix; a workload-balance (level loading, heijunka) finding; the agent weighing operator impact in every what-if answer                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                   | Section 2.3, section 3.1-3.3, section 4.1, section 5.2, section 5.10, section 5.11, section 6.1, section 7.2, section 7.8 |
| **E7**   | Energy KPIs from the existing motor-current sensors; energy per pallet; idle-energy waste as an eighth-waste LSS finding; what-if answers reporting the energy delta alongside throughput                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                             | Section 2.5, section 3.9, section 4.1, section 5.12-5.15, section 6.4, section 7.6, section 7.8                           |
| **E23**  | Half-hourly labor requirements derived from the forecast; a constraint-solver roster over skills matrix, shift rules, fairness and predicted absenteeism; the roster feeding the simulation as actual staffing; scored on understaffing cost versus overtime; the existing fatigue model as a constraint                                                                                                                                                                                                                                                                                                                                                                                                                                              | Section 2.4, section 3.8, section 4.1, section 5.16-5.20, section 6.5, section 7.7, section 7.8                           |
| **E17**  | Per-shipment embedded-carbon ledger; cradle-to-gate kgCO2e inherited through the genealogy graph (supplier factors, process energy, GLEC-style transport legs); CBAM-style declarations on cross-border shipments; carbon priced into landed cost so sourcing decisions feel regulation                                                                                                                                                                                                                                                                                                                                                                                                                                                               | Section 2.6, section 3.10-3.12, section 4.1, section 5.21-5.25, section 6.6, section 7.6, section 7.8                     |
| **E39**  | One-command ESG report aggregating Scope 1/2/3 from energy KPIs, transport legs and supplier factors, plus the social metrics already measured (TRIR, training hours, turnover), mapped to ESRS-style disclosure headings with a double-materiality readiness note                                                                                                                                                                                                                                                                                                                                                                                                                                                                                    | Section 2.6, section 3.13, section 4.1, section 5.26-5.29, section 6.7, section 7.6, section 7.8                          |

### 1.2 Requirements this section partially owns and the boundary

| Req                   | Owned here                                                                                                                                                                                                                                                                                                        | Owned elsewhere                                                                              |
| --------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------- |
| **2b** sensor catalog | The safety and compliance category (worker proximity, PPE compliance via CV, fall detection, e-stop status, machine guard, smoke, gas leak, CO) and the electrical and power category's consumption side (voltage, current, power meter, power factor, smart meter, battery SOC/SOH, UPS status) as energy inputs | Catalog schema, signal models, failure signatures and UNS topic mapping (sensor section)     |
| **4** CV auditing     | The PPE-compliance and posture-sample audit jobs, their finding types and their agreement metric against sim ground truth                                                                                                                                                                                         | Frame rendering, detector, tracker, SOP rule engine (`twinflow-vision`)                      |
| **5** LSS engine      | The metrics this section feeds it (TRIR on a u-chart, near-miss Pareto, energy per pallet on an I-MR chart, cumulative-load capability against an action limit) and the safety severity floor                                                                                                                     | Chart implementations, rule evaluation, hypothesis tests, capability report (`twinflow-lss`) |
| **1b** automation     | The ergonomic score consumed by the slotting objective and the AMR-worker proximity model                                                                                                                                                                                                                         | Slotting optimizer, AMR fleet, dispatch (`twinflow-slotting`, `twinflow-automation`)         |
| **6a14** HR           | The skills and cross-training matrix as the twin resource model, and the roster's consumption of absence predictions                                                                                                                                                                                              | Hiring pipelines, learning curve, attrition model, training records, turnover accounting     |
| **6a17** finance      | The unit costs this section emits (injury direct and indirect cost, energy cost, demand charge, carbon cost, understaffing and overtime cost)                                                                                                                                                                     | GL posting, capex governance, NPV and IRR, variance decomposition                            |
| **E14** tariffs       | CBAM as a trade-policy overlay sharing the HS code and country-of-origin master                                                                                                                                                                                                                                   | Tariff schedule, duty drawback, FTZ, scenario overlays                                       |
| **E38** insurance     | TRIR and loss history as the premium driver                                                                                                                                                                                                                                                                       | Claims cycle, business-interruption coverage                                                 |
| **E40** weather       | Slip risk and HVAC load as consumers of the shared weather state                                                                                                                                                                                                                                                  | Weather state generator                                                                      |

### 1.3 Requirements this section deliberately does not touch

Process mining, VSM generation, forecasting model selection, MEIO, the agent's accuracy stack, the
dashboard shell, and the deployment tiers. This section registers tools, metrics, findings, panels
and config against those subsystems' contracts and nothing more.

---

## 2. Packages

Five packages. Each installs alone, each has its own README, tests and `pip install` path, and none
imports another's internals (A1). Cross-package communication is by versioned event over the schema
registry (C3) or by a provider protocol declared in the protocol registry of section 2.7.

Every public symbol below has exactly one owning package (D-09). Other packages import it and do not
redeclare it. `OperatorImpact` is owned by `twinflow-workforce`, `EnergyDelta` by `twinflow-energy`,
and the value types both of them share with `twinflow.agent.whatif_completed` live in
`twinflow-schemas` and are re-exported, so no consumer has to install a producer package to read a
payload type. A CI test walks the import graph and fails on a cycle, and a second asserts that every
name in each package's `__all__` is defined in that package.

Heavy dependencies are extras (D-10). Each package's core install carries `pydantic` and the
twinflow packages named in section 2.1 and nothing else. `ortools` and `jinja2` arrive through extras. The
historian seam is a narrow structural protocol rather than an import: `twinflow-carbon` types its
reader against `HistorianQuery` (section 2.7) and imports the concrete table type only under
`TYPE_CHECKING`, so no columnar library enters the core install. The CI job `brick-installs-alone`
installs each package by itself into a clean environment and imports it, so the take-one-brick claim
is tested rather than asserted.

### 2.1 Dependency graph

```
twinflow-ergonomics   (pure functions; no twinflow dependencies)
        ^
        |  provider protocol (ErgonomicScore, section 2.7)
        |
twinflow-workforce    -> twinflow-kernel, twinflow-schemas
                          extras: [ergonomics] adds twinflow-ergonomics
                                  [cv] adds the PPE and posture ingestion path
                                  [roster] adds the roster staffing loader
        ^
        |  events: twinflow.roster.published, twinflow.workforce.absenteeism_predicted
        |
twinflow-roster       -> twinflow-schemas, twinflow-kernel
                          extras: [solver] adds ortools
                          (does NOT import twinflow-workforce)

twinflow-energy       -> twinflow-kernel, twinflow-schemas
twinflow-carbon       -> twinflow-schemas, twinflow-kernel
                          extras: [report] adds jinja2
                                  [historian] adds the twinflow-storage adapter
                          (reads the historian through HistorianQuery; imports no producer package)
```

`twinflow-workforce` depends on `twinflow-ergonomics` only through the `[ergonomics]` extra. That is
the shape roadmap CD2 forces: `twinflow-workforce` lands at P3b with E6, while the scoring library
lands at 6a10, so a core install that named it would be uninstallable for two phases. Without the
extra the package still models operators, shifts, skills and workload balance; with it, the fatigue
loop of section 5.6 scores tasks.

`twinflow-roster` and `twinflow-carbon` both depend on `twinflow-kernel` because both draw seeded
randomness: the sample-average-approximation absence scenarios in section 5.19 and the factor-uncertainty
run in section 5.21. Foundations R3 makes `Rng.child(name)` raise `UnregisteredStream` for a name that is
not registered through the `twinflow.rng.streams` entry point, so a package that draws is a package
that registers, and a package that registers depends on the kernel. Section 3.15 is the registration.
Neither package gains any other kernel-facing capability: neither reads a clock, and neither
publishes to the network port.

`twinflow-carbon` reads the historian rather than importing `twinflow-energy` or
`twinflow-workforce`, which is what lets the ESG report run against a directory of Delta tables
produced by someone else's system.

### 2.2 twinflow-ergonomics

Purpose: the published ergonomics assessment methods as pure, side-effect-free functions over
value objects. No clock, no RNG, no simulation, and no file access from inside an assessment
function. This is the brick a safety engineer installs on its own to score a job from a spreadsheet.

File access is confined to one seam. The lookup tables the published methods need are data, and
data has to be read from somewhere, so `tables.py` declares a `TableSource` protocol with one
implementation that reads the package's own read-only data directory and one that reads a
caller-supplied directory. A `TableSet` is loaded once by an explicit call, is frozen, and is passed
into the assessment functions as an argument. No assessment function opens a file, the package never
writes a file, and the nondeterminism lint that forbids ambient I/O inside a sampler holds.
Paths that arrive from configuration (`safety.costs_file`, `energy.tariff_file`,
`carbon.factors_file`, `carbon.cbam.covered_cn_codes`, `esg.output_dir`) are resolved by the config
loader and read or written through the storage port, never by a package function taking a raw path.

```
twinflow_ergonomics/
  units.py            # Metric | Imperial, explicit conversion, no implicit coercion
  profile.py          # ErgonomicProfile and its component value objects
  niosh.py            # revised NIOSH lifting equation (RNLE), FIRWL, STRWL, CLI
  niosh_tables.py     # FM and CM lookup tables, transcribed with provenance headers
  rula.py             # RULA group A/B, tables A/B/C, grand score, action level
  reba.py             # REBA group A/B, tables A/B/C, activity score, risk band
  ocra.py             # OCRA checklist index for repetitive upper-limb work
  pushpull.py         # psychophysical maximum acceptable forces, pluggable table source
  metabolic.py        # Garg metabolic rate prediction, 8-hour and peak criteria
  cumulative.py       # LiFFT cumulative damage, DUET distal upper extremity
  rest.py             # Rohmert rest allowance, recovery-debt integration
  fatigue.py          # alertness trajectory, error and speed multipliers
  index.py            # StationRiskIndex composition and banding
  tables.py           # TableSource protocol, TableSet loading, checksum verification
  tables/             # data files with source, edition, transcriber, checksum
```

Public API:

```python
from twinflow_ergonomics import (
    ErgonomicProfile, LiftTask, PostureSample, PushPullTask, RepetitionProfile,
    assess_lift,            # LiftTask            -> LiftAssessment
    assess_lift_multitask,  # list[LiftTask]      -> CompositeLiftAssessment
    assess_rula,            # PostureSample       -> RulaAssessment
    assess_reba,            # PostureSample       -> RebaAssessment
    assess_ocra,            # RepetitionProfile   -> OcraAssessment
    assess_pushpull,        # PushPullTask        -> PushPullAssessment
    metabolic_rate,         # LiftTask sequence   -> MetabolicAssessment
    cumulative_damage,      # list[LiftTask]      -> CumulativeDamage (LiFFT)
    duet_damage,            # list[HandExertion]  -> CumulativeDamage (DUET)
    rest_allowance,         # ExertionSpec        -> RestAllowance
    station_risk_index,     # component scores    -> StationRiskIndex
    load_tables,            # TableSource         -> TableSet, called once by the caller
    FatigueModel,           # stateful trajectory object, injected clock value only
)
```

`FatigueModel` is the one stateful object. It takes time as an explicit argument on every call
rather than reading a clock, which keeps the package free of the kernel and satisfies the
nondeterminism lint by construction.

Optional extras: `[validation]` adds the reference fixture corpus and the gate tests;
`[plots]` adds the RULA and REBA worksheet renderer used by the capability report.

Dependencies: `pydantic`, `numpy`. Nothing else, and no twinflow package.

Consumed by `twinflow-slotting` through the `ErgonomicScore` protocol (section 2.7). Twin-core section 3.9
declares the slotting objective's ergonomic term and twin-core section 5.10 declares the slotting
optimizer that consumes it, behind the config key `slotting.ergonomic_provider`. Roadmap CD2 names
the protocol `ErgonomicScore` and names its two implementations, `HeightWeightPenalty` at P3b and
the lifting-index scorer at 6a10, so `ErgonomicScore` is the spelling this section uses everywhere
and `ErgonomicScorer` appears nowhere. The protocol exists at P3b; this package lands at 6a10 behind
it, which is the answer roadmap CD2 already fixed and which section 8.2 records.

`ErgonomicScore` and twin-core section 3.3's `OperatorProvider` are two protocols, not one. `OperatorProvider`
supplies the twin with an operator reference and a capability figure so `twinflow-twin` runs alone;
`ErgonomicScore` scores a task descriptor against a published method and has no operator identity in
its signature. A single implementation may satisfy both, and none is required to.

### 2.3 twinflow-workforce

Purpose: the operator as a twin resource. Owns E6 in full and the simulation-facing half of 6a10.

```
twinflow_workforce/
  model.py            # Operator, ShiftPattern, SkillMatrix, Certification
  resource.py         # OperatorPool: a kernel-scheduled resource with skill-aware seizing
  assignment.py       # station and task assignment, rotation policies
  fatigue_loop.py     # per-task load accumulation, error and speed multiplier publication
  load.py             # CumulativeLoadState per operator per shift
  safety/
    proximity.py      # safety fields, separation distance, breach classification
    nearmiss.py       # near-miss synthesis and cause coding
    pyramid.py        # ratio-preset escalation and the independent hazard_rate model
    incidents.py      # 29 CFR 1904 recording criteria, days away, transfer and restriction
    rates.py          # TRIR, DART, LTIFR, severity rate windows
    costs.py          # direct and indirect injury cost from a versioned cost table
  ppe.py              # PPE state, CV check ingestion, agreement metric
  balance.py          # level loading, smoothness index, Yamazumi, unused-talent detection
  impact.py           # OperatorImpact construction for what-if answers
  trajectory.py       # fatigue trajectory precomputation published for the roster (section 5.18)
  providers.py        # AbsenteeismModel and LearningCurve protocols with declared defaults
```

Public API:

```python
from twinflow_workforce import (
    OperatorPool, Operator, ShiftPattern, SkillMatrix,
    FatigueLoop,               # reads twinflow.twin.activity_completed
    SafetyMonitor,             # reads twinflow.twin.amr_state_changed and position updates
    RateWindow,                # TRIR/DART/LTIFR over a window
    BalanceAnalyser,           # level-loading and unused-talent findings
    build_operator_impact,     # -> OperatorImpact, the required what-if block
    build_fatigue_trajectory,  # -> twinflow.workforce.fatigue_trajectory_published
)
```

Depends on `twinflow-kernel` (CLOCK, RNG, NETWORK ports) and `twinflow-schemas`. Optional extras:
`[ergonomics]` adds `twinflow-ergonomics` and turns on the scoring half of the fatigue loop (6a10);
`[cv]` adds the PPE and posture ingestion path (P4); `[roster]` adds the loader that turns a
`twinflow.roster.published` payload into an `OperatorPool` staffing plan (ROST).

This package owns every use of `FatigueModel` in the system, including the precomputation the roster
consumes (section 5.18). `trajectory.py` is the only module that constructs one. `twinflow-roster` reads the
resulting event and never constructs a fatigue model, which is what keeps the roster free of both
`twinflow-workforce` and `twinflow-ergonomics`.

Standalone use: with the `[ergonomics]` extra installed, and given a CSV of tasks with ergonomic
profiles and a shift pattern, the package produces cumulative load, a station risk index and a
projected recordable rate without any simulation. That is the "take one brick" story for an EHS team.
Without the extra the same CSV produces the assignment ledger, the shift accounting and the balance
measures, which is the P3b shape.

### 2.4 twinflow-roster

Purpose: E23. A constraint-solver rostering service with an independent feasibility checker.

```
twinflow_roster/
  requirement.py      # forecast -> half-hourly requirement by skill and station
  standards.py        # labor standards: minutes per unit by activity, measured or declared
  rules.py            # shift rules, rest rules, fairness rules, stability rules as data
  model_cpsat.py      # the CP-SAT model build
  fatigue_tuples.py   # fatigue trajectory event -> forbidden tuples and soft coefficients
  robustness.py       # expected-inflation and sample-average-approximation absence handling
  objective.py        # weighted cost terms and the reported breakdown
  checker.py          # independent hard-constraint verifier, never trusts the solver
  scoring.py          # planned versus realized understaffing, overtime, service
  benchmark.py        # translator for published staff-rostering benchmark instances
```

Public API:

```python
from twinflow_roster import (
    RequirementCurve, build_requirement,   # forecast + standards -> RequirementCurve
    RosterProblem, RosterRules, ObjectiveWeights,
    solve_roster,        # RosterProblem -> RosterSolution (status, assignments, breakdown)
    check_roster,        # RosterSolution -> list[ConstraintViolation], empty means feasible
    score_roster,        # planned vs actual -> RosterScore
)
```

Depends on `twinflow-schemas` and `twinflow-kernel`; the `[solver]` extra adds `ortools`. It does
not import `twinflow-workforce` or `twinflow-ergonomics`. It reads
`twinflow.forecast.horizon_published` and `twinflow.workforce.fatigue_trajectory_published` as
events, takes its worker population from `RosterProblem` data, takes absence probabilities through
the `AbsenteeismModel` protocol, and publishes `twinflow.roster.published`. Those two seams, one
event and one protocol, are what let 6a14 replace both the worker master and the absenteeism model
without touching this package, which is the shape roadmap CD1 and CD3 fix.

The kernel dependency exists for one reason: the sample-average-approximation mode of section 5.19 draws
absence realizations, and foundations R3 needs every draw to come from a registered child stream.
`twinflow-roster` registers the two streams section 3.15 names through the `twinflow.rng.streams` entry
point. It reads no clock and opens no network port. Its two twinflow dependencies are
`twinflow-schemas` and `twinflow-kernel`, and no sentence in this section claims a narrower set. A
caller who supplies pre-drawn absence realizations as data on `RosterProblem` reaches the same
result without the kernel drawing anything, and the `expected_inflation` mode draws nothing at all.

Standalone use: a JSON problem file plus a rules YAML on the command line produces a roster and a
feasibility report. A workforce planner can adopt this brick with no twin at all.

### 2.5 twinflow-energy

Purpose: E7. Turns electrical telemetry into energy, cost, carbon and waste findings.

```
twinflow_energy/
  meters.py           # EnergyMeter definitions, CT ratios, phase, power factor sourcing
  power.py            # current -> power, single and three phase, part-load efficiency curves
  efficiency.py       # motor efficiency tables by class and rating, with provenance
  integrate.py        # power -> interval energy against the sim clock, exact partitioning
  states.py           # asset state tagging: RUNNING_VA, RUNNING_NVA, STARVED, BLOCKED, IDLE, ...
  kpi.py              # energy per pallet, per order, per case, per line; specific energy
  demand.py           # rolling 15-minute kW, monthly peak, demand charge
  tariff.py           # time-of-use energy rate and demand rate from a tariff file
  grid.py             # location-based and marginal grid emission factors by half hour
  waste.py            # idle-energy waste findings, break-even restart analysis
  delta.py            # EnergyDelta construction for what-if answers
```

Public API:

```python
from twinflow_energy import (
    MeterRegistry, EnergyIntegrator, StateTagger,
    EnergyWindow,        # the aggregate published as twinflow.energy.window_closed
    compute_kpis, compute_demand, price_window,
    IdleWasteAnalyser,   # -> finding candidates
    build_energy_delta,  # -> EnergyDelta, the required what-if block
)
```

Depends on `twinflow-kernel`, `twinflow-schemas`. Optional extra `[grid]` ships the emission-factor
tables.

Standalone use: point it at a CSV of motor current readings with a nameplate file and it returns
kWh, cost, peak demand and an idle-waste report.

### 2.6 twinflow-carbon

Purpose: E17 and E39. The embedded-carbon ledger, the transport-leg calculator, CBAM declarations,
carbon in landed cost, and the ESG report generator.

```
twinflow_carbon/
  factors.py          # EmissionFactor registry, data-quality tiers, GWP set selection
  allocation.py       # allocation hierarchy: subdivision, system expansion, mass, energy, economic
  dag.py              # the genealogy DAG walk: topological order, tie-break, memoization
  ledger.py           # LotFootprint inheritance across the genealogy graph
  transport.py        # transport chain element emissions per leg
  shipment.py         # per-shipment ledger assembly
  cbam.py             # covered goods filter, declaration assembly, certificate arithmetic
  pricing.py          # internal carbon price and CBAM cost into landed cost
  scopes.py           # Scope 1, 2 (location and market based), 3 by GHG Protocol category
  esg/
    report.py         # the one-command generator
    esrs_map.py       # datapoint mapping with a standard_version field
    materiality.py    # double-materiality readiness matrix
    gaps.py           # the gaps and assurance register
    templates/        # HTML template, no external assets
```

Public API:

```python
from twinflow_carbon import (
    FactorRegistry, LotFootprint, propagate_footprint,
    TransportLeg, leg_emissions, allocate_vehicle_emissions,
    ShipmentLedger, build_shipment_ledger,
    CbamDeclaration, build_declarations,
    carbon_landed_cost,
    ScopeInventory, build_scope_inventory,
)
from twinflow_carbon.esg import generate_report   # -> EsgReportArtifacts
```

Depends on `twinflow-schemas` and `twinflow-kernel` (RNG only, for the factor-uncertainty stream of
Section 3.15). The historian is reached through the `HistorianQuery` protocol of section 2.7, whose concrete
result type is imported only under `TYPE_CHECKING`, so the columnar reader is an extra and not a
core install (D-10). The `[historian]` extra binds `twinflow-storage` to that protocol and the
`[report]` extra adds `jinja2`. No dependency on any producer package, and no dependency on a graph
library: `dag.py` implements Kahn's algorithm over the node and link records with the total order
Section 5.22 declares, because the walk needs a pinned order that a general-purpose library does not
promise (D-03).

Standalone use: `twinflow-carbon report --historian ./delta --from 2026-01-01 --to 2026-03-31`
generates the ESG artifacts from stored events alone. The `--from` and `--to` arguments are calendar
instants and resolve to sim time through `run.epoch_utc` (section 5.28).

### 2.7 The protocol registry

Cross-package communication is by versioned event or by provider protocol, and only the first half
of that sentence had a compatibility rule. Five protocols carry real contracts: `ErgonomicScore`,
`AbsenteeismModel`, `LearningCurve`, `PushPullTableSource` and `HistorianQuery`. The first two are
named by roadmap CD2 and CD1 and this section uses those spellings and no others. A protocol
signature that changes silently breaks a consumer exactly the way an event field would, and C3's
producer-consumer drift tests cover events only.

`schemas/protocols/<name>/v<major>.<minor>.json` declares each provider protocol as data: its
method names, its argument names and types, its return type, and its version. The rules match C3's.
Within a major version a protocol may gain an optional keyword argument or a new method with a
default implementation, and may not remove or rename anything or change a type. A breaking change is
a major version bump with both versions present for one release.

Two CI tests enforce it, both owned by this section (section 7.9):

- `protocol-registry-matches-code` compares each declared protocol against the runtime
  `typing.Protocol` object by introspection and fails on any difference. It fails when a developer
  edits the Python protocol without editing the registry entry.
- `protocol-consumer-contract` instantiates every shipped implementation of every protocol against
  the declared signature and runs the protocol's own conformance fixture. It fails when an
  implementation satisfies the type checker but returns a value outside the declared range.

The seams that can be events are events. The roster seam is already an event
(`twinflow.workforce.fatigue_trajectory_published`), and section 8.1 records that `ErgonomicScore`
publishes `twinflow.ergonomics.score_computed` alongside its protocol return so a consumer that
prefers the event contract never has to import a protocol at all.

`HistorianQuery` is the narrowest of the five and exists to satisfy D-10. It declares one method,
`query(sql: str, params: Mapping[str, object]) -> Table`, where `Table` is a structural protocol
carrying `column_names`, `num_rows` and `to_pylist`. `twinflow-carbon` types against it and imports
no columnar library, so `pip install twinflow-carbon` pulls `pydantic` and nothing heavy.

---

## 3. Domain model

Every entity is a Pydantic v2 model, frozen where it is configuration and a mutable dataclass where
it is live simulation state. Units are carried in the field name (`_kg`, `_cm`, `_deg`, `_s`, `_kwh`,
`_kw`, `_kgco2e`, `_usd`, `_pct`, `_per_min`) or in a typed `Quantity`. There is no implicit unit and
no silent conversion: `twinflow_ergonomics.units` requires an explicit `Metric` or `Imperial` tag on
construction and raises on a mixed-unit expression, because the NIOSH equation is stated in both
systems with different constants and a silent coercion there produces a plausible wrong number.

Time fields on a model carry seconds and end in `_s`. Configuration keys that a human writes may
carry hours and end in `_h`, because a shift rule reads better in hours than in seconds. The loader
converts `_h` to `_s` at load and records both, and section 6 names the model field each configuration key
fills, so the two spellings can never drift into two meanings.

Six modeling rules apply throughout and are enforced by tests rather than by runtime guards.

1. **Bounds that come from a published method are part of the method, not a clamp.** The NIOSH
   horizontal multiplier is defined as 1.0 below a lower reference distance and 0 above an upper
   cut-off. That is the published function's own definition, it is implemented as the function, and
   the test asserts it against the source. It is not the same thing as clamping a random draw, which
   this section never does.
2. **Stochastic streams get distributions whose support is already correct.** Durations are
   lognormal, gamma, or Weibull. Bounded ratios (error probability, absence probability, PPE
   compliance rate) are beta, or are transformed on the logit scale so the result lands in `(0, 1)`
   by construction. Counts (near misses per shift, absences per roster period) are Poisson or
   negative binomial. No tail is truncated and there is no sigma cap anywhere in this section. A
   threshold that fires a finding is not a clamp: it changes what is reported, never what is
   computed, and section 6 names every such threshold as a threshold rather than as a maximum.
3. **Physical invariants are property assertions.** Energy partitions, carbon conservation through
   genealogy, hours-worked denominators, and roster coverage are all stated as named invariants in
   section 3.14 with a property test in section 7.2, and are never enforced by silently correcting a value at
   runtime.
4. **Allowances use the divisor convention throughout.** Standard time is normal time divided by one
   minus the allowance fraction, which is the convention `people.sustainable_utilization_max` already
   encodes as one minus the allowance sum. The multiplicative convention (normal time times one plus
   the allowance) is not used anywhere in this section. At a total allowance of 0.15 the divisor
   convention gives a factor of 1.17647 and the multiplicative convention 1.15, so the multiplicative
   reading understates labor hours by 2.3 percent, and that difference lands directly in
   understaffing cost. The choice is stated once here and referenced from INV-ROST-01, section 5.16 and section 6.1
   rather than restated.
5. **Every draw names a registered stream.** Foundations R3 makes `Rng.child(name)` raise
   `UnregisteredStream` for an unregistered name, so a stochastic quantity with no stream id is a
   run that does not start. Section 3.15 registers every stream this section draws from.
6. **No iteration order that can reach an event, a hash, or a control decision is a set (D-03).**
   Where set semantics are wanted, the field is a sorted sequence with a stated key and the
   membership test is a comparison against that sequence. Section 3.7's `PpeState` is the case that forced
   the rule: its item lists reach a payload.

### 3.1 Operator, shift pattern, and the skills matrix (E6)

**`Operator`**: `operator_id: str`, `display_name: str` (synthetic, drawn at provisioning from the
name pool on stream `provision.workforce.<operator_id>.display_name`), `hire_sim_time_s: int`,
`role_id: str`, `home_station_id: str | None`,
`skills: dict[str, SkillLevel]`, `certifications: list[Certification]`,
`shift_pattern_id: str`, `anthropometry: Anthropometry`,
`base_speed_factor: float` (1.0 is the standard performance rating),
`base_error_rate: BetaSpec`, `employment: Literal["permanent","temp","agency"]`,
`cost_center_id: str`.

`SkillLevel` is `Literal["none","training","qualified","expert"]` with an ordinal so comparisons are
total. `Certification` is `{cert_id, granted_sim_time_s, expires_sim_time_s | None, issuing_body}`;
an expired certification degrades the corresponding skill to `training` at the instant of expiry, and
that transition is an event, not a recomputation.

`Anthropometry` is `{stature_cm, shoulder_height_cm, knuckle_height_cm, reach_cm, sex_code}`, drawn
at provisioning from the population distribution on stream
`provision.workforce.<operator_id>.anthropometry` (section 3.15). It exists because RULA and REBA posture
angles for a fixed station geometry depend on the person standing at it, so the same station produces
different scores for different operators, which is the point of the layer.

Invariants:

- INV-WF-01, identity: `operator_id` is unique within a run, and every `home_station_id`,
  `role_id`, `shift_pattern_id`, and `cost_center_id` resolves at config load. A dangling reference
  is a load error (C5).
- INV-WF-02, skill monotonicity: a skill level never decreases except through an explicit
  `twinflow.workforce.certification_expired` or `twinflow.workforce.skill_revoked` event. There is no
  implicit decay.

**`ShiftPattern`**: `pattern_id`, `cycle_days: int >= 1`,
`days: list[ShiftDay]` where `ShiftDay` is
`{offset_day, shift_id | None, start_s_of_day, duration_s, breaks: list[BreakSpec]}`,
`rotation: Literal["fixed","forward","backward"]`, `nights_per_cycle: int`.
`BreakSpec` is `{start_offset_s, duration_s, kind: Literal["paid","unpaid","meal"], recovery: bool}`.
A break with `recovery: true` feeds the rest-allowance and fatigue-recovery model; a break that is
merely unpaid does not.

Invariants:

- INV-SHF-01, shift closure: within a cycle, no two `ShiftDay` entries for the same operator overlap
  in absolute sim time, and every break lies strictly inside its shift.
- INV-SHF-02, rest between shifts: consecutive assigned shifts are separated by at least
  `people.rules.min_rest_h`, across the cycle wrap as well (INV-SHF-03). This is an invariant of a
  _published_ roster, not of the
  pattern; a pattern that cannot satisfy it fails validation with the offending pair named.

**`SkillMatrix`**: a sparse matrix over `(operator_id, station_id)` derived from
`Operator.skills` and `catalog/stations_skills.yaml`, exposing
`can_staff(operator_id, station_id, at_sim_time_s) -> bool`,
`qualified(station_id) -> list[operator_id]` in ascending `operator_id` order, and
`depth(station_id) -> int` (how many qualified operators exist). Depth is the resilience number the
cross-training what-if moves. `qualified` returns a sorted sequence rather than a set because
`OperatorPool` iterates it to choose whom to seize, which is a control decision (D-03).

**`CrossTrainingMatrix`**: the same shape with `target_level`, `training_hours_required`,
`training_cost_usd`, and `current_progress_hours`. Cross-training is an investment with a stated
cost, so it can be quoted in the same ROI language as a powered lift aid (section 5.11).

### 3.2 Assignment, rotation, and the assignment ledger (E6, 6a10)

**`StationAssignment`**: `operator_id`, `station_id`, `from_sim_time_s`, `to_sim_time_s | None`,
`source: Literal["roster","rotation_policy","reassignment","overtime_call"]`,
`ergonomic_profile_id` (which profile the operator is actually exposed to at that station).

**`RotationPolicy`**: `policy_id`, `kind: Literal["none","fixed_interval","load_balanced","skill_pull"]`,
`interval_s: int | None`, `eligible_stations: list[station_id]`,
`min_dwell_s` (a rotation shorter than this is refused because handover cost exceeds the benefit),
`handover_time_s: DistributionSpec` (gamma, drawn on `twin.workforce.handover_time`, section 3.15). The
source's "rotate operators across stations every two hours" is
`kind: fixed_interval, interval_s: 7200`, and it is a config value, not a constant in code.

**`AssignmentLedger`**: the append-only record of every assignment interval in a run. It is the join
key between the twin's activity events and this section's load accounting. INV-WF-05, assignment
coverage: at every sim instant, every station whose `staffing.min_operators > 0` and which is in a
running state has at least that many open assignment intervals, or a
`twinflow.workforce.understaffing_opened` event is open for it. Understaffing is always visible as an
event; it is never absorbed silently by slowing the station down.

### 3.3 Ergonomic task descriptors (6a10)

These are the inputs to the published methods. They are pure value objects with no reference to the
twin, which is what lets `twinflow-ergonomics` be installed and used from a spreadsheet.

**`LiftTask`**: `task_id`, `load_kg: float >= 0`,
`h_origin_cm`, `h_dest_cm` (horizontal distance, hand to midpoint between ankles),
`v_origin_cm`, `v_dest_cm` (vertical hand height at origin and destination),
`asymmetry_origin_deg`, `asymmetry_dest_deg` (0 to 180),
`frequency_lifts_per_min: float > 0`, `duration_h: Literal[1, 2, 8]`,
`coupling: Literal["good","fair","poor"]`,
`significant_control_at_destination: bool`,
`one_handed: bool`, `two_person: bool`, `seated: bool`, `restricted_posture: bool`.

The last four exist because the revised NIOSH equation's published applicability conditions exclude
them. `assess_lift` does not silently return a number for an out-of-scope task; it returns a
`LiftAssessment` whose `applicable: false` and whose `exclusions` list names the violated condition
from the Applications Manual. Returning a confident number for a task the method does not cover is
the single most common misuse of the equation and this API makes it impossible.

`vertical_travel_distance_cm` is derived as `abs(v_dest_cm - v_origin_cm)`, not supplied, so it can
never disagree with the endpoints.

**`PostureSample`**: `sample_id`, `taken_sim_time_s`, `station_id`, `operator_id`,
`source: Literal["sim_geometry","cv_estimate","manual"]`,
`upper_arm_deg`, `lower_arm_deg`, `wrist_deg`, `wrist_twist: Literal["mid","near_end"]`,
`neck_deg`, `trunk_deg`, `legs_supported: bool`,
`shoulder_raised: bool`, `arm_abducted: bool`, `arm_supported: bool`,
`trunk_twisted: bool`, `trunk_side_bent: bool`, `neck_twisted: bool`, `neck_side_bent: bool`,
`wrist_deviated: bool`,
`muscle_use: Literal["static","repeated_4_per_min","neither"]`,
`force_load_kg: float`, `force_shock: bool`,
`coupling: Literal["good","fair","poor","unacceptable"]`,
`activity_static: bool`, `activity_repeated: bool`, `activity_unstable: bool`,
`side: Literal["left","right"]`.

One object serves both RULA and REBA because their input sets overlap; each assessor reads the
fields its published worksheet names and ignores the rest. `source` is carried into every downstream
finding so a posture score derived from the synthetic CV channel is never presented as a measured
one.

**`PushPullTask`**: `task_id`, `action: Literal["push","pull"]`,
`initial_force_n`, `sustained_force_n`, `handle_height_cm`, `distance_m`,
`frequency_per_hour`, `duration_h`, `population_percentile_target: float` (default 0.90),
`surface: Literal["smooth","rough"]`, `cart_mass_kg`.

**`RepetitionProfile`** (OCRA): `task_id`, `cycle_time_s`, `technical_actions_per_cycle`,
`net_duration_min`, `force_borg_cr10: float`, `awkward_posture_codes: list[str]`,
`recovery_periods: list[(start_s, duration_s)]`, `additional_factors: list[str]`.

**`HandExertion`** (DUET): `exertion_id`, `peak_hand_force_n`, `repetitions`, `duty_cycle`,
`grip: Literal["power","pinch"]`.

Invariant INV-ERG-01: every descriptor's numeric fields lie in the domain the published method
declares, and the constructor rejects out-of-domain values with a message naming the method and the
declared range. `v_origin_cm = -5` is a data error, not a task with a small multiplier.

### 3.4 Assessment results (6a10)

**`LiftAssessment`**: `task_id`, `applicable: bool`, `exclusions: list[str]`,
`lc_kg` (the load constant actually used), `hm`, `vm`, `dm`, `am`, `fm`, `cm`,
`rwl_origin_kg`, `rwl_dest_kg`, `rwl_kg` (the governing minimum),
`li_origin`, `li_dest`, `li` (lifting index),
`firwl_kg`, `strwl_kg`, `fili`, `stli`,
`method: Literal["rnle_1994"]`, `table_version: str`, `warnings: list[str]`.

Every multiplier is reported, not just the result. A reviewer must be able to see which multiplier
drove the score, because "the lift is bad" is not actionable and "the horizontal multiplier is 0.40
because the reach is 62 cm" is.

**`CompositeLiftAssessment`**: `tasks_ordered: list[task_id]` (by decreasing single-task lifting
index, as the manual's procedure requires), `per_task: list[LiftAssessment]`,
`cli` (composite lifting index), `increments: list[float]`, `method: Literal["cli_1994"]`.

**`RulaAssessment`**: `posture_score_a`, `muscle_score_a`, `force_score_a`, `score_c`,
`posture_score_b`, `muscle_score_b`, `force_score_b`, `score_d`,
`grand_score: int in 1..7`, `action_level: int in 1..4`, `action_text: str`,
`table_versions: {a, b, c}`, `worksheet_trace: list[str]`.

**`RebaAssessment`**: `score_a`, `load_force_score`, `score_b`, `coupling_score`, `score_c`,
`activity_score`, `reba_score: int in 1..15`, `risk_level: int in 0..4`, `action_text`,
`worksheet_trace`.

`worksheet_trace` is an ordered list of the exact table lookups performed. It is what the capability
report renders as a filled RULA or REBA worksheet, and it is what makes a disagreement with a human
assessor resolvable in one reading rather than a debugging session.

**`OcraAssessment`**: `technical_actions_observed`, `reference_actions`, `ocra_index`,
`checklist_score`, `band: Literal["green","yellow","red"]`, `factor_breakdown: dict[str, float]`.

**`PushPullAssessment`**: `initial_force_n`, `sustained_force_n`,
`max_acceptable_initial_n`, `max_acceptable_sustained_n`,
`ratio_initial`, `ratio_sustained`, `acceptable: bool`, `table_source: str`,
`population_percentile: float`. `table_source` is mandatory and has no default, because the
psychophysical tables are a licensed data question (section 9 items 1 and 2) and no assessment may be produced without
recording which table produced it.

**`MetabolicAssessment`**: `predicted_kcal_per_min`, `eight_hour_criterion_kcal_per_min`,
`peak_criterion_kcal_per_min`, `exceeds_eight_hour: bool`, `exceeds_peak: bool`,
`component_breakdown: dict[str, float]` (posture maintenance plus each task component, per the
published additive model).

**`CumulativeDamage`**: `tool: Literal["lifft","duet"]`, `damage: float`,
`damage_by_task: dict[task_id, float]`, `equivalent_risk_pct: float`,
`s_n_curve_id: str`, `moment_arm_source: str`.

**`RestAllowance`**: `required_rest_fraction`, `required_rest_s_per_hour`,
`scheduled_recovery_s_per_hour`, `deficit_s_per_hour`, `method: Literal["rohmert_1973"]`.

Invariants:

- INV-ERG-02, multiplier range: every NIOSH multiplier lies in `[0, 1]`, and
  `rwl_kg == lc_kg * hm * vm * dm * am * fm * cm` to 1e-12.
- INV-ERG-03, index consistency: `li == load_kg / rwl_kg` whenever `rwl_kg > 0`, and `li` is
  reported as infinite (not as a large number, and not clamped) when `rwl_kg == 0`, with
  `warnings` naming the zeroing multiplier.
- INV-ERG-04, monotonicity: `rwl_kg` is non-increasing in horizontal distance, in asymmetry angle,
  and in frequency, and `li` is non-decreasing in load. This is the property the slotting objective
  in twin-core section 5.10 depends on for its ranking to mean anything.
- INV-ERG-05, composite ordering: `cli >= max(stli_i)` for every task in the set. A composite index
  below its worst single task is arithmetically impossible and indicates a task-ordering bug.

### 3.5 Station risk index (6a10)

**`StationRiskIndex`**: `station_id`, `computed_sim_time_s`,
`components: list[ComponentContribution]`, `index: float in [0, 1]`,
`band: Literal["acceptable","investigate","act_soon","act_now"]`,
`governing_component: str`, `method_version: str`, `is_validated_composite: bool`.

**`ComponentContribution`**: `name: Literal["lift","posture_rula","posture_reba","repetition_ocra","pushpull","metabolic","cumulative_lifft","cumulative_duet"]`,
`raw_score: float`, `normalized: float in [0,1]`, `weight: float`, `contribution: float`,
`source_assessment_id: str`.

`is_validated_composite` is a schema constant `false`, so nothing downstream can forget it. Each
component method is validated against its own published source (section 7.4). The act of combining them
into one index on `[0, 1]` is **not** a published method; it is a twinflow model parameter set
declared in `MODEL_CARDS.md` with its weights, its normalization, and a one-way sensitivity analysis
over the weights, enforced by the `model-card-completeness` gate in section 7.9. The banding thresholds map
to the action language the component methods already publish, so the band is defensible even though
the scalar is a modeling choice. The agent must present the band and the governing component, never
the scalar alone, and `agent-answer-contract` in section 7.9 fails an answer that carries `index` without
`band` and `governing_component`, which is the observation that would falsify the claim.

INV-SRI-02, governing component: `governing_component` names the component with the largest
`contribution`, and if any component's own published action level is at its worst band, the index
band is at least `act_soon` regardless of the weighted sum. A composite may not average away a
method that says "change immediately".

### 3.6 Fatigue and cumulative load (6a10)

**`CumulativeLoadState`** (mutable, one per operator per shift instance):
`operator_id`, `shift_instance_id`, `sim_time_s`,
`lifts_performed: int`, `mass_moved_kg: float`, `cumulative_lift_damage: float`,
`cumulative_duet_damage: float`, `time_weighted_rula: float`, `time_weighted_reba: float`,
`metabolic_kcal: float`, `rest_debt_s: float`,
`time_on_task_s: float`, `time_since_break_s: float`,
`peak_index_reached: float`, `by_station: dict[station_id, StationLoadSlice]`.

**`FatigueState`** (mutable, one per operator, spanning shifts):
`operator_id`, `sim_time_s`,
`alertness: float in [0, 1]` (1.0 is the fully rested baseline; the scale is defined in section 5.8 and is
the model's own, not a published index),
`homeostatic_pressure: float`, `circadian_phase_rad: float`,
`sleep_debt_s: float`, `hours_since_shift_start_s: float`,
`consecutive_shifts: int`, `consecutive_nights: int`,
`error_multiplier: float >= 1.0`, `speed_multiplier: float in (0, 1]`,
`model_id: str`, `model_version: str`.

Invariants:

- INV-FAT-01, recovery direction: during a `recovery: true` break or off-shift interval,
  `rest_debt_s` is non-increasing and `alertness` is non-decreasing. During work with no recovery,
  both move the other way. There is no configuration under which working restores alertness.
- INV-FAT-02, multiplier support: `error_multiplier >= 1.0` and `speed_multiplier in (0, 1]` by
  construction, because both are computed as monotone transforms on an unbounded latent fatigue
  variable rather than by clipping. Both equal exactly 1.0 at the rested baseline, which section 5.8 fixes
  by pinning the transform offsets rather than by a special case. The property test drives the latent
  variable across the full float64 exponent range and asserts the bounds hold and that no value is
  ever exactly at a configured ceiling, which is how a clip would be caught.
- INV-FAT-03, monotone accumulation: `cumulative_lift_damage`, `mass_moved_kg`, `lifts_performed`,
  and `metabolic_kcal` are non-decreasing within a shift instance. They reset at shift boundaries;
  `sleep_debt_s` and `consecutive_shifts` do not.
- INV-FAT-04, no free lunch: over a closed shift, the sum of per-station load slices equals the
  shift total for every accumulator, to 1e-9 relative.

### 3.7 Safety entities (6a10)

**`SafetyField`**: `field_id`, `zone_id`, `geometry: Polygon | Corridor`,
`protective_separation_distance_m`, `warning_distance_m`,
`source: Literal["amr_onboard","fixed_scanner","uwb_zone"]`,
`speed_and_separation: bool`. The separation distance is computed, not typed: section 5.9 derives it from
the AMR's declared speed, stopping distance, and reaction time from `catalog/amr_models.yaml`, so
raising `max_speed_mps` in an automation what-if automatically widens the field and changes the
near-miss rate. That coupling is what makes "raise the AMR speed 20 percent" produce a safety number
without anyone wiring one by hand.

**`ProximityEvent`**: `event_id`, `sim_time_s`, `zone_id`, `amr_id`, `operator_id | None`,
`separation_m`, `closing_speed_mps`, `amr_state`, `operator_activity`,
`field_breached: Literal["none","warning","protective"]`,
`amr_response: Literal["none","slow","stop","reroute"]`, `detection_source`.

**`NearMiss`**: `near_miss_id`, `sim_time_s`, `location: LocationRef`, `station_id | None`,
`operators_involved: list[operator_id]`, `equipment_involved: list[str]`,
`cause_code: str`, `cause_group: str`, `severity_potential: Literal["minor","serious","fatal"]`,
`source: Literal["proximity","manual_report","cv_detection","housekeeping_scan"]`,
`triggering_event_ids: list[str]`.

`cause_code` comes from `catalog/safety_causes.yaml`, a versioned closed list with a group column,
which is what makes the near-miss Pareto by cause reproducible rather than free text. The Pareto by
location uses `station_id` when present and `zone_id` otherwise.

**`Incident`**: `incident_id`, `sim_time_s`, `operator_id`, `location`,
`mechanism_code`, `body_part_code`, `nature_code`,
`classification: Literal["first_aid","medical_treatment","loss_of_consciousness",
"significant_diagnosis","restricted_or_transfer","days_away","fatality"]`,
`days_away: int`, `days_restricted: int`,
`escalated_from_near_miss_id: str | None`, `pyramid_model_id: str`,
`direct_cost_usd`, `indirect_cost_usd`, `cost_table_version: str`.

The six classifications after `first_aid` are the six outcomes 29 CFR 1904.7(a) names, in the
regulation's own words: death, days away from work, restricted work or transfer to another job,
medical treatment beyond first aid, loss of consciousness, and a significant injury or illness
diagnosed by a physician or other licensed health care professional. All six are recordable and
`first_aid` is not. The mapping is a table in `catalog/osha_classification.yaml`, not an `if` in
code, and VAL-GATE-SAF-01 checks it against the rule text.

**`RateWindowResult`**: `window_start_s`, `window_end_s`, `hours_worked: float`,
`recordable_cases: int`, `dart_cases: int`, `lost_time_cases: int`, `days_lost: int`,
`trir`, `dart_rate`, `ltifr`, `severity_rate`,
`base_hours: int` (200000 or 1000000, explicit, no default),
`hours_source: Literal["assignment_ledger","roster_planned"]`.

INV-SAFE-01, denominator honesty: `hours_worked` is the sum of realized assignment-interval
durations from the `AssignmentLedger`, never planned roster hours, unless `hours_source` explicitly
says otherwise. A rate computed on planned hours while people worked overtime understates itself,
and the field forces the choice into the open.

INV-SAFE-02, escalation conservation: every `Incident` with a non-null
`escalated_from_near_miss_id` references a `NearMiss` that exists, occurred at or before the
incident, and is referenced by at most one incident.

**`PpeState`**: `operator_id`, `required: list[PpeItem]`, `worn: list[PpeItem]`,
`last_checked_sim_time_s`, `compliance_history: list[PpeCheck]`. Both item lists are sorted by
`PpeItem` code and carry no duplicates, checked on construction. They are sequences rather than sets
because both reach the `twinflow.safety.ppe_checked` payload and set iteration order depends on hash
randomization, which would change the tape between processes (D-03).

**`PpeCheck`** and **`PostureCheck`**: `check_id`, `sim_time_s`, `station_id`, `operator_id | None`,
`channel: Literal["cv"]`, `frame_ref`, `predicted`, `ground_truth`, `confidence`,
`agreement: bool`, `synthetic: true`. `synthetic` is a literal `true` in the schema, not a boolean
field with a default, so no consumer can ever render a CV-derived safety observation without the
synthetic label. That is the source's "labeled as such" requirement made structural.

### 3.8 Rostering entities (E23)

**`LaborStandard`**: `standard_id`, `activity`, `station_id | None`, `skill_id`,
`minutes_per_unit: float > 0`, `allowance_pct: float >= 0`,
`basis: Literal["measured","declared","mtm_style"]`, `source_ref: str`,
`measured_from_run_ids: list[str]`. When `basis: measured` the standard is derived from the twin's
own activity durations at a stated percentile, and the derivation records which runs produced it, so
a standard can be re-derived and diffed rather than trusted.

**`RequirementCurve`**: `curve_id`, `period_start_s`, `period_end_s`, `bucket_s: int` (1800 by
default, the half-hourly requirement the source names),
`buckets: list[RequirementBucket]` where `RequirementBucket` is
`{bucket_index, station_id, skill_id, required_fte: float, driver_volume: float, driver_source}`,
`forecast_run_id`, `standards_version`.

INV-ROST-01, requirement traceability: every bucket's `required_fte` equals
`driver_volume * minutes_per_unit / (1 - allowance_pct) / bucket_minutes` to 1e-9, and
`driver_source` names the forecast horizon event it came from. The divisor form is the convention
Section 3 rule 4 fixes; the multiplicative form appears nowhere. A requirement with no forecast behind it is
a validation error.

**`RosterRules`** (data, not code): `min_shift_s`, `max_shift_s`, `max_consecutive_shifts`,
`min_rest_between_shifts_s`, `max_hours_per_week_s`, `max_nights_per_cycle`,
`weekend_fairness: Literal["none","max_spread","gini_cap"]`,
`overtime_threshold_s`, `overtime_multiplier`,
`stability_window_days` and `max_schedule_changes_within_window`,
`forbidden_sequences: list[list[shift_id]]` (a night followed by a morning is one entry, not a
hardcoded rule),
`skill_requirements: dict[station_id, dict[skill_id, int]]`,
`fatigue_limits: FatigueLimits`.

**`FatigueLimits`**: `max_predicted_cumulative_damage`, `min_predicted_alertness`,
`max_time_weighted_station_risk`, `enforcement: Literal["hard","soft"]`,
`soft_penalty_per_unit_usd`. The source calls the fatigue model a constraint; making the
hard-or-soft choice explicit is what keeps an infeasible roster from being reported as an
optimization failure when it is actually a staffing shortfall (section 5.18).

**`RosterProblem`**: `problem_id`, `horizon: (start_s, end_s)`, `requirement: RequirementCurve`,
`workers: list[WorkerAvailability]`, `shifts: list[ShiftTemplate]`, `rules: RosterRules`,
`objective: ObjectiveWeights`, `absence: AbsenceModelSpec`, `solver: SolverSpec`.

**`WorkerAvailability`**: `operator_id`, `skills`, `contracted_hours_s`,
`unavailable_intervals: list[(start_s, end_s)]`, `preferences: list[Preference]`,
`predicted_absence_p: float in [0,1]`, `history_hours_s`, `history_weekends_worked`,
`history_nights_worked`.

**`ObjectiveWeights`**: `w_understaffing_usd_per_fte_hour`, `w_overstaffing_usd_per_fte_hour`,
`w_overtime_usd_per_hour`, `w_agency_usd_per_hour`, `w_fairness`, `w_preference`,
`w_stability`, `w_fatigue_soft`, `normalization: Literal["none","usd"]`. When
`normalization: usd`, every term must carry a dollar conversion and the validator rejects a
dimensionless weight, because summing a Gini coefficient with a dollar cost is meaningless.

**`RosterSolution`**: `problem_id`, `status: Literal["OPTIMAL","FEASIBLE","INFEASIBLE","UNKNOWN"]`,
`assignments: list[ShiftAssignment]`, `objective_value`,
`objective_breakdown: dict[str, float]`, `coverage_by_bucket: list[float]`,
`solver_version`, `deterministic_time_used`, `branches_used`, `num_workers`, `seed`,
`proof: str | None`. `num_workers` is recorded because D-04 fixes it at one and a solution carrying
any other value is a defect rather than a configuration choice.

**`ConstraintViolation`**: `rule_id`, `severity: Literal["hard","soft"]`, `subject`, `detail`,
`magnitude`. `check_roster` returns a list; an empty list is the only definition of feasible that
this section accepts. The checker never imports the model builder (section 5.20).

**`RosterScore`**: `roster_id`, `planned_vs_realized: dict[str, float]`,
`understaffed_fte_hours`, `overtime_hours`, `agency_hours`, `absence_realized`,
`service_impact: dict[str, float]`, `understaffing_cost_usd`, `overtime_cost_usd`,
`total_cost_usd`, `simulation_run_ids: list[str]`.

INV-ROST-02, coverage arithmetic: for every bucket,
`assigned_fte - required_fte == overstaffing - understaffing`, both non-negative, to 1e-9. The two
never both exceed zero in the same bucket for the same skill.

### 3.9 Energy entities (E7)

**`EnergyMeter`**: `meter_id`, `asset_id`, `kind: Literal["ct_clamp","power_meter","smart_meter","submeter"]`,
`phases: Literal[1, 3]`, `nominal_voltage_v`, `ct_ratio`, `device_id` (the sensor in the 2b catalog),
`power_factor_source: Literal["measured","nameplate","constant"]`, `power_factor_constant: float | None`,
`serves: list[asset_id]`, `parent_meter_id: str | None`, `accuracy_class: float`.

`parent_meter_id` builds a meter tree. INV-ENERGY-02, submeter closure: for every parent, the sum of
child interval energies is less than or equal to the parent's, and the unattributed remainder is
reported explicitly as `unmetered_kwh` rather than being distributed. Silently allocating the
remainder is how energy accounting becomes fiction.

**`MotorNameplate`**: `model_id`, `rated_kw`, `efficiency_class: Literal["IE1","IE2","IE3","IE4","IE5"]`,
`rated_efficiency`, `poles`, `synchronous_rpm`, `full_load_rpm`, `full_load_amps`,
`no_load_amps`, `part_load_curve_id`, `source: str`.

**`PowerSample`**: `meter_id`, `sim_time_s`, `current_a`, `voltage_v`, `power_factor`,
`real_power_kw`, `apparent_power_kva`, `derivation: Literal["measured","computed_1ph","computed_3ph"]`.

**`EnergyInterval`**: `asset_id`, `meter_id`, `start_s`, `end_s`, `kwh`,
`state: AssetEnergyState`, `state_fraction: float`, `method: Literal["trapezoid","step_hold"]`.

**`AssetEnergyState`**: `RUNNING_VA`, `RUNNING_NVA`, `SETUP`, `STARVED`, `BLOCKED`, `IDLE_READY`,
`IDLE_UNPOWERED`, `DOWN`, `CHARGING`. The split between `RUNNING_VA` and `RUNNING_NVA` comes from
the twin's own value-added classification, which is what lets energy join the lean vocabulary rather
than sit beside it.

INV-ENERGY-01 (declared in the shared testkit) applies here: per asset over any window, the state
partitions are exhaustive and disjoint, and total energy equals the sum over assets. INV-ENERGY-03,
state closure: the sum of `state_fraction` over the intervals covering a window equals 1.0 to 1e-12,
computed on integer sim ticks so there is no float drift.

**`EnergyWindow`**: `window_start_s`, `window_end_s`, `by_asset: dict[asset_id, AssetEnergy]`,
`total_kwh`, `by_state_kwh: dict[AssetEnergyState, float]`, `idle_kwh`, `idle_share`,
`kwh_per_pallet`, `kwh_per_order`, `kwh_per_case`, `kwh_per_line`,
`specific_energy_kwh_per_kg_moved`, `peak_demand_kw`, `demand_interval_s`,
`cost_usd`, `energy_cost_usd`, `demand_cost_usd`, `co2e_location_kg`, `co2e_market_kg`,
`grid_factor_source`, `denominator_counts: dict[str, int]`.

`denominator_counts` is present because "energy per pallet" is ambiguous the moment throughput
changes: the numerator and denominator must come from the same window and the same run, and the
count is published so a reader can check.

**`DemandWindow`**: `interval_s` (900 by default), `rolling_kw: list[float]`, `peak_kw`,
`peak_at_sim_time_s`, `billing_period_peak_kw`, `ratchet_pct`, `ratchet_applies: bool`.

**`TariffSchedule`**: `tariff_id`, `currency`, `energy_rates: list[TouRate]`,
`demand_rate_usd_per_kw`, `ratchet: RatchetSpec | None`, `fixed_usd_per_month`,
`source_ref`. `TouRate` is `{name, applies: CalendarPredicate, usd_per_kwh}`; the predicates must
tile the calendar exactly, and a gap or overlap fails validation naming the uncovered interval.

**`GridFactorSeries`**: `region_id`, `basis: Literal["location","market","marginal"]`,
`interval_s`, `kgco2e_per_kwh: list[float]`, `source_ref`, `vintage_year`.

**`IdleWasteCandidate`**: `asset_id`, `window`, `idle_kwh`, `idle_cost_usd`, `idle_co2e_kg`,
`idle_episodes: int`, `median_episode_s`,
`restart_energy_kwh`, `restart_time_s`, `breakeven_idle_s`,
`recoverable_kwh` (idle episodes longer than breakeven), `recommended_action`,
`throughput_risk_s` (the delay a shutdown would add if demand arrives during restart).

**`EnergyDelta`**: `baseline_run_id`, `scenario_run_id`,
`kwh_per_pallet_baseline`, `kwh_per_pallet_scenario`, `delta_pct`,
`total_kwh_delta`, `peak_demand_kw_delta`, `cost_usd_delta_per_year`,
`co2e_kg_delta_per_year`, `by_asset_delta: dict[asset_id, float]`,
`n_replications`, `ci_95: (float, float)`, `provider_present: bool`.

### 3.10 Emission factors and allocation (E17)

**`EmissionFactor`**: `factor_id`, `activity_key`, `unit`, `kgco2e_per_unit`,
`gas_breakdown: dict[Literal["co2","ch4","n2o","other"], float]`,
`gwp_set: Literal["ar4","ar5","ar6"]`, `gwp_horizon_years: Literal[20, 100]`,
`scope_hint: Literal["s1","s2_location","s2_market","s3"]`,
`geography`, `vintage_year`, `data_quality: DataQualityTier`,
`uncertainty: LognormalSpec | None`, `source_ref`, `license`.

`gwp_set` is mandatory with no default. A factor stated under one assessment report's GWP values and
summed with a factor stated under another is a silent error that produces a plausible total, so the
registry refuses to sum across sets and `FactorRegistry.resolve` requires the caller to name the set
(section 5.21).

**`DataQualityTier`**: `technological`, `temporal`, `geographical`, `completeness`,
`reliability`, each an integer 1 to 5, plus a derived `composite: float` and
`uncertainty_gsd: float`. The tiering follows a pedigree-matrix approach and drives the lognormal
geometric standard deviation used in the uncertainty run, which is why factor uncertainty is
lognormal rather than normal: an emission factor is non-negative and multiplicative, and a normal
draw would put mass below zero.

**`AllocationRule`**: `rule_id`, `applies_to: NodeSelector`,
`method: Literal["subdivision","system_expansion","mass","energy_content","economic"]`,
`priority: int`, `justification: str`, `standard_ref: str`. The registry resolves rules in the
hierarchy the standard names, tries subdivision and system expansion first, and records which method
actually applied on every allocated node so a reviewer can see where an economic allocation was used
and why.

### 3.11 The footprint ledger (E17)

**`FootprintComponent`**: `component: Literal["upstream_material","supplier_process","inbound_transport","site_process_energy","site_other","outbound_transport","packaging","waste_treatment"]`,
`kgco2e`, `factor_id`, `activity_amount`, `activity_unit`, `data_quality_composite`,
`allocation_rule_id | None`, `evidence_event_ids: list[str]`.

**`LotFootprint`**: `node_id` (a genealogy node: lot, pallet, carton, or item),
`cradle_to_gate_kgco2e`, `components: list[FootprintComponent]`,
`inherited_kgco2e`, `added_kgco2e`, `mass_kg`, `intensity_kgco2e_per_kg`,
`gwp_set`, `computed_at_sim_time_s`, `completeness_pct`,
`primary_data_share_pct`, `uncertainty_p05_p95: (float, float) | None`.

Invariants:

- INV-CARBON-01 (declared in the shared testkit), conservation through genealogy: for any split, the
  sum of children's `inherited_kgco2e` equals the parent's `cradle_to_gate_kgco2e` allocated by the
  node's active `AllocationRule`, to 1e-9 relative. For any merge, the child's `inherited_kgco2e`
  equals the sum of the parents' contributions, to the same tolerance.
- INV-CARBON-02, no double counting: within one shipment ledger, no `evidence_event_ids` entry
  contributes to two `FootprintComponent` records of the same component type. The test builds a
  diamond genealogy (a lot that splits and re-merges) because that is the shape where naive
  propagation double counts, and it is a shape the returns and kitting flows actually produce.
- INV-CARBON-03, completeness honesty: `completeness_pct` is the mass-weighted share of inputs with
  a resolved factor. A node with unresolved inputs reports a footprint **and** a completeness below
  100, and the report renders both. There is no proxy-factor backfill that hides a gap.

### 3.12 Transport, shipments, and CBAM (E17)

**`TransportLeg`**: `leg_id`, `shipment_id`, `mode: Literal["truck","rail","sea","air","inland_waterway","parcel"]`,
`vehicle_class_id`, `origin: GeoRef`, `destination: GeoRef`,
`distance_km`, `distance_basis: Literal["actual","great_circle_adjusted","routed"]`,
`adjustment_factor`, `payload_t`, `vehicle_capacity_t`, `load_factor`, `empty_running_pct`,
`fuel_type`, `fuel_consumed_l | energy_kwh | null`,
`ttw_kgco2e`, `wtt_kgco2e`, `wtw_kgco2e`,
`factor_id`, `hub_operations_kgco2e`, `refrigeration_kgco2e`,
`allocation: Literal["mass","volume","pallet_slot","chargeable_weight"]`.

The well-to-tank and tank-to-wheel split is carried separately and the total is well-to-wheel,
because the two conventions produce different numbers and a report that states only one without
saying which is not auditable.

INV-CARBON-04, leg allocation: for a vehicle operation carrying multiple shipments, the sum of
per-shipment `wtw_kgco2e` equals the vehicle operation's total to 1e-9, and the allocation basis is
recorded on every leg.

**`VehicleOperationRecord`**: `operation_id`, `vehicle_class_id`, `total_distance_km`,
`total_payload_t`, `total_kgco2e`, `shipments: list[shipment_id]`, `empty_leg: bool`.
Empty running is attributed to the operation, not dropped, and the attribution rule is config.

**`ShipmentLedger`**: `shipment_id`, `order_ids`, `customer_id`, `ship_sim_time_s`,
`lines: list[ShipmentLine]` where each line carries `node_id`, `qty`, `mass_kg`,
`embedded_kgco2e` (from `LotFootprint`),
`transport_legs: list[TransportLeg]`, `packaging_kgco2e`,
`total_kgco2e`, `kgco2e_per_unit`, `kgco2e_per_kg`,
`cross_border: bool`, `origin_country`, `destination_country`,
`declaration_id: str | None`, `gwp_set`, `completeness_pct`.

**`CbamGood`**: `cn_code`, `covered: bool`, `goods_category`, `production_route_id`,
`direct_embedded_tco2e_per_t`, `indirect_embedded_tco2e_per_t`,
`electricity_kwh_per_t`, `electricity_factor_source`,
`carbon_price_paid_origin_usd_per_t`, `installation_ref`.

**`CbamDeclaration`**: `declaration_id`, `period`, `declarant_ref`,
`goods: list[CbamGood]`, `total_direct_tco2e`, `total_indirect_tco2e`,
`certificates_required`, `certificate_price_usd`, `certificate_cost_usd`,
`origin_price_adjustment_usd`, `net_cost_usd`,
`method: Literal["actual","default_values"]`, `standard_version: str`,
`completeness_pct`, `unresolved_inputs: list[str]`.

`method` and `standard_version` are mandatory. A declaration built from default values rather than
actual embedded emissions is a materially different artifact and the field says which it is on every
row.

**`CarbonPrice`**: `price_id`, `kind: Literal["internal_shadow","cbam_certificate","ets_market","offset"]`,
`usd_per_tco2e`, `applies_from_sim_time_s`, `source_ref`.

**`LandedCostCarbonLine`**: `sku_id`, `supplier_id`, `route_id`,
`goods_usd`, `freight_usd`, `duty_usd`, `tariff_usd`,
`carbon_embedded_tco2e`, `carbon_cost_usd`, `cbam_cost_usd`,
`landed_cost_usd`, `landed_cost_with_carbon_usd`, `rank_change_vs_no_carbon: int`.

`rank_change_vs_no_carbon` is the field the sourcing what-if reads. It is the number that makes the
source's "sourcing decisions feel regulation" concrete: a supplier that wins on price and loses once
carbon is priced shows a non-zero rank change, and that is the finding.

### 3.13 ESG reporting entities (E39)

**`ScopeLine`**: `scope: Literal["s1","s2_location","s2_market","s3"]`,
`category: str` (for Scope 3, the numbered value-chain category),
`kgco2e`, `activity_amount`, `activity_unit`, `factor_ids: list[str]`,
`source_events: str` (the historian query that produced it),
`data_quality_composite`, `completeness_pct`, `gwp_set`.

**`ScopeInventory`**: `period`, `organizational_boundary: Literal["operational_control","financial_control","equity_share"]`,
`lines: list[ScopeLine]`, `totals: dict[str, float]`,
`base_year`, `base_year_recalculation_policy`, `intensity_metrics: dict[str, float]`,
`exclusions: list[Exclusion]`. Every exclusion is named with a reason and an estimated magnitude
band; an inventory with silent exclusions is not publishable and the generator refuses to emit one.

**`SocialMetricSet`**: `period`, `headcount_by_type`, `hours_worked`,
`trir`, `dart_rate`, `ltifr`, `severity_rate`, `fatalities`,
`near_miss_count`, `near_miss_reporting_rate`,
`training_hours_total`, `training_hours_per_operator`, `cross_training_depth_mean`,
`turnover_rate`, `regretted_turnover_rate`, `absence_rate`,
`overtime_share`, `schedule_stability_index`, `weekend_frequency_mean`,
`ergonomic_action_stations: int` (stations whose risk band is `act_soon` or worse),
`source_run_ids`.

Every field here is already measured by section 3.1 through section 3.8. The ESG report computes nothing new about
people; it reads what the operation already produced, which is the source's point that the twin
generates a regulatory artifact from data it already holds.

**`EsrsDatapoint`**: `datapoint_id`, `standard: str`, `disclosure_requirement: str`,
`standard_version: str`, `value`, `unit`, `source: Literal["computed","narrative","not_material","not_available"]`,
`computed_from: str | None`, `narrative_ref: str | None`, `assurance_readiness: Literal["ready","partial","not_ready"]`.

**`MaterialityAssessment`**: `topic_id`, `topic_label`,
`impact_score: float`, `impact_rationale`, `impact_evidence_metric: str | None`,
`financial_score: float`, `financial_rationale`, `financial_evidence_metric: str | None`,
`material: bool`, `threshold_used`, `assessed_by: Literal["config","agent_draft"]`.

The matrix is a readiness aid and says so. Materiality is a governance judgment made by an
organization, so `esg.materiality` carries scores as declared config with rationale strings, the
agent may draft rationales from twin evidence, and the artifact is labeled a readiness note rather
than a materiality determination.

**`GapRegisterEntry`**: `datapoint_id`, `gap_kind: Literal["no_data","partial_data","no_method","no_assurance"]`,
`blocking_component`, `estimated_effort`, `owner`, `first_seen_period`.

**`EsgReportArtifacts`**: `report_id`, `period`, `html_path`, `json_path`,
`inventory: ScopeInventory`, `social: SocialMetricSet`,
`datapoints: list[EsrsDatapoint]`, `materiality: list[MaterialityAssessment]`,
`gaps: list[GapRegisterEntry]`, `coverage_pct`, `generator_version`, `run_ids`, `config_hash`.

---

### 3.14 Additional invariants declared by this section

The invariants named in section 5, section 6 and section 7 that are not stated inline above. Each has a property test in
Section 7.2 and each is enforced either at config load (C5) or at runtime.

| Id            | Statement                                                                                                                                                                                                                                                                                                                                                    |
| ------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| INV-SHF-01    | Shift entries within one pattern cycle never overlap                                                                                                                                                                                                                                                                                                         |
| INV-SHF-02    | Consecutive entries are separated by at least `people.rules.min_rest_h`                                                                                                                                                                                                                                                                                      |
| INV-SHF-03    | The rest gap also holds across the cycle wrap, from the last entry to the first entry of the next cycle                                                                                                                                                                                                                                                      |
| INV-ASM-03    | RULA grand score lies in 1 to 7 and REBA score in 1 to 15 for every input in the declared domain, with no lookup failure anywhere in that domain                                                                                                                                                                                                             |
| INV-ASM-04    | Metric and imperial evaluation of the same physical task agree to within 1 percent on the recommended weight limit. The floor is arithmetic: 51 lb is 23.133 kg, so the two published load constants differ by 0.58 percent before any multiplier applies, and a tighter tolerance would fail on a correct implementation                                    |
| INV-FAT-05    | Fatigue multipliers are read once at task start and held constant for that task's duration. Mutating a multiplier mid-task would make the event graph depend on evaluation order and would break C1                                                                                                                                                          |
| INV-FAT-06    | After a full rest opportunity of `people.fatigue.full_recovery_h`, fatigue state returns to baseline within 1e-9, so no float drift accumulates across a long run                                                                                                                                                                                            |
| INV-SAFE-03   | `recordable` is true exactly when the classification is one of the six 29 CFR 1904.7(a) outcomes listed in section 3.7 and false for `first_aid`, matching the recordkeeping definition the rate metrics depend on                                                                                                                                           |
| INV-SAFE-04   | Every rate equals its definition exactly (`trir == recordable_cases * rate_basis_hours / hours_worked`), and a zero denominator yields a null rate rather than a division error or a misleading zero                                                                                                                                                         |
| INV-SRI-01    | The station risk index composite lies in 0 to 1 and its configured weights sum to 1.0 within 1e-9                                                                                                                                                                                                                                                            |
| INV-SRI-02    | If any component exceeds its published action limit, the resulting finding severity is at least `HIGH` regardless of the composite value                                                                                                                                                                                                                     |
| INV-PPE-01    | PPE compliance equals the subset relation between required and worn items                                                                                                                                                                                                                                                                                    |
| INV-PPE-02    | Only PPE items listed in `safety.ppe.observable_from_topdown` may be checked from a top-down synthetic frame. Requesting any other item is a config error at load, not a silent always-compliant answer                                                                                                                                                      |
| INV-PPE-03    | Every artifact carrying a PPE or posture spot check states in visible text that the imagery is synthetic, not only in metadata                                                                                                                                                                                                                               |
| INV-ROST-03   | The independent checker finds zero hard-constraint violations in any published roster                                                                                                                                                                                                                                                                        |
| INV-ROST-04   | Every operator assigned to a station holds the required certification, unexpired at the assignment instant                                                                                                                                                                                                                                                   |
| INV-ROST-05   | On the pinned reference platform, the same instance, seed, solver version and deterministic budget produce a byte-identical roster solution. Across platforms the claim is value-equivalence: identical status, identical objective value, and an identical coverage vector, with any assignment-matrix difference reported rather than asserted away (D-05) |
| INV-ENERGY-04 | Interval energy is never negative, for any input current, power factor or state sequence                                                                                                                                                                                                                                                                     |
| INV-ENERGY-05 | Integrating power over an interval and summing its sub-intervals give the same energy to within 1e-9, independent of how the interval is subdivided                                                                                                                                                                                                          |
| INV-CARBON-05 | Transport leg emissions are non-decreasing in distance and in payload mass, all else equal                                                                                                                                                                                                                                                                   |
| INV-EF-01     | Every emission factor carries a non-empty `source` and an `as_of`. A factor without provenance fails config validation, so no number in the ESG report is untraceable                                                                                                                                                                                        |
| INV-EF-02     | Selecting a factor for a date outside its validity raises a warning finding and downgrades the consuming record's data quality one tier rather than using it silently                                                                                                                                                                                        |
| INV-CBM-01    | Only goods whose CN code is in the configured covered list produce a CBAM declaration                                                                                                                                                                                                                                                                        |
| INV-CBM-02    | Certificates due are never negative. A carbon price paid at origin that exceeds the liability yields zero certificates, never a credit                                                                                                                                                                                                                       |
| INV-CBM-03    | Every declaration names the `regulation_version` it was computed under, so a report regenerated after a rules change is visibly different rather than quietly different                                                                                                                                                                                      |
| INV-ESG-01    | Every datapoint in the configured disclosure map is either populated with a lineage or present in the gaps register with a reason. Silent omission is impossible and a test asserts the partition                                                                                                                                                            |
| INV-ESG-02    | Scope 1 plus Scope 2 plus Scope 3 in the report equals the sum of the underlying ledger entries over the same window, to within 1e-6 relative                                                                                                                                                                                                                |
| INV-ESG-03    | Market-based Scope 2 equals location-based Scope 2 exactly when no contractual instruments are configured                                                                                                                                                                                                                                                    |
| INV-ESG-04    | The report carries no assurance claim. The assurance note states readiness only                                                                                                                                                                                                                                                                              |

### 3.15 The RNG stream registry for this section

Foundations R3 makes an unregistered stream name a run that does not start, so every stochastic
quantity this section produces appears below with its owning package, its family, and its
registration point. Names follow the two forms `variability-and-faults` A.2 fixes:
`<domain>.<subsystem>.<quantity>` for a fixed stream and
`<domain>.<subsystem>.<entity_id>.<quantity>` for a per-entity stream. Per-entity attributes are
drawn at provisioning, before the sim clock advances, from `provision.*` streams, which is what keeps
operator identity constant across the two arms of a paired what-if.

| Stream name                                           | Owner     | Family            | Quantity                                                      |
| ----------------------------------------------------- | --------- | ----------------- | ------------------------------------------------------------- |
| `provision.workforce.<operator_id>.display_name`      | workforce | categorical       | Synthetic name drawn from the shipped pool                    |
| `provision.workforce.<operator_id>.anthropometry`     | workforce | multivariate norm | Stature, shoulder, knuckle, reach                             |
| `provision.workforce.<operator_id>.base_speed_factor` | workforce | lognormal         | Between-operator performance rating                           |
| `provision.workforce.<operator_id>.base_error_rate`   | workforce | beta              | Baseline mispick probability                                  |
| `provision.workforce.<operator_id>.fatigue_suscept`   | workforce | lognormal         | Between-operator fatigue susceptibility (section 5.8)         |
| `provision.workforce.<operator_id>.report_propensity` | workforce | beta              | Near-miss reporting probability (section 5.9)                 |
| `twin.workforce.handover_time`                        | workforce | gamma             | Rotation handover duration (section 3.2)                      |
| `safety.nearmiss.manual_report_arrival`               | workforce | Poisson process   | Manually reported near misses (section 5.9)                   |
| `safety.nearmiss.severity_potential`                  | workforce | categorical       | Minor, serious, or fatal potential per near miss              |
| `safety.escalation`                                   | workforce | Bernoulli         | Escalation of a near miss into an incident (section 5.9)      |
| `safety.incident.<mechanism_code>.days_away`          | workforce | gamma             | Days away by mechanism (section 5.9)                          |
| `safety.incident.<mechanism_code>.days_restricted`    | workforce | gamma             | Days restricted by mechanism                                  |
| `safety.ppe.<station_id>.compliance`                  | workforce | Bernoulli         | Whether a required item is worn at a check                    |
| `safety.ppe.<station_id>.cv_error`                    | workforce | Bernoulli         | Detector disagreement with ground truth (section 5.9)         |
| `safety.posture.<station_id>.cv_angle_error`          | workforce | normal            | Per-joint angle error of the CV estimate                      |
| `roster.absence`                                      | roster    | Bernoulli         | Per-worker absence realization under `saa` (section 5.19)     |
| `roster.absence_correlation`                          | roster    | beta              | Shared shift-level absence correlation term (section 5.19)    |
| `carbon.factor.uncertainty`                           | carbon    | lognormal         | Emission-factor draw under the uncertainty run (section 5.21) |

`twinflow-workforce` registers the first fifteen through the `twinflow.rng.streams` entry point,
`twinflow-roster` the two `roster.*` names, and `twinflow-carbon` the one `carbon.*` name. That is
the whole of the kernel dependency section 2.1 declares for the latter two packages. `twinflow-ergonomics`
registers nothing because it draws nothing; every assessment function is deterministic in its
arguments.

Two streams that a reader might expect are deliberately absent. The energy layer draws nothing:
motor current arrives as telemetry the sensor layer already generated on its own streams, and the
integration in section 5.13 is arithmetic. The ESG report draws nothing: section 5.28 is a pure function of the
historian contents, the config, and the standard version.

---

## 4. Events

Every event below lives in `schemas/<domain>/<event_name>/v<major>.<minor>.json` as JSON Schema
2020-12, is generated from the Pydantic model with the generation checked in CI, and evolves
additively within a major version (C3). Subjects are `twinflow.<domain>.<event_name>`, snake_case,
singular verb-phrase past tense, which is the naming rule foundations section 4.3 fixes for the whole
registry. This section adds seven domains to `schemas/registry.yaml`, each with one owning package:
`workforce` and `ergonomics` and `safety` owned by `twinflow-workforce`, `roster` by
`twinflow-roster`, `energy` by `twinflow-energy`, and `carbon` and `esg` by `twinflow-carbon`.

The envelope is the CloudEvents 1.0 envelope foundations section 3.4 declares, and this section restates
none of it. Three of its properties matter here and are stated once so no payload duplicates them.
`twinflowsimts` is the authoritative timestamp; no payload below carries a second one. `time` is
derived from the wall-clock anchor rather than observed, so no wall clock reaches a payload, a hash,
or a control decision (D-02). `twinflowseq` is dense per `(run_id, producer_id)` and the canonical
total order is `(twinflowsimts, twinflowproducerid, twinflowseq)` (D-07), which is the order every
window aggregation below folds in, so two producers emitting at the same tick cannot reorder a
window total. `twinflowproducerid` is `sim` for every subject in section 4.1 except the ESG report, which
`twinflow-carbon` emits as `cli`.

Two conventions are specific to this section. First, every event that carries a number derived from a
published method also carries `method_id` and `method_version` (for example
`{"method_id": "rnle_1994", "method_version": "1.0.0"}`), so a consumer can tell a NIOSH-grounded
score from a proxy score without inspecting configuration. Second, every event carrying a
human-safety finding from the vision channel carries `synthetic: true` as a schema constant, not
a defaulted field.

### 4.1 Published by this section

| Subject                                           | Ver | Owner     | Key payload fields                                                                                                                                                          | Purpose                                                |
| ------------------------------------------------- | --- | --------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------ |
| `twinflow.workforce.shift_started`                | 1.0 | workforce | `shift_instance_id`, `pattern_id`, `operator_ids`, `planned_hours_s`, `roster_id`                                                                                           | Opens the shift accounting window                      |
| `twinflow.workforce.shift_ended`                  | 1.0 | workforce | `shift_instance_id`, `realized_hours_s`, `overtime_hours_s`, `absences`                                                                                                     | Closes it; feeds the TRIR denominator                  |
| `twinflow.workforce.operator_assigned`            | 1.0 | workforce | `operator_id`, `station_id`, `from_s`, `source`, `ergonomic_profile_id`, `skill_level`                                                                                      | The assignment ledger interval                         |
| `twinflow.workforce.operator_released`            | 1.0 | workforce | `operator_id`, `station_id`, `to_s`, `duration_s`, `handover_s`                                                                                                             | Closes the interval                                    |
| `twinflow.workforce.operator_state_changed`       | 1.0 | workforce | `operator_id`, `station_id`, `alertness`, `error_multiplier`, `speed_multiplier`, `cumulative_lift_damage`, `time_since_break_s`, `model_id`                                | The fatigue loop's published state; the twin reads it  |
| `twinflow.workforce.rotation_applied`             | 1.0 | workforce | `policy_id`, `moves: [{operator_id, from_station, to_station}]`, `handover_cost_s`                                                                                          | Rotation what-if evidence                              |
| `twinflow.workforce.understaffing_opened`         | 1.0 | workforce | `interval_id`, `station_id`, `skill_id`, `required`, `present`, `from_s`                                                                                                    | Understaffing is never silent                          |
| `twinflow.workforce.understaffing_closed`         | 1.0 | workforce | `interval_id`, `to_s`, `duration_s`, `throughput_impact_units`                                                                                                              | The interval's measured cost                           |
| `twinflow.workforce.certification_expired`        | 1.0 | workforce | `operator_id`, `cert_id`, `station_ids_affected`                                                                                                                            | Gates assignment                                       |
| `twinflow.workforce.skill_revoked`                | 1.0 | workforce | `operator_id`, `skill_id`, `reason_code`                                                                                                                                    | The only other way a level drops                       |
| `twinflow.workforce.fatigue_trajectory_published` | 1.0 | workforce | `operator_id`, `horizon_s`, `bucket_s`, `alertness: [float]`, `predicted_damage: [float]`, `model_id`, `model_version`                                                      | The roster's fatigue constraint input                  |
| `twinflow.workforce.balance_window_closed`        | 1.0 | workforce | `window`, `by_station_load_s`, `takt_s`, `smoothness_index`, `yamazumi: [...]`, `imbalance_pct`, `unused_skill_hours`                                                       | Level-loading evidence                                 |
| `twinflow.ergonomics.score_computed`              | 1.0 | workforce | `station_id`, `task_id`, `profile_id`, `li`, `cli`, `rula_grand`, `reba_score`, `ocra_index`, `index`, `band`, `governing_component`, `method_id`, `is_validated_composite` | Read by slotting and the agent                         |
| `twinflow.ergonomics.profile_registered`          | 1.0 | workforce | `profile_id`, `station_id`, `activity`, `descriptor_hash`, `source`                                                                                                         | Ties a profile to a station and makes changes diffable |
| `twinflow.ergonomics.load_window_closed`          | 1.0 | workforce | `operator_id`, `shift_instance_id`, `window`, `lifts`, `mass_moved_kg`, `cumulative_lift_damage`, `time_weighted_rula`, `metabolic_kcal`, `rest_debt_s`                     | Per-operator cumulative load                           |
| `twinflow.safety.proximity_sampled`               | 1.0 | workforce | `amr_id`, `operator_id`, `separation_m`, `closing_speed_mps`, `field_breached`, `amr_response`, `zone_id`                                                                   | Raw safety telemetry join                              |
| `twinflow.safety.near_miss_detected`              | 1.0 | workforce | `near_miss_id`, `location`, `cause_code`, `cause_group`, `severity_potential`, `source`, `triggering_event_ids`                                                             | Pareto input                                           |
| `twinflow.safety.incident_recorded`               | 1.0 | workforce | `incident_id`, `operator_id`, `classification`, `days_away`, `days_restricted`, `mechanism_code`, `escalated_from_near_miss_id`, `pyramid_model_id`                         | Rate numerator                                         |
| `twinflow.safety.incident_costed`                 | 1.0 | workforce | `incident_id`, `direct_cost_usd`, `indirect_cost_usd`, `multiplier_source`, `cost_table_version`                                                                            | Feeds 6a17 and the ergonomic ROI                       |
| `twinflow.safety.rate_window_closed`              | 1.0 | workforce | `window`, `hours_worked`, `hours_source`, `recordable_cases`, `trir`, `dart_rate`, `ltifr`, `severity_rate`, `base_hours`                                                   | LSS u-chart input                                      |
| `twinflow.safety.ppe_checked`                     | 1.0 | workforce | `check_id`, `station_id`, `operator_id`, `required`, `predicted`, `ground_truth`, `agreement`, `confidence`, `synthetic`                                                    | CV agreement metric                                    |
| `twinflow.safety.posture_sampled`                 | 1.0 | workforce | `check_id`, `station_id`, `operator_id`, `angles`, `rula_grand`, `reba_score`, `ground_truth_scores`, `synthetic`                                                           | CV posture spot-check                                  |
| `twinflow.roster.requirement_published`           | 1.0 | roster    | `curve_id`, `bucket_s`, `buckets`, `forecast_run_id`, `standards_version`                                                                                                   | The demand side of E23                                 |
| `twinflow.roster.published`                       | 1.0 | roster    | `roster_id`, `problem_id`, `status`, `assignments`, `objective_value`, `objective_breakdown`, `coverage_by_bucket`, `solver_version`, `deterministic_time_used`, `seed`     | The roster the sim staffs from                         |
| `twinflow.roster.declared_infeasible`             | 1.0 | roster    | `problem_id`, `violations`, `relaxation_suggested`, `binding_rules`                                                                                                         | Infeasibility is an answer, not a crash                |
| `twinflow.roster.scored`                          | 1.0 | roster    | `roster_id`, `understaffed_fte_hours`, `overtime_hours`, `agency_hours`, `understaffing_cost_usd`, `overtime_cost_usd`, `total_cost_usd`, `simulation_run_ids`              | Plan versus realized                                   |
| `twinflow.energy.meter_read`                      | 1.0 | energy    | `meter_id`, `current_a`, `voltage_v`, `power_factor`, `real_power_kw`, `derivation`                                                                                         | The normalized power sample                            |
| `twinflow.energy.window_closed`                   | 1.0 | energy    | full `EnergyWindow`                                                                                                                                                         | The E7 aggregate every consumer reads                  |
| `twinflow.energy.demand_peak_recorded`            | 1.0 | energy    | `interval_s`, `peak_kw`, `peak_at_sim_time_s`, `billing_period_peak_kw`, `ratchet_applies`                                                                                  | Demand charge                                          |
| `twinflow.energy.idle_candidate_found`            | 1.0 | energy    | full `IdleWasteCandidate`                                                                                                                                                   | Becomes the ninth-waste finding of section 5.15        |
| `twinflow.carbon.factor_resolved`                 | 1.0 | carbon    | `activity_key`, `factor_id`, `gwp_set`, `data_quality_composite`, `fallback_used`                                                                                           | Every factor lookup is auditable                       |
| `twinflow.carbon.lot_footprint_computed`          | 1.0 | carbon    | full `LotFootprint`                                                                                                                                                         | The genealogy-inherited ledger                         |
| `twinflow.carbon.leg_computed`                    | 1.0 | carbon    | full `TransportLeg`                                                                                                                                                         | Per-leg emissions on the ISO 14083 basis               |
| `twinflow.carbon.shipment_ledger_built`           | 1.0 | carbon    | full `ShipmentLedger`                                                                                                                                                       | The per-shipment artifact E17 names                    |
| `twinflow.carbon.cbam_declaration_built`          | 1.0 | carbon    | full `CbamDeclaration`                                                                                                                                                      | Cross-border declaration                               |
| `twinflow.carbon.landed_cost_priced`              | 1.0 | carbon    | full `LandedCostCarbonLine`                                                                                                                                                 | Sourcing re-ranking                                    |
| `twinflow.esg.report_generated`                   | 1.0 | carbon    | `report_id`, `period`, `coverage_pct`, `totals`, `gap_count`, `html_path`, `json_path`, `run_ids`, `config_hash`                                                            | The one-command artifact                               |

Thirty-seven subjects, each with one owning package and one row in `schemas/registry.yaml`. The
three subjects a sibling section reads are `twinflow.ergonomics.score_computed` (twin-core's slotting
objective), `twinflow.roster.published` (the ai-layer roster tool and this section's own staffing
loader), and `twinflow.energy.window_closed` (the twin's what-if energy delta). Sibling sections
drafted before the naming rule was settled spell these `ergonomics.score.v1`, `roster.v1` and
`energy.reading.v1`; the registry manifest carries the spellings above and section 9 item 15 records the
reconciliation those sections need.

### 4.2 Consumed

Every row is declared in this section's `consumes.yaml` under the foundations section 4.2 mechanism, so a
row whose subject is not yet in `schemas/registry.yaml` is reported as `pending` and becomes binding
the day its producer registers. The spellings below are the subjects as this section declares them;
where the producing section has not yet registered one, `SCHEMA-6` keeps the entry pending rather
than letting it pass silently.

| Subject                                                                 | Owner        | Used for                                                                                                                            |
| ----------------------------------------------------------------------- | ------------ | ----------------------------------------------------------------------------------------------------------------------------------- |
| `twinflow.twin.activity_started` and `twinflow.twin.activity_completed` | component 1  | Charging ergonomic load to the operator who performed the activity; labor-standard derivation                                       |
| `twinflow.twin.resource_state_changed`                                  | component 1  | Asset energy state tagging; starved and blocked classification for idle waste                                                       |
| `twinflow.twin.pallet_created` and `twinflow.twin.pallet_moved`         | component 1  | Mass moved for cumulative load; the energy-per-pallet denominator                                                                   |
| `twinflow.twin.metrics_window_closed`                                   | component 1  | Throughput denominators, takt for level loading                                                                                     |
| `twinflow.twin.amr_state_changed`                                       | component 1b | AMR position and speed for the proximity model                                                                                      |
| `twinflow.twin.amr_task_completed`                                      | component 1b | AMR travel energy; separation-distance derivation                                                                                   |
| `twinflow.telemetry.sensor_reading`                                     | component 2  | Motor current, voltage, power factor, worker-proximity, PPE-compliance, e-stop, machine-guard, fall-detection, and battery channels |
| `twinflow.fleet.device_health_scored`                                   | component 3  | A degraded current sensor invalidates its energy interval rather than producing a wrong kWh                                         |
| `twinflow.cv.detection_emitted`                                         | component 4  | PPE and posture spot-check ingestion (`[cv]` extra)                                                                                 |
| `twinflow.lss.finding_raised`                                           | component 5  | Safety severity floor coordination; the LSS engine's verdicts on ergonomic what-ifs                                                 |
| `twinflow.forecast.horizon_published`                                   | 6a           | Half-hourly requirement derivation                                                                                                  |
| `twinflow.order.line_shipped`                                           | 6a3 and 6a6  | Shipment ledger assembly; energy per order and per line                                                                             |
| `twinflow.genealogy.node_created` and `twinflow.genealogy.link_created` | 6a11         | The graph the footprint propagates across                                                                                           |
| `twinflow.integration.expected_receipt_published`                       | 6b           | Supplier factors, HS code, country of origin on inbound lots                                                                        |
| `twinflow.workforce.worker_master_published`                            | 6a14         | Worker master data replacing the config-declared roster population                                                                  |
| `twinflow.workforce.absenteeism_predicted`                              | 6a14         | The behavioral `AbsenteeismModel` implementation replacing `ConfiguredRateAbsenteeism` (seam CD1)                                   |
| `twinflow.twin.transport_leg_executed`                                  | 6a7          | Actual mode, distance, payload, and fuel for the leg calculator                                                                     |
| `twinflow.finance.gl_posted`                                            | 6a17         | Cost-table reconciliation for injury, energy, and carbon cost                                                                       |
| `twinflow.twin.weather_state_changed`                                   | E40          | HVAC energy load and the slip-risk near-miss cause                                                                                  |

The last two `workforce` rows are the one place this section both owns a domain and consumes from
it. `twinflow-workforce` owns the `workforce` domain, and 6a14 lands its HR layer inside that same
package rather than adding a domain, which is why the subjects carry the `workforce` prefix and why
`schemas/registry.yaml` lists one owner for them. Until 6a14 lands, neither subject is produced and
neither is needed: `ConfiguredRateAbsenteeism` reads `workforce.absenteeism_rate` from
`facility.yaml` and the worker population is declared in config, which is the early half roadmap CD1
and CD3 fix.

### 4.3 Findings published

This section adds the following members to the `FindingKind` enum in
`schemas/lss/finding_raised/v1.0.json`. Addition is additive under C3, and every kind gets an
alarm-rationalization record before it can be raised (lss-engine section 5.8.2), so none of these can flood
the stream.

| Kind                          | Class      | Floor    | Raised when                                                                                                |
| ----------------------------- | ---------- | -------- | ---------------------------------------------------------------------------------------------------------- |
| `ERGONOMIC_RISK_HIGH`         | safety     | CRITICAL | A station's risk band reaches `act_now`, or any component method reports its worst published action level  |
| `ERGONOMIC_RISK_ELEVATED`     | safety     | HIGH     | Band reaches `act_soon`                                                                                    |
| `LIFT_TASK_OUT_OF_SCOPE`      | quality    | MEDIUM   | A configured lift task violates the equation's published applicability conditions, so no index is reported |
| `CUMULATIVE_LOAD_EXCEEDED`    | safety     | HIGH     | An operator's shift damage crosses the configured action limit                                             |
| `FATIGUE_ERROR_ELEVATED`      | quality    | HIGH     | The fatigue-driven error multiplier exceeds its threshold while quality findings rise on the same station  |
| `NEAR_MISS_RATE_SHIFT`        | safety     | HIGH     | The near-miss u-chart signals a rule violation                                                             |
| `SAFETY_INCIDENT_RECORDABLE`  | safety     | CRITICAL | Any recordable incident                                                                                    |
| `PPE_NONCOMPLIANCE`           | safety     | HIGH     | A PPE check fails against the station's requirement                                                        |
| `PROXIMITY_BREACH_PROTECTIVE` | safety     | CRITICAL | The protective separation field is breached                                                                |
| `WORKLOAD_IMBALANCE`          | production | MEDIUM   | Smoothness index or station imbalance exceeds its threshold                                                |
| `UNUSED_SKILL_CAPACITY`       | cost only  | LOW      | Qualified operators are assigned below their skill for more than a configured share of the shift           |
| `IDLE_ENERGY_WASTE`           | cost only  | MEDIUM   | Recoverable idle energy above the configured threshold, with the restart break-even satisfied              |
| `ENERGY_PER_UNIT_SHIFT`       | production | MEDIUM   | Energy per pallet signals on its I-MR chart                                                                |
| `DEMAND_PEAK_EXCEEDED`        | cost only  | MEDIUM   | Rolling demand exceeds the configured ceiling                                                              |
| `UNDERSTAFFED_INTERVAL`       | production | HIGH     | An open understaffing interval exceeds its duration threshold                                              |
| `ROSTER_INFEASIBLE`           | production | HIGH     | No feasible roster exists under the declared rules                                                         |
| `ROSTER_FATIGUE_BINDING`      | safety     | HIGH     | The fatigue constraint is the binding constraint on coverage                                               |
| `CARBON_DATA_GAP`             | quality    | MEDIUM   | A shipment ledger's completeness falls below its threshold                                                 |
| `CARBON_HOTSPOT`              | cost only  | MEDIUM   | A single component exceeds its share threshold of a shipment footprint                                     |
| `CBAM_DECLARATION_INCOMPLETE` | quality    | HIGH     | A covered good ships without resolvable embedded emissions                                                 |
| `ESG_DISCLOSURE_GAP`          | quality    | MEDIUM   | A mapped datapoint has no computable value at report time                                                  |

The safety class carries the floor lss-engine section 5.8.4 defines, and INV-ALARM-01 in the shared testkit
already asserts that no rationalization, dedupe, or shelving path can suppress a finding at or above
that floor. This section adds no new suppression mechanism, which is the design decision that makes
the source's "safety findings outrank throughput findings by definition" true structurally rather
than by convention.

### 4.4 Fields this section adds to other sections' schemas

Every row is additive within its major version. Each is reserved at the phase in which the target
schema is first registered and filled at the phase that implements it, which is the mechanism roadmap
Section 5.9 defines. Reserving is not deferral: the property exists in the schema from the reserved phase
onward, and CI fails if it is still unpopulated after its filling work package is marked done.

| Schema                             | Field                                                                                   | Reserved at | Filled at |
| ---------------------------------- | --------------------------------------------------------------------------------------- | ----------- | --------- |
| `twinflow.agent.whatif_completed`  | `operator_impact: OperatorImpact \                                                      | null`       | P2        |
| `twinflow.agent.whatif_completed`  | `energy_delta_kwh: float \                                                              | null`       | P2        |
| `twinflow.agent.whatif_completed`  | `energy_delta: EnergyDelta \                                                            | null`       | P2        |
| `twinflow.agent.whatif_completed`  | `carbon_delta: {kgco2e_per_year, per_shipment_mean} \                                   | null`       | P2        |
| `twinflow.lss.finding_raised`      | `carbon_kgco2e: float \                                                                 | null`       | P2        |
| `twinflow.genealogy.node_created`  | `embedded_kgco2e`, `emission_factor_ref`, `hs_code`, `country_of_origin`, `supplier_id` | P3          | ECON      |
| `twinflow.twin.activity_completed` | `operator_id`, `ergonomic_profile_id`, `fatigue_index`                                  | P1          | P3b, 6a10 |
| `station` in the facility schema   | `ergonomic_profile_ref`, `energy: EnergySpec`, `ppe_required`                           | P0          | P3b, 6a10 |
| `twinflow.order.line_shipped`      | `embedded_kgco2e`                                                                       | P3e         | ECON      |

Three of these rows differ from what roadmap section 5.9 currently records and the difference is deliberate.
The roadmap names the scalar `energy_delta_kwh`; this section keeps that scalar as the headline number
and registers the structured `energy_delta` block beside it, because a single float cannot carry the
per-asset breakdown or the confidence interval that section 3.9 declares, and section 9 item 18 records the choice
that would collapse the two back into one. The roadmap reserves the emissions
pair on `twinflow.genealogy.node_created`; this section needs three trade-master fields on the same
schema for CBAM, and reserving them at the same moment costs nothing. The roadmap does not list
`carbon_delta` at all, and because a required property cannot be added after a schema is registered
without a major bump, it has to be reserved at P2 with the other two blocks or it is optional
forever. Section 9 item 17 records that third item as a reconciliation the roadmap owner has to confirm,
because this section cannot amend the reserved-field registry on its own.

---

## 5. Behavior

### 5.1 The human and sustainability layers in one paragraph

The twin publishes an activity; `FatigueLoop` looks up which operator was assigned to that station at
that instant in the `AssignmentLedger`, resolves the station's `ErgonomicProfile`, scores the task
with the pure functions in `twinflow-ergonomics`, adds the result to that operator's
`CumulativeLoadState`, advances the operator's `FatigueState`, and publishes
`twinflow.workforce.operator_state_changed`. The twin reads `speed_multiplier` on the next
service-time draw and
`error_multiplier` on the next quality Bernoulli, which is how a tired picker mispicks more and the
quality findings show it. In parallel, `SafetyMonitor` joins AMR positions to operator positions,
detects separation-field breaches, synthesizes near misses, escalates a fraction of them into
incidents, and publishes rate windows. `twinflow-energy` integrates motor current into interval kWh
tagged by the same asset states the twin already publishes, producing energy per pallet and idle
waste. `twinflow-roster` reads the forecast and produces the staffing plan the next run consumes.
`twinflow-carbon` reads all of it back out of the historian and produces the shipment ledger, the
declarations, and the ESG report. Nothing in that chain reaches into another package's internals;
every arrow is an event in section 4.

### 5.2 Operators, shifts, skills, and assignment (E6)

`OperatorPool` is a kernel-scheduled resource, not a counter. It wraps a
`simpy.PriorityResource` per station and adds skill-aware seizing: a request names a station and a
required skill level, and the pool grants it only to an operator whose `SkillMatrix` entry satisfies
the requirement at the current sim time. Candidates are drawn from `SkillMatrix.qualified`, which
returns a sorted sequence, and the tie between two equally qualified operators breaks on
`operator_id`, so the grant is a deterministic function of state (D-03). A station whose request
cannot be satisfied opens a `twinflow.workforce.understaffing_opened` interval and the twin's station
blocks. It does not silently run unstaffed and it does not silently run slower.

Shift instantiation. At run start the pool expands each `ShiftPattern` across the horizon into
`ShiftInstance` objects with absolute sim times, applying the calendar and the roster if one is
present. Expansion is pure and deterministic: it takes no RNG.
`twinflow.workforce.shift_started` and `twinflow.workforce.shift_ended` bracket every instance, and
the realized hours from the closing event are the TRIR denominator.

Staffing source precedence, resolved once at load and recorded in the run manifest's hashed core:

1. A `twinflow.roster.published` payload for the horizon, when `[roster]` is installed and a roster
   exists.
2. `facility.yaml`'s `people.operators[]` list, or the seeded `people.operator_generator`.
3. The null implementation: one qualified operator per station with `min_operators > 0`, constant
   capability, no fatigue. This is what makes `twinflow-twin` runnable without this section at all
   (A1), and the run manifest records that the null implementation was used so no report claims a human
   model it did not have.

Rotation. When a `RotationPolicy` is active, a rotation tick fires every `interval_s`. For
`fixed_interval` the assignment is a deterministic rotation over `eligible_stations` in a stable
order. For `load_balanced` the pool moves the operator with the highest current
`cumulative_lift_damage` to the eligible station with the lowest `StationRiskIndex` for which that
operator is qualified, breaking ties by `operator_id` so the choice is reproducible. Every rotation
costs `handover_time_s`, drawn from a gamma on `twin.workforce.handover_time` (section 3.15) and charged to
both operators, which is why "rotate every two hours" is not free and the what-if reports a
throughput cost.

Cross-training as a lever. `CrossTrainingMatrix` increments `current_progress_hours` when an
operator works a station at `training` level, and promotes to `qualified` at
`training_hours_required`. Working while training carries a speed penalty and an error penalty from
the same config block that 6a14's learning curve later replaces, and the seam is a protocol
(`LearningCurve` in `providers.py`) whose ROST-era implementation returns the declared config
penalty. When 6a14 lands, the implementation is swapped and a regression test records how much the
numbers moved.

### 5.3 The revised NIOSH lifting equation

`assess_lift` implements the revised equation of Waters, Putz-Anderson, Garg and Fine (1993),
"Revised NIOSH equation for the design and evaluation of manual lifting tasks", _Ergonomics_ 36(7),
749-776, together with the worked procedure of the 1994 Applications Manual, DHHS (NIOSH) Publication
94-110. The form of the computation is:

```
RWL = LC x HM x VM x DM x AM x FM x CM
```

The load constant is a metric value and an imperial value, and the six multipliers are the
functions and lookup tables of those two documents. This specification does not restate their
constants, and no constant appears anywhere in this section, for one reason stated plainly: on
2026-08-09 `cdc.gov` returned HTTP 403 to automated retrieval of Publication 94-110 and the
publisher of the 1993 paper serves it behind a paywall, so no constant in this section would be a
retrieved value. The constants live in exactly one place, the transcription files under
`twinflow_ergonomics/tables/`, each carrying a provenance header naming the publication, the table or
equation number, the transcriber, the transcription date, and a SHA-256 of the value block.
VAL-GATE-ERG-02 is the check that the transcription matches the source, and it is the only place a
number is asserted.

Three properties of the equation's shape are structural rather than numeric and are stated here
because the API depends on them: `HM` and `DM` are declared as 1.0 below a lower reference distance
and 0 above an upper cut-off; `VM` falls linearly away from a reference height and reaches 0 above a
cut-off; `AM` falls linearly with asymmetry angle and reaches 0 above a cut-off. Those are the
published functions' own definitions rather than clamps applied afterwards, which is the distinction
Section 3 rule 1 draws.

`niosh_tables.py` does not compute `FM` or `CM`; it looks them up in `tables/niosh_fm.csv` and
`tables/niosh_cm.csv`. `FM` is keyed by lifts per minute, work duration, and whether the vertical
height is below the reference height; `CM` is keyed by coupling quality and the same vertical split.
Interpolation between published frequency rows is **not** performed. The published table is a step
function over named frequencies and the manual's own instruction is to use the next higher frequency,
so `frequency_lookup` rounds up to the next tabulated row and records that it did.

The equation is evaluated at both the origin and the destination. `rwl_kg` is the lower of the two
when `significant_control_at_destination` is true, and the origin value otherwise, which is the
manual's rule. `li = load_kg / rwl_kg`.

The frequency-independent and single-task forms exist because the composite index needs them:
`FIRWL` is the RWL computed with `FM = 1.0`, `STRWL = FIRWL * FM`, `FILI = load / FIRWL`, and
`STLI = load / STRWL`.

`assess_lift_multitask` computes the composite lifting index by the manual's procedure: order the
tasks by decreasing `STLI`, take `CLI = STLI_1 + sum over i = 2..n of FILI_i * (1/FM_{1..i} -
1/FM_{1..i-1})`, where `FM_{1..i}` is the frequency multiplier evaluated at the summed frequency of
the first `i` tasks. The increments are reported individually in `CompositeLiftAssessment.increments`
because a reviewer needs to see which added task drove the composite up.

Applicability. Before computing anything, `assess_lift` checks the manual's stated conditions:
two-handed, non-seated, unrestricted posture, stable load, moderate temperature, no shoveling or
carrying, no wheelbarrow, no high-speed lifting, and a reasonable coupling. A task failing any of
them yields `applicable: false` with the condition named, and the caller receives no lifting index.
The station using such a task raises `LIFT_TASK_OUT_OF_SCOPE` at MEDIUM rather than being scored
with a number the method does not support.

### 5.4 RULA and REBA

Both are table-driven and both keep the table lookups in data files with the same provenance headers.

RULA (`rula.py`) computes group A from upper arm, lower arm, wrist, and wrist twist, adds the
posture adjustments (shoulder raised, arm abducted, arm supported, wrist deviated) exactly where the
published worksheet adds them, looks the result up in table A, adds the muscle-use and force scores
to get score C. Group B does the same for neck, trunk, and legs to get score D. Table C maps
`(C, D)` to the grand score 1 through 7, which maps to the four published action levels.

REBA (`reba.py`) inverts the grouping: group A is trunk, neck, and legs into table A plus the
load/force score to give score A; group B is upper arm, lower arm, and wrist into table B plus the
coupling score to give score B; table C maps `(A, B)` to score C; the activity score (static hold
over one minute, repeated small-range actions more than four times per minute, or rapid large
postural changes and unstable base) is added to give the REBA score 1 through 15, which maps to the
five published risk levels.

Every lookup appends to `worksheet_trace` as a string of the form
`"table_a[trunk=3,neck=2,legs=2] -> 4"`. The trace is what the capability report renders and what the
validation gate diffs against the published worked examples, so a table transcription error is caught
at the row, not at the grand score where two errors can cancel.

Posture sources. In simulation, angles come from station geometry plus operator anthropometry: a
`PostureGeometry` block on the station declares work-surface height, reach depth, and whether the
task requires trunk rotation, and `posture_from_geometry` produces angles for a given operator. The
CV channel produces the same object with `source: cv_estimate` and its own noise, and section 5.9 measures
the agreement between the two rather than assuming it.

### 5.5 OCRA, push and pull, metabolic rate, and rest allowance

`ocra.py` builds the OCRA checklist index for repetitive upper-limb work: technical actions per
minute against a reference frequency, modified by force, posture, additional-factor, and
recovery-period multipliers, banded into the published three-band scale. It is scored per upper
limb, not per person, because the published method is. This section calls the method OCRA
everywhere; `repetition_checklist` is not a second name for it and appears nowhere, including in
config.

`pushpull.py` compares the task's initial and sustained forces to maximum acceptable forces for a
target population percentile. The tables are a licensing question, so the module defines a
`PushPullTableSource` protocol and ships two implementations: a `ManualTable` reading a user-supplied
CSV with a mandatory `source_ref`, and a `NullTable` that returns no assessment and states why. The
shipped facility profiles use `ManualTable` pointed at a small transcribed extract of the published
tables covering only the geometries the demo actually uses, cited by paper, table, and row. No
assessment is ever produced without a `table_source` string, so a push force can never appear in a
report with no provenance (section 9 items 1 and 2).

`metabolic.py` builds the additive prediction of metabolic rate for manual materials handling of
Garg, Chaffin and Herrin (1978), _American Industrial Hygiene Association Journal_ 39(8), 661-674: a
posture-maintenance component plus a component per task element, each a published regression in body
weight, load, and geometry, summed and divided by the job cycle time. The result is compared to the
published eight-hour and peak criteria, and both comparisons are reported separately because a job
can pass one and fail the other.

`rest.py` builds the Rohmert rest allowance from the relative force and relative holding time,
and integrates the deficit into `CumulativeLoadState.rest_debt_s`. The scheduled recovery from
`BreakSpec` entries with `recovery: true` is subtracted; the remainder is the deficit that drives
fatigue in section 5.8. The Rohmert relationship appears in the literature in more than one transcription,
so the implementation transcribes from the 1973 paper and the gate reproduces the paper's published
values at named points rather than checking an algebraic form taken from a textbook, which is what
VAL-GATE-ERG-09 asserts and why that gate states its digitization error in the fixture header.

`cumulative.py` builds two fatigue-failure tools. LiFFT converts each lift into a peak lumbar
moment from the load and the horizontal distance, converts the moment into a damage increment
through a published S-N curve for the lumbar motion segment, sums the increments across the shift,
and maps the cumulative damage to a probability band. DUET does the same for the distal upper
extremity from hand force and repetition. Both report `damage_by_task`, ranked by contribution,
because the actionable output of a cumulative tool is which tasks dominate the shift total rather
than the total itself. Both name their S-N curve id, so the curve is a stated model input rather than
a constant buried in a function.

### 5.6 Cumulative load across a shift

`load.py` maintains one `CumulativeLoadState` per operator per shift instance. On every
`twinflow.twin.activity_completed` for a manual activity:

1. Resolve the operator from the `AssignmentLedger` at the activity's start time. If no operator was
   assigned, the activity is machine work and no load is charged.
2. Resolve the station's `ErgonomicProfile` and select the descriptor matching the activity's
   `activity` name. A station may declare several (unload uses one lift profile, pick uses another).
3. Score it. Lift descriptors go to `assess_lift`; posture samples go to RULA and REBA; hand
   exertions accumulate for DUET.
4. Add the increments: lift count, mass moved, LiFFT damage, DUET damage, metabolic kcal, and the
   duration-weighted RULA and REBA scores.
5. Attribute the increment to `by_station`, which is what makes the rotation what-if measurable.
6. Publish `twinflow.ergonomics.load_window_closed` at the configured cadence and at every shift
   boundary.

Time-weighting matters and is easy to get wrong. `time_weighted_rula` is the duration-weighted mean
of the grand score over the assignment intervals, not the mean of scores per activity, because a
station worked for six minutes and a station worked for six hours must not contribute equally. The
weighting uses integer sim ticks so INV-FAT-04 closes exactly.

Action limits. `ergonomics.cumulative.damage_action_limit` (section 6.2) declares the shift action limit.
Crossing it raises `CUMULATIVE_LOAD_EXCEEDED` at HIGH, and the LSS engine charts the shift-end
damage distribution against the action limit as a capability study, which is what turns "people are
getting tired" into a Cpk number a plant manager already knows how to read.

### 5.7 The station risk index

`index.py` composes the component assessments into `StationRiskIndex`:

1. Each component method produces its own score on its own scale.
2. Each score is normalized to `[0, 1]` by a declared mapping from that method's own published action
   bands, not by a min-max over observed data. A RULA grand score at the top of its published range
   maps to 1.0 because the method's own action level at that score calls for immediate change, not
   because that score happens to be the maximum seen this shift. This is what keeps the index stable
   across runs and comparable across facilities.
3. The weighted sum is taken on the 0-to-1 scale, with the weights required to sum to 1.0
   (INV-SRI-01), so the composite is a convex combination and cannot leave the unit interval.
4. The band is the worse of the weighted-sum band and the worst component's own published band
   (INV-SRI-02).

The index is recomputed when any of its inputs change: a profile edit, a slotting move that changes
pick height, a load-weight change from the SKU catalog, or a lift-assist scenario. It is published as
`twinflow.ergonomics.score_computed` and read by `twinflow-slotting`'s objective through the
`ErgonomicScore` protocol, which is the seam roadmap CD2 names. The static `HeightWeightPenalty`
implementation that P3b ships is replaced by `NioshLiftingIndexScore` at 6a10, and
`SCN-HS-13` (section 7.8) asserts that the slotting ranking changes when the implementation is swapped on a
fixture where the two disagree, so the seam is proved load-bearing rather than assumed. That is an
end-to-end scenario rather than a validation gate, because the thing it proves is a property of this
repository and D-11 rule 1 bars the repository from being its own published reference.

### 5.8 The fatigue loop

`FatigueModel` advances an operator's `FatigueState` from `t` to `t + dt` given the work performed in
that interval. The state has three drivers:

- **Homeostatic pressure** rises during wake and work and falls during rest, following a two-process
  formulation with an exponential rise and an exponential recovery, each with its own time constant.
- **Circadian phase** is a fixed-period oscillation in absolute sim time, which is what makes a night
  shift worse than a day shift for the same workload and what makes the night-shift roster constraint
  meaningful.
- **Task load** is the within-shift component: rest debt from section 5.5, cumulative damage from section 5.6, and
  time on task since the last recovery break.

The three combine into a latent fatigue variable `z`, zero at the rested baseline and increasing with
fatigue. `alertness` is `exp(-z)`, which places it in `(0, 1]` with 1.0 at the baseline, and that is
the whole definition of the scale section 3.6 refers to here. The two multipliers the twin reads are monotone
transforms of the same variable:

```
speed_multiplier = 2 / (1 + exp(k_s * max(z, 0)))       # in (0, 1], exactly 1.0 at z = 0
error_multiplier = exp(k_e * softplus(z) - k_e * softplus(0))   # >= 1.0, exactly 1.0 at z = 0
```

Both forms have the correct support by construction, which is the rule stated in section 3, and both equal
exactly 1.0 at `z = 0` by the offset in the expression rather than by a special case, which is what
INV-FAT-02 asserts. `k_s` and `k_e` are model parameters with no public source, declared in the model
card section 9 item 5 describes. The error path is applied on the logit scale: a station's base mispick
probability `p0` is a beta parameter from config, and the fatigued probability is
`sigmoid(logit(p0) + log(error_multiplier))`, which stays strictly inside `(0, 1)` for any finite
multiplier. There is no `min(p, 1.0)` anywhere, and the property test in section 7.2 drives `z` across the
full float64 exponent range specifically to catch one if it appears.

Recovery. Off-shift intervals and `recovery: true` breaks reduce homeostatic pressure and rest debt.
Sleep is not simulated in detail; the off-shift interval is treated as a recovery opportunity whose
effectiveness is a config parameter per shift pattern, and `sleep_debt_s` accumulates when the
interval is shorter than the configured requirement. That accumulation is what makes consecutive
night shifts degrade rather than reset, and it is the quantity the roster constrains.

Coupling to the twin. The twin holds only `fatigue_index` on its `Operator` reference (twin-core
Section 3.3) and reads the two multipliers off `twinflow.workforce.operator_state_changed`. The twin never
imports `twinflow-workforce`. When the workforce package is absent, the twin's null implementation
returns constant capability and `mispick` uses the constant rate that planning-supply section 3 already
specifies, with the config flag recorded in the golden file so a reader knows which model produced
the run.

Determinism. `FatigueModel` takes time as an argument on every call and never reads a clock (D-02).
Its only stochastic element, the between-operator variation in fatigue susceptibility, is drawn once
at provisioning from a lognormal on `provision.workforce.<operator_id>.fatigue_suscept` (section 3.15) and
stored on the `Operator`, so the trajectory itself is a deterministic function of the work performed.

### 5.9 Safety events end to end

**Proximity.** `SafetyMonitor` reads `twinflow.twin.amr_state_changed` and operator position, which
is derived from the assignment ledger plus the station and zone geometry the twin already publishes.
At each `safety.proximity.sample_interval_s` it computes pairwise separation for AMR-operator pairs
in the same zone, iterating pairs in `(amr_id, operator_id)` order so the tape does not depend on
container ordering (D-03). The protective separation distance is computed per AMR from a
speed-and-separation
formulation: the distance covered by the AMR during the sensor and control reaction time, plus its
stopping distance at current speed, plus the distance an operator can cover during the same interval
at a configured walking speed, plus intrusion-detection and position-uncertainty terms. The result is
that raising `max_speed_mps` widens the field automatically, so the automation what-if
"raise AMR speed 20 percent" changes near-miss frequency without any separate wiring.

A pair whose separation falls below the warning distance produces a `ProximityEvent` with
`field_breached: warning`; below the protective distance, `field_breached: protective`, which raises
`PROXIMITY_BREACH_PROTECTIVE` at the safety floor and forces the AMR's `amr_response` to `stop`.

**Near misses.** Not every warning breach is a near miss. `nearmiss.py` classifies a breach as a near
miss when the closing speed exceeds a threshold, or when the operator's activity had their attention
elsewhere (a lift with the trunk flexed, per the posture sample), or when the AMR's response was
`none` because it had not detected the operator. The classification produces a `cause_code` from
`catalog/safety_causes.yaml`. Near misses also arrive from three other sources declared in the same
catalog: manual reports, arriving as a Poisson process on `safety.nearmiss.manual_report_arrival`
whose rate is a function of the configured reporting-culture parameter; CV detections, from the PPE
and posture path described below; and housekeeping scans tied to congestion and spill events the twin
already produces. Under-reporting is modeled explicitly: the observed near-miss count is a binomial
thinning of the true count with a reporting probability drawn per operator at provisioning on
`provision.workforce.<operator_id>.report_propensity`, and both counts are recorded so
`SocialMetricSet.near_miss_reporting_rate` is a measured quantity rather than an assumption.

**Escalation.** `pyramid.py` converts near-miss frequency into incidents. The pyramids are data, not
code: `catalog/safety_pyramids.yaml` is an open registry keyed by `pyramid_id`, and every entry
carries its class labels, its ratio row, and a `source_ref` naming an author, a title, an edition or
year, and a page or table locator. `safety.pyramid.preset` (section 6.3) names an entry in that registry.
Two entries ship, `heinrich` and `bird`, whose ratios are transcribed from the primary editions cited
in the file header rather than restated in this specification. No ratio value appears in this
section, because neither primary edition is a document this specification could retrieve, and D-11
rule 5 makes an unretrieved number an open question rather than a fact. Section 9 item 4 records that the
transcription with page locators is a pre-publication task and that the file cannot ship with an
uncited row: `safety-pyramid-provenance` in section 7.9 fails a registry entry whose `source_ref` lacks an
edition or a locator.

Marshall, Hirmas and Singer (2018), "Heinrich's pyramid and occupational safety: A statistical
validation methodology", _Safety Science_ 101, 180-189, is the peer-reviewed anchor for using a
pyramid as a generative device at all. Its abstract states the finding this section relies on: over
more than 50,000 companies observed for 28 months in Chile, the constant-proportion hypothesis is
statistically refuted, but "the discrepancy is so small that, for practical purposes, the pyramid is
valid". That is the strongest claim this section makes for the mechanism, and it is a claim about
proportions holding to a close approximation, never a causal claim (section 9 item 4).

The escalation itself is a hazard model, not a divide. Each near miss carries a
`severity_potential`, and the conditional probability of escalation to each incident class is a
function of that potential, the station's risk band, and the operator's current fatigue state, whose
baseline is calibrated so that a facility running at the model's baseline conditions reproduces the
selected registry entry's ratio to within the Poisson interval VAL-GATE-SAF-05 states. Incident
occurrence is a Bernoulli draw on the child stream `safety.escalation`; the count over a shift is
Poisson-binomial and its overdispersion is real rather than imposed. The pyramid model id is carried
on every incident so an analysis can be redone under a different model without re-running the
simulation.

The correlation is the point. A station whose risk index rises produces more near misses **and** a
higher escalation probability per near miss, so safety degradation compounds the way it does in real
buildings, and the ergonomic what-if's injury-cost-avoided figure has a mechanism behind it rather
than a linear assumption.

**Classification and rates.** `incidents.py` classifies an incident into the seven categories of
Section 3.7 using the table in `catalog/osha_classification.yaml`, assigning days away and days restricted
from gamma distributions on the per-mechanism streams of section 3.15. `rates.py` computes TRIR, DART,
LTIFR, and severity rate over a rolling window with the base-hours constant stated explicitly on
every result. The hours denominator comes from realized assignment intervals (INV-SAFE-01). Rates are
published as `twinflow.safety.rate_window_closed` and the LSS engine charts recordable counts on a
u-chart with hours worked as the area of opportunity, which is the correct chart for a rate with a
varying denominator and is the reason the denominator is carried on the event.

**Paretos.** The near-miss Pareto by location and by cause is produced by the LSS engine from
`twinflow.safety.near_miss_detected` events, grouping on `station_id` or `zone_id` and on
`cause_group`. This section supplies the closed cause list and the location resolution; it does not
build the chart.

**Costs.** `costs.py` assigns a direct cost per incident from a versioned cost table keyed by nature
and body-part code, and an indirect cost through the tiered multiplier VAL-GATE-SAF-02 pins to the
OSHA Safety Pays estimator. Both the table and the multiplier carry `cost_table_version` and a
`source_ref`, and the ergonomic what-if's "injury cost avoided" figure is the difference in expected
annual cost between the two scenarios, computed from the escalation model, with its confidence
interval, never as a point estimate.

**PPE and posture through the vision channel.** With the `[cv]` extra installed, `ppe.py` reads
`twinflow.cv.detection_emitted`. A PPE spot-check compares the detected item list against the
station's `ppe_required` list and produces `twinflow.safety.ppe_checked` with both the prediction and
the simulation's ground truth. Because the frames are synthetic and the ground truth is known, the
interesting output is not the compliance rate but the agreement: `ppe.agreement_window` publishes the
confusion matrix, Cohen's kappa, and the per-item false-negative rate, which is the number an EHS
manager would need before trusting a camera. A posture spot-check does the same for RULA and REBA
angles, reporting the mean absolute angle error per joint and the rate at which the CV-derived grand
score differs from the geometry-derived one by more than one point. Every such record carries
`synthetic: true` as a schema constant, and the dashboard renders the label on the panel, not in a
footnote.

### 5.10 Workload balance and level loading (E6)

`balance.py` computes six quantities per window.

| Quantity           | Definition                                                                                                                                                                    |
| ------------------ | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Station load       | Total operator-seconds of work content per station, from the assignment ledger and the activity durations                                                                     |
| Takt               | Taken from `twinflow.twin.metrics_window_closed`, so the balance analysis and the twin agree by construction                                                                  |
| Yamazumi           | The stacked per-station load bars against takt, published as data for the dashboard                                                                                           |
| Imbalance          | `(max_station_load - mean_station_load) / mean_station_load`                                                                                                                  |
| Smoothness index   | The root of the summed squared deviations of station loads from the maximum, reported beside line efficiency so the two cannot be confused                                    |
| Unused skill hours | Operator-hours worked at a station whose needed skill level is strictly below the operator's highest qualified level, which is the measurable form of the unused-talent waste |

`WORKLOAD_IMBALANCE` is raised when the imbalance exceeds `people.balance.imbalance_threshold` and
the condition persists across `min_consecutive_windows`, so a single unbalanced window from a truck
arrival does not fire. `UNUSED_SKILL_CAPACITY` is raised when unused skill hours exceed a configured
share of the shift. Both findings carry the Yamazumi data as evidence, so the suggested next tool is a
line-balancing what-if with the specific work elements that would move.

Level loading has a direct hook into E23: an imbalance finding raises the requirement curve's
smoothing weight for the next roster solve, so the balance measurement and the staffing decision are
the same loop rather than two reports.

### 5.11 Operator impact on every what-if (E6)

`build_operator_impact(baseline_run, scenario_run) -> OperatorImpact` produces:

`utilization_by_operator: dict[operator_id, float]`, `peak_utilization`,
`peak_utilization_operator_id`, `level_loading_index`, `cumulative_strain_delta`,
`station_risk_index_delta: dict[station_id, float]`, `stations_crossing_band: list[station_id]`,
`headcount_delta_fte`, `overtime_hours_delta`, `predicted_recordable_delta`,
`injury_cost_delta_usd_per_year`, `n_replications`, `ci_95_peak_utilization`,
`note: str | None`, `provider_present: bool`.

The rules that make this structural rather than decorative:

1. `operator_impact` is a required property of `twinflow.agent.whatif_completed`. It is nullable, but
   a null must carry `note: "operator impact not evaluated: provider absent"`. A fabricated zero is a
   contract violation and `whatif-envelope-contract` in section 7.9 fails on one.
2. When any station crosses into a worse risk band, the what-if answer's headline sentence must
   include it. The agent's answer template for `run_whatif` has the operator clause as a required
   slot, and ai-layer's grounding checker refuses a numeric claim with no query-result id behind it,
   so the clause is grounded or the answer does not ship.
3. Peak utilization is reported with its confidence interval across replications. The source's own
   example sentence, that a change raises throughput but pushes an operator to 97 percent utilization
   and is not sustainable at that level, needs the interval to be honest about whether 97 percent is
   distinguishable from 92 percent.

The two named ergonomic what-ifs ship as worked scenarios. `scenarios/lift_assist_station_2.yaml`
patches the station's `ErgonomicProfile` to reduce the load at the operator's hands and raise the
origin height to the presentation height of the powered lift aid, adds that equipment's capex and its
cycle-time penalty, and reports the station risk index delta, the cycle time delta, the throughput
delta with its LSS verdict, the predicted recordable delta, and the injury cost avoided with its
interval. That is the source's "injury-risk index drops X, cycle time changes Y, projected injury cost
avoided is Z" made into fields. `scenarios/rotate_operators_2h.yaml` sets
`RotationPolicy.kind: fixed_interval, interval_s: 7200` and reports the flattening of cumulative
strain across operators, meaning the reduction in the maximum shift-end damage and the change in its
spread, together with the handover throughput cost and the net.

Both feed the same `compare_scenarios` ranking as a throughput investment, ranked by the same
annualized-cost measure twin-core section 9 Q2 defines. A safety investment and a conveyor upgrade appear in
one table, which is the source's Industry 5.0 argument expressed as a data structure.

### 5.12 Metering and power computation (E7)

`power.py` turns a current reading into real power. Three phase, the form Equation 1 of the US
Department of Energy fact sheet DOE/GO-10097-517, _Determining Electric Motor Load and Efficiency_,
states: `P_kw = V * I * PF * sqrt(3) / 1000`, where `V` is the RMS voltage taken as the mean
line-to-line of the three phases and `I` is the RMS current taken as the mean of the three phases.
Single phase drops the `sqrt(3)` term. Power factor comes from the meter's declared
`power_factor_source`. When it is `nameplate`, the value is a function of load fraction from the
motor's part-load curve, because power factor falls at low load and treating it as constant overstates
idle power, which would then overstate the idle-waste finding this section exists to produce.

Load fraction is estimated from the current ratio against full-load and no-load amps, and motor
efficiency at that load comes from `efficiency.py`: a nominal full-load efficiency by rating and pole
count transcribed from 10 CFR 431.25, shaped by a part-load curve id. Every curve carries a `source`
string; the shipped curves are the part-load efficiency relationship of DOE/GO-10097-517, named as
such in the model card, and the sensitivity of the energy-per-pallet KPI to the curve choice is
published (the `model-card-completeness` gate in section 7.9) because it is a modeling choice and not a
measurement.

Degraded sensors. When `twinflow.fleet.device_health_scored` marks a current sensor as drifted,
stuck, or in calibration loss, the intervals it would have produced are marked `quality: suspect` and
excluded from the KPI numerator, with the excluded energy reported as `unmetered_kwh`. A drifted
sensor silently inflating the energy KPI is the failure the fleet-health layer exists to catch, and
letting it through would make the KPI worse than having no KPI.

### 5.13 Energy integration and state tagging

`integrate.py` converts the power series into `EnergyInterval` records. The integration is
trapezoidal over sim-time intervals with exact partitioning at state boundaries: when an asset
changes state mid-interval, the interval is split at the transition tick and the energy is
apportioned by the trapezoid rule on each side, so no kilowatt-hour is attributed to the wrong state.
The arithmetic runs on integer ticks, which is why INV-ENERGY-03 closes to 1e-12 rather than to a
tolerance.

`states.py` tags each interval with an `AssetEnergyState` by joining to
`twinflow.twin.resource_state_changed`. The
mapping from the twin's resource states to energy states is a declared table, not an inference, and
`RUNNING` splits into `RUNNING_VA` and `RUNNING_NVA` using the twin's value-added classification of
the activity in progress. That split is what lets the energy report speak the same language as the
value stream map.

Asset coverage. Not every asset has a meter. Assets with `energy.model: metered` integrate from
telemetry; assets with `energy.model: nameplate` synthesize power from their state and nameplate
draw; assets with no energy declaration contribute nothing and are listed by name in
`EnergyWindow.unmodeled_assets`. The report states its own coverage, always.

### 5.14 Energy KPIs, demand, tariff, and grid factors

`kpi.py` computes the intensity metrics. The rule that prevents the common error: numerator and
denominator must come from the same window, the same run, and the same asset scope, and
`denominator_counts` publishes the counts used. `kwh_per_pallet` uses pallets completed within the
window, not pallets in progress. Specific energy per kilogram moved is published beside it because
energy per pallet moves when pallet weight moves, and a plant that switches to heavier pallets would
otherwise read that as an efficiency loss.

`demand.py` maintains a rolling average over `demand_interval_s` (900 s by default), tracks the
period peak with its timestamp, and applies a ratchet when the tariff declares one. The peak's
timestamp is carried because the actionable answer to a demand charge is which fifteen minutes
caused it, and that answer is a link into the event tape.

`tariff.py` prices each interval at the time-of-use rate whose calendar predicate covers it. The
predicates must tile the calendar with no gap and no overlap; validation reports the first uncovered
instant. Demand cost is `peak_kw * demand_rate`, reported separately from energy cost, because they
respond to different interventions and a combined number hides which lever applies.

`grid.py` resolves emission factors per half hour from a `GridFactorSeries`. Location-based and
market-based Scope 2 figures are both computed and both carried on `EnergyWindow`, because the GHG
Protocol Scope 2 Guidance (2015) sets out both methods and computing only one makes the ESG report
unfinishable. A marginal series, when configured, is used only for the what-if delta, never for the
inventory, since the marginal factor answers "what does one more kilowatt-hour emit" and the
inventory question is "what did our consumption emit". The two are labeled distinctly on every
artifact.

### 5.15 Idle-energy waste and the energy delta

`waste.py` scans for idle episodes: contiguous intervals in `IDLE_READY`, `STARVED`, or `BLOCKED`
where the asset drew power. For each episode it computes the energy consumed, and it computes a
break-even idle duration from the asset's restart energy and restart time:
`breakeven_idle_s = restart_energy_kwh / idle_power_kw * 3600`, adjusted upward when restarting would
delay work, using the twin's own measured queue state at the episode's end. Episodes longer than
break-even contribute to `recoverable_kwh`.

`IDLE_ENERGY_WASTE` is raised when recoverable energy over a window exceeds its threshold. The
evidence carries the episode list, the break-even calculation, the recovered cost, the recovered
emissions, and `throughput_risk_s`, so the finding argues its own case in dollars, kilograms, and
seconds rather than asserting that idling is bad.

Naming. The source calls idle energy an eighth-waste finding. The canonical eighth waste in the lean
literature is non-utilized talent, which E6's `UNUSED_SKILL_CAPACITY` also claims. Both findings ship
and neither is reduced; the collision is in the label, not the capability, and section 9 item 16 records it
with a proposal rather than quietly renaming one of them.

`delta.py` builds `EnergyDelta` for a what-if from the paired baseline and scenario runs, using
common random numbers so the difference estimator has the variance reduction twin-core
VAL-GATE-CRN-01 measures. The delta is reported with a confidence interval across replications, and
the `energy_delta` property of `twinflow.agent.whatif_completed` follows the same nullability
contract as operator impact: a null carries a note naming the absent provider, never a zero.

### 5.16 Requirement curve from the forecast (E23)

`requirement.py` converts a forecast into half-hourly labor requirements:

1. Read `twinflow.forecast.horizon_published` for the roster horizon, taking the point forecast and
   its declared interval.
2. Explode volume into activity units per bucket using the arrival and order profiles the twin
   already publishes, so a day's volume becomes a shape rather than a flat line.
3. Convert activity units into minutes using `LaborStandard`, with allowances applied on the divisor
   convention of section 3 rule 4.
4. Divide by bucket minutes to get `required_fte` per station and skill.
5. Publish `twinflow.roster.requirement_published`.

Service-level coupling. The requirement can be built at the point forecast or at a stated quantile of
the forecast interval, declared as `roster.service_level` (section 6.5). Building at the point
forecast understaffs half the time by construction, and making the quantile an explicit config key
rather than a default is what stops that from being invisible. The scoring in section 5.20 then measures
whether the chosen quantile was right.

The interval this reads is whatever the bound forecast producer supplies. At ROST that is the
classical model's own prediction interval, populated into the `interval_lower`, `interval_upper` and
`nominal_coverage` properties roadmap section 5.9 reserves at P3d. E31 at P6-W2 replaces the producer with a
conformally calibrated one behind the same three properties, so this package's config key does not
change and no forward dependency exists. `RequirementCurve` records `interval_producer_id`, so a
requirement built before the calibrated producer landed is visibly different from one built after.

Labor standards from the twin. When `standards.basis: measured`, the standard is derived from the
twin's own `twinflow.twin.activity_completed` durations at a configured percentile, filtered to
activities performed by operators at `qualified` or better and outside the first `warmup_s` of a
shift. The derivation records its source runs, so a standard can be regenerated and the change
quantified.

### 5.17 The rostering model

`model_cpsat.py` builds a CP-SAT model. Decision variables: `x[worker, day, shift]` boolean, plus
`y[worker, day, shift, station]` boolean for station assignment when station-level rostering is
enabled, plus non-negative integer slack variables `under[bucket, station, skill]` and
`over[bucket, station, skill]`.

Hard constraints:

- One shift per worker per day; a worker assigned to a shift is assigned to exactly one station per
  bucket within it.
- Skill feasibility: `y[w, d, s, st] = 0` unless the skill matrix permits it at that time, which also
  encodes certification expiry inside the horizon.
- Coverage with slack: assigned FTE plus `under` minus `over` equals `required_fte` per bucket.
- Rest: `min_rest_between_shifts_s` between consecutive assigned shifts, encoded as forbidden
  consecutive-shift pairs.
- `max_consecutive_shifts`, `max_hours_per_week_s`, `max_nights_per_cycle`.
- `forbidden_sequences` as a table constraint over the shift sequence, which is how a
  night-followed-by-morning rule is expressed without a special case in code.
- Unavailability intervals.
- Fatigue limits when `enforcement: hard` (section 5.18).

Objective terms, each with a weight from `ObjectiveWeights` and each reported separately in
`objective_breakdown`:

`w_understaffing * sum(under) + w_overstaffing * sum(over) + w_overtime * overtime_hours +
w_agency * agency_hours + w_fairness * unfairness + w_preference * unmet_preferences +
w_stability * schedule_changes + w_fatigue_soft * fatigue_excess`.

Fairness is the spread of a per-worker burden vector (weekend shifts, night shifts, hours over
contract), expressed as a min-max deviation because CP-SAT handles that linearly and a Gini
coefficient does not linearize. The `gini_cap` option in `RosterRules` is evaluated by the checker as
a reported metric, not enforced in the model, and the distinction is stated on the solution.

Determinism. A constraint solver whose output steers the simulation is bounded deterministically and
never by wall time (D-04), so this package binds four CP-SAT parameters and the loader rejects any
run that leaves them unset. `num_workers` is 1, because parallel search interleaves subsolvers and
two runs on machines of different speed then explore different subtrees. `random_seed` is fixed.
`max_deterministic_time` is set, and the CP-SAT parameter of that name is the solver's own
deterministic budget rather than a wall clock: the OR-Tools `sat_parameters.proto` describes it as
"Maximum time allowed in deterministic time to solve a problem", with the time unit correlated with
but not equal to a second. `max_number_of_conflicts` is set as the branch cap D-04 also requires, so a
budget that is generous on one machine still terminates at the same search state on another. A
wall-clock limit is rejected outright at config load (section 6.5), not merely discouraged.

`RosterSolution` records `deterministic_time_used`, `branches_used`, `num_workers`, `seed` and
`solver_version`. Because a solver upgrade can legitimately change which of several equally optimal
rosters is returned, the golden-file comparison for a roster asserts the objective value, the
feasibility status, and the coverage vector, not the exact assignment matrix, and the normalizer that
drops the matrix is recorded in the golden file itself. That is the value-equivalent tier of D-05;
byte-identity is claimed only on the pinned reference platform, which is what INV-ROST-05 states.

### 5.18 Fatigue as a roster constraint

The fatigue model is nonlinear and stateful, so it cannot go inside the CP-SAT model directly. The
precomputation lives in `twinflow_workforce/trajectory.py`, which is the only module in the system
that constructs a `FatigueModel`, and `twinflow_roster/fatigue_tuples.py` turns its published output
into constraints. The two halves are:

1. For each worker, and for each candidate shift sequence up to `roster.fatigue_lookback_shifts`
   (section 6.5), `trajectory.py` runs `FatigueModel` over the sequence with the nominal workload for the
   stations that sequence implies.
2. It records the predicted end-of-sequence alertness and cumulative damage and publishes them as
   `twinflow.workforce.fatigue_trajectory_published`.
3. `fatigue_tuples.py` reads that event and emits the sequences that violate `FatigueLimits` as
   forbidden tuples, which CP-SAT accepts as a table constraint, plus the per-sequence excess as a
   coefficient for the soft term.

The precomputation is deterministic and is cached by `(worker_profile_hash, sequence)`. The event
seam is why `twinflow-roster` imports neither `twinflow-workforce` nor `twinflow-ergonomics`; it does
still depend on `twinflow-schemas` and `twinflow-kernel`, as section 2.4 states.

When the fatigue constraint is what makes a problem infeasible,
`twinflow.roster.declared_infeasible` names it and `ROSTER_FATIGUE_BINDING` is raised at HIGH. The
answer to "why can we not cover Saturday night" being
"because the only three qualified operators would each exceed the cumulative damage limit" is a real
operational answer, and it is only available because the constraint is explicit rather than folded
into a cost.

### 5.19 Absence robustness

Absence enters twice. `predicted_absence_p` comes from the `AbsenteeismModel` protocol, whose ROST-era
implementation `ConfiguredRateAbsenteeism` reads `workforce.absenteeism_rate` from `facility.yaml`
and whose 6a14 replacement is behavioral. That is roadmap seam CD1 and this section uses its
spellings. Two robustness modes are supported, selected by `roster.robustness.mode` (section 6.5).

`expected_inflation` inflates required coverage by `1 / (1 - p_bar)` per bucket. It is cheap and
transparent, and it is systematically optimistic when absence is correlated, which it is.

`saa` is sample average approximation. It draws `roster.robustness.scenarios` absence realizations on
the child stream `roster.absence`, where each worker's absence is Bernoulli with their predicted
probability, shifted by a shared shift-level correlation term drawn on `roster.absence_correlation`,
and it minimizes expected cost across the scenarios with the assignment variables shared and the
slack variables scenario-specific. The correlated term exists because a norovirus Monday is not
independent draws, and modeling it as independent is what makes a roster's measured coverage under
absence look higher than it turns out to be.

The number of scenarios, the seed, and the hash of the realized scenario set are recorded on
`twinflow.roster.published`, so the roster is reproducible without re-drawing.

### 5.20 Checking, scoring, and feeding the simulation

`checker.py` is an independent verifier. It imports `RosterRules` and `RosterSolution` and nothing
from `model_cpsat`. It re-derives every hard constraint from the rules data and returns a list of
`ConstraintViolation`. The rule is absolute: a solution is feasible only when the checker returns an
empty list, regardless of what the solver's status says. A solver bug, a model bug, or a translation
error between the rules and the model shows up here, and the gate in section 7.7 checks the checker itself
by feeding it published best-known solutions to published benchmark instances (which it must accept)
and deliberately corrupted versions of them (which it must reject, naming the corrupted rule).

Feeding the simulation. `twinflow-workforce`'s `[roster]` extra loads
`twinflow.roster.published` and expands it into `ShiftInstance` and `StationAssignment` objects,
which become the actual staffing for the run. The roster is a plan; the run realizes it with absence,
overtime calls, and reassignment. `scoring.py` then compares plan to realization and publishes
`twinflow.roster.scored`:

- `understaffed_fte_hours` and its cost at `w_understaffing`, plus the realized service impact from
  the twin's own metrics (orders late, throughput lost), so the understaffing cost is measured rather
  than assumed.
- `overtime_hours` and `agency_hours` at their realized rates.
- `absence_realized` against `absence_predicted`, which is the calibration record that lets 6a14's
  predictor be evaluated when it arrives.

The scored roster is the input to the next planning cycle, which closes E23's loop: the requirement
quantile, the absence mode, and the objective weights are all tunable against a measured outcome
rather than argued.

### 5.21 Emission factors, GWP sets, and data quality (E17)

`FactorRegistry.resolve(activity_key, *, gwp_set, geography, year) -> EmissionFactor` performs a
deterministic waterfall: exact match on activity, geography, and vintage; then activity and geography
with the nearest earlier vintage; then activity with a broader geography; then a declared proxy. Every
step is recorded on `twinflow.carbon.factor_resolved` with `fallback_used` naming which step matched,
so a report can state what share of its factors were exact.

`gwp_set` is a required argument with no default, and the registry refuses to return a factor stated
under a different set. Summation across sets raises. Converting between sets is possible only when
`gas_breakdown` is populated, in which case `convert_gwp_set` recomputes from the gas masses using
the target set's published values and records the conversion on the factor. A factor with only a
`kgco2e_per_unit` and no breakdown cannot be converted and the registry says so rather than
approximating.

Uncertainty. `data_quality` scores drive a geometric standard deviation, and the uncertainty run
draws factors from a lognormal on the child stream `carbon.factor.uncertainty`. Lognormal is the
correct family here because an emission factor is strictly positive and its error is multiplicative;
a normal draw puts mass below zero and would need a clamp, which this section does not do. The
uncertainty run is off by default and produces `uncertainty_p05_p95` on the footprint when enabled;
the deterministic run uses the point factors so the golden files stay stable.

### 5.22 Footprint propagation through genealogy

`ledger.py` walks the genealogy graph the QMS layer maintains. The graph is a DAG of nodes (lot,
pallet, carton, item) with typed edges (`split`, `merge`, `transform`, `pack`, `return`).
`propagate_footprint` runs a topological pass:

1. A source node's footprint is the supplier's cradle-to-gate factor times its mass, plus the inbound
   transport legs that delivered it, plus any supplier-declared process energy.
2. A `transform` node adds site process energy: the energy the twin measured for the activities that
   produced it, attributed from `EnergyInterval` records joined on the activity's asset and time
   window, converted at the location-based grid factor for those half hours. Market-based is computed
   in parallel and carried separately.
3. A `split` divides the parent's footprint among children by the node's active `AllocationRule`.
   Mass allocation is the default; economic allocation is used only where the rule declares it with a
   justification string, following the standard's own hierarchy, which prefers subdivision and system
   expansion before allocating at all.
4. A `merge` sums the parents' contributions.
5. A `pack` adds packaging emissions from the packaging bill of materials.
6. A `return` node inherits the outbound footprint of the unit being returned plus the return
   transport, and its disposition path (restock, refurbish, liquidate, scrap) determines whether the
   footprint continues forward or terminates in a waste-treatment component. Returns are where naive
   ledgers double count, which is why INV-CARBON-02's test fixture is a diamond.

The walk is memoized by node id, and its node order is a stated total order rather than a library's
default, which is what section 2.6 refers to (D-03). `dag.py` runs Kahn's algorithm with the ready set held
as a binary heap keyed on `(sim_time_of_node_creation, node_id)`, both taken from the genealogy event
that created the node, with `node_id` compared as a byte string. Every node has both fields, the pair
is unique because two nodes created at the same tick have different ids, and no set iteration enters
the walk. The same graph so always produces the same numbers, on any platform and under any
`PYTHONHASHSEED`. Cycles are impossible by the graph's own invariant; the walk asserts acyclicity
rather than trusting it, because a footprint that silently loops is unbounded.

Completeness. Any input with no resolvable factor contributes zero to the sum and its mass to the
incompleteness denominator, so `completeness_pct` falls. `CARBON_DATA_GAP` fires below the configured
threshold. There is no global average backfill; the gap is visible or the number is not published.

### 5.23 Transport legs

`transport.py` computes per-leg emissions on the basis of ISO 14083, the transport-chain greenhouse
gas quantification standard, whose worked examples reach this repository as the fixtures
VAL-GATE-CAR-01 names. The standard is paid and `iso.org` refused automated retrieval on 2026-08-09
with HTTP 403, so this section names the standard and does not quote or restate its text; the fixture
headers carry the edition and clause locators taken from the purchased copy. For each leg:

1. Establish the transport activity: `payload_t * distance_km` for freight, or vehicle-kilometers for
   an exclusive-use vehicle.
2. Establish distance. `actual` when the transport layer measured it, `routed` from the network
   model, or `great_circle_adjusted` with the mode's published adjustment factor when only endpoints
   are known. The basis is carried, because a great-circle sea distance without the adjustment
   understates by a material amount.
3. Resolve the factor by mode, vehicle class, fuel, and load factor. Both well-to-tank and
   tank-to-wheel components are resolved; the total is well-to-wheel and all three are carried.
4. Add hub operations (terminal handling, warehousing at transshipment) and refrigeration energy for
   temperature-controlled legs, which is where the cold-chain SKUs pick up a materially different
   footprint from ambient ones.
5. Allocate to shipments. When a vehicle operation carries several shipments, the leg's emissions are
   divided by the declared basis: mass, volume, pallet slot, or chargeable weight. INV-CARBON-04
   asserts the allocation closes.

Empty running is attributed to the operation and then to its shipments by the same basis, rather than
discarded, and `empty_running_pct` is reported so the effect is visible.

### 5.24 Shipment ledger and CBAM declarations

`build_shipment_ledger(shipment_id)` assembles the per-shipment artifact: for each line, the node's
`LotFootprint` cradle-to-gate figure, plus the outbound legs, plus packaging, giving `total_kgco2e`,
`kgco2e_per_unit`, and `kgco2e_per_kg`. The ledger is emitted at ship confirmation and is immutable
afterward; a later factor correction produces a new ledger version with a supersession link rather
than an edit, because a shipped declaration is a record.

`cbam.py` filters for covered goods. The regime is Regulation (EU) 2023/956 of 10 May 2023
establishing a carbon border adjustment mechanism, OJ L 130, 16 May 2023, page 52.
`catalog/cbam_goods.yaml` maps commodity codes to the covered categories, and a shipment crossing a
configured customs boundary with at least one covered line produces a `CbamDeclaration`. The
declaration carries direct and indirect embedded emissions per tonne of goods, where direct comes
from the production-route process emissions inherited through genealogy and indirect comes from the
electricity consumed in production at the applicable electricity factor. Certificates required,
certificate cost at the configured price, and the adjustment for a carbon price already paid in the
country of origin are computed and reported separately. That adjustment is a reduction in the number
of certificates to be surrendered, which is why INV-CBM-02 refuses a negative: recital 43 of the
Regulation frames it as a claim to "a reduction in the number of CBAM certificates to be surrendered
corresponding to the carbon price already effectively paid in the country of origin", and a reduction
below zero is not a form the instrument has.

Two properties matter more than the arithmetic. First, `method` states whether the declaration used
actual values or default values, and a covered good with unresolvable actuals raises
`CBAM_DECLARATION_INCOMPLETE` at HIGH rather than falling back silently. Second,
`standard_version` is mandatory and the mapping table is versioned, because the covered-goods list
and the reporting rules are a moving regulatory target and a declaration with no version stamp is
unauditable (section 9 item 7).

### 5.25 Carbon in landed cost

`pricing.py` computes `LandedCostCarbonLine` for each sourcing option. The carbon cost is the
embedded tonnes times the applicable price, where the price is the internal shadow price for internal
decisions and the certificate price for actual CBAM exposure, and both are reported so a reader can
see which is which. The line is computed twice, with and without carbon, and `rank_change_vs_no_carbon`
records how the option's rank moved.

The sourcing what-if consumes this directly: `compare_scenarios` over supplier options returns a
table with landed cost, landed cost with carbon, and the rank change, so the answer to "which supplier
wins" can differ from the answer to "which supplier wins under a carbon price" and the difference is
the deliverable. The internal price is a config value with no default, because there is no correct
one, and the shipped profiles state theirs in the model card.

### 5.26 Scope 1, 2, and 3 inventory (E39)

`scopes.py` builds `ScopeInventory` from stored events only.

| Scope          | Sources it draws from                                                                                                                                                                                                                                                                                                                        |
| -------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 1, direct      | On-site fuel combustion, meaning heating and propane forklifts where the facility profile declares them; refrigerant leakage from the configured charge and leak rate; any owned-vehicle transport legs                                                                                                                                      |
| 2, electricity | `twinflow.energy.window_closed` totals, computed twice. Location-based uses the grid average factor for the half hour. Market-based uses contractual instruments declared in the `esg` block (section 6.7) and falls back to the residual mix where none apply. Both figures are present                                                     |
| 3, by category | Purchased goods and services from supplier cradle-to-gate factors on inbound lots; upstream transport from inbound legs; waste from scrap and disposition records; business travel and commuting from configured factors and headcount; downstream transport from outbound legs; use and end-of-life from the product catalog where declared |

Every line carries the historian query that produced it in `source_events`, which is what makes the
inventory reproducible from the same data by someone else. Categories with no data are listed as
exclusions with a reason and an estimated magnitude band, never omitted. Intensity metrics (per
pallet shipped, per order, per revenue unit) are computed from the same window's denominators.

### 5.27 Social metrics

`SocialMetricSet` is assembled entirely from events this section already published. Rates come from
`twinflow.safety.rate_window_closed`. Near-miss counts and the reporting rate come from
`twinflow.safety.near_miss_detected`. Training hours come from the cross-training matrix's progress
records. Turnover is config-declared until 6a14 supplies the attrition model, with the source
recorded either way. Absence comes from `twinflow.roster.scored`. Overtime share and schedule
stability come from the assignment ledger compared against the published roster. The count of
stations in an ergonomic action band comes from `twinflow.ergonomics.score_computed`.

Nothing here is estimated. Every social number in the ESG report has an event stream behind it and a
query id the grounding checker can check, which is the same discipline the environmental side
follows.

### 5.28 The one-command ESG report

`twinflow-carbon report --historian <path> --from <t> --to <t> --standard-version <v>` runs:

1. Resolve the period and the organizational boundary from the `esg` block (section 6.7).
2. Build `ScopeInventory` (section 5.26) and `SocialMetricSet` (section 5.27).
3. Map both onto `EsrsDatapoint` records through `esrs_map.py`, a data file keyed by datapoint id
   with a `standard_version` column. A datapoint whose value cannot be computed is emitted with
   `source: not_available` and a `GapRegisterEntry`, never omitted and never zero-filled.
4. Build the double-materiality readiness matrix (section 5.29).
5. Render `report.html` from a Jinja template with no external assets, plus `report.json` carrying
   every number with its provenance, plus a machine-readable gap register.
6. Compute `coverage_pct` as the share of mapped datapoints with `source: computed`.

The HTML report opens with coverage and the gap count, not with the totals. A sustainability report
that leads with a number and buries its completeness is the failure mode this design refuses, and
putting coverage first is a one-line decision that makes the artifact honest.

Determinism, scoped as D-05 scopes it. The report is a pure function of the historian contents, the
config, and the standard version. The generator reads a wall clock exactly once, to stamp the
artifact's own generation time, and that value never enters a computed number, a hash, or a control
decision, which is the operator-facing carve-out D-02 permits. On the pinned reference platform two
runs produce byte-identical HTML and JSON after the declared normalizer strips that stamp. Across
platforms the claim is value-equivalence: every datapoint id, `source` value and gap-register entry is
identical, and every numeric value agrees within the tolerance SCN-HS-12 measures and reports rather
than assumes. `report_id` is `content_hash(config_hash, standard_version, sorted(run_ids), period)`,
so it is stable across both tiers and carries no clock reading.

### 5.29 Double materiality readiness and the gap register

`materiality.py` produces one `MaterialityAssessment` per topic in the configured topic list, scoring
impact materiality (the effect of the operation on people and environment) and financial materiality
(the effect of sustainability matters on the operation) on a declared scale. Where the twin measures
something relevant, the assessment cites it: the climate topic's impact score cites Scope 1 and 2
totals and the financial score cites the modeled CBAM cost and energy cost exposure; the own-workforce
topic cites TRIR, the count of stations in an action band, and the modeled injury cost. Those
citations are `impact_evidence_metric` and `financial_evidence_metric`, and a topic with no cited
evidence is flagged in the readiness note as declared rather than evidenced.

`gaps.py` produces the register: every datapoint that is not computed, why, which component would
supply it, and an effort estimate. The register is the honest half of the deliverable and it is
generated, so it cannot drift from the report.

The artifact is labeled a readiness assessment throughout. This section does not claim to make a
materiality determination, which is a governance act by an organization with stakeholders, and the
README says so in the same sentence that claims the one-command report.

### 5.30 Agent tools, governed metrics and dashboard

Tools registered with the agent (E26d schema-constrained, E26a execution-grounded, autonomy tier per
E5):

| Tool                   | Arguments                                                     | Returns                                                                        | Tier |
| ---------------------- | ------------------------------------------------------------- | ------------------------------------------------------------------------------ | ---- |
| `get_ergonomic_risk`   | `subject` (station, operator or slot), `window`               | component scores, action limits, driving component, band                       | L1   |
| `get_safety_metrics`   | `window`, `area?`, `basis?`                                   | TRIR, DART, LTIFR, near-miss rate, Pareto by cause and location, open findings | L1   |
| `get_operator_load`    | `operator_id?`, `window`                                      | cumulative damage, recovery debt, alertness trace, utilization                 | L1   |
| `get_energy_kpis`      | `window`, `scope`, `asset?`                                   | kWh totals and intensities, idle share, peak demand, cost, carbon              | L1   |
| `get_carbon_footprint` | `subject` (shipment, lot, sku or supplier), `window?`         | footprint breakdown, data quality, factor ids                                  | L1   |
| `get_landed_cost`      | `sku`, `supplier_id?`, `scenario_id?`                         | landed cost components including carbon and CBAM                               | L1   |
| `optimize_roster`      | `week`, `service_level?`, `objective_weights?`, `robustness?` | roster, objective breakdown, fairness, feasibility report                      | L2   |
| `run_esg_report`       | `period`                                                      | artifact paths, populated and gapped datapoint counts                          | L1   |
| `run_whatif`           | scenario ref or inline change                                 | the full what-if answer contract of section 4.4 and section 5.11               | L2   |

Every quantitative answer routes through the governed metric layer (E26b). Metrics this section
registers, each with an exact expression in `semantics/metrics.yaml`:

`trir`, `dart_rate`, `ltifr`, `severity_rate`, `near_miss_rate`, `recordable_count`,
`station_injury_risk_index`, `cumulative_damage_p95`, `operator_utilization`,
`peak_operator_utilization`, `level_loading_index`, `smoothness_index`, `unused_talent_hours`,
`understaffing_hours`, `overtime_share`, `agency_share`, `schedule_stability_index`,
`absence_rate`, `energy_per_pallet_kwh`, `energy_per_order_kwh`, `idle_energy_share`,
`peak_kw_15min`, `demand_charge_usd`, `kgco2e_per_unit_shipped`, `kgco2e_per_tkm`,
`embodied_carbon_lost_to_scrap`, `carbon_cost_share_of_landed_cost`, `injury_cost_avoided_usd`,
`training_hours_per_fte`, `turnover_rate`.

Defining `trir` once in the metric layer is what stops the agent from writing a plausible and wrong
incidence-rate expression, which is precisely the failure mode E26b exists to eliminate.

Four dashboard panels, all subject to C12 accessibility rules.

| Panel                 | What it shows                                                                                                                                                       |
| --------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Safety tile           | Near-miss rate and the worst station risk index band, leading rather than days since the last recordable. Days-since is a lagging count that rises while risk rises |
| Operator load heatmap | Operators by station, colored and hatched by cumulative damage share of the action limit, with the value in text in every cell                                      |
| Energy strip          | kW against the 15-minute demand line with the current billing peak marked, plus the idle share                                                                      |
| Carbon tile           | kgCO2e per unit shipped with the data-quality mix                                                                                                                   |

Severity is encoded by shape and text and color, new safety findings announce through an ARIA
live region, the palette is colorblind-safe, and the whole set respects reduced motion. A
color-only safety alarm is a control-room failure mode, and this is the section where getting that
wrong would contradict its own subject.

---

## 6. Configuration

Every key below is validated against a published JSON Schema at load, with line-numbered
suggestion-bearing errors and a `just validate` path (C5). Unknown keys are rejected, not ignored.

### 6.1 `facility.yaml`, `people` block

| Key                                                 | Type                                                             | Validation                                                                                                                                               |
| --------------------------------------------------- | ---------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `people.shift_patterns[]`                           | list of pattern objects                                          | INV-SHF-01 to 03 checked at load                                                                                                                         |
| `people.operators[]` or `people.operator_generator` | explicit list or a seeded generator spec                         | exactly one of the two; the generator takes headcount by skill and a seed                                                                                |
| `people.skills[]`                                   | list of skill ids                                                | referenced skills must exist                                                                                                                             |
| `people.certifications[]`                           | list of cert definitions with validity months and training hours | expiry must exceed grant                                                                                                                                 |
| `people.rules.max_hours_per_day`                    | float, 1 to 24                                                   |                                                                                                                                                          |
| `people.rules.min_rest_h`                           | float, 0 to 24                                                   | must be less than 24 minus `max_shift_h`                                                                                                                 |
| `people.allowances.personal_pct`                    | float, 0 to 0.5                                                  |                                                                                                                                                          |
| `people.allowances.basic_fatigue_pct`               | float, 0 to 0.5                                                  |                                                                                                                                                          |
| `people.allowances.delay_pct`                       | float, 0 to 0.5                                                  |                                                                                                                                                          |
| `people.sustainable_utilization_max`                | derived, read-only                                               | equals 1 minus the allowance sum; setting it directly is a config error                                                                                  |
| `people.fatigue.model`                              | enum                                                             | `none` \                                                                                                                                                 |
| `people.fatigue.full_recovery_h`                    | float                                                            |                                                                                                                                                          |
| `people.fatigue.k_error`                            | float, greater than 0                                            | the error-multiplier gain of section 5.8; a declared model parameter, not a cap                                                                          |
| `people.fatigue.k_speed`                            | float, greater than 0                                            | the speed-multiplier gain of section 5.8; a declared model parameter, not a cap                                                                          |
| `people.fatigue.error_multiplier_report_threshold`  | float, at least 1.0                                              | the value above which `FATIGUE_ERROR_ELEVATED` is raised. It changes what is reported and never what is computed, so it is a threshold and not a maximum |
| `people.fatigue.model_card`                         | path                                                             | must exist; the card must declare every non-validated coefficient                                                                                        |
| `people.balance.imbalance_threshold`                | float, 0 to 1                                                    | the station-load imbalance that raises `WORKLOAD_IMBALANCE`                                                                                              |
| `people.balance.min_consecutive_windows`            | int, at least 1                                                  | stops a single truck arrival from firing the finding                                                                                                     |
| `people.balance.unused_skill_share_threshold`       | float, 0 to 1                                                    | the share of shift hours worked below skill that raises `UNUSED_SKILL_CAPACITY`                                                                          |
| `people.rotation.policy`                            | enum                                                             | `none` \                                                                                                                                                 |
| `people.rotation.interval_s`                        | int                                                              | required when `fixed_interval`; the source's two-hour rotation is 7200                                                                                   |
| `people.rotation.min_dwell_s`                       | int                                                              | a rotation shorter than this is refused, because handover cost exceeds the benefit                                                                       |

### 6.2 `facility.yaml`, `ergonomics` block

| Key                                         | Type                       | Validation                                                                                                                                                                        |
| ------------------------------------------- | -------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `ergonomics.units`                          | enum `metric` \            | `imperial`                                                                                                                                                                        |
| `ergonomics.scorers[]`                      | list                       | subset of `niosh_rnle`, `rula`, `reba`, `ocra`, `pushpull`, `metabolic`, `lifft`, `duet`. Each name is the method's own name and this section uses no second name for any of them |
| `ergonomics.station_profiles`               | map station to profile ref | every manual task's station must resolve                                                                                                                                          |
| `ergonomics.profiles[]`                     | list of `ErgonomicProfile` | INV-ERG-01 to 03 at load; out-of-domain values are errors with the offending line                                                                                                 |
| `ergonomics.risk_index.weights`             | map component to float     | must sum to 1.0 within 1e-9                                                                                                                                                       |
| `ergonomics.risk_index.bands`               | list of band thresholds    | strictly increasing, covering 0 to 1                                                                                                                                              |
| `ergonomics.risk_index.action_limits`       | map component to float     | each must name its `source`                                                                                                                                                       |
| `ergonomics.cumulative.damage_action_limit` | float                      |                                                                                                                                                                                   |
| `ergonomics.tables_dir`                     | path                       | every table file must carry a provenance header and match its recorded checksum                                                                                                   |

### 6.3 `facility.yaml`, `safety` block

| Key                                         | Type                           | Validation                                                                                                                               |
| ------------------------------------------- | ------------------------------ | ---------------------------------------------------------------------------------------------------------------------------------------- |
| `safety.pyramid.preset`                     | string                         | a `pyramid_id` present in `catalog/safety_pyramids.yaml`; `heinrich` and `bird` ship, further entries are added by adding a cited row    |
| `safety.pyramid.ratios`                     | map class to ratio             | permitted only on an inline pyramid, which must also carry a `source_ref` with an edition and a locator; strictly decreasing in severity |
| `safety.pyramid.modulators`                 | map                            | which of risk band, alertness, PPE state, severity potential modulate the conditional probability, and their coefficient ranges          |
| `safety.generator`                          | enum                           | `pyramid` \                                                                                                                              |
| `safety.proximity.zones`                    | map asset class to three radii | warning at least slow at least protective, all positive                                                                                  |
| `safety.proximity.sample_interval_s`        | float                          | how often pairwise separation is evaluated; must divide the twin's position publication interval                                         |
| `safety.proximity.reaction_time_s`          | float                          | used in the separation calculation                                                                                                       |
| `safety.proximity.human_approach_speed_mps` | float                          |                                                                                                                                          |
| `safety.proximity.sensor_uncertainty_m`     | float                          |                                                                                                                                          |
| `safety.ppe.required_by_zone`               | map zone to PPE set            |                                                                                                                                          |
| `safety.ppe.observable_from_topdown[]`      | list of PPE items              | a check requested for an item outside this list is a load error                                                                          |
| `safety.ppe.check_rate_per_hour`            | float                          |                                                                                                                                          |
| `safety.rate_basis_hours`                   | int                            | 200000 or 1000000; both are always computed regardless                                                                                   |
| `safety.regulatory_region`                  | enum                           | selects the reported default basis and the recordability rules                                                                           |
| `safety.costs_file`                         | path                           | must carry `source`, `source_edition`, `as_of`; missing provenance is a load error                                                       |
| `safety.severity_floor`                     | enum                           | minimum severity for any finding in the `safety` class (section 4.3), default `HIGH`                                                     |

### 6.4 `facility.yaml`, `energy` block

| Key                                 | Type                  | Validation                                                            |
| ----------------------------------- | --------------------- | --------------------------------------------------------------------- |
| `energy.meters[]`                   | list of `EnergyMeter` | every `asset_id` must exist in the twin                               |
| `energy.default_power_factor`       | float, 0 to 1         | used only when `power_factor_source` is `constant` (section 3.9)      |
| `energy.efficiency_tables`          | path                  | provenance header required                                            |
| `energy.idle_states[]`              | list of asset states  | must be a subset of the declared state enum                           |
| `energy.interval_minutes`           | int                   | must divide 60                                                        |
| `energy.demand_window_minutes`      | int, default 15       |                                                                       |
| `energy.tariff_file`                | path                  | time-of-use periods must tile the day with no gap or overlap          |
| `energy.grid.inventory_factor`      | factor ref            | the average factor used for the disclosure                            |
| `energy.grid.marginal_curve`        | path or null          | the half-hourly curve used for decision support                       |
| `energy.waste.idle_share_threshold` | float, 0 to 1         |                                                                       |
| `energy.waste.restart_energy_kwh`   | map asset to float    | required for any asset the idle-waste analyzer may recommend stopping |

### 6.5 `facility.yaml`, `roster` block

| Key                                    | Type                       | Validation                                                                                                                        |
| -------------------------------------- | -------------------------- | --------------------------------------------------------------------------------------------------------------------------------- |
| `roster.bucket_minutes`                | int, default 30            | must divide the shift length                                                                                                      |
| `roster.service_level`                 | float, 0.5 to 0.999        | the quantile of the bound forecast producer's declared interval (section 5.16)                                                    |
| `roster.standards[]`                   | list of activity standards | each declares `basis` as `measured`, `declared` or `mtm_style`, and a `source_ref`                                                |
| `roster.rules.*`                       | the `RosterRules` fields   | mutual consistency checked, for example `min_shift_h` at most `max_shift_h`                                                       |
| `roster.objective_weights.*`           | floats                     | all non-negative, at least one positive                                                                                           |
| `roster.robustness.mode`               | enum                       | `expected_inflation` \                                                                                                            |
| `roster.robustness.scenarios`          | int                        | required when `saa`; at least 20                                                                                                  |
| `roster.solver.random_seed`            | int                        | required, no default                                                                                                              |
| `roster.solver.max_deterministic_time` | float                      | required. A wall-clock limit key is rejected at load, because a budget in wall time makes the tape depend on machine speed (D-04) |
| `roster.solver.max_conflicts`          | int                        | required. The branch cap D-04 also needs, so a budget generous on one machine still stops at the same search state on another     |
| `roster.solver.num_workers`            | int                        | must be 1. Parallel search interleaves subsolvers and is not reproducible across machines (D-04)                                  |
| `roster.fatigue_lookback_shifts`       | int, default 3             | how many shifts back the section 5.18 precomputation enumerates                                                                   |

### 6.6 `facility.yaml`, `carbon` block

| Key                                    | Type                          | Validation                                               |
| -------------------------------------- | ----------------------------- | -------------------------------------------------------- |
| `carbon.factors_file`                  | path                          | every factor must carry `source` and `as_of` (INV-EF-01) |
| `carbon.gwp_set`                       | enum `ar4` \                  | `ar5` \                                                  |
| `carbon.gwp_horizon_years`             | enum `20` \                   | `100`                                                    |
| `carbon.allocation.default_method`     | enum                          | `subdivision` \                                          |
| `carbon.transport.standard_version`    | string                        | recorded on every leg                                    |
| `carbon.transport.uplift_factors`      | map mode to float             | at least 1.0                                             |
| `carbon.transport.default_load_factor` | map mode to float             | 0 to 1                                                   |
| `carbon.transport.empty_running_share` | map mode to float             | 0 to 1                                                   |
| `carbon.dc_allocation`                 | enum                          | `activity_based` \                                       |
| `carbon.cbam.regulation_version`       | string                        | required, no default                                     |
| `carbon.cbam.covered_cn_codes`         | path                          |                                                          |
| `carbon.cbam.benchmarks`               | path                          |                                                          |
| `carbon.cbam.certificate_price`        | float or path to a price path |                                                          |
| `carbon.cbam.de_minimis_tonnes`        | float or null                 |                                                          |
| `carbon.internal_carbon_price`         | float, default 0              | currency declared alongside                              |

### 6.7 `facility.yaml`, `esg` block

| Key                                    | Type                                 | Validation                                                                                         |
| -------------------------------------- | ------------------------------------ | -------------------------------------------------------------------------------------------------- |
| `esg.standard_version`                 | string                               | required, recorded in every artifact                                                               |
| `esg.esrs_map`                         | path                                 | every datapoint id must be unique; every mapped metric must exist in the metric layer              |
| `esg.scope3_categories`                | map category to status and rationale | a non-calculated category without a rationale is a load error                                      |
| `esg.social.demographics`              | bool, default false                  | when false the demographic datapoints appear in the gaps register with reason `DISABLED_BY_CONFIG` |
| `esg.social.commute_distribution`      | distribution spec or null            | tagged PROXY in output                                                                             |
| `esg.materiality.impact_thresholds`    | map                                  |                                                                                                    |
| `esg.materiality.financial_thresholds` | map                                  |                                                                                                    |
| `esg.output_dir`                       | path                                 |                                                                                                    |

### 6.8 Sensor catalog entries this section requires

Added to the catalog as ordinary entries, since adding a sensor type is a catalog entry rather than
new plumbing: `worker_proximity_uwb`, `amr_safety_scanner`, `estop_status`, `machine_guard_switch`,
`fall_detection`, `smoke_detector`, `gas_leak`, `co_detector`, `ppe_camera` (the CV channel),
`motor_current`, `power_meter_3ph`, `voltage`, `power_factor`, `smart_meter`, `battery_soc_soh`,
`ups_status`. Each declares its signal model, its failure signatures, its UNS topic and the twin
subsystem it attaches to, per the catalog schema owned by the sensor section.

---

## 7. Testing

Four tiers per C4: fast unit, property-based invariants, seeded end-to-end scenarios with golden
files, and validation gates against published references. Every gate names its source and its
tolerance. A gate whose source cannot be redistributed encodes only the example's inputs and expected
outputs as a fixture with a citation, never the source document.

### 7.1 Unit tests

Per package, the ordinary coverage: multiplier functions at their boundaries, table lookups at every
edge row, unit conversion round trips, rate arithmetic with a zero denominator, event serialization
round trips against the registry, config loader rejection of every documented invalid case with the
expected line number in the message.

### 7.2 Property-based invariants (Hypothesis)

Named invariants, each mapped to the model invariant it protects:

| Property                            | Asserts                                                                                                                                                                                                          |
| ----------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `prop_niosh_multipliers_bounded`    | every multiplier in 0 to 1 and RWL at most the load constant, over the full input domain (INV-ERG-02)                                                                                                            |
| `prop_niosh_monotone`               | RWL is non-increasing as any single input moves away from its ideal, holding the others fixed                                                                                                                    |
| `prop_li_definition`                | lifting index equals load over RWL exactly, and is infinity not zero when RWL is zero (INV-ERG-03)                                                                                                               |
| `prop_units_roundtrip`              | metric and imperial evaluation of the same physical task agree within 1 percent, the floor INV-ASM-04 derives from the two published load constants                                                              |
| `prop_posture_total_function`       | RULA in 1 to 7 and REBA in 1 to 15 with no lookup failure for any input in the declared domain (INV-ASM-03)                                                                                                      |
| `prop_out_of_domain_rejected`       | an out-of-domain profile raises, and never returns a score (INV-ERG-01)                                                                                                                                          |
| `prop_damage_monotone`              | cumulative damage is non-decreasing within a shift (INV-FAT-03)                                                                                                                                                  |
| `prop_alertness_bounded_recovers`   | alertness stays in `(0, 1]` and is non-decreasing during rest (INV-FAT-01)                                                                                                                                       |
| `prop_multipliers_identity_at_zero` | both multipliers equal exactly 1.0 at zero fatigue, keep their support across the full float64 exponent range, and never sit exactly on a configured threshold (INV-FAT-02)                                      |
| `prop_fatigue_full_recovery`        | a full rest opportunity returns the state to baseline within 1e-9 (INV-FAT-06)                                                                                                                                   |
| `prop_multiplier_held_for_task`     | replaying a task with a mid-task state change yields the same duration and the same defect draw (INV-FAT-05)                                                                                                     |
| `prop_incident_has_precursor`       | every pyramid-generated incident references a prior near miss (INV-SAFE-02)                                                                                                                                      |
| `prop_recordable_definition`        | `recordable` matches the classification set exactly (INV-SAFE-03)                                                                                                                                                |
| `prop_rate_arithmetic`              | TRIR equals the definition exactly and a zero denominator yields null (INV-SAFE-04)                                                                                                                              |
| `prop_safety_never_shelved`         | no finding in the `safety` class is ever shelved or deduplicated, under any alarm-flood input (INV-ALARM-01)                                                                                                     |
| `prop_risk_index_weights`           | composite in 0 to 1 with weights summing to 1, and severity driven by the worst exceeding component (INV-SRI-01, 02)                                                                                             |
| `prop_ppe_compliance`               | compliance equals the subset relation (INV-PPE-01)                                                                                                                                                               |
| `prop_roster_checker_agrees`        | the independent checker finds zero violations in any solver output over random instances (INV-ROST-03)                                                                                                           |
| `prop_understaffing_non_negative`   | surplus never offsets shortfall across buckets (INV-ROST-02)                                                                                                                                                     |
| `prop_roster_certification`         | no assignment uses an expired or missing certification (INV-ROST-04)                                                                                                                                             |
| `prop_roster_deterministic`         | on the pinned platform, identical instance, seed, solver version and deterministic budget yield a byte-identical solution; across platforms, identical status, objective value and coverage vector (INV-ROST-05) |
| `prop_energy_partition`             | state-tagged energy sums exactly to the total under arbitrary state-change timing (INV-ENERGY-01)                                                                                                                |
| `prop_energy_subdivision`           | subdividing an interval does not change its energy within 1e-9 (INV-ENERGY-05)                                                                                                                                   |
| `prop_energy_non_negative`          | no negative energy for any input current or state sequence (INV-ENERGY-04)                                                                                                                                       |
| `prop_carbon_closure`               | carbon closes through arbitrary random transformation graphs within 1e-6 relative (INV-CARBON-01)                                                                                                                |
| `prop_leg_allocation_sums`          | shipment allocations sum to the vehicle total within 1e-9 (INV-CARBON-04)                                                                                                                                        |
| `prop_leg_monotone`                 | leg emissions non-decreasing in distance and payload (INV-CARBON-05)                                                                                                                                             |
| `prop_cbam_non_negative`            | certificates due never negative under any origin carbon price (INV-CBM-02)                                                                                                                                       |
| `prop_esg_partition`                | every mapped datapoint is populated or gapped, never absent (INV-ESG-01)                                                                                                                                         |
| `prop_esg_totals`                   | reported scope totals equal the underlying ledger sums within 1e-6 (INV-ESG-02)                                                                                                                                  |
| `prop_whatif_blocks_required`       | a what-if payload missing `operator_impact`, `energy_delta` or `carbon_delta` fails schema validation, and a null block without a reason string also fails                                                       |
| `prop_carbon_walk_order_stable`     | the genealogy walk of section 5.22 produces the same node order and the same totals under 100 shuffled input orderings and two `PYTHONHASHSEED` values (D-03)                                                    |
| `prop_ppe_lists_sorted`             | `PpeState.required` and `.worn` are sorted and duplicate-free on construction, so no set iteration reaches a payload (D-03)                                                                                      |

### 7.3 How a gate in this section is constructed

Every gate below satisfies the five conditions of D-11. It names a specific external published
reference with an edition and a locator, and this repository is never a reference for itself. Its
tolerance is never tighter than the precision of the published value it checks, so a gate against a
value printed to one decimal place is checked to one decimal place. A gate over a stochastic quantity
states a noise floor that is measured rather than assumed, by running the same experiment under 30
independent seeds and taking three times the observed standard deviation, and sets its tolerance
above that floor. Every gate states what result would falsify it. A statistic with no valid external
reference is recorded as an open question in section 9 and is never recorded as a passing gate.

Two checks that earlier drafts listed as gates are not gates, because their only reference was this
repository. Carbon closure through the genealogy graph is an internal consistency property and ships
as `prop_carbon_closure` in section 7.2. Roster feasibility against the independent checker is likewise a
property and ships as `prop_roster_checker_agrees`. Neither capability is reduced; both moved to the
tier where their evidence actually lives.

### 7.4 Validation gates, ergonomics

| Gate                | External reference                                                                                                                                                                                                                                   | Assertion, tolerance and noise floor                                                                                                                                                                                                                                                                | Falsified by                                                                                                 |
| ------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------ |
| **VAL-GATE-ERG-01** | Waters, Putz-Anderson and Garg (1994), _Applications Manual for the Revised NIOSH Lifting Equation_, DHHS (NIOSH) Publication 94-110, the worked example problems, cited by problem number. US Government work, public domain                        | For every worked example, the recommended weight limit reproduces the published value to the decimal place the manual prints it to, and the lifting index likewise. Multi-task examples reproduce the published composite lifting index on the same basis. Deterministic, so no noise floor applies | Any worked example whose reproduced value rounds differently from the printed one at the printed precision   |
| **VAL-GATE-ERG-02** | Waters, Putz-Anderson, Garg and Fine (1993), "Revised NIOSH equation for the design and evaluation of manual lifting tasks", _Ergonomics_ 36(7), 749-776, the frequency and coupling multiplier tables                                               | Every cell of the shipped frequency and coupling tables equals the published cell exactly, including the split at the reference vertical height and the zero cut-off above the maximum tabulated frequency. Exact equality, because a transcription is either right or wrong                        | One differing cell                                                                                           |
| **VAL-GATE-ERG-03** | McAtamney and Corlett (1993), "RULA: a survey method for the investigation of work-related upper limb disorders", _Applied Ergonomics_ 24(2), 91-99, the worked example and scoring tables                                                           | The grand score and action level reproduce the published example exactly, and every cell of tables A, B and C round-trips against the transcribed source. Exact equality on integers                                                                                                                | Any differing grand score, action level, or table cell                                                       |
| **VAL-GATE-ERG-04** | Hignett and McAtamney (2000), "Rapid Entire Body Assessment (REBA)", _Applied Ergonomics_ 31(2), 201-205, the worked example and scoring tables                                                                                                      | The REBA score and risk level reproduce the published example exactly and every table cell round-trips. Exact equality on integers                                                                                                                                                                  | Any differing score, risk level, or table cell                                                               |
| **VAL-GATE-ERG-05** | Gallagher, Sesek, Schall and Huangfu (2017), "Development and validation of an easy-to-use risk assessment tool for cumulative low back loading: The Lifting Fatigue Failure Tool (LiFFT)", _Applied Ergonomics_ 63, 142-150, and its worked example | Cumulative damage and the probability of a high-risk job reproduce the worked example to the precision the paper prints, and not tighter. Deterministic                                                                                                                                             | A reproduced value that differs at the paper's own printed precision                                         |
| **VAL-GATE-ERG-06** | The distal upper extremity companion tool of the same authors, cited in the fixture header by paper and worked example                                                                                                                               | Cumulative damage to the precision the companion paper prints. Deterministic                                                                                                                                                                                                                        | A reproduced value differing at the printed precision                                                        |
| **VAL-GATE-ERG-07** | Occhipinti (1998), "OCRA: a concise index for the assessment of exposure to repetitive movements of the upper limbs", _Ergonomics_ 41(9), 1290-1311, plus the informative annex example of ISO 11228-3                                               | The checklist score and band reproduce the published example exactly. Where the source leaves an input ambiguous the test is marked skipped with the ambiguity recorded in the fixture header, never silently loosened                                                                              | A differing score or band on an unambiguous example                                                          |
| **VAL-GATE-ERG-08** | Garg, Chaffin and Herrin (1978), "Prediction of metabolic rates for manual materials handling jobs", _American Industrial Hygiene Association Journal_ 39(8), 661-674, worked examples                                                               | Predicted metabolic rate reproduces the published values to the precision the paper prints. Deterministic                                                                                                                                                                                           | A reproduced rate differing at the printed precision                                                         |
| **VAL-GATE-ERG-09** | Rohmert (1973), the published rest allowance and endurance relationship, cited in the fixture header by paper, figure number and the digitizing tool used                                                                                            | Rest allowance within twice the stated digitization error of the values read from the source figure. The digitization error is measured by three independent re-digitizations of the same figure and stated in the fixture header, so the tolerance is above the reading noise rather than below it | A value outside twice the stated digitization error, or a fixture header with no measured digitization error |

### 7.5 Validation gates, safety

| Gate                | External reference                                                                                                                                                                                                                                         | Assertion, tolerance and noise floor                                                                                                                                                                                                                                                                                                                                                                            | Falsified by                                                                                                                                  |
| ------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------- |
| **VAL-GATE-SAF-01** | 29 CFR 1904, in particular section 1904.7(a)'s six recording criteria, retrieved from the eCFR on 2026-08-09 with HTTP 200, plus the incidence-rate calculation worksheet OSHA publishes with the recordkeeping forms                                      | The recordability classification matches section 1904.7(a) on a fixture of 30 constructed cases, at least one per criterion and at least five first-aid-only. TRIR, DART rate and severity rate reproduce the worksheet's worked calculation to the decimal place the worksheet prints. Deterministic                                                                                                           | Any fixture case classified differently from the rule text, or a rate differing at the worksheet's printed precision                          |
| **VAL-GATE-SAF-02** | The OSHA Safety Pays Individual Injury Estimator at `osha.gov/safetypays/estimator`, whose direct and indirect cost outputs are recorded for a fixture of input values with the retrieval date in the fixture header                                       | The indirect multiplier the implementation selects reproduces the estimator's own returned indirect cost for every fixture input, to the dollar the estimator prints, including at each tier boundary and one dollar either side of it. The tier boundaries are not published as a table on the page, so the fixture records the estimator's outputs rather than restating a tier table                         | A fixture input whose reproduced indirect cost differs from the recorded estimator output                                                     |
| **VAL-GATE-SAF-03** | Folkard and Tucker (2003), "Shift work, safety and productivity", _Occupational Medicine_ 53(2), 95-101, the published relative risk by hour on shift, by successive night, and by shift type                                                              | With the physical-load term neutralized, a seeded Monte Carlo reproduces each published relative risk within the stated tolerance. The tolerance is three times the standard deviation of the same estimate across 30 independent seeds, measured in the fixture-generation step and written into the fixture header, and the gate reports the observed divergence beside it rather than only pass or fail      | An observed divergence above three measured standard deviations on any published risk point, or a fixture header with no measured noise floor |
| **VAL-GATE-SAF-04** | The speed-and-separation protective distance formulation as reproduced in a named peer-reviewed paper, cited in the fixture header by author, journal, volume and equation number. The underlying technical specification is paid and is not redistributed | The computed protective separation reproduces the paper's worked example to the precision the paper prints. Deterministic. The gate covers the analytic check only; section 9 item 3 records that the primary safety model for a mobile robot is the scanner-field logic and not this formula, and section 9 item 19 records that no paper is named yet, so this row is an open question and not a passing gate | A reproduced separation differing at the paper's printed precision, or a fixture header naming no paper                                       |
| **VAL-GATE-SAF-05** | The `source_ref` of the selected `catalog/safety_pyramids.yaml` entry, which names an author, an edition and a page locator for the ratio row                                                                                                              | Over a seeded run long enough that the rarest class has an expected count of at least 30, the realized class ratios lie inside the Poisson 99 percent interval around the entry's ratio. The expected-count floor is what keeps the interval from being so wide that the gate cannot fail; the run length that achieves it is computed from the configured rates and recorded                                   | A realized ratio outside the Poisson 99 percent interval, or a run whose rarest expected class count is below 30                              |

### 7.6 Validation gates, energy, carbon and ESG

| Gate                | External reference                                                                                                                                                                                                                                                            | Assertion, tolerance and noise floor                                                                                                                                                                                                                                         | Falsified by                                                                                                         |
| ------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------- |
| **VAL-GATE-ENE-01** | 10 CFR 431.25, Tables 1 to 4, nominal full-load efficiency by horsepower and pole count for open and enclosed motors, retrieved from the eCFR on 2026-08-09 with HTTP 200. US Government work, public domain                                                                  | Full-load efficiency for every modeled rating and pole count matches the table within 0.1 percentage point, which is the precision the table prints. The IE class naming on `MotorNameplate` comes from a different, paid standard and is checked by no gate here            | Any modeled rating whose efficiency differs from the table by more than 0.1 percentage point                         |
| **VAL-GATE-ENE-02** | US Department of Energy fact sheet DOE/GO-10097-517, _Determining Electric Motor Load and Efficiency_, Equation 1 and its worked example, retrieved on 2026-08-09 with HTTP 200. US Government work, public domain                                                            | Three-phase power computed from the fact sheet's own example inputs reproduces its printed result within 0.1 kW, which is the precision the fact sheet prints. Twenty further nameplate cases are checked for the same form. Deterministic                                   | A computed value differing from the fact sheet's printed result by more than 0.1 kW                                  |
| **VAL-GATE-CAR-01** | ISO 14083, the transport-chain greenhouse gas quantification standard, through the GLEC Framework's published worked examples. Inputs and expected outputs are encoded as fixtures with the edition and clause locator; neither document is redistributed                     | Leg emissions, the tank-to-wheel and well-to-tank split, and intensity per tonne-kilometer reproduce the published examples to the precision those examples print, and not tighter. Deterministic                                                                            | Any example reproduced outside its own printed precision                                                             |
| **VAL-GATE-CAR-02** | GHG Protocol Scope 2 Guidance (2015), the amendment to the Corporate Standard that sets out the location-based and market-based methods, cited by chapter                                                                                                                     | Both totals are produced for every window, and they are equal to 1e-9 relative when no contractual instruments are configured (INV-ESG-03). Deterministic                                                                                                                    | A window carrying only one of the two totals, or unequal totals with no instruments configured                       |
| **VAL-GATE-CAR-03** | Regulation (EU) 2023/956 of 10 May 2023 establishing a carbon border adjustment mechanism, OJ L 130, 16 May 2023, page 52, retrieved from EUR-Lex on 2026-08-09 with HTTP 200, together with the Commission's published importer guidance and its worked declaration examples | Embedded emissions and certificates due reproduce the guidance's worked examples to the precision those examples print, under the pinned `regulation_version`. The certificate reduction for a carbon price paid at origin is checked to floor at zero, never to go negative | An example reproduced outside its printed precision, or a negative certificate count                                 |
| **VAL-GATE-CAR-04** | ISO 14044, the life cycle assessment requirements and guidelines standard, and its allocation hierarchy. Paid; `iso.org` refused automated retrieval on 2026-08-09 with HTTP 403, so the fixture header carries the clause locator from the purchased copy                    | Mass and economic allocation of a two-co-product transformation reproduce hand-computed shares to 1e-9 relative, and system expansion is refused with an error naming the node where the twin cannot subdivide. Deterministic                                                | A share differing beyond 1e-9, or a silent fallback where subdivision is impossible                                  |
| **VAL-GATE-ESG-01** | Commission Delegated Regulation (EU) 2023/2772 of 31 July 2023, supplementing Directive 2013/34/EU as regards sustainability reporting standards, OJ 2023/2772, 22 December 2023, retrieved from EUR-Lex on 2026-08-09 with HTTP 200                                          | Every datapoint in the shipped map is present in the report as populated or gapped, no datapoint outside the map appears, and the report's scope totals reconcile to the ledger within 1e-6 relative. Deterministic                                                          | A mapped datapoint absent from the report, a datapoint outside the map appearing, or a reconciliation gap above 1e-6 |

### 7.7 Validation gates, rostering

| Gate                | External reference                                                                                                                                                                                                                                                           | Assertion, tolerance and noise floor                                                                                                                                                                                                                                                                                                                                                                   | Falsified by                                                                                                           |
| ------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ | ---------------------------------------------------------------------------------------------------------------------- |
| **VAL-GATE-ROS-01** | The nurse rostering benchmark instance library at `schedulingbenchmarks.org/nrp/`, curated by Tim Curtois, instances 1 to 24, whose published tables carry a best-known lower bound and a best-known solution with proven optima in bold. Retrieved 2026-08-09 with HTTP 200 | On every instance the library marks as having a proven optimum, the solver returns that objective value with status OPTIMAL inside the declared deterministic budget. Exact equality on an integer objective                                                                                                                                                                                           | Any proven-optimal instance where the solver returns a different objective or a non-OPTIMAL status                     |
| **VAL-GATE-ROS-02** | The same library's published best-known solution values for the instances without a proven optimum, plus Curtois and Qu, "Computational results on new staff scheduling benchmark instances", cited in the fixture header                                                    | On the small instances, restricted to the constraint set the benchmark defines, the solver reaches within 5 percent of the published best-known value inside the declared deterministic budget. The translation from the benchmark's constraint vocabulary to this section's is itself tested, and any constraint that cannot be expressed is listed in the fixture header rather than quietly dropped | A gap above 5 percent on any listed instance, or a fixture header that omits an inexpressible constraint               |
| **VAL-GATE-ROS-03** | The library's own statement that "All solutions are verified before being reported on this website", which makes its published solutions an independent oracle for the checker                                                                                               | The independent checker accepts every published best-known solution translated into this section's rule vocabulary, and rejects each of 20 deliberately corrupted copies of them, naming the corrupted rule in every case                                                                                                                                                                              | Any published solution the checker rejects, or any corrupted copy it accepts, or a rejection that names the wrong rule |

### 7.8 Seeded end-to-end scenarios

Every scenario runs at a fixed seed with a golden-file comparison of the resulting capability-report
fragment and the what-if answer table.

| Scenario                               | Setup                                                                                                                         | Asserts                                                                                                                                                                                                                                                                                                                                                                                         |
| -------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `SCN-HS-01` lift aid                   | 30 sim-days, baseline against `lift_assist_station_2`                                                                         | station risk index falls, the driving component changes, the LSS hypothesis test is present with its chosen test named, projected recordables and injury cost avoided are populated, payback is computed, and the answer carries all three required blocks                                                                                                                                      |
| `SCN-HS-02` rotation                   | `rotate_operators_2h`                                                                                                         | mean cumulative damage across the workforce is unchanged within tolerance while its Gini falls, and the throughput cost is quantified and attributed to re-familiarization                                                                                                                                                                                                                      |
| `SCN-HS-03` AMR proximity              | AMR count raised in one aisle                                                                                                 | near-miss rate rises, slow-field entries cost measurable throughput and energy, incidents follow the configured pyramid within Poisson confidence, TRIR rises, and both Paretos are produced                                                                                                                                                                                                    |
| `SCN-HS-04` PPE drift                  | PPE compliance degraded mid-run                                                                                               | CV checks detect it, findings cite the SOP clause, and every artifact states the imagery is synthetic                                                                                                                                                                                                                                                                                           |
| `SCN-HS-05` fatigue to quality         | a roster with backward rotation and quick returns against a forward-rotating one                                              | mispick rate rises measurably on the worse roster, the LSS engine raises the quality finding, and the causal layer recovers the fatigue-to-error edge when asked                                                                                                                                                                                                                                |
| `SCN-HS-06` idle energy                | a conveyor left running while starved                                                                                         | an `IDLE_ENERGY_WASTE` finding fires with kWh, dollars, kgCO2e, the counterfactual, and the break-even idle duration                                                                                                                                                                                                                                                                            |
| `SCN-HS-07` demand peak                | AMR charging left on-peak against shifted                                                                                     | demand charge falls, energy per pallet is unchanged, and the marginal carbon delta differs in sign from a naive average-factor calculation, with both reported                                                                                                                                                                                                                                  |
| `SCN-HS-08` peak week roster           | forecast surge week, both robustness modes                                                                                    | the comparison table is published, understaffing and overtime costs move in the expected directions, and no hard constraint is violated in either roster                                                                                                                                                                                                                                        |
| `SCN-HS-09` fatigue-constrained roster | the fatigue constraint enabled against disabled                                                                               | the constrained roster raises labor cost and lowers projected recordables, and both numbers appear in the answer                                                                                                                                                                                                                                                                                |
| `SCN-HS-10` CBAM sourcing flip         | a metal-bearing input from a high-carbon origin                                                                               | the declaration is generated, landed cost changes, and the internal carbon price at which the supplier ranking flips is reported                                                                                                                                                                                                                                                                |
| `SCN-HS-11` carbon genealogy           | a lot split, kitted, partly scrapped and partly returned and refurbished                                                      | carbon closes end to end, embodied carbon lost to scrap is reported, and the refurbished units carry a lower footprint than new                                                                                                                                                                                                                                                                 |
| `SCN-HS-12` ESG report                 | one command over a fixed quarter, run twice on the pinned platform and once on each other supported platform                  | on the pinned platform the HTML and JSON are byte-identical after the declared normalizer strips the generation stamp; across platforms every datapoint id, `source` value and gap entry is identical and the maximum numeric divergence is reported rather than asserted (D-05). The JSON validates against the datapoint map, and the gaps register is non-empty with a reason on every entry |
| `SCN-HS-13` scorer seam                | the same slotting problem scored by `HeightWeightPenalty` and by `NioshLiftingIndexScore` on a fixture where the two disagree | the slotting ranking changes, so the `ErgonomicScore` seam of roadmap CD2 is proved load-bearing rather than assumed. This is a scenario and not a gate because its reference is this repository's own two implementations (D-11 rule 1)                                                                                                                                                        |
| `SCN-HS-14` unstaffed station          | a station whose `min_operators` cannot be met for one hour                                                                    | `twinflow.workforce.understaffing_opened` and `.._closed` bracket the interval, the station blocks rather than running slower, `UNDERSTAFFED_INTERVAL` is raised, and the realized throughput loss appears on the closing event                                                                                                                                                                 |

### 7.9 CI gates owned by this section

| CI gate                      | Runs                                                                                                                                                                                     | Cadence and budget                                                  |
| ---------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------- |
| `ergonomics-reference-gates` | Every VAL-GATE-ERG gate                                                                                                                                                                  | Every push, under 60 seconds, because they are pure and fast        |
| `safety-model-gates`         | Every VAL-GATE-SAF gate, including the Monte Carlo gate of VAL-GATE-SAF-03                                                                                                               | Every push, under 4 minutes, path-filtered to the workforce package |
| `roster-benchmark`           | VAL-GATE-ROS-01, 02 and 03 on the small instance set at a fixed deterministic budget                                                                                                     | Nightly, because it is the slowest gate here                        |
| `carbon-closure`             | `prop_carbon_closure` and `prop_carbon_walk_order_stable` on the end-to-end scenario                                                                                                     | Every push                                                          |
| `esg-golden`                 | `SCN-HS-12` golden files on the pinned platform, plus the cross-platform divergence report                                                                                               | Every push on the pinned platform, weekly on the others             |
| `whatif-envelope-contract`   | Every registered what-if scenario in the repo, asserting all three blocks are present and that a null block carries a reason string                                                      | Every push                                                          |
| `agent-answer-contract`      | Every `run_whatif` and `get_ergonomic_risk` answer template, asserting that an answer carrying `index` also carries `band` and `governing_component`                                     | Every push                                                          |
| `model-card-completeness`    | Every coefficient the code marks as declared, asserting it appears in a model card with a stated range                                                                                   | Every push, and it fails if a declared parameter is undocumented    |
| `safety-pyramid-provenance`  | Every row of `catalog/safety_pyramids.yaml`, asserting a `source_ref` with an author, an edition and a locator                                                                           | Every push                                                          |
| `gate-evidence-contract`     | Every VAL-GATE row in section 7.4 to section 7.7, asserting the fixture header names an external reference, a tolerance, a noise floor where the quantity is stochastic, and a falsifier | Every push                                                          |

`gate-evidence-contract` is the gate that keeps D-11 from decaying. A new gate added without a
fixture header that names all four fails the build, so the discipline is mechanical rather than a
review habit.

---

## 8. Phase placement

Nothing here is cut, deferred or optional. Everything is sequenced, and every move off the author's
stated position carries the dependency that forced it. The phase identifiers and their release tags
are the roadmap's, not this section's: where an earlier draft of this section invented a slot name,
the roadmap's name replaces it, and section 8.2 records what changed.

### 8.1 The placement table

| Phase            | Tag              | What lands                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                | Why here                                                                                                                                                                                                                                                                                                                                             |
| ---------------- | ---------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **P0**           | v0.1.0           | The `station` fields of section 4.4 in the facility schema, the `ErgonomicScore` and `AbsenteeismModel` protocol declarations in the protocol registry, and the safety severity floor rule in the alarm-rationalization contract                                                                                                                                                                                                                                                                          | P0 freezes the config schema and the protocol registry, and both seams have consumers before either implementation exists                                                                                                                                                                                                                            |
| **P1**           | v0.2.0           | One operator resource with one shift pattern seizing the one station. One power meter on that station. `twinflow.energy.meter_read` and a trivial `twinflow.energy.window_closed` with kWh per pallet. The `twinflow.twin.activity_completed` operator fields                                                                                                                                                                                                                                             | The walking skeleton is where a station first has an occupant and a meter, and the activity event gains its operator fields before any recorded run exists                                                                                                                                                                                           |
| **P2**           | v0.3.0           | The three what-if blocks reserved on `twinflow.agent.whatif_completed` in the null-with-reason form, and the `FindingKind` members of section 4.3 with `carbon_kgco2e` reserved on `twinflow.lss.finding_raised`. Energy per pallet and operator utilization routed through the LSS engine as charted metrics                                                                                                                                                                                             | P2 is where `twinflow.agent.whatif_completed` is first registered, and C3 makes the registry additive-only within a major version. A required property added after registration is a major bump on the most-read event in the system, so an optional operator-impact block is one the agent will eventually skip                                     |
| **P3b**          | v0.5.0           | `twinflow-energy` in full and `twinflow-workforce`'s E6 half: motor-current and power sensors, part-load efficiency, exact state partitioning, energy per pallet and per order, idle-energy waste, demand charges, grid carbon at both resolutions; operators as first-class resources, shift patterns, the cross-training matrix, workload balance, the unused-talent finding, `OperatorImpact` computed for real. **E6 and E7 both complete here**                                                      | The roadmap places E6, E7 and E9 at the head of P3b, ahead of component 1b, because 1b's automation what-ifs must answer with "throughput, cost, energy, and operator-impact deltas". Neither item can follow its consumer                                                                                                                           |
| **P3d**          | v0.7.0           | The requirement curve: half-hourly labor requirements from the forecast at a declared quantile of the bound producer's interval, and measured labor standards with provenance                                                                                                                                                                                                                                                                                                                             | The forecaster and its interval contract exist at P3d. The requirement curve is useful before any solver exists, because it is what makes staffing visible                                                                                                                                                                                           |
| **P3f**          | v0.9.0           | Circularity inputs: recovery versus scrap rates and embodied carbon lost to scrap, from the returns disposition flow                                                                                                                                                                                                                                                                                                                                                                                      | Returns land at P3f, and the source itself notes the sustainability tier extends naturally into recovery versus scrap                                                                                                                                                                                                                                |
| **ECON**         | v0.13.0          | **E17** in full: supplier emission factors, cradle-to-gate footprints, inheritance through the genealogy graph, transport legs on the ISO 14083 basis, allocation across shared vehicles, the per-shipment ledger, refrigerant fugitive emissions, CBAM declarations and certificate arithmetic, and carbon into landed cost                                                                                                                                                                              | The roadmap places E17 in ECON beside E14 and E22, and ECON follows P3h, so the transport network the leg calculator consumes already exists. CBAM shares the HS code and country-of-origin master with E14, so building it anywhere else duplicates that master                                                                                     |
| **6a10**         | v0.14.0          | `twinflow-ergonomics` in full and `twinflow-workforce`'s safety half: the published assessment methods, cumulative load across a shift, the fatigue model and its feedback into service time and defect rate, proximity and near-miss detection, incident generation by both generators, TRIR and the rate family, the near-miss Paretos, the station injury-risk index, and both ergonomic what-ifs with their ROI answers. Safety and structural sensors land with it                                   | The author's own ordering, which the roadmap keeps. The AMR fleet (P3b), the pick and pack stations (P3g), the production stations (P3i) and the returns triage (P3f) all have to exist before the near-miss and cumulative-load layers have a full operation to measure                                                                             |
| **ROST**         | v0.16.0          | `twinflow-roster` in full: the CP-SAT model, the fatigue constraint, both robustness formulations, the independent checker, roster feedback into the twin as actual staffing, and roster scoring                                                                                                                                                                                                                                                                                                          | The roadmap places E23 at v0.16.0, ahead of 6a14 and 6a12. By this tag the forecast (P3d), the skills matrix (P3b) and the fatigue model (6a10) all exist, which is what "with the existing fatigue model as a constraint" needs. The absenteeism model is the one input that does not, resolved by CD1's `ConfiguredRateAbsenteeism` reading config |
| **6a14**         | v0.20.0          | The behavioral `AbsenteeismModel` implementation, the worker master, and training hours and turnover with the regretted split flowing into the social block. No change to `twinflow-roster`                                                                                                                                                                                                                                                                                                               | The protocol seam means the roster package is untouched by this handover, which is the point of specifying it that way                                                                                                                                                                                                                               |
| **P4**           | v0.27.0          | The CV half of 6a10: PPE spot-checks, posture observation from synthetic frames, the observed-versus-design agreement metric, SOP clause citation on violations                                                                                                                                                                                                                                                                                                                                           | The CV channel lands at P4. Until then posture assessment uses the design profile and every artifact says which source it used, so none implies a measurement that did not happen                                                                                                                                                                    |
| **P5**           | v1.0.0           | Dashboard panels with the C12 accessibility rules, the ergonomics and safety sections of the capability report, and the demo path through a safety finding to an ROI answer                                                                                                                                                                                                                                                                                                                               | The polish tag. The safety tile is the panel most likely to be screenshotted, so it lands with the polish pass rather than before it                                                                                                                                                                                                                 |
| **P6-W2**        | v1.2.0           | The calibrated interval producer behind `roster.service_level`, from E31, and the causal validation of the fatigue-to-error edge is prepared here for CAUSAL                                                                                                                                                                                                                                                                                                                                              | E31 lands at P6-W2 and populates the same three interval properties P3d reserved, so no config key changes and no earlier phase waits on it                                                                                                                                                                                                          |
| **P6-W5**        | v1.5.0           | **E39** in full: the one-command report, Scope 1/2/3 assembly, the ESRS map, the double-materiality readiness matrix, the gaps and assurance register. E38 prices premiums from TRIR and loss history, and E40 drives floor condition and HVAC load                                                                                                                                                                                                                                                       | The roadmap places E39, E38 and E40 together at P6-W5. The social block needs TRIR (6a10) and turnover (6a14), the financial-materiality axis needs the financial twin (6a17), and Scope 3 category 1 needs procurement spend (6a13), so P6-W5 is the first tag at which every input exists                                                          |
| **P6 hardening** | v1.1.0 to v1.6.0 | E6 gains the full Yamazumi deliverable and the heijunka leveling scenario library; E7 gains the load-shifting optimization; E17 gains digital product passport linkage (E10b, P6-W4) and the signed-footprint path (E35b, P6-W4); E23 gains the Optuna weight tuning and the multi-objective front; E39 gains digital tagging readiness. CAUSAL (v0.23.0) validates the fatigue-to-error edge, E21b (P6-W4) gains a safety role agent, and E43b (P6-W2) puts the absenteeism model under model governance | Each of these depends on an item that itself lands in the tag named beside it, so none can precede its own dependency                                                                                                                                                                                                                                |

### 8.2 Resequencing decisions and their justification

Four moves off the author's stated order, each of them either a roadmap ruling this section now
follows or an application of the principle the author accepted, that an item which is an upstream
dependency of earlier work moves ahead of its dependents.

1. **E6 and E7 move from Phase 6 to the head of P3b.** Component 1b requires the automation what-ifs
   to be "answered with throughput, cost, energy, and operator-impact deltas". P3b is where those
   what-ifs land, so neither item can follow its consumer. This is roadmap R10a and R10b.
2. **The three what-if blocks are reserved at P2 rather than P0.** An earlier draft of this section
   put them at P0, which is wrong on its own terms: `twinflow.agent.whatif_completed` does not exist
   until component 7 lands at P2, and a property cannot be reserved on a schema that has not been
   registered. P2 is the first moment the reservation is possible and the last moment it is free,
   because C3 makes a required property added after registration a major version bump. Roadmap section 5.9
   already reserves `operator_impact` and `energy_delta_kwh` at P2, and this section adds the two
   remaining properties at the same point.
3. **6a10 does not split; the scoring library lands whole at 6a10.** An earlier draft moved
   `twinflow-ergonomics` forward to P3b so the slotting objective could consume it. Roadmap CD2
   settles that differently: P3b ships `HeightWeightPenalty`, a static rule, behind the
   `ErgonomicScore` protocol, and 6a10 defines the ergonomic index. This section follows the roadmap,
   which is why `twinflow-workforce` takes `twinflow-ergonomics` through an extra rather than in its
   core install (section 2.3). Nothing is dropped and no capability is reduced; the seam is what carries P3b.
4. **E17 lands whole in ECON rather than splitting across P3e, P3h and a separate CBAM slot.** An
   earlier draft split it because the transport-leg calculator needs a transport network. ECON follows
   P3h, so the dependency is satisfied without a split, and the roadmap's R14b places E17 there beside
   E14 so the trade-policy master data is built once.

### 8.3 What each phase leaves shippable

The quickstart stays intact at every step because every new implementation is registered behind an
existing protocol that already has one. A reader running the P3b quickstart gets an energy delta and
an operator impact on their what-if answer. A reader running it before P3b gets an explicit
"provider absent" reason in the same property, which is a shippable and honest answer rather
than a missing one. A reader running it before 6a10 gets an ergonomic score from
`HeightWeightPenalty` with `method_id` naming it, so no artifact ever implies a lifting index the
run did not compute.

---

## 9. Open questions

Genuine ambiguities an implementer will hit. None of these has been resolved by invention.

1. **Redistribution terms for the posture and OCRA scoring tables.** The RULA, REBA and OCRA scoring
   tables originate in copyrighted journal articles, and the official worksheets are freely
   distributed without an open license. The repo is Apache-2.0 and publishes to PyPI. Three options:
   encode the tables as data with attribution and a NOTICE file, on the argument that a lookup table
   of an assessment method is a method rather than an expression; ship an installer step that fetches
   the worksheets at first use; or restrict the shipped default to the lifting equation, which is a US
   Government work and unambiguously public domain, with the posture scorers behind an extra whose
   install prints the attribution. A decision is needed before `twinflow-ergonomics` is published, and
   it changes what VAL-GATE-ERG-03, 04 and 07 can assert.

2. **Paid standards used as method sources.** The separation-distance formulation, the driverless
   industrial truck safety standard, the transport chain emissions standard and the sustainability
   reporting standards are all paid documents. The proposed approach encodes only example inputs and
   expected outputs as fixtures, cites the document, and prefers peer-reviewed papers that reproduce
   the formula where one exists. Confirm this is acceptable, and confirm that citing a standard the
   repo has not redistributed is the intended posture rather than avoiding the standard entirely.

3. **Applying a collaborative-robot separation formula to autonomous mobile robots.** The
   speed-and-separation monitoring formulation was written for manipulators, not for mobile robots,
   which are governed by a different standard built around safety-scanner fields. Proposal: use the
   safety-field logic as the primary model and the separation formula as a secondary analytic check,
   and say so in the docs. This is exactly the kind of detail an industrial reader will probe, so
   getting the framing right matters more than getting a number.

4. **The pyramid ratio values, and how hard the causal reading is disclaimed.** Two parts, one
   mechanical and one editorial. Mechanical: neither Heinrich (1931) nor Bird and Germain are
   documents this specification could retrieve, so no ratio value appears anywhere in this section
   and `catalog/safety_pyramids.yaml` ships with its rows transcribed from the primary editions at
   implementation time, each carrying an author, an edition and a page locator. Confirm which
   editions to transcribe from, since the ratios are quoted inconsistently in the secondary
   literature and a transcription from a textbook restatement is not a transcription from the source.
   Editorial: using the ratios as a generative sampling device is defensible, and Marshall, Hirmas and
   Singer (2018) is the peer-reviewed anchor for treating the proportions as close to stable.
   Claiming that removing near misses removes fatalities is a different claim, is not supported, and
   is contested. The plan builds a second, independent hazard-rate generator and publishes the
   comparison. Confirm the README carries the caveat prominently rather than in a footnote, since the
   alternative is that an informed reader finds the weakness before the author points at it.

5. **The fatigue-to-error and fatigue-to-slowdown coefficients have no public warehouse source.** The
   shift-work relative-risk literature anchors the hours-on-shift and successive-night terms. Nothing
   public ties cumulative physical load to pick error rate or speed decrement in a distribution
   center. Proposal: declare them as model parameters in a model card with stated ranges, publish a
   sensitivity analysis showing which conclusions survive the range, and use the shift-work risk curve
   as a cross-check on the shape. Confirm this is preferred over picking a number and defending it.

6. **Which safety rate is the README headline.** Recordable incidence rate per 200,000 hours is the US
   convention; lost-time injury frequency per 1,000,000 hours is the international one. The shipped
   facility profiles are deliberately unlocated. Proposal: compute both always, let
   `safety.regulatory_region` pick the displayed default, and headline the recordable rate because
   the target audience is largely US. Confirm.

7. **Which snapshot of the border carbon adjustment rules to pin.** The regime's implementing rules,
   its treatment of indirect emissions by goods category, and its de minimis thresholds have all moved
   recently and will move again. The config carries `regulation_version`, but the shipped default has
   to be something. Proposal: pin the definitive-regime baseline, ship at least two scenario overlays
   so the mechanism visibly handles rule change, and state the pin date in the README.

8. **Employee commuting for synthetic workers.** Scope 3 category 7 needs commute distances that do
   not exist. Proposal: generate from a documented distribution, tag the data quality as PROXY, and
   have the gaps register say the category is calculated on a fabricated distribution. The alternative
   is declaring it a gap, which is more honest but less demonstrative of the mechanism. Which does the
   author prefer for a portfolio artifact?

9. **Average versus marginal grid emission factors.** The inventory standard expects an average factor
   for a Scope 2 disclosure, but load-shifting decisions only change marginal emissions. The plan
   computes both and uses each where it belongs, labeling every number. Confirm that a report which
   shows two different carbon numbers for the same electricity, each labeled, is the intended
   behavior rather than a source of confusion to be avoided.

10. **The deterministic budget and conflict cap the roster CI job uses.** The determinism question
    itself is settled and no longer open: D-04 bounds the solver by a deterministic budget, one
    worker, a fixed seed and a branch cap, and D-05 scopes the guarantee to byte-identity on the
    pinned platform and value-equivalence elsewhere, which INV-ROST-05 and section 5.17 now state. What is
    still open is arithmetic. A deterministic budget is not wall time, so the same budget takes
    different wall time on different runners, and `roster-benchmark` has to fit a job budget. Confirm
    the values of `roster.solver.max_deterministic_time` and `roster.solver.max_conflicts` the CI job
    uses, measured on the pinned reference runner, and confirm the nightly cadence section 7.9 assigns.

11. **Pose estimation model licensing for the observed-posture channel.** Most pose models ship weights
    under terms incompatible with an Apache-2.0 repo redistributing them. Proposal: ship no weights, pin a
    model identifier with a fetch step, default the posture path to sim ground truth, and make the CV
    comparison an opt-in extra. Confirm, and confirm whether the repo instead trains a tiny pose
    regressor on its own synthetic frames, which would be fully Apache-2.0 and would also be a more honest
    demonstration since the frames are synthetic anyway.

12. **What `HeightWeightPenalty` must preserve to be a usable stand-in.** An earlier draft proposed
    splitting 6a10 so the scoring library could land at P3b; roadmap CD2 settled that the other way
    and section 8.2 item 3 now follows it, so the split question is closed. The open question it leaves is
    sharper. INV-ERG-04 makes the lifting index monotone in horizontal distance, asymmetry and
    frequency, and the slotting objective in component 1b depends on that monotonicity for its ranking
    to mean anything. Confirm that `HeightWeightPenalty` is required to satisfy the same monotonicity
    contract, so that swapping in the real scorer at 6a10 changes the ranking's accuracy rather than
    its direction, and confirm whether `SCN-HS-13` asserts agreement in direction on top of the
    change in ranking it already asserts.

13. **Whether the operator model carries demographic attributes at all.** The social reporting standard
    asks for gender distribution and pay-gap datapoints. Synthesizing demographic attributes for a
    public portfolio repo carries an obvious optics risk and no engineering benefit. Proposal:
    `esg.social.demographics` defaults to false, and the affected datapoints appear in the gaps
    register with reason `DISABLED_BY_CONFIG` and an explicit note that the omission is deliberate.
    Confirm.

14. **What "energy delta in every what-if answer" includes.** Operational energy is unambiguous. The
    embodied carbon of the intervention itself, the manufacture of the powered lift aid or the AMR fleet, is
    the honest full accounting and needs capital-goods factors that mostly do not exist for synthetic
    equipment. Proposal: always report the operational delta, report embodied carbon when the capex item
    carries a factor, and tag it PROXY otherwise with the gap named in the answer. Confirm, because the
    alternative reading is that a what-if which ignores the intervention's own footprint is incomplete.

15. **Subject and field spellings the sibling sections still have to adopt.** The subject question is
    settled for this section: foundations section 4.3 fixes subjects as `twinflow.<domain>.<event_name>`,
    snake_case, past tense, and section 4.1 now spells all thirty-seven of this section's subjects that way.
    What is open is the other side of three producer-consumer pairs. Sibling sections drafted before
    the rule reference `ergonomics.score.v1`, `roster.v1` and `energy.reading.v1`. The mappings are
    unambiguous, and that is the hazard: a contract test written against either spelling passes on its
    own side of a producer-consumer pair whose two halves cannot talk. The same reconciliation is needed one level down on field names: this section
    spells the `OperatorImpact` fields `utilization_by_operator` and `peak_utilization` and registers
    the metric `operator_utilization`, while twin-core section 5.11 and dashboard-replay section 3.9 spell the same
    fields with an `s`. Proposal: the American spelling throughout `schemas/registry.yaml`, since the
    metric layer and the agent's governed metric names already use it, and a registry-wide sweep
    before P0 freezes the manifest.

16. **Which finding owns the "eighth waste" label.** The source calls idle energy an eighth-waste
    LSS finding (E7), while the canonical eighth waste in the lean literature is non-utilized talent,
    which E6's `UNUSED_SKILL_CAPACITY` also expresses. Both capabilities ship and neither is
    reduced; only the label collides. Proposal: keep the classical seven wastes plus non-utilized
    talent as the eighth, and register idle energy as a named ninth waste ("energy") in the waste
    taxonomy the LSS engine renders, with the README stating the deviation from the source's wording
    and the reason. Confirm, or confirm the opposite assignment, because the waste taxonomy is
    rendered in the capability report and on the VSM and cannot carry two eighths.

17. **Whether `carbon_delta` is reserved on the what-if payload at P2.** Roadmap section 5.9 reserves
    `operator_impact` and `energy_delta_kwh` on `twinflow.agent.whatif_completed` at P2 and does not
    list `carbon_delta`. C3 makes a required property added after a schema is registered a major
    version bump on the most-read event in the system, so `carbon_delta` is either reserved at P2
    alongside the other two or it is optional forever, and an optional carbon block on a what-if is
    one the agent will eventually skip. Section 4.4 assumes the former. This section cannot amend the
    reserved-field registry, so the roadmap owner has to confirm the addition, or confirm that E17's
    carbon block is deliberately optional and say why in the roadmap rather than here.

18. **Whether `energy_delta_kwh` and `energy_delta` both stay.** The same registry names a scalar
    where section 3.9 defines a structured block with a per-asset breakdown and a confidence interval. Section 4.4
    keeps both, the scalar as the headline number and the block beside it, which is additive and safe
    but leaves two fields that can disagree. The alternative is one block and a derived scalar in the
    metric layer. Confirm which, because a consumer that reads only the scalar and a consumer that
    reads only the block will otherwise report different numbers for the same what-if.

19. **Which peer-reviewed paper VAL-GATE-SAF-04 cites.** The gate needs a named paper that reproduces
    the speed-and-separation protective distance formulation with a worked example, because the
    underlying technical specification is paid and is not redistributed, and D-11 rule 1 needs a
    specific reference with a locator rather than a category of literature. No such paper is named
    here, so until one is chosen and its example transcribed, VAL-GATE-SAF-04 is an open question and
    not a passing gate, and `gate-evidence-contract` in section 7.9 fails it on the missing fixture header.
    That is the intended behavior: a gate with no valid external reference does not pass.
