"""The process entry point: what it reads, and what it refuses to claim.

`main` itself is not called here. It ends in `uvicorn.run`, which blocks until
the process is signaled, so the tests drive the two functions underneath it:
the parser that turns environment and flags into settings, and the run source
that decides what this surface has to serve.
"""

from __future__ import annotations

import pytest

from twinflow.api.__main__ import (
    DEFAULT_BIND,
    DEFAULT_HISTORIAN_ROOT,
    DEFAULT_PORT,
    _recorded_runs,
    build_parser,
)
from twinflow.kernel import DEFAULT_TICK_HZ, SimClock

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


def test_the_run_source_is_empty_while_no_storage_adapter_exists():
    """`Historian` holds its log in memory and no module reads one back off
    disk, so this returns nothing. The test states the gap rather than asserting
    a placeholder is correct: it fails the day an adapter lands, which is the
    day this function owes a body."""
    assert dict(_recorded_runs(DEFAULT_HISTORIAN_ROOT)) == {}


def test_the_surface_reports_itself_unready_over_an_empty_run_source():
    """A process with nothing to serve is live and not ready, and both are true
    at once. A readyz that passed here would put this container into rotation
    answering 404 for every run a caller asks for."""
    from twinflow.api.app import create_api

    app = create_api(runs=_recorded_runs(DEFAULT_HISTORIAN_ROOT), clock=SimClock())
    client = Client(app)

    assert client.get("/healthz").status_code == 200
    assert client.get("/readyz").status_code == 503
