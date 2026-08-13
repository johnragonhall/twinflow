def test_package_imports_and_ships_its_single_file():
    import twinflow.dashboard as dashboard

    assert dashboard.__version__.count(".") == 2
    assert (dashboard.viewer_asset_root() / dashboard.INDEX_FILENAME).is_file()


def test_both_distributions_share_one_namespace_path():
    """PEP 420 in action: twinflow/ is assembled from several installed wheels.

    If any distribution shipped a twinflow/__init__.py the namespace would
    collapse to one path and the others would be invisible. Asserting the two
    paths by name fails loudly, where a count would also pass on a machine that
    happened to have a third twinflow.* package installed.
    """
    import twinflow

    paths = [str(entry).replace("\\", "/") for entry in twinflow.__path__]
    assert any(p.endswith("twinflow-schemas/src/twinflow") for p in paths), paths
    assert any(p.endswith("twinflow-dashboard/src/twinflow") for p in paths), paths


def test_every_exported_name_is_defined_here():
    """Doctrine D-09 in miniature, and CI gate IMPORT-3 in full later."""
    import twinflow.dashboard as dashboard

    undefined = [name for name in dashboard.__all__ if not hasattr(dashboard, name)]
    assert undefined == []


def test_the_shipped_assets_travel_with_the_wheel():
    """`twinflow-dashboard demo` is the A1 proof: install one thing and see a
    working dashboard. A wheel that left index.html behind would import fine and
    serve a 500 on the first request."""
    import tomllib
    from pathlib import Path

    import twinflow.dashboard as dashboard

    manifest = tomllib.loads(
        (Path(dashboard.__file__).resolve().parents[3] / "pyproject.toml").read_text(
            encoding="utf-8"
        )
    )
    wheel = manifest["tool"]["hatch"]["build"]["targets"]["wheel"]

    assert wheel["packages"] == ["src/twinflow"]
    assert "**/assets/*.html" not in manifest["tool"]["hatch"]["build"]["targets"]["sdist"].get(
        "exclude", []
    )


def test_the_gate_this_package_serves_names_its_published_reference():
    """Doctrine D-11: a validation gate rests on external evidence, so the
    reference is a published standard rather than a document in this tree."""
    import twinflow.dashboard as dashboard

    assert dashboard.A11Y_GATE_ID == "VAL-GATE-A11Y-001"
    assert dashboard.WCAG_REFERENCE_URL.startswith("https://www.w3.org/TR/WCAG21/")
