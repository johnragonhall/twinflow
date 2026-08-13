"""Deferred numbers, and the plan that owes them.

An arming tag on a marker lets a release ship without a number. That is an
escape, and an escape nobody tracks is a way to defer a number forever, one
edit at a time, with every release green on the way.

These cases pin the three ways the plan refuses that: a deferred number names a
tag this plan cuts, a work package in that tag's phase claims it, and a work
package cannot be finished while the number it promised is still empty.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest
from fixtures import ROADMAP, write_fixture

from twinflow_roadmap import markers
from twinflow_roadmap.roadmap import Roadmap

REPO_ROOT = Path(__file__).resolve().parents[3]


@pytest.fixture
def plan(tmp_path: Path) -> Path:
    """A fixture repository, since the scan reads what git tracks."""
    subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=True)  # noqa: S603, S607
    write_fixture(tmp_path)
    return tmp_path


def build(plan: Path, marker: str, deliverables: str = '["docs/x.md"]') -> Roadmap:
    (plan / "README.md").write_text(f"The rate is {marker} today.\n", encoding="utf-8")
    roadmap = ROADMAP.replace(
        '    deliverables: ["packages/twinflow-storage/src/twinflow/storage/replay.py"]',
        f"    deliverables: {deliverables}",
    )
    (plan / "roadmap.yaml").write_text(roadmap, encoding="utf-8")
    subprocess.run(["git", "add", "-A"], cwd=plan, check=True)  # noqa: S603, S607
    return Roadmap.load(plan)


def rules(findings) -> list[str]:
    return [finding.rule for finding in findings]


def test_a_deferred_number_with_no_work_package_is_scheduled_nowhere(plan):
    """The plain case: a promise in a comment that the plan never heard of."""
    roadmap = build(plan, "<!--METRIC:some_rate@v0.2.0-->TBD<!--/METRIC-->")
    assert "MARKER-ORPHAN" in rules(markers.check(roadmap))


def test_a_deferred_number_claimed_by_that_phase_is_accepted(plan):
    """WP-P1-01 sits in P1, which releases v0.2.0."""
    roadmap = build(plan, "<!--METRIC:some_rate@v0.2.0-->TBD<!--/METRIC-->", '["metric:some_rate"]')
    assert markers.check(roadmap) == []


def test_pushing_the_tag_out_leaves_the_claim_behind(plan):
    """The gap this rule closes.

    Editing v0.2.0 to v0.3.0 moves the number one release further away. The
    work package that measures it stays in P1, so the claim and the marker no
    longer name the same phase and the plan says so.
    """
    roadmap = build(plan, "<!--METRIC:some_rate@v0.3.0-->TBD<!--/METRIC-->", '["metric:some_rate"]')
    findings = markers.check(roadmap)
    assert "MARKER-ORPHAN" in rules(findings)
    assert "P1" in findings[0].message


def test_a_tag_no_phase_releases_is_refused(plan):
    roadmap = build(plan, "<!--METRIC:some_rate@v9.9.9-->TBD<!--/METRIC-->")
    assert "MARKER-TAG" in rules(markers.check(roadmap))


def test_a_filled_number_owes_nothing(plan):
    roadmap = build(plan, "<!--METRIC:some_rate@v0.2.0-->0.981<!--/METRIC-->")
    assert markers.check(roadmap) == []


def test_a_marker_with_no_arming_tag_is_owed_by_every_release(plan):
    """Nothing to schedule: the release gate refuses it at any tag."""
    roadmap = build(plan, "<!--METRIC:some_rate-->TBD<!--/METRIC-->")
    assert "MARKER-ORPHAN" not in rules(markers.check(roadmap))


def test_a_finished_work_package_cannot_leave_its_number_empty(plan):
    """The failure the release gate only catches if somebody cuts that tag."""
    (plan / "README.md").write_text(
        "rate <!--METRIC:some_rate@v0.2.0-->TBD<!--/METRIC-->\n", encoding="utf-8"
    )
    roadmap_text = ROADMAP.replace(
        '    deliverables: ["packages/twinflow-storage/src/twinflow/storage/replay.py"]',
        '    deliverables: ["metric:some_rate"]',
    ).replace(
        """    brick: null
    release: v0.2.0
    status: planned""",
        """    brick: null
    release: v0.2.0
    status: done""",
    )
    (plan / "roadmap.yaml").write_text(roadmap_text, encoding="utf-8")
    subprocess.run(["git", "add", "-A"], cwd=plan, check=True)  # noqa: S603, S607
    findings = markers.check(Roadmap.load(plan))
    assert "MARKER-SKIPPED" in rules(findings)


def test_a_claim_no_document_carries_fills_nothing(plan):
    roadmap = build(plan, "no marker here", '["metric:absent_rate"]')
    assert "MARKER-UNUSED" in rules(markers.check(roadmap))


def test_the_shipped_plan_owes_every_deferred_number_to_a_work_package():
    """Each of the numbers this repository defers is scheduled somewhere."""
    roadmap = Roadmap.load(REPO_ROOT)
    findings = markers.check(roadmap)
    assert findings == [], "\n".join(str(finding) for finding in findings)

    deferred = {m.name for m in markers.scan(REPO_ROOT) if m.unfilled and m.arms_at}
    claimed = set(markers.claimed_metrics(roadmap))
    assert deferred, "the repository defers at least one number"
    assert deferred <= claimed, f"unclaimed: {sorted(deferred - claimed)}"
