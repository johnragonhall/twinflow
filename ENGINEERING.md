---
title: Engineering method
description: The eleven rules this repository is built under, what each one costs, and where the build enforces it without a human in the loop.
topic_type: concept
audience: contributors, and readers evaluating the project
---

# Engineering method

This file states how the work is done. It is not a style guide. The formatting
rules live in [CONTRIBUTING.md](CONTRIBUTING.md) and the writing rules live in
[docs/DOCUMENTATION-STANDARD.md](docs/DOCUMENTATION-STANDARD.md). What follows
is the reasoning those documents are downstream of.

Every rule below is enforced somewhere, and the enforcement column says where.
A rule with no enforcement is a preference, and preferences drift. Where a rule
costs something, the cost is stated rather than left for a contributor to
discover.

## Contents

1. [Evidence or TBD](#1-evidence-or-tbd)
2. [Say what falsifies it, before you build it](#2-say-what-falsifies-it-before-you-build-it)
3. [Contracts before capability](#3-contracts-before-capability)
4. [Nothing is deleted from the plan](#4-nothing-is-deleted-from-the-plan)
5. [A test that cannot fail is not a test](#5-a-test-that-cannot-fail-is-not-a-test)
6. [One home per rule](#6-one-home-per-rule)
7. [Scope the claim to what you can prove](#7-scope-the-claim-to-what-you-can-prove)
8. [Cross-cutting defects get one answer](#8-cross-cutting-defects-get-one-answer)
9. [Every brick comes out alone](#9-every-brick-comes-out-alone)
10. [The same command locally and in CI](#10-the-same-command-locally-and-in-ci)
11. [An escape hatch states its reason](#11-an-escape-hatch-states-its-reason)
12. [What this method costs](#12-what-this-method-costs)

## 1. Evidence or TBD

No document states a quantitative result the repository has not produced. Every
metric that is not yet measured appears as a marker holding `TBD`, and a marker
is only ever replaced by a number from a recorded run, with the seed and the
commit that produced it.

The rule has a hard edge. No estimate, no round figure, and no plausible guess
goes in a marker. At a tagged release the marker gate runs in release mode, and
a marker that release owes blocks the tag.

This exists because the README is what decides whether a reader trusts anything
else here. One invented number costs more than every honest one earns. The
visible consequence is that a reader arriving today finds a repository whose
headline numbers all read `TBD`, which is the intended state rather than an
oversight.

| Enforced by                                                                       | Where                |
| --------------------------------------------------------------------------------- | -------------------- |
| `metric-marker-gate.sh`, counting unfilled markers and failing on a malformed one | `scripts/checks/`    |
| Release mode, failing the tag on a marker that tag owes                           | The release workflow |

## 2. Say what falsifies it, before you build it

A validation gate is a named assertion, the thing that falsifies it, and the
command that runs it. Gates are declared at Phase 0 with the phase they start
at, so a subsystem states how it can be proven wrong one phase before it
exists.

Three statuses widen the required field set. A `declared` gate owes an id, a
first phase, and a standing flag. A `specified` gate owes its assertion and its
falsifier. An `implemented` gate owes a test on disk and the command the
phase-exit runner calls.

The phase-exit runner refuses to skip. A gate in force at a phase that is not
`implemented` fails the run, because the registry already promised it at the
phase it starts at. That is the difference between a plan and an intention.

The registry states its own totals, and `docs/gates.md` generates them from
`gates.yaml`. Read the count there rather than here: a count copied into prose is
a count that goes stale between two commits.

| Enforced by                                                                                     | Where                               |
| ----------------------------------------------------------------------------------------------- | ----------------------------------- |
| `roadmap validate`, refusing a work package that references a `declared` gate in the open phase | `tools/roadmap/`                    |
| `just gate phase-exit <phase>`, running every gate in force                                     | `scripts/checks/phase-exit-gate.py` |

## 3. Contracts before capability

Phase P0 ships no product. It fixes what a recorded run is: the event envelope,
the seed derivation, the schema registry, the config contract, and the release
pipeline.

Those are the decisions a later phase cannot change without invalidating every
run already recorded. Adding a field to the event envelope after P0 is a major
version bump on every schema subject. So the envelope lands in the root phase
and nowhere later.

The ordering is the point. A project that builds the dashboard first and the
determinism contract third has to choose, at that third step, between the
contract it wants and the recordings it already has.

| Enforced by                                                                             | Where                        |
| --------------------------------------------------------------------------------------- | ---------------------------- |
| `VAL-GATE-ENV-001`, asserting the envelope invariants over any log                      | `packages/twinflow-schemas/` |
| `VAL-GATE-SCH-001`, refusing a field removal or a type narrowing inside a major version | `tools/schema_diff.py`       |

## 4. Nothing is deleted from the plan

An idea recorded in the roadmap keeps its id forever. Ideas are reordered, and
section 5 of [ROADMAP.md](ROADMAP.md) records every move with the clause that
forced it.

The status vocabulary has no canceled value. The `wontfix` label does not exist
in this repository, and no issue carrying a `req:` label is closed as not
planned. An id that appears in no phase is a silent cut, and `roadmap coverage`
fails on one.

A cut list is the honest alternative, and this project keeps none because the
mechanical check is stronger. Scope reduction is a decision somebody has to
make in the open, rather than a file that quietly stops being mentioned.

| Enforced by                                                         | Where            |
| ------------------------------------------------------------------- | ---------------- |
| `roadmap coverage`, proving every milestone id is placed in a phase | `tools/roadmap/` |
| `roadmap drift`, and the banned-label policy                        | `tools/roadmap/` |

## 5. A test that cannot fail is not a test

Doctrine ruling D-12 states it. A test whose assertion holds for every possible
implementation measures nothing, and it is worse than no test because it reports
green.

Two habits follow. A known-answer test checks generated values against a frozen
corpus, so a change in the generator is caught rather than absorbed. A
property-based test asserts an invariant over generated inputs rather than over
one example, and Hypothesis is the tool.

Gates carry the same requirement in a stronger form. Doctrine D-11 says a
validation gate needs real external evidence, which means a published reference
value from a named source, not a value this repository computed and then
asserted against itself.

| Enforced by                                                  | Where                          |
| ------------------------------------------------------------ | ------------------------------ |
| The RNG known-answer corpus, regenerated and compared        | `tools/gen_rng_kat.py --check` |
| The property tier, run separately with its own budget        | `just test-property`           |
| Doctrine D-11, requiring a named external reference per gate | `gates.yaml`                   |

## 6. One home per rule

A rule lives in one place and every consumer reads it from there. The prose
gate holds no rules of its own: it reads them from `docs/style/banned-phrases.yml`
and `docs/style/ste-terms.yml`. The commit message gate does not carry the
accepted type set, it parses it out of the `commit-msg` hook.

The reason is drift. A second copy of a rule is a copy that disagrees with the
first one eventually, and then a commit the hook accepted fails the gate that
runs after it. Both halves are correct against their own copy, and the
contributor is the one who finds out.

The same rule applies to generated documents. `docs/gates.md` is written from
`gates.yaml` by `roadmap render`, and `roadmap render --check` fails the build
when it is stale.

| Enforced by                                                     | Where               |
| --------------------------------------------------------------- | ------------------- |
| `roadmap render --check`, failing on a stale generated document | `just roadmap-gate` |
| `gen_importlinter.py --check` and `gen_schemas.py --check`      | `tools/`            |

## 7. Scope the claim to what you can prove

Doctrine D-05 splits the determinism claim into two tiers, because one claim
covering both would be false. Tier one is byte-identical event logs at one seed,
one config, one platform, and one pinned dependency set. Tier two is identical
business events across platforms, with continuous fields agreeing inside a
tolerance measured from a real run rather than assumed.

The README then removes the overclaim the property invites. Determinism of the
run is not predictability of the operation, and reproducing a run byte for byte
and forecasting the next hour are different properties.

The cross-platform gate is the sharper example. It publishes the observed
maximum divergence on every run, and when that exceeds the recorded tolerance it
names whether the tolerance or the code is wrong. A gate that only says "failed"
sends somebody to read the code when the tolerance was the thing that was wrong.

| Enforced by                                                              | Where                          |
| ------------------------------------------------------------------------ | ------------------------------ |
| `VAL-GATE-DET-001`, two runs, one differing byte fails it                | `scripts/determinism-check.sh` |
| `VAL-GATE-DET-002`, two platforms, publishing the divergence it measured | The CI matrix                  |

## 8. Cross-cutting defects get one answer

An adversarial review of the fourteen design sections found contradictions,
dropped requirements, untestable claims, and determinism leaks. Most were local.
The ones where the same defect appeared in three or more sections were not,
because that pattern means each section invented its own answer.

Those became doctrine rulings, ids `D-01` to `D-14`. A ruling binds every
section. Where a section disagrees with a ruling, the ruling wins and the
section changes, and the section cites the ruling id where it applies it.

D-01 is the one worth reading first. The run manifest carried wall-clock time
and machine identity into the first event of every log, so the byte-identical
guarantee failed on its own first event and the cross-platform gate failed by
construction. The ruling splits the manifest into a hashed core and a provenance
sidecar, and a named unit test asserts the carve-out so it cannot regress
quietly.

| Enforced by                                                             | Where                       |
| ----------------------------------------------------------------------- | --------------------------- |
| `test_no_event_reads_the_wall_clock`, over a recorded run               | `packages/twinflow-kernel/` |
| `nondeterminism-gate.sh`, refusing a wall-clock read outside the kernel | `scripts/checks/`           |

## 9. Every brick comes out alone

Each package installs by itself and drags in nothing else. A reader who wants
the grounding checker and has their own agent takes `twinflow-accuracy` and
nothing more. A reader who wants the seed derivation takes `twinflow-rng`.

This is asserted rather than intended. Every package carries a
`test_brick_isolated.py`, and an import-boundary lint holds the layering that
makes isolation possible. Doctrine D-09 fixes one owner per public symbol, so
two packages cannot both define the same name and leave a consumer guessing.

The cost is real. Shared code has to be pushed down into a package both
consumers can depend on, rather than imported sideways, and that pressure shows
up on every new module.

| Enforced by                                                     | Where               |
| --------------------------------------------------------------- | ------------------- |
| `test_brick_isolated.py`, one per package                       | `packages/*/tests/` |
| `import-boundary-gate.py` and `lint-imports`, run with no cache | `just lint`         |

## 10. The same command locally and in CI

The `justfile` is the whole task surface, and CI calls the same recipes. A green
`just check` on a laptop and a green CI run mean the same thing, because they
are the same commands over the same pinned toolchain.

Where that breaks down, it gets fixed rather than documented around. The local
lint runs the same `shellcheck` and `actionlint` versions CI runs, and the
import lint runs with `--no-cache` because a stale cache reports every contract
as kept over a tree that breaks them.

The reference runner is pinned by digest, and every job carries a time budget in
`ci_budget.yaml`. A job that gets slower has to say so.

| Enforced by                                                          | Where                 |
| -------------------------------------------------------------------- | --------------------- |
| `ci-matrix-gate.py`, holding the workflow matrix to the declared set | `scripts/checks/`     |
| `just ci`, running the container-free set in CI order                | `scripts/ci-local.sh` |

## 11. An escape hatch states its reason

Every lint rule here can be escaped on a single line, and the escape names the
rule it sets aside. The prose gate goes further and refuses an escape carrying no
reason, because a gate that is easy to silence is not a gate. The nondeterminism
gate and the ruff suppressions read the token and not the reason, so the rule
holds by review there rather than by the linter.

```text
docs-lint-ok DIFF-01 quotes the narration this rule rejects
```

The reason is what makes the escape reviewable. A reviewer reading a diff sees
the rule that was set aside and the argument for setting it aside, in the line
where it happened, rather than finding out later that a file quietly stopped
being checked.

Files exempt from their own gates are listed rather than special-cased in code.
`docs/style/banned-phrases.yml` holds the phrases the rules reject, so it is
exempt from every rule. Section 5a of the documentation standard records each
exemption with the reason it exists.

| Enforced by                                                                 | Where                          |
| --------------------------------------------------------------------------- | ------------------------------ |
| The escape parser, failing an escape whose reason is under three characters | `scripts/checks/prose-gate.py` |

## 12. What this method costs

The method has a price, and a reader judging the repository should see it stated
rather than discover it.

It front-loads. Phase P0 produced five installable packages, a running gate set,
and no product. A reader who wants to see a warehouse running finds
contracts instead, and the argument for that ordering is section 3 above rather
than anything visible on screen.

It produces more planning than code early on. The design specification is
fourteen sections and the roadmap holds every milestone with its dependencies,
which is a large surface to keep true. The roadmap tool exists because keeping
it true by hand stopped being possible.

It is slow per change. A commit passes the prose gate, the spelling gate, the
banned-terms gate, the import-boundary lint, the nondeterminism gate, and the
roadmap gate before it lands. Some of those catch a real defect once a month
rather than once a day.

The bet is that the cost is paid once per rule and the benefit is paid on every
later change. That bet is falsifiable, and the phase table is where it gets
settled.
