"""Reading YAML in a way that keeps the line numbers.

C5 asks for a line-numbered error carrying a suggestion, and a plain safe_load
parses the same document and leaves every diagnostic pointing at nothing. The
round-trip loader keeps a `.lc` record on every container, so a finding about
`work_packages[41].covers[0].id` can name the line that value sits on.

The helpers are small on purpose. A caller asks for the line of a key, and gets
either the line or None, and a None line prints as a file-level finding rather
than as a wrong one.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from ruamel.yaml import YAML
from ruamel.yaml.error import YAMLError

from twinflow_roadmap.errors import RoadmapError


def read(path: Path) -> Any:
    """Parse one YAML document, keeping line and column on every node."""
    if not path.is_file():
        raise RoadmapError(f"{path} does not exist")
    parser = YAML(typ="rt")
    try:
        return parser.load(path.read_text(encoding="utf-8"))
    except YAMLError as error:
        raise RoadmapError(f"{path} is not valid YAML: {error}") from error


def line_of(container: Any, key: Any = None) -> int | None:
    """The one-based line of `key` inside `container`, or of the container.

    Returns None rather than guessing. A finding with no line prints against the
    file, which is honest; a finding with a line that points at the wrong place
    sends a contributor to the wrong part of the document.
    """
    marks = getattr(container, "lc", None)
    if marks is None:
        return None
    if key is None:
        line = getattr(marks, "line", None)
        return None if line is None else line + 1
    try:
        position = marks.item(key) if isinstance(key, int) else marks.key(key)
    except (KeyError, IndexError, TypeError, AttributeError):
        return None
    if position is None:
        return None
    return position[0] + 1


def plain(node: Any) -> Any:
    """The same data with the round-trip wrappers removed.

    Pydantic accepts a CommentedMap, since it is a Mapping, but the models are
    frozen and comparing two loads is easier when both sides are plain.
    """
    if isinstance(node, dict):
        return {key: plain(value) for key, value in node.items()}
    if isinstance(node, list):
        return [plain(item) for item in node]
    return node
