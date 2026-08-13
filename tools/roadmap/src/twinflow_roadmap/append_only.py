"""The append-only rule over the requirement register.

Two claims, and they are different claims. This checker proves that a given pair
of versions is a legal edit; the history test walks the real commits and proves
that no edit so far broke it; the property test generates pairs and proves the
checker is right about edits nobody has made yet. Calling the history walk a
property would have hidden that it says nothing about the next commit.

Removal and rewording are the same failure from two directions. Remove an entry
and the idea leaves the plan with no record. Reword the verbatim clause and the
plan drifts from the ask while every id still lines up.
"""

from __future__ import annotations

from collections.abc import Mapping

from twinflow_roadmap.errors import Finding

REQUIREMENTS_FILE = "requirements.yaml"


def check_append_only(
    before: Mapping[str, Mapping], after: Mapping[str, Mapping], *, revision: str = "this edit"
) -> list[Finding]:
    """Compare two versions of the register, oldest first."""
    findings: list[Finding] = []

    for identifier in sorted(set(before) - set(after)):
        findings.append(
            Finding(
                "APPEND-REMOVED",
                f"{revision} removes {identifier}. The register is append-only: an idea that "
                f"belongs somewhere else is reordered in roadmap.yaml, and the resequencing "
                f"register records the move",
                REQUIREMENTS_FILE,
                ids=(identifier,),
            )
        )

    for identifier, entry in before.items():
        later = after.get(identifier)
        if later is None:
            continue
        was, now = entry.get("quote"), later.get("quote")
        if was is not None and was != now:
            what = "removes" if now is None else "rewords"
            findings.append(
                Finding(
                    "APPEND-QUOTE",
                    f"{revision} {what} the verbatim clause on {identifier}. The quote is the "
                    f"ask, and editing it lets the plan drift from it without any id changing",
                    REQUIREMENTS_FILE,
                    ids=(identifier,),
                )
            )

    return findings
