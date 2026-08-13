---
title: "Upstream production, QMS and compliance, PLM, traceability"
description: Implementation contract for the factory, the quality system, product lifecycle, the genealogy ledger, and the standard-work corpus, with a named test behind every claim.
topic_type: reference
audience: contributors
---

# Upstream production, QMS and compliance, PLM, traceability

Design spec section. Implementation contract. Everything here is testable. Every gate that checks
an implementation against an outside source names that source with its edition and locator, the
tolerance the test asserts, the noise floor the tolerance sits above, and the observation that
would falsify it (doctrine D-11).

Doctrine rulings applied in this section, with the subsections that apply them:

| Ruling | What it settles here                                                                        | Applied in                      |
|--------|---------------------------------------------------------------------------------------------|---------------------------------|
| D-01   | Wall clock lives in the run provenance sidecar, never in the hashed tape                    | 3.3, 3.4, 4, 5.13, 5.15, 5.18   |
| D-02   | The four legal wall-clock readers, and the ban on wall clock in payloads                    | 4, 5.15, 5.18, 7.3              |
| D-03   | Every emitted collection is ordered by a declared key, and every tie breaks on a stated key | 2.2, 3, 4, 5.2, 5.15, 5.20, 7.2 |
| D-04   | Solvers and learned models stop on a deterministic budget, never on wall time               | 2.6, 5.5, 5.20, 5.21, 6.1       |
| D-05   | Two determinism tiers, byte-identical on a pinned platform and value-equivalent across      | 4, 5.18, 7.2, 7.3               |
| D-07   | The envelope carries `producer_id`; sequence density is per run and per producer            | 4                               |
| D-09   | One owning package per public symbol, and declared layering with no sibling imports         | 2, 2.1, 2.4, 3.1                |
| D-10   | Heavy dependencies are optional extras behind structural protocols                          | 2, 2.2, 2.6                     |
| D-11   | Every reference gate carries an external published source, a tolerance, a noise floor       | 7.3                             |
| D-12   | Every test states the observation that would fail it                                        | 7.2, 7.3                        |
| D-13   | Every test tier fits the job budget, and the arithmetic is itself asserted                  | 7                               |
| D-14   | Process mining is `twinflow-procmine`, written here under Apache-2.0, not PM4Py             | 5.7, 5.21                       |

---

## 1. Scope

This section is the implementation contract for the following numbered requirements from the
twinflow prompt.

| Requirement | Title                                                  | Coverage in this section                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                             |
|-------------|--------------------------------------------------------|----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| 6a9         | Upstream production and manufacturing                  | Full. Hybrid batch-plus-discrete factory, ISA-88 recipes, golden-batch scoring, PackML machine states, equipment-level OEE with six-big-losses decomposition, changeover and SMED, finite-capacity scheduling with sequence-dependent setups feeding the DC inbound schedule, push/pull/CONWIP/DBR with kanban card counts, takt discipline and level loading between stages (5.22), first-pass yield and scrap through lot genealogy, in-line SPC per stage, schedule-versus-actual divergence as a finding class (5.23), production-twin recalibration from telemetry (5.24), the make-versus-buffer what-if (5.25), and the one-point-of-FPY valuation experiment |
| 6a11        | QMS and compliance auditing                            | Full. Auto-raised NCRs with dedupe, CAPA lifecycle with statistical effectiveness verification and automatic reopen, MIL-STD-105E / ANSI-ASQ-Z1.4-class acceptance sampling with switching rules, CoA generation, COPQ four-bucket classification, append-only audit trail with agent attribution, audit checklists as versioned code mapped to ISO 9001-class clauses, layered process audits, timed mock recall drill returning full blast radius                                                                                                                                                                                                                  |
| 6b          | Business-system loop                                   | Full. ERP stub issuing ASN-style expected receipts, three-way reconciliation against observed RFID and CV counts with discrepancy-cause classification, mini CMMS turning PdM findings into prioritized work orders with twin-quantified cost of deferral                                                                                                                                                                                                                                                                                                                                                                                                            |
| E10         | Digital product passport traceability                  | Full. DPP data model over the genealogy graph, GS1 Digital Link identifiers, role-scoped access views, ESPR framing, honest conformance limitation                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                   |
| E35         | Tamper-evident traceability ledger                     | Full. RFC 6962 Merkle tree, hash-chained blocks, RFC 8785 canonicalisation, Ed25519 multi-party signatures with per-event-type threshold policy, GS1 EPCIS 2.0 event emission, third-party verifier that does not trust the DC database, honest trust-model statement                                                                                                                                                                                                                                                                                                                                                                                                |
| E37         | PLM and engineering change management                  | Full. Versioned items, BOMs and ISA-88 recipes, ECR/ECO/ECN lifecycle, effectivity by date/lot/serial, use-up versus scrap disposition, propagation into open POs and standard costs, as-built revision recorded in genealogy so recall scopes by revision                                                                                                                                                                                                                                                                                                                                                                                                           |
| E24         | Telemetry-grounded generative SOPs                     | Full. Structured SOP drafting from golden-batch profiles, CAPA history, alarm rationalization records, mined process variants and measured standard work; grounding gate on every number; document control lifecycle; simulated adherence so SOP quality is a measurable variable                                                                                                                                                                                                                                                                                                                                                                                    |
| E8          | SOP grounding via retrieval with clause-level citation | Full. Clause-addressable SOP corpus, hybrid retrieval with structural eligibility filter, citation contract, time-travel citation against the revision effective at violation time, abstention path, ground-truth eval set                                                                                                                                                                                                                                                                                                                                                                                                                                           |

Requirements this section depends on but does not own, with the owning section named so the seam is
explicit:

- Component 5 (LSS engine) owns every statistic. This section emits measurements and consumes
  findings. It never implements a control chart, a capability index, a hypothesis test, or a power
  calculation.
- Component 3 (fleet and predictive maintenance) owns time-to-threshold estimation. This section
  consumes those estimates and turns them into work orders.
- Component 4 (CV auditing) owns violation detection. This section owns the SOP clause the
  violation is cited against.
- Component 6a2 (supplier network) owns supplier reliability profiles. This section owns the
  inbound lot acceptance decision and the genealogy edge back to the supplier lot.
- Component 6a17 (finance) owns the general ledger. This section classifies quality cost and emits
  postings; it does not post them.
- Component 7 (agent) owns tool exposure and answer composition. This section owns the tools'
  return payloads.
- The dashboard section owns alarm rationalization: severity ranking, grouping and shelving. This
  section reads `shelve_policy` and `dedupe_key` from the finding catalog the back-office section
  declares, and applies them at NCR intake (5.9). It does not define a second shelving model.
- C1, C2, C3, C5, C10 and A1 are contracts this section is built inside, not requirements it owns.

Two facts about the repository govern several choices below and are stated once here. The
repository ships under Apache-2.0 with a commercial option, so every vendored artifact and every
runtime dependency must be Apache-2.0 compatible (2.8). All data is synthetic, generated by the
twin, so every ground-truth claim in section 7 is a claim about the twin's own injected truth and
is labeled as such.

Requirements this section reaches through a named protocol seam, with the pre-arrival binding
stated so nothing here is blocked on a later phase. Section 8.7 records the resequencing each seam
implies.

| Later item                        | Protocol seam           | Binding before the item lands                                                                                                                          |
|-----------------------------------|-------------------------|--------------------------------------------------------------------------------------------------------------------------------------------------------|
| E26(b) governed metrics           | `MetricOracle`          | The metrics subset this section names moves to 6a11 (8.7); free-text metrics are rejected at load from day one                                         |
| E26(f) grounding checker          | `GroundingOracle`       | The grounding checker moves to 6a11 (8.7) because the audit trail's first entry needs query result ids                                                 |
| E5 autonomy tiers                 | `AutonomyOracle`        | `Actor.autonomy_tier` is a Phase 0 field; before E5 the CoA rule keys on `actor.kind`, not on tier value                                               |
| E23 labor rostering               | `AuditorAvailability`   | Bound to the shift calendar of `production.calendar` until E23 replaces the binding                                                                    |
| E43 model registry                | `ModelRefResolver`      | Bound to a pinned model artifact digest declared in config until E43 replaces the binding                                                              |
| E46 RF read zones                 | `ReadZoneOracle`        | Reconciliation raises `portal_read_anomaly`; E46 refines it into read-zone and cross-read geometry findings                                            |
| E48 failure runbooks              | `RunbookResolver`       | `runbook_ref` is nullable and renders as "no runbook published" until E48                                                                              |
| 6a17 authority matrix             | `AuthorityOracle`       | Bound to `authority_matrix.yaml` in this section's config until 6a17 owns it                                                                           |
| E9 optimization engine            | `StudyRunner`           | The Optuna study for scheduling moves to 3i (8.7); the seam is the same one E9 later reuses                                                            |
| E17 carbon, 6a4 disposition       | passport attribute maps | An unpopulated passport attribute group renders as `not_yet_sourced` with the sourcing item named (5.17)                                               |
| E43 dense retrieval, E24 drafting | `Inference`             | Every learned model reached from this section goes through the kernel `Inference` port, bound to a recorded-response adapter in simulation mode (D-04) |

---

## 2. Packages

Seven independently installable packages: `twinflow-production`, `twinflow-genealogy`,
`twinflow-ledger`, `twinflow-quality`, `twinflow-plm`, `twinflow-sop` and `twinflow-bizsys`. Each
has its own `README.md`, its own test suite, its own PyPI name, and a documented "use just this
part" story for the A1 table.

The inter-package rule is the one the foundations section already declares, restated here so this
section cannot drift from it (D-09). Sibling domain packages do not import each other at all. They
communicate through versioned events validated against `/schemas` (C3), and, where a synchronous
answer is genuinely required, through a narrow structural protocol declared in `twinflow-kernel`
and bound at the composition root. The protocols this section uses are `StatisticalOracle`,
`GenealogyOracle`, `LedgerWriter`, `AuthorityOracle`, `MetricOracle`, `GroundingOracle`,
`AutonomyOracle`, `AuditorAvailability`, `ModelRefResolver`, `ReadZoneOracle`, `RunbookResolver`,
`StudyRunner` and `Inference`. A protocol is typed against the schema registry's value types, so
binding one never drags a heavy dependency downward (D-10).

Three consequences follow, and each is a test rather than a promise.

1. `twinflow-quality` does not import `twinflow-genealogy`, `twinflow-ledger` or the LSS engine. It
   reads genealogy through `GenealogyOracle`, writes ledger entries through `LedgerWriter`, and asks
   for hypothesis tests and power calculations through `StatisticalOracle`.
2. `twinflow-genealogy` does not import `twinflow-ledger`. It emits `genealogy.epcis.emitted` and
   the ledger subscribes.
3. Shared value types that both sides need (`Quantity`, `SimTime`, `NodeKind`, `EdgeKind`,
   `TraceScope` and its variants, `SubjectRef`, `Severity`) are owned by `twinflow-schemas` and
   re-exported by the package that reads best, with the re-export declared rather than inferred
   (D-09). No type is defined twice.

The seven packages are registered as domain packages in `[tool.twinflow.layers]` in the root
`pyproject.toml`, which is the table the foundations section's layering contract reads, so the
declared layering and the enforcing gate cannot disagree. `test_section_packages_are_independent`
asserts no import edge exists between any two of the seven, and
`test_section_packages_declare_their_layer` asserts each appears in that table.

All seven depend on `twinflow-kernel` (the `Clock`, RNG, `Network`, `EventBus`, `Storage` and
`Inference` interfaces that make dual-mode deterministic simulation testing possible),
`twinflow-schemas` (registry and validation), and `twinflow-config` (C5 loading and validation).
Those three are Phase 0 and are not described here.

### 2.1 `twinflow-production` (import `twinflow_production`)

Purpose: the upstream factory. A hybrid process-plus-discrete plant model, its recipes, its machine
state machines, its scheduler, and its flow control.

Take-one-brick story: a manufacturing engineer who wants only OEE-with-six-big-losses from a stream
of machine state events, or only a sequence-dependent-setup finite-capacity scheduler, installs this
package alone. Both subsystems accept plain event iterables and a config dict; neither requires the
rest of twinflow.

Public API surface:

```python
# twinflow_production/__init__.py
from twinflow_production.plant import Plant, build_plant
from twinflow_production.recipe import MasterRecipe, ControlRecipe, load_recipes
from twinflow_production.batch import BatchExecutor, BatchRecord
from twinflow_production.golden import GoldenProfile, score_batch, GoldenScore
from twinflow_production.states import MachineState, StateMachine, StateTransition
from twinflow_production.oee import (
    OeeWindow, compute_oee, decompose_losses, SixBigLosses, LossBucket,
)
from twinflow_production.changeover import Changeover, SmedAnalysis, analyse_smed
from twinflow_production.scheduling import (
    Job, SchedMachine, SetupMatrix, Schedule, schedule_atcs, evaluate_schedule,
)
from twinflow_production.flow import FlowController, KanbanLoop, kanban_card_count
from twinflow_production.takt import TaktProfile, compute_takt, LevellingReport, level_load
from twinflow_production.yield_ import FirstPassYield, RolledThroughputYield, compute_fpy, compute_rty
from twinflow_production.adherence import ScheduleAdherence, bucket_adherence, attribute_causes
from twinflow_production.recalibrate import (
    RecalibrationPlan, RecalibrationResult, recalibrate_from_telemetry,
)
```

Dependencies: `twinflow-kernel`, `twinflow-schemas`, `twinflow-config`, `numpy`.

It imports no other package in this section, in either direction. It publishes
`production.measurement.recorded` and the LSS engine subscribes; it publishes
`genealogy.transformation` and the genealogy package subscribes. Both directions are subscriptions
because the rule is one rule (D-09). So the factory can be adopted without the statistics engine
and without the genealogy graph, and neither is blocked on the factory.

The scheduling entity is named `SchedMachine` and not `Machine`. `twinflow_production.Machine` is
the domain machine of 3.1, with PackML state, cycle time and failure model; the scheduler's view
carries eligibility sets and a setup-matrix reference and nothing else. Two types with one exported
name in one namespace is the defect D-09 exists to prevent, so the scheduling view is renamed
rather than shadowed. `test_public_names_are_unique_per_package` asserts every name in `__all__`
resolves to exactly one definition.

### 2.2 `twinflow-genealogy` (import `twinflow_genealogy`)

Purpose: the lot and unit genealogy graph, its traversal, its EPCIS 2.0 projection, and the digital
product passport built on top of it.

Take-one-brick story: a traceability engineer installs this alone, feeds it transformation and
aggregation events from their own system, and gets forward and backward closure plus an EPCIS 2.0
document stream and a DPP document generator.

Public API surface:

```python
from twinflow_genealogy.graph import GenealogyGraph, Node, Edge, NodeKind, EdgeKind
from twinflow_genealogy.trace import (
    forward_closure, backward_closure, TraceResult, TraceScope,
    LotScope, BatchScope, SupplierLotScope, RevisionScope, EquipmentContactScope,
)
from twinflow_genealogy.epcis import (
    ObjectEvent, AggregationEvent, TransactionEvent, TransformationEvent, AssociationEvent,
    to_epcis_document, from_epcis_document,
)
from twinflow_genealogy.ids import sgtin, lgtin, sscc, gln, digital_link_uri
from twinflow_genealogy.dpp import ProductPassport, build_passport, PassportAudience, render_passport
```

Dependencies: `twinflow-kernel`, `twinflow-schemas`, `twinflow-config`, `networkx`
(graph storage in simulation mode; a Postgres-backed adjacency store in production mode behind the
same `GenealogyStore` protocol), `jsonschema`.

Traversal order is declared, never inherited from the graph library (D-03). Every closure walk is a
breadth-first walk whose frontier is sorted by `(sim_time, node_id)` before expansion, and every
returned collection is sorted by `node_id`. Two runs of the same traversal on the same graph
emit the same order, and `test_traversal_order_is_declared` shuffles the insertion order
of an identical graph and asserts the walk output is unchanged.

### 2.3 `twinflow-ledger` (import `twinflow_ledger`)

Purpose: a generic append-only, hash-chained, Merkle-committed, multi-party-signed event ledger with
standalone verification. Domain-agnostic by design.

Take-one-brick story: anyone who wants an append-only audit log with inclusion and consistency
proofs and multi-party signatures installs it alone and feeds it any JSON-serializable records. It
names no factory, quality or traceability concept anywhere in its public API, which is what makes
the claim checkable: `test_ledger_api_is_domain_free` asserts no symbol in `__all__` and no field
name in any exported model matches the section's domain vocabulary.

Public API surface:

```python
from twinflow_ledger.canonical import canonicalise            # RFC 8785 JCS
from twinflow_ledger.merkle import (
    merkle_tree_hash, inclusion_proof, verify_inclusion,      # RFC 6962
    consistency_proof, verify_consistency,
)
from twinflow_ledger.chain import Ledger, Block, BlockHeader, append, seal, verify_chain
from twinflow_ledger.signing import (
    Party, KeyRing, derive_keyring, sign_entry, verify_entry, SignaturePolicy,
)
from twinflow_ledger.verifier import verify_record_standalone, VerificationReport
```

Dependencies: `twinflow-kernel` (clock and seed only), `cryptography` (Ed25519 per RFC 8032).
It depends on nothing else in twinflow. `verify_record_standalone` in particular imports only
`twinflow_ledger` so it can be handed to a counterparty as a single-file verifier.

### 2.4 `twinflow-quality` (import `twinflow_quality`)

Purpose: the QMS. NCR and CAPA workflows, acceptance sampling, CoA, COPQ, audit trail, audit
checklists, layered process audits, recall drill.

Take-one-brick story: a quality manager who wants only ANSI/ASQ-Z1.4-class acceptance sampling with
switching rules as code, or only a CAPA workflow whose effectiveness verification is a real
statistical test rather than a checkbox, installs this alone.

Public API surface:

```python
from twinflow_quality.ncr import Ncr, NcrRule, NcrEngine, DedupeKey
from twinflow_quality.capa import (
    Capa, CapaState, VerificationPlan, EffectivenessVerdict, CapaEngine,
)
from twinflow_quality.sampling import (
    SamplingPlan, InspectionLevel, InspectionSeverity, SwitchingState, SwitchingRuleset,
    select_plan, inspect_lot, oc_curve, aoq_curve, ati,
)
from twinflow_quality.coa import CertificateOfAnalysis, issue_coa, render_coa
from twinflow_quality.copq import CopqClass, CopqPosting, classify, CopqReport
from twinflow_quality.audit_trail import AuditTrail, AuditEntry, Actor, append_only_writer
from twinflow_quality.checklists import (
    Checklist, ChecklistQuestion, ClauseRef, run_checklist, ChecklistResult,
)
from twinflow_quality.lpa import LpaLayer, LpaSchedule, LpaExecution, schedule_lpa
from twinflow_quality.recall import RecallDrill, run_recall_drill, RecallReadinessReport
```

Dependencies: `twinflow-kernel`, `twinflow-schemas`, `twinflow-config`. Nothing else from this
section and nothing from the LSS engine. Genealogy reads arrive through `GenealogyOracle`, ledger
writes through `LedgerWriter`, and hypothesis tests and power calculations through
`StatisticalOracle`. All three protocols are declared in `twinflow-kernel` and bound at the
composition root, so `pip install twinflow-quality` pulls three Phase 0 packages and no more, and a
test double satisfies each protocol in the unit suite.

### 2.5 `twinflow-plm` (import `twinflow_plm`)

Purpose: items, revisions, BOMs, routings, recipe versioning, ECR/ECO/ECN, effectivity resolution,
disposition, change propagation, standard cost rollup.

Take-one-brick story: anyone building a system where parts change over time installs this for its
effectivity resolver and its as-built-versus-as-designed discipline.

Public API surface:

```python
from twinflow_plm.item import Item, Revision, Interchangeability
from twinflow_plm.bom import Bom, BomLine, explode, where_used, rollup_standard_cost
from twinflow_plm.routing import Routing, Operation
from twinflow_plm.change import Ecr, Eco, Ecn, EcoState, Disposition, DispositionDecision
from twinflow_plm.effectivity import (
    Effectivity, DateEffectivity, LotEffectivity, SerialEffectivity, resolve_revision,
)
from twinflow_plm.propagation import propagate_eco, PropagationPlan, PropagationImpact
```

Dependencies: `twinflow-kernel`, `twinflow-schemas`, `twinflow-config`. It publishes change events
that procurement (6a13) and finance (6a17) consume; it does not import them.

### 2.6 `twinflow-sop` (import `twinflow_sop`)

Purpose: the standard-work corpus. Clause-addressable parsing, hybrid retrieval with structural
filtering, the citation contract, document control, generative drafting, and the adherence model.

Take-one-brick story: an AI team that wants clause-level grounded citation over a governed document
corpus, with a measured wrong-clause rate and an abstention path, installs this alone.

Public API surface:

```python
from twinflow_sop.corpus import SopDocument, SopClause, ClauseIndex, parse_sop, build_index
from twinflow_sop.retrieval import (
    RetrievalConfig, retrieve_clauses, Citation, CitationResult, Abstention,
)
from twinflow_sop.control import DocumentState, SopRevision, publish_revision, effective_at
from twinflow_sop.generate import EvidenceBundle, draft_sop, SopDraft, GroundingReport
from twinflow_sop.adherence import AdherenceModel, adherence_probability, ClarityScore
from twinflow_sop.training import TrainingRecord, is_trained
```

Dependencies: `twinflow-kernel`, `twinflow-schemas`, `twinflow-config`, `rank-bm25`.
`sentence-transformers` is an optional extra `[dense]`, never a core dependency (D-10). BM25-only
mode is the default, so the package installs and runs with no model download and no API key, per
the fully-local constraint.

The dense encoder is a learned model, so it reaches the simulation only through the kernel
`Inference` port (D-04). Under `[dense]` the port is bound to a local encoder pinned by model
artifact digest, single-threaded, with deterministic kernels enabled and the encoder seed fixed;
the digest is recorded in the run manifest's hashed core. In simulation mode the port is bound to a
recorded-response adapter, so replaying a run never re-runs the encoder. `RetrievalConfig` carries
the resolved `model_digest`, and a retrieval run whose digest differs from the recorded one fails
rather than silently ranking differently.

### 2.7 `twinflow-bizsys` (import `twinflow_bizsys`)

Purpose: the business-system loop of 6b. An ERP stub that issues ASN-style expected receipts, the
three-way reconciler that classifies what actually arrived, and the mini CMMS that turns predictive
maintenance findings into prioritized work orders with a twin-quantified cost of deferral.

Take-one-brick story: a systems integrator who wants only the three-way reconciliation classifier,
fed expected, RFID-observed and vision-observed counts, installs this alone and gets a typed
variance class with a confidence per line.

Public API surface:

```python
from twinflow_bizsys.erp import Asn, AsnLine, PackHierarchy, publish_expected_receipt
from twinflow_bizsys.reconcile import (
    ThreeWayCounts, VarianceClass, CauseClass, ReconciliationLine, reconcile_asn,
)
from twinflow_bizsys.inventory import BookLedger, adjust_book
from twinflow_bizsys.cmms import (
    WorkOrder, WorkOrderKind, priority_score, DeferralCurve, estimate_deferral_cost,
)
```

Dependencies: `twinflow-kernel`, `twinflow-schemas`, `twinflow-config`, `numpy`. It imports no
other package in this section. It reads predictive-maintenance estimates from
`pdm.threshold_crossing.estimated`, reads genealogy through `GenealogyOracle` when a receipt has to
attach to a supplier lot node, and runs paired what-if replications through `StudyRunner`.

This is a separate distribution rather than a subpackage of `twinflow-quality`. A1's "take one
brick" table routes an ERP-and-CMMS reader to one install line, and burying an ERP stub inside a
QMS package would make that line wrong.

### 2.8 Dependency licenses

The repository ships under Apache-2.0 with a commercial option, so every runtime dependency named
above must be compatible with both. The versions and licenses below were read from the PyPI JSON
API on 2026-08-10 (HTTP 200 for each) and are the versions the lockfile pins.

| Package                 | Version | License declared on the package index              |
|-------------------------|---------|----------------------------------------------------|
| `numpy`                 | 2.5.2   | BSD-3-Clause AND 0BSD AND MIT AND Zlib AND CC0-1.0 |
| `networkx`              | 3.6.1   | BSD-3-Clause                                       |
| `jsonschema`            | 4.26.0  | MIT                                                |
| `cryptography`          | 50.0.0  | Apache-2.0 OR BSD-3-Clause                         |
| `rank-bm25`             | 0.2.2   | Apache-2.0                                         |
| `sentence-transformers` | 5.7.0   | Apache-2.0                                         |
| `optuna`                | 4.9.0   | MIT                                                |
| `pydantic`              | 2.13.4  | MIT                                                |

No dependency in this section is copyleft, and none is AGPL. The process-mining capability this
section consumes runs on `twinflow-procmine`, the Apache-2.0 miner written in this repository,
because PM4Py is AGPL-3.0 and serving a dashboard, an MCP server and an HTTP API would place the
whole work under AGPL (D-14). `LICENSE-1` re-reads every declared license in CI against the
Apache-2.0-compatible allowlist (C11) and fails on a change, so a dependency that relicenses
between releases is caught at the next build rather than at the next audit.

---

## 3. Domain model

Field types are Python type annotations. Every entity is a Pydantic model in the implementation so
C5 config validation and E26(d) structured outputs come from the same declarations.

### 3.1 Production entities

**`Plant`**

| Field           | Type                 | Notes                                                                                           |
|-----------------|----------------------|-------------------------------------------------------------------------------------------------|
| `plant_id`      | `str`                | ISA-95 Site or Area identifier, used as the UNS path segment                                    |
| `process_cells` | `list[ProcessCell]`  | ISA-88 physical model, batch side                                                               |
| `work_centers`  | `list[WorkCenter]`   | discrete side                                                                                   |
| `stage_graph`   | `DiGraph[StageId]`   | must be a DAG with exactly one designated handoff edge from the batch side to the discrete side |
| `calendar`      | `ProductionCalendar` | shift patterns, planned downtime, holidays                                                      |

Invariants: `stage_graph` is acyclic; every `WorkCenter` and `ProcessCell` appears in exactly one
node; the batch-to-discrete handoff edge exists and is unique (the hybrid requirement is structural,
not decorative, so it is enforced at config load).

**`ProcessCell` / `Unit` / `EquipmentModule`** follow the ISA-88 physical model. A `Unit` is the
thing a batch occupies exclusively for the duration of a unit procedure.

**`WorkCenter`** (discrete): `work_center_id`, `machines: list[Machine]`, `queue_policy`,
`buffer_capacity: int`.

**`Machine`**

| Field                 | Type           | Notes                                                                             |
|-----------------------|----------------|-----------------------------------------------------------------------------------|
| `machine_id`          | `str`          | also the device-registry asset id, so PdM telemetry attaches without new plumbing |
| `state`               | `MachineState` | PackML state, see 5.3                                                             |
| `mode`                | `MachineMode`  | `producing`, `maintenance`, `manual`                                              |
| `ideal_cycle_time_s`  | `float`        | per unit, per product family; the denominator of Performance                      |
| `setup_matrix_ref`    | `str`          | key into the sequence-dependent setup matrix                                      |
| `failure_model_ref`   | `str`          | key into the reliability catalog (shared with the DC's conveyors)                 |
| `startup_scrap_units` | `int`          | drives the startup/yield loss bucket                                              |

Invariants: `ideal_cycle_time_s > 0`; a machine is in exactly one state at any sim-time; state
history is a total, gap-free partition of the run's sim-time.

**`MasterRecipe`** (ISA-88)

| Field                     | Type                         | Notes                                                                                                       |
|---------------------------|------------------------------|-------------------------------------------------------------------------------------------------------------|
| `recipe_id`               | `str`                        |                                                                                                             |
| `revision`                | `Revision`                   | PLM-controlled, see 3.5                                                                                     |
| `header`                  | `RecipeHeader`               | author, effective range, approval refs                                                                      |
| `formula`                 | `Formula`                    | `inputs: list[MaterialSpec]`, `outputs: list[MaterialSpec]`, `process_parameters: dict[str, ParameterSpec]` |
| `equipment_requirements`  | `list[EquipmentRequirement]` | constrains which `Unit` can run it                                                                          |
| `procedure`               | `Procedure`                  | Procedure -> UnitProcedure -> Operation -> Phase                                                            |
| `expected_yield_pct`      | `float`                      | mean, used in the material-balance tolerance                                                                |
| `expected_yield_loss_pct` | `float`                      | declared physical loss (evaporation, moisture, purge)                                                       |

Invariants: the procedure tree has exactly four levels; every `Phase` names a `Unit` capability that
at least one configured `Unit` provides; `expected_yield_pct + expected_yield_loss_pct <= 100`.

**`ControlRecipe`**: a `MasterRecipe` bound to a specific `Unit`, a specific batch size, and a
specific set of input lots. It is the as-built artifact and is immutable once the batch starts.

**`BatchRecord`**

| Field            | Type                      | Notes                                                                               |
|------------------|---------------------------|-------------------------------------------------------------------------------------|
| `batch_id`       | `str`                     |                                                                                     |
| `control_recipe` | `ControlRecipe`           | as-built, including the recipe revision                                             |
| `phase_log`      | `list[PhaseExecution]`    | start, end, unit, operator, hold events                                             |
| `profiles`       | `dict[CppId, TimeSeries]` | one series per critical process parameter, inserted in sorted `cpp_id` order (D-03) |
| `outputs`        | `list[LotQuantity]`       | good, rework, scrap by disposition                                                  |
| `golden_score`   | `GoldenScore \            | None`                                                                               |

Invariant `material_conservation` (see 7.2) holds over every `BatchRecord`.

**`GoldenProfile`**

| Field                | Type          | Notes                                                                  |
|----------------------|---------------|------------------------------------------------------------------------|
| `recipe_id`          | `str`         |                                                                        |
| `recipe_revision`    | `str`         | a golden profile is per recipe revision, never shared across revisions |
| `phase_id`           | `str`         |                                                                        |
| `cpp_id`             | `str`         | critical process parameter                                             |
| `grid`               | `int`         | number of normalized sample points, default 64                         |
| `mean`               | `list[float]` | length `grid`                                                          |
| `lower`              | `list[float]` | envelope                                                               |
| `upper`              | `list[float]` | envelope                                                               |
| `weight`             | `float`       | contribution to the aggregate score                                    |
| `built_from`         | `list[str]`   | batch ids of the qualifying batches, recorded for auditability         |
| `qualification_rule` | `str`         | the predicate that made a batch qualifying                             |

Invariants: `lower[i] <= mean[i] <= upper[i]` for all i; `built_from` has at least
`golden.min_qualifying_batches` entries; a profile whose `built_from` batches were themselves scored
against an earlier profile records that lineage (no circular bootstrapping without a recorded root).

**`Changeover`**: `changeover_id`, `machine_id`, `from_product_family`, `to_product_family`,
`started_at`, `ended_at`, `elements: list[ChangeoverElement]`.

**`ChangeoverElement`**: `name`, `kind: Literal["internal","external"]`, `duration_s`,
`value_added: bool`, `smed_stage: Literal["as_is","converted","streamlined"]`.

Invariant: the sum of internal element durations equals machine down-for-changeover time exactly;
external elements never overlap machine-down time in a compliant configuration, and a violation of
that is itself a finding (`smed_external_during_downtime`).

**`Job`, `SchedMachine`, `SetupMatrix`, `Schedule`**: see 5.5. `SchedMachine` is the scheduler's
view and carries an eligibility set and a setup-matrix reference; `Machine` above is the domain
machine. The two are never the same type and never share an exported name (D-09).

**`KanbanLoop`**: `loop_id`, `from_stage`, `to_stage`, `cards: int`, `container_size: int`,
`replenishment_lead_time_s: float`, `safety_factor: float`.

Invariant `kanban_wip_bound`: WIP in the loop never exceeds `cards * container_size`.

### 3.2 Genealogy entities

**`Node`**

| Field           | Type                   | Notes                                                                                                                                                                  |
|-----------------|------------------------|------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| `node_id`       | `str`                  | EPC URI where one applies, otherwise an internal id                                                                                                                    |
| `kind`          | `NodeKind`             | `raw_lot`, `batch`, `wip_lot`, `finished_lot`, `serial_unit`, `pallet`, `carton`, `shipment`                                                                           |
| `item_id`       | `str`                  | PLM item                                                                                                                                                               |
| `item_revision` | `str`                  | **as-built**, populated from Phase 0 onward even before E37 ships                                                                                                      |
| `quantity`      | `Quantity`             | value plus UOM                                                                                                                                                         |
| `created_at`    | `SimTime`              |                                                                                                                                                                        |
| `attributes`    | `dict[str, JsonValue]` | supplier_id, country_of_origin, hs_code, expiry, carbon_kgco2e, all reserved by their owning sections; keys inserted in sorted order so serialization is stable (D-03) |

**`Edge`**

| Field          | Type       | Notes                                                                  |
|----------------|------------|------------------------------------------------------------------------|
| `edge_id`      | `str`      |                                                                        |
| `kind`         | `EdgeKind` | `consumed_by`, `contains`, `custody_of`, `observed_at`, `derived_from` |
| `parent`       | `str`      | node id                                                                |
| `child`        | `str`      | node id                                                                |
| `quantity`     | `Quantity` | for `consumed_by`, the consumed amount                                 |
| `at`           | `SimTime`  |                                                                        |
| `equipment_id` | `str \     | None`                                                                  |

Invariants: the graph is a DAG (`genealogy_closure`); every non-`raw_lot` node has at least one
inbound `consumed_by` or `derived_from` edge; `item_revision` is never null; forward closure of the
backward closure of any node contains that node.

**`TraceScope`** variants: `LotScope(lot_id)`, `BatchScope(batch_id)`,
`SupplierLotScope(supplier_id, supplier_lot)`, `RevisionScope(item_id, rev_from, rev_to)`,
`EquipmentContactScope(equipment_id, window)`. The last one exists because real recalls scope by
shared-equipment contact (allergen and cross-contamination cases), not only by material lineage.

**`ProductPassport`** (E10): see 5.13.

### 3.3 Ledger entities

**`LedgerEntry`**: `entry_seq: int`, `payload: JsonValue`, `payload_hash: bytes` (SHA-256 over the
RFC 8785 canonical form with the RFC 6962 leaf prefix `0x00`), `signatures: list[Signature]`.

**`BlockHeader`**: `block_seq`, `prev_block_hash`, `merkle_root`, `tree_size`, `sim_time`,
`sealed_by`, `entry_count`.

The header carries no wall clock (D-01). A wall-clock reading in a hashed structure would make two
runs of the same seed on the same machine produce different roots seconds apart, which destroys the
determinism claim on the artifact the section is proudest of. C2 already gives the right home: the
run records one sim-time-to-wall-clock mapping in the provenance sidecar, and any wall-clock
question about a block is answered by applying that mapping to `sim_time`.
`test_block_header_carries_no_wall_clock` asserts the field set so the carve-out cannot regress.

**`Signature`**: `party_id`, `algorithm: Literal["ed25519"]`, `public_key`, `signature`,
`signed_over: Literal["entry_hash","block_header"]`, `role`.

**`SignaturePolicy`**: per event type, a required set of party roles and a threshold. Example:
`genealogy.custody_transfer` requires both `transferor` and `transferee`.

Invariants: `entry_seq` strictly increasing with no gaps; `prev_block_hash` of block N equals the
header hash of block N-1; `verify_chain` returns true for every prefix of the ledger; any single-byte
mutation anywhere in the persisted store causes verification failure.

### 3.4 Quality entities

**`Ncr`**

| Field                | Type              | Notes                                                           |
|----------------------|-------------------|-----------------------------------------------------------------|
| `ncr_id`             | `str`             |                                                                 |
| `dedupe_key`         | `DedupeKey`       | `(source_class, subject_ref, characteristic_id, window_bucket)` |
| `source_finding_ids` | `list[str]`       | appended to on recurrence within the correlation window         |
| `raised_at`          | `SimTime`         |                                                                 |
| `subject`            | `SubjectRef`      | lot, batch, machine, supplier lot, order, or device             |
| `quantity_affected`  | `Quantity`        |                                                                 |
| `severity`           | `Severity`        | inherited from the finding, floored by the safety rule          |
| `state`              | `NcrState`        | `open`, `contained`, `dispositioned`, `closed`, `voided`        |
| `disposition`        | `NcrDisposition \ | None`                                                           |
| `capa_id`            | `str \            | None`                                                           |
| `copq_postings`      | `list[str]`       |                                                                 |

**`Capa`**

| Field                  | Type                         | Notes                                              |
|------------------------|------------------------------|----------------------------------------------------|
| `capa_id`              | `str`                        |                                                    |
| `ncr_ids`              | `list[str]`                  | one CAPA may cover many NCRs sharing a root cause  |
| `state`                | `CapaState`                  | see 5.9                                            |
| `containment`          | `ContainmentAction \         | None`                                              |
| `rca`                  | `RcaRecord`                  | tools used, their outputs, the accepted root cause |
| `actions`              | `list[CorrectiveAction]`     | each may be an ECO reference (the PLM loop)        |
| `verification_plan`    | `VerificationPlan`           | declared **before** implementation                 |
| `verification_results` | `list[EffectivenessVerdict]` | initial and each sustain check                     |
| `reopen_count`         | `int`                        | monotone non-decreasing                            |

**`VerificationPlan`**

| Field                       | Type                             | Validation                                                                                |
|-----------------------------|----------------------------------|-------------------------------------------------------------------------------------------|
| `primary_metric`            | `str`                            | must resolve in the governed metrics layer (E26b); free-text metrics are rejected at load |
| `secondary_metrics`         | `list[str]`                      | reported, never decision-making                                                           |
| `direction`                 | `Literal["increase","decrease"]` |                                                                                           |
| `minimum_detectable_effect` | `float`                          | in metric units, required, no default                                                     |
| `alpha`                     | `float`                          | 0 < alpha < 0.5, default 0.05                                                             |
| `power`                     | `float`                          | 0.5 < power < 1, default 0.80                                                             |
| `pre_window`                | `Window`                         | must end at or before implementation time                                                 |
| `washout_s`                 | `float`                          | settling period after implementation, excluded from both windows                          |
| `post_window_min_n`         | `int`                            | computed by the LSS power module, not authored by hand                                    |
| `sustain_horizon_s`         | `float`                          | second verification point, default 90 sim-days                                            |

**`SamplingPlan`**: `code_letter`, `sample_size_n`, `accept_c`, `reject_r`, `severity`,
`plan_kind: Literal["single","double","multiple"]`, `aql`, `inspection_level`, `source_table`.

**`SwitchingState`**: `severity: Literal["normal","tightened","reduced","discontinued"]`,
`consecutive_accepted`, `rejects_in_last_five`, `switching_score`, `history: list[LotResult]`.

**`CertificateOfAnalysis`**: see 5.11.

**`CopqPosting`**: `posting_id`, `copq_class`, `amount`, `currency`, `source_event_id`,
`cost_driver`, `subject_ref`, `sim_time`. Exactly one class per posting, enforced by the type.

**`AuditEntry`**: `seq`, `sim_time`, `actor: Actor`, `action`, `subject_ref`, `before_digest`,
`after_digest`, `reason`, `evidence_refs: list[str]`, `query_result_ids: list[str]`,
`ledger_entry_seq`. `evidence_refs` and `query_result_ids` are sorted before the entry is hashed
(D-03). The entry carries sim-time only, for the reason `BlockHeader` does (D-01); the run's
sim-to-wall mapping in the provenance sidecar answers "when in real time" for any entry, which is
what C2 asks for and what a reviewer needs.

**`Actor`**: `kind: Literal["human","agent","system"]`, `id`, `role`, `autonomy_tier: int | None`
(E5 L1/L2/L3), `approving_human_id: str | None`, `tool_call_id: str | None`.

**`Checklist`**: `checklist_id`, `version`, `clause_refs: list[ClauseRef]`,
`questions: list[ChecklistQuestion]`, `applies_to: Selector`.

**`ChecklistQuestion`**: `question_id`, `text` (twinflow's own wording), `clause_ref`,
`evidence_query: MetricQuery | EventQuery`, `pass_predicate: Predicate`,
`nonconformity_class_on_fail: Literal["major","minor","observation"]`.

### 3.5 PLM entities

**`Item`**: `item_id`, `description`, `uom`, `item_type: Literal["raw","wip","finished","packaging","consumable"]`,
`revisions: list[Revision]`.

**`Revision`**: `rev`, `released_at`, `state: Literal["draft","released","superseded","obsolete"]`,
`interchangeability: Interchangeability`, `supersedes: str | None`, `eco_id: str | None`.

**`Interchangeability`**: `fully` (old and new substitute freely), `forward_only` (new replaces old
but not the reverse), `not_interchangeable` (revision change is a functional break). This enum is
what drives use-up-versus-scrap, so it is required, not optional.

**`Bom`**: `parent_item`, `parent_rev`, `lines: list[BomLine]`, `effectivity`.
**`BomLine`**: `component_item`, `component_rev_rule` (`pinned` to a rev, or `latest_effective`),
`qty_per`, `uom`, `scrap_factor_pct`, `reference_designator`.

Invariants: BOM explosion is acyclic (a cyclic BOM raises at load, not at rollup); `qty_per > 0`;
`scrap_factor_pct` in `[0, 100)`.

**`Eco`**: `eco_id`, `state: EcoState`, `ecr_id`, `affected: list[AffectedItem]`, `effectivity`,
`dispositions: list[DispositionDecision]`, `approvals: list[Approval]`, `reason`,
`source_capa_id: str | None`, `cost_impact: CostImpact`.

**`AffectedItem`**: `item_id`, `from_rev`, `to_rev`, `interchangeability`.

**`DispositionDecision`**: `stock_location`, `item_id`, `rev`, `on_hand_qty`,
`decision: Literal["use_up","rework","scrap","return_to_supplier","relabel"]`, `rationale`,
`cost`, `copq_class` (scrap decisions post as internal failure).

### 3.6 SOP entities

**`SopDocument`**: `sop_id`, `revision`, `title`, `owner_role`, `effective_from`, `effective_to`,
`applies_to: Selector` (stations, equipment, product families, item revisions), `state:
DocumentState`, `clauses: list[SopClause]`, `source_path`.

**`SopClause`**: `clause_id` (stable anchor of the form `sop:<sop_id>@<rev>#<number>`), `number`,
`heading`, `text`, `char_span`, `refs: ClauseRefs` (station ids, equipment ids, defect codes, spec
characteristic ids extracted at parse time), `parent_clause_id`.

**`Citation`**: `clause_id`, `quoted_span`, `char_start`, `char_end`, `retrieval_score`,
`eligibility_reason`, `sop_revision`, `resolved_at_sim_time`.

**`Abstention`**: `reason: Literal["no_eligible_clause","below_threshold","corpus_empty"]`,
`downgraded_finding_class: Literal["undocumented_deviation"]`.

**`AdherenceModel`**: `coefficients: dict[str, float]` with every coefficient named in config and
documented as chosen rather than fitted.

---

## 4. Events

Every event uses the common envelope owned by the schema registry (C3). Reproduced here only so the
determinism-relevant fields are visible.

```json
{
  "event_id": "uuid5(TWINFLOW_NS, run_id + ':' + producer_id + ':' + str(seq))",
  "schema": "production.batch.completed",
  "schema_version": "1.0.0",
  "run_id": "r-2026-03-04-seed4471",
  "producer_id": "twinflow-production",
  "producer_version": "0.9.2",
  "seq": 1234567,
  "sim_time": "2026-03-04T07:15:00.000Z",
  "actor": {
    "kind": "system",
    "id": "batch_executor",
    "role": null,
    "autonomy_tier": null
  },
  "causation_id": "<event_id of the cause>",
  "correlation_id": "<event_id of the originating request>",
  "payload": {}
}
```

Four envelope properties are load-bearing for this section and each is a doctrine ruling rather than
a local choice.

**No wall clock, anywhere in the envelope or in any payload (D-02).** A wall-clock value in an
event makes two runs of the same seed differ on their first event, so the byte-identity claim would
fail by construction. The four readers that may touch a real clock are the provenance sidecar
writer, the paced-clock pacer, the observability exporter, and operator-facing log lines. None of
them writes into an event. `test_no_payload_field_carries_wall_clock` walks every schema this
section registers and fails on any field whose type is a wall-clock instant.

**`producer_id`, and sequence density per producer (D-07).** `seq` is dense per
`(run_id, producer_id)`, not globally, because this section alone runs seven producers and the
enterprise tier partitions the log. The canonical total order is `(sim_time, producer_id, seq)`, and
both the replay reader and the pagination cursor use exactly that order. `producer_version` is
carried beside `producer_id` and is deliberately not part of the ordering key.

**`event_id` is a UUID5, never a UUID4.** The name is `run_id`, `producer_id` and `seq` together;
dropping `producer_id` would let two producers mint the same id once sequences are per-producer. Any
use of UUID4 in this section's packages is a CI lint failure.

**The determinism the envelope supports is the two-tier claim, not the stronger one (D-05).** Same
seed, same config, same platform and same pinned dependency set gives a byte-identical event log,
checked by hash equality. Across platforms the claim is value equivalence: every business event
appears with the same schema, order and discrete fields, and continuous fields agree within a
tolerance derived from measured divergence rather than assumed in advance. Section 7.3 states which
gate checks which tier.

### 4.1 Published by `twinflow-production`

| Schema                              | v     | Payload shape (abridged)                                                                                                                                                                                                                                                           |
|-------------------------------------|-------|------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| `production.batch.started`          | 1.0.0 | `{batch_id, recipe_id, recipe_revision, unit_id, planned_qty, input_lot_ids[], control_recipe_digest}`                                                                                                                                                                             |
| `production.batch.phase_transition` | 1.0.0 | `{batch_id, phase_id, from_state, to_state, reason, unit_id, operator_id}`                                                                                                                                                                                                         |
| `production.batch.completed`        | 1.0.0 | `{batch_id, good_qty, rework_qty, scrap_qty, declared_loss_qty, output_lot_ids[], duration_s}`                                                                                                                                                                                     |
| `production.golden_batch.scored`    | 1.0.0 | `{batch_id, profile_ref, score, per_cpp: [{cpp_id, nrmse, out_of_envelope_frac, weight}], verdict}`                                                                                                                                                                                |
| `production.machine.state_changed`  | 1.0.0 | `{machine_id, from_state, to_state, mode, reason_code, cause: "internal"\                                                                                                                                                                                                          |
| `production.oee.interval`           | 1.0.0 | `{machine_id, window_start, window_end, availability, performance, quality, oee, teep, losses: {breakdown_s, setup_s, minor_stop_s, reduced_speed_s, defect_units, startup_units}, valuable_operating_time_s, planned_production_time_s, external_stop_s, external_counted: bool}` |
| `production.changeover.completed`   | 1.0.0 | `{changeover_id, machine_id, from_family, to_family, total_s, internal_s, external_s, elements[]}`                                                                                                                                                                                 |
| `production.schedule.published`     | 1.0.0 | `{schedule_id, horizon_start, horizon_end, assignments: [{job_id, machine_id, setup_start, run_start, run_end, sequence_index}], objective: {makespan_s, total_weighted_tardiness, total_setup_s}, solver, solver_params}`                                                         |
| `production.schedule.divergence`    | 1.0.0 | `{schedule_id, bucket, planned_units, actual_units, adherence_pct, top_causes[]}`                                                                                                                                                                                                  |
| `production.unit.completed`         | 1.0.0 | `{unit_serial, item_id, item_revision, work_center_id, machine_id, cycle_time_s, first_pass: bool}`                                                                                                                                                                                |
| `production.scrap.recorded`         | 1.0.0 | `{lot_id_or_serial, stage_id, machine_id, defect_code, qty, cause_class, batch_id?}`                                                                                                                                                                                               |
| `production.kanban.card_moved`      | 1.0.0 | `{loop_id, card_id, from_stage, to_stage, wip_after}`                                                                                                                                                                                                                              |
| `production.measurement.recorded`   | 1.0.0 | `{characteristic_id, stage_id, machine_id, subgroup_id, values[], uom, lot_ref, sample_time}`                                                                                                                                                                                      |

`production.measurement.recorded` is the only feed the LSS engine needs from the factory. There is no
production-side statistics code.

### 4.2 Published by `twinflow-genealogy`

| Schema                       | v     | Payload shape (abridged)                                                                              |
|------------------------------|-------|-------------------------------------------------------------------------------------------------------|
| `genealogy.transformation`   | 1.0.0 | `{inputs: [{node_id, qty}], outputs: [{node_id, qty}], equipment_id, recipe_id, recipe_revision, at}` |
| `genealogy.aggregation`      | 1.0.0 | `{parent_node_id, child_node_ids[], action: "add"\                                                    |
| `genealogy.custody_transfer` | 1.0.0 | `{node_ids[], from_party, to_party, location_gln, at, conveyance_ref}`                                |
| `genealogy.observation`      | 1.0.0 | `{node_ids[], biz_step, disposition, read_point_gln, biz_location_gln, sensor_element_refs[]}`        |
| `genealogy.epcis.emitted`    | 1.0.0 | `{epcis_event_id, epcis_type, document_ref, ledger_entry_seq}`                                        |
| `dpp.passport.issued`        | 1.0.0 | `{passport_id, digital_link_uri, lot_ref, item_id, item_revision, merkle_root, audience_views[]}`     |

### 4.3 Published by `twinflow-ledger`

| Schema                       | v     | Payload shape                                                                  |
|------------------------------|-------|--------------------------------------------------------------------------------|
| `ledger.entry.appended`      | 1.0.0 | `{entry_seq, payload_schema, payload_hash, tree_size_after}`                   |
| `ledger.block.sealed`        | 1.0.0 | `{block_seq, prev_block_hash, merkle_root, tree_size, entry_count, sealed_by}` |
| `ledger.signature.attached`  | 1.0.0 | `{entry_seq, party_id, role, algorithm, public_key_fingerprint}`               |
| `ledger.root.published`      | 1.0.0 | `{block_seq, merkle_root, published_to: [party_id], at}`                       |
| `ledger.verification.failed` | 1.0.0 | `{scope, expected, observed, first_bad_seq}`                                   |

### 4.4 Published by `twinflow-quality`

| Schema                                 | v     | Payload shape (abridged)                                                                                                                                                                                                                      |
|----------------------------------------|-------|-----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| `qms.ncr.raised`                       | 1.0.0 | `{ncr_id, dedupe_key, source_finding_ids[], subject_ref, quantity_affected, severity}`                                                                                                                                                        |
| `qms.ncr.evidence_appended`            | 1.0.0 | `{ncr_id, finding_id, occurrence_count}`                                                                                                                                                                                                      |
| `qms.ncr.disposition`                  | 1.0.0 | `{ncr_id, disposition, qty, approved_by, copq_posting_ids[]}`                                                                                                                                                                                 |
| `qms.capa.opened`                      | 1.0.0 | `{capa_id, ncr_ids[], owner_role, verification_plan}`                                                                                                                                                                                         |
| `qms.capa.state_changed`               | 1.0.0 | `{capa_id, from_state, to_state, actor, reason}`                                                                                                                                                                                              |
| `qms.capa.effectiveness_verified`      | 1.0.0 | `{capa_id, check_kind: "initial"\                                                                                                                                                                                                             |
| `qms.capa.reopened`                    | 1.0.0 | `{capa_id, reopen_count, reason: "effectiveness_not_demonstrated"\                                                                                                                                                                            |
| `qms.sampling.lot_inspected`           | 1.0.0 | `{lot_ref, plan: {code_letter, n, c, r, severity, aql, level, source_table}, defectives_found, decision, switching_state_after}`                                                                                                              |
| `qms.sampling.switching_state_changed` | 1.0.0 | `{supplier_id, item_id, from_severity, to_severity, rule_fired, ruleset}`                                                                                                                                                                     |
| `qms.coa.issued`                       | 1.0.0 | `{coa_id, lot_ref, item_id, item_revision, results[], released_by, signature_ref, genealogy_merkle_root}`                                                                                                                                     |
| `qms.copq.posted`                      | 1.0.0 | `{posting_id, copq_class, amount, currency, cost_driver, source_event_id, subject_ref}`                                                                                                                                                       |
| `qms.audit.executed`                   | 1.0.0 | `{audit_id, checklist_id, checklist_version, scope, results: [{question_id, clause_ref, outcome, evidence_refs[]}], score, nonconformities[]}`                                                                                                |
| `qms.lpa.scheduled`                    | 1.0.0 | `{lpa_id, layer, auditor_role, station_id, due_at}`                                                                                                                                                                                           |
| `qms.lpa.executed`                     | 1.0.0 | `{lpa_id, layer, station_id, completed_at, results[], on_time: bool}`                                                                                                                                                                         |
| `qms.quarantine.requested`             | 1.0.0 | `{quarantine_id, node_ids[], reason, source: "ncr"\                                                                                                                                                                                           |
| `qms.quarantine.released`              | 1.0.0 | `{quarantine_id, node_ids[], released_by, rationale}`                                                                                                                                                                                         |
| `qms.recall_drill.completed`           | 1.0.0 | `{drill_id, scope, blast_radius: {raw_lots, batches, finished_lots, pallets, cartons, orders, shipments, customers, open_pos}, qty_produced, qty_accounted, qty_unlocated, elapsed_sim_s, graph_edges_walked, merkle_root, proof_bundle_ref}` |
| `qms.audit_trail.appended`             | 1.0.0 | `{seq, actor, action, subject_ref, before_digest, after_digest, reason, ledger_entry_seq}`                                                                                                                                                    |

### 4.5 Published by `twinflow-bizsys`

`twinflow-bizsys` is the seventh package (2.7), a separate distribution holding the ERP stub, the
three-way reconciler and the mini CMMS.

| Schema                           | v     | Payload shape (abridged)                                                                                                                                                                                          |
|----------------------------------|-------|-------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| `erp.expected_receipt.published` | 1.0.0 | `{asn_id, po_ref, supplier_id, ship_datetime, eta, carrier_scac, hierarchy: [{sscc, cartons: [{sscc_or_gtin, items: [{item_id, item_revision, lot, qty, uom, hs_code?, country_of_origin?, carbon_kgco2e?}]}]}]}` |
| `erp.receipt.reconciled`         | 1.0.0 | `{asn_id, receipt_id, lines: [{item_id, lot, expected_qty, rfid_qty, cv_qty, accepted_qty, variance_class, cause_class, confidence}], overall_variance_class}`                                                    |
| `erp.inventory.book_adjusted`    | 1.0.0 | `{item_id, lot, location, delta_qty, reason, source_event_id}`                                                                                                                                                    |
| `cmms.work_order.created`        | 1.0.0 | `{wo_id, asset_id, wo_type, source_finding_id, priority_score, rpn, predicted_failure_window, required_skills[], required_parts[], estimated_duration_s}`                                                         |
| `cmms.deferral_cost.estimated`   | 1.0.0 | `{wo_id, curve: [{defer_days, p_failure, expected_cost, planned_cost, total_expected_cost, ci_low, ci_high}], recommended_window, method: "paired_crn_twin_runs", replications, seed}`                            |
| `cmms.work_order.scheduled`      | 1.0.0 | `{wo_id, window_start, window_end, production_impact_units, approved_by}`                                                                                                                                         |
| `cmms.work_order.completed`      | 1.0.0 | `{wo_id, actual_duration_s, parts_used[], findings_closed[], runbook_ref, mtbf_after_s, mttr_after_s}`                                                                                                            |

### 4.6 Published by `twinflow-plm`

| Schema                      | v     | Payload shape (abridged)                                                                                              |
|-----------------------------|-------|-----------------------------------------------------------------------------------------------------------------------|
| `plm.item.revised`          | 1.0.0 | `{item_id, from_rev, to_rev, interchangeability, eco_id}`                                                             |
| `plm.eco.state_changed`     | 1.0.0 | `{eco_id, from_state, to_state, actor, approvals[]}`                                                                  |
| `plm.eco.effective`         | 1.0.0 | `{eco_id, effectivity, affected[], dispositions[]}`                                                                   |
| `plm.disposition.decided`   | 1.0.0 | `{eco_id, stock_location, item_id, rev, on_hand_qty, decision, cost, copq_class?}`                                    |
| `plm.standard_cost.revised` | 1.0.0 | `{item_id, rev, old_standard_cost, new_standard_cost, rollup_breakdown: {material, labor, overhead}, effective_from}` |
| `plm.po_change.requested`   | 1.0.0 | `{po_ref, po_line, from_rev, to_rev, action: "amend"\                                                                 |

### 4.7 Published by `twinflow-sop`

| Schema                   | v     | Payload shape (abridged)                                                                                                                           |
|--------------------------|-------|----------------------------------------------------------------------------------------------------------------------------------------------------|
| `sop.revision.published` | 1.0.0 | `{sop_id, revision, state, effective_from, applies_to, clause_count, clarity_score, content_digest}`                                               |
| `sop.clause.cited`       | 1.0.0 | `{finding_id, clause_id, sop_revision, quoted_span, char_start, char_end, retrieval_score, eligibility_reason}`                                    |
| `sop.citation.abstained` | 1.0.0 | `{finding_id, reason, downgraded_finding_class}`                                                                                                   |
| `sop.draft.generated`    | 1.0.0 | `{sop_id, draft_revision, evidence_bundle_ref, grounding_report: {numbers_total, numbers_grounded, query_result_ids[]}, model_ref, prompt_digest}` |
| `sop.training.recorded`  | 1.0.0 | `{operator_id, sop_id, revision, trained_at, method, assessor}`                                                                                    |
| `sop.adherence.sampled`  | 1.0.0 | `{station_id, operator_id, sop_id, revision, adherence_p, drivers: {clarity, training_recency_s, step_count, fatigue_index, tenure_s}}`            |

### 4.8 Consumed events

| Schema                             | Owning section | Used for                                                           |
|------------------------------------|----------------|--------------------------------------------------------------------|
| `lss.finding.raised`               | 5              | NCR auto-raise rules, checklist evidence, CAPA triggers            |
| `lss.hypothesis.result`            | 5              | CAPA effectiveness verdicts, FPY valuation, SMED validation        |
| `telemetry.reading`                | 2              | golden-batch profiles, in-line measurements, cold-chain excursions |
| `pdm.threshold_crossing.estimated` | 3              | CMMS work-order creation and the deferral-cost curve               |
| `cv.violation.detected`            | 4              | SOP clause citation, NCR raise                                     |
| `cv.count.observed`                | 4              | ASN reconciliation three-way match                                 |
| `rfid.read.observed`               | 2              | ASN reconciliation three-way match                                 |
| `wms.receipt.observed`             | 1              | reconciliation anchor                                              |
| `supplier.lot.shipped`             | 6a2            | inbound genealogy edge and supplier lot node                       |
| `order.shipped`                    | 6a3            | forward genealogy edge to customer, CoA trigger                    |
| `hr.certification.granted`         | 6a14           | SOP training records and station gating                            |
| `finance.standard_cost.applied`    | 6a17           | acknowledgement of `plm.standard_cost.revised`                     |

Schema evolution is additive-only within a major version (C3). The reserved attribute keys on
`genealogy.Node` (`hs_code`, `country_of_origin`, `carbon_kgco2e`, `supplier_id`, `expiry`) exist
from v1.0.0 even though E14, E17 and 6a2 populate them later, precisely so those sections do not
force a major version bump on the most-referenced schema in the repo.

---

## 5. Behavior

### 5.1 The hybrid factory shape (6a9)

The plant is one continuous/batch front end feeding one discrete back end, and the handoff is
modeled explicitly because hybrid support is the hard requirement the source calls out.

Reference shape shipped in the enterprise profile: **mix -> coat -> cure** (batch, ISA-88 controlled,
process cells and units, campaign-based) hands finished intermediate lots to **form -> finish ->
pack** (discrete, work centers and machines, unit-serialized). The handoff node is a
`wip_lot` genealogy node with a quantity in the batch UOM, consumed by the discrete side in a
different UOM through a declared conversion factor on the BOM line. UOM conversion at the handoff is
where real hybrid systems break, so the conversion is a first-class, validated config value and a
property test asserts round-trip conversion error is zero for the configured factors.

Batch side timing: each `Phase` has a duration distribution and a set of critical process parameters
whose trajectories are generated from a phase-local parameterized model (ramp, soak, decay) plus
noise drawn from the phase's child RNG stream. Every physics parameter is config, and the model is
documented as a chosen parameterization rather than a fitted plant model. The process and chemical
sensors from the 2b catalog (pH, conductivity, viscosity, Coriolis and magnetic flow, radar and
ultrasonic level, dissolved oxygen, corrosion) attach to units and read the same trajectories through
their catalog signal models, so a drifting viscosity sensor and a genuinely drifting viscosity are
distinguishable only by MSA, which is exactly the situation the LSS engine exists to resolve.

Discrete side timing: per-machine cycle-time distributions, buffers between work centers, blocking
and starvation propagated through the buffer occupancy.

Machines on both sides register in the device registry (component 3) with the same asset schema as
the DC's conveyors, so the PdM layer needs no factory-specific code.

### 5.2 ISA-88 recipes and golden-batch scoring (6a9)

Recipes are loaded from `recipes/*.yaml`, validated against `/schemas/recipe.v1.json`, and versioned
by `twinflow-plm` (5.14). The four ISA-88 recipe types are represented as follows: general and site
recipes are documentation-only files in `docs/recipes/` that name the master recipes derived from
them, master recipes are the executable configuration, and control recipes are runtime artifacts
recorded into the batch record. Modeling all four is what makes the ISA-88 claim honest rather than
a label on a config file.

**Golden profile construction.** A profile is built per `(recipe_id, recipe_revision, phase_id,
cpp_id)` from qualifying batches. A batch qualifies when it satisfies the configured
`qualification_rule`, whose default is: released without deviation, all release tests passed, batch
FPY at or above `golden.min_fpy`, and no NCR raised against it. At least
`golden.min_qualifying_batches` (default 20) are required, and the mean and envelope are computed as:

- resample each qualifying batch's CPP trajectory onto a fixed grid of `golden.grid` points
  (default 64) in **normalized phase progress**, not wall time, using piecewise-linear
  interpolation, because phase durations vary and comparing on absolute time compares a fast batch's
  soak against a slow batch's ramp;
- `mean[i]` is the median across qualifying batches at grid point i (median, not mean, so one
  outlier batch that slipped through qualification does not shift the golden path);
- `lower[i]`, `upper[i]` are the `golden.envelope_quantiles` (default 0.05 and 0.95) across
  qualifying batches, then widened by `golden.envelope_floor_frac` of the CPP's spec range so a
  parameter with almost no historical variation does not produce an impossibly tight envelope.

Alignment mode is config: `golden.alignment: progress_resample | dtw`. `progress_resample` is the
default because it is deterministic, cheap, and does not hide a genuine timing deviation by warping
it away. `dtw` is available for the case where the timing itself is not a quality attribute, and when
it is enabled the batch record stores the warp path so the deviation that was warped away is still
visible.

**Scoring.** For each CPP:

```
nrmse       = sqrt(mean_i((x[i] - mean[i])**2)) / (upper_ref - lower_ref)
oob_frac    = fraction of grid points where x[i] < lower[i] or x[i] > upper[i]
cpp_penalty = w_rmse * nrmse + w_oob * oob_frac          # weights in config, sum to 1
```

where `upper_ref - lower_ref` is the CPP's configured reference range (spec range if specs exist,
otherwise the golden envelope width at the widest grid point), so `nrmse` is dimensionless and
comparable across CPPs.

```
score = 100 * (1 - clamp01(sum_over_cpps(weight_cpp * cpp_penalty_cpp) / sum(weight_cpp)))
```

Verdict thresholds are config (`golden.verdict_bands`, default: `>= 90` golden, `>= 75` acceptable,
`>= 60` marginal, `< 60` deviation). A verdict of marginal or worse emits
`production.golden_batch.scored` with a verdict that the finding rules turn into an
`lss.finding.raised` of class `golden_batch_deviation`, which then feeds the NCR engine.

**Multivariate check.** Alongside the per-CPP score, the batch's CPP vector at each grid point is fed
to the LSS engine's multivariate control chart (Hotelling T-squared and MEWMA) so a batch where every
CPP is individually inside its envelope but the joint pattern is unprecedented is still caught. This
is delegated, not reimplemented. The reference validation of the multivariate charts belongs to the
LSS engine's own gates; this section asserts only that the CPP vector reaches the chart in grid-point
order with the CPPs in sorted `cpp_id` order, so the same batch produces the same input matrix on
every run (D-03).

### 5.3 Machine states and equipment-level OEE with six big losses (6a9)

**State model.** Machine states are the PackML state names and transition graph. PackML was
developed by OMAC and adopted by ISA as the technical report ISA-TR88.00.02, which is the statement
OMAC's own PackML page makes (omac.org/packml, retrieved 2026-08-10, HTTP 200). Implemented states:
`aborted`, `aborting`, `clearing`, `stopped`, `stopping`, `resetting`, `idle`, `starting`,
`execute`, `holding`, `held`, `unholding`, `suspending`, `suspended`, `unsuspending`, `completing`,
`complete`. Modes: `producing`, `maintenance`, `manual`. twinflow builds the state names and the
transition graph and cites ISA-TR88.00.02 as the formal source; it does not reproduce the technical
report's text, which is copyrighted and paid (Open Question 9.6). The report's edition year is not
asserted here because it could not be read from a primary or catalog source on 2026-08-10, and
Open Question 9.14 records the confirmation that must happen before the README cites it.

PackML is chosen over an ad hoc state enum for one reason that matters to OEE: PackML distinguishes
**held** (stopped by an internal condition, the machine's own fault) from **suspended** (stopped by
an external condition, starved or blocked). That distinction is exactly the argument practitioners
have about whether a starved machine's downtime is an availability loss, and having it in the state
model means twinflow can report both answers rather than picking one silently.

**OEE.** Computed per machine per window by `compute_oee`:

```
total_time                = window_end - window_start
planned_downtime          = calendar closures + PM windows + no-demand time
external_stop_time        = time SUSPENDED (starved or blocked by an upstream or downstream cause)
planned_production_time   = total_time - planned_downtime - (external_stop_time if not counted)
run_time                  = time in EXECUTE
availability              = run_time / planned_production_time
performance               = (ideal_cycle_time * total_count) / run_time
quality                   = good_count / total_count
oee                       = availability * performance * quality
teep                      = oee * (planned_production_time / total_time)
```

Every quantity above is an integer count of sim-ticks before it becomes a ratio, so the time
accounting closes exactly and only the four ratios are floating point.

`production.oee.interval` is emitted twice per window, and the two records differ in exactly one
input. With `external_counted: false` this is equipment OEE: external stop time leaves planned
production time entirely and is reported in its own field `external_stop_s`, so it is neither an
availability loss nor a performance loss. With `external_counted: true` this is line OEE: external
stop time stays inside planned production time and lands in loss bucket 1 or 3 by its duration. The
config key `oee.count_external_stops_as_availability_loss` selects which record the dashboard
headlines, and ARCHITECTURE.md states the choice and why. Both records are always emitted, so
neither answer is hidden.

If `performance > 1.0`, the ideal cycle time is misconfigured. The engine does not clamp silently:
it emits a config finding `oee_ideal_cycle_time_implausible` carrying the observed fastest realized
cycle time as the suggested correction, and reports performance uncapped so the error is visible.
The finding fires on the first completed unit whose realized cycle time is below
`ideal_cycle_time_s`, which is the same condition as `performance > 1.0` over any window containing
that unit, stated once so config validation (6.1) and runtime agree.

**Six big losses.** Every sim-tick of `planned_production_time` and every produced unit lands in
exactly one bucket. The six-loss taxonomy is the one Nakajima sets out in *Introduction to TPM*
(Productivity Press, 1988); twinflow names the six and maps its own states onto them, and does not
reproduce the book's text. The mapping from PackML state plus reason code to loss bucket is config
(`oee.loss_mapping`), with this default:

| Loss (Nakajima six)           | OEE factor   | Default source states and conditions                                                                                              |
|-------------------------------|--------------|-----------------------------------------------------------------------------------------------------------------------------------|
| 1. Breakdown                  | Availability | `aborted`, `aborting`, `clearing`, and `held`/`holding` with `cause=internal` at or above `minor_stop_threshold_s`                |
| 2. Setup and adjustment       | Availability | `resetting`, `starting` with `reason_code=changeover`, and mode `manual` during a changeover                                      |
| 3. Idling and minor stops     | Performance  | `held`/`holding` with `cause=internal` and duration below `minor_stop_threshold_s` (default 300 s)                                |
| 4. Reduced speed              | Performance  | time in `execute` where realized cycle time exceeds `ideal_cycle_time_s`                                                          |
| 5. Process defects and rework | Quality      | units scrapped or reworked while in steady `execute` outside the startup window                                                   |
| 6. Startup and yield loss     | Quality      | units scrapped within `oee.startup_window_units` after `starting` or `resetting`, and batch-side yield below `expected_yield_pct` |

External stop time is absent from the table because it is not one of the six. Under
`external_counted: false` it sits outside planned production time in `external_stop_s`. Under
`external_counted: true` it is classified into bucket 1 when its duration reaches
`minor_stop_threshold_s` and into bucket 3 below that, by the same duration rule the internal states
use. Leaving that rule unstated is what lets two plants quote different OEE for the same shift, so
both accountings are computed and both are published.

The invariant `loss_accounting_closure` (7.2) asserts closure for each accounting separately. Under
`external_counted: false`: the six time buckets plus valuable operating time equal planned
production time, and external stop time is accounted separately against total time. Under
`external_counted: true`: the six time buckets plus valuable operating time equal planned production
time with external stop time already inside it. In both accountings the two unit buckets plus good
count equal total count. All four sums are integer sums of sim-ticks and units with no tolerance, so
a decomposition that does not close fails a test rather than appearing in a report.

### 5.4 Changeover and SMED (6a9)

Every changeover records its elements from the machine's `changeover_template`, which lists elements
with a base duration distribution and an `as_is` internal/external classification. `analyse_smed`
produces:

- total changeover time distribution per `(from_family, to_family)` pair, trended on a control chart
  by the LSS engine;
- internal fraction = internal seconds / total seconds, the SMED headline metric;
- an element-level Pareto of internal time, which is the first move on a real SMED project;
- for each element, its `smed_stage`.

The SMED improvement lever is a config-declared program:

```yaml
smed:
  program_id: smed_2026_q2
  conversions: # stage 2 of SMED: internal -> external
    - { machine: form_01, element: "fetch tooling", to: external }
    - { machine: form_01, element: "preheat die", to: external }
  streamlining: # stage 3: reduce what remains
    - {
        machine: form_01,
        element: "bolt changeover",
        factor: 0.4,
        method: "quick clamps",
      }
  capex: 18000
```

Applying the program is a what-if. The before/after comparison runs as paired seeded runs with common
random numbers (5.16), and the throughput delta goes to the LSS hypothesis layer, so "SMED bought us
X units per shift" carries a p-value, an effect size and a confidence interval rather than an
anecdote. `smed.capex` feeds the capex governance path in 6a17.

An external element executed while the machine is down is `smed_external_during_downtime`, a finding,
because the whole point of external setup is that it happens while the machine runs.

### 5.5 Finite-capacity scheduling with sequence-dependent setups (6a9)

**Problem.** A flexible flow shop: stages in series, parallel non-identical machines within a stage,
jobs with release dates, due dates, weights, and machine-eligibility sets, and sequence-dependent
setup times `S[machine][from_family][to_family]` drawn from a configured matrix keyed on attribute
changes (color, formulation, allergen, tooling). Setup time is charged before the run and is
attributed to loss bucket 2.

**Solver ladder**, all three built, selectable by config, all deterministic given the seed:

1. `dispatch_atcs`: the Apparent Tardiness Cost with Setups dispatching rule of Lee, Bhaskaran and
   Pinedo, "A heuristic to minimize the total weighted tardiness with sequence-dependent setups",
   IIE Transactions 29(1):45-52, 1997, DOI 10.1080/07408179708966311, with its look-ahead parameters
   `k1` and `k2` exposed as config. Fast, explainable, the baseline.
2. `local_search`: `dispatch_atcs` followed by a deterministic first-improvement neighborhood search
   (adjacent-pair swap and single-job reinsertion) under a stated iteration budget.
3. `optuna_search`: an Optuna study over the dispatching-rule parameters and the sequencing decisions
   for the top-N bottleneck machines, under a stated trial budget. This is the E9 optimization engine
   applied to scheduling; the sampler name and its seed are recorded in
   `production.schedule.published` so the result is reproducible.

**Every solver stops on a deterministic budget and never on wall time (D-04).** `local_search` stops
at `scheduling.budget.iterations`. `optuna_search` stops at `scheduling.budget.trials`, runs with
`n_jobs = 1`, and takes its sampler seed from the run seed through the RNG registry. A configuration
that offers a solver a wall-clock stopping condition is rejected at load with the message that a
wall-clock budget makes the schedule depend on machine speed, and a schedule that depends on machine
speed makes the whole tape depend on it. `test_schedule_is_identical_under_cpu_throttling` runs the
same instance with the process restricted to one core and then unrestricted, and asserts the
published schedule is byte-identical.

The schedule **evaluator** is separate from every solver and is exact: `evaluate_schedule` computes
makespan, total weighted tardiness, total setup time and machine utilization from an assignment list
with no heuristics anywhere. That separation exists so the evaluator can be checked against
published benchmark instances while the solvers stay free to be heuristic (VAL-GATE-PROD-2).

**Feeding the DC inbound schedule.** Completed finished-goods lots are built into shipments,
shipments enter the transport network (6a7) with the configured lane and mode, and the arrival at the
DC is announced as an ASN through the same `erp.expected_receipt.published` contract the synthetic
suppliers already use (5.12). The interface is what makes this a swap rather than a rewrite: before
Phase 3i the ASN source for the factory supplier is `SyntheticSupplierAsnSource`; at Phase 3i it
becomes `FactoryAsnSource`, and no consumer changes. That is the A3 adapter seam applied inside the
simulation.

Because the factory schedule now drives DC arrivals, a factory schedule miss propagates visibly to
dock congestion, which is the cause-and-effect chain the source asks for at the planning layer,
extended one echelon further upstream.

### 5.6 Flow control: push, pull, kanban (6a9)

`production.flow_control` selects one of four, all implemented:

- `push`: each stage runs to its own schedule; WIP is bounded only by buffer capacity.
- `pull_kanban`: stage-to-stage kanban loops. Cards authorize production. Card count per loop is
  either set explicitly or computed by the classical kanban sizing formula
  `N = ceil(D * L * (1 + alpha) / C)` where D is demand rate in units per second, L is replenishment
  lead time in seconds, alpha is the safety factor, and C is container size. Both paths are
  built; when the formula is used, its four inputs are recorded on the loop so the number is
  auditable rather than folklore. The formula is twinflow's declared sizing rule, not a citation:
  no published source is claimed for it, and `docs/kanban_sizing.md` says so.
- `conwip`: constant work in process across the whole line with a single global card pool.
- `drum_buffer_rope`: the bottleneck (identified by the twin's own bottleneck detector, component 1)
  is the drum, a time buffer protects it, and the rope releases material to the gate at the drum's
  rate.

Kanban card count is a tunable, so it is also a what-if lever: "reduce cards on loop coat-to-form from
6 to 4" answers with WIP, cycle time, starvation minutes at the downstream stage and the LSS engine's
verdict on whether the throughput change is real. The `kanban_wip_bound` invariant makes the pull
system's central promise a test rather than a claim.

Little's Law is asserted at steady state across the line as a property test (`littles_law_holds`),
which catches a whole class of bookkeeping bugs in WIP accounting. The law itself is Little,
"A Proof for the Queuing Formula: L = lambda W", Operations Research 9(3):383-387, 1961,
DOI 10.1287/opre.9.3.383. The tolerance is not a chosen round number: VAL-GATE-PROD-3 measures the
run-to-run spread of the ratio `WIP / (throughput * cycle_time)` across replications and sets the
tolerance above that measured noise floor, then publishes both.

### 5.7 First-pass yield, scrap and lot genealogy (6a9)

Per stage: `FPY_stage = units_passing_first_time / units_entering_stage`, where "first time" means
without rework and without repair. Rolled throughput yield across n stages is
`RTY = prod(FPY_i)`, and normalized yield is `RTY ** (1/n)`. RTY is converted to DPMO and sigma level
by the LSS engine, not here.

Every scrap event writes `production.scrap.recorded` and a genealogy terminal node so scrapped
material is traceable, not merely subtracted. Rework writes a `derived_from` edge and increments the
rework counter that `twinflow-procmine`'s rework-loop detector is checked against. `twinflow-procmine`
is the Apache-2.0 miner written in this repository, not PM4Py, because PM4Py is AGPL-3.0 and this
repository serves a dashboard, an MCP server and an HTTP API (D-14). A rework loop discovered by
mining and a rework count from production accounting must agree; a disagreement is itself a finding
(`rework_accounting_divergence`). The agreement is checkable here because the twin generated the
rework and knows the true loop count, which is a property of synthetic data and is claimed as
nothing more.

The material balance for every transformation is asserted as `material_conservation`:

```
sum(input_qty * conversion_factor) * expected_yield_pct/100
  == good_qty + rework_qty + scrap_qty + declared_loss_qty
  within recipe.material_balance_tolerance_pct
```

with `declared_loss_qty` bounded above by `expected_yield_loss_pct` of input. A transformation that
needs more declared loss than the recipe allows raises `unexplained_material_loss`, which is how real
plants find theft, unrecorded scrap and a miscalibrated scale.

### 5.8 In-line SPC and upstream-versus-downstream detection (6a9)

Each stage declares its CTQ characteristics in config with subgroup size, sampling frequency, spec
limits and chart type preference. The stage emits `production.measurement.recorded`; the LSS engine
selects the chart (I-MR for n=1, X-bar/R for small n, p-chart for attribute data), evaluates Western
Electric and Nelson rules, and computes Cp/Cpk/Pp/Ppk. None of that code lives here.

The headline experiment is **detection lead time**. Scenario `E2E-PROD-001` injects a slow drift in
the coating stage's thickness. Two detectors race: the machine-level control chart at the coat stage,
and the DC's inbound AQL inspection on the finished lots that eventually arrive. The scenario asserts
that for a drift of the configured magnitude, the machine-level finding fires at least
`spc.min_detection_lead_days` (default 3 sim-days) before the DC's first lot rejection, and records
the measured lead time as a published number. That number is the concrete answer to "why bother with
quality at the source", and it is measured rather than asserted rhetorically.

The **one point of FPY** experiment is a designed paired comparison. Two seeded runs, common random
numbers, identical in every respect except `stages.coat.base_fpy` differing by one percentage point.
Measured deltas: DC inbound inspection labor hours, internal-failure COPQ, external-failure COPQ,
returns units (6a4), fill rate and on-time ship rate (6a3), and the total COPQ delta. Reported with
confidence intervals from the LSS engine over `experiment.replications` seed pairs. This is the
headline number the README can carry for the production layer.

### 5.9 NCR and CAPA (6a11)

**NCR auto-raise.** `ncr_rules.yaml` maps finding classes to NCR creation:

```yaml
ncr_rules:
  - id: spc_ooc_to_ncr
    when:
      finding_class: [spc_violation, capability_shortfall]
      severity_at_least: major
      subject_kind: [machine, stage, lot]
    dedupe:
      key: [source_class, subject_ref, characteristic_id]
      window_s: 28800 # one shift
    severity_floor: major
  - id: safety_floor
    when: { finding_class: [safety_event, ppe_violation] }
    severity_floor: critical # safety findings outrank throughput findings by definition
```

Dedupe is what stops an alarm flood from becoming an NCR flood. Within `window_s`, a repeat finding
with the same dedupe key appends `qms.ncr.evidence_appended` to the existing NCR and increments its
occurrence count rather than creating a new one. The occurrence count drives escalation: at
`ncr.escalate_after_occurrences` the NCR is escalated to a CAPA automatically.
`ncr_dedupe_idempotence` (7.2) asserts that replaying the same finding stream produces the same NCR
set with the same occurrence counts.

This is the QMS half of the alarm-rationalization requirement in the reference-architecture
paragraph. The other half, severity ranking and shelving, belongs to the dashboard section's alarm
manager, and the NCR engine consumes rather than duplicates it: intake reads `shelve_policy` from
the finding catalog, and a finding shelved at the alarm layer still raises its NCR but does not
page anyone. Shelving suppresses the notification, never the record, because a QMS that can hide a
nonconformance by shelving it is not a QMS. `test_shelved_finding_still_raises_its_ncr` asserts it.

**CAPA state machine.**

```
open -> containment -> investigation -> action_planned -> implemented
     -> awaiting_evidence -> verifying -> closed_effective
                                       -> reopened -> action_planned (loop)
any state -> canceled (with reason and approval)
```

`capa_state_monotone` (7.2) asserts transitions follow this graph and `reopen_count` never decreases.

**Containment** records the immediate action and its scope: which lots quarantined
(`qms.quarantine.requested`), whether the line was stopped, whether 100 percent inspection was
imposed, and the containment cost, which posts as internal-failure COPQ.

**Root cause analysis** records which tools were run and their outputs. The tools themselves belong
to the LSS engine (Pareto, fishbone structure, five-whys chain, fault tree, hypothesis tests,
regression). The CAPA stores tool run ids and the accepted root cause with the evidence that supports
it. A CAPA cannot move past `investigation` without at least one recorded tool run and an accepted
root cause; the state machine enforces it.

**Statistical effectiveness verification.** The source names this as "the part almost every real
QMS fakes", so it is specified tightly enough that faking it here would fail a test. <!-- docs-lint-ok PROMO-01 verbatim quotation of the source requirement text -->

1. The `VerificationPlan` is declared and frozen **before** `implemented`. The primary metric must
   resolve in the governed metrics layer (E26b). Declaring it afterwards is impossible because the
   state machine refuses the transition without a plan, and the plan is hashed into the audit trail.
2. `post_window_min_n` is computed by the LSS engine's power module from
   `(minimum_detectable_effect, alpha, power, pre_window variance)`. It is never hand-authored.
3. After implementation, a washout period (`washout_s`) is excluded from both windows so the
   transient of the change itself is not measured as the effect.
4. The CAPA sits in `awaiting_evidence` until the post window contains `post_window_min_n`
   observations. It does not decide early on thin data; that is the failure mode being designed out.
5. `verifying` runs the test the LSS assumption checker selects: two-sample t, Welch, Mann-Whitney,
   two-proportion z, or a Poisson rate test, based on data type, normality and variance homogeneity.
   The choice and the assumption-check outputs are recorded.
6. Verdict:
   - `effective`: the test rejects the null in the declared direction and the point estimate meets or
     exceeds the minimum detectable effect. State becomes `closed_effective`.
   - `not_demonstrated`: the test does not reject, or rejects with an effect below the MDE. The CAPA
     reopens with `reopen_reason=effectiveness_not_demonstrated`.
   - `regressed`: the test rejects in the wrong direction. Reopen, and raise a new finding.
7. **Sustain check.** At `implemented_at + sustain_horizon_s` (default 90 sim-days) the same test runs
   again on a fresh window. A regression reopens the CAPA with
   `reopen_reason=regression_at_sustain`. Closing a CAPA is provisional until the sustain
   check passes, which is what "the fix actually held" means.
8. **Multiplicity.** One primary metric per CAPA, declared up front. Secondary metrics are reported
   and explicitly marked non-decisional. Across the CAPA portfolio, the false-effective rate is
   itself measured and published, because the twin knows whether each corrective action truly changed
   the process and can score its own verdicts. The number is a property of this simulation
   under its configured effect sizes, not a statement about quality systems in general, and the
   README says so where it prints it.

### 5.10 Acceptance sampling with switching rules (6a11)

**Standard basis and the licensing decision.** ANSI/ASQ Z1.4 is a copyrighted ASQ standard and its
tables cannot be redistributed in an Apache-2.0 repository. MIL-STD-105E is a United States
Department of Defense publication, and 17 U.S.C. 105(a) states that copyright protection under that
title "is not available for any work of the United States Government" (Cornell Legal Information
Institute, retrieved 2026-08-10, HTTP 200). Its provenance as a government publication is stated by
the NIST/SEMATECH e-Handbook of Statistical Methods, section 6.2.3.1, which records that MIL-STD-105D
was issued by the U.S. government in 1963, was adopted by ANSI in 1971 as Z1.4 and by ISO in 1974 as
ISO 2859, and that the latest revision, MIL-STD-105E, was issued in 1989.

twinflow **builds from MIL-STD-105E**, encodes its tables in `sampling/mil_std_105e/*.yaml`
with the provenance recorded in the file header, describes the capability as "ANSI/ASQ Z1.4-class"
in prose, and documents two differences in `docs/sampling_provenance.md`:

- Z1.4 replaced 105E's Table VIII limit numbers for the normal-to-reduced switch with a switching
  score. twinflow builds both, selected by `sampling.switching_ruleset`. The Z1.4 switching-score
  rules could not be read from the standard itself, which is paid, so `sampling_provenance.md`
  attributes the score rules to the secondary description they were taken from and Open Question 9.2
  records that the author must check them against a licensed copy before release.
- Z1.4 uses "nonconformity" where 105E uses "defective". twinflow uses the modern term in its API
  and records the 105E table reference in `source_table`, so the API reads current while the
  provenance stays exact.

**Plan selection.** `select_plan(lot_size, aql, inspection_level, severity, plan_kind)` returns a
`SamplingPlan`. Inspection levels S-1 through S-4, I, II and III are implemented; II is the default.
Severity is the current switching state for the `(supplier_id, item_id)` pair.

**Inspection.** `inspect_lot` draws a sample of size n from the lot using the lot's true defect rate
(which the sim knows), counts nonconformities, and accepts when `d <= c`. Under double and multiple
plans the second and subsequent samples are drawn per the plan's cumulative accept and reject
numbers.

**Switching rules**, built as an explicit state machine with the rule that fired recorded on every
transition. The conditions below are MIL-STD-105E paragraphs 4.7.1 to 4.7.4 and 4.8, read from the
standard's own text on 2026-08-10, and the paragraph number is carried in the `rule_fired` field so
a reader can check any transition against the source.

| From      | To           | Condition, with the MIL-STD-105E paragraph that states it                                                                                                                                                                                             |
|-----------|--------------|-------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| normal    | tightened    | 4.7.1: 2 out of 2, 3, 4 or 5 consecutive lots rejected on original inspection, ignoring resubmitted lots                                                                                                                                              |
| tightened | normal       | 4.7.2: 5 consecutive lots considered acceptable on original inspection                                                                                                                                                                                |
| normal    | reduced      | 4.7.3, all four: the preceding 10 lots on normal inspection all accepted on original inspection; total nonconformities in those samples at or below the Table VIII limit number; production at a steady rate; reduced inspection considered desirable |
| reduced   | normal       | 4.7.4, any one: a lot rejected; a lot acceptable only under the reduced plan's split accept and reject numbers; production irregular or delayed; other conditions warrant                                                                             |
| tightened | discontinued | 4.8: the cumulative number of lots not accepted in a sequence of consecutive lots on original tightened inspection reaches five                                                                                                                       |

Two details in that table are the ones a reimplementation usually gets wrong, so they are called out.
The normal-to-tightened rule is a sliding window of at most five lots holding two rejections, not a
count of five lots. The discontinuation rule counts *cumulative* lots not accepted on tightened
inspection, not five consecutive rejections, and the two differ whenever an acceptance falls between
rejections.

`discontinued` is absorbing until a corrective action is recorded, not permanently absorbing.
MIL-STD-105E 4.8 states that inspection is not resumed until corrective action has been taken and
that tightened inspection is then used as if 4.7.1 had been invoked, so twinflow raises a
supplier-level finding, blocks acceptance while the state holds, and resumes into `tightened` rather
than into `normal` when the corrective action closes. `sampling_switching_reachability` (7.2) asserts
that `discontinued` is entered only by its declared condition and left only through a recorded
corrective action, and that the resumed state is always `tightened`.

Under `sampling.switching_ruleset: z14_switching_score`, the normal-to-reduced condition uses
switching-score accumulation reaching 30 instead of the Table VIII limit numbers, and the score's
accumulation rules per plan kind are built and unit-tested independently. Those rules carry the
attribution and the confirmation obligation described above.

**OC, AOQ, ATI.** The three definitions below are the NIST/SEMATECH e-Handbook of Statistical
Methods, section 6.2.2, retrieved 2026-08-10, HTTP 200. `oc_curve` computes the probability of
acceptance across incoming quality:

```
binomial (default, for lot_size / n >= 10):  Pa(p) = sum_{d=0..c} C(n,d) p^d (1-p)^(n-d)
hypergeometric (small lots):                 Pa(p) = sum_{d=0..c} C(D,d) C(N-D, n-d) / C(N,n)
AOQ(p)  = p * Pa(p) * (N - n) / N
ATI(p)  = n + (1 - Pa(p)) * (N - n)
AOQL    = max over p of AOQ(p)
```

The model choice is config (`sampling.oc_model`) with the default rule stated above, because using
binomial on a small lot is a real and common error.

Inbound lot rejection emits an NCR against the supplier lot, feeds the supplier scorecard (6a2),
writes a genealogy annotation so every downstream node inherits the "from a rejected-then-sorted lot"
attribute, and posts appraisal COPQ for the inspection labor plus internal-failure COPQ for any
sorting.

### 5.11 Certificate of analysis (6a11)

A CoA is issued per outbound finished lot when `coa.required_for` matches the item or the customer.
Content:

- lot identity: `item_id`, `item_revision` (the as-built revision, which is why E37 and CoA are in
  the same section), lot number, manufacture date, expiry, quantity;
- genealogy digest: the Merkle root covering every genealogy event for that lot, plus the inclusion
  proof bundle reference, so the CoA is verifiable without access to the DC's database (E35);
- test results: one row per specification characteristic with method reference, spec limits, result,
  units, and pass/fail;
- the sampling plan used, including severity and switching state, so the customer can see whether the
  lot was under tightened inspection;
- process context: the batch ids consumed, their golden-batch scores, and any open NCR references;
- release statement with the releasing actor and the meaning of the signature.

**Signature policy.** A CoA release is a regulated act. `coa.release_authority` names the roles
permitted to release. The AI agent may **prepare** a CoA at autonomy tier L1 or L2 but may not
release one; an actor of kind `agent` that tries to release emits a compliance finding
`unauthorised_release_attempt` and is refused. That rule is a test, not a note (see Open Question
9.12 for the author's confirmation).

The CoA renders as JSON (canonical, signed) and HTML (the artifact a person opens). Both are
generated **only** from replayed events, with no reads of live mutable state, so
`coa_derivable_from_log` (7.2) can assert byte-identical regeneration from the event log.

### 5.12 COPQ (6a11)

Four buckets: prevention, appraisal, internal failure and external failure. Those are the four the
source requirement names, so the taxonomy is the requirement rather than a citation, and no
attribution is claimed for it here. Every cost-bearing quality event carries exactly one class,
assigned by `copq_classification.yaml`:

| Class            | Default drivers wired in this repo                                                                                                                                                                                             |
|------------------|--------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| Prevention       | Gage R&R study labor, calibration program, SPC monitoring effort, FMEA sessions, supplier development visits, quality training hours (6a14), preventive maintenance attributable to quality, SOP authoring and revision effort |
| Appraisal        | Incoming AQL inspection labor and consumables, in-process inspection, final inspection, CoA generation, internal and layered process audits, CV audit compute                                                                  |
| Internal failure | Scrap material and labor, rework labor and material, re-inspection, downgrade loss, quality-hold downtime, yield loss below expected, ECO scrap disposition, containment cost                                                  |
| External failure | Returns processing (6a4), warranty and credit, complaint handling labor (6a12), recall execution cost, expedited replacement freight, lost margin from churned customers (6a12)                                                |

`copq_exhaustive_partition` (7.2) asserts that every event carrying a quality cost produces exactly
one posting, that the four bucket totals sum to total quality cost, and that no event is double
counted.

The reported KPIs are COPQ as a percentage of revenue, the prevention-plus-appraisal to failure
ratio, and the trend of each bucket on a control chart. Because twinflow can run paired seeded
configurations, the classic "one dollar of prevention saves ten of internal failure and a hundred of
external failure" claim becomes an experiment rather than a slogan: run the same seed with and
without a prevention program, difference the failure buckets, and publish the observed ratio under
the twin's parameters, including the case where the ratio does not hold. Saying so honestly is the
point.

Postings are emitted as `qms.copq.posted` and consumed by the financial twin (6a17), which owns the
general ledger. This section classifies; it does not post to the GL.

### 5.13 Audit trail with agent attribution (6a11)

The audit trail is append-only by construction. `AuditTrail` exposes `append` and read methods and
nothing else; there is no update, no delete, and no batch rewrite anywhere in the API surface. The
store behind it is the E35 ledger, so append-only is enforced cryptographically and by API
shape.

Every entry records: monotonic sequence, sim-time, the actor, the action, the subject, a digest of
the before and after state, the reason for the change, the evidence references, and the query result
ids backing any number the actor used to justify the action (E26f). The entry carries no wall clock;
the run's single sim-to-wall mapping in the provenance sidecar converts any entry's `sim_time` on
demand, which is what C2 specifies and what keeps the hashed trail reproducible (D-01). For agent
actors the entry also records the autonomy tier (E5), the approving human when the tier requires
one, and the tool call id. The query result ids are what make the trail answer "why did the system
do that", not only "what did it do".

**What the trail is measured against, and what it is not.** Three published texts set the bar.

- 21 CFR 11.10(e) requires "secure, computer-generated, time-stamped audit trails to independently
  record the date and time of operator entries and actions that create, modify, or delete electronic <!-- docs-lint-ok STE-TERM-WORD verbatim quotation of 21 CFR 11.10(e) -->
  records", and states that "record changes shall not obscure previously recorded information" <!-- docs-lint-ok STE-01 verbatim quotation of 21 CFR 11.10(e) -->
  (eCFR, title 21 as in force 2026-01-01, retrieved 2026-08-10, HTTP 200). Append-only with a
  before-and-after digest per entry is how twinflow meets the second sentence.
- 21 CFR 11.10(d) and 11.10(g) call for limiting system access to authorized individuals and for
  authority checks so that only authorized individuals can electronically sign a record. That is the
  `AuthorityOracle` binding and the CoA release rule in 5.11.
- 21 CFR 11.50(a) requires a signed electronic record to carry the printed name of the signer, the
  date and time the signature was executed, and the meaning associated with the signature. twinflow's
  signature manifestation carries all three, with the signing time recorded as sim-time and resolved
  to wall-clock through the run mapping.

ALCOA is a data-integrity expectation, not a Part 11 clause, and the two are cited separately for
that reason. The FDA guidance *Data Integrity and Compliance With Drug CGMP: Questions and Answers*
(December 2018), section III.1.a, states that complete, consistent and accurate data "should be <!-- docs-lint-ok STE-01 verbatim quotation of the FDA guidance -->
attributable, legible, contemporaneously recorded, original or a true copy, and accurate (ALCOA)".
The third element is "original or a true copy", which matters here: the ledger holds the original
and the dashboard renders a true copy derived from it.

The README states plainly that this is a laptop-scale nod to those expectations, that twinflow is
not a validated system, and that no claim of regulatory compliance is made. Claiming otherwise would
be the exact overreach this repository exists to avoid.

`audit_trail_append_only`, `ledger_tamper_detected` and VAL-GATE-QMS-8 (7.2, 7.3) are the tests that
make the append-only claim checkable rather than aspirational.

### 5.14 Audit checklists as code, and layered process audits (6a11)

**Checklists.** One YAML file per checklist under `checklists/`, versioned in git, validated against
`/schemas/checklist.v1.json`.

```yaml
checklist_id: cl_production_control
version: 3
clause_refs:
  - {
      standard: "iso9001:2015",
      clause: "8.5.1",
      local_label: "production and service provision control",
    }
  - {
      standard: "iso9001:2015",
      clause: "7.1.5",
      local_label: "monitoring and measuring resources",
    }
applies_to: { stage_ids: [coat, cure, form], shifts: [A, B, C] }
questions:
  - question_id: q1
    text:
      "Is every CTQ characteristic at this stage under an active control chart with limits
      recomputed within the configured recalculation interval?"
    clause_ref: { standard: "iso9001:2015", clause: "8.5.1" }
    evidence_query:
      kind: metric
      metric: spc_chart_freshness_days
      dimensions: { stage_id: "$stage" }
    pass_predicate: { op: "<=", value: 30 }
    nonconformity_class_on_fail: minor
  - question_id: q2
    text:
      "Do all measuring devices feeding this stage have a Gage R&R study within the
      configured validity period, with %R&R below the configured limit?"
    clause_ref: { standard: "iso9001:2015", clause: "7.1.5" }
    evidence_query:
      {
        kind: metric,
        metric: msa_pct_rr_max,
        dimensions: { stage_id: "$stage" },
      }
    pass_predicate: { op: "<", value: 30 }
    nonconformity_class_on_fail: major
```

Two properties make this more than a form. First, every question is answered by an **executed
evidence query** against the historian through the governed metrics layer, so an audit result is
evidence-backed and reproducible rather than an auditor's opinion. Second, the checklist version is
recorded on every audit result, so a historical audit can be re-run against its own version and
produce the same answer; changing a checklist does not retroactively change history.

ISO 9001 text is copyrighted. twinflow references clause **numbers** and writes its own question
wording; it does not reproduce clause text. `local_label` is twinflow's own short descriptor. This is
stated in `checklists/README.md` and is Open Question 9.6.

**Layered process audits.** LPA is short, frequent, multi-layer verification of high-risk steps.
Config declares layers and frequencies:

```yaml
lpa:
  layers:
    - {
        layer: 1,
        auditor_role: team_lead,
        frequency: per_shift,
        questions_per_audit: 5,
      }
    - {
        layer: 2,
        auditor_role: area_supervisor,
        frequency: weekly,
        questions_per_audit: 8,
      }
    - {
        layer: 3,
        auditor_role: plant_manager,
        frequency: monthly,
        questions_per_audit: 10,
      }
  coverage:
    max_interval_days_per_station: 7
    question_pool: cl_production_control
    selection: weighted_by_recent_failures # or round_robin, or random_seeded
```

The scheduler generates `qms.lpa.scheduled` events on the sim calendar and consumes auditor
availability from the rostering layer (E23), so an LPA that cannot be staffed is a missed audit, and
a missed audit is a finding (`lpa_missed`). Scoring produces LPA completion rate, first-time-pass
rate per question, and a repeat-failure Pareto that identifies which questions keep failing and
where. `lpa_coverage` (7.2) asserts every station is audited by at least one layer within
`max_interval_days_per_station`.

### 5.15 The mock recall drill (6a11)

The showcase demo, in the source's own words. `run_recall_drill(scope, budget)` takes any `TraceScope` variant. <!-- docs-lint-ok VOCAB-01 the source requirement names this the showcase demo -->

**Traversal.** Forward closure from the anchor over `consumed_by`, `derived_from` and `contains`
edges, then out through shipment and order edges to customers. Backward closure from the anchor to
identify sibling exposure (other outputs of the same raw lot). `EquipmentContactScope` also
walks `equipment_id` on edges within a time window, which catches cross-contamination exposure that
material lineage alone misses.

The walk order is the declared order of 2.2: a breadth-first frontier sorted by
`(sim_time, node_id)`, with every returned bucket sorted by node id (D-03). Two drills over the same
graph return byte-identical reports, which is what lets the drill's output be a golden
file at all.

**Blast radius returned**: raw lots, production batches, WIP lots, finished lots, pallets, cartons,
serialized units, storage locations, customer orders, shipments split by state (staged, in transit,
delivered), customers, open purchase orders (relevant when scoping by revision), and the quantity in <!-- docs-lint-ok STE-TERM-WORD purchase order is the domain term -->
each bucket.

**Recall-readiness report** fields:

- `qty_produced`, `qty_accounted` (located in inventory, in transit, or confirmed delivered),
  `qty_unlocated`, and mock recall effectiveness `= qty_accounted / qty_produced`;
- time to identify, expressed as `elapsed_sim_s` and `graph_edges_walked`, both of which are
  reproducible;
- the quarantine action set that would be issued, with `qms.quarantine.requested` emitted in
  execute mode and withheld in dry-run mode;
- the customer contact list ordered by exposed quantity, then by contract tier (6a12), then by
  customer id, so ties break the same way on every run;
- the verification bundle: the Merkle root, and an inclusion proof for every genealogy event in the
  trace, so a regulator or customer can check the trace without trusting twinflow's database (E35).

The drill's real elapsed time is a performance measurement, not a result. It is taken by the
observability exporter, written to the run's provenance sidecar as `recall_drill_elapsed_ms`, and
never entered into an event payload or the report body (D-02). That is why the report can be a
golden file while the timing still feeds VAL-GATE-QMS-7 and the A4 curves.

**Ground truth.** Because the twin injected the contamination, the true blast radius is known
exactly, so precision and recall against it are measurable rather than estimated. VAL-GATE-QMS-6
asserts precision and recall of 1.0 against that ground truth. The claim the README makes is exactly
that and no more: this is a measurement against synthetic injected truth, which is available here
because the data is synthetic, and is not a comparison against any other system.

**Timing.** VAL-GATE-QMS-7 measures p95 elapsed time at a stated graph size on a named runner class
and compares it against a recorded baseline. The measurement feeds the A4 scaling curves.

### 5.16 The business-system loop (6b)

**ERP stub and ASN.** The ERP stub issues `erp.expected_receipt.published` shaped as the
Shipment-Order-Tare-Pack-Item hierarchy that the ASC X12 856 Advance Ship Notice carries. That
standard is copyrighted and paid, so twinflow models the hierarchy's shape under its own field names
and reproduces none of its text (Open Question 9.6).

Modeling the hierarchy rather than a flat line list matters because the reconciliation logic depends
on it: an RFID portal reads pallet-level and item-level tags, and knowing which items were expected
on which pallet is what turns "we are two short" into "pallet SSCC 0042 is two short".

**Three-way reconciliation.** For each ASN line, three counts exist: expected (ASN), RFID observed,
and CV observed. The disambiguation matrix:

| Expected        | RFID | CV  | Classification       | Consequence                                                                                                                                           |
|-----------------|------|-----|----------------------|-------------------------------------------------------------------------------------------------------------------------------------------------------|
| E               | E    | E   | `match`              | receipt posted                                                                                                                                        |
| E               | E-k  | E   | `read_failure`       | E46 read-zone finding, portal read-rate control chart, no supplier NCR                                                                                |
| E               | E-k  | E-k | `genuine_short`      | supplier NCR, scorecard hit (6a2), three-way match exception (6a13)                                                                                   |
| E               | E    | E-k | `cv_count_failure`   | CV model finding, no supplier NCR                                                                                                                     |
| E               | E    | E+k | `cv_count_failure`   | CV model finding, no supplier NCR                                                                                                                     |
| E               | E+k  | E+k | `overship`           | supplier NCR (minor), inventory adjustment                                                                                                            |
| E               | E+k  | E   | `cross_read`         | E46 cross-read finding at the neighboring portal                                                                                                      |
| E               | 0    | 0   | `not_arrived_yet`    | partial-arrival timer, escalates to `missing` after the configured window                                                                             |
| absent from ASN | k    | k   | `unexpected_receipt` | ASN exception, procurement notified                                                                                                                   |
| any             | any  | any | `channels_disagree`  | catch-all when both channels differ from expected and from each other in opposite directions; both a portal finding and a CV finding, no supplier NCR |

The last row is the residual class, and it exists so that the classifier is total. The eight rows
above it do not cover every combination of two independent counts, and a classifier with a hole
either crashes or silently guesses. `channels_disagree` carries both channel deltas so the
disagreement is visible, and `reconciliation_total` (7.2) asserts that the ten classes partition the
outcome space for arbitrary generated count triples, which is a claim the table can now actually
support.

Lot-level and revision-level mismatches are orthogonal classes carried alongside the quantity class:
`wrong_lot` and `wrong_revision`. The second exists because E37 makes revision a receivable
attribute, and receiving the superseded revision after an ECO effectivity date is an expensive
error that a quantity-only reconciler cannot see.

The classification carries a confidence, because in the presence of a known-degraded portal the
read-failure and genuine-short hypotheses are not equally likely. Confidence is computed from the
portal's current read-rate control-chart state and the CV channel's measured accuracy, both of which
the system already tracks. VAL-GATE-BIZ-1 measures classification accuracy against the sim's injected
ground truth and publishes the confusion matrix, including the genuinely ambiguous cells.

**Mini CMMS.** A PdM finding (`pdm.threshold_crossing.estimated`) creates a work order with:

```
priority_score = w_rpn * normalize(rpn)
               + w_deferral * normalize(deferral_cost_slope_per_day)
               + w_safety * safety_multiplier
               + w_criticality * asset_criticality
```

with all weights in config and every term recorded on the work order so the ranking is explainable.

**Cost of deferral, twin-quantified.** This is the requirement's sharpest phrase and it is
implemented literally. For a candidate deferral of d days:

```
total_expected_cost(d) = P_fail(<= d) * E[cost_unplanned_failure]
                       + (1 - P_fail(<= d)) * cost_planned_intervention(d)
```

- `P_fail(<= d)` comes from the PdM layer's time-to-threshold distribution, not from a point
  estimate.
- `E[cost_unplanned_failure]` is computed **by running the twin**: R paired replications with common
  random numbers, identical seeds, differing only in whether the asset fails at the modeled time.
  The difference in throughput, overtime, expedite freight, scrap, and service-level penalty is the
  cost. Common random numbers are used deliberately as a variance-reduction technique so the
  difference is attributable to the failure rather than to seed noise, and a test asserts that the
  two runs' event logs are byte-identical up to the injection point on a pinned platform (D-05).
  Pairing is only valid when both arms draw the same number of values from every shared stream, so
  the runner's `crn_integrity` record is consulted first and a paired estimator is used only when it
  reports exact pairing; otherwise the independent-samples estimator runs and the report says which
  one was used and why.
- `cost_planned_intervention(d)` includes the production impact of the maintenance window, which
  depends on when in the schedule the window falls, so deferring into a planned changeover is cheaper
  than deferring into a peak shift. The scheduler (5.5) supplies that.

The output is a `deferral_cost_curve` with confidence intervals, published as
`cmms.deferral_cost.estimated`, and the recommended window is the argmin subject to the constraints
(parts availability, skill availability from 6a14, production window policy from 6a15). The agent
presents the curve, not just the recommendation, because the shape of the curve is the argument.

Work orders carry the E48 runbook reference and the E8 SOP clause references for the procedure.
Completion updates MTBF and MTTR and closes the source finding. A repeat failure on the same asset
within `cmms.repeat_failure_window_s` escalates to a problem record in the ITSM layer (6a15).

### 5.17 Digital product passport (E10)

The DPP is a projection of the genealogy graph into the data shape that Regulation (EU) 2024/1781 of
the European Parliament and of the Council of 13 June 2024, establishing a framework for the setting
of ecodesign requirements for sustainable products (ESPR), sets up in its Chapter III (EUR-Lex,
OJ L, 2024/1781, 28.6.2024, retrieved 2026-08-10, HTTP 200). Three of its provisions drive the model
below.

- Article 9(1) makes the passport a condition of placing a product on the market, and requires the
  data in it to be accurate, complete and up to date.
- Article 9(2) leaves the specifics to delegated acts adopted under Article 4, which "shall, as <!-- docs-lint-ok STE-01 verbatim quotation of ESPR Article 9(2) -->
  appropriate for the product groups covered, specify" the data to be included, one or more data
  carriers, whether the passport is at model, batch or item level, and, in point (f), "the actors
  that are to have access to data in the digital product passport and to what data they are to have
  access".
- Article 12 requires unique operator and facility identifiers to comply with the standards named in
  Annex III or equivalent European or international standards.

Point (f) is the reason role-scoped access is modeled rather than mentioned, and Article 9(2) is the
reason no conformance claim is made below.

**Identity.** Each passport is addressed by a GS1 Digital Link URI built from the item's GTIN plus
the batch or lot (application identifier 10) and, for serialized items, the serial (AI 21):

```
https://id.twinflow.example/01/09506000134352/10/L4471
https://id.twinflow.example/01/09506000134352/21/SN00042851
```

The GTIN in the examples is a syntactically valid GS1 documentation GTIN with a correct check digit,
and the company prefix is synthetic and not licensed from GS1, which 6.4 makes the load-time warning
say out loud. The resolver is a static route in the dashboard and in the E1 replay viewer, so a
passport is a link a reader can open. The data carrier modeled is a QR Code encoding the Digital
Link URI. ESPR Article 9(2)(b) leaves the choice of carrier to the delegated act for each product
group, so twinflow models one carrier and claims nothing about the carrier any delegated act will
name.

**Attribute groups**, each attribute annotated with the event that sourced it:

| Group                 | Attributes                                                          | Source                                               |
|-----------------------|---------------------------------------------------------------------|------------------------------------------------------|
| Identification        | GTIN, lot, serial, item revision, manufacturer GLN, production date | `genealogy.transformation`, `plm.item.revised`       |
| Composition           | component lots, materials, substances-of-concern flags              | BOM explosion plus `genealogy.transformation` inputs |
| Carbon                | cradle-to-gate kgCO2e                                               | E17 ledger inheritance through genealogy             |
| Durability and repair | spec characteristics, expected life, spare-part item ids            | PLM item attributes                                  |
| Circularity           | recycled-content fraction, disposition history, recovery route      | 6a4 returns disposition                              |
| Compliance            | CoA reference, inspection severity at release, open NCR references  | `qms.coa.issued`, `qms.ncr.raised`                   |
| Chain of custody      | custody transfers with signing parties                              | `genealogy.custody_transfer`, E35 signatures         |
| Verification          | Merkle root, inclusion proof bundle                                 | E35                                                  |

**Access roles.** `PassportAudience` is one of `public`, `customer`, `regulator`, `recycler`,
`internal`. Each attribute declares the minimum audience that may see it, and `render_passport`
filters accordingly. This is the Article 9(2)(f) mechanic, so it is modeled rather than mentioned,
and `test_passport_audience_filter_is_total` asserts every attribute declares an audience and that no
rendering for a lower audience contains a higher-audience attribute.

**Honest limitation, stated in the README and in `docs/dpp.md`.** twinflow builds the DPP data model,
the identifier scheme, the access-role mechanics and the verification path. It claims no conformance
to any delegated act's data requirements, because Article 9(2) leaves those to product-group
delegated acts adopted under Article 4 and they are still being issued. The claim made is narrower
and checkable: genealogy at this granularity is the input a passport needs, and here are the data
model, the resolver and the access filter.

### 5.18 Tamper-evident ledger, signatures and EPCIS 2.0 (E35)

**Canonicalisation.** Every payload is serialized with the RFC 8785 JSON Canonicalization Scheme
before hashing. This is not a detail: a canonicalisation bug produces signatures that check out on
the writer and fail on the reader, which is the classic and hard-to-debug failure of homegrown
ledgers. RFC 8785 carries its own vectors in three places, and VAL-GATE-LEDGER-2 runs all three:
section 3.2.3 gives a seven-key object and the exact sorted order its property names must take,
section 3.2.4 gives the canonical UTF-8 output of a sample document as a hexadecimal byte sequence,
and Appendix B Table 1 gives twenty-two IEEE 754 doubles with their required JSON serializations,
including the edge cases that break naive number printers.

**Merkle tree.** RFC 6962 (Certificate Transparency, June 2013) section 2.1 definitions, used
verbatim:

```
MTH({})        = SHA-256()
MTH({d0})      = SHA-256(0x00 || d0)
MTH(D[n])      = SHA-256(0x01 || MTH(D[0:k]) || MTH(D[k:n]))     k = largest power of 2 < n
```

The RFC states the reason for the two prefixes directly: "the hash calculations for leaves and nodes
differ. This domain separation is required to give second preimage resistance." That is why a
published definition is used rather than an invented one. Audit paths (inclusion proofs) and
consistency proofs follow RFC 6962 sections 2.1.1 and 2.1.2, and the verification algorithms follow
RFC 9162 (Certificate Transparency Version 2.0, December 2021) sections 2.1.3.2 and 2.1.4.2, which
state them as explicit procedures where RFC 6962 states only the structure. VAL-GATE-LEDGER-1 checks
against the worked seven-leaf example in RFC 6962 section 2.1.3, which enumerates the audit path for
four named leaves and the consistency proof between four named tree pairs.

**Chain.** Entries are appended and blocks are sealed every `ledger.block_max_entries` entries or
`ledger.block_max_interval_s` sim-seconds, whichever comes first. Both bounds are sim-time bounds, so
sealing happens at the same point in every replay of a run. A block header carries the previous
block's header hash, the Merkle root over that block's entries, the tree size, the sim-time of
sealing and the sealing party, and no wall clock (3.3, D-01). `verify_chain` checks header linkage
and per-block Merkle roots. Tampering with any entry changes its leaf hash, which changes the root,
which breaks the chain from that block forward.

**Signatures.** Ed25519 (RFC 8032). Ed25519 is chosen over ECDSA for a reason specific to this
repository: RFC 8032 section 8.2 states that "EdDSA signatures are deterministic", so the same seed
and config produce the same signature bytes, and the ledger can sit inside a hashed event log. A
randomized signature scheme would change the log on every run and quietly break the determinism hash
check. Under D-05 the resulting claim is the two-tier one: byte-identical on a pinned platform with a
pinned dependency set, and value-equivalent across platforms, which for the ledger means the same
entries in the same order producing the same roots, since every hashed input is an integer, a byte
string or a canonicalised JSON document rather than a float.

Test keys are derived from the run seed with HKDF, generated at runtime, and never committed. There
are no keys in the repository. The README says explicitly that these are throwaway simulation keys
and that no claim of real-world cryptographic assurance is made.

`SignaturePolicy` declares, per event type, the required signing roles and the threshold:

```yaml
signature_policy:
  genealogy.custody_transfer:
    required_roles: [transferor, transferee]
    threshold: 2
  qms.coa.issued:
    required_roles: [quality_release_authority]
    threshold: 1
    forbid_actor_kinds: [agent]
  genealogy.transformation:
    required_roles: [manufacturer]
    threshold: 1
```

An entry that does not satisfy its policy is appended with a `policy_unsatisfied` marker and raises a
finding; it is not silently dropped, because silently dropping records is precisely what a tamper-
evident log must not do.

**The trust model, stated honestly.** A permissioned hash chain with multi-party signatures gives
tamper-evidence and third-party verification. It does not prevent **withholding**: an operator who
controls the log can decline to publish an entry. twinflow models the standard mitigation: block
roots are periodically published to counterparties (`ledger.root.published`), and a counterparty who
holds an entry whose inclusion proof does not check out against a published root has cryptographic
evidence of withholding. The README states this precisely, along with the design conclusion the
source asks for: a permissioned hash chain with signatures delivers the tamper-evidence and
multi-party verification that matter here, and a public chain would add cost without adding trust.

**GS1 EPCIS 2.0.** Genealogy events are projected into EPCIS events in the JSON/JSON-LD binding of
the GS1 EPCIS Standard, Release 2.0, ratified June 2022 (ref.gs1.org/standards/epcis, retrieved
2026-08-10, HTTP 200), whose section 10 defines that binding. The event types below are its sections
7.4.2 to 7.4.6.

| twinflow event               | EPCIS 2.0 type and section                                | Key fields                                                                                                                    |
|------------------------------|-----------------------------------------------------------|-------------------------------------------------------------------------------------------------------------------------------|
| `genealogy.transformation`   | `TransformationEvent`, 7.4.5                              | `inputEPCList`/`inputQuantityList`, `outputEPCList`/`outputQuantityList`, `bizStep: commissioning`, `ilmd` for lot attributes |
| `genealogy.aggregation`      | `AggregationEvent`, 7.4.3                                 | `parentID` (SSCC), `childEPCs`, `action: ADD`/`DELETE`, `bizStep: packing`                                                    |
| `genealogy.custody_transfer` | `ObjectEvent`, 7.4.2, with `sourceList`/`destinationList` | `bizStep: shipping` with `disposition: in_transit`; `bizStep: receiving` with the disposition omitted                         |
| order linkage                | `TransactionEvent`, 7.4.4                                 | `bizTransactionList` with PO and shipment references                                                                          |
| AMR or asset pairing         | `AssociationEvent`, 7.4.6                                 | `parentID` asset, `childEPCs`                                                                                                 |
| telemetry attached to a lot  | `sensorElementList` on any event                          | EPCIS 2.0 sensor data, used for cold-chain excursions and in-line measurements                                                |

The receiving row omits the disposition on purpose. The GS1 Core Business Vocabulary Standard,
Release 2.0, ratified June 2022, notes that "omission of disposition is generally recommended instead
of `in_progress`, which adds little value to event data", so twinflow follows the vocabulary's own
guidance rather than filling the field for symmetry. A projection that emits `in_progress` fails
`test_receiving_event_omits_disposition`.

The `sensorElementList` mapping is the one that matters most here: EPCIS 2.0 added sensor data to
traceability events, and twinflow already attaches telemetry to lots, so cold-chain excursions and
in-line measurements ride the standard interoperability format rather than a bespoke side channel.

Identifiers: `sscc` for pallets and cartons (logistic units), `lgtin` for lot-level trade item
classes, `sgtin` for serialized units, `gln` for read points and business locations. Vocabulary
values for `bizStep` and `disposition` come from the GS1 Core Business Vocabulary Standard, Release
2.0, whose canonical form for a business step is `https://ref.gs1.org/cbv/Bizstep-<name>`.

Emitted documents validate against the GS1-published EPCIS 2.0 JSON schema (VAL-GATE-LEDGER-4), and
GS1's published example documents are parsed and re-serialized for a round-trip semantic-equality
check. Whether those artifacts can be vendored or must be fetched at test time depends on their
license; see Open Question 9.3.

### 5.19 PLM and engineering change management (E37)

**Revisions.** A revision is created only through an ECO. `Revision.interchangeability` is required
and drives everything downstream, because whether a superseded revision can still be used is the
question that
determines disposition, PO handling and recall scope.

**ECO lifecycle**: `draft -> review -> approved -> released -> effective -> closed`, with `canceled`
reachable from any pre-effective state. Approvals are checked against the authority matrix owned by
6a17, through a `AuthorityOracle` protocol so PLM does not import finance.

**Effectivity.** Three kinds, all implemented:

- `DateEffectivity(from_time, to_time)`: the new revision applies to anything started at or after
  `from_time`.
- `LotEffectivity(from_lot)`: applies from a named lot forward, which is how process industries do it.
- `SerialEffectivity(from_serial)`: applies from a named serial forward, which is how discrete
  industries do it.

`resolve_revision(item_id, at_sim_time, lot=None, serial=None) -> str` is a **total** function over
the configured horizon: for any item and any time in the horizon, it returns exactly one revision. It
raises on ambiguity at config-load time rather than at runtime, and `effectivity_totality` (7.2)
asserts totality and release-order monotonicity by property test.

**As-built versus as-designed.** A batch or unit that started before effectivity keeps the revision
it was built to, recorded on its genealogy node. The current BOM is as-designed; genealogy is
as-built. Confusing the two is the defect that makes real recalls over-scope or under-scope, so the
recall drill reads genealogy exclusively and never the current BOM.

**Disposition.** For each stock location holding the superseded revision at effectivity:

```
use_up_horizon_days = on_hand_qty / forecast_consumption_rate_per_day
decision:
  if interchangeability == fully:                      use_up
  elif use_up_horizon_days <= eco.max_use_up_days:     use_up   (effectivity may be delayed to suit)
  elif rework_cost < scrap_cost and reworkable:        rework
  else:                                                scrap    (posts internal-failure COPQ)
```

`eco.max_use_up_days` and the rework feasibility flags are config. The use-up-versus-scrap tradeoff
is itself a what-if: "set effectivity six weeks out and use up 1,200 units, versus cut over
immediately, scrap 300 units, and avoid the field failures the superseded revision causes", priced by the
financial twin and judged by the LSS engine.

**Propagation.** `propagate_eco` produces a `PropagationPlan` covering:

- **Open purchase orders.** For every open PO line for an affected item, the plan chooses `amend` <!-- docs-lint-ok STE-TERM-WORD purchase order is the domain term -->
  (new revision, supplier acknowledgement required), `allow_old_rev` (use-up applies), or `cancel`,
  and emits `plm.po_change.requested` for procurement (6a13) to execute. Receiving the superseded revision
  after an `amend` becomes the `wrong_revision` reconciliation class in 5.16.
- **Standard costs.** `rollup_standard_cost` explodes the new BOM, multiplies by component standard
  costs, adds routing labor and overhead at the configured rates, and emits
  `plm.standard_cost.revised`. Finance (6a17) consumes it, revalues inventory, and rebaselines
  purchase price variance. Rounding is banker's rounding at the configured currency precision, stated <!-- docs-lint-ok STE-TERM-WORD purchase price variance is the domain term -->
  in config, so the rollup is exactly reproducible.
- **In-flight WIP.** Batches already started are untouched; their as-built revision stands.
- **Downstream references.** Kanban loops, safety stock parameters, slotting entries and SOP
  `applies_to` selectors that reference the affected item are marked stale and regenerated, and a
  stale reference that is not regenerated before effectivity is a finding.
- **CAPA linkage.** When `eco.source_capa_id` is set, the CAPA's corrective action is the ECO, and the
  CAPA's effectiveness verification window starts at the ECO's effectivity date rather than its
  approval date. Getting that wrong is how real CAPA systems clear a fix that had not yet reached
  the floor.

**Recall by revision.** `RevisionScope(item_id, rev_from, rev_to)` walks genealogy for nodes whose
as-built `item_revision` falls in the range and returns their forward closure. VAL-GATE-PLM-3 asserts
this returns exactly the units built to the affected revisions, not the units of that item built
before or after.

### 5.20 SOP grounding via retrieval with clause-level citation (E8)

**Corpus.** SOPs are markdown files under `sops/`, one file per SOP revision, with required front
matter:

```markdown
---
sop_id: RCV-002
revision: r3
title: Inbound pallet staging
owner_role: receiving_supervisor
effective_from: 2026-02-01T06:00:00Z
effective_to: null
state: effective
applies_to:
  stations: [dock_1, dock_2, dock_3]
  equipment: [portal_a, portal_b]
  product_families: [dry_goods]
---

## 4. Staging

### 4.2 Zone assignment

Staged pallets must be placed in the zone printed on the pallet license plate. A pallet whose
zone cannot be read is staged in the exception lane and escalated to the supervisor.
```

`parse_sop` produces a `ClauseIndex` where each numbered heading becomes a `SopClause` with a stable
anchor `sop:RCV-002@r3#4.2`, its text, its character span in the source file, and structured `refs`
extracted from the text and the front matter (station ids, equipment ids, defect codes, spec
characteristic ids).

**Retrieval.** Hybrid and local by default:

1. Lexical: BM25 over clause text.
2. Dense: sentence-transformer embeddings, available under the `[dense]` extra and reached only
   through the kernel `Inference` port with a pinned model digest, a fixed seed, one thread and
   deterministic kernels (2.6, D-04). If the extra is not installed, retrieval runs BM25-only and
   reports `mode: lexical_only`, so the five-minute quickstart never needs a model download.
3. Fusion: reciprocal rank fusion over the two rankings, with the RRF constant in config. Ties in
   the fused score break on `(-score, clause_id)`, an explicit total order, so the ranking is the
   same on every run and on every platform (D-03).
4. **Structural eligibility filter, applied before scoring, not after.** A clause is eligible only if
   its `applies_to` selector matches the violation's station, equipment and product family. This is
   the step that makes citations correct rather than merely plausible, and the ablation in
   VAL-GATE-SOP-1 measures how much it buys instead of asserting it.

**Citation contract.** A finding that claims an SOP violation must carry at least one `Citation` with
the clause id, the quoted span and its character offsets, so the dashboard highlights the exact
sentence. If no eligible clause clears `retrieval.min_score`, the system **abstains**: it emits
`sop.citation.abstained` and the finding is downgraded from `sop_violation` to
`undocumented_deviation`. It never invents a clause and never cites an ineligible one. The abstention
path is tested directly (`sop_citation_or_abstain`, 7.2), and the downgrade is visible on the
dashboard because "we saw something wrong but no standard covers it" is a real and useful finding
class in its own right.

**Time-travel citation.** Retrieval runs against the SOP revision **effective at the violation's
sim-time**, resolved by `effective_at(sop_id, sim_time)`, not against the current revision. A
violation from March cites March's revision even after an April revision exists. Getting this wrong
makes every historical finding un-auditable, so it is a named test (VAL-GATE-SOP-2).

**Reuse for audit checklists.** The same `ClauseIndex` machinery indexes the audit-checklist clause
map (5.14), so audit questions and SOP clauses share one retrieval implementation. That is why the
`twinflow-sop` clause index lands with 6a11 rather than waiting for Phase 4 (see 8).

**Evaluation.** The eval set is generated by construction: the sim injects a violation of a
**specific** clause, so ground truth is exact. Metrics are precision@1, recall@3 and wrong-clause
rate, published in the README alongside the corpus size and the number of injected violations behind
each figure. VAL-GATE-SOP-1 states how those numbers are checked, and why they are checked against a
recorded baseline rather than against a threshold nobody published.

### 5.21 Telemetry-grounded generative SOPs (E24)

**Evidence bundle.** `draft_sop(process_id, evidence_bundle)` takes a structured bundle assembled
from the twin's own artifacts, never from free text:

- golden-batch profiles for the process, with the CPP setpoints and envelopes;
- CAPA history for the process, with accepted root causes and the corrective actions that verified
  effective;
- alarm rationalization records (which alarms fire, at what rates, with what operator response);
- process-mining output from `twinflow-procmine`, the Apache-2.0 miner written here rather than
  PM4Py (D-14): the discovered dominant variant and the rework loops, so the SOP documents what the
  process actually does rather than what someone remembers;
- measured standard work: per-step cycle times from the twin with their distributions;
- ergonomic profile and PPE requirements for the station (6a10);
- required certifications for the station (6a14);
- E48 failure runbooks for the equipment involved.

**Output shape.** The draft is a structured `SopDraft`, never free text, with fixed sections:
Purpose, Scope, Responsibilities (roles resolved from the skills matrix), Materials and Equipment,
Safety, Steps, Records, References, Revision history. Each `Step` carries: action text, actor role,
target station, expected duration with its source query, acceptance criterion with its tolerance
drawn from the spec limits, and the telemetry signal that evidences completion. Structured output is
schema-constrained (E26d), so a malformed draft is impossible by construction.

**The model never steers the simulation (D-04).** Drafting is a language-model call, and a language
model is not deterministic enough to sit inside a hashed tape. It reaches the run only through the
kernel `Inference` port. In simulation mode the port is bound to a recorded-response adapter, so a
replay reuses the recorded draft rather than regenerating it. The tape records the draft that was
produced, its `model_ref` digest and its `prompt_digest`; it never records a promise to recompute
one. A run whose recorded response is missing fails loudly instead of calling out to a live model.

**Grounding gate.** Every number appearing anywhere in a generated SOP must map to a logged
`query_result_id`. The E26(f) grounding checker runs over the rendered draft, and a draft containing
an unmatched number is rejected, not published. `sop.draft.generated` carries the `grounding_report`
with `numbers_total` and `numbers_grounded`, and CI asserts a 100 percent rate on the eval corpus
plus a negative test where an ungrounded number is injected and must be caught (VAL-GATE-SOP-3).

**Document control.** Drafts enter the QMS document lifecycle: `draft -> in_review -> approved ->
effective -> superseded -> obsolete`. Approval requires a human role from the authority matrix; the
agent drafts and revises but does not approve. Publishing a new effective revision emits training
requirements to 6a14; an operator executing an effective revision they are not trained on is a
compliance finding (`untrained_execution`). Training records gate station assignment in the rostering
optimizer (E23).

**Adherence as a measurable variable.** Each SOP revision has a computed `clarity_score` (a
transparent formula over step count, decision points, average sentence length, undefined-term count
and reading-level proxy, all published in `docs/sop_clarity.md`) and the adherence model maps SOP
quality to operator behavior:

```
logit(adherence_p) = a0
                   + a1 * clarity_score_z
                   + a2 * training_recency_score
                   + a3 * tenure_score
                   - a4 * step_count_z
                   - a5 * fatigue_index          # from 6a10
```

Every coefficient is config, and `docs/sop_adherence.md` states plainly that these coefficients are
chosen to produce plausible behavior, not fitted to field data, because claiming otherwise would be
a fabricated empirical result. What the model buys is a closed loop that can be measured inside the
twin: a worse SOP lowers adherence, lower adherence produces more CV-detected violations, violations
produce NCRs, the CAPA's corrective action is an SOP revision, the revision raises clarity, adherence
rises, and the LSS engine's hypothesis test says whether the improvement is real. `E2E-SOP-005` runs
that whole loop end to end on a fixed seed.

Monotonicity of the adherence model is a property test (7.2): raising clarity never lowers adherence,
raising fatigue never raises adherence.

### 5.22 Takt discipline and level loading between stages (6a9)

The source asks for WIP and takt discipline between stages, with push versus pull as a config choice
and kanban card counts as a tunable. 5.6 owns the second half. This subsection owns the first.

**Takt.** `compute_takt(window)` returns a `TaktProfile` per stage:

```
available_time_s   = shift seconds in the window minus planned breaks and planned downtime
takt_time_s        = available_time_s / demand_units_in_window
cycle_time_s       = measured mean cycle time at the stage over the window
takt_ratio         = cycle_time_s / takt_time_s
```

`takt_ratio` above 1 means the stage cannot meet demand at the current staffing and speed;
`takt_ratio` well below 1 means the stage is overbuilt relative to the drumbeat. Demand comes from
the planning layer's released schedule, never from what the stage happened to produce, because a
takt computed from actual output is a tautology that always looks healthy.

Two findings come out of it. `takt_exceeded` fires when a stage's `takt_ratio` stays above
`takt.ratio_ceiling` for `takt.consecutive_windows` consecutive windows, which is what keeps a single
slow window from raising an alarm. `takt_starved` fires on the mirror condition below
`takt.ratio_floor`. Both are ordinary findings and reach the NCR engine through the same path as
everything else.

**Level loading.** `level_load(schedule, horizon)` returns a `LevellingReport` measuring how uneven
the released mix is across the horizon, and it measures rather than lectures:

```
for each bucket b in the horizon and each product family f:
    units[b][f]                     = released units
mix_deviation      = mean over b of sum over f of abs(share[b][f] - share_target[f])
volume_cv          = stdev over b of total units[b] / mean over b of total units[b]
changeover_burden  = total setup seconds implied by the released sequence / available_time_s
levelling_index    = 1 - clamp01(w_mix * mix_deviation + w_vol * volume_cv + w_chg * changeover_burden)
```

The three weights are config and sum to 1, and `docs/leveling.md` states that `levelling_index` is
twinflow's own composite, not a published index, so nobody reads it as a standard metric. What makes
it useful is that it is comparable across scenario arms of the same configuration, which is the only
comparison the what-if engine ever asks it to support.

Leveling is a lever, not only a measurement. `production.leveling.policy` selects `as_released`
(no smoothing), `fixed_repeating_pattern` (a declared repeating sequence, the classic heijunka
pattern), or `smoothed_by_family` (the scheduler minimizes `mix_deviation` subject to due dates).
Switching policy is a what-if: the LSS engine judges whether the resulting change in throughput,
WIP and total setup time is real, and the ergonomics layer reports whether flattening the mix moved
operator load. `E2E-PROD-009` runs `as_released` against `smoothed_by_family` on paired seeds and
publishes all three deltas.

The invariant `takt_accounting_closure` (7.2) asserts that available time plus planned breaks plus
planned downtime equals window length exactly in sim-ticks, so a takt number can never be improved
by losing time out of the denominator.

### 5.23 Schedule-versus-actual divergence as a finding class (6a9)

The source states that divergence between scheduled and actual output is itself a finding. It is
computed per bucket, per stage, and per machine, and it is emitted as
`production.schedule.divergence`.

```
adherence_pct   = 100 * (1 - sum over buckets of abs(actual_units - planned_units)
                             / sum over buckets of planned_units)
```

Absolute deviation is used rather than signed deviation because overproduction and underproduction
are both misses against a level plan, and a signed measure lets them cancel into a comfortable zero.
The bucket width is `scheduling.adherence_bucket_s`, and both a shift-level and an hour-level series
are produced, because a shift that hits its number by running double in the last two hours is a
different operation from one that hit it evenly.

`attribute_causes` assigns each bucket's deviation to one cause class, ranked by the evidence
already in the log: `machine_down` (a breakdown overlapping the bucket), `material_starved` (an
upstream buffer empty), `blocked` (a downstream buffer full), `changeover_overrun` (a changeover
longer than its scheduled element sum), `quality_hold` (a quarantine intersecting the bucket),
`labor_short` (a station unstaffed against the roster), and `unexplained`. The last class is
deliberate and is reported rather than hidden: a divergence attribution model that always finds a
cause is not measuring anything. `scheduling.max_unexplained_share` sets the level at which the
unexplained share itself raises `divergence_attribution_weak`, which is a finding about the model,
not about the plant.

Divergence findings feed the NCR engine at `major` severity only when adherence falls below
`scheduling.adherence_floor_pct` for `scheduling.adherence_consecutive_buckets` consecutive buckets.
A single bad bucket is information; a run of them is a nonconformance.

`schedule_divergence_partition` (7.2) asserts every bucket's deviation is assigned to exactly one
cause class and that the class totals sum to the total absolute deviation.

### 5.24 Production-twin recalibration from telemetry (6a9)

The source's component 6 requires the twin to recalibrate continuously from telemetry, with
divergence between predicted and observed flow becoming a finding. 5.23 owns the divergence finding.
This subsection owns the recalibration, which is the part that makes it a twin rather than a
simulation.

`recalibrate_from_telemetry(window)` produces a `RecalibrationPlan`, and the plan is a proposal, not
an edit. Recalibration touches four parameter families and no others:

| Parameter                       | Estimator over the window                                                        | Guard                                                               |
|---------------------------------|----------------------------------------------------------------------------------|---------------------------------------------------------------------|
| Machine cycle-time distribution | Refit the configured family to observed realized cycle times in steady `execute` | Family is never changed by recalibration, only its parameters       |
| Changeover element durations    | Refit per `(machine, from_family, to_family)` element                            | Elements absent from the window keep their prior values             |
| Stage base first-pass yield     | Beta posterior over observed first-pass outcomes                                 | Never moves more than `recalibrate.max_step_frac` in one plan       |
| Phase CPP trajectory parameters | Least squares on the phase-local ramp, soak and decay parameters                 | Only for phases with at least `recalibrate.min_batches` completions |

Four properties keep this honest.

1. **It never runs inside the tape.** Recalibration reads a closed window of recorded events and
   writes a proposed config diff. It never mutates live simulation state, so a run's tape does not
   depend on when recalibration happened to fire (D-02, D-04).
2. **Every proposal is a config diff, reviewed like any other.** `RecalibrationResult` carries the
   old value, the new value, the estimator, the sample size, and a confidence interval per
   parameter. Applying it is an E5 autonomy decision recorded in the audit trail, and at tier L1 or
   L2 a human approves it. The agent may propose; it does not silently retune the twin.
3. **It is gated on a statistical test, not on a difference.** A parameter moves only when the LSS
   engine rejects equality between the prior and the window estimate at `recalibrate.alpha`, and
   only when the estimated shift exceeds `recalibrate.min_effect`. Chasing noise is the failure mode
   this design exists to prevent.
4. **Recalibration is scored against ground truth.** The twin generated the telemetry, so the true
   parameter is known. `VAL-GATE-PROD-6` measures the bias and the spread of each recalibrated
   parameter against the true value and publishes both, which is a check no field deployment can run
   on itself.

A parameter that recalibration moves repeatedly in the same direction is itself a finding
(`twin_parameter_drift`), because a twin that needs the same correction every week is modeling
something it has not represented.

### 5.25 The make-versus-buffer what-if (6a9)

The source names this as the question entire engagements are sold to answer: is the cheapest capacity
a third shift at the factory, a faster changeover program, or more DC safety stock? It is the last
capability in 3i because it composes the factory, the DC, the planning layer and the financial twin.

`compare_scenarios` runs four arms from one baseline config, on paired seeds with common random
numbers, over the same horizon and the same demand realization:

| Arm            | Config change                                                                     | Cost side                                                    |
|----------------|-----------------------------------------------------------------------------------|--------------------------------------------------------------|
| `baseline`     | none                                                                              | none                                                         |
| `third_shift`  | `production.calendar.shifts` gains a third shift on the bottleneck stage          | Labor cost from 6a14, including shift premium and ramp curve |
| `smed_program` | the 5.4 SMED program is applied to the bottleneck machine                         | `smed.capex` plus the engineering effort declared with it    |
| `more_buffer`  | DC safety stock for the affected SKU class is raised by `whatif.buffer_step_frac` | Carrying cost and space from the planning and finance layers |

Each arm reports the same measured vector: units shipped, fill rate, on-time ship rate, factory OEE
at the bottleneck, average WIP, total setup seconds, COPQ by bucket, labor hours, inventory
carrying cost, and total cost to serve. The comparison the agent presents is throughput gained per
dollar of assumed cost, ranked, with the LSS engine's verdict on whether each arm's throughput delta
is distinguishable from seed noise at the configured replication count.

Three rules keep the answer defensible.

- **The ranking always carries its assumption set.** Every cost input is config, and the output
  table prints the cost assumptions beside the result. A ranking that hides its cost assumptions is
  an opinion.
- **An arm whose delta is not statistically distinguishable is reported as such, not ranked.** The
  output says "not distinguishable from baseline at this replication count" and states the count.
- **The bottleneck is identified by the twin, not by the author.** The arms attach to whichever
  stage the bottleneck detector names in the baseline run, and if a change moves the bottleneck the
  report says where it moved to. Moving a constraint one station downstream is the outcome that makes
  a capacity investment disappoint, so it is named rather than left to be discovered later.

`E2E-PROD-010` runs all four arms on a fixed seed and produces the ranked investment table as a
golden file, which is the consulting deliverable generated by software that A1 asks for.

---

## 6. Configuration

All configuration validates against published JSON Schemas in `/schemas` at load time, with
line-numbered, suggestion-bearing errors and a `just validate` command plus `--dry-run` (C5).
Unknown keys are rejected rather than ignored, because a silently ignored misspelled key is the
config bug that costs a day.

### 6.1 `facility.yaml`, `production:` block

| Key                                             | Type                                           | Validation                                                                                                                         |
|-------------------------------------------------|------------------------------------------------|------------------------------------------------------------------------------------------------------------------------------------|
| `production.plant_id`                           | str                                            | matches `^[a-z0-9_]{2,32}$`, unique across sites                                                                                   |
| `production.stage_graph`                        | list of `{id, kind: batch\                     | discrete, downstream: [id]}`                                                                                                       |
| `production.process_cells[].units[]`            | list                                           | each unit declares `capabilities: [str]` matched against recipe phase requirements                                                 |
| `production.work_centers[].machines[]`          | list                                           | see machine keys below                                                                                                             |
| `production.machines[].ideal_cycle_time_s`      | float                                          | `> 0`; a value below the observed p1 cycle time at runtime raises `oee_ideal_cycle_time_implausible`                               |
| `production.machines[].setup_matrix_ref`        | str                                            | must resolve in `setup_matrices`                                                                                                   |
| `production.machines[].startup_scrap_units`     | int                                            | `>= 0`                                                                                                                             |
| `production.machines[].failure_model_ref`       | str                                            | must resolve in the shared reliability catalog                                                                                     |
| `production.calendar.shifts`                    | list                                           | must tile the week without overlap; gaps become planned downtime                                                                   |
| `production.uom_conversions`                    | map                                            | every batch-to-discrete handoff needs a factor; round-trip error must be zero                                                      |
| `oee.count_external_stops_as_availability_loss` | bool                                           | default false; both variants are always emitted regardless                                                                         |
| `oee.minor_stop_threshold_s`                    | float                                          | default 300; `> 0`                                                                                                                 |
| `oee.startup_window_units`                      | int                                            | default 10; `>= 0`                                                                                                                 |
| `oee.loss_mapping`                              | map state+reason to loss bucket                | must cover every reachable state; an uncovered state is a load error, not a runtime surprise                                       |
| `flow_control.mode`                             | enum                                           | `push \                                                                                                                            |
| `flow_control.kanban_loops[]`                   | list                                           | `cards` or the formula inputs `{demand_rate, lead_time_s, safety_factor, container_size}`, not both                                |
| `flow_control.conwip_cap`                       | int                                            | required when mode is `conwip`; `> 0`                                                                                              |
| `scheduling.solver`                             | enum                                           | `dispatch_atcs \                                                                                                                   |
| `scheduling.atcs.k1`, `.k2`                     | float                                          | `> 0`; defaults 2.0 and 1.5                                                                                                        |
| `scheduling.budget`                             | `{iterations}` or `{trials}`                   | required for non-baseline solvers; recorded on every published schedule; a wall-clock budget key is rejected at load (D-04)        |
| `setup_matrices.<ref>`                          | matrix of `from_family x to_family -> seconds` | square, non-negative, diagonal must be zero or the configured minor-setup value                                                    |
| `smed.program_id`                               | str                                            | optional; when present all named elements must exist on the named machines                                                         |
| `stages.<id>.ctq[]`                             | list                                           | `{characteristic_id, subgroup_size, sampling_period_s, lsl, usl, target, chart_preference}`; `lsl < target < usl` when all present |
| `stages.<id>.base_fpy`                          | float                                          | in `(0, 1]`                                                                                                                        |
| `takt.ratio_ceiling`                            | float                                          | `> 1`; default 1.05                                                                                                                |
| `takt.ratio_floor`                              | float                                          | `> 0` and below `takt.ratio_ceiling`; default 0.70                                                                                 |
| `takt.consecutive_windows`                      | int                                            | `>= 1`; default 3                                                                                                                  |
| `leveling.policy`                               | enum                                           | `as_released \                                                                                                                     |
| `leveling.weights`                              | `{w_mix, w_vol, w_chg}`                        | non-negative, sum to 1                                                                                                             |
| `leveling.share_target`                         | map family to share                            | shares in `[0,1]` summing to 1; required when policy is not `as_released`                                                          |
| `scheduling.adherence_bucket_s`                 | float                                          | `> 0`; must divide the shift length exactly                                                                                        |
| `scheduling.adherence_floor_pct`                | float                                          | `(0, 100]`                                                                                                                         |
| `scheduling.adherence_consecutive_buckets`      | int                                            | `>= 1`                                                                                                                             |
| `scheduling.max_unexplained_share`              | float                                          | `[0, 1]`; above this the model itself raises `divergence_attribution_weak`                                                         |
| `recalibrate.alpha`                             | float                                          | `(0, 0.5)`                                                                                                                         |
| `recalibrate.min_effect`                        | map parameter family to a minimum shift        | every recalibrated family needs one; no default of convenience                                                                     |
| `recalibrate.max_step_frac`                     | float                                          | `(0, 1]`; the largest single-plan move for a bounded parameter                                                                     |
| `recalibrate.min_batches`                       | int                                            | `>= 1`; phases below this are not recalibrated                                                                                     |
| `recalibrate.autonomy_tier_required`            | int                                            | E5 tier needed to apply a plan; default 2, so a human approves                                                                     |
| `whatif.buffer_step_frac`                       | float                                          | `> 0`; the safety-stock increase the `more_buffer` arm applies                                                                     |

### 6.2 `recipes/*.yaml` and `golden_batches/*.yaml`

| Key                                       | Type                                     | Validation                                                                                                         |
|-------------------------------------------|------------------------------------------|--------------------------------------------------------------------------------------------------------------------|
| `recipe_id`, `revision`                   | str                                      | revision must exist in PLM for this recipe                                                                         |
| `procedure`                               | nested                                   | exactly four levels: procedure, unit_procedure, operation, phase                                                   |
| `procedure...phase.required_capabilities` | list[str]                                | at least one configured unit must have all of them                                                                 |
| `formula.process_parameters.<cpp>`        | `{setpoint, tolerance, uom, model: ramp\ | soak\                                                                                                              |
| `expected_yield_pct`                      | float                                    | `(0, 100]`                                                                                                         |
| `expected_yield_loss_pct`                 | float                                    | `[0, 100)`; sum with `expected_yield_pct` at most 100                                                              |
| `material_balance_tolerance_pct`          | float                                    | default 0.5; `[0, 5]`, and a value above 2 emits a config warning because a loose material balance hides real loss |
| `golden.grid`                             | int                                      | default 64; power of two between 16 and 512                                                                        |
| `golden.min_qualifying_batches`           | int                                      | default 20; `>= 5`, and below 20 emits a warning recorded on every score                                           |
| `golden.envelope_quantiles`               | `[float, float]`                         | strictly increasing, both in `(0,1)`                                                                               |
| `golden.envelope_floor_frac`              | float                                    | default 0.05; `[0, 0.5]`                                                                                           |
| `golden.alignment`                        | enum                                     | `progress_resample \                                                                                               |
| `golden.verdict_bands`                    | list[float]                              | strictly decreasing, all in `[0,100]`                                                                              |
| `golden.weights`                          | `{w_rmse, w_oob}`                        | both `>= 0`, sum to 1                                                                                              |

### 6.3 `quality.yaml`

| Key                                            | Type                    | Validation                                                                                                                                                                                                                  |
|------------------------------------------------|-------------------------|-----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| `ncr_rules[]`                                  | list                    | each rule's `finding_class` must exist in the findings taxonomy                                                                                                                                                             |
| `ncr_rules[].dedupe.window_s`                  | float                   | `> 0`                                                                                                                                                                                                                       |
| `ncr.escalate_after_occurrences`               | int                     | `>= 2`                                                                                                                                                                                                                      |
| `capa.default_alpha`                           | float                   | `(0, 0.5)`; default 0.05                                                                                                                                                                                                    |
| `capa.default_power`                           | float                   | `(0.5, 1)`; default 0.80                                                                                                                                                                                                    |
| `capa.default_washout_s`                       | float                   | `>= 0`                                                                                                                                                                                                                      |
| `capa.sustain_horizon_s`                       | float                   | `> 0`; default 90 days in sim-seconds                                                                                                                                                                                       |
| `capa.require_frozen_plan_before_implement`    | bool                    | default true; setting false emits a governance finding on every CAPA, because it disables the honesty mechanism                                                                                                             |
| `sampling.switching_ruleset`                   | enum                    | `mil_std_105e \                                                                                                                                                                                                             |
| `sampling.default_inspection_level`            | enum                    | `S-1..S-4, I, II, III`; default II                                                                                                                                                                                          |
| `sampling.default_aql`                         | float                   | must be one of the preferred AQL values in the encoded table                                                                                                                                                                |
| `sampling.oc_model`                            | enum                    | `auto \                                                                                                                                                                                                                     |
| `sampling.reduced_requires_authority_approval` | bool                    | default true                                                                                                                                                                                                                |
| `copq.rates`                                   | map cost driver to rate | every driver referenced by a classification rule must have a rate                                                                                                                                                           |
| `copq.classification[]`                        | list                    | every rule maps to exactly one of the four classes; an event matching two rules is a load error                                                                                                                             |
| `checklists.enabled[]`                         | list[str]               | each must resolve to a file under `checklists/`                                                                                                                                                                             |
| `lpa.layers[]`                                 | list                    | layer numbers unique and contiguous from 1                                                                                                                                                                                  |
| `lpa.coverage.max_interval_days_per_station`   | int                     | `> 0`                                                                                                                                                                                                                       |
| `recall.default_scope`                         | enum                    | `material \                                                                                                                                                                                                                 |
| `recall.elapsed_budget_ms`                     | int                     | default 2000; an operator-facing budget for the dry-run banner only. VAL-GATE-QMS-7 gates on the recorded baseline for the runner class, not on this key, and the drill's elapsed time never enters an event payload (D-02) |
| `coa.required_for`                             | selector                | items or customers                                                                                                                                                                                                          |
| `coa.release_authority`                        | list[str]               | roles; `forbid_actor_kinds` defaults to `[agent]`                                                                                                                                                                           |

### 6.4 `ledger.yaml`

| Key                               | Type                                              | Validation                                                                                                          |
|-----------------------------------|---------------------------------------------------|---------------------------------------------------------------------------------------------------------------------|
| `ledger.block_max_entries`        | int                                               | `> 0`; default 1000                                                                                                 |
| `ledger.block_max_interval_s`     | float                                             | `> 0`; default 3600 sim-seconds                                                                                     |
| `ledger.hash`                     | enum                                              | `sha256` only; the key exists so the choice is explicit and auditable                                               |
| `ledger.canonicalisation`         | enum                                              | `rfc8785` only, same reason                                                                                         |
| `ledger.signature_algorithm`      | enum                                              | `ed25519` only; ECDSA is rejected at load with the message that a randomized signature scheme breaks C1 determinism |
| `ledger.key_derivation`           | `{scheme: hkdf_sha256, salt: str}`                | keys derived from the run seed; a config that points at a key file path is rejected so keys can never be committed  |
| `ledger.parties[]`                | list                                              | `{party_id, roles: [str]}`                                                                                          |
| `signature_policy.<event_schema>` | `{required_roles, threshold, forbid_actor_kinds}` | `threshold <= len(required_roles)`                                                                                  |
| `ledger.root_publication.to`      | list[party_id]                                    | may be empty; when empty, the withholding limitation is printed in the run summary                                  |
| `epcis.namespace_uri`             | str                                               | valid URI; used for EPC URI construction                                                                            |
| `epcis.company_prefix`            | str                                               | digits; used for SGTIN/SSCC construction, and a warning states these are synthetic prefixes not licensed from GS1   |

### 6.5 `plm.yaml`

| Key                                     | Type  | Validation                                                           |
|-----------------------------------------|-------|----------------------------------------------------------------------|
| `plm.revision_scheme`                   | enum  | `alpha \                                                             |
| `plm.default_interchangeability`        | enum  | required, no default of convenience                                  |
| `plm.eco.max_use_up_days`               | int   | `>= 0`                                                               |
| `plm.eco.require_supplier_ack_on_amend` | bool  | default true                                                         |
| `plm.cost_rollup.rounding`              | enum  | `bankers \                                                           |
| `plm.cost_rollup.currency_precision`    | int   | `[0, 6]`; default 2                                                  |
| `plm.cost_rollup.overhead_rate`         | float | `>= 0`                                                               |
| `plm.effectivity.horizon_days`          | int   | `> 0`; the window over which `resolve_revision` totality is asserted |

### 6.6 `bizsys.yaml`

| Key                                           | Type                                                    | Validation                                                                       |
|-----------------------------------------------|---------------------------------------------------------|----------------------------------------------------------------------------------|
| `erp.asn_lead_time_s`                         | distribution                                            | ASN issued this far before arrival; must be non-negative                         |
| `erp.asn_accuracy`                            | `{qty_error_rate, lot_error_rate, revision_error_rate}` | each in `[0,1]`; these inject the discrepancies the reconciler must classify     |
| `erp.reconciliation.partial_arrival_window_s` | float                                                   | `> 0`                                                                            |
| `erp.reconciliation.variance_thresholds`      | `{minor_pct, major_pct}`                                | `0 < minor_pct < major_pct`                                                      |
| `erp.inventory.book_owner`                    | enum                                                    | `erp_stub`; the physical owner is the WMS (see Open Question 9.11)               |
| `cmms.priority_weights`                       | `{w_rpn, w_deferral, w_safety, w_criticality}`          | non-negative, sum to 1                                                           |
| `cmms.deferral.replications`                  | int                                                     | `>= 10`; default 30                                                              |
| `cmms.deferral.horizon_days`                  | int                                                     | `> 0`; default 30                                                                |
| `cmms.deferral.use_common_random_numbers`     | bool                                                    | default true; setting false emits a warning that confidence intervals will widen |
| `cmms.repeat_failure_window_s`                | float                                                   | `> 0`                                                                            |
| `cmms.production_window_policy`               | enum                                                    | `any \                                                                           |

### 6.7 `sop_policy.yaml`

| Key                                      | Type  | Validation                                                                                                     |
|------------------------------------------|-------|----------------------------------------------------------------------------------------------------------------|
| `sop.corpus_dir`                         | path  | must exist; every file must parse and carry required front matter                                              |
| `sop.retrieval.mode`                     | enum  | `lexical_only \                                                                                                |
| `sop.retrieval.min_score`                | float | `(0, 1]`; the abstention threshold                                                                             |
| `sop.retrieval.rrf_k`                    | int   | `> 0`; default 60                                                                                              |
| `sop.retrieval.require_structural_match` | bool  | default true; setting false is allowed for ablation studies and is recorded in the eval report                 |
| `sop.adherence.coefficients`             | map   | all six named; every value required, none defaulted, so nobody accidentally ships an unexamined behavior model |
| `sop.clarity.weights`                    | map   | non-negative, sum to 1                                                                                         |
| `sop.generation.model_ref`               | str   | resolves in the model registry (E43) to a pinned artifact digest; a floating tag is rejected at load (D-04)    |
| `sop.generation.require_grounding`       | bool  | default true; false is rejected in CI configurations                                                           |
| `sop.retrieval.model_digest`             | str   | required when mode is `hybrid`; the pinned dense-encoder digest recorded in the run manifest's hashed core     |

---

## 7. Testing

C4 names three tiers. This section runs four, because the reference gates of 7.3 are neither
property tests nor end-to-end scenarios and hiding them inside either tier would hide their cost.
Each tier has a stated budget enforced in CI:

| Tier              | Budget                      | Scope                                         |
|-------------------|-----------------------------|-----------------------------------------------|
| unit              | 90 s for all seven packages | pure functions, state machines, table lookups |
| property          | 240 s                       | Hypothesis invariants, 7.2                    |
| gates             | 300 s                       | 7.3                                           |
| seeded end-to-end | 900 s                       | 7.4, golden-file comparisons                  |

The budgets are arithmetic, not aspiration, so the arithmetic is itself asserted (D-13).
`test_tier_budget_arithmetic` sums each tier's declared per-test cost from the recorded timing file
and fails when the sum exceeds the tier budget, so a scenario that grows past its budget fails as a
defect with a named cause rather than as a job timeout with none. Two consequences follow and are
recorded here rather than discovered later. The 10,000-replication gates in 7.3 do not fit a 300 s
budget as full simulation runs, so each of them runs against a precomputed measurement stream rather
than a full plant run, and the gate says so. The recall-drill timing gate needs a million-edge graph,
which is built once per job by a fixture shared across the gates that need it.

Every test in 7.2, 7.3 and 7.4 states the observation that would fail it (D-12). A test whose failure
condition cannot be written down is deleted rather than kept.

### 7.1 Unit tests, by package

`twinflow-production`: PackML transition legality (every illegal transition raises), loss-bucket
mapping coverage over all reachable states, OEE arithmetic on hand-constructed timelines, golden
profile construction from a fixed batch set, resample-on-progress correctness against a hand-computed
example, setup matrix lookup, ATCS priority-index arithmetic against a worked instance, kanban card
formula, RTY arithmetic.

`twinflow-genealogy`: DAG enforcement, forward and backward closure on hand-built graphs including
diamond and re-entrant shapes, EPC URI construction for SGTIN, LGTIN, SSCC and GLN including check
digits, Digital Link URI construction, DPP audience filtering.

`twinflow-ledger`: canonicalisation of pathological JSON (unicode escapes, number formats, key
ordering, nested empties), Merkle tree hash for sizes 0 through 17 (covering the non-power-of-two
split), inclusion and consistency proof generation and verification, signature policy evaluation
including the threshold and forbidden-actor cases.

`twinflow-quality`: NCR dedupe key construction and window expiry, CAPA transition legality, sampling
plan lookup across the full encoded table, switching state machine transitions one rule at a time,
COPQ classifier exactly-one-class enforcement, checklist predicate evaluation, LPA schedule
generation.

`twinflow-plm`: BOM explosion and where-used on a multi-level BOM, cycle detection, effectivity
resolution at boundaries (exactly at `from_time`, one tick before, one tick after), disposition
decision table over the full interchangeability cross product, standard cost rollup rounding.

`twinflow-sop`: markdown clause parsing including nested headings and character spans, front-matter
validation, `effective_at` resolution across revision boundaries, BM25 ranking on a fixture corpus,
structural eligibility filtering, fusion tie-breaking on `(-score, clause_id)`, clarity score
arithmetic.

`twinflow-bizsys`: ASN hierarchy construction and traversal, the reconciliation classifier over every
cell of the 5.16 matrix including the residual class, confidence computation from a degraded portal
state, work-order priority arithmetic against a worked instance, deferral curve shape on a supplied
hazard function.

### 7.2 Property-based invariants (Hypothesis)

Each is a named test. Generators are seeded from the run seed so failures reproduce. An invariant's
statement is also its failure condition (D-12): the test fails on any generated input for which the
stated sentence is false, and Hypothesis prints the shrunk counterexample.

| Invariant name                     | Statement                                                                                                                                                                                                                                 |
|------------------------------------|-------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| `material_conservation`            | For every transformation, inputs times conversion times expected yield equals good plus rework plus scrap plus declared loss, within `material_balance_tolerance_pct`, and declared loss never exceeds `expected_yield_loss_pct` of input |
| `genealogy_closure`                | The graph is acyclic; every non-raw node has at least one inbound lineage edge; for any node n, `n in forward_closure(backward_closure(n))`; forward closure is idempotent                                                                |
| `revision_in_genealogy`            | Every genealogy node carries a non-null as-built `item_revision`, for arbitrary generated event streams                                                                                                                                   |
| `loss_accounting_closure`          | Under both external-stop accountings, the six time buckets plus valuable operating time equal planned production time exactly in integer sim-ticks with no tolerance, and the two unit buckets plus good count equal total count exactly  |
| `oee_bounds`                       | Availability, performance and quality are each in `[0, inf)`; OEE equals their product to within float epsilon; quality is in `[0,1]`; performance above 1 always co-occurs with an `oee_ideal_cycle_time_implausible` finding            |
| `packml_total_partition`           | Machine state history partitions the run's sim-time with no gaps and no overlaps                                                                                                                                                          |
| `kanban_wip_bound`                 | For any generated demand sequence, WIP in a kanban loop never exceeds `cards * container_size`                                                                                                                                            |
| `littles_law_holds`                | At steady state after the warm-up window, WIP equals throughput times cycle time within the tolerance VAL-GATE-PROD-3 measures and records, never a tolerance chosen in advance                                                           |
| `schedule_feasibility`             | For any generated instance and any solver, no machine runs two jobs simultaneously, every setup time is charged, and no job starts before its release date                                                                                |
| `schedule_evaluator_determinism`   | `evaluate_schedule` is a pure function: same input, same output, across process restarts                                                                                                                                                  |
| `ncr_dedupe_idempotence`           | Replaying the same finding stream produces the same NCR set with the same occurrence counts                                                                                                                                               |
| `capa_state_monotone`              | CAPA transitions follow the declared graph; `reopen_count` is non-decreasing; a CAPA cannot reach `verifying` without a frozen plan and enough post-window observations                                                                   |
| `sampling_switching_reachability`  | For any generated lot-result sequence, the switching state machine reaches only declared states, and `discontinued` is reachable only by its declared condition                                                                           |
| `sampling_plan_monotone`           | For a fixed AQL and level, sample size is non-decreasing in lot size; tightened accept numbers are never above normal accept numbers                                                                                                      |
| `copq_exhaustive_partition`        | Every cost-bearing quality event produces exactly one posting; bucket totals sum to total quality cost; no source event id appears twice                                                                                                  |
| `audit_trail_append_only`          | Sequence numbers strictly increase with no gaps; no API path mutates a persisted entry; `verify_chain` holds after arbitrary interleavings of appends                                                                                     |
| `ledger_tamper_detected`           | For any single-byte mutation of any persisted entry or header, `verify_chain` fails and reports the first bad sequence                                                                                                                    |
| `ledger_proof_stability`           | An inclusion proof issued at tree size m still verifies against the root at any size n > m via the consistency proof; appending never invalidates a previously issued proof                                                               |
| `coa_derivable_from_log`           | Regenerating a CoA from the replayed event log yields a byte-identical canonical document                                                                                                                                                 |
| `effectivity_totality`             | `resolve_revision` returns exactly one revision for every item and every time in the configured horizon, and is monotone in release order                                                                                                 |
| `bom_acyclic`                      | BOM explosion terminates for every generated BOM, and a generated cycle raises at load                                                                                                                                                    |
| `lpa_coverage`                     | Every station is audited by at least one layer within `max_interval_days_per_station` for any generated roster                                                                                                                            |
| `sop_citation_or_abstain`          | Every SOP-violation finding either carries an eligible citation or has been downgraded to `undocumented_deviation`; no finding cites a clause whose `applies_to` does not match                                                           |
| `sop_time_travel_citation`         | For a violation at time t, the cited revision is the one effective at t, for arbitrary revision timelines                                                                                                                                 |
| `sop_adherence_monotone`           | Adherence probability is non-decreasing in clarity and training recency, and non-increasing in fatigue and step count                                                                                                                     |
| `reconciliation_total`             | Every ASN line receives exactly one of the ten variance classes of 5.16 for arbitrary generated count triples, including the residual class; no input reaches the classifier without a class                                              |
| `deferral_curve_monotone`          | When the hazard rate is non-decreasing, `total_expected_cost(d)` has no interior local minimum below the recommended window, and `P_fail(<= d)` is non-decreasing in d                                                                    |
| `crn_paired_runs_identical_prefix` | Two paired what-if runs with the same seed produce byte-identical event logs up to the injection point on one pinned platform, and value-equivalent logs across platforms under the D-05 tolerance                                        |
| `takt_accounting_closure`          | Available time plus planned breaks plus planned downtime equals window length exactly in sim-ticks, so takt cannot be improved by losing time out of the denominator                                                                      |
| `schedule_divergence_partition`    | Every adherence bucket's absolute deviation is assigned to exactly one cause class, and the class totals sum to the total absolute deviation                                                                                              |
| `levelling_index_bounded`          | `levelling_index` lies in `[0, 1]` for any generated release sequence, and is non-increasing in each of its three components                                                                                                              |
| `recalibration_is_a_proposal`      | A recalibration pass over a recorded window mutates no simulation state and emits no event into the tape; the run hash before and after the pass is identical                                                                             |

### 7.3 Validation gates

Gates come in two kinds, and conflating them is the defect D-11 exists to prevent.

A **reference gate** checks an implementation against a source outside this repository. It satisfies
all five D-11 conditions: it names the source with edition and locator, its tolerance is never
tighter than the precision of the value it checks, a gate over a stochastic quantity states a
measured noise floor and sits above it, it states what result would falsify it, and a statistic with
no valid external source is an open question rather than a passing gate.

An **invariant gate** checks an algebraic or logical identity inside the system, such as a partition
that must close or a classifier that must be total. It carries no external source because there is
nothing external to check against, and it never appears in the README's
"validated against published references" table. It still states its falsifier. Calling an invariant
gate a validation against a published reference is what makes a repository's evidence table
untrustworthy, so the two are labeled and reported separately.

This repository is never cited as its own external reference. Where a gate rests on ground truth,
that ground truth is the twin's own injected value, the gate says so, and the gate is an invariant
gate.

| Gate              | Kind      | Source, with edition and locator                                                                                                                                                                                                                                                                   | Assertion, tolerance and noise floor                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                | Falsifier                                                                                                            |
|-------------------|-----------|----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|-------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|----------------------------------------------------------------------------------------------------------------------|
| VAL-GATE-PROD-1a  | Invariant | None. Closed-form construction over a synthesised timeline                                                                                                                                                                                                                                         | Loss buckets and unit buckets close exactly in integer sim-ticks and integer units, tolerance 0. The four ratios equal the closed form to within 8 units in the last place of a double, which bounds the rounding of the four arithmetic operations that produce them                                                                                                                                                                                                                                                                                                               | Any bucket sum that misses closure by one tick, or a ratio outside 8 ulp                                             |
| VAL-GATE-PROD-1b  | Reference | ISO 22400-2:2014 including Amendment 1:2017, KPI definitions; ISA-TR88.00.02, state model. Both cited, neither reproduced. Designation read from the ANSI webstore catalog listing on 2026-08-10                                                                                                   | Every KPI this section computes carries a `standard_ref` annotation naming the clause it implements, and a docs test asserts the annotation exists and resolves. The standard text is paid, so the gate checks annotation coverage, not numeric agreement. No free certified dataset for OEE exists; Open Question 9.5                                                                                                                                                                                                                                                              | A KPI with no `standard_ref`, or a `standard_ref` naming a clause absent from the cited standard's clause list       |
| VAL-GATE-PROD-2   | Reference | Taillard, "Benchmarks for basic scheduling problems", European Journal of Operational Research 64(2):278-285, 1993, DOI 10.1016/0377-2217(93)90182-M. Setup-time extension per Ruiz, Maroto and Alcaraz, EJOR 165(1):34-54, 2005, DOI 10.1016/j.ejor.2004.01.022                                   | `evaluate_schedule` never returns a makespan below the published lower bound for the instance, tolerance 0 since both are integers. Solver quality is reported as the measured distribution of the ratio to the best value the ladder finds, published rather than asserted against a bound nobody published. Open Question 9.15 records that the bound table must be re-obtained from a live copy                                                                                                                                                                                  | A makespan below an instance's published lower bound, which can only mean the evaluator is wrong                     |
| VAL-GATE-PROD-3   | Reference | Little, "A Proof for the Queuing Formula: L = lambda W", Operations Research 9(3):383-387, 1961, DOI 10.1287/opre.9.3.383                                                                                                                                                                          | Over at least 10,000 completions after warm-up, `WIP / (throughput * cycle_time)` equals 1. The tolerance is 3 times the measured run-to-run standard deviation of that ratio across 30 replications, computed in the same job and printed with the result, never a number fixed in advance                                                                                                                                                                                                                                                                                         | A ratio outside the measured band, or a measured standard deviation that grows between releases without a cause      |
| VAL-GATE-PROD-4   | Reference | NIST/SEMATECH e-Handbook of Statistical Methods, section 6.3.2, which states that for a 3-sigma Shewhart chart on normal data p is 0.0027 and the ARL is approximately 371 (retrieved 2026-08-10, HTTP 200) <!-- docs-lint-ok STE-TERM-WORD verbatim quotation of the NIST/SEMATECH e-Handbook --> | In control, the empirical ARL over 10,000 seeded runs matches the handbook value. The published value carries three significant figures, so agreement is checked at that precision. Run length is geometric, so the standard error of the mean over 10,000 runs is about 1.0 percent of the ARL; the tolerance is 5 percent, five standard errors above that floor. For shifts of 1, 2 and 3 sigma the same 5 percent tolerance applies against `ARL1 = 1 / (1 - Phi(3 - delta*sqrt(n)) + Phi(-3 - delta*sqrt(n)))`, the geometric mean anchored on the same in-control probability | An empirical ARL outside the 5 percent band, which is a five-sigma event under the null                              |
| VAL-GATE-PROD-5   | Invariant | None. Golden-batch construction ground truth                                                                                                                                                                                                                                                       | Batches synthesised from the golden profile plus a known deviation land in the correct verdict band for every deviation at or beyond 1.5 times the band boundary. Scoring is deterministic, so the rate is 1.0 or the scorer is wrong. The 1.5 margin is a chosen separation, stated as chosen; the confusion matrix inside the ambiguous zone is published, not asserted                                                                                                                                                                                                           | A single misbanded batch outside the ambiguous zone                                                                  |
| VAL-GATE-PROD-6   | Invariant | None. Recalibration against the twin's own generating parameters                                                                                                                                                                                                                                   | For each recalibrated parameter family, the bias and spread of the recalibrated estimate against the true generating value are measured over 30 seeded windows and published. The gate asserts only that the estimate's confidence interval covers the true value at the configured coverage rate                                                                                                                                                                                                                                                                                   | A coverage rate below the configured level, which means the estimator's intervals are wrong                          |
| VAL-GATE-QMS-1    | Reference | NIST/SEMATECH e-Handbook of Statistical Methods, section 6.2.2 for the AOQ, AOQL and ATI definitions, and section 6.2.3.2 for the worked `Pa` table of the (n=52, c=3) plan (retrieved 2026-08-10, HTTP 200)                                                                                       | Computed `Pa` matches all twelve published values for p from 0.01 to 0.12. Those values are printed to three decimal places, so agreement is checked to three decimals, an absolute tolerance of 5e-4, which is the half-unit in the last published digit. `AOQ` and `ATI` are then computed from the handbook's own formulas and checked at the same precision                                                                                                                                                                                                                     | Any `Pa` whose value rounded to three decimals differs from the published value                                      |
| VAL-GATE-QMS-2    | Reference | MIL-STD-105E, sample-size code letters and the single, double and multiple sampling tables; public domain under 17 U.S.C. 105(a)                                                                                                                                                                   | Code-letter lookup and every accept and reject number match the encoded table exactly across every implemented lot-size band, AQL and inspection level. Tolerance 0, since every value is an integer. The measured `Pa(AQL)` distribution across all normal single plans is published beside the result rather than asserted against a band, because no source publishes such a band                                                                                                                                                                                                | One table cell that differs from the standard, or one lookup that returns a different code letter                    |
| VAL-GATE-QMS-3    | Reference | MIL-STD-105E paragraphs 4.7.1 to 4.7.4 and 4.8; the Z1.4 switching score under the alternate ruleset, attributed in `docs/sampling_provenance.md`                                                                                                                                                  | A scripted lot-outcome sequence drives the machine through normal, tightened, back to normal, reduced, back to normal, discontinued, and resumption into tightened, matching a golden file. Every transition records the paragraph that fired. Tolerance 0                                                                                                                                                                                                                                                                                                                          | A transition at the wrong lot index, a wrong paragraph recorded, or resumption into `normal` rather than `tightened` |
| VAL-GATE-QMS-4    | Invariant | None. Simulation-based power check of this section's own verification procedure                                                                                                                                                                                                                    | Under a true effect equal to the declared MDE, the rate of `effective` verdicts over 10,000 seeded CAPAs is within 3 percentage points of the declared power; the binomial standard error at power 0.80 and n=10,000 is 0.40 points, so the tolerance is 7.5 standard errors. Under a true null the rate is within 1 point of alpha; the standard error at alpha 0.05 is 0.22 points, so the tolerance is 4.6 standard errors                                                                                                                                                       | Either rate outside its band, which means the verification procedure is not the test it claims to be                 |
| VAL-GATE-QMS-5    | Invariant | None. COPQ partition closure                                                                                                                                                                                                                                                                       | The four bucket totals sum to total quality cost for a full seeded shift, exactly, in integer minor currency units. No source event id appears in two postings                                                                                                                                                                                                                                                                                                                                                                                                                      | A sum that misses by one unit, or a duplicated source event id                                                       |
| VAL-GATE-QMS-6    | Invariant | None. The twin injected the contamination, so the true closure is known                                                                                                                                                                                                                            | The returned blast radius equals the true forward closure over 100 seeded contamination scenarios spanning material, revision and equipment-contact scopes: precision 1.0 and recall 1.0. The traversal is deterministic, so anything below 1.0 is a defect, not sampling error                                                                                                                                                                                                                                                                                                     | One node present in the true closure and absent from the result, or the reverse                                      |
| VAL-GATE-QMS-7    | Invariant | None. A performance measurement, published in the A4 scaling evidence                                                                                                                                                                                                                              | Recall-drill p95 elapsed time at 1,000,000 genealogy edges on the GitHub-hosted `ubuntu-latest` standard runner for public repositories (4 vCPU, 16 GB RAM, x64), compared against the recorded baseline for that runner class. The threshold is the recorded baseline plus its measured run-to-run spread, not the round number in config. Elapsed time is read by the observability exporter and never enters the tape (D-02)                                                                                                                                                     | A p95 above the recorded baseline band on the same runner class, which is a performance regression                   |
| VAL-GATE-QMS-8    | Invariant | None. Tamper detection over the section's own persisted store                                                                                                                                                                                                                                      | For 10,000 Hypothesis-generated single-byte mutations of the persisted audit trail, the detection rate is 1.0 and the reported first bad sequence is the sequence containing the mutated byte. Detection is deterministic, so anything below 1.0 is a defect                                                                                                                                                                                                                                                                                                                        | One undetected mutation, or a first-bad-sequence that does not contain the mutated byte                              |
| VAL-GATE-LEDGER-1 | Reference | RFC 6962, June 2013, sections 2.1, 2.1.1, 2.1.2 and the worked seven-leaf example in 2.1.3; verification procedures from RFC 9162, December 2021, sections 2.1.3.2 and 2.1.4.2                                                                                                                     | For the seven-leaf tree of 2.1.3, the audit paths for d0, d3, d4 and d6 and the consistency proofs PROOF(3, D[7]), PROOF(4, D[7]) and PROOF(6, D[7]) equal the node lists the RFC enumerates. `MTH({})` equals SHA-256 of the empty string. Tolerance 0: these are byte comparisons                                                                                                                                                                                                                                                                                                 | Any audit path or consistency proof whose node list differs from the RFC's                                           |
| VAL-GATE-LEDGER-2 | Reference | RFC 8785, section 3.2.3 property-sort test data, section 3.2.4 canonical UTF-8 byte sequence, and Appendix B Table 1 number serialization samples                                                                                                                                                  | Sorted property order matches the seven-entry expected order; canonical output matches the published hexadecimal byte sequence; all twenty-two IEEE 754 samples serialize to the published strings. Tolerance 0 throughout                                                                                                                                                                                                                                                                                                                                                          | One byte of difference in any of the three                                                                           |
| VAL-GATE-LEDGER-3 | Reference | RFC 8032 section 7.1, Ed25519 test vectors                                                                                                                                                                                                                                                         | Signing each published secret key and message yields the published signature, and verification accepts it. Tolerance 0                                                                                                                                                                                                                                                                                                                                                                                                                                                              | One signature byte that differs, or one published vector that fails to check out                                     |
| VAL-GATE-LEDGER-4 | Reference | GS1 EPCIS Standard Release 2.0, ratified June 2022, section 10 JSON/JSON-LD binding and the GS1-published JSON schema; GS1's published example documents                                                                                                                                           | Every emitted document validates against the schema, and GS1's example documents round-trip through parse and re-serialize with semantic equality. Tolerance 0 on schema validity. Whether the artifacts can be vendored depends on their license; Open Question 9.3                                                                                                                                                                                                                                                                                                                | A document the schema rejects, or an example whose round trip changes any semantic field                             |
| VAL-GATE-PLM-1    | Invariant | None. Totality of `resolve_revision`                                                                                                                                                                                                                                                               | Over 10,000 generated effectivity timelines, `resolve_revision` returns exactly one revision for every item and every time in the horizon, and is monotone in release order                                                                                                                                                                                                                                                                                                                                                                                                         | One timeline and time for which the function raises, returns nothing, or returns two candidates                      |
| VAL-GATE-PLM-2    | Invariant | None. Hand-computed multi-level rollup in the test fixture                                                                                                                                                                                                                                         | A three-level BOM with known component costs and routing rates rolls up to the value derived by hand in the fixture, exactly, at the configured currency precision under the configured rounding mode                                                                                                                                                                                                                                                                                                                                                                               | Any difference at the configured precision                                                                           |
| VAL-GATE-PLM-3    | Invariant | None. The twin built the units, so the true revision of each is known                                                                                                                                                                                                                              | After an ECO, `RevisionScope` returns exactly the units built to the affected revisions: precision 1.0, recall 1.0                                                                                                                                                                                                                                                                                                                                                                                                                                                                  | One unit of an unaffected revision returned, or one affected unit omitted                                            |
| VAL-GATE-SOP-1    | Invariant | None. The sim injects a violation of a named clause, so the correct clause is known                                                                                                                                                                                                                | Over 2,000 injected violations spanning every SOP in the corpus, precision@1, recall@3 and wrong-clause rate are measured and published with a one-sided 99 percent Clopper-Pearson bound on each. The gate asserts no regression against the recorded baseline beyond that interval. No threshold is asserted, because no source publishes one; Open Question 9.16 holds the project's own acceptance level as an open decision                                                                                                                                                    | A point estimate whose lower bound falls below the recorded baseline's lower bound                                   |
| VAL-GATE-SOP-2    | Invariant | None. Time-travel citation over generated revision timelines                                                                                                                                                                                                                                       | A violation at time t cites the revision effective at t across 500 generated revision timelines, every time. Resolution is deterministic, so anything below 1.0 is a defect                                                                                                                                                                                                                                                                                                                                                                                                         | One citation resolving to a revision not effective at the violation time                                             |
| VAL-GATE-SOP-3    | Invariant | None. The E26(f) grounding checker run over this section's generated drafts                                                                                                                                                                                                                        | Every number in a generated SOP maps to a logged `query_result_id`, and a negative test that injects an ungrounded number is rejected. Both directions are asserted, so a checker that passes everything fails the negative case                                                                                                                                                                                                                                                                                                                                                    | One published draft containing an unmatched number, or a negative case the checker accepts                           |
| VAL-GATE-BIZ-1    | Invariant | None. The twin injected the discrepancy, so the true cause is known                                                                                                                                                                                                                                | Classification accuracy is 1.0 on the cells of the 5.16 matrix that are deterministic given the injected cause. For the ambiguous cells the confusion matrix is published rather than asserted, and the residual class is reported with its own rate                                                                                                                                                                                                                                                                                                                                | One deterministic cell misclassified                                                                                 |
| VAL-GATE-BIZ-2    | Invariant | None. Common random numbers against independent sampling                                                                                                                                                                                                                                           | Paired deferral-cost runs produce byte-identical logs up to the injection point on a pinned platform (D-05). At equal replication counts, the CRN confidence interval is narrower than the independent-sampling interval, and the measured ratio of the two widths is published. No multiple is asserted, because variance reduction is problem-dependent and no source publishes a factor for this problem                                                                                                                                                                         | A CRN interval no narrower than the independent interval, or a paired prefix that is not byte-identical              |

### 7.4 Seeded end-to-end scenarios with golden files

| Scenario         | Seed | Flow                                                                                                                                                                                                                                                                                                                                                           | Golden files                                                                             |
|------------------|------|----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|------------------------------------------------------------------------------------------|
| `E2E-PROD-001`   | 4471 | Coating viscosity sensor drifts; golden-batch score falls into `marginal`; in-line Cpk shortfall at cure; NCR raised and deduped across a shift; CAPA opened; containment quarantines three batches; corrective action is an ECO changing a recipe parameter; effectiveness verified at the ECO effectivity date; sustain check at 90 days passes; CAPA closes | capability report HTML, CAPA record JSON, batch records, detection-lead-time measurement |
| `E2E-PROD-002`   | 8812 | SMED program applied to `form_01`; paired CRN runs before and after; changeover time distribution, internal fraction, throughput delta with hypothesis-test verdict; capex request emitted                                                                                                                                                                     | VSM before and after, hypothesis result, schedule comparison                             |
| `E2E-QMS-003`    | 4471 | Supplier B lot 4471 arrives with elevated defect rate; AQL inspection under tightened severity rejects; NCR and supplier scorecard hit; contamination reaches three batches; timed mock recall drill over material and equipment-contact scope; recall-readiness report with Merkle proof bundle; quarantine issued                                            | recall report HTML and JSON, blast-radius counts, proof bundle, ground-truth comparison  |
| `E2E-PLM-004`    | 1337 | ECO from rev B to rev C, `forward_only`, six-week date effectivity; 1,200 units used up, 300 scrapped; two open POs amended with supplier acknowledgement; standard cost revised and consumed by finance; a later recall scopes to rev B only and correctly excludes rev C units                                                                               | ECO record, disposition table, standard cost rollup, revision-scoped recall result       |
| `E2E-BIZ-005`    | 2718 | ASN declares 40 cartons; RFID reads 38; CV counts 40; classified `read_failure`; no supplier NCR; E46 read-zone finding raised; portal read-rate control chart updated; a second ASN with a genuine short is classified correctly and does raise a supplier NCR                                                                                                | reconciliation report, confusion matrix, findings stream                                 |
| `E2E-CMMS-006`   | 3141 | Vibration trend on `form_01` crosses the PdM threshold estimate; work order created with RPN and deferral-cost curve from 30 paired CRN twin runs; agent recommends a window inside a planned changeover; work executed; MTBF updated; finding closed                                                                                                          | deferral cost curve, work order record, agent transcript                                 |
| `E2E-SOP-007`    | 1618 | A poorly written SOP revision lowers adherence; CV detects staging violations and cites clause `sop:RCV-002@r3#4.2`; NCRs accumulate; CAPA corrective action is an agent-drafted SOP revision that passes the grounding gate; training issued; adherence rises; hypothesis test confirms the improvement; SOP effectiveness recorded                           | SOP draft, grounding report, citation records, hypothesis result                         |
| `E2E-LEDGER-008` | 9001 | A full shift of genealogy events sealed into blocks; a customer checks a lot's chain of custody using only the standalone verifier and a published root; a deliberately tampered store is detected; a withheld entry is detected via root divergence                                                                                                           | verifier output, tamper report, withholding detection report                             |
| `E2E-PROD-009`   | 5772 | Level loading: the same released demand run under `as_released` and under `smoothed_by_family` on paired seeds; takt ratio per stage, leveling index, WIP, total setup seconds, throughput and operator load compared with the LSS engine's verdict on each delta                                                                                              | leveling report before and after, takt profiles, hypothesis result                       |
| `E2E-PROD-010`   | 6180 | Make versus buffer: baseline, third shift, SMED program and raised DC safety stock run as four arms on paired seeds; each arm's measured vector priced by the financial twin; ranked investment table with the bottleneck's final location named in each arm                                                                                                   | ranked investment table, per-arm measured vectors, bottleneck migration report           |
| `E2E-PROD-011`   | 2236 | Divergence and recalibration: a machine's true cycle time drifts away from its configured value; schedule adherence falls and buckets attribute to `machine_down` and `reduced_speed`; recalibration proposes a cycle-time refit; a human approves at E5 tier 2; the next window's adherence recovers and `twin_parameter_drift` is raised on the repeat move  | adherence series with cause attribution, recalibration plan, audit-trail entries         |

Each golden file is regenerated by `just golden-update` and reviewed in the diff, never
auto-accepted. Every scenario records its seed in its output header per C1.

---

## 8. Phase placement

The author's own phase order governs. Three kinds of movement are applied, each justified:
(a) **Phase 0 seam obligations**, where a contract cannot be retrofitted; (b) **as-listed**, the
default; (c) **dependency-driven moves** under the already-agreed rule that E-items which are
upstream dependencies of earlier work move ahead of their dependents. Nothing is dropped, deferred as
optional, or marked future work.

### 8.1 Phase 0 seam obligations

| Item                                                | What lands in Phase 0                                                                                                | Why it cannot wait                                                                                                                                                                                                                                      |
|-----------------------------------------------------|----------------------------------------------------------------------------------------------------------------------|---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| `twinflow-ledger` append-only core                  | `canonicalise`, `merkle_tree_hash`, `Ledger.append`, `seal`, `verify_chain`                                          | Every package in the repo writes to an audit trail. Retrofitting append-only semantics and hash chaining after twenty packages already write mutable records is the retrofit that fails. The Merkle proofs, signatures and EPCIS projection stay at E35 |
| `genealogy.Node.item_revision`                      | The field, required and non-null, populated with a literal `"-"` until PLM exists                                    | E37 is deep in Phase 6. If revision is added to the genealogy schema then, every recorded run before it becomes unreadable and C3's additive-only rule is violated at the most-referenced schema in the repo                                            |
| Reserved node attributes                            | `hs_code`, `country_of_origin`, `carbon_kgco2e`, `supplier_id`, `expiry` declared as optional in `genealogy.node.v1` | Same argument, for E14, E17 and 6a2                                                                                                                                                                                                                     |
| `Actor` with `autonomy_tier`                        | The audit-trail actor shape including agent fields                                                                   | E5 autonomy tiers are Phase 6, but every audit entry written before then must already have somewhere to record who or what acted                                                                                                                        |
| `/schemas` entries for `genealogy.*` and `ledger.*` | Versioned contracts                                                                                                  | C3                                                                                                                                                                                                                                                      |

### 8.2 Phase 3: the business-system loop

The author's order places the ERP/CMMS loop in Phase 3 alongside sensor breadth and predictive
maintenance. That is where 6b lands.

| Piece                                                           | Phase | Dependency reason                                                                                                                                                                                                      |
|-----------------------------------------------------------------|-------|------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| `twinflow-bizsys` ERP stub, ASN publication                     | 3     | Needs only the supplier stub and the receiving line from Phase 1                                                                                                                                                       |
| Three-way reconciliation, `read_failure` versus `genuine_short` | 3     | Needs RFID from Phase 1; the CV leg is stubbed as "CV unavailable" until Phase 4, at which point the full matrix activates. The matrix is written once, with the CV column optional, so Phase 4 adds data and not code |
| Mini CMMS work orders                                           | 3     | Needs the PdM layer, which is Phase 3                                                                                                                                                                                  |
| Deferral cost curve with paired CRN twin runs                   | 3     | Needs the what-if runner, which exists from Phase 1, and the sim clock from Phase 0                                                                                                                                    |
| `twinflow-genealogy` core graph and traversal                   | 3     | 6b requires "lot genealogy at warehouse scale: every pallet traceable truck to putaway". Everything later in this section builds on it                                                                                 |

### 8.3 Phase 3i: upstream production

All of 6a9. The author places it after the transport network and MEIO (3h), which is correct: the
factory schedule feeds the DC through the transport network, so transport must exist first.

Internal order within 3i, by dependency:

1. Plant topology, PackML state machines, machine registration in the device registry. Everything
   else needs machines that have states.
2. Discrete side: work centers, cycle times, buffers, blocking and starvation.
3. OEE and six-big-losses decomposition. Needs states and counts.
4. Batch side: ISA-88 recipes, phases, CPP trajectories, batch records. Needs the process/chemical
   sensor catalog entries, which the author schedules with 3i.
5. Genealogy extension upstream: transformation edges from raw lots through batches into the discrete
   side and out to finished lots. Needs the Phase 3 genealogy core.
6. FPY, RTY, scrap accounting, material conservation.
7. Golden-batch profiles and scoring. Needs enough completed batches to qualify a profile, so it
   comes after batches run.
8. In-line SPC wiring to the LSS engine and the detection-lead-time experiment.
9. Changeover recording and SMED analysis.
10. Finite-capacity scheduling with sequence-dependent setups; the `FactoryAsnSource` swap that feeds
    the DC inbound schedule.
11. Flow control: push, then kanban, then CONWIP, then drum-buffer-rope. Kanban needs the loops that
    the stage graph defines.
12. Takt profiles and level loading (5.22). Needs the stage graph, measured cycle times and the
    released schedule, so it follows both the flow control and the scheduler.
13. Schedule-versus-actual divergence findings and their cause attribution (5.23). Needs the
    published schedule from step 10 and the state and buffer histories from steps 1 and 2.
14. Production-twin recalibration from telemetry (5.24). Needs enough completed batches and cycles
    for the estimators to have data, so it follows the batch and discrete sides and the golden
    profiles.
15. The make-versus-buffer what-if (5.25) and the one-point-of-FPY valuation experiment. These are
    last because they compose everything above plus the DC, the planning layer and the financial
    twin.

### 8.4 After 3i: 6a10, then 6a11

The author's order is 3i, then 6a10 (safety and ergonomics), then 6a11 (QMS). 6a11 lands as follows,
in dependency order:

1. Audit trail with agent attribution. Everything in the QMS writes to it.
2. NCR engine with dedupe. Needs the findings stream from Phase 2 and the alarm-rationalization
   dedupe pattern.
3. Acceptance sampling with switching rules. Needs the supplier network from 3e and inbound lots.
4. CAPA workflow. Needs NCRs and the LSS hypothesis and power modules from Phase 2.
5. **`twinflow-sop` clause index (part of E8, moved forward).** The audit checklists in step 6 need
   clause-addressable documents and the same retrieval machinery. Building the index twice would be
   the waste. The move is justified under the agreed rule: E8 is an upstream dependency of 6a11.
   The retrieval-to-CV citation binding stays at Phase 4 where the CV auditor lands.
6. Audit checklists as code and layered process audits.
7. COPQ classification and posting.
8. CoA generation.
9. Mock recall drill. Needs genealogy (Phase 3), production genealogy (3i), outbound shipping (3e),
   and quarantine actions. It is last in 6a11 because it is the demo that composes all of it.

### 8.5 Phase 4: CV auditing and store-and-forward

- The rest of E8: retrieval binding, the citation contract on CV violations, the abstention path, and
  the constructed eval set with its published precision and wrong-clause rate. This is where E8 sits
  in the author's list only as far as the CV dependency goes; the index moved to 6a11 above.
- The CV column of the reconciliation matrix activates (8.2).

### 8.6 Phase 6: the bleeding-edge list, in the author's stated order

| Item                         | Position               | Notes                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                     |
|------------------------------|------------------------|-------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| E10 digital product passport | As listed at E10       | Depends only on genealogy, which exists from Phase 3. The source permits pulling an item forward when it is nearly free, and the passport generator plus resolver adds no new subsystem: it projects a graph that already exists and serves it on a route the dashboard already has. **Recommendation, for the author to confirm:** ship the passport generator immediately after 6a11 and leave the cryptographic upgrade at E35, which makes the 6a11 recall demo better and gives E1's replay viewer a shareable artifact. Recorded as a recommendation, not a unilateral resequencing |
| E24 generative SOPs          | **Moved to after E26** | E24 as listed precedes E26, but E24's grounding gate is E26(f). Under the agreed rule that dependencies move ahead of dependents, E26 precedes E24. Flagged as Open Question 9.4 so the author can confirm the rule applied here rather than the number order                                                                                                                                                                                                                                                                                                                             |
| E35 ledger completion        | As listed at E35       | Merkle proofs, Ed25519 signatures, signature policy, root publication, EPCIS 2.0 projection, standalone verifier. The append-only core already landed in Phase 0, so this phase is proofs, signatures and the standard format, not foundations                                                                                                                                                                                                                                                                                                                                            |
| E37 PLM and ECM              | As listed at E37       | The `item_revision` field it needs already exists from Phase 0. When E37 lands, the field stops being `"-"` and starts carrying real revisions; no schema change, no unreadable historical runs                                                                                                                                                                                                                                                                                                                                                                                           |

Two consequences of E37 landing at its listed position are worth stating so nobody is surprised. Any
recorded run from before E37 resolves every revision to `"-"`, and `RevisionScope` recall over those
runs returns the whole item rather than a revision slice; the C6 compatibility table states this.
And the CoA's `item_revision` field reads `"-"` until E37, which is honest rather than fabricated.

### 8.7 Resequencing record

Section 1 names five seams whose owning item lands later than the work that first needs them. Each
is recorded here with what moves, why, and what is bound in the meantime. Nothing is dropped,
deferred as optional, or marked future work: every item below still lands at its own position with
its full scope, and only the seam moves ahead of it.

| Item that moves ahead    | Moves to  | What exactly moves                                                                                    | Why it cannot wait                                                                                                                                                           | What the later item still owns                                           |
|--------------------------|-----------|-------------------------------------------------------------------------------------------------------|------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|--------------------------------------------------------------------------|
| E26(b) governed metrics  | 6a11      | The metric registry and the subset of metric names this section's CAPA plans and checklists reference | A `VerificationPlan` frozen before implementation must name a metric that resolves, or the freeze proves nothing. Free-text metrics are rejected at load from the first CAPA | The full metrics layer, its SQL expressions and its dimensional model    |
| E26(f) grounding checker | 6a11      | The checker itself, run over audit-trail justifications                                               | The audit trail's first entry already records query result ids behind a number, and a recorded id nobody checks is decoration                                                | The agent-facing integration and the abstention policy on top of it      |
| E8 clause index          | 6a11      | `parse_sop`, `ClauseIndex`, `build_index` and `effective_at`                                          | The audit checklists of 5.14 need clause-addressable documents and the same retrieval machinery. Building the index twice is the waste                                       | Retrieval binding to CV violations, the citation contract, the eval set  |
| E9 study runner          | 3i        | The `StudyRunner` protocol and one Optuna binding, used by `optuna_search` in 5.5                     | The scheduler's third rung is an optimization study, and the seam E9 later reuses is cheaper to declare once than to retrofit                                                | The general optimization engine, its search spaces and its cost budget   |
| E24 generative SOPs      | after E26 | The whole of E24                                                                                      | E24's grounding gate is E26(f). Shipping E24 first would leave a window in which generated SOPs carry unverified numbers                                                     | Nothing moves out of E24; only its position changes, and 9.4 confirms it |

Two registration obligations follow from section 2 and are recorded here so they are not discovered
during a release. The seven packages of this section are added to `[tool.twinflow.layers]` as domain
packages when the first of them lands, which is `twinflow-ledger` in Phase 0. The protocols this
section binds (`GenealogyOracle`, `LedgerWriter`, `StatisticalOracle`, `AuthorityOracle`,
`MetricOracle`, `GroundingOracle`, `AutonomyOracle`, `AuditorAvailability`, `ModelRefResolver`,
`ReadZoneOracle`, `RunbookResolver`, `StudyRunner`) are declared in `twinflow-kernel` at the phase
where their first consumer lands, each with a default binding that raises a named error rather than
returning a plausible value.

---

## 9. Open questions

These are genuine ambiguities in the source or genuine decisions the author must own. None has been
resolved silently.

**9.1 Which supplier becomes the factory, and what does it make?**
The source says "one becomes a simulated factory the twin models from the inside" but does not say
which tier-1 or what it produces. This changes the genealogy topology materially. If the factory
makes a component that the DC's SKUs consume, the DC's items need BOMs and the DC becomes an assembly
point. If the factory makes a finished good the DC only receives and ships, the DC's items have no
BOM and genealogy is a simple chain. The spec above assumes the second (factory makes finished goods,
DC is pure distribution) because it keeps the DC's existing model intact, but the first is the more
impressive demonstration and would let the recall drill cross an assembly boundary. Author decision.

**9.2 Z1.4 versus MIL-STD-105E, and the switching-score rules.**
The proposal is to build from MIL-STD-105E, describe the capability as "ANSI/ASQ Z1.4-class" in
prose, document the two differences, and build both switching rulesets. Two facts are settled and one
is not. Settled: 17 U.S.C. 105(a) removes copyright protection from works of the United States
Government, and MIL-STD-105E is a Department of Defense publication. Not settled: the Z1.4
switching-score rules could not be read from the standard, which is paid, so they rest on a secondary
description named in `docs/sampling_provenance.md`. The author must check them against a licensed
copy before the alternate ruleset ships, confirm the "Z1.4-class" phrasing for a public README, and
confirm nobody expects the Z1.4 tables themselves in the repository.

**9.3 GS1 EPCIS 2.0 artifact licensing.**
Emitted documents must validate against the GS1-published EPCIS 2.0 JSON schema, and the round-trip
gate uses GS1's published example documents. Whether those artifacts can be vendored into an Apache-2.0 repo
or must be fetched at test time depends on their license, which must be checked before Phase 6 rather
than assumed. If they cannot be vendored, VAL-GATE-LEDGER-4 becomes a network-dependent gate that is
skipped with a loud message when offline, which weakens the CI story. The author decides between
accepting that and writing a conformance subset by hand.

**9.4 E24 depends on E26, but is listed before it.**
E24's grounding gate is E26(f). The spec applies the agreed resequencing rule and puts E26 first.
Confirm that is what the author wants rather than shipping E24 ungated and retrofitting the gate,
which would leave a window where generated SOPs contain unverified numbers.

**9.5 OEE has no free certified reference dataset.**
NIST StRD does not cover it, the NIST/SEMATECH e-Handbook does not cover it, and ISO 22400-2 and
SEMI E79 are paid standards whose worked examples cannot be redistributed. VAL-GATE-PROD-1a is
an invariant gate over a closed-form construction and exact loss-accounting closure, and
ISO 22400-2 and ISA-TR88.00.02 are cited as definition sources without being reproduced. Under D-11
that means OEE never appears in the README's "validated against published references" table. If the
author wants a reference gate here, the only routes are to buy a standard and encode a worked example
privately, which cannot then be published, or to accept the invariant gate and say so. Author
decision, and it decides what the README may claim about this particular number.

**9.6 Standards text reproduction generally.**
ISO 9001 clause text, ISA-TR88.00.02 state descriptions, ISO 22400-2 KPI definitions, and the ASC
X12 856 transaction set whose Shipment-Order-Tare-Pack-Item hierarchy 5.16 models are all
copyrighted and paid. The spec references clause, state and segment **names and numbers** and writes
twinflow's own wording throughout. Two things need confirming. First, that referencing ISO 9001
clause numbers alongside twinflow's own `local_label` is acceptable in a public repository. Second,
that the specific clause numbers used in the shipped checklists were checked against a licensed copy
of ISO 9001:2015; they are used here as widely published clause identifiers, not as text read from
the standard, and nothing in this section verifies them.

**9.7 How much physics does the batch stage need?**
Two options. (a) Parameterized trajectories (ramp, soak, decay plus noise): deterministic, cheap,
enough for golden-batch scoring and for the process sensors to read something meaningful. (b) A
small ODE model for the cure kinetics, which would make the chemical sensors (pH, dissolved oxygen,
conductivity) physically coherent with each other rather than independently generated. The spec
assumes (a). Option (b) is more defensible under interrogation by anyone with a process background,
and it makes the 2b chemical sensor category genuinely earn its place, but it is meaningfully more
work in 3i. Author decision on where the fidelity bar sits.

**9.8 Signature key custody.**
The spec derives all keys from the run seed at runtime and commits nothing. Confirm that, and
confirm the README says plainly that these are simulation keys with no real-world assurance, so
nobody reads the passport check demo as a claim about production cryptography.

**9.9 CAPA multiplicity across the portfolio.**
One primary metric per CAPA is specified. Across many CAPAs, running many tests at alpha 0.05
produces some false "effective" verdicts by construction. Options: leave it and publish the measured
false-effective rate (which the twin can compute because it knows the truth), or add a
portfolio-level alpha-spending policy. The spec takes the first because it is more honest and more
interesting to show. Confirm.

**9.10 Recall scope semantics.**
Does "quarantine everything touched by supplier B's lot 4471" mean material lineage only, or does it
include units that shared equipment with the affected material without sharing material (the allergen
and cross-contamination case)? Real recalls often include equipment-contact scope. The spec
implements both (`EquipmentContactScope`) and makes the default a config key
(`recall.default_scope`), but the author must name the default the demo uses, because
equipment-contact scope produces a much larger and more dramatic blast radius and the demo's
credibility depends on the scope being stated rather than assumed.

**9.11 Who owns inventory balances?**
The ERP stub, the WMS, and the finance layer all have a claim. The spec proposes: WMS owns physical
on-hand, ERP stub owns book quantity, and book-versus-physical divergence becomes a KPI, which is
exactly what 6a17 asks for and what the RFID accuracy story needs. Confirm, because the alternative
(single shared inventory service) is simpler but destroys the book-versus-physical measurement that
the author's own inventory-record-accuracy narrative depends on.

**9.12 Can the AI agent release a CoA?**
The spec says no: the agent may prepare, a human role must release, and an agent attempting release
raises `unauthorised_release_attempt`. This is the correct answer for a regulated quality system and
it makes a good point about autonomy limits, but it does mean one artifact in the repo is
deliberately not fully autonomous. Confirm that is the intended message, and confirm the same rule
applies to ECO approval and CAPA closure, which is what the spec does with all three.

**9.13 Golden-batch bootstrapping.**
The first golden profile must be built from batches that were never scored against a golden profile.
The spec records that lineage explicitly (`built_from` plus `qualification_rule`) so the bootstrap is
auditable rather than hidden. The open part is which qualification rule governs the very
first profile, when no CAPA or NCR history exists yet. Options: use the sim's known-good parameters
directly (honest but circular, since the twin then scores itself against its own generator), or
need a minimum number of released batches with no findings (slower to bootstrap but not circular).
The spec assumes the second. Author confirmation matters here because the first option would make
every golden-batch score a tautology and an interviewer would find that.

**9.14 The ISA-TR88.00.02 edition year.**
5.3 names ISA-TR88.00.02 as the formal source for the PackML state names and transition graph, and
OMAC's own PackML page confirms that PackML was developed by OMAC and adopted by ISA under that
designation. The edition year could not be read: isa.org returned 404 for the product page and the
ANSI webstore search was blocked by its content-delivery network on 2026-08-10. The edition must be
confirmed from a licensed copy before the README cites the technical report, because a citation with
the wrong year is worse than no citation. Until then the section cites the designation without a
year, which is why VAL-GATE-PROD-1b checks annotation coverage rather than numeric agreement.

**9.15 The Taillard lower-bound table.**
VAL-GATE-PROD-2 falsifies on a makespan below an instance's published lower bound. The instances and
their bounds are Taillard's, and the paper's metadata is confirmed, but the author's original
benchmark host did not respond on 2026-08-10, so the bound table itself was not retrieved. The gate
cannot ship until a live copy of the instance and bound distribution is obtained and vendored with
its license checked. If no redistributable copy exists, the fallback is to check the evaluator
against hand-computed instances only and to say in the README that the scheduler is checked against
constructed instances rather than against a published benchmark. That is a real weakening, and the
author must choose it deliberately rather than inherit it.

**9.16 The acceptance level for the SOP citation gate.**
VAL-GATE-SOP-1 measures precision@1, recall@3 and the wrong-clause rate over 2,000 injected
violations, publishes each with a one-sided 99 percent bound, and asserts no regression against the
recorded baseline. It asserts no absolute threshold, for two reasons. No external source publishes
one for clause-level citation over a governed corpus. And a threshold set at a value the system
truly achieves fails about half the time by sampling alone unless the sample is large enough to
separate them, which is a coin flip rather than a gate. The open part is what the project's own
acceptance level is, and whether falling below it blocks a release. That is a product decision, not
a statistical one, so the author owns it.
