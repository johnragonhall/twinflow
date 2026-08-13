#!/usr/bin/env python3
"""Workspace membership gate, WORKSPACE-1.

Every package under packages/ has to be reachable three ways, and this checks
all three agree:

    tool.uv.workspace.members   the glob that makes it part of the workspace
    dependency-groups.dev       what a plain `uv sync` actually installs
    tool.uv.sources             where the member resolves from

The middle one is the trap. This workspace root is a virtual project, so
`uv sync` installs the root's own dependencies and prunes everything else, and
`uv run` syncs the same set before it runs anything. A package that is a
workspace member but not a root dev dependency is therefore uninstalled by the
very command that is about to test it. The failure reads as a broken import
rather than as a missing install, which is what makes it expensive to diagnose.

The third one fails louder but no earlier: without a tool.uv.sources entry uv
looks for the member on PyPI, where nothing under packages/ has ever been
published.

It also checks that each package carries LICENSE and NOTICE, byte for byte the
same as the repository root's. Apache-2.0 section 4(a) requires the license to
reach every recipient of the work and 4(d) requires the NOTICE text to travel
with it, and a wheel is a recipient. PEP 639 license-files cannot reach outside
the package directory, so each package holds its own copy, and a copy is a thing
that drifts unless something compares it.

Usage:

    python scripts/checks/workspace-members-gate.py

Needs no third-party module: tomllib is in the standard library from 3.11.
"""

from __future__ import annotations

import sys
import tomllib
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
ROOT_PYPROJECT = REPO_ROOT / "pyproject.toml"


def _member_directories(root: dict) -> list[Path]:
    """Every directory the workspace claims, from the globs it declares.

    Read from tool.uv.workspace.members rather than hard-coded to packages/*.
    A member that lives somewhere else is still a member: twinflow-roadmap sits
    under tools/ because it is not part of the twinflow namespace, and a gate
    scoped to packages/ lets it ship with no LICENSE.
    """
    globs = root.get("tool", {}).get("uv", {}).get("workspace", {}).get("members", [])
    found: list[Path] = []
    for pattern in globs:
        for path in sorted(REPO_ROOT.glob(pattern)):
            if path.is_dir() and (path / "pyproject.toml").is_file():
                found.append(path)
    return found


def _dependency_name(entry: str) -> str:
    """Strip any version marker, so "twinflow-rng>=0.1" reads as the name."""
    for separator in ("[", "<", ">", "=", "!", "~", ";", " "):
        entry = entry.split(separator, 1)[0]
    return entry.strip()


def main() -> int:
    if not ROOT_PYPROJECT.is_file():
        sys.stderr.write(f"BLOCKED: no {ROOT_PYPROJECT}\n")
        return 1

    root = tomllib.loads(ROOT_PYPROJECT.read_text(encoding="utf-8"))
    dev_group = root.get("dependency-groups", {}).get("dev", [])
    declared_dev = {_dependency_name(entry) for entry in dev_group if isinstance(entry, str)}
    declared_sources = set(root.get("tool", {}).get("uv", {}).get("sources", {}))

    members = _member_directories(root)
    if not members:
        print("[workspace] no workspace members yet, nothing to check")
        return 0

    findings: list[str] = []
    checked = 0

    for package_dir in members:
        manifest = package_dir / "pyproject.toml"
        relative = package_dir.relative_to(REPO_ROOT).as_posix()

        name = tomllib.loads(manifest.read_text(encoding="utf-8")).get("project", {}).get("name")
        if not name:
            findings.append(
                f"{relative}/pyproject.toml  has no project.name, so no other file can refer to it"
            )
            continue

        checked += 1

        if name not in declared_dev:
            findings.append(
                f"{name}  is a workspace member but not in dependency-groups.dev of "
                f"pyproject.toml, so `uv sync` and `uv run` will uninstall it"
            )
        if name not in declared_sources:
            findings.append(
                f"{name}  is a workspace member with no tool.uv.sources entry in "
                f"pyproject.toml, so uv will look for it on PyPI"
            )

        for legal_file in ("LICENSE", "NOTICE"):
            root_copy = REPO_ROOT / legal_file
            package_copy = package_dir / legal_file
            if not package_copy.is_file():
                findings.append(
                    f"{name}  has no {legal_file}, so its wheel ships without one; "
                    f"copy {legal_file} into {relative}/"
                )
            elif root_copy.is_file() and package_copy.read_bytes() != root_copy.read_bytes():
                findings.append(
                    f"{name}  has a {legal_file} that differs from the repository "
                    f"root's; re-copy it rather than editing the package copy"
                )

    if not findings:
        print(
            f"[workspace] {checked} members checked: declared in both places, "
            f"each carrying LICENSE and NOTICE"
        )
        return 0

    sys.stderr.write(
        "\n\033[31mBLOCKED: workspace membership is inconsistent [WORKSPACE-1]\033[0m\n"
    )
    for finding in findings:
        sys.stderr.write(f"  {finding}\n")
    sys.stderr.write(
        "\nAdding a package under packages/ takes two lines in the root "
        "pyproject.toml and two files:\n"
        '  dependency-groups.dev  += "<name>"\n'
        "  tool.uv.sources        += <name> = { workspace = true }\n"
        "  cp LICENSE NOTICE packages/<dir>/\n"
    )
    return 1


if __name__ == "__main__":
    sys.exit(main())
