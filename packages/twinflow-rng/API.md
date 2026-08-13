---
title: twinflow-rng API
description: Every public symbol twinflow-rng owns, which boundary rule A1.4 requires each package to list.
topic_type: reference
audience: contributors
---

# twinflow-rng API

Boundary rule A1.4 gives every public symbol exactly one owning package. These
are the names this package owns.

| Symbol                   | Kind     | What it is                                                             |
|--------------------------|----------|------------------------------------------------------------------------|
| `StreamRegistry`         | class    | The append-only registry of declared stream names for one run          |
| `generator_for`          | function | Build the generator for one stream name, seed, and replication index   |
| `derive_spawn_key`       | function | Hash a stream name into the four uint32 words of the spawn key         |
| `STREAM_COUNT_CEILING`   | constant | 750000, the declared operating ceiling on catalog size                 |
| `STREAM_CATALOG_VERSION` | constant | Bumped when the catalog gains, loses, or renames a stream              |
| `__version__`            | constant | The distribution version, read by the build so the two cannot disagree |

## Registry behavior worth knowing

`get` refuses an unregistered name, so the catalog stays a complete record of a
run's randomness. It refuses a retired name rather than deleting it, because a
freed address could later point an old log at new numbers.

A templated name validates its entity id before substitution. A device name is
attacker-controlled in any real fleet, and an id carrying a dot would insert a
segment and address a different stream.

`handout_counts()` counts generators handed out, not values drawn. The draw
counter that the run manifest hashes counts calls through
`twinflow.kernel.numeric` and lands with that module.

## Re-exports

None.
