---
title: twinflow-roadmap API
description: Every public symbol twinflow-roadmap owns, which boundary rule A1.4 requires each package to list.
topic_type: reference
audience: contributors
---

# twinflow-roadmap API

Boundary rule A1.4 gives every public symbol exactly one owning package. These
are the names this package owns.

| Symbol           | Kind     | What it is                                                                 |
|------------------|----------|----------------------------------------------------------------------------|
| `Roadmap`        | class    | The four files read together, with `load`, `validate`, and the phase views |
| `load`           | function | Read a roadmap from a repository root                                      |
| `check_coverage` | function | Prove every requirement id is placed and the partial flags close           |
| `CoverageReport` | class    | The result: tier counts, unplaced ids, and findings                        |
| `check_drift`    | function | Check the tracker and the sync policy, offline or through `gh`             |
| `DriftReport`    | class    | The result: findings, plus what could not be checked and why               |
| `graph_lint`     | function | Compare the ROADMAP.md phase diagram with the data                         |
| `render_mermaid` | function | The phase graph as `roadmap.yaml` holds it                                 |
| `parse_mermaid`  | function | Read a rendered graph back, so a claim about it can be checked             |
| `missing_quotes` | function | Requirement ids carrying no verbatim source clause                         |
| `Finding`        | class    | One problem: rule id, message, file, line, and the ids it is about         |
| `RoadmapError`   | class    | Raised when a file cannot be read at all                                   |
| `Requirement`    | class    | One atom of the source, with no status field by construction               |
| `Split`          | class    | One lettered half of a requirement that lands in two phases                |
| `Coverage`       | class    | One requirement covered by one work package, with its `partial` flag       |
| `WorkPackage`    | class    | The unit of build, of an issue, and of a commit series                     |
| `Phase`          | class    | One release, with its two dependency namespaces                            |
| `Gate`           | class    | One phase-exit assertion, with the fields its kind and status owe          |
| `Release`        | class    | A tag and the compatibility promises it carries                            |
| `PHASE_IDS`      | constant | The closed set of phase identifiers                                        |
| `__version__`    | constant | The distribution version, read by the build so the two cannot disagree     |

## Rule ids

A finding carries a rule id. The id is what a contributor searches for and what
a test asserts on, so the wording can improve without breaking either.

| Rule                                      | Refuses                                                            |
|-------------------------------------------|--------------------------------------------------------------------|
| `REQ-SHAPE`, `REQ-DUP`                    | A malformed or repeated requirement entry                          |
| `SPL-REQ`, `SPL-SPLITTABLE`, `SPL-LABEL`  | A split naming an unknown, unsplittable, or mismatched requirement |
| `SPL-WP`, `SPL-UNUSED`                    | A split pointing at no work package, or one nothing covers         |
| `PHASE-ID`, `PHASE-DUP`                   | A phase id outside the closed set, or declared twice               |
| `PHASE-DEP`, `PHASE-REQ`                  | A dependency naming the wrong namespace or nothing at all          |
| `PHASE-TAG`, `PHASE-ORDER`                | A tag that is not semver, or does not rise with the phase order    |
| `PHASE-CYCLE`, `PHASE-EMPTY`              | A cycle between phases, or a release holding no work               |
| `PHASE-EXITGATES`                         | An authored `exit_gates`, which is derived from the gate registry  |
| `WP-ID`, `WP-PHASE`, `WP-DUP`             | A work-package id that does not parse or disagrees with its phase  |
| `WP-COVER-STRING`, `WP-COVER-SPLIT`       | A bare string coverage entry, or one naming a split label          |
| `WP-COVER-ID`, `WP-COVER-NOTE`            | Coverage of an unknown id, or a partial with no note               |
| `WP-DEP`, `WP-CYCLE`                      | A dependency that does not resolve, or one that closes a cycle     |
| `WP-PHASE-ORDER`, `WP-WAVE`               | A dependency that ships later, or sits at an equal wave            |
| `WP-DELIVERABLE`, `WP-BRICK`              | No deliverable in the open phase, or a brick this workspace lacks  |
| `WP-REORDERED`                            | A reorder with no destination or no reason                         |
| `GATE-PHASE`, `GATE-FIELDS`               | A gate whose phase does not resolve, or that owes its kind a field |
| `GATE-TEST`, `GATE-ORPHAN`, `GATE-EARLY`  | A missing test, a gate nothing runs, or one specified too late     |
| `COV-UNPLACED`, `COV-PARTIAL`, `COV-LAST` | A requirement nobody places, or partial flags that do not close    |
| `GRAPH-NODE`, `GRAPH-ORDER`, `GRAPH-EDGE` | A diagram that has drifted from the data                           |
| `GRAPH-CYCLE`                             | A diagram that is not acyclic                                      |
| `APPEND-REMOVED`, `APPEND-QUOTE`          | A removed requirement, or a reworded verbatim clause               |
| `SYNC-BANNED`, `SYNC-DRYRUN`              | A sync config that disables a policy it is meant to enforce        |
| `DRIFT-LABEL`, `DRIFT-NOTPLANNED`         | The banned label existing, or a requirement closed as not planned  |

## Not here yet

`Roadmap.render_markdown`, `Roadmap.render_mermaid` as a method, `Roadmap.graph`
as a networkx projection, `GateRegistry`, and `GitHubSync` land with WP-P0-13.
The command line grows `sync` and `phase-exit` at the same time.
