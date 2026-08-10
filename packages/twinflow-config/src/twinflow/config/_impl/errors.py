"""Config diagnostics: a code, a location, and something to do about it.

A validator that says "invalid" has told the author nothing they did not
already know. Every diagnostic here carries three things: the code, the line and
column in the file the author edited, and a suggestion. Gate CFG-001 asserts
exactly that, because a schema error rendered as a JSON pointer is a puzzle
rather than a message.
"""

from __future__ import annotations

import difflib
from dataclasses import dataclass, field
from enum import StrEnum


class Severity(StrEnum):
    ERROR = "error"
    WARNING = "warning"


@dataclass(frozen=True)
class Diagnostic:
    """One finding against one config file."""

    code: str
    message: str
    path: str
    line: int
    column: int
    severity: Severity = Severity.ERROR
    #: What to do about it. A diagnostic without one is a diagnostic that makes
    #: the reader guess, which is what CFG-001 exists to prevent.
    suggestion: str | None = None
    notes: tuple[str, ...] = field(default_factory=tuple)

    def render(self, source_lines: list[str] | None = None) -> str:
        """The human format of foundations 5.6."""
        head = f"{self.severity.value}[{self.code}]: {self.message}"
        location = f"  --> {self.path}:{self.line}:{self.column}"
        out = [head, location]

        if source_lines and 1 <= self.line <= len(source_lines):
            text = source_lines[self.line - 1].rstrip("\n")
            gutter = " " * len(str(self.line))
            out.append(f" {gutter} |")
            out.append(f" {self.line} | {text}")
            caret = " " * max(self.column - 1, 0) + "^"
            if self.suggestion:
                out.append(f" {gutter} | {caret} {self.suggestion}")
            else:
                out.append(f" {gutter} | {caret}")
            out.append(f" {gutter} |")
        elif self.suggestion:
            out.append(f"   = {self.suggestion}")

        out.extend(f"   = {note}" for note in self.notes)
        return "\n".join(out)


def nearest(name: str, candidates: list[str]) -> str | None:
    """The closest candidate to a misspelling, or None when nothing is close.

    Returning None rather than the least-bad match matters: "did you mean
    'shipping'?" against a key that is nothing like it sends the author down a
    wrong path, which is worse than saying only that the key is unknown.
    """
    matches = difflib.get_close_matches(name, candidates, n=1, cutoff=0.6)
    return matches[0] if matches else None
