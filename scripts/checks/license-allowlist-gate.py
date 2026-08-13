#!/usr/bin/env python3
"""License allowlist gate, the SEC-001 half that reads the resolved tree.

    python scripts/checks/license-allowlist-gate.py

Every resolved dependency has to match a row in the CONTRIBUTING.md allowlist.
Two rows turn on where the dependency sits rather than only on its SPDX id:
MPL-2.0 is accepted for a development dependency and refused for one shipped at
run time, because its file-level condition would travel to whoever installs a
twinflow package.

The allowlist is parsed out of CONTRIBUTING.md rather than copied here. A second
copy is a copy that drifts, and the table a contributor reads has to be the
table CI enforces.

Metadata comes from the installed distributions, so it reports what would
actually ship rather than what a manifest claims. A distribution the resolver
did not install is not a distribution anybody receives.
"""

from __future__ import annotations

import re
import sys
import tomllib
from importlib import metadata
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
CONTRIBUTING = REPO_ROOT / "CONTRIBUTING.md"
ROOT_PYPROJECT = REPO_ROOT / "pyproject.toml"

DEV_ONLY = "Development only"
RUNTIME = "Shipped at run time"
ANY = "Any dependency"

_ROW = re.compile(
    r"^\|\s*`(?P<spdx>[^`]+)`\s*\|\s*(?P<applies>[^|]+?)\s*\|\s*(?P<decision>Accepted|Refused)\s*\|"
)

#: Classifier text maps onto an SPDX id. Only the ids the allowlist names are
#: listed: an unmapped license reaches the report as unknown rather than being
#: guessed at, because guessing is how a refused license passes.
_CLASSIFIER_TO_SPDX = {
    "MIT License": "MIT",
    "BSD License": "BSD-3-Clause",
    "Apache Software License": "Apache-2.0",
    "Python Software Foundation License": "Python-2.0",
    "Mozilla Public License 2.0 (MPL 2.0)": "MPL-2.0",
    "ISC License (ISCL)": "ISC",
    "GNU General Public License v2 (GPLv2)": "GPL-2.0",
    "GNU General Public License v3 (GPLv3)": "GPL-3.0",
    "GNU Affero General Public License v3": "AGPL-3.0",
}

_NORMALISE = {
    # PyPI metadata spells the Python license both ways, and the allowlist
    # names one of them.
    "PSF-2.0": "Python-2.0",
    "Apache 2.0": "Apache-2.0",
    "Apache-2.0": "Apache-2.0",
    "Apache License 2.0": "Apache-2.0",
    "MIT": "MIT",
    "MIT License": "MIT",
    "BSD": "BSD-3-Clause",
    "BSD-3-Clause": "BSD-3-Clause",
    "BSD 3-Clause": "BSD-3-Clause",
    "BSD-2-Clause": "BSD-2-Clause",
    "ISC": "ISC",
    "MPL-2.0": "MPL-2.0",
    "MPL 2.0": "MPL-2.0",
    "Python-2.0": "Python-2.0",
}


def read_allowlist() -> dict[tuple[str, str], str]:
    """The table from CONTRIBUTING.md, keyed by (spdx, applies)."""
    rows: dict[tuple[str, str], str] = {}
    for line in CONTRIBUTING.read_text(encoding="utf-8").splitlines():
        match = _ROW.match(line.strip())
        if match:
            rows[(match["spdx"], match["applies"])] = match["decision"]
    return rows


def runtime_distributions() -> set[str]:
    """Distributions reachable from a workspace member's runtime dependencies.

    Anything else in the environment is development tooling. The distinction is
    what the two MPL-2.0 rows turn on, so it is computed rather than assumed.
    """
    seen: set[str] = set()
    frontier: list[str] = []

    packages_dir = REPO_ROOT / "packages"
    if packages_dir.is_dir():
        for manifest in sorted(packages_dir.glob("*/pyproject.toml")):
            project = tomllib.loads(manifest.read_text(encoding="utf-8")).get("project", {})
            frontier.extend(_requirement_names(project.get("dependencies", [])))

    while frontier:
        name = _canonical(frontier.pop())
        if name in seen:
            continue
        seen.add(name)
        try:
            requires = metadata.requires(name) or []
        except metadata.PackageNotFoundError:
            continue
        for requirement in requires:
            # A dependency guarded by an extra is not installed unless the
            # extra is requested, so it is not something a user receives.
            if "extra ==" in requirement:
                continue
            frontier.extend(_requirement_names([requirement]))
    return seen


def _requirement_names(requirements: list[str]) -> list[str]:
    names = []
    for requirement in requirements:
        head = re.split(r"[<>=!~;\[\s]", requirement, maxsplit=1)[0].strip()
        if head:
            names.append(head)
    return names


def _canonical(name: str) -> str:
    return re.sub(r"[-_.]+", "-", name).lower()


def spdx_of(dist: metadata.Distribution) -> str | None:
    """The SPDX id for a distribution, or None when nothing declares one."""
    meta = dist.metadata
    declared = meta.get("License-Expression")
    if declared:
        return declared.strip()

    for classifier in meta.get_all("Classifier") or []:
        if classifier.startswith("License ::"):
            tail = classifier.split(" :: ")[-1].strip()
            if tail in _CLASSIFIER_TO_SPDX:
                return _CLASSIFIER_TO_SPDX[tail]

    legacy = (meta.get("License") or "").strip()
    if legacy in _NORMALISE:
        return _NORMALISE[legacy]
    if legacy and len(legacy) < 40:
        return legacy
    return None


def decide(expression: str, placement: str, allowlist: dict[tuple[str, str], str]) -> str | None:
    """Resolve one SPDX expression against the allowlist.

    A license field is often an expression rather than a bare id: numpy ships
    "BSD-3-Clause AND 0BSD AND MIT AND Zlib AND CC0-1.0", and packaging ships
    "Apache-2.0 OR BSD-2-Clause". The two operators mean opposite things to a
    redistributor, so they are resolved rather than pattern-matched:

      AND  every term binds, so every term has to be accepted
      OR   the recipient picks, so one accepted term is enough

    Returns "Accepted", "Refused", or None when a term matches no row.
    """
    cleaned = expression.replace("(", " ").replace(")", " ").strip()

    if " OR " in cleaned.upper():
        outcomes = [
            decide(term.strip(), placement, allowlist)
            for term in re.split(r"(?i)\s+OR\s+", cleaned)
        ]
        if "Accepted" in outcomes:
            return "Accepted"
        return "Refused" if "Refused" in outcomes else None

    if " AND " in cleaned.upper():
        outcomes = [
            decide(term.strip(), placement, allowlist)
            for term in re.split(r"(?i)\s+AND\s+", cleaned)
        ]
        if "Refused" in outcomes:
            return "Refused"
        return "Accepted" if all(o == "Accepted" for o in outcomes) else None

    spdx = _NORMALISE.get(cleaned, cleaned)
    return allowlist.get((spdx, placement)) or allowlist.get((spdx, ANY))


def main() -> int:
    allowlist = read_allowlist()
    if not allowlist:
        sys.stderr.write("no allowlist table found in CONTRIBUTING.md\n")
        return 1

    workspace = {
        _canonical(name)
        for name in (
            tomllib.loads(ROOT_PYPROJECT.read_text(encoding="utf-8"))
            .get("tool", {})
            .get("uv", {})
            .get("sources", {})
        )
    }
    runtime = runtime_distributions() - workspace

    refused: list[str] = []
    unknown: list[str] = []
    checked = 0

    for dist in sorted(metadata.distributions(), key=lambda d: d.metadata["Name"] or ""):
        name = dist.metadata["Name"]
        if not name or _canonical(name) in workspace:
            continue
        checked += 1

        spdx = spdx_of(dist)
        placement = RUNTIME if _canonical(name) in runtime else DEV_ONLY

        if spdx is None:
            unknown.append(f"{name}: declares no license this gate can read")
            continue

        decision = decide(spdx, placement, allowlist)
        if decision == "Accepted":
            continue
        if decision == "Refused":
            refused.append(f"{name} {spdx} is refused for a dependency {placement.lower()}")
        else:
            unknown.append(f"{name}: {spdx} matches no row, placement {placement.lower()}")

    if refused or unknown:
        sys.stderr.write("\n\033[31mBLOCKED: license allowlist [SEC-001]\033[0m\n")
        for line in refused:
            sys.stderr.write(f"  refused  {line}\n")
        for line in unknown:
            sys.stderr.write(f"  unknown  {line}\n")
        sys.stderr.write(
            "\nThe allowlist is the table in CONTRIBUTING.md. A license with no row is\n"
            "a decision nobody has made: add a row with its reasoning, or drop the\n"
            "dependency. Two rows turn on placement, so check the Applies to column.\n"
        )
        return 1

    print(
        f"[license] {checked} distributions checked against the allowlist, "
        f"{len(runtime)} of them shipped at run time"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
