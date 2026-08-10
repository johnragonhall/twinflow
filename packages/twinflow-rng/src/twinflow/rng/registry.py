"""The append-only registry of stream names.

Registration is append-only because a stream name is an address. Removing one
frees a name that a recorded run still refers to, and reusing it later points
an old log at new numbers with no error anywhere.

The naming grammar is section A.2 of docs/design/variability-and-faults.md, the
version suffix and the retirement marker are section A.3, and the stream-count
ceiling is section A.1a.
"""

from __future__ import annotations

import re
from collections import Counter
from collections.abc import Mapping

import numpy as np

from twinflow.rng.derive import generator_for

# Lowercase dotted segments. A braced segment is a template placeholder filled
# at resolution time with a stable entity id. The optional @vN suffix is the
# explicit draw-order version of section A.3: a stream whose draw order has to
# change gets a new address rather than new numbers under its current one.
_SEGMENT = r"(?:[a-z0-9_]+|\{[a-z0-9_]+\})"
_NAME = re.compile(rf"^{_SEGMENT}(?:\.{_SEGMENT})+(?:@v[1-9][0-9]*)?$")
_PLACEHOLDER = re.compile(r"\{([a-z0-9_]+)\}")

# Entity ids are deterministic slugs such as AMR-014 and CNV-02-VIB-01, so
# uppercase and hyphens are legal here and nowhere else in a stream name. A
# value carrying a dot would insert a segment and address a different stream,
# and a value carrying a brace would leave the placeholder in place. A device
# name is attacker-controlled in any real fleet, so the value is checked.
_ENTITY_ID = re.compile(r"^[A-Za-z0-9_-]{1,64}$")

#: A declared operating ceiling on catalog size, not a statistical one.
#: Set by the headroom rule of A.1a: at least ten times the largest stream
#: count any shipped scenario declares, which E.1 puts at 61402. That leaves
#: a full order of magnitude for the catalog to grow without review and still
#: fails on a runaway template expansion, which is the defect the check
#: exists to catch. Crossing it is a catalog review, not a bit-generator
#: decision.
#:
#: No published figure sets it, because none binds at this scale. The
#: governing collision bound under PCG64DXSM is a 128-bit SeedSequence pool
#: collision, 8.3e-28 here, and the PCG project's own overlap relation still
#: allows about 6.0e26 draws per stream at this count. G.14 records that
#: neither numpy nor the PCG project publishes a per-stream bound for
#: PCG64DXSM, G.15 carries the residual, and G.11 records the bit-generator
#: decision of 2026-08-09.
STREAM_COUNT_CEILING = 750_000


class StreamRegistry:
    """Holds the declared stream names for one run.

    Handout counts are recorded per stream so a run can publish which streams
    it touched. That record is what makes a divergence traceable to one stream
    rather than to the run as a whole.
    """

    def __init__(self, *, base_seed: int, replication_index: int = 0) -> None:
        self._base_seed = base_seed
        self._replication_index = replication_index
        # A dict rather than a set. Doctrine D-03 bans any collection whose
        # iteration order can reach an event, a hash, or a control decision,
        # and this one reaches declared_names(). Dict iteration is insertion
        # ordered in every supported Python version. The value is the
        # retirement marker of section A.3, or None while the name is live.
        self._declared: dict[str, str | None] = {}
        self._handouts: Counter[str] = Counter()

    def register(self, name: str, *, retired_at: str | None = None) -> None:
        if not _NAME.match(name):
            raise ValueError(
                f"{name!r} breaks the stream name grammar: lowercase dotted segments, "
                "at least two, with optional {placeholder} segments and an "
                "optional @vN draw-order suffix"
            )
        if name in self._declared:
            raise ValueError(f"{name!r} is already registered; registration is append-only")
        if len(self._declared) >= STREAM_COUNT_CEILING:
            raise ValueError(
                f"registering {name!r} crosses STREAM_COUNT_CEILING of "
                f"{STREAM_COUNT_CEILING}; that is a declared operating ceiling on "
                "catalog size set by the headroom rule of A.1a, so crossing it "
                "is a catalog review. A.1a records why no published bound sets "
                "the number and G.15 carries the residual"
            )
        self._declared[name] = retired_at

    def declared_names(self) -> tuple[str, ...]:
        """Every declared name, in registration order."""
        return tuple(self._declared)

    def get(self, name: str, **template_args: str) -> np.random.Generator:
        if name not in self._declared:
            raise KeyError(
                f"{name!r} is not registered. Declare it before drawing from it, so the "
                "catalog stays a complete record of the run's randomness."
            )
        retired_at = self._declared[name]
        if retired_at is not None:
            raise KeyError(f"{name!r} was retired at {retired_at}; draw from its successor instead")

        required = set(_PLACEHOLDER.findall(name))
        supplied = set(template_args)
        missing = sorted(required - supplied)
        if missing:
            raise ValueError(f"{name!r} needs template arguments: {missing}")
        unexpected = sorted(supplied - required)
        if unexpected:
            raise ValueError(f"{name!r} takes no template argument named {unexpected}")

        resolved = name
        for key in sorted(required):
            value = template_args[key]
            if not _ENTITY_ID.match(value):
                raise ValueError(
                    f"entity id {value!r} for {key!r} is not a slug of letters, digits, "
                    "underscores, and hyphens; a dot or a brace would address a "
                    "different stream"
                )
            resolved = resolved.replace("{" + key + "}", value)

        self._handouts[name] += 1
        return generator_for(
            resolved,
            base_seed=self._base_seed,
            replication_index=self._replication_index,
        )

    def handout_counts(self) -> Mapping[str, int]:
        """Generators handed out per declared name, sorted by name.

        This counts handouts, not draws. The draw counter that section A.6
        hashes into rng.draw_counts_sha256 counts calls through
        twinflow.kernel.numeric, which foundations 2.2a makes the only module
        allowed to call a Generator method, and it lands with that module. The
        two carry different names because the common-random-numbers pairing
        rule of section A.5 gives the wrong answer if it reads this one.

        Sorted because doctrine D-03 forbids an iteration order that can reach
        a hash from depending on insertion history.
        """
        return dict(sorted(self._handouts.items()))
