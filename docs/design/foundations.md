---
title: "Foundations: kernel, determinism, contracts, monorepo, deployment tiers"
description: The kernel ports, determinism contract, event envelope, schema registry, config loader, release automation, and deployment tier seams every other section builds on.
topic_type: reference
audience: contributors
---

# Foundations: kernel, determinism, contracts, monorepo, deployment tiers

Status: design spec, implementation contract. Written for TDD. Every capability named here has a
named test or CI gate.

---

## 1. Scope

This section is the substrate every other section stands on. It owns the seams that cannot be
retrofitted.

Requirements covered in full:

| Req                    | Source text                                                                                                                                                                                                                                | Owned here                                                                                                                                                                                                                                                         |
| ---------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| C1                     | Determinism: single seed, splittable per-subsystem child seeds, byte-identical event logs, seed recorded per demo and eval, CI repeated-run hash check                                                                                     | Yes, complete                                                                                                                                                                                                                                                      |
| C2                     | Sim-time versus wall-clock: one sim-clock service, configurable compression, all timestamps sim-time, wall-clock mapping per run, dashboard speed control                                                                                  | Yes, complete (dashboard widget markup is the dashboard section's, the control protocol is here)                                                                                                                                                                   |
| C3                     | Schema registry: `/schemas` versioned machine-validated contracts for every cross-package event type, additive-only within a major, CI producer/consumer drift tests                                                                       | Yes, complete                                                                                                                                                                                                                                                      |
| C5                     | Config validation: every config (facility.yaml, sensor catalog, spec limits, metrics layer) validates at load against a published schema with line-numbered, suggestion-bearing errors, plus a validate command and dry-run mode           | Yes, complete for all four named configs. facility.yaml and the metrics layer envelope (5.15) are owned here. The sensor catalog schema is registered by twinflow-sensors and the spec-limit schema by twinflow-lss, both through the mechanism of 2.4             |
| C6                     | Migration story: versioned historian migrations, config upgrader command, CHANGELOG compatibility table                                                                                                                                    | Yes, complete (the historian's own per-table migration scripts are registered by the historian section into the framework defined here)                                                                                                                            |
| C9                     | Versioning and releases: semver policy over package APIs, REST/MCP contracts, event schemas, facility.yaml; lockstep versions; automated tag/changelog/build/publish of every brick from CI                                                | Yes, complete                                                                                                                                                                                                                                                      |
| C10                    | Monorepo tooling: uv workspace, justfile as single task entry point, CI matrix over Python versions plus the Rust agent, path-filtered jobs, stated CI wall-time budget                                                                    | Yes, complete                                                                                                                                                                                                                                                      |
| A1                     | Take-one-brick modularity: independently installable packages, clean boundaries, per-package README/tests/pip path, "use just this part" table                                                                                             | Yes, complete                                                                                                                                                                                                                                                      |
| A2                     | Bring-your-own-facility: entire operation defined in facility.yaml, three worked profiles, CONFIGURING.md                                                                                                                                  | Yes, complete for the config envelope, profile set, and gates. Sub-blocks of facility.yaml whose semantics belong to another subsystem (station physics, automation, sensor instances, policies) are declared here as namespaced blocks with owning sections named |
| A3                     | Deployment tiers by configuration never by rewrite: garage, growth, enterprise, with adapter interfaces making swap points explicit, stubs plus one implemented example                                                                    | Yes, complete. All nine seams of the 5.11 table have a Protocol in 3.6, a conformance suite class, and an entry in `twinflow.kernel.__all__`                                                                                                                       |
| A6                     | Integration surface: versioned REST/GraphQL API over twin state and findings, webhook events, composable into someone else's stack                                                                                                         | Yes, complete for REST, GraphQL, webhooks, auth, and versioning. The MCP server (E2) and EPCIS export (E35) reuse the same service layer and are specified in their own sections                                                                                   |
| DST kernel             | Locked architecture decision: one codebase, production mode and simulation mode, interfaces for CLOCK, RNG, NETWORK, STORAGE, deterministic scheduler, virtual clock, in-memory network with partition/latency/reorder/duplicate injection | Yes, complete. Every port named in the manifest has a Protocol body in 3.6, including `Storage`, `BlobStore`, `KeyValue`, and `MetricsSink`, and the scheduler ships the resource primitives of 5.2                                                                |
| Nondeterminism CI lint | Locked architecture decision: lint bans `time.time`/`datetime.now`/`random.*`/raw sockets outside the kernel package, with an annotation escape hatch, backstopped by C1's repeated-run hash check                                         | Yes, complete                                                                                                                                                                                                                                                      |

Requirements touched here but owned elsewhere, listed so the boundary is explicit:

- C4 test tiers. This section defines the tier names, the runtime budgets, and the property-based
  invariants belonging to foundations. The testing section owns the golden-file suite for the
  capability report, VSM, and financial statements.
- C7 SECURITY.md and C8 CONTRIBUTING.md. This section defines the release and versioning
  automation those documents reference. The repo-hygiene section owns their content.
- C11 dependency hygiene. This section owns the SBOM-per-release step inside the release pipeline
  and the CI job wiring. The dependency-hygiene section owns the allowlist and audit policy, and
  5.14 records the one allowlist row this section's dependency group needs and does not have.
- A4 published scaling evidence. The load-test harness runs against the ports defined here; the
  scaling section owns the harness and the curves.
- A5 ADOPTION.md. Consumes the brick table defined here.
- Reference-architecture fidelity item (b), Purdue-style network segmentation expressed for real in
  docker compose. Owned here as part of A3. Items (a), (c), (d), (e) are owned by the architecture
  and IoT sections.
- E1 hosted replay demo, E4 event-sourced replay and counterfactuals, E5 closed-loop autonomy
  tiers, E25 synthetic data products, E27 eval harness, E36 edge compute tiers. All six depend on
  the run manifest, canonical event log, and snapshot interface defined here. Their behavior is
  specified in their own sections.
- E26b governed semantic metric layer. This section owns the `metrics.yaml` envelope, the metric
  identifier registry, and its JSON Schema, because the config loader must resolve `spec_limits`
  keys against metric ids from Phase 0 (5.15). The AI-layer section owns the metric expressions and
  their evaluation.
- The stochastic model. `docs/design/variability-and-faults.md` is the single source of truth for
  distribution families, stream naming, and the fault catalog. This section owns the `Rng` port,
  the run seed, and the manifest fields that record RNG state, and it restates nothing that file
  already fixes.

### 1.1 Doctrine rulings applied here

`docs/design/DOCTRINE.md` is binding. Where it and an earlier draft of this section disagreed, the
ruling won. Every place a ruling lands is marked in the text with its id.

| Ruling | What it fixes here                                                                        | Where                     |
| ------ | ----------------------------------------------------------------------------------------- | ------------------------- |
| D-01   | `RunManifest` splits into a hashed core and an unhashed provenance sidecar                | 3.3, 4.1, 5.4             |
| D-02   | Wall-clock reads are legal in four named places and never reach a payload or a branch     | 3.1, 5.3, 5.9             |
| D-03   | No collection whose iteration order can reach an event, a hash, or a branch is a `set`    | 3.6, 5.9, 7.2             |
| D-04   | The learned-model seam is the `Inference` port, bound to a recorded adapter in simulation | 2.2, 3.6, 5.11, 6         |
| D-05   | The determinism claim is two-tier: byte-identical on a pinned platform, value-equivalent  | 5.4, 7.3, 9.2             |
| D-06   | The Rust device agent derives its streams from the same name-addressed derivation         | 3.2, 5.5, 7.3, 8          |
| D-07   | The envelope carries `twinflowproducerid`; density is per `(run_id, producer_id)`         | 3.4, 5.13, 7.2            |
| D-08   | `Network` stays MQTT-shaped and `EventBus` is a separate port for analytics fan-out       | 3.6, 5.1, 5.10, 5.11      |
| D-09   | One owning package per public symbol, and the layering contract names every package       | 2.2, 2.3, 2.4, 2.7, 2.9   |
| D-10   | The kernel core install stays minimal; heavy adapters are extras on other packages        | 2.2, 2.7, 3.6, 7.6        |
| D-11   | Every validation gate names an external reference, a tolerance, and a falsifier           | 5.4, 7.3, 7.5, 9.13, 9.14 |
| D-12   | `simulation.mode` selects the port family and `deployment.adapters` selects within it     | 5.1, 5.12, 5.14, 7.4      |
| D-13   | Timing tests run on a short scenario that fits the job budget, and the clamp is generated | 5.3, 7.2, 7.3, 7.4        |
| D-14   | Process mining is written here under Apache-2.0; PM4Py is a development-only oracle       | 2.1, 2.7, 5.4, 8          |

---

## 2. Packages

### 2.1 Repository layout

```
twinflow/
  justfile                     # single task entry point (C10)
  pyproject.toml               # uv workspace root, no runtime code
  uv.lock                      # single lockfile for the whole workspace
  .importlinter                # package boundary contracts (A1)
  ci_budget.yaml               # per-job wall-time budgets (C10)
  packages/
    twinflow-schemas/          # this section (the one workspace leaf)
    twinflow-rng/              # this section (stream registry, generator construction)
    twinflow-kernel/           # this section
    twinflow-config/           # this section
    twinflow-storage/          # this section (storage port adapters + migration framework)
    twinflow-devtools/         # this section (nondeterminism lint, codegen, compat checker)
    twinflow-cli/              # this section (the `tf` command, plugin-discovered subcommands)
    twinflow-api/              # this section (A6)
    twinflow-twin/             # process twin section
    twinflow-sensors/          # IoT / sensor catalog section
    twinflow-fleet/            # fleet management + PdM section
    twinflow-lss/              # LSS engine section
    twinflow-procmine/         # process mining + VSM section, Apache-2.0, written here (D-14)
    twinflow-forecast/         # planning + forecasting arena section
    twinflow-optimize/         # optimization + what-if search section
    twinflow-causal/           # causal inference section
    twinflow-cv/               # computer vision auditing section
    twinflow-agent/            # AI agent + accuracy stack section
    twinflow-dashboard/        # dashboard section
    ...                        # further bricks introduced by their own sections
  crates/
    twinflow-device-agent/     # the one Rust device agent (component 2)
    twinflow-rng/              # the Rust half of the RNG contract (D-06)
  schemas/                     # the schema registry (C3), language-neutral, published
  profiles/                    # facility profiles (A2)
  deploy/
    garage/                    # compose, tier 1
    growth/                    # compose, Purdue-segmented, tier 2
    helm/twinflow/             # Helm chart, tier 3
    topologies/                # named network topologies referenced by deployment.network
  migrations/
    historian/                 # numbered store migrations (C6)
    config/                    # config upgrader steps (C6)
  tools/                       # scripts that both `just` and CI call
  scripts/checks/              # the gates the git hooks and CI both call
  docs/
```

Distribution names are the directory names. Import paths use a PEP 420 implicit namespace package
`twinflow.*`, so `twinflow-kernel` installs `twinflow/kernel/`, `twinflow-lss` installs
`twinflow/lss/`, and `twinflow-rng` installs `twinflow/rng/`. No package ships a
`twinflow/__init__.py`. Where `docs/design/variability-and-faults.md` section A.4 names the stream
registry module, the module is `twinflow/rng/registry.py` inside the `twinflow-rng` distribution;
the packaging convention is this section's and the registry contents are that file's.

### 2.2 twinflow-kernel

Purpose: the DST seam. Defines the four ports the locked decision names (clock, RNG, network,
storage) plus the ones experience proved are equally leaky (identity generation, environment
access, event fan-out, metrics, secrets, identity, inference, hashing and serialization), supplies
both a deterministic simulation implementation and a production implementation of each, and
supplies the deterministic scheduler.

Runtime dependencies, core install: `pydantic>=2.9`, `numpy>=2.1,<3`, `twinflow-schemas`,
`twinflow-rng`. Nothing else, and in particular no columnar, database, or broker library. This
matters for A1: a quality manager installing only `twinflow-lss` gets pydantic and numpy, which
they already have. The upper bound on numpy is not decoration. NumPy's published compatibility
policy for `numpy.random` states that breaking stream compatibility "in order to introduce new <!-- docs-lint-ok * verbatim quotation of the NumPy compatibility policy, whose wording is not editable -->
features or improve performance in `Generator` or `default_rng` will be allowed with caution", on
feature releases rather than patch releases, so an unbounded pin would let a routine upgrade
silently reshuffle every recorded run (5.4, VAL-F6a, VAL-F6b).

Applying D-10, no port signature names a heavy type. `TableStore` is typed against the narrow
structural protocols `ArrowRecordBatchLike`, `ArrowTableLike`, and `ArrowSchemaLike` declared in
`twinflow.schemas.structural`, with `pyarrow` imported only under `TYPE_CHECKING` and every module
carrying `from __future__ import annotations`. `BRICK-4` installs the kernel alone into a clean
environment and imports it, so the claim is tested rather than asserted.

Optional extras:

| Extra      | Pulls in                                           | Enables                                                               |
| ---------- | -------------------------------------------------- | --------------------------------------------------------------------- |
| `sim`      | `simpy`                                            | `SimEventLoop`, `SimClock`, simulation-mode runtime                   |
| `mqtt`     | `aiomqtt`, `paho-mqtt`                             | `MqttNetwork` and `MqttEventBus` production adapters                  |
| `otel`     | `opentelemetry-sdk`, `opentelemetry-exporter-otlp` | production tracing bridge                                             |
| `arrow`    | `pyarrow`                                          | the concrete Arrow types behind the `TableStore` structural protocols |
| `identity` | `authlib`, `cryptography`                          | `OidcIdentity` and `MtlsIdentity` production adapters                 |

Applying D-09 and D-10, the kernel has no `delta` extra and no `postgres` extra. Every concrete
storage adapter and every extra that would pull a database driver belongs to `twinflow-storage`
(2.7). One public symbol has one owning package.

Adapters are discovered, not hard-coded. Every package that ships an adapter registers it under the
`twinflow.kernel.adapters` entry-point group as `(port, name) -> class`, which is the registry
`deployment.adapters.<port>` resolves a name against and the registry `TF-C120` lists when the name
is unknown. The kernel names no adapter it does not itself ship: `twinflow-storage`
registers the storage adapters, `twinflow-agent` registers `OllamaInference`, `VllmInference`, and
`HostedInference` for the `Inference` port, and the kernel registers the rest.

Public API surface (`twinflow.kernel.__all__`):

```python
# ports
Clock, Rng, Network, EventBus, Storage, EventLog, TableStore, KeyValue, BlobStore
IdGen, Env, MetricsSink, Secrets, Identity, Inference
# value types re-exported from twinflow-schemas so a consumer needs one import (D-09)
Quantity, ConfigHash
# value types owned here
SimInstant, Duration, TickResolution, StreamId, RunId, EventId
# runtime
Runtime, RuntimeBuilder, RunManifest, RunProvenance, RunMode
# scheduler
SimEventLoop, run_scenario, Snapshot, SnapshotHandle, Snapshottable
# scheduler resource primitives
Resource, PriorityResource, PreemptiveResource, Container, Store
# simulation implementations
SimClock, PacedClock, SplittableRng, InMemoryNetwork, InMemoryEventBus, InMemoryStorage
InMemoryEventLog, InMemoryTableStore, InMemoryBlobStore, InMemoryKeyValue
DeterministicIdGen, FrozenEnv, RecordingMetricsSink, FrozenSecrets, NullIdentity
RecordedInference
# production implementations
RealClock, MqttNetwork, MqttEventBus, OsEnv, Uuid7IdGen
DotEnvSecrets, DockerSecrets, K8sSecrets, ApiKeyIdentity, OidcIdentity, MtlsIdentity
# the distribution layer, built only on the NEP 19 stream-stable methods (5.4)
numeric
# fault injection
Fault, FaultKind, FaultSchedule, NetworkTopology, Link
# serialization and hashing
canonical_encode, canonical_decode, stable_hash, content_hash
# testing support
adapter_conformance_suite, FrozenWallClock, RecordingEventLog
```

Everything under `twinflow.kernel._impl` is private. `twinflow-kernel` imports `twinflow-schemas`
and `twinflow-rng`, and nothing else in the workspace.

`Storage` is an aggregate facade, not a peer of the four storage ports. It holds
`Storage(event_log, table_store, blob_store, key_value)` and exists so a subsystem constructor
takes one argument instead of four. `Runtime` passes `storage` for the facade and `log` for the
`EventLog` the kernel itself appends to, and the two name the same object:
`runtime.log is runtime.storage.event_log` is an assertion in `RuntimeBuilder`, covered by
`test_runtime_log_is_the_storage_event_log`.

`twinflow.kernel.numeric` is the distribution layer. It implements every family the `Rng` port
exposes on top of the three NumPy `Generator` methods whose stream NEP 19 commits to keeping
stable, and it is the only module permitted to call a `Generator` method at all (`TFD017`). 5.4
states why the other distribution methods are unusable here.

`Uuid7IdGen` implements UUID version 7 from RFC 9562 section 5.7 inside
`twinflow.kernel._impl.real` rather than calling a standard-library helper, because the supported
Python versions do not all ship one and a version-dependent identity format would put the
interpreter minor version into production event ids.

### 2.2a twinflow-rng

Purpose: the one place a bit generator is constructed, and the registry of stream names. The
mechanism, the derivation, the naming grammar, and the append-only registry rule are specified in
`docs/design/variability-and-faults.md` sections A.1 through A.6 and are not restated here.

Dependencies: `numpy>=2.1,<3`, `twinflow-schemas`. It is a leaf apart from the schema package.

Public API:

```python
streams.get(name, **template_args) -> Generator   # the only generator factory
STREAM_CATALOG_VERSION: str                        # semver over the registry
derive_spawn_key(stream_name: str) -> tuple[int, int, int, int]
draw_counts() -> Mapping[str, int]                 # per-stream draw counter, for crn_integrity
```

The returned object is the `numpy.random.Generator` that `variability-and-faults.md` section A.1
specifies, and no caller outside `twinflow.kernel.numeric` may call a method on it. That module
uses `Generator.random`, `Generator.integers`, and `Generator.bytes` and nothing else, for the
reason 5.4 gives. `TFD017` enforces the restriction statically, and `draw_counts()` counts calls
through `twinflow.kernel.numeric`, which is what makes `rng.draw_counts_sha256` a complete record
of a run's draw order rather than a partial one.

The matching Rust crate `crates/twinflow-rng` implements `derive_spawn_key` and the PCG64DXSM stream
from the same specification, which is what D-06 requires so the Rust device agent's jitter, drift,
and fault draws come from the run seed like everything else. `RUST-1` (7.3) is the cross-language
known-answer gate.

### 2.3 twinflow-schemas

Purpose: the machine-validated contract registry (C3) plus generated bindings.

Contents: a loader over the language-neutral `/schemas` tree, the generated Pydantic v2 models, the
compatibility checker, the upcaster registry, the envelope definition, and the shared value types
that every other package needs and that must not drag a dependency downward. Dependencies:
`pydantic>=2.9`, `jsonschema>=4.23`, `referencing`, `pint>=0.24`. It is the only workspace leaf: it
imports no other twinflow package.

`ConfigHash`, `Quantity`, and the `Env` protocol live here rather than in the kernel, which is
D-09's rule that a shared value type sits in the leaf and is re-exported upward. The reason is
concrete: `twinflow-config` needs all three, and putting them in the kernel would make
`pip install twinflow-config` pull numpy for a package that does no arithmetic.

Public API:

```python
Envelope, Event, Subject, SchemaVersion
ConfigHash, Quantity, Env                # shared value types, re-exported by twinflow.kernel
structural.ArrowRecordBatchLike          # narrow protocols so ports need no columnar library
structural.ArrowTableLike
structural.ArrowSchemaLike
registry()                       # -> SchemaRegistry, loaded from the packaged /schemas snapshot
SchemaRegistry.get(subject, version) -> JsonSchema
SchemaRegistry.validate(event) -> None | raises SchemaViolation
SchemaRegistry.snapshot_hash() -> str
compat_check(old_schema, new_schema, mode) -> CompatReport
upcast(event) -> Event          # lifts any supported historical version to current
models.*                         # generated Pydantic classes, one per subject/major
```

The `/schemas` tree is packaged into the wheel as data files so a lone `pip install
twinflow-schemas` gives a consumer the full contract set without cloning the repo.

### 2.4 twinflow-config

Purpose: C5 and the config half of C6 and A2. Loads, validates, merges, hashes, upgrades, and
explains configuration.

Dependencies: `twinflow-schemas`, `ruamel.yaml>=0.18` (round-trip parse keeps line and column, and
preserves comments through the upgrader), `rapidfuzz` (suggestions). No kernel, and no numpy.
`ConfigHash`, `Quantity`, and `Env` come from `twinflow-schemas` (2.3), which is what makes that
dependency list honest rather than aspirational; `BRICK-4` proves it in a clean environment.

Public API:

```python
load(path, *, overlays=(), sets=(), strict=True) -> ResolvedConfig
validate(path, ...) -> ValidationReport            # never raises, returns all errors
ResolvedConfig.hash() -> ConfigHash
ResolvedConfig.section(name) -> Mapping            # namespaced block accessor
FacilityConfig, SimulationConfig, DeploymentConfig, IntegrationConfig  # pydantic models
MetricRegistry, MetricDefinition                   # the metrics.yaml envelope of 5.15 (C5)
ConfigError, ErrorCode, render_human(report), render_json(report)
upgrade(path, to_version) -> UpgradeResult
register_section(name, model, *, schema_path, owner)   # entry-point based extension
```

Other bricks register their own facility.yaml block through the
`twinflow.config.sections` entry-point group. `twinflow-config` knows nothing about
sortation conveyors; it knows that the `automation` block is owned by `twinflow-twin` and validates
it against the schema that package registers. A block whose owning package is not installed is
parsed, retained verbatim, and reported by `tf config validate` as `TF-C140 section 'automation'
has no installed owner (install twinflow-twin)`, which is a warning at garage tier and an error
when `strict_sections: true`.

### 2.5 twinflow-devtools

Purpose: the tools CI runs that are not library code. Never a runtime dependency of anything.

Console scripts:

| Script              | Purpose                                                                        |
| ------------------- | ------------------------------------------------------------------------------ |
| `tf-lint-det`       | the nondeterminism AST lint (section 5.9)                                      |
| `tf-schemas gen`    | generate Pydantic and Rust serde bindings from `/schemas`                      |
| `tf-schemas check`  | registry drift, additive-only compat, producer/consumer contract check         |
| `tf-api check`      | OpenAPI and GraphQL SDL diff gate                                              |
| `tf-api-diff`       | Python public API diff against the previous tag (`griffe`-backed)              |
| `tf-budget`         | assert a CI job stayed inside `ci_budget.yaml`                                 |
| `tf-brick-isolate`  | build each brick into a clean venv and run its isolated test subset            |
| `tf-count-services` | count containers and networks in a compose file, for TIER-5                    |
| `tf-measure-rows`   | measure stored bytes per row for a subject and write `x-twinflow-stored-bytes` |

### 2.6 twinflow-cli

Purpose: the `tf` command. A thin argument parser plus a plugin loader over the
`twinflow.cli.commands` entry-point group, so `pip install twinflow-lss` alone still gives you
`tf lss chart ...` and nothing else. Dependencies: `typer`, `rich`, `twinflow-config`.

Commands owned by this section: `tf run`, `tf replay`, `tf config validate|explain|upgrade|hash`,
`tf facility init|doctor`, `tf schemas list|show|check`, `tf historian migrate|status`,
`tf serve api`, `tf det check`.

`tf run` flags: `--profile`, `--scenario`, `--seed`, `--replication`, `--overlay`, `--set`,
`--faults`, `--speed`, `--horizon`, `--dry-run`, `--out`, `--force`. `--faults` names a fault
schedule file and is folded into the resolved config as `deployment.faults` before the config hash
is taken, so a faulted run and its clean baseline have different `config_hash` values and
so different `run_id` values (M1). Without `--force`, `tf run` refuses to write into an
existing `artifacts/runs/<run_id>/` and exits 4 with `TF-D002 run artifacts already exist`, so a
repeated run cannot silently destroy the artifacts it was meant to be compared against. `--out`
redirects a run to a named directory, which is how DET-1 and DET-4 get two artifact sets for two
runs that share a `run_id` by design (M6).

### 2.7 twinflow-storage

Purpose: implementations of the storage ports plus the migration framework (C6). Applying D-09,
every concrete storage adapter in the workspace is declared here and nowhere else. The kernel
declares the ports and the in-memory implementations; this package declares everything that talks
to a real system.

The adapter set this package owns: `DuckDbTableStore`, `DeltaTableStore` (delta-rs), `PostgresTableStore`,
`PostgresEventLog`, `PostgresKeyValue`, `LocalFileKeyValue`, `LocalNdjsonEventLog`,
`LocalBlobStore`, `S3BlobStore`, `KafkaEventBus` (the implemented enterprise example for the
`EventBus` port of D-08), and `KafkaEventLog`. Stub adapters with a documented conformance target: `SnowflakeTableStore`,
`DatabricksSqlTableStore`, `AzureIotHubIngress`, `AwsIotCoreIngress`.

Extras: `delta` pulls `deltalake`, `duckdb`, and `pyarrow`; `postgres` pulls `asyncpg`; `kafka`
pulls `aiokafka`; `s3` pulls `boto3`. The base install of `twinflow-storage` takes three workspace
packages and no driver, `twinflow-config`, `twinflow-kernel`, and `twinflow-schemas`, and its
public surface is the historian rather than any adapter above: `Historian`, `ConfigSnapshot`,
`TableFormat`, `SeriesName`, and the naming that places the historian in the Purdue map. Each
adapter lands with the phase whose port it serves, so the take-one-brick promise survives here
too.

License positions for the two storage libraries that carry the most weight, read from the Python
Package Index on 2026-08-09: `deltalake` 1.6.2 is Apache-2.0 and `duckdb` 1.5.5 is MIT. Both are
compatible with the Apache-2.0 plus commercial dual license, which is the check D-14 showed is not
automatic. `simpy` 4.1.2, the kernel's `sim` extra, is MIT from the same source.

Public API includes `migration_framework.register(domain, migrations_dir)` so the historian, the
QMS, and the ledger each register their own numbered migration sets without this package knowing
their tables.

### 2.8 twinflow-api

Purpose: A6. FastAPI application, Strawberry GraphQL schema, webhook delivery service, OpenAPI
artifact generation. Dependencies: `fastapi`, `strawberry-graphql`, `uvicorn`, `twinflow-kernel`,
`twinflow-schemas`, `twinflow-config`. Domain packages are optional dependencies discovered through
the `twinflow.api.routers` entry-point group, so `twinflow-api` with only the LSS brick installed
serves `/findings` and returns `404` with a `TF-A020 router not installed` problem document for
`/twin/state`.

### 2.9 Package boundary rules (A1)

1. No package imports another package's `_internal` or `_impl` subpackage. Enforced by
   `import-linter` contract `forbidden: *._impl from anything outside its own distribution`.
2. Sibling domain packages do not import each other at all. They communicate through kernel ports
   and versioned events. Enforced by an `independence` contract listing every domain package.
3. Layering contract, top to bottom: `apps (api, dashboard, cli)` -> `domain (twin, lss, sensors,
fleet, procmine, forecast, optimize, causal, cv, agent)` -> `storage` -> `config` -> `kernel` ->
   `rng` -> `schemas`. `devtools` sits outside the graph because nothing imports it at runtime. An
   import that skips upward fails CI. The layer list and the domain-package list are read from
   `[tool.twinflow.layers]` in the root `pyproject.toml`, the same table `BRICK-2` reads, so the
   contract and the gate cannot disagree (D-09).
4. Every public symbol has exactly one owning package. `IMPORT-2` walks the workspace import graph
   and fails on a cycle. `IMPORT-3` asserts that every name in each package's `__all__` is defined
   in that package or is listed in that package's declared re-export set, and that no name appears
   in two packages' declared ownership. Re-exports are declared, not inferred, which is how
   `twinflow.kernel` can re-export `ConfigHash` from `twinflow-schemas` without owning it.
5. Every package ships `README.md` with a copy-pasteable install line, `API.md` listing its public
   symbols, its own `tests/`, and at least one test marked `@pytest.mark.brick_isolated`.
6. The flagship README carries the "use just this part" table:

| You are                                        | Install                                 | You get                                                                        |
| ---------------------------------------------- | --------------------------------------- | ------------------------------------------------------------------------------ |
| A quality manager who wants SPC as code        | `pip install twinflow-lss`              | control charts, capability, Gage R&R, hypothesis tests, findings               |
| An AI team who wants the grounding checker     | `pip install twinflow-agent[grounding]` | execution-grounded answers, semantic metrics layer, grounding gate, abstention |
| An IoT team who wants a device fleet simulator | `pip install twinflow-sensors`          | catalog-driven sensor simulation, failure modes, Sparkplug B publishing        |
| A process analyst                              | `pip install twinflow-procmine`         | discovery, conformance, variant analysis, auto VSM, all Apache-2.0 (D-14)      |
| A planner                                      | `pip install twinflow-forecast`         | backtest arena, conformal intervals, inventory policy                          |
| Someone building their own deterministic sim   | `pip install twinflow-kernel[sim]`      | the DST kernel alone                                                           |

---

## 3. Domain model

All types are frozen Pydantic v2 models or dataclasses unless stated. Field types are exact.

### 3.1 Time

```python
TickResolution = Literal[1_000, 1_000_000, 1_000_000_000]   # ticks per simulated second
SimInstant  = NewType("SimInstant", int)   # non-negative integer ticks since sim epoch
Duration    = NewType("Duration", int)     # signed integer ticks
```

Invariants:

- T1. Sim time is an integer on every application-visible surface. No float represents a point in
  time or a duration in a port signature, an event payload, a config after resolution, or a
  comparison that orders events. Config authors write `"4.5 min"`; the loader converts to ticks
  with round-half-up away from zero and records the exact tick value.
- T1a. `SimEventLoop.time()` is the single float shim in the codebase. It exists because
  `asyncio.AbstractEventLoop` declares it, and its value never orders an event. `TFD015` bans
  `loop.time()` outside `twinflow.kernel._impl.sim`, and `SimEventLoop` overrides `call_later` so
  the deadline is computed as `env.now + round(delay * tick_hz)` in integer ticks rather than as
  `loop.time() + delay` in float seconds. `test_call_later_deadline_is_computed_in_ticks` asserts
  that a delay whose float representation is inexact still lands on the exact tick.
- T2. `SimInstant >= 0`. The sim epoch is tick 0 and maps to `wall_clock_anchor.utc`.
- T3. `Clock.now()` is non-decreasing within a run (INV-K1).
- T4. Default `tick_hz` is 1_000_000 (microsecond ticks). At 1 microsecond a 64-bit signed integer
  covers 292,000 years of sim time, so integer overflow is not a concern. The loader rejects a
  horizon beyond 100 sim years with `TF-C031`.
- T5. `horizon_ticks + warmup_ticks <= 2**53 - 1`, rejected as `TF-C032` otherwise. The bound comes
  from `SimEventLoop.time()`: above 2\*\*53 ticks, two distinct tick values can map to the same
  float64, and any asyncio-internal comparison over those floats stops being able to tell two
  scheduled instants apart. At `tick_hz: 1000` and `1000000` the 100-year cap of T4 binds first. At
  `tick_hz: 1000000000` this bound binds first and caps a run at about 104 sim days, which is
  stated in the `TF-C032` message together with the arithmetic. Open question 9 records that the
  nanosecond option carries this cap.
- T6. Wall clock and sim clock are different concepts with different names, and the vocabulary is
  never mixed. `SimInstant` and `Duration` are sim time. `WallClockAnchor.utc` and the provenance
  sidecar fields of 3.3 are wall time. Applying D-02, a wall clock is read in exactly four places:
  the provenance sidecar writer, the paced-clock pacer, the observability exporter, and
  operator-facing log lines. In none of the four does the value enter an event payload, enter the
  hashed tape, or steer control flow.

### 3.2 Randomness

```python
StreamId = NewType("StreamId", str)   # dotted path, e.g. "twin.station.unload.service_time"
```

`SplittableRng` invariants. The derivation itself is fixed by
`docs/design/variability-and-faults.md` section A.1 and is reproduced here only so a reader of this
section can see what the manifest records. Where the two differ, that file wins.

- R1. One `base_seed: int` in `[0, 2**64)` per run, taken from `simulation.seed` or `--seed`, and
  one `replication_index: int >= 0`, taken from `--replication` and defaulting to 0. The pair is
  the root entropy, so replications of one scenario get independent trees while stream names stay
  stable across them.
- R2. A child stream is addressed by name, not by creation order. The derivation is
  `key_bytes = blake2b(stream_name.encode("utf-8"), digest_size=16, person=b"twinflow-rng")`, then
  `spawn_key` is those 16 bytes read as four little-endian `uint32` words, then
  `SeedSequence(entropy=<four uint32 words>, spawn_key=spawn_key)`, then
  `Generator(PCG64DXSM(seed_seq))`. The entropy is a fixed-width four-word `uint32` array,
  never a tuple of Python integers: numpy emits as many words as each integer's magnitude
  needs, so a tuple yields two to four words depending on the seed and the mixing path
  changes with it. `docs/design/variability-and-faults.md` section A.1 owns the byte-for-byte
  form and this line never restates it, because a cross-language contract with two spellings
  has no contract.
  Adding, removing, or reordering subsystems does not perturb any
  other subsystem's draws (INV-K4). This is the single most important property of the RNG design:
  without it, adding a sensor type in Phase 3 would invalidate every golden file recorded in
  Phase 2.
- R3. Stream names are registered. `Rng.child(name)` raises `UnregisteredStream` unless the name
  matches a registered fixed name or template declared by the owning package through the
  `twinflow.rng.streams` entry point. A registry means the collision check is a startup assertion,
  not a bug hunt.
- R4. The name-to-key hash is BLAKE2b with a 16-byte digest and the personalisation string
  `twinflow-rng`. It is not Python's `hash()`, which is randomized per process, and it is not a
  truncation of a differently personalised digest. `stable_hash` (the general-purpose helper in
  5.4) is a different function with a different digest length and is never substituted for it.
- R5. Bit generator is `numpy.random.PCG64DXSM`, with `numpy>=2.1,<3` pinned in every package that
  draws, and known-answer vectors committed (VAL-F6a, VAL-F6b). NEP 19, NumPy's Random Number
  Generator Policy, names the methods whose stream NumPy commits to keeping stable: "They MUST
  guarantee stream-compatibility for a specified set of methods ... Namely, `.bytes()`,
  `integers()` ... `random()`". Every other `Generator` method, including `normal`, `gamma`, and
  `poisson`, sits outside that commitment, and the same document allows breaking their streams on a
  feature release. `twinflow.kernel.numeric` builds every family the `Rng` port
  exposes on those three methods alone. 5.4 states the consequence and VAL-F6a and VAL-F6b state
  the gates. The generator is `PCG64DXSM` rather than numpy's default `PCG64` by the decision
  recorded on 2026-08-09 in `docs/design/variability-and-faults.md` open question G.11. numpy
  seeds the two through one routine, so their seeded state and increment are identical and only
  generation differs, which is why this rule changes in name and in nothing else.
- R6. Applying D-06, the Rust device agent derives its streams from the same specification. The
  `crates/twinflow-rng` crate implements the BLAKE2b-16 personalised digest, the little-endian
  spawn-key packing, `SeedSequence` entropy mixing, and PCG64DXSM. `RUST-1` asserts that Python and
  Rust produce byte-identical first-1000 draws for each of the twelve named streams of VAL-F6a.
  Without this the agent's dropped connections, clock drift, duplicate reads, crash loops,
  degraded read rates, sensor drift, and stuck-at faults would be outside the single-seed
  guarantee C1 makes, which is the boundary this project is loudest about.
- R7. Draw counts are recorded. `twinflow-rng` keeps a per-stream draw counter and the manifest
  carries `rng.draw_counts_sha256` over the sorted stream-name-to-count map. A code change that
  alters draw order changes that hash even when the log hash happens to survive, which is the
  cheapest available detector for hazard 2 of `variability-and-faults.md` section A.3.
- R8. Draw block size is fixed at one. Every draw through `twinflow.kernel.numeric` requests a
  single value, never an array. NumPy's compatibility policy for `numpy.random` is explicit that
  block size is part of the stream contract: "Calling `rng.random()` 5 times is not guaranteed to
  give the same numbers as `rng.random(5)`". A vectorised path added later for speed would
  change the tape, so any such path gets its own stream name under the versioning rule of
  `variability-and-faults.md` section A.3 rather than reusing the scalar stream.
  `test_numeric_layer_draws_one_value_at_a_time` walks the module's calls and fails on a `size`
  argument.

### 3.3 Run identity

Applying D-01, run identity is two objects, not one. `RunManifest` is the hashed core and rides
inside `run_started`. `RunProvenance` is the sidecar, is written to `manifest.json` beside
`events.ndjson`, and never enters an event or a hash. The split exists because the earlier single
object carried `started_wall_utc` and a platform fingerprint into the first event of the log, which
made DET-1 unachievable by construction: two runs seconds apart could never match, and the
cross-platform gate could never pass.

```python
class RunManifest(BaseModel):          # hashed core, carried by run_started
    run_id: RunId                      # "run_" + 26-char Crockford base32 of content hash
    seed: int                          # base_seed (R1)
    replication_index: int             # R1
    mode: RunMode                      # "simulation" | "production"
    config_hash: ConfigHash            # blake2b-256 over canonical resolved config
    schema_snapshot_hash: str          # blake2b-256 over the registry manifest
    faults_hash: str                   # blake2b-256 over the canonical fault schedule, or of b""
    profile: str                       # e.g. "profiles/midmarket_3pl.yaml"
    scenario: str | None
    tick_hz: int
    horizon_ticks: int
    warmup_ticks: int
    wall_clock_anchor: WallClockAnchor  # declared sim epoch, from config, not observed
    rng: RngDescriptor                  # mechanism, bit generator, stream catalog version

class RunProvenance(BaseModel):        # sidecar, written to manifest.json, never hashed
    run_id: RunId
    speed: float | Literal["asap"]     # pacing only, never in the hash (M6)
    anchor_monotonic_ns: int | None    # production mode only, the pacer's own reading
    started_wall_utc: datetime
    finished_wall_utc: datetime | None
    event_log_hash: str | None         # blake2b-256 over the canonical log bytes
    event_count: int | None
    rng_draw_counts_sha256: str | None
    packages: dict[str, str]           # distribution -> version, sorted, every twinflow-*
    git: GitProvenance                 # sha, dirty flag, branch
    platform: PlatformFingerprint      # os, arch, python, numpy, simd features disabled
    host: str
    exit: Literal["completed", "horizon", "aborted", "error"] | None
```

Invariants:

- M1. `run_id` is derived, not random:
  `content_hash(seed, replication_index, config_hash, schema_snapshot_hash, faults_hash, scenario,
mode)`. Two identical runs produce the same `run_id`, which is what makes the CI repeated-run check
  a file comparison rather than an id-stripping exercise. `faults_hash` is in the inputs because
  without it a faulted run and its clean baseline collide on identity and on the artifact
  directory, and DET-5's second run would overwrite the first before it could be compared.
- M1a. `deployment.faults` is a resolved config key, so `config_hash` already covers the fault
  schedule. `faults_hash` is carried separately anyway, because the fault schedule is the one input
  a reader most often wants to compare between two runs and digging it out of a config hash is
  not comparison.
- M2. Every demo, eval case, dataset card (E25), and replay bundle (E1, E4) references a
  `RunManifest`. `tf run` refuses to start without a seed, either from config or flag, with
  `TF-D001 no seed supplied; determinism is a contract, not a default`.
- M3. `RunProvenance.platform.simd_disabled` records the value of `NPY_DISABLE_CPU_FEATURES` used,
  because numpy's runtime SIMD dispatch is a cross-machine determinism hazard for reductions. It
  sits in the sidecar, so recording it does not put the machine's identity into the tape.
- M4. `event_log_hash` covers the canonical bytes of every event from `run_started` up to but not
  including `run_finished`, and `run_started` carries the hashed core only. The carve-out is
  asserted by `test_run_started_carries_no_wall_clock_or_platform_field`, which walks the
  `run_started` payload schema and fails on any property whose name or type is a wall-clock
  instant, a host name, a package version, or a platform field. A field added later to
  `RunProvenance` cannot leak into the hash without that test failing.
- M5. `wall_clock_anchor` is declared, never observed. Its fields are `sim_ts`, `utc`, `tz`, and
  `dst_offset_minutes`, all of which come from `facility.timezone` and the scenario's declared
  start date. It carries no monotonic reading at all: the one the pacer takes lives in
  `RunProvenance.anchor_monotonic_ns` and is populated only in production mode. That is why INV-K19
  can freeze the process wall clock at two different instants and still get identical logs.
- M6. `speed` is not in the hashed core and not in `ConfigHash`. Pacing changes when an event is
  emitted in wall time and never which event is emitted or in what order (D-02, 5.3), so a speed
  that entered either hash would make DET-4 unachievable by construction: the gate runs the same
  scenario at `asap` and at a finite speed and compares logs, and a speed-bearing first event
  guarantees they differ. `simulation.speed` carries `x-twinflow-not-in-hash: true` in
  the facility schema, and that keyword marks the complete carve-out, currently one key.
  `test_config_hash_is_unchanged_by_speed` and `test_run_started_payload_has_no_speed_field` pin
  both halves, and INV-K11 excludes exactly the keys carrying the keyword rather than making a
  blanket exception. A consequence worth stating: two runs that differ only in speed share a
  `run_id`, so DET-1 and DET-4 pass `--out` to give each run its own directory, and `--force` is
  reserved for the case where an operator means to overwrite.

### 3.4 Events

```python
class Envelope(BaseModel):
    specversion: Literal["1.0"]        # CloudEvents 1.0
    id: EventId                        # unique within run, sortable
    source: str                        # URI-reference: "/twinflow/<package>/<component>"
    type: str                          # the subject, e.g. "twinflow.telemetry.sensor_reading"
    time: datetime                     # RFC 3339, derived from sim_ts via the anchor
    datacontenttype: Literal["application/json"]
    subject: str | None                # UNS topic where applicable
    dataschema: str                    # "twinflow:schemas/telemetry/sensor_reading/v1.3.json"
    # CloudEvents extension attributes (lowercase alphanumeric, at most 20 characters)
    twinflowsimts: str                 # decimal integer ticks, the authoritative timestamp
    twinflowrunid: str
    twinflowproducerid: str            # the emitting process, D-07
    twinflowseq: str                   # decimal, per (run, producer) emission sequence
    twinflowcausationid: str | None
    twinflowcorrid: str | None         # correlation id
    partitionkey: str | None           # CloudEvents Partitioning extension
    traceparent: str | None            # CloudEvents Distributed Tracing extension
    tracestate: str | None             # CloudEvents Distributed Tracing extension
    data: dict                         # payload, validated against dataschema
```

Decision and rationale: the envelope is CloudEvents 1.0 compliant. Alternative considered and
rejected: a bespoke envelope. CloudEvents costs nothing here, gives webhook consumers (A6) a format
their existing tooling already parses, and gives the test suite a published conformance target
(VAL-F12). The constraint it imposes comes from the specification's own naming rule, quoted from
the CloudEvents 1.0.2 specification, section "Attribute Naming Convention": "CloudEvents attribute
names MUST consist of lower-case letters ('a' to 'z') or digits ('0' to '9') from the ASCII
character set. Attribute names SHOULD be descriptive and terse and SHOULD NOT exceed 20 characters <!-- docs-lint-ok STE-01 verbatim quotation of CloudEvents 1.0.2 -->
in length." Hence `twinflowsimts` rather than `twinflow_sim_ts`, and hence `twinflowcorrid` at 14
characters rather than `twinflowcorrelationid` at 21, which would have failed the very conformance
gate the envelope was chosen to make possible. The longest name the envelope now carries is
`twinflowcausationid` at 19. `test_every_extension_attribute_name_is_at_most_20_chars` is a unit
test, not a review habit.

Three attributes are the specification's own rather than twinflow's, for one reason each time: a
twinflow-prefixed name would be invisible to every off-the-shelf CloudEvents tool, which is the
interoperability the envelope was adopted for. Tracing uses the Distributed Tracing extension,
whose attributes are `traceparent` (REQUIRED within the extension) and `tracestate` (OPTIONAL).
Partitioning uses the Partitioning extension's `partitionkey`, described there as "A partition key
for the event, typically for the purposes of defining a causal relationship/grouping between
multiple events", which is exactly what the historian partitions on. `time` is wall time under
CloudEvents, which is why `twinflowsimts` carries the authoritative value.

Two attributes are twinflow's where a standard extension exists, and the reason is a type
constraint rather than preference. CloudEvents 1.0.2 defines its `Integer` type as "A whole number
in the range -2,147,483,648 to +2,147,483,647 inclusive", and both of twinflow's counters leave
that range: at the default `tick_hz` of 1e6 a one-day horizon is already 8.64e10 ticks, and the
sensor-volume example of 5.6 produces 5.184e9 readings in one run. `twinflowsimts` and
`twinflowseq` are CloudEvents `String` attributes carrying a decimal integer, parsed back
to `int` by the reader. The Sequence extension is not used for the same reason plus two others: its
`sequence` values are string-encoded 32-bit integers that "wrap around" at 2^31-1, and its
`Integer` sequence type "MUST start with a value of `1`", while `twinflowseq` starts at 0 so that
`run_started` sits at sequence 0 with no off-by-one in the total order of E4.
`test_extension_attribute_types_match_cloudevents_type_system` asserts every attribute against the
type it declares, which is the assertion that would have caught the original integer typing.

Invariants:

- E1. `time` is always derivable: `anchor.utc + (twinflowsimts - anchor.sim_ts) / tick_hz`, and in
  simulation mode is derived, never observed.
- E2. `id` is `DeterministicIdGen` output in simulation mode:
  `content_hash(run_id, twinflowproducerid, twinflowseq)` truncated to 26 Crockford base32
  characters. In production mode it is UUIDv7. The producer id is inside the hash because sequence
  numbers are per producer (E3), so without it two producers would mint the same event id.
- E3. Applying D-07, `twinflowseq` increments by exactly 1 per emitted event within a
  `(twinflowrunid, twinflowproducerid)` pair. It is not globally dense, and no global counter is
  claimed, because every tier including garage runs several processes and the Rust device agent is
  a fourth. A gap within one producer's sequence means a dropped event and is a test failure
  (INV-K18). `twinflowproducerid` is a slug naming the process role, drawn from the closed set
  `sim`, `api`, `dashboard`, `agent`, `device-agent`, and `cli`, extended only by a line in
  `schemas/registry.yaml`.
- E3a. `twinflowproducerid` is added now rather than later because 5.5 makes an envelope change a
  MAJOR bump on every subject, and Phase 0 freezes the envelope. This is the reason D-07 was
  settled before any schema was written.
- E4. The canonical total order of the log is `(twinflowsimts, twinflowproducerid, twinflowseq)`,
  ascending, with `twinflowproducerid` compared as a byte string. All three components are needed:
  sim time orders across producers, the producer id breaks ties deterministically between
  processes that emit at the same tick, and the sequence orders within one producer. The
  pagination cursor of 5.13 and the replay reader of 5.7 both use this triple and no other order.

### 3.5 Configuration

```python
class ConfigDocument(BaseModel):
    path: Path
    schema_version: str                # "MAJOR.MINOR" of the facility schema, not the release
    raw: CommentedMap                  # ruamel round-trip node, carries line/col
    resolved: dict                     # after includes, overlays, --set, defaults
    provenance: dict[str, Origin]      # every leaf key -> (file, line, col, source_kind)

class ConfigError(BaseModel):
    code: ErrorCode                    # "TF-C012"
    severity: Literal["error", "warning"]
    message: str
    origin: Origin                     # file, line, col, and the source snippet
    suggestion: str | None
    valid_alternatives: list[str]
    docs_url: str
```

Invariants:

- G1. Every resolved leaf key has a provenance entry naming the file and line that set it, or the
  literal `default` origin naming the schema that supplied it. `tf config explain
layout.docks[2].width` prints the chain.
- G2. `validate()` returns all errors, never the first. An implementer fixing a profile must not
  have to run the loader eleven times.
- G3. Unknown keys are errors (`model_config = ConfigDict(extra="forbid")`), except inside a block
  whose owning package is not installed (see 2.4).
- G4. `ConfigHash` is computed over the resolved config serialized with RFC 8785 canonical JSON,
  minus the keys the facility schema marks `x-twinflow-not-in-hash: true`. Comments, key order, and
  whitespace do not affect it (INV-K11). The carve-out is one key today, `simulation.speed`, and
  M6 gives the argument for it; a second key may only be added with the same argument, that the
  key provably cannot change the tape, and `tf config explain` prints whether a key is in the hash.

### 3.6 Ports

```python
class Clock(Protocol):
    def now(self) -> SimInstant: ...
    async def sleep(self, d: Duration) -> None: ...
    async def sleep_until(self, t: SimInstant) -> None: ...
    def anchor(self) -> WallClockAnchor: ...
    def timeout(self, d: Duration) -> AbstractAsyncContextManager[None]: ...

class Rng(Protocol):
    def child(self, name: StreamId) -> Rng: ...
    def uniform(self, lo: float, hi: float) -> float: ...
    def normal(self, mu: float, sigma: float) -> float: ...
    def lognormal(self, mu: float, sigma: float) -> float: ...
    def exponential(self, scale: float) -> float: ...
    def gamma(self, shape: float, scale: float) -> float: ...
    def weibull(self, shape: float, scale: float) -> float: ...
    def triangular(self, lo: float, mode: float, hi: float) -> float: ...
    def bernoulli(self, p: float) -> bool: ...
    def poisson(self, lam: float) -> int: ...
    def choice(self, seq: Sequence[T], weights: Sequence[float] | None = None) -> T: ...
    def sample_without_replacement(self, seq: Sequence[T], k: int) -> list[T]: ...
    def permutation(self, seq: Sequence[T]) -> list[T]: ...
    def duration(self, dist: DistributionSpec) -> Duration: ...   # config-driven, returns ticks

class Network(Protocol):
    """MQTT-shaped transport. Sparkplug B rides on this port and only this port (D-08)."""
    async def publish(self, topic: str, payload: bytes, *, qos: int = 1,
                      retain: bool = False) -> None: ...
    def subscribe(self, pattern: str, *, qos: int = 1) -> AsyncIterator[Message]: ...
    async def connect(self, node: NodeId, *, will: Will | None = None) -> Connection: ...
    def topology(self) -> NetworkTopology: ...

class EventBus(Protocol):
    """Subject-addressed fan-out. No retain, no will, no wildcard pattern (D-08)."""
    async def publish(self, subject: str, event: Envelope, *, key: str | None) -> None: ...
    def subscribe(self, subjects: Sequence[str], *, group: str) -> AsyncIterator[Envelope]: ...
    async def commit(self, upto: Cursor) -> None: ...

class EventLog(Protocol):
    async def append(self, event: Envelope) -> None: ...
    def read(self, *, since: SimInstant | None, subjects: Sequence[str] | None,
             cursor: Cursor | None) -> AsyncIterator[Envelope]: ...
    async def hash(self) -> str: ...

class TableStore(Protocol):
    """Typed against structural protocols, never against pyarrow itself (D-10)."""
    async def write(self, table: str, batch: ArrowRecordBatchLike, *,
                    mode: Literal["append", "overwrite"]) -> None: ...
    async def query(self, sql: str, params: Mapping[str, Any], *,
                    order_by: Sequence[str]) -> ArrowTableLike: ...
    async def schema(self, table: str) -> ArrowSchemaLike: ...

class BlobStore(Protocol):
    async def put(self, key: str, data: bytes, *, content_type: str) -> BlobRef: ...
    async def get(self, key: str) -> bytes: ...
    def list(self, prefix: str) -> AsyncIterator[BlobRef]: ...   # ascending by key
    async def delete(self, key: str) -> None: ...
    def url(self, key: str, *, expires: Duration | None = None) -> str: ...

class KeyValue(Protocol):
    async def get(self, key: str) -> bytes | None: ...
    async def set(self, key: str, value: bytes, *, ttl: Duration | None = None) -> None: ...
    async def compare_and_set(self, key: str, expect: bytes | None,
                              value: bytes) -> bool: ...
    async def delete(self, key: str) -> None: ...
    def scan(self, prefix: str) -> AsyncIterator[tuple[str, bytes]]:  # ascending by key
        ...

class Storage(Protocol):
    """Aggregate facade over the four storage ports. Holds no state of its own."""
    event_log: EventLog
    table_store: TableStore
    blob_store: BlobStore
    key_value: KeyValue

class MetricsSink(Protocol):
    def counter(self, name: str, value: int, **labels: str) -> None: ...
    def gauge(self, name: str, value: float, **labels: str) -> None: ...
    def histogram(self, name: str, value: float, **labels: str) -> None: ...
    def flush(self) -> None: ...

class Secrets(Protocol):
    async def resolve(self, ref: SecretRef) -> str: ...       # "env:NAME" | "file:P" | "k8s:NAME"
    def redact(self, text: str) -> str: ...                   # for log lines and problem docs

class Identity(Protocol):
    async def authenticate(self, credential: Credential) -> Principal: ...
    def scopes(self, principal: Principal) -> Sequence[str]: ...   # sorted, D-03
    async def client_certificate(self, node: NodeId) -> ClientCert | None: ...

class Inference(Protocol):
    """The learned-model seam named by D-04. Simulation mode binds RecordedInference."""
    async def complete(self, request: InferenceRequest) -> InferenceResponse: ...
    def model_artifact_hash(self) -> str: ...
    def budget(self) -> InferenceBudget: ...   # deterministic token and step caps, never seconds

class IdGen(Protocol):
    def new(self, prefix: str) -> str: ...

class Env(Protocol):
    def get(self, key: str, default: str | None = None) -> str | None: ...
    def hostname(self) -> str: ...
    def cwd(self) -> Path: ...
```

Two rules bind every port signature and are checked by the conformance suite rather than by
review. First, applying D-03, no method returns an unordered collection whose iteration order could
reach an event, a hash, or a branch. `Identity.scopes`, `BlobStore.list`, and `KeyValue.scan` are
specified as ascending, and `TableStore.query` takes a mandatory `order_by` and returns rows in
exactly that order. Second, applying D-10, no signature names a type from a heavy dependency; the
three `Arrow*Like` protocols come from `twinflow-schemas` and describe only the members the kernel
touches.

`TableStore.query` deserves the explicit rule because the in-memory adapter runs DuckDB over Arrow
buffers, and a SQL engine is free to return hash-aggregate and hash-join results in any order.
`InMemoryTableStore` sets `threads=1` and `preserve_insertion_order=true` on its
connection, and rejects a query with an empty `order_by` as `TF-K012 query has no total order`.
INV-K21 is the property that a query's result is identical across thread counts.

`Runtime` is the injected bundle: `Runtime(clock, rng, net, bus, storage, ids, env, metrics,
secrets, identity, inference, log, manifest)`. There are no module-level singletons. Every
subsystem takes a `Runtime` in its constructor. This is what makes both modes possible and what the
lint enforces. `log` and `storage.event_log` are the same object (2.2).

### 3.7 Faults

```python
class FaultKind(StrEnum):
    PARTITION       # split the topology into named groups
    LATENCY         # add a delay drawn from a distribution to a link
    DROP            # drop with probability p
    DUPLICATE       # deliver twice with probability p
    REORDER         # buffer and release out of order within a window
    BANDWIDTH       # cap bytes per sim second on a link
    BROKER_DOWN     # the broker node refuses connections
    CLOCK_SKEW      # a node's reported wall clock drifts (sim clock never skews)
    CORRUPT         # flip payload bytes with probability p
    SLOW_CONSUMER   # a subscriber's queue drains at a capped rate

class Fault(BaseModel):
    kind: FaultKind
    start: SimInstant
    end: SimInstant | None            # None = for the rest of the run
    scope: FaultScope                 # links, nodes, or topic patterns
    params: dict[str, float | DistributionSpec]

class FaultSchedule(BaseModel):
    faults: list[Fault]
    rng_stream: StreamId = "kernel.net.faults"
```

Invariants:

- F1. All fault randomness draws from `kernel.net.faults`, a dedicated child stream. Enabling
  faults does not shift any process-level draw, so a faulted run and a clean run at the
  same seed remain comparable, which is exactly what the resilience tests need.
- F2. `end > start`. Overlapping faults on the same scope compose in declaration order, and the
  composition order is recorded in the manifest.
- F3. With an empty schedule, `InMemoryNetwork` delivers every message exactly once, per topic, in
  publish order (INV-K7).

---

## 4. Events

Every subject below lives in `/schemas`. Shapes show `data` only; the envelope of section 3.4
wraps all of them. All are additive-only within their major version.

### 4.1 Published by this section

**`twinflow.kernel.run_started` v1.0**

```json
{ "manifest": { "...the RunManifest hashed core of 3.3, complete, and nothing else..." } }
```

Always the first event in the log, at `twinflowsimts = 0`, `twinflowproducerid = "sim"`,
`twinflowseq = 0`. Applying D-01, the payload carries the hashed core only. It carries no
`started_wall_utc`, no git provenance, no platform fingerprint, no package versions, and no host
name; those are `RunProvenance` and live in `manifest.json`.
`test_run_started_carries_no_wall_clock_or_platform_field` (M4) is the standing assertion.

**`twinflow.kernel.run_finished` v1.0**

```json
{
    "event_count": 184213,
    "event_log_hash": "b2:...",
    "finished_sim_ts": 86400000000,
    "exit": "completed|horizon|aborted|error",
    "error": null
}
```

Two hazards, stated so an implementer chases neither. First, `event_log_hash` covers every event up
to but not including `run_finished`, so the field is not self-referential. Second, there is no
`finished_wall_utc` here. Wall time would put the machine's clock into the last event of the tape
and reopen exactly the hole D-01 closed at the first event; the value lives in `RunProvenance`
instead. `event_count` is the total across all producers and is recomputed by the reader from the
merged log, so it is a checksum rather than a counter any single producer maintains.

**`twinflow.kernel.fault_injected` v1.0**

```json
{
    "fault": {
        "kind": "PARTITION",
        "scope": { "groups": [["dev-*"], ["broker", "historian"]] },
        "params": {}
    },
    "phase": "start|end",
    "affected_links": 52
}
```

**`twinflow.kernel.clock_speed_changed` v1.0**

```json
{
    "from": 1.0,
    "to": "asap",
    "requested_by": "dashboard|api|agent|cli",
    "actor": "user:demo",
    "sim_ts": 3600000000
}
```

Consumed by the dashboard speed control and by the E5 audit trail.

**`twinflow.kernel.checkpoint_written` v1.0**

```json
{
    "checkpoint_id": "ckpt_01J...",
    "sim_ts": 43200000000,
    "size_bytes": 8412331,
    "state_hash": "b2:...",
    "resumable_from_schema_snapshot": "b2:...",
    "covered_subsystems": [
        "kernel.scheduler",
        "kernel.rng",
        "kernel.network",
        "kernel.storage"
    ],
    "resumable": false
}
```

`covered_subsystems` and `resumable` exist because the schema freezes at Phase 0 under
additive-only rules while subsystem snapshots land with E4. A Phase 0 checkpoint covers kernel
state only, so `state_hash` is honest about what it hashes and `resumable: false` says plainly that
resuming from it would drop subsystem state. `covered_subsystems` is a sorted list of the
`Snapshottable` implementations that participated, so a reader of an old checkpoint can tell what
was in it. The alternative, a `state_hash` over kernel state alone with no coverage record, would
have shipped a checkpoint that looks resumable and is not, and the frozen schema would have made
that unfixable without a MAJOR bump. `simulation.snapshot` stays a live config key from
Phase 0 and produces truthful checkpoints from Phase 0.

**`twinflow.config.config_applied` v1.0**

```json
{
    "config_hash": "b2:...",
    "schema_version": "1.3",
    "profile": "profiles/midmarket_3pl.yaml",
    "overlays": ["scenarios/peak_day.yaml"],
    "sets": ["simulation.speed=asap"],
    "changed_keys": ["resources.labor.pickers.count"],
    "applied_by": "cli|api|agent",
    "autonomy_tier": "L1|L2|L3"
}
```

This is the event E5's closed-loop autonomy audit trail is built from, and the reason it lives here
rather than in the autonomy section: an accepted what-if flowing back into the running config is a
config event, and the config event schema must exist from Phase 0 or the audit trail has a hole in
its history.

**`twinflow.config.validation_failed` v1.0**

```json
{
    "path": "profiles/x.yaml",
    "errors": [
        {
            "code": "TF-C012",
            "message": "...",
            "origin": { "file": "...", "line": 214, "col": 7 },
            "suggestion": "conveyor_speed"
        }
    ]
}
```

**`twinflow.migration.applied` v1.0**

```json
{
    "domain": "historian",
    "from_version": 6,
    "to_version": 7,
    "migration": "0007_add_energy_kwh",
    "rows_touched": 1240113,
    "duration_ms": 8412,
    "check": "passed"
}
```

**`twinflow.integration.webhook_delivery_attempted` v1.0**

```json
{
    "subscription_id": "whs_01J...",
    "event_id": "evt_01J...",
    "attempt_number": 2,
    "outcome": "delivered|failed|dropped",
    "status_code": 503,
    "latency_ticks": 412000,
    "next_retry_sim_ts": 3600412000
}
```

**`twinflow.integration.api_request` v1.0**

```json
{
    "method": "POST",
    "route": "/api/v1/whatif",
    "status": 202,
    "principal": "apikey:demo",
    "scopes": ["whatif:run"],
    "idempotency_key": "ik_...",
    "latency_ticks": 91000,
    "request_hash": "b2:...",
    "response_hash": "b2:..."
}
```

Feeds the 6a11 audit-trail integrity requirement and the 6a15 SIEM analog. Recording it here means
those sections consume an existing stream instead of retrofitting instrumentation.

### 4.2 Consumed by this section

`twinflow-api` and the event log consume every subject, but only through the envelope. They never
depend on a payload field. Two exceptions are declared in `consumes.yaml` and so covered by
the CI consumer-drift test:

- `/findings` reads `twinflow.lss.finding` fields `finding_id, severity, rule, evidence_window,
station_id, opened_sim_ts, status`.
- `/twin/state` reads `twinflow.twin.state_snapshot` fields `stations[].id, stations[].wip,
stations[].utilization, bottleneck_station_id`.

Any change to those fields fails `SCHEMA-3` until `twinflow-api`'s `consumes.yaml` is updated in
the same commit.

Sequencing, because `SCHEMA-3` is a required check from Phase 0 while `twinflow.lss.finding` lands
in Phase 2 and `twinflow.twin.state_snapshot` in Phase 1. Every `consumes.yaml` entry carries a
`since` field naming the phase its producer first exists. `SCHEMA-3` skips an entry whose subject
is absent from `schemas/registry.yaml` and reports it as `pending`, and prints the pending count.
The check that keeps that from becoming a silent hole is `SCHEMA-6`: a `consumes.yaml` entry may be
pending only while its subject is absent from the registry, so the day the producer registers its
subject, the consumer's declaration becomes binding without anyone editing it. A pending entry with
a registered subject is a failure, not a skip.

The same rule covers the reverse direction. `twinflow.integration.api_request` and
`twinflow.integration.webhook_delivery_attempted` are registered in Phase 0 (4.1) although
`twinflow-api` is a Phase 2 deliverable, because `SCHEMA-1` needs three samples per subject and
those samples are authored with the schema. Their `registry.yaml` rows carry
`producers: []` and `status: reserved` until Phase 2, and `SCHEMA-7` asserts that a reserved
subject has no producer and that a subject with a producer is not reserved.

### 4.3 Subject naming and the registry manifest

Subjects are `twinflow.<domain>.<event_name>`, snake_case, singular verb-phrase past tense.
Registered domains at Phase 0: `kernel, config, migration, integration, telemetry, twin, lss,
fleet, genealogy, order, finance, mining, forecast, agent, cv, security`. New domains need a
line in `schemas/registry.yaml` and an owning package.

```yaml
# schemas/registry.yaml
producer_ids: [sim, api, dashboard, agent, device-agent, cli] # the closed set of E3
subjects:
    - subject: twinflow.telemetry.sensor_reading
      owner: twinflow-sensors
      versions: ["1.0", "1.1", "1.2", "1.3"]
      current: "1.3"
      status: active # active | reserved | deprecated
      compat: additive-only
      since_phase: 3
      producers: [twinflow-sensors, crates/twinflow-device-agent]
      producer_ids: [sim, device-agent]
      consumers:
          [
              twinflow-fleet,
              twinflow-lss,
              twinflow-twin,
              twinflow-api,
              twinflow-storage,
          ]
      partition_key: device_id
      retention: historian
```

`producer_ids` at the top of the file is the closed set E3 draws `twinflowproducerid` from, and the
per-subject `producer_ids` list is which of them may emit that subject. `SCHEMA-8` fails an event
whose `twinflowproducerid` is not listed for its subject, which turns a mislabelled producer into a
contract failure rather than a confusing log.

---

## 5. Behavior

### 5.1 The two modes

One codebase, two runtimes. The difference is entirely which implementations `RuntimeBuilder`
binds.

| Port        | Simulation mode                                                                               | Production mode                                                                                                                                                   |
| ----------- | --------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Clock       | `SimClock` over the `SimEventLoop`, optionally wrapped in `PacedClock`                        | `RealClock` (`time.monotonic_ns` for durations, `datetime.now(UTC)` for the anchor only)                                                                          |
| Rng         | `SplittableRng(base_seed, replication_index)`                                                 | `SplittableRng(base_seed, replication_index)`, same class; production runs are seeded too, because a production device agent that draws jitter stays reproducible |
| Network     | `InMemoryNetwork` with `FaultSchedule`                                                        | `MqttNetwork` over aiomqtt to Mosquitto, EMQX, or NanoMQ                                                                                                          |
| EventBus    | `InMemoryEventBus`                                                                            | `MqttEventBus` over the tier's broker at garage and growth, `KafkaEventBus` at enterprise                                                                         |
| EventLog    | `InMemoryEventLog` plus optional NDJSON sink                                                  | `LocalNdjsonEventLog`, `PostgresEventLog`, or `KafkaEventLog`                                                                                                     |
| TableStore  | `InMemoryTableStore` (Arrow buffers, queried through an embedded DuckDB pinned to one thread) | `DuckDbTableStore` / `DeltaTableStore` / `PostgresTableStore`                                                                                                     |
| BlobStore   | `InMemoryBlobStore`                                                                           | `LocalBlobStore` or `S3BlobStore`                                                                                                                                 |
| KeyValue    | `InMemoryKeyValue`                                                                            | `LocalFileKeyValue` at garage, `PostgresKeyValue` above it                                                                                                        |
| IdGen       | `DeterministicIdGen`                                                                          | `Uuid7IdGen`                                                                                                                                                      |
| Env         | `FrozenEnv` populated from the resolved config only                                           | `OsEnv`                                                                                                                                                           |
| MetricsSink | `RecordingMetricsSink`                                                                        | OpenTelemetry OTLP exporter                                                                                                                                       |
| Secrets     | `FrozenSecrets` populated from the resolved config only                                       | `DotEnvSecrets`, `DockerSecrets`, or `K8sSecrets`                                                                                                                 |
| Identity    | `NullIdentity` (every principal is `sim:local` with the configured scopes)                    | `ApiKeyIdentity`, `OidcIdentity`, or `MtlsIdentity`                                                                                                               |
| Inference   | `RecordedInference` replaying a pinned response cassette (D-04)                               | `OllamaInference`, `VllmInference`, or `HostedInference`, registered by `twinflow-agent`                                                                          |

`InMemoryTableStore` is the one simulation implementation that embeds a third-party engine, so its
module path is listed in `adapter_paths` (5.9) with a reason string rather than left to trip
`TFD003`. It opens DuckDB with `threads=1`, `preserve_insertion_order=true`, and no filesystem
access, which removes the two nondeterminism sources a SQL engine otherwise contributes: a thread
count derived from the machine's core count, and an unordered hash aggregate. INV-K21 is the
property that proves it.

`EventBus` has no in-memory production binding at any tier, and the reason is that production means
more than one process. Garage tier already runs `twinflow-sim`, `twinflow-api`, and
`twinflow-dashboard` as separate containers (5.11), so an in-process fan-out would deliver to
nobody. `MqttEventBus` publishes subject-addressed messages over the tier's existing broker with
retain and last-will unused, which is the subset D-08 says an `EventBus` may rely on, and
`KafkaEventBus` takes over at enterprise where the fan-out is a partitioned log. The broker bridge
between them is the arrangement D-08 describes: MQTT at the operational edge, the partitioned log
at the information layer.

Precedence, applying D-12, because two keys can name a binding and the earlier draft did not say
which wins. `simulation.mode` selects the port family: `simulation` binds the deterministic family
in column two, `production` binds the real family in column three. `deployment.adapters.*` selects
within the production family only. Naming an adapter while `simulation.mode: simulation` is
`TF-C043 deployment.adapters.<port> is meaningless in simulation mode; the port family is chosen by
simulation.mode`, an error rather than a silent no-op. `deployment.tier` selects nothing by itself;
it only supplies the defaults each `deployment.adapters.*` key takes when the key is absent.

`RuntimeBuilder.from_config(cfg)` is the one place that reads either key. There is no
`if simulation:` anywhere outside `RuntimeBuilder` and the adapter modules. A lint rule (`TFD013`)
flags the identifier `mode` compared against a literal outside those files.

### 5.2 The deterministic scheduler

Every subsystem is written as ordinary `async def` code. In production mode it runs on the standard
asyncio loop. In simulation mode it runs on `SimEventLoop`, a full implementation of
`asyncio.AbstractEventLoop` whose time source and timer heap are backed by `simpy.Environment`.

Mechanics:

1. `SimEventLoop.time()` returns `env.now / tick_hz` as a float for asyncio's benefit, while
   `SimClock.now()` returns the integer tick value that all application code uses. Application code
   never calls `loop.time()`.
2. `call_at(when, cb)` schedules a SimPy timeout event. SimPy already breaks ties on
   `(time, priority, eid)` with a monotonic `eid` counter, which gives a total order over
   simultaneous events.
3. `call_soon(cb)` appends to a FIFO ready queue drained fully before sim time advances. The loop
   never advances sim time while a callback is runnable, which is what makes "zero-duration work"
   take zero sim time and makes ordering independent of machine speed.
4. All IO in simulation mode goes through `InMemoryNetwork` and `InMemoryStorage`, which complete
   through `call_soon` or `call_at`. There are no real file descriptors, so `add_reader`/
   `add_writer` raise `NotImplementedError`. That is deliberate: a subsystem that tries to open a
   socket fails loudly in simulation rather than silently becoming nondeterministic.
5. `run_in_executor` raises. `asyncio.to_thread` raises. Threads are the one thing the scheduler
   cannot make deterministic, and lint rule `TFD004` bans them ahead of the runtime error.
6. Structured concurrency uses `asyncio.TaskGroup`. Task creation order is the tie-break for
   simultaneous readiness, and task creation order is deterministic because the code path is
   deterministic.

Rationale for building the loop rather than writing subsystems as SimPy generators: SimPy
generators cannot run in production, and the whole point of DST is one codebase. The alternative
considered and rejected is writing the subsystems twice.

What SimPy is used for, stated concretely because the earlier draft used only `env.now` and the
tie-break rule, which `heapq` supplies in a few lines and which would not have justified the
dependency:

| SimPy element                                        | Used for                                                             |
| ---------------------------------------------------- | -------------------------------------------------------------------- |
| `Environment.now` and the timeout heap               | the loop's time source and timer heap                                |
| `(time, priority, eid)` ordering with monotonic eid  | the total order over simultaneous events                             |
| `Resource`, `PriorityResource`, `PreemptiveResource` | station servers, dock doors, AMR charge points, forklifts            |
| `Container`                                          | bulk levels: AMR battery charge, tank levels in the upstream factory |
| `Store` and `FilterStore`                            | buffers and staging lanes where an item is selected by predicate     |

The three resource classes, `Container`, and `Store` are the reason a warehouse twin reaches for a
DES library at all, and none of them is available to `async def` code through SimPy's generator
API. `twinflow.kernel.resources` rebuilds them as asyncio-native, deterministically
ordered primitives and is a Phase 0 deliverable, not a Phase 1 discovery. Waiter ordering is FIFO
within a priority class, ties broken by request sequence number, which is INV-K22.
`test_resources_match_simpy_semantics` runs a table of scripted request-and-release sequences
against both the twinflow primitive and the SimPy equivalent and asserts the grant order matches,
which makes SimPy a conformance oracle for the part of it that is not used directly.

The size of the loop is not estimated. `SimEventLoop` implements the subset of
`asyncio.AbstractEventLoop` that the codebase calls, and that subset is enumerated rather than
guessed: `time`, `call_soon`, `call_at`, `call_later`, `create_task`, `create_future`,
`run_until_complete`, `run_forever`, `stop`, `is_running`, `is_closed`, `close`,
`default_exception_handler`, and `set_exception_handler`. Everything else raises
`NotImplementedError`. `test_sim_event_loop_implements_exactly_the_declared_surface` compares the
overridden method set against that list and fails on either a missing entry or an undeclared
extra, so the surface is a checked contract rather than a line count.

Snapshotting: `Snapshot` captures the current sim instant, the ready queue, the timer heap, the RNG
stream draw counters, the resource waiter queues, storage state, network buffers, and per-subsystem
state gathered through the `Snapshottable` protocol. Phase 0 defines that protocol and implements it for the kernel's own
state, including the resource primitives above. Subsystem implementations land with E4, which is
when replay and counterfactuals need them. The DET-6 gate is written in Phase 0 and marked
`xfail(strict=True)` until E4, so the gate exists before the feature and flips to passing rather
than being invented later. `checkpoint_written.resumable` (4.1) is `false` until that flip, so a
Phase 0 checkpoint never claims more than it holds.

### 5.3 The sim clock and time compression (C2)

`SimClock` exposes integer tick time. `PacedClock` wraps it and is the pacer of D-02, one of the
four places a wall clock may be read:

```
before advancing sim time from t0 to t1:
    if speed is finite:
        target_wall = pacer_start_monotonic_ns
                    + (t1 - run_start_sim_ts) * 1_000_000_000 // (tick_hz * speed)
        block on the real monotonic clock until target_wall
```

The monotonic reading is the pacer's own, taken when pacing starts and held in `PacedClock`. The
`wall_clock_anchor` in the hashed core carries no monotonic field at all (M5), and the pacer's
reading never reaches an event payload, the hashed tape, or a branch. `PacedClock` lives at
`packages/twinflow-kernel/src/twinflow/kernel/_impl/paced.py`, which is listed in `adapter_paths`
(5.9) with the reason string `the D-02 pacer`, and it carries the required
`# twinflow: allow-nondeterminism(TFD001)` annotation with an ADR link because it sits inside the
kernel package.

Pacing delays the loop between events and never reorders them, so the emitted log is identical at
every speed. `test_pacing_does_not_change_the_tape` asserts a paced run and an unpaced run produce
identical logs, and DET-4 is the CI gate over the same property. That is the whole safety argument
for time compression: pacing changes when an event is emitted in wall time, never which event is
emitted or in what order.

Speed control protocol: a control-plane subject `twinflow.control.command` with
`{"command": "sim.speed.set", "value": 4.0}` accepted from the CLI, the REST API
(`POST /api/v1/runs/{id}/speed`), and the dashboard websocket. Accepted values: `pause`,
`step` with `{"ticks": n}` or `{"events": n}`, `asap`, or a float in `[0.01, 100000]`. Every change
emits `twinflow.kernel.clock_speed_changed`. Out-of-range values return `TF-A031`.

The lower bound of 0.01 is what a human operator can ask for at the dashboard, where running a
demo at one hundredth of real time is a legitimate request. It is not what a property test or a
determinism gate may use, and applying D-13 the arithmetic is written down rather than assumed.

| Consumer | Scenario                       | Speed range             | Worst-case wall time              | Budget |
| -------- | ------------------------------ | ----------------------- | --------------------------------- | ------ |
| Operator | any                            | `[0.01, 100000]`        | unbounded, and that is the point  | none   |
| DET-4    | `SCN-F0`, 60 simulated seconds | `asap` and 50           | 60 / 50 = 1.2 s for the paced arm | 6 min  |
| INV-K9   | `SCN-F0`, 60 simulated seconds | log-uniform `[60, 1e5]` | 60 / 60 x 25 examples = 25 s      | 5 min  |

The Hypothesis strategy `speeds()` clamps its log-uniform draw to `[60.0, 100000]` and caps INV-K9
at 25 examples, and both numbers live in the generator rather than only in the config validator, so
a property run cannot select a speed whose worst case exceeds the `property` job budget. The clamp
is stated in one place and imported by every property that draws a speed;
`test_speed_strategy_lower_bound_is_clamped` asserts the generator's own minimum, so a future edit
that widens it fails a test rather than a timeout. `BUDGET-1` reads the same three numbers and
recomputes the products above, which is what turns the table from arithmetic in prose into a
checked claim: a scenario that grows past its job budget then fails as a defect rather than as a
timeout.

Timeouts: `clock.timeout(Duration)` is the only timeout primitive. A "broker keepalive of 60
seconds" is 60 sim seconds and compresses with everything else. `asyncio.wait_for` is banned by
`TFD014` because it uses `loop.time()` directly.

Wall-clock mapping: recorded once per run in `RunManifest.wall_clock_anchor`:

```json
{
    "sim_ts": 0,
    "utc": "2026-03-02T06:00:00Z",
    "tz": "America/Chicago",
    "dst_offset_minutes": -360
}
```

Shift calendars, tariff effective dates, and S&OP monthly cycles all need a real calendar date, so
the anchor carries a timezone and the config declares `facility.timezone`. DST transitions inside a
run are honored through `zoneinfo` at the calendar layer; sim ticks themselves are monotonic and
unaffected, which is the property that avoids a night shift being recorded as 25 hours long across
a fall-back transition. VAL-F14 is the gate over it.

### 5.4 Determinism (C1)

Applying D-05, the determinism claim is two tiers and the README states both rather than the
stronger one alone. A vague determinism claim is worse than none, and an unachievable one is worse
than vague.

| Tier                | Conditions                                                           | Guarantee                                                                                                                                          | Gate                       |
| ------------------- | -------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------- | -------------------------- |
| A. Byte-identical   | same seed, same resolved config, same platform, same pinned lockfile | the canonical event log is byte-identical, and so is `event_log_hash`                                                                              | DET-1, hash equality       |
| B. Value-equivalent | same seed and resolved config, different OS or CPU                   | business events are identical in count, order, subject, and every integer and quantised field; continuous fields agree within a measured tolerance | DET-2, reported divergence |

The gap between A and B is not a rounding gap, and calling it one would have been the most
dangerous sentence in this document. NumPy's published compatibility policy for `numpy.random`
states the mechanism plainly: "different CPUs implement floating point arithmetic differently, and <!-- docs-lint-ok STE-TERM-WORD verbatim quotation of the NumPy compatibility policy -->
this can cause differences in certain edge cases that cascade to the rest of the stream." A
rejection-sampling distribution such as gamma or Poisson compares a transcendental against a
uniform draw. One unit in the last place of `log` or `exp` can flip that comparison, which consumes
a different number of uniforms, which desynchronises the stream from that point on. The result is
not a 1e-9 difference in one field. It is a different run, with different integer fields and a
different event count.

The same page sets the ceiling on tier A. It promises the stream only when you "perform the same <!-- docs-lint-ok STE-TERM-WORD verbatim quotation of the NumPy compatibility policy -->
sequence of method calls with the same arguments, on the same build of numpy, in the same
environment, on the same machine", and adds that "these conditions are very strict". Tier A's
conditions are that sentence restated as a gate, which is why tier A names the pinned lockfile and
the platform and tier B does not.

Two consequences follow, and both are design decisions rather than caveats.

First, the twinflow distribution layer calls only the three `Generator` methods NEP 19 commits to.
NEP 19, NumPy's Random Number Generator Policy, is specific about which methods carry a stream
guarantee: "They MUST guarantee stream-compatibility for a specified set of methods ... Namely,
`.bytes()`, `integers()` ... `random()`". `normal`, `gamma`, `poisson`, and every other
distribution method sit outside that set, and NEP 19 states that breaking their streams "will be
allowed with caution ... on X.Y releases, never X.Y.Z". `twinflow.kernel.numeric`
implements inversion and ziggurat sampling for the families the `Rng` port exposes on top of
`random`, `integers`, and `bytes` alone. This removes the rejection-loop desynchronisation from the
twinflow-owned path, because the number of draws a twinflow distribution consumes is fixed by its
own algorithm rather than by a floating-point comparison inside NumPy. `TFD017` bans every other
`Generator` method outside that module, and R8 fixes the block size at one value per call because
the same policy page states that "Calling `rng.random()` 5 times is not guaranteed to give the same
numbers as `rng.random(5)`".

Second, DET-2 distinguishes desynchronisation from drift instead of lumping them together.
`test_rng_stream_length_is_identical_across_platforms` compares
`RunProvenance.rng_draw_counts_sha256` between the two runners first. If the draw counts differ,
the failure is named as stream desynchronisation and the field-by-field comparison is not run,
because comparing two different runs field by field produces noise rather than a diagnosis. Only
when draw counts match does DET-2 compare fields.

The DET-2 tolerance is measured, not chosen, and until it has been measured it is absent rather
than guessed. The gate reports the observed maximum relative divergence over continuous fields
across the matrix, writes it to `artifacts/determinism/divergence-<version>.json`, and compares it
against `[tool.twinflow.det] cross_platform_tolerance` in the root `pyproject.toml`. That key is
set from the first ten green runs across the ubuntu and macos runners, at ten times the largest
divergence those runs showed, and the file records the run ids it came from. Before those ten runs
exist the key is absent, DET-2 asserts only the integer and quantised half and reports the
continuous divergence without judging it, and open question 14 records that the number is not yet
established. When a later observation exceeds the recorded tolerance, the gate names which of the
two explanations applies: the tolerance was set from too little evidence, or a real defect
appeared. It never passes by widening itself, and `test_cross_platform_tolerance_is_not_edited_by_ci`
asserts that no CI job writes the key.

Mitigations that narrow the gap: all times are integers (T1); every float that crosses the event
boundary is quantised to the precision its schema declares in `x-twinflow-precision` before
serialization; canonical JSON uses RFC 8785, whose section 3.2.2.3 requires numbers to be
serialized per ECMA-262 section 7.1.12.1 including its Note 2, which is shortest round-trip and
so platform independent; CI exports `NPY_DISABLE_CPU_FEATURES` to a common baseline so
numpy's SIMD dispatch matches across runners.

PYTHONHASHSEED: `just` and CI export `PYTHONHASHSEED=0`. DET-3 also runs one job at
`PYTHONHASHSEED=12345` and asserts an identical log, which catches the set-iteration leaks D-03
bans and that the lint's static rule cannot see.

Third-party determinism is the remaining risk. scikit-learn, Optuna, statsforecast, and any
torch-backed model all reach for global RNG state. Handling:

- `twinflow.kernel.thirdparty.deterministic_context(rng_child)` seeds `numpy.random` legacy global
  state, `random`, `torch` (if present), and `PYTHONHASHSEED`-sensitive library caches, and
  restores on exit. Every call into a third-party stochastic library is wrapped in it.
- Each such library gets a dedicated regression test in `tests/determinism/thirdparty/` named
  `test_<library>_is_deterministic`, asserting two calls with the same context produce identical
  output. When a library version bump breaks it, the failing test names the library.
- Libraries that cannot be made deterministic are recorded in `docs/limitations.md` with the
  specific call site and the effect, and their outputs are excluded from the byte-identity gate by
  an explicit allowlist in `determinism_exclusions.yaml`, each entry needing an owner and a
  linked issue. Exclusions are visible, never silent.

Process mining is not on that list, and the reason is a license rather than a seed. Applying D-14,
PM4Py and `pm4pyminimal` are AGPL-3.0 (version 2.7.23.3, read from the package index), and AGPL
section 13 covers network interaction, which this project does through a dashboard, an MCP server,
and an HTTP API. Importing either would place the whole work under AGPL and break the Apache-2.0
plus commercial dual license. `twinflow-procmine` is written here under Apache-2.0 instead, and
its determinism is this repository's to guarantee rather than a third party's to break. PM4Py
remains available as a development-only comparison oracle, which is what gives the conformance
gates in the LSS section an external reference under D-11.

Seed recording: `tf run` writes `artifacts/runs/<run_id>/manifest.json`, which is `RunProvenance`,
and `events.ndjson`, which is the tape. Every demo script, eval case (E27), dataset card (E25), and
replay bundle (E1) carries the run id and the seed in its front matter. A README claim with a
number carries the run id that produced it, checked by a docs lint
(`tools/check_measured_claims.py`) that fails on a number in the README's headline block without an
adjacent run reference. The same lint runs over the operator-facing strings in
`twinflow/config/messages/`, so a number printed to a user in a warning carries a run reference
too; 5.6's historian sizing warning is the case that rule was written for.

### 5.5 Schema registry (C3)

Layout:

```
schemas/
  registry.yaml
  envelope/v1.json
  telemetry/sensor_reading/v1.3.json
  telemetry/sensor_reading/v1.2.json          # historical versions are never deleted
  lss/finding/v2.0.json
  genealogy/lot_event/v1.0.json
  order/order_state_changed/v1.1.json
  finance/gl_posting/v1.0.json
  ...
  x-keywords.md                                # documentation of twinflow's custom keywords
```

JSON Schema 2020-12. Custom annotation keywords, all prefixed `x-twinflow-`:

| Keyword                    | Meaning                                                                                  |
| -------------------------- | ---------------------------------------------------------------------------------------- |
| `x-twinflow-precision`     | decimal places a float is quantised to before serialization                              |
| `x-twinflow-unit`          | the SI unit the number is expressed in, validated against pint                           |
| `x-twinflow-open-enum`     | consumers must tolerate unknown members; only such enums may gain members within a major |
| `x-twinflow-open-range`    | consumers must tolerate values outside the declared range; only such fields may widen    |
| `x-twinflow-pii`           | always false in this repo, asserted by a test, because the data is synthetic             |
| `x-twinflow-partition-key` | the field used for partitioning in the historian                                         |
| `x-twinflow-since`         | the release that added this field                                                        |
| `x-twinflow-not-in-hash`   | a config key excluded from `ConfigHash` because it cannot change the tape (G4, M6)       |
| `x-twinflow-stored-bytes`  | measured stored bytes per row for a subject, with the run id it was measured on (5.6)    |

Version numbering: `MAJOR.MINOR` per subject, independent of the release version. MAJOR changes are
breaking, MINOR are additive.

Compatibility rules, enforced by `tf-schemas check`:

| Change                                   | Within a major                                                        |
| ---------------------------------------- | --------------------------------------------------------------------- |
| Add an optional property with a default  | Allowed, MINOR bump                                                   |
| Add a required property                  | Rejected                                                              |
| Remove a property                        | Rejected                                                              |
| Make an optional property required       | Rejected                                                              |
| Make a required property optional        | Rejected (breaks consumers that assume presence)                      |
| Widen a numeric range or string pattern  | Allowed, MINOR bump, only where `x-twinflow-open-range: true`         |
| Widen a range on a closed-range field    | Rejected (breaks consumers that assume the narrow range)              |
| Narrow a numeric range or string pattern | Rejected                                                              |
| Add an enum member                       | Allowed only if `x-twinflow-open-enum: true`, MINOR bump              |
| Remove an enum member                    | Rejected                                                              |
| Change a type                            | Rejected                                                              |
| Rename a property                        | Rejected (add the new one, deprecate the old, remove at MAJOR)        |
| Add a new subject                        | Allowed, no bump to existing subjects                                 |
| Deprecate a subject                      | Allowed, MINOR bump, `status: deprecated` plus a `removed_in` release |

The range rule needs the paired keyword because widening breaks a consumer in the same way
narrowing does. A consumer that read `divert_rate` as a value in `[0, 1]` and sized a fixed-point
field accordingly breaks when the producer starts emitting 1.4, and it breaks silently. The
distinction is declared by the producer at the field level, exactly as
`x-twinflow-open-enum` declares it for enums, and a consumer that reads an `x-twinflow-open-range`
field has been told to handle values outside the range. `SCHEMA-3` fails on a widened range for any
field a consumer declares in `consumes.yaml` unless that field carries `x-twinflow-open-range:
true`, which closes the hole where a widened range passed the drift check in silence.

A MAJOR bump needs: a new `vN.0.json`, an upcaster from every prior major, an entry in the
CHANGELOG compatibility table, and both versions publishing in parallel for at least one minor
release of the repo. That last clause is a gate, not an intention. `SCHEMA-9` reads
`registry.yaml`'s `parallel_until` field on the superseded major, and for each release inside the
overlap window it asserts that the `SCN-F4` smoke run emitted at least one sample of the superseded major
and at least one of its successor. A producer that quietly stopped emitting the superseded major during the
overlap fails the check, which is what the clause was for.

Producer/consumer contract tests:

- Each producing package ships `tests/contract/samples/<subject>.v<ver>.json`, at least three
  samples per subject covering minimum, maximum, and a realistic middle case. `SCHEMA-1` validates
  every sample against its schema.
- Each consuming package ships `consumes.yaml` listing the subject, version range, the exact field
  paths it reads, and the `since` phase of 4.2. `SCHEMA-3` fails when a consumed path disappears,
  changes type, narrows, or widens outside `x-twinflow-open-range`.
- `SCHEMA-2` fails when a schema file changes without a version bump, detected by comparing content
  hashes against the previous tag.
- `SCHEMA-4` fails when generated bindings (Pydantic and Rust serde) differ from a fresh
  regeneration, which keeps the checked-in bindings honest.

Codegen: `just schemas-gen` runs `datamodel-code-generator` for Python into
`twinflow/schemas/models/` and a `typify`-class generator for
`crates/twinflow-device-agent/src/schemas/`. The Rust agent and the Python fleet cannot
drift on the wire format, which is the failure a hand-maintained second definition invites.

Codegen closes the wire-format gap. It does not close the behavior gap, and D-06 is the ruling
that names the other half: the Rust agent draws randomness, so it needs the same RNG contract, not
only the same field names. `RUST-1` (7.3) is to the RNG what `SCHEMA-4` is to the wire format, and
both run in the `rust` CI job.

### 5.6 Config validation (C5)

Pipeline, in order, each stage reporting all its errors before the next runs:

1. **Parse.** `ruamel.yaml` round-trip load. Syntax errors report as `TF-C001` with line and
   column from the parser.
2. **Include and overlay resolution.** `!include` of relative paths, `--overlay file.yaml` merges
   with documented semantics (mappings deep-merge, sequences replace unless the overlay key ends in
   `+`, in which case it appends), `--set dotted.path=value` applied last. Merge is associative
   over disjoint overlays and idempotent for a repeated identical overlay (INV-K10).
3. **Schema validation.** JSON Schema 2020-12 against `schemas/config/facility/v1.3.json` and the
   registered section schemas. Errors map JSON pointers back to line and column through the
   provenance map.
4. **Model validation.** Pydantic models with `extra="forbid"`, field validators for ranges and
   formats.
5. **Unit resolution.** Every value whose schema declares `x-twinflow-unit` is parsed by pint and
   converted to the canonical unit. `"1.2 m/s"` is fine, `"1.2"` is `TF-C201 missing unit`,
   `"1.2 kg"` for a speed field is `TF-C202 unit mismatch: expected a velocity, got a mass`.
6. **Cross-reference checks.** Every reference resolves: `flows[].station_id` into
   `layout.stations[].id` (`TF-C101`); `sensors.instances[].type` into the sensor catalog
   (`TF-C102`); `spec_limits` keys into metric ids in `metrics.yaml` (`TF-C103`);
   `policies.slotting.zones` into `layout.zones[].id` (`TF-C104`);
   `partners.suppliers[].lanes[]` into `transport.lanes[].id` (`TF-C105`). Each names both the
   dangling reference and the nearest valid candidate.
7. **Plausibility checks.** Warnings, not errors, in the `TF-C3xx` range: a station with zero
   capacity, a shift calendar covering fewer than 1 hour per day, a dock count of zero with inbound
   flows defined, and a sensor sample rate and horizon whose product exceeds the historian volume
   threshold.

Stage 6 works from Phase 0, and the sequencing that makes that true is worth stating because the
targets it resolves against belong to later phases. Each of the five reference targets is a
registered _reference domain_ declared through the `twinflow.config.references` entry-point group
by the package that owns it, and the loader resolves against the union of the domains that are
registered in the running installation. A reference into a domain no package has registered is
reported as `TF-C130 reference target 'transport.lanes' has no installed owner (install
twinflow-forecast)`, a warning at garage tier and an error under `strict_sections: true`. This is
the same mechanism 2.4 uses for config blocks, applied to cross-references.

That keeps `CFG-2` honest from Phase 0. Every `TF-C1xx` code is produced by at least one test
because each reference domain ships a fixture pair, one resolving and one dangling, alongside its
schema. `TF-C101` and `TF-C103` have their fixtures in Phase 0 because `layout` and `metrics.yaml`
are Phase 0 artifacts; `TF-C102` gains its fixture in Phase 3 with the sensor catalog; `TF-C104` in
Phase 3b with slotting; `TF-C105` in Phase 3h with the transport network. `CFG-2` reads the same
entry-point registry and asserts that every code belonging to a _registered_ domain has a test, so
the gate cannot pass by the domain being absent and cannot fail for a domain that has not shipped.
`CFG-4` asserts the complement: every reference domain declared in `docs/reference/error-codes.md`
either has a registered owner or a named phase.

Error rendering, human format:

```
error[TF-C012]: unknown key 'converyor_speed' in station 'sort-01'
  --> profiles/midmarket_3pl.yaml:214:7
     |
 212 |   - id: sort-01
 213 |     type: sortation
 214 |       converyor_speed: 1.2 m/s
     |       ^^^^^^^^^^^^^^^ did you mean 'conveyor_speed'?
     |
   = valid keys for station.type=sortation: conveyor_speed, divert_count, divert_logic,
     induct_rate, recirculation_limit
   = docs: https://<pages>/reference/facility/#stationsortation

warning[TF-C312]: sensor 'vib-conv-07' samples at 2000 Hz over a 30 day horizon
  --> profiles/midmarket_3pl.yaml:891:9
     |
   = 2000 Hz x 2592000 s = 5.184e9 readings
   = {STORED_BYTES} stored bytes per reading gives about {VOLUME} in the historian
   = bytes per reading measured from run {RUN_ID}, subject
     twinflow.telemetry.sensor_reading v1.3, Delta with zstd level 3
   = set sensors.instances[].downsample or shorten simulation.horizon
```

The volume warning prints two numbers and treats them differently, because they are two kinds of
claim. The reading count is arithmetic over the config, recomputed in the message so a reader can
check it against the two config values named on the line above. The byte figure is a measurement,
so the template carries no literal at all: `{STORED_BYTES}` is read from
`x-twinflow-stored-bytes` on the subject schema, `{VOLUME}` is the product, and `{RUN_ID}` is the
profile run the constant was measured on. `just measure-row-bytes` writes all three, and
`tools/check_measured_claims.py` fails the build when `x-twinflow-stored-bytes` changes without its
run reference changing.

Until that measurement exists, the field is absent and the message degrades to the reading count
plus `historian volume not yet measured, run just measure-row-bytes`. An unattributed round number
in operator-facing output is the same defect as an unattributed round number in the README, and it
is caught by the same lint. The current unfilled value is
<!--METRIC:historian_stored_bytes_per_sensor_reading@v0.4.0-->TBD<!--/METRIC-->, which the release gate

refuses to tag from v0.4.0 onward while it still reads TBD. The tag it names is the one its
producer arrives at: foundations 5.5 places `twinflow.telemetry.sensor_reading` at `since_phase: 3`,
which `roadmap.yaml` maps to v0.4.0, and the Delta writer `EVENT_TABLE` names is the `delta` extra
of 2.7 rather than a base install. A marker owed at a tag whose producer does not exist is a claim
no measurement can discharge, and the three exits the gate offers are to measure it, to drop the
claim, or to name the tag it arrives at. Dropping it would delete a number the plan owes, which
ENGINEERING rule 4 refuses, so it names the tag. `tools/measure_row_bytes.py` fills it, and today it
refuses. It prints the two reasons rather than assuming them. `twinflow.telemetry.sensor_reading` is
absent from `schemas/registry.yaml`, so nothing fixes the payload whose bytes would be counted. The
writer `EVENT_TABLE` names is not installed, so there is no Delta table to measure. A Parquet byte
count belongs to the encoder that produced it, and a substitute encoder measures itself.

JSON format is the same content under `{"errors": [...], "warnings": [...]}` for CI and editor
integration. Exit codes: 0 clean, 1 errors present, 2 warnings present with `--strict-warnings`,
3 the file could not be parsed at all.

Commands:

- `tf config validate <path> [--overlay ...] [--set ...] [--format human|json] [--strict-warnings]`
- `tf config explain <dotted.path>` prints the resolved value, its unit, its provenance chain, its
  schema description, and its default.
- `tf config hash <path>` prints the `ConfigHash`.
- `tf run --dry-run` performs the full load, builds the `Runtime`, constructs every subsystem,
  emits `run_started`, and exits without advancing the clock. It reports the resource counts it
  would create (devices, stations, tasks) and the estimated historian volume.

### 5.7 Migrations (C6)

Two domains, one framework.

**Store migrations.** `migrations/<domain>/NNNN_<slug>.py` with:

```python
VERSION = 7
DOMAIN = "historian"
DESCRIPTION = "add energy_kwh to station_cycle"
DEPENDS_ON = 6

async def up(store: TableStore, log: EventLog) -> MigrationResult: ...
async def check(store: TableStore) -> None: ...    # raises on failure
BACKFILL = "recompute"   # "none" | "recompute" | "null" | "constant:<value>"
```

Forward only. Rollback is by restoring a backup, and the drill for that is E18's backup and
recovery scenario, which is why that scenario is a real capability rather than a story. Applied by
`tf historian migrate [--to N] [--dry-run]`, recorded in a `_twinflow_schema_version` table and as
a `twinflow.migration.applied` event. Applying twice is a no-op (INV-K14). On Delta tables,
permitted operations are add-column and add-partition-column only; anything else writes a new table
version and a view, because rewriting a Delta table in place forfeits time travel and time travel
is the point of using Delta.

**Recorded-run compatibility.** A log recorded under an older schema snapshot is readable through
upcasters. `twinflow.schemas.upcast` holds a registry keyed `(subject, from_version)`. Every
version bump that removes or renames anything ships an upcaster in the same commit; `SCHEMA-5`
fails a version bump without one. Upcasters are never deleted, so the set grows monotonically and
the repo can always read every log it has ever written. Archived golden logs live in
`tests/fixtures/logs/<release>/` and `MIG-2` replays each one on every CI run, asserting that
derived KPIs match the golden values.

**Config upgrader.** `tf config upgrade <path> --to 2.0` applies steps from `migrations/config/`,
using ruamel round-trip so comments and formatting survive. Each step declares
`(from_version, to_version, transform, ambiguity_check)`. Where a transform cannot decide (a split
key whose new value depends on operator intent), it writes the best guess plus a
`# TODO(twinflow-upgrade): confirm, see docs/migrations/1.x-to-2.0.md#stations-split` comment and
exits 2. `--check` reports what would change without writing.

**CHANGELOG compatibility table**, maintained per release in `CHANGELOG.md`:

| Release | facility.yaml schema | event schema snapshot | historian version | reads runs from | reads configs from |
| ------- | -------------------- | --------------------- | ----------------- | --------------- | ------------------ |
| v0.3.0  | 1.0                  | s-2026.03             | 4                 | >= v0.1.0       | >= v0.1.0          |
| v0.4.0  | 1.1                  | s-2026.05             | 6                 | >= v0.1.0       | >= v0.1.0          |

`SEMVER-3` fails a release whose table row is missing or inconsistent with the registry.

### 5.8 Versioning and releases (C9)

Four versioned contracts and what governs each:

| Contract                   | Version carrier                                                                | Breaking change means                                                                                                                  |
| -------------------------- | ------------------------------------------------------------------------------ | -------------------------------------------------------------------------------------------------------------------------------------- |
| Python package public API  | the release version, lockstep across all bricks                                | removing or renaming a symbol in `__all__`, changing a signature incompatibly, tightening an input type, loosening an output guarantee |
| REST / GraphQL / MCP       | URL major (`/api/v1`), GraphQL SDL with `@deprecated`, MCP tool schema version | removing a route, field, or tool; adding a required parameter; changing a status code class; narrowing a response type                 |
| Event schemas              | per-subject `MAJOR.MINOR`, snapshot id in the manifest                         | anything in the rejected column of section 5.5                                                                                         |
| facility.yaml and catalogs | `schema_version` key inside the file                                           | removing a key, changing a default that changes behavior, changing a unit                                                              |

Lockstep versions across bricks, as C9 requires. Rationale: a reader who installs two bricks must
never consult a compatibility matrix. Cost, stated honestly in `docs/versioning.md`: a patch in one
brick republishes all of them, and PyPI carries versions with no changes for most bricks. The
alternative considered, independent versions per brick, was rejected because A1's promise is
"take one brick", not "solve a dependency graph", and because it would put a compatibility matrix in
the README where the "use just this part" table belongs.

Enforcement:

- `SEMVER-1`: `tf-api-diff` (griffe) compares public API against the previous tag and fails a
  removal or incompatible signature change unless the commit body has a `BREAKING CHANGE:` footer
  and the computed next version is a major.
- `SEMVER-2`: `tf-api check` diffs `api/openapi.v1.json` and `api/schema.graphql` against the
  previous tag with the same rule.
- `SEMVER-3`: CHANGELOG compatibility table present and consistent.
- Deprecation: `@deprecated(since="0.6.0", remove_in="1.0.0", use="new_name")` emits a
  `DeprecationWarning`, is listed in `API.md`, and a test asserts the warning is raised. Minimum
  overlap is one minor release for Python APIs and one major for event schemas.
- Pre-1.0: until Phase 5 completes, the minor acts as the major. `docs/versioning.md` states the
  1.0.0 criterion explicitly: Phase 5 complete, all VAL-GATEs green, all three A2 profiles running
  in CI, and the A6 surface frozen.

Release pipeline, triggered by a tag on `main`:

1. Compute the version from conventional commits since the last tag.
2. Regenerate the CHANGELOG section for the release, grouped by phase milestone.
3. Run the full CI matrix plus the nightly-only jobs.
4. Build sdists and wheels for every brick with `uv build --all`.
5. Build the Rust device agent for `x86_64-unknown-linux-gnu`, `aarch64-unknown-linux-gnu`, and
   `xtensa-esp32-espidf` (the last one for E47's hardware-in-the-loop path).
6. Generate the SBOM (CycloneDX) for the Python workspace and the Rust crate (C11 hook).
7. Record a determinism manifest: the `run_id` and `event_log_hash` of a smoke run for every
   profile present in `profiles/` at this version, committed to
   `artifacts/determinism/<version>.json` along with the profile count. This is what makes
   "byte-identical across releases where nothing relevant changed" a checkable claim rather than an
   assertion. The set is read from the directory rather than fixed at three, because
   `micro_fulfillment` lands in Phase 0, `midmarket_3pl` in Phase 3, and `enterprise_network` in
   Phase 3h, so a release tagged before Phase 3h has fewer than three and a manifest demanding
   three would fail every early release. `SEMVER-3` asserts the manifest lists exactly the profiles
   the tree contains, which is the assertion that keeps a profile from being quietly skipped once
   all three exist. `CFG-1` and `A2-1` apply to the profiles that exist, on the same rule.
8. Publish to PyPI with Trusted Publishing (OIDC, no long-lived token in the repo).
9. Create the GitHub release with the CHANGELOG section, SBOM, and determinism manifest attached.

Conventional commits are enforced on PR titles and on every commit by `commitlint` in CI
(`LINT-3`), with the parser tested against the Conventional Commits 1.0.0 specification's own
examples (VAL-F11).

### 5.9 The nondeterminism lint

`tf-lint-det` is an AST walker over `packages/*/src/**/*.py` plus `tools/**`. It is deliberately
not a Ruff plugin, because Ruff has no stable plugin API; it runs as a separate `just lint-det`
step and as CI gate `LINT-1`.

Rules:

| Code   | Bans                                                                                                                                                                      | Rationale                                     |
| ------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | --------------------------------------------- |
| TFD001 | `time.time`, `time.time_ns`, `time.monotonic`, `time.perf_counter`, `time.sleep`, `datetime.now`, `datetime.utcnow`, `date.today`, `pandas.Timestamp.now`                 | wall clock leak                               |
| TFD002 | `random.*`, `numpy.random.*` module-level functions, `numpy.random.seed`, `secrets.*`, `uuid.uuid1`, `uuid.uuid4`, `os.urandom`                                           | unseeded randomness                           |
| TFD003 | `socket`, `requests`, `httpx`, `urllib`, `aiomqtt`, `asyncpg`, `duckdb`, `deltalake` imports                                                                              | real IO outside adapters                      |
| TFD004 | `threading`, `multiprocessing`, `concurrent.futures`, `asyncio.to_thread`, `loop.run_in_executor`, `subprocess`                                                           | unschedulable concurrency                     |
| TFD005 | iteration over a set literal, `set(...)`, `frozenset(...)`, or a name annotated `set[...]`/`frozenset[...]` without `sorted()`                                            | hash-order dependence                         |
| TFD006 | `os.environ`, `os.getenv`                                                                                                                                                 | environment leak; use the `Env` port          |
| TFD007 | builtin `hash()`                                                                                                                                                          | randomized per process; use `stable_hash`     |
| TFD008 | `id()` in a comparison, sort key, f-string, or serialized value                                                                                                           | address leak                                  |
| TFD009 | `global` statements and module-level mutable containers                                                                                                                   | hidden state that survives across runs        |
| TFD010 | `open`, `Path.write_text`, `Path.write_bytes`, `Path.read_*`, `shutil`                                                                                                    | filesystem outside storage adapters           |
| TFD011 | `asyncio.run`, `asyncio.get_event_loop`, `asyncio.new_event_loop`                                                                                                         | the loop is chosen by `RuntimeBuilder`        |
| TFD012 | `platform.*`, `socket.gethostname`, `os.cpu_count`, `sys.getsizeof`                                                                                                       | machine-shape leak                            |
| TFD013 | comparing an identifier named `mode`/`run_mode` against a string literal outside `RuntimeBuilder` and adapter modules                                                     | mode branching in business logic              |
| TFD014 | `asyncio.wait_for`, `asyncio.timeout`                                                                                                                                     | use `clock.timeout` so timeouts are sim time  |
| TFD015 | `loop.time()`, and `.time()` on any name bound from `get_event_loop` or `get_running_loop`, outside `twinflow.kernel._impl.sim`                                           | the float time shim of T1a is not for callers |
| TFD016 | a `datetime`, a host name, or a package version reaching an argument of `EventLog.append` or `EventBus.publish`                                                           | the D-01 carve-out, checked at authoring time |
| TFD017 | any `numpy.random.Generator` method other than `random`, `integers`, and `bytes`, and any of those three called with a `size` argument, outside `twinflow.kernel.numeric` | only the NEP 19 stream-stable calls (R5, R8)  |

Scope and exemptions:

- Exempt paths are declared once, in the root `pyproject.toml`, each with a reason string so a
  reader can tell an adapter from an oversight:

    ```toml
    [tool.twinflow.det]
    adapter_paths = [
      { path = "packages/twinflow-kernel/src/twinflow/kernel/_impl/real/**", reason = "production adapters" },
      { path = "packages/twinflow-kernel/src/twinflow/kernel/_impl/paced.py", reason = "the D-02 pacer" },
      { path = "packages/twinflow-kernel/src/twinflow/kernel/_impl/memtable.py", reason = "embedded DuckDB over Arrow buffers, pinned to one thread" },
      { path = "packages/twinflow-storage/src/twinflow/storage/adapters/**", reason = "storage adapters" },
      { path = "packages/twinflow-api/src/twinflow/api/_server/**", reason = "ASGI server boundary" },
      { path = "packages/twinflow-cli/src/twinflow/cli/_entry.py", reason = "process entry point" },
      { path = "tools/**", reason = "build tooling, never imported at runtime" },
    ]
    ```

    The two kernel entries are the ones a reader checks first, because both are simulation-mode
    code rather than production adapters. `paced.py` reads the real monotonic clock and is the pacer
    D-02 permits; `memtable.py` imports DuckDB, which `TFD003` otherwise bans, and pins it to one
    thread with insertion order preserved so it contributes no nondeterminism. Both carry the inline
    annotation below in addition to the path entry, because they sit inside the kernel package.

- Inline escape hatch, required form:

    ```python
    # twinflow: allow-nondeterminism(TFD003) reason="paho-mqtt is the production transport" \
    #           owner="@jack" expires="2027-01-01" \
    #           adr="docs/adr/0003-the-network-port-and-its-mqtt-adapter.md"
    ```

    `reason` and `owner` are mandatory. `expires` is mandatory outside `adapter_paths`, and `LINT-2`
    fails on an expired annotation, which stops the escape hatch becoming a permanent hole. Inside
    the kernel package an `adr` link is also mandatory.

- Every annotation is inventoried by `just lint-det --report`, and the count is printed in CI
  output so the number is visible in every PR.

The lint is static, so it is incomplete. It cannot see nondeterminism inside a dependency, or a
dict ordering that happens to be derived from a set upstream. That is why DET-1 through DET-4 exist:
the lint catches the class cheaply at authoring time, and the hash check catches whatever the lint
missed at CI time.

### 5.10 In-memory fault-injecting network

`InMemoryNetwork` is the simulation implementation of the `Network` port, which D-08 keeps
MQTT-shaped. It models a topology of nodes and links, not a single bus, because the Purdue
segmentation of A3 and the E18 cross-zone drills need per-zone behavior. `InMemoryEventBus` is
the separate simulation implementation of `EventBus` and models subject fan-out with no retain, no
will, and no wildcard, which is what the analytics path actually needs and what a partitioned log
can deliver.

The topology file is named by `deployment.network.topology`, which resolves against
`deploy/topologies/`. Phase 0 ships two files so the key has a real default from the first run:
`single_zone.yaml`, which is one zone and no links and is the garage default, and
`purdue_three_zone.yaml`, which is the file below and is the growth and enterprise default. A run
with no topology named still has one, and `TF-C121` reports a name with no matching file
together with the list of files that do exist.

```yaml
# resolved from deployment.network
topology:
    zones:
        ot: { nodes: ["dev-*", "broker-ot", "gw-area-*"] }
        dmz: { nodes: ["broker-ot", "historian", "twin-sync"] }
        it: { nodes: ["analytics", "agent", "dashboard", "api"] }
    links:
        - {
              from: "ot",
              to: "dmz",
              via: "broker-ot",
              base_latency: "2 ms",
              jitter: { dist: "lognormal", mu: -6.9, sigma: 0.4 },
          }
        - { from: "dmz", to: "it", via: "historian", base_latency: "1 ms" }
    # no ot -> it link exists; a publish across it raises NoRouteToNode
```

Delivery semantics: MQTT QoS 0, 1, and 2 are modeled, including QoS 1 duplicate delivery on
retry, retained messages, last-will-and-testament on ungraceful disconnect (which is what the
Sparkplug death certificate rides on), and per-subscriber inflight windows. Store-and-forward
buffering at the device agent (component 6c) is device-side behavior that this network makes
testable: a `BROKER_DOWN` fault plus a device buffer yields the "kill the broker mid-demo and lose
nothing" demo as an automated test rather than a manual stunt.

Sequencing, because the device-side buffer is component 6c and lands in Phase 4 while `SCN-F2` runs
in the `e2e` job from Phase 0. `SCN-F2` asserts what exists at each phase and says which assertion
is which, rather than asserting a Phase 4 capability from Phase 0:

| Phase  | What SCN-F2 asserts about the broker outage                                                                                                                                                                                                |
| ------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| 0 to 3 | the outage is injected and healed on schedule, `fault_injected` brackets it, publishes during the outage raise `BrokerUnavailable` at the caller, no message is delivered twice after heal, and delivery order after heal is publish order |
| 4      | the above, plus zero message loss end to end: every reading published during the outage is present in the historian after reconnect, with the device buffer as the mechanism                                                               |

Both rows are written in Phase 0. The Phase 4 row is marked `xfail(strict=True)` until component 6c
lands, so it flips to passing rather than being invented then, which is the same discipline DET-6
uses for snapshots.

Fault application order per message: partition check, then drop, then corrupt, then duplicate, then
latency draw, then reorder buffer, then bandwidth accounting. Order is documented because it
changes outcomes, and the test suite pins it.

Every fault decision draws from `kernel.net.faults`, so a run with `--faults chaos/broker_flap.yaml`
at seed 42 is exactly reproducible, and the same seed with no faults produces a comparable baseline
because the process streams were never touched (F1).

### 5.11 Deployment tiers (A3)

The rule is that tiers differ by configuration, never by code path. What varies is which adapter is
bound to each port and which containers exist.

**Garage tier.** `just up-garage` runs `docker compose -f deploy/garage/compose.yaml up`.
Services: `mosquitto`, `twinflow-sim` (devices plus twin in one process), `twinflow-api`,
`twinflow-dashboard`, and `otel-collector`, with `ollama` behind an optional compose profile.
DuckDB runs in-process and is not a service. One network, no TLS, bound to loopback. Storage: a
DuckDB file plus a local Delta directory. This is the five-minute quickstart of requirement 9, and
`TIER-1` asserts the quickstart completes in under 5 minutes of wall time on the CI runner from a
cold image pull, with the number published in the README.

Service and network counts are asserted, not narrated. `TIER-5` runs `tf-count-services` over each
compose file and compares the result against `[tool.twinflow.tiers]` in the root `pyproject.toml`,
which is also the table the README renders from. A service added to a compose file without
updating that table fails CI, so the counts in the README cannot drift away from the deployment
they describe. The counts themselves are properties of files in this repository rather than
measurements of the world, which is why they can be asserted exactly.

**Growth tier.** `just up-growth`. Three docker networks that express the Purdue model for real,
which is reference-architecture fidelity item (b):

```yaml
networks:
    ot_net: { internal: true } # devices + broker-ot + area gateways
    dmz_net: { internal: true } # broker-ot + historian + twin-sync + otel-collector
    it_net: {} # analytics + agent + api + dashboard + postgres
```

`broker-ot` is on `ot_net` and `dmz_net`. `historian` is on `dmz_net` and `it_net`. No device
container is on `it_net`, and `ot_net` is `internal: true` so it has no default route out. The
crossing point is the broker bridge, and only the broker bridge. `TIER-2` proves it: a test
execs into a device container and tries a TCP connect to the analytics container and to
`1.1.1.1`, asserting both fail, then attempts a connect to `broker-ot` and asserts it succeeds.
Adapters: EMQX broker, Postgres, Delta on a local volume, OpenTelemetry collector.

**Enterprise tier.** `deploy/helm/twinflow` with a chart per subsystem and `values-enterprise.yaml`.
Kubernetes NetworkPolicies mirror the three docker networks so the Purdue statement holds at both
tiers. Adapters bind to Kafka, Delta on object storage or Databricks SQL or Snowflake, an external
Postgres, and a cloud IoT hub ingress. `TIER-3` runs `helm lint` plus `helm template` and validates
the rendered manifests with `kubeconform`; `TIER-4` runs the chart against a `kind` cluster in the
nightly job and asserts the API pod serves `/healthz` and the NetworkPolicy denies the OT-to-IT
path.

Adapter seam table, which is what A3 actually asks to be made explicit:

| Port                             | Garage               | Growth                   | Enterprise                                     | Shipped state                                                                                                        |
| -------------------------------- | -------------------- | ------------------------ | ---------------------------------------------- | -------------------------------------------------------------------------------------------------------------------- |
| `Network` (MQTT, Sparkplug)      | Mosquitto            | EMQX                     | EMQX at the OT edge, bridged into the log      | Mosquitto, EMQX, NanoMQ (E36 tier-1 gateway) implemented; `AzureIotHubIngress` and `AwsIotCoreIngress` ship as stubs |
| `EventBus` (analytics fan-out)   | MQTT over Mosquitto  | MQTT over EMQX           | Kafka                                          | `MqttEventBus` implemented; `KafkaEventBus` is the implemented enterprise example                                    |
| `TableStore`                     | DuckDB + local Delta | Postgres + local Delta   | Delta on ADLS/S3, Databricks SQL, Snowflake    | DuckDB, Delta, Postgres implemented; `DatabricksSqlTableStore` and `SnowflakeTableStore` ship as stubs               |
| `EventLog`                       | local NDJSON         | Postgres                 | Kafka + Delta                                  | local NDJSON, Postgres, and Kafka implemented                                                                        |
| `BlobStore` (CV frames, reports) | local filesystem     | local filesystem         | S3-compatible                                  | local and S3 implemented                                                                                             |
| `KeyValue` (idempotency, leases) | local file           | Postgres                 | Postgres                                       | `LocalFileKeyValue` and `PostgresKeyValue` implemented                                                               |
| `Secrets`                        | `.env` file          | docker secrets           | Kubernetes secrets or External Secrets         | all three implemented                                                                                                |
| `Identity`                       | single API key       | broker username/password | mTLS from the internal CA plus OIDC on the API | `ApiKeyIdentity` and `OidcIdentity` implemented; `MtlsIdentity` lands in Phase 5                                     |
| `Inference`                      | Ollama local         | Ollama or vLLM           | hosted API plus the E45 cost router            | `OllamaInference` and `HostedInference` implemented; `VllmInference` ships as a stub                                 |

Nine seams, nine `Protocol` bodies in 3.6, nine entries in `twinflow.kernel.__all__`, and nine
conformance classes. Kafka appears only on the `EventBus` and `EventLog` rows and never on
`Network`, which is D-08: a partitioned log has no retained message, no last will, and no wildcard
subscription, and the Sparkplug death certificate rides on the last will. `Identity` at garage is a
single API key rather than nothing, because `integrations.rest.auth: none` is permitted only with a
loopback bind (`TF-C212`) and an unauthenticated port is a shipped state a reader would rightly
distrust.

Every stub is a real class that raises `NotImplementedAdapter` with a docstring naming the
conformance suite it must pass. The suite is `twinflow.kernel.testing.adapter_conformance_suite`,
one parameterized pytest class per port, that any adapter can be pointed at:

```python
adapter_conformance_suite = (
    TestClockConformance, TestRngConformance, TestNetworkConformance,
    TestEventBusConformance, TestEventLogConformance, TestTableStoreConformance,
    TestBlobStoreConformance, TestKeyValueConformance, TestIdGenConformance,
    TestEnvConformance, TestMetricsSinkConformance, TestSecretsConformance,
    TestIdentityConformance, TestInferenceConformance,
)

@pytest.mark.parametrize("adapter", all_registered_table_stores())
class TestTableStoreConformance:
    async def test_write_then_query_roundtrip(self, adapter): ...
    async def test_append_preserves_order(self, adapter): ...
    async def test_schema_evolution_add_column(self, adapter): ...
    async def test_concurrent_append_no_loss(self, adapter): ...
    async def test_query_is_parameterised_not_interpolated(self, adapter): ...
    async def test_query_result_order_matches_order_by(self, adapter): ...
```

That suite is the seam made testable, and INV-K17 is true of all fourteen ports rather than of the
four that had bodies before. A reader who wants to plug in their own warehouse runs one command
against their adapter and knows whether it fits. Stubs are excluded from the parameterized run by a
marker and included in a separate test that asserts they raise the documented exception, so a stub
can never silently become a passing no-op. `test_every_port_has_a_conformance_class` compares the
suite tuple against the port list in `twinflow.kernel.__all__` and fails on either side being
longer, which is what stops a port added later from arriving without a suite.

### 5.12 Bring-your-own-facility (A2)

`facility.yaml` top-level blocks and their owning section:

| Block            | Owner                       | Contents                                                                                     |
| ---------------- | --------------------------- | -------------------------------------------------------------------------------------------- |
| `schema_version` | this section                | `"1.3"`                                                                                      |
| `facility`       | this section                | `id, name, timezone, geo, uom_system, site_type`                                             |
| `simulation`     | this section                | `seed, mode, tick_hz, horizon, warmup, speed, snapshot`                                      |
| `deployment`     | this section                | `tier, adapters{}, network{}`                                                                |
| `observability`  | this section                | `otel{}, log_level, metrics_sink`                                                            |
| `integrations`   | this section                | `rest{}, graphql{}, webhooks[]`                                                              |
| `calendar`       | twin section                | `shifts[], holidays[], operating_days`                                                       |
| `layout`         | twin section                | `zones[], docks[], stations[], aisles[], racks[], travel_graph`                              |
| `flows`          | twin section                | routing definitions per flow class                                                           |
| `resources`      | twin + HR sections          | `labor[], equipment[], automation{amr, palletizer, asrs, sortation}`                         |
| `sensors`        | IoT section                 | `catalog: <path>, instances[]`                                                               |
| `items`          | planning section            | `sku_classes[], sku_source`                                                                  |
| `partners`       | supplier/transport sections | `suppliers[], carriers[], customers[]`                                                       |
| `policies`       | multiple                    | `slotting, picking, replenishment, dock_scheduling, inventory, returns`                      |
| `metrics`        | this section, envelope only | `catalog: <path>` plus inline definitions; expressions belong to the AI-layer section (5.15) |
| `spec_limits`    | LSS section                 | `<metric_id>: {lsl, usl, target}` or a path to a separate file                               |
| `scenarios`      | this section                | named overlay paths available to `tf run --scenario`                                         |

Types for the blocks this section owns:

```yaml
schema_version: "1.3" # string, MAJOR.MINOR, must be a known version
facility:
    id: mid3pl-01 # slug, ^[a-z][a-z0-9-]{2,31}$
    name: "Mid-market 3PL building" # string, 1..120 chars
    timezone: America/Chicago # IANA zone, validated against zoneinfo
    geo: { lat: 41.88, lon: -87.63 } # optional, floats, needed by E42 and E40
    uom_system: metric # metric | us_customary, controls report rendering only
    site_type: distribution_center # distribution_center | micro_fulfillment | factory | crossdock
simulation:
    seed: 42 # int 0..2**64-1, required unless --seed given
    mode: simulation # simulation | production
    tick_hz: 1000000 # 1000 | 1000000 | 1000000000
    horizon: "30 d" # duration string, > 0, <= 100 y
    warmup: "1 d" # duration string, >= 0, < horizon
    speed: asap # asap | float in [0.01, 100000]
    snapshot: { every: "8 h", keep: 5 } # optional
deployment:
    tier: growth # garage | growth | enterprise
    adapters:
        network: emqx # must name a registered adapter for this port
        table_store: postgres
        event_log: postgres
        blob_store: local
        inference: ollama
    network:
        topology: purdue_three_zone # names a topology in deploy/topologies/
integrations:
    rest: { enabled: true, bind: "127.0.0.1:8080", auth: apikey }
    graphql: { enabled: true, max_depth: 12, max_complexity: 2000 }
    webhooks:
        - id: ops-slack
          url: "http://localhost:9001/hook" # http allowed only at garage tier
          subjects: ["twinflow.lss.finding"]
          filter: "severity >= high" # CEL-style expression, validated at load
          secret_ref: "env:WEBHOOK_SECRET_OPS"
          delivery: { max_attempts: 6, backoff: exponential, timeout: "5 s" }
```

Validation rules worth naming because they catch real mistakes: `warmup < horizon` (`TF-C041`);
`speed` finite requires `mode: simulation` (`TF-C042`, because pacing a production run is
meaningless); `deployment.adapters.*` must name an adapter registered by an installed package
(`TF-C120`, listing what is available); a webhook `url` with scheme `http` at growth or enterprise
tier is `TF-C210`; `secret_ref` must be `env:NAME`, `file:PATH`, or `k8s:NAME`, never a literal
(`TF-C211`, and a literal-looking value is reported as a secret leak, not a type error).

**Three worked profiles**, each a directory with the config, a smoke scenario, a golden KPI file,
and a README section:

| Profile                        | Shape                                                                                                                          | Devices | Purpose                                                                                                                |
| ------------------------------ | ------------------------------------------------------------------------------------------------------------------------------ | ------- | ---------------------------------------------------------------------------------------------------------------------- |
| `profiles/micro_fulfillment/`  | 1 dock, 3 stations, no automation, 1 shift, 1 SKU class                                                                        | 6       | proves the floor: a startup can model their unit in one screen of YAML. It is also the Phase 1 walking-skeleton target |
| `profiles/midmarket_3pl/`      | 8 docks, 24 stations, sortation plus 6 AMRs, 2 shifts, 2 customers, wholesale plus parcel                                      | ~120    | the everyday case, and the default for demos and the E1 replay recording                                               |
| `profiles/enterprise_network/` | 2 DCs plus 1 upstream factory plus a transport network, full automation, 3 shifts, cross-dock and e-commerce and returns flows | ~600    | proves the ceiling and is the E13 multi-site and A4 scaling target                                                     |

Gates: `A2-1` all three validate clean with `--strict-warnings`. `A2-2` all three complete a
one-simulated-day scenario inside the e2e budget. `A2-3` the golden KPI file matches.

`A2-4` is the mechanical proof that "same code, three companies" is true and not aspirational, and
it measures the claim instead of policing an identifier. An earlier draft made it a lint that
failed on any source line comparing `facility.id` or `facility.site_type` to a literal outside the
config package. That gate was both too strong and too weak. Too strong, because `site_type` is an
open enum whose members include `crossdock` and `factory`, and the cross-docking flow-versus-store
engine and the upstream factory are required capabilities that behave differently by construction.
Too weak, because `x = cfg.facility.site_type` on one line and `if x == "factory"` on the next
defeats it entirely.

The gate is structural instead. `SCN-F4` already runs all three profiles. `A2-4` collects
branch-level coverage for each of the three runs and asserts two things. First, that the set of
imported `twinflow.*` modules differs across the three profiles only within the capability modules
listed in `[tool.twinflow.capability_modules]`, each of which is enabled by a config key rather
than by a site-type test. Second, that within every module outside that list, the set of executed
branches is identical across the three profiles. A branch that fires for one profile and not
another, in a module that is not declared config-driven, is the exact defect the lint was reaching
for, and coverage data sees it whichever way the branch is spelled.
`test_a2_4_detects_a_planted_site_type_branch` adds a site-type comparison to a non-capability
module in a temporary working tree and asserts the gate fails, which is what stops A2-4 from
becoming a test that cannot fail (D-12).

`CONFIGURING.md` walks a reader from `tf facility init --template micro` through measuring their
own stations to a running twin, with `tf facility doctor` reporting what is still at default and
what the twin cannot yet represent about their building.

### 5.13 Integration surface (A6)

**REST**, `/api/v1`, OpenAPI 3.1, spec committed at `api/openapi.v1.json` and regenerated by
`just api-spec`.

| Route                             | Method            | Notes                                                                                                                                                                                               |
| --------------------------------- | ----------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `/api/v1/runs`                    | GET, POST         | list runs; POST starts a run from a profile plus scenario plus seed, returns 202 and a job                                                                                                          |
| `/api/v1/runs/{id}`               | GET, DELETE       | the `RunManifest`                                                                                                                                                                                   |
| `/api/v1/runs/{id}/events`        | GET               | cursor-paginated canonical event stream, filterable by subject and sim-time range                                                                                                                   |
| `/api/v1/runs/{id}/speed`         | POST              | C2 speed control                                                                                                                                                                                    |
| `/api/v1/stream`                  | GET (SSE)         | live envelope stream for the dashboard                                                                                                                                                              |
| `/api/v1/twin/state`              | GET               | current station states, WIP, utilization, bottleneck                                                                                                                                                |
| `/api/v1/twin/stations/{id}`      | GET               | per-station detail                                                                                                                                                                                  |
| `/api/v1/fleet/devices`           | GET               | registry with health scores                                                                                                                                                                         |
| `/api/v1/fleet/devices/{id}`      | GET               | device twin desired vs reported (E44)                                                                                                                                                               |
| `/api/v1/findings`                | GET               | filter by severity, subject, station, window; the findings stream                                                                                                                                   |
| `/api/v1/findings/{id}`           | GET, PATCH        | PATCH for shelve and acknowledge (alarm rationalization)                                                                                                                                            |
| `/api/v1/metrics/{metric_id}`     | GET               | a metric from the registry of 5.15, evaluated over a window once E26b supplies expressions; `404` for an unregistered id and `501` with a problem document naming E26b while the expression is null |
| `/api/v1/scenarios`               | GET               | available scenarios                                                                                                                                                                                 |
| `/api/v1/whatif`                  | POST              | run a config delta, returns 202 plus a job id                                                                                                                                                       |
| `/api/v1/jobs/{id}`               | GET               | job status and result reference                                                                                                                                                                     |
| `/api/v1/reports/capability`      | POST              | generate the capability report for a window, returns an artifact URL                                                                                                                                |
| `/api/v1/genealogy/lots/{id}`     | GET               | forward and backward trace                                                                                                                                                                          |
| `/api/v1/config`                  | GET, POST         | resolved config; POST proposes a change subject to the E5 autonomy tier                                                                                                                             |
| `/api/v1/webhooks`                | GET, POST, DELETE | subscriptions                                                                                                                                                                                       |
| `/healthz`, `/readyz`, `/version` | GET               | unversioned, outside `/api/v1`                                                                                                                                                                      |

Cross-cutting behavior:

- **Pagination** is cursor based. The cursor is an opaque base64 of
  `(twinflowsimts, twinflowproducerid, twinflowseq)`, the canonical total order of E4 and no other
  order. All three components are present because the sequence is dense only per producer (D-07),
  so a two-part cursor would skip or repeat items whenever two producers emitted at the same tick.
  Because the event log is append-only and read in that order, paging never skips or duplicates an
  item that existed when the cursor was created (INV-K16). Offset pagination is deliberately not
  offered.
- **Errors** are RFC 9457 problem documents with `type` pointing at
  `https://<pages>/errors/TF-A031`, and the `code` field carries the `TF-Axxx` code so a client can
  branch on it.
- **Idempotency** covers every POST, which accepts `Idempotency-Key`. Replaying a key within the retention
  window returns the original response with `Idempotency-Replayed: true`.
- **Conditional requests** put an `ETag` on every GET, and `If-None-Match` returns 304. The ETag is the
  content hash of the canonical response body, which makes it deterministic in simulation mode.
- **Auth** differs by tier. Garage uses a single API key from `secret_ref`. Growth uses per-client API keys
  with scopes. Enterprise uses OIDC bearer tokens with scopes mapped to the 6a15 RBAC roles.
  Scopes are per-route and listed in the OpenAPI security requirements: `runs:read`, `runs:write`,
  `findings:read`, `findings:write`, `whatif:run`, `config:read`, `config:propose`,
  `config:apply`, `webhooks:admin`. `config:apply` is never granted to the agent principal below
  autonomy tier L3, which is where E5's guardrail is actually enforced.
- **Rate limiting** is a token bucket per principal, answering `429` with `Retry-After`. The bucket refills on
  sim time in simulation mode, which keeps rate-limit tests deterministic.

**GraphQL** at `/graphql`, read-only in v1. It exists because findings, genealogy, and the supplier
DAG are graphs and REST forces clients into N+1 fetches over them. Strawberry, code-first, SDL
committed at `api/schema.graphql` with a diff gate. Depth limit 12, complexity limit 2000, both
configurable. Persisted-query allowlist available at enterprise tier. Mutations are deliberately
absent in v1 and the reason is written into the schema description: writes go through REST so that
idempotency keys, problem documents, and the audit event have one implementation.

**Webhooks**: subscriptions as configured above or created through the API. Delivery is
at-least-once with `event_id` as the natural idempotency key. Signature is
`X-Twinflow-Signature: t=<unix_seconds>,v1=<hex hmac-sha256 of "t.body">`, with a 300 second
tolerance window. The header shape follows Stripe's documented webhook signature scheme, so a
consumer that already verifies Stripe webhooks can reuse its verification code with the header name
changed. VAL-F10 grounds the primitive itself in RFC 4231 rather than in that scheme. Retries use exponential backoff with jitter drawn from `kernel.webhook.jitter`,
which makes retry timing deterministic in simulation and so testable. After `max_attempts`
the delivery lands in a dead-letter store readable at `/api/v1/webhooks/{id}/dead_letters`. Every
delivery try emits `twinflow.integration.webhook_delivery_attempted`.

The same service layer backs the MCP server (E2), the EPCIS export (E35), and the agent's tools
(component 7). Those three sections wrap `twinflow.api.services`, they do not call the HTTP surface
and they do not reimplement the queries. That is why the service layer is a separate module from
the router module, and `import-linter` has a contract asserting no router imports another router.

### 5.14 Monorepo tooling (C10)

Root `pyproject.toml`:

```toml
[tool.uv.workspace]
members = ["packages/*"]

[tool.uv]
required-version = ">=0.5"
default-groups = ["dev"]

[dependency-groups]
dev = ["pytest", "pytest-asyncio", "hypothesis", "pytest-cov", "ruff", "ty",
       "import-linter", "schemathesis", "griffe", "syrupy"]
```

One entry in that group needs a license note, because C4 names the tool and C11 owns the allowlist.
Hypothesis 6.165.2 is MPL-2.0, read from the Python Package Index on 2026-08-09. MPL-2.0 is
file-level copyleft that does not reach across a package boundary, and a development dependency is
not distributed with the product, so it is compatible with the Apache-2.0 plus commercial dual
license in this position and only in this position. The allowlist in CONTRIBUTING.md
needs an MPL-2.0 row scoped to `[dependency-groups] dev`, which is the dependency-hygiene section's
to write; until it has one, the allowlist refuses the property-testing library C4 requires. The
requirement is recorded here because this section declares the group.

`justfile` recipes, each a one-line delegation to `tools/` so local and CI run identical code:

| Recipe                                                       | Does                                                                                                  |
| ------------------------------------------------------------ | ----------------------------------------------------------------------------------------------------- |
| `just bootstrap`                                             | `uv sync --all-packages`, install git hooks, pull compose images                                      |
| `just fmt` / `just fmt-check`                                | ruff format, rustfmt                                                                                  |
| `just lint`                                                  | ruff check, `lint-det`, `lint-imports`, `check-profile-branches`, `check-measured-claims`, commitlint |
| `just lint-det`                                              | the nondeterminism lint, `--report` for the annotation inventory                                      |
| `just typecheck`                                             | `ty check` over the workspace, `cargo clippy -- -D warnings`                                          |
| `just test-unit`                                             | `pytest -m "not property and not e2e and not brick_isolated"`                                         |
| `just test-property`                                         | `pytest -m property` with a fixed Hypothesis profile and database                                     |
| `just test-contract`                                         | schema samples, consumer drift, adapter conformance, OpenAPI diff                                     |
| `just test-e2e`                                              | the seeded scenarios of section 7.4                                                                   |
| `just test-integration`                                      | the adapter conformance suite and SCN-F3 against real containers                                      |
| `just test-brick-isolation`                                  | `tf-brick-isolate` over every package                                                                 |
| `just measure-row-bytes`                                     | run a profile and write `x-twinflow-stored-bytes` plus its run id for every subject                   |
| `just det-check`                                             | DET-1 through DET-4 and DET-9                                                                         |
| `just schemas-gen` / `just schemas-check`                    | codegen and registry checks                                                                           |
| `just config-validate`                                       | validate all three profiles with `--strict-warnings`                                                  |
| `just run PROFILE SEED` / `just demo` / `just replay RUN_ID` | run, demo, replay                                                                                     |
| `just up-garage` / `just up-growth` / `just down`            | compose tiers                                                                                         |
| `just helm-lint` / `just kind-up`                            | enterprise tier checks                                                                                |
| `just bench`                                                 | the A4 load-test harness                                                                              |
| `just docs` / `just docs-serve`                              | mkdocs-material build                                                                                 |
| `just audit` / `just sbom`                                   | pip-audit, cargo-audit, license check, CycloneDX (C11)                                                |
| `just release VERSION`                                       | local dry run of the release pipeline                                                                 |
| `just ci`                                                    | everything a PR must pass, in the order CI runs it                                                    |

Any recipe a contributor needs that is not in `just --list` is a bug. The README quickstart uses
`just` and nothing else.

**CI matrix** (GitHub Actions):

| Job                     | Matrix                                                         | Trigger                                            | Budget        |
| ----------------------- | -------------------------------------------------------------- | -------------------------------------------------- | ------------- |
| `lint`                  | ubuntu, py3.13                                                 | every PR                                           | 3 min         |
| `typecheck`             | ubuntu, py3.13                                                 | every PR                                           | 3 min         |
| `unit`                  | {ubuntu, macos, windows} x {3.12, 3.13, 3.14}                  | every PR, path-filtered to `packages/**`           | 90 s per cell |
| `property`              | ubuntu, py3.13                                                 | every PR                                           | 5 min         |
| `contract`              | ubuntu, py3.13                                                 | PRs touching `schemas/**`, `packages/**`, `api/**` | 2 min         |
| `determinism`           | {ubuntu, macos} x py3.13, plus one `PYTHONHASHSEED=12345` cell | every PR                                           | 6 min         |
| `e2e`                   | ubuntu, py3.13                                                 | every PR                                           | 10 min        |
| `brick-isolation`       | ubuntu, py3.13                                                 | PRs touching `packages/**`                         | 4 min         |
| `rust`                  | {ubuntu, macos} x {stable, MSRV 1.85}                          | PRs touching `crates/**` or `schemas/**`           | 5 min         |
| `compose-garage`        | ubuntu                                                         | PRs touching `deploy/garage/**` or nightly         | 8 min         |
| `compose-growth-purdue` | ubuntu                                                         | PRs touching `deploy/growth/**` or nightly         | 10 min        |
| `integration`           | ubuntu                                                         | PRs touching adapter paths, plus nightly           | 15 min        |
| `helm`                  | ubuntu                                                         | PRs touching `deploy/helm/**`                      | 4 min         |
| `kind-enterprise`       | ubuntu                                                         | nightly                                            | 20 min        |
| `scaling`               | ubuntu, large runner                                           | nightly                                            | 30 min        |
| `audit`                 | ubuntu                                                         | daily and on release                               | 5 min         |

Stated wall-time budget: **15 minutes for the critical path on a PR** with jobs in parallel, 45
minutes for the full nightly. `tf-budget` reads `ci_budget.yaml` and fails a job that exceeds its
budget by more than 25 percent, which turns "CI got slow" into a failing test with an owner rather
than a slow drift nobody notices. Path filtering uses `dorny/paths-filter`-class detection with the
filter map in `.github/filters.yaml`; the filters are themselves tested by
`tools/test_ci_filters.py` against a table of changed-file sets and expected job sets, because a
broken path filter silently stops running tests, which is the worst kind of CI bug.

Concurrency group per PR with `cancel-in-progress: true`. Caches: uv cache keyed on `uv.lock`,
cargo cache keyed on `Cargo.lock`, Hypothesis example database keyed on the property test files so
found counterexamples persist across runs.

Required checks for merge: `lint`, `typecheck`, `unit` (all cells), `property`, `contract`,
`determinism`, `e2e`, `brick-isolation`.

The `integration` job is the container tier open question 1 asks about, and it now has a budget and
a trigger rather than an intention. It runs the adapter conformance suite against live Mosquitto,
EMQX, Postgres, and Delta, and it runs `SCN-F3`, which is a production-mode comparison and cannot
run anywhere else (7.4). It is not a required merge check, because a 15 minute container job on
every PR would break the 15 minute critical-path budget on its own; it gates the nightly and it
gates a release. `docs/limitations.md` states the consequence in the words open question 1 asks to
confirm: deterministic simulation covers business logic, and adapters are covered by container
integration tests.

### 5.15 The metric registry envelope (C5, E26b)

C5 names four configurations that must validate against a published schema at load with
line-numbered, suggestion-bearing errors: `facility.yaml`, the sensor catalog, the spec limits, and
the metrics layer. The first is owned here, the second by `twinflow-sensors` and the third by
`twinflow-lss` through the registration mechanism of 2.4. The fourth is owned here, and it is owned
here for a sequencing reason rather than a topical one: stage 6 of the config pipeline resolves
`spec_limits` keys into metric ids (`TF-C103`) from Phase 0, so the identifier space has to exist
from Phase 0 even though the expressions that compute the metrics are an E26b deliverable in the
AI-layer section.

The split is envelope here, semantics there. This section owns the file, its JSON Schema,
the identifier grammar, the registry, and the validation rules. The AI-layer section owns the
expression language, the evaluator, and the governance workflow around changing a definition.

File: `metrics.yaml`, named by `metrics.catalog` in `facility.yaml`, validated against
`schemas/config/metrics/v1.0.json`.

```yaml
schema_version: "1.0"
metrics:
    - id: twin.throughput.units_per_hour
      title: "Units per hour"
      unit: 1/h # x-twinflow-unit, resolved by pint
      grain: [facility, station, shift] # the dimensions it may be sliced by
      direction: higher_is_better # higher_is_better | lower_is_better | target_is_best
      precision: 2 # x-twinflow-precision, decimal places when serialized
      owner: twinflow-twin # the package that produces the inputs
      since: "0.1.0"
      expression: null # owned by the AI-layer section (E26b)
      status: active # active | deprecated
```

```python
class MetricDefinition(BaseModel):
    id: MetricId                       # grammar below
    title: str                         # 1..80 chars
    unit: str                          # pint-parseable, or "1" for dimensionless
    grain: list[str]                   # sorted at load, D-03
    direction: Literal["higher_is_better", "lower_is_better", "target_is_best"]
    precision: int                     # 0..9
    owner: str                         # a distribution name
    since: str                         # release that introduced it
    expression: str | None             # opaque here; parsed by the AI layer
    status: Literal["active", "deprecated"]
    deprecated_in: str | None

class MetricRegistry(BaseModel):
    schema_version: str
    metrics: list[MetricDefinition]    # ordered by id, checked at load
```

Identifier grammar: `<domain>.<area>.<name>`, lowercase, snake_case within each part, matching
`^[a-z][a-z0-9_]*(\.[a-z][a-z0-9_]*){2}$`. The domain part draws from the registered event domains
of 4.3, so a metric's identifier says which subsystem's events it is computed from. A metric id is
never reused for a different quantity; a redefinition takes a new id and deprecates its predecessor,
which is what makes a `spec_limits` entry recorded in a run last year still mean what it meant.

Validation rules, all producing the line-numbered rendering of 5.6:

| Code      | Condition                                                                       |
| --------- | ------------------------------------------------------------------------------- |
| `TF-C103` | a `spec_limits` key names a metric id that is not in the registry               |
| `TF-C150` | two definitions share an id                                                     |
| `TF-C151` | `unit` does not parse under pint                                                |
| `TF-C152` | `expression` is present but no installed package registers a metric evaluator   |
| `TF-C153` | `id` does not match the grammar, with the nearest registered id as a suggestion |
| `TF-C154` | `grain` names a dimension no installed package declares                         |
| `TF-C155` | a metric with `status: deprecated` and no `deprecated_in`                       |

`TF-C152` is the one that makes the Phase 0 and Phase 6 split honest. From Phase 0 the registry
loads and validates with `expression: null` on every entry, `TF-C103` works, and
`/api/v1/metrics/{metric_id}` returns `501` with a problem document naming E26b. When the AI layer
lands, its evaluator registers through the `twinflow.config.references` group of 5.6, expressions
become resolvable, and the same route starts serving values. Nothing about the file changes shape
in between, which is the property that lets `spec_limits` be authored in Phase 2 against ids that
compute in Phase 6.

The registry is the reference domain `metrics` for the purposes of 5.6, so `CFG-2` covers its error
codes from Phase 0 and `CFG-4` covers the domain's ownership.

Gates: `METRIC-1` asserts every metric id referenced anywhere in the workspace, in `spec_limits`,
in a dashboard tile definition, in an eval case, or in a golden KPI file, resolves against the
registry, so a renamed metric fails at CI rather than at a demo. `METRIC-2` asserts the registry is
append-only within a facility schema major: an id may gain `status: deprecated` and a
`deprecated_in`, and may be removed only at a MAJOR bump with an upcaster that maps it to its
replacement, which is the same rule 5.5 applies to event schemas and for the same reason.
`test_metric_id_grammar_table` is parametrised over accepting and rejecting cases, and
`test_spec_limits_dangling_metric_id_reports_nearest_candidate` pins the suggestion behavior C5
asks for.

---

## 6. Configuration

Every key this section reads, its type, and its validation rule. Keys owned by other sections are
listed in the block table of 5.12 and validated by their registered schemas.

| Key                                             | Type                  | Default                            | Validation                                                                                                      |
| ----------------------------------------------- | --------------------- | ---------------------------------- | --------------------------------------------------------------------------------------------------------------- |
| `schema_version`                                | string `MAJOR.MINOR`  | required                           | must be a known facility schema version; unknown gives `TF-C002` with the upgrade command in the suggestion     |
| `facility.id`                                   | slug                  | required                           | `^[a-z][a-z0-9-]{2,31}$`, unique across a multi-site config                                                     |
| `facility.name`                                 | string                | required                           | 1..120 chars                                                                                                    |
| `facility.timezone`                             | IANA zone             | required                           | resolvable by `zoneinfo`, `TF-C021`                                                                             |
| `facility.geo.lat` / `.lon`                     | float                 | null                               | -90..90, -180..180                                                                                              |
| `facility.uom_system`                           | enum                  | `metric`                           | `metric` or `us_customary`                                                                                      |
| `facility.site_type`                            | enum                  | `distribution_center`              | open enum, `x-twinflow-open-enum: true`                                                                         |
| `simulation.seed`                               | uint64                | required unless `--seed`           | 0..2^64-1, `TF-D001` if absent                                                                                  |
| `simulation.mode`                               | enum                  | `simulation`                       | `simulation` or `production`                                                                                    |
| `simulation.tick_hz`                            | enum int              | `1000000`                          | one of 1e3, 1e6, 1e9                                                                                            |
| `simulation.horizon`                            | duration string       | required                           | > 0, <= 100 y, `TF-C031`                                                                                        |
| `simulation.warmup`                             | duration string       | `0 s`                              | >= 0 and < horizon, `TF-C041`                                                                                   |
| `simulation.speed`                              | `asap` or float       | `asap`                             | float in [0.01, 100000]; finite requires `mode: simulation` (`TF-C042`); `x-twinflow-not-in-hash` (M6)          |
| `simulation.snapshot.every`                     | duration              | null                               | > 0 if present                                                                                                  |
| `simulation.snapshot.keep`                      | int                   | 3                                  | >= 1                                                                                                            |
| `simulation.rng_streams_strict`                 | bool                  | true                               | when true, an unregistered stream id raises rather than warns                                                   |
| `strict_sections`                               | bool                  | false at garage, true above        | when true, a block or reference domain with no installed owner is an error rather than a warning (2.4, 5.6)     |
| `metrics.catalog`                               | path                  | `metrics.yaml`                     | file exists and validates against the metric registry schema (5.15)                                             |
| `metrics.inline[]`                              | list                  | empty                              | inline `MetricDefinition` entries merged after the catalog; a duplicate id is `TF-C150`                         |
| `deployment.tier`                               | enum                  | `garage`                           | `garage`, `growth`, `enterprise`                                                                                |
| `deployment.adapters.network`                   | string                | tier default                       | must be a registered `Network` adapter, `TF-C120` lists available                                               |
| `deployment.adapters.event_bus`                 | string                | tier default                       | registered `EventBus` adapter                                                                                   |
| `deployment.adapters.table_store`               | string                | tier default                       | registered `TableStore` adapter                                                                                 |
| `deployment.adapters.event_log`                 | string                | tier default                       | registered `EventLog` adapter                                                                                   |
| `deployment.adapters.blob_store`                | string                | tier default                       | registered `BlobStore` adapter                                                                                  |
| `deployment.adapters.key_value`                 | string                | tier default                       | registered `KeyValue` adapter                                                                                   |
| `deployment.adapters.secrets`                   | string                | tier default                       | registered `Secrets` adapter                                                                                    |
| `deployment.adapters.identity`                  | string                | tier default                       | registered `Identity` adapter                                                                                   |
| `deployment.adapters.inference`                 | string                | `ollama`                           | registered `Inference` adapter                                                                                  |
| `deployment.network.topology`                   | string                | tier default                       | names a file in `deploy/topologies/`, `TF-C121`                                                                 |
| `deployment.faults`                             | path or inline        | null                               | validates against the `FaultSchedule` schema                                                                    |
| `observability.otel.enabled`                    | bool                  | false at garage, true above        |                                                                                                                 |
| `observability.otel.endpoint`                   | url                   | `http://otel-collector:4317`       | required when enabled                                                                                           |
| `observability.log_level`                       | enum                  | `info`                             | standard levels                                                                                                 |
| `observability.metrics_sink`                    | enum                  | `recording` in sim, `otlp` in prod |                                                                                                                 |
| `integrations.rest.enabled`                     | bool                  | true                               |                                                                                                                 |
| `integrations.rest.bind`                        | host:port             | `127.0.0.1:8080`                   | non-loopback bind at garage tier warns `TF-C320`                                                                |
| `integrations.rest.auth`                        | enum                  | `apikey`                           | `none` allowed only at garage tier with loopback bind (`TF-C212`)                                               |
| `integrations.graphql.enabled`                  | bool                  | true                               |                                                                                                                 |
| `integrations.graphql.max_depth`                | int                   | 12                                 | 1..50                                                                                                           |
| `integrations.graphql.max_complexity`           | int                   | 2000                               | 1..1e6                                                                                                          |
| `integrations.webhooks[].id`                    | slug                  | required                           | unique                                                                                                          |
| `integrations.webhooks[].url`                   | url                   | required                           | `http` only at garage tier (`TF-C210`)                                                                          |
| `integrations.webhooks[].subjects`              | list of subject globs | required                           | each must match a registered subject (`TF-C122`)                                                                |
| `integrations.webhooks[].filter`                | expression            | null                               | parses as a CEL-style predicate over the payload; unparseable is `TF-C013` with the column of the parse failure |
| `integrations.webhooks[].secret_ref`            | reference             | required                           | `env:`, `file:`, or `k8s:` prefix; a literal is `TF-C211`                                                       |
| `integrations.webhooks[].delivery.max_attempts` | int                   | 6                                  | 1..20                                                                                                           |
| `integrations.webhooks[].delivery.backoff`      | enum                  | `exponential`                      | `fixed`, `linear`, `exponential`                                                                                |
| `integrations.webhooks[].delivery.timeout`      | duration              | `5 s`                              | 100 ms .. 60 s                                                                                                  |
| `scenarios.<name>`                              | path                  | none                               | file exists and validates as an overlay                                                                         |

Environment variables, the only ones read, and all read through the `Env` port inside
`twinflow-config`: `TWINFLOW_CONFIG`, `TWINFLOW_SEED`, `TWINFLOW_PROFILE`, `TWINFLOW_LOG_LEVEL`,
`TWINFLOW_API_KEY`, `WEBHOOK_SECRET_*`, `ANTHROPIC_API_KEY` / `OPENAI_API_KEY` /
`GOOGLE_API_KEY` (optional, per the constraint that the repo runs fully local with an optional env
var for a hosted LLM), `NPY_DISABLE_CPU_FEATURES`, `PYTHONHASHSEED`. Any other `TWINFLOW_*`
variable present in the environment is a startup warning `TF-C321 unknown TWINFLOW_ variable`, with
a suggestion, because an env var name typo that silently does nothing is undiagnosable from inside
the running system.

---

## 7. Testing

Tiers and budgets are the C4 contract as it applies here: unit under 90 s per matrix cell, property
under 5 min, contract under 2 min, e2e under 10 min, determinism under 6 min.

### 7.1 Unit tests

Named per behavior, not per method. A non-exhaustive list of the ones that must exist because they
pin a decision:

- `test_sim_instant_is_integer_ticks_and_rejects_float`
- `test_duration_string_parsing_table` (a table of 40 duration strings and their tick values,
  including `"1.5 h"`, `"90 min"`, `"1 d 6 h"`, and rejections like `"soon"`, `"-5 s"`, `"5"`)
- `test_clock_now_never_decreases_across_1000_scheduled_wakeups`
- `test_paced_clock_emits_identical_log_at_speed_1_and_asap`
- `test_rng_child_stream_is_addressed_by_name_not_creation_order`
- `test_rng_unregistered_stream_raises_when_strict`
- `test_rng_known_answer_vectors` (committed golden draws for 12 named streams)
- `test_deterministic_id_gen_is_content_addressed_and_sorts_in_emission_order`
- `test_in_memory_network_delivers_exactly_once_with_no_faults`
- `test_in_memory_network_partition_blocks_ot_to_it_and_heals_in_order`
- `test_in_memory_network_qos1_duplicate_is_deduped_by_message_id`
- `test_fault_randomness_does_not_perturb_process_streams`
- `test_sim_event_loop_rejects_add_reader_and_run_in_executor`
- `test_canonical_encode_matches_rfc8785_vectors`
- `test_config_error_reports_line_and_column_for_every_error_class` (parametrised over every
  `TF-C` code, asserting each has a test that produces it; a code without a test fails
  `test_every_error_code_is_reachable`)
- `test_config_unknown_key_suggests_nearest_valid_key`
- `test_config_hash_ignores_comments_and_key_order`
- `test_config_hash_is_unchanged_by_speed` and `test_run_started_payload_has_no_speed_field` (M6)
- `test_run_started_carries_no_wall_clock_or_platform_field` (M4)
- `test_every_extension_attribute_name_is_at_most_20_chars` (3.4)
- `test_extension_attribute_types_match_cloudevents_type_system` (3.4)
- `test_numeric_layer_draws_one_value_at_a_time` (R8)
- `test_metric_id_grammar_table` and
  `test_spec_limits_dangling_metric_id_reports_nearest_candidate` (5.15)
- `test_every_port_has_a_conformance_class` (5.11)
- `test_a2_4_detects_a_planted_site_type_branch` (5.12)
- `test_cross_platform_tolerance_is_not_edited_by_ci` (5.4)
- `test_speed_strategy_lower_bound_is_clamped` (5.3)
- `test_call_later_deadline_is_computed_in_ticks` (T1a)
- `test_resources_match_simpy_semantics` (5.2)
- `test_runtime_log_is_the_storage_event_log` (2.2)
- `test_compat_checker_table` (parametrised over the full table in 5.5, both directions)
- `test_upcaster_exists_for_every_removed_field`
- `test_semver_policy_rejects_public_symbol_removal_without_breaking_footer`
- `test_webhook_signature_matches_rfc4231_derived_vectors`
- `test_problem_document_shape_matches_rfc9457`
- `test_cursor_pagination_is_stable_under_concurrent_append`

### 7.2 Property-based invariants (Hypothesis)

Each is a named test in `tests/property/`, run under the `ci` Hypothesis profile with a persistent
example database.

| Invariant                             | Statement                                                                                                                                                                                                                              | Generator                                                                                                      |
| ------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------- |
| INV-K1 monotone clock                 | for any interleaving of scheduled sleeps and immediate callbacks, `clock.now()` observed in emission order is non-decreasing                                                                                                           | random schedules of 1..200 tasks with durations 0..1e9 ticks                                                   |
| INV-K2 tick arithmetic                | `t + d1 + d2 == t + (d1 + d2)` and durations parsed from strings round-trip to the same tick value                                                                                                                                     | random instants and durations                                                                                  |
| INV-K3 stream independence            | draws from stream A are unchanged by any number of draws from stream B, in any interleaving                                                                                                                                            | random stream name pairs and interleavings                                                                     |
| INV-K4 name addressing                | the first 100 draws of stream `X` are identical regardless of which other streams exist or their creation order                                                                                                                        | random sets of stream names                                                                                    |
| INV-K5 canonical stability            | `encode(x)` is invariant to dict key insertion order and to numerically equal float representations, and `decode(encode(x)) == x`                                                                                                      | recursive JSON-shaped structures                                                                               |
| INV-K6 envelope validity              | every event produced by any registered producer validates against its schema and the envelope                                                                                                                                          | model-based generation from schemas                                                                            |
| INV-K7 lossless delivery              | with an empty fault schedule, the multiset of messages received by each subscriber equals the multiset published matching its pattern, and per-topic order is preserved                                                                | random topic trees and publish sequences                                                                       |
| INV-K8 fault bounds                   | with `PARTITION` active, zero messages cross; with `DROP p=0`, none are dropped; after heal, buffered messages deliver in publish order                                                                                                | random fault schedules                                                                                         |
| INV-K9 speed invariance               | the canonical log is identical for `speed=asap` and any finite speed                                                                                                                                                                   | `SCN-F0`, speeds log-uniform on the clamped range of 5.3, at most 25 examples                                  |
| INV-K10 merge algebra                 | overlay merge is associative over disjoint overlays and idempotent for a repeated identical overlay                                                                                                                                    | random config trees and overlays                                                                               |
| INV-K11 hash sensitivity              | any single leaf value change changes `ConfigHash`; comment, whitespace, and key-order changes do not                                                                                                                                   | mutation of a valid config                                                                                     |
| INV-K12 compat metamorphic            | schemas mutated by the additive-only mutator always pass `compat_check`; schemas mutated by the breaking mutator always fail                                                                                                           | schema generator plus two mutator families                                                                     |
| INV-K13 upcast totality               | every archived event version upcasts to an event valid against the current schema                                                                                                                                                      | archived logs plus generated historical events                                                                 |
| INV-K14 migration idempotence         | applying migrations to version N twice equals applying once, and `check()` passes                                                                                                                                                      | random fixture stores at each version                                                                          |
| INV-K15 webhook delivery closure      | under any fault schedule and any `max_attempts` in 1..20, every matching event is either delivered under a distinct `event_id` or present in the dead-letter store, never both and never neither                                       | random fault schedules, subscriptions, and delivery settings drawn from the configuration surface of section 6 |
| INV-K16 pagination stability          | paging a cursor created at time T never skips or duplicates an item that existed at T, regardless of appends during paging                                                                                                             | random append interleavings                                                                                    |
| INV-K17 port substitutability         | every registered adapter for a port passes the same conformance suite with the same assertions                                                                                                                                         | parametrised over adapters                                                                                     |
| INV-K18 sequence density per producer | for each `(twinflowrunid, twinflowproducerid)` pair in a completed run, `twinflowseq` is exactly `0..n-1` with no gaps or repeats, and the merged log is a strict total order under `(twinflowsimts, twinflowproducerid, twinflowseq)` | any scenario, run with one, two, and four producer processes                                                   |
| INV-K19 no wall-clock leak            | the same scenario run with the process wall clock frozen at two different instants produces identical logs                                                                                                                             | `FrozenWallClock` at random epochs                                                                             |
| INV-K20 unit round-trip               | converting a `Quantity` to base units and back is lossless to the declared precision                                                                                                                                                   | random quantities across all declared units                                                                    |
| INV-K21 query order independence      | a `TableStore.query` result is identical across thread counts and across repeated runs for any `order_by` that is a total order over the result                                                                                        | random tables, queries, and thread counts 1..8                                                                 |
| INV-K22 resource waiter ordering      | requests granted by `Resource`, `PriorityResource`, and `PreemptiveResource` follow FIFO within a priority class, ties broken by request sequence number                                                                               | random request and release scripts, compared against SimPy                                                     |
| INV-K23 metric id closure             | every metric id referenced by a resolved config, a golden KPI file, or an eval case resolves against the registry of 5.15, and no id resolves to two definitions                                                                       | random registries and reference sets                                                                           |

### 7.3 Determinism gates

| Gate   | What it does                                                                                                                                                                                                                                                 | Failure means                                                                                                                                     |
| ------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ | ------------------------------------------------------------------------------------------------------------------------------------------------- |
| DET-1  | run `SCN-F1` twice in separate processes on the same runner, each with its own `--out`, compare `event_log_hash` byte for byte                                                                                                                               | a nondeterminism the lint missed                                                                                                                  |
| DET-2  | compare `SCN-F1` logs produced on ubuntu and macos runners in two stages: first `rng_draw_counts_sha256`, then, only if those match, integer and quantised fields byte for byte and continuous fields against the measured `cross_platform_tolerance` of 5.4 | stage one, stream desynchronisation; stage two, a platform-dependent numeric path. The two are named separately because they need different fixes |
| DET-3  | run `SCN-F1` at `PYTHONHASHSEED=0` and `PYTHONHASHSEED=12345`, compare logs                                                                                                                                                                                  | a set or hash iteration order leak                                                                                                                |
| DET-4  | run `SCN-F0` at `speed=asap` and `speed=50`, each with its own `--out`, compare logs                                                                                                                                                                         | wall clock leaking into logic                                                                                                                     |
| DET-5  | run `SCN-F2` (faults active) twice at the same seed, compare logs                                                                                                                                                                                            | fault injection is not reproducible                                                                                                               |
| DET-6  | snapshot at mid-horizon, resume, compare the resumed suffix to the uninterrupted log                                                                                                                                                                         | snapshot state is incomplete. Written in Phase 0, `xfail(strict=True)` until E4 implements subsystem snapshots                                    |
| DET-7  | per third-party stochastic library, two calls inside `deterministic_context` produce identical output                                                                                                                                                        | that library version broke determinism; the test names it                                                                                         |
| DET-8  | the release determinism manifest for version N reproduces on the tagged commit                                                                                                                                                                               | a release cannot be reproduced from its tag                                                                                                       |
| DET-9  | `test_rng_stream_length_is_identical_across_platforms`, reported on its own rather than folded into DET-2                                                                                                                                                    | the RNG stream desynchronised, which is a different defect from numeric drift and takes a different fix                                           |
| RUST-1 | the Rust `crates/twinflow-rng` crate and the Python `twinflow-rng` package produce byte-identical first-1000 draws for each of the twelve named streams of VAL-F6a, at the same `base_seed` and `replication_index`                                          | the cross-language RNG contract of D-06 is broken and every recorded fleet run is suspect. Runs in the `rust` job                                 |

### 7.4 Seeded end-to-end scenarios

| Id     | Profile           | Seed     | Description                                                                                                                                                        | Asserts                                                                                                                                                                                                                     |
| ------ | ----------------- | -------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------ | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| SCN-F0 | micro_fulfillment | 42       | 60 simulated seconds, no faults, one arrival and one station cycle                                                                                                 | the paced-clock properties only: DET-4 and INV-K9. It exists because a paced run costs wall time in proportion to its simulated span, and the arithmetic of 5.3 shows a 1 sim day scenario cannot fit the job budget (D-13) |
| SCN-F1 | micro_fulfillment | 42       | 1 sim day, no faults                                                                                                                                               | manifest completeness, `run_started`/`run_finished` bracket the log, DET-1, DET-2, DET-3, DET-9                                                                                                                             |
| SCN-F2 | midmarket_3pl     | 1337     | 1 sim day with a 90 s broker outage at t=4 h                                                                                                                       | zero message loss with device buffering, fault events present, DET-5                                                                                                                                                        |
| SCN-F3 | midmarket_3pl     | 7        | same scenario in production mode against two real adapter stacks: garage compose (Mosquitto, DuckDB, local Delta) and growth compose (EMQX, Postgres, local Delta) | the normalized business event stream is identical across the two stacks, which is the mechanical proof of "tiers by configuration, never by rewrite" (D-12). Runs in the `integration` job because it needs containers      |
| SCN-F4 | all three         | 42       | 1 sim day each                                                                                                                                                     | A2-1 through A2-3                                                                                                                                                                                                           |
| SCN-F5 | archived          | recorded | replay each archived golden log through upcasters and recompute KPIs                                                                                               | MIG-2                                                                                                                                                                                                                       |
| SCN-F6 | midmarket_3pl     | 42       | boot the API against a completed run, run schemathesis over the OpenAPI spec, exercise webhook delivery under a `SLOW_CONSUMER` fault                              | API-1..API-4                                                                                                                                                                                                                |
| SCN-F7 | midmarket_3pl     | 99       | `tf run --dry-run` on all three profiles                                                                                                                           | dry run constructs every subsystem and exits with the resource inventory, without advancing the clock                                                                                                                       |

SCN-F3's normalization is a named function rather than a description, because a comparison that
strips whatever happens to differ proves nothing. `twinflow.kernel.testing.normalise_for_tier_diff`
does exactly four things and is itself unit tested: it drops the envelope's `id` and `time`, which
are UUIDv7 and wall time in production mode; it drops `twinflowrunid`, which differs because the
two stacks resolve different `deployment.adapters` values and so different `config_hash`
values; it drops the `twinflow.kernel.*` and `twinflow.integration.*` subjects, which describe the
run and the transport rather than the business; and it re-sorts the remainder under the canonical
total order of E4. Every payload field survives. `test_normalise_for_tier_diff_drops_only_the_four`
asserts the field set it removes against a literal list, so a future failure cannot be silenced by
widening the normalizer, which is the failure mode that makes tier-portability proofs worthless.

### 7.5 Validation gates against published references

These are the VAL-GATEs for foundations. There is no published reference for "is this simulation
deterministic", so the gates here validate the standards-bearing components rather than inventing
authority. Each names its source and its tolerance.

| Gate    | Reference (published, citable)                                                                                                                             | What is asserted                                                                                                                                                                                                                                                                                                                                                          | Tolerance                                   |
| ------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------- |
| VAL-F1  | JSON Schema Test Suite, draft 2020-12 (json-schema-org/JSON-Schema-Test-Suite)                                                                             | our validator configuration passes every case for the keywords the registry uses, and correctly rejects the negative cases                                                                                                                                                                                                                                                | exact, 100 percent of the filtered case set |
| VAL-F2  | Semantic Versioning 2.0.0 specification, including its precedence examples                                                                                 | the version comparator orders the specification's own example list identically, and the bump calculator matches a table derived from the spec text                                                                                                                                                                                                                        | exact                                       |
| VAL-F3  | RFC 9457 Problem Details for HTTP APIs; RFC 9110 conditional requests; RFC 8288 Link header                                                                | error bodies, ETag/If-None-Match handling, and Link pagination headers conform                                                                                                                                                                                                                                                                                            | exact field and header shape                |
| VAL-F4  | OpenAPI Specification 3.1.0                                                                                                                                | `api/openapi.v1.json` validates under `openapi-spec-validator`, and every route has a documented 4xx and a security requirement                                                                                                                                                                                                                                           | exact                                       |
| VAL-F5  | PEP 440 version identifiers, PEP 621 project metadata, PEP 420 namespace packages                                                                          | every built distribution passes `twine check` and `validate-pyproject`, and no package ships a `twinflow/__init__.py`                                                                                                                                                                                                                                                     | exact                                       |
| VAL-F6a | NEP 19, NumPy Random Number Generator Policy, which names `.bytes()`, `integers()`, and `random()` as the methods that MUST guarantee stream compatibility | committed known-answer vectors for the 12 named streams, taken through those three methods only, reproduce exactly. Falsified by any vector changing on a numpy upgrade inside the pinned range                                                                                                                                                                           | exact bit equality                          |
| VAL-F6b | The twinflow distribution layer's own committed vectors, generated from VAL-F6a's draws                                                                    | `twinflow.kernel.numeric`'s families reproduce their committed vectors from the same raw draws. This gate is twinflow-internal by construction and says so: NEP 19 is the external reference underneath it, and the layer exists because NEP 19 covers nothing above those three methods                                                                                  | exact bit equality                          |
| VAL-F7a | NIST Special Publication 811, Appendix B, the factors printed in boldface, which the source defines as exact                                               | pint reproduces each exact definitional factor, for example 1 in = 25.4 mm and 1 lb = 0.45359237 kg                                                                                                                                                                                                                                                                       | 4 units in the last place of float64        |
| VAL-F7b | NIST Special Publication 811, Appendix B, the rounded factors                                                                                              | pint reproduces each rounded factor across mass, length, velocity, pressure, energy, power, and temperature                                                                                                                                                                                                                                                               | relative 5e-7, derived below                |
| VAL-F8  | RFC 8785 JSON Canonicalization Scheme, whose Appendix B holds IEEE 754 sample values and their JSON serialization                                          | `canonical_encode` reproduces every Appendix B sample byte for byte, including the number-serialization edge cases of section 3.2.2.3                                                                                                                                                                                                                                     | exact bytes                                 |
| VAL-F9a | RFC 7693, Appendix A (BLAKE2b-512 trace), Appendix B (BLAKE2s-256 trace), and the Appendix E self-test module                                              | the BLAKE2b primitive reproduces the Appendix A digest and passes the Appendix E self-test, which covers digest lengths 20, 32, 48, and 64 bytes over inputs of 0, 3, 128, 129, 255, and 1024 bytes, keyed and unkeyed                                                                                                                                                    | exact bytes                                 |
| VAL-F9b | The BLAKE2 reference implementation in the BLAKE2/BLAKE2 repository, `ref/blake2b-ref.c`                                                                   | twinflow's personalised and shortened digests reproduce the reference implementation's output at the same `outlen` and `personal` parameters                                                                                                                                                                                                                              | exact bytes                                 |
| VAL-F10 | RFC 4231 HMAC-SHA test vectors                                                                                                                             | the webhook signature primitive reproduces the RFC vectors                                                                                                                                                                                                                                                                                                                | exact                                       |
| VAL-F11 | Conventional Commits 1.0.0 specification examples                                                                                                          | the commit parser classifies every example in the specification correctly, including the `!` and footer forms                                                                                                                                                                                                                                                             | exact                                       |
| VAL-F12 | CloudEvents 1.0.2 specification, its JSON Event Format, and the Partitioning extension                                                                     | every envelope validates against the CloudEvents JSON format schema; every extension attribute name is lower-case alphanumeric and at most 20 characters; every attribute value matches its declared CloudEvents type, which is the assertion that rules out `Integer` for the two counters of 3.4; a round trip through the binary HTTP binding preserves all attributes | exact                                       |
| VAL-F13 | W3C Trace Context Recommendation, and the CloudEvents Distributed Tracing extension that references it                                                     | `traceparent` values we emit parse under the specification's grammar and survive a round trip through the OTel SDK                                                                                                                                                                                                                                                        | exact                                       |
| VAL-F14 | IANA Time Zone Database (tzdata), via `zoneinfo`                                                                                                           | shift calendars spanning a DST transition produce the correct wall-clock shift boundaries for three named zones, including a spring-forward and a fall-back case                                                                                                                                                                                                          | exact to the minute                         |
| VAL-F15 | RFC 9562, Universally Unique IDentifiers, section 5.7                                                                                                      | `Uuid7IdGen` output carries version 7 and the variant bits in the positions the section requires, and its timestamp field is non-decreasing within a process                                                                                                                                                                                                              | exact bit fields                            |

Three of these tolerances are derived rather than chosen, and the derivations are written out
because D-11 rule 2 forbids a tolerance tighter than the precision of the value it checks.

VAL-F7b's 5e-7. NIST SP 811 Appendix B states how its factors are printed: "The factors given in
Secs. B.8 and B.9 are written as a number equal to or greater than 1 and less than 10, with 6 or
fewer decimal places", and "A factor in boldface is exact. All other factors have been rounded to
the significant digits given in accordance with accepted practice." A mantissa in the interval
[1, 10) carried to six decimal places is at most seven significant digits, so the half-unit in the
last printed place is 5e-7 absolute on the mantissa, which is 5e-7 relative at the worst case of a
mantissa near 1. An earlier draft asserted 1e-12 relative against the same table, which is five
orders of magnitude tighter than the published value and would have failed on every non-exact
entry. VAL-F7b is falsified by any entry whose deviation exceeds 5e-7 relative; VAL-F7a is
falsified by any exact factor deviating by more than 4 units in the last place of float64.

VAL-F9's split. RFC 7693 says of itself that "due to space constraints, this document does not
contain a full set of test vectors for BLAKE2", and its Appendix E self-test covers BLAKE2b at
digest lengths 20, 32, 48, and 64 bytes. `content_hash` is BLAKE2b-256, so it sits inside that set
and VAL-F9a covers it. Two twinflow digests do not: the 16-byte personalised name hash of R2 and
the 8-byte `stable_hash64`. Neither is a truncation of a longer digest, because RFC 7693's own
initialization mixes the digest length into the state, `h[0] := h[0] ^ 0x01010000 ^ (kk << 8) ^ nn`,
and personalisation is out of the RFC's scope entirely: "[BLAKE2] defines additional variants of
BLAKE2 with features such as salting, personalized hashes, and tree hashing. These OPTIONAL
features use fields in the parameter block that are not defined in this document." The external
reference for those two is the BLAKE2 reference implementation rather than the RFC, which
is what VAL-F9b names. Open question 13 records the residue: no published vector set covers
BLAKE2b at an 8-byte digest with a personalisation string, so VAL-F9b compares against an
implementation rather than against a published table, and that is a weaker footing than the rest of
this table stands on.

VAL-F6b's honesty note. D-11 rule 1 forbids a gate that cites this repository as its own reference.
VAL-F6b compares twinflow's distribution layer against twinflow's own committed vectors, so it is
recorded as a regression gate and never as external validation. It stands only on VAL-F6a beneath
it, which is grounded in NEP 19: NumPy guarantees the raw draws, and VAL-F6b asserts that a release
turns those draws into the same values as the release before it. It proves reproducibility, never
correctness. Correctness of the distribution families is the
goodness-of-fit work in `docs/design/variability-and-faults.md` section F.3, which is where an
external distributional reference belongs.

Sparkplug B TCK conformance is a VAL-GATE, but it belongs to the IoT section, which owns the
payload. It is named here only to record that the registry's Sparkplug mapping artifact is the input
to that gate.

### 7.6 Named CI gates owned by this section

| Gate     | Assertion                                                                                                          |
| -------- | ------------------------------------------------------------------------------------------------------------------ |
| LINT-1   | `tf-lint-det` clean                                                                                                |
| LINT-2   | no expired nondeterminism annotation; every annotation has reason and owner                                        |
| LINT-3   | conventional commits and `import-linter` contracts clean                                                           |
| SCHEMA-1 | every sample validates against its schema; every subject has at least 3 samples                                    |
| SCHEMA-2 | no schema content change without a version bump                                                                    |
| SCHEMA-3 | no consumer-declared field removed or narrowed                                                                     |
| SCHEMA-4 | generated bindings match a fresh regeneration (Python and Rust)                                                    |
| SCHEMA-5 | a version bump that removes or renames ships an upcaster in the same commit                                        |
| SCHEMA-6 | a `consumes.yaml` entry is `pending` only while its subject is absent from the registry (4.2)                      |
| SCHEMA-7 | a `reserved` subject has no producer, and a subject with a producer is not reserved (4.2)                          |
| SCHEMA-8 | every event's `twinflowproducerid` is listed for its subject in `registry.yaml` (4.3)                              |
| SCHEMA-9 | during a MAJOR overlap window, the `SCN-F4` smoke run emits at least one sample of each major (5.5)                |
| CFG-1    | all three profiles validate with `--strict-warnings`                                                               |
| CFG-2    | every `TF-C` error code belonging to a registered reference domain is produced by at least one test                |
| CFG-3    | `tf config upgrade` round-trips every archived config to the current version and the result validates              |
| CFG-4    | every reference domain in `docs/reference/error-codes.md` has a registered owner or a named phase                  |
| METRIC-1 | every metric id referenced anywhere in the workspace resolves against the registry of 5.15                         |
| METRIC-2 | the metric registry is append-only within a facility schema major                                                  |
| IMPORT-1 | `import-linter` boundary, independence, and layering contracts clean                                               |
| IMPORT-2 | the workspace import graph has no cycle                                                                            |
| IMPORT-3 | every name in a package's `__all__` is defined there or declared as a re-export, and no name has two owners        |
| MIG-1    | migrations apply forward from every supported historian version and `check()` passes                               |
| MIG-2    | every archived golden log replays and reproduces its golden KPIs                                                   |
| MIG-3    | the CHANGELOG compatibility table is present and matches the registry                                              |
| SEMVER-1 | no public Python symbol removed without a breaking footer and a major bump                                         |
| SEMVER-2 | no OpenAPI or GraphQL breaking change without the same                                                             |
| SEMVER-3 | release metadata consistent (table, tag, manifest)                                                                 |
| BRICK-1  | each package installs alone into a clean venv and its isolated tests pass                                          |
| BRICK-2  | no sibling domain package, as listed in `[tool.twinflow.layers]`, is in `sys.modules` in a brick-isolated test     |
| BRICK-3  | every package has README, API.md, tests, and at least one isolated test                                            |
| BRICK-4  | `twinflow-kernel` and `twinflow-config` import in a clean environment holding only their declared dependencies     |
| TIER-1   | garage quickstart completes cold in under 5 minutes and serves the dashboard                                       |
| TIER-2   | in the growth compose, a device container cannot reach the IT segment or the internet, and can reach the OT broker |
| TIER-3   | `helm lint` and `kubeconform` clean on the rendered enterprise manifests                                           |
| TIER-4   | nightly `kind` deploy serves `/healthz` and its NetworkPolicy denies OT to IT                                      |
| TIER-5   | container and network counts in each compose file match `[tool.twinflow.tiers]`, which the README renders from     |
| API-1    | schemathesis finds no spec violation over the generated OpenAPI                                                    |
| API-2    | webhook signature, replay-window rejection, and dead-letter behavior correct                                       |
| API-3    | GraphQL depth and complexity limits enforced; SDL diff gate clean                                                  |
| API-4    | every route emits `twinflow.integration.api_request` with the principal and scopes recorded                        |
| BUDGET-1 | every CI job inside its `ci_budget.yaml` allowance, and the paced-cell arithmetic of 5.3 recomputed                |
| A2-4     | executed branches outside the declared capability modules are identical across the three A2 profiles (5.12)        |
| RUST-1   | Python and Rust produce identical draws for the twelve named streams (7.3, D-06)                                   |

Two of these gates need a note on how they stay falsifiable, which is D-12's rule. `BRICK-2` reads
its domain-package list from `[tool.twinflow.layers]` in the root `pyproject.toml`. That is the
same table the layering contract of 2.9 reads, so the gate and the contract cannot disagree. The
list it excludes is exactly `schemas`, `rng`, `kernel`, `config`, and `storage`, which every domain
package depends on by construction. Naming a sibling domain package is the defect the gate exists
to catch, and an earlier wording that excluded every twinflow package could not fail at all.
`BUDGET-1` has two failure conditions. A job that exceeds its `ci_budget.yaml` allowance fails it.
So does a mismatch between the 5.3 table's products and the scenario lengths, speeds, and example
counts the test suite is configured with, which is what makes a scenario that grows past its budget
a defect rather than a timeout.

---

## 8. Phase placement

The ordering rule is simple: anything that later work would have to be rewritten to accommodate
goes in Phase 0. Everything else lands with the first consumer that needs it, and nothing is
dropped.

**Phase 0, contracts that cannot be retrofitted.** This is the agreed resequencing.

| Piece                                                                                   | Why it must be first                                                                                                                                               |
| --------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| Kernel ports (clock, RNG, network, storage, ids, env)                                   | every subsystem is written against them from its first line; retrofitting dependency injection across 20 packages is a rewrite                                     |
| `SimEventLoop` and `SimClock` (C2)                                                      | the scheduler determines how all async code is written                                                                                                             |
| `SplittableRng` with name-addressed streams (C1)                                        | if streams were creation-order addressed, every golden file recorded before the last subsystem was added would be invalid                                          |
| Canonical encoding, `stable_hash`, `RunManifest` (C1)                                   | the log format is the substrate for E1, E4, E25, E27, and every golden file                                                                                        |
| Schema registry with the envelope, the compat checker, and codegen (C3)                 | additive-only evolution is only enforceable from the first event; a registry added later cannot police the history it did not see                                  |
| Config loader with line-numbered errors (C5)                                            | every subsystem registers its block; a loader added later means every existing block gets rewritten                                                                |
| uv workspace, justfile, CI skeleton with LINT-1, DET-1, SCHEMA-1 (C10)                  | the gates must exist before the code they judge                                                                                                                    |
| Package topology and import-linter contracts (A1)                                       | boundaries are cheap to declare on day one and expensive to impose on day 400                                                                                      |
| The nondeterminism lint                                                                 | the same argument as the boundaries: it prevents the debt rather than paying it down                                                                               |
| `InMemoryNetwork` with the fault kinds                                                  | the twin's first message goes through it                                                                                                                           |
| Migration framework skeleton and the upcaster registry (C6)                             | the first schema version must already have somewhere to upcast from                                                                                                |
| `micro_fulfillment` profile (A2, first of three)                                        | it is the Phase 1 walking-skeleton target, so it is authored as the schema is authored                                                                             |
| Snapshot protocol definition plus DET-6 as `xfail(strict=True)`                         | the gate exists before the feature so E4 flips it rather than inventing it                                                                                         |
| `crates/twinflow-rng` and `RUST-1` (D-06)                                               | retrofitting a compatible RNG after the device agent ships invalidates every recorded fleet run, which is the one class of damage no later phase can undo          |
| `twinflow.kernel.numeric`, the distribution layer over the NEP 19 stream-stable methods | every draw in the repository goes through it, and moving a subsystem onto it later changes that subsystem's draw order and its golden files                        |
| `twinflow.kernel.resources`, the asyncio-native DES primitives (5.2)                    | the twin's stations, docks, and charge points are written against them from their first line; discovering in Phase 1 that there is no queue primitive is a rewrite |
| The metric registry envelope and its schema (C5, 5.15)                                  | stage 6 of the config pipeline resolves `spec_limits` into metric ids from Phase 0, so the identifier space has to exist even though the expressions do not        |
| `SCN-F0`, the 60 simulated second paced scenario                                        | DET-4 is a required merge check from Phase 0 and cannot run against a full simulated day inside the job budget (D-13)                                              |

**Phase 1, walking skeleton.** Garage tier compose (A3 tier 1) with Mosquitto, DuckDB, and the
five-minute quickstart; TIER-1; production-mode adapters for MQTT and DuckDB so both modes are
exercised from the first week rather than production mode being discovered broken in Phase 5;
`tf run`, `tf config validate`, `tf facility init`.

**Phase 2, LSS engine.** REST API v1 read surface (A6, first slice): `/findings`, `/twin/state`,
`/metrics/{id}`, `/runs`, `/stream`. It lands here because the dashboard and the E1 replay viewer
both consume it, and E1 pulls forward to just after Phase 2 in the agreed resequencing. GraphQL and
webhooks wait, because nothing consumes them yet and shipping an unused API surface is how APIs
acquire bad shapes.

**Just after Phase 2, E1 hosted replay.** Consumes the canonical event log and the run manifest,
both Phase 0. No new foundations work beyond a static export command, which is why E1 can move this
far forward.

**Phase 3, sensor breadth.** `midmarket_3pl` profile (A2, second of three), because that is the
first configuration with enough stations and sensors to exercise the catalog. Growth tier compose
with Purdue segmentation and TIER-2 (A3 tier 2), because a 120-device fleet is the first time the
single-network garage topology stops representing anything real. Historian migrations become live
(C6 store half), because Phase 3 is the first time the historian schema changes under recorded data.
Webhook delivery (A6), because the CMMS loop in 6b is the first genuine outbound integration.

**Phase 3c, process mining.** `twinflow-procmine` is written here under Apache-2.0, which is D-14.
No new foundations work beyond one arrangement: PM4Py enters the `integration` job as a
development-only comparison oracle, never as a runtime dependency and never distributed, so the
conformance gates in the LSS section get an external reference under D-11 without the AGPL reaching
the shipped work. DET-7 gains no entry here, because nothing stochastic from a third party runs
inside the simulation at this phase; its first entry arrives in Phase 3d with `statsforecast`.

**Phase 3h, transport network, and E13 multi-site.** `enterprise_network` profile (A2, third of
three), because it is the first configuration with more than one site. Broker-to-broker bridging
extends `InMemoryNetwork`'s topology model with an inter-site link class.

**Phase 4, CV and store-and-forward.** `BlobStore` port gains its first real consumer (synthetic
frames). SCN-F2's store-and-forward assertions become end-to-end rather than network-level.

**Phase 5, polish.** mTLS from the internal CA at the growth tier, which is `MtlsIdentity`, the last
unimplemented `Identity` adapter; the enterprise adapter set, which A3 requires as the one
implemented example per seam and which nothing earlier consumes: `KafkaEventBus`, `KafkaEventLog`,
`DeltaTableStore` against object storage, and `S3BlobStore`, each landing with its conformance-suite
run in the `integration` job; the enterprise Helm chart, TIER-3 and TIER-4 (A3 tier 3); GraphQL
(A6), by which point the findings and genealogy graphs are large enough to justify it; the 1.0.0
release and the frozen semver policy (C9 reaches full force at 1.0.0, having operated in pre-1.0
mode until then).

**Phase 6, the E-tier.** Foundations work that lands with its dependent:

- E2 MCP server wraps `twinflow.api.services`, no new foundations.
- E4 event-sourced replay implements subsystem snapshots and flips DET-6 from `xfail` to passing.
- E5 autonomy tiers consume `twinflow.config.config_applied` and the `config:apply` scope, both
  defined in Phase 0 and Phase 2 respectively.
- E36 edge compute tiers extend the network topology model with the four compute tiers and add
  per-tier latency budget assertions to the fault framework.
- E43 MLOps consumes the migration framework for model registry versioning.
- E45 AI FinOps consumes the `api_request` event for per-question cost accounting.

Cross-cutting: C9's release automation is wired in Phase 1 (tagging, changelog, build) and
completes in Phase 5 (PyPI publish of every brick, SBOM, determinism manifest). It is wired early
because a repo whose first release is at Phase 5 has no release history to show, and the release
history is itself part of the presentation requirement.

---

## 9. Open questions

These are genuine ambiguities an implementer will hit. None has been silently resolved.

1. **Production-mode code paths are not covered by DST.** The design deliberately swaps
   `aiomqtt`, `asyncpg`, and `deltalake` out in simulation mode, which means the production adapter
   code is never exercised by the deterministic suite. The `integration` job of 5.14 answers the
   mechanical half: `just test-integration`, 15 minutes, path-filtered plus nightly, running the
   adapter conformance suite against live Mosquitto, EMQX, Postgres, and Delta, plus SCN-F3. What
   is still open is the claim made to a reader. Confirm that the README says "deterministic
   simulation covers business logic; adapters are covered by container integration tests", rather
   than implying DST covers everything, and confirm that a nightly-only gate is acceptable coverage
   for the adapter layer or whether the conformance suite must become a required merge check at
   some later phase.

2. **Cross-platform float determinism has a floor.** DET-2 as specified asserts byte identity only
   for integer and quantised fields. Making continuous fields byte-identical across architectures
   would need either fixed-point arithmetic throughout the physics models or a vendored softfloat
   library for transcendental functions. Both are large and both would slow the sim. The question
   for the author: is quantise-at-the-boundary enough, or is full cross-architecture bit
   identity a requirement worth a fixed-point numerics layer in a later phase? The current spec
   assumes the former and documents the limit.

3. **Lockstep versioning versus take-one-brick.** C9 says lockstep versions across bricks. A1 says
   a reader adopts one brick. Those pull in opposite directions: lockstep means a quality manager
   pinning `twinflow-lss==0.9.3` gets a version number that moved because the transport network
   changed. The spec follows C9 because C9 is explicit, and records the cost. Confirm, because the
   alternative (independent versions with a published compatibility matrix) is defensible and the
   choice is visible to every adopter.

4. **CloudEvents adoption.** The envelope is specified as CloudEvents 1.0 compliant, which is an
   addition to the source requirements, not a contradiction of them. It buys an interoperability
   standard and a conformance test target, and it costs the awkward lowercase extension attribute
   names. Confirm before Phase 0 freezes the envelope, because changing it later is a major bump
   on every subject.

5. **Facility schema version versus release version.** The spec makes `schema_version` inside
   `facility.yaml` independent of the release version, on the grounds that a config author must
   not have to edit their file for every release. C9 lists facility.yaml as one of the four
   versioned contracts without saying whether it shares the release version. Confirm.

6. **GraphQL scope.** v1 is read-only, with writes going through REST. A reader might reasonably
   expect a `runWhatIf` mutation. The tradeoff is one implementation of idempotency and audit
   versus GraphQL feeling incomplete. Confirm the read-only decision, or accept the duplication.

7. **Enterprise cloud adapters cannot have real CI coverage.** `AzureIotHubIngress`,
   `AwsIotCoreIngress`, `SnowflakeTableStore`, and `DatabricksSqlTableStore` need accounts the
   constraint paragraph forbids ("fully local, no cloud account"). The spec ships them as stubs
   plus the conformance suite. The open question is whether to also ship recorded-cassette
   contract tests against captured protocol traces, which would raise confidence but requires the
   traces to have been captured somewhere, and capturing them on a client account would violate the
   IP hygiene rule. The current position is stubs plus conformance suite plus an explicit
   limitations entry.

8. **Sensor catalog schema ownership.** Requirement 2b puts the sensor catalog in YAML with its own
   structure. This section owns config mechanics and this section's schemas; the IoT section owns
   the catalog's content and semantics. The boundary proposed is that the catalog's JSON Schema
   lives in `/schemas/config/sensor_catalog/` and is registered by `twinflow-sensors` through the
   sections entry point. Confirm that split so neither section writes the other's schema.

9. **Tick resolution default.** 1 microsecond is proposed. Sub-millisecond resolution matters for
   E36's "safety interlocks under 100 ms" latency budget and for conveyor encoder physics; it costs
   nothing in memory (integers) but does mean sim-time arithmetic on a 30-day horizon uses values
   around 2.6e12, which is fine for int64 and awkward to read in raw logs. Nanosecond resolution
   would make E46's RF timing modeling exact. Confirm 1 microsecond, or choose nanosecond and
   accept 2.6e15 tick values in the logs.

10. **Webhook retry timing diverges between modes.** In simulation mode retry jitter is drawn from a
    seeded stream and is deterministic; in production it is drawn from the same stream but
    against a real clock, so wall-clock timing differs while the sequence of delays does not. This
    is correct but subtle. Confirm that "deterministic delay sequence, real wall-clock execution" is
    the intended production behavior rather than true randomness.

11. **Third-party determinism is a moving target.** DET-7 pins each stochastic dependency, but a
    dependency can become nondeterministic in a patch release. The proposal is that
    `determinism_exclusions.yaml` entries need an owner and a linked issue and are printed in CI
    output, so the exclusion set is visible rather than silent. The open question is the policy when
    a library cannot be fixed: exclude its outputs from the byte-identity gate (current proposal),
    pin the library forever, or replace it. Optuna, the RL dispatcher of E11, and any torch-backed
    model in E28/E31/E33 are the likely cases.

12. **Purdue segmentation test cost in CI.** TIER-2 needs docker compose with three networks and an
    exec into a container, which is feasible on GitHub-hosted runners but takes minutes. The spec
    puts it on path-filtered PRs plus nightly. Confirm that a change to `deploy/growth/**` is the
    right trigger, or whether the Purdue assertion is important enough to run on every PR despite
    the budget.

13. **No published vector set covers two of twinflow's BLAKE2b parameterizations.** VAL-F9a covers
    `content_hash` at a 256-bit digest through RFC 7693's Appendix E self-test, which exercises
    digest lengths 20, 32, 48, and 64 bytes. It does not cover the 16-byte personalised name hash of
    R2, and it does not cover the 8-byte `stable_hash64`, because personalisation is outside RFC
    7693's scope and neither length is a truncation of a longer digest. VAL-F9b compares
    against the BLAKE2 reference implementation rather than against a published table, which is a
    weaker footing than every other gate in 7.5. The options are to accept it and say so in the
    gate description, to move `stable_hash64` to a 256-bit digest truncated by an explicitly
    twinflow-owned rule so the primitive itself is RFC-covered, or to drop personalisation and mix
    the personalisation string into the message instead, which brings the derivation entirely
    inside RFC 7693. The third would change the RNG derivation, which
    `docs/design/variability-and-faults.md` section A.1 fixes, so it needs deciding before Phase 0
    rather than after.

14. **The DET-2 cross-platform tolerance has no value yet.** 5.4 says the number is set from the
    first ten green runs across the ubuntu and macos runners, at ten times the largest divergence
    those runs show. Until those runs exist the key is absent and DET-2 asserts only its integer
    and quantised half. Two things need confirming: that ten runs is enough evidence to set the
    number from, given that a runner image change can shift the underlying libm, and what the
    policy is when a runner image bump moves the divergence, since the gate is written to refuse to
    widen itself and a legitimate platform change is indistinguishable at the gate from a
    regression.

15. **The metric registry's expression field is a Phase 0 hole with a Phase 6 filling.** 5.15 ships
    the envelope, the grammar, and the identifier registry in Phase 0 with `expression: null` on
    every entry, and the AI-layer section supplies the expressions with E26b. The design assumes
    that no expression syntax decision made in Phase 6 will force a change to the envelope. That
    holds if expressions stay opaque strings, and it fails if they need structured operands, a
    dependency graph between metrics, or a per-metric evaluation window declared alongside the
    definition. Confirm the opaque-string assumption with the AI-layer section before Phase 0
    freezes the schema, because `metrics.yaml` is a validated config and widening it later is a
    facility schema MINOR at best and a MAJOR if the field type changes.
