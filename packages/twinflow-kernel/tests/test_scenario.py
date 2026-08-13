"""SCN-F1 and the determinism claim it carries (DET-001).

Reproducibility tests have a failure mode of their own: they pass because
nothing in them could have varied. So each case below names the specific way a
run stops being reproducible and shows that the scenario would have caught it,
rather than only asserting that two runs agree.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from twinflow.kernel import load_scenario, run_scenario
from twinflow.kernel._impl.scenario import SERVICE_STREAM, Scenario, Station
from twinflow.schemas import check_log_invariants, in_total_order, log_hash

REPO_ROOT = Path(__file__).resolve().parents[3]
SCENARIO_FILE = REPO_ROOT / "scenarios" / "determinism-smoke.yaml"


@pytest.fixture
def scenario() -> Scenario:
    return load_scenario(SCENARIO_FILE)


def test_the_shipped_scenario_loads(scenario):
    assert scenario.id == "SCN-F1"
    assert len(scenario.stations) == 3
    # Distinct arrival counts, so a bug that indexed by position rather than by
    # name shows up as a divergence rather than canceling out.
    assert len({station.arrivals for station in scenario.stations}) == 3


def test_two_runs_at_one_seed_are_byte_identical(scenario):
    # DET-001 itself.
    left = run_scenario(scenario, seed=0)
    right = run_scenario(scenario, seed=0)
    assert log_hash(left) == log_hash(right)


def test_two_seeds_produce_different_logs(scenario):
    # The other half of the same claim. A runner that ignored its seed would
    # pass the test above forever.
    assert log_hash(run_scenario(scenario, seed=0)) != log_hash(run_scenario(scenario, seed=1))


def test_the_log_satisfies_the_envelope_invariants(scenario):
    assert check_log_invariants(run_scenario(scenario, seed=0)) == []


def test_the_log_is_emitted_in_total_order(scenario):
    events = run_scenario(scenario, seed=0)
    assert events == in_total_order(events)


def test_the_event_count_is_a_function_of_the_scenario(scenario):
    # One started, one finished, and an arrival and a departure per item.
    arrivals = sum(station.arrivals for station in scenario.stations)
    assert len(run_scenario(scenario, seed=0)) == 2 + 2 * arrivals


def test_no_event_reads_the_wall_clock(scenario):
    # Every timestamp is the scenario epoch plus the sim offset, so a run in
    # 2030 produces the times a run today produced.
    events = run_scenario(scenario, seed=0)
    assert events[0].time == scenario.epoch
    for event in events:
        assert event.time >= scenario.epoch


def test_the_clock_never_runs_backwards(scenario):
    ticks = [int(event.twinflowsimts) for event in run_scenario(scenario, seed=0)]
    assert ticks == sorted(ticks)


def test_a_station_added_before_another_does_not_move_its_numbers(scenario):
    """The name-addressed derivation, stated as the thing it prevents.

    Positional derivation would shift every later station's stream each time
    one is inserted, silently invalidating every earlier golden file. That is
    the retrofit the whole seam exists to prevent, so it gets its own case.
    """
    original = run_scenario(scenario, seed=0)
    picking_before = [
        event.data["service_s"]
        for event in original
        if event.data.get("station_id") == "picking" and "service_s" in event.data
    ]

    inserted = Scenario(
        id=scenario.id,
        title=scenario.title,
        description=scenario.description,
        tick_hz=scenario.tick_hz,
        epoch=scenario.epoch,
        seed=scenario.seed,
        stations=[
            Station(id="inbound", arrivals=4, service_mean_s=10.0, service_spread_s=2.0),
            *scenario.stations,
        ],
    )
    after = run_scenario(inserted, seed=0)
    picking_after = [
        event.data["service_s"]
        for event in after
        if event.data.get("station_id") == "picking" and "service_s" in event.data
    ]

    assert picking_before == picking_after
    # And the run as a whole did change, or the assertion above proved nothing.
    assert log_hash(original) != log_hash(after)


def test_the_stream_name_is_the_one_the_registry_declared(scenario):
    finished = run_scenario(scenario, seed=0)[-1]
    assert finished.data["streams"] == [SERVICE_STREAM]


def test_service_ticks_is_an_integer_and_service_seconds_is_not(scenario):
    """The tier-one and tier-two split, at the field level.

    D-05 tier two compares business events exactly and continuous fields within
    a tolerance. That only works if the departure a reader acts on is the
    integer tick rather than the float second.
    """
    departures = [
        event for event in run_scenario(scenario, seed=0) if "service_ticks" in event.data
    ]
    assert departures
    for event in departures:
        assert isinstance(event.data["service_ticks"], int)
        assert isinstance(event.data["service_s"], float)


def test_every_payload_round_trips_through_json(scenario):
    # The hash is computed over a JSON dump, so a value that does not survive
    # one is a value the hash does not describe.
    for event in run_scenario(scenario, seed=0):
        payload = event.model_dump(mode="json", exclude_none=True)
        assert json.loads(json.dumps(payload, sort_keys=True)) == payload


#: The smallest scenario that loads, as a plain mapping. The cases below reach
#: the model through model_validate rather than through keyword arguments,
#: because two of them pass a key the model refuses and the type checker is
#: right to reject that spelled as a keyword.
MINIMAL: dict = {
    "id": "X",
    "title": "X",
    "epoch": "2026-01-01T00:00:00Z",
    "seed": 0,
    "stations": [{"id": "a", "arrivals": 1, "service_mean_s": 1.0, "service_spread_s": 0.0}],
}


def test_the_minimal_scenario_loads():
    # So the two refusals below are refusing the key rather than the fixture.
    assert Scenario.model_validate(MINIMAL).id == "X"


def test_a_scenario_refuses_an_unknown_key():
    # extra="forbid": a misspelled key that loaded as a default would be a
    # scenario nobody ran.
    with pytest.raises(ValueError):
        Scenario.model_validate({**MINIMAL, "arrivals_typo": 3})


def test_a_scenario_refuses_a_tick_rate_the_clock_does_not_have():
    with pytest.raises(ValueError):
        Scenario.model_validate({**MINIMAL, "tick_hz": 7})
