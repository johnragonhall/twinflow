"""The contributor agreement gate CLA-001, milestone C13.

CLA.md section 7 publishes three checks and says a pull request failing any of
them does not merge. This holds the checker to that, and holds the workflow to
calling the checker rather than carrying a second implementation of the rules.

Two properties are worth naming, because both were defects the first time:

    the expression has one home      section 7 publishes the expression a
                                     signature matches, and the checker reads
                                     it from there. A copy in the checker is a
                                     copy that disagrees with the document a
                                     contributor read
    the checks run outside a runner  they lived as inline awk and grep inside
                                     a job, so nobody could run them before
                                     pushing and the phase-exit runner could
                                     not run them at all

The trailer check is deliberately not run over this repository's own history.
The owner holds the copyright, so section 7 gives them no license to grant and
no signature to give, and none of their commits carries the trailer. A gate
asserting otherwise would fail on every commit and would be asserting the
wrong thing, so the range belongs to a pull request and the workflow supplies
it.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest
import yaml

REPO_ROOT = Path(__file__).resolve().parents[1]
GATE = REPO_ROOT / "scripts" / "checks" / "cla-gate.py"
CLA = REPO_ROOT / "CLA.md"
LINT_WORKFLOW = REPO_ROOT / ".github" / "workflows" / "lint.yml"

sys.path.insert(0, str(GATE.parent))
cla_gate = __import__("cla-gate")  # noqa: N816  the script is kebab-case like its siblings


def run(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(GATE), *args],
        capture_output=True,
        text=True,
        cwd=REPO_ROOT,
    )


def test_the_gate_refuses_what_it_is_meant_to_refuse():
    """The selftest is the evidence each check can fail at all (D-12)."""
    result = run("--selftest")
    assert result.returncode == 0, result.stdout + result.stderr


def test_the_published_document_passes_its_own_check():
    result = run("line-shape")
    assert result.returncode == 0, result.stdout + result.stderr


@pytest.mark.parametrize(
    ("line", "why"),
    [
        ("- @octocat 2026-8-9", "a date that is not zero padded"),
        ("- @octocat 26-08-09", "a two digit year"),
        ("- octocat 2026-08-09", "a handle with no at sign"),
        ("- @octocat", "no date at all"),
        ("- @octocat 2026-08-09 maintainer", "a trailing word"),
        ("- @has a space 2026-08-09", "a handle carrying a space"),
        ("-@octocat 2026-08-09", "no space after the list marker"),
    ],
)
def test_line_shape_refuses_a_malformed_signature(line, why):
    """Each of these was watched failing before the checker existed."""
    document = _document_with(line)
    assert cla_gate.check_line_shape(document) == [line], why


def test_line_shape_accepts_the_worked_example_section_7_publishes():
    assert cla_gate.check_line_shape(_document_with("- @octocat 2026-08-09")) == []


def test_prose_inside_the_section_is_not_read_as_a_signature():
    """A sentence is not a malformed signature, and reporting it as one sends
    somebody to fix prose that was never a signature."""
    document = _document_with("Each line below is one signature.")
    assert cla_gate.check_line_shape(document) == []


def test_the_expression_is_read_from_the_document_and_not_copied():
    """Change what section 7 publishes and the checker has to follow.

    This is the assertion that would catch a second copy of the expression
    inside the checker, which is the defect engineering rule 6 names.
    """
    narrowed = _document_with("- @octocat 2026-08-09").replace(
        "^- @[A-Za-z0-9-]{1,39} [0-9]{4}-[0-9]{2}-[0-9]{2}$",
        "^- @[a-z]{1,39} [0-9]{4}-[0-9]{2}-[0-9]{2} SIGNED$",
    )
    assert cla_gate.check_line_shape(narrowed) == ["- @octocat 2026-08-09"]


def test_a_document_publishing_no_expression_is_an_error_not_a_pass():
    """An unreadable rule must not read as a green check."""
    with pytest.raises(SystemExit):
        cla_gate.check_line_shape("# T\n\n## 8. Signatories\n\n- @octocat 2026-08-09\n")


def test_a_document_with_no_signatory_heading_is_an_error_not_a_pass():
    with pytest.raises(SystemExit):
        cla_gate.check_line_shape(
            "# T\n\n```text\n^- @[A-Za-z0-9-]{1,39} [0-9]{4}-[0-9]{2}-[0-9]{2}$\n```\n"
        )


def test_a_signature_outside_section_8_does_not_count():
    """Sections end at the next heading, so a line further down the file is not
    a signature somebody gave."""
    document = _document_with("- @octocat 2026-08-09")
    moved = (
        document.replace("- @octocat 2026-08-09", "") + "\n## 9. Later\n\n- @octocat 2026-08-09\n"
    )
    assert cla_gate.check_signature(moved, "octocat") is not None


def test_signature_finds_a_handle_that_signed():
    assert cla_gate.check_signature(_document_with("- @octocat 2026-08-09"), "octocat") is None


def test_signature_ignores_case_the_way_the_published_check_does():
    assert cla_gate.check_signature(_document_with("- @OctoCat 2026-08-09"), "octocat") is None


def test_signature_refuses_a_handle_that_did_not_sign():
    assert cla_gate.check_signature(_document_with("- @octocat 2026-08-09"), "mona") is not None


def test_signature_refuses_a_handle_against_an_empty_list():
    """The state this repository is in today. An empty list must refuse rather
    than pass vacuously, or the check cannot fail for the first contributor."""
    assert cla_gate.check_signature(_document_with(""), "octocat") is not None


def test_the_copyright_holder_is_not_asked_for_a_signature():
    """Section 7: the owner has no license to grant, so no line is owed."""
    assert cla_gate.check_signature(_document_with(""), "mona", owner="mona") is None


def test_a_bot_is_not_asked_for_a_signature():
    """Section 7: a machine holds no copyright, so no line is owed. The
    bracketed handle is one no user account can hold, so the exemption is not
    a suffix a person can claim."""
    assert cla_gate.check_signature(_document_with(""), "dependabot[bot]") is None


def test_a_bare_bot_suffix_with_no_handle_before_it_is_refused():
    assert cla_gate.check_signature(_document_with(""), "[bot]") is not None


def test_something_that_is_not_a_handle_is_refused():
    assert cla_gate.check_signature(_document_with(""), "not a handle") is not None


def test_trailers_refuses_an_unsigned_commit(tmp_path):
    signed, unsigned = _repo_with_two_commits(tmp_path)
    assert unsigned in _unsigned_in(tmp_path)
    assert signed not in _unsigned_in(tmp_path)


def _unsigned_in(repo: Path) -> str:
    original = cla_gate.REPO_ROOT
    cla_gate.REPO_ROOT = repo
    try:
        return "\n".join(cla_gate.check_trailers("HEAD~2..HEAD"))
    finally:
        cla_gate.REPO_ROOT = original


def _repo_with_two_commits(repo: Path) -> tuple[str, str]:
    def git(*args: str) -> str:
        return subprocess.run(
            ["git", *args], cwd=repo, capture_output=True, text=True, check=True
        ).stdout.strip()

    git("init", "-q", "-b", "main")
    git("config", "user.email", "t@example.com")
    git("config", "user.name", "T")
    git("config", "commit.gpgsign", "false")
    (repo / "a.txt").write_text("a", encoding="utf-8")
    git("add", "a.txt")
    git("commit", "-q", "-m", "root")
    (repo / "b.txt").write_text("b", encoding="utf-8")
    git("add", "b.txt")
    git("commit", "-q", "-s", "-m", "signed")
    signed = git("rev-parse", "HEAD")
    (repo / "c.txt").write_text("c", encoding="utf-8")
    git("add", "c.txt")
    git("commit", "-q", "-m", "unsigned")
    return signed, git("rev-parse", "HEAD")


def _cla_job() -> dict:
    document = yaml.safe_load(LINT_WORKFLOW.read_text(encoding="utf-8"))
    assert "cla" in document["jobs"], (
        "the contributor agreement job is what CLA.md section 7 promises runs on every pull request"
    )
    return document["jobs"]["cla"]


def test_the_job_runs_on_a_pull_request():
    """Two of the three checks read the author and the commit range, and
    neither exists outside a pull request."""
    assert "pull_request" in str(_cla_job()["if"])


def test_the_job_fetches_the_history_the_trailer_check_walks():
    """A shallow checkout cannot walk the range, and the check would pass by
    finding no commits to refuse."""
    checkout = next(
        s for s in _cla_job()["steps"] if str(s.get("uses", "")).startswith("actions/checkout")
    )
    assert checkout["with"]["fetch-depth"] == 0


def test_the_job_calls_the_gate_rather_than_reimplementing_the_rules():
    """Engineering rule 6: one home per rule. Engineering rule 10: the same
    command locally and in CI."""
    steps = "\n".join(str(step.get("run", "")) for step in _cla_job()["steps"])
    assert steps.count("scripts/checks/cla-gate.py") >= 3, (
        "each of the three checks CLA.md section 7 names runs through the gate"
    )
    assert "## 8. Signatories" not in steps, (
        "the section heading is the gate's to know, not the workflow's"
    )
    assert "[A-Za-z0-9-]{1,39}" not in steps, (
        "the signatory expression has one home, and it is CLA.md section 7"
    )


def _document_with(signature: str) -> str:
    """A minimal CLA document publishing the real expression."""
    return (
        "# Contributor agreement\n\n"
        "## 7. How to sign\n\n"
        "```text\n"
        "^- @[A-Za-z0-9-]{1,39} [0-9]{4}-[0-9]{2}-[0-9]{2}$\n"
        "```\n\n"
        "## 8. Signatories\n\n"
        f"{signature}\n"
    )
