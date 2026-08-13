"""The regression test gate REG-001.

The gate says a fix ships with the test that catches it, so the cases that
matter are the ones where it fires. A gate that has never been seen refusing a
commit is indistinguishable from one that cannot, which is the defect doctrine
D-12 names and the reason this file leans on the failing side.

The rule the gate cannot check is checked here instead: that its type set comes
from the hook rather than from a copy, and that the exemption cannot be
satisfied by writing the trailer without a reason.
"""

from __future__ import annotations

import importlib.util
import subprocess
from pathlib import Path

import pytest
import yaml

REPO_ROOT = Path(__file__).resolve().parents[1]
GATE = REPO_ROOT / "scripts" / "checks" / "regression-test-gate.py"
COMMIT_MSG_HOOK = REPO_ROOT / "scripts" / "hooks" / "commit-msg"


def _gate():
    spec = importlib.util.spec_from_file_location("regression_test_gate", GATE)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


gate = _gate()
TYPES = frozenset({"fix", "feat", "docs", "chore"})


# --- the rule ---------------------------------------------------------------


def test_a_fix_with_no_test_is_refused():
    findings = gate.judge("fix: a defect", ["src/a.py"], TYPES)
    assert len(findings) == 1
    assert "touches no test" in findings[0]


def test_a_fix_with_a_test_passes():
    assert gate.judge("fix: a defect", ["src/a.py", "tests/test_a.py"], TYPES) == []


@pytest.mark.parametrize(
    "path",
    [
        "tests/test_a.py",
        "packages/twinflow-kernel/tests/test_scenario.py",
        "tools/roadmap/tests/test_sync.py",
        "src/thing_test.py",
        "src/test_thing.py",
    ],
)
def test_every_shape_of_test_path_counts(path):
    # The layouts this repository actually uses. A gate that only recognizes
    # one of them sends a contributor to argue with it rather than write a test.
    assert gate.is_test_path(path), f"{path} is a test and the gate does not see one"


@pytest.mark.parametrize(
    "path",
    ["src/a.py", "README.md", "docs/testing-policy.md", "justfile", "attestation.jsonl"],
)
def test_a_non_test_path_does_not_count(path):
    assert not gate.is_test_path(path)


def test_a_corpus_regenerated_for_a_known_answer_test_counts():
    # A known-answer test's assertion lives in its corpus, so changing the
    # corpus is changing the test.
    assert gate.is_test_path("tests/corpus/rng.kat")


# --- what the rule does not reach -------------------------------------------


@pytest.mark.parametrize("subject", ["feat: a capability", "docs: a page", "chore: a bump"])
def test_only_a_fix_owes_a_test(subject):
    assert gate.judge(subject, ["src/a.py"], TYPES) == []


def test_an_unparseable_subject_is_left_to_cc_001():
    # Reporting it here too would send the author to two gates for one defect.
    assert gate.judge("not conventional at all", ["src/a.py"], TYPES) == []


# --- the exemption ----------------------------------------------------------


def test_the_trailer_exempts_a_fix_that_cannot_carry_a_test():
    reason = "a dead link has no runtime behavior to assert on"
    message = f"fix(docs): point the link at the file\n\nRegression-Test: none - {reason}"
    assert gate.judge(message, ["docs/x.md"], TYPES) == []


def test_a_trailer_with_no_real_reason_is_refused():
    message = "fix(docs): a link\n\nRegression-Test: none - typo"
    findings = gate.judge(message, ["docs/x.md"], TYPES)
    assert len(findings) == 1
    assert "character reason" in findings[0]


def test_the_bare_trailer_does_not_parse_as_an_exemption():
    # Without the reason the trailer is not an exemption, so the fix still owes
    # a test and the finding is the ordinary one.
    message = "fix(docs): a link\n\nRegression-Test: none"
    findings = gate.judge(message, ["docs/x.md"], TYPES)
    assert len(findings) == 1
    assert "touches no test" in findings[0]


@pytest.mark.parametrize("dash", ["-", "\u2013", "\u2014"])
def test_the_trailer_accepts_any_dash_a_writer_types(dash):
    reason = "the defect is in a comment nothing runs"
    message = f"fix: a thing\n\nRegression-Test: none {dash} {reason}"
    assert gate.judge(message, ["src/a.py"], TYPES) == []


# --- the gate's own wiring --------------------------------------------------


def test_the_type_set_comes_from_the_hook_not_a_copy():
    types = gate.hook_types()
    assert "fix" in types
    assert "feat" in types
    # Read from the hook's own regex, so a type added there arrives here with
    # no second edit. If this drifts, a commit the hook accepts fails the gate.
    text = COMMIT_MSG_HOOK.read_text(encoding="utf-8")
    for one in types:
        assert one in text


def test_the_gate_is_bound_to_a_type_the_hook_accepts():
    # If the hook stopped accepting `fix`, the gate would pass on every commit
    # forever and nothing would say so.
    assert gate.FIX_TYPE in gate.hook_types()


def test_the_commit_msg_hook_calls_this_gate():
    text = COMMIT_MSG_HOOK.read_text(encoding="utf-8")
    assert "regression-test-gate.py" in text, "the gate exists and the hook does not run it"
    assert "--staged" in text


def registry_command() -> str:
    """The command `VAL-GATE-REG-001` declares."""
    registry = yaml.safe_load((REPO_ROOT / "gates.yaml").read_text(encoding="utf-8"))
    return registry["gates"]["VAL-GATE-REG-001"]["command"].strip()


def test_the_justfile_runs_exactly_the_command_the_registry_names():
    """Regression. The range lived in three files and nothing compared them.

    An earlier assertion stopped at the script path, so `gates.yaml` and the
    justfile could name different ranges and both look wired. The phase-exit
    runner calls the registry command and a contributor calls the recipe, so a
    divergence means the two of them check different history.
    """
    justfile = (REPO_ROOT / "justfile").read_text(encoding="utf-8")
    command = registry_command()
    assert f"regression) {command} ;;" in justfile, (
        f"the justfile arm and the registry disagree. The registry says {command!r}"
    )


def test_the_documented_range_is_the_range_that_runs():
    # docs/testing-policy.md section 5 prints the range in a table, and a
    # reader takes that as what CI checks.
    command = registry_command()
    rng = command.split("--range", 1)[1].strip()
    policy = (REPO_ROOT / "docs" / "testing-policy.md").read_text(encoding="utf-8")
    assert rng in policy, f"the policy page does not name the range {rng!r} the gate runs"

    workflow = (REPO_ROOT / ".github" / "workflows" / "lint.yml").read_text(encoding="utf-8")
    assert rng in workflow, f"lint.yml does not run the range {rng!r} the policy claims"


def test_the_exemption_floor_is_the_one_the_documents_quote():
    """Regression. Three documents spelled out a constant nothing checked.

    `MIN_REASON_CHARS` is the floor, and the policy page, CONTRIBUTING, and the
    registry all state it in words. A contributor who writes to the documented
    length and is refused by the gate has been told the wrong number.
    """
    floor = gate.MIN_REASON_CHARS
    spelled = {20: "twenty", 25: "twenty-five", 30: "thirty", 40: "forty"}.get(floor)
    assert spelled, f"no spelling known for {floor}, so this check cannot read the prose"

    for relative in ("docs/testing-policy.md", "gates.yaml"):
        text = (REPO_ROOT / relative).read_text(encoding="utf-8")
        assert spelled in text or str(floor) in text, (
            f"{relative} does not state the {floor}-character floor the gate enforces"
        )


def test_the_selftest_case_count_is_the_one_the_policy_prints():
    result = subprocess.run(
        ["python", str(GATE), "--selftest"], capture_output=True, text=True, cwd=REPO_ROOT
    )
    assert result.returncode == 0, result.stdout + result.stderr
    total = int(result.stdout.rsplit("selftest:", 1)[1].split("/")[1].split()[0])
    spelled = {9: "nine", 10: "ten", 11: "eleven", 12: "twelve"}.get(total)
    assert spelled, f"no spelling known for {total} cases"
    policy = (REPO_ROOT / "docs" / "testing-policy.md").read_text(encoding="utf-8")
    assert f"{spelled} cases" in policy, (
        f"the selftest runs {total} cases and the policy page prints a different count"
    )


def test_the_selftest_passes_and_exercises_the_failing_path():
    result = subprocess.run(
        ["python", str(GATE), "--selftest"], capture_output=True, text=True, cwd=REPO_ROOT
    )
    assert result.returncode == 0, result.stdout + result.stderr
    # Two of the nine cases expect a finding. If the selftest ever reports only
    # passing cases it has stopped proving the gate can fail.
    assert "expected 1" in result.stdout


def test_the_shipped_history_satisfies_the_gate():
    """The baseline the policy adopts, checked rather than asserted.

    docs/testing-policy.md section 5 claims every fix since v0.1.0 carries a
    test. This is what makes that claim falsifiable.
    """
    result = subprocess.run(
        ["python", str(GATE), "--range", "v0.1.0..HEAD"],
        capture_output=True,
        text=True,
        cwd=REPO_ROOT,
    )
    assert result.returncode == 0, result.stdout + result.stderr
