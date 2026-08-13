def test_package_imports_and_declares_a_version():
    import twinflow.storage as storage

    assert isinstance(storage.__version__, str)
    assert storage.__version__.count(".") == 2


def test_the_namespace_holds_this_package_beside_its_dependencies():
    """PEP 420 in action: twinflow/ is assembled from several installed wheels.

    If any distribution shipped a twinflow/__init__.py the namespace would
    collapse to one path and the others would be invisible. Asserting the
    paths by name fails loudly, where a count would also pass on a machine
    that happened to have one more twinflow.* package installed.
    """
    import twinflow

    paths = [str(entry).replace("\\", "/") for entry in twinflow.__path__]
    assert any(p.endswith("twinflow-storage/src/twinflow") for p in paths), paths
    assert any(p.endswith("twinflow-kernel/src/twinflow") for p in paths), paths
    assert any(p.endswith("twinflow-schemas/src/twinflow") for p in paths), paths
    assert any(p.endswith("twinflow-config/src/twinflow") for p in paths), paths


def test_every_exported_name_is_defined_here():
    """Doctrine D-09 in miniature, and CI gate IMPORT-3 in full later."""
    import twinflow.storage as storage

    undefined = [name for name in storage.__all__ if not hasattr(storage, name)]
    assert undefined == []


def test_the_export_list_is_sorted():
    import twinflow.storage as storage

    assert list(storage.__all__) == sorted(storage.__all__)
