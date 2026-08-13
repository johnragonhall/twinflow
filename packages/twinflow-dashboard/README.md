---
title: twinflow-dashboard
description: The single-file dashboard stub, the accessibility floor it is held to, and the part of that floor a Python tier cannot reach.
topic_type: concept
audience: contributors
---

# twinflow-dashboard

One HTML file, served byte for byte off disk. No build step, no npm, no node at
run time. The page reads `twinflow-api` over HTTP from the browser, and this
process serves the file, a bootstrap document, and the one write path the browser
has.

## Install

```bash
pip install twinflow-dashboard
```

## Use

```python
from datetime import UTC, datetime

from twinflow.dashboard import DashboardConfig, create_app

config = DashboardConfig(
    run_id="run_01j...",
    epoch=datetime(2026, 1, 1, tzinfo=UTC),
    api_base_url="http://127.0.0.1:8000",
)
app = create_app(config, clock=lambda: 0)
```

## Routes

| Route          | Method | Notes                                                           |
| -------------- | ------ | --------------------------------------------------------------- |
| `/`            | GET    | `assets/index.html`, unchanged, with a content security policy  |
| `/config.json` | GET    | The deployment facts the page reads on load                     |
| `/healthz`     | GET    | Liveness, plus the sim instant read from the injected clock     |
| `/api/command` | POST   | 202 with the assigned `(producer_id, seq)`, or 422 with reasons |

Nothing is substituted into the HTML at serve time. The browser test tier of the
design page extracts the shipped `<script>` blocks and evaluates them in
`node:vm`, and that only tests the shipped artifact while the file under test is
the file being served.

## Why the API is over HTTP and not an import

Requirement R32: building the dashboard against internal calls and inserting an
API later rewrites every dashboard test. `twinflow.api` and `twinflow.dashboard`
are peers in the `apps` tier of boundary rule A1.2, neither imports the other,
and `tests/test_brick_isolated.py` asserts it from both sides so the rule does not
depend on `.importlinter` having been regenerated.

## Gate VAL-GATE-A11Y-001, and exactly how far this package takes it

The gate asserts four things:

> axe-core reports zero critical and zero serious violations, the demo path is
> completable by keyboard alone, severity is encoded by shape and by text and
> never by color alone, and reduced motion is honored.

| Clause                            | Status in this release                                   |
| --------------------------------- | -------------------------------------------------------- |
| Zero critical and serious in axe  | Not checked. Nothing here is evidence for it             |
| Demo path completable by keyboard | Reachability and focus order checked; completability not |
| Severity never by color alone     | Checked against the rendered markup                      |
| Reduced motion honored            | Checked against the stylesheet                           |

The first row is the important one. axe-core is JavaScript and needs a real DOM,
which the Python unit tier does not have. A hand-written subset of axe rules
would be a subset chosen by the same hand that wrote the markup, and doctrine
D-11 refuses to let a validation gate rest on this repository being a reference
for itself. So no such subset was written, and this package makes no claim about
that clause.

What is checked, and what each check goes red on:

- Every landmark of the frame is present and in the tab order section 10 fixes.
  Remove a region and the assertion names the gap.
- No element carries a positive `tabindex`, and the skip link is the first
  focusable element.
- Every demo step names a control that exists and that the tab order reaches.
  Delete the control or set `tabindex="-1"` and the assertion names the step.
- The five severities stay pairwise distinct once color is removed. Give two of
  them the same glyph and the assertion names the pair.
- Every glyph is `role="img"` with a `<title>` equal to the word the row prints.
- Every duration token is zeroed both by `prefers-reduced-motion: reduce` and by
  the in-interface override, and no transition or animation carries a literal
  duration, so nothing can bypass the preference.
- The one continuous animation, the conveyor flow, stops under reduced motion,
  and its information is also carried by a static arrow and a printed number.

## Contract tests CT-UI-2 and CT-UI-3

Both are three-way checks in the design and this release can carry two of the
three sides: the Python tables here against the hand-written JavaScript in
`index.html`. Neither is generated from the other, so a drift between them is a
real defect and the comparison is not self-reference.

The third side, `/schemas/lss/finding.v1.json` and `/schemas/ui/command/v1.json`,
does not exist yet. Publishing those is outside this package's boundary and is
recorded below.

## Dependencies

`starlette`, `uvicorn`, `pydantic`, `twinflow-schemas`, and nothing else, which
is the list section 2.1 of the design page fixes. No HTTP client: the browser
reads the API and this process serves a file. The test tier adds no dependency
either, driving the ASGI application directly rather than through a client
library built on `httpx`, which pulls the MPL-2.0 `certifi`.

## What the orchestrator still owes this package

- `schemas/ui/command/v1.json` and `schemas/lss/finding.v1.json`, so `CT-UI-2`
  and `CT-UI-3` become the three-way checks the design specifies.
- A browser test tier that can run axe-core, without which the first clause of
  VAL-GATE-A11Y-001 has no evidence.
- An `ACCESSIBILITY.md`, which section 10 of the design page says is where the
  deliberate divergence between visual order and DOM order is recorded.
