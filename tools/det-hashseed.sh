#!/bin/sh
# The behavioral half of TWF-RNG-002, and the Phase 0a form of gate DET-3.
#
# CPython randomizes string hashing per process unless PYTHONHASHSEED is fixed,
# so a set whose iteration order reaches a hash produces a different digest
# under a different seed. The lint catches the syntactic case at authoring
# time; this catches the ones a static pattern cannot see.
#
#   sh tools/det-hashseed.sh
set -eu

root=$(git rev-parse --show-toplevel)
cd "$root"

a=$(PYTHONHASHSEED=0 uv run python tools/rng_digest.py)
b=$(PYTHONHASHSEED=12345 uv run python tools/rng_digest.py)

if [ "$a" != "$b" ]; then
  printf '\033[31mFAIL\033[0m TWF-RNG-002 behavioral check\n' >&2
  printf '  PYTHONHASHSEED=0     %s\n' "$a" >&2
  printf '  PYTHONHASHSEED=12345 %s\n' "$b" >&2
  printf '\nA collection whose iteration order depends on string hashing reached\n' >&2
  printf 'the digest. Sort at the iteration site with an explicit total key.\n' >&2
  exit 1
fi

printf '\033[32mPASS\033[0m TWF-RNG-002 behavioral check: %s\n' "$a"
