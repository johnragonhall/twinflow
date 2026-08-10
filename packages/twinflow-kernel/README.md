---
title: twinflow-kernel
description: The deterministic simulation seam - the ports every other twinflow package takes as a parameter.
topic_type: reference
audience: contributors
---

# twinflow-kernel

The seam that lets one codebase run two ways: as real containers talking to
real services, and as a single-process deterministic simulation that replays a
scenario bit for bit.

Every other package takes its clock, randomness, network, and storage as
parameters rather than reaching for them. That is the whole trick, and it is
enforced mechanically: `TWF-DET-001` fails CI on a direct wall-clock, RNG, or
socket call outside this package.

## Install

```bash
pip install twinflow-kernel
```

## Use

```python
from twinflow.kernel import SimClock, PacedClock, duration_from_seconds

clock = SimClock()                      # microsecond ticks by default
deadline = clock.timeout(duration_from_seconds(60, tick_hz=clock.tick_hz))

watchable = PacedClock(clock, speed=50.0)   # 50x real time for a demo
```

## Sim time is an integer

No float represents a point in time or a duration on any visible surface. A
config author writes `"4.5 min"` and the loader converts it to exact ticks with
round-half-up away from zero, which is not what Python's `round` does.

The clock is non-decreasing and refuses to run backwards. Equal is allowed:
two events at one instant are ordered by the envelope key, not by the clock.

## Time compression is safe by construction

`PacedClock` delays the loop *between* events and never reorders them, so a
paced run and an unpaced run emit identical logs. Only the wall time at which
each line appears differs. `test_pacing_does_not_change_the_tape` asserts it.

It is the one place in this package that reads a wall clock, it reads a
monotonic one, and that reading never reaches an event payload, the hashed
tape, or a branch.

The public symbols are listed in [API.md](API.md).
