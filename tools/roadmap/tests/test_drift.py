"""Drift: a tracker that disagrees, and a tracker that does not exist yet.

Those are different facts and the gate has to tell them apart. Reading the
second as the first makes every work package a finding on a repository whose
projection has not been created, which blocks the release whose own sync step
creates it. That reading failed a release dry run before this test existed.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest
from fixtures import ROADMAP, write_fixture

from twinflow_roadmap import drift
from twinflow_roadmap.roadmap import Roadmap


@pytest.fixture
def plan(tmp_path: Path) -> Roadmap:
    subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=True)  # noqa: S603, S607
    write_fixture(tmp_path)
    return Roadmap.load(tmp_path)


def tracker(monkeypatch, labels, issues):
    """Stand in for `gh`, which needs a token and a network."""

    def fake(repo, *args):
        if "label" in args:
            return [{"name": name} for name in labels]
        return issues

    monkeypatch.setattr(drift, "_gh", fake)
    monkeypatch.setattr(drift.shutil, "which", lambda name: "/usr/bin/gh")


def test_an_unprojected_tracker_is_a_skip_and_not_a_finding(plan, monkeypatch):
    tracker(monkeypatch, labels=[], issues=[])
    report = drift.check_drift(plan)
    assert report.findings == []
    assert any("no projection of this plan yet" in note for note in report.skipped)


def test_a_projected_tracker_missing_one_issue_is_drift(tmp_path, monkeypatch):
    """One projected work package means the projection exists.

    WP-P1-01 is finished and unprojected while WP-P0-01 has an issue, so the
    tracker holds a projection and is missing a piece of it.
    """
    subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=True)  # noqa: S603, S607
    write_fixture(
        tmp_path,
        roadmap=ROADMAP.replace(
            """    brick: null
    release: v0.2.0
    status: planned""",
            """    brick: null
    release: v0.2.0
    status: done""",
        ),
    )
    plan = Roadmap.load(tmp_path)

    tracker(
        monkeypatch,
        labels=[],
        issues=[{"number": 1, "title": "[P0] WP-P0-01 record an append-only event log"}],
    )
    report = drift.check_drift(plan)
    assert "DRIFT-ISSUE" in {finding.rule for finding in report.findings}
    assert any("WP-P1-01" in finding.message for finding in report.findings)


def test_a_fully_projected_tracker_is_clean(plan, monkeypatch):
    titles = [
        {"number": index, "title": f"[{package.phase}] {package.id} {package.title}"}
        for index, package in enumerate(plan.work_packages, start=1)
    ]
    tracker(monkeypatch, labels=[], issues=titles)
    assert drift.check_drift(plan).findings == []


def test_the_banned_label_is_a_finding_whatever_the_projection(plan, monkeypatch):
    """The label rule does not wait for a projection: the label is the policy."""
    tracker(monkeypatch, labels=["bug", "wontfix"], issues=[])
    report = drift.check_drift(plan)
    assert "DRIFT-LABEL" in {finding.rule for finding in report.findings}


def test_offline_reports_what_it_did_not_read(plan):
    report = drift.check_drift(plan, offline=True)
    assert report.findings == []
    assert report.skipped
