---
title: twinflow-dashboard API
description: Every public symbol twinflow-dashboard owns, which boundary rule A1.4 requires each package to list.
topic_type: reference
audience: contributors
---

# twinflow-dashboard API

Boundary rule A1.4 gives every public symbol exactly one owning package. These
are the names this package owns. Gate `IMPORT-3` fails when `__all__` and this
package's declared ownership disagree.

## The application

| Symbol              | Kind     | What it is                                                        |
| ------------------- | -------- | ----------------------------------------------------------------- |
| `create_app`        | function | Build the ASGI app for one dashboard deployment                   |
| `serve`             | function | Run it on the configured address                                  |
| `viewer_asset_root` | function | Where the shipped viewer assets live, for the entry-point group   |
| `index_html`        | function | The shipped page, read off disk unchanged                         |
| `INDEX_FILENAME`    | constant | `index.html`, the single file requirement 8 names                 |
| `CSP_TEMPLATE`      | constant | The served content security policy, with the API origin as a slot |
| `DashboardConfig`   | class    | The `facility.yaml` dashboard block, validated                    |

## Severity encoding

| Symbol              | Kind     | What it is                                                     |
| ------------------- | -------- | -------------------------------------------------------------- |
| `SeverityLevel`     | class    | One severity, with every channel that carries it               |
| `SEVERITIES`        | constant | The five levels, most severe first, with their side counts     |
| `SEVERITY_NAMES`    | constant | The same five as names                                         |
| `SEVERITY_CHANNELS` | constant | The four channels of section 6.1: text, shape, color, position |
| `MIN_GLYPH_PX`      | constant | 14, the smallest a glyph renders at                            |
| `severity_for`      | function | One level by name, or a `KeyError` naming the legal set        |
| `FindingClass`      | class    | One class of finding and the `kind` values it covers           |
| `FINDING_CLASSES`   | constant | The six classes of section 6.3, safety first                   |
| `BANDED_CLASSES`    | constant | The two that render in the exempt safety band                  |
| `finding_class_for` | function | The class a kind belongs to, falling to `other`                |
| `finding_sort_key`  | function | The findings stream order of section 6.3                       |

## The accessibility floor

| Symbol                     | Kind     | What it is                                                |
| -------------------------- | -------- | --------------------------------------------------------- |
| `A11Y_GATE_ID`             | constant | `VAL-GATE-A11Y-001`                                       |
| `WCAG_REFERENCE`           | constant | The published standard the gate names                     |
| `WCAG_REFERENCE_URL`       | constant | Its locator                                               |
| `DemoStep`                 | class    | One demo step, and the control a keyboard reaches it by   |
| `DEMO_PATH`                | constant | The path a reader takes through the stub, in order        |
| `FOCUS_ORDER`              | constant | The six landmarks in the tab order section 10 fixes       |
| `MIN_TARGET_PX`            | constant | 24, the target-size floor                                 |
| `MOTION_TOKEN_PREFIX`      | constant | The prefix every duration in the stylesheet is written as |
| `REDUCED_MOTION_QUERY`     | constant | The media query the tests read                            |
| `REDUCED_MOTION_ATTRIBUTE` | constant | The in-interface override selector                        |

## The command path

| Symbol             | Kind     | What it is                                                          |
| ------------------ | -------- | ------------------------------------------------------------------- |
| `CommandKind`      | class    | One row of the dispatch table of section 4.2                        |
| `COMMAND_KINDS`    | constant | The whole table, sorted by name                                     |
| `COMMAND_NAMES`    | constant | The same set as names, which `CT-UI-3` compares                     |
| `SERVER_HANDLED`   | constant | The kinds that cross the wire at all                                |
| `COMMAND_SUBJECT`  | constant | `ui.command.v1`                                                     |
| `COMMAND_PRODUCER` | constant | `dashboard`, one of the closed producer set of invariant E3         |
| `validate_command` | function | Check one command against the table, or refuse it with every reason |
| `CommandError`     | class    | A refused command, carrying all its reasons at once                 |
| `CommandLog`       | class    | Assigns each accepted command its dense per-producer sequence       |
| `AcceptedCommand`  | class    | The position a command took, as the browser gets it back            |

## Packaging

| Symbol        | Kind     | What it is                                                             |
| ------------- | -------- | ---------------------------------------------------------------------- |
| `__version__` | constant | The distribution version, read by the build so the two cannot disagree |

## Behavior worth knowing

`create_app` takes the clock as a plain `Callable[[], int]` rather than the
kernel's `Clock` port. Section 2.1 of the design page fixes this package's
dependencies at four names, and taking `twinflow-kernel` for one method would
pull numpy into an install whose whole claim is that it is small. What doctrine
D-02 requires is that the reading arrive from outside, and it does.

`create_app` takes a `sink` for accepted commands and defaults it to a list on
`app.state.recorded` rather than to a no-op. A dropped command that answered 202
would be an audit-log hole nothing observes.

A refused command consumes no sequence number. A counter that advanced on refusal
would leave a gap, and `Historian.append` refuses the event after the gap rather
than the one that caused it.

Replaying a `command_id` returns the original position rather than taking a
second one. Section 4.2 calls commands idempotent by `command_id`, and a retry
after a dropped response is the ordinary case.

`finding_sort_key` orders by class before severity, so a medium safety finding
sorts above a critical quality finding. It never changes the severity a producer
emitted; the class word renders beside the severity word so the ordering is
explained on screen rather than inferred.

## Re-exports

None.

## Names this package does not export

`Envelope` is owned by `twinflow-schemas` and reaches this package as the type
`CommandLog` mints. `TickResolution` is owned by `twinflow-kernel`, and
`twinflow.dashboard.config` keeps its own three integers rather than taking a
dependency on that package for a constant.
