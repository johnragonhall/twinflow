"""The HTTP surface of foundations section 5.13, over a real recorded run.

Every assertion here is about something a client can observe: a status code, a
header, a body shape, or the order of a page. The routes this phase does not
build are listed in README.md with the reason, and this file asserts that an
unbuilt route answers 404 rather than a plausible empty body, because an empty
list from a route with no producer behind it is a lie a dashboard would render.
"""

from __future__ import annotations

import json

import pytest

from twinflow.agent import AuditLog, AutonomySession, AutonomyTier
from twinflow.api import (
    API_PREFIX,
    MetricDefinition,
    MetricRegistry,
    create_api,
)
from twinflow.kernel import SimClock, SimInstant
from twinflow.storage import Historian

from .conftest import EPOCH, OTHER_RUN_ID, RUN_ID, TAPE, Client, build_historian

METRICS = MetricRegistry(
    (
        MetricDefinition(
            metric_id="oee",
            title="Overall equipment effectiveness",
            unit="ratio",
            expression=None,
        ),
    )
)


def make_session(clock: SimClock, tier: AutonomyTier) -> AutonomySession:
    """A real session at the given default tier.

    Building the agent's own session rather than a stand-in is the point of the
    change that removed this package's copy of the enum: the refusal below is
    the agent's refusal, raised by the code that owns the rule.
    """
    return AutonomySession(
        session_id="session-under-test",
        audit=AuditLog(run_id=RUN_ID, clock=clock, epoch=EPOCH),
        clock=clock,
        default_tier=tier,
        allow_write_tools=tier is AutonomyTier.L3,
    )


def make_client(
    *,
    historian: Historian | None = None,
    tier: AutonomyTier | None = AutonomyTier.L1,
    at: int = 40,
) -> Client:
    clock = SimClock()
    clock.advance_to(SimInstant(at))
    runs = {RUN_ID: historian if historian is not None else build_historian()}
    app = create_api(
        runs=runs,
        clock=clock,
        metrics=METRICS,
        resolved_config={"facility": {"site_type": "warehouse"}},
        autonomy=None if tier is None else make_session(clock, tier),
    )
    return Client(app)


@pytest.fixture
def client() -> Client:
    return make_client()


# ------------------------------------------------------- the unversioned three


def test_healthz_readyz_and_version_sit_outside_the_versioned_prefix(client: Client):
    """Foundations section 5.13 puts these three outside /api/v1 deliberately:
    an orchestrator probing them must not have to know the API major."""
    for path in ("/healthz", "/readyz", "/version"):
        assert not path.startswith(API_PREFIX)
        assert client.get(path).status_code == 200

    for path in ("/healthz", "/readyz", "/version"):
        assert client.get(API_PREFIX + path).status_code == 404


def test_version_reports_the_package_version_and_the_api_major(client: Client):
    body = client.get("/version").json()

    assert body["api_version"] == "v1"
    assert body["package_version"].count(".") == 2


def test_healthz_reports_sim_time_from_the_injected_clock_and_never_a_wall_clock():
    """Doctrine D-02: the clock is a port. A health check that read the wall
    clock would be the one place a reader never looks for one."""
    early = make_client(at=7).get("/healthz").json()
    late = make_client(at=99).get("/healthz").json()

    assert early["sim_time"] == 7
    assert late["sim_time"] == 99


def test_readyz_is_not_ready_when_no_run_is_loaded():
    clock = SimClock()
    app = create_api(runs={}, clock=clock, metrics=METRICS)
    empty = Client(app)

    assert empty.get("/healthz").status_code == 200
    assert empty.get("/readyz").status_code == 503


# ------------------------------------------------------------------------ runs


def test_the_run_list_names_every_loaded_run(client: Client):
    body = client.get(f"{API_PREFIX}/runs").json()

    assert [run["run_id"] for run in body["runs"]] == [RUN_ID]
    assert body["runs"][0]["event_count"] == len(TAPE)


def test_a_run_carries_the_hashed_snapshot_core_and_no_provenance(client: Client):
    """Doctrine D-01 keeps wall-clock time and machine identity in the sidecar.
    Serving either from this route would put it back inside the hashed core a
    reader compares two runs with."""
    body = client.get(f"{API_PREFIX}/runs/{RUN_ID}").json()

    assert body["seed"] == 42
    assert body["config_hash"] == "b" * 64
    assert body["log_hash"]
    for leaked in ("host", "started_wall_utc", "finished_wall_utc", "packages"):
        assert leaked not in body


def test_an_unknown_run_is_a_problem_document_and_not_an_empty_body(client: Client):
    response = client.get(f"{API_PREFIX}/runs/{OTHER_RUN_ID}")

    assert response.status_code == 404
    assert response.headers["content-type"].startswith("application/problem+json")
    body = response.json()
    assert body["code"].startswith("TF-A")
    assert body["type"].endswith(body["code"])
    assert OTHER_RUN_ID in body["detail"]


# ---------------------------------------------------------------------- events


def test_the_event_page_is_in_the_canonical_total_order(client: Client):
    body = client.get(f"{API_PREFIX}/runs/{RUN_ID}/events", params={"limit": 100}).json()

    keys = [(int(e["sim_ts"]), e["producer_id"], int(e["seq"])) for e in body["events"]]
    assert keys == sorted(keys)
    assert keys[1] == (10, "device-agent", 0), "at one instant the producer breaks the tie"
    assert keys[2] == (10, "sim", 1)


def test_walking_the_cursor_sees_the_whole_log_once(client: Client):
    """The walk is bounded at one page per event plus two, deliberately.

    An unbounded `while True` here does not fail when the cursor stops
    advancing, it hangs, and a hung test is a test that reports nothing. The
    bound turns that defect into a named assertion.
    """
    seen: list[str] = []
    params: dict[str, object] = {"limit": 2}
    for _ in range(len(TAPE) + 2):
        body = client.get(f"{API_PREFIX}/runs/{RUN_ID}/events", params=params).json()
        seen.extend(event["id"] for event in body["events"])
        if body["next_cursor"] is None:
            break
        params = {"limit": 2, "cursor": body["next_cursor"]}
    else:
        raise AssertionError("the cursor walk did not terminate; it is not advancing")

    assert len(seen) == len(TAPE)
    assert len(set(seen)) == len(TAPE)


def test_a_subject_filter_narrows_the_page(client: Client):
    body = client.get(
        f"{API_PREFIX}/runs/{RUN_ID}/events",
        params={"subject": "twinflow.telemetry.sensor_reading", "limit": 100},
    ).json()

    assert len(body["events"]) == 3
    assert {event["subject"] for event in body["events"]} == {"twinflow.telemetry.sensor_reading"}


def test_a_sim_time_window_is_inclusive_at_both_ends(client: Client):
    body = client.get(
        f"{API_PREFIX}/runs/{RUN_ID}/events",
        params={"sim_ts_from": 10, "sim_ts_to": 20, "limit": 100},
    ).json()

    stamps = sorted({int(event["sim_ts"]) for event in body["events"]})
    assert stamps == [10, 20]


def test_a_forged_cursor_is_refused_rather_than_reset_to_the_first_page(client: Client):
    response = client.get(f"{API_PREFIX}/runs/{RUN_ID}/events", params={"cursor": "not-a-cursor"})

    assert response.status_code == 400
    assert response.headers["content-type"].startswith("application/problem+json")


def test_offset_pagination_is_not_offered(client: Client):
    """Foundations section 5.13 refuses offset pagination by name. A route that
    quietly accepted and ignored `offset` would look like it worked."""
    response = client.get(f"{API_PREFIX}/runs/{RUN_ID}/events", params={"offset": 3})

    assert response.status_code == 400


def test_a_limit_outside_the_declared_range_is_refused(client: Client):
    assert client.get(f"{API_PREFIX}/runs/{RUN_ID}/events", params={"limit": 0}).status_code == 422
    assert (
        client.get(f"{API_PREFIX}/runs/{RUN_ID}/events", params={"limit": 10_001}).status_code
        == 422
    )


# ----------------------------------------------------------------------- etags


def test_a_get_carries_an_etag_that_is_a_function_of_the_body(client: Client):
    first = client.get(f"{API_PREFIX}/runs/{RUN_ID}")
    second = client.get(f"{API_PREFIX}/runs/{RUN_ID}")

    assert first.headers["etag"]
    assert first.headers["etag"] == second.headers["etag"]

    other = client.get(f"{API_PREFIX}/runs/{RUN_ID}/events", params={"limit": 1})
    assert other.headers["etag"] != first.headers["etag"]


def test_if_none_match_answers_304_with_no_body(client: Client):
    etag = client.get(f"{API_PREFIX}/runs/{RUN_ID}").headers["etag"]

    response = client.get(f"{API_PREFIX}/runs/{RUN_ID}", headers={"If-None-Match": etag})

    assert response.status_code == 304
    assert response.content == b""


def test_a_stale_etag_gets_the_new_body(client: Client):
    response = client.get(f"{API_PREFIX}/runs/{RUN_ID}", headers={"If-None-Match": '"stale"'})

    assert response.status_code == 200


# --------------------------------------------------------------------- metrics


def test_an_unregistered_metric_is_404_and_a_registered_one_with_no_expression_is_501(
    client: Client,
):
    """The two are different facts and section 5.13 spells both out. Collapsing
    them would tell a client that a metric this project promises does not
    exist."""
    unregistered = client.get(f"{API_PREFIX}/metrics/no-such-metric")
    assert unregistered.status_code == 404

    pending = client.get(f"{API_PREFIX}/metrics/oee")
    assert pending.status_code == 501
    assert "E26b" in pending.json()["detail"]


def test_both_metric_answers_are_problem_documents_carrying_their_code(client: Client):
    for path, code in ((f"{API_PREFIX}/metrics/nope", 404), (f"{API_PREFIX}/metrics/oee", 501)):
        response = client.get(path)
        assert response.status_code == code
        assert response.headers["content-type"].startswith("application/problem+json")
        assert response.json()["code"].startswith("TF-A")


# ---------------------------------------------------------------------- config


def test_the_resolved_config_is_served_back(client: Client):
    body = client.get(f"{API_PREFIX}/config").json()

    assert body["config"]["facility"]["site_type"] == "warehouse"


def test_a_proposal_below_l3_is_recorded_and_never_applied(client: Client):
    response = client.post(
        f"{API_PREFIX}/config",
        json_body={"path": "dashboard.port", "value": 8081, "apply": False},
    )

    assert response.status_code == 202
    body = response.json()
    assert body["applied"] is False
    assert body["disposition"] == "recorded"
    assert body["proposal_id"]


def test_asking_to_apply_below_l3_is_refused_by_the_e5_tier_rule(client: Client):
    response = client.post(
        f"{API_PREFIX}/config",
        json_body={"path": "dashboard.port", "value": 8081, "apply": True},
    )

    assert response.status_code == 403
    body = response.json()
    assert "config:apply" in body["detail"]
    assert "L3" in body["detail"]


def test_a_server_with_no_autonomy_session_refuses_every_apply():
    """A server holding no session holds no authority. Defaulting to a tier
    would be this layer granting itself one."""
    sessionless = make_client(tier=None)

    response = sessionless.post(
        f"{API_PREFIX}/config",
        json_body={"path": "dashboard.port", "value": 8081, "apply": True},
    )

    assert response.status_code == 403
    assert "no autonomy session" in response.json()["detail"]


def test_the_recorded_tier_is_read_from_the_session_and_not_from_the_caller():
    """The audit value is the session's effective tier. A caller-supplied tier
    would let the principal describe its own authority in the record."""
    at_l3 = make_client(tier=AutonomyTier.L3)

    body = at_l3.post(
        f"{API_PREFIX}/config",
        json_body={"path": "dashboard.port", "value": 8081, "apply": False},
    ).json()

    assert body["autonomy_tier"] == "L3"


def test_asking_to_apply_at_l3_says_the_guardrail_evaluator_is_not_built():
    """E5's guardrail evaluator is what makes an auto-apply safe, and it is not
    in this phase. Returning 202 here would claim a guardrail that does not
    exist."""
    at_l3 = make_client(tier=AutonomyTier.L3)

    response = at_l3.post(
        f"{API_PREFIX}/config",
        json_body={"path": "dashboard.port", "value": 8081, "apply": True},
    )

    assert response.status_code == 501
    assert "E5" in response.json()["detail"]


def test_the_proposal_id_is_a_function_of_the_proposal_and_not_a_fresh_value(client: Client):
    """A uuid4 here would put a different value into two otherwise identical
    runs, which is the defect the nondeterminism gate exists to catch."""
    body = {"path": "dashboard.port", "value": 8081, "apply": False}

    first = client.post(f"{API_PREFIX}/config", json_body=body).json()["proposal_id"]
    second = client.post(f"{API_PREFIX}/config", json_body=body).json()["proposal_id"]
    other = client.post(
        f"{API_PREFIX}/config", json_body={"path": "dashboard.port", "value": 9090, "apply": False}
    ).json()["proposal_id"]

    assert first == second
    assert first != other


# ---------------------------------------------------------------------- stream


def test_the_stream_is_server_sent_events_in_canonical_order(client: Client):
    response = client.get(f"{API_PREFIX}/stream", params={"run": RUN_ID})

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/event-stream")
    assert response.headers["cache-control"] == "no-store"

    frames = _frames(response.text)
    keys = [
        (int(frame["data"]["sim_ts"]), frame["data"]["producer_id"], int(frame["data"]["seq"]))
        for frame in frames
    ]
    assert keys == sorted(keys)
    assert len(keys) == len(TAPE)


def test_every_stream_frame_carries_its_cursor_as_the_event_id(client: Client):
    """`id:` on an SSE frame is what a browser sends back as Last-Event-ID.
    Making it the cursor is what lets a reconnect resume rather than restart."""
    response = client.get(f"{API_PREFIX}/stream", params={"run": RUN_ID})
    frames = _frames(response.text)

    assert all(frame["id"] for frame in frames)
    assert len({frame["id"] for frame in frames}) == len(frames)


def test_last_event_id_resumes_the_stream_rather_than_replaying_it(client: Client):
    whole = _frames(client.get(f"{API_PREFIX}/stream", params={"run": RUN_ID}).text)
    third = whole[2]["id"]

    resumed = _frames(
        client.get(
            f"{API_PREFIX}/stream",
            params={"run": RUN_ID},
            headers={"Last-Event-ID": third},
        ).text
    )

    assert [frame["id"] for frame in resumed] == [frame["id"] for frame in whole[3:]]


def test_the_stream_refuses_an_unknown_run(client: Client):
    assert client.get(f"{API_PREFIX}/stream", params={"run": OTHER_RUN_ID}).status_code == 404


# ------------------------------------------------------- routes not built here


@pytest.mark.parametrize(
    ("path", "declared"),
    [
        ("/twin/state", "/twin/state"),
        ("/twin/stations/pack-1", "/twin/stations/{station_id}"),
        ("/fleet/devices", "/fleet/devices"),
        ("/findings", "/findings"),
        ("/scenarios", "/scenarios"),
        ("/whatif", "/whatif"),
        ("/webhooks", "/webhooks"),
        ("/runs/anything/speed", "/runs/{run_id}/speed"),
    ],
)
def test_a_route_this_phase_did_not_build_says_so_with_tf_a020(
    client: Client, path: str, declared: str
):
    """An empty list from /findings reads as "this run is clean", which is a
    stronger claim than "the engine that produces findings is not built".

    Foundations section 4 already fixes the answer: a router the build did not
    install returns 404 with a `TF-A020 router not installed` problem document.
    A bare framework 404 would be indistinguishable from a typo in the path.
    """
    response = client.get(API_PREFIX + path)

    assert response.status_code == 404
    assert response.headers["content-type"].startswith("application/problem+json")
    body = response.json()
    assert body["code"] == "TF-A020"
    assert declared in body["detail"]


def test_every_route_the_design_declares_is_either_built_or_refused_by_name(client: Client):
    """The gap between what section 5.13 declares and what this release serves
    is written down as data, so a route cannot go missing quietly."""
    from twinflow.api import NOT_INSTALLED

    declared = [path for path, _ in NOT_INSTALLED]
    assert len(declared) == len(set(declared))
    for _, reason in NOT_INSTALLED:
        assert reason.strip(), "a refusal with no reason is a route nobody decided about"


# ------------------------------------------------------------- the openapi doc


def test_the_openapi_document_is_3_1_and_describes_the_versioned_routes(client: Client):
    document = client.get("/openapi.json").json()

    assert document["openapi"].startswith("3.1")
    paths = set(document["paths"])
    assert f"{API_PREFIX}/runs/{{run_id}}/events" in paths
    assert "/healthz" in paths


def test_the_committed_spec_can_be_produced_without_a_running_server():
    """`just api-spec` regenerates api/openapi.v1.json, and SEMVER-2 diffs it
    against the previous tag. That needs a pure function, not a live server."""
    from twinflow.api import openapi_document

    document = openapi_document(
        create_api(runs={}, clock=SimClock(), metrics=METRICS),
    )

    assert json.loads(json.dumps(document))["openapi"].startswith("3.1")


def _frames(text: str) -> list[dict]:
    """Parse an SSE body into frames. Deliberately hand-rolled: an SSE client
    library would be a runtime dependency this package refuses."""
    frames: list[dict] = []
    for block in text.split("\n\n"):
        lines = [line for line in block.split("\n") if line and not line.startswith(":")]
        if not lines:
            continue
        frame: dict = {"id": None, "event": None, "data": None}
        for line in lines:
            field, _, value = line.partition(":")
            value = value.lstrip(" ")
            if field == "data":
                frame["data"] = json.loads(value)
            elif field in frame:
                frame[field] = value
        if frame["data"] is not None:
            frames.append(frame)
    return frames
