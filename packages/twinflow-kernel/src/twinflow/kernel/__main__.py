"""The scenario entry point behind `just determinism`.

    python -m twinflow.kernel simulate --scenario S --seed N
    python -m twinflow.kernel simulate --scenario S --seed N --format hash

Writes the event log to stdout as JSON Lines, one envelope per line, in the
canonical total order. scripts/determinism-check.sh runs it twice and compares
the bytes, which is what DET-001 asserts.

This is a thin argparse over the scenario module and holds no behavior of
its own. `twinflow.cli` arrives with P1 and takes this subcommand over; the
check script reads TWINFLOW_SIM_CMD so that move costs one environment variable
rather than an edit to the gate.

--format hash prints only the tier-one determinism hash, which is what a CI job
records when it wants the number rather than the log.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from twinflow.kernel._impl import scenario as scenario_module
from twinflow.schemas import canonical_json
from twinflow.schemas.log_invariants import check_log_invariants, in_total_order, log_hash


def command_simulate(args: argparse.Namespace) -> int:
    scenario = scenario_module.load_scenario(args.scenario)
    events = scenario_module.run_scenario(scenario, seed=args.seed)

    # ENV-001 over the log this run just produced. A determinism gate that
    # hashed a log breaking the envelope invariants would report two identical
    # broken runs as a pass.
    violations = check_log_invariants(events)
    if violations:
        sys.stderr.write(f"BLOCKED: the run broke {len(violations)} log invariants\n")
        for violation in violations:
            sys.stderr.write(f"  {violation}\n")
        return 1

    if args.format == "hash":
        print(log_hash(events))
        return 0

    for event in in_total_order(events):
        payload = event.model_dump(mode="json", exclude_none=True)
        # sort_keys and the tight separators are what make the bytes a function
        # of the values rather than of the dict's insertion order.
        print(canonical_json(payload))
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="twinflow.kernel", description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)

    simulate = subparsers.add_parser("simulate", help="run one scenario and write its event log")
    simulate.add_argument(
        "--scenario",
        type=Path,
        default=Path("scenarios/determinism-smoke.yaml"),
        help="the scenario file to run",
    )
    simulate.add_argument(
        "--seed",
        type=int,
        default=None,
        help="override the run seed the scenario file carries",
    )
    simulate.add_argument(
        "--format",
        choices=("jsonl", "hash"),
        default="jsonl",
        help="the whole log, or only its tier-one determinism hash",
    )
    simulate.set_defaults(handler=command_simulate)

    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    return int(args.handler(args))


if __name__ == "__main__":
    raise SystemExit(main())
