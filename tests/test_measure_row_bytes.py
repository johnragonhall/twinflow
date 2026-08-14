"""The row-size measurement tool, and the two things it must never do.

It must never produce a number it did not measure, and it must never produce a
different number from one seed. The first is the repository's central rule; the
second is what makes the first worth anything, because an unreproducible
measurement is a claim with a run id stapled to it.

Repository tooling under tools/ belongs to no distribution, so its tests live
here rather than inside a package.
"""

from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
TOOL = REPO_ROOT / "tools" / "measure_row_bytes.py"

#: Small enough to keep this file inside the unit tier's 90 second budget. The
#: row count is an input to the run id by design, so these tests pin behavior at
#: this count and never assert a value measured at another.
READINGS = 200


def _load():
    spec = importlib.util.spec_from_file_location("measure_row_bytes", TOOL)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    # Registered before execution, not after. The module uses dataclasses under
    # `from __future__ import annotations`, and dataclasses resolves a string
    # annotation through sys.modules[cls.__module__], which is None for a module
    # loaded from a path and never registered.
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def tool():
    return _load()


def run_cli(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run(  # noqa: S603
        [sys.executable, str(TOOL), *args],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )


def test_one_seed_gives_one_run_id_and_one_log(tool):
    """Two invocations of one seed are one run, not two observations."""
    first = tool.build_run(seed=7, readings=READINGS)
    second = tool.build_run(seed=7, readings=READINGS)
    assert first.run_id == second.run_id
    assert first.log_hash == second.log_hash
    assert first.rows == second.rows


def test_a_different_seed_gives_a_different_log(tool):
    """The seed reaches the readings. Without this the seed is decoration."""
    first = tool.build_run(seed=7, readings=READINGS)
    second = tool.build_run(seed=8, readings=READINGS)
    assert first.log_hash != second.log_hash


def test_the_run_id_moves_when_the_row_count_moves(tool):
    """Bytes per row is not independent of row count, so the id is not either."""
    assert (
        tool.build_run(seed=7, readings=READINGS).run_id
        != tool.build_run(seed=7, readings=READINGS + 1).run_id
    )


def test_every_reading_reaches_the_historian(tool):
    """The count the artifact would divide by is the count that was recorded."""
    run = tool.build_run(seed=7, readings=READINGS)
    assert run.events == READINGS
    assert len(run.rows) == READINGS


def test_the_rows_are_the_shipped_batch_columns(tool):
    """A measurement over a different column set measures a different table."""
    from twinflow.storage import EVENT_TABLE

    run = tool.build_run(seed=7, readings=READINGS)
    assert set(run.rows[0]) == {column.name for column in EVENT_TABLE.columns}


def test_the_rows_arrive_in_the_canonical_total_order(tool):
    """Invariant E4's order, which is what a replay reads them back in."""
    run = tool.build_run(seed=7, readings=READINGS)
    keys = [
        (row["twinflowsimts"], row["twinflowproducerid"], row["twinflowseq"]) for row in run.rows
    ]
    assert keys == sorted(keys)


def test_the_measurement_refuses_while_its_preconditions_are_absent(tool):
    """The observation that would fail this: the tool returning a number today.

    Neither the subject nor the writer is in this tree, so there is no honest
    value to return. This asserts the refusal rather than a number, and it flips
    to a failure the moment somebody makes `measure` return one without landing
    the two things `missing_preconditions` names.
    """
    missing = tool.missing_preconditions()
    assert missing, "preconditions look satisfied; this test and the tool both need revisiting"

    with pytest.raises(tool.Unmeasurable) as caught:
        tool.measure(seed=7, readings=READINGS)
    assert caught.value.missing == missing


def test_the_refusal_names_the_registry_and_the_writer(tool):
    """A refusal that does not say what is missing is a refusal nobody can clear."""
    missing = " ".join(tool.missing_preconditions())
    assert "schemas/registry.yaml" in missing
    assert "deltalake" in missing


def test_the_cli_exits_three_and_writes_no_artifact(tmp_path):
    """Exit 3 is "cannot measure". It is not exit 0 with a blank where a number goes."""
    out = tmp_path / "should-not-exist.json"
    done = run_cli("--readings", str(READINGS), "--out", str(out))
    assert done.returncode == 3, done.stdout + done.stderr
    assert not out.exists()
    assert "CANNOT MEASURE" in done.stderr


def test_the_refusal_still_reports_what_it_did_measure(tmp_path):
    """The scenario ran; only the writer is missing. The report says which."""
    done = run_cli("--readings", str(READINGS), "--json", "--out", str(tmp_path / "x.json"))
    report = json.loads(done.stdout)
    assert report["measured"] is False
    assert report["value"] is None
    assert report["events"] == READINGS
    assert report["run_id"].startswith("run_")
    assert len(report["missing"]) == 2


def test_the_cli_refuses_a_zero_row_scenario():
    """Dividing bytes by zero readings is not a measurement of anything."""
    assert run_cli("--readings", "0").returncode == 2
