def test_package_imports_and_declares_a_catalog_version():
    import twinflow.rng as rng

    assert isinstance(rng.STREAM_CATALOG_VERSION, str)
    assert rng.STREAM_CATALOG_VERSION.count(".") == 2


def test_both_distributions_share_one_namespace_path():
    """PEP 420 in action: twinflow/ is assembled from two installed wheels.

    If either distribution shipped a twinflow/__init__.py the namespace would
    collapse to one path and the other package would be invisible. Asserting
    the two paths by name fails loudly, where a count would also pass on a
    machine that happened to have a third twinflow.* package installed.
    """
    import twinflow

    paths = [str(entry).replace("\\", "/") for entry in twinflow.__path__]
    assert any(p.endswith("twinflow-schemas/src/twinflow") for p in paths), paths
    assert any(p.endswith("twinflow-rng/src/twinflow") for p in paths), paths


def test_every_exported_name_is_defined_here():
    """Doctrine D-09 in miniature, and CI gate IMPORT-3 in full later."""
    import twinflow.rng as rng

    undefined = [name for name in rng.__all__ if not hasattr(rng, name)]
    assert undefined == []
