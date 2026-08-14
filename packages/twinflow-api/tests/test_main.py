"""The process entry point: what it reads, and what it refuses to claim.

`main` itself is not called here. It ends in `uvicorn.run`, which blocks until
the process is signaled, so the tests drive the two functions underneath it:
the parser that turns environment and flags into settings, and the run source
that decides what this surface has to serve.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from twinflow.api.__main__ import (
    DEFAULT_BIND,
    DEFAULT_HISTORIAN_ROOT,
    DEFAULT_PORT,
    _clock_for,
    _recorded_runs,
    build_parser,
)
from twinflow.api.app import create_api
from twinflow.kernel import DEFAULT_TICK_HZ
from twinflow.storage import Historian, write_run

from .conftest import Client


def test_the_defaults_are_the_loopback_address_and_the_documented_port():
    args = build_parser().parse_args([])

    assert args.bind == DEFAULT_BIND
    assert args.port == DEFAULT_PORT
    assert args.tick_hz == DEFAULT_TICK_HZ
    assert args.historian_root == DEFAULT_HISTORIAN_ROOT


def test_every_setting_reads_from_the_environment(monkeypatch: pytest.MonkeyPatch):
    """The compose file passes settings as environment and no flags, so a
    default that ignored the environment would serve the wrong port with
    nothing failing at the time it happened."""
    monkeypatch.setenv("TWINFLOW_BIND", "0.0.0.0")  # noqa: S104 - what the container does
    monkeypatch.setenv("TWINFLOW_PORT", "9000")
    monkeypatch.setenv("TWINFLOW_TICK_HZ", "1000")
    monkeypatch.setenv("TWINFLOW_HISTORIAN_ROOT", "/srv/runs")

    args = build_parser().parse_args([])

    assert args.bind == "0.0.0.0"  # noqa: S104 - what the container does
    assert args.port == 9000
    assert args.tick_hz == 1000
    assert args.historian_root == "/srv/runs"


def test_a_flag_beats_the_environment(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("TWINFLOW_PORT", "9000")

    args = build_parser().parse_args(["--port", "8123"])

    assert args.port == 8123


def test_a_root_that_holds_nothing_yields_no_runs(tmp_path: Path):
    """An `api` container starting before anything has been recorded is the
    ordinary first run of the tier rather than an error."""
    assert dict(_recorded_runs(str(tmp_path))) == {}
    assert dict(_recorded_runs(str(tmp_path / "absent"))) == {}


def test_the_surface_reports_itself_unready_over_an_empty_run_source(tmp_path: Path):
    """A process with nothing to serve is live and not ready, and both are true
    at once. A readyz that passed here would put this container into rotation
    answering 404 for every run a caller asks for."""
    from twinflow.api.app import create_api

    runs = _recorded_runs(str(tmp_path))
    client = Client(create_api(runs=runs, clock=_clock_for(runs, DEFAULT_TICK_HZ)))

    assert client.get("/healthz").status_code == 200
    assert client.get("/readyz").status_code == 503


def test_a_recorded_run_is_read_back_and_served(tmp_path: Path, historian: Historian):
    """The end WP-P1-25 is for: a run that outlived its process, loaded into
    the shape `create_api` takes, answering on the versioned routes."""
    provenance = historian.seal(
        started_wall_utc=None,
        finished_wall_utc=None,
        host="reference-runner",
        packages={"twinflow-api": "0.1.0"},
    )
    write_run(historian, provenance, tmp_path)

    runs = _recorded_runs(str(tmp_path))
    client = Client(create_api(runs=runs, clock=_clock_for(runs, DEFAULT_TICK_HZ)))

    assert client.get("/readyz").status_code == 200
    listed = client.get("/api/v1/runs").json()
    assert [row["run_id"] for row in listed["runs"]] == [historian.snapshot.run_id]
    assert listed["runs"][0]["log_hash"] == historian.hash()


def test_the_clock_starts_at_the_latest_arrival_rather_than_at_zero(
    tmp_path: Path, historian: Historian
):
    """A surface reporting sim instant zero while serving events stamped later
    would describe a present that precedes its own data."""
    provenance = historian.seal(
        started_wall_utc=None,
        finished_wall_utc=None,
        host="reference-runner",
        packages={},
    )
    write_run(historian, provenance, tmp_path)
    runs = _recorded_runs(str(tmp_path))

    latest = max(
        int(runs[historian.snapshot.run_id].received_at(event.id))
        for event in runs[historian.snapshot.run_id].events()
    )

    assert int(_clock_for(runs, DEFAULT_TICK_HZ).now()) == latest
