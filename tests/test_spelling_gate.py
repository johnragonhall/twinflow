"""The spelling gate.

Repository policy gates live in scripts/checks and are not part of any
distribution, so their tests live here rather than inside a package.

Every case comes from the `selftest` block of docs/style/spelling.yml. That is
not indirection for its own sake: a wrong spelling written into this file would
be a wrong spelling in a file the gate reads for findings, so the gate would
fail on its own test suite. One file holds the rules and the words that prove
them, and it is the one file the gate skips.

What these pin is the half a word list cannot state. A rule has to fire on the
variant and leave the correctly spelled word that shares its first eight letters
alone: hypothesis, specialist, cancellation, and totally are each one careless
stem rule away from being rewritten into something that is not a word, and a
rewrite like that is invisible in review because the diff looks like every
other spelling fix.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
GATE = REPO_ROOT / "scripts" / "checks" / "spelling-gate.py"
RULES = REPO_ROOT / "docs" / "style" / "spelling.yml"


def _load():
    spec = importlib.util.spec_from_file_location("spelling_gate", GATE)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


_GATE = _load()
_RULES, _SKIP, _EXPECT = _GATE.load_rules(RULES)

FIRES = sorted((_EXPECT.get("fires") or {}).items())
PASSES = sorted(_EXPECT.get("passes") or [])
#: One word the rules catch, for the cases that need any wrong spelling at all.
SAMPLE = FIRES[0][0] if FIRES else ""
SECOND = FIRES[1][0] if len(FIRES) > 1 else ""


def findings(text: str) -> list[str]:
    return _GATE.check_text(text, _RULES, "sample")


def test_the_rule_file_carries_cases_to_run():
    """An empty expectations block would make every test below vacuous."""
    assert len(FIRES) >= 20
    assert len(PASSES) >= 20


@pytest.mark.parametrize(("wrong", "right"), FIRES, ids=[pair[1] for pair in FIRES])
def test_a_wrong_spelling_is_reported_with_the_right_one(wrong, right):
    reported = findings(f"one line saying {wrong} here")
    assert reported, f"nothing fired on {wrong}"
    assert right in reported[0], reported[0]


@pytest.mark.parametrize("word", PASSES)
def test_a_correct_word_is_left_alone(word):
    assert findings(f"one line saying {word} here") == []


def test_the_suggestion_keeps_the_suffix():
    """A suffixed form suggests the suffixed correction.

    A suggestion that drops the suffix reads as a different word and sends the
    author to fix something they did not write.
    """
    suffixed = [(wrong, right) for wrong, right in FIRES if wrong.endswith(("ed", "es", "ing"))]
    assert suffixed, "the rule file lists no suffixed case"
    for wrong, right in suffixed:
        reported = findings(f"the {wrong} form")
        assert f"'{right}'" in reported[0], reported[0]


def test_case_is_reported_as_written():
    reported = findings(f"{SAMPLE.capitalize()} at the start of a line")
    assert f"'{SAMPLE.capitalize()}'" in reported[0]


def test_the_escape_needs_a_reason():
    excused = findings(f"a {SAMPLE} here  spell-ok {SAMPLE} the name is somebody else's")
    assert excused == []
    # A bare token with no reason does not parse as an escape, so the word is
    # still reported. A gate that is easy to silence is not a gate.
    assert findings(f"a {SAMPLE} here  spell-ok {SAMPLE}")


def test_one_escape_carries_a_list_of_words():
    """A sentence naming two variants needs two exemptions.

    Two tokens on one line cannot be parsed, because the reason of the first
    swallows the rest, so one token carries a comma-separated list.
    """
    line = f"{SAMPLE} and {SECOND}  spell-ok {SAMPLE},{SECOND} this line names them"
    assert findings(line) == []


def test_one_escape_does_not_silence_the_rest_of_the_line():
    reported = findings(f"{SAMPLE} and {SECOND}  spell-ok {SAMPLE} only this one is theirs")
    assert len(reported) == 1
    assert SECOND in reported[0]


def test_the_selftest_passes():
    """The gate ships its own proof, and this asserts the proof runs green."""
    assert _GATE.selftest(_RULES, _EXPECT) == 0


def test_the_files_that_may_hold_a_wrong_spelling_are_skipped():
    assert "docs/style/spelling.yml" in _SKIP
    # The legal files carry verbatim text that a byte comparison depends on.
    assert "LICENSE" in _SKIP
    assert "NOTICE" in _SKIP


def test_a_path_outside_the_repository_is_refused(tmp_path):
    """The gate reads what it is given, so what it is given is confined.

    Same treatment `comment_judge.py` gives its message file. A checker that
    opens whatever an argument names is a checker that reads whatever the
    caller wants read, and this one runs from a git hook where the argument
    arrives from the tool rather than from a person.
    """
    outside = tmp_path / "elsewhere.txt"
    outside.write_text("any text\n", encoding="utf-8")
    with pytest.raises(ValueError, match="outside this repository"):
        _GATE.path_within(str(outside), roots=[REPO_ROOT])


def test_a_symlink_is_judged_by_where_it_lands(tmp_path):
    target = tmp_path / "target.txt"
    target.write_text("any text\n", encoding="utf-8")
    link = REPO_ROOT / "tests" / "link-under-test.txt"
    try:
        link.symlink_to(target)
    except (OSError, NotImplementedError):
        pytest.skip("this platform does not allow the test to create a symlink")
    try:
        with pytest.raises(ValueError, match="outside this repository"):
            _GATE.path_within(str(link), roots=[REPO_ROOT])
    finally:
        link.unlink()


def test_a_traversal_segment_is_refused(tmp_path):
    outside = tmp_path / "elsewhere.txt"
    outside.write_text("any text\n", encoding="utf-8")
    spelled_through_the_root = REPO_ROOT / ".." / outside.name
    with pytest.raises(ValueError):
        _GATE.path_within(str(spelled_through_the_root), roots=[REPO_ROOT])


def test_a_file_in_the_repository_is_accepted():
    accepted = _GATE.path_within(str(REPO_ROOT / "CONTRIBUTING.md"), roots=[REPO_ROOT])
    assert accepted == REPO_ROOT / "CONTRIBUTING.md"


def test_a_directory_and_a_missing_file_are_refused():
    with pytest.raises(ValueError, match="is not a file"):
        _GATE.path_within(str(REPO_ROOT / "tests"), roots=[REPO_ROOT])
    with pytest.raises(ValueError, match="is not a file"):
        _GATE.path_within(str(REPO_ROOT / "no-such-file.md"), roots=[REPO_ROOT])
