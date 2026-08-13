#!/usr/bin/env python3
"""The phase-exit gate runner.

    python scripts/checks/phase-exit-gate.py            the open phase
    python scripts/checks/phase-exit-gate.py P1         one named phase
    python scripts/checks/phase-exit-gate.py P1 --list  what would run, and nothing else

A tag is refused unless every gate in force at that phase passes. Which gates
those are is derived from gates.yaml rather than listed here: a gate whose
first phase is this one, plus every standing gate already in force. Deriving it
is what stops this runner and the registry disagreeing about what a release
promised.

A GATE THAT IS NOT IMPLEMENTED IS A FAILURE, NOT A SKIP
--------------------------------------------------------
The registry declares every gate at P0 with the phase it starts at, so a gate
in this phase's exit set has already been promised to be in force. If it is
still at status declared or specified, the promise is outstanding and the tag
is refused. The alternative is a runner that reports "12 gates, 8 skipped" and
a release note that says twelve.

This is why P0 does not exit today: DET-001 and DET-002 are in its set and are
not armed until the SCN-F1 scenario lands.
"""

from __future__ import annotations

import argparse
import subprocess
import sys
import time
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "tools" / "roadmap" / "src"))

from twinflow_roadmap.roadmap import Roadmap  # noqa: E402

GREEN, RED, YELLOW, RESET = "\033[32m", "\033[31m", "\033[33m", "\033[0m"


def run_gate(gate_id: str, command: str) -> tuple[bool, float]:
    """Run one gate's command from the repository root."""
    started = time.monotonic()
    result = subprocess.run(command, cwd=REPO_ROOT, shell=True)
    return result.returncode == 0, time.monotonic() - started


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("phase", nargs="?", help="the phase to exit. Default: the open phase.")
    parser.add_argument("--list", action="store_true", help="print the gate set and run none of it")
    args = parser.parse_args(argv)

    roadmap = Roadmap.load(REPO_ROOT)
    phase = args.phase or roadmap.open_phase
    if phase is None:
        sys.stderr.write("BLOCKED: no open phase, and no phase named on the command line\n")
        return 2
    if phase not in {p.id for p in roadmap.phases}:
        sys.stderr.write(f"BLOCKED: {phase} is not a phase in roadmap.yaml\n")
        return 2

    gate_ids = roadmap.exit_gates(phase)
    print(f"[phase-exit] {phase}: {len(gate_ids)} gates in force\n")

    unarmed: list[str] = []
    failed: list[str] = []
    passed: list[str] = []

    for gate_id in gate_ids:
        gate = roadmap.gates[gate_id]
        if gate.status != "implemented":
            unarmed.append(gate_id)
            marker = "standing" if gate.standing else f"first at {gate.first_phase}"
            print(f"{YELLOW}NOT ARMED{RESET} {gate_id:<24} status {gate.status}, {marker}")
            continue

        if args.list:
            print(f"          {gate_id:<24} {gate.command}")
            continue

        print(f"--- {gate_id} ---")
        ok, seconds = run_gate(gate_id, gate.command or "")
        if ok:
            passed.append(gate_id)
            print(f"{GREEN}PASS{RESET} {gate_id} ({seconds:.1f}s)\n")
        else:
            failed.append(gate_id)
            print(f"{RED}FAIL{RESET} {gate_id} ({seconds:.1f}s)\n")

    if args.list:
        return 0

    print(
        f"[phase-exit] {phase}: {len(passed)} passed, {len(failed)} failed, "
        f"{len(unarmed)} not armed"
    )

    if failed or unarmed:
        sys.stderr.write(f"\n{RED}BLOCKED: {phase} does not exit{RESET}\n")
        for gate_id in failed:
            sys.stderr.write(f"  failed     {gate_id}\n")
        for gate_id in unarmed:
            gate = roadmap.gates[gate_id]
            sys.stderr.write(
                f"  not armed  {gate_id} is at status {gate.status} and its first phase is "
                f"{gate.first_phase}, so it is already promised\n"
            )
        sys.stderr.write(
            "\nA gate in a phase's exit set was promised at P0 with the phase it starts\n"
            "at. Arm it, or move its first_phase in gates.yaml, which is a reviewed diff\n"
            "and a changelog entry rather than a quiet skip.\n"
        )
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
