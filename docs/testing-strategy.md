---
title: Testing strategy
description: The six kinds of test this repository writes, how to pick one, and the rule that decides whether a test is worth keeping.
topic_type: concept
audience: contributors
---

# Testing strategy

The tiers and their time budgets live in
[CONTRIBUTING.md](https://github.com/johnragonhall/twinflow/blob/main/CONTRIBUTING.md).
This page covers the question that comes before the tier: what kind of test the
change needs, and what makes it worth keeping.

## Contents

1. [The rule everything else follows from](#1-the-rule-everything-else-follows-from)
2. [Six kinds of test](#2-six-kinds-of-test)
3. [Choosing one](#3-choosing-one)
4. [What a validation gate adds](#4-what-a-validation-gate-adds)
5. [Timing, and why it is bounded](#5-timing-and-why-it-is-bounded)
6. [What is not measured yet](#6-what-is-not-measured-yet)

## 1. The rule everything else follows from

Doctrine D-12 states it: a test that cannot fail is not a test. A test whose
assertion holds for every possible implementation measures nothing, and it is
worse than an absent test because it reports green and buys confidence it did
not earn.

The practical form of the rule is a question a reviewer asks out loud. What
input makes this test fail? A test with no answer does not merge. Section 3 of
[code-review.md](code-review.md) puts that question second in the reading order,
before the code itself.

The rule bites hardest on tests that look thorough. A test asserting that a
function returns a value of the right type passes against a stub. A test
asserting that a log has events passes against a log of the wrong events. Both
read as coverage and neither is.

## 2. Six kinds of test

| Kind            | Asserts                                                                        | Fails when                                                     |
| --------------- | ------------------------------------------------------------------------------ | -------------------------------------------------------------- |
| Known-answer    | Generated values match a frozen corpus, byte for byte                          | The generator changes at all, deliberately or not              |
| Property        | An invariant holds over inputs Hypothesis generates                            | Any generated input breaks the invariant                       |
| Determinism     | Two runs at one seed produce identical logs                                    | One byte differs                                               |
| Contract        | A producer and a consumer agree on a schema, and the differ finds no narrowing | A field is removed or a type narrows inside a major version    |
| Brick isolation | A package imports and works with nothing else installed                        | The package gained a hidden dependency on a sibling            |
| Validation gate | A computed statistic matches a published external reference                    | The implementation disagrees with the reference the gate names |

The first three carry most of the weight in Phase P0, because P0 ships
contracts rather than behavior.

A known-answer test is the strongest cheap test available. The RNG corpus is
regenerated and compared by `tools/gen_rng_kat.py --check`, so a change to the
derivation is caught at the commit that makes it rather than absorbed into a
later run. The corpus is frozen early on purpose: every day it does not exist
adds a file that will need regenerating, and phase P1 adds a second language
reading the same file.

A property test earns its place where the input space is too large to enumerate
and an invariant is easy to state. Stream independence is the example here. The
assertion is not that a particular pair of streams differs, it is that no pair
derived from distinct names collides, and that is a statement about all pairs.

## 3. Choosing one

Work down this list and take the first row that fits.

1. The change alters generated values that anything downstream depends on. Write
   a known-answer test and freeze the corpus.
2. The change adds a statistic. Write a validation gate against a published
   reference, per doctrine D-11, and declare the gate one phase before the
   statistic lands.
3. The change states an invariant that holds over a range of inputs. Write a
   property test.
4. The change crosses a package boundary or touches a schema. Write a contract
   test, and check that the schema differ agrees.
5. The change adds a public symbol to a package. Extend that package's brick
   isolation test.
6. The change fixes a bug. Write a regression test in the tier matching its
   runtime, not the tier matching where the bug lived. This one is a rule
   rather than a choice, and `VAL-GATE-REG-001` enforces it.
   [testing-policy.md](testing-policy.md) carries the procedure and the
   trailer that exempts a defect with no test which could fail.

A change matching none of the six is either an implementation detail with an
existing test above it, or a change whose effect nobody has stated. The second
case is the one to catch in review.

## 4. What a validation gate adds

A gate is not a bigger test. It is a test plus a named external reference plus a
declared falsifier, and the reference is the part that makes it different.

Doctrine D-11 refuses a gate whose expected value this repository computed. The
number comes from the NIST Statistical Reference Datasets, from chapter 6 of the
NIST/SEMATECH e-Handbook, or from another published source that the gate names.
Each test states which reference its own expected value came from, because the
sources cover different ground and a single blanket citation would be wrong.

The scope discipline is part of it. The StRD is a numerical-accuracy benchmark
whose stated scope names no control chart and no capability index, so those
expected values come from the e-Handbook instead. A project that cited the StRD
for a capability index would be citing a source that does not cover the claim.

Gates carry a status, and the required field set widens with it. A `declared`
gate owes an id, a first phase, and a standing flag. A `specified` gate owes its
assertion and its falsifier. An `implemented` gate owes a test on disk and the
command the phase-exit runner calls. `roadmap validate` fails a work package in
the open phase that references a gate still at `declared`.

## 5. Timing, and why it is bounded

Doctrine D-13 scopes timing tests to fit their budget. A test that measures
wall-clock duration is a test whose result depends on the machine, and a suite
full of them fails on a loaded runner and teaches contributors to re-run rather
than to read.

So timing assertions state a budget rather than a target, and the budget is set
where a real regression trips it and normal variance does not. The per-job
budgets live in `ci_budget.yaml`, and a job that gets slower has to say so
rather than drifting quietly.

The tier budgets work the same way. A tier that drifts past its budget gets
split or moved to a nightly run, because a slow gate is a gate people learn to
skip.

## 6. What is not measured yet

No coverage figure is published. Statement and branch coverage are named by the
OpenSSF Best Practices gold criteria, and
[code-review.md](code-review.md) section 6 records both as unmet rather than
estimating them. A coverage number arrives the same way every other number in
this repository arrives: from a recorded run, written into a marker, with the
commit that produced it.

Mutation testing is in no gate. `just mutants` runs it over the roadmap tool on
demand, and nothing in CI calls it. It is the technique that would answer
doctrine D-12 mechanically rather than by a reviewer's judgment, so until it
gates something the rule is enforced by reading. That is a real limit on how
strongly the rule holds, and it is stated here rather than left implied.

The cross-platform determinism gate reports a measured divergence and asserts no
bound. `VAL-GATE-DET-002` publishes the observed maximum on every run, and the
tolerance it compares against is set from a real two-platform run rather than
assumed. Until such a run has happened, the gate reports what it saw and holds
nobody to a number.
