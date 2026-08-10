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
| --------------------------- | -------- | ----------------------------------------------------------------------- |
| `Envelope`                  | class    | The CloudEvents 1.0.2 envelope every event carries                      |
| `Envelope.total_order_key`  | method   | The canonical replay order: sim time, producer as bytes, sequence       |
| `PRODUCER_IDS`              | constant | The closed set of process roles that may emit an event                  |
| `MAX_ATTRIBUTE_NAME_LENGTH` | constant | 20, the attribute-name ceiling this project adopts from CloudEvents     |
| `DecimalString`             | type     | A bounded string used for the two counters that overflow a 32-bit int   |
| `__version__`               | constant | The distribution version, read by the build so the two cannot disagree  |

## Re-exports

None. This package is the leaf and borrows no name from another package.
