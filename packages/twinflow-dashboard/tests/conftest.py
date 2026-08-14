"""A minimal DOM over the shipped page, built with the standard library.

Gate VAL-GATE-A11Y-001 is checked here against the rendered markup rather than
against a description of it. That needs a parser, and it deliberately does not
need a browser: the three clauses this tier can falsify are properties of the
document and the stylesheet, and the clause that needs a browser is named in
`twinflow.dashboard.accessibility` as out of reach from here and is asserted by
`browser/axe-gate.mjs` instead.

`html.parser` rather than a dependency, because section 2.1 of the design page
fixes this package's dependency list at four names and a test tier that added a
fifth would be trading the install-alone claim of D-10 for convenience.
"""

from __future__ import annotations

import asyncio
import json
import re
from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import UTC, datetime
from html.parser import HTMLParser
from typing import Any
from urllib.parse import urlencode

import pytest

from twinflow.dashboard import DashboardConfig, index_html
from twinflow.schemas import Envelope

#: Elements the HTML specification says have no closing tag. `html.parser` does
#: not know them, so a page nesting everything after the first `<meta>` inside
#: it would give a tree that no browser agrees with.
VOID_TAGS = frozenset(
    {
        "area",
        "base",
        "br",
        "col",
        "embed",
        "hr",
        "img",
        "input",
        "link",
        "meta",
        "param",
        "source",
        "track",
        "wbr",
    }
)

#: Focusable without a `tabindex`, per the HTML specification's definition of a
#: default tab index. `a` counts only with an `href`, which is why it is checked
#: rather than listed.
NATIVELY_FOCUSABLE = frozenset({"button", "select", "textarea", "input", "summary"})


@dataclass
class Node:
    tag: str
    attrs: dict[str, str]
    children: list[Node] = field(default_factory=list)
    parent: Node | None = None
    text: str = ""

    @property
    def id(self) -> str | None:
        return self.attrs.get("id")

    def walk(self):
        for child in self.children:
            yield child
            yield from child.walk()

    def all_text(self) -> str:
        parts = [self.text]
        for child in self.children:
            parts.append(child.all_text())
        return " ".join(part for part in parts if part).strip()

    def find(self, node_id: str) -> Node | None:
        for node in self.walk():
            if node.id == node_id:
                return node
        return None

    def by_tag(self, tag: str) -> list[Node]:
        return [node for node in self.walk() if node.tag == tag]


class _Tree(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.root = Node(tag="#document", attrs={})
        self._stack = [self.root]

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        node = Node(
            tag=tag,
            attrs={name: (value if value is not None else "") for name, value in attrs},
            parent=self._stack[-1],
        )
        self._stack[-1].children.append(node)
        if tag not in VOID_TAGS:
            self._stack.append(node)

    def handle_startendtag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        node = Node(
            tag=tag,
            attrs={name: (value if value is not None else "") for name, value in attrs},
            parent=self._stack[-1],
        )
        self._stack[-1].children.append(node)

    def handle_endtag(self, tag: str) -> None:
        for index in range(len(self._stack) - 1, 0, -1):
            if self._stack[index].tag == tag:
                del self._stack[index:]
                return

    def handle_data(self, data: str) -> None:
        stripped = data.strip()
        if stripped:
            self._stack[-1].text = (self._stack[-1].text + " " + stripped).strip()


def parse(markup: str) -> Node:
    tree = _Tree()
    tree.feed(markup)
    tree.close()
    return tree.root


def is_focusable(node: Node) -> bool:
    """Whether a keyboard reaches this element in the ordinary tab order."""
    if node.attrs.get("hidden") is not None and "hidden" in node.attrs:
        return False
    if node.attrs.get("aria-hidden") == "true":
        return False
    if "disabled" in node.attrs:
        return False
    tabindex = node.attrs.get("tabindex")
    if tabindex is not None:
        return int(tabindex) >= 0
    if node.tag == "a":
        return "href" in node.attrs
    if node.tag == "input":
        return node.attrs.get("type") != "hidden"
    return node.tag in NATIVELY_FOCUSABLE


def focusables(root: Node) -> list[Node]:
    """Every focusable element, in document order."""
    return [node for node in root.walk() if is_focusable(node)]


@pytest.fixture(scope="session")
def markup() -> str:
    return index_html()


@pytest.fixture(scope="session")
def dom(markup: str) -> Node:
    return parse(markup)


@pytest.fixture(scope="session")
def stylesheet(markup: str) -> str:
    """The one `<style>` block, extracted from the shipped file.

    A regex rather than the tree above, because `html.parser` treats the
    contents of `<style>` as character data and a CSS selector containing `>`
    would come back mangled.
    """
    blocks = re.findall(r"<style>(.*?)</style>", markup, flags=re.S)
    assert len(blocks) == 1, f"the page ships exactly one style block, found {len(blocks)}"
    return blocks[0]


@pytest.fixture(scope="session")
def script(markup: str) -> str:
    """The one `<script>` block, the same way the node:vm tier extracts it."""
    blocks = re.findall(r"<script>(.*?)</script>", markup, flags=re.S)
    assert len(blocks) == 1, f"the page ships exactly one script block, found {len(blocks)}"
    return blocks[0]


def make_config(**overrides: object) -> DashboardConfig:
    fields: dict[str, object] = {
        "run_id": "run_01jabcdefghijklmnopqrstuvw",
        "epoch": datetime(2026, 1, 1, tzinfo=UTC),
    }
    fields.update(overrides)
    # `model_validate` rather than `DashboardConfig(**fields)`: an override may
    # carry any field, so the mapping is typed `object`, and unpacking it into
    # the constructor asks the checker to match `object` against every
    # annotation on the model. This validates the same fields and raises the
    # same refusals.
    return DashboardConfig.model_validate(fields)


@pytest.fixture
def config() -> DashboardConfig:
    return make_config()


class StepClock:
    """A sim clock the test drives, so nothing here reads a wall clock."""

    def __init__(self, at: int = 0) -> None:
        self.at = at

    def __call__(self) -> int:
        return self.at


# ------------------------------------------------------------------ ASGI driver


@dataclass(frozen=True)
class Reply:
    """One HTTP response, collected from the ASGI messages the app sent."""

    status_code: int
    headers: Mapping[str, str]
    content: bytes

    @property
    def text(self) -> str:
        return self.content.decode("utf-8")

    def json(self) -> Any:
        return json.loads(self.content)


class Client:
    """Drives an ASGI app directly, with no HTTP client between test and app.

    Starlette ships a `TestClient` and it is not used here, for a licensing
    reason that is a project rule rather than a preference. That client is built
    on httpx, httpx depends on certifi, and certifi is MPL-2.0. The
    CONTRIBUTING.md allowlist refuses copyleft in the shipped tree, and the
    owner's ruling extends that to the development closure unless it is
    unavoidable. Here it is avoidable in about forty lines.

    Driving the app directly is also the stricter test. An ASGI application is
    an async callable over `(scope, receive, send)`, and this exercises that
    contract with nothing in between: the scope is built here, the request body
    is fed through `receive`, and the status, headers, and body come back as the
    `http.response.start` and `http.response.body` messages the app actually
    emitted. A streaming response arrives as the several body messages it really
    sends, which is how the server-sent-event tests see more than one frame.
    """

    def __init__(self, app: Any, recorded: list[Envelope] | None = None) -> None:
        self._app = app
        #: The envelopes the app wrote through its sink, for a caller that
        #: wired one. Declared here rather than attached from the outside: a
        #: field a test assigns onto the instance is a field neither a reader
        #: nor a checker can find from the class.
        self.recorded: list[Envelope] = [] if recorded is None else recorded

    def get(
        self,
        path: str,
        *,
        params: Mapping[str, Any] | None = None,
        headers: Mapping[str, str] | None = None,
    ) -> Reply:
        return self.request("GET", path, params=params, headers=headers)

    def post(
        self,
        path: str,
        *,
        json_body: Any = None,
        content: bytes | None = None,
        params: Mapping[str, Any] | None = None,
        headers: Mapping[str, str] | None = None,
    ) -> Reply:
        return self.request(
            "POST", path, params=params, headers=headers, json_body=json_body, content=content
        )

    def request(
        self,
        method: str,
        path: str,
        *,
        params: Mapping[str, Any] | None = None,
        headers: Mapping[str, str] | None = None,
        json_body: Any = None,
        content: bytes | None = None,
    ) -> Reply:
        raw_headers: list[tuple[bytes, bytes]] = [(b"host", b"testserver")]
        body = b""
        if json_body is not None:
            body = json.dumps(json_body).encode("utf-8")
            raw_headers.append((b"content-type", b"application/json"))
        elif content is not None:
            body = content
        if body:
            raw_headers.append((b"content-length", str(len(body)).encode("ascii")))
        for name, value in (headers or {}).items():
            raw_headers.append((name.lower().encode("ascii"), value.encode("utf-8")))

        scope = {
            "type": "http",
            "asgi": {"version": "3.0", "spec_version": "2.3"},
            "http_version": "1.1",
            "method": method,
            "scheme": "http",
            "path": path,
            "raw_path": path.encode("utf-8"),
            "query_string": _query_string(params),
            "root_path": "",
            "headers": raw_headers,
            "client": ("test", 12345),
            "server": ("testserver", 80),
        }
        return asyncio.run(_drive(self._app, scope, body))


def _query_string(params: Mapping[str, Any] | None) -> bytes:
    """Encode query parameters, repeating a key for each value in a list.

    Repetition rather than a comma-joined value, because that is how a browser
    sends a repeated parameter and how the routes read `subject`.
    """
    if not params:
        return b""
    pairs: list[tuple[str, str]] = []
    for key in params:
        value = params[key]
        if isinstance(value, (list, tuple)):
            pairs.extend((key, str(item)) for item in value)
        else:
            pairs.append((key, str(value)))
    return urlencode(pairs).encode("ascii")


async def _drive(app: Any, scope: dict[str, Any], body: bytes) -> Reply:
    """Run one request through the app and collect what it sent back."""
    delivered = False
    status = 0
    headers: dict[str, str] = {}
    chunks: list[bytes] = []

    async def receive() -> dict[str, Any]:
        nonlocal delivered
        if delivered:
            return {"type": "http.disconnect"}
        delivered = True
        return {"type": "http.request", "body": body, "more_body": False}

    async def send(message: Mapping[str, Any]) -> None:
        nonlocal status
        if message["type"] == "http.response.start":
            status = int(message["status"])
            for name, value in message.get("headers", ()):
                headers[name.decode("latin-1").lower()] = value.decode("latin-1")
        elif message["type"] == "http.response.body":
            chunks.append(bytes(message.get("body", b"")))

    await app(scope, receive, send)
    return Reply(status_code=status, headers=headers, content=b"".join(chunks))
