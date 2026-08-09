#!/bin/sh
# Determinism check: run one scenario twice and compare the hash of what it
# emitted. Two identical runs must produce byte-identical output, because every
# clock read, random draw, network call, and storage write goes through an
# injected port that the simulation seeds and controls.
#
#   sh scripts/determinism-check.sh              # 2 runs
#   sh scripts/determinism-check.sh --runs 5     # 5 runs
#   sh scripts/determinism-check.sh --strict     # fail if the entry point is absent
#
# Overridable so the check does not have to be edited when the CLI shape moves:
#   TWINFLOW_SIM_CMD       command that runs a scenario and writes the ledger
#                          to stdout (default below)
#   TWINFLOW_SIM_SCENARIO  scenario file passed to it
#
# Until the kernel and its CLI land, this reports SKIP and exits 0 so it can sit
# in CI from day one. Pass --strict (as CI does once the entry point exists) to
# turn a missing entry point into a failure.
set -u

RUNS=2
STRICT=0
while [ $# -gt 0 ]; do
  case "$1" in
    --runs)   RUNS="$2"; shift 2 ;;
    --strict) STRICT=1; shift ;;
    *) echo "usage: $0 [--runs N] [--strict]" >&2; exit 2 ;;
  esac
done

root=$(git rev-parse --show-toplevel 2>/dev/null) || exit 0
cd "$root" || exit 0

SIM_CMD="${TWINFLOW_SIM_CMD:-uv run python -m twinflow.cli simulate}"
SCENARIO="${TWINFLOW_SIM_SCENARIO:-scenarios/determinism-smoke.yaml}"

skip_or_fail() {
  if [ "$STRICT" = "1" ]; then
    printf '\033[31mFAIL\033[0m determinism check: %s\n' "$1" >&2
    exit 1
  fi
  printf '\033[33mSKIP\033[0m determinism check: %s\n' "$1"
  exit 0
}

[ -f "$SCENARIO" ] || skip_or_fail "scenario not found at $SCENARIO"
# shellcheck disable=SC2086
$SIM_CMD --help >/dev/null 2>&1 || skip_or_fail "entry point not runnable ($SIM_CMD)"

hash_of() {
  if command -v sha256sum >/dev/null 2>&1; then
    sha256sum | cut -d' ' -f1
  elif command -v shasum >/dev/null 2>&1; then
    shasum -a 256 | cut -d' ' -f1
  else
    echo "no sha256 tool available" >&2
    exit 1
  fi
}

first=""
i=1
while [ "$i" -le "$RUNS" ]; do
  # shellcheck disable=SC2086
  h=$($SIM_CMD --scenario "$SCENARIO" --seed 0 | hash_of) || {
    printf '\033[31mFAIL\033[0m determinism check: run %s errored\n' "$i" >&2
    exit 1
  }
  echo "  run $i: $h"
  if [ -z "$first" ]; then
    first="$h"
  elif [ "$h" != "$first" ]; then
    cat >&2 <<MSG

FAIL: run $i produced $h, run 1 produced $first.

Two runs of the same scenario at the same seed diverged, so something read
state the simulation does not control: a wall clock, an unseeded RNG, a real
socket, iteration over an unordered set, or a hash seed. Bisect by narrowing
the scenario, then route the offending call through its injected port.
MSG
    exit 1
  fi
  i=$((i + 1))
done

printf '\033[32mPASS\033[0m determinism check: %s runs, identical output (%s)\n' "$RUNS" "$first"
