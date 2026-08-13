---
title: twinflow-config
description: Loads a facility profile, validates it, reports every problem with a line number and a suggestion, and owns the unified namespace grammar the model projects onto.
topic_type: concept
audience: contributors
---

# twinflow-config

Loads a facility profile, validates it, and reports what is wrong in a form the
author can act on. It also owns the unified namespace grammar, because
ARCHITECTURE.md section 5 makes the namespace a projection of the facility
model this package already holds.

## Install

```bash
pip install twinflow-config
```

## Use

```python
from twinflow.config import ConfigError, load_facility

try:
    profile, warnings = load_facility("profiles/starter_dc.yaml")
except ConfigError as exc:
    print(exc.rendered)
```

## What a diagnostic looks like

```text
error[TF-C012]: unknown key 'capacitty'
  --> profiles/starter_dc.yaml:16:7
    |
 16 |       capacitty: 4
    |       ^ did you mean 'capacity'?
    |
   = valid keys here: capacity, id, type, zone
```

Three things are always there: the code, the line and column in the file that
was edited, and something to do about it. A validator that answers "invalid"
has told the author nothing they did not already know, so gate `CFG-001`
asserts all three on every invalid fixture.

Every stage reports all of its findings before the next stage runs. An author
who fixes one error, reruns, and finds the next one gives up long before an
author who is handed the list.

## Suggestions decline to guess

`nearest` returns nothing when no candidate is close. A confident wrong
suggestion sends the author further from the fix than no suggestion does.

## The namespace is part of the model

ARCHITECTURE.md section 5 says the unified namespace is "a projection of the
facility model, not a parallel truth". So the six-level grammar lives here, with
the model, and both renderers import it:

```python
from twinflow.config import UnsPath

topic = UnsPath(
    enterprise="twinflow",
    site="dc-01",
    area="receiving",
    line="inbound-line-01",
    equipment="conveyor-02",
    parameter="motor_temp_c",
)
topic.topic            # twinflow/dc-01/receiving/inbound-line-01/conveyor-02/motor_temp_c
topic.subscription(3)  # twinflow/dc-01/receiving/#
```

Levels are validated at construction, so nothing downstream has to remember to
check: `twinflow.sensors` renders the same object as a Sparkplug address and a
JSON mirror topic, and `twinflow.storage` mints the historian series key from
it. Neither package carries its own copy of the rules, because one contract
with two definitions is a disagreement waiting for the first tightening.

`UnsPath.subscription` is the only place a wildcard is produced. A published
topic cannot get one by accident.

## Warnings are not errors

A station with zero capacity is legal and almost certainly a mistake, so it
loads with a `TF-C3xx` warning. Pass `strict=True` to make any finding fail.

The public symbols are listed in [API.md](API.md).
