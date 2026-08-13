#!/usr/bin/env python3
"""Spelling gate: British variants and common misspellings, in prose and in code.

Every rule is read from docs/style/spelling.yml, so the rules have one home and
this script has none. That is the same arrangement the prose gate has with
banned-phrases.yml, and it is what lets a rule change be a diff a reviewer can
read rather than a change buried in a regex.

Usage:

    python scripts/checks/spelling-gate.py                 staged files (git hook)
    python scripts/checks/spelling-gate.py --all           every tracked file (CI)
    python scripts/checks/spelling-gate.py path/to/file    one or more explicit files
    python scripts/checks/spelling-gate.py --commit-msg F  a commit message
    python scripts/checks/spelling-gate.py --selftest      prove the rules still fire

Escape token, on the line that needs it:

    spell-ok <word> <reason>

The reason is not optional. A gate that is easy to silence is not a gate, and
the escape exists for a word that belongs to somebody else: a third-party API
whose own name carries a variant spelling, a quoted title, a URL.

The selftest is not decoration. These rules are regexes over a word list, and a
rule that silently stops matching is worse than no rule, so CI runs the selftest
beside the gate. It asserts both halves: that each family fires on the British
form, and that it leaves cancellation, hypothesis, analysis, specialist, and
totally alone, which are the words a careless stem rule destroys.

Needs PyYAML. Without it the gate reports SKIP and exits 0, matching how the
prose gate treats a missing dependency: CI is the hard backstop and installs it.
"""

from __future__ import annotations

import argparse
import contextlib
import io
import re
import subprocess
import sys
from pathlib import Path

for _stream in (sys.stdout, sys.stderr):
    if isinstance(_stream, io.TextIOWrapper):
        # A stream somebody already replaced has no reconfigure to call, and
        # reconfigure itself raises on an encoding this platform lacks.
        with contextlib.suppress(ValueError):
            _stream.reconfigure(encoding="utf-8")

REPO_ROOT = Path(__file__).resolve().parents[2]
RULES_FILE = REPO_ROOT / "docs" / "style" / "spelling.yml"

RED = "\033[31m"
YELLOW = "\033[33m"
GREEN = "\033[32m"
RESET = "\033[0m"

#: Binary and generated files nothing gains from reading.
SKIP_SUFFIXES = {".png", ".jpg", ".jpeg", ".gif", ".ico", ".woff", ".woff2", ".pdf", ".lock"}

#: `spell-ok colour,licence a line that names the words rather than using them`
#: One escape carries a list, because a sentence that names four spellings
#: needs four exemptions and four tokens on one line cannot be parsed: the
#: reason of the first would swallow the rest.
ESCAPE = re.compile(r"spell-ok\s+([A-Za-z][A-Za-z,\-]*)\s+(\S.*)")


class Rule:
    """One spelling rule: what it matches, and what to write instead.

    The suggestion is built from the word that matched rather than stored, so
    that a form carrying a suffix keeps that suffix in the correction. A
    suggestion that drops it reads as a different word and sends the author to
    fix something they did not write.
    """

    __slots__ = ("pattern", "kind", "wrong", "_stem", "_american")

    def __init__(
        self, pattern: re.Pattern, kind: str, wrong: str, stem: str | None, american: str
    ) -> None:
        self.pattern = pattern
        self.kind = kind
        self.wrong = wrong
        self._stem = stem
        self._american = american

    def suggest(self, word: str) -> str:
        if self._stem is None:
            return self._american
        return re.sub(re.escape(self._stem), self._american, word, count=1, flags=re.IGNORECASE)


def load_rules(path: Path) -> tuple[list[Rule], set[str], dict]:
    import yaml

    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    rules: list[Rule] = []

    suffixes = "|".join(data.get("ise_suffixes") or [])
    for stem in data.get("ise_stems") or []:
        american = stem[:-1] + "z" if stem.endswith("s") else stem
        rules.append(
            Rule(
                re.compile(rf"\b{stem}(?:{suffixes})\b", re.IGNORECASE),
                "british",
                stem + "e",
                stem,
                american,
            )
        )

    for wrong, right in (data.get("british_words") or {}).items():
        rules.append(
            Rule(re.compile(rf"\b{wrong}\b", re.IGNORECASE), "british", wrong, None, right)
        )

    for wrong, right in (data.get("british_stems") or {}).items():
        rules.append(
            Rule(re.compile(re.escape(wrong), re.IGNORECASE), "british", wrong, wrong, right)
        )

    for wrong, right in (data.get("typos") or {}).items():
        rules.append(Rule(re.compile(rf"\b{wrong}\b", re.IGNORECASE), "typo", wrong, None, right))

    return rules, set(data.get("skip_paths") or []), data.get("selftest") or {}


def tracked_files() -> list[str]:
    result = subprocess.run(  # noqa: S603
        ["git", "ls-files"],  # noqa: S607
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    return result.stdout.split() if result.returncode == 0 else []


def staged_files() -> list[str]:
    result = subprocess.run(  # noqa: S603
        ["git", "diff", "--cached", "--name-only", "--diff-filter=ACM"],  # noqa: S607
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    return result.stdout.split() if result.returncode == 0 else []


def check_text(text: str, rules: list[Rule], label: str) -> list[str]:
    """Every finding in one document, as printable lines."""
    findings = []
    for number, line in enumerate(text.splitlines(), start=1):
        excused = set()
        for match in ESCAPE.finditer(line):
            excused.update(word.strip().lower() for word in match.group(1).split(",") if word)
        # The escape token names the word it excuses, so one escape on a line
        # does not silence a second mistake beside it.
        stripped = ESCAPE.sub("", line)
        for rule in rules:
            found = rule.pattern.search(stripped)
            if found is None:
                continue
            word = found.group(0)
            if word.lower() in excused or rule.wrong.lower() in excused:
                continue
            kind = "British spelling" if rule.kind == "british" else "misspelling"
            findings.append(f"{label}:{number}  {kind} {word!r}, use {rule.suggest(word)!r}")
    return findings


def selftest(rules: list[Rule], expectations: dict) -> int:
    """Prove the rules still fire, and still leave the near misses alone.

    The expectations come from the rule file, because a wrong spelling written
    here would be a wrong spelling in a file this gate reads for findings. One
    file holds the rules and the proof, and it is the file the gate skips.
    """
    fires = expectations.get("fires") or {}
    passes = expectations.get("passes") or []
    failures = []

    for wrong, right in fires.items():
        findings = check_text(f"a line with {wrong} in it", rules, "selftest")
        if not findings:
            failures.append(f"no rule fires on {wrong!r}")
        elif right not in findings[0]:
            failures.append(f"{wrong!r} was reported without suggesting {right!r}: {findings[0]}")

    for word in passes:
        findings = check_text(f"a line with {word} in it", rules, "selftest")
        if findings:
            failures.append(f"{word!r} is correct and was reported: {findings[0]}")

    sample = next(iter(fires), None)
    if sample is not None:
        escaped = check_text(
            f"the {sample} call is theirs  spell-ok {sample} a third-party name",
            rules,
            "selftest",
        )
        if escaped:
            failures.append(f"the escape token did not excuse the word: {escaped[0]}")

    if failures:
        sys.stderr.write(f"\n{RED}BLOCKED: the spelling rules do not behave{RESET}\n")
        for failure in failures:
            sys.stderr.write(f"  {failure}\n")
        return 1

    print(
        f"{GREEN}[spelling] selftest: {len(fires)} rules fire, "
        f"{len(passes)} correct words pass, the escape token works{RESET}"
    )
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("paths", nargs="*", help="files to check; default is the staged set")
    parser.add_argument("--all", action="store_true", help="every tracked file")
    parser.add_argument("--commit-msg", metavar="FILE", help="check a commit message")
    parser.add_argument("--selftest", action="store_true", help="prove the rules still fire")
    args = parser.parse_args()

    try:
        import yaml  # noqa: F401
    except ImportError:
        print(f"{YELLOW}[spelling] SKIP: PyYAML is not installed (CI installs it).{RESET}")
        return 0

    if not RULES_FILE.is_file():
        sys.stderr.write(f"BLOCKED: no {RULES_FILE}\n")
        return 1
    rules, skip_paths, expectations = load_rules(RULES_FILE)

    if args.selftest:
        return selftest(rules, expectations)

    findings: list[str] = []

    if args.commit_msg:
        path = Path(args.commit_msg)
        if not path.is_file():
            sys.stderr.write(f"BLOCKED: no commit message at {path}\n")
            return 1
        # Comment lines are git's own, and the trailing diff a verbose commit
        # carries is the diff, not the message.
        body = []
        for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
            if line.startswith("diff --git "):
                break
            if line.startswith("#"):
                continue
            body.append(line)
        findings = check_text("\n".join(body), rules, "COMMIT_MSG")
    else:
        if args.paths:
            names = args.paths
        elif args.all:
            names = tracked_files()
        else:
            names = staged_files()

        for name in names:
            relative = Path(name).as_posix()
            if relative in skip_paths or Path(name).suffix in SKIP_SUFFIXES:
                continue
            path = REPO_ROOT / name if not Path(name).is_absolute() else Path(name)
            if not path.is_file():
                continue
            try:
                text = path.read_text(encoding="utf-8")
            except (UnicodeDecodeError, OSError):
                continue
            findings += check_text(text, rules, relative)

    if findings:
        where = "COMMIT_MSG" if args.commit_msg else "the files checked"
        sys.stderr.write(f"\n{RED}BLOCKED: {len(findings)} spelling findings in {where}{RESET}\n")
        for finding in findings:
            sys.stderr.write(f"  {finding}\n")
        sys.stderr.write(
            "\nFix the word, or excuse it on that line with a reason:\n"
            "    spell-ok <word> <why this spelling is somebody else's>\n"
        )
        return 1

    print(f"{GREEN}[spelling] clean{RESET}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
