---
title: ADR-0003 The kernel owns the Network port, and its production adapter wraps paho-mqtt
description: Adds the fourth seam as a kernel Protocol with an in-memory simulation adapter, and takes paho-mqtt under the BSD-3-Clause half of its dual license for the production side.
topic_type: concept
audience: contributors
---

# ADR-0003 The kernel owns the `Network` port, and its production adapter wraps paho-mqtt

## Status

`proposed`, 2026-08-14.

## Context

Section 2 of ARCHITECTURE.md names four seams and calls them the defining
architectural decision of the repository: CLOCK, RNG, NETWORK, and STORAGE. It
gives NETWORK the surface `connect()`, `publish()`, `subscribe()`,
`disconnect()`, an MQTT client over TCP with TLS in production mode, and an
in-memory bus with a fault-injection layer in simulation mode.

`twinflow.kernel` publishes `Clock` and nothing else. Three of the four seams
have no port in this tree, and NETWORK has neither of its two adapters. No MQTT
client is a dependency of any package in the workspace.

That gap is not visible from a checkout, because everything static about the
garage tier passes. `deploy/garage/docker-compose.yaml` validates, the image
builds, and the certificate script issues. The compose segmentation gate reports
one crossing point with the OT segment internal, and the broker demands an
identity on both listeners. Five of its seven services then fail at their first
instruction, because the command each one names does not exist. The tier was
asserted statically and had never been started.

Three obligations constrain the answer.

`twinflow.sensors` may not hold the transport itself. Its package docstring
states the rule it follows: the devices publish value objects and something
above wires them to a transport. Doctrine D-09 declares the layering, and
section 2.9 of `docs/design/iot-fleet.md` places the wiring in `twinflow-edge`,
a package the roadmap carries at no phase. So the seam has to arrive somewhere
that exists.

The client cannot be selected on features alone, because the licensing rule
binds first. Technology decision D15 admits permissive dependencies only, the
CONTRIBUTING.md allowlist carries no Eclipse Public License row, and ADR-0002
records that this project refuses a dependency on its license tree rather than
work around it. The same ruling refused certifi at MPL-2.0 and cost
`twinflow-api` its HTTP test client.

The asynchronous clients collide with a rule this repository already made.
Section 5.3 of `docs/design/iot-fleet.md` makes `Clock.timeout` the only timeout
primitive, so a broker keepalive of sixty seconds is sixty sim seconds and
compresses with everything else. Lint rule TFD014 bans `asyncio.wait_for` for
the matching reason: it reads `loop.time()` and would not compress at all. A
client whose own timeouts run on the event loop's clock puts a second,
uncompressible time source underneath the seam.

`docs/design/foundations.md` section 5.4 illustrates the escape-hatch annotation
form with the string `reason="aiomqtt is the production transport"` and a link
to `docs/adr/0004-mqtt-adapter.md`. Both are contents of a worked example rather
than a decision: no record was written, no number was reserved, and section 2 of
the decision index assigns numbers in order, which makes this record 0003. The
example is left as it stands, and this section is the note that the two differ.

Licensing and release facts below were read from the PyPI JSON API on
2026-08-14.

| Client      | Version | Declared license          | Latest release | Resolves paho |
| ----------- | ------- | ------------------------- | -------------- | ------------- |
| `paho-mqtt` | 2.1.0   | `EPL-2.0 OR BSD-3-Clause` | 2024-04-29     | is paho       |
| `aiomqtt`   | 2.5.1   | BSD (classifier)          | 2026-03-05     | yes, `>=2.1`  |
| `gmqtt`     | 0.7.0   | `MIT`                     | 2024-11-22     | no            |

## Decision

The `Network` port becomes a `Protocol` in `twinflow.kernel`, beside `Clock`,
carrying the four calls section 2 of ARCHITECTURE.md gives the seam. Its
simulation adapter is an in-memory bus in the kernel, ordered deterministically.
Its production adapter wraps `paho-mqtt` version 2.1.0, taken under the
BSD-3-Clause half of that project's `EPL-2.0 OR BSD-3-Clause` dual license, and
lives under the kernel's production adapter path, which
`docs/design/foundations.md` already exempts from the determinism lint. The
client is an optional extra under doctrine D-10, so the base install stays pure
Python and a reader taking one brick never resolves it.

## Alternatives considered

| Alternative                                    | Why it lost                                                                                                                                                                                                                                                                                                            |
| ---------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `aiomqtt`                                      | The most actively released of the three, and it resolves `paho-mqtt>=2.1.0,<3.0.0` into the tree regardless. So it inherits the same license question and adds a dependency to reach it. Its asynchronous surface also puts the event loop's clock underneath a seam whose only timeout primitive is `Clock.timeout`.  |
| `gmqtt`                                        | MIT, needing no license reasoning at all, and more recently released than paho. It lost on the same clock argument, and on being a standalone client with no relationship to the Eclipse project that publishes the Sparkplug specification this repository implements.                                                |
| Take `paho-mqtt` under EPL-2.0                 | A dual-licensed dependency is taken under one of its licenses, not both. EPL-2.0 is weak copyleft with no allowlist row, and adding one to accept a license the BSD-3-Clause half makes unnecessary is a condition taken on for nothing.                                                                               |
| Write the MQTT client here                     | Decision D14 in ADR-0002 wrote an agent seam rather than adopt a framework, so the precedent exists. It does not carry: an agent seam is a few hundred lines over a schema, and an MQTT 3.1.1 and 5.0 client with TLS, session state, and will handling is a protocol implementation nobody asked this project to own. |
| Put the port in a new `twinflow-edge` package  | Section 2.9 of `docs/design/iot-fleet.md` does place the edge agent there, and that package is still the right home for the connection state machine and the store-and-forward buffer. The port itself is not: ARCHITECTURE.md gives the kernel all four seams, and a port in a leaf package inverts the layering.     |
| Leave the OT half of the garage tier unstarted | The cheapest option, and it makes RA-b assert a segmentation claim over a topology with nothing on the OT segment. Gate VAL-GATE-QS-001 also times a quickstart ending on a live dashboard serving non-empty state, which no arrangement of unstarted containers reaches.                                              |

## Consequences

What this buys. The fourth seam exists, so a device can publish without knowing
which mode it is in. The fault catalog of section 5.24 of
`docs/design/iot-fleet.md` gets the in-memory transport it drives in simulation
mode. `twinflow.sensors` keeps its layering: it still publishes value objects
and still imports no transport. The garage tier gets a runtime, which is what
turns VAL-GATE-QS-001 from unarmable into merely unmet.

What it costs. A dependency now needs watching, and its most recent release is
2024-04-29, which is the oldest of the three candidates. The license is held by
a choice this project makes rather than by the dependency's own metadata. So the
allowlist gate has to record which half of the dual license was taken, and a
tool reading `EPL-2.0 OR BSD-3-Clause` and matching the first token would refuse
the build. The in-memory bus is a second implementation of message delivery, and
two implementations of one contract disagree unless something asserts they do
not.

The obligation this creates: `paho-mqtt` is taken under BSD-3-Clause, and the
NOTICE file and the allowlist row both have to say so. A future release that
drops the BSD-3-Clause half returns this decision to the table.

## Validation

VAL-GATE-SEC-001 holds the license half: the allowlist gate refuses a resolved
dependency with no row, and the row added for `paho-mqtt` names BSD-3-Clause as
the half taken. VAL-GATE-DET-001 holds the determinism half, because a run over
the in-memory bus is part of the hashed event log and a nondeterministic
delivery order changes the hash.

Nothing yet holds the claim that the two adapters implement one contract. That
is stated plainly here rather than left implied. Until a shared conformance
suite runs against both, the two agree only by construction, and this record is
where a later reader learns it was known at the time.
