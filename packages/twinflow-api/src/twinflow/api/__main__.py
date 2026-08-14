"""The process entry point behind the `api` service of the garage tier.

    python -m twinflow.api
    python -m twinflow.api --bind 0.0.0.0 --port 8000

`deploy/garage/docker-compose.yaml` names this command and passes its settings
as environment, so every flag below reads its default from one, and the flag is
what a reader drives it by hand with.

WHAT THIS PROCESS SERVES

Every run directory under `--historian-root`, read back by
`twinflow.storage.discover_runs`. A root holding nothing is not an error: the
mapping comes back empty, `/readyz` answers 503 with the reason `create_api`
carries, and the process stays live. A liveness probe passing over an empty
mapping would put a container into rotation with nothing to serve, which is the
failure `readyz` exists to refuse.

A directory that fails to load fails the start. `read_run` re-hashes the log it
replayed and compares it to the sidecar, so a run that has been edited or
truncated raises rather than being served, and this process would rather not
start than publish a `log_hash` describing a log nobody has.

WHY THE CLOCK IS A `SimClock` AT THE LAST ARRIVAL

Doctrine D-02 makes the clock a port, and `create_api` stamps every instant it
reports from the injected one. A wall clock here would put the host's time into
`/healthz` and into every ETag the section 5.13 rules make a content hash. The
clock starts at the latest arrival across the runs loaded, because a surface
reporting sim instant zero while serving events stamped later would describe a
present that precedes its own data.

uvicorn is imported inside `main` for the reason `twinflow.dashboard.serve`
gives: nothing in this package imports it at module scope, so a reader
embedding `create_api` in their own server pays for it at install and never at
import.
"""

from __future__ import annotations

import argparse
import os
from collections.abc import Mapping
from pathlib import Path

from twinflow.api.app import create_api
from twinflow.kernel import DEFAULT_TICK_HZ, SimClock, SimInstant
from twinflow.storage import Historian, discover_runs

#: Where the historian's recorded runs land in the garage tier. Read from the
#: environment so the container's mount point and a local checkout can differ.
DEFAULT_HISTORIAN_ROOT = "/var/lib/twinflow"

#: The container publishes through a loopback port mapping, so the process
#: inside it binds every interface and the host mapping is what narrows the
#: reach. A checkout running this by hand gets the loopback default instead.
DEFAULT_BIND = "127.0.0.1"
DEFAULT_PORT = 8000


def _recorded_runs(root: str) -> Mapping[str, Historian]:
    """The runs on disk under `root`, as historians.

    Sorted by run id, because `discover_runs` reads the directory in sorted
    order per doctrine D-03, so two `api` containers over one volume list their
    runs the same way and a cursor pages identically on both.
    """
    return discover_runs(Path(root))


def _clock_for(runs: Mapping[str, Historian], tick_hz: int) -> SimClock:
    """A clock at the latest arrival across every run loaded.

    Zero would have this surface reporting a present that precedes its own
    data, and `create_api` reads `clock.now()` for `/healthz`. The reading is
    taken from the runs rather than from the wall, so two processes over one
    volume report the same instant.
    """
    clock = SimClock(tick_hz=tick_hz)
    arrivals = [
        int(historian.received_at(event.id))
        for historian in runs.values()
        for event in historian.events()
    ]
    if arrivals:
        clock.advance_to(SimInstant(max(arrivals)))
    return clock


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="twinflow.api", description="Serve the REST surface.")
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
        "--tick-hz",
        type=int,
        default=int(os.environ.get("TWINFLOW_TICK_HZ", DEFAULT_TICK_HZ)),
        help="the tick resolution of the clock this surface reports instants from",
    )
    parser.add_argument(
        "--historian-root",
        default=os.environ.get("TWINFLOW_HISTORIAN_ROOT", DEFAULT_HISTORIAN_ROOT),
        help="the directory recorded runs are read from",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)

    runs = _recorded_runs(args.historian_root)
    app = create_api(runs=runs, clock=_clock_for(runs, args.tick_hz))

    import uvicorn

    uvicorn.run(app, host=args.bind, port=args.port)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
