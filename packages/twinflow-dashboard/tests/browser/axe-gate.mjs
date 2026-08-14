/*
  The browser tier of gate VAL-GATE-A11Y-001: axe-core over the shipped page.

      node axe-gate.mjs                 audit src/twinflow/dashboard/assets/index.html
      node axe-gate.mjs --selftest      watch the audit refuse an injected violation
      node axe-gate.mjs --page <path>   audit some other file
      node axe-gate.mjs --json <path>   also write the full result of every state

  WHY A SECOND TIER EXISTS AT ALL
  -------------------------------
  The gate's other three clauses are properties of the document and the
  stylesheet and are asserted from Python in ../test_accessibility_floor.py. The
  axe-core clause is not. axe-core is a rule engine that needs computed style,
  layout boxes, and an accessibility tree, and none of those exist until a
  browser has laid the page out. Doctrine D-11 is the reason the clause names
  axe-core rather than "an accessibility check": a rule list written in this
  repository would be a rule list chosen by whoever wrote the markup, and a gate
  cannot rest on the repository grading itself. axe-core is an external,
  published, versioned rule set, and the version it ran at is printed below with
  the result so a reader can go read the rules.

  WHAT MAKES A RUN FAIL
  ---------------------
  One violation whose impact axe-core rates critical or serious, in any audited
  state. That is the gate's own falsifying condition, quoted from its registry
  row. Moderate and minor violations and the incomplete set are printed and do
  not fail the run, because the gate did not promise them and a gate that
  quietly asserts more than its row says is a gate nobody can predict.

  WHY SEVERAL STATES
  ------------------
  A single audit of the page as it parses would never see the dark palette, the
  raised-contrast palette, the provenance note, the plan table, or the settings
  dialog, because four of those five start hidden and the fifth is a token set
  behind an attribute. Each state below is reached the way a reader reaches it:
  the display attributes are the ones the page's own boot code sets from
  /config.json, and the revealed panels are opened by clicking the control that
  the demo path in twinflow.dashboard.accessibility already names.

  LICENSING
  ---------
  axe-core is MPL-2.0. The CONTRIBUTING.md allowlist accepts MPL-2.0 for a
  development dependency and refuses it for one shipped at run time. This
  directory is neither imported by nor packaged with any twinflow distribution:
  the dashboard wheel builds from src/twinflow only, and this tree has no Python
  in it. playwright is Apache-2.0.
*/

import { createRequire } from "node:module";
import { mkdtemp, readFile, writeFile } from "node:fs/promises";
import { tmpdir } from "node:os";
import path from "node:path";
import process from "node:process";
import { fileURLToPath } from "node:url";

const require = createRequire(import.meta.url);
const HERE = path.dirname(fileURLToPath(import.meta.url));

/*
  The shipped file, reached by walking up out of the test tree rather than by a
  copy kept beside this script. A copy is a second page that drifts from the one
  the server sends, and then the gate audits something nobody receives.
*/
const SHIPPED_PAGE = path.resolve(
  HERE,
  "../../src/twinflow/dashboard/assets/index.html",
);

/* The impacts the gate's row names. Everything else is reported, not enforced. */
const FAILING_IMPACTS = new Set(["critical", "serious"]);

/*
  The states audited, and the control that reaches each one. `theme` and
  `contrast` are the two attributes TF.start writes onto the document element
  from the bootstrap document, so setting them here puts the page in a state the
  server really produces. `reveal` holds element ids that get clicked, in order,
  after the palette settles.

  The settings dialog is its own state rather than a third click in the revealed
  state. It opens with showModal, which makes the rest of the document inert,
  and an audit taken with it open sees the dialog and nothing else.
*/
const STATES = [
  { name: "light, normal contrast", theme: "light", contrast: "normal" },
  { name: "dark, normal contrast", theme: "dark", contrast: "normal" },
  { name: "light, raised contrast", theme: "light", contrast: "more" },
  { name: "dark, raised contrast", theme: "dark", contrast: "more" },
  {
    name: "light, panels revealed",
    theme: "light",
    contrast: "normal",
    reveal: ["tf-synthetic-badge", "tf-plan-table-toggle"],
  },
  {
    name: "dark, panels revealed",
    theme: "dark",
    contrast: "normal",
    reveal: ["tf-synthetic-badge", "tf-plan-table-toggle"],
  },
  {
    name: "light, settings dialog open",
    theme: "light",
    contrast: "normal",
    reveal: ["tf-settings"],
  },
  {
    name: "dark, settings dialog open",
    theme: "dark",
    contrast: "normal",
    reveal: ["tf-settings"],
  },
];

/*
  The violation the selftest injects: an image with no alt attribute and no
  role, which axe-core's image-alt rule rates critical. It is injected into a
  copy in a temporary directory and the copy is never written back, so the tree
  this gate audits never contains it.
*/
const INJECTED_RULE = "image-alt";
const INJECTED_MARKUP =
  '<img id="tf-injected-violation" ' +
  'src="data:image/gif;base64,R0lGODlhAQABAIAAAAAAAP///yH5BAEAAAAALAAAAAABAAEAAAIBRAA7" ' +
  'width="24" height="24">';

function parseArguments(argv) {
  const options = { page: SHIPPED_PAGE, selftest: false, json: null };
  for (let index = 0; index < argv.length; index += 1) {
    const flag = argv[index];
    if (flag === "--selftest") {
      options.selftest = true;
    } else if (flag === "--page") {
      options.page = path.resolve(argv[(index += 1)]);
    } else if (flag === "--json") {
      options.json = path.resolve(argv[(index += 1)]);
    } else {
      throw new Error(`unknown argument ${flag}. Read the header of this file.`);
    }
  }
  return options;
}

/*
  The shipped page is one self-contained file, so the audit hands it to the
  browser through a route rather than through a socket. Playwright fulfills the
  navigation from memory, which gives the document a real https origin: a rule
  that asks about a same-origin resource or a secure context then reports a
  property of the page rather than an environment quirk, and the audit opens no
  port and serves no directory.
*/
const PAGE_ORIGIN = "https://dashboard.twinflow.test";

/*
  Resolve once every CSS transition in flight has finished.

  The body carries a 200ms background-color transition, so an audit taken in the
  same task as the attribute flip reads the outgoing background against the
  incoming text color and reports a contrast failure that no reader ever sees.
  Waiting on the transitions themselves rather than on a duration keeps the
  result independent of how fast the machine is, and the filter keeps the
  conveyor animation, which never finishes, from holding the audit open forever.
*/
const SETTLE = () =>
  Promise.all(
    document
      .getAnimations({ subtree: true })
      .filter((animation) => animation instanceof CSSTransition)
      .map((animation) => animation.finished),
  );

async function auditOneState(browser, html, axeSource, state) {
  const page = await browser.newPage();
  await page.route(`${PAGE_ORIGIN}/`, (route) =>
    route.fulfill({
      status: 200,
      contentType: "text/html; charset=utf-8",
      body: html,
    }),
  );
  /*
    The page fetches /config.json for its deployment settings and this tier
    serves no such document. Refusing the request leaves the display attributes
    at the values the file ships with, which the loop below then sets
    explicitly. Serving a synthetic bootstrap here instead would put a second
    copy of the shape config.py owns into this file, where it would drift.
  */
  await page.route("**/config.json", (route) => route.abort());
  await page.addInitScript({ content: axeSource });
  await page.goto(`${PAGE_ORIGIN}/`, { waitUntil: "load" });
  await page.evaluate(
    ([theme, contrast]) => {
      document.documentElement.setAttribute("data-theme", theme);
      document.documentElement.setAttribute("data-contrast", contrast);
    },
    [state.theme, state.contrast],
  );
  await page.evaluate(SETTLE);
  for (const id of state.reveal ?? []) {
    await page.click(`#${id}`);
  }
  await page.evaluate(SETTLE);
  const result = await page.evaluate(() => window.axe.run(document, {}));
  await page.close();
  return result;
}

async function audit(pagePath) {
  const axeSource = await readFile(require.resolve("axe-core/axe.min.js"), "utf8");
  const html = await readFile(pagePath, "utf8");
  const browser = await require("playwright").chromium.launch();
  const states = [];
  try {
    for (const state of STATES) {
      states.push({ state, result: await auditOneState(browser, html, axeSource, state) });
    }
  } finally {
    await browser.close();
  }
  return states;
}

function report(states) {
  const failing = [];
  for (const { state, result } of states) {
    for (const violation of result.violations) {
      const line =
        `  ${state.name}: [${violation.impact}] ${violation.id}, ` +
        `${violation.nodes.length} node(s): ${violation.help}`;
      console.log(line);
      for (const node of violation.nodes) {
        console.log(`      ${node.target.join(" ")}`);
        console.log(`      ${node.failureSummary.replace(/\n/g, " ")}`);
      }
      console.log(`      ${violation.helpUrl}`);
      if (FAILING_IMPACTS.has(violation.impact)) {
        failing.push({ state: state.name, rule: violation.id, impact: violation.impact });
      }
    }
    console.log(
      `  ${state.name}: ${result.passes.length} rules passed, ` +
        `${result.violations.length} violated, ${result.incomplete.length} needing review`,
    );
  }
  return failing;
}

/*
  Doctrine D-12: a gate nobody has watched refuse anything may be a gate that
  cannot refuse. This runs the whole audit a second time over a copy of the page
  with one image stripped of its alt attribute, and fails when axe-core does not
  catch it. The copy lives in a temporary directory that the operating system
  owns, so no run can leave a violation behind in the tree.
*/
async function selftest(pagePath) {
  const markup = await readFile(pagePath, "utf8");
  const injected = markup.replace("</body>", `${INJECTED_MARKUP}\n  </body>`);
  if (injected === markup) {
    throw new Error(`${pagePath} has no </body> to inject into`);
  }
  const directory = await mkdtemp(path.join(tmpdir(), "twinflow-axe-selftest-"));
  const copy = path.join(directory, path.basename(pagePath));
  await writeFile(copy, injected, "utf8");

  console.log(`selftest: auditing a copy carrying one ${INJECTED_RULE} violation`);
  console.log(`selftest: ${copy}`);
  const caught = (await audit(copy)).flatMap(({ state, result }) =>
    result.violations
      .filter((v) => v.id === INJECTED_RULE && FAILING_IMPACTS.has(v.impact))
      .map((v) => `${state.name} [${v.impact}]`),
  );
  if (caught.length === 0) {
    console.error(
      `selftest FAILED: axe-core did not report ${INJECTED_RULE} on a page that carries it, ` +
        "so a green run of this gate means nothing",
    );
    return 1;
  }
  console.log(`selftest passed: ${INJECTED_RULE} reported in ${caught.length} state(s)`);
  console.log(`  ${caught.join(", ")}`);
  return 0;
}

const options = parseArguments(process.argv.slice(2));
console.log(`axe-core ${require("axe-core").version}, playwright ${require("playwright/package.json").version}`);

if (options.selftest) {
  process.exit(await selftest(options.page));
}

console.log(`auditing ${options.page}`);
const states = await audit(options.page);
if (options.json) {
  await writeFile(options.json, JSON.stringify(states, null, 2), "utf8");
  console.log(`full result written to ${options.json}`);
}
const failing = report(states);
if (failing.length > 0) {
  console.error(
    "VAL-GATE-A11Y-001 axe-core clause FAILED: " +
      failing.map((f) => `${f.rule} (${f.impact}) in ${f.state}`).join(", "),
  );
  process.exit(1);
}
console.log(
  `VAL-GATE-A11Y-001 axe-core clause: zero critical and zero serious violations ` +
    `across ${states.length} states`,
);
