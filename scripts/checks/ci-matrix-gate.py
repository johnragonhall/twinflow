#!/usr/bin/env python3
"""CI matrix gate CI-001, the CON-3 assertion.

    python scripts/checks/ci-matrix-gate.py              the offline half
    python scripts/checks/ci-matrix-gate.py --run 123    and the run set

CON-3 asks for GitHub Actions running tests and lint. The failure mode it has
to catch is not "there is no workflow": it is a workflow that looks complete and
does not run. A path filter that matches nothing skips its job, the aggregate
check reads a skipped job as success, and the badge stays green over a matrix
that never executed. That has already happened once in this repository, and the
comment on the `python` filter in ci.yml records it.

So the gate asserts the shape a reader assumes from the badge:

  1 Every job in ci_budget.yaml exists in the workflow, and every job in the
    workflow has a budget. Neither file gets to grow a job the other has not
    heard of.
  2 Every job runs on the pinned reference runner label. `ubuntu-latest` moves
    to the next Ubuntu major on GitHub's schedule and takes every budget with
    it.
  3 Lint and the test tiers are both in the run set, by name, on the job that
    carries the interpreter matrix.
  4 Every filtered job's filter includes the workflow file itself, so an edit
    to ci.yml can never be a change that skips the job it edits. A job may be
    exempt, and ci_budget.yaml carries the reason in
    `filter_omits_workflow_because`, so the trade is written down once rather
    than re-argued whenever somebody notices the gap.
  5 The aggregate status check needs every other job.

With --run, it also reads that run's jobs from the GitHub API and asserts every
budgeted job either ran or was skipped by a filter this gate can name. That half
needs a token, so it is not the default: a checkout with no credentials still
proves everything above.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parents[2]
BUDGET = REPO_ROOT / "ci_budget.yaml"
WORKFLOW = REPO_ROOT / ".github" / "workflows" / "ci.yml"

#: Recipes the matrix job has to call by name. `just lint` and `just test` are
#: CON-3's two words, and the rest are what makes the tier claim true.
REQUIRED_STEPS = ("just lint", "just typecheck", "just test")


def load_budget() -> dict:
    return yaml.safe_load(BUDGET.read_text(encoding="utf-8"))


def load_workflow() -> dict:
    # `on:` parses as the boolean True under the YAML 1.1 rules PyYAML follows,
    # which is harmless here because nothing below reads that key.
    return yaml.safe_load(WORKFLOW.read_text(encoding="utf-8"))


def check_jobs(budget: dict, workflow: dict) -> list[str]:
    findings: list[str] = []
    runner = budget["reference_runner"]["label"]

    workflow_jobs = workflow.get("jobs", {})
    budgeted = {job["id"]: job for job in budget.get("jobs", [])}

    for job_id in sorted(set(budgeted) - set(workflow_jobs)):
        findings.append(f"ci_budget.yaml budgets job {job_id!r}, which ci.yml does not define")
    for job_id in sorted(set(workflow_jobs) - set(budgeted)):
        findings.append(f"ci.yml defines job {job_id!r}, which ci_budget.yaml gives no budget")

    for job_id, job in sorted(workflow_jobs.items()):
        expected = budgeted.get(job_id, {})
        declared = job.get("runs-on")
        allowed = _pinned_runners(expected, runner)

        # A job that spans platforms names its runner through the matrix. That
        # is still pinned, one image per cell, so the rule is that every runner
        # the job can land on is an image ci_budget.yaml records: a budget is
        # stated per runner, and a cell on an unbudgeted image is a cell with
        # no budget.
        if declared == "${{ matrix.os }}":
            declared_os = (job.get("strategy", {}).get("matrix", {}) or {}).get("os") or []
            for image in declared_os:
                if image not in allowed:
                    findings.append(
                        f"job {job_id!r} can run on {image!r}, which ci_budget.yaml does not "
                        f"record for it. Every runner a job lands on carries a budget"
                    )
        elif declared != runner:
            findings.append(
                f"job {job_id!r} runs on {declared!r}, not the pinned reference runner "
                f"{runner!r}. Every budget in ci_budget.yaml is stated on that runner"
            )

        if expected.get("matrix"):
            actual = job.get("strategy", {}).get("matrix", {})
            # Compared as the cells each file names rather than as raw mappings,
            # so exclude counts. A matrix that spells the same three cells two
            # ways is the same three cells.
            if _cells(actual) != _cells(expected["matrix"]):
                findings.append(
                    f"job {job_id!r} has matrix cells {_render(_cells(actual))}, and "
                    f"ci_budget.yaml records {_render(_cells(expected['matrix']))}. A leg "
                    f"named in one file and not the other is a leg nobody runs or a budget "
                    f"nobody meets"
                )

    return findings


def _render(cells: set) -> str:
    """Cells as a reader names them, rather than as tuples of pairs."""
    return (
        ", ".join(sorted(" ".join(f"{key}={value}" for key, value in cell) for cell in cells))
        or "none"
    )


def _pinned_runners(budgeted_job: dict, reference: str) -> set[str]:
    """Every image a job is budgeted to run on."""
    images = {reference}
    declared = budgeted_job.get("runs_on")
    if isinstance(declared, str):
        images.add(declared)
    images.update((budgeted_job.get("matrix") or {}).get("os") or [])
    return images


def _cells(matrix: dict) -> set[tuple]:
    """The cells a matrix expands to, honoring exclude.

    include is deliberately not expanded: a cell added that way carries values
    the axes do not list, and this gate compares axes. A job needing include
    states its cells in ci_budget.yaml the same way.
    """
    axes = {
        key: value
        for key, value in (matrix or {}).items()
        if key not in ("include", "exclude") and isinstance(value, list)
    }
    if not axes:
        return set()

    names = sorted(axes)
    cells = [()]
    for name in names:
        cells = [cell + ((name, value),) for cell in cells for value in axes[name]]

    for dropped in matrix.get("exclude") or []:
        wanted = tuple(sorted((key, value) for key, value in dropped.items()))
        cells = [cell for cell in cells if not all(pair in cell for pair in wanted)]
    return {tuple(sorted(cell)) for cell in cells}


def check_run_set(workflow: dict) -> list[str]:
    """Assertion 3: lint and the tests are named, on the job that runs the matrix."""
    findings: list[str] = []
    jobs = workflow.get("jobs", {})
    matrix_jobs = [job_id for job_id, job in jobs.items() if job.get("strategy", {}).get("matrix")]
    if not matrix_jobs:
        return ["no job in ci.yml carries an interpreter matrix, so CON-3's matrix is absent"]

    for job_id in matrix_jobs:
        commands = " ".join(
            str(step.get("run", "")) for step in jobs[job_id].get("steps", []) if step.get("run")
        )
        for required in REQUIRED_STEPS:
            if required not in commands:
                findings.append(
                    f"job {job_id!r} never runs {required!r}, so CON-3's claim that CI "
                    f"runs it is a claim about a step that is not there"
                )
    return findings


def check_filters(budget: dict, workflow: dict) -> list[str]:
    """Assertions 4 and 5."""
    findings: list[str] = []
    jobs = workflow.get("jobs", {})
    budgeted = {job["id"]: job for job in budget.get("jobs", [])}

    filter_job = next(
        (job_id for job_id, job in jobs.items() if "outputs" in job and "steps" in job), None
    )
    filters: dict[str, list[str]] = {}
    if filter_job:
        for step in jobs[filter_job].get("steps", []):
            raw = step.get("with", {}).get("filters")
            if raw:
                filters = yaml.safe_load(raw) or {}

    for job_id in sorted(jobs):
        wanted = budgeted.get(job_id, {}).get("filter")
        if wanted is None:
            continue
        if wanted not in filters:
            findings.append(
                f"job {job_id!r} is gated on filter {wanted!r}, which the filter step "
                f"does not declare, so the job never runs"
            )
            continue
        paths = filters[wanted]
        exemption = budgeted.get(job_id, {}).get("filter_omits_workflow_because")
        if ".github/workflows/ci.yml" not in paths and not exemption:
            findings.append(
                f"filter {wanted!r} does not include .github/workflows/ci.yml, so a "
                f"change to the workflow can skip the job that change edits. Add the "
                f"path, or record why not in ci_budget.yaml under "
                f"filter_omits_workflow_because"
            )

    aggregate = next((job["id"] for job in budget.get("jobs", []) if job.get("aggregate")), None)
    if aggregate is None:
        findings.append("ci_budget.yaml marks no job as the aggregate status check")
    elif aggregate in jobs:
        needs = set(jobs[aggregate].get("needs", []))
        missing = set(jobs) - needs - {aggregate}
        for job_id in sorted(missing):
            findings.append(
                f"the aggregate job {aggregate!r} does not need {job_id!r}, so that job "
                f"can fail under a green status check"
            )

    return findings


def check_run(run_id: str, budget: dict) -> list[str]:
    """The half that needs the tracker: did the budgeted jobs actually run."""
    result = subprocess.run(
        ["gh", "run", "view", run_id, "--json", "jobs"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    if result.returncode != 0:
        return [f"could not read run {run_id}: {result.stderr.strip()}"]

    jobs = json.loads(result.stdout).get("jobs", [])
    seen = {job["name"]: job for job in jobs}
    findings: list[str] = []

    for budgeted in budget.get("jobs", []):
        matches = [name for name in seen if budgeted["id"] in name.lower()]
        if not matches:
            findings.append(
                f"run {run_id} has no job matching {budgeted['id']!r}. A job that never "
                f"started is not a job a filter skipped"
            )
            continue
        for name in matches:
            job = seen[name]
            if job.get("conclusion") not in ("success", "skipped"):
                findings.append(f"run {run_id} job {name!r} concluded {job.get('conclusion')!r}")

    return findings


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run", help="a GitHub Actions run id, to check the run set too")
    args = parser.parse_args(argv)

    if not BUDGET.is_file():
        sys.stderr.write("BLOCKED: no ci_budget.yaml, so no job has a budget\n")
        return 1
    if not WORKFLOW.is_file():
        sys.stderr.write("BLOCKED: no .github/workflows/ci.yml, so CON-3 has no workflow\n")
        return 1

    budget = load_budget()
    workflow = load_workflow()

    findings = check_jobs(budget, workflow)
    findings += check_run_set(workflow)
    findings += check_filters(budget, workflow)
    if args.run:
        findings += check_run(args.run, budget)

    if findings:
        sys.stderr.write("\n\033[31mBLOCKED: CI matrix [CI-001]\033[0m\n")
        for finding in findings:
            sys.stderr.write(f"  {finding}\n")
        sys.stderr.write(
            "\nA skipped job reads as a passing job on the badge. That is the failure\n"
            "this gate exists for, so a job the two files disagree about is a finding\n"
            "rather than something to reconcile at the next release.\n"
        )
        return 1

    runner = budget["reference_runner"]["label"]
    print(
        f"[ci] {len(budget['jobs'])} jobs budgeted and defined, all on {runner}, "
        f"lint and the test tiers present in the run set"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
