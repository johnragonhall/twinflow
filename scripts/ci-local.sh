#!/bin/sh
# scripts/ci-local.sh - run the CI battery locally.
#
# Routine validation costs zero GitHub Actions minutes when it happens here.
# The hosted workflows stay for the badge, the pull-request gate, and the
# matrix breadth a single dev machine cannot cover.
#
# Usage:
#   sh scripts/ci-local.sh             fast gate: lint, format, unit tests
#   sh scripts/ci-local.sh --full      + audits, secret scan, SBOM, all test tiers
#   sh scripts/ci-local.sh --security  audits and scans only
#
# Every check is skipped, with a note, when its tool is not installed, so a
# partial toolchain still runs what it can. Nothing here installs anything.
set -u

MODE="${1:-fast}"
root=$(git rev-parse --show-toplevel) || exit 1
cd "$root" || exit 1

pass=0
fail=0
skip=0
failed_names=""

have() { command -v "$1" >/dev/null 2>&1; }

step() {
  # step "name" <command...>
  name=$1
  shift
  printf '\n\033[1m== %s ==\033[0m\n' "$name"
  if "$@"; then
    printf '\033[32mPASS\033[0m %s\n' "$name"
    pass=$((pass + 1))
  else
    printf '\033[31mFAIL\033[0m %s\n' "$name"
    fail=$((fail + 1))
    failed_names="$failed_names\n  - $name"
  fi
}

note_skip() {
  printf '\033[33mSKIP\033[0m %s (%s)\n' "$1" "$2"
  skip=$((skip + 1))
}

# Resolve a Python interpreter for the gate scripts. The prose gate needs
# PyYAML, and uv can supply it without touching the project environment.
PY=""
if have uv; then
  PY="uv run --quiet --no-project --with pyyaml python"
elif have python && python -c "import sys" >/dev/null 2>&1; then
  PY="python"
elif have python3 && python3 -c "import sys" >/dev/null 2>&1; then
  PY="python3"
fi

# ---------------------------------------------------------------------------
# Repo policy gates - always, pure scripts, no toolchain needed
# ---------------------------------------------------------------------------
if [ "$MODE" != "--security" ]; then
  if [ -n "$PY" ]; then
    # shellcheck disable=SC2086
    step "prose gate (repo-wide)" $PY scripts/checks/prose-gate.py --all
    # WORKSPACE-1. Needs only tomllib, so it runs on the bare interpreter.
    # shellcheck disable=SC2086
    step "workspace membership gate" $PY scripts/checks/workspace-members-gate.py
  else
    note_skip "prose gate" "no python interpreter"
    note_skip "workspace membership gate" "no python interpreter"
  fi
  step "nondeterminism gate (repo-wide)" sh scripts/checks/nondeterminism-gate.sh --all
  # Report mode: an unfilled metric marker is normal during the build and only
  # becomes fatal on a release tag, where the workflow passes --release.
  [ -f scripts/checks/metric-marker-gate.sh ] && \
    step "metric marker gate" sh scripts/checks/metric-marker-gate.sh
  step "changelog-sync selftest" sh scripts/changelog-sync.sh --selftest
fi

# ---------------------------------------------------------------------------
# Python: lint, types, tests
# ---------------------------------------------------------------------------
if [ "$MODE" != "--security" ]; then
  if have ruff; then
    step "ruff check" ruff check .
    step "ruff format --check" ruff format --check .
  elif have uvx; then
    step "ruff check" uvx ruff check .
    step "ruff format --check" uvx ruff format --check .
  else
    note_skip "ruff" "install: uv tool install ruff"
  fi

  # ty is the type checker of record; mypy is accepted as a stand-in on a
  # machine that only has mypy installed.
  #
  # Both the type check and the test run are skipped until a package exists.
  # Before then the only Python here is the gate scripts, and reporting a
  # standing FAIL for a package that has not been written yet would make the
  # whole battery permanently red. A gate nobody can turn green is a gate
  # everybody learns to ignore, which costs more than the check is worth.
  # Milestone C10 lands pyproject.toml, and both checks arm themselves the
  # moment it appears, with no edit to this file.
  if [ ! -f pyproject.toml ]; then
    note_skip "type check" "no pyproject.toml yet; arms at milestone C10"
    note_skip "pytest" "no pyproject.toml yet; arms at milestone C10"
  else
    if have ty; then
      step "ty check" ty check
    elif have uvx && uvx ty --version >/dev/null 2>&1; then
      step "ty check" uvx ty check
    elif have mypy; then
      step "mypy" mypy .
    else
      note_skip "type check" "install: uv tool install ty"
    fi

    if have uv; then
      step "pytest (fast tier)" uv run pytest -m "not slow and not integration and not property" -q
    elif have pytest; then
      step "pytest (fast tier)" pytest -m "not slow and not integration and not property" -q
    else
      note_skip "pytest" "install: uv sync"
    fi
  fi
fi

# ---------------------------------------------------------------------------
# Rust device agent
# ---------------------------------------------------------------------------
if [ "$MODE" != "--security" ]; then
  if have cargo && [ -f agent/Cargo.toml ]; then
    step "cargo fmt --check" sh -c 'cd agent && cargo fmt --check'
    step "cargo clippy" sh -c 'cd agent && cargo clippy --all-targets -- -D warnings'
    step "cargo test" sh -c 'cd agent && cargo test'
  else
    note_skip "Rust device agent" "cargo or agent/Cargo.toml not found"
  fi
fi

# ---------------------------------------------------------------------------
# Linters that CI also runs repo-wide
# ---------------------------------------------------------------------------
if [ "$MODE" != "--security" ]; then
  # Same glob as .github/workflows/lint.yml. Ignored trees are dropped by the
  # gitignore setting in .markdownlint-cli2.jsonc, not by negations here.
  if have markdownlint-cli2; then
    step "markdownlint" markdownlint-cli2 "**/*.md"
  elif have npx && npx --no-install markdownlint-cli2 --help >/dev/null 2>&1; then
    step "markdownlint" npx --no-install markdownlint-cli2 "**/*.md"
  else
    note_skip "markdownlint" "install: npm i -g markdownlint-cli2"
  fi

  if have shellcheck; then
    step "shellcheck" sh -c '
      files=$(git ls-files "*.sh" "scripts/hooks/*")
      [ -n "$files" ] || { echo "no shell scripts"; exit 0; }
      # Word splitting is the point here.
      # shellcheck disable=SC2086
      shellcheck $files'
  else
    note_skip "shellcheck" "install shellcheck from your package manager"
  fi

  if have actionlint; then
    step "actionlint" actionlint -color
  else
    note_skip "actionlint" "install actionlint from your package manager"
  fi
fi

# ---------------------------------------------------------------------------
# Heavier test tiers - --full only
# ---------------------------------------------------------------------------
if [ "$MODE" = "--full" ]; then
  step "determinism repeated-run hash check" sh scripts/determinism-check.sh --runs 3

  if have uv; then
    step "pytest (property invariants)" uv run pytest -m property -q
    step "pytest (integration tier)" uv run pytest -m integration -q
  elif have pytest; then
    step "pytest (property invariants)" pytest -m property -q
    step "pytest (integration tier)" pytest -m integration -q
  else
    note_skip "heavy test tiers" "install: uv sync"
  fi
fi

# ---------------------------------------------------------------------------
# Security, dependency audits, SBOM - --full and --security
# ---------------------------------------------------------------------------
if [ "$MODE" = "--full" ] || [ "$MODE" = "--security" ]; then
  if have pip-audit; then
    step "pip-audit" pip-audit
  elif have uvx; then
    step "pip-audit" uvx pip-audit
  else
    note_skip "pip-audit" "install: uv tool install pip-audit"
  fi

  if have cargo && cargo audit --version >/dev/null 2>&1 && [ -f agent/Cargo.toml ]; then
    step "cargo audit" sh -c 'cd agent && cargo audit'
  else
    note_skip "cargo audit" "install: cargo install cargo-audit"
  fi

  if have gitleaks; then
    step "gitleaks (secret scan)" gitleaks detect --no-banner
  else
    note_skip "gitleaks" "install gitleaks to scan for secrets locally"
  fi

  if have trufflehog; then
    step "trufflehog (verified secrets)" trufflehog filesystem . --only-verified --fail
  else
    note_skip "trufflehog" "install trufflehog for verified-secret scanning"
  fi

  if have semgrep; then
    step "semgrep (security-audit, python, secrets)" \
      semgrep scan --config p/security-audit --config p/python --config p/secrets --error --metrics=off
  else
    note_skip "semgrep" "install: uv tool install semgrep"
  fi

  # SBOM. syft covers the whole tree; the cyclonedx generators cover one
  # ecosystem each and are the fallback.
  if have syft; then
    step "SBOM (syft, cyclonedx-json)" sh -c 'syft dir:. -o cyclonedx-json > sbom.cdx.json'
  elif have uvx; then
    step "SBOM (cyclonedx-py)" sh -c 'uvx cyclonedx-py environment > sbom.cdx.json'
  else
    note_skip "SBOM" "install syft, or use: uvx cyclonedx-py"
  fi
fi

# ---------------------------------------------------------------------------
printf '\n\033[1m================ ci-local summary ================\033[0m\n'
printf 'passed: %s   failed: %s   skipped: %s\n' "$pass" "$fail" "$skip"
if [ "$fail" -ne 0 ]; then
  printf '\033[31mFAILED:%b\033[0m\n' "$failed_names"
  exit 1
fi
printf '\033[32mAll local CI checks passed.\033[0m\n'
