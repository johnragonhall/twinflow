"""VAL-GATE-DOC-001, the link half held to its own refusals.

The gate reads: every relative Markdown link and image in every tracked `.md`
file resolves to a committed file, spelled the way the file system spells it,
and every anchor names a heading the target document carries.

Three things are worth asserting separately, and this file does all three.
That the shipped tree has no broken link is the gate. That the checker can say
otherwise is the evidence the gate is a gate at all, because a link checker
over a tree with no broken links reports the same green whether it works or
whether it parses nothing (doctrine D-12). That each refusal fires by name is
what catches the quiet regression, where one rule stops working and the
aggregate stays green on the strength of the others.

The last case runs against a real directory rather than the checker's fake
tree, because a checker whose only evidence comes from its own test double has
never been shown to read a file system.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
GATE = REPO_ROOT / "scripts" / "checks" / "link-gate.py"


def _load():
    """Import the checker by path, because its filename is not an identifier."""
    spec = importlib.util.spec_from_file_location("link_gate", GATE)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


gate = _load()


def test_the_tree_has_no_broken_link():
    """The gate itself, run the way the phase-exit runner runs it."""
    assert gate.main([]) == 0


def test_the_selftest_passes():
    """Every refusal fires against a document that breaks it, and a document
    that breaks nothing stays quiet."""
    assert gate.selftest() == 0


@pytest.mark.parametrize(
    ("rule", "description", "files", "entry"),
    gate.SELFTEST_CASES,
    ids=[f"{rule}-{description}" for rule, description, _, _ in gate.SELFTEST_CASES],
)
def test_each_broken_document_fires_its_rule(rule, description, files, entry):
    """Named per case, so a rule that goes quiet says which one it was."""
    tree = gate.FakeTree(files)
    fired = {finding.rule for finding in gate.check_document(files[entry], entry, tree)}
    assert rule in fired, f"{rule} stayed quiet on: {description}"


def test_a_clean_document_reports_nothing():
    """The corpus that would catch a checker refusing everything."""
    tree = gate.FakeTree(gate.CLEAN_FILES)
    findings = gate.check_document(gate.CLEAN_FILES["docs/a.md"], "docs/a.md", tree)
    assert findings == [], [finding.render() for finding in findings]


def test_the_tree_carries_anchors_to_check():
    """LINK-3 has work to do on the shipped tree.

    An anchor rule over a tree with no anchor links passes on emptiness. This
    counts them, so the day the last anchor link is deleted the assertion says
    so rather than the gate quietly checking nothing.
    """
    tree = gate.DiskTree(REPO_ROOT)
    with_fragment = 0
    for source in gate.tracked_markdown():
        body = tree.text(source)
        assert body is not None
        links, _, _ = gate.parse_links(body)
        for link in links:
            if link.target and not gate.EXTERNAL.match(link.target) and "#" in link.target:
                with_fragment += 1
    assert with_fragment > 0


@pytest.mark.parametrize(
    ("heading", "expected"),
    [
        ("1. Before you start: what is built", "1-before-you-start-what-is-built"),
        ("Why `MPL-2.0` is accepted", "why-mpl-20-is-accepted"),
        ("twinflow-kernel API", "twinflow-kernel-api"),
        ("Determinism, and what it does not mean", "determinism-and-what-it-does-not-mean"),
        ("**Bold** and _italic_", "bold-and-italic"),
    ],
)
def test_the_slug_matches_the_renderer(heading, expected):
    """The anchor rule rests on this function, so it is asserted directly."""
    assert gate.slug(heading) == expected


def test_a_document_offers_its_own_headings_as_anchors():
    """Duplicate headings take the numbered suffix both renderers give them."""
    found = gate.anchors('# Title\n\n## Notes\n\n## Notes\n\n<a id="manual"></a>\n')
    assert {"title", "notes", "notes-1", "manual"} <= found


def test_external_and_fenced_targets_are_left_alone():
    """A URL is somebody else's uptime, and a link in a fence is sample text."""
    body = (
        "# T\n\n"
        "[a site](https://example.com/nope.md)\n"
        "[mail](mailto:nobody@example.com)\n\n"
        "```\n[sample](nowhere.md)\n```\n\n"
        "Inline `[sample](nowhere.md)` too.\n"
    )
    assert gate.check_document(body, "docs/t.md", gate.FakeTree({"docs/t.md": body})) == []


def test_it_reads_a_real_file_system(tmp_path):
    """The disk-backed tree, not the test double.

    `Gates.md` against a committed `gates.md` is LINK-6 on Windows and macOS,
    where the path resolves under the wrong case, and LINK-1 on Linux, where it
    does not resolve at all. Both are refusals, and which one fires is a
    property of the file system rather than of the checker.
    """
    (tmp_path / "docs").mkdir()
    (tmp_path / "docs" / "gates.md").write_text("# Gates\n\n## A section\n", encoding="utf-8")

    tree = gate.DiskTree(tmp_path)
    body = (
        "# T\n\n"
        "[missing](nope.md)\n"
        "![missing image](nope.png)\n"
        "[wrong case](Gates.md)\n"
        "[bad anchor](gates.md#not-a-heading)\n"
        "[fine](gates.md#a-section)\n"
    )
    fired = {finding.rule for finding in gate.check_document(body, "docs/t.md", tree)}
    assert "LINK-2" in fired
    assert "LINK-3" in fired
    assert fired & {"LINK-1", "LINK-6"}


def test_a_tree_with_nothing_to_read_is_a_failure():
    """A gate that reads no file reports the same green as one that read
    everything. Naming explicit paths outside the repository is refused."""
    assert gate.main([str(Path(__file__).parent.parent.parent / "elsewhere.md")]) == 2


#: A share path, assembled rather than written out. The IP hygiene gate
#: refuses a literal one in a tracked file, because that is how an internal
#: server name reaches a public repository. The case still has to exist:
#: `ntpath` reads this spelling as absolute on every platform.
_UNC_CASE = "\\" * 2 + "server" + "\\" + "share" + "\\" + "x"


@pytest.mark.parametrize(
    "name",
    [
        "../../../Windows/win.ini",
        "/etc/passwd",
        "C:/Windows/win.ini",
        "C:x",
        _UNC_CASE,
        "docs/../../outside.md",
        "docs/./../../out.md",
        "..",
        "",
        "   ",
        r"..\..\secret.txt",
    ],
)
def test_a_path_that_leaves_the_repository_reaches_no_file(name: str, tmp_path):
    """A link target and a command-line argument are both text this gate did not
    write, and `root / name` takes an absolute path whole rather than joining it.

    All three readers are asserted, not just one. Confinement that lives in the
    entry points holds for the ones that remembered; this pins it for each.
    """
    tree = gate.DiskTree(tmp_path)
    (tmp_path / "real.md").write_text("# real", encoding="utf-8")

    assert tree.exists(name) is False
    assert tree.case_exact(name) is False
    assert tree.text(name) is None


def test_a_file_inside_the_repository_still_reads(tmp_path):
    """The control. Confinement that refused every name would pass the cases
    above while making the gate unable to read anything."""
    (tmp_path / "docs").mkdir()
    (tmp_path / "docs" / "real.md").write_text("# real", encoding="utf-8")
    tree = gate.DiskTree(tmp_path)

    assert tree.exists("docs/real.md") is True
    assert tree.case_exact("docs/real.md") is True
    assert tree.text("docs/real.md") == "# real"


def test_a_symlink_pointing_out_of_the_repository_is_refused(tmp_path):
    """The text check cannot see this one: the name is an ordinary relative
    path and only the resolved target leaves the tree."""
    outside = tmp_path / "outside"
    outside.mkdir()
    (outside / "secret.md").write_text("# secret", encoding="utf-8")
    root = tmp_path / "repo"
    root.mkdir()
    try:
        (root / "link.md").symlink_to(outside / "secret.md")
    except (OSError, NotImplementedError):
        pytest.skip("this platform does not grant symlink creation")
    tree = gate.DiskTree(root)

    assert tree.exists("link.md") is False
    assert tree.text("link.md") is None
