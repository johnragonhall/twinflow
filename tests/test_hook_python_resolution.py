"""One interpreter resolution for every hook gate.

`scripts/hooks/resolve-python.sh` exists because both hooks need to pick a
Python interpreter and two copies of that choice drift. It also exists because
the choice is measured: the project virtualenv starts in roughly a fifth of the
time `uv run` takes, and a commit runs six gates through it.

The assertions here are about the shape of the resolution rather than about
timing. A wall-clock assertion in the unit tier fails on a loaded runner and
teaches people to re-run, which doctrine D-13 refuses. The number that
justifies the file lives in its header, next to the measurement that produced
it.
"""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
HOOKS = REPO_ROOT / "scripts" / "hooks"
RESOLVER = HOOKS / "resolve-python.sh"
SOURCING_HOOKS = (HOOKS / "pre-commit", HOOKS / "commit-msg")


def test_the_resolver_exists_and_is_shell():
    assert RESOLVER.is_file()
    assert RESOLVER.read_text(encoding="utf-8").startswith("#!/bin/sh")


@pytest.mark.parametrize("hook", SOURCING_HOOKS, ids=lambda p: p.name)
def test_every_hook_sources_the_resolver(hook):
    text = hook.read_text(encoding="utf-8")
    assert ". scripts/hooks/resolve-python.sh" in text, (
        f"{hook.name} picks an interpreter without the shared resolver"
    )


@pytest.mark.parametrize("hook", SOURCING_HOOKS, ids=lambda p: p.name)
def test_no_hook_keeps_its_own_fallback_chain(hook):
    """Regression. The resolution lived in five places and drifted.

    Each site had its own `command -v uv` chain, and they disagreed about
    whether to pass `--with pyyaml`. A gate moved between hooks would then get
    an interpreter missing the dependency it imports.
    """
    text = hook.read_text(encoding="utf-8")
    assert "uv run --quiet --no-project" not in text, (
        f"{hook.name} carries its own uv invocation instead of using HOOK_PY"
    )


def test_the_resolver_prefers_the_project_virtualenv():
    """The measured choice, checked against a real checkout.

    Skipped rather than faked when no virtualenv is present, because the
    assertion is about which of two real options wins.
    """
    venvs = [REPO_ROOT / ".venv" / "bin" / "python", REPO_ROOT / ".venv" / "Scripts" / "python.exe"]
    if not any(v.exists() for v in venvs):
        pytest.skip("no virtualenv in this checkout, so there is nothing to prefer")

    shell = shutil.which("sh") or shutil.which("bash")
    if not shell:
        pytest.skip("no POSIX shell available to source the resolver")

    result = subprocess.run(
        [shell, "-c", ". scripts/hooks/resolve-python.sh; echo $HOOK_PY; echo $HOOK_PY_YAML"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr
    chosen = [line.strip() for line in result.stdout.splitlines() if line.strip()]
    assert len(chosen) == 2, f"the resolver set {len(chosen)} of its two variables"
    for value in chosen:
        assert ".venv" in value, f"the resolver picked {value!r} over the virtualenv"


def test_the_virtualenv_carries_what_the_yaml_gates_import():
    """The premise the resolver's fast path rests on.

    If the virtualenv stops carrying PyYAML the resolver falls back for
    HOOK_PY_YAML, which is correct but silently slower. This says so.
    """
    venvs = [REPO_ROOT / ".venv" / "bin" / "python", REPO_ROOT / ".venv" / "Scripts" / "python.exe"]
    interpreter = next((v for v in venvs if v.exists()), None)
    if interpreter is None:
        pytest.skip("no virtualenv in this checkout")

    result = subprocess.run([str(interpreter), "-c", "import yaml"], capture_output=True, text=True)
    assert result.returncode == 0, "the virtualenv cannot run the prose and spelling gates"


def test_the_resolver_names_the_measurement_that_picked_the_order():
    # A performance decision with no number in it is a preference. The header
    # carries the medians, and this keeps them from being edited out.
    text = RESOLVER.read_text(encoding="utf-8")
    assert "ms" in text
    assert "medians of five" in text
