"""Fixtures shared by this package's tests."""

from __future__ import annotations

from pathlib import Path

import pytest


@pytest.fixture(scope="session")
def repo_root() -> Path:
    """The workspace root, so a test can read profiles/ without a relative path.

    Derived from this file rather than from the working directory: pytest is run
    from the root by the justfile and from the package directory by an editor,
    and a relative path works in exactly one of those.
    """
    return Path(__file__).resolve().parents[3]
