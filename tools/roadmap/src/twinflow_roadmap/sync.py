"""Sync: GitHub as a projection of roadmap.yaml.

    twinflow-roadmap sync                    print the plan and change nothing
    twinflow-roadmap sync --apply            apply it from a checkout
    twinflow-roadmap sync --apply --context release-workflow

One milestone per phase, one issue per work package, and every label generated.
Nobody opens a roadmap issue by hand and nobody edits a generated body, because
the two would then disagree and the disagreement would be invisible until
somebody read both.

TWO CLASSES OF OPERATION, AND THE CLASS DECIDES WHO MAY APPLY IT
-----------------------------------------------------------------
Milestone lifecycle, which is creating a milestone, closing one, and setting its
description or due date, is what step 11 of the release ritual performs
unattended. Issue mutation, which is everything else, waits for a human running
`--apply` from a checkout.

The scope is named rather than asserted away. A blanket "CI never applies" rule
is what contradicted the release ritual, which has to close the milestone it
just released.

WHY THE PLAN IS A VALUE RATHER THAN A SEQUENCE OF CALLS
--------------------------------------------------------
Every operation is computed before any is performed, so the dry run prints
exactly what the apply would do. A tool that decided its next call from the
result of the last one could not show you the plan, and a plan you cannot read
before it runs against a public tracker is a plan nobody should run.

Nothing here deletes. An issue whose work package is gone is reported and left
alone: the roadmap has no way to drop a work package, so an issue with no
package behind it is a finding about this tool or about somebody editing the
tracker by hand, and neither is fixed by deleting the evidence.
"""

from __future__ import annotations

import json
import shutil
import subprocess
from dataclasses import dataclass, field

from twinflow_roadmap.drift import SYNC_FILE, load_sync_config
from twinflow_roadmap.model import Phase, WorkPackage
from twinflow_roadmap.roadmap import Roadmap

#: Milestone lifecycle. The release workflow may apply these unattended.
MILESTONE = "milestone"

#: Issue mutation. A human runs these from a checkout.
ISSUE = "issue"

#: The label taxonomy of ROADMAP.md section 8. Generated, never hand-applied:
#: a hand-applied label is a claim about a work package that roadmap.yaml did
#: not make.
LABEL_PREFIXES = ("phase:", "req:", "tier:", "brick:", "gate:", "wave:")


@dataclass(frozen=True)
class Operation:
    """One change the tracker needs, and what it is for."""

    #: MILESTONE or ISSUE. Decides which contexts may apply it.
    kind: str
    #: What this does, in one line, for the dry run.
    summary: str
    #: The gh arguments, without the executable and without --repo.
    args: tuple[str, ...]

    def __str__(self) -> str:
        return f"[{self.kind}] {self.summary}"


@dataclass
class SyncPlan:
    operations: list[Operation] = field(default_factory=list)
    #: What could not be planned, and why. Printed whether or not it is empty.
    skipped: list[str] = field(default_factory=list)
    #: Tracker state that roadmap.yaml does not explain. Reported, never fixed.
    unexplained: list[str] = field(default_factory=list)

    @property
    def milestone_operations(self) -> list[Operation]:
        return [op for op in self.operations if op.kind == MILESTONE]

    @property
    def issue_operations(self) -> list[Operation]:
        return [op for op in self.operations if op.kind == ISSUE]

    def render(self) -> str:
        lines = []
        if self.skipped and not self.operations:
            # An empty plan means "nothing to do" only when the tracker was
            # actually read. Saying "already matches" over a read that never
            # happened is the same defect as a skipped CI job reading as a pass.
            lines.append("[sync] no plan: the tracker was not read, so nothing was compared")
        elif not self.operations:
            lines.append("[sync] the tracker already matches roadmap.yaml")
        else:
            lines.append(
                f"[sync] {len(self.milestone_operations)} milestone operations, "
                f"{len(self.issue_operations)} issue operations"
            )
            for operation in self.operations:
                lines.append(f"  {operation}")
        for note in self.skipped:
            lines.append(f"[sync] SKIP {note}")
        for note in self.unexplained:
            lines.append(f"[sync] UNEXPLAINED {note}")
        return "\n".join(lines)


def _gh_json(repo: str, *args: str) -> list[dict] | None:
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
        parsed = json.loads(completed.stdout or "[]")
    except json.JSONDecodeError:
        return None
    return parsed if isinstance(parsed, list) else [parsed]


def phase_by_id(roadmap: Roadmap, phase_id: str) -> Phase:
    """One phase, by id. The loader already refused an unknown one."""
    for phase in roadmap.phases:
        if phase.id == phase_id:
            return phase
    raise KeyError(phase_id)


def milestone_title(config: dict, phase: Phase) -> str:
    template = config.get("milestone_title_template") or "{phase_id} {name} ({release_tag})"
    return template.format(phase_id=phase.id, name=phase.name, release_tag=phase.release_tag)


def issue_title(config: dict, package: WorkPackage) -> str:
    template = config.get("issue_title_template") or "[{phase_id}] {id} {title}"
    return template.format(phase_id=package.phase, id=package.id, title=package.title)


def labels_for(roadmap: Roadmap, package: WorkPackage) -> list[str]:
    """Every label this work package gets, per ROADMAP.md section 8.

    Sorted, because the comparison against the tracker is on the set and a
    stable order makes the dry run readable rather than reshuffled each run.
    """
    labels = {f"phase:{package.phase}", f"wave:{package.wave}"}
    labels.update(f"req:{entry.id}" for entry in package.covers)
    labels.update(f"gate:{gate_id}" for gate_id in package.gates)
    if package.brick:
        labels.add(f"brick:{package.brick}")
    for entry in package.covers:
        requirement = roadmap.requirements.get(entry.id)
        if requirement is not None:
            labels.add(f"tier:{requirement.tier}")
    if package.status == "reordered":
        labels.add("moved")
    return sorted(labels)


def milestone_body(roadmap: Roadmap, phase: Phase) -> str:
    """What the milestone description carries, per ROADMAP.md section 8."""
    depends = ", ".join(phase.depends_on_phases) or "nothing"
    unblocks = ", ".join(
        other.id for other in roadmap.phases if phase.id in other.depends_on_phases
    )
    gates = roadmap.exit_gates(phase.id)
    packages = [p for p in roadmap.work_packages if p.phase == phase.id]

    lines = [
        f"**{phase.name}**, released as `{phase.release_tag}`.",
        "",
        phase.delivers.strip(),
        "",
        f"- Depends on: {depends}",
        f"- Unblocks: {unblocks or 'nothing downstream yet'}",
        f"- Work packages: {len(packages)}",
        "",
        f"### Exit gates ({len(gates)})",
        "",
    ]
    for gate_id in gates:
        gate = roadmap.gates[gate_id]
        lines.append(f"- `{gate_id}` ({gate.kind}, {gate.status})")
    lines += [
        "",
        "### Phase exit",
        "",
        f"- [ ] `just gate phase-exit {phase.id}` is green",
        "- [ ] Every work package above is done",
        f"- [ ] The release pipeline produced `{phase.release_tag}` unattended",
        "",
        "Generated from `roadmap.yaml` by `just roadmap sync`. Do not edit by hand.",
    ]
    return "\n".join(lines)


def issue_body(roadmap: Roadmap, package: WorkPackage) -> str:
    """What one work package's issue carries."""
    covers = ", ".join(
        f"`{entry.id}`" + (" (partial)" if entry.partial else "") for entry in package.covers
    )
    depends = ", ".join(f"`{other}`" for other in package.depends_on) or "nothing"

    lines = [
        f"**{package.title}**",
        "",
        f"- Phase: `{package.phase}`, wave {package.wave}",
        f"- Release: `{package.release}`",
        f"- Brick: `{package.brick}`" if package.brick else "- Brick: none",
        f"- Covers: {covers or 'nothing'}",
        f"- Depends on: {depends}",
        "",
        "### Deliverables",
        "",
    ]
    lines += [f"- [ ] `{item}`" for item in package.deliverables] or ["- none recorded yet"]

    if package.gates:
        lines += ["", "### Validation gates", ""]
        for gate_id in package.gates:
            gate = roadmap.gates.get(gate_id)
            assertion = (gate.assertion or "not specified yet").strip() if gate else "unknown gate"
            lines.append(f"- `{gate_id}`: {assertion}")

    lines += [
        "",
        "### Definition of done",
        "",
        "- [ ] Every deliverable above exists",
        "- [ ] Every gate above is at status implemented and passes",
        f"- [ ] `just gate phase-exit {package.phase}` is no worse than before this change",
        "",
        "Generated from `roadmap.yaml` by `just roadmap sync`. Do not edit by hand.",
    ]
    return "\n".join(lines)


def build_plan(roadmap: Roadmap, *, offline: bool = False) -> SyncPlan:
    """What the tracker needs to match roadmap.yaml."""
    plan = SyncPlan()
    config = load_sync_config(roadmap.root)
    repo = str(config.get("repo") or "")

    if not repo:
        plan.skipped.append(f"{SYNC_FILE} names no repo, so there is nothing to project onto")
        return plan
    if offline:
        plan.skipped.append("tracker read: --offline was passed, so no plan was computed")
        return plan
    if shutil.which("gh") is None:
        plan.skipped.append("tracker read: gh is not installed")
        return plan

    milestones = _gh_json(
        repo, "api", f"repos/{repo}/milestones", "--paginate", "--jq", "[.[]]", "--method", "GET"
    )
    if milestones is None:
        plan.skipped.append(
            f"tracker read: gh could not read {repo}, which usually means no credentials here"
        )
        return plan

    by_title = {str(entry.get("title", "")): entry for entry in milestones}
    for phase in roadmap.phases:
        title = milestone_title(config, phase)
        body = milestone_body(roadmap, phase)
        existing = by_title.get(title)
        if existing is None:
            plan.operations.append(
                Operation(
                    MILESTONE,
                    f"create milestone {title!r}",
                    (
                        "api",
                        f"repos/{repo}/milestones",
                        "-f",
                        f"title={title}",
                        "-f",
                        f"description={body}",
                    ),
                )
            )
        elif (existing.get("description") or "").strip() != body.strip():
            number = existing.get("number")
            plan.operations.append(
                Operation(
                    MILESTONE,
                    f"update the description of milestone {title!r}",
                    (
                        "api",
                        f"repos/{repo}/milestones/{number}",
                        "--method",
                        "PATCH",
                        "-f",
                        f"description={body}",
                    ),
                )
            )

    issues = _gh_json(
        repo,
        "issue",
        "list",
        "--state",
        "all",
        "--limit",
        "500",
        "--json",
        "number,title,body,labels,milestone,state",
    )
    if issues is None:
        plan.skipped.append("tracker read: gh could not list issues")
        return plan

    by_issue_title = {str(entry.get("title", "")): entry for entry in issues}
    planned_titles = set()

    for package in roadmap.work_packages:
        title = issue_title(config, package)
        planned_titles.add(title)
        body = issue_body(roadmap, package)
        labels = labels_for(roadmap, package)
        milestone = milestone_title(config, phase_by_id(roadmap, package.phase))
        existing = by_issue_title.get(title)

        if existing is None:
            plan.operations.append(
                Operation(
                    ISSUE,
                    f"open issue {title!r} with {len(labels)} labels",
                    (
                        "issue",
                        "create",
                        "--title",
                        title,
                        "--body",
                        body,
                        "--milestone",
                        milestone,
                        "--label",
                        ",".join(labels),
                    ),
                )
            )
            continue

        number = existing.get("number")
        actual_labels = sorted(
            entry.get("name", "")
            for entry in existing.get("labels") or []
            if str(entry.get("name", "")).startswith(LABEL_PREFIXES)
        )
        if actual_labels != labels:
            plan.operations.append(
                Operation(
                    ISSUE,
                    f"relabel issue #{number} {title!r}",
                    ("issue", "edit", str(number), "--add-label", ",".join(labels)),
                )
            )
        if (existing.get("body") or "").strip() != body.strip():
            plan.operations.append(
                Operation(
                    ISSUE,
                    f"rewrite the body of issue #{number} {title!r}",
                    ("issue", "edit", str(number), "--body", body),
                )
            )
        if package.status == "done" and existing.get("state") == "OPEN":
            plan.operations.append(
                Operation(
                    ISSUE,
                    f"close issue #{number} {title!r}, whose work package is done",
                    ("issue", "close", str(number), "--reason", "completed"),
                )
            )

    for title, entry in sorted(by_issue_title.items()):
        labels = {label.get("name", "") for label in entry.get("labels") or []}
        if title in planned_titles or not any(name.startswith("req:") for name in labels):
            continue
        plan.unexplained.append(
            f"issue #{entry.get('number')} {title!r} carries a req: label and no work package "
            f"names it. Nothing here deletes it: an issue roadmap.yaml cannot explain is a "
            f"finding about this tool or about a tracker edited by hand"
        )

    return plan


def apply_plan(plan: SyncPlan, roadmap: Roadmap, *, context: str | None) -> list[str]:
    """Run the plan, refusing what this context may not perform.

    Returns the operations it refused. An empty list means every operation ran.
    """
    config = load_sync_config(roadmap.root)
    repo = str(config.get("repo") or "")
    allowed = list(config.get("allowed_apply_contexts") or [])

    # A context the config does not name may apply nothing unattended. A human
    # at a checkout passes no context and applies everything, which is the case
    # the config's dry_run_default protects rather than this check.
    may_mutate_issues = context is None
    may_touch_milestones = context is None or context in allowed

    refused: list[str] = []
    executable = shutil.which("gh")
    if executable is None:
        return [str(operation) for operation in plan.operations]

    for operation in plan.operations:
        permitted = may_touch_milestones if operation.kind == MILESTONE else may_mutate_issues
        if not permitted:
            refused.append(str(operation))
            continue
        completed = subprocess.run(  # noqa: S603
            [executable, *operation.args, "--repo", repo],
            capture_output=True,
            text=True,
            timeout=120,
            check=False,
        )
        if completed.returncode != 0:
            refused.append(f"{operation} failed: {completed.stderr.strip()}")

    return refused
