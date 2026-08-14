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

# One grep over every file, one awk over its output. The alternation makes grep report
# three tokens: a whole well formed marker, a bare opening tag, and a bare closing tag.
# Leftmost-longest matching means a well formed marker is reported whole and its own
# opening and closing tags are not reported again, so a marker counts once toward the
# balance and a stray tag is the only thing that can unbalance it.
#
#   <!--METRIC:name-->value<!--/METRIC-->   a marker, with the name optionally naming
#                                           the tag its number arrives at: name@v0.3.0
#   <!--METRIC:                             an opening tag no marker claimed
#   <!--/METRIC-->                          a closing tag no marker claimed
#
# awk holds every marker and every per-file tag count, then reports malformed files,
# unfilled markers, and metrics that disagree with themselves. Counting the whole
# corpus in one process is what keeps this gate off the critical path of every release
# check: a per-file loop spawns processes in proportion to the documentation, and this
# repository's markdown is the input that grows.
tmp=$(mktemp) || exit 1
trap 'rm -f "$tmp"' EXIT

# shellcheck disable=SC2086
# $files holds a newline-separated list of tracked paths and has to split
# into one argument per file. Quoting it hands grep a single argument naming
# a file whose name is every path joined together.
grep -oHE \
  -e '<!--METRIC:[A-Za-z0-9_]+(@v[0-9]+\.[0-9]+\.[0-9]+)?-->[^<]*<!--/METRIC-->' \
  -e '<!--METRIC:' \
  -e '<!--/METRIC-->' \
  $files 2>/dev/null \
| awk -v red="$red" -v yellow="$yellow" -v green="$green" -v reset="$reset" \
      -v cutting="$CUTTING" -v summary="$tmp" '
  # Is version a at or before version b? Compared field by field, because a string
  # comparison puts v0.10.0 before v0.9.0 and would arm a marker early.
  function reached(a, b,   x, y, i) {
    split(a, x, "."); split(b, y, ".")
    for (i = 1; i <= 3; i++) {
      if ((x[i] + 0) < (y[i] + 0)) return 1
      if ((x[i] + 0) > (y[i] + 0)) return 0
    }
    return 1
  }
  # Names carrying more than one distinct value in second, sorted. The list is short
  # enough that an insertion sort beats reaching for sort(1) and another process.
  function conflicting(count, out,   name, k, j) {
    k = 0
    for (name in count) {
      if (count[name] < 2) continue
      for (j = k; j > 0 && out[j] > name; j--) out[j + 1] = out[j]
      out[j + 1] = name
      k++
    }
    return k
  }
  {
    i = index($0, ":<!--")
    f = substr($0, 1, i - 1)
    token = substr($0, i + 1)
    if (!(f in seen)) { seen[f] = 1; files[++nfiles] = f; opens[f] = 0; closes[f] = 0 }
    if (token == "<!--METRIC:") { opens[f]++; next }
    if (token == "<!--/METRIC-->") { closes[f]++; next }

    opens[f]++; closes[f]++
    body = substr(token, 12)                       # past "<!--METRIC:"
    cut = index(body, "-->")
    head = substr(body, 1, cut - 1)
    rest = substr(body, cut + 3)
    value = substr(rest, 1, length(rest) - 14)     # short of "<!--/METRIC-->"
    at = index(head, "@")
    if (at) { name = substr(head, 1, at - 1); arms = substr(head, at + 1) }
    else    { name = head; arms = "-" }

    n++
    mfile[n] = f; mname[n] = name; mvalue[n] = value; marms[n] = arms
    if (!((name SUBSEP value) in valueseen)) { valueseen[name SUBSEP value] = 1; values[name]++ }
    if (arms != "-" && !((name SUBSEP arms) in armseen)) { armseen[name SUBSEP arms] = 1; tags[name]++ }
  }
  END {
    # An opening tag with no matching close, or a close with no open, is malformed.
    # Tags are counted, not lines: two markers can share a line, and a line count
    # would report that line once and hide the imbalance.
    malformed = 0
    for (k = 1; k <= nfiles; k++) {
      f = files[k]
      if (opens[f] == closes[f]) continue
      printf "%sMALFORMED%s %s: %d opening tags, %d closing tags\n", \
        red, reset, f, opens[f], closes[f] > "/dev/stderr"
      malformed++
    }

    # Unfilled markers. A marker naming a later tag is deferred rather than unfilled:
    # the release being cut does not promise that number.
    unfilled = 0; owed = 0; deferred = 0
    for (k = 1; k <= n; k++) {
      value = mvalue[k]
      if (value != "TBD" && value != "tbd" && value != "" && value != "?" && value != "N/A") continue
      unfilled++
      arms = marms[k]
      if (arms != "-" && cutting != "") {
        arm = arms; sub(/^v/, "", arm)
        if (reached(arm, cutting)) {
          printf "%sUNFILLED%s %s: %s (owed from %s)\n", yellow, reset, mfile[k], mname[k], arms
          owed++
        } else {
          printf "%sDEFERRED%s %s: %s arrives at %s\n", green, reset, mfile[k], mname[k], arms
          deferred++
        }
      } else {
        printf "%sUNFILLED%s %s: %s\n", yellow, reset, mfile[k], mname[k]
        owed++
      }
    }

    # The same metric name must not carry two different values in two places. One
    # number, one home. A reader who sees the same metric disagree with itself stops
    # trusting both.
    conflicts = 0
    split("", bad)
    count = conflicting(values, bad)
    for (k = 1; k <= count; k++) {
      printf "%sCONFLICT%s metric \"%s\" has different values in different files:\n", \
        red, reset, bad[k] > "/dev/stderr"
      for (j = 1; j <= n; j++)
        if (mname[j] == bad[k]) printf "    %s = %s\n", mfile[j], mvalue[j] > "/dev/stderr"
      conflicts++
    }

    if (cutting != "")
      printf "\n%d markers found, %d unfilled: %d owed at %s, %d deferred to a later tag\n", \
        n, unfilled, owed, cutting, deferred
    else
      printf "\n%d markers found, %d unfilled\n", n, unfilled

    # A metric that names two different arming tags in two places has two answers to
    # "which release owes this number", and the gate would enforce whichever it read
    # first. One number, one home, one tag.
    split("", bad)
    count = conflicting(tags, bad)
    if (count) {
      printf "%sCONFLICT%s these metrics name more than one arming tag:\n", \
        red, reset > "/dev/stderr"
      for (k = 1; k <= count; k++) print bad[k] > "/dev/stderr"
      conflicts++
    }

    printf "%d %d %d\n", malformed, conflicts, owed > summary
  }'

# read is a shell builtin, so carrying the counts back out of awk costs no process.
# An empty summary means awk never reached its END block, so there is no clean corpus
# to report and the run is a failure rather than a pass.
if ! read -r malformed conflicts owed < "$tmp"; then
  printf '%sFAIL%s the marker scan produced no summary
' "$red" "$reset" >&2
  exit 1
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
