def test_package_imports_and_declares_a_version():
    import twinflow.sensors as sensors

    assert isinstance(sensors.__version__, str)
    assert sensors.__version__.count(".") == 2


def test_the_namespace_is_assembled_from_several_installed_wheels():
    """PEP 420 in action: twinflow/ has no __init__.py in any distribution.

    If any distribution shipped one the namespace would collapse to a single
    path and the other packages would be invisible. Asserting the paths by name
    fails loudly, where a count would also pass on a machine that happened to
    have one more twinflow.* package installed.
    """
    import twinflow

    paths = [str(entry).replace("\\", "/") for entry in twinflow.__path__]
    assert any(p.endswith("twinflow-sensors/src/twinflow") for p in paths), paths
    assert any(p.endswith("twinflow-kernel/src/twinflow") for p in paths), paths
    assert any(p.endswith("twinflow-config/src/twinflow") for p in paths), paths


def test_every_exported_name_is_defined_here():
    """Doctrine D-09 in miniature, and CI gate IMPORT-3 in full later."""
    import twinflow.sensors as sensors

    undefined = [name for name in sensors.__all__ if not hasattr(sensors, name)]
    assert undefined == []


def test_the_export_list_is_sorted_so_two_readers_scan_it_the_same_way():
    import twinflow.sensors as sensors

    assert list(sensors.__all__) == sorted(sensors.__all__)
