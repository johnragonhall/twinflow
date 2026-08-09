# Pull request

## What changed

<!-- Plain description of the change and why it is the right shape. If an earlier approach was tried and dropped, say what was wrong with it. -->

## Requirement implemented

<!--
One or more identifiers, plus the issue this closes.
Tiers: component (1, 2b, 5, 6a10), E (bleeding edge), C (engineering craft), A (adoption and scale).
Example: implements C1, part of E4. Closes #12.
-->

- Requirement id(s):
- Closes:

## Test evidence

Which tiers ran, and their result. Paste the command and the summary line, not the whole log.

- [ ] Fast unit tests
- [ ] Property-based invariant suite (material conservation, ledger balance, genealogy closure, monotone clock)
- [ ] Seeded end-to-end scenarios with golden-file comparison
- [ ] Reference-validated statistics tests (any new statistic cites its published source in the test)
- [ ] Agent eval suite (accuracy, grounding pass rate, abstention rate)
- [ ] Schema contract tests (producer and consumer)
- [ ] Lint, format, and type checks

```
<!-- commands and result summaries -->
```

New or changed tests, and what failure each one would have caught:

<!-- Every bug fix carries a regression test. Name it here. -->

## Validation gates

- [ ] No validation gate is affected by this change.
- [ ] A gate is affected. Which one, what changed, and why the new behavior is correct:

<!--
Gates: determinism hash check, schema contract tests, property-based invariants,
reference-validated statistics, golden-file scenarios, agent eval thresholds,
config schema validation, accessibility checks, dependency and license audit,
quickstart timing, CI wall-time budget.
-->

## Determinism

- [ ] Not affected. No stochastic stream, seeding path, ordering, or event-log field changed.
- [ ] Affected. Details below.

If affected:

- Golden files or recorded runs regenerated: <!-- yes/no, and which -->
- Every new random draw comes from a seeded child RNG: <!-- yes/no -->
- Repeated-run hash check passes on this branch: <!-- yes/no -->
- Previously recorded runs still load, or a migration is included: <!-- yes/no -->

## Compatibility

- [ ] No public surface changed.
- [ ] Public surface changed (package API, REST or MCP contract, event schema, or `facility.yaml`), and the change is additive within the major version, or a migration and an upgrader path are included.

## Checklist

- [ ] CLA signed: my GitHub handle is in the signatories list in CLA.md, and every commit I added carries a `Signed-off-by` trailer. The `cla` job in `.github/workflows/lint.yml` checks both. It exempts the repository owner from the first, and exempts merge commits and base-branch commits from the second.
- [ ] CHANGELOG.md updated under the unreleased heading, with the compatibility note if recorded runs or configs are affected.
- [ ] Conventional commit messages.
- [ ] Documentation updated where behavior changed (README, ARCHITECTURE.md, ROADMAP.md, the brick's own README, or the relevant docs page).
- [ ] Any number added to documentation comes from a recorded run and sits inside a metric marker; no estimate replaces a TBD.
- [ ] New config keys validate against a published schema with line-numbered errors.
- [ ] Every new dependency matches a row in the CONTRIBUTING.md license allowlist, including the `Applies to` column, and I have named the row in this pull request. No hosted job checks this yet; the reviewer checks it by hand until milestone C11 lands.
- [ ] `sh scripts/ci-local.sh --security` run locally for a dependency change, with the audit and secret-scan steps present rather than skipped.
- [ ] No real, client, employer, or proprietary data is introduced anywhere, including in test fixtures.
- [ ] Dashboard changes keep severity encoded by shape and text as well as color, and stay keyboard navigable.
- [ ] The five-minute quickstart still works.
