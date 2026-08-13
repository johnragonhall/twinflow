"""Compare two recorded runs across platforms, for DET-002.

    uv run python tools/compare_runs.py left.jsonl right.jsonl
    uv run python tools/compare_runs.py left.jsonl right.jsonl --tolerance 1e-9

Doctrine D-05 has two tiers, and they are different claims:

  tier one   byte-identical logs on the pinned reference runner. DET-001, and
             a sha256 of the file answers it.
  tier two   identical business events everywhere else, with continuous fields
             agreeing inside a tolerance derived from measured divergence.
             DET-002, which is what this tool answers.

Tier two exists because IEEE-754 arithmetic is not reproducible across
platforms in the last bits, and pretending otherwise produces a gate that fails
for reasons nothing in the codebase caused. It is not a license to ignore
divergence: a business event that differs is a failure whatever the tolerance,
and the observed maximum is published on every run whatever it is.

WHAT COUNTS AS CONTINUOUS
-------------------------
A float in the payload. Everything else, the event type, the ordering key, the
identifiers, the counts, and every integer, is a business field and has to
match exactly. That rule is mechanical rather than a per-field list, because a
list is a thing somebody forgets to add a field to, and a field nobody added
would be compared with a tolerance nobody intended.

NO TOLERANCE IS ASSERTED UNTIL ONE IS MEASURED
-----------------------------------------------
gates.yaml records DET-002's noise floor as not yet measured. Until a
two-platform run sets it, this tool publishes the divergence it observed and
fails only on a business-event difference. Passing `--tolerance` asserts a
bound, and the release that first records one is what turns that on.
"""

from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

#: The envelope fields that order the log. A difference in any of them is a
#: different log, not a different rounding.
ORDER_FIELDS = ("twinflowsimts", "twinflowproducerid", "twinflowseq")


def read_log(path: Path) -> list[dict]:
    """One JSON Lines event log."""
    events = []
    for line_no, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        try:
            events.append(json.loads(line))
        except json.JSONDecodeError as error:
            raise SystemExit(f"BLOCKED: {path}:{line_no} is not JSON: {error}") from error
    return events


def flatten(value: object, prefix: str = "") -> dict[str, object]:
    """Every leaf in an event, keyed by its path.

    Flattening rather than walking two structures in step, because two events
    that disagree about which keys exist have to report that as a finding
    rather than raising a KeyError on the first one.
    """
    if isinstance(value, dict):
        leaves: dict[str, object] = {}
        for key, item in value.items():
            leaves.update(flatten(item, f"{prefix}.{key}" if prefix else str(key)))
        return leaves
    if isinstance(value, list):
        leaves = {}
        for index, item in enumerate(value):
            leaves.update(flatten(item, f"{prefix}[{index}]"))
        return leaves
    return {prefix: value}


def compare(
    left: list[dict], right: list[dict], tolerance: float | None
) -> tuple[list[str], float]:
    """Findings, and the largest relative divergence seen in a continuous field."""
    findings: list[str] = []
    worst = 0.0

    if len(left) != len(right):
        findings.append(
            f"event count differs: {len(left)} against {len(right)}. A run that "
            f"produced a different number of events did different work"
        )

    for index, (one, other) in enumerate(zip(left, right, strict=False)):
        one_leaves, other_leaves = flatten(one), flatten(other)

        for field in ORDER_FIELDS:
            if one.get(field) != other.get(field):
                findings.append(
                    f"event {index}: ordering field {field} differs, "
                    f"{one.get(field)!r} against {other.get(field)!r}"
                )

        missing = set(one_leaves) ^ set(other_leaves)
        for key in sorted(missing):
            findings.append(f"event {index}: field {key!r} is present in one log and not the other")

        for key in sorted(set(one_leaves) & set(other_leaves)):
            a, b = one_leaves[key], other_leaves[key]
            if a == b:
                continue

            # bool before float: in Python a bool is an int, and an int is not
            # a continuous field however it compares.
            if isinstance(a, float) and isinstance(b, float) and not isinstance(a, bool):
                divergence = relative_divergence(a, b)
                worst = max(worst, divergence)
                if tolerance is not None and divergence > tolerance:
                    findings.append(
                        f"event {index}: continuous field {key!r} diverges by "
                        f"{divergence:.3e}, over the recorded tolerance of {tolerance:.3e}"
                    )
                continue

            findings.append(
                f"event {index}: business field {key!r} differs, {a!r} against {b!r}. "
                f"A business event is identical on every platform or the run is not "
                f"the same run"
            )

    return findings, worst


def relative_divergence(a: float, b: float) -> float:
    """How far apart two floats are, relative to their size.

    Relative rather than absolute, because an absolute bound that suits a
    service time in seconds is meaningless for a cost in cents. Near zero the
    denominator falls back to 1, so the measure stays defined rather than
    dividing by nothing.
    """
    if math.isnan(a) and math.isnan(b):
        return 0.0
    if math.isinf(a) or math.isinf(b) or math.isnan(a) or math.isnan(b):
        return math.inf
    scale = max(abs(a), abs(b), 1.0)
    return abs(a - b) / scale


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("left", type=Path, help="one run's JSON Lines log")
    parser.add_argument("right", type=Path, help="the other platform's log")
    parser.add_argument(
        "--tolerance",
        type=float,
        default=None,
        help=(
            "the relative bound continuous fields must agree within. Without one, "
            "divergence is published and no bound is asserted, which is what "
            "gates.yaml records for DET-002 until a two-platform run measures it"
        ),
    )
    parser.add_argument(
        "--label-left", default=None, help="what to call the left log in the report"
    )
    parser.add_argument(
        "--label-right", default=None, help="what to call the right log in the report"
    )
    args = parser.parse_args(argv)

    left_label = args.label_left or str(args.left)
    right_label = args.label_right or str(args.right)

    findings, worst = compare(read_log(args.left), read_log(args.right), args.tolerance)

    # Published on every run whatever it is, per D-05. A divergence nobody
    # printed is a divergence nobody can set a tolerance from later.
    print(f"[det-002] {left_label} against {right_label}")
    print(f"[det-002] maximum relative divergence in a continuous field: {worst:.6e}")
    if args.tolerance is None:
        print(
            "[det-002] no tolerance asserted: gates.yaml records this noise floor as "
            "not yet measured, so this run publishes the number and bounds nothing"
        )
    else:
        print(f"[det-002] tolerance asserted: {args.tolerance:.6e}")

    if findings:
        sys.stderr.write("\n\033[31mBLOCKED: cross-platform divergence [DET-002]\033[0m\n")
        for finding in findings[:50]:
            sys.stderr.write(f"  {finding}\n")
        if len(findings) > 50:
            sys.stderr.write(f"  ... and {len(findings) - 50} more\n")
        return 1

    print("[det-002] every business event is identical across the two platforms")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
