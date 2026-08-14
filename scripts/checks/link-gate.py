#!/usr/bin/env python3
"""Relative link gate, the docs half of VAL-GATE-DOC-001.

Every relative Markdown link and image in every tracked `.md` file resolves to
a file that exists, spelled the way the file system spells it, and every anchor
names a heading the target document actually carries.

    LINK-1  a relative link resolves to nothing on disk
    LINK-2  an image resolves to nothing on disk
    LINK-3  an anchor names no heading in the Markdown file it points at
    LINK-4  a reference-style link uses a label nothing defines
    LINK-5  a target climbs out of the repository root
    LINK-6  a target exists but is spelled with different case

LINK-6 is the one a local run cannot see for itself. Windows and macOS resolve
`docs/Gates.md` to `docs/gates.md` and the link works; the published site runs
on a case-sensitive file system and serves a 404. So the check compares the
spelling against the directory listing rather than asking whether the path
exists.

Absolute targets are out of scope. An `http`, `https`, or `mailto` target is
somebody else's uptime, and a gate that fetches URLs fails on a network rather
than on a defect.

Usage:

    python scripts/checks/link-gate.py            every tracked .md file
    python scripts/checks/link-gate.py PATH ...   named files
    python scripts/checks/link-gate.py --selftest prove each refusal fires

The selftest is the point of doctrine D-12. A link checker over a tree with no
broken links reports the same green whether it works or whether it parses
nothing at all, so each rule is fired against a document that breaks it and a
clean document is checked for silence.
"""

from __future__ import annotations

import argparse
import contextlib
import io
import ntpath
import posixpath
import re
import subprocess
import sys
from pathlib import Path, PurePosixPath

for _stream in (sys.stdout, sys.stderr):
    if isinstance(_stream, io.TextIOWrapper):
        # reconfigure raises on an encoding this platform lacks.
        with contextlib.suppress(ValueError):
            _stream.reconfigure(encoding="utf-8")

REPO_ROOT = Path(__file__).resolve().parents[2]

RED = "\033[31m"
GREEN = "\033[32m"
RESET = "\033[0m"

#: Schemes that leave this repository. A target carrying one of them is not a
#: path and nothing here can decide whether it resolves.
EXTERNAL = re.compile(r"^(?:[a-z][a-z0-9+.-]*:|//)", re.IGNORECASE)

#: An inline link or image: `[text](target)` and `![alt](target)`, with the
#: optional title Markdown allows after the target.
INLINE = re.compile(
    r"(?P<bang>!?)\[(?P<text>(?:[^\]\[]|\[[^\]]*\])*)\]\(\s*(?P<target>[^()\s]*|<[^>]*>)"
    r"(?:\s+(?P<title>\"[^\"]*\"|'[^']*'|\([^)]*\)))?\s*\)"
)

#: A reference-style use, `[text][label]` or the collapsed `[text][]`, and the
#: definition that has to exist for it, `[label]: target`.
REFERENCE_USE = re.compile(r"(?P<bang>!?)\[(?P<text>[^\]\[]+)\]\[(?P<label>[^\]]*)\]")
REFERENCE_DEF = re.compile(r"^ {0,3}\[(?P<label>[^\]]+)\]:\s*(?P<target>\S+)")

#: An anchor a document declares for itself rather than deriving from a
#: heading: the HTML form, and the attribute-list form the docs site accepts.
HTML_ANCHOR = re.compile(r"<a\s[^>]*(?:id|name)\s*=\s*[\"']([^\"']+)[\"']", re.IGNORECASE)
ATTR_ANCHOR = re.compile(r"\{#([A-Za-z0-9_-]+)\}")

FENCE = re.compile(r"^\s*(```+|~~~+)")
HTML_COMMENT = re.compile(r"<!--.*?-->", re.DOTALL)

MARKDOWN_SUFFIXES = frozenset({".md", ".markdown"})


class Finding:
    """One link that does not resolve, with the file and line it sits on."""

    __slots__ = ("rule", "where", "message")

    def __init__(self, rule: str, where: str, message: str) -> None:
        self.rule = rule
        self.where = where
        self.message = message

    def render(self) -> str:
        return f"  [{self.rule}] {self.where}\n      {self.message}"


class Link:
    """One parsed link, before anything is asked of the file system."""

    __slots__ = ("target", "line", "is_image", "raw")

    def __init__(self, target: str, line: int, *, is_image: bool, raw: str) -> None:
        self.target = target
        self.line = line
        self.is_image = is_image
        self.raw = raw


class Tree:
    """The file system a document is checked against.

    An interface rather than a bare `Path.exists`, so the selftest can hand the
    checker a tree it wrote by hand. A checker that can only run against the
    real repository is a checker whose refusals nobody can fire on purpose.
    """

    def exists(self, relative: str) -> bool:
        raise NotImplementedError

    def case_exact(self, relative: str) -> bool:
        raise NotImplementedError

    def text(self, relative: str) -> str | None:
        raise NotImplementedError


def _is_safe_relative(name: str) -> bool:
    """Whether this text names a path inside a tree, read as text.

    A link target and a command-line argument are both written by someone other
    than this gate, and `root / name` takes an absolute path whole rather than
    joining it. `ntpath` reads the Windows spellings as well, so a drive-
    relative `C:x` and a UNC share are refused on every platform rather than
    only where they happen to mean something.
    """
    if not name or name.isspace():
        return False
    if posixpath.isabs(name) or ntpath.isabs(name):
        return False
    if ntpath.splitdrive(name)[0]:
        return False
    parts = PurePosixPath(name.replace("\\", "/")).parts
    return ".." not in parts


class DiskTree(Tree):
    """The repository as it sits on disk.

    Every path this reads is resolved and confined to the root. A link target
    and a command-line argument are both text this gate did not write, and
    `root / relative` follows `..` out of the repository and takes an absolute
    path whole. Confining here keeps that true for every caller rather than for
    the ones that remembered.
    """

    def __init__(self, root: Path) -> None:
        self.root = root.resolve()
        self._listing: dict[str, set[str]] = {}

    def _within(self, relative: str) -> Path | None:
        """The path this names inside the repository, or nothing if it escapes.

        Two checks, in this order, because each catches what the other cannot.
        The first reads the text before it becomes a path at all: a name that is
        absolute, that names a drive or a share, or that carries a `..` segment
        is refused without ever being joined to the root. The second reads the
        resolved path afterwards, which is what catches a symlink that sits
        inside the repository and points outside it.
        """
        if not _is_safe_relative(relative):
            return None
        try:
            candidate = (self.root / relative).resolve()
        except (OSError, ValueError):
            return None
        if candidate != self.root and self.root not in candidate.parents:
            return None
        return candidate

    def exists(self, relative: str) -> bool:
        candidate = self._within(relative)
        return candidate is not None and candidate.exists()

    def case_exact(self, relative: str) -> bool:
        """Whether every segment is spelled the way the directory spells it.

        Walked segment by segment against the real listing, because
        `Path.exists` on Windows and macOS answers yes to a path that a
        case-sensitive server answers 404 to.
        """
        if self._within(relative) is None:
            return False
        current = self.root
        for segment in PurePosixPath(relative).parts:
            names = self._names(current)
            if names is None or segment not in names:
                return False
            current = current / segment
        return True

    def _names(self, directory: Path) -> set[str] | None:
        key = directory.as_posix()
        if key not in self._listing:
            try:
                self._listing[key] = {child.name for child in directory.iterdir()}
            except (OSError, ValueError):
                return None
        return self._listing[key]

    def text(self, relative: str) -> str | None:
        path = self._within(relative)
        if path is None or not path.is_file():
            return None
        try:
            return path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            return None


class FakeTree(Tree):
    """A tree written out in a test, keyed by repository-relative posix path."""

    def __init__(self, files: dict[str, str]) -> None:
        self.files = dict(files)
        self.directories = {
            parent.as_posix()
            for name in files
            for parent in PurePosixPath(name).parents
            if parent.as_posix() not in (".", "")
        }

    def exists(self, relative: str) -> bool:
        """Case-insensitive, which is what a developer's laptop answers."""
        folded = relative.casefold()
        return any(name.casefold() == folded for name in self.files) or any(
            name.casefold() == folded for name in self.directories
        )

    def case_exact(self, relative: str) -> bool:
        return relative in self.files or relative in self.directories

    def text(self, relative: str) -> str | None:
        return self.files.get(relative)


def strip_code(text: str) -> str:
    """Blank out fenced blocks and HTML comments, keeping the line count.

    A link inside a fence is sample text, and a link inside a comment is not
    published. Blanking rather than deleting keeps every reported line number
    equal to the line number in the file.
    """
    text = HTML_COMMENT.sub(lambda match: "\n" * match.group(0).count("\n"), text)

    out: list[str] = []
    fence: str | None = None
    for line in text.split("\n"):
        opener = FENCE.match(line)
        if fence is None and opener:
            fence = opener.group(1)[0] * 3
            out.append("")
            continue
        if fence is not None:
            if opener and opener.group(1).startswith(fence):
                fence = None
            out.append("")
            continue
        out.append(line)
    return "\n".join(out)


def strip_inline_code(line: str) -> str:
    """Blank out inline code spans, keeping the length."""
    return re.sub(r"`[^`]*`", lambda match: " " * len(match.group(0)), line)


def parse_links(text: str) -> tuple[list[Link], list[tuple[str, int]], set[str]]:
    """Every inline link, every reference use, and every label defined.

    Returns `(links, reference_uses, defined_labels)`. Reference definitions
    contribute their own target to `links`, because a definition nothing
    resolves is as broken as an inline link nothing resolves.
    """
    links: list[Link] = []
    uses: list[tuple[str, int]] = []
    defined: set[str] = set()

    for number, raw in enumerate(strip_code(text).split("\n"), start=1):
        line = strip_inline_code(raw)

        definition = REFERENCE_DEF.match(line)
        if definition:
            defined.add(definition["label"].strip().lower())
            links.append(
                Link(
                    definition["target"].strip(),
                    number,
                    is_image=False,
                    raw=definition.group(0).strip(),
                )
            )
            continue

        for match in INLINE.finditer(line):
            target = match["target"].strip()
            if target.startswith("<") and target.endswith(">"):
                target = target[1:-1].strip()
            links.append(Link(target, number, is_image=bool(match["bang"]), raw=match.group(0)))

        for match in REFERENCE_USE.finditer(line):
            label = (match["label"] or match["text"]).strip().lower()
            uses.append((label, number))

    return links, uses, defined


def slug(heading: str) -> str:
    """The anchor a heading gets, by the rule GitHub and mkdocs agree on.

    Formatting is removed, then everything that is not a word character, a
    space, or a hyphen, then the spaces become hyphens. The two renderers
    disagree on exotic headings; they agree on every heading in this tree, and
    a disagreement shows up as a finding rather than as a silent pass.
    """
    text = re.sub(r"<[^>]+>", "", heading)
    text = ATTR_ANCHOR.sub("", text)
    text = re.sub(r"`([^`]*)`", r"\1", text)
    text = re.sub(r"!?\[([^\]]*)\]\([^)]*\)", r"\1", text)
    text = re.sub(r"!?\[([^\]]*)\]\[[^\]]*\]", r"\1", text)
    text = re.sub(r"[*_~]", "", text)
    text = text.strip().lower()
    text = re.sub(r"[^\w\- ]", "", text)
    return re.sub(r"\s+", "-", text).strip("-")


def anchors(text: str) -> set[str]:
    """Every anchor a document offers: its headings, and its explicit ids."""
    found: set[str] = set()
    seen: dict[str, int] = {}

    for line in strip_code(text).split("\n"):
        heading = re.match(r"^ {0,3}(#{1,6})\s+(?P<title>.+?)\s*#*\s*$", line)
        if heading:
            base = slug(heading["title"])
            if base:
                count = seen.get(base, 0)
                found.add(base if count == 0 else f"{base}-{count}")
                seen[base] = count + 1
        for explicit in HTML_ANCHOR.finditer(line):
            found.add(explicit.group(1))
        for explicit in ATTR_ANCHOR.finditer(line):
            found.add(explicit.group(1))

    return found


def _normalize(source: str, target: str) -> str | None:
    """Resolve one target against the file that carries it.

    Returns the repository-relative posix path, or None when the target climbs
    out of the repository.
    """
    parts = PurePosixPath(source).parent / target
    resolved: list[str] = []
    for part in parts.parts:
        if part == ".":
            continue
        if part == "..":
            if not resolved:
                return None
            resolved.pop()
            continue
        resolved.append(part)
    return "/".join(resolved)


def check_document(text: str, source: str, tree: Tree) -> list[Finding]:
    """Every relative link in one document, checked against one tree."""
    findings: list[Finding] = []
    links, uses, defined = parse_links(text)
    own_anchors = anchors(text)

    for label, number in uses:
        if label not in defined:
            findings.append(
                Finding(
                    "LINK-4",
                    f"{source}:{number}",
                    f"reference label [{label}] has no definition in this file, so the "
                    "link renders as literal brackets",
                )
            )

    for link in links:
        target = link.target
        if not target or EXTERNAL.match(target):
            continue

        path_part, _, fragment = target.partition("#")
        path_part = path_part.split("?", 1)[0]
        rule = "LINK-2" if link.is_image else "LINK-1"

        if not path_part:
            if fragment and fragment not in own_anchors:
                findings.append(
                    Finding(
                        "LINK-3",
                        f"{source}:{link.line}",
                        f"#{fragment} names no heading in this file. "
                        f"{_near(fragment, own_anchors)}",
                    )
                )
            continue

        relative = _normalize(source, path_part)
        if relative is None:
            findings.append(
                Finding(
                    "LINK-5",
                    f"{source}:{link.line}",
                    f"{path_part} climbs above the repository root, so it resolves to "
                    "whatever sits beside the clone rather than to anything committed",
                )
            )
            continue

        if not tree.exists(relative):
            findings.append(
                Finding(
                    rule,
                    f"{source}:{link.line}",
                    f"{path_part} resolves to {relative}, and nothing is there",
                )
            )
            continue

        if not tree.case_exact(relative):
            findings.append(
                Finding(
                    "LINK-6",
                    f"{source}:{link.line}",
                    f"{relative} exists under a different case. This resolves on a "
                    "case-insensitive file system and serves a 404 on the published site",
                )
            )
            continue

        if not fragment or PurePosixPath(relative).suffix.lower() not in MARKDOWN_SUFFIXES:
            continue

        body = tree.text(relative)
        if body is None:
            continue
        available = anchors(body)
        if fragment not in available:
            findings.append(
                Finding(
                    "LINK-3",
                    f"{source}:{link.line}",
                    f"#{fragment} names no heading in {relative}. {_near(fragment, available)}",
                )
            )

    return findings


def _near(fragment: str, available: set[str]) -> str:
    """The closest anchors that do exist, so a typo is one line from its fix."""
    import difflib

    close = difflib.get_close_matches(fragment, sorted(available), n=3, cutoff=0.6)
    if close:
        return "Closest: " + ", ".join(f"#{item}" for item in close)
    return f"That file offers {len(available)} anchor(s)"


def tracked_markdown() -> list[str]:
    """Every tracked `.md` path, from git rather than from a glob.

    A glob walks build output and vendored trees; the gate is about the files
    this repository publishes.
    """
    result = subprocess.run(
        ["git", "ls-files", "*.md"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        return []
    return [line.strip() for line in result.stdout.splitlines() if line.strip()]


#: Each case is (rule, description, files, entry). The checker runs over
#: `entry` inside a tree built from `files`, and the case fails when the named
#: rule stays quiet.
SELFTEST_CASES: tuple[tuple[str, str, dict[str, str], str], ...] = (
    (
        "LINK-1",
        "a link to a file that is not there",
        {"docs/a.md": "# A\n\nSee [the plan](plan.md).\n"},
        "docs/a.md",
    ),
    (
        "LINK-2",
        "an image that is not there",
        {"docs/a.md": "# A\n\n![a diagram](img/flow.png)\n"},
        "docs/a.md",
    ),
    (
        "LINK-3",
        "an anchor no heading in the target file carries",
        {
            "docs/a.md": "# A\n\nSee [section two](b.md#the-missing-part).\n",
            "docs/b.md": "# B\n\n## The first part\n",
        },
        "docs/a.md",
    ),
    (
        "LINK-3",
        "a same-file anchor no heading carries",
        {"docs/a.md": "# A\n\nSee [below](#no-such-heading).\n\n## Something else\n"},
        "docs/a.md",
    ),
    (
        "LINK-4",
        "a reference label nothing defines",
        {"docs/a.md": "# A\n\nSee [the plan][plan].\n"},
        "docs/a.md",
    ),
    (
        "LINK-5",
        "a target that climbs out of the repository",
        {"docs/a.md": "# A\n\nSee [outside](../../secrets.md).\n"},
        "docs/a.md",
    ),
    (
        "LINK-6",
        "a target whose case does not match the file on disk",
        {
            "docs/a.md": "# A\n\nSee [the gates](Gates.md).\n",
            "docs/gates.md": "# Gates\n",
        },
        "docs/a.md",
    ),
)

#: A document that uses every construct the checker parses and breaks nothing.
#: Without it a checker that reported every link as broken would pass the cases
#: above and fail the whole tree.
CLEAN_FILES: dict[str, str] = {
    "docs/a.md": (
        "# A\n\n"
        "## The first part\n\n"
        "See [B](b.md), [a section of B](b.md#the-only-part), and\n"
        "[the first part](#the-first-part).\n\n"
        "![a diagram](img/flow.png)\n\n"
        "A reference [link][plan] and a bare [collapsed][] one.\n\n"
        "An external [site](https://example.com/nothing.md) and a\n"
        "[mail](mailto:nobody@example.com) target.\n\n"
        "```\n"
        "[not a link](nowhere.md)\n"
        "```\n\n"
        "Inline `[not a link](nowhere.md)` too.\n\n"
        "<!-- [commented out](nowhere.md) -->\n\n"
        "[plan]: b.md\n"
        "[collapsed]: b.md\n"
    ),
    "docs/b.md": "# B\n\n## The only part\n",
    "docs/img/flow.png": "",
}


def selftest() -> int:
    """Fire every rule, then check that a clean document stays quiet."""
    failures: list[str] = []

    for rule, description, files, entry in SELFTEST_CASES:
        tree = FakeTree(files)
        fired = {finding.rule for finding in check_document(files[entry], entry, tree)}
        if rule not in fired:
            failures.append(
                f"{rule} did not fire on: {description} (fired: {sorted(fired) or 'nothing'})"
            )

    clean = FakeTree(CLEAN_FILES)
    noise = check_document(CLEAN_FILES["docs/a.md"], "docs/a.md", clean)
    if noise:
        failures.append(
            "a document with no broken link reported: "
            + ", ".join(f"{f.rule} {f.message}" for f in noise)
        )

    # The anchor rule is the one most likely to rot into a permanent pass, so
    # the slug function is asserted directly as well as through a document.
    for heading, expected in (
        ("## 1. Before you start: what is built", "1-before-you-start-what-is-built"),
        ("### Why `MPL-2.0` is accepted", "why-mpl-20-is-accepted"),
        ("# twinflow-kernel API", "twinflow-kernel-api"),
    ):
        produced = slug(heading.lstrip("# "))
        if produced != expected:
            failures.append(f"slug({heading!r}) produced {produced!r}, expected {expected!r}")

    if failures:
        sys.stderr.write(f"\n{RED}BLOCKED: link gate selftest [DOC-001]{RESET}\n")
        for failure in failures:
            sys.stderr.write(f"  {failure}\n")
        return 1

    print(
        f"{GREEN}[links] selftest: {len(SELFTEST_CASES)} cases fire their rule, "
        f"and a document with no broken link stays quiet{RESET}"
    )
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("paths", nargs="*", help="markdown files to check")
    parser.add_argument("--selftest", action="store_true", help="prove each refusal fires")
    args = parser.parse_args(argv)

    if args.selftest:
        return selftest()

    if args.paths:
        sources = []
        for item in args.paths:
            path = Path(item).resolve()
            if not path.is_relative_to(REPO_ROOT):
                sys.stderr.write(f"{item} is outside the repository\n")
                return 2
            sources.append(path.relative_to(REPO_ROOT).as_posix())
    else:
        sources = tracked_markdown()

    if not sources:
        sys.stderr.write(
            f"\n{RED}BLOCKED: no tracked Markdown file to check [DOC-001]{RESET}\n"
            "  A link gate that reads nothing reports the same green as one that\n"
            "  read every file and found nothing wrong.\n"
        )
        return 1

    tree = DiskTree(REPO_ROOT)
    findings: list[Finding] = []
    links = 0

    for source in sources:
        body = tree.text(source)
        if body is None:
            findings.append(Finding("LINK-0", source, "this file does not read as UTF-8 text"))
            continue
        parsed, _, _ = parse_links(body)
        links += sum(1 for link in parsed if link.target and not EXTERNAL.match(link.target))
        findings += check_document(body, source, tree)

    if findings:
        sys.stderr.write(f"\n{RED}BLOCKED: a relative link resolves to nothing [DOC-001]{RESET}\n")
        for finding in findings:
            sys.stderr.write(finding.render() + "\n")
        sys.stderr.write(
            "\nVAL-GATE-DOC-001 is falsified by a broken link. Fix the target, or\n"
            "point the link at the file that holds the section now.\n"
        )
        return 1

    print(
        f"[links] {len(sources)} markdown files, {links} relative links and images, "
        f"every one resolving to a committed file"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
