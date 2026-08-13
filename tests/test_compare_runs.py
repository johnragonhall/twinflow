"""The cross-platform comparison behind DET-002.

The distinction these pin is the one the whole second tier rests on: a business
field has to match exactly and a continuous field is allowed to move in its last
bits. Get that backwards in either direction and the gate is useless. Compare
every field exactly and it fires on arithmetic nothing in the codebase caused;
compare every field with a tolerance and a run that shipped to the wrong station
passes.
"""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
TOOL = REPO_ROOT / "tools" / "compare_runs.py"


def _tool():
    spec = importlib.util.spec_from_file_location("compare_runs", TOOL)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


tool = _tool()


def event(**overrides):
    base = {
        "twinflowsimts": "100",
        "twinflowproducerid": "sim",
        "twinflowseq": "3",
        "type": "twinflow.sim.item.departed.v1",
        "id": "scn-f1-0-sim-3",
        "data": {"station_id": "receiving", "service_ticks": 45123, "service_s": 45.123},
    }
    base.update(overrides)
    return base


def test_two_identical_logs_agree():
    findings, worst = tool.compare([event()], [event()], None)
    assert findings == []
    assert worst == 0.0


def test_a_float_in_the_last_bits_is_not_a_finding():
    # No tolerance asserted, which is what gates.yaml records today: the
    # divergence is published and nothing is bounded.
    right = event()
    right["data"] = {**right["data"], "service_s": 45.123000000000005}
    findings, worst = tool.compare([event()], [right], None)
    assert findings == []
    assert 0 < worst < 1e-12


def test_a_float_past_an_asserted_tolerance_is_a_finding():
    right = event()
    right["data"] = {**right["data"], "service_s": 45.2}
    findings, _ = tool.compare([event()], [right], 1e-9)
    assert any("continuous field" in f for f in findings)


def test_an_integer_that_differs_is_always_a_finding():
    # service_ticks is the business fact. No tolerance applies to it, and
    # passing a generous one has to change nothing.
    right = event()
    right["data"] = {**right["data"], "service_ticks": 45124}
    findings, _ = tool.compare([event()], [right], 1.0)
    assert any("business field" in f and "service_ticks" in f for f in findings)


def test_a_bool_is_a_business_field_even_though_python_calls_it_an_int():
    left, right = event(), event()
    left["data"] = {**left["data"], "reworked": False}
    right["data"] = {**right["data"], "reworked": True}
    findings, _ = tool.compare([left], [right], 1.0)
    assert any("reworked" in f for f in findings)


def test_an_ordering_field_that_differs_is_a_finding():
    findings, _ = tool.compare([event()], [event(twinflowsimts="101")], 1.0)
    assert any("ordering field" in f for f in findings)


def test_a_different_event_count_is_a_finding():
    findings, _ = tool.compare([event(), event()], [event()], None)
    assert any("event count" in f for f in findings)


def test_a_field_present_in_one_log_only_is_a_finding():
    right = event()
    right["data"] = {**right["data"], "extra": 1}
    findings, _ = tool.compare([event()], [right], None)
    assert any("present in one log" in f for f in findings)


def test_the_worst_divergence_is_the_maximum_and_not_the_last_one():
    # The number is published on every run, so it has to be the maximum rather
    # than whichever field happened to be compared last.
    left = [event(), event()]
    right = [event(), event()]
    right[0]["data"] = {**right[0]["data"], "service_s": 45.2}
    right[1]["data"] = {**right[1]["data"], "service_s": 45.1231}
    _, worst = tool.compare(left, right, None)
    assert worst == tool.relative_divergence(45.123, 45.2)


def test_relative_divergence_stays_defined_near_zero():
    assert tool.relative_divergence(0.0, 0.0) == 0.0
    assert tool.relative_divergence(0.0, 1e-18) == 1e-18


def test_the_shipped_scenario_compares_clean_against_itself(tmp_path):
    import subprocess

    log = tmp_path / "run.jsonl"
    result = subprocess.run(
        ["uv", "run", "python", "-m", "twinflow.kernel", "simulate", "--seed", "0"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    assert result.returncode == 0, result.stderr
    log.write_text(result.stdout, encoding="utf-8")

    events = [json.loads(line) for line in result.stdout.splitlines() if line.strip()]
    findings, worst = tool.compare(events, events, 0.0)
    assert findings == []
    assert worst == 0.0
