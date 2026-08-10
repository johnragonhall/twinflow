---
title: twinflow-config
description: Loads a facility profile, validates it, and reports every problem with a line number and a suggestion.
topic_type: concept
audience: contributors
---

# twinflow-config

Loads a facility profile, validates it, and reports what is wrong in a form the
author can act on.

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

## Warnings are not errors

A station with zero capacity is legal and almost certainly a mistake, so it
loads with a `TF-C3xx` warning. Pass `strict=True` to make any finding fail.

The public symbols are listed in [API.md](API.md).
