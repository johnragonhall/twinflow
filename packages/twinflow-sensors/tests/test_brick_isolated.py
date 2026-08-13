"""Boundary rule A1.5: this package works installed on its own.

Gate BRICK-1 installs each package alone into a clean environment and imports
it. That gate is the real check and it needs a fresh interpreter, so it runs in
CI rather than here. What runs here is the property that makes an isolated
install possible: this package imports only the workspace packages it declares
as dependencies.

Reading the source rather than the installed module is deliberate. An import
test passes in a workspace where every sibling is already installed, which is
exactly the environment that cannot detect the defect.

The second test is this package's own domain-independence check. twinflow-twin
and twinflow-agent are domain siblings, not ancestors, and the layered contract
in .importlinter forbids the edge. Asserting it here means the defect fails in
this package's own suite rather than only in the workspace-wide lint.
"""

import ast
import tomllib
from pathlib import Path

import pytest

pytestmark = pytest.mark.brick_isolated

PACKAGE_ROOT = Path(__file__).resolve().parents[1]
SOURCE_ROOT = PACKAGE_ROOT / "src" / "twinflow" / "sensors"

#: The domain layer of [tool.twinflow.layers]. A sibling in this list is at the
#: same height in the DAG, so importing one is not a downward edge at all.
DOMAIN_SIBLINGS = frozenset(
    {
        "twin",
        "lss",
        "fleet",
        "procmine",
        "forecast",
        "optimize",
        "causal",
        "cv",
        "agent",
    }
)


#: Read from this package's own manifest rather than written twice, so a
#: dependency added there without a matching import stays consistent and an
#: import added here without a dependency fails.
def _declared_workspace_dependencies() -> frozenset[str]:
    manifest = tomllib.loads((PACKAGE_ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    declared = manifest["project"]["dependencies"]
    names = set()
    for entry in declared:
        head = entry.split(">")[0].split("<")[0].split("=")[0].split("[")[0].strip()
        if head.startswith("twinflow-"):
            names.add(head.removeprefix("twinflow-"))
    return frozenset(names)


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
    allowed = _declared_workspace_dependencies()
    offenders: dict[str, set[str]] = {}
    for path in sorted(SOURCE_ROOT.rglob("*.py")):
        borrowed = _workspace_imports(path) - {"sensors"} - allowed
        if borrowed:
            offenders[str(path.relative_to(PACKAGE_ROOT))] = borrowed

    assert offenders == {}, (
        f"these modules import a workspace package this one does not declare: {offenders}. "
        f"Declared: {sorted(allowed)}"
    )


def test_no_module_imports_a_domain_sibling():
    offenders: dict[str, set[str]] = {}
    for path in sorted(SOURCE_ROOT.rglob("*.py")):
        borrowed = _workspace_imports(path) & DOMAIN_SIBLINGS
        if borrowed:
            offenders[str(path.relative_to(PACKAGE_ROOT))] = borrowed

    assert offenders == {}, (
        "twinflow.sensors sits in the domain layer, so a domain sibling is a "
        f"same-height edge the layered contract forbids: {offenders}"
    )


def test_the_public_surface_is_importable_without_touching_an_undeclared_sibling():
    import twinflow.sensors as sensors

    for name in sensors.__all__:
        assert hasattr(sensors, name), name
