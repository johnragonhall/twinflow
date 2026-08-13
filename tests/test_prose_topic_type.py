"""FM-06, a topic type outside the declared set.

Repository policy gates live in scripts/checks and are not part of any
distribution, so their tests live here rather than inside a package.

The sentence-limit profiles are keyed by topic type. A lookup that misses
returns no profile, and every rule scoped to a type is skipped for that page,
so an invented type takes a document out of the linter and the run still
reports no error. The failure is silent in the worst direction: the page looks
checked.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
GATE = REPO_ROOT / "scripts" / "checks" / "prose-gate.py"
STANDARD = REPO_ROOT / "docs" / "DOCUMENTATION-STANDARD.md"


def _load():
    spec = importlib.util.spec_from_file_location("prose_gate", GATE)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


gate = _load()

PAGE = """---
title: A page
description: A description long enough to clear the front matter word floor this gate applies.
topic_type: {topic_type}
audience: contributors
---

# A page

A short sentence.
"""


def findings(topic_type: str) -> list[tuple]:
    """Run the front matter check in process, the way the DASH-02 cases do."""
    document = gate.Document("sample.md", PAGE.format(topic_type=topic_type))
    collected: list[tuple] = []
    gate.check_front_matter(document, {"min_words": 10, "max_words": 30}, set(), collected)
    return collected


def rules(topic_type: str) -> set[str]:
    return {item[2] for item in findings(topic_type)}


def test_an_undeclared_topic_type_is_refused():
    """Regression. `procedure` read as a valid type and silenced the page.

    docs/testing-policy.md shipped with it. The gate reported no error while
    LEN-01, LEN-02, and every type-scoped rule were skipped for that file, and
    two sentences over the ceiling sat in it unreported.
    """
    assert "FM-06" in rules("procedure")


def test_the_finding_is_an_error_rather_than_a_warning():
    # A warning would leave the page unchecked and the run green, which is the
    # state this rule exists to end.
    reported = [item for item in findings("procedure") if item[2] == "FM-06"]
    assert reported and reported[0][3] == gate.ERROR


@pytest.mark.parametrize("topic_type", sorted(gate.TOPIC_TYPES))
def test_every_declared_topic_type_passes(topic_type):
    assert "FM-06" not in rules(topic_type)


def test_the_declared_set_is_the_one_the_standard_names():
    # The standard is the owner. If it gains a fourth type this fails rather
    # than letting the gate quietly refuse a type the standard allows.
    text = STANDARD.read_text(encoding="utf-8")
    for topic_type in gate.TOPIC_TYPES:
        assert topic_type in text, f"the gate accepts {topic_type!r} and the standard omits it"


def test_every_page_in_the_tree_uses_a_declared_type():
    # The check is only worth having if the tree satisfies it, and a page that
    # slipped through before the rule existed would fail here rather than in a
    # contributor's commit.
    offenders = []
    for path in list(REPO_ROOT.glob("docs/**/*.md")) + list(REPO_ROOT.glob("*.md")):
        for line in path.read_text(encoding="utf-8", errors="replace").splitlines()[:10]:
            if line.startswith("topic_type:"):
                value = line.split(":", 1)[1].strip()
                if value not in gate.TOPIC_TYPES:
                    offenders.append(f"{path.relative_to(REPO_ROOT).as_posix()}: {value}")
                break
    assert offenders == [], f"pages naming an undeclared topic type: {offenders}"


def test_the_sentence_limits_are_keyed_by_topic_type():
    """The mechanism behind the defect, pinned against the file that holds it.

    FM-06 matters only because a lookup miss means no sentence checks. The
    limits live in docs/style/, keyed by topic type, so a rewrite that stops
    keying them that way fails here and the rule can be reconsidered rather
    than left guarding nothing.
    """
    limits_file = REPO_ROOT / "docs" / "style" / "limits.yml"
    if not limits_file.is_file():
        candidates = sorted((REPO_ROOT / "docs" / "style").glob("*.yml"))
        limits_file = next(
            (c for c in candidates if "limit" in c.name or "sentence" in c.name), None
        )
    if limits_file is None or not limits_file.is_file():
        # The profiles are defined in the gate itself rather than in a file.
        source = GATE.read_text(encoding="utf-8")
        assert "limits.get(doc.topic_type" in source, (
            "the sentence limits are no longer looked up by topic type, so FM-06 "
            "guards nothing and should be reconsidered"
        )
        return

    text = limits_file.read_text(encoding="utf-8")
    assert any(f"{topic_type}:" in text for topic_type in gate.TOPIC_TYPES), (
        f"{limits_file.name} keys no profile by a declared topic type"
    )
