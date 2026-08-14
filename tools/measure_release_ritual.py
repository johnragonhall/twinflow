#!/usr/bin/env python
"""Measure the release ritual, step by step, and derive its ceiling.

`ci_budget.yaml` records the ceiling behind VAL-GATE-RELBUD-001 as null while
the steps behind it are unmeasured, and says why: a ceiling computed from nulls
is a number nobody measured, and a gate asserting it passes because nothing can
fail it. This produces the measurements that replace those nulls.

Only the steps that run at the tag being cut are timed. A step whose input
arrives at a later phase contributes nothing to the ritual's wall time today, so
including it would put a zero into a sum that is meant to be a measurement. Each
such step keeps its null and names the phase it arrives with, and the ceiling
covers the steps that ran.

The ceiling is the measured sum times the margin ratio the same file records.
Both halves are read from the file rather than restated here.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
BUDGET = REPO_ROOT / "ci_budget.yaml"

#: What each ritual step of docs/design/roadmap.md 5.11 runs, for the steps a
#: tag at P1 executes. A step absent here is one whose input arrives later; it
#: keeps its null rather than contributing a zero.
STEP_COMMANDS: dict[str, tuple[str, ...]] = {
    "check": ("just", "check"),
    "property": ("just", "test-property"),
    "e2e": ("just", "test-e2e"),
    "phase-exit": ("just", "gate", "phase-exit", "P1"),
    "readme-metric": (
        "uv",
        "run",
        "--no-sync",
        "python",
        "scripts/checks/docs-gate.py",
        "--release",
        "0.2.0",
    ),
}


def time_step(name: str, command: tuple[str, ...]) -> tuple[float, int]:
    """Wall seconds and exit code for one step.

    Wall clock is the quantity under measurement, which is the one place in this
    repository a real clock is the right reading rather than a determinism
    defect.
    """
    started = time.perf_counter()
    result = subprocess.run(  # noqa: S603 - fixed argv, no shell
        command,
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    return (time.perf_counter() - started, result.returncode)


def margin_ratio() -> float:
    """The margin the budget file records, read rather than restated."""
    import yaml

    document = yaml.safe_load(BUDGET.read_text(encoding="utf-8"))
    return float(document["release"]["margin_ratio"])


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, help="write the measurement as JSON here")
    args = parser.parse_args(argv)

    # Every step, always. A ceiling derived from a subset is not the ritual's
    # ceiling, and a caller who could ask for one could produce a number that
    # reads like a measurement of something it never measured. No argument
    # selects what runs, so the argv reaching `subprocess.run` is exactly the
    # table above.
    measured: dict[str, float] = {}
    failed: list[str] = []
    for name, command in STEP_COMMANDS.items():
        seconds, code = time_step(name, command)
        status = "ok" if code == 0 else f"exit {code}"
        print(f"[ritual] {name:14} {seconds:8.1f} s  {status}")
        if code != 0:
            failed.append(name)
        measured[name] = round(seconds, 1)

    if failed:
        print(f"[ritual] {', '.join(failed)} did not pass, so this is not a ritual measurement")
        return 1

    total = round(sum(measured.values()), 1)
    ceiling = round(total * margin_ratio(), 1)
    print(f"[ritual] measured sum {total} s, ceiling {ceiling} s at the recorded margin")

    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(
            json.dumps(
                {"steps": measured, "measured_sum_s": total, "ceiling_s": ceiling},
                indent=2,
                sort_keys=True,
            )
            + "\n",
            encoding="utf-8",
        )
        print(f"[ritual] wrote {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
