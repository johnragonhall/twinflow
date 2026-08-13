"""RFC 9457 problem documents, and the `TF-Axxx` codes this surface answers with.

Foundations section 5.13 fixes the shape: `type` points at
`https://<pages>/errors/TF-Axxx` and the `code` field carries the same code, so
a client branches on a stable token rather than on prose it has to parse. The
duplication between `type` and `code` is in the design on purpose. A client that
only ever sees the URI would have to string-split it to act on the error.

The codes live here rather than at each raise site because two routes answering
the same condition with two codes is exactly the drift a client cannot defend
against, and because the published error pages are generated from one list.
"""

from __future__ import annotations

from dataclasses import dataclass

#: RFC 9457 section 3. A problem document is not `application/json`, and a
#: client that content-negotiates on the media type needs the distinction.
PROBLEM_MEDIA_TYPE = "application/problem+json"

#: Where the published explanation of each code lives. Overridable at
#: `create_app`, because the docs site host is a deployment fact rather than an
#: API fact, and hard-coding it here would put a 404 in every error document
#: served from a fork.
DEFAULT_PROBLEM_BASE_URL = "https://twinflow.github.io/twinflow/errors/"


@dataclass(frozen=True)
class Problem:
    """One refusal: its code, its status, its title, and what a client does now.

    `title` is the same for every occurrence of a code and `detail` names the
    particular thing that went wrong, which is the split RFC 9457 section 3.1.1
    asks for. A title that varied per occurrence would make the code useless
    for grouping.
    """

    code: str
    status: int
    title: str

    def raised(self, detail: str) -> ProblemError:
        return ProblemError(self, detail)


class ProblemError(Exception):
    """A refusal on its way to the client as a problem document."""

    def __init__(self, problem: Problem, detail: str) -> None:
        super().__init__(f"{problem.code}: {detail}")
        self.problem = problem
        self.detail = detail


def problem_document(problem: Problem, detail: str, *, base_url: str) -> dict[str, object]:
    """The document body, with the code in both of the places section 5.13 puts it."""
    return {
        "type": f"{base_url.rstrip('/')}/{problem.code}",
        "title": problem.title,
        "status": problem.status,
        "detail": detail,
        "code": problem.code,
    }


#: Foundations section 4 names this one: a router the build did not install
#: answers 404 with `TF-A020` rather than an empty collection, because an empty
#: `/findings` reads as "this run is clean".
ROUTER_NOT_INSTALLED = Problem(
    code="TF-A020",
    status=404,
    title="Router not installed",
)

UNKNOWN_RUN = Problem(
    code="TF-A040",
    status=404,
    title="No such run",
)

UNKNOWN_METRIC = Problem(
    code="TF-A041",
    status=404,
    title="No such metric",
)

#: Distinct from UNKNOWN_METRIC on purpose. A registered metric with no
#: expression is a promise this project has made and not yet kept, and
#: answering 404 for it would tell a client to stop asking.
METRIC_EXPRESSION_PENDING = Problem(
    code="TF-A042",
    status=501,
    title="Metric registered but not evaluable",
)

MALFORMED_CURSOR = Problem(
    code="TF-A043",
    status=400,
    title="Malformed cursor",
)

#: Foundations section 5.13 says offset pagination is deliberately not offered.
#: Accepting the parameter and ignoring it would silently serve the first page
#: to a client that believes it asked for the fourth.
OFFSET_NOT_OFFERED = Problem(
    code="TF-A044",
    status=400,
    title="Offset pagination is not offered",
)

AUTONOMY_TIER_REFUSES_APPLY = Problem(
    code="TF-A045",
    status=403,
    title="Autonomy tier does not carry config:apply",
)

GUARDRAIL_EVALUATOR_ABSENT = Problem(
    code="TF-A046",
    status=501,
    title="Guardrail evaluator not built",
)

NOT_READY = Problem(
    code="TF-A047",
    status=503,
    title="Not ready",
)

#: Every code this surface can answer with, sorted, so the published error pages
#: and the router cannot disagree about which codes exist.
PROBLEMS: tuple[Problem, ...] = tuple(
    sorted(
        (
            ROUTER_NOT_INSTALLED,
            UNKNOWN_RUN,
            UNKNOWN_METRIC,
            METRIC_EXPRESSION_PENDING,
            MALFORMED_CURSOR,
            OFFSET_NOT_OFFERED,
            AUTONOMY_TIER_REFUSES_APPLY,
            GUARDRAIL_EVALUATOR_ABSENT,
            NOT_READY,
        ),
        key=lambda problem: problem.code,
    )
)
