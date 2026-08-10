"""The commit-message path check in the comment judge.

The judge reads a file and sends what it reads to an external CLI, so the path
it accepts decides what leaves the machine. A mistyped or hostile
`--commit-msg` argument must not turn a git hook into a way to post a private
key to a third party.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
JUDGE = REPO_ROOT / "scripts" / "hooks" / "comment_judge.py"


def _judge():
    spec = importlib.util.spec_from_file_location("comment_judge", JUDGE)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


judge = _judge()


def test_a_path_inside_the_allowed_root_is_accepted(tmp_path):
    message = tmp_path / "COMMIT_EDITMSG"
    message.write_text("feat(x): y\n", encoding="utf-8")
    assert judge.message_path_within(message, roots=[tmp_path]) == message.resolve()


def test_a_path_outside_every_allowed_root_is_refused(tmp_path):
    outside = tmp_path / "secret.txt"
    outside.write_text("private\n", encoding="utf-8")
    allowed = tmp_path / "repo"
    allowed.mkdir()

    with pytest.raises(ValueError, match="outside this repository"):
        judge.message_path_within(outside, roots=[allowed])


def test_a_traversal_segment_is_judged_by_where_it_lands(tmp_path):
    """Resolved before comparison, so `..` cannot walk out of the root."""
    allowed = tmp_path / "repo"
    allowed.mkdir()
    outside = tmp_path / "secret.txt"
    outside.write_text("private\n", encoding="utf-8")

    with pytest.raises(ValueError, match="outside this repository"):
        judge.message_path_within(allowed / ".." / "secret.txt", roots=[allowed])


def test_the_returned_path_is_rebuilt_from_the_root(tmp_path):
    """The value handed to open() carries nothing the caller wrote.

    The argument selects which file under the root is opened. It does not
    become the thing that is opened.
    """
    root = tmp_path / "repo"
    (root / "rebase-merge").mkdir(parents=True)
    message = root / "rebase-merge" / "message"
    message.write_text("feat(x): y\n", encoding="utf-8")

    rebuilt = judge.message_path_within(message, roots=[root])
    assert rebuilt == root / "rebase-merge" / "message"
    assert rebuilt.is_relative_to(root)


@pytest.mark.parametrize("name", ["COMMIT_EDITMSG", "MERGE_MSG", "SQUASH_MSG", "TAG_EDITMSG"])
def test_the_names_git_actually_writes_are_accepted(tmp_path, name):
    message = tmp_path / name
    message.write_text("feat(x): y\n", encoding="utf-8")
    assert judge.message_path_within(message, roots=[tmp_path]).name == name


def test_a_component_outside_the_name_pattern_is_refused(tmp_path):
    """A name nobody expects is a name nobody reviewed."""
    odd = tmp_path / "msg;rm -rf"
    odd.write_text("feat(x): y\n", encoding="utf-8")

    with pytest.raises(ValueError, match="plain file name"):
        judge.message_path_within(odd, roots=[tmp_path])


def test_a_directory_is_refused(tmp_path):
    with pytest.raises(ValueError, match="not a file"):
        judge.message_path_within(tmp_path, roots=[tmp_path])


def test_a_missing_file_is_refused(tmp_path):
    with pytest.raises(ValueError, match="not a file"):
        judge.message_path_within(tmp_path / "nope", roots=[tmp_path])


def test_a_refused_path_skips_the_judge_without_blocking_the_commit(tmp_path, capsys):
    """Nothing was read, so nothing leaked, and an author cannot act on a path
    their own tooling chose. Blocking there would be a dead end.
    """
    outside = tmp_path / "secret.txt"
    outside.write_text("private\n", encoding="utf-8")

    assert judge.judge_commit_message(outside) == 0
    assert "judge skipped" in capsys.readouterr().err


def test_the_repository_roots_resolve():
    """git hands the hook a file under the git directory, not the work tree."""
    roots = judge.git_roots()
    assert roots
    assert any(root.name == ".git" or root == REPO_ROOT for root in roots)
