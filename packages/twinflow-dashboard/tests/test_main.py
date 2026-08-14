"""The process entry point: the two settings it refuses to invent, and its clock.

`main` itself is not called here. It ends in `serve`, which blocks until the
process is signaled, so the tests drive the parser, the config builder, and the
clock underneath it.
"""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from twinflow.dashboard.__main__ import (
    DEFAULT_BIND,
    DEFAULT_PORT,
    ConfigurationError,
    build_parser,
    config_from,
    monotonic_ticks,
)


def parse(argv: list[str] | None = None):
    return build_parser().parse_args(argv or [])


def test_the_defaults_are_the_loopback_address_and_the_documented_port():
    args = parse()

    assert args.bind == DEFAULT_BIND
    assert args.port == DEFAULT_PORT


def test_a_missing_run_id_is_refused_by_name():
    """Section 6.2 defaults neither `run_id` nor `epoch`, and this process does
    not default them either. A dashboard that chose its own run id would stamp
    an operator's command against a run nobody can find."""
    args = parse(["--epoch", "2026-01-01T00:00:00+00:00"])

    with pytest.raises(ConfigurationError) as refusal:
        config_from(args)

    assert "--run-id" in str(refusal.value)
    assert "TWINFLOW_RUN_ID" in str(refusal.value)


def test_a_missing_epoch_is_refused_by_name():
    args = parse(["--run-id", "run-01"])

    with pytest.raises(ConfigurationError) as refusal:
        config_from(args)

    assert "--epoch" in str(refusal.value)
    assert "TWINFLOW_EPOCH" in str(refusal.value)


def test_an_epoch_that_is_not_an_instant_names_what_it_read():
    args = parse(["--run-id", "run-01", "--epoch", "last tuesday"])

    with pytest.raises(ConfigurationError) as refusal:
        config_from(args)

    assert "last tuesday" in str(refusal.value)


def test_both_settings_arrive_from_the_environment(monkeypatch: pytest.MonkeyPatch):
    """The compose file passes them as environment and no flags."""
    monkeypatch.setenv("TWINFLOW_RUN_ID", "run-01")
    monkeypatch.setenv("TWINFLOW_EPOCH", "2026-01-01T00:00:00+00:00")
    monkeypatch.setenv("TWINFLOW_API_URL", "http://api:8000")
    monkeypatch.setenv("TWINFLOW_BIND", "0.0.0.0")  # noqa: S104 - what the container does

    # The wide bind warns rather than refuses, because a container publishes
    # that way on purpose. Caught here so the warning is asserted rather than
    # printed past.
    with pytest.warns(UserWarning, match="every interface"):
        config = config_from(parse())

    assert config.run_id == "run-01"
    assert config.epoch == datetime(2026, 1, 1, tzinfo=UTC)
    assert config.api_base_url == "http://api:8000"
    assert config.bind == "0.0.0.0"  # noqa: S104 - what the container does


def test_an_unset_api_url_leaves_the_model_default_standing(monkeypatch: pytest.MonkeyPatch):
    """`api_base_url` defaults to the loopback origin the API binds by default,
    and passing `None` through would fail validation instead."""
    monkeypatch.delenv("TWINFLOW_API_URL", raising=False)

    config = config_from(parse(["--run-id", "run-01", "--epoch", "2026-01-01T00:00:00+00:00"]))

    assert config.api_base_url == "http://127.0.0.1:8000"


def test_a_refused_origin_still_fails_at_construction(monkeypatch: pytest.MonkeyPatch):
    """The entry point adds no validation of its own and takes none away. An
    origin carrying a policy separator is refused by the model, which is where
    the content security policy is assembled."""
    monkeypatch.setenv("TWINFLOW_API_URL", "http://api;script-src *")

    with pytest.raises(ValueError, match="content security policy"):
        config_from(parse(["--run-id", "run-01", "--epoch", "2026-01-01T00:00:00+00:00"]))


# ----------------------------------------------------------------------- clock


def test_the_clock_starts_at_its_anchor_and_never_runs_backwards():
    reader = monotonic_ticks(1_000_000)

    readings = [reader() for _ in range(8)]

    assert readings[0] >= 0
    assert readings == sorted(readings)


def test_the_clock_reports_ticks_rather_than_seconds():
    """Two readers built in the same instant, at tick rates a thousand apart.
    The faster one counts at least as many ticks over the same elapsed span,
    which a reader returning seconds would not."""
    fast = monotonic_ticks(1_000_000_000)
    slow = monotonic_ticks(1_000)

    # Ordered fast-then-slow so the slow reader measures the longer span. It
    # still cannot exceed the fast one unless the scaling is wrong.
    fast_ticks, slow_ticks = fast(), slow()

    assert fast_ticks >= slow_ticks
