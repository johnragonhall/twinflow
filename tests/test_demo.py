"""Gate VAL-GATE-DEMO-001, asserted rather than described.

The gate is falsified by "a run over 600 seconds, or one beat that asserts on a
sleep". Both halves are checked here, and each check is written so that a reader
can see what would make it go red.

The budget half is the easy one: the demo measures itself and this reads the
measurement back. The sleep half is the one worth the machinery. A test that
merely searched this repository for the string `sleep` would pass for as long as
nobody typed it and would say nothing about whether a beat could assert on
elapsed time. So the demo ships two scanners and a closed observation kind set,
and the tests below fire each of them on a fixture that must trip it, which is
what doctrine D-12 asks: every test states the observation that would fail it,
and a check nobody has watched refuse anything is a check that may be unable to.
"""

from __future__ import annotations

import importlib.util
import sys
from dataclasses import fields
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
DEMO_FILE = REPO_ROOT / "scripts" / "demo" / "ten_minute_demo.py"


def _demo():
    """Load the demo the way tests/test_compare_runs.py loads its tool.

    The module is registered in `sys.modules` before it is executed. That is not
    tidiness: `dataclasses` resolves a field annotation by looking the defining
    module up there, and a module that has not been registered yet makes every
    `@dataclass` in the file raise while it is still being imported.
    """
    spec = importlib.util.spec_from_file_location("ten_minute_demo", DEMO_FILE)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


demo = _demo()


# ------------------------------------------------------------------ the budget


@pytest.mark.slow
def test_the_demo_runs_green_and_inside_its_budget():
    """The gate itself: eleven beats, every one green, under 600 seconds.

    Marked slow so the 60 second unit tier stays a unit tier. `just demo` is
    where this runs on every pull request, and it runs the same script.
    """
    report = demo.measure(runs=1)
    assert [beat.ordinal for beat in report.beats] == list(range(1, len(demo.BEATS) + 1))
    assert report.wall_s < demo.BUDGET_SECONDS
    assert report.within_budget


@pytest.mark.slow
def test_the_report_publishes_the_measurement_and_not_only_the_pass():
    """Section 7.5 asks for the measured wall time beside the pass.

    A gate that printed PASS alone would hide a run that cleared 600 seconds by
    one, which is the thing that section says has to read as marginal.
    """
    report = demo.measure(runs=1)
    rendered = demo.render(report)
    assert f"{report.wall_s:.3f}" in rendered
    assert "budget 600" in rendered
    payload = report.as_dict()
    assert payload["gate"] == "VAL-GATE-DEMO-001"
    assert payload["budget_s"] == 600.0
    assert payload["wall_s"] == round(report.wall_s, 3)


def test_one_run_publishes_no_deviation_rather_than_a_zero():
    """A single run has no run-to-run deviation, and says so.

    Printing 0.000 would claim a stability nobody measured, which is the
    unattributed number foundations 5.6 refuses in operator-facing output.
    """
    single = demo.DemoReport(durations_s=(3.0,), beats=())
    assert single.stdev_s is None
    assert "no run-to-run deviation" in str(single.as_dict()["stdev_note"])

    several = demo.DemoReport(durations_s=(3.0, 3.5, 4.0), beats=())
    assert several.stdev_s == pytest.approx(0.5)
    assert several.mean_s == pytest.approx(3.5)


def test_the_budget_is_held_against_the_slowest_run_not_the_fastest():
    """Five runs where one is over budget is a demo over budget."""
    marginal = demo.DemoReport(durations_s=(10.0, 10.0, 601.0), beats=())
    assert marginal.wall_s == 601.0
    assert not marginal.within_budget


# --------------------------------------------------- no beat asserts on a sleep


def test_the_shipped_demo_and_this_test_contain_no_wait_at_all():
    """The falsification condition, checked over the two files that could carry it."""
    assert demo.structural_refusals(demo.scanned_files()) == ()


def test_the_sleep_scanner_fires_on_every_shape_a_wait_arrives_in(tmp_path: Path):
    """The scanner has been watched refusing each form it exists to refuse.

    Four shapes, because a check that only caught `time.sleep` would pass over
    the three ways the same wait is spelled by somebody working around it.
    """
    shapes = {
        "dotted": "import time\ntime.sleep(1)\n",
        "async": "import asyncio\n\n\nasync def f():\n    await asyncio.sleep(1)\n",
        "bare": "from time import sleep\nsleep(1)\n",
        "event": "import threading\nthreading.Event().wait(1)\n",
        "select": "import select\nselect.select([], [], [], 1)\n",
    }
    for name, source in shapes.items():
        target = tmp_path / f"{name}.py"
        target.write_text(source, encoding="utf-8")
        assert demo.sleeping_call_sites(target), f"the scanner did not refuse the {name} form"


def test_the_sleep_scanner_leaves_the_sanctioned_forms_alone(tmp_path: Path):
    """It refuses waits, not every identifier with those letters in it.

    A scanner that fired on `asyncio.run` or on a variable called `sleep_note`
    would be turned off within a week, which is the failure mode of a gate that
    is easy to trip by accident.
    """
    target = tmp_path / "clean.py"
    target.write_text(
        "import asyncio\n"
        "sleep_note = 'the demo never waits'\n"
        "parts = ', '.join(['a', 'b'])\n"
        "asyncio.run(main())\n",
        encoding="utf-8",
    )
    assert demo.sleeping_call_sites(target) == ()


def test_the_wall_clock_scanner_refuses_a_beat_that_reads_one(tmp_path: Path):
    """A beat cannot read a wall clock, which is what stops it asserting on one.

    Refusing the read is stronger than refusing the comparison: there is one way
    to read a clock and an unbounded number of ways to compare two numbers.
    """
    target = tmp_path / "beats.py"
    target.write_text(
        "import time\n"
        "\n"
        "\n"
        "def beat_timing(stage):\n"
        "    started = time.perf_counter()\n"
        "    return started\n"
        "\n"
        "\n"
        "def measure():\n"
        "    return time.perf_counter()\n",
        encoding="utf-8",
    )
    refusals = demo.wall_clock_reads_in_beats(target)
    assert len(refusals) == 1
    assert "beat_timing" in refusals[0]
    assert "measure" not in refusals[0]


def test_the_demo_refuses_to_run_at_all_when_a_wait_is_present(monkeypatch, tmp_path: Path):
    """The refusal is a precondition of the run, not a lint somebody may skip.

    A demo that reported a duration and then a review caught the sleep would
    have published a green run under a gate the sleep already falsified.
    """
    planted = tmp_path / "planted.py"
    planted.write_text("import time\ntime.sleep(0)\n", encoding="utf-8")
    monkeypatch.setattr(demo, "scanned_files", lambda: (planted,))
    with pytest.raises(demo.DemoFailure, match="refuses to run"):
        demo.measure(runs=1)


def test_the_observation_kinds_carry_nothing_a_timing_assertion_could_use():
    """The closed set is the third mechanism, and it is closed on purpose."""
    for kind in demo.OBSERVABLE_KINDS:
        assert not any(word in kind for word in ("elapsed", "wall", "duration", "seconds", "timer"))
    with pytest.raises(demo.DemoFailure, match="is not one of"):
        demo.Observation("elapsed_seconds", "how long the beat took", 0.1)


def test_a_beat_cannot_reach_the_elapsed_measurement():
    """The stopwatch lives in `measure` and never reaches the stage a beat gets.

    So even with both scanners deleted and the kind set widened, a beat has no
    value to assert on: `measure` times `run_beats` from the outside.
    """
    names = {item.name for item in fields(demo.Stage)}
    assert not any(
        word in name for name in names for word in ("elapsed", "wall", "started", "duration")
    )


# --------------------------------------------------------- the beats themselves


def test_every_beat_is_declared_once_and_in_order():
    ordinals = [beat.ordinal for beat in demo.BEATS]
    assert ordinals == sorted(ordinals)
    assert len(set(ordinals)) == len(ordinals)
    assert len({beat.name for beat in demo.BEATS}) == len(demo.BEATS)


def test_a_beat_that_observes_nothing_fails_the_run(monkeypatch):
    """A beat reporting no observation is a beat that cannot fail.

    D-12 in the form this harness can enforce: silence is refused rather than
    counted as a pass, so a beat gutted down to `return ()` goes red.
    """
    silent = demo.Beat(1, "silent", "observes nothing", lambda stage: ())
    monkeypatch.setattr(demo, "BEATS", (silent,))
    with pytest.raises(demo.DemoFailure, match="observes nothing|reported nothing"):
        demo.run_beats()


def test_a_failing_beat_names_itself_and_what_it_expected(monkeypatch):
    def broken(_stage):
        demo.require(False, expected="a balanced ledger", observed="a hole")
        return ()

    monkeypatch.setattr(demo, "BEATS", (demo.Beat(3, "the line runs", "", broken),))
    with pytest.raises(demo.DemoFailure) as caught:
        demo.run_beats()
    message = str(caught.value)
    assert "beat 3" in message
    assert "a balanced ledger" in message
    assert "a hole" in message


def test_require_passes_a_truth_and_fails_a_falsehood():
    demo.require(1 == 1, expected="one to equal one", observed=1)
    with pytest.raises(demo.DemoFailure):
        demo.require(1 == 2, expected="one to equal two", observed=1)


# ---------------------------------------------------- determinism of the script


def test_the_demo_reads_its_seed_from_the_profile_rather_than_choosing_one():
    """Nothing here invents a seed, and nothing reads a wall clock for one."""
    stage = demo.Stage()
    demo.beat_config(stage)
    assert int(stage.profile["run"]["seed"]) == 20260813
    spec = demo.line_spec(stage.profile)
    assert spec.epoch == demo.EPOCH
    assert spec.arrivals[0].release_tick == 0


def test_two_passes_of_the_line_produce_one_log_hash():
    """Doctrine D-05 tier one, over the material the demo actually runs.

    Beat 4 asserts this inside the script. Asserting it here as well is what
    lets a failure say whether the demo harness moved or the twin did.
    """
    stage = demo.Stage()
    demo.beat_config(stage)
    demo.beat_namespace(stage)
    first = demo.beat_twin(stage)
    second = demo.beat_determinism(stage)
    hashes = {item.value for item in second if item.kind == "event_log_hash"}
    assert stage.replay_hash in hashes
    assert any(item.what == "events on the tape" and item.value > 0 for item in first)
