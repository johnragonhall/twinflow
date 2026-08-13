"""The commit message gate (CC-001).

What these pin is the bump arithmetic and the exemption. The arithmetic is what
the release pipeline computes a version from, so a wrong answer here ships a
wrong tag. The exemption is one commit wide on purpose, and a test is the only
thing that keeps it that way.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
GATE = REPO_ROOT / "scripts" / "checks" / "commit-message-gate.py"


def _gate():
    spec = importlib.util.spec_from_file_location("commit_message_gate", GATE)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


gate = _gate()

TYPES = frozenset({"feat", "fix", "refactor", "test", "docs", "chore", "perf"})


def commit(subject: str, body: str = "", parents: int = 1):
    return gate.Commit("0" * 40, parents, subject, body)


def test_the_type_set_comes_from_the_hook():
    # Not a copy. The hook is the thing a contributor's commit meets first, and
    # a gate enforcing a different set would accept what the hook refused.
    assert gate.accepted_types() == TYPES


@pytest.mark.parametrize(
    "subject",
    [
        "feat(rng): derive the child stream from the run seed",
        "fix: pass the roadmap subcommand through to the tool",
        "docs(style): write one English across the tracked tree",
        "perf(kernel): read the clock once per tick",
        "feat(schemas)!: rename the envelope sequence field",
    ],
)
def test_a_conventional_subject_passes(subject):
    assert gate.subject_findings(commit(subject), TYPES) == []


@pytest.mark.parametrize(
    "subject",
    [
        "Initial commit",
        "update the readme",
        "Feat(rng): capitalized type",
        "feature(rng): a type the hook does not accept",
        "feat(RNG): an upper-case scope",
        "feat(rng) missing the colon",
        "feat(rng): ends with a period.",
    ],
)
def test_a_non_conventional_subject_fails(subject):
    assert gate.subject_findings(commit(subject), TYPES) != []


def test_the_root_commit_is_the_only_exemption():
    # GitHub writes "Initial commit" before any hook exists to refuse it, and
    # rewriting the root rewrites every hash after it.
    assert gate.subject_findings(commit("Initial commit", parents=0), TYPES) == []
    assert gate.subject_findings(commit("Initial commit", parents=1), TYPES) != []


@pytest.mark.parametrize(
    "subjects,bump",
    [
        (["fix: one", "docs: two"], "patch"),
        (["chore: one"], "patch"),
        (["feat: one", "fix: two"], "minor"),
        (["fix: one", "feat: two"], "minor"),
        (["feat!: one"], "major"),
        (["fix!: one"], "major"),
        ([], "patch"),
    ],
)
def test_the_bump_reads_the_types(subjects, bump):
    assert gate.bump_from([commit(s) for s in subjects]) == bump


def test_a_breaking_change_footer_counts_as_a_bang():
    # Conventional Commits 1.0.0 gives a break two spellings, and a pipeline
    # that read only the bang would compute a minor for a major.
    breaking = commit("fix: drop the field", body="BREAKING CHANGE: producer_id is required")
    assert gate.bump_from([breaking]) == "major"


@pytest.mark.parametrize(
    "previous,needed,expected",
    [
        # Below 1.0.0 there is no promise to break, so a break raises the minor.
        ("0.1.0", "major", "minor"),
        ("0.9.0", "major", "minor"),
        ("0.1.0", "minor", "minor"),
        ("0.1.0", "patch", "patch"),
        # At and above 1.0.0 a break is a major and nothing else will do.
        ("1.0.0", "major", "major"),
        ("2.4.1", "major", "major"),
    ],
)
def test_the_zero_major_rule(previous, needed, expected):
    assert gate.expected_bump(needed, previous) == expected


@pytest.mark.parametrize(
    "previous,proposed,bump",
    [
        ("0.1.0", "0.2.0", "minor"),
        ("0.1.0", "0.1.1", "patch"),
        ("0.9.0", "1.0.0", "major"),
        ("0.2.0", "0.2.0", None),
        ("0.2.0", "0.1.0", None),
    ],
)
def test_the_bump_between_two_tags(previous, proposed, bump):
    assert gate.bump_between(previous, proposed) == bump


def test_this_repository_passes_its_own_gate():
    assert gate.main(["--all"]) == 0
