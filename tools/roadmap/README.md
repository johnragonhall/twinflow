---
title: twinflow-roadmap
description: Reads the roadmap as data, proves every requirement is placed, and refuses a plan that quietly drops one.
topic_type: concept
audience: contributors
---

# twinflow-roadmap

Program management as code. The plan is four YAML files, ROADMAP.md is their
readable projection, and the issue tracker is their public one.

That arrangement exists to make one claim checkable. This project records every
idea and reorders rather than cuts, and a claim like that is worth nothing while
the only thing enforcing it is somebody's memory. Here a requirement with no
coverage entry fails the build, the status enum has no `canceled` member, and
the label an idea would be dropped under does not exist in the repository.

## Install

```bash
pip install twinflow-roadmap
```

It imports nothing else in this workspace on purpose. `roadmap validate` is the
first thing CI runs on a branch that broke the twin, so it has to run on a
checkout that does not build.

## Use

```bash
just roadmap validate      # the graph, the references, and the gate registry
just roadmap coverage      # every requirement id placed, and the ones that are not
just roadmap graph-lint    # the ROADMAP.md phase diagram against the data
just roadmap drift         # the tracker, the banned label, and the sync policy
just roadmap gates --phase P0
```

```python
from twinflow_roadmap import Roadmap, check_coverage

roadmap = Roadmap.load(repo_root)
for finding in roadmap.validate():
    print(finding)
print(check_coverage(roadmap).render())
```

## The four files

| File                | Holds                                                                      |
|---------------------|----------------------------------------------------------------------------|
| `requirements.yaml` | The requirement register: one entry per source atom, append-only           |
| `splits.yaml`       | One entry per lettered half of a requirement that lands in two phases      |
| `gates.yaml`        | Every gate id, declared at Phase 0, with its kind, first phase, and status |
| `roadmap.yaml`      | The phases, the work packages, what each covers, and what each depends on  |

`requirements.yaml` holds source atoms only. `E4a` is not an entry there,
because the source carries only `E4` and a split label has neither a source line
nor a verbatim clause. That restriction is what lets the append-only check stay
absolute while nine requirements still land in two or three phases each.

## What a finding looks like

```text
roadmap.yaml:1284  [WP-COVER-ID] WP-P3-07 covers E99, which the requirement register does not carry
gates.yaml:412     [GATE-EARLY] VAL-GATE-YARD-001 is still declared and WP-P1-04 in phase P1
                   references it. A gate reached by the open phase or the next one carries its
                   assertion and its falsifier
```

Nothing stops at the first problem. A validator that raised on one finding would
tell a contributor about one of the eight things they got wrong and let them
find the other seven one CI run at a time.

## The rules with teeth

- **Nothing is cut.** Every requirement id is covered, exactly one covering work
  package carries `partial: false`, and it is the last one in build order.
- **Nothing is reworded.** Once a requirement carries its verbatim clause, an
  edit to that clause fails, in the git history and over generated file pairs.
- **A gate is specified one phase ahead.** A work package in the open phase or
  the next one may not reference a gate that still says nothing.
- **The diagram is checked, not trusted.** The Mermaid graph in ROADMAP.md is
  re-parsed and compared with the data, because a drifted dependency picture is
  worse than none: a reader believes it.
- **The open phase is derived.** It is the earliest phase holding work that is
  not done, rather than a pointer somebody forgets to move.

## Not here yet

`render`, `sync`, and `phase-exit` land with WP-P0-13 and WP-P0-14, and the
networkx, jinja2, and typer dependencies land with them. Until then ROADMAP.md
is maintained by hand under the same rules and `drift` reports what it could not
check rather than passing quietly.
