#!/usr/bin/env python3
"""License bytes gate LIC-001, the CON-2 half a script can decide.

    python scripts/checks/license-bytes-gate.py
    python scripts/checks/license-bytes-gate.py --online

Four assertions, in the order a legal review makes them:

  1 The repository root carries LICENSE, and its bytes are the Apache License
    2.0 text published at apache.org, to the byte.
  2 NOTICE exists beside it and is not empty.
  3 LICENSING.md states the commercial option, so the dual offer is written
    down rather than implied by a sentence in the README.
  4 Every distributed package carries the same LICENSE and its own NOTICE. A
    wheel is what a user receives, and a wheel with no license file is
    unlicensed however well licensed the repository it came from was.

WHY A DIGEST AND NOT A FETCH
----------------------------
CON-1 puts no outbound network in the default path, and a gate that fetches is
a gate that fails when apache.org is slow. The published bytes are pinned here
as a digest, and --online re-fetches and checks the pin itself, which is the
half that needs a network and therefore does not run by default.

The pin is a digest of the whole file rather than of its text with whitespace
normalized. The published file opens with a bare newline, and a check that
trimmed it would accept a LICENSE that is one byte short of the text it claims
to be.
"""

from __future__ import annotations

import argparse
import hashlib
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]

#: https://www.apache.org/licenses/LICENSE-2.0.txt, 11358 bytes, Last-Modified
#: Sun, 28 Dec 2025 17:09:26 GMT, read 2026-08-13. Re-check it with --online.
APACHE_2_0_SHA256 = "cfc7749b96f63bd31c3c42b5c471bf756814053e847c10f3eb003417bc523d30"
APACHE_2_0_BYTES = 11358
APACHE_2_0_URL = "https://www.apache.org/licenses/LICENSE-2.0.txt"

#: The offer LICENSING.md has to carry. Substrings rather than a sentence,
#: because the wording is the author's and only the offer is the contract.
COMMERCIAL_MARKERS = ("commercial license", "Apache-2.0")


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def check_tree() -> list[str]:
    """Every assertion that reads only this checkout."""
    findings: list[str] = []

    root_license = REPO_ROOT / "LICENSE"
    if not root_license.is_file():
        findings.append("no LICENSE in the repository root")
        return findings

    root_digest = digest(root_license)
    if root_digest != APACHE_2_0_SHA256:
        size = root_license.stat().st_size
        findings.append(
            f"LICENSE is not the published Apache-2.0 text: {size} bytes, "
            f"sha256 {root_digest[:16]}..., expected {APACHE_2_0_BYTES} bytes, "
            f"sha256 {APACHE_2_0_SHA256[:16]}... from {APACHE_2_0_URL}"
        )

    notice = REPO_ROOT / "NOTICE"
    if not notice.is_file():
        findings.append("no NOTICE in the repository root")
    elif not notice.read_text(encoding="utf-8").strip():
        findings.append("NOTICE is empty")

    licensing = REPO_ROOT / "LICENSING.md"
    if not licensing.is_file():
        findings.append("no LICENSING.md, so the commercial option is stated nowhere")
    else:
        text = licensing.read_text(encoding="utf-8").lower()
        missing = [m for m in COMMERCIAL_MARKERS if m.lower() not in text]
        for marker in missing:
            findings.append(f"LICENSING.md does not mention {marker!r}")

    findings.extend(check_packages(root_digest))
    return findings


def check_packages(root_digest: str) -> list[str]:
    """Assertion 4, over every package that produces a wheel."""
    findings: list[str] = []
    packages_dir = REPO_ROOT / "packages"
    if not packages_dir.is_dir():
        return findings

    for manifest in sorted(packages_dir.glob("*/pyproject.toml")):
        package = manifest.parent
        name = package.name

        package_license = package / "LICENSE"
        if not package_license.is_file():
            findings.append(f"{name} carries no LICENSE, so its wheel ships unlicensed")
        elif digest(package_license) != root_digest:
            findings.append(
                f"{name}/LICENSE differs from the root LICENSE. "
                f"Every wheel carries the same text or the texts disagree"
            )

        package_notice = package / "NOTICE"
        if not package_notice.is_file():
            findings.append(f"{name} carries no NOTICE beside its LICENSE")
        elif not package_notice.read_text(encoding="utf-8").strip():
            findings.append(f"{name}/NOTICE is empty")

    return findings


def check_pin() -> list[str]:
    """Re-fetch the published text and check the pin above still describes it.

    Only --online reaches this. It is the one assertion this repository cannot
    make about itself: the pin is a claim about a file on another server, and a
    claim about another server is checked by reading that server.
    """
    import urllib.request

    try:
        with urllib.request.urlopen(APACHE_2_0_URL, timeout=30) as response:
            published = response.read()
    except OSError as error:
        return [f"could not read {APACHE_2_0_URL}: {error}"]

    published_digest = hashlib.sha256(published).hexdigest()
    if published_digest != APACHE_2_0_SHA256:
        return [
            f"the pin no longer describes {APACHE_2_0_URL}: it now serves "
            f"{len(published)} bytes, sha256 {published_digest}. Apache republished "
            f"the text, or something is between this checkout and apache.org. "
            f"Read the diff before touching the pin"
        ]
    print(f"[license] the pin matches {APACHE_2_0_URL} as served now")
    return []


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--online",
        action="store_true",
        help="also re-fetch the published text and check the pinned digest against it",
    )
    args = parser.parse_args(argv)

    findings = check_tree()
    if args.online:
        findings.extend(check_pin())

    if findings:
        sys.stderr.write("\n\033[31mBLOCKED: license bytes [LIC-001]\033[0m\n")
        for finding in findings:
            sys.stderr.write(f"  {finding}\n")
        sys.stderr.write(
            f"\nThe license text is not this repository's to edit. Restore it with\n"
            f"  curl -o LICENSE {APACHE_2_0_URL}\n"
            f"and copy that file to every packages/*/LICENSE. The copyright line\n"
            f"belongs in NOTICE, which is the file Apache-2.0 section 4(d) governs.\n"
        )
        return 1

    packages = len(list((REPO_ROOT / "packages").glob("*/pyproject.toml")))
    print(
        f"[license] LICENSE is the published Apache-2.0 text, NOTICE and LICENSING.md "
        f"are present, and {packages} packages carry both"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
