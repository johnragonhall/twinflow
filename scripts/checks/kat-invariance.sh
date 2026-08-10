#!/bin/sh
# Known-answer invariance across the declared numpy pin range.
#
# The frozen vectors in packages/twinflow-rng/tests/test_derive.py are the only
# values in this project read from an implementation rather than quoted from a
# publisher. That is acceptable only because they are fixed by composing three
# published algorithms -- BLAKE2b, numpy's SeedSequence mixing, and PCG64DXSM --
# rather than by a numpy release. This is the check that keeps that true.
#
# A divergence between versions means numpy broke the stream stability its own
# compatibility policy commits to. That is a decision for the owner, never a
# value to refresh: a known-answer test whose expected value is regenerated from
# the implementation it tests asserts nothing.
#
# Each version runs in a throwaway environment, so the workspace venv is not
# touched. Python is pinned because the older numpy releases in the range
# publish no wheels for the newest interpreters.
#
# Usage: sh scripts/checks/kat-invariance.sh

set -eu

PYTHON_VERSION="${PYTHON_VERSION:-3.12}"
EXPECTED="[5611998823145079523, 4040095332396109674, 474682057325833967, 5149392380048760938]"

DRAW="from twinflow.rng import generator_for
g = generator_for('twinflow.selftest', base_seed=0)
print([int(g.bit_generator.random_raw()) for _ in range(4)])"

status=0

for version in 2.1.0 2.2.0 2.3.0; do
  printf 'numpy %s: ' "$version"
  actual=$(uv run --no-project --quiet \
    --python "$PYTHON_VERSION" \
    --with "numpy==$version" \
    --with-editable packages/twinflow-rng \
    python -c "$DRAW" 2>/dev/null) || {
    printf 'FAILED to run\n'
    status=1
    continue
  }

  if [ "$actual" = "$EXPECTED" ]; then
    printf 'match\n'
  else
    printf 'DIVERGED\n  expected %s\n  actual   %s\n' "$EXPECTED" "$actual"
    status=1
  fi
done

if [ "$status" -eq 0 ]; then
  printf '\n[kat] the frozen vector is identical across the declared pin range\n'
else
  printf '\n[kat] BLOCKED: the frozen vector is not invariant across the pin range\n' >&2
  printf '[kat] do not refresh the expected values; decide what changed first\n' >&2
fi

exit "$status"
