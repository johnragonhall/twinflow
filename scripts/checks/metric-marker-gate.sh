#!/bin/sh
# Metric marker gate.
#
# README.md and the docs state quantitative results. Every one of those numbers is
# either measured and committed, or it is wrapped in an unfilled marker:
#
#     <!--METRIC:name-->TBD<!--/METRIC-->
#
# This gate does two things.
#
#   1. Always: report how many markers are still unfilled, and fail if any marker is
#      malformed or if two markers share a name with different values.
#   2. On a release tag: fail if any marker is still unfilled.
#
# An unfilled marker is normal during the build. The repository is public from Phase 1
# and most numbers arrive later. What is never acceptable is shipping a tagged release
# whose README shows TBD where a reader expects a result.
#
# Usage:
#   sh scripts/checks/metric-marker-gate.sh            # report, never fatal
#   sh scripts/checks/metric-marker-gate.sh --release  # fatal on any unfilled marker
#
# The --release mode is what the release workflow calls. CI calls the default mode.

set -u

MODE="${1:-report}"
root=$(git rev-parse --show-toplevel 2>/dev/null || pwd)
cd "$root" || exit 1

red=$(printf '\033[31m')
yellow=$(printf '\033[33m')
green=$(printf '\033[32m')
reset=$(printf '\033[0m')

# Markdown outside vendored and ignored trees.
#
# --others --exclude-standard includes files that are not committed yet but are not
# ignored either. Without it this gate reads only tracked files, and in a young repo
# that means it scans almost nothing and reports PASS, which is worse than failing.
# docs/DOCUMENTATION-STANDARD.md is excluded because it defines the marker convention
# and has to show one. prose-gate.py carves the same file out of the prose rules for the
# same reason: a document that states a rule necessarily contains what the rule matches.
files=$(git ls-files --cached --others --exclude-standard '*.md' 2>/dev/null \
        | grep -v '^docs/DOCUMENTATION-STANDARD\.md$' \
        | sort -u)
[ -z "$files" ] && files=$(find . -name '*.md' -not -path './.git/*')
[ -z "$files" ] && { echo "no markdown files"; exit 0; }

unfilled=0
malformed=0
tmp=$(mktemp) || exit 1
trap 'rm -f "$tmp" "$tmp.names"' EXIT

for f in $files; do
  # A well formed marker: <!--METRIC:name-->value<!--/METRIC-->
  # Extract name and value together so a mismatched pair is visible.
  grep -oE '<!--METRIC:[A-Za-z0-9_]+-->[^<]*<!--/METRIC-->' "$f" 2>/dev/null \
    | while IFS= read -r m; do
        name=$(printf '%s' "$m" | sed -E 's/^<!--METRIC:([A-Za-z0-9_]+)-->.*/\1/')
        value=$(printf '%s' "$m" | sed -E 's/^<!--METRIC:[A-Za-z0-9_]+-->(.*)<!--\/METRIC-->$/\1/')
        printf '%s\t%s\t%s\n' "$f" "$name" "$value"
      done >> "$tmp"

  # An opening tag with no matching close, or a close with no open, is malformed.
  # Count occurrences, not matching lines: two markers can share a line, and grep -c
  # would report that line once and hide the imbalance.
  opens=$(grep -o '<!--METRIC:' "$f" 2>/dev/null | wc -l | tr -d ' ')
  closes=$(grep -o '<!--/METRIC-->' "$f" 2>/dev/null | wc -l | tr -d ' ')
  if [ "$opens" != "$closes" ]; then
    printf '%sMALFORMED%s %s: %s opening tags, %s closing tags\n' \
      "$red" "$reset" "$f" "$opens" "$closes" >&2
    malformed=$((malformed + 1))
  fi
done

# Unfilled markers.
while IFS="$(printf '\t')" read -r f name value; do
  case "$value" in
    TBD|tbd|""|"?"|"N/A")
      printf '%sUNFILLED%s %s: %s\n' "$yellow" "$reset" "$f" "$name"
      unfilled=$((unfilled + 1))
      ;;
  esac
done < "$tmp"

# The same metric name must not carry two different values in two places. One number,
# one home. A reader who sees the same metric disagree with itself stops trusting both.
awk -F'\t' '{print $2"\t"$3}' "$tmp" | sort -u | awk -F'\t' '
  { if ($1 in seen && seen[$1] != $2) { print $1; } seen[$1] = $2 }
' | sort -u > "$tmp.names"

conflicts=0
while IFS= read -r name; do
  [ -z "$name" ] && continue
  printf '%sCONFLICT%s metric "%s" has different values in different files:\n' \
    "$red" "$reset" "$name" >&2
  awk -F'\t' -v n="$name" '$2 == n { printf "    %s = %s\n", $1, $3 }' "$tmp" >&2
  conflicts=$((conflicts + 1))
done < "$tmp.names"

total=$(wc -l < "$tmp" | tr -d ' ')
printf '\n%s markers found, %s unfilled\n' "$total" "$unfilled"

if [ "$malformed" -gt 0 ] || [ "$conflicts" -gt 0 ]; then
  printf '%sFAIL%s malformed markers: %s, conflicting metric names: %s\n' \
    "$red" "$reset" "$malformed" "$conflicts" >&2
  exit 1
fi

if [ "$MODE" = "--release" ] && [ "$unfilled" -gt 0 ]; then
  printf '%sFAIL%s %s unfilled metric marker(s) block a tagged release.\n' \
    "$red" "$reset" "$unfilled" >&2
  printf 'Measure the value and commit the artifact that produced it, or remove the claim.\n' >&2
  exit 1
fi

printf '%sPASS%s metric markers\n' "$green" "$reset"
exit 0
