---
title: Dashboard, hosted replay demo, accessibility, and 3D view
description: Presentation-layer contract for the single-file dashboard, the static replay bundle, the WCAG conformance gates, and the browser-native 3D factory view.
topic_type: reference
audience: contributors
---

# Dashboard, hosted replay demo, accessibility, and 3D view

Status: design spec, implementation contract. Written to be built with TDD.
Owning packages: `twinflow-dashboard`, `twinflow-replay`, `twinflow-alarms`, `twinflow-view3d`.

Binding doctrine: `docs/design/DOCTRINE.md`. Where that page and this one disagree, the doctrine wins. Rulings D-01, D-02, D-03, D-04, D-05, D-07, D-08, D-09, D-10, D-11, D-12, D-13 and D-14 are applied here and each is cited at the point where it changes the design.

Evidence discipline: every external reference in this section names its edition and its locator, and every one was retrieved as raw text on 2026-08-09 with the HTTP status recorded. Four references could not be read: three are sold by their publishers and one publisher's copy answered an automated request with a bot challenge. Section 7.3.3 names all four, names what could not be read in each, and routes every number that depends on them to an open question instead of to a gate (D-11 rule 5). One free primary source for control-room human factors was read in full: NUREG-0700 Revision 4, retrieved as a PDF and extracted to text on 2026-08-09. Section 5.6.4 records that retrieval, names the nine guidelines this document applies, and routes each one to the clause it backs and to the place it is quoted.

Two gate classes, kept apart because D-11 applies to one of them. A validation gate checks a computed value against a named external published reference, at a tolerance no tighter than that reference's printed precision, and carries the id `VAL-GATE <name>`, the same form the accuracy stack and the roadmap use. A budget gate checks a value this repository chose for itself, names the machine that measured it, and carries the id `BG-<name>`. A budget gate never claims external authority for its number. Section 7.3.1 holds the first class, section 7.3.2 the second.

---

## 1. Scope

This section is the presentation layer of twinflow: the thing a hiring manager looks at, plus the artifact they look at when they will not install anything, plus the document that decides whether they look at all.

### 1.1 Requirements owned in full

| Req                                             | Text in source                                                                                                                                                                                                                                                                                                                                                                                                                 | Where covered here                                                                            |
| ----------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ | --------------------------------------------------------------------------------------------- |
| Component 8                                     | "Dashboard: single-file, no build step: live line state, fleet health, findings stream, bottleneck, agent chat."                                                                                                                                                                                                                                                                                                               | Section 2.1, section 3, section 5.1 to section 5.9, section 7.1, section 7.2                  |
| Component 9                                     | "README: one-line pitch, a measured headline, demo GIF of the agent what-if flow ending in the statistical verdict, architecture diagram, five-minute docker compose quickstart, honest limitations section, and a short 'why I built this' connecting it to real fleet deployments and LSS practice without naming clients."                                                                                                  | Section 5.14, section 7.1, section 7.3.2, section 7.7                                         |
| E1                                              | "Hosted replay demo on GitHub Pages: record a full simulated shift (telemetry, findings, agent transcript) and ship a static replay viewer so anyone can watch the factory run, alarms fire, and the agent answer questions IN THE BROWSER without installing anything. Most people who judge this repo will never run docker; this is the single highest-visibility feature. Link it in the first three lines of the README." | Section 2.2, section 4.4.3, section 5.10, section 5.11, section 7.3.2, section 7.4, section 8 |
| C12                                             | "Dashboard accessibility: WCAG 2.1 AA basics; severity encoded by shape and text as well as color, colorblind-safe palette, keyboard navigation, ARIA live regions for new findings, reduced-motion mode (color-only alarm severity is a classic control-room failure; not making it is a differentiator)."<!-- docs-lint-ok STE-TERM-WORD verbatim quotation of the source requirement text -->                               | Section 5.12, section 6.3, section 7.3.1                                                      |
| Reference-architecture fidelity, final sentence | "The 2D dashboard ships first; a browser-native 3D factory view (three.js-class, driven by the same live state that feeds the 2D view) is a committed later milestone on the roadmap, and the limitations section notes that an Omniverse-class XR layer is the real-world counterpart the 3D view stands in for."                                                                                                             | Section 5.13, section 7.3.2, section 7.4, section 8                                           |
| Reference-architecture fidelity (d), UI half    | "include alarm management the way SCADA vendors mean it: alarm prioritization and rationalization so the findings stream cannot flood (dedupe, severity ranking, shelving)"                                                                                                                                                                                                                                                    | Section 2.3, section 5.6, section 6.2, section 7.3.2                                          |

### 1.2 Requirements owned in part

| Req    | Part owned here                                                                                                                                                                                                    | Part owned elsewhere                                                                   |
| ------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ | -------------------------------------------------------------------------------------- |
| C2     | The dashboard speed control, the sim-time readout, the wall-clock mapping readout, the achieved-compression readout, the browser-side replay clock.                                                                | The sim-clock service itself and the sim-time stamping of all events (kernel section). |
| C1     | The `ViewStateCanonical` hash used as the UI determinism check, byte-identical replay bundles on a pinned platform, and the measured cross-platform divergence report (D-05).                                      | The kernel RNG and the repeated-run hash check.                                        |
| C3     | The versioned contracts for every event the UI consumes and the one it publishes, plus the UI-side contract tests.                                                                                                 | The `/schemas` registry mechanics and the producer-side tests.                         |
| C4     | The UI test tiers: unit, property-based, seeded end-to-end, golden view-model snapshots, visual regression.                                                                                                        | The runtime budget policy across the repo.                                             |
| C5     | Validation rules for the `dashboard:`, `facility.geometry`, and `replay:` config blocks.                                                                                                                           | The config loader and the line-numbered error reporter.                                |
| C10    | The `just` recipes this section adds.                                                                                                                                                                              | The workspace and CI matrix.                                                           |
| C11    | Licence records and SBOM entries for the three vendored browser assets (font subset, three.js, DuckDB-Wasm) and for the test-only browser tooling.                                                                 | The audit and allowlist tooling.                                                       |
| C7     | The SECURITY.md paragraphs that cover the command surface, the absence of a model key in the browser, and the framing risk on the Pages path.                                                                      | The threat model for the MCP and REST surfaces.                                        |
| A1     | Four independently installable bricks and the README "use just this part" table.                                                                                                                                   | Package topology enforcement.                                                          |
| A2     | Facility geometry as config so both the 2D and 3D views come from `facility.yaml`, meaning the three worked profiles render without code changes.                                                                  | The profiles themselves.                                                               |
| A4     | The README slot for the published scaling curves, and the dashboard's own measured render budget.                                                                                                                  | The load-test harness.                                                                 |
| A5, A6 | README routing to ADOPTION.md, and the SSE/POST surface as one of the documented integration surfaces.                                                                                                             | ADOPTION.md content and the REST/GraphQL/MCP surfaces.                                 |
| E5     | The approval UI for L2 recommendations, autonomy-tier badges, and the who-changed-what audit strip.                                                                                                                | Autonomy tiers and the bi-directional connector.                                       |
| E6, E7 | The what-if result card fields for operator impact and energy delta.                                                                                                                                               | Operator model and energy KPIs.                                                        |
| E26    | The grounding chips in the chat transcript that make every number traceable to a query-result id, and the generated README metrics block carrying eval accuracy, abstention rate, and grounding-checker pass rate. | The accuracy stack itself.                                                             |
| E34    | The voice-demo clip slot in the replay viewer.                                                                                                                                                                     | STT/TTS.                                                                               |
| E47    | The "physical" badge on a hardware-in-the-loop device row and tile.                                                                                                                                                | Provisioning and the real device agent.                                                |
| E4     | The counterfactual compare view (two runs side by side, diffed).                                                                                                                                                   | Event-sourced replay in the historian.                                                 |

### 1.3 Consumed, not owned

Twin line state, fleet registry and health scores, LSS findings, bottleneck verdicts, agent turns and tool traces, what-if results, sim clock ticks, historian queries. This section defines the shape it needs from each and a contract test that fails when a producer drifts. It defines no business logic for any of them.

---

## 2. Packages

Four bricks. Each has its own README, its own tests, its own PyPI name, and installs alone.

Layering, declared once so the import graph test in D-09 has something to check. `twinflow-schemas` is the leaf and depends on nothing in this repository. `twinflow-alarms` depends on the leaf. `twinflow-dashboard` depends on the leaf. `twinflow-view3d` depends on the leaf. `twinflow-replay` depends on the leaf. No package in this section imports another package in this section, at all, in either direction. Asset exchange between `twinflow-dashboard`, `twinflow-view3d` and `twinflow-replay` runs through entry-point groups, described in section 2.5, because an import would create the cycle D-09 forbids and would break the install-alone claim D-10 requires to be tested rather than asserted.

### 2.1 `twinflow-dashboard`

Purpose: serve the single-file dashboard and stream events to it. Also ships the palette and contrast tooling because the tokens live with the view.

Distribution name: `twinflow-dashboard`. Import path: `twinflow.dashboard`.

Layout:

```
packages/twinflow-dashboard/
  pyproject.toml
  README.md
  src/twinflow/dashboard/
    __init__.py
    app.py              # create_app, ASGI
    stream.py           # SSE multiplexer, coalescing, backpressure
    commands.py         # POST /api/command handler, validation
    palette.py          # OKLCH token model, contrast, CVD simulation
    config.py           # DashboardConfig pydantic model
    assets/
      index.html        # THE single file
      fixture/          # tiny built-in replay bundle (~200 KB) so the brick demos alone
      fonts/LICENSE.txt
  tests/
  tools/
    extract_scripts.mjs # test-only: pulls <script> blocks out of index.html for node:vm
```

Public API:

```python
from twinflow.dashboard import create_app, serve, DashboardConfig, viewer_asset_root
from twinflow.dashboard.palette import (
    Oklch, Palette, contrast_ratio, simulate_cvd, delta_e_2000, load_palette,
)

def create_app(bus: EventBus, config: DashboardConfig) -> ASGIApp: ...
def serve(config: DashboardConfig) -> None: ...
def viewer_asset_root() -> Path: ...   # entry point 'twinflow.viewer_assets' -> 'dashboard'
```

`EventBus` is the subject-addressed fan-out port from D-08, declared as a `Protocol` in `twinflow-schemas` and imported from there, not redeclared here (D-09, one owner per public symbol). Its shape is `subscribe(types) -> AsyncIterator[Envelope]`, `publish(envelope)`, and `snapshot() -> Envelope` returning `ui.snapshot.v1`. The dashboard binds `EventBus` and never binds `Network`: retained messages, quality-of-service levels and last-will semantics belong to the device fleet, and a presentation client that asked for them would be claiming a broker relationship it does not have.

In production mode `EventBus` is backed by the historian and twin-sync API on the DMZ network. In simulation mode it is backed by the in-memory bus. The dashboard package never imports the twin, the LSS engine, or the fleet registry. It knows `/schemas` and nothing else.

CLI: `twinflow-dashboard serve`, `twinflow-dashboard demo [--bundle PATH]`, `twinflow-dashboard check-palette`, `twinflow-dashboard emit-tokens`.

`twinflow-dashboard demo` with no bundle argument serves the built-in fixture bundle. This is the A1 proof: `pip install twinflow-dashboard && twinflow-dashboard demo` shows a working dashboard with nothing else installed. There is a test for exactly that (section 7.1, `T-A1-1`).

Dependencies: `starlette`, `uvicorn`, `pydantic`, `twinflow-schemas`. Nothing else. No frontend toolchain, no npm, no node at runtime. Node is a development dependency for tests only. No port signature in this package names a columnar or dataframe type, so the core install stays at four packages and the D-10 clean-environment import job has a claim it can falsify.

### 2.2 `twinflow-replay`

Purpose: record a shift into a static, seekable, self-checking bundle; check a bundle; publish a Pages site.

Distribution name: `twinflow-replay`. Import path: `twinflow.replay`.

Public API:

```python
from twinflow.replay import (
    record, check, publish, ReplayConfig, Bundle, BundleManifest, Frame, CheckReport,
)

def record(config: ReplayConfig, runner: SimRunner) -> Bundle: ...
def check(path: Path, *, strict: bool = True) -> CheckReport: ...
def publish(bundle: Bundle, out: Path, *, base_path: str = "/") -> None: ...

class SimRunner(Protocol):
    """Discovered via the 'twinflow.runners' entry point group."""
    def run(self, *, seed: int, config: Path, until_sim_seconds: float) -> AsyncIterator[Envelope]: ...
```

The operation that reads a bundle and reports whether it is intact is named `check` everywhere: the function, the CLI subcommand, the report type, and the prose. One concept, one word. The repository word list in `docs/style/ste-terms.yml` is the reason, and the prose gate is what keeps a synonym from creeping back in.

The `SimRunner` Protocol plus entry-point discovery is what lets `twinflow-replay` install alone: `check` needs no simulator and no viewer, `publish` needs a viewer provider but no simulator, and only `record` needs a runner. Someone who wants "a seekable event-log replay format with a static viewer" adopts this brick and points it at their own event stream.

CLI: `twinflow replay record|check|publish|inspect`.

Dependencies: `twinflow-schemas`, `pydantic`. Nothing else. `record` also needs an installed runner and `publish` also needs an installed viewer-asset provider; both are resolved through entry points at call time and both fail with a named, actionable error when absent (section 2.5). `twinflow-dashboard` is not a dependency, which is what makes the venv in `T-A1-2` constructible.

### 2.3 `twinflow-alarms`

Purpose: alarm prioritisation and rationalisation as code. Turns a raw finding stream into a stream an operator can survive. Publishes `alarm.state.v1`.

Distribution name: `twinflow-alarms`. Import path: `twinflow.alarms`.

Public API:

```python
from twinflow.alarms import (
    AlarmManager, AlarmConfig, AlarmState, AlarmGroup, ShelfEntry, FloodVerdict,
)

class AlarmManager:
    def ingest(self, finding: Finding, *, sim_time: float) -> AlarmState: ...
    def shelve(self, key: AlarmKey, *, until_sim_time: float, reason: str, actor: str) -> AlarmState: ...
    def unshelve(self, key: AlarmKey, *, actor: str) -> AlarmState: ...
    def rate_per_10min(self, *, sim_time: float, role: str) -> float: ...
    def rates_per_10min(self, *, sim_time: float) -> Mapping[str, float]: ...  # every configured role
    def flood(self, *, sim_time: float, role: str) -> FloodVerdict: ...
    def floods(self, *, sim_time: float) -> Mapping[str, FloodVerdict]: ...
    def state(self) -> AlarmState: ...
```

`role` is mandatory on the single-role calls rather than defaulted, because an alarm rate is only meaningful against the attention of one operating position, and a default of "all roles" would meter a different quantity under the same name (section 5.6.3). The plural forms return one entry per configured role and are what the server publishes.

This is a real standalone brick. A quality or controls engineer who wants per-operator alarm rate metering and shelving with an audit trail installs this and nothing else.

Dependencies: `twinflow-schemas`, `pydantic`. No I/O.

Iteration order: every collection this package iterates into an `AlarmState`, a group, or a hash is a sorted sequence or a dict built by sorted insertion, never a `set` (D-03). Group member lists sort by `(severity_rank, first_sim_time, finding_id)`; the role map sorts by role id. A `set` here would make the published `alarm.state.v1` differ between processes with different hash seeds, which would break the tape for a reason that has nothing to do with alarms.

Ownership note: this brick exists here because the findings UI is unusable without it and no other section names an owner. If the LSS/findings section also specifies a rationaliser, `alarm.state.v1` is the merge point and this implementation becomes the reference consumer. Recorded as Open Question OQ-1.

### 2.4 `twinflow-view3d`

Purpose: the browser-native 3D factory view. Kept out of `twinflow-dashboard` so the base dashboard stays one file with zero vendored JS libraries.

Distribution name: `twinflow-view3d`. Import path: `twinflow.view3d`.

Ships: `assets/view3d.html`, `assets/view3d.js`, `assets/vendor/three.module.js`, and `twinflow.view3d.geometry`, which turns a validated `facility.yaml` into a scene description.

The vendored library is three.js, version 0.185.1, licence MIT, read from the npm registry metadata for `three` on 2026-08-09 (HTTP 200, `https://registry.npmjs.org/three/latest`). The version is pinned in `pyproject.toml`, the file hash is recorded in the SBOM, and the licence text ships beside it (C11). Renewing the pin is a deliberate commit that updates the version, the hash and the SBOM row together.

MIT is a permissive licence and can be redistributed inside an Apache-2.0 work with attribution, which is why three.js can be vendored at all. D-14 is the case that shows the alternative: a copyleft dependency whose network clause reaches a served dashboard would take the whole project with it. Every browser asset this section ships is checked against that rule before it is pinned, and section 7.3.4 holds the three pins and the one test-only tool with its licence.

Public API:

```python
from twinflow.view3d import scene_from_facility, SceneDescription, viewer_asset_root

def scene_from_facility(facility: FacilityConfig) -> SceneDescription: ...
def viewer_asset_root() -> Path: ...   # entry point 'twinflow.viewer_assets' -> 'view3d'
```

`twinflow-dashboard` detects `twinflow-view3d` at startup through the `twinflow.viewer_assets` entry-point group and mounts `/view3d/`. If no `view3d` provider is installed, the 2D dashboard's view toggle renders as disabled with an explanatory tooltip and an `aria-describedby` message. The 2D dashboard never fails because 3D is missing, and `E2E-3D-2` is the test that says so.

When a provider is installed, the 3D view is on by default (section 6.2, `view3d.enabled` defaults to `true`). Shipping a committed milestone switched off is a way of shipping it disabled forever, and the graceful-absence path above already covers the machine that has no provider.

### 2.5 Boundary rules

- No package in this section imports any other package in this section. There is no exception and no documented-public-function carve-out. The import-graph test required by D-09 fails the build on any edge between them.
- Asset exchange runs through the `twinflow.viewer_assets` entry-point group, the same mechanism `twinflow-replay` already uses for `twinflow.runners`. A provider registers a name and a callable returning a directory: `dashboard` from `twinflow-dashboard`, `view3d` from `twinflow-view3d`. `publish` resolves `dashboard`; the dashboard server resolves `view3d`.
- A missing provider is a named failure, never a traceback. `publish` with no `dashboard` provider exits non-zero with "no viewer asset provider installed: pip install twinflow-dashboard". `record` with no runner exits non-zero with "no runner installed". Both messages are asserted verbatim in `T-A1-2` and `T-A1-4`.
- All four packages validate every envelope they receive against `/schemas` in debug mode, and against a compiled fast validator in release mode.
- Every name in each package's `__all__` is defined in that package (D-09). `EventBus`, `Envelope` and `Finding` are imported from `twinflow-schemas` and are not re-exported by any package here.
- The browser code has no package manager and no build step. It is one HTML file containing classic `<script>` blocks (section 5.2 explains why classic and not ES modules).

---

## 3. Domain model

The dashboard has a view model, not a business model. It is a pure function of the event stream. Everything below lives in browser memory and is reconstructible from frames plus a keyframe.

### 3.1 `ViewState`

```
ViewState
  run:            RunIdentity
  clock:          ClockState
  stations:       Map<station_id, StationView>
  edges:          Map<edge_id, EdgeView>
  devices:        Map<device_id, DeviceView>
  findings:       Map<finding_id, FindingView>
  alarms:         AlarmView
  bottleneck:     BottleneckView | null
  constraint_log: List<ConstraintShift>
  chat:           List<AgentTurnView>
  whatifs:        Map<scenario_id, WhatIfView>
  approvals:      Map<request_id, ApprovalView>
  stream:         StreamHealth
  prefs:          Preferences
```

Invariants, all asserted in property tests (section 7.2):

- `V1`: `ViewState` is produced only by `apply(state, envelope) -> state`, which is pure and total. Unknown event types are ignored and counted, never thrown.
- `V2`: `clock.sim_time` never decreases during forward replay.
- `V3`: `findings` is append-and-update only within a run. A finding is removed from `findings` only by a `run` change.
- `V4`: every `FindingView.severity` maps to exactly one entry in the severity table (section 5.12.1).
- `V5`: `hash(canonical(state))` is stable under key insertion order and under repeated application of an idempotent envelope.
- `V11`: `canonical(state)` contains no field whose value derives from a wall clock, from transport health, or from browser-local preference. The field list below is the whole definition and the test enumerates it.

#### 3.1.1 `ViewStateCanonical`

Nothing in this section hashes `ViewState`. Everything hashes `ViewStateCanonical`, the subset produced by `canonical(state)`:

| Included                                                                                                                                                     | Excluded, and why                                                                          |
| ------------------------------------------------------------------------------------------------------------------------------------------------------------ | ------------------------------------------------------------------------------------------ |
| `run` (the hashed core of section 3.2), `stations`, `edges`, `devices`, `findings`, `alarms`, `bottleneck`, `constraint_log`, `chat`, `whatifs`, `approvals` | `clock.achieved_speed` and `clock.wall_elapsed`: measured against a wall clock (D-02)      |
| `clock.sim_time`, `clock.requested_speed`, `clock.authority`, `clock.bounds`                                                                                 | `stream`: transport health, a property of one connection and not of the run                |
| Map keys emitted in sorted order, floats emitted with the fixed formatting rule in section 5.3                                                               | `prefs`: browser-local, never sent by the server, never recorded (section 4.2, `set_pref`) |

`canonical` is one function with one definition, used by four consumers: `V5`, `T-STORE-3`, `P-BUNDLE-ROUNDTRIP`, and the `ui.snapshot.v1` payload (section 4.1). Defining it once is what stops the four from drifting apart, and `T-CANON-1` asserts that the excluded set is exactly the set above by round-tripping a state with every excluded field perturbed and asserting the hash does not move.

This is D-01 applied at the presentation layer. The kernel splits its run manifest into a hashed core and a provenance sidecar for the same reason: a hash that covers wall-clock and machine identity can never match twice, so a byte-identity claim over it is false on its first event.

### 3.2 `RunIdentity`

| Field              | Type       | In `canonical` | Notes                                                                         |
| ------------------ | ---------- | -------------- | ----------------------------------------------------------------------------- |
| `run_id`           | UUIDv5 hex | Yes            | Derived, not generated. See below                                             |
| `seed`             | int        | Yes            | C1. Always shown in the header                                                |
| `config_hash`      | sha256 hex | Yes            | Hash of the resolved config tree                                              |
| `schema_snapshot`  | sha256 hex | Yes            | Hash of the `/schemas` tree the run was produced against                      |
| `scenario_id`      | str        | Yes            | Names the scenario, including the fault schedule                              |
| `profile`          | str        | Yes            | `micro_fulfillment` \| `mid_market_3pl` \| `enterprise_network` (A2)          |
| `mode`             | enum       | Yes            | `production` \| `simulation` \| `replay`                                      |
| `sim_epoch`        | ISO 8601   | Yes            | Sim time zero. A config value, not a reading of the machine clock             |
| `twinflow_version` | semver     | Yes            | Release version, not a build timestamp                                        |
| `schema_versions`  | map        | Yes            | Event type to version, from the envelopes seen, emitted sorted by key         |
| `synthetic`        | enum       | Yes            | `fully_synthetic` \| `hybrid_hil`. Rendered as a permanent badge              |
| `wall_clock_epoch` | ISO 8601   | No             | C2 mapping. Lives in `provenance.json`, delivered to the UI on `ui.pacing.v1` |

`run_id` is `uuid5(TWINFLOW_RUN_NAMESPACE, f"{seed}:{config_hash}:{schema_snapshot}:{scenario_id}:{mode}")`, where the namespace is a fixed UUID constant compiled into `twinflow-schemas`. A ULID embeds a millisecond wall reading plus randomness, so two runs of the same scenario could never agree on it, and it sat inside the first event of the log. Deriving it from the hashed core instead makes two runs of the same scenario carry the same identity, which is exactly what C1 claims and what `BG-DET-UI-1` measures.

`wall_clock_epoch` stays a requirement: C2 asks for the wall-clock mapping to be recorded per run and shown in the dashboard. It is recorded in the provenance sidecar and displayed from `ui.pacing.v1`, so the requirement is met without the value entering the hashed tape. This is D-02: the four legal wall-clock readers are the sidecar writer, the pacer, the observability exporter, and operator-facing log lines, and in none of them does the value enter an event payload or steer control flow.

The `synthetic` badge is not dismissible. Every screenshot, GIF frame, and replay frame carries it. The header renders "SYNTHETIC" for `fully_synthetic` and "SYNTHETIC + N PHYSICAL" for `hybrid_hil`, where N is the count of devices carrying `physical: true`. The enum exists because E47 puts one real ESP32 into the fleet, and a badge that reads "synthetic" over a tile driven by a hand touching a real sensor is a false statement on the most-shared clip the repository will produce. Precision makes the honesty control stronger, not weaker.

### 3.3 `ClockState`

| Field             | Type                     | In `canonical` | Notes                                                        |
| ----------------- | ------------------------ | -------------- | ------------------------------------------------------------ |
| `sim_time`        | float, sim seconds       | Yes            |                                                              |
| `requested_speed` | float \| `"max"`         | Yes            | 0 means paused                                               |
| `authority`       | enum                     | Yes            | `server` in live mode, `browser` in replay mode              |
| `bounds`          | `[float, float]` \| null | Yes            | Replay only: seekable range                                  |
| `achieved_speed`  | float                    | No             | Sim seconds per wall second, measured over a 5 s wall window |
| `wall_elapsed`    | float                    | No             | Wall seconds since the run started                           |

`achieved_speed` exists because a request for 60x that the simulator cannot meet must be visible. Showing only the requested speed would be a lie the reader could catch.

Both wall-derived fields arrive on `ui.pacing.v1`, a transport-level frame that is never recorded into a bundle and never enters `canonical`. In replay mode there is no server to send it, so `ReplayClock` computes both locally from its own animation-frame timer, which is a wall clock the browser owns and which steers nothing but the displayed number. D-02 permits the pacer to read a wall clock precisely because pacing changes when a frame is drawn and never which frame is drawn.

### 3.4 `StationView`, `EdgeView`

```
StationView
  id, label
  position: {x, y, z}      # metres, from facility.yaml
  footprint: {w, d, h}
  level: int               # mezzanine support
  state: enum(idle, running, blocked, starved, down, changeover)
  wip: int
  utilisation: float 0..1
  cycle_time_s: float | null
  takt_s: float | null
  operators: int | null    # E6
  is_bottleneck: bool
  open_findings: int
```

```
EdgeView
  id, from_station, to_station
  kind: enum(conveyor, manual, amr, crane, dock)
  flow_rate_per_h: float
  queue: int
  path: List<{x, y}>       # polyline, from facility.yaml
```

Invariant `V6`: exactly zero or one station carries `is_bottleneck = true`. If a `twin.bottleneck.v1` names a station the view has never seen, the panel renders the id verbatim with a "station not in current layout" note rather than dropping the fact.

### 3.5 `DeviceView`

```
DeviceView
  device_id, device_type, uns_topic
  state: enum(online, degraded, offline, stale, provisioning)
  health_score: float 0..100
  fmea: {severity: int 1..10, occurrence: int 1..10, detection: int 1..10, rpn: int}
  last_seen_sim_time: float
  firmware: str | null
  physical: bool            # E47
  station_id: str | null
  sparkline: List<{t: float, v: float}> | null   # aggregate series, lazily loaded
```

Invariant `V7`: `rpn == severity * occurrence * detection`. The UI recomputes and flags a mismatch as a stream integrity warning rather than displaying the producer's number silently.

### 3.6 `FindingView`

```
FindingView
  finding_id
  kind: enum(spc_violation, capability_shortfall, msa_failure, sop_violation,
             fleet_health, twin_divergence, process_mining_deviation, safety, security, other)
  severity: enum(critical, high, medium, low, info)
  rule_id: str              # e.g. "nelson_2", "we_1", "cpk_below_1_33"
  entity_ref: {kind, id}    # station / device / lot / supplier / order
  sim_time: float
  title, detail
  evidence: EvidenceWindow  # series id, t_start, t_end, limits, points
  suggested_next_tool: str | null
  state: enum(new, acknowledged, shelved, resolved)     # lifecycle, set by operator action
  display_state: enum(visible, grouped, shelved)        # placement, derived by the alarm manager
  count: int                # dedupe collapse count, number of ingest events folded into this row
  first_sim_time, last_sim_time: float
  chattering: bool
  sop_citation: {doc, clause, url} | null   # E8
```

Invariant `V8`: `count >= 1` and `first_sim_time <= last_sim_time`.

`state` and `display_state` are two fields because they answer two questions, and folding them into one makes the conservation law below unprovable. `state` answers "what has an operator done about this", and `resolved` is one of its values. `display_state` answers "where does this row appear right now", and every row has exactly one placement. A `resolved` row is `visible` until the run ends; resolution greys the row and moves it to the bottom of its severity band, it does not remove it, because a findings list that deletes its own history cannot be audited.

### 3.7 `AlarmView`

```
AlarmView
  rates: Map<role_id, {rate_per_10min: float, flooding: bool}>   # one entry per configured role
  aggregate: {rate_per_10min: float, flooding: bool}             # all roles, labelled as such
  target_rate_per_10min: float      # configured, see 5.6.3 for the source
  flood_threshold_per_10min: float  # configured, see 5.6.3 for the source
  flooding_roles: List<role_id>     # sorted, empty when no role is flooding
  groups: List<AlarmGroup>          # populated only while a role is flooding or when dedupe fires
  shelved: List<ShelfEntry>
  suppressed_by_design: List<{rule_id, reason}>
  totals: {
    ingested: int,        # ingest events accepted since the run started
    rows: int,            # FindingView rows in the view
    visible_rows: int,    # rows with display_state == visible
    grouped_rows: int,    # rows with display_state == grouped
    shelved_rows: int     # rows with display_state == shelved
  }
```

Metering is per role because the quantity a rate threshold is about is the load on one operating position, and the roles are configured in `dashboard.alarms.roles` (section 6.2). With three roles configured, an all-roles aggregate crosses a single-position threshold at roughly a third of the load that threshold represents, which would make the meter fire early and the flood banner meaningless. The aggregate is still computed and still shown, labelled "all roles", because a supervisor watching the whole floor wants it; it is never compared against a single-position threshold. Whether the two published standards state their own figures per operator is unread and is Open Question OQ-13, so this section states the design reason and not a reading of a document it does not hold.

Invariant `V9` (finding conservation), in two parts, both asserted by `P-FINDING-CONSERVATION`:

- `V9a`, no ingest event is lost: `totals.ingested == sum(row.count for row in findings)`. Dedupe folds seven ingest events into one row with `count == 7`, and the sum still reaches seven. This is the law that matters, because dedupe is exactly the operation that would otherwise hide a fact while claiming to hide only noise.
- `V9b`, every row has exactly one placement: `totals.rows == totals.visible_rows + totals.grouped_rows + totals.shelved_rows`, and each term counts rows whose `display_state` equals the matching enum value.

The split into two statements is what makes each one falsifiable. A single equation counting ingest events on one side and rows on the other reads `7 == 1` for the worked dedupe example in section 5.6.2, where seven ingest events fold into one row. A sum over `count` and a partition over `display_state` are both true of that example and both fail on a real defect, which is what a conservation law has to be.

### 3.8 `AgentTurnView`

```
AgentTurnView
  turn_id, role: enum(user, agent, system)
  sim_time
  text
  tool_calls: List<{tool, args, result_id, duration_bucket: enum, ok: bool}>
  grounded_numbers: List<{text_span: [int, int], value: str, result_id: str}>
  ungrounded_numbers: List<{text_span: [int, int], value: str}>
  abstained: bool
  model: str                # model id, from the cassette header
  model_artifact_hash: str  # sha256 of the pinned model artifact or the cassette entry
  cost: {input_tokens: int, output_tokens: int, usd: float} | null   # E45
```

`duration_bucket` is one of `instant`, `fast`, `slow`, `very_slow`, with boundaries at 0.1 s, 1 s and 10 s of measured wall time. The raw millisecond figure is a wall-clock reading and cannot enter the tape (D-02); the bucket is what the tool-trace disclosure needs, because the reader is asking "did this call take a moment or a while", not "did it take 412 ms". The unbucketed value is written to the provenance sidecar for anyone profiling the agent.

Bucketing at record time is not enough on its own, because a slower machine would bucket the same call differently and the tape would move with the hardware. The bucket is measured once, at `record --refresh-cassette` time, stored in the cassette entry beside the response text and the token counts, and read back on every later run. That is D-04 applied: a component whose output cannot be made deterministic does not steer the run, so the tape records the decision it produced rather than recomputing it. `T-BUCKET-1` runs the same cassette twice under an injected clock that reports different durations and asserts both runs record the same bucket.

`cost` survives in the tape because with the response cassette of section 5.10 the token counts are recorded once and replayed, and `usd` is computed from a price table whose hash is in the sidecar. Without the cassette these three numbers would move on every run and `BG-DET-UI-1` would fail on its first execution.

Invariant `V10`: if `ungrounded_numbers` is non-empty, the turn renders with a visible "ungrounded number" warning and the numbers are marked in the text. The UI does not quietly present an unverified figure. This is E26(f) enforced at the last possible layer, in the pixels.

### 3.9 `WhatIfView`

```
WhatIfView
  scenario_id, label, config_diff: List<{path, from, to}>
  baseline_run, scenario_run: {run_id, seed, n_replications}
  throughput: {baseline, scenario, delta, delta_pct, unit}
  cost: {capex_usd, opex_usd_per_year, payback_months} | null
  energy: {kwh_per_pallet_baseline, kwh_per_pallet_scenario, delta_pct} | null   # E7
  operator_impact: {station_id, utilisation_before, utilisation_after, note} | null  # E6
  verdict: {
    test: enum(welch_t, students_t, mann_whitney, anova, kruskal),
    assumption_checks: List<{name, passed, statistic, p}>,
    statistic: float, p_value: float, alpha: float,
    effect_size: {name, value}, ci: [float, float], n_baseline: int, n_scenario: int,
    conclusion: enum(significant_improvement, significant_regression, no_significant_difference),
    caveat: str
  }
```

The verdict block is the final frame of the demo GIF. Its rendering is specified to the field level in section 5.8 because it is the single screenshot that carries the repo's thesis.

---

## 4. Events

All envelopes share the repo-wide envelope from `/schemas/envelope.v1.json`:

```json
{
  "schema": "lss.finding.v1",
  "run_id": "8f14e45f-ea7f-5e4c-9a1b-2c3d4e5f6a7b",
  "producer_id": "twinflow-lss",
  "producer": "twinflow-lss/0.4.1",
  "sim_time": 12345.5,
  "seq": 918234,
  "payload": {}
}
```

`producer_id` and the ordering rule come from D-07, which settles the envelope before Phase 0 freezes the schemas. `seq` is dense per `(run_id, producer_id)`, assigned by that producer, and the canonical total order over the whole log is `(sim_time, producer_id, seq)`. A single counter dense across every producer would need one allocator, and the garage tier already runs several containers plus the Rust agent with no allocator between them.

Three consequences the UI depends on:

- Gap detection is per producer. A hole in `twinflow-lss` sequence numbers means findings were dropped; it says nothing about the twin's frames. The stream health strip reports gaps per `producer_id`, which is more useful than one number anyway.
- The replay reader sorts by `(sim_time, producer_id, seq)` and never by `seq` alone. Sorting on a string producer id makes the order total and stable without any float comparison on `sim_time`.
- The pagination cursor for the historian query surface is the same triple.

### 4.1 Consumed

| Schema                      | Version | Payload shape (abridged)                                                                                 | Recorded | UI use                                  |
| --------------------------- | ------- | -------------------------------------------------------------------------------------------------------- | -------- | --------------------------------------- |
| `twin.line_state.v1`        | 1       | `{stations: [StationView-without-derived], edges: [...]}`                                                | yes      | Line state panel, 3D view               |
| `twin.bottleneck.v1`        | 1       | `{station_id, method, evidence: {utilisation, queue_len, takt_s, cycle_time_s}, confidence}`             | yes      | Bottleneck panel, station outline       |
| `fleet.device_health.v1`    | 1       | `{device_id, device_type, uns_topic, state, health_score, fmea, last_seen_sim_time, firmware, physical}` | yes      | Fleet panel                             |
| `lss.finding.v1`            | 1       | See section 3.6                                                                                          | yes      | Findings stream, alarm manager          |
| `alarm.state.v1`            | 1       | See section 3.7                                                                                          | yes      | Alarm meter, flood banner, shelf drawer |
| `sim.clock_tick.v1`         | 1       | `{sim_time, requested_speed}`                                                                            | yes      | Clock readout and speed control         |
| `agent.turn.v1`             | 1       | See section 3.8                                                                                          | yes      | Chat panel                              |
| `agent.whatif_result.v1`    | 1       | See section 3.9                                                                                          | yes      | What-if card                            |
| `agent.approval_request.v1` | 1       | `{request_id, scenario_id, autonomy_tier: 1..3, proposed_diff, expires_sim_time}`                        | yes      | Approval UI (E5)                        |
| `ui.snapshot.v1`            | 1       | `{view_state: <ViewStateCanonical>, at_sim_time, at_seq_by_producer: Map<producer_id, int>}`             | yes      | Late joiners, replay keyframes          |
| `ui.pacing.v1`              | 1       | `{achieved_speed, wall_elapsed, wall_clock_epoch}`                                                       | no       | Achieved-speed readout, C2 mapping      |
| `stream.control.v1`         | 1       | `{kind: "heartbeat"\|"overflow"\|"resync", coalesced: int, dropped: int, producer_id}`                   | no       | Stream health strip                     |

The "Recorded" column defines the exclusion list `BG-DET-UI-1` uses: a schema marked no is never written into a bundle, so its values never reach a byte comparison. Two schemas carry values a wall clock or one transport connection produced, so recording them would put a number into the bundle that changes between runs for reasons the seed does not control.

`sim.clock_tick.v1` lost three fields. `achieved_speed` and `wall_elapsed` are wall-derived and moved to `ui.pacing.v1`; `wall_clock_epoch` moved to the provenance sidecar and is republished on `ui.pacing.v1` for the C2 readout. What remains is the sim time and the requested compression, both of which are inputs to the run rather than measurements of the machine running it.

`ui.snapshot.v1` and `ui.pacing.v1` are produced by the dashboard server, and `ui.snapshot.v1` also by the recorder. They are the only two events this section produces on the read path. The snapshot exists so that a browser joining at minute 240 does not have to replay 240 minutes, and it carries `ViewStateCanonical` rather than the full `ViewState` so that applying it can never overwrite the reader's theme, contrast, motion or shortcut preferences with the server's defaults. One subset definition serves the snapshot contract, the determinism hash, and the golden view-state files.

### 4.2 Published

One schema, discriminated by `kind`, so the command surface is a single contract:

`ui.command.v1`

```json
{
  "kind": "set_speed",
  "actor": { "type": "human", "id": "local-operator" },
  "sim_time": 12345.5,
  "command_id": "c-0007",
  "payload": {}
}
```

The envelope carries `sim_time` and no wall-clock field. An audited command is written to the append-only event log, C1 requires that log to be byte-identical from a seed, and a wall-clock stamp inside it makes that false by construction. The operator-facing audit strip still needs a human-readable time, so the server writes the wall reading for each `command_id` to the provenance sidecar and the strip joins the two when it shows the row. D-02 again: the value is legal to read, illegal to put in the payload.

`command_id` is assigned by the browser as `c-%04d` from a per-session counter, which makes retries idempotent without a random identifier.

| `kind`                             | Payload                                         | Mode   | Handled by | Effect                                                                    | Audit                     |
| ---------------------------------- | ----------------------------------------------- | ------ | ---------- | ------------------------------------------------------------------------- | ------------------------- |
| `set_speed`                        | `{speed: float \| "max"}`                       | both   | server     | Live: clock service sets compression. Replay: browser sets its multiplier | yes in live, no in replay |
| `pause` / `resume`                 | `{}`                                            | both   | server     | Same split as `set_speed`                                                 | yes in live, no in replay |
| `step`                             | `{steps: int}`                                  | both   | both       | Advances one step, defined below                                          | yes in live, no in replay |
| `seek`                             | `{sim_time: float}`                             | replay | browser    | Moves the playhead                                                        | no                        |
| `ack_finding`                      | `{finding_id}`                                  | live   | server     | `state` to `acknowledged`                                                 | yes                       |
| `shelve_alarm`                     | `{key: AlarmKey, duration_s: int, reason: str}` | live   | server     | Shelf entry with expiry                                                   | yes, reason mandatory     |
| `unshelve_alarm`                   | `{key: AlarmKey}`                               | live   | server     | Returns the key to the list                                               | yes                       |
| `ask_agent`                        | `{text: str, context: {sim_time, entity_ref?}}` | live   | server     | Agent turn                                                                | yes                       |
| `approve_whatif` / `reject_whatif` | `{request_id, note?}`                           | live   | server     | E5 flow-back                                                              | yes, always               |
| `set_pref`                         | `{key, value}`                                  | both   | browser    | Theme, contrast, motion, palette, shortcuts                               | no                        |

Every `kind` with "audit: yes" is written to the append-only event log with the actor, meeting the audit-trail expectations in 6a11 and E5. A `live`-only command issued in replay mode is refused by the browser with the labelled message "this is a recorded demo, that control is live-only", never sent, and never silently ignored. `E2E-REPLAY-6` asserts the refusal for every `live` row in the table, so a command added later without a replay answer fails the build.

One step, defined so that `E2E-DASH-3` is implementable in both modes. In replay mode a step is one recorded frame, and `steps` counts frames. In live simulation mode there are no frames, only the next scheduled event on the SimPy queue, so a step is one advance of the sim clock to the next event time and `steps` counts events. The button label follows the mode: "Step frame" in replay, "Step event" in live. Live production mode has no step at all and the control is disabled with an explanation, because stepping a real plant is not a thing a dashboard gets to do.

Transport: `POST /api/command` with the envelope as JSON, in live mode only. Response is `202` plus the assigned `(producer_id, seq)`, or `422` with the schema validation error. Not WebSocket: commands are rare, idempotent by `command_id`, and POST keeps the surface auditable and testable with `curl`. In replay mode there is no server and no POST; `TF.transport` binds `ReplayTransport`, which routes `browser`-handled commands locally and refuses the rest. Recorded as Open Question OQ-8 for the E5 approval latency case.

### 4.3 Contract tests (C3)

This is a defining table under the id rule of section 7, so a contract test named anywhere in this document appears here.

| Id        | Subject           | Assertion                                                                                                                                                                         |
| --------- | ----------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `CT-UI-1` | Golden envelopes  | For every schema in section 4.1, a golden envelope fixture in `/schemas/<type>/examples/` validates and applies cleanly, and the resulting `ViewState` diff matches a golden file |
| `CT-UI-2` | Severity enum     | The severity enum in `/schemas/lss/finding.v1.json` matches the dashboard's severity table. A value present in one and absent from the other fails CI                             |
| `CT-UI-3` | Command enum      | The `kind` enum in `ui.command.v1`, the server's command dispatch table, and the browser's command builders all carry the same set                                                |
| `CT-UI-4` | Additive-only     | A new minor version of any consumed schema still validates the previous version's example fixtures against the UI's reader                                                        |
| `CT-UI-5` | Envelope ordering | Sorting a shuffled fixture log by `(sim_time, producer_id, seq)` reproduces the recorded order exactly, and the sort is stable across a shuffled input (D-07)                     |

`CT-UI-2` is the row that pays for itself: it stops a severity value added in a later phase from reaching the UI as an unstyled blank.

### 4.4 Replay bundle format

`replay.manifest.v1`, the on-disk contract for E1. The shape, with types rather than sample values, because every numeric field below is measured or derived by `record` and no number in a shipped manifest is ever typed by a human:

```json
{
  "schema": "replay.manifest.v1",
  "run": {
    "run_id": "<uuid5 hex, derived per section 3.2>",
    "seed": "<int>",
    "config_hash": "<sha256 hex>",
    "schema_snapshot": "<sha256 hex>",
    "scenario_id": "<str>",
    "profile": "<micro_fulfillment | mid_market_3pl | enterprise_network>",
    "sim_epoch": "<ISO 8601, a config value>",
    "twinflow_version": "<semver>",
    "synthetic": "<fully_synthetic | hybrid_hil>"
  },
  "tier": "<view_model | full_tap>",
  "sim_time_range": ["<float>", "<float>"],
  "frame_rate_hz": "<float>",
  "frame_encoding": {
    "kind": "json_patch",
    "spec": "RFC 6902",
    "ops_used": ["add", "remove", "replace"],
    "base": "previous_frame_of_same_schema"
  },
  "producers": ["<producer_id>", "..."],
  "counts": {
    "frames": "<int>",
    "envelopes": "<int>",
    "findings": "<int>",
    "devices": "<int>",
    "agent_turns": "<int>"
  },
  "chunks": [
    {
      "path": "frames/0000.ndjson.gz",
      "sim_time_range": ["<float>", "<float>"],
      "seq_ranges": { "<producer_id>": ["<int>", "<int>"] },
      "envelopes": "<int>",
      "bytes": "<int, measured>",
      "sha256": "<hex>"
    }
  ],
  "keyframes": [
    {
      "path": "keyframes/0000.json",
      "sim_time": "<float>",
      "at_seq_by_producer": { "<producer_id>": "<int>" },
      "sha256": "<hex>"
    }
  ],
  "cassette": {
    "path": "cassette.json",
    "sha256": "<hex>",
    "entries": "<int>"
  },
  "media": { "whatif": "media/whatif.webm", "voice": "media/voice.webm" },
  "questions": [
    {
      "id": "q1",
      "sim_time": "<float>",
      "text": "<str>",
      "turn_ids": ["<str>"]
    }
  ],
  "schema_versions": { "lss.finding": 1, "twin.line_state": 1 },
  "budget": { "bytes_gz": "<int, measured>", "limit_bytes_gz": "<int, config>" }
}
```

#### 4.4.1 Frame encoding

A chunk is gzipped NDJSON. Each line is one JSON object and is one of two things:

- A full envelope, for every schema that is not a periodic frame: findings, alarm state, agent turns, what-if results, approval requests, bottleneck verdicts.
- A frame delta, for the two schemas emitted every tick, `twin.line_state.v1` and `sim.clock_tick.v1`. The delta is a JSON Patch document as defined by RFC 6902 (IETF Standards Track, April 2013), restricted to the `add`, `remove` and `replace` operations, applied to the previous frame of the same schema within the same chunk. `move` and `copy` are excluded because they make a patch order-sensitive in ways that complicate the reverse-apply a backward step needs; `test` is excluded because a failing `test` would abort a replay the integrity hash already covers.

The first line of every chunk is a full envelope for each frame schema, so a chunk is self-contained and a seek never has to read the chunk before it. That is what makes the seek cost bound in `SEEK-1` true rather than approximate.

Delta encoding is not an optimisation, it is the reason the size budget is reachable at all. A full `twin.line_state.v1` frame for a facility with S stations and E edges is O(S + E) fields; between two frames a quarter second apart, a handful of those fields move. The budget gate in section 7.4 measures the outcome and the manifest records it, so if the delta assumption stops holding the build says so instead of quietly shipping a bundle nobody will download.

#### 4.4.2 Counts, and how they relate

`frames` counts ticks. `envelopes` counts lines across all chunks. The second is always larger than the first, because every tick contributes two frame deltas and the run also emits findings, alarm state, device health, agent turns and what-if results between ticks. A manifest whose `envelopes` did not exceed `frames` would be describing a run in which nothing happened, and `T-MANIFEST-1` asserts the inequality along with the per-producer `seq_ranges` covering every envelope in the chunk exactly once.

Sequence ranges are per producer because `seq` is dense per `(run_id, producer_id)` (D-07). A single range would be describing a counter that does not exist.

#### 4.4.3 Bundle tiers

E1's requirement text is "record a full simulated shift (telemetry, findings, agent transcript)". The view-model tier below is what the viewer loads; it is not the whole of that requirement, so the requirement is tiered rather than narrowed, and both tiers are produced by the same recorder.

| Tier         | Contents                                                                                                                                                                                     | Produced                 | Published                                                                      | Milestone          |
| ------------ | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------ | ------------------------------------------------------------------------------ | ------------------ |
| `view_model` | View-model frames at `frame_rate_hz`, per-device aggregate series at `telemetry_aggregate_seconds`, full-rate evidence windows around every finding, findings, alarm state, agent transcript | Every `record` run       | Deployed to Pages, loaded by the viewer                                        | E1                 |
| `full_tap`   | Every raw device envelope at its native publish rate, same run, same seed, same chunk and keyframe layout                                                                                    | `record --tier full_tap` | Attached to the release as a downloadable artifact, never loaded by the viewer | `M-REPLAY-FULLTAP` |

The reader who wants the raw tap gets the raw tap. The reader who wants to watch a factory run in a browser is not made to download hundreds of megabytes of Sparkplug NDATA to do it. `M-REPLAY-FULLTAP` is sequenced in section 8, not dropped, and it reuses the recorder, the chunk format, the keyframe layout and the integrity hashes without change; the only difference is which subscription the recorder opens.

#### 4.4.4 Rules

- Chunks are gzip with `mtime=0`, no `FNAME` field, and a fixed compression level, so the bundle is byte-reproducible on a pinned platform (C1, D-05 tier one).
- JSON is canonicalised before hashing and before writing, by RFC 8785 as section 5.3 states: properties sorted on UTF-16 code units, no insignificant whitespace, ECMAScript number serialisation. Sorted keys are D-03 applied to serialisation, and they are why `V5` can claim stability under insertion order.
- One keyframe per chunk boundary, so a seek loads exactly one keyframe plus at most one chunk.
- A keyframe holds `ViewStateCanonical`, not `ViewState`, so applying one never overwrites reader preferences and never injects a stale transport-health reading.
- `provenance.json` holds `generated_at`, `wall_clock_epoch`, the per-`command_id` wall times, the unbucketed tool durations, the CI run URL, the runner image digest, the platform fingerprint and the resolved package versions. It sits outside the manifest so the manifest stays deterministic. This is the presentation-layer instance of D-01's hashed core and provenance sidecar split.
- `dataset_card.md` accompanies the bundle with generation parameters, seed, config hash, licence, and the synthetic-data declaration, applying the E25 dataset-card discipline to the demo artifact.
- Every chunk carries a sha256. The viewer checks each chunk after fetch and shows a tamper warning on mismatch, which is a small, honest echo of E35.
- The committed manifest fixture at `/schemas/replay/examples/manifest.v1.json` is generated by `just demo-bundle --manifest-only` and checked by `readme-check`-style diff in CI, the same discipline the README metrics block uses. No manifest example in this repository is hand-written, which is why this section shows the shape and not a set of plausible numbers.

Seek algorithm (`SEEK-1`): binary search `chunks` by `sim_time_range` for target `t`; load the keyframe whose `sim_time` is the greatest value not exceeding `t`; apply frames from that keyframe's `seq` until `sim_time >= t`. Cost is bounded by one keyframe plus one chunk regardless of how far the seek travels.

---

## 5. Behaviour

### 5.1 One view layer, two data sources

This is the design thesis of the section and it mirrors the locked dual-mode DST decision. The kernel runs one codebase in production mode and simulation mode behind CLOCK, RNG, NETWORK, and STORAGE seams. The browser does the same thing with two seams:

- `TF.transport`: `LiveTransport` (the browser's `EventSource` API over SSE, commands over POST) or `ReplayTransport` (fetch manifest, chunks, keyframes; `browser`-handled commands run locally, `server`-handled commands are refused with a labelled message, per the mode columns in section 4.2).
- `TF.clock`: `ServerClock` (renders `sim.clock_tick.v1`, holds no timer) or `ReplayClock` (owns a `requestAnimationFrame` loop, a virtual sim time, and a speed multiplier).

Everything above the seams (`TF.store`, `TF.panels`, `TF.render2d`, `TF.render3d`, `TF.a11y`) is identical in both modes and does not know which mode it is in. Mode selection happens once at boot:

```
if (location.search has "bundle") -> replay
else if HEAD /api/stream returns 200 -> live
else if ./replay/manifest.json exists -> replay
else -> offline placeholder with instructions
```

Consequence: the GitHub Pages viewer and the live dashboard are the same file. There is no second UI to keep in sync, no drift between what the reader sees online and what they see after `docker compose up`, and every panel added in phase 9 appears in the replay demo for free. That property is the reason E1 is cheap enough to pull forward to just after Phase 2.

### 5.2 The single file

`index.html`, one file, no build step, no package manager, no CDN. Section 5.2.3 states that as a decision, names the two mechanisms in this document that are its grounds, and records what it costs. Section 5.2.4 states what a page with no build step is allowed to depend on.

Structure:

```
<head>
  <style id="tf-tokens">   :root { --tf-... : oklch(...); } ... </style>
  <style id="tf-layout">   grid, panels, responsive breakpoints </style>
  <style id="tf-a11y">     focus rings, prefers-reduced-motion, prefers-contrast, forced-colors </style>
  <style id="tf-font">     @font-face with a base64 woff2 variable subset </style>
</head>
<body>
  <a class="tf-skip" href="#tf-main">Skip to dashboard</a>
  <header>...</header>
  <main id="tf-main">...</main>
  <script id="tf-core">     TF namespace, util, hash, canonical JSON  </script>
  <script id="tf-schema">   envelope validation (shape checks, not full JSON Schema) </script>
  <script id="tf-store">    apply(), subscribe(), hash()  </script>
  <script id="tf-clock">    ServerClock, ReplayClock  </script>
  <script id="tf-transport">LiveTransport, ReplayTransport </script>
  <script id="tf-alarms-view">presentation of groups, dedupe counts, shelf countdown; no grouping decisions </script>
  <script id="tf-a11y">     severity table, live-region controller, keyboard map, prefs </script>
  <script id="tf-panels">   panel registry </script>
  <script id="tf-render2d"> SVG plan view, tables, sparklines </script>
  <script id="tf-chat">     transcript, grounding chips, tool trace </script>
  <script id="tf-boot">     mode detection, mount, error boundary </script>
</body>
```

The alarm block is named `tf-alarms-view` so the language boundary is visible in the file itself. Every grouping, dedupe, chatter and flood decision is made server-side in `twinflow-alarms` and arrives in `alarm.state.v1`; the browser renders what it received and counts down shelf timers. Section 5.6 states the split in full.

Each `<script>` is a classic script containing an IIFE that assigns one namespace onto `window.TF`. Not ES modules, for two reasons of unequal strength, stated in order.

The strong reason is testability. A classic script is a plain string of source that `node:vm` can evaluate directly, so `tools/extract_scripts.mjs` pulls each block out of `index.html` and the unit tier runs the real shipped source rather than a copy maintained beside it. An ES module graph would need either a bundler or a loader shim, and either one puts a build step between the file on disk and the file under test, which is the thing component 8 forbids.

The weaker reason is `file://`, and it is stated with its limits because the obvious version of it is false. Double-clicking `index.html` never produces a playing demo, whatever the script type: `fetch()` against a `file:` URL is blocked in Chromium, so the manifest, chunks and keyframes cannot load. What classic scripts buy is that the page still boots, still renders, and still explains itself. `T-FILE-1` asserts exactly that documented degraded behaviour, loading the page from a `file:` URL and requiring the offline placeholder with its two-line instruction to appear, no white screen and no console-only failure. Claiming more than that would be claiming something no test covers.

The rejected alternative (blob-URL import map) is recorded in ARCHITECTURE.md with the testability reason.

Boot order is asserted: `tf-boot` checks that every required namespace exists and renders a legible failure page listing what is missing if one does not. A silent white page is not acceptable.

Budgets, enforced by test `T-SIZE-1`:

- `index.html` uncompressed: 400 KB maximum, of which the base64 font subset is at most 60 KB.
- Zero requests to any origin other than the page's own, asserted by request interception in Playwright.
- No `eval`, no `new Function`, no inline event handler attributes, so the page runs under `script-src 'nonce-...'` with no `unsafe-inline` for scripts.

#### 5.2.1 Styling under a strict CSP

The policy carries no `'unsafe-inline'` for styles, and a nonce does not reach a `style` attribute: W3C Content Security Policy Level 3 section 6.1.15 defines `style-src-attr` as the directive governing style attributes, with the fallback chain `style-src-attr`, `style-src`, `default-src` (retrieved 2026-08-09, HTTP 200, `https://www.w3.org/TR/CSP3/`). With `style-src 'nonce-{n}'` and no `style-src-attr`, any `style` attribute is blocked. Two rules follow and both are lint-enforced:

- Geometry is expressed as SVG presentation attributes, never as CSS. Station rectangles carry `x`, `y`, `width`, `height`, `transform`; edge polylines carry `points`; the scale-to-fit is a single `viewBox`. Presentation attributes are markup, not style, and CSP does not touch them. This is why the per-frame regeneration of the plan view in section 5.4 is legal.
- Dynamic styling that is genuinely style goes through the CSSOM: `element.style.setProperty(name, value)` and `element.classList`. `setAttribute('style', ...)` is banned outright, because setting the attribute is what triggers the `style-src-attr` check while the property setter does not.

`just lint-colour` grows a second rule that greps the extracted scripts for `setAttribute(` with a first argument of `'style'` and fails on any hit, so the ban is a build failure rather than a convention.

#### 5.2.2 Two CSP delivery paths

The dashboard server and the Pages site are the same file on two hosts with different capabilities, so the policy ships twice.

| Path               | Delivery                                                                 | Policy                                                                                                                                                                                                       | Notes                                                                                                             |
| ------------------ | ------------------------------------------------------------------------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ | ----------------------------------------------------------------------------------------------------------------- |
| Dashboard server   | `Content-Security-Policy` response header, nonce per request             | `default-src 'none'; script-src 'nonce-{n}'; style-src 'nonce-{n}'; connect-src 'self'; img-src 'self' data:; font-src data:; media-src 'self'; base-uri 'none'; form-action 'none'; frame-ancestors 'none'` | Full policy, every directive enforced                                                                             |
| GitHub Pages build | `<meta http-equiv="Content-Security-Policy">`, first element in `<head>` | Same directive set with `'nonce-{n}'` replaced by a build-time nonce baked into both the meta tag and every `<script>` and `<style>` tag, and with `frame-ancestors` omitted                                 | `frame-ancestors` MUST be ignored in a meta-delivered policy (CSP3 section 6.4.2), so stating it would be theatre |

GitHub Pages is a static file host and gives a repository no way to set a response header on its own content. A `HEAD` request against a Pages-served origin on 2026-08-09 returned HTTP 200 with no `Content-Security-Policy` header, which is what the gate measures rather than what this paragraph asserts. `BG-CSP-2` records the response headers of the deployed Pages URL, requires the meta policy to be present and parsed, and requires the report to name every directive that is unavailable on that path. If GitHub ever gains header control the gate keeps passing and the report gets shorter.

Clickjacking protection on the Pages path does not come from CSP. The published site has no authenticated action, no credential field and no state a framing page could steal, so the residual risk is a stale screenshot in someone else's frame. SECURITY.md says that in one sentence rather than implying a protection the platform cannot deliver.

#### 5.2.3 No build step, stated as a decision

Component 8 says "single-file, no build step". A component library of the kind a reader expects in 2026, React plus a component kit plus a motion library, needs a bundler, a package manager and a compile step. Both cannot hold, so one is argued away here rather than quietly dropped. The rule stays and the library goes, on two mechanisms already in this document.

The first is the browser unit tier of section 5.2. It runs by extracting the shipped `<script>` blocks out of `index.html` and evaluating them in `node:vm`, which works because a classic script is a plain string of source. A bundle is not. The tier would run against a compiled artifact, and the file under test would stop being the file on disk.

The second is section 5.1. The live dashboard and the hosted replay are the same file behind `TF.transport` and `TF.clock`, which is what makes every panel added in a later phase appear in the public demo at no cost. A toolchain on one side of that pair creates a second viewer, and a second viewer carries its own accessibility gates, its own visual-regression goldens and its own severity table, each kept honest twice.

What the decision costs, with nothing softened:

- Between fifty and sixty interface elements are hand-written. `docs/design/ui-direction.md` section 12.5 lists them one by one and its section 12.4 counts 60 hand-written items of 65 total, while its own summary sentence rounds the figure to about fifty.
- Two of them are hard rather than tedious: the virtualised grid that keeps `aria-rowcount` honest at 500 devices (section 5.3), and roving focus across the plan view, the fleet table and the findings list (section 5.12.3). Neither is recovered by a component kit, which is why this cost is real whatever the architecture.
- Spring physics is unavailable without a motion library, so motion is CSS transitions and the Web Animations API and nothing else.
- Browser code carries no compile-time type check. The property tier of section 7.2 is the mitigation, and it is weaker than a typed build.
- Review cost per element is higher, because a hand-written combobox is a correctness surface that a vendored one has already paid for.

`shadcn` and the React component corpora are out, and that is a decision rather than an oversight. A React component cannot be vendored into a hand-written single file, and rewriting one by hand produces a new file that owes the original nothing but the idea, which is not vendoring. Their licences are not the obstacle and most of that corpus is MIT. The architecture is. Section 7.3.4 records what is vendored and section 7.3.5 records the sources that ship no bytes.

This decision covers the 2D dashboard, which is where component 8 attaches the constraint. Whether the 3D view inherits it stays open as OQ-5.

#### 5.2.4 What the page is allowed to depend on

A page with no build step is only as good as the platform under it, so the rule for depending on a platform feature is stated rather than assumed. A feature at Baseline "widely" may carry structure. A feature below that carries polish only, behind an `@supports` block or a capability check, and the page is complete without it.

Four features this interface wants sit below "widely". Each was read from `https://api.webstatus.dev/v1/features/<id>` on 2026-08-09, HTTP 200 for each, and the status is that project's own: `popover` (newly, low date 2025-01-27), `view-transitions` (newly, 2025-10-14), `light-dark` (newly, 2024-05-13), and `text-wrap-balance` (newly, 2024-05-13). Each carries polish only. `popover` sits behind a scripted fallback on grounding chips and filter menus, `view-transitions` runs on panel and view swaps and is off under reduced motion, `light-dark` sits behind the `@supports` fallback block section 5.12.2 already generates, and `text-wrap-balance` runs on headings and the verdict caveat.

`T-PROGRESSIVE-1` holds the line. It renders every panel with those four made unavailable and asserts that every control still works.

### 5.3 Store and rendering

`TF.store.apply(state, envelope)` is pure, total, and returns a new object with structural sharing of untouched sub-maps. Unknown schema names increment `state.stream.unknown[schema]` and are otherwise ignored, so a newer producer never breaks an older viewer (C3 additive-only, enforced from the consumer side).

Canonical serialisation, used by `hash()` and by the recorder, is the JSON Canonicalization Scheme of RFC 8785 (IETF Independent Submission, Informational, June 2020), not a rule invented here. JCS fixes the three choices that would otherwise differ between the browser and the recorder: object properties sort by their UTF-16 code units, whitespace between tokens is removed, and numbers serialise by the ECMAScript rule that yields the shortest decimal string round-tripping to the same double. Every map the store holds is serialised in that sorted order, never in insertion order and never from a `Set` (D-03). Insertion order in this store depends on arrival order, and arrival order can differ between a live run and a replay of the same run, so hashing insertion order would make `P-BUNDLE-ROUNDTRIP` fail for a reason unrelated to correctness.

The sort key is the one place a plausible-looking local rule silently breaks the cross-language hash, so it is stated rather than assumed. RFC 8785 section 3.2.3 sorts on UTF-16 code units. JavaScript string comparison already does that. Python's `sorted()` over `str` sorts by Unicode code point, and the two orders differ for any key containing a character above U+FFFF, because a supplementary character encodes as a surrogate pair whose first unit is below U+E000. So the Python side sorts on `key.encode("utf-16-be")` and the browser side sorts natively, and `VAL-GATE JCS-1` checks both against the RFC's own published sorting test data. Without that rule `T-STORE-3` would pass on ASCII fixtures and fail the first time a station label carried an emoji or a rare ideograph.

Rendering is explicit, not virtual-DOM. Each panel exposes `mount(root)` once and `apply(prev, next)` per frame, and must be idempotent: calling `apply(s, s)` produces no DOM mutation. Test `T-RENDER-1` asserts idempotence by counting MutationObserver records.

Emphasis is marked, not decided per panel. At most one element inside a panel container carries the `data-tf-isolated` attribute, because two differentiated elements inside one container cancel each other and the container then has no focal point at all. Which element carries it is a placement question per container, and `docs/design/ui-direction.md` section 5.5 answers it container by container. `T-ISOLATION-1` counts the marked elements per container and fails on a second one, which is the failure that arrives by accretion as panels are added.

Frame pipeline:

1. Transport delivers a batch of envelopes.
2. `store.applyBatch` folds them into one new state.
3. One `requestAnimationFrame` callback runs every subscribed panel's `apply`.
4. Panels write DOM only inside that callback. No panel reads layout after writing (no forced reflow).

Budget `BG-PERF-1`, on a fixed workload of 500 devices, 2000 findings and 4 Hz frames, split into two legs for the reason section 5.13 gives for the 3D budget. The CI leg asserts no absolute time: it fails when p95 scripting time per frame exceeds 1.25 times the committed baseline for the same runner image digest, because a shared runner's absolute speed is not a property of this code. The workstation leg is the absolute one, p95 scripting time per frame at most 8 ms, and 8 ms is one third of a frame at the 4 Hz workload's 250 ms budget rather than a figure taken from anywhere else. Both legs write the measuring machine's CPU model, browser build and OS build into `artifacts/ui-perf.json`, and a measurement with no machine block is not published. The header carries an optional perf overlay (toggle `P`) showing apply-time p50/p95 and frames per second, because a dashboard that reports its own health is more credible than one that does not.

Long lists (fleet table, findings stream) are virtualised with a windowed renderer. Virtualisation and screen readers conflict, so the virtualised containers use `role="grid"` with `aria-rowcount` set to the full count and `aria-rowindex` on rendered rows, which is the pattern that keeps assistive technology's row count honest.

### 5.4 Live line state panel

An SVG plan view generated from `facility.yaml` geometry. Stations are rectangles at their configured position and footprint, scaled to fit by the root `viewBox`, with a `level` selector when the facility has mezzanines. Edges are polylines. Every per-frame geometry write is a presentation attribute (`x`, `y`, `width`, `height`, `points`, `transform`) and never a `style` attribute, for the CSP reason in section 5.2.1.

Per station: label, state glyph, WIP count, a utilisation bar with a numeric label, and a bottleneck marker when applicable. The bottleneck marker is a heavy dashed outline plus the text "BOTTLENECK" plus a distinct glyph, never colour alone.

Flow animation on conveyor edges uses a dashed stroke offset animation. Under `prefers-reduced-motion: reduce` or the in-UI motion preference, the animation is replaced by a static arrow marker plus a numeric flow rate, and above 4x clock speed it is disabled regardless of preference because it stops being readable.

Every station rectangle is a focusable element (`tabindex` roving within the plan view, arrow keys move between stations in reading order, Enter opens the station detail drawer). The plan view also has a table equivalent (`Toggle: plan / table`) so nothing in the graphic is unreachable by a screen reader. That table is the same data, not a summary.

Alt text: the SVG carries `role="img"` and an `aria-label` regenerated each frame with a one-sentence summary ("12 stations, 1 bottleneck at Putaway 2, 3 stations blocked"), throttled so it does not spam the accessibility tree.

### 5.5 Fleet health panel

A sortable, filterable, virtualised table. Columns: device id, type, UNS topic (truncated with a title and an expand), state, health score, FMEA RPN, last seen (sim time and sim-time-ago), firmware, badges.

Badges, each with the phase that makes it renderable, because a badge whose data source has not landed is a badge that never appears:

| Badge           | Source                                                   | Phase                                          |
| --------------- | -------------------------------------------------------- | ---------------------------------------------- |
| `PHYSICAL`      | `fleet.device_health.v1.physical` (E47)                  | Schema field from P1, populated at P6 with E47 |
| `TIER-1 EDGE`   | Compute-placement tier on the device record (E36)        | P6, with E36                                   |
| `CERT EXP <n>d` | Client certificate expiry on the device record (6c mTLS) | P5, with the mTLS work                         |

Until its source lands, a badge is absent, not blank, and the fleet table renders no placeholder for it. Section 8 carries the P5 and P6 rows that turn each one on, so the growth of this panel is sequenced rather than assumed.

The `PHYSICAL` badge is text plus an outline shape, so it survives greyscale printing and colour blindness, which matters because that badge is the one that makes the hardware-in-the-loop demo clip legible. It is also what the header's `hybrid_hil` badge counts (section 3.2).

Row expansion loads the device's aggregate sparkline from the evidence buffer (live: an API call; replay: the aggregate series in the bundle) and shows the last five findings for that device.

Filter chips: state, type, station, `has open findings`, `degraded only`, `physical only`. Filters are reflected into the URL fragment so a filtered view is shareable.

### 5.6 Findings stream and alarm-flood protection

The findings panel is a `role="log"` list with `aria-live="polite"` and `aria-relevant="additions"`.

#### 5.6.1 Where each decision is made

One authority per decision, stated before the ingest path so the path can be read without wondering who is deciding.

| Decision                                                      | Owner                     | Delivered how                                         |
| ------------------------------------------------------------- | ------------------------- | ----------------------------------------------------- |
| `AlarmKey` computation, dedupe, `count`, `first`/`last` times | `twinflow-alarms`, server | `alarm.state.v1` and the updated `lss.finding.v1` row |
| Chatter detection and the transition count                    | `twinflow-alarms`, server | `alarm.state.v1`                                      |
| Per-role rate metering and the flood verdict                  | `twinflow-alarms`, server | `alarm.state.v1`                                      |
| Group membership and group ordering                           | `twinflow-alarms`, server | `alarm.state.v1.groups`                               |
| `display_state` for every row                                 | `twinflow-alarms`, server | `lss.finding.v1` row field                            |
| Shelf entries, expiry times, and expiry itself                | `twinflow-alarms`, server | `alarm.state.v1.shelved`                              |
| Rendering groups, meters, banners, badges                     | `tf-alarms-view`, browser | DOM                                                   |
| Shelf countdown between server updates                        | `tf-alarms-view`, browser | DOM, from the server's expiry sim time                |
| Sort order within a rendered group, and collapse state        | `tf-alarms-view`, browser | DOM, reset on `run` change                            |

The browser recomputes none of the server's decisions. It re-asserts `V9` on the state it received as a consistency check, and a violation renders a stream-integrity warning naming the two totals that disagree rather than silently correcting either. That is the difference between a check and a second implementation, and a second implementation of alarm grouping in a different language is exactly the drift this table exists to prevent.

#### 5.6.2 Ingest path per finding

1. `twinflow-alarms` receives `lss.finding.v1` and computes an `AlarmKey` of `(rule_id, entity_ref.kind, entity_ref.id)`.
2. Dedupe: a second finding with the same key inside `dedupe_window_seconds` does not create a new row. It increments `count`, extends `last_sim_time`, and updates the evidence window. The row shows `x7` and a first/last time range. `totals.ingested` still counts seven, which is what `V9a` checks.
3. Chatter detection: a key that transitions between active and clear more than `chatter_transitions` times inside `chatter_window_seconds` is badged `CHATTERING` with the transition count. Chattering alarms sort below stable ones of the same severity, because a chattering low is noise and a stable low might not be.
4. Rate metering: a rolling 10-minute sim-time count, computed separately for each role in `dashboard.alarms.roles`, from the role each finding is routed to by `dashboard.alarms.routing`. The meter renders for the role the reader has selected, with the target band at `target_rate_per_10min` and the flood line at `flood_threshold_per_10min`. Both defaults, and the one source this repository was able to read for them, are in section 5.6.3.
5. Flood mode: when a role's rolling rate crosses the flood threshold, `alarm.state.v1` adds that role to `flooding_roles` and supplies `groups`. The UI then:
   - shows a banner naming the role: "Alarm flood, picker role: N findings in the last 10 minutes, grouped into M causes";
   - switches the list to grouped mode, using the server's `groups`, with each group collapsible and showing its member count and severity histogram;
   - stops assertive announcements of individual criticals and announces a single summary instead (section 5.12.4);
   - keeps a persistent "ungrouped list" toggle so nothing is unreachable.
6. Shelving: an operator shelves a key for a duration with a mandatory reason. Shelved rows leave the main list and enter the shelf drawer with a live countdown. A shelf badge in the header always shows the shelved count and never hides at zero (it shows "0 shelved"), because an always-present counter is what stops shelving from becoming silent suppression. Shelves auto-expire and the item returns with a `RETURNED FROM SHELF` marker.
7. Suppression by design (a rule intentionally muted in config, for example a known-noisy sensor during commissioning) is shown in a separate list from shelving, with its config path and reason. The distinction between operator shelving and engineered suppression is what alarm rationalisation practice insists on, and showing both is cheap.

Invariant `V9` (section 3.7) is checked continuously in the browser in debug mode and in every property test, in both its parts: the sum of `count` over all rows equals `totals.ingested`, and the three `display_state` counts partition the rows.

Steps 2, 3, 5, 6 and 7 each have a published guideline behind them. Section 5.6.4 names which guideline, quotes it, and gives the page it was read from.

#### 5.6.3 Where the two default thresholds come from

The two configured numbers, `target_rate_per_10min: 1` and `flood_threshold_per_10min: 10`, are attributed rather than asserted, because the standards that carry the primary figures are sold and this repository has not read them (section 7.3.3).

The retrievable source is the UK Health and Safety Executive information sheet Better alarm handling, Chemicals Sheet No 6, published March 2000 (retrieved 2026-08-09, HTTP 200, `https://www.hse.gov.uk/pubns/chis6.pdf`). Citing page 37 of its reference 2, which it lists as EEMUA Publication 191, 1999, ISBN 0 8593 1076 0, that sheet states: "the long-term average alarm rate during normal operation should be no more than one every ten minutes; and no more than ten displayed in the first ten minutes following a major plant upset". HSE contributed to that guide and recommends it, which is why a regulator's sheet is the best free locator for the figures and also why it is not an independent second opinion on them.<!-- docs-lint-ok STE-01 verbatim quotation of the published source -->

Three consequences, all of which change what this section is allowed to claim.

The default target rate of one per ten minutes and the default flood line of ten per ten minutes match the two figures in that sentence. They ship at confidence tier C with the attribution above, in the config comments of section 6.2 and in `BG-ALARM-1`, and never as a bare number.

The second figure is a post-upset acceptability target in the source's own words, not a definition of the term alarm flood. ANSI/ISA-18.2-2016 carries the term and this repository has not read it, so section 7.3.3 records it as unread and OQ-13 carries the question of what it defines and at what rate. The config key keeps the name `flood_threshold_per_10min` because that is what the detector does; the claim that the name matches a standard's definition is the part that is withheld.

EEMUA Publication 191 is now in a Fourth Edition according to the publisher's own product page (retrieved 2026-08-09, HTTP 200, `https://www.eemua.org/products/publications/print/eemua-publication-191/`), and the sheet above quotes the 1999 edition. Whether the current edition keeps the figures is unread, and OQ-13 carries that too.

The same sheet supplies the sentence the whole flood-protection design exists for: at the Texaco Milford Haven refinery on 24 July 1994, "in the last 11 minutes before the explosion the two operators had to recognise, acknowledge and act on 275 alarms". That is 25 alarms a minute for the pair, against a normal-operation target of one every ten minutes. `E2E-DASH-2` injects 40 findings in 10 sim minutes, which is a mild version of the same shape, and the flood policy in section 5.12.4 is what keeps a screen-reader user from receiving that burst one announcement at a time.

The sheet also records, from page 65 of the same guide, "use about three priorities" and an example split of 5 percent high, 15 percent medium and 80 percent low. This section renders five severities because `lss.finding.v1` defines five, and a UI that collapsed the schema's enum would be hiding a distinction the producer made. The tension between a five-value schema enum and a three-priority operating recommendation is real and is Open Question OQ-14.

Finding detail drawer: title, severity triple, rule reference with a link to the LSS engine's rule documentation, evidence chart (the control chart segment with limits and the violating points marked by shape), the entity's recent history, the suggested next tool as a button that hands the agent a pre-filled question, and the SOP citation when present (E8).

#### 5.6.4 NUREG-0700 Revision 4, and what it settles

NUREG-0700 Revision 4, Human-System Interface Design Review Guidelines, is published by the United States Nuclear Regulatory Commission, Office of Nuclear Regulatory Research. Its manuscript was completed in August 2025 and its title page carries a publication date of January 2026. It was retrieved as a PDF on 2026-08-09 from `https://www.nrc.gov/docs/ML2602/ML26022A094.pdf`, HTTP 200, 5,043,444 bytes, 622 pages, and its text was extracted locally. Every guideline below was read from that file rather than from a summary of it, and every locator below is the printed page number the guideline sits on.

This matters because the two standards usually cited for alarm management, EEMUA Publication 191 and ANSI/ISA-18.2-2016, are both sold by their publishers and section 7.3.3 records that neither was read. A free, current, primary source is the difference between a design decision that is sourced and one that is asserted.

The document is written for nuclear control rooms and this is a warehouse twin. It is a source of human-factors guidance and not a conformance target, and no gate in this section claims conformance to it. Its guidelines are written in the recommending voice that this repository's word list rejects, so each quotation below carries a line escape for the prose gate.

Chapter 4 defines the alarm-processing taxonomy this section already builds. Page 4-3 states: "Four classes of processing techniques are defined: nuisance alarm processing, redundant alarm processing, significance processing, and alarm generation processing." Table 4.1 on the same page gives examples of each. Three of the four already exist here under other names, and naming the mapping is worth more than inventing a vocabulary for it.

| Processing class            | The mechanism in this section                                          | What the reader sees                                                                         | Where it is specified                         |
| --------------------------- | ---------------------------------------------------------------------- | -------------------------------------------------------------------------------------------- | --------------------------------------------- |
| Nuisance alarm processing   | Chatter detection, and suppression by design set in config             | The `CHATTERING` badge with its transition count, and the separate suppressed-by-design list | Section 5.6.2, steps 3 and 7                  |
| Redundant alarm processing  | Dedupe on `AlarmKey` inside the dedupe window, and the server's groups | The `x7` count with its first and last sim time on one row, and the group row                | Section 5.6.2, steps 2 and 5                  |
| Significance processing     | Severity rank, class rank, and per-role rate metering                  | Sort order, and the alarm rate meter with its target band and its flood line                 | This subsection, and section 5.6.2, step 4    |
| Alarm generation processing | Not built here, and not claimed                                        | Nothing. No alarm in this section is synthesised from other alarms                           | This row. No gate names it and none claims it |

Nine guidelines change a decision in this section or in another one. Each is routed to the clause it backs.

| Guideline  | Title                                             | Locator in Revision 4 | What it asks for                                                                                              | Where it lands                                             |
| ---------- | ------------------------------------------------- | --------------------- | ------------------------------------------------------------------------------------------------------------- | ---------------------------------------------------------- |
| `1.3.8-7`  | Easily Distinguishable Colors                     | Page 1-51             | Colours in a coding set stay distinguishable from each other, with a separation figure stated in CIELUV units | OQ-15, which stays open and now names the figure           |
| `1.3.8-10` | Redundant Color Coding                            | Page 1-53             | Colour coding is redundant with another cue, and the information survives monochrome rendering                | Section 5.12.1, where it is quoted                         |
| `1.3.8-12` | Red-Green Combinations                            | Page 1-53             | Red and green are not combined where that can be avoided                                                      | Section 6.4, where it is quoted and becomes a palette rule |
| `1.3.8-13` | Chromostereopsis                                  | Page 1-53             | Pure red and pure blue are not shown together on a dark background                                            | Section 6.4, where it is quoted and becomes a palette rule |
| `4.1.2-1`  | Assured Functionality Under High Alarm Conditions | Page 4-13             | Alarms needing immediate action stay rapidly detectable under every alarm loading condition                   | Section 5.6.2 step 5, and section 5.12.4                   |
| `4.1.2-2`  | Alarm Reduction                                   | Page 4-13             | Processing cuts the message count during off-normal conditions, from a no-processing baseline                 | Section 5.6.2, steps 2 and 3                               |
| `4.1.3-1`  | Prioritization Criteria                           | Page 4-15             | Alarms are ranked by urgency and by challenge to safety, with the highest safety significance ranked highest  | The class rank below, and section 5.12.1                   |
| `4.1.3-2`  | Access to Suppressed Alarms                       | Page 4-16             | What suppression leaves off the screen stays reachable                                                        | Section 5.6.2, steps 5 to 7                                |
| `4.1.3-3`  | Filtered Alarms                                   | Page 4-16             | Redundant and lower-priority alarms are suppressed and retrievable rather than deleted                        | Section 5.6.2 step 2, and invariant `V9a`                  |

Guideline 4.1.2-1 reads: "The alarm processing system should ensure that alarms that require immediate action or indicate a threat to plant critical safety functions are presented in a manner that supports rapid detection and understanding under all alarm loading conditions."<!-- docs-lint-ok * verbatim quotation of NUREG-0700 Revision 4, whose wording is not editable -->
That is why flood mode in section 5.6.2 step 5 reduces what competes for attention and never what is reachable, and why the announcement policy of section 5.12.4 keeps announcing the flood state instead of going quiet. The direction page's section 6.3 places a full-width safety band for the same reason.

Guideline 4.1.2-2 reads: "The number of alarm messages presented to the crew during off-normal conditions should be reduced by alarm processing techniques (from a no-processing baseline) to support the crew's ability to detect, understand, and act upon all alarms that are important to the plant condition within the necessary time."<!-- docs-lint-ok * verbatim quotation of NUREG-0700 Revision 4, whose wording is not editable -->
Dedupe and chatter detection are that reduction. The same guideline states the limit of its own guidance: "Since there is no specific guidance on the degree of alarm reduction required to support operator performance, the designer should evaluate the system with operators to assess the effectiveness of the alarm reduction process."<!-- docs-lint-ok * verbatim quotation of NUREG-0700 Revision 4, whose wording is not editable -->
So no gate here claims a reduction ratio, and `BG-ALARM-1` checks the detector rather than a figure.

Guideline 4.1.3-2 reads: "When alarm suppression is used, the user should be able to access the alarm information that is not displayed."<!-- docs-lint-ok * verbatim quotation of NUREG-0700 Revision 4, whose wording is not editable -->
Four things in section 5.6.2 exist for that sentence: the shelf badge that renders "0 shelved" rather than hiding at zero, the mandatory reason and live countdown on every shelf entry, the `RETURNED FROM SHELF` marker at expiry, and the ungrouped-list toggle that stays one control away in flood mode.

Guideline 4.1.3-3 reads: "Alarms that are considered redundant or lower priority should be suppressed (where users can retrieve them) rather than filtered."<!-- docs-lint-ok * verbatim quotation of NUREG-0700 Revision 4, whose wording is not editable -->
Dedupe here folds a repeat into a `count` and never drops an ingest event, which is that distinction exactly. `V9a` is the law that keeps it true, and it is the reason dedupe cannot hide a fact while claiming to hide only noise.

Prioritisation, in this section, is two ranks and not one. Guideline 4.1.3-1 reads: "Alarm messages should be presented in prioritized form to indicate urgency (immediacy of required action) and challenges to plant safety."<!-- docs-lint-ok * verbatim quotation of NUREG-0700 Revision 4, whose wording is not editable -->
Its additional information adds: "The selected prioritization scheme should be logical such that those alarms of the highest safety significance receive the highest priority and such that the prioritization appears reasonable to users."<!-- docs-lint-ok * verbatim quotation of NUREG-0700 Revision 4, whose wording is not editable -->
The severity enum answers how bad and it does not answer bad at what. A critical throughput finding and a critical safety finding both render CRITICAL, and ranking those two as equals is what that guideline asks a design not to do.

`finding_class` is derived in the view model from the `kind` enum already carried on `lss.finding.v1`. Nothing new is published, `/schemas` is unchanged, and the derivation belongs to the presentation layer.

| Class       | `class_rank` | `kind` values it covers                                                                             |
| ----------- | ------------ | --------------------------------------------------------------------------------------------------- |
| safety      | 1            | `safety`                                                                                            |
| security    | 2            | `security`                                                                                          |
| quality     | 3            | `spc_violation`, `capability_shortfall`, `msa_failure`, `sop_violation`, `process_mining_deviation` |
| reliability | 4            | `fleet_health`                                                                                      |
| fidelity    | 5            | `twin_divergence`                                                                                   |
| other       | 6            | `other`                                                                                             |

The findings stream sorts by `(class_rank, severity_rank, chattering, -last_sim_time, finding_id)`, which is the general form of the chattering rule in section 5.6.2 step 3. A medium safety finding sorts above a critical quality finding, and the class word renders in the row beside the severity word so the ordering is on screen rather than inferred. The class rank is a presentation ordering and never a severity rewrite: the severity the producer emitted is the severity that renders. `P-CLASS-ORDER` asserts the totality of the map, the untouched severity, and the ordering, and any of the three can fail on its own.

Whether this ranking belongs in the view or in `twinflow-alarms` is a real fork and it is not settled here. Publishing the class on `alarm.state.v1` would make the ordering testable server-side and would put safety ranking inside the brick a controls engineer adopts alone, at the cost of a schema field. OQ-19 on the direction page carries it, and OQ-1 already names `alarm.state.v1` as the merge point if the LSS section claims the same ground.

Three things this document does not settle, each checked in the extracted text rather than assumed. It carries no alarm rate figure, so the two defaults of section 5.6.3 stay attributed to the HSE sheet and OQ-13 stays open on the numbers. It fixes no count of priority levels, so the five-against-three fork in OQ-14 stands. Its one published colour separation figure, in guideline 1.3.8-7, is stated in CIELUV units and not in CIEDE2000, so it does not move `BG-SEP-1` into section 7.3.1, and OQ-15 now records the figure and what using it would take.

#### 5.6.5 Focus stability while the list moves under a reader

A list that reorders under a keyboard reader is the defect this panel is most likely to ship, because it appears only under load and never in a screenshot. Three rules keep the reader's place, and all three are view-level.

- No arriving envelope moves focus. Arrival is announced through the polite live region of section 5.12.4, and nothing in the stream calls `focus()` in response to an envelope.
- The stream container holds DOM focus and carries `aria-activedescendant` pointing at the current row, so a row that re-ranks or unmounts cannot take focus with it. Row identity is `finding_id` and nothing else, so a row keeps its DOM node across a rank change.
- While focus is inside the list, reordering is held. Arriving and re-ranked rows queue, a control at the top of the list reads "N updates paused, press R to resume" with the count live, and the hold releases on blur.

The hold is a view-level hold and never a store-level one. Every envelope still applies, every count stays exact, and `V9` still holds, so a paused reader is behind on rendering and never behind on facts. `T-FOCUS-1` asserts the three rules together.

Whether holding the reorder is the right trade is not settled, and OQ-24 on the direction page carries it: during a flood the visible order stops being the ranked order for as long as focus stays inside the list. `T-FOCUS-1` is written against the behaviour above, and a change to that behaviour changes the test with it.

### 5.7 Bottleneck panel

Current constraint, the method that identified it, the evidence numbers (utilisation, queue length, takt versus cycle time), a confidence value, and a constraint timeline showing every shift of the constraint across the shift as a horizontal band chart. The timeline is the panel a Lean reader will stare at, because "where did the constraint move and when" is the question that drives the whole improvement cycle.

Clicking a band seeks the replay to that sim time (replay mode) or opens the historian window (live mode).

### 5.8 Agent chat and the what-if verdict card

Transcript with three roles. Each agent turn shows:

- The answer text, with every numeral wrapped in a chip carrying `data-result-id`. Hovering or focusing a chip reveals the tool, the query, and the raw result. Clicking opens the tool trace.
- A tool trace disclosure listing each call: tool name, arguments, result id, duration bucket, ok/failed.
- An abstention notice when the agent declined (E26g), rendered as an informational state and not an error, with the reason.
- An ungrounded-number warning when any numeral lacks a `result_id` (E26f). The warning is visually and textually prominent and the offending numerals are marked. Test `T-GROUND-1` asserts that a synthetic ungrounded answer renders the warning.
- Optional cost line (E45) when cost accounting is enabled.

The what-if result card is a distinct element, not a chat bubble, because it is the deliverable. Layout top to bottom:

1. Scenario label and the config diff as a `from -> to` list.
2. Throughput: baseline, scenario, absolute delta, percentage delta, unit, replication count.
3. Cost, energy, and operator impact rows when present.
4. The verdict block: test name, the assumption checks that selected it, statistic, p value, alpha, effect size with its name, confidence interval, sample sizes, and the conclusion as a text label plus a shape, never colour alone.
5. The caveat sentence.

#### 5.8.1 Numeric formatting contract for the verdict block

This card is the screenshot the repository is judged on, so the rendering of every number in it is a contract with a test, not a styling preference. `T-VERDICT-1` renders the card from a fixture with fixed producer values and compares the serialised DOM against a golden file; each rule below has at least one fixture row that fails if the rule is broken.

| Field                      | Rule                                                                                                       | Never                                                                 |
| -------------------------- | ---------------------------------------------------------------------------------------------------------- | --------------------------------------------------------------------- |
| `p_value`                  | Three significant figures when at least 0.001. Below that, the literal string `p < 0.001`                  | `0.000`, `0.0000`, or a bare `0`                                      |
| `alpha`                    | Shown beside the p value, always, as `alpha = 0.05`                                                        | Omitted because it is "the usual one"                                 |
| `statistic`                | Three significant figures, with the test's own symbol (`t`, `U`, `F`, `H`)                                 | An unlabelled number                                                  |
| `effect_size`              | The name always renders beside the value: `Hedges g = 0.42`, never `0.42`                                  | A value with no name                                                  |
| `ci`                       | Three significant figures per bound, rendered `[lo, hi]` with `lo <= hi` asserted before render            | Reversed bounds, or a bound with different precision from its partner |
| `delta_pct`                | One decimal place with an explicit sign                                                                    | An unsigned percentage                                                |
| `n_baseline`, `n_scenario` | Integers, both always shown, even when equal                                                               | A single "n" when the two differ                                      |
| `conclusion`               | Text label plus the shape from section 5.12.1, in that order                                               | Colour alone                                                          |
| Every numeral              | Wrapped in a grounding chip carrying `data-result-id`, or counted in `ungrounded_numbers` and warned (V10) | A bare numeral with no provenance                                     |

The reason for a field-level contract, rather than an assertion that the card holds a populated test block, is that a populated block can still be wrong in public. A reversed confidence interval, a p value printed as `0.0000`, and an effect size shown without its name each satisfy "populated" and each is a defect a statistically literate reader spots in the screenshot before reading a word of the README.

The GIF (section 5.14.3) ends on this card with the verdict block in frame. That is not a styling preference. It is the requirement in component 9 read literally: "demo GIF of the agent what-if flow ending in the statistical verdict".

Approval UI (E5): when `agent.approval_request.v1` arrives, the card grows an approval strip showing the autonomy tier (L1 advise, L2 recommend, L3 auto-apply within guardrails) as a labelled badge, the exact config diff that would be applied, an expiry countdown, and Approve/Reject buttons that need a note on reject. Approvals and rejections publish `ui.command.v1` and are logged with the actor. An audit strip at the bottom of the dashboard shows the last five config changes with who or what made them.

### 5.9 Sim-clock speed control (C2)

A `role="group"` labelled "Simulation clock" in the header containing:

- Sim time, formatted from `sim_epoch` as `Day 1 03:15:00` plus the absolute ISO timestamp in a tooltip.
- Wall elapsed and the `wall_clock_epoch` mapping, shown in a disclosure so the C2 mapping is on screen without cluttering it.
- Speed preset buttons from `dashboard.clock.speed_presets` (default `0, 0.25, 1, 4, 16, 60`) plus `MAX` when allowed. The active preset has `aria-pressed="true"`.
- Achieved-speed readout: `requested 60x / achieved 41x` when they differ, with a shape-coded lag indicator. When achieved is within 5 percent of requested, only one number shows. The achieved figure comes from `ui.pacing.v1` in live mode and from `ReplayClock`'s own animation-frame timer in replay mode, and it is never recorded (section 3.3).
- Step controls: step one unit as defined in section 4.2, step to next finding, step to next constraint shift. The first control is labelled "Step frame" in replay mode and "Step event" in live simulation mode.
- Replay only: a scrubber (`<input type="range">`) with `aria-valuetext` set to the sim time, plus a chapter track marking findings, agent turns, and constraint shifts as tick marks with accessible names.

Authority rules:

- Live mode: the clock service is the only authority (C2). The browser sends `set_speed` and renders whatever `sim.clock_tick.v1` reports. The browser never extrapolates sim time between ticks except for a sub-second smoothing of the displayed seconds field, and that smoothing is disabled under reduced motion.
- Replay mode: `ReplayClock` owns the time. It advances `sim_time` by `delta_wall * speed` per animation frame, clamps to `bounds`, and pulls frames from the buffer up to the new time. Buffering never stalls silently: if the next chunk has not arrived, replay pauses with a visible "buffering" state and resumes automatically.

Keyboard (all disabled while focus is in a text field, satisfying SC 2.1.4 Character Key Shortcuts):

| Key             | Action                                                             |
| --------------- | ------------------------------------------------------------------ |
| `Space`         | Pause / resume                                                     |
| `[` / `]`       | Slower / faster preset                                             |
| `,` / `.`       | Step back / forward one frame (replay)                             |
| `J` / `K` / `L` | Shuttle back, pause, shuttle forward                               |
| `Home` / `End`  | Seek to start / end (replay)                                       |
| `N` / `Shift+N` | Next / previous finding                                            |
| `1`..`9`        | Focus the first nine panels in registration order                  |
| `G` then letter | Focus the panel holding that mnemonic, over every registered panel |
| `?`             | Shortcut help dialog, listing every panel with number and mnemonic |
| `P`             | Toggle perf overlay                                                |

The number row reaches nine panels. The registry admits more than nine: section 8 adds roughly twenty over phases 3 and 6, so a fixed number map stops covering the dashboard the moment the tenth panel registers. The chord covers all of them, at any registry size. `TF.panels.register` takes a mandatory single-letter `mnemonic`, refuses a duplicate at registration time with an error naming both panels, and refuses a letter already bound to a top-level shortcut. `T-KBD-2` registers thirty panels from a fixture and asserts three things: every panel is reachable by chord, the duplicate registration raises, and the help dialog lists every registered panel. The failure that test rules out is a shortcut map that quietly stops covering the UI as the UI grows.

All bindings are remappable and persisted in `localStorage` under `tf.shortcuts`, with a reset control, which is the second half of conformance with SC 2.1.4 Character Key Shortcuts.

### 5.10 Recording a shift (E1)

`twinflow replay record` runs the whole stack in DST simulation mode with a fixed seed and as-fast-as-possible clock compression, subscribes to exactly the event set in section 4.1, and writes the bundle.

What gets recorded:

What the `view_model` tier records, which is the tier the viewer loads (section 4.4.3):

- View-model events at `frame_rate_hz` (default 2 Hz). The dashboard consumes aggregated view events anyway, so the recorder records the same thing the browser would have received live.
- Aggregate per-device series at `telemetry_aggregate_seconds` (default 60) for the sparklines.
- Full-rate evidence windows of `evidence_window_seconds` (default 120) either side of every finding, so clicking a finding shows the actual signal that tripped the rule rather than a smoothed version. This is the detail that makes the replay demo defensible under questioning: the reader can see the raw data behind the verdict.
- The agent transcript, driven by `replay_questions.yaml` against the response cassette of section 5.10.1, with the full tool trace and result ids captured.
- Keyframes at `keyframe_interval_sim_seconds` (default 300).

The raw device stream is not dropped from E1, it is a second tier of the same bundle format. `record --tier full_tap` records every device envelope at its native publish rate from the same seeded run, and section 4.4.3 states where each tier is published. The view-model tier is what a browser can load; the full tap is what a reader who wants the raw signal downloads.

#### 5.10.1 The agent response cassette

An agent turn is the one part of a recorded shift that a seed does not govern. A model samples, and its latency and token counts move between calls, so a record path that called a live model would produce a different bundle every run and `BG-DET-UI-1` would fail on its first execution. A gate that fails on its first execution gets turned off, and section 7.7 argues that a gate turned off is worse than a gate never written.

So `record` reads a cassette. This is D-04 taken literally at the presentation layer: a learned model cannot be made deterministic here, so it does not steer the recorded run. The cassette is the recorded-response adapter D-04 names, bound behind the kernel's `Inference` port, and the tape carries the decision the model produced rather than recomputing it on replay. Nothing about that is a workaround for the model's benefit; it is the only arrangement in which a bundle recorded on one machine can be checked on another.

| Property          | Rule                                                                                                                                                                                       |
| ----------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| File              | `replay/cassette.json`, committed to the repository, hashed in the manifest, and copied into the published bundle                                                                          |
| Key               | sha256 over the canonicalised request: model id, system prompt, the tool schema set, the message list, and the decoding parameters                                                         |
| Value             | The model's response text, the tool calls it made, the token counts, the model id, and the duration bucket of each tool call (section 3.8), all recorded once                              |
| Default path      | `record` resolves every turn from the cassette and calls no model at all                                                                                                                   |
| Miss              | `record` exits non-zero naming every missing key and the question that produced it. It never falls back to a live call, because a silent fallback is how a bundle stops being reproducible |
| Refresh           | `record --refresh-cassette` is the only path that calls a model. It rewrites `cassette.json`, and the diff is reviewed like source                                                         |
| Model for refresh | The local model by default, per the source constraint "fully local, no cloud account, optional env var for a hosted LLM". The env var selects a hosted model when the author wants one     |

Three consequences follow and each is worth stating.

`BG-DET-UI-1` gets a precondition it can state: a complete cassette. With one, two `record` runs at the same seed differ in nothing.

`cost` and `model_artifact_hash` survive in `AgentTurnView` (section 3.8). Token counts come from the cassette entry rather than from a fresh call, and `usd` is computed from a price table whose hash is in the provenance sidecar.

`just demo-bundle` needs no model. That is what makes the sentence in section 5.11 about a stranger reproducing the demo true rather than aspirational, and it is why the cassette is committed while the bundle is not: the cassette is small text that makes the build reproducible, and the bundle is tens of megabytes the build regenerates.

#### 5.10.2 The question script, sequenced by what exists

The demo narrative is six questions. Three of them need subsystems that land after the phase E1 ships in, so the script is phased rather than assumed. Nothing is dropped: every question below is recorded, in the first phase that can record it, and `VAL-GATE-E1-001` in ROADMAP.md already re-records the bundle from the code at every tag from v0.3.0 onward, so a question joins the shipped demo at no extra cost when its subsystem lands.

| Id   | Question                                                                                                          | Needs                                                                    | First recordable |
| ---- | ----------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------ | ---------------- |
| `q1` | "what is the current bottleneck and how confident are you?"                                                       | Twin constraint identification, agent `get_bottleneck`                   | P2               |
| `q3` | "there are 40 alarms in ten minutes, what is the root cause and what do I look at first?"                         | `twinflow-alarms` flood mode and grouping                                | P2               |
| `q4` | "what happens to daily throughput if I add a second scan portal at dock 3?", ending in the statistical verdict    | Component 7 what-if tool, component 5 hypothesis test                    | P2               |
| `q7` | An out-of-domain question refused by the tool router because no tool covers it                                    | The router's own coverage check, which exists as soon as tools do        | P2               |
| `q2` | "device conv2-vib-01 is trending, when does it cross the alarm limit and what does running to failure cost?"      | Component 3 trend and time-to-threshold, plus the cost-of-deferral model | P3               |
| `q6` | An out-of-scope question that triggers calibrated abstention                                                      | E26(g), which ROADMAP.md places in P3                                    | P3               |
| `q5` | "compare adding a portal, adding an operator, and raising conveyor speed, ranked by throughput gained per dollar" | Component 7 `compare_scenarios` and the cost assumptions                 | P3b              |

The first shipped script is `q1`, `q3`, `q4`, `q7`. It has a narrative shape on its own: find the constraint, survive the flood, run the experiment, watch the agent refuse something. `q7` and `q6` are both refusals and they refuse for different reasons, which is why both exist rather than one standing in for the other. `q7` refuses because no tool covers the question, a routing fact available the moment tools exist. `q6` refuses because self-consistency agreement fell below the calibrated threshold, which needs the measured threshold E26(g) produces. Showing the agent refuse is worth more than showing it answer, and the cheap refusal ships first so the demo never lacks one.

`replay_questions.yaml` carries a `min_phase` per entry, and `record` skips entries above the current phase with a line in the report rather than failing. `T-QSCRIPT-1` asserts that every entry's `min_phase` matches the table above and that the shipped script is non-empty at P2.

#### 5.10.3 Determinism of the bundle

With the same seed, the same config, the same twinflow version, and a complete cassette, `record` produces a byte-identical bundle on the pinned reference runner. Gzip is written with `mtime=0` and a fixed level; JSON is canonicalised (sorted keys, no insignificant whitespace, fixed float formatting); `run_id` is derived rather than generated (section 3.2); every wall-derived value lives in `provenance.json`. `BG-DET-UI-1` asserts byte equality across two runs over the named exclusion list in section 7.3.2.

The claim stops there, and D-05 is why. Byte-identity is claimed on one pinned platform with one pinned dependency set. Across platforms the claim is value-equivalence: the business events are identical and the continuous fields agree within a tolerance derived from measured divergence. `BG-DET-UI-2` runs the same record on a second platform and reports the observed maximum divergence per field rather than asserting a number chosen in advance.

### 5.11 The hosted viewer and the GitHub Pages site

`twinflow replay publish` produces:

```
site/
  index.html          # the same single file from twinflow-dashboard
  .nojekyll
  replay/manifest.json
  replay/frames/*.ndjson.gz
  replay/keyframes/*.json
  replay/media/*.webm
  replay/dataset_card.md
  replay/provenance.json
  docs/               # mkdocs-material build
```

Load sequence: fetch `manifest.json`, fetch keyframe 0 and chunk 0, render the first frame, then prefetch chunks ahead of the playhead with a two-chunk lookahead. First frame renders without waiting for the whole bundle.

First-run overlay: a dismissable panel explaining what the reader is looking at, that the data is synthetic, what the five panels are, and the three things worth clicking. It is keyboard-reachable, focus-trapped while open with a documented escape, and remembered in `localStorage`.

Deep links, all shareable and all tested:

- `#t=03:15:00` seek to a sim time.
- `#finding=F-0142` open a finding drawer at its sim time.
- `#q=4` jump to recorded question 4 and play from there.
- `#panel=findings&filter=severity:critical` open a filtered view.

The agent in replay mode: the transcript is recorded, and the viewer is explicit about that. The chat panel presents the recorded questions as a clickable list and a free-text box. Free text does one of two things and says which:

- It lexically matches a recorded question above a threshold, and the viewer answers with "closest recorded question: <q>", then plays that turn.
- It matches nothing, and the viewer says "this is a recorded demo; the live stack answers free-form questions, here is the quickstart" with a link.

The viewer never fabricates an answer and never holds an API key. This honesty is itself a feature: a reader who tests the boundary finds a system that admits its boundary, which is the same behaviour the accuracy stack claims for the agent.

#### 5.11.1 `M-REPLAY-QUERY` is part of E1, not a follow-on

E1's own text says the agent answers questions in the browser. A recorded transcript with a question picker is a recorded transcript, and shipping only that would meet the visible half of the requirement while quietly narrowing the half the requirement is named for. So real in-browser execution is inside E1's definition of done rather than after it.

`M-REPLAY-QUERY` needs no model and no key. It needs three things that all exist when E1 ships:

| Piece                                  | Where it comes from                                                   | Available |
| -------------------------------------- | --------------------------------------------------------------------- | --------- |
| The recorded run's aggregates, Parquet | `record` writes them beside the frames from the same seeded run       | E1 itself |
| The governed semantic metrics layer    | E26(b), which ROADMAP.md places in P0 as a contract                   | Before P2 |
| A SQL engine in the browser            | `@duckdb/duckdb-wasm`, vendored and served from the site's own origin | Vendored  |

The reader picks a metric and its dimensions from controls, the page runs the SQL in their own browser, and the page shows the SQL beside the number. The number is executed, not recalled. That makes the E26(a) and E26(b) claims visible in the artifact that most readers will be the only thing they ever open.

The engine is a vendored asset and carries the same discipline as three.js. The npm registry entry for `@duckdb/duckdb-wasm` read on 2026-08-09 (HTTP 200, `https://registry.npmjs.org/@duckdb/duckdb-wasm/latest`) gives licence MIT with the `latest` dist-tag resolving to `1.33.1-dev57.0`. That tag currently points at a development build, so the pin is a chosen version recorded in `pyproject.toml` and the SBOM with its file hash (C11), never a floating `latest`. The engine loads lazily on first query, from the page's own origin, so `BG-CSP-1`'s zero-third-party-origin assertion still holds and `T-SIZE-1`'s 400 KB budget on `index.html` is untouched. `BG-BUNDLE-1`'s bundle budget covers the replay bundle; the engine is measured separately in `BG-BUNDLE-4` because a reader who never opens the query panel never downloads it.

The resequencing this forces is recorded rather than left implicit. `M-REPLAY-QUERY` moves from the P6 follow-on list to E1's own work package at P2, and section 8 carries it there. Its one non-local dependency is E26(b), which ROADMAP.md rule R04 places in P0, so the move creates no forward dependency. `T-QUERY-1` is the test that holds the move honest: it loads the published bundle, runs one governed metric through the engine, and asserts that the rendered number equals the value the Python metric layer computes for the same metric and window over the same Parquet files.

One sequenced follow-on remains, and it is the one that genuinely needs something the repository does not have:

- `M-REPLAY-BYOK`: an optional "bring your own model" mode where a reader pastes a key into `sessionStorage` and asks free-form questions against the in-browser tools. Gated behind an explicit warning about key handling in a static page, defaulted off, and documented in SECURITY.md. This one waits because it changes the security posture of the published page, not because it is hard.

#### 5.11.2 Publishing

A GitHub Actions workflow `pages.yml` builds, checks, gates, and deploys, on a schedule split by cost. Every push to `main` records a short smoke bundle of `smoke_sim_minutes` (default 20), checks it, and runs the accessibility and CSP gates against the built site. Every tag records the full-length bundle. A nightly schedule records the full-length bundle as well, so a break in the long path is found within a day rather than at the next tag. `BG-CI-1` in section 7.3.2 carries the wall-time budget for each of the three paths, which C10 needs because these are the longest jobs in the repository.

The bundle is a build artifact and is never committed, so the repository stays small. `just demo-bundle` regenerates it from a clone in one command with no model and no key, because the response cassette of section 5.10.1 is committed and `record` resolves every agent turn from it. That is the whole of what "reproducible by a stranger" means here, and it is a property of the build rather than a hope about the reader's environment. Recorded as Open Question OQ-7 for the separate question of whether a bundle is also attached to each release tag.

The README's demo link points at the Pages URL and is asserted to appear within the first three non-empty lines after the H1 by test `T-README-1`, which is E1's "link it in the first three lines" turned into a failing build.

### 5.12 Accessibility (C12)

Target: WCAG 2.1 Level AA for the dashboard and the replay viewer. Stated in `ACCESSIBILITY.md` as a conformance claim with the known gaps listed, because an unqualified claim is not credible and a qualified one is.

#### 5.12.1 Severity as a triple

Colour, shape, and text. Every severity indicator renders all three. Never colour alone (WCAG 1.4.1), never shape alone (shape without text fails for low vision), never text alone (a control room needs a glance).

A second published source asks for the same triple and asks for more than WCAG 1.4.1 does. NUREG-0700 Revision 4 guideline 1.3.8-10, Redundant Color Coding, page 1-53, reads: "Color coding should be redundant with some other display feature", and its additional information reads: "Displayed information should be sufficient even when viewed on a monochromatic display terminal or hardcopy printout, or when viewed by a user with color vision impairment."<!-- docs-lint-ok * verbatim quotation of NUREG-0700 Revision 4, whose wording is not editable -->
WCAG 1.4.1 forbids colour as the only channel. The guideline asks that the information survive the loss of colour altogether, which is the stronger test and the one this triple is built to pass. Section 5.6.4 records the retrieval and the locator. Guideline 4.1.3-1 of the same document, page 4-15, is the source for `severity_rank` being a rank and not a label, and section 5.6.4 carries the second rank that goes with it.

| Severity | `severity_rank` | Text label | Glyph                       | `side_count` | Token               |
| -------- | --------------- | ---------- | --------------------------- | ------------ | ------------------- |
| critical | 1               | CRITICAL   | octagon with an exclamation | 8            | `--tf-sev-critical` |
| high     | 2               | HIGH       | hexagon                     | 6            | `--tf-sev-high`     |
| medium   | 3               | MEDIUM     | pentagon                    | 5            | `--tf-sev-medium`   |
| low      | 4               | LOW        | square                      | 4            | `--tf-sev-low`      |
| info     | 5               | INFO       | upward triangle             | 3            | `--tf-sev-info`     |

Glyphs are inline SVG with `role="img"` and a `<title>` equal to the text label. No icon font, no emoji, because both break in unexpected renderers and emoji are announced inconsistently.

`side_count` is a real column and not a description, because two other things read it. Shape carries an ordinal meaning, more sides means more severe, so the encoding is learnable rather than arbitrary; and the 3D halo of section 5.13 draws a ring of exactly `side_count` segments, so a glyph with no side count would leave that ring undefined.

The ramp has to satisfy two properties at once, and a shape set chosen for looks satisfies neither. It has to be monotone, so that more sides reads as more severe across the whole ordered enum; a set holding a triangle at `high` and a square at `medium` inverts the rule it claims. It also has to be total, so that every value has a side count for the 3D halo to draw; a circle and a flat bar have none, which would leave `low` and `info` with no halo. The ramp above is strictly decreasing in `side_count` and every value is a polygon. `P-SEVERITY-TOTAL` asserts the strict decrease, so a severity added later cannot break either property quietly.

Under `forced-colors: active` (Windows High Contrast) the shapes stay distinguishable because they are geometry, not fill colour, and the CSS uses `forced-color-adjust: auto` with explicit `CanvasText`/`Canvas` system colours where needed.

`CT-UI-2` guarantees this table stays in sync with the schema enum, and `T-SEV-1` asserts that `severity_rank` and `side_count` are both injective over the enum.

#### 5.12.2 Colour tokens in OKLCH

Every colour in the file is declared once, in `:root`, as an OKLCH value. No hex literals, no `rgb()`, no `hsl()`, outside a single `@supports not (color: oklch(0 0 0))` fallback block. A CI lint (`just lint-colour`) greps `index.html` for colour literals outside the token block and the fallback block and fails on any hit.

OKLCH is used because lightness in OKLCH is perceptually uniform, which means a palette can be generated by holding L constant across hues and the contrast ratios stay predictable instead of being discovered by trial. That is the practical reason, and it is the one to give when asked.

Token families:

```
--tf-bg, --tf-bg-raised, --tf-bg-sunken
--tf-fg, --tf-fg-muted, --tf-fg-inverse
--tf-border, --tf-border-strong
--tf-focus
--tf-sev-critical, --tf-sev-high, --tf-sev-medium, --tf-sev-low, --tf-sev-info
--tf-sev-*-fg      (foreground to use on that severity fill)
--tf-series-1 .. --tf-series-8   (chart series)
--tf-ok, --tf-warn, --tf-stale
```

Four token sets, selected by `data-theme` and `data-contrast` on `<html>`: light normal, light more-contrast, dark normal, dark more-contrast. Defaults follow `prefers-color-scheme` and `prefers-contrast`, and both are overridable in the settings menu and persisted.

All four live in the palette file. The schema in section 6.4 is `light: {normal, more_contrast}` and `dark: {normal, more_contrast}`, so the generator's input has one entry per token set it emits. A two-key palette file feeding a four-set stylesheet would mean two of the four sets were written by hand somewhere, which is the state the generator exists to prevent.

Palettes are data. `packages/twinflow-dashboard/src/twinflow/dashboard/palettes/*.yaml` hold named palettes; `twinflow-dashboard emit-tokens` regenerates the `<style id="tf-tokens">` block from the selected palette, and a CI check fails if the block in `index.html` differs from the generator's output. Colour is generated and gated, not hand-tuned, which is what makes the validation gates in section 7.3.1 mean anything.

`emit-tokens` also generates the `@supports not (color: oklch(0 0 0))` fallback block. It converts every token through the converter `VAL-GATE OKLCH-1` checks and writes sRGB, so the fallback is a derived artifact under the same CI diff check as the OKLCH block. A hand-written fallback would be a second palette nobody gates, and it would be the one an old browser actually renders. `T-TOKENS-1` asserts that the two blocks declare the same token names in the same order and that every fallback value is the converter's output for its OKLCH source.

#### 5.12.3 Keyboard

- Skip link to `#tf-main` as the first focusable element.
- Landmarks: `banner`, `main`, `complementary` for the shelf drawer, `contentinfo`. Each panel is a `<section>` with `aria-labelledby` pointing at its heading.
- Logical tab order; no positive `tabindex`.
- Roving `tabindex` inside the plan view, the fleet table, and the findings list, so those are one tab stop each with arrow-key navigation inside, which is what keeps the total tab count sane at 500 devices.
- Visible focus indicator: 2 px solid `--tf-focus` plus a 2 px offset ring in the background colour, giving a visible boundary on every background. Non-text contrast at least 3:1 against both adjacent colours.
- No keyboard trap. The only focus trap is the modal dialog set (shortcut help, first-run overlay, shelve dialog), each with Escape to close and focus restoration to the invoking element.
- Every mouse-only interaction has a keyboard path, including the plan view, the scrubber, the chapter ticks, and the 3D camera.
- Minimum target size 24 by 24 CSS pixels for all controls, checked by `VAL-GATE TARGET-1`. The source is SC 2.5.8 Target Size (Minimum), Level AA, in WCAG 2.2 (W3C Recommendation 12 December 2024, retrieved 2026-08-09, HTTP 200, `https://www.w3.org/TR/WCAG22/`), whose text is "The size of the target for pointer inputs is at least 24 by 24 CSS pixels" with five listed exceptions. That criterion is above the WCAG 2.1 AA target this section conforms to. It is adopted because a control-room UI is used in a hurry, and ACCESSIBILITY.md states it as a voluntary addition rather than letting it read as part of the 2.1 claim. The gate applies the Spacing and Inline exceptions as the criterion writes them, so a link inside a sentence is not reported as a failure.
- `T-KBD-1` walks the entire page with `Tab` and asserts reachability of every element carrying a click handler, plus absence of traps.

#### 5.12.4 Live regions

Two regions with different jobs.

- Polite log, `role="log" aria-live="polite" aria-relevant="additions" aria-atomic="false"`: the findings list. New non-critical findings are announced as they arrive. Announcements are coalesced at a minimum interval of 1 s so a burst does not queue behind itself.
- Assertive alert, `role="alert"`: critical findings only, and rate-limited to at most one announcement per `assertive_announce_min_interval_seconds` (default 3). Additional criticals inside the interval are folded into the next announcement as "and N further critical findings".
- Flood mode changes the announcement policy: individual criticals stop being announced and the region announces the flood state once, then a rolling summary at most once per 30 s. This is the direct point of contact between alarm-flood protection and accessibility. A screen reader user in an alarm flood without this policy is receiving a denial-of-service, and a control-room UI that does that has failed the person it exists for.
- Region content is plain text with the severity label first, then the entity, then the rule, then the short title. Never "new item added".
- `T-LIVE-1` asserts the announcement rate limits and the flood policy by observing mutations to the live regions during the seeded flood scenario.

NUREG-0700 Revision 4 guideline 4.1.2-1, page 4-13, is why the flood policy keeps announcing rather than going silent. What needs immediate action stays rapidly detectable under every alarm loading condition, and a live region that fell silent in a flood would fail exactly the condition that guideline names. Section 5.6.4 carries the quotation and the retrieval.

#### 5.12.5 Reduced motion

- `@media (prefers-reduced-motion: reduce)` sets `--tf-motion: 0` and disables every transition, the conveyor flow animation, sparkline draw-on, sub-second clock smoothing, panel entry animation, and 3D camera easing.
- An in-UI motion preference with values `system | full | reduced` overrides the media query, because the OS setting is not always available or not always right for this content.
- Reduced motion does not remove information. Anything conveyed by motion has a static equivalent: flow direction becomes an arrow marker plus a rate number, arriving findings get a brief static highlight ring that fades in one step rather than a slide-in, and 3D camera moves become cuts.
- Auto-playing content: the replay viewer does not autoplay on load. It renders the first frame paused with a visible Play control, satisfying WCAG 2.2.2 without a special case. The demo GIF in the README is the one place with unavoidable auto-motion, handled in section 5.14.3.
- `T-MOTION-1` asserts that with reduced motion active, no element has a non-zero computed `transition-duration` or a running animation.

#### 5.12.6 Other AA criteria explicitly handled

| SC                                 | How                                                                                                                                                            |
| ---------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 1.1.1 Non-text content             | Every SVG has `role="img"` and an accessible name; charts have a table equivalent                                                                              |
| 1.3.1 Info and relationships       | Headings, landmarks, `role="grid"` with row/col indices, `aria-describedby` on complex controls                                                                |
| 1.3.4 Orientation                  | No orientation lock                                                                                                                                            |
| 1.3.5 Identify input purpose       | The only free-text field is the shelve reason, which collects no information about the user, so no `autocomplete` token applies and ACCESSIBILITY.md says that |
| 1.4.3 Contrast (minimum)           | VAL-GATE A11Y-1                                                                                                                                                |
| 1.4.4 Resize text                  | 200 percent text-only zoom with no loss                                                                                                                        |
| 1.4.10 Reflow                      | VAL-GATE A11Y-5, 320 CSS px with no horizontal scroll                                                                                                          |
| 1.4.11 Non-text contrast           | VAL-GATE A11Y-2                                                                                                                                                |
| 1.4.12 Text spacing                | VAL-GATE A11Y-6                                                                                                                                                |
| 1.4.13 Content on hover or focus   | Tooltips are dismissable with Escape, hoverable, and persistent                                                                                                |
| 2.1.1 / 2.1.2 Keyboard             | Section 5.12.3, T-KBD-1                                                                                                                                        |
| 2.1.4 Character key shortcuts      | Single-key shortcuts inactive in text fields and remappable                                                                                                    |
| 2.4.3 Focus order                  | Asserted in T-KBD-1                                                                                                                                            |
| 2.4.7 Focus visible                | 2 px ring with offset, tested for contrast                                                                                                                     |
| 3.2.x Predictable                  | No context change on focus; settings changes take effect without navigation                                                                                    |
| 3.3.1 / 3.3.3 Error identification | Command failures render inline with the field, with a suggestion                                                                                               |
| 4.1.2 Name, role, value            | Every custom control uses native elements or documented ARIA patterns                                                                                          |
| 4.1.3 Status messages              | Section 5.12.4                                                                                                                                                 |

Honest note for `ACCESSIBILITY.md`, with the number and its source rather than a vague quantity. Deque's Automated Accessibility Coverage Report (retrieved 2026-08-09, HTTP 200, `https://www.deque.com/automated-accessibility-coverage-report/`) states that across a sample of more than 13,000 pages and page states and nearly 300,000 issues, "On average across all the audits included in the sample data, we found that 57.38% of total issues were identified using Deque's automated tests", and that automated issues appeared for 16 of the 50 success criteria under WCAG 2.1 Level AA. Deque sells the tool the report measures, so the figure ships at confidence tier C with that attribution and not as an independent finding, and the report is explicit that it was written to disprove the lower coverage figures in common use.

The same report's per-criterion table is the part that matters for this dashboard, because the criteria it shows as almost entirely manual are the ones a control-room UI lives on: 2.4.3 Focus Order and 2.4.7 Focus Visible at 100.00 percent manual, 2.1.1 Keyboard at 97.51 percent manual, and 1.4.11 Non-text Contrast at 100.00 percent manual. Section 5.12.3 is exactly focus order, focus visibility and keyboard reach. A green axe run says nothing about them.

So the repository also carries a manual screen-reader checklist, run per release as one Windows and NVDA pass and one macOS and VoiceOver pass, with results recorded per version. `VAL-GATE A11Y-4` is written into ACCESSIBILITY.md as necessary and not enough, with the sentence above beside it.

### 5.13 3D factory view

A committed milestone, not a stretch, and not a separate application.

Design constraints, in order of importance:

1. It is driven by the same `TF.store` state as the 2D view. `TF.render3d` is a second subscriber, not a second data path. Switching views does not reconnect, does not re-fetch, and does not lose position in a replay.
2. Its geometry comes from `facility.yaml`. There are no hand-modelled assets. This means the three A2 profiles all render in 3D with no code change, and a reader who twins their own building gets the 3D view for free. That property is the reason the geometry keys are mandated in Phase 0 (section 8), before anything renders them.
3. It never becomes the only path to information. Every value visible in 3D is present in the 2D view or a table. This is WCAG 1.1.1 and 1.3.1, and it is also plain risk management for a WebGL feature.

Implementation:

- `twinflow-view3d` vendors three.js (MIT) at a pinned version with its hash in the SBOM. This is the only vendored JavaScript library in the repo, and it lives outside `twinflow-dashboard` so the base dashboard keeps its zero-dependency, single-file property. The honest README sentence: the 2D dashboard is one file with no dependencies; the 3D view adds one vendored MIT library and loads on demand.
- `scene_from_facility` emits a `SceneDescription`: floor plane from `facility.bounds`, station boxes from `position` and `footprint`, conveyor ribbons from edge polylines, racking from the storage config, dock doors on the wall line, and an AMR travel graph when 3b has landed.
- Entities (pallets, AMRs, totes) render as instanced meshes. Positions interpolate between state frames with the interpolation disabled under reduced motion.
- Severity encoding carries over: a station with an open critical finding gets a halo ring of exactly `side_count` segments, read from the severity table in section 5.12.1, plus a floating text label. Every severity has a polygon and so a defined segment count, which is the property that makes this encoding total rather than a rule with two holes in it. Colour is never the only channel in 3D either.
- Camera: orbit, pan, dolly, with keyboard equivalents on arrow keys plus modifiers, and named presets. One preset, `top_down_camera`, matches the pose of the component 4 synthetic camera so the 3D view and the CV channel are visibly the same world.
- WebGL absent or context lost: the toggle is disabled with an explanation, and a context-loss event falls back to 2D with a message rather than a blank canvas.
- Performance budget `BG-3D-1`, on named hardware and split in two because the two measurements answer different questions. The CI leg runs on the GitHub-hosted `ubuntu-24.04` x64 runner, which the GitHub Actions runners reference lists under "Standard GitHub-hosted runners for public repositories" as 4 CPU, 16 GB RAM, 14 GB SSD (retrieved 2026-08-09, HTTP 200, `https://docs.github.com/en/actions/reference/runners/github-hosted-runners`). The qualifier is load-bearing: the same page's private-repository table gives the same label 2 CPU and 8 GB, and twinflow is a public repository, so the public row is the one its jobs get. The leg runs under headless Chromium with the software rasteriser, and it asserts no absolute frame time at all: it fails when p95 frame time exceeds 1.25 times the committed baseline for the same runner image digest. The workstation leg is the absolute one, p95 frame time at most 16.7 ms with 500 instanced entities, and 16.7 ms is one frame at the 60 Hz `view3d.target_fps` default rather than a figure taken from anywhere else. Its hardware is not invented here: the recipe writes the measuring machine's CPU model, GPU model, driver version, browser build and OS build into `artifacts/3d-perf.json`, and the README prints that block beside the number. A measurement with no machine block is not published. Section 7.3.2 holds both legs.

Limitations text, required in the README limitations section per the fidelity paragraph: the 3D view is a browser-native visualisation of the twin's state. The real-world counterpart it stands in for is an Omniverse-class XR layer with physically based rendering, USD scene interchange, and headset-scale interaction. This repo does not do that and does not claim to.

### 5.14 README (component 9)

The README is a build artifact with hand-written prose in it, not a document someone edits by hand and hopes stays true.

#### 5.14.1 Structure, in order

1. `# twinflow` and the one-line pitch. One sentence, no adjectives, says what it is and what it does.
2. Line 2 or 3: **Watch it run in your browser (no install):** link to the Pages replay demo. Asserted by `T-README-1` to fall within the first three non-empty lines after the H1, per E1.
3. Badge row: CI, tests, coverage, licence Apache-2.0 or commercial, PyPI version per brick, docs site, accessibility conformance.
4. The measured headline block, generated (section 5.14.2).
5. The demo GIF, above the fold, with the captioned-video link directly beneath it (section 5.14.3).
6. "What this is" in three short paragraphs: the twin, the fleet, the LSS judge, the agent. Explicitly states the digital twin versus simulation distinction, because component 6 says interviewers probe it.
7. Architecture diagram (section 5.14.4).
8. Five-minute quickstart (section 5.14.5).
9. "Use just this part" table (A1), routing by role: quality manager wants SPC as code, AI team wants the grounding checker and agent harness, controls engineer wants the alarm rationaliser, data team wants the synthetic data products, integrator wants the REST/MCP surface. Each row: role, brick, `pip install` line, link to that brick's README.
10. Sensor catalog table, generated from the YAML catalog (2b says the catalog file becomes README material).
11. Validation table: every statistic the LSS engine computes, its published reference, and the tolerance the test asserts. Generated from the test suite's gate registry so it cannot drift.
12. Scaling evidence: the A4 curve chart and the stated knee, with the hardware named.
13. Honest limitations (section 5.14.6).
14. "Why I built this" (section 5.14.7).
15. Links: ARCHITECTURE.md, ROADMAP.md, ADOPTION.md, CONFIGURING.md, ACCESSIBILITY.md, SECURITY.md, CONTRIBUTING.md, CHANGELOG.md, the docs site, the public issue tracker.
16. Licence.

Length budget: the README stays under 400 lines and the first 40 lines carry the pitch, the demo link, the headline, and the GIF. When content exceeds that, it moves to the mkdocs-material docs site and the README links to it. `T-README-2` asserts both budgets.

#### 5.14.2 The measured headline is generated

No number in the README is typed by hand.

CI produces `artifacts/headline.json` from the seeded benchmark and eval runs. `just readme-sync` rewrites the block between `<!-- tf:metrics:start -->` and `<!-- tf:metrics:end -->` from that file. CI runs `just readme-sync --check` and fails the build if the working tree differs, the same discipline as a formatter check. Test `T-README-3`.

The block carries, at minimum:

- The twin/LSS headline: the constraint-identification and what-if prediction accuracy against simulated ground truth across N seeded scenarios, with the seed set named.
- The agent headline (E26): eval-suite accuracy, abstention rate, grounding-checker pass rate, on the versioned eval suite with its version stamped.
- The run that produced them: commit, seed, date, CI run link.

Which single number is _the_ headline sentence is an author decision, not an implementer one. Recorded as Open Question OQ-2. The mechanism above works for any choice.

#### 5.14.3 Demo GIF, generated and deterministic

`just demo-gif` runs a scripted Playwright session against a seeded deterministic replay bundle, captures frames at a fixed viewport and a fixed device pixel ratio, and encodes. Because the run is deterministic (C1) and the bundle is byte-reproducible (section 5.10), the GIF is reproducible: the same commit produces the same GIF.

The scripted flow is exactly the component 9 requirement: the reader sees the line running, the operator asks the portal what-if, the tool trace appears, the twin runs the experiment, and the final frames hold on the verdict card with the hypothesis test visible and readable at GIF resolution.

Constraints, all of them budget gate `BG-GIF-1` and all of them chosen here rather than taken from a published source: at most 30 s, at least 12 fps, at most 5 MB, and every glyph in the verdict frame at least 11 CSS pixels tall when the capture viewport is set to GitHub's rendered content width. The font-size rule is asserted by rendering at the target width in the capture and measuring the rendered glyph box, never by scaling a larger capture down afterwards, because scaling down is exactly the operation that makes an unreadable GIF pass a naive check. `BG-GIF-1` fails when any of the four numbers is exceeded, and the failure message names which.

Accessibility handling, because an auto-playing GIF has no pause control and WCAG 2.2.2 asks for one:

- The same session also produces `demo.webm` and `demo.mp4` with captions (`demo.vtt`) and a full text transcript at `docs/demo-transcript.md`. The link to the captioned video sits directly under the GIF.
- The README embeds the GIF inside a `<picture>` element whose first `<source>` carries `media="(prefers-reduced-motion: reduce)"` and points at a static PNG of the verdict frame. Whether GitHub's markdown pipeline honours that media query is verified at build time by `T-README-4`, and if it does not, the fallback is a static hero image with an explicit "play the demo" link and the GIF moved one section down. Recorded as Open Question OQ-11.

#### 5.14.4 Architecture diagram

Two diagrams, both Mermaid so they render natively on GitHub, both also exported to SVG for the docs site in light and dark variants via `<picture>` with `prefers-color-scheme`:

1. The component and data-flow diagram: devices, broker, UNS, historian, twin, LSS engine, agent, dashboard, with the packages named.
2. The Purdue/ISA-95 segmentation diagram: OT segment (devices, broker), DMZ (historian, twin sync), IT segment (analytics, agent, dashboard), with the bridge as the only crossing point.

`T-DIAG-1` asserts that every package in the uv workspace appears in diagram 1 and that every container in `docker-compose.yml` appears in diagram 2. A diagram that silently goes stale is worse than no diagram.

#### 5.14.5 Five-minute quickstart, tested as written

The quickstart is a single fenced block tagged so a test can extract and execute the literal text:

````
```bash tf:quickstart
git clone https://github.com/<owner>/twinflow && cd twinflow
docker compose up -d
just seed-demo
open http://localhost:8080
```
````

`T-QS-1` extracts every ` ```bash tf:quickstart ` block from the README, runs the commands in a clean container, and asserts:

- every command exits zero;
- the dashboard returns HTTP 200 and streams at least one `twin.line_state.v1` and one `lss.finding.v1`;
- total wall time from clone to first finding is at most 300 s on the stated CI runner.

The measured time is written into `artifacts/headline.json` and rendered in the README, so the five-minute claim is a measurement, not a promise.

The quickstart must keep working in every phase. The source constraint is explicit: "Each phase must leave the repo shippable and the five-minute quickstart intact". `T-QS-1` runs on every push, which is the mechanism that enforces it.

#### 5.14.6 Honest limitations

A bulleted section, written plainly. At minimum:

- All data is synthetic. No client data, no employer code, no proprietary content. Built on the author's own time and equipment.
- The twin is a model of a warehouse, not a warehouse. Its parameters are chosen to be realistic, not measured from a real building.
- Detection on synthetically rendered frames is an easy computer-vision problem. The interesting part is the audit logic, and the model is deliberately simple.
- Statistical validation covers the estimators the engine implements against named published references. It is not a claim of parity with a commercial statistics package.
- The Gage R&R implementation exposes two F-test error terms because published sources differ on which to use; the repo implements both and validates each against its own published output rather than picking one and hiding the ambiguity.
- Scaling evidence is a measured curve on stated hardware with a stated knee, not a claim of unlimited scale.
- The 3D view is a browser visualisation. Its real-world counterpart is an Omniverse-class XR layer, which this is not.
- The replay demo's agent transcript is recorded. The live stack answers free-form questions; the static page does not, and says so on screen.
- Determinism holds within a pinned dependency set and a pinned container image.
- Accessibility conformance is a WCAG 2.1 AA claim with a published gap list, verified by automated gates plus a manual screen-reader pass, and automated tooling does not catch everything.

#### 5.14.7 "Why I built this"

Short, first person, present tense. Content constraints:

- Connects the repo to real work: deploying RFID and IoT tracking fleets, MQTT and edge devices, FMEA-based reliability engineering, and applying Lean Six Sigma to industrial processes.
- Names no employer, no client, no product the author has worked on, and no internal document. Describes the class of system, never the instance.
- Says why a simulation is the right medium: a twin with known ground truth lets every claim be tested, which a real deployment's data never can be shared to demonstrate.
- No marketing adjectives. No em-dashes (the repo's humaniser gate blocks them and `T-STYLE-1` enforces it across all markdown).

IP hygiene enforcement: a pre-commit hook checks the diff against a banned-terms list held in a git-ignored local file (`.tf-private/banned-terms.txt`), so the list of names never enters the public repo. CI runs a weaker generic check (organisation-shaped proper nouns not on a small allowlist are flagged for review). Both are documented in CONTRIBUTING.md.

---

## 6. Configuration

### 6.1 `facility.yaml` geometry (read by both views, required from Phase 0)

```yaml
facility:
  units: metres # enum: metres. Fixed, to avoid unit bugs.
  bounds: { x: 120.0, y: 60.0, z: 9.0 }
  levels: 2 # int >= 1
  stations:
    - id: dock_3 # str, unique, matches twin station ids
      label: "Dock Door 3"
      position: { x: 12.0, y: 4.0, z: 0.0 }
      footprint: { w: 6.0, d: 4.0, h: 4.5 }
      orientation_deg: 90.0 # float, 0..360
      level: 0 # int, 0 <= level < facility.levels
  edges:
    - id: conv_a
      from: dock_3
      to: scan_1
      kind: conveyor # enum: conveyor|manual|amr|crane|dock
      path: [{ x: 15.0, y: 4.0 }, { x: 15.0, y: 20.0 }, { x: 30.0, y: 20.0 }]
```

Validation rules (C5), each with a line-numbered, suggestion-bearing error:

- `id` unique within `stations` and within `edges`.
- Every `edges[].from` and `edges[].to` resolves to a station id. Error names the nearest match.
- `position` plus `footprint` fits inside `bounds`. Violation is an error, with the overflow amount in the message.
- `level` within range.
- Footprint overlap between stations on the same level is a warning, not an error, since staging areas legitimately overlap in plan view.
- `path` has at least two points and its endpoints are within 2 m of the `from` and `to` station footprints. Violation is a warning with the measured distance.
- `orientation_deg` in `[0, 360)`.

These keys are mandatory from Phase 0 even though only the 2D plan view consumes them at first, because retrofitting coordinates into a config that already has three published profiles and dozens of recorded runs is exactly the kind of retrofit the Phase 0 contract list exists to prevent.

### 6.2 `facility.yaml` dashboard block

```yaml
dashboard:
  bind: "127.0.0.1" # str, default 127.0.0.1. Binding 0.0.0.0 emits a warning.
  port: 8080 # int 1024..65535
  stream:
    transport: sse # enum: sse
    client_queue_frames: 1000 # int 100..100000
    coalesce: [twin.line_state.v1, fleet.device_health.v1]
    never_drop:
      [lss.finding.v1, agent.turn.v1, alarm.state.v1, agent.approval_request.v1]
    heartbeat_seconds: 15 # int 1..300
    snapshot_on_connect: true # bool
  theme:
    mode: system # enum: system|light|dark
    contrast: normal # enum: normal|more
    motion: system # enum: system|full|reduced
    palette: default # id resolving to palettes/<id>.yaml
  alarms:
    roles: [picker, controls, supervisor] # non-empty, ids unique, sorted on load
    routing: # finding kind -> role id. Every kind in the schema enum needs a row.
      spc_violation: controls
      capability_shortfall: supervisor
      msa_failure: supervisor
      sop_violation: supervisor
      fleet_health: controls
      twin_divergence: controls
      process_mining_deviation: supervisor
      safety: supervisor
      security: supervisor
      other: supervisor
    flood_threshold_per_10min: 10 # int >= 1. See 5.6.3 for the source and its limits.
    target_rate_per_10min: 1 # int >= 0. See 5.6.3 for the source and its limits.
    dedupe_window_seconds: 30 # int >= 0
    chatter_transitions: 3 # int >= 2
    chatter_window_seconds: 60 # int >= 1
    shelve_max_seconds: 28800 # int >= 60
    shelve_reason_required: true # bool
    assertive_announce_min_interval_seconds: 3 # int >= 1
    group_by: [entity_ref, kind, rule_id] # ordered list of grouping keys
  clock:
    speed_presets: [0, 0.25, 1, 4, 16, 60] # sorted ascending, must contain 0 and 1
    allow_max_speed: true # bool
    default_speed: 1 # must appear in speed_presets
  view3d:
    enabled: true # bool. Ignored with a warning if twinflow-view3d absent.
    max_entities: 2000 # int
    target_fps: 60 # int
    default_camera: orbit # enum: orbit|top_down|dock_view
  hil_badge: true # bool, E47
  perf_overlay: false # bool
```

Cross-field validation:

- `target_rate_per_10min <= flood_threshold_per_10min`, error otherwise.
- `default_speed in speed_presets`, error otherwise, message lists the presets.
- `coalesce` and `never_drop` are disjoint, and every entry names a schema present in `/schemas`.
- `shelve_max_seconds <= 86400` produces a warning above 8 hours, because indefinite shelving is the failure mode alarm rationalisation exists to prevent.
- Every palette id resolves and passes the palette gates in section 7.3.1 at load time in debug mode.
- `roles` is non-empty and its ids are unique. The loader sorts it and keeps the sorted order, so the role map in `alarm.state.v1` is emitted in one order whatever the file said (D-03).
- Every value in `routing` names an id in `roles`, and every value of the `kind` enum in `/schemas/lss/finding.v1.json` appears as a key. A missing kind is an error naming that kind. An unrouted finding is metered against no role and vanishes from every rate. `T-CFG-2` asserts both directions.

The `view3d.enabled` default is `true`, which matches section 2.4. A committed milestone shipped switched off is a milestone shipped disabled forever, and the graceful-absence path of section 2.4 already covers the machine with no provider installed.

### 6.3 `replay.yaml`

```yaml
replay:
  run_seed: 42 # int
  profile: mid_market_3pl # enum over the A2 profiles
  facility: profiles/mid_market_3pl/facility.yaml
  sim_duration_hours: 8 # float > 0
  frame_rate_hz: 2.0 # float 0.2..10
  keyframe_interval_sim_seconds: 300 # int >= 10
  chunk_target_bytes: 1048576 # int
  evidence_window_seconds: 120 # int >= 0
  telemetry_aggregate_seconds: 60 # int >= 1
  questions: replay_questions.yaml # path
  include_media: [whatif, voice] # subset of [whatif, voice]
  tier: view_model # enum: view_model|full_tap. See 4.4.3.
  smoke_sim_minutes: 20 # int >= 1. The short bundle every push to main records.
  budget_bytes_gz: 26214400 # int. record fails if exceeded. 25 MiB.
  output_dir: site/replay # path
  base_path: "/" # str, for Pages project sites
```

Validation: `frame_rate_hz * sim_duration_hours * 3600` must not exceed a configured maximum frame count (default 200000) or the loader errors with the computed value and a suggested frame rate. Exceeding `budget_bytes_gz` is an error at the end of `record`, with the per-chunk size breakdown printed so the fix is obvious. `smoke_sim_minutes * 60` must be less than `sim_duration_hours * 3600`, because a smoke bundle longer than the full bundle is a config mistake rather than a fast check. `tier: full_tap` sets no budget of its own and `budget_bytes_gz` is ignored for it, since the full tap is a release download and not a page load.

### 6.4 Palette files

Four token sets, one file, one key per set, because `emit-tokens` writes four stylesheet blocks and every one of them comes from this file (section 5.12.2). The values below are the shape, not a committed palette: the committed values are whatever `check-palette` accepts, and no colour in this repository is chosen by eye and then defended.

```yaml
id: default
label: "Default, colourblind-safe"
reference: "checked by VAL-GATE A11Y-1, A11Y-2, A11Y-3, CVD-1, OKLCH-1 and BG-SEP-1"
light:
  normal:
    bg: "oklch(0.99 0.003 250)"
    fg: "oklch(0.22 0.02 250)"
    sev_critical: "oklch(0.55 0.19 25)"
    sev_high: "oklch(0.66 0.16 60)"
    sev_medium: "oklch(0.78 0.13 95)"
    sev_low: "oklch(0.62 0.10 230)"
    sev_info: "oklch(0.60 0.02 250)"
  more_contrast: { ... } # same key set, no key added and none omitted
dark:
  normal: { ... }
  more_contrast: { ... }
```

Validation: every value matches the OKLCH grammar; every value converts to an in-gamut sRGB colour or the loader errors naming the out-of-gamut channel; all four sets declare exactly the same key set, and a key present in one and missing from another is an error naming both sets; the whole palette passes the contrast, conversion and separability gates before it can be selected. `T-PAL-2` asserts the four-set key equality on a fixture with one key deliberately dropped.

Two more loader rules, each taken from a NUREG-0700 Revision 4 guideline whose locator and retrieval are in section 5.6.4.

Guideline 1.3.8-12, Red-Green Combinations, page 1-53, reads: "Whenever possible, red and green colors should not be used in combination."<!-- docs-lint-ok * verbatim quotation of NUREG-0700 Revision 4, whose wording is not editable -->
So no severity token in any of the four sets sits in the green hue band, taken here as OKLCH hue 120 to 180 degrees, and the loader errors naming the token and its hue. That band is a number chosen here. Green stays reserved for `--tf-ok`, a device health state, and it never shares a row with a severity token, because a device carrying an open critical finding renders the finding severity and not the health colour.

Guideline 1.3.8-13, Chromostereopsis, page 1-53, reads: "Simultaneous presentation of both pure red and pure blue on a dark background should be avoided."<!-- docs-lint-ok * verbatim quotation of NUREG-0700 Revision 4, whose wording is not editable -->
The dark sets put `--tf-sev-critical` red beside `--tf-sev-low` blue on a dark surface, which is that arrangement in outline. So in both dark sets the chroma of each of those two tokens stays below the chroma of the sRGB primary at the same hue, computed with the converter `VAL-GATE OKLCH-1` checks, and the loader errors naming the token, its chroma and the primary's. The rule is written against what the guideline names, a pure primary, rather than against a fraction chosen here.

Both rules are covered by `T-CFG-1`, which asserts that each validation rule in section 6 produces its documented error with a line number.

### 6.5 Environment

| Variable                       | Purpose                                         | Default |
| ------------------------------ | ----------------------------------------------- | ------- |
| `TWINFLOW_DASHBOARD_BASE_PATH` | Pages project-site subpath                      | `/`     |
| `TWINFLOW_DASHBOARD_BIND`      | Overrides `dashboard.bind`                      | unset   |
| `TWINFLOW_DASHBOARD_NO_AGENT`  | Hide the chat panel when no model is configured | unset   |

No LLM key ever reaches the browser. In live mode the key stays in the agent service on the IT segment. In replay mode there is no key at all. This is stated in SECURITY.md's threat-model note (C7) alongside the command surface: `POST /api/command` is the only write path from the browser, every `kind` is schema-validated, and the dashboard container has no route to the OT network.

---

## 7. Testing

Runtime budgets (C4): unit tier under 20 s total, property tier under 90 s, browser end-to-end tier under 6 min, visual and Lighthouse gates under 4 min. Path-filtered in CI so a change to the LSS engine does not run the browser tier unless a schema changed.

D-13 applies to those four numbers and changes two things about how they are held. First, `BG-BUDGET-1` asserts the arithmetic rather than trusting it: it sums each scenario's declared worst-case runtime, compares the total against its tier budget, and fails when a tier is oversubscribed. A scenario that grows past its job budget then fails as a defect with a named cause, instead of as a timeout that reads as flakiness. Second, the two timing-sensitive scenarios are scoped to fit. `E2E-DASH-3` proves paced-clock behaviour over about 60 simulated seconds, not over a simulated shift, which is the length D-13 fixes for that proof. The generator behind `P-CLOCK-MONOTONE` clamps its speed multiplier at the low end, and the clamp lives in the generator rather than only in the config validator, so a shrinking search cannot walk into a case that runs for 29 minutes inside a 6 minute job.

Tooling: `pytest` plus `hypothesis` for the Python side; `node --test` plus `fast-check` plus `node:vm` for browser logic; Playwright plus `axe-core` for the DOM and accessibility tiers; Lighthouse CI for the Pages build. The axe-core version is 4.13.0 under MPL-2.0, read from the npm registry metadata on 2026-08-09 (HTTP 200, `https://registry.npmjs.org/axe-core/latest`). It is a test dependency, never bundled into `index.html` and never served, so its file-level copyleft reaches nothing this project distributes. Section 7.3.4 records that alongside the three vendored assets.

Every check id this document names is defined in exactly one table. The id grammar is fixed so the rule can be enforced by a script rather than by reading: `T-` for a unit or integration test, `CT-` for a contract test, `P-` for a property, `E2E-` for a seeded end-to-end scenario, the two-word prefix `VAL-GATE` for a validation gate, and `BG-` for a budget gate. `SEEK-1` is an algorithm name and `V1` to `V11` are invariants, and neither form is a check id.

`T-INDEX-1` enforces the rule. It extracts every string matching that grammar from this file, compares the result against the union of the defining tables, which are section 4.3 for contract tests and section 7.1 to section 7.4 for everything else, and fails on a difference in either direction. A capability described with a test id that no table defines is the failure it catches. That failure is what lets a document look tested when it is not, and it is invisible to every other check in this section.

### 7.1 Unit and integration tests

| Id                | Subject              | Assertion                                                                                                                                                                                                                                                                             |
| ----------------- | -------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `T-STORE-1`       | `apply`              | Applying a fixture envelope produces the golden `ViewState` diff                                                                                                                                                                                                                      |
| `T-STORE-2`       | `apply`              | An unknown schema name is counted, not thrown, and leaves state otherwise unchanged                                                                                                                                                                                                   |
| `T-STORE-3`       | `hash`               | RFC 8785 canonical JSON plus SHA-256 in the browser equals `hashlib` in Python for the same state, over a fixture set that includes keys above U+FFFF                                                                                                                                 |
| `T-CANON-1`       | `canonical`          | Perturbing every field the section 3.1.1 exclusion column names leaves `hash(canonical(state))` unchanged, and perturbing any included field changes it                                                                                                                               |
| `T-SEEK-1`        | Seek math            | `SEEK-1` selects the correct chunk and keyframe for boundary, mid-chunk, first, and last targets                                                                                                                                                                                      |
| `T-MANIFEST-1`    | Manifest arithmetic  | `counts.envelopes > counts.frames`, and the per-producer `seq_ranges` cover every envelope in each chunk exactly once with no gap and no overlap                                                                                                                                      |
| `T-BUCKET-1`      | Duration bucket      | The same cassette replayed under an injected clock reporting 40 ms and then 4000 ms emits the same `duration_bucket` both times                                                                                                                                                       |
| `T-ALARM-1`       | Dedupe               | Two findings with the same key inside the window produce one row with `count == 2`                                                                                                                                                                                                    |
| `T-ALARM-2`       | Chatter              | Four transitions in 60 s sets `chattering`                                                                                                                                                                                                                                            |
| `T-ALARM-3`       | Rate                 | The rolling 10-minute rate matches a fixture whose expected value is computed in exact rational arithmetic, to 1e-9 after conversion to double                                                                                                                                        |
| `T-ALARM-4`       | Shelve               | Shelving needs a reason, sets expiry, and auto-unshelves at expiry                                                                                                                                                                                                                    |
| `T-SEV-1`         | Severity table       | `severity_rank` and `side_count` are each injective over the enum, and every value maps to a distinct glyph, label, and token                                                                                                                                                         |
| `T-PAL-1`         | Palette              | OKLCH parse, gamut check, and sRGB conversion round-trip                                                                                                                                                                                                                              |
| `T-PAL-2`         | Palette shape        | All four token sets declare the same key set; a fixture with one key dropped from `dark.more_contrast` fails with a message naming the key and both sets                                                                                                                              |
| `T-TOKENS-1`      | Token generation     | The OKLCH block and the `@supports` fallback block declare the same token names in the same order, and every fallback value is the converter's output for its OKLCH source                                                                                                            |
| `T-CFG-1`         | Config               | Each validation rule in section 6 produces its documented error with a line number                                                                                                                                                                                                    |
| `T-CFG-2`         | Alarm routing        | Every `routing` value names a configured role, and every value of the schema `kind` enum has a `routing` key; a fixture missing one kind fails with that kind named                                                                                                                   |
| `T-A1-1`          | Brick isolation      | In a venv holding only `twinflow-dashboard`, `twinflow-dashboard demo` serves the fixture bundle and renders                                                                                                                                                                          |
| `T-A1-2`          | Brick isolation      | In a venv holding only `twinflow-replay`, `check` and `publish` work on a fixture bundle and `record` exits non-zero with the verbatim message "no runner installed"                                                                                                                  |
| `T-A1-3`          | Brick isolation      | In a venv holding only `twinflow-alarms`, the manager processes a finding fixture stream                                                                                                                                                                                              |
| `T-A1-4`          | Brick isolation      | In a venv holding only `twinflow-replay`, `publish` exits non-zero with the verbatim message "no viewer asset provider installed: pip install twinflow-dashboard"                                                                                                                     |
| `T-SIZE-1`        | File budget          | `index.html` under 400 KB uncompressed; the base64 font subset inside it under 60 KB                                                                                                                                                                                                  |
| `T-FILE-1`        | Degraded `file://`   | Loading `index.html` from a `file:` URL renders the offline placeholder with its two-line instruction, with no blank page and no console-only failure                                                                                                                                 |
| `T-PROGRESSIVE-1` | Progressive features | With `popover`, `view-transitions`, `light-dark` and `text-wrap-balance` made unavailable to the page, every panel renders and every control works; a build that puts a structural behaviour behind one of the four fails                                                             |
| `T-ISOLATION-1`   | Panel emphasis       | At most one element inside any one panel container carries `data-tf-isolated`, over a random `ViewState`; a fixture marking two elements inside one container fails with both named                                                                                                   |
| `T-RENDER-1`      | Idempotent render    | `panel.apply(s, s)` produces zero MutationObserver records for every registered panel                                                                                                                                                                                                 |
| `T-KBD-1`         | Keyboard reach       | Tabbing the whole page reaches every element carrying a click handler, in the documented order, with no trap outside the declared modals                                                                                                                                              |
| `T-KBD-2`         | Panel shortcuts      | With thirty panels registered from a fixture, every panel is reachable by chord, a duplicate mnemonic raises at registration naming both panels, and the help dialog lists all thirty                                                                                                 |
| `T-FOCUS-1`       | Focus stability      | With focus inside the findings stream, 40 arrivals and one rank change leave `document.activeElement` and `aria-activedescendant` unchanged and the paused-update counter reading 40; a build that calls `focus()` on arrival, or that reorders while focus is inside the list, fails |
| `T-LIVE-1`        | Live regions         | Observed mutations to the two live regions obey the coalescing interval, the assertive rate limit, and the flood policy of section 5.12.4                                                                                                                                             |
| `T-MOTION-1`      | Reduced motion       | With reduced motion active, no element has a non-zero computed `transition-duration` and no animation is running                                                                                                                                                                      |
| `T-GROUND-1`      | Ungrounded warning   | A synthetic answer holding a numeral with no `result_id` renders the warning and marks the numeral                                                                                                                                                                                    |
| `T-VERDICT-1`     | Verdict card         | The card rendered from a fixture matches a golden serialised DOM, with one fixture row per formatting rule in section 5.8.1 that fails when that rule is broken                                                                                                                       |
| `T-QSCRIPT-1`     | Question script      | Every entry in `replay_questions.yaml` carries the `min_phase` the section 5.10.2 table gives it, and the script filtered to P2 is non-empty                                                                                                                                          |
| `T-QUERY-1`       | In-browser query     | For one governed metric and window, the number the page computes through the query engine equals the value the Python metric layer computes over the same Parquet files                                                                                                               |
| `T-DIAG-1`        | Diagrams             | Every package in the uv workspace appears in diagram 1, and every container in `docker-compose.yml` appears in diagram 2                                                                                                                                                              |
| `T-QS-1`          | Quickstart           | Every ` ```bash tf:quickstart ` block extracted from the README runs in a clean container, each command exits zero, and the dashboard streams one `twin.line_state.v1` and one `lss.finding.v1`                                                                                       |
| `T-README-1`      | Demo link            | The Pages URL falls within the first three non-empty lines after the H1                                                                                                                                                                                                               |
| `T-README-2`      | README budget        | The README is under 400 lines and its first 40 lines carry the pitch, the demo link, the headline block, and the GIF                                                                                                                                                                  |
| `T-README-3`      | Generated metrics    | `just readme-sync --check` leaves the working tree unchanged, so no number between the metric markers was typed by hand                                                                                                                                                               |
| `T-README-4`      | Reduced-motion GIF   | The built README's `<picture>` element is fetched as GitHub renders it, and the test records whether the `prefers-reduced-motion` source is honoured, driving the OQ-11 fallback                                                                                                      |
| `T-INDEX-1`       | Test index           | The set of check ids matching the grammar above, extracted from this file, equals the set defined in section 4.3 and section 7.1 to section 7.4                                                                                                                                       |
| `T-STYLE-1`       | Humaniser gate       | No em-dash in any markdown or user-visible string in the repo                                                                                                                                                                                                                         |

### 7.2 Property-based invariants

Each named invariant below is a Hypothesis or fast-check property with the generator described.

| Id                       | Invariant                                                                                                                                                                                                                                                                   | Generator                                                                                     |
| ------------------------ | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------- |
| `P-REPLAY-EQUIV`         | For any frame sequence and any seek target `t`, state reconstructed from the last keyframe at or before `t` equals state reconstructed by applying all frames from zero to `t`.                                                                                             | Random valid frame sequences with keyframes at random intervals                               |
| `P-CLOCK-MONOTONE`       | During forward replay at any speed sequence, rendered `sim_time` never decreases; after a seek it equals the target within one frame interval.                                                                                                                              | Random speed change and seek scripts                                                          |
| `P-FINDING-CONSERVATION` | Both parts of `V9` hold after any operation sequence: the sum of `count` over all rows equals `totals.ingested`, and `visible + grouped + shelved` equals `totals.rows`.                                                                                                    | Random operation sequences over a random finding pool                                         |
| `P-SHELF-EXPIRY`         | No shelf entry survives past its expiry; every shelved key reappears at or after expiry.                                                                                                                                                                                    | Random durations including zero and the maximum                                               |
| `P-SEVERITY-TOTAL`       | Every value of the schema severity enum maps to exactly one triple, no two severities share a glyph, a label, or a token, and `side_count` strictly decreases along the enum.                                                                                               | Enumerated from the schema file                                                               |
| `P-CLASS-ORDER`          | Every value of the schema `kind` enum maps to exactly one `finding_class`, the severity a row renders equals the producer's value whatever its class, and the rendered order is the section 5.6.4 sort key applied to the rows in view. Each of the three fails on its own. | Random finding pools drawn from the whole `kind` and severity enums, in random arrival orders |
| `P-COLOUR-NEVER-ALONE`   | Every DOM element carrying a severity token also has a non-empty accessible name containing that severity's text label.                                                                                                                                                     | Random `ViewState` rendered into a DOM                                                        |
| `P-COALESCE-LATEST`      | Under any drop or coalesce policy, the last state frame per entity is always applied; `never_drop` schemas are never dropped.                                                                                                                                               | Random overflow scenarios at random queue depths                                              |
| `P-BUNDLE-ROUNDTRIP`     | `record -> bundle -> viewer replay to end` yields a final `ViewStateCanonical` hash equal to the live run's, on one platform with one pinned dependency set (D-05 tier one).                                                                                                | Random seeds over short sim durations                                                         |
| `P-RENDER-IDEMPOTENT`    | `panel.apply(s, s)` produces zero MutationObserver records for every registered panel.                                                                                                                                                                                      | Random `ViewState`                                                                            |
| `P-KEYBOARD-REACHABLE`   | Every element with a click handler is reachable by `Tab` plus documented arrow-key navigation, and no focus trap exists outside declared modals.                                                                                                                            | Random `ViewState` and random panel visibility                                                |
| `P-REDUCED-MOTION`       | With reduced motion active, no element has a non-zero computed transition or a running animation.                                                                                                                                                                           | Random `ViewState`                                                                            |
| `P-DEEPLINK-ROUNDTRIP`   | Serialising view position to a fragment and parsing it back restores the same panel, filter, and sim time.                                                                                                                                                                  | Random view positions                                                                         |
| `P-PATCH-REVERSE`        | For any pair of consecutive frames, applying the forward patch then its computed inverse returns the earlier frame exactly, which is what a backward step needs.                                                                                                            | Random frame pairs over the two frame schemas                                                 |

### 7.3 Gates

Two classes, split for the reason the front matter of this section gives. A validation gate checks a computed value against an external published reference. A budget gate checks a number this repository chose. Nothing in section 7.3.2 is presented as evidence about the world.

#### 7.3.1 Validation gates, with external published references

Every reference below names its edition and its locator, and every one was retrieved as raw text on 2026-08-09 with the HTTP status shown. No tolerance is tighter than the printed precision of the value it checks.

| Gate                | External reference, edition, locator, status                                                                                                                                                                                                                                                                                           | Assertion and tolerance                                                                                                                                                                                                                                                                                                                 | Falsified by                                                                                                |
| ------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------- |
| `VAL-GATE A11Y-1`   | WCAG 2.1 SC 1.4.3 Contrast (Minimum), Level AA. W3C Recommendation 06 May 2025, `https://www.w3.org/TR/WCAG21/`, HTTP 200. Text: "contrast ratio of at least 4.5:1", with "at least 3:1" for large-scale text                                                                                                                          | Every text-on-background token pair in the rendered DOM has a ratio of at least 4.5, or at least 3 where the text meets the specification's large-scale definition. The published figures carry one decimal place and the comparison uses them as written, with no rounding step before it, so a computed 4.4999 is below 4.5 and fails | Any pair below its threshold in any of the six DOM states of `VAL-GATE A11Y-4`                              |
| `VAL-GATE A11Y-2`   | WCAG 2.1 SC 1.4.11 Non-text Contrast, Level AA. Same edition and locator, HTTP 200. Text: "contrast ratio of at least 3:1 against adjacent color(s)"                                                                                                                                                                                   | Severity glyphs, focus indicators, control boundaries, and chart series each reach at least 3 against every adjacent colour, at the published one-decimal precision                                                                                                                                                                     | Any glyph, indicator, boundary, or series below 3 against any adjacent colour                               |
| `VAL-GATE A11Y-3`   | Sharma, Wu and Dalal, "The CIEDE2000 Color-Difference Formula: Implementation Notes, Supplementary Test Data, and Mathematical Observations", Color Research and Application 30(1):21-30, February 2005. Test data at `https://hajim.rochester.edu/ece/sites/gsharma/ciede2000/dataNprograms/ciede2000testdata.txt`, HTTP 200, 34 rows | For all 34 published pairs, the computed CIEDE2000 difference agrees with the published difference to within 1e-4. The published differences are printed to four decimal places, so their own rounding is at most 5e-5 and the tolerance sits above it                                                                                  | Any of the 34 pairs off by more than 1e-4, or a row count other than 34                                     |
| `VAL-GATE CVD-1`    | Machado, Oliveira and Fernandes, "A Physiologically-based Model for Simulation of Color Vision Deficiency", IEEE Transactions on Visualization and Computer Graphics 15(6):1291-1298, November/December 2009. Authors' project page at `https://www.inf.ufrgs.br/~oliveira/pubs_files/CVD_Simulation/CVD_Simulation.html`, HTTP 200    | The protanopia, deuteranopia and tritanopia matrices compiled into `simulate_cvd` equal the published matrices element for element at the published precision                                                                                                                                                                           | Any matrix element differing beyond the last printed digit of the published value                           |
| `VAL-GATE OKLCH-1`  | CSS Color Module Level 4, W3C Candidate Recommendation Draft 6 August 2026, dated version `https://www.w3.org/TR/2026/CRD-css-color-4-20260806/`, HTTP 200. Section 7 gives sRGB blue as `oklch(0.452 0.313 264.1)` and sRGB yellow as `oklch(0.968 0.211 109.8)`; section 19 gives the sample conversion code                         | Converting sRGB `#0000FF` and `#FFFF00` reproduces those two published triples within half a unit of the last printed digit: 0.0005 in L, 0.0005 in C, and 0.05 degrees in h. Separately, the converter reproduces the section 19 sample code's output over a fixed 64-colour input set                                                 | Either published triple missed by more than half a unit in the last printed place                           |
| `VAL-GATE TARGET-1` | WCAG 2.2 SC 2.5.8 Target Size (Minimum), Level AA. W3C Recommendation 12 December 2024, `https://www.w3.org/TR/WCAG22/`, HTTP 200. Text: "at least 24 by 24 CSS pixels", with the Spacing, Equivalent, Inline, User Agent Control and Essential exceptions                                                                             | Every pointer target is at least 24 by 24 CSS pixels, or meets one of the five listed exceptions, with the exception applied by name in the report                                                                                                                                                                                      | Any target under 24 by 24 that matches no listed exception                                                  |
| `VAL-GATE A11Y-4`   | axe-core 4.13.0 rules tagged `wcag2a`, `wcag2aa`, `wcag21a`, `wcag21aa`, mapping to WCAG 2.1 Level A and AA at the edition above                                                                                                                                                                                                       | Zero violations on six states: idle, populated, alarm flood, chat open with a what-if card, shelf drawer open, 3D view active. The version is pinned, so a rule set change is a deliberate commit                                                                                                                                       | One or more violations in any of the six states                                                             |
| `VAL-GATE A11Y-5`   | WCAG 2.1 SC 1.4.10 Reflow, Level AA. Same edition and locator, HTTP 200                                                                                                                                                                                                                                                                | At 320 CSS px width and 400 percent zoom, `scrollWidth <= clientWidth + 1` and no content is clipped                                                                                                                                                                                                                                    | Horizontal scroll or clipped content at that viewport                                                       |
| `VAL-GATE A11Y-6`   | WCAG 2.1 SC 1.4.12 Text Spacing, Level AA. Same edition and locator, HTTP 200                                                                                                                                                                                                                                                          | With line-height 1.5, letter-spacing 0.12em, word-spacing 0.16em and paragraph spacing 2em applied, no text is clipped and no interactive element overlaps another                                                                                                                                                                      | Any clipped text or overlapping control under that stylesheet                                               |
| `VAL-GATE A11Y-7`   | WCAG 2.1 Level AA criteria list at the edition above, worked through the checklist in `docs/accessibility/manual-checks.md`                                                                                                                                                                                                            | One NVDA pass and one VoiceOver pass per release, results recorded per version, every gap listed in ACCESSIBILITY.md. This gate is a human procedure and states so                                                                                                                                                                      | A release tagged with no recorded pass, or a recorded failure with no entry in the gap list                 |
| `VAL-GATE MOTION-1` | WCAG 2.1 SC 2.2.2 Pause, Stop, Hide, Level A. Same edition and locator, HTTP 200                                                                                                                                                                                                                                                       | The replay viewer renders its first frame paused, with a visible Play control, and no content moves before the reader asks for it                                                                                                                                                                                                       | Any motion in the first 3 s of a cold load with no input                                                    |
| `VAL-GATE KEYS-1`   | WCAG 2.1 SC 2.1.4 Character Key Shortcuts, Level A. Same edition and locator, HTTP 200                                                                                                                                                                                                                                                 | Every single-character shortcut is inactive while focus is in a text field, and every binding is remappable through the settings menu with a reset control                                                                                                                                                                              | Any single-key shortcut firing from a text field, or any binding with no remap path                         |
| `VAL-GATE PATCH-1`  | RFC 6902 JavaScript Object Notation (JSON) Patch, IETF Standards Track, April 2013, `https://www.rfc-editor.org/rfc/rfc6902.txt`, HTTP 200. Appendix A carries worked examples                                                                                                                                                         | The frame patch applier reproduces every Appendix A example exactly, and rejects any document holding `move`, `copy` or `test`, which section 4.4.1 excludes                                                                                                                                                                            | Any Appendix A example producing a different document, or an excluded operation applied rather than refused |
| `VAL-GATE JCS-1`    | RFC 8785 JSON Canonicalization Scheme (JCS), IETF Independent Submission, Informational, June 2020, `https://www.rfc-editor.org/rfc/rfc8785.txt`, HTTP 200. Section 3.2.3 carries sorting test data, Appendix B carries number serialisation samples                                                                                   | The Python canonicaliser and the browser canonicaliser both reproduce the section 3.2.3 sorted output byte for byte, and both reproduce every Appendix B number sample byte for byte                                                                                                                                                    | Either implementation differing from the RFC's output on any sample, or the two differing from each other   |

#### 7.3.2 Budget gates, with numbers this repository chose

Each row names the number, where the number came from, the machine that measures it, and what result would fail it. Where the measured quantity is noisy, the row states the noise floor and sets the threshold above it. The noise floor is measured by running the same gate ten times on an unchanged tree and taking the observed spread, and it is refreshed whenever the runner image digest changes.

| Gate              | What it budgets                       | Number and its origin                                                                                                                                                                                                                                                                                                                                         | Measurement and noise floor                                                                                                                                                                                                                                                                                              | Falsified by                                                                                                                                                                                                                    |
| ----------------- | ------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `BG-DET-UI-1`     | Bundle byte-identity                  | Zero differing bytes. C1 is the requirement; D-05 tier one is the scope                                                                                                                                                                                                                                                                                       | Two `record` runs, same seed, config and version, on the pinned reference runner, over every file except `provenance.json`. Not a noisy quantity: the comparison is exact                                                                                                                                                | Any differing byte outside `provenance.json`                                                                                                                                                                                    |
| `BG-DET-UI-2`     | Cross-platform divergence             | No threshold is asserted in advance. D-05 tier two says the gate reports the observed maximum divergence per field                                                                                                                                                                                                                                            | The same `record` on a second platform. Business events are compared for exact equality; continuous fields are compared numerically and the maximum absolute and relative divergence per field is published as a table                                                                                                   | Any business event differing at all, or a continuous field exceeding the tolerance the previous release measured, in which case the report names which of the two it is                                                         |
| `BG-BUNDLE-1`     | Replay bundle size                    | 25 MiB gzipped for an 8-hour mid-market shift, from `replay.budget_bytes_gz`. Chosen so a reader on a slow link can watch the demo                                                                                                                                                                                                                            | Measured at the end of `record` from the written files. Not noisy: the byte count is exact                                                                                                                                                                                                                               | A bundle over 25 MiB gzipped, reported with the per-chunk breakdown                                                                                                                                                             |
| `BG-BUNDLE-4`     | Query engine payload                  | Measured and published, with no ceiling asserted until three releases of data exist                                                                                                                                                                                                                                                                           | The transferred bytes of the DuckDB-Wasm assets on first query, measured separately from `BG-BUNDLE-1` because a reader who never opens the query panel never downloads them                                                                                                                                             | A release that publishes no number, which is what turns this into an unmeasured claim                                                                                                                                           |
| `BG-LOAD-1`       | First frame                           | 3 s under 4x CPU throttling. Chosen against the 90-second attention span the requirements source describes for a first-time reader                                                                                                                                                                                                                            | Playwright with 4x CPU throttling on the CI runner image named in `BG-3D-1`. Noise floor is the observed spread over ten runs on an unchanged tree, currently republished with each runner image change; the threshold sits above it                                                                                     | First contentful frame later than 3 s, or a run whose spread exceeds the recorded noise floor, which invalidates the measurement rather than the code                                                                           |
| `BG-LH-1`         | Lighthouse scores                     | Performance at least 90 and accessibility exactly 100, on the deployed Pages build under Lighthouse's default throttling profile                                                                                                                                                                                                                              | Lighthouse CI at a pinned major version, because a scoring-curve change between versions moves the number without any change here. A version bump is a deliberate commit that re-baselines the gate                                                                                                                      | Either score below its threshold at the pinned version                                                                                                                                                                          |
| `BG-CSP-1`        | Third-party origins                   | Zero. From the single-file, no-CDN constraint in component 8                                                                                                                                                                                                                                                                                                  | Playwright request interception over a full replay, counting requests whose origin is not the page's own. Exact, not noisy                                                                                                                                                                                               | One or more requests to any other origin                                                                                                                                                                                        |
| `BG-CSP-2`        | Pages policy capability               | No number. The gate records what the platform gives and requires the report to be complete                                                                                                                                                                                                                                                                    | A `HEAD` against the deployed Pages URL, recording every response header, plus a parse of the `<meta>` policy. A Pages-served origin answered a `HEAD` on 2026-08-09 with HTTP 200 and no `Content-Security-Policy` header                                                                                               | A missing or unparsed meta policy, or a report that omits a directive unavailable on that path                                                                                                                                  |
| `BG-3D-1`         | 3D frame time                         | CI leg: 1.25 times the committed baseline. Workstation leg: 16.7 ms p95, which is one frame at the 60 Hz `view3d.target_fps` default                                                                                                                                                                                                                          | CI leg on the public-repository `ubuntu-24.04` x64 runner under headless Chromium with the software rasteriser. Workstation leg on the machine whose CPU, GPU, driver, browser and OS build are written to `artifacts/3d-perf.json`                                                                                      | Either leg over its threshold, or a workstation run published with no machine block                                                                                                                                             |
| `BG-PERF-1`       | 2D frame time                         | CI leg: 1.25 times the committed baseline. Workstation leg: 8 ms p95, one third of a frame at the 4 Hz workload                                                                                                                                                                                                                                               | Same two-leg arrangement, at 500 devices and 2000 findings, writing `artifacts/ui-perf.json`                                                                                                                                                                                                                             | Either leg over its threshold, or a workstation run published with no machine block                                                                                                                                             |
| `BG-QS-1`         | Quickstart wall time                  | 300 s from clone to first rendered finding. From the source constraint "runnable by a stranger in five minutes"                                                                                                                                                                                                                                               | `T-QS-1` in a clean container on the named CI runner. Noise floor from ten runs on an unchanged tree, dominated by image pull time, which is why the pull is timed and reported separately                                                                                                                               | Total over 300 s, and the report says whether the pull or the build carried the overrun                                                                                                                                         |
| `BG-README-1`     | Demo link position                    | Within the first three non-empty lines after the H1. From E1's own sentence                                                                                                                                                                                                                                                                                   | `T-README-1` over the built README. Exact                                                                                                                                                                                                                                                                                | The link on line four or later, or absent                                                                                                                                                                                       |
| `BG-GIF-1`        | Demo GIF                              | At most 30 s, at least 12 fps, at most 5 MB, every glyph in the verdict frame at least 11 CSS pixels tall at GitHub's rendered content width                                                                                                                                                                                                                  | Measured on the encoded artifact and on the capture viewport, never on a downscaled copy                                                                                                                                                                                                                                 | Any of the four numbers exceeded, with the failure naming which                                                                                                                                                                 |
| `BG-BUDGET-1`     | Test tier arithmetic                  | The four tier budgets in the section 7 preamble: 20 s, 90 s, 6 min and 4 min. All four were chosen here                                                                                                                                                                                                                                                       | The sum of the declared worst-case runtimes per tier, computed from the scenario declarations rather than from a run, so the check is instant and cannot flake                                                                                                                                                           | A tier whose declared total exceeds its budget, naming the tier and the scenarios carrying most of it                                                                                                                           |
| `BG-CI-1`         | Pages job wall time                   | Smoke path 12 min, tag path 45 min, nightly path 45 min. Chosen so the smoke path fits inside the push-feedback loop and the long paths fit inside a scheduled window                                                                                                                                                                                         | Job duration from the workflow run, averaged over the last ten runs of each path, with the spread published                                                                                                                                                                                                              | A path whose ten-run average exceeds its budget                                                                                                                                                                                 |
| `BG-ALARM-1`      | Alarm threshold behaviour             | The default `target_rate_per_10min: 1` and `flood_threshold_per_10min: 10` are the two figures section 5.6.3 attributes to the HSE sheet. This gate checks the detector, not the figures                                                                                                                                                                      | A seeded ingest stream stepped one finding at a time across the configured threshold                                                                                                                                                                                                                                     | The flood verdict changing at threshold minus one, or not changing at the threshold                                                                                                                                             |
| `BG-SEP-1`        | Severity colour separability          | Minimum pairwise CIEDE2000 distance at least 15 under normal vision and at least 12 under each of the three simulated deficiencies at severity 1.0. Both numbers were chosen here                                                                                                                                                                             | Computed over the five severity colours with the converter of `VAL-GATE OKLCH-1`, the matrices of `VAL-GATE CVD-1` and the formula of `VAL-GATE A11Y-3`. Deterministic, so no noise floor applies                                                                                                                        | Any pair below its threshold in any of the four vision conditions                                                                                                                                                               |
| `BG-SERIES-1`     | Chart series separability             | The lightness band, the chroma floor, the worst-adjacent deficiency distances, and the cap of three series on scatter, bubble and small-multiple forms. All were chosen here, from the palette validation run recorded in `docs/design/ui-direction.md` section 8.2. The 3:1 contrast part of that run is owned by `VAL-GATE A11Y-2` and is not restated here | The eight `--tf-series-*` tokens, converted with the converter of `VAL-GATE OKLCH-1`, simulated with the matrices of `VAL-GATE CVD-1`, compared with the formula of `VAL-GATE A11Y-3`, against `--tf-bg-raised` in each theme. Deterministic, so no noise floor applies                                                  | Any adjacent pair below its recorded floor in either theme, any slot outside the lightness band or under the chroma floor, or a capped chart form rendering a fourth series                                                     |
| `BG-FLOOD-1`      | Findings re-render under saturation   | No number asserted in advance. The shipped constant is the row-mutation count per animation frame at which the stream stops re-rendering in full and switches to a ranked head, chosen from the `BG-PERF-1` scripting budget and recorded at 120 in `docs/design/ui-direction.md` section 7.2. This gate measures the count on the reference runner           | A seeded flood stepping row mutations per frame upward one step at a time on the reference runner image, with p95 scripting time measured at each step. Noise floor from ten runs on an unchanged tree, published beside the number. Moving the constant is a deliberate commit that records the measurement it moved to | A measured count below the shipped constant, which means the constant claims headroom the runner does not have. A release that publishes no measured count also fails, because that is what turns this into an unmeasured claim |
| `BG-FIRSTPAINT-1` | First-paint payload on the Pages path | 1.2 MB transferred, covering `index.html` plus the manifest plus keyframe 0 plus chunk 0. Derived here from the 3 s first-frame budget of `BG-LOAD-1` at an assumed 5 megabit per second link. Both the link speed and the derived figure were chosen here                                                                                                    | Playwright over the deployed Pages build, summing transferred bytes up to the first rendered frame, on the runner image `BG-3D-1` names. Noise floor from ten runs on an unchanged tree. Moving the figure is a deliberate commit that records the measurement it moved to                                               | More than 1.2 MB transferred before the first rendered frame, or a release that publishes no byte count                                                                                                                         |

`BG-SEP-1` is the row that most needs its class stated. The two distances are a design budget, not a published finding: no source this repository was able to read gives a minimum CIEDE2000 separation for categorical colour coding. The gate is still worth running, because it turns "the palette looks distinguishable" into a number that a palette change can fail against. What it must not do is read as a standards claim, and OQ-15 carries the search for a real external basis. One published figure now sits beside it in a different colour space, recorded in section 5.6.4: NUREG-0700 Revision 4 guideline 1.3.8-7 asks for a separation of 40 units or more in the 1976 CIE UCS L\*u\*v\* space, which is neither this formula nor this scale, so it does not move this row into section 7.3.1.

`BG-SERIES-1` arrives from the direction page in the other class, and the class is the only thing that changed. That page proposes it as a validation gate with the name part `SERIES-1`; it is registered here as a budget gate, same name part, `BG-` prefix. D-11 rule 1 is the reason. The palette validator whose floors it checks is a method this repository runs, and its lightness band, chroma floor and deficiency distances have no external published reference with an edition and a locator, so the validation prefix would claim authority those numbers do not have. The one part of that validation run with a published reference, the 3:1 non-text contrast floor, is already owned by `VAL-GATE A11Y-2` at its own locator and is not duplicated here.

`BG-FLOOD-1` and `BG-FIRSTPAINT-1` are budget gates for the same reason and each states a falsifier that does not move with the number. A gate that reads "the constant moves to whatever we measure" cannot fail, so both rows fix the direction of the comparison: the shipped constant has to survive the measurement, and moving it is a commit that records the measurement it moved to.

#### 7.3.3 References that could not be read

D-11 rule 5 says a statistic with no valid external reference is recorded as an open question rather than as a passing gate. Four references fall under that rule, and each is named with what was retrieved in its place.

| Reference                                                                                           | What was retrieved on 2026-08-09                                                                                                                                                                                                                   | What could not be read                                                                                          | Where it goes                                             |
| --------------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------- | --------------------------------------------------------- |
| EEMUA Publication 191, Alarm systems: a guide to design, management and procurement, Fourth Edition | The publisher's product page, `https://www.eemua.org/products/publications/print/eemua-publication-191/`, HTTP 200. It confirms the title, the Fourth Edition, first publication in 1999, and that ISA 18.2 and IEC 62682:2023 are aligned with it | The body. EEMUA sells the guide. No rate figure and no page 37 text was read from the primary source            | OQ-13                                                     |
| ANSI/ISA-18.2-2016, Management of Alarm Systems for the Process Industries                          | The ISA product page, `https://www.isa.org/products/ansi-isa-18-2-2016-management-of-alarm-systems-for`, HTTP 200, and the ISA18 committee page, HTTP 200. Both confirm the title and designation                                                  | The body, including the definition of alarm flood and any rate attached to it. ISA sells the standard           | OQ-13                                                     |
| IEC 62682:2023                                                                                      | Named on the EEMUA page above as aligned with EEMUA 191. The IEC webstore entry answered HTTP 200                                                                                                                                                  | The body. IEC sells the standard                                                                                | OQ-13                                                     |
| The publisher's copy of Machado, Oliveira and Fernandes (2009)                                      | IEEE Xplore answered an automated request with HTTP 202 and an empty body, which is a bot challenge and not a paywall                                                                                                                              | The publisher's typeset copy. The authors' own project page was read instead and is what `VAL-GATE CVD-1` cites | Named here so the citation's provenance is not overstated |

Two figures in this section rest on a source that quotes a primary text this repository has not read, and both are marked as such where they are used: section 5.6.3 carries the alarm rate defaults with their attribution, and section 5.12.6 carries the automated-coverage percentage with its.

One reference in the same subject area is not in the table above, because nothing stopped it being read. NUREG-0700 Revision 4 is free, current and primary for control-room human factors, and section 5.6.4 records its retrieval and routes the nine guidelines this document applies. It settles the qualitative half of what the three sold documents were carrying here: alarm processing, prioritisation criteria and access to suppressed alarms now rest on a document this repository holds and cites by page. It carries no alarm rate figure, so the two numbers stay where the table above puts them, in OQ-13.

#### 7.3.4 Vendored browser assets and their licences (C11)

Three assets ship inside published artifacts and one tool runs only in tests. Each row carries the version, the licence, the retrieval that established the licence, and where the pin lives. Renewing any pin is a deliberate commit that moves the version, the file hash and the SBOM row together.

| Asset                          | Version           | Licence | How the licence was established                                                                        | Shipped in                            |
| ------------------------------ | ----------------- | ------- | ------------------------------------------------------------------------------------------------------ | ------------------------------------- |
| three.js                       | 0.185.1           | MIT     | npm registry metadata for `three`, `https://registry.npmjs.org/three/latest`, HTTP 200 on 2026-08-09   | `twinflow-view3d`, loaded on demand   |
| `@duckdb/duckdb-wasm`          | pinned, see below | MIT     | npm registry metadata, `https://registry.npmjs.org/@duckdb/duckdb-wasm/latest`, HTTP 200 on 2026-08-09 | The Pages site, loaded on first query |
| Subsetted variable font, woff2 | subset hash       | SIL OFL | The licence text that ships beside the subset, recorded in the allowlist                               | `index.html`, base64 inside the file  |
| axe-core                       | 4.13.0            | MPL-2.0 | npm registry metadata, `https://registry.npmjs.org/axe-core/latest`, HTTP 200 on 2026-08-09            | Nothing. Test dependency only         |

The DuckDB-Wasm `latest` dist-tag resolved to `1.33.1-dev57.0` on 2026-08-09, which is a development build. The pin is a chosen release version recorded in `pyproject.toml` and the SBOM with its file hash, never the floating tag, because a floating tag would move the published site's behaviour without a commit.

MPL-2.0 is file-level copyleft and reaches only the files it covers. axe-core is never bundled into `index.html`, never served from the Pages site, and never imported by a shipped package, so nothing this project distributes falls under it. That is stated here rather than assumed, because D-14 is the case in this repository where a licence read too casually would have taken the whole work with it.

#### 7.3.5 Sources that ship no bytes

Four sources named in the design work behind this section contribute no code and ship in no artifact. Their status is Inspiration: the idea was read, written down in this repository's own words, and specified from that description. None of them appears in `NOTICE`, because `NOTICE` describes what the distribution contains, and naming a source there whose code is absent would make the one file whose job is accuracy about the contents say something untrue.

| Source        | Licence, and how it was established                                                                                                                                                                                                                | Status                     | What was taken                                                                                       |
| ------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | -------------------------- | ---------------------------------------------------------------------------------------------------- |
| Grafana       | GNU Affero General Public License version 3, read from `https://raw.githubusercontent.com/grafana/grafana/main/LICENSE`, HTTP 200 on 2026-08-09                                                                                                    | Inspiration                | The convention that one time-range control scopes every panel, and that a panel states its own query |
| netdata       | GNU General Public License version 3, read from `https://raw.githubusercontent.com/netdata/netdata/master/LICENSE`, HTTP 200 on 2026-08-09                                                                                                         | Inspiration                | The idea behind the perf overlay of section 5.3: a dashboard that reports its own render health      |
| Aceternity UI | Proprietary. Its licence page at `https://ui.aceternity.com/licence`, HTTP 200 on 2026-08-09, states: "You cannot re-distribute the Item as a stock image or its source files, regardless of modifications"                                        | Inspiration, nothing taken | Nothing. Its catalogue is landing-page motion, which this interface refuses on a work surface        |
| Hover.dev     | Proprietary. Its licence page at `https://www.hover.dev/license`, HTTP 200 on 2026-08-09, permits "Use of components for open source projects" and also states that components "may not be redistributed without the written consent of Hover.dev" | Inspiration, nothing taken | Nothing, for the same reason                                                                         |

The first two are unavailable because of their licences, and D-14 is the ruling that says why: a network copyleft reaching a served dashboard would relicense the whole work, which is the case this repository already had to answer once. The last two are unavailable for a different reason. A public repository publishes its source, which is the act both sets of terms name. Hover.dev's page permits open-source use and forbids redistribution without written consent, and a public Apache-2.0 repository does both at once; an ambiguous grant is not a grant, and OQ-17 on the direction page records the ambiguity rather than resolving it in this project's favour. Nothing in this section depends on any of the four, so the verifications change no design, only the record.

### 7.4 Seeded end-to-end scenarios

All run in DST simulation mode with a fixed seed so they are reproducible and so failures are debuggable by replay.

| Id             | Scenario                                                           | Assertions                                                                                                                                                                                                          |
| -------------- | ------------------------------------------------------------------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `E2E-DASH-1`   | Seed 42, mid-market profile, 30 sim minutes, live SSE              | Plan view renders all stations; at least one finding reaches the polite live region; bottleneck panel names a station; the canonical portal what-if returns a verdict card matching the `T-VERDICT-1` golden file   |
| `E2E-DASH-2`   | Alarm flood chaos scenario injecting 40 findings in 10 sim minutes | Flood banner appears at the threshold crossing; list switches to grouped mode; assertive announcements at most one per 3 s; `P-FINDING-CONSERVATION` holds throughout; ungrouped toggle still reaches every finding |
| `E2E-DASH-3`   | Speed control                                                      | Setting 16x changes the achieved-speed readout within 5 s of wall time; pause halts sim time; one step advances exactly one unit as section 4.2 defines it for the mode; resume continues monotonically             |
| `E2E-DASH-4`   | Shelving                                                           | Shelve needs a reason; shelf count badge updates; countdown runs; auto-unshelve returns the item with its marker; the shelve action appears in the audit strip with the actor                                       |
| `E2E-DASH-5`   | Approval (E5)                                                      | An `agent.approval_request.v1` renders the tier badge and diff; approving publishes the command; the audit strip records it; expiry disables the buttons with an explanation                                        |
| `E2E-DASH-6`   | Grounding (E26f)                                                   | An agent turn containing a numeral with no `result_id` renders the ungrounded warning and marks the numeral                                                                                                         |
| `E2E-DASH-7`   | Physical badge (E47)                                               | A device with `physical: true` renders the badge in the fleet table and on its station tile, and the header badge reads "SYNTHETIC + 1 PHYSICAL"                                                                    |
| `E2E-DASH-8`   | Stream degradation                                                 | Forcing queue overflow renders the stream health strip with coalesced counts per producer, and no `never_drop` schema is lost                                                                                       |
| `E2E-REPLAY-1` | Full bundle replay from a static server                            | Manifest, keyframe, and chunk load; replay reaches the end; final `ViewStateCanonical` hash equals the live run's; zero third-party requests                                                                        |
| `E2E-REPLAY-2` | Seek                                                               | Five random seeks land within one frame interval of target and produce states matching full-replay states                                                                                                           |
| `E2E-REPLAY-3` | Deep links                                                         | `#t=`, `#finding=`, `#q=` each restore the documented position                                                                                                                                                      |
| `E2E-REPLAY-4` | Recorded agent honesty                                             | A free-text question with no lexical match renders the "recorded demo" message and never fabricates an answer                                                                                                       |
| `E2E-REPLAY-5` | Integrity                                                          | A chunk with a mutated byte triggers the tamper warning and does not apply                                                                                                                                          |
| `E2E-REPLAY-6` | Live-only commands in replay                                       | For every `kind` the section 4.2 table marks `live`, the viewer refuses with the labelled message, sends nothing, and logs the refusal. A `kind` added with no replay answer fails this test                        |
| `E2E-REPLAY-7` | Full-tap tier                                                      | `record --tier full_tap` on the same seed produces a bundle whose chunk and keyframe layout matches the `view_model` bundle, whose envelope count is strictly larger, and which `check` accepts                     |
| `E2E-3D-1`     | 3D parity                                                          | Toggling to 3D preserves sim time and selection; every station present in 2D is present in 3D; toggling back preserves position                                                                                     |
| `E2E-3D-2`     | WebGL absent                                                       | With WebGL disabled, the toggle is disabled with an explanation and the 2D view is unaffected                                                                                                                       |
| `E2E-QS-1`     | Quickstart                                                         | `BG-QS-1` and `T-QS-1` together                                                                                                                                                                                     |

### 7.5 Golden files (C4)

- `golden/view_state/seed42_t1800.json` and its hash: the full `ViewState` at a fixed sim time.
- `golden/replay/manifest_seed42.json`: the manifest with `provenance` excluded.
- `golden/dom/*.html`: serialised DOM for four panel states, normalised (attribute order sorted, generated ids stripped).
- `golden/screens/*.png`: visual regression at 1440x900 and 390x844, captured only on the pinned CI container image with the vendored font, diff threshold at most 0.1 percent of pixels.

The vendored font exists specifically so screenshots are deterministic across machines. System font stacks make visual regression tests flap, and a flapping test gets disabled, and a disabled test is worse than none. The font is a subsetted variable woff2 under SIL OFL, recorded in the licence allowlist and the SBOM (C11, section 7.3.4).

### 7.6 CI wiring

`just` recipes this section adds: `dash-serve`, `dash-test`, `dash-a11y`, `lint-colour`, `emit-tokens`, `demo-bundle`, `demo-gif`, `readme-sync`, `readme-check`, `pages-build`, `pages-check`.

The recipe that reads a built artifact and reports whether it is intact is `pages-check`, not `pages-verify`, for the reason section 2.2 gives: the operation has one name across the CLI, the API, the recipes and the prose, and the repository word list is what keeps a synonym from creeping back.

Workflows: `ci.yml` runs unit, property, contract, and config tiers on every push with path filters; `browser.yml` runs the Playwright, axe, and visual tiers when `index.html`, any schema, or any palette changes; `pages.yml` builds, checks, gates, and deploys the replay site on `main` and on tags; `quickstart.yml` runs `BG-QS-1` nightly and on any change to `docker-compose.yml`, the justfile, or the README.

### 7.7 Why the gates are shaped this way

This subsection is rationale, not contract. It records the reasoning that produced the shapes above, so a later change can argue with the reasoning instead of guessing at it.

A gate that fails on its first execution gets turned off. That is the failure mode behind the response cassette of section 5.10.1 and behind the two-leg split in `BG-3D-1` and `BG-PERF-1`. A determinism gate over a bundle holding live model output fails immediately and forever. An absolute frame-time gate on a shared runner fails on a busy neighbour. Both would be switched off inside a month, and a turned-off gate is worse than a gate never written, because the repository keeps the claim while losing the check.

A budget gate that borrows a standard's authority is worse than one that admits its number was chosen. The 25 MiB bundle budget, the 300 s quickstart, the 8 ms frame budget and the two CIEDE2000 separations are all engineering choices. Writing them beside gates whose numbers come from W3C and IETF documents, with no marking, would make a reader treat all of them the same way. Section 7.3.1 and section 7.3.2 exist so a reader can tell in one glance which kind of number they are looking at.

Every number the README shows is generated from a run, never typed. `T-README-3` is the check, and it is a formatter-style check: CI regenerates the block and fails if the working tree differs. This is the same discipline the manifest fixture uses in section 4.4.4, and for the same reason. A hand-typed number is correct once, at the moment it is typed, and stale from then on. The README is the artifact a reader spends ninety seconds on, so a stale number there costs more than a stale number anywhere else in the repository.

A test whose failure condition cannot be stated is deleted and replaced (D-12). Every row in section 7.1 to section 7.4 names a result that would fail it. The rows that were hardest to write that way were the ones worth writing: `BG-CSP-2` reports a platform capability rather than asserting one, `BG-DET-UI-2` publishes a measured divergence rather than an assumed tolerance, and `VAL-GATE A11Y-7` states plainly that it is a human procedure.

---

## 8. Phase placement

The controlling constraint from the source: every phase leaves the repo shippable and the five-minute quickstart intact. The dashboard is never absent, only thinner.

| Phase                                   | Deliverable                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                  | Why here                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                     |
| --------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| **P0**                                  | Facility geometry keys in the config schema and their validators; the severity enum in `/schemas`; the OKLCH palette file format plus the `VAL-GATE OKLCH-1`, `VAL-GATE A11Y-1`, `VAL-GATE A11Y-2`, `VAL-GATE A11Y-3`, `VAL-GATE CVD-1`, `BG-SEP-1` and `BG-SERIES-1` gates; the two palette rules of section 6.4; the `lint-colour` rule; the README metrics marker block and `readme-check`; the quickstart extraction harness; the `ui.command.v1` and `ui.snapshot.v1` schemas                                           | These are the contracts that cannot be retrofitted. Coordinates added after three published profiles and dozens of recorded runs is a migration. A severity enum that grows without a contract test ships a grey blank in phase 9. A README that ever contains a hand-typed number will contain a stale one. The palette gates must exist before any colour is chosen, or the colours get chosen by eye and then defended by argument                                                                        |
| **P1**                                  | The single file with header, clock and speed control, plan view with one station, fleet table with two devices, findings list with the live regions, agent chat with one tool, SSE transport, keyboard navigation, reduced-motion mode, the settings menu; `T-PROGRESSIVE-1` and `T-ISOLATION-1`. README v1 with pitch, badges, quickstart, limitations, why-I-built-this. `T-QS-1` green                                                                                                                                    | The source's P1 explicitly includes a dashboard stub. Accessibility ships here, not in P5, because retrofitting keyboard navigation and live regions into a grown UI is a rewrite, and because C12's whole argument is that colour-only severity is a failure you avoid by design rather than repair                                                                                                                                                                                                         |
| **P2**                                  | Findings panel proper against the real LSS engine, bottleneck panel with the constraint timeline, `twinflow-alarms` v1 with dedupe, chatter, rate metering, flood mode, and shelving; the finding detail drawer with evidence charts; the class rank and sort key of section 5.6.4; the focus hold of section 5.6.5 with `T-FOCUS-1`; `P-CLASS-ORDER` and `BG-FLOOD-1`; capability-report link-out; golden view-state hashes                                                                                                 | Needs the LSS engine to exist. Alarm rationalisation lands with the findings it rationalises, not later, because a findings stream without it is unusable from the first flood and the fix would touch every finding surface                                                                                                                                                                                                                                                                                 |
| **P2, closing work package**            | **E1**: `twinflow-replay` record, check, publish; the bundle format; replay mode in the same file; the Pages workflow; deep links; the first-run overlay; the demo GIF pipeline; the README first-three-lines link; `M-REPLAY-QUERY`; `BG-BUNDLE-1`, `BG-LOAD-1`, `BG-FIRSTPAINT-1`, `BG-LH-1`, `BG-DET-UI-1`, `BG-DET-UI-2`, `BG-CSP-1`, `BG-CSP-2`, `BG-GIF-1`, `BG-CI-1`                                                                                                                                                  | ROADMAP.md places E1 as the closing work package of P2 under gate `E1-001`, and this section follows that placement rather than restating it differently. E1 needs only an event log and a viewer, and after P2's other work both exist. From this point every new subsystem appears in the public demo automatically, because the recorder is generic over the event set, so no later phase pays to be in the demo. `M-REPLAY-QUERY` is inside E1 rather than after it, for the reason section 5.11.1 gives |
| **P3, with the catalog**                | **`M-REPLAY-FULLTAP`**: `record --tier full_tap`, the release-artifact upload, and `E2E-REPLAY-7`                                                                                                                                                                                                                                                                                                                                                                                                                            | The raw tap is one extra subscription on the recorder that already exists at E1, so the cost is small wherever it lands. It lands at P3 because that is where the sensor catalog gives the raw stream enough breadth to be worth downloading, and because the release-artifact path is the same one the catalog's own fixtures use                                                                                                                                                                           |
| **P3**                                  | The panel registry (`TF.panels.register`) so later subsystems extend the dashboard without editing core; sensor catalog panel; PdM trend panel with time-to-threshold; CMMS work-order queue view; ERP reconciliation view                                                                                                                                                                                                                                                                                                   | The registry lands the moment a second subsystem wants a panel. Landing it earlier is speculative; landing it later means a monolith to unpick                                                                                                                                                                                                                                                                                                                                                               |
| **P3b to P3i**                          | One panel or one plan-view layer per subsystem, each registered, each with a heading, a landmark, a table equivalent, and an axe pass in `VAL-GATE A11Y-4`. Plan view gains AMR paths, ASRS bays, sortation diverts (3b); process-mining variant view and VSM render (3c); forecast and inventory panels (3d); supplier scorecards and outbound docks (3e); returns triage (3f); cross-dock staging lanes and parcel flow (3g); transport network map and MEIO echelon view (3h); factory line view with batch profiles (3i) | Each rides its own subsystem phase. The registry contract plus the six accessibility requirements per panel is what keeps twenty panels from degrading into twenty inconsistent surfaces                                                                                                                                                                                                                                                                                                                     |
| **6a10 to 6a17**                        | Ergonomics heat layer on the plan view; QMS and CAPA queue with the recall-drill blast-radius view; order and WISMO panel; procurement and eRFX panel; workforce roster view; ITSM and SLO panel; S&OP decision-packet view; finance variance drill-down                                                                                                                                                                                                                                                                     | Same rule. The recall-drill view is worth calling out: it is a graph blast-radius render and it is the highest-impact single screen in the whole QMS phase                                                                                                                                                                                                                                                                                                                                                   |
| **P4**                                  | Camera tile with synthetic-frame replay and SOP violation overlay, permanently labelled synthetic                                                                                                                                                                                                                                                                                                                                                                                                                            | Rides the CV phase. The 3D renderer does not become the CV frame source here; that inversion would make P4 depend on a Phase 6 milestone                                                                                                                                                                                                                                                                                                                                                                     |
| **P5**                                  | Polish pass, demo GIF regenerated at release quality, mkdocs-material docs site, ACCESSIBILITY.md conformance statement with the gap list, `VAL-GATE A11Y-7` manual passes recorded, Lighthouse gates enforced on Pages, README trimmed to its length budget                                                                                                                                                                                                                                                                 | The polish phase in the source. The accessibility conformance statement waits for here because it must describe the finished surface, while the gates it summarises have been running since P0                                                                                                                                                                                                                                                                                                               |
| **P6, positioned immediately after E4** | **`M-3D`**: `twinflow-view3d`, `scene_from_facility`, instanced entity rendering, severity halos, camera presets including `top_down_camera`, keyboard camera control, WebGL fallback, `BG-3D-1`, and the limitations paragraph naming the Omniverse-class XR counterpart                                                                                                                                                                                                                                                    | Placed after E4 because event-sourced replay and counterfactuals are what make a 3D view worth building: watching two runs of the same shift diverge in space is the demo the 3D view exists for, and it does not exist before E4. Placed before E29 because the VLM copilot's frame source can then be the 3D renderer rather than a second raster path. It cannot come earlier than P3b because a facility with no automation has little to show in three dimensions                                       |
| **P6, with their E items**              | E2 (no UI), E4 counterfactual compare view, E5 approval UI, E6 and E7 what-if card fields, E11 dispatcher comparison table, E18 security-zone view, E21 multi-agent view with the decision register, E25 dataset-card links, E27 eval dashboard, E34 voice control and the 30-second voice clip in the replay viewer, E36 compute-placement overlay, E43 model registry panel, E45 AI cost panel, E47 physical badge already in place from P1's schema                                                                       | Each UI surface ships with its E item, in the stated E order, as a registered panel                                                                                                                                                                                                                                                                                                                                                                                                                          |
| **P6 follow-on to E1**                  | `M-REPLAY-BYOK`, the optional reader-supplied model key, gated behind SECURITY.md                                                                                                                                                                                                                                                                                                                                                                                                                                            | Sequenced, not dropped. It waits because it changes the security posture of a published static page, and that is a decision a polish phase is the right place to take                                                                                                                                                                                                                                                                                                                                        |

Dependency summary in one line: geometry and severity contracts (P0) gate everything visual; the LSS engine (P2) gates the findings and alarm surfaces; E1 gates nothing and unblocks the repo's visibility, which is why it closes P2; the 3D view depends on facility geometry (P0), automation content (P3b), and counterfactual replay (E4).

One milestone in this section carries a sequencing change against the shape section 5.11.1 inherited, and it is recorded here so ROADMAP.md and this page agree. `M-REPLAY-QUERY` moves from the P6 follow-on list into E1's own work package at P2. Its only non-local dependency is the governed semantic metrics layer E26(b), which ROADMAP.md rule R04 places in P0, so the move pulls nothing forward that does not already exist. Nothing else in section 8 moves.

---

## 9. Open questions

These are genuine ambiguities in the source or genuine forks where the author's preference decides. None has been silently resolved.

**OQ-1. Who owns the alarm rationaliser.** The reference-architecture paragraph puts alarm prioritisation and rationalisation in the architecture, not in a numbered component. This spec puts it in `twinflow-alarms` and has the dashboard consume `alarm.state.v1`. If the LSS or findings section also specifies a rationaliser, one of the two becomes the reference consumer and `alarm.state.v1` is the merge point. Needs a single owner before P2.

**OQ-2. Which number is the headline.** Component 9 says "a measured headline". The generation mechanism works for any choice, but the sentence at the top of the README frames the whole repo and the candidates pull in different directions: a twin-accuracy number (what-if prediction error against ground truth) speaks to digital-twin and simulation readers; an agent number (eval accuracy plus zero ungrounded numbers) speaks to AI solutions engineering readers; an LSS number (findings validated against published references) speaks to quality and consulting readers. Author's call. A two-number headline is possible and is the current placeholder.

**OQ-3. What "the agent answer questions in the browser" means for E1.** A static page cannot run inference without a key. This spec ships two things inside E1: a recorded transcript with a question picker and an explicit statement of its boundary, and `M-REPLAY-QUERY`, real in-browser SQL execution against the recorded run with no model involved. `M-REPLAY-BYOK`, the optional reader-supplied key, stays sequenced after. Confirm that this reading satisfies the intent, because the alternative reading, a live model inside the static page, changes the security posture of the whole demo.

**OQ-4. GIF versus captioned video as the primary asset.** Component 9 asks for a GIF. A GIF has no pause control, which is a WCAG 2.2.2 problem in a repo whose C12 requirement is accessibility, and it is bandwidth-heavy. This spec ships both, with the GIF above the fold and the captioned video linked directly beneath. Confirm the GIF stays primary.

**OQ-5. Whether the 3D view must inherit the single-file, no-build-step constraint.** Component 8's constraint attaches to the dashboard. This spec keeps the 2D dashboard single-file and dependency-free and puts the 3D view in a second package with one vendored MIT library, loaded on demand. The alternative (hand-written WebGL2 with no library, keeping everything in one file) is possible and costs materially more implementation time for a defensible but narrow purity gain. Section 5.2.3 states the 2D half as a decision with its two grounds, so what is left open here is only the 3D half, and OQ-22 on the direction page asks the same question from the other side.

**OQ-6. Where the 3D milestone belongs in the Phase 6 order.** The source says Phase 6 is the bleeding-edge list "in its stated order" and separately says the 3D view is "a committed later milestone on the roadmap", without giving it an E number. This spec places `M-3D` immediately after E4 with the rationale in section 8. Any other placement is defensible; it needs to be recorded in ROADMAP.md either way so it is not a floating commitment.

**OQ-7. Whether the replay bundle is committed or built.** This spec builds it in CI and uploads it as the Pages artifact, never committing it, so the repo stays small. The cost is that the exact bytes behind the live demo are not in the clone. `just demo-bundle` regenerates them deterministically from the same seed, so the demo is reproducible, but a reader cannot diff the live artifact against the repo without running it. The alternative is committing a bundle per release tag, which adds tens of megabytes per release to the repo forever.

**OQ-8. Whether E5 approvals need a bidirectional socket.** Commands go over `POST /api/command` because they are rare and auditable. The approval flow has an expiry countdown and would feel better with a server-initiated channel for expiry and for a second viewer's action. SSE already carries the state back, so the current design is adequate. If a future phase adds real multi-operator collaboration, a WebSocket becomes worth the added surface.

**OQ-9. Vendored font versus system font stack.** Vendoring a subsetted variable font makes visual regression tests deterministic and removes a class of flaky failures, at the cost of about 60 KB inside a file whose budget is 400 KB, plus one more licence and SBOM entry. A system font stack is free and flappy. This spec vendors.

**OQ-10. Whether the `PHYSICAL` badge needs a shape channel.** C12's shape requirement is written about severity. Device provenance is not severity, so a text badge with an outline is specified. A reviewer who reads C12 broadly might expect every categorical encoding to carry a shape. Cheap either way; worth deciding once and applying consistently.

**OQ-11. Whether GitHub's markdown pipeline honours `prefers-reduced-motion` in `<picture>`.** The reduced-motion fallback for the README GIF depends on it. `T-README-4` checks at build time and the spec names the fallback plan, but the answer determines whether the GIF or a static hero image sits above the fold for reduced-motion readers.

**OQ-12. Whether alarm shelving is per-viewer or shared.** Real control rooms share shelf state, and this spec defaults to server-side shared state with a per-viewer visual override. A portfolio demo mostly has one viewer, so per-browser `localStorage` would be simpler. Shared is specified because a shelf that only one operator can see is the exact failure mode alarm management literature warns about, but it costs a server-side store and a conflict rule for simultaneous shelving.

**OQ-13. What the alarm-rate standards say.** The two default thresholds in section 6.2 rest on the UK Health and Safety Executive sheet quoted in section 5.6.3, which cites page 37 of the 1999 edition of EEMUA Publication 191. Three things are unread and each changes what this section may claim. Whether the current Fourth Edition of EEMUA 191 keeps those figures is unknown. Whether ANSI/ISA-18.2-2016 defines alarm flood by a rate, and at what rate, is unknown, so the phrase "flood definition" appears nowhere in this section as a claim about that standard. Whether either document states its figures per operator is unknown, which is why section 3.7 argues for per-role metering from the design rather than from the standards. Resolving this needs a copy of at least one of the three documents in section 7.3.3.

Part of this question is now answered and the numbers are not. NUREG-0700 Revision 4 was retrieved and read on 2026-08-09, and section 5.6.4 records it. It is a free primary source for the qualitative half: the processing taxonomy, the prioritisation criteria and the rule that suppressed alarms stay reachable are cited by page rather than asserted, so the design statements built on them no longer wait on a sold document. It carries no alarm rate figure at all, and its guideline 4.1.2-2 states that there is no specific guidance on the degree of alarm reduction, which means the missing figures are missing from the free literature and not only from this repository. The three unknowns above stand, the two defaults in section 6.2 stay attributed to the HSE sheet, and this question stays open on the numbers alone.

**OQ-14. Five severities against a three-priority recommendation.** `lss.finding.v1` defines five severity values and this section renders all five, because collapsing a producer's enum in the view would hide a distinction the producer made. The HSE sheet of section 5.6.3 records, from page 65 of the guide it cites, the advice to use about three priorities with an example split of 5, 15 and 80 percent. Both positions are defensible and they are not the same design. The fork is whether the findings stream keeps five bands, or renders five severities inside three operator-facing priority groups with the mapping in config. The second costs one config block and one more grouping level, and it would make the alarm meter's bands mean what a control-room reader expects them to mean.

NUREG-0700 Revision 4 guideline 4.1.3-1, read on 2026-08-09 and quoted in section 5.6.4, narrows this without settling it. It asks for prioritisation by urgency and by challenge to safety, with the highest safety significance ranked highest, which is the class rank section 5.6.4 now states. It fixes no count of priority levels anywhere in the document, so the choice between five bands and five severities inside three operator-facing groups is still an author decision.

**OQ-15. Whether a published minimum colour separation exists.** `BG-SEP-1` asserts a minimum pairwise CIEDE2000 distance of 15 under normal vision and 12 under each simulated deficiency. Both numbers were chosen here, and section 7.3.2 says so. No source this repository was able to read gives a minimum separation for categorical colour coding at a stated viewing condition. If one exists, the gate moves from section 7.3.2 to section 7.3.1 and its numbers change to the published ones. Until then it stays a budget gate and the README's accessibility claim says separability was budgeted, not that it meets a published threshold.

One published figure is now on the table and it does not close this. NUREG-0700 Revision 4 guideline 1.3.8-7, Easily Distinguishable Colors, page 1-51, asks that all colours in a coding set differ from one another by delta E distances "of 40 units or more" in the 1976 CIE UCS L\*u\*v\* space, and notes that this makes 7 to 10 simultaneous colours available. That is a published minimum separation for a colour set, in a colour space and a difference formula that are not CIEDE2000, so restating it as a CIEDE2000 threshold would be a conversion this repository invented and D-11 rule 1 would not accept it. The fork is now narrower and it needs one decision: keep `BG-SEP-1` and `BG-SERIES-1` as budget gates in CIEDE2000, or add a second computation in CIELUV checked against the published 40-unit figure and put that one in section 7.3.1 beside the other validation gates. The same question applies to the eight chart series slots, since the guideline is written about a coding set and not about severity alone.

**OQ-16. Whether the tier-two determinism tolerance is per field or global.** D-05 tier two asks for value-equivalence within a tolerance derived from measured divergence. `BG-DET-UI-2` publishes the observed maximum divergence per field. That is the honest reporting shape, and it leaves open what the next run compares its report against. A single global tolerance is simple and lets a large divergence in one insensitive field mask a small one in a sensitive field. A per-field tolerance table is precise and grows a maintenance burden with every new field. This section publishes per field and compares against the previous release's measured values.

Whether that becomes the repo-wide rule belongs with the kernel section that owns D-05.
