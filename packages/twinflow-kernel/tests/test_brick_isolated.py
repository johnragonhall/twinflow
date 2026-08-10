"""Boundary rule A1.5: this package works installed with only what it declares.

Gate BRICK-1 installs each package alone into a clean environment and imports
it. That gate is the real check and it needs a fresh interpreter, so it runs in
CI rather than here. What runs here is the property that makes an isolated
install possible: this package imports only the workspace packages it declares.

The kernel is the interesting case, because it is the first package with real
workspace dependencies. Foundations 2.2 fixes its core install at pydantic,
numpy, twinflow-schemas and twinflow-rng, and says why: a quality manager who
installs one domain brick gets what they already have, and no columnar,
database, or broker library.
"""

import ast
import tomllib
from pathlib import Path

import pytest

pytestmark = pytest.mark.brick_isolated

PACKAGE_ROOT = Path(__file__).resolve().parents[1]
SOURCE_ROOT = PACKAGE_ROOT / "src" / "twinflow" / "kernel"

#: Runtime dependencies the core install may not exceed, per foundations 2.2.
#: A columnar, database, or broker library appearing here is the defect this
#: pin exists to catch, and it belongs to twinflow-storage instead.
ALLOWED_THIRD_PARTY = frozenset({"pydantic", "numpy"})


def _manifest() -> dict:
    return tomllib.loads((PACKAGE_ROOT / "pyproject.toml").read_text(encoding="utf-8"))


def _declared_dependencies() -> tuple[frozenset[str], frozenset[str]]:
    workspace, third_party = set(), set()
    for entry in _manifest()["project"]["dependencies"]:
        head = entry.split(">")[0].split("<")[0].split("=")[0].split("[")[0].strip()
        if head.startswith("twinflow-"):
            workspace.add(head.removeprefix("twinflow-"))
        else:
            third_party.add(head)
    return frozenset(workspace), frozenset(third_party)


def _workspace_imports(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    found: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                parts = alias.name.split(".")
                if len(parts) >= 2 and parts[0] == "twinflow":
                    found.add(parts[1])
        elif isinstance(node, ast.ImportFrom) and node.module and node.level == 0:
            parts = node.module.split(".")
            if len(parts) >= 2 and parts[0] == "twinflow":
                found.add(parts[1])
    return found


def test_package_imports_only_its_declared_workspace_dependencies():
    allowed, _ = _declared_dependencies()
    offenders: dict[str, set[str]] = {}
    for path in sorted(SOURCE_ROOT.rglob("*.py")):
        borrowed = _workspace_imports(path) - {"kernel"} - allowed
        if borrowed:
            offenders[str(path.relative_to(PACKAGE_ROOT))] = borrowed

    assert offenders == {}, (
        f"these modules import a workspace package this one does not declare: {offenders}. "
        f"Declared: {sorted(allowed)}"
    )


def test_the_core_install_pulls_no_heavy_dependency():
    """D-10. No port signature names a heavy type, and none is installed.

    A broker or database library reaching the core install is what turns
    `pip install twinflow-lss` from a small thing into a large one.
    """
    _, third_party = _declared_dependencies()
    assert third_party <= ALLOWED_THIRD_PARTY, (
        f"the core install declares {sorted(third_party - ALLOWED_THIRD_PARTY)}, which "
        f"foundations 2.2 keeps out of it. Concrete adapters belong to twinflow-storage."
    )


def test_the_private_implementation_is_a_regular_package():
    """Only twinflow itself is a namespace package.

    A missing __init__.py under _impl would make it an implicit namespace
    package, which lets another installed distribution add modules into it and
    hides the whole subtree from the import graph. When that happened here,
    import-linter reported every private-module contract as KEPT while the
    modules those contracts name were absent from the graph entirely.
    """
    assert (SOURCE_ROOT / "_impl" / "__init__.py").is_file()


def test_the_public_surface_is_importable():
    import twinflow.kernel as kernel

    for name in kernel.__all__:
        assert hasattr(kernel, name), name
