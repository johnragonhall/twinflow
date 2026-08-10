---
title: UI direction for the dashboard and the hosted replay
description: The build-step ruling, the OKLCH token set with computed contrast, severity encoding beyond colour, flood behaviour, chart forms, motion, and the vendored-asset licence record.
topic_type: concept
audience: contributors
---

# UI direction for the dashboard and the hosted replay

Status: design direction. It refines the visual and interaction layer of
`docs/design/dashboard-replay.md` and changes none of that page's contracts.
Where the two disagree on a contract, the contract page wins. Where they
disagree on how something looks or behaves at the pixel, this page wins and
names the contract clause it works inside.

Binding doctrine: `docs/design/DOCTRINE.md`.

Evidence discipline: every claim below about a library, a licence, a browser
capability, or a published standard was retrieved with `curl` on 2026-08-09 and
carries its locator and its HTTP status. Section 12 holds the licence record.
Section 15 holds what could not be settled.

Two number classes, kept apart, matching the convention of the contract page. A
number taken from a named external published reference names that reference at
the point of use. A number chosen here says so in the sentence that states it.
No number below borrows authority it does not have.

---

## 1. What this page decides

The contract page fixes the event shapes, the invariants, the test ids, and the
budget gates. It leaves five things open that a reader of the repository judges
in the first ninety seconds.

| Open question from the contract page                                            | Decided here |
| ------------------------------------------------------------------------------- | ------------ |
| Whether "single-file, no build step" survives contact with a striking interface | Section 2    |
| What the tokens are, in OKLCH, with contrast computed rather than asserted      | Section 4    |
| What a reader sees first, second, and third                                     | Section 5    |
| What the findings stream does when it saturates                                 | Section 7    |
| Which chart forms carry which questions                                         | Section 8    |

---

## 2. The build-step decision

### 2.1 The contradiction, stated plainly

Component 8 of the source requirements says the dashboard is "single-file, no
build step". A component library of the kind a reader expects in 2026, React
plus a Radix-based kit plus a motion library, needs a bundler, a package
manager, and a compile step. Both statements cannot hold. One of them has to be
argued away rather than quietly dropped.

### 2.2 The three candidates

| Option                             | What it is                                                                                                          | What it buys                                                                                            | What it costs                                                                                                     |
| ---------------------------------- | ------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------- |
| 1. Keep single-file, no build      | Hand-written HTML, modern CSS, vanilla JS, using platform features that did not exist when the rule became folklore | The quickstart never breaks, the shipped source is the tested source, one viewer serves live and replay | About fifty components are hand-written, including a virtualised grid and roving focus                            |
| 2. Build step, vendored components | React plus a component kit plus a motion library, bundled                                                           | Faster component delivery, a familiar stack on a resume                                                 | The quickstart grows a toolchain, the tested source stops being the shipped source, node enters the runtime story |
| 3. Split                           | No-build live dashboard, built static replay viewer for Pages                                                       | Each artifact optimised for its host                                                                    | Two viewers to keep in sync, and the artifact most readers see stops being the artifact the repository runs       |

### 2.3 The decision

Option 1 wins, with one true observation taken from option 3 and the rest of
option 3 refused.

Option 2 loses on a mechanism the contract page already relies on. Section 5.2
of that page runs the browser unit tier by extracting the shipped `<script>`
blocks out of `index.html` and evaluating them in `node:vm`. That works because
a classic script is a plain string of source. A bundle is not: the tier would
test a compiled artifact and the repository would lose the property that the
file under test is the file on disk. Section 5.14.5 then measures the quickstart
end to end with a wall-clock budget of 300 seconds. Adding a frontend toolchain
puts an install between clone and first finding, and a five-minute claim that
depends on an npm cache is a claim about the reader's network.

Option 3 loses on drift, which is the exact failure section 5.1 of the contract
page exists to prevent. That section makes the live dashboard and the hosted
replay the same file behind two seams, `TF.transport` and `TF.clock`. The
consequence stated there is that every panel added in a later phase appears in
the public demo for free. Splitting the two gives that up and creates a second
codebase whose accessibility gates, visual-regression goldens, and severity
table all have to be kept honest twice. The artifact most readers ever open
would stop being evidence about the system the repository runs, which
is the whole reason E1 is worth building.

The true half of option 3 is that the Pages site is a separate deployment with
different platform capabilities. That half is already honoured. Section 5.2.2 of
the contract page ships two content security policies, because a static host
cannot set a response header. Section 5.11.1 loads the query engine lazily
from the site's own origin. Those are deployment differences, not a second
viewer.

### 2.4 What the decision costs, stated without softening

Every item below is a real cost of choosing option 1, and none of them is
recovered later.

- Roughly fifty interface elements are hand-written. Section 12 counts them.
- Two of them are genuinely hard rather than tedious: a virtualised grid that
  keeps `aria-rowcount` honest at 500 devices, and roving focus across the plan
  view, the fleet table, and the findings list. That cost is real whatever the
  architecture. The seven prior vendoring passes in the owner's research
  repository cover several hundred components and record no virtualisation
  implementation at all. Option 2 would have bought a component kit and still
  left this to hand.
- Spring physics is unavailable without a motion library, so motion is CSS
  transitions plus the Web Animations API. Section 9 shows that the motion this
  interface wants is a small set of short, linear-to-decelerate moves, so the
  loss is small, but it is a loss.
- Browser code carries no compile-time type check. The mitigation is the
  property tier in section 7.2 of the contract page plus JSDoc annotations
  checked by `tsc --checkJs` as a test-only tool. That is weaker than a typed
  build and this page does not pretend otherwise.
- Review cost per component is higher, because a hand-written combobox is a
  correctness surface that a vendored one has already paid for.

### 2.5 What the reader gains

- `git clone && docker compose up -d && just seed-demo` reaches a rendered
  finding with no package manager involved. The claim is measured by `BG-QS-1`,
  not promised.
- The dashboard has zero third-party origins at runtime, asserted by `BG-CSP-1`,
  which is what makes the strict content security policy in section 5.2.2
  enforceable rather than aspirational.
- One file is auditable. A reader who wants to know what the page does opens it
  and reads it.
- The live dashboard and the public demo are provably the same code, so a
  hiring manager who runs docker sees what the demo showed them.

### 2.6 `shadcn` is out, and that is a decision

The design council lists `shadcn` as conditional on this ruling. The ruling went
to no build, so `shadcn` is the wrong tool here and is not used. Its component
inventory still informs section 12: the list of elements a serious product
interface needs is worth reading even when the delivery mechanism differs.

### 2.7 The platform features the decision rests on

The claim that a no-build page can be a good interface in 2026 is checkable, so
it is checked. Every row below comes from the Web Platform Status API on
2026-08-09, `https://api.webstatus.dev/v1/features/<id>`, HTTP 200 for each.
Baseline "widely" means the feature has been interoperable across the core
browser set for at least thirty months by that project's own definition.

| Feature                    | Baseline status | Baseline low date | Baseline high date | Used here for                                                        |
| -------------------------- | --------------- | ----------------- | ------------------ | -------------------------------------------------------------------- |
| `dialog`                   | widely          | 2022-03-14        | 2024-09-14         | Shortcut help, first-run overlay, shelve dialog, focus trap for free |
| `container-queries`        | widely          | 2023-02-14        | 2025-08-14         | Panels that adapt to their column, not to the viewport               |
| `subgrid`                  | widely          | 2023-09-15        | 2026-03-15         | Findings row fields aligned across rows without a fixed table        |
| `nesting`                  | widely          | 2023-12-11        | 2026-06-11         | One style block per panel, no preprocessor                           |
| `has`                      | widely          | 2023-12-19        | 2026-06-19         | Row state driven by descendant state, no class bookkeeping in JS     |
| `forced-colors`            | widely          | 2022-09-12        | 2025-03-12         | Windows high contrast, required by the contract page section 5.12.1  |
| `light-dark`               | newly           | 2024-05-13        | not yet            | Two themes from one declaration, with a fallback path                |
| `text-wrap-balance`        | newly           | 2024-05-13        | not yet            | Panel headings and the verdict caveat, progressive                   |
| `popover`                  | newly           | 2025-01-27        | not yet            | Grounding chips, filter menus, progressive over a scripted fallback  |
| `view-transitions`         | newly           | 2025-10-14        | not yet            | Panel and view swaps, progressive, off under reduced motion          |
| `scroll-driven-animations` | limited         | not yet           | not yet            | Refused. Section 9 says why                                          |
| `anchor-positioning`       | limited         | not yet           | not yet            | Refused. Popover placement is computed in script instead             |

Two rules follow from the split in that table. A feature at "widely" carries
structure and may be depended on. A feature at "newly" or below carries polish
only, behind `@supports` or a capability check, and the page is complete without
it. `T-PROGRESSIVE-1` is proposed in section 14 to hold that line.

---

## 3. The design council and where it disagreed

### 3.1 How disagreements were resolved

The precedence ladder from `docs/superpowers/plans/_EXECUTION-PROTOCOL.md`
section 6a applies, highest first: correctness of the signal, the accessibility
floor, legibility under load, information hierarchy, visual distinction, then
motion. Tier 5 is a real requirement and loses to tiers 1 through 4.

### 3.2 The disagreements worth recording

| Conflict                   | Position A                                                                                                          | Position B                                                                                              | Winner and why                                                                                                       |
| -------------------------- | ------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------- |
| What leads the eye         | Visual hierarchy work argues for the plan view, because it is the picture and it is what a screenshot sells         | Nielsen visibility of system status and the brief argue for the findings stream and the bottleneck      | B, on tier 4. The plan view is large but sits left and reads recessive. Section 5.4 places it                        |
| How many things stand out  | The isolation effect allows exactly one differentiated element per region, and says a second one destroys the first | The brief names two centres, the findings stream and the bottleneck                                     | Both, resolved by region. One isolation per container, never two inside one container. Section 5.5                   |
| Severity colour saturation | Aesthetic usability argues that a saturated palette reads as more competent and tests as more usable                | Control-room practice reserves saturation for the abnormal state                                        | B, on tier 1. A resting screen that is already colourful gives an abnormal colour nothing to say                     |
| Chart colour authority     | The repository standing rule is OKLCH, generated, never eyeballed                                                   | The `dataviz` method requires a documented, validated categorical palette and forbids invented values   | Both. The validated palette is adopted and expressed in OKLCH. Section 8.2 shows the run                             |
| Motion budget              | Portfolio instinct wants entrance motion on panels so the demo GIF feels alive                                      | Motion-audit practice frequency-gates continuous and decorative motion off high-frequency work surfaces | B, on tier 3. Motion means change here. Section 9                                                                    |
| Density                    | Responsive practice wants generous spacing at large sizes                                                           | A control room at a wall display wants more data, not more air                                          | Split by distance. A density multiplier grows spacing with viewing distance, not with pixel count alone. Section 4.5 |

### 3.3 Platform guidance, and what was taken from it

The dashboard is a browser surface on no vendor platform, so neither Apple Human
Interface Guidelines nor Windows Fluent is a contract here, and this page makes
no conformance claim to either. Three things were taken because they are human
factors rather than platform convention.

- Minimum pointer target size. The contract page already adopts WCAG 2.2 SC
  2.5.8 at 24 by 24 CSS pixels as a voluntary addition above its 2.1 target.
- Motion duration and easing ranges. Short entrances with a decelerating curve,
  exits faster than entrances, and opacity-only changes shortest of all.
  Section 9 states the numbers as choices made here.
- Reduced motion and increased contrast as operating-system settings a browser
  surface honours whatever platform it runs on.

Nothing about window chrome, title bars, control metrics, or platform iconography
is taken, because none of it applies to a page served over HTTP.

---

## 4. Visual direction

### 4.1 The look, in one paragraph

An instrument, not a poster. A neutral field at rest, thin strokes, hairline
rules, tabular numerals, and a single accent hue reserved for focus. Colour
enters when something is abnormal, and it leaves when the abnormality clears.

The visual interest comes from density done well. A plan view that is a real
scale drawing of the configured facility. A findings stream that stays readable
at forty rows a minute. A verdict card that a statistician cannot fault.
That is the distinction this repository is competing on. A gradient hero would
compete with every other portfolio instead.

The one deliberate flourish is the severity glyph set. Five polygons with
descending side counts, drawn as inline SVG, doubling as the 3D halo ring
segment count. It is decoration that carries information, which is the only kind
this interface has room for.

### 4.2 Why colour is reserved

NUREG-0700 Revision 4, Human-System Interface Design Review Guidelines, published
January 2026 by the United States Nuclear Regulatory Commission, is a free and
current primary source for control-room human factors. It was retrieved as a PDF
on 2026-08-09 from `https://www.nrc.gov/docs/ML2602/ML26022A094.pdf`, HTTP 200,
5,043,444 bytes, 622 pages. Guideline 1.3.8-10, Redundant Color Coding, reads:
"Color coding should be redundant with some other display feature". Its
additional information reads: "Displayed information should be sufficient even
when viewed on a monochromatic display terminal or hardcopy printout, or when
viewed by a user with color vision impairment."
<!-- docs-lint-ok STE-01 verbatim quotation of the published source -->

That document is written for nuclear control rooms and this is a warehouse twin.
It is a source of human-factors guidance rather than a conformance target, and
no gate in this repository claims conformance to it. Three of its guidelines
change decisions here and each is cited where it lands: 1.3.8-10 in section 6,
1.3.8-13 in section 4.4, and 4.1.2-1 and 4.1.2-2 in section 7.

### 4.3 The token set, in OKLCH, with contrast computed

Four token sets, selected by `data-theme` and `data-contrast` on `<html>`,
exactly the shape section 6.4 of the contract page requires. Every value is
OKLCH. Every value below was fitted to the sRGB gamut by reducing chroma only,
never lightness, so the hue and the lightness relationships survive the fit.

Contrast ratios are computed, not estimated. The method is the WCAG relative
luminance formula applied to the sRGB conversion of each OKLCH triple. The
converter was self-checked against the two published triples in CSS Color Module
Level 4 section 7. `oklch(0.452 0.313 264.1)` reproduces `#0100FF` against a
published `#0000FF`, and `oklch(0.968 0.211 109.8)` reproduces `#FFFF01` against
a published `#FFFF00`. Both sit inside one 8-bit step, which is the precision
the published three-decimal triples support. Ratios are reported truncated to two
decimals, so a computed 4.4999 reads as 4.49 and fails rather than rounding into
a pass.

#### 4.3.1 Light, normal contrast

| Token                | OKLCH                    | sRGB      | Contrast check      | Ratio     |
| -------------------- | ------------------------ | --------- | ------------------- | --------- |
| `--tf-bg`            | `oklch(0.985 0.004 250)` | `#F8FAFD` | reference surface   | n/a       |
| `--tf-bg-raised`     | `oklch(1.000 0.000 250)` | `#FFFFFF` | reference surface   | n/a       |
| `--tf-bg-sunken`     | `oklch(0.945 0.006 250)` | `#EAEDF1` | reference surface   | n/a       |
| `--tf-fg`            | `oklch(0.250 0.020 250)` | `#1A222B` | on `--tf-bg`        | 15.31     |
| `--tf-fg-muted`      | `oklch(0.500 0.020 250)` | `#5B646F` | on `--tf-bg`        | 5.73      |
| `--tf-fg-inverse`    | `oklch(0.990 0.000 250)` | `#FCFCFC` | on severity fills   | see 4.3.5 |
| `--tf-border`        | `oklch(0.860 0.012 250)` | `#CBD2D9` | decorative only     | n/a       |
| `--tf-border-strong` | `oklch(0.610 0.018 250)` | `#7B848E` | on `--tf-bg-sunken` | 3.22      |
| `--tf-focus`         | `oklch(0.520 0.192 258)` | `#0162D4` | on `--tf-bg`        | 5.43      |
| `--tf-sev-critical`  | `oklch(0.420 0.170 27)`  | `#94020D` | on `--tf-bg-raised` | 9.23      |
| `--tf-sev-high`      | `oklch(0.460 0.104 62)`  | `#804804` | on `--tf-bg-raised` | 7.34      |
| `--tf-sev-medium`    | `oklch(0.650 0.130 92)`  | `#AC8C0E` | on `--tf-bg-raised` | 3.24      |
| `--tf-sev-low`       | `oklch(0.500 0.130 248)` | `#0B67A9` | on `--tf-bg-raised` | 5.97      |
| `--tf-sev-info`      | `oklch(0.540 0.020 250)` | `#66707A` | on `--tf-bg-raised` | 5.04      |
| `--tf-ok`            | `oklch(0.520 0.130 150)` | `#1D7D3E` | on `--tf-bg-raised` | 5.18      |
| `--tf-warn`          | `oklch(0.580 0.122 75)`  | `#A46E01` | on `--tf-bg-raised` | 4.37      |
| `--tf-stale`         | `oklch(0.580 0.020 250)` | `#727C86` | on `--tf-bg-raised` | 4.27      |

#### 4.3.2 Light, more contrast

Same key set, every key present. Text pairs reach 9.29 or better, non-text pairs
4.33 or better.

| Token                | OKLCH                    | sRGB      | Contrast check      | Ratio |
| -------------------- | ------------------------ | --------- | ------------------- | ----- |
| `--tf-bg`            | `oklch(1.000 0.000 250)` | `#FFFFFF` | reference surface   | n/a   |
| `--tf-bg-raised`     | `oklch(0.975 0.004 250)` | `#F5F7F9` | reference surface   | n/a   |
| `--tf-bg-sunken`     | `oklch(0.930 0.008 250)` | `#E4E8ED` | reference surface   | n/a   |
| `--tf-fg`            | `oklch(0.160 0.020 250)` | `#070E16` | on `--tf-bg`        | 19.40 |
| `--tf-fg-muted`      | `oklch(0.380 0.020 250)` | `#3B434D` | on `--tf-bg`        | 9.99  |
| `--tf-border-strong` | `oklch(0.480 0.020 250)` | `#555F69` | on `--tf-bg-sunken` | 5.02  |
| `--tf-focus`         | `oklch(0.420 0.154 258)` | `#02489F` | on `--tf-bg`        | 8.70  |
| `--tf-sev-critical`  | `oklch(0.360 0.146 27)`  | `#780108` | on `--tf-bg-raised` | 11.02 |
| `--tf-sev-high`      | `oklch(0.400 0.092 60)`  | `#6B3903` | on `--tf-bg-raised` | 8.87  |
| `--tf-sev-medium`    | `oklch(0.590 0.120 90)`  | `#997902` | on `--tf-bg-raised` | 4.33  |
| `--tf-sev-low`       | `oklch(0.440 0.124 250)` | `#015493` | on `--tf-bg-raised` | 7.34  |
| `--tf-sev-info`      | `oklch(0.480 0.020 250)` | `#555F69` | on `--tf-bg-raised` | 6.03  |

#### 4.3.3 Dark, normal contrast

The dark background is not black. `oklch(0.205 0.014 250)` keeps a projector
image from crushing every dark value into the same shadow, and it keeps a bright
room from turning the screen into a mirror.

| Token                | OKLCH                    | sRGB      | Contrast check      | Ratio     |
| -------------------- | ------------------------ | --------- | ------------------- | --------- |
| `--tf-bg`            | `oklch(0.205 0.014 250)` | `#262C33` | reference surface   | n/a       |
| `--tf-bg-raised`     | `oklch(0.255 0.014 250)` | `#31383F` | reference surface   | n/a       |
| `--tf-bg-sunken`     | `oklch(0.165 0.014 250)` | `#1D2228` | reference surface   | n/a       |
| `--tf-fg`            | `oklch(0.950 0.008 250)` | `#EEF1F5` | on `--tf-bg`        | 15.48     |
| `--tf-fg-muted`      | `oklch(0.745 0.014 250)` | `#A5AEB8` | on `--tf-bg`        | 7.91      |
| `--tf-fg-inverse`    | `oklch(0.180 0.010 250)` | `#20262C` | on severity fills   | see 4.3.5 |
| `--tf-border`        | `oklch(0.360 0.016 250)` | `#4B535B` | decorative only     | n/a       |
| `--tf-border-strong` | `oklch(0.550 0.020 250)` | `#727C86` | on `--tf-bg-raised` | 3.14      |
| `--tf-focus`         | `oklch(0.800 0.140 240)` | `#5EC6FF` | on `--tf-bg-raised` | 8.42      |
| `--tf-sev-critical`  | `oklch(0.640 0.190 27)`  | `#E64F45` | on `--tf-bg-raised` | 4.24      |
| `--tf-sev-high`      | `oklch(0.780 0.150 62)`  | `#F79C3F` | on `--tf-bg-raised` | 7.44      |
| `--tf-sev-medium`    | `oklch(0.860 0.140 92)`  | `#F2CE55` | on `--tf-bg-raised` | 10.14     |
| `--tf-sev-low`       | `oklch(0.720 0.120 248)` | `#63A9EA` | on `--tf-bg-raised` | 6.13      |
| `--tf-sev-info`      | `oklch(0.680 0.020 250)` | `#909AA5` | on `--tf-bg-raised` | 5.36      |

#### 4.3.4 Dark, more contrast

| Token                | OKLCH                    | sRGB      | Contrast check      | Ratio |
| -------------------- | ------------------------ | --------- | ------------------- | ----- |
| `--tf-bg`            | `oklch(0.145 0.012 250)` | `#181D22` | reference surface   | n/a   |
| `--tf-bg-raised`     | `oklch(0.205 0.012 250)` | `#262C33` | reference surface   | n/a   |
| `--tf-fg`            | `oklch(0.990 0.004 250)` | `#FBFCFE` | on `--tf-bg`        | 19.23 |
| `--tf-fg-muted`      | `oklch(0.830 0.012 250)` | `#C4CBD3` | on `--tf-bg`        | 11.73 |
| `--tf-border-strong` | `oklch(0.620 0.020 250)` | `#828C97` | on `--tf-bg-raised` | 4.92  |
| `--tf-focus`         | `oklch(0.880 0.130 240)` | `#88DDFF` | on `--tf-bg-raised` | 12.21 |
| `--tf-sev-critical`  | `oklch(0.700 0.180 27)`  | `#FA6A5C` | on `--tf-bg-raised` | 6.19  |
| `--tf-sev-high`      | `oklch(0.840 0.140 62)`  | `#FFB05E` | on `--tf-bg-raised` | 9.29  |
| `--tf-sev-medium`    | `oklch(0.920 0.120 92)`  | `#FFE28C` | on `--tf-bg-raised` | 12.88 |
| `--tf-sev-low`       | `oklch(0.780 0.110 248)` | `#7DBCF7` | on `--tf-bg-raised` | 8.40  |
| `--tf-sev-info`      | `oklch(0.740 0.020 250)` | `#A3ADB8` | on `--tf-bg-raised` | 7.61  |

#### 4.3.5 The label colour on each severity fill

A severity chip carries its text label on the fill, so the pair is a text
contrast case at 4.5 rather than a non-text case at 3.

| Severity | Light: label token | Light ratio | Dark: label token | Dark ratio |
| -------- | ------------------ | ----------- | ----------------- | ---------- |
| critical | `--tf-fg-inverse`  | 8.97        | `--tf-fg-inverse` | 5.09       |
| high     | `--tf-fg-inverse`  | 7.14        | `--tf-fg-inverse` | 8.94       |
| medium   | `--tf-fg`          | 4.93        | `--tf-fg-inverse` | 12.19      |
| low      | `--tf-fg-inverse`  | 5.81        | `--tf-fg-inverse` | 7.36       |
| info     | `--tf-fg-inverse`  | 4.90        | `--tf-fg-inverse` | 6.44       |

Light-mode `medium` is the only fill that takes dark text, and that is not an
accident of tuning. Against a near-white surface a fill has to sit at OKLCH
lightness at or below about 0.55 to carry white text at 4.5, and at or above
about 0.62 to carry dark text at 4.5. The band between is unusable for a filled
chip. Amber at usable chroma sits above the band, so it takes dark text, which
is also what a painted plant floor does.

#### 4.3.6 A lightness ladder, so greyscale still separates

The five severity lightness values are pairwise distinct with a minimum gap of
0.04 OKLCH lightness in all four token sets. Shape and text carry the ordinal
meaning, so the ladder is not required to be monotone in rank, and it is not.
Its job is that a monochrome print or a failing projector still resolves five
distinct greys.

| Token set           | Lightness ladder, ascending                                |
| ------------------- | ---------------------------------------------------------- |
| light.normal        | critical 0.42, high 0.46, low 0.50, info 0.54, medium 0.65 |
| light.more_contrast | critical 0.36, high 0.40, low 0.44, info 0.48, medium 0.59 |
| dark.normal         | critical 0.64, info 0.68, low 0.72, high 0.78, medium 0.86 |
| dark.more_contrast  | critical 0.70, info 0.74, low 0.78, high 0.84, medium 0.92 |

### 4.4 Two colour hazards the dark theme has to answer

NUREG-0700 Revision 4 guideline 1.3.8-13, Chromostereopsis, states that
"Simultaneous presentation of both pure red and pure blue on a dark background
should be avoided". The two focus at different depths and appear to sit on
different planes.
<!-- docs-lint-ok STE-01 verbatim quotation of the published source -->
The dark findings stream shows `critical` red beside `low` blue on a dark field,
which is that arrangement in outline. The answer is chroma. In OKLCH the sRGB
primaries are `oklch(0.628 0.258 29.2)` for red and `oklch(0.452 0.313 264.1)`
for blue, the second matching the published value in CSS Color Module Level 4
section 7 exactly. The dark tokens sit at chroma 0.190 and 0.120, which is 74
percent and 38 percent of the corresponding primary. Neither is a pure primary
and the depth artifact needs pure primaries to appear at strength.

Guideline 1.3.8-12 states that red and green "should not be used in combination"
where avoidable.
<!-- docs-lint-ok STE-01 verbatim quotation of the published source -->
No severity token is green in any set. Green appears only as `--tf-ok`, a device
health state, and it never shares a row with `--tf-sev-critical`, because a
device with an open critical finding renders the finding severity and not the
health colour.

### 4.5 Type, spacing, and density

Type. Inter for the interface and numerals, JetBrains Mono for code, SQL, hashes,
and the tool trace. Both are variable fonts under SIL Open Font License 1.1,
subset to Latin, digits, and punctuation. Both are embedded as base64 inside
`index.html`, inside the 60 KB share of the 400 KB file budget that section 5.2
of the contract page sets aside. Section 12 records both licences.

The scale is a fixed ramp rather than a fluid clamp. A fluid scale makes a
visual-regression golden depend on viewport width, and the golden set in section
7.5 of the contract page is what keeps this interface honest.

| Step             | Size      | Line height | Use                                          |
| ---------------- | --------- | ----------- | -------------------------------------------- |
| `--tf-text-2xs`  | 0.6875rem | 1.0rem      | Axis ticks, badge text, sim-time-ago         |
| `--tf-text-xs`   | 0.75rem   | 1.125rem    | Table cells, chip labels, tool trace         |
| `--tf-text-sm`   | 0.8125rem | 1.25rem     | Findings row body, panel toolbars            |
| `--tf-text-base` | 0.875rem  | 1.375rem    | Default interface text, chat transcript      |
| `--tf-text-lg`   | 1.0rem    | 1.5rem      | Panel headings                               |
| `--tf-text-xl`   | 1.25rem   | 1.625rem    | Bottleneck station name, verdict conclusion  |
| `--tf-text-2xl`  | 1.75rem   | 2rem        | The one measured headline number on the card |

`font-variant-numeric: tabular-nums` applies to table cells, axis ticks, the sim
clock, and every findings-row numeral, so columns of numbers align and a value
that changes does not shift its neighbours. It does not apply to the verdict
card's headline figure, where equal-width digits make a three-digit number read
loose at display size.

Measure. The findings row title is capped at 72 characters, and the chat
transcript column at 68 characters, both enforced with `ch` units so the cap
follows the font rather than a pixel guess. Above the cap, the title truncates
with a tooltip and the full text stays in the detail drawer, so nothing is lost.

Spacing. A 4-pixel base scale, multiplied by a density token.

```css
:root { --tf-density: 1; }
@media (min-width: 2560px) { :root { --tf-density: 1.25; } }
@media (min-width: 3840px) { :root { --tf-density: 1.5; } }
```

The multiplier keys on viewport width as a proxy for viewing distance, which is
the honest version of the rule. A 4K panel on a desk wants the same density as a
laptop, so the settings menu carries a density override and it persists. That
override is the reason the media query is allowed to be a guess.

Elevation. A panel is separated from the page by a hairline border and a
background step, never by a drop shadow. Shadow is reserved for the three things
that genuinely float: the dialog set, the popover layer, and the drag ghost in
the panel-reorder interaction. A control room read at an angle loses soft
shadows entirely, so nothing structural depends on one.

---

## 5. Information architecture

### 5.1 The first five seconds

A reader who looks at one screenshot has to come away with four facts, in this
order, from a single vertical scan of the centre column.

1. This is synthetic data. The `SYNTHETIC` badge is in the header, is not
   dismissible, and is in every frame of every capture.
2. Something is wrong, and how badly. The top of the findings stream carries the
   highest-ranked open finding, with its severity glyph, its severity word, and
   its class word.
3. Where the constraint is. The bottleneck card names one station, gives the
   method that identified it, and gives the evidence numbers.
4. The system is running, and at what speed. The sim clock shows requested and
   achieved compression when they differ.

Nothing else competes for that scan. The repository name sits at 0.875rem in the
header, at `--tf-fg-muted`, and there is no logo.

### 5.2 The ninety-second path

| Second   | What the reader does                                    | What the interface has to make easy                                                                                                     |
| -------- | ------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------- |
| 0 to 10  | Reads the header and the top of the findings stream     | Severity legible without a legend, synthetic badge unmissable                                                                           |
| 10 to 25 | Looks at the plan view and finds the bottleneck station | The bottleneck marker is a heavy dashed outline plus the word, visible without hover                                                    |
| 25 to 45 | Opens one finding                                       | The drawer shows the control chart with the violating points marked by shape and the rule id spelled out                                |
| 45 to 70 | Reads the agent answer for the recorded question        | Every numeral wears a grounding chip, and the tool trace opens in one click                                                             |
| 70 to 90 | Reaches the what-if verdict card                        | The statistical block is complete: test, assumption checks, statistic, p, alpha, effect size with its name, interval, both sample sizes |

The verdict card is the last frame of the demo GIF for the same reason it ends
this path. It is the single screenshot that carries the thesis.

### 5.3 The deep path

For the reader who interrogates every choice, each of these is reachable and
each ends in evidence rather than in an assertion.

- A finding leads to its evidence window, then to the rule documentation, then
  to the validation gate that checks the rule against a published reference.
- The bottleneck leads to the constraint timeline, then to the sim time when the
  constraint moved, then to a seek in replay mode or a historian window in live
  mode.
- An agent numeral leads to its `result_id`, then to the tool call, then to the
  query, then to the raw result.
- A metric on the query panel leads to the SQL that produced it, executed in the
  reader's own browser, with the number and the SQL shown together.
- Any panel leads to its table equivalent, which is the same data rather than a
  summary.

### 5.4 The frame

Three columns above 1200 CSS pixels, two below 1200, one below 760. Column
behaviour is driven by container queries so a panel moved between columns adapts
to its column rather than to the window.

| Region                                    | Contents                                                                         | Why here                                                     |
| ----------------------------------------- | -------------------------------------------------------------------------------- | ------------------------------------------------------------ |
| Header, full width                        | Run identity, synthetic badge, sim clock, speed control, stream health, settings | Persistent facts that frame every other reading              |
| Safety band, full width, under the header | Open findings of class safety or security, never collapsed, never scrolled away  | Section 6.3                                                  |
| Left column, about 34 percent             | Plan view, then the fleet table                                                  | The picture, recessive by treatment, present for orientation |
| Centre column, about 40 percent           | Bottleneck card, then the findings stream, which takes the remaining height      | The two things the brief puts at the centre                  |
| Right column, about 26 percent            | Agent chat, then the what-if card and the approval strip                         | The narrative surface, read after the state is understood    |
| Footer strip                              | Audit strip, last five config changes with actor                                 | Present without competing                                    |

At two columns the right column moves under the centre. At one column the order
becomes header, safety band, bottleneck, findings, plan view, fleet, chat. The
findings stream never drops below the fold on any width, which is the one
ordering rule that does not bend.

### 5.5 The one thing that stands out, per region

The isolation effect only works when a single element deviates. Two competing
highlights cancel. The resolution is one isolation per container, and never two
inside one container.

| Container        | The one isolated element                          | How it is isolated                                                                                           |
| ---------------- | ------------------------------------------------- | ------------------------------------------------------------------------------------------------------------ |
| Plan view        | The bottleneck station                            | Heavy dashed outline, the word BOTTLENECK, a distinct glyph. Every other station is a hairline rectangle     |
| Findings stream  | The top-ranked open finding                       | A 3-pixel leading rail in its severity token, plus a raised background step. Rows below carry a 1-pixel rail |
| Safety band      | Nothing, because the band itself is the isolation | The band exists only when it is non-empty, and its presence is the signal                                    |
| Agent transcript | The what-if verdict card                          | It is a card rather than a bubble, with a border and its own background                                      |
| Header           | The synthetic badge                               | The only filled element in a row of text                                                                     |

Isolation inflation is the failure mode. A gate is proposed in section 14:
`T-ISOLATION-1` counts elements carrying the isolation class per container and
fails on more than one.

---

## 6. Severity encoding that is not colour alone

### 6.1 Four channels, all four always present

The contract page section 5.12.1 fixes colour, shape, and text. This page adds
position as a fourth channel and states what each one is for.

| Channel                            | Carries                                              | Fails alone when                                                              |
| ---------------------------------- | ---------------------------------------------------- | ----------------------------------------------------------------------------- |
| Text label                         | The exact severity, unambiguously                    | The reader is glancing rather than reading                                    |
| Shape, by side count 8, 6, 5, 4, 3 | The ordinal, learnably: more sides means more severe | Low vision, small render, or a compressed GIF                                 |
| Colour                             | Fast pre-attentive grouping                          | Colour vision deficiency, greyscale print, forced colors, a failing projector |
| Position, the sorted band          | Relative rank against everything else on screen      | The list is filtered or grouped                                               |

The rule the interface holds is that removing any one channel leaves the severity
readable. That is what NUREG-0700 guideline 1.3.8-10 asks for and it is stronger
than WCAG 1.4.1, which only forbids colour as the sole channel.

### 6.2 What the glyph is

Inline SVG, `role="img"`, a `<title>` equal to the text label, a stroked polygon
with a filled interior at the severity token, and a stroke at
`--tf-border-strong` so the shape survives `forced-colors: active` where fills
are replaced by system colours. No icon font, no emoji. Minimum rendered size 14
CSS pixels across the bounding box, which is the size at which an octagon and a
hexagon are still distinguishable at arm's length on a 1080p projector, a number
chosen here.

### 6.3 Safety outranks throughput, and the interface shows it

The severity enum answers "how bad", and it does not answer "bad at what". A
critical throughput finding and a critical safety finding both render CRITICAL,
and treating them as equals is a design defect rather than a display defect.

A `finding_class` is derived from the existing `kind` enum. Nothing new is
published; the mapping is a view-model derivation and belongs to the presentation
layer.

| Class       | Rank | `kind` values it covers                                                                             |
| ----------- | ---- | --------------------------------------------------------------------------------------------------- |
| safety      | 1    | `safety`                                                                                            |
| security    | 2    | `security`                                                                                          |
| quality     | 3    | `spc_violation`, `capability_shortfall`, `msa_failure`, `sop_violation`, `process_mining_deviation` |
| reliability | 4    | `fleet_health`                                                                                      |
| fidelity    | 5    | `twin_divergence`                                                                                   |
| other       | 6    | `other`                                                                                             |

Four consequences, and each is visible rather than implied.

The sort key for the findings stream is
`(class_rank, severity_rank, chattering, -last_sim_time, finding_id)`, so a
medium safety finding sorts above a critical quality finding. The class word
renders in the row beside the severity word, so the ordering is explained on
screen rather than inferred.

A finding of class safety or security renders in the safety band, a full-width
region under the header that exists only when it is non-empty. The band is not
collapsible, does not scroll, and is exempt from every reduction in section 7.
Guideline 4.1.2-1 of NUREG-0700 Revision 4 is the reason it is exempt. Alarms
that "indicate a threat to plant critical safety functions" have to be
"presented in a manner that supports rapid detection and understanding under all
alarm loading conditions".
<!-- docs-lint-ok STE-01 verbatim quotation of the published source -->

Shelving a safety-class finding needs a second confirmation naming the class,
and the shelf badge shows safety shelves as a separate count that never folds
into the total.

The class rank is a presentation ordering and never a severity rewrite. The
severity the producer emitted is what renders. `P-CLASS-ORDER` is proposed in
section 14 to assert that the rendered severity of a row always equals the
producer's value whatever its class.

### 6.4 What survives each removal

| Condition                                       | What still works                                                                                                       |
| ----------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------- |
| Greyscale print                                 | Glyph shape, text label, sorted position, and five distinct greys from the lightness ladder                            |
| Protanopia, deuteranopia, tritanopia            | Glyph shape, text label, position. Colour separability is budgeted by `BG-SEP-1` and not claimed as a standards result |
| `forced-colors: active`                         | Glyph geometry and stroke, text label, position. Fill colour is replaced by the system                                 |
| 12-frame-per-second GIF at GitHub content width | Text label at the 11-pixel floor `BG-GIF-1` sets, and the glyph at its 14-pixel floor                                  |
| Screen reader                                   | Text label first in the accessible name, then the class, then the entity, then the rule                                |

---

## 7. Alarm flood behaviour

### 7.1 What the interface is defending against

The contract page section 5.6.3 already carries the case. At Texaco Milford
Haven on 24 July 1994, two operators had 275 alarms to handle in the eleven
minutes before the explosion. The normal-operation target that sheet gives is
one alarm every ten minutes. That is the shape `E2E-DASH-2` reproduces at lower amplitude.

NUREG-0700 Revision 4 section 4.1.2 gives the processing taxonomy this interface
renders. Its four classes are nuisance processing, redundant processing,
significance processing, and alarm generation processing. The twinflow alarm
manager already does three of them under different names, and naming the mapping
is worth more than inventing a vocabulary.

| NUREG-0700 class | The twinflow mechanism                                 | Where the reader sees it                                                             |
| ---------------- | ------------------------------------------------------ | ------------------------------------------------------------------------------------ |
| Nuisance         | Chatter detection, and suppression by design in config | `CHATTERING` badge with a transition count, and a separate suppressed-by-design list |
| Redundant        | Dedupe on `AlarmKey` inside the dedupe window          | The `x7` count with a first and last sim time on one row                             |
| Significance     | Severity rank, class rank, and per-role rate metering  | Sort order, the safety band, and the alarm rate meter                                |
| Alarm generation | Not implemented, and not claimed                       | Recorded in section 15                                                               |

### 7.2 The saturation ladder

Five states. Each one names its trigger, what changes, and what does not.

| State                | Trigger                                             | What changes                                                                                                                             | What never changes                                          |
| -------------------- | --------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------- | ----------------------------------------------------------- |
| Normal               | Role rate below `target_rate_per_10min`             | Nothing. Rows arrive, the newest highlights for one step and settles                                                                     | Ingest counting, `V9` conservation                          |
| Busy                 | Role rate at or above target, below flood threshold | The rate meter leaves its target band and shows the count. Arrival highlight shortens                                                    | Announcement policy, sort order                             |
| Flood                | Role rate at or above `flood_threshold_per_10min`   | Banner naming the role and the counts. List switches to server-supplied groups. Assertive announcements stop and a summary replaces them | The safety band, the ungrouped toggle, every count          |
| Render saturation    | More than 120 row mutations in one animation frame  | The stream renders a ranked head of 50 rows plus a live tail counter reading "and N more, ranked below". Scrolling loads further pages   | The store applies every envelope. The tail counter is exact |
| Transport saturation | `stream.control.v1` reports overflow                | The stream health strip shows coalesced and dropped counts per producer. Findings are in `never_drop` so none are lost                   | No `never_drop` schema is dropped, per `P-COALESCE-LATEST`  |

The 120-mutation figure and the 50-row head are chosen here, not taken from any
source. They come from the 8-millisecond scripting budget `BG-PERF-1` sets for
the workstation leg. A findings row is about 14 DOM nodes, and 120 rows is the
point at which a full re-render stops fitting. `BG-FLOOD-1` is proposed in
section 14. It measures the real number on the reference runner and moves the
constant to what was measured.

### 7.3 Ranking, which is the part that decides what a human reads

Under saturation the head of the stream is the only part most readers see, so
what reaches it is the whole design.

Rank key, highest first: class rank, then severity rank, then stability, where a
chattering finding sorts below a stable one of the same severity, then recency
by `last_sim_time`, then `finding_id` for a total order. Every element is a
sorted comparison and no element is a set, so the head is identical between two
runs of the same seed, which is what makes a golden screenshot of a flood
possible.

Grouping is the server's decision and the browser renders it. A group shows its
member count, its severity histogram as five stacked segments with a 2-pixel
surface gap, and its highest-ranked member as the group's own row. Collapsing is
a browser-side view state that resets on a run change.

### 7.4 Shelving, and the rule that keeps it honest

Guideline 4.1.3-2 of NUREG-0700 Revision 4 states that when suppression is used
"the user should be able to access the alarm information that is not displayed".
<!-- docs-lint-ok STE-01 verbatim quotation of the published source -->
Four interface rules follow.

- The shelf badge shows a count at all times and renders "0 shelved" rather than
  hiding at zero, so the control is discoverable before it is needed.
- A shelf entry carries a mandatory reason, an actor, and a live countdown.
- Expiry returns the finding with a `RETURNED FROM SHELF` marker rather than
  silently.
- Suppression by design is a separate list from operator shelving, with the
  config path that caused it, because the two have different owners and
  collapsing them hides who decided what.

### 7.5 Keeping focus stable while the list moves under it

A list that reorders while a keyboard user has focus inside it is the defect this
interface is most likely to ship, because it only appears under load and never in
a screenshot. Rows arrive, ranks change, and the row a reader was reading moves
or is pushed off the rendered head.

The prior vendoring passes covered seven accounts and several hundred components,
and none of them records a solution to this. Two transferable primitives do
appear in that corpus and both are used here.

The first is announcement politeness, taken from the way a well-built toast
system informs a screen reader through a live region rather than by moving focus.
Nothing in the findings stream ever calls `focus()` in response to an arriving
envelope. Arrival is announced, never focused.

The second is active descendant, taken from the way an accessible combobox keeps
DOM focus on one element while the announced position moves through a list. The
findings stream container holds DOM focus and carries `aria-activedescendant`
pointing at the current row. A row that reorders or unmounts therefore cannot
take focus with it, because focus was never on the row.

Three rules complete it, and all three are this document's own design rather than
anything read from a source.

Row identity is `finding_id` and nothing else. A row keeps its DOM node across a
rank change, so the reader's active descendant survives a reorder.

Reordering pauses while focus is inside the list. Arriving and re-ranked rows
queue, and a persistent control at the top of the list reads "N updates paused,
press R to resume", with the count live. This is the hover-pause idea applied to
the keyboard, and it is what stops the list from moving under a reader who is
reading it. The pause releases on blur, and it never applies to the safety band,
which is exempt from every reduction in this section.

The paused queue is a view-level hold and never a store-level one. Every envelope
still applies, every count is still exact, and `V9` conservation still holds. A
paused reader is behind on rendering, never behind on facts.

Section 12.8 records where the two primitives came from. Section 15 records what
is still open about the pause.

### 7.6 What the reader is never allowed to lose

Under every state above, four things hold. The ingest count equals the sum of
row counts. Every row has exactly one placement. The ungrouped list stays one
control away. The safety band renders in full.

---

## 8. Charts

The `dataviz` method was applied before any chart form was chosen, in its stated
order: form, then colour by job, then validate, then marks, then interaction,
then the accessibility pass.

### 8.1 Form by question

| Question the reader has                     | Form                                                                                      | Why not something else                                              |
| ------------------------------------------- | ----------------------------------------------------------------------------------------- | ------------------------------------------------------------------- |
| Is this process in statistical control      | Individuals and moving-range control chart, violations marked by shape                    | A line chart with no limits cannot answer it                        |
| Can this process meet its specification     | Histogram with specification limits and a fitted curve overlay                            | A capability index alone hides bimodality and truncation            |
| Which few causes carry most of the findings | Pareto chart, bars descending with a cumulative line on the same axis, indexed to percent | A pie cannot be read in rank order                                  |
| Where does the value stream lose time       | Value stream map, a horizontal process chain with a value-add and wait timeline beneath   | A bar chart of stage times loses the sequence, which is the point   |
| Where has the constraint been               | Constraint timeline, a horizontal band chart, one row per station, one band per interval  | A line chart of utilisation does not answer where the constraint is |
| Is this device trending                     | Sparkline, no axes, one endpoint value labelled                                           | A full chart in a table row is unreadable at 500 rows               |
| Where am I in the recorded shift            | Scrubber with a chapter track marking findings, agent turns, and constraint shifts        | A bare range input hides the structure of the run                   |
| What is this one number                     | Stat tile, no plot                                                                        | A one-bar bar chart is the number with extra ink                    |

The Pareto chart is the one form with a documented hazard. A Pareto normally
draws bars on a count axis and a cumulative line on a percent axis, which is a
dual-axis chart, and dual axes are the method's first refusal. The resolution is
to index the bars to percent of total on the same axis as the cumulative line,
so both marks read against one scale. The raw counts stay in the tooltip and in
the table view. That is a real deviation from the conventional Pareto and it is
recorded here rather than shipped quietly.

### 8.2 The categorical series palette, validated

The repository standing rule is OKLCH and generated colour. The `dataviz` method
requires a documented palette validated by its own script rather than values
chosen by eye. Both hold at once. The method's documented eight-slot categorical
palette is adopted as the series ramp and converted to OKLCH for declaration. It
is then re-validated against twinflow's own surfaces, which is what the method's
palette file instructs a consumer to do.

The validator was run on 2026-08-09 against `--tf-bg-raised` in each theme.

| Run                       | Surface   | Lightness band              | Chroma floor                 | Worst adjacent CVD | Worst adjacent normal vision | Contrast                    |
| ------------------------- | --------- | --------------------------- | ---------------------------- | ------------------ | ---------------------------- | --------------------------- |
| light, adjacent pairs     | `#FFFFFF` | pass, all 8 in 0.43 to 0.77 | pass, all 8 at or above 0.10 | 9.1, protanopia    | 19.6                         | relief required for 3 slots |
| dark, adjacent pairs      | `#31383F` | pass, all 8 in 0.48 to 0.67 | pass, all 8 at or above 0.10 | 8.4, protanopia    | 19.3                         | relief required for 1 slot  |
| light, all pairs, first 3 | `#FFFFFF` | pass                        | pass                         | 9.2, deuteranopia  | 24.0                         | relief required for 1 slot  |
| dark, all pairs, first 3  | `#31383F` | pass                        | pass                         | 9.4, deuteranopia  | 20.9                         | pass, all 3 at or above 3:1 |

Two consequences.

The relief rule is satisfied by construction rather than by a promise. Three
light-mode slots sit below 3:1 on white, and the method's relief for that is
visible direct labels or a table view. Section 5.12.6 of the contract page
already requires a table equivalent for every chart, so the relief channel exists
before the palette needs it.

Scatter, bubble, and small-multiple forms carry a hard cap of three series,
because only the first three slots clear the all-pairs floors. Past three the
chart facets or folds a tail into "Other". No fourth colour is generated, ever.

| Slot | Hue     | Light, OKLCH               | Dark, OKLCH                |
| ---- | ------- | -------------------------- | -------------------------- |
| 1    | blue    | `oklch(0.575 0.163 255.5)` | `oklch(0.622 0.161 255.1)` |
| 2    | orange  | `oklch(0.671 0.175 40.6)`  | `oklch(0.622 0.173 40.1)`  |
| 3    | aqua    | `oklch(0.669 0.141 162.1)` | `oklch(0.621 0.128 163.1)` |
| 4    | yellow  | `oklch(0.764 0.161 75.1)`  | `oklch(0.670 0.143 73.2)`  |
| 5    | magenta | `oklch(0.716 0.141 357.4)` | `oklch(0.622 0.171 0.8)`   |
| 6    | green   | `oklch(0.529 0.180 142.5)` | `oklch(0.529 0.180 142.5)` |
| 7    | violet  | `oklch(0.433 0.167 283.6)` | `oklch(0.670 0.145 286.8)` |
| 8    | red     | `oklch(0.623 0.191 24.9)`  | `oklch(0.669 0.159 22.3)`  |

Sequential encoding, for the utilisation heat layer and the ergonomics layer,
takes one hue and steps lightness. The blue ramp runs from
`oklch(0.905 0.041 252.8)` at the light end to `oklch(0.338 0.103 256.9)` at the
dark end, thirteen steps. An ordinal use starts no lighter than
`oklch(0.764 0.097 253.2)` on a light surface, so the lightest mark still clears
2:1.

Diverging encoding, for a counterfactual comparison of two runs, takes blue
against red with a neutral grey midpoint, `oklch(0.952 0.004 91.4)` on light and
`oklch(0.340 0.005 106.7)` on dark. A hue at the midpoint is refused, because the
midpoint has to read as nothing.

Status colour is reserved and never doubles as a series. The severity tokens in
section 4.3 are the status scale here, and a chart series never wears one. Where
a series genuinely means good or bad, such as a pass rate, it wears the status
token and no categorical slot is assigned to it.

### 8.3 Axis, legend, and tooltip rules

Axes and gridlines are solid hairlines at `--tf-border`, one step off the
surface, never dashed. Dashing is reserved for two meanings in this interface and
both are load-bearing: a control limit, and a specification limit.

The y axis starts at zero for any bar or area form. A line form may use a
non-zero baseline, and when it does the axis carries an explicit break marker and
the baseline value is labelled.

A legend is present whenever a chart carries two or more series. A single-series
chart has no legend box, because the panel heading names the series. At four
series or fewer the series are also direct-labelled at their endpoint, so
identity is never colour alone. A number is never printed on every point.

Tooltips add to a chart and never gate it. Every value in every chart is reachable from
the table equivalent, and keyboard focus on a mark shows the same content hover
shows. Hit areas are at least 24 by 24 CSS pixels even where the mark is an
8-pixel dot, and the dense scatter in the capability view uses a nearest-point
layer rather than exact hit testing.

Filters sit in one row above everything they scope, never inside a chart card,
so every chart in a panel re-renders against the same slice.

On refetch the previous render holds at reduced opacity. There is no skeleton
flash and no layout jump, because a jumping panel in a monitoring interface reads
as a state change.

### 8.4 The four charts that carry the thesis

The control chart. Points as 3-pixel dots on a 1.5-pixel line, centre line
solid at `--tf-fg-muted`, control limits dashed at `--tf-border-strong`,
specification limits dashed at `--tf-warn` when present. A violating point is
drawn as a filled square rather than a dot and is ringed with a 2-pixel surface
ring. It carries the rule id as a direct label at the first violation in each
run of them. The rule id is text, so the reason is readable without the legend.

The capability histogram. Bars in slot 1, specification limits as dashed
verticals with their labels, and the fitted normal curve as a 1.5-pixel line in
`--tf-fg-muted`. The out-of-specification tails are filled at `--tf-sev-high`,
with a texture available under the accessibility setting. The capability indices
render as a stat tile beside the chart, never as an annotation floating inside
the plot.

The constraint timeline. One row per station, bands drawn where that station was
the constraint, all bands in slot 1, because this is one series over time and not
eight categories. The current constraint's band is the isolated element in this
container and carries a 2-pixel outline. Clicking a band seeks the replay.

The verdict card. Not a chart. Section 5.8.1 of the contract page fixes every
number's formatting. This page adds two things. The conclusion renders as text
plus the section 6.2 glyph. The confidence interval draws as a horizontal
interval mark, with the point estimate as an 8-pixel dot and zero marked by a
hairline. The reader sees whether the interval crosses zero without reading two
numbers.

---

## 9. Motion

### 9.1 The rule

Motion in this interface means a change in the system. Anything that moves
without a state change behind it teaches the reader to stop looking, which is
the failure that makes a real alarm invisible. Continuous, ambient, and
decorative motion is refused outright on the dashboard, which is the frequency
gate a motion audit applies to a high-frequency work surface.

### 9.2 What moves

| Element                   | Motion                                                                   | Duration                 | Easing                        | Reason it is allowed                                               |
| ------------------------- | ------------------------------------------------------------------------ | ------------------------ | ----------------------------- | ------------------------------------------------------------------ |
| A finding arriving        | Background highlight fades from the severity token to the row background | 400 ms                   | linear                        | It marks the one thing that changed                                |
| Rank change in the stream | Row translates to its new position                                       | 150 ms                   | decelerate                    | Without it the reader loses the row                                |
| Panel open or close       | Height and opacity                                                       | 150 ms in, 100 ms out    | decelerate in, accelerate out | Preserves the reader's spatial model                               |
| Dialog and drawer         | Opacity plus a 8-pixel translate                                         | 150 ms                   | decelerate                    | Signals a layer change                                             |
| Conveyor flow             | Dashed stroke offset                                                     | continuous while running | linear                        | The only continuous motion, and it encodes flow direction and rate |
| Sparkline update          | Last point moves, line redraws in place                                  | 100 ms                   | linear                        | It is the data moving                                              |
| Alarm rate meter          | Needle or bar moves to the new rate                                      | 250 ms                   | decelerate                    | The rate is the message                                            |
| Speed or seek change      | Playhead moves                                                           | immediate                | none                          | A lagging playhead would be a lie about sim time                   |
| Theme change              | View transition across the whole page                                    | 200 ms                   | decelerate                    | Progressive only, per section 2.7                                  |

### 9.3 What does not move

Panel entry on load, number counters ticking up, skeleton shimmer, hover lifts on
cards, parallax anything, background gradients, particle fields, marquee strips,
and typewriter reveal on the agent's answer. The last one is worth naming. A
token-by-token reveal is standard in chat interfaces and is refused here. The
recorded transcript is not being generated, and animating it would imply live
inference that the replay viewer does not do.

The conveyor flow animation is the single exception to the no-continuous-motion
rule, and it is bounded twice. It stops above 4x clock speed because it stops
being readable, and it stops entirely under reduced motion, where a static arrow
marker plus the numeric flow rate replaces it. No information lives only in that
animation.

### 9.4 Reduced motion

`prefers-reduced-motion: reduce` sets `--tf-motion: 0`, and the in-interface
motion preference overrides the operating system in both directions. Under
reduced motion every duration above becomes zero. The arrival highlight becomes a
single static step that persists for 3 seconds of sim time and then clears. Rank
changes redraw without translation, and view transitions do not run at all.

Nothing conveyed by motion is lost. The arrival highlight has a static form, flow
direction has an arrow and a number, and a camera move in the 3D view becomes a
cut.

---

## 10. Accessibility

The conformance target, the criterion list, the live-region policy, the keyboard
map, and the manual screen-reader procedure are fixed by section 5.12 of the
contract page and are not restated. Six additions follow from decisions on this
page.

The safety band is its own live region, `role="region"` with
`aria-labelledby` pointing at its heading and `aria-live="assertive"`. It is the
only region exempt from the flood announcement policy, because guideline 4.1.2-1
asks for exactly that exemption. Its announcement rate is capped at one per 3
seconds like any other assertive region, so the exemption does not become a
denial of service by another route.

Focus order follows the frame in section 5.4: header, safety band, centre column,
left column, right column, footer. The centre column comes before the left
column in the tab order even though it comes after it visually at three columns.
That is a deliberate divergence between visual order and DOM order, and it is the
one place this interface makes that trade. The reason is that a keyboard reader
reaches the finding before the picture. It is recorded in
`ACCESSIBILITY.md` rather than left for a reviewer to find.

The findings stream is one tab stop with roving focus inside, so the total tab
count does not grow with the number of findings. Under render saturation the
roving range covers the rendered head, and moving past the last rendered row
loads the next page rather than trapping.

Every chart has a table equivalent reachable by a control in the panel toolbar,
not only from a menu, because that table is the relief channel three chart colours
depend on.

The density override, the theme, the contrast, and the motion preference all live
in one settings dialog, all persist in `localStorage`, and none of them enters
`ViewStateCanonical`, per section 3.1.1 of the contract page.

Target size is 24 by 24 CSS pixels minimum, including the scrubber thumb, the
chapter ticks, and the chart hit areas. The chapter ticks are the hardest case,
because a dense run puts many of them close together. The answer is that a
tick's hit area is 24 pixels wide while its visual mark is 2 pixels, and
overlapping hit areas resolve to the nearest tick centre.

---

## 11. The replay viewer

Most readers never run docker, so this artifact is the one that is judged. It is
the same `index.html` in replay mode, per section 5.1 of the contract page.

### 11.1 What it shows

The same panels the live dashboard shows, driven by recorded frames. Four things
differ and each says so on screen rather than pretending.

- The clock is browser-owned, so the speed control moves the reader's playhead
  rather than a simulator.
- Live-only commands are refused with a labelled message naming the reason.
- The agent transcript is recorded, and free-text input either matches a recorded
  question or says that it did not.
- The query panel executes real SQL over the recorded run's Parquet aggregates in
  the reader's own browser, and shows the SQL beside the number.

### 11.2 How it scrubs

The scrubber is a native `<input type="range">` with `aria-valuetext` carrying
the formatted sim time, which gives keyboard and screen-reader support without
a custom widget. Above it sits a chapter track, a hairline rail with a tick per
finding, agent turn, and constraint shift. Each tick is coloured by its severity
token, shaped by its kind, and carries an accessible name.

Seek cost is bounded by the `SEEK-1` algorithm at one keyframe plus one chunk
whatever the distance travelled, so dragging the scrubber across an eight-hour
shift is not a different operation from stepping one frame. While a chunk is in
flight the viewer shows an explicit buffering state and never stalls silently.

Keyboard: the map in section 5.9 of the contract page applies unchanged, and the
scrubber adds arrow keys for one frame, page keys for one chapter, and Home and
End for the run bounds.

The first frame renders paused with a visible play control, which satisfies WCAG
2.2.2 without a special case and is checked by `VAL-GATE MOTION-1`.

The scrubber and the chapter track have no prior art in the corpus section 12.3
describes. None of the seven vendoring passes records a scrubber, a transport
control, or a seek bar of any kind. That is worth stating because it means this
element is specified from the requirement rather than from a pattern, and a
reviewer has nothing to compare it against except a media player.

### 11.3 The size budget

Three budgets, and all three are numbers chosen by this repository rather than
taken from a source.

| Budget              | Value                                                  | What it covers                                          | Existing gate               |
| ------------------- | ------------------------------------------------------ | ------------------------------------------------------- | --------------------------- |
| Viewer file         | 400 KB uncompressed, of which 60 KB is the font subset | `index.html` alone                                      | `T-SIZE-1`                  |
| First paint payload | 1.2 MB transferred                                     | `index.html` plus manifest plus keyframe 0 plus chunk 0 | `BG-FIRSTPAINT-1`, proposed |
| Full bundle         | 25 MiB gzipped for an eight-hour shift                 | Every chunk, keyframe, and media file                   | `BG-BUNDLE-1`               |
| Query engine        | measured, no ceiling until three releases exist        | DuckDB-Wasm on first query only                         | `BG-BUNDLE-4`               |

The 1.2 MB first-paint figure is derived from the 3-second first-frame budget
`BG-LOAD-1` already sets under 4x CPU throttling. The link speed assumed is
about 5 megabits per second, which is the slow-link case that budget was chosen
for. `BG-FIRSTPAINT-1` measures the transferred bytes rather than trusting the
derivation. If the measurement disagrees, the budget moves to the measurement.

The reason the budget is reachable at all is the delta encoding in section 4.4.1
of the contract page, plus one rule this page adds. The viewer fetches chunk 0
and keyframe 0, renders, then prefetches two chunks ahead of the playhead. It
never waits for the whole bundle, so bundle size affects how long a reader can
watch rather than how long they wait.

---

## 12. Component inventory

### 12.1 Three statuses, and why the third one is not a NOTICE entry

Every item below carries one of three statuses, and each has a different legal
consequence.

| Status      | Meaning                                                                         | NOTICE entry | Provenance header                                 |
| ----------- | ------------------------------------------------------------------------------- | ------------ | ------------------------------------------------- |
| Vendored    | The file is in the tree, verbatim, under a compatible licence                   | Required     | Required                                          |
| Adapted     | Compatible licence, in the tree, modified rather than copied                    | Required     | Required, and it states that the file was changed |
| Inspiration | Incompatible or unverified licence, or incompatible architecture. No code taken | None         | None. The credit lives here only                  |

Apache License 2.0 section 4(b) is why Adapted differs from Vendored: a modified
file has to "carry prominent notices stating that You changed the files".
Section 4(d) is why the first two need a `NOTICE` entry at all. Both retrieved
from `https://www.apache.org/licenses/LICENSE-2.0.txt`, HTTP 200, 2026-08-09.
<!-- docs-lint-ok STE-01 verbatim quotation of the licence text -->

Inspiration credits stay out of `NOTICE` on purpose. `NOTICE` describes what the
distribution contains. Listing a source there whose code is not in the tree would
state something untrue in the one file whose job is to be accurate about the
contents.

### 12.2 What the licence rules are, applied outbound

twinflow is Apache-2.0 outbound with a commercial option, which is a stricter
filter than an inbound-only reading gives.

| Inbound licence                         | Ruling here                                                                                                                               |
| --------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------- |
| MIT, BSD-2, BSD-3, ISC, Apache-2.0, CC0 | Vendorable, with a provenance header and a NOTICE line each                                                                               |
| MPL-2.0                                 | File-level copyleft. Acceptable as a development dependency. Any shipped file would be a separate per-file decision, and none is proposed |
| AGPL-3.0, GPL-3.0                       | Not vendorable. Network and strong copyleft would relicense the whole work. Inspiration status only                                       |
| No licence file, or NOASSERTION         | Not vendorable. No licence means all rights reserved. Inspiration status only                                                             |
| Proprietary, non-OSI                    | Not vendorable. Inspiration status only, and only where its terms permit reading                                                          |

Two carve-outs recorded in the prior vendoring passes are honoured here. Fluent
font and icon assets are not covered by the `microsoft/fluentui` MIT licence and
are listed under a separate asset licence, so no Fluent font or icon is proposed
anywhere in this document. Magic UI Pro is a paid product that exists in no
public repository, and nothing from it is proposed; only the free MIT registry is
referenced, and then as inspiration.

### 12.3 The corpus is inspiration by architecture, not by licence

The seven completed vendoring passes in the owner's private research repository
cover roughly 550 vendored files, with licences read from LICENSE files at pinned
commits rather than assumed. Most of that corpus is MIT and would be vendorable
under the rules above.

It is still inspiration here, and the reason is architecture rather than licence.
Every repository in those passes is React plus Tailwind, several assume Next.js,
and the whole corpus presumes a build step. Section 2 ruled that out. A React
component cannot be vendored into a single hand-written HTML file, and rewriting
one by hand is not vendoring: it produces a new file that owes the original
nothing but the idea.

That is the honest outcome and this document does not bend either way to avoid
it. The architecture was chosen on its own merits in section 2, before the corpus
was consulted. What the corpus contributes is a list of problems worth solving
and states worth handling, which is worth recording and costs nothing.

### 12.4 Counts

| Category                  | Hand-written | Vendored | Adapted | Total |
| ------------------------- | ------------ | -------- | ------- | ----- |
| Shell and chrome          | 12           | 0        | 0       | 12    |
| Data display              | 14           | 0        | 0       | 14    |
| Findings and alarms       | 9            | 0        | 0       | 9     |
| Charts                    | 8            | 0        | 0       | 8     |
| Agent and what-if         | 7            | 0        | 0       | 7     |
| State, empty, and failure | 6            | 0        | 0       | 6     |
| 3D view                   | 2            | 1        | 0       | 3     |
| Query panel               | 2            | 1        | 0       | 3     |
| Typeface                  | 0            | 2        | 0       | 2     |
| Test-only tooling         | 0            | 1        | 0       | 1     |
| Totals                    | 60           | 5        | 0       | 65    |

Twelve inspiration sources sit alongside those 65 items and contribute no code.
Section 12.8 lists them.

Of the five vendored items, three ship inside a published artifact, one ships
only on the Pages site and only on first query, and one never ships at all.
Nothing carries the Adapted status, because nothing third-party is modified in
the tree.

### 12.5 Hand-written elements

| Element                        | Region   | Note                                                     |
| ------------------------------ | -------- | -------------------------------------------------------- |
| App shell grid                 | Shell    | Container queries, three to one column                   |
| Skip link                      | Shell    | First focusable element                                  |
| Run identity strip             | Shell    | Seed, config hash, profile, mode                         |
| Synthetic badge                | Shell    | Not dismissible, counts physical devices                 |
| Sim clock readout              | Shell    | Requested and achieved compression                       |
| Speed preset group             | Shell    | `aria-pressed`, presets from config                      |
| Step controls                  | Shell    | Label follows mode                                       |
| Stream health strip            | Shell    | Gaps and coalescing per producer                         |
| Settings dialog                | Shell    | Theme, contrast, motion, density, palette, shortcuts     |
| Shortcut help dialog           | Shell    | Lists every registered panel                             |
| First-run overlay              | Shell    | Focus trapped, remembered                                |
| Panel frame                    | Shell    | Heading, landmark, toolbar, table toggle, mnemonic badge |
| Plan view SVG                  | Data     | Stations, edges, levels, presentation attributes only    |
| Station rectangle              | Data     | Focusable, state glyph, WIP, utilisation bar             |
| Edge polyline                  | Data     | Flow marker, rate label                                  |
| Bottleneck marker              | Data     | Dashed outline plus word plus glyph                      |
| Station detail drawer          | Data     | Opens from plan view or table                            |
| Fleet table                    | Data     | Virtualised grid, `aria-rowcount` honest                 |
| Filter chip bar                | Data     | Reflected into the URL fragment                          |
| Device badge                   | Data     | Physical, edge tier, certificate expiry                  |
| Table equivalent view          | Data     | Every chart has one                                      |
| Data grid row expander         | Data     | Loads sparkline and last five findings                   |
| Sortable column header         | Data     | Three-state, announced                                   |
| Pagination and tail counter    | Data     | Exact count under saturation                             |
| Stat tile                      | Data     | The number is the chart                                  |
| Audit strip                    | Data     | Last five config changes with actor                      |
| Severity chip                  | Findings | Glyph plus label plus class word                         |
| Severity glyph set             | Findings | Five polygons, side counts 8 to 3                        |
| Findings row                   | Findings | Rail, chip, entity, rule, title, count, times            |
| Findings group                 | Findings | Member count, severity histogram, top member             |
| Safety band                    | Findings | Never collapsed, never scrolled away                     |
| Alarm rate meter               | Findings | Target band and flood line marked                        |
| Flood banner                   | Findings | Names the role and both counts                           |
| Shelf drawer                   | Findings | Live countdown, mandatory reason                         |
| Suppressed-by-design list      | Findings | Config path and reason                                   |
| Finding detail drawer          | Findings | Evidence chart, rule link, next tool, citation           |
| Control chart                  | Charts   | Violations by shape plus rule id                         |
| Capability histogram           | Charts   | Specification limits, fitted curve, tails                |
| Pareto chart                   | Charts   | Indexed to percent, one axis                             |
| Value stream map               | Charts   | Generated from the process chain                         |
| Constraint timeline            | Charts   | Band per interval, click to seek                         |
| Sparkline                      | Charts   | No axes, one labelled endpoint                           |
| Interval mark                  | Charts   | Confidence interval with zero marked                     |
| Chart legend and tooltip layer | Charts   | Keyboard parity with hover                               |
| Chat transcript                | Agent    | Roles, sim time, measure cap                             |
| Grounding chip                 | Agent    | `data-result-id`, popover with fallback                  |
| Tool trace disclosure          | Agent    | Tool, arguments, result id, bucket                       |
| Ungrounded number warning      | Agent    | Marks the numeral in place                               |
| Abstention notice              | Agent    | Informational state, not an error                        |
| What-if verdict card           | Agent    | Field-level formatting contract                          |
| Approval strip                 | Agent    | Tier badge, diff, expiry, note on reject                 |
| Empty state                    | State    | Per panel, says what would fill it                       |
| Loading state                  | State    | Previous render held at reduced opacity                  |
| Error boundary page            | State    | Names the missing namespace                              |
| Offline placeholder            | State    | The documented `file://` degraded path                   |
| Buffering state                | State    | Visible, resumes automatically                           |
| Tamper warning                 | State    | Chunk hash mismatch                                      |
| Scrubber and chapter track     | Replay   | 24-pixel hit areas, nearest-tick resolution              |
| View toggle 2D and 3D          | 3D       | Disabled with explanation when absent                    |
| Severity halo ring             | 3D       | Segment count equals glyph side count                    |
| Metric picker                  | Query    | Governed metrics only                                    |
| SQL display                    | Query    | Shown beside the number                                  |

### 12.6 Vendored items

Every row carries a provenance header in the file and a line in `NOTICE`, per
section 12.1. All five are status Vendored.

| Asset                            | Source                               | Version or commit                                               | Licence     | Ships in                     | NOTICE line                                                                                     |
| -------------------------------- | ------------------------------------ | --------------------------------------------------------------- | ----------- | ---------------------------- | ----------------------------------------------------------------------------------------------- |
| Inter, variable, subset          | `github.com/rsms/inter`              | tag `v4.1`, commit `e3a3d4c57d5ecc01453a575621882a384c1995a3`   | SIL OFL 1.1 | `index.html`, base64         | `Inter. Copyright (c) 2016 The Inter Project Authors. SIL Open Font License 1.1.`               |
| JetBrains Mono, variable, subset | `github.com/JetBrains/JetBrainsMono` | tag `v2.304`, commit `cd5227bd1f61dff3bbd6c814ceaf7ffd95e947d9` | SIL OFL 1.1 | `index.html`, base64         | `JetBrains Mono. Copyright 2020 The JetBrains Mono Project Authors. SIL Open Font License 1.1.` |
| three.js                         | npm `three`                          | `0.185.1`                                                       | MIT         | `twinflow-view3d`, on demand | `three.js. Copyright (c) 2010-2026 three.js authors. MIT License.`                              |
| DuckDB-Wasm                      | npm `@duckdb/duckdb-wasm`            | pinned release, see below                                       | MIT         | Pages site, first query only | `DuckDB-Wasm. Copyright (c) 2020-2026 DuckDB Labs and contributors. MIT License.`               |
| axe-core                         | npm `axe-core`                       | `4.13.0`                                                        | MPL-2.0     | nothing                      | Not in NOTICE. Test dependency, never distributed                                               |

The DuckDB-Wasm `latest` dist-tag resolved to `1.33.1-dev57.0` on 2026-08-09,
which is a development build. The pin is a chosen release version recorded in
`pyproject.toml` with its file hash, never the floating tag, exactly as section
7.3.4 of the contract page states.

The two fonts replace the single unnamed font in the contract page's section
7.3.4. Both are variable fonts, which is what the 60 KB budget for two families
depends on. Neither IBM Plex npm package ships a variable font. The jsDelivr
file listing for `@ibm/plex-sans@1.1.0` and `@ibm/plex-mono@2.5.0` on 2026-08-09,
HTTP 200 for both, holds only static weight files. That is why Plex was not
chosen despite being one repository for two families.

### 12.7 Evaluated, licence verified, and declined

Recording these matters because a reader cannot tell a decision from an oversight
otherwise.

Each row below has a compatible licence and could be vendored. None is, and the
reason is stated so a reader can tell a decision from an oversight.

| Candidate              | Licence, verified                                        | Why it is not vendored                                                                                                                                  |
| ---------------------- | -------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------- |
| uPlot                  | MIT                                                      | About 40 KB against a 400 KB file budget, for sparklines and control charts that are roughly eighty lines of SVG path generation                        |
| Open Props             | MIT                                                      | Ships hex and HSL values. The palette here is generated from OKLCH and gated, so a second ungated colour source would be the one an old browser renders |
| modern-normalize       | MIT                                                      | A 15-line hand reset covers this interface, and the sentence "the only third-party bytes in the file are the font subsets" is worth more than the reset |
| Lucide icons           | ISC                                                      | The severity set has to be polygons with defined side counts, because the 3D halo reads the side count. No general icon set satisfies that              |
| shadcn/ui              | MIT                                                      | Presumes React and a build. Section 2.6. Inspiration status instead, per section 12.8                                                                   |
| Magic UI free registry | MIT                                                      | Same architecture problem, and its continuous-motion components are refused by section 9 whatever the delivery mechanism                                |
| microsoft/fluentui     | MIT for code, separate asset licence for fonts and icons | Same architecture problem. No Fluent font or icon asset is proposed anywhere, because those assets are outside the MIT grant                            |

### 12.8 Inspiration sources

Nothing on this list contributes code. Each row records a problem worth solving
or a set of states worth handling, written down in this document's own words and
specified from that description rather than from the source. None of these
appears in `NOTICE`, per section 12.1.

The method that keeps the line clear: read the source, write down what it does
and why, close it, then specify from the description. A specification that would
let someone build the thing without ever seeing the original took the idea. One
that reads like a transcription took the expression.

| Source                                                  | Licence, and how it was established                                                                   | Why inspiration rather than vendored                                          | What was taken                                                                                                                                                                                                           |
| ------------------------------------------------------- | ----------------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| openstatusHQ/openstatus                                 | AGPL-3.0, read from LICENSE with curl, section 13.1                                                   | Network copyleft would relicense the whole work                               | The idea that a monitoring list wants a typed query language in a command bar, and that a row should open a detail sheet with previous and next navigation rather than a modal                                           |
| Grafana                                                 | AGPL-3.0, read from LICENSE with curl, section 13.1                                                   | Same                                                                          | The convention that a time range is one control scoping every panel, and that a panel states its own query                                                                                                               |
| Netdata                                                 | GPL-3.0, read from LICENSE with curl, section 13.1                                                    | Same                                                                          | The idea that a dashboard reporting its own render health is more credible than one that does not, which section 5.3 of the contract page already adopts as the perf overlay                                             |
| Perses                                                  | Apache-2.0, read from LICENSE with curl, section 13.1                                                 | Compatible, but React and a build step                                        | Dashboard-as-data: the panel layout is a validated document, not code, which is why this interface has a panel registry rather than a hand-laid grid                                                                     |
| Prometheus                                              | Apache-2.0, read from LICENSE with curl, section 13.1                                                 | Compatible, but not an interface library                                      | The convention that a stale series is drawn as absent rather than as a flat line                                                                                                                                         |
| shadcn-ui/ui                                            | MIT, verified in the prior passes at a pinned commit                                                  | React and a build step                                                        | The inventory of states a serious control handles: hover, focus visible, active, disabled, invalid, loading, and read-only, applied to every element in section 12.5                                                     |
| Magic UI free registry                                  | MIT, verified in the prior passes at a pinned commit                                                  | React and a build step, and its continuous-motion set is refused by section 9 | A negative finding: which motion patterns to exclude from a work surface                                                                                                                                                 |
| microsoft/fluentui                                      | MIT for code, assets under a separate licence                                                         | React and a build step, and no asset is usable                                | That an elevation scale needs calibrating per surface rather than applied by taste, and that exits run faster than entrances                                                                                             |
| The dashboard-cluster passes                            | 59 MIT, 9 with no licence, 7 AGPL-3.0, per the prior record                                           | React and a build step throughout                                             | The set of problems a dense table has to solve: live tailing, column density, sort announcement, row detail, and filter state that survives a reload                                                                     |
| The definitive-opensource pass                          | 118 MIT, 65 Apache-2.0, 65 AGPL-3.0, 44 GPL-3.0, 5 MPL-2.0, 2 BSD-3, per the prior record             | Mixed licences and mixed architectures                                        | Which device-monitoring surfaces exist at all: connection quality, resource graphs, threshold-coloured series, and hardware info tables                                                                                  |
| The product-cluster pass                                | 41 MIT, 8 AGPL-3.0, 5 Apache-2.0, 4 CC0, 3 with no licence, per the prior record                      | React and a build step throughout                                             | Two ideas this design uses. That a live event log wants a split list-and-preview rather than a modal, and that a human-in-the-loop gate shows the exact payload before it commits, which is what the approval strip does |
| Codehagen/Dingify                                       | AGPL-3.0, read from a full-tree licence scan in the prior pass                                        | Network copyleft                                                              | The only realtime monitoring dashboard in the whole corpus. What was taken is the shape of an event-feed surface, nothing else                                                                                           |
| The four no-licence repositories in the product cluster | No licence file anywhere in tree, confirmed by a full-tree scan                                       | No licence means all rights reserved                                          | Nothing beyond the observation that a status vocabulary belongs in one place shared by rows, badges, and headers, rather than per panel                                                                                  |
| Fluent toast architecture                               | MIT for code, per the prior pass. Fluent font and icon assets are outside that grant and none is used | React and a build step                                                        | Announcement politeness, and pause while the reader is engaged. Both applied in section 7.5                                                                                                                              |
| Accessible combobox pattern                             | Not a repository. A published authoring pattern                                                       | Not code                                                                      | Active descendant, so DOM focus stays put while the announced position moves. Applied in section 7.5                                                                                                                     |
| Aceternity UI                                           | Proprietary, verified with curl, section 13.2                                                         | Its terms forbid redistributing source files                                  | Nothing. Its catalogue is landing-page motion, which section 9 refuses on a work surface                                                                                                                                 |
| Hover.dev                                               | Proprietary, verified with curl, section 13.2                                                         | Its terms are internally inconsistent for a public repository, per OQ-17      | Nothing, for the same reason                                                                                                                                                                                             |

Two of those rows deserve their own sentence. The prior research recorded that
individual component licences for Aceternity UI and Hover.dev had never been
verified. They are verified now, in section 13.2, and both turn out to forbid
what a public Apache-2.0 repository does by definition. Neither contributes
anything to this design, so the verification changes nothing except that the
question is now closed.

---

## 13. Licence record

### 13.1 Everything verified, with locator and status

Every row retrieved with `curl` on 2026-08-09. No summarising fetcher was used.

| Subject                       | Locator                                                                        | HTTP | Result                                             |
| ----------------------------- | ------------------------------------------------------------------------------ | ---- | -------------------------------------------------- |
| openstatusHQ/openstatus       | `https://raw.githubusercontent.com/openstatusHQ/openstatus/main/LICENSE`       | 200  | GNU Affero General Public License, Version 3       |
| grafana/grafana               | `https://raw.githubusercontent.com/grafana/grafana/main/LICENSE`               | 200  | GNU Affero General Public License, Version 3       |
| netdata/netdata               | `https://raw.githubusercontent.com/netdata/netdata/master/LICENSE`             | 200  | GNU General Public License, Version 3              |
| prometheus/prometheus         | `https://raw.githubusercontent.com/prometheus/prometheus/main/LICENSE`         | 200  | Apache License 2.0                                 |
| perses/perses                 | `https://raw.githubusercontent.com/perses/perses/main/LICENSE`                 | 200  | Apache License 2.0                                 |
| louislam/uptime-kuma          | `https://raw.githubusercontent.com/louislam/uptime-kuma/master/LICENSE`        | 200  | MIT                                                |
| rsms/inter                    | `https://raw.githubusercontent.com/rsms/inter/master/LICENSE.txt`              | 200  | SIL Open Font License 1.1                          |
| JetBrains/JetBrainsMono       | `https://raw.githubusercontent.com/JetBrains/JetBrainsMono/master/OFL.txt`     | 200  | SIL Open Font License 1.1                          |
| IBM/plex                      | `https://raw.githubusercontent.com/IBM/plex/master/LICENSE.txt`                | 200  | SIL Open Font License 1.1                          |
| npm `@ibm/plex-sans`          | `https://registry.npmjs.org/@ibm/plex-sans/latest`                             | 200  | `OFL-1.1`, version 1.1.0                           |
| npm `@ibm/plex-mono`          | `https://registry.npmjs.org/@ibm/plex-mono/latest`                             | 200  | `OFL-1.1`, version 2.5.0                           |
| npm `three`                   | `https://registry.npmjs.org/three/latest`                                      | 200  | `MIT`, version 0.185.1                             |
| npm `@duckdb/duckdb-wasm`     | `https://registry.npmjs.org/@duckdb/duckdb-wasm/latest`                        | 200  | `MIT`, version 1.33.1-dev57.0                      |
| npm `axe-core`                | `https://registry.npmjs.org/axe-core/latest`                                   | 200  | `MPL-2.0`, version 4.13.0                          |
| npm `uplot`                   | `https://registry.npmjs.org/uplot/latest`                                      | 200  | `MIT`                                              |
| leeoniya/uPlot                | `https://raw.githubusercontent.com/leeoniya/uPlot/master/LICENSE`              | 200  | MIT                                                |
| argyleink/open-props          | `https://raw.githubusercontent.com/argyleink/open-props/main/LICENSE`          | 200  | MIT                                                |
| sindresorhus/modern-normalize | `https://raw.githubusercontent.com/sindresorhus/modern-normalize/main/license` | 200  | MIT                                                |
| lucide-icons/lucide           | `https://raw.githubusercontent.com/lucide-icons/lucide/main/LICENSE`           | 200  | ISC                                                |
| shadcn-ui/ui                  | `https://raw.githubusercontent.com/shadcn-ui/ui/main/LICENSE.md`               | 200  | MIT                                                |
| magicuidesign/magicui         | `https://raw.githubusercontent.com/magicuidesign/magicui/main/LICENSE.md`      | 200  | MIT                                                |
| npm `react`                   | `https://registry.npmjs.org/react/latest`                                      | 200  | `MIT`, version 19.2.8                              |
| npm `tailwindcss`             | `https://registry.npmjs.org/tailwindcss/latest`                                | 200  | `MIT`                                              |
| npm `motion`                  | `https://registry.npmjs.org/motion/latest`                                     | 200  | `MIT`                                              |
| npm `framer-motion`           | `https://registry.npmjs.org/framer-motion/latest`                              | 200  | `MIT`                                              |
| Apache License 2.0 text       | `https://www.apache.org/licenses/LICENSE-2.0.txt`                              | 200  | Section 4(d) NOTICE obligation read verbatim       |
| SIL OFL official text         | `https://openfontlicense.org/open-font-license-official-text/`                 | 200  | Retrieved and available to ship beside the subsets |
| Inter tag `v4.1`              | `https://api.github.com/repos/rsms/inter/git/ref/tags/v4.1`                    | 200  | commit `e3a3d4c57d5ecc01453a575621882a384c1995a3`  |
| JetBrains Mono tag `v2.304`   | `https://api.github.com/repos/JetBrains/JetBrainsMono/git/ref/tags/v2.304`     | 200  | commit `cd5227bd1f61dff3bbd6c814ceaf7ffd95e947d9`  |

### 13.2 The two the prior research left unverified

| Subject       | Locator                             | HTTP | What the page says                                                                                                                                                                                                                                              |
| ------------- | ----------------------------------- | ---- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Aceternity UI | `https://ui.aceternity.com/licence` | 200  | "The Aceternity License provides you with an ongoing, non-exclusive, worldwide license to use the digital work"; prohibited uses include "Re-distribution: You cannot re-distribute the Item as a stock image or its source files, regardless of modifications" |
| Hover.dev     | `https://www.hover.dev/license`     | 200  | Permitted list includes "Use of components for open source projects"; the same page states "Components subject to copyright and may not be redistributed without the written consent of Hover.dev"                                                              |

Both are unavailable to this repository. Aceternity is unambiguous: publishing a
component's source in a public repository is redistributing source files.
Hover.dev is internally inconsistent, since permitting open-source use and
forbidding redistribution without written consent cannot both hold for a public
repository, and an ambiguous grant is not a grant. OQ-17 records the
ambiguity rather than resolving it in this project's favour.

### 13.3 Non-licence sources

| Subject                          | Locator                                                                  | HTTP     | What was read                                                                                                        |
| -------------------------------- | ------------------------------------------------------------------------ | -------- | -------------------------------------------------------------------------------------------------------------------- |
| NUREG-0700 Revision 4            | `https://www.nrc.gov/docs/ML2602/ML26022A094.pdf`                        | 200      | 5,043,444 bytes, 622 pages. Guidelines 1.3.8-10, 1.3.8-12, 1.3.8-13, 4.1.2-1, 4.1.2-2, 4.1.3-1, 4.1.3-2 read as text |
| NUREG-0700 publication record    | `https://www.nrc.gov/reading-rm/doc-collections/nuregs/staff/sr0700/r4/` | 200      | Manuscript completed August 2025, published January 2026                                                             |
| Baseline status, twelve features | `https://api.webstatus.dev/v1/features/<id>`                             | 200 each | Section 2.7                                                                                                          |
| CSS Color Module Level 4         | `https://www.w3.org/TR/2026/CRD-css-color-4-20260806/`                   | 200      | The two published OKLCH triples used to self-check the converter                                                     |
| WCAG 2.1                         | `https://www.w3.org/TR/WCAG21/`                                          | 200      | SC 1.4.1 text: "Color is not used as the only visual means of conveying information"                                 |

---

## 14. Proposed additions to the test and gate registry

Section 7 of the contract page owns every check id, and `T-INDEX-1` fails the
build on an id described anywhere and defined nowhere. Six ids are proposed here
and none of them is real until it has a row in that page's tables.

| Proposed id         | Class      | What it would assert                                                                                                                                                                         |
| ------------------- | ---------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `T-PROGRESSIVE-1`   | unit       | With `popover`, `view-transitions`, and `light-dark` stubbed out, every panel still renders and every control still works                                                                    |
| `T-ISOLATION-1`     | unit       | At most one element carries the isolation class inside any one container, over a random `ViewState`                                                                                          |
| `P-CLASS-ORDER`     | property   | The rendered severity of a row always equals the producer's value, and the sort key orders by class before severity                                                                          |
| `BG-FLOOD-1`        | budget     | The measured row-mutation count at which a full re-render exceeds the frame budget on the reference runner, replacing the chosen 120                                                         |
| `BG-FIRSTPAINT-1`   | budget     | Transferred bytes to first rendered frame on the Pages build, against the 1.2 MB derived figure                                                                                              |
| `T-FOCUS-1`         | unit       | With focus inside the findings stream, injecting 40 arrivals and a rank change leaves `document.activeElement` and `aria-activedescendant` unchanged, and the paused-update counter reads 40 |
| `VAL-GATE SERIES-1` | validation | The categorical series palette passes the `dataviz` validator in both modes against this repository's own surfaces, at the thresholds section 8.2 records                                    |

---

## 15. Open questions

**OQ-17. Whether Hover.dev's licence permits open-source use.** Its licence page
lists "Use of components for open source projects" as permitted and also states
that components "may not be redistributed without the written consent of
Hover.dev". A public Apache-2.0 repository does both at once. Settling it needs
written confirmation from the licensor, and until then nothing from that source
is used. Nothing in this design depends on the answer.

**OQ-18. Whether a published minimum glyph size exists for shape-coded severity.**
The 14 CSS pixel floor in section 6.2 was chosen here from the requirement that
an octagon and a hexagon stay distinguishable at projector distance. No source
this document could retrieve gives a minimum angular size for polygon
discrimination at a stated viewing distance. If one exists the floor moves to it.
This is the shape-channel counterpart to the existing OQ-15 on colour separation.

**OQ-19. Whether the class ordering belongs in the view or in the alarm manager.**
Section 6.3 derives `finding_class` in the presentation layer from the existing
`kind` enum, which keeps the schema unchanged. The alternative publishes the class
on `alarm.state.v1` and lets `twinflow-alarms` rank by it, which would make the
ordering testable server-side and would put safety ranking inside the brick a
controls engineer adopts alone. The second is probably right and it costs a
schema field, so it is an owner decision rather than an implementer one.

**OQ-20. Whether the centre-column-before-left-column focus order is the right
trade.** Section 10 puts the findings stream ahead of the plan view in the tab
order while the plan view sits left visually. WCAG 2.4.3 asks for a focus order
that preserves meaning and operability, and a keyboard reader reaching the
finding first preserves meaning better than matching the visual order does. A
reviewer could reasonably read it the other way. It is one line of DOM order
either way and it needs deciding once.

**OQ-21. Whether the Pareto deviation is acceptable.** Section 8.1 indexes the
Pareto bars to percent so the chart has one axis, against the conventional form
which puts counts on the left axis and cumulative percent on the right. The
conventional form is what a quality engineer expects to see and what every Lean
Six Sigma textbook prints. The single-axis form is what the charting method
requires and what avoids the alignment being arbitrary. Both positions are
defensible and this document picked the second.

**OQ-22. Whether the 3D view inherits the no-build ruling.** Section 2 decides
the 2D dashboard. The contract page's OQ-5 already asks the same question for the
3D view, and this page does not answer it. The answer depends on whether
`twinflow-view3d` ever needs a shader pipeline that hand-written WebGL2 makes
unreasonable. Nothing in section 2 forecloses either answer.

**OQ-23. Whether a published source states the colour-for-exception convention.**
Section 4.1 argues that a resting screen should be neutral so that colour carries
information when it appears. NUREG-0700 Revision 4 supports the redundancy rule
and the red-green and chromostereopsis rules, and it was read. It does not state
the colour-for-exception convention in those words in the sections read here. The
convention is attributed to this document's reasoning, not to a source, until one
is found and read.

**OQ-24. Whether pausing the reorder while the list has focus is right.** Section
7.5 holds arriving and re-ranked rows while a keyboard reader has focus inside the
findings stream, and shows a live paused-update count. The reader keeps their
place, which is the point. The cost lands during a flood. The visible order stops
being the ranked order for as long as focus stays there, and a reader who misses
the banner could act on a stale head. The alternatives are worse in
different ways: reordering live loses the reader's place, and refusing focus
inside the list breaks keyboard reach. This needs one round of use before it is
settled, and `T-FOCUS-1` should be written whichever way it goes.

**OQ-25. What stable focus in a live list is supposed to look like.** The seven
prior vendoring passes cover several hundred components and record no solution to
a list reordering under a focused reader, and no scrubber of any kind. Section 7.5
composes an answer from two primitives found elsewhere in that corpus, and section
11.2 specifies the scrubber from the requirement. Both are this document's own
design and neither has prior art to check against. If a published pattern exists,
it should replace the composed one.
