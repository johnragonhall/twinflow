"""The local model path (ARCHITECTURE.md decision D10, ADR-0002).

The claim under test is that the schema guarantee does not weaken when the API
key is absent. Every assertion here is an attempt to obtain an answer that the
schema did not constrain: by dropping the constraint from the request, by
returning a document the constraint should have prevented, by returning prose,
or by having the daemon disappear. Each attempt has to end in a refusal.

No test here needs a running Ollama. The transport is injected, so the suite
drives a fake and asserts what reached the wire. The one test that genuinely
needs the daemon is marked `integration` and skips without it.
"""

from __future__ import annotations

import ast
import json
import sys
import urllib.error
import urllib.request
from collections.abc import Mapping
from pathlib import Path
from typing import Any

import pytest
from pydantic import ValidationError

from twinflow.agent import local_model
from twinflow.agent.local_model import (
    DEFAULT_OLLAMA_BASE_URL,
    ConstraintNotHonored,
    OllamaError,
    OllamaStructuredOutput,
    OllamaUnavailable,
    UrllibJsonTransport,
)
from twinflow.agent.tools import (
    QUERY_METRIC,
    MetricSelection,
    StructuredOutputAdapter,
    ToolCall,
    build_default_registry,
)

METRICS = "profiles/starter_dc.metrics.yaml"

VALID = {
    "metric": "twin.throughput.units_per_hour",
    "time_window": {"start_sim_ticks": 0, "end_sim_ticks": 10},
}

#: A document a constrained decoder should never have produced: it satisfies
#: the shape but not the governed grammar the pattern declares.
SHAPED_BUT_INVALID = {
    "metric": "NOT A METRIC ID",
    "time_window": {"start_sim_ticks": 0, "end_sim_ticks": 10},
}


class FakeTransport:
    """Records what reached the wire, and answers from a scripted list.

    A scripted answer is either a string, which becomes the assistant content
    verbatim, or an exception, which is raised in place of a response.
    """

    def __init__(self, answers: list[object]) -> None:
        self._answers = list(answers)
        self.urls: list[str] = []
        self.payloads: list[dict[str, Any]] = []
        self.timeouts: list[float] = []

    # `Mapping`, not `dict`, because that is what `JsonHttpTransport` accepts.
    # A fake that takes less than its port is a fake the port cannot stand in
    # for, and the suite would be asserting against a narrower contract than
    # the one the module publishes.
    def post_json(
        self, url: str, payload: Mapping[str, Any], *, timeout_s: float
    ) -> dict[str, Any]:
        self.urls.append(url)
        self.payloads.append(json.loads(json.dumps(payload)))
        self.timeouts.append(timeout_s)
        answer = self._answers[min(len(self.payloads) - 1, len(self._answers) - 1)]
        if isinstance(answer, Exception):
            raise answer
        return {"model": "fake", "done": True, "message": {"role": "assistant", "content": answer}}


def content(*documents: object) -> list[object]:
    return [json.dumps(document) for document in documents]


def adapter(answers: list[object], **kwargs: Any) -> tuple[OllamaStructuredOutput, FakeTransport]:
    transport = FakeTransport(answers)
    return OllamaStructuredOutput(transport=transport, **kwargs), transport


def prompt_only(_feedback: str | None) -> str:
    return "select the throughput metric over the first ten ticks"


# --------------------------------------------------------------------------
# The constraint reaches the wire, on every attempt
# --------------------------------------------------------------------------


def test_the_request_carries_the_models_json_schema_as_the_decode_constraint():
    """D10's whole claim. The schema is enforced at decode time, which is only
    true if it is in the request rather than in a prompt asking politely."""
    local, transport = adapter(content(VALID))

    local.structured(MetricSelection, prompt_only, max_retries=2)

    assert transport.payloads[0]["format"] == MetricSelection.model_json_schema()


def test_no_attempt_falls_back_to_an_unconstrained_call():
    """The failure this test exists to catch is a retry that drops the schema to
    get an answer. A guarantee that degrades on the hard case is not one."""
    local, transport = adapter(content(SHAPED_BUT_INVALID))

    with pytest.raises(ValidationError):
        local.structured(MetricSelection, prompt_only, max_retries=2)

    assert len(transport.payloads) == 3
    schema = MetricSelection.model_json_schema()
    assert [payload["format"] for payload in transport.payloads] == [schema, schema, schema]


def test_the_request_is_addressed_to_the_local_daemon_and_asks_for_one_document():
    local, transport = adapter(content(VALID))

    local.structured(MetricSelection, prompt_only, max_retries=0)

    assert DEFAULT_OLLAMA_BASE_URL == "http://localhost:11434"
    assert transport.urls == ["http://localhost:11434/api/chat"]
    assert transport.payloads[0]["stream"] is False


def test_the_request_pins_the_sampler_so_two_runs_of_one_prompt_agree():
    """Not determinism in the tape sense, which a model cannot give. It is the
    part this package controls: the sampler is pinned rather than left free."""
    local, transport = adapter(content(VALID), seed=7)

    local.structured(MetricSelection, prompt_only, max_retries=0)

    assert transport.payloads[0]["options"]["temperature"] == 0.0
    assert transport.payloads[0]["options"]["seed"] == 7


# --------------------------------------------------------------------------
# The answer is validated a second time
# --------------------------------------------------------------------------


def test_a_document_the_constraint_should_have_prevented_is_still_refused():
    """The second enforcement. A server that ignored `format`, or a build whose
    grammar does not carry `pattern`, produces exactly this document, and the
    only thing standing between it and the twin is this validation."""
    local, _transport = adapter(content(SHAPED_BUT_INVALID))

    with pytest.raises(ValidationError):
        local.structured(MetricSelection, prompt_only, max_retries=0)


def test_prose_instead_of_a_document_is_a_refusal_and_never_a_returned_string():
    local, _transport = adapter(["I think you want the throughput metric."])

    with pytest.raises(ConstraintNotHonored) as raised:
        local.structured(MetricSelection, prompt_only, max_retries=0)

    assert "format" in str(raised.value)


def test_an_empty_answer_is_a_refusal():
    local, _transport = adapter(["   "])

    with pytest.raises(ConstraintNotHonored):
        local.structured(MetricSelection, prompt_only, max_retries=0)


def test_a_repaired_answer_is_returned_and_the_error_travelled_back_to_the_model():
    """D9's validation-retry, kept on the local path so the two adapters behave
    the same way under a schema failure."""
    local, _transport = adapter(content(SHAPED_BUT_INVALID, VALID))
    seen: list[str | None] = []

    def emit(feedback: str | None) -> str:
        seen.append(feedback)
        return "select the throughput metric"

    out = local.structured(MetricSelection, emit, max_retries=2)

    assert isinstance(out, MetricSelection)
    assert out.metric == "twin.throughput.units_per_hour"
    assert seen[0] is None
    assert seen[1] is not None and "metric" in seen[1]


def test_prose_is_retried_with_feedback_rather_than_accepted():
    local, _transport = adapter(["not a document", *content(VALID)])
    seen: list[str | None] = []

    def emit(feedback: str | None) -> str:
        seen.append(feedback)
        return "select the throughput metric"

    assert isinstance(local.structured(MetricSelection, emit, max_retries=1), MetricSelection)
    assert seen[1] is not None and "JSON" in seen[1]


def test_it_raises_rather_than_returning_something_unvalidated_when_retries_run_out():
    local, _transport = adapter(content(SHAPED_BUT_INVALID))

    with pytest.raises(ValidationError):
        local.structured(MetricSelection, prompt_only, max_retries=1)


def test_a_negative_retry_budget_is_refused():
    local, _transport = adapter(content(VALID))

    with pytest.raises(ValueError, match="max_retries"):
        local.structured(MetricSelection, prompt_only, max_retries=-1)


# --------------------------------------------------------------------------
# A missing daemon is loud
# --------------------------------------------------------------------------


def test_a_daemon_that_is_not_running_raises_an_actionable_error():
    local, _transport = adapter([OllamaUnavailable("connection refused")])

    with pytest.raises(OllamaUnavailable):
        local.structured(MetricSelection, prompt_only, max_retries=2)


def test_a_missing_daemon_is_not_retried_and_is_never_swallowed():
    """Retrying a refused connection turns one clear failure into three, and
    catching it is how a silent fallback gets written by accident."""
    local, transport = adapter([OllamaUnavailable("connection refused")])

    with pytest.raises(OllamaUnavailable):
        local.structured(MetricSelection, prompt_only, max_retries=2)

    assert len(transport.payloads) == 1


def test_a_daemon_that_answers_with_an_http_error_is_not_retried():
    local, transport = adapter([OllamaError("HTTP 404: model not found")])

    with pytest.raises(OllamaError):
        local.structured(MetricSelection, prompt_only, max_retries=2)

    assert len(transport.payloads) == 1


def test_the_unavailable_error_tells_the_reader_what_to_run():
    transport = UrllibJsonTransport()

    # Port 1 on the loopback interface is not something a daemon listens on, so
    # this exercises the real refusal path without a network of any kind.
    with pytest.raises(OllamaUnavailable) as raised:
        transport.post_json("http://127.0.0.1:1/api/chat", {"model": "none"}, timeout_s=2.0)

    message = str(raised.value)
    assert "ollama serve" in message
    assert "127.0.0.1:1" in message


# --------------------------------------------------------------------------
# The seam, and the swap
# --------------------------------------------------------------------------


def test_it_fills_the_structured_output_seam():
    local, _transport = adapter(content(VALID))

    assert isinstance(local, StructuredOutputAdapter)


def test_the_registry_binds_a_call_through_the_local_adapter(repo_root):
    """The point of the seam: a tool call built by a local model is the same
    ToolCall a test fixture builds, so nothing downstream can tell them apart."""
    local, _transport = adapter(content(VALID))
    registry = build_default_registry(metrics_path=repo_root / METRICS)

    call = registry.bind_structured(QUERY_METRIC, prompt_only, adapter=local, max_retries=1)

    assert isinstance(call, ToolCall)
    # `ToolCall.args` is whichever model the tool declared, so naming the one
    # `query_metric` declares is part of the assertion rather than scaffolding
    # around it.
    assert isinstance(call.args, MetricSelection)
    assert call.args.metric == "twin.throughput.units_per_hour"


def test_an_emitter_written_for_the_pydantic_adapter_fails_loudly_here():
    """The two adapters ask their callback for different things, because only
    this one owns the model call. A quiet coercion would send the repr of a dict
    to the model as a prompt, so the mismatch is a TypeError naming both."""
    local, _transport = adapter(content(VALID))

    with pytest.raises(TypeError, match="prompt"):
        local.structured(MetricSelection, lambda _feedback: dict(VALID), max_retries=0)


def test_a_base_url_that_is_not_http_is_refused_at_construction():
    with pytest.raises(ValueError, match="http"):
        OllamaStructuredOutput(base_url="file:///etc/passwd", transport=FakeTransport([]))


def test_a_base_url_with_no_host_is_refused_at_construction():
    with pytest.raises(ValueError, match="host"):
        OllamaStructuredOutput(base_url="http://", transport=FakeTransport([]))


def test_a_trailing_slash_on_the_base_url_does_not_double_the_separator():
    local, transport = adapter(content(VALID), base_url="http://localhost:11434/")

    local.structured(MetricSelection, prompt_only, max_retries=0)

    assert transport.urls == ["http://localhost:11434/api/chat"]


# --------------------------------------------------------------------------
# The license argument this module exists to keep
# --------------------------------------------------------------------------


def test_the_local_path_costs_no_third_party_dependency():
    """ADR-0002 in one assertion. The reason this module was written rather
    than imported is that an HTTP client to localhost needs no certificate
    authority bundle, so it needs no certifi, so the run-time license allowlist
    stays as it is. An import of httpx or requests here would quietly undo that
    argument while every test above kept passing.

    pydantic is the one distribution this package already declares, and it is
    MIT, so it is named rather than discovered.
    """
    source = Path(twinflow_agent_local_model_path()).read_text(encoding="utf-8")
    tree = ast.parse(source)
    roots: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            roots.update(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module and node.level == 0:
            roots.add(node.module.split(".")[0])

    allowed = set(sys.stdlib_module_names) | {"twinflow", "pydantic"}
    outside = roots - allowed
    assert outside == set(), f"the local model path grew a third-party dependency: {outside}"


def twinflow_agent_local_model_path() -> Path:
    import twinflow.agent.local_model as module

    return Path(module.__file__)


# --------------------------------------------------------------------------
# The one test that needs the daemon
# --------------------------------------------------------------------------


@pytest.mark.integration
def test_a_running_ollama_answers_within_the_schema():
    """Skips unless the daemon is up. Everything above proves the wire format;
    this proves the daemon agrees with it, which no fake can establish."""
    local = OllamaStructuredOutput()
    try:
        out = local.structured(
            MetricSelection,
            lambda feedback: (
                "Select the metric twin.throughput.units_per_hour over sim ticks 0 to 10."
                if feedback is None
                else feedback
            ),
            max_retries=2,
        )
    except OllamaUnavailable as error:
        pytest.skip(f"no local Ollama daemon: {error}")
    assert out.metric == "twin.throughput.units_per_hour"


# ------------------------------------------------------- the base URL is loopback

# The module ships no certificate authority bundle, and ADR-0002 rests the whole
# no-third-party-dependency argument on that being safe because loopback
# verifies no certificate. A base URL naming another host posts the prompt and
# the schema off this machine over a connection nothing here can authenticate.


@pytest.mark.parametrize(
    "base_url",
    [
        "http://169.254.169.254",
        "http://10.0.0.5:11434",
        "https://attacker.example",
        "http://localhost@evil.example",
        "http://evil.example#localhost",
        "http://127.0.0.1.evil.example",
    ],
)
def test_a_base_url_off_this_machine_is_refused(base_url: str):
    with pytest.raises(ValueError, match="loopback"):
        local_model._chat_url(base_url)


@pytest.mark.parametrize(
    "base_url",
    [
        "http://127.0.0.1:11434",
        "http://localhost:11434",
        "http://[::1]:11434",
        "http://127.0.0.2:11434",
    ],
)
def test_a_loopback_base_url_is_accepted(base_url: str):
    """The control. A check that refused every host would pass the six cases
    above while making the local path unreachable."""
    assert local_model._chat_url(base_url).endswith("/api/chat")


def test_the_scheme_refusal_still_stands():
    """`urlopen` opens file: and ftp:, so the scheme is checked as well as the
    host. Neither check subsumes the other: `file:///etc/passwd` names no host
    and `http://evil.example` names a legal scheme."""
    for base_url in ("file:///etc/passwd", "ftp://127.0.0.1/x"):
        with pytest.raises(ValueError):
            local_model._chat_url(base_url)


def test_a_redirect_off_loopback_is_refused():
    """The host check reads the URL a caller configured. A redirect is a second
    URL, and the stdlib handler follows one to ftp as readily as to https."""
    handler = local_model._RefuseRedirect()
    request = urllib.request.Request("http://127.0.0.1:11434/api/chat")

    with pytest.raises(urllib.error.HTTPError, match="refused"):
        handler.redirect_request(
            request, None, 302, "Found", {}, "http://169.254.169.254/latest/meta-data"
        )


def test_the_transport_opener_does_not_follow_redirects():
    """The refusal above only matters while the transport uses this opener."""
    assert any(
        # `OpenerDirector.handlers` is set in its constructor and typeshed does
        # not declare it, so the attribute is real and only the stub is short.
        isinstance(handler, local_model._RefuseRedirect)
        for handler in local_model._OPENER.handlers  # ty: ignore[unresolved-attribute]
    )
