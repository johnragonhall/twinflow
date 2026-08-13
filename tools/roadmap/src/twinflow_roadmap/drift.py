"""Drift: the two policies this repository enforces rather than promises.

The `wontfix` label does not exist here, and no issue carrying a `req:` label is
closed as not planned. Both are the same rule from two directions: an idea is
reordered, never dropped, and a tracker that can express "not planned" over a
requirement is a tracker where a requirement can quietly stop being planned.

Two halves, because CI runs this on a checkout that may have no tracker
credentials. The local half reads `.roadmap-sync.yaml` and the roadmap files and
always runs. The tracker half shells out to `gh` and is skipped, loudly, when
`gh` is absent or unauthenticated. A skipped tracker half prints what it skipped
and why, so a green run never silently means "nothing was checked".
"""

from __future__ import annotations

import json
import shutil
import subprocess
from dataclasses import dataclass, field
from pathlib import Path

from twinflow_roadmap import yamlio
from twinflow_roadmap.errors import Finding, RoadmapError
from twinflow_roadmap.roadmap import ROADMAP_FILE, Roadmap

SYNC_FILE = ".roadmap-sync.yaml"

#: Labels that may not exist in the repository, whatever the config says. The
#: config has to name them too, and the two are compared: a config that quietly
#: dropped `wontfix` would otherwise disable the check it exists to run.
REQUIRED_BANNED = ("wontfix",)


@dataclass
class DriftReport:
    findings: list[Finding] = field(default_factory=list)
    #: What could not be checked, and why. Printed whether or not it is empty.
    skipped: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.findings


def _gh(repo: str, *args: str) -> list[dict] | None:
    """One `gh` call returning parsed JSON, or None when gh cannot answer."""
    executable = shutil.which("gh")
    if executable is None:
        return None
    try:
        completed = subprocess.run(  # noqa: S603
            [executable, *args, "--repo", repo],
            capture_output=True,
            text=True,
            timeout=60,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired):
        return None
    if completed.returncode != 0:
        return None
    try:
        return json.loads(completed.stdout or "[]")
    except json.JSONDecodeError:
        return None


def load_sync_config(root: Path) -> dict:
    document = yamlio.read(root / SYNC_FILE)
    return yamlio.plain(document)


def check_drift(roadmap: Roadmap, *, offline: bool = False) -> DriftReport:
    """Check the local policy, then the tracker if one can be reached."""
    report = DriftReport()
    root = roadmap.root

    try:
        config = load_sync_config(root)
    except RoadmapError as error:
        report.findings.append(Finding("SYNC-MISSING", str(error), SYNC_FILE))
        return report

    banned = list(config.get("banned_labels") or [])
    for label in REQUIRED_BANNED:
        if label not in banned:
            report.findings.append(
                Finding(
                    "SYNC-BANNED",
                    f"{SYNC_FILE} does not ban the {label} label. The ban is the policy, and a "
                    f"config that drops it turns the check off",
                    SYNC_FILE,
                )
            )
    if config.get("dry_run_default") is not True:
        report.findings.append(
            Finding(
                "SYNC-DRYRUN",
                f"{SYNC_FILE} sets dry_run_default to {config.get('dry_run_default')!r}. A sync "
                f"that applies by default applies from a job nobody meant to run",
                SYNC_FILE,
            )
        )
    contexts = list(config.get("allowed_apply_contexts") or [])
    if [context for context in contexts if context != "release-workflow"]:
        report.findings.append(
            Finding(
                "SYNC-CONTEXT",
                f"{SYNC_FILE} allows apply from {contexts}. Only release-workflow may apply, "
                f"and only milestone lifecycle operations",
                SYNC_FILE,
            )
        )

    repo = str(config.get("repo") or "")
    if offline:
        report.skipped.append("tracker checks: --offline was passed")
        return report
    if shutil.which("gh") is None:
        report.skipped.append(
            "tracker checks: gh is not installed, so labels, milestones, and issues were not read"
        )
        return report

    labels = _gh(repo, "label", "list", "--json", "name", "--limit", "200")
    if labels is None:
        report.skipped.append(
            f"tracker checks: gh could not read {repo}, which usually means no credentials in "
            f"this environment"
        )
        return report

    present = {entry.get("name") for entry in labels}
    for label in banned:
        if label in present:
            report.findings.append(
                Finding(
                    "DRIFT-LABEL",
                    f"the {label} label exists in {repo}. Delete it: an idea is reordered, "
                    f"never dropped",
                    SYNC_FILE,
                    ids=(label,),
                )
            )

    issues = _gh(
        repo,
        "issue",
        "list",
        "--state",
        "closed",
        "--json",
        "number,labels,stateReason,milestone,title",
        "--limit",
        "500",
    )
    if issues is None:
        report.skipped.append("tracker checks: gh could not list closed issues")
        return report

    for issue in issues:
        names = {label.get("name", "") for label in issue.get("labels") or []}
        requirement_labels = sorted(name for name in names if name.startswith("req:"))
        if requirement_labels and issue.get("stateReason") == "NOT_PLANNED":
            report.findings.append(
                Finding(
                    "DRIFT-NOTPLANNED",
                    f"issue #{issue.get('number')} carries {', '.join(requirement_labels)} and "
                    f"is closed as not planned. Reopen it and reorder the work package instead",
                    ROADMAP_FILE,
                    ids=tuple(requirement_labels),
                )
            )

    open_issues = _gh(
        repo,
        "issue",
        "list",
        "--state",
        "all",
        "--json",
        "number,title,milestone",
        "--limit",
        "500",
    )
    if open_issues is None:
        report.skipped.append("tracker checks: gh could not list issues for the milestone check")
        return report

    titles = {str(issue.get("title", "")) for issue in open_issues}
    projected = [
        package for package in roadmap.work_packages if any(package.id in t for t in titles)
    ]

    # A tracker holding no roadmap issue at all has never been projected, which
    # is a different fact from a tracker that disagrees. Reporting the first as
    # the second makes every work package a finding on a repository whose
    # projection has not been created yet, and that reading blocks the very
    # release whose sync step creates it.
    #
    # One projected work package is enough to say the projection exists, and
    # from there a missing issue is drift.
    if not projected:
        report.skipped.append(
            f"issue checks: no issue in {repo} names a work package, so the tracker holds no "
            f"projection of this plan yet. `just roadmap sync --apply` creates it, and the "
            f"release ritual runs that at step 11c"
        )
        return report

    for package in roadmap.work_packages:
        if package.status == "planned":
            continue
        if not any(package.id in title for title in titles):
            report.findings.append(
                Finding(
                    "DRIFT-ISSUE",
                    f"{package.id} is {package.status} and no issue in {repo} names it, while "
                    f"{len(projected)} other work packages do. Run `just roadmap sync --apply` "
                    f"from a checkout",
                    ROADMAP_FILE,
                    ids=(package.id,),
                )
            )
    return report
