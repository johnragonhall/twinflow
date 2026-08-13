"""Boundary rule A1.5: this package works installed with only what it declares.

Stricter here than for the packages under packages/. This one is a leaf outside
the twinflow namespace and it has to run on a checkout that does not build, so
the rule is not "imports only its declared workspace dependencies" but "imports
no workspace package at all".
"""

import ast
import tomllib
from pathlib import Path

import pytest

pytestmark = pytest.mark.brick_isolated

PACKAGE_ROOT = Path(__file__).resolve().parents[1]
SOURCE_ROOT = PACKAGE_ROOT / "src" / "twinflow_roadmap"


def _imports(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    found: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            found.update(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module and node.level == 0:
            found.add(node.module.split(".")[0])
    return found


def test_the_roadmap_tool_imports_no_simulation_package():
    offenders = {
        str(path.relative_to(PACKAGE_ROOT)): sorted(names)
        for path in sorted(SOURCE_ROOT.rglob("*.py"))
        if (names := {name for name in _imports(path) if name == "twinflow"})
    }
    assert offenders == {}, (
        f"these modules import a workspace package: {offenders}. The roadmap tool is a leaf, "
        f"because `roadmap validate` is the first thing CI runs on a branch that broke the twin"
    )


def test_every_third_party_import_is_declared():
    manifest = tomllib.loads((PACKAGE_ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    # ruamel.yaml is distributed under a dotted name and imported as a
    # namespace package, so the top-level module a source file names is
    # `ruamel`. Both spellings count as declared.
    declared = set()
    for entry in manifest["project"]["dependencies"]:
        name = entry.split(">")[0].split("<")[0].split("=")[0].split("[")[0].strip()
        declared.add(name)
        declared.add(name.replace("-", "_"))
        declared.add(name.split(".")[0])
    standard_library = {
        "__future__",
        "argparse",
        "ast",
        "collections",
        "dataclasses",
        "json",
        "pathlib",
        "re",
        "shutil",
        "subprocess",
        "sys",
        "textwrap",
        "tomllib",
        "typing",
    }
    borrowed: dict[str, list[str]] = {}
    for path in sorted(SOURCE_ROOT.rglob("*.py")):
        outside = {
            name
            for name in _imports(path)
            if name not in standard_library and name != "twinflow_roadmap" and name not in declared
        }
        if outside:
            borrowed[str(path.relative_to(PACKAGE_ROOT))] = sorted(outside)
    assert borrowed == {}, f"undeclared imports: {borrowed}. Declared: {sorted(declared)}"


def test_the_public_surface_is_importable():
    import twinflow_roadmap

    for name in twinflow_roadmap.__all__:
        assert hasattr(twinflow_roadmap, name), name
