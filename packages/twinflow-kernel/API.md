---
title: twinflow-kernel API
description: Every public symbol twinflow-kernel owns, which boundary rule A1.4 requires each package to list.
topic_type: reference
audience: contributors
---

# twinflow-kernel API

Boundary rule A1.4 gives every public symbol exactly one owning package. These
are the names this package owns today. The remaining ports of foundations
section 2.2 arrive with the phases that need them: a port with no
implementation and no consumer is a name nobody has tested.

| Symbol                  | Kind     | What it is                                                             |
| ----------------------- | -------- | ---------------------------------------------------------------------- |
| `Clock`                 | protocol | The port a component takes when it needs to know the time              |
| `SimClock`              | class    | Integer tick time for one run, non-decreasing                          |
| `PacedClock`            | class    | The D-02 pacer: wraps a clock and blocks so sim time tracks wall time  |
| `SimInstant`            | type     | Non-negative integer ticks since the sim epoch                         |
| `Duration`              | type     | Signed integer ticks                                                   |
| `TickResolution`        | constant | The three legal tick rates, each with declared overflow arithmetic     |
| `DEFAULT_TICK_HZ`       | constant | 1000000, microsecond ticks                                             |
| `MAX_SIM_YEARS`         | constant | 100, the horizon cap of T4                                             |
| `MAX_HORIZON_TICKS`     | constant | 2\*\*53 - 1, the float64 tick limit of T5                              |
| `duration_from_seconds` | function | Convert a written duration to exact ticks, half up away from zero      |
| `__version__`           | constant | The distribution version, read by the build so the two cannot disagree |

## Private

Everything under `twinflow.kernel._impl` is private, and boundary rule A1.1 is
enforced by an import-linter contract rather than by convention.

## Re-exports

None yet. When this package re-exports a value type owned by
`twinflow-schemas`, the borrowed name is declared in `[tool.twinflow]
reexports` so gate `IMPORT-3` can tell a re-export from a second owner.
