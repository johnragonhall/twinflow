# Single task entry point. CI calls these same recipes, so a green local run
# and a green CI run mean the same thing.

# List every recipe with its description.
default:
    @just --list

# Install the workspace and its dev dependencies.
install:
    uv sync

# Fast unit tier. Budget: 60 seconds.
test:
    uv run pytest -m "not slow and not integration and not property"

# Property invariants. Budget: 5 minutes.
test-property:
    uv run pytest -m property

# DET-001: two runs of SCN-F1 at one seed produce byte-identical logs, plus the
# four stream-level forms that say which part of the machinery moved when they
# do not. Budget: 3 minutes.
#
# --strict rather than the default, so a missing entry point is a failure. The
# script reported SKIP while there was no scenario to run, and a recipe built on
# a skip is a recipe that proves nothing.
determinism:
    uv run pytest packages/twinflow-rng/tests/test_derive.py -q
    uv run pytest packages/twinflow-rng/tests/test_rng_known_answers.py -q
    uv run python tools/gen_rng_kat.py --check
    just det-hashseed
    uv run pytest -m property -q
    sh scripts/determinism-check.sh --strict --runs 2

# The end-to-end tier: the scenario runs, its log satisfies the envelope
# invariants, and the comparison tool agrees with itself. Budget: 12 minutes.
test-e2e:
    uv run pytest packages/twinflow-kernel/tests/test_scenario.py tests/test_compare_runs.py -q
    sh scripts/determinism-check.sh --strict --runs 3

# Write one run of SCN-F1 to a file, which is what the cross-platform legs
# upload for DET-002 to compare.
#
#   just record-run out.jsonl 0
record-run out seed="0":
    uv run python -m twinflow.kernel simulate --seed {{seed}} > {{out}}

# Step 1 of the release ritual, and the thing a contributor runs before pushing:
# every gate that does not need a container, in the order that fails fastest.
check:
    just lint
    just typecheck
    just test

# Types over the whole workspace. ty is the type checker of record.
typecheck:
    uvx ty check

# The fast gates only: ruff check, ruff format, prose, nondeterminism. ci runs the rest.
lint:
    uv run ruff check .
    uv run ruff format --check .
    uv run python scripts/checks/prose-gate.py --all
    uv run python scripts/checks/spelling-gate.py --selftest
    uv run python scripts/checks/spelling-gate.py --all
    uv run python scripts/checks/workspace-members-gate.py
    uv run python scripts/checks/import-boundary-gate.py
    uv run python tools/gen_importlinter.py --check
    uv run python tools/gen_schemas.py --check
    uv run python scripts/checks/license-allowlist-gate.py
    uv run python scripts/checks/license-bytes-gate.py
    uv run python scripts/checks/ci-matrix-gate.py
    uv run python scripts/checks/banned-terms-gate.py --selftest
    uv run python scripts/checks/banned-terms-gate.py --all
    # --no-cache is not optional. A stale .import_linter_cache reports every
    # contract as KEPT over a tree that breaks them.
    uv run lint-imports --no-cache
    sh scripts/checks/nondeterminism-gate.sh --selftest
    sh scripts/checks/nondeterminism-gate.sh --all
    just roadmap-gate
    # The two checks the hosted lint workflow also runs. Both ship a binary on
    # PyPI, so uvx reaches them with no package manager, and a workflow that
    # does not parse fails here rather than on push.
    uvx --from shellcheck-py shellcheck $(sh scripts/checks/shell-files.sh)
    uvx --with shellcheck-py --from actionlint-py actionlint
    just actions-audit

# The roadmap, as data. Without a subcommand it validates, proves coverage, and
# lints the phase diagram, which is the RMAP-001 set minus the tracker half.
#
#   just roadmap                 validate, coverage, graph-lint
#   just roadmap validate        one of them
#   just roadmap coverage --quotes
#   just roadmap drift           needs gh; reports what it skipped without it
#   just roadmap render          write docs/gates.md from gates.yaml
#   just roadmap render --check  fail when a generated document is stale
#   just roadmap sync            print the tracker plan and change nothing
#   just roadmap sync --apply    perform it from a checkout
roadmap *args:
    #!/usr/bin/env sh
    set -eu
    # {{args}} rather than "$@": just does not pass a recipe's arguments to the
    # shebang script it writes, so $# is always zero here and every invocation
    # would take the no-argument branch.
    if [ -z '{{args}}' ]; then
        uv run twinflow-roadmap validate
        uv run twinflow-roadmap coverage
        uv run twinflow-roadmap graph-lint
    else
        uv run twinflow-roadmap {{args}}
    fi

# The gate runner. `just gate phase-exit` runs every gate in force at the open
# phase, and a named phase overrides it.
#
#   just gate phase-exit          the open phase
#   just gate phase-exit P1       one named phase
#   just gate phase-exit P1 --list
#
# A gate in the set that is not implemented fails the run rather than being
# skipped, because the registry already promised it at the phase it starts at.
gate subcommand="phase-exit" *args:
    #!/usr/bin/env sh
    set -eu
    case '{{subcommand}}' in
        phase-exit) uv run python scripts/checks/phase-exit-gate.py {{args}} ;;
        *) echo "unknown gate subcommand: {{subcommand}}. Known: phase-exit" >&2; exit 2 ;;
    esac

# RMAP-001. The three offline commands plus the offline half of drift, which is
# what a checkout with no tracker credentials can prove.
roadmap-gate:
    uv run twinflow-roadmap validate
    uv run twinflow-roadmap coverage
    uv run twinflow-roadmap graph-lint
    uv run twinflow-roadmap render --check
    uv run twinflow-roadmap drift --offline

# REL-001 for a tag about to be cut. Without a version it checks the
# unreleased section only, which is what CI runs on every push.
release-check version="":
    uv run python scripts/checks/release-gate.py {{version}}

# The behavioral half of TWF-RNG-002. Budget: 20 seconds.
det-hashseed:
    sh tools/det-hashseed.sh

# The cross-language known-answer corpus, regenerated in memory and diffed.
kat-check:
    uv run python tools/gen_rng_kat.py --check

# The frozen vector against every numpy in the declared pin range. Budget: 3 minutes.
kat-invariance:
    sh scripts/checks/kat-invariance.sh

# Format what can be formatted.
fmt:
    uv run ruff format .
    uv run ruff check --fix .

# The fast local CI battery: lint, format, unit tests.
ci:
    sh scripts/ci-local.sh

# The full local CI battery: audits, secret scan, SBOM, every test tier.
ci-full:
    sh scripts/ci-local.sh --full

# Serve the docs site, with mkdocs-material and pymdown-extensions passed in.
docs:
    uv run --with mkdocs-material --with pymdown-extensions mkdocs serve

# Build the docs site the way CI publishes it.
#
# --strict is what makes this a check rather than a render. Without it mkdocs
# prints a warning for a link that resolves nowhere and exits zero, so a site
# with broken navigation publishes green.
docs-build:
    uv run --with mkdocs-material --with pymdown-extensions mkdocs build --strict

# Coverage over the unit tier, reported and never asserted.
#
# No threshold. A coverage floor is a number somebody chose, and this project
# ships no number it did not measure. The report is published so the figure is
# visible and moves under review; a gate on it arrives when there is a measured
# basis for one.
coverage:
    uv run pytest -m "not slow and not integration and not property" --cov=twinflow --cov=twinflow_roadmap --cov-report=term-missing --cov-report=xml

# Static security analysis of the workflows themselves.
#
# actionlint reads a workflow for syntax; this reads it for security. A
# workflow is executable code holding write permissions, and it is the part of
# this repository an attacker reaches without cloning it.
actions-audit:
    uvx zizmor --config .github/zizmor.yml .github/workflows/

# Mutation testing over the gate scripts.
#
# The stated bar in this repository is that a gate nobody has seen fail may be
# passing because it cannot fail. Every test here argues that by hand; this
# argues it mechanically, by perturbing the source and failing when the suite
# still passes. Budget: slow, so it is not in `just check`.
mutants:
    uvx mutmut run --paths-to-mutate tools/roadmap/src/twinflow_roadmap
