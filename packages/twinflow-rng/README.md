---
title: twinflow-rng
description: The one place a bit generator is constructed, and the append-only registry of stream names.
topic_type: concept
audience: contributors
---

# twinflow-rng

Deterministic randomness addressed by name. Every stream is a dotted name
hashed into a seed, so a stream's identity comes from what it is called rather
than from when it was created.

## Install

```bash
pip install twinflow-rng
```

## Use

```python
from twinflow.rng import StreamRegistry

registry = StreamRegistry(base_seed=42)
registry.register("twin.receiving.unload_duration")
registry.register("twin.amr.{amr_id}.task_travel")

rng = registry.get("twin.receiving.unload_duration")
per_robot = registry.get("twin.amr.{amr_id}.task_travel", amr_id="AMR-014")
```

## Why name-addressed

`SeedSequence.spawn(n)` extends the parent key by the child's index, so the
seed a subsystem receives depends on how many subsystems were created before
it. Adding subsystem forty would shift subsystem one, and every recorded run
and golden file would break.

Hashing the name instead means **adding a stream perturbs no existing stream**.
That property is asserted as a Hypothesis property rather than trusted, and it
was watched failing against a positional derivation.

## The cross-language contract

The derivation is fixed byte for byte, because the Rust device agent derives
its streams the same way:

- BLAKE2b over the UTF-8 name, 16-byte digest, personalisation `twinflow-rng`
- the digest read as four little-endian uint32 words, used as the spawn key
- run entropy as exactly four uint32 words
- `PCG64DXSM` as the bit generator

`tests/fixtures/rng_kat.json` at the repository root holds 384 known-answer
cases that both implementations must reproduce. Regenerating it to make a test
pass destroys the only evidence the two agree.

The public symbols are listed in [API.md](API.md).
