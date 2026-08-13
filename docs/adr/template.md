---
title: Decision record template
description: The section structure every numbered decision record in this directory follows, with the question each section answers.
topic_type: concept
audience: contributors
---

# Decision record template

Copy this file to `NNNN-short-title-in-kebab-case.md`, take the next unused
number, and fill in every section. Delete nothing: a section with no content
means the decision is not ready to accept.

The structure is the four-part form Michael Nygard published in 2011, with a
consequences section that separates what the decision buys from what it costs.

---

## Front matter

```yaml
---
title: ADR-NNNN Short title stating the decision
description: One sentence, 10 to 30 words, saying what was decided and what it rules out.
topic_type: concept
audience: contributors
---
```

## Status

One of `proposed`, `accepted`, `superseded`, or `deprecated`, followed by the
date in `YYYY-MM-DD` form.

A superseded record names the record that replaced it. A record that supersedes
an earlier one names the earlier one. Both directions are written, so a reader
arriving at either end finds the other.

## Context

What is true that forces a decision. Constraints, obligations already taken on,
and the thing that stops the obvious answer from working.

Write what was known when the decision was made. A reader a year from now needs
to judge whether the reasoning still holds, and that is only possible when the
inputs are on the page.

State facts, not preferences. Where a fact comes from a source, name the source
in the sentence that uses it. Where a number appears, it comes from a recorded
run or from a published reference, per section 1 of ENGINEERING.md.

## Decision

The choice, in one paragraph, in the active voice. Name the thing chosen and the
version or edition where one applies.

## Alternatives considered

Every option a competent engineer would reach for, and the reason each one lost.
An alternatives section holding only weak options is an argument nobody will
believe.

| Alternative | Why it lost |
| ----------- | ----------- |
|             |             |

## Consequences

What this buys, and what it costs. Both are required.

The cost section is the one that earns the record its place. A decision with no
stated cost has not been examined, and the reader who inherits it will find the
cost on their own schedule rather than on yours.

Name any obligation the decision creates: a license term to keep, a gate that
must keep passing, a compatibility promise, or a dependency that now needs
watching.

## Validation

How somebody checks that the decision is still being honored. Name the gate, the
test, or the lint that holds it. Where nothing holds it, say so plainly, because
an unenforced decision drifts.
