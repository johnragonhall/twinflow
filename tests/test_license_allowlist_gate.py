"""The license allowlist gate (SEC-001).

Repository policy gates live in scripts/checks and are not part of any
distribution, so their tests live here rather than inside a package.

The decision logic is what these pin. Two things about it are easy to get
wrong, and both change the answer for a redistributor:

    AND  every term binds, so one refused term refuses the whole expression
    OR   the recipient picks, so one accepted term accepts it

and MPL-2.0, which is accepted for a development dependency and refused for one
shipped at run time.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
GATE = REPO_ROOT / "scripts" / "checks" / "license-allowlist-gate.py"


def _gate():
    spec = importlib.util.spec_from_file_location("license_allowlist_gate", GATE)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


gate = _gate()
allowlist = gate.read_allowlist()


def test_the_allowlist_parses_out_of_contributing():
    """The table a contributor reads is the table CI enforces.

    Parsed rather than copied, because a second copy is a copy that drifts.
    """
    assert len(allowlist) >= 10
    assert allowlist[("MIT", gate.ANY)] == "Accepted"


@pytest.mark.parametrize(
    "expression,placement,decision",
    [
        ("MIT", gate.RUNTIME, "Accepted"),
        ("Apache-2.0", gate.RUNTIME, "Accepted"),
        ("AGPL-3.0", gate.RUNTIME, "Refused"),
        ("GPL-2.0", gate.DEV_ONLY, "Refused"),
        ("GPL-3.0", gate.DEV_ONLY, "Refused"),
        # The two rows that turn on placement rather than on the id.
        ("MPL-2.0", gate.DEV_ONLY, "Accepted"),
        ("MPL-2.0", gate.RUNTIME, "Refused"),
        # Expressions, which most of the ecosystem now publishes.
        ("BSD-3-Clause AND 0BSD AND MIT AND Zlib AND CC0-1.0", gate.RUNTIME, "Accepted"),
        ("Apache-2.0 OR BSD-2-Clause", gate.DEV_ONLY, "Accepted"),
        ("MIT AND AGPL-3.0", gate.RUNTIME, "Refused"),
        ("MIT OR AGPL-3.0", gate.RUNTIME, "Accepted"),
        # Spelled one way by the allowlist and another by the ecosystem.
        ("PSF-2.0", gate.RUNTIME, "Accepted"),
        # No row at all is not a silent pass.
        ("WTFPL", gate.RUNTIME, None),
        ("MIT AND WTFPL", gate.RUNTIME, None),
    ],
)
def test_decision_table(expression, placement, decision):
    assert gate.decide(expression, placement, allowlist) == decision


def test_an_and_expression_refuses_when_any_term_refuses():
    """The asymmetry worth stating: AND binds every term on the redistributor."""
    assert gate.decide("MIT AND MPL-2.0", gate.RUNTIME, allowlist) == "Refused"
    assert gate.decide("MIT AND MPL-2.0", gate.DEV_ONLY, allowlist) == "Accepted"


def test_the_installed_tree_passes_the_gate():
    """SEC-001 over what is actually resolved, rather than what a manifest claims."""
    assert gate.main() == 0
