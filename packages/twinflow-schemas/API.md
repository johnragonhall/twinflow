---
title: twinflow-schemas API
description: Every public symbol twinflow-schemas owns, which boundary rule A1.4 requires each package to list.
topic_type: reference
audience: contributors
---

# twinflow-schemas API

Boundary rule A1.4 gives every public symbol exactly one owning package. These
are the names this package owns. Gate `IMPORT-3` fails when `__all__` and this
package's declared ownership disagree.

| Symbol                      | Kind     | What it is                                                              |
|-----------------------------|----------|-------------------------------------------------------------------------|
| `Envelope`                  | class    | The CloudEvents 1.0.2 envelope every event carries                      |
| `Envelope.total_order_key`  | method   | The canonical replay order: sim time, producer as bytes, sequence       |
| `PRODUCER_IDS`              | constant | The closed set of process roles that may publish an event               |
| `ProducerId`                | type     | The same closed set as a type, which the published schema reads as enum |
| `SourceUri`                 | type     | A source constrained to `/twinflow/<package>/<component>`               |
| `MAX_ATTRIBUTE_NAME_LENGTH` | constant | 20, the attribute-name ceiling this project adopts from CloudEvents     |
| `DecimalString`             | type     | A bounded string used for the two counters that overflow a 32-bit int   |
| `compare_schemas`           | function | The section 5.5 compatibility rules: what may change within a major     |
| `check_log_invariants`      | function | ENV-001 over a whole log: dense sequence, no duplicate, no tie          |
| `LogViolation`              | class    | One way a log breaks ENV-001, naming which of the three                 |
| `in_total_order`            | function | A log in canonical replay order                                         |
| `log_hash`                  | function | What tier one of D-05 means by two runs being identical                 |
| `compare_runs`              | function | Where two runs first diverge, rather than only that they do             |
| `OPEN_ENUM`                 | constant | The keyword a field sets to let new enum members in                     |
| `OPEN_RANGE`                | constant | The keyword a field sets to let its range widen                         |
| `__version__`               | constant | The distribution version, read by the build so the two cannot disagree  |

`compare_schemas` lives here rather than in a script because the rules are part
of the contract. A consumer deciding whether it can read a newer version asks
the same question CI asks, and both read the answer from one place.

## Re-exports

None. This package is the leaf and borrows no name from another package.
