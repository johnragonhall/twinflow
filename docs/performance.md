---
title: Performance standard
description: How a change earns the right to be called faster here, which optimizations determinism forbids, and the order to try fixes in.
topic_type: concept
audience: contributors
---

# Performance standard

The fastest code is the code that never runs. The second fastest is the code
simple enough that a reader can see what it does.

This page states how performance work is done here. It binds the same way
[ENGINEERING.md](https://github.com/johnragonhall/twinflow/blob/main/ENGINEERING.md)
binds: a claim about speed is a quantitative claim, and this repository does not
ship a quantitative claim it has not measured.

## Contents

1. [No claim without a number](#1-no-claim-without-a-number)
2. [Determinism bounds what you may optimize](#2-determinism-bounds-what-you-may-optimize)
3. [What counts as a measurement](#3-what-counts-as-a-measurement)
4. [Check the target before calling an input small](#4-check-the-target-before-calling-an-input-small)
5. [The ladder](#5-the-ladder)
6. [What you may apply, and what needs sign-off](#6-what-you-may-apply-and-what-needs-sign-off)
7. [Simplification is a performance strategy](#7-simplification-is-a-performance-strategy)
8. [Never traded for speed](#8-never-traded-for-speed)
9. [Recording the decision](#9-recording-the-decision)
10. [What is not measured yet](#10-what-is-not-measured-yet)

## 1. No claim without a number

Donald Knuth wrote, in "Structured Programming with go to Statements" for ACM
Computing Surveys in 1974, that "premature optimization is the root of all evil".
The sentence is usually quoted without the rest of the passage, which says a good
programmer "will be wise to look carefully at the critical code; but only after
that code has been identified".

That is the rule here, and it cuts both ways. Care intensely about the part a
measurement identified. Leave the rest alone.

A hand-tuning change needs a profile or a benchmark naming the hotspot. The word
"faster" in a commit message, a comment, or a review is a result, and section 1
of ENGINEERING.md governs a result: it comes from a recorded run, with the seed
and the commit that produced it, or it is not stated.

One exception, and it is narrow. A complexity-class fix is allowed on inspection
when the input is unbounded or demonstrably large: a query inside a loop, an
N-plus-one, a nested scan over a collection that grows with the facility. A
bounded collection does not qualify. Below some size a linear scan over
contiguous memory beats a hash lookup. The complexity class hides both the
constant factors and the cache behavior, and both favor the simple structure, so
"fewer operations in theory" is not a reason on its own.

## 2. Determinism bounds what you may optimize

This constraint is specific to this repository, and it removes techniques that
are ordinary elsewhere. One run seed governs every stochastic stream, and
`VAL-GATE-DET-001` fails on one differing byte between two runs. An optimization
that changes the event log is not a faster version of the code. It is a different
program.

| Technique                                                               | Status inside the tape                                                                                      |
| ----------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------- |
| Reordering an iteration whose order can reach an event or a hash        | Refused. Doctrine D-03 makes iteration order explicit for this reason                                       |
| Floating-point reassociation, fused-multiply-add contraction, fast-math | Refused. It changes results, which fails DET-001 and moves the DET-002 divergence                           |
| Parallelism whose completion order reaches the log                      | Refused unless the tape is proven identical. Doctrine D-04 puts a non-deterministic solver outside the tape |
| Caching a pure function keyed on its inputs                             | Allowed, with the invalidation decision written down                                                        |
| Work moved off the critical path that no event observes                 | Allowed                                                                                                     |

The paced clock is the model for a legal optimization. Pacing changes when an
event is emitted in wall time. It never changes which event is emitted or in what
order, and `test_pacing_does_not_change_the_tape` asserts exactly that. Judge any
performance change to the simulated world the same way: run the determinism tier
and show the hash still matches.

Outside the tape, in the dashboard, the report generators, the tooling, and the
gates, none of this applies. The constraint follows the event log, not the
repository.

## 3. What counts as a measurement

Execution time is the primary metric. Use the wall clock for batch work, and
percentiles for anything a reader waits on. An average hides the tail a reader
feels, so report p50, p95, and p99 rather than a mean.

Measure before and after, because the delta is the deliverable. A single run
showing a small gain is indistinguishable from noise on ordinary hardware, so
repeat the run, report the median with its spread, and treat a result inside the
noise as no result.

Predict first, then measure, then read the gap. Estimate whether the work is
bound by computation or by memory traffic before touching it, because that
decides which rungs below can pay at all. When the measurement is far from the
prediction, the gap is the finding, and it is usually worth more than the tuning
you set out to do.

Amdahl's Law sets the ceiling. A part taking one twentieth of the runtime cannot
return more than about one twentieth however hard it is tuned, so target the
largest fraction rather than the first flaw you notice. Doctrine D-13 scopes
timing assertions to a budget, and `ci_budget.yaml` carries the per-job budgets a
regression has to trip.

Measure a release build. A benchmark of a debug build measures the build.

## 4. Check the target before calling an input small

A comment claiming a collection stays small describes what its author had in
mind. The project's own documents are what settle the scale, and they are
readable.

[ROADMAP.md](https://github.com/johnragonhall/twinflow/blob/main/ROADMAP.md) says
which phase a subsystem lands in and what depends on it. The facility profiles
say what a deployment tier holds, and the tiers differ by more than a constant.
The garage tier is one laptop. The growth and enterprise tiers are named in the
same roadmap, and a structure bounded at the first is not automatically bounded
at the third. A tier that has not been built yet is a reason to record the
assumption, not a reason to forget it.

Two habits follow.

Trace the caller before judging the cost. A function that looks hot alone may
already sit behind a cache one hop up, and a function that looks cheap alone may
run inside a loop three hops up. Cost belongs to the call site.

Reach a verdict rather than parking a guess. When reading the roadmap and the
call site settles the question, settle it: make the change, or record that you
investigated and none is needed, with the reasoning that closed it. An open
deferral is for a scope question only the maintainer can answer.

## 5. The ladder

Climb in order. Each rung is cheaper and safer than the one below it, and most
work stops well before rung six.

0. **Configuration before code.** Build flags, connection reuse, prepared
   statements, right-sized pools. Nothing in the code changes, so nothing in the
   correctness argument changes either.
1. **Do not do the work.** Delete what nothing calls, subject to section 8.
   Exit early. Cache pure work, with its invalidation decision. Skip work whose
   output nothing reads.
2. **Do it less often.** Batch. Paginate an unbounded list. Precompute at write
   time what is read many times.
3. **Fix the complexity class**, subject to section 1. A nested scan becomes a
   set lookup. A query in a loop becomes one query. A missing index gets added.
4. **Let the platform do it.** Push filtering into the query. Use the standard
   library implementation, which is tuned by people who do only that.
5. **Move it off the critical path**, subject to section 2. Much slowness is
   waiting rather than computing, so check the time spent off the processor
   before assuming a processor problem.
6. **Micro-optimize the measured hotspot**, only it, and only while the code
   stays readable or the trade is written down.

## 6. What you may apply, and what needs sign-off

| Class                | Techniques                                                                                                                                                       | Condition                                                          |
| -------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------ |
| Safe by default      | Removing duplicate work, hoisting loop-invariant work, the right data structure, avoiding an N-plus-one, fewer allocations in a hot loop, ordering tests by cost | None. These improve clarity and speed together                     |
| Measurement-gated    | Vectorization, cache blocking, memoization, concurrency, any rewrite that adds complexity                                                                        | A profile naming the hotspot first, and a second measurement after |
| Maintainer signs off | Lock-free concurrency, disabling bounds checks, floating-point reassociation, any trade of correctness for speed                                                 | Ask. Inside the tape, section 2 refuses several of these outright  |

## 7. Simplification is a performance strategy

Delete before you tune. Fewer layers means fewer cycles and fewer places for a
defect to sit, and the honest justification is correctness and maintainability
rather than any complexity score.

Prefer a deep module, one with a simple interface over a rich implementation, to
many shallow ones. John Ousterhout argues this in "A Philosophy of Software
Design". It is deliberately not the tiny-function rule a reader may expect: a
long routine somebody can follow beats a call chain that scatters the same logic
across six frames.

Martin Fowler's ordering in "Refactoring" is the one used here. Write code that
can be tuned, then tune the fraction measurement shows is hot. Where simplifying
and optimizing conflict, simplicity wins everywhere except a measured hotspot,
and there the complexity carries a comment saying what it buys.

## 8. Never traded for speed

Correctness beats speed. A fast wrong answer is a defect with good latency.

Input validation at a trust boundary, authentication, error handling, and
accessibility are exempt from both simplification and optimization. A cache ships
with its invalidation decision written down, because an unstated one is a plan to
serve stale data. An optimization that changes observable behavior, whether
ordering, timing, or precision, is stated in the change rather than slipped into
it.

Parked work is never deleted for looking unused. This repository never cuts
scope, so a module with no caller can be work staged ahead of its wiring. Before
proposing a deletion, grep `ROADMAP.md`, `roadmap.yaml`, and `gates.yaml` for the
file, its symbols, or its feature. Anything named there is parked, and it gets
flagged for wiring. Deleting code you did not write is a proposal for the
maintainer rather than an action.

## 9. Recording the decision

The tag is `PERF:`, which editors already highlight next to `TODO:` and `FIX:`.
It is deliberately not a name invented for this project, because a tag nobody
else uses stops ordinary tooling from finding these lines.

```text
# PERF: L3 - query in a loop becomes one query, 1.2s to 45ms, median of 10 runs
# PERF: L1 - memoized parse. Estimated: the function is pure and runs per frame
# PERF: deferred - the merge holds at the garage tier, revisit at the growth tier
# PERF: L3 rejected - the scan stays under the documented tier size, and an index
#       would add invalidation cost for no measurable win
```

A marker states what the code does now. The marker line is the only place a
before and an after belong, and the prose around it describes the current code,
because a future reader sees only that. Write "a borrowed value means the input
is unchanged, so nothing is copied" rather than an account of what the code did
before the edit.

Not every file needs a marker. A marker earns its place when it overrides what a
reader would otherwise assume, such as an input that looks small and is set by
the caller. Marking a clean file as reviewed is noise that buries the markers
that matter.

## 10. What is not measured yet

No profile exists, and no scaling curve has been recorded. `VAL-GATE-PERF-001`
holds the A4 load harness to a published curve on stated hardware. It starts at
v0.4.0, so nothing before that phase has a performance gate to pass.

What exists today is the budget layer. `ci_budget.yaml` carries a per-job time
budget, the test tiers in
[CONTRIBUTING.md](https://github.com/johnragonhall/twinflow/blob/main/CONTRIBUTING.md)
carry their own, and a tier drifting past its budget gets split rather than
tolerated. A budget is not a measurement of this system, and neither is a
published figure from somebody else's hardware. Until the harness runs, every
performance number about the simulated world is an unfilled marker, which is the
intended state rather than an oversight.

The build tooling is the exception, and it is a narrow one. Hook startup is
measured, because the change that cut it had to be justified against a number
rather than a preference. Those figures live in the header of
`scripts/hooks/resolve-python.sh` and in the marker at the top of the justfile,
each with the method that produced it. They say nothing about the simulation.
