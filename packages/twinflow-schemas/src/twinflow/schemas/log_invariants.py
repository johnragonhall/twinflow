"""The log invariants behind gates ENV-001 and DET-001.

ENV-001 is doctrine D-07 stated over a whole log rather than over one event:
every event carries a producer, the sequence is dense per producer, and
(sim_ts, producer, seq) totally orders the log. A gap, a duplicate, or a tie
fails it.

Each of the three catches a different failure, and none of them substitutes for
the others:

    a gap       an event was dropped between producer and log
    a duplicate an event was written twice, so a replay counts it twice
    a tie       two events claim one position, so the order is not a function
                of the log and two readers can disagree about what happened

DET-001 is tier one of doctrine D-05: two runs at one seed, one config, one
platform, and one pinned dependency set produce byte-identical logs. The hash
here is what "identical" means, and it is computed over the ordering key and
the payload rather than over the file, so a difference in whitespace or in key
order is not mistaken for a difference in behavior.
"""

from __future__ import annotations

import hashlib
import json
from collections import defaultdict
from collections.abc import Iterable, Sequence
from dataclasses import dataclass

from twinflow.schemas.envelope import Envelope


@dataclass(frozen=True)
class LogViolation:
    """One way a log breaks ENV-001."""

    rule: str
    message: str

    def __str__(self) -> str:
        return f"[{self.rule}] {self.message}"


def check_log_invariants(events: Sequence[Envelope]) -> list[LogViolation]:
    """Every ENV-001 violation in one log, as one entry each.

    An empty log is valid. A run that produced nothing is a run that produced
    nothing, and reporting that as a violation would make the gate fire on
    every scenario that has not started.
    """
    violations: list[LogViolation] = []

    by_producer: dict[str, list[int]] = defaultdict(list)
    seen_ids: dict[str, int] = {}
    positions: dict[tuple[int, str, int], int] = {}

    for index, event in enumerate(events):
        producer = event.twinflowproducerid
        sequence = int(event.twinflowseq)
        by_producer[producer].append(sequence)

        if event.id in seen_ids:
            violations.append(
                LogViolation(
                    "ENV-001-duplicate-id",
                    f"event id {event.id!r} appears at positions "
                    f"{seen_ids[event.id]} and {index}; a replay would count it twice",
                )
            )
        else:
            seen_ids[event.id] = index

        key = Envelope.total_order_key(event)
        comparable = (key[0], key[1].decode("utf-8"), key[2])
        if comparable in positions:
            violations.append(
                LogViolation(
                    "ENV-001-tie",
                    f"positions {positions[comparable]} and {index} share the ordering key "
                    f"{comparable}; the order is not a function of the log, so two readers "
                    f"can disagree about what happened",
                )
            )
        else:
            positions[comparable] = index

    for producer in sorted(by_producer):
        sequences = sorted(by_producer[producer])
        expected = list(range(len(sequences)))
        if sequences != expected:
            missing = sorted(set(expected) - set(sequences))
            repeated = sorted({s for s in sequences if sequences.count(s) > 1})
            detail = []
            if missing:
                detail.append(f"missing {missing}")
            if repeated:
                detail.append(f"repeated {repeated}")
            if not detail:
                detail.append(f"runs {sequences[0]}..{sequences[-1]}")
            violations.append(
                LogViolation(
                    "ENV-001-not-dense",
                    f"producer {producer!r} has {len(sequences)} events, so its sequence "
                    f"has to be exactly 0..{len(sequences) - 1}: " + ", ".join(detail),
                )
            )

    return violations


def in_total_order(events: Iterable[Envelope]) -> list[Envelope]:
    """The log in canonical replay order, per invariant E4."""
    return sorted(events, key=Envelope.total_order_key)


def log_hash(events: Iterable[Envelope]) -> str:
    """The tier-one determinism hash of doctrine D-05.

    Computed over the canonical order and a canonical encoding rather than over
    the bytes of a file. Two runs that agree on every event but serialize their
    keys in a different order are the same run, and a hash that disagreed about
    that would make DET-001 fire on a formatting change.
    """
    digest = hashlib.blake2b(digest_size=32, person=b"twinflow-log")
    for event in in_total_order(events):
        payload = event.model_dump(mode="json", exclude_none=True)
        digest.update(json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8"))
        digest.update(b"\x1e")
    return digest.hexdigest()


def compare_runs(left: Sequence[Envelope], right: Sequence[Envelope]) -> list[str]:
    """Why two runs differ, or an empty list when they are identical.

    A hash tells you that two runs differ. It does not tell you where, and
    "the logs differ" is not something anybody can act on, so the first
    divergence is named.
    """
    if log_hash(left) == log_hash(right):
        return []

    findings: list[str] = []
    ordered_left = in_total_order(left)
    ordered_right = in_total_order(right)

    if len(ordered_left) != len(ordered_right):
        findings.append(f"event count differs: {len(ordered_left)} against {len(ordered_right)}")

    for index, (one, other) in enumerate(zip(ordered_left, ordered_right, strict=False)):
        if one == other:
            continue
        findings.append(
            f"first divergence at position {index}: "
            f"{one.type} seq {one.twinflowseq} from {one.twinflowproducerid} "
            f"against {other.type} seq {other.twinflowseq} from {other.twinflowproducerid}"
        )
        break

    return findings
