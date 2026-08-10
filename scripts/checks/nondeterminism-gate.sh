#!/bin/sh
# Nondeterminism gate. Blocks direct wall-clock, RNG, and socket calls in any
# Python file outside the kernel adapter package, and enforces the three RNG
# rules of docs/design/variability-and-faults.md sections A.2 and A.4.
#
#   sh scripts/checks/nondeterminism-gate.sh            # staged files (git hook)
#   sh scripts/checks/nondeterminism-gate.sh --all      # every tracked file (CI)
#   sh scripts/checks/nondeterminism-gate.sh --selftest # prove each rule fires
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

# The one distribution allowed to construct a bit generator, per section A.4.
RNG_PATH_RE='(^|/)packages/twinflow-rng/'

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

# TWF-RNG-001. A stream is addressed by name, so a bit generator built anywhere
# else is a stream nobody registered and nobody can reproduce. Section A.4
# names SeedSequence.spawn( and a direct PCG64DXSM( construction; the other
# generators are here because switching to one of them outside the one
# distribution has the same effect. Section F.4 asks for exactly this static
# check as the companion to the stream-addition test.
RNG001='(^|[^A-Za-z0-9_])(SeedSequence|PCG64|PCG64DXSM|Philox|SFC64|MT19937)\(|\.spawn\('

# TWF-RNG-002. Set iteration order in CPython depends on hash values and
# insertion history, so a set walked by a for statement can change the tape
# between processes. The sanctioned form is sorted(...), which this pattern
# lets through because the iterable then starts with sorted rather than with
# set( or a brace. The brace alternative excludes a colon, so a dict literal
# and a dict comprehension are not matched.
RNG002='for[[:space:]][^:]*[[:space:]]in[[:space:]]+((set|frozenset)\(|\{[^:}]*\})'

# TWF-RNG-003. The legacy global RNG state is process-wide and nothing here may
# depend on it. This rule has no kernel carve-out, because seeding the global
# state inside an adapter is no safer than seeding it anywhere else.
RNG003='(^|[^A-Za-z0-9_])((numpy|np)\.random\.[a-z_]+|random\.[a-z_]+)\('

hits_total=""

# check_rule <id> <pattern> <exempt-ere-or-empty> <file...>
check_rule() {
  rule_id=$1
  pattern=$2
  exempt=$3
  shift 3
  [ $# -gt 0 ] || return 0
  scoped=$(printf '%s\n' "$@")
  if [ -n "$exempt" ]; then
    scoped=$(printf '%s\n' "$scoped" | grep -vE "$exempt" || true)
  fi
  scoped=$(printf '%s\n' "$scoped" | grep -v '^[[:space:]]*$' || true)
  [ -n "$scoped" ] || return 0
  # shellcheck disable=SC2086
  found=$(grep -HnE "$pattern" $scoped 2>/dev/null | grep -v 'nondeterminism-ok' || true)
  if [ -n "$found" ]; then
    hits_total="$hits_total$(printf '%s\n' "$found" | sed "s/^/[$rule_id] /")
"
  fi
}

# run_rules <file...>
run_rules() {
  hits_total=""
  check_rule "TWF-DET-001" "$BANNED" "$KERNEL_PATH_RE" "$@"
  check_rule "TWF-RNG-001" "$RNG001" "$RNG_PATH_RE" "$@"
  check_rule "TWF-RNG-002" "$RNG002" "" "$@"
  check_rule "TWF-RNG-003" "$RNG003" "" "$@"
}

selftest() {
  # Every rule gets a file that must trip it and a file that must not, so a
  # pattern that stops matching fails here instead of going quiet in CI.
  tmp=$(mktemp -d) || { echo "selftest: cannot create a temp directory" >&2; exit 1; }
  trap 'rm -rf "$tmp"' EXIT
  mkdir -p "$tmp/packages/twinflow-rng" "$tmp/packages/twinflow-twin"

  printf 'import time\nt = time.time()\n' > "$tmp/bad_det001.py"
  printf 'from numpy.random import PCG64DXSM\ng = PCG64DXSM(1)\n' > "$tmp/packages/twinflow-twin/bad_rng001.py"
  printf 'g = PCG64DXSM(1)\n' > "$tmp/packages/twinflow-rng/ok_rng001.py"
  printf 'for name in {"b", "a"}:\n    print(name)\n' > "$tmp/bad_rng002_literal.py"
  printf 'for name in set(names):\n    print(name)\n' > "$tmp/bad_rng002_call.py"
  printf 'for name in sorted(names):\n    print(name)\n' > "$tmp/ok_rng002.py"
  printf 'for key in {"a": 1}:\n    print(key)\n' > "$tmp/ok_rng002_dict.py"
  printf 'import numpy as np\nnp.random.seed(0)\n' > "$tmp/bad_rng003.py"
  printf 'import numpy as np\nnp.random.seed(0)  # nondeterminism-ok: selftest fixture\n' > "$tmp/ok_escape.py"

  failures=0
  # expect <fires|clean> <rule-id> <file>
  expect() {
    want=$1
    rule=$2
    target=$3
    run_rules "$target"
    got=$(printf '%s' "$hits_total" | grep -c "\[$rule\]" || true)
    if [ "$want" = "fires" ] && [ "$got" -eq 0 ]; then
      printf 'selftest FAIL: %s did not fire on %s\n' "$rule" "$target" >&2
      failures=$((failures + 1))
    fi
    if [ "$want" = "clean" ] && [ "$got" -ne 0 ]; then
      printf 'selftest FAIL: %s fired on %s, which is a sanctioned form\n' "$rule" "$target" >&2
      failures=$((failures + 1))
    fi
  }

  expect fires TWF-DET-001 "$tmp/bad_det001.py"
  expect fires TWF-RNG-001 "$tmp/packages/twinflow-twin/bad_rng001.py"
  expect clean TWF-RNG-001 "$tmp/packages/twinflow-rng/ok_rng001.py"
  expect fires TWF-RNG-002 "$tmp/bad_rng002_literal.py"
  expect fires TWF-RNG-002 "$tmp/bad_rng002_call.py"
  expect clean TWF-RNG-002 "$tmp/ok_rng002.py"
  expect clean TWF-RNG-002 "$tmp/ok_rng002_dict.py"
  expect fires TWF-RNG-003 "$tmp/bad_rng003.py"
  expect clean TWF-RNG-003 "$tmp/ok_escape.py"

  if [ "$failures" -ne 0 ]; then
    printf '\033[31m[nondeterminism] selftest failed: %s check(s)\033[0m\n' "$failures" >&2
    exit 1
  fi
  echo "[nondeterminism] selftest clean (9 checks over 4 rules)"
  exit 0
}

case "$MODE" in
  --selftest)
    selftest
    ;;
  --all)
    files=$(git ls-files '*.py')
    scope="tracked files"
    ;;
  --staged|"")
    files=$(git diff --cached --name-only --diff-filter=ACM -- '*.py')
    scope="staged files"
    ;;
  *)
    echo "usage: $0 [--staged|--all|--selftest]" >&2
    exit 2
    ;;
esac

files=$(printf '%s\n' "$files" | grep -v '^[[:space:]]*$' || true)
[ -n "$files" ] || { echo "[nondeterminism] no python $scope to check"; exit 0; }

# shellcheck disable=SC2086
run_rules $files

if [ -n "$hits_total" ]; then
  printf '\n\033[31mBLOCKED: nondeterministic call sites\033[0m\n' >&2
  printf '%s' "$hits_total" >&2
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

  TWF-RNG-001  build a generator through twinflow.rng, never a bit generator
  TWF-RNG-002  iterate sorted(...), never a set, where order reaches a hash
  TWF-RNG-003  the legacy global RNG state is banned everywhere

  Genuinely outside the simulated world (a build script, a dev-only tool)?
  Annotate that line:      # nondeterminism-ok: <reason>

  Bypass every hook once:  git commit --no-verify
MSG
  exit 1
fi

echo "[nondeterminism] clean ($scope)"
exit 0
