"""Gate VAL-GATE-A11Y-001, as far as a Python tier can honestly take it.

The gate's assertion has four clauses:

    axe-core reports zero critical and zero serious violations, the demo path is
    completable by keyboard alone, severity is encoded by shape and by text and
    never by color alone, and reduced motion is honored.

Three of them are properties of the shipped document and stylesheet and are
asserted below, each against the rendered markup rather than against a
description of it. The first is not. axe-core is JavaScript and needs a DOM, and
a hand-written subset of its rules would be a subset chosen by the same hand that
wrote the markup, which is the self-reference doctrine D-11 refuses to let a
validation gate rest on. Nothing in this file is evidence for that clause.
`browser/axe-gate.mjs` runs the published rule set unmodified in headless
chromium, which is where that evidence comes from, and README.md says so in the
same words.

Doctrine D-12 is the other constraint these assertions are written against. Each
one below fails on a specific, named change: delete a control and the demo-path
assertion names the step, give two severities the same glyph and the
color-independence assertion names the pair, add a transition with a literal
duration and the reduced-motion assertion names the declaration.
"""

from __future__ import annotations

import re

import pytest

from twinflow.dashboard import (
    DEMO_PATH,
    FOCUS_ORDER,
    MIN_GLYPH_PX,
    MIN_TARGET_PX,
    MOTION_TOKEN_PREFIX,
    REDUCED_MOTION_ATTRIBUTE,
    REDUCED_MOTION_QUERY,
    SEVERITIES,
)

from .conftest import Node, focusables, is_focusable

# ------------------------------------------------------------------- structure


def test_the_document_declares_a_language(dom: Node):
    """WCAG 3.1.1. A screen reader with no language picks its default voice,
    and a German voice reading English severity words is unusable."""
    html = dom.by_tag("html")[0]

    assert html.attrs.get("lang") == "en"


def test_the_page_has_exactly_one_top_level_heading(dom: Node):
    headings = dom.by_tag("h1")

    assert len(headings) == 1
    assert headings[0].all_text()


def test_every_landmark_of_the_frame_is_present_and_in_the_declared_order(dom: Node):
    """Section 10 fixes the tab order as header, safety band, center, left,
    right, footer. A landmark missing from the page would take its whole region
    out of the keyboard path with nothing failing at the time."""
    seen = [node.id for node in dom.walk() if node.id in FOCUS_ORDER]

    assert seen == list(FOCUS_ORDER)


def test_the_center_column_precedes_the_left_column_in_the_dom(dom: Node):
    """The one deliberate divergence between visual order and DOM order. A
    keyboard reader reaches the finding before the picture, and the CSS `order`
    property is what puts the picture on the left at three columns."""
    order = [node.id for node in dom.walk() if node.id in ("tf-left", "tf-center")]

    assert order == ["tf-center", "tf-left"]


def test_the_safety_band_is_its_own_assertive_live_region(dom: Node):
    """Section 6.3. NUREG-0700 Revision 4 guideline 4.1.2-1 asks for exactly
    this exemption, and it is the only region that gets one."""
    band = dom.find("tf-safety-band")

    assert band is not None
    assert band.attrs.get("role") == "region"
    assert band.attrs.get("aria-live") == "assertive"
    assert band.attrs.get("aria-labelledby")
    assert dom.find(band.attrs["aria-labelledby"]) is not None

    others = [
        node.id
        for node in dom.walk()
        if node.attrs.get("aria-live") == "assertive" and node.id != "tf-safety-band"
    ]
    assert others == []


# -------------------------------------------------------------------- keyboard


def test_no_element_carries_a_positive_tabindex(dom: Node):
    """A positive tabindex jumps its element ahead of everything with a natural
    order, so one of them reorders the whole page for a keyboard reader and the
    author of the next element cannot see why."""
    offenders = {
        node.tag: node.attrs["tabindex"]
        for node in dom.walk()
        if "tabindex" in node.attrs and int(node.attrs["tabindex"]) > 0
    }

    assert offenders == {}


def test_the_skip_link_is_the_first_focusable_element(dom: Node):
    """A skip link that is not first is a skip link a keyboard reader reaches
    after the thing it exists to skip."""
    first = focusables(dom)[0]

    assert first.id == "tf-skip-link"
    assert first.attrs.get("href", "").startswith("#")
    assert dom.find(first.attrs["href"][1:]) is not None


@pytest.mark.parametrize("step", DEMO_PATH, ids=lambda step: step.control_id)
def test_every_demo_step_names_a_control_a_keyboard_reaches(dom: Node, step):
    control = dom.find(step.control_id)

    assert control is not None, (
        f"demo step {step.ordinal}, {step.what}, needs a control with id "
        f"{step.control_id!r} and the page has none"
    )
    assert is_focusable(control), (
        f"demo step {step.ordinal}, {step.what}, has a control the tab order does not "
        f"reach: {control.tag} {control.attrs}"
    )


def test_the_demo_path_is_ordered_and_every_step_is_distinct():
    ordinals = [step.ordinal for step in DEMO_PATH]
    controls = [step.control_id for step in DEMO_PATH]

    assert ordinals == sorted(ordinals)
    assert len(set(controls)) == len(controls)


def test_the_findings_stream_is_one_tab_stop_with_roving_focus_inside(dom: Node, script: str):
    """Section 10: the total tab count must not grow with the number of
    findings, so the stream is one stop and the arrow keys move inside it."""
    stream = dom.find("tf-findings")

    assert stream is not None
    assert stream.attrs.get("tabindex") == "0"
    assert stream.attrs.get("aria-label")
    assert "ArrowDown" in script and "ArrowUp" in script


def test_every_interactive_control_has_an_accessible_name(dom: Node):
    """A button whose name is only its background color is a button a screen
    reader announces as "button"."""
    nameless = []
    for node in dom.walk():
        if node.tag not in ("button", "a", "summary"):
            continue
        named = (
            node.all_text()
            or node.attrs.get("aria-label")
            or node.attrs.get("title")
            or node.attrs.get("aria-labelledby")
        )
        if not named:
            nameless.append((node.tag, node.attrs))

    assert nameless == []


def test_every_form_control_is_labeled(dom: Node):
    """WCAG 1.3.1 and 4.1.2. A select with a visible caption beside it and no
    `for` is a control a screen reader announces without its purpose."""
    labelled_ids = {node.attrs["for"] for node in dom.by_tag("label") if "for" in node.attrs}
    wrapped = {
        child.id
        for label in dom.by_tag("label")
        for child in label.walk()
        if child.tag in ("input", "select", "textarea")
    }
    unlabelled = []
    for node in dom.walk():
        if node.tag not in ("input", "select", "textarea"):
            continue
        if node.attrs.get("type") == "hidden":
            continue
        named = (
            node.id in labelled_ids
            or node.id in wrapped
            or node.attrs.get("aria-label")
            or node.attrs.get("aria-labelledby")
            or _is_inside_label(node)
        )
        if not named:
            unlabelled.append((node.tag, node.attrs))

    assert unlabelled == []


def _is_inside_label(node: Node) -> bool:
    parent = node.parent
    while parent is not None:
        if parent.tag == "label":
            return True
        parent = parent.parent
    return False


def test_the_target_size_floor_is_declared_and_applied(stylesheet: str):
    """Section 10: 24 by 24 CSS pixels minimum. Declared once as a token and
    applied through it, so a control added later inherits the floor."""
    assert f"--tf-target: {MIN_TARGET_PX}px" in stylesheet
    assert "min-height: var(--tf-target)" in stylesheet
    assert "min-width: var(--tf-target)" in stylesheet


# ------------------------------------------------- severity, without any color


def _severity_rows(dom: Node) -> dict[str, Node]:
    return {
        node.attrs["data-severity"]: node for node in dom.walk() if "data-severity" in node.attrs
    }


def test_the_legend_renders_every_severity_the_package_declares(dom: Node):
    """CT-UI-2 in the shape this phase can reach. A severity present in the
    table and absent from the page renders as an unstyled blank."""
    rows = _severity_rows(dom)

    assert sorted(rows) == sorted(level.name for level in SEVERITIES)


def test_every_severity_carries_both_a_word_and_a_shape(dom: Node):
    """The two channels that survive when color is gone. Either one missing
    falsifies the gate on its own."""
    for name, row in sorted(_severity_rows(dom).items()):
        words = [
            node.all_text() for node in row.walk() if "tf-sev-word" in node.attrs.get("class", "")
        ]
        polygons = [node for node in row.walk() if node.tag == "polygon"]

        assert words and words[0].strip(), f"{name} has no severity word"
        assert len(polygons) == 1, f"{name} has {len(polygons)} glyph polygons"


def test_no_two_severities_look_alike_once_color_is_removed(dom: Node):
    """The gate is falsified by "one severity encoded by color alone". This is
    that clause as a property: strip the color channel and the five severities
    must still be pairwise distinct on what is left."""
    signatures: dict[str, tuple[str, int]] = {}
    for name, row in sorted(_severity_rows(dom).items()):
        word = next(
            node.all_text() for node in row.walk() if "tf-sev-word" in node.attrs.get("class", "")
        )
        polygon = next(node for node in row.walk() if node.tag == "polygon")
        signatures[name] = (word.strip().upper(), _vertex_count(polygon))

    collisions = [
        (a, b)
        for index, a in enumerate(sorted(signatures))
        for b in sorted(signatures)[index + 1 :]
        if signatures[a] == signatures[b]
    ]

    assert collisions == [], (
        f"these severities are indistinguishable without color: {collisions}. "
        f"Signatures were {signatures}"
    )


def test_the_side_count_ladder_descends_with_severity(dom: Node):
    """Section 6.1: more sides means more severe, which is what makes the ladder
    learnable from the legend in one glance."""
    rows = _severity_rows(dom)
    rendered = [
        _vertex_count(next(node for node in rows[level.name].walk() if node.tag == "polygon"))
        for level in SEVERITIES
    ]

    assert rendered == sorted(rendered, reverse=True)
    assert rendered == [level.sides for level in SEVERITIES]


def test_every_glyph_names_itself_for_a_screen_reader(dom: Node):
    """Section 6.2: inline SVG, `role="img"`, and a `<title>` equal to the text
    label. Without the title the shape is decoration and the word is the only
    channel left, which is the failure this encoding exists to avoid."""
    glyphs = [node for node in dom.walk() if "tf-glyph" in node.attrs.get("class", "")]

    assert len(glyphs) == len(SEVERITIES)
    for glyph in glyphs:
        assert glyph.attrs.get("role") == "img"
        labelled_by = glyph.attrs.get("aria-labelledby")
        assert labelled_by
        title = next(node for node in glyph.walk() if node.tag == "title")
        assert title.attrs.get("id") == labelled_by
        assert title.all_text().strip()


def test_the_glyph_title_is_the_severity_word_the_row_prints(dom: Node):
    """A title that disagreed with the printed word would give a screen reader
    and a sighted reader two different severities for one finding."""
    for name, row in sorted(_severity_rows(dom).items()):
        title = next(node for node in row.walk() if node.tag == "title").all_text().strip()
        word = next(
            node.all_text() for node in row.walk() if "tf-sev-word" in node.attrs.get("class", "")
        ).strip()

        assert title == word, f"{name} announces {title!r} and prints {word!r}"


def test_the_glyph_carries_a_stroke_so_the_shape_survives_forced_colors(stylesheet: str):
    """Section 6.2: `forced-colors: active` replaces fills with system colors,
    so a glyph carried only by its fill loses its shape entirely."""
    assert "stroke: var(--tf-border-strong)" in stylesheet
    assert f"--tf-glyph: {MIN_GLYPH_PX}px" in stylesheet


def test_the_severity_color_is_a_fill_and_never_the_only_declaration(stylesheet: str):
    """Every per-severity rule sets a fill and nothing else. A rule that also
    set the shape would make color and shape one channel rather than two."""
    for level in SEVERITIES:
        rule = re.search(rf"\.tf-glyph-{level.name} polygon \{{(.*?)\}}", stylesheet, flags=re.S)
        assert rule is not None, f"{level.name} has no glyph rule"
        declarations = [part.strip() for part in rule.group(1).split(";") if part.strip()]
        assert declarations == [f"fill: var({level.token})"]


# -------------------------------------------------------------- reduced motion


def _declared_duration_tokens(stylesheet: str) -> set[str]:
    root = re.search(r":root \{(.*?)\n      \}", stylesheet, flags=re.S)
    assert root is not None, "the page declares its tokens on :root"
    return set(re.findall(rf"({re.escape(MOTION_TOKEN_PREFIX)}[a-z-]+):", root.group(1)))


def _block_after(stylesheet: str, marker: str) -> str:
    start = stylesheet.index(marker)
    depth = 0
    for index in range(start, len(stylesheet)):
        if stylesheet[index] == "{":
            depth += 1
        elif stylesheet[index] == "}":
            depth -= 1
            if depth == 0:
                return stylesheet[start : index + 1]
    raise AssertionError(f"unbalanced braces after {marker!r}")


def test_the_page_declares_at_least_one_duration_token(stylesheet: str):
    """Guards the two assertions below from passing vacuously: a stylesheet with
    no tokens satisfies "every token is zeroed" and proves nothing."""
    assert len(_declared_duration_tokens(stylesheet)) >= 5


@pytest.mark.parametrize("marker", [REDUCED_MOTION_QUERY, REDUCED_MOTION_ATTRIBUTE])
def test_every_duration_token_is_zeroed_under_reduced_motion(stylesheet: str, marker: str):
    """Section 9.4: under reduced motion every duration becomes zero, and the
    in-interface preference overrides the operating system in both directions,
    which is why both the media query and the attribute selector are checked."""
    declared = _declared_duration_tokens(stylesheet)
    block = _block_after(stylesheet, marker)
    zeroed = {token for token in declared if re.search(rf"{re.escape(token)}:\s*0m?s\s*;", block)}

    assert declared - zeroed == set(), (
        f"{marker} leaves these durations non-zero: {sorted(declared - zeroed)}"
    )


def test_no_transition_or_animation_carries_a_literal_duration(stylesheet: str):
    """A literal duration is invisible to the reduced-motion block above, so a
    transition written as `150ms` keeps moving after the preference is set. This
    is the assertion that makes the two above mean something."""
    offenders: list[str] = []
    for declaration in re.findall(
        r"(?:transition|animation)(?:-duration)?\s*:\s*([^;]+);", stylesheet
    ):
        without_vars = re.sub(r"var\([^)]*\)", "", declaration)
        if re.search(r"\d+\s*m?s\b", without_vars):
            offenders.append(declaration.strip())

    assert offenders == [], f"these declarations bypass the motion tokens: {offenders}"


def test_the_one_continuous_animation_stops_under_reduced_motion(stylesheet: str):
    """Section 9.3: the conveyor flow is the single exception to the
    no-continuous-motion rule, and it stops entirely under reduced motion."""
    flow = re.search(r"\.tf-flow \{(.*?)\}", stylesheet, flags=re.S)

    assert flow is not None
    assert "var(--tf-duration-flow)" in flow.group(1)
    assert f"{MOTION_TOKEN_PREFIX}flow" in _declared_duration_tokens(stylesheet)


def test_nothing_is_conveyed_only_by_the_flow_animation(dom: Node):
    """Section 9.3: under reduced motion a static arrow marker plus the numeric
    flow rate replaces the animation, so no information lives only in it."""
    plan = dom.find("tf-plan")
    assert plan is not None

    arrows = [node for node in plan.walk() if node.tag == "path" and "fill" in node.attrs]
    rate_text = " ".join(node.all_text() for node in plan.walk() if node.tag == "text")

    assert arrows, "the flow direction needs a static arrow marker"
    assert re.search(r"\d", rate_text), "the flow rate needs a number, not only a speed of dashes"


def test_the_plan_view_has_a_table_equivalent_in_the_panel_toolbar(dom: Node):
    """Section 10: every chart has a table equivalent reachable by a control in
    the panel toolbar, not only from a menu, because that table is the relief
    channel three chart colors depend on."""
    toggle = dom.find("tf-plan-table-toggle")
    table = dom.find("tf-plan-table")

    assert toggle is not None and is_focusable(toggle)
    assert toggle.attrs.get("aria-controls") == "tf-plan-table"
    assert table is not None and table.tag == "table"
    assert table.by_tag("th"), "a table equivalent with no headers is a grid of numbers"


def _vertex_count(polygon: Node) -> int:
    return len([pair for pair in polygon.attrs["points"].split() if pair.strip()])
