#!/usr/bin/env python3
"""The ten-minute scripted demo behind gate VAL-GATE-DEMO-001.

    just demo                  one pass, the way CI runs it
    just demo 5                five passes, which is what produces the deviation

    uv run python scripts/demo/ten_minute_demo.py --runs 5 --json demo.json

WHAT THIS IS
------------
One headless pass through every package the walking skeleton ships, in the
order a reader meets them: `twinflow.config` loads `profiles/micro_fulfillment.yaml`,
`twinflow.twin` runs the station line at the seed that profile declares,
`twinflow.sensors` publishes onto the six-level namespace and speaks Sparkplug B
over it, `twinflow.storage` records the append-only log, `twinflow.api` serves
that log, and `twinflow.dashboard` renders it and writes one command back.

Nothing here is a stand-in. Every beat calls the shipped surface, so a change
that breaks the walking skeleton breaks this script rather than a mock of it.

WHY EVERY BEAT ASSERTS ON AN OBSERVABLE
---------------------------------------
The gate is falsified by "a run over 600 seconds, or one beat that asserts on a
sleep". Avoiding a sleep by intention is not enough, because intention is not
checkable, so three mechanisms make it structural.

First, a beat reports what it saw as an `Observation`, and the kind of every
observation has to be one of `OBSERVABLE_KINDS`. That set names an event on the
tape, a row in the log, a status code, a rendered element, and nothing else. It
carries no elapsed-time kind, so there is no shape a timing assertion could
take on the way out of a beat.

Second, `sleeping_call_sites` refuses this file and its test if either ever
grows a call to `sleep` or `wait`, and `wall_clock_reads_in_beats` refuses a
beat function that reads a wall clock at all. Both run as a precondition of
every demo run, so the demo fails itself rather than waiting for review.

Third, the stopwatch is held by `measure` and is never placed on the `Stage`
the beats receive. A beat has no route to the elapsed value even if the two
scanners above were deleted.

WHY THE WALL CLOCK IS READ AT ALL
---------------------------------
Once, in `measure`, through `time.perf_counter`. Doctrine D-02 allows a wall
clock in four places and this is the operator-facing one: the value is reported
to whoever ran the demo and to the gate that holds it to 600 seconds. It never
enters an event payload, never enters the hashed tape, and never reaches a beat.
Everything the simulation does reads the injected `SimClock` instead.

Section 7.5 of `docs/design/roadmap.md` asks for more than a pass: the measured
wall time and its run-to-run standard deviation are published beside it, so a
run that clears the budget by one second reads as marginal rather than as green.
`--runs 5` on the reference runner is what produces the deviation. One run has
none, and the report says so rather than printing zero.
"""

from __future__ import annotations

import argparse
import ast
import asyncio
import hashlib
import json
import statistics
import sys
import time
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from html.parser import HTMLParser
from pathlib import Path
from typing import Any
from urllib.parse import urlencode

from twinflow.api import API_PREFIX, create_api
from twinflow.config import UnsPath, load_facility
from twinflow.dashboard import DEMO_PATH, DashboardConfig, create_app
from twinflow.kernel import SimClock, SimInstant
from twinflow.rng import StreamRegistry
from twinflow.schemas import Envelope, check_log_invariants, in_total_order
from twinflow.sensors import (
    DataType,
    EdgeNodeSession,
    MessageType,
    Metric,
    MetricSpec,
    PlausibilityBand,
    PortalReader,
    ReaderConfig,
    SparkplugIds,
    TagRead,
    TemperatureSensor,
    TemperatureSensorConfig,
    topic_for,
)
from twinflow.storage import EVENT_TABLE, ConfigSnapshot, Historian, rows_for, series_for
from twinflow.twin import (
    DistributionSpec,
    PalletArrival,
    StationLineSpec,
    StationSpec,
    run_station_line,
)

REPO_ROOT = Path(__file__).resolve().parents[2]

#: The profile the walking skeleton runs against. One file, so the demo and the
#: quickstart cannot drift into describing two different facilities.
PROFILE = REPO_ROOT / "profiles" / "micro_fulfillment.yaml"

#: The facility contract the profile is validated against, hashed into the run
#: snapshot so a schema revision is visible in the manifest.
FACILITY_SCHEMA_FILE = REPO_ROOT / "schemas" / "config" / "facility" / "v1.json"

#: The budget of section 7.5 of docs/design/roadmap.md, in seconds. Read here
#: rather than passed in, because the gate is falsified by a run over it and a
#: budget a caller could raise is not a budget.
BUDGET_SECONDS = 600.0

#: The sim epoch. Declared rather than read from a clock, for the reason
#: `StationLineSpec.epoch` gives: a value read from a wall clock puts a
#: different number into every run and no two runs of one seed ever agree.
EPOCH = datetime(2026, 1, 1, tzinfo=UTC)

#: The five identifier levels of the two devices, from the concrete topics
#: ARCHITECTURE.md section 5 prints. The parameter level is the device's own.
PORTAL_PREFIX = ("twinflow", "dc-01", "receiving", "inbound-line-01", "portal-03")

#: The temperature channel is addressed at `conveyor-02` rather than at the
#: `temp-01` the profile's comment names. `twinflow.sensors.temperature` ships
#: `motor_temp_c` on the conveyor motor and ships no ambient channel, so a demo
#: publishing `temp-01/temperature_c` would be publishing a device that does not
#: exist. The gap belongs to the sensor catalog work package, not to this file.
TEMPERATURE_PREFIX = ("twinflow", "dc-01", "receiving", "inbound-line-01", "conveyor-02")

#: The declared stream names this demo draws from, quoted from the catalog rows
#: of docs/design/variability-and-faults.md rather than invented here. A stream
#: nobody declared is a stream nobody can reproduce.
PORTAL_READ_RATE_STREAM = "variability.autoid.portal_read_rate"
TEMPERATURE_STREAM = "sensors.temperature_contact"

#: Measurement noise on a contact temperature channel, from the same document's
#: sensor row: `normal(0, 0.35 C)` around the modeled ambient.
AMBIENT_C = 18.0
TEMPERATURE_NOISE_C = 0.35

#: Service times. The facility schema carries no distribution member yet, which
#: the profile's own header records, so the families and parameters are declared
#: here and move into config when that schema grows the member that holds them.
#: Both are lognormal because a duration is strictly positive and right skewed,
#: and `scale_s` is the median rather than the mean, per `DistributionSpec`.
UNLOAD_TIME = DistributionSpec(family="lognormal", scale_s=45.0, shape=0.35)
PUTAWAY_TIME = DistributionSpec(family="lognormal", scale_s=60.0, shape=0.45)

#: Pallets held between the two stations before receiving blocks.
STAGING_CAPACITY = 4

#: How many telemetry windows the two devices close over the horizon. One an
#: hour over an eight-hour shift, which is the publish cadence a dock portal
#: reporting a read-rate ratio would run at.
TELEMETRY_WINDOWS = 8
WINDOW_SECONDS = 3600

#: The observation kinds a beat may report. Closed, and deliberately carrying
#: no elapsed-time member: a beat that wanted to assert on a sleep would have to
#: widen this tuple, and widening it is a diff a reviewer reads.
OBSERVABLE_KINDS: tuple[str, ...] = (
    "config_document",
    "uns_topic",
    "tape_event",
    "event_log_hash",
    "sparkplug_message",
    "log_row",
    "http_status",
    "rendered_element",
)

#: Call names no file in this demo may contain. The tail check catches
#: `time.sleep`, `asyncio.sleep`, and a bare `sleep` imported from either, and
#: the `wait` tail catches the threading primitives that are a sleep with a
#: different name on them.
BANNED_CALL_TAILS = frozenset({"sleep", "wait"})

#: Whole names that are a wait by another route.
BANNED_CALL_NAMES = frozenset({"select.select", "signal.pause", "os.wait", "os.waitpid"})

#: Wall-clock readers. Legal in `measure` and refused inside any beat, which is
#: what makes "no beat asserts on elapsed time" a property of the source rather
#: than a promise in a docstring.
WALL_CLOCK_CALLS = frozenset(
    {"time.perf_counter", "time.monotonic", "time.time", "time.process_time", "time.time_ns"}
)

#: The prefix every beat function carries, so the scanner above knows which
#: functions it is holding to the wall-clock rule.
BEAT_PREFIX = "beat_"


class DemoFailure(AssertionError):
    """A beat observed something other than what the script says happens."""


def require(condition: object, *, expected: str, observed: object) -> None:
    """Fail the beat, naming what was expected and what was there instead.

    Both halves travel. A failure reading "assertion failed" sends the reader
    to the source to find out what the demo thought it was watching, and the
    whole value of a scripted demo is that a reader does not have to.
    """
    if not condition:
        raise DemoFailure(f"expected {expected}, observed {observed!r}")


def _need(value: Any, what: str) -> Any:
    """Read a stage artifact an earlier beat was supposed to have produced."""
    if value is None:
        raise DemoFailure(f"{what} is not on the stage; an earlier beat did not produce it")
    return value


# --------------------------------------------------------------- the observable


@dataclass(frozen=True)
class Observation:
    """One thing a beat saw, and what kind of thing it is.

    `value` is printed in the report, so the reader of a green run sees the
    numbers the beats actually read rather than a row of check marks.
    """

    kind: str
    what: str
    value: object

    def __post_init__(self) -> None:
        if self.kind not in OBSERVABLE_KINDS:
            raise DemoFailure(
                f"observation kind {self.kind!r} is not one of {OBSERVABLE_KINDS}; the set "
                "is closed because gate VAL-GATE-DEMO-001 is falsified by a beat that "
                "asserts on a sleep, and an elapsed-time kind is how that would arrive"
            )


@dataclass(frozen=True)
class Beat:
    """One scripted step, its narration, and the code that performs it."""

    ordinal: int
    name: str
    narration: str
    perform: Callable[[Stage], tuple[Observation, ...]]


@dataclass
class Stage:
    """What the beats hand each other.

    Every field is an artifact of the simulated world. The elapsed wall time is
    not here and cannot be put here by a beat, because `measure` holds it and
    never passes it in.
    """

    profile: Any = None
    topics: tuple[UnsPath, ...] = ()
    clock: SimClock | None = None
    spec: StationLineSpec | None = None
    run: Any = None
    replay_hash: str | None = None
    publications: tuple[tuple[SimInstant, UnsPath, Any], ...] = ()
    session: EdgeNodeSession | None = None
    sparkplug: tuple[Any, ...] = ()
    historian: Historian | None = None
    sensor_events: tuple[Envelope, ...] = ()
    api_client: Client | None = None
    dashboard_client: Client | None = None
    commands: list[Envelope] = field(default_factory=list)
    sidecar: Any = None

    @property
    def run_id(self) -> str:
        return str(_need(self.run, "the station run").run_id)


# ------------------------------------------------------- the structural refusals


def _dotted(node: ast.AST) -> str:
    """Render a call target as a dotted name, or an empty string."""
    parts: list[str] = []
    current = node
    while isinstance(current, ast.Attribute):
        parts.append(current.attr)
        current = current.value
    if isinstance(current, ast.Name):
        parts.append(current.id)
    else:
        return ""
    return ".".join(reversed(parts))


def _tail(node: ast.AST) -> str:
    """The last segment of a call target, whatever the receiver is.

    Separate from `_dotted` because `_dotted` gives up when the receiver is not
    a plain name, and `threading.Event().wait(1)` has a call for a receiver.
    That spelling is a wait like any other, and a scanner that missed it would
    be one working-around away from useless.
    """
    if isinstance(node, ast.Attribute):
        return node.attr
    if isinstance(node, ast.Name):
        return node.id
    return ""


def sleeping_call_sites(path: Path) -> tuple[str, ...]:
    """Every call in this file that waits instead of observing.

    Returned as `path:line name` strings rather than raised, so the caller
    decides what a hit means and so a test can watch this fire on a fixture.
    """
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    found: list[str] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        name = _dotted(node.func)
        tail = _tail(node.func)
        if tail in BANNED_CALL_TAILS or (name and name in BANNED_CALL_NAMES):
            found.append(f"{path.name}:{node.lineno} {name or tail}")
    return tuple(found)


def wall_clock_reads_in_beats(path: Path) -> tuple[str, ...]:
    """Every wall-clock read inside a beat function in this file.

    A beat that can read the wall clock is a beat that can assert on elapsed
    time, which is the second half of what falsifies this gate. Refusing the
    read is stronger than refusing the assertion, because there is one way to
    read a clock and many ways to compare two numbers.
    """
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    found: list[str] = []
    for outer in ast.walk(tree):
        if not isinstance(outer, ast.FunctionDef) or not outer.name.startswith(BEAT_PREFIX):
            continue
        for node in ast.walk(outer):
            if isinstance(node, ast.Call) and _dotted(node.func) in WALL_CLOCK_CALLS:
                found.append(f"{path.name}:{node.lineno} {outer.name} reads {_dotted(node.func)}")
    return tuple(found)


def structural_refusals(paths: Sequence[Path]) -> tuple[str, ...]:
    """Both scanners over both files, as one list of reasons to refuse."""
    reasons: list[str] = []
    for path in paths:
        if not path.is_file():
            continue
        reasons.extend(sleeping_call_sites(path))
        reasons.extend(wall_clock_reads_in_beats(path))
    return tuple(reasons)


def scanned_files() -> tuple[Path, ...]:
    """The files the scanners hold: this demo and the test that runs it."""
    return (Path(__file__).resolve(), REPO_ROOT / "tests" / "test_demo.py")


# ------------------------------------------------------------- the ASGI driver


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
    """Drives an ASGI app directly, with no HTTP client between demo and app.

    The same driver the dashboard and api test tiers use, and for the same
    reason: Starlette's `TestClient` is built on httpx, httpx pulls certifi,
    and certifi is MPL-2.0, which the CONTRIBUTING.md allowlist refuses. An
    ASGI application is an async callable over `(scope, receive, send)`, so the
    forty lines below exercise the real contract with nothing in between.
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
        headers: Mapping[str, str] | None = None,
    ) -> Reply:
        return self.request("POST", path, json_body=json_body, headers=headers)

    def request(
        self,
        method: str,
        path: str,
        *,
        params: Mapping[str, Any] | None = None,
        headers: Mapping[str, str] | None = None,
        json_body: Any = None,
    ) -> Reply:
        raw_headers: list[tuple[bytes, bytes]] = [(b"host", b"testserver")]
        body = b""
        if json_body is not None:
            body = json.dumps(json_body).encode("utf-8")
            raw_headers.append((b"content-type", b"application/json"))
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
            "client": ("demo", 12345),
            "server": ("testserver", 80),
        }
        return asyncio.run(_drive(self._app, scope, body))


def _query_string(params: Mapping[str, Any] | None) -> bytes:
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


class _IdIndex(HTMLParser):
    """Every element carrying an id, keyed by it.

    `html.parser` rather than a dependency, for the reason the dashboard test
    tier gives: section 2.1 of the dashboard design fixes that package's
    dependency list, and a demo that added a parser to see the page would be
    proving the page renders with a tool the shipped install does not have.
    """

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.by_id: dict[str, dict[str, str]] = {}
        self.tags: dict[str, str] = {}

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        mapping = {name: (value if value is not None else "") for name, value in attrs}
        node_id = mapping.get("id")
        if node_id:
            self.by_id[node_id] = mapping
            self.tags[node_id] = tag

    def handle_startendtag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        self.handle_starttag(tag, attrs)


def index_of(markup: str) -> _IdIndex:
    parser = _IdIndex()
    parser.feed(markup)
    parser.close()
    return parser


# ------------------------------------------------------------ the demo material


def arrival_trace(
    *, rate_per_hour: int, horizon_seconds: int, tick_hz: int
) -> tuple[PalletArrival, ...]:
    """The exogenous inbound trace, derived from the profile's declared rate.

    Declared data rather than a draw. `twinflow.twin` takes the arrival trace as
    exogenous on purpose, and the truck and dock-door model that produces one in
    a full facility is a later work package. Inventing a stream here to stand in
    for it would be randomness the stream table of twin-core 5.2 never declared,
    which is exactly the drift the stream registry exists to prevent.
    """
    cadence = 3600 // rate_per_hour
    count = horizon_seconds // cadence
    return tuple(
        PalletArrival(
            pallet_id=f"plt-{index:04d}",
            sku_id=f"sku-{'abc'[index % 3]}",
            qty_units=20 + (index % 5) * 4,
            release_tick=index * cadence * tick_hz,
        )
        for index in range(count)
    )


def line_spec(profile: Mapping[str, Any]) -> StationLineSpec:
    """The modeled line, built from the loaded profile and nothing typed twice."""
    run = profile["run"]
    tick_hz = int(run["tick_hz"])
    stations = {station["id"]: station for station in profile["layout"]["stations"]}
    receiving = stations["inbound-line-01"]
    putaway = stations["putaway-01"]
    rate = int(profile["flows"][0]["arrival_rate_per_hour"])
    return StationLineSpec(
        line_id="inbound-line-01",
        tick_hz=tick_hz,
        epoch=EPOCH,
        receiving=StationSpec(
            station_id=receiving["id"],
            kind="receiving",
            zone_id=receiving["zone"],
            capacity=int(receiving["capacity"]),
            service_time=UNLOAD_TIME,
        ),
        putaway=StationSpec(
            station_id=putaway["id"],
            kind="putaway",
            zone_id=putaway["zone"],
            capacity=int(putaway["capacity"]),
            service_time=PUTAWAY_TIME,
        ),
        staging_capacity=STAGING_CAPACITY,
        arrivals=arrival_trace(
            rate_per_hour=rate,
            horizon_seconds=int(run["horizon_seconds"]),
            tick_hz=tick_hz,
        ),
    )


def _blake(payload: bytes, person: bytes) -> str:
    return hashlib.blake2b(payload, digest_size=32, person=person).hexdigest()


def snapshot_for(
    spec: StationLineSpec, *, run_id: str, seed: int, horizon_ticks: int
) -> ConfigSnapshot:
    """The hashed core of doctrine D-01: the inputs and none of the machine."""
    return ConfigSnapshot(
        run_id=run_id,
        seed=seed,
        replication_index=0,
        mode="simulation",
        config_hash=_blake(PROFILE.read_bytes(), b"twinflow-conf"),
        schema_snapshot_hash=_blake(FACILITY_SCHEMA_FILE.read_bytes(), b"twinflow-schm"),
        # No fault is injected on this pass, and an empty catalog is hashed as
        # the empty catalog rather than left as a plausible-looking constant.
        faults_hash=_blake(b"[]", b"twinflow-flts"),
        profile=PROFILE.relative_to(REPO_ROOT).as_posix(),
        scenario=None,
        tick_hz=spec.tick_hz,
        horizon_ticks=horizon_ticks,
        warmup_ticks=0,
    )


PORTAL_METRICS: tuple[MetricSpec, ...] = (
    MetricSpec(name="dropped_new_epcs", datatype=DataType.UInt32, unit="1"),
    MetricSpec(name="read_rate", datatype=DataType.Float, unit="1", eng_low=0.0, eng_high=1.0),
    MetricSpec(name="reads_total", datatype=DataType.UInt64, unit="1"),
    MetricSpec(name="rssi_mean_dbm", datatype=DataType.Float, unit="dB[mW]"),
    MetricSpec(name="tags_expected", datatype=DataType.UInt32, unit="1"),
    MetricSpec(name="unique_epcs", datatype=DataType.UInt32, unit="1"),
)

TEMPERATURE_METRICS: tuple[MetricSpec, ...] = (
    MetricSpec(name="motor_temp_c", datatype=DataType.Float, unit="Cel"),
    MetricSpec(name="motor_temp_ewma_c", datatype=DataType.Float, unit="Cel"),
)


def epc_for(index: int) -> str:
    """A 96-bit Gen2 identifier for one pallet, as 24 uppercase hex characters."""
    return f"E28011606000{index:012X}"


def sensor_envelope(
    *,
    run_id: str,
    seq: int,
    sim_ts: int,
    tick_hz: int,
    topic: UnsPath,
    source: str,
    value: Any,
) -> Envelope:
    """One reading on the tape, published by the device-agent producer role.

    The `time` attribute is the declared epoch plus sim time. CloudEvents needs
    the attribute and doctrine D-02 forbids the reading, and deriving it from
    the epoch satisfies both without putting a fresh value into every run.
    """
    return Envelope(
        specversion="1.0",
        id=f"{run_id}-device-agent-{seq}",
        source=source,
        type="twinflow.telemetry.sensor_reading",
        time=EPOCH + timedelta(seconds=sim_ts / tick_hz),
        datacontenttype="application/json",
        dataschema="twinflow:schemas/envelope/v1.json",
        subject=topic.topic,
        twinflowsimts=str(sim_ts),
        twinflowrunid=run_id,
        twinflowproducerid="device-agent",
        twinflowseq=str(seq),
        data={
            "series": series_for(topic).key,
            "parameter": topic.parameter,
            "value": value,
        },
    )


# ------------------------------------------------------------------- the beats


def beat_config(stage: Stage) -> tuple[Observation, ...]:
    """`twinflow.config` loads the profile and reports no error diagnostic."""
    document, diagnostics = load_facility(PROFILE, strict=True)
    stage.profile = document
    errors = [str(item) for item in diagnostics]
    require(errors == [], expected="no diagnostic from the shipped profile", observed=errors)
    seed = int(document["run"]["seed"])
    require(seed > 0, expected="a declared run seed", observed=seed)
    stations = [station["id"] for station in document["layout"]["stations"]]
    require(
        stations == ["inbound-line-01", "putaway-01"],
        expected="the two stations the walking skeleton models",
        observed=stations,
    )
    return (
        Observation("config_document", "run.seed", seed),
        Observation("config_document", "run.tick_hz", int(document["run"]["tick_hz"])),
        Observation("config_document", "layout.stations", stations),
    )


def beat_namespace(stage: Stage) -> tuple[Observation, ...]:
    """The six-level namespace is generated from the facility, never typed."""
    facility = {
        "enterprise": PORTAL_PREFIX[0],
        "site": PORTAL_PREFIX[1],
        "areas": [
            {
                "id": PORTAL_PREFIX[2],
                "lines": [
                    {
                        "id": PORTAL_PREFIX[3],
                        "equipment": [
                            {"id": PORTAL_PREFIX[4], "parameters": ["read_rate"]},
                            {"id": TEMPERATURE_PREFIX[4], "parameters": ["motor_temp_c"]},
                        ],
                    }
                ],
            }
        ],
    }
    topics = tuple(UnsPath.from_facility(facility))
    stage.topics = topics
    rendered = [topic.topic for topic in topics]
    require(
        "twinflow/dc-01/receiving/inbound-line-01/portal-03/read_rate" in rendered,
        expected="the portal topic ARCHITECTURE.md section 5 prints",
        observed=rendered,
    )
    require(
        all(len(topic.levels) == 6 for topic in topics),
        expected="six levels on every telemetry topic",
        observed=[len(topic.levels) for topic in topics],
    )
    return tuple(Observation("uns_topic", "generated topic", name) for name in rendered)


def beat_twin(stage: Stage) -> tuple[Observation, ...]:
    """`twinflow.twin` runs the station line at the seed the profile declares."""
    profile = _need(stage.profile, "the loaded profile")
    spec = line_spec(profile)
    stage.spec = spec
    clock = SimClock(tick_hz=spec.tick_hz)
    stage.clock = clock
    horizon_ticks = int(profile["run"]["horizon_seconds"]) * spec.tick_hz
    run = run_station_line(
        spec,
        seed=int(profile["run"]["seed"]),
        replication_index=int(profile["run"]["replication_index"]),
        horizon_ticks=horizon_ticks,
        clock=clock,
    )
    stage.run = run

    types = [event.type for event in run.events]
    require(
        types[0] == "twinflow.twin.model_built",
        expected="the model_built event first on the tape",
        observed=types[:1],
    )
    require(
        "twinflow.twin.activity_completed" in types,
        expected="at least one completed activity",
        observed=sorted(set(types)),
    )
    require(
        run.ledger.is_balanced,
        expected="a balanced material ledger, per INV-TWIN-01",
        observed=run.ledger,
    )
    require(
        run.ledger.units_putaway > 0,
        expected="units reaching storage",
        observed=run.ledger.units_putaway,
    )
    for station_id, spells in sorted(run.traces.items()):
        total = sum(spell.duration_ticks for spell in spells)
        require(
            total == run.end_tick,
            expected=f"{station_id} state spells partitioning [0, {run.end_tick}], per INV-TWIN-09",
            observed=total,
        )
    return (
        Observation("tape_event", "events on the tape", len(run.events)),
        Observation("tape_event", "distinct event types", len(set(types))),
        Observation("tape_event", "units received", run.ledger.units_received),
        Observation("tape_event", "units put away", run.ledger.units_putaway),
        Observation("tape_event", "end tick", run.end_tick),
    )


def beat_determinism(stage: Stage) -> tuple[Observation, ...]:
    """The same seed and the same config produce the same log, per D-05 tier one."""
    spec = _need(stage.spec, "the line spec")
    profile = _need(stage.profile, "the loaded profile")
    run = _need(stage.run, "the station run")
    horizon_ticks = int(profile["run"]["horizon_seconds"]) * spec.tick_hz
    replay = run_station_line(
        spec,
        seed=int(profile["run"]["seed"]),
        replication_index=int(profile["run"]["replication_index"]),
        horizon_ticks=horizon_ticks,
        clock=SimClock(tick_hz=spec.tick_hz),
    )
    from twinflow.schemas import log_hash

    first = log_hash(run.events)
    second = log_hash(replay.events)
    stage.replay_hash = second
    require(
        first == second,
        expected=f"the replay to hash to {first}",
        observed=second,
    )
    require(
        replay.facility_hash == run.facility_hash,
        expected=f"facility hash {run.facility_hash}",
        observed=replay.facility_hash,
    )
    return (
        Observation("event_log_hash", "log hash of both runs", first),
        Observation("event_log_hash", "facility hash", run.facility_hash),
    )


def beat_sensors(stage: Stage) -> tuple[Observation, ...]:
    """`twinflow.sensors` publishes onto the namespace the facility generated."""
    spec = _need(stage.spec, "the line spec")
    run = _need(stage.run, "the station run")
    streams = StreamRegistry(base_seed=run.seed, replication_index=0)
    streams.register(PORTAL_READ_RATE_STREAM)
    streams.register(TEMPERATURE_STREAM)
    read_rate_draws = streams.get(PORTAL_READ_RATE_STREAM)
    temperature_draws = streams.get(TEMPERATURE_STREAM)

    reader = PortalReader(
        config=ReaderConfig(
            sensitivity_dbm=-70,
            # A receiving door that sees six trailers a shift is legitimately
            # quiet for a long time, so the silence threshold is a shift rather
            # than a number that would report every quiet hour as a fault.
            silence_threshold_ticks=WINDOW_SECONDS * spec.tick_hz * TELEMETRY_WINDOWS,
            epc_prefix="E280",
        ),
        uns_prefix=PORTAL_PREFIX,
    )
    sensor = TemperatureSensor(
        config=TemperatureSensorConfig(
            plausibility=PlausibilityBand(low_c=-40.0, high_c=120.0),
            ewma_alpha=0.3,
        ),
        uns_prefix=TEMPERATURE_PREFIX,
    )

    for index, arrival in enumerate(spec.arrivals):
        reader.observe(
            TagRead(
                epc=epc_for(index),
                sim_ts=SimInstant(arrival.release_tick),
                antenna_port=1 + (index % 4),
                rssi_dbm=-70 + (index % 25),
                phase_deg=float((index * 37) % 360),
                read_count=1 + (index % 3),
            )
        )

    # Each point carries the instant its window closed. Recovering that later
    # from a point's position in the list would be arithmetic that quietly
    # stops being true the first time a device publishes a different number of
    # parameters, and the historian would then stamp a reading at the wrong
    # instant with nothing failing.
    published: list[tuple[SimInstant, UnsPath, Any]] = []
    for window in range(1, TELEMETRY_WINDOWS + 1):
        now = SimInstant(window * WINDOW_SECONDS * spec.tick_hz)
        published.extend(
            (now, topic, value)
            for topic, value in reader.publish(
                now=now,
                read_rate=PortalReader.draw_read_rate(read_rate_draws),
                tags_expected=len(spec.arrivals),
            )
        )
        raw_c = AMBIENT_C + float(temperature_draws.normal(0.0, TEMPERATURE_NOISE_C))
        published.extend((now, topic, value) for topic, value in sensor.publish(raw_c, now=now))
    stage.publications = tuple(published)

    topics = sorted({topic.topic for _, topic, _ in published})
    require(
        "twinflow/dc-01/receiving/inbound-line-01/portal-03/read_rate" in topics,
        expected="the portal read rate on its documented topic",
        observed=topics,
    )
    require(
        "twinflow/dc-01/receiving/inbound-line-01/conveyor-02/motor_temp_c" in topics,
        expected="the raw motor temperature beside anything derived from it",
        observed=topics,
    )
    rates = [value for _, topic, value in published if topic.parameter == "read_rate"]
    require(
        all(0.0 <= rate <= 1.0 for rate in rates),
        expected="every read rate inside [0, 1] without a clamp",
        observed=rates,
    )
    require(
        sensor.ewma_c is not None,
        expected="a seeded smoothing filter after the first good reading",
        observed=sensor.ewma_c,
    )
    return (
        Observation("uns_topic", "topics published", len(topics)),
        Observation("uns_topic", "points published", len(published)),
        Observation("uns_topic", "unique tags read", reader.inventory.tracked_epcs),
        Observation("uns_topic", "mean read rate", round(sum(rates) / len(rates), 6)),
    )


def beat_sparkplug(stage: Stage) -> tuple[Observation, ...]:
    """The same readings, addressed as Sparkplug B, with the mirror derived from them."""
    clock = _need(stage.clock, "the sim clock")
    ids = SparkplugIds.for_path(UnsPath.from_prefix(PORTAL_PREFIX, "read_rate"))
    session = EdgeNodeSession(
        group_id=ids.group_id,
        edge_node_id=ids.edge_node_id,
        clock=clock,
        devices={
            PORTAL_PREFIX[4]: PORTAL_METRICS,
            TEMPERATURE_PREFIX[4]: TEMPERATURE_METRICS,
        },
    )
    stage.session = session

    will = session.connect()
    messages = [session.node_birth()]
    messages.append(session.device_birth(PORTAL_PREFIX[4]))
    messages.append(session.device_birth(TEMPERATURE_PREFIX[4]))

    # Report by exception: the DDATA carries the last value of each metric, so
    # the last window wins and an unchanged metric is simply absent.
    latest: dict[str, Any] = {}
    for _, topic, value in _need(stage.publications, "the sensor publications"):
        latest.setdefault(topic.equipment, {})[topic.parameter] = value
    messages.append(session.device_data(PORTAL_PREFIX[4], latest[PORTAL_PREFIX[4]]))
    messages.append(session.device_data(TEMPERATURE_PREFIX[4], latest[TEMPERATURE_PREFIX[4]]))
    stage.sparkplug = tuple(messages)

    require(
        will.message.message_type is MessageType.NDEATH,
        expected="the will registered before anything is published",
        observed=will.message.message_type,
    )
    require(
        messages[0].payload.seq == 0,
        expected="NBIRTH at seq 0",
        observed=messages[0].payload.seq,
    )
    require(
        messages[0].topic == topic_for(session.ids, MessageType.NBIRTH),
        expected="the four-element node topic",
        observed=messages[0].topic,
    )
    data_metrics: tuple[Metric, ...] = messages[-1].payload.metrics
    require(
        all(metric.name is None and metric.alias is not None for metric in data_metrics),
        expected="a DDATA referencing metrics by alias with the name excluded",
        observed=[(metric.name, metric.alias) for metric in data_metrics],
    )
    mirror = session.mirror_records(messages[-2])
    mirror_topics = sorted(record.topic for record in mirror)
    require(
        "twinflow/dc-01/receiving/inbound-line-01/portal-03/read_rate" in mirror_topics,
        expected="the JSON mirror on the plain ISA-95 topic",
        observed=mirror_topics,
    )
    return (
        Observation("sparkplug_message", "session messages", len(messages)),
        Observation("sparkplug_message", "NBIRTH topic", messages[0].topic),
        Observation("sparkplug_message", "alias table size", len(session.alias_table())),
        Observation("sparkplug_message", "mirror records", len(mirror)),
    )


def beat_storage(stage: Stage) -> tuple[Observation, ...]:
    """`twinflow.storage` records both tapes into one append-only log."""
    spec = _need(stage.spec, "the line spec")
    run = _need(stage.run, "the station run")
    clock = _need(stage.clock, "the sim clock")
    profile = _need(stage.profile, "the loaded profile")
    horizon_ticks = int(profile["run"]["horizon_seconds"]) * spec.tick_hz
    historian = Historian(
        clock=clock,
        snapshot=snapshot_for(spec, run_id=run.run_id, seed=run.seed, horizon_ticks=horizon_ticks),
    )
    for event in run.events:
        historian.append(event)

    sensor_events: list[Envelope] = []
    for seq, (device_ts, topic, value) in enumerate(
        _need(stage.publications, "the sensor publications")
    ):
        source = (
            "/twinflow/sensors/portal"
            if topic.equipment == PORTAL_PREFIX[4]
            else "/twinflow/sensors/temperature"
        )
        # The sim stamp is the instant the device closed its window, carried
        # here from the publish rather than reconstructed. Sim time and arrival
        # time are different quantities, and the historian records both.
        envelope = sensor_envelope(
            run_id=run.run_id,
            seq=seq,
            sim_ts=int(device_ts),
            tick_hz=spec.tick_hz,
            topic=topic,
            source=source,
            value=value,
        )
        historian.append(envelope)
        sensor_events.append(envelope)
    stage.sensor_events = tuple(sensor_events)
    stage.historian = historian

    violations = [str(item) for item in historian.violations()]
    require(violations == [], expected="no ENV-001 violation", observed=violations)
    require(
        len(historian) == len(run.events) + len(sensor_events),
        expected=f"{len(run.events) + len(sensor_events)} rows in the log",
        observed=len(historian),
    )
    replayed = historian.replay()
    require(
        list(replayed) == in_total_order(historian.events()),
        expected="the replay in the canonical total order of invariant E4",
        observed="a different order",
    )
    rows = rows_for(historian.events())
    columns = tuple(column.name for column in EVENT_TABLE.columns)
    require(
        tuple(rows[0]) == columns,
        expected=f"batch rows carrying the declared columns {columns}",
        observed=tuple(rows[0]),
    )
    require(
        check_log_invariants(list(replayed)) == [],
        expected="a log the gate's own invariant check accepts",
        observed=check_log_invariants(list(replayed)),
    )
    return (
        Observation("log_row", "rows recorded", len(historian)),
        Observation(
            "log_row", "producers on the log", sorted({e.twinflowproducerid for e in replayed})
        ),
        Observation("log_row", "log hash", historian.hash()),
        Observation("log_row", "first batch row seq", rows[0]["twinflowseq"]),
    )


def beat_api(stage: Stage) -> tuple[Observation, ...]:
    """`twinflow.api` serves the recorded log, paged in the canonical order."""
    historian = _need(stage.historian, "the historian")
    clock = _need(stage.clock, "the sim clock")
    run_id = stage.run_id
    client = Client(create_api(runs={run_id: historian}, clock=clock))
    stage.api_client = client

    ready = client.get("/readyz")
    require(ready.status_code == 200, expected="200 from /readyz", observed=ready.status_code)

    manifest = client.get(f"{API_PREFIX}/runs/{run_id}")
    require(
        manifest.status_code == 200,
        expected=f"200 from {API_PREFIX}/runs/{run_id}",
        observed=manifest.status_code,
    )
    body = manifest.json()
    require(
        body["log_hash"] == historian.hash(),
        expected=f"the served log hash to be {historian.hash()}",
        observed=body["log_hash"],
    )
    require(
        "started_wall_utc" not in body and "host" not in body,
        expected="a run manifest carrying no provenance, per doctrine D-01",
        observed=sorted(body),
    )

    cached = client.get(
        f"{API_PREFIX}/runs/{run_id}", headers={"if-none-match": manifest.headers["etag"]}
    )
    require(
        cached.status_code == 304, expected="304 on a matching ETag", observed=cached.status_code
    )

    seen = 0
    pages = 0
    cursor: str | None = None
    while True:
        params: dict[str, Any] = {"limit": 200}
        if cursor is not None:
            params["cursor"] = cursor
        page = client.get(f"{API_PREFIX}/runs/{run_id}/events", params=params)
        require(
            page.status_code == 200, expected="200 from the events route", observed=page.status_code
        )
        payload = page.json()
        seen += len(payload["events"])
        pages += 1
        cursor = payload["next_cursor"]
        if cursor is None:
            break
    require(
        seen == len(historian),
        expected=f"every one of the {len(historian)} recorded events across the pages",
        observed=seen,
    )

    # A declared route this release does not build answers a problem document
    # naming what it waits on, not an empty list. An empty list would say this
    # facility has no findings, which is a stronger and more dangerous claim
    # than "not built", so the demo watches the code rather than the status.
    refused = client.get(f"{API_PREFIX}/findings")
    require(
        refused.headers.get("content-type", "").startswith("application/problem+json"),
        expected="an RFC 9457 problem document from a route this release does not build",
        observed=refused.headers.get("content-type"),
    )
    refusal_code = refused.json()["code"]
    require(
        refusal_code == "TF-A020",
        expected="the TF-A020 code a router that was never installed answers with",
        observed=refusal_code,
    )

    stream = client.get(f"{API_PREFIX}/stream", params={"run": run_id})
    frames = stream.text.count("\nevent: ")
    require(
        frames == len(historian),
        expected=f"{len(historian)} server-sent frames",
        observed=frames,
    )
    return (
        Observation("http_status", "/readyz", ready.status_code),
        Observation("http_status", "run manifest", manifest.status_code),
        Observation("http_status", "conditional re-read", cached.status_code),
        Observation("http_status", "declared but not installed route", refusal_code),
        Observation("log_row", "events served across pages", seen),
        Observation("log_row", "pages walked", pages),
        Observation("log_row", "server-sent frames", frames),
    )


def beat_dashboard(stage: Stage) -> tuple[Observation, ...]:
    """`twinflow.dashboard` renders the page and answers for its own controls."""
    spec = _need(stage.spec, "the line spec")
    clock = _need(stage.clock, "the sim clock")
    config = DashboardConfig(
        run_id=stage.run_id,
        epoch=EPOCH,
        tick_hz=spec.tick_hz,
        mode="live",
    )
    client = Client(create_app(config, clock=lambda: int(clock.now()), sink=stage.commands.append))
    stage.dashboard_client = client

    page = client.get("/")
    require(
        page.status_code == 200, expected="200 from the dashboard index", observed=page.status_code
    )
    require(
        "connect-src" in page.headers.get("content-security-policy", ""),
        expected="a content security policy naming the api origin",
        observed=page.headers.get("content-security-policy"),
    )

    dom = index_of(page.text)
    missing = [step.control_id for step in DEMO_PATH if step.control_id not in dom.by_id]
    require(
        missing == [],
        expected="every control on the demo path present in the rendered markup",
        observed=missing,
    )
    badge = dom.by_id["tf-synthetic-badge"]
    require(
        badge.get("hidden") is None,
        expected="a provenance badge that is not dismissible",
        observed=badge,
    )

    bootstrap = client.get("/config.json")
    require(
        bootstrap.status_code == 200,
        expected="200 from /config.json",
        observed=bootstrap.status_code,
    )
    boot = bootstrap.json()
    require(
        boot["run_id"] == stage.run_id,
        expected=f"the page bootstrapped onto run {stage.run_id}",
        observed=boot["run_id"],
    )
    require(
        boot["provenance_badge"] == "SYNTHETIC",
        expected="a badge saying what this run is",
        observed=boot["provenance_badge"],
    )
    return (
        Observation("http_status", "dashboard index", page.status_code),
        Observation("http_status", "dashboard bootstrap", bootstrap.status_code),
        Observation("rendered_element", "elements carrying an id", len(dom.by_id)),
        Observation("rendered_element", "demo path controls found", len(DEMO_PATH)),
        Observation("rendered_element", "provenance badge", boot["provenance_badge"]),
    )


def beat_command(stage: Stage) -> tuple[Observation, ...]:
    """The operator pauses the run, and the write lands in the audit log."""
    client = _need(stage.dashboard_client, "the dashboard client")
    accepted = client.post(
        "/api/command",
        json_body={"command_id": "c-0001", "kind": "pause", "data": {}},
    )
    require(
        accepted.status_code == 202,
        expected="202 from the one write path the browser has",
        observed=accepted.status_code,
    )
    body = accepted.json()
    require(
        body["producer_id"] == "dashboard" and body["seq"] == 0,
        expected="the command taking position 0 under the dashboard producer",
        observed=body,
    )
    published = len(stage.commands)
    require(
        published == 1,
        expected="the accepted command reaching the sink",
        observed=published,
    )
    envelope = stage.commands[0]
    require(
        envelope.subject == "ui.command.v1",
        expected="the command envelope published under its subject",
        observed=envelope.subject,
    )

    replayed = client.post(
        "/api/command",
        json_body={"command_id": "c-0001", "kind": "pause", "data": {}},
    )
    require(
        replayed.json()["seq"] == 0,
        expected="a retry of one command_id taking the same position",
        observed=replayed.json()["seq"],
    )

    refused = client.post(
        "/api/command",
        json_body={"command_id": "c-0002", "kind": "set_pref", "data": {"key": "a", "value": "b"}},
    )
    require(
        refused.status_code == 422,
        expected="422 for a browser-handled command that must never reach the log",
        observed=refused.status_code,
    )
    return (
        Observation("http_status", "command accepted", accepted.status_code),
        Observation("http_status", "browser-handled command refused", refused.status_code),
        Observation("log_row", "audited command envelopes", published),
        Observation("log_row", "command id", envelope.data["command_id"]),
    )


def beat_seal(stage: Stage) -> tuple[Observation, ...]:
    """The log is sealed and its provenance is written beside it, never inside."""
    historian = _need(stage.historian, "the historian")
    sidecar = historian.seal(
        # None rather than a reading. Doctrine D-01 puts wall-clock time in the
        # sidecar and D-02 allows the sidecar writer to read one, and this demo
        # reads a wall clock exactly once, in `measure`. A second read here
        # would buy a field nothing in the gate observes.
        started_wall_utc=None,
        finished_wall_utc=None,
        host="reference-runner",
        packages={"twinflow-twin": "0.1.0", "twinflow-storage": "0.1.0"},
    )
    stage.sidecar = sidecar
    require(
        sidecar.event_log_hash == historian.hash(),
        expected=f"the sidecar carrying log hash {historian.hash()}",
        observed=sidecar.event_log_hash,
    )
    require(
        sidecar.event_count == len(historian),
        expected=f"a sidecar event count of {len(historian)}",
        observed=sidecar.event_count,
    )
    require(
        "host" not in historian.snapshot.payload(),
        expected="a hashed core with no machine identity in it",
        observed=sorted(historian.snapshot.payload()),
    )
    require(
        historian.sealed,
        expected="a sealed log",
        observed=historian.sealed,
    )
    return (
        Observation("log_row", "sealed event count", sidecar.event_count),
        Observation("log_row", "sidecar log hash", sidecar.event_log_hash),
        Observation("log_row", "snapshot hash", historian.snapshot.snapshot_hash()),
    )


#: The script, in order. The ordinal is written here rather than inferred from
#: the position, so a beat that is reordered is a beat whose number changed in
#: the diff.
BEATS: tuple[Beat, ...] = (
    Beat(1, "config loads", "the profile validates and declares its seed", beat_config),
    Beat(2, "namespace projects", "topics are generated from the facility", beat_namespace),
    Beat(3, "the line runs", "pallets arrive, unload, stage, and are put away", beat_twin),
    Beat(4, "the run replays", "one seed, one config, one log hash", beat_determinism),
    Beat(5, "devices publish", "the portal and the motor channel reach the UNS", beat_sensors),
    Beat(6, "sparkplug speaks", "births, aliases, and the derived JSON mirror", beat_sparkplug),
    Beat(7, "the historian records", "one append-only log in the canonical order", beat_storage),
    Beat(8, "the api serves", "manifest, paging, the stream, and the refusals", beat_api),
    Beat(9, "the dashboard renders", "the page and every control on the demo path", beat_dashboard),
    Beat(
        10,
        "the operator writes back",
        "one audited command through the one write path",
        beat_command,
    ),
    Beat(11, "the log is sealed", "provenance beside the log, never inside it", beat_seal),
)


# ------------------------------------------------------------------- the runner


@dataclass(frozen=True)
class BeatResult:
    ordinal: int
    name: str
    narration: str
    observations: tuple[Observation, ...]

    def as_dict(self) -> dict[str, object]:
        return {
            "ordinal": self.ordinal,
            "name": self.name,
            "narration": self.narration,
            "observations": [
                {"kind": item.kind, "what": item.what, "value": item.value}
                for item in self.observations
            ],
        }


@dataclass(frozen=True)
class DemoReport:
    """One or more passes, their measured wall times, and the gate's verdict."""

    durations_s: tuple[float, ...]
    beats: tuple[BeatResult, ...]
    budget_s: float = BUDGET_SECONDS

    @property
    def wall_s(self) -> float:
        """The slowest pass. The budget is held against the worst run, not the best."""
        return max(self.durations_s)

    @property
    def mean_s(self) -> float:
        return statistics.fmean(self.durations_s)

    @property
    def stdev_s(self) -> float | None:
        """The run-to-run standard deviation, or None when one run cannot have one.

        None rather than 0.0. Section 7.5 asks for the deviation beside the
        measurement so a run that clears its budget by a second reads as
        marginal, and a printed zero from a single run would claim a stability
        nobody measured.
        """
        if len(self.durations_s) < 2:
            return None
        return statistics.stdev(self.durations_s)

    @property
    def within_budget(self) -> bool:
        return self.wall_s < self.budget_s

    def as_dict(self) -> dict[str, object]:
        return {
            "gate": "VAL-GATE-DEMO-001",
            "budget_s": self.budget_s,
            "runs": len(self.durations_s),
            "durations_s": [round(value, 3) for value in self.durations_s],
            "wall_s": round(self.wall_s, 3),
            "mean_s": round(self.mean_s, 3),
            "stdev_s": None if self.stdev_s is None else round(self.stdev_s, 3),
            "stdev_note": (
                "a single run has no run-to-run deviation; --runs 5 on the reference "
                "runner is what produces one"
                if self.stdev_s is None
                else "sample standard deviation over the runs above"
            ),
            "beat_count": len(self.beats),
            "within_budget": self.within_budget,
            "beats": [beat.as_dict() for beat in self.beats],
        }


def run_beats() -> tuple[BeatResult, ...]:
    """One pass through the script, refusing anything that is not an observable."""
    stage = Stage()
    results: list[BeatResult] = []
    for beat in BEATS:
        try:
            observations = beat.perform(stage)
        except DemoFailure as failure:
            raise DemoFailure(f"beat {beat.ordinal} ({beat.name}): {failure}") from failure
        if not observations:
            raise DemoFailure(
                f"beat {beat.ordinal} ({beat.name}) reported nothing it observed; a beat "
                "that observes nothing is a beat that cannot fail"
            )
        results.append(BeatResult(beat.ordinal, beat.name, beat.narration, tuple(observations)))
    return tuple(results)


def measure(runs: int = 1) -> DemoReport:
    """Run the script `runs` times and report what the wall clock said.

    This is the only wall-clock read in the file. It is the operator-facing one
    doctrine D-02 permits, the value never reaches an event or a beat, and the
    two structural refusals below run first so a demo that has grown a sleep
    fails before it has a duration to report.
    """
    refusals = structural_refusals(scanned_files())
    if refusals:
        raise DemoFailure(
            "this demo refuses to run: gate VAL-GATE-DEMO-001 is falsified by a beat that "
            "asserts on a sleep, and these call sites are how that arrives:\n  "
            + "\n  ".join(refusals)
        )
    if runs < 1:
        raise DemoFailure(f"--runs is a count of passes and {runs} is not one")

    durations: list[float] = []
    beats: tuple[BeatResult, ...] = ()
    for _ in range(runs):
        started = time.perf_counter()
        beats = run_beats()
        durations.append(time.perf_counter() - started)
    return DemoReport(durations_s=tuple(durations), beats=beats)


def render(report: DemoReport) -> str:
    """The operator-facing report: every beat, what it saw, and the wall time."""
    lines = ["twinflow ten-minute demo, VAL-GATE-DEMO-001", ""]
    for beat in report.beats:
        lines.append(f"  beat {beat.ordinal:>2}  {beat.name}: {beat.narration}")
        for item in beat.observations:
            lines.append(f"           [{item.kind}] {item.what} = {item.value}")
    lines.append("")
    lines.append(f"  runs           {len(report.durations_s)}")
    lines.append(f"  durations (s)  {[round(value, 3) for value in report.durations_s]}")
    lines.append(f"  wall time (s)  {report.wall_s:.3f}   budget {report.budget_s:.0f}")
    lines.append(f"  mean (s)       {report.mean_s:.3f}")
    if report.stdev_s is None:
        lines.append(
            "  stdev (s)      not measured: one run has no run-to-run deviation. "
            "Use --runs 5 on the reference runner"
        )
    else:
        lines.append(f"  stdev (s)      {report.stdev_s:.3f}")
    lines.append("")
    verdict = "PASS" if report.within_budget else "FAIL"
    lines.append(f"  {verdict}: {len(report.beats)} beats, every one on an observable")
    return "\n".join(lines)


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument(
        "--runs",
        type=int,
        default=1,
        help="passes to time. Five on the reference runner is what produces the deviation "
        "section 7.5 asks to be published beside the measurement",
    )
    parser.add_argument(
        "--json", type=Path, default=None, help="also write the report as JSON here"
    )
    args = parser.parse_args(argv)

    try:
        report = measure(runs=args.runs)
    except DemoFailure as failure:
        print(f"demo failed: {failure}", file=sys.stderr)
        return 1

    print(render(report))
    if args.json is not None:
        args.json.write_text(json.dumps(report.as_dict(), indent=2, default=str), encoding="utf-8")

    if not report.within_budget:
        print(
            f"demo failed: {report.wall_s:.3f}s is over the {report.budget_s:.0f}s budget of "
            "section 7.5 of docs/design/roadmap.md",
            file=sys.stderr,
        )
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
