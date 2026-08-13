# Changelog

All notable changes to this project are recorded here.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and the project follows [Semantic Versioning](https://semver.org/spec/v2.0.0.html).
The six headings below are the six change types Keep a Changelog names: Added,
Changed, Deprecated, Removed, Fixed, and Security.

Entries under `[Unreleased]` are written by the `post-commit` hook, which maps
`feat` to Added, `fix` to Fixed, and `perf` to Changed, then folds the edit into
the commit that produced it. `docs`, `chore`, `refactor`, and `test` commits
record nothing. The three headings the hook never writes are filled in by hand.
See [CONTRIBUTING.md](CONTRIBUTING.md) for the full rules, and edit the wording
here freely: the hook only ever adds.

## [Unreleased]

### Added

- hold a deferred metric to the work package that owes it

### Changed

### Deprecated

### Removed

### Fixed

### Security

## [0.1.0] - 2026-08-13

The contracts that fix what a recorded run is, and the pipeline that produces
every tag from here. There is no product at this tag: no station, no device, no
dashboard. What there is instead is the set of decisions that a later phase
cannot change without invalidating the runs already recorded, which is why they
land first.

A run seed derives every stochastic stream, the event envelope carries a
producer and a dense sequence, the schema registry publishes both, and a config
that fails to load says which line is wrong and what to write instead. Twelve
gates stand at this phase exit and ten of them run a command; the two that
measure cross-platform divergence report it and assert no bound until a
two-platform run sets one.

Take one brick: `twinflow-schemas`, `twinflow-rng`, `twinflow-kernel`,
`twinflow-config`, and `twinflow-roadmap` each install alone.

### Added

- let a metric marker name the release that owes its number
- reject a double dash standing in for punctuation
- record SCN-F1 and prove the two-run hash match
- assert the five source constraints and run a phase's exit set
- pin the reference runner and give every job a budget
- block a shell or workflow error at the commit that writes it
- check spelling in the tree and in the commit message
- cut every tag from one pipeline, starting at the first
- run the roadmap gate everywhere the other gates run
- validate the plan and prove every idea is placed
- record the plan as data the build can check
- assert the log invariants and the release policy
- enforce the license allowlist against the resolved tree
- open the environment seam and the metric identifier space
- validate a facility profile and say what to fix
- publish the schema registry and the compatibility differ
- enforce the package boundary rules
- add the sim clock and the clock port
- add the three rng lint rules and the two-hash-seed check
- freeze the cross-language known-answer corpus
- add the append-only stream registry
- fix the name-addressed derivation byte for byte
- add the rng leaf package
- settle the event envelope before any schema publishes
- add the schema leaf package

### Changed

### Deprecated

### Removed

### Fixed

- call the phase-exit runner and record the work it ran
- carry the Apache-2.0 text to the byte
- give the local actionlint the shellcheck it needs to match CI
- run shellcheck and actionlint locally, and on shell files only
- confine the files the spelling gate opens to this repository
- pass the roadmap subcommand through to the tool
- resolve the comment judge through uv where uv is present
- build the judged message path from the repository root
- confine the judged commit message to this repository
- make uvx ty check pass on prose-gate.py
- reconcile justfile, contributing guide, and ci-local.sh
- stop two sections spelling the rng derivation differently
- carry the bit-generator change through every section that names it
- switch the bit generator to pcg64dxsm before the corpus freezes
- name the vendored fonts and correct the asset count
- skip the type check and tests until a package exists
- stop ruff reformatting the code samples inside the design documents
- name each source in the text instead of pointing at a ledger

### Security
