"""Program management as code.

The roadmap is data. ROADMAP.md is its readable projection and the issue tracker
is its public one, and both are generated. That arrangement is what makes
"nothing is ever cut" a property something checks rather than a promise
somebody makes: a requirement with no coverage entry fails the build.

This package is a leaf. It imports nothing else in the workspace, because it has
to run on a checkout that does not yet build.
"""

from __future__ import annotations

# The entry points are named check_coverage and check_drift rather than
# coverage and drift, because a function exported beside a module of the
# same name shadows it: `from twinflow_roadmap import coverage` would then
# bind whichever of the two imported last, and the caller would not know
# which one it got.
from twinflow_roadmap.coverage import CoverageReport, check_coverage, missing_quotes
from twinflow_roadmap.drift import DriftReport, check_drift
from twinflow_roadmap.errors import Finding, RoadmapError
from twinflow_roadmap.graph import graph_lint, parse_mermaid, render_mermaid
from twinflow_roadmap.model import (
    PHASE_IDS,
    Coverage,
    Gate,
    Phase,
    Release,
    Requirement,
    Split,
    WorkPackage,
)
from twinflow_roadmap.roadmap import Roadmap, load

#: Read by tool.hatch.version, so this is the only place the version is written.
__version__ = "0.1.0"

__all__ = [
    "PHASE_IDS",
    "Coverage",
    "CoverageReport",
    "DriftReport",
    "Finding",
    "Gate",
    "Phase",
    "Release",
    "Requirement",
    "Roadmap",
    "RoadmapError",
    "Split",
    "WorkPackage",
    "__version__",
    "check_coverage",
    "check_drift",
    "graph_lint",
    "load",
    "missing_quotes",
    "parse_mermaid",
    "render_mermaid",
]
