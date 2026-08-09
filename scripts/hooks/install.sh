#!/bin/sh
# Install the tracked git hooks into .git/hooks. Run once per clone:
#
#   sh scripts/hooks/install.sh
#
# This copies the hooks rather than setting core.hooksPath, deliberately.
# core.hooksPath replaces the whole hook directory, which would silently
# disable any machine-local hook already sitting in .git/hooks. Copying leaves
# those in place. The cost is that you re-run this after a hook changes.
set -eu

repo_root=$(git rev-parse --show-toplevel)
src="$repo_root/scripts/hooks"
dst="$repo_root/.git/hooks"

mkdir -p "$dst"

# Everything in scripts/hooks/ is a hook except this installer. Iterating over
# the directory rather than a hardcoded list means a machine-local hook dropped
# in here gets installed too, and a hook absent from this clone is simply
# skipped instead of failing the install.
for path in "$src"/*; do
  [ -f "$path" ] || continue
  hook=$(basename "$path")
  [ "$hook" = "install.sh" ] && continue
  cp "$path" "$dst/$hook"
  chmod +x "$dst/$hook"
  echo "installed: .git/hooks/$hook"
done

# The gate scripts the hooks call are run from the working tree, not copied.
chmod +x "$repo_root"/scripts/*.sh "$repo_root"/scripts/checks/* 2>/dev/null || true

cat <<'MSG'

What the hooks do:
  pre-commit    prose and nondeterminism gates, plus ruff, markdownlint,
                shellcheck, and actionlint, on staged files only
  commit-msg    conventional subject, ASCII subject, ALL-CAPS body headings
  post-commit   folds the CHANGELOG entry into the commit just made

Bypass:
  LINT_OK=1 git commit ...           skip the pre-commit lint gates only
  NO_CHANGELOG_SYNC=1 git commit ... skip the changelog amend for one commit
  git commit --no-verify ...         skip every hook

Re-run this script after pulling a change to scripts/hooks/.
MSG
