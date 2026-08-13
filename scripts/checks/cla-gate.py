#!/usr/bin/env python3
"""Contributor agreement gate CLA-001, the C13 check CLA.md section 7 publishes.

    python scripts/checks/cla-gate.py line-shape
    python scripts/checks/cla-gate.py signature --author octocat
    python scripts/checks/cla-gate.py trailers --range BASE..HEAD
    python scripts/checks/cla-gate.py --selftest

Three checks, and CLA.md section 7 names all three. `Line shape` reads section
8 and holds every signature to the published expression. `Signature present`
asks whether one handle appears there. `Trailers present` walks a commit range
and asks whether every non-merge commit carries a `Signed-off-by`.

THE EXPRESSION IS NOT WRITTEN HERE
----------------------------------
It is parsed out of the fenced block in CLA.md section 7, the same way the
commit message gate parses its type set out of the commit-msg hook. A second
copy is a copy that drifts, and then a signature the published rule accepts
fails the check that runs after it. A contributor reading section 7 and a job
refusing their pull request would both be correct against their own copy, and
the contributor is the one who finds out.

WHY THE WORKFLOW CALLS THIS AND DOES NOT REIMPLEMENT IT
------------------------------------------------------
Engineering rule 10: the same command locally and in CI. These checks lived as
inline `awk` and `grep` inside the `cla` job, which meant a contributor could
not run them before pushing and the phase-exit runner could not run them at
all. A gate the release ritual cannot execute is a gate nobody executes.

WHAT `trailers` IS NOT RUN OVER
-------------------------------
Not this repository's own history. The owner is the copyright holder, so under
section 7 there is no license to grant and no signature to give, and their
commits carry no trailer by design. Running this over `v0.1.0..HEAD` would fail
on every commit and would be asserting the wrong thing. The range belongs to a
pull request, which is why the workflow passes one and the gate does not.
"""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
CLA = REPO_ROOT / "CLA.md"

#: The heading that opens the signatory list. Section 7 points a contributor at
#: it by name, so the heading text is part of the published contract.
SIGNATORIES_HEADING = "## 8. Signatories"

#: A fenced block in section 7 holding a line-anchored expression. Section 7
#: also fences a worked signatory line and a worked commit message, so the
#: anchors are what tell the expression apart from the examples.
_PUBLISHED_EXPRESSION = re.compile(r"^\^- @.*\$$", re.MULTILINE)

#: A line somebody meant as a signature. Held separately from the published
#: expression because a sentence is not a malformed signature, and reporting it
#: as one would send somebody to fix prose that was never a signature.
#:
#: The space after the marker is deliberately not required. CommonMark says
#: `-@octocat 2026-08-09` is a paragraph rather than a list item, so a
#: contributor who forgets the space writes a signature that renders as prose
#: and counts for nothing. Reading it as a near miss is what lets `Line shape`
#: say which character is wrong, rather than leaving `Signature present` to
#: report the handle as absent from a list it is visibly sitting in.
_LIST_ITEM = re.compile(r"^[ \t]*[-*+]")

#: A GitHub handle, as section 7's own expression bounds it.
_HANDLE = re.compile(r"^[A-Za-z0-9-]{1,39}$")


def published_expression(text: str) -> re.Pattern[str]:
    """Read the signatory expression out of CLA.md rather than restating it."""
    found = _PUBLISHED_EXPRESSION.findall(text)
    if not found:
        raise SystemExit(
            "CLA.md publishes no line-anchored signatory expression. Section 7 "
            "carries it in a fenced block, and this gate reads it from there "
            "rather than holding a second copy."
        )
    if len(found) > 1:
        raise SystemExit(
            f"CLA.md publishes {len(found)} line-anchored expressions and this "
            "gate cannot tell which one governs a signature. Leave one."
        )
    return re.compile(found[0])


def signatory_block(text: str) -> list[str]:
    """Every line inside section 8, up to the next heading."""
    lines = text.splitlines()
    try:
        start = lines.index(SIGNATORIES_HEADING) + 1
    except ValueError:
        raise SystemExit(
            f"CLA.md carries no {SIGNATORIES_HEADING!r} heading, so there is no "
            "signatory list to check. Section 7 sends every contributor there."
        ) from None
    block: list[str] = []
    for line in lines[start:]:
        if line.startswith("## "):
            break
        block.append(line)
    return block


def check_line_shape(text: str) -> list[str]:
    """Hold every signature in section 8 to the published expression."""
    expression = published_expression(text)
    return [
        line
        for line in signatory_block(text)
        if _LIST_ITEM.match(line) and not expression.match(line)
    ]


def check_signature(text: str, author: str, *, owner: str = "") -> str | None:
    """Ask whether one handle has signed. Returns a reason when it has not."""
    if not _HANDLE.match(author):
        return f"author handle {author!r} is not a GitHub handle"
    if owner and author.lower() == owner.lower():
        return None
    expression = published_expression(text)
    for line in signatory_block(text):
        if not _LIST_ITEM.match(line) or not expression.match(line):
            continue
        # The expression bounds the handle, so the second token is one.
        if line.split()[1].lstrip("@").lower() == author.lower():
            return None
    return f"@{author} is not in the signatories list in {SIGNATORIES_HEADING}"


def _git(*args: str) -> str:
    return subprocess.run(
        ["git", *args], capture_output=True, text=True, check=True, cwd=REPO_ROOT
    ).stdout.strip()


def check_trailers(rev_range: str) -> list[str]:
    """Every non-merge commit in the range carries a Signed-off-by with a value.

    Merge commits are excluded. A merge carries no author-written content, and
    the button that writes one leaves a subject no contributor can sign after
    the fact.
    """
    revisions = _git("rev-list", "--no-merges", *rev_range.split()).splitlines()
    unsigned: list[str] = []
    for sha in revisions:
        if not sha:
            continue
        trailer = _git("show", "-s", "--format=%(trailers:key=Signed-off-by,valueonly)", sha)
        if not trailer.strip():
            subject = _git("show", "-s", "--format=%s", sha)
            unsigned.append(f"{sha} has no Signed-off-by trailer: {subject}")
    return unsigned


def _selftest() -> int:
    """Prove each check can fail. A check nobody has seen fail may not be one."""
    expression = "^- @[A-Za-z0-9-]{1,39} [0-9]{4}-[0-9]{2}-[0-9]{2}$"
    good = (
        f"# T\n\n## 7. How\n\n```text\n{expression}\n```\n\n"
        f"{SIGNATORIES_HEADING}\n\n- @octocat 2026-08-09\n"
    )
    failures: list[str] = []

    if check_line_shape(good):
        failures.append("line-shape rejected a signature the published expression accepts")

    for bad, why in [
        ("- @octocat 2026-8-9", "a date that is not YYYY-MM-DD"),
        ("- octocat 2026-08-09", "a handle with no @"),
        ("- @octocat", "a line with no date"),
        ("- @not a handle 2026-08-09", "a handle carrying a space"),
    ]:
        if not check_line_shape(good.replace("- @octocat 2026-08-09", bad)):
            failures.append(f"line-shape accepted {why}: {bad!r}")

    if check_signature(good, "octocat") is not None:
        failures.append("signature refused a handle that is in the list")
    if check_signature(good, "mona") is None:
        failures.append("signature accepted a handle that is not in the list")
    if check_signature(good, "MONA", owner="mona") is not None:
        failures.append("signature asked the copyright holder for a signature")
    if check_signature(good, "not a handle") is None:
        failures.append("signature accepted something that is not a GitHub handle")

    # An empty list is the state this repository is in, and it must not read as
    # a pass that proves something. It proves only that nothing is malformed.
    empty = good.replace("- @octocat 2026-08-09\n", "")
    if check_signature(empty, "octocat") is None:
        failures.append("signature accepted a handle against an empty list")

    for line in failures:
        print(f"[cla] SELFTEST {line}")
    if failures:
        return 1
    print("[cla] selftest: every check refuses what it is meant to refuse")
    return 0


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--selftest", action="store_true", help="prove each check can fail")
    sub = parser.add_subparsers(dest="check")
    sub.add_parser("line-shape", help="every signature matches the published expression")
    signature = sub.add_parser("signature", help="one handle has signed")
    signature.add_argument("--author", required=True)
    signature.add_argument("--owner", default="")
    trailers = sub.add_parser("trailers", help="every non-merge commit is signed off")
    trailers.add_argument("--range", dest="rev_range", required=True)
    args = parser.parse_args(argv)

    if args.selftest:
        return _selftest()
    if args.check is None:
        parser.error("name a check, or pass --selftest")

    text = CLA.read_text(encoding="utf-8")

    if args.check == "line-shape":
        bad = check_line_shape(text)
        for line in bad:
            print(f"[cla] {CLA.name}: signature does not match the published expression: {line}")
        if bad:
            return 1
        print(f"[cla] every signature in {SIGNATORIES_HEADING} matches the published expression")
        return 0

    if args.check == "signature":
        reason = check_signature(text, args.author, owner=args.owner)
        if reason:
            print(f"[cla] {reason}")
            return 1
        print(f"[cla] @{args.author} has signed, or holds the copyright")
        return 0

    unsigned = check_trailers(args.rev_range)
    for line in unsigned:
        print(f"[cla] {line}")
    if unsigned:
        print("[cla] sign every commit with: git commit -s")
        return 1
    print(f"[cla] every non-merge commit in {args.rev_range} carries a Signed-off-by trailer")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
