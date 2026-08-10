"""Boundary rule A1.5: this package works installed on its own.

Gate BRICK-1 installs each package alone into a clean environment and imports
it. That gate is the real check and it needs a fresh interpreter, so it runs in
CI rather than here. What runs here is the property that makes an isolated
install possible in the first place, read from the source tree: this package
imports nothing else from the workspace.

Reading the source rather than the installed module is deliberate. An import
test passes in a workspace where every sibling is already installed, which is
exactly the environment that cannot detect the defect.
"""

import ast
from pathlib import Path

import pytest

pytestmark = pytest.mark.brick_isolated

PACKAGE_ROOT = Path(__file__).resolve().parents[1]
SOURCE_ROOT = PACKAGE_ROOT / "src" / "twinflow" / "schemas"

#: The workspace packages this one may import. Empty: it is the leaf, and that
#: is what lets a consumer install one brick without pulling the rest.
ALLOWED_WORKSPACE_IMPORTS: frozenset[str] = frozenset()


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
    offenders: dict[str, set[str]] = {}
    for path in sorted(SOURCE_ROOT.rglob("*.py")):
        borrowed = _workspace_imports(path) - {"schemas"} - ALLOWED_WORKSPACE_IMPORTS
        if borrowed:
            offenders[str(path.relative_to(PACKAGE_ROOT))] = borrowed

    assert offenders == {}, (
        f"these modules import a workspace package this one does not declare: {offenders}. "
        f"Allowed: {sorted(ALLOWED_WORKSPACE_IMPORTS) or 'nothing, this is the leaf'}"
    )


def test_the_public_surface_is_importable_without_touching_a_sibling():
    """A star import is what a consumer of a single brick actually writes."""
    import twinflow.schemas as schemas

    for name in schemas.__all__:
        assert hasattr(schemas, name), name
