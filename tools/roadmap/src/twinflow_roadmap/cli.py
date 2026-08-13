"""The command line behind `just roadmap`.

argparse rather than a framework, because this package has to run on a checkout
that does not build, and every dependency is one more thing that has to install
before the roadmap can say what is wrong with the checkout.

Every command exits non-zero on a finding and prints one line per finding, in
file order, each carrying the file, the line, the rule id, and what to do.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from twinflow_roadmap import render as render_module
from twinflow_roadmap.coverage import check_coverage, missing_quotes
from twinflow_roadmap.drift import check_drift
from twinflow_roadmap.errors import Finding, RoadmapError
from twinflow_roadmap.graph import graph_lint, render_mermaid
from twinflow_roadmap.roadmap import Roadmap
from twinflow_roadmap.sync import apply_plan, build_plan

#: The repository root, from this file: tools/roadmap/src/twinflow_roadmap/cli.py
DEFAULT_ROOT = Path(__file__).resolve().parents[4]


def _print(findings: list[Finding]) -> None:
    for finding in sorted(findings, key=lambda item: (item.path, item.line or 0, item.rule)):
        sys.stderr.write(f"{finding}\n")


def _load(root: Path) -> Roadmap:
    try:
        return Roadmap.load(root)
    except RoadmapError as error:
        sys.stderr.write(f"BLOCKED: {error}\n")
        raise SystemExit(2) from error


def command_validate(args: argparse.Namespace) -> int:
    roadmap = _load(args.root)
    findings = roadmap.validate()
    if findings:
        sys.stderr.write(f"\nBLOCKED: the roadmap does not validate [{len(findings)} findings]\n")
        _print(findings)
        return 1
    print(
        f"[roadmap] {len(roadmap.phases)} phases, {len(roadmap.work_packages)} work packages, "
        f"{len(roadmap.gates)} gates, {len(roadmap.requirements)} requirements: valid"
    )
    print(f"[roadmap] open phase {roadmap.open_phase}, next phase {roadmap.next_phase}")
    return 0


def command_coverage(args: argparse.Namespace) -> int:
    roadmap = _load(args.root)
    report = check_coverage(roadmap)
    print(report.render())
    if args.quotes:
        missing = missing_quotes(roadmap)
        print("")
        print(
            f"verbatim clauses recorded: {len(roadmap.requirements) - len(missing)} of "
            f"{len(roadmap.requirements)}"
        )
        if missing:
            print(f"missing: {' '.join(missing)}")
    if not report.ok:
        sys.stderr.write(f"\nBLOCKED: coverage is not proved [{len(report.findings)} findings]\n")
        _print(report.findings)
        return 1
    return 0


def command_graph_lint(args: argparse.Namespace) -> int:
    roadmap = _load(args.root)
    findings = graph_lint(roadmap, args.root / "ROADMAP.md")
    if findings:
        sys.stderr.write("\nBLOCKED: the phase diagram disagrees with roadmap.yaml\n")
        _print(findings)
        return 1
    print(
        f"[roadmap] the ROADMAP.md phase diagram matches roadmap.yaml over "
        f"{len(roadmap.phases)} phases"
    )
    return 0


def command_drift(args: argparse.Namespace) -> int:
    roadmap = _load(args.root)
    report = check_drift(roadmap, offline=args.offline)
    for note in report.skipped:
        print(f"[roadmap] SKIP {note}")
    if not report.ok:
        sys.stderr.write("\nBLOCKED: the tracker and roadmap.yaml disagree\n")
        _print(report.findings)
        return 1
    print("[roadmap] no drift: the banned label does not exist and every policy holds")
    return 0


def command_render(args: argparse.Namespace) -> int:
    roadmap = _load(args.root)
    if args.check:
        findings = render_module.check(roadmap)
        if findings:
            sys.stderr.write(f"\nBLOCKED: {len(findings)} generated documents are stale\n")
            _print(findings)
            return 1
        print(f"[roadmap] {len(render_module.DOCUMENTS)} generated documents are current")
        return 0

    changed = render_module.write(roadmap)
    for path in changed:
        print(f"[roadmap] wrote {path.as_posix()}")
    if not changed:
        print(f"[roadmap] {len(render_module.DOCUMENTS)} generated documents were already current")
    return 0


def command_sync(args: argparse.Namespace) -> int:
    roadmap = _load(args.root)
    plan = build_plan(roadmap, offline=args.offline)
    print(plan.render())

    if not args.apply:
        if plan.operations:
            print(
                "\n[roadmap] dry run: nothing was changed. Re-run with --apply "
                "from a checkout to perform the operations above"
            )
        return 0

    # An apply that could not read the tracker compared nothing, so its empty
    # plan means "unknown" rather than "already in step". Exiting zero there
    # reports a projection that was never made, and the release ritual carries
    # on as though the tracker holds one.
    if plan.skipped:
        sys.stderr.write(
            "\nBLOCKED: the tracker was not read, so there is nothing to apply and no way "
            "to tell an up-to-date tracker from an unreachable one\n"
        )
        for note in plan.skipped:
            sys.stderr.write(f"  {note}\n")
        return 1

    refused = apply_plan(plan, roadmap, context=args.context)
    if refused:
        sys.stderr.write(
            f"\nBLOCKED: {len(refused)} operations were refused or failed in "
            f"context {args.context or 'a checkout'}\n"
        )
        for line in refused:
            sys.stderr.write(f"  {line}\n")
        return 1

    print(f"[roadmap] applied {len(plan.operations)} operations")
    return 0


def command_gates(args: argparse.Namespace) -> int:
    roadmap = _load(args.root)
    if args.phase:
        gate_ids = roadmap.exit_gates(args.phase)
        print(f"exit gates for {args.phase} ({len(gate_ids)}):")
    else:
        gate_ids = sorted(roadmap.gates)
        print(f"gate registry ({len(gate_ids)}):")
    for gate_id in gate_ids:
        gate = roadmap.gates[gate_id]
        standing = "standing" if gate.standing else "one phase"
        print(f"  {gate_id:<28}{gate.first_phase:<8}{gate.kind:<14}{gate.status:<12}{standing}")
    return 0


def command_render_mermaid(args: argparse.Namespace) -> int:
    roadmap = _load(args.root)
    print(render_mermaid(roadmap), end="")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="twinflow-roadmap", description=__doc__)
    parser.add_argument(
        "--root",
        type=Path,
        default=DEFAULT_ROOT,
        help="repository root holding roadmap.yaml (default: the checkout this package sits in)",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    validate = subparsers.add_parser(
        "validate", help="DAG acyclicity, reference integrity, and gate integrity"
    )
    validate.set_defaults(handler=command_validate)

    coverage = subparsers.add_parser(
        "coverage", help="prove every requirement id is placed, and print the unplaced ones"
    )
    coverage.add_argument(
        "--quotes",
        action="store_true",
        help="also report how many requirements carry their verbatim source clause",
    )
    coverage.set_defaults(handler=command_coverage)

    graph_lint = subparsers.add_parser(
        "graph-lint", help="re-parse the ROADMAP.md phase diagram and check it against the data"
    )
    graph_lint.set_defaults(handler=command_graph_lint)

    drift = subparsers.add_parser(
        "drift", help="check the tracker against roadmap.yaml and the banned-label policy"
    )
    drift.add_argument(
        "--offline",
        action="store_true",
        help="run the local half only, without contacting the tracker",
    )
    drift.set_defaults(handler=command_drift)

    render = subparsers.add_parser(
        "render", help="write the documents generated from the roadmap data"
    )
    render.add_argument(
        "--check",
        action="store_true",
        help="regenerate in memory and fail when a document on disk disagrees",
    )
    render.set_defaults(handler=command_render)

    sync = subparsers.add_parser(
        "sync", help="project roadmap.yaml onto the tracker. Prints the plan and changes nothing"
    )
    sync.add_argument(
        "--apply",
        action="store_true",
        help="perform the plan. Without it the plan is printed and nothing is changed",
    )
    sync.add_argument(
        "--context",
        default=None,
        help=(
            "the automation context applying this. Only a context .roadmap-sync.yaml "
            "allows may touch milestones, and none may mutate issues: that waits for a "
            "human running --apply from a checkout"
        ),
    )
    sync.add_argument(
        "--offline",
        action="store_true",
        help="compute nothing and report what a tracker read would have covered",
    )
    sync.set_defaults(handler=command_sync)

    gates = subparsers.add_parser("gates", help="print the gate registry")
    gates.add_argument("--phase", help="print the exit gates for one phase instead")
    gates.set_defaults(handler=command_gates)

    mermaid = subparsers.add_parser(
        "render-mermaid", help="print the phase graph as roadmap.yaml holds it"
    )
    mermaid.set_defaults(handler=command_render_mermaid)

    # TODO(WP-P0-13): `sync --dry-run` and `sync --apply`, which reconcile
    # GitHub milestones and issues against roadmap.yaml under the policy in
    # .roadmap-sync.yaml.
    # TODO(WP-P0-13): `render`, which regenerates ROADMAP.md, docs/gates.md,
    # and docs/dependency-graph.md and fails on a diff over those three paths.
    # TODO(WP-P0-14): `gate phase-exit <phase>`, which runs the standing gates
    # plus the gates whose first phase is that one.
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    return int(args.handler(args))


if __name__ == "__main__":
    raise SystemExit(main())
