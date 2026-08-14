"""One recorded run, built once, for every test in this package.

The fixtures build a real `twinflow.storage.Historian` rather than a stand-in.
The pagination contract of foundations section 5.13 is a claim about the
canonical total order of invariant E4, and a hand-rolled list of dictionaries
would let this package's tests agree with themselves while disagreeing with the
log the historian actually hands out.
"""

from __future__ import annotations

import asyncio
import json
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any
from urllib.parse import urlencode

import pytest

from twinflow.kernel import SimClock, SimInstant
from twinflow.schemas import Envelope, ProducerId
from twinflow.storage import ConfigSnapshot, Historian

#: The sim epoch. Declared rather than read from a clock, for the reason
#: `StationLineSpec.epoch` gives: a default read from a wall clock puts a
#: different value into two runs of one seed.
EPOCH = datetime(2026, 1, 1, tzinfo=UTC)

RUN_ID = "run_01jabcdefghijklmnopqrstuvw"
OTHER_RUN_ID = "run_01jzzzzzzzzzzzzzzzzzzzzzzz"

#: Two producers emitting at overlapping sim instants, which is the only shape
#: that can tell a three-part cursor from a two-part one. With one producer any
#: cursor implementation passes.
TAPE: tuple[tuple[ProducerId, int, int, str], ...] = (
    # producer, sim_ts, seq, subject
    ("sim", 0, 0, "twinflow.twin.model_built"),
    ("sim", 10, 1, "twinflow.twin.pallet_created"),
    ("device-agent", 10, 0, "twinflow.telemetry.sensor_reading"),
    ("sim", 10, 2, "twinflow.twin.activity_started"),
    ("device-agent", 20, 1, "twinflow.telemetry.sensor_reading"),
    ("sim", 20, 3, "twinflow.twin.activity_completed"),
    ("sim", 30, 4, "twinflow.twin.wip_sampled"),
    ("device-agent", 30, 2, "twinflow.telemetry.sensor_reading"),
    ("sim", 40, 5, "twinflow.twin.resource_state"),
)


def make_snapshot(run_id: str = RUN_ID) -> ConfigSnapshot:
    return ConfigSnapshot(
        run_id=run_id,
        seed=42,
        replication_index=0,
        mode="simulation",
        config_hash="b" * 64,
        schema_snapshot_hash="c" * 64,
        faults_hash="d" * 64,
        profile="profiles/micro_fulfillment.yaml",
        scenario="SCN-F1",
        tick_hz=1_000_000,
        horizon_ticks=86_400_000_000,
        warmup_ticks=0,
    )


def make_event(
    *,
    producer: ProducerId,
    sim_ts: int,
    seq: int,
    subject: str,
    run_id: str = RUN_ID,
) -> Envelope:
    return Envelope(
        specversion="1.0",
        id=f"{run_id}-{producer}-{seq}",
        source="/twinflow/twin/station",
        type=subject,
        time=datetime(2026, 1, 1, tzinfo=UTC),
        datacontenttype="application/json",
        subject=subject,
        dataschema="twinflow:schemas/twin/station/v1.json",
        twinflowsimts=str(sim_ts),
        twinflowrunid=run_id,
        twinflowproducerid=producer,
        twinflowseq=str(seq),
        data={"seq": seq, "producer": producer},
    )


def build_historian(
    tape: tuple[tuple[ProducerId, int, int, str], ...] = TAPE,
    *,
    run_id: str = RUN_ID,
) -> Historian:
    clock = SimClock()
    historian = Historian(clock=clock, snapshot=make_snapshot(run_id))
    for producer, sim_ts, seq, subject in tape:
        clock.advance_to(SimInstant(sim_ts))
        historian.append(
            make_event(producer=producer, sim_ts=sim_ts, seq=seq, subject=subject, run_id=run_id)
        )
    return historian


@pytest.fixture
def historian() -> Historian:
    return build_historian()


@pytest.fixture
def clock() -> SimClock:
    moving = SimClock()
    moving.advance_to(SimInstant(40))
    return moving


# ------------------------------------------------------------------ ASGI driver


@dataclass(frozen=True)
class Reply:
    """One HTTP response, collected from the ASGI messages the app sent."""

    status_code: int
    headers: Mapping[str, str]
    content: bytes

    @property
    def text(self) -> str:
        return self.content.decode("utf-8")

    def json(self) -> Any:
        return json.loads(self.content)


class Client:
    """Drives an ASGI app directly, with no HTTP client between test and app.

    Starlette ships a `TestClient` and it is not used here, for a licensing
    reason that is a project rule rather than a preference. That client is built
    on httpx, httpx depends on certifi, and certifi is MPL-2.0. The
    CONTRIBUTING.md allowlist refuses copyleft in the shipped tree, and the
    owner's ruling extends that to the development closure unless it is
    unavoidable. Here it is avoidable in about forty lines.

    Driving the app directly is also the stricter test. An ASGI application is
    an async callable over `(scope, receive, send)`, and this exercises that
    contract with nothing in between: the scope is built here, the request body
    is fed through `receive`, and the status, headers, and body come back as the
    `http.response.start` and `http.response.body` messages the app actually
    emitted. A streaming response arrives as the several body messages it really
    sends, which is how the server-sent-event tests see more than one frame.
    """

    def __init__(self, app: Any) -> None:
        self._app = app

    def get(
        self,
        path: str,
        *,
        params: Mapping[str, Any] | None = None,
        headers: Mapping[str, str] | None = None,
    ) -> Reply:
        return self.request("GET", path, params=params, headers=headers)

    def post(
        self,
        path: str,
        *,
        json_body: Any = None,
        content: bytes | None = None,
        params: Mapping[str, Any] | None = None,
        headers: Mapping[str, str] | None = None,
    ) -> Reply:
        return self.request(
            "POST", path, params=params, headers=headers, json_body=json_body, content=content
        )

    def request(
        self,
        method: str,
        path: str,
        *,
        params: Mapping[str, Any] | None = None,
        headers: Mapping[str, str] | None = None,
        json_body: Any = None,
        content: bytes | None = None,
    ) -> Reply:
        raw_headers: list[tuple[bytes, bytes]] = [(b"host", b"testserver")]
        body = b""
        if json_body is not None:
            body = json.dumps(json_body).encode("utf-8")
            raw_headers.append((b"content-type", b"application/json"))
        elif content is not None:
            body = content
        if body:
            raw_headers.append((b"content-length", str(len(body)).encode("ascii")))
        for name, value in (headers or {}).items():
            raw_headers.append((name.lower().encode("ascii"), value.encode("utf-8")))

        scope = {
            "type": "http",
            "asgi": {"version": "3.0", "spec_version": "2.3"},
            "http_version": "1.1",
            "method": method,
            "scheme": "http",
            "path": path,
            "raw_path": path.encode("utf-8"),
            "query_string": _query_string(params),
            "root_path": "",
            "headers": raw_headers,
            "client": ("test", 12345),
            "server": ("testserver", 80),
        }
        return asyncio.run(_drive(self._app, scope, body))


def _query_string(params: Mapping[str, Any] | None) -> bytes:
    """Encode query parameters, repeating a key for each value in a list.

    Repetition rather than a comma-joined value, because that is how a browser
    sends a repeated parameter and how the routes read `subject`.
    """
    if not params:
        return b""
    pairs: list[tuple[str, str]] = []
    for key in params:
        value = params[key]
        if isinstance(value, (list, tuple)):
            pairs.extend((key, str(item)) for item in value)
        else:
            pairs.append((key, str(value)))
    return urlencode(pairs).encode("ascii")


async def _drive(app: Any, scope: dict[str, Any], body: bytes) -> Reply:
    """Run one request through the app and collect what it sent back."""
    delivered = False
    status = 0
    headers: dict[str, str] = {}
    chunks: list[bytes] = []

    async def receive() -> dict[str, Any]:
        nonlocal delivered
        if delivered:
            return {"type": "http.disconnect"}
        delivered = True
        return {"type": "http.request", "body": body, "more_body": False}

    async def send(message: Mapping[str, Any]) -> None:
        nonlocal status
        if message["type"] == "http.response.start":
            status = int(message["status"])
            for name, value in message.get("headers", ()):
                headers[name.decode("latin-1").lower()] = value.decode("latin-1")
        elif message["type"] == "http.response.body":
            chunks.append(bytes(message.get("body", b"")))

    await app(scope, receive, send)
    return Reply(status_code=status, headers=headers, content=b"".join(chunks))
