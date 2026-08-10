---
title: twinflow-schemas
description: The event envelope and shared value types, the one workspace leaf every other twinflow package imports.
topic_type: reference
audience: contributors
---

# twinflow-schemas

The event envelope every twinflow event carries, and the value types shared
across packages. This is the workspace leaf: it imports nothing else from
twinflow, which is what lets you install one brick without the rest.

## Install

```bash
pip install twinflow-schemas
```

## Use

```python
from twinflow.schemas import Envelope

event = Envelope(
    specversion="1.0",
    id="01J0000000000000000000000A",
    source="/twinflow/sim/receiving",
    type="twinflow.twin.pallet_scanned",
    time="2026-08-09T00:00:00Z",
    datacontenttype="application/json",
    dataschema="twinflow:schemas/twin/pallet_scanned/v1.0.json",
    twinflowsimts="0",
    twinflowrunid="run_01J0000000000000000000000A",
    twinflowproducerid="sim",
    twinflowseq="0",
    data={},
)

ordered = sorted(events, key=Envelope.total_order_key)
```

## What to know before you use it

The envelope is CloudEvents 1.0.2, so attribute names are lower-case ASCII with
no separators: `twinflowsimts`, never `twinflow_sim_ts`.

`twinflowsimts` and `twinflowseq` are decimal strings rather than integers.
CloudEvents fixes its `Integer` type at 32 bits signed and requires event
formats to stay inside that range, and both counters leave it in normal use:
one simulated day at the default tick rate is 8.64e10 ticks.

The sequence starts at 0, and it is dense per producer rather than globally.
`Envelope.total_order_key` gives the canonical replay order.

An `Envelope` is immutable and deliberately **not** hashable, because `data` is
a dict. Deduplicate on the event id rather than by putting envelopes in a set.

The public symbols are listed in [API.md](API.md).
