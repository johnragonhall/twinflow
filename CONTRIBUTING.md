---
title: Contributing
description: How to set up the toolchain, run the test tiers, pass the lint gates, and write a commit message this repository accepts.
topic_type: task
audience: contributors
---

# Contributing

Read [docs/DOCUMENTATION-STANDARD.md](docs/DOCUMENTATION-STANDARD.md) before
you write any prose. It defines topic types, front matter, and the writing
rules that CI checks.

## Setup

Run these once per clone:

```sh
sh scripts/hooks/install.sh    # install the git hooks
uv sync --all-extras --dev     # create .venv and install the toolchain
```

The `pre-commit` and `commit-msg` hooks each end with a judge. It reads the
added comments, the added prose, and the commit message. It blocks a comment
that restates its code and a bullet that narrates a change.

The judge needs the `claude` CLI and fails open without it, so no network
problem blocks a commit. Turn it off for one commit with
`COMMENT_JUDGE=0 git commit ...`.

`install.sh` copies the hooks into `.git/hooks`. It does not point
`core.hooksPath` at the tracked directory, so a machine-local hook you already
have keeps working. Run it again after a pull that touches `scripts/hooks/`.

| Hook          | What it does                                                                                          |
|---------------|-------------------------------------------------------------------------------------------------------|
| `pre-commit`  | Runs the prose, determinism, and language linters over the staged files. A finding blocks the commit. |
| `commit-msg`  | Checks the subject shape, rejects a non-ASCII subject, and checks the body headings.                  |
| `post-commit` | Writes the changelog entry and folds it into the commit you just made.                                |

A pre-commit gate whose tool is missing prints a warning and lets the commit
through. CI is the hard backstop, so a partial local toolchain slows you down
rather than shipping a finding.

Bypasses, when you have read the finding and it is wrong:

```sh
LINT_OK=1 git commit ...            # skip the pre-commit lint gates
NO_CHANGELOG_SYNC=1 git commit ...  # skip the changelog amend for one commit
git commit --no-verify ...          # skip every hook
```

## Commands

The `just` recipes wrap the commands below. Run the underlying command if you
do not have `just` installed.

| Recipe               | Runs                                                                   |
|----------------------|------------------------------------------------------------------------|
| `just`               | Lists every recipe, with its description (same as `just --list`)       |
| `just install`       | `uv sync`                                                              |
| `just test`          | The fast tier below                                                    |
| `just test-property` | The property tier below                                                |
| `just determinism`   | The determinism tier below                                             |
| `just typecheck`     | `uvx ty check`                                                         |
| `just lint`          | ruff check, ruff format check, the prose gate, the nondeterminism gate |
| `just fmt`           | `uv run ruff format .` and `uv run ruff check --fix .`                 |
| `just ci`            | `sh scripts/ci-local.sh`                                               |
| `just ci-full`       | `sh scripts/ci-local.sh --full`                                        |
| `just docs`          | `uv run --with mkdocs-material --with pymdown-extensions mkdocs serve` |

Run the whole local CI battery before every push: <!-- docs-lint-ok STE-TERM-SYN git push, not a UNS publish -->

```sh
sh scripts/ci-local.sh            # fast: lint, format, unit tests
sh scripts/ci-local.sh --full     # adds audits, secret scan, SBOM, all tiers
sh scripts/ci-local.sh --security # audits and scans only
```

Every check in that script skips itself, with a note, when its tool is absent.
Running it locally is what keeps routine validation off the hosted runners.

## Test tiers and time budgets

Each tier has a budget. A tier that drifts past its budget gets split, or moved
to a nightly run. A slow gate is a gate people learn to skip.

| Tier        | Command                                                            | Budget       |
|-------------|--------------------------------------------------------------------|--------------|
| Fast        | `uv run pytest -m "not slow and not integration and not property"` | Under 60 s   |
| Property    | `uv run pytest -m property`                                        | Under 5 min  |
| Determinism | `sh scripts/determinism-check.sh --runs 3`                         | Under 2 min  |
| Integration | `uv run pytest -m integration`                                     | Under 10 min |

The fast tier runs on every commit. The property tier runs the invariant suite
over generated inputs. The determinism tier runs one scenario several times and
compares the hash of the output. That is the check that catches a stray clock
read before it reaches a reviewer.

Write a regression test for every bug you fix, and put it in the tier that
matches its runtime rather than the tier that matches where the bug lived.

This one is enforced. `VAL-GATE-REG-001` refuses a commit whose type is `fix`
and which touches no test file, so a fix without a test does not reach the log.
Write the test first and watch it fail before you fix the code: a test written
afterwards passes on its first run, and a first run that passes proves only
that the code and the test agree today.

A fix that carries no test which could fail says so in a trailer:

```text
fix(docs): point the license link at the file it names

Regression-Test: none - a dead link has no runtime behavior to assert on
```

The reason is required and runs to at least twenty characters. It is a trailer
rather than a list of exempt scopes, because `fix(ci)` covers both a typo and a
workflow that silently skipped a job, and the trailer puts the reason in the
log beside the commit it excuses.

[docs/testing-policy.md](docs/testing-policy.md) carries the procedure and what
the gate cannot check. [docs/testing-strategy.md](docs/testing-strategy.md)
covers which of the six kinds of test a change needs.

## Linting

Two workflows share this work, and they do not cover the same ground. Read the
`Enforced by` column before you assume a green tick covers your change.

| Target      | Tool                                     | Config                     | Enforced by                                                        |
|-------------|------------------------------------------|----------------------------|--------------------------------------------------------------------|
| IP hygiene  | `scripts/checks/banned-terms-gate.py`    | `.ip-denylist`             | `pre-commit`, staged files, before either bypass is read           |
| Regression  | `scripts/checks/regression-test-gate.py` | none                       | `commit-msg`, the commit being written, and `just gate regression` |
| Commit log  | `scripts/checks/commit-message-gate.py`  | `scripts/hooks/commit-msg` | `lint.yml`, the range since the previous tag                       |
| Prose       | `scripts/checks/prose-gate.py`           | `docs/style/*.yml`         | `lint.yml`, whole tree, on every commit that reaches it            |
| Spelling    | `scripts/checks/spelling-gate.py`        | `docs/style/spelling.yml`  | `lint.yml`, whole tree, and the commit message                     |
| Determinism | `scripts/checks/nondeterminism-gate.sh`  | none                       | `lint.yml`, whole tree                                             |
| Metrics     | `scripts/checks/metric-marker-gate.sh`   | none                       | `lint.yml`, report mode, fatal only on a release tag               |
| Markdown    | `markdownlint-cli2`                      | `.markdownlint.jsonc`      | `lint.yml`, whole tree                                             |
| Shell       | `shellcheck`                             | `.shellcheckrc`            | `lint.yml`, whole tree                                             |
| Workflows   | `actionlint`                             | none                       | `lint.yml`, whole tree                                             |
| Agreement   | the `cla` job                            | `CLA.md` section 7         | `lint.yml`, pull requests only                                     |
| Python      | `ruff check`, `ruff format --check`      | `pyproject.toml`           | `ci.yml`, only when its `python` path filter matches               |
| Types       | `ty check`                               | `pyproject.toml`           | `ci.yml`, only when its `python` path filter matches               |
| Rust        | `cargo fmt`, `cargo clippy -D warnings`  | `agent/`                   | `ci.yml`, only when `agent/` changed                               |

The `python` filter in `ci.yml` covers `src/`, `tests/`, `scenarios/`,
`pyproject.toml`, `uv.lock`, and `ci.yml` itself. A Python file outside those
paths is linted by the pre-commit hook and by `scripts/ci-local.sh`, and not by
a hosted job.

The pre-commit hook runs the IP hygiene, prose, determinism, Python, Markdown,
shell, and workflow gates over the staged files. It does not run `ty`, `cargo`,
or the metric marker gate.

IP hygiene runs first and is the one gate that neither `LINT_OK=1` nor
`--no-verify` skips. The others guard style, and a style finding costs a
follow-up commit. That one guards a client name or an internal document marker
reaching a public history, which costs a history rewrite, so it runs before the
bypass is read.

The commit-msg hook runs the spelling gate, the narration judge, and the
regression gate against the message and the staged files together. It runs
there rather than in pre-commit because two of those rules read the commit
type. That type does not exist until the message does.

Markdown tables are column-aligned. markdownlint reports a misaligned table as
`MD060` and does not repair it. Re-align an edited table with
`npx prettier --write <file>`, which produces the layout `MD060` accepts.

The prose gate needs PyYAML, because it reads its rules from
`docs/style/banned-phrases.yml` and `docs/style/ste-terms.yml`. Without PyYAML
it prints a skip line and passes, and CI catches what it missed.

Both hooks pick their interpreter through `scripts/hooks/resolve-python.sh`,
which prefers the project virtualenv and falls back to `uv` and then to a bare
interpreter. The virtualenv carries PyYAML and starts in roughly a fifth of the
time `uv run` takes, which is most of what a commit waits for. Its header
carries the measurement.

Install the tools you are missing so the hook stops skipping them:

```sh
uv tool install ruff
uv tool install ty
npm i -g markdownlint-cli2
```

### The determinism gate

Every module reads the clock, draws randomness, opens sockets, and touches
storage through an injected port. That is what lets one codebase run as real
containers and as a single deterministic simulation.

So `time.time`, `datetime.now`, `datetime.utcnow`, the module-level `random`
helpers, and `socket.socket` are blocked in any Python file outside the kernel
adapter package. An explicitly seeded `random.Random(...)` instance is fine,
since that is how a deterministic RNG port gets built.

If a line sits outside the simulated world, such as a build script, annotate
it and say why:

```python
started = time.time()  # nondeterminism-ok: build timing, not simulated state
```

## Commit messages

The `commit-msg` hook checks every rule below. It also runs two covered
elsewhere on this page: the spelling gate reads the message, and
`VAL-GATE-REG-001` refuses a `fix` that touches no test.

The subject is `type(scope): description`, in ASCII, lowercase after the colon,
with no trailing period.

| Type       | Use for                               |
|------------|---------------------------------------|
| `feat`     | A new capability                      |
| `fix`      | A bug fix                             |
| `refactor` | A restructure with no behavior change |
| `test`     | Tests only                            |
| `docs`     | Documentation only                    |
| `chore`    | Build, tooling, dependency updates    |
| `perf`     | A performance change                  |

A non-ASCII subject is rejected because it corrupts the changelog entry the
`post-commit` hook copies out of it.

A commit with a body needs at least one ALL-CAPS section heading on its own
line, drawn from this list:

```text
UI  BACKEND  INFRA  DOCS  FIX  SECURITY  DEPS  TEST  FEAT  REFACTOR  PERF  CHORE
```

`TESTS` is accepted as `TEST`. Put the detail in bullets under a heading rather
than inventing a heading of your own.

```text
fix(mcp): reject oversized tool payloads

BACKEND
- cap the request body at 1 MiB and return 413 past it
TEST
- add a payload-size case to the MCP contract tests
```

Keep the subject under 72 characters. One logical change per commit.

### A bullet summarizes, it does not narrate

Write what the code **does**, in the present tense. The reader is somebody
reading `git log` a year from now who never saw the previous version, so the
previous version is not the subject.

```text
write:  - cap the request body at 1 MiB
not:    - the body used to be uncapped and now is not     docs-lint-ok DIFF-01 quotes the narration this rule rejects

write:  - the sequence starts at 0
not:    - fixed a bug where the sequence started at 1

write:  - read the version from the module
not:    - the version was written twice and now reads from the module

write:  - refuse an entity id carrying a dot
not:    - added support for entity id validation
```

"Previously", "used to", "no longer", "now reads", "changed X to Y", and "fixed
a bug where" describe the edit rather than the result. The `commit-msg` hook
rejects them.

A `TEST` section is exempt. It reports what a run measured, so `- 126 passed`
is a fact about that run rather than a narration.

A bullet naming a defect the change removes is fine when it says what the code
does. `- refuse a name that is already registered` carries the fix without
making the reader reconstruct the bug.

## Changelog automation

The `post-commit` hook maps the commit type to a Keep a Changelog heading and
writes the bullet into the `[Unreleased]` section. It then amends your commit,
so the edit lands inside it. No separate sync commit appears in the log.

| Commit type                         | Changelog heading |
|-------------------------------------|-------------------|
| `feat`                              | Added             |
| `fix`                               | Fixed             |
| `perf`                              | Changed           |
| `docs`, `chore`, `refactor`, `test` | Nothing recorded  |

The hook only ever adds. Edit the wording in `CHANGELOG.md` freely. Skip it for
one commit with `NO_CHANGELOG_SYNC=1 git commit ...`, and check the insertion
logic with `sh scripts/changelog-sync.sh --selftest`.

Do not add AI-attribution trailers to a commit. The history of this repository
is part of what it shows, and it reads as a record of the work.

## Contributor agreement

Every contributor signs [CLA.md](CLA.md) before their first pull request merges.
It grants the maintainer the license needed to offer this project under both
Apache-2.0 and the commercial terms in [LICENSING.md](LICENSING.md). You keep
your copyright, and you can reuse your own work anywhere.

Two steps, both inside your first pull request:

1. Add your line to the signatories list at the bottom of `CLA.md`.
2. Sign every commit with `git commit -s`, which writes the `Signed-off-by` trailer.

The `cla` job in `.github/workflows/lint.yml` runs on every pull request. It
reads the merge result, so the line you add in this pull request counts. It
checks three things:

1. Every list line in `CLA.md` section 8 matches the published expression.
2. A signatory line names the pull request author, matched without regard to case.
3. Every commit you added carries a `Signed-off-by` trailer.

The repository owner skips the second check, because the owner holds the
copyright and has nobody to license it to. The third check skips merge commits,
and skips commits merged in from the base branch.
[CLA.md section 7](CLA.md#7-how-to-sign) states all three carve-outs and the
expression. Read `CLA.md` in full before you sign it. It is short.

## Dependency licenses

Every dependency carries a license compatible with Apache-2.0 redistribution.
The table below is the allowlist. Read the `Applies to` column: two rows turn
on where the dependency sits, not only on its SPDX id.

| SPDX id        | Applies to          | Decision | Reason                                                                                        |
|----------------|---------------------|----------|-----------------------------------------------------------------------------------------------|
| `MIT`          | Any dependency      | Accepted | Permissive, with no condition Apache-2.0 redistribution breaks.                               |
| `BSD-2-Clause` | Any dependency      | Accepted | Permissive, same reasoning as MIT.                                                            |
| `BSD-3-Clause` | Any dependency      | Accepted | Permissive, plus a no-endorsement clause that costs nothing here.                             |
| `ISC`          | Any dependency      | Accepted | Permissive, functionally MIT.                                                                 |
| `Apache-2.0`   | Any dependency      | Accepted | The outbound license of this project.                                                         |
| `Python-2.0`   | Any dependency      | Accepted | Permissive, and unavoidable on the standard library path.                                     |
| `0BSD`         | Any dependency      | Accepted | Permissive with no attribution condition at all. Reaches the tree through numpy.              |
| `Zlib`         | Any dependency      | Accepted | Permissive, and its only condition is not misrepresenting origin. Reaches the tree via numpy. |
| `CC0-1.0`      | Any dependency      | Accepted | A public-domain dedication, so it imposes no condition on redistribution.                     |
| `MPL-2.0`      | Development only    | Accepted | Copyleft that stops at the file it covers, and a test dependency is never shipped. See below. |
| `MPL-2.0`      | Shipped at run time | Refused  | The file-level condition would travel to a user who installs a twinflow package.              |
| `GPL-2.0`      | Any dependency      | Refused  | Incompatible with Apache-2.0, and no waiver is available.                                     |
| `GPL-3.0`      | Any dependency      | Refused  | Pulls the whole work under GPL and breaks both licensing options.                             |
| `AGPL-3.0`     | Any dependency      | Refused  | Section 13 covers network interaction, and this project serves an API. See below.             |

### Why MPL-2.0 is accepted for development dependencies

Hypothesis is MPL-2.0, and requirement C4 names a property-based invariant
suite built on it. An allowlist with no MPL-2.0 row refuses a library the
specification mandates. That is a defect in the allowlist, not a reason to drop
the suite.

MPL-2.0 attaches its condition to the files it covers. It does not reach across
a package boundary the way AGPL-3.0 does. A test dependency stays in the
development extra, so nobody who installs a twinflow package receives it. Both
facts have to hold for the row to apply, which is why the row is scoped rather
than open.

### Why AGPL-3.0 is refused, and the case behind the ruling

PM4Py and `pm4pyminimal` are both AGPL-3.0 at version 2.7.23.3, read from the
Python Package Index on 2026-08-09. Section 13 of AGPL-3.0 triggers on network
interaction, and this project serves a dashboard, an MCP server, and an HTTP
API. Importing either package would put the whole work under AGPL-3.0 and break
the dual license in [LICENSING.md](LICENSING.md).

Doctrine ruling D-14 in [docs/design/DOCTRINE.md](docs/design/DOCTRINE.md)
settles it. The project writes its own process mining under Apache-2.0. PM4Py
stays available as a development-only comparison oracle, never shipped and
never served.

### How the allowlist is checked today

There is no automated license gate yet, because the repository has no
dependency manifest to resolve. Until one exists, the maintainer reads the
license of each new dependency by hand against the table above.

Milestone C11 in `ROADMAP.md` sequences the automated form: a resolver run over
the manifest on every change, with a failure on any license outside the table.
Release gate `VAL-GATE-SEC-001` names the same allowlist, including the
MPL-2.0 row.

Anything not in the table needs a decision before the dependency lands. Open a
[discussion](https://github.com/johnragonhall/twinflow/discussions) naming the
package, its SPDX id, and whether it links at run time, at build time, or only
in tests. [LICENSING.md](LICENSING.md) states the policy this table carries out.

## Governance

John Ragon Hall maintains this repository and merges every change. The rest of
this file calls that person the maintainer.

Open a GitHub issue before you start anything larger than a bug fix. <!-- docs-lint-ok STE-TERM-SYN the GitHub issue tracker, not an engine finding -->
That settles the scope before the code exists.

A roadmap addition is accepted when it names a capability, states the evidence
that the capability is worth building, and lists what it depends on. Roadmap
entries are noun phrases with dependencies, not prose. An accepted entry lands
in `ROADMAP.md`, under the earliest phase its dependencies permit.

Work a newcomer can finish in one sitting carries the `good first issue` label. <!-- docs-lint-ok STE-TERM-SYN GitHub label name -->
Work that is scoped and unclaimed carries `help wanted`. A pull request with no
linked issue still gets read, but a large one may be turned down on scope alone. <!-- docs-lint-ok STE-TERM-SYN the GitHub issue tracker, not an engine finding -->

## Security

Never open a public GitHub issue for a security finding. See <!-- docs-lint-ok STE-TERM-SYN the GitHub issue tracker, not an engine finding -->
[SECURITY.md](SECURITY.md) for the private channel and the threat model.
