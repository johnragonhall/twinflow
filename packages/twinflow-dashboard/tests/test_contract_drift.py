"""Contract tests CT-UI-2 and CT-UI-3, as far as this release can carry them.

`docs/design/dashboard-replay.md` section 4.3 states both as three-way checks.
CT-UI-2 compares the severity enum in `/schemas/lss/finding.v1.json` with the
dashboard's severity table. CT-UI-3 compares the `kind` enum in `ui.command.v1`
with the server's dispatch table and the browser's command builders.

Neither schema exists yet, and README.md records that as owed. What does exist is
two independently maintained artifacts per check: a Python table and a hand-written
JavaScript list inside `index.html`. Comparing those two is not self-reference,
because neither is generated from the other. Editing one and forgetting the other
is the exact defect these contract tests were written to catch, and it is the
defect a hand-written single-file dashboard makes easiest to commit.
"""

from __future__ import annotations

import json
import re

from twinflow.dashboard import COMMAND_NAMES, SEVERITY_NAMES


def _js_array(script: str, name: str) -> list[str]:
    """Read one `TF.<name> = [...]` literal out of the shipped script block."""
    match = re.search(rf"TF\.{name} = (\[.*?\]);", script, flags=re.S)
    assert match is not None, f"the shipped script declares no TF.{name}"
    literal = re.sub(r",(\s*\])", r"\1", match.group(1))
    return json.loads(literal)


def test_the_browser_severity_list_matches_the_server_table(script: str):
    """CT-UI-2, on the two artifacts this repository has today. Most severe
    first in both, because the browser reads the index as the rank."""
    assert _js_array(script, "SEVERITIES") == list(SEVERITY_NAMES)


def test_the_browser_command_builders_match_the_server_dispatch_table(script: str):
    """CT-UI-3, on the same two. A kind the browser can build and the server
    does not know is a 422 the operator sees as a broken button."""
    assert _js_array(script, "COMMANDS") == list(COMMAND_NAMES)


def test_the_browser_refuses_to_build_a_command_the_table_does_not_carry(script: str):
    """The check has to be in the shipped source, not only in this test. A
    browser that posted an unknown kind would learn about it from a 422."""
    assert "unknown command kind" in script


def test_the_browser_class_ranks_agree_with_the_server_ones(script: str):
    """Section 6.3's mapping, mirrored in the page so a row can explain its own
    position. A drift here reorders the findings stream in the browser only,
    which is the hardest kind of disagreement to notice."""
    from twinflow.dashboard import finding_class_for

    match = re.search(r"TF\.CLASS_RANK = \{(.*?)\};", script, flags=re.S)
    assert match is not None
    pairs = dict(re.findall(r"(\w+):\s*(\d+)", match.group(1)))

    mismatched = {
        kind: (int(rank), finding_class_for(kind).rank)
        for kind, rank in sorted(pairs.items())
        if int(rank) != finding_class_for(kind).rank
    }
    assert mismatched == {}


def test_the_browser_mints_command_ids_the_server_accepts(script: str):
    """Section 4.2 fixes the shape at `c-%04d`. The browser builds it and the
    server validates it, and the two are written in different languages."""
    from twinflow.dashboard.commands import COMMAND_ID_PATTERN

    assert 'return "c-" + String(TF.commandCounter).padStart(4, "0")' in script
    assert COMMAND_ID_PATTERN.match("c-0001")
    assert COMMAND_ID_PATTERN.match("c-123456")
    assert not COMMAND_ID_PATTERN.match("c-1")
