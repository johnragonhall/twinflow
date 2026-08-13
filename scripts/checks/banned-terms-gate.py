#!/usr/bin/env python3
"""IP hygiene gate IPH-001, the CON-5 scan.

    python scripts/checks/banned-terms-gate.py --all        the tracked tree
    python scripts/checks/banned-terms-gate.py --staged     the staged added lines
    python scripts/checks/banned-terms-gate.py --history    every commit message
    python scripts/checks/banned-terms-gate.py --selftest   prove the detector fires

CON-5 is the one constraint with legal consequences and the one that cannot be
fixed afterwards: this repository is public, and a pushed commit is permanent.
So the scan runs at the commit, where a finding costs a re-edit, rather than at
the tag, where it costs a history rewrite.

TWO HALVES, BECAUSE ONE OF THEM CANNOT EXIST ON A RUNNER
--------------------------------------------------------
The strong half reads `.ip-denylist`, a list of client and employer names. That
file is gitignored and never committed, because committing a list of client
names to a public repository defeats the purpose of having the list.
`.ip-denylist.example` is committed in its place, carrying placeholders and the
instructions. A checkout with no denylist reports the half it skipped rather
than passing quietly.

The weak half runs everywhere, including CI, and looks for generic markers of
internal provenance: share-drive paths, document control numbers, and
classification banners.

WHY A BANNER AND NOT A PHRASE
-----------------------------
This repository's own prose discusses confidentiality constantly: CONTRIBUTING.md
tells contributors not to paste anything confidential, and the issue forms make
them affirm that a report carries no proprietary data. A scan for the word would
fire on the policy that exists to prevent the thing.

A leaked document header does not read like prose. It reads like a banner: a
short standalone line that is the classification and nothing else. So a
classification marker counts when the line it sits on is a banner, and a
share-drive path or a control number counts wherever it appears, because neither
has an innocent reading.
"""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
DENYLIST = REPO_ROOT / ".ip-denylist"
DENYLIST_EXAMPLE = REPO_ROOT / ".ip-denylist.example"
PRE_COMMIT_HOOK = REPO_ROOT / "scripts" / "hooks" / "pre-commit"

#: A banner line is short. A classification marker inside a longer line is prose
#: about classification, which this repository writes on purpose.
BANNER_MAX_CHARS = 60

#: Classification markers. These count on a banner line only.
CLASSIFICATION_MARKERS = (
    "internal use only",
    "company confidential",
    "confidential and proprietary",
    "proprietary and confidential",
    "do not distribute",
    "not for distribution",
    "restricted internal",
    "internal only",
    "for internal distribution",
)

#: Markers with no innocent reading, matched anywhere on a line.
_ALWAYS = (
    (
        "share-drive path",
        # A UNC path naming a host and a share. Two backslashes, a host, a
        # separator, and a share name.
        re.compile(r"\\\\[A-Za-z0-9][A-Za-z0-9._-]{2,}\\[A-Za-z0-9._$-]+"),
    ),
    (
        "corporate document store",
        re.compile(r"\b[A-Za-z0-9-]+(?:-my)?\.sharepoint\.com\b", re.IGNORECASE),
    ),
    (
        "document control number",
        # "Document No. 12345", "Doc Control Number: QA-0042". Two narrowings,
        # because the loose form matched "a document no consultant produces":
        # the abbreviation carries its period, so the English word "no" is not
        # it, and the identifier has to contain a digit, because a control
        # number does and an English noun does not.
        re.compile(
            r"\b(?:document|doc)\.?\s*(?:control\s*)?(?:no\.|nos\.|number|id)\s*[:#]?\s*"
            r"(?=[A-Za-z0-9-]*\d)[A-Za-z0-9][A-Za-z0-9-]{2,}",
            re.IGNORECASE,
        ),
    ),
    (
        "controlled copy marker",
        re.compile(r"\b(?:uncontrolled|controlled)\s+copy\b", re.IGNORECASE),
    ),
)

#: Markdown, comment, and table syntax that wraps a banner without softening it.
_DECORATION = re.compile(r"[#>*_`|\-=~\[\]()\"'.,:;!?]+")


class Hit:
    def __init__(self, where: str, line_no: int, reason: str, text: str) -> None:
        self.where = where
        self.line_no = line_no
        self.reason = reason
        self.text = text.strip()

    def __str__(self) -> str:
        excerpt = self.text if len(self.text) <= 120 else self.text[:117] + "..."
        return f"{self.where}:{self.line_no}: {self.reason}: {excerpt}"


def _git(*args: str) -> str:
    result = subprocess.run(
        ["git", *args],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    if result.returncode != 0:
        raise SystemExit(f"BLOCKED: git {' '.join(args)} failed: {result.stderr.strip()}")
    return result.stdout


def normalize(line: str) -> str:
    """A line stripped of decoration, for the banner test."""
    return " ".join(_DECORATION.sub(" ", line).split()).casefold()


def is_banner(line: str) -> bool:
    stripped = normalize(line)
    return 0 < len(stripped) <= BANNER_MAX_CHARS


def denylist_terms() -> list[str]:
    """The private list, or an empty list where it does not exist."""
    if not DENYLIST.is_file():
        return []
    terms = []
    for raw in DENYLIST.read_text(encoding="utf-8").splitlines():
        term = raw.split("#", 1)[0].strip()
        if term:
            terms.append(term)
    return terms


def scan_line(where: str, line_no: int, line: str, terms: list[str]) -> list[Hit]:
    """Every finding on one line."""
    hits: list[Hit] = []
    folded = line.casefold()

    for term in terms:
        if term.casefold() in folded:
            hits.append(Hit(where, line_no, f"denylisted term {term!r}", line))

    for reason, pattern in _ALWAYS:
        if pattern.search(line):
            hits.append(Hit(where, line_no, reason, line))

    if is_banner(line):
        stripped = normalize(line)
        for marker in CLASSIFICATION_MARKERS:
            if marker in stripped:
                hits.append(Hit(where, line_no, f"classification banner {marker!r}", line))

    return hits


def tracked_files() -> list[str]:
    """Every tracked file, minus the ones whose bytes are not text.

    Three files are skipped, and all three for the same reason: they exist to
    carry the shapes this scan looks for. The example denylist holds
    placeholder names, and the gate and its test hold the markers that have to
    fire. Scanning them would turn every fixture into a finding, and a gate
    that reports its own test data has taught everybody to ignore it.
    """
    skip = {
        ".ip-denylist.example",
        "scripts/checks/banned-terms-gate.py",
        "tests/test_banned_terms_gate.py",
    }
    files = []
    for path in _git("ls-files").splitlines():
        if path in skip or not path:
            continue
        files.append(path)
    return files


def scan_tree(terms: list[str]) -> list[Hit]:
    hits: list[Hit] = []
    for path in tracked_files():
        full = REPO_ROOT / path
        try:
            text = full.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        for line_no, line in enumerate(text.splitlines(), start=1):
            hits.extend(scan_line(path, line_no, line, terms))
    return hits


def scan_staged(terms: list[str]) -> list[Hit]:
    """Added lines only. A line the commit does not add is not this commit's."""
    hits: list[Hit] = []
    diff = _git("diff", "--cached", "--unified=0", "--no-color")
    path = "<staged>"
    line_no = 0
    for line in diff.splitlines():
        if line.startswith("+++ b/"):
            path = line[6:]
            continue
        if line.startswith("@@"):
            match = re.search(r"\+(\d+)", line)
            line_no = int(match.group(1)) if match else 0
            continue
        if line.startswith("+") and not line.startswith("+++"):
            hits.extend(scan_line(path, line_no, line[1:], terms))
            line_no += 1
    return hits


def scan_history(terms: list[str]) -> list[Hit]:
    record = "\x1e"
    raw = _git("log", f"--format=%H%n%B{record}")
    hits: list[Hit] = []
    for chunk in raw.split(record):
        chunk = chunk.strip("\n")
        if not chunk:
            continue
        sha, _, message = chunk.partition("\n")
        for line_no, line in enumerate(message.splitlines(), start=1):
            hits.extend(scan_line(f"commit {sha[:8]}", line_no, line, terms))
    return hits


def wiring_findings() -> list[str]:
    """The gate is only standing if the hook that runs it is wired to it."""
    findings: list[str] = []

    if not DENYLIST_EXAMPLE.is_file():
        findings.append(".ip-denylist.example is missing, so nobody is told the denylist exists")

    tracked = set(_git("ls-files").splitlines())
    if ".ip-denylist" in tracked:
        findings.append(
            ".ip-denylist is tracked. A list of client names in a public repository "
            "is the leak this gate exists to prevent"
        )

    ignored = subprocess.run(
        ["git", "check-ignore", "-q", ".ip-denylist"],
        cwd=REPO_ROOT,
        capture_output=True,
    )
    if ignored.returncode != 0:
        findings.append(".ip-denylist is not gitignored, so a real one could be committed")

    if not PRE_COMMIT_HOOK.is_file():
        findings.append("no scripts/hooks/pre-commit, so the scan runs nowhere locally")
    elif "banned-terms-gate.py" not in PRE_COMMIT_HOOK.read_text(encoding="utf-8"):
        findings.append(
            "scripts/hooks/pre-commit does not run this gate, so a commit reaches the "
            "history unscanned"
        )

    return findings


#: Lines that must be found, and lines that must not. The second half is what
#: keeps the detector from firing on this repository's own IP-hygiene policy.
SELFTEST_HITS = (
    r"CONFIDENTIAL - INTERNAL USE ONLY",
    r"Company Confidential",
    r"see \\fileserver01\engineering\specs",
    r"https://contoso-my.sharepoint.com/personal/someone",
    r"Document No. QA-0042",
    r"Uncontrolled copy when printed",
)

SELFTEST_MISSES = (
    "Do not put anything confidential in the discussion itself.",
    "This report contains no proprietary, employer, or client data.",
    "- [ ] No real, client, employer, or proprietary data is introduced anywhere.",
    "Real NMFC classification data is proprietary and is not redistributed.",
    "It contains no client artifacts, no employer code, and no internal documents.",
    # The control-number pattern read "document no consultant" as an
    # abbreviation followed by an identifier. Both narrowings that fixed it are
    # pinned here.
    "a map whose numbers carry intervals is a document no consultant produces",
    "the document id is written by hand",
)


def selftest() -> int:
    """Prove the detector fires, and prove it stays quiet on policy prose.

    A gate nobody has seen fail is a gate that may be passing because it cannot
    fail. The miss half matters more than the hit half here: a scan that fired
    on CONTRIBUTING.md would be turned off within a week.
    """
    failures: list[str] = []

    for line in SELFTEST_HITS:
        if not scan_line("<selftest>", 1, line, []):
            failures.append(f"no finding on a line that should fire: {line!r}")

    for line in SELFTEST_MISSES:
        hits = scan_line("<selftest>", 1, line, [])
        if hits:
            failures.append(f"fired on policy prose: {line!r} -> {hits[0].reason}")

    if not scan_line("<selftest>", 1, "we shipped it to Contoso last spring", ["Contoso"]):
        failures.append("a denylisted term was not found")

    if failures:
        sys.stderr.write("\n\033[31mBLOCKED: banned-terms selftest [IPH-001]\033[0m\n")
        for failure in failures:
            sys.stderr.write(f"  {failure}\n")
        return 1

    print(
        f"[ip-hygiene] selftest: {len(SELFTEST_HITS)} markers fire, "
        f"{len(SELFTEST_MISSES)} policy lines stay quiet"
    )
    return 0


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--all", action="store_true", help="scan every tracked file")
    mode.add_argument("--staged", action="store_true", help="scan the staged added lines")
    mode.add_argument("--history", action="store_true", help="scan every commit message")
    mode.add_argument("--selftest", action="store_true", help="prove the detector fires")
    args = parser.parse_args(argv)

    if args.selftest:
        return selftest()

    terms = denylist_terms()
    findings = wiring_findings() if args.all else []

    if args.staged:
        hits = scan_staged(terms)
        scope = "the staged added lines"
    elif args.history:
        hits = scan_history(terms)
        scope = "every commit message"
    else:
        hits = scan_tree(terms)
        scope = f"{len(tracked_files())} tracked files"

    if hits or findings:
        sys.stderr.write("\n\033[31mBLOCKED: IP hygiene [IPH-001]\033[0m\n")
        for finding in findings:
            sys.stderr.write(f"  {finding}\n")
        for hit in hits:
            sys.stderr.write(f"  {hit}\n")
        sys.stderr.write(
            "\nThis repository is public and a pushed commit is permanent. Remove the\n"
            "line rather than rewording it, and if it reached a commit that is already\n"
            "pushed, treat it as a disclosure rather than as a lint failure.\n"
        )
        return 1

    if terms:
        print(f"[ip-hygiene] {scope}: clean against {len(terms)} denylisted terms")
    else:
        print(
            f"[ip-hygiene] {scope}: clean against the generic markers. "
            f"SKIP the denylist half: no .ip-denylist in this checkout, which is "
            f"expected on a runner and is a missing local setup step anywhere else"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
