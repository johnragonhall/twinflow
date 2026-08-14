"""The process entry point behind the `api` service of the garage tier.

    python -m twinflow.api
    python -m twinflow.api --bind 0.0.0.0 --port 8000

`deploy/garage/docker-compose.yaml` names this command and passes its settings
as environment, so every flag below reads its default from one, and the flag is
what a reader drives it by hand with.

WHAT THIS PROCESS SERVES TODAY

Nothing, and it says so through `/readyz`. `create_api` takes a mapping of run
id to `Historian`, and `Historian` is an in-memory object: no adapter in this
tree reads one back off disk, so `_recorded_runs` returns an empty mapping and
`/readyz` answers 503 with the reason `create_api` already carries. That is the
honest state rather than a defect of this module. A liveness probe passing over
an empty mapping would put a process into rotation with nothing to serve, which
is the failure `readyz` exists to refuse.

`_recorded_runs` is the seam the storage adapter fills. It is a named function
rather than a literal so that the run source has one place to arrive, and so a
reader looking for "where do the runs come from" finds the answer rather than
an empty dict inline.

WHY THE CLOCK IS A `SimClock` AT ZERO

Doctrine D-02 makes the clock a port, and `create_api` stamps every instant it
reports from the injected one. A wall clock here would put the host's time into
`/healthz` and into every ETag the section 5.13 rules make a content hash. The
clock advances when a run is loaded, which is the same edit that gives
`_recorded_runs` a body.

uvicorn is imported inside `main` for the reason `twinflow.dashboard.serve`
gives: nothing in this package imports it at module scope, so a reader
embedding `create_api` in their own server pays for it at install and never at
import.
"""

from __future__ import annotations

import argparse
import os
from collections.abc import Mapping

from twinflow.api.app import create_api
from twinflow.kernel import DEFAULT_TICK_HZ, SimClock
from twinflow.storage import Historian

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

    Empty until a storage adapter exists to read one back. `Historian` holds
    its log in memory and seals it there; `twinflow/storage/adapters/`, the
    path `docs/design/foundations.md` reserves for exactly this, carries no
    module yet. Returning an empty mapping rather than raising is deliberate:
    the process is live, answers `/healthz` and `/version`, and reports itself
    unready, which is three true statements instead of a crash loop.
    """
    del root
    return {}


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

    app = create_api(
        runs=_recorded_runs(args.historian_root),
        clock=SimClock(tick_hz=args.tick_hz),
    )

    import uvicorn

    uvicorn.run(app, host=args.bind, port=args.port)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
