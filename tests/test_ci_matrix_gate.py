"""The CI matrix gate (CI-001).

This gate exists because of a defect this repository already had: the `python`
path filter matched `src/**`, which no longer existed, so a pull request
touching only package code skipped the whole matrix, and the aggregate check
read the skip as success. The badge stayed green over tests that never ran.

So the cases below are all shapes of "the workflow looks complete and does not
run", rather than "there is no workflow".
"""

from __future__ import annotations

import copy
import importlib.util
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parents[1]
GATE = REPO_ROOT / "scripts" / "checks" / "ci-matrix-gate.py"


def _gate():
    spec = importlib.util.spec_from_file_location("ci_matrix_gate", GATE)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


gate = _gate()


def fixtures():
    return gate.load_budget(), gate.load_workflow()


def test_the_real_workflow_and_budget_agree():
    budget, workflow = fixtures()
    assert gate.check_jobs(budget, workflow) == []
    assert gate.check_run_set(workflow) == []
    assert gate.check_filters(budget, workflow) == []


def test_a_job_with_no_budget_is_a_finding():
    budget, workflow = fixtures()
    workflow = copy.deepcopy(workflow)
    workflow["jobs"]["surprise"] = {"runs-on": budget["reference_runner"]["label"]}
    findings = gate.check_jobs(budget, workflow)
    assert any("surprise" in f for f in findings)


def test_a_budget_for_a_job_that_does_not_exist_is_a_finding():
    budget, workflow = fixtures()
    budget = copy.deepcopy(budget)
    budget["jobs"].append({"id": "ghost", "budget_s": 1})
    findings = gate.check_jobs(budget, workflow)
    assert any("ghost" in f for f in findings)


def test_an_unpinned_runner_is_a_finding():
    budget, workflow = fixtures()
    workflow = copy.deepcopy(workflow)
    workflow["jobs"]["python"]["runs-on"] = "ubuntu-latest"
    findings = gate.check_jobs(budget, workflow)
    assert any("ubuntu-latest" in f for f in findings)


def test_a_matrix_leg_the_budget_does_not_know_about_is_a_finding():
    budget, workflow = fixtures()
    workflow = copy.deepcopy(workflow)
    workflow["jobs"]["python"]["strategy"]["matrix"]["python-version"] = ["3.13"]
    findings = gate.check_jobs(budget, workflow)
    assert any("matrix" in f for f in findings)


def test_dropping_lint_from_the_matrix_job_is_a_finding():
    budget, workflow = fixtures()
    workflow = copy.deepcopy(workflow)
    workflow["jobs"]["python"]["steps"] = [
        step for step in workflow["jobs"]["python"]["steps"] if step.get("run") != "just lint"
    ]
    findings = gate.check_run_set(workflow)
    assert any("just lint" in f for f in findings)


def test_a_filter_no_job_declares_is_a_finding():
    budget, workflow = fixtures()
    budget = copy.deepcopy(budget)
    for job in budget["jobs"]:
        if job["id"] == "roadmap":
            job["filter"] = "nonexistent"
    findings = gate.check_filters(budget, workflow)
    assert any("nonexistent" in f for f in findings)


def test_a_filter_that_cannot_see_the_workflow_is_a_finding():
    # The exact defect: a filter that does not watch ci.yml lets an edit to the
    # workflow skip the job that edit changed.
    budget, workflow = fixtures()
    workflow = copy.deepcopy(workflow)
    step = workflow["jobs"]["changes"]["steps"][1]
    filters = yaml.safe_load(step["with"]["filters"])
    filters["python"] = [path for path in filters["python"] if not path.endswith("ci.yml")]
    step["with"]["filters"] = yaml.safe_dump(filters)
    findings = gate.check_filters(budget, workflow)
    assert any("ci.yml" in f for f in findings)


def test_a_recorded_exemption_silences_that_finding_and_nothing_else():
    # The agent job is exempt and says why in ci_budget.yaml. Removing the
    # reason has to bring the finding back, or the exemption is unconditional.
    budget, workflow = fixtures()
    stripped = copy.deepcopy(budget)
    for job in stripped["jobs"]:
        job.pop("filter_omits_workflow_because", None)
    assert gate.check_filters(budget, workflow) == []
    assert gate.check_filters(stripped, workflow) != []


def test_an_aggregate_that_misses_a_job_is_a_finding():
    budget, workflow = fixtures()
    workflow = copy.deepcopy(workflow)
    workflow["jobs"]["ci"]["needs"] = ["changes"]
    findings = gate.check_filters(budget, workflow)
    assert any("aggregate" in f for f in findings)


def test_this_repository_passes_its_own_gate():
    assert gate.main([]) == 0
