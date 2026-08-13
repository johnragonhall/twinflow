---
title: "Back office: orders, procurement, workforce, IT operations, commercial, finance"
description: Implementation contract for the enterprise functions that sit on the physical twin, from order capture through the general ledger and risk transfer.
topic_type: reference
audience: contributors
---

# Back office: order management, procurement, workforce, IT and cyber operations, commercial and S&OP, finance

This section is the implementation contract for the enterprise functions that sit on top of the
physical twin. It covers the front office, the buy side, the people layer, the twin's own IT and
security operations, the demand-side brain, and the finance department that prices all of it.

This section conforms to `docs/design/DOCTRINE.md`. Where a doctrine ruling is applied the ruling id
is cited at the point of application. The rulings that reach this section are D-01, D-03, D-04,
D-05, D-07, D-09, D-10, D-11, D-12, D-13, and D-14.

## 1. Scope

This section covers the following numbered requirements in full.

| Requirement | Title in the source                                  | Owned here                                                                                                           |
|-------------|------------------------------------------------------|----------------------------------------------------------------------------------------------------------------------|
| 6a12        | Order management and customer service                | Entire component                                                                                                     |
| 6a13        | Procurement and purchasing                           | Entire component                                                                                                     |
| 6a14        | HR and workforce management                          | Entire component except the roster solver itself (E23), whose input and output contracts are defined here            |
| 6a15        | IT and cybersecurity operations                      | Entire component. The adversarial scenario catalog is E18 and consumes the hooks defined here                        |
| 6a16        | Marketing, sales operations, and the full S&OP cycle | Entire component. Causal estimation of marketing-mix ROI is E30 and consumes the ground-truth generator defined here |
| 6a17        | Finance and accounting operations                    | Entire component                                                                                                     |
| E14         | Tariff and trade-policy scenario engine              | Entire item                                                                                                          |
| E22         | Financial twin overlay                               | Entire item                                                                                                          |
| E38         | Insurance and risk transfer                          | Entire item                                                                                                          |

Requirements owned elsewhere that this section consumes or extends, listed so the boundary is
explicit and no implementer builds the same thing twice:

| Requirement                                 | Boundary                                                                                                                                                                                                                                                                                  |
|---------------------------------------------|-------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| 5 (LSS engine)                              | Every KPI defined here is trended by the LSS engine. This section names the chart type per metric and emits the sample stream; it never implements a control chart                                                                                                                        |
| 6a2 (supplier network)                      | Supplier reliability profiles, ASNs, and OTIF observations are produced there. `twinflow-procurement` consumes them and adds the buyer-side view                                                                                                                                          |
| 6a3, 6a6 (outbound, e-commerce)             | Shipment and pack events are produced there. `twinflow-orders` consumes them for order state and perfect-order scoring                                                                                                                                                                    |
| 6a4 (returns)                               | Return and disposition events are produced there. Consumed here for complaint generation and for the returns P&L postings                                                                                                                                                                 |
| 6a9 (upstream production)                   | Production completion, material issue, scrap, and yield events are produced there. Consumed here for standard-cost variances                                                                                                                                                              |
| 6a10 (ergonomics)                           | Strain index and TRIR are produced there. Consumed here for attrition hazard and for the workers' compensation experience modifier                                                                                                                                                        |
| 6a11 (QMS)                                  | NCR and CAPA workflow is there. Complaints raised here become external-failure COPQ there                                                                                                                                                                                                 |
| 6a7 (transport)                             | Freight rates, premium freight quotes, and in-transit shock/temperature telemetry are produced there. Consumed here for expediting economics and cargo claims                                                                                                                             |
| 6a1, 6a8 (planning, MEIO)                   | Forecast, reorder signals, and echelon policies are produced there. Consumed here for requisitions and for the S&OP supply review                                                                                                                                                         |
| E5, E21 (autonomy tiers, decision register) | The append-only decision register schema is a dependency of 6a16 and is pulled forward (see section 8). Multi-agent negotiation stays in E21                                                                                                                                              |
| E16 (ATP/CTP promising)                     | Promise computation is E16. `twinflow-orders` calls it through a port and owns quoted-versus-actual promise reliability                                                                                                                                                                   |
| E19 (n-tier mapping)                        | The supplier DAG stays in Phase 6. In-band, `SupplierDagPort` returns unavailable, tier-2 concentration is reported as `unenforced`, and no in-band test asserts a tier-2 number. When E19 lands the same port returns the DAG and the constraint becomes enforceable with no code change |
| E23 (rostering)                             | The constraint solver is there. This section publishes the labor requirement and absence forecast it consumes, and consumes the roster it produces                                                                                                                                        |
| E26 (accuracy stack)                        | Layers a, b, d, and f are resequenced ahead of this band (section 8.2) because this section's tools and tests exercise them. This section contributes metric definitions and tool schemas; E26 owns layers c, e, and g                                                                    |
| E27 (agent evaluation harness)              | The harness runner and the eval-suite file format are resequenced ahead of this band. This section contributes eval questions and their ground-truth answers, not the scoring machinery                                                                                                   |
| E5 (autonomy tiers)                         | The tier enum and the approval gate for mutating tools are resequenced ahead of this band. E5 later adds L3 auto-apply and the guardrail evaluator                                                                                                                                        |
| E43 (AI security evals)                     | The four indirect prompt-injection fixtures defined here ship as this section's own tool tests now. E43 later adopts them into the red-team suite and adds scoring across the whole tool surface                                                                                          |
| E30 (causal inference)                      | Promotion lift, cannibalisation, and forward buy are generated here with known ground-truth parameters. E30's pipeline lands before the generator and its scoring lands after it (section 8.3)                                                                                            |
| E28 (learned surrogate)                     | The surrogate model is there. The S&OP supply review declares a `surrogate` mode that calls it through `CapacityPort` and defaults to the analytic mode, so the cycle runs with or without E28                                                                                            |
| Chaos scenario framework                    | This section defines and publishes `chaos.scenario_started` and `chaos.scenario_ended` for its own restore drills and business-interruption triggers. The Phase 4 store-and-forward catalog extends the same schema                                                                       |
| E37 (PLM)                                   | BOM and recipe versioning with effectivity dates is there. Standard-cost roll-up here consumes a single effective revision and gains effectivity handling when E37 lands                                                                                                                  |

## 2. Packages

Eight independently installable distributions. Distribution names use hyphens, import names use
underscores, no namespace package. Every package depends on `twinflow-kernel` (the `Clock`, `Rng`,
`Network`, `EventBus`, `Storage`, `Inference`, and `WhatIfPort` protocols plus the seeded RNG tree)
and on `twinflow-schemas` (the generated event models from `/schemas`). No package in this section
imports another's internals. Where one needs data from another, it declares a `typing.Protocol` port
and ships a null implementation so `pip install` of that package alone produces a runnable example
(A1).

Two packaging rules from the doctrine bind every list below.

Per D-09, every public symbol has exactly one owning package in this section. A name that would
otherwise appear in two packages is disambiguated at its source rather than by import alias, which
is why the workforce package exports `JobRole` and `HiringRequisition` while the IT operations
package exports `AccessRole` and the procurement package exports `PurchaseRequisition`. A protocol
that two packages here both need (`WhatIfPort`) is declared once in `twinflow-kernel` and imported,
never redeclared. CI walks the import graph, fails on a cycle, and asserts that every name in a
package's `__all__` is defined in that package.

Per D-10, each core install stays minimal and every heavy dependency ships as an extra. A port whose
signature would drag a columnar or modeling library in is typed against a narrow structural
protocol, with the concrete type imported only under `TYPE_CHECKING`. The A1 job in section 7.6
installs each package alone in a clean environment and runs its example, so the claim is tested.

### 2.1 `twinflow-orders`

Purpose: order lifecycle, allocation policy, promise tracking, and the customer service operation.

Public API:

```python
from twinflow_orders import OrderBook, OrderLifecycle, PerfectOrderScorer
from twinflow_orders.allocation import AllocationEngine, FairShare, Priority, Hybrid, AllocationResult
from twinflow_orders.allocation import JainFairnessIndex
from twinflow_orders.promising import PromiseEngine, PromisePort
from twinflow_orders.changes import ChangeRequestHandler, ChangeCostModel
from twinflow_orders.service import ServiceCenter, ContactGenerator, ContactRouter, Visibility
from twinflow_orders.customer import CustomerModel, SatisfactionState, ChurnHazard, ClvCalculator
from twinflow_orders.arrival import ArrivalProcess, ArrivalIntensity, ChannelDraw
from twinflow_orders.ports import InventoryAvailabilityPort, ShipmentPort, AgentRosterPort
from twinflow_orders.ports import ReturnsPort, CostToServePort
from twinflow_kernel.ports import DemandShapingPort, ChannelMixPort
```

Depends on: `twinflow-kernel`, `twinflow-schemas`. Optional extra `[analysis]` adds `duckdb` for
the standalone KPI queries. Ports resolved at runtime; `twinflow_orders.ports.stubs` ships
`StaticInventory`, `InstantShipment`, `FixedAgentRoster`, `NoReturns`, `BaselineCostToServe`,
`NoDemandShaping`, and `StaticChannelMix` so the package runs alone. `BaselineCostToServe` returns
the customer's `annual_baseline_margin` divided by the periods per year, which is what makes the
customer-lifetime value calculation runnable before activity-based costing lands (section 5.2).

`ArrivalProcess` is the one place order arrivals are generated, and it is the consumer side of the
two demand-shaping seams. It multiplies its baseline intensity by whatever `DemandShapingPort`
returns for the period and samples the order's channel from whatever `ChannelMixPort` returns.
Both protocols are declared once in `twinflow-kernel` and imported by this package and by
`twinflow-commercial` (D-09), so the coupling 6a16 needs is a typed interface rather than a shared
module.

`AgentRosterPort` is named for the service agents it staffs, and is distinct from
`twinflow_workforce.ports.RosterPort`, which carries the whole-building roster. The two are separate
symbols with separate owners under D-09 rather than one name declared twice.

Standalone example: `examples/allocation_policy_bakeoff.py` runs 500 orders against a fixed supply
under all three allocation policies and prints fill rate by segment plus the Jain fairness index over
every demand in the run. A quality or planning reader can take this brick for the allocation policy
library alone.

### 2.2 `twinflow-procurement`

Purpose: procure-to-pay, strategic sourcing, contract management, spend analytics, and the buy-side
KPI stream.

Public API:

```python
from twinflow_procurement import RequisitionQueue, PurchaseOrderBook, ApprovalRouter
from twinflow_procurement.matching import ThreeWayMatcher, MatchTolerances, MatchException
from twinflow_procurement.payments import PaymentScheduler, TermsCalendar, DiscountEvaluator
from twinflow_procurement.sourcing import RfxEvent, BidCurve, WeightedScorecard, AwardEngine
from twinflow_procurement.sourcing import GreedyAwardStrategy, ExactAwardStrategy, AwardGapReport
from twinflow_procurement.contracts import Contract, TierSchedule, RebateAccrual, RenegotiationTrigger
from twinflow_procurement.spend import SpendClassifier, MaverickDetector, SavingsLedger
from twinflow_procurement.tactics import ForwardBuyEvaluator, ExpediteEvaluator, EoqValidator
from twinflow_procurement.tactics import SpotBuyEvaluator, SpotBuyDecision
from twinflow_procurement.ports import SupplierPort, InventoryPolicyPort, LandedCostPort, FreightQuotePort
from twinflow_procurement.ports import SpotPricePort, SupplierDagPort
```

`PurchaseRequisition` is the requisition type this package owns; the hiring requisition of the same
concept name lives in `twinflow-workforce` as `HiringRequisition` (D-09).

Depends on: `twinflow-kernel`, `twinflow-schemas`. `LandedCostPort` is satisfied by
`twinflow-trade` when installed; the null implementation returns duty zero. `SpotPricePort` is
satisfied by the transport and supplier packages when installed; the null implementation returns the
contract price plus the configured `spot_premium_default_pct`, which makes the spot-buy evaluator
runnable alone and biased against the spot buy rather than for it. `SupplierDagPort` is the seam to
E19's n-tier map; its null implementation returns `SupplierDag.unavailable()`, and the award engine
reports `max_tier2_concentration` as `unenforced` rather than as satisfied, so a missing map is never
read as an absence of hidden concentration.

Standalone example: `examples/rfx_award.py` runs a synthetic three-supplier RFQ with price-volume
curves and prints the weighted scorecard, the single-award and dual-award outcomes, the cost of
the resilience constraint, and the measured gap between the greedy award and the exact award.

### 2.3 `twinflow-trade` (E14)

Purpose: classification, tariff schedules, policy scenario overlays, landed cost, FTZ and drawback.

Public API:

```python
from twinflow_trade import Classification, TariffSchedule, DutyRate, LandedCostCalculator
from twinflow_trade.scenarios import ScenarioOverlay, RateShock, Retaliation, DeMinimisChange
from twinflow_trade.scenarios import apply_overlay, merge_overlays
from twinflow_trade.programs import ForeignTradeZone, DrawbackClaim, DutyDeferral
from twinflow_trade.ports import FreightCostPort, FxRatePort, MeioPort
```

Depends on: `twinflow-kernel`, `twinflow-schemas`. Classification, duty evaluation, overlay
composition, and landed cost are pure functions of their inputs and draw no randomness, which makes
this the smallest brick in this section and the easiest to adopt alone. One quantity in the package
is stochastic and it is declared as such: drawback refund timing draws from the
`root/trade/drawback` stream (section 6.9), so the package takes an `Rng` like every other package
rather than claiming to need none. Duty arithmetic stays reproducible without an `Rng`, and
`examples/landed_cost_scenarios.py` runs with the drawback program disabled to show that.

`MeioPort` is the seam through which a scenario re-run reaches multi-echelon inventory optimization
(6a8). Its null implementation returns `MeioDelta.unavailable()`, and every consumer renders that as
"not available" rather than as zero, so a missing planning package can never be read as no impact.

Standalone example: `examples/landed_cost_scenarios.py` prices one SKU from three origins under the
base schedule and three named scenario overlays and prints the re-ranked sourcing table.

### 2.4 `twinflow-workforce`

Purpose: hiring pipeline, onboarding learning curves, skills and certification gating,
cross-training, attrition, absenteeism prediction, and labor cost accounting.

Public API:

```python
from twinflow_workforce import Worker, WorkerRegistry, JobRole, WageTable
from twinflow_workforce.hiring import HiringRequisition, CandidatePipeline, TimeToFillModel
from twinflow_workforce.skills import Skill, Certification, SkillsMatrix, StationEligibility
from twinflow_workforce.learning import LearningCurve, WrightCurve, ProductivityRamp, ErrorRamp
from twinflow_workforce.attrition import AttritionHazard, TerminationClassifier, ReplacementCost
from twinflow_workforce.absence import AbsenceGenerator, AbsencePredictor, AbsenceForecast
from twinflow_workforce.engagement import ScheduleStabilityIndex, WeekendShiftRate, StrainTrend
from twinflow_workforce.costing import LaborLedger, HourType, BurdenModel
from twinflow_workforce.ports import StrainPort, RosterPort, DemandPlanPort
```

Depends on: `twinflow-kernel`, `twinflow-schemas`. Optional extra `[ml]` adds `scikit-learn` for the
absence predictor challenger; the baseline predictor has no ML dependency. Per D-04 the challenger
is constructed with `random_state` derived from the run seed through the RNG tree, with the
thread count pinned to one and the fitted artifact hashed; the hash is recorded in the provenance
sidecar and asserted by `test_absence_challenger_artifact_hash_is_stable`. The challenger reaches
the simulation only through the `Inference` port, so simulation mode can bind a recorded-response
adapter and the tape never depends on library-version numerics.

The engagement module is the behavioral measurement 6a14 asks for. It computes schedule stability,
weekend shift rate, and strain trend from state the twin already records, and publishes them as
metric samples for the LSS engine to chart. No survey instrument is modeled anywhere.

Standalone example: `examples/crosstrain_payback.py` runs a 12-week horizon with and without a
cross-training investment under an absenteeism shock and prints coverage, overtime hours, and the
payback period.

### 2.5 `twinflow-itops`

Purpose: ITSM, SRE observability and error budgets, DORA metrics, vulnerability and patch
economics, IEC 62443 zones and conduits, the detection-rule engine, RBAC, and backup drills.

Public API:

```python
from twinflow_itops import ConfigurationItem, CmdbGraph, ServiceCatalog
from twinflow_itops.itsm import Incident, Problem, Change, ChangeAdvisoryBoard, ChangeWindowPolicy
from twinflow_itops.sre import Sli, Slo, ErrorBudget, BurnRateAlert, GoldenSignals, DoraMetrics
from twinflow_itops.sre import BurnRateTable, derive_burn_rates
from twinflow_itops.telemetry import Span, TraceSample, LogRecord, TraceIndex, SpanDerivedMetric
from twinflow_itops.vuln import SyntheticCveFeed, Vulnerability, CvssV31, PatchWindowEvaluator
from twinflow_itops.vuln import ExposureModel, CvarObjective
from twinflow_itops.zones import SecurityZone, Conduit, ConduitMonitor, ZoneCrossing
from twinflow_itops.detect import DetectionRule, RuleRegistry, RuleEngine, RuleFixture
from twinflow_itops.correlate import CorrelationRule, CorrelationEngine, CorrelationWindow, Alert
from twinflow_itops.access import AccessRole, Permission, Grant, AccessDecision, RbacEngine
from twinflow_itops.backup import BackupSchedule, BackupCatalog, RestoreDrill, RpoRtoMeasurement
from twinflow_itops.ports import TelemetryPort, NetworkTapPort
from twinflow_kernel.ports import WhatIfPort, GrossProfitRatePort
```

Depends on: `twinflow-kernel`, `twinflow-schemas`. `NetworkTapPort` is the seam that makes conduit
monitoring identical in both DST modes: in simulation mode it is bound to the in-memory `Network`
middleware, in production mode to the broker bridge exporter. `WhatIfPort` is imported from the
kernel rather than redeclared, because `twinflow-finance` needs the same protocol and D-09 allows
one owner per public symbol.

The telemetry module carries the logs and traces half of 6a15's observability requirement. Without
it, deployment lead time and change-caused recovery time have no request-level evidence, which is
the gap section 5.6 closes.

The correlation module is the lightweight SIEM analog 6a15 names. Detection rules judge one event
stream; correlation rules join findings across zones inside a time window and raise a single
correlated alert, which is what makes IT-004's suggested next tool a component rather than a label.

Standalone example: `examples/patch_window_economics.py` takes one synthetic CVE, three candidate
windows, and a stubbed production cost curve, and prints the expected-cost ranking with the
risk-aversion weight swept from risk neutral to strongly risk averse.

### 2.6 `twinflow-commercial`

Purpose: promotions and demand shaping, sales pipeline and forecast bias, quota effects, NPI
cold-start, and the five-step S&OP cycle.

Public API:

```python
from twinflow_commercial.promotions import Promotion, LiftCurve, PullForwardKernel, CannibalisationMatrix
from twinflow_commercial.promotions import PromoCalendar, PromoFeatureFrame
from twinflow_commercial.channels import ChannelMixModel, ChannelMixState, DirichletDrift
from twinflow_commercial.pipeline import Opportunity, StageModel, RepBiasModel, QuotaCalendar
from twinflow_commercial.npi import NewProduct, BassDiffusion, AnalogProfile, ColdStartBlender
from twinflow_commercial.fva import FvaLadder, FvaStep, FvaReport
from twinflow_commercial.sop import SopCycle, ProductReview, DemandReview, SupplyReview
from twinflow_commercial.sop import RoughCutCapacityCheck, SupplyReviewMode
from twinflow_commercial.sop import SopReconciliation, ExecutiveMeeting, DecisionPacket, OneNumberPlan
from twinflow_commercial.maturity import PlanAdherence, DecisionLatency, OneNumberVariance
from twinflow_commercial.ports import ForecastPort, CapacityPort, PricingPort, DecisionRegisterPort
from twinflow_commercial.ports import PromoFeaturePort
from twinflow_kernel.ports import DemandShapingPort, ChannelMixPort
```

`SopReconciliation` is the S&OP step; the month-end close step of the same English name is
`CloseReconciliation` in `twinflow-finance` (D-09).

Three ports are outbound, which is what makes this package a demand-shaping engine rather than a
reporting layer. `PromoFeaturePort` hands the promotion calendar to the forecaster as a feature
frame, which is 6a16's requirement that the forecaster ingest the promo calendar as a feature.
`DemandShapingPort` gives the order arrival process a per-SKU per-period intensity multiplier.
`ChannelMixPort` gives it the drifting wholesale, e-commerce, and marketplace shares to sample the
channel from. The last two are declared in `twinflow-kernel` and implemented in `twinflow-orders`
(D-09); this package is the caller. Null implementations return a multiplier of 1.0 and the
configured static shares, so the package runs alone and a reader can see what each coupling carries.

Depends on: `twinflow-kernel`, `twinflow-schemas`.

Standalone example: `examples/promo_decomposition.py` generates 26 weeks of baseline demand, applies
one promotion, and prints the exact decomposition into incremental, pulled-forward, cannibalised,
and halo units with the conservation check.

### 2.7 `twinflow-finance`

Purpose: general ledger, subledgers, statements, standard costing and variance attribution,
inventory valuation, activity-based costing, FP&A, capex governance, month-end close, and controls.
Also carries E22 (AP/AR terms, cash-to-cash, working capital per echelon) because the working
capital calculation is a query over the same ledger and splitting it would duplicate the schema.

Public API:

```python
from twinflow_finance.money import Money, Currency, minor_units
from twinflow_finance.gl import ChartOfAccounts, Account, JournalEntry, JournalLine, Ledger, Period
from twinflow_finance.posting import PostingRule, PostingRuleSet, PostingEngine
from twinflow_finance.statements import ProfitAndLoss, BalanceSheet, CashFlow, TrialBalance
from twinflow_finance.costing import StandardCost, CostRollUp, VarianceEngine, VarianceAttribution
from twinflow_finance.inventory import ValuationMethod, WeightedAverage, Fifo, EandOReserve, CycleCountProgram
from twinflow_finance.activity_costing import ActivityPool, CostDriver, AbcModel, CostToServe
from twinflow_finance.fpa import DriverBasedBudget, RollingReforecast, VarianceBridge
from twinflow_finance.capex import CapexRequest, Appraisal, npv, irr, payback, PostInvestmentAudit
from twinflow_finance.close import CloseChecklist, CloseTask, Accrual, CloseReconciliation
from twinflow_finance.close import CloseMetrics, ClosingEntryGenerator, IncomeSummary
from twinflow_finance.controls import AuthorityMatrix, SodRule, Control, ControlLibrary, ControlTest
from twinflow_finance.working_capital import Dso, Dpo, Dio, CashToCash, EchelonWorkingCapital
from twinflow_finance.ports import ValuationSourcePort, ActivityRecordPort, GrantsPort
from twinflow_kernel.ports import WhatIfPort
```

The activity-costing module is named `activity_costing` rather than `abc` so it cannot be confused
with the standard library module of that name in a traceback or an import-graph report.

Depends on: `twinflow-kernel`, `twinflow-schemas`. Optional extra `[report]` adds the HTML statement
renderer, which writes through `Storage` and never opens a path itself. `numpy-financial` is a
test-only dependency used to cross-check NPV and IRR at float64 precision, never a runtime
dependency; the exactness gate for NPV is evaluated in `decimal`, because a float64 library cannot
witness a claim stated in more digits than float64 carries (section 7.3).

Standalone example: `examples/variance_drilldown.py` replays a fixture event log through the posting
rules and prints the gross margin bridge with each variance classified common cause or assignable
and each assignable variance expanded to its source events.

### 2.8 `twinflow-insurance` (E38)

Purpose: policies, cargo and business-interruption claims, experience-rated premiums, and total cost
of risk.

Public API:

```python
from twinflow_insurance import Policy, CoverageType, Limit, Deductible, WaitingPeriod, Sublimit
from twinflow_insurance import SublimitResolver
from twinflow_insurance.claims import Claim, ClaimLifecycle, CargoClaimTrigger, BiClaimTrigger
from twinflow_insurance.rating import RatingTable, ExposureBase, ExperienceModifier, PremiumQuote
from twinflow_insurance.tcor import TotalCostOfRisk, RiskTransferOption, RiskTransferComparison
from twinflow_insurance.ports import LossHistoryPort, SafetyMetricsPort
from twinflow_kernel.ports import GrossProfitRatePort
```

`SublimitResolver` maps a loss to at most one sublimit key by an explicit, ordered rule set, so the
sublimits shipped in config change the payout rather than sitting inert (section 5.9).

`GrossProfitRatePort` is declared once, in `twinflow-kernel`, and imported by both this package and
`twinflow-itops` (D-09). Both are satisfied by the same `fin.gross_profit_rate` event, so business
interruption loss and breach exposure are valued from one number rather than two.

Depends on: `twinflow-kernel`, `twinflow-schemas`.

Standalone example: `examples/deductible_vs_control.py` compares a higher deductible against a
risk-control capex over 1000 seeded loss draws and prints the TCOR distribution for each with the
significance test result.

### 2.9 Cross-package artifacts every package in this section contributes

| Artifact              | Path                                        | Purpose                                                                                             |
|-----------------------|---------------------------------------------|-----------------------------------------------------------------------------------------------------|
| Event schemas         | `/schemas/<domain>/<event>/v<major>.json`   | C3 registry, additive-only within a major version                                                   |
| Metric definitions    | `packages/<pkg>/metrics/<pkg>.metrics.yaml` | E26(b) governed semantic layer, merged at load                                                      |
| Stream manifest       | `packages/<pkg>/seeds.toml`                 | The RNG stream names this package draws from, checked against the `twinflow-rng` registry at import |
| Finding catalog       | `packages/<pkg>/findings/catalog.yaml`      | Finding codes, severity floors, dedupe keys, shelve policy                                          |
| Agent tool manifest   | `packages/<pkg>/tools/manifest.yaml`        | Tool name, Pydantic input and output model, required RBAC permission, autonomy tier                 |
| Config schema         | `/schemas/config/<pkg>.v1.json`             | C5 validation with line-numbered errors                                                             |
| Posting rule fixtures | `packages/<pkg>/tests/fixtures/postings/`   | One fixture per event type this package emits that has a GL consequence                             |
| Eval questions        | `packages/<pkg>/evals/<pkg>.evals.yaml`     | At least three questions per agent tool with ground truth computed from the simulation              |

The stream manifest is a declaration, not a second registry. `docs/design/variability-and-faults.md`
section A.4 makes `twinflow-rng` the only place allowed to construct a generator, and every stream
name in a `seeds.toml` must resolve there. A name present in a manifest and absent from the registry
fails at import with the offending name quoted, which is how a new draw gets a reviewed stream name
instead of a silent reuse of an existing one.

Process mining over the case notions this section supplies (order, PO, incident, service contact,
S&OP cycle, claim, close period) runs on `twinflow-procmine`, the Apache-2.0 miner this repository
implements per D-14. No package here imports an AGPL process mining library, because doing so would
place the whole work under AGPL and break the dual license.

## 3. Domain model

Conventions used throughout.

**Time.** All timestamps are sim-time from the `Clock` port (C2). No model here reads a wall clock.
Per D-02 the four places a wall clock may legally be read (the provenance sidecar writer, the paced
clock, the observability exporter, and operator log lines) are all outside this section's packages.

**Money.** All money is `Money(amount_minor: int, currency: str)` with integer minor units. Floating
point money is banned and a CI lint rejects `float` annotations on any field whose name matches
`(amount|price|cost|value|premium|duty|payout|salary|wage)`.

**Rounding.** Every money-producing formula in this section multiplies an integer minor-unit amount
by a rate, so the rounding contract is stated once here and implemented once in `Money`.

1. `Money.__mul__(rate)` evaluates in `decimal.Decimal` at a context precision of 34 significant
   digits and rounds the result to whole minor units with `ROUND_HALF_EVEN`. The mode is stated
   rather than inherited, because `decimal`'s default is already `ROUND_HALF_EVEN` and a reader must
   not have to know that to predict a cent.
2. Rounding happens exactly once per posted amount, at the point the amount becomes a
   `JournalLine`, a payout, a duty, or a price. Intermediate products stay in `Decimal`. A chain of
   three rates rounds once, not three times.
3. When a rounded total is split across dimension lines (cost center, station, SKU, customer,
   supplier, channel, lot, scenario), the split uses the largest-remainder method with the dimension
   key as the tie-break, so the lines sum to the total exactly and the allocation is deterministic.
   The residual never lands on an arbitrary line.
4. Property test `rounding_allocation_closes` asserts, for any total and any weight vector, that the
   allocated lines sum to the total and that each line differs from its unrounded share by less than
   one minor unit. Property test `money_multiply_is_half_even` asserts the mode at the boundary,
   including the two cases that separate half-even from half-up.

Without this contract `journal_balances`, `tcor_reconciles_to_gl`, and `variance_attribution_closure`
are not implementable as stated, because two paths to the same cent could disagree.

**Currency.** Version 1 is single-currency. Config validation rejects any document, rate table, or
authority row whose currency differs from `finance.functional_currency`, quoting the offending file,
line, and value. The `currency` field stays on every money-carrying model and the `FxRatePort` seam
stays declared, because removing them would make multi-currency a rewrite rather than an addition.
Multi-currency posting, translation, and revaluation are sequenced as a named ROADMAP milestone with
its dependency on E14 recorded; they are not dropped and they are not assumed away. Open question 1
records what that milestone must still decide.

**Identifiers.** All identifiers are deterministic strings derived from the run seed and a per-entity
counter, assigned from a declared id policy, never from a random UUID. This is what makes the
per-entity RNG streams of `docs/design/variability-and-faults.md` section A.2 addressable, and it is
what keeps the event log stable.

**Determinism, scoped per D-05.** Two tiers, and this section claims only what each tier supports.
Byte-identical: same seed, same resolved config, same platform, same pinned dependency set, checked
by hash equality over the event log, the GL table, and the generated statements. Value-equivalent:
same seed and config across platforms, where business events are identical and continuous fields
agree within a tolerance derived from measured divergence. The cross-platform job reports the
observed maximum divergence rather than asserting a number chosen in advance. Nowhere does this
section claim byte identity across platforms.

**Iteration order, per D-03.** No collection whose iteration order can reach an event payload, a
hash, or a control decision is a `set`. `SkillsMatrix`, `single_point_of_failure_stations`,
`CannibalisationMatrix`, the promoted SKU list, the conduit list, and the grant set are all sorted
sequences with a declared sort key. Where a set is the right semantic type, the iteration site
writes `sorted(s)` with the key named in a comment. Float summations over such a collection
(cannibalisation conservation, ABC pool totals, variance attribution) sum in sorted key order using
`math.fsum`, so the result does not depend on dictionary insertion history.

**Storage.** No model in this section carries a filesystem path. Artifacts are addressed by storage
key through the `Storage` port, which is what lets the same code run against a local directory, an
object store, or an in-memory fixture. Section 7.6's C1 lint bans `open(`, `pathlib.Path`,
`os.path`, and `shutil` in these packages alongside `time`, `random`, and `socket`. Config file
paths in section 6 are resolved once by the config loader, before any package is constructed, and
the loader hands each package parsed objects and storage keys. A directory key such as
`detections_dir` names a `Storage` prefix, and the rule loader enumerates it in lexicographic key
order so the rule set is the same set in the same order on every platform.

**Query determinism.** Several models carry SQL: `Sli.definition_sql`, `DetectionRule.query`,
`CorrelationRule` inputs, `Control.evidence_query`, and every metric expression in section 6.10.
Four rules make a query result part of a reproducible tape.

1. Every query that returns rows carries a total `ORDER BY`. The canonical order is
   `(sim_ts, producer_id, seq)` from D-07, and a query whose declared ordering is not total fails
   config validation with the query quoted. A query returning a single scalar is exempt and is
   marked `scalar: true` so the exemption is declared rather than inferred.
2. Floating-point aggregation over event rows uses an order-stable sum. The metric layer compiles
   `SUM` over a float column into a sum in the query's declared order, never into an engine-chosen
   parallel reduction, and integer minor units are summed as integers.
3. Any query feeding a control decision or an event payload runs against a snapshot of the historian
   pinned to a stated `sim_time` watermark, which is carried on the emitting event. A query that
   reads rows later than its watermark is a defect, and `test_query_respects_watermark` asserts it.
4. Engine version and the compiled SQL text are hashed into the metric definition's `query_hash`,
   which is recorded in the provenance sidecar. A columnar-engine upgrade that changes a number
   shows up as a hash change with a diff, rather than as a golden-file failure with no explanation.

### 3.1 `twinflow-orders`

#### Customer

| Field                       | Type                                             | Notes                                                                         |
|-----------------------------|--------------------------------------------------|-------------------------------------------------------------------------------|
| `customer_id`               | str                                              | Deterministic                                                                 |
| `segment`                   | enum `contract` \| `spot` \| `marketplace`       | Drives promise rule and allocation tier                                       |
| `allocation_tier`           | int 1..5                                         | 1 is highest. Invariant: contract customers have tier <= 3                    |
| `sla`                       | `ServiceLevelAgreement`                          | Promise lead time, on-time definition, fill-rate commitment, penalty schedule |
| `credit_limit`              | Money                                            | Credit check stub compares open AR plus order value                           |
| `payment_terms_id`          | str                                              | Resolves in `twinflow-finance` terms calendar                                 |
| `region`                    | str                                              | Feeds transport lane selection                                                |
| `channel`                   | enum `wholesale` \| `ecommerce` \| `marketplace` | Home channel. An order's channel is drawn per order from the drifting mix     |
| `satisfaction`              | float 0..1                                       | State, updated by service outcomes                                            |
| `contract_commitment_units` | int \| None                                      | Volume commitment honored first under hybrid allocation                       |
| `annual_baseline_margin`    | Money                                            | Fallback margin used by `BaselineCostToServe` only, never by the ABC path     |

Invariants: `0.0 <= satisfaction <= 1.0`; a customer with `segment == contract` has a non-null
`sla`; `allocation_tier` is stable for the life of a run unless a `customer.tier_changed.v1` event
is emitted.

`annual_baseline_margin` exists so the customer-lifetime-value calculation is runnable before
activity-based costing lands. It is read only through `CostToServePort`'s null implementation, and
`customer.churned` records which implementation produced the margin it used, so a reader can always
tell a modeled contribution from a fallback (section 5.2).

#### SalesOrder

| Field                 | Type                         | Notes                                                               |
|-----------------------|------------------------------|---------------------------------------------------------------------|
| `order_id`            | str                          | Process-mining case id for order-to-cash                            |
| `customer_id`         | str                          |                                                                     |
| `channel`             | enum                         | Sampled by `ArrivalProcess` from `ChannelMixPort` shares at capture |
| `captured_at`         | SimTime                      |                                                                     |
| `requested_ship_date` | SimDate                      |                                                                     |
| `promise_date`        | SimDate \| None              | Set by the promise engine, null until promised                      |
| `promise_source`      | enum, five values, see below | The supply tier the promise was taken from                          |
| `promise_breached_at` | SimTime \| None              | Set when the promise date passes with no delivery confirmation      |
| `status`              | enum, see state machine      |                                                                     |
| `lines`               | list[OrderLine]              | Non-empty                                                           |
| `holds`               | list[Hold]                   |                                                                     |
| `priority_score`      | float                        | Computed, not stored input                                          |
| `value`               | Money                        | Sum of line extended price                                          |

`promise_source` takes one of five values, one per supply tier the promise engine tries:
`on_hand`, `in_transit`, `scheduled_receipt`, `ctp`, `default_lead_time`. The first three are the
available-to-promise tiers and the fourth is capable-to-promise. They are separate values, not one
`atp` value, because promise reliability decomposed by source is the analysis section 5.1 claims and
a collapsed enum cannot answer whether the capable-to-promise path is trustworthy relative to a
scheduled receipt. The enum is the same list as `orders.promise.sources` in config, and a config
validation rule asserts the two are identical so they cannot drift.

Status set: `CAPTURED`, `VALIDATED`, `ON_HOLD`, `PROMISED`, `ALLOCATED`, `PARTIALLY_ALLOCATED`,
`RELEASED`, `PICKING`, `PACKED`, `STAGED`, `SHIPPED`, `INVOICED`, `CLOSED`, `CANCELED`,
`REJECTED`. Fifteen statuses.

Legal transitions (the only ones the state machine accepts):

```
CAPTURED    -> VALIDATED | REJECTED | CANCELED
VALIDATED   -> ON_HOLD | PROMISED | CANCELED
ON_HOLD     -> VALIDATED | CANCELED
PROMISED    -> ALLOCATED | PARTIALLY_ALLOCATED | ON_HOLD | CANCELED
PARTIALLY_ALLOCATED -> ALLOCATED | RELEASED | CANCELED
ALLOCATED   -> RELEASED | CANCELED
RELEASED    -> PICKING | CANCELED
PICKING     -> PACKED | CANCELED
PACKED      -> STAGED
STAGED      -> SHIPPED
SHIPPED     -> INVOICED
INVOICED    -> CLOSED
```

Twenty-five legal transitions. `CAPTURED -> CANCELED` and `VALIDATED -> CANCELED` are present
because `cancel` is a legal `OrderChangeRequest.type` at any `stage_at_request`, and a request type
the state machine cannot execute is a contradiction rather than a policy.

Invariant `order_state_machine_legality`: no transition outside this table is ever recorded, and
`CANCELED` is unreachable from `PACKED` onward (a cancel after pack becomes a return, routed to
6a4, which is exactly why the change-cost model rises at that boundary).

#### OrderLine

`line_id`, `order_id`, `sku`, `qty_ordered`, `qty_allocated`, `qty_backordered`, `qty_picked`,
`qty_shipped`, `qty_cancelled`, `qty_substituted`, `unit_price: Money`, `substitution_of: str|None`,
`line_promise_date`.

Invariant `order_quantity_conservation`, checked after every mutation:
`qty_ordered == qty_allocated + qty_backordered + qty_cancelled` and
`qty_shipped <= qty_picked <= qty_allocated`.

#### Allocation

`allocation_id`, `line_id`, `source: enum on_hand|in_transit|scheduled_receipt|ctp_build`,
`qty`, `lot_ids: list[str]`, `allocated_at`, `released_at`, `policy_run_id`.

Invariant `allocation_no_oversell`: for every lot, the sum of open allocations never exceeds the
lot's on-hand quantity as reported by `InventoryAvailabilityPort` at the allocation instant.

#### Backorder

`backorder_id`, `line_id`, `qty`, `created_at`, `aged_days` (derived), `fill_priority` (recomputed
each allocation run), `promised_recovery_date`.

#### Hold

`hold_id`, `order_id`, `type: enum credit|fraud|quality|trade_compliance|price`, `placed_at`,
`placed_by`, `released_at`, `released_by`, `reason`.

#### OrderChangeRequest

`change_id`, `order_id`, `type: enum qty_increase|qty_decrease|date_pull_in|date_push_out|
address_change|line_add|line_remove|cancel`, `requested_at`, `stage_at_request` (the order status
when the request landed), `decision: enum accepted|rejected|accepted_with_cost`,
`cost: Money`, `rework_minutes: float`, `rejection_reason`.

#### SubstitutionRule

`from_sku`, `to_sku`, `ratio: float`, `allowed_segments: list[str]`,
`requires_customer_approval: bool`, `price_treatment: enum hold_original|use_substitute`.

#### ServiceContact

`contact_id` (process-mining case id for the service process), `customer_id`, `order_id | None`,
`reason_code: enum wismo|late_delivery|short_ship|damage|wrong_item|invoice_dispute|
return_request|order_change|other`, `channel: enum phone|email|chat`, `created_at`,
`caused_by_event_id` (mandatory, never null except for the `other` reason code),
`queued_at`, `answered_at`, `agent_id`, `handle_seconds`, `resolved_first_contact: bool`,
`escalation_level: int 0..3`, `abandoned: bool`, `resolution_at`.

Invariant `contact_generation_causality`: for every contact with a non-null `caused_by_event_id`,
that event exists in the log and its sim-time is strictly earlier than `created_at`.

Every reason code has a producing event, including `wismo`. A promise date that passes without a
delivery confirmation emits `orders.promise_breached`, and that event is the causation for every
WISMO contact. The absence of an event cannot be a cause, so the event that records the absence is
emitted instead.

#### ServiceAgent

`agent_id`, `worker_id` (links to `twinflow-workforce`), `skills: list[str]`,
`tool_visibility: enum none|order_header|order_detail|twin_grounded`,
`aht_distribution` (per reason code), `shift_id`.

#### PerfectOrderRecord

`order_id`, `complete: bool`, `on_time: bool`, `damage_free: bool`, `correctly_invoiced: bool`,
`perfect: bool` (the AND), `failed_components: list[str]`, `evaluated_at`.

Invariant `perfect_order_bound`: over any population, `perfect_order_rate <= min(component rates)`.

#### PromiseBreach

`order_id`, `promise_date`, `breached_at`, `elapsed_days` (recomputed each day until delivery or
cancellation), `open_at_breach: bool`. The record is what gives ORD-004's u-chart a countable
exposure: the denominator is order-days open past promise, and the numerator is WISMO contacts. A
rate with no denominator is not a u-chart, so the denominator is a modeled quantity rather than an
assumed constant.

### 3.2 `twinflow-procurement`

**PurchaseRequisition**: `req_id`, `source: enum reorder_point|manual|project|expedite|spot_buy`,
`sku`, `qty`, `need_by`, `requester_role`, `cost_center`, `category_id`, `status: enum open|sourced|
converted|canceled`, `triggering_event_id` (the reorder signal from the inventory optimizer, or the
supplier slip event that opened the spot-buy question).

**PurchaseOrder**: `po_id` (process-mining case id for procure-to-pay), `supplier_id`, `lines`,
`contract_id | None`, `incoterm: enum EXW|FCA|FOB|CIF|DAP|DDP`, `currency`, `payment_terms_id`,
`status`, `approval_chain: list[ApprovalStep]`, `created_at`, `sent_at`, `acknowledged_at`,
`confirmed_dates: dict[line_id, SimDate]`, `buy_mode: enum contract|spot`.

PO status set and legal transitions:

```
DRAFT -> PENDING_APPROVAL -> APPROVED -> SENT -> ACKNOWLEDGED
ACKNOWLEDGED -> PARTIALLY_RECEIVED | RECEIVED
PARTIALLY_RECEIVED -> PARTIALLY_RECEIVED | RECEIVED
RECEIVED -> CLOSED
PENDING_APPROVAL -> REJECTED
any state before the first receipt -> CANCELED
```

`ACKNOWLEDGED -> RECEIVED` is direct, because a single full receipt is the common case and a chain
that forces every order through `PARTIALLY_RECEIVED` would put a state in the log that never
happened.

The invoice is not a PO state. `INVOICED`, `MATCHED`, and `PAID` are gone from this list and live on
`SupplierInvoice` instead, because an invoice can arrive with no PO at all, can arrive before any
receipt, and can cover lines from several POs. Modeling invoicing as a PO state made three of the
declared match exception classes unreachable. The two aggregates are linked by reference, not by a
shared status field, and a PO can reach `CLOSED` with an unmatched invoice still open against it,
which is exactly the condition the accrual for goods received not invoiced exists to cover.

Which PO states admit an invoice: `SENT`, `ACKNOWLEDGED`, `PARTIALLY_RECEIVED`, `RECEIVED`, and
`CLOSED`. An invoice referencing a PO in `DRAFT`, `PENDING_APPROVAL`, `APPROVED`, `REJECTED`, or
`CANCELED` is classified `invoice_against_invalid_po` rather than rejected silently.

**POLine**: `po_line_id`, `sku`, `qty_ordered`, `qty_received`, `qty_invoiced`, `unit_price: Money`,
`contract_price: Money | None`, `hs_code`, `country_of_origin`, `requested_date`, `confirmed_date`.

Invariant `receipt_never_exceeds_order_beyond_tolerance`:
`qty_received <= qty_ordered * (1 + over_receipt_tolerance_pct)`.

**ApprovalStep**: `step_index`, `required_role`, `threshold: Money`, `approver_id`, `decided_at`,
`decision`, `delegated_from`. Invariant `approval_authority`: no step is marked approved by a
subject whose authority limit for that category is below the PO value, and the approver is never
the requester (`sod_requester_not_approver`).

**SupplierInvoice**: an aggregate in its own right with its own lifecycle. `invoice_id`,
`supplier_id`, `po_id | None`, `lines`, `subtotal`, `tax`, `freight`, `duty`, `total`,
`invoice_date`, `received_at`, `duplicate_of | None`,
`status: enum RECEIVED|MATCHED|EXCEPTION|APPROVED|PAID|REJECTED`.

Invoice legal transitions:

```
RECEIVED  -> MATCHED | EXCEPTION | REJECTED
EXCEPTION -> MATCHED | REJECTED
MATCHED   -> APPROVED -> PAID
```

Because the invoice is independent of the PO, every declared exception class is reachable. An
invoice with no `po_id` reaches `missing_po`. An invoice whose PO exists but has no receipt against
the invoiced lines reaches `missing_receipt`, which happens whenever an invoice arrives while the PO
sits in `SENT` or `ACKNOWLEDGED`. VG-PRC-01's promise that every exception class is produced is
satisfiable under this model, and it was not while invoicing was a PO state.

**ThreeWayMatchResult**: `match_id`, `po_id | None`, `receipt_ids`, `invoice_id`,
`result: enum matched|price_mismatch|qty_mismatch|missing_receipt|missing_po|duplicate_invoice|
uom_mismatch|freight_mismatch|tax_mismatch|invoice_against_invalid_po`, `variance_amount: Money`,
`tolerance_applied`, `opened_at`, `resolved_at`, `resolution: enum auto_accept|credit_memo|
price_correction|receipt_correction|reject`, `handler_id`.

**Payment**: `payment_id`, `supplier_id`, `invoice_ids`, `scheduled_for`, `executed_at`,
`amount`, `discount_taken: Money`, `discount_available: Money`, `terms_id`.

**RfxEvent**: `rfx_id`, `category_id`, `volume_forecast: dict[period, qty]`,
`invited_suppliers`, `issued_at`, `bid_deadline`, `criteria: list[ScoringCriterion]`,
`award_constraints: AwardConstraints`.

**ScoringCriterion**: `name`, `weight: float`, `direction: enum lower_better|higher_better`,
`normalization: enum min_max|z_score|ratio_to_best`, `source: enum bid|scorecard|risk_map`.
Invariant: weights sum to 1.0 within 1e-9.

**Bid**: `bid_id`, `rfx_id`, `supplier_id`, `price_curve: list[(break_qty, unit_price)]`,
`lead_time_days`, `capacity_units_per_period`, `quality_ppm_history`, `payment_terms_offered`,
`submitted_at`. Invariant `price_curve_monotone`: unit price is non-increasing in break quantity.

**AwardConstraints**: `min_suppliers`, `max_share_per_supplier`, `must_include`, `must_exclude`,
`total_volume`, `max_concentration_by_tier2_node` (reads the E19 DAG when available).

**Contract**: `contract_id`, `supplier_id`, `category_id`, `start`, `end`,
`tier_schedule: list[(cumulative_volume, unit_price)]`, `volume_commitment`,
`rebate: RebateTerm | None`, `price_index_escalator | None`, `renegotiation_lead_days`,
`auto_renew: bool`.

**RebateTerm**: `basis: enum retrospective|incremental`, `tiers: list[(threshold, rate)]`,
`settlement_period`. Invariant `rebate_never_exceeds_spend`.

**SpendRecord**: `spend_id`, `source_document_id`, `supplier_id`, `category_path: list[str]`
(three-level synthetic taxonomy), `amount`, `contract_id | None`, `is_maverick: bool`,
`leakage: Money` (zero when not maverick).

**SavingsEntry**: `entry_id`, `kind: enum savings|avoidance`, `category_id`, `supplier_id`,
`baseline_method: enum prior_price|market_index|budget|announced_increase`,
`baseline_unit_price`, `achieved_unit_price`, `volume`, `amount`, `evidence_event_ids`,
`gl_posting_id | None`.

Invariant `savings_baseline_is_gl_auditable`: an entry with `kind == savings` has
`baseline_method == prior_price` and a non-null `gl_posting_id` that resolves to a `material_price`
variance posting (PPV). An entry with any other baseline method has `kind == avoidance`, a null
`gl_posting_id`, and at least one entry in `evidence_event_ids`.

The restriction is not a preference, it is what the chart of accounts can witness. Section 5.8's
posting table records a price difference against standard cost, which is the PPV account. No account
records a difference against a market index, a budget line, or an announced increase, so an entry on
those baselines has nothing in the ledger to point at. Calling it a saving and demanding a posting id
would make the invariant unsatisfiable; calling it an avoidance and demanding event evidence makes it
checkable. The README limitations section states plainly that only prior-price savings reach the
P&L, which is the honest version of the claim procurement organizations make.

Invariant `savings_avoidance_disjoint` is unchanged: no event id appears as evidence in both an
entry with `kind == savings` and an entry with `kind == avoidance`.

**SpotBuyDecision**: the fourth tactical decision 6a13 names, alongside forward buy, economic order
quantity, and expediting. `decision_id`, `triggering_event_id` (the supplier slip or the shortage
that opened the question), `sku`, `qty_short`, `need_by`, `contract_supplier_id`,
`contract_unit_price`, `spot_unit_price` (from `SpotPricePort`), `spot_lead_time_days`,
`contract_recovery_date`, `stockout_cost_avoided: Money`, `price_premium: Money`,
`quality_risk_ppm_delta`, `contract_penalty: Money` (any minimum-volume or exclusivity charge the
contract levies on an off-contract buy), `net_benefit: Money`,
`decision: enum spot|wait_for_contract|expedite_contract`, `decided_by`, `decided_at`.

`net_benefit` is `stockout_cost_avoided - price_premium - contract_penalty - quality_cost`, where
`quality_cost` is `quality_risk_ppm_delta` times the units times the standard cost of an external
failure from 6a11. Invariant `spot_buy_never_beats_available_contract`: when the contract supplier
can still meet `need_by`, `decision` is never `spot`, because a spot buy that is not driven by a
slip is maverick spend and is classified as such rather than as a tactic. The decision is recorded
whichever way it goes, so the ledger of declined spot buys is as auditable as the ledger of taken
ones.

### 3.3 `twinflow-trade` (E14)

**Classification**: `sku_id`, `hs_code` (6 digit heading plus optional national 4 digit suffix,
fully synthetic values drawn from the public HS nomenclature structure), `country_of_origin`,
`origin_rule: enum wholly_obtained|substantial_transformation|tariff_shift`,
`preferential_program_id | None`, `classified_at`, `classified_by`.

**DutyRate**: `hs_code`, `origin_country`, `destination_country`, `effective_from`,
`effective_to | None`, `kind: enum ad_valorem|specific|compound`, `ad_valorem_pct: float`,
`specific_per_unit: Money`, `uom`. Invariant `no_overlapping_effectivity` for the same key tuple.

**TariffSchedule**: an immutable, versioned collection of `DutyRate` rows with a `schedule_id` and
content hash. Loading the same YAML twice yields the same hash (C1).

**ScenarioOverlay**: `scenario_id`, `name`, `deltas: list[RateDelta]`,
`de_minimis_threshold: Money | None`, `retaliation_of: str | None`, `effective_from`,
`narrative`. `RateDelta` targets by `(hs_chapter or hs_code, origin_country, destination_country)`
and carries `additive_pct` and `multiplicative_factor`.

Two operations, two signatures. `apply_overlay(schedule, overlay) -> schedule` produces a new
schedule. `merge_overlays(overlay, overlay) -> overlay` produces a single overlay from two. The
single `compose` name previously stood for both, which made its associativity invariant unstatable:
the outer call took a schedule and the inner call took two overlays, so the two sides of the equation
did not have the same type.

The merge rule is stated because `additive_pct` and `multiplicative_factor` do not commute and the
shipped scenarios overlap. A merged overlay carries, per target, `additive_total: Decimal` and
`factors: list[Decimal]` in `trade.active_scenarios` order. `merge_overlays` concatenates the factor
lists and sums the additive terms in `Decimal`, so the merged form is canonical and comparable
without a float product. Targets are matched most specific first: an `hs_code` delta wins over an
`hs_chapter` delta covering the same code, and two deltas at the same specificity for the same
target merge by the rule above.

Every delta is expressed against the **base schedule rate**, never against the running overlaid
rate. The effective rate for a target is
`(base_rate + additive_total) * prod(factors)` evaluated left to right in `Decimal`. Defining the
deltas against the base is what makes overlay order irrelevant to the additive part and makes the
multiplicative part depend only on the declared list order, rather than on how many overlays
happened to be applied before.

Invariants, each a property test over generated overlays with deliberately overlapping targets:
`merge_overlays` is associative on the canonical form for any three overlays;
`apply_overlay(apply_overlay(base, A), B)` and `apply_overlay(base, merge_overlays(A, B))` produce
the same schedule content hash for any A and B; deactivating every overlay restores the base
schedule to the same content hash. The previous invariant held only for non-overlapping targets,
which proved nothing about the configuration the repository actually ships, since
`retaliation_mirror` can overlap `rate_shock_plastics`.

**LandedCost**: `sku_id`, `supplier_id`, `qty`, `unit_price`, `freight`, `insurance`,
`duty`, `broker_fee`, `handling`, `total`, `unit_landed_cost`, `incoterm`, `schedule_id`,
`scenario_id | None`, `computed_at`. Invariant `landed_cost_monotone_in_duty`.

**ForeignTradeZone**: `zone_id`, `admission_events`, `withdrawal_events`,
`inverted_tariff_allowed: bool`. Invariant `ftz_duty_neutrality`: for goods admitted to an FTZ and
later withdrawn for domestic consumption at an unchanged rate, total duty paid equals the duty that
would have been paid on direct import; only the payment date differs.

**DrawbackClaim**: `claim_id`, `export_event_ids`, `import_duty_paid`, `refund_rate`,
`claim_filed_at`, `refund_received_at`, `status`. Invariant `drawback_bounded`:
`refund <= import_duty_paid * refund_rate` and `refund_rate <= 1.0`.

### 3.4 `twinflow-workforce`

**Worker**: `worker_id`, `role_id`, `hire_date`, `termination_date | None`, `wage_rate: Money`,
`shift_pattern_id`, `home_station_id`, `certifications: list[CertificationHolding]`,
`tenure_days` (derived), `cumulative_units_produced` (drives the learning curve),
`productivity_multiplier` (derived), `error_rate_multiplier` (derived),
`strain_index` (read from `StrainPort`, owned by 6a10),
`overtime_hours_rolling_4w`, `weekend_shifts_rolling_8w`, `schedule_stability_index`,
`attrition_hazard` (derived, recomputed weekly).

Invariant `no_work_after_termination`: no labor record exists for a worker with sim-time beyond
`termination_date`.

**JobRole**: `role_id`, `title`, `base_wage`, `burden_pct`, `required_certifications`,
`time_to_fill_distribution`, `recruiting_cost`, `target_headcount_driver` (which twin metric drives
required headcount). Named `JobRole` because `AccessRole` in `twinflow-itops` is a different concept
and D-09 allows one owner per public symbol.

**HiringRequisition**: `hr_req_id`, `role_id`, `opened_at`, `target_start`, `status`,
`pipeline: CandidatePipeline`, `filled_at | None`, `time_to_fill_days` (derived).

**CandidatePipeline**: ordered stages `sourced -> screened -> interviewed -> offered -> accepted ->
started`, each with a conversion probability and a time-in-stage distribution. Invariant
`pipeline_monotone`: a candidate never moves backwards; a drop is terminal.

**Certification**: `cert_id`, `name`, `stations_unlocked`, `training_hours`, `trainer_role`,
`validity_days`, `renewal_hours`. **CertificationHolding**: `worker_id`, `cert_id`, `granted_at`,
`expires_at`, `lapsed: bool`.

Invariant `certification_gating`: no task assignment exists where the assigned worker lacks a valid,
unexpired holding of every certification the station requires at the assignment's sim-time. This is
enforced at assignment time and asserted as a property over the whole event log.

**SkillsMatrix**: sparse matrix of `(worker_id, station_id) -> proficiency 0..1` derived from
certifications and cumulative station hours. Backed by a dict keyed on the pair and iterated as
`sorted(matrix, key=lambda k: (k.station_id, k.worker_id))` wherever the iteration can reach an
event, a hash, or a decision (D-03). `StationEligibility.eligible(worker, station, t)` returns a
boolean plus the blocking reason.

Derived metric `single_point_of_failure_stations`: stations with exactly one eligible worker on the
current roster, returned as a list sorted by `station_id`, never as a set. Raised as finding HR-005,
and the finding's `evidence_event_ids` inherit that order, so the log is stable across processes
with different hash seeds. CI runs the determinism scenario twice under different `PYTHONHASHSEED`
values and compares hashes.

**EngagementSnapshot**: `worker_id`, `period`, `schedule_stability_index`,
`weekend_shift_rate_8w`, `strain_trend_slope`, `overtime_pct_4w`, `sample_count`. Published weekly
per worker and aggregated per shift and per station.

This is the behavioral engagement measurement 6a14 requires, and it is behavioral precisely
because every input is a quantity the twin already records from the roster, the labor ledger, and
the ergonomics layer. No survey exists in the model. The three leading indicators go on control
charts (section 7.4), which is what the requirement asks for: engagement trended, not surveyed.

`schedule_stability_index` is `1 - (shift-start changes inside the notice window / shifts worked)`
over the trailing eight weeks, bounded in [0, 1]. `weekend_shift_rate_8w` is weekend shifts over
shifts worked in the same window. `strain_trend_slope` is the ordinary-least-squares slope of the
worker's strain index over the trailing eight weeks, in strain units per week, read from
`StrainPort` and owned by 6a10.

**LearningCurve**: Wright log-linear cumulative-average model.
`cumulative_average_hours(x) = a * x**b` where `b = ln(learning_rate) / ln(2)`, `a` is the
first-unit time, and `x` is cumulative units produced. Productivity multiplier at unit `x` is
`a / marginal_hours(x)` normalized so a fully ramped worker equals 1.0, with a configured
`plateau_units` beyond which the multiplier is clamped. Error rate uses the same functional form
with its own `error_learning_rate` and floor.

**AttritionHazard**: discrete-time hazard evaluated weekly.

```
logit(p_quit_week) = b0
                   + b_ot   * overtime_hours_rolling_4w
                   + b_strain * strain_index
                   + b_under * understaffing_ratio_rolling_4w
                   + b_sched * (1 - schedule_stability_index)
                   + b_wknd  * weekend_shifts_rolling_8w
                   + f_tenure(tenure_days)
```

`f_tenure` is a piecewise-linear spline with knots in config (new hires and long-tenure workers have
different baseline hazards). All coefficients live in config and are documented as illustrative
synthetic values, not fitted to any real workforce data.

**Termination**: `worker_id`, `at`, `reason: enum voluntary|involuntary|end_of_assignment`,
`performance_percentile: float 0..1`, `regretted: bool`, `replacement_cost: ReplacementCost`.

`regretted` is true when the reason is `voluntary` and `performance_percentile` exceeds
`attrition.regret_threshold_percentile`. The percentile is not drawn at termination time. It is a
provisioned worker attribute, drawn once from the `provision.workforce.W-<id>.performance_percentile`
stream before the sim clock starts, following the provisioning rule in
`docs/design/variability-and-faults.md` section A.2. Drawing it at termination would make the
regretted flag depend on how many workers quit before this one, which is the draw-order hazard that
section A.3 names.

**ReplacementCost**: `recruiting: Money`, `onboarding_labor: Money`,
`ramp_loss: Money` (the integral of the productivity gap over the ramp period, valued at the
station's contribution per hour), `backfill_overtime: Money`, `total`.

**AbsenceRecord** and **AbsenceForecast**: per worker per day, `probability`, `predicted: bool`,
`actual: bool`, `driver_contributions: dict[str, float]`. The forecast is published for E23.

**LaborLedger** entries: `worker_id`, `date`, `station_id`, `activity_id`,
`hour_type: enum regular|overtime|double_time|training|idle|absent_paid`, `hours`,
`rate`, `burden`, `cost`, `charged_to: enum direct|indirect`. Invariant `hours_conservation`:
per worker per day, ledger hours equal roster hours minus absence hours plus recorded overtime.

### 3.5 `twinflow-itops`

**ConfigurationItem**: `ci_id`, `name`, `type: enum broker|historian|mes_analog|edge_gateway|
dashboard|agent_service|twin_service|database|ca`, `version: semver`, `zone_id`,
`purdue_level: int 0..5`, `depends_on: list[ci_id]`, `owner_role`, `slo_id | None`,
`patch_requires_production_window: bool`, `criticality: int 1..4`.

Invariant `cmdb_acyclic`: `depends_on` forms a DAG.

**Sli**: `sli_id`, `ci_id`, `signal: enum latency|traffic|errors|saturation`,
`definition_sql`, `good_events_expr`, `valid_events_expr`, `unit`.
**Slo**: `slo_id`, `sli_id`, `target: float`, `window_days: int`, `objective_kind: enum
availability|latency_percentile`, `threshold`.
**ErrorBudget**: derived, `budget_seconds_or_events`, `consumed`, `remaining`, `burn_rate_1h`,
`burn_rate_6h`, `exhausted_at | None`.
**BurnRateTable**: derived at config load from `window_days` and the declared budget fractions, not
stored as literals. `derive_burn_rates(window_days, fraction, long_window)` returns
`fraction * window_days * 24 / long_window_hours`, the formula published in the Google SRE Workbook
chapter 5. Section 6.5 states the shipped values and section 7.3 states the gate.

**Span**: `span_id`, `trace_id`, `parent_span_id | None`, `ci_id`, `operation`, `started_at`,
`ended_at`, `duration_ms`, `status: enum ok|error`, `attributes: dict[str, str]`,
`sampled_by: enum head|tail|always`. Spans carry sim-time from the `Clock` port like every other
timestamp in this section.

**TraceSample**: `trace_id`, `root_span_id`, `span_count`, `critical_path_span_ids: list[str]`,
`total_duration_ms`, `error_span_count`, `case_id` (the business case the request belongs to, when
one exists). The critical path is what makes deployment lead time and change-caused recovery time
measurable at request level rather than inferred from ticket timestamps.

**LogRecord**: `log_id`, `ci_id`, `severity: enum debug|info|warn|error|fatal`, `at`, `template_id`
(the structured message template, so log volume is countable per template rather than per rendered
string), `fields: dict[str, str]`, `trace_id | None`, `span_id | None`.

Three derived metrics come from spans and logs and appear in the semantic layer:
`request_error_rate`, `request_latency_p95_ms`, and `log_error_rate_per_1k_requests`. Golden signals
in section 5.6 read the same span stream, so the observability claim rests on modeled evidence
rather than on a stated intention.

Invariants: `trace_spans_form_a_tree` (every non-root span's parent exists in the same trace and the
parent's interval contains the child's); `span_time_is_sim_time` (no span timestamp comes from a
wall clock).

**Incident**: `inc_id` (process-mining case id for the ITSM process), `ci_id`, `severity: P1..P4`,
`detected_at`, `detection_source: enum monitor|user_report|detection_rule|drill`,
`acknowledged_at`, `mitigated_at`, `resolved_at`, `closed_at`, `caused_by_change_id | None`,
`problem_id | None`, `impact: ImpactAssessment`.
Derived: `mtta = acknowledged_at - detected_at`, `mttr = resolved_at - detected_at`.

**Problem**: `problem_id`, `linked_incidents`, `root_cause_method` (shared RCA toolkit with 6a11),
`known_error_published_at`, `workaround`, `permanent_fix_change_id | None`.

**Change**: `chg_id`, `ci_id`, `type: enum standard|normal|emergency`, `requested_window`,
`implemented_at`, `duration_minutes`, `risk_score`, `has_rollback_plan: bool`,
`approvals: list[ApprovalStep]`, `outcome: enum successful|failed|rolled_back`,
`caused_incident_id | None`.

**ChangeWindowPolicy**: `freeze_windows: list[(dow, start_hour, end_hour)]`,
`risk_multipliers: dict`, `emergency_override_role`, `error_budget_gate: bool`.

**Vulnerability**: `vuln_id` (format `TWF-CVE-<year>-<seq>`, deliberately not a real CVE
identifier), `affected_component`, `affected_version_range`, `cvss_v31_vector`, `base_score`,
`exploit_probability` (a synthetic EPSS analog in 0..1), `known_exploited: bool`,
`published_at`, `patch_available_at`, `remediation: PatchAction`.

**PatchAction**: `vuln_id`, `ci_id`, `requires_window: bool`, `window_minutes`,
`decision: enum patch|defer|compensating_control`, `deferred_until | None`,
`accepted_risk_amount: Money`, `decided_by`, `decision_event_id`.

**SecurityZone**: `zone_id`, `name`, `purdue_level`, `criticality`, `member_ci_ids`,
`security_level_target: SL-T 1..4` (IEC 62443 vocabulary).
**Conduit**: `conduit_id`, `src_zone`, `dst_zone`, `allowed_protocols`, `allowed_ports`,
`direction: enum unidirectional|bidirectional`, `baseline_profile: TrafficBaseline`.
**ZoneCrossing**: every message the `NetworkTapPort` observes crossing a zone boundary, with
`src_ci`, `dst_ci`, `protocol`, `bytes`, `at`, `conduit_id | None` (null means no conduit permits
this flow, which is a violation by construction).

**DetectionRule**: `rule_id`, `version: semver`, `title`, `query` (over the historian event tables),
`severity`, `attack_ics_technique_ids: list[str]`, `suppression_window`,
`fixtures: list[RuleFixture]`.
**RuleFixture**: `kind: enum positive|negative`, `event_log_key`, `expected_fire_count`. The fixture
is addressed by storage key and read through the `Storage` port, never by filesystem path.

The technique identifiers come from the MITRE ATT&CK for ICS matrix, published at
`https://attack.mitre.org/matrices/ics/` (retrieved 2026-08-09, matrix version v19). Config
validation rejects a technique id that does not match the published identifier grammar, and the
shipped rules record the matrix version they were written against so a matrix revision is a visible
config change rather than a silent drift.

**CorrelationRule**: `corr_rule_id`, `version: semver`, `title`,
`inputs: list[finding_code | detection_rule_id]`, `join_keys: list[str]` (for example `src_ci`,
`zone_id`, `subject_id`), `window_seconds`, `min_distinct_zones: int`, `min_inputs: int`,
`severity`, `suppression_window`, `fixtures: list[RuleFixture]`.

**CorrelationEngine** consumes the finding stream and the detection-rule stream, groups by the
declared join keys inside a tumbling window of `window_seconds`, and raises
`sec.correlation_alert_raised` when at least `min_inputs` distinct inputs appear across at least
`min_distinct_zones` zones. This is the lightweight SIEM analog 6a15 names, and it is what IT-004's
suggested next tool points at. Correlation rules are versioned code in the same directory as
detection rules, ship the same positive and negative fixtures, and fail CI under the same three
rules: a missing fixture, a logic change without a version bump, and a rule that stops firing on its
own positive fixture.

Invariant `correlation_is_deterministic_under_reordering`: for a fixed event set, the alerts raised
do not depend on the arrival order of events inside a window, because the engine sorts each window
by the canonical total order `(sim_ts, producer_id, seq)` before evaluating (D-07).

**Grant**: `subject_id`, `subject_kind: enum human|agent|service`, `role_id`, `granted_at`,
`expires_at | None`, `granted_by`. **Permission**: `resource`, `action`. **AccessRole**: `role_id`,
`permissions: list[Permission]` held as a sorted sequence, never a set (D-03).
**AccessDecision**: `granted` or `denied`, matching the two events `sec.access_granted` and
`sec.access_denied` so one word covers the concept everywhere.

Invariant `rbac_deny_by_default`: `RbacEngine.decide(subject, resource, action)` returns `granted`
if and only if some unexpired grant maps the subject to a role holding a permission matching that
resource and action. Wildcards are explicit permission entries, never implicit.

**BackupSchedule**: `ci_id`, `cadence`, `retention`, `target_rpo_minutes`, `target_rto_minutes`.
**BackupRecord**: `backup_id`, `ci_id`, `taken_at`, `size_bytes`, `integrity_hash`, `verified: bool`.
**RestoreDrill**: `drill_id`, `ci_id`, `failure_injected_at`, `detected_at`, `restore_started_at`,
`service_healthy_at`, `backup_used_id`, `measured_rpo_minutes`, `measured_rto_minutes`,
`target_met: bool`, `data_loss_event_count`.

**ChaosScenario**: the schema this section defines because two of its own capabilities need it and
no earlier requirement owns it. `scenario_run_id`, `scenario_id`, `kind: enum ci_failure|
zone_partition|broker_outage|store_and_forward|restore_drill`, `target_ci_ids: list[str]` sorted,
`injected_at`, `planned_duration_minutes`, `actual_ended_at`, `injected_by`,
`downtime_window: (start, end)`, `affected_zone_ids: list[str]` sorted.

Two consumers in this section: a restore drill is a chaos scenario of kind `restore_drill`
(section 5.6), and a business-interruption claim reads `downtime_window` to compute indemnified
hours (section 5.9). The Phase 4 store-and-forward catalog extends the same schema with the
`store_and_forward` kind and adds no field, which is why the schema is settled here rather than
invented twice. Injection is deterministic: the schedule of scenario runs is part of the resolved
config and its hash is in the hashed core (D-01), so a chaos run replays exactly.

### 3.6 `twinflow-commercial`

**Promotion**: `promo_id`, `skus`, `mechanic: enum pct_off|bogo|display|feature|feature_and_display`, <!-- docs-lint-ok STE-TERM-WORD display and feature are retail promotion mechanics, not verbs -->
`depth_pct`, `start`, `end`, `planned_lift_multiplier`, `pull_forward_fraction: float 0..1`,
`pull_forward_decay_periods: int`, `halo_skus: dict[sku, float]`, `funding: Money`,
`channel_scope`.

**LiftCurve**: a saturating response `lift(depth) = 1 + L_max * (1 - exp(-k * depth))` with
`L_max` and `k` per SKU class in config. Deterministic given the parameters; the stochastic layer
adds a multiplicative lognormal noise term drawn from the `commercial.promo_noise` seed namespace.

**PullForwardKernel**: the incremental units in the promo window are split into true incremental
and pulled-forward. The pulled-forward share is removed from the following
`pull_forward_decay_periods` at geometrically decaying weights that sum to exactly 1.0.

**CannibalisationMatrix**: `C[i][j]` is the fraction of SKU `j`'s baseline demand transferred to
SKU `i` while `i` is promoted. Rows and columns are held in SKU-id sorted order, and every summation
over promoted SKUs uses `math.fsum` over that order (D-03), so the conservation check does not
depend on which SKUs happened to be inserted first. Invariants: `C[i][i] == 0`; for every `j`, the
sum over promoted `i` of `C[i][j]` is at most 1.0; every transferred unit is removed from `j` and
added to `i` in the same period, so units are conserved.

The conservation tolerance is 1e-9 relative, which is above the accumulated rounding of an
`fsum` over the shipped catalog and is stated as a tolerance rather than as exactness because the
shares are floats. Transferred **units** are integers and their conservation is exact; the 1e-9
tolerance applies to the share matrix only.

**ChannelMixState**: `period`, `shares: list[(channel, float)]` sorted by channel name,
`concentration_hhi`, `drift_step`, `source: enum config_static|dirichlet_drift`. Channel shares
drift over the run rather than staying at their configured start values, because 6a16 requires the
wholesale versus e-commerce balance to be dynamic rather than a constant the building argues about
once. The shares are published through `ChannelMixPort`, and `ArrivalProcess` in `twinflow-orders`
samples each order's channel from them.

The drift is a Dirichlet random walk on the share simplex, the same family
`docs/design/variability-and-faults.md` section B.4 uses for slotting mix drift, drawn from the
`root/commercial/channel_mix` stream. Invariants: shares are non-negative and sum to 1.0 within
1e-12; with `drift_step` set to zero the shares equal the configured start values exactly, which is
the switch a determinism test uses to separate drift from noise. `concentration_hhi` is the
Herfindahl-Hirschman index of the share vector, which is what makes a channel-concentration finding
countable rather than a matter of opinion.

**PromoFeatureFrame**: the feature the forecaster ingests, which is 6a16's stated requirement rather
than a convenience. One row per `(sku, period)` over the forecast horizon, with columns
`promo_active: bool`, `depth_pct`, `mechanic_one_hot`, `days_into_promo`, `days_since_promo_end`,
`planned_lift_multiplier`, `is_pull_forward_decay_period: bool`, and `halo_source_sku | None`.
Rows are emitted in `(sku, period)` sorted order.

The frame is built from the promo calendar alone, never from realized demand, so a forecaster
consuming it cannot leak the outcome it is predicting. Invariant `promo_feature_frame_is_causal`:
every column for period `t` is computable from the calendar as it stood at the forecast cut-off, and
a fixture that back-dates a calendar entry past the cut-off fails the check. Without this frame the
statistical forecaster sees the promotion only as unexplained demand, which is the naive behavior
section 5.7 uses as the FVA baseline rather than the shipped behavior.

**DemandMultiplier**: `sku`, `period`, `multiplier: float > 0`, `sources: list[(source, factor)]`
sorted by source name, where `source` is one of `promotion`, `quota_pressure`, `channel_mix`, or
`npi_launch`. The multiplier is the product of its factors, computed in sorted source order with
`math.fsum` over the logs so the product does not depend on insertion history (D-03). This is the
value `DemandShapingPort` returns, and it is the whole of the coupling between the commercial brain
and the arrival process.

Invariant `demand_multiplier_decomposes`: the product of the listed factors equals `multiplier` to
1e-12 relative, so a demand spike can always be attributed to the levers that caused it rather than
being an unexplained jump in the arrival rate.

**Opportunity**: `opp_id`, `customer_id`, `rep_id`, `stage`, `amount`, `expected_close`,
`created_at`, `stage_history`, `outcome: enum won|lost|open`.
**StageModel**: per-stage conversion probability and dwell distribution.
**RepBiasModel**: per rep, `bias_multiplier`, `mode: enum optimistic|sandbagging|calibrated`,
`variance`. The submitted rep forecast equals the probability-weighted pipeline times the bias
multiplier plus noise.

**QuotaCalendar**: `period_boundaries`, `pressure_exponent k`, `pressure_amplitude q`,
`discount_escalation_pct`. Order arrival intensity within a quota period is multiplied by
`1 + q * ((t - t_start) / (t_end - t_start)) ** k`, which produces the quarter-end hockey stick.

**NewProduct**: `sku`, `launch_date`, `bass_p`, `bass_q`, `market_potential_m`,
`analog_sku | None`, `cold_start_blend_periods`.

**FvaLadder**: ordered steps, by default `naive -> statistical -> sales_override -> consensus`,
each with its own forecast series. `FvaReport` is the stairstep table: per step, the accuracy
metric, the delta versus the previous step, and the delta versus naive.

**SopCycle**: `cycle_id` (process-mining case id for the S&OP process), `period`,
`steps: list[SopStep]`, `plan: OneNumberPlan | None`, `decisions: list[DecisionPacket]`,
`scored_prior_cycle_id | None`.
**SopStep**: `step: enum product_review|demand_review|supply_review|reconciliation|executive`,
`started_at`, `completed_at`, `inputs_event_ids`, `outputs_event_ids`, `owner_role`.

**RoughCutCapacityCheck**: the supply review's computation, specified here rather than left open.
`mode: enum analytic|surrogate|full_simulation` (config key `sop.supply_review_mode`, default
`analytic`), `resource_set: list[resource_id]`, `capacity_by_period: list[(period, resource_id,
available_hours, required_hours)]`, `gaps: list[(period, resource_id, shortfall_hours,
shortfall_units)]`, `constraint_resources: list[resource_id]` sorted by shortfall descending then by
`resource_id`, `evaluated_at`, `inputs_event_ids`.

The analytic mode is a rough-cut capacity plan. For each period in the horizon and each resource in
`resource_set`, required hours are the consensus volume per family multiplied by the family's
bill-of-resource coefficient, summed over families in sorted family order. Available hours come from
the three capacity ports: the factory finite schedule (6a9), the DC labor requirement
(`hr.labor_requirement_published`), and transport capacity (6a7). A resource whose required hours
exceed available hours in any period is a gap, and the constraining resource for a period is the one
with the largest shortfall. Bill-of-resource coefficients live in
`config/commercial/bill_of_resource.yaml` and carry `provenance: synthetic`.

The surrogate mode calls E28's learned surrogate through `CapacityPort` and is available only when
E28 is installed; the full simulation mode runs the twin over the horizon. Both are configuration,
and neither is required for the S&OP cycle to run, which is what makes an 18-period monthly cycle
affordable inside the sim-time budget. `sop.supply_review_completed` records which mode produced its
numbers, so a reader can never mistake a rough-cut figure for a simulated one. Open question 9 is
narrowed accordingly: what stays open is which mode the shipped demo profile selects, not whether
the computation exists.

**OneNumberPlan**: `plan_id`, `cycle_id`, `horizon_periods`,
`volume_by_period_by_family: dict`, `revenue_by_period`, `supply_commitment_by_period`,
`published_at`. Invariant `one_number_identity`: the volume the finance reforecast uses, the volume
the supply plan commits, and the consensus demand volume are the same numbers for every period in
the horizon.

**DecisionPacket**: `decision_id`, `cycle_id`, `question`, `options: list[Option]`,
`recommendation`, `assumptions: list[Assumption]`, `confidence`, `authority_tier`,
`decided_by`, `decided_at`, `expected_outcome: dict[metric, value]`. Each `Assumption` carries a
`metric`, an `assumed_value`, and a `measurement_query` so next cycle can score it.

### 3.7 `twinflow-finance`

**Account**: `account_id` (four digit synthetic numbering), `name`,
`type: enum asset|liability|equity|revenue|expense`, `normal_balance: enum debit|credit`,
`parent_id | None`, `is_postable: bool`, `is_control_account: bool`, `subledger | None`.

**JournalEntry**: `je_id`, `posting_date`, `period_id`, `source_event_id`, `source_event_type`,
`rule_id`, `lines: list[JournalLine]`, `description`, `reversal_of | None`, `is_accrual: bool`,
`posted_by`. **JournalLine**: `account_id`, `debit: Money`, `credit: Money`, `dimensions: dict`
(cost center, station, sku, customer, supplier, channel, lot, scenario).

Invariants: `journal_balances` (sum of debits equals sum of credits, exactly, in integer minor
units, per entry); `no_negative_amounts` (a line carries a positive debit or a positive credit,
never both, never negative); `period_closed_is_immutable` (no posting to a closed period without an
explicit reopening event).

**Ledger**: append-only. The statements are pure functions of the ledger:
`statements = f(journal_entries, period, chart_of_accounts)`. No statement value comes from any
other source. This is the property that makes the drill-down honest.

**PostingRule**: `rule_id`, `source_event_type`, `version`, `condition` (a predicate over the event
payload), `lines: list[LineTemplate]` where each template names the account (directly or by a
lookup key such as valuation class), the amount expression, and the dimensions to copy from the
event. Rules live in `posting_rules.yaml` and every rule has at least one fixture.

**StandardCost**: `sku`, `revision_id`, `effective_from`,
`material_standards: list[(component_sku, std_qty, std_price)]`,
`labor_standards: list[(operation_id, std_hours, std_rate)]`,
`variable_oh_rate`, `fixed_oh_rate`, `oh_base: enum labor_hours|machine_hours`,
`total_standard_cost`. Roll-up is bottom-up over the BOM and asserts
`total == sum(material) + sum(labor) + variable_oh + fixed_oh`.

**Variance**: `variance_id`, `period_id`, `kind`, `amount: Money`,
`favorable: bool`, `attribution: list[VarianceAttribution]`,
`causal_class: enum common_cause|assignable|insufficient_data`,
`control_chart_evidence: FindingRef | None`.

Variance kinds implemented, each with its published algebraic definition:

| Kind                     | Formula                                                                       |
|--------------------------|-------------------------------------------------------------------------------|
| `material_price` (PPV)   | `(actual_price - standard_price) * actual_qty_purchased`                      |
| `material_quantity`      | `(actual_qty_used - standard_qty_allowed) * standard_price`                   |
| `material_mix`           | `sum_i (actual_mix_i - standard_mix_i) * total_actual_qty * standard_price_i` |
| `material_yield`         | `(total_actual_input - standard_input_for_output) * weighted_standard_price`  |
| `labor_rate`             | `(actual_rate - standard_rate) * actual_hours`                                |
| `labor_efficiency`       | `(actual_hours - standard_hours_allowed) * standard_rate`                     |
| `variable_oh_spending`   | `actual_variable_oh - (actual_hours * standard_variable_rate)`                |
| `variable_oh_efficiency` | `(actual_hours - standard_hours_allowed) * standard_variable_rate`            |
| `fixed_oh_budget`        | `actual_fixed_oh - budgeted_fixed_oh`                                         |
| `fixed_oh_volume`        | `(budgeted_hours - standard_hours_allowed) * standard_fixed_rate`             |
| `freight`                | `actual_freight - standard_freight_per_unit * units`                          |
| `premium_freight`        | expedite spend isolated from the freight variance                             |
| `scrap`                  | `scrapped_units * standard_cost_at_scrap_point`                               |
| `rework`                 | `rework_hours * standard_rate + rework_material_at_standard`                  |
| `duty`                   | `actual_duty - standard_duty` (the E14 hook)                                  |

**VarianceAttribution**: `variance_id`, `source_event_id`, `source_event_type`, `amount: Money`,
`explanation_key`. Invariant `variance_attribution_closure`: the attributed amounts sum exactly to
the variance amount.

**ValuationMethod**: `weighted_average` or `fifo`, config selected, applied per valuation class.
Invariant `inventory_flow_identity`: `beginning + receipts - issues - adjustments = ending`, in both
quantity and value, per SKU per period, exactly.

**EandOReserve**: `sku`, `period`, `on_hand_qty`, `forward_coverage_periods` (from the demand
model), `excess_qty`, `aging_bucket`, `reserve_rate`, `reserve_amount`, `driver_event_ids`.

**CycleCountProgram**: `abc_class -> count_frequency_days`, `count_method: enum cycle|wall_to_wall`,
`counter_role`, `tolerance`. **CountResult**: `location`, `sku`, `book_qty`, `physical_qty`,
`variance_qty`, `variance_value`, `absolute_value_accuracy`, `rfid_confirmed: bool`.

Inventory record accuracy is measured two ways and both are reported: location-level exact-match
accuracy, and absolute-value accuracy `1 - sum(|book - physical| * unit_cost) / sum(book * unit_cost)`.

**AbcModel**: `activity_pools: list[ActivityPool]`, each with `pool_id`, `cost_accounts`,
`driver: CostDriver`, `rate` (recomputed each period as pool cost divided by total driver quantity).
**CostToServe**: `subject: enum order|customer|channel|sku`, `subject_id`, `period`,
`activity_costs: dict[pool_id, Money]`, `freight`, `returns_cost`, `service_cost`, `total`,
`revenue`, `gross_margin`, `contribution_after_cost_to_serve`.

**CapexRequest**: `capex_id`, `origin_whatif_id`, `title`, `investment: Money`,
`cash_flows: list[(period, Money)]`, `discount_rate`, `npv`, `irr`, `simple_payback_periods`,
`discounted_payback_periods`, `authority_tier`, `approvals`, `decision`,
`post_audit: PostInvestmentAudit | None`.
**PostInvestmentAudit**: `capex_id`, `audit_at`, `projected_benefit`, `realised_benefit`
(measured by the twin over the same metric definition), `variance`, `hit: bool`,
`explanation_event_ids`.

**CloseTask**: `task_id`, `period_id`, `name`, `owner_role`, `depends_on: list[task_id]`,
`planned_duration`, `started_at`, `completed_at`, `blocked_minutes`, `rework_count`.
**CloseMetrics**: `period_id`, `close_cycle_days`, `critical_path`, `tasks_late`,
`accrual_count`, `manual_journal_count`, `reconciliation_breaks`.

**ClosingEntryGenerator** and **IncomeSummary**: the roll-up mechanism the period-boundary
invariants need. Without it, revenue and expense balances never move to equity, retained earnings
never changes, and both `trial_balance_closure` and `statement_articulation` fail by construction
rather than by defect.

At every period close the generator emits exactly one closing journal entry, in this order:

1. Every account of type `revenue` with a non-zero balance is debited to zero, credit to
   `Income summary`.
2. Every account of type `expense` with a non-zero balance is credited to zero, debit to
   `Income summary`.
3. The `Income summary` balance is closed to `Retained earnings`, debit or credit as its sign
   requires.

Accounts are visited in `account_id` order so the entry's line order is stable across processes
(D-03). The entry carries `rule_id = "close.period_roll_up"` and a `source_event_id` pointing at
`gl.period_closed`, so it drills down like any other posting. `gl.period_closed` carries
`closing_entry_id` alongside `trial_balance_hash`.

For a `four_four_five` calendar the same mechanism runs on the period boundaries the calendar file
declares. Interim periods inside a fiscal year close to `Retained earnings` directly; there is no
separate year-end entry, and the fiscal-year opening balance test asserts that.

Invariant `closing_entry_zeroes_nominal_accounts`: after the closing entry posts, every revenue and
expense account has a zero balance and the change in `Retained earnings` for the period equals net
income for the period, exactly, in integer minor units.

**AuthorityMatrix**: rows of
`(role_id, process, category, basis, max_amount, currency, max_authority_tier)`.

`basis: enum amount|tier` says which dimension the row authorizes on, because the three processes
that read this matrix do not all carry a money amount. A PO and a capex request carry a value, so
their rows use `basis: amount` and resolve against `max_amount`. A change carries no value, so its
rows use `basis: tier` and resolve against `max_authority_tier`.

Change authority tier is derived, not invented at the point of approval. The mapping is a published
table in the same config artifact:

| `risk_score` band | CI `criticality` 1 to 2 | CI `criticality` 3 to 4 |
|-------------------|-------------------------|-------------------------|
| 0.00 to 0.29      | tier 1                  | tier 2                  |
| 0.30 to 0.69      | tier 2                  | tier 3                  |
| 0.70 to 1.00      | tier 3                  | tier 4                  |

Resolution rule, one per process, stated so three packages cannot each invent their own:
procurement resolves `(role_id, "purchase_order", category)` on amount; finance resolves
`(role_id, "journal", category)` and `(role_id, "capex", category)` on amount; IT operations
resolves `(role_id, "change", category)` on tier using the table above. A row whose `basis` does not
match the resolution rule for its process fails config validation with the row quoted.

Shared config artifact at `/schemas/config/authority_matrix.v1.json`, read by procurement (PO
approval), IT operations (change approval), and finance (journal and capex approval). No package
imports another to use it.

Because three packages read one file, agreement on semantics is proved rather than assumed. The
cross-package conformance test `authority_matrix_interpretation_agrees` loads one fixture matrix,
asks each package's resolver for the minimal approving role over a shared grid of
`(process, category, amount, risk_score, criticality)` cases, and fails when any two packages
disagree on the same case or when a package accepts a case its `basis` does not cover. Open
question 2 covers ownership of the artifact, which is a separate question from this one.

**SodRule**: `rule_id`, `conflicting_permissions: tuple[Permission, Permission]`, `severity`,
`mitigating_control_id | None`. **Control**: `control_id`, `objective`, `process`,
`frequency`, `type: enum preventive|detective`, `automation: enum manual|automated`,
`owner_role`, `test_procedure_query`, `evidence_query`.

**Terms** (E22): `terms_id`, `net_days`, `discount_pct`, `discount_days`,
`applies_to: enum ap|ar`. **EchelonWorkingCapital**: `echelon: enum supplier_stock|in_transit_inbound|
dc_stock|wip|finished_goods|in_transit_outbound|accounts_receivable`, `period`, `value: Money`,
`days`, `carrying_cost`.

Cash-to-cash is `DIO + DSO - DPO`, each computed from the ledger with the definitions published in
the metrics layer so the agent can never compute them a different way.

### 3.8 `twinflow-insurance` (E38)

**Policy**: `policy_id`, `coverage: enum cargo|property|business_interruption|general_liability|
workers_compensation`, `insurer_name` (synthetic), `period_start`, `period_end`,
`limit: Money`, `deductible: Money`, `sublimits: dict[str, Money]`,
`waiting_period_hours` (BI only), `indemnity_period_days` (BI only), `coinsurance_pct`,
`premium: Money`, `exposure_base_value`.

**Claim**: `claim_id` (process-mining case id for the claims process), `policy_id`,
`trigger_event_ids`, `loss_type`, `reported_at`, `documented_at`, `adjusted_at`, `decided_at`,
`paid_at`, `gross_loss: Money`, `deductible_applied`, `payout: Money`,
`status: enum open|documented|under_review|settled|denied`, `denial_reason | None`,
`recovery_ratio` (payout over gross loss).

`Claim` also carries `sublimit_key | None` and `applicable_limit: Money`, so the limit that actually
bound a payout is on the record rather than inferred later.

**SublimitResolver**: maps a loss to at most one sublimit key. The rule set is ordered and declared
in `insurance.sublimit_rules`, each rule a predicate over `(loss_type, trigger_event_type,
peril_tag)`. The first matching rule wins, and a loss matching no rule takes the policy limit. The
shipped `temperature_excursion` sublimit matches losses whose trigger is
`transport.temperature_excursion`, which is the loss class the cold-chain scenario produces. Without
the resolver the shipped sublimit value would sit in config and change nothing, which is worse than
not shipping it.

Invariant `claim_payout_bounds`, restated so the sublimit participates:

```
applicable_limit = policy.sublimits[key] if key is not None else policy.limit
payout           = min(applicable_limit, max(0, gross_loss - deductible) * coinsurance_pct)
```

with `0 <= payout <= applicable_limit <= policy.limit`, and payout monotone non-decreasing in
`gross_loss`. Config validation rejects a sublimit greater than the policy limit, quoting both.

**RetainedLoss**: `loss_id`, `claim_id | None`, `period`, `loss_type`, `gross_loss: Money`,
`recovered: Money`, `retained: Money`, `gl_posting_id`. Every loss the twin generates is recognized
in the ledger when it occurs, whether or not it is ever claimed, and the recovery is posted
separately when a claim settles. Invariant `retained_equals_gross_minus_recovered`, exactly, in
integer minor units.

This record is what lets `tcor_reconciles_to_gl` hold. `retained_losses` is the largest component of
total cost of risk in most periods, and until the gross loss itself had a posting there was nothing
in the ledger for that component to tie to.

**ExperienceModifier**: `policy_id`, `rating_period`, `loss_history_ratio`, `trir` (from 6a10),
`modifier: float`, `inputs_event_ids`. Invariant `experience_modifier_monotone`: the modifier is
non-decreasing in both the loss ratio and TRIR, holding exposure fixed.

**TotalCostOfRisk**: `period`, `premiums`, `retained_losses`, `risk_control_spend`,
`admin_cost`, `total`. Invariant `tcor_reconciles_to_gl`: every TCOR component equals the sum of
its mapped GL accounts for the period, exactly.

## 4. Events

### 4.1 Envelope

Every event in this section uses the common envelope defined by the schema registry (C3). Fields
this section relies on:

| Field              | Type                                                        | Notes                                                                                                                                                                      |
|--------------------|-------------------------------------------------------------|----------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| `event_id`         | str                                                         | `uuid5(namespace=run_namespace, name=f"{producer_id}:{seq}")`, see below                                                                                                   |
| `schema`           | str                                                         | `twinflow.<domain>.<event_name>`                                                                                                                                           |
| `schema_version`   | semver                                                      | Additive-only within a major version                                                                                                                                       |
| `sim_time`         | ISO-8601 sim-clock instant                                  | From the `Clock` port, never wall clock                                                                                                                                    |
| `run_id`           | str                                                         |                                                                                                                                                                            |
| `stream_name`      | str                                                         | The RNG stream that produced any draw behind this event, for example `orders.service.contacts`, or null when the event is deterministic                                    |
| `producer_id`      | str                                                         | The distribution name alone, for example `twinflow-orders`. No version (D-07)                                                                                              |
| `producer_version` | semver                                                      | The producing package's version, carried outside the identity so a release does not renumber history                                                                       |
| `seq`              | int                                                         | Dense per `(run_id, producer_id)`, starting at 1 (D-07)                                                                                                                    |
| `case_id`          | str or null                                                 | Process-mining case key. This section supplies additional case notions: `order_id`, `po_id`, `inc_id`, `contact_id`, `cycle_id`, `claim_id`, and `period_id` for the close |
| `correlation_id`   | str                                                         | Business transaction thread                                                                                                                                                |
| `causation_id`     | str or null                                                 | The `event_id` that caused this one. Mandatory for every derived event in this section                                                                                     |
| `zone_id`          | str                                                         | Producer's IEC 62443 zone, used by conduit monitoring                                                                                                                      |
| `actor`            | object with `kind` (human, agent, service), `id`, `role_id` | The audit trail identity, required on every state-changing event                                                                                                           |

Three envelope rules this section depends on, all from D-07 and D-01.

**The sequence number is per producer, not global.** A single dense counter across every producer
has no allocator once the garage tier runs several containers plus the Rust agent, so `seq` is dense
per `(run_id, producer_id)` and each package allocates its own. The canonical total order over the
log is `(sim_ts, producer_id, seq)`, and both the replay reader and the pagination cursor use it.

**`event_id` does not embed a version.** `producer_id` is the distribution name with no version
suffix, and `run_namespace` is `uuid5(TWINFLOW_ROOT_NAMESPACE, run_id)`, because `uuid5` requires a
UUID namespace and `run_id` is a string. Embedding `package@version` in the name would change every
event id on every release, which would break the byte-identical log check, invalidate every golden
file, and make C6's compatibility table unanswerable. The version travels in `producer_version`,
where a release changes a field rather than an identity.

**The hashed log covers no wall clock and no machine identity.** Per D-01 the run manifest is split:
`run_started` carries the hashed core only (seed, config hash, schema snapshot hash, scenario id,
mode, tick rate, horizon, warmup, fault schedule hash), and `started_wall_utc`, git provenance,
platform, package versions, and host go to the provenance sidecar at `manifest.json`. Every hash
comparison in section 7.6 is over the log, so the log holds nothing that two runs seconds apart must
differ on.

Schema files live at `/schemas/<domain>/<event_name>/v<major>.json` with a companion Pydantic model
generated into `twinflow-schemas`. CI producer and consumer contract tests fail on drift: every
event named in a published table has a schema file and at least one declared consumer or an explicit
`consumers: []` marker, and every event named in a consumed list has a producer in some section.

### 4.2 `twinflow-orders` (domains `orders`, `service`, `customer`)

Published:

| Event                                 | Version | Key payload                                                                                               |
|---------------------------------------|---------|-----------------------------------------------------------------------------------------------------------|
| `orders.order_captured`               | 1.0.0   | `order_id`, `customer_id`, `channel`, `lines[]`, `requested_ship_date`, `value`                           |
| `orders.order_validated`              | 1.0.0   | `order_id`, `validations[]`, `passed`                                                                     |
| `orders.order_rejected`               | 1.0.0   | `order_id`, `reason_code`                                                                                 |
| `orders.credit_check_completed`       | 1.0.0   | `order_id`, `open_ar`, `credit_limit`, `decision`                                                         |
| `orders.hold_placed`                  | 1.0.0   | `order_id`, `hold_id`, `type`, `reason`                                                                   |
| `orders.hold_released`                | 1.0.0   | `hold_id`, `released_by`, `held_hours`                                                                    |
| `orders.promise_quoted`               | 1.0.0   | `order_id`, `promise_date`, `source` (one of the five tiers), `confidence`, `supply_basis[]`              |
| `orders.promise_breached`             | 1.0.0   | `order_id`, `promise_date`, `breached_at`, `elapsed_days`, `open_lines`, `promise_source`                 |
| `orders.allocation_run_completed`     | 1.0.0   | `policy_run_id`, `policy`, `demand_units`, `supply_units`, `filled_units`, `fairness_index`, `by_segment` |
| `orders.line_allocated`               | 1.0.0   | `line_id`, `qty`, `source`, `lot_ids[]`, `policy_run_id`                                                  |
| `orders.line_backordered`             | 1.0.0   | `line_id`, `qty`, `reason`, `promised_recovery_date`                                                      |
| `orders.backorder_filled`             | 1.0.0   | `backorder_id`, `qty`, `aged_days`, `fill_priority`                                                       |
| `orders.substitution_applied`         | 1.0.0   | `line_id`, `from_sku`, `to_sku`, `ratio`, `customer_approved`                                             |
| `orders.change_requested`             | 1.0.0   | `change_id`, `order_id`, `type`, `stage_at_request`                                                       |
| `orders.change_accepted`              | 1.0.0   | `change_id`, `cost`, `rework_minutes`                                                                     |
| `orders.change_rejected`              | 1.0.0   | `change_id`, `reason`                                                                                     |
| `orders.order_cancelled`              | 1.0.0   | `order_id`, `stage_at_cancel`, `cost`, `initiator`                                                        |
| `orders.order_released`               | 1.0.0   | `order_id`, `wave_id`                                                                                     |
| `orders.order_invoiced`               | 1.0.0   | `order_id`, `invoice_id`, `amount`, `terms_id`                                                            |
| `orders.order_closed`                 | 1.0.0   | `order_id`, `cycle_time_hours`                                                                            |
| `orders.perfect_order_evaluated`      | 1.0.0   | `order_id`, four component booleans, `perfect`, `failed_components[]`                                     |
| `service.contact_created`             | 1.0.0   | `contact_id`, `customer_id`, `order_id`, `reason_code`, `channel`, `caused_by_event_id`                   |
| `service.contact_queued`              | 1.0.0   | `contact_id`, `queue_id`, `queue_depth`                                                                   |
| `service.contact_answered`            | 1.0.0   | `contact_id`, `agent_id`, `wait_seconds`                                                                  |
| `service.contact_abandoned`           | 1.0.0   | `contact_id`, `wait_seconds`, `patience_seconds`                                                          |
| `service.contact_resolved`            | 1.0.0   | `contact_id`, `handle_seconds`, `first_contact_resolution`, `visibility_level`, `blocking_data`           |
| `service.contact_escalated`           | 1.0.0   | `contact_id`, `to_level`, `reason`                                                                        |
| `service.external_failure_classified` | 1.0.0   | `contact_id`, `order_id`, `copq_class`, `copq_amount`, `reason_code`, `evidence_event_ids[]`              |
| `customer.satisfaction_updated`       | 1.0.0   | `customer_id`, `before`, `after`, `driver_event_id`                                                       |
| `customer.churned`                    | 1.0.0   | `customer_id`, `hazard_at_churn`, `remaining_clv`, `clv_margin_source`, `failure_event_ids[]`             |
| `customer.tier_changed`               | 1.0.0   | `customer_id`, `from_tier`, `to_tier`, `reason`                                                           |

`service.external_failure_classified` is the outbound half of the loop 6a12 names. Every resolved
complaint whose reason code maps to an external quality failure is classified into the
cost-of-poor-quality taxonomy (`copq_class` is one of `external_failure` or `appraisal`) with the
cost the complaint consumed attached, and 6a11 consumes it as external-failure COPQ. Without this
event the section consumed `qms.ncr_raised` and published nothing back, so the loop the source calls
out ran one way only.

`customer.churned` carries `clv_margin_source`, one of `abc_cost_to_serve` or `baseline_fallback`,
so a churn number computed before activity-based costing lands can never be read as a modeled
contribution (section 5.2).

Consumed: `inventory.availability_snapshot`, `outbound.shipment_confirmed`, `outbound.pick_short`,
`outbound.pack_completed`, `returns.return_received`, `returns.disposition_completed`,
`transport.delivery_confirmed`, `transport.delivery_exception`, `planning.atp_response`,
`planning.ctp_response`, `ar.dispute_opened` and `ar.invoice_corrected` (together, the
invoice-accuracy leg of the perfect order), `hr.shift_assigned` (service agent staffing),
`qms.ncr_raised`, `mkt.demand_multiplier_published` (the arrival intensity multiplier),
`mkt.channel_mix_published` (the channel shares each order's channel is drawn from).

The invoice-accuracy leg reads customer-invoice events, not
`procurement.three_way_match_evaluated`. The three-way match compares a supplier's invoice against a
PO the customer never sees, so it cannot witness whether the customer was correctly invoiced.
Section 5.1 defines the component as no accounts-receivable dispute and no pricing correction, and
those are the two events now consumed.

### 4.3 `twinflow-procurement` (domains `procurement`, `sourcing`, `contract`, `spend`)

Published:

| Event                                   | Version | Key payload                                                                                                                                                                                 |
|-----------------------------------------|---------|---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| `procurement.requisition_created`       | 1.0.0   | `req_id`, `source`, `sku`, `qty`, `need_by`, `triggering_event_id`                                                                                                                          |
| `procurement.po_created`                | 1.0.0   | `po_id`, `supplier_id`, `lines[]`, `contract_id`, `incoterm`, `value`                                                                                                                       |
| `procurement.po_approval_requested`     | 1.0.0   | `po_id`, `step_index`, `required_role`, `threshold`                                                                                                                                         |
| `procurement.po_approved`               | 1.0.0   | `po_id`, `approver_id`, `authority_limit`, `elapsed_hours`                                                                                                                                  |
| `procurement.po_rejected`               | 1.0.0   | `po_id`, `approver_id`, `reason`                                                                                                                                                            |
| `procurement.po_sent`                   | 1.0.0   | `po_id`, `channel`                                                                                                                                                                          |
| `procurement.po_acknowledged`           | 1.0.0   | `po_id`, `confirmed_dates`, `date_slip_days`                                                                                                                                                |
| `procurement.po_line_changed`           | 1.0.0   | `po_line_id`, `field`, `from`, `to`, `initiator`                                                                                                                                            |
| `procurement.expedite_requested`        | 1.0.0   | `po_id`, `premium_freight_quote`, `stockout_cost_avoided`, `decision`                                                                                                                       |
| `procurement.expedite_completed`        | 1.0.0   | `po_id`, `days_pulled_in`, `actual_premium`                                                                                                                                                 |
| `procurement.goods_receipt_matched`     | 1.0.0   | `po_id`, `receipt_id`, `qty`, `over_receipt_pct`                                                                                                                                            |
| `procurement.invoice_received`          | 1.0.0   | `invoice_id`, `po_id`, `total`, `duplicate_of`                                                                                                                                              |
| `procurement.three_way_match_evaluated` | 1.0.0   | `match_id`, `result`, `variance_amount`, `tolerance_applied`                                                                                                                                |
| `procurement.match_exception_opened`    | 1.0.0   | `match_id`, `exception_type`, `assigned_to`                                                                                                                                                 |
| `procurement.match_exception_resolved`  | 1.0.0   | `match_id`, `resolution`, `open_hours`                                                                                                                                                      |
| `procurement.payment_scheduled`         | 1.0.0   | `payment_id`, `invoice_ids[]`, `scheduled_for`, `discount_available`                                                                                                                        |
| `procurement.payment_executed`          | 1.0.0   | `payment_id`, `amount`, `discount_taken`, `days_from_invoice`                                                                                                                               |
| `sourcing.rfx_issued`                   | 1.0.0   | `rfx_id`, `category_id`, `invited_suppliers[]`, `criteria[]`                                                                                                                                |
| `sourcing.bid_submitted`                | 1.0.0   | `bid_id`, `rfx_id`, `supplier_id`, `price_curve[]`, `lead_time_days`                                                                                                                        |
| `sourcing.bids_scored`                  | 1.0.0   | `rfx_id`, `scores`, `normalization`, `ranking[]`                                                                                                                                            |
| `sourcing.award_decided`                | 1.0.0   | `rfx_id`, `awards[]`, `constraint_costs`, `decision_id`                                                                                                                                     |
| `contract.created`                      | 1.0.0   | `contract_id`, `supplier_id`, `tier_schedule[]`, `commitment`, `end`                                                                                                                        |
| `contract.tier_achieved`                | 1.0.0   | `contract_id`, `cumulative_volume`, `new_unit_price`                                                                                                                                        |
| `contract.rebate_accrued`               | 1.0.0   | `contract_id`, `period`, `basis`, `amount`                                                                                                                                                  |
| `contract.expiring`                     | 1.0.0   | `contract_id`, `days_to_expiry`, `annual_spend_at_risk`                                                                                                                                     |
| `contract.renegotiated`                 | 1.0.0   | `contract_id`, `from_terms`, `to_terms`, `savings_entry_id`                                                                                                                                 |
| `spend.transaction_classified`          | 1.0.0   | `spend_id`, `category_path[]`, `contract_id`, `confidence`                                                                                                                                  |
| `spend.maverick_detected`               | 1.0.0   | `spend_id`, `covering_contract_id`, `leakage`, `price_delta_pct`                                                                                                                            |
| `procurement.savings_recorded`          | 1.0.0   | `entry_id`, `kind`, `baseline_method`, `amount`, `evidence_event_ids[]`                                                                                                                     |
| `procurement.forward_buy_decided`       | 1.0.0   | `sku`, `qty`, `carrying_cost`, `duty_avoided`, `scenario_id`, `decision`, `breakeven_days`                                                                                                  |
| `procurement.spot_buy_evaluated`        | 1.0.0   | `decision_id`, `triggering_event_id`, `sku`, `qty_short`, `contract_unit_price`, `spot_unit_price`, `stockout_cost_avoided`, `price_premium`, `contract_penalty`, `net_benefit`, `decision` |
| `procurement.eoq_validated`             | 1.0.0   | `sku`, `analytic_eoq`, `simulated_argmin_qty`, `grid_points[]`, `total_cost_at_analytic`, `total_cost_at_argmin`, `agreement`                                                               |

Consumed: `planning.reorder_point_signal`, `supplier.asn_issued`, `supplier.otif_observed`,
`supplier.quality_event`, `supplier.commit_date_slipped` (the trigger that opens a spot-buy
question), `receiving.goods_receipt`, `trade.landed_cost_computed`, `trade.scenario_activated`,
`transport.premium_freight_quote`, `orders.line_backordered` (stockout cost in the expedite and
spot-buy decisions), `gl.journal_posted` (savings reconciliation).

### 4.4 `twinflow-trade` (domain `trade`, E14)

| Event                           | Version | Key payload                                                                             |
|---------------------------------|---------|-----------------------------------------------------------------------------------------|
| `trade.classification_assigned` | 1.0.0   | `sku_id`, `hs_code`, `country_of_origin`, `origin_rule`                                 |
| `trade.tariff_schedule_loaded`  | 1.0.0   | `schedule_id`, `content_hash`, `row_count`, `effective_from`                            |
| `trade.scenario_activated`      | 1.0.0   | `scenario_id`, `name`, `deltas[]`, `de_minimis_threshold`                               |
| `trade.scenario_deactivated`    | 1.0.0   | `scenario_id`, `restored_schedule_hash`                                                 |
| `trade.landed_cost_computed`    | 1.0.0   | `sku_id`, `supplier_id`, `qty`, component breakdown, `unit_landed_cost`, `scenario_id`  |
| `trade.duty_accrued`            | 1.0.0   | `receipt_id`, `hs_code`, `origin`, `basis_value`, `rate_kind`, `duty`                   |
| `trade.duty_paid`               | 1.0.0   | `payment_id`, `duty`, `entry_reference`                                                 |
| `trade.ftz_admission`           | 1.0.0   | `zone_id`, `lot_ids[]`, `deferred_duty`                                                 |
| `trade.ftz_withdrawal`          | 1.0.0   | `zone_id`, `lot_ids[]`, `destination` (domestic or export), `duty_due`                  |
| `trade.drawback_claimed`        | 1.0.0   | `claim_id`, `export_event_ids[]`, `import_duty_paid`, `refund_rate`, `refund_requested` |
| `trade.drawback_received`       | 1.0.0   | `claim_id`, `refund_received`, `days_to_refund`                                         |
| `trade.de_minimis_rule_changed` | 1.0.0   | `from_threshold`, `to_threshold`, `affected_channels[]`                                 |

Consumed: `receiving.goods_receipt`, `outbound.shipment_confirmed` (export leg for drawback),
`procurement.po_created` (classification requirement), `transport.leg_costed`.

### 4.5 `twinflow-workforce` (domain `hr`)

| Event                             | Version | Key payload                                                                                                                                                   |
|-----------------------------------|---------|---------------------------------------------------------------------------------------------------------------------------------------------------------------|
| `hr.requisition_opened`           | 1.0.0   | `hr_req_id`, `role_id`, `target_start`, `driver_metric`, `driver_value`                                                                                       |
| `hr.candidate_stage_changed`      | 1.0.0   | `hr_req_id`, `candidate_id`, `from_stage`, `to_stage`, `days_in_stage`                                                                                        |
| `hr.offer_accepted`               | 1.0.0   | `hr_req_id`, `candidate_id`, `start_date`, `time_to_fill_days`                                                                                                |
| `hr.hire_started`                 | 1.0.0   | `worker_id`, `role_id`, `wage_rate`, `cohort_id`                                                                                                              |
| `hr.onboarding_progressed`        | 1.0.0   | `worker_id`, `cumulative_units`, `productivity_multiplier`, `error_rate_multiplier`                                                                           |
| `hr.time_to_productivity_reached` | 1.0.0   | `worker_id`, `days`, `threshold_multiplier`                                                                                                                   |
| `hr.certification_granted`        | 1.0.0   | `worker_id`, `cert_id`, `training_hours`, `cost`, `expires_at`                                                                                                |
| `hr.certification_expired`        | 1.0.0   | `worker_id`, `cert_id`, `stations_lost[]`                                                                                                                     |
| `hr.cross_training_completed`     | 1.0.0   | `worker_id`, `station_id`, `investment`, `coverage_before`, `coverage_after`                                                                                  |
| `hr.station_eligibility_changed`  | 1.0.0   | `worker_id`, `station_id`, `eligible`, `blocking_reason`                                                                                                      |
| `hr.shift_assigned`               | 1.0.0   | `worker_id`, `shift_id`, `station_id`, `roster_id`, `source` (roster_solver or fallback)                                                                      |
| `hr.absence_forecast_published`   | 1.0.0   | `date`, `by_worker`, `model_id`, `expected_absent_fte`                                                                                                        |
| `hr.absence_recorded`             | 1.0.0   | `worker_id`, `date`, `type` (sick, no_show, planned), `predicted_probability`                                                                                 |
| `hr.overtime_recorded`            | 1.0.0   | `worker_id`, `hours`, `hour_type`, `rolling_4w_total`                                                                                                         |
| `hr.attrition_risk_scored`        | 1.0.0   | `worker_id`, `hazard`, `driver_contributions`                                                                                                                 |
| `hr.termination`                  | 1.0.0   | `worker_id`, `reason`, `regretted`, `tenure_days`, `replacement_cost`                                                                                         |
| `hr.labor_cost_posted`            | 1.0.0   | `period`, `by_station`, `by_hour_type`, `direct`, `indirect`, `total`                                                                                         |
| `hr.labor_requirement_published`  | 1.0.0   | `date`, `half_hourly[]`, `by_station`, `source_forecast_id`                                                                                                   |
| `hr.engagement_snapshot`          | 1.0.0   | `worker_id`, `period`, `schedule_stability_index`, `weekend_shift_rate_8w`, `strain_trend_slope`, `overtime_pct_4w`, `sample_count`, `shift_id`, `station_id` |

Consumed: `planning.forecast_published`, `ergonomics.strain_updated`, `ergonomics.trir_updated`,
`twin.station_activity_recorded`, `roster.roster_published` (E23), `qms.error_attributed`.

### 4.6 `twinflow-itops` (domains `itops`, `sec`, `chaos`)

| Event                           | Version | Key payload                                                                                                                                                                      |
|---------------------------------|---------|----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| `itops.ci_registered`           | 1.0.0   | `ci_id`, `type`, `version`, `zone_id`, `purdue_level`, `depends_on[]`                                                                                                            |
| `itops.ci_version_changed`      | 1.0.0   | `ci_id`, `from_version`, `to_version`, `chg_id`                                                                                                                                  |
| `itops.health_sample`           | 1.0.0   | `ci_id`, `signal`, `value`, `window`                                                                                                                                             |
| `itops.slo_budget_updated`      | 1.0.0   | `slo_id`, `consumed_pct`, `remaining`, `burn_rate_1h`, `burn_rate_6h`                                                                                                            |
| `itops.slo_budget_exhausted`    | 1.0.0   | `slo_id`, `at`, `gating_policy_applied`                                                                                                                                          |
| `itops.incident_opened`         | 1.0.0   | `inc_id`, `ci_id`, `severity`, `detection_source`, `impact`                                                                                                                      |
| `itops.incident_acknowledged`   | 1.0.0   | `inc_id`, `mtta_minutes`, `responder_role`                                                                                                                                       |
| `itops.incident_mitigated`      | 1.0.0   | `inc_id`, `mitigation`, `minutes_from_detect`                                                                                                                                    |
| `itops.incident_resolved`       | 1.0.0   | `inc_id`, `mttr_minutes`, `caused_by_change_id`                                                                                                                                  |
| `itops.problem_opened`          | 1.0.0   | `problem_id`, `linked_incidents[]`                                                                                                                                               |
| `itops.known_error_published`   | 1.0.0   | `problem_id`, `root_cause`, `workaround`, `runbook_ref`                                                                                                                          |
| `itops.change_requested`        | 1.0.0   | `chg_id`, `ci_id`, `type`, `requested_window`, `risk_score`, `has_rollback_plan`                                                                                                 |
| `itops.change_approved`         | 1.0.0   | `chg_id`, `approver_id`, `authority_tier`, `conditions[]`                                                                                                                        |
| `itops.change_rejected`         | 1.0.0   | `chg_id`, `reason`                                                                                                                                                               |
| `itops.change_implemented`      | 1.0.0   | `chg_id`, `duration_minutes`, `window_actual`                                                                                                                                    |
| `itops.change_failed`           | 1.0.0   | `chg_id`, `failure_mode`, `caused_incident_id`                                                                                                                                   |
| `itops.change_rolled_back`      | 1.0.0   | `chg_id`, `rollback_minutes`, `restored_version`                                                                                                                                 |
| `itops.freeze_window_violation` | 1.0.0   | `chg_id`, `window`, `override_role`                                                                                                                                              |
| `itops.dora_snapshot`           | 1.0.0   | `period`, `deployment_frequency`, `lead_time_hours`, `change_failure_rate`, `failed_deployment_recovery_hours`                                                                   |
| `itops.trace_sampled`           | 1.0.0   | `trace_id`, `root_span_id`, `span_count`, `critical_path_span_ids[]`, `total_duration_ms`, `error_span_count`, `case_id`, `sampled_by`, `chg_id`                                 |
| `itops.log_volume_snapshot`     | 1.0.0   | `ci_id`, `window`, `by_template[]` (template id, severity, count), `error_rate_per_1k_requests`                                                                                  |
| `chaos.scenario_started`        | 1.0.0   | `scenario_run_id`, `scenario_id`, `kind`, `target_ci_ids[]`, `injected_at`, `planned_duration_minutes`, `affected_zone_ids[]`                                                    |
| `chaos.scenario_ended`          | 1.0.0   | `scenario_run_id`, `actual_ended_at`, `downtime_window`, `recovered: bool`                                                                                                       |
| `sec.vulnerability_published`   | 1.0.0   | `vuln_id`, `affected_component`, `version_range`, `cvss_v31_vector`, `base_score`, `exploit_probability`, `known_exploited`                                                      |
| `sec.vulnerability_assigned`    | 1.0.0   | `vuln_id`, `ci_id[]`, `zone_id[]`, `exposure_days`                                                                                                                               |
| `sec.patch_window_evaluated`    | 1.0.0   | `vuln_id`, `candidate_windows[]`, `modelled_breach_exposure`, `recommended_window`                                                                                               |
| `sec.patch_applied`             | 1.0.0   | `vuln_id`, `ci_id`, `chg_id`, `patch_latency_hours`                                                                                                                              |
| `sec.patch_deferred`            | 1.0.0   | `vuln_id`, `until`, `accepted_risk_amount`, `compensating_control_id`, `decided_by`                                                                                              |
| `sec.zone_crossing_observed`    | 1.0.0   | `src_zone`, `dst_zone`, `src_ci`, `dst_ci`, `protocol`, `bytes`, `conduit_id`                                                                                                    |
| `sec.conduit_violation`         | 1.0.0   | `src_zone`, `dst_zone`, `protocol`, `reason` (no_conduit, protocol_not_allowed, baseline_deviation), `evidence_event_ids[]`                                                      |
| `sec.detection_rule_fired`      | 1.0.0   | `rule_id`, `rule_version`, `severity`, `attack_ics_technique_ids[]`, `evidence_event_ids[]`                                                                                      |
| `sec.correlation_alert_raised`  | 1.0.0   | `corr_rule_id`, `corr_rule_version`, `severity`, `window_start`, `window_end`, `join_key_values`, `distinct_zone_ids[]`, `contributing_finding_ids[]`, `contributing_rule_ids[]` |
| `sec.access_granted`            | 1.0.0   | `subject_id`, `resource`, `action`, `role_id`, `tool_name`                                                                                                                       |
| `sec.access_denied`             | 1.0.0   | `subject_id`, `resource`, `action`, `reason`                                                                                                                                     |
| `sec.backup_completed`          | 1.0.0   | `backup_id`, `ci_id`, `size_bytes`, `integrity_hash`, `verified`                                                                                                                 |
| `sec.restore_drill_completed`   | 1.0.0   | `drill_id`, `ci_id`, `measured_rpo_minutes`, `measured_rto_minutes`, `target_met`, `data_loss_event_count`                                                                       |

Consumed: every subsystem's health sample stream, `network.message_observed` (the tap),
`twin.whatif_result` (production cost of a patch window), `fin.gross_profit_rate` (breach exposure
valuation), `hr.shift_assigned` (on-call roster).

One domain prefix, one event. Breach exposure and business-interruption loss are valued from the
same `fin.gross_profit_rate`, published by `twinflow-finance` in section 4.8 and reached through the
kernel-owned `GrossProfitRatePort` (D-09). Two spellings of one event name would have broken the
producer and consumer contract test on the first CI run.

### 4.7 `twinflow-commercial` (domains `mkt`, `sales`, `npi`, `sop`)

| Event                             | Version | Key payload                                                                                                                                                                                                        |
|-----------------------------------|---------|--------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| `mkt.promotion_planned`           | 1.0.0   | `promo_id`, `skus[]`, `mechanic`, `depth_pct`, `window`, `planned_lift`, `funding`                                                                                                                                 |
| `mkt.promotion_started`           | 1.0.0   | `promo_id`, `baseline_units_forecast`                                                                                                                                                                              |
| `mkt.promotion_ended`             | 1.0.0   | `promo_id`, `realised_units`                                                                                                                                                                                       |
| `mkt.lift_realised`               | 1.0.0   | `promo_id`, `period`, `baseline`, `incremental_true`, `pulled_forward`, `cannibalised`, `halo`, `ground_truth_params`                                                                                              |
| `mkt.campaign_spend_posted`       | 1.0.0   | `promo_id`, `amount`, `channel`                                                                                                                                                                                    |
| `mkt.promo_features_published`    | 1.0.0   | `frame_id`, `cut_off`, `horizon_periods`, `rows[]` (sku, period, promo_active, depth_pct, mechanic, days_into_promo, days_since_promo_end, planned_lift_multiplier, is_pull_forward_decay_period, halo_source_sku) |
| `mkt.demand_multiplier_published` | 1.0.0   | `period`, `by_sku[]` (sku, multiplier, sources[]), `horizon_periods`                                                                                                                                               |
| `mkt.channel_mix_published`       | 1.0.0   | `period`, `shares[]`, `concentration_hhi`, `drift_step`, `source`                                                                                                                                                  |
| `sales.opportunity_created`       | 1.0.0   | `opp_id`, `customer_id`, `rep_id`, `amount`, `expected_close`                                                                                                                                                      |
| `sales.opportunity_stage_changed` | 1.0.0   | `opp_id`, `from_stage`, `to_stage`, `days_in_stage`                                                                                                                                                                |
| `sales.opportunity_closed`        | 1.0.0   | `opp_id`, `outcome`, `amount`, `days_open`                                                                                                                                                                         |
| `sales.rep_forecast_submitted`    | 1.0.0   | `rep_id`, `period`, `submitted_amount`, `pipeline_weighted_amount`, `bias_multiplier_truth`                                                                                                                        |
| `sales.quota_period_closed`       | 1.0.0   | `period`, `by_rep`, `last_week_share`, `discount_escalation_realised`                                                                                                                                              |
| `npi.product_launched`            | 1.0.0   | `sku`, `bass_p`, `bass_q`, `market_potential`, `analog_sku`                                                                                                                                                        |
| `npi.adoption_observed`           | 1.0.0   | `sku`, `period`, `cumulative_adopters`, `analytic_expectation`                                                                                                                                                     |
| `sop.product_review_completed`    | 1.0.0   | `cycle_id`, `npi_decisions[]`, `rationalisation_decisions[]`                                                                                                                                                       |
| `sop.demand_review_completed`     | 1.0.0   | `cycle_id`, `consensus_by_period`, `fva_report`, `inputs[]`                                                                                                                                                        |
| `sop.supply_review_completed`     | 1.0.0   | `cycle_id`, `mode`, `capacity_by_period`, `gaps[]`, `constraint_resources[]`, `inputs_event_ids[]`                                                                                                                 |
| `sop.reconciliation_completed`    | 1.0.0   | `cycle_id`, `priced_gaps[]`                                                                                                                                                                                        |
| `sop.executive_decision_logged`   | 1.0.0   | `cycle_id`, `decision_id`, `question`, `options[]`, `recommendation`, `assumptions[]`, `confidence`, `authority_tier`                                                                                              |
| `sop.plan_published`              | 1.0.0   | `plan_id`, `cycle_id`, `horizon`, `volume_by_period_by_family`, `revenue_by_period`                                                                                                                                |
| `sop.decision_scored`             | 1.0.0   | `decision_id`, `scored_at`, `assumption_errors[]`, `outcome_vs_expected`, `verdict`                                                                                                                                |
| `sop.maturity_snapshot`           | 1.0.0   | `cycle_id`, `plan_adherence`, `decision_latency_days`, `one_number_variance`, `fva_by_source`                                                                                                                      |

Consumed: `planning.forecast_published`, `planning.backtest_scored`,
`factory.finite_schedule_published`, `transport.capacity_published`,
`hr.labor_requirement_published`, `fpa.reforecast_published`, `orders.order_captured`
(actual demand realization), `governance.decision_logged` (the register).

`sop.executive_decision_logged` is mirrored into `governance.decision_logged.v1` using the
register's own schema so E21 can audit it later without a schema translation.

The three outbound events are what make 6a16 a demand-shaping component rather than a reporting
layer. `mkt.promo_features_published` is consumed by the planning package (6a1), whose forecaster
ingests the frame as a feature. `mkt.demand_multiplier_published` and `mkt.channel_mix_published`
are consumed by `twinflow-orders`, whose `ArrivalProcess` multiplies its baseline intensity by the
first and samples each order's channel from the second. Demand stops being purely exogenous at
exactly these three seams, and each one has a schema, a consumer, and a contract test.

### 4.8 `twinflow-finance` (domains `gl`, `ap`, `ar`, `inv`, `cost`, `fpa`, `capex`, `close`, `ctrl`, `fin`)

| Event                          | Version | Key payload                                                                                                                                   |
|--------------------------------|---------|-----------------------------------------------------------------------------------------------------------------------------------------------|
| `gl.journal_posted`            | 1.0.0   | `je_id`, `period_id`, `source_event_id`, `rule_id`, `lines[]`                                                                                 |
| `gl.journal_reversed`          | 1.0.0   | `je_id`, `reversal_of`, `reason`                                                                                                              |
| `gl.period_opened`             | 1.0.0   | `period_id`, `opened_at`                                                                                                                      |
| `gl.period_closed`             | 1.0.0   | `period_id`, `closed_at`, `trial_balance_hash`, `closing_entry_id`, `net_income`, `retained_earnings_delta`                                   |
| `ap.invoice_recorded`          | 1.0.0   | `invoice_id`, `supplier_id`, `amount`, `terms_id`, `due_date`                                                                                 |
| `ap.payment_made`              | 1.0.0   | `payment_id`, `amount`, `discount_taken`, `dpo_contribution_days`                                                                             |
| `ar.invoice_issued`            | 1.0.0   | `invoice_id`, `customer_id`, `amount`, `terms_id`, `due_date`                                                                                 |
| `ar.cash_received`             | 1.0.0   | `invoice_id`, `amount`, `days_outstanding`, `discount_taken`                                                                                  |
| `ar.dispute_opened`            | 1.0.0   | `invoice_id`, `reason`, `amount_in_dispute`, `caused_by_event_id`                                                                             |
| `ar.invoice_corrected`         | 1.0.0   | `invoice_id`, `order_id`, `correction_kind` (price, quantity, tax, terms), `from_amount`, `to_amount`, `credit_memo_id`, `caused_by_event_id` |
| `inv.valuation_updated`        | 1.0.0   | `sku`, `method`, `qty`, `unit_value`, `total_value`                                                                                           |
| `inv.reserve_updated`          | 1.0.0   | `sku`, `aging_bucket`, `excess_qty`, `reserve_rate`, `reserve_amount`                                                                         |
| `inv.count_completed`          | 1.0.0   | `location`, `sku`, `book_qty`, `physical_qty`, `variance_value`, `rfid_confirmed`                                                             |
| `inv.adjustment_posted`        | 1.0.0   | `sku`, `qty_delta`, `value_delta`, `reason`, `je_id`                                                                                          |
| `inv.accuracy_snapshot`        | 1.0.0   | `period`, `location_accuracy`, `absolute_value_accuracy`, `shrink_value`, `rfid_coverage_pct`                                                 |
| `cost.standard_published`      | 1.0.0   | `sku`, `revision_id`, `material`, `labor`, `variable_oh`, `fixed_oh`, `total`                                                                 |
| `cost.variance_computed`       | 1.0.0   | `variance_id`, `kind`, `amount`, `favorable`, `attribution[]`, `causal_class`, `control_chart_evidence`                                       |
| `cost.abc_rate_updated`        | 1.0.0   | `pool_id`, `driver`, `pool_cost`, `driver_qty`, `rate`                                                                                        |
| `cost.cost_to_serve_computed`  | 1.0.0   | `subject`, `subject_id`, `period`, `activity_costs`, `total`, `contribution`                                                                  |
| `fpa.budget_published`         | 1.0.0   | `budget_id`, `period_range`, `drivers`, `by_account`, `source_plan_id`                                                                        |
| `fpa.reforecast_published`     | 1.0.0   | `reforecast_id`, `horizon`, `by_account`, `source_plan_id`                                                                                    |
| `fpa.bridge_computed`          | 1.0.0   | `from_label`, `to_label`, `components[]`, `residual`                                                                                          |
| `capex.request_created`        | 1.0.0   | `capex_id`, `origin_whatif_id`, `investment`, `cash_flows[]`                                                                                  |
| `capex.appraised`              | 1.0.0   | `capex_id`, `npv`, `irr`, `simple_payback`, `discounted_payback`, `discount_rate`                                                             |
| `capex.approved`               | 1.0.0   | `capex_id`, `approver_id`, `authority_tier`                                                                                                   |
| `capex.rejected`               | 1.0.0   | `capex_id`, `reason`                                                                                                                          |
| `capex.post_audit_completed`   | 1.0.0   | `capex_id`, `projected_benefit`, `realised_benefit`, `variance`, `hit`                                                                        |
| `close.task_started`           | 1.0.0   | `period_id`, `task_id`, `owner_role`                                                                                                          |
| `close.task_completed`         | 1.0.0   | `period_id`, `task_id`, `duration_minutes`, `rework_count`                                                                                    |
| `close.reconciliation_break`   | 1.0.0   | `period_id`, `control_account`, `subledger`, `difference`                                                                                     |
| `close.period_certified`       | 1.0.0   | `period_id`, `close_cycle_days`, `critical_path[]`, `manual_journal_count`                                                                    |
| `ctrl.sod_conflict_detected`   | 1.0.0   | `subject_id`, `rule_id`, `conflicting_permissions[]`, `mitigating_control_id`                                                                 |
| `ctrl.control_test_executed`   | 1.0.0   | `control_id`, `period`, `result`, `sample_size`, `exceptions`, `evidence_query_hash`                                                          |
| `fin.working_capital_snapshot` | 1.0.0   | `period`, `by_echelon`, `dio`, `dso`, `dpo`, `cash_to_cash_days`                                                                              |
| `fin.cash_forecast_published`  | 1.0.0   | `as_of`, `horizon_weeks`, `inflows[]`, `outflows[]`, `closing_balance[]`                                                                      |
| `fin.statements_generated`     | 1.0.0   | `period_id`, `pnl_hash`, `balance_sheet_hash`, `cash_flow_hash`, `artifact_keys[]`                                                            |
| `fin.gross_profit_rate`        | 1.0.0   | `period`, `basis` (rolling_12m or period), `revenue`, `cost_of_goods_sold`, `gross_profit`, `rate_per_hour`, `rate_pct`, `source_je_ids[]`    |

`fin.gross_profit_rate` is the one published gross profit rate in the repository, and it exists
because two other packages were valuing losses from a number nobody produced. `twinflow-insurance`
reads it to value a business-interruption loss and `twinflow-itops` reads it to value breach
exposure, both through the kernel-owned `GrossProfitRatePort` (D-09). `rate_per_hour` is gross
profit divided by operating hours in the period, which is the unit a downtime claim needs;
`rate_pct` is gross profit over revenue. Both are computed from the ledger alone, so a claim payout
and the P&L can never disagree about what an hour of downtime was worth.

`fin.statements_generated` carries storage keys, not filesystem paths. The rendered statement
artifacts are written through `Storage` like every other artifact in this section.

Consumed: every operational event with a financial consequence. The authoritative list is the key
set of `posting_rules.yaml`, which includes `receiving.goods_receipt`, `production.completion`,
`production.material_issue`, `production.scrap_recorded`, `outbound.shipment_confirmed`,
`returns.disposition_completed`, `transport.freight_invoice`, `hr.labor_cost_posted`,
`trade.duty_accrued`, `risk.loss_recognised`, `risk.claim_settled`, `risk.premium_rated`,
`mkt.campaign_spend_posted`, `procurement.three_way_match_evaluated`, and
`procurement.payment_executed`.

### 4.9 `twinflow-insurance` (domain `risk`, E38)

| Event                     | Version | Key payload                                                                                                                          |
|---------------------------|---------|--------------------------------------------------------------------------------------------------------------------------------------|
| `risk.policy_bound`       | 1.0.0   | `policy_id`, `coverage`, `limit`, `deductible`, `premium`, `period`                                                                  |
| `risk.policy_renewed`     | 1.0.0   | `policy_id`, `prior_premium`, `new_premium`, `experience_modifier`                                                                   |
| `risk.loss_recognised`    | 1.0.0   | `loss_id`, `period`, `loss_type`, `gross_loss`, `trigger_event_ids[]`, `claim_id` (null when never claimed), `peril_tag`             |
| `risk.recovery_posted`    | 1.0.0   | `loss_id`, `claim_id`, `recovered`, `retained`, `gl_posting_id`                                                                      |
| `risk.claim_filed`        | 1.0.0   | `claim_id`, `policy_id`, `trigger_event_ids[]`, `loss_type`, `gross_loss`, `sublimit_key`, `applicable_limit`                        |
| `risk.claim_documented`   | 1.0.0   | `claim_id`, `documents[]`, `days_from_fnol`                                                                                          |
| `risk.claim_adjusted`     | 1.0.0   | `claim_id`, `adjuster_finding`, `recommended_payout`                                                                                 |
| `risk.claim_settled`      | 1.0.0   | `claim_id`, `payout`, `deductible_applied`, `sublimit_key`, `applicable_limit`, `binding_constraint`, `recovery_ratio`, `cycle_days` |
| `risk.claim_denied`       | 1.0.0   | `claim_id`, `denial_reason`                                                                                                          |
| `risk.bi_claim_triggered` | 1.0.0   | `claim_id`, `disruption_event_id`, `downtime_hours`, `waiting_period_hours`, `indemnified_hours`, `lost_gross_profit`                |
| `risk.premium_rated`      | 1.0.0   | `policy_id`, `exposure_base_value`, `base_rate`, `experience_modifier`, `loss_ratio`, `trir`, `premium`                              |
| `risk.tcor_snapshot`      | 1.0.0   | `period`, `premiums`, `retained_losses`, `risk_control_spend`, `admin_cost`, `total`                                                 |

Consumed: `transport.shock_excursion`, `transport.temperature_excursion`,
`returns.disposition_completed` (damage confirmation), `ergonomics.trir_updated`,
`itops.incident_resolved` (business interruption trigger), `fin.gross_profit_rate`,
`chaos.scenario_started` and `chaos.scenario_ended` (downtime windows, schema in section 3.5).

`risk.loss_recognised` fires when the twin generates a loss, not when a claim is filed, and it fires
whether or not the loss is ever claimed. Section 5.8's posting table debits the loss account and
credits the asset or accrual on that event, and `risk.recovery_posted` records the insurance
recovery separately when a claim settles. Retained loss is the difference, and it is the largest
component of total cost of risk in most periods. Until the gross loss itself had a posting, that
component had nothing in the ledger to tie to and `tcor_reconciles_to_gl` could not hold.

### 4.10 Findings contributed

Each code is emitted as the standard `finding.raised.v1` with `code`, `severity`,
`evidence_event_ids`, `suggested_next_tool`, `dedupe_key`, and `shelve_policy`, so the alarm
rationalization layer applies uniformly and the findings stream cannot flood.

| Code    | Trigger                                                                      | Severity floor | Suggested next tool                 |
|---------|------------------------------------------------------------------------------|----------------|-------------------------------------|
| ORD-001 | Promise reliability p-chart signal                                           | medium         | hypothesis test on before and after |
| ORD-002 | Backorder aged beyond `backorder_max_age_days`                               | medium         | allocation policy what-if           |
| ORD-003 | `priority_dominance` violated in an allocation run                           | high           | allocation audit                    |
| ORD-004 | WISMO u-chart signal                                                         | low            | promise reliability drill-down      |
| ORD-005 | First contact resolution below target with a named blocking data element     | medium         | visibility what-if                  |
| ORD-006 | CLV at risk above `churn_alert_value`                                        | high           | customer contact ranking            |
| PRC-001 | Maverick leakage above `maverick_alert_pct`                                  | medium         | spend Pareto                        |
| PRC-002 | Match exception backlog aging beyond policy                                  | medium         | process mining on procure-to-pay    |
| PRC-003 | Contract expiry inside the renegotiation lead time                           | medium         | sourcing what-if                    |
| PRC-004 | Material price variance I-MR assignable signal                               | medium         | variance drill-down                 |
| PRC-005 | Tier-1 award concentration above `max_share_per_supplier`                    | high           | reverse stress test                 |
| PRC-006 | Early payment discount missed                                                | low            | payment scheduling review           |
| PRC-007 | Spot buy taken while the contract supplier could still meet the need-by date | medium         | spend Pareto                        |
| HR-001  | Attrition hazard concentration by station or shift                           | high           | labor what-if                       |
| HR-002  | Overtime above `overtime_alert_hours` for `n` consecutive weeks              | high           | rostering what-if                   |
| HR-003  | Certification lapse removes the last eligible worker for a station           | high           | cross-training what-if              |
| HR-004  | Time-to-productivity I-MR signal                                             | medium         | onboarding review                   |
| HR-005  | Single point of failure station                                              | medium         | cross-training what-if              |
| HR-006  | Schedule stability index I-MR signal, or weekend shift rate p-chart signal   | medium         | rostering what-if                   |
| IT-001  | Error budget burn rate above the fast or slow threshold                      | high           | change gating                       |
| IT-002  | Change failure rate p-chart signal                                           | medium         | change window policy what-if        |
| IT-003  | Critical vulnerability unpatched past the zone SLA                           | high           | patch window economics              |
| IT-004  | Conduit violation or cross-zone baseline deviation                           | high           | SIEM correlation                    |
| IT-005  | Detection rule stopped firing on its positive fixture                        | high           | rule regression review              |
| IT-006  | Backup age exceeds the target RPO                                            | high           | restore drill                       |
| IT-007  | Restore drill overdue                                                        | medium         | schedule drill                      |
| IT-008  | Live grant set contains an unmitigated SOD conflict                          | high           | access review                       |
| IT-009  | Correlated cross-zone alert raised by `CorrelationEngine`                    | high           | zone containment review             |
| CMR-001 | Planned promotion lift exceeds modeled servable capacity                     | high           | S&OP reconciliation                 |
| CMR-002 | A forecast ladder step has negative forecast value added                     | medium         | FVA review                          |
| CMR-003 | Rep forecast bias sustained beyond tolerance                                 | low            | bias adjustment                     |
| CMR-004 | S&OP decision latency I-MR signal                                            | low            | cycle retrospective                 |
| CMR-005 | One-number-plan variance above tolerance                                     | high           | reconciliation rerun                |
| FIN-001 | Assignable-cause variance with attribution                                   | medium         | variance drill-down                 |
| FIN-002 | Inventory record accuracy below target                                       | high           | cycle count what-if                 |
| FIN-003 | Excess and obsolete reserve step change                                      | medium         | demand aging review                 |
| FIN-004 | Close cycle time I-MR signal or a close task past due                        | low            | close kaizen                        |
| FIN-005 | Control test failure                                                         | high           | CAPA in 6a11                        |
| FIN-006 | Cash-to-cash degradation signal                                              | medium         | working capital drill-down          |
| FIN-007 | Capex post-audit shortfall beyond tolerance                                  | medium         | assumption review                   |
| TRD-001 | Landed cost shift beyond tolerance under an active scenario                  | medium         | sourcing re-rank                    |
| TRD-002 | Drawback claim window expiring                                               | low            | claim filing                        |
| INS-001 | Claim cycle time I-MR signal                                                 | low            | claims process mining               |
| INS-002 | Loss class outside all policy coverage                                       | high           | coverage gap review                 |
| INS-003 | Experience modifier deterioration                                            | medium         | risk transfer what-if               |
| INS-004 | A payout bound by a sublimit rather than by the policy limit                 | medium         | coverage gap review                 |

Two of these codes are scoped so they cannot become permanent alarms under the shipped
configuration, which is the failure mode this catalog exists to prevent.

ORD-003 fires on a violation of the `priority_dominance` property (section 7.2), not on a raw fill
comparison between two lines. Under `fair_share` and under the shipped `hybrid` default, a
lower-tier line receiving remainder units while a tier-1 contract remainder is short is the policy
working as specified, not a defect. Under `priority` the same observation is a real violation. The
finding evaluates the property the active policy declares, so a policy change changes
what counts as a violation rather than flooding the stream.

PRC-005 asserts only the tier-1 concentration the award engine can measure in-band. Tier-2
concentration needs the E19 supplier DAG, which stays in Phase 6, so `SupplierDagPort` returns
unavailable, `max_tier2_concentration` is reported as `unenforced`, and no in-band finding or
scenario asserts a tier-2 number. When E19 lands, the constraint becomes enforceable and PRC-005
gains a second trigger clause.

## 5. Behavior

### 5.0 How this section obeys the dual-mode rule

Nothing in this section reads a wall clock, calls `random`, opens a socket, or touches a file
directly. Every package receives `Clock`, `Rng`, `Network`, and `Storage` from `twinflow-kernel` at
construction. Three consequences that matter for the implementer:

1. **Every stochastic draw declares a seed namespace.** `seeds.toml` per package lists them, and the
   RNG tree derives a child stream per namespace, so adding a new draw in the service center cannot
   perturb the promotion noise stream and break C1's hash check.
2. **The service center and the AP exception queue are SimPy resources in both modes.** In
   production mode the same code drives the same queue model; only the arrival source differs
   (simulated failure events versus real events off the broker). The queue mathematics is never
   re-implemented.
3. **Conduit monitoring uses one code path.** `NetworkTapPort` is bound to the in-memory `Network`
   middleware in simulation mode and to the broker bridge exporter in production mode. The zone
   lookup, baseline comparison, and violation logic are identical, which is what makes the IEC 62443
   claim testable at all rather than a diagram.
4. **Every paired comparison runs on common random numbers.** Per-namespace streams stop one
   subsystem's draws from perturbing another's. They do nothing for the A/B studies this section
   rests on, and without the rule below those studies measure path divergence rather than treatment.

#### Common random numbers for paired studies

Six comparisons in this section run the same seeded scenario twice and hypothesis-test a delta: the
visibility study in section 5.2, the Friday freeze study in section 5.6, the RFID confirmation study
in section 5.8, the allocation policy bake-off in section 5.1, the cross-training what-if in
section 5.5, and the risk transfer comparison in section 5.9.

Changing the treatment changes control flow. A more visible agent resolves at first contact, so no
escalation is generated, so the number of draws taken from `root/orders/service/handle` differs from
that point on and the two arms desynchronise. Every draw after the first divergence is then a
different draw for a reason that has nothing to do with the treatment, and the measured delta
contains that noise. The rule that removes it:

1. **Every draw is addressed by entity, not by call order.** A stream is subscripted by the id of
   the entity the draw belongs to, following the substream rule in
   `docs/design/variability-and-faults.md` section A.2:
   `root/orders/service/handle/<contact_id>`, `root/itops/change_outcome/<chg_id>`,
   `root/workforce/absence/<worker_id>/<date>`, `root/finance/count_error/<location>/<sku>`,
   `root/insurance/loss_severity/<loss_id>`. Contact 4104's handle time is the same draw in both
   arms because it comes from contact 4104's substream, whatever happened to contacts 1 through
   4103.
2. **Entity ids are assigned before the treatment can affect them.** Ids come from the deterministic
   id policy in section 3, and the entities a paired study compares are provisioned before the sim
   clock starts wherever the treatment could otherwise change how many exist.
3. **A draw an arm does not need is not taken.** Skipping a substream costs nothing, because a
   substream is addressed rather than consumed in order.
4. **The pairing is asserted, not assumed.** `test_paired_arms_share_draws` runs both arms of each
   of the six studies and asserts that every entity present in both arms drew identical values from
   every shared substream. A study whose arms diverge on a shared substream fails as a defect, which
   is the only way to know the hypothesis test is measuring the treatment.

The variance reduction this buys is the reason the section can claim a significant difference from
20 replications rather than needing hundreds. The paired tests in sections 5.2, 5.5, 5.6, 5.8, and
5.9 are all paired-difference tests over matched entities, and each names its replication count
where it is stated.

### 5.1 Order lifecycle (6a12)

**Capture and validation.** An order arrives from one of three sources: the wholesale demand
process, the e-commerce stream (6a6), or the marketplace feed. Validation checks SKU existence,
minimum order quantity, ship-to serviceability, and trade classification presence (a missing HS code
raises a `trade_compliance` hold, which is how E14 makes itself felt on the sell side). The credit
check is a stub by design: it compares open AR from the finance package plus the order value against
`credit_limit` and places a `credit` hold on breach. The source calls it a stub, so it stays one, and
the README limitations section says so.

**Promising.** `PromiseEngine` calls `PromisePort`, which E16 implements. The order of attempts is
on-hand, then in-transit, then scheduled receipts (ATP), then a capable-to-promise build slot from
the finite scheduler (CTP), then a configured default lead time as the last resort. The chosen
source is recorded on the event so promise reliability can later be decomposed by promise source,
which is the analysis that tells an operator whether the CTP path is trustworthy. Quoted date versus
actual ship or delivery date becomes the promise reliability series.

**Allocation.** An allocation run collects open demand within `allocation_horizon_days` and available
supply, then applies the configured policy.

- `Priority`: sort demand by `(allocation_tier, promise_date, -order_value, order_id)` and fill
  greedily. The final `order_id` term makes the sort total, and so deterministic.
- `FairShare`: each demand receives `floor(supply * demand_i / total_demand)` units, then the
  remainder is distributed by largest fractional part with `order_id` as the tie-break (the largest
  remainder method). Deterministic and provably proportional.
- `Hybrid`: contract customers are filled up to `contract_commitment_units` under priority, then all
  remaining demand including the contract remainder is fair-shared.

Every run publishes `fairness_index`, so the policy what-if has a fairness number next to the
service number rather than an argument. The index is Jain's fairness index over the fill ratio of
every demand in the run, including demands filled zero:

```
x_i            = allocated_i / requested_i          for every demand i in the run
fairness_index = (sum_i x_i) ** 2 / (n * sum_i x_i ** 2)
```

Three properties make it usable as a gate. It lies in `[1/n, 1]` and reaches 1 only when every
demand has the same fill ratio. It counts a starved customer, because a demand with `x_i = 0` stays
in the population and drags the index down, so a policy cannot improve its score by starving the
worst-off customer completely. It is defined when total supply is zero: every `x_i` is 0, the
numerator and denominator are both 0, and the implementation returns 1.0 by the stated convention
that a run in which nobody is filled is perfectly equal rather than undefined. That convention is
asserted by `test_fairness_index_at_zero_supply`, so the edge case is a decision rather than an
exception.

The earlier definition, the ratio of the minimum to the maximum fill rate across served customers,
is not used anywhere, because excluding zero-fill customers made it rise when a customer was starved
and left it undefined at zero supply. `fairness_index` is declared in `orders.metrics.yaml` with
this exact expression (section 6.10), which is what lets `run_allocation_whatif` return it and
scenario `s_backoffice_02` assert it.

Sums over demands run in `order_id` order with `math.fsum`, so the index does not depend on
insertion history (D-03).

**Backorders.** Unfilled demand becomes a backorder with a recovery date taken from the next
scheduled receipt covering the SKU. When supply arrives, backorders are filled by
`backorder_fill_policy`, either `fifo_by_created_at` or `priority_then_age`. Aging is trended, and
ORD-002 fires past the policy age.

**Changes and cancellations.** `ChangeCostModel` returns a cost and a rework time from a table keyed
by `(change_type, stage_at_request)`. The cost rises across stages because the physical work already
done must be undone: a quantity decrease before release costs an allocation rewrite, after pick it
costs a putaway, after pack it costs a repack, and after ship it is not a change at all but a return
routed to 6a4. Invariant `change_cost_monotone_in_stage` holds for every change type. Accepted
changes republish the promise if the change affects the date.

**Substitution.** When a line cannot be filled and a `SubstitutionRule` exists for the SKU and the
customer's segment, the engine offers the substitute. If `requires_customer_approval` is true, a
service contact is generated with reason `order_change`, and the approval decision and delay are
drawn from the `root/orders/substitution_response` stream, subscripted by `line_id`. Substitutions
never change the invoice price unless `price_treatment` says so.

**Perfect order.** Evaluated at close, from four independently sourced booleans:

| Component          | Source of truth                                                                   |
|--------------------|-----------------------------------------------------------------------------------|
| Complete           | All lines shipped in full on the first shipment, from outbound events             |
| On time            | Ship date or delivery date versus promise date, per `perfect_order.on_time_basis` |
| Damage free        | No damage-coded return and no damage claim linked to the order                    |
| Correctly invoiced | No AR dispute and no pricing correction on the invoice                            |

`perfect_order_rate` is defined once in the metrics layer. The agent cannot compute it another way
because the tool returns the metric, not a table to aggregate.

### 5.2 Customer service as an operation (6a12)

**Contact generation.** `ContactGenerator` subscribes to a configured set of operational failure
events. For each, it draws whether a contact occurs and when:

```
p_contact = base_rate[reason_code]
          * segment_sensitivity[customer.segment]
          * (1 + escalation_gain * prior_failures_90d)
delay ~ LogNormal(mu[reason_code], sigma[reason_code])   # seed root/orders/service/contacts
```

The generated contact carries `caused_by_event_id`, which is why the causality invariant is
enforceable and why a demo can trace a phone call back to a dock door that stuck.

WISMO takes a second path to the same invariant. An order whose promise date passes with no delivery
confirmation emits `orders.promise_breached` at that instant, and thereafter accrues a WISMO hazard
per elapsed day drawn from `root/orders/service/contacts`. Every WISMO contact names that
`orders.promise_breached` event as its `caused_by_event_id`. The absence of a delivery is not an
event and cannot be a cause, so the event that records the absence is emitted and used instead. The
WISMO rate still rises on its own when promise reliability falls, which was the point of the hazard
formulation, and it now satisfies `contact_generation_causality` rather than needing an exemption
from it.

The same event supplies ORD-004's exposure denominator. A u-chart needs a countable exposure, and
`PromiseBreach.elapsed_days` summed over open breached orders gives order-days open past promise.
Numerator is WISMO contacts, denominator is order-days, and neither is an assumed constant.

**The queue.** `ServiceCenter` is a SimPy resource with capacity taken from the roster
(`RosterPort`). Contacts queue, wait, and abandon if wait exceeds a drawn patience. Handle time is
drawn per reason code and scaled by the agent's proficiency from the workforce learning curve.
Reported KPIs: average speed of answer, service level (fraction answered within
`service_level_seconds`), abandonment rate, occupancy, and contacts per order.

**First contact resolution.** Each reason code declares `required_visibility`. An agent resolves at
first contact if `agent.tool_visibility >= reason.required_visibility` and a skill draw succeeds;
otherwise the contact escalates or produces a callback, and the event records `blocking_data`, the
name of the data element the agent could not see. This is what makes the visibility argument
measurable: run the same seeded shift at `order_header` and at `twin_grounded`, and the LSS engine
hypothesis-tests the FCR delta. The system demonstrates the value of its own API rather than
asserting it.

**Satisfaction, churn, CLV.** Satisfaction decrements by `impact[reason_code]` on each unresolved or
repeated failure and recovers toward baseline at `recovery_rate` per period. Churn is a weekly
hazard `p = logistic(a + b * (1 - satisfaction) + c * failures_90d)`. On churn, remaining CLV is
computed as

```
CLV = sum over t of  (margin_t * survival_t) / (1 + discount_rate) ** t
```

where `margin_t` comes from `CostToServePort`. That port has two implementations and the calculation
ships in two stages, because the activity-based costing model it wants lands eighteen slices later
than the churn model that needs it.

| Stage    | Implementation        | `margin_t`                                                               | `clv_margin_source` |
|----------|-----------------------|--------------------------------------------------------------------------|---------------------|
| Slice 4  | `BaselineCostToServe` | `annual_baseline_margin` divided by the periods per year, per customer   | `baseline_fallback` |
| Slice 22 | `AbcCostToServe`      | Contribution after activity-based cost to serve, per customer per period | `abc_cost_to_serve` |

Wiring the second implementation is a config change, not a code change, and no churn or CLV code
moves. `customer.churned` carries `clv_margin_source`, so every CLV number in the log says which
implementation produced the margin behind it, and a reader can never mistake a fallback for a
modeled contribution. `Customer.annual_baseline_margin` exists only to feed the fallback and is
read nowhere else.

The agent question "what does it cost us if the top two churn" is answered by summing two
`remaining_clv` values, and `get_impacted_customers` returns `clv_margin_source` alongside them so
the answer states which stage it was computed at. From slice 22 those values come from the ABC
model. Before slice 22 they come from the baseline, and saying so is the difference between a
staged delivery and a false claim.

### 5.3 Procure-to-pay (6a13)

Requisitions arrive from the inventory optimizer's reorder signals, carrying the triggering event id
so the whole chain from a stockout risk to a payment is one traceable thread. PO creation selects
the contract that covers the category and supplier; if none exists, the buy is flagged for maverick
evaluation at spend classification time.

**Approval.** `ApprovalRouter` walks the authority matrix for the PO's category and value, producing
the minimal chain of approvers whose limits cover it. Two rules are enforced and tested: the
requester is never an approver, and no approver's limit is below the value they approve. Approval
delay is drawn per role, which is what makes PO cycle time a real distribution instead of a constant.

**Acknowledgment.** The supplier model returns confirmed dates drawn from its reliability profile.
The slip between requested and confirmed is recorded and feeds the buyer-side OTIF view, which is
deliberately different from the supplier scorecard in 6a2: the buyer measures against the requested
date, the supplier measures against the confirmed date, and the gap between the two views is itself
a finding worth showing.

**Three-way match.** On invoice receipt the matcher pulls the PO and every receipt against it and
evaluates in a fixed order: duplicate detection first (same supplier, same amount, invoice date
within `duplicate_window_days`), then PO existence, then receipt existence, then unit of measure,
then quantity within tolerance, then price within tolerance, then freight and tax. The first failing
check determines the exception type, so the exception taxonomy is deterministic rather than
order-dependent. Exceptions enter a queue staffed by AP handlers modeled the same way as service
agents, which gives match exception cycle time a real queueing explanation and gives the process
miner a second office process to discover.

**Payment.** `PaymentScheduler` evaluates each matched invoice against its terms. If a discount is
available, it compares the discount against the annualised cost of capital
(`discount_pct / (1 - discount_pct) * 365 / (net_days - discount_days)`) and takes it when it beats
the hurdle rate. Missed economic discounts raise PRC-006. Payment timing drives DPO and the cash
forecast.

**Strategic sourcing.** An RFX event issues to invited suppliers, who submit price-volume curves,
lead times, and capacity. Scoring normalizes each criterion per `normalization`, applies weights, and
ranks.

The award engine ships two strategies against one interface. `GreedyAwardStrategy` fills by
descending score subject to capacity, max-share, and min-supplier constraints, breaking ties on
`(-score, supplier_id)` so the fill order is total and the result is deterministic. That tie-break
is stated because the allocation engine's is, and an award engine with no tie-break would make two
equal-scoring suppliers order-dependent. `ExactAwardStrategy` enumerates feasible allocations on a
declared quantity lattice and takes the argmax under the same `(-score, supplier_id)` ordering, so
the exact answer is unique too.

Greedy is not optimal in general and the section does not claim it is. Price-volume break curves
make the objective non-convex in the allocation: a supplier whose unit price drops at a break
quantity can be worth more volume than its marginal score justifies at the previous break, and
min-supplier and max-share caps make the feasible set non-matroidal. The shipped counterexample
`tests/fixtures/sourcing/greedy_suboptimal.yaml` has three suppliers, one break curve, and
`min_suppliers: 2`, on which greedy lands below the exact optimum. The fixture is committed together
with the gap the suite measures on it, so the number is recorded rather than asserted from memory,
and VG-PRC-03 fails if the measured gap moves. It is a fixture rather than a footnote, so the
limitation cannot quietly disappear.

`AwardGapReport` is what the engine returns alongside the award: the greedy objective, the exact
objective when the instance is small enough to enumerate, and the relative gap. The enumeration
budget is a config key (`sourcing.exact_award_max_suppliers`, default 6) and the report says
`exact_unavailable` above it rather than reporting a gap it did not measure. VG-PRC-03 asserts the
measured gap on the fixture suite; it does not assert that the gap is zero.

A mixed-integer formulation that closes the gap in general is a named ROADMAP milestone with its
dependency on the OR-Tools deterministic budget contract (D-04) recorded. It is sequenced, not
dropped, and until it lands the report states the gap rather than hiding it.

Tier-1 concentration is computed from the award itself. Tier-2 concentration needs the E19 supplier
DAG, which stays in Phase 6, so in-band `SupplierDagPort` returns unavailable and the consolidation
what-if reports tier-2 concentration as `unenforced` rather than as zero.

**Spot buy versus contract.** The fourth tactical decision 6a13 names, and the one that only exists
when a supplier slips. `SpotBuyEvaluator` subscribes to `supplier.commit_date_slipped` and to
`orders.line_backordered`, and opens a decision whenever a slip leaves a shortage that the contract
supplier cannot recover before `need_by`.

It prices three options against each other: buy spot at `SpotPricePort`'s quote, wait for the
contract recovery date and carry the stockout, or expedite the contract order through
`ExpediteEvaluator`. The spot option carries the price premium, any minimum-volume or exclusivity
charge the contract levies, and a quality cost from the spot supplier's higher defect rate. The wait
option carries the stockout cost from the at-risk order lines and the SLA penalty schedule, the same
input the expedite decision uses, so the three options are priced on one basis.

The decision is recorded whichever way it goes, and a requisition raised from it carries
`source: spot_buy` and `buy_mode: spot` on the PO, which is what keeps a justified spot buy out of
the maverick spend numbers. A spot buy taken while the contract supplier could still meet the
need-by date is not a tactic, it is maverick spend; `spot_buy_never_beats_available_contract`
forbids the engine from recommending it and PRC-007 raises it when a human does it anyway.

**Contracts.** Cumulative volume advances through the tier schedule, republishing the unit price on
tier achievement. Rebates accrue per period on either a retrospective basis (the whole volume
reprices at the achieved tier) or an incremental basis (only volume above the threshold reprices).
Both are implemented because the accounting differs and the difference shows up in the GL. Expiry
inside `renegotiation_lead_days` raises PRC-003 with annual spend at risk attached.

**Spend analytics and maverick detection.** Every settled spend transaction is classified into the
three-level taxonomy. A transaction is maverick when a live contract covers its category and supplier
class but the transaction did not reference it. Leakage is
`(paid_unit_price - contract_unit_price) * qty`, floored at zero, and the Pareto by category and by
supplier is the standard first move.

**Savings versus avoidance.** Two ledgers, never merged, and the split is drawn where the chart of
accounts can witness it. A savings entry has `baseline_method: prior_price` and a GL posting that
resolves to the material price variance account, which is the one account in section 5.8's posting
table that records a price difference. Every other baseline (market index, budget, announced
increase) is an avoidance entry: it records an increase that did not happen, has no GL posting by
construction, and carries the announced increase or the index quote in `evidence_event_ids`. The
report presents them side by side with a note that only one of them reaches the P&L, which is the
honest version of the claim procurement teams make.

**Tactical decisions.** `ForwardBuyEvaluator` compares duty and price increase avoided against
carrying cost, obsolescence risk from the E&O model, and the cash cost of buying early, and returns a
breakeven horizon. `ExpediteEvaluator` compares the premium freight quote from the transport package
against the stockout cost derived from the order book's at-risk lines and the customer's SLA penalty
schedule. `EoqValidator` computes the closed-form EOQ and then runs the twin at a grid of order
quantities around it to confirm the analytic answer is actually the simulated minimum, which is the
same analytic-versus-simulated discipline the MEIO layer uses.

### 5.4 Tariffs and trade policy (E14)

`LandedCostCalculator` computes, per incoterm, the components each party bears, and returns a
breakdown that always sums to the total. Duty is evaluated from the active schedule composed with
any active scenario overlays:

```
duty = ad_valorem_pct * dutiable_value        (kind = ad_valorem)
     = specific_per_unit * qty                (kind = specific)
     = ad_valorem_pct * dutiable_value + specific_per_unit * qty   (kind = compound)
```

`dutiable_value` is config-selectable between transaction value and transaction value plus freight
and insurance, because the choice changes the answer and a reader from trade compliance will look
for it.

Scenario overlays are pure functions on the schedule, and the two operations have separate names
because they have separate types (section 3.3). `merge_overlays(overlay, overlay) -> overlay`
combines two overlays into a canonical one, and it is tested for associativity over generated
overlays with deliberately overlapping targets, not only disjoint ones. `apply_overlay(schedule,
overlay) -> schedule` produces a new schedule, and the test that matters is that applying A then B
yields the same content hash as applying `merge_overlays(A, B)`. The shipped `retaliation_mirror`
can overlap `rate_shock_plastics`, so an invariant that held only on disjoint targets proved nothing
about the configuration the repository actually ships. De minimis changes affect the parcel channel
only, which is where the e-commerce flow (6a6) feels trade policy directly. Retaliation overlays are
declared as mirrors of another overlay so a scenario author writes one line rather than a table.

FTZ admission defers duty until withdrawal. If the withdrawal is for export, no duty is due and the
lot becomes eligible for drawback instead. If it is for domestic consumption, duty is due at the rate
in force at withdrawal, which is what makes the FTZ interesting under a rate shock scenario. The
neutrality invariant pins the implementation: with an unchanged rate, FTZ changes only the payment
date, so any test that shows a different total duty has found a bug.

The tariff engine is the input to three things outside itself, and each one is reached through a
declared seam rather than an assumption.

| Consumer                             | Seam                                                     | Behavior when the other side is absent                                           |
|--------------------------------------|----------------------------------------------------------|----------------------------------------------------------------------------------|
| Procurement forward-buy and sourcing | `trade.landed_cost_computed`, `trade.scenario_activated` | Procurement's `LandedCostPort` null implementation returns duty zero             |
| Multi-echelon inventory re-run (6a8) | `MeioPort.rerun(scenario_id, landed_costs) -> MeioDelta` | Returns `MeioDelta.unavailable()`, rendered as "not available" and never as zero |
| Finance duty variance                | `trade.duty_accrued` through the posting rules           | The duty variance kind reports zero rows rather than a wrong number              |

`MeioPort` is the interface `run_landed_cost_scenario`'s MEIO delta comes from. Without it the tool
declared an output field nothing could produce. The port is declared in `twinflow_trade.ports` and
implemented by the planning package (6a8) when installed; its null implementation returns
`MeioDelta.unavailable()`, and every consumer renders that as "not available". A missing planning
package can never be read as no inventory impact, which is the failure mode a zero default creates.

The landed cost event carries `scenario_id` so every downstream number can be attributed to the
policy assumption that produced it.

### 5.5 Workforce (6a14)

**Hiring lag.** A requisition opens when a headcount driver crosses its threshold. The pipeline runs
stage by stage with drawn conversions and dwell times, so time-to-fill is an emergent distribution,
not a parameter. The consequence the source cares about is that headcount decisions lag demand: a
peak that needs people in week 40 needs a requisition in week 33, and the twin makes that lag
visible instead of assuming labor is instantly available.

**Ramp.** A new hire starts at `initial_productivity_ratio` and climbs the Wright curve as cumulative
units accumulate. Error rate follows its own curve downward. Both feed the physical twin: a station
staffed by ramping workers is slower and produces more quality findings, which is the loop the source
asks for between onboarding and the quality stream.

**Skills gating.** Station assignment consults `StationEligibility`. An expired certification removes
stations immediately, and if that leaves a station with no eligible worker on the roster, HR-003
fires at high severity because the line is about to stop. `single_point_of_failure_stations` is
computed each roster publication and raises HR-005.

**Cross-training as an investment.** The what-if takes a list of `(worker, station)` pairs, prices the
training (trainee hours, trainer hours, lost production during training), applies the new eligibility,
and reruns a seeded absenteeism scenario. The payoff is measured in coverage, overtime hours avoided,
and service level held, and the LSS engine tests whether the difference is significant across
replications rather than across one lucky seed.

**Attrition.** The hazard is evaluated weekly per worker. Because its drivers are quantities the twin
already measures, burning the workforce out shows up as regretted turnover with a bill attached:
recruiting cost, onboarding labor, the ramp-loss integral, and backfill overtime. That is what turns
workforce care into a P&L argument instead of a slogan.

**Absenteeism.** The generator draws absence from a model whose true coefficients are known. The
predictor is trained on the generated history and scored with the Brier score and a calibration
curve against a base-rate benchmark. The forecast publishes to E23, and the roster it produces
returns as `hr.shift_assigned`, closing the loop. When E23 has not landed, a fallback roster
allocates workers to stations by eligibility and seniority so the workforce package is never blocked.

**Engagement, measured behaviorally.** 6a14 asks for engagement measured behaviorally rather than
by survey, trended on control charts as a leading indicator. No survey instrument exists anywhere in
the model. `EngagementSnapshot` is published weekly per worker from state the twin already records,
and aggregated per shift and per station.

| Indicator                  | Computed from                                                            | Chart                 |
|----------------------------|--------------------------------------------------------------------------|-----------------------|
| `schedule_stability_index` | Shift-start changes inside the notice window over shifts worked, 8 weeks | I-MR                  |
| `weekend_shift_rate_8w`    | Weekend shifts over shifts worked, 8 weeks                               | p-chart               |
| `strain_trend_slope`       | OLS slope of the strain index over 8 weeks, strain units per week        | I-MR                  |
| `overtime_pct_4w`          | Overtime hours over total hours, 4 weeks                                 | I-MR on log transform |

The chart assignments are in section 7.4 and the metric definitions are in section 6.10, because a
leading indicator that is not in the semantic layer cannot be charted and cannot be asked about.
HR-006 fires on a signal from the first two. The loop closes back on attrition: the same
`schedule_stability_index` and `weekend_shifts_rolling_8w` are drivers in the attrition hazard, so a
schedule-stability signal is an early warning of the turnover the hazard prices later.

**Labor cost accounting.** Every hour lands in the labor ledger with its hour type and its
activity, which is what lets ABC allocate labor to orders later and what lets the labor efficiency
variance drill down to a specific shift.

**The peak season what-if.** Three strategies are priced over the same seeded demand: temps (fast,
lower productivity, higher error rate, no attrition cost), overtime (no ramp, rising strain and
attrition hazard, premium rates), and a hiring pulse with partial post-peak layoff (ramp cost,
severance, morale effect on the remaining workforce through schedule stability). Output is a total
cost comparison with the error-rate and attrition consequences priced in, and the LSS engine's
verdict on whether the differences are real.

### 5.6 IT and cybersecurity operations (6a15)

**The twin's own infrastructure is modeled.** Each CI has a service model with a capacity, a queue,
and a failure process. Golden signals come from that model in simulation mode and from OpenTelemetry
in production mode, but the SLI computation is one implementation over `itops.health_sample`.

**Logs and traces.** 6a15 asks for metrics, logs, and traces on every service, and metrics alone
cannot carry two of the four DORA measures. Every request through a modeled CI produces a `Span`,
spans join into a `TraceSample` with a critical path, and every log line is a `LogRecord` carrying a
`template_id` and, where one exists, the `trace_id` it belongs to.

Three things become measurable that were previously inferred from ticket timestamps. Lead time for
changes reads the trace that carries the change's `chg_id` from first commit-analog event to the
span in which the new version first serves a request. Failed deployment recovery time reads the
first error-free trace after the incident's mitigation span. Request error rate and latency p95 come
from the span stream rather than from a health sample that already aggregated them away.

Sampling is head-based at a configured rate plus tail-based retention of every trace containing an
error span, and `sampled_by` records which rule kept a trace so a rate estimate can correct for it.
The sampling decision is drawn from `root/itops/trace_sampling` subscripted by `trace_id`, which
keeps it deterministic and keeps it out of the way of every other draw. Log volume is published as
`itops.log_volume_snapshot` per template rather than per rendered string, so log volume is countable
and a log storm is a chart rather than an anecdote.

**Error budgets.** Budget consumed is `(1 - achieved_sli) / (1 - target)` over the window. Burn-rate
alerting uses the multi-window multi-burn-rate pattern published in the Google SRE Workbook,
chapter 5: a fast burn alert on a short window and a long window together, and a slow burn alert on
longer windows, with both windows required to be in breach so a brief blip does not page. When the
budget is exhausted, the change policy gate flips: only emergency changes are approved until the
budget recovers. That gate is a testable behavior, not a policy document.

The burn-rate thresholds are derived at config load, never written as literals:

```
burn_rate = budget_fraction * window_days * 24 / long_window_hours
```

The Workbook's table gives budget fractions and windows, not portable constants. Its recommended
2 percent in one hour, 5 percent in six hours, and 10 percent in three days evaluate to 14.4, 6, and
1 only at a 30-day SLO window, which is the window that chapter uses throughout. This section's
SLOs run on a 28-day window, so the same fractions give 13.44, 5.6, and 0.9333. Hard-coding 14.4
against a 28-day window would have claimed the Workbook's derivation while consuming 2.14 percent of
budget rather than 2 percent.

`derive_burn_rates(window_days, budget_fraction, long_window_hours)` computes them,
`BurnRateTable` holds the result, and section 6.5 declares fractions and windows. VG-IT-02 asserts
the derivation against the Workbook's published pairs by evaluating it at `window_days = 30` and
checking it reproduces 14.4, 6, and 1 exactly, then asserts the alerting boundaries on a fixture SLI
series at the configured 28 days. A change to `window_days` moves the thresholds and the gate stays
true, which is the property a hard-coded constant destroys.

**Change management.** Change failure probability is

```
p_fail = base[type]
       * risk_multiplier(risk_score)
       * window_multiplier(day_of_week, hour)
       * criticality_multiplier(ci.criticality)
       * (1.0 if has_rollback_plan else no_rollback_penalty)
```

The shipped default configuration gives Friday late-afternoon a materially higher multiplier, which
reproduces the classic lesson the source names. A failed change opens an incident with
`caused_by_change_id` set, which is exactly what makes change failure rate computable rather than
self-reported. The what-if "enforce a Friday freeze" reruns the same seeded change stream against a
policy that reschedules those changes and hypothesis-tests the change failure rate delta.

**DORA metrics.** Deployment frequency counts implemented changes per window. Lead time for changes
measures request to implementation. Change failure rate is failed or rolled-back changes over total
changes. Failed deployment recovery time measures the incident MTTR for change-caused incidents.
Each goes on the chart its data type demands, listed in section 7.

**Vulnerability and patch economics.** The synthetic CVE feed emits vulnerabilities against component
versions present in the CMDB. Identifiers are prefixed `TWF-CVE-` and never collide with real CVE
identifiers; the README states the feed is synthetic. CVSS v3.1 base scores are computed from the
vector rather than stored, so the implementation is testable against the published specification.

For a vulnerability on a CI that needs a production window, `PatchWindowEvaluator` enumerates
candidate windows over the next `patch_horizon_days`, calls the twin's what-if engine to price the
production cost of taking that CI down for `window_minutes` in each window (throughput lost, orders
at risk, overtime to recover), and computes the modeled breach exposure of waiting.

`ExposureModel` is a distribution, not a scalar, and every step says which it is:

```
p_daily(v) = exploit_probability_daily[v.severity] * (known_exploited_multiplier if v.known_exploited else 1.0)
P_breach(t) = 1 - (1 - p_daily(v)) ** t                      # scalar in [0, 1]
Impact ~ downtime_hours x gross_profit_rate_per_hour + recovery_cost + claim_cost + regulatory_cost
Loss(t) = Bernoulli(P_breach(t)) * Impact                    # a distribution over Money
```

`downtime_hours` is drawn from `root/itops/breach_impact` subscripted by `vuln_id`, and
`gross_profit_rate_per_hour` comes from `fin.gross_profit_rate` through `GrossProfitRatePort`, so
breach exposure is valued from the same ledger number as a business-interruption claim.
`known_exploited_multiplier` is a declared config key (section 6.5) with a stated default, because
"raised for known exploited" without a number is not a model. It multiplies the daily hazard, and
`p_daily` is clamped to 1.0 so a large multiplier cannot produce a probability above one.
`known_exploited_fraction` is a separate key that sets how many published vulnerabilities carry the
flag; prevalence and uplift are two parameters and the section keeps them apart.

The objective is stated in the risk measure it actually uses. `CvarObjective` ranks candidate
windows by

```
objective(w) = production_cost(w) + (1 - alpha) * E[Loss(t_w)] + alpha * CVaR_beta[Loss(t_w)]
```

with `alpha` in `[0, 1]` and `beta` the tail probability, both config keys. At `alpha = 0` this is
expected total cost, which is risk neutral. At `alpha = 1` it is conditional value at risk at level
`beta`, which prices the tail rather than the mean. A scalar multiplier on expected cost, which the
config previously called `risk_aversion`, is a linear weight on a mean and is risk neutral for any
value it takes; it is gone, and `risk_preference_alpha` and `cvar_beta` replace it. The tail is
estimated from `cvar_samples` draws of `Loss(t)` per candidate window, seeded from
`root/itops/breach_impact`, and the event carries the sample count so the estimate's noise is
visible.

`sec.patch_window_evaluated` carries every candidate window with its production cost, its expected
loss, its CVaR, and the objective value, so the agent presents the tradeoff rather than only the
answer. Deferral needs an explicit accepted risk amount and a decision maker, which is how risk
acceptance is supposed to work and rarely does.

**Zones and conduits.** Zones are declared in config with their Purdue level and target security
level. Conduits declare the flows that may cross. The tap observes every crossing. A crossing with
no matching conduit, or with a protocol the conduit does not permit, is a violation. Crossings that
match a conduit are compared against a learned baseline profile (rate, byte volume, direction mix)
and deviations beyond the configured control limits are anomalies. Both are security findings, and
both are things the Purdue-segmented docker topology makes real rather than notional.

**Detection rules.** Rules are versioned code under the `detections` storage prefix. The engine runs
them over the historian on a schedule, against a snapshot pinned to a stated watermark and with the
total ordering every historian query in this section carries (section 3). Each rule must ship a
positive and a negative fixture; CI fails a rule without both, fails a rule whose logic changed
without a version bump, and fails a rule that stops firing on its own positive fixture. That last
check is IT-005 and it is the difference between detection engineering and a wall of untested
queries.

**Correlation, the lightweight SIEM analog.** A detection rule judges one event stream in isolation,
which is why a slow credential-spray across three zones looks like three unremarkable findings. 6a15
asks for cross-zone correlation with detection rules as versioned code, and `CorrelationEngine`
supplies the second half.

It consumes the finding stream and the detection-rule stream, groups by the join keys the rule
declares (`src_ci`, `zone_id`, `subject_id`, or `subject_kind`), and raises
`sec.correlation_alert_raised` when at least `min_inputs` distinct inputs appear across at least
`min_distinct_zones` zones inside a tumbling window of `window_seconds`. The alert carries every
contributing finding id, so a correlated alert drills down to the individual detections and from
there to the raw events.

Correlation rules live beside detection rules, ship the same positive and negative fixtures, and
fail CI under the same three rules. Each window is sorted by the canonical total order
`(sim_ts, producer_id, seq)` before evaluation, so the alerts raised do not depend on arrival order
inside the window (D-07). IT-004's suggested next tool now points at a component with an API, an
event, a config block, and a gate, rather than at a label.

**RBAC.** Deny by default. Every twin REST route, MCP tool, and agent tool declares its required
permission in `tools/manifest.yaml`. The agent's tool calls pass through the same engine as a
human's API call, and every `granted` and `denied` decision is logged with the actor identity, which
is the audit trail the governance register consumes.

**Autonomy tier on mutating tools.** Two tools in section 5.10 change state rather than reading it:
`run_restore_drill` injects a failure, and every `twin:whatif` tool consumes a simulation budget.
E5's tier enum and its approval gate are resequenced ahead of this band (section 8.2), so every tool
in `tools/manifest.yaml` declares a tier. In-band this section ships L1 and L2 only: a read tool is
L1 (advise) and a mutating tool is L2 (recommend, human approval recorded before execution). No tool
here is L3. The approval is an event with an `actor`, so an agent-invoked restore drill has the same
audit trail as a human-invoked one. E5 later adds L3 and the guardrail evaluator; it does not have
to retrofit the tier field.

**Backup and restore.** Backups run on schedule with an integrity hash and a verification flag. A
restore drill is a `ChaosScenario` of kind `restore_drill` (section 3.5): inject a CI failure at a
sim-time, detect, select the newest verified backup, restore, and measure. RPO is the sim-time
between the last verified backup and the failure, and the drill counts the events that fall in that
window so data loss is a number, not an estimate. RTO is detection to healthy. Targets are declared
in config as synthetic policy values carrying `provenance: synthetic`; the README states they are
illustrative and are not drawn from any client deliverable.

**What 6a15 leaves for E18.** The zone model, the conduit tap, the detection engine, the incident
pipeline, backups with measured restore times, and the error budget. E18 adds adversarial scenarios
that drive them, and the readiness report it produces is scored against the runbooks and SLOs defined
here.

### 5.7 Marketing, sales operations, S&OP (6a16)

**Promotions.** A promotion multiplies baseline demand by its lift curve during the window. The
incremental units split three ways, and the split is recorded as ground truth on
`mkt.lift_realised`:

```
incremental_total = promoted_units - baseline_units
pulled_forward    = pull_forward_fraction * incremental_total
incremental_true  = incremental_total - pulled_forward
cannibalised_from[j] = C[i][j] * baseline_j   (removed from j, added to i)
```

Pulled-forward units are subtracted from the following periods at geometric weights summing to one,
so the post-promotion dip is generated by construction and the naive forecaster gets fooled by it
exactly the way real ones do. Because the true decomposition is logged, E30's causal estimate has a
ground truth to be scored against, which is the point the source makes about promotion effects being
the textbook case where correlation lies.

A promotion is checked against modeled capacity at planning time. If the planned lift exceeds what
the DC can serve within the SLA, CMR-001 fires before the campaign runs, which is the marketing
operations failure the source names: the campaign that fills the order book and empties the fill
rate.

**Demand as a lever, not an input.** 6a16's thesis is that demand stops being purely exogenous and
becomes partly something the company pulls. Three seams carry that, and none of them is implicit.

| Lever             | Carrier                                                | Consumer                | Effect                                                        |
|-------------------|--------------------------------------------------------|-------------------------|---------------------------------------------------------------|
| Promotion lift    | `DemandShapingPort`, `mkt.demand_multiplier_published` | `ArrivalProcess` (6a12) | Multiplies the baseline arrival intensity per SKU per period  |
| Quota pressure    | The same multiplier, source `quota_pressure`           | `ArrivalProcess`        | Adds the intra-period pressure curve to the same multiplier   |
| Channel mix drift | `ChannelMixPort`, `mkt.channel_mix_published`          | `ArrivalProcess`        | Sets the share vector each order's channel is drawn from      |
| Promo calendar    | `PromoFeaturePort`, `mkt.promo_features_published`     | Forecaster (6a1)        | Feeds the promo calendar to the forecaster as a feature frame |

`DemandMultiplier` carries its factor decomposition, so an arrival spike is always attributable to
the levers that caused it. The multiplier applies to intensity, never to realized orders, so the
arrival process stays a point process rather than a scaled count and the queueing results downstream
stay meaningful.

The forecaster coupling matters most and is the one 6a16 states outright: the forecaster must ingest
the promo calendar as a feature. `PromoFeatureFrame` (section 3.6) is built from the calendar alone
and never from realized demand, so a forecaster consuming it cannot leak the outcome. The naive rung
of the FVA ladder does not receive the frame and is fooled by the post-promotion dip; the
statistical rung does receive it and is not. That contrast is what makes the FVA ladder measure
something rather than restate an assumption.

Channel mix drifts as a Dirichlet random walk on the share simplex, so the wholesale versus
e-commerce balance moves over a run instead of being a constant the building argues about once. The
mix feeds cost-to-serve through the channel dimension on every order, so a mix shift shows up as a
margin movement with a named cause rather than as unexplained variance.

**Sales pipeline and bias.** Opportunities progress through stages with drawn conversions. Each rep
submits a forecast equal to the probability-weighted pipeline scaled by their true bias multiplier
plus noise. The demand planning function measures each rep's realized bias over time and learns whose
numbers to haircut. The bias multiplier truth is logged so the measurement can be scored.

**Quota effects.** Order arrival intensity within a quota period follows the configured pressure
curve, and discount depth escalates near the boundary. The result is a quarter-end spike that hits
the DC every thirteenth week as a standard demand pattern the rest of the system has to absorb.

**NPI cold start.** A launched product has no history. The forecaster uses the analog SKU's profile
blended with the Bass diffusion prior for `cold_start_blend_periods`, then transitions to its own
history. `npi.adoption_observed` carries the analytic Bass expectation next to the observed value so
the cold-start handling is measurable rather than asserted.

**The S&OP cycle.** Five steps run on the configured monthly calendar, each a process instance with
start and end events:

1. **Product review.** NPI decisions and rationalization decisions, published as changes to the
   active SKU set.
2. **Demand review.** The statistical forecast, the sales input, and the marketing calendar are
   reconciled into one consensus number. The FVA ladder scores each input's historical contribution,
   so a step that makes the forecast worse is visible as negative FVA.
3. **Supply review.** Capacity against the consensus, taken from the factory finite schedule, DC
   labor requirement, and transport capacity. `RoughCutCapacityCheck` (section 3.6) is the
   computation, and `sop.supply_review_mode` selects it: `analytic` is a rough-cut plan over
   bill-of-resource coefficients and is the shipped default, `surrogate` calls E28 through
   `CapacityPort`, and `full_simulation` runs the twin over the horizon. Gaps are identified with
   their constraining resource, and `sop.supply_review_completed` records which mode produced the
   numbers so a rough-cut figure is never mistaken for a simulated one.
4. **Integrated reconciliation.** Each gap is turned into options, and each option is priced by the
   financial twin: margin impact, cash impact, service impact.
5. **Executive meeting.** The agent presents the decision packet. The decision is logged with its
   assumptions and confidence, and mirrored to the governance register.

Next month's cycle scores last month's decisions: `sop.decision_scored` compares each logged
assumption against its measurement query and reports the outcome versus expectation. Maturity metrics
(plan adherence, FVA by source, decision latency, one-number-plan variance) are computed each cycle
and trended.

Because every step emits start and end events with `cycle_id` as the case key, the process mining kit
can discover the S&OP process itself, find the rework loops in it, and compute where the month goes.
The twin runs a kaizen on its own planning ritual.

### 5.8 Finance and accounting (6a17, E22)

**Posting.** `PostingEngine` subscribes to the event bus and evaluates `posting_rules.yaml`. Each
matching rule produces a balanced journal entry carrying `source_event_id` and `rule_id`. Nothing
else writes to the ledger. Money is integer minor units end to end, and every rule fixture asserts
the entry balances exactly.

A representative slice of the rule set (the full set lives in the file, and each row has a fixture):

| Source event                                                              | Debit                                                            | Credit                                              | Amount basis                                                                 |
|---------------------------------------------------------------------------|------------------------------------------------------------------|-----------------------------------------------------|------------------------------------------------------------------------------|
| `receiving.goods_receipt`                                                 | Inventory raw material                                           | GR/IR clearing                                      | PO price times qty received                                                  |
| `trade.duty_accrued`                                                      | Inventory raw material or duty expense per `duty_capitalisation` | Duty payable                                        | computed duty                                                                |
| `procurement.three_way_match_evaluated` (matched)                         | GR/IR clearing                                                   | Accounts payable                                    | invoice amount                                                               |
| `procurement.three_way_match_evaluated` (price variance within tolerance) | Material price variance (PPV)                                    | Accounts payable                                    | (invoice price minus standard) times qty                                     |
| `production.material_issue`                                               | Work in process                                                  | Inventory raw material                              | standard qty times standard price, usage delta to material quantity variance |
| `production.completion`                                                   | Finished goods                                                   | Work in process                                     | standard cost of output                                                      |
| `production.scrap_recorded`                                               | Scrap variance                                                   | Work in process                                     | standard cost at the scrap point                                             |
| `hr.labor_cost_posted`                                                    | Work in process (direct) or labor expense (indirect)             | Accrued payroll                                     | hours times rate, rate and efficiency deltas to their variance accounts      |
| `outbound.shipment_confirmed`                                             | Cost of goods sold                                               | Finished goods                                      | valuation method                                                             |
| `orders.order_invoiced`                                                   | Accounts receivable                                              | Revenue and tax payable                             | extended price net of discounts                                              |
| `transport.freight_invoice`                                               | Freight expense or premium freight expense                       | Accounts payable                                    | carrier invoice, expedite premium isolated                                   |
| `ar.cash_received`                                                        | Cash                                                             | Accounts receivable                                 | payment, early-pay discount to sales discounts                               |
| `procurement.payment_executed`                                            | Accounts payable                                                 | Cash                                                | payment, discount taken to discounts received                                |
| `returns.disposition_completed`                                           | Inventory or disposal loss by disposition                        | Returns allowance                                   | recovery value by disposition path                                           |
| `inv.count_completed` (variance)                                          | Shrink expense                                                   | Inventory                                           | book minus physical at valuation                                             |
| `inv.reserve_updated`                                                     | Excess and obsolete expense                                      | Inventory reserve (contra)                          | reserve model output                                                         |
| `capex.approved` and asset placed in service                              | Fixed assets                                                     | Cash or accounts payable                            | invoice                                                                      |
| depreciation run                                                          | Depreciation expense                                             | Accumulated depreciation                            | schedule                                                                     |
| `risk.premium_rated`                                                      | Insurance expense                                                | Prepaid insurance or accounts payable               | premium accrual                                                              |
| `risk.loss_recognised`                                                    | Loss expense by `loss_type`                                      | Inventory, fixed assets, or accrued liabilities     | gross loss at the valuation the loss type declares                           |
| `risk.claim_settled`                                                      | Cash                                                             | Loss recovery (contra to the original loss account) | payout                                                                       |
| `ar.invoice_corrected`                                                    | Revenue or tax payable                                           | Accounts receivable                                 | correction amount, signed                                                    |
| `mkt.campaign_spend_posted`                                               | Marketing expense                                                | Accounts payable                                    | campaign cost                                                                |
| `gl.period_closed`                                                        | Income summary, then retained earnings                           | Nominal accounts, then income summary               | the closing entry of section 3.7                                             |

**Statements.** `ProfitAndLoss`, `BalanceSheet`, and `CashFlow` are pure functions of the ledger for a
period. The cash flow statement is produced by the indirect method from the ledger and cross-checked
against the direct sum of cash-account movements; the two must agree exactly, which catches a whole
class of posting-rule mistakes.

**Standard costing and variance drill-down.** The roll-up produces standard costs from the BOM and
routing at a single effective revision. During the period, actuals accumulate against standards and
`VarianceEngine` computes each variance kind from its published formula. Every variance carries an
attribution list: the specific goods receipts, labor records, scrap events, duty accruals, and
freight invoices that produced it, with signed amounts that sum exactly to the variance. Clicking a
variance lands on physical events, which is the thesis the source states: every dollar of variance
has a physical explanation and the system can show it.

**The common-cause gate.** Before a variance appears on the explain list, the engine sends its
historical series to the LSS engine, which runs an I-MR chart. A point inside the limits with no
rule firing is labeled `common_cause` and the report says so. Only `assignable` variances are put
in front of a human. This is the statistical discipline finance reviews lack.

The gate has an acceptance criterion, and the criterion is scoped to what a published source states.
Under the single rule "one point beyond the 3-sigma limits", the NIST/SEMATECH e-Handbook section
6.3.1 publishes the false alarm rate for a normal characteristic on a chart with known parameters:
0.00135 in one direction, 0.0027 in both. VG-FIN-07 runs the gate with `nelson_rules: [rule_1]` on a
seeded in-control stream and asserts the observed assignable rate against 0.0027 to the precision
the handbook prints it, three significant digits.

The full Nelson rule set on an I-MR chart whose limits are estimated from the same data has no
published false alarm rate, and no closed form. It needs a Markov-chain average run length
computation or a simulation, and the handbook does not contain it. The section does not assert one.
The shipped rule set's rate is measured once, recorded as `nelson_set_false_alarm_rate` in the
capability report with its measurement method and its Monte Carlo standard error, and treated as a
regression baseline rather than as a validated statistic. Open question 13 records what would be
needed to promote it. Under D-11 condition 5, a statistic with no valid external reference is an
open question rather than a passing gate, and the gate ships at the scope the reference supports.

**Inventory.** Valuation runs per SKU per period under the configured method, and the flow identity is
asserted in both units and value. The E&O reserve reads forward coverage from the demand model, so the
reserve moves when the forecast moves, and the driver events are recorded. Cycle counts run by ABC
class and produce both accuracy measures. Because RFID scan confirmation can be turned off in config,
the repo can run the same seeded shift with and without it and hypothesis-test the record accuracy
delta, then propagate that delta into shrink, reserves, and write-offs. The two arms draw count
errors from `root/finance/count_error` subscripted by `(location, sku)`, so the same location draws
the same error in both arms and the measured delta is the treatment rather than path divergence
(section 5.0). That chain is the honest, fully synthetic version of the inventory-record-accuracy
argument.

**Activity-based costing.** Pools collect indirect costs from the GL. Drivers come from the twin's own
activity records: every station touch, every pick line, every service contact, every return
inspection. Rates are recomputed each period. Cost to serve is then computed per order by summing the
activities that order actually consumed, which is why a five-station parcel order carries five
stations of cost. Channel and customer profitability roll up from there.

**FP&A.** The budget is driver-based: the S&OP consensus volume drives activity quantities, ABC rates
turn those into costs, and the result is a budget by account that reconciles to the plan. Rolling
reforecasts refresh at each cycle. The variance-to-budget bridge decomposes budget to actual into
named components (volume, price, mix, rate, efficiency, spend, and the residual), and the bridge must
reconcile exactly, which is the test that keeps the narration honest.

**Capex governance.** An accepted what-if becomes a capex request. Cash flows come from twin
projections over the same metric definitions used to measure the result later, which is what makes the
post-investment audit meaningful. NPV, IRR, and both payback measures are computed, the authority
matrix routes the approval, and at `post_audit_lag_periods` the realized benefit is measured and
compared. The hit rate across all approved capex becomes a KPI of the decision process itself.

**Month-end close.** The close checklist is a task graph with dependencies and owners. Tasks emit
start and complete events with `period_id` as the case key. Accruals post for goods received not
invoiced and for unbilled revenue with their reversal entries scheduled. Subledger to control account
reconciliations run, and a break raises `close.reconciliation_break`. Close cycle time, critical path,
manual journal count, and rework count are the KPIs, and the close kaizen what-if reorders or
parallelises tasks subject to the dependency graph and tests whether close time actually dropped.

**Controls.** SOD rules are evaluated against the live grant set from `twinflow-itops` through
`GrantsPort`, so the finance package owns what conflicts and the IT package owns who has what. The
controls library maps each control to the process it governs, and control tests run on their declared
frequency as automated audits whose results feed the compliance layer in 6a11 and the findings stream.

**E22 working capital.** AP and AR terms drive scheduled cash. DIO, DSO, and DPO are computed from
ledger balances and flows with the definitions fixed in the metrics layer. Cash-to-cash is their
combination. Working capital is attributed per echelon (supplier stock, inbound in transit, DC stock,
WIP, finished goods, outbound in transit, receivables) so a disruption reports where cash is locked as
well as what service did. Every disruption scenario's report carries a cash impact line next to its
service impact line, which is the language the source says CFOs fund twins in.

### 5.9 Insurance and risk transfer (E38)

Every loss the twin generates is recognized in the ledger when it happens, through
`risk.loss_recognised`, whether or not it is ever claimed. Insurance recovery is a separate posting
on settlement. Retained loss is the difference, and it is the largest component of total cost of
risk in most periods, so recognizing the gross loss is what lets `tcor_reconciles_to_gl` hold at
all.

Cargo claims trigger from in-transit telemetry: a shock event above the policy's threshold or a
temperature excursion beyond the cold-chain limit, confirmed by a damage-coded disposition on
receipt. The claim runs a lifecycle with drawn durations per stage.

The payout applies the sublimit, the deductible, the coinsurance, and the limit in that order.
`SublimitResolver` maps the loss to at most one sublimit key by the ordered rule set in
`insurance.sublimit_rules`, first match wins, and a loss matching no rule takes the policy limit.
The shipped `temperature_excursion` sublimit matches losses whose trigger is
`transport.temperature_excursion`, which is the class the cold-chain scenario produces. The key and
the resolved `applicable_limit` go on the claim record and on `risk.claim_settled`, alongside
`binding_constraint`, which names whether the deductible, the coinsurance, the sublimit, or the
policy limit determined the payout. Without the resolver the sublimit shipped in config would change
nothing, which is worse than not shipping it; INS-004 fires when a payout is bound by a sublimit
rather than by the policy limit, because that is a coverage gap a risk manager needs to see.

Business interruption claims trigger from disruption scenarios. The downtime window comes from
`chaos.scenario_started` and `chaos.scenario_ended` or from an incident's mitigation timestamps.
Downtime beyond the waiting period is indemnified up to the indemnity period, valued at
`rate_per_hour` from `fin.gross_profit_rate` through `GrossProfitRatePort` rather than at a guessed
rate, which is why the claim and the P&L cannot disagree about what an hour of downtime was worth.

Premiums are experience-rated. The modifier is a function of the twin's own loss ratio over the rating
period and, for workers' compensation, of TRIR from the ergonomics layer. That closes a loop the
source cares about: a safety program that reduces TRIR reduces premium, so safety investments and
throughput investments argue in the same currency.

The risk transfer what-if compares options over a common seeded loss corpus: raise the deductible,
buy a risk-control capex such as a sprinkler upgrade, buy a higher limit, or self-insure a layer.
Each option is scored on total cost of risk across replications, reported as a distribution with the
significance test attached rather than a single number, because the difference between two risk
options is exactly the kind of comparison a single run cannot settle.

### 5.10 Agent tools contributed

Every tool below is schema-constrained with Pydantic input and output models (E26d), executes a query
against the historian rather than computing in tokens (E26a), resolves every metric through the
governed semantic layer (E26b), and is gated by an RBAC permission (6a15). Each ships at least three
eval questions with ground-truth answers computed from the simulation (E27). Each declares an
autonomy tier in `tools/manifest.yaml`: L1 for a read tool, L2 for a tool that changes state or
consumes a simulation budget, which needs a recorded human approval before it executes. No tool in
this section is L3.

Every tool that returns a statistical verdict takes `replications` and `base_seed`, never a single
seed. A verdict from one run is not a verdict, and a tool signature that accepts one seed while
promising a hypothesis test is a contract that cannot be met. The arms of every paired comparison
share substreams under the common random numbers rule in section 5.0, which is what makes 20
replications enough.

| Tool                                | Input                                                          | Output                                                                                                      | Permission                    | Tier |
|-------------------------------------|----------------------------------------------------------------|-------------------------------------------------------------------------------------------------------------|-------------------------------|------|
| `get_order_status`                  | `order_id`                                                     | status, promise, allocation, shipment, perfect order components                                             | `orders:read`                 | L1   |
| `get_impacted_customers`            | window, optional failure event ids                             | ranked customers with failures, CLV at risk, `clv_margin_source`, recommended contact order                 | `orders:read`, `finance:read` | L1   |
| `get_service_queue_state`           | none                                                           | queue depth, ASA, service level, occupancy, FCR rate, top blocking data                                     | `service:read`                | L1   |
| `run_allocation_whatif`             | policies, window, base seed, replications                      | fill by segment, Jain fairness index, backorder aging, paired verdict with effect size and interval         | `twin:whatif`                 | L2   |
| `get_spend_analysis`                | category, period                                               | Pareto by supplier and category, maverick leakage, contract coverage                                        | `procurement:read`            | L1   |
| `run_sourcing_whatif`               | category, supplier set, constraints, scenario id, replications | award, savings from tiers, tier-1 concentration, award gap report, resilience cost, recommendation          | `twin:whatif`                 | L2   |
| `get_supplier_scorecard_buyer_view` | supplier id, period                                            | OTIF against requested and confirmed dates, PPV, defect PPM, PO cycle time                                  | `procurement:read`            | L1   |
| `get_spot_buy_options`              | shortage event id                                              | spot, wait, and expedite options priced on one basis, net benefit, recommendation                           | `procurement:read`            | L1   |
| `run_landed_cost_scenario`          | sku or category, scenario id                                   | landed cost by origin, re-ranked sourcing table, MEIO delta or `unavailable`                                | `trade:read`, `twin:whatif`   | L2   |
| `get_workforce_state`               | date                                                           | headcount, coverage, eligibility gaps, overtime, engagement indicators, attrition hazard concentration      | `hr:read`                     | L1   |
| `run_labor_whatif`                  | strategies, horizon, base seed, replications                   | total cost, error rate, attrition risk, service level, paired verdict per strategy pair                     | `twin:whatif`                 | L2   |
| `get_slo_status`                    | service                                                        | SLI, target, budget remaining, burn rate, derived thresholds, gating state                                  | `itops:read`                  | L1   |
| `get_patch_options`                 | vuln id                                                        | candidate windows with production cost, expected loss, CVaR, objective, recommendation                      | `sec:read`, `twin:whatif`     | L2   |
| `get_correlated_alerts`             | window, zone set                                               | correlated alerts with contributing findings and distinct zones                                             | `sec:read`                    | L1   |
| `run_restore_drill`                 | ci id                                                          | measured RPO, RTO, data loss events, target met                                                             | `sec:drill`                   | L2   |
| `get_sop_packet`                    | cycle id                                                       | gaps, options, priced impacts, supply review mode, recommendation, confidence                               | `sop:read`                    | L1   |
| `run_promo_whatif`                  | promo definition, base seed, replications                      | lift, cannibalisation, pull-forward, overtime and expedite cost, margin after all of it, alternative timing | `twin:whatif`                 | L2   |
| `get_variance_decomposition`        | period, metric                                                 | ranked variance components with causal class and drill-down event ids                                       | `finance:read`                | L1   |
| `run_capex_appraisal`               | whatif id, discount rate                                       | NPV, IRR, payback, authority tier required                                                                  | `finance:read`                | L1   |
| `get_cash_position`                 | horizon weeks                                                  | inflows, outflows, closing balances, cash-to-cash, working capital by echelon                               | `finance:read`                | L1   |
| `get_tcor`                          | period                                                         | premiums, retained losses, risk control spend, total                                                        | `risk:read`                   | L1   |
| `run_risk_transfer_whatif`          | options, base seed, replications                               | TCOR distribution per option with paired significance verdict                                               | `twin:whatif`                 | L2   |

The two headline questions from the source map directly. "Which customers were hurt by yesterday's
dock failure, what does it cost us if the top two churn, and in what order do we call them?" is
`get_impacted_customers` over the failure window, ranked by CLV at risk with the recommended contact
order derived from hazard times value, and with `clv_margin_source` stating whether the margin came
from the ABC model or the baseline fallback. "Gross margin dropped 1.8 points this month: decompose
it into price, mix, freight, scrap, labor, and tariff, rank by contribution, and tell me which are
common cause versus assignable" is `get_variance_decomposition`, which returns the ranked components
each already carrying its `causal_class` from the control chart gate.

## 6. Configuration

All configuration validates against a published JSON Schema at load with line-numbered,
suggestion-bearing errors (C5), and `just validate` checks every file without running anything.
`facility.yaml` carries the operation-shaped keys. Reference data that would bloat it lives in
sibling catalog files named in `facility.yaml` under a `catalogs:` block, which keeps A2's
bring-your-own-facility promise workable: a reader edits one file to model their building and points
at catalogs for the rest.

```yaml
catalogs:
  chart_of_accounts: config/finance/chart_of_accounts.yaml
  posting_rules: config/finance/posting_rules.yaml
  standard_costs: config/finance/standard_costs.yaml
  abc_model: config/finance/abc_model.yaml
  authority_matrix: config/governance/authority_matrix.yaml
  controls_library: config/governance/controls_library.yaml
  sod_rules: config/governance/sod_rules.yaml
  tariff_schedule: config/trade/tariff_schedule.yaml
  trade_scenarios: config/trade/scenarios.yaml
  classifications: config/trade/classifications.yaml
  insurance_policies: config/insurance/policies.yaml
  rating_tables: config/insurance/rating_tables.yaml
  detections: config/itops/detections/ # Storage prefix, enumerated in key order
  zones: config/itops/zones.yaml
  service_catalog: config/itops/service_catalog.yaml
```

### 6.1 `orders`

```yaml
orders:
  segments: # map[str, SegmentSpec], at least one
    contract:
      allocation_tier: 1 # int 1..5
      promise_lead_days: 2 # int >= 0
      on_time_window_hours: 24 # int > 0
      fill_rate_commitment: 0.98 # float 0..1
      penalty_per_late_order: { amount_minor: 5000, currency: USD }
      contact_sensitivity: 0.6 # float 0..2, multiplier on contact probability
      patience_seconds: { dist: lognormal, mu: 5.6, sigma: 0.5 }
    spot: { allocation_tier: 3, promise_lead_days: 5, ... }
    marketplace: { allocation_tier: 4, promise_lead_days: 3, ... }
  allocation:
    policy: hybrid # enum fair_share | priority | hybrid
    horizon_days: 3 # int 1..30
    run_cadence_hours: 4 # int > 0
    honor_commitment_first: true # bool, hybrid only
    tie_break: [order_id] # ordered list of sort keys, last must be a unique key
  backorder:
    fill_policy: priority_then_age # enum fifo_by_created_at | priority_then_age
    max_age_days: 7 # int > 0, drives ORD-002
    auto_cancel_after_days: 30 # int > max_age_days
  changes:
    cost_table: # map[change_type, map[stage, ChangeCost]]
      qty_decrease:
        {
          PROMISED: { amount_minor: 0 },
          ALLOCATED: { amount_minor: 250 },
          PICKING: { amount_minor: 1200 },
          PACKED: { amount_minor: 2600 },
        }
      cancel: { ... }
    accept_after_stage: PACKED # enum, changes past this become returns
  substitution:
    rules_file: config/orders/substitutions.yaml
    require_approval_default: true
  promise:
    sources: [on_hand, in_transit, scheduled_receipt, ctp, default_lead_time]
    default_lead_days: 7
    on_time_basis: delivery # enum ship | delivery
  perfect_order:
    components: [complete, on_time, damage_free, correctly_invoiced]
    complete_basis: first_shipment # enum first_shipment | any_shipment
  service:
    queues:
      general: { reason_codes: [wismo, late_delivery, other], skill: general }
      claims: { reason_codes: [damage, short_ship, wrong_item], skill: claims }
      billing: { reason_codes: [invoice_dispute], skill: billing }
    service_level_seconds: 60 # int > 0
    tool_visibility: order_detail # enum none | order_header | order_detail | twin_grounded
    reason_visibility_required: # map[reason_code, visibility level]
      wismo: order_detail
      short_ship: order_detail
      damage: twin_grounded
      invoice_dispute: order_detail
    handle_seconds: # map[reason_code, Distribution]
      wismo: { dist: lognormal, mu: 5.0, sigma: 0.4 }
      # dist is one of lognormal | exponential | gamma | deterministic
    proficiency_scaling: true # bool, scales handle time by the learning curve
    queue_discipline: fifo # enum fifo | priority_by_segment
    validation_profile: # the configuration the Erlang gates instantiate
      enabled: false # bool, true only in the validation-gate job
      arrival: { dist: poisson, rate_per_hour: 120 }
      handle_seconds: { dist: exponential, mean: 300 }
      patience_seconds: none # null disables abandonment, for the Erlang C gate
      proficiency_scaling: false
      agents: 12 # c, the number of servers
    contact_generation:
      base_rate: # map[reason_code, float 0..1]
        late_delivery: 0.35
        short_ship: 0.55
        damage: 0.70
      escalation_gain: 0.25 # float >= 0
      delay: # map[reason_code, Distribution]
        late_delivery: { dist: lognormal, mu: 10.5, sigma: 0.8 }
  customer_health:
    satisfaction_start: 0.85 # float 0..1
    impact: # map[reason_code, float > 0]
      late_delivery: 0.05
      damage: 0.12
    recovery_rate_per_week: 0.02 # float >= 0
    churn:
      { intercept: -6.0, satisfaction_weight: 4.0, failures_90d_weight: 0.4 }
    clv_horizon_periods: 36 # int > 0
    clv_discount_rate_annual: 0.10 # float 0..1
    churn_alert_value: { amount_minor: 5000000, currency: USD }
```

`tie_break` is an ordered list of sort keys, not a scalar enum, because the total order a
deterministic allocation needs is usually a compound one. Members are drawn from `order_id`,
`promise_date`, `allocation_tier`, `order_value`, and `captured_at`, and the last member must be a
key the validator knows to be unique per demand. Today that is `order_id` alone. Writing
`[promise_date]` is rejected with the suggestion `[promise_date, order_id]`, and that suggestion is
now representable in the schema, which it was not while the key was a scalar enum whose members did
not include the compound form the error message told the user to write.

Validation rules: segment `allocation_tier` values are unique or explicitly marked shared; a
`contract` segment needs a non-null `fill_rate_commitment`; every reason code appearing in
`contact_generation.base_rate` appears in exactly one queue; `tie_break` is non-empty, contains no
duplicates, and ends in a unique key, and a list that does not is rejected with the corrected list
quoted; `max_age_days < auto_cancel_after_days`; the change cost table is non-decreasing across the
stage sequence, and a decreasing entry is rejected at load with the offending pair quoted.

`service.validation_profile` exists because the Erlang gates need a configuration the shipped
operating profile does not offer, and a gate that cannot be instantiated from the published schema
is not a gate. Erlang C assumes Poisson arrivals, exponential handle times, `c` servers, and no
abandonment; Erlang A adds exponential patience. The shipped profile uses lognormal handle times,
mandatory per-segment patience, and proficiency scaling from the workforce learning curve, all three
of which break the assumption. The profile names `exponential` among the permitted handle
distributions, permits `patience_seconds: none`, and turns proficiency scaling off. It is enabled
only in the validation-gate job, config validation rejects `enabled: true` in any shipped scenario
profile, and `test_validation_profile_is_not_shipped_enabled` asserts that. The gate then checks the
queueing implementation against the analytic result on the analytic model's own terms, which is what
validation against a published formula means.

### 6.2 `procurement`

```yaml
procurement:
  match_tolerances:
    price_pct: 0.02 # float 0..0.25
    qty_pct: 0.05 # float 0..0.25
    freight_abs: { amount_minor: 2500, currency: USD }
    tax_abs: { amount_minor: 500, currency: USD }
    over_receipt_pct: 0.05
    duplicate_window_days: 30 # int > 0
  approval:
    matrix_ref: authority_matrix # key into catalogs
    delay_hours_by_role:
      { buyer: { dist: lognormal, mu: 1.6, sigma: 0.6 }, director: { ... } }
    requester_may_approve: false # bool, must be false or CI SOD test fails
  payment:
    default_terms_id: net30
    hurdle_rate_annual: 0.08 # float 0..1, drives discount capture
    run_cadence_days: 7
  sourcing:
    provenance: synthetic # mandatory; load fails without it
    exact_award_max_suppliers: 6 # int > 0, above this the gap report says exact_unavailable
    default_criteria: # weights must sum to 1.0 +/- 1e-9
      - {
          name: unit_price,
          weight: 0.45,
          direction: lower_better,
          normalization: ratio_to_best,
          source: bid,
        }
      - {
          name: lead_time,
          weight: 0.20,
          direction: lower_better,
          normalization: min_max,
          source: bid,
        }
      - {
          name: quality_ppm,
          weight: 0.20,
          direction: lower_better,
          normalization: min_max,
          source: scorecard,
        }
      - {
          name: otif,
          weight: 0.15,
          direction: higher_better,
          normalization: min_max,
          source: scorecard,
        }
    award_constraints:
      min_suppliers: 2
      max_share_per_supplier: 0.6 # float 0..1
      max_tier2_concentration: 0.5 # float 0..1, requires E19 when enforced
  spend:
    taxonomy_file: config/procurement/categories.yaml
    maverick_alert_pct: 0.05 # float 0..1
  savings:
    baseline_method: prior_price # enum prior_price | market_index | budget | announced_increase
    avoidance_requires_announcement: true # bool
  tactics:
    forward_buy:
      carrying_cost_annual_pct: 0.22
      obsolescence_source: eando_model # enum eando_model | fixed_pct
      max_forward_months: 6
    expedite:
      stockout_cost_source: order_sla # enum order_sla | fixed_per_unit
      max_premium_multiple: 3.0
    spot_buy:
      enabled: true
      trigger_events: [supplier.commit_date_slipped, orders.line_backordered]
      spot_premium_default_pct: 0.18 # float >= 0, used by the null SpotPricePort
      spot_quality_ppm_uplift: 400 # int >= 0, defect ppm above the contract supplier
      max_spot_share_of_category_spend: 0.15 # float 0..1, above this raises PRC-007
      off_contract_penalty_source: contract # enum contract | none
      provenance: synthetic
```

Validation rules: sourcing criterion weights sum to 1.0; `max_share_per_supplier * min_suppliers >= 1.0`
or the constraint set is infeasible and load fails with that arithmetic quoted;
`requester_may_approve` is false; `max_tier2_concentration` may be set only when the n-tier map is
available, otherwise load warns and the constraint is reported as unenforced rather than ignored in
silence; every `spot_buy.trigger_events` entry names an event with a producer in some section.

The `sourcing` and `tactics.spot_buy` blocks carry a mandatory `provenance: synthetic` key and load
fails without it. The scorecard weights are the block open question 11 names as the IP hygiene risk,
and the spot-buy premium and quality uplift are equally invented, so both sit under the same
config-level enforcement as the attrition coefficients and the rating tables rather than relying on
a reviewer noticing.

### 6.3 `trade` (E14)

```yaml
trade:
  destination_country: US # str, ISO 3166-1 alpha-2, synthetic scenarios only
  dutiable_value_basis: transaction_value # enum transaction_value | transaction_value_plus_freight_insurance
  duty_capitalisation: inventory # enum inventory | expense
  broker_fee_per_entry: { amount_minor: 12500, currency: USD }
  schedule_ref: tariff_schedule
  active_scenarios: [] # list[scenario_id], composed in order
  de_minimis:
    threshold: { amount_minor: 80000, currency: USD }
    applies_to_channels: [marketplace, ecommerce]
  ftz:
    enabled: false
    inverted_tariff_allowed: false
  drawback:
    enabled: true
    refund_rate: 0.99 # float 0..1
    filing_window_days: 1095 # int > 0
    processing_days: { dist: lognormal, mu: 5.2, sigma: 0.3 } # seed root/trade/drawback
    provenance: synthetic
```

`drawback.processing_days` is the one stochastic quantity in the trade package, so the package
declares the `root/trade/drawback` seed namespace in section 6.9 and takes an `Rng`. Declaring the
engine seedless while shipping a lognormal draw that reaches `trade.drawback_received.days_to_refund`
would have broken C1's hash check on the first run with drawback enabled.

`tariff_schedule.yaml` rows:

```yaml
rows:
  - {
      hs_code: "840790",
      origin: DE,
      destination: US,
      effective_from: 2026-01-01,
      kind: ad_valorem,
      ad_valorem_pct: 0.027,
    }
  - {
      hs_code: "392690",
      origin: CN,
      destination: US,
      effective_from: 2026-01-01,
      kind: compound,
      ad_valorem_pct: 0.053,
      specific_per_unit: { amount_minor: 15, currency: USD },
      uom: kg,
    }
```

`scenarios.yaml`:

```yaml
scenarios:
  - scenario_id: rate_shock_plastics
    name: "Plastics chapter rate shock"
    effective_from: 2026-04-01
    deltas:
      - { target: { hs_chapter: "39", origin: CN }, additive_pct: 0.15 }
  - scenario_id: retaliation_mirror
    retaliation_of: rate_shock_plastics
    mirror_origin: US
```

Validation rules: no two rows share `(hs_code, origin, destination)` with overlapping effectivity;
`ad_valorem_pct` in `[0, 5.0]` with anything above 1.0 warning that it is above 100 percent;
`specific_per_unit` requires a `uom`; a `retaliation_of` scenario must name an existing scenario; a
scenario listed in `active_scenarios` must exist; header comment in the shipped file states every
rate is synthetic and not a reproduction of any real tariff schedule.

### 6.4 `workforce`

```yaml
workforce:
  roles:
    picker:
      base_wage: {amount_minor: 2100, currency: USD}   # per hour
      burden_pct: 0.28                    # float 0..1
      required_certifications: []
      time_to_fill_days: {dist: lognormal, mu: 3.0, sigma: 0.4}
      recruiting_cost: {amount_minor: 120000, currency: USD}
      headcount_driver: forecast_lines_per_day
    forklift_operator:
      required_certifications: [forklift]
      ...
  certifications:
    forklift: {training_hours: 8, trainer_role: supervisor, validity_days: 1095, stations_unlocked: [receiving, putaway]}
    hazmat: {training_hours: 16, validity_days: 730, stations_unlocked: [hazmat_staging]}
  learning_curve:
    model: wright                         # enum wright  (only implemented model; see open questions)
    learning_rate: 0.85                   # float 0.5..1.0
    initial_productivity_ratio: 0.55      # float 0..1
    plateau_units: 4000                   # int > 0
    error_learning_rate: 0.80
    initial_error_multiplier: 2.5         # float >= 1
    error_floor_multiplier: 1.0
  attrition:
    evaluation_cadence: weekly
    coefficients:                         # illustrative synthetic values, documented as such
      intercept: -5.2
      overtime_hours_rolling_4w: 0.035
      strain_index: 1.10
      understaffing_ratio_rolling_4w: 0.90
      schedule_instability: 0.75
      weekend_shifts_rolling_8w: 0.06
    tenure_spline_knots: [30, 90, 365, 1095]
    tenure_spline_values: [0.9, 0.3, -0.2, -0.5]
    regret_threshold_percentile: 0.4      # float 0..1
  absence:
    generator: {base_rate: 0.035, strain_weight: 0.6, consecutive_days_weight: 0.05, seasonal_amplitude: 0.4}
    predictor: {model: logistic, features: [strain_index, consecutive_days, weekday, weather_index, tenure_days]}
    publish_horizon_days: 14
  overtime:
    daily_threshold_hours: 8
    weekly_threshold_hours: 40
    premium_multiplier: 1.5
    double_time_after_hours: 12
    alert_hours_rolling_4w: 40            # drives HR-002
    alert_consecutive_weeks: 3
  cross_training:
    trainer_productivity_loss: 0.3        # float 0..1
    trainee_productivity_during: 0.2
  peak_strategies:
    temp: {productivity_ratio: 0.7, error_multiplier: 1.8, agency_markup: 0.35, attrition_cost: 0}
    overtime: {strain_gain: 0.15}
    hiring_pulse: {layoff_fraction: 0.5, severance_weeks: 2, morale_penalty: 0.05}
```

Validation rules: every certification named in a role exists; every station named in
`stations_unlocked` exists in `facility.yaml`; `0.5 <= learning_rate <= 1.0` with a suggestion that
values above 1.0 mean workers get slower; `tenure_spline_knots` and `tenure_spline_values` have equal
length and knots are strictly increasing; the attrition coefficient block carries a mandatory
`provenance: synthetic` key and load fails without it, which is the config-level enforcement of the
IP hygiene rule.

### 6.5 `itops`

```yaml
itops:
  service_catalog_ref: service_catalog
  zones_ref: zones
  detections_dir: config/itops/detections/
  slos:
    - {
        slo_id: broker_availability,
        ci_id: broker,
        sli: availability,
        target: 0.999,
        window_days: 28,
      }
    - {
        slo_id: twin_api_latency,
        ci_id: twin_service,
        sli: latency_p95,
        target: 0.99,
        threshold_ms: 400,
        window_days: 28,
      }
  burn_rate_alerts: # multi-window multi-burn-rate; thresholds are derived, never written
    - {
        name: fast,
        long_window_hours: 1,
        short_window_minutes: 5,
        budget_fraction: 0.02,
        severity: page,
      }
    - {
        name: slow,
        long_window_hours: 6,
        short_window_minutes: 30,
        budget_fraction: 0.05,
        severity: page,
      }
    - {
        name: trend,
        long_window_hours: 72,
        short_window_minutes: 360,
        budget_fraction: 0.10,
        severity: ticket,
      }
  change:
    freeze_windows:
      [
        { dow: FRI, start_hour: 15, end_hour: 24 },
        { dow: SAT, start_hour: 0, end_hour: 24 },
      ]
    base_failure_probability: { standard: 0.005, normal: 0.03, emergency: 0.12 }
    window_multipliers: { FRI_15_24: 3.0, weekend: 1.5, default: 1.0 }
    no_rollback_penalty: 2.0
    error_budget_gate: true # when a budget is exhausted, only emergency changes approve
    approval_matrix_ref: authority_matrix
  vulnerability:
    feed: synthetic # enum synthetic  (only value; identifiers are TWF-CVE-*)
    arrival_rate_per_week: 2.5
    severity_mix: { critical: 0.08, high: 0.25, medium: 0.45, low: 0.22 }
    exploit_probability_daily:
      { critical: 0.010, high: 0.004, medium: 0.001, low: 0.0002 }
    known_exploited_fraction: 0.05 # prevalence: share of published vulns carrying the flag
    known_exploited_multiplier: 8.0 # uplift: multiplier on the daily hazard when flagged
    patch_sla_days_by_zone: { ot: 90, dmz: 30, it: 14 }
    patch_horizon_days: 14
    risk_preference_alpha: 0.5 # float 0..1; 0 is risk neutral, 1 is pure CVaR
    cvar_beta: 0.95 # float 0..1, tail probability for the CVaR term
    cvar_samples: 2000 # int > 0, draws per candidate window
    provenance: synthetic
  breach_impact:
    downtime_hours: { dist: lognormal, mu: 3.0, sigma: 0.8 } # seed root/itops/breach_impact
    recovery_cost: { amount_minor: 5000000, currency: USD }
    regulatory_cost: { amount_minor: 0, currency: USD }
    provenance: synthetic
  telemetry:
    head_sample_rate: 0.05 # float 0..1
    tail_keep_error_traces: true
    log_templates_file: config/itops/log_templates.yaml
  correlation:
    rules_dir: config/itops/correlations/
    default_window_seconds: 900 # int > 0
    default_min_inputs: 3 # int >= 2
    default_min_distinct_zones: 2 # int >= 1
    max_alerts_per_window: 20 # int > 0, the flood guard
  chaos:
    scenarios_file: config/itops/chaos_scenarios.yaml
    enabled_kinds: [ci_failure, restore_drill]
  backup:
    schedules:
      - {
          ci_id: historian,
          cadence_hours: 6,
          retention_days: 30,
          target_rpo_minutes: 360,
          target_rto_minutes: 120,
        }
      - {
          ci_id: mes_analog,
          cadence_hours: 24,
          retention_days: 14,
          target_rpo_minutes: 1440,
          target_rto_minutes: 240,
        }
    drill_cadence_days: 90
    verify_every_backup: true
    provenance: synthetic
  rbac:
    default: deny # enum deny  (only value)
    roles_file: config/itops/roles.yaml
    grants_file: config/itops/grants.yaml
```

`zones.yaml`:

```yaml
zones:
  - {
      zone_id: ot,
      purdue_levels: [0, 1, 2],
      security_level_target: 3,
      members: [devices, broker],
    }
  - {
      zone_id: dmz,
      purdue_levels: [3],
      security_level_target: 2,
      members: [historian, twin_sync],
    }
  - {
      zone_id: it,
      purdue_levels: [4],
      security_level_target: 2,
      members: [analytics, agent, dashboard],
    }
conduits:
  - {
      conduit_id: ot_to_dmz,
      src_zone: ot,
      dst_zone: dmz,
      allowed_protocols: [mqtt],
      allowed_ports: [8883],
      direction: unidirectional,
    }
  - {
      conduit_id: dmz_to_it,
      src_zone: dmz,
      dst_zone: it,
      allowed_protocols: [https, postgres],
      allowed_ports: [443, 5432],
      direction: bidirectional,
    }
```

Validation rules: every CI belongs to exactly one zone; every SLO references an existing CI and SLI;
burn-rate alert windows satisfy `short_window < long_window`; `budget_fraction` lies in `(0, 1)` and
the derived burn rate is recomputed at load from `window_days`, so a threshold literal cannot appear
in a config file at all; `patch_sla_days_by_zone` covers every declared zone; a conduit whose
`src_zone` equals its `dst_zone` is rejected; every correlation rule names inputs that exist as
finding codes or detection rule ids; the shipped grants file is checked against `sod_rules.yaml` at
load and a conflict fails validation rather than waiting for runtime, so a misconfigured demo cannot
ship an SOD violation in silence.

Three blocks in this file carry a mandatory `provenance: synthetic` key and load fails without it:
`vulnerability` (the `exploit_probability_daily` table and the known-exploited uplift are invented),
`breach_impact` (the downtime and recovery costs are invented), and `backup` (the RPO and RTO
targets are the resilience targets open question 11 names as the IP hygiene risk). The rule is the
same one the attrition coefficients and the insurance rating tables already carry, applied to every
block that would otherwise look like it came from a real deliverable.

### 6.6 `commercial`

```yaml
commercial:
  promotions:
    calendar_file: config/commercial/promo_calendar.yaml
    lift:
      max_lift_by_class: { A: 2.4, B: 1.8, C: 1.4 } # L_max per SKU class
      depth_response_k: 6.0 # float > 0
      noise: { dist: lognormal, mu: 0.0, sigma: 0.08 }
      provenance: synthetic # mandatory; load fails without it
    feature_frame:
      publish_to_forecaster: true # drives PromoFeaturePort
      horizon_periods: 26 # int > 0
      cut_off_offset_days: 0 # int >= 0, features never read past the cut-off
    pull_forward:
      default_fraction: 0.35 # float 0..1
      decay_periods: 4 # int >= 1
      decay_ratio: 0.5 # weights are geometric and normalized to sum to 1
    cannibalisation_file: config/commercial/cannibalisation.yaml
    serveability_check: true # drives CMR-001
  sales:
    stages: [qualify, discover, propose, negotiate, close]
    conversion:
      { qualify: 0.55, discover: 0.60, propose: 0.65, negotiate: 0.75 }
    dwell_days: { qualify: { dist: lognormal, mu: 1.8, sigma: 0.5 }, ... }
    reps:
      - { rep_id: r1, bias_multiplier: 1.18, mode: optimistic, variance: 0.10 }
      - { rep_id: r2, bias_multiplier: 0.92, mode: sandbagging, variance: 0.06 }
  quota:
    period: quarter # enum month | quarter
    pressure_exponent: 3.0 # k
    pressure_amplitude: 1.6 # q
    discount_escalation_pct: 0.04
  demand_shaping:
    enabled: true # publishes mkt.demand_multiplier_published
    sources: [promotion, quota_pressure, channel_mix, npi_launch]
    max_multiplier: 4.0 # float > 0, clamp so a stacked lever cannot break the queue model
    publish_cadence: period # enum period | daily
  channel_mix:
    start_shares: { wholesale: 0.62, ecommerce: 0.28, marketplace: 0.10 }
    drift_model: dirichlet # enum config_static | dirichlet
    drift_step: 0.015 # float >= 0; zero pins the shares to start_shares exactly
    concentration_alert_hhi: 0.55 # float 0..1
    provenance: synthetic
  npi:
    default_bass_p: 0.03 # innovation coefficient
    default_bass_q: 0.38 # imitation coefficient
    cold_start_blend_periods: 8
  sop:
    calendar:
      product_review_day: 3 # business day of month, int 1..20
      demand_review_day: 6
      supply_review_day: 9
      reconciliation_day: 12
      executive_day: 15
    horizon_periods: 18
    supply_review_mode: analytic # enum analytic | surrogate | full_simulation
    bill_of_resource_file: config/commercial/bill_of_resource.yaml
    fva_ladder: [naive, statistical, sales_override, consensus]
    accuracy_metric: wape # enum mape | wape | mase
    one_number_tolerance_pct: 0.005 # drives CMR-005
    decision_register_ref: governance.decision_register
```

Validation rules: cannibalisation matrix rows have a zero diagonal and column sums no greater than
1.0, and a violating column is quoted with its sum; S&OP calendar days are strictly increasing;
`fva_ladder` starts with `naive`; `pull_forward.default_fraction` in `[0, 1]`; every promoted SKU in
the calendar exists in the SKU catalog and has a declared class in `max_lift_by_class`;
`channel_mix.start_shares` sums to 1.0 within 1e-12 and names only declared channels;
`supply_review_mode: surrogate` is rejected unless E28 is installed, with the missing package named.

Three blocks carry a mandatory `provenance: synthetic` key and load fails without it:
`promotions.lift` (the lift ceilings and depth response are invented), `channel_mix` (the starting
shares and drift step are invented), and `bill_of_resource.yaml` (the resource coefficients the
rough-cut capacity check multiplies volume by).

### 6.7 `finance`

```yaml
finance:
  functional_currency: USD
  period_calendar: monthly # enum monthly | four_four_five
  fiscal_year_start_month: 1
  chart_of_accounts_ref: chart_of_accounts
  posting_rules_ref: posting_rules
  inventory:
    valuation_method: weighted_average # enum weighted_average | fifo
    valuation_classes: [raw, wip, finished, returns]
    eando:
      coverage_horizon_periods: 12
      aging_buckets_days: [90, 180, 365]
      reserve_rate_by_bucket: [0.15, 0.40, 0.85]
    cycle_count:
      method: cycle # enum cycle | wall_to_wall
      frequency_days_by_abc: { A: 30, B: 90, C: 180 }
      tolerance_units: 0
      rfid_confirmation: true # the A/B switch for the record accuracy study
  standard_costing:
    revision_source: bom # enum bom | recipe
    overhead_base: labor_hours # enum labor_hours | machine_hours
    revalue_on_standard_change: true
    variance_common_cause_gate: true # route every variance through the LSS chart first
  abc:
    model_ref: abc_model
    rate_refresh: monthly
  fpa:
    budget_source: sop_consensus # enum sop_consensus | manual
    reforecast_cadence: monthly
    bridge_components: [volume, price, mix, rate, efficiency, spend, residual]
  capex:
    discount_rate_annual: 0.10 # float 0..1
    authority_matrix_ref: authority_matrix
    post_audit_lag_periods: 6 # int > 0
    irr_solver:
      bracket: [-0.99, 10.0] # lower bound > -1.0
      max_iterations: 200 # int > 0, bisection steps before NoConvergence
      tolerance_rel: 1.0e-12 # relative width of the final bracket
      on_no_sign_change: raise # enum raise | return_none
      on_multiple_roots: enumerate # enum enumerate | raise
  close:
    checklist_file: config/finance/close_checklist.yaml
    target_close_days: 5
    accruals: [gr_ni, unbilled_revenue, payroll, freight]
    reconciliations: [ap, ar, inventory, payroll, cash]
  controls:
    library_ref: controls_library
    sod_rules_ref: sod_rules
    test_cadence_default: quarterly
  working_capital: # E22
    echelons:
      [
        supplier_stock,
        inbound_in_transit,
        dc_stock,
        wip,
        finished_goods,
        outbound_in_transit,
        accounts_receivable,
      ]
    carrying_cost_annual_pct: 0.12
    cash_forecast_horizon_weeks: 13
  terms:
    ap:
      {
        net30: { net_days: 30 },
        2_10_net30: { net_days: 30, discount_pct: 0.02, discount_days: 10 },
      }
    ar: { net45: { net_days: 45 }, net15: { net_days: 15 } }
```

Validation rules: every account referenced by a posting rule exists and is postable; every posting
rule template balances symbolically (the debit expressions and the credit expressions are provably
equal, checked by a symbolic balance test at load, not only at runtime); `reserve_rate_by_bucket`
has the same length as `aging_buckets_days` plus one and is non-decreasing; `irr_solver.bracket`
lower bound is greater than -1.0 and the upper bound exceeds it; every echelon named has a valuation
source; `target_close_days` is positive; a `four_four_five` calendar needs a period boundary file.

The internal rate of return is a root of a polynomial, so its solver has a stated contract rather
than a bracket alone. Bisection runs at most `max_iterations` steps and stops when the bracket width
falls below `tolerance_rel` relative to the midpoint. Three outcomes are named rather than left to
the implementation.

| Situation                                           | Behavior                                                                                             |
|-----------------------------------------------------|------------------------------------------------------------------------------------------------------|
| No sign change of NPV across the bracket            | Raise `NoIrrInBracket` naming the bracket and both endpoint NPVs; the true rate may lie outside it   |
| Sign change present, bisection converges            | Return the root; `capex.appraised` carries the final bracket width so the precision is on the record |
| Sign change present, `max_iterations` reached       | Raise `IrrDidNotConverge` with the final bracket, never a midpoint presented as an answer            |
| More than one sign change in the cash flow sequence | Enumerate the roots in the bracket and return them all with a `multiple_irr` flag                    |

The last row is a correction. Descartes' rule of signs bounds the number of positive roots by the
number of sign changes; it does not imply there is more than one. An ordinary project with a
terminal decommissioning cost has two sign changes and usually one root, and raising `AmbiguousIrr`
on the sign-change count alone would reject it. The engine enumerates instead, and only reports
ambiguity when it finds more than one root. Where more than one root exists, the report says so and
directs the reader to NPV, because a project with several internal rates of return does not have an
internal rate of return worth quoting.

### 6.8 `insurance` (E38)

```yaml
insurance:
  policies:
    - policy_id: cargo_2026
      coverage: cargo
      limit: { amount_minor: 50000000, currency: USD }
      deductible: { amount_minor: 250000, currency: USD }
      coinsurance_pct: 1.0
      sublimits:
        { temperature_excursion: { amount_minor: 10000000, currency: USD } }
      exposure_base: shipped_value
      base_rate: 0.0012 # per unit of exposure base
    - policy_id: bi_2026
      coverage: business_interruption
      limit: { amount_minor: 200000000, currency: USD }
      waiting_period_hours: 48
      indemnity_period_days: 90
      exposure_base: annual_gross_profit
      base_rate: 0.0035
    - policy_id: wc_2026
      coverage: workers_compensation
      exposure_base: payroll
      base_rate: 0.021
  sublimit_rules: # ordered; first match wins, no match takes the policy limit
    - {
        key: temperature_excursion,
        when_trigger_event: transport.temperature_excursion,
      }
    - { key: temperature_excursion, when_peril_tag: cold_chain }
  claim_triggers:
    shock_g_threshold: 5.0
    temperature_excursion_minutes: 60
    require_damage_disposition: true
  claim_process:
    fnol_to_documented_days: { dist: lognormal, mu: 1.2, sigma: 0.5 }
    documented_to_adjusted_days: { dist: lognormal, mu: 2.0, sigma: 0.6 }
    adjusted_to_settled_days: { dist: lognormal, mu: 2.4, sigma: 0.7 }
    denial_probability: 0.06
  rating:
    experience_period_years: 3
    loss_ratio_weight: 0.6
    trir_weight: 0.4
    modifier_bounds: [0.7, 2.0]
  tcor:
    admin_cost_annual: { amount_minor: 4000000, currency: USD }
    risk_control_accounts: [6410, 6420]
```

Validation rules: every policy has an exposure base that resolves to a computable metric; the
deductible is less than the limit; every sublimit is at most the policy limit, and a larger one is
rejected with both values quoted; every `sublimit_rules` key names a sublimit declared on some
policy; `modifier_bounds` lower bound is positive and below the upper bound; `coinsurance_pct` in
`(0, 1]`; a workers' compensation policy needs the ergonomics layer enabled or load fails with the
reason named; the shipped rating tables and `claim_process` distributions carry
`provenance: synthetic` and load fails without it.

### 6.9 Seed namespaces

Declared in each package's `seeds.toml` so C1's splittable RNG can derive stable child streams.
Adding a namespace is additive and never reorders existing streams. The substream column names the
entity id a draw is subscripted by, following section A.2 of
`docs/design/variability-and-faults.md`. A stream with a substream is addressed, not consumed in
order, which is what makes the paired studies of section 5.0 comparable.

| Namespace                             | Used for                                                   | Substream key          |
|---------------------------------------|------------------------------------------------------------|------------------------|
| `root/orders/arrival`                 | order interarrival, composition, and channel draw          | period                 |
| `root/orders/service/contacts`        | contact occurrence, delay, and the WISMO hazard            | `caused_by_event_id`   |
| `root/orders/service/handle`          | handle time, patience, and the skill draw                  | `contact_id`           |
| `root/orders/substitution_response`   | substitution approval decision and delay                   | `line_id`              |
| `root/orders/churn`                   | churn hazard draws                                         | `customer_id`          |
| `root/orders/changes`                 | change request occurrence and type                         | `order_id`             |
| `root/procurement/approval_delay`     | approver response times                                    | `po_id`                |
| `root/procurement/rfx/bids`           | bid generation                                             | `bid_id`               |
| `root/procurement/invoice`            | invoice arrival, duplicates, and errors                    | `invoice_id`           |
| `root/procurement/spot_price`         | spot quote and spot supplier quality draw                  | `decision_id`          |
| `root/trade/drawback`                 | drawback refund processing days                            | `claim_id`             |
| `root/workforce/pipeline`             | hiring stage conversions and dwell                         | `hr_req_id`            |
| `root/workforce/absence`              | absence realization                                        | `worker_id`, date      |
| `root/workforce/attrition`            | quit draws                                                 | `worker_id`, week      |
| `root/itops/cve_feed`                 | vulnerability arrival and severity                         | week                   |
| `root/itops/change_outcome`           | change success or failure                                  | `chg_id`               |
| `root/itops/incident`                 | incident arrival from CI failure processes                 | `ci_id`                |
| `root/itops/breach_impact`            | breach downtime hours and the CVaR sample draws            | `vuln_id`              |
| `root/itops/trace_sampling`           | head and tail sampling decisions                           | `trace_id`             |
| `root/commercial/promo_noise`         | lift noise                                                 | `promo_id`, period     |
| `root/commercial/pipeline`            | opportunity progression                                    | `opp_id`               |
| `root/commercial/rep_forecast`        | forecast submission noise                                  | `rep_id`, period       |
| `root/commercial/channel_mix`         | Dirichlet drift of the channel share vector                | period                 |
| `root/commercial/npi_adoption`        | noise around the Bass adoption expectation                 | `sku`, period          |
| `root/finance/close_task_duration`    | close task durations                                       | `task_id`, `period_id` |
| `root/finance/count_error`            | physical count discrepancy                                 | location, `sku`        |
| `root/insurance/claim_process`        | claim stage durations and denial                           | `claim_id`             |
| `root/insurance/loss_severity`        | loss severity draws for the risk transfer study            | `loss_id`              |
| `provision/workforce/<id>/percentile` | worker performance percentile, drawn before the sim starts | `worker_id`            |

The trade package no longer declares a `none` namespace. It draws one quantity, drawback refund
timing, so it declares the stream that quantity comes from. A package that claims to need no seed
while shipping a lognormal draw is a determinism leak that C1's hash check finds on the second run,
and the manifest check in section 2.9 finds it at import.

### 6.10 Metric definitions contributed to the semantic layer (E26b)

Each package ships `metrics/<pkg>.metrics.yaml`. Every metric declares a name, a description, an
exact SQL expression over the historian tables, its dimensions, its unit, and the total ordering
section 3's query determinism rule requires. CI fails if any agent eval question references a metric
that is not defined here. CI also fails if any metric named in section 7.4's chart table or returned
by any tool in section 5.10 is not defined here, which is the check that catches the reverse drift.
The agent selects metrics rather than writing aggregations, which is what stops it computing fill
rate a second way.

| Package     | Metrics                                                                                                                                                                                                                                                                                                                                                                                                                                                          |
|-------------|------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| orders      | `perfect_order_rate`, `fill_rate`, `line_fill_rate`, `on_time_ship_rate`, `on_time_delivery_rate`, `promise_reliability`, `promise_reliability_by_source`, `order_cycle_time_hours`, `backorder_aging_days`, `wismo_rate`, `promise_breach_order_days`, `fairness_index`, `contacts_per_100_orders`, `first_contact_resolution_rate`, `average_speed_of_answer_seconds`, `service_level_pct`, `abandonment_rate`, `clv_at_risk`, `churn_rate`, `channel_mix_hhi` |
| procurement | `purchase_price_variance`, `contract_price_variance`, `market_index_price_variance`, `po_cycle_time_hours`, `supplier_otif_buyer_view`, `first_pass_match_rate`, `match_exception_aging_hours`, `maverick_spend_pct`, `contract_coverage_pct`, `discount_capture_rate`, `cost_savings`, `cost_avoidance`, `spend_by_category`, `spot_buy_share_of_category_spend`, `award_greedy_gap_pct`                                                                        |
| trade       | `landed_cost_per_unit`, `duty_rate_effective`, `duty_paid`, `drawback_recovered`, `tariff_exposure_by_origin`                                                                                                                                                                                                                                                                                                                                                    |
| workforce   | `turnover_rate`, `regretted_turnover_rate`, `time_to_fill_days`, `time_to_productivity_days`, `absenteeism_rate`, `labor_cost_per_unit`, `overtime_pct`, `overtime_pct_4w`, `schedule_stability_index`, `weekend_shift_rate_8w`, `strain_trend_slope`, `span_of_control`, `training_hours_per_improvement_point`, `station_coverage_ratio`                                                                                                                       |
| itops       | `slo_attainment`, `error_budget_remaining_pct`, `mttd_minutes`, `mttr_minutes`, `change_failure_rate`, `deployment_frequency`, `change_lead_time_hours`, `patch_latency_hours`, `cross_zone_anomaly_rate`, `correlated_alert_rate`, `request_error_rate`, `request_latency_p95_ms`, `log_error_rate_per_1k_requests`, `backup_restore_success_rate`, `measured_rpo_minutes`, `measured_rto_minutes`                                                              |
| commercial  | `promo_lift`, `incremental_units`, `cannibalisation_units`, `forecast_bias`, `forecast_value_added`, `rep_forecast_bias`, `quota_attainment`, `plan_adherence`, `decision_latency_days`, `one_number_variance`, `demand_multiplier_by_source`                                                                                                                                                                                                                    |
| finance     | `gross_margin_pct`, `gross_profit_rate_per_hour`, `cost_to_serve`, `contribution_after_cost_to_serve`, `inventory_record_accuracy`, `absolute_value_accuracy`, `shrink_value`, `eando_reserve`, `dio`, `dso`, `dpo`, `cash_to_cash_days`, `working_capital_by_echelon`, `close_cycle_days`, `capex_hit_rate`, `variance_by_kind`                                                                                                                                 |
| insurance   | `total_cost_of_risk`, `loss_ratio`, `claim_cycle_days`, `claim_recovery_ratio`, `experience_modifier`, `retained_loss`                                                                                                                                                                                                                                                                                                                                           |

Three procurement price variances are defined rather than one, because 6a13 asks for price variance
against contract and market, not only against standard cost.

| Metric                        | Baseline                | Expression                                                |
|-------------------------------|-------------------------|-----------------------------------------------------------|
| `purchase_price_variance`     | Standard cost           | `(paid_unit_price - standard_price) * qty_received`       |
| `contract_price_variance`     | `POLine.contract_price` | `(paid_unit_price - contract_price) * qty_received`       |
| `market_index_price_variance` | Published index quote   | `(paid_unit_price - index_price_at_order) * qty_received` |

Only the first posts to the GL, because only the first has an account (section 5.8). The other two
are analytic metrics with a control chart each and no ledger consequence, which is the same
distinction the savings ledger draws in section 3.2 and is the honest treatment of a baseline the
chart of accounts cannot witness. `contract_price_variance` is what finally reads
`POLine.contract_price`, which was declared and never differenced.

## 7. Testing

Five tiers per C4, each with a runtime budget enforced in CI.

| Tier                   | Budget for this section | Runs on                           | Contents                                                                               |
|------------------------|-------------------------|-----------------------------------|----------------------------------------------------------------------------------------|
| Unit                   | 90 s                    | Every push                        | Pure functions, state machines, formulas, posting rules                                |
| Property               | 180 s                   | Every push                        | Hypothesis invariants listed in 7.2                                                    |
| Validation gates, fast | 240 s                   | Every push                        | The gates in 7.3 marked fast: closed-form checks, fixture matrices, arithmetic         |
| Validation gates, full | 1800 s                  | Nightly, and on every release tag | Every gate in 7.3, including the replicated statistical ones                           |
| Seeded end to end      | 420 s                   | Every push                        | Scenario runs with golden-file comparison of statements, reports, and decision packets |

The split exists because the earlier single 240-second budget was not credible and a budget that
cannot be met is not a budget. Seven gates dominate the cost: VG-FIN-07 charts 100,000 points,
VG-HR-02 fits 200 logistic replications, VG-HR-04 and VG-HR-05 run batch-means queueing simulations
at three utilization levels across 20 seeds, VG-FIN-11 runs 20 long seeded runs, VG-PRC-04 runs a
17-point grid across 20 twin runs, and VG-INS-01 draws 5000 losses. Their measured budgets are
declared per gate in 7.3, and `test_validation_gate_budget_arithmetic` sums the declared budgets per
tier and fails when a sum exceeds the tier's ceiling (D-13). A gate that grows past its budget fails
as a defect rather than as a timeout.

Both validation tiers are required checks. The full tier is not optional, and no gate is dropped to
fit the fast tier; a gate too slow for a push job runs nightly and blocks the release tag.

### 7.1 Unit tests worth naming

- Order state machine: every legal transition accepted, every illegal transition raises
  `IllegalTransition` naming the pair. The rejected set is generated from the transition table rather
  than written down, so the count cannot drift: 15 statuses give 210 ordered pairs excluding
  self-transitions, 25 of which are legal, leaving 185 that must raise. Self-transitions are tested
  separately as 15 further rejections, for 200 rejected pairs in total. Both counts are computed in
  the test, and `test_transition_counts_match_the_table` asserts the arithmetic so an added status
  cannot silently shrink the matrix.
- Allocation determinism: the same demand and supply under the same policy produce the identical
  allocation list, including tie-break order, across 100 shuffles of the input list.
- Change cost table: monotone across stages for every change type.
- Three-way match: one fixture per violation class plus one per tolerance boundary (just inside and
  just outside), with the evaluation order asserted so the taxonomy is stable.
- Fairness index: Jain's index at full equality, at maximal inequality, with a zero-fill demand in
  the population, and at zero total supply, where the stated convention returns 1.0.
- Burn-rate derivation: `derive_burn_rates` reproduces 14.4, 6, and 1 at a 30-day window for budget
  fractions of 2, 5, and 10 percent over 1 hour, 6 hours, and 3 days, and returns 13.44, 5.6, and
  0.9333 at 28 days.
- Sublimit resolution: an ordered rule set maps a loss to at most one key, first match wins, and a
  loss matching no rule takes the policy limit.
- Closing entry: nominal accounts zero after the entry, retained earnings moves by net income
  exactly, and the entry's line order follows `account_id`.
- IRR solver: a bracket with no sign change raises, a non-converging bracket raises, and a cash flow
  with two sign changes and one root returns that root without raising.
- Weighted scorecard: each normalization method against hand-computed values.
- Rebate accrual: retrospective and incremental bases against hand-computed schedules at, just below,
  and just above each tier threshold.
- Learning curve: `cumulative_average_hours` and the derived marginal hours at units 1 through 32.
- Certification expiry: eligibility flips exactly at the expiry instant, not the day boundary.
- Error budget arithmetic: consumed, remaining, and burn rate for a fixture SLI series.
- Change failure probability: the multiplier chain evaluates in a fixed order and is invariant to
  config key ordering.
- CVSS v3.1 base score: vector parsing round-trips and scoring matches the specification's rounding.
- RBAC decision: `granted` and `denied` for a fixture grant set including expired grants and wildcard
  entries.
- Promotion decomposition: incremental, pulled forward, cannibalised, halo for a fixture calendar.
- Bass diffusion: adopters per period against the closed form.
- FVA ladder: stairstep deltas for a fixture set of four forecast series.
- Journal entry: balance check, no-negative check, closed-period rejection.
- Every variance formula against a hand-computed fixture with signs and favorability.
- NPV, IRR, simple and discounted payback for fixture cash flows including a no-root case that must
  raise rather than return.
- Claim payout: deductible, coinsurance, and limit applied in the correct order for boundary losses.
- Landed cost: ad valorem, specific, and compound duty for fixture entries.

### 7.2 Property-based invariants (Hypothesis)

Each is named as it appears in the test module so an implementer can find it.

| Invariant                                       | Statement                                                                                                                                                                      |
|-------------------------------------------------|--------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| `order_quantity_conservation`                   | For any sequence of legal order operations, `qty_ordered == qty_allocated + qty_backordered + qty_cancelled` and `qty_shipped <= qty_picked <= qty_allocated` after every step |
| `order_state_machine_legality`                  | No recorded transition lies outside the transition table                                                                                                                       |
| `allocation_no_oversell`                        | For any demand and supply vectors and any policy, total allocated per lot never exceeds lot on-hand                                                                            |
| `allocation_unit_conservation`                  | Allocated plus backordered equals demanded, and allocated never exceeds supply                                                                                                 |
| `fair_share_proportionality`                    | Under `FairShare`, for any two demands, the difference between their fill ratios is at most one unit of quantisation                                                           |
| `priority_dominance`                            | Under `Priority`, no lower-tier demand is filled while a higher-tier demand with an earlier promise date is short                                                              |
| `change_cost_monotone_in_stage`                 | For any change type, cost is non-decreasing across the stage sequence                                                                                                          |
| `perfect_order_bound`                           | `perfect_order_rate <= min(component rates)` for any population                                                                                                                |
| `contact_generation_causality`                  | Every generated contact references an existing earlier event                                                                                                                   |
| `service_queue_conservation`                    | Contacts created equals answered plus abandoned plus in queue at every instant                                                                                                 |
| `approval_authority`                            | No approval is recorded by a subject whose limit is below the approved value                                                                                                   |
| `sod_requester_not_approver`                    | For any generated PO, requester and approver differ                                                                                                                            |
| `price_curve_monotone`                          | Generated bid curves have non-increasing unit price in break quantity                                                                                                          |
| `award_respects_constraints`                    | Any award satisfies min suppliers, max share, and capacity for any feasible constraint set                                                                                     |
| `savings_avoidance_disjoint`                    | No event id appears as evidence in both a savings and an avoidance entry, and avoidance entries have no GL posting                                                             |
| `rebate_never_exceeds_spend`                    | Accrued rebate is at most the spend it is computed on                                                                                                                          |
| `landed_cost_monotone_in_duty`                  | Holding everything else fixed, landed cost is non-decreasing in the duty rate                                                                                                  |
| `merge_overlays_associative`                    | `merge_overlays` is associative on the canonical form for any three generated overlays, including overlapping targets                                                          |
| `apply_matches_merge`                           | `apply_overlay(apply_overlay(base, A), B)` and `apply_overlay(base, merge_overlays(A, B))` yield the same schedule content hash, for overlapping and disjoint targets alike    |
| `scenario_deactivation_restores`                | Deactivating every overlay restores the base schedule hash exactly                                                                                                             |
| `ftz_duty_neutrality`                           | With an unchanged rate, FTZ admission then domestic withdrawal yields the same total duty as direct import                                                                     |
| `drawback_bounded`                              | Refund is at most duty paid times the refund rate                                                                                                                              |
| `certification_gating`                          | No assignment exists where the worker lacks a valid certification at that sim-time                                                                                             |
| `no_work_after_termination`                     | No labor record exists past a termination date                                                                                                                                 |
| `hours_conservation`                            | Per worker per day, ledger hours equal roster hours minus absence plus overtime                                                                                                |
| `attrition_hazard_bounded`                      | The hazard lies in (0, 1) for any coefficient and driver values in the declared ranges                                                                                         |
| `cmdb_acyclic`                                  | The CI dependency graph has no cycle                                                                                                                                           |
| `rbac_deny_by_default`                          | `granted` is returned if and only if a matching unexpired grant exists                                                                                                         |
| `error_budget_bounded`                          | Consumed budget lies in [0, 1] and remaining equals one minus consumed                                                                                                         |
| `conduit_violation_completeness`                | Every crossing with no matching conduit produces exactly one violation event                                                                                                   |
| `promo_unit_conservation`                       | Over the promo window plus the pull-forward decay window, total units equal baseline total plus true incremental                                                               |
| `cannibalisation_conservation`                  | Units removed from cannibalised SKUs equal units added to the promoted SKU                                                                                                     |
| `cannibalisation_matrix_bounds`                 | Zero diagonal and column sums at most 1.0 for any generated matrix                                                                                                             |
| `bass_monotone`                                 | Cumulative adopters are non-decreasing and bounded by market potential                                                                                                         |
| `fva_ladder_identity`                           | The sum of step deltas equals the accuracy difference between the first and last rung                                                                                          |
| `one_number_identity`                           | Consensus volume, supply commitment, and finance reforecast volume agree for every period in the horizon                                                                       |
| `journal_balances`                              | Every generated journal entry has equal total debits and credits in integer minor units                                                                                        |
| `no_negative_amounts`                           | Every line has exactly one positive side                                                                                                                                       |
| `trial_balance_closure`                         | Assets equal liabilities plus equity at every period boundary                                                                                                                  |
| `statement_articulation`                        | Net income equals the change in retained earnings, and cash flow closing cash equals the balance sheet cash line                                                               |
| `inventory_flow_identity`                       | Beginning plus receipts minus issues minus adjustments equals ending, in units and value, for both valuation methods                                                           |
| `variance_attribution_closure`                  | Attributed amounts sum exactly to the variance amount                                                                                                                          |
| `bridge_reconciles`                             | Budget plus the sum of bridge components equals actual, exactly                                                                                                                |
| `money_never_created`                           | Across any generated event stream, the sum of all ledger postings is zero                                                                                                      |
| `cash_ledger_identity`                          | Cash balance equals opening plus inflows minus outflows                                                                                                                        |
| `claim_payout_bounds`                           | Payout lies in `[0, applicable_limit]`, `applicable_limit` is at most the policy limit, and payout is non-decreasing in gross loss                                             |
| `experience_modifier_monotone`                  | The modifier is non-decreasing in loss ratio and in TRIR                                                                                                                       |
| `tcor_reconciles_to_gl`                         | Each TCOR component equals the sum of its mapped accounts                                                                                                                      |
| `rounding_allocation_closes`                    | For any total and weight vector, largest-remainder lines sum to the total and each differs from its unrounded share by under one minor unit                                    |
| `money_multiply_is_half_even`                   | `Money.__mul__` rounds half to even at the boundary, including the two cases that separate half-even from half-up                                                              |
| `fairness_index_bounds`                         | Jain's index lies in `[1/n, 1]` over any demand population, equals 1 only at equal fill ratios, and never rises when a partially filled demand is driven to zero               |
| `spot_buy_never_beats_available_contract`       | No generated decision returns `spot` while the contract supplier can still meet `need_by`                                                                                      |
| `demand_multiplier_decomposes`                  | The product of a multiplier's listed factors equals the multiplier to 1e-12 relative                                                                                           |
| `promo_feature_frame_is_causal`                 | Every feature column for period `t` is computable from the calendar as it stood at the cut-off                                                                                 |
| `channel_shares_close`                          | Drifted shares are non-negative and sum to 1.0 within 1e-12 at every period, and equal the start shares exactly at `drift_step` zero                                           |
| `closing_entry_zeroes_nominal_accounts`         | After the closing entry, every revenue and expense account is zero and retained earnings moved by net income exactly                                                           |
| `correlation_is_deterministic_under_reordering` | For a fixed event set, the alerts raised do not depend on arrival order inside a window                                                                                        |
| `trace_spans_form_a_tree`                       | Every non-root span's parent exists in the same trace and the parent's interval contains the child's                                                                           |
| `authority_matrix_interpretation_agrees`        | Procurement, IT operations, and finance resolve the same matrix identically over a shared case grid                                                                            |
| `retained_equals_gross_minus_recovered`         | Retained loss equals gross loss minus recovery, exactly, in integer minor units, for any claim outcome                                                                         |
| `query_ordering_is_total`                       | Every metric and detection query with more than one row declares an ordering that is total over its result set                                                                 |

### 7.3 Validation gates

Two kinds of check live here and the section stopped calling them the same thing, because a table
whose stated contract is external validation cannot contain rows that cite nothing.

**External-reference gates** satisfy all five conditions of D-11. Each names a specific published
reference with edition and locator, asserts a tolerance no tighter than the precision that reference
prints, states a noise floor where the quantity is stochastic, and states what result falsifies it.
This repository is never a reference for itself.

**Definitional property checks** assert an identity that follows from a definition this section
states: double entry balances, attributed amounts close, an affine rescaling leaves a ranking
unchanged. They are real tests and several are the strongest tests in the suite, but they validate
internal consistency rather than agreement with the world, and they are labeled so.

**Golden-file regressions** are neither. A golden file detects change; it cannot detect that the
committed output was wrong on the day it was written. They moved out of this section into 7.6, where
the other regression checks live, because listing a file this repository generated as a validated
reference is exactly the self-citation D-11 forbids.

Every gate declares its tier and its measured budget in its test module, and
`test_validation_gate_budget_arithmetic` sums them per tier. Eight gates run in the full tier
because their replication counts cannot fit a push job: VG-FIN-07, VG-FIN-11, VG-PRC-04, VG-HR-02,
VG-HR-04, VG-HR-05, VG-CMR-05, and VG-INS-01. Every other gate runs in the fast tier on every push.

Where a reference is openly licensed for the use, the worked example is reproduced in the fixture
with attribution. Where it is not, the numeric inputs and the published result are encoded with a
citation and the source's prose, tables, and layout are not reproduced. The OpenStax gates fall in
the second case, and open question 15 records why.

#### Finance and costing

| Gate      | Reference                                                                                                                                                                                                                                | Assertion and tolerance                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                    |
|-----------|------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| VG-FIN-01 | Double-entry identity (definitional)                                                                                                                                                                                                     | Every entry balances exactly in integer minor units. Zero tolerance                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                        |
| VG-FIN-02 | Accounting equation (definitional)                                                                                                                                                                                                       | Trial balance closes and assets equal liabilities plus equity at each period close. Zero tolerance                                                                                                                                                                                                                                                                                                                                                                                                                                                                         |
| VG-FIN-03 | Statement articulation (definitional)                                                                                                                                                                                                    | Net income ties to retained earnings movement; indirect and direct cash flow agree. Zero tolerance                                                                                                                                                                                                                                                                                                                                                                                                                                                                         |
| VG-FIN-04 | OpenStax, _Principles of Accounting, Volume 2: Managerial Accounting_, Chapter 8 (Standard Costs and Variances). License CC BY-NC-SA, verified from the OpenStax book metadata API on 2026-08-09                                         | Direct material price and quantity, direct labor rate and efficiency, variable overhead spending and efficiency, and fixed overhead budget and volume variances reproduce the published worked-example figures. Exact to the cent. The fixture encodes the numeric inputs and the published answers with a citation to the chapter, and reproduces no prose, table, or layout from the book                                                                                                                                                                                |
| VG-FIN-05 | Flexible budget reconciliation (definitional)                                                                                                                                                                                            | The sum of all computed variances equals total actual cost minus total standard cost allowed for actual output. Zero tolerance                                                                                                                                                                                                                                                                                                                                                                                                                                             |
| VG-FIN-06 | Attribution closure (definitional)                                                                                                                                                                                                       | Attributed event contributions sum to the variance. Zero tolerance                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                         |
| VG-FIN-07 | NIST/SEMATECH e-Handbook of Statistical Methods, Section 6.3.1 (What are Control Charts?), which publishes the 3-sigma false alarm rate for a normal characteristic as 0.00135 in one direction and 0.0027 in both. Retrieved 2026-08-09 | Configured with `nelson_rules: [rule_1]` and chart limits supplied rather than estimated, over 100,000 seeded in-control variance points the fraction the common-cause gate classifies `assignable` matches 0.0027 to the three significant digits the handbook prints. Noise floor: the binomial standard error at n = 100,000 and p = 0.0027 is 1.6e-4, so the gate asserts the 99 percent binomial interval, which is wider than the published precision. Falsified by an observed rate outside `[0.00228, 0.00312]`                                                    |
| VG-FIN-08 | Present value definition (definitional), plus `numpy-financial` as an independent implementation at its own precision                                                                                                                    | Two separate assertions. The Decimal evaluation of the definition matches the implementation to zero error at 28 significant digits, which is an identity check between two Decimal evaluations. The float64 cross-check against `numpy-financial` asserts 1e-12 relative agreement, which is the precision float64 can witness. IRR matches a bisection root of the same polynomial to 1e-9 relative on 1000 seeded vectors. Falsified by any vector exceeding either tolerance, or by a two-sign-change cash flow with one real root that raises instead of returning it |
| VG-FIN-09 | OpenStax, _Principles of Accounting, Volume 1: Financial Accounting_, Chapter 10 (Inventory). License CC BY-NC-SA, verified 2026-08-09                                                                                                   | Weighted average and FIFO ending inventory and cost of goods sold reproduce the published worked examples. Exact to the cent. Numeric inputs and answers encoded with a citation, no prose reproduced                                                                                                                                                                                                                                                                                                                                                                      |
| VG-FIN-10 | OpenStax, _Principles of Accounting, Volume 1: Financial Accounting_, Chapter 11 (Long-Term Assets). License CC BY-NC-SA, verified 2026-08-09                                                                                            | Straight line, double declining balance, and units of production depreciation schedules reproduce the published examples. Exact to the cent. Encoded as above                                                                                                                                                                                                                                                                                                                                                                                                              |
| VG-FIN-11 | Little, J. D. C. (1961), "A Proof for the Queuing Formula: L = lambda W", _Operations Research_ 9(3), 383-387, doi:10.1287/opre.9.3.383                                                                                                  | Over a long seeded run, mean orders in the pipeline equals arrival rate times mean order cycle time, inside the batch-means 95 percent confidence interval, on at least 16 of 20 declared seeds. 16 is the 0.005 lower quantile of Binomial(20, 0.95), so a correct implementation fails about one run in 390 if the seeds were resampled; the seeds are fixed, so the gate is reproducible and the threshold states the risk it was chosen against. Falsified by 15 or fewer covering seeds                                                                               |

#### Procurement and trade

| Gate      | Reference                                                                                                                            | Assertion and tolerance                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                    |
|-----------|--------------------------------------------------------------------------------------------------------------------------------------|----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| VG-PRC-01 | Fixture matrix (definitional)                                                                                                        | Every three-way match violation class and both sides of every tolerance boundary produce the expected classification. Exact. Falsified by any reachable class the fixture suite cannot produce, which is why the invoice is its own aggregate                                                                                                                                                                                                                                                                                                                                                                                                                                                                              |
| VG-PRC-02 | Scale invariance (definitional)                                                                                                      | An affine transformation of a criterion's raw scores followed by renormalisation leaves the ranking unchanged, for 1000 generated bid sets                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                 |
| VG-PRC-03 | Measured heuristic gap (definitional)                                                                                                | On every fixture with at most `sourcing.exact_award_max_suppliers` suppliers, `AwardGapReport` reports the relative gap between the greedy award and the exact argmax, both totally ordered by `(-score, supplier_id)`. The suite asserts the gap recorded alongside each fixture, including the non-zero one on `greedy_suboptimal.yaml`. It does not assert the gap is zero, because greedy is not optimal under break curves and share caps. Falsified by a gap differing from the recorded value, which flags either a scoring change or a strategy regression                                                                                                                                                         |
| VG-PRC-04 | Harris, F. W. (1913), "How Many Parts to Make at Once", reprinted in _Operations Research_ 38(6), 947-950, doi:10.1287/opre.38.6.947 | Computed EOQ matches `sqrt(2DS/H)` to 1e-9. The simulated total cost at EOQ is the minimum over a grid of plus or minus 40 percent in 5 percent steps on at least 16 of 20 declared seeds, the same Binomial(20, 0.95) threshold VG-FIN-11 uses and for the same reason. Noise floor: the gate computes the batch-means half-width at the shipped run length and reports it, and asserts that adjacent grid points differ by more than the measured half-width at the shipped parameters. If they do not, the grid is too fine for the run length and the gate says so rather than reporting a spurious argmin. Falsified by 15 or fewer covering seeds, or by any seed whose argmin lies more than one grid step from EOQ |
| VG-PRC-05 | Discount economics (definitional)                                                                                                    | The annualised discount rate formula matches hand computation, and the take-or-skip decision flips exactly at the hurdle rate                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                              |
| VG-PRC-06 | Spot-buy dominance (definitional)                                                                                                    | Over 1000 generated slip scenarios, no recommendation is `spot` while the contract supplier can meet `need_by`, and `net_benefit` equals its stated components to the cent                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                 |
| VG-TRD-01 | Duty arithmetic (definitional)                                                                                                       | Ad valorem, specific, and compound duty match hand computation on 200 fixture entries. Exact to the cent under the section 3 rounding contract                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                             |
| VG-TRD-02 | Overlay algebra (definitional)                                                                                                       | `merge_overlays` associativity, agreement between sequential application and merged application, deactivation restoration, and monotonicity of landed cost in duty, over 1000 generated overlay pairs of which at least half share a target. Falsified by any pair whose two application paths give different schedule hashes                                                                                                                                                                                                                                                                                                                                                                                              |
| VG-TRD-03 | FTZ neutrality (definitional)                                                                                                        | Total duty under FTZ admission then domestic withdrawal equals direct import duty at an unchanged rate. Exact                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                              |

#### Workforce

| Gate     | Reference                                                                                                                                                                                                                   | Assertion and tolerance                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                 |
|----------|-----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| VG-HR-01 | Wright, T. P. (1936), "Factors Affecting the Cost of Airplanes", _Journal of the Aeronautical Sciences_ 3(4), 122-128, doi:10.2514/8.155                                                                                    | The cumulative average at units 1, 2, 4, 8, 16, 32 reproduces the doubling sequence `a * x ** (ln(rate)/ln(2))` for the configured learning rate to 1e-12, which is the precision of the closed form in float64. Falsified by any of the six points exceeding it                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                        |
| VG-HR-02 | Ground-truth recovery (definitional, against the generator's own declared coefficients)                                                                                                                                     | Over 200 replications of a seeded population of 5000 workers, each generator coefficient lies inside the fitted logistic model's 95 percent Wald interval on at least 182 of 200 replications. 182 is the smallest threshold whose false-failure probability under Binomial(200, 0.95) is at or below 0.006: P(X <= 181) = 0.0058, so a correct implementation fails about one run in 172. The fitter is cross-checked against `statsmodels` on the same design matrix to 1e-6 relative on the coefficient vector, which is the agreement an iterative MLE can hold across BLAS backends and library versions; 1e-8 was tighter than the numerical reality. Both libraries run single-threaded with a pinned convergence tolerance. Falsified by 171 or fewer covering replications for any coefficient |
| VG-HR-03 | Calibration and leakage control (definitional)                                                                                                                                                                              | The absence predictor's Brier score beats the base-rate predictor on held-out seeded data with a paired test at p below 0.01, and the calibration slope lies in [0.9, 1.1]. A null run with all generator coefficients set to zero must NOT beat base rate, which catches leakage                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                       |
| VG-HR-04 | Erlang C, as given in Gans, Koole, and Mandelbaum (2003), "Telephone Call Centers: Tutorial, Review, and Research Prospects", _Manufacturing and Service Operations Management_ 5(2), 79-141, doi:10.1287/msom.5.2.79.16071 | Run under `service.validation_profile` (Poisson arrivals, exponential handle times, `c` servers, abandonment disabled, proficiency scaling off), the simulated mean wait matches the Erlang C analytic value inside the batch-means 95 percent confidence interval on at least 16 of 20 declared seeds, at utilizations 0.6, 0.8, and 0.9. Noise floor: the gate computes the batch-means half-width at 30 batches, reports it as a fraction of mean wait at each utilization, and records it in the capability report. The tolerance is that measured half-width, not a number chosen in advance, which is why the gate can be tightened only by lengthening the run. Falsified by 15 or fewer covering seeds at any utilization                                                                       |
| VG-HR-05 | Erlang A, as given in Garnett, Mandelbaum, and Reiman (2002), "Designing a Call Center with Impatient Customers", _Manufacturing and Service Operations Management_ 4(3), 208-227, doi:10.1287/msom.4.3.208.7753            | Under the same profile with exponential patience enabled, the simulated abandonment rate matches the Erlang A analytic value inside the batch-means 95 percent confidence interval on at least 16 of 20 seeds at two utilization levels. Falsified as above                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                             |
| VG-HR-06 | Engagement measurement (definitional)                                                                                                                                                                                       | `schedule_stability_index`, `weekend_shift_rate_8w`, and `strain_trend_slope` match hand computation on a fixture roster and strain series, each is bounded as declared, and each accumulates its declared points per worker inside the long-horizon profile of 7.5                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                     |

#### IT and cyber

| Gate     | Reference                                                                                                                                                                                                                                 | Assertion and tolerance                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                     |
|----------|-------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|-------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| VG-IT-01 | FIRST, _Common Vulnerability Scoring System v3.1: Specification Document_, section 7 (Roundup) and section 8.1, plus the published CVSS v3.1 Examples page. Both retrieved 2026-08-09                                                     | Base scores computed from vectors match the published values exactly, including the Roundup rule that returns the smallest number to one decimal place at or above its input. Every worked example on the Examples page is a test case. Falsified by any published example whose score the implementation does not reproduce                                                                                                                                                                                                                                                                                                                                |
| VG-IT-02 | Google, _The Site Reliability Workbook_, Chapter 5 (Alerting on SLOs), Tables 5-6 and 5-8, retrieved 2026-08-09. Those tables give 2 percent over 1 hour, 5 percent over 6 hours, and 10 percent over 3 days, against a 30-day SLO window | Two assertions. `derive_burn_rates` evaluated at `window_days = 30` reproduces the Workbook's 14.4, 6, and 1 exactly, which validates the derivation against the published pairs. Then, at this section's configured 28-day window, alerts fire and clear exactly at the derived thresholds 13.44, 5.6, and 0.9333 on a fixture SLI series, boundary cases tested on both sides. Falsified by a threshold literal appearing anywhere in config, or by any boundary case firing on the wrong side                                                                                                                                                            |
| VG-IT-03 | DORA metric definitions (definitional, from the published four key metrics)                                                                                                                                                               | Computed values match hand computation on a fixture change, trace, and incident log. Lead time and failed-deployment recovery time are computed from the span stream, not from ticket timestamps. Exact                                                                                                                                                                                                                                                                                                                                                                                                                                                     |
| VG-IT-04 | Detection rule fixtures (definitional)                                                                                                                                                                                                    | Every rule fires on its positive fixture with the expected count and does not fire on its negative fixture, under the pinned watermark and total ordering of section 3. CI fails a rule missing either fixture, or whose logic changed without a semver bump                                                                                                                                                                                                                                                                                                                                                                                                |
| VG-IT-05 | RPO and RTO definitions (definitional)                                                                                                                                                                                                    | In a seeded restore drill, measured RPO equals the sim-time between the last verified backup and the failure instant, and the counted data-loss events equal the events logged in that window. Exact                                                                                                                                                                                                                                                                                                                                                                                                                                                        |
| VG-IT-06 | Bounded model check against a reference implementation (definitional)                                                                                                                                                                     | The model is 3 roles, 4 permissions, 3 subjects, each subject holding at most 2 roles, with expiry drawn from three declared instants. That is `2 ** 12` role-permission assignments times `3 ** 7` grant configurations times 12 requests, and the suite enumerates a declared 1,000,000-case pseudo-random sample of it with a fixed seed rather than the whole space. The word "exhaustive" is gone: the earlier model (4 roles, 6 permissions, 5 subjects) has more than 1e14 cases before expiry and wildcards and cannot be enumerated in any budget. Falsified by one case where the engine and the reference set-membership implementation disagree |
| VG-IT-07 | Conduit completeness (definitional)                                                                                                                                                                                                       | Every simulated cross-zone message either matches a conduit or produces exactly one violation, over 10,000 generated messages. Exact                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                        |
| VG-IT-08 | Correlation determinism and completeness (definitional)                                                                                                                                                                                   | For each correlation rule, the positive fixture raises exactly one alert with the expected contributing findings and the negative fixture raises none. The same event set shuffled 100 ways raises the identical alert list, which is what the window sort guarantees. Falsified by any shuffle changing the alert list                                                                                                                                                                                                                                                                                                                                     |
| VG-IT-09 | Exposure model arithmetic (definitional)                                                                                                                                                                                                  | `P_breach(t)` matches `1 - (1 - p) ** t` to 1e-12, the known-exploited uplift multiplies the daily hazard and clamps at 1.0, and the CVaR estimate at `cvar_samples` draws lies inside its own reported standard error of an analytic CVaR on a fixture lognormal impact. Falsified by the objective ranking two windows differently at `alpha = 0` from expected total cost                                                                                                                                                                                                                                                                                |

#### Commercial and S&OP

| Gate      | Reference                                                                                                                                                                                                                                | Assertion and tolerance                                                                                                                                                                                                                                                                                                                                                               |
|-----------|------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| VG-CMR-01 | Unit conservation (definitional)                                                                                                                                                                                                         | Total demand over the promotion window plus the decay window equals baseline plus true incremental, to 1e-9 relative on the share matrix and exactly on integer units. The tolerance is stated rather than claimed exact because the shares are floats, and the `fsum` in sorted key order keeps accumulated error below it                                                           |
| VG-CMR-02 | Bass, F. M. (1969), "A New Product Growth for Model Consumer Durables", _Management Science_ 15(5), 215-227, doi:10.1287/mnsc.15.5.215                                                                                                   | With stochasticity disabled, the simulated cumulative adoption path matches `F(t) = (1 - exp(-(p+q)t)) / (1 + (q/p) exp(-(p+q)t))` to 1e-10. Falsified by any horizon point exceeding it                                                                                                                                                                                              |
| VG-CMR-03 | Hyndman, R. J. and Koehler, A. B. (2006), "Another look at measures of forecast accuracy", _International Journal of Forecasting_ 22(4), 679-688, doi:10.1016/j.ijforecast.2006.03.001, for MASE; standard definitions for MAPE and WAPE | Metric implementations match the published formulas on fixture series to 1e-12, and are cross-checked against an independent implementation. Falsified by a fixture series where the two implementations differ beyond the tolerance                                                                                                                                                  |
| VG-CMR-04 | FVA identity (definitional)                                                                                                                                                                                                              | The stairstep deltas sum to the total accuracy change; the naive rung's FVA against itself is exactly zero; a deliberately degraded rung yields a negative FVA                                                                                                                                                                                                                        |
| VG-CMR-05 | Quota pressure (definitional, against the generator's own parameters)                                                                                                                                                                    | The measured ratio of last-period-week volume to mean-week volume matches the value implied by the configured `k` and `q` inside the Monte Carlo 95 percent interval on at least 16 of 20 declared seeds. Noise floor: the gate computes and reports the Monte Carlo interval half-width at the shipped run length rather than asserting one. Falsified by 15 or fewer covering seeds |
| VG-CMR-06 | One-number identity (definitional)                                                                                                                                                                                                       | Consensus, supply commitment, and finance reforecast volumes agree exactly for every horizon period across 50 seeded S&OP cycles, in every supply review mode                                                                                                                                                                                                                         |
| VG-CMR-07 | Promo feature causality (definitional)                                                                                                                                                                                                   | Every column of `PromoFeatureFrame` for period `t` is computable from the calendar at the cut-off, and a fixture back-dating a calendar entry past the cut-off is rejected. Falsified by a frame column that changes when realized demand changes and the calendar does not                                                                                                           |
| VG-CMR-08 | Demand shaping decomposition (definitional)                                                                                                                                                                                              | The product of a `DemandMultiplier`'s factors equals its multiplier to 1e-12 relative over 1000 generated lever combinations, the multiplier is clamped at `max_multiplier`, and channel shares stay on the simplex under drift                                                                                                                                                       |

#### Insurance

| Gate      | Reference                                       | Assertion and tolerance                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                |
|-----------|-------------------------------------------------|----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| VG-INS-01 | Indemnity arithmetic (definitional)             | Payout equals `min(applicable_limit, max(0, loss - deductible) * coinsurance)` on 5000 generated losses, where `applicable_limit` is the sublimit `SublimitResolver` selects or the policy limit when no rule matches. Exact to the cent under the section 3 rounding contract. At least 500 of the generated losses match a sublimit rule, so the sublimit path is covered rather than declared. Falsified by any loss whose payout exceeds its applicable limit, or by `binding_constraint` naming a constraint that was not binding |
| VG-INS-02 | Business interruption arithmetic (definitional) | Indemnified hours equal downtime minus waiting period, capped at the indemnity period, and the loss equals indemnified hours times `rate_per_hour` from `fin.gross_profit_rate`. Exact. Falsified by a claim valued at a rate that does not appear in the ledger for that period                                                                                                                                                                                                                                                       |
| VG-INS-03 | Monotonicity (definitional)                     | The experience modifier is non-decreasing in loss ratio and in TRIR, and stays inside `modifier_bounds`, over 1000 generated histories                                                                                                                                                                                                                                                                                                                                                                                                 |
| VG-INS-04 | TCOR reconciliation (definitional)              | Each component ties to its mapped GL accounts for the period. Exact. `retained_losses` ties because `risk.loss_recognised` posts the gross loss and `risk.recovery_posted` posts the recovery; falsified by a period where recognized losses and the mapped accounts differ by any amount                                                                                                                                                                                                                                              |

### 7.4 Control chart assignment per KPI

The LSS engine selects a chart by data type. This section declares the expected selection per metric
so the assignment itself is testable and a reviewer can see the statistics were chosen, not defaulted.

A chart needs points before it has limits. An I-MR chart needs about 20 points, and a metric that
produces one point per month needs twenty months of sim time before it can signal at all. The
`Points needed` column states the requirement and the `Profile` column states which scenario horizon
supplies them: `demo` is the 90-day horizon most scenarios in 7.5 run, and `long` is the 36-month
horizon of `s_backoffice_18`, which exists so that the low-frequency charts have a run in which they
can be tested. `test_chart_has_enough_points` asserts, for every row, that the named profile produces
at least the points the row needs. A chart with no profile that can supply its points is a defect,
not a diagram.

| Metric                                   | Data type                 | Chart                 | Point cadence           | Points needed | Profile | Notes                                                                                                                                                                          |
|------------------------------------------|---------------------------|-----------------------|-------------------------|---------------|---------|--------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| `perfect_order_rate`                     | proportion, variable n    | p-chart               | weekly subgroups        | 20            | demo    | weekly subgroups                                                                                                                                                               |
| `on_time_delivery_rate`                  | proportion                | p-chart               | weekly subgroups        | 20            | demo    |                                                                                                                                                                                |
| `wismo_rate`                             | count per exposure        | u-chart               | weekly                  | 20            | demo    | per 100 order-days open past promise                                                                                                                                           |
| `order_cycle_time_hours`                 | continuous                | X-bar and R           | daily subgroups         | 25            | demo    | daily subgroups                                                                                                                                                                |
| `first_contact_resolution_rate`          | proportion                | p-chart               | daily                   | 25            | demo    |                                                                                                                                                                                |
| `average_speed_of_answer_seconds`        | continuous, right skewed  | I-MR on log transform | daily                   | 25            | demo    | the transform is declared, not silent                                                                                                                                          |
| `fairness_index`                         | continuous, bounded       | I-MR                  | one per allocation run  | 25            | demo    | runs every `run_cadence_hours`                                                                                                                                                 |
| `purchase_price_variance`                | continuous                | I-MR plus EWMA        | one per receipt         | 25            | demo    | EWMA for small sustained shifts                                                                                                                                                |
| `contract_price_variance`                | continuous                | I-MR plus EWMA        | one per receipt         | 25            | demo    | analytic only, no GL consequence                                                                                                                                               |
| `market_index_price_variance`            | continuous                | I-MR plus EWMA        | one per receipt         | 25            | demo    | analytic only, no GL consequence                                                                                                                                               |
| `po_cycle_time_hours`                    | continuous                | X-bar and R           | weekly subgroups        | 20            | demo    | weekly subgroups                                                                                                                                                               |
| `first_pass_match_rate`                  | proportion                | p-chart               | weekly                  | 20            | demo    |                                                                                                                                                                                |
| `maverick_spend_pct`                     | proportion                | p-chart               | weekly                  | 20            | demo    |                                                                                                                                                                                |
| `turnover_rate`                          | proportion of headcount   | p-chart               | monthly                 | 20            | long    | 20 months of sim time; the demo profile charts the points and reports limits as provisional                                                                                    |
| `absenteeism_rate`                       | proportion                | p-chart               | daily                   | 25            | demo    |                                                                                                                                                                                |
| `schedule_stability_index`               | continuous, bounded       | I-MR                  | weekly per worker       | 20            | demo    | 6a14's behavioral engagement indicator                                                                                                                                         |
| `weekend_shift_rate_8w`                  | proportion                | p-chart               | weekly per worker       | 20            | demo    | 6a14's behavioral engagement indicator                                                                                                                                         |
| `strain_trend_slope`                     | continuous                | I-MR                  | weekly per worker       | 20            | demo    | needs 8 weeks of strain history before the first point                                                                                                                         |
| `overtime_pct_4w`                        | continuous, right skewed  | I-MR on log transform | weekly per worker       | 20            | demo    |                                                                                                                                                                                |
| `labor_cost_per_unit`                    | continuous                | I-MR                  | daily                   | 25            | demo    |                                                                                                                                                                                |
| `time_to_productivity_days`              | continuous                | I-MR                  | one per hire            | 20            | long    | needs 20 hires, which the demo hiring rate does not reach                                                                                                                      |
| `mttd_minutes`, `mttr_minutes`           | continuous, right skewed  | I-MR on log transform | one per incident        | 25            | demo    |                                                                                                                                                                                |
| `change_failure_rate`                    | proportion                | p-chart               | weekly                  | 20            | demo    |                                                                                                                                                                                |
| `deployment_frequency`                   | count per fixed window    | c-chart               | weekly                  | 20            | demo    |                                                                                                                                                                                |
| `patch_latency_hours`                    | continuous, right skewed  | I-MR on log transform | one per patch           | 20            | demo    |                                                                                                                                                                                |
| `cross_zone_anomaly_rate`                | count per exposure        | u-chart               | hourly                  | 25            | demo    | per 10,000 messages                                                                                                                                                            |
| `correlated_alert_rate`                  | count per exposure        | u-chart               | daily                   | 20            | demo    | per 1000 findings                                                                                                                                                              |
| `request_error_rate`                     | proportion                | p-chart               | hourly                  | 25            | demo    | from the span stream                                                                                                                                                           |
| `request_latency_p95_ms`                 | continuous, right skewed  | I-MR on log transform | hourly                  | 25            | demo    | from the span stream                                                                                                                                                           |
| `backup_restore_success_rate`            | rare-event proportion     | g-chart               | one per drill           | 20            | long    | successes between failures. At `drill_cadence_days: 90` this needs 20 drills, so 60 months; the long profile runs drills at 30 days for the chart test and states that it does |
| `forecast_bias`, `forecast_value_added`  | continuous                | I-MR plus EWMA        | one per cycle           | 20            | long    | one point per S&OP cycle, so 20 months                                                                                                                                         |
| `decision_latency_days`                  | continuous                | I-MR                  | one per cycle           | 20            | long    | one point per cycle                                                                                                                                                            |
| `close_cycle_days`                       | continuous                | I-MR                  | one per period          | 20            | long    | one point per period, so 20 months                                                                                                                                             |
| `variance_by_kind`                       | continuous                | I-MR                  | one per period per kind | 20            | long    | per variance kind, feeds the common-cause gate                                                                                                                                 |
| `dio`, `dso`, `dpo`, `cash_to_cash_days` | continuous                | I-MR                  | monthly                 | 20            | long    | monthly                                                                                                                                                                        |
| `inventory_record_accuracy`              | proportion                | p-chart               | per count cycle         | 20            | demo    | A-class SKUs count every 30 days                                                                                                                                               |
| `claim_cycle_days`                       | continuous, right skewed  | I-MR on log transform | one per claim           | 20            | long    |                                                                                                                                                                                |
| `total_cost_of_risk`                     | continuous, low frequency | I-MR                  | quarterly               | 20            | long    | 20 quarters is 60 months, beyond even the long profile; the chart is defined, its limits are reported as provisional, and open question 14 records the gap                     |

### 7.5 Seeded end-to-end scenarios

Each runs in simulation mode with a fixed seed, produces golden files, and doubles as demo material.
Every scenario states its simulated horizon, because a chart assignment that no run can ever
populate is not checkable, and because the sim-time budget is what section 7's tier budgets are
spent on.

| Scenario                    | Seed name         | Horizon   | What it proves                                                                                                                                                                                                                                                                                                                                                                            |
|-----------------------------|-------------------|-----------|-------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| `dock_failure_to_churn`     | `s_backoffice_01` | 14 days   | A dock door failure delays shipments, generates contacts, degrades satisfaction, churns a customer, and posts the lost margin. Asserts the causal chain from a physical event to a finance number, and the ranked customer callback list                                                                                                                                                  |
| `allocation_policy_bakeoff` | `s_backoffice_02` | 90 days   | The same shortage under fair share, priority, and hybrid across 20 paired replications. Asserts fill by segment, the Jain fairness index over every demand including zero-fill, and the paired verdict with its effect size and interval                                                                                                                                                  |
| `visibility_ab`             | `s_backoffice_03` | 90 days   | The same shift at `order_header` and `twin_grounded` visibility, 20 paired replications on common random numbers. Asserts the FCR delta, its paired interval, and that both arms drew identical values from every shared contact substream                                                                                                                                                |
| `p2p_exception_storm`       | `s_backoffice_04` | 90 days   | A supplier sends malformed invoices for two weeks. Asserts exception queue growth, match rate drop, discount capture loss, DPO movement, and the mined procure-to-pay variant map                                                                                                                                                                                                         |
| `sourcing_consolidation`    | `s_backoffice_05` | 180 days  | Five suppliers to three. Asserts tier savings, tier-1 concentration, the greedy-versus-exact award gap, resilience cost from a disruption replay, and the recommendation. Tier-2 concentration is reported as `unenforced` and is not asserted, because the E19 supplier DAG is Phase 6                                                                                                   |
| `tariff_shock_forward_buy`  | `s_backoffice_06` | 180 days  | A rate shock scenario activates with 60 days notice. Asserts landed cost re-ranking, the forward-buy breakeven, the cash impact, and the duty variance in the GL                                                                                                                                                                                                                          |
| `peak_labor_strategy`       | `s_backoffice_07` | 8 weeks   | Temps versus overtime versus hiring pulse over an eight-week peak, 20 paired replications. Asserts total cost, error rates, attrition, and service level with the paired verdict per strategy pair                                                                                                                                                                                        |
| `certification_cliff`       | `s_backoffice_08` | 90 days   | Two certifications lapse in the same week. Asserts HR-003 fires before the line stops and the cross-training what-if quantifies the prevention                                                                                                                                                                                                                                            |
| `friday_change_freeze`      | `s_backoffice_09` | 90 days   | The same change stream with and without a Friday freeze, 20 paired replications. Each change draws its outcome from `root/itops/change_outcome` subscripted by `chg_id`, so rescheduling does not desynchronise the arms. Asserts the change failure rate delta, incident count, error budget consumption, and the paired interval                                                        |
| `critical_cve_window`       | `s_backoffice_10` | 14 days   | A critical vulnerability on the broker with a four-hour patch requirement. Asserts the candidate window costs, the breach exposure curve, and the recommendation, and that the agent answer contains only numbers traceable to query results                                                                                                                                              |
| `restore_drill`             | `s_backoffice_11` | 7 days    | Historian failure and restore. Asserts measured RPO and RTO, counted data-loss events, and the target-met verdict                                                                                                                                                                                                                                                                         |
| `promo_that_broke_the_dc`   | `s_backoffice_12` | 90 days   | A 20 percent promotion timed into a capacity peak. Asserts CMR-001 fires at planning time, and the run quantifies overtime, expedite, cannibalisation, forward buy, and margin after all of it, plus the alternative timing recommendation                                                                                                                                                |
| `sop_cycle_with_scoring`    | `s_backoffice_13` | 3 months  | Three consecutive S&OP cycles. Asserts the one-number identity, the FVA report, the decision packet golden file, and that cycle three scores cycle two's assumptions                                                                                                                                                                                                                      |
| `month_end_close_kaizen`    | `s_backoffice_14` | 6 months  | The close run before and after task reordering, paired across 20 replications with task durations drawn per `task_id`. Asserts the close cycle time reduction, its paired interval, and that the mined close process matches the checklist graph                                                                                                                                          |
| `margin_drop_decomposition` | `s_backoffice_15` | 90 days   | Gross margin falls 1.8 points from a mix of tariff, scrap, labor, and freight causes. Asserts the ranked decomposition, the common-cause versus assignable split, and that each assignable component drills to the seeded physical events                                                                                                                                                 |
| `cargo_claim_to_premium`    | `s_backoffice_16` | 24 months | A cold-chain excursion produces a claim, and the claim history raises next year's premium. Asserts payout arithmetic, TCOR movement, and the risk transfer comparison                                                                                                                                                                                                                     |
| `sod_violation_caught`      | `s_backoffice_17` | 7 days    | A grant set is changed to create a create-vendor plus approve-payment conflict. Asserts config validation rejects it at load, and that a runtime-injected grant raises IT-008 and FIN-005                                                                                                                                                                                                 |
| `long_horizon_charts`       | `s_backoffice_18` | 36 months | The low-frequency charts of 7.4 accumulate their declared points. Asserts that `close_cycle_days`, `turnover_rate`, `decision_latency_days`, `forecast_bias`, the working capital series, and `backup_restore_success_rate` each reach at least the points their row needs and each produces limits. This scenario exists so the chart assignments are checkable rather than aspirational |
| `spot_buy_versus_contract`  | `s_backoffice_19` | 60 days   | A supplier slips two weeks into a shortage. Asserts the three priced options, the recommendation, the PO carrying `buy_mode: spot`, and that the justified spot spend is excluded from maverick leakage                                                                                                                                                                                   |
| `cross_zone_correlation`    | `s_backoffice_20` | 14 days   | A credential-spray pattern crosses three zones over four days. Asserts three separate detection findings, one correlated alert naming all three, IT-009, and that a shuffled event order raises the identical alert                                                                                                                                                                       |

### 7.6 Determinism and contract tests

- C1, byte-identical tier (D-05): each scenario runs twice in the same CI job on the same platform
  and the same pinned dependency set, and the SHA-256 of the full event log, the GL table, and the
  generated statements must match. A mismatch prints the first differing event.
- C1, value-equivalent tier (D-05): the same scenario runs on the two other supported platforms and
  the job asserts that the business events are identical and reports the observed maximum divergence
  on continuous fields. The tolerance is derived from measured divergence rather than chosen in
  advance, and the job names whether an excess is a wrong tolerance or a real defect. Nothing in this
  section claims byte identity across platforms.
- C1 lint: no module in these packages imports `time`, `datetime.now`, `random`, `secrets`, or
  `socket`, and none calls `open(`, `pathlib.Path`, `os.path`, or `shutil`, outside an annotated
  escape hatch. The filesystem entries are as load-bearing as the clock entries, because a model
  that opens a path is a model that cannot run against an object store or an in-memory fixture. CI
  enforces the lint; the hash check backstops it.
- C1 hash-seed check (D-03): the determinism scenario runs twice under different `PYTHONHASHSEED`
  values and the hashes are compared, which is what catches an unsorted iteration reaching the log.
- C3: producer and consumer contract tests per event type. Adding a required field to an event within
  a major version fails; adding an optional field passes; removing a field fails. The same job
  asserts that every event named in a consumed list has a producer somewhere, and that every
  published event has a declared consumer or an explicit `consumers: []` marker.
- C5: every shipped config file validates, and a corrupted copy of each produces an error message
  containing the file name, the line number, and a suggestion. The suggestion text itself is
  asserted for the ten most likely mistakes (weights not summing to one, a missing certification, a
  tie-break list not ending in a unique key, an unbalanced posting rule, a decreasing change cost
  table, an infeasible award constraint set, a missing `provenance` key, a self-referencing conduit,
  overlapping tariff effectivity, and a reserve rate vector of the wrong length). Each suggestion is
  asserted to be representable in the schema it suggests, so an error message can never tell a user
  to write something the config cannot express.
- A1: a CI job creates a fresh virtualenv per package, installs only that package from the built
  wheel, and runs its standalone example. If a package needs a sibling to run its own example, the
  job fails, which is the mechanical enforcement of take-one-brick.
- Budget arithmetic (D-13): `test_validation_gate_budget_arithmetic` sums the declared budget of
  every test in a tier and fails when the sum exceeds the tier ceiling in section 7. A scenario or
  gate that grows past its budget fails as a defect with the offending total quoted, rather than as
  a CI timeout with no explanation.
- Golden-file regressions: the P&L, balance sheet, cash flow, working capital snapshot, decision
  packet, and maturity snapshot for the reference seeded scenarios byte-match their committed
  files. Regenerating needs an explicit `just regolden` and a diff review. These detect change; they
  do not validate correctness, which is why they sit here and not in 7.3.

### 7.7 Agent evaluation contributions (E27)

Each tool ships at least three eval questions whose ground truth is computed from the simulation.
Refusal cases are included by design: a question about a customer that does not exist, a question
requiring a metric not in the semantic layer, and a question asked while the underlying tool is
failing must all produce an abstention or a refusal, never a number. The grounding checker (E26f)
must reject any answer sentence containing a number without a matching query-result id, and the
back-office eval set includes three adversarial questions that invite the model to do arithmetic in
tokens (percentage changes, per-unit divisions, and a currency conversion) to prove it does not.

Indirect prompt injection cases contributed to the E43 red-team suite from this section: an
instruction embedded in a supplier name, in a service contact free-text field, in a detection rule
title, and in a capex request description. The agent must treat all four as data.

## 8. Phase placement

### 8.1 What the source says

The constraints paragraph places the safety and ergonomics layer (6a10) "after 3i", then runs
6a11 through 6a17 in order, then Phase 4. So the band this section occupies is:

```
... P3i upstream production -> 6a10 -> 6a11 -> [6a12 -> 6a13 -> 6a14 -> 6a15 -> 6a16 -> 6a17] -> P4 -> P5 -> P6
```

That ordering is already dependency-sound for the bulk of this section, because every physical flow
this section reads (outbound, e-commerce, returns, cross-dock, transport, MEIO, production) has
landed by the time 6a12 starts. Nothing here needs to move because it arrived too early.

### 8.2 Resequencing applied

Ten E-items are upstream dependencies of work in this band. The agreed rule (an E-item that is an
upstream dependency of earlier work moves ahead of its dependent) is applied to each. Nothing is
dropped, and nothing already scheduled is delayed past its dependents. Every row states the smallest
part that moves, because moving a whole Phase 6 item to satisfy one dependency would be
resequencing by sledgehammer.

| Item                                                                                       | Default position | Moved to                | Why                                                                                                                                                                                                                                                                                                                                                                                         |
|--------------------------------------------------------------------------------------------|------------------|-------------------------|---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| E16 ATP/CTP order promising                                                                | Phase 6          | Immediately before 6a12 | 6a12's source text requires allocation "against ATP/CTP". The order lifecycle cannot be built without the promise engine it calls. E16 also needs only on-hand, in-transit, scheduled receipts, and the finite scheduler, all of which exist after 3i                                                                                                                                       |
| E14 tariff and trade-policy scenario engine                                                | Phase 6          | Immediately before 6a13 | Already agreed. 6a13's forward-buy-versus-tariff decision and landed-cost sourcing are named requirements of 6a13, not additions                                                                                                                                                                                                                                                            |
| E22 financial twin overlay                                                                 | Phase 6          | Immediately after 6a13  | 6a17's source text says it "graduates the financial twin (E22) from an overlay into a functioning finance department", so E22 precedes it. AP terms need procurement and AR terms need orders, so the earliest sound slot is after 6a13. Placing it here also lets 6a14 payroll and 6a15 patch-window costs be quoted in cash from the moment they exist                                    |
| E23 labor rostering optimization                                                           | Phase 6          | Immediately before 6a14 | Already agreed. 6a14's absenteeism prediction "feeds the rostering optimizer (E23)", and the skills matrix gates the roster                                                                                                                                                                                                                                                                 |
| Decision register (the append-only schema and store from E21, not multi-agent negotiation) | Phase 6          | Immediately before 6a16 | 6a16's executive step ends in "the decision is logged to the governance register". The register is a schema plus an append-only table; E21 later adds role agents and a supervisor on top of it. Splitting the register out is sequencing, not descoping: E21 keeps every remaining part                                                                                                    |
| E30 causal inference                                                                       | Phase 6          | Immediately before 6a16 | Already agreed. Marketing-mix ROI is "measured honestly by the causal layer (E30)" inside 6a16's own text                                                                                                                                                                                                                                                                                   |
| E38 insurance and risk transfer                                                            | Phase 6          | Immediately after 6a17  | Cargo telemetry (3h), TRIR (6a10), and gross profit (6a17) all exist at that point, so E38 is close to free there, and the source invites pulling an E item forward when it is nearly free. This is a decision, not a candidacy: E38 ships in-band as slice 24, section 1 owns it entire, sections 3.8, 4.9, and 6.8 are in-band content, and scenario `s_backoffice_16` is an in-band test |
| E26 accuracy stack, layers a, b, d, and f                                                  | Phase 6          | Immediately before 6a12 | Every tool in section 5.10 executes a query rather than computing in tokens (layer a), resolves metrics through the governed semantic layer (layer b), is schema-constrained (layer d), and is grounding-checked (layer f). Section 7.7 tests all four, so they cannot arrive after the tools do. Layers c, e, and g stay in E26                                                            |
| E27 agent evaluation harness, the runner and the suite file format                         | Phase 6          | Immediately before 6a12 | Every tool ships at least three eval questions with ground truth computed from the simulation. The questions are this section's content; the runner that executes them is E27's, and it has to exist first. Scoring across the whole tool surface stays in E27                                                                                                                              |
| E5 autonomy tiers, the tier enum and the approval gate                                     | Phase 6          | Immediately before 6a15 | Two tools here change state, and an agent-invoked restore drill with no approval gate is a guardrail hole in the section that defines RBAC. In-band this section ships L1 and L2 only. E5 keeps L3 auto-apply and the guardrail evaluator                                                                                                                                                   |
| E43 AI security evals                                                                      | Phase 6          | Not moved               | The four indirect prompt-injection fixtures ship as this section's own tool tests now, so nothing here waits on E43. E43 later adopts them and adds scoring across the whole tool surface                                                                                                                                                                                                   |
| E19 n-tier supplier mapping                                                                | Phase 6          | Not moved               | Nothing in-band asserts a tier-2 number. `SupplierDagPort` returns unavailable, `max_tier2_concentration` is reported as `unenforced`, PRC-005 asserts tier-1 only, and `s_backoffice_05` asserts tier-1 only. The seam is built now so E19 lands as a port implementation                                                                                                                  |

### 8.3 Ordering inside the band

Each package is delivered in slices so that every phase boundary leaves the repo shippable with the
five-minute quickstart intact. A slice is only "done" when its tests, its metrics file, its findings
catalog, and its standalone example all pass.

| Order | Slice                        | Contents                                                                                                                                                                                                  | Depends on                                                                           |
|-------|------------------------------|-----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|--------------------------------------------------------------------------------------|
| 1     | E26 layers a, b, d, f        | Query execution, governed semantic layer, tool schema constraint, grounding checker                                                                                                                       | Historian, schema registry (Phase 0)                                                 |
| 2     | E27 harness                  | Eval runner and the eval-suite file format                                                                                                                                                                | Slice 1                                                                              |
| 3     | E16 promise engine           | ATP cascade, CTP fallback, promise reliability tracking by source                                                                                                                                         | Planning (3d), finite scheduler (3i)                                                 |
| 4     | 6a12-A order core            | Order model, state machine, capture, validation, credit stub, holds, promise integration, arrival process with both shaping ports bound to null implementations                                           | Slice 3, outbound (3e), e-commerce (3g)                                              |
| 5     | 6a12-B allocation            | Three policies, backorders, Jain fairness index, substitution, change and cancellation costs                                                                                                              | Slice 4, inventory availability                                                      |
| 6     | 6a12-C service and customers | Contact generation, promise breach, queue, FCR and visibility, satisfaction, churn, CLV on `BaselineCostToServe`, perfect order, external-failure COPQ classification                                     | Slice 5, returns (3f), QMS (6a11) for COPQ routing                                   |
| 7     | E14 trade engine             | Classification, schedule, overlay apply and merge, landed cost, FTZ, drawback, MEIO port                                                                                                                  | Supplier network (3e), transport (3h)                                                |
| 8     | 6a13-A procure to pay        | Requisition, PO, approval, acknowledgment, receipt, the invoice aggregate, three-way match, payment                                                                                                       | Slice 7, planning reorder signals (3d)                                               |
| 9     | Contract publication         | The `Contract` schema, tier schedule, and `contract.created` published as the standing contract set, with no sourcing engine yet                                                                          | Slice 8                                                                              |
| 10    | 6a13-B sourcing              | RFX, scoring, greedy and exact award strategies, gap report, tier achievement, rebates, renegotiation triggers                                                                                            | Slice 9, supplier scorecards (3e)                                                    |
| 11    | 6a13-C spend and tactics     | Spend taxonomy, maverick detection, savings and avoidance ledgers, forward buy, spot buy, expedite, EOQ validation                                                                                        | Slices 7, 8, 10                                                                      |
| 12    | E22 financial overlay        | AP and AR terms, invoice and payment streams, DSO, DPO, DIO, cash to cash, working capital by echelon, cash forecast, and the FP&A stub that publishes `fpa.reforecast_published` from a fixed driver set | Slices 6 and 8                                                                       |
| 13    | 6a14-A workforce core        | Worker registry, roles, wage table, skills matrix, certifications, eligibility gating, labor ledger, engagement snapshots                                                                                 | Ergonomics (6a10) for strain, slice 9 for the contract set the roster prices against |
| 14    | E23 rostering                | Constraint-solver roster consuming the labor requirement and absence forecast                                                                                                                             | Slice 13                                                                             |
| 15    | 6a14-B lifecycle             | Hiring pipeline, learning curves, cross-training, attrition, absence generation and prediction, peak strategies                                                                                           | Slices 13 and 14                                                                     |
| 16    | 6a15-A ITSM, SRE, telemetry  | CMDB, spans, traces, logs, golden signals, SLOs, derived burn rates, error budgets, incidents, problems, changes, DORA                                                                                    | The twin's own services already exist from P1 onward                                 |
| 17    | E5 tiers                     | Autonomy tier enum and the approval gate for mutating tools                                                                                                                                               | Slice 16 for the actor identity on the approval event                                |
| 18    | 6a15-B security operations   | Synthetic CVE feed, CVSS scoring, exposure model and CVaR patch economics, zones and conduits, detection rules, correlation engine, RBAC, chaos scenarios, backups and drills                             | Slices 16 and 17, twin what-if engine                                                |
| 19    | Decision register            | Append-only decision schema, store, and query surface                                                                                                                                                     | Slice 18 for RBAC on the register                                                    |
| 20    | E30-A causal pipeline        | DoWhy and EconML estimator pipeline, seeded and pinned, run against fixture data with known effects                                                                                                       | Historian, slice 1                                                                   |
| 21    | 6a16-A demand shaping        | Promotions, lift, pull forward, cannibalisation, NPI and Bass, channel mix drift, demand multiplier, promo feature frame, serveability check                                                              | Slice 20, forecaster (3d), slice 4 for the arrival ports                             |
| 22    | E30-B causal scoring         | Scoring the estimator against the ground-truth parameters slice 21 logs on `mkt.lift_realised`                                                                                                            | Slices 20 and 21                                                                     |
| 23    | 6a16-B sales operations      | Pipeline, rep bias, quota effects, FVA ladder                                                                                                                                                             | Slice 21                                                                             |
| 24    | 6a16-C S&OP cycle            | Five steps as events, rough-cut capacity check, consensus, priced gaps, decision packet, scoring, maturity metrics                                                                                        | Slices 12, 19, 21, 23, factory schedule (3i), transport capacity (3h)                |
| 25    | 6a17-A ledger                | Chart of accounts, posting engine, subledgers, statements, closing entries, period close mechanics, gross profit rate                                                                                     | Slice 12                                                                             |
| 26    | 6a17-B costing               | Standard cost roll-up, variance engine, attribution, common-cause gate, inventory valuation, E&O, cycle counts and record accuracy                                                                        | Slice 25, production (3i)                                                            |
| 27    | 6a17-C ABC and FP&A          | Activity pools, cost to serve, `AbcCostToServe` wired behind `CostToServePort`, driver-based budget replacing the slice 12 stub, rolling reforecast, variance bridge                                      | Slice 26, slice 24 for the budget source                                             |
| 28    | 6a17-D governance            | Capex appraisal and post-audit, month-end close as a process, close kaizen, SOD and controls testing                                                                                                      | Slices 25 to 27, authority matrix, RBAC grants from slice 18                         |
| 29    | E38 insurance                | Policies, sublimits, cargo and BI claims, loss recognition, experience rating, TCOR, risk transfer what-if                                                                                                | Slice 28, transport telemetry (3h), TRIR (6a10)                                      |

Four orderings changed, and each is recorded rather than corrected in silence.

**E23 no longer depends on a later slice.** The previous table had slice 10 depending on "slice 11's
contracts published first as stubs", which is a slice depending on its own successor. Contract
publication is now slice 9, ahead of everything that reads a contract, and the roster lands at 14
after the workforce core it staffs. Nothing was descoped to achieve it; one slice was split out and
its dependents follow it.

**The FP&A stub is named in the slice that owns it.** The previous table had the S&OP slice
depending on an "FP&A stub from slice 9" that slice 9's contents did not mention. Slice 12 now lists
it: a reforecast publisher over a fixed driver set, enough for the S&OP cycle to reconcile against.
Slice 27 replaces it with the driver-based budget once activity-based costing exists.

**E30 is split so the generator precedes the scoring.** The previous table ran the whole causal
layer before the ground-truth generator, which scored an estimator against data that did not yet
exist. The pipeline lands at 20 and is developed against fixture data with known effects, the
generator that logs the true decomposition lands at 21, and the scoring lands at 22.

**Customer lifetime value ships in two stages.** Slice 6 computes it through `BaselineCostToServe`,
and slice 27 wires `AbcCostToServe` behind the same port. Every churn event records which one
produced its margin. That is a config change at slice 27 rather than a rewrite, and it is why the
churn model does not wait twenty slices for the costing model.

### 8.4 Phase 0 obligations this section relies on

Nothing here can be retrofitted, which is why these sit in Phase 0 and this section simply consumes
them: C1 determinism and the splittable RNG tree, C2 the sim clock, C3 the schema registry with
additive-only evolution, C5 config validation, C10 monorepo tooling, and A1's package topology. Two
additions this section depends on that are worth naming explicitly at Phase 0 because retrofitting
them is expensive:

1. **The event envelope carries `actor` and `causation_id` from day one.** The audit trail, the SOD
   evidence, the decision register, and the variance drill-down all read them. Adding `actor` later
   means every historical run is unauditable.
2. **Money is integer minor units from the first event that carries an amount.** A float amount
   anywhere upstream poisons the ledger's exactness invariants, and the CI lint that bans float money
   fields has to exist before the first amount is emitted.

### 8.5 What this band leaves for Phase 6

| Later item                                    | What this section leaves ready for it                                                                                                                               |
|-----------------------------------------------|---------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| E18 OT cyberattack drill                      | Zones, conduits, tap, detection engine, incident pipeline, backups with measured restore, error budgets, runbook format                                             |
| E21 collaborative multi-agent with governance | The decision register, RBAC on every tool, and the S&OP decision packet as the first real decision type                                                             |
| E19 n-tier illumination                       | `SupplierDagPort`, the award engine's `max_tier2_concentration` constraint hook, and the consolidation what-if that reports it as `unenforced` until the DAG exists |
| E20 reverse stress testing                    | Service and cash thresholds already defined (SLA penalties, working capital, TCOR) so the optimizer has objectives to break                                         |
| E37 PLM                                       | Standard cost roll-up reads a single effective revision; E37 adds effectivity dates, ECO propagation into open POs and standard costs, and revision in genealogy    |
| E39 ESG and CSRD                              | Social metrics (turnover, training hours) and the GL structure the report aggregates from                                                                           |
| E40 weather                                   | The absence model already accepts a `weather_index` feature and the promo baseline accepts a weather driver                                                         |
| E45 AI operations economics                   | The GL, ABC model, and posting rules that absorb a monthly AI P&L as one more cost pool                                                                             |
| E48 field-grade failure artifacts             | The runbook reference field on `itops.known_error_published` and the CMMS analog linkage                                                                            |

## 9. Open questions

These are genuine ambiguities in the source or genuine cross-section boundaries. None is resolved by
inventing an answer here.

1. **Multi-currency.** The source requires tariffs, imports, cross-border shipments, and CBAM-style
   declarations, all of which imply foreign exchange, but never names FX exposure, translation, or
   revaluation. This section ships `Money` with a currency code and an `FxRatePort` whose default is
   a fixed-rate table, so the seam exists, but the decision on whether the finance layer models FX
   gain and loss, translation of a foreign subsidiary, and hedging is not made here. Version 1 is
   single-currency and config validation rejects any document whose currency differs from
   `finance.functional_currency`, so the ledger invariants hold today. The multi-currency milestone
   is recorded in ROADMAP with its dependency on E14, and what it must still decide is the rate
   selection rule, the rounding point for a translated amount, and whether revaluation posts.

2. **Ownership of the authority matrix.** Procurement (PO approval), IT operations (change approval),
   and finance (journal and capex approval) all need it, and A1 forbids cross-package imports. This
   section treats it as a shared config artifact validated by the config layer with each package
   reading it independently, and `authority_matrix_interpretation_agrees` proves the three packages
   read it identically. If another section defines a governance package that owns it as code, this
   section consumes that instead. The semantics are settled and tested; the ownership is not.

3. **Where the decision register lives.** 6a16 needs it, E5 and E21 extend it. This section assumes it
   is pulled forward as a standalone append-only store with its own schema. Whether it belongs to the
   agent section or to a governance package is a boundary decision for whoever owns E5.

4. **Standard cost revision source before E37.** 6a17 requires standard costing with material usage
   and yield variances, which needs a BOM. 6a9 provides ISA-88 recipes for the factory, but the DC's
   purchased SKUs may have no BOM at all. This section reads `revision_source: bom | recipe` and rolls
   up from whichever exists, treating a purchased SKU's standard as a single material line. Whether
   that is the intended treatment for purchased-for-resale items, or whether they carry landed-cost
   standards instead, is not stated in the source.

5. **Whether the AP exception queue and the service center share a staffing model.** Both are staffed
   office queues. 6a12 explicitly makes service agents "a staffed resource with queues, handle times,
   and their own rostering". 6a13 describes AP exceptions as consuming "real AP departments" but does
   not say they are rostered. This section models both as SimPy resources but routes only service
   agents through E23's roster. If AP handlers are also to be rostered, the config gains a queue and
   the workforce package gains a role, which is additive.

6. **Definition of on-time for the perfect order.** The source names "on time" without saying whether
   it is measured at ship or at delivery, and the two give materially different rates. This section
   makes it a config key (`perfect_order.on_time_basis`) defaulting to delivery, and reports both in
   the capability report. If the intent was ship date, the default flips; the metric definition in
   the semantic layer changes in one place.

7. **Whether cost avoidance appears in any published KPI headline.** The source is explicit that
   savings and avoidance are tracked separately "the way real procurement organizations defend their
   existence", which this section implements as two ledgers with a hard test that avoidance never
   posts to the GL. What is not stated is whether the README's measured headline may ever include an
   avoidance number. The recommendation from this section is that it must not, because an unauditable
   number in a repo whose thesis is auditable numbers is a self-inflicted wound, but that is a
   presentation decision for the README owner.

8. **Severity ordering between security findings and safety findings.** 6a10 establishes that safety
   findings outrank throughput findings by definition. 6a15 produces high-severity security findings
   (unpatched critical, SOD conflict, conduit violation). The relative ordering of a safety finding
   and a security finding at the same nominal severity is not stated anywhere in the source. This
   section assigns severity floors but does not assert a total order across classes. The alarm
   rationalization layer needs one, and it must come from an explicit policy config rather than from
   an accident of enum ordering.

9. **Which supply review mode the shipped demo profile selects.** The computation is specified:
   `RoughCutCapacityCheck` in section 3.6 defines all three modes, `sop.supply_review_mode` selects
   one, `analytic` is the default, and `sop.supply_review_completed` records which mode produced its
   numbers. What is not decided is which mode the shipped demo profile runs. A full finite-capacity
   run of the factory over an 18-period horizon every month is expensive in simulation time, and the
   choice determines whether the S&OP cycle replays inside the viewer's budget. That belongs with
   whoever owns the sim-time budget.

10. **Insurance policy realism boundary.** E38 names cargo claims, business interruption with waiting
    periods, and premiums as functions of loss history and TRIR. It does not say whether to model
    reinsurance, captives, parametric covers, or claims-made versus occurrence triggers. This section
    implements occurrence-triggered indemnity policies with limits, deductibles, coinsurance,
    sublimits, and waiting periods, and stops there. Anything beyond that is a ROADMAP addition rather
    than an assumption.

11. **Provenance of the vendor scorecard weights and the resilience RPO and RTO targets.** The source
    describes both as coming from the author's professional deliverables. Hard rule 2 forbids that.
    Every config block that could carry invented parameters now needs a `provenance: synthetic` key
    and load fails without it: `sourcing`, `tactics.spot_buy`, `attrition.coefficients`,
    `vulnerability`, `breach_impact`, `backup`, `promotions.lift`, `channel_mix`,
    `bill_of_resource.yaml`, the insurance rating tables, and `claim_process`. A schema check proves
    the key is present; it cannot prove the values behind it were re-derived from public practice.
    Whoever populates the shipped configs has to confirm that, and the capability report has to say
    who did.

12. **Whether HS codes and country codes may be plausible real values.** This section uses the public
    HS nomenclature structure with synthetic codes and ISO 3166 country codes, with a header comment
    stating every rate is invented. Real HS chapter numbers are public reference data rather than
    proprietary information, so using them appears safe, but a reviewer who wants zero resemblance to
    any real tariff schedule may prefer entirely fictional codes. The choice affects only readability.

13. **The false alarm rate of the full Nelson rule set on an estimated-limits I-MR chart.** VG-FIN-07
    validates the common-cause gate against the one rate the NIST/SEMATECH e-Handbook publishes:
    0.0027 for a single point outside 3-sigma limits, with the limits supplied rather than estimated.
    The shipped configuration runs several Nelson rules on limits estimated from the same data, and
    that combined rate has no published value and no closed form. Getting one needs a Markov-chain
    average run length computation for the specific rule set, or a large simulation whose result is
    this repository's own number and so cannot be a reference for itself under D-11. In the meantime
    the shipped rule set's rate is measured, recorded with its method and Monte Carlo standard error,
    and used as a regression baseline rather than as a validated statistic. Promoting it needs an
    external published derivation for the exact rule set, or an accepted argument that a
    per-rule-1-only gate is enough to validate the classifier.

14. **Whether an annual metric can have a control chart in any demoable run.** Section 7.4 assigns
    `total_cost_of_risk` an I-MR chart at quarterly cadence. Twenty points is five years of sim
    time, which is beyond even the 36-month long-horizon profile. The chart is defined and its limits
    are reported as provisional until the point count is reached. The options are a longer profile
    that costs sim-time budget, a shorter TCOR period that changes the accounting meaning, or
    accepting that some charts are defined for production use and are never exercised in a demo run.
    This section does not pick one, because the choice belongs with whoever owns the sim-time budget
    and the demo story.

15. **Whether the OpenStax worked examples may be encoded at all.** VG-FIN-04, VG-FIN-09, and
    VG-FIN-10 check the variance, inventory, and depreciation implementations against worked examples
    in the OpenStax _Principles of Accounting_ volumes. Both volumes are licensed
    CC BY-NC-SA, verified from the OpenStax book metadata API on 2026-08-09, not CC BY as this
    section previously stated. The non-commercial term conflicts with this repository's commercial
    license option and the share-alike term would reach a derivative work, so the fixtures encode the
    numeric inputs and the published answers with a citation and reproduce no prose, table, or layout.
    Individual facts and figures are not themselves copyrightable, which is the basis for that
    treatment, but it is the same class of question D-14 settled for PM4Py and it deserves the same
    treatment: the owner's own legal read before release. If the answer is no, the gates need a
    differently licensed source of worked examples, and they are not dropped.
