"""The workflows as a supply chain (ACT-001, PROV-001, SAST-001).

A workflow is executable code holding write permissions, and it is the part of
this repository an attacker reaches without cloning it. actionlint reads these
files for syntax and zizmor reads them for security; this reads them for the
three properties a release depends on and neither of those tools can state:

    the inputs are pinned      an action on a tag or a branch is an action
                               whose upstream can change under the pin
    the output is attested     an artifact with no provenance is a file that
                               claims a builder rather than proving one
    the tree is analyzed       a language nothing scans is a language whose
                               defects nobody looks for

Every assertion reads the workflow files rather than a run, because these have
to hold before a release rather than be discovered during one.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest
import yaml

REPO_ROOT = Path(__file__).resolve().parents[1]
WORKFLOWS = REPO_ROOT / ".github" / "workflows"
RELEASE = WORKFLOWS / "release.yml"

#: A 40-character hex commit SHA. A tag or a branch does not match, which is
#: the whole point: `@v4` and `@stable` both move.
PINNED = re.compile(r"^[^@]+@[0-9a-f]{40}$")

#: `uses:` values that name a local path or a Docker image rather than a
#: repository, neither of which carries a commit to pin to.
NOT_A_REPOSITORY = ("./", "docker://")


def workflow_files() -> list[Path]:
    return sorted(WORKFLOWS.glob("*.yml"))


def uses_lines() -> list[tuple[Path, int, str]]:
    """Every `uses:` in every workflow, with where it sits."""
    found = []
    for path in workflow_files():
        for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
            stripped = line.strip()
            if stripped.startswith(("uses:", "- uses:")):
                value = stripped.split("uses:", 1)[1].split("#")[0].strip()
                if value and not value.startswith(NOT_A_REPOSITORY):
                    found.append((path, number, value))
    return found


def load(path: Path) -> dict:
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def test_there_are_workflows_to_check():
    # Every assertion below passes vacuously over an empty directory.
    assert len(workflow_files()) >= 5
    assert len(uses_lines()) >= 10


@pytest.mark.parametrize("path,number,value", uses_lines(), ids=lambda v: str(v)[:60])
def test_every_action_is_pinned_to_a_commit(path, number, value):
    assert PINNED.match(value), (
        f"{path.name}:{number} uses {value!r}, which is a tag or a branch. "
        f"An upstream force-push moves it, and nothing here would notice"
    )


def test_every_pin_records_the_tag_it_came_from():
    # A bare SHA is unreadable. The trailing comment is what lets a reviewer
    # see that a dependabot bump moved v4 to v5 rather than only that forty
    # hex characters changed.
    for path in workflow_files():
        for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
            if "uses:" in line and re.search(r"@[0-9a-f]{40}", line):
                assert "#" in line.split("uses:", 1)[1], f"{path.name}:{number} pins with no tag"


#: The two shorthands GitHub accepts in place of a scope map. `write-all` is
#: every scope at write, which is the opposite of what a top-level default is
#: for, and it arrives as a plain string rather than as a mapping.
PERMISSION_SHORTHANDS = ("read-all", "write-all")


def test_no_workflow_grants_write_by_default():
    """The top-level default is the floor every job starts from.

    A scope map and a shorthand string are both legal here, so both are read.
    Checking only the map would leave the shorthand unread, and `write-all` is
    written as a shorthand.
    """
    checked = 0
    for path in workflow_files():
        document = load(path)
        permissions = document.get("permissions")
        assert permissions is not None, f"{path.name} declares no top-level permissions"

        if isinstance(permissions, str):
            assert permissions in PERMISSION_SHORTHANDS, (
                f"{path.name} declares permissions {permissions!r}, which is neither a "
                f"scope map nor a shorthand this test knows how to read"
            )
            assert permissions != "write-all", (
                f"{path.name} grants write on every scope to every job"
            )
        else:
            for scope, level in permissions.items():
                assert level != "write", f"{path.name} grants {scope}: write to every job"
        checked += 1

    # A workflow whose permissions this test cannot parse is a workflow it does
    # not check, and a count proves every one was read rather than skipped.
    assert checked == len(workflow_files())


def test_the_shorthand_form_is_actually_exercised():
    """At least one workflow uses the string form the branch above reads.

    Without this the shorthand branch is unreachable in this repository, and an
    unreachable branch is one nothing would notice going wrong.
    """
    shorthands = [
        path.name for path in workflow_files() if isinstance(load(path).get("permissions"), str)
    ]
    assert shorthands, "no workflow uses the shorthand form, so that branch is untested"


def test_the_release_builds_twice_and_compares(  # PROV-001
):
    text = RELEASE.read_text(encoding="utf-8")
    assert "SOURCE_DATE_EPOCH" in text, "no pinned timestamp, so the zip mtimes come from a clock"
    assert "dist-verify" in text, "the release builds once, so reproducibility is untested"
    assert "cmp -s" in text, "two builds exist and nothing compares them"


def test_the_release_attests_its_provenance():  # PROV-001
    text = RELEASE.read_text(encoding="utf-8")
    assert "attest-build-provenance" in text
    assert "attestations: write" in text, "provenance needs the token scope that signs it"


def test_the_release_verifies_the_index_attestation():  # PROV-001
    # PEP 740 publishes the Integrity API precisely so the claim can be checked
    # from outside the pipeline that made it.
    text = RELEASE.read_text(encoding="utf-8")
    assert "attestations: true" in text, "the publish leaves attestations to a default"
    assert "integrity" in text, "nothing reads the attestation back off the index"


def test_the_release_restores_no_cache():  # PROV-001
    # A cache is writable by any run that reaches the same key. Restoring one
    # here would let a build nobody reviewed put bytes into artifacts this job
    # signs, and the attestation would faithfully attest to them.
    document = load(RELEASE)
    for job in document["jobs"].values():
        for step in job.get("steps", []):
            with_block = step.get("with") or {}
            assert with_block.get("enable-cache") is not True, (
                "the release workflow enables a cache"
            )


def test_no_run_block_interpolates_a_workflow_expression():
    """Values reach a shell through the environment, never through expansion.

    A `${{ }}` expression inside a `run:` block is expanded by the workflow
    engine before the shell parses the script, so a value carrying shell syntax
    becomes shell syntax. Through the environment it stays a string.
    """
    offenders = []
    for path in workflow_files():
        document = load(path)
        for job_name, job in document.get("jobs", {}).items():
            for step in job.get("steps", []):
                script = step.get("run")
                if isinstance(script, str) and "${{" in script:
                    offenders.append(f"{path.name}:{job_name}:{step.get('name', 'unnamed')}")
    assert offenders == [], f"expressions interpolated into a shell: {offenders}"


def test_static_analysis_covers_the_languages_in_the_tree():  # SAST-001
    document = load(WORKFLOWS / "codeql.yml")
    languages = set()
    for job in document["jobs"].values():
        matrix = job.get("strategy", {}).get("matrix", {})
        languages.update(matrix.get("language", []))
    assert "python" in languages, "the language this repository is written in is not analyzed"
    assert "actions" in languages, "the workflows are code and nothing analyzes them"


def test_static_analysis_runs_on_a_schedule_as_well_as_a_diff():  # SAST-001
    # A query pack published next month finds defects in code that has not
    # changed, and a scan that only runs on a diff never revisits them.
    document = load(WORKFLOWS / "codeql.yml")
    triggers = document[True] if True in document else document.get("on", {})
    assert "schedule" in triggers
    assert "pull_request" in triggers


def test_the_analysis_results_are_published():  # SAST-001
    document = load(WORKFLOWS / "codeql.yml")
    for job in document["jobs"].values():
        assert job.get("permissions", {}).get("security-events") == "write", (
            "a scan whose findings nobody can read is a scan nobody acts on"
        )


def test_the_security_posture_is_scored_by_somebody_else():
    # Every other gate here is one this project wrote, and a project that only
    # grades itself has graded nothing.
    document = load(WORKFLOWS / "scorecard.yml")
    text = (WORKFLOWS / "scorecard.yml").read_text(encoding="utf-8")
    assert "ossf/scorecard-action" in text
    assert "publish_results: true" in text
    # `on:` parses as the boolean True under the YAML 1.1 rules PyYAML follows,
    # which is why this reads the key rather than the string.
    triggers = document[True] if True in document else document.get("on", {})
    assert "schedule" in triggers
