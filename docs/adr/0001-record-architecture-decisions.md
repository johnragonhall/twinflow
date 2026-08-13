---
title: ADR-0001 Record architecture decisions
description: Keeps three decision registers rather than one, and fixes the citation rule that keeps the technology and doctrine ids apart.
topic_type: concept
audience: contributors
---

# ADR-0001 Record architecture decisions

## Status

`accepted`, 2026-08-13.

## Context

Two decision registers existed before this record, and both are load-bearing.

Section 1 of ARCHITECTURE.md carries sixteen technology decisions, `D1` to
`D16`, each with its rejected alternatives and its reason. DOCTRINE.md carries
fourteen cross-cutting rulings, `D-01` to `D-14`, each written because the same
defect appeared in three or more design sections.

They record different things. A technology decision picks a tool. A doctrine
ruling settles a question that more than one design section answered
differently, and it binds every section thereafter. Neither register is a
superset of the other.

The ids are one hyphen apart. `D1` and `D-01` are unrelated decisions, and a
reader who has met only one register reads a bare `D1` as whichever they know.
Fourteen design sections, ROADMAP.md, and `gates.yaml` all cite these ids.

Neither register has room for a decision that fits neither shape. Choosing to
keep a decision log at all, choosing a review policy, and choosing how a release
is cut are architecturally significant, hard to reverse, and belong to no design
section.

Section 1 of ROADMAP.md fixes the rule that a recorded id never changes.
Renumbering either register to remove the ambiguity would break every existing
citation and would contradict that rule.

## Decision

Keep three registers. The technology decision record and the doctrine stay where
they are and keep their ids. A third register, numbered `ADR-0001` onward, lives
in `docs/adr/` and takes any architecturally significant decision that fits
neither of the first two.

Every citation names its register: "decision D1" for the first, "doctrine D-01"
or "ruling D-01" for the second. A bare id is not a citation.

Records use the Nygard four-part form, extended with an alternatives table and a
validation section. An accepted record is never edited. A decision that changes
gets a new record, and both records point at each other.

## Alternatives considered

| Alternative                                                         | Why it lost                                                                                                                                                                               |
| ------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| One register: move all thirty decisions into `docs/adr/`            | It puts a second copy of every decision in the tree while the originals stay cited from fourteen sections, and a second copy is the drift that section 6 of ENGINEERING.md exists to stop |
| Renumber the doctrine to `DOC-01`, or the technology set to `TDR-1` | It breaks every citation in the design sections, the roadmap, the gate registry, and the commit history, to buy one hyphen of clarity                                                     |
| Keep two registers and force new decisions into one of them         | A review policy is not a technology choice and binds no design section, so it would land in whichever register it fit least badly                                                         |
| Keep no numbered register and write decisions into commit messages  | A commit message is not findable by a reader who does not already know the change exists, and it cannot record a status that later changes                                                |

## Consequences

What this buys: a decision taken after v0.1.0 has a home, a reader can tell the
three registers apart by id shape alone, and no existing citation moves. The
immutability rule keeps the reasoning as evidence of what was known at the time,
rather than as a rolling summary of current opinion.

What it costs: three registers is more surface than one, and a contributor has
to pick the right one. Section 3 of the index is the test that makes that
mechanical, and picking wrong is recoverable, because a record can be superseded
by one in the correct register.

The ambiguity between `D1` and `D-01` is reduced by a citation convention rather
than removed by renumbering. A citation that omits the register is still
ambiguous, and nothing mechanical catches it today.

## Validation

The index in `docs/adr/index.md` lists every numbered record with its status,
and a record missing from that table is the defect this section names.

The citation convention is checked in review, not by a gate. A lint that
distinguished a bare `D1` from the `D1` inside a table cell in ARCHITECTURE.md
would need context a regular expression does not carry, and section 11 of
ENGINEERING.md records what happens to a rule contributors learn to escape.
