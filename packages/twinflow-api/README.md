---
title: twinflow-api
description: The REST surface the dashboard reads through, at the subset this release actually serves.
topic_type: concept
audience: contributors
---

# twinflow-api

The `/api/v1` surface of requirement A6. Cursor pagination over the canonical
event order, RFC 9457 problem documents, and a live event stream, over runs a
caller hands in.

## Install

```bash
pip install twinflow-api
```

## Use

```python
from twinflow.api import MetricDefinition, MetricRegistry, create_api
from twinflow.kernel import SimClock
from twinflow.storage import Historian

app = create_api(
    runs={"run_01j...": historian},
    clock=SimClock(),
    metrics=MetricRegistry([MetricDefinition("oee", "Overall equipment effectiveness", "ratio")]),
)
```

`app` is an ASGI application. Serve it with any ASGI server:

```bash
uvicorn --factory my_module:build_api
```

## What this release serves

| Route                         | Method | Notes                                                       |
| ----------------------------- | ------ | ----------------------------------------------------------- |
| `/healthz`                    | GET    | Liveness, plus the sim instant read from the injected clock |
| `/readyz`                     | GET    | 503 while no run is loaded                                  |
| `/version`                    | GET    | Package version and the API major                           |
| `/api/v1/runs`                | GET    | Every loaded run with its event count and log hash          |
| `/api/v1/runs/{id}`           | GET    | The run manifest: the hashed core of D-01 and no provenance |
| `/api/v1/runs/{id}/events`    | GET    | Cursor paginated, filterable by subject and sim-time window |
| `/api/v1/stream`              | GET    | Server-sent events, resumable through `Last-Event-ID`       |
| `/api/v1/metrics/{metric_id}` | GET    | 404 unregistered, 501 while the expression is null          |
| `/api/v1/config`              | GET    | The resolved config the caller supplied                     |
| `/api/v1/config`              | POST   | Proposes a change, subject to the E5 autonomy tier          |

Cross-cutting behavior that is built: cursor pagination over the
`(sim_ts, producer_id, seq)` total order, RFC 9457 problem documents carrying
the `TF-Axxx` code, and a deterministic `ETag` on every GET with `If-None-Match`
answering 304.

## What this release does not serve, and why

Every route below is declared in foundations section 5.13 and answers `404` with
a `TF-A020 router not installed` problem document naming what it waits on. That
is deliberate. A `/findings` that answered `200 []` would tell a dashboard that a
facility is clean, which is a stronger and more dangerous claim than "not built".

| Route                         | Waits on                                         |
| ----------------------------- | ------------------------------------------------ |
| `POST /api/v1/runs`           | The job runner that starts a run and returns 202 |
| `DELETE /api/v1/runs/{id}`    | Run lifecycle, which nothing owns yet            |
| `/api/v1/runs/{id}/speed`     | C2 speed control, which needs the paced runtime  |
| `/api/v1/twin/state`          | The `twin.line_state` producer                   |
| `/api/v1/twin/stations/{id}`  | The same producer                                |
| `/api/v1/fleet/devices`       | The fleet registry and health scoring of E44     |
| `/api/v1/fleet/devices/{id}`  | The device twin of E44                           |
| `/api/v1/findings`            | The LSS engine                                   |
| `/api/v1/findings/{id}`       | The LSS engine and alarm rationalization         |
| `/api/v1/scenarios`           | The scenario catalog                             |
| `/api/v1/whatif`              | The job runner and the config delta path         |
| `/api/v1/jobs/{id}`           | The job runner                                   |
| `/api/v1/reports/capability`  | The capability report generator                  |
| `/api/v1/genealogy/lots/{id}` | Lot genealogy                                    |
| `/api/v1/webhooks`            | Delivery, signature, and dead-letter machinery   |

Cross-cutting behavior that is also not built, listed so nobody reads its absence
as a decision: `Idempotency-Key` replay on POST, the per-principal rate limit,
the auth tiers and their scopes, and the GraphQL surface at `/graphql`.

## Determinism

Nothing here reads a wall clock, draws a random number, or mints a `uuid4`. The
sim instant arrives through the `Clock` port of `twinflow-kernel`, the config
proposal id is a hash of the proposal and the instant it arrived at, and the
`ETag` is a hash of the exact bytes the response carries. Two replays of one
recorded session produce the same bodies and the same headers.

## Dependencies

`fastapi`, `uvicorn`, and three workspace packages. No `httpx`: it pulls
`certifi`, which is MPL-2.0, and the CONTRIBUTING.md allowlist refuses copyleft
in the shipped tree. The tests drive the ASGI application directly rather than
through a client library, which is both license-clean and a stricter test of the
contract the server actually implements.

## What the orchestrator still owes this package

- `api/openapi.v1.json`, the committed spec that gate SEMVER-2 diffs. This
  package produces the document through `openapi_document(app)`; publishing it
  at the repository root is outside this package's boundary.
- Error pages for the nine `TF-Axxx` codes listed in
  `twinflow.api.problems.PROBLEMS`. The problem document's `type` points at
  them, and until they exist that link is a 404.
