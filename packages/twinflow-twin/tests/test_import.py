def test_package_imports_and_declares_a_version():
    import twinflow.twin as twin

    assert isinstance(twin.__version__, str)
    assert twin.__version__.count(".") == 2


def test_the_namespace_holds_this_package_beside_the_ones_it_depends_on():
    """PEP 420 in action: twinflow/ is assembled from several installed wheels.

    If any distribution shipped a twinflow/__init__.py the namespace would
    collapse to one path and the others would be invisible. Asserting the paths
    by name fails loudly, where a count would also pass on a machine that
    happened to have one more twinflow.* package installed.
    """
    import twinflow

    paths = [str(entry).replace("\\", "/") for entry in twinflow.__path__]
    assert any(p.endswith("twinflow-twin/src/twinflow") for p in paths), paths
    assert any(p.endswith("twinflow-kernel/src/twinflow") for p in paths), paths


def test_every_exported_name_is_defined_here():
    """Doctrine D-09 in miniature, and CI gate IMPORT-3 in full later."""
    import twinflow.twin as twin

    undefined = [name for name in twin.__all__ if not hasattr(twin, name)]
    assert undefined == []


def test_the_public_surface_is_sorted_and_carries_the_version():
    """A package with no __all__, or an unsorted one, fails the boundary gate."""
    import twinflow.twin as twin

    assert twin.__all__ == sorted(twin.__all__)
    assert "__version__" in twin.__all__


def test_the_discrete_event_framework_is_the_pinned_one():
    """ARCH-1, decision D1. SimPy 4 is the framework, and it is really used.

    A twin that declared SimPy and then hand-rolled its own event loop would
    satisfy the dependency list and none of the reason for it.
    """
    import simpy

    from twinflow.twin import station

    assert simpy.__version__.startswith("4.")
    assert station.simpy is simpy
