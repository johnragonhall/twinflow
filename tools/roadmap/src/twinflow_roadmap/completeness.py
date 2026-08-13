"""Completeness: done means delivered, and nothing in the tree is unreachable.

Two checks, both answering questions a status field cannot.

DELIVERED
---------
`status: done` is a claim somebody typed. Nothing else in this tool reads it
against the tree, so a work package can be marked done with none of its
deliverables on disk and every other check still passes: coverage proves the
requirement is placed, validate proves the graph is sound, and neither opens a
file. This check does.

A deliverable takes one of three forms and each is verified differently:

    a path        exists in the checkout
    `just <name>` the justfile carries that recipe
    `metric:<n>`  markers.py owns it, and this check leaves it alone

REACHED
-------
The other direction. A script under scripts/ or tools/ that nothing invokes is
dead code, and dead code in a repository built as a hiring artifact reads as
work abandoned halfway. A script counts as reached when the justfile, a
workflow, a git hook, a gate command, or another script names it.

An orphan is allowed when the plan says so: a work package may name the file as
a deliverable of work that is not finished, which is the "unless the plan needs
it" case. That exemption is data rather than a list maintained here, so it
expires when the work package does.
"""

from __future__ import annotations

import re
from pathlib import Path

from twinflow_roadmap.errors import Finding

#: Named here rather than imported from the roadmap module. That module imports
#: this one to run the check, so importing it back is a cycle, and markers.py
#: names the same file the same way for the same reason.
ROADMAP_FILE = "roadmap.yaml"

#: `just <recipe>`, possibly with arguments. Only the recipe name is checked:
#: the arguments are what a caller passes, not something the justfile declares.
JUST_RECIPE = re.compile(r"^just\s+([a-z][a-z0-9-]*)")

#: A deliverable naming a metric. markers.py checks these against the documents
#: that carry the marker, so this module would only duplicate it.
METRIC_DELIVERABLE = re.compile(r"^metric:")

#: Where a script has to be named to count as reached.
CALLERS = (
    Path("justfile"),
    Path("gates.yaml"),
    Path(".github") / "workflows",
    Path("scripts") / "hooks",
    Path("scripts") / "ci-local.sh",
    Path("pyproject.toml"),
)

#: The directories whose scripts have to be reachable. Package source is out of
#: scope: import-linter already owns which module may reach which, and a module
#: nobody imports is what the brick-isolation tests cover.
SCRIPT_ROOTS = (Path("scripts"), Path("tools"))

#: Extensions that are scripts rather than data or documentation.
SCRIPT_SUFFIXES = (".py", ".sh")


def justfile_recipes(root: Path) -> set[str]:
    """Every recipe name the justfile declares."""
    path = root / "justfile"
    if not path.is_file():
        return set()
    names = set()
    for line in path.read_text(encoding="utf-8").splitlines():
        # A recipe header sits at column zero and ends in a colon. A comment,
        # a continuation, and a recipe body are all indented or prefixed.
        match = re.match(r"^([a-z][a-z0-9-]*)(\s+[^:]*)?:", line)
        if match:
            names.add(match.group(1))
    return names


def check_delivered(roadmap) -> list[Finding]:
    """Every deliverable of a done work package, against the tree."""
    findings: list[Finding] = []
    recipes = justfile_recipes(roadmap.root)

    for package in roadmap.work_packages:
        if package.status != "done":
            continue
        for deliverable in package.deliverables:
            item = deliverable.strip()
            if METRIC_DELIVERABLE.match(item):
                continue

            recipe = JUST_RECIPE.match(item)
            if recipe:
                if recipe.group(1) not in recipes:
                    findings.append(
                        Finding(
                            "DELIV-RECIPE",
                            f"{package.id} is done and names `{item}`, and the justfile "
                            f"carries no recipe {recipe.group(1)!r}",
                            ROADMAP_FILE,
                            ids=(package.id,),
                        )
                    )
                continue

            if not (roadmap.root / item).exists():
                findings.append(
                    Finding(
                        "DELIV-MISSING",
                        f"{package.id} is done and names deliverable {item!r}, which is not "
                        f"in the checkout. Either the work is not done or the deliverable "
                        f"moved and roadmap.yaml still names where it was",
                        ROADMAP_FILE,
                        ids=(package.id,),
                    )
                )

    return findings


def planned_paths(roadmap) -> set[str]:
    """Every path any work package names, done or not.

    Not-done packages count here on purpose: a file that exists because work
    that is still open needs it is the "unless the plan needs it" exemption,
    and it expires when that work package reaches done and gets checked by
    check_delivered instead.
    """
    paths = set()
    for package in roadmap.work_packages:
        for deliverable in package.deliverables:
            item = deliverable.strip()
            if not JUST_RECIPE.match(item) and not METRIC_DELIVERABLE.match(item):
                paths.add(item.rstrip("/"))
    return paths


def caller_text(root: Path) -> str:
    """Everything that could name a script, concatenated once."""
    chunks = []
    for relative in CALLERS:
        path = root / relative
        if path.is_file():
            chunks.append(path.read_text(encoding="utf-8", errors="replace"))
        elif path.is_dir():
            for child in sorted(path.rglob("*")):
                if child.is_file():
                    chunks.append(child.read_text(encoding="utf-8", errors="replace"))
    return "\n".join(chunks)


def check_reached(roadmap) -> list[Finding]:
    """Every script under scripts/ and tools/ that nothing invokes."""
    findings: list[Finding] = []
    root = roadmap.root
    text = caller_text(root)
    planned = planned_paths(roadmap)

    # A script may also be called by another script, so the scripts themselves
    # are part of the caller set. Read once rather than per candidate.
    scripts: list[Path] = []
    for script_root in SCRIPT_ROOTS:
        base = root / script_root
        if not base.is_dir():
            continue
        for path in sorted(base.rglob("*")):
            if path.suffix in SCRIPT_SUFFIXES and "__pycache__" not in path.parts:
                scripts.append(path)

    peer_text = "\n".join(path.read_text(encoding="utf-8", errors="replace") for path in scripts)
    haystack = text + "\n" + peer_text

    for path in scripts:
        relative = path.relative_to(root).as_posix()
        # A package's own module is reached through an import, which
        # import-linter and the brick tests already own.
        if "/src/" in relative or "/tests/" in relative:
            continue
        if relative in planned:
            continue
        # By full path or by bare name: a justfile calls the path, and a Python
        # caller may import the stem.
        if relative in haystack or path.name in haystack:
            continue
        findings.append(
            Finding(
                "ORPHAN-SCRIPT",
                f"{relative} is not named by the justfile, a workflow, a hook, a gate "
                f"command, or another script, and no work package names it as a "
                f"deliverable. A script nothing calls is dead code",
                relative,
            )
        )

    return findings


def check(roadmap) -> list[Finding]:
    """Both halves."""
    return check_delivered(roadmap) + check_reached(roadmap)
