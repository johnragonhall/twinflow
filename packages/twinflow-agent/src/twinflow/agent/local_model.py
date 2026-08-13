"""The local model path: constrained decoding through Ollama (D10, ADR-0002).

ARCHITECTURE.md decision D10 asks that the demo run with no API key and no cloud
account, and that the accuracy stack not degrade when the key is absent:
"constrained decoding gives the same schema guarantee locally that hosted
providers give through their structured-output APIs". This module is that path.
It fills the `StructuredOutputAdapter` seam of `twinflow.agent.tools`, so a
planner swaps the shipped pydantic adapter for a real local model by changing a
constructor argument and no tool changes at all.

Why this is written here rather than imported
---------------------------------------------
ADR-0002 records the decision and its evidence. In one paragraph: decision D9
names Pydantic AI, the run-time license allowlist in CONTRIBUTING.md refuses
MPL-2.0 shipped at run time, and Pydantic AI reaches `certifi`, which is
MPL-2.0, through httpx. So the framework cannot be adopted without either
weakening the allowlist or vendoring around it.

The thing that makes writing it cheap rather than heroic: Ollama listens on the
loopback interface, and a request to loopback needs no certificate authority
bundle, because there is no certificate to verify. That removes the reason httpx
carries certifi in the first place. `urllib.request` from the standard library
posts JSON to `http://localhost:11434` and reads the answer, so the local path
costs zero third-party distributions and the allowlist stays as it is.
`test_the_local_path_costs_no_third_party_dependency` asserts that no import
here leaves the standard library, which is what keeps that argument true rather
than merely stated.

Two enforcements, not one
-------------------------
Ollama's `/api/chat` takes a `format` parameter holding a JSON Schema, and the
sampler is constrained to that schema at decode time. That is the first
enforcement, and it is the one D10 asks for. The answer is then validated
against the same pydantic model, which is the second. The second exists because
the first is a promise made by a server this package does not control: an older
build, a proxy, or a grammar compiler that drops `pattern` all produce a
document that is shaped right and still wrong. `SHAPED_BUT_INVALID` in the test
module is exactly that document.

What this module refuses to do
------------------------------
There is no path that answers without the schema in the request, and no path
that answers after a failure by asking again unconstrained. A structured-output
guarantee that quietly degrades on the hard case is worse than none, because
every refusal above it was built on the assumption that it holds. A daemon that
is not running raises `OllamaUnavailable` naming the command to run, and that
error is neither retried nor caught.

The callback, and how it differs from the pydantic adapter
----------------------------------------------------------
`PydanticStructuredOutput.structured` asks its callback for the emission itself,
because the model call happens outside it. This adapter owns the model call,
because the schema has to reach the request for the constraint to exist, so its
callback is asked for the prompt instead. Both are called with None first and
with the repair text on each retry. The mismatch is a real edge of the seam
rather than a hidden one, so a callback returning anything but a string raises a
`TypeError` naming both adapters instead of sending a dict repr to the model.

Determinism
-----------
`scripts/checks/nondeterminism-gate.sh` bans a direct clock read, RNG draw, and
`socket.socket` outside the kernel adapter package, because twinflow replays a
scenario only when every module reaches the outside world through an injected
port. This module holds to that shape: `OllamaStructuredOutput` takes its
transport as a parameter and never constructs one implicitly, so a simulation
run drives a recorded transport and never opens a connection. `sim` behavior is
therefore a fixture rather than a network. The one real adapter here,
`UrllibJsonTransport`, is the piece that belongs in the kernel package under
that rule; it lives here only because this work package does not own that
package, and ADR-0002 records the move as an obligation rather than leaving it
implicit. Nothing here reads a clock, draws a random number, or iterates an
unordered collection. The sampler is pinned with `temperature` 0 and an explicit
seed, which is the part of the answer's reproducibility this package controls.
"""

from __future__ import annotations

import json
import urllib.error
import urllib.parse
import urllib.request
from collections.abc import Callable, Mapping
from typing import Any, Protocol, runtime_checkable

from pydantic import BaseModel, ValidationError

from twinflow.agent.tools import ModelT, _repair_prompt

#: Where Ollama listens by default. Loopback, which is the whole license
#: argument in this module: no remote host means no certificate to verify.
DEFAULT_OLLAMA_BASE_URL = "http://localhost:11434"

#: The model the quickstart pulls. Named rather than discovered, so a run that
#: cannot find it says which model it wanted instead of picking a different one.
DEFAULT_OLLAMA_MODEL = "llama3.1"

#: Generous, because a first call on a cold model loads weights from disk. A
#: caller that wants a tighter bound passes one.
DEFAULT_TIMEOUT_S = 120.0

#: The schema is enforced by the decoder, so this says only what the decoder
#: cannot: no fence, no commentary, one document.
DEFAULT_SYSTEM_PROMPT = (
    "Answer with exactly one JSON document matching the supplied schema. "
    "Write no prose, no explanation, and no markdown code fence."
)

#: What a reader does next when the daemon is missing. Written once, because a
#: failure message that varies by call site teaches the reader nothing.
_START_HINT = (
    f"The local model path needs the Ollama daemon. Install it from "
    f"https://ollama.com, start it with `ollama serve`, then pull a model with "
    f"`ollama pull {DEFAULT_OLLAMA_MODEL}`. There is no unconstrained fallback: "
    f"an answer produced without the schema constraint would not carry the "
    f"guarantee this seam exists to provide."
)


class OllamaError(Exception):
    """The local model could not answer. Nothing partial is returned with it."""


class OllamaUnavailable(OllamaError):
    """The daemon is not reachable. Raised once, never retried, never caught."""


class ConstraintNotHonored(OllamaError):
    """The answer was not a JSON document, so `format` did not take effect.

    Separate from a `ValidationError` on purpose. A validation failure means the
    model produced the wrong document, which a retry can repair. This means the
    server did not apply the constraint at all, which is a deployment fact the
    reader needs to see named.
    """


@runtime_checkable
class JsonHttpTransport(Protocol):
    """One POST of a JSON document, returning a JSON document.

    The injected port of this module. It exists so the suite drives a fake and
    asserts what reached the wire, and so a simulation run replays a recording
    rather than opening a connection.
    """

    def post_json(
        self, url: str, payload: Mapping[str, Any], *, timeout_s: float
    ) -> Mapping[str, Any]:
        """POST `payload` as JSON. Raise `OllamaUnavailable` when unreachable."""
        ...


class UrllibJsonTransport:
    """The real transport, on the standard library alone.

    `urllib.request` rather than an HTTP client distribution, because the client
    distributions reach `certifi` for their certificate authority bundle and
    `certifi` is MPL-2.0, which the run-time allowlist refuses. A request to
    loopback verifies no certificate, so the bundle buys nothing here.
    """

    def post_json(
        self, url: str, payload: Mapping[str, Any], *, timeout_s: float
    ) -> Mapping[str, Any]:
        body = json.dumps(dict(payload), ensure_ascii=False).encode("utf-8")
        # The scheme reached _chat_url before it reached here, so this cannot be
        # a file: or ftp: URL however the base URL was configured.
        request = urllib.request.Request(
            url,
            data=body,
            method="POST",
            headers={"Content-Type": "application/json", "Accept": "application/json"},
        )
        try:
            with urllib.request.urlopen(request, timeout=timeout_s) as response:
                raw = response.read()
        except urllib.error.HTTPError as error:
            detail = error.read().decode("utf-8", "replace").strip()
            raise OllamaError(
                f"{url} answered HTTP {error.code}: {detail or error.reason}. {_START_HINT}"
            ) from error
        except urllib.error.URLError as error:
            raise OllamaUnavailable(f"cannot reach {url}: {error.reason}. {_START_HINT}") from error
        except TimeoutError as error:
            raise OllamaUnavailable(
                f"{url} did not answer within {timeout_s} seconds. {_START_HINT}"
            ) from error
        except OSError as error:
            raise OllamaUnavailable(f"cannot reach {url}: {error}. {_START_HINT}") from error

        try:
            document = json.loads(raw.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as error:
            raise OllamaError(f"{url} answered with a body that is not JSON") from error
        if not isinstance(document, dict):
            raise OllamaError(f"{url} answered with {type(document).__name__}, not a JSON object")
        return document


class OllamaStructuredOutput:
    """Constrained decoding against a local Ollama daemon (D10).

    Fills `twinflow.agent.tools.StructuredOutputAdapter`, so this is a swap at
    one constructor rather than a change to any tool.

        adapter = OllamaStructuredOutput(model_name="llama3.1")
        call = registry.bind_structured("query_metric", prompt_for, adapter=adapter)

    `prompt_for` is called with None first and with the repair text on each
    retry, and returns the prompt to send. See the module docstring for why this
    callback differs from the pydantic adapter's.
    """

    def __init__(
        self,
        *,
        model_name: str = DEFAULT_OLLAMA_MODEL,
        base_url: str = DEFAULT_OLLAMA_BASE_URL,
        transport: JsonHttpTransport | None = None,
        timeout_s: float = DEFAULT_TIMEOUT_S,
        seed: int = 0,
        temperature: float = 0.0,
        system_prompt: str = DEFAULT_SYSTEM_PROMPT,
    ) -> None:
        self._model_name = model_name
        self._chat_url = _chat_url(base_url)
        self._transport: JsonHttpTransport = transport or UrllibJsonTransport()
        self._timeout_s = timeout_s
        self._seed = seed
        self._temperature = temperature
        self._system_prompt = system_prompt

    @property
    def chat_url(self) -> str:
        """The endpoint this adapter posts to. Read by an operator, not by code."""
        return self._chat_url

    def structured(
        self,
        model: type[ModelT],
        emit: Callable[[str | None], object],
        *,
        max_retries: int = 2,
    ) -> ModelT:
        """Return a validated instance of `model`, or raise. Never anything else.

        The schema goes into every request, including every retry. The exhausted
        branch re-raises the last failure rather than returning a partial value,
        which is the same refusal `PydanticStructuredOutput` makes and for the
        same reason.
        """
        if max_retries < 0:
            raise ValueError("max_retries cannot be negative")
        schema = model.model_json_schema()
        feedback: str | None = None
        for attempt in range(max_retries + 1):
            prompt = emit(feedback)
            if not isinstance(prompt, str):
                raise TypeError(
                    f"this adapter owns the model call, so its callback returns the prompt "
                    f"to send and got {type(prompt).__name__}. A callback written for "
                    f"PydanticStructuredOutput returns the emission instead, and that "
                    f"adapter is the one to pass when the emission is produced elsewhere"
                )
            try:
                return model.model_validate(self._ask(prompt, schema))
            except (ValidationError, ConstraintNotHonored) as error:
                # OllamaUnavailable and the other OllamaError cases are not
                # caught here. Retrying a refused connection turns one clear
                # failure into three, and a broad except around this call is
                # exactly how a silent unconstrained fallback gets written.
                if attempt == max_retries:
                    raise
                feedback = _feedback_for(model, error)
        raise AssertionError("unreachable: the loop returns or raises on every attempt")

    def _ask(self, prompt: str, schema: Mapping[str, Any]) -> object:
        """One constrained request, and the document it produced."""
        payload = {
            "model": self._model_name,
            "messages": [
                {"role": "system", "content": self._system_prompt},
                {"role": "user", "content": prompt},
            ],
            # The decode-time constraint. This key is what makes the local path
            # a guarantee rather than a request, so nothing may make it optional.
            "format": dict(schema),
            "stream": False,
            "options": {"temperature": self._temperature, "seed": self._seed},
        }
        body = self._transport.post_json(self._chat_url, payload, timeout_s=self._timeout_s)
        message = body.get("message")
        content = message.get("content") if isinstance(message, Mapping) else None
        if not isinstance(content, str) or not content.strip():
            raise ConstraintNotHonored(
                f"{self._chat_url} returned no assistant content, so the `format` "
                f"constraint produced nothing to validate"
            )
        try:
            return json.loads(content)
        except json.JSONDecodeError as error:
            raise ConstraintNotHonored(
                f"{self._chat_url} returned text that is not a JSON document, so the "
                f"`format` constraint was not applied. Check that the daemon is a build "
                f"that supports schema-constrained decoding"
            ) from error


def _chat_url(base_url: str) -> str:
    """The chat endpoint, with the base URL checked before it reaches urlopen.

    The scheme check is not decoration. `urlopen` also opens `file:` and `ftp:`,
    so an unchecked base URL turns a configuration value into a file read.
    """
    parts = urllib.parse.urlsplit(base_url)
    if parts.scheme not in ("http", "https"):
        raise ValueError(
            f"the Ollama base URL is {base_url!r}, whose scheme is {parts.scheme!r}. "
            f"Only http and https are accepted, because urlopen also opens file and ftp"
        )
    if not parts.netloc:
        raise ValueError(f"the Ollama base URL {base_url!r} names no host")
    return base_url.rstrip("/") + "/api/chat"


def _feedback_for(model: type[BaseModel], error: Exception) -> str:
    """The repair text the next prompt carries.

    A schema failure reuses `_repair_prompt`, so the two adapters give a model
    the same words for the same miss and the repair text has one home.
    """
    if isinstance(error, ValidationError):
        return _repair_prompt(model, error)
    return (
        f"That answer was not a JSON document. Emit one {model.__name__} JSON "
        f"document and nothing else."
    )
