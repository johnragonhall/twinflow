---
title: Planning, suppliers, outbound, returns, cross-dock, e-commerce, transport, and multi-echelon inventory
description: The implementation contract for deciding what arrives, what leaves, when, from where, at what cost, and how each of those decisions is measured.
topic_type: reference
audience: contributors
---

# Planning, suppliers, outbound, returns, cross-dock, e-commerce, transport, and multi-echelon inventory

Status: design spec, implementation contract. Written to be built with TDD.
Prose rule for this file: plain present tense, no em-dashes, no marketing adjectives.

Binding doctrine: `docs/design/DOCTRINE.md`. Where this section and a doctrine ruling disagree, the ruling wins and this section changes. Every place a ruling is applied cites its id.

Settled stochastic and fault model: `docs/design/variability-and-faults.md`. Every distribution family, parameter default, config key, and RNG stream name used below is defined there. This section names them and never redefines them.

Evidence rule, from doctrine D-11. A claim taken from a primary text this section retrieved ships
plainly. A claim taken from one secondary source ships with the source named in the sentence that
makes it. An unverified claim never ships as a fact: it is cut or it becomes an open question in
section 9. Where a source blocked retrieval, the sentence that depends on it says so.

---

## 1. Scope

This section is the implementation contract for the supply chain planning and flow layers of twinflow. It decides what arrives, what leaves, when, from where, and at what cost, and it measures whether each decision held.

### 1.1 Numbered requirements this section implements

Every requirement below is built here. Six of them have a part owned by another section. Each
such part is named in 1.2 with the interface across the seam: 6a2's recall drill (6a11), 6a5's
dock schedule optimizer (E12), 6a6's AMR fleet (1b), E13's broker and bridge (the IoT and UNS
section), E15's alarm rationalization (`twinflow-lss`), and E16's finite-capacity scheduler
(6a9). No requirement is listed here when part of it has no owner anywhere.

| Req | Title                                                                                                                                                                                                                                                                    | Where covered here                                               |
|-----|--------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|------------------------------------------------------------------|
| 6a  | Planning layer: demand forecasting with honest backtests, forecast bias on a control chart, inventory optimization, safety stock and reorder points from twin-measured lead times, ABC/XYZ segmentation, forecast propagating into truck scheduling and floor congestion | 2.1, 2.2, 2.3, 3.1, 3.2, 3.3, 5.1, 5.2, 5.3, 5.19, 7.3, 7.4, 7.5 |
| 6a2 | Supplier network: reliability profiles, OTIF / lead-time-variability / defect-PPM scorecards, disruption what-ifs, inbound quality events through lot genealogy, backward traceback and forward blast radius                                                             | 2.4, 3.4, 5.4, 7.3, 7.5                                          |
| 6a3 | Outbound shipping: wave versus waveless, carrier assignment, trailer cubing, shared inbound/outbound dock contention, order cycle time and fill rate, the carrier-cutoff shift what-if                                                                                   | 2.5, 3.5, 5.5, 5.6, 5.19, 7.3, 7.5                               |
| 6a4 | Returns and reverse logistics: reason codes, triage and disposition, reverse P&L, Pareto, restock feeding planning                                                                                                                                                       | 2.7, 3.7, 5.8, 7.3, 7.5                                          |
| 6a5 | Cross-docking: flow-versus-store decision engine, staging dwell, dock-to-dock time, missed-connection rate                                                                                                                                                               | 2.6, 3.6, 5.7, 7.3, 7.5                                          |
| 6a6 | E-commerce fulfillment: batch/zone/cluster each-picking, goods-to-person AMR what-if, cartonisation, parcel rate shopping, peak-day chaos, parcel-versus-pallet interference, per-channel unit economics                                                                 | 2.5, 3.5, 5.5, 5.6, 5.9, 7.3, 7.5                                |
| 6a7 | Transportation network: TL/LTL/parcel mode selection, transit distributions with disruptions, carrier contracts and a moving spot market, load consolidation, freight spend analytics                                                                                    | 2.8, 3.8, 5.10, 7.3, 7.5                                         |
| 6a8 | Multi-echelon inventory optimization: base-stock per echelon, guaranteed-service-time frontier validated against the twin, budget-constrained placement, explicit risk pooling, disruption propagation across echelons                                                   | 2.3, 3.3, 5.3, 5.13, 5.19, 7.3, 7.5                              |
| E13 | Multi-site scale-out with broker-to-broker UNS bridging and federated learning                                                                                                                                                                                           | 2.11, 3.11, 5.14, 7.3, 7.5                                       |
| E15 | S&OE weekly execution tick with exception queues and bounded corrective actions measured against the untouched plan                                                                                                                                                      | 2.10, 3.10, 5.12, 7.3, 7.5                                       |
| E16 | ATP/CTP order promising and promise reliability                                                                                                                                                                                                                          | 2.9, 3.9, 5.11, 7.3, 7.5                                         |
| E19 | N-tier supplier illumination, hidden shared tier-2 concentration, ROI of mapping                                                                                                                                                                                         | 2.4, 3.4, 5.4, 7.3, 7.5                                          |
| E20 | Reverse stress testing: minimal breaking sets, time-to-survive, time-to-recover                                                                                                                                                                                          | 2.12, 3.12, 5.15, 7.3, 7.5                                       |
| E40 | Weather as one shared correlated exogenous driver across demand, transit, yard, energy, slip risk                                                                                                                                                                        | 2.13, 3.13, 5.16, 7.3, 7.5                                       |
| E41 | VMI/consignment, value-added services, postponement                                                                                                                                                                                                                      | 2.3, 2.5, 3.3, 3.5, 5.17, 7.3, 7.5                               |
| E42 | Strategic network design handing winning designs to the operational twin                                                                                                                                                                                                 | 2.11, 3.11, 5.18, 7.3, 7.5                                       |

### 1.2 Requirements touched at a declared seam, owned elsewhere

This section publishes to or consumes from the following, and names the exact interface in each case. It does not build them.

- Component 5 (LSS engine): every control chart, Pareto, capability index, and hypothesis test in this section is a call into `twinflow-lss`. This section owns the data and its declared statistical type; the engine owns chart selection and rule evaluation. The engine also owns alarm rationalization, which the S&OE exception queue calls in 5.12 step 4. Section 8.4 states what the queue does at P3e when that call is not yet available.
- Component 1 / 1b (twin, automation, AMR fleet, slotting): docks, labor, staging positions, AMRs, and conveyors are twin resources, held as SimPy resources inside the twin package. This section requests them and never owns them. `DockBroker` (3.5, 5.5) is a policy layer above the twin's door resources, not a second owner of those doors.
- Component 2 / 2b (sensor catalog): three behaviors here read sensor streams the catalog owns. Cargo shock, tilt, and temperature sensors on transport legs raise the `DAMAGED_IN_TRANSIT` reason-code uplift (3.7, 5.8). Ambient temperature, humidity, and dew-point sensors derive their readings from the weather state (5.16). Dock door sensors report door occupancy, and disagreement between that stream and `dock.allocation.v1` is an audit finding (4.5).
- Component 6b (ERP stub, CMMS): the ERP stub is the publisher of record for `order.created.v1` and `supplier.po.issued.v1` in production mode, re-publishing what the packages here compute. See open question 9.1.
- Component 6a9 (upstream production): supplies the finite-capacity scheduler behind CTP. Interface `CapacityPromiseProvider`.
- Component 6a11 (QMS and compliance): runs the mock recall drill on the forward blast-radius query this section defines in 5.4 and asserts in INV-GEN-2. This section owns the query, its result type, and its correctness gate; 6a11 owns the drill, the quarantine workflow, and the recall-readiness report.
- Component 6a12 (order management), 6a13 (procurement), 6a16 (S&OP), 6a17 (finance): consume this section's events. Order lifecycle, PO approval workflow, S&OP consensus, and the GL live there.
- Component 7 and E26 (the agent and the accuracy stack): the agent is the reader of every what-if answer named in 6a, 6a3, 6a6, 6a8, E13, and E15. Two rules bind this section. E26(a) means the agent never computes a number in tokens, so every KPI named below is emitted as a field on an event the agent can query, never left as something a reader derives. E26(b) means the governed semantic metrics layer holds the single definition of `fill_rate`, `otif`, `days_of_supply`, and `landed_cost`. This section emits the numerator and the denominator of each on the events in section 4, references those definitions, and does not publish a second one. Open question 9.14 records the part of that split that is still unsettled.
- E9 (Optuna optimization engine), E28 (surrogate), E30 (causal), E31 (forecast foundation models), E43 (MLOps): register into this section's arenas and search loops through named protocols.
- E12 (yard and dock scheduling optimization): cross-dock and inbound scheduling call `DockScheduleProvider`. A deterministic baseline provider ships here at P3d; E12 replaces it. See open question 9.4.
- E13 broker and bridge mechanics: the IoT and UNS section owns broker deployment, the site-to-enterprise bridge, the Sparkplug encoding, and the birth and death certificates that ride on it. This section owns the topic policy schema (`BridgeTopicPolicy`), the site registry, the cross-site KPI rollup, and the federated round protocol. The interface is the topic policy document plus `bridge.stats.period.v1`, and 5.14 states the bridging contract this section depends on.
- E14 (tariffs), E17 (carbon), E22 (financial twin), E35 (EPCIS ledger): landed cost, carbon per leg, working capital, and custody events are computed by those layers from this section's events.
- E23 (labor rostering): supplies the roster that replaces the shift-calendar labor plan in `PlanSnapshot.planned_labor_hours` at P6. The `labor_source` field on that snapshot records which source produced the number.

---

## 2. Packages

All packages are members of the `uv` workspace, are independently installable (A1), and follow the monorepo rules from Phase 0: distribution name `twinflow-<brick>`, import path `twinflow.<brick>` via PEP 420 namespace packages, no package imports another package's internals, all cross-package communication is versioned schema'd events from `/schemas` (C3).

Every package here depends on three internal packages that all of them share, plus a declared list of
its own. The shared three:

- `twinflow-kernel`: the `Clock`, `Rng`, `Network`, `EventBus`, `Storage`, and `Inference` ports. No module in this section calls `time.time`, `datetime.now`, `random.*`, `uuid4`, or opens a socket. Lint `TWF-DET-001` and `TWF-RNG-003` fail CI on any of them, and C1's repeated-run hash check backstops both. Doctrine D-08 splits `Network` (MQTT shaped) from `EventBus` (subject-addressed fan-out). Every package in this section publishes to `EventBus` and to nothing else. The four subjects marked UNS-published in section 4 reach MQTT because the IoT and UNS section's bridge subscribes to them on `EventBus` and republishes them on `Network`; no package here holds a `Network` handle, and `test_planning_packages_bind_no_network_port` asserts it.
- `twinflow-schemas`: generated Pydantic models from `/schemas`, plus the event bus client. Under doctrine D-09 this leaf package also owns every shared value type and every structural protocol that would otherwise force a heavy dependency downward, and re-exports it. In this section that is four names: `MeioNetwork`, `Node`, `DockBrokerProtocol`, and `TwinResourceProtocol`.
- `twinflow-lss`: the statistical judge, consumed through its public finding-producing API.

No package in this section imports another package in this section. Every shared name lives in the
leaf schema package, and every run-time coupling travels as a schema'd event on `EventBus`, so a
package installed alone still starts and still runs with that input absent. The CI import-graph test
from doctrine D-09 fails on a cycle, and with the table below it has no edge to find.

| Package                | Declared internal dependencies beyond the shared three | What crosses the seam                                                                                                |
|------------------------|--------------------------------------------------------|----------------------------------------------------------------------------------------------------------------------|
| `twinflow-demand`      | none                                                   | consumes `weather.state.v1` when weather is enabled; installs and runs standalone with the coupling disabled         |
| `twinflow-forecast`    | none                                                   | consumes `demand.signal.published.v1`; usable on any `(unique_id, ds, y)` frame with no twinflow concepts present    |
| `twinflow-inventory`   | none                                                   | consumes `forecast.point.v1`, `leadtime.observed.v1`, `lane.rate.quoted.v1`, `meio.network.published.v1`             |
| `twinflow-supply`      | none                                                   | consumes `replenishment.plan.published.v1`; produces PO, ASN, receipt, and scorecard events                          |
| `twinflow-fulfillment` | none                                                   | requests twin dock, labor, and AMR resources through `TwinResourceProtocol`; consumes `order.created.v1`             |
| `twinflow-crossdock`   | none                                                   | door requests and wait attribution through `DockBrokerProtocol`; the concrete broker is injected, never imported     |
| `twinflow-returns`     | none                                                   | door requests through `DockBrokerProtocol`; the `CausalUpliftRegistry` receives transport and pick uplifts as events |
| `twinflow-transport`   | none                                                   | produces `lane.rate.quoted.v1`, `transport.leg.completed.v1`, `spot.index.v1`                                        |
| `twinflow-promise`     | none                                                   | consumes ATP inputs as events; `CapacityPromiseProvider` is injected                                                 |
| `twinflow-soe`         | none                                                   | consumes plan and actual events; `ActionRegistry` entries register themselves                                        |
| `twinflow-network`     | none                                                   | echelon structure and stage cost through `MeioNetwork`; freight rates arrive as `lane.rate.quoted.v1`                |
| `twinflow-resilience`  | none                                                   | echelon structure for `EchelonPropagation`; disruption knobs are declarative config                                  |
| `twinflow-exogenous`   | none                                                   | produces `weather.state.v1` and `weather.event.v1`                                                                   |

Four names would otherwise have created an import edge, and doctrine D-09 places all four in
`twinflow-schemas` instead.

| Name                   | Needed at import time by         | Why the leaf package owns it                                                  |
|------------------------|----------------------------------|-------------------------------------------------------------------------------|
| `MeioNetwork`          | inventory, network, resilience   | owning it in inventory would push scipy and networkx onto the other two       |
| `Node`                 | inventory, network, resilience   | same edge, same two packages                                                  |
| `DockBrokerProtocol`   | fulfillment, cross-dock, returns | cross-dock and returns receive a concrete broker by injection and import none |
| `TwinResourceProtocol` | fulfillment                      | keeps the fulfillment package free of an import edge to the twin package      |

Two of those names are re-exported where a reader looks for them. The inventory package re-exports
`MeioNetwork` and `Node`, and the fulfillment package re-exports `DockBrokerProtocol`. A re-export is
not a second declaration, and the CI test from D-09 checks that each name is defined in exactly one
package.

`pip install twinflow-forecast` gives a usable forecasting arena with no warehouse in sight. That is the A1 test for each brick below, and doctrine D-10 makes it a test rather than a claim: a CI job installs each package alone into a clean environment, imports it, and runs its unit tier.

Three determinism rules bind every package here, from doctrine D-03, D-04, and D-05.

Iteration order is explicit everywhere (D-03). No field whose iteration order can reach an event
payload, a hash, or a control decision is a Python `set`. Where set semantics are wanted, the field
is a `frozenset` with a mandated sorted serialization, or a tuple with a uniqueness validator. A
`dict` is permitted where insertion order is the meaning, and any `dict` whose keys come from a set,
from a config mapping, or from concurrent inserts is built by inserting its keys in sorted order.
Lint `TWF-RNG-002` fails CI on set iteration inside these packages, and CI runs the determinism
scenario twice under different `PYTHONHASHSEED` values and compares hashes, so a pinned hash seed
cannot hide the defect.

Anything that steers the simulation is bounded deterministically and never by wall time (D-04).
Every solver in this section runs single-threaded with a child seed derived from the run seed and a
deterministic budget: HiGHS with `threads=1`, a fixed `random_seed`, a node limit, and a fixed
relative MIP gap; the branch-and-bound consolidator with a node limit; Optuna with a seeded sampler,
`n_jobs=1`, and a fixed trial count. Every fitting library runs single-threaded, and the kernel pins
`OMP_NUM_THREADS`, `MKL_NUM_THREADS`, `OPENBLAS_NUM_THREADS`, `NUMEXPR_NUM_THREADS`, and
`NUMBA_NUM_THREADS` to 1 at process start for a run marked deterministic. Applying doctrine D-01,
the pinned values are written to the provenance sidecar `manifest.json` and never to the hashed
core, because they are platform facts and a hashed platform fact makes every cross-platform
comparison fail by construction. `statsforecast` is configured with `n_jobs=1` for the same reason:
its model search is numba-compiled and parallel float reduction order is not reproducible across
worker counts. A challenger whose fit does not reproduce under a fixed child seed is refused
registration by the arena, which INV-FCST-0 asserts.

The determinism claim is two-tier and this section claims no more than doctrine D-05 allows. On one
platform with the pinned dependency set, one seed and one config produce a byte-identical event log,
and INV-DET-1 asserts hash equality. Across platforms, one seed and one config produce identical
business events, and continuous fields agree within a tolerance derived from measured divergence.
Every byte-identical claim in this section, including INV-SOE-1, INV-WX-2, and the golden files of
7.5, is a same-platform claim. The cross-platform job reports the observed maximum divergence for
the fields listed in 7.2 rather than asserting a number chosen in advance, and names whether an
exceedance is a wrong tolerance or a defect.

| Package                | Import                 | Covers                                                 | Extra third-party deps                                                        |
|------------------------|------------------------|--------------------------------------------------------|-------------------------------------------------------------------------------|
| `twinflow-demand`      | `twinflow.demand`      | 6a demand signal, 6a3/6a6 order streams                | numpy, scipy                                                                  |
| `twinflow-forecast`    | `twinflow.forecast`    | 6a forecasting arena                                   | statsforecast, numpy, pandas, pyarrow; scikit-learn under the `learned` extra |
| `twinflow-inventory`   | `twinflow.inventory`   | 6a inventory optimization, 6a8 MEIO, E41 VMI policy    | numpy, scipy, networkx                                                        |
| `twinflow-supply`      | `twinflow.supply`      | 6a2 supplier network, E19 n-tier                       | networkx, numpy                                                               |
| `twinflow-fulfillment` | `twinflow.fulfillment` | 6a3 outbound, 6a6 e-commerce, E41 VAS and postponement | numpy, scipy                                                                  |
| `twinflow-crossdock`   | `twinflow.crossdock`   | 6a5                                                    | numpy                                                                         |
| `twinflow-returns`     | `twinflow.returns`     | 6a4                                                    | numpy                                                                         |
| `twinflow-transport`   | `twinflow.transport`   | 6a7                                                    | numpy, scipy, networkx                                                        |
| `twinflow-promise`     | `twinflow.promise`     | E16 ATP/CTP                                            | none beyond kernel                                                            |
| `twinflow-soe`         | `twinflow.soe`         | E15                                                    | none beyond kernel                                                            |
| `twinflow-network`     | `twinflow.network`     | E13 site topology and rollup, E42 network design       | networkx, highspy, numpy                                                      |
| `twinflow-resilience`  | `twinflow.resilience`  | E20 reverse stress testing, 6a8 disruption propagation | optuna, numpy                                                                 |
| `twinflow-exogenous`   | `twinflow.exogenous`   | E40 weather                                            | numpy, scipy                                                                  |

Heavy dependencies are optional extras (D-10). The core install of every package above is the three
shared internal packages plus the distributions in its own row. A learned challenger needs a
gradient-boosting implementation, which no other capability here needs, so it ships as
`twinflow-forecast[learned]` and the arena registers it only when the extra is installed. The CI job
of D-10 installs each package alone in a clean environment, imports it, and runs its unit tier, so
the claim that a brick installs alone is tested rather than asserted.

Third-party license note (C11). Every distribution named in the two tables above was read from the
Python Package Index JSON API at `https://pypi.org/pypi/<name>/json` on 2026-08-09, each request
returning HTTP 200, and the value below is the license this section relies on. The `Field read`
column names which JSON field carried it, because the API populates `license_expression` for some
projects and only the trove classifier for others, and a table that hides the difference is not
evidence. This table is the evidence for the claim that the allowlist check passes on this section,
not a summary of it.

| Distribution    | Version read | Declared license                                   | Field read                                       |
|-----------------|--------------|----------------------------------------------------|--------------------------------------------------|
| `numpy`         | 2.5.2        | BSD-3-Clause AND 0BSD AND MIT AND Zlib AND CC0-1.0 | `license_expression`                             |
| `scipy`         | 1.18.0       | BSD, from the OSI-approved trove classifier        | `classifiers`, `license` holds the full BSD text |
| `pandas`        | 3.0.5        | BSD 3-Clause                                       | `license`, confirmed by the trove classifier     |
| `pyarrow`       | 25.0.0       | Apache-2.0                                         | `license_expression`                             |
| `networkx`      | 3.6.1        | BSD-3-Clause                                       | `license_expression`                             |
| `statsforecast` | 2.1.1        | Apache Software License 2.0                        | `license`, confirmed by the trove classifier     |
| `optuna`        | 4.9.0        | MIT                                                | `classifiers`, `license_expression` is unset     |
| `highspy`       | 1.15.1       | MIT                                                | `license_expression`                             |
| `scikit-learn`  | 1.9.0        | BSD-3-Clause                                       | `license_expression`                             |

`highspy` packages the HiGHS solver. The HiGHS `LICENSE.txt` at
`https://raw.githubusercontent.com/ERGO-Code/HiGHS/master/LICENSE.txt` was retrieved on 2026-08-09
and is the MIT License text, so the wrapper and the wrapped solver carry the same terms. Every entry
above is permissive and compatible with the Apache-2.0 plus commercial dual license, so the CI
allowlist check covers this section with no exception row. The pinned versions live in the lock
file, and the release SBOM under C11 is the record that ships, not this table.

Doctrine D-14 applies to this section only in the negative: nothing here imports PM4Py or any other
AGPL-3.0 distribution, and no capability in this section depends on one.

### 2.1 `twinflow-demand`

Purpose: generate the synthetic demand signal with the structure 6a requires (trend, weekly and seasonal cycles, promotions, shocks) and turn it into concrete order streams for two channels (wholesale pallet orders, e-commerce parcel orders).

Public API:

```python
from twinflow.demand import (
    DemandModel,          # build from DemandConfig; .expected(sku, region, date) -> float
    DemandGenerator,      # .step(sim_date) -> list[DemandSignalPublished]
    OrderStreamGenerator, # .step(sim_date) -> list[OrderCreated]
    ChannelMix,           # time-varying wholesale/ecommerce split
    PromoCalendar,        # read-only view of promo events from 6a16, or a local stub
    DemandConfig,         # pydantic model, validates demand.yaml
)
```

Depends on: the kernel RNG streams named in `docs/design/variability-and-faults.md` section B.8, split per `(sku_id, region_id)` as section A.2 rule 2 requires. No internal package dependency beyond the shared three. The weather multiplier arrives as `weather.state.v1` on `EventBus`, never as an import of `twinflow-exogenous`, so `twinflow-demand` installs alone and runs with `weather.enabled=false`.

### 2.2 `twinflow-forecast`

Purpose: the forecasting arena. Named in A1 as a take-one-brick target, so it must be usable on any pandas frame of `(unique_id, ds, y)` with no twinflow concepts present.

Public API:

```python
from twinflow.forecast import (
    Arena,               # register models, run backtest, rank, emit comparison table
    ModelSpec,           # id, factory, family, eligible_quadrants
    ChallengerProtocol,  # the protocol E31 and learned models satisfy to enter the arena
    RollingOriginBacktest,
    metrics,             # mape, smape, wape, mase, rmsse, me_bias, tracking_signal
    diebold_mariano,     # with Harvey-Leybourne-Newbold small-sample correction
    ConformalWrapper,    # split conformal, per-horizon quantiles
    BiasMonitor,         # emits forecast.error.observed.v1 for the LSS control chart
    ForecastConfig,
)
```

### 2.3 `twinflow-inventory`

Purpose: segmentation, single-echelon policy, multi-echelon placement, replenishment planning, and the consignment ownership model.

Public API:

```python
from twinflow.inventory import (
    segmentation,        # abc(), xyz(), sbc_quadrant()  (Syntetos-Boylan-Croston)
    single_echelon,      # safety_stock(), reorder_point(), base_stock(), eoq(), newsvendor()
    loss_functions,      # standard_normal_loss G(k), inverse_loss k_for_fill_rate(),
                         # conformal_loss() and conformal_k_for_fill_rate() for the
                         # distribution-free path
    LeadTimeEstimator,   # fits twin-measured lead times, GOF gated
    PolicyEngine,        # per SKU-node policy selection and emission
    ReplenishmentPlanner,  # netting -> PO proposals -> appointment proposals
    NetRequirement,        # one (sku, node, bucket) row of the netting result
    PoProposal,            # what the planner asks the supply layer to issue
    AppointmentProposal,   # what the planner asks the dock schedule provider to book
    DockScheduleProvider,  # protocol; the deterministic baseline provider ships here
    RestockInflowModel,    # distributed lag from shipments to expected restock supply
    multi_echelon,       # GuaranteedServiceModel, ClarkScarfSerial, RiskPooling,
                         # BudgetConstrainedPlacement
    MeioNetwork, Node,   # the echelon graph and its nodes; declared in
                         # twinflow-schemas under D-09 and re-exported here
    Ownership,           # OWNED | CONSIGNED; location lives on the position and the leg
    VmiPolicy,           # min/max bands, consumption signal cadence, visibility latency
    InventoryConfig,
)
```

`ReplenishmentPlanner` is the component every headline 6a claim runs through, so it is a named module
with a public API rather than an implied step. Its three methods are the three things the rest of the
section asks of it.

| Method                                      | Input                                                               | Output                                                         |
|---------------------------------------------|---------------------------------------------------------------------|----------------------------------------------------------------|
| `net_requirements(plan_horizon)`            | forecast points, positions, open POs, in-transit, expected restock  | `list[NetRequirement]` per `(sku, node, bucket)`               |
| `propose_pos(net_requirements, policy_set)` | the netting result plus the active policy per SKU-node              | `list[PoProposal]` with quantity, supplier, and requested date |
| `propose_appointments(po_proposals)`        | PO proposals plus lane transit distributions plus the door calendar | `list[AppointmentProposal]` with door, window, and flow type   |

The planner proposes and never commits. `twinflow-supply` turns a `PoProposal` into
`supplier.po.issued.v1`, and `DockScheduleProvider` turns an `AppointmentProposal` into a booked
window. That split is what keeps the planner installable and testable alone, and it is what makes
`E2E-FCSTPROP-01` a mechanism test rather than a correlation: the forecast enters at
`net_requirements` and leaves as a dock arrival time.

### 2.4 `twinflow-supply`

Purpose: the supplier tier, its reliability physics, its scorecards, and the n-tier graph with hidden edges.

Public API:

```python
from twinflow.supply import (
    Supplier, SupplierNetwork,       # networkx DiGraph wrapper, tiers 1..n
    ReliabilityProfile,              # lead time dist, OTIF, defect rate, capacity
    PoLifecycle,                     # issue -> acknowledge -> ASN -> receipt
    Scorecard, ScorecardPeriod,      # OTIF, LT mean/sd/cv, defect PPM, sample n
    DisruptionCatalog,               # supplier outage, capacity cut, LT inflation
    NTierMap,                        # visibility states, reveal actions, concentration
    concentration,                   # dependent_tier1_share, hhi
    Genealogy,                       # trace_back(unit) -> ReceiptLot
                                     # blast_radius(lot_id) -> BlastRadius
    BlastRadius,                     # every downstream unit, order, shipment, and site
                                     # a lot reached, with the path to each
    SupplyConfig,
)
```

### 2.5 `twinflow-fulfillment`

Purpose: outbound execution for both channels plus value-added services.

Public API:

```python
from twinflow.fulfillment import (
    ReleasePolicy,        # WavePolicy | WavelessPolicy (CONWIP cap)
    PickingMode,          # DISCRETE | BATCH | ZONE | CLUSTER | GOODS_TO_PERSON
    TravelModel,          # s_shape, return, midpoint, largest_gap, optimal (Ratliff-Rosenthal)
    Cartoniser,           # box selection + 3D feasibility + dim weight
    FitChecker,           # independent geometric verifier, never the packer itself
    LoadBuilder,          # trailer cubing, weight, axle, LIFO stop order
    CarrierAssigner,      # cost/service selection, parcel rate shopping
    DockBroker,           # flow-type and changeover policy over the twin's door
                          # resources, plus wait attribution; it requests, never owns
    DockBrokerProtocol,   # declared in twinflow-schemas under D-09, re-exported
                          # here; cross-dock and returns type against it
    ChannelEconomics,     # per-order activity cost rollup
    VasLine,              # kitting, labeling, bundling, light assembly
    PostponementPlanner,  # stock_finished vs postpone
    FulfillmentConfig,
)
```

### 2.6 `twinflow-crossdock`

```python
from twinflow.crossdock import (
    FlowOrStoreEngine,   # RulePolicy | CostPolicy
    StagingLanes,        # capacity in pallet positions, dwell limit, forced putaway
    ConnectionTracker,   # planned vs actual outbound connection
    CrossdockKpis,       # dock_to_dock, staging_dwell, flow_through_pct, missed_connection_rate
    CrossdockConfig,
)
```

A `DockBrokerProtocol` implementation is injected at construction. The package types against the
protocol declared in `twinflow-schemas` (D-09) and imports no concrete broker, so it installs and
runs its unit tier alone with an in-memory door pool.

### 2.7 `twinflow-returns`

```python
from twinflow.returns import (
    ReturnGenerator,     # rate by SKU class and channel, delay distribution, causal reason linkage
    ReasonCode,          # enum
    CausalUpliftRegistry,  # reason-code uplift rules register as their source layer lands
    TriageStation,       # inspect, grade
    DispositionEngine,   # RESTOCK | REFURBISH | LIQUIDATE | SCRAP
    ReversePnl,          # recovery rate, cost per return, time to disposition
    RestockFeedback,     # emits inventory.adjustment.v1 and feeds RestockInflowModel
    ReturnsConfig,
)
```

A `DockBrokerProtocol` implementation is injected here for the same reason it is injected into
`twinflow-crossdock`, and the protocol is imported from `twinflow-schemas` (D-09).

### 2.8 `twinflow-transport`

```python
from twinflow.transport import (
    Lane, LaneNetwork,
    Mode,                # TL | LTL | PARCEL
    RateEngine,          # contract tariff, break weights, accessorials, fuel surcharge
    SpotMarket,          # mean-reverting log-rate index, shock coupling
    TransitModel,        # lognormal base + disruption multipliers
    Consolidator,        # Clarke-Wright savings + exact solver for small instances
    ModeSelector,        # cost vs service-days feasibility
    FreightSpendAnalytics,
    TransportConfig,
)
```

### 2.9 `twinflow-promise`

```python
from twinflow.promise import (
    AtpEngine,           # discrete and cumulative ATP over time buckets
    CtpEngine,           # falls back to CapacityPromiseProvider
    CapacityPromiseProvider,  # protocol implemented by 6a9 finite scheduler and DC labor
    PromiseLedger,       # quoted vs actual, promise reliability
    PromiseConfig,
)
```

### 2.10 `twinflow-soe`

```python
from twinflow.soe import (
    PlanOfRecord,        # snapshot interface; source is the replenishment plan, later S&OP consensus
    SoeTick,
    ExceptionDetector, ExceptionType, ExceptionQueue,
    CorrectiveAction, ActionRegistry,   # expedite, reallocate, substitute, de-expedite, re-wave
    CounterfactualArm,   # control arm re-run from the same checkpoint with identical child seeds
    SoeConfig,
)
```

### 2.11 `twinflow-network`

```python
from twinflow.network import (
    SiteRegistry, Site,          # E13
    BridgeTopicPolicy,           # which topics cross site broker -> enterprise broker
    NetworkKpis,                 # network fill rate, turns, inter-site transfer cost
    OverflowAllocator,           # "which site absorbs next week's overflow"
    FederatedRound, FederatedAggregator,  # FedAvg contract, weights only
    CenterOfGravity,             # Weiszfeld 1-median
    FacilityLocationMilp,        # capacitated, service-constrained, HiGHS
    RobustDesign,                # expected-cost and minimax-regret designs
    DesignInstantiator,          # writes facility.yaml configs for the operational twin
    NetworkConfig,
)
```

`MeioNetwork` and `Node` are imported from `twinflow-schemas` and are not redeclared here (D-09).
Freight rates arrive as `lane.rate.quoted.v1` on `EventBus`, so this package has no import edge to
`twinflow-transport`. Every HiGHS solve runs with `threads=1`, a fixed `random_seed`, a node limit,
and a fixed relative MIP gap, so the returned design does not depend on machine speed (D-04). Ties
between designs of equal objective value are broken by the sorted tuple of opened candidate ids.

### 2.12 `twinflow-resilience`

```python
from twinflow.resilience import (
    DisruptionSpace,     # declarative knob schema, shared with the chaos catalog
    ExhaustiveSearch,    # cardinality <= k, exact
    OptunaSearch,        # minimal-magnitude breaking sets
    BreakingSet,
    survival,            # time_to_survive, time_to_recover  (Simchi-Levi TTR/TTS framing)
    EchelonPropagation,  # disruption cascade across echelons
    ResilienceConfig,
)
```

`MeioNetwork` and `Node` are imported from `twinflow-schemas` (D-09). The search is a driver over
whole simulation runs, not a step inside one: each trial launches its own run with its own `run_id`,
and no search state ever enters a simulated run's event tape. That placement is what doctrine D-04
requires of a component whose scheduler is order-dependent, and it is why INV-DET-1 covers each
trial run individually rather than covering the search. The search itself is separately reproducible:
the Optuna sampler is seeded from the run seed, `n_jobs=1`, the trial count is fixed rather than
time-bounded, and the reduction over trial results is a sort by `(total_magnitude, cardinality,
sorted knob-id tuple)` so equal-magnitude sets return in one order.

### 2.13 `twinflow-exogenous`

```python
from twinflow.exogenous import (
    WeatherState, WeatherProcess,   # spatially correlated daily state
    SevereEvent, SevereEventCatalog,
    ClimateTrend,
    Coupling, CouplingRegistry,     # demand, transit, yard, hvac, slip_risk
    degree_days,                    # HDD and CDD, base 65F, daily mean of max and min
    ExogenousConfig,
)
```

---

## 3. Domain model

Types are Python types. Every entity below has a corresponding JSON Schema in `/schemas` when it crosses a package boundary as an event payload. Invariants marked INV-* are enforced by Hypothesis properties named in section 7.

Three type rules apply to every entity below, so they are stated once here rather than repeated.

**Money is `Decimal`, quantised, with a named rounding mode.** Every monetary field in this section
is a `decimal.Decimal` quantised to `Decimal("0.01")` in the run currency, rounded with
`ROUND_HALF_EVEN`. A monetary field is never a `float`, and a rate that multiplies a quantity is
carried at `Decimal("0.000001")` and quantised only when it becomes a posted cost. The JSON Schema
type for a monetary field is `string` with a decimal pattern, not `number`, so serialization cannot
introduce a binary rounding error. Allocated shares of a shared resource cost (dock occupancy,
staging occupancy, supervision) are split by the largest-remainder rule: each activity takes the
floor of its exact share, and the remaining cents go one each to activities ranked by descending
exact remainder, ties broken by ascending activity id. That rule is what makes INV-COST-1 a testable
statement rather than an aspiration.

**No field whose iteration order is observable is a `set`.** Where set semantics are wanted, the
field is a `frozenset` and its serialization is the sorted sequence of its members; where order is
part of the meaning, the field is a `tuple` with a uniqueness validator. Every `dict` field below is
built by inserting its keys in ascending key order and serializes in that order, so two processes
produce the same bytes for the same content. That covers `MeioSolution.service_times` and
`base_stocks`, `ReversePnl.by_reason`, `NetworkDesign.assignment`, `ContractTerms.accessorials`,
`BlastRadius.path_by_unit`, and every config-derived mapping in section 6. This is doctrine D-03
applied to the domain model, and section 7.2 names the property that asserts it.

**Every distribution named below is a row in the settled catalog.** `DistSpec` references a family
and parameters from `config/distributions.yaml` as defined in `docs/design/variability-and-faults.md`
section B. No entity here declares a family, a parameter default, or an RNG stream of its own.

### 3.1 Demand

**Sku**: `sku_id: str`, `category_id: str`, `unit_cost: Decimal`, `unit_price: Decimal`, `cube_m3: float`, `weight_kg: float`, `dims_mm: tuple[int,int,int]`, `shelf_life_days: int | None`, `hazmat: bool`, `stackable: bool`, `hs_code: str` (for E14), `weather_sensitivity: float` (elasticity to the severity index, default 0.0).

**Region**: `region_id: str`, `lat: float`, `lon: float`, `population_weight: float`, `weather_region_id: str`.

**DemandComponents**: `base: float`, `trend: float`, `seasonal_annual: float`, `dow: float`, `promo_lift: float`, `weather_mult: float`, `shock: float`. Invariant INV-DEM-1: `expected_units == base * trend * seasonal_annual * dow * promo_lift * weather_mult * shock` to within 1e-9 relative. The components are always published with the realized value so the causal chain is auditable and so E30's causal layer has the true structure to be scored against.

**PromoDecomposition**: per promotion, per SKU: `promo_id`, `sku_id`, `lift_integral_units: float`, `pull_forward_fraction: float`, `cannibalisation_fraction: float`, `incremental_fraction: float`, `dip_units: float`, `cannibalised_units: float`, `incremental_units: float`. The three fractions are not one parameter with two names. `pull_forward_fraction` is the share of the lift integral taken from the same SKU's post-promotion window, drawn per promotion from `variability.demand.forward_buy`. `cannibalisation_fraction` is the share taken from other SKUs in the same category over the promotion window, drawn from `variability.demand.cannibalisation`. `incremental_fraction` is the residual, `1 - pull_forward_fraction - cannibalisation_fraction`, and it is a reported output rather than a configured input. The residual can be negative when both drawn shares are large, which means the promotion destroyed more baseline demand than it created; that is a real outcome and it is reported, not clamped, so `incremental_fraction` has range `[-1, 1]` and no configured bound.

Invariant INV-DEM-4 is stated over realized units, not over the fractions. The three fractions sum
to 1.0 by construction, because the third is defined as one minus the other two, so asserting that
sum is a test no state of the world can fail and doctrine D-12 forbids it. What can fail is the
reconciliation between the declared decomposition and the series the generator produced.
INV-DEM-4 asserts three things: `incremental_units == lift_integral_units - dip_units -
cannibalised_units` to within 1e-9 relative; `dip_units` equals the summed shortfall of the promoted
SKU's realized expectation against its unpromoted counterfactual over the post-promotion dip window,
to within 1e-9 relative; and `cannibalised_units` equals the summed shortfall of the other SKUs in
the same category over the promotion window, on the same basis. A generator that publishes a
decomposition it did not produce fails on the second or third clause.

**DemandSignal**: `(sku_id, region_id, sim_date)` key, `expected_units: float`, `realised_units: int`, `components: DemandComponents`, `dist: Literal["poisson","negbin","zip"]`, `dispersion: float | None`.

**OrderLite**: the minimal order carried between P3e and 6a12. `order_id`, `channel: Literal["wholesale","ecommerce"]`, `customer_id`, `region_id`, `created_ts`, `requested_ship_date`, `lines: list[OrderLine]`, `priority_class: Literal["contract","spot","marketplace"]`, `state: OrderLiteState`. `OrderLiteState` is `CREATED | PROMISED | ALLOCATED | RELEASED | PICKED | PACKED | STAGED | LOADED | SHIPPED | DELIVERED | CANCELED | BACKORDERED`. 6a12 extends this enum additively (C3 additive-only within a major version) rather than replacing it. See open question 9.3.

**OrderLine**: `line_id`, `sku_id`, `qty_ordered: int`, `qty_allocated: int`, `qty_shipped: int`, `unit_price`, `promise: PromiseRef | None`.

Invariant INV-DEM-2: `qty_allocated <= qty_ordered` and `qty_shipped <= qty_allocated` at every sim time, for every line, in every scenario.

### 3.2 Forecast

**Series**: `(unique_id, ds, y)` with `unique_id = f"{sku_id}|{region_id}|{channel}"`. Granularity is daily by default, with weekly rollup as a config.

**ModelSpec**: `model_id`, `family: Literal["baseline","classical","learned","foundation"]`, `factory: Callable[[], Model]`, `eligible_quadrants: frozenset[SbcQuadrant]` serialized sorted (D-03), `requires_exog: bool`, `deterministic: bool`, `thread_count: int` fixed at 1. Invariant INV-FCST-0: registration is refused unless the model accepts an explicit RNG child stream from the kernel and two fits of the same training slice under the same stream produce parameter vectors that agree to 1e-12 and forecasts that are bit-identical. Accepting a seed is not enough; the fit must reproduce, and the arena proves that at registration time rather than trusting the flag.

**BacktestPlan**: `cutoffs: list[date]`, `horizon: int`, `window: Literal["expanding","sliding"]`, `sliding_len: int | None`, `step: int`, `min_train_periods: int`.

**ForecastPoint**: `run_id`, `model_id`, `unique_id`, `cutoff`, `target_date`, `h: int`, `yhat: float`, `lo: float | None`, `hi: float | None`, `interval_method: Literal["none","model","conformal"]`, `nominal_coverage: float | None`.

**ArenaResult**: per model, per horizon, per SBC quadrant: `mape, smape, wape, mase, rmsse, me_bias, tracking_signal, coverage`. Plus a pairwise `diebold_mariano` matrix against the incumbent.

Invariant INV-FCST-2: `wape` is invariant to multiplying every `y` and `yhat` by the same positive constant; `mase` is invariant to a change of measurement unit; `smape` as implemented lies in [0, 200].

### 3.3 Inventory

**Node**: `node_id`, `kind: Literal["supplier","factory","dc","forward","customer_region"]`, `site_id | None`, `echelon: int`, `region_id`.

**InventoryPosition**: `(node_id, sku_id, owner_party_id)` key, `on_hand: int`, `on_order: int`, `in_transit: int`, `allocated: int`, `available: int`, `ownership: Ownership`, `demand_rate_units_per_day: float`, `demand_rate_window_days: int`, `demand_rate_source: Literal["forecast","trailing_actual"]`.

The last three fields exist because `days_of_supply` is one of the four metrics the governed
semantic layer defines (1.2, E26b). This section publishes the numerator and the denominator of that
metric, never the ratio: `available` is the numerator, `demand_rate_units_per_day` is the
denominator, and `demand_rate_window_days` and `demand_rate_source` say how the denominator was
formed, because a days-of-supply computed on a forecast and one computed on trailing actuals are
different numbers and a report that does not say which is misleading.

`Ownership` is `OWNED | CONSIGNED` and carries no location. An earlier draft of this section put
`IN_TRANSIT` in the same enum, which made the most interesting case unrepresentable: consigned stock
on a truck is supplier-owned and in transit at the same time, and one enum cannot hold both. Location
lives where it always lived, on `in_transit` in this record and on the `Leg` and shipment records in
3.8, so the two dimensions are orthogonal and INV-VMI-1 is satisfiable. Section 8.1 freezes the
two-value enum into Phase 0 for that reason.

Invariant INV-INV-1: `on_hand >= 0` and `available == on_hand - allocated` at every sim time, in every scenario. Invariant INV-VMI-1: for a given `(node_id, sku_id)` the sum of `on_hand` across owner parties equals the physical count at that node; every physical unit has exactly one `owner_party_id` at every sim time, wherever it is; and ownership transitions are total and non-overlapping, so no unit is unowned or doubly owned for any interval, including the interval it spends on a truck.

**LeadTimeObservation**: `supplier_id | lane_id`, `sku_id | None`, `ordered_ts`, `promised_ts`, `received_ts`, `lead_time_days: float`, `source: Literal["twin","config_prior"]`. The policy engine consumes only `source="twin"` observations once `n >= leadtime.min_observations`; before that it uses the config prior and marks the emitted policy `derived_from.prior=True` so no report can silently claim a twin-measured number that is not one.

**LeadTimeFit**: `dist: Literal["lognormal","gamma","empirical"]`, `params`, `n`, `ad_stat`, `ad_pvalue`, `accepted: bool`. Invariant INV-INV-4: if `accepted=False` for all parametric candidates, the fit falls back to `empirical` bootstrap and never to a normal approximation.

**Policy**: `policy_type: Literal["sQ","sS","RS","base_stock"]`, `params`, `service_measure: Literal["cycle_service_level","fill_rate"]`, `target: float`, `review_period_days: int`, `uncertainty_source: Literal["normal_theory","conformal"]`, `derived_from: {leadtime_fit_id, demand_fit_id, forecast_run_id, conformal_calibration_id | None, prior: bool}`.

`uncertainty_source` records which distributional path produced the safety stock, because the two
give different numbers on the same inputs and a report that does not say which is misleading. It is
set to `conformal` whenever a calibrated conformal interval exists for the series at the policy's
horizon, and to `normal_theory` otherwise. 5.3 defines both paths.

Invariant INV-INV-2: `safety_stock` is non-decreasing in the service target, for fixed demand and lead-time parameters, under both values of `uncertainty_source`. Invariant INV-INV-3: `safety_stock` is non-decreasing in lead-time variance and in demand variance.

**NetRequirement**: `(sku_id, node_id, bucket_date)` key, `gross_demand: float`, `expected_restock_inflow: float`, `scheduled_receipts: float`, `on_hand_projected: float`, `safety_stock: float`, `net_requirement: float`, `forecast_run_id`, `policy_id`. Invariant INV-PLAN-1: `net_requirement == max(0, gross_demand - expected_restock_inflow - scheduled_receipts - on_hand_projected + safety_stock)` to within 1e-9 relative, and `expected_restock_inflow` is 0.0 exactly when `RestockInflowModel` is disabled, so the two configurations are distinguishable in the record rather than only in the result.

**PoProposal**: `proposal_id`, `sku_id`, `node_id`, `supplier_id`, `qty`, `requested_date`, `source_net_requirement_ids: tuple[str, ...]`, `policy_id`, `unit_price: Decimal`. **AppointmentProposal**: `proposal_id`, `door_flow_type: Literal["inbound","outbound","returns","crossdock"]`, `window_start_ts`, `window_end_ts`, `expected_pallets: int`, `source_po_ids: tuple[str, ...]`, `lane_id | None`. Invariant INV-PLAN-2: every `AppointmentProposal` traces to at least one `PoProposal` and every `PoProposal` above `planning.appointment_min_pallets` traces to exactly one `AppointmentProposal`, so no PO reaches a dock without a booked window and no window exists without a PO behind it.

**Segmentation**: `sku_id`, `abc: Literal["A","B","C"]`, `xyz: Literal["X","Y","Z"]`, `sbc_quadrant: Literal["smooth","erratic","intermittent","lumpy"]`, `adi: float`, `cv2: float`, `period`. Invariant INV-SEG-1: the ABC and XYZ assignments each form a total partition of the active SKU set with no SKU unassigned and no SKU in two classes.

**MeioNetwork**: a directed graph of nodes with, per arc, a processing time and a demand-propagation rule; per node a `max_service_time` bound and a stage cost. The guaranteed-service model also carries `net_replenishment_time` and `demand_bound` per node. This type has exactly one owning package, `twinflow-inventory`, and `twinflow-network` and `twinflow-resilience` import it rather than redeclaring it (D-09).

**MeioSolution**: `method: Literal["gst_dp","clark_scarf_serial","sim_search","budget_constrained"]`, `service_times: dict[node_id, int]`, `base_stocks: dict[node_id, float]`, `total_cost: Decimal`, `holding_cost: Decimal`, `holding_cost_budget: Decimal | None`, `budget_binding: bool | None`, `frontier: list[(service_target, cost)]`, `validated_against_sim: {run_id, achieved_service, ci_low, ci_high}`, `optimum_is_unique: bool`. Dict fields are built by inserting node ids in sorted order, so their iteration order is the sorted order and the serialized solution is stable across processes (D-03).

`optimum_is_unique` is set by the solver when it detects a tie in total cost between distinct service-time vectors, which happens routinely on trees with equal marginal stage costs. It is what lets VAL-GATE MEIO-1 compare against a published solution honestly: a different argmin at the same cost is a correct answer, and the gate says so.

Invariant INV-MEIO-1: base-stock level at a node is non-decreasing in that node's downstream service target. Invariant INV-MEIO-2: under `service_measure = cycle_service_level` with normally distributed location demand, pooled safety stock never exceeds the sum of decentralized safety stocks for non-negatively correlated demand across locations. That is a consequence of variance addition under a common safety factor, and it is stated with its assumptions because it does not survive without them. Invariant INV-MEIO-3 covers the fill-rate case, where per-location order quantities differ and the pooling comparison does not follow from variance addition: the analytic pooled requirement and the simulated pooled requirement agree within Monte Carlo error, and the direction of the pooling benefit is reported rather than asserted.

### 3.4 Supply

**Supplier**: `supplier_id`, `tier: int`, `country_of_origin: str`, `region_id`, `capacity_per_day: int`, `lead_time: DistSpec`, `otif_target: float`, `defect_rate_ppm: float`, `price_volume_curve: list[(min_qty, unit_price)]`, `certifications: list[str]`, `contract: ContractTerms | None`, `is_vmi: bool`.

**ReliabilityProfile** is the executable half of a Supplier. It draws an actual lead time from `variability.supplier.lead_time`. It draws the on-time and in-full outcomes jointly from a latent bivariate normal with correlation `otif_corr`, thresholded at `Phi^-1(p_on_time)` and `Phi^-1(p_in_full)`, because on-time and in-full are correlated in reality and independent draws produce an OTIF that is systematically too high. It draws per-lot defect counts from `variability.supplier.lot_defect_count`, which is overdispersed rather than binomial, because defects cluster inside a lot.

The latent-normal construction has an exact published joint probability, which is what makes it
testable rather than plausible: `P(on_time and in_full) = Phi_2(Phi^-1(p_1), Phi^-1(p_2); rho)`,
the bivariate normal orthant probability of the tetrachoric model in Pearson (1900),
Philosophical Transactions of the Royal Society of London A 195:1-47, DOI 10.1098/rsta.1900.0022.
VAL-GATE SUP-2 checks the simulated joint frequency against that value. Kendall's tau is not the
right summary here and is not used: the arcsine identity relating tau to rho, Kruskal (1958),
Journal of the American Statistical Association 53(284):814-861, DOI 10.1080/01621459.1958.10501481,
holds for continuous marginals, and two Bernoulli outcomes are tied almost everywhere.

**PurchaseOrder**: `po_id`, `supplier_id`, `lines`, `issued_ts`, `requested_date`, `acknowledged_date | None`, `state: ISSUED | ACKNOWLEDGED | SHIPPED | RECEIVED | CLOSED | CANCELED`.

**Asn**: `asn_id`, `po_id`, `lots: list[LotRef]`, `eta`, `carrier_id`, `mode`.

**ReceiptLot**: `lot_id`, `supplier_id`, `po_id`, `sku_id`, `qty`, `defect_qty`, `received_ts`, `genealogy_parent_lot_ids: tuple[str, ...]` in ascending lot-id order. Invariant INV-GEN-1 (backward traceback): every `ReceiptLot` resolves to exactly one supplier and one PO; every downstream defect finding traces back through the genealogy graph to exactly one `ReceiptLot`.

**BlastRadius**: the forward half of traceability, which 6a2 requires in the same sentence as the backward half. `Genealogy.blast_radius(lot_id)` returns `lot_ids: tuple[str, ...]`, `unit_ids: tuple[str, ...]`, `pallet_ids: tuple[str, ...]`, `order_ids: tuple[str, ...]`, `shipment_ids: tuple[str, ...]`, `customer_ids: tuple[str, ...]`, `site_ids: tuple[str, ...]`, `in_transit_leg_ids: tuple[str, ...]`, `still_on_hand_positions: tuple[(node_id, sku_id, qty), ...]`, and `path_by_unit: dict[unit_id, tuple[str, ...]]` giving the genealogy path from the queried lot to each unit. Every tuple is sorted, so two runs of the same query return the same object.

Invariant INV-GEN-2 (forward blast radius): for every `ReceiptLot`, the set of units returned by `blast_radius(lot_id)` equals exactly the set of units whose backward traceback under INV-GEN-1 resolves to that lot. The two directions are the same relation read two ways, and asserting them against each other is what makes either one trustworthy. A unit that appears in one and not the other is a genealogy graph defect, and the property names which direction dropped it.

The query is the input to 6a11's mock recall drill. This section owns the query, its result type, and
ORACLE SUP-4; 6a11 owns the drill, the quarantine workflow, and the recall-readiness report.

**Scorecard**: `supplier_id`, `period`, `otif`, `on_time_rate`, `in_full_rate`, `lead_time_mean`, `lead_time_sd`, `lead_time_cv`, `defect_ppm`, `lines_n`, `units_n`, `on_time_n`, `in_full_n`, `otif_n`, `defect_units_n`. Each metric carries a `stat_type` field declaring `proportion_defective | defects_per_unit | continuous` so the LSS engine selects p-chart, u-chart, or I-MR without guessing, and each proportion carries its own numerator and denominator so the engine never has to infer a subgroup size. Invariant INV-SUP-1: `otif`, `on_time_rate`, `in_full_rate` in [0,1]; `defect_ppm` in [0, 1e6]; `otif <= min(on_time_rate, in_full_rate)`; and each rate equals its numerator over `lines_n` to within 1e-12.

**ScorecardRestatement**: `restatement_id`, `supplier_id`, `period`, `metric`, `value_before`, `value_after`, `trigger_event_id`, `restated_ts`. A defect found downstream belongs to the period the lot was received in, not the period the defect was found in, so the scorecard for a closed period changes after the fact. The change is a record, never an overwrite: the restatement carries both values and the event that caused it. Invariant INV-SUP-3: for every `(supplier_id, period, metric)` the current value equals the originally published value composed with every restatement in `restated_ts` order, and no restatement exists without a `trigger_event_id` that resolves to a defect finding.

**SupplierCapacity**: `supplier_id`, `sim_date`, `capacity_units`, `requested_units`, `granted_units`, `rationing_rule: Literal["proportional","priority_then_fcfs"]`, `shortfall_units`. Supplier capacity is a hard limit, so a day whose requested quantity exceeds `capacity_per_day` is rationed rather than silently satisfied. The default rule is `proportional`: each open PO line receives `floor(capacity_units * requested_line / requested_total)` units, and the remainder is distributed one unit at a time to lines ranked by descending fractional part, ties broken by ascending `po_id` then ascending `line_id`. That tie-break is what makes the rationing reproducible under D-03. Invariant INV-SUP-2: `granted_units <= capacity_units`, `granted_units + shortfall_units == requested_units`, and the granted quantities are unchanged when the input lines are presented in a different order.

**NTierEdge**: `parent_supplier_id`, `child_supplier_id`, `component_class`, `share: float`, `visibility: Literal["unknown","inferred","confirmed"]`, `mapping_cost`, `mapping_effort_days`. Invariant INV-NTIER-1: for each parent and component class, the shares over children sum to 1.0 within 1e-9, whether or not the edges are visible. The visible-share sum is a direct measure of mapping completeness.

**ConcentrationReport**: per node, `dependent_tier1_ids`, `dependent_tier1_share`, `hhi` over sources per component class, `revealed_fraction`.

### 3.5 Fulfillment

**Wave**: `wave_id`, `release_ts`, `cutoff_ts`, `orders: list[order_id]`, `sizing_rule`, `zone_scope`. **WavelessRelease**: `wip_cap_per_zone`, `release_priority_rule`.

**PickTask**: `task_id`, `order_id | batch_id`, `sku_id`, `qty`, `location_id`, `zone_id`, `mode`, `travel_distance_m`, `assigned_resource_id`, `start_ts`, `end_ts`, `mispick: bool`. `mispick` is driven by the operator fatigue and error model from 6a10 when that layer exists, by a constant rate before it, and the switch is a config flag so the golden files record which model produced the run.

**Carton**: `carton_id`, `box_id`, `items: list[(sku_id, qty)]`, `item_cube_m3`, `box_cube_m3`, `cube_fill: float`, `actual_weight_kg`, `dim_weight_kg`, `billable_weight_kg`, `void_fill_cost`. Invariant INV-CART-1: `billable_weight_kg == max(actual_weight_kg, dim_weight_kg)`; `cube_fill in (0, 1]`; the packed set passes `FitChecker`, which is a separate implementation from the packer.

**Load**: `load_id`, `trailer_type`, `stops: list[stop]`, `pallets`, `cube_util`, `weight_util`, `axle_loads`, `lifo_valid: bool`. Invariant INV-LOAD-1: `cube_util <= 1.0`, `weight_util <= 1.0`, every axle load within its configured limit, and for multi-stop loads the pallet order is LIFO-consistent with the stop order.

**DockDoor**: `door_id`, `types_allowed: frozenset[Literal["inbound","outbound","returns","crossdock"]]` serialized as a sorted sequence (D-03), `current_type`, `changeover_minutes`.

The door itself is a twin resource. The twin package holds each door as a SimPy `Resource` and is the
only thing that can grant it, which is why 1.2 lists docks under Component 1. `DockBroker` sits above
that resource and owns three things the twin does not: which flow types a door accepts, what a type
switch costs in unavailability, and which flow to attribute each queue wait to. It requests the twin's
door resource like any other requester and never grants one itself. Every inbound receipt, outbound
load, returns intake, and cross-dock move arrives at the same twin resource, through one policy
layer, which is what makes the contention real rather than modeled twice.

Invariant INV-DOCK-1: a door is never occupied by two flows at once, and a type switch always charges `changeover_minutes` of unavailability. Invariant INV-DOCK-2: every queue wait recorded by `DockBroker` is attributed to exactly one flow type, and the sum of attributed waits per door equals that door's total granted-request wait time in the twin's own resource log to within 1e-9 seconds. The second invariant is what proves the broker is a policy layer rather than a second scheduler: if it were granting doors on its own, the two logs would diverge.

**VasJob**: `job_id`, `type: Literal["kitting","labeling","bundling","light_assembly"]`, `output_sku_id`, `components: list[(sku_id, qty)]`, `labor_minutes`, `defect_qty`. Invariant INV-VAS-1: material conservation, `sum(component qty consumed) == bom qty * output qty + scrap qty`.

**OrderCostRecord**: per order, an activity list with `(activity_id, activity, resource, minutes: Decimal, rate: Decimal, cost: Decimal)` plus material lines, freight lines, and allocated shared-resource lines. Every monetary field follows the quantisation and rounding rule stated at the head of section 3. Allocated shared-resource lines carry `allocation_basis` (`dock_occupancy_seconds`, `staging_position_seconds`, or `supervision_minutes`) and `allocation_residual_cents`, the number of cents this line received from the largest-remainder split. This is the raw feed for 6a17's activity-based costing. Invariant INV-COST-1: the sum of the `cost` fields of every line equals the reported `cost_per_order` exactly, as `Decimal` equality at `Decimal("0.01")`, with no tolerance; and the sum of `allocation_residual_cents` across the orders sharing one resource pool equals the pool's unallocated remainder exactly, so no cent is created or lost by the split.

### 3.6 Cross-dock

**FlowDecision**: `pallet_id`, `decision: Literal["FLOW","STORE"]`, `policy: Literal["rule","cost"]`, `score_flow`, `score_store`, `reason_codes: list[str]`, `connection_deadline_ts`, `target_load_id | None`.

**StagingLane**: `lane_id`, `capacity_positions: int`, `dwell_limit_s: int`, `assigned_door_id`. Invariant INV-XDOCK-1: no pallet exceeds `dwell_limit_s` on a lane without a `crossdock.forced_putaway.v1` event being emitted in the same sim instant.

**Connection**: `pallet_id`, `planned_load_id`, `made: bool`, `dwell_s`, `dock_to_dock_s`, `subgroup_key`. `subgroup_key` is the `(site_id, sim_date, shift_id)` triple the LSS engine aggregates over to build a p-chart subgroup, because a single connection is a binary outcome and a proportion needs a denominator.

Invariant INV-XDOCK-2 is a two-level closure, because the section's own forced-putaway mechanic
means a decision and an outcome are different things and one bucket pair cannot hold both.

At the decision level, every received pallet is decided exactly once:
`decided_flow + decided_store == received`.

At the outcome level, every pallet decided FLOW ends in exactly one of three states:
`flowed + force_putaway + still_staged == decided_flow`, where `still_staged` counts pallets whose
decision has not yet resolved at the end of the run.

`flow_through_pct` is defined over resolved decisions only, `flowed / (flowed + force_putaway)`, and
the denominator is published on the same event so no reader has to guess it. The missed-connection
p-chart uses a different denominator, `decided_flow` resolved in the subgroup, because a missed
connection is a failure of a pallet that was supposed to make a truck, and a forced putaway is a
different defect with its own chart. Both denominators are named on the event, so the two charts are
never accidentally computed on the same base.

### 3.7 Returns

**ReturnRequest**: `rma_id`, `order_id`, `sku_id`, `qty`, `reason_code`, `created_ts`, `causal_link: {source_event_id, kind} | None`.

`ReasonCode` enum: `DAMAGED_IN_TRANSIT`, `WRONG_ITEM_SHIPPED`, `CUSTOMER_REMORSE`, `QUALITY_DEFECT`, `NOT_AS_DESCRIBED`, `LATE_DELIVERY_REFUSAL`.

Causal linkage rules, which are what make the Pareto worth drawing. Each rule is an entry in
`CausalUpliftRegistry`, and each entry registers when the layer that produces its evidence lands.
The base reason mix comes from `variability.returns.reason_mix`; an uplift multiplies one reason's
weight when its evidence is present, by the factor in `returns.causal_uplift`.

| Reason code             | Evidence that raises it                                                               | Evidence source layer     | Registers at |
|-------------------------|---------------------------------------------------------------------------------------|---------------------------|--------------|
| `WRONG_ITEM_SHIPPED`    | a `mispick` on the order's pick tasks                                                 | fulfillment               | P3f          |
| `QUALITY_DEFECT`        | the defect fraction of the lots consumed by that order                                | supply genealogy          | P3f          |
| `LATE_DELIVERY_REFUSAL` | a missed promise date on the promise ledger                                           | promise                   | P3f          |
| `DAMAGED_IN_TRANSIT`    | outbound handling exceptions and load-quality signals on the shipment                 | fulfillment               | P3f          |
| `DAMAGED_IN_TRANSIT`    | a shock or temperature excursion on the shipment's transport legs, from cargo sensors | transport, sensor catalog | P3h          |

`DAMAGED_IN_TRANSIT` has two registered uplifts because its strongest evidence, the cargo shock and
temperature sensors on a transport leg, does not exist until transport lands at P3h, and returns land
at P3f. Rather than assert an uplift that has no source at P3f, the reason code ships at P3f with
the uplift that does have a source, and the transport uplift registers later through the same
registry. Every returns event and every reason-code Pareto carries `causal_sources_active`, the
sorted tuple of uplift ids that were live for that run, and `E2E-RET-01` records it in the golden
file. A Pareto computed at P3f and a Pareto computed at P3h are comparable and are never mistaken
for each other. Section 8.5 states the same sequencing from the phase side.

Invariant INV-RET-1: every `QUALITY_DEFECT` return resolves through genealogy to exactly one `ReceiptLot` and so to exactly one supplier scorecard. Invariant INV-RET-3: every return whose reason code was raised by an uplift carries a `causal_link` naming the source event, and every uplift id in `causal_sources_active` is a registered entry, so a run cannot claim an evidence source that was not live.

**TriageResult**: `rma_id`, `grade: Literal["A","B","C","SCRAP"]`, `inspect_minutes`, `inspector_id`.

**Disposition**: `rma_id`, `path: RESTOCK | REFURBISH | LIQUIDATE | SCRAP`, `labor_minutes`, `material_cost`, `recovery_value`, `cycle_time_s`, `restock_lot_id | None`.

Invariant INV-RET-2 (returns closure): `received == restocked + refurbished + liquidated + scrapped + in_triage_wip` at every sim time.

**ReversePnl**: `period`, `returns_units`, `recovery_rate` (recovered value / original COGS), `cost_per_return`, `mean_time_to_disposition_s`, `by_reason: dict[ReasonCode, ...]`.

### 3.8 Transport

**Lane**: `lane_id`, `origin_node_id`, `dest_node_id`, `distance_km`, `modes_allowed`, `base_transit: DistSpec` per mode, `weather_region_path: list[region_id]`, `international: bool`, `border_delay: DistSpec | None`.

**Carrier**: `carrier_id`, `modes`, `service_levels`, `contract: ContractTerms | None`, `on_time_profile`, `capacity_per_day_per_lane`.

**ContractTerms**: `rate_basis: Literal["per_mile","per_cwt_class","parcel_zone"]`, `tiers: list[(min_volume, rate)]`, `min_charge`, `fuel_surcharge_index_id`, `accessorials: dict[str, Decimal]`, `committed_volume`, `expiry_date`, `escalator_pct`.

**RateQuote**: `lane_id`, `mode`, `carrier_id`, `service`, `rate_source: Literal["contract","spot"]`, `linehaul: Decimal`, `fuel: Decimal`, `accessorials: Decimal`, `total_cost: Decimal`, `transit_days_p50`, `transit_days_p95`. Invariant INV-TRN-4: `total_cost == linehaul + fuel + accessorials` as exact `Decimal` equality at `Decimal("0.01")`, with no tolerance.

**SpotIndex**: `lane_group_id`, `sim_date`, `index_value`. Process: `d log X = theta (mu - log X) dt + sigma dW`, discretised exactly (the OU exact transition, not Euler), with `mu` shifted by weather severity and by aggregate capacity utilization on the lane group. Invariant INV-TRN-3: with `sigma=0`, the index converges monotonically to `exp(mu)`; the estimator recovers `theta, mu, sigma` from a 10,000-step simulated path within a 95% confidence interval.

**Leg**: `leg_id`, `shipment_id`, `lane_id`, `mode`, `carrier_id`, `planned_transit_s`, `actual_transit_s`, `disruption_ids`, `distance_km`, `billable_weight_kg`.

Invariant INV-TRN-1: no load exceeds cube or weight capacity.

Invariant INV-TRN-2 is scoped to the exact solver, because it is false for the heuristic that
ships. On a metric distance matrix with non-negative distances, adding a stop to a route
never reduces the length of the **optimal** tour, so the property holds for the branch-and-bound
consolidator's output and is asserted there. It does not hold for the Clarke and Wright savings
heuristic: a savings pass over a larger stop set can merge routes it could not merge before, and the
heuristic tour can get shorter when a stop is added. Asserting the optimal-tour property over the
heuristic would fail on the first counterexample a property test generated, which is a defect in the
statement and not in the code.

Invariant INV-TRN-5 is the true property of the heuristic, and it is the one asserted over the
production path: on every instance small enough for the exact solver to run, the heuristic tour is
never shorter than the exact optimum, and the recorded gap is reported. That is a real check with a
real failure mode, because a heuristic that beats the optimum has a bug in its distance
accumulation.

Freight class handling: LTL pricing uses a density-to-class table. Real NMFC classification data is proprietary and is not redistributed. The repo ships `catalogs/freight_classes.synthetic.yaml`, a synthetic density-to-class table with the same shape (density bands mapping to class numbers), labeled synthetic in the file header and in the README. See open question 9.5.

### 3.9 Promise

**AtpBucket**: `(node_id, sku_id, bucket_date)`, `on_hand`, `scheduled_receipts`, `in_transit`, `committed`, `atp`, `cumulative_atp`.

**Promise**: `order_id`, `line_id`, `method: Literal["atp","ctp"]`, `quoted_date`, `quoted_ts`, `supply_refs: list[event_id]`, `confidence: float`, `is_repromise: bool`, `superseded_by: promise_id | None`.

**PromiseOutcome**: `promise_id`, `quoted_date`, `actual_ship_date`, `actual_delivery_date`, `met: bool`, `days_late: int`, `subgroup_key`. `subgroup_key` is the `(site_id, sim_date, priority_class)` triple the LSS engine aggregates over to form a p-chart subgroup, because a single promise is a binary outcome and a proportion needs a denominator.

Invariant INV-ATP-1 (no over-promise): for every `(node, sku, bucket)`, the sum of open promises consuming that bucket never exceeds its available supply.

Quantity monotonicity is stated as two properties, because an earlier draft collapsed them into one
clause that had no meaning. Invariant INV-ATP-2a: holding the requested date fixed, raising the
requested quantity never returns an earlier promised date. Invariant INV-ATP-2b: holding the
requested date and the supply state fixed, the promised quantity is non-decreasing in the requested
quantity, and it never exceeds the requested quantity. Each half is a separate Hypothesis property
in 7.2, so a failure names which monotonicity broke.

### 3.10 S&OE

**PlanSnapshot**: `snapshot_id`, `taken_ts`, `horizon_days`, `planned_receipts`, `planned_shipments`, `planned_labor_hours`, `forecast_run_id`, `policy_set_id`, `source: Literal["replenishment_plan","sop_consensus"]`.

**Exception**: `exception_id`, `type`, `severity`, `revenue_at_risk`, `service_impact` (orders and lines at risk), `cost_impact`, `evidence: list[event_id]`, `node_id | lane_id | sku_id`, `detected_ts`, `state: OPEN | ACTIONED | SHELVED | CLOSED`.

`ExceptionType` enum: `FORECAST_MISS`, `RECEIPT_LATE`, `CAPACITY_SHORT`, `SERVICE_AT_RISK`, `INVENTORY_BELOW_REORDER`, `PROMISE_AT_RISK`, `LANE_DISRUPTED`, `SUPPLIER_OUTAGE`, `RETURNS_SURGE`, `DOCK_CONGESTED`.

**CorrectiveAction**: `action_id`, `exception_id`, `kind`, `params`, `authority_tier` (L1 advise / L2 recommend / L3 auto-apply, from E5), `cost_estimate`, `applied_ts`.

**ActionMeasurement**: `action_id`, `treated_run_id`, `control_run_id`, `delta: {service, cost, revenue}`, `hypothesis_test: {test, statistic, p_value, effect_size, ci}`. The control arm is a re-run from the same checkpoint with identical RNG child seeds, so the difference is the action and not noise.

Invariant INV-SOE-1: applying the null action produces a byte-identical event log to the control arm. This is a direct test of C1 through the S&OE machinery.

### 3.11 Network

**Site**: `site_id`, `facility_config_uri`, `region_id`, `roles: frozenset[Literal["dc","forward","factory","crossdock"]]` serialized as a sorted sequence (D-03), `broker_endpoint`, `uns_prefix`, `timezone`.

**BridgeTopicPolicy**: `forward: list[topic_glob]`, `block: list[topic_glob]`, `qos`, `retain_policy`. The default policy forwards findings, KPI rollups, and birth/death certificates, and blocks raw high-rate telemetry. The measured effect (events per second and bytes crossing the bridge, versus raw forwarding) is the E36 edge-economics number for the multi-site case.

**NetworkKpi**: `period`, `network_fill_rate`, `network_turns`, `intersite_transfer_units`, `intersite_transfer_cost`, `load_balance_gini`, per-site breakdown.

**FederatedUpdate**: `round_id`, `site_id`, `model_id`, `model_version`, `param_count`, `param_blob_uri`, `sample_count`, `metric_before`, `metric_after`. Invariant INV-FL-1: the `fl.update.v1` schema has `additionalProperties: false` and contains no telemetry-typed field; a CI test asserts the field set is a subset of the allowlist and that the payload byte size is bounded by `param_count * bytes_per_param + header_bytes`, so raw data cannot be smuggled in a padded blob.

**Candidate**: `candidate_id`, `lat`, `lon`, `fixed_cost_year`, `capacity_units_year`, `labor_rate`, `labor_availability`, `real_estate_cost_m2`, `region_id`.

**NetworkDesign**: `design_id`, `method: Literal["cog","milp","robust_expected","robust_minimax_regret"]`, `opened_sites: list[candidate_id]`, `assignment: dict[region_id, candidate_id]`, `predicted_cost_breakdown`, `service_coverage` (fraction of demand within N transit days), `scenario_id`.

**DesignValidation**: `design_id`, `facility_config_uris`, `twin_run_id`, `simulated_cost`, `predicted_cost`, `gap_pct`, `gap_decomposition: {congestion, labor_queueing, dock_contention, other}`.

### 3.12 Resilience

**DisruptionKnob**: `knob_id`, `target: Literal["supplier","lane","site","labor","demand"]`, `target_id`, `kind`, `domain: {min, max}` for continuous or `{False, True}` for binary, `magnitude_cost` (a scalar making disruptions comparable so "minimal" is well defined).

**BreakingSet**: `set_id`, `disruptions: list[(knob_id, magnitude)]`, `cardinality`, `total_magnitude`, `threshold_breached: Literal["service","cash","both"]`, `tts_days`, `ttr_days`, `search_method`, `trials`, `seed`.

`time_to_survive` is the number of days the network holds the threshold with no recovery action after the disruption starts. `time_to_recover` is the number of days from the disruption start to restored threshold compliance with recovery actions enabled. Both follow the risk-exposure framing in Simchi-Levi, Schmidt, Wei et al. (2015), Interfaces 45(5):375-390.

Invariant INV-RST-1: if a set of disruptions breaks a threshold, every superset also breaks it under monotone disruption knobs. The search exploits this and a test asserts it.

### 3.13 Exogenous weather

**WeatherState**: `(weather_region_id, sim_date)` key, `temp_c`, `temp_anomaly_c`, `precip_mm`, `snow_mm`, `wind_ms`, `severity_index: float in [0,1]`, `event_id | None`. Generated by a seasonal mean plus a vector autoregressive anomaly process with a spatial correlation matrix built from inter-region distance with an exponential decay length `corr_length_km`.

**SevereEvent**: `event_id`, `kind: Literal["heat_wave","winter_storm","hurricane","flood","ice_storm"]`, `regions`, `start_date`, `end_date`, `intensity in [0,1]`.

**ClimateTrend**: `warming_c_per_decade`, `severe_event_frequency_multiplier_per_decade`.

**Coupling**: a registered function `(WeatherState, target_context) -> multiplier`, with `target` in `{demand, transit, yard_rate, hvac_load, slip_risk, ambient_sensor}`. Invariant INV-WX-1: all subscribers reading `(weather_region_id, sim_date)` observe an identical state object, compared by content hash. Invariant INV-WX-2: same seed produces an identical weather series, byte for byte.

---

## 4. Events

Schema location: `/schemas/<domain>/<event>.v<major>.schema.json`, JSON Schema draft 2020-12, `additionalProperties: false`, additive-only evolution within a major version (C3).

Envelope. This section declares payloads only. The envelope is owned by the foundations section and
frozen in Phase 0, and doctrine D-07 fixes its shape: the CloudEvents 1.0 attributes plus the
extension attributes `twinflowsimts`, `twinflowrunid`, `twinflowproducerid`, `twinflowseq`,
`twinflowcausationid`, and `twinflowcorrid`. Every producer named below draws its
`twinflowproducerid` from the closed set in `schemas/registry.yaml`, and `twinflowseq` is dense per
`(twinflowrunid, twinflowproducerid)` and not globally. The canonical total order of the log is
`(twinflowsimts, twinflowproducerid, twinflowseq)`, and every reader in this section, including the
S&OE plan-versus-actual diff of 5.12 and the replay used by the control arm, uses that triple and no
other order.

Two consequences bind the payload tables below. No payload carries a wall-clock field, because
doctrine D-02 permits a wall-clock read in exactly four places and none of them is an event payload;
where a payload needs a timestamp it carries sim time in ticks. No payload carries the run seed,
because doctrine D-01 puts the seed in the hashed core of the manifest and duplicating it per event
would let the two disagree.

Transport. Planning events are L4 business-layer events published on `EventBus` and persisted to
Delta by the historian. Four subjects are marked UNS-published below, meaning they must also reach
the OT segment or another site's broker. Applying doctrine D-08, the packages here do not publish
them on MQTT: the IoT and UNS section's bridge subscribes to them on `EventBus` and republishes them
on `Network`, where retain, quality of service, and last will apply. The set is exactly
`dock.allocation.v1`, `weather.state.v1`, `site.kpi.period.v1`, and `network.kpi.period.v1`, and
`test_uns_published_set_matches_the_bridge_subscription` asserts the two lists agree.

### 4.1 Demand

| Event                     | Version | Key fields                                                                                                | Producer                                  | Consumers                                  |
|---------------------------|---------|-----------------------------------------------------------------------------------------------------------|-------------------------------------------|--------------------------------------------|
| `demand.signal.published` | v1      | sku_id, region_id, sim_date, expected_units, realised_units, components{}, dist, seed_stream              | `twinflow-demand`                         | forecast, inventory, soe, causal (E30)     |
| `order.created`           | v1      | order_id, channel, customer_id, region_id, requested_ship_date, lines[], priority_class, source_signal_id | `twinflow-demand` (P3e), ERP stub (later) | promise, fulfillment, crossdock, soe, 6a12 |
| `order.canceled`          | v1      | order_id, reason, stage_reached, cancel_cost                                                              | fulfillment                               | finance, soe                               |
| `channel.mix.changed`     | v1      | period, wholesale_share, ecommerce_share, source                                                          | demand                                    | fulfillment, network                       |

### 4.2 Forecast

| Event                         | Version | Key fields                                                                                                                    |
|-------------------------------|---------|-------------------------------------------------------------------------------------------------------------------------------|
| `forecast.run.completed`      | v1      | run_id, model_id, model_version, cutoff, horizon_days, granularity, series_count, metrics{}, seed, deterministic              |
| `forecast.point`              | v1      | run_id, unique_id, cutoff, target_date, h, yhat, lo, hi, interval_method, nominal_coverage                                    |
| `forecast.error.observed`     | v1      | run_id, unique_id, target_date, h, y, yhat, error, scaled_error, ape, stat_type="continuous"                                  |
| `forecast.backtest.completed` | v1      | arena_id, plan{}, models[], per_model_metrics[], winner_model_id, dm_tests[], comparison_table_uri, published_either_way=true |
| `forecast.bias.finding`       | v1      | unique_id_group, chart="I-MR", rule_violated, evidence_window, severity                                                       |

`forecast.error.observed.v1` is the feed for the LSS engine's control chart. The `stat_type` field is what lets the engine select the chart without this package knowing anything about SPC.

### 4.3 Inventory

| Event                             | Version | Key fields                                                                                                                                                                      |
|-----------------------------------|---------|---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| `inventory.policy.set`            | v1      | sku_id, node_id, policy_type, params{}, service_measure, target, derived_from{leadtime_fit_id, demand_fit_id, prior}                                                            |
| `inventory.position.snapshot`     | v1      | node_id, sku_id, owner_party_id, sim_ts, on_hand, on_order, in_transit, allocated, available, ownership, demand_rate_units_per_day, demand_rate_window_days, demand_rate_source |
| `inventory.adjustment`            | v1      | node_id, sku_id, qty_delta, reason, source_event_id, lot_id                                                                                                                     |
| `inventory.ownership.transferred` | v1      | node_id, sku_id, qty, from_party, to_party, trigger, lot_id                                                                                                                     |
| `segmentation.assigned`           | v1      | sku_id, abc, xyz, sbc_quadrant, adi, cv2, period                                                                                                                                |
| `leadtime.observed`               | v1      | source_kind, source_id, sku_id, ordered_ts, promised_ts, received_ts, lead_time_days                                                                                            |
| `leadtime.fit.completed`          | v1      | fit_id, source_id, dist, params{}, n, ad_stat, ad_pvalue, accepted                                                                                                              |
| `meio.solution`                   | v1      | solution_id, network_hash, method, service_times{}, base_stocks{}, total_cost, frontier[], validated_against_sim{}                                                              |
| `vmi.consumption`                 | v1      | node_id, sku_id, qty_consumed, period, signal_latency_days, record_accuracy_assumed                                                                                             |
| `vmi.replenishment.triggered`     | v1      | supplier_id, node_id, sku_id, qty, min_band, max_band, observed_position                                                                                                        |

### 4.4 Supply

| Event                         | Version | Key fields                                                                                                                                    |
|-------------------------------|---------|-----------------------------------------------------------------------------------------------------------------------------------------------|
| `supplier.po.issued`          | v1      | po_id, supplier_id, lines[], requested_date, source: reorder_signal_id                                                                        |
| `supplier.po.acknowledged`    | v1      | po_id, promised_date, confirmed_lines[]                                                                                                       |
| `supplier.asn.sent`           | v1      | asn_id, po_id, lots[], eta, carrier_id, mode                                                                                                  |
| `supply.lot.received`         | v1      | lot_id, po_id, supplier_id, sku_id, qty, defect_qty, received_ts, genealogy_parent_lot_ids[]                                                  |
| `supplier.scorecard`          | v1      | supplier_id, period, otif, on_time_rate, in_full_rate, lead_time_mean, lead_time_sd, lead_time_cv, defect_ppm, lines_n, units_n, stat_types{} |
| `supplier.scorecard.restated` | v1      | restatement_id, supplier_id, period, metric, value_before, value_after, trigger_event_id, restated_ts                                         |
| `supplier.capacity.rationed`  | v1      | supplier_id, sim_date, capacity_units, requested_units, granted_units, rationing_rule, shortfall_units, affected_po_ids[]                     |
| `supplier.disruption`         | v1      | supplier_id, kind, start_date, end_date, capacity_multiplier, lead_time_multiplier, cause_ref                                                 |
| `ntier.edge.revealed`         | v1      | parent_id, child_id, component_class, share, visibility_before, visibility_after, mapping_cost, effort_days                                   |
| `ntier.concentration`         | v1      | node_id, dependent_tier1_ids[], dependent_tier1_share, hhi, revealed_fraction, period                                                         |

### 4.5 Fulfillment

| Event                                       | Version | Key fields                                                                                                          |
|---------------------------------------------|---------|---------------------------------------------------------------------------------------------------------------------|
| `wave.released`                             | v1      | wave_id, orders[], sizing_rule, zone_scope, cutoff_ts                                                               |
| `pick.task.created` / `pick.task.completed` | v1      | task_id, order_id/batch_id, sku_id, qty, zone_id, mode, travel_distance_m, duration_s, mispick                      |
| `carton.packed`                             | v1      | carton_id, order_id, box_id, items[], cube_fill, actual_weight_kg, dim_weight_kg, billable_weight_kg                |
| `load.built`                                | v1      | load_id, trailer_type, stops[], pallets[], cube_util, weight_util, axle_loads[], lifo_valid                         |
| `shipment.tendered`                         | v1      | shipment_id, load_id, carrier_id, mode, service, rate_quote_id                                                      |
| `shipment.shipped`                          | v1      | shipment_id, ship_ts, door_id, on_time_ship                                                                         |
| `order.fulfillment.completed`               | v1      | order_id, cycle_time_s, line_fill, unit_fill, order_fill, on_time_ship, cost_breakdown{labor, carton, freight, vas} |
| `vas.job.completed`                         | v1      | job_id, type, output_sku_id, components[], labor_minutes, defect_qty                                                |
| `dock.allocation`                           | v1      | door_id, flow_type, from_ts, to_ts, changeover_charged_minutes, queue_wait_s                                        |

`dock.allocation.v1` is UNS-published, because dock door state is an OT-visible signal that the dock door sensors also report, and the disagreement between the two is itself an audit finding. The republication path is the bridge described at the head of section 4, not a `Network` handle held here (D-08).

### 4.6 Cross-dock

| Event                      | Version | Key fields                                                                                                   |
|----------------------------|---------|--------------------------------------------------------------------------------------------------------------|
| `crossdock.decision`       | v1      | pallet_id, decision, policy, score_flow, score_store, reason_codes[], connection_deadline_ts, target_load_id |
| `crossdock.staged`         | v1      | pallet_id, lane_id, staged_ts                                                                                |
| `crossdock.forced_putaway` | v1      | pallet_id, lane_id, dwell_s, dwell_limit_s                                                                   |
| `crossdock.connection`     | v1      | pallet_id, planned_load_id, made, dwell_s, dock_to_dock_s, stat_type="proportion_defective"                  |

### 4.7 Returns

| Event                          | Version | Key fields                                                                                                              |
|--------------------------------|---------|-------------------------------------------------------------------------------------------------------------------------|
| `return.created`               | v1      | rma_id, order_id, sku_id, qty, reason_code, causal_link{source_event_id, kind}, causal_sources_active[]                 |
| `return.received`              | v1      | rma_id, received_ts, door_id, queue_wait_s                                                                              |
| `return.triaged`               | v1      | rma_id, grade, inspect_minutes, inspector_id                                                                            |
| `return.disposition.completed` | v1      | rma_id, path, labor_minutes, material_cost, recovery_value, cycle_time_s, restock_lot_id                                |
| `returns.pnl.period`           | v1      | period, returns_units, recovery_rate, cost_per_return, mean_time_to_disposition_s, by_reason{}, causal_sources_active[] |

### 4.8 Transport

| Event                     | Version | Key fields                                                                                                                              |
|---------------------------|---------|-----------------------------------------------------------------------------------------------------------------------------------------|
| `lane.rate.quoted`        | v1      | quote_id, lane_id, mode, carrier_id, service, rate_source, linehaul, fuel, accessorials, total_cost, transit_days_p50, transit_days_p95 |
| `transport.leg.started`   | v1      | leg_id, shipment_id, lane_id, mode, carrier_id, planned_transit_s, depart_ts                                                            |
| `transport.leg.completed` | v1      | leg_id, actual_transit_s, arrive_ts, disruption_ids[], on_time                                                                          |
| `spot.index`              | v1      | lane_group_id, sim_date, index_value                                                                                                    |
| `transport.disruption`    | v1      | disruption_id, kind, lanes[], start, end, transit_multiplier, capacity_multiplier, cause_ref                                            |
| `freight.spend.period`    | v1      | period, cost_per_mile, cost_per_unit, cost_per_cwt, mode_mix{}, accessorial_share, by_lane[], by_carrier[]                              |

### 4.9 Promise

| Event                 | Version | Key fields                                                                                                        |
|-----------------------|---------|-------------------------------------------------------------------------------------------------------------------|
| `promise.quoted`      | v1      | promise_id, order_id, line_id, method, quoted_date, supply_refs[], confidence, is_repromise                       |
| `promise.outcome`     | v1      | promise_id, quoted_date, actual_ship_date, actual_delivery_date, met, days_late, stat_type="proportion_defective" |
| `atp.bucket.snapshot` | v1      | node_id, sku_id, bucket_date, on_hand, scheduled_receipts, in_transit, committed, atp, cumulative_atp             |

### 4.10 S&OE

| Event                 | Version | Key fields                                                                                      |
|-----------------------|---------|-------------------------------------------------------------------------------------------------|
| `soe.tick`            | v1      | tick_id, period_start, period_end, plan_snapshot_id                                             |
| `soe.exception`       | v1      | exception_id, type, severity, revenue_at_risk, service_impact{}, cost_impact, evidence[], state |
| `soe.action.applied`  | v1      | action_id, exception_id, kind, params{}, authority_tier, cost_estimate                          |
| `soe.action.measured` | v1      | action_id, treated_run_id, control_run_id, delta{}, hypothesis_test{}                           |

### 4.11 Network

| Event                    | Version | Key fields                                                                                                         |
|--------------------------|---------|--------------------------------------------------------------------------------------------------------------------|
| `site.registered`        | v1      | site_id, region_id, roles[], uns_prefix, facility_config_uri                                                       |
| `site.kpi.period`        | v1      | site_id, period, fill_rate, turns, throughput, labor_hours, cost_per_unit                                          |
| `network.kpi.period`     | v1      | period, network_fill_rate, network_turns, intersite_transfer_units, intersite_transfer_cost, load_balance_gini     |
| `intersite.transfer`     | v1      | transfer_id, from_site, to_site, sku_id, qty, reason, cost, lane_id                                                |
| `bridge.stats.period`    | v1      | site_id, period, events_forwarded, events_blocked, bytes_forwarded, bytes_if_raw, reduction_pct                    |
| `fl.round.started`       | v1      | round_id, model_id, participants[], aggregation="fedavg"                                                           |
| `fl.update`              | v1      | round_id, site_id, model_id, model_version, param_count, param_blob_uri, sample_count, metric_before, metric_after |
| `fl.round.completed`     | v1      | round_id, global_model_version, participants_n, held_out_score, centralised_baseline_score, degradation_pct        |
| `netdesign.solution`     | v1      | design_id, method, opened_sites[], assignment{}, predicted_cost_breakdown{}, service_coverage, scenario_id         |
| `netdesign.instantiated` | v1      | design_id, facility_config_uris[], twin_run_id, simulated_cost, predicted_cost, gap_pct, gap_decomposition{}       |

`site.kpi.period.v1` and `network.kpi.period.v1` are UNS-published and are exactly the class of message the broker bridge forwards.

### 4.12 Resilience

| Event                   | Version | Key fields                                                                                             |
|-------------------------|---------|--------------------------------------------------------------------------------------------------------|
| `stress.search.started` | v1      | search_id, space_hash, threshold{}, method, budget_trials, seed                                        |
| `stress.breaking_set`   | v1      | set_id, search_id, disruptions[], cardinality, total_magnitude, threshold_breached, tts_days, ttr_days |
| `disruption.propagated` | v1      | origin_node_id, affected_node_ids[], echelon_path[], lag_days, service_delta, cash_delta               |

### 4.13 Exogenous

| Event                      | Version | Key fields                                                                                                 |
|----------------------------|---------|------------------------------------------------------------------------------------------------------------|
| `weather.state`            | v1      | weather_region_id, sim_date, temp_c, temp_anomaly_c, precip_mm, snow_mm, wind_ms, severity_index, event_id |
| `weather.event`            | v1      | event_id, kind, regions[], start_date, end_date, intensity                                                 |
| `weather.coupling.applied` | v1      | subscriber, weather_region_id, sim_date, target, multiplier, input_state_hash                              |

`weather.state.v1` is UNS-published, because the ambient temperature and humidity sensors in the catalog derive their readings from it and an operator looking at the historian must see one weather truth.

---

## 5. Behavior

### 5.1 Demand signal generation (6a)

Per SKU, per region, per sim day the expected rate is

```
lambda = base * trend(t) * seasonal_annual(t) * dow(t) * promo_lift(t) * weather_mult(t) * shock(t)
```

with:

- `trend(t) = (1 + g) ** (t / 365)` where `g` is annual growth, per SKU or per category.
- `seasonal_annual(t)` a Fourier series with `k` harmonics on a 365.25-day period, coefficients per category.
- `dow(t)` seven multipliers per category, normalized to mean 1.0 so day-of-week never changes the annual total.
- `promo_lift(t)` from the promo calendar: a lift multiplier during the promo window, followed by a post-promo dip window implementing forward-buy pull-forward. The pull-forward is conservative: the dip integral equals `pull_forward_fraction` of the lift integral, so the promo does not create demand it did not steal, unless `incremental_fraction > 0` says it does. Before 6a16 exists, the calendar is a local stub read from `demand.yaml`; after 6a16, it is consumed from the marketing layer's promo events.
- `weather_mult(t)` from `twinflow-exogenous`, defaulting to 1.0 when weather is disabled.
- `shock(t)` from a rare-event process: Poisson arrivals with a magnitude distribution, used for genuine demand shocks distinct from promotions.

The realized count is drawn from Poisson, negative binomial, or zero-inflated Poisson depending on the SKU's declared `dist`. Intermittent SKUs use zero inflation with probability `p0`, which is what makes Croston-class methods necessary and what gives the SBC quadrant classifier real work.

Order construction: the realized units for a `(sku, region, day)` are split into orders. Wholesale orders take large multi-unit lines with a configured lines-per-order distribution and a pallet-quantity rounding rule. E-commerce orders take a lines-per-order distribution skewed to 1 and 2 lines and a units-per-line distribution skewed to 1, which is what makes each-picking and cartonisation meaningful. The channel split comes from `ChannelMix`, which is time-varying so the wholesale-versus-e-commerce balance the building fights over changes over the run.

Determinism: `twinflow-demand` draws only from the kernel child stream `demand`, further split per `(sku_id, region_id)` so adding a SKU does not change any other SKU's realized series. This matters: without per-entity stream splitting, a config change in one SKU perturbs every golden file.

### 5.2 Forecasting arena (6a)

The arena is a registry plus a backtest plus a ranking rule.

Registered baselines, all from `statsforecast`: `SeasonalNaive` (the reference every other model must beat), `WindowAverage`, `AutoETS`, `AutoARIMA`, `AutoTheta`, `MSTL` for the combined weekly and annual seasonality, `CrostonOptimized`, `CrostonSBA`, and `TSB` for intermittent series, and `ARIMAX` or `AutoETS` with exogenous regressors for the promo and weather features. Eligibility is by SBC quadrant: intermittent and lumpy series route to Croston-class methods, smooth and erratic to ETS/ARIMA/Theta. A model that is not eligible for a quadrant is not scored on it, and the arena table says so explicitly rather than reporting a meaningless number.

Challengers enter through `ChallengerProtocol`, which requires `fit(train) -> None`, `predict(h) -> array`, `model_id`, `deterministic`, and an optional `seed` setter. A global gradient-boosted model on lagged and calendar features registers here, built on `HistGradientBoostingRegressor` from scikit-learn and installed through the `learned` extra of 2.2, so the core forecasting install stays free of it (D-10). E31's foundation models (Chronos-2, TimesFM class) register here. Nothing in the arena knows the difference.

**Two target families, not one.** 6a requires the forecast to predict inbound and outbound volume,
which are different series with different owners. Outbound series are `(sku, region, channel)` daily
demand from `demand.signal.published.v1`. Inbound series are daily receipt volume per
`(supplier, node)` and per `(lane, node)`, in pallets and in units, built from `supply.lot.received.v1`
and `transport.leg.completed.v1`. Both families run through the same arena, the same backtest, and
the same metrics; they differ only in the target column and in which SBC quadrant their series land
in, and inbound series are usually lumpier because receipts arrive in PO-sized batches. The inbound
forecast is what the dock appointment plan of 5.19 is judged against, and reporting only the outbound
forecast would leave the more congestion-relevant of the two unmeasured.

Backtest: rolling-origin evaluation with configurable expanding or sliding window, `step` days between cutoffs, and horizon `H`. Every cutoff trains only on data at or before the cutoff. A test asserts no target-date row is present in any training slice for the cutoff that produced it, which is the leakage test that most portfolio forecasting code fails.

Metrics: MAPE, sMAPE, WAPE, MASE, RMSSE, mean error (bias), and Brown's tracking signal. MASE is scaled by the in-sample seasonal naive mean absolute error following Hyndman and Koehler (2006). WAPE is the primary ranking metric because the demand contains zeros and MAPE is undefined on them, and the arena documents that choice inline rather than silently dropping zero rows.

Ranking rule, which is the honest-evaluation requirement made executable: a challenger replaces the incumbent only if (a) it wins on WAPE at the target horizon, and (b) the Diebold-Mariano test with the Harvey-Leybourne-Newbold small-sample correction rejects equal predictive accuracy at alpha 0.05 in the challenger's favor, and (c) its absolute bias is not worse than the incumbent's by more than `bias_tolerance`. If any condition fails, the incumbent stays and the comparison table is published anyway. The README carries the table either way.

Intervals: split conformal prediction wrapped around whichever model wins, calibrated per horizon on a held-out calibration set. The inventory optimizer consumes the conformal quantiles, not a normal approximation, whenever conformal intervals are available for that series.

Forecast bias on a control chart: `BiasMonitor` publishes `forecast.error.observed.v1` per realized target date. The LSS engine plots scaled error on an I-MR chart per SKU class and per channel. Nelson rule 2, nine points in a row on the same side of the center line, is the bias-drift detector, and a violation produces a finding of type `forecast_bias_drift` with the evidence window. The rule set is the one published in Nelson (1984), "The Shewhart Control Chart: Tests for Special Causes", Journal of Quality Technology 16(4):237-239, and the engine owns the rule numbering; this package only declares the statistical type of the stream. The tracking signal is a second, independent detector, with the limit read from `forecast.tracking_signal_limit`, whose default is 4. That default is a working convention rather than a value this section takes from a published table, and open question 9.17 records that. Disagreement between the two detectors is itself reported, because a bias the control chart sees and the tracking signal misses is a different situation from the reverse.

### 5.3 Inventory optimization (6a) and MEIO (6a8)

**Lead times come from the twin.** `LeadTimeEstimator` consumes `leadtime.observed.v1` records produced by supplier receipts and transport legs. It fits lognormal and gamma candidates by maximum likelihood, tests each with Anderson-Darling, and accepts the better-fitting candidate if its p-value clears `leadtime.ad_alpha`. If neither clears, it falls back to an empirical bootstrap distribution. It never falls back to a normal approximation, because lead times are positive and right-skewed and a normal fit produces negative lead times in the tail. Below `min_observations`, the config prior is used and the emitted policy is flagged `prior=True`.

The p-value is obtained by parametric bootstrap, not from a table, and the reason is a real
statistical trap rather than fastidiousness. The parameters here are estimated from the same sample
the statistic is computed on, which shifts the null distribution of the Anderson-Darling statistic
away from the case-0 distribution whose critical values are the ones usually quoted. Stephens
(1974), "EDF Statistics for Goodness of Fit and Some Comparisons", Journal of the American
Statistical Association 69(347):730-737, tabulates the case-specific values for the distributions it
treats, and the lognormal fit uses them through the log transform to the normal case. The gamma fit
has no such table here, so its p-value comes from `leadtime.bootstrap_replicates` samples drawn from
the fitted gamma, refitted and re-tested each time, with the child stream fixed so the p-value is
reproducible. A run that used case-0 critical values on estimated parameters would accept fits it
must reject, and VAL-GATE LT-1 is written to catch exactly that.

**Safety stock.** Two service measures, both implemented, one chosen by config with no default:

- Cycle service level (Type 1): `SS = z_CSL * sqrt(L * sigma_D^2 + D_bar^2 * sigma_L^2)`, the standard demand-and-lead-time-variability form.
- Fill rate (Type 2): solve for `k` such that the expected shortage per replenishment cycle equals `Q * (1 - beta)`, where for normal demand over lead time the expected shortage is `sigma_L * G(k)` and `G(k) = phi(k) - k * (1 - Phi(k))` is the standardized normal loss function. `k` is found by Brent root finding on `G`.

The two answers differ, sometimes by a lot, and the reports always name which measure produced the number. That distinction is the first thing a competent reviewer probes.

**Reorder point and policies.** `ROP = D_bar * L + SS`. Policies implemented: `(s,Q)`, `(s,S)`, `(R,S)` periodic review, and pure base-stock. EOQ is implemented with an assumption checker: if the demand coefficient of variation over the review horizon exceeds `eoq.max_cv`, or a quantity-discount schedule is present, the engine refuses to emit an EOQ and emits a reason instead of a number. Refusing is the correct behavior and it is tested.

**Newsvendor** for single-period decisions (promotional buys, short-life SKUs): critical ratio `CR = Cu / (Cu + Co)`, `Q* = F^-1(CR)`, using the fitted demand distribution rather than assuming normality.

**Segmentation.** ABC by cumulative annual COGS with configurable cut points (defaults 80/95 percent cumulative). XYZ by demand coefficient of variation with configurable cut points (defaults CV <= 0.5 is X, CV <= 1.0 is Y, else Z). The Syntetos-Boylan-Croston quadrant uses average demand interval and squared coefficient of variation with the published cut-offs ADI = 1.32 and CV^2 = 0.49 from Syntetos, Boylan and Croston (2005), JORS 56(5):495-503. The quadrant drives forecast method eligibility and policy class, so the classifier is load-bearing rather than decorative.

**MEIO, guaranteed service time.** The primary model is the guaranteed-service framework of Graves and Willems (2000), M&SOM 2(1):68-83: each stage quotes an outbound service time, each stage's net replenishment time is its own processing time plus its inbound service time minus its outbound service time, and safety stock at a stage covers demand over its net replenishment time against a demand bound. The optimization over service times is a dynamic program on the spanning tree of the supply network. The implementation follows the paper's DP formulation, handles the general spanning-tree case, and refuses networks that are not spanning trees with an explicit error naming the offending cycle. The output is a full frontier: cost as a function of the customer-facing service target, so the question of where safety stock lives is answered as a curve, not a point.

**MEIO, stochastic service anchor.** `ClarkScarfSerial` implements the exact echelon base-stock optimum for a serial system following Clark and Scarf (1960), Management Science 6(4):475-490. It exists as a validation anchor: on a serial network under its assumptions, the two frameworks answer different questions and the repo says so in the README rather than pretending they agree. See open question 9.8.

**Risk pooling.** `RiskPooling` computes the analytic centralization benefit for independent identically distributed locations, which is the square-root law from Eppen (1979), Management Science 25(5):498-501, and the general correlated case numerically. The what-if "centralized versus forward-positioned stock" reports the service-versus-cost tradeoff with both the analytic and the simulated number side by side.

**MEIO, budget-constrained placement.** 6a8 asks a second question in its own words: holding cost is capped at a stated figure, so place inventory across the network to maximize service. `BudgetConstrainedPlacement` answers it as the dual of the frontier rather than as a separate model. The guaranteed-service dynamic program is solved once per candidate customer-facing service target on the grid of `meio.frontier_points`, each solve returning a total holding cost; the placement returned is the one with the highest service target whose holding cost is at or below `meio.holding_cost_budget`. `MeioSolution` records `holding_cost_budget` and `budget_binding`, which is true when the chosen point sits on the budget rather than at the unconstrained optimum. When even the lowest service target on the grid exceeds the budget, the engine returns no placement and raises a finding naming the shortfall in currency, because a budget that cannot buy the cheapest feasible network is a planning input error and inventing a placement for it would hide that. The grid is refined by bisection between the two adjacent frontier points that bracket the budget, to `meio.budget_tolerance` in currency, so the answer does not depend on how coarse the frontier grid happened to be.

**Validation against the twin.** Every MEIO solution is re-run in simulation under the derived base-stock levels, and `meio.solution.v1` carries `validated_against_sim` with the achieved service level and its Monte Carlo confidence interval. If the achieved service falls outside the interval containing the target, the solution is emitted with a warning finding rather than silently reported. This is the same reference-validation discipline the LSS engine uses, applied to planning.

**Disruption propagation across echelons** lives in `twinflow-resilience` and is described in 5.15.

### 5.4 Supplier network (6a2) and n-tier (E19)

The supplier tier drives what arrives. Each PO issued by the replenishment planner is acknowledged with a promised date drawn from the supplier's profile (which may differ from the requested date, and the difference is itself a scorecard input), then an ASN is sent, then a shipment moves on the transport network, then a receipt lands at the dock.

On-time and in-full are drawn jointly from the latent bivariate normal of 3.4, with the configured marginals `on_time_rate` and `in_full_rate` and latent correlation `otif_corr`, which defaults to a positive value because a supplier having a bad week tends to be both late and short. Independent draws produce an OTIF that is systematically too high. The test asserts two things and neither is a rank correlation: the two marginal frequencies reproduce the configured rates within their binomial confidence intervals, and the joint frequency of on-time and in-full reproduces the orthant probability `Phi_2(Phi^-1(p_1), Phi^-1(p_2); rho)` within its confidence interval. Kendall's tau is not asserted here, for the reason 3.4 gives: the arcsine identity that would relate it to `rho` needs continuous marginals, and two Bernoulli outcomes are tied almost everywhere, so a tau target would be a number with no meaning.

Supplier capacity is enforced, not decorative. Each supplier has a daily capacity, and a day whose open PO lines request more than that capacity is rationed by the `proportional` rule of 3.4, which publishes `supplier.capacity.rationed.v1` with the granted and shortfall quantities and the POs affected. Rationing pushes the unfilled remainder to the next day, which is what turns a capacity limit into a lead-time effect the scorecard can see, and INV-SUP-2 asserts the arithmetic and the order independence.

Defects: each received lot draws its defect count from `variability.supplier.lot_defect_count`, which is the overdispersed count model of the settled catalog and not a binomial, because defects cluster inside a lot and a binomial draw understates the tail that acceptance sampling exists to catch. Defective units are detected either at inbound inspection (with a detection probability that is itself a measurement-system property, feeding the MSA layer) or downstream, and a defect detected downstream traces back through genealogy to its `ReceiptLot`, its PO, and its supplier, updating the scorecard for the period in which the lot was received, not the period in which the defect was found. That retroactive attribution is what a real supplier quality manager insists on. The restatement is a record and never an overwrite: `supplier.scorecard.restated.v1` carries the value before, the value after, and the defect finding that triggered it, and INV-SUP-3 asserts that the current value of any period is the published value composed with its restatements in order.

Scorecards are computed per period, carry sample sizes, and declare their statistical type so the LSS engine picks p-chart for OTIF proportions, u-chart or c-chart for defect counts, and I-MR or Xbar-R for lead-time continuous data. Scorecard periods with a sample size below `scorecard.min_n` are emitted with `insufficient_sample=True` and are excluded from control limit calculation rather than plotted as if they were solid.

Disruption scenarios are first-class: `supplier.disruption.v1` with a capacity multiplier and a lead-time multiplier over a date window. The standard what-ifs from the source are catalogd scenarios: `supplier_b_down_two_weeks.yaml` and `supplier_a_leadtime_doubles.yaml`. Each is answered with service level, cost, and the dual-sourcing versus higher-safety-stock comparison expressed as resilience per dollar, computed by paired runs with common random numbers so the difference is the policy and not the seed.

**N-tier illumination (E19).** The supplier graph is n-tier from birth. Tier-1 suppliers are visible. Deeper edges start `unknown` and carry a `mapping_cost` and `mapping_effort_days`. A mapping action reveals a subset of edges from a chosen parent, with a reveal probability per edge, so mapping is an investment with an uncertain return rather than a free lookup.

The demonstration: several tier-1 suppliers share a hidden tier-2 source for a component class. When that tier-2 node goes down, all dependent tier-1s fail together. A scorecard fitted only on historical tier-1 performance cannot predict this, because historically the tier-1 failures were independent. The measurable claim is a correlation, and it is stated with the numbers that make it falsifiable. Across `network.mapping.demo_episodes` seeded episodes, the mean pairwise phi coefficient of tier-1 failure indicators is compared between a network with a shared tier-2 and an otherwise identical network without one. The noise floor is the standard error of that mean phi under the no-shared-tier-2 network, measured over the same episode count and checked into the fixture, and the claim is that the shared-tier-2 network's mean phi exceeds the other by more than 3 of those standard errors. The difference is reported with its confidence interval either way. What would falsify it: the two networks producing mean phi within the noise floor, which would mean the shared tier-2 is not propagating and the demonstration does not demonstrate anything.

The ROI of mapping is computed by paired simulation: run the same seeds with and without the map available to the planner, where having the map lets the planner pre-position buffer or dual-source against the concentration. The difference in expected loss, minus the mapping cost, is the ROI, reported with its confidence interval.

### 5.5 Outbound and e-commerce execution (6a3, 6a6)

**Release.** `WavePolicy` groups orders into waves at scheduled release times, with a sizing rule (`fixed_count`, `carrier_cutoff`, `zone_balanced`) and a wave scope. Wave completion gates packing for the wave's orders, which is what creates the characteristic wave sawtooth in labor utilization. `WavelessPolicy` releases orders continuously subject to a WIP cap per zone (a CONWIP rule), with a priority rule (`earliest_cutoff`, `contract_first`, `shortest_processing_time`). The comparison of the two on identical demand and identical seeds is a standard what-if, and the answer is published either way.

**Picking modes.** Discrete (one order at a time), batch (a cart carries `batch_size` orders, sorted after picking), zone (pick-and-pass or pick-and-sort across zones), cluster (a cart with per-order totes, no downstream sort), and goods-to-person (the AMR fleet from 1b brings the shelf to a station, so picker travel goes to zero and the constraint moves to AMR fleet size and station throughput). Mode is config. GTP requires the automation layer and is disabled with a clear error when the AMR fleet is absent from `facility.yaml`.

**Travel model.** For picker-to-goods modes, travel distance per pick tour is computed from the rack layout and the routing strategy: S-shape (traversal), return, midpoint, largest-gap, and an optimal router. The optimal router for a single-block layout implements the Ratliff and Rosenthal (1983) dynamic program, Operations Research 31(3):507-521. The heuristics follow the survey in De Koster, Le-Duc and Roodbergen (2007), EJOR 182(2):481-501. Travel distance feeds pick time through a walk speed and a per-pick handling time, so slotting changes (from 1b) show up as measurable pick-rate changes.

**Cartonisation.** Given an order's items, choose the box from `catalogs/cartons.yaml` that minimizes billable cost subject to geometric fit, weight limit, and compatibility rules (hazmat segregation, fragile-on-top, no mixing of temperature-controlled with ambient). Geometric fit is solved by a constructive extreme-point heuristic with rotations, and the result is verified by `FitChecker`, an independent implementation that only answers yes or no. Using two implementations means a packing bug cannot silently produce impossible cartons. Multi-box splitting is supported when no single box fits.

Dim weight: `dim_weight = L * W * H / dim_divisor`, with the divisor a config key per carrier and unit system. The shipped defaults are 139 cubic inches per pound and 5000 cubic centimetres per kilogram. Those are configured working values, not values this section takes from a carrier's published tariff, and the synthetic carrier catalog says so in its header; open question 9.16 records what calibrating them against a real tariff would need. Billable weight is the maximum of actual and dim weight. Carton fill rate is item cube over box cube and is a reported KPI, because void volume is what the dim-weight charge is taxing.

**Parcel rate shopping.** For each carton, quote every eligible carrier service on the destination zone, compute total landed parcel cost including fuel and residential surcharges, filter by the service days needed to meet the promise, and choose the cheapest feasible. The chosen and rejected quotes are both logged, so the savings from rate shopping is measurable rather than assumed.

**Trailer cubing and load building.** Pallets are assigned to trailers subject to cube, gross weight, per-axle weight, stackability, and, for multi-stop loads, LIFO order consistency with the stop sequence. Fill rate is reported as the binding one of cube utilization and weight utilization, with the binding constraint named, because "we run at 78 percent fill" means nothing without saying which dimension binds.

**Carrier assignment for TL and LTL.** Enumerate feasible carrier and mode combinations for the lane, quote each through `RateEngine`, filter by transit days against the promise, and select by the configured objective (`least_cost`, `least_cost_feasible`, `best_on_time_within_budget`). Contract commitments create a soft constraint: falling short of committed volume triggers a rate escalation at contract review, which is modeled and shows up in the freight spend analytics.

**Dock contention.** Every door request goes through `DockBroker`, which is the policy layer above the twin's door resources and never grants a door itself (3.5). Inbound receipts, outbound loading, returns intake, and cross-dock all queue for the same pool. Doors declare which flow types they accept, and switching a door's type charges `changeover_minutes`. Queue waits are recorded per flow type, so the interference between flows is directly measured rather than inferred. This is the mechanism behind the parcel-versus-pallet interference claim in 6a6: the two channels compete for doors, labor pools, and AMRs, and every contention point emits a wait time attributable to a flow type.

**Channel unit economics.** Every order accumulates an `OrderCostRecord` from the actual activity records: pick minutes times the picker's loaded rate, pack minutes, carton and void-fill material, VAS labor, freight from the actual rate quote, and an allocated share of dock and staging occupancy. Cost per order, cost per line, and labor minutes per order are reported per channel. These records are the input the finance layer's activity-based costing consumes, so channel profitability is computed from the same events the operation ran on.

**Peak-day chaos.** `chaos/peak_day.yaml` defines an hourly demand multiplier profile, compressed carrier cutoffs, elevated e-commerce channel share, and a follow-on elevated return rate in the subsequent weeks. It is a standard scenario in the catalog, run with a fixed seed, and its results are golden-filed.

### 5.6 Value-added services and postponement (E41 second half)

VAS lines are scheduled DC work content with their own labor pool, cycle-time distributions, and defect rates. Kitting consumes component SKUs and produces a kit SKU per a light bill of materials. Labeling and bundling transform a SKU in place. Light assembly is kitting with a longer cycle time and a higher defect rate. Defects raise quality findings through the same path as any other defect and so reach the QMS layer.

Postponement is a planning decision: `strategy: stock_finished | postpone` per kit SKU. Under `stock_finished`, safety stock is held on each finished variant. Under `postpone`, safety stock is held on the shared components and the kit is built to order, which pools the variant demand variability into the component. The analytic benefit for independent identically distributed variants is the square-root law again, which is the same Eppen result, and the general case is simulated. The cost side is the added per-order VAS labor and the added order cycle time, which can push orders past a carrier cutoff. The what-if reports both sides and the crossover point.

### 5.7 Cross-docking (6a5)

Every inbound pallet reaches a decision point at receipt. The rule policy flows a pallet when it is pre-allocated to an open outbound order whose departure is within `connection_window_hours`, a staging lane position is free, and the outbound door queue is under a threshold. The cost policy computes an expected cost for each branch:

```
cost_flow  = staging_occupancy_cost + P(miss) * miss_penalty + expedite_cost_if_missed
cost_store = putaway_labor + storage_cost_until_needed + retrieval_labor
```

where `P(miss)` is estimated from the current dock queue state and the remaining time to the outbound departure. The pallet flows when `cost_flow < cost_store`. The rule policy is the baseline the cost policy must beat, and both are run on identical seeds with the comparison published either way, in the same pattern the anomaly detection and dispatcher comparisons use.

Staging lanes are finite. A pallet that exceeds `dwell_limit_s` is force-put-away, which emits `crossdock.forced_putaway.v1`, consumes putaway labor, and counts as a cross-dock defect distinct from a missed connection.

Missed connection is the defining defect: a pallet planned to flow that does not make its planned outbound load. It is emitted as a proportion so the LSS engine plots it on a p-chart. Dock-to-dock time and staging dwell are continuous and go on I-MR or Xbar-R charts.

The flow-through sweep what-if raises the pre-allocated share from 20 to 40 to 60 percent and identifies the first binding constraint by ranking resources on utilization and on their contribution to total queueing delay. A controlled test injects a known constraint (a reduced staging lane count) and asserts the sweep names that constraint.

Inbound and outbound schedules must synchronize for cross-docking to work at all. The scheduler is behind `DockScheduleProvider`. A deterministic baseline provider ships with this section (fixed appointment windows from the replenishment plan and the outbound cutoffs). E12's optimizer replaces it through the same interface, and the improvement is measured against the baseline.

### 5.8 Returns and reverse logistics (6a4)

Returns are generated as a function of shipments, not of demand: for each shipped unit, a return is drawn with probability `return_rate(sku_class, channel)` and a return delay drawn from `variability.returns.delay`. The two configured rates combine multiplicatively and are clamped at 1.0, `return_rate = min(1.0, rate_by_sku_class[class] * rate_by_channel[channel] / rate_by_channel_baseline)`, where the baseline is the volume-weighted mean of the channel rates so that changing the channel mix alone does not move the overall return rate. Writing the combination down matters because the two tables are the levers the returns-spike what-if pulls, and a reader who guesses at addition gets a different answer. That construction is what makes the return stream lag the outbound stream realistically, and it is what makes returns arrive unpredictably relative to the current week's plan.

Reason codes are assigned by the causal rules in 3.7 rather than by a flat categorical draw. That is the difference between a Pareto chart that is decoration and a Pareto chart that points at a fixable cause.

Returns compete for doors through `DockBroker`, for triage labor through the labor pool, and for staging space. The competition is the point: a returns surge degrades outbound service through shared resources, and the twin measures the path.

Triage inspects (labor minutes drawn per reason code, since a damage claim takes longer than a remorse return), grades A/B/C/scrap, and dispositions. Each disposition path carries labor minutes, material cost, cycle time, and a recovery value as a fraction of original price. Restocked units emit `inventory.adjustment.v1` with a lot reference so genealogy stays closed.

The reverse P&L reports recovery rate, cost per return, and mean time to disposition, per period and per reason code. Reason codes are Pareto-charted by the LSS engine, and a finding fires when the top reason exceeds `returns.pareto_concentration_threshold` of total volume.

**Feedback into planning.** Restocked units are a supply source, not negative demand. The replenishment planner computes net requirements as forecast gross demand minus expected restock inflow, where expected restock inflow is a distributed lag on shipments: `E[restock_t] = sum_k shipments_{t-k} * return_rate * P(delay = k) * P(disposition = RESTOCK)`. The forecaster continues to forecast gross demand. Keeping the two separable is what makes the numbers auditable, and a test asserts that ignoring the restock inflow produces measurably higher inventory, which is the failure mode this models.

The returns spike what-if raises the return rate to 12 percent and reports the triage labor and staging space needed before outbound service level degrades, plus the recovery-versus-scrap split that E7's sustainability tier consumes as a circular-economy KPI.

### 5.9 Parcel and pallet interference (6a6)

The interference is not modeled as an abstraction; it emerges from three shared resources: dock doors through `DockBroker`, the labor pool through the twin's worker resources, and the AMR fleet through the automation layer. Each contention point records wait time attributed to the requesting flow type, so the question "what does adding e-commerce cost my wholesale service level" is answered by decomposing wholesale order cycle time into its waiting components and attributing each to the flow that occupied the resource. The staffing split answer comes from a sweep over labor allocation between the two channels, ranked by the combined service objective, with the LSS engine's hypothesis test on the before and after samples.

### 5.10 Transportation network (6a7)

**Mode selection.** For a shipment, enumerate feasible modes: TL when the load fills enough of a trailer that TL cost per unit beats LTL, LTL for mid-size freight, parcel for cartons under the parcel weight and dimension limits. Feasibility is filtered by transit days against the promise date. The selector reports the chosen mode, the runner-up, and the cost and service difference, so mode decisions are auditable.

**Rating.** TL is `max(min_charge, rate_per_mile * miles) + fuel_surcharge + accessorials`, with the rate coming from the contract tier matching the shipper's trailing volume, or from the spot market. LTL is rated from a class-based tariff with break weights and a discount off tariff, where the class comes from density through the synthetic density-to-class table. Parcel is rated by zone and billable weight with service-level and surcharge adders.

**Transit.** Base transit per lane and mode is lognormal. Disruption multipliers stack multiplicatively: weather severity along the lane's region path, spot-market tightness as a proxy for capacity crunches, and border or port delay on international lanes. A disruption also has a probability of a hard service failure, which produces a late delivery rather than a slow one.

**Spot market.** A mean-reverting process on the log rate per lane group, simulated with the exact OU transition so the discretisation is unbiased at any step size. The long-run mean is shifted by weather severity and by aggregate capacity utilization across the lane group, which is what makes the spot market move for reasons the rest of the twin can explain rather than moving for its own sake.

**Consolidation.** Orders and lanes are consolidated into multi-stop loads. The baseline is the Clarke and Wright (1964) savings heuristic, Operations Research 12(4):568-581. An exact branch-and-bound solver handles instances up to `consolidation.exact_max_stops` (default 10) and is used both as a production path for small problems and as the correctness oracle for the heuristic in tests.

**Freight spend analytics.** Cost per mile, cost per unit, cost per hundredweight, mode mix, accessorial share, lane scorecards, and carrier on-time rates, all per period, all with declared statistical types so the LSS engine charts them. Accessorial share is called out separately because accessorial creep is the classic hidden leak in freight spend.

**Network what-ifs.** Diesel up 20 percent shifts the fuel surcharge index and re-runs mode selection and consolidation, reporting the cost delta and any mode-mix shift. The zone-skip breakpoint what-if shifts the weight at which parcel gives way to LTL and reports the total-cost curve with the crossover. The carrier degradation what-if reduces a carrier's on-time rate by 10 percent and computes the indifference point between switching (with switching cost and onboarding transit variability) and renegotiating (with a rate concession that buys back the service gap in dollars).

### 5.11 ATP and CTP (E16)

ATP is computed over time buckets per `(node, sku)`. Discrete ATP for a bucket is on-hand plus scheduled receipts landing in that bucket minus commitments due in that bucket. Cumulative ATP is the running sum with look-ahead, which is what lets a promise consume a future receipt. Both are implemented, and the mode is config, because they give different answers and a system that only implements one is hiding a decision.

The promise flow: a line requests a quantity by a date. ATP is checked first. If ATP cannot cover it, CTP is asked: `CapacityPromiseProvider` (the factory's finite-capacity scheduler from 6a9, and the DC's own labor and dock capacity) returns the earliest date the quantity can be made available. The promise records which supply references it consumed, so the audit trail from a promise to the specific receipts backing it is complete.

Over-promising is prevented structurally: promises consume ATP buckets atomically inside the sim's single-threaded scheduler, and the invariant is asserted continuously. Allocation policy (fair share versus priority during shortage) is a hook: `AllocationPolicy` is a protocol this package calls, implemented here with a simple priority-class policy and replaced by 6a12's richer policy later.

Promise reliability is the customer-facing KPI: the fraction of promises met, tracked on a p-chart, plus the quoted-versus-actual delta in days on an I-MR chart. First promises and re-promises are tracked separately, because a system that re-promises until it is right can otherwise report perfect reliability.

### 5.12 S&OE weekly tick (E15)

Every `soe.cadence_days` (default 7) at `soe.tick_time`, the tick runs. `soe.tick_time` is a time of day on the simulated clock, resolved against the site's configured timezone and never against a wall clock (D-02), so a run started at any hour produces the same tick schedule.

1. Snapshot the plan of record. Before 6a16 exists, this is the replenishment plan plus the current forecast run plus the planned labor. After 6a16, it is the S&OP consensus. The `source` field records which.
2. Diff plan against simulated actuals for the elapsed period, at the granularity the plan was made at.
3. Detect exceptions and quantify each: revenue at risk (units at risk times price), service impact (orders and lines at risk of missing promise), cost impact (expedite or overtime cost implied).
4. Rank and rationalize. The exception queue passes through the LSS engine's alarm rationalization (deduplication, severity ranking, shelving), which is the reference-architecture requirement that the findings stream cannot flood. A supplier outage that generates 400 line-level exceptions collapses into one ranked exception with 400 pieces of evidence. Section 8.4 states what the queue does when that call is not yet bound.
5. Offer bounded corrective actions from `ActionRegistry`. Actions register themselves as their owning layer arrives: `expedite` needs the transport layer, `reallocate` needs multiple nodes, `substitute` needs substitution rules, `re_wave` needs the fulfillment layer, `de_expedite` needs an existing expedite. Bounds are per-action limits on cost and on quantity, enforced before application.
6. Apply the chosen action and measure it. Measurement branches the simulation at the tick checkpoint into a treated arm and a control arm with identical RNG child seeds. The control arm runs the untouched plan. The difference between arms is the action's effect with no seed noise, and the LSS engine runs the appropriate hypothesis test on the paired outcomes across replications.

The null-action test is the important one: applying an action with zero effect must produce a byte-identical event log to the control arm. If it does not, either the branching leaks state or a subsystem is drawing from a shared RNG stream, and the test catches both.

### 5.13 Disruption propagation across echelons (6a8)

A disruption at any node propagates downstream through the material flow with a lag equal to the transit and processing times on the path, and its severity at each downstream node is attenuated by the buffer at each intervening echelon. `EchelonPropagation` records, for each affected node, the path, the lag, and the service and cash deltas. That record is what answers the question 6a8 poses: which echelon's buffer actually saved us, and what did the others cost for nothing. <!-- docs-lint-ok FILLER-03 verbatim quotation of the source requirement text --> The answer is computed by paired runs with each echelon's buffer independently zeroed, which is a Shapley-style attribution over echelons for small networks and a one-at-a-time attribution with the interaction residual reported for larger ones.

### 5.14 Multi-site (E13)

`sites.yaml` registers sites, each pointing at its own `facility.yaml`. Each site runs its own broker with its own UNS prefix `enterprise/<enterprise>/<site>/...`. Site brokers bridge to an enterprise broker with a topic policy that forwards findings, KPI rollups, and birth/death certificates and blocks raw telemetry. `bridge.stats.period.v1` reports events and bytes forwarded against what raw forwarding would have cost, which is the measured bandwidth reduction number. The broker configuration and bridging mechanics belong to the IoT and UNS section; this package owns the topic policy schema, the site registry, and the KPI rollup.

Cross-site KPIs roll up per period. The overflow allocation question ("which site absorbs next week's overflow volume") is an assignment problem over sites subject to capacity, labor availability, and inter-site transfer cost, solved with the same MILP machinery as network design, then executed in the twin so the recommended answer is verified rather than asserted.

Federated learning: `FederatedRound` coordinates rounds, each site trains locally on its own telemetry, and `FederatedAggregator` combines updates by FedAvg (McMahan et al., 2017, AISTATS), weighting by local sample count. `fl.update.v1` carries model parameters and a sample count and nothing else. The privacy claim is enforced at the schema level and tested. The published result is the comparison of the federated model against a centrally trained model on the same data, on both IID and non-IID site partitions, with the degradation reported either way. Model training and the registry belong to the MLOps layer (E43); this package owns the round protocol and the aggregation.

### 5.15 Reverse stress testing (E20)

The disruption space is declared, not hard-coded: `DisruptionSpace` reads a schema of knobs, each with a target, a domain, and a magnitude cost that makes disruptions comparable so "minimal" is well defined. The same declaration feeds the chaos catalog, so a scenario and a search point are the same object.

Search proceeds in three stages, cheapest first:

1. Exhaustive over cardinality 1 and 2. Exact, and parallel across trials without touching determinism: each trial is its own simulation run with its own `run_id`, and the reduction over trial results is the sort of 2.12, so the number of workers changes how long the stage takes and never what it returns.
2. Optuna search over the full space, minimizing total disruption magnitude subject to a threshold breach, using the multi-objective sampler when both service and cash thresholds are in play.
3. Surrogate-accelerated search once E28 exists: the surrogate screens candidates, the full simulation confirms every reported breaking set. No breaking set is ever published on surrogate evidence alone.

For each breaking set, time-to-survive and time-to-recover are measured following the risk-exposure framing of Simchi-Levi et al. (2015), Interfaces 45(5):375-390. TTS runs the disruption with recovery actions disabled and records days to threshold breach. TTR enables recovery actions and records days to restored compliance.

Results feed back into the n-tier map: a low-cardinality breaking set that includes a hidden tier-2 node is the quantified argument for paying the mapping cost, which closes the loop with E19.

### 5.16 Weather (E40)

One process, one state, many subscribers. A seasonal climatological mean per region plus a vector autoregressive anomaly with a spatial correlation matrix `exp(-d_ij / corr_length_km)` produces daily temperature, precipitation, snow, and wind per region. A severity index in [0,1] summarizes the state for subscribers that need one number. Severe events are injected from the catalog with a footprint of regions, a duration, and an intensity, and they override the anomaly process for their window.

Couplings, each a registered function with its own config block and its own test:

- Demand: category demand multiplier as a function of temperature anomaly and severity, per the SKU's `weather_sensitivity`.
- Transit: transit-time multiplier and hard-failure probability along a lane's region path, taking the maximum severity encountered.
- Yard: unload and load rate multiplier plus a dock door cycle penalty during precipitation and high wind.
- HVAC energy: heating and cooling degree days driving building load, which feeds E7's energy KPIs. The definition is the one NOAA's Climate Prediction Center publishes for its degree-day products: the daily mean is the average of the daily maximum and minimum temperature, and 65 degrees Fahrenheit is the base for both heating and cooling degree days, with heating degree days summing the negative differences from that base and cooling degree days the positive ones. The computation runs in Fahrenheit to match that definition; 18.3 Celsius is a rounded conversion of the base and is never the number the sum is taken against, because rounding the base before summing moves every daily term.
- Slip risk: a multiplier on the incident probability in 6a10's safety model during precipitation and ice.
- Ambient sensors: the catalog's ambient temperature, humidity, and dew-point sensors derive from the outdoor state through a building thermal lag, so the weather is visible in raw telemetry and not only in aggregates.

`ClimateTrend` shifts the climatological mean and the severe-event frequency per decade, which is what makes long-horizon stress tests meaningful.

### 5.17 VMI and consignment (E41 first half)

Every inventory position carries an owner. Under consignment, stock physically at the DC is owned by the supplier until consumption. Consumption (a pick for shipment, or an issue to a VAS line) triggers `inventory.ownership.transferred.v1`, which is what the financial twin turns into a payable, replacing the receipt-triggered payable of the owned model. That single change is the whole billing difference consignment implies, and modeling it as an ownership transfer event rather than a special case keeps the GL derivation uniform.

The supplier manages min and max bands. It sees a consumption signal whose cadence is config (`real_time`, `daily`, `weekly`) and whose accuracy is bounded by the DC's inventory record accuracy. That second point is the one worth building: if record accuracy is 92 percent, the supplier replenishes against a wrong picture, and the twin can quantify how much of VMI's benefit depends on the accuracy of the consumption signal. Record accuracy is a property the RFID layer directly improves, so the chain from tag reads to VMI viability is measurable end to end.

The VMI case is quantified on three axes: working capital shifted upstream (the DC's carrying cost drops, the supplier's rises, and the financial twin reports both), stockouts reduced by visibility, and the signal infrastructure required. The tests assert the direction of each effect and the monotonicity of stockouts in record accuracy.

### 5.18 Strategic network design (E42)

Inputs: demand by region with geography, candidate sites with fixed cost, capacity, labor rate and availability, and real estate cost, freight rates from `twinflow-transport`, and service targets expressed as the fraction of demand within N transit days.

`CenterOfGravity` implements Weiszfeld's algorithm for the weighted 1-median under Euclidean distance, with an explicit note in the code and the report that the naive demand-weighted centroid minimizes squared distance rather than distance and is the wrong answer to the question usually asked of it. Both are computed and both are reported, with the difference shown.

`FacilityLocationMilp` is a capacitated facility location model with service constraints: binary open decisions per candidate, continuous flow from candidate to region, minimizing fixed cost plus transport plus handling plus labor, subject to demand satisfaction, capacity, and a service-coverage constraint. Solved with HiGHS through `highspy`. For instances at or below `netdesign.exact_max_candidates` (default 8 candidates, 20 regions), a brute-force enumeration runs in tests as the correctness oracle.

`RobustDesign` solves under a scenario set (demand scenarios, tariff scenarios from E14, freight-rate scenarios) and reports both the minimum-expected-cost design and the minimax-regret design. They differ, and showing that they differ is the point.

`DesignInstantiator` writes each candidate design out as one or more `facility.yaml` files plus a `sites.yaml`, which the operational twin then runs. `netdesign.instantiated.v1` reports the simulated cost against the MILP's predicted cost, with the gap decomposed into congestion, labor queueing, dock contention, and residual. The gap is the deliverable: a network design model that omits queueing systematically under-predicts cost, and this is the repo that measures by how much.

### 5.19 The three planning what-ifs the source names by number

The source states three planning questions in the numbers a planner would use, and each needs a
named mechanism rather than a general claim that the what-if engine can answer questions. Each runs
as a paired comparison against a base run on the same seed, so the difference is the change and not
the noise, and each has an end-to-end scenario in 7.5.

**The 15 percent demand surge (6a).** The scenario multiplies the expected demand rate by 1.15 from
a stated sim date to the end of the horizon, leaving every other stream identical. It reports four
quantities, which are the four the source asks for. Dock capacity is reported as the door
utilization and the mean and 95th-percentile queue wait per flow type from `dock.allocation.v1`. AMR
utilization is reported as the fleet's busy fraction and task queue depth, read from the automation
layer's own events, because that fleet belongs to 1b and this section consumes rather than owns it.
Stockout risk is reported as the fill rate and the count of stockout hours per SKU class. The fourth
is the answer to the question the other three set up: `ReplenishmentPlanner` is re-run with the
service target held fixed and the demand distribution updated to the surged one, and the difference
in safety stock per SKU class is the absorbing quantity, reported in units and in currency. The
surge is applied to the demand rate rather than to the order stream so the forecast sees it as a
level shift it must detect, which is what makes the propagation into congestion real. When the AMR
fleet is absent from `facility.yaml`, the AMR row is reported as unavailable with the reason, never
as zero.

**The carrier-cutoff shift (6a3).** The scenario moves the outbound carrier cutoff later, with 16:00
to 18:00 as the shipped default pair, and answers what it costs. Moving the cutoff later admits
orders that previously fell to the next day, which raises same-day volume, compresses the pick, pack
and load window against a fixed carrier departure, and changes the wave schedule. The comparison
reports the change in orders shipped same day, in order cycle time, in labor hours and overtime
hours, in dock queue wait on the outbound flow type, in the on-time ship rate against the promise,
and in cost per order from `OrderCostRecord`. It also reports the failure mode that makes the
question interesting: the count of orders released under the later cutoff that missed the carrier
departure anyway, because a cutoff a building cannot physically serve buys nothing and costs
overtime. Wave sizing under `carrier_cutoff` is re-derived from the shifted cutoff rather than held
fixed, since holding it fixed would answer a different question.

**Budget-constrained inventory placement (6a8).** The scenario caps holding cost at a stated figure
and asks which nodes hold inventory to maximize service. It runs `BudgetConstrainedPlacement` from
5.3, then validates the returned placement in the twin under the same discipline every MEIO solution
gets, and reports the achieved service with its confidence interval next to the analytic prediction.
The deliverable is the pair: the placement, and the gap between what the model promised and what the
simulated network delivered. It also reports which echelon the budget bought the last unit of
service at, which is the operational reading of the binding constraint.

---

## 6. Configuration

Every config validates at load against a published JSON Schema with line-numbered, suggestion-bearing errors (C5). `just validate` runs all validators. Every key below has a schema entry with a type, a range, and a required flag. Keys with no safe default are declared required and have no default, so a silent wrong answer is impossible.

Files:

- `facility.yaml`: per-site operational configuration. This section reads the blocks named below.
- `configs/demand.yaml`, `configs/planning.yaml`, `configs/suppliers.yaml`, `configs/supplier_network.yaml`, `configs/outbound.yaml`, `configs/ecommerce.yaml`, `configs/crossdock.yaml`, `configs/returns.yaml`, `configs/transport.yaml`, `configs/lanes.yaml`, `configs/carriers.yaml`, `configs/promise.yaml`, `configs/soe.yaml`, `configs/sites.yaml`, `configs/netdesign.yaml`, `configs/weather.yaml`, `configs/vmi.yaml`.
- `catalogs/cartons.yaml`, `catalogs/trailers.yaml`, `catalogs/freight_classes.synthetic.yaml`, `catalogs/disruption_space.yaml`.
- `chaos/peak_day.yaml`, `chaos/supplier_b_down_two_weeks.yaml`, `chaos/supplier_a_leadtime_doubles.yaml`, `chaos/supplier_a_capacity_halved.yaml`, `chaos/demand_surge_15pct.yaml`, `chaos/carrier_cutoff_shift.yaml`, `chaos/meio_budget_cap.yaml`, `chaos/returns_spike.yaml`, `chaos/diesel_up_20pct.yaml`, `chaos/winter_storm.yaml`. Each is a scenario overlay on the configs above, validated against the same schemas, and each is the input to a named scenario in 7.5.

Selected keys with types and validation rules. The full schema is the normative source; this is the shape.

Every dotted config key named anywhere in this section has a row below or in the settled catalog,
and `test_every_config_key_named_in_the_spec_has_a_schema_entry` reads the dotted key names out of
this document and fails on one that has no schema entry. A key with no default that is also not marked
required is the defect that check exists to catch, because it is the shape a silent wrong answer
takes. Keys whose home is `docs/design/variability-and-faults.md`, every `variability.*` key, are
not restated here; the rows below reference them and never redefine them.

### 6.1 `demand.yaml`

| Key                                | Type                                                                   | Rule                                                                       |
|------------------------------------|------------------------------------------------------------------------|----------------------------------------------------------------------------|
| `horizon_days`                     | int                                                                    | required, >= 28                                                            |
| `skus[].sku_id`                    | str                                                                    | required, unique                                                           |
| `skus[].base_units_per_day`        | float                                                                  | required, > 0                                                              |
| `skus[].dist`                      | enum poisson/negbin/zip                                                | required                                                                   |
| `skus[].dispersion`                | float                                                                  | required when dist=negbin, > 0                                             |
| `skus[].p0`                        | float                                                                  | required when dist=zip, in [0,1)                                           |
| `skus[].weather_sensitivity`       | float                                                                  | default 0.0, in [-2,2]                                                     |
| `skus[].annual_growth`             | float                                                                  | default from the category, in [-0.5, 2.0]                                  |
| `categories[].annual_growth`       | float                                                                  | required, in [-0.5, 2.0]                                                   |
| `categories[].seasonal_harmonics`  | int                                                                    | default 3, in [1,6]                                                        |
| `categories[].dow_multipliers`     | list[float] len 7                                                      | mean must equal 1.0 within 1e-6, else error naming the offending category  |
| `promo.calendar[]`                 | list of (promo_id, skus, start, end, lift_multiplier, dip_window_days) | dates ascending, windows per SKU must not overlap, lift_multiplier > 0     |
| `promo.pull_forward`               | DistSpec reference                                                     | must name `variability.demand.forward_buy`; the fraction is drawn, not set |
| `promo.cannibalisation`            | DistSpec reference                                                     | must name `variability.demand.cannibalisation`                             |
| `shock.arrival_rate_per_year`      | float                                                                  | default 2.0, >= 0                                                          |
| `shock.magnitude`                  | DistSpec                                                               | required when `arrival_rate_per_year > 0`, support must exclude 0          |
| `channel_mix.schedule[]`           | list of (date, wholesale_share)                                        | shares in [0,1], dates ascending                                           |
| `orders.wholesale.lines_per_order` | DistSpec                                                               | required                                                                   |
| `orders.wholesale.units_per_line`  | DistSpec                                                               | required, integer support                                                  |
| `orders.wholesale.pallet_round_to` | int                                                                    | default 1, > 0; line quantities round up to this multiple                  |
| `orders.ecommerce.lines_per_order` | DistSpec                                                               | required                                                                   |
| `orders.ecommerce.units_per_line`  | DistSpec                                                               | required, integer support                                                  |

`promo.incremental_fraction` is not a key. It was one in an earlier draft, alongside a rule that it
and `pull_forward_fraction` sum to 1.0, which contradicts 3.1: the incremental share is the residual
after pull-forward and cannibalisation, both of which are drawn per promotion from the settled
catalog rather than configured. Configuring the residual would let a config assert a decomposition
the generator did not produce.

### 6.2 `planning.yaml`

| Key                                   | Type                                       | Rule                                                               |
|---------------------------------------|--------------------------------------------|--------------------------------------------------------------------|
| `forecast.granularity`                | enum daily/weekly                          | default daily                                                      |
| `forecast.horizon_days`               | int                                        | required, >= 7                                                     |
| `forecast.backtest.window`            | enum expanding/sliding                     | default expanding                                                  |
| `forecast.backtest.step_days`         | int                                        | default 7, > 0                                                     |
| `forecast.backtest.min_train_days`    | int                                        | required, >= 2 * seasonal period                                   |
| `forecast.ranking_metric`             | enum wape/mase/rmsse                       | default wape                                                       |
| `forecast.dm_alpha`                   | float                                      | default 0.05, in (0, 0.2]                                          |
| `forecast.bias_tolerance`             | float                                      | default 0.02                                                       |
| `forecast.conformal.alpha`            | float                                      | default 0.10, in (0,0.5)                                           |
| `forecast.conformal.calibration_days` | int                                        | default 60, >= 30                                                  |
| `forecast.tracking_signal_limit`      | float                                      | default 4.0, > 0; see open question 9.17                           |
| `forecast.target_families`            | list[enum outbound_demand/inbound_receipt] | default both; an empty list is rejected                            |
| `inventory.service_measure`           | enum cycle_service_level/fill_rate         | **required, no default**                                           |
| `inventory.service_target`            | float                                      | required, in (0,1)                                                 |
| `inventory.review_period_days`        | int                                        | required for R,S policies                                          |
| `inventory.policy_by_segment`         | map segment -> policy_type                 | every ABC-XYZ cell must be covered, error names uncovered cells    |
| `inventory.eoq.max_cv`                | float                                      | default 0.5                                                        |
| `planning.appointment_min_pallets`    | int                                        | default 4, > 0; PO proposals at or above this need a booked window |
| `leadtime.min_observations`           | int                                        | default 30, >= 10                                                  |
| `leadtime.ad_alpha`                   | float                                      | default 0.05                                                       |
| `leadtime.bootstrap_replicates`       | int                                        | default 2000, >= 500; the parametric-bootstrap size of 5.3         |
| `segmentation.abc_cutoffs`            | list[float] len 2                          | ascending, in (0,1)                                                |
| `segmentation.xyz_cutoffs`            | list[float] len 2                          | ascending, > 0                                                     |
| `segmentation.sbc.adi_cutoff`         | float                                      | default 1.32                                                       |
| `segmentation.sbc.cv2_cutoff`         | float                                      | default 0.49                                                       |
| `meio.method`                         | enum gst_dp/clark_scarf_serial/sim_search  | default gst_dp                                                     |
| `meio.validate_against_sim`           | bool                                       | default true; setting false raises a warning finding               |
| `meio.frontier_points`                | int                                        | default 9, >= 3                                                    |
| `meio.holding_cost_budget`            | Decimal                                    | optional; when present, `BudgetConstrainedPlacement` runs          |
| `meio.budget_tolerance`               | Decimal                                    | default 0.01 of the budget, > 0; the bisection stop of 5.3         |

### 6.3 `suppliers.yaml` and `supplier_network.yaml`

| Key                                  | Type                                 | Rule                                                              |
|--------------------------------------|--------------------------------------|-------------------------------------------------------------------|
| `suppliers[].supplier_id`            | str                                  | required, unique                                                  |
| `suppliers[].tier`                   | int                                  | required, >= 1                                                    |
| `suppliers[].country_of_origin`      | ISO-3166 alpha-2                     | required                                                          |
| `suppliers[].lead_time`              | DistSpec                             | required, support must be positive                                |
| `suppliers[].on_time_rate`           | float                                | required, in [0,1]                                                |
| `suppliers[].in_full_rate`           | float                                | required, in [0,1]                                                |
| `suppliers[].otif_corr`              | float                                | default 0.4, in [-1,1]                                            |
| `suppliers[].defect_rate_ppm`        | float                                | required, in [0,1e6]                                              |
| `suppliers[].capacity_per_day`       | int                                  | required, > 0                                                     |
| `suppliers[].price_volume_curve[]`   | list[(min_qty, unit_price)]          | min_qty ascending, prices non-increasing                          |
| `suppliers[].is_vmi`                 | bool                                 | default false                                                     |
| `suppliers[].rationing_rule`         | enum proportional/priority_then_fcfs | default proportional                                              |
| `scorecard.period`                   | enum week/month                      | default month                                                     |
| `scorecard.min_n`                    | int                                  | default 20                                                        |
| `scorecard.restate_on_late_defect`   | bool                                 | default true; false is rejected when genealogy is enabled         |
| `network.edges[].visibility`         | enum unknown/inferred/confirmed      | default unknown for tier >= 2                                     |
| `network.edges[].share`              | float                                | shares per (parent, component_class) must sum to 1.0 within 1e-9  |
| `network.mapping.reveal_probability` | float                                | default 0.6, in (0,1]                                             |
| `network.mapping.demo_episodes`      | int                                  | default 200, >= 50; the episode count of the demonstration in 5.4 |

### 6.4 `outbound.yaml` and `ecommerce.yaml`

| Key                                | Type                                                           | Rule                                                                         |
|------------------------------------|----------------------------------------------------------------|------------------------------------------------------------------------------|
| `release_policy`                   | enum wave/waveless                                             | required                                                                     |
| `wave.schedule[]`                  | list[time]                                                     | required when wave, ascending, unique                                        |
| `wave.sizing_rule`                 | enum fixed_count/carrier_cutoff/zone_balanced                  | required when wave                                                           |
| `waveless.wip_cap_per_zone`        | int                                                            | required when waveless, > 0                                                  |
| `picking.mode`                     | enum discrete/batch/zone/cluster/goods_to_person               | required                                                                     |
| `picking.batch_size`               | int                                                            | required when batch or cluster, > 1                                          |
| `picking.routing`                  | enum s_shape/return/midpoint/largest_gap/optimal               | default s_shape                                                              |
| `picking.walk_speed_m_s`           | float                                                          | default 1.2, > 0                                                             |
| `picking.handling_time_per_pick_s` | DistSpec                                                       | required, positive support                                                   |
| `cartonisation.dim_divisor_in3_lb` | float                                                          | default 139                                                                  |
| `cartonisation.dim_divisor_cm3_kg` | float                                                          | default 5000                                                                 |
| `cartonisation.allow_split`        | bool                                                           | default true                                                                 |
| `docks.doors[].types_allowed`      | list[enum inbound/outbound/returns/crossdock]                  | required, non-empty, unique, stored and serialized in ascending order (D-03) |
| `docks.changeover_minutes`         | int                                                            | default 15, >= 0                                                             |
| `carrier.cutoff_times[]`           | list of (carrier_id, time)                                     | required, one per carrier used on outbound                                   |
| `carrier.objective`                | enum least_cost/least_cost_feasible/best_on_time_within_budget | default least_cost_feasible                                                  |
| `load.axle_limits_kg`              | list[float]                                                    | required per trailer type                                                    |
| `vas.lines[].type`                 | enum kitting/labeling/bundling/light_assembly                  | required                                                                     |
| `vas.lines[].cycle_time`           | DistSpec                                                       | required                                                                     |
| `postponement.strategy_by_sku`     | map sku -> enum stock_finished/postpone                        | unknown SKUs rejected by name                                                |

### 6.5 `crossdock.yaml`, `returns.yaml`

| Key                                      | Type                    | Rule                                  |
|------------------------------------------|-------------------------|---------------------------------------|
| `crossdock.preallocated_share`           | float                   | required, in [0,1]                    |
| `crossdock.policy`                       | enum rule/cost          | default cost                          |
| `crossdock.connection_window_hours`      | float                   | required, > 0                         |
| `crossdock.lanes[].capacity_positions`   | int                     | required, > 0                         |
| `crossdock.lanes[].dwell_limit_s`        | int                     | required, > 0                         |
| `crossdock.miss_penalty`                 | Decimal                 | required when policy=cost             |
| `returns.rate_by_sku_class`              | map class -> float      | values in [0,1]                       |
| `returns.rate_by_channel`                | map channel -> float    | values in [0,1]                       |
| `returns.delay`                          | DistSpec reference      | must name `variability.returns.delay` |
| `returns.causal_uplift`                  | map ReasonCode -> float | >= 1.0                                |
| `returns.disposition.recovery_fraction`  | map path -> float       | in [0,1]                              |
| `returns.pareto_concentration_threshold` | float                   | default 0.4                           |

The base reason mix has no key here. It is `variability.returns.reason_mix` in the settled catalog,
which draws the mix per lot and channel rather than fixing one prior vector, and an earlier draft
named a second key `returns.reason_priors` for the same concept. Two names for one concept is the
defect that makes a config silently ignore half of itself.

### 6.6 `transport.yaml`, `lanes.yaml`, `carriers.yaml`

| Key                               | Type                                    | Rule                                                     |
|-----------------------------------|-----------------------------------------|----------------------------------------------------------|
| `lanes[].distance_km`             | float                                   | required, > 0                                            |
| `lanes[].base_transit`            | map mode -> DistSpec                    | required for each allowed mode                           |
| `lanes[].weather_region_path`     | list[str]                               | each must exist in `weather.yaml`                        |
| `carriers[].contract.rate_basis`  | enum per_mile/per_cwt_class/parcel_zone | required when contract present                           |
| `carriers[].contract.tiers[]`     | list[(min_volume, rate)]                | min_volume ascending, rate non-increasing                |
| `carriers[].contract.expiry_date` | date                                    | must be after run start                                  |
| `spot.theta`                      | float                                   | default 0.15, > 0                                        |
| `spot.sigma`                      | float                                   | default 0.25, > 0                                        |
| `spot.mu_log`                     | float                                   | required                                                 |
| `spot.weather_beta`               | float                                   | default 0.3                                              |
| `consolidation.exact_max_stops`   | int                                     | default 10, in [2,14]                                    |
| `mode.parcel_max_weight_kg`       | float                                   | default 31.75                                            |
| `mode.parcel_max_dims_cm`         | list[float] len 3                       | required, each > 0; the parcel dimension filter of 5.10  |
| `mode.parcel_max_girth_cm`        | float                                   | required, > 0; length plus twice width plus twice height |
| `fuel.index_baseline`             | float                                   | required                                                 |

### 6.7 `promise.yaml`, `soe.yaml`

| Key                      | Type                              | Rule                                                                                 |
|--------------------------|-----------------------------------|--------------------------------------------------------------------------------------|
| `atp.mode`               | enum discrete/cumulative          | required                                                                             |
| `atp.bucket_days`        | int                               | default 1, > 0                                                                       |
| `atp.horizon_days`       | int                               | required, >= forecast horizon                                                        |
| `ctp.enabled`            | bool                              | default true                                                                         |
| `promise.tolerance_days` | int                               | default 0, >= 0                                                                      |
| `soe.cadence_days`       | int                               | default 7, > 0                                                                       |
| `soe.tick_time`          | time                              | required                                                                             |
| `soe.actions_enabled`    | list[str]                         | every entry must be registered in ActionRegistry, error names unknown actions        |
| `soe.action_bounds`      | map action -> {max_cost, max_qty} | required for every enabled action                                                    |
| `soe.control_arm`        | bool                              | default true; false emits a warning finding because measurement becomes uncontrolled |

### 6.8 `sites.yaml`, `netdesign.yaml`, `weather.yaml`, `vmi.yaml`

| Key                                          | Type                        | Rule                                                                                   |
|----------------------------------------------|-----------------------------|----------------------------------------------------------------------------------------|
| `sites[].site_id`                            | str                         | required, unique                                                                       |
| `sites[].facility_config_uri`                | path                        | must exist and validate                                                                |
| `sites[].uns_prefix`                         | str                         | must match the ISA-95 topic pattern                                                    |
| `bridge.forward`                             | list[topic glob]            | required, non-empty                                                                    |
| `bridge.block`                               | list[topic glob]            | forward and block must not both match any concrete test topic in the schema's test set |
| `federated.rounds`                           | int                         | default 10, > 0                                                                        |
| `federated.min_participants`                 | int                         | default 2, >= 2                                                                        |
| `federated.iid_tolerance`                    | float                       | default 0.02, > 0; the IID acceptance band of VAL-GATE FL-2                            |
| `netdesign.candidates[]`                     | list                        | required, non-empty                                                                    |
| `netdesign.service_days`                     | int                         | required, > 0                                                                          |
| `netdesign.service_coverage_target`          | float                       | required, in (0,1]                                                                     |
| `netdesign.exact_max_candidates`             | int                         | default 8                                                                              |
| `netdesign.scenarios[]`                      | list[scenario ref]          | each must resolve                                                                      |
| `weather.regions[]`                          | list with lat/lon           | required                                                                               |
| `weather.corr_length_km`                     | float                       | default 400, > 0                                                                       |
| `weather.severe_events[]`                    | list                        | each kind must exist in the catalog                                                    |
| `weather.climate_trend.warming_c_per_decade` | float                       | default 0.0                                                                            |
| `weather.couplings_enabled`                  | list[str]                   | subset of registered couplings                                                         |
| `vmi.signal_cadence`                         | enum real_time/daily/weekly | required when any supplier is_vmi                                                      |
| `vmi.record_accuracy`                        | float                       | default 1.0, in (0,1]                                                                  |
| `vmi.min_band` / `vmi.max_band`              | map sku -> int              | max must exceed min                                                                    |

### 6.9 `catalogs/disruption_space.yaml` and the stress search

| Key                                 | Type                                 | Rule                                                                                           |
|-------------------------------------|--------------------------------------|------------------------------------------------------------------------------------------------|
| `knobs[].knob_id`                   | str                                  | required, unique                                                                               |
| `knobs[].target`                    | enum supplier/lane/site/labor/demand | required                                                                                       |
| `knobs[].domain`                    | {min, max} or {false, true}          | required; a continuous domain must have min < max                                              |
| `knobs[].magnitude_cost`            | float                                | required, > 0; what makes "minimal" comparable across knobs                                    |
| `stress.thresholds.service`         | float                                | required, in (0,1)                                                                             |
| `stress.thresholds.cash`            | Decimal                              | optional; rejected with a named reason until E22 exists (open question 9.13)                   |
| `stress.exhaustive_max_cardinality` | int                                  | default 2, in [1,3]                                                                            |
| `stress.budget_trials`              | int                                  | required, > 0; a fixed count, never a wall-clock budget (D-04)                                 |
| `stress.confirm_with_full_sim`      | bool                                 | default true; false is rejected, because no breaking set publishes on surrogate evidence alone |
| `stress.tts_horizon_days`           | int                                  | required, > 0                                                                                  |
| `stress.ttr_horizon_days`           | int                                  | required, > 0, >= `stress.tts_horizon_days`                                                    |

---

## 7. Testing

Test tiers follow C4: fast unit, property-based invariants, seeded end-to-end with golden files, each with a runtime budget declared in `justfile`. Every VALIDATION GATE below names its published reference and the tolerance asserted.

Where a gate depends on a published table, the expected values live in a small checked-in extract under `tests/reference/`, cited in a header comment with the full source, never bulk-redistributed. Where a published number is not freely redistributable, the gate is paired with an independent numerical cross-check that stands alone.

### 7.1 Runtime budgets

Doctrine D-13 requires a test suite to fit the budget its own document sets, and requires the
arithmetic to be asserted rather than discovered as a timeout. This section's heavy checks do not fit
one job, so they run in two profiles and every test declares which profile it belongs to.

| Tier             | Profile    | Budget | Command                                        |
|------------------|------------|--------|------------------------------------------------|
| unit             | per-commit | 90 s   | `just test-unit planning-supply`               |
| property         | per-commit | 240 s  | `just test-prop planning-supply`               |
| e2e seeded       | per-commit | 900 s  | `just test-e2e planning-supply`                |
| validation gates | per-commit | 600 s  | `just test-valgates planning-supply`           |
| validation gates | nightly    | 3600 s | `just test-valgates planning-supply --nightly` |
| e2e seeded       | nightly    | 3600 s | `just test-e2e planning-supply --nightly`      |

The per-commit profile runs every test at its reduced replication count, which is stated per test
below and is the count the tolerance in that test is derived from. The nightly profile runs the full
replication counts. A test never changes what it asserts between profiles, only how many
replications it draws, and its tolerance is recomputed from the replication count so a reduced run
is not a looser run pretending to be the same one.

`test_declared_budgets_sum_within_their_job` reads the per-test budget declarations out of the test
registry and fails when a tier's declared total exceeds the tier's budget in either profile. A
scenario that grows past its budget then fails as a defect that names itself, rather than as a
timeout that names nothing. Applying D-13 to the two longest checks here: the M/G/1 queueing gate
runs 30 replications of 100,000 arrivals nightly and 5 replications of 20,000 arrivals per commit,
and the weather spatial-correlation gate runs 10,000 simulated days nightly and 1,000 per commit.

### 7.2 Property-based invariants (Hypothesis)

Each invariant below is a named Hypothesis test. The generator strategies build schema-valid configs
over their declared ranges, and seed values over the full 64-bit range. Every invariant declared in
section 3 has a row here, and `test_every_declared_invariant_has_a_property` fails when one does
not, because an invariant with no test is a claim and this document is a contract.

| ID           | Invariant                                                                                                                                                                                                                                                     | Package                 |
|--------------|---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|-------------------------|
| INV-DEM-1    | expected units equals the product of published components within 1e-9 relative                                                                                                                                                                                | demand                  |
| INV-DEM-2    | qty_allocated <= qty_ordered and qty_shipped <= qty_allocated at all times                                                                                                                                                                                    | demand, fulfillment     |
| INV-DEM-3    | adding a SKU to the config leaves every other SKU's realized series byte-identical (per-entity RNG splitting)                                                                                                                                                 | demand                  |
| INV-DEM-4    | the published promo decomposition reconciles with the realized dip and cannibalisation windows within 1e-9 relative                                                                                                                                           | demand                  |
| INV-FCST-0   | the arena refuses to register a model whose fit does not reproduce under a fixed child seed                                                                                                                                                                   | forecast                |
| INV-FCST-1   | split-conformal coverage averaged over R independent calibration draws falls in [1-alpha, 1-alpha+1/(n+1)] within its stated Monte Carlo error, and the per-draw coverage distribution is not rejected against Beta(n+1-l, l)                                 | forecast                |
| INV-FCST-2   | WAPE is scale-invariant; MASE is unit-free; sMAPE in [0,200]                                                                                                                                                                                                  | forecast                |
| INV-FCST-3   | no target-date row appears in the training slice of the cutoff that produced it (no leakage)                                                                                                                                                                  | forecast                |
| INV-INV-1    | on_hand >= 0 and available == on_hand - allocated at all times                                                                                                                                                                                                | inventory               |
| INV-INV-2    | safety stock is non-decreasing in the service target under both values of uncertainty_source                                                                                                                                                                  | inventory               |
| INV-INV-3    | safety stock is non-decreasing in demand variance and in lead-time variance                                                                                                                                                                                   | inventory               |
| INV-INV-4    | when no parametric lead-time fit is accepted the fallback is empirical, never normal                                                                                                                                                                          | inventory               |
| INV-PLAN-1   | net requirement equals the netting identity within 1e-9 relative, and expected restock inflow is exactly 0.0 when the restock model is disabled                                                                                                               | inventory               |
| INV-PLAN-2   | every appointment proposal traces to a PO proposal, and every PO proposal at or above appointment_min_pallets traces to exactly one appointment proposal                                                                                                      | inventory               |
| INV-SEG-1    | ABC and XYZ each form a total partition of the active SKU set                                                                                                                                                                                                 | inventory               |
| INV-MEIO-1   | base stock at a node is non-decreasing in its downstream service target                                                                                                                                                                                       | inventory               |
| INV-MEIO-2   | under cycle service level with normal location demand, pooled safety stock never exceeds the sum of decentralized safety stocks for non-negatively correlated demand                                                                                          | inventory               |
| INV-MEIO-3   | under fill rate, the analytic and simulated pooled requirements agree within Monte Carlo error and the direction of the pooling benefit is reported rather than asserted                                                                                      | inventory               |
| INV-SUP-1    | otif <= min(on_time_rate, in_full_rate); all rates in [0,1]; ppm in [0,1e6]                                                                                                                                                                                   | supply                  |
| INV-SUP-2    | rationed quantities never exceed capacity, granted plus shortfall equals requested, and the result is unchanged when input lines are reordered                                                                                                                | supply                  |
| INV-SUP-3    | the current value of any scorecard period equals the published value composed with its restatements in order, and no restatement lacks a trigger event                                                                                                        | supply                  |
| INV-NTIER-1  | child shares per (parent, component class) sum to 1.0 regardless of visibility                                                                                                                                                                                | supply                  |
| INV-GEN-1    | every receipt lot resolves to exactly one supplier and PO; every defect finding traces to exactly one receipt lot                                                                                                                                             | supply, returns         |
| INV-GEN-2    | the unit set returned by blast_radius equals the unit set whose backward traceback resolves to that lot, and a mismatch names the direction that dropped a unit                                                                                               | supply                  |
| INV-CART-1   | billable weight equals max(actual, dim); every packed carton passes the independent FitChecker                                                                                                                                                                | fulfillment             |
| INV-LOAD-1   | no load exceeds cube, gross weight, or any axle limit; multi-stop pallet order is LIFO-consistent                                                                                                                                                             | fulfillment             |
| INV-DOCK-1   | a door is never doubly occupied and every type switch charges the changeover                                                                                                                                                                                  | fulfillment             |
| INV-DOCK-2   | every recorded queue wait is attributed to exactly one flow type, and the attributed waits per door sum to that door's granted-request wait time in the twin's resource log within 1e-9 s                                                                     | fulfillment             |
| INV-VAS-1    | VAS material conservation: components consumed equal BOM times output plus scrap                                                                                                                                                                              | fulfillment             |
| INV-COST-1   | the sum of activity costs equals the reported cost per order to the cent, and allocation residual cents sum to the pool remainder exactly                                                                                                                     | fulfillment             |
| INV-XDOCK-1  | no pallet exceeds the dwell limit without a forced-putaway event in the same sim instant                                                                                                                                                                      | cross-dock              |
| INV-XDOCK-2  | decided_flow plus decided_store equals received, and flowed plus force_putaway plus still_staged equals decided_flow                                                                                                                                          | cross-dock              |
| INV-RET-1    | every quality-defect return resolves through genealogy to exactly one receipt lot                                                                                                                                                                             | returns                 |
| INV-RET-2    | returns closure: received equals restocked plus refurbished plus liquidated plus scrapped plus WIP                                                                                                                                                            | returns                 |
| INV-RET-3    | every uplift-raised return carries a causal_link, and every id in causal_sources_active is a registered uplift                                                                                                                                                | returns                 |
| INV-TRN-1    | no trailer exceeds cube or weight capacity                                                                                                                                                                                                                    | transport               |
| INV-TRN-2    | on a metric distance matrix, adding a stop never reduces the length of the optimal tour, asserted over the exact solver only                                                                                                                                  | transport               |
| INV-TRN-3    | with sigma zero the spot index converges monotonically to exp(mu)                                                                                                                                                                                             | transport               |
| INV-TRN-4    | quoted total cost equals linehaul plus fuel plus accessorials as exact Decimal equality at two places                                                                                                                                                         | transport               |
| INV-TRN-5    | on every instance the exact solver can run, the savings heuristic tour is never shorter than the optimum, and the gap is recorded                                                                                                                             | transport               |
| INV-ATP-1    | the sum of open promises against a bucket never exceeds its available supply                                                                                                                                                                                  | promise                 |
| INV-ATP-2a   | holding the requested date fixed, a larger requested quantity never returns an earlier promised date                                                                                                                                                          | promise                 |
| INV-ATP-2b   | holding requested date and supply state fixed, promised quantity is non-decreasing in requested quantity and never exceeds it                                                                                                                                 | promise                 |
| INV-SOE-1    | the null corrective action produces a byte-identical event log to the control arm on one platform                                                                                                                                                             | soe                     |
| INV-RST-1    | any superset of a breaking set also breaks the threshold under monotone knobs                                                                                                                                                                                 | resilience              |
| INV-FL-1     | fl.update.v1 contains no telemetry-typed field and its payload size is bounded by the parameter count                                                                                                                                                         | network                 |
| INV-WX-1     | every subscriber reading (region, day) observes an identical state by content hash                                                                                                                                                                            | exogenous               |
| INV-WX-2     | the same seed produces a byte-identical weather series on one platform                                                                                                                                                                                        | exogenous               |
| INV-VMI-1    | ownership conservation: every unit has exactly one owner at all times, transitions total and non-overlapping                                                                                                                                                  | inventory               |
| INV-ORD-1    | no field reachable from an event payload, a hash, or a control decision is a set, and every dict field serializes in ascending key order under two different PYTHONHASHSEED values                                                                            | all                     |
| INV-DET-1    | on one platform with the pinned dependency set, the full planning and supply stack run twice with one seed produces byte-identical event logs (C1 backstop, D-05 tier one)                                                                                    | all                     |
| INV-DET-2    | across the supported platforms, one seed and one config produce identical business events, and the continuous fields listed in the cross-platform manifest agree within the measured tolerance, with the observed maximum divergence reported (D-05 tier two) | all                     |
| INV-LITTLE-1 | Little's Law holds on staging lanes and pick WIP over a long run: L equals lambda times W within the stated Monte Carlo tolerance                                                                                                                             | cross-dock, fulfillment |

INV-DET-2 reports rather than asserts a preset number, per doctrine D-05: the tolerance is the
measured divergence from the calibration run recorded in the cross-platform manifest, and an
exceedance names whether the tolerance was wrong or a defect exists.

### 7.3 Validation gates and oracle tests

Two kinds of test live here and doctrine D-11 treats them differently, so they are labeled
differently. A VAL-GATE checks a statistic against a value published outside this repository. An
ORACLE test checks an implementation against an independently implemented exact answer, usually
brute-force enumeration, and claims no external evidence. D-11 rule 5 says a statistic with no valid
external reference is an open question and never a passing gate; it does not say an exact
algorithmic identity needs a citation, and calling a brute-force comparison a validation gate would
misdescribe what it proves. Every entry below states four things: what it checks, what it checks
against, the tolerance and where that tolerance comes from, and the observation that would fail it.

Every bibliographic record cited below was retrieved from the Crossref works API on 2026-08-09, each
request returning HTTP 200, and the author, title, journal, volume, issue, page range, and year in
this section are the values that API returned. That verifies the citation, not the content of the
paper behind it. Where a gate depends on a number printed inside a paywalled source, the number
lives in a checked-in extract under `tests/reference/` whose header names the exact table it came
from and who transcribed it, and the gate reports a recorded skip with that reason when the extract
is absent. A skipped gate is never reported as a pass.

Benchmark instance data follows the same rule and one more. Instance files are not vendored unless
their terms permit redistribution and those terms are recorded next to them. The M-competition
series are the worked case: the convenient public redistribution is the `Mcomp` package on CRAN,
version 2.8, published 2018-06-19, whose CRAN page states its license as GPL-3, which cannot be
vendored into an Apache-2.0 repository, so `VAL-GATE FCST-2` reads its series from a
directory the operator supplies and records a skip with that reason otherwise. Open question 9.15
records what a redistributable copy would need.

Stochastic gates state a noise floor and set the tolerance above it. The noise floor is measured by
running the gate's own null configuration `noise_floor_replications` times and recording the observed
standard deviation of the statistic, and that measured value is checked into the gate's fixture
alongside the run that produced it. A tolerance below the recorded noise floor fails the fixture
check before the gate runs.

#### Forecasting

- **VAL-GATE FCST-1 (metric definitions).** MASE as implemented matches the definition in Hyndman and Koehler (2006), "Another look at measures of forecast accuracy", International Journal of Forecasting 22(4):679-688, DOI 10.1016/j.ijforecast.2006.03.001, transcribed into `tests/reference/mase.md`. Tolerance: the metric is a closed-form ratio, so agreement is asserted to 1e-12, which is above double-precision accumulation error on the fixture sizes used and below any difference a wrong denominator could produce. Falsified by: a fixture value differing beyond 1e-12, which is what scaling by the wrong in-sample error would produce.
- **VAL-GATE FCST-2 (published competition benchmark).** The Naive2 forecast and the sMAPE implementation, run on the M3 monthly subset, reproduce the Naive2 sMAPE published in Makridakis and Hibon (2000), "The M3-Competition: results, conclusions and implications", International Journal of Forecasting 16(4):451-476, DOI 10.1016/S0169-2070(00)00057-1. Expected values come from a checked-in extract of the paper's results table. Tolerance: 0.1 sMAPE points, which is looser than the two-decimal precision the table prints, per D-11 rule 2. Series data is operator-supplied for the license reason stated above, and the gate records a skip with that reason when `M3_DATA_DIR` is unset. Falsified by: a reproduced sMAPE more than 0.1 points from the published figure, which is what a seasonally unadjusted Naive2 would produce.
- **VAL-GATE FCST-3 (intermittent classification).** The SBC quadrant classifier uses the cut-offs ADI = 1.32 and CV^2 = 0.49 attributed to Syntetos, Boylan and Croston (2005), "On the categorization of demand patterns", Journal of the Operational Research Society 56(5):495-503, DOI 10.1057/palgrave.jors.2601841, and classifies a checked-in fixture of series with hand-labeled quadrants. Tolerance: exact classification on the fixture. Falsified by: one misclassified fixture series, which is what a swapped cut-off pair would produce.
- **VAL-GATE FCST-4 (Croston and SBA).** The Croston implementation matches the recursion attributed to Croston (1972), "Forecasting and Stock Control for Intermittent Demands", Operational Research Quarterly 23(3):289-303, DOI 10.1057/jors.1972.50, on a worked fixture, and the SBA variant applies the bias correction factor attributed to Syntetos and Boylan (2005), "The accuracy of intermittent demand estimates", International Journal of Forecasting 21(2):303-314, DOI 10.1016/j.ijforecast.2004.10.001. Tolerance: 1e-10 on the fixture, since both are deterministic recursions on exact inputs. Falsified by: the SBA output equalling the Croston output, which is what omitting the correction factor produces.
- **VAL-GATE FCST-5 (model comparison test).** The Diebold-Mariano statistic matches the definition in Diebold and Mariano (1995), "Comparing Predictive Accuracy", Journal of Business and Economic Statistics 13(3):253-263, DOI 10.1080/07350015.1995.10524599, on a fixture, and the small-sample correction matches Harvey, Leybourne and Newbold (1997), "Testing the equality of prediction mean squared errors", International Journal of Forecasting 13(2):281-291, DOI 10.1016/S0169-2070(96)00719-4. Tolerance: 1e-8 on the statistic. Falsified by: the corrected and uncorrected statistics agreeing at horizons above 1, which is what dropping the correction produces.
- **VAL-GATE FCST-6 (conformal coverage).** The finite-sample marginal coverage bound this gate checks is the one attributed to Lei, G'Sell, Rinaldo, Tibshirani and Wasserman (2018), "Distribution-Free Predictive Inference for Regression", Journal of the American Statistical Association 113(523):1094-1111, DOI 10.1080/01621459.2017.1307116: split-conformal coverage at level `1-alpha` lies in `[1-alpha, 1-alpha + 1/(n+1)]` marginally over calibration draws. The gate is written over that marginal statement and not over one draw, because coverage conditional on a single calibration set is random, and an earlier draft asserted a band of plus or minus 0.015 at `n = 1000` that the conditional distribution violates roughly one run in nine. The gate draws `R` independent calibration and test splits, `R = 200` nightly and `R = 40` per commit, computes mean coverage, and asserts it lies in the published band widened by 3 standard errors of the mean. Noise floor: the standard deviation of per-split coverage is `sqrt(beta(1-beta)/(n+2))` for the Beta distribution the split-conformal construction implies, measured at 0.0095 for `alpha = 0.1` and `n = 1000` and checked into the fixture. It also runs a Kolmogorov-Smirnov test of the per-split coverages against `Beta(n+1-l, l)` with `l = floor(alpha(n+1))`, at alpha 0.01. Falsified by: mean coverage outside the widened band, or a KS rejection, either of which is what a calibration set contaminated by training data produces.
- **VAL-GATE FCST-7 (control chart routing).** The forecast-error stream declared as continuous is charted by the LSS engine as I-MR. The limits themselves are checked in the LSS engine's own suite against the NIST/SEMATECH e-Handbook of Statistical Methods, section 6.3.2, and the tolerance there is one unit in the last decimal the handbook prints, per D-11 rule 2; an earlier draft asserted 1e-6 against a value the handbook does not print to six places. This section asserts only that a stream declared `stat_type="continuous"` routes to I-MR and one declared `proportion_defective` does not. Falsified by: a proportion stream routed to I-MR, which is the misrouting this declaration exists to prevent.

#### Inventory and MEIO

- **VAL-GATE INV-1 (loss function).** The standardized normal loss function `G(k) = phi(k) - k(1 - Phi(k))` is checked two ways. Against a published primary text: `G` rebuilt from the complementary error function as `phi(k) - k * erfc(k / sqrt(2)) / 2`, where `erfc` is the function defined in equation 7.2.2 of the NIST Digital Library of Mathematical Functions, Version 1.2.7, released 2026-06-15, section 7.2, agrees with the implementation to 1e-12 across k in [-4, 6]. Against adaptive quadrature of the defining integral `int_k^inf (x - k) phi(x) dx`: agreement to 1e-10, which is the quadrature routine's own reported error bound and so the tightest honest tolerance. A third check compares a checked-in extract of the tabulated unit normal loss function in Silver, Pyke and Thomas, Inventory and Production Management in Supply Chains, 4th edition, at one unit in the last decimal the extract prints; that book is not retrievable here, so the extract carries a transcription header and the check records a skip with that reason when it is absent. Falsified by: disagreement with the DLMF-built form beyond 1e-12, which is what an implementation using the lower tail in place of the upper produces.
- **ORACLE INV-2 (fill-rate inversion).** `k_for_fill_rate` inverted through Brent root finding satisfies `G(k) = Q(1-beta)/sigma_L` to 1e-10, and re-substituting recovers the target fill rate to 1e-10. Oracle: the forward function of VAL-GATE INV-1. Falsified by: a root that does not satisfy the forward equation, which is what a bracket that excludes the root produces.
- **ORACLE INV-3 (EOQ).** The EOQ closed form matches a brute-force grid minimization of the total cost function to within one unit of quantity over a randomized parameter sweep, and the assumption checker refuses to return an EOQ when demand CV exceeds `inventory.eoq.max_cv` or a quantity-discount schedule is present. Falsified by: a returned EOQ under either refusal condition, or a closed-form answer the grid beats by more than one unit.
- **ORACLE INV-4 (newsvendor).** For normal demand, `Q*` matches the closed-form critical-ratio quantile to 1e-10, and simulated expected cost at `Q*` is not beaten by a grid search over Q by more than 2 standard errors of the simulated cost difference. Noise floor: the standard error of the paired cost difference, measured over the same replication count and checked into the fixture.
- **VAL-GATE INV-5 (policy achieves its target in simulation).** For each service measure, running the derived policy in the twin under the same demand and lead-time distributions achieves the configured target. Reference: the target itself is the published statement being checked, and the analytic form is the loss-function relation validated in VAL-GATE INV-1. Replications: 30 nightly, 10 per commit. Noise floor: the standard error of achieved service across replications, measured and checked into the fixture; the gate asserts the target lies inside the 95 percent interval, whose half-width is 1.96 times that measured standard error. Falsified by: the target lying outside the interval, which is what applying a cycle-service factor to a fill-rate target produces.
- **VAL-GATE MEIO-1 (guaranteed service time).** The dynamic program is checked against the guaranteed-service model of Graves and Willems (2000), "Optimizing Strategic Safety Stock Placement in Supply Chains", Manufacturing and Service Operations Management 2(1):68-83, DOI 10.1287/msom.2.1.68.23267, on instances from Willems (2008), "Data Set: Real-World Multiechelon Supply Chains Used for Inventory Optimization", Manufacturing and Service Operations Management 10(1):19-23, DOI 10.1287/msom.1070.0176. Both are behind the publisher's paywall here, so the expected values live in a checked-in extract with a transcription header and the gate records a skip with that reason when the extract is absent. Tolerance: total cost within 0.5 percent of the extracted figure. Service times are compared as a set of optima and not as one vector, because ties in total cost between distinct service-time vectors are routine on trees with equal marginal stage costs; the gate asserts the returned cost matches and, when the vector differs, asserts `optimum_is_unique` is false and that the returned vector achieves the same cost. Falsified by: a cost outside 0.5 percent, or a differing vector reported with `optimum_is_unique` true.
- **VAL-GATE MEIO-2 (risk pooling square-root law).** For n identical independent locations under cycle service level, the ratio of pooled safety stock to the sum of individual safety stocks equals `1/sqrt(n)` to 1e-9, which is an algebraic identity of variance addition under a common safety factor. The simulated cost difference is compared against the closed form attributed to Eppen (1979), "Note: Effects of Centralization on Expected Costs in a Multi-Location Newsboy Problem", Management Science 25(5):498-501, DOI 10.1287/mnsc.25.5.498. Replications: 30 nightly, 10 per commit. Noise floor: the measured standard error of the simulated cost difference, checked into the fixture; tolerance is 2 standard errors. Falsified by: an analytic ratio away from `1/sqrt(n)`, which is what summing standard deviations rather than variances produces.
- **ORACLE MEIO-3 (serial anchor).** `ClarkScarfSerial` reproduces the echelon base-stock optimum for a two-stage and a three-stage serial system, matched against an independent brute-force dynamic program over a discretised state space. Tolerance: 1e-6 on cost. The model formulation is the one attributed to Clark and Scarf (1960), "Optimal Policies for a Multi-Echelon Inventory Problem", Management Science 6(4):475-490, DOI 10.1287/mnsc.6.4.475. Falsified by: a cost the brute-force search beats by more than 1e-6.
- **VAL-GATE MEIO-4 (analytic versus twin).** Every published `meio.solution.v1` re-run in simulation achieves the target customer service within its confidence interval, or the solution is published with a warning finding. The gate asserts the warning is present in the second case rather than asserting the solution is correct, so a model that systematically misses its target fails visibly instead of failing silently. Replications and noise floor as for VAL-GATE INV-5. Falsified by: a missed target with no warning finding.

#### Lead-time fitting

- **VAL-GATE LT-1 (goodness of fit and recovery).** The Anderson-Darling statistic is checked against the case-specific critical values attributed to Stephens (1974), "EDF Statistics for Goodness of Fit and Some Comparisons", Journal of the American Statistical Association 69(347):730-737, DOI 10.1080/01621459.1974.10480196, transcribed into a checked-in extract, at one unit in the last decimal that extract prints. The gate also asserts the trap of 5.3: a fit with estimated parameters tested against case-0 critical values accepts at a rate materially above the nominal level, and the parametric-bootstrap path does not. It measures the empirical rejection rate of both paths at nominal alpha 0.05 over 2,000 simulated samples nightly and 400 per commit. Noise floor: the binomial standard error of the rejection rate at the replication count, measured and checked in. Tolerance: the bootstrap path's rejection rate lies within 3 standard errors of 0.05. Parameter recovery: the estimator recovers known lognormal and gamma parameters from simulated samples within a 95 percent confidence interval. Falsified by: the bootstrap path rejecting at a rate outside the band, or the case-0 path passing the same check, which would mean the trap does not exist and this gate is unnecessary.

#### Supply

- **VAL-GATE SUP-2 (joint OTIF probability).** The on-time and in-full outcomes are drawn from a latent bivariate normal, so their joint probability has a closed form: `P(on time and in full) = Phi_2(Phi^-1(p_1), Phi^-1(p_2); rho)`, the bivariate normal orthant probability of the tetrachoric model attributed to Pearson (1900), "Mathematical contributions to the theory of evolution. VII. On the correlation of characters not quantitatively measurable", Philosophical Transactions of the Royal Society of London, Series A, 195:1-47, DOI 10.1098/rsta.1900.0022. The gate compares the simulated joint frequency against that value, computed by a bivariate normal integrator independent of the sampler. Replications: 200,000 draws nightly, 40,000 per commit. Noise floor: the binomial standard error of the joint frequency at the draw count, measured and checked in; tolerance is 3 standard errors. The gate does not assert a Kendall tau, because the arcsine identity relating tau to rho, attributed to Kruskal (1958), "Ordinal Measures of Association", Journal of the American Statistical Association 53(284):814-861, DOI 10.1080/01621459.1958.10501481, needs continuous marginals and two Bernoulli outcomes are tied almost everywhere. Falsified by: a joint frequency at the product of the marginals, which is what independent draws produce and is the specific error this construction exists to avoid.
- **ORACLE SUP-3 (scorecard restatement closure).** For every `(supplier_id, period, metric)` touched by a late defect, the current value equals the originally published value composed with its restatements in `restated_ts` order, and every restatement resolves to a defect finding. This is INV-SUP-3 exercised over a seeded run with defects planted in closed periods. Falsified by: a period whose current value cannot be reconstructed from its published history, which is what an in-place overwrite produces.
- **ORACLE SUP-4 (forward blast radius).** For every `ReceiptLot` in a seeded run, the unit set returned by `blast_radius(lot_id)` equals the unit set whose backward traceback resolves to that lot, and the returned tuples are sorted so two calls return the same object. This is the query 6a11's recall drill consumes, and it is checked here because this section owns the query and the drill lives elsewhere. Falsified by: a unit present in one direction and absent in the other, which the assertion reports by naming the direction that dropped it.

#### Fulfillment

- **VAL-GATE PICK-1 (routing heuristics).** Expected travel distance for the traversal and return routing strategies in a single-block warehouse is compared against the closed-form approximations attributed to Hall (1993), "Distance approximations for routing manual pickers in a warehouse", IIE Transactions 25(4):76-87, DOI 10.1080/07408179308964306, on the layouts that paper specifies, transcribed into a checked-in extract. The heuristic families themselves follow the survey of De Koster, Le-Duc and Roodbergen (2007), "Design and control of warehouse order picking: A literature review", European Journal of Operational Research 182(2):481-501, DOI 10.1016/j.ejor.2006.07.009. Tolerance: 2 percent, which is above the approximation error the extract records for the published formula, per D-11 rule 2. Falsified by: a simulated mean distance more than 2 percent from the approximation on a layout the paper covers.
- **ORACLE PICK-2 (optimal routing).** The dynamic program of Ratliff and Rosenthal (1983), "Order-Picking in a Rectangular Warehouse: A Solvable Case of the Traveling Salesman Problem", Operations Research 31(3):507-521, DOI 10.1287/opre.31.3.507, matches brute-force enumeration exactly on all instances with at most 9 pick locations, and never returns a longer tour than any heuristic on 1,000 generated instances. Falsified by: one instance where brute force finds a shorter tour, which is what an incomplete edge-state set produces.
- **ORACLE CART-1 (packing feasibility).** `FitChecker` correctly classifies a checked-in set of known-feasible and known-infeasible three-dimensional packing instances, including rotation-dependent cases. Tolerance: exact. Falsified by: one misclassification, in either direction.
- **VAL-GATE CART-2 (packing quality).** The cartoniser's volume utilization is measured on the container-loading instances `thpack1` to `thpack7`, which OR-Library's container-loading page states were generated and used in Bischoff and Ratcliff (1995), "Issues in the development of approaches to container loading", Omega 23(4):377-390, DOI 10.1016/0305-0483(95)00015-G, and whose objective that page states is to maximize the volume utilization of the container. The comparison figures are transcribed from that paper into a checked-in extract. Tolerance: the achieved mean utilization is within 5 percentage points of the extracted figure, a band set from the spread the extract itself records across instance classes rather than chosen for comfort. The result is published in the README whichever side of the band it lands on. Falsified by: a mean utilization more than 5 points below the extracted figure, or above it, since beating a published container-loading result with a constructive heuristic is more likely a measurement error than a discovery.
- **VAL-GATE DOCK-1 (queueing).** The dock contention model is checked against queueing theory in two parts, because only one of them has a reference this section could retrieve. Part one, Little's Law: over a long run of a single door, the mean number in the door queue equals the arrival rate times the mean wait, the relation whose statement is the title of Little (1961), "A Proof for the Queuing Formula: L = lambda W", Operations Research 9(3):383-387, DOI 10.1287/opre.9.3.383. Part two, M/G/1 mean wait: with Poisson arrivals and a general service-time distribution, the simulated mean wait is compared against the Pollaczek-Khinchine mean-value formula, attributed to Pollaczek (1930), Mathematische Zeitschrift 32(1):64-100, DOI 10.1007/BF01194620, and to Khintchine (1932), Matematicheskii Sbornik 39(4):73-84. Neither body text was retrievable here, so the formula the test uses is written out in the fixture header and the comparison is reported with its attribution rather than presented as a reproduction of a text this section read. Replications: 30 of 100,000 arrivals nightly, 5 of 20,000 per commit. Noise floor: the measured standard error of the mean wait across replications, checked into the fixture; tolerance is 3 standard errors. Falsified by: Little's Law failing, which is what double-counting a queued request produces, or the M/G/1 comparison drifting with the service-time variance, which is what modeling the door as M/M/1 produces.

#### Cross-dock

- **ORACLE XD-1 (constraint identification).** With a known constraint injected, staging lanes reduced to a level that binds first by analytic capacity comparison, the flow-through sweep names that constraint. Tolerance: exact identification in 20 of 20 seeds. Falsified by: one seed naming a different resource, which is what ranking on utilization alone rather than on queueing-delay contribution produces.
- **VAL-GATE XD-2 (policy comparison).** The cost policy is compared to the rule policy on paired seeds with common random numbers, 30 nightly and 10 per commit, and the LSS engine's paired test reports the difference with its effect size and interval. Reference: the comparison is reported, not asserted, so the published claim is the table and not a winner. Noise floor: the measured standard error of the paired difference, checked in. Falsified by: the comparison table absent from the run artifacts, or a paired test run on unpaired seeds, which the fixture detects by checking that the two arms share child seeds.

#### Returns

- **ORACLE RET-1 (causal traceability).** In a seeded run with injected defective lots, every quality-defect return traces through genealogy to the injected lots and to no others. Tolerance: exact, in both directions, which is INV-GEN-2 exercised end to end. Falsified by: one return tracing to an uninjected lot, or one injected lot with no return.
- **VAL-GATE RET-2 (restock feedback).** Running the planner with and without the restock-inflow model on identical seeds shows the ignoring case holds more inventory at equal service. Replications: 30 nightly, 10 per commit, paired. Noise floor: the measured standard error of the paired inventory difference, checked in. Tolerance: the difference is asserted significant at alpha 0.05 on the paired test and its point estimate exceeds 2 standard errors. Falsified by: no detectable difference, which would mean the restock inflow is not reaching the netting step, the exact defect this models.

#### Transport

- **VAL-GATE TRN-1 (savings heuristic).** The savings heuristic attributed to Clarke and Wright (1964), "Scheduling of Vehicles from a Central Depot to a Number of Delivery Points", Operations Research 12(4):568-581, DOI 10.1287/opre.12.4.568, is run on the CVRPLIB set A instances, which that library attributes to Augerat et al. (1995), and the achieved cost is recorded against the best-known solution CVRPLIB publishes for each instance. Tolerance: the mean gap to best-known is at or below 12 percent, a band taken from the spread the extract records rather than from this repository's own history. An earlier draft asserted only that the gap does not regress from a recorded baseline, which makes this repository its own reference and D-11 rule 1 forbids it; non-regression against the recorded baseline remains, as a separate regression test rather than as the gate. Falsified by: a mean gap above the band, or an achieved cost below a published best-known solution, which for a savings heuristic means the distance accumulation is wrong. <!-- docs-lint-ok STE-TERM-WORD verbatim journal article title -->
- **ORACLE TRN-2 (exact oracle).** The branch-and-bound consolidator matches brute-force enumeration exactly on all instances with at most 8 stops. Falsified by: one instance where enumeration finds a shorter tour.
- **VAL-GATE TRN-3 (spot process).** Parameters `theta`, `mu`, and `sigma` estimated from a simulated Ornstein-Uhlenbeck path recover the generating parameters within a 95 percent confidence interval, and the exact discretisation matches the analytic transition mean and variance to 1e-8. Path length: 10,000 steps nightly, 2,000 per commit. Noise floor: the measured standard error of each estimator at the path length, checked in. Reference: the analytic transition moments of the process, which are closed-form and stated in the fixture header. Falsified by: the estimator biased at long path lengths, which is what an Euler discretisation produces and the exact transition does not.
- **ORACLE TRN-4 (rating arithmetic).** Billable weight, break-weight selection, fuel surcharge application, and accessorial summation reproduce hand-computed values on a fixture of 40 rating cases, as exact `Decimal` equality at two places with no tolerance, which is INV-TRN-4 at fixture scale. Falsified by: one cent of difference on any case.

#### Promise

- **ORACLE PRM-1 (no over-promise).** Over 100 seeded runs with aggressive order arrival, the ATP invariant never breaks, and a deliberately broken variant of the engine is caught by the same assertion. The mutation is the point: a gate that cannot catch a planted defect is not a gate, and this one states the defect it catches. Falsified by: the mutant surviving.
- **ORACLE PRM-2 (CTP fallback).** When ATP cannot cover a line and the capacity provider returns a date, the promise uses it; when the provider is absent, the line is rejected rather than promised optimistically. Both branches are tested. Falsified by: a promise issued with no supply reference behind it.

#### S&OE

- **ORACLE SOE-1 (control arm exactness).** The null action produces a byte-identical log to the control arm across 20 configurations and seeds, on one platform with the pinned dependency set (D-05 tier one). Falsified by: one differing byte, which is what a leaked scheduler state or a shared RNG stream produces.
- **VAL-GATE SOE-2 (measurement).** For an action with an injected known effect size, the measured delta recovers the injected effect within its confidence interval. Replications: 30 nightly, 10 per commit. Noise floor: the measured standard error of the paired delta, checked in. The gate also states its power: at the injected effect size and the nightly replication count, the LSS engine's paired test rejects the null in at least 90 of 100 repeated gate runs, a figure measured once and checked in with the run that produced it. Falsified by: recovery outside the interval, or a rejection rate below the recorded power, either of which means the control arm is not controlling.

#### Network and design

- **ORACLE ND-1 (MILP exactness).** On instances with at most 8 candidates and 20 regions, the HiGHS solution equals brute-force enumeration exactly in objective value, and where the opened-site set differs the gate asserts the objective is equal and the tie-break of 2.11 was applied. Falsified by: an objective enumeration beats.
- **VAL-GATE ND-2 (1-median).** Weiszfeld's algorithm is checked against instances whose 1-median is known in closed form rather than against an unnamed textbook example. For a triangle with all angles below 120 degrees the minimizer is the Fermat point; for a triangle with an angle at or above 120 degrees it is that vertex. That characterization and the convergence treatment are attributed to Kuhn (1973), "A note on Fermat's problem", Mathematical Programming 4(1):98-107, DOI 10.1007/BF01584648, with the algorithm's original statement available in the annotated English translation, Weiszfeld and Plastria, "On the point for which the sum of the distances to n given points is minimum", Annals of Operations Research 167(1):7-41, DOI 10.1007/s10479-008-0352-z. Tolerance: 1e-6 on the located point. The gate also asserts the demand-weighted centroid differs from the 1-median on the same instance, which documents the trap rather than hiding it. Falsified by: convergence to the centroid, which is what minimizing squared distance produces.
- **VAL-GATE ND-3 (design-to-operation gap).** The winning design instantiated as `facility.yaml` and run in the twin reports its simulated cost against the MILP's predicted cost with the gap decomposed into congestion, labor queueing, dock contention, and residual. Reference: the MILP's own objective, which is an external-to-the-simulation prediction rather than a published statistic, so this is a consistency gate on the decomposition and says so. Tolerance: the four components sum to the total gap within 1 percent of the total. Falsified by: a residual that grows with instance size, which means the decomposition is missing a term.
- **ORACLE FL-1 (federated privacy).** `fl.update.v1` schema validation rejects any payload containing a telemetry-typed field, and a runtime test asserts the payload size is bounded by `param_count * bytes_per_param + header_bytes`. Falsified by: a padded blob passing the size bound, which is the smuggling path the bound exists to close.
- **VAL-GATE FL-2 (federated accuracy).** FedAvg, the aggregation rule of McMahan, Moore, Ramage, Hampson and Aguera y Arcas (2017), "Communication-Efficient Learning of Deep Networks from Decentralized Data", Proceedings of the 20th International Conference on Artificial Intelligence and Statistics, Proceedings of Machine Learning Research 54:1273-1282, is run on an IID partition and reaches within `federated.iid_tolerance` of the centrally trained model's held-out score. On a non-IID partition the degradation is measured and published either way, with no threshold, because that paper's abstract states only that "the approach is robust to the unbalanced and non-IID data distributions that are a defining characteristic of this setting", which is a direction and not a bound, and asserting a bound this section cannot derive would be inventing evidence. Falsified by: IID degradation beyond the configured tolerance, which is what a sample-count weighting error produces. <!-- docs-lint-ok PROMO-01 verbatim quotation of the McMahan et al. 2017 abstract, retrieved from proceedings.mlr.press -->
- **ORACLE BRG-1 (bridge policy).** No concrete topic in the schema's test set is matched by both the forward and the block list, and the measured bridge reduction is recorded per run. Falsified by: one topic matched by both lists, which makes forwarding order-dependent.

#### Resilience

- **ORACLE RST-1 (known single point of failure).** On a hand-constructed network with one injected single point of failure, the cardinality-1 exhaustive search finds exactly that node and nothing else. Falsified by: any other node in the result, or that node absent.
- **VAL-GATE RST-2 (search efficiency).** The Optuna search finds the known minimal breaking set within `budget_trials`, and every reported breaking set is confirmed by full simulation. Acceptance: at least 95 successes in 100 seeds nightly, at least 17 in 20 per commit. Noise floor: those two acceptance regions are the lower tails of a binomial at a true success probability of 0.98, so a search at that quality passes about 99 times in 100 and a search at 0.90 fails almost always. Falsified by: a success count below the acceptance region, or one reported breaking set that full simulation does not confirm.
- **VAL-GATE RST-3 (TTS and TTR).** On a scenario with an analytically computable buffer depletion time, the measured time-to-survive matches the analytic value within one simulation day, which is the resolution of the measurement and so the tightest honest tolerance. The framing of time-to-survive and time-to-recover follows Simchi-Levi, Schmidt, Wei, Zhang, Combs and Ge (2015), "Identifying Risks and Mitigating Disruptions in the Automotive Supply Chain", Interfaces 45(5):375-390, DOI 10.1287/inte.2015.0804. Falsified by: a measured time-to-survive more than one day from the analytic depletion time, which is what counting in-transit stock as available produces.

#### Weather

- **VAL-GATE WX-1 (spatial correlation).** The empirical correlation of temperature anomalies between region pairs matches the configured `exp(-d/corr_length_km)` structure. Run length: 10,000 simulated days nightly, 1,000 per commit. Noise floor: the standard error of a Pearson correlation at the run length, measured and checked in; tolerance is 3 standard errors per pair with a Bonferroni adjustment over the pair count. Reference: the configured correlation function itself, which is a stated model rather than a published statistic, so this is a self-consistency gate and says so. Falsified by: correlation that does not decay with distance, which is what a shared scalar shock produces.
- **VAL-GATE WX-2 (degree days).** Heating and cooling degree days match hand-computed values on a fixture to 1e-9, computed on the definition NOAA's Climate Prediction Center publishes for its degree-day products: the daily mean is the average of the daily maximum and minimum temperature, 65 degrees Fahrenheit is the base for both, heating degree days sum the negative differences from that base and cooling degree days the positive ones. Tolerance: 1e-9, because both sides are exact arithmetic on the same daily means. Falsified by: a nonzero heating degree day on a day whose mean is above the base, which is what taking the absolute difference produces.
- **ORACLE WX-3 (single source).** All couplings applied on the same sim day reference the same state hash, asserted across a full seeded run. Falsified by: two subscribers on one day with different hashes, which is what a second weather draw produces.

### 7.4 The headline test: forecast quality propagating into floor congestion

`E2E-FCSTPROP-01` is the test that proves 6a's central claim. It runs the same 120-day scenario at
four injected forecast bias levels, 0, 10, 20, and 30 percent, holding every other stream identical.
The forecast drives the replenishment plan, which drives the PO schedule, which drives the truck
appointment schedule, which drives dock arrivals.

The test runs `R` independent seeds at each level, `R = 30` nightly and `R = 8` per commit, because
one run per level makes assertion 1 a statement about noise. Every seed is used at all four levels,
so the four groups are paired and the paired variance is what the assertions are measured against.
Budget: the 120-day scenario is declared at its measured per-run cost in the test registry, and the
budget test of 7.1 fails when four levels times `R` seeds exceeds the tier budget in either profile.

The assertions:

1. Mean dock queue wait is non-decreasing in absolute forecast bias across the four levels, asserted
   on the level means with their paired confidence intervals rather than on point estimates, and
   backed by a Jonckheere-Terpstra trend test at alpha 0.05, which is the test for an ordered
   alternative and is what assertion 1 states. A one-way ANOVA is also run and reported;
   it detects any difference among the four means and so is the weaker of the two here.
2. Noise floor: the standard error of the paired difference in mean queue wait between adjacent bias
   levels, measured over `R` seeds at zero injected bias and checked into the fixture. The gate
   requires the observed step between the 0 and 30 percent levels to exceed 3 of those standard
   errors, so an effect smaller than the measurement cannot pass as a demonstration.
3. The effect size, eta squared for the ANOVA and the standardized paired difference for the trend,
   is recorded in the golden file, so a regression that flattens the effect is caught by the number
   and not only by the p-value.
4. The appointment-versus-arrival mismatch count mediates the effect: with appointments held fixed
   to the true demand and everything else unchanged, the congestion step falls below the noise floor
   of assertion 2. That mediation check is what proves the mechanism rather than a correlation.
5. Falsified by: a non-monotone level mean outside its interval, a trend test that does not reject,
   a step below the noise floor, or a mediation arm that still shows the effect. The fourth is the
   most informative failure, because it means congestion is being driven by something other than the
   appointment schedule and the causal claim in 6a is wrong as stated.

### 7.5 Seeded end-to-end scenarios with golden files

| ID              | Scenario                                                 | Golden artifacts                                                                                                             |
|-----------------|----------------------------------------------------------|------------------------------------------------------------------------------------------------------------------------------|
| E2E-PLAN-01     | 120-day two-channel base run                             | planning report, forecast arena table for both target families, policy set, event log hash                                   |
| E2E-FCSTPROP-01 | forecast bias to congestion (7.4)                        | trend test, ANOVA result, queue-wait table with intervals, mediation check                                                   |
| E2E-SURGE-01    | demand surge 15 percent (5.19)                           | door utilization and queue wait, AMR utilization, fill rate and stockout hours, absorbing safety stock in units and currency |
| E2E-CUTOFF-01   | carrier cutoff moved from 16:00 to 18:00 (5.19)          | same-day orders, cycle time, labor and overtime hours, on-time ship, cost per order, missed-departure count                  |
| E2E-MEIOBUD-01  | holding cost capped, placement maximizing service (5.19) | placement, analytic service, simulated service with interval, binding echelon                                                |
| E2E-SUP-01      | supplier B down two weeks                                | service level, scorecard restatement, dual-source versus safety-stock comparison                                             |
| E2E-CAP-01      | supplier A capacity halved for one month                 | rationing record, shortfall by PO, lead-time effect on the scorecard                                                         |
| E2E-NTIER-01    | hidden shared tier-2 causes correlated tier-1 failure    | correlation estimate with CI, mapping ROI                                                                                    |
| E2E-OUT-01      | wave versus waveless on identical demand                 | cycle time, fill rate, labor utilization, comparison table                                                                   |
| E2E-PEAK-01     | peak-day chaos with elevated follow-on returns           | channel unit economics, dock contention decomposition                                                                        |
| E2E-XDOCK-01    | flow-through sweep 20 to 40 to 60 percent                | binding constraint, missed-connection p-chart, dwell I-MR                                                                    |
| E2E-RET-01      | returns spike to 12 percent                              | reverse P&L, reason-code Pareto, `causal_sources_active`, outbound service degradation                                       |
| E2E-TRN-01      | diesel up 20 percent                                     | freight spend table, mode-mix shift                                                                                          |
| E2E-TRN-02      | carrier X on-time down 10 percent                        | switch-versus-renegotiate indifference point                                                                                 |
| E2E-MEIO-01     | centralize versus forward-position                       | frontier, analytic and simulated service side by side                                                                        |
| E2E-PRM-01      | promise reliability under a supply shortfall             | promise p-chart, quoted-versus-actual I-MR                                                                                   |
| E2E-SOE-01      | weekly tick with an expedite action                      | treated versus control arms, hypothesis test                                                                                 |
| E2E-WX-01       | winter storm across two regions                          | demand, transit, yard, HVAC, slip-risk deltas from one state                                                                 |
| E2E-NET-01      | two sites, overflow allocation                           | network KPIs, bridge reduction, chosen site with justification                                                               |
| E2E-ND-01       | greenfield siting to facility.yaml to operational run    | design, predicted cost, simulated cost, gap decomposition                                                                    |
| E2E-RST-01      | reverse stress test finds the hidden tier-2              | minimal breaking sets, TTS and TTR per node                                                                                  |
| E2E-VMI-01      | VMI versus owned at record accuracy 1.00, 0.96, 0.92     | stockouts, working capital by party, monotonicity assertion                                                                  |
| E2E-POST-01     | postponement versus stock-finished                       | pooling benefit analytic and simulated, cutoff-miss cost                                                                     |

Every scenario records its seed, its config hash, and its schema versions in the golden file header, so C6's migration story can state exactly which recorded runs a release still loads.

### 7.6 Contract tests

For every event type in section 4, a producer test asserts the emitted payload validates against its schema, and a consumer test asserts the consumer tolerates every field the schema permits, including fields added since the consumer was written. CI fails on producer and consumer drift (C3). A schema-evolution test also replays the golden event logs from the previous release against the current consumers.

---

## 8. Phase placement

The author's phase order is the baseline. The agreed resequencing rule applies: E-items that are upstream dependencies of earlier work move ahead of their dependents, and nothing is ever dropped.

### 8.1 Phase 0 contributions (contracts that cannot be retrofitted)

Landing in Phase 0 alongside C1, C2, C3, C5, C10, A1:

- The `/schemas` entries for `demand.signal.published.v1`, `order.created.v1`, `inventory.position.snapshot.v1`, `leadtime.observed.v1`, and `weather.state.v1`. Reason: every later package produces or consumes these, and adding a required field later is a major-version break under C3.
- The `ownership` field on `InventoryPosition` and the `Ownership` enum. Reason: E41's consignment model cannot be added later without a historian migration on every inventory row, and C6 would have to carry that migration forever. The field ships at birth with `OWNED` as the only populated value until P3e.
- The `stat_type` declaration convention on every metric event. Reason: it is what lets the LSS engine select charts without coupling, and retrofitting it means restating every recorded run.
- `catalogs/disruption_space.yaml` schema. Reason: the chaos catalog and E20's search space are the same declaration, and having two would guarantee they diverge.

### 8.2 Pre-P3d: E40 weather, moved forward

E40 lands immediately before P3d. Reason: weather is an input to the demand generator's seasonality and to the ambient sensor readings that already exist from Phase 3's sensor breadth. Adding a correlated exogenous driver after the demand generator is seeded changes every realized series and invalidates every golden file recorded before it. Moving it forward costs nothing and saves a repository-wide golden-file rebase. The couplings for transit, yard, HVAC, and slip risk register as their target layers arrive; the coupling registry is open from the start.

### 8.3 P3d: the planning layer (6a)

Order within the phase, driven by dependencies:

1. `twinflow-demand`: demand signal and order streams. Depends only on the kernel and E40.
2. `twinflow-forecast`: the arena with classical baselines, backtest, metrics, and the bias monitor. Depends on demand and on the LSS engine (P2) for the control chart.
3. `twinflow-inventory` part one: segmentation, lead-time estimation from twin observations, single-echelon policy. Depends on forecast for demand variability and on the twin (P1/P3) for lead-time observations.
4. Replenishment planning and the propagation into truck scheduling, which is what makes `E2E-FCSTPROP-01` runnable. Depends on the twin's dock and appointment model.

MEIO is not here. It needs a network, and the network arrives at P3h.

### 8.4 P3e: suppliers and outbound

1. `twinflow-supply` with an n-tier graph from birth. E19's data model lands here even though its mapping mechanic and concentration analytics land later in the phase, because a tier-1-only supplier schema would need a migration to become n-tier.
2. E19 mapping mechanic, visibility states, concentration reporting, and the correlated-failure demonstration.
3. E16 ATP/CTP, moved forward from P6. Reason: 6a3's on-time-ship and fill-rate KPIs need a promise to measure against, and building outbound without a promise means retrofitting the promise reference into every order line later. CTP's capacity provider is stubbed with the DC's own labor and dock capacity until 6a9 supplies the factory scheduler.
4. `twinflow-fulfillment` outbound half: wave and waveless release, pallet picking, load building, carrier assignment for TL and LTL, dock contention through `DockBroker`.
5. E41 VMI policy half, moved forward from P6. Reason: VMI is a supplier-facing replenishment mode and the supplier layer is being built now; the ownership field already exists from Phase 0, so this is policy only.
6. E15 S&OE core, moved forward from P6. Reason: the plan of record and the actuals both exist as of this phase, the exception queue is the natural consumer of everything P3d and P3e produce, and the control-arm mechanism is a direct exercise of C1 that is cheaper to build now than to retrofit. The action registry starts with `reallocate` and `re_wave`; `expedite` registers at P3h when transport exists; `substitute` registers when 6a12 supplies substitution rules.

   Two seams in the S&OE tick are unbound at P3e and both have a stated behavior rather than a
   silent one. Alarm rationalization belongs to `twinflow-lss`, which lands at P2, so the call is
   normally bound; when the engine is absent, as it is in a standalone install of `twinflow-soe`,
   the queue ranks exceptions by `revenue_at_risk` descending, then `severity` descending, then
   `exception_id` ascending, groups them by `(type, node_id or lane_id or sku_id)`, and marks every
   published exception `rationalized=False`. A reader can then tell an unrationalised queue from a
   rationalized one, which a queue that silently skipped the step could not. The authority tier on
   `CorrectiveAction` comes from E5's autonomy levels; until E5 lands, every action is published at
   `L1` and the field is never absent, so no consumer has to handle a missing tier and no action can
   auto-apply by default.

### 8.5 P3f: returns

`twinflow-returns` in full. Depends on outbound (to have shipments to return), on the dock broker (to contend for doors), on genealogy (for defect traceback), and on the planner (for the restock feedback). Every one of those exists by the end of P3e.

### 8.6 P3g: cross-dock and e-commerce

1. `twinflow-crossdock`. Depends on inbound receipts, outbound loads, and the dock broker. Ships with the baseline `DockScheduleProvider`; E12 replaces it later and the improvement is measured against this baseline.
2. `twinflow-fulfillment` e-commerce half: each-picking modes, travel models, cartonisation, parcel rate shopping, peak-day chaos, channel unit economics, parcel-versus-pallet interference measurement. Goods-to-person needs the AMR fleet, which arrived at P3b.
3. E41 VAS and postponement half. Reason for placing it here rather than with the VMI half: kitting and postponement are DC work content whose value shows up against the e-commerce order profile, and the pooling argument needs the variant demand structure that the e-commerce channel supplies.

### 8.7 P3h: transport, then sites, then MEIO

This is a resequencing inside the author's own phase, and it is the one place the order matters.

1. `twinflow-transport` in full. Everything downstream needs lane costs and transit distributions.
2. E13a multi-site: site registry, bridge topic policy, cross-site KPI rollup, overflow allocation. Moved forward from P6. Reason: 6a8's own text says inventory is positioned across echelons including "forward positions once E13 adds sites". Building MEIO against a single-site network means building it twice. E13's federated learning half stays at P6 with E43, because it needs the model registry.
3. `twinflow-inventory` part two: MEIO. Guaranteed-service DP, the Clark-Scarf serial anchor, risk pooling, the frontier, and validation against the twin.
4. `EchelonPropagation` in `twinflow-resilience`: disruption propagation across echelons, which is a named 6a8 requirement and needs both the transport network and the echelon structure.
5. E15 action registry gains `expedite` now that premium freight exists.

### 8.8 P3i and the 6a10 to 6a17 group

No new packages from this section land here, but three integrations do, and they are listed so nobody has to rediscover them:

- 6a9 supplies the real `CapacityPromiseProvider`, so CTP stops using the DC-only stub.
- 6a12 supplies the real `AllocationPolicy` and substitution rules; `OrderLite` states are extended additively.
- 6a16 replaces the S&OE plan of record with the S&OP consensus, changing `PlanSnapshot.source` from `replenishment_plan` to `sop_consensus`. Both remain supported, because a reader running only the planning brick has no S&OP.
- 6a17 consumes `OrderCostRecord` for activity-based costing and `inventory.ownership.transferred.v1` for consignment accounting.

### 8.9 Phase 6

Remaining items from this section, in the author's stated E order:

- **E20 reverse stress testing.** Stays in P6 because it is not an upstream dependency of earlier work, and because stage 3 of its search wants E28's surrogate and E9's optimizer, both P6. Its `DisruptionSpace` declaration already shipped in Phase 0, so E20 is additive when it lands.
- **E42 strategic network design.** Stays in P6 per the author's order. It is downstream of everything: it needs the transport rate model, the demand geography, the multi-site instantiation path, and a mature operational twin to hand designs to. Its value is highest last, because the design-versus-operation gap it publishes is only interesting once the operational model is trustworthy.
- **E13b federated learning.** With E43's model registry, per 8.7.

---

## 9. Open questions

These are genuine ambiguities in the source. None has been silently resolved.

**9.1 Who owns the demand generator.** Component 6a says "the ERP stub generates a synthetic demand signal", and 6b says the ERP stub is "kept deliberately small". This spec puts the generator in `twinflow-demand` and makes the ERP stub a thin publisher that calls it, on the grounds that a forecasting brick a reader installs alone needs a demand source and the ERP stub must stay small. If the author prefers the generator inside the ERP stub, `twinflow-demand` becomes a library the stub depends on and the event producer field changes. The event contract is identical either way, so this is reversible, but the decision belongs before P3d.

**9.2 Goods-to-person station ownership.** 6a6 calls goods-to-person an AMR what-if. The AMR fleet, its task allocation, and its traffic management are 1b, which lands at P3b. This spec puts the GTP pick station and its queueing in `twinflow-fulfillment` and calls into the AMR fleet for transport tasks. The alternative is putting the station in the automation package. The seam matters because the station's throughput is the constraint in most GTP designs, and whichever package owns it owns that KPI.

**9.3 Order state model boundary.** 6a3 and 6a6 need orders at P3e; 6a12's full order-lifecycle engine arrives after P3i. This spec defines `OrderLite` with a minimal state set that 6a12 extends additively under C3. The open question is whether 6a12 is permitted to extend the enum, or whether the author wants a single order state model designed up front in Phase 0 and frozen. Extending an enum is additive and legal under C3; replacing it is a major version break.

**9.4 Cross-dock's dependence on E12.** 6a5 says "the yard optimization of E12 becomes load-bearing here", but 6a5 is P3g and E12 is P6. This spec ships a deterministic baseline `DockScheduleProvider` at P3g and has E12 replace it later through the same interface, with the improvement measured against the baseline. The alternative is moving E12 forward to P3g under the agreed resequencing rule, on the grounds that it is an upstream dependency of 6a5. Both are defensible. The baseline-first version has the advantage that it produces the comparison table E12 needs to justify itself.

**9.5 Freight classification data.** LTL rating needs a density-to-class mapping. Real NMFC classification tables are proprietary and cannot be redistributed in an Apache-2.0 repo. This spec ships a synthetic density-to-class table with the same structure, labeled synthetic. The alternative is to abstract away class entirely and rate LTL on density directly, which is simpler but loses a piece of vocabulary that a freight audience recognizes immediately. Confirm which trade the author wants.

**9.6 Currency and FX.** E14's tariff engine and international inbound lanes imply cross-border transactions. The source never states whether the system is single-currency. Multi-currency affects landed cost, the GL in 6a17, contract terms, and the spot market. This spec assumes single-currency with a `currency` field present on monetary events so multi-currency is additive later, but the decision belongs to the finance section and is made once for the whole repo.

**9.7 Default service measure.** Cycle service level and fill rate give different safety stock for the same inputs, and reports that do not say which was used are misleading. This spec makes `inventory.service_measure` a required key with no default, which forces every config to state it. If the author wants a default, fill rate is the better one because it is what a DC promises a customer, but a silent default on this key is how planning systems produce numbers nobody can reconcile.

**9.8 MEIO framing.** 6a8 says "research the right 2026 framing of the Graves/Willems-class approach". Guaranteed-service (Graves-Willems) and stochastic-service (Clark-Scarf, and the Simchi-Levi line of work) answer different questions: guaranteed-service assumes demand bounds and internal service commitments, stochastic-service models backorders propagating upstream. This spec implements guaranteed-service as primary because it is what 6a8 names, and Clark-Scarf serial as a validation anchor. The open question is whether the README presents both as first-class alternatives with a comparison, which would be more honest and would cost one more implementation.

**9.9 Geography realism.** E42's center-of-gravity and MILP siting, E40's spatial weather correlation, and the transport network's distances all need coordinates. Fully fictional geography makes distances implausible and makes the siting result impossible to sanity check. Real public geography (published metro-area centroids) is freely usable and makes the model legible, with all demand and cost data still synthetic. This spec assumes real public coordinates with synthetic everything else, and the README must say so plainly so nobody mistakes the demand for real. Confirm.

**9.10 Federated learning across the Purdue boundary.** E13's federated updates flow from each site to an enterprise aggregator, which crosses the site-to-enterprise boundary. 6a15's IEC 62443 zone model will want that crossing declared as a conduit with its own monitoring. This spec declares the `fl.update.v1` contract and the privacy invariant but does not place the aggregator in a zone. That placement is a cross-section decision between this section, the IoT/UNS section, and 6a15.

**9.11 Gross versus net forecasting with returns.** 6a4 says "return-inflated stock is a real forecasting complication; the forecaster must handle it". Two conventions exist: forecast gross demand and model return inflow separately, or forecast net requirements directly. This spec chooses gross plus a separable distributed-lag return-inflow model, because it keeps the forecast auditable and lets the return model be validated on its own. If the author wants net forecasting, the arena's target series changes and every backtest number changes with it.

**9.12 Spot-market calibration.** The spot index needs volatility and mean-reversion parameters that produce plausible behavior. Public freight rate indices exist but their data is proprietary. This spec uses a synthetic Ornstein-Uhlenbeck process with parameters chosen to produce a plausible volatility band, documented as synthetic and not calibrated to any real index. Confirm that no calibration claim is wanted, because claiming calibration to a real index would need data the repo cannot ship.

**9.13 What counts as the E20 threshold.** Reverse stress testing needs thresholds to search against. Service level is obvious. Cash comes from E22's financial twin, which is P6. This spec supports both and lets the config declare which are active, but until E22 exists only the service threshold is available, which makes the P6 ordering of E20 relative to E22 relevant. If E20 lands before E22, its first release searches on service alone and gains the cash threshold when E22 arrives.

**9.14 Where the four governed metrics are defined and where their parts are published.** E26(b) puts one definition of `fill_rate`, `otif`, `days_of_supply`, and `landed_cost` in the governed semantic metrics layer, and this section publishes the numerator and the denominator of each rather than a second definition. Three of the four are settled: `fill_rate` and `otif` have their counts and denominators on `order.fulfillment.completed.v1` and `supplier.scorecard.v1`, and `days_of_supply` gained its denominator fields on `inventory.position.snapshot.v1` in 3.3. `landed_cost` is not settled, because its parts arrive from four sections: freight from `lane.rate.quoted.v1` here, duty from E14, carbon price from E17, and handling from 6a17. This section publishes its own part and names the others, but who assembles the total, and whether a partially assembled landed cost may be published at all before E14 and E17 land, is a decision for the metrics layer and the finance section together. Publishing a landed cost that silently omits duty is the failure mode to avoid.

**9.15 Benchmark instance data and redistribution terms.** Three gates in 7.3 compare against published benchmark results, and the instance data behind them has three different license positions. The M-competition series are conveniently redistributed in the `Mcomp` package on CRAN, version 2.8, published 2018-06-19, whose CRAN page states the license as GPL-3, which cannot be vendored into an Apache-2.0 repository, so that gate reads operator-supplied data and records a skip otherwise. The container-loading instances `thpack1` to `thpack7` are published on OR-Library, which carries its own statement on legal use that has not been read here. CVRPLIB publishes the set A instances and their best-known solutions under terms that have likewise not been read here. Confirm for each source whether the instances may be vendored, and if not, the operator-supplied path with a recorded skip becomes the shipped arrangement for all three. Reporting a skipped gate as a pass is the outcome this question exists to prevent.

**9.16 Carrier tariff calibration.** Three shipped defaults look like carrier tariff values and are not: the dimensional divisors of 139 cubic inches per pound and 5000 cubic centimetres per kilogram, the parcel weight limit of 31.75 kilograms, and the parcel dimension and girth limits. They are working values chosen to produce plausible behavior, and the synthetic carrier catalog says so in its header. Calibrating them against a real published tariff would make the parcel economics recognizable to a freight audience, and would need a tariff whose terms permit the numbers to be checked in. Confirm whether the author wants that, because the alternative, which is what ships now, is a model that is internally consistent and matches no carrier in particular.

**9.17 The tracking signal limit.** Brown's tracking signal is a second bias detector alongside the control chart, and the limit at which it fires is `forecast.tracking_signal_limit`, default 4. That default is a working convention. This section did not retrieve a published table that sets it, so it is not attributed to one, and a report that called it a standard limit would be asserting evidence this section does not have. Two ways out: attribute it to a retrievable published source and state the source in the README, or derive the limit from the false-alarm rate wanted on the smoothed-error process and publish that derivation. The second is more work and produces a number the repository can defend on its own.
