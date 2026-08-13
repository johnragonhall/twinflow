"""Installed hooks against the tracked ones, WORKSPACE-2.

scripts/hooks/install.sh copies the hooks into .git/hooks rather than pointing
core.hooksPath at them, so that a machine-local hook already sitting there keeps
working. The cost is that the copy goes stale the moment a tracked hook changes,
and a stale copy fails silently: the commit-msg hook runs, prints nothing about
the check it no longer carries, and the commit lands.

That is how a `fix` commit reaches main with no test. REG-001 is wired into
scripts/hooks/commit-msg in blocking `--staged` form, and an installed copy
predating that wiring never runs it. The author is never offered the trailer the
gate exists to ask for, and the defect surfaces later against history, where the
only remedies left are a rewrite or an exemption.

The comparison asks whether every line of the tracked hook still appears, in
order, in the installed one. Equality is too strict: the installer deliberately
supports a machine-local hook, so a block inserted anywhere in the copy is
allowed. Containment is too strict as well, because an inserted block splits the
tracked text and a copy carrying every check would read as stale. Only a copy
that has lost a line is a finding.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
TRACKED = REPO_ROOT / "scripts" / "hooks"

#: Not a hook. It is what installs them.
INSTALLER = "install.sh"


def _hooks_dir() -> Path:
    result = subprocess.run(
        ["git", "rev-parse", "--git-path", "hooks"],  # noqa: S607
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=True,
    )
    return (REPO_ROOT / result.stdout.strip()).resolve()


def _normalize(text: str) -> str:
    """Line endings only. A CRLF checkout is not a stale hook."""
    return text.replace("\r\n", "\n")


def is_current(tracked: str, installed: str) -> bool:
    """True when every line of the tracked hook survives, in order, in the copy.

    A subsequence rather than a substring, so a machine-local block inserted
    into the installed hook stays legal while a dropped check does not.
    """
    remaining = iter(_normalize(installed).splitlines())
    return all(
        any(line == candidate for candidate in remaining)
        for line in _normalize(tracked).splitlines()
    )


def _tracked_hooks() -> list[Path]:
    return sorted(p for p in TRACKED.iterdir() if p.is_file() and p.name != INSTALLER)


def test_every_tracked_hook_is_installed_and_current():
    """A stale copy is reported here rather than by the history it lets through."""
    hooks_dir = _hooks_dir()
    tracked = _tracked_hooks()
    assert tracked, "scripts/hooks carries no hooks, so this check guards nothing"

    installed = [hook for hook in tracked if (hooks_dir / hook.name).is_file()]
    if not installed:
        pytest.skip(
            f"no tracked hook is installed in {hooks_dir}, which is a fresh clone or CI "
            f"rather than a stale checkout. Run: sh scripts/hooks/install.sh"
        )

    stale = [
        hook.name
        for hook in installed
        if not is_current(
            hook.read_text(encoding="utf-8"),
            (hooks_dir / hook.name).read_text(encoding="utf-8"),
        )
    ]
    assert stale == [], (
        f"{len(stale)} installed hook(s) no longer carry what scripts/hooks says: "
        f"{', '.join(stale)}. Every check added to a tracked hook since the last install "
        f"is silently not running. Fix: sh scripts/hooks/install.sh"
    )


def test_the_comparison_catches_a_hook_that_lost_a_check():
    """The falsifier. Without it the check above passes on any repository."""
    tracked = "#!/bin/sh\nrun the prose gate\nrun the regression gate\n"
    assert is_current(tracked, tracked)

    # A block inserted after the shebang, which is where a machine-local hook
    # puts itself, keeps every tracked line.
    local = "#!/bin/sh\nlocal preamble\nrun the prose gate\nrun the regression gate\n"
    assert is_current(tracked, local)
    assert is_current(tracked, f"{tracked}an appended local step\n")

    # A dropped check is the finding.
    assert not is_current(tracked, "#!/bin/sh\nrun the prose gate\n")

    # So is a reorder, which no longer runs the checks in the order they carry.
    assert not is_current(tracked, "#!/bin/sh\nrun the regression gate\nrun the prose gate\n")


def test_line_endings_alone_are_not_staleness():
    assert is_current("#!/bin/sh\ncheck\n", "#!/bin/sh\r\ncheck\r\n")
