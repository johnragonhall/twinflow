#!/usr/bin/env python3
"""Import boundary gate: IMPORT-2 and IMPORT-3 of boundary rule A1.4.

    python scripts/checks/import-boundary-gate.py

import-linter owns rules A1.1 through A1.3, which are about which package may
import which. These two are about ownership of names, which import-linter has no
way to express:

    IMPORT-2  the workspace import graph has no cycle
    IMPORT-3  every name in a package's __all__ is defined in that package or
              declared as a re-export, and no name is owned by two packages

IMPORT-3 is what lets twinflow.kernel re-export ConfigHash from twinflow-schemas
without owning it. Re-exports are declared rather than inferred, because a name
that appears in two packages' public surface has two owners and a consumer
writing a star import gets whichever one it imported last.

The declaration lives in each package's pyproject.toml:

    [tool.twinflow]
    reexports = ["Quantity", "ConfigHash"]

This reads source with ast rather than importing anything, so it runs before the
workspace is installed and cannot be fooled by an import side effect.
"""

from __future__ import annotations

import ast
import sys
import tomllib
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
PACKAGES_DIR = REPO_ROOT / "packages"
NAMESPACE = "twinflow"


def _packages() -> dict[str, Path]:
    """Map twinflow.<name> to the directory holding its source."""
    found: dict[str, Path] = {}
    if not PACKAGES_DIR.is_dir():
        return found
    for package_dir in sorted(PACKAGES_DIR.iterdir()):
        src = package_dir / "src" / NAMESPACE
        if not src.is_dir():
            continue
        for module in sorted(src.iterdir()):
            if module.is_dir() and (module / "__init__.py").is_file():
                found[module.name] = module
    return found


def _declared_reexports(name: str) -> set[str]:
    manifest = PACKAGES_DIR / f"{NAMESPACE}-{name}" / "pyproject.toml"
    if not manifest.is_file():
        return set()
    data = tomllib.loads(manifest.read_text(encoding="utf-8"))
    declared = data.get("tool", {}).get("twinflow", {}).get("reexports", [])
    return {entry for entry in declared if isinstance(entry, str)}


def _module_tree(root: Path) -> list[Path]:
    return sorted(p for p in root.rglob("*.py"))


def _imports_of(path: Path) -> set[str]:
    """The twinflow.<name> packages this file imports."""
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    found: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                parts = alias.name.split(".")
                if len(parts) >= 2 and parts[0] == NAMESPACE:
                    found.add(parts[1])
        elif isinstance(node, ast.ImportFrom) and node.module and node.level == 0:
            parts = node.module.split(".")
            if len(parts) >= 2 and parts[0] == NAMESPACE:
                found.add(parts[1])
    return found


def _public_names(init_path: Path) -> list[str] | None:
    """The __all__ list, read from source. None when the module declares none."""
    tree = ast.parse(init_path.read_text(encoding="utf-8"), filename=str(init_path))
    for node in tree.body:
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id == "__all__":
                    try:
                        value = ast.literal_eval(node.value)
                    except ValueError:
                        return None
                    if isinstance(value, (list, tuple)):
                        return [str(entry) for entry in value]
    return None


def _defined_names(root: Path) -> set[str]:
    """Every name bound at module level anywhere in the package."""
    defined: set[str] = set()
    for path in _module_tree(root):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in tree.body:
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                defined.add(node.name)
            elif isinstance(node, ast.Assign):
                for target in node.targets:
                    if isinstance(target, ast.Name):
                        defined.add(target.id)
            elif isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
                defined.add(node.target.id)
    return defined


def _find_cycle(graph: dict[str, set[str]]) -> list[str] | None:
    """Depth-first search for a cycle, returning the path that closes it."""
    WHITE, GREY, BLACK = 0, 1, 2
    colour = dict.fromkeys(graph, WHITE)
    stack: list[str] = []

    def visit(node: str) -> list[str] | None:
        colour[node] = GREY
        stack.append(node)
        for neighbour in sorted(graph.get(node, ())):
            if neighbour not in colour:
                continue
            if colour[neighbour] == GREY:
                return stack[stack.index(neighbour) :] + [neighbour]
            if colour[neighbour] == WHITE:
                found = visit(neighbour)
                if found:
                    return found
        stack.pop()
        colour[node] = BLACK
        return None

    for node in sorted(graph):
        if colour[node] == WHITE:
            found = visit(node)
            if found:
                return found
    return None


def main() -> int:
    packages = _packages()
    if not packages:
        print("[import] no packages yet, nothing to check")
        return 0

    findings: list[str] = []

    # IMPORT-2: the import graph has no cycle.
    graph: dict[str, set[str]] = {}
    for name, root in packages.items():
        edges: set[str] = set()
        for path in _module_tree(root):
            edges |= _imports_of(path)
        graph[name] = {edge for edge in edges if edge != name and edge in packages}

    cycle = _find_cycle(graph)
    if cycle:
        findings.append(
            "[IMPORT-2] the workspace import graph has a cycle: "
            + " -> ".join(f"{NAMESPACE}.{part}" for part in cycle)
        )

    # IMPORT-3: every exported name is owned here or declared as a re-export,
    # and no name is owned by two packages.
    owned: dict[str, str] = {}
    for name, root in sorted(packages.items()):
        exported = _public_names(root / "__init__.py")
        if exported is None:
            findings.append(
                f"[IMPORT-3] {NAMESPACE}.{name} declares no __all__, so its public "
                "surface is whatever happens to be importable"
            )
            continue

        reexports = _declared_reexports(name)
        defined = _defined_names(root)
        for entry in exported:
            if entry.startswith("__") and entry.endswith("__"):
                continue
            if entry not in defined and entry not in reexports:
                findings.append(
                    f"[IMPORT-3] {NAMESPACE}.{name}.__all__ carries {entry!r}, which this "
                    f"package neither defines nor declares in tool.twinflow.reexports"
                )
                continue
            if entry in reexports:
                continue
            if entry in owned:
                findings.append(
                    f"[IMPORT-3] {entry!r} is owned by both {NAMESPACE}.{owned[entry]} and "
                    f"{NAMESPACE}.{name}; one public symbol has exactly one owning package"
                )
            else:
                owned[entry] = name

    if findings:
        sys.stderr.write("\n\033[31mBLOCKED: import boundary violations\033[0m\n")
        for finding in findings:
            sys.stderr.write(f"  {finding}\n")
        sys.stderr.write(
            "\nA1.4: every public symbol has exactly one owning package. Declare a "
            "borrowed name in that package's pyproject.toml:\n"
            "  [tool.twinflow]\n"
            '  reexports = ["Quantity"]\n'
        )
        return 1

    print(
        f"[import] {len(packages)} packages checked: no cycle, "
        f"{len(owned)} public names each owned once"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
