---
title: twinflow custom schema keywords
description: The x-twinflow annotation keywords used across the schema registry and what each one obliges a consumer to do.
topic_type: reference
audience: contributors
---

# twinflow custom schema keywords

JSON Schema 2020-12 ignores keywords it does not know, so these annotate rather
than validate. They exist because two of the compatibility rules in
`docs/design/foundations.md` section 5.5 cannot be decided from a schema alone.

| Keyword                    | Meaning                                                                                  |
| -------------------------- | ---------------------------------------------------------------------------------------- |
| `x-twinflow-precision`     | Decimal places a float is quantised to before serialisation                              |
| `x-twinflow-unit`          | The SI unit the number is expressed in, validated against pint                           |
| `x-twinflow-open-enum`     | Consumers must tolerate unknown members. Only such enums may gain members within a major |
| `x-twinflow-open-range`    | Consumers must tolerate values outside the declared range. Only such fields may widen    |
| `x-twinflow-pii`           | Always false in this repository, asserted by a test, because the data is synthetic       |
| `x-twinflow-partition-key` | The field the historian partitions on                                                    |
| `x-twinflow-since`         | The release that added this field                                                        |
| `x-twinflow-not-in-hash`   | A config key excluded from `ConfigHash` because it cannot change the tape                |
| `x-twinflow-stored-bytes`  | Measured stored bytes per row for a subject, with the run id it was measured on          |

## Why the two "open" keywords exist

A widened range breaks a consumer in the same way a narrowed one does. A
consumer that read `divert_rate` as a value in `[0, 1]` and sized a fixed-point
field to match breaks when the producer starts publishing `1.4`, and it breaks
silently.

So widening is rejected by default. A producer that intends a field to grow
declares `x-twinflow-open-range: true` on it, which tells every consumer to
handle values outside the printed range. `x-twinflow-open-enum` says the same
thing for enum members.

The point of both is that the obligation is written down at the field a
consumer reads, rather than assumed by whoever changes the schema next.

## Checking

`tools/schema_diff.py OLD.json NEW.json` implements the section 5.5 table and
reads these keywords. Gate `SCH-001` runs it for every subject whose schema
changed.
