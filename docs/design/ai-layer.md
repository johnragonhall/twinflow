---
title: AI layer
description: The agent runtime, accuracy stack, MCP surface, multi-agent governance, computer vision auditing, and model lifecycle for twinflow.
topic_type: reference
audience: contributors
---

# AI layer

The agent, the accuracy stack, MCP, multi-agent governance, computer vision auditing, and the ML lifecycle.

This section is an implementation contract. Every capability named here has a package, a schema, a config key, and a test. Where a number is claimed, the test that produces it is named. Where a statistic is validated, the external published reference is named, along with the tolerance the test asserts and the result that would falsify it. A statistic with no external reference is published in section 7.6 with its method and no pass threshold, never as a passing gate.

`docs/design/DOCTRINE.md` binds this section. Where a ruling and this section disagreed, the ruling won and this section changed. Each application cites its ruling id. The rulings applied here are D-01, D-02, D-03, D-04, D-05, D-07, D-09, D-10, D-11, D-12, and D-14.

Evidence rules, applied throughout. A claim whose primary text was retrieved and quoted ships plainly, with its locator. A claim carried by one secondary source ships with the source named in the sentence. A claim that could not be verified never ships as fact: it appears in section 9 as an open question. Three measurements the requirements source attributes to the accuracy stack could not be retrieved and are recorded that way in open questions 15, 16, and 17.

---

## 1. Scope

This section owns the following numbered requirements in full.

| Requirement | Title                                                                                                                                                                          | Ownership                                |
|-------------|--------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|------------------------------------------|
| 4           | Computer vision auditing (SOP compliance, independent throughput counting, sensor disagreement as a finding)                                                                   | Full                                     |
| 7           | AI agent: `get_fleet_health`, `get_bottleneck`, `get_findings`, `run_whatif`, `run_capability_report`, `explain_finding`, `compare_scenarios`, grounded answers, refusal tests | Full                                     |
| E2          | MCP server exposing twin, fleet, and LSS tools with a one-line Claude Desktop config                                                                                           | Full                                     |
| E21         | Collaborative multi-agent system with decision governance (role agents, supervisor budgets, decision register, counterfactual audit)                                           | Full                                     |
| E25         | Synthetic data products with dataset cards                                                                                                                                     | Full                                     |
| E26         | The accuracy stack, layers (a) through (g), plus live README metrics                                                                                                           | Full                                     |
| E27         | Agent evaluation harness with simulation-derived ground truth, case-based incident memory, published improvement curve                                                         | Full                                     |
| E29         | Vision-language operations copilot benchmarked against the classical CV channel                                                                                                | Full                                     |
| E30         | Causal inference with ground-truth structure and effect recovery                                                                                                               | Full                                     |
| E31         | Forecasting foundation-model bakeoff, conformal calibration, interval coverage on a control chart                                                                              | Full (model arena and conformal wrapper) |
| E32         | Plant-distilled edge SLM, benchmarked against the hosted model, deployed air-gapped at tier 1                                                                                  | Full                                     |
| E33         | GNN for disruption propagation, validated against simulated truth, compared with E20                                                                                           | Full                                     |
| E34         | Local voice interface                                                                                                                                                          | Full                                     |
| E43         | MLOps for the twin's own models plus the AI red-team suite                                                                                                                     | Full                                     |
| E45         | AI FinOps: cost-aware routing, per-question and per-tool accounting, cache hit rates, monthly AI P&L                                                                           | Full                                     |

This section also owns the AI-facing half of requirements whose other half lives elsewhere.

| Requirement | This section owns                                                                                                                                                                                                                                                                      | Owned elsewhere                                                                                                                     |
|-------------|----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|-------------------------------------------------------------------------------------------------------------------------------------|
| E5          | The decision register, authority tiers, the tool-permission gate that implements L1/L2/L3, and the tier-transition contract (elevation request, approval, scope, expiry)                                                                                                               | The bi-directional connector that writes an approved change back into the running config                                            |
| E8          | Retrieval over `sop/*.md`, clause-level citation in agent answers and CV violations, the citation-integrity test                                                                                                                                                                       | Authoring the SOP corpus and the QMS versioning of it                                                                               |
| E28         | The agent-side policy that searches with the surrogate and confirms winners with the full simulation                                                                                                                                                                                   | Training and validating the surrogate itself                                                                                        |
| A1          | Package topology and installability for every AI brick listed in section 2                                                                                                                                                                                                             | The workspace tooling (C10) and the release automation (C9)                                                                         |
| A6          | MCP as one integration surface, and the tool registry the REST/GraphQL layer reuses                                                                                                                                                                                                    | The REST/GraphQL server and webhook dispatch                                                                                        |
| C1, C2      | `ModelTransport` record/replay for every model call in the repository, the kernel RNG child seeds `agent.accuracy.self_consistency_nonce`, `agent.transport.latency`, and `vision.vlm.sample`, sim-time cost of a model call, and the `@causal_edge` decorator's registration contract | The kernel clock, RNG, network, and storage interfaces themselves, and the placement of `@causal_edge` on each kernel process class |
| C3          | The `/schemas/agent/**`, `/schemas/governance/**`, `/schemas/mlops/**`, `/schemas/vision/**` contracts                                                                                                                                                                                 | The registry mechanism and the producer/consumer contract test runner                                                               |
| C7          | The threat-model note for the MCP surface and the SQL/Python sandbox boundary                                                                                                                                                                                                          | SECURITY.md as a document                                                                                                           |

Requirements referenced but not owned: 1, 1b, 2, 2b, 3, 5, 6, 6a through 6a17, 6b, 6c, 8, 9, E1, E3, E4, E6, E7, E9 through E20, E22 through E24, E35 through E42, E44, E46 through E48, C4 through C6, C8 through C12, A2 through A5. Where this section consumes one of them, it declares the exact fields it depends on. The C3 consumer contract test then fails on drift.

---

## 2. Packages

Distribution names are `twinflow-<name>`; import names are `twinflow.<name>` under a PEP 420 namespace package. Every distribution declares only its own dependencies, ships its own README, its own tests, and its own `pip install` path, per A1. No package imports another package's internals.

Three layering rules bind, from D-09 and D-10.

1. Every public symbol has exactly one owning package. Other packages import it and never redeclare it.
2. Cross-package data crosses on one of two channels and no third: a versioned schema'd event or schema'd record from `/schemas` (C3), or a structural protocol declared by the consumer and satisfied by the producer. A concrete class from another package never appears in a public signature.
3. Any dependency that would otherwise be dragged downward ships as an extra, and the concrete type is imported only under `TYPE_CHECKING`.

A CI job installs each distribution alone into a clean virtual environment and imports its public API, which is the only test that proves A1 rather than asserting it (D-10). A second CI job walks the import graph and fails on a cycle, and a third asserts every name in each package's `__all__` is defined in that package (D-09).

| Distribution          | Purpose                                                                                                                        | Requirements                                 | Heavy deps                                              |
|-----------------------|--------------------------------------------------------------------------------------------------------------------------------|----------------------------------------------|---------------------------------------------------------|
| `twinflow-semantics`  | Governed metric layer and the sandboxed execution substrate                                                                    | E26(a), E26(b)                               | duckdb, deltalake, sqlglot, pydantic                    |
| `twinflow-accuracy`   | Verification loop, structured-output enforcement, self-consistency, rubric verifier, grounding checker, abstention calibration | E26(c) to E26(g)                             | pydantic, outlines/xgrammar (extra)                     |
| `twinflow-agent`      | Tool registry, the component 7 tools, agent runtime, model providers, SOP retrieval, transcripts                               | 7, E8, E28 (agent side)                      | pydantic-ai                                             |
| `twinflow-mcp`        | MCP server over the tool registry                                                                                              | E2, A6                                       | mcp                                                     |
| `twinflow-governance` | Authority tiers, budget ledger, role agents, supervisor, negotiation protocol, decision register, counterfactual audit         | E21, E5 (register side), E43 (approval gate) | pydantic                                                |
| `twinflow-evals`      | Eval suite, simulation-derived ground truth, scoring, incident memory, improvement curve, red-team suite                       | E27, E43 (red team)                          | duckdb                                                  |
| `twinflow-vision`     | Frame ingest, classical detector, SOP compliance rules, independent counting, reconciliation, VLM copilot, head-to-head bench  | 4, E29                                       | opencv-python, pillow                                   |
| `twinflow-mlops`      | Model registry, lineage, drift monitors, champion-challenger shadow, retraining triggers, rollback                             | E43                                          | duckdb, scipy                                           |
| `twinflow-causal`     | Causal graph, identification, estimation, refutation, structure and effect recovery scoring                                    | E30                                          | dowhy, econml, causal-learn                             |
| `twinflow-forecast`   | Forecast arena: entrants, rolling-origin backtest protocol, ranking tests, conformal wrappers                                  | E31                                          | statsforecast, mapie or custom conformal, torch (extra) |
| `twinflow-cascade`    | Disruption-propagation GNN, scenario sampler, sim-truth scoring, heuristic and E20 baselines                                   | E33                                          | torch, torch-geometric                                  |
| `twinflow-edge-ai`    | Plant-distilled SLM pipeline and edge serving (`[distill]`), local voice pipeline (`[voice]`)                                  | E32, E34                                     | peft, llama-cpp-python, faster-whisper, piper-tts       |
| `twinflow-datasets`   | Dataset export layer and dataset cards                                                                                         | E25                                          | pyarrow                                                 |
| `twinflow-finops`     | Price book, cost accounting, model router, cache policy, AI P&L postings                                                       | E45                                          | pydantic                                                |

A package exists when it has a distinct dependency footprint and a standalone adopter. `twinflow-accuracy` depends on `pydantic` and on nothing else at runtime. It reaches the ledger, the sandbox, and the compiled query through protocols it declares itself, so a team that already has an agent can install it and satisfy those protocols with its own classes. `twinflow-semantics` installs with no agent, because a governed metrics layer over DuckDB and Delta stands alone. The install-alone CI job covers both claims. The flagship README's "use just this part" table routes: quality manager to `twinflow-lss`, AI engineer to `twinflow-accuracy`, data engineer to `twinflow-semantics`, MLOps engineer to `twinflow-mlops`.

`EvalResultRecord` is the one type that would otherwise create a cycle: abstention calibration lives in `twinflow-accuracy`, and the results it calibrates on are produced by `twinflow-evals`, which runs the agent, which depends on accuracy. The cycle is cut by putting the record in the schema registry at `/schemas/agent/eval_result/v1.json` (D-09). `AbstentionPolicy.calibrate` takes a sequence of those records, not a class owned by evals. That also makes the checked-in `configs/abstention_policy.json` regenerable from the event log alone.

### 2.1 Public API surface

`twinflow.semantics`

```python
class MetricLayer:
    @classmethod
    def load(cls, path: Path) -> "MetricLayer": ...
    def metric(self, name: str) -> MetricDef: ...
    def compile(self, sel: MetricSelection) -> CompiledQuery: ...   # -> SQL + required watermark
    def list_metrics(self, *, domain: str | None = None) -> list[MetricDef]: ...
    def catalog_snippet(self, names: Sequence[str]) -> str: ...     # prompt-sized schema text

class Limits:
    memory_limit_mb: int          # ai.sandbox.memory_limit_mb
    threads: int                  # ai.sandbox.threads, pinned to 1
    max_rows_scanned: int         # ai.sandbox.max_rows_scanned, the deterministic budget
    max_result_rows: int          # ai.sandbox.max_result_rows
    extension_dir: Path           # ai.sandbox.extension_dir, baked at image build

class Sandbox(Protocol):
    def run_sql(self, sql: str, *, limits: Limits) -> QueryResult: ...
    def run_python(self, src: str, *, limits: Limits) -> QueryResult: ...

class DuckDBSandbox(Sandbox): ...
class ResultLedger:
    def record(self, result: QueryResult) -> ResultId: ...
    def numerals(self) -> Iterator[LedgerNumeral]: ...
    def get(self, rid: ResultId) -> QueryResult: ...
```

`twinflow.accuracy`. Every cross-package type in these signatures is a protocol this package declares, so the distribution installs and runs with `pydantic` alone (D-09, D-10). `twinflow.semantics` satisfies the protocols structurally; it is not imported.

```python
class LedgerLike(Protocol):
    def numerals(self) -> Iterator[LedgerNumeral]: ...
    def get(self, rid: ResultId) -> ResultLike: ...

class ExecutorLike(Protocol):
    def run_sql(self, sql: str, *, limits: Limits) -> ResultLike: ...

class QueryLike(Protocol):
    sql: str
    metric_refs: Sequence[str]
    tables: Sequence[str]

class GroundingChecker:
    def __init__(self, ledger: LedgerLike, policy: GroundingPolicy): ...
    def check(self, answer: str) -> GroundingVerdict: ...          # PASS | REFUSE + unmatched numerals

class GroundingPolicy:
    @classmethod
    def strict(cls) -> "GroundingPolicy": ...                      # every allowance off
    def allowances(self) -> Mapping[str, bool]: ...                # the enumerated flag set

class SelfConsistency:
    def run(self, sampler: Callable[[int], QueryLike], executor: ExecutorLike, n: int) -> ConsensusResult: ...

class RubricVerifier:
    def score(self, q: QueryLike, ctx: QuestionContext) -> RubricScore: ...

class RepairLoop:
    def run(self, gen: QueryGenerator, executor: ExecutorLike, max_retries: int) -> ResultLike: ...

class AbstentionPolicy:
    @classmethod
    def calibrate(
        cls,
        results: Sequence[EvalResultRecord],                       # /schemas/agent/eval_result/v1.json
        target: float,
        min_support: int,
    ) -> "AbstentionPolicy": ...
    def decide(self, signals: ConfidenceSignals) -> AbstentionDecision: ...
    def risk_coverage_curve(self) -> RiskCoverageCurve: ...
```

`twinflow.agent`

```python
class ToolRegistry:
    def register(self, fn: ToolFn, *, tier: AutonomyTier, schema: type[BaseModel]) -> None: ...
    def json_schemas(self) -> dict[str, dict]: ...                 # single source of truth for MCP and REST
    def allowed(self, tier: AutonomyTier) -> list[str]: ...

class Agent:
    def __init__(self, registry, layer, accuracy, governance, finops, transport): ...
    def ask(self, question: str, *, ctx: AskContext) -> Answer: ...
    def transcript(self) -> Transcript: ...                        # E1 replay viewer input

class ModelTransport(Protocol):
    def complete(self, req: ModelRequest) -> ModelResponse: ...
class LiveTransport(ModelTransport): ...
class RecordingTransport(ModelTransport): ...
class ReplayTransport(ModelTransport): ...
```

`twinflow.governance`

```python
class BudgetLedger:
    def reserve(self, actor: ActorId, amount: Budget) -> Reservation: ...
    def settle(self, r: Reservation, actual: Budget) -> None: ...
    def remaining(self) -> Budget: ...

class DecisionRegister:
    def record(self, d: DecisionRecord) -> DecisionId: ...          # append-only, hash-chained
    def backfill_outcome(self, did: DecisionId, o: RealizedOutcome) -> None: ...  # appends, never mutates
    def verify_chain(self) -> ChainVerdict: ...
    def replay_counterfactual(self, did: DecisionId, alternative: str) -> CounterfactualResult: ...

class Supervisor:
    def solve(self, task: NegotiationTask, roles: Sequence[RoleAgent]) -> Award: ...
```

`twinflow.mcp`, `twinflow.evals`, `twinflow.vision`, `twinflow.mlops`, `twinflow.causal`, `twinflow.forecast`, `twinflow.cascade`, `twinflow.edge_ai`, `twinflow.datasets`, `twinflow.finops` expose the entry points named in the behavior subsections below. Each ships a console script wired into the justfile: `twinflow-mcp`, `twinflow-evals run`, `twinflow-vision audit`, `twinflow-mlops promote`, `twinflow-forecast bakeoff`, `twinflow-datasets export`, `twinflow-finops report`.

---

## 3. Domain model

### 3.1 Question and answer

`Question`: `question_id` (ULID), `text` (str), `asked_by` (ActorId: human user id or role agent id), `sim_time` (int, sim microseconds), `session_id`, `autonomy_tier` (L1|L2|L3), `budget` (Budget), `channel` (chat|mcp|voice|eval|multi_agent).

`Question` carries no wall-clock field (D-02). The wall-clock arrival instant of a question is written by the provenance sidecar writer to `runs/<run_id>/profile.ndjson`, keyed by `question_id`, and is never read by any control path (D-01).

`Answer`: `question_id`, `text`, `abstained` (bool), `abstain_reason` (enum or null), `result_ids` (list[ResultId]), `citations` (list[Citation]), `tool_calls` (list[ToolCallRef]), `grounding` (GroundingVerdict), `confidence` (ConfidenceSignals), `model_route` (RouteDecision), `cost` (CostRecord), `sim_latency_us` (int, from the modeled transport latency, C2), `seed`, `transcript_id`.

Invariants:

- Every numeral in `Answer.text` maps to a `ResultId` in `result_ids` under the grounding policy, or `abstained` is true.
- `abstained == True` implies `Answer.text` contains no numeral outside the echoed question span.
- `result_ids` is a subset of the ledger entries produced by tool calls that returned successfully. A failed tool contributes nothing.
- `cost.total_usd` equals the sum of `cost` over `tool_calls` plus the model cost of the turn, to the cent.
- `sim_latency_us` is a function of the seed, the config, and the cassette. Wall-clock latency for the same turn lands in the profile sidecar and is never compared against it inside a test assertion.

### 3.2 Metric and query

`MetricDef`: `name` (snake_case, unique), `type` (simple|ratio|derived|cumulative), `expr` or (`numerator`, `denominator`), `unit`, `domain` (min, max, both optional), `grain` (list[entity]), `agg_time_dimension`, `allowed_dimensions` (list), `definition_source` (path anchor), `fixture` (path), `owner_package`, `since_version`.

Invariants: a ratio metric's numerator and denominator are declared measures; `domain.min < domain.max`; every metric's SQL parses under sqlglot's DuckDB dialect; every metric references only tables in the read allowlist; every metric has an existing fixture file.

`MetricSelection`: `metric` (name), `dimensions` (list), `filters` (list[Filter]), `time_window` (start, end in sim time), `grain`, `limit`.

`CompiledQuery`: `sql`, `metric_refs` (list[str]), `tables` (list[str]), `required_watermark` (per-table max event id the answer depends on), `est_rows`.

`QueryResult`: `result_id` (monotone int within a run, allocated by the ledger's single-threaded allocator), `sql_hash`, `columns`, `rows` (bounded), `scalars` (dict[str, Decimal] for the values the answer may cite), `row_count`, `rows_scanned` (int, the deterministic cost measure), `watermark` (per table), `error` (null on success).

`QueryResult` carries no wall-clock duration (D-02). Wall-clock query time is written to the profile sidecar keyed by `result_id`.

`LedgerNumeral`: `result_id`, `path` (column or scalar key), `value` (Decimal), `unit`, `magnitude_class` (count|ratio|currency|duration|rate|temperature|mass|distance|energy).

### 3.3 Tools

`ToolSpec`: `name`, `args_model` (Pydantic class), `result_model`, `tier` (minimum autonomy tier), `side_effects` (none|simulate|write_config), `cost_class` (cheap|sim|heavy), `sim_budget` (Budget or null), `deadline_sim_s`, `description`, `since_version`.

Authority and resource cost are separate axes and the spec keeps them separate. `tier` answers who may change the world. `sim_budget` answers what an experiment may consume. Running a simulation changes nothing outside the run, so it is not an authority question.

Invariants:

- `side_effects == write_config` implies `tier == L3`.
- `side_effects == simulate` implies `tier == L1` and `sim_budget` is not null. The budget is enforced by `BudgetLedger` exactly as a model-token budget is.
- `side_effects == none` implies `tier == L1` and `sim_budget` is null.
- Every tool named in a documented quickstart command is reachable at the shipped `autonomy.default_tier` with the shipped MCP flags. A cross-field config test asserts this over the quickstart command list in `docs/quickstart-commands.yaml`, so a tier change that breaks the headline demo fails CI (D-12).

### 3.4 Governance

`DecisionRecord`: `decision_id`, `sim_time`, `question_id` or `task_id`, `actor` (agent role or human), `authority_tier`, `alternatives` (list[Alternative]), `chosen` (alternative id), `inputs` (list[ResultId]), `expected_outcome` (metric, point estimate, interval, method), `constraints` (budget, policy refs), `approver` (ActorId or null), `model_versions` (dict), `policy_version`, `seed`, `prev_hash`, `hash`.

`Alternative`: `id`, `description`, `config_delta` (JSON Patch against facility.yaml), `projected` (dict[metric, PointWithInterval]), `cost_usd`, `score`.

`RealizedOutcome`: `decision_id`, `measured_at` (sim time), `metric`, `actual`, `variance_vs_expected`, `lss_verdict` (finding id if the variance is assignable cause).

Invariants: the register is append-only; `hash = H(prev_hash || canonical_json(record_without_hash))`; `verify_chain()` recomputes every hash; `backfill_outcome` appends a new record referencing the original, never edits it.

`Budget`: `usd` (Decimal), `tokens` (int), `tool_calls` (int), `sim_seconds` (int), `sandbox_rows_scanned` (int). Ordered componentwise; a reservation succeeds only if every component fits.

`Budget` carries no wall-clock component (D-02). A wall-second cap would make the tape depend on machine speed, which breaks C1 on the first slow runner. Every component is a count the run itself produces, so the same seed and config always produce the same reservation decisions. Loop control is a different concept and lives in its own type.

`LoopControl`: `max_rounds` (int), `patience` (int), `max_repair_retries` (int). It bounds iteration counts, not spend. A config test asserts that every budget key in `facility.yaml` deserializes into a complete `Budget` with all five components, and that every loop key deserializes into a `LoopControl`, so the two shapes cannot drift into one another.

`AutonomyGrant`: `grant_id`, `session_id`, `granted_tier` (L2|L3), `requested_by` (ActorId), `approver` (ActorId, a human at L2 and L3), `scope` (list of tool names, never a wildcard), `reason`, `expires_after_questions` (int), `expires_at_sim_time` (int), `decision_id`.

The tier-transition contract, which E5 requires and which the gate alone does not supply:

- A session starts at `autonomy.default_tier` and never rises on its own. The agent cannot elevate itself, and no tainted content can request elevation (see 5.12).
- A tool call refused by the gate emits `governance.autonomy.elevation.requested` carrying the tool, the tier needed, and the question id. That event is the approval seam the dashboard and the MCP client both render.
- A human approval emits `governance.autonomy.elevation.decided` with the `AutonomyGrant` or the refusal, and writes a `DecisionRecord`. The grant is scoped to named tools and expires on whichever of the two limits arrives first.
- Expiry emits `governance.autonomy.elevation.expired` and returns the session to `autonomy.default_tier`. There is no renewal path that skips a fresh approval.
- An L3 grant also needs `autonomy.allow_write_tools: true` in the facility config, so an operator cannot approve a write the deployment forbids.

### 3.5 Vision

`Frame`: `frame_id`, `sim_time`, `camera_id`, `width`, `height`, `path` (PNG), `render_seed`, `degradation` (DegradationSpec), `truth` (list[TruthObject], present only in dataset export mode).

`Detection`: `frame_id`, `class` (pallet|forklift|amr|operator|carton|placard), `bbox`, `track_id`, `confidence`, `detector_id`, `detector_version`.

`SOPRule`: `rule_id`, `sop_clause` (path anchor into `sop/*.md`), `predicate` (declarative over zones, classes, tracks, and sequence), `severity_floor`, `evidence_fields`.

`CountReconciliation`: `window`, `zone`, `count_cv`, `count_rfid`, `count_twin_truth`, `disagreement_cv_rfid`, `disagreement_cv_truth`, `disagreement_rfid_truth`, `kappa`, `p_chart_state`.

Invariant: the reconciliation record carries all three counts or is not emitted. Disagreement is symmetric and zero exactly when the two counts are equal.

### 3.6 Models and lifecycle

`ModelRecord`: `model_id`, `family` (pdm|forecast|cv|surrogate|dispatcher|slm|cascade|router), `version` (semver), `framework`, `training_run_id`, `dataset_card_id`, `feature_spec_hash`, `code_commit`, `seed`, `metrics` (dict), `artifact_sha256`, `license`, `status` (candidate|shadow|champion|retired), `promoted_at`, `retired_at`.

`DriftMonitor`: `monitor_id`, `model_id`, `kind` (input|prediction|residual), `feature`, `statistic` (psi|ks|wasserstein), `reference_window`, `chart` (control chart id in the LSS engine).

`ShadowComparison`: `champion_id`, `challenger_id`, `window`, `n`, `metric`, `delta`, `test` (paired t | Wilcoxon | McNemar), `p_value`, `effect_size`, `decision` (promote|hold|reject), `decision_id`.

Invariant: promotion requires a `ShadowComparison` with `n >= min_support`, `p_value <= alpha`, and `effect_size >= floor`, plus an approved `DecisionRecord`. No code path promotes without both.

### 3.7 Cost

`CostRecord`: `question_id` or `job_id`, `subsystem`, `tool`, `model_id`, `input_tokens`, `output_tokens`, `cached_input_tokens`, `usd_modeled`, `usd_actual` (null in replay), `price_book_version`.

Invariant: `usd_modeled` is always populated, including in replay mode, from the versioned price book. `usd_actual` is populated only when `transport.mode == live`.

### 3.8 Eval and memory

`EvalCase`: `case_id`, `suite`, `class` (lookup|metric|multi_hop|whatif|causal|ranking|abstain_required|adversarial), `question`, `ground_truth` (typed: scalar with unit and tolerance, ranking, set, or `ABSTAIN`), `facility_profile`, `seed`, `window`, `since_version`, `provenance` (how the truth was computed from the sim).

`IncidentCase`: `case_id`, `finding_signature` (finding type, subsystem, evidence feature vector), `context`, `actions_taken`, `outcome`, `time_to_resolution`, `embedding`, `source_seed_family`.

Invariant (leakage guard): `IncidentCase.source_seed_family` is disjoint from every `EvalCase.seed` family used for scoring. A test asserts the intersection is empty.

---

## 4. Events

All schemas live under `/schemas/<domain>/<name>/<major>.json`, are additive-only within a major version, and are validated in CI by the C3 producer/consumer contract tests. Every event carries the common envelope settled by D-07: `event_id` (ULID), `type`, `schema_version`, `sim_time` (int microseconds), `run_id`, `producer_id`, `producer` (package and version), `seq` (dense per `(run_id, producer_id)`), `seed`, `causation_id`, `correlation_id`.

The canonical total order over the log is `(sim_time, producer_id, seq)` (D-07). Every reader in this section uses that order: the replay viewer's transcript, the pagination cursor on the MCP resource, and the improvement-curve script.

**What the C1 hash covers.** The event-log hash covers the canonical JSON body of each event minus a declared non-deterministic field set, which is the same carve-out D-01 makes for the run manifest. The declared set is exactly: wall-clock durations, wall-clock timestamps, host and process identity, and provider-reported usage that exists only in `live` mode. No event in this section carries a field in that set, because those values are written to `runs/<run_id>/profile.ndjson` instead. The field set is a checked-in list at `/schemas/_hash_carveout.yaml`, and `test_hash_carveout_is_empty_for_ai_events` asserts that no schema under `/schemas/agent/**`, `/schemas/governance/**`, `/schemas/mlops/**`, or `/schemas/vision/**` declares a field named in it. A future addition fails CI rather than silently leaving the hash.

### 4.1 Published by this section

| Type                                      | Version | Payload                                                                                                                                                                                                 |
|-------------------------------------------|---------|---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| `agent.question.received`                 | v1      | `question_id`, `channel`, `asked_by`, `text_sha256`, `autonomy_tier`, `budget`                                                                                                                          |
| `agent.query.executed`                    | v1      | `question_id`, `result_id`, `sql_hash`, `metric_refs[]`, `tables[]`, `watermark{}`, `row_count`, `rows_scanned`, `error`                                                                                |
| `agent.tool.invoked`                      | v1      | `question_id`, `call_id`, `tool`, `args_sha256`, `tier`, `reserved_budget`                                                                                                                              |
| `agent.tool.returned`                     | v1      | `call_id`, `status` (one of ok, error, deadline_exceeded), `result_ids[]`, `duration_sim_us`, `cost`                                                                                                    |
| `agent.plan.rejected`                     | v1      | `question_id`, `retry_index`, `failure_class`, `violated_constraint`, `plan_sha256`                                                                                                                     |
| `agent.selfconsistency.sampled`           | v1      | `question_id`, `n`, `cluster_sizes[]`, `modal_value`, `agreement`, `no_majority` (bool), `majority_rule`                                                                                                |
| `agent.grounding.checked`                 | v1      | `question_id`, `verdict`, `numerals_total`, `numerals_unmatched[]`, `allowance_hits{}`, `policy_version`                                                                                                |
| `agent.abstained`                         | v1      | `question_id`, `reason` (one of tool_failure, no_majority, below_threshold, out_of_scope, budget_exhausted, verification_failed), `signals`                                                             |
| `agent.answer.emitted`                    | v1      | `question_id`, `text_sha256`, `abstained`, `result_ids[]`, `citations[]`, `cost`, `route`, `sim_latency_us`                                                                                             |
| `agent.route.selected`                    | v1      | `question_id`, `question_class`, `candidate_tiers[]`, `chosen_model`, `policy_version`, `predicted_pass`, `reason`                                                                                      |
| `agent.cache.lookup`                      | v1      | `question_id`, `key_sha256`, `namespace`, `hit` (bool), `required_watermark{}`, `entry_watermark{}`, `staleness_reject` (bool)                                                                          |
| `agent.cache.evicted`                     | v1      | `namespace`, `key_sha256`, `rank`, `reason` (one of capacity, watermark, policy_version)                                                                                                                |
| `finops.cost.accrued`                     | v1      | `job_id`, `subsystem`, `tool`, `model_id`, tokens, `usd_modeled`, `usd_actual`, `price_book_version`                                                                                                    |
| `finops.pnl.posted`                       | v1      | `period`, `account`, `cost_center`, `amount`, `source_event_ids[]`                                                                                                                                      |
| `governance.decision.recorded`            | v1      | full `DecisionRecord`                                                                                                                                                                                   |
| `governance.decision.outcome`             | v1      | `RealizedOutcome`                                                                                                                                                                                       |
| `governance.budget.reserved`              | v1      | `actor`, `reservation_id`, `amount`, `remaining`                                                                                                                                                        |
| `governance.budget.exceeded`              | v1      | `actor`, `requested`, `remaining`, `action` (one of deny, escalate)                                                                                                                                     |
| `governance.negotiation.round`            | v1      | `task_id`, `round`, `phase` (one of announce, bid, award, critique, revise), `actor`, `order_index`, `payload_sha256`, `score`                                                                          |
| `governance.autonomy.elevation.requested` | v1      | `session_id`, `question_id`, `tool`, `current_tier`, `needed_tier`, `reason`                                                                                                                            |
| `governance.autonomy.elevation.decided`   | v1      | `session_id`, `grant_id` or null, `granted_tier`, `approver`, `scope[]`, `expires_after_questions`, `expires_at_sim_time`, `decision_id`                                                                |
| `governance.autonomy.elevation.expired`   | v1      | `session_id`, `grant_id`, `trigger` (one of question_count, sim_time, revoked)                                                                                                                          |
| `vision.frame.captured`                   | v1      | `frame_id`, `camera_id`, `path`, `render_seed`, `degradation`                                                                                                                                           |
| `vision.detection`                        | v1      | `frame_id`, `detections[]`, `detector_id`, `detector_version`, `duration_sim_us`                                                                                                                        |
| `vision.sop_violation`                    | v1      | `rule_id`, `sop_clause`, `frame_ids[]`, `evidence`, `severity`                                                                                                                                          |
| `vision.count.reconciled`                 | v1      | `CountReconciliation`                                                                                                                                                                                   |
| `vision.vlm.observation`                  | v1      | `frame_ids[]`, `question`, `answer_sha256`, `claimed_events[]`, `model_id`, `transport_mode`, `cost`                                                                                                    |
| `mlops.model.registered`                  | v1      | `ModelRecord` minus mutable status fields                                                                                                                                                               |
| `mlops.shadow.scored`                     | v1      | `ShadowComparison`                                                                                                                                                                                      |
| `mlops.drift.detected`                    | v1      | `monitor_id`, `statistic`, `value`, `threshold`, `chart_id`, `severity`                                                                                                                                 |
| `mlops.retrain.requested`                 | v1      | `model_id`, `trigger` (one of drift, slo, schedule, manual), `decision_id`                                                                                                                              |
| `mlops.model.promoted`                    | v1      | `model_id`, `previous_champion`, `decision_id`                                                                                                                                                          |
| `mlops.model.rolled_back`                 | v1      | `model_id`, `restored`, `reason`, `decision_id`                                                                                                                                                         |
| `eval.run.completed`                      | v1      | `suite`, `suite_version`, `n_cases`, `accuracy`, `abstention_rate`, `grounding_pass_rate`, `cost_usd`, `p50_sim_latency_us`, `transport_mode`, `cassette_recorded_on`, `commit`, `seed`                 |
| `redteam.attack.attempted`                | v1      | `attack_id`, `family`, `surface` (one of device_name, sop_doc, supplier_record, finding_evidence, mcp_resource, frame_placard, incident_memory), `outcome` (blocked or succeeded), `defense_that_fired` |
| `dataset.exported`                        | v1      | `dataset_id`, `card_path`, `rows`, `bytes`, `sha256`, `config_hash`, `seed`, `license`                                                                                                                  |
| `forecast.published`                      | v1      | `series_id`, `origin`, `horizon`, `point[]`, `lower[]`, `upper[]`, `alpha`, `model_id`, `conformal_method`                                                                                              |
| `causal.estimate.published`               | v1      | `treatment`, `outcome`, `estimand`, `estimator`, `ate`, `ci`, `refutations[]`                                                                                                                           |
| `cascade.prediction`                      | v1      | `seed_disruption`, `horizon`, `nodes_at_risk[]`, `time_to_impact[]`, `model_id`                                                                                                                         |

### 4.2 Finding candidates emitted into the LSS engine's stream

This section does not own the `finding` schema. It emits `finding.candidate` records conforming to `/schemas/finding/v1` with these registered `source` values and finding types:

`vision.sop_violation`, `vision.sensor_disagreement`, `mlops.model_drift`, `mlops.shadow_regression`, `forecast.interval_coverage_breach`, `forecast.bias_drift` (shared with the planning section, which owns the point-forecast bias chart), `finops.cost_excursion`, `agent.grounding_refusal_rate_excursion`, `security.prompt_injection_blocked`, `governance.decision_outcome_variance`.

Each carries `severity`, `evidence` (window plus the `result_ids` or `frame_ids` behind it), and `suggested_next_tool`, per the LSS engine's uniform finding contract.

### 4.3 Consumed

`telemetry.reading.v1` (normalized from Sparkplug), `device.registry.state.v1`, `finding.raised.v1`, `twin.state.snapshot.v1`, `whatif.completed.v1`, `genealogy.link.v1`, `order.lifecycle.v1`, `gl.posting.v1`, `sop.document.v1`, `roster.published.v1`, `energy.reading.v1`.

For each consumed type this section declares a consumer contract file at `/schemas/_consumers/twinflow-<pkg>.yaml` listing the exact fields it reads. CI fails when a producer removes or retypes a consumed field within a major version.

---

## 5. Behavior

### 5.1 The answer pipeline

One pipeline serves chat, MCP, voice, eval, and inter-agent questions. The channel changes the surface, never the guarantees.

1. **Admit.** Validate the question envelope, resolve the autonomy tier, reserve a budget from `BudgetLedger`. On refusal, emit `governance.budget.exceeded` and abstain with reason `budget_exhausted`.
2. **Classify and route.** A cheap classifier assigns a `question_class` from the eval taxonomy. The router (E45) picks the cheapest model tier whose recorded eval accuracy for that class clears the policy bar. Before E27 has produced at least `routing.min_history_cases` scored cases for a class, that class has no measured accuracy, so the router selects `routing.cold_start_tier` (the highest-capability tier the policy lists) and records `reason: cold_start`. The router never treats an absent measurement as a passing one. Emit `agent.route.selected`.
3. **Cache probe.** Compute the cache key from the normalized question, the metric selection when it is already determined, the facility config hash, the policy version, and the model tier. The key is qualified by a cache namespace, which is the `run_id` in every deterministic tier and the facility id in a long-lived deployment (see 5.13). A hit is served only when the cached entry's watermark is greater than or equal to the watermark the query requires. Otherwise it is a miss, recorded with `staleness_reject = true`. Emit `agent.cache.lookup`.
4. **Plan.** The model emits a grammar-constrained plan: an ordered list of tool calls and metric selections, decoded against a grammar compiled from the plan's Pydantic schema. Grammar-constrained decoding makes a syntactically malformed plan impossible, which is what constrained decoding guarantees and all it guarantees. Semantic constraints the grammar cannot express (numeric bounds, discriminated unions, cross-field rules) are caught by Pydantic validation, and a rejected plan emits `agent.plan.rejected` and feeds one bounded revalidation retry (E26d, and see 5.3(d) for what each mechanism does and does not cover).
5. **Execute with verification.** Every quantitative step becomes a `CompiledQuery` from the metric layer, or, where no metric fits, generated SQL constrained to the read allowlist. The query runs in the sandbox before anything is written into the answer (E26a, E26c). Failures feed a structured repair message back into the generator for at most `max_repair_retries` attempts. Failure classes are `SqlError`, `EmptyResult`, `ImplausibleMagnitude`, `Timeout`, `PermissionDenied`, `SchemaViolation`.
6. **Self-consistency for hard classes.** For classes flagged `hard` in the routing policy, sample `self_consistency_n` independent query programs using the kernel RNG child seed `agent.accuracy.self_consistency_nonce`, execute all of them, cluster the scalar results with relative tolerance `numeric_cluster_rel_tol`, and take the modal cluster. When no cluster holds a strict majority, the pipeline abstains with reason `no_majority` (E26e). A rubric verifier scores each candidate before the vote.
7. **Compose.** The model writes the answer text with the ledger in context. It is instructed to cite, but the instruction is not the control. The control is step 8.
8. **Ground.** The grounding checker (E26f) segments the answer into sentences, extracts numerals, and matches each against the ledger. Unmatched numerals cause refusal under the default policy. Emit `agent.grounding.checked`.
9. **Abstain or ship.** The abstention policy (E26g) combines self-consistency agreement, rubric score, repair-retry count, and grounding verdict into a decision. Below threshold, the agent states that the twin lacks the data to answer reliably and names what would be needed.
10. **Account and record.** Emit `finops.cost.accrued` per tool and per model call, `agent.answer.emitted`, and, when the turn produced a recommendation at L2 or above, `governance.decision.recorded`.

**Determinism, stated at the strength it holds (D-05).** Two tiers, and this section claims both rather than the stronger one alone. Byte-identical: the same seed, config, cassette, platform, and pinned dependency set produce an identical event-log hash. Value-equivalent: across platforms, the sequence of business events (the ordered tuple of event type, question id, and sim-time rank) is identical, and continuous fields agree within a tolerance derived from measured divergence rather than chosen in advance. The cross-platform job reports the observed maximum divergence and names whether an excess means the tolerance was wrong or a defect exists.

Determinism (C1) holds because every model call goes through `ModelTransport`. That includes the vision-language model in 5.6, the edge SLM in 5.9, the voice pipeline's transcription and synthesis in 5.11, and the cheap classifier in step 2. No package in this repository calls a model provider or a local inference runtime directly, and the nondeterminism gate in `scripts/checks/nondeterminism-gate.sh` fails on an import of a provider SDK or `llama_cpp` outside `twinflow.agent.transport`.

In `replay` mode, the request is hashed over the model id, sampling parameters, and the normalized message list, and the recorded response is returned. CI runs in `replay`. A recording session under `record` mode refreshes cassettes and is committed as a reviewable diff. Sampling for self-consistency draws from the kernel RNG, not from the provider's own randomness, by varying an explicit nonce in the request.

Sim-time cost of a model call is modeled (C2). `transport.latency_model: recorded` replays the latency distribution captured during recording. Replaying a distribution means sampling, so it draws from the kernel RNG child seed `agent.transport.latency`, registered in the stream catalog defined by `docs/design/variability-and-faults.md` section A.2. All three streams this section adds follow that section's `<domain>.<subsystem>.<quantity>` grammar: `agent.accuracy.self_consistency_nonce`, `agent.transport.latency`, and `vision.vlm.sample`. Without that registration the replayed latency would be an unseeded draw and `sim_latency_us` could not enter the hashed log at all. With it, decision latency is a reproducible KPI rather than an artifact of whether the test had network. Wall-clock latency is still recorded, in the profile sidecar, where it informs a human and steers nothing (D-02).

**Scheduling.** Steps 4 through 9 run to completion for one question before the next question in the same session starts. Where several agents are live at once, 5.5 fixes their order. Tool execution is dispatched through the kernel's deterministic scheduler, never through an ambient asyncio event loop, so interleaving cannot vary between runs (D-03, D-04).

### 5.2 The component 7 tools

Nine tools: the seven named by requirement 7, plus `query_metric` and `apply_change`, which this section adds. Each has a Pydantic args model, a Pydantic result model, a tier, a simulation budget where it runs experiments, and a declared side-effect class. Every result model carries `result_ids` so its numbers enter the ledger.

| Tool                    | Args                                                                                                    | Result                                                                                                                                                            | Tier | Side effects | Sim budget  |
|-------------------------|---------------------------------------------------------------------------------------------------------|-------------------------------------------------------------------------------------------------------------------------------------------------------------------|------|--------------|-------------|
| `get_fleet_health`      | `window`, `area?`, `device_type?`, `min_severity?`                                                      | per-device health score, SOD/RPN components, degraded list, MTTD stats                                                                                            | L1   | none         | null        |
| `get_bottleneck`        | `window`, `scope` (one of line, area, site, network), `method` (one of utilization, queue, sensitivity) | ranked stations with utilization, queue length, blocking, starving, and the sensitivity coefficient                                                               | L1   | none         | null        |
| `get_findings`          | `window`, `type?`, `severity_min?`, `subsystem?`, `limit`                                               | paged findings with evidence refs and suggested next tool                                                                                                         | L1   | none         | null        |
| `explain_finding`       | `finding_id`                                                                                            | the rule that fired, the evidence window, the chart state, the SOP clause when one applies, `similar_cases[]` with `memory_status`, and the recommended next tool | L1   | none         | null        |
| `run_capability_report` | `metric`, `window`, `spec_limits?`, `format`                                                            | artifact path plus the headline capability numbers                                                                                                                | L1   | none         | null        |
| `query_metric`          | `MetricSelection`                                                                                       | `QueryResult`                                                                                                                                                     | L1   | none         | null        |
| `run_whatif`            | `config_change` (JSON Patch), `horizon`, `replications`, `seed`, `use_surrogate`                        | before/after `kpi_deltas[]`, the LSS hypothesis-test verdict, effect size, confidence interval                                                                    | L1   | simulate     | per_whatif  |
| `compare_scenarios`     | `candidates[]`, `budget_usd`, `objective`, `replications`, `seed`                                       | ranked investment roadmap                                                                                                                                         | L1   | simulate     | per_compare |
| `apply_change`          | `decision_id`, `alternative_id`                                                                         | applied config version, connector ack                                                                                                                             | L3   | write_config | null        |

**Why the simulate tools are L1.** E5 defines the tiers by authority: L1 advises, L2 recommends with human approval, L3 applies inside guardrails. Running an experiment against a copy of the config changes nothing in the world, so gating it on authority is a category error, and it would put the headline demo behind a flag that the shipped config turns off. What a simulation does consume is compute, which is a budget question, so `run_whatif` and `compare_scenarios` carry a `sim_budget` enforced by `BudgetLedger` and denied on exhaustion. The recommendation a what-if produces still needs L2 to be accepted, and applying it still needs L3. The gate moved from the experiment to the acceptance, which is where E5 put it.

`apply_change` is the tool the source implies through requirement 6 and E5 but never names. It exists behind the L3 gate and is disabled by default. See open question 1.

**Result fields that outrun their producers.** `run_whatif`'s KPI table names deltas whose producing subsystems land later than the tool does: the energy delta needs E7's energy KPIs and the operator-impact delta needs E6's operator model. The field is not dropped and is not silently absent. `kpi_deltas[]` is a list of typed records, each carrying `metric`, `status` (one of `measured`, `awaiting_subsystem`), `value`, `interval`, and `required_by` (the requirement id that will supply it). Before E6 and E7 land, the record for operator utilization is present with `status: awaiting_subsystem` and `required_by: E6`, so a reader of the answer sees what is missing and why. `test_kpi_delta_coverage` asserts that every metric in the roadmap table resolves to a record in one of the two states, never to a missing key and never to a zero. The preferred resolution is resequencing rather than degradation: this section requests that E7's energy KPIs land in Phase 3 with the motor-current sensors that already produce their inputs, and records the request in section 8.

`explain_finding` has the same shape, and it matters more, because the tool lands in Phase 2 while E27's incident memory lands in Phase 6. The result model carries `similar_cases[]` from Phase 2 onward, along with `memory_status`, an enum of `populated`, `empty`, and `awaiting_subsystem`. Before incident memory exists the field is present, the list is empty, and the status reads `awaiting_subsystem` with `required_by: E27`. The schema does not change shape at Phase 6; only the status and the list contents change. That is the difference between a versioned-contract break on a Phase 0 surface and a field whose emptiness is declared, and this section chooses the second.

`use_surrogate` has the same shape. Its default is `false`. When it is `true` and no surrogate model is registered in `twinflow-mlops`, the tool returns `surrogate_status: unavailable` with `required_by: E28` and runs the full simulation, rather than ignoring the flag. Config validation rejects a facility profile that sets `use_surrogate: true` by default while no surrogate is registered.

**`run_whatif`.** Applies the JSON Patch to a copy of the facility config and runs `replications` seeded replications of both the baseline and the variant with common random numbers. The pairing is not assumed. The runner emits the `crn_integrity` record defined in `docs/design/variability-and-faults.md` section A.5, listing per-stream draw counts in both arms, and the LSS engine's assumption checker applies a paired test only when every shared stream's counts match. Otherwise it applies the independent-samples test and says so.

The tool returns the delta, the test name, the statistic, the p-value, the effect size, the confidence interval, and which test was chosen with the reason. The agent is forbidden from computing any of these; it reports what the engine returned. `use_surrogate` runs the E28 surrogate first for a fast screen and always re-runs the returned winner through the full simulation before the number is reported. The result carries `surrogate_status` and `surrogate_error_vs_sim` so the answer can state the confirmation honestly.

**`compare_scenarios`.** Runs each candidate as a `run_whatif`, computes the objective per candidate (default: throughput gained per dollar of assumed cost), applies a multiple-comparison correction across candidates (Holm by default, configurable), and returns an `InvestmentRoadmap` whose columns are:

```
rank, change, capex, delta throughput/day, delta energy/pallet,
delta operator utilization, p, effect size, 95% CI, payback (months),
cost_basis, verdict
```

Rows whose difference is not significant after correction are marked `not distinguishable at this replication count` and carry the replication count needed to reach the configured power. That last column is the part a consulting deliverable usually lacks and is cheap to compute with a standard power calculation.

Three columns depend on subsystems that land after the tool does, and each states its dependency in the row rather than going blank. The energy and operator columns carry the `kpi_deltas` status described above. The payback column carries `cost_basis`, an enum: `capex_and_operating` once the financial twin at 6a17 supplies operating deltas, and `capex_and_rate_card` before that, where the operating cost comes from a config-declared rate card in `facility.yaml` under `finance.rate_card`. The rate card is the minimal cost model, it lands with `compare_scenarios`, and it makes the column honest at Phase 3b instead of empty. `test_roadmap_cost_basis_declared` asserts every roadmap row names its basis, so a reader never sees a payback figure without knowing what produced it.

**Refusal when tools fail.** A tool that raises, times out, or returns a schema-invalid result contributes nothing to the ledger. The pipeline never falls back to model priors. If the question cannot be answered from what did succeed, the agent abstains with reason `tool_failure` and names the tool. This is tested by fault injection over every tool, including partial failure where two of three tools succeed.

### 5.3 E26 layer by layer

E26's README sentence is "here is the architecture and the measured evidence, layer by layer", so the evidence comes first and each layer is then specified against it.

#### 5.3.1 Evidentiary basis for the seven layers

Each row names the published measurement that motivates the layer, the retrieval that verified it, and the gate in section 7 that measures the same property inside this repository. A row whose measurement could not be retrieved from primary text says so and points at the open question that holds it. No row's number is restated anywhere else in this section as an unattributed fact.

| Layer                      | Published measurement                                                                                                                                                                                                                                                     | Verification                                                                                               | Gate here                       |
|----------------------------|---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|------------------------------------------------------------------------------------------------------------|---------------------------------|
| (a) execution grounding    | Gao, Madaan, Zhou, Alon, Liu, Yang, Callan and Neubig, "PAL: Program-aided Language Models", arXiv:2211.10435v2. The abstract states PAL with Codex surpasses PaLM-540B with chain-of-thought on GSM8K by absolute 15% top-1                                              | Abstract page retrieved 2026-08-09, HTTP 200, <https://arxiv.org/abs/2211.10435>                           | VAL-GATE AI-10                  |
| (b) governed metrics layer | The requirements source attributes a 57% to 78% execution-accuracy gain to a Snowflake measurement. The primary text could not be retrieved                                                                                                                               | snowflake.com returned HTTP 403 to a direct request on 2026-08-09. No figure is published here             | VAL-GATE AI-9, open question 15 |
| (c) execution verification | Li, Hui, Qu and 15 others, "Can LLM Already Serve as A Database Interface? A BIg Bench for Large-Scale Database Grounded Text-to-SQLs", arXiv:2305.03111v3 (NeurIPS 2023). The abstract states ChatGPT reaches 40.08% execution accuracy against a human result of 92.96% | Abstract page retrieved 2026-08-09, HTTP 200, <https://arxiv.org/abs/2305.03111>                           | MEAS-AI-8, open question 16     |
| (d) structured outputs     | OpenAI, "Introducing Structured Outputs in the API", 6 August 2024: "our new model gpt-4o-2024-08-06 with Structured Outputs scores a perfect 100%. In comparison, gpt-4-0613 scores less than 40%", on OpenAI's own schema-following eval                                | Page retrieved 2026-08-09, HTTP 200, <https://openai.com/index/introducing-structured-outputs-in-the-api/> | CONF-AI-6                       |
| (d) grammar guarantee      | Willard and Louf, "Efficient Guided Generation for Large Language Models", arXiv:2307.09702v4, which guarantees the structure of generated text for regular expressions and context-free grammars; Dong and others, "XGrammar", arXiv:2411.15100v3, the engine used here  | Both abstract pages retrieved 2026-08-09, HTTP 200                                                         | CONF-AI-6                       |
| (e) self-consistency       | Wang, Wei, Schuurmans, Le, Chi, Narang, Chowdhery and Zhou, "Self-Consistency Improves Chain of Thought Reasoning in Language Models", arXiv:2203.11171v4 (ICLR 2023). The abstract reports GSM8K +17.9%                                                                  | Abstract page retrieved 2026-08-09, HTTP 200, <https://arxiv.org/abs/2203.11171>                           | MEAS-AI-9                       |
| (f) grounding checker      | The requirements source cites a production team measuring source hallucinations falling from 10% to zero, with no publisher named. There is nothing to retrieve                                                                                                           | Not verifiable as written. No figure is published here                                                     | CONF-AI-7, open question 17     |
| (g) calibrated abstention  | El-Yaniv and Wiener, "On the Foundations of Noise-free Selective Classification", Journal of Machine Learning Research 11(53):1605-1641 (2010), the risk-coverage formulation this section implements                                                                     | Article page retrieved 2026-08-09, HTTP 200, <https://www.jmlr.org/papers/v11/el-yaniv10a.html>            | VAL-GATE AI-8                   |

Two consequences follow, and they are the reason this table exists rather than a list of encouraging numbers.

First, the measurements that survived retrieval are about reasoning benchmarks and schema conformance, not about warehouse operations. They justify the shape of the architecture. They do not predict this repository's accuracy, and the README says so beside its own numbers.

Second, the three rows that did not survive retrieval are the three the source leaned on hardest. They are recorded as open questions rather than quietly repeated, which is the same discipline the grounding checker applies to the agent.

#### 5.3.2 The layers

**(a) Execution-grounded answers.** No arithmetic in tokens. The model may emit a metric selection or SQL; it may not emit a computed number. Enforcement is structural, not instructional: the answer composer receives the ledger as the only source of numerals, and the grounding checker at step 8 refuses anything else.

The sandbox is a DuckDB connection in a separate OS process, attached read-only to the Delta tables through `delta_scan`. Its limits come from the `ai.sandbox` config block and nothing is hardcoded (C5): `SET memory_limit` from `memory_limit_mb`, `SET threads` from `threads`, and a deterministic budget of `max_rows_scanned` enforced through the progress callback. The budget replaces the wall-clock statement timeout that an earlier draft specified. A wall timeout makes the result depend on machine speed, and a query that succeeds on a fast runner and is canceled on a slow one produces two different tapes from one seed (D-02). `threads` is pinned to 1 for a second determinism reason: parallel floating-point aggregation sums partitions in completion order, so a multi-threaded `sum` over the same rows can differ in the last bits between runs (D-04).

Extensions are pre-provisioned. DuckDB autoloads and autoinstalls a missing extension over the network on first use, and the sandbox has no network namespace, so a cold container could not open its own Delta tables. The image build bakes the `delta` extension and any other required extension into a directory, and the sandbox opens with `SET extension_directory` pointing at it, `SET autoinstall_known_extensions=false`, and `SET autoload_known_extensions=false`. CONF-AI-13 runs the sandbox against a Delta table with egress blocked and fails if it cannot read.

Generated SQL is parsed with sqlglot before execution and rejected if it contains DDL or DML, references a table outside the allowlist, or uses a function outside the allowlist. The Python path (for analysis a single query cannot express) runs in the same isolated process with an AST allowlist over imports and a ban on `__import__`, `eval`, `exec`, `open`, and dunder attribute access. The AST allowlist is defense in depth. The hard boundary is the process and container: no network namespace, read-only mount, no credentials in the environment. SECURITY.md (C7) states exactly this, including that a determined attacker with SQL execution can read every table in the allowlist, which is why the allowlist excludes any table holding credentials or user content.

**(b) Governed semantic metrics layer.** `metrics.yaml` is a MetricFlow-shaped file defining entities, dimensions, measures, and metrics. The five named by the source (`fill_rate`, `otif`, `oee`, `landed_cost`, `days_of_supply`) are mandatory and land with the subsystems that produce their inputs.

The read allowlist grows with them. An earlier draft fixed the allowlist at seven tables and separately required all five metrics, which is unsatisfiable: `days_of_supply` needs inventory, `oee` needs equipment state, and `landed_cost` needs freight and tariff tables, none of which were listed. The rule is stated the other way round instead. The allowlist is the union of the tables declared by the metrics that have landed, minus a deny-list of tables holding credentials, secrets, or user-supplied content. `metrics.yaml` carries both the derived allowlist and the deny-list, the loader recomputes the union at validation time and fails when the file's copy disagrees, and `test_allowlist_denylist_disjoint` asserts the intersection is empty. That keeps C7's security property, which is about what the sandbox must never reach, while letting the metric catalog grow.

Each of the five names the tables it needs, so the growth is auditable: `fill_rate` needs `orders`; `otif` needs `orders` and `shipments`; `oee` needs `equipment_state` and `production_counts`; `landed_cost` needs `freight_invoices` and `tariff_schedule`; `days_of_supply` needs `inventory_positions` and `demand_history`.

The agent is given the metric catalog, not the raw schema, for any question a metric covers. `MetricLayer.compile` produces the SQL; the model never writes an aggregation over a governed metric's inputs. When no metric fits, the pipeline falls back to constrained free SQL and the answer is tagged `ungoverned_metric`, which the eval harness reports separately so the coverage gap is visible rather than hidden. Adding a metric requires a fixture with a hand-computed expected value (see VAL-GATE AI-9), so the catalog cannot grow faster than its tests.

**(c) Execution-based verification.** Nothing ships unexecuted. `ImplausibleMagnitude` is decided by two sources: the metric's declared `domain` (a fill rate outside 0 to 1 is rejected outright), and, for unbounded metrics, a historical plausibility band computed as the p1 and p99 of the metric's own history widened by a configured factor, with a minimum history requirement before the band is active. Out-of-band values are not discarded; they drive one repair retry, and if the query is unchanged on re-execution the value is reported with an explicit special-cause note and a finding is raised. The repair message contains the exception text, the failing SQL, the relevant schema snippet, and the metric definition. Retries are bounded at two.

**(d) Structured outputs everywhere.** Every tool call, every plan, every metric selection, and every structured answer component is a Pydantic model. Hosted providers get the schema through Pydantic AI's structured output path with validation-retry. Local models get a grammar compiled from the same JSON Schema through XGrammar (default) or Outlines.

The claim is split, because the two mechanisms guarantee different things and conflating them is how a spec overclaims. Grammar-constrained decoding enforces a context-free grammar, so a syntactically malformed plan cannot be produced: no unbalanced braces, no missing required key, no value of the wrong JSON type. It does not enforce the parts of JSON Schema that are not context-free, and this section names them so nobody is surprised in review: numeric `minimum` and `maximum`, `oneOf` and discriminated unions, string `format`, `pattern` beyond what the grammar compiler lowers to a regular expression, and any cross-field validator. Those are enforced by Pydantic validation after decoding, with one bounded retry carrying the validation error back to the generator, and a rejection emits `agent.plan.rejected` with its failure class.

Two measurements follow from the split, and CONF-AI-6 asserts the first while publishing the second. Grammar conformance rate is exactly 1.0 by construction and any failure is a defect in the grammar compiler. Post-validation acceptance rate is a measured number with a published floor and a published failure taxonomy, because a model can emit a grammatically perfect plan that asks for a negative horizon.

One test asserts that the grammar path and the hosted path accept exactly the same set of instances for every tool schema in the registry.

**(e) Self-consistency.** `n = 5` by default, odd, configurable 1 to 11. Programs are sampled, not answers: each sample is a `CompiledQuery` or a plan, all are executed, and the vote is over executed results. `majority_rule: strict` is the default and the release profile refuses anything else, because a plurality winner among five samples can hold two votes and still be reported as consensus. The `plurality` mode remains in the enum for the sensitivity study that open question 3 asks for, and the eval report publishes the abstention-rate and accuracy delta between the two modes so the cost of the strict rule is a measured number rather than an assertion. Clustering uses relative tolerance for continuous values, exact match for identifiers, and rank-correlation clustering for ranked results (two rankings are the same cluster when Kendall's tau exceeds the configured threshold). The rubric verifier scores each candidate on: uses a governed metric where one exists, joins are schema-valid under the catalog, magnitude is inside the plausibility band, the time window matches the question's window, and no unbounded scan. Candidates below the rubric floor are dropped before the vote; if all are dropped the pipeline abstains with reason `verification_failed`.

**(f) Grounding checker.** Sentence segmentation, then numeral extraction covering digits, decimals, thousands separators, percentages, currency symbols and codes, ranges (`12 to 15`), scientific notation, and spelled-out integers up to twenty. Each numeral is normalized to a `(value, unit, magnitude_class)` triple using the surrounding unit tokens, then matched against `LedgerNumeral` entries with relative tolerance `match_rel_tol` (default 0.005, which admits honest rounding and rejects a fabricated third digit).

Four classes of unmatched numeral may be allowed through, each behind its own flag, and the flag set is exactly this list with no fifth member:

| Allowance          | Flag                     | Default | What it admits                                                         |
|--------------------|--------------------------|---------|------------------------------------------------------------------------|
| Question echo      | `allow_question_echo`    | true    | A numeral repeated verbatim from the question's own span               |
| Ordinal list index | `allow_ordinals`         | true    | An ordinal used to number a list item, not to state a quantity         |
| Sim-time timestamp | `allow_timestamp_match`  | true    | A sim-time timestamp inside a ledger record's declared window          |
| Identifier         | `allow_identifier_match` | false   | A device id, finding id, or SOP clause number matching a ledger string |

Everything else fails. `GroundingPolicy.strict()` sets all four to false and is the policy the load-bearing property test runs against. `test_grounding_allowance_set` enumerates `GroundingPolicy.allowances()` and asserts both the member set and the defaults against this table, so prose and config cannot drift apart again. Each allowance that fires is counted in `allowance_hits` on `agent.grounding.checked`, so a deployment can see how often it is leaning on one.

`on_violation: refuse` is the default and the profile CI asserts it; `strip_sentence` and `annotate` exist for interactive debugging and are refused by the release profile check. The checker is a pure function of (answer text, ledger, policy) with no model in the loop, so it is fast, deterministic, and separately installable.

**(g) Calibrated abstention.** Confidence signals are the self-consistency agreement fraction, the rubric score, the repair-retry count, whether every step used a governed metric, and the grounding verdict. Calibration sweeps a threshold over the combined score on the eval suite's calibration split and selects the lowest threshold whose conditional accuracy on answered questions has a Wilson 95% lower bound at or above `target_conditional_accuracy` (0.98) with at least `min_support` answered cases. The resulting `AbstentionPolicy` is a checked-in JSON artifact with the suite version and commit that produced it, so the threshold is reproducible and reviewable. The risk-coverage curve and the area under it are published. Thresholds are fit per question class when a class has enough support and fall back to the global threshold otherwise.

**README metrics.** `just eval` writes `docs/eval/latest.json` and a badge fragment. The README carries eval-suite accuracy, abstention rate, and grounding-checker pass rate, generated by a script. Each number is labeled with six fields, not three: suite version, model tier, seed, transport mode, cassette recording date, and the date of the run that produced it.

The transport label is the honest part. Everything CI runs is `transport.mode: replay` against committed cassettes, so a CI figure measures the pipeline against a frozen model response set. It is reproducible by anyone who clones the repository, and it is not a live measurement of a current hosted model. A scheduled `record`-mode refresh job re-records the cassettes, and its diff is reviewed like any other change, which is what dates the evidence. The README limitations section states the distinction in one sentence: CI reproduces the number, and the recording session produces it. A CI job fails when the README numbers differ from the latest committed eval artifact, so the published numbers cannot drift from the artifact, and the artifact cannot drift from its own provenance.

### 5.4 E2, the MCP server

`twinflow-mcp` wraps `ToolRegistry`. Tool JSON Schemas are generated from the same Pydantic models the in-process agent uses, so there is exactly one definition of every tool. Equality between the advertised schema and the registry schema is asserted after canonicalization, not on raw bytes: both sides are serialized through the JSON Canonicalization Scheme of RFC 8785 with `$ref` resolved and `$defs` inlined, and the canonical forms are compared byte for byte. A raw byte comparison would fail on a key-ordering change in a dependency rather than on a real contract drift, which is a gate that cries wolf. Transports: stdio (default, for Claude Desktop) and streamable HTTP (for remote clients). The server also exposes MCP resources and prompts:

- Resources: `twinflow://findings/{id}`, `twinflow://run/{run_id}/transcript`, `twinflow://sop/{clause}`, `twinflow://metrics/catalog`, `twinflow://facility/config`.
- Prompts: `shift_handover`, `investigate_finding`, `investment_roadmap`.

README one-liner:

```json
{
  "mcpServers": {
    "twinflow": {
      "command": "uvx",
      "args": ["twinflow-mcp", "--facility", "./configs/facility.yaml"]
    }
  }
}
```

Security posture for the MCP surface, documented in SECURITY.md per C7. Read tools and simulate tools are available at the shipped defaults, because neither changes anything outside the run and the headline demo is a simulate tool. Simulate tools are bounded by `sim_budget`, and an exhausted budget is a denial, not a queue. `apply_change` requires `--allow-write` plus an autonomy tier of L3 in the facility config, and even then writes go through the decision register. All resource content returned to a client is wrapped in a data envelope and marked tainted, because an MCP client is an untrusted caller and the content it reads is untrusted data. The threat-model note states what a malicious client can reach (every table in the read allowlist, every finding, the facility config) and what it cannot (the host filesystem, the network, credentials, any table outside the allowlist).

### 5.5 E21, collaborative multi-agent system with decision governance

Role agents: `planner`, `expediter`, `maintenance`, `transport_buyer`, plus `supervisor`. Each role is the same `Agent` class with a different tool allowlist, a different objective, and its own budget. Roles do not share a context window; they share state through the tool layer, which means their common ground is executed query results, not narrative.

**Transport, and the divergence from the source.** The source says role agents negotiate "over shared MCP state". This section runs the negotiation over an internal bus, which is faster and replayable, and it does not pretend the two readings are the same: see open question 4 before reading further. The compromise is concrete rather than rhetorical. Every `Proposal` and every `Critique` is serialized through the same MCP resource schemas an external client would receive, and the transcript is exposed at `twinflow://negotiation/{task_id}`. `e2e_mcp_negotiation_transcript` starts a scripted external MCP client and asserts it can read the full negotiation transcript, every round, from that resource. Both readings are then satisfied at the observable surface, and the divergence is confined to the wire between two in-process agents.

**Scheduling, which is what makes the negotiation deterministic.** Within a negotiation phase, role agents execute in a fixed order: the ascending sort of their role ids, computed once and recorded as `order_index` on `governance.negotiation.round`. No phase runs roles concurrently and no phase depends on which agent finishes first. Every tool call inside a role's turn is dispatched through the kernel's deterministic scheduler, never through an ambient asyncio event loop, and no collection whose iteration order could reach an event is a Python set (D-03, D-04). This matters because `result_id` is a run-global monotone counter: under a concurrent scheduler, two roles racing to record results would swap ledger ids between runs and change the log hash without changing a single decision. The rule is a Phase 0 contract line in section 8, because it is exactly the kind of thing that cannot be retrofitted once four role agents are written against an async runtime.

**Negotiation protocol.** A Contract Net Protocol variant (FIPA Contract Net, a published interaction protocol, which gives the implementation a named reference rather than an invented dance):

1. `announce`: the supervisor publishes a `NegotiationTask` (typically an S&OE exception from E15, a disruption, or an S&OP gap) with the objective, the hard constraints, and the total budget.
2. `bid`: each role runs its own answer pipeline over its own tools and submits a `Proposal` (config delta, projected effect per metric with intervals, cost, its own confidence, and the `result_ids` behind every number). Proposals go through the grounding checker exactly as user answers do. An ungrounded proposal is rejected before the supervisor sees it.
3. `critique`: roles see one another's proposals as data and may submit a `Critique` naming a constraint the proposal violates, with evidence.
4. `revise`: bounded revision rounds.
5. `award`: the supervisor scores surviving proposals against the objective, checks budget feasibility, and awards. Ties break by the objective's secondary key, then by proposal id, so the outcome is deterministic.

Termination: `LoopControl.max_rounds` (default 3), budget exhaustion, or no score improvement for `LoopControl.patience` rounds. Deadlock, defined as no feasible proposal after `max_rounds`, escalates to a human with the full proposal set attached. Every phase emits `governance.negotiation.round`.

**Budgets.** `BudgetLedger` holds the total; roles reserve before spending and settle after. Reservations are componentwise over the five `Budget` components: usd, tokens, tool calls, sim seconds, and sandbox rows scanned. Round and patience limits are `LoopControl` and are not budget components, so `per_negotiation` in the config carries a complete `Budget` next to a `LoopControl` rather than mixing the two shapes. Over-reservation is denied, not throttled, and denial is an event. The supervisor may reallocate unspent reservations between rounds, and reallocation is itself a `governance.budget.reserved` pair so the ledger identity in property 6 holds across it.

**Decision register.** Every award, every L2 recommendation accepted by a human, and every L3 auto-applied change writes a `DecisionRecord` with its alternatives, its inputs as `result_ids`, its authority tier, the model versions and policy version in force, and the seed. Records are hash-chained; `verify_chain()` is a CI job on the demo run. Outcomes are backfilled by a separate appended record once the twin has observed enough to measure them, and the variance between expected and actual goes to the LSS engine, which decides whether it is common cause or assignable. An assignable variance becomes a `governance.decision_outcome_variance` finding, which is how the system grades its own decisions.

**Counterfactual audit.** `replay_counterfactual(decision_id, alternative_id)` reconstructs the twin's state from the event log at the decision's sim time (E4), applies the alternative instead of the chosen option, and runs forward with the same seed family. It reports the realized objective under both branches. This is what makes the register auditable rather than decorative: an auditor can ask what the road not taken would have produced, and get a number with the same statistical treatment as the original.

### 5.6 Component 4, computer vision auditing

**Frames, and where this section's boundary sits.** The renderer produces a top-down orthographic view at a configurable rate (default 1 Hz) from the same state that drives the dashboard, using the kernel RNG for any stochastic rendering, so frames are reproducible from a seed. The raw render is the only part of the chain this section does not own, and open question 8 asks who does. Everything after ingest is owned here and is specified so that the unowned part is a single narrow seam rather than a dependency spread across Phase 4.

The seam: the producer emits `vision.frame.captured.v1` carrying `frame_id`, `camera_id`, `path`, `render_seed`, and `sim_time`, and nothing else is required of it. Degradation runs inside `twinflow-vision` on the ingested frame, not in the renderer. Truth annotations are also produced inside `twinflow-vision`, by joining `twin.state.snapshot.v1` on the frame's `sim_time` and projecting entity positions through the same camera model the renderer declares in the event. A consumer contract file pins those five fields, so a renderer change that drops one fails CI rather than silently producing unlabelled frames.

Every frame is watermarked `SYNTHETIC` in the corner and every exported dataset card repeats it.

**Degradation.** Frames pass through a configurable degradation stage: Gaussian blur, JPEG artifacts, lighting variation, partial occlusion, motion blur proportional to object speed, and dropped frames. This exists for a specific reason: a perfect detector makes the audit logic untestable, because reconciliation between two systems that never disagree proves nothing. The degradation level is a config knob, and the test suite runs the audit at a level where the detector's error rate is non-zero and known.

**Detectors.** Two, both registered as models in `twinflow-mlops`:

- `ColorBlobDetector`: deterministic OpenCV pipeline (color thresholding per class, morphological opening, connected components, centroid tracking with a Hungarian assignment across frames). No training, no weights, runs anywhere.
- `TinyDetector`: a small trained detector fitted on the exported labeled frames, for the honest comparison.

The README says plainly that detection on synthetic frames is easy, and the repo proves it by publishing both detectors' precision and recall at several degradation levels. The interesting part is what follows.

**Job 1: SOP compliance auditing.** `SOPRule` predicates are declarative and versioned, written over zones, classes, tracks, and activity sequence: a pallet staged in a zone not permitted for its lot, a scan step skipped between two observed activities, a forklift in a pedestrian-only aisle, PPE absent in a zone that requires it (landing with 6a10), dwell exceeding a zone's limit. Every rule names the SOP clause it enforces by path anchor, and the emitted violation carries the clause text (E8). A citation-integrity test asserts every `rule_id` resolves to an existing clause anchor and that the quoted text matches the file, so a renamed clause breaks CI rather than producing a confidently wrong citation.

**Job 2: independent throughput counting.** A line-crossing counter over tracked objects at each portal's virtual line produces a CV count per window. The RFID layer produces its own count. The twin knows the truth. The reconciliation record carries all three. The audit logic:

- Disagreement between CV and RFID beyond the control limit on a p-chart of disagreement rate is a `vision.sensor_disagreement` finding. Neither channel is assumed correct.
- The finding's `explain_finding` output names the likely side by comparing each channel against its own historical accuracy profile, and, once E46 lands, distinguishes a read-zone physics problem from a device problem using read-rate-by-portal signatures.
- Agreement between the two channels is scored as an attribute agreement analysis with Cohen's kappa, because two measurement systems disagreeing about a count is a measurement system problem before it is a process problem. This is the CV channel's link into the LSS engine's MSA layer.

**E29, the VLM copilot.** A vision-language model watches the same frames, answers open questions ("why is dock 3 backed up?"), and writes shift-change summaries. Two hard rules keep it inside the accuracy stack. The VLM may describe what it sees, but any number in its output goes through the same grounding checker, which means it must call tools to quantify anything it claims. Its structured event claims (`claimed_events[]`) are scored against the classical channel and against sim truth on the same frames. Every VLM call goes through `ModelTransport` like every other model call, so `vision.vlm.observation` is reproducible in replay and the event records its `transport_mode`.

**The comparison protocol, fixed here rather than left open.** A benchmark table between a deterministic detector and a sampled model is meaningless without a stated protocol, so this is it. The frame set is a fixed seeded scenario's frames at a named degradation level, listed by `frame_id` in `configs/vision_bench.yaml`. The classical channel runs once, because it is deterministic. The VLM runs at temperature 0 with `n = 5` samples per frame, drawing its nonce from the kernel RNG child seed `vision.vlm.sample`, through `ModelTransport` in replay.

The table reports, per event class: precision, recall, and F1 as the mean over the five samples with the standard deviation beside each, sim latency from the modeled transport, and cost per frame from the price book. Sample count, temperature, seed, degradation level, and cassette date are printed in the table header, so the table can be regenerated exactly. Open question 7 now holds only the remaining unknown, which is which VLM runs locally at an acceptable frame rate on CPU. If the classical channel wins, the table says so, which is the more useful result for the reader.

### 5.7 E30, causal inference with ground-truth validation

**Graph.** `causal_graph.yaml` declares nodes (observable variables from the historian and the twin), edges, and unobserved confounders. The ground-truth graph is not hand-written twice. Sim processes declare their reads and writes through a `@causal_edge(reads=..., writes=...)` decorator, and a generator emits the true DAG from those declarations. This removes the circularity of grading discovery against a graph someone drew from memory.

**The decorator is a Phase 0 contract, not a Phase 6 one.** E30 lands before 6a16, but the declarations it reads are written by every sim process from Phase 1 onward. A decorator introduced at Phase 6 would have to be retrofitted onto every process class written in the five phases before it, and a process that nobody remembered to annotate deletes a true edge from the ground-truth DAG and inflates the discovery score in the direction that flatters the repository. That is the same argument this section uses for `ResultLedger` and `ModelTransport`, so it gets the same answer: `@causal_edge` is in the Phase 0 contract list in section 8, its decorator and registry are owned jointly with the kernel section, and `test_every_sim_process_declares_causal_edges` fails CI on any subclass of the kernel process base that carries no declaration. A process with genuinely no causal reads or writes declares `@causal_edge(reads=(), writes=())` explicitly, so silence is never the same as an empty declaration.

The residual risk is a wrong declaration rather than a missing one, mitigated by a test that intervening on a declared non-parent produces no detectable effect at the configured power. That test's power is finite and open question 11 asks how much is enough.

**Pipeline.** DoWhy's four steps, kept explicit in the API: `model` (graph plus data), `identify` (backdoor, frontdoor, instrumental variable, with the identified estimand recorded), `estimate` (EconML: linear DML, causal forest DML, the DR learner, which is augmented inverse-propensity weighting, plus propensity-score matching as a baseline), `refute` (placebo treatment, random common cause, data subset removal, add unobserved common cause). All four steps are recorded in `causal.estimate.published`.

**Ground-truth validation, the part only a simulation owner can do.**

- _Effect recovery._ The twin computes the true interventional effect by running the do-operation directly: same seed family, common random numbers, treatment forced. The estimator's answer is compared with that truth. Reported: absolute error, relative error, and, across N seeds, the empirical coverage of the estimator's 95% interval.
- _Structure recovery._ Discovery algorithms (PC, GES, LiNGAM, NOTEARS via causal-learn) run on observational twin data and are scored against the generated true DAG with structural Hamming distance, edge precision and recall, and orientation accuracy on the comparable subset, as a function of sample size. The table is published whichever way it comes out, because "discovery recovered 61% of edges at 50k samples and confused these three" is a more credible result than a claim of success.

E30 lands before 6a16 because the marketing layer's promotion-effect measurement is the textbook confounded case and must not be built on correlation.

### 5.8 E31, forecasting bakeoff and conformal calibration

**Arena.** Entrants: `SeasonalNaive` (the MASE denominator), `AutoETS`, `AutoARIMA`, `AutoTheta` (statsforecast), a gradient-boosted learned model with calendar, promo, and price features, and the foundation-model challengers (Chronos-2 class, TimesFM class) under the `[fm]` extra so a default install stays light.

**Protocol.** Rolling-origin backtest with a fixed origin schedule, fixed horizons, and a fixed seed. Metrics: MASE, WAPE, sMAPE, and bias, per series and aggregated.

Ranking is not a leaderboard by mean error alone. Entrants are compared with a Friedman test across series followed by a Nemenyi post-hoc, and pairwise claims use a Diebold-Mariano test on the loss differential. Only differences that survive are called differences. This is the same statistical discipline the LSS engine applies to the shop floor, applied to model selection.

**Conformal.** The winner is wrapped in split conformal prediction (and conformalized quantile regression when the winner emits quantiles). For non-stationary series, adaptive conformal inference adjusts alpha online. The inventory optimizer consumes the interval, not the point, which is the whole reason this exists. Coverage is measured on the holdout and, once live, on rolling windows, and plotted on a control chart with the nominal 1 minus alpha as the centerline (the source's explicit requirement). A coverage breach becomes a `forecast.interval_coverage_breach` finding.

Ownership boundary: this package owns model adapters, the backtest protocol, the ranking tests, the conformal wrappers, and the coverage chart feed. The planning section owns the demand signal, the promo calendar feature contract, and the inventory policy that consumes intervals. The seam is `forecast.published.v1`.

### 5.9 E32, the plant-distilled edge SLM

**Corpus.** E32 says the corpus comes from twin traces and docs, so it has two halves and both are specified.

The trace half: the eval-case generator produces questions whose answers the simulation computes exactly, and the tool-use traces come from the deterministic pipeline's own recorded plans.

The document half, which an earlier draft dropped: the SOP corpus in `sop/*.md`, `ARCHITECTURE.md`, and the reference pages under `docs/references/` are chunked by heading anchor and turned into question and answer pairs whose answer is a quotation plus its clause anchor. This half is what teaches the SLM the E8 clause-citation behavior that every channel is required to support, and without it the air-gapped model can retrieve a clause but cannot cite one in the shape the citation-integrity test expects. Generated pairs are checked by the same citation-integrity test the CV rules use: the anchor must resolve and the quoted text must match the file, so a renamed clause invalidates the training pair rather than teaching a wrong citation. The corpus manifest records, per pair, its source file, its anchor, and the commit it was drawn from.

The teacher is the plant, not another vendor's model. That choice is deliberate: it sidesteps any provider terms-of-service question about training on model outputs, and it produces training targets that are correct by construction rather than correct-looking. An optional hosted-teacher variant exists behind a flag and is documented as off by default with the reasoning stated.

**Training.** LoRA fine-tune of a small permissively licensed open model (Qwen3-class 1.7B or 4B, or Llama-3.2-3B class), export to GGUF, serve with llama.cpp. The adapter's license and the base model's license are recorded in the model card and checked against the Apache-2.0-compatible allowlist (C11).

**Artifact distribution.** No model weight file is committed to the repository, and no build step silently downloads one. Both the Phase 1 stock model and the distilled model ship as GitHub release assets. `just fetch-models` downloads them, verifies the SHA-256 recorded in the model registry, and writes them under `models/`. The path is git-ignored. `configs/models.lock` carries, per artifact, its file name, size in bytes, SHA-256, source release tag, and license, and the C11 license job reads that file, so a base model or adapter with an incompatible license fails the same gate that a Python dependency does. CI obtains the artifact once in a preparation job with network access, caches it, and mounts the cache into the egress-blocked container that CONF-AI-14 runs, so the air-gap test never needs a network of its own. A clone with no network can still run everything in `transport.mode: replay`, because replay reads cassettes and never loads a model.

**Deployment.** Tier 1 in the E36 compute-placement table: the edge gateway, on the OT segment, with no route to the internet. Constrained decoding via XGrammar keeps E26(d) true locally, so tool calls from the SLM are as schema-safe as from the hosted model.

**Benchmark.** The same eval suite, the same grounding checker, the same abstention policy calibrated separately for the SLM. Published per question class: accuracy, abstention rate, grounding pass rate, p50 and p95 latency, and cost. The expected and honest result is that the SLM matches on lookup and metric classes and loses on multi-hop and what-if classes, which is exactly what the E45 router then exploits.

**Air-gap proof.** A CI job runs the SLM path in a container with egress blocked and asserts the suite completes. An air-gap claim without that test is a slogan.

### 5.10 E33, GNN for disruption propagation

**Graph.** Nodes are suppliers (by tier), facilities, and customer regions; edges are lanes and supply relationships. Node features: capacity, inventory cover in days, criticality, single-source flag, echelon. Edge features: volume, mode, transit-time mean and variance, contractual flexibility.

**Task.** Given a seed disruption (node down for d days, or lane capacity cut by x%), predict per node whether service breaches its threshold within horizon H, and the time to impact. Model: a relational GNN (R-GCN or GAT over typed edges) in PyTorch Geometric.

**Training data and the generalization test.** Scenarios are sampled and run through the simulation, which labels the truth. The split is by topology family, not by scenario: train on one family of generated network topologies, test on another. A random scenario split would measure memorization. Baselines: a reachability-plus-buffer heuristic (how many days of cover sit between the disruption and the node), and the E20 reverse-stress-test optimizer viewed as the complementary lens. The published comparison names when the heuristic wins.

**The point the source cares about.** Hidden tier-2 concentration (E19) produces correlated tier-1 failures that no scorecard predicts. The GNN's value is measured specifically on those cases: accuracy on scenarios where the true cause is a shared hidden tier-2 node, versus scenarios with independent failures.

### 5.11 E34, local voice interface

Pipeline: VAD, then local STT (faster-whisper, base.en by default), then the same answer pipeline, then the grounding checker on the text, then local TTS (Piper). Nothing leaves the machine. Voice-specific behavior: answers are rendered in a short spoken form with the same `result_ids` logged; any L2 or L3 action requires a spoken confirmation and a repeated read-back of the change; a stated latency budget with measured p50 and p95 per stage published in the docs. The 30-second clip in the replay viewer is generated by a script from a seeded transcript, not recorded by hand, so it regenerates when the agent changes.

Testing uses TTS-generated audio fixtures from eval-case questions fed through STT, with an assertion on intent-parse accuracy and a word-error-rate gate on a fixed fixture set. Model-dependent tests are a separate tier gated by `just test-models` and run nightly, not on every push.

### 5.12 E43, MLOps for the twin's own models

**Registry and lineage.** Every model produced anywhere in the repo (PdM trend models, the forecaster, the CV detectors, the surrogate, the AMR dispatcher, the SLM, the cascade GNN, the router) registers a `ModelRecord`. Lineage is a graph: dataset card, feature spec, training run, model, deployment, prediction batch. `twinflow-mlops lineage <model_id>` prints the chain and `twinflow-mlops why <prediction_id>` walks back from a prediction to the data that trained the model that made it.

**Drift.** Monitors on inputs (PSI, KS, Wasserstein per feature), predictions, and residuals. Every monitor's statistic is fed to the LSS engine as a metric with its own control chart, because model drift is a process shift and gets treated like one. A signaled chart raises a `mlops.model_drift` finding with the standard severity and evidence.

**Champion-challenger.** A challenger is deployed in shadow: it scores the same live inputs, its outputs are logged, and nothing downstream consumes them. Promotion requires a `ShadowComparison` with a minimum sample size, a paired test chosen by the LSS engine's assumption checker, a p-value under alpha, and an effect size over a floor. Promotion also requires an approved `DecisionRecord` in the governance register. Rollback is an atomic pointer swap plus a test that asserts the restored champion reproduces byte-identical predictions on a fixture batch.

**Retraining triggers.** Drift severity above a threshold, a performance SLO breach, or a schedule. A trigger creates a `mlops.retrain.requested` event and a pending decision in the register. Human approval is required at L1 and L2; at L3 the retraining runs automatically inside declared guardrails and still writes the decision.

**AI red-team suite.** A versioned corpus of attacks, run in CI beside the accuracy evals. Attack surfaces, all of which exist because the system reads content it did not write:

| Surface          | Example payload location                               |
|------------------|--------------------------------------------------------|
| Device name      | the operator-facing name field on `device.registry`    |
| SOP document     | a clause in `sop/*.md`                                 |
| Supplier record  | supplier name, notes, certificate text                 |
| Finding evidence | free-text evidence on an ingested finding              |
| MCP resource     | content returned to or supplied by an MCP client       |
| Frame placard    | text rendered into a synthetic frame, read by the VLM  |
| Incident memory  | a poisoned case written by an earlier compromised turn |

Attack families: indirect instruction injection, tool-permission escalation (persuading the agent to call an L3 tool from an L1 session), exfiltration (getting secrets or out-of-scope data into an answer or a tool argument), scope escape (querying outside the allowlist), budget exhaustion, and memory poisoning.

Defenses, each individually testable: retrieved content is wrapped in a data envelope and never concatenated into a system-prompt slot, with a structural test on the assembled prompt; every field originating from a writable source carries a `tainted` flag, and tainted content can never authorize a tool call above L1; the tool allowlist is enforced by the registry, not by the prompt; arguments are schema-validated (E26d); the answer passes an egress filter for secret-shaped strings; the grounding checker means an injected number cannot become a reported number; the supervisor budget caps loops. `redteam.attack.attempted` records which defense fired, which is more useful than a pass count because it shows whether the defense in depth is layered.

The published claim is bounded and states what it is a claim about: no attack in the sealed suite succeeds at the pinned commit. That is a statement about the corpus, not about the system, so it is a conformance gate (CONF-AI-15) and not a validation gate, and it never appears beside a statistically validated number as though it were one. The informative number beside it is the defense-firing distribution from `redteam.attack.attempted`: how often each defense was the one that stopped an attack, and how many attacks were stopped by more than one. A corpus where every block comes from a single defense is a corpus that has not tested the depth. The README does not claim prompt injection is solved, and new attacks are an invited issue type.

### 5.13 E45, AI FinOps

**Price book.** `model_prices.yaml`: per model id, input, output, and cached-input prices with a `quoted_on` date and a `source_url`. Versioned, and never described as live pricing. Costs computed from it are `usd_modeled`.

**Router.** `routing_policy.yaml` maps question class to an ordered list of model tiers with the minimum recorded eval accuracy required for that class. Those accuracy figures come from E27's per-class history, which does not exist when the router first ships, so the policy carries `cold_start_tier` and `min_history_cases` and the router uses the cold-start tier for any class with too little history, recording `reason: cold_start`. The policy file also carries `measured_from_suite_version`, and validation fails when that version is absent from the eval artifact history, so a policy can never claim a measurement that was never taken. The router picks the cheapest tier that clears the bar, with an escalation rule: if the pipeline abstains or the rubric floor is missed at a cheap tier, escalate once to the next tier and record the escalation. The policy itself is evaluated: `twinflow-finops evaluate-routing` reports percent routed down, accuracy retained against an all-frontier baseline, dollars saved, escalation rate, and a regret metric (accuracy lost per dollar saved). That table is published, because a routing policy nobody measured is a guess.

**Accounting.** `finops.cost.accrued` per model call and per tool call, tagged with subsystem and question class. Derived unit economics: cost per answered question, cost per finding triaged, cost per what-if, cost per eval run. Each is a metric in the semantic layer and each goes on an I-MR chart in the LSS engine, so a cost excursion is a finding like any other.

**Cache.** Two layers: provider prompt-prefix caching (measured hit rate from usage fields, modeled in replay), and a semantic answer cache keyed by normalized question plus config hash plus policy version plus model tier.

The correctness rule that makes the cache safe: an entry stores the per-table watermark its answer depended on, and a hit is only served when every required watermark is still satisfied. A cache can never serve a number that predates data the question would now see.

The determinism rule that makes the cache replayable: the cache key is qualified by a namespace, and in every deterministic tier the namespace is the `run_id`. A run starts with an empty cache and can only hit entries it wrote itself, so the hit and miss sequence is a function of the seed and the config, exactly like every other control decision. A long-lived deployment sets the namespace to the facility id and gets a durable cache, and it accepts that its hit sequence is history-dependent; that mode is refused by the release-profile check for any run that also claims a determinism hash. Eviction is deterministic too: least recently used, ranked by the ledger sequence number of the last hit, with `result_id` as the tie-break, never by wall-clock timestamp. Each eviction emits `agent.cache.evicted` with its rank and reason, so the eviction order is in the tape rather than inferred.

Hit rates are published; staleness rejections are counted separately so a high hit rate cannot hide a stale one.

**AI P&L.** Monthly rollup posts to the general ledger through the financial twin (6a17) as an operating expense with cost centers by subsystem, sourced from `finops.cost.accrued`. `finops.pnl.posted` carries the source event ids so a line in the P&L drills back to the questions that caused it, which is the same drill-down discipline 6a17 applies to physical variances.

### 5.14 E27, the eval harness and incident memory

**Ground truth from the simulation.** The twin knows the true bottleneck, the true throughput, the true effect of a change, the true causal parent, and which questions its data cannot answer. The case generator produces cases in eight classes (lookup, metric, multi-hop, whatif, causal, ranking, abstain-required, adversarial) with the truth computed by direct query of sim state rather than by an LLM. Abstain-required cases are generated by deleting or windowing out the data a question needs, which is how the abstention rate becomes measurable rather than asserted.

**Scoring.** Scalars: relative tolerance per case, unit-aware. Rankings: Kendall tau against the true ordering, plus top-1 accuracy. Sets: F1. Abstention: correct abstention counts as correct, wrong abstention counts as a miss and is reported separately so over-refusal is visible. Free text: a rubric checked by a verifier plus the grounding checker's verdict, never a model-graded vibe score alone.

**CI integration, and where it narrows the requirement.** E27 says the suite is scored on every change, like unit tests for intelligence. Scoring several hundred cases on every push to a documentation file is waste, so the cadence is path-filtered rather than uniformly reduced, and the narrowing is stated here rather than left for a reader to discover.

- Every push runs the fast subset (`evals.fast_subset_size`, default 40 cases, stratified across the eight classes) in `replay` transport with a fixed seed, at no cost.
- Every push that touches `twinflow-accuracy`, `twinflow-agent`, `twinflow-semantics`, `twinflow-evals`, `twinflow-finops`, or any file under `configs/evals/` runs the full suite. Those are the paths that can move accuracy, so a change to intelligence is scored like a unit test, which is the requirement's actual intent.
- The full suite also runs nightly and on release, which catches a change that moves accuracy from outside the filtered paths.
- The path filter lives in `configs/evals/scoring_paths.yaml`, and `test_scoring_paths_cover_ai_packages` asserts every distribution listed in section 2 is either in the filter or explicitly listed as accuracy-neutral with a reason. A new package cannot quietly escape scoring.

`eval.run.completed` events feed the improvement curve, and each carries its transport mode and cassette date so a curve point is never compared against a point recorded against different cassettes.

**Incident memory.** Resolved findings become `IncidentCase` records. Retrieval combines a structured filter (finding type, subsystem, equipment class) with vector similarity over an evidence embedding, using DuckDB's vector similarity functions so no extra service is required. Retrieved cases are offered to `explain_finding` as prior art, and any resolution the agent proposes from memory is validated by the LSS engine's hypothesis test against the current data before it is recommended. Memory suggests; statistics decides.

**Improvement curve.** `twinflow-evals curve` plots eval accuracy and mean time to a correct recommendation against the number of cases in memory, with bootstrap confidence bands, regenerated from the event log by a script and published in the docs. Leakage guard: eval seeds and memory seeds come from disjoint families, asserted by a test, otherwise the curve measures memorization.

### 5.15 E25, synthetic data products and dataset cards

Exports, each produced by the subsystem that owns the data and packaged by `twinflow-datasets`:

| Dataset                                          | Format                    | Ground truth included                                        |
|--------------------------------------------------|---------------------------|--------------------------------------------------------------|
| Process-mining event log with injected anomalies | XES, OCEL 2.0, Parquet    | the designed process model and the injected deviation labels |
| PdM time series with fault labels                | Parquet plus label file   | fault onset time, fault class, RUL                           |
| CV frames                                        | PNG plus COCO annotations | object boxes, classes, tracks, SOP violation labels          |
| Scenario corpus for RL curricula                 | JSONL specs plus seeds    | scenario outcome under the baseline policy                   |
| Agent eval sets                                  | YAML plus JSON            | answers, with provenance of how each was computed            |
| Causal benchmark bundle                          | Parquet plus DAG JSON     | the true DAG and the true interventional effects             |

The process-mining export is produced against twinflow's own miner, not against PM4Py. PM4Py and `pm4pyminimal` are AGPL-3.0, verified from the package index at version 2.7.23.3, and AGPL section 13 reaches a served dashboard, MCP server, and HTTP API, so importing either would place the whole work under AGPL and break the Apache-2.0 and commercial dual license (D-14). `twinflow-procmine` is written here under Apache-2.0 and owns the discovery, conformance, and variant analysis the export's ground-truth labels are checked against. PM4Py stays available as a development-only oracle, compared against in CI without being distributed or served. The dataset card names the miner and its version, so a consumer of the exported log knows which implementation labeled it.

**Dataset card.** Structured on the published "Datasheets for Datasets" questionnaire (Gebru et al.) rendered as markdown with a machine-readable front matter block: motivation, composition, generation process (twinflow version, code commit, facility profile, config hash, seed, generation command), preprocessing, recommended uses, out-of-scope uses, distribution and license, maintenance, and a limitations section that opens by stating the data is entirely synthetic. Model and dataset licenses are recorded here and checked by the C11 license job.

Reproducibility gate: the card records the row count and SHA-256 of every file; a test regenerates the dataset from the recorded seed and command and asserts the hashes match, which is C1's determinism claim applied to the data product.

---

## 6. Configuration

Every file below validates against a JSON Schema in `/schemas/config/` at load, with line-numbered errors produced by parsing with `ruamel.yaml` round-trip mode and a suggestion engine that offers the closest valid key by edit distance (C5). `just validate` and `--dry-run` cover all of them.

### 6.1 `facility.yaml`, the `ai:` block

```yaml
ai:
  providers:
    default: local # enum: local | hosted; local so the demo runs with no API key
    local:
      backend: llama_cpp # enum: llama_cpp | ollama
      model_id: stock-small-instruct-q4 # key in configs/models.lock; the E32 model replaces it
      model_path: models/stock-small-instruct-q4.gguf # path, must exist unless transport.mode == replay
      context_window: 32768 # int, >= 8192
      grammar_backend: xgrammar # enum: xgrammar | outlines
    hosted:
      enabled: false # bool; true requires env TWINFLOW_LLM_API_KEY
      vendor: anthropic # enum: anthropic | openai | google
      model: <model-id> # str, must be a key in model_prices.yaml
  transport:
    mode: replay # enum: live | record | replay; CI pins replay
    cassette_dir: tests/cassettes/agent # path
    latency_model: recorded # enum: zero | fixed | recorded; recorded draws from agent.transport.latency
  sandbox:
    memory_limit_mb: 2048 # int, 256..16384; passed to SET memory_limit
    threads: 1 # int, fixed at 1; parallel float aggregation is order-dependent (D-04)
    max_rows_scanned: 50000000 # int; the deterministic budget that replaces a wall-clock timeout
    max_result_rows: 5000 # int, 1..100000
    extension_dir: /opt/duckdb/extensions # path baked at image build; autoinstall and autoload are off
  accuracy:
    self_consistency_n: 5 # int, odd, 1..11
    majority_rule: strict # enum: strict | plurality; plurality is refused by the release profile
    numeric_cluster_rel_tol: 0.005 # float, 0 < x < 0.1
    rank_cluster_tau: 0.8 # float, 0..1
    max_repair_retries: 2 # int, 0..3
    rubric_floor: 0.75 # float, 0..1
    plausibility:
      history_min_points: 200 # int
      widen_factor: 1.5 # float, >= 1.0
    grounding:
      enabled: true # bool; false is refused by the release profile check
      match_rel_tol: 0.005 # float
      allow_question_echo: true # bool
      allow_ordinals: true # bool
      allow_timestamp_match: true # bool
      allow_identifier_match: false # bool
      on_violation: refuse # enum: refuse | strip_sentence | annotate
      policy_version: 1 # int, recorded on every verdict
    abstention:
      policy_file: configs/abstention_policy.json # path, produced by calibration, committed
      target_conditional_accuracy: 0.98 # float, 0.5..1.0
      min_support: 30 # int
      per_class: true # bool
  autonomy:
    default_tier: L1 # enum: L1 | L2 | L3
    allow_write_tools: false # bool; true requires default_tier == L3
    elevation:
      max_grant_questions: 20 # int, 1..200; a grant expires after this many questions
      max_grant_sim_seconds: 3600 # int; or at this sim-time age, whichever comes first
      require_named_scope: true # bool; a grant lists tools, never a wildcard
  budgets:
    # Every budget key deserializes into a complete Budget: five components, no loop control.
    per_question:
      { usd: 0.25, tokens: 120000, tool_calls: 24, sim_seconds: 300, sandbox_rows_scanned: 50000000 }
    per_session:
      { usd: 5.00, tokens: 2000000, tool_calls: 400, sim_seconds: 86400, sandbox_rows_scanned: 2000000000 }
    per_negotiation:
      { usd: 2.00, tokens: 800000, tool_calls: 120, sim_seconds: 43200, sandbox_rows_scanned: 400000000 }
    per_whatif:
      { usd: 0.00, tokens: 0, tool_calls: 0, sim_seconds: 172800, sandbox_rows_scanned: 200000000 }
    per_compare:
      { usd: 0.00, tokens: 0, tool_calls: 0, sim_seconds: 864000, sandbox_rows_scanned: 1000000000 }
  loops:
    # LoopControl, kept apart from Budget so neither shape absorbs the other.
    negotiation: { max_rounds: 3, patience: 1, max_repair_retries: 0 }
    answer: { max_rounds: 1, patience: 0, max_repair_retries: 2 }
  routing:
    enabled: true
    policy_file: configs/routing_policy.yaml
    cold_start_tier: hosted_frontier # tier used for a class with too little measured history
    min_history_cases: 30 # int; below this a class has no measured accuracy
  cache:
    enabled: true
    namespace: run_id # enum: run_id | facility_id; facility_id is refused when a determinism hash is claimed
    watermark_strict: true # bool; false is refused by the release profile check
    max_entries: 5000
    eviction: lru_by_ledger_seq # enum: lru_by_ledger_seq; wall-clock eviction is not offered
  mcp:
    transport: stdio # enum: stdio | http
    allow_simulate: true # bool; simulate tools change nothing outside the run and are bounded by sim_budget
    allow_write: false # bool; true requires autonomy.default_tier == L3
    resource_taint: true # bool; false is refused by the release profile check
  vision:
    enabled: true
    frame_rate_hz: 1.0 # float, 0.1..10
    resolution: [512, 512]
    detector: color_blob # enum: color_blob | tiny
    degradation:
      blur_sigma: 1.2 # float, >= 0
      jpeg_quality: 70 # int, 10..100
      occlusion_rate: 0.05 # float, 0..0.5
      dropped_frame_rate: 0.02 # float, 0..0.5
    counting:
      window_s: 300 # int
      chart: p # enum: p | u | np
    vlm:
      enabled: false
      model: <vlm-id>
  voice:
    enabled: false
    stt_model: base.en # enum from the packaged set
    tts_voice: en_US-lessac-medium
    confirm_actions: true # bool; false is refused when autonomy.default_tier != L1
  evals:
    suite: configs/evals/core.yaml
    fast_subset_size: 40 # int
    seed: 20260101 # int
  finops:
    price_book: configs/model_prices.yaml
    pnl_cost_centers_by: subsystem # enum: subsystem | package | question_class
```

Cross-field validation rules, all enforced at load and all with their own test:

- `hosted.enabled` requires the API key environment variable when `transport.mode == live`.
- `allow_write_tools` requires `default_tier == L3`, and `mcp.allow_write` requires `allow_write_tools`.
- `voice.confirm_actions` cannot be false above L1.
- `providers.local.model_id` must be a key in `configs/models.lock` unless `transport.mode == replay`.
- `sandbox.threads` must equal 1. Any other value is rejected with the determinism reason quoted in the error.
- Every key under `budgets` deserializes into a complete `Budget` and every key under `loops` into a complete `LoopControl`. A budget carrying `rounds`, or a loop carrying `usd`, is a load error.
- Every tool exercised by a command in `docs/quickstart-commands.yaml` is reachable at `autonomy.default_tier` with the shipped `mcp` flags. This is what stops the headline demo from being disabled by a default (D-12).
- `cache.namespace: facility_id` is rejected for any run that also requests a determinism hash.
- The release profile (`just check-release-profile`) refuses `grounding.enabled: false`, `grounding.on_violation != refuse`, `accuracy.majority_rule != strict`, `cache.watermark_strict: false`, `cache.namespace != run_id`, and `mcp.resource_taint: false`.

### 6.2 `metrics.yaml`

```yaml
version: 1
# Derived, not hand-maintained: the union of tables declared by the metrics below,
# minus deny_list. The loader recomputes it and fails when this copy disagrees.
read_allowlist:
  [
    historian.telemetry,
    twin.state,
    findings,
    orders,
    genealogy,
    gl_postings,
    energy,
    shipments,
    equipment_state,
    production_counts,
    freight_invoices,
    tariff_schedule,
    inventory_positions,
    demand_history,
  ]
# Never reachable from the sandbox, whatever a metric declares (C7).
deny_list: [credentials, api_keys, user_messages, agent_transcripts, sop_drafts]
entities: [{ name: order_line, primary_key: [order_id, line_no] }, ...]
dimensions: [{ name: channel, type: categorical, source: orders.channel }, ...]
measures: [{ name: units_ordered, agg: sum, expr: orders.qty_ordered }, ...]
metrics:
  - name: fill_rate
    type: ratio
    numerator: units_shipped_first_pass
    denominator: units_ordered
    unit: ratio
    domain: { min: 0.0, max: 1.0 }
    grain: [order_line]
    agg_time_dimension: order_created_at
    allowed_dimensions: [channel, customer_segment, sku_class, site, week]
    definition_source: docs/references/metric-definitions.md#fill-rate
    fixture: tests/fixtures/metrics/fill_rate.yaml
    owner_package: twinflow-semantics
    since_version: "0.2.0"
```

Validation: names are unique snake_case; a ratio metric's numerator and denominator resolve to declared measures; `domain.min < domain.max`; the compiled SQL parses under sqlglot's DuckDB dialect; `fixture` exists; `definition_source` resolves to an existing anchor. Two allowlist rules replace the single one an earlier draft used: every referenced table is in the derived `read_allowlist`, and the intersection of `read_allowlist` and `deny_list` is empty.

**The required-metrics test, made capable of failing.** An earlier draft required the five metrics "once their producing subsystems have landed", which has no trigger, so no state of the world could fail it (D-12). The trigger is now mechanical. `configs/metrics_manifest.yaml` maps each required metric to the phase that must supply it:

```yaml
required_metrics:
  - { metric: days_of_supply, required_by_phase: "3d", requirement: 6a }
  - { metric: otif, required_by_phase: "3e", requirement: 6a2 }
  - { metric: fill_rate, required_by_phase: "3e", requirement: 6a3 }
  - { metric: landed_cost, required_by_phase: "3h", requirement: 6a7 }
  - { metric: oee, required_by_phase: "3i", requirement: 6a9 }
```

`test_required_metrics_present_for_current_phase` reads the current phase from `[tool.twinflow] phase` in `pyproject.toml`, selects every metric whose `required_by_phase` is at or before it, and asserts each is defined in `metrics.yaml` with a fixture and a resolvable `definition_source`. What fails it is a phase bump landing without its metric, which is exactly the moment a human would otherwise forget. Until the phase arrives, the same test asserts the metric is absent, so a metric cannot land early with an unbacked definition either.

### 6.3 Other files

- `configs/routing_policy.yaml`: `question_class -> [{model_tier, min_class_accuracy, max_usd}]`, plus `escalate_on: [abstain, rubric_floor, no_majority]`, `cold_start_tier`, `min_history_cases`, and `measured_from_suite_version`. Validation: every model tier exists in the price book; every class exists in the eval taxonomy; `min_class_accuracy` in 0..1; `measured_from_suite_version` exists in the committed eval artifact history.
- `configs/models.lock`: per model artifact, `file`, `bytes`, `sha256`, `release_tag`, `license`. Validation: every license is on the C11 allowlist; every referenced file resolves after `just fetch-models`; no weight file is tracked in git.
- `configs/metrics_manifest.yaml`: required metric to required-by phase and requirement id, read by the required-metrics test.
- `configs/vision_bench.yaml`: the frame set, degradation level, temperature, sample count, and seed for the E29 comparison.
- `configs/evals/scoring_paths.yaml`: the path filter that decides when a push runs the full eval suite.
- `configs/model_prices.yaml`: `model_id -> {input_per_mtok, output_per_mtok, cached_input_per_mtok, quoted_on (date), source_url}`. Validation: `quoted_on` is a valid past date; every price is non-negative.
- `configs/abstention_policy.json`: generated artifact, carries `suite_version`, `commit`, `thresholds` (global and per class), `risk_coverage` points. Validation: thresholds in 0..1; suite version exists.
- `configs/causal_graph.yaml`: `nodes`, `edges`, `unobserved`, `treatments`, `outcomes`. Validation: the graph is acyclic; every node maps to an available column; the file's `generated_from_commit` matches the current kernel edge registration hash, or CI fails with an instruction to regenerate.
- `configs/evals/*.yaml`: eval cases. Validation: every case has a typed ground truth, a seed, a facility profile, and provenance; `abstain_required` cases must declare what was withheld.
- `configs/redteam/*.yaml`: attacks with surface, payload, expected outcome `blocked`, and the defense expected to fire.
- `configs/sop_rules.yaml`: `SOPRule` definitions. Validation: every `sop_clause` anchor resolves and the quoted text matches.
- `configs/datasets.yaml`: export definitions with format, filters, and license.
- `configs/forecast_arena.yaml`: entrants, horizons, origins, alpha, conformal method, and which extras are required.

---

## 7. Testing

Four tiers with runtime budgets (C4): unit under 60s for this section's packages, property suite under 180s, seeded end-to-end under 8 minutes, model-dependent tier nightly. Everything in the first three tiers runs with `transport.mode: replay` and a fixed seed, so the AI layer's CI is deterministic and free.

### 7.1 Unit tests, by package

Representative and non-exhaustive; every public function gets one.

- `semantics`: metric compilation for each metric type; watermark computation; sqlglot rejection of DDL/DML/out-of-allowlist tables; sandbox resource limits stop a runaway query; ledger id monotonicity.
- `accuracy`: numeral extraction across every supported format; unit normalization; tolerance boundary behavior at exactly `match_rel_tol`; repair-message construction for each failure class; clustering for scalars, identifiers, and rankings; Wilson lower bound computation.
- `agent`: tool schema generation; tier gating; transcript serialization; SOP retrieval and clause anchor resolution; fault handling per tool.
- `governance`: hash chain construction and verification; append-only enforcement; budget reservation arithmetic; contract-net phase transitions and termination conditions.
- `mcp`: schema equality with the registry; resource taint marking; flag gating for simulate and write.
- `vision`: line-crossing counter on synthetic tracks; SOP predicate evaluation for each rule kind; kappa computation; p-chart state transitions.
- `mlops`: PSI and KS computation; promotion gate refusals when any condition is unmet; rollback pointer swap.
- `causal`, `forecast`, `cascade`, `edge_ai`, `datasets`, `finops`: scoring functions, protocol mechanics, price arithmetic to the cent.

### 7.2 Property-based invariants (Hypothesis)

Each is a named test with a generated input space.

1. `prop_grounding_refuses_every_unlogged_numeral`: under `GroundingPolicy.strict()`, where every allowance is off, for arbitrary answer text and arbitrary ledgers, if any extracted numeral has no ledger match within tolerance, the verdict is REFUSE. No generated counterexample may exist. The strict qualifier is load-bearing: under the shipped policy three allowance classes deliberately pass, so the unqualified statement is false and Hypothesis would find a counterexample on the first run.
2. `prop_grounding_allowances_are_exactly_the_documented_four`: under any policy, an unmatched numeral that passes belongs to one of the four classes in the 5.3(f) table, and the class that admitted it is recorded in `allowance_hits`. A numeral outside all four never passes unmatched.
3. `prop_grounding_stable_under_formatting`: reformatting a matched value (thousands separators, percent versus ratio, unit word versus symbol, rounding within tolerance) never flips PASS to REFUSE.
4. `prop_grounding_no_false_pass_on_digit_edit`: for a ledger whose numerals are pairwise separated by more than `2 * match_rel_tol` in relative terms, editing any single significant digit of a matched numeral beyond tolerance flips PASS to REFUSE. The separation precondition is required, not cosmetic: with 120 and 130 both in the ledger, editing the tens digit of a cited 120 lands on 130, which is a genuine ledger value, so PASS survives and the unconditioned claim is false. The generator enforces the precondition, and a second variant asserts the same conclusion for an edited value absent from the ledger at any separation.
5. `prop_ledger_ids_monotone_and_unique`: result ids strictly increase within a run and are never reused, including across a multi-role negotiation, where the fixed role order in 5.5 is what makes the sequence reproducible.
6. `prop_budget_conservation`: at every step, sum of live reservations plus remaining equals the total on all five `Budget` components, and no reservation is granted beyond remaining, for arbitrary interleavings of reserve, settle, and supervisor reallocation.
7. `prop_decision_register_append_only`: mutating an existing record raises, for any generated mutation, and `verify_chain` fails on any tampered byte.
8. `prop_tool_schema_roundtrip`: any instance of any tool's args model serializes to JSON that validates against the emitted JSON Schema and deserializes equal, and the MCP-advertised schema equals the registry schema after RFC 8785 canonicalization with `$ref` resolved.
9. `prop_selfconsistency_modal_is_a_sample`: the returned consensus value is one of the executed sample results. Under `majority_rule: strict` the outcome is ABSTAIN whenever no strict majority exists; under `plurality` the outcome is the largest cluster and the property asserts the reported `agreement` fraction matches that cluster's share. The property is stated against the configured rule because both modes exist in the enum.
10. `prop_abstention_coverage_monotone`: on a fixed eval result set, raising the threshold never increases coverage. Only the coverage half is asserted. Conditional accuracy is not monotone in the threshold on a finite sample unless the confidence score ranks perfectly, since raising the cut can drop a correct answer that sat just above it while keeping an incorrect one, so asserting monotone accuracy would fail on honest data.
11. `prop_risk_coverage_curve_well_formed`: the risk-coverage curve is non-increasing in coverage after tie-breaking, every point carries its support count, and the selected threshold is the lowest whose Wilson 95% lower bound on conditional accuracy clears `target_conditional_accuracy` with at least `min_support` answered cases. This is the property the calibration procedure in 5.3(g) depends on.
12. `prop_sandbox_rejects_mutation`: for arbitrary generated SQL strings, any statement containing DDL or DML is rejected before execution.
13. `prop_metric_domain_holds`: for arbitrary fixture data and windows, every metric's value lies inside its declared domain or the query is flagged `ImplausibleMagnitude`.
14. `prop_cache_never_stale`: for arbitrary interleavings of writes and reads, a served hit's stored watermark is greater than or equal to the query's required watermark on every table.
15. `prop_cache_deterministic`: for a fixed seed, config, and cassette, two runs produce the identical sequence of hit, miss, staleness-reject, and eviction decisions. The generator varies the pre-existing cache contents, which the run must ignore under `namespace: run_id`.
16. `prop_cost_accounting_adds_up`: per-question cost equals the sum of its tool and model costs to the cent, and the monthly P&L equals the sum of its source events.
17. `prop_tainted_content_never_in_system_slot`: for arbitrary retrieved content, the assembled prompt places it only in data envelopes, and no tainted span authorizes a tool above L1.
18. `prop_autonomy_never_self_elevates`: for arbitrary question text, tool results, and retrieved content, no path raises a session's effective tier without an `AutonomyGrant` carrying a human approver, and every grant expires at whichever of its two limits arrives first.
19. `prop_reconciliation_symmetry`: the disagreement measure is symmetric and is zero exactly when the two counts are equal.
20. `prop_answer_numerals_subset_of_successful_results`: for any subset of tools forced to fail, the numerals in the emitted answer come only from ledger entries produced by successful calls.
21. `prop_determinism_of_the_turn`: on one platform with a pinned dependency set, identical seed, config, and cassette produce identical answer text, identical event ids, and an identical event-log hash over the hashed core. Across platforms the property asserts the weaker D-05 tier: identical business-event sequence, and continuous fields agreeing within the measured tolerance the cross-platform job reports. The section claims exactly these two tiers and no more.
22. `prop_negotiation_terminates`: for arbitrary role proposal generators, the contract-net loop terminates within `LoopControl.max_rounds` or escalates, never loops.
23. `prop_negotiation_order_is_fixed`: for arbitrary role registration orders and arbitrary per-role latencies, the emitted `order_index` sequence within a phase is the ascending sort of role ids, and the event sequence is unchanged. This is the property that would catch an asyncio scheduler creeping back in.

### 7.3 Seeded end-to-end scenarios

- `e2e_killer_demo`: "what happens to daily throughput if I add a second scan portal at dock 3?" runs `run_whatif`, receives the LSS verdict, and produces an answer containing the delta, the test name, the p-value, the effect size, the interval, and a confidence caveat. Golden-file compared.
- `e2e_investment_roadmap`: `compare_scenarios` over five candidates under a budget produces a ranked table; golden-file compared including the not-distinguishable rows and their required replication counts.
- `e2e_tool_failure_refusal`: each tool in turn is fault-injected to raise, timeout, and return a schema-invalid payload. Assertions: the answer contains no numeral outside the echoed question, `agent.abstained` is emitted with reason `tool_failure`, the failing tool is named, and no cached entry is written.
- `e2e_sensor_disagreement`: a seeded scenario degrades RFID read rate at one portal; the CV channel disagrees; a `vision.sensor_disagreement` finding is raised with all three counts; `explain_finding` returns the evidence and the suggested next tool.
- `e2e_mcp_session`: a scripted MCP client lists tools, calls three read tools, runs `run_whatif` successfully at the shipped defaults, is denied a second `run_whatif` once `per_whatif` is exhausted, and is refused on `apply_change` without L3.
- `e2e_quickstart_reachability`: every command in `docs/quickstart-commands.yaml` runs against a freshly cloned configuration with no flags added, and the killer demo is among them.
- `e2e_negotiation`: a disruption triggers a four-role negotiation under a budget; the award is deterministic, the decision register verifies, and `replay_counterfactual` on the runner-up returns a number.
- `e2e_mcp_negotiation_transcript`: an external MCP client reads `twinflow://negotiation/{task_id}` and reconstructs every round, proposal, and critique of the run above from the MCP resource alone.
- `e2e_autonomy_elevation`: an L1 session is refused `apply_change`, an elevation request is emitted, a human approval writes a scoped grant and a decision record, the call then succeeds, and the grant expires at its question limit and is refused again.
- `e2e_shadow_promotion`: a challenger PdM model shadows the champion, the comparison reaches significance, promotion is blocked without an approved decision, then succeeds with one, then rolls back to byte-identical predictions.
- `e2e_injection_gauntlet`: the red-team corpus runs against a live facility whose device names, SOP file, and supplier records carry payloads. Zero successes required.
- `e2e_airgap_slm`: the SLM path answers the fast eval subset in a container with egress blocked.

### 7.4 Validation gates

D-11 governs this table. Every row names a specific external published reference with an edition or locator, sets a tolerance no tighter than that reference's own precision, states a measured noise floor where the quantity is stochastic, and states what would falsify it. This repository is never a reference for itself. Gates that compare an implementation against an internal contract are not statistical validations and live in 7.5. Measurements with no external reference are published without a pass threshold in 7.6, and the missing reference is recorded as an open question rather than hidden behind a passing gate.

Which statistics twinflow implements itself, since a cross-check against the library you called is not a cross-check. Implemented here, and so eligible for a cross-implementation gate: Cohen's kappa, population stability index, the Wilson score interval, structural Hamming distance, split conformal calibration, and the Friedman and Nemenyi statistics. Wrapped from a library, and so checked against a published worked example only: the Kolmogorov-Smirnov two-sample test (`scipy.stats.ks_2samp`), the DoWhy and EconML estimators, and the statsforecast model family. Each gate below says which case it is in.

Offline handling, made falsifiable. A gate that cannot run offline is marked nightly, and its last result is committed as an artifact carrying the commit SHA and the UTC date that produced it. `test_nightly_artifacts_are_fresh` fails when an artifact is older than 30 days, or when the paths it validates have changed by more than 20 commits since it was produced. A committed number with no staleness check is not a gate (D-12).

| Gate           | What it validates                                             | External published reference                                                                                                                                                                                                                                                                                                                                                                                                                                                          | Tolerance, noise floor, and falsification                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                          |
|----------------|---------------------------------------------------------------|---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|--------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| VAL-GATE AI-1  | Split conformal marginal coverage                             | Lei, G'Sell, Rinaldo, Tibshirani and Wasserman, "Distribution-Free Predictive Inference For Regression", arXiv:1604.04173v2, Theorem 2.2, full text retrieved 2026-08-09 (HTTP 200, <https://ar5iv.labs.arxiv.org/html/1604.04173>): coverage is at least 1-alpha, and at most 1-alpha+2/(n+2) for n split in half, which is 1-alpha+1/(m+1) for m calibration residuals. Also Vovk, Gammerman and Shafer, _Algorithmic Learning in a Random World_ (2005), chapter 2                 | m=999, alpha=0.10, so the exact marginal coverage is 900/1000 = 0.9000 and per-replication conditional coverage is Beta(900, 100) with sd 0.0095. Design: 2000 replications, each with a fresh calibration set and 2000 fresh test points. Measured pooled-mean noise floor: standard error 2.6e-4, 99% half-width 6.7e-4. Assert pooled coverage within 0.002 of 0.9000, a band three times the half-width. Falsified by pooled coverage outside [0.898, 0.902]. The second falsifier is the spread: an observed coverage estimate carries both the Beta sd 0.0095 and the test-sampling sd sqrt(0.09/2000) = 0.0067, so the expected between-replication sd is sqrt(0.0095^2 + 0.0067^2) = 0.0116, and a measured sd outside [0.0093, 0.0139] falsifies the gate. Asserting the Beta sd alone against the observed spread would fail every run, because the observed spread also contains the test-sampling term |
| VAL-GATE AI-2  | Theta forecasting implementation                              | `statsforecast` 2.1.1 (Apache-2.0, version verified from the package index), `AutoTheta` on the M3 monthly subset, as the external published implementation. The method is Assimakopoulos and Nikolopoulos, "The theta model: a decomposition approach to forecasting", International Journal of Forecasting 16(4):521-530 (2000), locator verified from Crossref 2026-08-09                                                                                                          | Per-series sMAPE agrees with the pinned `statsforecast` version within 1e-6 relative on every series, and the aggregate within 1e-9. Falsified by any series exceeding it. The competition's own published sMAPE for Theta is not asserted, because the primary text has not been read: see open question 18. Dataset fetched at test time, never vendored (C11)                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                   |
| VAL-GATE AI-3  | Attribute agreement between the CV and RFID counting channels | AIAG _Measurement Systems Analysis_ 4th edition, attribute agreement analysis worked example (a paid manual; the small worked table is transcribed, not bulk redistributed), plus `sklearn.metrics.cohen_kappa_score` at a pinned version as the independent implementation of a statistic twinflow computes itself                                                                                                                                                                   | Two tolerances, because the two references have different precision. Against the AIAG figure, agreement within half a unit in its last printed digit. Against sklearn on the same table, agreement within 1e-9. Falsified by either. The AIAG figure is attributed in the test docstring because the manual is not publicly retrievable                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                            |
| VAL-GATE AI-4  | Causal estimator correctness and interval coverage            | Pearl, _Causality_ 2nd edition (2009), the backdoor adjustment formula, applied to a linear-Gaussian design whose true average treatment effect is available in closed form                                                                                                                                                                                                                                                                                                           | Bias of the DML estimate below 0.01 of the analytic effect at n=20000, with the measured Monte Carlo standard error reported beside it. Coverage of the 95% interval over 500 seeds: the one-sided exact Clopper-Pearson 99% lower bound on the coverage rate is at or above 0.90. This single rule is the CI decision. Falsified when the lower bound drops below 0.90, which happens when true coverage falls to roughly 0.92                                                                                                                                                                                                                                                                                                                                                                                                                                                                                    |
| VAL-GATE AI-4b | Placebo refutation calibration                                | Same design as AI-4 with the treatment permuted, so the true effect is zero by construction                                                                                                                                                                                                                                                                                                                                                                                           | Over 500 seeds, the one-sided exact Clopper-Pearson 99% lower bound on the rate at which the 95% interval contains zero is at or above 0.90. A plain "at least 95% of replications" rule is not used: under the null the observed rate is 0.95 with a standard error of 0.0097 at 500 seeds, so that rule fails about half the time and is a coin flip, not a gate                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                 |
| VAL-GATE AI-5  | Structure-recovery scoring correctness                        | Tsamardinos, Brown and Aliferis, "The max-min hill-climbing Bayesian network structure learning algorithm", Machine Learning 65(1):31-78 (2006), locator verified from Crossref 2026-08-09, for the structural Hamming distance definition, which twinflow implements itself                                                                                                                                                                                                          | SHD on a hand-computed 4-node example matches exactly, since both values are integers. Falsified by any disagreement. The discovery algorithms' own recovery scores carry no pass threshold and are published in 7.6                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                               |
| VAL-GATE AI-8  | Abstention calibration                                        | El-Yaniv and Wiener, "On the Foundations of Noise-free Selective Classification", Journal of Machine Learning Research 11(53):1605-1641 (2010), page retrieved 2026-08-09 (HTTP 200), for the risk-coverage construction; Wilson, "Probable Inference, the Law of Succession, and Statistical Inference", Journal of the American Statistical Association 22(158):209-212 (1927), locator verified from Crossref 2026-08-09, for the score interval, which twinflow implements itself | On the held-out split, conditional accuracy above the selected threshold has a Wilson 95% lower bound at or above 0.98 with at least 30 answered cases. Noise floor: with 30 cases the Wilson lower bound at 100% observed accuracy is 0.885, so the gate cannot pass on 30 perfect cases alone and the support requirement rises with the target. Falsified when no threshold in the sweep meets both conditions, which is a genuine result and is reported rather than worked around                                                                                                                                                                                                                                                                                                                                                                                                                             |
| VAL-GATE AI-9  | Semantic metric correctness                                   | Per-metric worked fixture with a hand-computed expected value stated to a declared precision, plus the twin's own Python KPI computation frozen as a golden fixture at a named commit that predates the metric layer                                                                                                                                                                                                                                                                  | Fixture match exact to the fixture's stated precision. Frozen cross-implementation relative difference at most 1e-9. The word independent is not used: both implementations read `docs/references/metric-definitions.md`, so this checks implementation agreement, not definitional independence                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                   |
| VAL-GATE AI-10 | Numerical substrate under the agent's answers                 | NIST Statistical Reference Datasets, univariate summary statistics, retrieved 2026-08-09 (HTTP 200): NumAcc1 certifies mean 10000002 and standard deviation 1 as exact on 3 observations; NumAcc4 certifies mean 10000000.2 and standard deviation 0.1 as exact on 1001 observations; Lew certifies mean -177.435000000000 and standard deviation 277.332168044316 on 200 observations                                                                                                | Against exact certified values, agreement is exact. Against Lew's 15-significant-digit certification, relative agreement within 1e-12, which is looser than the certification's own precision. NumAcc4 is the conditioning case and is asserted rather than skipped. Falsified by any dataset missing its certified digits                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                         |
| VAL-GATE AI-11 | Drift statistics                                              | For PSI, a hand-computed worked example committed as a fixture, since twinflow implements PSI itself. For KS, `scipy.stats.ks_2samp` at a pinned version, which is the shipped implementation, so this row is a regression fixture and not a cross-check, and it says so                                                                                                                                                                                                              | PSI within 1e-12 of the hand-computed fixture. KS statistic and p-value within 1e-12 of the pinned scipy values recorded in the fixture, which detects a scipy version bump changing behavior and detects nothing else. Falsified by either drifting                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                               |
| VAL-GATE AI-16 | Forecast ranking honesty                                      | Demsar, "Statistical Comparisons of Classifiers over Multiple Data Sets", Journal of Machine Learning Research 7(1):1-30 (2006), page retrieved 2026-08-09 (HTTP 200), for the Friedman test with Nemenyi post-hoc and the critical-difference diagram, which twinflow implements itself against the article's worked construction                                                                                                                                                    | The Friedman statistic and Nemenyi critical difference match the article's worked example to its printed precision. A pairwise "better" claim appears in the published table only when the post-hoc comparison is significant at alpha=0.05, and the test asserts the table's claim flags match the computed significance. Falsified by a claim flag with no significant comparison behind it                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                      |

### 7.5 Conformance gates

These check an implementation against a contract this repository defines. They are deterministic pass or fail, they carry no statistics, and they are kept out of 7.4 so the reference column there keeps its meaning (D-11).

| Gate       | What it checks                                 | Contract                                                                                                                                                                | Pass condition and falsification                                                                                                                                                                                                                                                                                                                                                                                                               |
|------------|------------------------------------------------|-------------------------------------------------------------------------------------------------------------------------------------------------------------------------|------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| CONF-AI-6  | Grammar conformance under constrained decoding | The registry's JSON Schemas compiled to grammars                                                                                                                        | 1000 generated tool calls across every registry schema parse as valid JSON and satisfy the grammar: rate exactly 1.0. Falsified by one failure. Post-validation acceptance is measured, not asserted, and its taxonomy is published in 7.6                                                                                                                                                                                                     |
| CONF-AI-7  | Grounding checker regression corpus            | A committed labeled corpus of 200 answers, 100 grounded and 100 with at least one unlogged numeral, including near-miss rounding, unit-swap, and transposed-digit cases | Recall on unlogged numerals 1.00 and false-refusal rate at most 0.02, on that corpus. The corpus is a regression fixture written by the same author as the checker, so it proves the checker handles the cases the author imagined and nothing more. The load-bearing test is property 1 under `GroundingPolicy.strict()` plus an adversarial numeral generator authored separately from the extractor and reviewed as a red-team contribution |
| CONF-AI-12 | MCP contract fidelity                          | The registry's JSON Schemas as the single source of truth                                                                                                               | Every MCP-advertised tool schema equals the registry schema after RFC 8785 canonicalization with `$ref` resolved. A new tool with no MCP entry fails. Falsified by a canonical-form difference, not by key reordering                                                                                                                                                                                                                          |
| CONF-AI-13 | Sandbox opens its data with no network         | The baked extension directory and the autoload settings in 5.3(a)                                                                                                       | The sandbox reads a Delta table inside a container with egress blocked. Falsified by any outbound connection or by an extension load failure                                                                                                                                                                                                                                                                                                   |
| CONF-AI-14 | Air-gapped operation of the edge SLM           | E32's requirement that the OT segment does not reach out                                                                                                                | The fast eval subset completes with egress blocked, using the pre-fetched artifact from `configs/models.lock`. Falsified by any outbound connection                                                                                                                                                                                                                                                                                            |
| CONF-AI-15 | Red-team suite                                 | The committed attack corpus at the pinned commit                                                                                                                        | Zero successful attacks at that commit, and every attack run records which defense fired. This is a claim about the corpus. The defense-firing distribution is published in 7.6                                                                                                                                                                                                                                                                |
| CONF-AI-17 | Dataset reproducibility                        | C1 determinism applied to E25 exports                                                                                                                                   | Regenerating from the recorded seed and command reproduces every file's SHA-256 exactly, on the pinned platform (D-05). Falsified by any hash mismatch                                                                                                                                                                                                                                                                                         |
| CONF-AI-18 | Package installability                         | A1 and D-10                                                                                                                                                             | Each distribution installs alone into a clean environment and imports its public API. `twinflow-accuracy` does so with `pydantic` alone. Falsified by an import error or a transitive install                                                                                                                                                                                                                                                  |

### 7.6 Reported measurements

These are published with their method and no pass threshold, because no external reference exists to validate them against and D-11 forbids recording such a statistic as a passing gate. Each names the open question that would have to be resolved to promote it.

| Measurement | What is published                                                                                                                                                                                            | Why it is not a gate                                                                                                                                                                                                                                                 |
|-------------|--------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| MEAS-AI-1   | Causal effect recovery against the twin's own do-intervention truth: absolute error, relative error, and empirical interval coverage across N seeds                                                          | The truth is generated by this repository, so the comparison is a self-check. Open question 19 asks what external benchmark would make it a gate                                                                                                                     |
| MEAS-AI-2   | Structure recovery against the generated true DAG: SHD, edge precision and recall, and orientation accuracy as a function of sample size, with a random-DAG baseline                                         | Same reason. Publishing "discovery recovered 61% of edges at 50k samples" is a result; asserting a threshold against a self-generated truth is not                                                                                                                   |
| MEAS-AI-3   | Post-validation acceptance rate for constrained decoding, with the failure taxonomy by constraint kind                                                                                                       | The floor is a property of the model, not of an external standard                                                                                                                                                                                                    |
| MEAS-AI-4   | The classical CV channel against the VLM: precision, recall, F1 with sample standard deviation, sim latency, and cost per frame, under the protocol fixed in 5.6                                             | No external benchmark covers synthetic warehouse frames                                                                                                                                                                                                              |
| MEAS-AI-5   | Router report: percent routed down, accuracy retained against an all-frontier baseline, dollars saved, escalation rate, and regret                                                                           | Depends entirely on this repository's own price book and suite                                                                                                                                                                                                       |
| MEAS-AI-6   | Red-team defense-firing distribution and the count of attacks blocked by more than one defense                                                                                                               | A property of the corpus, informative about layering                                                                                                                                                                                                                 |
| MEAS-AI-7   | SLM against the hosted model, per question class, with the cassette date and the hosted model version                                                                                                        | Reproducible only against a frozen hosted version: open question 6                                                                                                                                                                                                   |
| MEAS-AI-8   | Repair-loop yield: eval-suite accuracy with the E26(c) verification loop disabled and enabled, per question class, with the distribution over the six failure classes and the retry count that resolved each | The BIRD article establishes that execution accuracy on a large text-to-SQL benchmark is far below human, not what a repair loop recovers on warehouse questions. The figure the requirements source attributes to the loop could not be retrieved: open question 16 |
| MEAS-AI-9   | Self-consistency yield: eval accuracy, abstention rate, and the agreement distribution at n = 1, 3, 5, 7, 9, with the no-majority rate at each                                                               | The published GSM8K gain is a reasoning-benchmark result under a different sampling regime, so it motivates the layer and does not bound this repository's yield                                                                                                     |

### 7.7 Published live metrics

`just eval` regenerates `docs/eval/latest.json`, `docs/eval/risk_coverage.svg`, `docs/eval/improvement_curve.svg`, `docs/eval/routing_report.md`, `docs/eval/redteam_report.md`, and `docs/eval/cv_vs_vlm.md`. A CI job asserts the README's quoted accuracy, abstention rate, and grounding-checker pass rate match `latest.json`. The README numbers cannot be stale, and the honesty claim in E26 is enforced by a test rather than by good intentions.

---

## 8. Phase placement

The ordering rule from the agreed resequencing applies: contracts that cannot be retrofitted go to Phase 0, and an E-item that is an upstream dependency of earlier work moves ahead of its dependents. Nothing is dropped and nothing is optional.

**Phase 0 (contracts).**

- `ToolSpec`, `ToolRegistry`, and the tool JSON Schema emission. Every later surface (agent, MCP, REST, role agents) reads from it, so it must exist before the first tool.
- `ModelTransport` with record and replay. Retrofitting determinism onto an agent that already has 200 tests is the retrofit that never happens, and C1 is non-negotiable.
- `/schemas/agent/**`, `/schemas/governance/**`, `/schemas/mlops/**`, `/schemas/vision/**` v1 envelopes.
- `ResultLedger` and the `result_id` field on every tool result model. The grounding checker is impossible to add later if results were never given ids.
- `CostRecord` and `finops.cost.accrued`. Per-question cost history cannot be reconstructed from data never recorded, which is exactly the argument E45 makes about enterprises that cannot price their AI.
- `DecisionRecord` schema and the append-only hash-chained store. Same argument: a decision register that starts in Phase 6 has no history to audit.
- Config schema files for the `ai:` block, `metrics.yaml`, and `model_prices.yaml`, with the C5 loader.
- The rule that every model invocation in every package goes through `ModelTransport`, including vision, voice, and the cheap classifier, with the nondeterminism gate that enforces it. A package that calls a provider SDK directly is cheap to write and expensive to unwind.
- The deterministic scheduling rule from 5.5: fixed role order by sorted role id, tool dispatch through the kernel scheduler, no ambient asyncio loop. Four role agents written against an async runtime cannot be made deterministic afterwards without rewriting all four.
- `@causal_edge` and its registry, owned jointly with the kernel section. Every sim process from Phase 1 onward carries it, because a decorator added at Phase 6 is a decorator that silently misses the processes written before it.
- The three RNG child seeds this section adds, registered in the stream catalog under the naming grammar in `docs/design/variability-and-faults.md` section A.2: `agent.transport.latency`, `agent.accuracy.self_consistency_nonce`, and `vision.vlm.sample`. A stream name added later shifts nothing, because streams are name-addressed, but a draw taken before its stream exists is unseeded and cannot enter the hashed log.
- The declared hash carve-out at `/schemas/_hash_carveout.yaml` (D-01), because the first event schema written under a different rule is the one that breaks the C1 gate.

**Phase 1 (walking skeleton).** One tool (`get_fleet_health`), the local provider, E26(d) structured outputs through the grammar path, tool-call events, and the dashboard chat stub. The skeleton proves the seam: a tool call, a schema-valid response, a logged event, replayable.

The local provider's Phase 1 default is a stock small permissively licensed instruction-tuned GGUF, recorded in `configs/models.lock` and fetched by `just fetch-models`. It is not the plant-distilled SLM, which does not exist until E32 in Phase 6. Pointing the shipped config at a file that will not exist for five phases would have broken the source's requirement that the demo runs without an API key for most of the project's life. When E32 lands, the swap is a `models.lock` entry and a `providers.local.model_id` change, both recorded in the model registry with the benchmark that justified them.

**Phase 2 (LSS engine plus reference-validated tests).** The engine's arrival is what makes the rest of the accuracy stack meaningful, because now there are governed numbers to ground against.

- E26(a) sandbox and execution grounding; E26(b) semantic layer with the first metrics; E26(c) verification loop; E26(f) grounding checker; E26(e) self-consistency.
- `get_bottleneck`, `get_findings`, `explain_finding`, `run_capability_report`, `query_metric`.
- E27 first eval suite and CI integration, with E26(g) abstention calibrated on it. Abstention cannot be calibrated before an eval suite exists, which fixes the order of (g) after the harness even though the source lists it last in the stack.
- The E43 red-team harness (not the full corpus) with the attack surfaces that exist by Phase 2: device names and finding evidence. The corpus grows as new content surfaces land, because a suite written against an empty system audits nothing.
- VAL-GATE AI-8, AI-9, and AI-10 land here, with conformance gates CONF-AI-6, CONF-AI-7, CONF-AI-13, and CONF-AI-18, and reported measurements MEAS-AI-3, MEAS-AI-8, and MEAS-AI-9.

**Immediately after Phase 2.** E1 (hosted replay demo) pulls forward per the agreed resequencing; this section supplies the transcript artifact format and the agent's contribution to the recorded shift. E2 (MCP) lands here too: it is a pure adapter over a registry that already exists, it adds no domain logic, and it is the highest legibility-per-hour item in the AI tier. The one-line `uvx` config in the README requires the first PyPI release (C9), so the README carries a local-path config until that release.

**Phase 3 (sensor breadth, PdM, ERP/CMMS).** E43's registry, lineage, and drift monitors land with the first real models (the PdM trend models), because a registry created after five models exist starts with five untraceable models. Champion-challenger and rollback land with the second PdM model version.

**Phase 3b to 3c.** `run_whatif` and `compare_scenarios` land once the automation layer gives what-ifs something worth asking about and process mining gives the findings stream depth. The investment roadmap table is the consulting deliverable, so it lands as soon as the cost model behind it exists.

**Phase 3d (planning).** E31: the arena, the ranking tests, and the conformal wrapper, with interval coverage on a control chart. The foundation-model entrants land here rather than in Phase 6 because they are entrants in an arena that exists now, and adding a competitor to a running benchmark is cheaper than building the benchmark twice.

**Phase 3e to 3i.** Red-team surfaces expand with each new writable field: supplier records at 3e, SOP documents once E8's corpus grows, frame placards once the VLM lands. Metrics land with their producing subsystems: `otif` and `landed_cost` at 3e and 3h, `oee` at 3i, `days_of_supply` at 3d.

**Before 6a16.** E30 (causal), per the agreed resequencing, because the marketing layer's promotion-effect measurement is the confounded case and must not be built on correlation.

**Phase 4.** Component 4, the CV auditing channel: renderer hookup, degradation, the classical detector, SOP rules with clause citation, independent counting, and the reconciliation finding. VAL-GATE AI-3 lands here.

**Phase 5.** Polish: the E1 viewer's agent panel, the demo GIF ending on the statistical verdict, the README's live metrics job, and the SECURITY.md threat model for the MCP and sandbox surface (C7).

**Phase 6, in the stated E order.** E21 (multi-agent and decision governance, which needs E4 replay for counterfactual audit and the register that has been accumulating since Phase 0), E25 (dataset export layer, with each dataset shipping alongside its producing subsystem's card), E27's incident memory and improvement curve, E29 (VLM copilot benchmarked against the Phase 4 classical channel), E32 (edge SLM, which needs the eval harness to be benchmarked against and the corpus that Phase 2 onward has been accumulating), E33 (cascade GNN, which needs the E19 n-tier graph and the E20 optimizer to compare against), E34 (voice), E43's remaining MLOps pieces and the full red-team corpus, E45 (router, cache measurement, AI P&L into the financial twin from 6a17).

Dependency summary that fixes the order inside Phase 6: E21 requires E4 and the register; E29 requires component 4; E32 requires E27; E33 requires E19 and E20; E45 requires 6a17 for the P&L posting and E32 for a cheap tier to route down to.

---

## 9. Open questions

These are genuine ambiguities in the source or genuine cross-section boundaries. They are surfaced rather than resolved silently.

1. **Is there an `apply_change` tool?** Requirement 7 lists seven tools and adds `compare_scenarios`; requirement 6 says accepted what-ifs flow back as config, and E5 defines L3 auto-apply within guardrails. No tool is named for the application step. This section specifies `apply_change` behind an L3 gate and disabled by default, but the source never names it, and the alternative reading is that application is a human action in the dashboard with the agent only recommending. An implementer needs a decision.
2. **What is the denominator in E26(g)'s 98%?** "The threshold where accuracy exceeds 98%" is ambiguous between accuracy over all questions and accuracy conditional on answering. Selective-prediction convention is conditional on answering, which is what this section specifies, but the two readings produce different thresholds. Also unresolved: whether the threshold is global or per question class. This section fits per class with a global fallback.
3. **Modal result tolerance in E26(e).** Voting over executed results requires a tolerance for continuous values, which the source does not state. A tolerance too tight always reports no majority; too loose it manufactures consensus. Default 0.005 relative is proposed, and the sensitivity must be published, not assumed.
4. **Is MCP the real inter-agent transport in E21?** The source says role agents negotiate "over shared MCP state". Running the internal negotiation through an MCP loopback costs serialization and makes deterministic replay harder; an internal bus with MCP as the external facade is faster and more testable but is a looser reading of the requirement. This section specifies the internal bus with an MCP facade and flags the divergence.
5. **Modeled versus actual cost in E45.** In `replay` mode there are no provider calls, so there is no actual spend. The monthly AI P&L that the financial twin absorbs is modeled by default. Whether the repo ever publishes an actual-spend P&L, which needs a live run with a key, is a decision about what the demo claims.
6. **Reproducibility of the E32 hosted-model benchmark.** Benchmarking the SLM against the hosted model requires hosted calls, which CI cannot make without a key. This section proposes recording the hosted side once into cassettes and publishing it as a dated, versioned artifact, but that means the comparison is reproducible only against a frozen hosted model version, and hosted models change. The limitation needs stating in the README.
7. **Fair comparison in E29.** The classical CV channel is deterministic and the VLM is not. Comparing precision and recall across a deterministic and a sampled system needs a stated protocol (fixed temperature, fixed seed, n samples with variance reported). Which VLM can run locally at an acceptable frame rate on CPU is also unresolved and affects whether the benchmark is honest about cost.
8. **Who owns the frame renderer?** Requirement 4 says the camera watches "a rendered top-down view of the line (synthetic frames generated by the sim)". The renderer is arguably the twin section's or the dashboard section's. This section assumes it consumes frames through `vision.frame.captured.v1` and owns everything after ingest. The producing side needs an owner.
9. **Who owns the backtest arena?** Requirement 6a describes the forecasting evaluation (baselines, MAPE/WAPE, rolling backtest) inside the planning layer; E31 adds foundation-model entrants and conformal calibration. This section claims the arena mechanics and conformal wrapper; the planning section claims the demand signal and the inventory consumption. If both sections build a backtest loop the repo has two, which violates the single-source-of-truth rule.
10. **Data licensing for E25.** The repo is Apache-2.0. Datasets are usually licensed separately (CC0 or CC BY 4.0). The source does not say. Related: M3 and M4 data used in VAL-GATE AI-2 is fetched at test time rather than vendored, on the assumption that redistribution is not permitted; that assumption must be verified against the dataset's own terms before the gate ships.
11. **Circularity risk in E30's ground-truth DAG.** Deriving the true DAG from kernel edge registrations removes the "graph drawn from memory" problem but introduces a new one: a missing registration silently removes a true edge and inflates the discovery score. The proposed mitigation (intervening on declared non-parents must produce no detectable effect) has finite power. An implementer must decide how much power is enough and state it.
12. **E26(f) only covers numbers.** A sentence containing no numeral but a false causal claim ("the bottleneck moved because of the new roster") passes the grounding checker. The source's stated scope is numeric grounding and this section implements exactly that, with the rubric verifier and clause citation as partial cover for non-numeric claims. Whether a claim-level entailment check belongs in the stack is a real extension the source does not ask for.
13. **Where do plausibility bounds come from for unbounded metrics?** The metric `domain` covers ratios and non-negative quantities. Throughput, cost, and cycle time have no natural bound, so the band is derived from history with a widening factor. During Phase 1 to 2 there is no history, so the check is inert. The false-positive risk after a genuine step change (a new automation cell doubling throughput) needs a stated policy: the current design reports the value with a special-cause note and raises a finding rather than suppressing the answer, which can be the wrong tradeoff for some questions.
14. **Sequencing of the E2 one-line config.** The README's one-line `uvx twinflow-mcp` config is only true after the first PyPI publish (C9). Until then the README must show a local path invocation, and the two must not diverge. Whether the release automation is pulled earlier to make this line true is a judgement call about which promise the README makes first.
15. **The governed-metrics figure in E26(b).** The requirements source attributes a jump from 57% to 78% execution accuracy, and modeled questions reaching 90 to 100 percent, to a Snowflake measurement. A direct request to snowflake.com returned HTTP 403 on 2026-08-09, so the primary text was not read and no figure is published in this section. Either a retrievable primary source is named, or the layer keeps its architectural justification with no number attached to it.
16. **The verification-loop figure in E26(c).** The source attributes a move from 46% to about 80% on BIRD to the execution-verification loop. The BIRD article's abstract reports 40.08% execution accuracy for ChatGPT against a human result of 92.96%, and contains neither of the source's two figures, so the source is describing a later system whose paper it does not name. Until that paper is named and read, the repair loop's effect here is published as MEAS-AI-8 rather than validated against an external number.
17. **The grounding-checker figure in E26(f).** The source cites a production team measuring source hallucinations falling from 10% to zero, naming no publisher, no system, and no measurement protocol. There is nothing to retrieve. The layer keeps its structural argument, CONF-AI-7 keeps its regression corpus, and no external rate is claimed anywhere in the repository.
18. **The M3 reference behind VAL-GATE AI-2.** The gate compares twinflow's Theta implementation against `statsforecast` 2.1.1, which is an external published implementation but not the competition's published result. The M3 competition's own sMAPE for Theta sits in Makridakis and Hibon's published account of that competition, which has not been read here. Transcribing that figure with its edition and table locator would let the gate check the method against the competition, not only against one library.
19. **What external benchmark would promote MEAS-AI-1 and MEAS-AI-2 to gates?** Effect recovery and structure recovery are both scored against truth this repository generates, so a threshold on either would be self-referential, and D-11 forbids recording such a statistic as a passing gate. A published causal benchmark with distributed data and known interventional effects would change that. Which benchmark, and whether its data license permits use here, is unresolved.
