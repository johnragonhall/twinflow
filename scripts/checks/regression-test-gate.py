#!/usr/bin/env python3
"""Regression test gate REG-001: a fix ships with the test that catches it.

    python scripts/checks/regression-test-gate.py --staged .git/COMMIT_EDITMSG
    python scripts/checks/regression-test-gate.py --range v0.1.0..HEAD
    python scripts/checks/regression-test-gate.py --selftest

THE RULE
--------
A commit whose type is `fix` touches at least one test file in the same commit.

A fix without a test is a fix that holds until somebody refactors past it. The
defect is gone from the tree and nothing in the tree remembers it was ever
there, so the next person to touch that code has no way to know which behavior
was paid for. The test is the memory.

This is the enforceable half of docs/testing-policy.md. The half that is not
enforceable here is whether the test actually reproduces the defect, because
nothing mechanical can read a test and tell whether it fails against code that
no longer exists. Section 2 of that page gives the procedure a human follows:
write the test first, watch it fail, then fix. The gate checks that a test is
present, and review checks that it is the right one.

WHY THE TYPE AND NOT A KEYWORD
------------------------------
The type set is parsed out of scripts/hooks/commit-msg, the same way CC-001
reads it, so a type the hook accepts and a type this gate reads can never
disagree. `fix` is the one Conventional Commits 1.0.0 binds to a bug, and
binding the rule to the type means the author declares the category once, in
the subject, rather than in a second place this gate would have to trust.

THE EXEMPTION IS A TRAILER, NOT A GUESS
---------------------------------------
Some fixes genuinely cannot carry a test: a broken link in a document, a
workflow that fails to parse, a typo in a comment. Those pass by writing

    Regression-Test: none - <why this defect has no test that could fail>

in the commit message. A trailer rather than a scope allowlist, because an
allowlist decides in advance that a whole category needs no test, and `fix(ci)`
covers both a typo and a workflow that silently skipped a job. The trailer puts
the reason in the log next to the commit it excuses, where review reads it.

THE BASELINE
------------
History before this gate landed was written under a policy that did not exist,
and rewriting it would rewrite every hash. `--range` therefore takes an
explicit range and the justfile passes one that starts where the policy starts.
Nothing here defaults to scanning the whole history and calling the past a
failure.
"""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
COMMIT_MSG_HOOK = REPO_ROOT / "scripts" / "hooks" / "commit-msg"

#: The alternation inside the hook's subject regex, read rather than copied.
#: CC-001 reads the same line for the same reason: two copies drift, and then a
#: commit the hook accepted fails the gate that runs after it.
_HOOK_TYPES = re.compile(r"\^\((?P<types>[a-z]+(?:\|[a-z]+)+)\)")

#: Conventional Commits 1.0.0: type, optional scope, optional breaking marker.
_SUBJECT = re.compile(
    r"^(?P<type>[a-z]+)(?:\((?P<scope>[a-z0-9_-]+)\))?(?P<breaking>!)?: (?P<description>.+)$"
)

#: The type this gate binds to. Conventional Commits 1.0.0 defines `fix` as a
#: commit that patches a bug, which is exactly the set that owes a test.
FIX_TYPE = "fix"

#: A FIX category heading in the body, which the commit-msg hook already
#: requires a body to carry one of. The type alone undercounts: a commit typed
#: `feat` or `refactor` that repairs something declares it here, and the
#: changelog reads the same headings to route a mostly-SECURITY commit to its
#: own section. Reading the author's own declaration beats scanning the
#: description for the word, which flags "say what to fix" and every commit
#: about the fix gate itself.
_FIX_CATEGORY = re.compile(r"^FIX:?[ \t]*$", re.MULTILINE)

#: `Regression-Test: none - reason`. The reason is required and has to say
#: something: a trailer with an empty reason is a trailer that excuses itself.
#: The dashes are written as escapes rather than as characters. `re` reads
#: them the same way, and the style gate refuses a literal en or em dash in
#: the tree.
_EXEMPTION = re.compile(
    r"^Regression-Test:\s*none\s*[-\u2013\u2014]\s*(?P<reason>\S.*)$", re.MULTILINE
)

#: How short a reason is too short to be one.
MIN_REASON_CHARS = 20

#: `Regression-Test: <path>`, naming a test that already covers the defect.
#: A data fix is the case: correcting roadmap.yaml or gates.yaml can be caught
#: by a check that predates the commit, so the covering test is red before the
#: fix and green after, and the commit touches no test file because there was
#: nothing to add. The path is verified rather than taken on trust.
_COVERED_BY = re.compile(r"^Regression-Test:\s*(?P<path>[\w./\\-]+\.py)\s*$", re.MULTILINE)

#: What counts as a test. A path under a tests directory, or a file named the
#: way pytest discovers one.
TEST_DIR_PARTS = ("tests",)
TEST_NAME = re.compile(r"^(test_.+|.+_test)\.py$")

#: Corpora a known-answer test compares against. Regenerating one of these is
#: the test changing, so it counts.
TEST_DATA_SUFFIXES = (".kat", ".jsonl")
TEST_DATA_DIRS = ("corpus", "fixtures", "golden", "testdata")


def hook_types() -> frozenset[str]:
    """The types the commit-msg hook accepts, read from the hook itself."""
    if not COMMIT_MSG_HOOK.is_file():
        raise SystemExit(
            f"BLOCKED: {COMMIT_MSG_HOOK} is missing, so the type set cannot be read. "
            f"This gate refuses to guess it"
        )
    text = COMMIT_MSG_HOOK.read_text(encoding="utf-8")
    match = _HOOK_TYPES.search(text)
    if not match:
        raise SystemExit(
            f"BLOCKED: no type alternation found in {COMMIT_MSG_HOOK}. The hook's subject "
            f"regex changed shape and this gate cannot read it"
        )
    return frozenset(match.group("types").split("|"))


def is_test_path(path: str) -> bool:
    """Whether a repository-relative path is a test or the data one reads."""
    parts = Path(path).parts
    if any(part in TEST_DIR_PARTS for part in parts):
        return True
    if TEST_NAME.match(Path(path).name):
        return True
    is_data = Path(path).suffix in TEST_DATA_SUFFIXES
    return is_data and any(part in TEST_DATA_DIRS for part in parts)


def git(*args: str) -> str:
    result = subprocess.run(
        ["git", *args], cwd=REPO_ROOT, capture_output=True, text=True, check=False
    )
    if result.returncode != 0:
        raise SystemExit(f"BLOCKED: git {' '.join(args)} failed: {result.stderr.strip()}")
    return result.stdout


def subject_of(message: str) -> str:
    for line in message.splitlines():
        if line.strip():
            return line.strip()
    return ""


def covering_test(message: str) -> str | None:
    """The test a `Regression-Test: <path>` trailer names, if there is one."""
    match = _COVERED_BY.search(message)
    return match.group("path").strip() if match else None


def exemption_reason(message: str) -> str | None:
    match = _EXEMPTION.search(message)
    return match.group("reason").strip() if match else None


def repairs(match: re.Match[str], message: str) -> bool:
    """True when this commit patches a defect, by its type or by its own body.

    Two declarations, either of which counts. `fix(...)` is the conventional
    one. A FIX category in the body is the same claim made by a commit whose
    headline work is something else, and a repair carried inside a feature owes
    a test exactly as much as one committed on its own.
    """
    if match.group("type") == FIX_TYPE:
        return True
    body = message.split("\n", 1)[1] if "\n" in message else ""
    return _FIX_CATEGORY.search(body) is not None


def judge(message: str, paths: list[str], types: frozenset[str]) -> list[str]:
    """Findings for one commit. Empty means it satisfies the rule."""
    subject = subject_of(message)
    match = _SUBJECT.match(subject)
    if not match:
        # CC-001 owns the shape of a subject. A subject this gate cannot parse
        # is that gate's finding, not this one's, and reporting it twice sends
        # the author to two places for one defect.
        return []
    if not repairs(match, message):
        return []

    covering = covering_test(message)
    if covering is not None:
        if not is_test_path(covering):
            return [
                f"names `Regression-Test: {covering}`, which is not a test path. "
                f"The trailer names the test that already covers the defect, and a "
                f"path outside a tests directory is not one"
            ]
        if not (REPO_ROOT / covering).is_file():
            return [
                f"names `Regression-Test: {covering}`, which is not in the checkout. "
                f"A trailer naming a test nobody can run records nothing"
            ]
        return []

    reason = exemption_reason(message)
    if reason is not None:
        if len(reason) < MIN_REASON_CHARS:
            return [
                f"carries `Regression-Test: none` with a {len(reason)}-character reason. "
                f"An exemption reason states why the defect has no test that could fail, "
                f"in at least {MIN_REASON_CHARS} characters"
            ]
        return []

    if any(is_test_path(path) for path in paths):
        return []

    return [
        "is a fix and touches no test. A fix without a test is a fix that holds until "
        "somebody refactors past it: the defect leaves the tree and nothing in the tree "
        "remembers it was there. Add the test that fails against the unfixed code, or "
        "record `Regression-Test: none - <reason>` in the message"
    ]


def check_staged(message_file: Path, types: frozenset[str]) -> list[str]:
    if not message_file.is_file():
        raise SystemExit(f"BLOCKED: no commit message at {message_file}")
    message = message_file.read_text(encoding="utf-8", errors="replace")
    # A comment line in a commit template is not part of the message.
    message = "\n".join(line for line in message.splitlines() if not line.startswith("#"))
    paths = [p for p in git("diff", "--cached", "--name-only").splitlines() if p.strip()]
    return [f"this commit {finding}" for finding in judge(message, paths, types)]


def check_range(rev_range: str, types: frozenset[str]) -> list[str]:
    findings = []
    revisions = [r for r in git("rev-list", rev_range).splitlines() if r.strip()]
    for revision in revisions:
        message = git("log", "-1", "--format=%B", revision)
        paths = [
            p
            for p in git(
                "diff-tree", "--no-commit-id", "--name-only", "-r", "-m", revision
            ).splitlines()
            if p.strip()
        ]
        subject = subject_of(message)
        for finding in judge(message, paths, types):
            findings.append(f"{revision[:9]} {subject[:60]!r} {finding}")
    return findings


def selftest() -> int:
    """The gate has to be seen failing, or it is indistinguishable from absent."""
    types = frozenset({"fix", "feat", "docs"})
    cases = [
        ("fix: a thing", ["src/a.py"], 1, "a fix with no test"),
        ("fix: a thing", ["src/a.py", "tests/test_a.py"], 0, "a fix with a test"),
        ("fix: a thing", ["src/a.py", "pkg/tests/test_a.py"], 0, "a test under a package"),
        ("fix: a thing", ["src/a.py", "src/a_test.py"], 0, "a pytest-named sibling"),
        ("feat: a thing", ["src/a.py"], 0, "a feature owes nothing here"),
        ("docs: a thing", ["README.md"], 0, "documentation owes nothing here"),
        (
            "feat: a thing\n\nFIX\n- the off-by-one under it\n",
            ["src/a.py"],
            1,
            "a repair declared in the body of a feature owes a test",
        ),
        (
            "feat: a thing\n\nFIX\n- the off-by-one under it\n",
            ["src/a.py", "tests/test_a.py"],
            0,
            "and is satisfied by one",
        ),
        (
            "refactor: split it\n\nFIX:\n- the leak it hid\n",
            ["src/a.py"],
            1,
            "the heading counts with or without its colon",
        ),
        (
            "feat: a thing\n\nBACKEND\n- prefix a line with FIX and nothing else\n",
            ["src/a.py"],
            0,
            "FIX inside a bullet is prose, not a category heading",
        ),
        (
            "feat(gate): say what to fix\n\nFEAT\n- the message\n",
            ["src/a.py"],
            0,
            "the word fix in a description is not a declaration",
        ),
        (
            "fix: a link\n\nRegression-Test: none - a dead link has no runtime behavior",
            ["docs/x.md"],
            0,
            "an exempted fix",
        ),
        (
            "fix: a link\n\nRegression-Test: none - typo",
            ["docs/x.md"],
            1,
            "an exemption with no real reason",
        ),
        (
            "fix: data\n\nRegression-Test: tests/test_regression_test_gate.py",
            ["roadmap.yaml"],
            0,
            "a data fix naming the test that already covers it",
        ),
        (
            "fix: data\n\nRegression-Test: tests/test_nope.py",
            ["roadmap.yaml"],
            1,
            "a trailer naming a test nobody can run",
        ),
        (
            "fix: data\n\nRegression-Test: scripts/checks/prose-gate.py",
            ["roadmap.yaml"],
            1,
            "a trailer naming something that is not a test",
        ),
        ("not a conventional subject", ["src/a.py"], 0, "CC-001 owns an unparseable subject"),
    ]
    failures = 0
    for message, paths, expected, label in cases:
        actual = len(judge(message, paths, types))
        status = "ok" if actual == expected else "FAILED"
        if actual != expected:
            failures += 1
        print(f"  [{status}] {label}: {actual} findings, expected {expected}")

    print(f"[reg-001] selftest: {len(cases) - failures}/{len(cases)} cases")
    return 1 if failures else 0


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--staged", type=Path, metavar="MSGFILE", help="the commit being written")
    group.add_argument("--range", dest="rev_range", help="a revision range, e.g. v0.1.0..HEAD")
    group.add_argument(
        "--selftest", action="store_true", help="prove the rule fires and where it does not"
    )
    args = parser.parse_args(argv)

    if args.selftest:
        return selftest()

    types = hook_types()
    if FIX_TYPE not in types:
        raise SystemExit(
            f"BLOCKED: the commit-msg hook does not accept {FIX_TYPE!r}, so this gate would "
            f"never fire. Either the hook changed or this gate is checking the wrong type"
        )

    if args.staged:
        findings = check_staged(args.staged, types)
    else:
        findings = check_range(args.rev_range, types)

    if findings:
        sys.stderr.write("\n\033[31mBLOCKED: a fix ships with its test [REG-001]\033[0m\n")
        for finding in findings:
            sys.stderr.write(f"  {finding}\n")
        sys.stderr.write("\n  docs/testing-policy.md section 2 gives the procedure.\n")
        return 1

    print("[reg-001] every fix in scope carries a test")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
