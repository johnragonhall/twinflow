"""The IP hygiene gate (IPH-001).

Two halves matter here and the second matters more. The detector has to fire on
a leaked document header, and it has to stay silent on this repository's own
prose about IP hygiene, which discusses confidentiality on nearly every page a
contributor reads. A scan that flagged CONTRIBUTING.md would be switched off
within a week, and a switched-off gate protects nothing.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
GATE = REPO_ROOT / "scripts" / "checks" / "banned-terms-gate.py"


def _gate():
    spec = importlib.util.spec_from_file_location("banned_terms_gate", GATE)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


gate = _gate()


def hits(line: str, terms: list[str] | None = None):
    return gate.scan_line("<test>", 1, line, terms or [])


@pytest.mark.parametrize("line", gate.SELFTEST_HITS)
def test_an_internal_document_marker_fires(line):
    assert hits(line)


@pytest.mark.parametrize("line", gate.SELFTEST_MISSES)
def test_policy_prose_stays_quiet(line):
    assert hits(line) == []


def test_the_repositorys_own_ip_policy_stays_quiet():
    # The real files, not paraphrases of them. These are the pages a
    # contributor reads, and every one of them is about confidentiality.
    for name in ("CONTRIBUTING.md", "SECURITY.md", "README.md"):
        path = REPO_ROOT / name
        if not path.is_file():
            continue
        for line_no, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            assert gate.scan_line(name, line_no, line, []) == [], f"{name}:{line_no}"


def test_a_denylisted_term_is_found_case_insensitively():
    assert hits("exported from CONTOSO_WMS last March", ["Contoso"])
    assert hits("contoso-logistics gave us the file", ["Contoso"])


def test_a_term_that_is_not_on_the_list_is_not_found():
    assert hits("exported from the simulator last March", ["Contoso"]) == []


def test_a_banner_is_short_and_prose_is_not():
    assert gate.is_banner("CONFIDENTIAL - INTERNAL USE ONLY")
    assert not gate.is_banner(
        "This report contains no proprietary, employer, or client data, and every "
        "dataset in twinflow is synthetic and must stay that way."
    )


def test_a_classification_word_inside_prose_does_not_fire():
    # The banner rule, stated as its own case: the same words, in a sentence.
    assert hits("CONFIDENTIAL - INTERNAL USE ONLY")
    assert (
        hits(
            "Contributors are asked not to paste anything marked internal use only "
            "into an issue, because issues are public."
        )
        == []
    )


def test_the_denylist_is_never_tracked():
    assert not (REPO_ROOT / ".ip-denylist").exists() or gate.wiring_findings()
    assert (REPO_ROOT / ".ip-denylist.example").is_file()


def test_the_hook_runs_this_gate():
    hook = (REPO_ROOT / "scripts" / "hooks" / "pre-commit").read_text(encoding="utf-8")
    assert "banned-terms-gate.py" in hook


def test_the_selftest_passes():
    assert gate.selftest() == 0


def test_this_repository_passes_its_own_gate():
    assert gate.main(["--all"]) == 0
    assert gate.main(["--history"]) == 0
