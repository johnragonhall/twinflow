"""DASH-02, the transliterated em dash.

Repository policy gates live in scripts/checks and are not part of any
distribution, so their tests live here rather than inside a package.

This rule sits in code rather than in docs/style/banned-phrases.yml because the
three characters it matches are legitimate in three common shapes: a command
separator, a comment banner, and an option cluster. A regex rule flagging
`git diff -- path` is a rule every contributor escapes, and an escaped rule
protects nothing. What these cases pin is the line between the shapes.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
GATE = REPO_ROOT / "scripts" / "checks" / "prose-gate.py"


def _load():
    spec = importlib.util.spec_from_file_location("prose_gate", GATE)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


_GATE = _load()


def findings(text: str, path: str = "sample.py") -> list[str]:
    document = _GATE.Document(path, text)
    collected: list[tuple] = []
    _GATE.check_prose_double_dash(document, collected)
    return [f"{item[0]}:{item[1]} {item[2]}" for item in collected]


@pytest.mark.parametrize(
    "line",
    [
        "# published algorithms -- BLAKE2b and PCG64DXSM -- are frozen",
        "a sentence -- with a dash standing in for punctuation",
        "The registry declares every gate -- and nothing else.",
    ],
)
def test_a_dash_between_words_is_reported(line):
    assert findings(line), line


@pytest.mark.parametrize(
    "line",
    [
        "git diff --cached -- path/to/file",
        "cargo clippy --all-targets -- -D warnings",
        "uv run pytest -m property -- tests/",
        "    # -- loading -----------------------------------------------",
        "shellcheck $files -- extra",
        "a rule -------- of many dashes",
        "an option cluster --all on its own",
    ],
)
def test_the_three_characters_doing_a_job_are_left_alone(line):
    assert findings(line) == [], line


def test_the_escape_needs_a_reason():
    excused = "a sentence -- with a dash  docs-lint-ok DASH-02 quoted from upstream"
    assert findings(excused) == []
    bare = "a sentence -- with a dash  docs-lint-ok DASH-02"
    assert findings(bare), "an escape with no reason is not an escape"


def test_the_gate_source_states_the_pattern_and_is_exempt():
    """A file that states a rule necessarily contains what the rule matches."""
    line = "a sentence -- with a dash"
    assert findings(line, path=_GATE.SELF_PATH) == []
    assert findings(line, path="docs/DOCUMENTATION-STANDARD.md") == []


def test_the_repository_is_clean_under_this_rule():
    """The rule ships green, so its first failure is a new violation."""
    import subprocess

    done = subprocess.run(  # noqa: S603
        ["git", "ls-files"],  # noqa: S607
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    hits = []
    for name in done.stdout.split():
        path = REPO_ROOT / name
        if path.suffix not in _GATE.TEXT_EXT or not path.is_file():
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue
        hits += findings(text, path=Path(name).as_posix())
    assert hits == [], "\n".join(hits)
