"""The accessibility floor of gate VAL-GATE-A11Y-001, written as data.

The gate's assertion has four clauses and they are not equally checkable from
Python. This module states which is which, because doctrine D-11 says a
validation gate needs external evidence and doctrine D-12 says a test that cannot
fail is worse than no test, and the honest thing is to name the boundary rather
than to write a check that looks like it covers all four.

| Clause                            | Where it is checked                             |
|-----------------------------------|-------------------------------------------------|
| Zero critical and serious in axe  | tests/browser/axe-gate.mjs, in a browser        |
| Demo path completable by keyboard | Statically, for reachability and focus order    |
| Severity never by color alone     | Statically, against the rendered markup         |
| Reduced motion honored            | Statically, against the stylesheet              |

The middle two and the last are what this package's pytest tier asserts. The
first needs computed style, layout boxes, and an accessibility tree, so it lives
in a second tier that drives a browser. No Python assertion here is evidence for
it, and none tries to be: a hand-written subset of axe rules is a subset chosen
by the same person who wrote the markup, which is the self-reference D-11
forbids a gate from resting on. The browser tier runs the published rule set
unmodified, which is why it satisfies the clause and a subset would not.

The keyboard clause is split as well, and the split matters. Reachability, focus
order, and the absence of a positive `tabindex` are properties of the document
and are checked here. Completability, meaning that a real keyboard user gets
through every step, is a property of behavior under a real focus model and is
not.
"""

from __future__ import annotations

from dataclasses import dataclass

#: The gate this module serves. Its registry row carries the reference below.
A11Y_GATE_ID = "VAL-GATE-A11Y-001"

#: The published standard the gate names, quoted from its registry row so the
#: two cannot drift.
WCAG_REFERENCE = "Web Content Accessibility Guidelines 2.1, W3C recommendation, level AA."
WCAG_REFERENCE_URL = "https://www.w3.org/TR/WCAG21/"


@dataclass(frozen=True)
class DemoStep:
    """One step of the demo path, and the control a keyboard reaches it by.

    `control_id` is the DOM id of the element that performs the step. Naming it
    is what turns "the demo path is completable by keyboard" from a claim into
    something a test can falsify: delete the control, or hide it from the tab
    order, and the assertion goes red with the step named.
    """

    ordinal: int
    what: str
    control_id: str


#: The path a reader takes through the stub, in order. It is short because the
#: stub is short. Every step a later phase adds belongs here on the same commit
#: as the control it needs, which is what keeps the keyboard assertion honest as
#: the interface grows.
DEMO_PATH: tuple[DemoStep, ...] = (
    DemoStep(1, "jump past the header to the findings stream", "tf-skip-link"),
    DemoStep(2, "read what the synthetic badge claims about this run", "tf-synthetic-badge"),
    DemoStep(3, "change the clock speed", "tf-speed"),
    DemoStep(4, "open the findings stream and move through it", "tf-findings"),
    DemoStep(5, "read the severity legend that explains the glyph ladder", "tf-legend"),
    DemoStep(6, "open the plan view table equivalent", "tf-plan-table-toggle"),
    DemoStep(7, "open the settings dialog and choose reduced motion", "tf-settings"),
)

#: The frame of `docs/design/ui-direction.md` section 5.4, in the tab order
#: section 10 fixes. The center column comes before the left column even though
#: it comes after it visually at three columns, so a keyboard reader reaches the
#: finding before the picture. That divergence is deliberate, it is the one
#: place this interface makes the trade, and a test asserts the DOM order rather
#: than trusting the comment.
FOCUS_ORDER: tuple[str, ...] = (
    "tf-header",
    "tf-safety-band",
    "tf-center",
    "tf-left",
    "tf-right",
    "tf-footer",
)

#: Section 10: 24 by 24 CSS pixels minimum, including the scrubber thumb, the
#: chapter ticks, and the chart hit areas.
MIN_TARGET_PX = 24

#: The custom property every duration in the stylesheet is written through.
#: Section 9.4 sets it to zero under reduced motion, which only reaches a
#: transition that was written as `var(--tf-duration-...)`. A literal duration
#: is invisible to the preference, so the stylesheet has none and a test says so.
MOTION_TOKEN_PREFIX = "--tf-duration-"

#: The media query and the in-interface override, which section 9.4 says work in
#: both directions: the preference in the interface overrides the operating
#: system, and the operating system is honored when the interface has no opinion.
REDUCED_MOTION_QUERY = "@media (prefers-reduced-motion: reduce)"
REDUCED_MOTION_ATTRIBUTE = 'html[data-tf-motion="reduced"]'

__all__ = [
    "A11Y_GATE_ID",
    "DEMO_PATH",
    "FOCUS_ORDER",
    "MIN_TARGET_PX",
    "MOTION_TOKEN_PREFIX",
    "REDUCED_MOTION_ATTRIBUTE",
    "REDUCED_MOTION_QUERY",
    "WCAG_REFERENCE",
    "WCAG_REFERENCE_URL",
    "DemoStep",
]
