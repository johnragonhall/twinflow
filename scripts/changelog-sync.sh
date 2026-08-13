#!/bin/sh
# Insert a Conventional-Commit summary into CHANGELOG.md's [Unreleased] section.
# Called by scripts/hooks/post-commit, but runnable by hand:
#
#   sh scripts/changelog-sync.sh                        # sync from HEAD's subject
#   sh scripts/changelog-sync.sh --subject "feat: x"    # sync from a given subject
#   sh scripts/changelog-sync.sh --catch-up             # recover missed entries
#   sh scripts/changelog-sync.sh --selftest             # run the built-in check
#
# Type to Keep a Changelog heading:
#   feat     -> Added
#   fix      -> Fixed
#   perf     -> Changed
#   refactor -> Changed
# Everything else (docs, chore, test) records nothing: those commits do not
# change what a user of the project can observe.
#
# The body overrides the type for one case. A commit body carries ALL-CAPS
# category headings, which the commit-msg hook requires, and a commit whose
# body is mostly SECURITY items lands under Security, the section Keep a
# Changelog reserves for it. "Mostly" means SECURITY carries strictly more
# items than any other category, so one hardening note inside a feature leaves
# that feature under Added. There is no `security` conventional type here, so
# this heading is the only route a security change has to its own section.
#
# Idempotent. An entry already present under [Unreleased] is never duplicated.
set -u

FILE="CHANGELOG.md"
SUBJECT=""
BODY=""
selftest=0
catchup=0

while [ $# -gt 0 ]; do
  case "$1" in
    --file)     FILE="$2"; shift 2 ;;
    --subject)  SUBJECT="$2"; shift 2 ;;
    --body)     BODY="$2"; shift 2 ;;
    --catch-up) catchup=1; shift ;;
    --selftest) selftest=1; shift ;;
    *) echo "usage: $0 [--file F] [--subject S] [--body B] [--catch-up] [--selftest]" >&2; exit 2 ;;
  esac
done

# dominant_category <body>
# Prints the category carrying strictly more items than any other, or nothing.
# An item is one bullet, or one paragraph under a heading; that is what makes
# "mostly SECURITY" a count of the work rather than a count of the headings,
# which are one apiece and would tie every time.
dominant_category() {
  printf '%s\n' "$1" | awk '
    /^[A-Z][A-Z0-9 +\/-]{1,23}:?$/ { cat=$0; sub(/:$/, "", cat); started=0; next }
    /^[[:space:]]*$/               { started=0; next }
    {
      if (cat == "") next
      if ($0 ~ /^[[:space:]]*[-*][[:space:]]/) { count[cat]++; started=0; next }
      if (!started) { count[cat]++; started=1 }     # a paragraph is one item
    }
    END {
      best=""; top=0; tie=0
      for (c in count) {
        if (count[c] > top) { top=count[c]; best=c; tie=0 }
        else if (count[c] == top) { tie=1 }
      }
      if (best != "" && !tie) print best
    }
  '
}

# insert <file> <commit-subject> [<commit-body>]
# Edits <file> in place when the subject is a recorded conventional type and the
# entry is not already present.
insert() {
  f="$1"; subject="$2"; body="${3:-}"
  [ -f "$f" ] || return 0
  type=$(printf '%s' "$subject" | sed -nE 's/^([a-z]+)(\([^)]*\))?!?:.*/\1/p')
  desc=$(printf '%s' "$subject" | sed -E 's/^[a-z]+(\([^)]*\))?!?:[[:space:]]*//')
  [ -n "$type" ] || return 0
  case "$type" in
    feat)     head="Added" ;;
    fix)      head="Fixed" ;;
    perf)     head="Changed" ;;
    refactor) head="Changed" ;;
    *) return 0 ;;
  esac
  # The body can move a recorded entry to Security, but never make an
  # unrecorded type recordable: a docs commit full of SECURITY notes is still
  # a docs commit.
  [ "$(dominant_category "$body")" = "SECURITY" ] && head="Security"
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
  grep -qF -e "split the router"               "$tmp" || { echo "FAIL: refactor not added"; exit 1; }
  grep -qF -e "adoption guide"                 "$tmp" && { echo "FAIL: docs leaked in"; exit 1; }
  grep -qF -e "bump ruff"                      "$tmp" && { echo "FAIL: chore leaked in"; exit 1; }
  grep -qF -e "cover the replay path"          "$tmp" && { echo "FAIL: test leaked in"; exit 1; }
  insert "$tmp" "feat(kernel): add seeded rng port"   # re-run: must stay idempotent
  n=$(grep -cF -e "- add seeded rng port" "$tmp")
  [ "$n" = "1" ] || { echo "FAIL: not idempotent (count=$n)"; exit 1; }

  # The body override. A body that is mostly SECURITY moves the entry, and one
  # hardening note beside two feature notes does not.
  mostly_security='SECURITY
- pin the update CA
- reject an unsigned manifest

BACKEND
- read the pin from config
'
  one_note='BACKEND
- add the reader
- wire it to the router

SECURITY
- bound the copy
'
  insert "$tmp" "feat(update): verify the manifest" "$mostly_security"
  insert "$tmp" "feat(reader): add tag dedup" "$one_note"
  grep -qF -e "### Security"        "$tmp" || { echo "FAIL: Security heading not created"; exit 1; }
  awk '/^### Security/{f=1;next} /^### /{f=0} f' "$tmp" | grep -qF -e "verify the manifest" \
    || { echo "FAIL: mostly-SECURITY body not filed under Security"; exit 1; }
  awk '/^### Added/{f=1;next} /^### /{f=0} f' "$tmp" | grep -qF -e "add tag dedup" \
    || { echo "FAIL: one SECURITY note moved a feature out of Added"; exit 1; }

  # A body cannot make an unrecorded type recordable.
  insert "$tmp" "docs: describe the pinning" "$mostly_security"
  grep -qF -e "describe the pinning" "$tmp" && { echo "FAIL: docs leaked in via its body"; exit 1; }

  # A tie is not dominance.
  [ -z "$(dominant_category 'FIX
- one

TEST
- one
')" ] || { echo "FAIL: a tie reported a dominant category"; exit 1; }

  rm -f "$tmp"
  echo "changelog-sync selftest: OK"
  exit 0
fi

# Read the subject as UTF-8 regardless of the platform's log output encoding,
# so a non-ASCII byte cannot land mangled in CHANGELOG.md.
# --catch-up walks every commit since the last release tag and inserts whatever
# is missing. The post-commit hook covers the normal path, but it cannot cover
# every path: `git commit-tree` writes a commit with no hooks at all, a rebase
# and a merge deliberately skip the amend, and `--no-verify` skips everything.
# A changelog that silently misses those is worse than one nobody trusts, so
# this makes the gap recoverable in one command instead of by hand.
if [ "$catchup" = "1" ]; then
  since=$(git describe --tags --abbrev=0 --match 'v[0-9]*' 2>/dev/null || echo "")
  range=${since:+$since..HEAD}
  added=0
  # Oldest first, so the newest commit ends up the top bullet of its section.
  for sha in $(git rev-list --reverse --no-merges "${range:-HEAD}" 2>/dev/null); do
    s=$(git -c i18n.logOutputEncoding=UTF-8 log -1 --format=%s "$sha" 2>/dev/null) || continue
    b=$(git -c i18n.logOutputEncoding=UTF-8 log -1 --format=%b "$sha" 2>/dev/null) || b=""
    before=$(cksum < "$FILE")
    insert "$FILE" "$s" "$b"
    [ "$(cksum < "$FILE")" = "$before" ] || { added=$((added + 1)); echo "  recovered: $s"; }
  done
  echo "[changelog-sync] catch-up over ${since:-the whole history}: $added entries recovered"
  exit 0
fi

if [ -z "$SUBJECT" ]; then
  SUBJECT=$(git -c i18n.logOutputEncoding=UTF-8 log -1 --format=%s 2>/dev/null) || exit 0
  [ -n "$BODY" ] || BODY=$(git -c i18n.logOutputEncoding=UTF-8 log -1 --format=%b 2>/dev/null) || BODY=""
fi
insert "$FILE" "$SUBJECT" "$BODY"
