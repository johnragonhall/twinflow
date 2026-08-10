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

# Prove a stream reproduces from a seed, in the four forms available before
# there is a scenario to run end to end. Budget: 3 minutes.
#
# scripts/determinism-check.sh is not called here: it reports SKIP while no
# scenario file exists, so a recipe built on it would be a recipe that proves
# nothing. It returns as a line below when Phase 0b lands SCN-F1.
determinism:
    uv run pytest packages/twinflow-rng/tests/test_derive.py -q
    uv run pytest packages/twinflow-rng/tests/test_rng_known_answers.py -q
    uv run python tools/gen_rng_kat.py --check
    just det-hashseed
    uv run pytest -m property -q

# Types over the whole workspace. ty is the type checker of record.
typecheck:
    uvx ty check

# The fast gates only: ruff check, ruff format, prose, nondeterminism. ci runs the rest.
lint:
    uv run ruff check .
    uv run ruff format --check .
    uv run python scripts/checks/prose-gate.py --all
    uv run python scripts/checks/workspace-members-gate.py
    uv run python scripts/checks/import-boundary-gate.py
    uv run python tools/gen_importlinter.py --check
    uv run python tools/gen_schemas.py --check
    uv run python scripts/checks/license-allowlist-gate.py
    # --no-cache is not optional. A stale .import_linter_cache reports every
    # contract as KEPT over a tree that breaks them.
    uv run lint-imports --no-cache
    sh scripts/checks/nondeterminism-gate.sh --selftest
    sh scripts/checks/nondeterminism-gate.sh --all

# The behavioural half of TWF-RNG-002. Budget: 20 seconds.
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
