"""RA-b, the Purdue segmentation of the garage compose, held to its own rules.

Two things are asserted separately here. That the shipped topology and the
shipped broker config satisfy the five rules is the gate. That the checker can
say otherwise is the evidence the gate is a gate at all, because a check written
against a document that already passes is a check nobody has watched refuse
anything (doctrine D-12).

RULE-5 gets its own corpus because it reads a mosquitto config rather than a
compose document. The case that matters is a broker with two listeners and one
copy of the TLS settings: mosquitto applies a listener option to the listener
declared above it, so that config authenticates clients on one listener and
leaves the other with transport encryption and no client certificate. A reader
that scans the file flat sees `require_certificate true` and reports the broker
demanding an identity.
"""

from __future__ import annotations

import importlib.util
import textwrap
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
GATE = REPO_ROOT / "scripts" / "checks" / "compose-segmentation-gate.py"
SHIPPED_BROKER_CONFIG = REPO_ROOT / "deploy" / "garage" / "mosquitto" / "mosquitto.conf"


def _load():
    """Import the checker by path, because its filename is not an identifier."""
    spec = importlib.util.spec_from_file_location("compose_segmentation_gate", GATE)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


gate = _load()


def test_the_shipped_topology_passes():
    """The gate itself, run the way the phase-exit runner runs it."""
    assert gate.main([]) == 0


def test_the_selftest_runs_clean():
    assert gate.main(["--selftest"]) == 0


def test_the_shipped_broker_demands_an_identity_on_every_listener():
    assert gate.broker_findings(SHIPPED_BROKER_CONFIG.read_text(encoding="utf-8")) == []


@pytest.mark.parametrize(
    ("description", "config", "should_find"),
    gate.BROKER_SELFTEST_CASES,
    ids=[case[0] for case in gate.BROKER_SELFTEST_CASES],
)
def test_each_broker_case_lands_the_way_it_says(description: str, config: str, should_find: bool):
    assert bool(gate.broker_findings(textwrap.dedent(config))) is should_find


def test_one_copy_of_the_tls_settings_does_not_cover_two_listeners():
    """The refusal RULE-5 exists for.

    Every setting rule 5 names is present in this config and spelled correctly.
    What is wrong is where they sit: below both listeners, so they configure the
    second and leave the first taking clients with no certificate at all.
    """
    findings = gate.broker_findings(
        textwrap.dedent(
            """
            per_listener_settings false
            listener 8883
            cafile /c/ca.crt
            listener 8884
            cafile /c/ca.crt
            require_certificate true
            use_identity_as_username true
            allow_anonymous false
            acl_file /mosquitto/config/acl
            """
        )
    )

    assert findings
    assert all("8883" in finding for finding in findings)


def test_a_listener_owns_the_settings_written_under_it():
    """The parse the refusal above rests on, asserted directly so a change to it
    names itself rather than showing up as a rule that quietly stopped firing."""
    globals_, listeners = gate.parse_broker_config(
        textwrap.dedent(
            """
            allow_anonymous false
            listener 8883
            require_certificate true
            listener 8884
            require_certificate false
            """
        )
    )

    assert globals_["allow_anonymous"] == "false"
    assert [port for port, _ in listeners] == ["8883", "8884"]
    assert listeners[0][1]["require_certificate"] == "true"
    assert listeners[1][1]["require_certificate"] == "false"
