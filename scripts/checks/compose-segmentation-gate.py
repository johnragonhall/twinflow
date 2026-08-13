#!/usr/bin/env python3
"""Purdue segmentation gate, RA-b.

ARCHITECTURE.md section 7 states five rules and then says which of them CI
asserts statically. This is that static half, read over every compose file under
deploy/. The two runtime halves, a TCP connection from `it` to a device and a
publish outside a device's own prefix, belong to the integration suite and are
not attempted here.

    Rule 1  Single crossing point   the broker is the only service attached to
                                    `ot` and any other network
    Rule 2  No IT to device path    no device is attached to `it`
    Rule 3  DMZ mediates            a service on `dmz` is on `dmz` and `it`,
                                    never on `ot`
    Rule 4  OT does not reach out   `ot` is declared internal: true
    Rule 5  Identity, not location  the broker config requires a client
                                    certificate, refuses anonymous clients, and
                                    names an ACL file

Rule 3 is vacuous at the garage tier, where section 7's tier table collapses
`dmz` into `it`. It is implemented all the same, so the growth-tier compose
inherits it the day that file lands.

Roles are read from the `com.twinflow.role` label rather than from the service
name. A rule keyed on a name is a rule that a rename evades, and the rename
looks like tidying in a diff.

Usage:

    python scripts/checks/compose-segmentation-gate.py            every deploy/ compose file
    python scripts/checks/compose-segmentation-gate.py PATH ...   named files
    python scripts/checks/compose-segmentation-gate.py --selftest prove each rule fires

Needs PyYAML. Unlike the prose gate this one fails rather than skipping without
it: a segmentation gate that exits zero when it read nothing is the kind of gate
that has never been seen to fail because it cannot.
"""

from __future__ import annotations

import argparse
import contextlib
import io
import sys
from pathlib import Path
from typing import Any

for _stream in (sys.stdout, sys.stderr):
    if isinstance(_stream, io.TextIOWrapper):
        # reconfigure raises on an encoding this platform lacks.
        with contextlib.suppress(ValueError):
            _stream.reconfigure(encoding="utf-8")

REPO_ROOT = Path(__file__).resolve().parents[2]
DEPLOY_ROOT = REPO_ROOT / "deploy"

RED = "\033[31m"
GREEN = "\033[32m"
RESET = "\033[0m"

#: The OT segment, the mediated zone, and the IT segment, by the names section 7
#: gives them. A compose file that spells one of them differently is describing
#: a different topology, and the gate reports the network it could not find.
OT = "ot"
DMZ = "dmz"
IT = "it"

#: Roles a service may declare. `device` and `broker` carry rules of their own;
#: `historian` and `app` are IT-side and are distinguished only so the compose
#: file reads as the topology rather than as a list of containers.
ROLES = frozenset({"device", "broker", "historian", "app"})

#: Settings mosquitto.conf has to carry for rule 5's static half.
BROKER_TLS_SETTINGS = {
    "require_certificate": "true",
    "allow_anonymous": "false",
    "use_identity_as_username": "true",
}


class Finding:
    """One violated rule, with the file and the service that violated it."""

    __slots__ = ("rule", "where", "message")

    def __init__(self, rule: str, where: str, message: str) -> None:
        self.rule = rule
        self.where = where
        self.message = message

    def render(self) -> str:
        return f"  [{self.rule}] {self.where}\n      {self.message}"


def _service_networks(service: dict) -> list[str]:
    """The networks one service lists, in either compose form.

    Compose accepts a sequence of names and a mapping of name to options, and a
    gate that understands only one of them passes a file written in the other.
    """
    declared = service.get("networks")
    if declared is None:
        return []
    if isinstance(declared, dict):
        return [str(name) for name in declared]
    if isinstance(declared, list):
        return [str(name) for name in declared]
    return [str(declared)]


def _role(service: dict) -> str | None:
    labels = service.get("labels")
    if isinstance(labels, dict):
        value = labels.get("com.twinflow.role")
        return str(value) if value is not None else None
    if isinstance(labels, list):
        for item in labels:
            text = str(item)
            if text.startswith("com.twinflow.role="):
                return text.split("=", 1)[1]
    return None


def check_document(document: Any, where: str) -> list[Finding]:
    """Apply every static rule to one parsed compose document."""
    findings: list[Finding] = []

    if not isinstance(document, dict):
        return [Finding("COMPOSE-0", where, "this file does not parse as a compose document")]

    networks = document.get("networks") or {}
    services = document.get("services") or {}

    if not isinstance(services, dict) or not services:
        return [Finding("COMPOSE-0", where, "this compose file declares no services")]

    # Rule 4. The whole OT segment rests on one attribute, so a missing or false
    # `internal` is reported before anything else: without it the other four
    # rules describe a segment that has a route to the internet.
    if OT not in networks:
        findings.append(
            Finding(
                "RULE-4",
                where,
                f"no network named {OT!r} is declared, so this file states no OT boundary",
            )
        )
    else:
        ot_options = networks.get(OT) or {}
        if not isinstance(ot_options, dict) or ot_options.get("internal") is not True:
            findings.append(
                Finding(
                    "RULE-4",
                    f"{where}  networks.{OT}",
                    "the OT segment is not declared `internal: true`, so its containers "
                    "get a default gateway and can reach the internet",
                )
            )

    # The `ot` and `it` split is the architectural claim, and section 7 keeps it
    # at every tier. A compose file that drops one of the two is a different
    # system wearing the same file name.
    if IT not in networks:
        findings.append(
            Finding(
                "RULE-4",
                where,
                f"no network named {IT!r} is declared, so the OT and IT split is not expressed",
            )
        )

    crossers: list[str] = []

    for name, service in sorted(services.items()):
        if not isinstance(service, dict):
            continue
        location = f"{where}  services.{name}"
        attached = _service_networks(service)
        role = _role(service)

        if role is None:
            findings.append(
                Finding(
                    "ROLE-1",
                    location,
                    "no com.twinflow.role label, so no rule below can be applied to it. "
                    f"Declare one of: {', '.join(sorted(ROLES))}",
                )
            )
            continue
        if role not in ROLES:
            findings.append(
                Finding(
                    "ROLE-1",
                    location,
                    f"com.twinflow.role is {role!r}, which is not one of: "
                    f"{', '.join(sorted(ROLES))}",
                )
            )
            continue

        if not attached:
            findings.append(
                Finding(
                    "ROLE-1",
                    location,
                    "lists no networks, so compose puts it on the default bridge and "
                    "the segmentation this file claims does not hold for it",
                )
            )
            continue

        # Rule 1. Anything on `ot` plus something else is a crossing point.
        if OT in attached and len(set(attached)) > 1:
            crossers.append(name)
            if role != "broker":
                findings.append(
                    Finding(
                        "RULE-1",
                        location,
                        f"role {role!r} is attached to {OT!r} and to "
                        f"{', '.join(sorted(set(attached) - {OT}))}. The broker is the only "
                        "container that may cross, because every byte leaving OT leaves "
                        "through it",
                    )
                )

        # Rule 2. A device belongs to the OT segment and to nothing else.
        if role == "device":
            outside = sorted(set(attached) - {OT})
            if outside:
                findings.append(
                    Finding(
                        "RULE-2",
                        location,
                        f"a device is attached to {', '.join(outside)}. A device is on "
                        f"{OT!r} and nowhere else, so no container on {IT!r} has a route "
                        "to it",
                    )
                )

        # Rule 3. A container in the mediated zone talks north and south, never
        # into OT. Vacuous where `dmz` is collapsed, which is the garage tier.
        if DMZ in attached:
            if OT in attached:
                findings.append(
                    Finding(
                        "RULE-3",
                        location,
                        f"a {DMZ!r} container is attached to {OT!r}. IT systems talk to "
                        "the DMZ and the DMZ talks to the broker, so the DMZ never "
                        "reaches into OT itself",
                    )
                )
            if IT not in attached:
                findings.append(
                    Finding(
                        "RULE-3",
                        location,
                        f"a {DMZ!r} container is not attached to {IT!r}, so nothing it "
                        "mediates is reachable and the zone mediates nothing",
                    )
                )

    if OT in networks and not crossers:
        findings.append(
            Finding(
                "RULE-1",
                where,
                f"nothing crosses out of {OT!r}. A segment with no crossing point publishes "
                "no data, so this file is not the topology it claims to be",
            )
        )
    elif len(crossers) > 1:
        findings.append(
            Finding(
                "RULE-1",
                where,
                f"{len(crossers)} containers cross out of {OT!r}: {', '.join(sorted(crossers))}. "
                "Exactly one may",
            )
        )

    return findings


def _display(path: Path) -> str:
    """A repository-relative path where there is one, and the full path otherwise."""
    if path.is_absolute() and path.is_relative_to(REPO_ROOT):
        return path.relative_to(REPO_ROOT).as_posix()
    return path.as_posix()


def check_broker_config(compose_path: Path, where: str) -> list[Finding]:
    """Rule 5's static half: the broker demands an identity before a topic.

    Read from the file the compose document mounts as the broker config. A
    broker with no config file mounted is reported rather than assumed safe.
    """
    config = compose_path.parent / "mosquitto" / "mosquitto.conf"
    if not config.is_file():
        return [
            Finding(
                "RULE-5",
                f"{where}  {_display(config)}",
                "no broker configuration beside this compose file, so nothing states "
                "that a device has to present a certificate",
            )
        ]

    settings: dict[str, str] = {}
    acl_file = None
    for line in config.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        parts = stripped.split(None, 1)
        key = parts[0]
        value = parts[1].strip() if len(parts) > 1 else ""
        if key in BROKER_TLS_SETTINGS:
            settings[key] = value.lower()
        elif key == "acl_file":
            acl_file = value

    findings: list[Finding] = []
    location = f"{where}  {_display(config)}"

    for key, expected in sorted(BROKER_TLS_SETTINGS.items()):
        actual = settings.get(key)
        if actual != expected:
            findings.append(
                Finding(
                    "RULE-5",
                    location,
                    f"{key} is {actual or 'unset'}, and identity rather than location "
                    f"needs {key} {expected}",
                )
            )

    if not acl_file:
        findings.append(
            Finding(
                "RULE-5",
                location,
                "no acl_file, so an authenticated device may publish under any prefix "
                "including another area's",
            )
        )

    return findings


def compose_files(explicit: list[str]) -> list[Path]:
    if explicit:
        return [Path(item).resolve() for item in explicit]
    if not DEPLOY_ROOT.is_dir():
        return []
    found = sorted(
        path
        for pattern in ("**/docker-compose.yaml", "**/docker-compose.yml", "**/compose.yaml")
        for path in DEPLOY_ROOT.glob(pattern)
    )
    return found


def _load(path: Path) -> Any:
    import yaml

    return yaml.safe_load(path.read_text(encoding="utf-8"))


SELFTEST_CASES: tuple[tuple[str, str, str], ...] = (
    (
        "RULE-4",
        "ot declared without internal",
        """
        networks: {ot: {}, it: {}}
        services:
          broker: {labels: {com.twinflow.role: broker}, networks: [ot, it]}
          device-a: {labels: {com.twinflow.role: device}, networks: [ot]}
        """,
    ),
    (
        "RULE-1",
        "a second container crosses out of ot",
        """
        networks: {ot: {internal: true}, it: {}}
        services:
          broker: {labels: {com.twinflow.role: broker}, networks: [ot, it]}
          historian: {labels: {com.twinflow.role: historian}, networks: [ot, it]}
          device-a: {labels: {com.twinflow.role: device}, networks: [ot]}
        """,
    ),
    (
        "RULE-2",
        "a device is reachable from it",
        """
        networks: {ot: {internal: true}, it: {}}
        services:
          broker: {labels: {com.twinflow.role: broker}, networks: [ot, it]}
          device-a: {labels: {com.twinflow.role: device}, networks: [ot, it]}
        """,
    ),
    (
        "RULE-3",
        "a dmz container reaches into ot",
        """
        networks: {ot: {internal: true}, dmz: {}, it: {}}
        services:
          broker: {labels: {com.twinflow.role: broker}, networks: [ot, dmz]}
          historian: {labels: {com.twinflow.role: historian}, networks: [dmz, it, ot]}
          device-a: {labels: {com.twinflow.role: device}, networks: [ot]}
        """,
    ),
    (
        "ROLE-1",
        "a service with no role label",
        """
        networks: {ot: {internal: true}, it: {}}
        services:
          broker: {labels: {com.twinflow.role: broker}, networks: [ot, it]}
          mystery: {networks: [it]}
          device-a: {labels: {com.twinflow.role: device}, networks: [ot]}
        """,
    ),
)


def selftest() -> int:
    """Prove each rule fires, and that the shipped topology is clean.

    A gate nobody has seen fail may be passing because it cannot. Each case
    below breaks exactly one rule, and the case fails if that rule stays quiet.
    """
    import textwrap

    import yaml

    failures: list[str] = []

    for rule, description, source in SELFTEST_CASES:
        document = yaml.safe_load(textwrap.dedent(source))
        fired = {finding.rule for finding in check_document(document, "<selftest>")}
        if rule not in fired:
            failures.append(
                f"{rule} did not fire on: {description} (fired: {sorted(fired) or 'nothing'})"
            )

    clean = yaml.safe_load(
        textwrap.dedent(
            """
            networks: {ot: {internal: true}, it: {}}
            services:
              broker: {labels: {com.twinflow.role: broker}, networks: [ot, it]}
              device-a: {labels: {com.twinflow.role: device}, networks: [ot]}
              historian: {labels: {com.twinflow.role: historian}, networks: [it]}
            """
        )
    )
    noise = check_document(clean, "<selftest>")
    if noise:
        failures.append("a legal garage topology reported: " + ", ".join(f.rule for f in noise))

    if failures:
        sys.stderr.write(f"\n{RED}BLOCKED: compose segmentation selftest [RA-b]{RESET}\n")
        for failure in failures:
            sys.stderr.write(f"  {failure}\n")
        return 1

    print(
        f"{GREEN}[segmentation] selftest: {len(SELFTEST_CASES)} rules fire, "
        f"and a legal topology stays quiet{RESET}"
    )
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("paths", nargs="*", help="compose files to check")
    parser.add_argument("--selftest", action="store_true", help="prove each rule fires")
    args = parser.parse_args(argv)

    try:
        import yaml  # noqa: F401
    except ModuleNotFoundError:
        sys.stderr.write(
            f"\n{RED}BLOCKED: PyYAML is not installed, and this gate reads YAML "
            f"[RA-b]{RESET}\n  uv sync, or run it through `uv run`\n"
        )
        return 1

    if args.selftest:
        return selftest()

    paths = compose_files(args.paths)
    if not paths:
        sys.stderr.write(
            f"\n{RED}BLOCKED: no compose file under deploy/ [RA-b]{RESET}\n"
            "  RA-b says the Purdue segmentation is expressed in docker compose.\n"
            "  With no compose file there is nothing expressing it.\n"
        )
        return 1

    findings: list[Finding] = []
    for path in paths:
        where = _display(path)
        document = _load(path)
        file_findings = check_document(document, where)
        findings += file_findings
        if not any(finding.rule == "COMPOSE-0" for finding in file_findings):
            findings += check_broker_config(path, where)

    if findings:
        sys.stderr.write(f"\n{RED}BLOCKED: Purdue segmentation is broken [RA-b]{RESET}\n")
        for finding in findings:
            sys.stderr.write(finding.render() + "\n")
        sys.stderr.write(
            "\nARCHITECTURE.md section 7 states the five rules and which of them are "
            "asserted statically.\n"
        )
        return 1

    print(
        f"[segmentation] {len(paths)} compose file(s): one crossing point, no device on the "
        f"IT segment, the OT segment internal, and the broker demanding an identity"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
