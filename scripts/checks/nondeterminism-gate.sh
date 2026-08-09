#!/bin/sh
# Nondeterminism gate. Blocks direct wall-clock, RNG, and socket calls in any
# Python file outside the kernel adapter package.
#
#   sh scripts/checks/nondeterminism-gate.sh            # staged files (git hook)
#   sh scripts/checks/nondeterminism-gate.sh --all      # every tracked file (CI)
#
# Why this rule exists
# --------------------
# twinflow is written against injected clock, RNG, network, and storage
# interfaces so that one codebase runs two ways: as real containers talking to
# real services, and as a single-process deterministic simulation that replays
# a scenario bit for bit. A stray wall-clock read or an unseeded random draw
# does not fail loudly. It silently makes a run unreproducible, which is the
# one property the whole design exists to provide. So the check is mechanical
# and fatal rather than a review convention.
#
# The kernel package is where the real adapters live, so it is the one place
# these calls are legitimate. Every other module takes the port as a parameter.
#
# Escape hatch: annotate the line with the token  nondeterminism-ok  plus a
# reason. Use it for build scripts and one-shot developer tools that sit
# outside the simulated world, not for production paths.
set -u

MODE="${1:---staged}"
root=$(git rev-parse --show-toplevel 2>/dev/null) || exit 0
cd "$root" || exit 0

# Path prefix holding the real adapter implementations. Update this if the
# package layout moves the kernel elsewhere.
KERNEL_PATH_RE='(^|/)twinflow/kernel/'

# Banned call sites. The leading class is a hand-rolled word boundary that
# still allows a dotted prefix, so datetime.datetime.now( is caught while
# datetime.time( and mytime.time( are not. It is plain POSIX ERE, so the same
# pattern works under GNU and BSD grep.
#
# The RNG alternative matches the module-level helpers (random.random,
# random.choice, random.seed, numpy.random.rand) but deliberately not
# random.Random(...): an explicitly seeded instance is how a deterministic RNG
# port gets built, and the lowercase-only class lets it through.
BANNED='(^|[^A-Za-z0-9_])(time\.time|datetime\.now|datetime\.utcnow|socket\.socket|random\.[a-z_]+)\('

case "$MODE" in
  --all)
    files=$(git ls-files '*.py')
    scope="tracked files"
    ;;
  --staged|"")
    files=$(git diff --cached --name-only --diff-filter=ACM -- '*.py')
    scope="staged files"
    ;;
  *)
    echo "usage: $0 [--staged|--all]" >&2
    exit 2
    ;;
esac

# Drop the kernel package: the adapters there are the sanctioned call sites.
files=$(printf '%s\n' "$files" | grep -vE "$KERNEL_PATH_RE" | grep -v '^[[:space:]]*$' || true)
[ -n "$files" ] || { echo "[nondeterminism] no python $scope to check"; exit 0; }

# shellcheck disable=SC2086
hits=$(grep -HnE "$BANNED" $files 2>/dev/null | grep -v 'nondeterminism-ok' || true)

if [ -n "$hits" ]; then
  printf '\n\033[31mBLOCKED: nondeterministic call sites outside the kernel package\033[0m\n' >&2
  printf '%s\n' "$hits" >&2
  cat >&2 <<'MSG'

twinflow replays a scenario bit for bit only because every module reads the
clock, draws randomness, opens sockets, and touches storage through an
injected port. A direct call here does not break a test, it quietly makes the
run unreproducible.

  Fix: take the port as a parameter and call it instead.
       clock.now()      instead of the wall clock
       rng.uniform(...)  instead of the module-level RNG helpers
       net.connect(...)  instead of opening a socket
  Real implementations belong in the kernel adapter package only.

  Genuinely outside the simulated world (a build script, a dev-only tool)?
  Annotate that line:      # nondeterminism-ok: <reason>

  Bypass every hook once:  git commit --no-verify
MSG
  exit 1
fi

echo "[nondeterminism] clean ($scope)"
exit 0
