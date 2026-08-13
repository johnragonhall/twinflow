"""Boundary rule A1.5: this package works installed on its own.

Gate BRICK-1 installs each package alone into a clean environment and imports
it. That gate is the real check and it needs a fresh interpreter, so it runs in
CI rather than here. What runs here is the property that makes an isolated
install possible: this package imports only the workspace packages it declares
as dependencies.

Reading the source rather than the installed module is deliberate. An import
test passes in a workspace where every sibling is already installed, which is
exactly the environment that cannot detect the defect.
"""

import ast
import tomllib
from pathlib import Path

import pytest

pytestmark = pytest.mark.brick_isolated

PACKAGE_ROOT = Path(__file__).resolve().parents[1]
SOURCE_ROOT = PACKAGE_ROOT / "src" / "twinflow" / "agent"

#: twinflow.agent sits in the domain layer, and boundary rule A1.3 says a domain
#: package never imports a sibling domain package. Naming them here rather than
#: deriving them keeps this test honest when a new domain package is added: the
#: import-linter contract is the enforcement, and this is the local echo of it
#: that fails in the package's own suite rather than only in the whole-repo run.
FORBIDDEN_SIBLINGS = frozenset(
    {"twin", "lss", "sensors", "fleet", "procmine", "forecast", "optimize", "causal", "cv"}
)

FORBIDDEN_APPS = frozenset({"api", "dashboard", "cli"})


def _declared_workspace_dependencies() -> frozenset[str]:
    """Read from this package's own manifest rather than written twice, so a
    dependency added there without a matching import stays consistent and an
    import added here without a dependency fails."""
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
        borrowed = _workspace_imports(path) - {"agent"} - allowed
        if borrowed:
            offenders[str(path.relative_to(PACKAGE_ROOT))] = borrowed

    assert offenders == {}, (
        f"these modules import a workspace package this one does not declare: {offenders}. "
        f"Declared: {sorted(allowed)}"
    )


def test_no_module_reaches_sideways_into_another_domain_package():
    """A1.3. The domain-independence contract fails the whole build on this, and
    a build failure names the contract rather than the file, so the same rule is
    asserted here where the failure names the line."""
    offenders: dict[str, set[str]] = {}
    for path in sorted(SOURCE_ROOT.rglob("*.py")):
        sideways = _workspace_imports(path) & FORBIDDEN_SIBLINGS
        if sideways:
            offenders[str(path.relative_to(PACKAGE_ROOT))] = sideways
    assert offenders == {}, f"domain packages must not import each other: {offenders}"


def test_no_module_reaches_upward_into_an_app_package():
    """A domain package that imported the API would make a quality manager
    install a web server to read a metric."""
    offenders: dict[str, set[str]] = {}
    for path in sorted(SOURCE_ROOT.rglob("*.py")):
        upward = _workspace_imports(path) & FORBIDDEN_APPS
        if upward:
            offenders[str(path.relative_to(PACKAGE_ROOT))] = upward
    assert offenders == {}, f"a domain package must not import an app package: {offenders}"


def test_the_public_surface_is_importable_without_touching_an_undeclared_sibling():
    import twinflow.agent as agent

    for name in agent.__all__:
        assert hasattr(agent, name), name
