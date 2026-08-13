"""The tracker projection and the generated documents (CON-10).

Two things are worth pinning here and neither is "the strings come out right".

The first is that the plan is a value. Every operation is computed before any is
performed, so a dry run can be trusted to describe the apply. These tests read
the plan directly and never let a tracker call happen, which is also why they
run with no credentials.

The second is the permission split. Milestone lifecycle is what the release
ritual performs unattended and issue mutation waits for a human, and a test is
the only thing that keeps the release workflow from quietly gaining the ability
to rewrite the backlog.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from twinflow_roadmap import render, sync
from twinflow_roadmap.roadmap import Roadmap

REPO_ROOT = Path(__file__).resolve().parents[3]


@pytest.fixture(scope="module")
def roadmap() -> Roadmap:
    return Roadmap.load(REPO_ROOT)


@pytest.fixture(scope="module")
def config(roadmap: Roadmap) -> dict:
    return sync.load_sync_config(roadmap.root)


def phase(roadmap: Roadmap, phase_id: str):
    return sync.phase_by_id(roadmap, phase_id)


def package(roadmap: Roadmap, package_id: str):
    return next(p for p in roadmap.work_packages if p.id == package_id)


def test_the_milestone_title_follows_the_configured_template(roadmap, config):
    assert sync.milestone_title(config, phase(roadmap, "P0")) == "P0 Contracts (v0.1.0)"


def test_the_issue_title_names_the_phase_and_the_work_package(roadmap, config):
    title = sync.issue_title(config, package(roadmap, "WP-P0-03"))
    assert title.startswith("[P0] WP-P0-03 ")


def test_every_label_comes_from_the_data(roadmap):
    labels = sync.labels_for(roadmap, package(roadmap, "WP-P0-03"))
    assert "phase:P0" in labels
    assert "wave:3" in labels
    assert "req:C1" in labels
    assert "tier:craft" in labels
    assert "brick:twinflow-rng" in labels
    assert "gate:VAL-GATE-DET-001" in labels


def test_a_work_package_with_no_brick_gets_no_brick_label(roadmap):
    labels = sync.labels_for(roadmap, package(roadmap, "WP-P0-01"))
    assert not any(label.startswith("brick:") for label in labels)


def test_labels_are_sorted_so_the_dry_run_does_not_reshuffle(roadmap):
    for work_package in roadmap.work_packages[:20]:
        labels = sync.labels_for(roadmap, work_package)
        assert labels == sorted(labels)


def test_every_generated_label_carries_a_taxonomy_prefix(roadmap):
    # The comparison against the tracker only looks at labels with these
    # prefixes, so a generated label outside them would be added and never
    # noticed as drift again.
    allowed = (*sync.LABEL_PREFIXES, "moved")
    for work_package in roadmap.work_packages:
        for label in sync.labels_for(roadmap, work_package):
            assert label.startswith(allowed), label


def test_the_milestone_body_carries_the_exit_gates(roadmap):
    body = sync.milestone_body(roadmap, phase(roadmap, "P0"))
    for gate_id in roadmap.exit_gates("P0"):
        assert gate_id in body
    assert "just gate phase-exit P0" in body
    assert "Do not edit by hand" in body


def test_the_issue_body_carries_every_deliverable(roadmap):
    work_package = package(roadmap, "WP-P0-03")
    body = sync.issue_body(roadmap, work_package)
    for deliverable in work_package.deliverables:
        assert deliverable in body
    assert "Do not edit by hand" in body


def test_a_partial_coverage_entry_says_so(roadmap):
    # A reader of the issue has to be able to tell "this finishes C1" from
    # "this is one of several work packages that together finish C1".
    assert "(partial)" in sync.issue_body(roadmap, package(roadmap, "WP-P0-03"))


def test_an_offline_plan_computes_nothing_and_says_why(roadmap):
    plan = sync.build_plan(roadmap, offline=True)
    assert plan.operations == []
    assert plan.skipped


def test_an_unread_tracker_does_not_read_as_a_match(roadmap):
    # The defect this guards: an empty plan printed as "already matches" when
    # nothing was compared is the same failure as a skipped CI job reading as
    # a pass.
    rendered = sync.build_plan(roadmap, offline=True).render()
    assert "already matches" not in rendered
    assert "not read" in rendered


def test_a_plan_with_no_operations_and_no_skips_reads_as_a_match():
    assert "already matches" in sync.SyncPlan().render()


def test_the_apply_context_split(roadmap, monkeypatch):
    """The release workflow may close a milestone and may not touch an issue."""
    plan = sync.SyncPlan(
        operations=[
            sync.Operation(sync.MILESTONE, "close a milestone", ("api", "x")),
            sync.Operation(sync.ISSUE, "rewrite an issue body", ("issue", "edit", "1")),
        ]
    )
    performed: list[tuple[str, ...]] = []

    monkeypatch.setattr(sync.shutil, "which", lambda _name: "gh")

    class Completed:
        returncode = 0
        stderr = ""

    def fake_run(args, **_kwargs):
        performed.append(tuple(args))
        return Completed()

    monkeypatch.setattr(sync.subprocess, "run", fake_run)

    refused = sync.apply_plan(plan, roadmap, context="release-workflow")
    assert len(performed) == 1
    assert "api" in performed[0]
    assert len(refused) == 1
    assert "issue" in refused[0]


def test_a_human_at_a_checkout_may_apply_everything(roadmap, monkeypatch):
    plan = sync.SyncPlan(
        operations=[
            sync.Operation(sync.MILESTONE, "close a milestone", ("api", "x")),
            sync.Operation(sync.ISSUE, "rewrite an issue body", ("issue", "edit", "1")),
        ]
    )
    monkeypatch.setattr(sync.shutil, "which", lambda _name: "gh")

    class Completed:
        returncode = 0
        stderr = ""

    monkeypatch.setattr(sync.subprocess, "run", lambda *_a, **_k: Completed())
    assert sync.apply_plan(plan, roadmap, context=None) == []


def test_a_context_the_config_does_not_name_may_apply_nothing(roadmap, monkeypatch):
    plan = sync.SyncPlan(
        operations=[sync.Operation(sync.MILESTONE, "close a milestone", ("api", "x"))]
    )
    monkeypatch.setattr(sync.shutil, "which", lambda _name: "gh")
    refused = sync.apply_plan(plan, roadmap, context="some-other-workflow")
    assert len(refused) == 1


def test_the_config_this_repository_ships_forbids_applying_by_default(config):
    assert config["dry_run_default"] is True
    assert config["allowed_apply_contexts"] == ["release-workflow"]


def test_the_generated_gate_document_is_current(roadmap):
    # The same assertion step 8 of the release ritual makes.
    assert render.check(roadmap) == []


def test_the_gate_document_names_every_gate(roadmap):
    text = render.render_gates(roadmap)
    for gate_id in roadmap.gates:
        assert gate_id in text


def test_an_implemented_gate_publishes_what_runs_it(roadmap):
    text = render.render_gates(roadmap)
    for gate_id, gate in roadmap.gates.items():
        if gate.status == "implemented":
            assert gate.command in text, gate_id


def test_editing_the_generated_document_is_a_finding(roadmap, tmp_path, monkeypatch):
    stale = tmp_path / "docs" / "gates.md"
    stale.parent.mkdir(parents=True)
    stale.write_text("somebody edited this by hand\n", encoding="utf-8")
    monkeypatch.setattr(render, "GATES_DOC", Path("docs") / "gates.md")
    monkeypatch.setattr(roadmap, "root", tmp_path)
    findings = render.check(roadmap)
    assert findings and findings[0].rule == "RENDER-STALE"


# --- the test index ---------------------------------------------------------


def test_the_index_names_every_test_in_the_tree(roadmap):
    """The inventory is walked, not maintained.

    A hand-written list goes stale the first time somebody adds a file, and
    nobody notices until they trust it. This is what says the walk still finds
    everything.
    """
    listed = render.render_tests(roadmap)
    for relative in render.test_files(roadmap):
        assert f"`{relative.as_posix()}`" in listed, f"{relative} is in the tree and not indexed"


def test_the_index_joins_a_test_to_the_gate_that_names_it(roadmap):
    listed = render.render_tests(roadmap)
    for gate_id, gate in roadmap.gates.items():
        for named in gate.test_paths():
            if (roadmap.root / named).exists():
                assert gate_id in listed, f"{gate_id} names {named} and the index omits the join"


def test_the_index_counts_what_it_lists(roadmap):
    # The two numbers in the opening sentence are computed from the same walk
    # that builds the table, so they cannot disagree with it.
    listed = render.render_tests(roadmap)
    total = len(render.test_files(roadmap))
    assert f"{total} test files." in listed


def test_a_test_no_gate_names_still_appears(roadmap):
    # The whole point. A test below the gate line is listed with `none` rather
    # than left out, so the reader sees the untracked ones.
    listed = render.render_tests(roadmap)
    assert "| none " in listed or "| none" in listed


def test_the_index_is_a_generated_document(roadmap):
    # It has to be regenerated by the same recipe and checked by the same
    # --check that keeps gates.md honest, or it is a hand-written list again.
    assert render.TESTS_DOC in render.DOCUMENTS
