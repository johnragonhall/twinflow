"""What the published artifacts actually contain.

Every other test here reads the source tree, which is a different thing from
what ships. A wheel that omits the package, an sdist carrying the monorepo's
tooling, a distribution with no LICENSE, or metadata whose version disagrees
with the module: each one passes an import test and still publishes something
broken.

These build the real distributions, so they are marked slow and stay out of the
fast tier.
"""

from __future__ import annotations

import re
import subprocess
import tarfile
import zipfile
from pathlib import Path

import pytest

import twinflow.schemas as schemas

PACKAGE_ROOT = Path(__file__).resolve().parents[1]
WORKSPACE_ROOT = PACKAGE_ROOT.parents[1]

pytestmark = pytest.mark.slow


@pytest.fixture(scope="module")
def dists(tmp_path_factory: pytest.TempPathFactory) -> tuple[Path, Path]:
    """Build both distributions once, and hand back (wheel, sdist)."""
    out = tmp_path_factory.mktemp("dist")
    result = subprocess.run(
        ["uv", "build", "--package", "twinflow-schemas", "-o", str(out)],
        cwd=WORKSPACE_ROOT,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr

    wheels = list(out.glob("*.whl"))
    sdists = list(out.glob("*.tar.gz"))
    assert len(wheels) == 1, wheels
    assert len(sdists) == 1, sdists
    return wheels[0], sdists[0]


def test_wheel_carries_the_package_and_no_namespace_init(dists: tuple[Path, Path]) -> None:
    """The source-tree namespace test cannot see what the build put in the wheel."""
    wheel, _ = dists
    with zipfile.ZipFile(wheel) as zf:
        names = zf.namelist()

    assert "twinflow/schemas/__init__.py" in names, names
    assert "twinflow/__init__.py" not in names, names


def test_wheel_metadata_version_is_the_module_version(dists: tuple[Path, Path]) -> None:
    """One version, read from the module by the build, so the two cannot drift.

    The version used to be written twice, once in pyproject.toml and once as
    __version__, with nothing comparing them. tool.hatch.version now reads the
    module, and this asserts the build honored it.
    """
    wheel, _ = dists
    with zipfile.ZipFile(wheel) as zf:
        metadata_name = next(n for n in zf.namelist() if n.endswith(".dist-info/METADATA"))
        metadata = zf.read(metadata_name).decode("utf-8")

    declared = re.search(r"^Version: (.+)$", metadata, re.MULTILINE)
    assert declared is not None, metadata[:500]
    assert declared.group(1).strip() == schemas.__version__


def test_both_distributions_carry_the_license_and_the_notice(dists: tuple[Path, Path]) -> None:
    """Apache-2.0 section 4(a) and 4(d).

    4(a) requires a copy of the License to reach every recipient of the work,
    and 4(d) requires the NOTICE text to travel with it. A wheel published
    without them is a license breach, and it is invisible from the source tree.
    """
    wheel, sdist = dists
    with zipfile.ZipFile(wheel) as zf:
        wheel_names = zf.namelist()
    assert any(n.endswith(".dist-info/licenses/LICENSE") for n in wheel_names), wheel_names
    assert any(n.endswith(".dist-info/licenses/NOTICE") for n in wheel_names), wheel_names

    with tarfile.open(sdist) as tf:
        sdist_names = tf.getnames()
    assert any(n.endswith("/LICENSE") for n in sdist_names), sdist_names
    assert any(n.endswith("/NOTICE") for n in sdist_names), sdist_names


def test_sdist_ships_this_package_gitignore_not_the_repository_one(
    dists: tuple[Path, Path],
) -> None:
    """hatchling force-includes whichever .gitignore it located.

    It walks up from the package until it reaches .git and consults no setting
    that can stop it, so without a .gitignore beside this package it publishes
    the repository root's, which describes local agent tooling and means
    nothing to somebody unpacking one package from PyPI. Comparing bytes rather
    than looking for a phrase keeps this from passing on a near miss.
    """
    _, sdist = dists
    with tarfile.open(sdist) as tf:
        ignored = [n for n in tf.getnames() if n.endswith(".gitignore")]
        assert len(ignored) == 1, ignored
        member = tf.extractfile(ignored[0])
        assert member is not None
        shipped = member.read()

    assert shipped == (PACKAGE_ROOT / ".gitignore").read_bytes()


def test_sdist_carries_the_sources_and_the_tests(dists: tuple[Path, Path]) -> None:
    """An sdist a consumer cannot build and test is not a source distribution."""
    _, sdist = dists
    with tarfile.open(sdist) as tf:
        names = tf.getnames()

    assert any(n.endswith("/src/twinflow/schemas/__init__.py") for n in names), names
    assert any(n.endswith("/tests/test_import.py") for n in names), names
    assert any(n.endswith("/pyproject.toml") for n in names), names
