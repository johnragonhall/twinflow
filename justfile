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

# Types over the whole workspace. ty is the type checker of record.
typecheck:
    uvx ty check

# Every gate the pre-commit hook runs, over the whole tree.
lint:
    uv run ruff check .
    uv run ruff format --check .
    uv run --no-project --with pyyaml python scripts/checks/prose-gate.py --all
    sh scripts/checks/nondeterminism-gate.sh --all

# Format what can be formatted.
fmt:
    uv run ruff format .
    uv run ruff check --fix .
