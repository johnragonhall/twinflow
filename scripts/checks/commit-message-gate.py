#!/usr/bin/env python3
"""Commit message gate CC-001, the CON-4 half that reads history.

    python scripts/checks/commit-message-gate.py             since the last tag
    python scripts/checks/commit-message-gate.py --all       the whole history
    python scripts/checks/commit-message-gate.py 0.2.0       and check the bump

Two assertions, from Conventional Commits 1.0.0 and the C9 version policy:

  1 Every commit in range parses as a conventional commit whose type is one the
    commit-msg hook accepts.
  2 With a version argument, the bump those types imply is the bump the tag
    makes over the previous tag.

The local hook is the same rule applied one commit at a time, and this is the
same rule applied to the range a release covers. Both exist because history
cannot be relinted: a subject reaches the log once, and a subject nobody can
parse is a version the release pipeline computes wrongly.

THE TYPE SET IS NOT WRITTEN HERE
--------------------------------
It is parsed out of scripts/hooks/commit-msg. A second copy is a copy that
drifts, and then a commit the hook accepted fails the gate that runs after it,
or the reverse, which is worse.

WHAT IS EXEMPT, AND WHY
-----------------------
The root commit only. GitHub writes "Initial commit" when it creates a
repository from the web, before any hook exists to refuse it, and rewriting the
root commit rewrites every hash in the history. Nothing else is exempt: a merge
commit's subject is written by whoever merged, and the hook asks them for
`chore(merge): ...`.

BUMPS BELOW 1.0.0
-----------------
Semantic Versioning 2.0.0 section 4 puts no compatibility promise on 0.y.z, and
section 5 says 1.0.0 is declared, not arrived at. This project declares it at
the end of P5. So below 1.0.0 a breaking change raises the minor rather than the
major, which is what the phase table already does: one minor per phase.
"""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
COMMIT_MSG_HOOK = REPO_ROOT / "scripts" / "hooks" / "commit-msg"

#: The alternation inside the hook's subject regex. Matching the hook's own
#: line rather than a copy of its contents is what keeps the two in step.
_HOOK_TYPES = re.compile(r"\^\((?P<types>[a-z]+(?:\|[a-z]+)+)\)")

SEMVER = re.compile(r"^(?P<major>\d+)\.(?P<minor>\d+)\.(?P<patch>\d+)$")

#: Conventional Commits 1.0.0: type, optional scope, an optional `!` marking a
#: breaking change, then `: ` and a description.
_SUBJECT = re.compile(
    r"^(?P<type>[a-z]+)(?:\((?P<scope>[a-z0-9_-]+)\))?(?P<breaking>!)?: (?P<description>.+)$"
)

#: Types that add a capability. Everything else the hook accepts is a patch.
MINOR_TYPES = frozenset({"feat"})

_RANK = {"patch": 0, "minor": 1, "major": 2}


class Commit:
    """One commit, as this gate reads it."""

    def __init__(self, sha: str, parents: int, subject: str, body: str) -> None:
        self.sha = sha
        self.parents = parents
        self.subject = subject
        self.body = body

    @property
    def is_root(self) -> bool:
        return self.parents == 0

    def __repr__(self) -> str:  # pragma: no cover - diagnostics only
        return f"Commit({self.sha[:8]}, {self.subject!r})"


def accepted_types() -> frozenset[str]:
    """The type set scripts/hooks/commit-msg enforces."""
    if not COMMIT_MSG_HOOK.is_file():
        raise SystemExit(f"BLOCKED: no commit-msg hook at {COMMIT_MSG_HOOK}")
    match = _HOOK_TYPES.search(COMMIT_MSG_HOOK.read_text(encoding="utf-8"))
    if match is None:
        raise SystemExit(
            "BLOCKED: could not read the type set out of scripts/hooks/commit-msg. "
            "Its subject regex moved, and this gate reads it rather than keeping a copy."
        )
    return frozenset(match.group("types").split("|"))


def _git(*args: str) -> str:
    result = subprocess.run(
        ["git", *args],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    if result.returncode != 0:
        raise SystemExit(f"BLOCKED: git {' '.join(args)} failed: {result.stderr.strip()}")
    return result.stdout


def is_shallow() -> bool:
    """True on a clone that does not carry the history this gate reads.

    A shallow checkout has one commit with no recorded parent, which this gate
    would read as the exempt root and report as a clean history. That is a pass
    nothing could have failed, so it is refused instead. The release workflow
    checks out with fetch-depth 0 for exactly this reason.
    """
    return _git("rev-parse", "--is-shallow-repository").strip() == "true"


def previous_tag() -> str | None:
    """The newest release tag reachable from HEAD, or None before the first."""
    result = subprocess.run(
        ["git", "describe", "--tags", "--abbrev=0", "--match", "v[0-9]*"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    return result.stdout.strip() or None if result.returncode == 0 else None


def commits_in(revision_range: str | None) -> list[Commit]:
    """Every commit in a range, newest first."""
    #: A record separator no commit message contains, because the log is the
    #: one input this gate does not control the shape of.
    unit, record = "\x1f", "\x1e"
    args = ["log", f"--format=%H{unit}%P{unit}%s{unit}%b{record}"]
    if revision_range:
        args.append(revision_range)
    raw = _git(*args)

    commits: list[Commit] = []
    for chunk in raw.split(record):
        chunk = chunk.strip("\n")
        if not chunk:
            continue
        sha, parents, subject, body = chunk.split(unit, 3)
        commits.append(Commit(sha, len(parents.split()), subject, body))
    return commits


def subject_findings(commit: Commit, types: frozenset[str]) -> list[str]:
    """What is wrong with one commit's subject, if anything."""
    if commit.is_root:
        return []

    match = _SUBJECT.match(commit.subject)
    if match is None:
        return [f"{commit.sha[:8]} does not parse as a conventional commit: {commit.subject!r}"]
    if match["type"] not in types:
        return [
            f"{commit.sha[:8]} uses type {match['type']!r}, which the commit-msg hook "
            f"does not accept: {', '.join(sorted(types))}"
        ]
    if commit.subject.rstrip().endswith("."):
        return [f"{commit.sha[:8]} ends its subject with a period: {commit.subject!r}"]
    return []


def is_breaking(commit: Commit) -> bool:
    """Conventional Commits 1.0.0 marks a break two ways, and both count."""
    match = _SUBJECT.match(commit.subject)
    if match and match["breaking"]:
        return True
    return any(
        line.startswith(("BREAKING CHANGE:", "BREAKING-CHANGE:"))
        for line in commit.body.splitlines()
    )


def bump_from(commits: list[Commit]) -> str:
    """The smallest bump the commit types make honest."""
    result = "patch"
    for commit in commits:
        if commit.is_root:
            continue
        if is_breaking(commit):
            return "major"
        match = _SUBJECT.match(commit.subject)
        if match and match["type"] in MINOR_TYPES:
            result = "minor"
    return result


def bump_between(previous: str, proposed: str) -> str | None:
    """The bump a tag makes over the one before it, or None if it moves nowhere."""
    old, new = SEMVER.match(previous), SEMVER.match(proposed)
    if not old or not new:
        return None
    if int(new["major"]) > int(old["major"]):
        return "major"
    if int(new["major"]) == int(old["major"]) and int(new["minor"]) > int(old["minor"]):
        return "minor"
    if (
        int(new["major"]) == int(old["major"])
        and int(new["minor"]) == int(old["minor"])
        and int(new["patch"]) > int(old["patch"])
    ):
        return "patch"
    return None


def expected_bump(needed: str, previous: str) -> str:
    """The bump policy, with the 0.y.z rule applied.

    Below 1.0.0 there is no compatibility promise to break, so a break raises
    the minor. Above it, a break is a major and nothing else will do.
    """
    if needed == "major" and previous.startswith("0."):
        return "minor"
    return needed


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "version",
        nargs="?",
        help="the version about to be tagged. Without one, only the subjects are checked.",
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="read the whole history rather than the commits since the last tag",
    )
    args = parser.parse_args(argv)

    if is_shallow():
        sys.stderr.write(
            "\nBLOCKED: this is a shallow clone, so the commit range is not the"
            " real one. Check out with fetch-depth 0 before running the commit gate;"
            " a pass over one commit with no parent is a pass nothing could have"
            " failed.\n"
        )
        return 1

    types = accepted_types()
    tag = None if args.all else previous_tag()
    commits = commits_in(f"{tag}..HEAD" if tag else None)
    scope = "the whole history" if tag is None else f"the {len(commits)} commits since {tag}"

    findings: list[str] = []
    for commit in commits:
        findings.extend(subject_findings(commit, types))

    if args.version is not None:
        if not SEMVER.match(args.version):
            findings.append(f"{args.version!r} is not a semantic version")
        elif tag is None:
            print(
                f"[commits] no previous tag, so the type-derived bump has nothing to "
                f"move from. {args.version} is the first tag and its number is declared, "
                f"not computed"
            )
        else:
            previous = tag.lstrip("v")
            needed = expected_bump(bump_from(commits), previous)
            actual = bump_between(previous, args.version)
            if actual is None:
                findings.append(f"{args.version} does not move forward from {previous}")
            elif _RANK[actual] < _RANK[needed]:
                findings.append(
                    f"{args.version} is a {actual} bump from {previous}, but the commit "
                    f"types since {tag} make a {needed} the smallest honest bump"
                )

    if findings:
        sys.stderr.write("\n\033[31mBLOCKED: commit messages [CC-001]\033[0m\n")
        for finding in findings:
            sys.stderr.write(f"  {finding}\n")
        sys.stderr.write(
            "\nConventional Commits 1.0.0: type(scope): description, with an optional\n"
            "`!` or a BREAKING CHANGE footer marking a break. The release pipeline\n"
            "derives the version from these types, so a subject nobody can parse is a\n"
            "wrong version rather than an untidy log.\n"
        )
        return 1

    print(f"[commits] {len(commits)} commits over {scope}: every subject parses")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
