#!/usr/bin/env python3
"""Documentation standard gate.

Enforces docs/DOCUMENTATION-STANDARD.md. Every rule this script applies is read
from the two style files, so the rules have one home and this script has none:

    docs/style/banned-phrases.yml   regex rules, sentence limits, description rules
    docs/style/ste-terms.yml        project word list and non-approved words

Usage:

    python scripts/checks/prose-gate.py                 staged files (git hook)
    python scripts/checks/prose-gate.py --all           every tracked file (CI)
    python scripts/checks/prose-gate.py path/to/file.md one or more explicit files
    python scripts/checks/prose-gate.py --all --strict  promote warnings to errors

Checks, in the order docs/DOCUMENTATION-STANDARD.md section 9 lists them:

    1,2,6  regex rules from banned-phrases.yml, by severity and topic type
    3      front matter present, description one sentence and within word bounds
    4,10   heading case
    5      sentence length ceilings by topic type
    7      non-approved words from ste-terms.yml, in task and reference topics
    8      unfilled metric markers: NOT here, see below
    9      bold-header vertical lists (LIST-01 in banned-phrases.yml)

Escape token, per line, per rule:

    docs-lint-ok <RULE-ID> <reason>

Check 8 lives in scripts/checks/metric-marker-gate.sh, which also catches a
malformed marker and two markers that share a name with different values. One
home per rule, so it is not duplicated here.

An escape with no reason fails, because a gate that is easy to silence is not a
gate. The two style files are exempt from every rule, since they hold the words
the rules reject.

Needs PyYAML. Without it the gate reports SKIP and exits 0, matching how the
pre-commit hook treats every other missing tool: CI is the hard backstop and
installs it.
"""

import contextlib
import fnmatch
import os
import re
import subprocess
import sys

for _stream in (sys.stdout, sys.stderr):
    with contextlib.suppress(AttributeError, ValueError):
        _stream.reconfigure(encoding="utf-8", errors="replace")

try:
    import yaml
except ImportError:
    print(
        "[prose] SKIP: PyYAML not installed, cannot read docs/style/*.yml.\n"
        "        Install it (uv tool install pyyaml, or pip install pyyaml),\n"
        "        or let the Lint workflow enforce this."
    )
    sys.exit(0)

BANNED_PHRASES = "docs/style/banned-phrases.yml"
STE_TERMS = "docs/style/ste-terms.yml"

# The style files hold the words the rules reject, so they are exempt from
# every rule (docs/DOCUMENTATION-STANDARD.md section 5a).
CONFIG_FILES = (BANNED_PHRASES, STE_TERMS)

# The standard itself quotes the phrases it bans, in its editorial-rules list.
# It gets the same carve-out for the same reason, but a narrower one: only the
# prose rules are lifted. The mechanical character rules (dashes, curly quotes,
# emoji) still apply, because no document has a reason to contain those.
RULE_STATING_FILES = ("docs/DOCUMENTATION-STANDARD.md",)

TEXT_EXT = (
    ".md",
    ".markdown",
    ".py",
    ".rs",
    ".sh",
    ".toml",
    ".yml",
    ".yaml",
    ".json",
    ".jsonc",
    ".txt",
    ".cfg",
    ".ini",
    ".sql",
    ".ts",
    ".tsx",
    ".js",
)
MARKDOWN_EXT = (".md", ".markdown")

# Build output, virtual environments, vendored trees. Nothing authored here.
EXCLUDE = (
    ".git/",
    ".venv/",
    "node_modules/",
    "target/",
    "dist/",
    "build/",
    "site/",
    "__pycache__/",
)

ESCAPE_TOKEN = "docs-lint-ok"
ESCAPE_RE = re.compile(re.escape(ESCAPE_TOKEN) + r"\s+([A-Za-z0-9_*-]+)\s*(.*)$")

ERROR = "error"
WARN = "warn"


# --------------------------------------------------------------------------
# Loading
# --------------------------------------------------------------------------


def run_git(*args):
    """Run a git command and return stdout, or an empty string on failure."""
    result = subprocess.run(
        ["git", *args],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    return result.stdout if result.returncode == 0 else ""


def load_yaml(path):
    try:
        with open(path, encoding="utf-8") as handle:
            return yaml.safe_load(handle) or {}
    except OSError:
        sys.stderr.write(
            f"\n\033[31mBLOCKED: {path} is missing.\033[0m\n"
            "The documentation standard keeps its rules there. Restore the file\n"
            "or update docs/DOCUMENTATION-STANDARD.md before disabling the gate.\n"
        )
        sys.exit(1)
    except yaml.YAMLError as exc:
        sys.stderr.write(f"\n\033[31mBLOCKED: {path} is not valid YAML.\033[0m\n{exc}\n")
        sys.exit(1)


def compile_rules(config):
    """Compile every regex rule, keeping the metadata each one carries."""
    rules = []
    for raw in config.get("rules", []):
        try:
            pattern = re.compile(raw["pattern"])
        except (KeyError, re.error) as exc:
            sys.stderr.write(f"[prose] skipping malformed rule {raw.get('id')}: {exc}\n")
            continue
        rules.append(
            {
                "id": raw.get("id", "UNNAMED"),
                "severity": raw.get("severity", ERROR),
                "pattern": pattern,
                "reason": raw.get("reason", ""),
                "replace_with": raw.get("replace_with", ""),
                "topic_types": raw.get("topic_types"),
                "exempt_files": raw.get("exempt_files", []),
                # A rule applies outside Markdown when it says so, or, when it
                # says nothing, whenever its pattern holds no ASCII letter. That
                # is exactly the mechanical character rules (dashes, curly
                # quotes, emoji), which belong in source files too. Prose rules
                # carry words, so they stay in Markdown where prose lives.
                "all_files": (
                    "all" in raw["applies_to"]
                    if raw.get("applies_to")
                    else not re.search("[A-Za-z]", raw["pattern"])
                ),
            }
        )
    return rules


def build_term_rules(terms):
    """Turn ste-terms.yml into the same rule shape the regex rules use.

    non_approved words are errors: the standard states the replacement, so the
    fix is mechanical. The rejected synonyms attached to a declared technical
    noun or verb are warnings, because a word like "issue" or "robot" is only
    wrong when it names the declared concept, and correct in any other sense.
    """
    rules = []

    def add(word, replacement, severity, kind, declared=None):
        # The hyphen and underscore in the boundary classes keep a CLI flag or
        # an identifier from tripping a prose rule: --no-verify is not the word
        # "verify", and no_verify is not it either.
        try:
            pattern = re.compile(r"(?i)(?<![A-Za-z0-9_-])" + re.escape(word) + r"(?![A-Za-z0-9_-])")
        except re.error:
            return
        rules.append(
            {
                "id": f"STE-TERM-{kind}",
                "severity": severity,
                "pattern": pattern,
                "reason": (
                    f"'{word}' is not the approved word"
                    + (f" for the declared term '{declared}'" if declared else "")
                ),
                "replace_with": replacement,
                "topic_types": ["task", "reference"],
                "exempt_files": [],
                "all_files": False,
            }
        )

    for entry in terms.get("non_approved", []):
        if isinstance(entry, dict) and entry.get("word"):
            add(entry["word"], entry.get("use", ""), ERROR, "WORD")

    for group in (terms.get("technical_nouns") or {}).values():
        for entry in group or []:
            for synonym in entry.get("rejects", []) or []:
                add(synonym, entry.get("term", ""), WARN, "SYN", entry.get("term"))

    for entry in terms.get("technical_verbs") or []:
        for synonym in entry.get("rejects", []) or []:
            add(synonym, entry.get("term", ""), WARN, "SYN", entry.get("term"))

    return rules


def protected_pattern(terms):
    """One regex matching every protected term, so those never trip a word rule."""
    protected = [str(t) for t in terms.get("protected_terms", []) or []]
    if not protected:
        return None
    protected.sort(key=len, reverse=True)
    return re.compile("|".join(re.escape(t) for t in protected), re.IGNORECASE)


# --------------------------------------------------------------------------
# File selection
# --------------------------------------------------------------------------


def in_scope(path):
    if not path:
        return False
    normalized = path.replace("\\", "/")
    if any(part in normalized for part in EXCLUDE):
        return False
    if normalized in CONFIG_FILES:
        return False
    return normalized.endswith(TEXT_EXT)


def within_repo(path, root):
    """True when path resolves to a location inside root.

    Explicit paths arrive from the command line, and in CI the caller is often a
    changed-file list derived from a pull request. Findings quote the text they match,
    and CI logs on a public repository are public, so a path that resolves outside the
    working tree would print the contents of an arbitrary file into a public log.
    Resolution follows symlinks, so a link committed inside the tree that points outside
    it is refused on the same test.
    """
    try:
        resolved = os.path.realpath(path)
    except OSError:
        return False
    return resolved == root or resolved.startswith(root + os.sep)


def select_files(argv):
    root = os.path.realpath(os.getcwd())
    explicit = [a for a in argv if not a.startswith("-")]
    if explicit:
        selected = []
        for candidate in explicit:
            if not in_scope(candidate):
                continue
            if not within_repo(candidate, root):
                sys.stderr.write(
                    f"\033[31mrefused\033[0m {candidate}: resolves outside the working tree\n"
                )
                continue
            selected.append(candidate.replace("\\", "/"))
        return selected
    if "--all" in argv:
        listing = run_git("ls-files")
    else:
        listing = run_git("diff", "--cached", "--name-only", "--diff-filter=ACM")
    return [p for p in listing.splitlines() if in_scope(p) and within_repo(p, root)]


# --------------------------------------------------------------------------
# Document model
# --------------------------------------------------------------------------


class Document:
    """A file plus whatever the standard needs to know about it."""

    def __init__(self, path, text):
        self.path = path
        self.text = text
        self.lines = text.splitlines()
        self.is_markdown = path.endswith(MARKDOWN_EXT)
        self.front_matter = {}
        self.body_offset = 0
        if self.is_markdown:
            self._parse_front_matter()

    def _parse_front_matter(self):
        if not self.lines or self.lines[0].strip() != "---":
            return
        for index in range(1, len(self.lines)):
            if self.lines[index].strip() in ("---", "..."):
                block = "\n".join(self.lines[1:index])
                try:
                    parsed = yaml.safe_load(block)
                except yaml.YAMLError:
                    parsed = None
                self.front_matter = parsed if isinstance(parsed, dict) else {}
                self.body_offset = index + 1
                return

    @property
    def topic_type(self):
        value = self.front_matter.get("topic_type")
        return str(value).strip().lower() if value else None


def escaped(line, rule_id):
    """True when the line carries a valid escape for this rule.

    Returns the string "no-reason" when the escape names the rule but gives no
    reason, so the caller can report that instead of honoring it.
    """
    match = ESCAPE_RE.search(line)
    if not match:
        return False
    named, reason = match.group(1), match.group(2).strip()
    if named not in (rule_id, "*"):
        return False
    return True if len(reason) >= 3 else "no-reason"


# --------------------------------------------------------------------------
# Checks
# --------------------------------------------------------------------------


def check_rules(doc, rules, protected, findings):
    states_the_rules = doc.path in RULE_STATING_FILES
    for rule in rules:
        if not rule["all_files"] and (not doc.is_markdown or states_the_rules):
            continue
        if any(fnmatch.fnmatch(doc.path, p) for p in rule["exempt_files"]):
            continue
        if rule["topic_types"] and doc.topic_type not in rule["topic_types"]:
            continue
        for number, line in enumerate(doc.lines, start=1):
            match = rule["pattern"].search(line)
            if not match:
                continue
            if (
                protected is not None
                and rule["id"].startswith("STE-TERM")
                and any(
                    span.start() <= match.start() < span.end() for span in protected.finditer(line)
                )
            ):
                continue
            state = escaped(line, rule["id"])
            if state is True:
                continue
            if state == "no-reason":
                findings.append(
                    (
                        doc.path,
                        number,
                        rule["id"],
                        ERROR,
                        f"{ESCAPE_TOKEN} with no reason. State why the rule does not apply.",
                    )
                )
                continue
            detail = rule["reason"]
            if rule["replace_with"]:
                detail = f"{detail} Use: {rule['replace_with']}"
            findings.append((doc.path, number, rule["id"], rule["severity"], detail))


def check_front_matter(doc, description_rules, exempt, findings):
    if not doc.is_markdown or doc.path in exempt:
        return
    if not doc.front_matter:
        findings.append(
            (
                doc.path,
                1,
                "FM-01",
                ERROR,
                "no YAML front matter. Needs title, description, topic_type, audience.",
            )
        )
        return

    for field in ("title", "description", "topic_type"):
        if not doc.front_matter.get(field):
            findings.append((doc.path, 1, "FM-02", ERROR, f"front matter has no {field}"))

    description = str(doc.front_matter.get("description") or "").strip()
    if not description:
        return

    words = description.split()
    low = description_rules.get("min_words", 10)
    high = description_rules.get("max_words", 30)
    if not low <= len(words) <= high:
        findings.append(
            (
                doc.path,
                1,
                "FM-03",
                ERROR,
                f"description is {len(words)} words, needs {low} to {high}",
            )
        )

    max_sentences = description_rules.get("max_sentences", 1)
    if len(split_sentences(description)) > max_sentences:
        findings.append(
            (
                doc.path,
                1,
                "FM-04",
                ERROR,
                f"description is more than {max_sentences} sentence",
            )
        )

    if description_rules.get("must_not_restate_title"):
        title = str(doc.front_matter.get("title") or "").strip().lower()
        if title and description.lower().startswith(title):
            findings.append((doc.path, 1, "FM-05", ERROR, "description restates the title"))


HEADING_RE = re.compile(r"^(#{1,6})\s+(.*?)\s*#*\s*$")
CODE_FENCE_RE = re.compile(r"^\s*(```|~~~)")
INLINE_CODE_RE = re.compile(r"`[^`]*`")
LINK_RE = re.compile(r"\[([^\]]*)\]\([^)]*\)")
HTML_COMMENT_RE = re.compile(r"<!--.*?-->", re.DOTALL)


def strip_markup(text):
    """Reduce a line to the words a reader actually reads.

    HTML comments go first: an escape annotation is not prose, and counting it
    would push an honest sentence over the length ceiling.
    """
    text = HTML_COMMENT_RE.sub(" ", text)
    text = INLINE_CODE_RE.sub(" ", text)
    text = LINK_RE.sub(r"\1", text)
    return re.sub(r"[*_>]+", "", text)


ABBREVIATIONS = ("e.g.", "i.e.", "etc.", "vs.", "cf.", "no.", "fig.")


def split_sentences(text):
    """Split into sentences, keeping common abbreviations intact."""
    parts = re.split(r'(?<=[.!?])\s+(?=[A-Z"(\[])', text.strip())
    merged = []
    for part in parts:
        if merged and merged[-1].lower().endswith(ABBREVIATIONS):
            merged[-1] = merged[-1] + " " + part
        else:
            merged.append(part)
    return [p for p in merged if p.strip()]


def check_headings(doc, findings):
    """Sentence case only. Advisory, because proper nouns look like title case."""
    if not doc.is_markdown:
        return
    in_fence = False
    for number, line in enumerate(doc.lines, start=1):
        if CODE_FENCE_RE.match(line):
            in_fence = not in_fence
            continue
        if in_fence:
            continue
        match = HEADING_RE.match(line)
        if not match:
            continue
        text = strip_markup(match.group(2))
        words = text.split()[1:]
        capitalized = [
            word for word in words if len(word) > 1 and word[0].isupper() and word[1:].islower()
        ]
        if len(capitalized) >= 2 and escaped(line, "HEAD-01") is not True:
            findings.append(
                (
                    doc.path,
                    number,
                    "HEAD-01",
                    WARN,
                    (
                        "heading looks like title case. Sentence case only, "
                        f"unless these are proper nouns: {' '.join(capitalized)}"
                    ),
                )
            )


def iter_prose_blocks(doc):
    """Yield (start_line, is_list_item, text) for each prose block.

    Front matter, fenced code, tables, headings, HTML comments, and link
    definitions are not prose and are skipped.
    """
    in_fence = False
    block = []
    start = 0
    is_list = False

    def flush():
        if block:
            return (start, is_list, " ".join(block))
        return None

    for index in range(doc.body_offset, len(doc.lines)):
        line = doc.lines[index]
        number = index + 1
        stripped = line.strip()

        if CODE_FENCE_RE.match(line):
            in_fence = not in_fence
            out = flush()
            if out:
                yield out
            block = []
            continue
        if in_fence:
            continue

        skip = (
            not stripped
            or stripped.startswith(("#", "|", ">", "<!--", "---", "==="))
            or re.match(r"^\s{4,}\S", line)
            or re.match(r"^\[[^\]]+\]:", stripped)
        )
        if skip:
            out = flush()
            if out:
                yield out
            block = []
            continue

        item = bool(re.match(r"^\s*([-*+]|\d+\.)\s+", line))
        if item and block:
            out = flush()
            if out:
                yield out
            block = []
        if not block:
            start = number
            is_list = item
        block.append(re.sub(r"^\s*([-*+]|\d+\.)\s+", "", line).strip())

    out = flush()
    if out:
        yield out


def check_sentences(doc, limits, exempt, findings):
    """Sentence and paragraph ceilings, by topic type."""
    if not doc.is_markdown or doc.path in exempt:
        return
    profile = limits.get(doc.topic_type or "concept")
    if not profile:
        return

    instruction_max = profile.get("instruction_max_words")
    descriptive_max = profile.get("descriptive_max_words")
    paragraph_max = profile.get("paragraph_max_sentences")

    for start, is_list, text in iter_prose_blocks(doc):
        clean = strip_markup(text)
        sentences = split_sentences(clean)
        line = doc.lines[start - 1] if start - 1 < len(doc.lines) else ""
        too_many = paragraph_max and not is_list and len(sentences) > paragraph_max
        if too_many and escaped(line, "LEN-02") is not True:
            findings.append(
                (
                    doc.path,
                    start,
                    "LEN-02",
                    WARN,
                    f"paragraph has {len(sentences)} sentences, ceiling is {paragraph_max}",
                )
            )
        for sentence in sentences:
            count = len(sentence.split())
            ceiling = instruction_max if (is_list and instruction_max) else descriptive_max
            if ceiling and count > ceiling:
                if escaped(line, "LEN-01") is True:
                    continue
                findings.append(
                    (
                        doc.path,
                        start,
                        "LEN-01",
                        WARN,
                        (f"sentence is {count} words, ceiling is {ceiling}: {sentence[:60]}..."),
                    )
                )


# --------------------------------------------------------------------------
# Entry point
# --------------------------------------------------------------------------


def main(argv):
    root = run_git("rev-parse", "--show-toplevel").strip()
    if root:
        with contextlib.suppress(OSError):
            os.chdir(root)

    config = load_yaml(BANNED_PHRASES)
    terms = load_yaml(STE_TERMS)

    rules = compile_rules(config) + build_term_rules(terms)
    protected = protected_pattern(terms)
    limits = config.get("sentence_limits", {}) or {}
    exempt = set(limits.get("exempt", []) or [])
    description_rules = config.get("description_rules", {}) or {}

    strict = "--strict" in argv
    files = select_files(argv)

    findings = []
    for path in files:
        try:
            with open(path, encoding="utf-8", errors="replace") as handle:
                text = handle.read()
        except OSError:
            continue
        doc = Document(path, text)
        check_rules(doc, rules, protected, findings)
        check_front_matter(doc, description_rules, exempt, findings)
        check_headings(doc, findings)
        check_sentences(doc, limits, exempt, findings)

    errors = [f for f in findings if f[3] == ERROR or strict]
    warnings = [f for f in findings if f[3] == WARN and not strict]

    for path, number, rule_id, _severity, message in sorted(warnings):
        sys.stdout.write(f"\033[33mwarn\033[0m  {path}:{number}  [{rule_id}]  {message}\n")

    if not errors:
        print(f"[prose] {len(files)} files checked, {len(warnings)} warnings, no errors")
        return 0

    sys.stderr.write("\n\033[31mBLOCKED: documentation standard violations\033[0m\n")
    for path, number, rule_id, _severity, message in sorted(errors):
        sys.stderr.write(f"  {path}:{number}  [{rule_id}]  {message}\n")
    sys.stderr.write(
        f"\nThe rules live in {BANNED_PHRASES} and {STE_TERMS}.\n"
        f"They are explained in docs/DOCUMENTATION-STANDARD.md.\n"
        f"Exempt one line with:  {ESCAPE_TOKEN} <RULE-ID> <reason>\n"
    )
    return 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
