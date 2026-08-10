---
title: "Repo craft: CI, gates, hooks, security, releases, docs, adoption"
description: Specifies the workspace, lint rules, validation gates, hooks, release flow, and adoption model that enforce every other design section.
topic_type: reference
audience: contributors
---

# Repo craft: CI, gates, hooks, security, releases, docs, adoption

This section is the implementation contract for the machinery that judges every other section.
Each gate named below blocks a merge, blocks a release, or blocks a phase from closing, and each
one has a test that proves the gate itself can fail.

Doctrine rulings applied in this section, cited at each point of use: D-01 (hashed core against
provenance sidecar), D-02 (where a wall clock may be read), D-05 (the two-tier determinism claim),
D-07 (the event envelope), D-09 (one owner per public symbol), D-10 (heavy dependencies are
optional extras), D-11 (validation gates carry real external evidence), D-12 (a test that cannot
fail is not a test), D-13 (timing tests scoped to fit their budget), and D-14 (twinflow builds its
own process mining). Where this section disagreed with a ruling, the ruling won and the text below
changed.

Every external source cited below was retrieved on 2026-08-09 with its HTTP status recorded. A
statistic whose reference could not be retrieved is attributed to its publisher in the sentence
that uses it, and a statistic with no valid external reference is an open question in section 9,
never a passing gate. That is D-11 condition 5 applied to this section's own prose.

## 1. Scope

Requirement numbers owned in full by this section:

| Number | Requirement                                                                                                                                                                                                  | Where covered       |
| ------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ | ------------------- |
| C4     | Test tiers: fast unit, property-based invariant suite, seeded end-to-end scenarios with golden-file comparison of the capability report, VSM, and financial statements, each tier with a runtime budget      | 5.3, 7.1, 7.2, 7.3  |
| C6     | Versioned historian migrations, config upgrader command, CHANGELOG compatibility table stating which recorded runs and configs each release loads                                                            | 2.3, 5.6, 6.4, 7.6  |
| C7     | SECURITY.md with private disclosure channel, supported versions, threat-model note for the MCP/REST surface documenting the SQL/Python sandbox boundary                                                      | 5.8                 |
| C8     | CONTRIBUTING.md, code of conduct, one-paragraph governance note                                                                                                                                              | 5.9                 |
| C9     | Semver policy across package APIs, REST/MCP contracts, event schemas, facility.yaml; lockstep versions across bricks; automated releases that tag, changelog, build, and publish every brick to PyPI from CI | 5.10, 5.11          |
| C10    | uv workspace, justfile as single task entry point, CI matrix over Python versions plus the Rust agent, path-filtered jobs, stated CI wall-time budget                                                        | 5.1, 5.2, 5.4       |
| C11    | pip-audit / cargo-audit in CI, licence allowlist compatible with the outbound licence, SBOM per release, model and dataset licences recorded in the E25 dataset cards                                        | 5.12, 6.5, 7.7      |
| A4     | Published scaling evidence: load-test harness, reproducible device-vs-throughput-vs-latency curves on stated hardware, documented backpressure, honest knee of the curve                                     | 2.4, 5.13, 6.6, 7.8 |
| A5     | ADOPTION.md as a consulting maturity model mapping Industry 3.0-to-5.0 stages to module adoption order and each stage's payback                                                                              | 5.14, 6.7           |

Requirement fragments owned here that live inside other numbered items:

| Fragment                                                                                                                                  | Source                                                                                | Where covered             |
| ----------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------- | ------------------------- |
| The VAL-GATE registry as a first-class CI artifact; no phase closes until its statistics validate against their named published reference | Component 5 validation requirement, plus the constraints paragraph's phase discipline | 2.1, 5.5, 7.4             |
| Nondeterminism CI lint banning time / random / socket calls outside the kernel package, with an annotation escape hatch                   | Locked architecture decision backing C1                                               | 2.5, 5.7, 7.5             |
| Repeated-run hash check asserting determinism                                                                                             | C1                                                                                    | 5.7, 7.5                  |
| CI producer/consumer contract tests on the /schemas registry; additive-only evolution within a major version                              | C3                                                                                    | 5.4 job `contracts`, 7.9  |
| Config validation at load with a validate command and dry-run mode, exercised in CI                                                       | C5                                                                                    | 5.4 job `static`, 6.4     |
| Independently installable packages, each with its own README, tests, and pip install path; the "use just this part" table                 | A1                                                                                    | 2, 5.11, 5.15, 7.10       |
| Docs site (mkdocs-material) once the README outgrows one screen                                                                           | Quality-bar paragraph                                                                 | 5.15                      |
| Tagged releases with a CHANGELOG per phase                                                                                                | Quality-bar paragraph                                                                 | 5.11                      |
| GitHub Issues used as the public face of ROADMAP.md                                                                                       | Quality-bar paragraph, constraints paragraph                                          | 5.16                      |
| A natural commit history that tells the story of the build                                                                                | Quality-bar paragraph                                                                 | 5.17, 5.18                |
| Git hooks (inherited private-monorepo conventions, adapted)                                                                               | Author's inherited tooling                                                            | 5.17                      |
| GitHub Actions CI running tests and lint; conventional commits; Apache-2.0 licence with a commercial option and a contributor agreement   | Constraints paragraph                                                                 | 5.4, 5.17                 |
| Passing CI badge, five-minute quickstart intact every phase                                                                               | Quality-bar paragraph, constraints paragraph                                          | 5.4, 7.3                  |
| Release tag creation, so all four C9 verbs (tag, changelog, build, publish) are automated                                                 | C9                                                                                    | 5.11, 7.6                 |
| Comment judge: the nine comment rules, their CI equivalent, and their hook test                                                           | Author's inherited tooling                                                            | 5.17, 5.19, 7.11          |
| Dashboard accessibility gate wired into CI                                                                                                | C12 (dashboard section owns the implementation)                                       | 5.4 job `a11y`            |
| Model and dataset licence fields inside dataset cards                                                                                     | E25 (data-products section owns the card content)                                     | 6.5, 7.7                  |
| Agent eval suite and AI red-team suite scored in CI next to each other                                                                    | E27, E43 (agent section owns the suites)                                              | 5.4 nightly               |
| Public-repo CI policy override resolving the private-monorepo conflict                                                                    | Explicit brief instruction                                                            | 5.0                       |
| Fully local, no cloud account, one optional environment variable for a hosted model                                                       | Constraints paragraph                                                                 | 5.4 job `quickstart`, 7.3 |
| The outbound licence forces the process-mining engine to be built here rather than imported (D-14)                                        | C11 read against the locked process-mining decision                                   | 5.12, 7.7, 9              |
| Fully synthetic data, zero client or employer artifacts, enforced rather than promised                                                    | Constraints paragraph, IP hygiene rule                                                | 5.17, 7.11                |

Requirement numbers referenced but owned elsewhere: C1 (kernel section owns the splittable RNG and
clock), C2 (kernel), C3 (schemas section owns the registry contents), C5 (config section owns the
loader), C12 (dashboard), E1 (replay section owns the viewer; this section owns its deploy job),
E2 (MCP surface), E25 (dataset card content), E26 (agent accuracy stack; this section owns the
sandbox boundary statement in SECURITY.md), E27, E43, A1 (package topology decided in Phase 0 by
the architecture section; this section enforces it), A2, A3, A6.

## 2. Packages

Five publishable bricks are owned by this section, alongside one unpublished tools tree. The
workspace holds eighteen bricks in total (5.1); the other thirteen belong to the sections that
specify them. Every brick installs alone with `pip install twinflow-<name>` and carries its own
README with an executable example.

The boundary rule, stated exactly, because an absolute version of it is false two subsections
later and a reviewer will find the counterexample:

1. Cross-brick **data** is a versioned schema'd record, per C3. No brick reads another brick's
   in-memory objects across a process boundary.
2. Cross-brick **code** dependencies are permitted, must be declared in the importing package's
   `pyproject.toml`, and are linted (`TFB002`). `twinflow-loadtest` declaring the twinflow
   historian read client as an extra is the worked example.
3. Importing another brick's private submodule path (`twinflow.lss._internal.*`) is always a
   violation (`TFB001`), in every direction, with no declaration that makes it legal.

Per D-10, a brick's core install stays minimal and any dependency heavy enough to change that
answer ships as an extra. Each brick below states its core dependency set and its extras
separately, and 7.10 installs each brick alone in a clean environment and imports it, so the
claim is tested rather than asserted.

### 2.1 `twinflow-valgate`

Purpose: declare, run, and publish validation gates that bind a computed statistic to a named
published reference. It is the mechanism behind the non-negotiable validation requirement in
component 5 and behind the phase-closure rule.

Public API:

```python
from twinflow.valgate import (
    val_gate,          # decorator, registers and marks a pytest test
    Reference,         # external published source
    SelfReference,     # the twin is the ground truth (process mining, causal recovery)
    Tolerance,         # absolute | relative | lre | coverage
    GateClass,         # REFERENCE | GROUND_TRUTH | META
    Registry,          # load, query, render
    PhaseSet,          # phases.yaml model
    record_measurement # called inside a gate body to log measured vs expected
)

Registry.load(root: Path) -> Registry
Registry.results(run_id: str) -> list[GateResult]
Registry.render_markdown() -> str
Registry.render_json() -> dict
Registry.badge_endpoint() -> dict           # shields.io endpoint payload
Registry.counts() -> GateCounts             # passing, failing, pending_reference, total
Registry.assert_phase_closure(phases: PhaseSet) -> None
Registry.assert_bidirectional(phases: PhaseSet) -> None
```

CLI: `twinflow-valgate check | render | badge | phase-closure | list --phase P2 --status FAIL`.

Pytest plugin entry point `twinflow_valgate.plugin` registers the `val_gate` marker, collects
measurements, and writes `artifacts/ci/val-gates.json` plus a GitHub step-summary table.

Core dependencies: `pytest`, `pydantic`, `tomli`. No extras. It never imports the LSS engine, so a
reader who wants only the gate mechanism for their own statistical library gets it.

Timing note: `GateResult.duration_s` is measured with `time.perf_counter`, which rule TFD001 bans
inside package source. `twinflow-valgate` is one of the three packages holding a
`[measurement_boundary]` allowance in 5.7, and the measured value is written only to the gate
report. It never enters an event payload, a hashed tape, or a control decision, which is what
D-02 requires of a legal wall-clock read.

### 2.2 `twinflow-testkit`

Purpose: the C4 tier machinery. Hypothesis strategies over twinflow's own data shapes, the named
invariant predicates, the golden-file comparator with declared normalisers, and the tier budget
plugin.

Public API:

All twenty-four named invariants in 5.3 are testkit predicates. Each takes plain mappings,
sequences, or dataclasses, never a twinflow domain object, so the brick is usable against any
simulation and needs no twinflow runtime dependency. Three of them (`spc_affine_invariance`,
`capability_ordering`, `digest_equality`) are predicates over records that the owning engine has
already computed, which is what keeps `twinflow-testkit` from importing `twinflow-lss` and what
keeps the A1 brick-isolation test in 7.10 passing on the first release.

```python
from twinflow.testkit import invariants, strategies, golden, budgets

# INV-MASS-01..03
invariants.material_conservation(snapshot, *, tol=0)            -> None | raises InvariantError
invariants.no_negative_inventory(snapshot)                      -> None | raises
invariants.transform_mass_balance(steps, *, rel_tol=1e-9)       -> None | raises
# INV-LEDGER-01..04
invariants.ledger_balance(postings)                             -> None | raises
invariants.accounting_identity(close_records)                   -> None | raises
invariants.cash_continuity(periods)                             -> None | raises
invariants.variance_closure(decomposition)                      -> None | raises
# INV-GEN-01..03
invariants.genealogy_closure(graph)                             -> None | raises
invariants.recall_closure(graph, lot_id, blast_radius)          -> None | raises
invariants.quantity_conservation(graph, *, rel_tol=1e-9)        -> None | raises
# INV-CLOCK-01..03
invariants.monotone_clock(events, *, per_publisher=True)        -> None | raises
invariants.causal_order(events)                                 -> None | raises
invariants.drift_bookkeeping(device_events, corrected_events)   -> None | raises
# INV-DET-01: a predicate over two digests the caller produced, so testkit never runs a simulation
invariants.digest_equality(digest_a: str, digest_b: str, *, context: str) -> None | raises
# INV-NET-01, INV-SCHEMA-01, INV-QUEUE-01
invariants.delivery_idempotence(sent, applied)                  -> None | raises
invariants.schema_roundtrip(record, schema)                     -> None | raises
invariants.work_conservation(queue_events, horizon)             -> None | raises
# INV-SPC-01 and INV-CAP-01: predicates over computed chart and capability records
invariants.spc_affine_invariance(base: ChartResult, transformed: ChartResult, a: float, b: float) -> None | raises
invariants.capability_ordering(capability: Mapping[str, float])  -> None | raises
# INV-ENERGY-01, INV-CARBON-01, INV-ORDER-01, INV-ALARM-01, INV-FIND-01
invariants.energy_partition(assets, window)                     -> None | raises
invariants.carbon_conservation(genealogy, tol=1e-9)             -> None | raises
invariants.order_state_machine(order_events, table)             -> None | raises
invariants.alarm_floor(findings, shelved)                       -> None | raises
invariants.finding_provenance(findings, event_index)            -> None | raises

invariants.CATALOGUE: Mapping[str, Callable]   # INV id -> predicate, exactly 24 entries

strategies.facility_configs(profile="micro"|"3pl"|"enterprise") -> SearchStrategy
strategies.event_streams(kinds=..., horizon=...)                -> SearchStrategy
strategies.lot_graphs(depth=..., fanout=...)                    -> SearchStrategy
strategies.measurement_studies(parts=..., operators=..., trials=...) -> SearchStrategy

golden.compare(actual: Path, expected: Path, normaliser: str, tolerance: Tolerance) -> Diff
golden.update(actual: Path, expected: Path, normaliser: str, reason: str) -> None
golden.register_normaliser(name: str, fn: Callable[[bytes], bytes]) -> None

budgets.tier(name) -> TierSpec       # marker, budget_s, hard_fail_ratio, scope
```

`ChartResult` and the capability mapping are plain typed mappings defined in
`twinflow-schemas`, the leaf schema package, and re-exported by testkit. Per D-09 the owning
package is `twinflow-schemas` and testkit imports rather than redeclares them.

CLI: `twinflow-testkit golden-diff <actual> <expected> --normaliser capability_report`.

Core dependencies: `hypothesis`, `pytest`, `pydantic`, `twinflow-schemas`. No extras.

Test-dependency licence note. Hypothesis publishes `license_expression: MPL-2.0` at version
6.165.2, read from the Python Package Index JSON API at
`https://pypi.org/pypi/hypothesis/json` on 2026-08-09, HTTP 200. MPL-2.0 is file-level copyleft,
it sits in the `allow` list in 6.5, and it enters the product only as a test and development <!-- docs-lint-ok STE-TERM-WORD allow is the literal key name in licenses.allow.toml -->
dependency. The licence policy permits the library C4 names, and LIC-GATE-01 checks that rather
than assuming it.

Timing note: the tier budget plugin measures per-test duration with `time.perf_counter`, which
TFD001 bans in package source. `twinflow-testkit` holds a `[measurement_boundary]` allowance in
5.7 for TFD001 only, and the measured value reaches the tier report and nothing else.

### 2.3 `twinflow-migrate`

Purpose: C6. Versioned historian migrations across three storage backends, a config upgrader that
preserves comments, and the generator for the CHANGELOG compatibility table.

Public API:

```python
from twinflow.migrate import (
    HistorianMigrator, ConfigUpgrader, ConfigMigration,
    CompatibilityTable, RunBundleReader, MigrationError,
)

HistorianMigrator(backend: "duckdb"|"postgres"|"delta", dsn: str)
  .status() -> MigrationStatus
  .plan(to: str | None) -> list[Migration]
  .apply(to: str | None, dry_run: bool = False) -> list[MigrationApplied]

ConfigUpgrader.for_kind("facility"|"catalog"|"metrics"|"spec_limits")
  .plan(doc, to: str) -> list[ConfigMigration]
  .upgrade(doc, to: str) -> UpgradeResult   # carries new doc, diff, applied ids
  .check(path, to: str) -> bool             # CI mode, no writes

CompatibilityTable.build(releases: list[str]) -> CompatibilityTable
CompatibilityTable.render_markdown() -> str
```

CLI:

```
twinflow-migrate historian status|plan|apply [--to VERSION] [--dry-run]
twinflow-migrate config upgrade <path> --to VERSION [--check | --write] [--diff]
twinflow-migrate compat-table --out docs/compatibility.md
twinflow-migrate verify-fixtures --dir tests/fixtures/compat
```

Core dependencies: `pydantic`, `ruamel.yaml`. Backend drivers are extras: `[duckdb]`,
`[postgres]`, `[delta]`. Installing the brick bare gives the config upgrader with no database
dependency, which is the piece a reader is most likely to want alone. This is the D-10 pattern:
`HistorianMigrator` is typed against a narrow structural protocol and the concrete driver types
are imported only under `TYPE_CHECKING`, so the bare install imports cleanly.

### 2.4 `twinflow-loadtest`

Purpose: A4. Drive N simulated devices through the real broker and the real ingest path, measure
throughput and end-to-end latency, find and publish the knee, and regression-gate it.

Public API:

```python
from twinflow.loadtest import LoadProfile, HardwareProfile, Harness, ScalingReport, Knee

Harness(profile: LoadProfile, hardware: HardwareProfile, sink: Path)
  .run() -> ScalingReport
ScalingReport.samples -> list[LoadSample]
ScalingReport.knee(criterion="p99_latency_ms>1000") -> Knee
ScalingReport.to_csv(path) / .to_json(path)
ScalingReport.plot(path: Path, theme="light"|"dark") -> None
Knee.regression_against(baseline: Path, tolerance: float) -> GateResult
```

CLI:

```
twinflow-loadtest run --profile ramp-devices --hardware ref-a --out artifacts/loadtest/
twinflow-loadtest plot --in artifacts/loadtest --out docs/assets/scaling
twinflow-loadtest gate --baseline benchmarks/baseline.json --tolerance 0.15
```

Core dependencies: `pydantic` and `numpy`. Extras: `[broker]` pulls `aiomqtt`, `[historian]` pulls
the twinflow historian read client, `[plot]` pulls the charting stack. The bare install computes
percentiles and knees from a recorded sample file, which is the piece a reader can use against
their own harness. Driving a real broker needs `[broker]`, per D-10.

In simulation mode the harness drives the in-memory network instead of a broker, which is how its
own accuracy is tested (7.8).

Timing note: A4 measures end-to-end latency in wall time by construction, so `twinflow-loadtest`
holds `[measurement_boundary]` allowances for TFD001 and TFD003. Each allowance is bounded in
5.7 and 6.1 by path and by rule, the harness runs only in production mode, and its samples are
measurement records rather than simulation tape events. This is the observability-exporter
allowance in D-02.

### 2.5 `twinflow-repolint`

Purpose: the nondeterminism lint that keeps the CLOCK / RNG / NETWORK / STORAGE seam intact, plus
two adjacent structural lints that have the same shape (kernel-boundary enforcement and package
import-boundary enforcement).

Public API:

```python
from twinflow.repolint import check_paths, Config, Violation, Rule

check_paths(paths: Iterable[Path], config: Config) -> list[Violation]
Config.load(path: Path = Path("repolint.toml")) -> Config
```

CLI: `twinflow-repolint check [PATHS] --config repolint.toml --format github|text|json`,
`twinflow-repolint escapes --list [--json]`, `twinflow-repolint allowlist --print`.

Core dependencies: stdlib `ast` and `tomli` only. No extras, no third-party runtime dependency,
because it runs in a pre-commit hook where install weight is felt.

What that dependency budget costs, stated rather than hidden. An `ast`-only checker decides
syntactic facts about one module at a time. It cannot decide interprocedural taint questions such
as "is this path derived from the STORAGE interface" or "does this set's iteration order reach an
output". Rules TFD003, TFD004, and TFD006 are written in 5.7 as conservative syntactic
approximations, each with a stated list of what it misses, and the determinism hash check
(DET-GATE-01) is the backstop for what the approximations let through. A lint that claims more
reach than its checker has is worse than no lint, because a reader trusts it.

### 2.6 `tools/` (not published)

Repo-local scripts that are not library code and have no adoption story:
`tools/hooks/` (the git hooks, mirrored from the author's private monorepo and adapted),
`tools/ci-local.sh` (the zero-cost local CI mirror), `tools/roadmap_sync.py`,
`tools/reference_provenance.py`, `tools/ip_hygiene.py`, `tools/readme_examples.py`,
`tools/ci_budget.py`, `tools/arch_table_check.py`.

## 3. Domain model

### 3.1 ValGate

| Field                   | Type                          | Notes                                                          |
| ----------------------- | ----------------------------- | -------------------------------------------------------------- |
| `id`                    | str                           | Pattern `VAL-[A-Z]{2,8}-\d{3}`. Immutable once published.      |
| `title`                 | str                           | One line, states what is being validated against what.         |
| `gate_class`            | GateClass                     | `REFERENCE`, `GROUND_TRUTH`, or `META`.                        |
| `requirement_ids`       | list[str]                     | Component / E / C / A numbers this gate proves. Non-empty.     |
| `phase`                 | str                           | Phase id from `phases.yaml`.                                   |
| `reference`             | Reference or SelfReference    | Required. `None` is a registration error.                      |
| `external_anchor`       | Reference, optional           | Required when `gate_class` is `GROUND_TRUTH`. See D-11 below.  |
| `tolerance`             | Tolerance                     | Required.                                                      |
| `noise_floor`           | NoiseFloor, optional          | Required when the measured quantity is stochastic.             |
| `falsifies_on`          | str                           | Non-empty prose naming the observation that fails this gate.   |
| `dataset`               | Path, optional                | Fixture under `tests/fixtures/reference/` for REFERENCE gates. |
| `status`                | GateStatus                    | Set at run time. See the status enum below.                    |
| `measured` / `expected` | dict[str, float]              | Keyed by the quantity name.                                    |
| `deviation`             | dict[str, float]              | Computed by the tolerance kind.                                |
| `duration_s`            | float                         | For the tier budget report.                                    |

`GateStatus` is `PASS`, `FAIL`, `ERROR`, `SKIP`, or `PENDING_REFERENCE`. The last value exists
because D-11 condition 5 forbids recording a statistic with no valid external reference as a
passing gate, and because deleting the gate instead would delete a requirement. A
`PENDING_REFERENCE` gate is declared, counted in the registry total, listed in section 9, blocks
the closure of the phase it is assigned to, and is never counted as passing.

`NoiseFloor(kind: "binomial"|"bootstrap"|"replicate_sd", replicates: int, value: float, derivation: str)`
records how the floor was obtained. `derivation` is the arithmetic or the measurement procedure,
written out, so a reader can check it.

Invariants:

- INV-VG-01: a REFERENCE gate has a `Reference` with non-empty `name`, `section`, and `url`, a
  `retrieved` date, and a `dataset` that exists and is listed in
  `tests/fixtures/reference/SOURCES.md`. The `section` must be a leaf locator that resolves to one
  page of the cited work, not a chapter.
- INV-VG-02: a GROUND_TRUTH gate has a `SelfReference` whose `ground_truth_construction` field is
  a non-empty prose description of how truth is generated, and an `external_anchor` naming the
  published algorithm, published guarantee, or external oracle implementation that sets the
  threshold. D-11 condition 1 says this repository is never a reference for itself, so a
  GROUND_TRUTH gate whose threshold rests on nothing but this repository is a registration error
  and is recorded as `PENDING_REFERENCE`.
- INV-VG-03: `id` is unique across the registry.
- INV-VG-04: every id in `phases.yaml.val_gates` resolves to a declared gate, and every declared
  gate's `phase` appears in `phases.yaml`. Bidirectional, both directions fatal.
- INV-VG-05: `status == PASS` implies every entry in `deviation` is within `tolerance`.
- INV-VG-06: `falsifies_on` is non-empty for every gate. D-12 requires every test to state the
  observation that would fail it, and a gate whose failure condition cannot be described is not a
  gate.
- INV-VG-07: when `noise_floor` is set, `tolerance.value >= noise_floor.value`. D-11 condition 3
  forbids a tolerance tighter than the Monte Carlo noise of the experiment that produces the
  number. Registration fails with both values printed.
- INV-VG-08: `tolerance` is never tighter than the printed precision of the value it checks. A
  REFERENCE gate records `expected_precision` per quantity (the number of decimal places or
  significant digits the source prints) and registration fails if the tolerance implies more
  digits than the source published. This is D-11 condition 2, mechanised.

### 3.2 Reference and SelfReference

`Reference(name, edition, section, url, retrieved: date, http_status: int, rights: "public-domain"|"cited-excerpt"|"permissive", redistributable: bool, printed_precision: dict[str, int])`.

`edition` carries the edition, version, or publication year, because a locator without an edition
points at a moving target. `http_status` records the status code observed when the URL was last
retrieved, so a source that has since become unreachable is visible in the registry rather than
implied to be fine. `printed_precision` maps each quantity name to the number of decimal places or
significant digits the source prints, which is what INV-VG-08 checks the tolerance against.

`SelfReference(ground_truth_construction: str, replicates: int | None, seed: int | None, external_anchor: Reference)`.

A `SelfReference` carries an `external_anchor` for the reason D-11 gives: the twin may be the
source of the data, and it may never be the source of the standard the data is judged against.
The anchor is a published algorithm, a published guarantee, or an external oracle implementation
that is compared against in CI without being distributed.

Invariant INV-REF-01: `redistributable is False` implies the committed fixture contains only the
numeric data needed to reproduce the example, never prose or layout from the source, and
`SOURCES.md` records the citation. This is the rule that lets Minitab documentation examples be
encoded and cited without bulk redistribution.

### 3.3 Tolerance

`Tolerance(kind, value, applies_to: list[str], per_quantity: dict[str, float] | None = None)`.

`per_quantity` exists because one published table often prints its quantities to different
precisions. Where it is set, its entry overrides `value` for that quantity name, and INV-VG-08
checks each quantity against its own `printed_precision`. The individuals-chart gate in 5.5 is the
worked case: the cited page prints the upper and lower limits to four decimal places and the
centre line to two, so a single tolerance cannot be right for all three.

`kind` is one of:

- `absolute`: `abs(measured - expected) <= value`.
- `relative`: `abs(measured - expected) <= value * abs(expected)`.
- `lre`: log relative error `-log10(abs(measured - expected) / abs(expected)) >= value`. The
  metric is not NIST's. It is McCullough's, defined in "Assessing the Reliability of Statistical
  Software: Part I", The American Statistician 52(4), 358-366 (1998), DOI
  10.1080/00031305.1998.10480597, which is the paper that established scoring a package against
  the NIST StRD certified values by counting correct significant digits. NIST StRD publishes the
  certified values; the scoring rule applied to them is cited to its own author.
- `coverage`: empirical coverage of a nominal interval falls inside `[nominal - value, nominal + value]`
  over `replicates` seeded runs. A `coverage` tolerance always carries a `NoiseFloor` of kind
  `binomial`, whose value is `3 * sqrt(nominal * (1 - nominal) / replicates)`. INV-VG-07 then
  refuses any coverage tolerance tighter than the sampling noise of its own experiment, which is
  the defect D-11 condition 3 names.

### 3.4 Phase

`Phase(id, title, status: planned|open|closed, order: int, depends_on: list[str], val_gates: list[str], no_gates_justification: str | None, exit_criteria: list[str], declared_tag: str | None, changelog_section: str | None, tag_observed: bool)`.

Invariants:

- INV-PH-01: `status == closed` implies every id in `val_gates` resolves and its last recorded
  status is PASS. A gate at `PENDING_REFERENCE` is not PASS, so it blocks closure.
- INV-PH-02: `val_gates == []` implies `no_gates_justification` is non-empty. A phase can never
  silently have zero gates.
- INV-PH-03: `status == closed` implies every phase in `depends_on` is closed.
- INV-PH-04a, checked by the closure pull request: `status == closed` implies `declared_tag`
  matches `^v\d+\.\d+\.\d+$`, equals the contents of `VERSION`, and `changelog_section` exists as a
  heading in CHANGELOG.md.
- INV-PH-04b, checked by `release.yml` after the tag is pushed: for every phase with
  `status == closed`, `declared_tag` resolves to a real annotated git tag whose commit is an
  ancestor of the release commit, and the workflow sets `tag_observed: true` in the same run.
  The split exists because the tag is created after the closure pull request merges, so a single
  check that demands both at once can never pass. INV-PH-04a and INV-PH-04b together are the
  original invariant, sequenced correctly.
- INV-PH-05: phases are never removed from `phases.yaml`; `order` may change, the set may only
  grow. Enforced by comparing against the file at the previous release tag. Before the first
  release tag exists there is no previous file, so the baseline is the empty set, every current id
  satisfies the superset test trivially, and the tool prints
  `no previous release tag; baseline is empty` rather than passing silently. 7.6 has a fixture
  repository with no tags that asserts this path.

### 3.5 RoadmapMilestone

`RoadmapMilestone(id, title, requirement_ids, phase, order, depends_on, status: backlog|planned|in-progress|done, issue_number: int | None, rationale: str)`.

Invariant INV-RM-01: the set of ids at HEAD is a superset of the set of ids at the previous
release tag. Ideas are only ever reordered, never deleted. This encodes the constraints paragraph
mechanically rather than by good intentions. Before the first release tag the baseline is the
empty set and the check reports `no previous release tag; baseline is empty`, the same first-run
rule as INV-PH-05 and the schema-additivity diff in 7.9, so all three behave identically on run
one and all three have the same fixture test.

Invariant INV-RM-02: `issue_number` is set for every milestone with `status != backlog` once the
repo is public, and the Issue's title and labels match the milestone.

### 3.6 TestTier

`TestTier(id, marker, budget_s, hard_fail_ratio, scope_globs, parallelism)`.

Invariant INV-TT-01: every test in the suite carries exactly one tier marker. An unmarked test is
a collection error, not a silently-tier-0 test.

Invariant INV-TT-02: measured wall time for a tier <= `budget_s * hard_fail_ratio`.

### 3.7 GoldenArtifact

`GoldenArtifact(id, path, producer, normaliser, comparator, tolerance, owning_requirement)`.

Invariant INV-GA-01: `normalise(normalise(x)) == normalise(x)`.

Invariant INV-GA-02: normalising two runs that differ only in the declared volatile field set
yields byte-identical output. The volatile field set is exactly the provenance sidecar defined by
D-01, enumerated here so the normaliser and the manifest carve-out cannot drift apart:
`started_wall_utc`, `finished_wall_utc`, git sha and dirty flag, platform fingerprint, package
versions, host name, container digests, the clock compression factor, absolute paths, and the
twinflow version string. That list and the `run.manifest.sidecar.v1` field list in section 4 are
the same list, and a test compares them field by field rather than leaving a reader to check two
paragraphs against each other.

`run_id` is deliberately absent from that list. Per D-01 it is derived from the hashed core, so
two identical runs produce the same `run_id` and it is a stable field rather than a volatile one.
A `run_id` that differed between two identical runs would be a determinism defect, and the
golden comparator must fail rather than normalise it away. INV-GA-03 states the same rule from the
other side.

Invariant INV-GA-03: no identifier that the determinism contract requires to be stable appears in
any normaliser's volatile set. The set of stable identifiers is read from the run manifest schema,
so adding a volatile-looking field to the manifest hashed core cannot silently make it
normalisable. 7.4 has a fixture normaliser that tries to strip `run_id` and asserts the
registration fails.

### 3.8 Migration and CompatibilityRow

`Migration(kind: historian|delta|config, id, from_version, to_version, checksum, reversible: bool, description)`.

`CompatibilityRow(release, config_schema, catalog_schema, event_schema_major, historian_schema, run_bundle_format, reads_runs_from: list[str], reads_configs_from: list[str])`.

Invariant INV-MG-01: historian migration ids are strictly increasing and forward-only; a migration
file that changes after being applied in any released version is a checksum failure.
Invariant INV-MG-02: for every release in `reads_runs_from` there is a committed fixture run under
`tests/fixtures/compat/runs/` that opens.
Invariant INV-MG-03: for every release in `reads_configs_from` there is a committed fixture config
that the upgrader converts to the current version and that then validates.

### 3.9 LicensePolicy

`LicensePolicy(allow: list[SPDX], review: list[SPDX], deny: list[SPDX], exceptions: list[LicenseException])`, <!-- docs-lint-ok STE-TERM-WORD allow is a field name in the policy model -->
`LicenseException(package, version_spec, license, justification, approved_by, expires: date, linkage: "runtime"|"build"|"test"|"optional-extra")`.

Invariant INV-LP-01: no dependency resolves to a licence in `deny` without an unexpired exception.
Invariant INV-LP-02: an exception with `linkage == "runtime"` and a copyleft licence is refused by
the policy loader itself, so an expiring exception can never be the only thing standing between an
Apache-2.0 repo and a copyleft runtime dependency.
Invariant INV-LP-03: every exception has `expires` within 180 days of `approved_by` date.

### 3.10 HardwareProfile and ScalingRun

`HardwareProfile(id, cpu_class, physical_cores, logical_cores, ram_gb, storage_class, os, kernel, container_runtime, notes)`.

`LoadSample(device_count, offered_eps, achieved_eps, e2e_latency_ms_p50/p95/p99, broker_cpu_pct, broker_rss_mb, ingest_queue_depth_max, shed_total, buffer_bytes_max, duration_s, seed)`.

`Knee(criterion, device_count, achieved_eps, binding_resource, evidence)`.

Invariant INV-LT-01: `achieved_eps <= offered_eps` for every sample; a sample violating it means
the harness is double counting and the run is invalid.
Invariant INV-LT-02: `p50 <= p95 <= p99`.
Invariant INV-LT-03: a report with `shed_total > 0` and no recorded backpressure event is invalid;
shedding without an emitted backpressure record is an instrumentation bug, not a result.

### 3.11 MaturityStage

`MaturityStage(id, level: "3.0"|"3.2"|"3.5"|"4.0"|"4.5"|"5.0", order: int, name, entry_test: list[str], bricks: list[str], deployment_tier: "garage"|"growth"|"enterprise", payback_model: PaybackModel, prerequisites: list[str], failure_mode: str, adoptable: bool)`.

`PaybackModel(headline_metric, formula, units: dict[str, str], inputs: list[InputRef], worked_example_profile, synthetic_disclaimer: bool)`.

`units` maps every symbol in `formula`, and the result, to a unit string drawn from a closed set
(`usd`, `usd_per_year`, `usd_per_month`, `months`, `ratio`, `hours`, `count`). It exists so
INV-MS-04 can check the formula rather than trust it.

Invariant INV-MS-01, two tiers, because the one-tier version cannot hold on the phase where
ADOPTION.md first ships:

- INV-MS-01a: every brick named in a stage resolves to a declared milestone id in `roadmap.yaml`.
  A stage may never name a brick that nobody has committed to building.
- INV-MS-01b: `adoptable is True` implies every brick named in that stage exists in `packages/`
  and has published to PyPI at the current version. A stage whose bricks are not all published
  renders in ADOPTION.md with the heading suffix `(not yet adoptable)` and a line naming the
  milestone each missing brick waits on.

Invariant INV-MS-02: `synthetic_disclaimer is True` for every payback model, and the rendered
ADOPTION.md carries the disclaimer sentence once per stage. Payback numbers come from the twin
running the A2 profiles, not from any engagement.

Invariant INV-MS-03: a stage's `prerequisites` are stages of a lower or equal `level` with a
strictly lower `order`. Two stages may share a maturity level, because Industry 3.0 covers both an
uninstrumented operation and an instrumented one that nobody acts on; what may never happen is a
prerequisite that does not strictly precede its dependant. Skipping is described in
`failure_mode`, never silently permitted.

Invariant INV-MS-04: every payback formula is dimensionally consistent. The renderer evaluates the
formula symbolically against `units`, and a formula whose result unit differs from
`headline_metric`'s declared unit fails to load. A payback stated in months whose arithmetic
yields years is the failure this catches, and it is a failure a reader can spot in ten seconds,
which is why it gets a check rather than a proofread.

### 3.12 RepoLintRule and Escape

`RepoLintRule(code, title, banned_symbols: list[str], banned_node_kinds: list[str], allowed_paths: list[glob], approximation_note: str, severity)`.

`approximation_note` is non-empty for every rule whose stated intent is broader than an
`ast`-local check can decide. It says what the rule catches and what it misses, and 7.1 asserts it
is non-empty for TFD003, TFD004, and TFD006.

`Escape(path, line, rule_code, reason, added_in_commit)`.

`Allowance(rule_code, path_glob, justification, owning_requirement)` is the second exception
mechanism and is not the same thing as an escape. An escape is one annotated line. An allowance is
a reviewed path glob for one rule, declared in `repolint.toml`, and the complete set of allowances
is fixed and small (5.7). Escapes are counted against `max_escapes`; allowances are not, because
they are declared centrally rather than scattered.

Invariant INV-RL-01: an escape annotation without a non-empty `reason` is itself a violation.

Invariant INV-RL-02: `len(escapes) <= config.max_escapes`. The ceiling is committed, so escapes
can only increase through a deliberate reviewed bump.

Invariant INV-RL-03: the allowance set loaded from `repolint.toml` equals the allowance set
declared in 5.7, compared as a sorted list of `(rule_code, path_glob)` pairs. A unit test holds
the expected set literally, so adding an allowance requires editing the test, which is the review
step. Without this the escape ceiling of zero would be met by quietly widening the allowlist
instead, which is the outcome INV-RL-02 exists to prevent.

Invariant INV-RL-04: every allowance has a non-empty `justification` and an `owning_requirement`
that resolves to a requirement number this repository declares.

## 4. Events and records

This section produces artifact records rather than bus telemetry, with two exceptions that are
real runtime events written to the historian. Everything below has a JSON Schema in
`schemas/artifacts/` or `schemas/events/`, is versioned, and evolves additive-only within a major
version per C3.

Envelope conformance, per D-07. The two runtime events carry `producer_id`, their `seq` is dense
per `(run_id, producer_id)` rather than globally, and any reader of this section's records sorts
by the canonical total order `(sim_ts, producer_id, seq)`. The artifact records are not bus
events and carry no `seq`; they are keyed by `(run_id, artifact_id)`.

Wall-clock conformance, per D-02. Several artifact records below carry wall-derived fields
(`duration_s`, `wall_s`, `total_wall_s`, latency percentiles). Every one of them is written by
the observability and measurement path, which is one of the four legal wall-clock readers D-02
names. None of them enters an event payload on the simulation tape, none is hashed, and none
steers a control decision. The two runtime events carry no wall-derived field at all, which is
why `duration_s` on `historian.migration.applied` moved to the provenance sidecar; a unit test
named `test_runtime_events_carry_no_wall_derived_field` asserts the carve-out over the schemas in
`schemas/events/`, so the split cannot regress silently.

| Name                          | Version | Direction          | Shape (fields)                                                                                                                                                                                                                  | Consumed by                                                     |
| ----------------------------- | ------- | ------------------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | --------------------------------------------------------------- |
| `repo.val_gate.result`        | v1      | produced           | `run_id, gate_id, gate_class, phase, requirement_ids, status, measured{}, expected{}, deviation{}, tolerance{kind,value}, reference{name,section,url,retrieved,rights}, dataset, duration_s, git_sha, platform, python_version` | val-gates CI job, docs macro, badge endpoint, phase-closure job |
| `repo.ci.tier_summary`        | v1      | produced           | `run_id, tier_id, tests_run, passed, failed, skipped, wall_s, budget_s, over_budget: bool, slowest[{nodeid,duration_s}]`                                                                                                        | ci-budget job, docs macro                                       |
| `repo.ci.run_summary`         | v1      | produced           | `run_id, workflow, event, git_sha, jobs[{name,conclusion,duration_s}], total_wall_s, billable_s`                                                                                                                                | ci-budget job, docs macro                                       |
| `repo.loadtest.sample`        | v1      | produced           | as `LoadSample` in 3.10 plus `hardware_profile, topology, broker, seed, container_digests{}`                                                                                                                                    | historian, LSS engine control charts, scaling report            |
| `repo.loadtest.summary`       | v1      | produced           | `run_id, hardware_profile, topology, samples_ref, knee{criterion,device_count,achieved_eps,binding_resource}, baseline_ref, regression_pct`                                                                                     | A4-GATE-01, README macro, ADOPTION.md macro                     |
| `repo.golden.diff`            | v1      | produced           | `run_id, artifact_id, path, normaliser, changed: bool, first_divergence{line,field}, numeric_deltas[]`                                                                                                                          | e2e-golden job, PR annotation                                   |
| `historian.migration.applied` | v1      | produced (runtime) | `producer_id, seq, migration_id, kind, from_version, to_version, checksum, backend, rows_touched, sim_time_at_apply, operator`; `wall_time_at_apply` and `duration_s` are written to the provenance sidecar, not to this record | historian audit trail, 6a11 audit-trail integrity, compat table |
| `config.upgraded`             | v1      | produced (runtime) | `producer_id, seq, kind, path_hash, from_version, to_version, applied[{migration_id,description}], before_hash, after_hash, tool_version`                                                                                       | run manifest, replay reproducibility, compat table              |
| `repo.dataset_card`           | v1      | co-owned with E25  | this section requires `license (SPDX), license_url, redistributable, model_licenses[{model,base_model,license,source_url}], generation_seed, twinflow_version, config_hash, container_digests`                                  | LIC-GATE-02, release bundle                                     |
| `run.manifest.core`           | v1      | consumed           | requires `run_id, seed, config_hash, schema_snapshot_hash, scenario, mode, tick_rate, horizon, warmup, fault_schedule_hash`. This is D-01's hashed core and it is what `run_started` carries                                    | determinism gate, golden comparison, replay                     |
| `run.manifest.sidecar`        | v1      | consumed           | requires `run_id, started_wall_utc, finished_wall_utc, git_sha, git_dirty, platform, python_version, package_versions{}, host, container_digests{}, clock_compression`. Written to `manifest.json`, never into the hashed tape  | release notes, golden normaliser volatile set, provenance       |
| `finding`                     | v1      | consumed           | this section reads `severity` and `shelved` to assert INV-ALARM-01 in the property tier                                                                                                                                         | property tier                                                   |
| `gl.posting`                  | v1      | consumed           | this section reads `debit, credit, account, period` to assert INV-LEDGER-01/02                                                                                                                                                  | property tier, financial-statement golden                       |
| `genealogy.edge`              | v1      | consumed           | reads `parent_lot, child_lot, quantity, transform` to assert INV-GEN-01/02 and INV-CARBON-01                                                                                                                                    | property tier                                                   |

`run_id` in every record above is the derived value the kernel section defines: a content hash of
seed, config hash, schema snapshot hash, scenario, and mode, rendered as `run_` plus 26 Crockford
base32 characters. It is not a UUID, which is why TFD002's ban on `uuid.uuid4` costs this section
nothing. Two identical runs produce the same `run_id`, so it is neither a determinism leak nor an
unnormalised golden diff, and INV-GA-03 forbids any normaliser from stripping it. In production
mode, where a run is not required to be reproducible, `run_id` is a UUIDv7 produced inside the
kernel behind the RNG interface.

Schema evolution rule enforced by the `contracts` job: within a major version, a new field must be
optional with a default, no field may change type, no enum value may be removed, and no required
field may be added. The job compares the schema at HEAD with the schema at the last release tag
and fails on any of those. Before the first release tag the baseline is empty, the job reports
`no previous release tag; baseline is empty`, and it passes, which matches INV-PH-05 and
INV-RM-01. Removing anything requires a major bump, which by C9 is a lockstep major across every
brick.

## 5. Behaviour

### 5.0 Policy override: this repo pushes to origin and uses GitHub-hosted CI

The author's private monorepo carries two rules that must not travel to twinflow:

1. "Push policy: land work on LOCAL `main` only. NEVER push to origin."
2. A `ci-cost-guard` hook that blocks new GitHub-hosted workflows, cron triggers on them, and
   macOS runners, permitting only `runs-on: [self-hosted, superapp]`.

Both rules exist because that repo is private, where GitHub Actions minutes are metered and macOS
minutes bill at ten times the Linux rate, and because the owner controls origin pushes there.

twinflow is public and Apache-2.0, with a separately negotiated commercial licence available. The
quality bar in the source needs a passing CI badge, a natural commit history, tagged releases with
a CHANGELOG per phase, GitHub Issues as the public face of ROADMAP.md, a docs site, and a hosted
replay demo (E1) that anyone can open without installing anything. Not one of those exists without
pushing to origin and running GitHub-hosted workflows.

GitHub's billing documentation states that "GitHub Actions usage is free for self-hosted runners
and for public repositories that use standard GitHub-hosted runners" and that "Larger runners are
always charged for, even when used by public repositories or when you have quota available from
your plan". Read from
`https://docs.github.com/en/billing/managing-billing-for-your-products/about-billing-for-github-actions`
on 2026-08-09, HTTP 200. twinflow uses standard runners only, and a workflow that asks for a
larger runner fails the `static` job's workflow lint. The cost model that motivates the private
repository's guard does not apply here.

Resolution, stated plainly:

- twinflow overrides the local-main-only rule. Work is pushed to `origin/main` through pull
  requests, and the commit history is public from Phase 1 onward.
- twinflow overrides the ci-cost-guard. All workflows run on GitHub-hosted runners
  (`ubuntu-latest`, plus `windows-latest` and `macos-latest` in the nightly matrix).
  `.claude/hooks/ci-cost-guard.ps1` is deliberately not installed in this repo, and
  `docs/ci.md` says so, so the guard is never copied across by habit.
- The self-hosted runner is not used at all. On a public repository a self-hosted runner is a
  documented hazard: a pull request from a fork can execute arbitrary code on the runner host,
  which in this case is the machine holding the private monorepo. Using it would trade a cost risk
  for a compromise risk.
- Everything else from the private repo is retained. The local CI mirror (`tools/ci-local.sh`)
  stays, reframed from a cost guard to a latency guard. Its fast mode carries a stated budget of
  120 seconds on the `ref-a` hardware profile, it records its own elapsed time and its skipped
  check count to `artifacts/local/ci-local-timing.json`, and `pre-push` runs it. 5.18 states how
  that budget is measured and what happens when tools are missing, because an unmeasured latency
  claim is the same defect as an unmeasured throughput claim.

Fork-PR safety policy, which is the risk that replaces the cost risk on a public repo:

- Any workflow that runs fork-authored code triggers on `pull_request`, never
  `pull_request_target`.
- No secret is exposed to a fork PR job. Publishing uses PyPI Trusted Publishing (OIDC) inside a
  GitHub Environment named `pypi` that requires manual approval, so there is no long-lived token
  to leak.
- Every workflow declares `permissions: contents: read` at the top level; jobs that need more
  elevate individually and state why in a comment.
- `actions/checkout` is called with `persist-credentials: false` in every job that runs untrusted
  code.
- Every third-party action is pinned to a full 40-character commit SHA with a trailing comment
  naming the human-readable version. `actionlint` and `zizmor` run in the `static` job and fail on
  unpinned actions, on `pull_request_target` with a checkout of the PR head, and on script
  injection through `${{ github.event.* }}` in a `run:` block.
- Anything needing write access on a fork PR (labelling, the golden-diff comment) uses the
  `workflow_run` pattern with the untrusted output passed as an artifact, never interpolated into
  a shell.

Dependabot against that policy, stated because the two look like a conflict and are not. A
Dependabot pull request is raised from a branch inside this repository, not from a fork, so the
fork rules above do not govern it. What does govern it is the token: a `pull_request`-triggered
workflow run for Dependabot receives a read-only token and cannot approve or merge anything. The
mechanism, named rather than implied:

1. Repository setting "Allow auto-merge" is enabled. <!-- docs-lint-ok STE-TERM-WORD GitHub's own name for the setting -->
2. `automerge.yml` triggers on `workflow_run` for the completed `ci.yml` run, with
   `permissions: contents: write, pull-requests: write`.
3. The job exits unless the triggering run's `conclusion` is `success`, its `event` is
   `pull_request`, the pull request actor is `dependabot[bot]`, and the Dependabot metadata action
   reports `update-type: version-update:semver-patch`.
4. It then calls `gh pr merge --auto --merge` on that pull request number, read from the
   `workflow_run` payload and never interpolated into a shell string.
5. Branch protection still applies, so the merge waits for the `all-green` check regardless.

Minor and major dependency updates are never auto-merged. 7.11 has a fixture test for step 3's
predicate, including the case where the update type is minor and the job must decline.

### 5.1 Monorepo layout and uv workspace

```
twinflow/
  pyproject.toml                # [tool.uv.workspace] members = ["packages/*"]
  uv.lock                       # committed, single lock for the whole workspace
  justfile
  VERSION                       # single source of the lockstep version
  repolint.toml
  phases.yaml
  roadmap.yaml
  licenses.allow.toml           # docs-lint-ok STE-TERM-WORD literal filename
  mkdocs.yml
  packages/
    twinflow-kernel/            # CLOCK, RNG, NETWORK, STORAGE interfaces (kernel section)
    twinflow-schemas/           # /schemas registry loader (schemas section)
    twinflow-config/            # C5 loader (config section)
    twinflow-twin/  twinflow-sensors/  twinflow-uns/  twinflow-fleet/
    twinflow-lss/  twinflow-procmine/  twinflow-forecast/  twinflow-optimise/
    twinflow-agent/  twinflow-historian/  twinflow-dashboard/  twinflow-cli/
    twinflow-valgate/  twinflow-testkit/  twinflow-migrate/
    twinflow-loadtest/  twinflow-repolint/
  crates/
    twinflow-device-agent/      # the Rust device agent (component 2)
  schemas/
    events/  artifacts/  config/
  tests/
    fixtures/reference/         # published-reference datasets + SOURCES.md
    fixtures/compat/            # C6 fixture runs and configs per supported release
    goldens/                    # C4 tier-3 golden artifacts
  benchmarks/baseline.json
  adoption/maturity.yaml
  docs/
  tools/
  .github/workflows/
```

Package boundary rules, enforced by `twinflow-repolint` and matching the three-clause statement in
section 2. TFB002: a package may import another twinflow package's public root (`twinflow.lss`)
only if that dependency is declared in its `pyproject.toml`. TFB001: importing a private submodule
path (`twinflow.lss._internal.*`) from another package is always a violation, declared or not. A1
is a lint, not a promise.

Per D-09, every public symbol has exactly one owning package and other packages import it rather
than redeclaring it. A CI test walks the workspace import graph and fails on a cycle, and a second
asserts every name in each package's `__all__` is defined in that package. Shared value types that
would otherwise drag a heavy dependency downward live in `twinflow-schemas`, the leaf package, and
are re-exported.

### 5.2 justfile as the single task entry point

Every task a human or CI runs is a `just` recipe. CI calls the same recipes, so "works locally,
fails in CI" has one fewer cause.

```
just bootstrap        # uv sync --all-packages, then just hooks
just hooks            # sh tools/hooks/install.sh, then pre-commit install
just fmt              # ruff format, taplo fmt, cargo fmt
just fmt-check        # the check-only half, called by the pre-commit framework
just lint             # ruff check, ty, repolint, yamllint, codespell, actionlint, zizmor
just lint-staged      # the staged-file subset, called by the pre-commit framework
just test-unit        # tier 1
just test-prop        # tier 2
just test-e2e         # tier 3
just test-nightly     # tier 4
just test             # tiers 0..3, the pre-push set
just val-gates        # run marked gates, write artifacts/ci/val-gates.json
just phase-close P2   # assert gates green, then flip status in phases.yaml
just golden-update    # regenerate goldens, print the diff, need a reason
just determinism      # DET-GATE-01/02
just contracts        # C3 producer/consumer + schema-additivity diff
just audit            # pip-audit, cargo-audit, cargo-deny, licence allowlist
just sbom             # CycloneDX for python + rust
just docs             # mkdocs serve
just docs-build       # mkdocs build --strict
just loadtest ref-a   # A4 curve on a named hardware profile
just repeatability ref-a  # repeated knee runs that measure the A4 regression band
just procmine-oracle  # compare the owned miner against the development-only oracle (D-14)
just roadmap-sync     # regenerate ROADMAP.md and sync GitHub Issues
just release-prepare 0.4.0
just release-tag      # create and push the annotated tag from VERSION, after the release PR lands
just ci-local         # sh tools/ci-local.sh
just quickstart-check # the five-minute quickstart, exactly as README states it
```

`just --list` is the onboarding path in CONTRIBUTING.md.

The single-entry-point claim (C10) covers the pre-commit framework too. `pre-commit` is installed
by `just hooks` and every framework hook it runs is a `just` recipe: the ruff, taplo, yamllint, and
codespell hooks call `just fmt-check` and `just lint-staged` rather than invoking those tools
directly. One definition of each check, called from two places. `TASK-GATE-01` in the `static` job
parses `.pre-commit-config.yaml` and fails if any hook's `entry` is not a `just` recipe that
exists in the justfile, so the two entry points cannot drift apart. The one deliberate exception
is `pre-commit`'s own bootstrap, which cannot call `just` before `just` is installed, and
CONTRIBUTING.md says so.

### 5.3 Test tiers (C4)

Five tiers, numbered 0 to 4. C4 names three of them (unit, property, seeded end-to-end); tier 0
carries the static checks that gate the same pull request and tier 4 carries the soak and chaos
work that cannot fit a pull request. Each has a pytest marker, except tier 0, which is not pytest,
a stated budget, and a scope. Budgets are wall time on a standard GitHub-hosted `ubuntu-latest`
runner, measured with `-p xdist` at the stated parallelism.
GitHub documents that runner for public repositories as 4 CPU, 16 GB RAM, and 14 GB SSD on x64,
and states that "Use of the standard GitHub-hosted runners is free and unlimited on public
repositories" (read from `https://docs.github.com/en/actions/reference/runners/github-hosted-runners`
on 2026-08-09, HTTP 200).

| Tier       | Marker                  | Budget | Hard fail at | Parallelism | Scope                                                                                                 |
| ---------- | ----------------------- | ------ | ------------ | ----------- | ----------------------------------------------------------------------------------------------------- |
| 0 static   | (not pytest)            | 180 s  | 1.0x         | n/a         | format, lint, types, repolint, schema additivity, config validation, workflow lint                    |
| 1 unit     | `@pytest.mark.unit`     | 120 s  | 1.25x        | `-n auto`   | pure functions, no I/O, no broker, virtual clock only, no test over 200 ms                            |
| 2 property | `@pytest.mark.property` | 420 s  | 1.25x        | `-n auto`   | Hypothesis invariants over generated configs, event streams, lot graphs                               |
| 3 e2e      | `@pytest.mark.e2e`      | 420 s  | 1.2x         | `-n 4`      | seeded scenarios in simulation mode, golden comparison. The compose run lives in `quickstart`         |
| 4 nightly  | `@pytest.mark.nightly`  | 1800 s | 1.1x         | `-n auto`   | soak and chaos catalogue, per OS-and-Python cell. Load curves and agent scorecards have own workflows |

Tiers 2 and 3 are budgeted at 420 s each, and the garage-tier `docker compose` run sits in the
dedicated `quickstart` job rather than inside tier 3. Three reasons, all arithmetic against
BUDGET-GATE-02 below. First, the compose quickstart would otherwise be specified twice, once as a
tier and once as its own job, so the same three-hundred-second sequence would run twice per pull
request. Second, a tier whose budget times its hard-fail ratio plus the 45 s setup reserve exceeds
its job budget can never pass rule 2, and at 600 s the property tier needed 795 s inside a 600 s
job. Third, every per-job budget has to stay at or below the twelve-minute p95 wall-time target in
5.4. D-13 requires a timing claim to fit the budget its own document sets rather than to sit next
to a number that contradicts it, so the tier budgets moved rather than the claim.

Tier 4's budget is per matrix cell, not per workflow. The nightly matrix is three operating
systems times three Python versions, so a single per-workflow budget could never hold: nine cells
at even ten minutes each exceed an hour. 5.4 states the nightly per-cell budget of 35 minutes,
which is what 1800 s times the 1.1 hard-fail ratio plus the 45 s reserve needs.

Enforcement: the `twinflow-testkit` pytest plugin records per-test durations, writes
`repo.ci.tier_summary.v1`, and fails the session if tier wall time exceeds
`budget_s * hard_fail_ratio`. It also prints the ten slowest tests, so the fix is obvious. An
unmarked test is a collection error (INV-TT-01).

Budget arithmetic is itself checked (D-13). `BUDGET-GATE-02` asserts three inequalities before any
test runs, so a scenario that grows past its job budget fails as a defect rather than as a
timeout:

1. For every workflow, the largest single job budget is at or below that workflow's stated p95
   wall-time target. A job budgeted above the wall-time target cannot fit inside it under any
   scheduling.
2. For every job that runs a tier, `tier.budget_s * tier.hard_fail_ratio + 45` is at or below the
   job's budget in seconds. The 45 s covers checkout, environment setup, and artifact upload.
3. For the nightly and release workflows, the sum of every job budget in the workflow, counting
   each matrix cell as its own job, is at or below the workflow budget.

Worked against the numbers this section states, so a reader can check the gate rather than trust
it. Rule 2: static 180 x 1.00 + 45 = 225 <= 240; unit 120 x 1.25 + 45 = 195 <= 240; property
420 x 1.25 + 45 = 570 <= 600; e2e 420 x 1.20 + 45 = 549 <= 600; nightly cell 1800 x 1.10 + 45 =
2025 <= 2100. Rule 1: the largest pull-request job budget is 600 s, which is at or below the 720 s
p95 target. Rule 3: the nightly workflow is 9 cells at 2100 s plus 900 + 720 + 600 + 600 s of
single jobs, or 21720 s, at or below its 22200 s budget.

The gate reads `.github/ci-budget.yml`, the tier table in `pyproject.toml`, and the workflow
matrix definitions, so all three numbers have one home each and the check is over data rather than
over prose. Falsification: any one of the five rule-2 inequalities above evaluating false on the
committed data fails the gate and names which job and which tier.

Tier 1 detail. Unit tests never touch the historian, the broker, the filesystem outside `tmp_path`,
or wall time. `twinflow-repolint` rule TFD005 already bans `time.sleep` in package code; the plugin
also fails any unit test whose duration exceeds 200 ms, because a slow unit test is almost
always an accidental I/O test.

Tier 2 detail, the twenty-four named invariants. Each is a Hypothesis property with a stated
generator and a stated shrink target, and each is a `twinflow-testkit` predicate listed in
`invariants.CATALOGUE`. These are the actual invariants, not categories:

- INV-MASS-01 material conservation. For any generated facility config and any seeded run to a
  random horizon: `units_received == units_putaway + units_in_wip + units_scrapped + units_in_returns_hold + units_shipped - units_restocked_from_returns`, evaluated at every event boundary, exactly, in integer units. Generator: `strategies.facility_configs()` crossed with `strategies.event_streams()`. Shrinks to the smallest station count that breaks it.
- INV-MASS-02 no negative inventory. For every location and every sim instant, `on_hand >= 0` and `allocated <= on_hand + in_transit`.
- INV-MASS-03 mass through a transform. For any production step with a declared yield, `input_mass * yield == good_output_mass + scrap_mass` within 1e-9 relative, and scrap is always recorded, never implied by the difference.
- INV-LEDGER-01 double-entry balance. For every posting batch, `sum(debits) == sum(credits)` exactly in minor currency units (integers, never floats). For every period, the same holds cumulatively.
- INV-LEDGER-02 accounting identity. At every close event, `assets == liabilities + equity`.
- INV-LEDGER-03 cash continuity. `closing_cash == opening_cash + inflows - outflows` for every period, and the cash-flow statement's total ties to the balance-sheet cash delta.
- INV-LEDGER-04 variance decomposition closure (6a17). The sum of the named variances equals the total variance exactly; no residual bucket.
- INV-GEN-01 genealogy closure. The genealogy graph is a DAG. Every node has at least one path to a root, and every root is a supplier receipt or a raw-material issue. No cycles, no orphans.
- INV-GEN-02 recall closure. For any lot L, the blast radius returned by the recall query equals the exact set of nodes whose ancestor set contains L. Tested by generating a graph, computing the truth by brute-force transitive closure, and comparing.
- INV-GEN-03 quantity conservation across splits and merges. The sum of child quantities equals the parent quantity minus recorded scrap, within integer exactness for discrete units and 1e-9 relative for continuous batch mass.
- INV-CLOCK-01 monotone clock. For any single publisher, `sim_time` is non-decreasing across its emitted events. The global sim clock never decreases.
- INV-CLOCK-02 causal order. For any event E with a causation chain, `E.sim_time >= max(sim_time of every event in the chain)`.
- INV-CLOCK-03 clock-drift bookkeeping. A device with injected clock drift still emits monotone device-local timestamps, and the historian's recorded `sim_time` remains monotone after the drift correction is applied.
- INV-DET-01 determinism. Same seed plus same config yields the same event-log hash on the same platform and pinned dependency set, which is the byte-identical tier in D-05. Property form: for a generated config and a generated seed, two runs in separate processes hash equal. The repository's own test harness runs the two processes and passes the two digests to `invariants.digest_equality`, so the testkit predicate stays a comparison over records and the brick never imports a twinflow engine.
- INV-NET-01 delivery idempotence. Under any injected combination of partition, latency, reorder, and duplicate delivery from the simulation-mode network, the consumer's applied set equals the producer's sent set after reconnect and replay. This is the property form of 6c.
- INV-SCHEMA-01 round-trip. Every event record serialises and deserialises to an equal value, and a consumer pinned to schema major N reads a payload produced at any minor version of N.
- INV-QUEUE-01 work conservation. Every task that enters a resource queue leaves it or is accounted as WIP at the horizon. No task is silently dropped.
- INV-SPC-01 affine invariance. For I-MR and Xbar-R, transforming the data by `x -> a*x + b` with `a > 0` yields the same set of rule violations and limits transformed identically. The LSS engine computes both chart results; the testkit predicate compares the two result records, so this invariant does not make `twinflow-testkit` depend on `twinflow-lss`.
- INV-CAP-01 capability ordering. `Cpk <= Cp` always, with equality only when the process mean sits at the spec midpoint. Same for `Ppk <= Pp`. Again a predicate over a computed capability record, not over the engine that produced it.
- INV-ENERGY-01 energy partition. Total energy equals the sum over assets, and per asset the idle and running partitions are exhaustive and disjoint.
- INV-CARBON-01 carbon conservation (E17). Inherited kgCO2e is conserved through genealogy splits within 1e-9 relative.
- INV-ORDER-01 order state machine. Only transitions declared in the state table occur, and every order at the horizon sits in a terminal or a named exception state.
- INV-ALARM-01 alarm floor. Alarm rationalisation never shelves or dedupes away a finding at or above the safety severity floor. Generated finding storms of arbitrary composition still surface every safety finding.
- INV-FIND-01 finding provenance. Every finding carries a non-empty evidence window that resolves to real events in the historian.

Hypothesis configuration, chosen so a pull-request run is a function of its inputs and nothing
else. Profile `ci`: `max_examples=100`, `deadline=None` (the simulation runs are not latency
tests), `derandomize=False`, `database=None`, and an explicit `--hypothesis-seed=0`. Three
deliberate choices, each with its reason:

- `derandomize` and an explicit seed are mutually redundant, and setting both makes the seed inert
  while implying it matters. The seed is kept because it is visible on the command line, appears
  in the CI log, and reproduces the run locally; `derandomize` is dropped.
- The example database is disabled on pull-request runs. A cached database makes the executed
  example set depend on which examples failed in earlier runs, so two runs at the same commit can
  exercise different inputs. That contradicts C1's thesis that a run is a function of its inputs,
  and it makes a red build irreproducible in exactly the situation where reproducing it matters.
- Falsifying examples are not lost by disabling the cache. They are promoted into source: a
  nightly failure opens an Issue containing the falsifying example and the seed, and the example
  is committed to `tests/property/regressions/` as an `@example` decorator, which makes it a
  tier-1 test forever after. A reviewable file beats a cache directory nobody can inspect.

The nightly job runs profile `thorough` with `max_examples=1000`, a seed derived from the run date
and printed at the top of the log, and `database=None` for the same reason. `PROP-HYP-01` in 7.2
asserts that two `ci`-profile sessions at the same commit and seed execute the same example set,
which is the observation that would fail if either of the first two choices regressed.

Tier 3 detail, the golden files. Three golden artifact families, each with a declared normaliser:

| Golden id            | Producer                                       | Path                                                 | Normaliser                                                                                                                                                                                                                       | Comparator                                                    |
| -------------------- | ---------------------------------------------- | ---------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------- |
| `GOLD-CAP-<profile>` | `twinflow report capability --window ...`      | `tests/goldens/capability/<profile>.json` and `.txt` | `capability_report`: strip wall-clock, host, version, absolute paths; canonical JSON with sorted keys; floats to 12 significant digits; the HTML is reduced to a text projection of headings, table cells, and chart data series | field-wise, numeric fields relative 1e-9, string fields exact |
| `GOLD-VSM-<profile>` | `twinflow report vsm --state {current,future}` | `tests/goldens/vsm/<profile>.json` and `.svg.norm`   | `vsm`: JSON canonicalised; the SVG reduced to an ordered list of (element type, class, text, numeric attributes rounded to 3 dp) so layout jitter does not fail the test but a moved station does                                | field-wise, numeric relative 1e-9                             |
| `GOLD-FIN-<profile>` | `twinflow report financials --period ...`      | `tests/goldens/financials/<profile>/{pl,bs,cf}.csv`  | `financials`: integer minor currency units only, sorted by account code, period stamps replaced by ordinal index                                                                                                                 | exact equality, since money is integer                        |

Three profiles are golden-tested, matching A2: `micro` (one dock, three stations, no automation),
`3pl` (mid-market building), `enterprise` (full network). Each golden run is a fixed seed recorded
in `tests/goldens/manifest.yaml` alongside the config hash and the twinflow version that produced
it.

Each family declares the release at which it first exists, because a golden for an artifact the
code cannot yet produce is a failing test rather than a placeholder:

| Golden family | First produced at | Waiting on                                     | Profiles at that point |
| ------------- | ----------------- | ---------------------------------------------- | ---------------------- |
| `GOLD-CAP`    | v0.1.0            | the capability report stub                     | `micro`                |
| `GOLD-VSM`    | v0.6.0            | P3c process mining and the generated VSM       | all three              |
| `GOLD-FIN`    | v0.20.0           | 6a17's event-driven general ledger             | all three              |

`GOLD-CAP` widens from `micro` to all three profiles at v0.4.0, when the 3pl and enterprise
profiles are complete. The golden tier itself and its comparator exist from Phase 1; what grows is
the artifact set the tier compares. `tests/goldens/manifest.yaml` carries a `first_produced_at`
field per family and the tier-3 runner skips a family whose release has not arrived, reporting
`SKIP (not produced until v0.20.0)` rather than passing silently.

The normaliser volatile field set in the table above is the D-01 provenance sidecar, enumerated in
3.7. `run_id` is not in it and cannot be added, per INV-GA-03.

Golden update flow: `just golden-update` regenerates, prints the diff, and refuses to write unless
`--reason "..."` is given. The reason is written into `tests/goldens/manifest.yaml` next to the
artifact. A CI check `GOLDEN-GATE-01` fails any PR whose diff touches `tests/goldens/**` unless
the commit body contains a `GOLDEN` section heading (the commit-msg vocabulary already supports
ALL-CAPS headings) explaining the behavioural change. Silent golden churn is how a golden suite
stops meaning anything.

### 5.4 CI workflows, matrix, path filters, and wall-time budget (C10)

Workflow inventory. Every workflow declares `concurrency: group: ${{ github.workflow }}-${{ github.ref }}` with `cancel-in-progress: true` on PR refs.

**`ci.yml`** on `pull_request` and `push: main`.

`changes` job runs `dorny/paths-filter` and outputs booleans consumed by every downstream job's
`if:`. Filters, naming the jobs exactly as the job table below names them:

| Filter      | Paths                                      | Jobs unlocked                                              |
| ----------- | ------------------------------------------ | ---------------------------------------------------------- |
| `python`    | `packages/**`, `pyproject.toml`, `uv.lock` | `unit`, `property`, `e2e-golden`, `determinism`, `rust`\*  |
| `rust`      | `crates/**`, `Cargo.toml`, `Cargo.lock`    | `rust`                                                     |
| `schemas`   | `schemas/**`                               | `contracts`, `unit`                                        |
| `dashboard` | `packages/twinflow-dashboard/**`           | `a11y`, `e2e-golden`                                       |
| `docs`      | `docs/**`, `mkdocs.yml`, `*.md`            | `docs`                                                     |
| `workflows` | `.github/**`                               | `static`                                                   |
| `config`    | `*.yaml`, `*.toml`, `profiles/**`          | `static`, `e2e-golden`                                     |
| `goldens`   | `tests/goldens/**`                         | `e2e-golden`                                               |

The asterisk on `rust` marks the one cross-language case: a change under `packages/**` that
touches the shared event schemas also unlocks `rust`, because the device agent encodes them.

Five jobs carry no path filter and run on every pull request: `static`, `val-gates`, `ci-budget`,
`quickstart`, and `all-green`. `val-gates` and `ci-budget` are unconditional because the `docs`
job downloads their artifacts, and a `needs:` on a skipped job skips the dependant, which would
silently drop the rule that every number in the docs comes from a CI artifact. `quickstart` is
unconditional because the source makes the five-minute quickstart a requirement of every phase,
not of every diff. GOLDEN-GATE-01 runs inside `e2e-golden` rather than as a job of its own.

Jobs, with per-job budget:

| Job           | Matrix                                           | Budget         | Contents                                                                                                                                                                                                                                                                                                                                                             |
| ------------- | ------------------------------------------------ | -------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `static`      | py3.12, ubuntu                                   | 4 min          | `ruff format --check`, `ruff check`, `ty check` (mypy fallback), `twinflow-repolint check`, humaniser gate on the diff, comment judge, `yamllint`, `taplo check`, `codespell`, `actionlint`, `zizmor`, `twinflow config validate` on every A2 profile present at this phase, TASK-GATE-01, PROFILE-GATE-01, PROV-GATE-01, IP-GATE-01, CHANGELOG-GATE-01, SEC-GATE-02 |
| `unit`        | py 3.11 / 3.12 / 3.13 x ubuntu; py3.12 x windows | 4 min per cell | tier 1                                                                                                                                                                                                                                                                                                                                                               |
| `property`    | py3.12 x ubuntu                                  | 10 min         | tier 2, profile `ci`, fixed hypothesis seed, example database disabled                                                                                                                                                                                                                                                                                               |
| `e2e-golden`  | py3.12 x ubuntu                                  | 10 min         | tier 3 seeded scenarios in simulation mode, golden comparison, GOLDEN-GATE-01. No compose run                                                                                                                                                                                                                                                                        |
| `val-gates`   | py3.12 x ubuntu                                  | 6 min          | tier gates only, uploads `val-gates.json` and writes the step summary                                                                                                                                                                                                                                                                                                |
| `determinism` | py 3.11 and 3.12 x ubuntu                        | 5 min          | DET-GATE-01, DET-GATE-02                                                                                                                                                                                                                                                                                                                                             |
| `contracts`   | py3.12                                           | 3 min          | C3 producer/consumer tests, schema additivity diff against the last tag, REST and MCP schema snapshot diff                                                                                                                                                                                                                                                           |
| `rust`        | stable + MSRV, ubuntu; stable on windows         | 6 min          | `cargo fmt --check`, `cargo clippy --all-targets -- -D warnings`, `cargo test`, `cargo deny check`, `cargo check --target riscv32imc-unknown-none-elf --features esp32c3`                                                                                                                                                                                            |
| `a11y`        | py3.12                                           | 4 min          | axe-core against the dashboard, C12 checks. Reporting or blocking by phase, see below                                                                                                                                                                                                                                                                                |
| `docs`        | py3.12                                           | 4 min          | `needs: [val-gates, ci-budget]`, downloads their artifacts, then `mkdocs build --strict`, README example extraction and execution (README-GATE-01), ARCHITECTURE.md table structural check (DOC-GATE-04)                                                                                                                                                             |
| `quickstart`  | ubuntu                                           | 6 min          | the README five-minute quickstart executed verbatim from a clean checkout with no credentials in the environment, timed; fails if it exceeds 300 s, if any documented step errors, or if any process opens an outbound connection off the compose network                                                                                                            |
| `ci-budget`   | ubuntu                                           | 1 min          | BUDGET-GATE-01 and BUDGET-GATE-02: reads the run's job durations, compares to this table, checks the budget arithmetic, fails on breach                                                                                                                                                                                                                              |
| `all-green`   | ubuntu                                           | 10 s           | `if: always()` plus `needs:` every job; fails when any dependency's `result` is `failure` or `cancelled`, and passes when it is `success` or `skipped`                                                                                                                                                                                                               |

`all-green` is the single required status check in branch protection. It carries `if: always()`
because a job with a skipped dependency is itself skipped by default, which would turn the
required check into a check that never runs, and a required check that never runs is the D-12
failure mode of a test that cannot fail. Its own test is a fixture workflow run in which one
dependency is skipped and one fails, asserting the second makes `all-green` fail.

The `quickstart` job also carries the constraint the source states as "fully local, no cloud
account, optional env var for a hosted LLM". It runs with an empty secret context, so any step
that needed an account would fail there rather than in a reader's hands. QUICKSTART-GATE-01 is the
name of that assertion, and its falsification condition is a quickstart step that reads a
credential from the environment or resolves a hostname outside the compose network.

Stated CI wall-time budget (C10): the pull-request fast lane (`static`, `unit`, `contracts`)
completes within 5 minutes at p95. The full pull-request set, running in parallel, completes within
12 minutes at p95 and 8 minutes at p50. Every per-job budget above is at or below 10 minutes,
which is what makes the 12-minute figure reachable rather than aspirational, and BUDGET-GATE-02
rule 1 asserts that relation on every run. `ci-budget` enforces the per-job numbers on every run
and, on `push: main`, reads the last 20 runs through the API and fails if the median total exceeds
8 minutes. The budget is restated in `docs/ci.md` and in ADOPTION.md, because a reader deciding
whether to fork the repository cares what the loop costs.

Three job details that would otherwise be wrong on the day they land.

_The Rust embedded target._ The Rust project's platform support page lists
`riscv32imc-unknown-none-elf` in the "Tier 2 without Host Tools" table and
`xtensa-esp32-none-elf` in the "Tier 3" table, of which the page says "Official builds are not
available" (read from `https://doc.rust-lang.org/nightly/rustc/platform-support.html` on
2026-08-09, HTTP 200). An upstream `rustup` toolchain cannot build the Xtensa target, so the
pull-request lane targets the RISC-V variant. The board choice, an ESP32-C3, is recorded in
ARCHITECTURE.md next to the device-agent entry. The Xtensa cross-check is not dropped:
`nightly.yml` installs the esp-rs toolchain with `espup` and runs
`cargo check --target xtensa-esp32-none-elf --features esp32`, which keeps the original ESP32
claim provable while keeping the pull-request lane on toolchains `rustup` can install.

_The docs job and the CI-produced numbers._ 5.15 claims that a headline number no CI job produced
cannot reach the docs. That claim only holds if the docs build can see the artifacts, so the
`docs` job declares `needs: [val-gates, ci-budget]` and downloads both artifacts with
`actions/download-artifact` before building. The strict build is run once, in `docs`, and was
removed from `static`, because running the same build twice on every pull request costs three
minutes and proves nothing extra. When a macro references a key that no downloaded artifact
provides, it renders `not yet measured` and the build passes on a pull request and fails on a
release build, which is the split that lets Phase 0 exist before any measurement does.

_The a11y job by phase._ The job is in the matrix from Phase 1 and its behaviour is defined at
every point, rather than left to the reader. From Phase 1 to Phase 4 it runs axe-core against the
dashboard served from a static fixture state, uploads the violation report, and never fails the
build; the job's own conclusion is `success` with the report attached. From v0.3.0 it serves the
dashboard from the seeded E1 replay bundle instead of the fixture, which is when the C12 checks
have real findings to render. At Phase 5, when the dashboard reaches its final shape, the job
becomes blocking: any axe-core violation at serious or critical impact fails it. The transition is
one line in `.github/ci-budget.yml` (`a11y.blocking: true`) and a CHANGELOG entry, so a reader can
see when the promise hardened.

The `static` job's config-validation step validates the A2 profiles that exist at the current
phase, which is `micro` at Phase 0 and all three from v0.4.0. The job reads
`profiles/*.yaml` rather than a hard-coded list, so a profile landing does not need an edit to the
workflow, and PROFILE-GATE-01 asserts that the profile set on disk equals the set ADOPTION.md and
the golden manifest reference.

Caching: `astral-sh/setup-uv` with the uv cache keyed on `uv.lock`; `Swatinem/rust-cache` keyed on
`Cargo.lock`; a docker layer cache for the compose e2e keyed on the compose file digest and the
Dockerfile digests.

**`nightly.yml`** on `schedule: cron "0 3 * * *"` and `workflow_dispatch`. Workflow budget 370
minutes, budgeted per matrix cell because nine cells cannot share one job budget:

| Cell or job          | Count | Budget per cell | Contents                                                                                              |
| -------------------- | ----- | --------------- | ----------------------------------------------------------------------------------------------------- |
| tier 4 matrix        | 9     | 35 min          | ubuntu, windows, macos x py 3.11 / 3.12 / 3.13; soak and the chaos catalogue; Hypothesis `thorough`   |
| `det-cross-platform` | 1     | 15 min          | DET-GATE-03 across the three operating systems, reporting observed divergence                         |
| `rust-xtensa`        | 1     | 12 min          | `espup` install then `cargo check --target xtensa-esp32-none-elf --features esp32`                    |
| `links`              | 1     | 10 min          | `lychee` external link check, DOC-GATE-02, per-domain rate-limit allowlist                            |
| `fleet-compliance`   | 1     | 10 min          | the E48 fleet configuration-compliance audit                                                          |

The per-cell budget is 35 minutes rather than 30 because tier 4's 1800 s budget times its 1.1
hard-fail ratio plus the 45 s setup reserve is 2025 s, and BUDGET-GATE-02 rule 2 refuses a job
budget below that. The workflow budget of 370 minutes is the sum in rule 3, which is
9 x 35 + 15 + 12 + 10 + 10 = 362 minutes, with 8 minutes of headroom.

The chaos catalogue in the tier-4 cells covers broker kill, partition, clock drift, and the botched
firmware push (E44).

Two workloads that used to sit inside `nightly.yml` have their own scheduled workflows, because
each has a budget the nightly cannot absorb and a cadence the nightly does not need:

- **`loadtest.yml`** on `schedule: cron "0 4 * * 0"` and `workflow_dispatch`. Budget 90 minutes.
  Runs the A4 curves on `ref-gh`, writes `repo.loadtest.sample.v1` and `repo.loadtest.summary.v1`,
  and runs A4-GATE-01 against `benchmarks/baseline.json`. Weekly rather than nightly because a
  scaling curve that changes between two consecutive nights is measuring the runner, not the code.
- **`agent-evals.yml`** on `schedule: cron "0 4 * * *"` and `workflow_dispatch`. Budget 45 minutes.
  Runs the E27 agent eval suite and the E43 AI red-team suite and writes
  `artifacts/ci/agent-scorecard.json`. Separate because its cost tracks model latency rather than
  this repository's code, so a slow provider must not consume the nightly's budget.

A failure in any of the three opens an Issue labelled `ci:nightly` containing the run link, the
failing job, and any falsifying example.

**`security.yml`** on `pull_request`, `push: main`, and `schedule: cron "0 5 * * 1"`. `pip-audit`
on the exported lock, `cargo audit`, `cargo deny check advisories bans sources`, `gitleaks`
(staged range on PR, full history on schedule), `semgrep` with `p/security-audit` and `p/python`,
CodeQL for Python and JavaScript (and Rust where CodeQL's Rust support is available; otherwise the
Rust surface is covered by `cargo audit` plus clippy's correctness and security lints, and
`docs/security.md` says which), `dependency-review-action` on PRs, and OpenSSF Scorecard weekly
publishing to the badge.

**`tag.yml`** on `push: main` where the head commit touches `VERSION`. This workflow is the answer
to C9's first verb, which nothing else in the pipeline performs. Steps:

1. Read `VERSION`. Exit without acting if a tag `v<VERSION>` already exists.
2. Assert `CHANGELOG.md` has a released section for that version and that its `[Unreleased]`
   section is empty, which is what `just release-prepare` leaves behind.
3. Assert every phase whose `declared_tag` equals `v<VERSION>` has `status: closed` and passed
   INV-PH-04a in the closure pull request.
4. Create an annotated, signed tag `v<VERSION>` at that commit with the CHANGELOG section as the
   tag message, and push it. Permissions `contents: write`, elevated only in this job with the
   reason in a comment.
5. Record `tag_observed` for the affected phases by opening a follow-up commit on `main` through
   the same job.

Pushing the tag is what triggers `release.yml`, so the chain runs `just release-prepare` (human),
release pull request (human review), merge, `tag.yml` (automated tag), `release.yml` (automated
changelog extraction, build, publish). All four C9 verbs are covered by automation and the only
human acts are naming the version and approving the release. `just release-tag` performs the same
tag creation locally for the case where the workflow is unavailable, and it refuses to run if
steps 1 to 3 do not hold.

**`release.yml`** on `push: tags: v*`. Budget 45 minutes, which BUDGET-GATE-02 rule 3 checks
against the job budgets it runs: tiers 0 to 3 sum to 180 + 120 + 420 + 420 seconds, or 19 minutes;
`val-gates` adds 6 and `determinism` adds 5; the build, cross-build, SBOM, attestation, and publish
job is budgeted at 13. That is 43 minutes against a 45 minute workflow budget. Steps in order:

1. Assert the tag equals `VERSION` and that `CHANGELOG.md` has a section for it.
2. Run tiers 0 to 3 plus `val-gates` plus `determinism` on the release commit.
3. `twinflow-valgate phase-closure` must be green for every phase marked closed, and INV-PH-04b
   asserts each closed phase's declared tag now resolves to a real annotated tag.
4. `twinflow-migrate verify-fixtures` (MIG-GATE-01).
5. `uv build --all-packages` producing an sdist and a wheel per brick.
6. Cross-build the Rust device agent for `x86_64-unknown-linux-gnu`, `aarch64-unknown-linux-gnu`,
   `x86_64-pc-windows-msvc`, and a `cargo check` for `riscv32imc-unknown-none-elf`.
7. CycloneDX SBOM per Python artifact (`cyclonedx-py`) and for the Rust crate
   (`cargo cyclonedx`), plus an aggregate repo SBOM. The specification version is recorded in the
   document and SBOM-GATE-01 needs at least 1.6. The CycloneDX specification repository publishes
   JSON schemas `bom-1.2` through `bom-1.7` in its `schema/` directory (listing read through the
   GitHub contents API at
   `https://api.github.com/repos/CycloneDX/specification/contents/schema` on 2026-08-09,
   HTTP 200), so 1.6 is a floor and not a ceiling.
8. `actions/attest-build-provenance` for SLSA provenance on every artifact.
9. Publish to PyPI with Trusted Publishing from the `pypi` environment, which requires approval.
10. Create the GitHub Release with notes from the CHANGELOG section, attaching the SBOMs, the
    VAL-GATE report, the scaling report, the agent scorecard, and the compatibility table row.
11. From v0.3.0 onward, trigger `docs.yml` and `replay.yml`. The step is guarded by a check that
    the workflow file exists, so the v0.2.0 release, which is the first release and predates both
    workflows, runs the same file without a missing-workflow error. The guard is removed at
    v0.3.0's release and the CHANGELOG says so.

Pre-release tags `vX.Y.Z-rc.N` publish to TestPyPI and skip step 11's Pages trigger.

**`docs.yml`** on `push: main` touching `docs/**` or `mkdocs.yml`, and on release. Builds
mkdocs-material, deploys with `mike` under the version alias, publishes to GitHub Pages.

**`replay.yml`** (E1) on release and `workflow_dispatch`. Regenerates the replay bundle from the
pinned seed in `demo/replay.yaml`, publishes it under the Pages site at `/replay/`, and asserts the
bundle's manifest seed matches the pinned value.

**`roadmap-sync.yml`** on `push: main` touching `roadmap.yaml` and weekly. Runs
`tools/roadmap_sync.py --apply`.

### 5.5 The VAL-GATE registry (component 5 validation requirement)

A validation gate is a test that binds a computed statistic to a named published reference with a
stated tolerance. Gates are declared in code, not in a spreadsheet, so a gate cannot exist without
an executable check.

```python
from twinflow.valgate import val_gate, Reference, Tolerance, GateClass, record_measurement

@val_gate(
    id="VAL-SPC-004",
    title="Individuals and moving-range chart limits reproduce the NIST/SEMATECH "
          "e-Handbook 6.3.2.2 flow-rate worked example",
    gate_class=GateClass.REFERENCE,
    requirement_ids=["5"],
    phase="P2",
    reference=Reference(
        name="NIST/SEMATECH e-Handbook of Statistical Methods",
        edition="chapter 6, as served 2026-08-09",
        section="6.3.2.2 Individuals Control Charts",
        url="https://www.itl.nist.gov/div898/handbook/pmc/section3/pmc322.htm",
        retrieved="2026-08-09",
        http_status=200,
        rights="public-domain",
        redistributable=True,
        printed_precision={"UCL": 4, "CL": 2, "LCL": 4},   # decimal places as printed
    ),
    tolerance=Tolerance(
        kind="absolute",
        value=1e-4,
        applies_to=["UCL", "CL", "LCL"],
        per_quantity={"CL": 1e-2},      # the page prints the centre line to two decimals
    ),
    falsifies_on=(
        "UCL or LCL differs from the published value by more than 1e-4, "
        "or CL differs by more than 1e-2"
    ),
    dataset="tests/fixtures/reference/nist_ehandbook_63222_flowrate.csv",
)
def test_imr_limits():
    data = load_fixture("nist_ehandbook_63222_flowrate.csv")   # 10 batch flow-rate readings
    chart = IMRChart().fit(data)
    record_measurement(UCL=chart.ucl, CL=chart.cl, LCL=chart.lcl)
    return {"UCL": 55.8041, "CL": 50.81, "LCL": 45.8159}       # values as published
```

The expected values above are the ones the cited page prints, under its heading "Limits for the
moving range chart", for the batch flow-rate example: `x-bar = 50.81`, `MR-bar = 1.8778`,
`UCL = 55.8041`, `Center Line = 50.81`, and `LCL = 45.8159`, with the limits formed as
`x-bar +/- 3 * MR-bar / 1.128` and 1.128 identified on the same page as `d2` for `n = 2`. Read
from `https://www.itl.nist.gov/div898/handbook/pmc/section3/pmc322.htm` on 2026-08-09, HTTP 200.
The arithmetic checks: `3 * 1.8778 / 1.128 = 4.99414`, and `50.81 +/- 4.99414` rounds to the two
printed limits.

The tolerance is `absolute 1e-4` on the limits rather than `relative 1e-6`, because the source
prints UCL and LCL to four decimal places. It relaxes to `1e-2` on the centre line, because the
source prints that to two. D-11 condition 2 forbids checking to more digits than the source
published, and INV-VG-08 refuses the registration if any quantity's tolerance implies more digits
than its `printed_precision` entry. A single tight number across all three quantities would look
more rigorous and would be testing the arithmetic of a rounding, not the engine.

The decorator registers the gate, applies `@pytest.mark.val_gate`, and wraps the test so the
returned expected mapping and the recorded measured mapping are compared by the tolerance kind.
The plugin writes one `repo.val_gate.result.v1` record per gate.

Gate classes and their rules:

- `REFERENCE`: an external published source. Names the source, edition, section, URL, retrieval
  date, HTTP status, and rights. This is the class the source's non-negotiable validation
  requirement means.
- `GROUND_TRUTH`: the twin generates the data and a published algorithm or guarantee sets the
  threshold. Process-mining conformance is the canonical case: the designed model is the truth, so
  no external data exists, while the fitness definition being measured is published and is named in
  `external_anchor`. Causal-structure recovery (E30), MEIO analytic-versus-simulated agreement
  (6a8), and the MSA variance-component recovery test are the others. Every gate in this class
  states its ground-truth construction and carries an `external_anchor`, per INV-VG-02.
- `META`: gates over the gate machinery itself (7.4). A META gate makes no claim about the world,
  so it is counted separately in the registry and is never presented as external validation. The
  badge in the README shows the REFERENCE and GROUND_TRUTH counts only, and `Registry.counts()`
  returns the META count as its own field so a reader can see both numbers.

CI artifacts produced by the `val-gates` job:

- `artifacts/ci/val-gates.json`, one record per gate, uploaded and retained 90 days.
- `artifacts/ci/val-gates.md`, written to `$GITHUB_STEP_SUMMARY` so the result is visible on the
  run page without downloading anything.
- `artifacts/ci/val-gates-badge.json`, published to Pages and consumed by a shields.io endpoint
  badge in the README. The badge text is rendered from `Registry.counts()` as
  `VAL-GATES <passing>/<total>` over the REFERENCE and GROUND_TRUTH gates declared at that
  release, so the number moves with the registry rather than being typed into the README. A gate
  at `PENDING_REFERENCE` counts in the denominator and never in the numerator, which is what stops
  the badge from improving when a gate loses its reference.
- `docs/validation.md`, regenerated by `twinflow-valgate render` and committed, so the public
  registry table of every statistic, its reference, and its tolerance is browsable on the docs
  site. A CI check fails if the committed file differs from the regenerated one.

Phase-closure rule, mechanised. `phases.yaml` lists per phase the gate ids that must pass. The
`phase-closure` job asserts INV-PH-01 through INV-PH-05. Closing a phase is a pull request that
flips `status: open` to `status: closed`; that pull request fails unless every listed gate exists
and its last run passed. This is the literal implementation of "no phase closes until its
statistics validate against their named published reference". A phase with genuinely no
statistical content (Phase 0, Phase 5 polish) must supply `no_gates_justification`, which CI
requires to be non-empty prose, so the absence is a recorded decision rather than an oversight.

Reference provenance rule. `tests/fixtures/reference/SOURCES.md` lists every fixture file with
`file, source, section, url, retrieved, rights, redistributable, note`. `PROV-GATE-01` fails if a
file in that directory is missing from SOURCES.md or if a file marked `redistributable: false`
exceeds 200 numeric cells (a size heuristic that catches an accidental bulk copy). NIST StRD and
the NIST/SEMATECH e-Handbook are works of the United States Government, and 17 U.S.C. 105 states
that "Copyright protection under this title is not available for any work of the United States
Government" (read from `https://www.law.cornell.edu/uscode/text/17/105` on 2026-08-09, HTTP 200),
so both are marked `rights: public-domain` and `redistributable: true`. Minitab documentation
examples and the AIAG manual's example are marked `redistributable: false`, encoded as the numeric
data only, and cited by edition and page.

Seed gate catalogue. The LSS section owns the full catalogue; this section owns the registry
contract and seeds it with the gates the validation source map makes mandatory. Every one names a
leaf locator that resolves to one page, per INV-VG-01, and the NIST/SEMATECH locators below were
read from the chapter 6 and chapter 7 detailed tables of contents at
`https://www.itl.nist.gov/div898/handbook/pmc/pmc_d.htm` and
`https://www.itl.nist.gov/div898/handbook/prc/prc_d.htm` on 2026-08-09, both HTTP 200.

Deterministic gates, where the measured quantity is arithmetic over a fixed dataset and the only
tolerance question is the source's printed precision:

| Gate         | Validates                                                                                              | Reference                                                                                     | Tolerance                                                                                                        |
| ------------ | ------------------------------------------------------------------------------------------------------ | --------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------- |
| VAL-NUM-001  | Mean and standard deviation on `PiDigits`, `Lottery`, `Lew`, `Michelso`, `NumAcc1..4`                  | NIST StRD, Univariate Summary Statistics, per-dataset certified value page                    | `lre >= 12` on NumAcc1, whose certified mean and sd are exact by construction; `lre >= 7` on NumAcc3 and NumAcc4 |
| VAL-NUM-002  | One-way ANOVA F statistic and between/within mean squares on `SiRstv`, `AtmWtAg`, `SmLs01`, `SmLs09`   | NIST StRD, Analysis of Variance, per-dataset certified value page                             | `lre >= 8` on the low-difficulty sets, `lre >= 5` on `SmLs09`                                                    |
| VAL-NUM-003  | Linear regression coefficients and residual sd on `Norris`, `Pontius`, `Filip`                         | NIST StRD, Linear Regression, per-dataset certified value page                                | `lre >= 7` via the QR path; the report also records the normal-equations path's LRE on `Filip` as a note         |
| VAL-NUM-004  | Nonlinear regression parameters on `Misra1a`, `Chwirut2`, `MGH09`                                      | NIST StRD, Nonlinear Regression, per-dataset certified value page                             | `lre >= 5` from both the certified start and the far start                                                       |
| VAL-SPC-001  | Xbar and R chart limits, worked example                                                                | NIST/SEMATECH e-Handbook 6.3.2.1 Shewhart X-bar and R and S Control Charts                    | per quantity, from `printed_precision`; the gate lists a tolerance for every quantity it checks                  |
| VAL-SPC-004  | I-MR chart limits                                                                                      | NIST/SEMATECH e-Handbook 6.3.2.2 Individuals Control Charts                                   | `absolute 1e-4` on UCL and LCL, `absolute 1e-2` on the centre line, as worked above                              |
| VAL-SPC-006  | p-chart limits and the variable-sample-size case                                                       | NIST/SEMATECH e-Handbook 6.3.3.2 Proportions Control Charts                                   | per quantity, from `printed_precision`                                                                           |
| VAL-SPC-008  | EWMA chart limits and the smoothing recursion                                                          | NIST/SEMATECH e-Handbook 6.3.2.4 EWMA Control Charts                                          | per quantity, from `printed_precision`                                                                           |
| VAL-SPC-010  | Hotelling T2 control limits, subgroup-average case                                                     | NIST/SEMATECH e-Handbook 6.5.4.3.1 T2 Chart for Subgroup Averages, Phase I                    | per quantity, from `printed_precision`                                                                           |
| VAL-CAP-001  | Cp, Cpk, Pp, Ppk, sigma level, DPMO on the worked example                                              | NIST/SEMATECH e-Handbook 6.1.6 What is Process Capability?                                    | per quantity, from `printed_precision`                                                                           |
| VAL-ACC-001  | Acceptance sampling OC curve points and plan selection                                                 | NIST/SEMATECH e-Handbook 6.2.3.2 Choosing a Sampling Plan with a given OC Curve               | per quantity, from `printed_precision`                                                                           |
| VAL-MSA-001  | Gage R and R ANOVA table and %GRR with `errorTerm="repeatability"`                                     | AIAG Measurement Systems Analysis manual, 4th edition, worked example; see note below         | `absolute 0.1` percentage point on %Contribution and %StudyVar; `relative 1e-4` on mean squares                  |
| VAL-MSA-002  | The same study with `errorTerm="interaction"` (operator x part interaction)                            | Minitab's published Gage R and R documentation example, and R package `SixSigma` 0.11.1       | same tolerances                                                                                                  |
| VAL-MSA-003  | The default error term is documented, and switching it moves %GRR in the direction both sources imply  | both of the above                                                                             | direction assertion, no numeric tolerance                                                                        |
| VAL-HYP-001  | Two-sample t and one-way ANOVA statistics and p-values                                                 | NIST/SEMATECH e-Handbook 7.3.1 and 7.4.3.4                                                    | per quantity, from `printed_precision`                                                                           |
| VAL-HYP-003  | Rank-sum statistic and p-value for the two-sample nonparametric comparison                             | NIST/SEMATECH e-Handbook 7.3.5 Do two arbitrary processes have the same central tendency?     | per quantity, from `printed_precision`                                                                           |
| VAL-PM-001   | Token-replay fitness of the designed model against a log that model generated is 1.0                   | GROUND_TRUTH construction; anchor is the fitness definition in Rozinat and van der Aalst 2008 | `absolute 1e-9`, since the quantity is an exact ratio of token counts                                            |

Note on VAL-MSA-001 and VAL-MSA-002. The AIAG manual is sold, not served, so its worked example
was not retrieved for this document and the claim that it contains one is attributed to AIAG
rather than asserted from primary text. The gate encodes the numeric study data only, marks it
`redistributable: false`, and cites the manual by edition and page in `SOURCES.md`. The R package
`SixSigma` publishes on CRAN at version 0.11.1, dated 2023-08-22, under "GPL-2 | GPL-3" (read from
`https://cran.r-project.org/web/packages/SixSigma/index.html` on 2026-08-09, HTTP 200), which is
why its vignette output is read as a published number and its bundled dataset is never copied into
this repository. Open question 2 records the rights decision that follows.

Stochastic gates, where the measured quantity carries sampling noise. D-11 condition 3 forbids a
tolerance tighter than that noise, so each row states its replicate count, its noise floor with the
arithmetic that produced it, and what would falsify it. INV-VG-07 refuses registration when the
tolerance falls below the floor:

| Gate           | Nominal and replicates                         | Noise floor                                                             | Tolerance                | Falsifies on                                                                                   |
| -------------- | ---------------------------------------------- | ----------------------------------------------------------------------- | ------------------------ | ---------------------------------------------------------------------------------------------- |
| VAL-MSA-004    | interval coverage 0.90, 500 seeded replicates  | binomial, `3 * sqrt(0.90 * 0.10 / 500) = 0.0402`                        | `coverage 0.05`          | observed coverage outside 0.85 to 0.95                                                         |
| VAL-HYP-002    | routing error rate 0.02, 500 seeded datasets   | binomial, `3 * sqrt(0.02 * 0.98 / 500) = 0.0188`                        | `absolute 0.019`         | more than 19 of the 500 datasets routed to the wrong test                                      |
| VAL-FCST-001   | AutoARIMA coefficient recovery, 100 replicates | replicate standard deviation, measured by the committed calibration run | `relative 0.05`          | the measured floor exceeding 0.05, which fails registration, or a coefficient outside the band |
| VAL-FCST-002   | split-conformal coverage 0.90, 500 replicates  | binomial, `3 * sqrt(0.90 * 0.10 / 500) = 0.0402`                        | `coverage 0.05`          | observed coverage outside 0.85 to 0.95                                                         |
| VAL-MEIO-001   | fill rate 0.95, 20000 seeded demand periods    | binomial, `3 * sqrt(0.95 * 0.05 / 20000) = 0.0046`                      | `absolute 0.005`         | simulated fill rate differing from the analytic answer by more than 0.005                      |
| VAL-PM-002     | miner recovery, 200 seeded logs                | replicate standard deviation, measured by the committed calibration run | see the anchor row below | fitness or precision disagreeing with the oracle beyond the stated band                        |
| VAL-CAUSAL-001 | structural Hamming distance, 200 replicates    | replicate standard deviation, measured by the committed calibration run | PENDING_REFERENCE        | recorded as open question 14 until its anchor is named                                         |

External anchors for the GROUND_TRUTH rows, so none of them rests on this repository (D-11
condition 1). All four were confirmed through the Crossref REST API on 2026-08-09, HTTP 200:

| Gate           | Anchor                                                                                                                                                                                                                                                             |
| -------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| VAL-PM-001     | Rozinat and van der Aalst, "Conformance checking of processes based on monitoring real behavior", Information Systems 33(1), 64-95, 2008, DOI 10.1016/j.is.2007.07.001                                                                                             |
| VAL-PM-002     | Leemans, Fahland, and van der Aalst, "Discovering Block-Structured Process Models from Event Logs, A Constructive Approach", LNCS 7927, 311-329, 2013, DOI 10.1007/978-3-642-38697-8_17, plus the development-only oracle of 5.12 as an independent implementation |
| VAL-FCST-002   | Lei, G'Sell, Rinaldo, Tibshirani, and Wasserman, "Distribution-Free Predictive Inference for Regression", Journal of the American Statistical Association 113(523), 1094-1111, 2018, DOI 10.1080/01621459.2017.1307116                                             |
| VAL-MEIO-001   | Graves and Willems, "Optimizing Strategic Safety Stock Placement in Supply Chains", Manufacturing and Service Operations Management 2(1), 68-83, 2000, DOI 10.1287/msom.2.1.68.23267                                                                               |
| VAL-CAUSAL-001 | none yet, which is why the gate registers as `PENDING_REFERENCE` and blocks its phase                                                                                                                                                                              |

Alignment-based conformance, which D-14 puts inside `twinflow-procmine`, anchors on Adriansyah,
van Dongen, and van der Aalst, "Conformance Checking Using Cost-Based Fitness Analysis", EDOC
2011, 55-64, DOI 10.1109/EDOC.2011.12. The textbook treatment the package's docstrings cite is
van der Aalst, "Process Mining", Springer, 2016, DOI 10.1007/978-3-662-49851-4.

META gates, which assert properties of this machinery rather than of the world, are listed
separately in 7.12 and are counted separately in the badge.

### 5.6 Migrations and the compatibility table (C6)

Three migration kinds, one command surface.

Historian relational migrations live in `migrations/historian/NNNN_<slug>.sql`, forward-only,
applied inside a transaction, recorded in a `schema_migrations` table holding
`(version, slug, checksum, applied_at_wall, applied_at_sim, twinflow_version)`. The migrator
refuses to run if a recorded checksum no longer matches the file on disk (INV-MG-01), which is what
stops a released migration from being edited in place.

Delta table migrations live in `migrations/delta/NNNN_<slug>.py`, each exposing
`def apply(table: DeltaTable) -> None`. Only additive column adds, metadata updates, and backfills
are permitted; a migration that drops or retypes a column fails the migration linter. Delta's own
protocol versions and the twinflow schema version are recorded in a `_twinflow_meta` Delta table.

Config migrations are Python objects registered against a kind:

```python
class AddDockDoorCapacity(ConfigMigration):
    kind = "facility"
    from_version = "0.3"
    to_version = "0.4"
    description = "dock doors gain an explicit capacity; previously implied by station count"
    def apply(self, doc):        # ruamel round-trip document, comments preserved
        for door in doc["docks"]["doors"]:
            door.setdefault("capacity_pallets_per_hour", 12)
        return doc
```

`twinflow-migrate config upgrade facility.yaml --to 0.9 --diff` prints the unified diff and exits
without writing. `--write` applies and emits `config.upgraded.v1`. `--check` is the CI mode: it
exits non-zero if the file is not already at the current version, which keeps the three shipped A2
profiles current.

The upgrader uses `ruamel.yaml` in round-trip mode so comments and key order survive. A reader who
annotated their own `facility.yaml` gets their annotations back, which is the difference between a
tool people run and a tool people avoid.

CHANGELOG compatibility table, generated by `twinflow-migrate compat-table` into
`docs/compatibility.md` and inlined into each release's CHANGELOG section:

| Release | facility.yaml | sensor catalog | event schema major | historian schema | run bundle | reads runs from | reads configs from |
| ------- | ------------- | -------------- | ------------------ | ---------------- | ---------- | --------------- | ------------------ |
| v0.4.0  | 0.4           | 0.3            | 1                  | 0007             | 2          | v0.2.0+         | v0.1.0+            |

`reads runs from` means: a run bundle recorded by that release opens in this release, proven by a
committed fixture under `tests/fixtures/compat/runs/<release>/`. `reads configs from` means the
upgrader converts a config from that release and the result validates. MIG-GATE-01 in
`release.yml` proves every row before the release publishes. Fixture runs are deliberately tiny
(one simulated shift on the `micro` profile, under 200 KB) so the fixture set can grow forever.

### 5.7 The nondeterminism lint and the determinism gate

`twinflow-repolint` is an AST checker, not a regex grep, so `from time import time as t` and
`import numpy.random as r` are caught.

| Rule   | Bans                                                                                                                                                                                     | Rationale                                                                                                |
| ------ | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------- |
| TFD001 | `time.time`, `time.monotonic`, `time.perf_counter`, `time.time_ns`, `datetime.now`, `datetime.utcnow`, `datetime.today`, `date.today`, `pandas.Timestamp.now`, `numpy.datetime64("now")` | wall clock outside the CLOCK interface breaks C2 and makes runs unreproducible                           |
| TFD002 | `random.*` module functions, `numpy.random` legacy globals (`seed`, `rand`, `randn`, `choice`, `permutation`), `secrets.*`, `uuid.uuid1`, `uuid.uuid4`, `os.urandom`                     | unseeded entropy breaks C1's splittable-RNG contract                                                     |
| TFD003 | `socket.*`, `requests.*`, `urllib.request.*`, `http.client.*`, `httpx.Client()` construction, `subprocess.*`                                                                             | raw network and process calls bypass the NETWORK interface, so partitions and latency cannot be injected |
| TFD004 | `open()` on a path not derived from the STORAGE interface, `pathlib.Path.write_*` outside storage, `os.remove`, `shutil.rmtree`                                                          | filesystem access outside STORAGE is invisible to simulation mode                                        |
| TFD005 | `time.sleep`, `asyncio.sleep`, `threading.Timer`, `threading.Event.wait(timeout=...)`                                                                                                    | wall-clock waits desynchronise the virtual clock                                                         |
| TFD006 | `hash()` applied to `str` or `bytes` where the result is persisted, iteration over a `set` whose order reaches an output, `concurrent.futures` results consumed as completed             | PYTHONHASHSEED and scheduling order leak into the event log                                              |
| TFB001 | importing another twinflow package's private submodule                                                                                                                                   | A1 boundary                                                                                              |
| TFB002 | a package importing a package not declared in its `pyproject.toml` dependencies                                                                                                          | A1 boundary                                                                                              |

Three scopes, and nothing outside them.

_Kernel boundary._ Every rule is lifted inside the four kernel modules
`packages/twinflow-kernel/src/twinflow/kernel/{clock,rng,net,storage}.py`, plus any path listed in
`repolint.toml` under `[kernel_boundary] paths = [...]`, which is short and reviewed. This is where
the seam is implemented, so it is the one place the seam may be crossed.

_Test boundary._ Under `packages/*/tests/**` and `tests/**`, rules TFD003 to TFD006 are lifted and
TFD001 and TFD002 still apply. A test may open a file or a socket; a test may not read a wall
clock or draw unseeded entropy, because a test that does either is the reason a suite goes flaky.

_Measurement boundary._ Four allowances, and no fifth, because A4 and C4 measure wall time by
construction. This is the complete set INV-RL-03 compares `repolint.toml` against, held literally
in a unit test so that widening it is a reviewed edit rather than a quiet one:

| Rule   | Path glob                        | Justification                                                            | Owning requirement |
| ------ | -------------------------------- | ------------------------------------------------------------------------ | ------------------ |
| TFD001 | `packages/twinflow-valgate/**`   | `GateResult.duration_s` for the gate report                              | component 5        |
| TFD001 | `packages/twinflow-testkit/**`   | per-test duration for the tier budget report                             | C4                 |
| TFD001 | `packages/twinflow-loadtest/**`  | end-to-end latency is a wall-time quantity by definition                 | A4                 |
| TFD003 | `packages/twinflow-loadtest/**`  | the harness drives a real broker over a real socket in production mode   | A4                 |

Every allowance carries a non-empty `justification` and an `owning_requirement` that resolves
(INV-RL-04). Allowances are not counted against `max_escapes`, because they are declared centrally
rather than scattered through the source. `tools/**` needs no allowance: the `include` glob in 6.1
covers package source and tests only, so repo-local scripts are outside the checker's scope, and
6.1 says so rather than leaving a reader to infer it.

Escape hatch: a trailing comment `# twinflow: allow-nondeterminism(TFD001, reason="...")` on the
offending line. An escape with an empty or missing reason is itself a violation (INV-RL-01).
`twinflow-repolint escapes --list` prints the full inventory; the `static` job writes it to the
step summary and fails if the count exceeds `max_escapes` in `repolint.toml` (INV-RL-02). The
ceiling starts at 0 in Phase 0 and only moves in a commit that says why.

Output format: `--format github` emits `::error file=...,line=...,title=TFD002::message` so
violations annotate the pull request diff directly.

Backstop, per the locked decision that C1's repeated-run hash check backstops the lint. The three
gates below carry D-05's two tiers, and neither the code nor the README claims more than the
tier it can prove:

- DET-GATE-01, the byte-identical tier. Run the reference scenario four ways on the same runner
  cell (twice in one process, twice in fresh processes, once under `PYTHONHASHSEED=random`, once
  with `-X dev`) and assert all four event-log SHA-256 digests are equal. Falsifies on any pair of
  the four digests differing. Scope: same seed, same config, same platform, same pinned dependency
  set, which is exactly D-05's byte-identical row.
- DET-GATE-02, the same tier across a Python minor. Assert the digest is equal across Python 3.11
  and 3.12 on the same operating system and architecture. Falsifies on the two digests differing.
- DET-GATE-03 (nightly), the value-equivalent tier. Across ubuntu, windows, and macos, assert that
  the business events are identical under the documented normalisation, and for continuous fields
  report the observed maximum relative divergence rather than asserting a number chosen in
  advance. D-05 sets that rule: the gate reports what it measured, and the tolerance it compares
  against is the one derived from the previous measured divergence and committed in
  `benchmarks/cross-platform-divergence.json` with the run that produced it. Until that file has a
  measurement in it, the gate publishes its divergence and does not block, and the missing
  tolerance is open question 3. Falsifies on a business-event mismatch at any time, and, once the
  tolerance exists, on a continuous field exceeding it. When it exceeds the tolerance, the gate
  names which of the two it found: a tolerance that was set too tight, or a real defect.

Cross-platform byte-identity is not asserted anywhere in this repository, and DET-GATE-03 is the
gate that would have to change if it ever were.

### 5.8 SECURITY.md and the MCP/REST threat model (C7)

`SECURITY.md` contains, in this order:

**Reporting.** GitHub private vulnerability reporting is the primary channel (Security tab, Report
a vulnerability), which is free on public repositories and keeps the report private until an
advisory publishes. A dedicated email alias is the fallback. Response commitments: acknowledge
within 72 hours, triage within 7 days, fix or publish an advisory within 90 days. Reporters are
credited in the advisory unless they decline.

**Supported versions.** A table: the latest minor of the current major receives fixes; the
previous minor receives fixes for 90 days after the next minor publishes; older versions receive
none. Pre-1.0 the table says the latest minor only, which is honest.

**Scope.** In scope: the REST/GraphQL surface (A6), the MCP server (E2), the agent's SQL and
Python execution sandbox (E26a), the dashboard, the broker configuration shipped in the compose
files, the release supply chain (workflows, publishing, SBOM), and the git hooks. Out of scope:
the simulated CVE feed, the simulated SIEM, and the synthetic attack scenarios in 6a15 and E18,
which are fiction and are not vulnerability channels. A finding that "the simulated MES analog has
a simulated unpatched CVE" is the demo working, not a bug.

**Threat model for the MCP and REST surface.** Assets: the historian's recorded runs, the governed
metric layer, the running facility config, the broker's publish path, the host filesystem, and any
credential in the environment. Trust boundaries: an MCP client is untrusted; a REST caller is
untrusted; the OT network segment is not reachable from either.

The SQL/Python sandbox boundary, stated concretely because a vague sandbox claim is worse than
none:

_SQL path._ Generated SQL executes against a DuckDB connection opened read-only on a snapshot copy
of the historian, with `enable_external_access=false`, `allow_unsigned_extensions=false`, and no
`INSTALL` or `LOAD`. The statement is parsed with `sqlglot` before execution and rejected unless
it is exactly one `SELECT` (or `WITH ... SELECT`) statement. Rejected: any DDL, any DML, `ATTACH`,
`COPY`, `EXPORT`, `PRAGMA`, `SET`, and any call to a function on the denylist (`read_csv`,
`read_parquet`, `read_json`, `sniff_csv`, `glob`, `httpfs` functions). Limits: 5 second statement
timeout, 100000 row cap, 256 MB memory limit. The snapshot is per-request and read-only at the
filesystem level.

_Python path._ Generated Python executes in a subprocess launched with a restricted import hook
that allows only `math`, `statistics`, `decimal`, `fractions`, `numpy`, `pandas`, and the twinflow
read-only client shim. Denied: `os`, `sys`, `subprocess`, `socket`, `ctypes`, `importlib`,
`builtins.open`, `builtins.eval`, `builtins.exec`, `builtins.__import__` beyond the allowlist.
Resource limits: `RLIMIT_CPU` 5 seconds, `RLIMIT_AS` 512 MB, `RLIMIT_FSIZE` 0 outside a per-call
temporary directory, `RLIMIT_NPROC` 0. In production mode the sandbox container runs with
`network_mode: none`, so even a hook bypass reaches nothing. The subprocess is killed as a process
group on timeout.

_What a malicious client can reach._ The governed metric definitions, a read-only historian
snapshot, the findings stream, and the what-if runner subject to a scenario budget (maximum
scenario count and maximum sim horizon per client per window).

_What it cannot reach._ The OT network segment, the broker's publish path, the running facility
config (writes flow only through the E5 autonomy tiers with an authority check and an audit-trail
entry), the host filesystem, the network, other clients' snapshots, and any credential. The REST
surface is read-mostly; every mutating route requires an authority tier and writes to the decision
register.

_Indirect prompt injection._ In scope and treated as a real threat, because the system reads
untrusted strings from device names, SOP documents, supplier records, and customer notes. Controls:
untrusted text is wrapped in a delimited, escaped block that the prompt template marks as data;
tool arguments are schema-constrained (E26d) so a smuggled instruction cannot produce a malformed
call; the grounding checker (E26f) refuses any number not tied to a logged query-result id; and
the E43 red-team suite scores injection resistance in the nightly run, with the score published.

**Hardening notes for operators.** The compose files ship with development defaults, named as such:
default broker credentials, no TLS at the garage tier, and a dashboard bound to localhost. The
enterprise tier ships mTLS from an internal CA. A "do not run the garage tier on an untrusted
network" sentence sits at the top of the compose section, and CI check SEC-GATE-02 fails if a
compose file binds a service to `0.0.0.0` without a matching entry in `docs/security.md`.

**Testable, not prose.** SEC-GATE-01 asserts that SECURITY.md's surfaces table lists every route
registered by the REST app and every tool registered by the MCP server. Adding a tool without
documenting its reach fails CI. SEC-GATE-03 runs the sandbox escape corpus
(`tests/security/sandbox_escapes/`), a set of SQL and Python payloads that try file reads,
network calls, imports outside the allowlist, multi-statement injection, and resource exhaustion;
every payload must be refused or contained.

### 5.9 CONTRIBUTING.md, code of conduct, governance (C8)

`CONTRIBUTING.md` covers: `just bootstrap` and the two-step hook install (the tracked shell hooks
plus `pre-commit install`), the test tiers and which one to run when, the commit convention with
examples, the golden update flow and its required commit heading, the VAL-GATE rule (a statistical
change without a gate is not mergeable), the licence allowlist and what to do when a dependency is
denied, the synthetic-data rule (contributions must contain no employer or client artifacts, and
all data must be generated), the contributor agreement and how to sign it, the pull request
checklist, and the label taxonomy.

Inbound licence: a contributor licence agreement in `CLA.md`, not inbound-equals-outbound. The
owner has overridden the original MIT-and-DCO requirement: the outbound licence is Apache-2.0
plus a separately negotiated commercial licence, and a dual licence only holds if one party can
relicense the whole work, which a DCO does not grant. `CLA.md` grants the maintainer a
relicensing-capable copyright and patent licence while the contributor keeps their copyright.
Signing is two mechanical steps enforced in CI: a signatory line added to `CLA.md` matching
`^- @[A-Za-z0-9-]{1,39} [0-9]{4}-[0-9]{2}-[0-9]{2}$`, and a `Signed-off-by` trailer on every
commit (`git commit -s`), so the existing DCO check keeps its job as the trailer half of the
gate. See `LICENSING.md` for why the agreement exists.

`CODE_OF_CONDUCT.md`: Contributor Covenant 2.1 verbatim with the enforcement contact filled in.

Governance, one paragraph in `CONTRIBUTING.md` and expanded in `GOVERNANCE.md`: a single
maintainer holds release authority. Roadmap additions are accepted as entries in `roadmap.yaml`
with a requirement number, a phase, dependencies, and a rationale; they are then reordered into a
phase by the maintainer. Nothing is ever removed from the roadmap, which is project policy, not a
preference, and is enforced by INV-RM-01. Issues labelled `good-first-issue` must name the file,
the test to add, and the acceptance check, or the label is removed.

Label taxonomy: `phase:P0` through `phase:P6`, `req:C4` style requirement labels, `brick:lss`
style package labels, `type:milestone`, `type:bug`, `type:val-gate`, `good-first-issue`,
`help-wanted`, `ci:nightly`, `security`.

Issue templates in `.github/ISSUE_TEMPLATE/`: `bug.yml` (version, profile, seed, run manifest,
reproduction), `milestone.yml` (requirement number, phase, dependencies, rationale, acceptance),
`val-gate.yml` (statistic, named published reference with URL and retrieval date, proposed
tolerance), `question.yml`. `config.yml` disables blank issues and routes security reports to the
private channel.

### 5.10 Semver policy (C9)

One version number, in `VERSION`, injected into every package at build time by a build-backend
hook that reads that file. `VERSION` is the single source, not the git tag: `tag.yml` creates the
tag from `VERSION` (5.4), so deriving the version from the tag would make the two definitions
circular. A `static` job check asserts that every built wheel's metadata version equals the
contents of `VERSION`. Lockstep across bricks, as C9 needs.

Five contract surfaces, each with an explicit rule for what constitutes a major, minor, and patch
change:

| Surface                                           | Major (breaking)                                                                                                      | Minor (additive)                                                                 | Patch                                         |
| ------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------- | --------------------------------------------- |
| Python package APIs                               | remove or rename a public name, change a required parameter, narrow a return type, change a documented exception type | add a function, class, keyword argument with a default, or optional return field | fix behaviour that contradicted the docstring |
| REST / GraphQL (A6)                               | remove or rename a route, field, or enum value; change a field's type; add a required request field                   | add a route, add an optional request field, add a response field                 | fix a wrong value                             |
| MCP tool contracts (E2)                           | remove or rename a tool, remove an output field, add a required input                                                 | add a tool, add an optional input, add an output field                           | fix a wrong value                             |
| Event schemas (C3)                                | remove a field, retype a field, remove an enum value, add a required field                                            | add an optional field with a default, add an enum value                          | fix a description                             |
| facility.yaml, sensor catalog, metrics layer (C5) | remove a key, retype a key, add a required key without a migration, change a default in a way that changes results    | add an optional key, add a value to an enum, add a migration                     | fix validation messages                       |

Deprecation policy: a public name marked deprecated emits a `DeprecationWarning` naming the
replacement and the version in which it will be removed, survives at least two minor releases, and
is listed in the CHANGELOG's Deprecated section. Removal is a major bump.

Version zero: while the version is `0.y.z`, the minor position carries breaking changes, and the
CHANGELOG says so at the top. `1.0.0` publishes at the close of Phase 5, when every contract
surface above exists, is documented, and has a snapshot test. Phase 6's E-tier milestones ship as
`1.x` minors because they are additive by construction. See open question 5.

Phase-to-version map, which is also the CHANGELOG's section structure:

| Version            | Phase closed                                                  |
| ------------------ | ------------------------------------------------------------- |
| v0.1.0             | P1 walking skeleton                                           |
| v0.2.0             | P2 LSS engine with reference-validated tests                  |
| v0.3.0             | E1 hosted replay demo (pulled forward)                        |
| v0.4.0             | P3 sensor breadth, PdM, ERP/CMMS loop                         |
| v0.5.0             | P3b automation and robotics                                   |
| v0.6.0             | P3c process mining and VSM                                    |
| v0.7.0             | P3d planning                                                  |
| v0.8.0             | P3e supplier network and outbound                             |
| v0.9.0             | P3f returns                                                   |
| v0.10.0            | P3g cross-dock and e-commerce                                 |
| v0.11.0            | P3h transport and MEIO                                        |
| v0.12.0            | P3i upstream production                                       |
| v0.13.0 to v0.20.0 | 6a10 through 6a17, one minor each, in the source's order      |
| v0.21.0            | P4 CV and store-and-forward                                   |
| v1.0.0             | P5 polish, report, GIF, OPC UA bridge, mTLS; contracts frozen |
| v1.1.0 onward      | P6, one minor per E milestone in the source's order           |

### 5.11 Releases, CHANGELOG, and PyPI publishing (C9)

CHANGELOG follows Keep a Changelog 1.1.0 with `Added`, `Changed`, `Deprecated`, `Removed`,
`Fixed`, `Security`, plus two twinflow-specific sections per release: `Validation` (the VAL-GATE
delta, gates added and their references) and `Compatibility` (the C6 table row).

The `[Unreleased]` section is maintained by the inherited `post-commit` hook, which inserts a
bullet for every `feat`, `fix`, and `perf` commit and amends the commit so the changelog cannot
drift behind the code. Adaptation required for a public repo: the private version amends HEAD
unconditionally because that repo never pushes. Here the hook first runs
`git branch -r --contains HEAD`; if HEAD is already on a remote branch it prints a note and exits
without amending, because rewriting a pushed commit corrupts a public history. Entries are never
hand-edited; the only manual step is `just release-prepare <version>`, which promotes
`[Unreleased]` to a version section, inserts the compatibility row, and opens the release pull
request.

CI check `CHANGELOG-GATE-01`: a pull request touching `packages/**` must also touch
`CHANGELOG.md`, unless labelled `no-changelog`.

Publishing. `release.yml` publishes every brick to PyPI using Trusted Publishing, so no API token
exists in the repository. Each brick's metadata carries its own description, its own README as the
long description, `Homepage` pointing at the docs site's page for that brick, and the shared
`twinflow` keyword set. The flagship `twinflow` package is a metapackage that depends on every
brick at the exact lockstep version, so `pip install twinflow` gets everything and
`pip install twinflow-lss` gets one brick, which is A1's promise made real at install time.

Every release attaches: the per-artifact CycloneDX SBOMs, the aggregate SBOM, SLSA build
provenance attestations, `val-gates.json`, the scaling report and its CSVs, the agent scorecard,
and the compatibility table row. The release notes lead with what the phase makes possible and the
measured numbers that changed.

### 5.12 Dependency hygiene (C11)

Auditing. `pip-audit --strict` runs against the full workspace resolution exported from `uv.lock`
including every extra, on pull requests, on main, and weekly. `cargo audit` and
`cargo deny check advisories bans sources licenses` cover the Rust crate. A new advisory on the
weekly schedule opens an Issue labelled `security`; a new advisory on a pull request fails it.

The source states the allowlist as "MIT-compatible". The outbound licence was overridden from MIT
to Apache-2.0 plus a separately negotiated commercial licence (5.9), so the allowlist below is
stated as Apache-2.0-compatible. The substitution is recorded here rather than made silently,
because it is the reader's only clue that the two documents disagree on purpose. For the
permissive licences in the `allow` list the two readings select the same set; the difference bites <!-- docs-lint-ok STE-TERM-WORD allow is the literal key name in licenses.allow.toml -->
only on patent-clause interaction, which is why `Apache-2.0 WITH LLVM-exception` is enumerated
rather than assumed.

Licence allowlist. `licenses.allow.toml` defines three lists by SPDX identifier, using the current <!-- docs-lint-ok STE-TERM-WORD literal filename -->
identifiers from SPDX License List 3.28.0 (read from `https://spdx.org/licenses/licenses.json` on
2026-08-09, HTTP 200):

- `allow`: `MIT`, `BSD-2-Clause`, `BSD-3-Clause`, `Apache-2.0`, `ISC`, `PSF-2.0`, `Python-2.0`, <!-- docs-lint-ok STE-TERM-WORD allow is the literal key name in licenses.allow.toml -->
  `Unlicense`, `CC0-1.0`, `BSL-1.0`, `Zlib`, `MPL-2.0` (file-level copyleft, acceptable for an
  unmodified dependency), and the expression `Apache-2.0 WITH LLVM-exception`, whose exception
  identifier is in the SPDX exceptions list of the same version.
- `review`: `LGPL-2.1-or-later`, `LGPL-3.0-or-later`, `EPL-2.0`, `CDDL-1.1`, any dual licence
  needing an election, and any package resolving to `UNKNOWN`. A `review` licence needs an
  exception entry with a justification, an approver, an expiry date within 180 days, and a stated
  linkage.
- `deny`: `GPL-2.0-only`, `GPL-2.0-or-later`, `GPL-3.0-only`, `GPL-3.0-or-later`,
  `AGPL-3.0-only`, `AGPL-3.0-or-later`, `SSPL-1.0`, `BUSL-1.1`, the `CC-BY-NC` family
  (`CC-BY-NC-4.0`, `CC-BY-NC-SA-4.0`, `CC-BY-NC-ND-4.0`), and no licence at all. The bare forms
  `GPL-2.0`, `GPL-3.0`, and `AGPL-3.0` are deprecated identifiers in SPDX 3.28.0, so the policy
  loader accepts them on input, maps each to its `-only` and `-or-later` pair, and prints the
  rewrite. Without the map the policy silently fails to match a dependency that declares the old
  spelling, which is the worst outcome available: a denied licence that no gate reports.
- `deny_riders`: `Commons-Clause`. This is a licence rider rather than a licence, and it has no
  SPDX licence identifier, so it cannot live in `deny` without breaking the rule that every entry
  parses as an SPDX identifier. It is matched by substring against the raw licence text field
  instead, and the loader says which mechanism fired.

INV-LP-02 makes a copyleft runtime dependency unrepresentable: the policy loader refuses an
exception whose `linkage == "runtime"` and whose licence is copyleft, so the only path for such a
library is an optional extra in a brick that documents it, or removal. LIC-GATE-01 runs
`uv pip licenses` style resolution plus `cargo deny check licenses` and fails on any denied licence
or expired exception. The full resolved licence inventory is written to
`artifacts/ci/licenses.json`, attached to each release, and rendered into `docs/licenses.md`.

Process mining against this policy, resolved by D-14. The Python Package Index reports PM4Py at
version 2.7.23.3 with the licence field `AGPL 3.0` (read from `https://pypi.org/pypi/pm4py/json`
on 2026-08-09, HTTP 200). The policy loader maps that field to the `AGPL-3.0-only` and
`AGPL-3.0-or-later` pair, both of which sit in `deny`, and INV-LP-02 makes a runtime exception for
either unrepresentable. Section 13 of the AGPL triggers on network interaction, and this project
serves a dashboard, an MCP server, and an HTTP API, so importing the library at runtime would
place the whole work under AGPL and break the Apache-2.0 and commercial dual licence.

The ruling is that `twinflow-procmine` is written here, under Apache-2.0. It implements the
directly-follows graph, the inductive miner, token-based replay, alignment-based conformance as A
star search over the synchronous product net, variant analysis, rework-loop detection, and
per-activity cycle-time contribution. The capability is not reduced; its supplier changes. The
external anchors those algorithms are validated against are named in 5.5.

PM4Py stays in the repository as a development-only oracle. Its exception entry carries
`linkage = "test"`, it is installed only by the `just procmine-oracle` recipe and the
`agent-evals.yml` and nightly jobs that call it, and it is never a dependency of any published
wheel and never reachable from a served surface. Three checks hold that line:

- LIC-GATE-03a: no path under `packages/*/src/**` imports the oracle. An AST check, not a grep, so
  an aliased import is caught.
- LIC-GATE-03b: no built wheel or sdist declares the oracle in its dependency metadata, checked
  against the artifacts `uv build --all-packages` produced rather than against `pyproject.toml`.
- LIC-GATE-03c: the oracle's exception entry has `linkage = "test"` and an unexpired approval, and
  the loader refuses any other linkage for a licence in `deny`.

Each fails the release rather than warning. Whether a development-only AGPL oracle is acceptable
at all is a legal question rather than an engineering one, and D-14 says it needs the owner's own
legal read before release; open question 1 records that.

SBOM. `cyclonedx-py` produces a CycloneDX 1.6 JSON SBOM per Python artifact;
`cargo cyclonedx` produces one for the Rust crate; `tools/sbom_merge.py` produces the aggregate.
SBOM-GATE-01 fails the release if any SBOM is missing a `licenses` entry for a component, or if
the component set differs from the resolved lock.

Model and dataset licences (C11 into E25). The dataset card schema `schemas/artifacts/dataset_card.v1.json`
needs `license` (SPDX, in the `allow` list), `license_url`, `redistributable`, <!-- docs-lint-ok STE-TERM-WORD allow is the literal key name in licenses.allow.toml -->
`generation_seed`, `twinflow_version`, `config_hash`, `container_digests`, `ground_truth_labels`,
`intended_use`, `known_limitations`, and `model_licenses` (for cards describing a dataset produced
by or intended for a specific model, each entry naming the model, its base model, its licence, and
its source URL). LIC-GATE-02 validates every card in `datasets/` against the schema and fails if
`license` is outside the allowlist. twinflow's own emitted datasets carry a single project-wide
licence decision (see open question 10). No model weights are committed; weights are fetched at
run time by a loader that records the SHA-256 and asserts the licence against the allowlist before
use, so an E32 fine-tune cannot silently inherit a non-redistributable base model.

Update policy. Dependabot runs weekly, grouped: one pull request for Python patch updates, one for
Python minor, one for Rust, one for GitHub Actions. Patch-level groups auto-merge when CI is green.
Libraries declare version ranges; the compose and Helm tiers pin exact versions and container
digests, so the quickstart cannot break because an upstream published at the wrong moment.

### 5.13 Load-test harness and published scaling evidence (A4)

What is measured. For a device population of size N publishing at a stated rate through the real
broker into the real ingest path: offered events per second, achieved events per second,
end-to-end latency percentiles (p50, p95, p99, p99.9), broker CPU and RSS, ingest queue depth,
messages shed, device buffer high-water mark, and the count of backpressure events by stage.

How latency is measured honestly. End-to-end latency is stamped at device publish and read at
historian commit, both on the same host using a monotonic wall clock, so no clock skew enters the
number. The measurement is stated in the report, because a latency curve without a stated
measurement point is not evidence. Sim time is not used for this measurement, and the report says
so, since A4 is about the production-mode data path, not the simulation.

Topologies measured: single node garage tier (Mosquitto, DuckDB); single node growth tier (EMQX,
Postgres plus Delta); partitioned by ISA-95 area with one ingest worker per area against a shared
EMQX; and, once E13 exists, two sites with broker-to-broker bridging.

Stated hardware. `benchmarks/hardware.yaml` defines named profiles. Two are always published:
`ref-gh` (the GitHub-hosted `ubuntu-latest` standard runner, 4 vCPU, 16 GB, so anyone can
reproduce the curve for free) and `ref-a` (the author's own machine, described by class: core
count, RAM, storage class, OS, container runtime). Every chart axis label names the profile, and
the reproduction command is printed under the chart.

Backpressure, documented as a chain with a named policy and a named metric at each stage:

| Stage                                | Policy                                                                    | Metric                                                          | Behaviour at saturation                                                                                              |
| ------------------------------------ | ------------------------------------------------------------------------- | --------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------- |
| Device store-and-forward buffer (6c) | ring buffer, drop-oldest above `buffer_max_bytes`, with a dropped counter | `twinflow_device_buffer_bytes`, `twinflow_device_dropped_total` | the device keeps publishing its newest data and reports the gap; the fleet-health layer raises a finding             |
| MQTT QoS 1 inflight window           | block the publisher at `max_inflight`                                     | `twinflow_device_inflight`                                      | device publish blocks, which is visible as a rising buffer rather than silent loss                                   |
| Broker queue                         | EMQX per-session message queue with its own overload protection           | broker metrics scraped into the historian                       | broker sheds and reports; the harness records it                                                                     |
| Ingest consumer                      | bounded asyncio queue of size K, backpressure by not acknowledging        | `twinflow_ingest_queue_depth`                                   | the consumer stops acking, the broker queue grows, the device buffers; loss moves to the device, where it is visible |
| Batch writer                         | commit every M events or T seconds, whichever first                       | `twinflow_ingest_commit_lag_s`                                  | commit lag rises; the knee criterion usually binds here first                                                        |

The honest knee. `ScalingReport.knee()` finds the smallest device count at which p99 end-to-end
latency first exceeds 1000 ms, and separately the point at which achieved throughput stops
tracking offered throughput within 5%. Both are reported, the binding resource at each is named
from the metric that saturated first, and the README quotes the number with the hardware profile
in the same sentence. The report also states what the curve does not prove: it is a synthetic
device population on one host, not a multi-tenant production fleet.

Regression gate A4-GATE-01: the weekly run compares the knee against `benchmarks/baseline.json`
and fails when it regresses beyond the regression band. The band is not a round number chosen for
how it reads. It is measured: `just repeatability ref-gh` runs the same curve ten times on the
same hardware profile with the same seed and container digests, and writes the mean knee and the
run-to-run standard deviation to `benchmarks/repeatability.json`. The band is three standard
deviations of that measurement, which is the smallest regression the harness can distinguish from
its own noise. A gate set tighter than the harness's repeatability would fire on the runner rather
than on the code, which is the defect D-11 condition 3 names for stochastic quantities.

Until `benchmarks/repeatability.json` holds a measurement, A4-GATE-01 runs in reporting mode: it
publishes the observed change and does not fail. The interim band is open question 15, and the
`PENDING_REFERENCE` mechanism of 3.1 is what keeps that visible in the registry instead of letting
a placeholder number look like a validated one. Falsification, once the band exists: a knee
`device_count` or `achieved_eps` outside three measured standard deviations of the committed
baseline on the same profile and topology.

The baseline is updated only by a commit that says why. Raw CSVs and the plotting script are
committed, so the chart in the docs can be regenerated by a reader.

### 5.14 ADOPTION.md as a consulting maturity model (A5)

`adoption/maturity.yaml` is the source of truth; `ADOPTION.md` is generated from it by
`tools/render_adoption.py`, and CI fails if the committed markdown differs from the regenerated
one. The same file generates the README's "use just this part" table (A1), so the routing table
and the maturity model cannot drift apart.

Six stages, each with an entry test, the bricks to adopt, the deployment tier (A3), a payback
model, the prerequisite stage, and the failure mode of skipping ahead.

| Stage | Level | Name                         | Entry test (you are here if)                                                                    | Adopt first                                                                               | Tier                 |
| ----- | ----- | ---------------------------- | ----------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------- | -------------------- |
| S0    | 3.0   | Paper and clipboard          | cycle times are estimated, not measured; the last process study was a stopwatch and a clipboard | `twinflow-sensors` catalogue and `twinflow-historian`                                     | garage               |
| S1    | 3.0   | Instrumented                 | data is collected but nobody judges it; dashboards exist and no one acts on them                | `twinflow-lss`, then `twinflow-procmine`                                                  | garage               |
| S2    | 3.5   | Connected                    | systems talk but through point-to-point integrations; there is no namespace                     | `twinflow-uns`, `twinflow-fleet`                                                          | growth               |
| S3    | 4.0   | Modelled                     | you can answer what happened but not what would happen                                          | `twinflow-twin`, the what-if engine                                                       | growth               |
| S4    | 4.5   | Predictive and optimised     | you can answer what would happen but you choose by judgement                                    | `twinflow-forecast`, `twinflow-optimise`, MEIO                                            | growth or enterprise |
| S5    | 5.0   | Autonomous and human-centric | the machine layer is optimised and the human and sustainability layers are still unmeasured     | `twinflow-agent` with the accuracy stack, ergonomics and workforce layers, carbon and ESG | enterprise           |

Each stage's payback model is a named formula with named inputs, not a claim:

- S0: value of a credible baseline. `payback_months = implementation_cost / (baseline_error_pct * annual_labour_cost * improvement_capture_rate)`, where `baseline_error_pct` comes from the MSA study the stage recommends running first. The honest statement: this stage produces no direct saving, it produces the ability to measure one, and skipping it means every later number rests on estimates.
- S1: findings-driven scrap and rework reduction. Inputs: finding rate by severity from the LSS engine on the reader's own data, current COPQ split, and the historical capture rate.
- S2: unplanned downtime avoided, driven by mean time to detect. Inputs: MTTD before and after, downtime cost per hour, failure frequency.
- S3: capex decisions defended before spend. Inputs: the avoided cost of one wrong capacity decision, measured on the shipped profiles as the delta between the naive choice and the twin-ranked choice.
- S4: inventory turns and service level at lower cost. Inputs: safety stock before and after, carrying rate, fill-rate target.
- S5: decision latency, injury cost avoided, and AI cost per answered question, from the E45 unit economics.

Every payback number printed in ADOPTION.md is computed by the twin on the three A2 profiles and
is labelled synthetic in the same sentence. INV-MS-02 enforces the disclaimer. This is not
decorative caution: an adoption document on a public portfolio repo that implies client results
would violate the repo's own IP hygiene rule.

Self-assessment: `twinflow adopt assess` asks the entry tests interactively (or reads answers from
a file), returns the stage, the recommended brick order, the deployment tier, and the payback model
with the reader's own inputs substituted. Because the model is data, it is unit tested: a fixture
answer set maps to a known stage, and a property test asserts that answering "yes" to a
higher-stage entry test while failing a lower one always returns the lower stage with the skip
warning attached (INV-MS-03).

### 5.15 Docs site (mkdocs-material)

`mkdocs.yml` at the root, Material theme, navigation mirroring the reader-by-role routing:
Start here, Quickstart, Architecture, Bricks (one page per package, generated), Validation (the
VAL-GATE registry), Adoption, Configuring your facility (A2's CONFIGURING.md), Scaling evidence,
Security, Contributing, Roadmap, Changelog and compatibility.

Plugins: `mkdocstrings[python]` with `mkdocs-gen-files` and `mkdocs-literate-nav` generating one
API page per brick from docstrings; Material's native Mermaid support for the architecture and
dependency diagrams; `mike` for versioned docs (`dev`, `latest`, and each `vX.Y`); and
`mkdocs-macros-plugin` reading `artifacts/ci/*.json` so every number printed in the docs comes from
a CI artifact. A headline number in the README or docs that no CI job produced is impossible by
construction, which is the same discipline the agent's grounding checker applies to answers.

Gates:

- DOC-GATE-01: `mkdocs build --strict` fails on a broken internal link, a missing nav entry, or a
  docstring reference that does not resolve.
- DOC-GATE-02: `lychee` external link check, nightly only, with a per-domain rate-limit allowlist,
  so a flaky third-party host never fails a pull request.
- DOC-GATE-03 / README-GATE-01: every published brick has a README containing an install line
  `pip install twinflow-<brick>` and a fenced example; `tools/readme_examples.py` extracts every
  fenced `python` block marked `<!-- exec -->` and executes it in a clean environment with only
  that brick installed. A1's promise that one brick installs and works alone is a test,
  not a claim.
- DOC-GATE-04: `tools/arch_table_check.py` parses ARCHITECTURE.md and asserts that every directory
  under `packages/` and every service in every compose file appears in the ISA-95 layer map table
  with a non-empty ISA-95 level, Purdue level, and real-world counterpart, and in the E36
  compute-placement table with a non-empty tier and reason. The architecture document cannot drift
  behind the code.
- DOC-GATE-05: the humaniser gate runs repo-wide on the diff, so no em dash, en dash, or curly
  quote enters the documentation either.

Deployment: `docs.yml` publishes to GitHub Pages on main and on release. The E1 replay viewer is
published to the same Pages site under `/replay/`, so one Pages deployment serves the docs and the
demo, and the README's first three lines link the replay.

Badges in the README, all of them earned by a job: CI status, VAL-GATES count (shields endpoint
reading the published `val-gates-badge.json`), PyPI version, Python versions, licence, docs,
OpenSSF Scorecard.

### 5.16 ROADMAP.md, GitHub Issues, and the never-delete rule

`roadmap.yaml` is the machine-readable backlog: one entry per milestone with `id`, `title`,
`requirement_ids`, `phase`, `order`, `depends_on`, `status`, `rationale`, and `issue_number`.

`tools/roadmap_sync.py`:

1. Validates `roadmap.yaml` against `schemas/config/roadmap.v1.json`.
2. Asserts INV-RM-01 by diffing the id set against the file at the previous release tag. A removed
   id fails with the message "milestones are reordered, never deleted; move it to a later phase
   instead". This is the constraints paragraph enforced by a script rather than by discipline.
3. Creates or updates one GitHub Issue per milestone: title from `title`, body from `rationale`
   plus the requirement numbers plus a task list of `depends_on` rendered as issue links, labels
   `phase:*`, `req:*`, `brick:*`, `type:milestone`, and the GitHub Milestone set to the phase.
4. Writes `issue_number` back into `roadmap.yaml` in the same commit.
5. Regenerates `ROADMAP.md` from the same data, including a Mermaid dependency graph, so the
   markdown and the Issues are two renderings of one source.
6. Refuses to close an Issue whose milestone is still open in the file, and refuses to reopen one
   whose milestone is `done`.

A GitHub Project board grouped by phase gives the public backlog view. The board, the Issues, and
ROADMAP.md all derive from `roadmap.yaml`, so the program-management story a reader sees is the
same one the build actually follows.

### 5.17 Git hooks and commit discipline (inherited, adapted)

Installed by `just hooks`, which runs `tools/hooks/install.sh`. The install copies hooks into
`.git/hooks` rather than setting `core.hooksPath`, so machine-local hooks survive, which is the
inherited behaviour and the reason for it. A second step, `pre-commit install`, installs the
framework-managed hooks (ruff, taplo, yamllint, codespell). CONTRIBUTING.md states both steps.

| Hook                 | Behaviour                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                | Change from the private monorepo                                                                                                                                                                                                                                                                                                                                   |
| -------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| `prepare-commit-msg` | strips AI attribution from the message: any `Co-Authored-By` trailer naming an agent or its vendor, any generated-with footer an agent tool appends, and the robot emoji. The patterns live in `tools/hooks/attribution-patterns.txt` rather than in this table, so the hook and its test read one list and this document does not have to restate strings that a prose gate then flags                                                                                                                                                                                                                  | unchanged, and the rationale strengthens: this repository's commit history is a portfolio artifact that a hiring manager may read, and the source explicitly asks for a natural commit history that tells the story of the build                                                                                                                                   |
| `commit-msg`         | subject matches the conventional-commit pattern held in `tools/hooks/commit-subject.regex`, whose type set is feat, fix, refactor, test, docs, chore, and perf, whose scope matches `[a-z0-9_-]+`, and whose description starts with a lowercase letter, a digit, or a space. The pattern lives in a file rather than in this table because a regular expression full of alternation bars cannot be written inside a Markdown cell. Any multi-line body carries at least one standalone ALL-CAPS section heading drawn from the approved vocabulary, and git's leftover `# Conflicts:` block is rejected | vocabulary extended with `GOLDEN` (golden-file changes, required by GOLDEN-GATE-01) and `VALIDATION` (a VAL-GATE added or a tolerance changed); the scope is validated against the set of directory names under `packages/` and `crates/` plus a fixed extra set (`ci`, `docs`, `schemas`, `hooks`, `release`, `roadmap`, `deps`), so a typo'd scope fails locally |
| `pre-commit`         | humaniser gate (em and en dashes anywhere, curly quotes and emoji in source, prose `--` in comments), comment judge (the nine comment rules plus fuzzy prose patterns, failing open when the CLI is absent), `ruff format --check` and `ruff check` on staged Python, `rustfmt --check` on staged Rust, `twinflow-repolint check` on staged package files, `gitleaks protect --staged`, and the IP-hygiene scan                                                                                                                                                                                          | adds repolint, gitleaks, and the IP-hygiene scan; drops the multi-session commit fence, which solved a problem specific to the private repo's concurrent-agent setup                                                                                                                                                                                               |
| `post-commit`        | inserts the CHANGELOG bullet for feat, fix, and perf commits and amends the commit so the changelog never drifts behind the code                                                                                                                                                                                                                                                                                                                                                                                                                                                                         | adds a pushed-commit guard: if `git branch -r --contains HEAD` is non-empty the hook prints a note and exits without amending, because rewriting a pushed commit corrupts a public history                                                                                                                                                                         |
| `pre-push`           | runs `tools/ci-local.sh` (the fast lane), skipping the compile-heavy checks when the tree is dirty and saying so rather than reporting a false pass                                                                                                                                                                                                                                                                                                                                                                                                                                                      | reframed from a CI-cost guard to a latency guard; the runner-busy check is removed because there is no self-hosted runner here                                                                                                                                                                                                                                     |
| `post-merge`         | prunes a linked worktree once its branch merges and its tree is clean                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                    | unchanged                                                                                                                                                                                                                                                                                                                                                          |

New hook behaviour unique to twinflow, the IP-hygiene scan (`tools/ip_hygiene.py`, run from
`pre-commit` and again in `pre-push`): it scans staged added lines against a denylist of client and
employer names held in `.ip-denylist`. That file is gitignored and never committed, because
committing a list of client names to a public repository defeats its own purpose;
`.ip-denylist.example` is committed containing placeholder entries and instructions. The scan also
flags generic markers of internal provenance (file paths under corporate share drives, document
control numbers, "internal use only" strings). It fails the commit with the offending line and no
suggestion to bypass. CI runs a reduced version (IP-GATE-01) against the generic markers only,
since the denylist cannot exist on a runner.

Commit discipline, stated because the history is an artifact:

- One logical change per commit. `just commit-check` warns when a staged set spans more than two
  packages or more than fifteen files without a `chore(sweep)` scope.
- No AI attribution, ever, enforced by `prepare-commit-msg` and by an empty attribution setting in
  the local agent configuration.
- Commits are signed with SSH signing, so every commit shows Verified. This is free and it reads
  well on a public repository.
- Squash merging is disabled in the repository settings. Rebase merging is the only merge method,
  which keeps a linear history while preserving the individual one-logical-change commits. Squash
  merging would collapse a phase's build story into one commit, which is exactly the "single giant
  commit reads as generated" failure the source names.
- Branch protection on `main`: the `all-green` check, linear history, and a pull request are all
  needed to merge; stale approvals are dismissed and conversations must be resolved. The maintainer can
  self-approve, since this is a single-maintainer repo, and CONTRIBUTING.md says so rather than
  pretending otherwise.

### 5.18 The local CI mirror

`tools/ci-local.sh` mirrors the pull-request job set, skipping any check whose tool is missing with
a printed note, and ending with a pass/fail/skip summary. Modes: default fast (format, lint,
repolint, humaniser, unit), `--full` (adds property, e2e, goldens, val-gates, determinism, rust),
`--security` (adds pip-audit, cargo-audit, gitleaks, semgrep, licence allowlist). It calls the same
`just` recipes CI calls. Its purpose here is latency, not cost: a 90 second local failure beats an
8 minute CI failure, and `pre-push` runs the fast mode automatically.

## 6. Configuration

Every file below validates against a published JSON Schema at load with line-numbered,
suggestion-bearing errors, per C5, and each has a `--check` mode used in CI.

### 6.1 `repolint.toml`

```toml
[packages]
# Package source and tests. tools/ is deliberately outside the checker's scope:
# repo-local scripts are not library code and never run inside a simulation.
include = ["packages/*/src/**/*.py", "packages/*/tests/**/*.py", "tests/**/*.py"]
exclude = ["**/_vendor/**"]

[kernel_boundary]
paths = [
  "packages/twinflow-kernel/src/twinflow/kernel/clock.py",
  "packages/twinflow-kernel/src/twinflow/kernel/rng.py",
  "packages/twinflow-kernel/src/twinflow/kernel/net.py",
  "packages/twinflow-kernel/src/twinflow/kernel/storage.py",
]

[test_boundary]
paths = ["packages/*/tests/**/*.py", "tests/**/*.py"]
lifted = ["TFD003", "TFD004", "TFD005", "TFD006"]   # TFD001 and TFD002 still apply

# The complete allowance set of 5.7. INV-RL-03 compares this against the
# literal set held in tests/unit/test_repolint_allowances.py.
[[measurement_boundary]]
rule_code = "TFD001"
path_glob = "packages/twinflow-valgate/**"
justification = "GateResult.duration_s for the gate report"
owning_requirement = "component 5 validation"

[[measurement_boundary]]
rule_code = "TFD001"
path_glob = "packages/twinflow-testkit/**"
justification = "per-test duration for the tier budget report"
owning_requirement = "C4"

[[measurement_boundary]]
rule_code = "TFD001"
path_glob = "packages/twinflow-loadtest/**"
justification = "end-to-end latency is a wall-time quantity by definition"
owning_requirement = "A4"

[[measurement_boundary]]
rule_code = "TFD003"
path_glob = "packages/twinflow-loadtest/**"
justification = "the harness drives a real broker over a real socket in production mode"
owning_requirement = "A4"

[rules]
TFD001 = "error"   # wall clock
TFD002 = "error"   # unseeded RNG
TFD003 = "error"   # raw network
TFD004 = "error"   # raw filesystem
TFD005 = "error"   # wall-clock sleeps
TFD006 = "error"   # hash and iteration-order leakage
TFB001 = "error"   # cross-package private import
TFB002 = "error"   # undeclared cross-package dependency

[escapes]
max_escapes = 0
require_reason = true
```

Validation: `paths` entries must exist; a rule set to anything other than `error`, `warn`, or
`off` is rejected; `max_escapes` must be a non-negative integer; every `measurement_boundary`
entry has a non-empty `justification` and an `owning_requirement` that resolves to a requirement
number this repository declares (INV-RL-04); and the loaded `measurement_boundary` set equals the
literal set the unit test holds (INV-RL-03), so widening it is a reviewed edit.

### 6.2 `phases.yaml`

```yaml
version: 1
phases:
  - id: P2
    title: LSS engine with reference-validated tests
    status: open # planned | open | closed
    order: 20
    depends_on: [P1]
    declared_tag: null
    changelog_section: null
    tag_observed: false
    exit_criteria:
      - capability report generated for all three A2 profiles
      - every statistic validated against its named published reference
    val_gates:
      [
        VAL-NUM-001,
        VAL-NUM-002,
        VAL-SPC-001,
        VAL-SPC-004,
        VAL-CAP-001,
        VAL-MSA-001,
        VAL-MSA-002,
        VAL-MSA-004,
        VAL-HYP-001,
      ]
    no_gates_justification: null
```

Validation: `status` enum; `depends_on` ids must exist and must not form a cycle; `val_gates` ids
must match the gate id pattern; `val_gates: []` needs a non-empty `no_gates_justification`;
`status: closed` needs `declared_tag` and `changelog_section` (INV-PH-04a). `tag_observed` is
written by `release.yml` after the tag is pushed and is never hand-edited; the field names here
match the `Phase` model in 3.4 exactly, so a reader can move between the two without translating.

### 6.3 `roadmap.yaml`

```yaml
version: 1
milestones:
  - id: E9
    title: Optimisation engine over twin configurations
    requirement_ids: [E9]
    phase: P6
    order: 900
    depends_on: [P3b, P3d]
    status: backlog # backlog | planned | in-progress | done
    rationale: feeds the scenario-ranking table the agent returns
    issue_number: null
```

Validation: ids unique and stable; `depends_on` resolves; `phase` exists in `phases.yaml`;
`requirement_ids` non-empty; the id set is a superset of the id set at the previous release tag.

### 6.4 Config schema versions read by the upgrader

The upgrader reads a `schema_version` key at the root of each config kind:

| File                          | Key              | Type                 | Validation                                                                                                        |
| ----------------------------- | ---------------- | -------------------- | ----------------------------------------------------------------------------------------------------------------- |
| `facility.yaml`               | `schema_version` | string `MAJOR.MINOR` | must be a version the upgrader knows; unknown versions fail with the list of known versions and the nearest match |
| `sensors/catalog.yaml`        | `schema_version` | string               | same                                                                                                              |
| `metrics/semantic_layer.yaml` | `schema_version` | string               | same                                                                                                              |
| `quality/spec_limits.yaml`    | `schema_version` | string               | same                                                                                                              |

Every config file also carries `twinflow_min_version`, so loading a config newer than the
installed code fails with "this config needs twinflow >= X, you have Y" rather than a schema error
that says nothing useful.

### 6.5 `licenses.allow.toml` <!-- docs-lint-ok STE-TERM-WORD literal filename -->

```toml
[policy]
spdx_list_version = "3.28.0"     # the list the ids below were checked against
allow  = ["MIT", "BSD-2-Clause", "BSD-3-Clause", "Apache-2.0", "ISC", "PSF-2.0",  # docs-lint-ok STE-TERM-WORD allow is the literal TOML key
          "Python-2.0", "Unlicense", "CC0-1.0", "BSL-1.0", "Zlib", "MPL-2.0",
          "Apache-2.0 WITH LLVM-exception"]
review = ["LGPL-2.1-or-later", "LGPL-3.0-or-later", "EPL-2.0", "CDDL-1.1", "UNKNOWN"]
deny   = ["GPL-2.0-only", "GPL-2.0-or-later", "GPL-3.0-only", "GPL-3.0-or-later",
          "AGPL-3.0-only", "AGPL-3.0-or-later", "SSPL-1.0", "BUSL-1.1",
          "CC-BY-NC-4.0", "CC-BY-NC-SA-4.0", "CC-BY-NC-ND-4.0"]

# Riders, not licences. These have no SPDX licence id, so they are matched
# against the raw licence text rather than parsed.
deny_riders = ["Commons-Clause"]

# Deprecated ids that upstream metadata still uses, mapped on load and printed.
[deprecated_aliases]
"GPL-2.0"  = ["GPL-2.0-only", "GPL-2.0-or-later"]
"GPL-3.0"  = ["GPL-3.0-only", "GPL-3.0-or-later"]
"AGPL-3.0" = ["AGPL-3.0-only", "AGPL-3.0-or-later"]
"AGPL 3.0" = ["AGPL-3.0-only", "AGPL-3.0-or-later"]   # the string PM4Py publishes

[[exceptions]]
package     = "pm4py"
version     = "==2.7.23.3"
license     = "AGPL 3.0"
linkage     = "test"               # runtime | build | test | optional-extra
justification = "development-only conformance oracle per D-14; never imported from package source, never in a published wheel, never served. LIC-GATE-03a/b/c hold that line."
approved_by = "maintainer"
approved_on = "2026-08-09"
expires     = "2027-02-05"

[datasets]
emitted_dataset_license = "CC-BY-4.0"   # see open question 10
```

Validation: every entry in `allow`, `review`, and `deny` parses as an SPDX licence identifier or <!-- docs-lint-ok STE-TERM-WORD allow is the literal key name in licenses.allow.toml -->
expression against the list version named in `spdx_list_version`; a deprecated identifier is
rewritten through `deprecated_aliases` and the rewrite is printed; `deny_riders` entries are
matched as substrings and never parsed; a package cannot appear in two lists; `expires` is within
180 days of `approved_on`; `linkage = "runtime"` with a copyleft licence is refused by the loader
(INV-LP-02). The identifiers above were checked against SPDX License List 3.28.0 on 2026-08-09,
where `Commons-Clause` is absent and `LLVM-exception` appears in the companion exceptions list.

### 6.6 `benchmarks/hardware.yaml` and `benchmarks/baseline.json`

```yaml
profiles:
  - id: ref-gh
    cpu_class: "GitHub-hosted standard runner for public repositories, x64"
    physical_cores: 4
    logical_cores: 4
    ram_gb: 16
    storage_class: "14 GB SSD, runner-provided"
    os: "ubuntu-24.04"
    container_runtime: "docker 27.x"
    spec_source: "https://docs.github.com/en/actions/reference/runners/github-hosted-runners"
    spec_retrieved: "2026-08-09"
    spec_http_status: 200
    notes: "free to reproduce; the baseline anyone can rerun"
```

The `ref-gh` numbers are GitHub's published specification for the standard Linux runner on public
repositories (4 CPU, 16 GB RAM, 14 GB SSD, x64), not a measurement taken here, which is why the
profile carries the URL, the retrieval date, and the status code as fields rather than as a
comment. `ref-a`, the author's own machine, carries the same fields with `spec_source: self` and
is described by class; open question 9 asks whether to name the exact CPU model.

`baseline.json` holds, per profile and topology, the committed knee (`device_count`,
`achieved_eps`, `binding_resource`) and the run manifest that produced it (seed, container
digests, twinflow version). `repeatability.json` holds, per profile and topology, the mean knee
and the run-to-run standard deviation over ten repeats, which is where A4-GATE-01's band comes
from (5.13). A4-GATE-01 reads both, and fails to run rather than guessing when the second is
absent.

### 6.7 `adoption/maturity.yaml`

Keys per stage: `id`, `level`, `name`, `entry_test` (list of yes/no questions), `bricks` (must
resolve to published package names), `deployment_tier`, `prerequisites`, `failure_mode`, and
`payback_model` with `headline_metric`, `formula`, `inputs` (each naming where the value comes
from), `worked_example_profile` (one of the three A2 profiles), and `synthetic_disclaimer: true`.

### 6.8 Tier budgets in `pyproject.toml`

```toml
[tool.twinflow.testkit]
# One home for these numbers. 5.3 states them, BUDGET-GATE-02 reads them from
# here, and a docs macro renders 5.3's table from this table, so the two cannot
# disagree. The nightly budget is per matrix cell, not per workflow.
tiers = [
  { id = "static",   marker = "",         budget_s = 180,  hard_fail_ratio = 1.00 },
  { id = "unit",     marker = "unit",     budget_s = 120,  hard_fail_ratio = 1.25, max_test_s = 0.2 },
  { id = "property", marker = "property", budget_s = 420,  hard_fail_ratio = 1.25 },
  { id = "e2e",      marker = "e2e",      budget_s = 420,  hard_fail_ratio = 1.20 },
  { id = "nightly",  marker = "nightly",  budget_s = 1800, hard_fail_ratio = 1.10 },
]
setup_reserve_s = 45
require_marker = true
timing_out = "artifacts/ci/tier-timing.json"
```

The `static` row carries an empty marker because tier 0 is not a pytest tier. It is listed anyway
so BUDGET-GATE-02 rule 2 can check the `static` job the same way it checks the others, rather than
having one job outside the arithmetic.

### 6.9 CI budget

`.github/ci-budget.yml` lists per-job budgets in seconds and the aggregate p50 and p95 targets.
`tools/ci_budget.py` reads it and the run's job durations. On `push: main` it also queries
the last 20 runs and fails on a median breach.

## 7. Testing

Everything in this section has tests of its own. A gate with no test proving it can fail is a gate
nobody trusts.

### 7.1 Unit tests (tier 1)

- `twinflow-repolint`: one positive fixture and one negative fixture per rule, plus an
  escape-annotation fixture per rule, plus a fixture proving the AST checker catches aliased
  imports (`from time import time as t`, `import numpy.random as r`, `getattr(time, "time")` is
  documented as out of reach and is instead covered by DET-GATE-01).
- `twinflow-valgate`: registration rejects a gate with no reference, with a duplicate id, with a
  malformed id, and with an empty `requirement_ids`. Tolerance kinds each have a table-driven test
  including boundary values and NaN handling.
- `twinflow-migrate`: each registered config migration has a unit test with a before and after
  document. The historian migrator's checksum guard has a test that mutates an applied migration
  file and asserts the failure.
- `twinflow-testkit`: each invariant predicate has a passing case and at least two distinct
  failing cases, and the failure message is asserted to contain the counterexample.
- `twinflow-loadtest`: percentile computation against a known distribution; the knee finder against
  hand-built sample series with a knee at a known index; INV-LT-01 to INV-LT-03 validation of a
  malformed report.
- `tools/ci_budget.py`, `tools/roadmap_sync.py`, `tools/readme_examples.py`,
  `tools/arch_table_check.py`, `tools/ip_hygiene.py`: each against recorded fixtures.

### 7.2 Property-based invariants (tier 2)

The twenty-four named invariants in 5.3 are the suite, matching `invariants.CATALOGUE`, which
INV-TT-01's companion test asserts holds exactly twenty-four entries. Each is implemented in
`packages/twinflow-testkit/src/twinflow/testkit/invariants.py` and exercised from
`tests/property/test_<invariant>.py` against generated inputs. Additional properties owned by this
section's own machinery:

- PROP-GOLD-01 normaliser idempotence: `normalise(normalise(x)) == normalise(x)` for every
  registered normaliser over generated artifact bytes.
- PROP-GOLD-02 volatility blindness: for a generated artifact, injecting any combination of
  wall-clock timestamps, host names, absolute paths, and version strings into the declared volatile
  fields leaves the normalised bytes unchanged.
- PROP-GOLD-03 sensitivity: changing any non-volatile numeric field by more than the comparator's
  tolerance always produces a diff. A normaliser that hides real changes is worse than none.
- PROP-CFG-01 upgrade totality: for every pair of registered config versions `i < j`, upgrading a
  generated valid `i` document to `j` yields a document that validates against the `j` schema.
- PROP-CFG-02 upgrade idempotence: upgrading a document already at the terminal version is a
  no-op producing a byte-identical file.
- PROP-CFG-03 comment preservation: for a generated document with comments at random positions,
  the upgraded document retains every comment.
- PROP-VG-01 tolerance monotonicity: for a fixed measured and expected pair, widening the tolerance
  never turns a PASS into a FAIL.
- PROP-RL-01 escape accounting: for a generated file with `k` annotated escapes, the reported
  escape count is exactly `k` and the violation count is zero.
- PROP-LIC-01 policy totality: for a generated dependency set with licences drawn from the union
  of the three lists, the policy decision is exactly one of `allow`, `review`, or `deny`, and no licence <!-- docs-lint-ok STE-TERM-WORD the three list names in licenses.allow.toml -->
  is unclassified.

### 7.3 Seeded end-to-end scenarios (tier 3)

Nine scenario runs at the full set, three profiles times three scenario classes:

1. `nominal`: a clean shift, no injected faults. Produces whichever of GOLD-CAP, GOLD-VSM, and
   GOLD-FIN exist at the current release.
2. `degraded`: injected sensor drift, one crash-looping device, one broker outage with
   store-and-forward recovery. Produces GOLD-CAP with the findings section populated, and asserts
   INV-NET-01 held across the outage.
3. `whatif`: a scenario applied through the what-if engine, before and after samples compared by
   the LSS engine's hypothesis layer, producing a future-state VSM golden and the scenario-ranking
   table.

The set reaches nine runs at v0.6.0 and not before. At Phase 1 there is one profile (`micro`) and
one golden family (GOLD-CAP), so the tier runs three scenario classes against one profile. The
profile set widens to three at v0.4.0 and GOLD-VSM arrives at v0.6.0, per the first-produced table
in 5.3. The runner reads `tests/goldens/manifest.yaml` for `first_produced_at` and reports
`SKIP (not produced until vX.Y.0)` for a family that does not exist yet, rather than passing
silently or failing on a missing artifact. A test asserts that the number of runs the tier
executes equals the number the manifest implies for the current version, so the count in this
paragraph cannot drift away from the code.

Each run records its seed and config hash in `tests/goldens/manifest.yaml`. Every run also asserts
the run manifest carries every field this section names (the 5.4 events table), because a run that
cannot describe itself cannot be replayed.

The garage-tier compose run is not in this tier. It runs once per pull request in the `quickstart`
job (5.3, 5.4), executing the same command sequence the README quickstart prints, from a clean
checkout, timed, with an empty secret context. If it takes longer than 300 seconds the job fails,
because the source makes the five-minute quickstart a requirement of every phase, not a Phase 5
goal. Running it here as well would run the same three-hundred-second sequence twice per pull
request and prove nothing the first run did not.

### 7.4 VAL-GATE registry tests, including the meta gate

- Registry invariants INV-VG-01 to INV-VG-08 each have a failing fixture. INV-VG-07's fixture
  declares a `coverage 0.02` tolerance at nominal 0.90 over 200 replicates, whose binomial floor is
  `3 * sqrt(0.90 * 0.10 / 200) = 0.0636`, and asserts registration fails with both numbers printed.
  INV-VG-08's fixture declares `absolute 1e-4` against a quantity whose `printed_precision` is 2
  and asserts the same.
- Bidirectional completeness: a gate id in `phases.yaml` with no implementation fails; a declared
  gate whose phase is absent from `phases.yaml` fails.
- Phase closure: a fixture repository state with a closed phase and one failing gate makes
  `phase-closure` exit non-zero with the gate id in the message. A second fixture uses a gate at
  `PENDING_REFERENCE` and asserts closure is refused for that too, since a pending gate is not a
  passing gate.
- VAL-META-001, the meta gate that gives the registry teeth. A mutation harness applies a fixed set
  of deliberate defects to the statistical implementations (return `Cp` where `Cpk` is asked for;
  use `n` instead of `n-1` in the variance; use the wrong `d2` constant for the moving range;
  swap the Gage R and R error terms; drop the Bonferroni correction in the multivariate limits) and
  asserts that each defect makes at least one REFERENCE gate fail. A validation suite that passes
  against a broken implementation is the failure this gate exists to catch, and it is checked on
  every run, not once. The mutation-adequacy idea it applies is DeMillo, Lipton, and Sayward's,
  "Hints on Test Data Selection: Help for the Practicing Programmer", Computer 11(4), 34-41, 1978,
  DOI 10.1109/C-M.1978.218136, confirmed through the Crossref REST API on 2026-08-09, HTTP 200.
  The criterion is a mutation score of 1.0 over the declared mutant set, and the falsification is
  one surviving mutant.
- Tolerance sensitivity (VAL-META-002): for each REFERENCE gate, perturbing the expected value by
  twice that quantity's tolerance flips the gate to FAIL. This catches a tolerance so loose it
  validates nothing, and it is the same mutation-adequacy argument applied to the tolerances
  rather than to the implementations. Falsification: any REFERENCE gate that still passes at twice
  its own tolerance.

### 7.5 Determinism and lint tests

- DET-GATE-01, DET-GATE-02, DET-GATE-03 as specified in 5.7.
- A negative test: a fixture module containing a `time.time()` call outside the kernel makes
  `twinflow-repolint check` exit non-zero with the file, line, and rule code.
- A backstop test: temporarily allowing TFD002 in a fixture package and running the reference
  scenario twice produces different hashes, proving DET-GATE-01 detects what the lint would have
  prevented. This proves the two mechanisms are genuinely redundant rather than both vacuous.

### 7.6 Migration and compatibility tests

- MIG-GATE-01: for every release listed in `reads_runs_from`, the committed fixture run under
  `tests/fixtures/compat/runs/<release>/` opens and its manifest parses. For every release in
  `reads_configs_from`, the fixture config upgrades and validates.
- MIG-GATE-02: applying all historian migrations from empty produces a schema identical to the
  schema produced by the current `CREATE TABLE` definitions, compared structurally. This is the
  check that stops the migration chain and the fresh-install schema from diverging, which is the
  most common migration bug.
- A test asserts that a migration file edited after being recorded as applied fails the checksum
  guard.
- A test asserts the compat table generated from the fixtures equals the committed
  `docs/compatibility.md`.

### 7.7 Dependency hygiene tests

- LIC-GATE-01 against a fixture resolution containing one denied licence asserts a non-zero exit
  and the package name in the message. A second fixture, with an expired exception, asserts the
  same.
- INV-LP-02: a fixture policy declaring a runtime copyleft exception fails to load.
- Deprecated identifier mapping: a fixture dependency declaring the bare string `AGPL 3.0` resolves
  through `deprecated_aliases` to the `AGPL-3.0-only` and `AGPL-3.0-or-later` pair, is denied, and
  the printed message names both the input string and the rewrite. Without this test the policy
  would silently fail to match the exact string PM4Py publishes.
- Rider matching: a fixture dependency whose licence text contains `Commons-Clause` is denied by
  `deny_riders`, and the message says the rider mechanism fired rather than the SPDX one.
- LIC-GATE-02: a dataset card missing `license`, or carrying a licence outside the allowlist, or
  missing `model_licenses` when it declares a model-produced dataset, fails validation.
- LIC-GATE-03a: a fixture package whose source imports the process-mining oracle fails, including
  the aliased-import form, since the check is over the AST rather than over the text.
- LIC-GATE-03b: a fixture wheel declaring the oracle in its dependency metadata fails, and the
  check reads the built artifact rather than `pyproject.toml`, because those two can disagree.
- LIC-GATE-03c: a fixture exception for the oracle with `linkage = "runtime"` or `optional-extra`
  fails to load, and only `test` is accepted.
- SBOM-GATE-01: an SBOM whose component set differs from the resolved lock fails; a component with
  no `licenses` entry fails.
- A test asserts the model-weight loader refuses a weight file whose recorded licence is not in the
  allowlist, and refuses one whose SHA-256 does not match.

### 7.8 Load-test harness tests

- Harness self-accuracy: run the harness in simulation mode against the in-memory network with a
  latency distribution whose population quantiles are known in closed form, drawing 100000 samples
  per replicate over 50 seeded replicates. The reported p50, p95, and p99 must fall within three
  bootstrap standard errors of the population value, where the standard error is measured from the
  replicates and committed to `tests/fixtures/calibration/loadtest_percentiles.json` rather than
  assumed. A fixed percentage would be a number chosen for how it reads; a percentile estimator's
  error depends on the sample size and on the density at the quantile, so the band is measured.
  Falsification: any of the three percentiles outside its measured band.
- Backpressure detection: inject a consumer slower than the producer and assert every stage's
  backpressure metric moves and that `shed_total > 0` is always accompanied by a recorded
  backpressure event (INV-LT-03).
- Knee detection: hand-built sample series with a knee at a known device count; the finder returns
  that count for both criteria.
- A4-GATE-01: with a fixture `repeatability.json` declaring a standard deviation of one unit, a
  fixture report four standard deviations from the baseline fails and one two standard deviations
  from it passes. A third fixture omits `repeatability.json` and asserts the gate reports rather
  than fails, which is the reporting mode of 5.13.
- Reproducibility: two runs of the harness in simulation mode with the same seed produce identical
  sample series.

### 7.9 Contract and schema tests

- C3 producer/consumer tests: for every event type, a producer fixture emits and a consumer fixture
  reads, both pinned to the schema version they declare.
- SCHEMA-GATE-01, additivity: the schema at HEAD is diffed against the schema at the previous
  release tag. A removed field, a retyped field, a removed enum value, or a newly required field
  fails, unless the major version increments in the same commit. Before the first release tag the
  baseline is empty and the gate prints `no previous release tag; baseline is empty`.
- Envelope conformance (D-07): every event schema in `schemas/events/` declares `producer_id` and
  `seq`, and a test asserts a reader sorting by `(sim_ts, producer_id, seq)` recovers the emission
  order on a generated multi-producer log.
- Wall-clock carve-out (D-02): `test_runtime_events_carry_no_wall_derived_field` walks
  `schemas/events/` and fails on any field whose name or description marks it as wall-derived. A
  fixture schema carrying `duration_s` asserts the check fires.
- REST and MCP snapshot tests: the OpenAPI document and the MCP tool manifest are snapshotted;
  a diff fails unless the semver rules in 5.10 are satisfied by the version change in the same
  commit.

### 7.10 Brick isolation tests

For every published brick, a job creates a fresh virtual environment, installs only that brick from
the built wheel, runs its README example (DOC-GATE-03), and imports its public root. Any import of
a package not in its declared dependencies fails at install or import time. This is A1 proven per
release rather than asserted in a README.

### 7.11 Hook tests

Shell and Python tests under `tests/hooks/`:

- `test_commit_msg.sh`: accepted and rejected subjects, the ALL-CAPS body heading requirement, the
  approved vocabulary including `GOLDEN` and `VALIDATION`, scope validation against the package
  set, and the `# Conflicts:` rejection.
- `test_humanizer_gate.py`: one case per pattern, the `humanizer-allow` token, the excluded paths,
  and the added-lines-only behaviour.
- `test_post_commit_guard.sh`: builds a throwaway repository with a fake remote, asserts the
  changelog amend runs on an unpushed commit and refuses on a commit contained in a remote branch.
- `test_ip_hygiene.py`: a fixture denylist containing placeholder tokens blocks a staged file
  containing one, and the generic-marker path fires without a denylist.
- `test_prepare_commit_msg.sh`: attribution trailers are stripped and trailing blank lines
  collapse.

### 7.12 VAL-GATEs owned by this section

All three are META. A META gate asserts a property of this machinery rather than a fact about the
world, so none of them names an external reference for a statistic, none is counted in the
reference-validated badge total, and none is ever cited as validation of a twinflow number. What
each one does carry is the published idea it applies and the observation that would falsify it,
because D-12 makes an undescribable failure condition a defect rather than a style choice.

| Gate          | Class | Asserts                                                                                                | Idea applied                                                                      | Falsifies on                                                      |
| ------------- | ----- | ------------------------------------------------------------------------------------------------------ | --------------------------------------------------------------------------------- | ----------------------------------------------------------------- |
| VAL-META-001  | META  | every declared mutation of a statistical implementation fails at least one REFERENCE gate              | mutation adequacy, DeMillo, Lipton, and Sayward 1978, DOI 10.1109/C-M.1978.218136 | one surviving mutant in the declared set                          |
| VAL-META-002  | META  | every REFERENCE gate flips to FAIL when its expected value moves by twice that quantity's tolerance    | the same mutation-adequacy argument, applied to tolerances                        | a REFERENCE gate that still passes at twice its own tolerance     |
| VAL-REPRO-001 | META  | the published scaling curve regenerates from the committed seed, container digests, and profile        | reproducibility of a measurement, not a claim about performance                   | a regenerated knee outside the measured band of 5.13              |

VAL-REPRO-001 is a META gate rather than a GROUND_TRUTH one, because a gate whose reference is
this repository's own committed baseline fails D-11 condition 1. What it proves is that the harness
repeats; it says nothing about how fast anything is. Its band is the
measured one from `benchmarks/repeatability.json` rather than a chosen percentage, and until that
file holds a measurement the gate reports rather than blocks, exactly as A4-GATE-01 does.

### 7.13 CI gate index

Every gate this section owns, in one place, so a reader can find what blocks what:

| Gate                                  | Blocks                                | Job                            |
| ------------------------------------- | ------------------------------------- | ------------------------------ |
| DET-GATE-01 / 02                      | merge, release                        | `determinism`                  |
| DET-GATE-03                           | nightly, on business-event mismatch   | `nightly.yml`                  |
| MIG-GATE-01 / 02                      | release                               | `release.yml`, `e2e-golden`    |
| DOC-GATE-01 / 03 / 04 / 05            | merge                                 | `static`, `docs`               |
| README-GATE-01                        | merge                                 | `docs`                         |
| DOC-GATE-02                           | nightly report only                   | `nightly.yml`                  |
| LIC-GATE-01 / 02                      | merge, release                        | `security.yml`                 |
| LIC-GATE-03a / 03b / 03c              | merge, release                        | `security.yml`, `release.yml`  |
| SBOM-GATE-01                          | release                               | `release.yml`                  |
| A4-GATE-01                            | weekly load run, release              | `loadtest.yml`, `release.yml`  |
| BUDGET-GATE-01 / 02                   | merge                                 | `ci-budget`                    |
| PHASE-GATE-01                         | phase closure, release                | `phase-closure`, `release.yml` |
| PROV-GATE-01                          | merge                                 | `static`                       |
| IP-GATE-01                            | merge                                 | `static`                       |
| SCHEMA-GATE-01                        | merge                                 | `contracts`                    |
| GOLDEN-GATE-01                        | merge                                 | `e2e-golden`                   |
| SEC-GATE-01 / 02 / 03                 | merge                                 | `static`, `security.yml`       |
| CHANGELOG-GATE-01                     | merge                                 | `static`                       |
| TASK-GATE-01                          | merge                                 | `static`                       |
| PROFILE-GATE-01                       | merge                                 | `static`                       |
| QUICKSTART-GATE-01                    | merge                                 | `quickstart`                   |
| every VAL-REFERENCE and GROUND_TRUTH  | phase closure, release                | `val-gates`                    |
| every VAL-META                        | merge, phase closure, release         | `val-gates`                    |

Two gates in that list block nothing today and say so rather than pretending otherwise.
A4-GATE-01 and VAL-REPRO-001 report until `benchmarks/repeatability.json` holds a measured band
(5.13), and DET-GATE-03 blocks on a business-event mismatch from the first run while its
continuous-field tolerance waits on a measured divergence (5.7). Each is listed here in its
reporting state, with the open question that closes it named in section 9, because a gate index
that shows an unearned pass is worse than no index.

## 8. Phase placement

### Phase 0, contracts that cannot be retrofitted

Lands here: the uv workspace and package skeletons (C10), the justfile (C10), the git hooks and
`pre-commit` config, `twinflow-repolint` with `max_escapes = 0`, `twinflow-valgate` with an empty
registry, `phases.yaml` and `roadmap.yaml` with the Issues sync, `licenses.allow.toml`, <!-- docs-lint-ok STE-TERM-WORD literal filename -->
`SECURITY.md` with the sandbox boundary written as a design contract, `CONTRIBUTING.md`,
`CODE_OF_CONDUCT.md`, `GOVERNANCE.md`, the semver policy document, the CHANGELOG scaffold, the
Apache-2.0 `LICENSE`, `NOTICE`, `LICENSING.md`, `CLA.md`, `ci.yml` with `static`, `unit`,
`ci-budget`, `quickstart`, and `all-green`, and branch protection. The licence policy lands
complete, including the `deny_riders` list, the deprecated-identifier map, and LIC-GATE-03a to
03c, because the process-mining decision of D-14 is what the policy is for and a policy that
arrives after the dependency it exists to refuse has already lost.

Why here: a repository whose first two hundred commits predate the commit-msg hook has a history
that can only be fixed by rewriting it, and the history is one of the artifacts a reader judges.
The licence allowlist must exist before the first dependency is added, or the first denied licence
is already in the lockfile and removing it is a refactor. The VAL-GATE registry must exist before
Phase 2 writes its first gate, or every Phase 2 gate lands as an ordinary test and the registry
becomes a retrofit that no longer proves the phase-closure rule was ever enforced. The
nondeterminism lint must exist before the first subsystem is written, because retrofitting the
CLOCK, RNG, NETWORK, and STORAGE seam into working code is the single most expensive rewrite this
project could take on. `all-green` and `ci-budget` land with the first workflow so branch
protection has a required check from the first pull request rather than from the first one that
needed it.

### Phase 1, walking skeleton

Test tiers 0 to 3 wired with the first invariants that have something to constrain (INV-CLOCK-01,
INV-CLOCK-02, INV-MASS-01 on the one-station line, INV-SCHEMA-01, INV-DET-01). The golden harness
with its first golden, the capability report stub for the `micro` profile. DET-GATE-01 and
DET-GATE-02, both of which need only one platform and are so provable on the first walking
skeleton. DET-GATE-03 lands with `nightly.yml` in the same phase, in reporting mode, because its
tolerance comes from a measured divergence that cannot exist before the first cross-platform run
(5.7). The docs site skeleton and its strict build. The README with the CI badge, stating both
determinism tiers rather than the stronger one alone, per D-05. Tag `v0.1.0`.

Why here: the tier machinery must be present before the suite grows, because retrofitting markers
onto several hundred existing tests is tedious and gets skipped. The first golden is written when
there is one artifact to freeze, so the normaliser design is validated on a small case. The
cross-platform gate starts measuring in the same phase it starts running, so that by the time a
tolerance is set there is a record of divergence to set it from.

### Phase 2, LSS engine

The registry fills with VAL-NUM-_, VAL-SPC-_, VAL-CAP-_, VAL-MSA-_, VAL-HYP-*, and PROV-GATE-01
becomes load-bearing. `phase-closure` blocks for the first time: Phase 2 cannot close until the
statistics validate. VAL-META-001 lands with the first gates, not later, because a validation suite
that has never been tested against a broken implementation has never been tested. The capability
report golden becomes real. `docs/validation.md` publishes. Automated PyPI publishing turns on at
`v0.2.0`, because `twinflow-lss` is the first brick a stranger would plausibly want alone (A1).
SBOM per release starts here, since an SBOM for an unpublished artifact has no consumer.

### Just after Phase 2, E1 pulled forward

`docs.yml`, GitHub Pages, `replay.yml`, and the full badge set. Tag `v0.3.0`. The docs macros that
inject CI-produced numbers land here, since the replay page is the first public surface quoting a
measured number.

### Phase 3, sensor breadth

`twinflow-migrate` ships with the historian migration runner and the config upgrader, including an
identity config migration, so the first real migration is not also the first use of the tool. The
compatibility table starts, with `v0.2.0` as the earliest supported run format. `twinflow-loadtest`
ships and publishes its first curve on `ref-gh` and `ref-a`, because a device count only becomes a
meaningful axis once the catalogue has breadth. The repeatability run lands in the same phase and
before the first published curve, since A4-GATE-01's band is measured from it and a curve
published without a band is a number nobody can regress against. ADOPTION.md's first version lands
at Phase 3 close, when sensors, historian, LSS, and process mining exist, so the maturity model
routes to bricks that are real. Writing it earlier would promise modules that do not exist, which
is the credibility failure the whole repository is built to avoid.

The process-mining brick that ADOPTION.md routes to at stage S1 is `twinflow-procmine`, written
here under Apache-2.0 per D-14 and validated against the anchors of 5.5 plus the development-only
oracle of 5.12. It closes at v0.6.0 with P3c. INV-MS-01b is what stops ADOPTION.md from routing a
reader to it before it publishes: the stage renders with the suffix `(not yet adoptable)` and
names the milestone the brick waits on.

### Phase 3b onward

Each phase adds its gates to `phases.yaml`, its goldens where it produces a new artifact, and its
compatibility row when it changes a schema. The financial-statement golden family (GOLD-FIN) can
only exist after 6a17, so the tier-3 golden set grows through the 6a sequence while the tier itself
has existed since Phase 1. The partitioned-by-area scaling curve regenerates with E36; the
multi-site curve with E13.

### Phase 4 and Phase 5

The a11y job becomes enforcing rather than reporting when the dashboard reaches its final shape in
Phase 5. The README headline number is fixed from the Phase 5 load run. `1.0.0` publishes at Phase
5 close, when every contract surface exists, is documented, and has a snapshot test; before that
the CHANGELOG states plainly that minors carry breaking changes.

### Phase 6

Each E milestone is one minor release with its own CHANGELOG section, its own gates, and its own
compatibility row. E2 and A6 trigger the SECURITY.md revision that SEC-GATE-01 then enforces
against the live route and tool registries. E25 triggers LIC-GATE-02's dataset-card enforcement.
E43's red-team suite joins the nightly scorecard next to E27's accuracy evals.

### Ordering rationale in one line each

- Hooks and lint before code, because both are retrofits otherwise.
- Licence policy before the first dependency, because D-14's ruling is only cheap while the
  lockfile is empty.
- Registry before the first statistic, because the phase-closure rule must have been true from the
  first gate for it to mean anything.
- Test tiers before the suite grows, because markers are retrofitted badly.
- The cross-platform determinism gate in reporting mode from Phase 1, because its tolerance is
  measured from its own history and cannot precede it.
- Publishing at the first brick worth adopting alone, not before.
- SBOM at the first published artifact, not before.
- Load harness when device count becomes a real axis, with the repeatability run before the first
  published curve.
- ADOPTION.md when the bricks it routes to exist.
- Compatibility table at the first schema change, with the machinery one phase earlier.

## 9. Open questions

These are genuine ambiguities in the source, genuine conflicts between locked decisions, or
statistics whose external reference does not yet exist. None has an answer invented here, and per
D-11 condition 5 none of them is recorded anywhere else as a passing gate.

1. **The legal read on a development-only AGPL oracle.** The engineering question is closed. The
   Python Package Index reports PM4Py 2.7.23.3 with the licence field `AGPL 3.0`, the policy denies
   both members of that family at runtime, and D-14 rules that `twinflow-procmine` is written here
   under Apache-2.0 rather than wrapping a copyleft engine. What stays open is narrower and is not
   an engineering call: whether keeping PM4Py as a development-only conformance oracle, compared
   against in CI, never distributed in a wheel and never reachable from a served surface, is
   acceptable to the owner's own reading of the AGPL. LIC-GATE-03a, 03b, and 03c mechanise the
   boundary that reading would rely on, so the checks exist either way. If the answer is no, the
   oracle is dropped, VAL-PM-002 keeps the published algorithm of Leemans, Fahland, and van der
   Aalst as its only anchor, and the gate says so. The capability does not change under either
   answer.

2. **Which Gage R and R reference dataset is committed.** The validation source map needs both
   error terms tested against their published outputs: the AIAG Measurement Systems Analysis
   manual's worked example for `errorTerm="repeatability"`, and Minitab's documentation example
   plus the R `SixSigma` package for `errorTerm="interaction"`. The AIAG manual is sold rather than
   served, so it was not retrieved for this document and its content is attributed to AIAG rather
   than quoted. CRAN reports `SixSigma` 0.11.1, dated 2023-08-22, under "GPL-2 | GPL-3" (read from
   `https://cran.r-project.org/web/packages/SixSigma/index.html` on 2026-08-09, HTTP 200), which
   is why its bundled dataset cannot be copied into an Apache-2.0 repository even though its
   printed output can be cited. This section states the mechanism (encode the numeric study data
   only, cite by edition and page, mark `redistributable: false`). The owner confirms which dataset
   backs each gate and on what rights basis.

3. **The cross-platform divergence tolerance.** D-05 settles the shape of the claim: byte-identical
   on a pinned platform with a pinned dependency set, value-equivalent across platforms with a
   measured tolerance. This section implements both tiers, and the README states both rather than
   the stronger one alone. What is open is the number, and it is open by construction rather than
   by omission. D-05 requires the cross-platform tolerance to be derived from measured divergence,
   not chosen in advance, so it cannot exist until DET-GATE-03 has run across ubuntu, windows, and
   macos and written `benchmarks/cross-platform-divergence.json`. Until then the gate blocks on any
   business-event mismatch and reports the observed maximum divergence on continuous fields without
   asserting a bound. The open item is the commit that reads that file and sets the tolerance, and
   the decision it records is which of the two D-05 names the observed number is: the platform
   floating-point spread, or a defect.

4. **Lockstep versioning against single-brick adoption.** C9 requires lockstep versions across
   bricks. A1 promises a reader can adopt one brick. Under lockstep, `twinflow-lss` publishes a
   major bump because an unrelated brick broke its API, which is hostile to someone who pinned only
   the LSS engine. Candidate resolutions: keep lockstep as C9 states and add a per-brick "API
   stability" note in each brick's README and changelog listing which releases actually changed
   that brick's surface; or move to independent semver per brick with a published compatibility
   matrix; or lockstep the minor and let majors move independently. The section builds lockstep
   because the source says so, and records the cost.

5. **Which release is 1.0.0.** This section proposes Phase 5 close, on the reasoning that 1.0.0
   must mean the contract surfaces are stable and Phase 6 is additive. The source does not say.
   The choice sets the semver clock for every downstream contract, so it is an explicit decision
   rather than a default.

6. **Windows in the pull-request matrix.** The author develops on Windows, so a Windows-only
   regression is likely, and catching it in the nightly run means catching it late. This section
   puts one Windows unit cell in the pull-request matrix and the rest in nightly. The owner
   confirms whether the five-minute quickstart is also proven on Windows every pull request, which
   would add about six minutes to the wall-time budget.

7. **The post-commit changelog amend on a public repository.** The inherited hook amends HEAD to
   fold the CHANGELOG bullet into the commit. This section adds a guard that refuses to amend a
   commit already contained in a remote branch. That guard is enough for the normal flow. The
   open item is whether the owner wants amend-based sync at all on a public repository, against a
   separate `docs(changelog)` commit that never rewrites history. Amending keeps the history clean,
   which the source values, and it is the reason the private repo does it.

8. **GitHub Discussions.** An adoption-focused public repo usually wants a place for "how do I
   model my building" questions that are not bugs or milestones. Enabling Discussions changes the
   issue templates and the CONTRIBUTING routing. The source does not mention it.

9. **Naming the author's hardware.** A4 requires stated hardware. The author's own machine
   specification is not client data and can be named exactly, which strengthens reproducibility.
   Confirm whether to name the exact CPU model or describe it by class.

10. **Licence for twinflow's emitted synthetic datasets (E25).** Code is Apache-2.0. Data conventionally
    ships as CC-BY-4.0 or CC0. The dataset card schema requires a licence from the allowlist, and
    the allowlist file carries an `emitted_dataset_license` key that must be set. The choice affects
    whether a third party can redistribute a twinflow-generated benchmark corpus, which is the
    whole point of E25 as a data product.

11. **Phases with no statistical content.** "No phase closes until its statistics validate" is
    clear for Phase 2 and the analytics phases. Phase 0, Phase 4, and Phase 5 have little or no
    statistical content. This section makes such a phase declare `val_gates: []` with a non-empty
    `no_gates_justification`, so the absence is recorded rather than silent. The owner confirms
    that reading, or names the non-statistical gates those phases carry instead.

12. **Code coverage.** The source never mentions coverage, and a coverage badge is something a
    reader expects. A global coverage threshold tends to produce tests written for the number. This
    section proposes diff coverage of at least 85% on changed lines, reported but not badged, and
    no global threshold. Confirm, because adding it later means a large backfill.

13. **Reference for the standard-cost variance formulas (6a17).** The variance decomposition
    closure invariant (INV-LEDGER-04) is self-referential and testable, but the individual variance
    formulas (buying price, labour efficiency, overhead absorption, material usage) need a named
    published reference the way the SPC statistics do. A public-domain or freely citable
    cost-accounting source needs identifying before the 6a17 gates are written. Without one those
    gates fall to GROUND_TRUTH class with no external anchor, which INV-VG-02 records as
    `PENDING_REFERENCE` rather than as a pass, so the gap blocks the phase instead of hiding.

14. **The external anchor for causal-structure recovery (VAL-CAUSAL-001).** The gate measures
    structural Hamming distance between the recovered graph and the twin's known causal structure.
    The data is ground truth the twin generates, which is legitimate, but the threshold that
    separates a pass from a fail has no external basis in this document. D-11 condition 1 forbids
    this repository from being the reference for its own threshold, so the gate registers as
    `PENDING_REFERENCE`, counts in the registry total, and blocks its phase until a published
    distance definition and a published threshold, or an external oracle implementation to compare
    against, is named by the section that owns the causal layer. Its result is published either
    way, which is what keeps the gap visible rather than convenient.

15. **The A4 regression band and the scaling-curve repeatability measurement.** 5.13 sets the band
    at three standard deviations of the harness's own run-to-run spread, measured by ten repeated
    runs on one profile and committed to `benchmarks/repeatability.json`. That file does not exist
    until the Phase 3 load harness runs, so A4-GATE-01 and VAL-REPRO-001 report rather than block
    until it does, and the 7.13 index lists both in that state. The open item is the measurement,
    not the method: once the ten runs exist the band follows from them arithmetically, and no
    judgement is left. This entry exists so a reader never mistakes a reporting gate for a passing
    one, which is the failure D-12 names.
