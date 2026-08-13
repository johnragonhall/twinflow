---
title: Testing policy
description: The rule that a fix ships with the test that catches it, the procedure that makes such a test valid, and the gate that enforces the rule.
topic_type: task
audience: contributors
---

# Testing policy

[testing-strategy.md](testing-strategy.md) covers which kind of test a change
needs. This page covers the one case that has a rule rather than a choice: a
change that fixes a bug.

## Contents

1. [The rule](#1-the-rule)
2. [Writing a regression test](#2-writing-a-regression-test)
3. [What the gate checks, and what it cannot](#3-what-the-gate-checks-and-what-it-cannot)
4. [The exemption](#4-the-exemption)
5. [Where the rule runs](#5-where-the-rule-runs)

## 1. The rule

A commit whose type is `fix` touches at least one test file.

A fix without a test is a fix that holds until somebody refactors past it. The
defect leaves the tree, and nothing left in the tree remembers it was ever
there. The next person to touch that code cannot tell which behavior was paid
for and which is incidental. The test is the memory.

This follows from doctrine D-12, which
[testing-strategy.md](testing-strategy.md) section 1 states: a test that cannot
fail is not a test. A regression test is the cheapest test that satisfies it.
The input that makes it fail is known before the test is written, because it is
the defect.

## 2. Writing a regression test

The order matters, and it is the whole procedure.

1. **Reproduce the defect as an assertion.** Write the test against the code as
   it stands, before any fix.
2. **Watch it fail.** Run it. A regression test that has never been seen red is
   a test whose relationship to the defect is a guess.
3. **Read the failure.** It has to fail for the reason the bug exists, not
   because of a typo in the fixture. These look identical in a summary line.
4. **Fix the code.**
5. **Watch it pass**, and run the rest of the tier to see what else moved.

Step 2 is the step that gets skipped, and skipping it is how a test that
asserts nothing reaches the suite. A test written after the fix passes on its
first run. A first run that passes proves only that the code and the test agree
today.

Name the test for the defect rather than the function. `test_a_script_does_not
_answer_for_itself` says what broke. `test_check_reached` says where somebody
was standing when they found it.

Put a `Regression.` line in the docstring, then what the defect was. A future
reader deleting a test needs to know what it bought. This one is real:

```python
def test_a_bool_is_a_business_field_not_a_continuous_one():
    """Regression. `True` must never be compared under a tolerance.

    A bool subclasses int, so the guard that matters is that neither reaches
    the float branch. Asserted against behavior rather than against the
    isinstance chain, so a rewrite of that chain is still held to it.
    """
```

Assert against behavior, not against the shape of the fix. A test that asserts
the isinstance chain has three branches breaks when somebody rewrites the chain
correctly. A test that asserts a bool is compared exactly survives the rewrite
and still catches the defect.

Pick the tier by the test's runtime, not by where the bug lived. A bug in a slow
integration path can often be pinned by a fast unit test. That test then runs
on every commit rather than nightly.

## 3. What the gate checks, and what it cannot

`scripts/checks/regression-test-gate.py` is REG-001. It checks that a `fix`
commit touches a test file. That is the mechanical half.

It cannot check that the test reproduces the defect. Nothing mechanical can
read a test and decide whether it would have failed against code that no longer
exists. Step 2 above is the part a human does, and section 3 of
[code-review.md](code-review.md) is where a reviewer asks for it.

So the gate is a floor rather than a proof. It catches the fix that shipped
with no test at all, which is the common case. It does not catch a test that
passes against the unfixed code, which is the case review exists for.

The gate reads its type set from `scripts/hooks/commit-msg` rather than keeping
a copy, the same way CC-001 does. Two copies drift, and then a commit the hook
accepted fails the gate that runs after it.

## 4. The exemption

Some fixes carry no test that could fail. A dead link in a document, a workflow
that does not parse, a typo in a comment. Those pass by writing a trailer:

```text
fix(docs): point the license link at the file it names

Regression-Test: none - a dead link has no runtime behavior to assert on
```

The reason is required and has to be at least twenty characters. A trailer with
an empty reason is a trailer that excuses itself.

It is a trailer rather than a list of exempt scopes. A scope list decides in
advance that a whole category owes nothing, and `fix(ci)` covers both a typo
and a workflow that silently skipped a job. The trailer puts the reason in the
log beside the commit it excuses, where review reads it.

## 5. Where the rule runs

| Where                  | Range                    | Blocks                               |
| ---------------------- | ------------------------ | ------------------------------------ |
| `commit-msg` hook      | the commit being written | the commit                           |
| `lint.yml`             | `v0.1.0..HEAD`           | the branch and the pull request      |
| `just gate regression` | `v0.1.0..HEAD`           | the phase exit                       |
| `--selftest`           | nine cases               | a change that breaks the gate itself |

The range starts at `v0.1.0`, which is 17 commits before the gate landed. The
tag is a boundary rather than the moment the rule became readable. A handful of
fixes in that gap are held to a rule their author could not have read.

That is deliberate, and it is cheap. Every fix since the tag already carries a
test, checked by `test_the_shipped_history_satisfies_the_gate` rather than
asserted here. Starting earlier would judge history written before any of this
existed. Moving the boundary later would weaken a range the tree already
passes.

The selftest is there because a gate has to be seen failing. It runs nine
cases, and two of them expect a finding. A gate whose failing path nobody
exercises is indistinguishable from a gate that cannot fail, which is the
defect doctrine D-12 names.
