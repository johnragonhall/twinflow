"""The HTTP surface of foundations section 5.13, at the P1 subset.

Requirement A6 asks for an integration surface; this module builds the part of
it the dashboard reads through, and refuses the rest out loud. README.md lists
route by route what is here and what is not, with the requirement each missing
one waits on. The refusal matters more than the list: a route with no producer
behind it that answers `200 []` tells a dashboard that a facility has no
findings, which is a stronger and more dangerous claim than "not built".

Three cross-cutting decisions, each of which is a contract clause rather than a
framework habit:

Requirement R32 says building the dashboard against internal calls and inserting
an API later rewrites every dashboard test. So the dashboard talks to this
surface over HTTP from the first commit, `twinflow.dashboard` never imports
`twinflow.api`, and the import graph is what enforces it rather than a review
convention.

Doctrine D-02 makes the clock a port. An API server is the natural home for a
wall-clock stamp and a `uuid4`, and both would put a fresh value into two runs
of one seed. Every instant this module reports comes from the injected `Clock`,
and every identifier it mints is a hash of its own inputs.

Foundations section 5.13 puts an ETag on every GET and says it is the content
hash of the canonical response body, "which makes it deterministic in simulation
mode". That only holds if the bytes hashed are the bytes sent, so the body is
serialized once, canonically, and both the hash and the response read it.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import AsyncIterator, Mapping, Sequence
from typing import Annotated, Any

from fastapi import FastAPI, Query, Request
from fastapi.responses import JSONResponse, Response, StreamingResponse
from pydantic import BaseModel, ConfigDict, Field

from twinflow.agent import AutonomySession, AutonomyTier, TierRefused
from twinflow.api.cursor import Cursor, CursorError, decode_cursor, encode_cursor
from twinflow.api.metrics import EXPRESSION_REQUIREMENT, MetricRegistry
from twinflow.api.pagination import DEFAULT_PAGE_SIZE, MAX_PAGE_SIZE, page_of
from twinflow.api.problems import (
    AUTONOMY_TIER_REFUSES_APPLY,
    DEFAULT_PROBLEM_BASE_URL,
    GUARDRAIL_EVALUATOR_ABSENT,
    MALFORMED_CURSOR,
    METRIC_EXPRESSION_PENDING,
    NOT_READY,
    OFFSET_NOT_OFFERED,
    PROBLEM_MEDIA_TYPE,
    ROUTER_NOT_INSTALLED,
    UNKNOWN_METRIC,
    UNKNOWN_RUN,
    ProblemError,
    problem_document,
)
from twinflow.kernel import Clock
from twinflow.schemas import Envelope
from twinflow.storage import Historian

#: The URL major of the REST contract, per the versioning table of section 5.8.
#: Removing a route, adding a required parameter, or changing a status code
#: class is what moves this to v2.
API_PREFIX = "/api/v1"

#: Section 5.13 puts these three outside the versioned prefix, because a
#: liveness probe written by an orchestrator must not have to be updated when
#: the API major changes.
UNVERSIONED_PATHS = ("/healthz", "/readyz", "/version")


#: The tier at which section 5.13 allows the `config:apply` scope at all.
#: `AutonomyTier` is owned by `twinflow.agent`, which is where E5's tier
#: semantics live: non-self-elevation is enforced at construction and the
#: audit event reads the authority from the session rather than from the
#: caller. Boundary rule A1.4 gives that name one owning package, and this
#: layer imports it rather than declaring a second enum that would agree with
#: the first until somebody added a tier to one of them.
APPLY_TIER = AutonomyTier.L3

#: The tool name the grant scope would have to carry. A grant lists tools rather
#: than a pattern, so a session approved to apply one change is not thereby
#: approved to apply every other write tool in the registry.
CONFIG_APPLY_TOOL = "apply_change"


class ConfigProposal(BaseModel):
    """A proposed config change, as `POST /api/v1/config` receives it."""

    model_config = ConfigDict(extra="forbid")

    path: str = Field(min_length=1, max_length=200)
    value: Any
    apply: bool = False


#: Routes foundations section 5.13 declares and this phase does not build. Each
#: one answers `TF-A020`, which section 4 already defines as the answer from a
#: router the build did not install. The reason travels with the path so a
#: client reading the problem document learns what it is waiting for rather
#: than filing a bug against a route that was never claimed.
NOT_INSTALLED: tuple[tuple[str, str], ...] = (
    ("/runs/{run_id}/speed", "C2 speed control needs the paced runtime, which P1 does not wire"),
    ("/twin/state", "needs the twin.line_state producer, which arrives with the line runtime"),
    ("/twin/stations/{station_id}", "same producer as /twin/state"),
    ("/fleet/devices", "needs the fleet registry and health scoring of E44"),
    ("/fleet/devices/{device_id}", "needs the device twin of E44"),
    ("/findings", "needs the LSS engine; an empty list here would read as a clean facility"),
    ("/findings/{finding_id}", "needs the LSS engine and the alarm rationalization of E5"),
    ("/scenarios", "needs the scenario catalog"),
    ("/whatif", "needs the job runner and the config delta path"),
    ("/jobs/{job_id}", "needs the job runner"),
    ("/reports/capability", "needs the capability report generator"),
    ("/genealogy/lots/{lot_id}", "needs lot genealogy"),
    ("/webhooks", "needs the delivery, signature, and dead-letter machinery"),
)

_NOT_INSTALLED_METHODS = ["GET", "POST", "PATCH", "DELETE"]


def create_api(
    *,
    runs: Mapping[str, Historian],
    clock: Clock,
    metrics: MetricRegistry | None = None,
    resolved_config: Mapping[str, object] | None = None,
    autonomy: AutonomySession | None = None,
    problem_base_url: str = DEFAULT_PROBLEM_BASE_URL,
) -> FastAPI:
    """Build the ASGI application over one set of recorded runs.

    Named `create_api` rather than `create_app` because boundary rule A1.4 gives
    one public name exactly one owning package, and `twinflow.dashboard` already
    owns `create_app`: section 2.1 of the dashboard design page publishes it as
    part of that package's surface. Two `create_app` symbols would leave a
    consumer writing a star import with whichever one it imported last.

    Everything the app reads arrives here as an argument. There is no module
    state and no import-time construction, so two apps in one process serve two
    different sets of runs, which is what makes the test tier able to assert a
    `readyz` failure without tearing anything down.
    """
    registry = metrics if metrics is not None else MetricRegistry()
    config = dict(resolved_config or {})

    app = FastAPI(
        title="twinflow",
        version="v1",
        description=(
            "The REST surface of requirement A6. Cursor pagination follows the canonical "
            "total order of invariant E4, and errors are RFC 9457 problem documents whose "
            "code field carries the TF-Axxx token."
        ),
    )

    @app.exception_handler(ProblemError)
    async def _problem_handler(_: Request, exc: ProblemError) -> Response:
        return JSONResponse(
            status_code=exc.problem.status,
            content=problem_document(exc.problem, exc.detail, base_url=problem_base_url),
            media_type=PROBLEM_MEDIA_TYPE,
        )

    def _run_or_refuse(run_id: str) -> Historian:
        historian = runs.get(run_id)
        if historian is None:
            raise UNKNOWN_RUN.raised(
                f"run {run_id!r} is not loaded; this server serves {len(runs)} run(s)"
            )
        return historian

    # -------------------------------------------------------- unversioned three

    @app.get("/healthz", tags=["operations"])
    def healthz(request: Request) -> Response:
        return _serve(request, {"status": "ok", "sim_time": int(clock.now())})

    @app.get("/readyz", tags=["operations"])
    def readyz(request: Request) -> Response:
        if not runs:
            raise NOT_READY.raised(
                "no run is loaded, so every read route would answer 404; a liveness probe "
                "passing here would put this process into rotation with nothing to serve"
            )
        return _serve(request, {"status": "ready", "runs": len(runs)})

    @app.get("/version", tags=["operations"])
    def version(request: Request) -> Response:
        from twinflow.api import __version__

        return _serve(
            request,
            {"package_version": __version__, "api_version": "v1", "prefix": API_PREFIX},
        )

    # -------------------------------------------------------------------- runs

    @app.get(f"{API_PREFIX}/runs", tags=["runs"])
    def list_runs(request: Request) -> Response:
        listed = [
            {
                "run_id": run_id,
                "event_count": len(runs[run_id]),
                "profile": runs[run_id].snapshot.profile,
                "scenario": runs[run_id].snapshot.scenario,
                "mode": runs[run_id].snapshot.mode,
                "log_hash": runs[run_id].hash(),
            }
            for run_id in sorted(runs)
        ]
        return _serve(request, {"runs": listed})

    @app.get(f"{API_PREFIX}/runs/{{run_id}}", tags=["runs"])
    def get_run(request: Request, run_id: str) -> Response:
        historian = _run_or_refuse(run_id)
        return _serve(request, _run_view(historian))

    @app.get(f"{API_PREFIX}/runs/{{run_id}}/events", tags=["runs"])
    def get_events(
        request: Request,
        run_id: str,
        limit: Annotated[int, Query(ge=1, le=MAX_PAGE_SIZE)] = DEFAULT_PAGE_SIZE,
        cursor: str | None = None,
        subject: Annotated[list[str] | None, Query()] = None,
        sim_ts_from: Annotated[int | None, Query(ge=0)] = None,
        sim_ts_to: Annotated[int | None, Query(ge=0)] = None,
    ) -> Response:
        _refuse_offset(request)
        historian = _run_or_refuse(run_id)
        page = page_of(
            historian.events(),
            after=_cursor_or_refuse(cursor),
            limit=limit,
            subjects=subject,
            sim_ts_from=sim_ts_from,
            sim_ts_to=sim_ts_to,
        )
        return _serve(
            request,
            {
                "run_id": run_id,
                "events": [_event_view(event) for event in page.events],
                "next_cursor": (
                    None if page.next_cursor is None else encode_cursor(page.next_cursor)
                ),
            },
        )

    # ------------------------------------------------------------------ stream

    @app.get(f"{API_PREFIX}/stream", tags=["stream"])
    def stream(
        request: Request,
        run: str,
        subject: Annotated[list[str] | None, Query()] = None,
    ) -> Response:
        historian = _run_or_refuse(run)
        resume = _cursor_or_refuse(request.headers.get("Last-Event-ID"))
        page = page_of(
            historian.events(),
            after=resume,
            limit=MAX_PAGE_SIZE,
            subjects=subject,
        )
        return StreamingResponse(
            _sse_frames(page.events),
            media_type="text/event-stream",
            headers={"cache-control": "no-store", "x-accel-buffering": "no"},
        )

    # ----------------------------------------------------------------- metrics

    @app.get(f"{API_PREFIX}/metrics/{{metric_id}}", tags=["metrics"])
    def get_metric(request: Request, metric_id: str) -> Response:
        definition = registry.get(metric_id)
        if definition is None:
            raise UNKNOWN_METRIC.raised(
                f"metric {metric_id!r} is not in the registry; the registered ids are "
                f"{', '.join(registry.ids()) or '(none)'}"
            )
        if not definition.evaluable:
            raise METRIC_EXPRESSION_PENDING.raised(
                f"metric {metric_id!r} is registered and its expression is null until "
                f"requirement {EXPRESSION_REQUIREMENT} supplies the expression language; "
                f"the id is stable and a client may keep asking"
            )
        raise METRIC_EXPRESSION_PENDING.raised(
            f"metric {metric_id!r} carries an expression and no evaluator is built; "
            f"requirement {EXPRESSION_REQUIREMENT} owns the evaluator"
        )

    # ------------------------------------------------------------------ config

    @app.get(f"{API_PREFIX}/config", tags=["config"])
    def get_config(request: Request) -> Response:
        return _serve(request, {"config": config})

    @app.post(f"{API_PREFIX}/config", status_code=202, tags=["config"])
    def propose_config(request: Request, proposal: ConfigProposal) -> Response:
        """Record a proposal, or refuse to apply one.

        The tier decision is delegated to `AutonomySession.authorize`, not
        reimplemented. That method is where E5's rules actually hold: the tier
        rises only through a grant a self-elevating caller cannot construct, and
        the held tier is read from the session rather than taken from whoever is
        calling. An `if tier >= 3` here would be a second copy of a rule whose
        whole value is that there is one copy.
        """
        if proposal.apply:
            if autonomy is None:
                raise AUTONOMY_TIER_REFUSES_APPLY.raised(
                    "this server holds no autonomy session, so it holds no authority to "
                    "apply anything; the config:apply scope is never granted below "
                    f"{APPLY_TIER.value} and a server with no session is below every tier"
                )
            try:
                autonomy.authorize(CONFIG_APPLY_TOOL, APPLY_TIER)
            except TierRefused as exc:
                raise AUTONOMY_TIER_REFUSES_APPLY.raised(
                    f"{exc}. The config:apply scope is never granted below "
                    f"{APPLY_TIER.value}; the proposal can be recorded with apply=false "
                    f"and approved by a human"
                ) from exc
            raise GUARDRAIL_EVALUATOR_ABSENT.raised(
                f"this session holds {APPLY_TIER.value} for {CONFIG_APPLY_TOOL}, and "
                f"requirement E5's guardrail evaluator is what decides whether a change is "
                f"inside the guardrails; it is not built, and applying without it would "
                f"claim a check that does not run"
            )
        recorded = {
            "proposal_id": _proposal_id(proposal, at=int(clock.now())),
            "path": proposal.path,
            "value": proposal.value,
            "applied": False,
            "disposition": "recorded",
            "autonomy_tier": (None if autonomy is None else autonomy.effective_tier.value),
            "sim_time": int(clock.now()),
        }
        return JSONResponse(status_code=202, content=recorded)

    # ------------------------------------------------- declared, not installed

    for path, reason in NOT_INSTALLED:
        _install_refusal(app, path, reason)

    return app


def openapi_document(app: FastAPI) -> dict[str, object]:
    """The OpenAPI 3.1 document, as a plain dictionary.

    A pure function of the app rather than a request against a running server,
    because `just api-spec` regenerates `api/openapi.v1.json` in CI and gate
    SEMVER-2 diffs it against the previous tag. Booting a server to produce a
    file that a diff gate reads would make the gate depend on a free port.
    """
    return app.openapi()


# --------------------------------------------------------------------- helpers


def _install_refusal(app: FastAPI, path: str, reason: str) -> None:
    """Register a declared-but-absent route so it answers TF-A020, not 404 prose."""

    async def _refuse() -> Response:
        raise ROUTER_NOT_INSTALLED.raised(
            f"{API_PREFIX}{path} is declared in foundations section 5.13 and is not built "
            f"in this release: {reason}"
        )

    app.add_api_route(
        f"{API_PREFIX}{path}",
        _refuse,
        methods=_NOT_INSTALLED_METHODS,
        include_in_schema=False,
        name=f"not_installed:{path}",
    )


def _refuse_offset(request: Request) -> None:
    if "offset" in request.query_params:
        raise OFFSET_NOT_OFFERED.raised(
            "foundations section 5.13 offers cursor pagination and no other kind; accepting "
            "an offset and ignoring it would serve the first page to a client that asked for "
            "a later one"
        )


def _cursor_or_refuse(text: str | None) -> Cursor | None:
    if text is None or text == "":
        return None
    try:
        return decode_cursor(text)
    except CursorError as exc:
        raise MALFORMED_CURSOR.raised(str(exc)) from exc


def _canonical(payload: object) -> bytes:
    """One body, one spelling. Sorted keys and no incidental whitespace.

    The ETag below is the hash of exactly these bytes. Serializing twice, once
    to hash and once to send, is how an ETag ends up describing a body nobody
    received.
    """
    return json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")


def _etag(body: bytes) -> str:
    return f'"{hashlib.blake2b(body, digest_size=16, person=b"twinflow-api").hexdigest()}"'


def _serve(request: Request, payload: object) -> Response:
    """A GET body with its ETag, and a 304 when the client already has it."""
    body = _canonical(payload)
    tag = _etag(body)
    offered = request.headers.get("if-none-match", "")
    candidates = [part.strip() for part in offered.split(",") if part.strip()]
    if "*" in candidates or tag in candidates:
        return Response(status_code=304, headers={"etag": tag})
    return Response(
        content=body,
        media_type="application/json",
        headers={"etag": tag},
    )


def _run_view(historian: Historian) -> dict[str, object]:
    """The run manifest: the hashed core of doctrine D-01 and nothing else.

    `SnapshotProvenance` carries the wall-clock instants and the host name, and
    it is a sidecar rather than part of the log for exactly the reason it stays
    out of this body: two runs of one config on two machines must compare equal.
    """
    view: dict[str, object] = dict(historian.snapshot.payload())
    view["event_count"] = len(historian)
    view["log_hash"] = historian.hash()
    view["snapshot_hash"] = historian.snapshot.snapshot_hash()
    return view


def _event_view(event: Envelope) -> dict[str, object]:
    """One envelope as a client reads it, with its cursor already computed.

    The cursor travels on every event so a client can resume from any row it
    rendered, rather than only from the end of a page it may not have finished.
    """
    return {
        "id": event.id,
        "run_id": event.twinflowrunid,
        "source": event.source,
        "type": event.type,
        "subject": event.subject,
        "dataschema": event.dataschema,
        "sim_ts": int(event.twinflowsimts),
        "producer_id": event.twinflowproducerid,
        "seq": int(event.twinflowseq),
        "data": event.data,
        "cursor": encode_cursor(Cursor.from_event(event)),
    }


async def _sse_frames(events: Sequence[Envelope]) -> AsyncIterator[bytes]:
    """The live envelope stream, in the canonical order, one frame per event.

    `id:` is the cursor, which is what a browser hands back as `Last-Event-ID`
    after a dropped connection. Any other id would make a reconnect restart the
    stream, and the dashboard would render every event twice.
    """
    yield b": twinflow event stream, canonical order of invariant E4\n\n"
    for event in events:
        frame = (
            f"id: {encode_cursor(Cursor.from_event(event))}\n"
            f"event: {event.type}\n"
            f"data: {json.dumps(_event_view(event), sort_keys=True, separators=(',', ':'))}\n\n"
        )
        yield frame.encode("utf-8")


def _proposal_id(proposal: ConfigProposal, *, at: int) -> str:
    """A hash of the proposal and the sim instant it arrived at.

    Not a `uuid4`. Two replays of one recorded session must produce the same
    proposal id, or the decision register of E21 records two different
    decisions for one act and no run compares equal to another.
    """
    canonical = json.dumps(
        {"at": at, "path": proposal.path, "value": proposal.value},
        sort_keys=True,
        separators=(",", ":"),
        default=str,
    )
    digest = hashlib.blake2b(
        canonical.encode("utf-8"), digest_size=16, person=b"twinflow-prop"
    ).hexdigest()
    return f"prop_{digest}"


__all__ = [
    "API_PREFIX",
    "APPLY_TIER",
    "CONFIG_APPLY_TOOL",
    "NOT_INSTALLED",
    "UNVERSIONED_PATHS",
    "ConfigProposal",
    "create_api",
    "openapi_document",
]
