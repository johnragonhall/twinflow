---
title: "Process twin, automation and robotics, slotting, and the what-if engine"
description: Implementation contract for the discrete-event twin, its automation layer, slotting, the what-if and replay engine, twin-to-reality sync, and four optimisation capabilities.
topic_type: reference
audience: contributors
---

# Process twin, automation and robotics, slotting, and the what-if engine

Status: design contract. An implementer builds from this with TDD and does not need to guess.

---

## 1. Scope

This section is the implementation contract for the discrete-event process twin, the automation and
robotics layer inside it, the slotting layer, the what-if experiment engine, and the twin-to-reality
sync connector. It also owns the four optimisation and learning capabilities that sit on top of the
twin.

### 1.1 Requirements covered in full

| Requirement                | Source text (abbreviated)                                                                                                                                                                                                                                                                                                                                                                                                                           | Covered in                                       |
| -------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------ |
| **1**                      | Process twin: DES of receiving and putaway (trucks, dock doors, unload, scan, convey, sort, putaway) with realistic variability; parameters in one config file; computes takt, cycle times, WIP, utilisation, OEE; identifies the bottleneck; produces a value-stream summary                                                                                                                                                                       | 2.1, 3.1 to 3.4, 5.1 to 5.5, 6.1, 7              |
| **1b**                     | AGV/AMR fleet (task allocation, traffic and deadlock management, battery and charging, congestion as measurable bottleneck source); robotic palletiser cell (cycle time distributions, jam and fault modes, recovery time); ASRS with crane scheduling; conveyor sortation with divert logic; slotting on velocity, cube, affinity, ergonomics; automation what-ifs answered with throughput, cost, energy and operator deltas plus the LSS verdict | 2.2, 2.3, 3.5 to 3.9, 5.6 to 5.11, 6.2 to 6.4, 7 |
| **6**                      | Bi-directional twin/reality sync: twin recalibrates from telemetry, divergence is itself a finding, accepted what-ifs flow back as config                                                                                                                                                                                                                                                                                                           | 2.5, 3.12, 5.14 to 5.16, 6.6                     |
| **7 (what-if parts only)** | `run_whatif(config_change)` and `compare_scenarios` ranked by throughput gained per dollar, producing an investment-roadmap table                                                                                                                                                                                                                                                                                                                   | 2.4, 5.12, 5.13, 6.5                             |
| **E4**                     | Event-sourced replay and counterfactuals: replay the historian event log through a modified config; time-travel debugging of any finding                                                                                                                                                                                                                                                                                                            | 2.4, 5.13, 7.5                                   |
| **E5**                     | Autonomy tiers L1 advise, L2 recommend with approval, L3 auto-apply within guardrails; approved what-if flows back through the bi-directional connector; audit trail of who or what changed the line and why                                                                                                                                                                                                                                        | 2.5, 3.13, 4.6, 5.17                             |
| **E9**                     | Optimisation engine: search over twin configurations under a cost budget, feeding the scenario-ranking table                                                                                                                                                                                                                                                                                                                                        | 2.6, 5.18, 7.6                                   |
| **E11**                    | Learning-based AGV dispatch benchmarked honestly against the rule-based dispatcher on identical scenarios, comparison table published either way                                                                                                                                                                                                                                                                                                    | 2.7, 5.19, 7.7                                   |
| **E12**                    | Yard and dock scheduling optimisation: truck arrival slotting and dock-door assignment optimised against the twin                                                                                                                                                                                                                                                                                                                                   | 2.6, 5.20, 7.8                                   |
| **E28**                    | Neural twin surrogate for millisecond approximate what-ifs, always validated against the full sim with the error distribution published; agent searches with the surrogate, confirms winners with the sim                                                                                                                                                                                                                                           | 2.8, 5.21, 7.9                                   |

Engineering-craft and adoption requirements this section is bound by and contributes to, owned
elsewhere, obligations discharged here: **C1** determinism (5.2, 7.4), **C2** sim clock (5.2),
**C3** schema registry (4), **C4** test tiers (7), **C5** config validation (6), **C9** semver on
`facility.yaml` and event schemas (4, 6), **C10** the CI matrix (5.2, 7.4), **A1** take-one-brick
packaging (2), **A2** bring-your-own-facility across the three worked profiles (6, 7.4), **A3**
deployment tiers (5.3).

### 1.2 Interfaces consumed but not owned here

| Interface                       | Owner        | Needed by this section from | Fallback when absent                                        |
| ------------------------------- | ------------ | --------------------------- | ----------------------------------------------------------- |
| Operator model, fatigue index   | E6           | P3b                         | `OperatorProvider` null implementation, constant capability |
| Energy KPIs per resource        | E7           | P3b                         | `energy_delta` reported as null with a stated reason        |
| Ergonomic score (NIOSH, RULA)   | 6a10         | P3b                         | `ergonomic_provider: proxy_v1`, formula in 3.9              |
| Findings, hypothesis tests, SPC | 5 (LSS)      | P2                          | Comparison ships without `lss_verdict`, flagged as such     |
| Alarm rationalisation           | 5 (LSS)      | P3                          | Divergence findings are not deduped; 5.15 states the risk   |
| Telemetry, device faults        | 2 and 2b     | P3                          | Calibration and divergence do not run                       |
| Order streams and affinity      | 6a3 and 6a6  | P3e                         | Synthetic order-line generator, 9 Q4                        |
| Labour roster                   | E23          | P6                          | `LabourProfileProvider` null implementation, 5.20           |
| Synthetic scenario corpora      | E25          | before E11                  | RL curriculum runs on the three A2 profiles only            |
| Replay viewer                   | E1           | after P2                    | Not needed to run the twin                                  |
| Financial twin, NPV and capex   | 6a17 and E22 | P6                          | Ranking table carries payback and annualised cost only      |

### 1.3 Amendment proposed to C3, stated as an amendment

C3 as locked names the versioned schema registry as the only interface between packages. This
section proposes extending that rule, and states the extension here rather than presenting it as a
restatement, because every brick below imports another brick's Python objects.

Grounds: an event is the right contract between processes and the wrong contract inside one process.
A dispatch decision happens thousands of times per simulated hour inside a single SimPy environment,
and routing it through a serialised schema would make the twin slower than the operation it models.
The extension is narrow: cross-brick communication is by versioned schema'd event from `/schemas`
(C3), or by one of the published protocol classes listed below.

| Protocol                | Owning package        | Method surface                                                | Consumers                          |
| ----------------------- | --------------------- | ------------------------------------------------------------- | ---------------------------------- |
| `ResourceProvider`      | `twinflow-twin`       | `register(TwinModel, Facility) -> None`                       | automation, upstream factory (3i)  |
| `OperatorProvider`      | `twinflow-twin`       | `capability(operator_id, sim_ts) -> OperatorCapability`       | twin, E6                           |
| `StateView`             | `twinflow-twin`       | Declared read-only field set, 2.1                             | automation, dispatch-rl, optimize  |
| `DispatchPolicy`        | `twinflow-automation` | `assign(tasks, fleet, state) -> list[Assignment]`             | dispatch-rl, optimize              |
| `RoutingPolicy`         | `twinflow-automation` | `route(amr, origin, dest, state) -> Route`                    | dispatch-rl, research competitors  |
| `Evaluator`             | `twinflow-optimize`   | `evaluate(config) -> ObjectiveVector`                         | surrogate                          |
| `SurrogateModel`        | `twinflow-surrogate`  | `fit`, `predict`, `predict_interval`                          | optimize                           |
| `LabourProfileProvider` | `twinflow-optimize`   | `profile(window) -> list[LabourInterval]`                     | E12, E23                           |

The list lives in `/schemas/protocols/twinflow-protocols.v1.yaml` beside the event schemas: one
entry per protocol, carrying the method names, the parameter and return type names, and a semver.
The same CI contract test that fails on producer and consumer schema drift also fails when a
package's implementation no longer matches the declared protocol surface, and a protocol change is a
MAJOR bump under C9. Without that file the extension would be an unchecked exception to C3, which is
the failure mode the rule exists to stop.

### 1.4 Doctrine rulings applied

| Ruling | Applied as                                                                                              | Where                  |
| ------ | ------------------------------------------------------------------------------------------------------- | ---------------------- |
| D-01   | Run identity is the kernel's hashed core plus an unhashed provenance sidecar                            | 4.1, 5.2               |
| D-02   | Every wall-clock measurement leaves the tape for the metrics sink or the provenance sidecar             | 4.9, 5.2, 5.6, 5.20    |
| D-03   | No collection whose iteration order reaches an event, a hash or a branch is a `set`                     | 3.1 to 3.3, 3.9, 5.2   |
| D-04   | CP-SAT runs on a deterministic budget; learned inference runs through the `Inference` port              | 5.19, 5.20             |
| D-05   | Byte-identical on a pinned platform, value-equivalent across platforms with a measured tolerance        | 5.2, 7.4               |
| D-06   | The Rust agent's stream contract is the fleet section's; its boundary with this one is 9 Q19            | 9                      |
| D-07   | The envelope is the kernel's; the canonical order is `(twinflowsimts, twinflowproducerid, twinflowseq)` | 4                      |
| D-08   | The live telemetry subscriber binds `Network`; analytics fan-out binds `EventBus`                       | 2.5, 4, 5.3            |
| D-09   | Run identity and run completion are kernel-owned events; this section publishes neither                 | 2, 4, 4.1              |
| D-11   | Every gate names an external reference, a tolerance, a noise floor and a falsifier                      | 7.4                    |
| D-12   | Every test names the observation that fails it, and no test asserts a tautology                         | 5.3, 7.1 to 7.9        |
| D-13   | Every gate's repetition count carries an asserted runtime budget                                        | 7.4, 7.10              |

Nothing in this section is deferred or optional. Where an item lands later than another, section 8
gives the dependency reason.

---

## 2. Packages

Eight independently installable bricks. Each has its own `README.md`, its own test suite, its own
`pyproject.toml`, and its own PyPI name. They share the PEP 420 namespace package `twinflow`. No
brick imports another brick's internals; cross-brick communication is by versioned schema'd event
from `/schemas` (C3) or by a protocol class in the 1.3 table.

All eight depend on `twinflow-kernel` (owned by the foundations section) for the seams: `Clock`,
`Rng`, `Network`, `EventBus`, `Storage`, `Inference`. None of them import `time`, `datetime.now`,
`random`, or a socket library directly. The nondeterminism gate in
`scripts/checks/nondeterminism-gate.sh` fails CI on any such import outside the kernel package
(D-02), and C1's repeated-run hash check backstops it.

### 2.1 `twinflow-twin`

Purpose: the discrete-event process twin of receiving and putaway, its metric engine, its bottleneck
detector, and its value-stream summary. This is component 1 in its entirety. Installable alone: a
reader who wants only a warehouse DES with Lean metrics takes this brick.

Runtime dependencies: `twinflow-kernel`, `twinflow-schemas`, `simpy` (4.1.2, MIT), `pydantic`,
`numpy`, `pyyaml`, `duckdb` (1.5.5, MIT, metric queries), `deltalake` (1.6.2, Apache-2.0, event log
writer, optional extra `[historian]`). Versions and licences are the verified values recorded in the
repository's dependency ledger.

Public API:

```python
from twinflow.twin import (
    Facility,            # validated facility.yaml -> object graph
    load_facility,       # (path | dict, *, strict: bool = True) -> Facility
    TwinModel,           # the SimPy model; owns stations, resources, flows
    TwinRun,             # one execution: run_id, seed, mode, event log handle
    run,                 # (facility, *, seed, horizon, mode, log) -> TwinRun
    EventTape,           # append-only writer/reader of twin.* events
    TwinSnapshot,        # serialisable full state at a sim instant
    MetricEngine,        # windowed KPI computation over an event log
    WindowMetrics,       # takt, cycle time, WIP, utilisation, OEE, throughput
    BottleneckReport,    # three detectors plus agreement flag
    ValueStreamSummary,  # per-station ladder, VA/NVA, PCE
    StateView,           # read-only observation of live model state
    OperatorProvider,    # Protocol, null implementation shipped
)
```

The event log this section writes is the run's `events.ndjson`, and `EventTape` is the writer and
reader for it. The prose below calls the file the event log and never calls it anything else.

`StateView` matters: it is the only object a dispatcher, an optimiser, or an RL policy may read. Its
field set is declared as a frozen allowlist in `twinflow/twin/state_view.py`, and every field is a
quantity a real WMS would hold at that instant. The deny list is explicit: no pending event queue,
no RNG state, no fault schedule, no arrival time that has not yet happened, no ground-truth
parameter. Section 7.2 INV-RL-01 and section 7.7 assert observation parity between E11's policy and
the rule-based dispatchers, which is the entire basis of the honest-benchmark claim.

### 2.2 `twinflow-automation`

Purpose: component 1b's four automation subsystems as first-class simulated resources with their own
failure modes and telemetry. Depends on `twinflow-twin` (registers resources into `TwinModel`
through the `ResourceProvider` protocol) and `twinflow-kernel`. Excludes RL and solver dependencies
so the brick stays small to install.

Runtime dependencies: `twinflow-twin`, `twinflow-kernel`, `twinflow-schemas`, `networkx` (travel
graph and wait-for graph), `numpy`.

Public API:

```python
from twinflow.automation import (
    AmrFleet, Amr, TravelGraph, ReservationManager, ChargingPolicy,
    Assignment,                # (task_id, amr_id, reason_code)
    DispatchPolicy,            # Protocol: assign(tasks, fleet, state) -> list[Assignment]
    RoutingPolicy,             # Protocol: route(amr, origin, dest, state) -> Route
    NearestVehicleFirst, EarliestDueDate, ContractNetAuction, RandomDispatch,
    ReservationRouting,        # the shipped RoutingPolicy
    PalletiserCell, PalletPattern, JamModel,
    AsrsAisle, StackerCrane, CraneScheduler, SingleCommandCycle, DualCommandCycle,
    Conveyor, ConveyorSegment, Sorter, Diverter, DivertDecision, Chute,
    ScanPoint, ReadOutcome,
    register_automation,       # (TwinModel, Facility) -> None
)
```

`DispatchPolicy` has one signature, given above and in 5.6, and `Assignment` is exported because it
is the return type. `RoutingPolicy` is exported so the alternative traffic protocol of section 9 Q7
is implementable without a fork. Both protocols are declared here, in the light brick, so the RL
brick depends on automation and not the reverse.

### 2.3 `twinflow-slotting`

Purpose: decide which SKU lives in which slot, on velocity, cube, affinity and ergonomics; measure
travel-distance and picks-per-hour deltas; compute re-slot labour payback. Installable alone: a
consultant who wants only a slotting engine takes this brick and feeds it a CSV.

Runtime dependencies: `twinflow-schemas`, `numpy`, `scipy` (`linear_sum_assignment`), `pandas`.
Optional extras: `[twin]` adds `twinflow-twin` for the measured-delta path; `[ergonomics]` adds
`twinflow-ergonomics` for the NIOSH and RULA score in place of the proxy whose formula section 3.9
states. Section 2.3 does not restate that formula, because two statements of one formula is how the
two drift apart.

Public API:

```python
from twinflow.slotting import (
    SlotGrid, Slot, SkuProfile, AffinityMatrix,
    SlottingObjective,       # weighted terms + hard constraints
    SlottingPlan, SlotMove,
    plan_slotting,           # (SlotGrid, list[SkuProfile], SlottingObjective) -> SlottingPlan
    coi_baseline,            # Heskett cube-per-order-index ordering, the reference optimum
    evaluate_plan,           # (SlottingPlan, DemandWindow) -> SlottingMetrics
    reslot_payback,          # (SlottingPlan, LabourRates) -> PaybackReport
)
```

### 2.4 `twinflow-scenario`

Purpose: the what-if experiment engine. Owns the scenario patch language, the replication and
common-random-numbers protocol, counterfactual replay (E4), the comparison and ranking table, and
the autonomy state machine's proposal side (E5).

Runtime dependencies: `twinflow-twin`, `twinflow-kernel`, `twinflow-schemas`, `pydantic`,
`duckdb`. Optional extras: `[lss]` adds `twinflow-lss` for the statistical verdict;
`[automation]` for automation-touching patches.

Public API:

```python
from twinflow.scenario import (
    ScenarioPatch, PatchOp, ExogenousBoundary,
    Scenario, ScenarioSet, Replication,
    ExperimentEngine,        # run(), run_paired(), compare()
    ScenarioResult, ComparisonTable, RankedOption, RankBucket,
    CostModel, annualised_cost, capital_recovery_factor,
    replay,                  # exact | patched | to_event
    ExogenousTrace,
    ChangeProposal,          # the E5 artefact a scenario result can become
)
```

### 2.5 `twinflow-sync`

Purpose: component 6. Reality-to-twin calibration, divergence detection and its raising as a
finding, and the twin-to-reality write path with autonomy tiers, guardrails and audit trail (E5).

Runtime dependencies: `twinflow-kernel`, `twinflow-schemas`, `twinflow-twin`, `numpy`, `scipy`,
`pydantic`, `pynacl` (Ed25519 verification for 5.17).

This brick opens no socket. The live telemetry subscriber binds the kernel `Network` port (D-08) to
the `MqttNetwork` adapter, which lives in `twinflow-adapters` and carries `paho-mqtt` as its
own dependency. The extra is `twinflow-sync[live]`, which pulls the adapter package rather
than the broker client, and `scripts/checks/nondeterminism-gate.sh` names `twinflow-adapters` as the
one package where a socket import is legal. Stating the allowlist is what makes the no-sockets claim
checkable instead of decorative.

Public API:

```python
from twinflow.sync import (
    Calibrator, CalibrationPolicy, ParameterEstimate, CalibrationReport,
    DivergenceMonitor, DivergenceSignal, DivergenceFinding,
    ConfigWriter, Guardrail, GuardrailSet, AutonomyTier,
    ChangeRequest, ChangeDecision, Approval, AuditChain, verify_audit_chain,
)
```

### 2.6 `twinflow-optimize`

Purpose: E9 (Optuna search over twin configurations under a budget) and E12 (yard and dock
scheduling as a constrained scheduling problem). Both are search over configurations evaluated on
the twin, so they share a brick and an evaluation protocol.

Runtime dependencies: `twinflow-scenario`, `twinflow-twin`, `optuna` (4.9.0, MIT), `ortools`
(CP-SAT for E12), `numpy`. Optional extra `[surrogate]` swaps the evaluator for the E28 surrogate.

Every CP-SAT solve whose plan the twin executes runs under the deterministic settings of 5.20. The
brick refuses to hand a plan to the twin when those settings are not in force, because a plan
produced under a wall-clock deadline cannot be replayed.

Public API:

```python
from twinflow.optimize import (
    SearchSpace, SearchSpec,          # experiments/*.study.yaml -> object
    Evaluator,                        # Protocol: evaluate(config) -> ObjectiveVector
    TwinEvaluator, SurrogateEvaluator,
    run_study,                        # -> StudyResult (best, pareto_front, trials)
    StudyResult, ParetoFront,
    YardProblem, DockAssignment, AppointmentSlot,
    LabourProfileProvider, CalendarLabourProfile,   # protocol plus shipped null implementation
    solve_yard,                       # -> YardPlan
    YardPlan, plan_realisability,     # executes the plan on the twin, compares
)
```

### 2.7 `twinflow-dispatch-rl`

Purpose: E11. A Gymnasium environment over the AMR dispatch decision, a maskable PPO policy, and the
benchmark harness against the rule-based dispatchers. Separate brick because it pulls `torch`, and
`twinflow-automation` must stay installable without it.

Runtime dependencies: `twinflow-automation`, `twinflow-scenario`, `gymnasium`,
`stable-baselines3`, `sb3-contrib` (MaskablePPO), `torch`, `numpy`.

Applying D-04, the policy never calls `torch` from inside the simulation loop. It calls the kernel
`Inference` port, which binds `TorchInference` in training and benchmark mode and
`RecordedInference` in replay mode. The settings and the recorded artefact hash are in 5.19.

Public API:

```python
from twinflow.dispatch_rl import (
    AmrDispatchEnv, ObservationBuilder, ActionMask,
    RlDispatchPolicy,        # implements twinflow.automation.DispatchPolicy
    train, evaluate,
    BenchmarkHarness, BenchmarkTable,
)
```

### 2.8 `twinflow-surrogate`

Purpose: E28. Learn a fast approximation of the twin's KPI response to configuration and scenario
inputs, quantify its error, refuse to extrapolate, and hand candidates to the full sim for
confirmation.

Runtime dependencies: `twinflow-scenario`, `numpy`, `pandas`, `scikit-learn`, `lightgbm`.
Optional extras: `[nn]` adds `torch` for the MLP and sequence challengers; `[conformal]` adds
`mapie` for calibrated intervals, with a vendored split-conformal implementation as the fallback so
the core stays small to install.

Public API:

```python
from twinflow.surrogate import (
    FeatureSpec, encode_config,
    SurrogateModel,          # Protocol: fit/predict/predict_interval
    GbtSurrogate, MlpSurrogate, SequenceSurrogate,
    TrainingCorpus, build_corpus,
    ValidationReport,        # error distribution, coverage, decision agreement
    DomainEnvelope, in_domain,
    screen_and_confirm,      # surrogate screens N, sim confirms top-k
)
```

---

## 3. Domain model

Every entity below is a Pydantic v2 model with `model_config = ConfigDict(frozen=True)` where it is
a configuration object, and a mutable dataclass where it is live simulation state. Every quantity
carries its unit in the field name (`_s`, `_m`, `_kg`, `_kwh`, `_usd`, `_pct`) or is a typed
`Quantity`. Units are SI plus USD; there is no implicit unit anywhere.

Applying D-03, no field whose iteration order can reach an event, a hash, or a control decision is a
Python `set`. Where the semantic type is a set, the field is a `tuple[...]` sorted by a declared key
at load time, and the loader is the only place that sorts. The field comments below name the sort
key. `test_no_set_typed_field_in_the_domain_model` walks the Pydantic models and fails on any `set`
annotation, so the rule cannot regress by inattention.

### 3.1 Facility and topology

**`Facility`**: `facility_id: str`, `name: str`, `schema_version: str` (semver, C9), `calendar_id`,
`zones: list[Zone]`, `dock_doors: list[DockDoor]`, `scan_points: list[ScanPoint]`,
`stations: list[Station]`, `conveyors: list[Conveyor]`, `sorters: list[Sorter]`,
`storage: StorageSystem`, `automation: AutomationConfig`, `arrivals: ArrivalConfig`,
`costs: CostModel`, `metrics: MetricConfig`.

Invariants:

- `facility_id` unique; every cross-reference id (station, door, zone, scan point, slot, chute)
  resolves. A dangling reference is a load error, not a runtime error (C5).
- The flow graph implied by `Station.successors` is a DAG with exactly one source set (dock doors)
  and at least one sink (putaway or ship). Cycles are permitted only where a station declares
  `allows_rework: true`, and each such cycle must have a declared maximum revisit count.
- Total declared station capacity is finite and positive.

**`Zone`**: `zone_id`, `kind: Literal["dock","staging","conveyance","sortation","storage","charge","yard"]`,
`polygon_m: list[tuple[float,float]]`, `area_m2` (derived from the polygon at load, not declared),
`isa95_area: str`, `uns_path: str`. The polygon drives travel distance, CV frame rendering
(component 4), and the vehicle density of 5.6. `uns_path` is the enterprise/site/area prefix every
resource inside the zone publishes under, which is the seam named in 4.8.

**`Station`**: `station_id`, `name`, `zone_id`, `capacity: int >= 1`,
`priority_discipline: Literal["fifo","priority"]`, `service_time: DistributionSpec`,
`setup_time: DistributionSpec | None`, `changeover: ChangeoverSpec | None`,
`ideal_cycle_time_s: float > 0`, `failure: FailureSpec | None`, `staffing: StaffingSpec`,
`successors: list[RouteEdge]`, `ergonomic_profile_ref: str | None`, `energy: EnergySpec | None`,
`allows_rework: bool = False`, `buffer_capacity: int | None`, `uns_equipment: str`.

Invariants:

- `ideal_cycle_time_s` is the OEE denominator and must be less than or equal to the 1st percentile
  of `service_time`. Violating this makes Performance greater than 1, which the load-time validator
  rejects with a suggestion.
- `capacity` and `buffer_capacity` are separate. A full buffer blocks the upstream station; that
  blocking is recorded as a distinct state so the six-big-losses classification can attribute it.
- `priority_discipline` selects the SimPy resource class in 5.1. It is declared per station because
  a dock door and a putaway queue behave differently, and leaving it implicit made 5.1 reference a
  field that did not exist.

**`DockDoor`**: `door_id`, `zone_id`, `modes: tuple[Literal["inbound","outbound","crossdock"], ...]`
(sorted alphabetically at load, D-03), `levelers: bool`, `restraint_time_s: DistributionSpec`,
`adjacent_staging_lanes: tuple[str, ...]` (sorted), `uns_equipment: str`. Doors are shared between
inbound and outbound (component 6a3 depends on this contention existing); the twin models a door as
a `simpy.PriorityResource` with capacity 1.

**`ScanPoint`**: `scan_point_id`, `zone_id`, `door_id | None`, `station_id | None`,
`device_ref: str` (a device in the component 2 fleet config), `read_model_ref: str` (a read model in
the 2b sensor catalog), `service_time: DistributionSpec`, `occupancy: int >= 1`,
`identity_scope: Literal["pallet","case","both"]`,
`on_no_read: Literal["manual_key","recirculate","reject_lane"]`, `uns_equipment: str`.

A scan point is the RFID portal or barcode station the source names in requirement 1, and it is the
only element that produces the `SCANNED` transition of 3.2. Its read outcome comes from the 2b read
model, and from E46's read-zone geometry when that lands, so the twin never invents a read
probability of its own. `Sorter.read_dependency` resolves to a `scan_point_id`, which is how a no-read
at the portal becomes a divert failure downstream.

Invariant INV-TWIN-10: every pallet that reaches a station whose predecessor set contains a scan
point has either a `SCANNED` transition or a recorded no-read outcome. A pallet cannot arrive
identified without a read having happened.

**`RouteEdge`**: `to_station_id`, `probability: float in [0,1]` or `condition: str` (a restricted
expression over pallet attributes, parsed rather than evaluated), `transit: TransitSpec`.
Probabilities out of a station must sum to 1.0 within 1e-9 or the load fails.

### 3.2 Flow entities

**`Truck`**: `truck_id`, `carrier_id`, `scheduled_arrival_s`, `actual_arrival_s`,
`manifest: list[PalletManifestLine]`, `trailer_type`, `appointment_id | None`,
`detention_free_minutes`. Arrival time is exogenous (5.13).

**`Pallet`**: `pallet_id` (the process-mining case id), `lot_id`, `sku_id`, `qty_units`,
`cube_m3`, `weight_kg`, `source_truck_id`, `destination_slot_id | None`,
`state: PalletState`, `location: LocationRef`, `attributes: dict[str, str|float]`.

Invariants:

- INV-TWIN-06: at any sim instant a pallet has exactly one `LocationRef`. `LocationRef` is a tagged
  union of `Door`, `ScanPoint`, `Station`, `ConveyorSegment(offset_m)`, `Chute`, `Slot`, `AmrDeck`,
  `AsrsShuttle`, `Staging(lane, position)`. Transitions are atomic in sim time.
- Material conservation (INV-TWIN-01): `units_received == units_in_system + units_putaway + units_scrapped`
  at every event boundary. Scrap needs an explicit `twin.pallet.scrapped.v1` event with a reason
  code; there is no silent disposal.

**`PalletState`**: enum `EXPECTED -> ON_TRUCK -> UNLOADING -> STAGED -> SCANNED -> IN_CONVEYANCE ->
SORTED -> AWAITING_PUTAWAY -> STORED`, plus `REWORK`, `QUARANTINED`, `SCRAPPED`. The state machine is
declared as a table and transitions are validated; an illegal transition raises rather than logs.

**`Sku`**: `sku_id`, `description`, `class_abc: Literal["A","B","C"]`, `class_xyz`,
`units_per_case`, `cases_per_pallet`, `case_cube_m3`, `case_weight_kg`, `hazmat: bool`,
`temp_regime`, `velocity_picks_per_day`, `handling_flags: tuple[str, ...]` (sorted alphabetically at
load, D-03). Owned by `catalog/skus.yaml`, read by the twin and the slotting brick.

### 3.3 Resources and operators

**`ResourceState`** (per station, per machine, per AMR): a time-stamped state trace over
`{RUNNING, IDLE_NO_WORK, IDLE_BLOCKED, IDLE_STARVED, SETUP, DOWN_UNPLANNED, DOWN_PLANNED, CHARGING,
TRAVEL_LOADED, TRAVEL_EMPTY, WAITING_TRAFFIC}`. This trace is the single source for utilisation, OEE,
the six-big-losses classification, and the blocking and starving bottleneck detector. It is written
to the event log, not held only in memory, so E4 replay and E1's viewer can reconstruct it.

Invariant INV-TWIN-09: for every resource, the sum of state durations over a window equals the
window length exactly (integer arithmetic on sim-time ticks, not floats). Sim time is an integer
count of ticks; `facility.tick_ns` is a facility-level constant (default 1e6 ns, that is 1 ms
resolution). This removes float drift from every duration test.

**`Operator`**: consumed from E6 (`twinflow-workforce`). The twin holds a reference
(`operator_id`, `skills: tuple[str, ...]` sorted alphabetically at load, `station_assignment`,
`fatigue_index`) and reads `fatigue_index` to modulate service time and error rate. The twin does not
own the fatigue model; it declares the `OperatorProvider` protocol and ships a null implementation
returning constant capability so `twinflow-twin` installs and runs alone (A1).

### 3.4 Metric entities

**`WindowMetrics`**: `run_id`, `window_start_s`, `window_end_s`, `takt_s`,
`throughput_units`, `throughput_per_hour`, `flow_time_s: Distribution` (p50/p90/p95/max),
`station_cycle_time_s: dict[station_id, Distribution]`, `wip_time_weighted_mean`,
`wip_max`, `utilisation: dict[resource_id, float]`,
`oee: dict[resource_id, OeeBreakdown]`, `six_big_losses: dict[resource_id, LossBreakdown]`,
`energy_kwh`, `energy_per_pallet_kwh`, `little_law_residual_pct`.

**`OeeBreakdown`**: `availability`, `performance`, `quality`, `oee`, `planned_production_time_s`,
`run_time_s`, `ideal_cycle_time_s`, `total_count`, `good_count`,
`convention: Literal["nakajima","semi_e79"]`. Invariant INV-TWIN-08: each of A, P, Q lies in [0,1];
`oee == a*p*q` to within 1e-12; `oee <= min(a,p,q)`.

**`ResourceRef`**: `kind: Literal["station","amr","crane","conveyor","sorter","scan_point","zone"]`,
`id: str`. A ranked entry is `(ResourceRef, score)`, and `RankedResources` is an ordered tuple of
those entries.

**`BottleneckReport`**: `by_utilisation: RankedResources`, `by_active_period: RankedResources`
(Roser shifting-bottleneck), `by_blocking_starving: RankedResources`, `agreement: bool`,
`shifting_bottleneck_timeline: list[(interval, ResourceRef, sole_or_shifting)]`,
`headline_resource: ResourceRef`, `headline_rationale: str`.

The rankings are over resources rather than stations because requirement 1b names congestion as a
measurable bottleneck source, and a congested zone is not a station. A zone enters the ranking with
its aggregate `WAITING_TRAFFIC` time; an AMR enters with its own state trace; a crane, a conveyor
segment and a sorter enter the same way. Scenario SCN-E2E-15 is the case whose correct headline
answer is a zone, and it exists so the wider type is exercised rather than merely declared.

When the three detectors disagree the report says so, the headline is taken from the active-period
method, and the disagreement is raised as a low-severity finding. A shifting bottleneck is a real
operational fact, not a defect.

**`ValueStreamSummary`**: ordered `list[VssStation]` where `VssStation` carries
`station_id`, `cycle_time_s`, `changeover_time_s`, `uptime_pct`, `operators`, `wip_before_units`,
`wip_before_time_s`, `va_time_s`, `nva_time_s`, `first_pass_yield_pct`; plus totals
`total_lead_time_s`, `total_va_time_s`, `process_cycle_efficiency = va/lead`, and
`demand_units_per_day`, `takt_s`. This is the object the Phase 3c VSM renderer consumes; the twin
owns the numbers, the VSM layer owns the drawing.

### 3.5 AMR fleet

**`TravelGraph`**: a directed graph of `Node(node_id, xy_m, zone_id, kind)` and
`Edge(from, to, length_m, max_speed_mps, width_class, one_way: bool)`. Built from `facility.yaml`
aisle geometry. Node kinds: `AISLE`, `INTERSECTION`, `PICK_FACE`, `DROP`, `CHARGER`, `QUEUE`.

**`Amr`**: `amr_id`, `model_id`, `max_speed_mps`, `accel_mps2`, `decel_mps2`,
`turn_time_s`, `payload_capacity_kg`, `battery_kwh`, `soc` (state of charge, 0 to 1),
`draw_travel_kw`, `draw_idle_kw`, `draw_lift_kw`, `charge_kw`, `charge_efficiency`,
`soc_dispatch_floor`, `soc_target`, `mtbf_s`, `mttr: DistributionSpec`,
`failure_modes: tuple[FailureMode, ...]`, `state: ResourceState`, `route: list[Node]`,
`reservation_window: list[(node, t_in, t_out)]`, `uns_equipment: str`.

`failure_modes` closes the half of requirement 1b that an MTBF alone leaves open. Each `FailureMode`
carries `name`, `weight`, `mttr_override`, `telemetry_signature_ref` and `scrap_probability`, the
same shape `FailureSpec` uses in 6.1, so an AMR fault produces a sensor signature the PdM layer can
detect rather than an unexplained downtime. The shipped `catalog/amr_models.yaml` declares four
modes per model: `drive_motor_thermal`, `caster_wear`, `lidar_occlusion`, `battery_cell_imbalance`.

Invariants:

- INV-AMR-02: `soc` stays in [0, 1]; it is non-increasing while `state != CHARGING`; the energy
  ledger closes, meaning `battery_kwh * (soc_start - soc_end) + charged_kwh == sum(segment_energy_kwh)`
  to 1e-9.
- INV-AMR-01: under the reservation protocol no two AMRs hold overlapping time windows on the same
  node, and no two hold opposing windows on the same one-way edge.
- INV-AMR-04: every task is completed, cancelled or reassigned exactly once; the count of
  `task.assigned` minus `task.completed` minus `task.cancelled` minus `task.reassigned` is zero at
  end of run.

**`Task`**: `task_id`, `kind: Literal["move_pallet","replenish","return_empty","charge"]`,
`origin_node`, `dest_node`, `pallet_id | None`, `release_time_s`, `due_time_s | None`,
`priority: int`, `assigned_amr_id | None`, `state`.

**`ReservationManager`**: holds the node and edge reservation table, resolves conflicts, and
maintains the wait-for graph. INV-AMR-03: the wait-for graph is acyclic at every decision point.

### 3.6 Palletiser cell

**`PalletiserCell`**: `cell_id`, `station_id`, `mode: Literal["palletise","depalletise"]`,
`pattern: PalletPattern`, `cycle_time_s: DistributionSpec` (per case),
`layer_change_time_s`, `pallet_change_time_s`, `infeed_buffer_cases`, `outfeed_buffer_pallets`,
`jam: JamModel`, `energy: EnergySpec`, `uns_equipment: str`.

**`JamModel`**: `jam_probability_per_case`, `jam_types: tuple[JamType, ...]` where each `JamType` has
`name`, `weight`, `clear_time_s: DistributionSpec`, `requires_operator: bool`,
`scrap_probability` (a jam can damage the case), `telemetry_signature_ref` (which sensor pattern in
the 2b catalog this jam produces, so PdM has something to detect).

The numeric jam rate and clear-time distribution are not stated here. They live in
`variability-and-faults.md` section B.4 under `variability.palletiser.jam_rate_baseline` and
`variability.palletiser.jam_clear`, which is the single source of truth for every stochastic
parameter in the repository. Section 9 Q16 records that those two values carry no external published
reference and states what would settle them.

Invariant INV-PAL-01: cases on a completed pallet equal `pattern.cases_per_pallet` exactly; a jam
that occurs mid-pallet leaves a partial pallet whose case count is recorded, and clearing resumes
from that count. No cases appear or vanish across a jam.

### 3.7 ASRS

**`AsrsAisle`**: `aisle_id`, `bays: int`, `levels: int`, `bay_pitch_m`, `level_pitch_m`,
`crane: StackerCrane`, `io_point: Node`, `storage_policy: Literal["random","dedicated","class_based"]`,
`class_boundaries: list[float] | None`.

**`StackerCrane`**: `horizontal_speed_mps`, `vertical_speed_mps`, `horizontal_accel_mps2`,
`vertical_accel_mps2`, `pickup_deposit_time_s`, `dual_command_enabled: bool`,
`failure: FailureSpec`, `energy: EnergySpec`, `uns_equipment: str`.

Travel is Chebyshev: horizontal and vertical motion run at the same time, so travel time is the
larger of the two leg times. This is the standard unit-load AS/RS assumption and the assumption
behind the Bozer and White travel-time model that VAL-GATE-ASRS-01 checks against.

**`CraneScheduler`**: policies `FCFS`, `NEAREST_NEIGHBOUR`, `DUAL_COMMAND_PAIRING`,
`SHORTEST_LEG_FIRST`. Dual command pairing takes a storage request and a retrieval request and
sequences them into one cycle when both are queued.

Invariants: INV-ASRS-01, one crane occupies one aisle; a retrieval returns exactly the pallet stored
in the addressed slot. INV-ASRS-02, occupied slot count equals stored pallet count at all times.

### 3.8 Conveyor and sortation

**`ConveyorSegment`**: `segment_id`, `length_m`, `speed_mps`, `accumulating: bool`,
`capacity_units`, `min_gap_m`, `failure: FailureSpec`, `energy: EnergySpec`, `uns_equipment: str`.

**`Sorter`**: `sorter_id`, `type: Literal["shoe","tilt_tray","cross_belt","pusher"]`,
`induct_rate_units_per_min`, `divert_window_m`, `chutes: list[Chute]`,
`decision_point_offset_m`, `read_dependency: str | None` (a `scan_point_id` from 3.1),
`missort_on_no_read: Literal["recirculate","reject_lane"]`, `mechanical_missort_rate`,
`failure: FailureSpec`, `uns_equipment: str`.

`Sorter.failure` is present for the same reason `Amr.failure_modes` is: requirement 1b asks for
failure modes on every automation resource, and a missort rate is a quality defect, not a failure.
The shipped catalogue declares `induct_belt_stall`, `divert_actuator_stuck` and
`chute_full_backpressure`, each with a `telemetry_signature_ref`.

**`DivertDecision`**: computed at `decision_point_offset_m` from `pallet.destination_chute`, which in
turn comes from the slotting plan and the storage system. If the identity is unknown, which is a real
and common failure that the 2b read model and E46 produce, the item recirculates or goes to the
reject lane per config, and that outcome is a finding candidate.

Invariant INV-SORT-01: every inducted unit leaves via exactly one chute or the reject lane; a unit
cannot occupy two chutes; the count balance closes per window.

### 3.9 Storage and slotting

**`SlotGrid`**: `slots: list[Slot]` where `Slot` has `slot_id`, `aisle`, `bay`, `level`,
`xy_m`, `height_m` (floor to beam, the ergonomic driver), `cube_capacity_m3`,
`weight_capacity_kg`, `allowed_temp_regimes: tuple[str, ...]` (sorted),
`allowed_handling_flags: tuple[str, ...]` (sorted), `travel_distance_m`
(from the designated I/O point, computed on the travel graph, not Euclidean).

**`SkuProfile`**: `sku_id`, `picks_per_day`, `units_per_pick`, `cube_per_unit_m3`,
`weight_per_unit_kg`, `days_of_supply`, `replenishments_per_day`, `abc_class`,
`affinity_group_id | None`, `ergonomic_sensitivity` (derived from unit weight and pick frequency).

**`AffinityMatrix`**: sparse symmetric matrix of co-occurrence counts from order lines
(`support`, `lift`), sourced from the order stream. Until the order stream exists (Phase 3e) this is
supplied by the synthetic order-line generator described in section 9 Q4.

**`SlottingObjective`**: weighted terms plus hard constraints. Cube is a term, not only a
feasibility test, because the source lists it as one of the four optimisation dimensions.

```
slots_required(sku) = ceil( days_of_supply * picks_per_day * units_per_pick
                            * cube_per_unit_m3 / slot.cube_capacity_m3 )

mean_travel(sku)    = mean over the slots assigned to sku of travel_distance_m(slot)

minimise  w_travel  * sum_over_skus( picks_per_day * 2 * mean_travel(sku) )
        + w_replen  * sum_over_skus( replenishments_per_day * 2 * mean_travel(sku) )
        + w_affinity* sum_over_pairs( lift(i,j) * distance(slot_i, slot_j) )
        + w_ergo    * sum_over_skus( picks_per_day * ergonomic_risk(sku, slot) )
subject to  slots_required(sku) slots assigned to sku
            weight(sku) <= slot.weight_capacity_kg
            temp_regime(sku) in slot.allowed_temp_regimes
            handling_flags(sku) subset of slot.allowed_handling_flags
            hazmat segregation rules
            one slot per sku (dedicated) or n slots per sku (bounded)
```

Writing the travel term over `mean_travel` rather than over one slot is what makes cube bite. A bulky
SKU occupies more slots, its assigned slots reach further from the I/O point, and its mean travel
rises, so cube changes the ranking rather than only the feasibility. In the reference case of
VAL-GATE-SLOT-01, where every SKU takes one slot, the term reduces to `picks_per_day * 2 *
travel_distance_m` and the optimum is the cube-per-order-index ordering. That reduction is the gate,
and it is stated as a reduction rather than asserted as a coincidence.

`ergonomic_risk` is the E6 and 6a10 score. Until that brick lands, the null provider returns
`proxy_v1`, defined once, here:

```
low, high = slotting.golden_zone_m            # default [0.75, 1.40]
d = 0                       if low <= height_m <= high
    (low - height_m)        if height_m < low
    (height_m - high)       if height_m > high
proxy_v1(height_m) = (d / slotting.golden_zone_scale_m) ** 2      # default scale 0.50 m
```

The proxy is zero inside the golden zone, from knuckle height to shoulder height, and grows with the
square of the distance outside it. It is not linear, and no other section restates it. The config
records `ergonomic_provider: "proxy_v1"` so no report can claim NIOSH grounding it does not have.

Invariants: INV-SLOT-01 feasibility (every constraint above satisfied, every SKU assigned its
`slots_required` slots, no double assignment of a dedicated slot). INV-SLOT-02 velocity
monotonicity: with `w_affinity = 0`, `w_ergo = 0` and all slots homogeneous in capacity, increasing
one SKU's `picks_per_day` never moves it to a strictly farther slot in the resulting plan.
INV-SLOT-03 cube monotonicity: with the same weights, and two SKUs equal in `picks_per_day` and
unequal in `cube_per_unit_m3`, the bulkier SKU never receives the strictly nearer mean travel. Both
are real properties of the cube-per-order-index ordering and both are regression traps.

### 3.10 Scenario entities

**`ScenarioPatch`**: an ordered list of `PatchOp`, each `{op: "set"|"add"|"remove", path: JSONPointer,
value: Any}` against the facility document. RFC 6902 JSON Patch semantics, restricted to paths the
patch schema declares patchable. A patch that touches a non-patchable path, for example
`facility_id`, is rejected at parse time. `/facility/scan_points/-` is patchable, which is what makes
the headline demo of 5.13 a valid scenario rather than an aspiration.

**`Scenario`**: `scenario_id`, `label`, `patch: ScenarioPatch`, `cost: ScenarioCost`,
`exogenous_boundary: ExogenousBoundary`, `replications: int`, `horizon_s`, `warmup_policy`,
`notes`.

**`ScenarioCost`**: `capex_usd`, `install_usd`, `life_years`, `salvage_usd`,
`opex_annual_usd` (excludes labour by definition), `labour_delta_fte` (signed; negative removes
staff), `assumption_source: str` (free text, printed in the table so every dollar in the ranking
traces to a stated assumption).

Labour appears exactly once in the cost model, through `labour_delta_fte` priced at
`costs.labour_rate_usd_per_hour` times `costs.annual_hours_per_fte` times
`costs.labour_burden_multiplier`. `opex_annual_usd` carries energy, maintenance and consumables and
nothing else. The split is stated in both places because a cost model that declares a labour field
and prices labour inside opex is either carrying a dead field or double counting, and a reader
cannot tell which from the numbers alone.

**`RankedOption`**: `scenario_id`, `label`, `throughput_delta_units_per_year`,
`throughput_delta_ci95`, `annualised_cost_usd`, `annual_net_saving_usd`,
`throughput_per_dollar: float | None`, `payback_years`, `energy_delta_kwh_per_year`,
`operator_impact: OperatorImpact`, `lss_verdict: HypothesisResult`, `significant: bool`,
`bucket: RankBucket`, `pareto_dominated: bool`, `rank`, `caveats: list[str]`.

### 3.11 Yard and dock entities (E12)

**`AppointmentSlot`**: `slot_id`, `window_start_s`, `window_end_s`, `door_id | None`.

**`YardProblem`**: `trucks: list[TruckArrivalRequest]`, `doors: list[DoorCapability]`,
`labour_profile: list[LabourInterval]`, `objective_weights`, `hard_windows`,
`crossdock_links: list[CrossdockLink]` (empty until Phase 3g, see 8).

**`LabourInterval`**: `start_s`, `end_s`, `fte: float`. Supplied by a `LabourProfileProvider`. The
shipped implementation is `CalendarLabourProfile`, which reads shift patterns and headcount from
`calendars.yaml`, so E12 runs before E23 exists. When E23 lands it registers a provider that reads
`roster.v1` and the yard solver changes not at all.

**`YardPlan`**: `assignments: list[DockAssignment]`, `objective_value`, `solver_status`,
`deterministic_time_used`, `branches_used`, `predicted_makespan_s`, `predicted_detention_usd`,
`predicted_overtime_hours`.

`YardPlan` carries the solver's deterministic time consumption and its branch count. It carries no
wall-clock field, because the plan steers the simulation and anything inside it is hashed (D-02).
The wall-clock duration of the solve goes to the metrics sink named in 4.9.

### 3.12 Sync entities (component 6)

**`ParameterEstimate`**: `parameter_path` (JSON pointer into the facility document),
`estimate`, `std_error`, `n_observations`, `window`,
`estimator: Literal["mle","trimmed_mle","bayes_shrunk"]`, `changepoint_detected: bool`,
`accepted: bool`, `rejection_reason | None`.

**`DivergenceSignal`**: `signal_id`, `metric` (for example `station.unload.cycle_time_s.p50`),
`predicted`, `observed`, `standardised_residual`, `ewma`, `cusum`, `window`,
`state: Literal["in_control","warning","diverged"]`, `late_arrival_suppressed: bool`.

**`DivergenceFinding`**: the payload the LSS engine wraps into a `finding.v1` with
`finding_type = "TWIN_DIVERGENCE"`, `severity`, `evidence: {signal, window, chart_ref, run_id}`,
`suggested_next_tool` (typically `recalibrate` or `investigate_assignable_cause`).

### 3.13 Autonomy entities (E5)

**`AutonomyTier`**: `L1_ADVISE`, `L2_RECOMMEND_APPROVE`, `L3_AUTO_APPLY`.

**`Guardrail`**: `path: JSONPointer`, `min`, `max`, `max_step_pct`, `cooldown_s`,
`max_changes_per_window`, `requires_tier: AutonomyTier`,
`blast_radius: Literal["station","line","facility"]`, `rollback_trigger: MetricPredicate`.

**`ChangeRequest`**: `change_id`, `change_hash`, `proposed_by: Actor`, `tier`, `patch: ScenarioPatch`,
`evidence: {scenario_run_ids, finding_ids, hypothesis_test_id, comparison_table_id}`,
`predicted_effect`, `guardrail_evaluation`, `approvals: list[Approval]`,
`state: PROPOSED|APPROVED|REJECTED|APPLIED|REVERTED|EXPIRED`, `expires_at_s`.

**`Approval`**: `actor_id`, `public_key_id`, `signature` (Ed25519, 64 bytes, base64),
`signed_over: change_hash`, `signed_at_sim_ns`, `authority_scope`.

**`Actor`**: `kind: Literal["human","agent"]`, `id`, and for agents `model_id`, `prompt_hash`,
`tool_call_id`, `session_id`.

**`AuditChain`**: append-only, hash-chained. Each entry carries `prev_hash`, `entry_hash`,
`config_hash_before`, `config_hash_after`, `approvals`. INV-AUT-02: replaying the chain from genesis
reproduces the current running configuration exactly, and `verify_audit_chain` returns the first
broken link if not. INV-AUT-03: `verify_audit_chain` also checks every `Approval` signature against
the public key registered under `autonomy.approvers`, and rejects an entry whose signature does not
check out, whose key is not registered, or whose `authority_scope` does not cover the patched path.
This is the same hash-chain primitive E35 uses on genealogy; the implementation lives in
`twinflow-kernel` and both consume it.

---

## 4. Events

The envelope belongs to `twinflow-kernel` and this section declares payloads only (D-09). The
envelope is CloudEvents 1.0 with the twinflow extension attributes the foundations section fixes at
Phase 0: `twinflowsimts`, `twinflowrunid`, `twinflowproducerid`, `twinflowseq`,
`twinflowcausationid`, `twinflowcorrid`. Applying D-07, `twinflowseq` is dense per
`(twinflowrunid, twinflowproducerid)` and the canonical total order of the event log is
`(twinflowsimts, twinflowproducerid, twinflowseq)` ascending, with the producer id compared as a
byte string. Every reader in this section uses that triple and no other order: the replay reader of
5.13, the metric engine of 5.4, and the process-mining export.

Applying D-09, this section publishes neither run identity nor run completion. `run_started` and
`run_finished` are kernel subjects carrying `RunManifest`, the hashed core of D-01. The twin
declares what it built, not what the run is.

Subjects follow the foundations grammar: `twinflow.<domain>.<event_name>`, snake_case, with the
event name a past-tense verb phrase. Phase 0 registers the domain `twin`. This section adds six
domains to `schemas/registry.yaml`, each with an owning package, because the registry is the only
place a domain may come from.

| Domain       | Owning package         | First phase | Reason it is not a sub-name of `twin`                              |
| ------------ | ---------------------- | ----------- | ------------------------------------------------------------------ |
| `automation` | `twinflow-automation`  | P3b         | The bricks install separately, and one subject has one owner       |
| `slotting`   | `twinflow-slotting`    | P3b         | A reader who takes only the slotting brick still gets its subjects |
| `scenario`   | `twinflow-scenario`    | P2b         | Scenario subjects are consumed by the agent and the dashboard      |
| `optimize`   | `twinflow-optimize`    | P6          | E9 and E12 share a brick and a subject domain                      |
| `sync`       | `twinflow-sync`        | P3          | Calibration and divergence are component 6, not the twin           |
| `autonomy`   | `twinflow-sync`        | P6          | E5's audit trail is a separate contract from calibration           |

`twinflow-surrogate` publishes under `optimize`, because a surrogate prediction is an evaluation
result and splitting it from `optimize.trial_completed` would make the two impossible to join.

Schemas live at `/schemas/<domain>/<event_name>.v<major>.json` as JSON Schema 2020-12, are
generated from the Pydantic models, and evolve additively within a major version (C3). The
generation step runs in CI, so a model change that is not reflected in the schema fails the build
rather than drifting.

### 4.1 Published by `twinflow-twin`

| Subject                               | Version | Key payload fields                                                                                  | Purpose                                                            |
| ------------------------------------- | ------- | --------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------ |
| `twinflow.twin.model_built`           | v1      | `facility_hash`, `station_count`, `resource_count`, `stream_names`, `tick_hz`, `ergonomic_provider` | What the twin built from the config, for a reader diffing two runs |
| `twinflow.twin.truck_arrived`         | v1      | `truck_id`, `carrier_id`, `scheduled_arrival_s`, `readiness_s`, `manifest_lines`, `appointment_id`  | Exogenous, and 5.13 replays it verbatim                            |
| `twinflow.twin.truck_departed`        | v1      | `truck_id`, `dwell_s`, `detention_minutes`, `door_id`                                               | Yard KPI and E12's realised objective                              |
| `twinflow.twin.door_assigned`         | v1      | `truck_id`, `door_id`, `wait_s`, `assigner: "policy" or "yard_plan"`, `plan_id`                     | E12 execution trace                                                |
| `twinflow.twin.pallet_created`        | v1      | `pallet_id`, `lot_id`, `sku_id`, `qty_units`, `cube_m3`, `weight_kg`, `source_truck_id`             | Case creation for process mining                                   |
| `twinflow.twin.pallet_scanned`        | v1      | `pallet_id`, `scan_point_id`, `outcome`, `reads`, `identity_source`, `dwell_s`                      | The `SCANNED` transition of 3.2, and INV-TWIN-10's evidence        |
| `twinflow.twin.activity_started`      | v1      | `case_id`, `activity`, `resource_id`, `station_id`, `operator_id`, `attrs`                          | XES `lifecycle:transition = start`                                 |
| `twinflow.twin.activity_completed`    | v1      | `case_id`, `activity`, `resource_id`, `duration_s`, `outcome`, `attrs`                              | XES `complete`, and the process-mining spine                       |
| `twinflow.twin.activity_aborted`      | v1      | `case_id`, `activity`, `reason_code`                                                                | Rework and exception paths                                         |
| `twinflow.twin.pallet_moved`          | v1      | `pallet_id`, `from: LocationRef`, `to: LocationRef`, `distance_m`, `mover_id`                       | Travel accounting                                                  |
| `twinflow.twin.pallet_scrapped`       | v1      | `pallet_id`, `reason_code`, `qty_units`                                                             | Conservation ledger, INV-TWIN-01                                   |
| `twinflow.twin.resource_state`        | v1      | `resource_id`, `state`, `previous_state`, `duration_s`, `loss_class`                                | Utilisation, OEE, six big losses                                   |
| `twinflow.twin.resource_failed`       | v1      | `resource_id`, `failure_mode`, `telemetry_signature_ref`, `expected_ttr_s`                          | Feeds PdM and the CMMS queue (6b)                                  |
| `twinflow.twin.resource_repaired`     | v1      | `resource_id`, `failure_mode`, `ttr_s`, `parts_used`                                                | Closes the failure record                                          |
| `twinflow.twin.wip_sampled`           | v1      | `zone_id`, `station_id`, `units`, `queue_units`                                                     | Time-weighted WIP, sampled at config cadence and at every change   |
| `twinflow.twin.window_measured`       | v1      | full `WindowMetrics`                                                                                | The dashboard and the LSS engine consume this                      |
| `twinflow.twin.bottleneck_identified` | v1      | full `BottleneckReport`                                                                             | The agent tool `get_bottleneck` reads this                         |
| `twinflow.twin.vss_generated`         | v1      | full `ValueStreamSummary`                                                                           | Phase 3c VSM renderer input                                        |

`twinflow.twin.model_built` carries `facility_hash` and not `code_version`. Package versions live in
`RunProvenance` in `manifest.json` (D-01), so a release that changes no behaviour does not invalidate
a golden hash. A version string inside a hashed payload makes every release a golden-file rewrite,
which is the outcome 5.2's stream discipline exists to avoid.

### 4.2 Published by `twinflow-automation`

| Subject                                     | Version | Key payload fields                                                                                     |
| ------------------------------------------- | ------- | ------------------------------------------------------------------------------------------------------ |
| `twinflow.automation.amr_task_created`      | v1      | `task_id`, `kind`, `origin_node`, `dest_node`, `due_time_s`, `priority`                                |
| `twinflow.automation.amr_task_assigned`     | v1      | `task_id`, `amr_id`, `policy_id`, `candidates_considered`, `inference_steps`, `reason_code`            |
| `twinflow.automation.amr_task_completed`    | v1      | `task_id`, `amr_id`, `travel_empty_m`, `travel_loaded_m`, `wait_traffic_s`, `energy_kwh`, `lateness_s` |
| `twinflow.automation.amr_state_changed`     | v1      | `amr_id`, `state`, `previous_state`, `soc`, `node_id`, `speed_mps`                                     |
| `twinflow.automation.amr_charge_started`    | v1      | `amr_id`, `charger_id`, `soc_start`, `queue_wait_s`                                                    |
| `twinflow.automation.amr_charge_completed`  | v1      | `amr_id`, `charger_id`, `soc_end`, `energy_kwh`, `charge_phase_split_s`                                |
| `twinflow.automation.amr_conflict_resolved` | v1      | `amr_ids`, `node_id`, `resolution: "yield" or "reroute" or "replan"`, `delay_s`                        |
| `twinflow.automation.amr_deadlock_detected` | v1      | `cycle: list[amr_id]`, `nodes`, `resolution`, `recovery_s`                                             |
| `twinflow.automation.congestion_sampled`    | v1      | `zone_id`, `vehicles_present`, `density_per_m`, `mean_speed_mps`, `speed_ratio`, `queue_length`        |
| `twinflow.automation.palletiser_cycled`     | v1      | `cell_id`, `pallet_id`, `cases`, `cycle_time_s`, `layer_changes`, `energy_kwh`                         |
| `twinflow.automation.palletiser_jammed`     | v1      | `cell_id`, `jam_type`, `cases_on_pallet_at_jam`, `clear_time_s`, `operator_required`, `cases_scrapped` |
| `twinflow.automation.asrs_command_queued`   | v1      | `aisle_id`, `command_type: "SC_store" or "SC_retrieve" or "DC"`, `slot_ids`, `queued_at_s`             |
| `twinflow.automation.asrs_cycle_completed`  | v1      | `aisle_id`, `command_type`, `travel_time_s`, `pickup_deposit_time_s`, `total_time_s`, `energy_kwh`     |
| `twinflow.automation.sorter_inducted`       | v1      | `unit_id`, `sorter_id`, `scan_point_id`, `identity_source: "rfid" or "barcode" or "unknown"`           |
| `twinflow.automation.sorter_diverted`       | v1      | `unit_id`, `chute_id`, `intended_chute_id`, `missort: bool`, `missort_cause`                           |
| `twinflow.automation.sorter_recirculated`   | v1      | `unit_id`, `pass_number`, `cause`                                                                      |

`amr_task_assigned` carries `candidates_considered` and `inference_steps`, both of which are
deterministic counts computed from the decision itself. It carries no wall-clock duration, because
applying D-02 a wall-clock reading never enters an event payload. Section 4.9 states where the
compute cost of a dispatch decision does go, and 5.19 states how the benchmark table joins the two.

`congestion_sampled` carries `density_per_m` alongside `vehicles_present`, because the congestion
relation of 5.6 is stated over density and a reader who wants to refit it needs the independent
variable rather than a count.

### 4.3 Published by `twinflow-slotting`

| Subject                              | Version | Key payload fields                                                                                                                                                   |
| ------------------------------------ | ------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `twinflow.slotting.plan_proposed`    | v1      | `plan_id`, `solver_used`, `objective_value`, `terms_breakdown`, `moves`, `predicted_travel_delta_m_per_day`, `predicted_picks_per_hour_delta`, `constraints_binding` |
| `twinflow.slotting.plan_evaluated`   | v1      | `plan_id`, `measured_travel_delta_m_per_day`, `measured_picks_per_hour_delta`, `ci95_low`, `ci95_high`, `measurement_run_ids`                                        |
| `twinflow.slotting.move_planned`     | v1      | `plan_id`, `sku_id`, `from_slot`, `to_slot`, `units`, `labour_minutes`, `equipment`                                                                                  |
| `twinflow.slotting.payback_computed` | v1      | `plan_id`, `move_labour_hours`, `move_cost_usd`, `savings_usd_per_year`, `payback_days`, `assumptions`                                                               |

`solver_used` is in the payload because 5.10 offers three solvers and a plan whose provenance is
hidden cannot be argued with.

### 4.4 Published by `twinflow-scenario`

| Subject                                | Version | Key payload fields                                                                                                        |
| -------------------------------------- | ------- | ------------------------------------------------------------------------------------------------------------------------- |
| `twinflow.scenario.run_started`        | v1      | `scenario_id`, `replication_index`, `patch_hash`, `base_kind: "facility" or "run_id" or "snapshot"`, `exogenous_boundary` |
| `twinflow.scenario.run_completed`      | v1      | `scenario_id`, `replication_index`, `kpis`, `child_run_id`, `crn_integrity`                                               |
| `twinflow.scenario.compare_completed`  | v1      | `comparison_id`, `baseline_scenario_id`, `ranked: list[RankedOption]`, `method`, `replications`, `alpha`, `test_chosen`   |
| `twinflow.scenario.replay_started`     | v1      | `source_run_id`, `mode: "exact" or "to_event" or "patched"`, `patch_hash`, `exogenous_boundary`                           |
| `twinflow.scenario.replay_completed`   | v1      | `source_run_id`, `mode`, `divergence_point_sim_ts`, `hash_match: bool`, `synthesised_devices`                             |

`crn_integrity` is the per-stream draw-count record the variability section defines. It rides on
the scenario event rather than being recomputed downstream, because the LSS engine's assumption
checker picks the paired or the unpaired test from it and needs to state which and why.

### 4.5 Published by `twinflow-optimize`, `twinflow-dispatch-rl`, and `twinflow-surrogate`

| Subject                                     | Version | Key payload fields                                                                                                                       |
| ------------------------------------------- | ------- | ---------------------------------------------------------------------------------------------------------------------------------------- |
| `twinflow.optimize.trial_completed`         | v1      | `study_id`, `trial_number`, `params`, `objectives`, `constraints`, `pruned: bool`, `evaluator: "twin" or "surrogate"`                    |
| `twinflow.optimize.study_completed`         | v1      | `study_id`, `best_trials`, `pareto_front`, `sampler`, `stream_name`, `budget_usd`, `execution: "sequential" or "replayed"`               |
| `twinflow.optimize.yard_plan_generated`     | v1      | full `YardPlan`                                                                                                                          |
| `twinflow.optimize.yard_plan_checked`       | v1      | `plan_id`, `predicted_makespan_s`, `simulated_makespan_s`, `gap_pct`, `requantiled: bool`, `duration_quantile_used`                      |
| `twinflow.optimize.dispatch_benchmarked`    | v1      | `policies`, `seed_set_id`, `metrics_per_policy`, `paired_test`, `effect_size`, `holm_adjusted`, `winner`, `published_table_uri`          |
| `twinflow.optimize.surrogate_validated`     | v1      | `model_id`, `n_holdout`, `error_quantiles`, `interval_coverage`, `top_k_agreement`, `kendall_tau`, `in_domain_rate`, `baseline_model_id` |
| `twinflow.optimize.surrogate_predicted`     | v1      | `model_id`, `encoder_version`, `config_hash`, `predicted`, `interval`, `in_domain: bool`, `confirmed_by_run_id`                          |

### 4.6 Published by `twinflow-sync`

| Subject                                | Version | Key payload fields                                                                                                        |
| -------------------------------------- | ------- | ------------------------------------------------------------------------------------------------------------------------- |
| `twinflow.sync.calibration_completed`  | v1      | `estimates: list[ParameterEstimate]`, `accepted_count`, `rejected_count`, `config_version_before`, `config_version_after` |
| `twinflow.sync.divergence_observed`    | v1      | full `DivergenceSignal`, plus `late_arrival_suppressed` and `suppression_window_s`                                        |
| `twinflow.autonomy.change_proposed`    | v1      | `ChangeRequest` without approvals, plus `Actor`                                                                           |
| `twinflow.autonomy.change_approved`    | v1      | `change_id`, `approvals: list[Approval]`, `audit_entry_hash`                                                              |
| `twinflow.autonomy.change_rejected`    | v1      | `change_id`, `guardrail_failed`, `evaluated_values`, `audit_entry_hash`                                                   |
| `twinflow.autonomy.change_applied`     | v1      | `change_id`, `patch`, `config_hash_before`, `config_hash_after`, `audit_entry_hash`                                       |
| `twinflow.autonomy.change_reverted`    | v1      | `change_id`, `rollback_trigger_fired`, `restored_config_version`, `audit_entry_hash`                                      |

Every autonomy subject carries `audit_entry_hash`, which is the link into the `AuditChain` of 3.13.
A reader who has the event log alone can walk the chain without the sidecar, and
`verify_audit_chain` compares the two.

### 4.7 Consumed

| Subject                                | Owner             | Used for                                                                | Behaviour when absent                                     |
| -------------------------------------- | ----------------- | ----------------------------------------------------------------------- | --------------------------------------------------------- |
| `twinflow.telemetry.sensor_reading`    | component 2       | Calibration, divergence, congestion cross-check                         | Calibration and divergence do not run, and say so         |
| `twinflow.lss.finding`                 | component 5 (LSS) | Scenario verdicts, autonomy evidence, alarm rationalisation routing     | `lss_verdict` is null and the caveat names the reason     |
| `twinflow.lss.hypothesis_result`       | component 5       | `RankedOption.lss_verdict` and `significant`                            | Ranking falls back to the effect-size order with a caveat |
| `twinflow.forecast.horizon_issued`     | 6a                | Yard scheduling demand input, slotting velocity refresh                 | `arrivals.mode: forecast_driven` is a config error        |
| `twinflow.order.line_released`         | 6a3 and 6a6       | Affinity matrix, pick velocity                                          | The synthetic order-line generator of 9 Q4 supplies it    |
| `twinflow.workforce.roster_published`  | E23               | Labour profile for E12                                                  | `CalendarLabourProfile` supplies it from `calendars.yaml` |
| `twinflow.workforce.ergonomics_scored` | 6a10              | Slotting `ergonomic_risk`, operator impact in what-ifs                  | `proxy_v1` of 3.9, stamped on every report                |
| `twinflow.energy.window_measured`      | E7                | Energy deltas in `RankedOption`                                         | `energy_delta_kwh_per_year` is null with a stated reason  |
| `twinflow.fleet.device_health`         | component 3       | Failure injection realism, PdM-driven scenarios                         | Faults come from the fault schedule only                  |

Two of the domains above, `workforce` and `energy`, are not in the Phase 0 domain list. Their
owning sections register them, and their rows in `schemas/registry.yaml` carry `status: reserved`
with an empty producer list until those sections land. A consumer of a reserved subject takes the
fallback in the last column, which is why that column exists.

Every row's absent-behaviour column is asserted by a test. Section 7.1 names
`test_missing_consumed_subject_degrades_as_declared`, which loads each brick with the producing
package uninstalled and asserts the declared fallback rather than an exception.

### 4.8 The UNS publication seam

Requirement 1b asks for automation resources to be first-class simulated resources with telemetry
into the UNS. The subjects of 4.2 are internal package events on the `EventBus`, not UNS telemetry,
so the seam between a 1b resource and its UNS topic must be named or the requirement is only half
covered.

Every automation entity in section 3 carries `uns_equipment`, a slug naming the equipment level of
the ISA-95 path. Every `Zone` carries `uns_path`, the enterprise, site, and area prefix. The full
topic for a resource is the concatenation:

```
<zone.uns_path>/<line>/<resource.uns_equipment>/<parameter>
```

The twin does not publish to that topic. Component 2 does, and the binding is declared data rather
than code: `catalog/devices.yaml` carries an `attaches_to` field naming a twin resource id, and the
device publishes its readings under the resource's topic. The twin's obligation is to make the
attachment resolvable and to expose the physical quantity the device reads.

| Automation resource | Parameters a device may attach to                                     | Consuming layer                     |
| ------------------- | --------------------------------------------------------------------- | ----------------------------------- |
| `Amr`               | `soc`, `speed_mps`, `motor_current_a`, `drive_temp_c`, `vibration_g`  | PdM trending, energy KPIs (E7)      |
| `PalletiserCell`    | `cycle_time_s`, `motor_torque_nm`, `motor_current_a`, `jam_state`     | PdM, jam-signature detection        |
| `StackerCrane`      | `position_m`, `motor_current_a`, `drive_temp_c`, `cycle_count`        | PdM, ASRS availability              |
| `ConveyorSegment`   | `belt_speed_mps`, `motor_current_a`, `bearing_temp_c`, `vibration_g`  | PdM, the six-big-losses attribution |
| `Sorter`            | `induct_rate_units_per_min`, `divert_actuations`, `chute_full_state`  | Missort findings, CV cross-check    |
| `ScanPoint`         | `reads_per_pass`, `read_rate_pct`, `rssi_dbm`                         | Read-rate charts, E46               |

Two invariants make the seam checkable. INV-TWIN-11: every `uns_equipment` slug in the facility
document is unique within its zone, and the concatenated topic is unique across the facility.
INV-TWIN-12: every device in the fleet config whose `attaches_to` names a twin resource resolves to
an existing resource and to a parameter in the row above, and a dangling attachment is a load error
in the fleet config rather than a silent no-op.

### 4.9 What never enters an event payload

Applying D-02, a wall clock may be read only by the provenance sidecar writer, the paced-clock
pacer, the observability exporter, and operator-facing log lines. None of those values reaches an
event payload, the hashed log, or a control decision. Three quantities that a naive design puts in
the tape are named here so the rule has teeth.

| Quantity                       | Where it goes instead                                                               | Deterministic substitute in the tape          |
| ------------------------------ | ----------------------------------------------------------------------------------- | --------------------------------------------- |
| Run wall duration              | `RunProvenance.started_wall_utc` and `finished_wall_utc`                            | `twinflowsimts` of the last event             |
| Dispatch decision wall latency | `MetricsSink` series `dispatch.decision.latency`, keyed by `run_id` and `policy_id` | `candidates_considered`, `inference_steps`    |
| Solver wall duration           | `MetricsSink` series `yard.solve.wall`, keyed by `run_id` and `plan_id`             | `deterministic_time_used`, `branches_used`    |

The metrics series are joined to a run by `run_id` when a benchmark table is rendered, so compute
cost stays visible next to benefit without steering the simulation. Section 7.1 names
`test_no_wall_clock_field_in_any_declared_payload`, which walks every schema this section owns and
fails on a property whose name matches the wall-clock naming convention (`wall_`, `_wall`,
`_latency_ns`, `_time_s` on a solver or policy object) outside the three sinks above. A new event
that reintroduces the defect fails at authoring time.

---

## 5. Behaviour

### 5.1 The model in one paragraph

`TwinModel` builds a SimPy environment whose `env.now` is an integer tick counter supplied by the
kernel `Clock`. Trucks are generated by an arrival process, claim a `DockDoor` (a
`simpy.PriorityResource` of capacity 1), and are unloaded into pallets, which then flow as SimPy
processes through the stations declared in `facility.yaml`. Each station is a `simpy.Resource`, or a
`simpy.PriorityResource` where `Station.priority_discipline` says `priority`, with an optional
buffer modelled as a `simpy.Store` of bounded capacity. Every state change of every resource and
every pallet is appended to the `EventTape`. The metric engine never reads model internals: it reads
the tape. That separation is what lets E4 replay, E1's browser viewer, and process mining consume
exactly the same bytes the live dashboard does.

SimPy is version 4.1.2 under the MIT licence, the version and licence the repository's dependency
ledger records from the package index.

### 5.2 Determinism, clock, and tie-breaking (C1, C2)

This subsection is the one every other subsection depends on, so it states mechanisms rather than
intentions.

**Streams.** Randomness comes from the `twinflow-rng` registry through the kernel `Rng` port. A
stream is addressed by a dotted name, not by a position, and its seed is derived from the name by
the content-addressed derivation that `docs/design/variability-and-faults.md` section A.1 fixes byte
for byte. No component in this section constructs a generator. The streams this section owns are
declared in the registry and listed here so a reader can find every source of randomness in one
place.

| Stream name                                    | Drawn by | Quantity                                     |
| ---------------------------------------------- | -------- | -------------------------------------------- |
| `twin.receiving.unload_duration`               | 5.1      | Unload service time per pallet               |
| `twin.station.{station_id}.service`            | 5.1      | Station service time                         |
| `twin.station.{station_id}.failure`            | 5.1      | Time to failure and time to repair           |
| `twin.routing.{station_id}.successor`          | 5.1      | Probabilistic routing choice                 |
| `twin.autoid.{scan_point_id}.read`             | 5.9      | Read outcome at a scan point                 |
| `twin.amr.{amr_id}.task_travel`                | 5.6      | Travel-time multiplier                       |
| `twin.amr.{amr_id}.transfer_dwell`             | 5.6      | Pick and drop dwell                          |
| `twin.amr.{amr_id}.charge_efficiency`          | 5.6      | Charge efficiency multiplier                 |
| `twin.amr.{amr_id}.failure`                    | 5.6      | Failure mode selection and repair duration   |
| `twin.palletiser.{cell_id}.cycle`              | 5.7      | Per-case cycle time                          |
| `twin.palletiser.{cell_id}.jam`                | 5.7      | Jam occurrence, type, and clear duration     |
| `twin.asrs.{aisle_id}.cycle_multiplier`        | 5.8      | Crane control jitter                         |
| `twin.asrs.{aisle_id}.exception`               | 5.8      | Pick-face exception                          |
| `twin.conveyor.{segment_id}.speed_multiplier`  | 5.9      | Realised belt speed                          |
| `twin.sortation.{sorter_id}.divert`            | 5.9      | Divert success and recirculation count       |
| `twin.slotting.anneal`                         | 5.10     | Simulated-annealing proposals and acceptance |
| `twin.optimize.sampler`                        | 5.18     | The Optuna sampler's own randomness          |
| `twin.yard.cpsat`                              | 5.20     | The CP-SAT solver seed of 5.20               |
| `twin.optimize.explore`                        | 5.21     | The surrogate exploration quota of 5.21      |

Four of them are easy to miss because the drawing component does not look stochastic. The annealer
in 5.10, the Optuna sampler in 5.18, the CP-SAT solver in 5.20, and the exploration quota in 5.21
all draw, and a draw with no declared stream is an unnamed source of randomness, which C1 forbids. `test_every_draw_site_has_a_registered_stream` walks the sampler call sites in
these eight packages and fails on a generator that the registry does not declare.

**Integer time.** Sim time is an integer count of ticks and every duration is an integer.
`facility.tick_ns` is a facility-level constant, default 1e6 nanoseconds, which is 1 millisecond
resolution. Distributions sample floats and round once, at the point of scheduling, under
`round_half_even`. Rounding at the scheduling point and nowhere else is what makes INV-TWIN-09's
exact state-trace closure hold in integer arithmetic.

**Iteration order.** Applying D-03, no collection whose iteration order can reach an event, a hash,
or a control decision is a Python `set`. Section 3 lists the fields that would otherwise be sets and
states the sort key for each. Dict iteration is insertion-ordered in the supported Python versions
and is permitted, but a dict built from a set or from concurrent inserts is sorted before use. CI
runs the determinism scenario twice with different `PYTHONHASHSEED` values and compares hashes,
which is the variable that changes string hashing. A separate job varies the process start
time, which catches wall-clock leakage and nothing else. Both jobs exist because they catch
different defects.

**Simultaneous events.** SimPy's scheduler keys its heap on `(time, priority, eid)` where `eid` is
an insertion counter, and it knows nothing about producers. The tie-break this section relies on is
imposed rather than inherited. `twinflow-kernel` ships `DeterministicEnv`, a
`simpy.Environment` subclass whose `schedule` method pushes
`(time, priority_class, producer_id, seq)` as the heap key, where `priority_class` is a small
integer declared per producer in `facility.yaml` under `scheduling.priority_classes` and
`producer_id` is the process-role slug of D-07. `TwinModel` accepts no other environment class, and
its constructor raises when handed a bare `simpy.Environment`.
`test_simultaneous_events_order_canonically` schedules 200 events at one tick from four producers in
a shuffled insertion order across 50 shuffles and asserts one canonical tape order every time. This
is the mechanism the whole C1 claim rests on, so it is specified and tested rather than asserted.

**The hash.** `TwinRun.state_hash` is a BLAKE3 hash over the canonical form of the tape. The
canonical form is an explicit allowlist, not a subtraction: for each subject, the schema declares
which properties are hashed, and a property is hashed only if the registry marks it so. Defining the
allowlist positively is what makes 4.9's rule enforceable, because a new field defaults to unhashed
and must be argued into the hash rather than accidentally landing there.

**Two tiers of determinism.** Applying D-05, the claim is stated at two strengths and never at one.

| Tier             | Guarantee                                                                 | Gate                                                                                      |
| ---------------- | ------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------- |
| Byte-identical   | Same seed, same config, same platform, same pinned dependency set         | `state_hash` equality, VAL-GATE-DET-01                                                    |
| Value-equivalent | Same seed and same config across the platforms of the C10 matrix          | Business events identical, continuous fields within a measured tolerance, VAL-GATE-DET-02 |

The reason the stronger claim does not hold across platforms is specific and worth stating.
Lognormal and gamma sampling go through `log`, `exp`, and `erfinv`, whose numpy implementations are
SIMD-dispatched and can differ in the last bits across CPU microarchitectures and library builds. A
one-unit-in-the-last-place difference near a `round_half_even` boundary flips one scheduled tick,
and one flipped tick changes the tape. VAL-GATE-DET-02 reports the observed maximum divergence
rather than asserting a number chosen in advance, and names whether an excess is a wrong tolerance
or a real defect. `RunProvenance.platform` records the platform and the value of
`NPY_DISABLE_CPU_FEATURES` used, which is what makes the byte-identical tier's qualifier checkable.

**Solvers and learned models.** Applying D-04, no component whose output steers the simulation is
bounded by wall time. CP-SAT runs under the deterministic settings of 5.20. Learned inference runs
through the kernel `Inference` port under the settings of 5.19. Optuna's sampler is seeded from a
declared stream and its sequential-execution rule is in 5.18. Where determinism cannot be reached,
the component does not steer the simulation: it becomes an advisory output recorded in the sidecar,
and the tape records the decision it produced rather than recomputing it on replay.

**Modes.** Simulation mode uses the virtual clock and runs as fast as the machine permits.
Production mode uses the paced clock with a configurable speed and the dashboard speed control (C2).
The same `TwinModel` code runs in both, and the only difference is which `Clock` implementation
`RuntimeBuilder` binds. Pacing changes when an event is appended in wall time and never which event
is appended or in what order, which the kernel gate `test_pacing_does_not_change_the_tape` asserts
(D-02).

### 5.3 Production mode versus simulation mode

In production mode the twin runs as a container in the DMZ segment, subscribes to normalised
telemetry through the kernel `Network` port, and maintains a live model instance. What-if instances
never run in the live process. `ExperimentEngine` forks them into a worker pool, a
`concurrent.futures.ProcessPoolExecutor` at garage and growth tiers and a job queue at enterprise
tier, each worker holding its own virtual clock. A forked instance is initialised either from
`facility.yaml` at t0, which is a cold what-if, or from a `TwinSnapshot` taken from the live model,
which is a warm what-if. Warm what-ifs are how the agent answers what to do for the rest of a shift.

Applying D-12, `simulation.mode` selects the port family and `deployment.adapters` selects within
the production family. A `deployment.adapters` key set while the mode is simulation is a config
validation error, not a silent no-op, because a test that compares two runtimes the binding rules
make identical asserts a tautology.

### 5.4 Metric computation

All metrics are computed by SQL over the tape in DuckDB, from views defined once in
`packages/twinflow-twin/sql/`. DuckDB is version 1.5.5 under the MIT licence. This matters for
E26(b): the governed SQL expression the metric engine uses is the one the agent's semantic layer
references, so the agent cannot compute utilisation differently from the dashboard.

Definitions, stated so an implementer has no room to guess:

- `takt_s = available_time_s / customer_demand_units`, where `available_time_s` is scheduled shift
  time minus planned breaks minus planned changeover, taken from the shift calendar, and
  `customer_demand_units` is the demand for the same window. The demand comes from the ERP stub
  when one is present and from `metrics.demand_units_per_day` when running standalone. There is one
  key and one name for it, declared in 6.1.
- `station_cycle_time_s` is reported two ways because practitioners mean two different things:
  `processing_time_s`, the busy time per unit at the station, and `departure_interval_s`, the
  inter-departure time from the station, which is what a stopwatch on the line measures. Both are in
  `WindowMetrics` and the value-stream summary uses `departure_interval_s`.
- `flow_time_s` is per pallet, from `twinflow.twin.truck_arrived` for its truck to the pallet's
  `STORED` transition. It is reported as a distribution, never as a bare mean.
- `wip_time_weighted_mean = (1/T) * integral over the window of units_in_system(t) dt`, computed
  exactly from the step function implied by `twinflow.twin.wip_sampled` plus every arrival and
  departure event, not by periodic polling.
- `utilisation_r = run_time_r / planned_production_time_r`, taken from the resource state trace.
- OEE per `OeeBreakdown` in 3.4, with `convention` explicit. Both conventions are built and 9 Q1
  records the ambiguity.
- The six-big-losses mapping is: `DOWN_UNPLANNED` to breakdown; `SETUP` to setup and adjustment;
  `IDLE_BLOCKED` and `IDLE_STARVED` spells shorter than `metrics.minor_stop_threshold_s` to idling
  and minor stops; measured cycle time above ideal to reduced speed; first-pass scrap within
  `metrics.startup_window_s` of a transition into `RUNNING` to startup rejects, and outside that
  window to production rejects.
- `little_law_residual_pct = 100 * abs(L - lambda*W) / L` over the steady-state portion of the
  window. It is appended to every `twinflow.twin.window_measured` and the LSS engine control-charts
  it. A drifting residual means the warm-up cut is wrong or the system is not in steady state, and
  saying so is more useful than reporting a wrong average in silence.

The residual is reported alongside `L`, `lambda`, and `W`, and it is suppressed with a stated reason
when `L` falls below `metrics.little_law_min_l` (default 1.0). Dividing by a value that approaches
zero in a lightly loaded window produces a large residual from a correct simulation, and a
self-check that fires on correct behaviour trains a reader to ignore it.

Warm-up and confidence intervals: the metric engine builds Welch's graphical procedure to pick the
truncation point, configured as `metrics.warmup: {policy: "welch", window: int, replications: int}`
or `{policy: "fixed", seconds: int}`, and reports steady-state means with batch-means confidence
intervals. The batch size is chosen so the lag-1 autocorrelation of batch means falls below
`metrics.batch_autocorr_threshold`, default 0.1. Every reported mean carries `n`, `ci95_low`,
`ci95_high`, and `method`.

### 5.5 Bottleneck identification

Three detectors run on every window, and the report publishes all three.

| Detector              | Rule                                                                                                                   | What it catches that the others miss                            |
| --------------------- | ---------------------------------------------------------------------------------------------------------------------- | --------------------------------------------------------------- |
| Utilisation           | Rank resources by `busy_time / available_time`                                                                         | Nothing the others miss; it is what most readers expect         |
| Active period         | Rank by the length of the uninterrupted active period covering each instant, per Roser, Nakano, and Tanaka             | Bottlenecks that utilisation hides behind blocking and starving |
| Blocking and starving | Rank by `blocked_downstream_time + starved_upstream_time`, attributed to the neighbour that caused it                  | Points at the constraint rather than at its victim              |

The active-period method comes from Roser, C., Nakano, M., and Tanaka, M., "A practical bottleneck
detection method", Proceeding of the 2001 Winter Simulation Conference, volume 2, pages 949 to 953,
DOI 10.1109/wsc.2001.977398, extended to the shifting case in the same authors' "Shifting bottleneck
detection", Proceedings of the Winter Simulation Conference, volume 2, pages 1079 to 1086, DOI
10.1109/wsc.2002.1166360. At any instant the momentary bottleneck is the resource with the longest
active period covering that instant. A sole bottleneck is one whose active period strictly contains
the others; a shifting bottleneck is a handover where active periods overlap.

The rankings are over resources rather than stations. Requirement 1b names congestion as a
measurable bottleneck source, and a congested zone is not a station, so a report typed to stations
could not hold the answer. `RankedResources` is an ordered tuple of `(ResourceRef, score)` and
`ResourceRef` tags the kind, so a zone enters the ranking with its aggregate `WAITING_TRAFFIC` time,
an AMR with its own state trace, and a crane, a conveyor segment, a sorter, or a scan point the same
way.

When the three detectors disagree the report sets `agreement: false`, takes the headline from the
active-period method, and raises a `twinflow.lss.finding` of type `BOTTLENECK_DISAGREEMENT` at
severity `info` with the three rankings as evidence. A shifting bottleneck is an operational fact,
not a defect.

### 5.6 AMR fleet behaviour

**Task allocation.** A `TaskPool` holds released tasks. On every dispatch trigger, which is a task
release, an AMR becoming free, or the timer at `automation.amr_fleet.dispatch.tick_s`, the
configured `DispatchPolicy` is called as `assign(tasks, fleet, state) -> list[Assignment]` and
returns assignments. That signature appears in the protocol table of 1.3, in the export list of 2.2,
and here, and the three agree because `test_protocol_surface_matches_declaration` compares the
runtime signature against `/schemas/protocols/twinflow-protocols.v1.yaml`.

Four policies ship. `NearestVehicleFirst` assigns each task to the idle AMR with the shortest graph
distance to origin. `EarliestDueDate` orders tasks by `due_time_s` and then takes the nearest
vehicle. `ContractNetAuction` has each AMR bid `estimated_completion_time + energy_penalty` with the
lowest bid winning, and the bids are computed from the same `StateView` the learned policy gets.
`RandomDispatch` is the deliberately bad baseline, present so the benchmark table has a floor; it
draws from `twin.amr.{amr_id}.task_travel` only through the model, never from an undeclared stream.

Assignments carry `candidates_considered` and `inference_steps`, both deterministic. The wall-clock
cost of a decision goes to the `MetricsSink` under 4.9 and joins the benchmark table by `run_id`.

**Traffic.** Routing is time-expanded A star on the travel graph with reservations. Each AMR
requests node and edge reservation windows along its route. Conflicts resolve by `task.priority`,
then by the lower `amr_id` compared as a byte string, which is a deterministic tie-break and not an
object-identity comparison. A vehicle that cannot reserve waits at its last safe node in
`WAITING_TRAFFIC` and replans after `automation.traffic.replan_delay_s`.

**Congestion.** Speed on an edge falls with the density of vehicles in the same zone:

```
density_per_m = (vehicles_in_zone - 1) / zone.travel_length_m
speed         = max_speed * max(min_speed_ratio, 1 - congestion_k * density_per_m / jam_density_per_m)
jam_density_per_m = 1 / (vehicle_length_m + min_following_gap_m)
```

The form is the linear speed-density relation Greenshields fitted to observed highway traffic in
1935, restated in the normalised units a warehouse aisle needs. His primary text states it directly:
"The plotted points shown in Figure 5, seem to represent a straight line relationship between speed <!-- docs-lint-ok STE-01 verbatim quotation of Greenshields 1935 -->
and density per mile", with the fitted relation `S = F' - m * D'` and a slope of 0.221 for the
section reported. The reference is Greenshields, B.D., Bibbins, J.R., Channing, W.S., and Miller,
H.H., "A study of traffic capacity", Highway Research Board Proceedings, volume 14, part 1, pages
448 to 477, 1935, retrieved 2026-08-09 with HTTP 200 from
`onlinepubs.trb.org/Onlinepubs/hrbproceedings/14/14P1-023.pdf`. That file is a scan of the 1935
printing read through optical character recognition, and the quotation above normalises two
scanning artefacts in the words "points" and "line". The relation, the slope, and the free speed
were read from the same pages and are not reconstructions.

Two claims must be kept apart. The relation's form is published and VAL-GATE-CONG-01 checks that the
implementation reproduces the published numbers on a fixture configured to them. The values of
`automation.traffic.congestion_k` and `automation.traffic.min_speed_ratio` for a warehouse AMR fleet
are engineering judgment and carry no published reference, so they are recorded as open question
Q14 and no gate claims them. Section 3 of `docs/design/variability-and-faults.md` records the same
status for every default in its catalog, and G.3 there is the standing record.

`twinflow.automation.congestion_sampled` carries `density_per_m`, `mean_speed_mps`, and
`speed_ratio`. The bottleneck detector sees the resulting `WAITING_TRAFFIC` time on the zone, the
zone enters `RankedResources`, and the LSS engine control-charts the speed ratio. Scenario
SCN-E2E-15 is the case whose correct headline answer is a zone rather than a station, and it exists
so the wider type is exercised rather than declared.

**Deadlock.** Two layers, kept deliberately. Prevention: the reservation manager refuses any
reservation that would create a cycle in the wait-for graph, which makes deadlock impossible under
the protocol (INV-AMR-03). Detection and recovery: an independent watchdog runs cycle detection on
the wait-for graph every `automation.traffic.deadlock_check_s`. A cycle found there is a bug, so the
watchdog appends `twinflow.automation.amr_deadlock_detected`, resolves by forcing the
lowest-priority vehicle in the cycle to back off to the nearest passing bay, and the test suite
treats any detection outside an injected fault scenario as a failure. The prevention proof is only
as good as the code, and the watchdog is the evidence that it holds. Recovery duration is drawn from
`variability.amr.deadlock_resolution`.

**Battery and charging.** State of charge falls by `draw_* * dt / battery_kwh` per state. Below
`automation.amr_fleet.charging.soc_dispatch_floor` the AMR stops accepting tasks and creates a
`charge` task to the nearest free charger, queueing when all are busy. Charging follows a two-phase
curve: constant power to `automation.amr_fleet.charging.cc_cutoff_soc`, then tapering linearly to
zero at a state of charge of 1.0, with the efficiency multiplier drawn from
`variability.amr.charge_efficiency`. `charge_phase_split_s` on the completion event records the time
spent in each phase, so a reader can see the curve rather than infer it.

The curve's shape carries no external published reference for this vehicle class. It is recorded as
open question Q15 and no validation gate claims it. What is tested is the implementation:
`test_charge_curve_integral_matches_closed_form` asserts that simulated charge time equals the
analytic integral of the declared curve to 1e-9, and INV-AMR-02 asserts the energy ledger closes.
A correct ledger with a wrong curve is exactly the failure INV-AMR-02 cannot see, which is why the
open question exists rather than a gate that would pass either way.

Battery state of health degrades under `variability.amr.soh_degradation` and is consumed by the PdM
layer. The twin models the drain and the charge; it does not model cell chemistry.

### 5.7 Palletiser cell behaviour

Cases arrive on the infeed and the cell builds pallets per `PalletPattern`, a list of layer patterns
with case counts and orientations. Per-case cycle time is drawn from `variability.palletiser.cycle`;
layer and pallet changes add their fixed times. On each cycle a Bernoulli draw against
`variability.palletiser.jam_rate_baseline` decides a jam, the jam type is drawn by weight, the cell
enters `DOWN_UNPLANNED`, requests an operator when `requires_operator` is set, waits
`variability.palletiser.jam_clear`, may scrap the case, and resumes.

The numeric jam rate and clear-time distribution are not restated here. They live in
`docs/design/variability-and-faults.md` section B.4 under
`variability.palletiser.jam_rate_baseline` and `variability.palletiser.jam_clear`, which is the
single source of truth for every stochastic parameter in the repository. Those two values carry no
external published reference. Section G.3 of that document records the status for the whole catalog,
and 9 Q16 here records what would settle these two.

Jams publish the telemetry signature declared in the 2b sensor catalog, a motor current spike and a
torque anomaly for the mechanical jam types, so the PdM layer has real work rather than a synthetic
label. INV-PAL-01: cases on a completed pallet equal `pattern.cases_per_pallet` exactly, a jam
mid-pallet leaves a partial pallet whose case count is recorded, and clearing resumes from that
count. No cases appear or vanish across a jam.

Depalletiser mode is the same machine with inverted material flow and its own pattern-recognition
failure mode, `unknown_pattern`, which needs manual help and draws from
`variability.depalletiser.cycle`.

### 5.8 ASRS behaviour

The crane serves a queue of storage and retrieval commands under the configured scheduler. Travel
time between two points is Chebyshev, meaning horizontal and vertical motion run at the same time
and the travel time is the larger of the two leg times:

```
t = max( leg_time(dx, v_h, a_h), leg_time(dy, v_v, a_v) )
```

`leg_time` uses the trapezoidal velocity profile, falling back to the triangular profile when the
distance is too short to reach top speed. Control jitter is a multiplier drawn from
`variability.asrs.cycle_multiplier`. Single command is I/O point to slot to I/O point. Dual command
is I/O point to storage slot to retrieval slot to I/O point. `DUAL_COMMAND_PAIRING` pairs a queued
storage with the queued retrieval that minimises the interleaving leg, subject to a maximum wait so
retrievals are not starved.

Slot selection under `random` draws uniformly from free slots, under `class_based` draws from the
class band the SKU belongs to, and under `dedicated` uses the slotting plan. Failures follow
`FailureSpec`, and a crane down makes its whole aisle unavailable, which is a real and painful
property the bottleneck detector will find.

The Chebyshev assumption is the one behind the travel-time model VAL-GATE-ASRS-01 checks, so the
kinematics and the gate agree by construction rather than by coincidence. Section 9 Q6 records the
tension between the gate's randomised-storage assumption and the slotting layer's dedicated
storage.

### 5.9 Conveyor and sortation behaviour

Conveyor segments are modelled at the unit level with position tracking, not as a delay. A segment
holds units with a minimum gap. An accumulating segment lets units close up when the downstream is
blocked; a non-accumulating one blocks upstream at once. The throughput ceiling of a segment is
`speed_mps / (unit_length_m + min_gap_m)` units per second, and 7.1 asserts the simulated ceiling
matches that arithmetic exactly for a saturated segment. Realised belt speed varies under
`variability.conveyor.speed_multiplier`.

Identity at induct comes from the `ScanPoint` named by `Sorter.read_dependency`. The scan point
draws its read outcome from the 2b read model and, once E46 lands, from the read-zone geometry, so
the twin never invents a read probability of its own. A no-read takes the `missort_on_no_read` path.
This is the chain that makes the source's named receiving step, the RFID portal, a modelled element
rather than a word in a diagram: a portal is a `ScanPoint`, its read outcome is a device-level
draw, and a failed read at the portal becomes a divert failure downstream.

Divert decisions are taken at `decision_point_offset_m` before the chute. When the required chute is
full or the divert window is missed, the item recirculates with an incremented `pass_number`, and
after `automation.sorters[].max_passes` it goes to the reject lane and raises a finding. Recirculation
counts are drawn from `variability.sortation.recirculations`, and mechanical missorts from
`variability.sortation.divert_success`. Every missort is a candidate finding and cross-checks against
the CV throughput counter of component 4.

INV-SORT-01: every inducted unit leaves through exactly one chute or the reject lane, no unit
occupies two chutes, and the count balance closes per window.

### 5.10 Slotting behaviour

`plan_slotting` solves the assignment. Three solvers are selected by problem size, and the solver
used is written into `twinflow.slotting.plan_proposed` so no report hides which one ran.

| Solver               | When it runs                                                 | What it gives                                                     |
| -------------------- | ------------------------------------------------------------ | ----------------------------------------------------------------- |
| Exact assignment     | The objective is separable, meaning `w_affinity` is zero     | A provably optimal SKU-to-slot assignment                         |
| Cube-per-order index | Single-command, dedicated storage, independent demand        | The closed-form reference optimum and the gate target             |
| Local search         | The affinity term makes the problem quadratic                | An improvement over the exact seed, with both objectives reported |

Exact assignment uses `scipy.optimize.linear_sum_assignment`. Local search is simulated annealing
over pairwise swaps, seeded from the exact assignment, drawing proposals and acceptance decisions
from the declared stream `twin.slotting.anneal` and no other source. Naming the stream is what makes
"deterministic under the run seed" a checkable statement rather than a claim.

`evaluate_plan` does not trust the objective. It runs the twin with the current plan and with the
proposed plan over the same demand window under common random numbers and reports the measured
travel-distance delta and picks-per-hour delta with confidence intervals, which is what the source
asks for when it says the deltas are measured by the twin. `reslot_payback` costs the moves as
`labour_minutes = move_distance_m / walk_speed_mps / 60 + handling_time_minutes`, prices them at the
labour rate plus equipment time, and computes payback days from the measured savings rather than the
modelled ones.

Re-slotting for a new demand mix is a first-class named scenario,
`scenarios/reslot_new_demand_mix.yaml`, which takes a demand-mix patch, recomputes velocities,
replans, evaluates, and produces the payback report.

### 5.11 Automation what-ifs

The three the source names ship as worked scenarios, each parameterised so a reader can change the
numbers.

| Scenario file                                | Patch                                                                | Cost fields it must carry                                               |
| -------------------------------------------- | -------------------------------------------------------------------- | ----------------------------------------------------------------------- |
| `scenarios/replace_forklifts_with_amrs.yaml` | Remove two forklift operator resources, add three AMRs and a charger | `capex_usd`, `install_usd`, `opex_annual_usd`, `labour_delta_fte` of -2 |
| `scenarios/second_palletiser_cell.yaml`      | Add a cell and split the infeed                                      | `capex_usd`, `install_usd`, `opex_annual_usd`                           |
| `scenarios/asrs_crane_speed_plus_20.yaml`    | Raise `horizontal_speed_mps` and `vertical_speed_mps` by 20 percent  | `capex_usd` of the drive upgrade, `life_years`                          |

Each returns throughput, cost, energy, and operator-impact deltas plus the LSS verdict. Operator
impact comes from E6 as an `OperatorImpact` carrying `utilisation_by_operator`, `peak_utilisation`,
`level_loading_index`, and `cumulative_strain_delta`. Energy comes from E7. When either provider is
absent the field is null and the report reads `operator impact not evaluated: provider absent`
rather than a zero. Silence is honest and a fabricated zero is not.

### 5.12 What-if experiment engine

`ExperimentEngine.run(scenario)` does six things in order.

1. Resolve the base configuration: a `facility.yaml` path, a `run_id` whose config snapshot is in
   the historian, or a live `TwinSnapshot`.
2. Apply `ScenarioPatch` and re-validate the patched document against the facility schema. A patch
   that produces an invalid facility fails here, before any compute is spent.
3. Derive per-replication seeds. Exogenous streams take `replication_index = i` with the scenario id
   fixed to `baseline`; endogenous streams take `replication_index = i` with this scenario's id.
   Exogenous streams match across arms as a result, which is common random numbers.
4. Run `replications` independent replications, each in its own process, each writing its own tape.
5. Compute `WindowMetrics` per replication over the post-warm-up window.
6. Return `ScenarioResult` with per-replication KPI vectors, not only means.

**Result ordering.** Workers finish in whatever order the operating system schedules them, so the
collection step sorts. `ScenarioResult.replications` is sorted by `replication_index` ascending
before any statistic is computed, and `ComparisonTable.rows` is sorted by `scenario_id` as a byte
string before ranking. INV-SCN-04 asserts that a run with the worker pool size set to 1, 2, and 8
produces byte-identical `ScenarioResult` serialisations. Per-tape determinism is not enough on its
own: a correct set of tapes assembled in completion order still gives two different comparison
tables from one seed.

`ExperimentEngine.compare(scenario_set)` runs the baseline and every arm under common random numbers
and calls the LSS engine for a paired test per KPI, a paired t-test where the assumption checker
passes and a Wilcoxon signed-rank test otherwise, reporting effect size and confidence interval. The
paired test is chosen only when the `crn_integrity` record shows identical draw counts on every
shared stream; otherwise the independent-samples test runs and the table states which test ran and
why. Common random numbers correlate the arms, and an unpaired test on correlated samples is wrong,
so the pairing has to be checked rather than assumed.

**Ranking rule.** The cost model is stated once:

```
annualised_cost_usd = (capex_usd + install_usd - salvage_usd / (1 + r)^life) * CRF(r, life)
                      + opex_annual_usd
                      + labour_delta_fte * costs.labour_rate_usd_per_hour
                                         * costs.annual_hours_per_fte
                                         * costs.labour_burden_multiplier
CRF(r, n) = r * (1 + r)^n / ((1 + r)^n - 1)
annual_net_saving_usd = -annualised_cost_usd
```

Labour enters exactly once, through `labour_delta_fte`, and `opex_annual_usd` carries energy,
maintenance, and consumables and nothing else. Section 3.10 states the split on the entity, and
`test_labour_is_not_double_counted` asserts that raising `labour_delta_fte` by one changes
`annualised_cost_usd` by exactly the priced amount and changes nothing else.

The ratio `throughput_delta_units_per_year / annualised_cost_usd` is undefined or sign-flipping when
the denominator is zero or negative, and the flagship automation scenario produces exactly that:
removing two operators can make the annualised cost negative. Ordering is instead defined over
three buckets, and `RankBucket` is a field on `RankedOption` rather than an implicit consequence of
a sort.

| Bucket             | Membership                                                              | Ordered by                                | `throughput_per_dollar` |
| ------------------ | ----------------------------------------------------------------------- | ----------------------------------------- | ----------------------- |
| `PAYS_FOR_ITSELF`  | `annualised_cost_usd <= 0` and the throughput delta is not negative     | `annual_net_saving_usd` descending        | null, with a caveat     |
| `COSTS_MONEY`      | `annualised_cost_usd > 0`                                               | `throughput_per_dollar` descending        | the computed ratio      |
| `NOT_WORTH_IT`     | The throughput delta is negative and `annualised_cost_usd > 0`          | `annualised_cost_usd` ascending           | null, with a caveat     |

Buckets print in that order. Inside `COSTS_MONEY`, options whose throughput delta is significant at
`alpha` come before options that are not, and each of the latter carries the caveat
`delta not statistically distinguishable from zero at alpha=<a> with n=<n> replications`. Ties break
on lower `annualised_cost_usd`. Options dominated on the Pareto front over throughput, cost, energy,
and peak operator utilisation are flagged `pareto_dominated: true` and stay in the table rather than
disappearing, because a reader's first question is why something is missing.

The table renders to Markdown and HTML with a footnote per row naming `assumption_source`,
`replications`, `seed`, and the `run_id` set. That footnote is the difference between a consulting
deliverable and a screenshot.

### 5.13 Event-sourced replay and counterfactuals (E4)

Three modes, one command.

`replay --exact` re-executes the recorded run from its manifest and asserts `state_hash` equality.
This applies the C1 determinism gate to real recorded runs, not only to test fixtures.

`replay --to <event_id>` reconstructs state at any event by loading the nearest preceding
`TwinSnapshot` and re-applying tape entries in the canonical total order of D-07. Snapshots are
written every `historian.snapshot_interval_s` and at every `twinflow.twin.window_measured`. This is
time-travel debugging, and `explain_finding` in component 7 uses it to show the state at the instant
a finding fired.

`replay --patch <scenario.yaml>` is the counterfactual. Its semantics are declared per scenario in
`ExogenousBoundary`.

Exogenous by default, meaning replayed verbatim from the source run: truck readiness times and
manifests, order arrivals and lines, supplier lot quality outcomes, injected device faults and chaos
events, weather state (E40), absenteeism draws (6a14), and demand realisations.

Endogenous, meaning re-simulated: everything the facility does, including which door a truck gets,
which AMR takes a task, station service times, queueing, sortation outcomes, and storage assignment.

The subtle case is a patch that changes the appointment schedule, which is E12's whole point. Arrival
times then stop being exogenous and the boundary must be redeclared as
`exogenous_boundary: {truck_arrivals: "readiness_only"}`, meaning the recorded value used is the
truck's readiness time, when it could have arrived, and the scheduled slot becomes endogenous. The
engine validates that every stream named in the patch is consistent with the declared boundary and
refuses to run otherwise, naming the conflicting stream. A counterfactual whose boundary is wrong
produces a number that looks fine and is meaningless, so this check is not optional.

INV-SCN-01, the null-patch identity property: `replay --patch <empty>` with the same boundary
reproduces the original `state_hash` exactly. This single property catches almost every replay bug.

The headline demo is a valid scenario rather than an aspiration, and the patch is shown in full so a
reader can check it against the patchable allowlist of 6.5.

```yaml
# scenarios/second_portal_dock3.yaml
scenario_id: second_portal_dock3
label: Second scan portal at dock 3
base: profiles/midmarket_3pl.yaml
replications: 30
horizon_s: 86400
alpha: 0.05
exogenous_boundary:
  truck_arrivals: verbatim
patch:
  - op: add
    path: /facility/scan_points/-
    value:
      scan_point_id: sp-dock3-b
      zone_id: zone-dock
      door_id: door-3
      device_ref: rfid-portal-dock3-b
      read_model_ref: rfid_uhf_portal_v1
      service_time: { dist: constant, value_s: 0 }
      occupancy: 1
      identity_scope: pallet
      on_no_read: recirculate
      uns_equipment: portal-3b
  - op: replace
    path: /facility/sorters/0/read_dependency
    value: sp-dock3-b
cost:
  capex_usd: 18500
  install_usd: 4200
  life_years: 7
  salvage_usd: 0
  opex_annual_usd: 900
  labour_delta_fte: 0
  assumption_source: "Portal capex from the shipped capex_catalog entry rfid_portal_4antenna"
```

`/facility/scan_points/-` is in the patchable allowlist, which is what makes the demo pass config
validation. Running it against a recorded day is
`twinflow scenario replay --run <yesterday> --patch scenarios/second_portal_dock3.yaml
--replications 30`, and it returns a paired comparison against the actual recorded day.

### 5.14 Reality to twin calibration (component 6)

The `Calibrator` runs on `sync.calibration_interval_s` and on demand. For each declared calibratable
parameter it does five things.

1. Pull the observation window from the historian: telemetry plus derived activity durations.
2. Fit the declared family, one of `lognormal`, `gamma`, `exponential`, or `empirical`, by maximum
   likelihood, or by a trimmed-likelihood estimator when `estimator: robust_mle`, so
   one stuck sensor does not move the model.
3. Shrink towards the prior, which is the current config value, with weight
   `n / (n + sync.shrinkage_pseudocount)`. This stops a twenty-observation window from rewriting a
   parameter.
4. Run a change-point test, Pettitt or a CUSUM on the parameter series, so a genuine process shift
   is flagged as `changepoint_detected` rather than smoothed into the estimate. A detected change
   point raises a finding and pauses automatic acceptance for that parameter.
5. Accept the estimate when the relative change is within `sync.max_parameter_step_pct` and the
   standard error is below `sync.max_relative_se`; otherwise record `accepted: false` with a reason.

Accepted estimates produce a new `config_version` recorded in
`twinflow.sync.calibration_completed`, and the live twin instance is rebuilt from it at the next
window boundary, never mid-window, so a metrics window never straddles two parameter sets.

**Hard rule.** The calibrator may not read the ground-truth generator parameters. The device fleet's
true physics live in `catalog/sensors.yaml` and `ground_truth/reality_offsets.yaml`, and
`twinflow-sync` declares neither as a dependency. A CI import lint asserts that no module under
`twinflow.sync` or `twinflow.twin` imports the ground-truth loader, and a runtime capability check
raises when the path is opened. INV-SYNC-01 covers both halves. Without this rule, calibration,
measurement system analysis, and divergence are all theatre.

### 5.15 Divergence as a finding

`DivergenceMonitor` tracks a declared list of paired signals, twin-predicted against
reality-observed: throughput per window, per-station cycle time at the median and the 90th
percentile, WIP, dock queue length, AMR task completion rate, sorter divert rate, and energy per
pallet. For each it computes the standardised residual against the twin's predictive distribution,
obtained from the replication ensemble rather than from a point prediction, then runs an EWMA with
`sync.ewma_lambda`, default 0.2, and a two-sided CUSUM. Crossing the control limit appends
`twinflow.sync.divergence_observed`, which the LSS engine wraps as a finding with
`finding_type = "TWIN_DIVERGENCE"` and a severity from the residual magnitude and the business
impact of the signal.

Divergence findings pass through the same alarm rationalisation path as every other finding, which
is dedupe by signal and window, severity ranking, and shelving. Alarm rationalisation is owned by
the LSS section and is needed here from P3; 1.2 records it as an interface consumed and not owned,
with the fallback that divergence findings are not deduped and this subsection states the risk. A
model that goes badly wrong without deduplication produces a flood rather than one escalating
finding.

The suggested next tool is `recalibrate` when the divergence is a level shift with no change point
in the inputs, and `investigate_assignable_cause` when a change point coincides with an input
change. That chaining is the Black Belt behaviour the LSS section specifies.

**The known false positive between P3 and P4.** Store-and-forward is component 6c and lands at P4.
Between P3 and P4 the monitor has no late-arrival window, so a replayed telemetry burst after a
broker outage arrives as a step change in observed throughput and reads as divergence. Any demo run
in that interval that includes a broker outage produces a spurious `TWIN_DIVERGENCE` finding. The
interim mitigation is stated rather than hidden: `sync.suppress_after_gap_s` (default 0, meaning
off) suppresses divergence evaluation for a stated period after a telemetry gap longer than
`sync.gap_threshold_s`, the suppression is recorded on the signal as `late_arrival_suppressed`, and
the shipped P3 profiles set it to zero so nothing is hidden by default. At P4 the monitor gains the
real late-arrival window keyed on the store-and-forward replay marker, and the interim key is
removed in the same commit that adds it.

### 5.16 Twin to reality write path

Reality in this repository is the running production-mode system: the device fleet simulator, the
line controller configuration it reads, and the yard appointment schedule. `ConfigWriter` is the
only component permitted to write it. It writes by appending `twinflow.autonomy.change_applied` with
the patch. The controller applies it at the next safe point and acknowledges with its resulting
`config_hash`. `ConfigWriter` compares that hash against the expected one and raises when they
differ, so a partially applied change cannot pass unnoticed.

### 5.17 Autonomy tiers and audit trail (E5)

At L1 advise, the agent may propose. `ChangeRequest` is created in state `PROPOSED` and appears in
the findings stream and on the dashboard. Nothing is written to reality. This is the default and the
demo default.

At L2 recommend with approval, a `PROPOSED` request needs an explicit approval from a human `Actor`
holding the authority declared in `autonomy.approvers`. The request expires at `expires_at_s` when
unapproved.

At L3 auto-apply within guardrails, the change is applied without human approval if and only if
every guardrail passes. Guardrails are evaluated in a fixed order and all must pass: the path is in
the L3 whitelist; the new value is within `[min, max]`; the step size is within `max_step_pct`; the
cooldown since the last change on that path has elapsed; changes in the rolling window are below
`max_changes_per_window`; the blast radius is at or below the tier's allowance; the predicted effect
is statistically significant per the attached hypothesis test; and the evidence is fresher than
`autonomy.max_evidence_age_s`. Any failure appends `twinflow.autonomy.change_rejected` naming the
guardrail.

**Identity is cryptographic and self-contained.** Each `Approval` carries an Ed25519 signature over
the `change_hash`, the signer's `public_key_id`, and an `authority_scope` expressed as a list of
JSON Pointer prefixes. The keys come from `autonomy.approvers`, a keyring declared in
`autonomy.yaml` with one entry per approver holding the public key in PEM form. The keyring is
independent of the broker's transport security. The source lists mTLS on the OT broker as an
optional stretch under component 6c, so an identity story that borrowed the broker's certificate
authority would inherit that uncertainty. Where mTLS is deployed, an operator may point a keyring
entry at the certificate's public key, and that is a configuration choice rather than a dependency.

`verify_audit_chain` checks three things and returns the first failure with its entry index: the
hash chain is unbroken; replaying the chain from genesis reproduces the current running
configuration exactly (INV-AUT-02); and every `Approval` verifies against the registered public key
with an `authority_scope` covering the patched path (INV-AUT-03). An entry whose signature does not
check out, whose key is not registered, or whose scope does not cover the path is rejected. Section
7.1 names `test_forged_approval_is_rejected` and `test_out_of_scope_approval_is_rejected`, which
tamper with the patch and swap the key respectively. Ed25519 verification uses `pynacl`, which is
why 2.5 lists it.

Post-application monitoring: `rollback_trigger` is a metric predicate evaluated over
`autonomy.observation_window_s` after application, for example
`throughput_per_hour < baseline_ci95_low for 3 consecutive windows`. Tripping it appends
`twinflow.autonomy.change_reverted`, restores the previous config version, and raises a finding. The
revert path is tested, because an autonomy story without a tested revert is a liability.

Every state transition appends to the `AuditChain` with actor, evidence references, config hashes,
and, for agent actors, the model id and prompt hash. `twinflow autonomy audit --check` walks the
chain and reproduces the current config. The demo shows the chain rendered as a table answering who
or what changed the line, when, why, on what evidence, and what happened next.

### 5.18 Optimisation engine (E9)

A study is declared in `experiments/*.study.yaml`: the search space, each parameter a JSON Pointer
plus a distribution of `int`, `float`, `log_float`, or `categorical`; the objectives with name,
direction, and weight; the constraints `budget_usd`, `max_peak_operator_utilisation`, and
`max_energy_kwh_per_pallet`; the sampler; the pruner; and the evaluation protocol of replications
per trial, horizon, and warm-up.

`run_study` builds an Optuna study, version 4.9.0 under the MIT licence. The sampler is
`TPESampler` seeded from the declared stream `twin.optimize.sampler`, or `GPSampler` for expensive
low-dimensional spaces, or `NSGAIISampler` or `MOTPESampler` for multi-objective studies. Pruning
uses `HyperbandPruner` over replications, so a trial clearly worse after 5 of 30 replications stops.
Each trial is evaluated with `TwinEvaluator`, or with `SurrogateEvaluator` followed by full-sim
confirmation of the top k when `evaluator: surrogate`. Budget constraints use Optuna's constrained
optimisation support so infeasible trials inform the sampler rather than being dropped in silence.

Output is a `StudyResult` with the best trial, the Pareto front for multi-objective studies, and
every trial's parameters and objectives. The Pareto front converts directly into a `ScenarioSet` and
flows into `compare_scenarios`, which is the requirement that E9 feeds the scenario-ranking table.

Determinism: sequential execution with a seeded sampler is reproducible. Parallel trial execution is
not, because trial completion order feeds the sampler. The study manifest records the
trial-number to parameters mapping, `run_study --replay <study_id>` re-evaluates exactly that
sequence, and `twinflow.optimize.study_completed` carries `execution` so a reader can tell which
mode produced a published number. Studies behind published results run sequentially or are replayed.
Section 9 Q8 records the decision still open.

### 5.19 Learned AGV dispatch (E11)

`AmrDispatchEnv` is a Gymnasium environment wrapping the twin in simulation mode, where one step is
one dispatch decision.

The observation is built only from `StateView`, the same object the rule-based policies get. It
carries per-AMR features, which are a position embedding on the graph, state of charge, current
state, and distance to each open task origin; per-task features, which are age, slack to due time,
priority, and origin and destination zone; and zone-level congestion features. It is fixed size
through top-k task and AMR truncation under a declared ordering, `(due_time_s, task_id)` for tasks
and `(distance_m, amr_id)` for vehicles, both compared with the id as a byte-string tie-break.

The action is an index into the (AMR, task) pair matrix plus a `no_assignment` action, with a mask
removing infeasible pairs where the AMR is busy, the state of charge is below the floor, or the
payload is exceeded. Masking is needed rather than optional; an unmasked policy spends its whole
budget learning feasibility.

The reward is
`w_thr*completed_tasks - w_late*lateness_s - w_travel*empty_travel_m - w_energy*energy_kwh -
w_traffic*waiting_traffic_s`, with the weights in the study config and printed alongside every
result, because a reward function is a hidden objective statement. The algorithm is MaskablePPO,
with a curriculum from E25's scenario corpora ordered by arrival intensity and fault density.

**Determinism.** Applying D-04, the policy never calls `torch` from inside the simulation loop. It
calls the kernel `Inference` port. In training and benchmark mode the port binds `TorchInference`,
which runs CPU-only with `torch.use_deterministic_algorithms(True)`, a thread count pinned to 1, and
a pinned policy-weights hash. In replay mode the port binds `RecordedInference`, which replays the
recorded response cassette, so a replayed run reproduces the recorded decisions without re-running
the network. The weights hash and the torch version are recorded in `RunProvenance`, and a change to
either invalidates the golden files for the RL scenarios. `twinflow.optimize.dispatch_benchmarked`
carries the weights hash so a published table names the artefact it came from.

**Observation parity.** The honest-benchmark claim rests entirely on the learned policy seeing no
more than the rule-based one, and a claim with no test is a slogan. `StateView` declares a frozen
allowlist of fields in `twinflow/twin/state_view.py`, and the deny list is explicit: no pending
event queue, no RNG state, no fault schedule, no arrival time that has not yet happened, and no
ground-truth parameter. INV-RL-01 in 7.2 asserts the allowlist and the deny list hold under
generated facilities, and 7.7 asserts the stronger property, that the observation is a pure function
of `StateView` and that a fault injected in the future does not change the current observation.

**Benchmark protocol.** A held-out seed set of `benchmark.n_seeds`, default 200, is generated once,
committed, and never used in training. Training and evaluation seed sets are disjoint by
construction and `test_train_and_eval_seed_sets_are_disjoint` asserts the intersection is empty.
Every policy runs the identical seed set under common random numbers. The metrics are tasks
completed per hour, mean and 95th-percentile task lateness, empty travel metres per task, energy per
task, traffic wait per task, deadlock events, and decision latency taken from the `MetricsSink`
series of 4.9. The statistics are a paired Wilcoxon signed-rank test per metric through the LSS
engine, with the Hodges-Lehmann effect size and confidence interval and a Holm correction across the
metric family. Generalisation is measured by repeating the benchmark on the two facility profiles
the policy was not trained on (A2) and reporting them separately; a policy that wins only on its
training facility is reported as such. The table is published in `docs/benchmarks/dispatch.md` and
in the README whatever the outcome. When the heuristic wins, the README says the heuristic wins and
by how much, and the RL code stays.

### 5.20 Yard and dock scheduling (E12)

`YardProblem` is solved with CP-SAT from OR-Tools. The model has one `IntervalVar` per truck, whose
start lies within its arrival window and whose duration comes from the manifest and the door's
unload rate; `AddNoOverlap` per door; `AddCumulative` over the labour profile; and
`AddAllowedAssignments` for door capability, so a refrigerated trailer cannot take a
non-refrigerated door.

The objective is a weighted sum of detention cost, labour overtime hours, total truck dwell, and
door changeover count, with the weights in `yard.yaml`.

**Deterministic bounding.** Applying D-04, a solve whose plan the twin executes is bounded by a
deterministic budget and never by wall time. The settings are fixed and the brick refuses to hand a
plan to the twin when any of them is missing.

| Setting                      | Value                                     | Reason                                                                  |
| ---------------------------- | ----------------------------------------- | ----------------------------------------------------------------------- |
| `max_deterministic_time`     | `yard.max_deterministic_time`             | A machine-speed-independent budget, which a wall-clock deadline is not  |
| `num_search_workers`         | 1                                         | Multi-threaded search returns a machine-dependent incumbent             |
| `random_seed`                | Derived from the stream `twin.yard.cpsat` | The solver's own randomness joins the run's seed tree                   |
| `max_branches`               | `yard.max_branches`                       | A second deterministic cap, so a pathological instance still terminates |
| Wall-clock cap               | `yard.max_solve_wall_s`, raises on breach | A safety net that fails loudly rather than returning a different plan   |

`YardPlan` records `deterministic_time_used`, `branches_used`, and `solver_status`. It carries no
wall-clock field, because the plan steers the simulation and anything inside it is hashed. The
wall-clock duration of the solve goes to the `MetricsSink` series named in 4.9. A timeout on the
deterministic budget returns the best incumbent and says so in `solver_status`; a breach of the
wall-clock cap raises, because a plan produced past the safety net is a plan whose determinism
nobody can vouch for.

**Cross-dock.** `YardProblem.crossdock_links` is empty until Phase 3g. The cross-dock extension adds
a precedence constraint plus a maximum staging dwell between an inbound and its paired outbound, and
adds missed connections to the objective. Section 8 splits E12 into the two pieces for that reason:
the base model lands before P3g because cross-docking needs it, and the extension lands with P3g
because it needs cross-docking.

**Labour.** `YardProblem.labour_profile` comes from a `LabourProfileProvider`. The shipped
`CalendarLabourProfile` reads shift patterns and headcount from `calendars.yaml`, so E12 runs before
E23 exists. When E23 lands it registers a provider reading `twinflow.workforce.roster_published`,
and the yard solver changes not at all.

`plan_realisability` is the honesty check. The plan's predicted makespan is compared against the
twin executing the plan under the stochastic model. A plan built on deterministic unload times looks
better on paper than in the twin, and the gap is reported as `gap_pct`. When the gap exceeds
`yard.realisability_tolerance_pct`, the scheduler re-solves with duration estimates taken from
`yard.duration_quantile`, default 0.7, of the twin's distribution rather than from the mean, and
`twinflow.optimize.yard_plan_checked` records `requantiled: true`. This turns a naive deterministic
scheduler into a defensible one, and it is the failure mode real appointment systems have.

### 5.21 Learned twin surrogate (E28)

`encode_config` produces a fixed-length feature vector from a facility document plus a scenario
descriptor: counts and capacities per resource class, service-time distribution moments, the hourly
arrival intensity profile, SKU mix summary statistics, the slotting plan summary as mean and
90th-percentile travel distance, automation parameters, and staffing. Categorical structure is
one-hot with a declared vocabulary so the encoding is stable across versions, and the encoder
version is stamped on every prediction.

The targets are the KPI vector `compare_scenarios` needs: throughput per day, flow time at the
median and 95th percentile, peak WIP, utilisation of the top three resources, energy per pallet, and
peak operator utilisation.

The corpus is every trial from every Optuna study, every scenario replication, and a space-filling
design over the declared envelope run specifically for training. `build_corpus` deduplicates by
config hash and records provenance per row for the E25 dataset card.

The model ladder runs baseline first: ridge regression on the encoded features as the floor, then
LightGBM as the real baseline, then an MLP, then a sequence model over the hourly arrival profile. A
model is promoted only when it beats the incumbent on held-out mean absolute error for every target
under a paired test, and the comparison is published. When LightGBM wins, the README calls it a
gradient-boosted surrogate and the neural label is not used. Section 9 Q10 records the naming
decision.

Validation runs against held-out configs never seen in training, from a separate space-filling
batch. `ValidationReport` publishes the error distribution per target as mean absolute error, mean
absolute percentage error, and the 50th, 90th, and 99th percentiles of absolute error; the interval
coverage from split conformal prediction at 80 and 95 percent nominal; and two decision-quality
measures that matter more than error, which are top-1 agreement, whether the surrogate picks the
same winner as the twin from a candidate set, and Kendall tau between the surrogate and twin
rankings.

Coverage has a published finite-sample guarantee and the gate uses it. Decision agreement does not,
so 7.9 splits them: VAL-GATE-SURR-01 checks coverage against the conformal bound, and the decision
measures are published and gated only against the committed baseline. Section 9 Q17 records that no
external reference fixes an acceptable agreement level and states what would settle it.

`screen_and_confirm(candidates, k)` scores every candidate with the surrogate, takes the top k by
predicted objective plus an exploration quota drawn from the declared stream `twin.optimize.explore`
against the upper conformal bound, runs those on the full sim, and returns the sim's answer. A
surrogate number is never shown to a user or an agent without the flag `surrogate_estimate: true`
and its interval, and the E26(f) grounding checker treats an unconfirmed surrogate number as
unsourced unless the sentence carries that flag.

`DomainEnvelope` stores the training feature distribution and `in_domain` tests a query with a
Mahalanobis distance threshold plus per-feature range checks. Out-of-domain queries return
`in_domain: false` and no prediction, and the caller falls back to the full sim. A surrogate that
extrapolates in silence is worse than no surrogate.

---

## 6. Configuration

All configuration is YAML, validated at load against JSON Schema generated from the Pydantic models,
with line-numbered errors carrying a suggestion (C5). `twinflow config validate <path>` and
`--dry-run` on every command are needed entry points. Every file carries `schema_version` and the
loader refuses a major-version mismatch, pointing at `twinflow config upgrade` (C6).

### 6.0 Which file a parameter goes in

The source says parameters live in one config file, and A2 says the entire operation is defined in a
`facility.yaml`. This section ships more than one file, so it states the departure as a departure
and gives the rule that decides where a parameter goes. Hiding a split behind a diagram is how a
reader ends up guessing.

| File                       | Holds                                                                 | Test that decides                                           |
| -------------------------- | --------------------------------------------------------------------- | ----------------------------------------------------------- |
| `facility.yaml`            | Everything that describes this building and its equipment             | Would a different building change it? Then it lives here    |
| `catalog/*.yaml`           | Reusable equipment and item definitions shared across buildings       | Would two buildings share the identical entry? Then catalog |
| `costs.yaml`               | Money: rates, prices, discount rate, capex catalog                    | Is it denominated in currency?                              |
| `calendars.yaml`           | Shift patterns, breaks, holidays, headcount by interval               | Is it a time pattern rather than a physical fact?           |
| `sync.yaml`                | Calibration and divergence policy                                     | Does it govern how the twin learns from reality?            |
| `autonomy.yaml`            | Tiers, approvers, guardrails, L3 whitelist                            | Does it govern what may be written back?                    |
| `yard.yaml`                | E12 solver settings and objective weights                             | Does it configure a solver rather than the building?        |
| `benchmark.yaml`           | Held-out seed sets, replication counts, published-table paths         | Does it configure an experiment rather than an operation?   |
| `scenarios/*.yaml`         | One what-if each                                                      | Is it a change to the building rather than the building?    |
| `experiments/*.study.yaml` | One optimisation study each                                           | Is it a search over changes?                                |

`facility.yaml` remains the single document that defines the operation, and A2's promise holds:
modelling a different building is editing `facility.yaml` and the catalogs it references. The other
files configure the machinery that studies the building, and none of them changes what the building
is. `twinflow config explain <key>` prints which file set a key and why that file owns it, which
turns the rule above from prose into a command a reader can run.

### 6.1 `facility.yaml`, twin core keys

| Key                                   | Type                    | Validation                                                                                        |
| ------------------------------------- | ----------------------- | ------------------------------------------------------------------------------------------------- |
| `schema_version`                      | semver string           | Must match a supported major                                                                      |
| `facility.facility_id`                | slug                    | `^[a-z0-9-]{3,40}$`, unique                                                                       |
| `facility.tick_ns`                    | int                     | Power of 10 from 1e3 to 1e9, default 1e6                                                          |
| `facility.calendar_id`                | ref                     | Must resolve in `calendars.yaml`                                                                  |
| `zones[].zone_id`                     | slug                    | Unique                                                                                            |
| `zones[].kind`                        | enum                    | See 3.1                                                                                           |
| `zones[].polygon_m`                   | list of 2-tuples        | At least 3 points, a simple polygon, non-self-intersecting                                        |
| `zones[].isa95_area`                  | string                  | Non-empty when any device attaches to a resource in the zone                                      |
| `zones[].uns_path`                    | string                  | Enterprise, site, and area segments, no leading or trailing slash                                 |
| `zones[].travel_length_m`             | float                   | `> 0` when the zone contains travel-graph edges; the denominator of 5.6's density                 |
| `dock_doors[].door_id`                | slug                    | Unique                                                                                            |
| `dock_doors[].modes`                  | list of enum            | Non-empty, sorted at load, no duplicates                                                          |
| `dock_doors[].restraint_time_s`       | DistributionSpec        | Support strictly positive                                                                         |
| `scan_points[].scan_point_id`         | slug                    | Unique; exactly one of `door_id` or `station_id` is set                                           |
| `scan_points[].device_ref`            | ref                     | Must resolve in the component 2 fleet config                                                      |
| `scan_points[].read_model_ref`        | ref                     | Must resolve in the 2b sensor catalog                                                             |
| `scan_points[].on_no_read`            | enum                    | `manual_key`, `recirculate`, or `reject_lane`                                                     |
| `stations[].station_id`               | slug                    | Unique                                                                                            |
| `stations[].capacity`                 | int                     | `>= 1`                                                                                            |
| `stations[].priority_discipline`      | enum                    | `fifo` or `priority`; selects the SimPy resource class in 5.1; no default                         |
| `stations[].service_time`             | DistributionSpec        | Support strictly positive, mean finite                                                            |
| `stations[].ideal_cycle_time_s`       | float                   | `> 0` and `<=` the 1st percentile of `service_time`; the error names the violated bound           |
| `stations[].buffer_capacity`          | int or null             | `>= 0`; null means unbounded, which warns because unbounded buffers hide bottlenecks              |
| `stations[].successors[].probability` | float                   | Sum to 1.0 within 1e-9 per station                                                                |
| `stations[].failure`                  | FailureSpec             | `mtbf_s > 0`, `mttr` support positive                                                             |
| `arrivals.mode`                       | enum                    | `schedule`, `poisson`, `trace`, or `forecast_driven`                                              |
| `arrivals.rate_per_hour`              | float or hourly profile | `> 0`; a profile has length 24                                                                    |
| `arrivals.trace_uri`                  | path                    | Needed when `mode: trace`; the file must exist                                                    |
| `metrics.window_s`                    | int                     | `>= 60`, divides the horizon                                                                      |
| `metrics.warmup`                      | object                  | `policy: welch`, `fixed`, or `none`; `none` warns and names the risk                              |
| `metrics.oee_convention`              | enum                    | `nakajima` or `semi_e79`; no default, must be chosen                                              |
| `metrics.minor_stop_threshold_s`      | float                   | `> 0`, default 300                                                                                |
| `metrics.startup_window_s`            | float                   | `>= 0`, default 600; the six-big-losses startup-rejects window of 5.4                             |
| `metrics.demand_units_per_day`        | int or null             | Needed when no ERP stub is present, else null; the only demand-override key                       |
| `metrics.batch_autocorr_threshold`    | float                   | 0 to 1, default 0.1                                                                               |
| `metrics.little_law_min_l`            | float                   | `> 0`, default 1.0; below this the residual is suppressed with a reason                           |
| `distributions.catalog_uri`           | path                    | Must resolve; the file's `catalog_version` is pinned and recorded in the run manifest             |
| `distributions.min_empirical_samples` | int                     | `>= 2`, default 30; the floor for an `empirical` DistributionSpec                                 |
| `scheduling.priority_classes`         | map                     | Every producer id present, integers unique; the tie-break of 5.2                                  |
| `historian.snapshot_interval_s`       | int                     | `>= metrics.window_s`; the snapshot cadence 5.13 replays from                                     |

`DistributionSpec` is a tagged union: `{dist: "lognormal", mean_s, cv}`, `{dist: "gamma", shape,
scale_s}`, `{dist: "triangular", min_s, mode_s, max_s}`, `{dist: "empirical", samples_uri}`, and
`{dist: "constant", value_s}`. Validation asserts non-negative support, a finite mean, and for
`empirical` that the file exists and holds at least `distributions.min_empirical_samples` rows. The
spec carries an optional `stream` name so two stations can be told to share or not share a stream,
which matters for common random numbers.

`FailureSpec` is `{mtbf_s, mttr: DistributionSpec, failure_modes: [{name, weight, mttr_override,
telemetry_signature_ref, scrap_probability}]}`. Validation asserts the weights sum to 1.0 and that
every `telemetry_signature_ref` resolves in the sensor catalog.

### 6.2 `facility.yaml`, automation keys

| Key                                                  | Type   | Validation                                                                                                                       |
| ---------------------------------------------------- | ------ | -------------------------------------------------------------------------------------------------------------------------------- |
| `automation.amr_fleet.enabled`                       | bool   |                                                                                                                                  |
| `automation.amr_fleet.vehicles[]`                    | list   | Each with `amr_id` and a `model_id` resolving in `catalog/amr_models.yaml`                                                       |
| `automation.amr_fleet.dispatch.policy`               | string | A registered `DispatchPolicy` id; an unknown id lists the registered ones                                                        |
| `automation.amr_fleet.dispatch.tick_s`               | float  | `> 0`, default 1.0                                                                                                               |
| `automation.amr_fleet.charging.policy`               | enum   | `threshold`, `opportunity`, or `swap`                                                                                            |
| `automation.amr_fleet.charging.soc_dispatch_floor`   | float  | 0 to 1, strictly below `soc_target`                                                                                              |
| `automation.amr_fleet.charging.soc_target`           | float  | 0 to 1                                                                                                                           |
| `automation.amr_fleet.charging.cc_cutoff_soc`        | float  | 0 to 1, strictly above `soc_dispatch_floor`; the phase boundary of 5.6                                                           |
| `automation.amr_fleet.chargers[]`                    | list   | `charger_id`, a `node_id` resolving on the travel graph, `power_kw > 0`                                                          |
| `automation.travel_graph.source`                     | enum   | `derived` from zone polygons and the aisle spec, or `file`                                                                       |
| `automation.travel_graph.aisles[]`                   | list   | `width_m > 0`, `one_way` bool; connectivity is checked and the load fails naming the unreachable nodes                           |
| `automation.travel_graph.vehicle_length_m`           | float  | `> 0`; a jam-density input in 5.6                                                                                                |
| `automation.travel_graph.min_following_gap_m`        | float  | `>= 0`; the other jam-density input                                                                                              |
| `automation.traffic.congestion_k`                    | float  | `>= 0`, default 0.35; carries no external reference, see 9 Q14                                                                   |
| `automation.traffic.min_speed_ratio`                 | float  | 0 to 1, default 0.25; carries no external reference, see 9 Q14                                                                   |
| `automation.traffic.replan_delay_s`                  | float  | `> 0`                                                                                                                            |
| `automation.traffic.deadlock_check_s`                | float  | `> 0`                                                                                                                            |
| `automation.palletisers[]`                           | list   | `cell_id`, a `pattern_id` resolving in `catalog/pallet_patterns.yaml`                                                            |
| `automation.asrs[]`                                  | list   | `bays >= 1`, `levels >= 1`, speeds `> 0`, a `storage_policy` enum; `class_boundaries` needed and monotone when `class_based`     |
| `automation.conveyors[]`                             | list   | `speed_mps > 0`, `min_gap_m >= 0`, `capacity_units >= 1`                                                                         |
| `automation.sorters[]`                               | list   | `induct_rate_units_per_min > 0`, every `chutes[].chute_id` unique                                                                |
| `automation.sorters[].read_dependency`               | ref    | Resolves to a `scan_points[].scan_point_id`, not to a device id                                                                  |
| `automation.sorters[].max_passes`                    | int    | `>= 1`, default 3                                                                                                                |
| `automation.uns.line`                                | string | The line segment of the topic built in 4.8; non-empty when any resource carries `uns_equipment`                                  |

Jam rates, cycle-time families, and every other stochastic parameter are not keys here. They live in
the distribution catalog that `distributions.catalog_uri` points at, which is the single source of
truth named in 6.0 and in `docs/design/variability-and-faults.md` section B.1. Two homes for one
number is the defect this repository exists to criticise.

### 6.3 `facility.yaml`, slotting keys

| Key                                | Type    | Validation                                                                                                                                |
| ---------------------------------- | ------- | ----------------------------------------------------------------------------------------------------------------------------------------- |
| `slotting.enabled`                 | bool    |                                                                                                                                           |
| `slotting.storage_mode`            | enum    | `dedicated`, `random`, or `class_based`                                                                                                   |
| `slotting.objective.w_travel`      | float   | `>= 0`                                                                                                                                    |
| `slotting.objective.w_replen`      | float   | `>= 0`                                                                                                                                    |
| `slotting.objective.w_affinity`    | float   | `>= 0`; a positive value needs an affinity source, else the load fails                                                                    |
| `slotting.objective.w_ergo`        | float   | `>= 0`                                                                                                                                    |
| `slotting.objective.normalise`     | enum    | `none`, `zscore`, or `range`; needed when more than one weight is non-zero, because summing raw metres and risk indices is meaningless    |
| `slotting.ergonomic_provider`      | enum    | `proxy_v1`, `niosh`, or `rula`; the latter two need `twinflow-ergonomics` installed                                                       |
| `slotting.golden_zone_m`           | 2-tuple | `0 <= low < high`, default `[0.75, 1.40]`                                                                                                 |
| `slotting.golden_zone_scale_m`     | float   | `> 0`, default 0.50; the denominator of `proxy_v1` in 3.9                                                                                 |
| `slotting.solver`                  | enum    | `auto`, `exact`, `coi`, or `local_search`                                                                                                 |
| `slotting.local_search.iterations` | int     | `> 0`                                                                                                                                     |
| `slotting.replan_cadence`          | enum    | `manual`, `daily`, `weekly`, or `on_demand_mix_shift`                                                                                     |
| `slotting.max_moves_per_replan`    | int     | `>= 0`; 0 means propose only                                                                                                              |
| `slotting.affinity_source`         | enum    | `order_lines`, `synthetic`, or `none`                                                                                                     |

### 6.4 `costs.yaml`

Keys: `labour_rate_usd_per_hour` by role, `annual_hours_per_fte`, `labour_burden_multiplier`,
`energy_price_usd_per_kwh`, `discount_rate` between 0 and 1 exclusive, `default_life_years`,
`maintenance_pct_of_capex_per_year`, `detention_usd_per_hour`, `overtime_multiplier`, and a
`capex_catalog` mapping equipment model ids to acquisition and install cost.

Validation: the discount rate is strictly between 0 and 1, because a zero rate makes the capital
recovery factor undefined at the limit and the error says so; every cost is non-negative; and every
equipment id a scenario references resolves. `annual_hours_per_fte` and `labour_burden_multiplier`
are here rather than in `facility.yaml` because 5.12's cost model prices `labour_delta_fte` with
them, and the money rule of 6.0 puts money in one file.

### 6.5 `scenarios/*.yaml` and `experiments/*.study.yaml`

Scenario keys: `scenario_id`, `label`, `base` as a facility path or a `run_id`, `patch` as a list of
JSON Patch operations, `cost` as a `ScenarioCost`, `exogenous_boundary`, `replications` as an
integer at least 5 with a warning below 20, `horizon_s`, `warmup_policy`, `alpha` default 0.05, and
`notes`.

Validation: every patch path exists in the base document and is in the patchable allowlist; the
patched document validates; and `cost.assumption_source` is non-empty, because an unattributed cost
assumption is rejected rather than printed.

The patchable allowlist is declared in the facility schema with the `x-patchable` annotation, and
the paths it covers are listed here so a scenario author does not have to read the schema.

| Patchable path prefix              | Why it is patchable                                                             |
| ---------------------------------- | ------------------------------------------------------------------------------- |
| `/facility/scan_points/`           | The headline demo adds a portal (5.13)                                          |
| `/facility/stations/`              | Capacity, service time, staffing, and buffer what-ifs                           |
| `/facility/dock_doors/`            | Door count and mode what-ifs                                                    |
| `/facility/automation/`            | Every 1b what-if in 5.11                                                        |
| `/facility/slotting/`              | Re-slotting and objective-weight what-ifs                                       |
| `/facility/arrivals/`              | Demand and appointment what-ifs, which trigger 5.13's boundary rule             |
| `/facility/metrics/`               | Window and warm-up what-ifs, which change measurement rather than the operation |

Everything else is non-patchable, and `facility.facility_id`, `facility.tick_ns`, and
`schema_version` are named in the schema as such so the error message can say why.

Study keys: `study_id`, `base`, `space` as a list of `{path, type, low, high, step, choices, log}`,
`objectives` as a list of `{metric, direction, weight}`, `constraints`, `sampler` from `tpe`, `gp`,
`nsga2`, `motpe`, or `random`, `pruner`, `n_trials`, `replications_per_trial`, `evaluator` of `twin`
or `surrogate`, `confirm_top_k`, and `stream_name`. Validation: every `path` is patchable and its
type matches the declared distribution; at least one objective is present; and every constraint
metric exists in `WindowMetrics`.

### 6.6 `sync.yaml` and `autonomy.yaml`

`sync.yaml` keys: `calibration_interval_s`; `calibratable_parameters` as a list of JSON Pointers
each with `family`, `estimator`, and `min_observations`; `shrinkage_pseudocount` as an integer at
least 0; `max_parameter_step_pct` from 0 to 100; `max_relative_se`; `changepoint_test` of `pettitt`,
`cusum`, or `none`; `divergence_signals` as a list with `metric`, `ewma_lambda`, `cusum_k`,
`cusum_h`, and `severity_map`; `detect_budget_s`, the sim-time budget SCN-E2E-08 and VAL-GATE-SYNC-01
measure detection against; `gap_threshold_s`; and `suppress_after_gap_s`, the interim mitigation of
5.15, default 0.

Validation: every pointer is calibratable per the facility schema's `x-calibratable` annotation;
every `metric` exists in `WindowMetrics`; `ewma_lambda` lies in (0, 1]; and `suppress_after_gap_s`
is 0 in every shipped profile, asserted by a test rather than by convention.

`autonomy.yaml` keys: `default_tier`, which must be `L1_ADVISE` in shipped profiles; `approvers` as
the keyring of 5.17, each entry holding `actor_id`, `public_key_id`, a PEM Ed25519 public key, and
an `authority_scope` list of JSON Pointer prefixes; `guardrails` as a list of `Guardrail`;
`max_evidence_age_s`; `observation_window_s`; and `l3_whitelist` as a list of JSON Pointers.

Validation: every whitelisted path has at least one guardrail with `min`, `max`, and `max_step_pct`
set; every `authority_scope` prefix is a patchable path; no two approvers share a `public_key_id`;
and `l3_whitelist` is empty unless `autonomy.acknowledge_l3: true` is set, so nobody turns on
auto-apply by accident.

### 6.7 `yard.yaml` and `benchmark.yaml`

`yard.yaml` configures E12's solver and objective. Nothing here describes the building.

| Key                                 | Type  | Validation                                                                        |
| ----------------------------------- | ----- | --------------------------------------------------------------------------------- |
| `yard.max_deterministic_time`       | float | `> 0`; the CP-SAT deterministic budget of 5.20                                    |
| `yard.max_branches`                 | int   | `> 0`; the second deterministic cap                                               |
| `yard.max_solve_wall_s`             | float | `> 0`; the safety net that raises rather than returning a different incumbent     |
| `yard.realisability_tolerance_pct`  | float | `> 0`, default 10; the re-solve trigger of 5.20                                   |
| `yard.duration_quantile`            | float | 0 to 1 exclusive, default 0.7; used on re-solve                                   |
| `yard.objective.w_detention`        | float | `>= 0`                                                                            |
| `yard.objective.w_overtime`         | float | `>= 0`                                                                            |
| `yard.objective.w_dwell`            | float | `>= 0`                                                                            |
| `yard.objective.w_changeover`       | float | `>= 0`                                                                            |
| `yard.objective.w_missed_crossdock` | float | `>= 0`; must be 0 until `crossdock_links` is non-empty, else the load fails       |
| `yard.labour_provider`              | enum  | `calendar` or `roster`; `roster` needs E23 installed                              |

`benchmark.yaml` configures experiments, not operations.

| Key                               | Type   | Validation                                                                             |
| --------------------------------- | ------ | -------------------------------------------------------------------------------------- |
| `benchmark.n_seeds`               | int    | `>= 30`, default 200; the held-out seed count of 5.19                                  |
| `benchmark.seed_set_uri`          | path   | Must exist and be committed; the file is content-hashed into the published table       |
| `benchmark.training_seed_set_uri` | path   | Must exist; the intersection with the held-out set must be empty                       |
| `benchmark.published_table_uri`   | path   | Default `docs/benchmarks/dispatch.md`; CI fails when the file is missing or stale      |
| `benchmark.surrogate_holdout_n`   | int    | `>= 100`, default 500; the held-out batch of 5.21                                      |
| `benchmark.coverage_reps`         | int    | `>= 100`, default 400; the repetition count VAL-GATE-QUEUE-02's interval is derived at |

### 6.8 Every key in this section resolves to a row

An implementer must not need to guess, and prose that names a key no table declares is a guess with
extra steps. `scripts/checks/config-reference-gate.py` extracts every backticked token in this
document matching `<file>.<dotted.path>` or a bare `<section>.<key>` in the declared key namespaces,
resolves each against the tables in section 6 and against the generated facility schema, and fails
on the first token that resolves to nothing. It applies the same discipline to configuration that
the schema registry applies to events. The gate runs in the docs job and its failure message names
the document, the line, and the token.

---

## 7. Testing

Four tiers with runtime budgets (C4). `just test-fast` runs tiers 1 and 2 inside 90 seconds.
`just test-scenarios` runs tier 3 inside 10 minutes. `just test-gates` runs tier 4 inside 20
minutes. CI runs all four on push, path-filtered per brick (C10). Subsection 7.10 states how those
budgets are held.

Applying D-12, every test below names the observation that would fail it. A test whose failure
condition cannot be described is deleted and replaced rather than kept as decoration.

### 7.1 Tier 1, unit tests

Per package, with the usual coverage of parsers, validators, and formulas. The ones that are easy
to get wrong, and the ones that hold a rule in this document, are named.

| Test                                                   | Asserts                                                                                                                       | Fails when                                                              |
| ------------------------------------------------------ | ----------------------------------------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------- |
| `test_crf_matches_closed_form`                         | `capital_recovery_factor(r, n) * ((1+r)^n - 1) / (r * (1+r)^n) == 1` to 1e-12 over a grid of r and n                          | The identity fails for any grid point                                   |
| `test_conveyor_throughput_ceiling`                     | `speed_mps / (unit_length_m + min_gap_m)` equals the simulated maximum induct rate for a saturated segment                    | The simulated ceiling differs by more than one unit per hour            |
| `test_trapezoidal_travel_profile`                      | Crane travel below the accelerate-plus-decelerate distance uses the triangular branch, and the branches agree at the boundary | The two branches disagree at the boundary distance                      |
| `test_charge_curve_integral_matches_closed_form`       | Simulated charge time equals the analytic integral of the declared two-phase curve to 1e-9                                    | The integral and the simulation disagree                                |
| `test_oee_both_conventions`                            | One equipment log yields the two documented OEE values and neither convention is defaulted                                    | A convention is silently chosen, or the two agree when they must not    |
| `test_patch_rejects_non_patchable_path`                | A patch touching `facility.facility_id` fails at parse with the path named                                                    | The patch parses, or the message omits the path                         |
| `test_exogenous_boundary_conflict_detected`            | A patch changing appointments without redeclaring the truck-arrival boundary raises, naming the stream                        | The run starts, or the message omits the stream                         |
| `test_guardrail_rejects_out_of_bounds`                 | Every guardrail field independently blocks a change                                                                           | Any single field can be violated without a rejection                    |
| `test_forged_approval_is_rejected`                     | An `Approval` whose signature covers a different `change_hash` fails `verify_audit_chain`                                     | The chain checks out, or the failure index is wrong                     |
| `test_out_of_scope_approval_is_rejected`               | A valid signature from a key whose `authority_scope` does not cover the patched path is rejected                              | The change is applied                                                   |
| `test_slotting_infeasible_when_cube_exceeds_all_slots` | An infeasibility report naming the SKU and the binding constraint, not an exception                                           | An exception is raised, or the report omits the constraint              |
| `test_two_skus_equal_picks_unequal_cube_order_by_cube` | The bulkier SKU never gets the strictly nearer mean travel                                                                    | The bulkier SKU is placed nearer                                        |
| `test_simultaneous_events_order_canonically`           | 200 events at one tick from four producers, across 50 insertion shuffles, give one tape order                                 | Any shuffle produces a different order                                  |
| `test_every_draw_site_has_a_registered_stream`         | Every sampler call site in these eight packages resolves to a registry entry                                                  | A generator is constructed outside the registry                         |
| `test_no_wall_clock_field_in_any_declared_payload`     | No schema this section owns carries a wall-clock property outside the three sinks of 4.9                                      | A new payload property matches the wall-clock naming convention         |
| `test_no_set_typed_field_in_the_domain_model`          | No Pydantic model in these packages carries a `set` annotation                                                                | A `set` annotation appears                                              |
| `test_protocol_surface_matches_declaration`            | Every runtime protocol signature matches `/schemas/protocols/twinflow-protocols.v1.yaml`                                      | A method name, parameter, or return type drifts                         |
| `test_labour_is_not_double_counted`                    | A one-FTE change moves `annualised_cost_usd` by exactly the priced amount and moves nothing else                              | `opex_annual_usd` also moves, or the delta is wrong                     |
| `test_missing_consumed_subject_degrades_as_declared`   | Each row of 4.7 behaves as its fallback column says with the producer uninstalled                                             | An exception is raised, or a zero is reported instead of a null         |
| `test_train_and_eval_seed_sets_are_disjoint`           | The held-out and training seed sets share no element                                                                          | The intersection is non-empty                                           |
| `test_uns_topic_is_unique_per_facility`                | INV-TWIN-11, concatenated topics are unique                                                                                   | Two resources build the same topic                                      |
| `test_device_attachment_resolves`                      | INV-TWIN-12, every `attaches_to` resolves to a resource and a declared parameter                                              | A dangling attachment loads without an error                            |

### 7.2 Tier 2, property-based invariants

Each property generates facilities, demand profiles, and fault schedules from a constrained
strategy, runs a short horizon, and asserts the invariant. Hypothesis is version 6.165.2 under
MPL-2.0, which the dependency ledger records; the licence question that raises for the allowlist is
the repository's to settle and is recorded in the ledger rather than here.

| ID          | Invariant                                                                                                                                      |
| ----------- | ---------------------------------------------------------------------------------------------------------------------------------------------- |
| INV-TWIN-01 | Material conservation: `units_received == units_in_system + units_putaway + units_scrapped` at every event boundary                            |
| INV-TWIN-02 | Monotone clock: tape `twinflowsimts` non-decreasing, and `twinflowseq` dense per `(run_id, producer_id)`                                       |
| INV-TWIN-03 | Little's Law holds inside the batch-means interval, under the stationarity precondition stated below                                           |
| INV-TWIN-04 | No negative WIP, queue length, or inventory at any instant                                                                                     |
| INV-TWIN-05 | Resource capacity respected: concurrent users never exceed declared capacity                                                                   |
| INV-TWIN-06 | Pallet single-location: exactly one `LocationRef` per pallet per instant                                                                       |
| INV-TWIN-07 | Activity closure: every `activity_started` has exactly one `activity_completed` or `activity_aborted`, and no overlap on a capacity-1 resource |
| INV-TWIN-08 | OEE bounds: A, P, Q in [0,1], `oee == a*p*q` to 1e-12, `oee <= min(a,p,q)`                                                                     |
| INV-TWIN-09 | State trace closure: per resource, summed state durations equal the window length exactly in integer ticks                                     |
| INV-TWIN-10 | Scan closure: every pallet past a scan point has a `SCANNED` transition or a recorded no-read outcome                                          |
| INV-TWIN-11 | UNS topic uniqueness within a facility                                                                                                         |
| INV-TWIN-12 | Device attachment resolution                                                                                                                   |
| INV-AMR-01  | Node and one-way-edge exclusivity under the reservation protocol                                                                               |
| INV-AMR-02  | SOC in [0,1], non-increasing while not charging, energy ledger closes to 1e-9                                                                  |
| INV-AMR-03  | Wait-for graph acyclic at every decision point                                                                                                 |
| INV-AMR-04  | Task conservation: assigned equals completed plus cancelled plus reassigned                                                                    |
| INV-ASRS-01 | One crane per aisle, and a retrieval returns the pallet stored in the addressed slot                                                           |
| INV-ASRS-02 | Occupied slot count equals stored pallet count                                                                                                 |
| INV-SORT-01 | Every inducted unit leaves through exactly one chute or the reject lane, and counts balance                                                    |
| INV-PAL-01  | Cases on a completed pallet equal the pattern count, and jams neither create nor destroy cases                                                 |
| INV-SLOT-01 | Plan feasibility: all hard constraints satisfied, every SKU assigned its `slots_required` slots, no double assignment                          |
| INV-SLOT-02 | Velocity monotonicity under the travel-only objective with homogeneous slots                                                                   |
| INV-SLOT-03 | Cube monotonicity: equal picks and unequal cube never place the bulkier SKU at strictly nearer mean travel                                     |
| INV-SCN-01  | Null-patch identity: an empty patch replay reproduces `state_hash`                                                                             |
| INV-SCN-02  | Exogenous trace fidelity: replayed exogenous events match the source in count and sim time                                                     |
| INV-SCN-03  | Common random numbers pairing: two arms with the same seed have identical exogenous streams and matching draw counts                           |
| INV-SCN-04  | Replication ordering: worker pool sizes 1, 2, and 8 give byte-identical `ScenarioResult` serialisations                                        |
| INV-AUT-01  | Guardrail containment: no applied change lies outside declared bounds, and L3 never touches a non-whitelisted path                             |
| INV-AUT-02  | Audit completeness: replaying the chain reproduces the current config hash with no gaps                                                        |
| INV-AUT-03  | Approval validity: every entry carries a verifying signature from a registered key whose scope covers the patched path                         |
| INV-SYNC-01 | Calibration isolation: no module in `twinflow.sync` or `twinflow.twin` can reach the ground-truth loader                                       |
| INV-RL-01   | Observation parity: the learned policy's observation is a pure function of `StateView`, and no denied field reaches it                         |
| INV-SURR-01 | Out-of-envelope queries return no prediction                                                                                                   |
| INV-OPT-01  | Sequential study reproducibility: the same seed yields the same trial sequence                                                                 |

INV-TWIN-03 carries a precondition, because Little's Law is not testable over freely generated
facilities without one. A generated facility can be near-empty or near-saturated over a short
horizon, and `abs(L - lambda*W) / L` divides by a quantity that approaches zero in a lightly loaded
window, so any fixed percentage tolerance rejects correct simulations there. The property now runs only on generated
configurations that pass three preconditions, and skips with a recorded reason otherwise: the
offered load lies in [0.3, 0.9]; the post-warm-up window holds at least 500 completions; and the
time-weighted mean `L` is at least `metrics.little_law_min_l`. Its assertion is that
`lambda * W` lies inside the batch-means 95 percent confidence interval for `L`, which scales its
tolerance with the sample it has. The fixed-tolerance form belongs on a known analytic
fixture, and that is VAL-GATE-QUEUE-01.

### 7.3 Tier 3, seeded end-to-end scenarios with golden files

Each scenario runs against every A2 profile that declares the subsystem it exercises, writes a golden JSON of
`WindowMetrics`, `BottleneckReport`, `ValueStreamSummary`, and the tape hash, and diffs.

| ID         | Scenario                                                                        | Asserts                                                                                                                                        |
| ---------- | ------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------- |
| SCN-E2E-01 | `baseline_shift`, 8 simulated hours                                             | Golden metrics, tape hash, and the runtime budget of 7.10                                                                                      |
| SCN-E2E-02 | `second_portal_dock3` counterfactual on a recorded run                          | A paired comparison is produced, and null-patch identity holds on the same run                                                                 |
| SCN-E2E-03 | `replace_forklifts_with_amrs`                                                   | Throughput, cost, energy, and operator-impact fields are populated or explicitly null with a reason, and the option lands in `PAYS_FOR_ITSELF` |
| SCN-E2E-04 | `second_palletiser_cell`                                                        | The bottleneck moves off the palletiser and the report names where it moved to                                                                 |
| SCN-E2E-05 | `asrs_crane_speed_plus_20`                                                      | ASRS cycle time drops, and the throughput gain saturates once the constraint moves, with the saturation asserted                               |
| SCN-E2E-06 | `reslot_new_demand_mix`                                                         | The measured travel delta's sign matches the objective's predicted sign, and the payback report is produced                                    |
| SCN-E2E-07 | `dock_schedule_optimised`                                                       | `plan_realisability` gap within tolerance after the quantile re-solve, and `requantiled` recorded                                              |
| SCN-E2E-08 | `divergence_drift`, a 12 percent service-time offset injected into reality only | A `TWIN_DIVERGENCE` finding is raised within `sync.detect_budget_s` of sim time, and the calibrator recovers the offset afterwards             |
| SCN-E2E-09 | `autonomy_L3_guardrail_trip`                                                    | A change outside bounds is rejected, the audit chain records the rejection, and nothing is written to reality                                  |
| SCN-E2E-10 | `autonomy_L3_rollback`                                                          | An applied change that degrades throughput trips `rollback_trigger`, reverts, and raises a finding                                             |
| SCN-E2E-11 | `amr_deadlock_stress`, narrow aisles and high task density                      | Zero deadlock detections, traffic wait time recorded, and the run completes                                                                    |
| SCN-E2E-12 | `sorter_no_read_storm`, read rate degraded to 85 percent                        | Recirculation and reject counts balance, findings are raised, and no units are lost                                                            |
| SCN-E2E-13 | `warm_whatif_midshift`, forked from a live snapshot at 4 simulated hours        | The forked run's first event continues the parent's state exactly                                                                              |
| SCN-E2E-14 | `rl_dispatch_shift`, the learned policy driving dispatch for 8 simulated hours  | The tape hash is stable across two runs and across a fresh process, with `Inference` bound to `RecordedInference` on the second                |
| SCN-E2E-15 | `congested_zone_headline`, aisle traffic as the binding constraint              | `headline_resource.kind == "zone"`, and the three detectors' agreement flag is recorded                                                        |
| SCN-E2E-16 | `crossdock_yard_plan`, E12 with `crossdock_links` populated                     | Precedence and staging-dwell constraints hold in the executed plan, and missed connections are counted                                         |
| SCN-E2E-17 | `broker_outage_replay`, a telemetry gap then a replayed burst                   | With `suppress_after_gap_s` at 0 the spurious finding appears and is asserted; with the P4 late-arrival window it does not                     |
| SCN-E2E-18 | `surrogate_screen_and_confirm`, 200 candidates screened, top 5 confirmed        | Every surfaced number carries `surrogate_estimate` or a confirming `run_id`, and out-of-domain candidates return no prediction                 |

SCN-E2E-14 exists because VAL-GATE-DET-01 covers every tier-3 scenario and no earlier scenario ran
the learned policy, so the torch path was outside the determinism gate's reach. SCN-E2E-15 exists so
the resource-typed bottleneck report of 3.4 is exercised rather than only declared. SCN-E2E-17
asserts the known false positive of 5.15 in both directions, so the P4 fix is proved to fix
something.

### 7.4 Tier 4, validation gates

Every gate satisfies D-11: it names a specific external published reference with a locator, its
tolerance is never tighter than the precision of the published value it checks, a gate over a
stochastic quantity states a measured noise floor and sets its tolerance above it, and each states
what result falsifies it.

Two gates in the table check exact equality of this system with itself rather than agreement with a
published quantity. VAL-GATE-DET-01 and VAL-GATE-DET-02 compare two runs of the same code, so there
is no published value to be checked against and no tolerance to be too tight. They are listed with
their falsification conditions and are marked as such rather than being given a citation that would
not mean anything.

| Gate                 | External published reference                                                                                                                                                                                                                                                                                                                                                                                                                                              | Assertion and tolerance                                                                                                                                                                                                                                                                                                                                      | Noise floor and falsification                                                                                                                                                                                                                                                                                    |
| -------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| VAL-GATE-QUEUE-01    | Little, J.D.C. (1961), "A Proof for the Queuing Formula: L = lambda W", Operations Research 9(3), 383-387, DOI 10.1287/opre.9.3.383                                                                                                                                                                                                                                                                                                                                       | On an M/M/1 twin configuration at offered load 0.7, `lambda * W` lies inside the batch-means 95 percent confidence interval for `L`, over 30 replications                                                                                                                                                                                                    | The interval half-width is the noise floor and is reported. Falsified when `lambda * W` lies outside the interval in more than 2 of 30 replications                                                                                                                                                              |
| VAL-GATE-QUEUE-02    | Gross, D., Shortle, J.F., Thompson, J.M., and Harris, C.M., Fundamentals of Queueing Theory, 5th edition, Wiley 2018, DOI 10.1002/9781119453765, M/M/1 chapter                                                                                                                                                                                                                                                                                                            | Coverage: over `benchmark.coverage_reps` (400) seeded repetitions at offered load 0.7, the count of repetitions whose batch-means 95 percent interval covers the analytic `L` lies in the exact binomial acceptance region [365, 392]                                                                                                                        | The region is derived from Binomial(400, 0.95) at 0.001 per tail, so a correct build fails about 12 times in 10,000 runs. Falsified when the count lands outside [365, 392]                                                                                                                                      |
| VAL-GATE-QUEUE-02b   | Same reference, M/M/1 closed forms                                                                                                                                                                                                                                                                                                                                                                                                                                        | Point accuracy: for offered load in {0.5, 0.7, 0.9}, simulated `L = rho/(1-rho)` and `Wq = rho/(mu*(1-rho))` within 3 percent over 30 replications                                                                                                                                                                                                           | The 3 percent tolerance is set above the measured batch-means half-width at load 0.9, which the fixture records. Falsified when any load's point estimate falls outside                                                                                                                                          |
| VAL-GATE-QUEUE-03    | Same reference, M/G/1 chapter, the Pollaczek-Khinchine formula                                                                                                                                                                                                                                                                                                                                                                                                            | With deterministic and with lognormal service, simulated `Wq = lambda*E[S^2] / (2*(1-rho))` within 3 percent                                                                                                                                                                                                                                                 | Tolerance set above the measured half-width for the lognormal case, which is the wider of the two. Falsified when either service law falls outside                                                                                                                                                               |
| VAL-GATE-QUEUE-04    | Same reference, M/M/c chapter, the Erlang C formula                                                                                                                                                                                                                                                                                                                                                                                                                       | A dock-door bank with c in {2, 4, 8}: the simulated probability of waiting matches Erlang C within 2 percent                                                                                                                                                                                                                                                 | Tolerance set above the measured binomial standard error of the waiting proportion at c = 8. Falsified when any c falls outside                                                                                                                                                                                  |
| VAL-GATE-QUEUE-05    | Jackson, J.R. (1957), "Networks of Waiting Lines", Operations Research 5(4), 518-521, DOI 10.1287/opre.5.4.518                                                                                                                                                                                                                                                                                                                                                            | For an open Jackson network with known routing, per-station arrival rates match the traffic equations within 1 percent, and `by_utilisation` names `argmax(lambda_i / mu_i)` as the bottleneck                                                                                                                                                               | Tolerance set above the measured standard error of the per-station rate estimate. Falsified when a rate falls outside, or when the ranking names a different station                                                                                                                                             |
| VAL-GATE-ASRS-01     | Bozer, Y.A. and White, J.A. (1984), "Travel-Time Models for Automated Storage/Retrieval Systems", IIE Transactions 16(4), 329-338, DOI 10.1080/07408178408975252                                                                                                                                                                                                                                                                                                          | Under randomised storage with Chebyshev travel, normalised expected single-command time matches `E[SC] = 1 + b^2/3` and dual-command time matches `E[DC] = 4/3 + b^2/2 - b^3/30`, for shape factor b in {0.25, 0.5, 0.75, 1.0}, to 1 percent, 100,000 cycles                                                                                                 | Noise floor is the standard error over 100,000 cycles, which the fixture records and which is far below 1 percent. Falsified when any b falls outside, or when the two forms cross                                                                                                                               |
| VAL-GATE-SLOT-01     | Malmborg, C.J. and Bhaskaran, K. (1990), "A revised proof of optimality for the cube-per-order index rule for stored item location", Applied Mathematical Modelling 14(2), 87-95, DOI 10.1016/0307-904x(90)90076-h                                                                                                                                                                                                                                                        | In the reference case of single-command, dedicated storage, independent demand, and homogeneous slot capacity, `plan_slotting` returns exactly the cube-per-order-index ordering, asserted as set equality of SKU-to-slot pairs                                                                                                                              | Deterministic, so no noise floor applies. Falsified by any pair differing from the index ordering                                                                                                                                                                                                                |
| VAL-GATE-SLOT-01b    | Kallina, C. and Lynn, J. (1976), "Application of the Cube-Per-Order Index Rule for Stock Location in a Distribution Warehouse", Interfaces 7(1), 37-46, DOI 10.1287/inte.7.1.37                                                                                                                                                                                                                                                                                           | The 3.9 objective reduces to the index ordering in the reference case, asserted symbolically on the formula and numerically on 200 instances                                                                                                                                                                                                                 | Deterministic. Falsified when the reduction fails on any instance, which would mean the cube term was written wrongly rather than that the gate is loose                                                                                                                                                         |
| VAL-GATE-SLOT-02     | Jonker, R. and Volgenant, A. (1987), "A shortest augmenting path algorithm for dense and sparse linear assignment problems", Computing 38(4), 325-340, DOI 10.1007/bf02278710, with the implementation notes in Crouse, D.F. (2016), IEEE Transactions on Aerospace and Electronic Systems 52(4), 1679-1696, DOI 10.1109/taes.2016.140952                                                                                                                                 | On 200 random separable instances up to 300 SKUs, the exact solver reproduces the published algorithm's optimum to 1e-9, and the local-search solver lands within 1 percent of it                                                                                                                                                                            | The exact branch is deterministic. The local-search branch's spread over 200 instances is measured and reported, and the 1 percent bound sits above it. Falsified when the exact branch is not optimal, or when local search exceeds 1 percent                                                                   |
| VAL-GATE-SLOT-03     | Waters, T.R., Putz-Anderson, V., and Garg, A. (1994), Applications Manual for the Revised NIOSH Lifting Equation, DHHS (NIOSH) Publication 94-110, worked examples                                                                                                                                                                                                                                                                                                        | With `ergonomic_provider: niosh`, the recommended weight limit and lifting index for the manual's worked examples reproduce the published values to the precision the manual prints. The gate lives in `twinflow-ergonomics`, and `twinflow-slotting` asserts it delegates and that `ergonomic_risk` decreases monotonically in the recommended weight limit | Deterministic. Falsified when any worked example differs at the manual's printed precision. Retrieval note: `cdc.gov` and `stacks.cdc.gov` returned HTTP 403 on 2026-08-09, so the publication number and title here come from the citation and not from retrieved primary text                                  |
| VAL-GATE-CONG-01     | Greenshields, B.D., Bibbins, J.R., Channing, W.S., and Miller, H.H. (1935), "A study of traffic capacity", Highway Research Board Proceedings 14, part 1, 448-477, retrieved 2026-08-09 HTTP 200 from onlinepubs.trb.org                                                                                                                                                                                                                                                  | On a single-corridor fixture configured to the paper's reported free speed and its fitted slope of 0.221, the simulated mean speed reproduces `S = F' - m * D'` to the third decimal of the slope, which is the precision the paper prints                                                                                                                   | Noise floor is the standard error of mean speed over the fixture's vehicle passes, measured and reported; the tolerance is the larger of the paper's precision and three standard errors. Falsified when the simulated relation is non-linear in density, or when the fitted slope differs beyond that tolerance |
| VAL-GATE-DEADLOCK-01 | Coffman, E.G., Elphick, M., and Shoshani, A. (1971), "System Deadlocks", ACM Computing Surveys 3(2), 67-78, DOI 10.1145/356586.356588, the four necessary conditions                                                                                                                                                                                                                                                                                                      | A constructed resource-allocation state satisfying all four conditions is refused by the reservation manager at the allocation that would complete the circular wait. Over 10,000 randomised high-contention episodes, zero deadlock detections                                                                                                              | Deterministic for the constructed state. For the episodes, one detection is a failure, so no noise floor applies. Falsified by any allocation that completes a circular wait, or by any detection                                                                                                                |
| VAL-GATE-SCHED-01    | Graham, R.L. (1969), "Bounds on Multiprocessing Timing Anomalies", SIAM Journal on Applied Mathematics 17(2), 416-429, DOI 10.1137/0117039                                                                                                                                                                                                                                                                                                                                | For identical parallel doors with no time windows, the longest-processing-time heuristic's makespan stays within the published `4/3 - 1/(3m)` bound of the CP-SAT optimum on 500 random instances, and CP-SAT matches brute force exactly for n at most 7                                                                                                    | Deterministic given the instances and the fixed CP-SAT settings of 5.20. Falsified when any instance exceeds the bound, or when CP-SAT and brute force disagree                                                                                                                                                  |
| VAL-GATE-OPT-01      | Jamil, M. and Yang, X.-S. (2013), "A literature survey of benchmark functions for global optimisation problems", International Journal of Mathematical Modelling and Numerical Optimisation 4(2), 150, DOI 10.1504/ijmmno.2013.055204                                                                                                                                                                                                                                     | `run_study` on Sphere, Rosenbrock, Rastrigin, and Ackley in 5 dimensions reaches within 1 percent of the published global optimum inside the configured trial budget, seeded and sequential                                                                                                                                                                  | The across-seed spread of the best value is measured over 20 seeds and reported; the 1 percent bound sits above it. Falsified when the median best value over those seeds exceeds 1 percent                                                                                                                      |
| VAL-GATE-CRN-01      | Law, A.M., Simulation Modeling and Analysis, 5th edition, McGraw-Hill 2015, ISBN 978-0-07-340132-4, common random numbers chapter                                                                                                                                                                                                                                                                                                                                         | On the `second_portal_dock3` comparison over 100 paired replications, the variance of the paired difference estimator under common random numbers is not greater than under independent streams, and the measured ratio is reported rather than asserted                                                                                                     | The ratio's own sampling distribution is an F ratio on 99 and 99 degrees of freedom, whose 95 percent upper point is computed in the fixture. Falsified when the measured ratio exceeds that upper point, which would mean the pairing is broken                                                                 |
| VAL-GATE-WARMUP-01   | Welch, P.D. (1983), "The Statistical Analysis of Simulation Results", in Lazowska et al., Computer Performance Modeling Handbook, Academic Press, cited as a single secondary locator because the Crossref index returns no record for the chapter; the procedure is also described in Law, Simulation Modeling and Analysis, 5th edition, initial-transient chapter                                                                                                      | On M/M/1 started empty at offered load 0.8, the post-warm-up mean falls within 3 percent of the analytic `L` and the untruncated mean does not, with both directions asserted                                                                                                                                                                                | Tolerance set above the measured batch-means half-width at load 0.8. Falsified when the truncated mean misses, or when the untruncated mean happens to pass, which would mean the fixture is not transient enough to test anything                                                                               |
| VAL-GATE-OEE-01      | Nakajima, S. (1988), Introduction to TPM: Total Productive Maintenance, Productivity Press, ISBN 978-0-915299-23-5, OEE definition and the six big losses; SEMI E10 and SEMI E79 for the alternative convention                                                                                                                                                                                                                                                           | Two encoded worked equipment logs, one per convention, reproduce the OEE the cited source prints, to the precision that source prints, in rational arithmetic. Separately, OEE recomputed from the tape equals the model's instrumented counters exactly                                                                                                     | Deterministic. Falsified when either convention's figure differs at the source's printed precision, or when the tape and the counters disagree. The fixture records the page locator it transcribed from, and a fixture with no locator fails the gate                                                           |
| VAL-GATE-VSM-01      | Rother, M. and Shook, J. (1999), Learning to See, Lean Enterprise Institute, ISBN 978-0-9667843-0-5, current-state map worked example                                                                                                                                                                                                                                                                                                                                     | A `ValueStreamSummary` computed from an encoded event log reproducing the book's stated station times, changeovers, uptimes, and inventories yields the same total lead time, total value-added time, and process cycle efficiency, at the map's stated precision. Only the small worked dataset is encoded; the book is cited and not redistributed         | Deterministic. Falsified when any of the three totals differs at the map's precision. The fixture records its page locator, and a fixture with no locator fails the gate                                                                                                                                         |
| VAL-GATE-SYNC-01     | Lucas, J.M. and Saccucci, M.S. (1990), "Exponentially Weighted Moving Average Control Schemes: Properties and Enhancements", Technometrics 32(1), 1-12, DOI 10.1080/00401706.1990.10484583                                                                                                                                                                                                                                                                                | With `ewma_lambda` and the control limit set to a row of the paper's published average run length tables, the measured average run length to detection for that row's shift size matches the published value to the precision the table prints, over 1,000 seeded series                                                                                     | The standard error of the run-length mean over 1,000 series is measured and reported; the tolerance is the larger of the table's precision and three standard errors. Falsified when the measured average run length falls outside for any tabulated row                                                         |
| VAL-GATE-SYNC-02     | The sampling distribution of the maximum likelihood estimator for the lognormal location parameter, whose variance is `sigma^2 / n`, as given in Johnson, N.L., Kotz, S., and Balakrishnan, N., Continuous Univariate Distributions, volume 1, 2nd edition, Wiley 1994, ISBN 978-0-471-58495-7, lognormal chapter                                                                                                                                                         | Inject a known multiplicative offset in {0.85, 0.9, 1.1, 1.25} into a reality-side service-time parameter. Over 400 seeded repetitions at `min_observations`, the standardised recovery error has mean 0 and variance 1 within the chi-square interval for 399 degrees of freedom                                                                            | The estimator's own standard error is the noise floor and is computed rather than assumed. Falsified when the standardised error's variance falls outside the chi-square interval, or when its mean differs from 0 by more than three standard errors                                                            |
| VAL-GATE-SURR-01     | Papadopoulos, H., Proedrou, K., Vovk, V., and Gammerman, A. (2002), "Inductive Confidence Machines for Regression", Machine Learning: ECML 2002, 345-356, DOI 10.1007/3-540-36755-1_29, with the finite-sample statement in Lei, J., G'Sell, M., Rinaldo, A., Tibshirani, R.J., and Wasserman, L. (2018), "Distribution-Free Predictive Inference for Regression", Journal of the American Statistical Association 113(523), 1094-1111, DOI 10.1080/01621459.2017.1307116 | On a held-out batch of `benchmark.surrogate_holdout_n` configurations, the empirical coverage of the 95 percent split-conformal interval lies inside the exact binomial acceptance region for the published bound, which is at least 0.95 and at most 0.95 + 1/(n_calib + 1)                                                                                 | The region is derived from the binomial at 0.001 per tail and the fixture prints it. Falsified when coverage lands outside, which means either the calibration split leaks or the interval construction is wrong                                                                                                 |
| VAL-GATE-SURR-02     | The committed baseline model, compared by the paired test of the LSS engine                                                                                                                                                                                                                                                                                                                                                                                               | Mean absolute error, mean absolute percentage error, and the 50th, 90th, and 99th absolute-error percentiles per target are published, and CI fails when any target regresses against the committed baseline under a paired test at alpha 0.05                                                                                                               | The paired test's own power is reported. Falsified by a significant regression on any target. No absolute error threshold is asserted, because no external reference fixes one; see 9 Q17                                                                                                                        |
| VAL-GATE-RL-01       | Wilcoxon, F. (1945), "Individual Comparisons by Ranking Methods", Biometrics Bulletin 1(6), 80, DOI 10.2307/3001968, and Hodges, J.L. and Lehmann, E.L. (1963), "Estimates of Location Based on Rank Tests", The Annals of Mathematical Statistics 34(2), 598-611, DOI 10.1214/aoms/1177704172                                                                                                                                                                            | The signed-rank statistic and the Hodges-Lehmann estimator computed by the LSS engine reproduce the worked examples in those two papers exactly. The benchmark then runs on `benchmark.n_seeds` held-out seeds under common random numbers, and the table is written with Holm-adjusted p-values. No assertion is made about which policy wins               | The statistics reproduction is deterministic. The benchmark half is a publication gate: falsified when the table is missing, when it is stale against the policy-weights hash or the code version, or when the seed sets intersect                                                                               |
| VAL-GATE-DET-01      | None, and none is possible: this compares two runs of one build                                                                                                                                                                                                                                                                                                                                                                                                           | Every tier-3 scenario run twice in-process and once in a fresh process yields an identical `state_hash`, and `replay --exact` on each recorded run reproduces its hash. Exact equality, so no tolerance                                                                                                                                                      | No noise floor: the assertion is bitwise. Falsified by any hash mismatch, including one caused by `PYTHONHASHSEED` varying between the two jobs                                                                                                                                                                  |
| VAL-GATE-DET-02      | None, for the same reason                                                                                                                                                                                                                                                                                                                                                                                                                                                 | Across the C10 platform matrix, the business-event sequence is identical and continuous fields agree within the tolerance the gate itself measures and reports. The reported figure is the observed maximum divergence, not a number chosen in advance                                                                                                       | The measured divergence is the noise floor and the output. Falsified when the business-event sequence differs at all, and flagged for investigation when the continuous divergence exceeds the tolerance recorded at the previous release, with the message naming which of the two explanations applies         |

### 7.5 Notes on the gates that are easiest to get wrong

VAL-GATE-QUEUE-02 asserts interval coverage, not point accuracy, and the two are split into a and b
because they fail for different reasons. A simulation that reports a correct mean with a wrong
interval is more dangerous than one that is visibly off, because the hypothesis tests in
`compare_scenarios` inherit the interval machinery. Coverage is the gate protecting every downstream
statistical claim in this section.

The acceptance region matters as much as the statistic. A gate that demands at least 93 covering
intervals out of 100 fails about 12.8 percent of the time under a perfectly correct build, because
the lower tail of Binomial(100, 0.95) is that heavy. Since C1 fixes the seeds, a failure then
invites re-rolling the seed set, which is p-hacking with extra steps. The region [365, 392] over 400
repetitions is derived from the exact binomial at 0.001 per tail, and the derivation is printed by
the fixture so a reader can check it rather than trust it.

VAL-GATE-ASRS-01 needs randomised storage, which is not the policy the slotting layer uses, so the
gate runs against an ASRS configured with `storage_policy: random`. A separate test asserts that
switching to `class_based` improves expected cycle time, which is the direction the literature
predicts but not a closed form this section can assert a value against. Section 9 Q6 records the
tension.

VAL-GATE-CONG-01 checks the implementation of a published relation against that relation's own
published numbers. It does not claim that warehouse AMR traffic obeys 1935 highway parameters, and
no gate here claims that `congestion_k` or `min_speed_ratio` is right for an AMR fleet. Section 9
Q14 records what would settle those two, and the absence of a gate for them is the honest state
rather than an oversight.

### 7.6 E9 tests, the optimisation engine

| Test                                     | Asserts                                                                                                    | Fails when                                                    |
| ---------------------------------------- | ---------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------- |
| `test_study_replay_reproduces_trials`    | `run_study --replay <study_id>` re-evaluates the recorded trial sequence exactly                           | Any trial's parameters differ from the manifest               |
| `test_parallel_study_is_marked`          | A parallel study records `execution: "parallel"` and is refused as a source for a published number         | A parallel study's result reaches a published table           |
| `test_infeasible_trials_reach_sampler`   | A budget-violating trial is recorded with its constraint value rather than dropped                         | The trial count in the study is lower than `n_trials`         |
| `test_pareto_front_becomes_scenario_set` | Every point on the front converts to a valid `Scenario` that passes patch validation                       | Any front point produces an invalid facility document         |

### 7.7 E11 tests, observation parity and the benchmark

`test_observation_is_a_pure_function_of_state_view` builds an observation twice from one
`TwinSnapshot` and asserts byte equality, then mutates a field that `StateView` denies and asserts
the observation does not change. `test_future_fault_does_not_leak` injects a fault scheduled after
the current instant and asserts the observation is unchanged, which is the specific leak an
RL environment wired to the model rather than to `StateView` would have.
`test_rule_based_policies_see_the_same_fields` runs each shipped policy through an instrumented
`StateView` and asserts the read set of the learned policy is a subset of the union of the read sets
of the rule-based ones. `test_action_mask_removes_every_infeasible_pair` enumerates infeasible pairs
from the model state and asserts each is masked. INV-RL-01 in 7.2 carries the property-based form.

The claim that the benchmark is honest rests on those four tests plus the disjoint seed sets, and
without them it is a sentence in a README. That is why 2.1 points here.

### 7.8 E12 tests, yard and dock scheduling

| Test                                        | Asserts                                                                                                      | Fails when                                                        |
| ------------------------------------------- | ------------------------------------------------------------------------------------------------------------ | ----------------------------------------------------------------- |
| `test_solver_settings_are_enforced`         | A solve with `num_search_workers` other than 1, or with no deterministic budget, refuses to hand over a plan | A plan reaches the twin under non-deterministic settings          |
| `test_same_instance_same_plan`              | One instance solved twice in two processes gives an identical `YardPlan` serialisation                       | Any field differs, including `branches_used`                      |
| `test_wall_clock_cap_raises`                | Exceeding `yard.max_solve_wall_s` raises rather than returning an incumbent                                  | A plan is returned past the cap                                   |
| `test_labour_provider_swap_changes_nothing` | The same profile supplied by `CalendarLabourProfile` and by a roster provider gives the same plan            | The plan differs when the values are identical                    |
| `test_crossdock_weight_requires_links`      | A non-zero `w_missed_crossdock` with empty `crossdock_links` fails config validation                         | The load succeeds                                                 |

### 7.9 E28 tests, the surrogate

`test_out_of_domain_returns_no_prediction` covers INV-SURR-01 at the unit level.
`test_unconfirmed_number_carries_the_flag` asserts that every surrogate value crossing the API
boundary carries `surrogate_estimate: true` and an interval, and that the grounding checker rejects
a sentence carrying such a number without the flag. `test_encoder_version_is_stamped` asserts a
prediction made under a different encoder version is not comparable and is refused rather than
silently mixed into a validation report. `test_promotion_requires_a_paired_win_on_every_target`
asserts that a challenger beating the incumbent on three of seven targets is not promoted.

### 7.10 Runtime budgets

Applying D-13, a budget is an assertion rather than a hope. Each tier declares an allocation, each
fixture records its measured per-repetition cost on the pinned runner into
`artifacts/test-budgets.json`, and `test_tier_budgets_are_satisfiable` multiplies the recorded cost
by the configured repetition count and fails when the product exceeds the allocation. A scenario
that grows past its budget then fails as a defect with a message naming the fixture, rather than as
a job timeout that reads as flakiness.

| Tier                | Allocation | Largest single consumer                                    | How it is held inside the allocation                                                        |
| ------------------- | ---------- | ---------------------------------------------------------- | ------------------------------------------------------------------------------------------- |
| 1 and 2             | 90 s       | The property suite's generated facilities                  | Horizons are capped by the Hypothesis strategy, not only by the config validator            |
| 3                   | 10 min     | SCN-E2E-01 across three profiles                           | 8 simulated hours per profile, and the golden diff is on metrics rather than on every event |
| 4                   | 20 min     | VAL-GATE-QUEUE-02's 400 coverage repetitions               | Coverage runs at one offered load; point accuracy runs at three with 30 replications each   |

Two rules keep the paced-clock and speed-multiplier tests inside the tier-1 allocation. Paced-clock
behaviour is proved on a short scenario of about 60 simulated seconds rather than on a simulated
day, because the property under test is the ratio between sim time and wall time and a longer run
adds nothing to it. Property tests over the speed multiplier clamp the lower bound in the Hypothesis
strategy itself, so a generated multiplier can never produce a worst case longer than the
allocation. Putting the clamp only in the config validator lets the generator produce a run the
validator would have rejected, which is how a property suite acquires a 29-minute test inside a
6-minute job.

---

## 8. Phase placement

Phase names follow the source's constraints paragraph, with the agreed Phase 0 and the agreed
pull-forwards. Nothing here is cut, marked optional, or deferred. Where an item lands later than
another, the dependency reason is in the third column.

| Phase                          | Pieces landing                                                                                                                                                                                                                                                                                                                                                                                                       | Why here                                                                                                                                                                                                                                                                              |
| ------------------------------ | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| P0                             | The six new subject domains registered in `schemas/registry.yaml`; the `twinflow.twin.activity_*` payloads; `facility.yaml` schema v0 with the `x-calibratable` and `x-patchable` annotations; `DeterministicEnv` and the tie-break of 5.2; `EventTape` and the hashed-field allowlist; `exogenous_boundary` and the audit-chain fields as declared shapes; package skeletons for all eight bricks with CI wiring    | These are the contracts 5.2, 5.13, 5.17, and 7 depend on. Adding an envelope field, the boundary field, or the calibratable annotation later is a MAJOR bump on every subject and a rewrite of every recorded run and golden file                                                     |
| P1                             | Walking skeleton twin: one dock door, one station, one scan point, pallet flow to putaway, tape writing, `WindowMetrics` for throughput and one utilisation figure, `StateView`                                                                                                                                                                                                                                      | The source's Phase 1 requirement, end to end before anything widens                                                                                                                                                                                                                   |
| P2                             | Component 1 in full: the multi-station flow graph, distributions, failures, buffers and blocking, takt, both cycle-time definitions, the WIP integral, utilisation, both OEE conventions, six big losses, all three bottleneck detectors, `ValueStreamSummary`, warm-up and batch means. VAL-GATE-QUEUE-01 to 05, VAL-GATE-OEE-01, VAL-GATE-VSM-01, VAL-GATE-WARMUP-01, VAL-GATE-DET-01 and 02                       | Component 1 in full, and the LSS engine, also at P2, needs real metric streams to judge. The queueing gates land here because they validate the simulation core everything else stands on                                                                                             |
| P2b, immediately after P2      | E4 replay and the counterfactual engine; the minimal what-if engine of `run` and `compare` without the LSS verdict; `ExogenousTrace` and `ExogenousBoundary`; the ranking buckets of 5.12; VAL-GATE-CRN-01                                                                                                                                                                                                           | Pulled forward from P6 because E1's hosted replay demo is pulled to just after P2 and needs the replay path, and because `compare_scenarios` is the agent's headline demo. The LSS verdict is wired in as soon as P2's engine exists, completing `RankedOption`                       |
| P3                             | Component 6 calibration and the divergence monitor, with VAL-GATE-SYNC-01 and 02                                                                                                                                                                                                                                                                                                                                     | Needs telemetry breadth from P3's sensor catalog and the findings stream from P2. The digital-twin claim in the README depends on this landing before the repository is presented as a twin. The known false positive of 5.15 is stated from the day this ships, not discovered at P4 |
| P3b                            | Component 1b in full: the AMR fleet with dispatch, traffic, deadlock, battery and charging; the palletiser cell with jams; the ASRS with crane scheduling; conveyor and sortation with divert logic; slotting; the three named automation what-ifs. VAL-GATE-ASRS-01, VAL-GATE-SLOT-01, 01b, 02 and 03, VAL-GATE-DEADLOCK-01, VAL-GATE-CONG-01                                                                       | The source's stated Phase 3b. Three consequences for other sections are in the list below                                                                                                                                                                                             |
| P3b+                           | The slotting affinity term, fed by the synthetic order-line generator of 9 Q4 when that resolution is taken; otherwise the affinity weight stays zero until P3e and the config validator holds it there                                                                                                                                                                                                              | Affinity needs order lines, which arrive with outbound at P3e. Sequencing rather than cutting: the term exists from P3b and turns on when its data source exists                                                                                                                      |
| Before P3g                     | E12 base model: the interval, no-overlap, cumulative-labour, and door-capability constraints, the deterministic solver settings of 5.20, `plan_realisability`, and VAL-GATE-SCHED-01                                                                                                                                                                                                                                 | Moved ahead of its stated P6 position because the source says cross-docking at Phase 3g makes E12's yard optimisation load-bearing. A dependency of later work moves ahead of its dependent                                                                                           |
| P3g                            | E12 cross-dock extension: `crossdock_links`, the precedence and staging-dwell constraints, and the missed-connection objective term. SCN-E2E-16                                                                                                                                                                                                                                                                      | The extension models a flow that does not exist until 6a5 lands at P3g, so it cannot precede it. Splitting E12 in two is what removes the mutual dependency the single-piece placement created                                                                                        |
| P3c to P3i                     | No new pieces owned here, but three consumers appear: the VSM renderer consumes `ValueStreamSummary` at P3c, the forecast drives arrivals when `arrivals.mode: forecast_driven` at P3d, and the upstream factory at P3i instantiates a second `TwinModel` from the same package                                                                                                                                      | The twin core must be stable before these consume it, which it is from P2                                                                                                                                                                                                             |
| P4                             | Sortation identity resolution cross-checked against the CV throughput counter; the real late-arrival window on the divergence monitor, keyed on the store-and-forward replay marker, replacing the interim `sync.suppress_after_gap_s`. SCN-E2E-17's second direction                                                                                                                                                | Both need component 4 and 6c to exist                                                                                                                                                                                                                                                 |
| P5                             | Golden-file coverage across all three A2 profiles; the demo scenario `second_portal_dock3`; the investment-roadmap table rendering                                                                                                                                                                                                                                                                                   | The source's polish phase                                                                                                                                                                                                                                                             |
| P6, in the order below         | E5 autonomy tiers, guardrails, audit chain, and rollback, whose write-path schema was frozen at P0; E9 the Optuna engine with VAL-GATE-OPT-01; E25 the scenario corpora; E11 the learned dispatcher with VAL-GATE-RL-01; E28 the surrogate with VAL-GATE-SURR-01 and 02                                                                                                                                              | E5 needs the mature agent and the sync write path. E9 needs the what-if engine and a stable KPI vector. E11 needs E9's benchmark plumbing, the automation layer, and E25's corpora for its curriculum, so E25 comes before it. E28 needs E9's trials plus E25 as its training corpus  |

Four sequencing consequences change other sections' phases. Each is a reordering the source's own
text implies, and none is a cut.

1. E6, the operator model, and E7, the energy KPIs, move to P3b. The source requires the 1b what-ifs
   to report energy and operator-impact deltas, and a what-if that reports null for two of its four
   required outputs has not met the requirement.
2. The NIOSH scorer inside 6a10 moves to P3b. VAL-GATE-SLOT-03 is scheduled at P3b and lives in
   `twinflow-ergonomics`, which is 6a10 and which the source's constraints paragraph places after
   Phase 3i. Since E6 is already moving to P3b, pulling the scorer with it is cheap. The rest of
   6a10, which is the shift-level strain accumulation and the safety findings, stays where the
   source puts it.
3. E12 splits, with the base model before P3g and the cross-dock extension at P3g. The single-piece
   placement made E12 and 6a5 mutually dependent, which no order can satisfy.
4. E25 moves ahead of E11 within P6. The source's stated E order puts E25 after E11, and E11's
   curriculum reads E25's corpora, so the stated order cannot be built in that order.

One dependency does not move a phase, because a shipped null implementation removes it. E23's labour
roster is a P6 item and E12 needs a labour profile before P3g, so `LabourProfileProvider` ships with
`CalendarLabourProfile` reading `calendars.yaml`. E23 later registers a provider reading
`twinflow.workforce.roster_published` and the solver is untouched. This is the same pattern
`OperatorProvider` uses in 3.3, and it is the pattern to reach for before proposing a reordering.

---

## 9. Open questions

These are genuine ambiguities. Each carries the proposal an implementer follows absent a decision,
and the ambiguity is not hidden behind the proposal. Questions Q14 through Q17 exist because a
number in this section has no external published reference, and D-11 says such a number is recorded
here rather than dressed as a passing gate.

**Q1. Which OEE convention is authoritative?** The source says the twin computes OEE without naming
a convention. Nakajima's TPM definition and the SEMI E10 and E79 equipment-state definitions treat
planned downtime, no-demand time, and engineering time differently, and they give different numbers
from one log. Line-level OEE is a further ambiguity: OEE is defined for equipment, and rolling it up
to a line needs a stated rule, either bottleneck equipment, a weighted average, or true line OEE
from line-level counts. Proposal: build both conventions, make `metrics.oee_convention` mandatory
with no default, report line OEE from the bottleneck resource's counts, and label every OEE figure
with its convention. Decision needed on which convention the README headline uses.

**Q2. Throughput gained per dollar of which dollar?** The source says per dollar of assumed cost.
Capex alone, first-year total cost, annualised total cost of ownership, and net present value give
different rankings, and a reader who knows finance will ask. Proposal: annualised total cost of
ownership through the capital recovery factor with an explicit discount rate in `costs.yaml`, with
payback years and raw capex in adjacent columns so a reader can re-rank by their preferred measure.
Net present value and internal rate of return come from the financial twin at 6a17 and E22, and the
table gains those columns then. Decision needed on the default discount rate for the shipped
profiles.

**Q3. Which bottleneck definition is the bottleneck?** The three detectors can disagree, and a
shifting bottleneck has no single answer. Proposal: publish all three plus the shifting timeline,
take the headline from the active-period method of Roser, Nakano, and Tanaka, and raise the
disagreement as an informational finding. Decision needed on which one the agent's `get_bottleneck`
tool returns as its primary answer, since the agent must give one number.

**Q4. Slotting affinity has no data source until Phase 3e.** Component 1b puts slotting at Phase 3b
and requires an affinity term, but affinity comes from order-line co-occurrence, and order lines
arrive with outbound shipping at 6a3, Phase 3e, and e-commerce at 6a6, Phase 3g. Two resolutions are
consistent with nothing being cut. The first ships a synthetic order-line generator at Phase 3b
whose co-occurrence structure is declared config, which makes the affinity term real from 3b and is
later replaced by the true order stream. The second ships the term disabled at 3b with the validator
holding `w_affinity` at zero until an affinity source exists, and turns it on at 3e. Proposal: the
first, because it lets the slotting gates and the re-slot payback demo run at 3b, and because the
generator is reusable as an E25 synthetic data product. Decision needed.

**Q5. How much may the twin know about reality?** For calibration, divergence, and measurement
system analysis to mean anything, the twin must not read the generator's true parameters. The design
puts true physics in `catalog/sensors.yaml` and `ground_truth/reality_offsets.yaml`, forbids
`twinflow-sync` and `twinflow-twin` from importing either, and holds the rule with an import lint
and a runtime capability check. Open: how large the shipped reality offsets are, and whether
they drift over the demo shift, which makes divergence a live event a viewer can watch, or
stay static, which makes the demo reproducible. Proposal: a small static offset plus one scheduled
drift event at a known sim time in the demo profile, so the replay viewer shows the divergence
finding appear. Decision needed on magnitude.

**Q6. The ASRS storage policy conflicts between the gate and the slotting layer.** The Bozer and
White travel-time model assumes randomised storage; the slotting layer implies dedicated or
class-based storage. Proposal: run VAL-GATE-ASRS-01 against a `storage_policy: random` fixture, and
separately assert that class-based storage improves expected cycle time relative to random, which is
the direction the literature predicts but not a closed form this section can assert a value against.
Open: whether a published closed form for class-based AS/RS travel time becomes a second gate,
and which one.

**Q7. Which AMR traffic protocol?** Time-window reservations, zone-based blocking, and
conflict-based search have different deadlock guarantees, different determinism properties under
replanning, and different realism. Reservations give a clean acyclicity proof and deterministic
replay. Conflict-based search gives better throughput at higher compute cost and is harder to make
deterministic. Proposal: reservations for the shipped implementation, with the `RoutingPolicy`
protocol of 1.3 exported so a conflict-based-search implementation can be added as a benchmark
competitor alongside E11 without a fork. Decision needed on whether that competitor is a committed
roadmap item in its own right.

**Q8. Parallel Optuna trials break exact determinism.** Trial completion order feeds the sampler, so
a parallel study is not byte-reproducible. Proposal: record the trial-number to parameters mapping
in the study manifest, support `--replay <study_id>`, run any study behind a published number in
sequential mode, and record the mode in `twinflow.optimize.study_completed`. Decision needed on
whether C1's determinism claim states sequential studies only in the README, or whether a
deterministic parallel scheme with fixed batch synchronisation becomes a committed roadmap item.

**Q9. Does a counterfactual replay re-simulate the device fleet?** E4's counterfactual re-simulates
the facility, but the telemetry stream comes from the device fleet, whose sensors attach to twin
subsystems. Replaying with a patch that adds a scan portal implies a device that did not exist in
the source run. Proposal: the counterfactual re-runs the device fleet in simulation mode inside the
forked instance, with device faults taken from the recorded exogenous trace where the device existed
and drawn fresh where it did not, and `twinflow.scenario.replay_completed` records which devices
were synthesised. Decision needed on whether the counterfactual's telemetry is written to the
historian as a separate scenario-tagged stream or discarded after metric extraction, which is a
storage cost against inspectability.

**Q10. Naming the surrogate if the tree model wins.** E28 is called a neural twin surrogate, but the
repository's own discipline is baseline first and promotion only on measured improvement. When
LightGBM beats the MLP, the honest label is a learned surrogate and the roadmap item's name no
longer matches its implementation. Proposal: keep the E28 identifier, title the deliverable the
learned twin surrogate, and state in the README which model family won and by how much. Decision
needed on whether the roadmap milestone text is edited to match.

**Q11. Where does the cost catalog live?** `costs.yaml` is proposed here because
`compare_scenarios` needs it from Phase 2b, but the finance layer at 6a17 will own a chart of
accounts and standard costs, and two sources of truth for a labour rate is the defect this
repository exists to criticise. Proposal: `costs.yaml` is the single source from 2b onwards, and
when 6a17 lands it reads `costs.yaml` rather than duplicating it, with the general ledger's standard
costs derived from it. Decision needed on ownership at the point 6a17 lands.

**Q12. Is L3 autonomy ever turned on in the shipped demo?** L3 auto-applies changes to the
running configuration. In a public demo repository that is a strong claim and a possible foot-gun
for anyone adapting the code toward a real line. Proposal: shipped profiles default to `L1_ADVISE`,
`l3_whitelist` stays empty unless `autonomy.acknowledge_l3: true` is set, and the demo shows L3 in a
clearly labelled sandbox scenario with a guardrail trip and a rollback, which is a better story than
L3 quietly working. Decision needed on whether the recorded shift behind E1's replay viewer includes
an L3 episode.

**Q13. Where do what-if worker processes run at the enterprise tier?** Subsection 5.3 forks what-ifs
into a worker pool. In production mode on a Purdue-segmented deployment the twin runs in the DMZ and
the agent in IT, so the question is which segment runs the workers and whether they may read the
historian directly. Proposal: workers run in the IT segment against a read replica of the historian
and never touch the OT segment, which keeps the segmentation claim true. Decision needed from the
deployment section, since it affects the Helm chart and the compose topology.

**Q14. The AMR congestion parameters have no published reference.** The form of the relation in 5.6
is Greenshields' linear speed-density relation and VAL-GATE-CONG-01 checks the implementation
against his published numbers. The values `automation.traffic.congestion_k` at 0.35 and
`automation.traffic.min_speed_ratio` at 0.25 are engineering judgment for a warehouse AMR fleet, and
no gate claims them. Two things would settle them, and both are real work rather than a literature
search. The first is a published AGV or AMR speed-density study with stated vehicle dimensions and
aisle widths, entered as a second gate configured to that study's fixture. The second is a
hardware-in-the-loop measurement under E47 on a real vehicle in a measured aisle, which produces a
parameter this repository can attribute to its own published method. Until one of those exists, the
values ship labelled as judgment, exactly as section G.3 of
`docs/design/variability-and-faults.md` labels the whole catalog. Falsification of the current
choice: a measured speed-density curve whose fitted slope differs from `congestion_k` by more than
the measurement's own confidence interval.

**Q15. The AMR charging curve has no published reference for this vehicle class.** The two-phase
constant-power-then-taper shape in 5.6, the value of
`automation.amr_fleet.charging.cc_cutoff_soc`, and the taper's linearity are engineering judgment.
INV-AMR-02 checks that the energy ledger closes, which a wrong curve satisfies perfectly, so the
invariant is not evidence for the curve. What would settle it is a published charge-profile
measurement for an industrial lithium-iron-phosphate pack of the modelled capacity, with the state
of charge at which constant current ends stated, entered as a gate configured to that measurement.
Proposal until then: ship the curve, label it judgment in the config comment, and publish
`charge_phase_split_s` on every completion event so a reader can see the modelled shape rather than
infer it. Decision needed on whether the repository commits to sourcing one such measurement before
the E47 hardware milestone.

**Q16. The palletiser jam rate and clear-time distribution have no published reference.**
`variability.palletiser.jam_rate_baseline` and `variability.palletiser.jam_clear` come from the
distribution catalog and are judgment values there. Section G.3 of
`docs/design/variability-and-faults.md` records the status for the whole catalog and lists the
options: ship judgment values labelled as such, fit what can be fitted to public datasets and cite
them, or carry a `source:` field per parameter taking `judgment`, `public_dataset`, or `textbook`.
This section adds one consequence specific to it: SCN-E2E-04 asserts that the bottleneck moves off
the palletiser when a second cell is added, and that assertion holds for any jam rate in a wide
band, so the scenario is not evidence for the value either. Decision needed at the catalog level,
not here.

**Q17. No external reference fixes an acceptable surrogate decision-agreement level.** A threshold
on top-1 decision agreement or on Kendall tau would need a published basis, and none exists for a
learned surrogate of a discrete-event warehouse model. A threshold picked here would also leave only
two responses when a surrogate lands below it: lowering the bar, which is a silent cut, or blocking
the milestone, which is a cut of a different kind. The gate is split in two: coverage is checked against the published finite-sample
conformal bound, and the decision measures are published and gated only against the committed
baseline. Proposal: publish the measured agreement and tau, and let them set the operating point
rather than the pass mark, by choosing `confirm_top_k` in `screen_and_confirm` from the measured
agreement so that a weaker surrogate confirms more candidates on the full sim. Decision needed on
whether the README states a target for agreement at all, given that any target this section invents
would be the defect it just removed.

**Q18. Two gates depend on values in books this section has not transcribed.** VAL-GATE-OEE-01 and
VAL-GATE-VSM-01 name Nakajima 1988 and Rother and Shook 1999 and assert reproduction of their
worked examples. Both are valid external published references, and neither has been transcribed into
a fixture yet, so this document states the gates operationally and does not print numbers it has not
read. The fixtures record the edition and page locator they transcribe from, and a fixture with no
locator fails its gate rather than passing on an untraceable number. Decision needed on which
editions the repository standardises on, since page locators differ between printings.

**Q19. The Rust device agent's stochastic streams and this section's boundary.** Doctrine D-06 gives
the Rust agent an RNG contract derived from the run seed and its device id by the same
name-addressed derivation the Python side uses, and section G.2 of
`docs/design/variability-and-faults.md` records that PCG64 parity between the two languages is not
something to assume. This section consumes the agent's telemetry at scan points and at automation
resources through 4.8, so a parity failure shows up here as a divergence finding rather than as a
determinism failure, which would send an investigator to the wrong subsystem. Proposal: until the
conformance test D-06 requires is green, `twinflow.twin.pallet_scanned` records
`read_source: "device-agent"` for reads originating in the Rust agent, so a divergence investigation
can separate the two populations in one query. Decision needed from the fleet section, which owns
the agent.
