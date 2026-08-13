"""Requirement RA-c: the historian's placement and the names it stores under.

The layer row in ARCHITECTURE.md section 4 is the requirement. A row in a table
is prose, and prose drifts away from code without anything failing, so the two
drift tests here read the table and compare it against the value the package
ships.

The six-level grammar those names obey is asserted in twinflow-config, which
now owns it. This package's share of the contract is what a series is called
and which layer answers for it, and that is what is left here.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from twinflow.config import NamingError, UnsPath
from twinflow.storage import HISTORIAN, LayerPlacement, series_for

REPO_ROOT = Path(__file__).resolve().parents[3]
ARCHITECTURE = REPO_ROOT / "ARCHITECTURE.md"

PORTAL = UnsPath(
    enterprise="twinflow",
    site="dc-01",
    area="receiving",
    line="inbound-line-01",
    equipment="portal-03",
    parameter="read_rate",
)


def _architecture_row(component: str) -> list[str]:
    """The layer-map row for one component, cell by cell."""
    for line in ARCHITECTURE.read_text(encoding="utf-8").splitlines():
        if not line.startswith("| "):
            continue
        cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
        if cells and cells[0] == component:
            return cells
    raise AssertionError(f"ARCHITECTURE.md has no layer-map row for {component!r}")


# --------------------------------------------------------------- RA-c, the row


@pytest.mark.skipif(not ARCHITECTURE.is_file(), reason="installed without the repository")
def test_the_historian_placement_matches_the_layer_map_row():
    component, isa95, purdue, counterpart = _architecture_row("Historian")

    assert component == HISTORIAN.component
    assert isa95 == HISTORIAN.isa95
    assert purdue == f"{HISTORIAN.purdue}, published into {HISTORIAN.published_into}"
    assert counterpart == HISTORIAN.counterpart


def test_the_historian_is_the_system_of_record_for_time_series():
    assert HISTORIAN.system_of_record_for == "time-series"
    assert HISTORIAN.isa95 == "L2"


def test_every_series_carries_the_placement_it_is_the_record_for():
    """RA-c in code: a name cannot be minted without the layer it answers for."""
    series = series_for(PORTAL)

    assert series.placement is HISTORIAN
    assert series.key == PORTAL.topic
    assert series.published_into == "L3.5"


def test_a_placement_is_immutable():
    with pytest.raises((AttributeError, TypeError)):
        HISTORIAN.isa95 = "L3"  # type: ignore[misc]


def test_a_placement_refuses_a_level_it_does_not_recognise():
    with pytest.raises(NamingError) as caught:
        LayerPlacement(
            component="Historian",
            isa95="Level 2",
            purdue="L3",
            published_into="L3.5",
            counterpart="",
            system_of_record_for="time-series",
        )
    assert caught.value.code == "TF-S006"
