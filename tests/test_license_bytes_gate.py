"""The license bytes gate (LIC-001).

The interesting assertion is the one about one byte. The published Apache-2.0
text opens with a bare newline, and the copy in this repository was missing it
until this gate was written, so "byte-identical" was already false while every
human reading the file would have called it correct. That is the whole reason
the check is a digest rather than a diff of the visible text.
"""

from __future__ import annotations

import hashlib
import importlib.util
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
GATE = REPO_ROOT / "scripts" / "checks" / "license-bytes-gate.py"


def _gate():
    spec = importlib.util.spec_from_file_location("license_bytes_gate", GATE)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


gate = _gate()


def test_the_repository_license_is_the_published_text():
    assert gate.digest(REPO_ROOT / "LICENSE") == gate.APACHE_2_0_SHA256


def test_the_pinned_length_and_digest_agree():
    assert (REPO_ROOT / "LICENSE").stat().st_size == gate.APACHE_2_0_BYTES


def test_every_package_carries_the_same_license_and_a_notice():
    packages = sorted((REPO_ROOT / "packages").glob("*/pyproject.toml"))
    assert packages, "no packages found, so this assertion proved nothing"
    for manifest in packages:
        package = manifest.parent
        assert gate.digest(package / "LICENSE") == gate.APACHE_2_0_SHA256
        assert (package / "NOTICE").read_text(encoding="utf-8").strip()


def test_one_dropped_byte_fails(tmp_path):
    # The exact defect this gate was written for: the published text minus its
    # leading newline still reads as the Apache License to a human.
    published = (REPO_ROOT / "LICENSE").read_bytes()
    mangled = published.lstrip(b"\n")
    assert mangled != published
    assert hashlib.sha256(mangled).hexdigest() != gate.APACHE_2_0_SHA256

    path = tmp_path / "LICENSE"
    path.write_bytes(mangled)
    assert gate.digest(path) != gate.APACHE_2_0_SHA256


def test_the_notice_and_the_commercial_option_are_present():
    assert (REPO_ROOT / "NOTICE").read_text(encoding="utf-8").strip()
    licensing = (REPO_ROOT / "LICENSING.md").read_text(encoding="utf-8").lower()
    for marker in gate.COMMERCIAL_MARKERS:
        assert marker.lower() in licensing


def test_this_repository_passes_its_own_gate():
    # The default run reads no network. --online is the half that does, and it
    # is not run here for the same reason CON-1 keeps it out of the default.
    assert gate.main([]) == 0
