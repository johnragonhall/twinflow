"""A UHF RFID portal reader, modeled as the inventory it actually produces.

WP-P1-02, and the `rfid_portal_reader_uhf` catalog entry of
docs/design/iot-fleet.md 3.1. Read outcomes belong to the RF layer; what this
module owns is the reader-side aggregation and the telemetry that reaches the
UNS.

The design decision that drives everything below: a portal reader speaking EPC
Gen2 does not hand you one event per tag. It hands you an inventory of reads,
and one tag sitting in a read zone produces hundreds of them per interval
across several antennas. A model that emits one event per tag is not a simpler
model of the same device, it is a model of a different device, and every
downstream read-rate statistic computed from it is wrong.

Four rules here were defects somewhere before they were code:

- The running mean weights an incoming sample by its READ COUNT, not by one. A
  batch of three hundred reads at -60 dBm and a single read at -40 dBm is not a
  mean of -50.
- An EMPTY EPC prefix filter is refused. An empty prefix matches every tag, so
  accepting one silently disables the filtering a read zone depends on, and
  nothing observable fails at the time.
- Accumulation is bounded, and at the cap only NEW EPCs are dropped while
  already-tracked ones keep updating. What was dropped is published, because
  silent data loss is the defect rather than the loss itself.
- A reader that is unreachable and a reader that is reachable but has read
  nothing are two faults and are never conflated. The second is the silent one:
  a portal that answers every health check while reading nothing looks perfect
  on a dashboard, and the threshold that catches it is a calibration knob
  rather than a constant of nature.

Absent is not zero throughout. A value that could not be read is omitted from
the published payload, never published as a fake zero that a control chart
would treat as a real observation.
"""

from __future__ import annotations

import re
from collections.abc import Iterator, Mapping, Sequence
from dataclasses import dataclass
from enum import StrEnum
from typing import Any

from twinflow.config import UnsPath
from twinflow.kernel import SimInstant

#: A Gen2 EPC is 96 bits written as 24 hexadecimal characters. Uppercase is the
#: canonical spelling, and accepting both cases would make one tag two keys in
#: the aggregation below.
EPC = re.compile(r"^[0-9A-F]{24}$")

#: Hexadecimal, because a prefix that is not a prefix of any legal EPC can only
#: ever match nothing, and a filter that silently matches nothing is the same
#: class of defect as one that silently matches everything.
HEX_PREFIX = re.compile(r"^[0-9A-F]+$")

#: The number of hexadecimal characters in an EPC, so a prefix cannot be longer.
EPC_LENGTH = 24

#: Plausible portal RSSI sits roughly in this band, with the reader's configured
#: sensitivity acting as the floor. Declared here as the band the model works
#: in, not as a measured constant: it is a repo-defined modeling assumption, not
#: a measurement, and the catalog entry is where a deployment states its own.
TYPICAL_RSSI_BAND_DBM = (-70, -40)


class PortalFault(StrEnum):
    """The two portal faults, kept apart on purpose.

    UNREACHABLE is the loud one: the reader does not answer. SILENT is the
    quiet one: the reader answers and reads nothing, which every liveness check
    reports as healthy.
    """

    UNREACHABLE = "unreachable"
    SILENT = "silent"


@dataclass(frozen=True, slots=True)
class TagRead:
    """One read record out of an inventory round.

    `read_count` is what makes this a record of an inventory rather than of an
    event: the reader reports how many times it saw this tag on this antenna in
    this window, and collapsing that to one loses the weight the aggregation
    below needs.
    """

    epc: str
    sim_ts: SimInstant
    antenna_port: int
    rssi_dbm: int
    phase_deg: float
    read_count: int = 1

    def __post_init__(self) -> None:
        if not isinstance(self.epc, str) or not EPC.match(self.epc):
            raise ValueError(
                f"epc {self.epc!r} is not a 96-bit Gen2 identifier: {EPC_LENGTH} "
                "uppercase hexadecimal characters"
            )
        if self.antenna_port < 1:
            raise ValueError(
                f"antenna_port {self.antenna_port} is out of range; ports are 1-based, "
                "the way a reader labels them on its own housing"
            )
        if self.rssi_dbm >= 0:
            raise ValueError(
                f"rssi_dbm {self.rssi_dbm} is not a received level; backscatter RSSI "
                "is a negative dBm integer"
            )
        if not 0.0 <= self.phase_deg < 360.0:
            raise ValueError(
                f"phase {self.phase_deg} is outside one turn; RF phase is reported in "
                "degrees over [0, 360)"
            )
        if self.read_count < 1:
            raise ValueError(
                f"read_count {self.read_count} stands for no read at all; a read "
                "record represents at least one"
            )


class EpcPrefixFilter:
    """The prefix that decides which tags belong to this read zone.

    An empty prefix is REFUSED. It matches every EPC, so accepting one turns
    filtering off while leaving a filter object in place, and the run that
    results looks exactly like a run with a correctly configured filter and a
    surprisingly busy dock. Refusing at construction is the only point where
    the mistake is still visible.
    """

    __slots__ = ("_prefix",)

    def __init__(self, prefix: str) -> None:
        candidate = prefix.strip() if isinstance(prefix, str) else prefix
        if not candidate:
            raise ValueError(
                "an empty EPC prefix filter is refused: it matches every tag, so it "
                "silently disables the filtering this read zone depends on. Name the "
                "prefix this zone's inventory actually carries."
            )
        if len(candidate) > EPC_LENGTH:
            raise ValueError(
                f"prefix {candidate!r} is longer than the {EPC_LENGTH} characters of an "
                "EPC, so it can never match"
            )
        if not HEX_PREFIX.match(candidate):
            raise ValueError(
                f"prefix {candidate!r} is not uppercase hex, so it is not a prefix of any legal EPC"
            )
        self._prefix = candidate

    @property
    def prefix(self) -> str:
        return self._prefix

    def matches(self, epc: str) -> bool:
        return epc.startswith(self._prefix)


@dataclass(frozen=True, slots=True)
class ReadAggregate:
    """What one EPC looked like on one antenna over one window."""

    epc: str
    antenna_port: int
    read_count: int
    rssi_min_dbm: int
    rssi_max_dbm: int
    rssi_mean_dbm: float
    first_seen_ts: SimInstant
    last_seen_ts: SimInstant


class InventoryAccumulator:
    """Bounded accumulation of an inventory, keyed by (EPC, antenna).

    Keyed by the pair rather than by the EPC alone because which antenna saw a
    tag is the whole diagnostic: a tag strong on port 1 and absent on port 3 is
    a coverage answer, and collapsing the antennas throws that away.

    The cap counts DISTINCT EPCs rather than distinct keys. One tag seen on
    four antennas is one tag, and a cap spent per key would evict real
    inventory as soon as a portal used all its ports.
    """

    __slots__ = (
        "_aggregates",
        "_dropped_epcs",
        "_epc_filter",
        "_epcs",
        "_max_epcs",
        "dropped_reads",
        "filtered_reads",
    )

    def __init__(self, *, max_epcs: int, epc_filter: EpcPrefixFilter | None = None) -> None:
        if max_epcs < 1:
            raise ValueError(
                f"max_epcs {max_epcs} tracks nothing; a cap of zero drops every read "
                "while still looking like a configured accumulator"
            )
        self._max_epcs = max_epcs
        self._epc_filter = epc_filter
        # Dicts, not sets. D-03 bans an iteration order that can reach an
        # emitted value, and aggregates() reaches the published payload.
        self._aggregates: dict[tuple[str, int], ReadAggregate] = {}
        self._epcs: dict[str, None] = {}
        self._dropped_epcs: dict[str, None] = {}
        self.dropped_reads = 0
        self.filtered_reads = 0

    @property
    def dropped_new_epcs(self) -> int:
        """How many DISTINCT tags the cap refused.

        Distinct, not per read record, because the two answer different
        questions and an operator needs both. This one sizes the loss: it is
        how many tags went unrecorded, and it is the number that belongs beside
        a pallet's expected tag count. `dropped_reads` counts the read records
        discarded, which is larger whenever a refused tag was seen more than
        once, and is the number that says how hard the reader was working while
        the cap was full.
        """
        return len(self._dropped_epcs)

    @property
    def max_epcs(self) -> int:
        return self._max_epcs

    @property
    def tracked_epcs(self) -> int:
        return len(self._epcs)

    def offer(self, read: TagRead) -> bool:
        """Take one read record. Returns whether it was accumulated.

        Three outcomes, and they are counted separately because they mean
        different things to an operator: filtered (not our inventory), dropped
        (our inventory, but the cap was full), and accumulated.
        """
        if self._epc_filter is not None and not self._epc_filter.matches(read.epc):
            self.filtered_reads += 1
            return False

        key = (read.epc, read.antenna_port)
        existing = self._aggregates.get(key)
        if existing is None and read.epc not in self._epcs:
            if len(self._epcs) >= self._max_epcs:
                # At the cap only a NEW EPC is refused. An already-tracked tag
                # keeps updating, because dropping it would corrupt the counts
                # already published for it rather than merely omit a tag.
                self._dropped_epcs[read.epc] = None
                self.dropped_reads += 1
                return False
            self._epcs[read.epc] = None

        self._aggregates[key] = _accumulate(existing, read)
        return True

    def aggregates(self) -> tuple[ReadAggregate, ...]:
        """Every aggregate, in a deterministic order.

        Sorted rather than in insertion order: the order two portals see the
        same tags in depends on the RF draw, and an emitted order that depends
        on it would make two runs at one seed differ in their payloads without
        differing in their content.
        """
        return tuple(
            self._aggregates[key]
            for key in sorted(self._aggregates, key=lambda key: (key[0].encode(), key[1]))
        )

    def total_reads(self) -> int:
        return sum(aggregate.read_count for aggregate in self._aggregates.values())

    def mean_rssi_dbm(self) -> float | None:
        """The read-count-weighted mean across every aggregate, or None.

        None rather than 0.0 when nothing was read. Zero dBm is a physically
        impossible received level and would sit at the top of every chart.
        """
        total = self.total_reads()
        if total == 0:
            return None
        weighted = sum(
            aggregate.rssi_mean_dbm * aggregate.read_count
            for aggregate in self._aggregates.values()
        )
        return weighted / total


def _accumulate(existing: ReadAggregate | None, read: TagRead) -> ReadAggregate:
    """Fold one read record into the running aggregate.

    The mean is weighted by `read_count`. Weighting an incoming sample by one
    treats a batch of three hundred reads as a single observation, which drags
    the mean toward whichever antenna reported least often. That is a real bug
    someone shipped, and it survives review because the arithmetic looks like
    a textbook running mean.
    """
    if existing is None:
        return ReadAggregate(
            epc=read.epc,
            antenna_port=read.antenna_port,
            read_count=read.read_count,
            rssi_min_dbm=read.rssi_dbm,
            rssi_max_dbm=read.rssi_dbm,
            rssi_mean_dbm=float(read.rssi_dbm),
            first_seen_ts=read.sim_ts,
            last_seen_ts=read.sim_ts,
        )
    total = existing.read_count + read.read_count
    mean = (
        existing.rssi_mean_dbm * existing.read_count + float(read.rssi_dbm) * read.read_count
    ) / total
    return ReadAggregate(
        epc=existing.epc,
        antenna_port=existing.antenna_port,
        read_count=total,
        rssi_min_dbm=min(existing.rssi_min_dbm, read.rssi_dbm),
        rssi_max_dbm=max(existing.rssi_max_dbm, read.rssi_dbm),
        rssi_mean_dbm=mean,
        first_seen_ts=min(existing.first_seen_ts, read.sim_ts),
        last_seen_ts=max(existing.last_seen_ts, read.sim_ts),
    )


def diagnose_portal(
    *, reachable: bool, ticks_since_last_read: int, silence_threshold_ticks: int
) -> PortalFault | None:
    """Decide which of the two portal faults is present, if either.

    Unreachable wins when both could be said, and that ordering is deliberate:
    a reader nobody can talk to has of course read nothing, and reporting the
    silence as well would send an operator looking at antennas when the fault
    is a network drop.
    """
    if not reachable:
        return PortalFault.UNREACHABLE
    if ticks_since_last_read > silence_threshold_ticks:
        return PortalFault.SILENT
    return None


@dataclass(frozen=True, slots=True)
class ReaderConfig:
    """The reader's own settings, all of them calibration rather than physics.

    `silence_threshold_ticks` has no defensible default, so there is none. How
    long a portal may legitimately read nothing is a property of the dock it
    is over: a receiving door that sees four trailers a shift is silent for
    hours without any fault at all, and a sortation induct that is silent for
    thirty seconds has already stopped the line. A constant here would be a
    number pretending to be a fact.
    """

    sensitivity_dbm: int
    silence_threshold_ticks: int
    max_epcs: int = 4096
    epc_prefix: str | None = None

    def __post_init__(self) -> None:
        if self.sensitivity_dbm >= 0:
            raise ValueError(
                f"sensitivity_dbm {self.sensitivity_dbm} is not a received level; a "
                "reader's sensitivity floor is a negative dBm integer"
            )
        if self.silence_threshold_ticks < 1:
            raise ValueError(
                f"silence_threshold_ticks {self.silence_threshold_ticks} would report "
                "every quiet moment as a fault; it is a calibration knob and needs a "
                "value the read zone justifies"
            )

    def epc_filter(self) -> EpcPrefixFilter | None:
        """Build the filter, or none at all if this zone declared no prefix.

        None and an empty string are different answers. None says this zone
        takes every tag it sees on purpose; an empty string says someone meant
        to filter and wrote nothing, which EpcPrefixFilter refuses.
        """
        if self.epc_prefix is None:
            return None
        return EpcPrefixFilter(self.epc_prefix)


@dataclass(frozen=True, slots=True)
class PortalTelemetry:
    """What the portal publishes for one window.

    Every optional field is optional because it can genuinely be unknown, and
    an unknown one is omitted from metric_values() rather than defaulted. A
    read rate of 0.0 means every expected tag was missed; a read rate of None
    means nothing passed, so the ratio has no denominator. A p-chart cannot
    tell those apart once the second has been written as the first.
    """

    device_ts: SimInstant
    unique_epcs: int
    reads_total: int
    dropped_new_epcs: int
    read_rate: float | None = None
    tags_expected: int | None = None
    rssi_mean_dbm: float | None = None
    fault: PortalFault | None = None

    def metric_values(self) -> dict[str, Any]:
        """The parameter-to-value mapping this window publishes.

        Sorted, and absent values omitted.
        """
        values: dict[str, Any] = {
            "unique_epcs": self.unique_epcs,
            "reads_total": self.reads_total,
            "dropped_new_epcs": self.dropped_new_epcs,
        }
        if self.read_rate is not None:
            values["read_rate"] = self.read_rate
        if self.tags_expected is not None:
            values["tags_expected"] = self.tags_expected
        if self.rssi_mean_dbm is not None:
            values["rssi_mean_dbm"] = self.rssi_mean_dbm
        return dict(sorted(values.items()))


class PortalReader:
    """One portal reader instance: its inventory, its faults, its telemetry.

    The clock and the RNG are handed in per call rather than held, so this
    object has no way to reach a wall clock or an unseeded generator. Two runs
    at one seed produce byte-identical output because every source of variation
    arrives through a parameter.
    """

    #: `beta_scaled(lo, hi, mean, conc)` for the true per-portal read rate, from
    #: the `variability.autoid.portal_read_rate` row of
    #: docs/design/variability-and-faults.md. A read rate is a bounded ratio, so
    #: its family is a scaled beta whose support IS [0, 1]. A clamped normal
    #: would pile probability mass exactly on 1.0, and a portal that reads every
    #: tag on a measurable fraction of windows is an artifact of the sampler
    #: rather than a property of the dock.
    READ_RATE_BETA = (0.0, 1.0, 0.986, 400.0)

    def __init__(
        self,
        *,
        config: ReaderConfig,
        uns_prefix: Sequence[str] | None = None,
    ) -> None:
        self._config = config
        self._uns_prefix = tuple(uns_prefix) if uns_prefix is not None else None
        self.inventory = InventoryAccumulator(
            max_epcs=config.max_epcs, epc_filter=config.epc_filter()
        )
        self._last_read_ts: SimInstant | None = None

    @property
    def config(self) -> ReaderConfig:
        return self._config

    @property
    def last_read_ts(self) -> SimInstant | None:
        return self._last_read_ts

    def observe(self, read: TagRead, *, now: SimInstant | None = None) -> bool:
        """Take one read record off the air.

        A read weaker than the configured sensitivity is refused rather than
        accumulated, because it does not happen: the sensitivity is the floor
        below which the reader cannot demodulate a backscatter response at all.
        A model that accepts one is quietly modeling a different reader.
        """
        if read.rssi_dbm < self._config.sensitivity_dbm:
            raise ValueError(
                f"a read at {read.rssi_dbm} dBm is below this reader's sensitivity of "
                f"{self._config.sensitivity_dbm} dBm, so it does not happen; the RF "
                "layer decides what is readable, and this is not"
            )
        accumulated = self.inventory.offer(read)
        if accumulated:
            stamp = now if now is not None else read.sim_ts
            self._last_read_ts = stamp
        return accumulated

    def fault(self, *, now: SimInstant, reachable: bool) -> PortalFault | None:
        """Which fault, if any, this reader is showing at this instant."""
        since = int(now) - int(self._last_read_ts if self._last_read_ts is not None else now)
        return diagnose_portal(
            reachable=reachable,
            ticks_since_last_read=since,
            silence_threshold_ticks=self._config.silence_threshold_ticks,
        )

    def telemetry(
        self,
        *,
        now: SimInstant,
        read_rate: float | None = None,
        tags_expected: int | None = None,
        reachable: bool = True,
    ) -> PortalTelemetry:
        """Close the window and describe it."""
        return PortalTelemetry(
            device_ts=now,
            unique_epcs=self.inventory.tracked_epcs,
            reads_total=self.inventory.total_reads(),
            dropped_new_epcs=self.inventory.dropped_new_epcs,
            read_rate=read_rate,
            tags_expected=tags_expected,
            rssi_mean_dbm=self.inventory.mean_rssi_dbm(),
            fault=self.fault(now=now, reachable=reachable),
        )

    def publish(
        self,
        *,
        now: SimInstant,
        read_rate: float | None = None,
        tags_expected: int | None = None,
        reachable: bool = True,
    ) -> tuple[tuple[UnsPath, Any], ...]:
        """Render this window as (topic, value) pairs on the six-level namespace.

        The paths are built from the prefix this reader was configured with, so
        no topic string is typed anywhere in this module. ARCHITECTURE section
        5 makes that a rule rather than a habit: the namespace is a projection
        of the modeled facility, and a hand-typed topic is a second truth.
        """
        if self._uns_prefix is None:
            raise RuntimeError(
                "this reader was built with no UNS prefix, so it has no address to "
                "publish on; hand it the five identifier levels of its equipment"
            )
        telemetry = self.telemetry(
            now=now, read_rate=read_rate, tags_expected=tags_expected, reachable=reachable
        )
        return tuple(
            (UnsPath.from_prefix(self._uns_prefix, parameter), value)
            for parameter, value in telemetry.metric_values().items()
        )

    def metric_specs(self) -> Iterator[str]:
        """Every parameter this reader may ever publish, in sorted order.

        The DBIRTH needs the complete list, because a metric absent from a
        birth certificate may never appear in a data message. This is the one
        place that list is written, so the birth and the publish cannot drift.
        """
        yield from (
            "dropped_new_epcs",
            "read_rate",
            "reads_total",
            "rssi_mean_dbm",
            "tags_expected",
            "unique_epcs",
        )

    @classmethod
    def draw_read_rate(cls, rng: Any, params: Mapping[str, float] | None = None) -> float:
        """Draw the true read rate for one window from a scaled beta.

        The generator is injected. twinflow.rng.generator_for is the only place
        in the workspace that constructs a bit generator, and a device model is
        exactly where an unseeded draw would otherwise appear.
        """
        low, high, mean, concentration = cls.READ_RATE_BETA
        if params is not None:
            low = params.get("lo", low)
            high = params.get("hi", high)
            mean = params.get("mean", mean)
            concentration = params.get("conc", concentration)
        return beta_scaled(rng, low=low, high=high, mean=mean, concentration=concentration)


def beta_scaled(rng: Any, *, low: float, high: float, mean: float, concentration: float) -> float:
    """`beta_scaled(lo, hi, mean, conc)` from variability-and-faults section A.

    A bounded ratio gets a distribution whose support already IS its physical
    range, so no draw ever needs clamping. Rule R2 of that section is explicit
    that clamping a normal is the wrong answer: it converts the tail into a
    spike of probability sitting exactly on the boundary, and every capability
    statistic computed over it is then measuring the sampler.
    """
    if not low < high:
        raise ValueError(f"beta_scaled needs lo < hi, got lo={low} hi={high}")
    if not low < mean < high:
        raise ValueError(f"beta_scaled mean {mean} is outside its own support [{low}, {high}]")
    if concentration <= 0:
        raise ValueError(f"beta_scaled concentration {concentration} must be positive")
    position = (mean - low) / (high - low)
    alpha = concentration * position
    beta = concentration * (1.0 - position)
    return low + float(rng.beta(alpha, beta)) * (high - low)
