"""The three routes this process serves, and the one it writes through.

The dashboard holds no query logic. Requirement R32 says building it against
internal calls and inserting an API later rewrites every dashboard test, so the
page reads `twinflow-api` over HTTP and this process serves the file, the
bootstrap, and the command path. The tests below are about exactly those.
"""

from __future__ import annotations

import json

import pytest

from twinflow.dashboard import COMMAND_PRODUCER, create_app

from .conftest import Client, StepClock, make_config


@pytest.fixture
def clock() -> StepClock:
    return StepClock(at=1_000_000)


def make_client(clock: StepClock, **overrides) -> Client:
    recorded: list = []
    app = create_app(make_config(**overrides), clock=clock, sink=recorded.append)
    client = Client(app)
    client.recorded = recorded  # type: ignore[attr-defined]
    return client


@pytest.fixture
def client(clock: StepClock) -> Client:
    return make_client(clock)


# --------------------------------------------------------------- the page itself


def test_the_page_is_served_byte_for_byte_off_disk(client: Client):
    """Section 5.2 of the design page extracts the shipped `<script>` blocks and
    evaluates them in node:vm. That only tests the shipped artifact while the
    file being served is the file on disk, so nothing is substituted in."""
    from twinflow.dashboard import index_html

    response = client.get("/")

    assert response.status_code == 200
    assert response.text == index_html()


def test_the_page_carries_a_content_security_policy_naming_the_api_origin(client: Client):
    response = client.get("/")

    policy = response.headers["content-security-policy"]
    assert "default-src 'none'" in policy
    assert "connect-src 'self' http://127.0.0.1:8000" in policy
    assert "frame-ancestors 'none'" in policy


def test_the_deployment_facts_reach_the_page_as_json_and_not_as_markup(client: Client):
    """The alternative, substituting the API origin into the HTML, would make
    the served file differ from the tested one."""
    body = client.get("/config.json").json()

    assert body["api_base_url"] == "http://127.0.0.1:8000"
    assert body["provenance_badge"] == "SYNTHETIC"
    assert body["speed_presets"][0] == 0.0
    assert client.get("/").text.count("127.0.0.1:8000") == 0


def test_the_badge_names_the_physical_device_count_when_a_real_device_is_in_the_fleet(
    clock: StepClock,
):
    """A badge reading "synthetic" over a tile driven by a hand touching a real
    sensor is a false statement on the most-shared clip this repository will
    produce."""
    hybrid = make_client(clock, provenance="hybrid_hil", physical_device_count=2)

    assert hybrid.get("/config.json").json()["provenance_badge"] == "SYNTHETIC + 2 PHYSICAL"


def test_healthz_reports_the_injected_sim_clock(client: Client, clock: StepClock):
    clock.at = 42

    assert client.get("/healthz").json()["sim_time"] == 42


# ------------------------------------------------------------- POST /api/command


def command(kind: str = "set_speed", data: dict | None = None, command_id: str = "c-0001") -> dict:
    return {
        "command_id": command_id,
        "kind": kind,
        "data": {"speed": 4.0} if data is None else data,
    }


def test_an_accepted_command_answers_202_with_its_assigned_position(client: Client):
    """Section 4.2: the response is 202 plus the assigned (producer_id, seq)."""
    response = client.post("/api/command", json_body=command())

    assert response.status_code == 202
    body = response.json()
    assert body["producer_id"] == COMMAND_PRODUCER
    assert body["seq"] == 0
    assert body["audited"] is True


def test_the_sequence_is_dense_per_producer(client: Client):
    """Doctrine D-07, and what `Historian.append` refuses a gap in."""
    seqs = [
        client.post("/api/command", json_body=command(command_id=f"c-{index:04d}")).json()["seq"]
        for index in range(1, 5)
    ]

    assert seqs == [0, 1, 2, 3]


def test_replaying_a_command_id_returns_the_original_position(client: Client):
    """Commands are idempotent by `command_id`, so a retry after a dropped
    response must not take a second sequence number."""
    first = client.post("/api/command", json_body=command()).json()
    again = client.post("/api/command", json_body=command()).json()

    assert first == again
    assert len(client.recorded) == 2  # type: ignore[attr-defined]
    assert client.recorded[0].id == client.recorded[1].id  # type: ignore[attr-defined]


def test_the_recorded_envelope_carries_sim_time_and_no_wall_clock_reading(
    client: Client, clock: StepClock
):
    """Requirement C1 needs the log byte-identical from a seed, and a wall-clock
    stamp inside it makes that false by construction."""
    clock.at = 2_000_000

    client.post("/api/command", json_body=command())
    envelope = client.recorded[0]  # type: ignore[attr-defined]

    assert envelope.twinflowsimts == "2000000"
    assert envelope.twinflowproducerid == COMMAND_PRODUCER
    assert envelope.data["sim_time"] == 2_000_000
    assert envelope.time.isoformat().startswith("2026-01-01T00:00:02")


def test_two_runs_of_one_command_at_one_instant_produce_one_envelope_id(clock: StepClock):
    """Nothing random reaches the envelope. Two processes replaying the same
    session mint the same id, which is what makes the log comparable."""
    first = make_client(clock)
    second = make_client(clock)

    first.post("/api/command", json_body=command())
    second.post("/api/command", json_body=command())

    assert first.recorded[0].id == second.recorded[0].id  # type: ignore[attr-defined]


@pytest.mark.parametrize(
    ("payload", "expected"),
    [
        ({"kind": "set_speed", "data": {"speed": 1}}, "command_id"),
        (command(command_id="42"), "command_id"),
        (command(kind="explode"), "not one of"),
        (command(kind="set_speed", data={}), "needs speed"),
        (command(kind="set_speed", data={"speed": 1, "extra": 2}), "does not carry extra"),
        (command(kind="set_pref", data={"key": "a", "value": "b"}), "handled by the browser"),
        (command(kind="seek", data={"sim_time": 1}), "replay mode"),
        (
            command(kind="shelve_alarm", data={"key": "k", "duration_s": 10, "reason": "  "}),
            "non-empty reason",
        ),
    ],
)
def test_a_command_the_dispatch_table_refuses_answers_422(
    client: Client, payload: dict, expected: str
):
    response = client.post("/api/command", json_body=payload)

    assert response.status_code == 422
    assert any(expected in reason for reason in response.json()["errors"]), response.json()


def test_a_refused_command_is_never_recorded(client: Client):
    """A 422 that still wrote to the log would make the audit trail disagree
    with what the operator was told happened."""
    client.post("/api/command", json_body=command(kind="explode"))

    assert client.recorded == []  # type: ignore[attr-defined]


def test_a_refused_command_does_not_consume_a_sequence_number(client: Client):
    """A counter that advanced on refusal would leave a gap, and the historian
    refuses the next event rather than the one that caused the gap."""
    client.post("/api/command", json_body=command(kind="explode"))

    assert client.post("/api/command", json_body=command()).json()["seq"] == 0


def test_every_reason_travels_at_once(client: Client):
    """One mistake per round trip is one audit-log attempt per mistake, on the
    surface whose whole purpose is being auditable."""
    response = client.post(
        "/api/command", json_body={"command_id": "nope", "kind": "set_speed", "data": {}}
    )

    assert len(response.json()["errors"]) >= 2


def test_a_body_that_is_not_json_is_refused_rather_than_raised(client: Client):
    response = client.post(
        "/api/command", content=b"{", headers={"content-type": "application/json"}
    )

    assert response.status_code == 422


def test_a_replay_deployment_refuses_the_live_commands(clock: StepClock):
    """Section 4.2: a live-only command issued in replay is refused with a
    labeled message, never silently ignored."""
    replay = make_client(clock, mode="replay")

    response = replay.post(
        "/api/command", json_body=command(kind="ack_finding", data={"finding_id": "f-1"})
    )

    assert response.status_code == 422
    assert "replay mode" in json.dumps(response.json())


def test_the_default_sink_keeps_what_it_accepted(clock: StepClock):
    """A dropped command that answered 202 would be an audit hole nothing sees,
    so the default is observable rather than a no-op."""
    app = create_app(make_config(), clock=clock)
    client = Client(app)

    client.post("/api/command", json_body=command())

    assert len(app.state.recorded) == 1
