---
title: Layer map
description: Every workspace package and every level split, with its ISA-95 level, its Purdue level, its compute tier, and its latency budget.
topic_type: reference
audience: contributors
---

# Layer map

This page is RA-a. It places every package in the uv workspace on the ISA-95 and
Purdue level scales. It names the compute tier that runs each one, and the
latency budget that tier carries. Gate `VAL-GATE-TIER-001` reads the package
table below. The gate fails on one unfilled cell, or on one package with no
row.

Section 4 of [ARCHITECTURE.md](https://github.com/johnragonhall/twinflow/blob/main/ARCHITECTURE.md) maps the architecture components. This
page maps the distributions, which is a different list. A component can span
several packages. A package can be a library that no component names.

## 1. The levels

ANSI/ISA-95 is a paid standard and its text is not reproduced here. The table
below states the level meanings this repository uses. The mapping is a design
decision, not a quotation.

| Level | ISA-95                                                         | Purdue                                         |
|-------|----------------------------------------------------------------|------------------------------------------------|
| 0     | The physical process                                           | The physical process                           |
| 1     | Sensing and actuation, PLC analog                              | Basic control: sensors, actuators, controllers |
| 2     | Monitoring and supervisory control, SCADA and historian analog | Area supervisory control: HMI, SCADA           |
| 3     | Manufacturing operations management, MES and analytics analog  | Site operations: MES, historian, scheduling    |
| 3.5   | Not an ISA-95 level                                            | Industrial DMZ: the mediated boundary          |
| 4     | Business planning and logistics, business and agent layer      | Business logistics: ERP, planning              |

## 2. The compute tiers

Compute placement is an explicit decision, not a consequence of where code was
easy to run. Section 6 of [ARCHITECTURE.md](https://github.com/johnragonhall/twinflow/blob/main/ARCHITECTURE.md) states four tiers, each with
a latency budget.

| Tier | Location               | Physical analog                     | Latency budget                                 |
|------|------------------------|-------------------------------------|------------------------------------------------|
| 0    | On-device              | Sensor or embedded controller       | Microseconds to a few milliseconds             |
| 1    | Edge gateway, per area | Gateway appliance on the OT segment | Safety checks under 100 ms, flagging under 1 s |
| 2    | Site                   | Server room, DMZ and site network   | Seconds to minutes                             |
| 3    | Network                | Central or hosted                   | Minutes to hours, no interactive budget        |

One rule governs the placement. A function may run at a lower tier than its
budget needs, never at a higher one. A safety check may move down to tier 0 when
the signal is there. It may never move up to tier 2, because a tier-2 placement
makes the decision depend on a network link.

## 3. The latency budgets

Each budget below is a declared target for a class of decision. Section 6 of
[ARCHITECTURE.md](https://github.com/johnragonhall/twinflow/blob/main/ARCHITECTURE.md) is the source, and every row keeps the name that
source gives it. Section 5 of this page says what these budgets are not.

| Decision class            | Budget             | Enforced at |
|---------------------------|--------------------|-------------|
| Safety interlock          | Under 100 ms       | Tier 0 or 1 |
| Machine protection trip   | Under 100 ms       | Tier 0 or 1 |
| Anomaly flag              | Under 1 s          | Tier 1      |
| Operator dashboard update | Under 2 s          | Tier 2      |
| Finding to work order     | Seconds to minutes | Tier 2      |
| What-if experiment        | Minutes            | Tier 2 or 3 |
| Planning and optimization | Hours              | Tier 3      |

## 4. The workspace packages

Every row is one distribution in the uv workspace. The `Package` cell is the
name you install.

<!-- layer-map:packages -->

| Package              | ISA-95                                           | Purdue                  | Compute tier             | Latency budget                                                       | Real-world counterpart                                                         |
|----------------------|--------------------------------------------------|-------------------------|--------------------------|----------------------------------------------------------------------|--------------------------------------------------------------------------------|
| `twinflow-schemas`   | Cross-cutting                                    | Cross-cutting           | 0 to 3                   | The caller's budget                                                  | Schema registry in a UNS platform                                              |
| `twinflow-rng`       | Cross-cutting                                    | Cross-cutting           | 0 to 3                   | The caller's budget                                                  | No plant counterpart. The determinism substrate                                |
| `twinflow-kernel`    | Cross-cutting                                    | Cross-cutting           | 0 to 3                   | The caller's budget                                                  | No plant counterpart. The simulation runtime                                   |
| `twinflow-config`    | Cross-cutting                                    | Cross-cutting           | 0 to 3                   | The caller's budget                                                  | The facility model in a UNS platform                                           |
| `twinflow-twin`      | L0                                               | L0                      | 2                        | Seconds to minutes                                                   | The physical process. As software, an AnyLogic-class discrete-event simulation |
| `twinflow-sensors`   | L1                                               | L1                      | 0 and 1                  | Microseconds to a few milliseconds at tier 0, under 100 ms at tier 1 | Field instrumentation, and the protocol gateway in front of it                 |
| `twinflow-storage`   | L2                                               | L3, published into L3.5 | 2                        | Seconds to minutes                                                   | Plant historian, the L2 system of record for time-series                       |
| `twinflow-agent`     | L4                                               | L4                      | 3                        | Minutes to hours, no interactive budget                              | Control tower and operations copilot                                           |
| `twinflow-api`       | L2 for live line state, L4 for findings and KPIs | L2 and L4               | 2                        | Under 2 s for an operator dashboard update                           | The read API behind an HMI and a BI tool                                       |
| `twinflow-dashboard` | L2 for live line state, L4 for findings and KPIs | L2 and L4               | 2                        | Under 2 s for an operator dashboard update                           | HMI for the line view, BI for the analytics view                               |
| `twinflow-roadmap`   | Outside the model                                | Outside the model       | Build time, not run time | No run-time budget                                                   | Program management tooling                                                     |

Four of those rows say `Cross-cutting` in both level columns. `twinflow-schemas`,
`twinflow-rng`, `twinflow-kernel`, and `twinflow-config` are libraries. Each one
runs inside the process of whatever calls it, so it sits at no single level and
at no single tier. Their budget cell says the same thing: the caller owns the
budget, and the library adds none of its own. Writing a number there would state
a budget nobody set.

`twinflow-twin` is the L0 process, because in this system the twin stands in for
the plant. Its software runs at tier 2, beside the historian, because a process
model needs the full site state.

`twinflow-api` has no row of its own in section 4 of [ARCHITECTURE.md](https://github.com/johnragonhall/twinflow/blob/main/ARCHITECTURE.md).
It is the read path the dashboard goes through, so it takes the dashboard's
levels and the dashboard's split.

`twinflow-roadmap` is the one member outside the layer model. It is program
management as code, it lives under `tools/` rather than under `packages/`, and
nothing at run time imports it. It still owns a row, for two reasons. The gate
says every package in the uv workspace, and `tools/roadmap` is a workspace
member. A reader who installs it alone needs to be told that it models no part
of a plant, and a silent exclusion tells them nothing.

## 5. What the budget column is not

Every budget on this page is a declared target. Not one of them is a
measurement. The measured decision latency for each tier arrives with
WP-P6-W1-01, which measures the four compute placement tiers:
<!--METRIC:decision_latency_by_tier@v1.1.0-->TBD<!--/METRIC-->.

A budget belongs in the table because it is a decision, and a decision is
knowable the day the package is placed. A measurement belongs behind the marker
above, where `scripts/checks/metric-marker-gate.sh` counts it. The layer map
gate rejects a marker inside the four checked columns for that reason.

## 6. Two components that sit at two levels

| Component  | Why it is two                                                                                               | Levels      |
|------------|-------------------------------------------------------------------------------------------------------------|-------------|
| Dashboard  | Two products on one page: a live view of the running line, and an analytics view of findings and KPIs       | L2 and L4   |
| UNS broker | Both the area-level message bus and the mediated crossing point, which is how a real UNS broker is deployed | L2 and L3.5 |

Neither split is an unresolved argument. Each names a component that does two
jobs at two levels, and collapsing it to one level would misplace one of them.

## 7. How this page is checked

`scripts/checks/layer-map-gate.py` reads the table under the
`<!-- layer-map:packages -->` anchor. It takes the member list from
`tool.uv.workspace.members` in the root `pyproject.toml`. That is the same route
`scripts/checks/workspace-members-gate.py` takes, so the two gates cannot
disagree about what a member is.

Run it:

```text
uv run python scripts/checks/layer-map-gate.py
uv run python scripts/checks/layer-map-gate.py --selftest
```

The gate fails on any one of these:

- a member with no row
- a checked cell holding a placeholder
- a metric marker inside a checked column
- a renamed or missing column
- a row naming a package the workspace does not hold

The selftest breaks each of those in turn. It fails when the rule it broke stays
quiet.
