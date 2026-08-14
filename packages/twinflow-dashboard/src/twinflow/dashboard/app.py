"""The dashboard stub: one HTML file, a bootstrap document, and one write path.

Requirement 8 asks for a single-file dashboard with no build step, and
`docs/design/ui-direction.md` section 2.3 argues that decision through rather
than inheriting it: a bundle would make the tested source stop being the shipped
source, and the browser unit tier of the contract page works by extracting the
shipped `<script>` blocks and evaluating them in `node:vm`. So `assets/index.html`
is served byte for byte off disk, and everything this process knows about the
deployment reaches the page as JSON from `/config.json` rather than as a
substitution into the markup.

Requirement R32 is the reason this package holds no query logic at all: building
the dashboard against internal calls and inserting an API later rewrites every
dashboard test. The page reads `twinflow-api` over HTTP from the browser,
`twinflow.dashboard` never imports `twinflow.api`, and boundary rule A1.2 puts
both in the `apps` tier as peers so the import graph refuses the shortcut.

The one thing this process does own is `POST /api/command`, which section 4.2 of
`docs/design/dashboard-replay.md` makes the only write path from the browser.
SECURITY.md's threat-model note depends on that being true: every `kind` is
schema-validated here, and the dashboard container has no route to the OT
network.
"""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import Any

from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import JSONResponse, Response
from starlette.routing import Route

from twinflow.dashboard.commands import CommandError, CommandLog, validate_command
from twinflow.dashboard.config import DashboardConfig
from twinflow.schemas import Envelope

#: The single file requirement 8 names. One file, so a reader who wants to see
#: what the dashboard is opens one thing.
INDEX_FILENAME = "index.html"

#: The one media type `POST /api/command` accepts. Named rather than inlined
#: because the refusal message and the check have to agree.
JSON_MEDIA_TYPE = "application/json"

#: Section 5.2.2 of the design page ships two content security policies, because
#: a static host cannot set a response header and the live server can. This is
#: the served one. `unsafe-inline` is the cost of the no-build decision and is
#: named here rather than left for a reviewer to discover: the script and the
#: style are inline because the file is the artifact, and a nonce would have to
#: be injected into the markup, which is the substitution this design refuses.
CSP_TEMPLATE = (
    "default-src 'none'; "
    "script-src 'unsafe-inline'; "
    "style-src 'unsafe-inline'; "
    "img-src 'self' data:; "
    "font-src 'self'; "
    "connect-src 'self' {api_origin}; "
    "form-action 'none'; "
    "frame-ancestors 'none'; "
    "base-uri 'none'"
)


def viewer_asset_root() -> Path:
    """Where the shipped viewer assets live.

    Exposed as a function rather than a constant because the design registers it
    on the `twinflow.viewer_assets` entry-point group: `twinflow-view3d` and
    `twinflow-replay` exchange assets with this package through entry points
    rather than imports, since an import would create the cycle boundary rule
    A1.2 forbids and would break the install-alone claim D-10 tests.
    """
    return Path(__file__).resolve().parent / "assets"


def index_html() -> str:
    """The shipped page, read off disk unchanged."""
    return (viewer_asset_root() / INDEX_FILENAME).read_text(encoding="utf-8")


def create_app(
    config: DashboardConfig,
    *,
    clock: Callable[[], int],
    sink: Callable[[Envelope], None] | None = None,
) -> Starlette:
    """Build the ASGI application for one dashboard deployment.

    `clock` returns the current sim instant in ticks. It is a plain callable
    rather than the kernel's `Clock` port on purpose: section 2.1 of the design
    page fixes this package's dependencies at starlette, uvicorn, pydantic, and
    `twinflow-schemas`, and taking the kernel for one method would pull numpy
    into an install whose whole claim is that it is small. What matters for
    doctrine D-02 is that the reading arrives from outside, and it does.

    `sink` is where an accepted command goes. In production it is the seam the
    historian sits behind. Defaulting it to a list rather than to a no-op is
    deliberate: a dropped command that returned 202 would be an audit-log hole
    that nothing observes.
    """
    log = CommandLog(run_id=config.run_id, epoch=config.epoch, tick_hz=config.tick_hz)
    recorded: list[Envelope] = []
    publish = sink if sink is not None else recorded.append

    async def index(_: Request) -> Response:
        return Response(
            content=index_html(),
            media_type="text/html; charset=utf-8",
            headers={
                "content-security-policy": CSP_TEMPLATE.format(
                    api_origin=config.api_base_url.rstrip("/")
                ),
                "referrer-policy": "no-referrer",
                "x-content-type-options": "nosniff",
            },
        )

    async def bootstrap(_: Request) -> Response:
        return JSONResponse(config.bootstrap(), headers={"cache-control": "no-store"})

    async def healthz(_: Request) -> Response:
        return JSONResponse({"status": "ok", "sim_time": int(clock())})

    async def command(request: Request) -> Response:
        """The browser's only write path. Prove it is ours, validate, then assign
        a position."""
        refusal = _cross_site_refusal(request)
        if refusal is not None:
            return _refused(refusal)
        media_type = request.headers.get("content-type", "").split(";", 1)[0].strip().lower()
        if media_type != JSON_MEDIA_TYPE:
            return _unsupported_media_type(media_type)

        try:
            payload: Any = await request.json()
        except ValueError:
            return _invalid(("the request body is not JSON",))
        if not isinstance(payload, dict):
            return _invalid(("the request body must be a JSON object",))

        try:
            kind = validate_command(payload, mode=config.mode)
        except CommandError as exc:
            return _invalid(exc.reasons)

        accepted, envelope = log.record(payload, kind=kind, sim_time=int(clock()))
        # None means this command_id already holds a position, so its event is
        # already on the log. Publishing again repeats an event id the log
        # holds, which the historian refuses.
        if envelope is not None:
            publish(envelope)
        return JSONResponse(
            {
                "command_id": accepted.command_id,
                "kind": accepted.kind,
                "producer_id": accepted.producer_id,
                "seq": accepted.seq,
                "sim_time": accepted.sim_time,
                "audited": accepted.audited,
            },
            status_code=202,
        )

    app = Starlette(
        routes=[
            Route("/", index, methods=["GET"]),
            Route("/config.json", bootstrap, methods=["GET"]),
            Route("/healthz", healthz, methods=["GET"]),
            Route("/api/command", command, methods=["POST"]),
        ]
    )
    #: Reachable by a caller that wants what this process recorded without
    #: installing a sink, which is what makes the default observable.
    app.state.recorded = recorded
    app.state.config = config
    return app


def serve(config: DashboardConfig, *, clock: Callable[[], int]) -> None:  # pragma: no cover
    """Run the dashboard on the configured address.

    uvicorn is imported here rather than at module scope so that importing this
    package costs nothing but starlette, and a reader embedding `create_app` in
    their own server never loads a second one.
    """
    import uvicorn

    uvicorn.run(create_app(config, clock=clock), host=config.bind, port=config.port)


def _cross_site_refusal(request: Request) -> str | None:
    """Why this write should not be honored, or nothing if it is same-origin.

    `POST /api/command` carries no credential, so the browser will send it for
    anyone who asks. Without this check any page the operator has open can drive
    the dashboard: a form post or a `text/plain` fetch is a CORS *simple*
    request, so it is delivered without a preflight and the reply being
    unreadable does not undo the write. The audit log is append-only, which
    makes a forged entry permanent.

    Two independent signals, because each covers the other's gap. `Origin` is
    sent on every cross-origin POST but is also sent same-origin by some
    browsers, so it is compared rather than merely required. `Sec-Fetch-Site` is
    set by the browser and cannot be spoofed by page script, but is absent on
    clients that are not browsers. A request carrying neither is not a browser
    request at all, and the media-type check at the call site is what stands in
    front of it.
    """
    site = request.headers.get("sec-fetch-site")
    if site is not None and site != "same-origin":
        return f"sec-fetch-site is {site!r}, and this endpoint answers same-origin requests only"

    origin = request.headers.get("origin")
    if origin is not None and origin != f"{request.url.scheme}://{request.url.netloc}":
        return f"origin {origin!r} is not this dashboard"
    return None


def _refused(reason: str) -> Response:
    """403 for a write that did not come from this dashboard's own page."""
    return JSONResponse({"errors": [reason]}, status_code=403)


def _unsupported_media_type(media_type: str) -> Response:
    """415 for a body this endpoint does not accept.

    Requiring `application/json` is a control rather than pedantry: it is the
    media type that takes a cross-origin POST out of the CORS simple-request set
    and forces a preflight, which this app answers for nobody.
    """
    return JSONResponse(
        {
            "errors": [
                f"content-type must be {JSON_MEDIA_TYPE}, got {media_type or 'nothing'!r}",
            ]
        },
        status_code=415,
    )


def _invalid(reasons: tuple[str, ...]) -> Response:
    """422 with the validation error, as section 4.2 specifies.

    Every reason travels at once. A browser that learned one mistake per round
    trip would write one audit-log entry per attempt on the surface whose whole
    purpose is being auditable.
    """
    return JSONResponse({"errors": list(reasons)}, status_code=422)
