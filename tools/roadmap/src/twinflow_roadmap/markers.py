"""Deferred metric markers, and the work packages that owe them.

A marker in the documentation may name the tag its number arrives at:

    <!--METRIC:agent_eval_accuracy@v0.3.0-->TBD<!--/METRIC-->

which lets a release before that tag ship without the number. On its own that is
a promise written in a comment, and a promise in a comment is a promise nobody
tracks: the tag can move to a later release, one edit at a time, and every
release passes on the way.

So the plan owns it. A work package in the phase that tag releases names the
metric among its deliverables:

    deliverables:
      - "metric:agent_eval_accuracy"

and this module asserts the two agree. A deferred marker with no work package
behind it is a number nobody is scheduled to measure, and a work package naming
a metric no document carries is a deliverable with nothing to fill.

The check runs inside `roadmap validate`, so moving a marker's tag fails the
build unless the work that produces it moves too.
"""

from __future__ import annotations

import re
import subprocess
from dataclasses import dataclass
from pathlib import Path

from twinflow_roadmap.errors import Finding

#: `<!--METRIC:name@v0.3.0-->value<!--/METRIC-->`, the grammar
#: scripts/checks/metric-marker-gate.sh owns. Read here, never redefined: the
#: gate decides what a marker is and this module decides who owes it.
MARKER = re.compile(
    r"<!--METRIC:(?P<name>[A-Za-z0-9_]+)(?:@(?P<arms>v\d+\.\d+\.\d+))?-->"
    r"(?P<value>[^<]*)<!--/METRIC-->"
)

#: The deliverable form that claims a metric.
DELIVERABLE = re.compile(r"^metric:(?P<name>[A-Za-z0-9_]+)$")

#: Values that mean the number is not measured yet.
UNFILLED = {"TBD", "tbd", "", "?", "N/A"}


@dataclass(frozen=True)
class Marker:
    name: str
    arms_at: str | None
    value: str
    path: str
    line: int

    @property
    def unfilled(self) -> bool:
        return self.value.strip() in UNFILLED


def scan(root: Path) -> list[Marker]:
    """Every marker in the tracked documentation."""
    listing = subprocess.run(  # noqa: S603
        ["git", "ls-files", "*.md"],  # noqa: S607
        cwd=root,
        capture_output=True,
        text=True,
        check=False,
    )
    found: list[Marker] = []
    for name in listing.stdout.split():
        path = root / name
        if not path.is_file():
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue
        for number, line in enumerate(text.splitlines(), start=1):
            for match in MARKER.finditer(line):
                found.append(
                    Marker(
                        name=match.group("name"),
                        arms_at=match.group("arms"),
                        value=match.group("value"),
                        path=Path(name).as_posix(),
                        line=number,
                    )
                )
    return found


def claimed_metrics(roadmap) -> dict[str, list]:
    """Metric name to the work packages that name it as a deliverable."""
    claims: dict[str, list] = {}
    for package in roadmap.work_packages:
        for deliverable in package.deliverables:
            match = DELIVERABLE.match(deliverable.strip())
            if match:
                claims.setdefault(match.group("name"), []).append(package)
    return claims


def check(roadmap) -> list[Finding]:
    """Every deferred number is owed by a work package, and the reverse."""
    findings: list[Finding] = []
    markers = scan(roadmap.root)
    claims = claimed_metrics(roadmap)
    tag_phase = {phase.release_tag: phase.id for phase in roadmap.phases}

    for marker in markers:
        if not marker.unfilled or marker.arms_at is None:
            continue

        phase = tag_phase.get(marker.arms_at)
        if phase is None:
            findings.append(
                Finding(
                    "MARKER-TAG",
                    f"{marker.name} arrives at {marker.arms_at}, which no phase releases. A "
                    f"deferred number names a tag this plan actually cuts",
                    marker.path,
                    marker.line,
                    (marker.name,),
                )
            )
            continue

        owners = [package for package in claims.get(marker.name, []) if package.phase == phase]
        if not owners:
            elsewhere = claims.get(marker.name, [])
            detail = (
                f"and the work packages claiming it sit in "
                f"{', '.join(sorted({p.phase for p in elsewhere}))}"
                if elsewhere
                else "and no work package claims it"
            )
            findings.append(
                Finding(
                    "MARKER-ORPHAN",
                    f"{marker.name} is deferred to {marker.arms_at}, which phase {phase} "
                    f"releases, {detail}. Name it as a deliverable on the work package that "
                    f"measures it, or the number is scheduled nowhere",
                    marker.path,
                    marker.line,
                    (marker.name, phase),
                )
            )

    # The failure a deferred number actually has: the phase ships, the work
    # package is marked done, and the marker still reads TBD. The release gate
    # catches it at the tag, and only if somebody cuts that tag; this catches it
    # the moment the work package claims to be finished.
    by_name: dict[str, list[Marker]] = {}
    for marker in markers:
        by_name.setdefault(marker.name, []).append(marker)

    for name, packages in sorted(claims.items()):
        for package in packages:
            if package.status != "done":
                continue
            still_empty = [marker for marker in by_name.get(name, []) if marker.unfilled]
            for marker in still_empty:
                findings.append(
                    Finding(
                        "MARKER-SKIPPED",
                        f"{package.id} is done and delivers metric {name}, and the marker in "
                        f"{marker.path} still reads {marker.value.strip() or 'empty'}. The work "
                        f"that measures the number is finished, so the number exists or the "
                        f"work package does not",
                        marker.path,
                        marker.line,
                        (package.id, name),
                    )
                )

    documented = {marker.name for marker in markers}
    for name, packages in sorted(claims.items()):
        if name not in documented:
            for package in packages:
                findings.append(
                    Finding(
                        "MARKER-UNUSED",
                        f"{package.id} delivers metric {name}, and no document carries a marker "
                        f"for it. The deliverable fills nothing",
                        "roadmap.yaml",
                        roadmap.lines.get(("roadmap.yaml", package.id)),
                        (package.id, name),
                    )
                )

    return findings
