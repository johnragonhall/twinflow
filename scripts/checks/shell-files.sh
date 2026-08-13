#!/bin/sh
# Print the tracked files that are shell scripts, one per line.
#
# One home for the list, because the hosted lint workflow and the local battery
# both hand it to shellcheck, and two globs that drift apart mean CI checks a
# file nobody checked locally.
#
# Selected by shebang rather than by name. scripts/hooks/ holds the git hooks,
# which carry no extension, beside comment_judge.py, which is Python; a glob
# over that directory hands shellcheck a Python file, and shellcheck reports a
# parse error for every docstring in it.
set -u

cd "$(git rev-parse --show-toplevel)" || exit 1

git ls-files '*.sh' 'scripts/hooks/*' | while IFS= read -r file; do
  [ -f "$file" ] || continue
  case "$file" in
    *.sh) echo "$file" ; continue ;;
  esac
  # A shebang naming a shell, on the first line. Anything else is not a shell
  # script whatever directory it sits in.
  head -n 1 "$file" | grep -Eq '^#!.*\b(sh|bash|dash|ksh|zsh)$|^#!.*\b(sh|bash|dash|ksh|zsh)[[:space:]]' \
    && echo "$file"
done
