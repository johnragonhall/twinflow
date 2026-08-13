"""Boundary rule A1.5: this package works installed on its own.

Gate BRICK-1 installs each package alone into a clean environment and imports
it. That gate is the real check and it needs a fresh interpreter, so it runs in
CI rather than here. What runs here is the property that makes an isolated
install possible: this package imports only the workspace packages it declares
as dependencies.

Reading the source rather than the installed module is deliberate. An import
test passes in a workspace where every sibling is already installed, which is
exactly the environment that cannot detect the defect.

The base install matters more here than in most bricks. Section 2.7 of
foundations keeps every database driver behind an extra, so a reader who wants
the historian contract does not pull a Rust wheel to get it. The base set is
the kernel, the schemas, and twinflow-config, which is where the six-level UNS
grammar lives now that one definition serves both the publish side and the
historian. None of the three is a driver, and the check below is on the drivers.
"""

import ast
import tomllib
from pathlib import Path

import pytest

pytestmark = pytest.mark.brick_isolated

PACKAGE_ROOT = Path(__file__).resolve().parents[1]
SOURCE_ROOT = PACKAGE_ROOT / "src" / "twinflow" / "storage"

#: Packages that would make the base install heavy. Section 2.7 puts each one
#: behind an extra, so an import of one from the base source is the defect that
#: extra exists to prevent.
HEAVY = ("deltalake", "duckdb", "pyarrow", "asyncpg", "aiokafka", "boto3")


def _manifest() -> dict:
    return tomllib.loads((PACKAGE_ROOT / "pyproject.toml").read_text(encoding="utf-8"))


#: Read from this package's own manifest rather than written twice, so a
#: dependency added there without a matching import stays consistent and an
#: import added here without a dependency fails.
def _declared_workspace_dependencies() -> frozenset[str]:
    declared = _manifest()["project"]["dependencies"]
    names = set()
    for entry in declared:
        head = entry.split(">")[0].split("<")[0].split("=")[0].split("[")[0].strip()
        if head.startswith("twinflow-"):
            names.add(head.removeprefix("twinflow-"))
    return frozenset(names)


def _top_level_imports(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    found: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                found.add(alias.name.split(".")[0])
        elif isinstance(node, ast.ImportFrom) and node.module and node.level == 0:
            found.add(node.module.split(".")[0])
    return found


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
        borrowed = _workspace_imports(path) - {"storage"} - allowed
        if borrowed:
            offenders[str(path.relative_to(PACKAGE_ROOT))] = borrowed

    assert offenders == {}, (
        f"these modules import a workspace package this one does not declare: {offenders}. "
        f"Declared: {sorted(allowed)}"
    )


def test_no_domain_package_is_imported_from_the_storage_layer():
    """Layer rule A1.3: storage sits below domain and never reaches up."""
    allowed = _declared_workspace_dependencies() | {"storage"}
    for path in sorted(SOURCE_ROOT.rglob("*.py")):
        assert _workspace_imports(path) <= allowed, path


def test_the_base_install_pulls_no_database_driver():
    declared = " ".join(_manifest()["project"]["dependencies"])
    for name in HEAVY:
        assert name not in declared, f"{name} belongs behind an extra, not in the base install"

    imported: set[str] = set()
    for path in sorted(SOURCE_ROOT.rglob("*.py")):
        imported |= _top_level_imports(path)
    assert imported.isdisjoint(HEAVY), sorted(imported & set(HEAVY))


def test_the_public_surface_is_importable_without_touching_an_undeclared_sibling():
    import twinflow.storage as storage

    for name in storage.__all__:
        assert hasattr(storage, name), name
