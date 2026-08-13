"""Every recordable commit reaches the changelog, CHANGELOG-1.

The post-commit hook writes the entry, so in the normal case this holds by
construction. It is the abnormal cases that lose entries, and each one is
ordinary: `git commit-tree` writes a commit with no hooks at all, a rebase and
a merge skip the amend on purpose, `--no-verify` skips everything, and an
installed hook that has gone stale runs without the step it never received.

None of those announce themselves. The changelog just quietly lacks a line,
and nobody notices until a release is cut from it. This is what makes the
omission loud, and `sh scripts/changelog-sync.sh --catch-up` is what repairs
it.

The expected section comes from running the sync script rather than from a
second copy of its mapping here. Two copies of a rule drift, and the drift
shows up as a test that passes while the tool it checks does something else.
"""

from __future__ import annotations

import re
import subprocess
import tempfile
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
CHANGELOG = REPO_ROOT / "CHANGELOG.md"
SYNC = REPO_ROOT / "scripts" / "changelog-sync.sh"

#: Conventional Commits 1.0.0, the same shape the commit-msg hook enforces.
_SUBJECT = re.compile(r"^(?P<type>[a-z]+)(?:\((?P<scope>[a-z0-9_-]+)\))?!?: (?P<desc>.+)$")

#: The types that owe an entry. Read from the sync script so the two agree.
_MAPPED = re.compile(r"^\s*(?P<type>[a-z]+)\)\s*head=\"(?P<section>[A-Z][a-z]+)\"", re.MULTILINE)

#: A category heading in a commit body. Only a body naming SECURITY can be
#: routed away from its type's section, so only those need the script run.
_SECURITY_HEADING = re.compile(r"^SECURITY:?[ \t]*$", re.MULTILINE)


def _git(*args: str) -> str:
    return subprocess.run(  # noqa: S603
        ["git", *args], cwd=REPO_ROOT, capture_output=True, text=True, check=True
    ).stdout


def recorded_types() -> dict[str, str]:
    """The type-to-section map, read out of the script that applies it."""
    return {m.group("type"): m.group("section") for m in _MAPPED.finditer(SYNC.read_text("utf-8"))}


def unreleased_entries() -> dict[str, str]:
    """Every bullet under [Unreleased], mapped to the section holding it."""
    text = CHANGELOG.read_text(encoding="utf-8")
    body = text.split("## [Unreleased]", 1)[1].split("\n## [", 1)[0]
    entries, section = {}, None
    for line in body.splitlines():
        if line.startswith("### "):
            section = line[4:].strip()
        elif line.startswith("- ") and section:
            entries[line[2:].strip()] = section
    return entries


def section_the_script_picks(subject: str, body: str) -> str | None:
    """What changelog-sync.sh does with this commit, asked rather than assumed."""
    with tempfile.TemporaryDirectory() as directory:
        target = Path(directory) / "CHANGELOG.md"
        target.write_text(
            "# Changelog\n\n## [Unreleased]\n\n## [0.1.0] - 2026-01-01\n",
            encoding="utf-8",
            newline="\n",
        )
        subprocess.run(  # noqa: S603
            ["sh", str(SYNC), "--file", str(target), "--subject", subject, "--body", body],  # noqa: S607
            cwd=REPO_ROOT,
            capture_output=True,
            check=True,
        )
        for line in target.read_text(encoding="utf-8").splitlines():
            if line.startswith("### "):
                return line[4:].strip()
    return None


#: A record separator that cannot occur inside a commit message. The format
#: argument spells it as git's own escape, because an argv entry cannot carry
#: a NUL byte; the split works on what git writes.
_RECORD_FORMAT = "%x00%x00"
_RECORD = "\x00\x00"


def _commits_since_the_last_tag() -> list[tuple[str, str, str]]:
    """(sha, subject, body) for each commit since the tag, in one git call.

    Reading them a commit at a time costs a process per field, which put this
    file alone over the whole unit tier's runtime budget.
    """
    tag = subprocess.run(  # noqa: S603
        ["git", "describe", "--tags", "--abbrev=0", "--match", "v[0-9]*"],  # noqa: S607
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    ).stdout.strip()
    span = f"{tag}..HEAD" if tag else "HEAD"
    raw = _git("log", "--no-merges", f"--format=%H%x00%s%x00%b{_RECORD_FORMAT}", span)

    commits = []
    for record in raw.split(_RECORD):
        if not record.strip():
            continue
        sha, subject, body = record.lstrip("\n").split("\x00", 2)
        commits.append((sha, subject.strip(), body))
    return commits


def test_every_recordable_commit_since_the_tag_has_an_entry():
    mapped = recorded_types()
    assert mapped, "no type-to-section map found in changelog-sync.sh"
    entries = unreleased_entries()

    missing = []
    for sha, subject, _ in _commits_since_the_last_tag():
        match = _SUBJECT.match(subject)
        if not match or match.group("type") not in mapped:
            continue
        if match.group("desc") not in entries:
            missing.append(f"{sha[:9]} {match.group('desc')[:60]}")

    assert missing == [], (
        f"{len(missing)} commit(s) record nothing in [Unreleased]:\n  "
        + "\n  ".join(missing)
        + "\nRepair with: sh scripts/changelog-sync.sh --catch-up"
    )


def test_a_security_body_is_filed_under_security():
    """The body can move an entry, so the section is checked where it can move.

    Only commits whose body names SECURITY are re-run through the script: every
    other commit is routed by its type alone, which the check above covers.
    """
    mapped = recorded_types()
    entries = unreleased_entries()

    wrong = []
    for sha, subject, body in _commits_since_the_last_tag():
        match = _SUBJECT.match(subject)
        if not match or match.group("type") not in mapped:
            continue
        if not _SECURITY_HEADING.search(body):
            continue
        want = section_the_script_picks(subject, body)
        got = entries.get(match.group("desc"))
        if got is not None and want is not None and got != want:
            wrong.append(f"{sha[:9]} is under {got}, and belongs under {want}")

    assert wrong == [], "\n  ".join(["entries in the wrong section:", *wrong])


def test_the_map_is_read_from_the_script_and_not_guessed():
    """The falsifier for the reader above: a wrong map makes both checks noise."""
    mapped = recorded_types()
    assert mapped.get("fix") == "Fixed"
    assert mapped.get("feat") == "Added"
    assert "docs" not in mapped, "documentation records nothing, so it owes no entry"


@pytest.mark.parametrize(
    ("subject", "body", "expected"),
    [
        ("fix(a): repair it", "", "Fixed"),
        ("feat(a): add it", "", "Added"),
        ("refactor(a): split it", "", "Changed"),
        ("feat(a): add it", "SECURITY\n- one\n- two\n\nUI\n- one\n", "Security"),
        ("feat(a): add it", "UI\n- one\n- two\n\nSECURITY\n- one\n", "Added"),
    ],
)
def test_the_script_routes_a_commit_the_way_this_suite_reads_it(subject, body, expected):
    assert section_the_script_picks(subject, body) == expected
