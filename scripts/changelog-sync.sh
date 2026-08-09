#!/bin/sh
# Insert a Conventional-Commit summary into CHANGELOG.md's [Unreleased] section.
# Called by scripts/hooks/post-commit, but runnable by hand:
#
#   sh scripts/changelog-sync.sh                        # sync from HEAD's subject
#   sh scripts/changelog-sync.sh --subject "feat: x"    # sync from a given subject
#   sh scripts/changelog-sync.sh --selftest             # run the built-in check
#
# Type to Keep a Changelog heading:
#   feat -> Added
#   fix  -> Fixed
#   perf -> Changed
# Everything else (docs, chore, refactor, test) records nothing: those commits
# do not change what a user of the project can observe.
#
# Idempotent. An entry already present under [Unreleased] is never duplicated.
set -u

FILE="CHANGELOG.md"
SUBJECT=""
selftest=0

while [ $# -gt 0 ]; do
  case "$1" in
    --file)     FILE="$2"; shift 2 ;;
    --subject)  SUBJECT="$2"; shift 2 ;;
    --selftest) selftest=1; shift ;;
    *) echo "usage: $0 [--file F] [--subject S] [--selftest]" >&2; exit 2 ;;
  esac
done

# insert <file> <commit-subject>
# Edits <file> in place when the subject is a feat/fix/perf conventional commit
# and the entry is not already recorded.
insert() {
  f="$1"; subject="$2"
  [ -f "$f" ] || return 0
  type=$(printf '%s' "$subject" | sed -nE 's/^([a-z]+)(\([^)]*\))?!?:.*/\1/p')
  desc=$(printf '%s' "$subject" | sed -E 's/^[a-z]+(\([^)]*\))?!?:[[:space:]]*//')
  [ -n "$type" ] || return 0
  case "$type" in
    feat) head="Added" ;;
    fix)  head="Fixed" ;;
    perf) head="Changed" ;;
    *) return 0 ;;
  esac
  entry="- $desc"
  grep -qF -e "$entry" "$f" && return 0
  # Insert as the first bullet under "### <head>" inside [Unreleased].
  #
  # The output has to stay markdownlint-clean in both shapes the section can
  # take. An empty section needs a blank line after the new bullet so the next
  # "###" heading is still surrounded by blanks (MD022). A section that already
  # has bullets must NOT get one, or the list turns loose (MD032). So the
  # separator is decided by looking at the line that follows the insert point,
  # which is what the two-step pending/after state below does.
  awk -v h="$head" -v e="$entry" '
    function flush(){ if (in_u && !done){ print "### " h; print ""; print e; print ""; done=1 } }
    /^## \[Unreleased\]/ { print; in_u=1; next }
    {
      if (pending) {                 # the previous line was the target heading
        pending=0; done=1
        if ($0 == "") { print ""; print e; after=1; next }
        print ""; print e; print ""; print; next
      }
      if (after) {                   # the entry just went in, pick a separator
        after=0
        if ($0 == "")        { print ""; next }   # reuse the blank already there
        if ($0 ~ /^[-*] /)   { print; next }      # tight list, no blank wanted
        print ""; print; next                     # heading or prose, needs one
      }
      if (in_u && $0 ~ /^## /)  { flush(); in_u=0 }
      if (in_u && $0 == "### " h) { print; pending=1; next }
      print
    }
    END {
      if (pending) { print ""; print e; print ""; done=1 }
      if (after)   { print "" }
      flush()
    }
  ' "$f" > "$f.tmp" && mv "$f.tmp" "$f"
}

if [ "$selftest" = "1" ]; then
  tmp=$(mktemp)
  printf '# Changelog\n\n## [Unreleased]\n\n### Added\n\n- existing\n\n## [0.1.0] - 2026-01-01\n' > "$tmp"
  insert "$tmp" "feat(kernel): add seeded rng port"
  insert "$tmp" "fix(mcp): reject oversized tool payloads"
  insert "$tmp" "perf(store): batch the delta commit"
  insert "$tmp" "refactor(api): split the router"
  insert "$tmp" "docs: rewrite the adoption guide"
  insert "$tmp" "chore(deps): bump ruff"
  insert "$tmp" "test(sim): cover the replay path"
  grep -qF -e "- add seeded rng port"          "$tmp" || { echo "FAIL: feat not added"; exit 1; }
  grep -qF -e "- reject oversized tool payloads" "$tmp" || { echo "FAIL: fix not added"; exit 1; }
  grep -qF -e "### Fixed"                      "$tmp" || { echo "FAIL: Fixed heading not created"; exit 1; }
  grep -qF -e "- batch the delta commit"       "$tmp" || { echo "FAIL: perf not added"; exit 1; }
  grep -qF -e "### Changed"                    "$tmp" || { echo "FAIL: Changed heading not created"; exit 1; }
  grep -qF -e "split the router"               "$tmp" && { echo "FAIL: refactor leaked in"; exit 1; }
  grep -qF -e "adoption guide"                 "$tmp" && { echo "FAIL: docs leaked in"; exit 1; }
  grep -qF -e "bump ruff"                      "$tmp" && { echo "FAIL: chore leaked in"; exit 1; }
  grep -qF -e "cover the replay path"          "$tmp" && { echo "FAIL: test leaked in"; exit 1; }
  insert "$tmp" "feat(kernel): add seeded rng port"   # re-run: must stay idempotent
  n=$(grep -cF -e "- add seeded rng port" "$tmp")
  [ "$n" = "1" ] || { echo "FAIL: not idempotent (count=$n)"; exit 1; }
  rm -f "$tmp"
  echo "changelog-sync selftest: OK"
  exit 0
fi

# Read the subject as UTF-8 regardless of the platform's log output encoding,
# so a non-ASCII byte cannot land mangled in CHANGELOG.md.
if [ -z "$SUBJECT" ]; then
  SUBJECT=$(git -c i18n.logOutputEncoding=UTF-8 log -1 --format=%s 2>/dev/null) || exit 0
fi
insert "$FILE" "$SUBJECT"
