"""The metric registry of foundations section 5.13, addressed without a request.

`create_api` receives a registry that is already built, so the constructor's own
refusal is unreachable through any route: by the time a request arrives, a
duplicate id has already been refused or already been resolved to whichever
definition was declared last. The route tests in `test_app.py` cover what a
client sees; this file covers what the registry refuses to become.
"""

from __future__ import annotations

import pytest

from twinflow.api import MetricDefinition, MetricRegistry


def test_one_id_declared_twice_is_refused_rather_than_resolved_to_the_last_one():
    """Two definitions of one id make the answer depend on declaration order.

    The body carries an ETag, so silently keeping the last one would also give
    two deployments of one configuration two different hashes for one metric,
    and a client caching on the ETag would see them disagree.
    """
    with pytest.raises(ValueError, match="registered twice"):
        MetricRegistry(
            (
                MetricDefinition(metric_id="oee", title="Overall equipment", unit="ratio"),
                MetricDefinition(metric_id="oee", title="Overall equipment", unit="percent"),
            )
        )


def test_two_distinct_ids_are_both_registered_and_answered_in_sorted_order():
    """The control, and the ordering claim the class docstring makes. A
    constructor that refused every second definition would pass the test above
    and hold a registry of one."""
    registry = MetricRegistry(
        (
            MetricDefinition(metric_id="oee", title="Overall equipment", unit="ratio"),
            MetricDefinition(metric_id="cycle_time", title="Cycle time", unit="s"),
        )
    )

    assert registry.ids() == ("cycle_time", "oee")
    assert len(registry) == 2
    assert registry.get("oee") is not None
    assert registry.get("no-such-metric") is None


def test_a_definition_with_an_expression_is_the_evaluable_one():
    """`evaluable` is the fact the route turns into two different 501 details,
    so it is a property of the definition rather than a check at the seam."""
    assert not MetricDefinition(metric_id="oee", title="t", unit="ratio").evaluable
    assert MetricDefinition(
        metric_id="oee", title="t", unit="ratio", expression="good / total"
    ).evaluable
