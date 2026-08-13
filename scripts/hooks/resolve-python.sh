#!/bin/sh
# Resolve the Python interpreter the git hooks run their gates with.
#
# Sourced rather than executed. It sets two variables in the caller:
#
#   HOOK_PY        for a gate that imports only the standard library
#   HOOK_PY_YAML   for a gate that imports PyYAML, which the prose and
#                  spelling gates do to read their rules out of docs/style/
#
# WHY THE VIRTUALENV COMES FIRST
# ------------------------------
# Startup, measured on the reference checkout, medians of five:
#
#   .venv interpreter                                145 ms
#   uv run --quiet --no-project python               643 ms
#   uv run --quiet --no-project --with pyyaml python 792 ms
#
# A commit runs six of these, so the difference is 5110 ms against 1389 ms of
# wall clock, three runs each with no overlap. A hook a contributor waits
# through is a hook they learn to pass --no-verify.
#
# Nothing is given up for it. `--no-project` already syncs nothing, so the uv
# path is a launcher rather than an environment check, and a stale virtualenv
# was equally stale before. `just install` is what refreshes it, and CI builds
# one from the lockfile on every run.
#
# WHY THIS FILE EXISTS RATHER THAN THE SAME BLOCK IN BOTH HOOKS
# -------------------------------------------------------------
# pre-commit and commit-msg both need it, and two copies drift. The gates
# already read their type sets and rule lists from one place for the same
# reason.

# HOOK_PY and HOOK_PY_YAML are read by the hooks that source this file, so the
# use is not visible from here.
# shellcheck disable=SC2034
HOOK_PY=""
HOOK_PY_YAML=""

# bin/ on Unix, Scripts/ on Windows. Testing both costs nothing and keeps the
# hook working in either checkout.
for _hook_venv in .venv/bin/python .venv/Scripts/python.exe; do
  if [ -x "$_hook_venv" ]; then
    HOOK_PY="$_hook_venv"
    HOOK_PY_YAML="$_hook_venv"
    break
  fi
done

if [ -z "$HOOK_PY" ]; then
  if command -v uv >/dev/null 2>&1; then
    HOOK_PY="uv run --quiet --no-project python"
    HOOK_PY_YAML="uv run --quiet --no-project --with pyyaml python"
  else
    for _hook_candidate in python3 python; do
      if command -v "$_hook_candidate" >/dev/null 2>&1; then
        HOOK_PY="$_hook_candidate"
        HOOK_PY_YAML="$_hook_candidate"
        break
      fi
    done
  fi
elif ! "$HOOK_PY" -c "import yaml" >/dev/null 2>&1; then
  # A virtualenv exists and does not carry PyYAML, which happens on a partial
  # install. The stdlib gates still run from it; the two that need PyYAML get
  # it from uv, or say what is missing rather than failing on an import.
  if command -v uv >/dev/null 2>&1; then
    HOOK_PY_YAML="uv run --quiet --no-project --with pyyaml python"
  else
    HOOK_PY_YAML=""
  fi
fi

unset _hook_venv _hook_candidate 2>/dev/null || true
