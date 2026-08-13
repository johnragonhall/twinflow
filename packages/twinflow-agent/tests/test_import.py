"""The package imports, and its declared surface is the surface it has."""


def test_package_imports_and_declares_a_version():
    import twinflow.agent as agent

    assert isinstance(agent.__version__, str)
    assert agent.__version__.count(".") == 2


def test_every_exported_name_is_defined_here():
    """Doctrine D-09 in miniature, and CI gate IMPORT-3 in full later."""
    import twinflow.agent as agent

    undefined = [name for name in agent.__all__ if not hasattr(agent, name)]
    assert undefined == []


def test_the_exported_names_are_sorted_and_unique():
    """A sorted __all__ makes a diff show what changed rather than where it
    landed, and a duplicate means two things claimed one name."""
    import twinflow.agent as agent

    assert list(agent.__all__) == sorted(agent.__all__)
    assert len(set(agent.__all__)) == len(agent.__all__)


def test_the_namespace_is_assembled_from_several_installed_wheels():
    """PEP 420 in action. If any distribution shipped a twinflow/__init__.py the
    namespace would collapse to one path and the rest would be invisible."""
    import twinflow

    paths = [str(entry).replace("\\", "/") for entry in twinflow.__path__]
    assert any(p.endswith("twinflow-agent/src/twinflow") for p in paths), paths
    assert any(p.endswith("twinflow-schemas/src/twinflow") for p in paths), paths
    assert any(p.endswith("twinflow-config/src/twinflow") for p in paths), paths


def test_the_two_halves_of_this_brick_are_importable_on_their_own():
    """A reader who wants the tier rules alone should not have to import the
    tool surface to get them, and the other way round."""
    import twinflow.agent.autonomy as autonomy
    import twinflow.agent.tools as tools

    assert autonomy.AutonomyTier.L1.permits(autonomy.AutonomyTier.L1)
    assert tools.QUERY_METRIC == "query_metric"
