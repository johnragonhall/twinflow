---
title: twinflow-storage API
description: Every public symbol twinflow-storage owns, which boundary rule A1.4 requires each package to list.
topic_type: reference
audience: contributors
---

# twinflow-storage API

Boundary rule A1.4 gives every public symbol exactly one owning package. These
are the names this package owns.

## Naming

| Symbol           | Kind     | What it is                                                          |
| ---------------- | -------- | ------------------------------------------------------------------- |
| `SeriesName`     | class    | One time series, carrying the layer the historian answers for it at |
| `series_for`     | function | The historian's name for one topic                                  |
| `LayerPlacement` | class    | One row of the ISA-95 and Purdue layer map                          |
| `HISTORIAN`      | constant | Requirement RA-c as a value: L2, L3, published into L3.5            |
| `PURDUE_LEVELS`  | constant | The levels a `LayerPlacement` can name                              |

`series_for` takes a `UnsPath` from `twinflow.config` and returns the one name
this historian stores it under. `LayerPlacement` refuses a level outside
`PURDUE_LEVELS` with code `TF-S006`, raised as the `NamingError` that package
owns.

## The historian

| Symbol               | Kind     | What it is                                                |
| -------------------- | -------- | --------------------------------------------------------- |
| `Historian`          | class    | One run's append-only log, over an injected clock         |
| `HistorianError`     | class    | A refused event or snapshot, carrying its `TF-S0xx` code  |
| `ConfigSnapshot`     | class    | The hashed core of doctrine D-01, carried inside the log  |
| `SnapshotProvenance` | class    | The sidecar of doctrine D-01, written beside the log      |
| `provenance_leaks`   | function | The D-01 carve-out as a check: which fields must stay out |
| `PROVENANCE_MARKERS` | constant | The field-name fragments that check reads                 |

## The batch path

| Symbol                     | Kind     | What it is                                                 |
| -------------------------- | -------- | ---------------------------------------------------------- |
| `EVENT_TABLE`              | constant | The event log's Delta table: columns, partition, order     |
| `TableFormat`              | class    | A batch table declared as data, never as a writer call     |
| `Column`                   | class    | One column, its Arrow type, and where its value comes from |
| `rows_for`                 | function | The rows for a log, in the canonical total order           |
| `STORED_BYTES_METRIC`      | constant | The name of the metric marker this brick owes              |
| `STORED_BYTES_PER_READING` | constant | `None` until measured, never an estimate                   |
| `STORED_BYTES_MEASURED_ON` | constant | The run the number above was measured on                   |

## Packaging

| Symbol        | Kind     | What it is                                                             |
| ------------- | -------- | ---------------------------------------------------------------------- |
| `__version__` | constant | The distribution version, read by the build so the two cannot disagree |

## Behavior worth knowing

`Historian.events` returns the append order and `Historian.replay` returns the
total order of invariant E4. Both are needed. The first is what happened at one
process, the second is what happened.

`Historian.violations` calls `check_log_invariants` from `twinflow-schemas`,
which is the function gate VAL-GATE-ENV-001 runs. A second reading of the rule
written here would be a second rule that can disagree with the first.

`UnsPath.subscription` in `twinflow.config` is the one place a wildcard is
produced. A caller who wants every parameter in an area asks for it there. A
caller building a published topic cannot get a wildcard by accident.

`Historian` is synchronous. The kernel's async `EventLog` port arrives with the
runtime builder, and the adapter that satisfies it wraps this core.

## Re-exports

None.

## Names this package does not export

The UNS grammar. `UnsPath`, `NamingError`, `TOPIC_LEVELS`, `TOPIC_SEPARATOR`,
`WILDCARDS`, `LEVEL_NAMES`, `IDENTIFIER`, and `PARAMETER` are owned by
`twinflow.config`, which owns the facility model the namespace projects.

Neither this package nor `twinflow.sensors` carries its own copy of those
rules. Two definitions of one six-level contract disagree on the first day
either is tightened, and the import-boundary gate cannot see a duplicate whose
names differ. One definition sits below both, which is what boundary rule A1.4
and layer rule A1.3 exist to produce.

They are not declared as re-exports either. A re-export puts the same public
name on two surfaces, and a consumer building a topic must reach the one
definition directly:

```python
from twinflow.config import UnsPath
from twinflow.storage import series_for
```

`UnsPath.parse(text)` is the one spelling of that operation, and it lives with
the grammar it applies.
