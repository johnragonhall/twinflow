"""The metric registry behind `/api/v1/metrics/{metric_id}`.

Foundations section 5.13 asks this route to make a distinction most APIs
collapse: `404` for an unregistered id, and `501` with a problem document naming
E26b while the expression is null. The two are different facts. A `404` tells a
client the metric does not exist and to stop asking. A `501` tells it the metric
is registered, its name is stable, and the expression language that evaluates it
is a later requirement.

Collapsing them would also hide the registry's own defect: a metric with no
expression is a promise this project has published and not yet kept, and it
should be visible from the outside rather than only in a table.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass

#: The requirement that supplies the expression language. Named in the problem
#: document so a client reading the error can find the plan rather than guess.
EXPRESSION_REQUIREMENT = "E26b"


@dataclass(frozen=True)
class MetricDefinition:
    """One registered metric. `expression` is null until E26b lands."""

    metric_id: str
    title: str
    unit: str
    expression: str | None = None

    @property
    def evaluable(self) -> bool:
        return self.expression is not None


class MetricRegistry:
    """The registered metrics, addressed by id.

    A mapping rather than a list, and sorted on the way out, because
    `/api/v1/metrics` would otherwise answer in whatever order the definitions
    were declared and two deployments would disagree on a response body that
    carries an ETag.
    """

    def __init__(self, definitions: Iterable[MetricDefinition] = ()) -> None:
        self._by_id: dict[str, MetricDefinition] = {}
        for definition in definitions:
            if definition.metric_id in self._by_id:
                raise ValueError(
                    f"metric {definition.metric_id!r} is registered twice, and a reader asking "
                    f"for it would get whichever definition was declared last"
                )
            self._by_id[definition.metric_id] = definition

    def get(self, metric_id: str) -> MetricDefinition | None:
        return self._by_id.get(metric_id)

    def ids(self) -> tuple[str, ...]:
        return tuple(sorted(self._by_id))

    def __len__(self) -> int:
        return len(self._by_id)
