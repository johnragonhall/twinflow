#!/usr/bin/env python3
"""Fatal pre-commit judge for the rules a regex gate cannot see.

Two modes:

    python scripts/hooks/comment_judge.py                 added comments and docs
    python scripts/hooks/comment_judge.py --commit-msg F  the commit message in F

The prose gate owns everything mechanical: banned phrases, sentence length,
approved words. What it cannot see is whether a comment restates the code, or
whether a commit bullet narrates a change instead of describing what the code
now does. That judgement goes to the `claude` CLI, which sees only the added
lines rather than the whole file.

Design guards, each one deliberate:

  * FATAL on a finding, but FAILS OPEN on any infrastructure problem: no CLI, no
    network, a timeout, unparseable output. A network blip must never
    permanently block a commit.
  * A verdict of "violations found" exits VIOLATION_EXIT (3), never 1. The
    caller cannot otherwise tell a real finding from a launcher that refused to
    start this script at all, and treating the second as a finding blocks a
    commit for a reason the author cannot act on.
  * The timeout kills the whole process tree. The CLI spawns children that
    inherit the output pipes, so killing only the parent leaves communicate()
    blocked on pipes nobody will close, which is a hang no per-process timeout
    prevents.
  * It runs only when comment or doc lines actually changed.
  * Budget: COMMENT_JUDGE_TIMEOUT=<seconds>, default 120. A short budget
    silently fails open under load, which costs more than the wait.
  * Disable once:  COMMENT_JUDGE=0 git commit ...
  * Bypass all:    git commit --no-verify
"""

import contextlib
import glob
import io
import json
import os
import re
import subprocess
import sys
from pathlib import Path

for _stream in (sys.stdout, sys.stderr):
    # Both are TextIOWrapper on a real console, but typeshed declares the
    # narrower TextIO, which has no reconfigure().
    if isinstance(_stream, io.TextIOWrapper):
        _stream.reconfigure(encoding="utf-8", errors="replace")

CODE_EXT = (".py", ".rs")
DOC_EXT = (".md", ".markdown")
EXCLUDE = (
    "node_modules/",
    "target/",
    "dist/",
    "build/",
    ".git/",
    ".venv/",
    "site/",
    "scripts/hooks/",
    # The frozen design specification and the style files that hold the words
    # the rules reject. Judging either produces noise about text that is
    # deliberate.
    "docs/design/",
    "docs/style/",
    "docs/superpowers/",
)
MAX_LINES = 160
TIMEOUT_S = int(os.environ.get("COMMENT_JUDGE_TIMEOUT", "120"))

#: Exit code meaning "the judge ran and found violations". Distinct from 1 so a
#: wrapper that refuses to launch this script, or an interpreter that is not
#: there, cannot be mistaken for a finding.
VIOLATION_EXIT = 3

_SHARED_TONE = """\
 - rule-of-three padding, and forced "not just X but Y" negative parallelism
 - promotional or significance-inflating tone ("crucial", "seamless", "robust")
 - AI vocabulary pile-ups ("delve", "leverage", "underscore", "tapestry")"""

COMMENT_RULES = f"""You are a fatal pre-commit reviewer. Judge ONLY the added lines below,
which are code comments and markdown prose from a staged commit. Report a
violation ONLY when you are highly confident; when unsure, stay silent. Do NOT
flag em dashes, curly quotes, or emoji, which a deterministic gate owns. Do NOT
flag text that is quoting or defining a rule as an example.

Flag against these rules:

Code-comment rules:
 1 A comment must not restate what the code plainly does.
 2 A comment must not paper over unclear code that should be renamed instead.
 3 A comment must dispel confusion, not add it.
 4 A bug-fix comment should say what and why, rather than be absent.
 5 Incomplete work should be marked with TODO or FIXME and context.

Prose rules:
{_SHARED_TONE}
 - diff-anchored comments that narrate a change instead of describing the thing
   as it now is ("this replaces the old...", "previously we...", "used to be").

Return ONLY a JSON object, no prose:
{{"violations":[{{"file":"path","line":N,"rule":"short-tag","why":"one sentence"}}]}}
Empty list means clean."""

COMMIT_RULES = f"""You are a fatal commit-message reviewer. Judge ONLY the message below.
Report a violation ONLY when you are highly confident; when unsure, stay silent.

The single most important rule:

 A bullet states what the change DOES, in the present tense, as a summary of the
 behaviour that now exists. It is not a description of the past and not a
 narration of the edit. The reader is somebody reading `git log` a year from
 now who does not know what the code looked like before.

 Good:  "- cap the request body at 1 MiB and return 413 past it"
 Good:  "- the sequence starts at 0, so run_started sits at 0"
 Bad:   "- the version was written twice, and now it is read from the module"
 Bad:   "- previously the gate reported KEPT over a broken tree"
 Bad:   "- fixed a bug where the loader crashed"
 Bad:   "- changed X to Y"

Flag a bullet that:
 - narrates the edit or the previous state ("was", "used to", "previously",
   "now reads", "no longer", "changed from ... to", "fixed a bug where")
 - describes the work rather than the result ("added support for", "updated the
   handling of", "refactored")
 - is a past-tense report rather than a present-tense summary

Also flag:
{_SHARED_TONE}

A TEST section may state measured results in the past tense ("142 passed"), and
a bullet that names a defect the change removes is fine when it says what the
code does instead. Do not flag the subject line.

Return ONLY a JSON object, no prose:
{{"violations":[{{"file":"COMMIT_MSG","line":N,"rule":"short-tag","why":"one sentence"}}]}}
Empty list means clean."""


def added_prose(diff):
    """The added comment and doc lines from a staged diff, with line numbers."""
    path, line_number, out = None, 0, []
    for raw in diff.splitlines():
        if raw.startswith("+++ "):
            candidate = raw[4:]
            path = candidate[2:] if candidate.startswith("b/") else candidate
        elif raw.startswith("@@"):
            match = re.search(r"\+(\d+)", raw)
            line_number = int(match.group(1)) if match else 0
        elif raw.startswith("+"):
            content = raw[1:]
            if path and not any(x in path for x in EXCLUDE):
                stripped = content.lstrip()
                is_doc = path.endswith(DOC_EXT)
                is_comment = stripped.startswith(("#", "//", "///", "//!", "*", "/*", '"""'))
                if (is_doc or (path.endswith(CODE_EXT) and is_comment)) and stripped.strip():
                    out.append((path, line_number, content.rstrip()))
            line_number += 1
    return out


def delete_transcript(session_id):
    """Remove the transcript this headless run created.

    Each commit would otherwise leave a resumable conversation behind. Best
    effort: never fatal to the commit.
    """
    if not session_id:
        return
    pattern = os.path.join(
        os.path.expanduser("~"), ".claude", "projects", "*", f"{session_id}.jsonl"
    )
    for path in glob.glob(pattern):
        with contextlib.suppress(OSError):
            os.remove(path)


def extract_json(text):
    start, end = text.find("{"), text.rfind("}")
    if start == -1 or end == -1 or end < start:
        raise ValueError("no json object in model output")
    return json.loads(text[start : end + 1])


def kill_tree(proc):
    """Fell the judge's whole process tree.

    The CLI spawns children that inherit our pipes. On Windows proc.kill()
    reaps only the parent, the orphans hold the pipe handles open, and
    communicate() blocks on them forever.
    """
    if os.name == "nt":
        subprocess.run(["taskkill", "/F", "/T", "/PID", str(proc.pid)], capture_output=True)
    else:
        proc.kill()


JUDGE_ARGV = ["claude", "-p", "--output-format", "json"]


def run_judge(prompt, argv=None):
    """Run the CLI with a hard wall-clock budget.

    Raises RuntimeError, which is the caller's fail-open path. argv is
    injectable so the timeout path is testable without the real CLI.
    """
    proc = subprocess.Popen(
        argv or JUDGE_ARGV,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    try:
        out, err = proc.communicate(input=prompt, timeout=TIMEOUT_S)
    except subprocess.TimeoutExpired:
        kill_tree(proc)
        with contextlib.suppress(subprocess.TimeoutExpired):
            proc.communicate(timeout=10)
        raise RuntimeError(
            f"judge timed out after {TIMEOUT_S}s, process tree killed "
            "(COMMENT_JUDGE_TIMEOUT to adjust)"
        ) from None
    if proc.returncode != 0:
        raise RuntimeError(err.strip()[:200] or "claude exited non-zero")
    return out


def judge(prompt, label):
    """Send one payload and return its violations, failing open on any problem."""
    session_id = None
    try:
        stdout = run_judge(prompt)
        envelope = json.loads(stdout)
        session_id = envelope.get("session_id")
        verdict = extract_json(envelope.get("result", stdout))
        return verdict.get("violations", [])
    except Exception as exc:  # fail OPEN on any infrastructure problem
        sys.stderr.write(f"\033[33m{label}: judge skipped ({exc})\033[0m\n")
        return None
    finally:
        delete_transcript(session_id)


def report(violations, label):
    if violations is None:
        return 0
    if not violations:
        sys.stderr.write(f"\033[32m{label}: judge clean\033[0m\n")
        return 0
    sys.stderr.write(f"\n\033[31m{label} BLOCKED\033[0m\n")
    for item in violations:
        sys.stderr.write(
            f"  {item.get('file')}:{item.get('line')}  [{item.get('rule')}]  {item.get('why')}\n"
        )
    sys.stderr.write(
        "\nFix them, disable the judge once (COMMENT_JUDGE=0 git commit ...),\n"
        "or bypass every hook once (git commit --no-verify).\n"
    )
    return VIOLATION_EXIT


def git_roots():
    """The working tree and the git directory, resolved.

    Both, because git hands the hook a message file under the git directory
    while a caller testing the hook points it at a file in the working tree,
    and a worktree or a submodule puts those two in different places.
    """
    roots = []
    for flag in ("--show-toplevel", "--git-dir"):
        result = subprocess.run(
            ["git", "rev-parse", flag],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
        if result.returncode == 0 and result.stdout.strip():
            roots.append(Path(result.stdout.strip()).resolve())
    return roots


def message_path_within(candidate, roots=None):
    """Resolve a commit-message path, refusing anything outside the repository.

    This script reads the file and sends its contents to an external CLI, so
    the path decides what leaves the machine. Confining it to the repository
    keeps a mistyped or malicious --commit-msg argument from turning the hook
    into a way to post ~/.ssh/id_rsa to a third party.

    Resolved before the comparison, so a symlink or a .. segment is judged by
    where it lands rather than by how it is spelled. `roots` is injectable so
    the check itself is testable.
    """
    path = Path(candidate).resolve()
    if not path.is_file():
        raise ValueError(f"{candidate!r} is not a file")

    allowed = git_roots() if roots is None else [Path(r).resolve() for r in roots]
    if not allowed:
        raise ValueError("not inside a git repository")
    if not any(path == root or root in path.parents for root in allowed):
        raise ValueError(
            f"{path} is outside this repository. A commit message lives in the "
            f"working tree or the git directory, and this script sends what it "
            f"reads to an external service"
        )
    return path


def judge_commit_message(path):
    try:
        resolved = message_path_within(path)
    except ValueError as exc:
        # Refuse to read it, and do not block the commit. Nothing left the
        # machine, and an author cannot act on a path their tooling chose.
        sys.stderr.write(f"\033[33mcommit-msg: judge skipped ({exc})\033[0m\n")
        return 0

    with open(resolved, encoding="utf-8", errors="replace") as handle:
        text = handle.read()
    body = "\n".join(line for line in text.splitlines() if not line.startswith("#")).strip()
    if not body:
        return 0
    numbered = "\n".join(f"{i}: {line}" for i, line in enumerate(body.splitlines(), 1))
    return report(judge(COMMIT_RULES + "\n\nMessage:\n" + numbered, "commit-msg"), "commit-msg")


def judge_staged_prose():
    diff = subprocess.run(
        ["git", "diff", "--cached", "-U0", "--diff-filter=ACM"],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    ).stdout
    lines = added_prose(diff)
    if not lines:
        return 0
    payload = "\n".join(f"{p}:{n}: {c}" for p, n, c in lines[:MAX_LINES])
    return report(judge(COMMENT_RULES + "\n\nAdded lines:\n" + payload, "pre-commit"), "pre-commit")


def main(argv):
    if os.environ.get("COMMENT_JUDGE", "1") == "0":
        return 0
    if len(argv) >= 2 and argv[0] == "--commit-msg":
        return judge_commit_message(argv[1])
    return judge_staged_prose()


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
