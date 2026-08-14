"""The SBOM gate, and the property that makes it worth running.

A CycloneDX document parses and validates whatever environment it was taken
from, so an SBOM attached to a release proves nothing on its own about whether
it lists the software that release ships. The gate reads the stronger property
against `uv.lock`, and the tests below assert it discriminates: a document
naming the shipped closure passes, and one naming the SBOM generator's own
closure is refused.

Every case in the checker's selftest corpus is parametrized here by name, so a
refusal that stops firing names itself in the failure rather than disappearing
into an aggregate that still reports green (doctrine D-12).
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
GATE = REPO_ROOT / "scripts" / "checks" / "sbom-gate.py"


def _load():
    """Import the checker by path, because its filename is not an identifier."""
    spec = importlib.util.spec_from_file_location("sbom_gate", GATE)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


gate = _load()


@pytest.mark.parametrize(
    ("name", "document", "expected", "should_find"),
    gate.SELFTEST_CASES,
    ids=[case[0] for case in gate.SELFTEST_CASES],
)
def test_each_selftest_case_lands_the_way_it_says(
    name: str, document: dict, expected: tuple[str, ...], should_find: bool
):
    assert bool(gate.check_sbom(document, expected)) is should_find


def test_the_selftest_runs_clean_as_the_release_runs_it():
    assert gate.main(["--selftest"]) == 0


def test_an_sbom_of_the_generator_is_refused():
    """The document an environment scan produces when it is pointed at the
    environment the scanner itself lives in.

    This is the case the gate exists for: every component in it is real, the
    document is well formed, and not one entry is software this project ships.
    """
    findings = gate.check_sbom(
        {
            "components": [
                {"name": "cyclonedx-python-lib"},
                {"name": "py-serializable"},
                {"name": "lxml"},
            ]
        },
        ("numpy", "pydantic", "starlette"),
    )

    assert findings
    assert any("describes the tool" in finding for finding in findings)


def test_an_sbom_of_the_shipped_closure_passes():
    """The control. A gate that refused every document would pass the test above
    while blocking every release."""
    assert (
        gate.check_sbom(
            {"components": [{"name": "numpy"}, {"name": "pydantic"}, {"name": "starlette"}]},
            ("numpy", "pydantic", "starlette"),
        )
        == []
    )


def test_the_two_spellings_of_a_distribution_name_are_one_name():
    """`typing_extensions` on a component and `typing-extensions` in the lock are
    the same distribution, and a gate that missed that would fail every release
    for a reason that is not a defect."""
    assert gate.normalize("typing_extensions") == gate.normalize("typing-extensions")
    assert (
        gate.check_sbom({"components": [{"name": "Typing_Extensions"}]}, ("typing-extensions",))
        == []
    )


@pytest.mark.parametrize(
    ("spelling", "canonical"),
    [
        ("typing__extensions", "typing-extensions"),
        ("zope.interface", "zope-interface"),
        ("a.b_c", "a-b-c"),
        ("A__B", "a-b"),
        ("ruamel...yaml", "ruamel-yaml"),
    ],
)
def test_a_run_of_separators_collapses_to_one(spelling: str, canonical: str):
    """PEP 503 replaces runs of `-`, `_`, and `.` with a single `-`.

    Mapping each character on its own leaves `typing__extensions` as
    `typing--extensions`, which compares unequal to the lock's spelling and
    reports a shipped distribution as absent from an SBOM that carries it.
    """
    assert gate.normalize(spelling) == canonical
    assert gate.check_sbom({"components": [{"name": spelling}]}, (canonical,)) == []
