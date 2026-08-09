---
title: Documentation standard
description: The writing rules every document in this repository follows, which standard governs which document type, and how CI enforces it.
topic_type: reference
audience: contributors
---

# Documentation standard

Every document in this repository conforms to a named standard. This page says which
standard applies where, what each one requires, and which parts CI checks
automatically.

Documentation is part of the deliverable. A statistical engine validated against
published references, described in prose that contradicts itself, is not finished work.

## 1. The standards in force

| Standard                | Status                                    | What it governs here                                    |
| ----------------------- | ----------------------------------------- | ------------------------------------------------------- |
| ISO/IEC/IEEE 26514:2022 | Current. Replaces ISO/IEC 26514:2008      | Structure, content, and format of information for users |
| ISO/IEC/IEEE 26511:2018 | Current                                   | How documentation work is managed and scheduled         |
| ISO/IEC/IEEE 26512:2018 | Current                                   | Acquirer and supplier requirements for information      |
| ISO/IEC/IEEE 26515:2018 | Current                                   | Producing documentation inside an agile cycle           |
| IEEE 1063-2001          | Withdrawn, superseded by the 2651x series | Retained for its minimum content checklist only         |
| DITA 1.3                | OASIS standard                            | Topic typing, short descriptions, reuse discipline      |
| ASD-STE100 Issue 9      | Released 15 January 2025                  | Controlled language for procedural and reference topics |

IEEE 1063 appears because the source requirements name it. It is withdrawn and the
2651x series supersedes it, so this repository treats 26514:2022 as authoritative and
keeps IEEE 1063 only as a content checklist. Recording that supersession is itself part
of the standard: a repository that cites a withdrawn standard as current has not read it.

## 2. Topic typing

Every document is one DITA topic type. Mixing types in one file is the most common
structural defect in software documentation, and it is what makes a page impossible to
maintain and impossible to reuse.

| Type      | Answers                                     | Verb mood  | Examples in this repo                                     |
| --------- | ------------------------------------------- | ---------- | --------------------------------------------------------- |
| Concept   | What is this, and why does it work this way | Indicative | ARCHITECTURE.md, ADOPTION.md                              |
| Task      | How do I do this                            | Imperative | CONFIGURING.md, CONTRIBUTING.md, quickstarts              |
| Reference | What are the exact values                   | Indicative | Sensor catalog, event schemas, API reference, config keys |

A concept topic does not contain numbered steps. A task topic does not contain
architectural rationale. Where a task needs rationale, it links to the concept topic.

Three documents are deliberately exempt because they serve a different job:
README.md, ROADMAP.md, and CHANGELOG.md. Section 6 covers them.

## 3. Front matter

Every document under `docs/` and every top-level Markdown file carries YAML front
matter. The `description` field is the DITA short description: one sentence, stating
what the topic covers, readable on its own in a search result or a navigation panel.

```yaml
---
title: Sensor catalog
description: Every implemented sensor type, its signal model, its failure modes, and the UNS topic it publishes to.
topic_type: reference
audience: contributors
---
```

Rules for `description`:

- One sentence. No trailing fragment after a semicolon.
- It states what the reader gets. It does not restate the title.
- Between 10 and 30 words.
- It is not a marketing sentence.

Descriptions are required in three other places:

- The GitHub repository description.
- Every package `pyproject.toml` `description` field.
- Every `just` recipe, as a comment directly above it.

CI fails when any of these is missing or when a `description` merely repeats its title.

## 4. Controlled language: where ASD-STE100 applies

ASD-STE100 was written for aircraft maintenance manuals. Its purpose is to make a
procedure unambiguous for a reader whose first language is not English, under time
pressure, with safety consequences. Applied to a page whose job is to explain an
architectural tradeoff, it produces prose that reads like a machine wrote it.

So the standard is scoped by topic type rather than applied flat.

### 4.1 Full STE profile: task and reference topics

Task and reference topics follow ASD-STE100 Issue 9 writing rules. The rules that bite
most often:

- One instruction per sentence.
- Instructional sentences stay at or under 20 words. Descriptive sentences stay at or
  under 25 words.
- Descriptive paragraphs stay at or under 6 sentences.
- Use the active voice. Name the actor.
- Use simple present, simple past, or simple future. Do not use perfect or progressive
  tenses.
- Do not use a gerund or a present participle except inside an established technical
  name.
- Keep the article. Write "the control chart", not "control chart".
- One word carries one meaning, and one meaning takes one word. Do not vary vocabulary
  for style.
- Use a technical noun or a technical verb only when it names something in this system.
- Write sequential actions as separate numbered steps, never as one sentence joined by
  "and then".

Issue 9 carries 53 writing rules, roughly 900 approved words, and roughly 1200
non-approved words with suggested replacements. The full dictionary is not vendored
here. The repository maintains `docs/style/ste-terms.yml`, a project word list holding
the approved technical nouns and technical verbs this system defines, plus the
non-approved words CI rejects with their replacements.

### 4.2 Relaxed CNL profile: concept topics and the README

Concept topics and the README follow a controlled natural language profile that keeps
the parts of STE that improve clarity and drops the parts that would flatten an
argument:

Kept: active voice, one meaning per word, the article rule, sentence length ceilings,
no undefined jargon, no ambiguous pronoun reference.

Dropped: the approved word list, the gerund ban, the one-instruction-per-sentence rule.

A concept topic still has to argue. An argument needs subordinate clauses.

## 5. Editorial rules

These apply to every document with no exception, including the README, and CI enforces
the mechanical ones.

Mechanical, checked by CI:

- No em dash or en dash. Use a comma, a colon, a period, or restructure the sentence.
- No curly quotation marks or curly apostrophes.
- No emoji.
- No title case in headings. Sentence case only.
- No AI attribution, no "generated with" line, no robot emoji.
- No bold-header vertical lists, where each bullet opens with a bold phrase and a colon.

Judgment, checked in review:

- No significance inflation. Cut "plays a crucial role", "stands as a testament",
  "marks a pivotal moment", "underscores the importance of".
- No promotional adjectives. Cut "vibrant", "seamless", "robust", "powerful",
  "comprehensive", "cutting-edge", "state-of-the-art".
- No superficial participle tails. Cut clauses that open with "highlighting",
  "showcasing", "ensuring", "reflecting", "fostering" and add no information.
- No vague attribution. "Experts argue" and "industry reports suggest" are banned. Name
  the source or delete the claim.
- No rule of three for its own sake. Two items are usually the honest count.
- No negative parallelism. Write the positive claim instead of "not just X, but Y".
- No filler openers. Cut "It is important to note that", "In order to", "At this point
  in time".
- No signposting. Do not announce what the section will do. Do the thing.
- No fragmented header. A heading followed by a one-line restatement of the heading is
  padding.
- No generic upbeat conclusion.
- No diff narration outside CHANGELOG.md and migration guides. Documentation describes
  the system as it is, not as it changed. A sentence about code that no longer exists is
  dead weight.
- No hedging stack. "may potentially possibly" states nothing.
- Prefer "is" and "has" over "serves as", "stands as", "boasts", "features".

## 5a. Files exempt from their own gates

`docs/style/banned-phrases.yml` and `docs/style/ste-terms.yml` are exempt from every gate
in this document, because they hold the words the gates reject.

There is no spelling-variant gate. Contributors write in whichever English they write in,
and the linter does not have an opinion about it.

## 6. The three exempt documents

**README.md** must hold a reader who spends 90 seconds and then decide whether they
install anything. It follows the relaxed CNL profile and every mechanical anti-slop
rule, and it may open with a pitch sentence. It may not carry an unmeasured number.
Section 7 covers that.

**ROADMAP.md** is a backlog. Entries are noun phrases with dependencies, not prose.

**CHANGELOG.md** is version-scoped by definition, so the diff-narration ban does not
apply. It follows Keep a Changelog and is written by the post-commit hook, never by
hand.

## 7. The unmeasured number rule

No document states a quantitative result that the repository has not produced.

Every metric that is not yet measured appears as an explicit marker:

```
<!--METRIC:agent_eval_accuracy-->TBD<!--/METRIC-->
```

CI counts unfilled markers. An unfilled marker never blocks a normal build, because the
repository is public from Phase 1 and most numbers arrive later. An unfilled marker does
block a tagged release.

This rule exists because the README is the artifact that decides whether a reader
trusts anything else in the repository. One invented number costs more than every
honest one earns.

## 8. Structure required by ISO/IEC/IEEE 26514

Every user-facing document provides, or links to, the following. The list is the IEEE
1063 minimum content checklist, which 26514 carries forward.

- Identification: title, version, and the software version it describes.
- Scope statement: what the document covers and who it is for.
- Access to information: a table of contents for any document over one screen, and
  working cross-references.
- Concept of operations: what the software does, before how to operate it.
- Procedures: preconditions, steps, and the result of each procedure.
- Software commands: exact syntax, parameters, and defaults.
- Error messages and known problems: the message text, its cause, and the recovery
  action.
- Related information: links to the concept topics behind each task.

Any document over one screen carries a table of contents. Any procedure states its
preconditions before its first step. Any error the software emits is documented with its
recovery action, because an error message with no documented recovery is an unfinished
feature.

## 9. Enforcement

| Gate                         | Runs                    | Scope            |
| ---------------------------- | ----------------------- | ---------------- |
| `scripts/hooks/pre-commit`   | Local, on commit        | Staged files     |
| `scripts/ci-local.sh`        | Local, on demand        | Whole repository |
| `.github/workflows/lint.yml` | GitHub Actions, on push | Whole repository |

`scripts/checks/prose-gate.py` implements the mechanical checks:

1. Dash and quote characters.
2. Emoji.
3. Front matter present, with a `description` that is one sentence, 10 to 30 words, and
   not a restatement of the title.
4. Heading case.
5. Sentence length ceilings, applied by topic type.
6. Banned phrases from `docs/style/banned-phrases.yml`.
7. Non-approved words from `docs/style/ste-terms.yml`, in task and reference topics
   only, reported with the approved replacement.
8. Unfilled metric markers, counted always, fatal only on a release tag.
9. Bold-header vertical lists.
10. Title case in headings.

Every check accepts a per-line escape token, `docs-lint-ok`, followed by the rule number
and a reason. An escape without a reason fails. Escapes are reviewed on their own,
because a gate that is easy to silence stops being a gate.

## 10. Applying this to an existing document

1. Decide the topic type. Split the file if it holds more than one.
2. Add the front matter, and write the description last, once the topic is settled.
3. Run `uv run --with pyyaml python scripts/checks/prose-gate.py <file>`.
4. Fix the mechanical findings.
5. Read the file aloud. Anything you would not say to a colleague is slop, whether or
   not a linter caught it.
