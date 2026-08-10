"""Gate CFG-001: every shipped config validates, and every invalid fixture
produces a line-numbered error carrying a suggestion.

Both halves matter. The first is the obvious one. The second is the one that
decides whether anybody can use this: a validator that answers "invalid" has
told the author nothing they did not already know.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from twinflow.config import ConfigError, Severity, load_facility, nearest

REPO_ROOT = Path(__file__).resolve().parents[3]
PROFILES_DIR = REPO_ROOT / "profiles"
FIXTURES = Path(__file__).parent / "fixtures"


def _shipped_profiles() -> list[Path]:
    return sorted(PROFILES_DIR.glob("*.yaml"))


def test_there_is_at_least_one_shipped_profile():
    """Otherwise the gate below passes over an empty list."""
    assert _shipped_profiles()


@pytest.mark.parametrize("profile", _shipped_profiles(), ids=lambda p: p.name)
def test_every_shipped_profile_validates(profile):
    """The first half of CFG-001."""
    document, diagnostics = load_facility(profile)
    assert document["version"] == "1"
    assert [d for d in diagnostics if d.severity is Severity.ERROR] == []


@pytest.mark.parametrize(
    "fixture,code",
    [
        ("invalid_unknown_key.yaml", "TF-C012"),
        ("invalid_dangling_station.yaml", "TF-C101"),
        ("invalid_bad_enum.yaml", "TF-C013"),
        ("invalid_syntax.yaml", "TF-C001"),
    ],
)
def test_every_invalid_fixture_reports_its_code(fixture, code):
    with pytest.raises(ConfigError) as caught:
        load_facility(FIXTURES / fixture)
    assert code in {d.code for d in caught.value.diagnostics}


@pytest.mark.parametrize(
    "fixture",
    [
        "invalid_unknown_key.yaml",
        "invalid_dangling_station.yaml",
        "invalid_bad_enum.yaml",
        "invalid_syntax.yaml",
    ],
)
def test_every_error_carries_a_line_and_a_suggestion(fixture):
    """The second half of CFG-001, which is the half that gets skipped."""
    with pytest.raises(ConfigError) as caught:
        load_facility(FIXTURES / fixture)

    errors = [d for d in caught.value.diagnostics if d.severity is Severity.ERROR]
    assert errors
    for diagnostic in errors:
        assert diagnostic.line >= 1, diagnostic
        assert diagnostic.column >= 1, diagnostic
        assert diagnostic.suggestion, f"{diagnostic.code} has no suggestion"


def test_the_line_number_points_at_the_line_the_author_edited():
    """A diagnostic pointing at line 1 of every file is a diagnostic with no location."""
    with pytest.raises(ConfigError) as caught:
        load_facility(FIXTURES / "invalid_unknown_key.yaml")

    source = (FIXTURES / "invalid_unknown_key.yaml").read_text(encoding="utf-8").splitlines()
    unknown = next(d for d in caught.value.diagnostics if d.code == "TF-C012")
    assert "capacitty" in source[unknown.line - 1]


def test_a_misspelled_key_is_offered_the_key_it_meant():
    with pytest.raises(ConfigError) as caught:
        load_facility(FIXTURES / "invalid_unknown_key.yaml")

    unknown = next(d for d in caught.value.diagnostics if d.code == "TF-C012")
    assert "capacity" in (unknown.suggestion or "")


def test_a_dangling_reference_names_the_nearest_declared_candidate():
    with pytest.raises(ConfigError) as caught:
        load_facility(FIXTURES / "invalid_dangling_station.yaml")

    dangling = next(d for d in caught.value.diagnostics if d.code == "TF-C101")
    assert "sort-01" in (dangling.suggestion or "")
    assert "sort-01" in " ".join(dangling.notes)


def test_a_bad_enum_lists_the_values_that_are_allowed():
    with pytest.raises(ConfigError) as caught:
        load_facility(FIXTURES / "invalid_bad_enum.yaml")

    bad = next(d for d in caught.value.diagnostics if d.code == "TF-C013")
    assert "sortation" in (bad.suggestion or "")


def test_a_plausibility_finding_is_a_warning_and_does_not_block():
    """Stage 7 is warnings. A legal config that looks odd still loads."""
    document, diagnostics = load_facility(FIXTURES / "warns_zero_capacity.yaml")

    assert document is not None
    warnings = [d for d in diagnostics if d.severity is Severity.WARNING]
    assert [d.code for d in warnings] == ["TF-C301"]
    assert warnings[0].suggestion


def test_strict_mode_promotes_a_warning_to_a_failure():
    with pytest.raises(ConfigError):
        load_facility(FIXTURES / "warns_zero_capacity.yaml", strict=True)


def test_the_rendered_error_shows_the_offending_line_with_a_caret():
    """The human format of foundations 5.6, which is what an author reads."""
    with pytest.raises(ConfigError) as caught:
        load_facility(FIXTURES / "invalid_unknown_key.yaml")

    rendered = caught.value.rendered
    assert "error[TF-C012]" in rendered
    assert "--> " in rendered
    assert "^" in rendered
    assert "capacitty" in rendered


def test_all_findings_are_reported_together_not_one_at_a_time():
    """An author who fixes one error and reruns to find the next gives up."""
    with pytest.raises(ConfigError) as caught:
        load_facility(FIXTURES / "invalid_bad_enum.yaml")
    assert len(caught.value.diagnostics) >= 1


def test_nearest_declines_to_guess_when_nothing_is_close():
    """A wrong suggestion sends the author further from the fix than none."""
    assert nearest("capacitty", ["capacity", "type", "zone"]) == "capacity"
    assert nearest("zzzzzzzz", ["capacity", "type", "zone"]) is None
