"""Severity as four channels, of which color is only one.

Gate VAL-GATE-A11Y-001 is falsified by "one severity encoded by color alone",
and `docs/design/ui-direction.md` section 6.1 is the owner section that says what
the other channels are: a text label carrying the exact severity, a shape whose
side count carries the ordinal, color for pre-attentive grouping, and position in
the sorted band for relative rank. The rule that interface holds is that removing
any one channel leaves the severity readable, which is stronger than WCAG 1.4.1.

The side counts descend 8, 6, 5, 4, 3 so that more sides means more severe. That
is learnable in one glance at the legend and it survives grayscale print, a
compressed GIF, and `forced-colors: active`, which are the three conditions
section 6.4 says the encoding has to survive.

Section 6.3 adds the second ordering this module owns. The severity enum answers
"how bad" and not "bad at what", so a critical throughput finding and a critical
safety finding render the same word. The finding class is derived from the `kind`
enum and is a presentation ordering only: the severity a producer emitted is
always the severity that renders.
"""

from __future__ import annotations

from dataclasses import dataclass

#: The four channels of section 6.1, in the order that table lists them. Named
#: here so a test can assert the rendered markup carries every one of them
#: rather than counting on a reviewer to remember there are four.
SEVERITY_CHANNELS: tuple[str, ...] = ("text", "shape", "color", "position")


@dataclass(frozen=True)
class SeverityLevel:
    """One severity, with every channel that carries it."""

    name: str
    label: str
    rank: int
    sides: int
    token: str

    @property
    def glyph_id(self) -> str:
        return f"tf-glyph-{self.name}"


#: Rank 1 is the most severe, so the sort key of section 6.3 ascends. The token
#: names match the OKLCH set of section 4.3 exactly, because the stylesheet and
#: this table are two readers of one palette and a rename in one place would
#: render an unstyled blank rather than fail.
SEVERITIES: tuple[SeverityLevel, ...] = (
    SeverityLevel(name="critical", label="CRITICAL", rank=1, sides=8, token="--tf-sev-critical"),
    SeverityLevel(name="high", label="HIGH", rank=2, sides=6, token="--tf-sev-high"),
    SeverityLevel(name="medium", label="MEDIUM", rank=3, sides=5, token="--tf-sev-medium"),
    SeverityLevel(name="low", label="LOW", rank=4, sides=4, token="--tf-sev-low"),
    SeverityLevel(name="info", label="INFO", rank=5, sides=3, token="--tf-sev-info"),
)

SEVERITY_NAMES: tuple[str, ...] = tuple(level.name for level in SEVERITIES)

#: The minimum rendered size of a glyph, in CSS pixels, across the bounding box.
#: Section 6.2 chooses this number in the repository rather than taking it from
#: a published source, and says so: it is the size at which an octagon and a
#: hexagon are still distinguishable at arm's length on a 1080p projector.
MIN_GLYPH_PX = 14


@dataclass(frozen=True)
class FindingClass:
    """One class of finding, and the `kind` values it covers."""

    name: str
    rank: int
    kinds: tuple[str, ...]


#: Section 6.3. Nothing new is published: the class is derived from the existing
#: `kind` enum and belongs to the presentation layer.
FINDING_CLASSES: tuple[FindingClass, ...] = (
    FindingClass(name="safety", rank=1, kinds=("safety",)),
    FindingClass(name="security", rank=2, kinds=("security",)),
    FindingClass(
        name="quality",
        rank=3,
        kinds=(
            "capability_shortfall",
            "msa_failure",
            "process_mining_deviation",
            "sop_violation",
            "spc_violation",
        ),
    ),
    FindingClass(name="reliability", rank=4, kinds=("fleet_health",)),
    FindingClass(name="fidelity", rank=5, kinds=("twin_divergence",)),
    FindingClass(name="other", rank=6, kinds=("other",)),
)

#: The classes whose findings render in the safety band, which is exempt from
#: every reduction of section 7. NUREG-0700 Revision 4 guideline 4.1.2-1 is the
#: reason, and the exemption is capped at one announcement per three seconds so
#: it does not become a denial of service by another route.
BANDED_CLASSES: tuple[str, ...] = ("safety", "security")


def finding_class_for(kind: str) -> FindingClass:
    """The class a finding kind belongs to.

    An unmapped kind falls to `other` rather than raising. A kind added to the
    schema in a later phase should render in the stream with a lower rank, not
    take the panel down; `CT-UI-2` is the check that notices the gap, and it
    belongs in CI rather than in a running dashboard.
    """
    for finding_class in FINDING_CLASSES:
        if kind in finding_class.kinds:
            return finding_class
    return FINDING_CLASSES[-1]


def severity_for(name: str) -> SeverityLevel:
    for level in SEVERITIES:
        if level.name == name:
            return level
    raise KeyError(
        f"severity {name!r} is not one of {', '.join(SEVERITY_NAMES)}; a value present in the "
        f"schema and absent here renders as an unstyled blank, which is what CT-UI-2 exists "
        f"to catch"
    )


def finding_sort_key(
    *,
    kind: str,
    severity: str,
    chattering: bool,
    last_sim_time: int,
    finding_id: str,
) -> tuple[int, int, int, int, str]:
    """The findings stream order of section 6.3.

    `(class_rank, severity_rank, chattering, -last_sim_time, finding_id)`, so a
    medium safety finding sorts above a critical quality finding. That inversion
    is the point and it is why the class word renders in the row beside the
    severity word: the ordering is explained on screen rather than inferred.

    `finding_id` is last so the order is total. Two findings agreeing on every
    other component would otherwise sort by whatever order the stream happened
    to deliver them in, and the list would reshuffle under the reader.
    """
    return (
        finding_class_for(kind).rank,
        severity_for(severity).rank,
        int(chattering),
        -last_sim_time,
        finding_id,
    )
