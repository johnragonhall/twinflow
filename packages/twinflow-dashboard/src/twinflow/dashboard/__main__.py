"""The process entry point behind the `dashboard` service of the garage tier.

    python -m twinflow.dashboard
    python -m twinflow.dashboard --run-id demo-01 --epoch 2026-01-01T00:00:00Z

`deploy/garage/docker-compose.yaml` names this command and passes its settings
as environment, so every flag below reads its default from one, and the flag is
what a reader drives it by hand with.

TWO SETTINGS HAVE NO DEFAULT, AND THAT IS THE POINT

`DashboardConfig` requires `run_id` and `epoch` and defaults neither.
`config.py` says why for `epoch`, quoting `StationLineSpec`: a default read from
a wall clock puts a different value into two runs of one seed. `run_id` is the
same argument one step further out, because it is the identifier every command
this dashboard accepts is stamped against and attributed to.

Neither is in `profiles/micro_fulfillment.yaml`, whose `run:` block carries the
seed, the replication index, the tick rate, and the horizon. So both arrive from
the environment, and this module refuses to start without them rather than
inventing either. A dashboard that picked its own run id would attribute an
operator's command to a run nobody can find.

WHY THE CLOCK READS MONOTONIC TIME

`create_app` takes `clock` as a plain callable returning the current sim instant
in ticks, and uses it to stamp accepted commands into the append-only log. A
live dashboard attached to no scenario has no scheduler advancing a `SimClock`,
so the reading comes from elapsed real time since this process started, scaled
to the configured tick rate.

That is a wall-clock read, and it is confined to this file on purpose: this is
a process entry point, which `docs/design/foundations.md` lists among the paths
where an adapter reads real time. The anchor is monotonic rather than wall, for
the reason `PacedClock` gives, so a clock adjustment mid-run cannot move a
timestamp backwards and reorder the command log.

uvicorn is imported by `serve`, not here, so importing this package still costs
nothing but starlette.
"""

from __future__ import annotations

import argparse
import os
import time
from collections.abc import Callable
from datetime import datetime

from twinflow.dashboard.app import serve
from twinflow.dashboard.config import DashboardConfig

#: The container publishes through a loopback port mapping, so the process
#: inside it binds every interface and the host mapping is what narrows the
#: reach. A checkout running this by hand gets the loopback default instead.
DEFAULT_BIND = "127.0.0.1"
DEFAULT_PORT = 8080

_NANOSECONDS_PER_SECOND = 1_000_000_000


class ConfigurationError(ValueError):
    """A setting this process cannot start without, named rather than guessed."""


def monotonic_ticks(tick_hz: int) -> Callable[[], int]:
    """A sim-instant reader anchored at the instant it is built.

    Returns ticks since the anchor, never a translation of wall-clock time, so
    the value is a duration this process measured rather than a claim about
    what time it is anywhere.
    """
    # twinflow: allow-nondeterminism(TFD001) the process entry point of a live
    # dashboard, which has no scheduler advancing a clock for it.
    anchor_ns = time.monotonic_ns()

    def reader() -> int:
        elapsed_ns = time.monotonic_ns() - anchor_ns
        return elapsed_ns * tick_hz // _NANOSECONDS_PER_SECOND

    return reader


def _required(args_value: str | None, variable: str, flag: str) -> str:
    if args_value:
        return args_value
    raise ConfigurationError(
        f"{flag} is required, or {variable} in the environment. "
        f"The dashboard stamps every accepted command with it, and a value this "
        f"process chose for itself would attribute that command to a run nobody can find"
    )


def config_from(args: argparse.Namespace) -> DashboardConfig:
    """The validated config this process serves, or a named refusal."""
    run_id = _required(args.run_id, "TWINFLOW_RUN_ID", "--run-id")
    raw_epoch = _required(args.epoch, "TWINFLOW_EPOCH", "--epoch")
    try:
        epoch = datetime.fromisoformat(raw_epoch)
    except ValueError as exc:
        raise ConfigurationError(
            f"--epoch is an ISO 8601 instant, got {raw_epoch!r}: {exc}"
        ) from exc

    settings: dict[str, object] = {
        "bind": args.bind,
        "port": args.port,
        "run_id": run_id,
        "epoch": epoch,
        "tick_hz": args.tick_hz,
    }
    if args.api_base_url:
        settings["api_base_url"] = args.api_base_url
    # `model_validate` rather than the constructor, for the reason the test
    # helper gives: the mapping is typed `object` because `api_base_url` is
    # conditional, and unpacking it into the constructor asks the checker to
    # match `object` against every `Literal` annotation on the model. This
    # validates the same fields and raises the same refusals.
    return DashboardConfig.model_validate(settings)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="twinflow.dashboard", description="Serve the dashboard stub."
    )
    parser.add_argument(
        "--bind",
        default=os.environ.get("TWINFLOW_BIND", DEFAULT_BIND),
        help="the address to listen on",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=int(os.environ.get("TWINFLOW_PORT", DEFAULT_PORT)),
        help="the port to listen on",
    )
    parser.add_argument(
        "--api-base-url",
        default=os.environ.get("TWINFLOW_API_URL"),
        help="the origin twinflow-api answers on, read by the browser rather than by this process",
    )
    parser.add_argument(
        "--run-id",
        default=os.environ.get("TWINFLOW_RUN_ID"),
        help="the run this dashboard is attached to",
    )
    parser.add_argument(
        "--epoch",
        default=os.environ.get("TWINFLOW_EPOCH"),
        help="the sim epoch commands are stamped against, as an ISO 8601 instant",
    )
    parser.add_argument(
        "--tick-hz",
        type=int,
        default=int(
            os.environ.get("TWINFLOW_TICK_HZ", DashboardConfig.model_fields["tick_hz"].default)
        ),
        help="the tick resolution the epoch is counted in",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    config = config_from(args)
    serve(config, clock=monotonic_ticks(config.tick_hz))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
