"""The release gate (REL-001).

The bump policy is what these pin. It reads the Keep a Changelog headings and
decides the smallest version bump that is honest for them, which is the rule a
release manager would otherwise apply from memory at the moment they are most
in a hurry.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
GATE = REPO_ROOT / "scripts" / "checks" / "release-gate.py"


def _gate():
    spec = importlib.util.spec_from_file_location("release_gate", GATE)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


gate = _gate()


@pytest.mark.parametrize(
    "headings,bump",
    [
        ({"Fixed"}, "patch"),
        ({"Security"}, "patch"),
        ({"Changed"}, "patch"),
        ({"Added"}, "minor"),
        ({"Deprecated"}, "minor"),
        ({"Added", "Fixed"}, "minor"),
        # Removing a published symbol, a schema field, or a config key breaks
        # whoever depended on it, whatever else the release also carries.
        ({"Removed"}, "major"),
        ({"Removed", "Added", "Fixed"}, "major"),
        (set(), "patch"),
    ],
)
def test_the_bump_policy_reads_the_headings(headings, bump):
    assert gate.required_bump(headings) == bump


@pytest.mark.parametrize(
    "previous,proposed,bump",
    [
        ("1.2.3", "2.0.0", "major"),
        ("1.2.3", "1.3.0", "minor"),
        ("1.2.3", "1.2.4", "patch"),
        ("1.2.3", "1.2.3", None),
        ("1.2.3", "1.2.2", None),
        ("1.2.3", "not-a-version", None),
    ],
)
def test_the_actual_bump_is_read_from_the_two_versions(previous, proposed, bump):
    assert gate.actual_bump(previous, proposed) == bump


def test_a_patch_carrying_a_removal_is_refused():
    """The case the policy exists for.

    A removal shipped as a patch reaches every consumer that pinned a caret
    range, which is the whole point of semantic versioning.
    """
    assert gate.required_bump({"Removed"}) == "major"
    assert gate._RANK[gate.actual_bump("1.2.3", "1.2.4")] < gate._RANK["major"]


def test_the_current_unreleased_section_passes():
    assert gate.main([]) == 0


def test_a_tag_with_no_changelog_section_is_refused():
    assert gate.main(["99.0.0"]) == 1


def test_known_headings_are_the_keep_a_changelog_six():
    assert {
        "Added",
        "Changed",
        "Deprecated",
        "Removed",
        "Fixed",
        "Security",
    } == gate.KNOWN_HEADINGS
