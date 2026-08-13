"""Findings, and how they print.

One finding type rather than an exception hierarchy. A validator that raises on
the first problem tells a contributor about one of the eight things they got
wrong, and they find the other seven one CI run at a time. Every check here
collects, and the command prints the whole set.

Each finding carries a rule id. The id is what a contributor searches for, what
a commit message cites when it fixes one, and what a test asserts on, so the
message wording can improve without breaking either.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class Finding:
    """One thing that is wrong, and where to look."""

    rule: str
    message: str
    #: Repository-relative, so the printed line is clickable from the root.
    path: str
    #: One-based, as an editor counts. None where the finding is about a file
    #: as a whole rather than about a line in it.
    line: int | None = None
    #: The identifiers the finding is about, for a caller that wants to group.
    ids: tuple[str, ...] = field(default_factory=tuple)

    def __str__(self) -> str:
        where = f"{self.path}:{self.line}" if self.line else self.path
        return f"{where}  [{self.rule}] {self.message}"


class RoadmapError(Exception):
    """Raised when a file cannot be read at all.

    Only for the case where there is nothing to validate: a missing file, or a
    document that is not YAML. Anything the parser can read becomes findings
    instead, because a caller wants the whole list.
    """
