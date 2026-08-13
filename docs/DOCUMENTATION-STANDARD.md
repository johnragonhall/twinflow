---
title: Documentation standard
description: The writing rules every document in this repository follows, which standard governs which document type, and how CI enforces it.
topic_type: reference
audience: contributors
---

# Documentation standard

Every document in this repository conforms to a named standard. This page says
which standard applies where, what each one asks for, and which parts CI checks
without a human.

Documentation is part of the deliverable. A statistical engine validated against
published references, described in prose that contradicts itself, is not
finished work.

## 1. The standards in force

The `Status` column below was read from the issuing body on 2026-08-09. Section
12 records each locator and its HTTP status. A repository that cites a
withdrawn standard as current has not read it, so the withdrawn rows stay
visible rather than being quietly dropped.

| Standard                | Status on 2026-08-09                               | What it governs here                                      |
|-------------------------|----------------------------------------------------|-----------------------------------------------------------|
| ISO/IEC/IEEE 26514:2022 | Published, edition 1, 2022-01                      | Structure, content, and format of information for users   |
| ISO/IEC 26514:2008      | Withdrawn. ISO names 26514:2022 as the new version | Nothing. Recorded because it is what 26514:2022 replaced  |
| ISO/IEC/IEEE 26511:2018 | Published, edition 2, 2018-12                      | How documentation work is managed and scheduled           |
| ISO/IEC/IEEE 26512:2026 | Published, edition 3, 2026-08                      | Acquirer and supplier requirements for information        |
| ISO/IEC/IEEE 26512:2018 | Withdrawn, stage 95.99, revised by 26512:2026      | Nothing. Recorded because the source requirements name it |
| ISO/IEC/IEEE 26515:2018 | Published, edition 2, 2018-12                      | Producing documentation inside an agile cycle             |
| IEEE 1063-2001          | Superseded Standard, in IEEE SA's own wording      | Retained for the minimum content checklist in section 8   |
| DITA 1.3                | OASIS Standard, approved 17 December 2015          | Topic typing, short descriptions, reuse discipline        |
| ASD-STE100 Issue 9      | Current issue, dated 15 January 2025               | Controlled language for procedural and reference topics   |

Three of those rows record a supersession, and each one changes what this
repository treats as authoritative.

ISO/IEC 26514:2008 is withdrawn, and the ISO catalog entry names
ISO/IEC/IEEE 26514:2022 as its replacement. This repository treats the 2022
edition as authoritative for document structure.

ISO/IEC/IEEE 26512:2018 is withdrawn at stage 95.99 and was revised by
ISO/IEC/IEEE 26512:2026. The source requirements for this project name the 2018
edition. The requirement is unchanged, and the edition in force is the 2026 one.

IEEE 1063-2001 carries the status "Superseded Standard" on its own IEEE SA
page. That page does not name what superseded it. This repository keeps IEEE
1063 only as the origin of the content checklist in section 8, and treats
26514:2022 as the standard in force.

## 2. Topic typing

Every document is one DITA topic type. Mixing types in one file is the most
common structural defect in software documentation. It is also what makes a
page impossible to maintain and impossible to reuse.

DITA 1.3 defines concept, reference, and task as topic types in Part 2, the
Technical Content Edition, at sections 2.7.1.1 through 2.7.1.4. The `shortdesc`
element that section 3 of this page uses is defined in the same part, at
section 3.2.1.6.

| Type      | Answers                                     | Verb mood  | Examples in this repo                               |
|-----------|---------------------------------------------|------------|-----------------------------------------------------|
| Concept   | What is this, and why does it work this way | Indicative | ARCHITECTURE.md, SECURITY.md, CODE_OF_CONDUCT.md    |
| Task      | How do I do this                            | Imperative | CONTRIBUTING.md, quickstarts                        |
| Reference | What are the exact values                   | Indicative | Sensor catalog, event schemas, CLA.md, LICENSING.md |

A concept topic does not contain numbered steps. A task topic does not contain
architectural rationale. Where a task needs rationale, it links to the concept
topic.

Four documents are exempt, because each serves a job the typing does not fit.
Section 5a lists them, next to three files that are exempt for a different
reason.

## 3. Front matter

Every document under `docs/`, and every top-level Markdown file, carries YAML
front matter. The exceptions are the four files in section 5a. The
`description` field is the DITA short description. It is one sentence, it
states what the topic covers, and it reads on its own in a search result or a
navigation panel.

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
- It states what the reader gets. It does not open with the title text.
- Between 10 and 30 words.
- It is not a marketing sentence.

Three other places carry a description, and none of them is machine-checked
today:

- The GitHub repository description.
- Every package `pyproject.toml` `description` field.
- Every `just` recipe, as a comment directly above it.

A reviewer checks those three. The prose gate reads front matter only, and
section 9 names the three fields it checks for presence.

## 4. Controlled language: where ASD-STE100 applies

ASD-STE100 was written for aircraft maintenance manuals. Its purpose is to make
a procedure unambiguous for a reader whose first language is not English, under
time pressure, with safety consequences. Applied to a page whose job is to
explain an architectural tradeoff, it produces prose that reads like a machine
wrote it.

So the standard is scoped by topic type rather than applied flat.

### 4.1 What ASD-STE100 itself publishes

The ASD Simplified Technical English Maintenance Group publishes four points on
its public pages. This repository builds on those four, rather than on the
dictionary, which is not vendored here:

- The standard is a set of writing rules in Part 1 and a dictionary of
  controlled vocabulary in Part 2.
- The writing rules cover grammar and style, and the dictionary fixes the
  general words a writer can use.
- In general there is one word for one meaning, and one part of speech for one
  word.
- A project may declare its own technical names and technical verbs, and use
  them alongside the dictionary.

The fourth point is what `docs/style/ste-terms.yml` exists for. It holds the
technical nouns and technical verbs this system defines. It also holds the
non-approved general words that show up often enough here to fail on, each with
its replacement.

The dictionary is copyright ASD and is not reproduced here. Get a free official
copy from <https://www.asd-ste100.org/>.

### 4.2 Full profile: task and reference topics

Task and reference topics take the four ASD-STE100 principles above, plus these
project rules:

- One instruction per sentence.
- Instructional sentences stay at or under 20 words. Descriptive sentences stay
  at or under 25 words.
- Descriptive paragraphs stay at or under 6 sentences.
- Use the active voice. Name the actor.
- Use simple present, simple past, or simple future.
- Keep the article. Write "the control chart", not "control chart".
- Do not vary vocabulary for style.
- Use a technical noun or a technical verb only when it names something in this
  system.
- Write sequential actions as separate numbered steps.

The numeric ceilings in that list are this repository's own values, not
quotations from Issue 9. They live in the `sentence_limits` block of
`docs/style/banned-phrases.yml`, which is the single place to change them.
Section 11 records what remains unverified about Issue 9.

One published ASD-STE100 rule is deliberately not adopted. The STEMG states
that STE picks American spelling where American and British forms differ. This
repository has no spelling-variant gate, for the reason in section 5a.

### 4.3 Relaxed profile: concept topics and the README

Concept topics and the README keep the parts of the full profile that improve
clarity, and drop the parts that would flatten an argument:

Kept: active voice, one meaning per word, the article rule, sentence length
ceilings, no undefined jargon, no ambiguous pronoun reference.

Dropped: the project word list, the one-instruction-per-sentence rule.

A concept topic still has to argue. An argument needs subordinate clauses. The
sentence ceiling is looser to match: 35 words and 8 sentences, against 25 and 6
for the full profile.

## 5. Editorial rules

These apply to every document, including the README. Section 9 says which ones
block a build and which ones only print.

Mechanical, and a build-blocking error:

- No em dash or en dash. Use a comma, a colon, a period, or restructure the
  sentence.
- No curly quotation marks or curly apostrophes.
- No emoji.
- No AI attribution, no "generated with" line, no robot emoji.
- No bold-header vertical lists, where each bullet opens with a bold phrase and
  a colon.

Mechanical, and a warning that prints without blocking:

- No title case in headings. Sentence case only. This one warns rather than
  blocks, because a proper noun is indistinguishable from title case to a
  regular expression.
- The sentence and paragraph ceilings in section 4.

Judgment, checked in review:

- No significance inflation. Cut "plays a crucial role", "stands as a
  testament", "marks a pivotal moment", "underscores the importance of".
- No promotional adjectives. Cut "vibrant", "seamless", "robust", "powerful",
  "comprehensive", "cutting-edge", "state-of-the-art".
- No superficial participle tails. Cut clauses that open with "highlighting",
  "showcasing", "ensuring", "reflecting", "fostering" and add no information.
- No vague attribution. "Experts argue" and "industry reports suggest" are
  banned. Name the source or delete the claim.
- No rule of three for its own sake. Two items are usually the honest count.
- No negative parallelism. Write the positive claim instead of "not just X, but
  Y".
- No filler openers. Cut "It is important to note that", "In order to", "At
  this point in time".
- No signposting. Do not announce what the section will do. Do the thing.
- No fragmented header. A heading followed by a one-line restatement of the
  heading is padding.
- No generic upbeat conclusion.
- No diff narration outside CHANGELOG.md and migration guides. Documentation
  describes the system as it is, not as it changed.
- No hedging stack. "may potentially possibly" states nothing.
- Prefer "is" and "has" over "serves as", "stands as", "boasts", "features".

Many of the judgment rules above also carry a regular expression in
`docs/style/banned-phrases.yml`. A regular expression catches the stock phrasing
and misses the paraphrase. So the rule is listed as judgment, and the pattern is
a net rather than the definition.

## 5a. Files exempt from their own gates

| File                               | Exempt from                              | Reason                                                                                                |
|------------------------------------|------------------------------------------|-------------------------------------------------------------------------------------------------------|
| `docs/style/banned-phrases.yml`    | Every rule                               | It holds the phrases the rules reject                                                                 |
| `docs/style/ste-terms.yml`         | Every rule                               | It holds the words the rules reject                                                                   |
| `docs/DOCUMENTATION-STANDARD.md`   | The prose rules, not the character rules | It quotes the phrases it bans. Dashes, curly quotes, and emoji still fail here                        |
| `README.md`                        | Front matter and sentence ceilings       | Section 6                                                                                             |
| `ROADMAP.md`                       | Front matter and sentence ceilings       | Section 6                                                                                             |
| `CHANGELOG.md`                     | Front matter and sentence ceilings       | Section 6                                                                                             |
| `.github/PULL_REQUEST_TEMPLATE.md` | Front matter and sentence ceilings       | GitHub copies the file verbatim into every pull request body, where front matter would appear as text |

There is no spelling-variant gate. Contributors write in whichever English they
write in, and the linter has no opinion about it. Section 4.2 records that this
departs from ASD-STE100.

## 6. The four exempt documents

README.md must hold a reader who spends 90 seconds and then decides whether to
install anything. It follows the relaxed profile and every mechanical
anti-slop rule, and it may open with a pitch sentence. It may not carry an
unmeasured number. Section 7 covers that.

ROADMAP.md is a backlog. Entries are noun phrases with dependencies, not prose.

CHANGELOG.md is version-scoped by definition, so the diff-narration ban does
not apply. It follows Keep a Changelog and is written by the post-commit hook,
except for the three headings that hook never writes.

`.github/PULL_REQUEST_TEMPLATE.md` is copied into a pull request body by
GitHub, not rendered as a page. Front matter in it would show up as text in
every pull request.

## 7. The unmeasured number rule

No document states a quantitative result that the repository has not produced.

Every metric that is not yet measured appears as an explicit marker:

```text
<!--METRIC:agent_eval_accuracy@v0.3.0-->TBD<!--/METRIC-->
```

A marker may name the tag its number arrives at, and is then owed from that tag
onward:

```text
<!--METRIC:agent_eval_accuracy@v0.3.0-->TBD<!--/METRIC-->
```

`scripts/checks/metric-marker-gate.sh` counts unfilled markers. An unfilled
marker never blocks a normal build, because the repository is public from Phase
1 and most numbers arrive with the subsystem that measures them. At a tagged
release, where the gate runs as `--release <version>`, a marker that release
owes blocks it and a marker naming a later tag is reported as deferred. A
marker naming no tag is owed by every release, which is the strict reading and
the default.

This rule exists because the README is the artifact that decides whether a
reader trusts anything else in the repository. One invented number costs more
than every honest one earns.

## 8. Minimum content

Every user-facing document gives, or links to, each item below.

- Identification: title, version, and the software version it describes.
- Scope statement: what the document covers and who it is for.
- Access to information: a table of contents for any document over one screen,
  and working cross-references.
- Concept of operations: what the software does, before how to operate it.
- Procedures: preconditions, steps, and the result of each procedure.
- Software commands: exact syntax, parameters, and defaults.
- Error messages and known problems: the message text, its cause, and the
  recovery action.
- Related information: links to the concept topics behind each task.

That list came into this repository as the IEEE 1063 minimum content checklist.
The full texts of IEEE 1063-2001 and ISO/IEC/IEEE 26514:2022 are sold, not
published. No clause of either is quoted here, and no item above is a quotation. Section 11 records the mapping as an open question. The list
binds this repository on its own authority either way.

Any document over one screen carries a table of contents. Any procedure states
its preconditions before its first step. Any error the software emits is
documented with its recovery action, because an error message with no
documented recovery is an unfinished feature.

## 9. Enforcement

| Gate                         | Runs                    | Scope            |
|------------------------------|-------------------------|------------------|
| `scripts/hooks/pre-commit`   | Local, on commit        | Staged files     |
| `scripts/ci-local.sh`        | Local, on demand        | Whole repository |
| `.github/workflows/lint.yml` | GitHub Actions, on push | Whole repository |

`scripts/checks/prose-gate.py` reads every rule it applies from
`docs/style/banned-phrases.yml` and `docs/style/ste-terms.yml`. It applies four
families of check, and nothing else.

| Family              | Rule ids                | Severity                          | Where it applies                                                                           |
|---------------------|-------------------------|-----------------------------------|--------------------------------------------------------------------------------------------|
| Regular expressions | As given in the YAML    | The `severity` field of each rule | Markdown only, unless the rule sets `applies_to: all` or its pattern holds no ASCII letter |
| Front matter        | `FM-01` through `FM-05` | Error                             | Markdown, minus the files in section 5a                                                    |
| Heading case        | `HEAD-01`               | Warning                           | Markdown                                                                                   |
| Sentence length     | `LEN-01`, `LEN-02`      | Warning                           | Markdown, minus the files in section 5a                                                    |

The project word list arrives as a fifth family that is compiled into the same
shape as the regular expressions. A word under `non_approved` becomes an error
carrying rule id `STE-TERM-WORD`. A synonym rejected by a declared technical
noun or verb becomes a warning carrying `STE-TERM-SYN`. A word like "issue" is
wrong only when it names the declared concept. Both apply to task and
reference topics only, and neither fires inside a string listed under
`protected_terms`.

What the front matter family checks, exactly:

| Rule    | Fails when                                                  |
|---------|-------------------------------------------------------------|
| `FM-01` | The file has no YAML front matter block                     |
| `FM-02` | `title`, `description`, or `topic_type` is missing or empty |
| `FM-03` | The description is under 10 words or over 30                |
| `FM-04` | The description is more than one sentence                   |
| `FM-05` | The description begins with the title text                  |

`audience` is required by section 3 of this page and is not checked by
`FM-02`. A reviewer catches a missing `audience`.

Two rules that section 5 lists as mechanical do not live in this script.

Unfilled metric markers are counted by
`scripts/checks/metric-marker-gate.sh`, which also catches a malformed marker
and two markers sharing a name with different values. Section 7 covers it.

The bold-header vertical list is rule `LIST-01` in
`docs/style/banned-phrases.yml`, so it arrives through the regular expression
family rather than as a check of its own.

Three behaviors of the script bound what a clean run proves:

1. Without PyYAML the script prints a skip line and exits 0. The Lint workflow
   installs PyYAML, so the repo-wide run is the one that counts.
2. `--all` reads `git ls-files`, so an untracked file is not checked. Pass the
   path explicitly to check a file before its first commit.
3. `--strict` promotes every warning to an error. Nothing in CI passes it
   today.

Every check accepts a per-line escape token:

```text
docs-lint-ok <RULE-ID> <reason>
```

The rule id must match the finding's rule id, or be `*` for any rule. The
reason must be at least 3 characters. An escape with no reason is itself an
error. Escapes are reviewed on their own, because a gate that is easy to
silence stops being a gate.

The front matter family is the one exception. It consults no escape token, so a
file that cannot carry front matter belongs in section 5a.

## 10. Applying this to an existing document

1. Decide the topic type. Split the file if it holds more than one.
2. Add the front matter, and write the description last, once the topic is settled.
3. Run `uv run --no-project --with pyyaml python scripts/checks/prose-gate.py <file>`.
4. Fix the mechanical findings.
5. Read the file aloud. Anything you would not say to a colleague is slop.

Step 3 names the file explicitly on purpose. A new file is untracked, and
`--all` would skip it.

## 11. Open questions

These are recorded rather than asserted, because the primary text is sold and
was not read.

- ASD-STE100 Issue 9 is widely described as carrying 53 writing rules, roughly
  900 approved words, and roughly 1200 non-approved words. None of those three
  counts appears on the public STEMG pages, and the standard itself is supplied
  only on request. Until a copy is read, no count is stated in this repository
  as fact, and no rule of Issue 9 is cited here by number.
- Whether each item in section 8 maps to a numbered clause of IEEE 1063-2001,
  and whether ISO/IEC/IEEE 26514:2022 carries each one forward, is unverified.
  Both texts are sold.
- IEEE SA gives IEEE 1063-2001 the status "Superseded Standard" without naming
  the superseding document. That the 2651x series is what superseded it is a
  reasonable reading and is not confirmed by the source.
- ISO/IEC/IEEE 26512 was revised in 2026. Whether 26511:2018 and 26515:2018
  have revisions in progress was not checked.

## 12. Sources

Every locator below was retrieved on 2026-08-09 with `curl`, and each returned
HTTP 200.

| Claim                                                       | Locator                                                                                                 |
|-------------------------------------------------------------|---------------------------------------------------------------------------------------------------------|
| ISO/IEC/IEEE 26514:2022 published, edition 1, 2022-01       | <https://www.iso.org/standard/77451.html>                                                               |
| ISO/IEC 26514:2008 withdrawn, replaced by 26514:2022        | <https://www.iso.org/standard/43073.html>                                                               |
| ISO/IEC/IEEE 26511:2018 published, edition 2, 2018-12       | <https://www.iso.org/standard/70879.html>                                                               |
| ISO/IEC/IEEE 26512:2018 withdrawn at stage 95.99            | <https://www.iso.org/standard/72088.html>                                                               |
| ISO/IEC/IEEE 26512:2026 published, edition 3, 2026-08       | <https://www.iso.org/standard/91114.html>                                                               |
| ISO/IEC/IEEE 26515:2018 published, edition 2, 2018-12       | <https://www.iso.org/standard/70880.html>                                                               |
| IEEE 1063-2001 status "Superseded Standard"                 | <https://standards.ieee.org/standard/1063-2001.html>                                                    |
| DITA 1.3 OASIS Standard, 17 December 2015, topic types      | <https://docs.oasis-open.org/dita/dita/v1.3/os/part2-tech-content/dita-v1.3-os-part2-tech-content.html> |
| ASD-STE100 Issue 9 dated 15 January 2025                    | <https://www.asd-ste100.org/>                                                                           |
| ASD-STE100 structure, one word one meaning, technical names | <https://www.asd-ste100.org/about.html>                                                                 |
| Keep a Changelog change types, used by CHANGELOG.md         | <https://keepachangelog.com/en/1.1.0/>                                                                  |

One caution about the last two ASD-STE100 rows. On the retrieval date the
`about.html` page still named Issue 8 of April 2021 as current. The site home
page named Issue 9 of 15 January 2025. The structural description is taken
from `about.html` and the issue date from the home page.
