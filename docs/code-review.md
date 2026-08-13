---
title: Code review policy
description: What a reviewer checks before a change lands, what blocks a merge outright, and which review criteria this repository cannot meet with one maintainer.
topic_type: reference
audience: contributors
---

# Code review policy

Every change to `main` passes the automated gates and a human read. This page
states what the human looks at, what stops a merge, and where the policy has a
gap that no process fixes.

The mechanics of opening a change live in
[CONTRIBUTING.md](https://github.com/johnragonhall/twinflow/blob/main/CONTRIBUTING.md).
This page is the standard the change is judged against.

## Contents

1. [The two halves](#1-the-two-halves)
2. [What blocks a merge](#2-what-blocks-a-merge)
3. [The reviewer checklist](#3-the-reviewer-checklist)
4. [Review depth by change class](#4-review-depth-by-change-class)
5. [Who reviews, and the gap that leaves](#5-who-reviews-and-the-gap-that-leaves)
6. [External criteria: met and unmet](#6-external-criteria-met-and-unmet)

## 1. The two halves

A machine checks the things a machine checks better. A human checks the rest,
and a review that spends its attention on formatting has spent it badly.

| Half      | Covers                                                                                                             | Runs                         |
| --------- | ------------------------------------------------------------------------------------------------------------------ | ---------------------------- |
| Automated | Formatting, types, lint, prose, spelling, import boundaries, wall-clock reads, license allowlist, roadmap coverage | `just check`, then CI        |
| Human     | Correctness, the test's power to fail, the claim a document makes, and whether the change belongs in this phase    | Before the merge, every time |

The automated half must be green before the human half starts. A reviewer
reading a change that has not passed `just check` is doing work the build was
going to do anyway.

## 2. What blocks a merge

Each row is a hard stop. None of them is waived by argument in a review thread,
because each one has a document or a gate behind it.

| Blocker                                                                       | Behind it                      |
| ----------------------------------------------------------------------------- | ------------------------------ |
| A red gate in the set in force at the open phase                              | `just gate phase-exit <phase>` |
| A number in a document that no recorded run produced                          | Section 1 of ENGINEERING.md    |
| A new statistic with no validation gate naming its external reference         | Doctrine D-11                  |
| A test whose assertion holds for every possible implementation                | Doctrine D-12                  |
| A wall-clock read outside the four places doctrine permits                    | Doctrine D-02                  |
| A dependency whose license is outside the allowlist                           | Decision D15                   |
| A milestone id removed from the plan rather than reordered                    | Section 1 of ROADMAP.md        |
| A public symbol owned by two packages, or a sideways import between bricks    | Doctrine D-09                  |
| An event envelope field added after P0 without a major version bump           | Doctrine D-07                  |
| A lint escape carrying no reason                                              | Section 11 of ENGINEERING.md   |
| A commit message that narrates the edit instead of stating what the code does | CONTRIBUTING.md                |

## 3. The reviewer checklist

Read in this order. The order matters, because a change that fails an early
item makes the later items moot.

1. Read the commit subject and the linked milestone. Check that the change is
   one logical change, and that it belongs to the phase now open.
2. Read the tests before the code. Ask what input makes each test fail. A test
   with no such input is doctrine D-12's defect, and it blocks the merge.
3. Read the code against the tests. Look for behavior the tests do not reach.
4. Check every claim the change makes in prose. A sentence stating a number
   names the run that produced it. A sentence citing a source names the source.
5. Check the seams. A new module reads the clock, draws randomness, opens a
   socket, and touches storage through an injected port, or it does none of
   those things.
6. Check what the change owes. A new statistic owes a gate. A new public symbol
   owes an entry in the package `API.md`. A new document owes front matter and
   a nav entry.
7. Check the blast radius. Name what breaks if this change is wrong, and say
   whether a gate would catch it.

## 4. Review depth by change class

Not every change earns the same attention, and pretending otherwise makes the
deep reviews shallower.

| Class                                                       | Depth                                                                               |
| ----------------------------------------------------------- | ----------------------------------------------------------------------------------- |
| A contract: event envelope, schema, seed derivation, config | Full checklist, plus a second read on a later day. These cannot be fixed by a patch |
| A statistic or a gate                                       | Full checklist, plus the external reference read at its source                      |
| A package public API                                        | Full checklist, plus the compatibility question the C9 policy asks                  |
| A test, a script, or a lint rule                            | Full checklist. A gate that is wrong is worse than a gate that is missing           |
| Prose in a shipped document                                 | Items 4 and 6 only, plus the prose gate                                             |
| A dependency bump                                           | The license allowlist, the lockfile diff, and a determinism run                     |

The first row carries the second read because a contract decision is the one
class of change this repository cannot walk back. Doctrine D-07 says why: an
envelope field added later is a major version bump on every schema subject.

## 5. Who reviews, and the gap that leaves

One maintainer owns this repository and merges every change. That is stated
plainly here rather than dressed up, because it is the weakest part of the
process and no wording fixes it.

What one person can do is separate the reading from the writing. A contract
change gets its second read on a later day, so the reviewer is not the author
still holding the argument in their head. An outside pull request gets a review
by someone who did not write it, which is the only case where the separation is
structural rather than a habit.

What one person cannot do is catch the error they cannot see. The compensations
are mechanical, and each is listed so a reader can judge whether they are
enough:

The gate registry states what falsifies each claim, and a gate is written before
the subsystem that satisfies it, so the assertion is fixed while the
implementation that might bend it does not exist yet.

Doctrine D-11 makes a validation gate cite a published external reference. A
number this repository computed and then asserted against itself is not
evidence, and that rule holds whether one person or ten wrote the code.

CodeQL and OpenSSF Scorecard run on the repository, and `zizmor` lints the
workflows. Those find classes of defect a single reader misses.

## 6. External criteria: met and unmet

The OpenSSF Best Practices badge criteria name a documented review policy at the
gold level. This page is that document. The same criteria name two things this
repository does not meet, and both are recorded here rather than left for a
reader to find.

| Criterion                                                      | State here                                                                                                 |
| -------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------- |
| The project documents its code review requirements             | Met by this page                                                                                           |
| At least half of proposed changes reviewed by a non-author     | Not met. One maintainer writes and merges. Section 5 states what stands in for it                          |
| A bus factor of two or more                                    | Not met. One maintainer                                                                                    |
| At least two unassociated significant contributors             | Not met. This is a single-author portfolio and reference project                                           |
| Automated test suite with stated statement and branch coverage | Not met yet. No coverage figure is published, because none has been recorded                               |
| A security review within the last five years                   | Not met. No assessment has been done, and `security-insights.yml` records that as an empty self assessment |

The three contributor criteria are structural. A single-author repository cannot
satisfy them, and claiming otherwise would be the kind of unbacked assertion the
rest of this project exists to avoid. They are listed so that a reader comparing
this repository against the badge criteria gets the answer from here rather than
from a discrepancy.
