"""The measured-claims checker, and the states it has to refuse.

The tool carries its own `--selftest` because doctrine D-12 asks a checker to
prove each of its refusals fires. That is run here as one test, and the rest of
this file covers what a selftest cannot: the command line, the exit codes, and
the checker's behavior against this repository as it actually stands.
"""

from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
TOOL = REPO_ROOT / "tools" / "check_measured_claims.py"

GOOD_ARTIFACT = {
    "metric": "widget_rate",
    "value": 12.5,
    "unit": "widget/second",
    "seed": 7,
    "run_id": "run_deadbeef",
    "tool": "tools/measure_row_bytes.py",
}


def _load():
    spec = importlib.util.spec_from_file_location("check_measured_claims", TOOL)
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
def checker():
    return _load()


@pytest.fixture
def tree(tmp_path: Path) -> Path:
    (tmp_path / "docs").mkdir()
    return tmp_path


def write_marker(
    tree: Path, value: str, *, name: str = "widget_rate", arms: str = "@v0.1.0"
) -> None:
    marker = f"<!--METRIC:{name}{arms}-->{value}<!--/METRIC-->"
    (tree / "docs" / "claim.md").write_text(f"The rate is {marker}.\n", encoding="utf-8")


def write_artifact(tree: Path, record: dict, *, name: str = "widget_rate") -> None:
    target = tree / "artifacts" / "measured"
    target.mkdir(parents=True, exist_ok=True)
    (target / f"{name}.json").write_text(json.dumps(record), encoding="utf-8")
    producer = record.get("tool")
    if producer:
        path = tree / producer
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("# stand-in\n", encoding="utf-8")


def run_cli(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run(  # noqa: S603
        [sys.executable, str(TOOL), *args],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )


def rules(checker, tree: Path, release: str | None = None) -> set[str]:
    return {finding.rule for finding in checker.check(tree, release)}


def test_the_selftest_passes():
    """Each refusal fires on the state it names, and a clean tree passes."""
    done = run_cli("--selftest")
    assert done.returncode == 0, done.stdout + done.stderr
    assert "every refusal fires" in done.stdout


def test_a_hand_typed_number_is_refused(checker, tree):
    """The central case. A number in a doc with nothing behind it."""
    write_marker(tree, "12.5")
    assert rules(checker, tree) == {"no-artifact"}


def test_a_number_that_drifted_from_its_artifact_is_refused(checker, tree):
    """Editing the doc without re-measuring is the same defect one step later."""
    write_marker(tree, "99.0")
    write_artifact(tree, GOOD_ARTIFACT)
    assert rules(checker, tree) == {"value-drift"}


def test_an_artifact_missing_its_run_id_is_refused(checker, tree):
    """A value with no run behind it is a guess wearing a unit."""
    write_marker(tree, "12.5")
    write_artifact(tree, dict(GOOD_ARTIFACT, run_id=None))
    assert rules(checker, tree) == {"unattributed"}


def test_an_artifact_missing_its_seed_is_refused(checker, tree):
    write_marker(tree, "12.5")
    write_artifact(tree, dict(GOOD_ARTIFACT, seed=None))
    assert rules(checker, tree) == {"unattributed"}


def test_an_artifact_naming_a_tool_that_is_gone_is_refused(checker, tree):
    """The record leads back to something a reader can run, or it leads nowhere."""
    write_marker(tree, "12.5")
    write_artifact(tree, dict(GOOD_ARTIFACT, tool="tools/deleted.py"))
    (tree / "tools" / "deleted.py").unlink()
    assert rules(checker, tree) == {"no-producer"}


def test_a_marker_that_resolves_passes(checker, tree):
    """The pass case. Without it this checker proves only that it can refuse."""
    write_marker(tree, "12.5")
    write_artifact(tree, GOOD_ARTIFACT)
    assert rules(checker, tree, "0.1.0") == set()


def test_trailing_whitespace_in_a_marker_is_not_drift(checker, tree):
    """A formatting change is not a change of measurement."""
    write_marker(tree, " 12.5 ")
    write_artifact(tree, GOOD_ARTIFACT)
    assert rules(checker, tree) == set()


def test_a_marker_written_as_a_decimal_equal_to_its_artifact_passes(checker, tree):
    """12.50 and 12.5 are one number, and Decimal is why this is not a string compare."""
    write_marker(tree, "12.50")
    write_artifact(tree, GOOD_ARTIFACT)
    assert rules(checker, tree) == set()


def test_an_unfilled_marker_is_silent_without_a_release(checker, tree):
    """Coverage belongs to the marker gate. A branch lint does not fail over it."""
    write_marker(tree, "TBD")
    assert rules(checker, tree) == set()


def test_an_unfilled_marker_blocks_the_release_that_owes_it(checker, tree):
    write_marker(tree, "TBD")
    assert rules(checker, tree, "0.1.0") == {"unfilled"}


def test_an_unfilled_marker_does_not_block_an_earlier_release(checker, tree):
    write_marker(tree, "TBD")
    assert rules(checker, tree, "0.0.9") == set()


def test_the_arming_tag_is_compared_as_a_version_not_as_text(checker, tree):
    """v0.10.0 sorts before v0.9.0 as text and after it as a version."""
    write_marker(tree, "TBD", arms="@v0.10.0")
    assert rules(checker, tree, "0.9.0") == set()
    assert rules(checker, tree, "0.10.0") == {"unfilled"}


def test_a_marker_naming_no_tag_is_owed_by_every_release(checker, tree):
    write_marker(tree, "TBD", arms="")
    assert rules(checker, tree, "0.0.1") == {"unfilled"}


def test_a_stored_bytes_keyword_without_its_run_is_refused(checker, tree):
    """Foundations 5.6: the run id is half of what that keyword means."""
    schema = tree / "schemas" / "telemetry"
    schema.mkdir(parents=True)
    (schema / "v1.json").write_text(json.dumps({"x-twinflow-stored-bytes": 214}), encoding="utf-8")
    assert rules(checker, tree) == {"stored-bytes"}


def test_a_stored_bytes_keyword_with_its_run_passes(checker, tree):
    schema = tree / "schemas" / "telemetry"
    schema.mkdir(parents=True)
    (schema / "v1.json").write_text(
        json.dumps({"x-twinflow-stored-bytes": {"bytes": 214, "run_id": "run_x"}}),
        encoding="utf-8",
    )
    assert rules(checker, tree) == set()


def test_the_checker_passes_over_this_repository_as_a_lint():
    """No marker in this tree carries a filled value, so nothing is unattributed."""
    done = run_cli()
    assert done.returncode == 0, done.stdout + done.stderr


def test_a_malformed_release_argument_is_refused():
    assert run_cli("--release", "0.2").returncode == 2
