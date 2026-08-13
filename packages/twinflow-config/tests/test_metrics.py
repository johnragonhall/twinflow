"""The metric registry envelope (E26b), and the rules of foundations 5.15.

The identifier space is a Phase 0 artifact even though the expressions that
compute the metrics arrive with the AI layer. These tests pin the property that
makes the split honest: a registry of entries with a null expression loads,
validates, and resolves a spec limit.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from twinflow.config import ConfigError, Severity, load_metrics, resolve_spec_limits

REPO_ROOT = Path(__file__).resolve().parents[3]
SHIPPED = REPO_ROOT / "profiles" / "starter_dc.metrics.yaml"
FIXTURES = Path(__file__).parent / "fixtures"


def test_the_shipped_registry_validates():
    registry, diagnostics = load_metrics(SHIPPED)
    assert registry["schema_version"] == "1.0"
    assert [d for d in diagnostics if d.severity is Severity.ERROR] == []


def test_every_shipped_entry_carries_a_null_expression():
    """The Phase 0 and Phase 6 split, asserted.

    The registry loads and resolves with no evaluator installed. When the AI
    layer lands, an expression stops being null and nothing else about the file
    changes shape.
    """
    registry, _ = load_metrics(SHIPPED)
    assert [m["id"] for m in registry["metrics"] if m["expression"] is not None] == []


@pytest.mark.parametrize(
    "metric_id,accepted",
    [
        ("twin.throughput.units_per_hour", True),
        ("twin.flow.cycle_time_seconds", True),
        ("a.b.c", True),
        ("twin.throughput", False),
        ("twin.throughput.units.per.hour", False),
        ("Twin.Throughput.Units", False),
        ("twin.throughput.Units", False),
        ("1twin.throughput.units", False),
        ("twin..units", False),
        ("twin.throughput.units-per-hour", False),
    ],
)
def test_metric_id_grammar_table(metric_id, accepted):
    """Parametrised over accepting and rejecting cases, as 5.15 asks."""
    from twinflow.config import METRIC_ID

    assert bool(METRIC_ID.match(metric_id)) is accepted


def test_a_duplicate_id_is_refused():
    with pytest.raises(ConfigError) as caught:
        load_metrics(FIXTURES / "metrics_duplicate_id.yaml")
    assert "TF-C150" in {d.code for d in caught.value.diagnostics}


def test_an_id_outside_the_grammar_is_refused_with_a_suggestion():
    with pytest.raises(ConfigError) as caught:
        load_metrics(FIXTURES / "metrics_bad_id.yaml")
    finding = next(d for d in caught.value.diagnostics if d.code == "TF-C153")
    assert finding.suggestion
    assert finding.line >= 1


def test_a_deprecated_metric_without_a_release_is_refused():
    with pytest.raises(ConfigError) as caught:
        load_metrics(FIXTURES / "metrics_deprecated_without_release.yaml")
    assert "TF-C155" in {d.code for d in caught.value.diagnostics}


def test_spec_limits_resolve_against_the_registry():
    registry, _ = load_metrics(SHIPPED)
    assert resolve_spec_limits({"twin.throughput.units_per_hour": {}}, registry, "x.yaml") == []


def test_spec_limits_dangling_metric_id_reports_nearest_candidate():
    """The suggestion behavior C5 asks for, pinned.

    A renamed metric fails here rather than at a demo.
    """
    registry, _ = load_metrics(SHIPPED)
    findings = resolve_spec_limits(
        {"twin.throughput.units_per_hr": {}}, registry, "spec_limits.yaml"
    )
    assert [f.code for f in findings] == ["TF-C103"]
    assert "twin.throughput.units_per_hour" in (findings[0].suggestion or "")
