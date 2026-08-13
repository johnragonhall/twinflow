---
title: twinflow-storage
description: The append-only historian, the per-run config snapshot it records beside a log, and the naming that makes it the system of record.
topic_type: concept
audience: contributors
---

# twinflow-storage

The plant historian. It holds one run's events in the order they happened, it
records the config that produced them, and it refuses a name or an event that
would make the run unreplayable later.

## Install

```bash
pip install twinflow-storage
```

The base install pulls `twinflow-kernel`, `twinflow-schemas`, and
`twinflow-config` and nothing else. Every database driver sits behind an extra,
so a reader who wants the historian contract does not download a Rust wheel to
read it. `twinflow-config` is there for the UNS grammar: a series has exactly
one name, that name is the six-level topic, and the rules for it live in the
package that owns the facility model rather than in a copy here.

## Use

```python
from twinflow.config import UnsPath
from twinflow.kernel import SimClock
from twinflow.storage import ConfigSnapshot, Historian, series_for

topic = UnsPath(
    enterprise="twinflow",
    site="dc-01",
    area="receiving",
    line="inbound-line-01",
    equipment="conveyor-02",
    parameter="motor_temp_c",
)
series = series_for(topic)          # one series, one name, one owning layer
subscription = topic.subscription(3)  # twinflow/dc-01/receiving/#

historian = Historian(clock=SimClock(), snapshot=ConfigSnapshot(...))
historian.append(envelope)
sidecar = historian.seal(...)       # the wall clock lands here, never in the log
```

## Why the historian is the L2 system of record

ARCHITECTURE.md section 4 places the historian at ISA-95 L2, running at Purdue
L3 and published into the DMZ at L3.5. That row is requirement RA-c, and a row
in a table drifts from the code with nothing failing at the moment it drifts.
So the row is the value `HISTORIAN`, and a test reads the table back and
compares the two.

Being the system of record has one mechanical consequence. A series has exactly
one name. That name is the six-level UNS topic of section 5, generated from
config. A second spelling gives two answers to what happened at one conveyor,
and something that gives two answers is a cache.

That is also why the grammar itself is imported rather than restated. Two sets
of patterns for the six levels are two answers to what a legal name is.
`UnsPath` in `twinflow.config` is the only one.

## What the log refuses

An append is checked at the seam rather than at the end of the run, because
every one of these defects is unrepairable once the producers have gone away.

| Code    | Refused                                           | Why it cannot wait                                    |
| ------- | ------------------------------------------------- | ----------------------------------------------------- |
| TF-S010 | An event from another run                         | Two runs in one log have no single total order        |
| TF-S011 | A gap in one producer's sequence                  | A gap cannot be filled after the run ends             |
| TF-S012 | An event id already recorded                      | A replay would count it twice                         |
| TF-S014 | An event stamped after the clock                  | A reading from the future has no position in a replay |
| TF-S015 | An append after the sidecar recorded the log hash | It would invalidate the hash already written          |

A reading buffered across a site-link outage is not one of these. It arrives
late and keeps its original sim-time timestamp, which is what `backfilled`
reports.

## The snapshot split

Doctrine D-01 split the run manifest. Wall-clock time and machine identity in
the first event made a byte-identical log impossible by construction. The
hashed core is `ConfigSnapshot` and carries neither. The sidecar is
`SnapshotProvenance` and carries both. That carve-out is a runtime check named
`provenance_leaks`. It refuses a snapshot that grows a field it must not have.

## The batch path

Decision D2 makes Delta the table format and DuckDB the query engine. Treating
one as both is the mistake that decision exists to avoid. The table, its
partition column, its sort order, and its codec are declared by `EVENT_TABLE`,
and `rows_for` produces the rows in the canonical total order.

`deltalake` and `duckdb` themselves are deferred to the `delta` extra of
foundations section 2.7. The format is data here rather than a library call, so
the contract is readable and testable without spending the five-minute
quickstart budget on wheels that a reader of the contract never calls.

## The number this brick owes

Stored bytes per sensor reading is not measured yet, so
`STORED_BYTES_PER_READING` is `None` rather than a plausible integer, and
`STORED_BYTES_MEASURED_ON` names no run. A test asserts that the constant and
the metric marker in the design documents agree about whether the number
exists, so neither can be filled alone.

The public symbols are listed in [API.md](API.md).
