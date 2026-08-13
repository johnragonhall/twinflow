"""Done means delivered, and nothing in the tree is unreachable.

These two checks exist because `status: done` is a claim somebody typed and
nothing else in this tool reads it against the tree. Every other check passes
over a work package marked done with none of its deliverables on disk: coverage
proves the requirement is placed, validate proves the graph is sound, and
neither opens a file.

So the cases that matter here are the failing ones. A completeness check that
has never been seen to fire is indistinguishable from one that cannot.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from twinflow_roadmap import completeness
from twinflow_roadmap.roadmap import Roadmap

REPO_ROOT = Path(__file__).resolve().parents[3]


@pytest.fixture(scope="module")
def roadmap() -> Roadmap:
    return Roadmap.load(REPO_ROOT)


def package(roadmap: Roadmap, package_id: str):
    return next(p for p in roadmap.work_packages if p.id == package_id)


def test_this_repository_delivers_what_it_says_it_did(roadmap):
    assert completeness.check_delivered(roadmap) == []


def test_this_repository_has_no_orphaned_script(roadmap):
    assert completeness.check_reached(roadmap) == []


def test_every_done_work_package_is_actually_checked(roadmap):
    # The check would pass vacuously over a roadmap with nothing done, and this
    # repository has plenty done. If that stops being true the assertions above
    # stop meaning anything.
    done = [p for p in roadmap.work_packages if p.status == "done"]
    assert len(done) >= 15
    assert any(p.deliverables for p in done)


def test_a_done_package_whose_deliverable_is_missing_is_a_finding(roadmap):
    subject = package(roadmap, "WP-P0-03")
    original = list(subject.deliverables)
    object.__setattr__(subject, "deliverables", [*original, "packages/does-not-exist.py"])
    try:
        findings = completeness.check_delivered(roadmap)
    finally:
        object.__setattr__(subject, "deliverables", original)

    assert any(f.rule == "DELIV-MISSING" and "WP-P0-03" in f.message for f in findings)


def test_a_done_package_naming_a_recipe_that_does_not_exist_is_a_finding(roadmap):
    subject = package(roadmap, "WP-P0-03")
    original = list(subject.deliverables)
    object.__setattr__(subject, "deliverables", [*original, "just no-such-recipe"])
    try:
        findings = completeness.check_delivered(roadmap)
    finally:
        object.__setattr__(subject, "deliverables", original)

    assert any(f.rule == "DELIV-RECIPE" for f in findings)


def test_a_planned_package_is_not_held_to_its_deliverables(roadmap):
    # Work that has not started names files that do not exist yet. That is the
    # plan describing the future, not a defect.
    planned = [p for p in roadmap.work_packages if p.status == "planned" and p.deliverables]
    assert planned, "no planned work package with deliverables, so this proved nothing"
    reported = {f.message for f in completeness.check_delivered(roadmap)}
    for work_package in planned:
        assert not any(work_package.id in message for message in reported)


def test_the_recipes_are_read_from_the_justfile(roadmap):
    recipes = completeness.justfile_recipes(REPO_ROOT)
    for expected in ("check", "lint", "test", "determinism", "roadmap", "gate"):
        assert expected in recipes
    # A recipe body line is indented, so it is never mistaken for a header.
    assert "uv" not in recipes


def test_an_orphaned_script_is_a_finding(roadmap, tmp_path):
    root = tmp_path
    (root / "scripts" / "checks").mkdir(parents=True)
    (root / "justfile").write_text("check:\n    echo hi\n", encoding="utf-8")
    (root / "scripts" / "checks" / "nobody-calls-this.py").write_text("x = 1\n", encoding="utf-8")

    original = roadmap.root
    object.__setattr__(roadmap, "root", root)
    try:
        findings = completeness.check_reached(roadmap)
    finally:
        object.__setattr__(roadmap, "root", original)

    assert any(f.rule == "ORPHAN-SCRIPT" for f in findings)


def test_a_script_the_justfile_calls_is_reached(roadmap, tmp_path):
    root = tmp_path
    (root / "scripts" / "checks").mkdir(parents=True)
    (root / "justfile").write_text(
        "lint:\n    uv run python scripts/checks/called.py\n", encoding="utf-8"
    )
    (root / "scripts" / "checks" / "called.py").write_text("x = 1\n", encoding="utf-8")

    original = roadmap.root
    object.__setattr__(roadmap, "root", root)
    try:
        findings = completeness.check_reached(roadmap)
    finally:
        object.__setattr__(roadmap, "root", original)

    assert findings == []


def test_a_script_the_plan_still_owes_is_allowed_to_be_unreached(roadmap):
    # The "unless the plan needs it" exemption. It is data rather than a list
    # kept in the checker, so it expires when the work package reaches done and
    # check_delivered takes over.
    planned = completeness.planned_paths(roadmap)
    assert planned
    assert all(not path.startswith("just ") for path in planned)


def test_validate_runs_both_halves(roadmap):
    # The checks are only worth writing if something runs them, and `roadmap
    # validate` is what the roadmap gate and the release ritual call.
    findings = roadmap.validate()
    assert findings == []
    assert completeness.check(roadmap) == []
