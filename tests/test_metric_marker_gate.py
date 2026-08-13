"""The metric marker gate, and which release owes which number.

Repository policy gates live in scripts/checks and are not part of any
distribution, so their tests live here rather than inside a package.

The arming tag is what these pin. A marker names the tag its number arrives at,
so the first release does not wait for the last measurement, and the comparison
that decides "has this tag arrived" is the one place a string comparison quietly
gets it wrong: v0.10.0 sorts before v0.9.0 as text and after it as a version.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
GATE = REPO_ROOT / "scripts" / "checks" / "metric-marker-gate.sh"


def run(*args: str, cwd: Path | None = None) -> subprocess.CompletedProcess:
    return subprocess.run(  # noqa: S603
        ["sh", str(GATE), *args],  # noqa: S607
        cwd=cwd or REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    """A repository holding one marker, so the gate reads a known corpus."""
    subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=True)  # noqa: S603, S607
    return tmp_path


def write(repo: Path, marker: str) -> None:
    (repo / "README.md").write_text(f"The rate is {marker} today.\n", encoding="utf-8")


def test_a_marker_naming_a_later_tag_does_not_block_this_release(repo):
    write(repo, "<!--METRIC:agent_eval_accuracy@v0.3.0-->TBD<!--/METRIC-->")
    done = run("--release", "0.1.0", cwd=repo)
    assert done.returncode == 0, done.stdout + done.stderr
    assert "DEFERRED" in done.stdout


def test_a_marker_the_release_owes_blocks_it(repo):
    write(repo, "<!--METRIC:agent_eval_accuracy@v0.3.0-->TBD<!--/METRIC-->")
    done = run("--release", "0.3.0", cwd=repo)
    assert done.returncode == 1
    assert "owed from v0.3.0" in done.stdout


def test_a_marker_naming_no_tag_is_owed_by_every_release(repo):
    write(repo, "<!--METRIC:some_rate-->TBD<!--/METRIC-->")
    assert run("--release", "0.1.0", cwd=repo).returncode == 1


def test_a_filled_marker_blocks_nothing(repo):
    write(repo, "<!--METRIC:some_rate@v0.1.0-->0.97<!--/METRIC-->")
    assert run("--release", "0.1.0", cwd=repo).returncode == 0


@pytest.mark.parametrize(
    ("arms", "cutting", "blocks"),
    [
        ("v0.9.0", "0.10.0", True),
        ("v0.10.0", "0.9.0", False),
        ("v1.0.0", "0.27.0", False),
        ("v0.2.0", "0.2.0", True),
        ("v0.2.1", "0.2.0", False),
    ],
)
def test_the_tag_comparison_is_by_field_and_not_by_string(repo, arms, cutting, blocks):
    """v0.10.0 sorts before v0.9.0 as text, and after it as a version."""
    write(repo, f"<!--METRIC:some_rate@{arms}-->TBD<!--/METRIC-->")
    done = run("--release", cutting, cwd=repo)
    assert (done.returncode == 1) is blocks, f"{arms} at {cutting}: {done.stdout}"


def test_report_mode_never_blocks(repo):
    write(repo, "<!--METRIC:some_rate-->TBD<!--/METRIC-->")
    done = run(cwd=repo)
    assert done.returncode == 0
    assert "unfilled" in done.stdout


def test_one_metric_naming_two_arming_tags_is_a_conflict(repo):
    """Two answers to which release owes a number is no answer."""
    (repo / "README.md").write_text(
        "here <!--METRIC:some_rate@v0.2.0-->TBD<!--/METRIC-->\n", encoding="utf-8"
    )
    (repo / "OTHER.md").write_text(
        "there <!--METRIC:some_rate@v0.3.0-->TBD<!--/METRIC-->\n", encoding="utf-8"
    )
    done = run("--release", "0.1.0", cwd=repo)
    assert done.returncode == 1
    assert "more than one arming tag" in done.stderr


def test_a_malformed_marker_fails_in_every_mode(repo):
    (repo / "README.md").write_text("open <!--METRIC:some_rate-->TBD\n", encoding="utf-8")
    assert run(cwd=repo).returncode == 1


def test_the_shipped_tree_can_cut_the_first_tag():
    """v0.1.0 owes no number, which is what makes the phase exit reachable."""
    done = run("--release", "0.1.0")
    assert done.returncode == 0, done.stdout + done.stderr
    assert "0 owed at 0.1.0" in done.stdout
