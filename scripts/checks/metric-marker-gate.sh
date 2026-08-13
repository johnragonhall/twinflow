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
#   2. On a release tag: fail on an unfilled marker whose number that release owes.
#
# A marker may name the tag its number arrives at:
#
#     <!--METRIC:agent_eval_accuracy@v0.3.0-->TBD<!--/METRIC-->
#
# and is then owed from that tag onward. A marker naming no tag is owed by every
# release. This is the arrangement gates.yaml uses for a gate's first phase, and it
# exists for the same reason: the repository is public from Phase 1, most numbers
# arrive with the subsystem that measures them, and a rule making the first tag wait
# for the last number stops every release rather than one false one. What is never
# acceptable is a tagged release whose README shows TBD where that release promised a
# result.
#
# Usage:
#   sh scripts/checks/metric-marker-gate.sh                # report, never fatal
#   sh scripts/checks/metric-marker-gate.sh --release 0.1.0
#
# The --release mode is what the release workflow calls, with the version being cut.
# Without a version every unfilled marker is owed, which is the strict reading and the
# safe default.

set -u

MODE="${1:-report}"
CUTTING="${2:-}"
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
  # A well formed marker: <!--METRIC:name-->value<!--/METRIC-->, with the name
  # optionally naming the tag its number arrives at: name@v0.3.0.
  # Extract the parts together so a mismatched pair is visible.
  grep -oE '<!--METRIC:[A-Za-z0-9_]+(@v[0-9]+\.[0-9]+\.[0-9]+)?-->[^<]*<!--/METRIC-->' "$f" 2>/dev/null \
    | while IFS= read -r m; do
        head=$(printf '%s' "$m" | sed -E 's/^<!--METRIC:([^>]*)-->.*/\1/')
        name=${head%@*}
        case "$head" in
          *@*) arms=${head#*@} ;;
          *)   arms="-" ;;
        esac
        value=$(printf '%s' "$m" | sed -E 's/^<!--METRIC:[^>]*-->(.*)<!--\/METRIC-->$/\1/')
        printf '%s\t%s\t%s\t%s\n' "$f" "$name" "$value" "$arms"
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

# Is version $1 at or before version $2? Compared field by field, because a
# string comparison puts v0.10.0 before v0.9.0 and would arm a marker early.
version_reached() {
  awk -v a="$1" -v b="$2" '
    BEGIN {
      split(a, x, "."); split(b, y, ".")
      for (i = 1; i <= 3; i++) {
        if ((x[i] + 0) < (y[i] + 0)) exit 0
        if ((x[i] + 0) > (y[i] + 0)) exit 1
      }
      exit 0
    }'
}

# Unfilled markers. A marker naming a later tag is deferred rather than unfilled:
# the release being cut does not promise that number.
owed=0
deferred=0
while IFS="$(printf '\t')" read -r f name value arms; do
  case "$value" in
    TBD|tbd|""|"?"|"N/A") ;;
    *) continue ;;
  esac
  unfilled=$((unfilled + 1))
  if [ "$arms" != "-" ] && [ -n "$CUTTING" ]; then
    if version_reached "${arms#v}" "$CUTTING"; then
      printf '%sUNFILLED%s %s: %s (owed from %s)\n' "$yellow" "$reset" "$f" "$name" "$arms"
      owed=$((owed + 1))
    else
      printf '%sDEFERRED%s %s: %s arrives at %s\n' "$green" "$reset" "$f" "$name" "$arms"
      deferred=$((deferred + 1))
    fi
  else
    printf '%sUNFILLED%s %s: %s\n' "$yellow" "$reset" "$f" "$name"
    owed=$((owed + 1))
  fi
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
if [ -n "$CUTTING" ]; then
  printf '\n%s markers found, %s unfilled: %s owed at %s, %s deferred to a later tag\n' \
    "$total" "$unfilled" "$owed" "$CUTTING" "$deferred"
else
  printf '\n%s markers found, %s unfilled\n' "$total" "$unfilled"
fi

# A metric that names two different arming tags in two places has two answers to
# "which release owes this number", and the gate would enforce whichever it read
# first. One number, one home, one tag.
split_arms=$(awk -F'\t' '$4 != "-" {print $2"\t"$4}' "$tmp" | sort -u \
  | awk -F'\t' '{ if ($1 in seen && seen[$1] != $2) print $1; seen[$1] = $2 }' | sort -u)
if [ -n "$split_arms" ]; then
  printf '%sCONFLICT%s these metrics name more than one arming tag:\n' "$red" "$reset" >&2
  printf '%s\n' "$split_arms" >&2
  conflicts=$((conflicts + 1))
fi

if [ "$malformed" -gt 0 ] || [ "$conflicts" -gt 0 ]; then
  printf '%sFAIL%s malformed markers: %s, conflicting metric names: %s\n' \
    "$red" "$reset" "$malformed" "$conflicts" >&2
  exit 1
fi

if [ "$MODE" = "--release" ] && [ "$owed" -gt 0 ]; then
  printf '%sFAIL%s %s unfilled metric marker(s) block this release.\n' \
    "$red" "$reset" "$owed" >&2
  printf 'Measure the value and commit the artifact that produced it, remove the claim,\n' >&2
  printf 'or name the tag it arrives at:  <!--METRIC:name@v0.3.0-->TBD<!--/METRIC-->\n' >&2
  exit 1
fi

printf '%sPASS%s metric markers\n' "$green" "$reset"
exit 0
