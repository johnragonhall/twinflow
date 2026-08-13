def test_package_imports_and_declares_its_url_major():
    import twinflow.api as api

    assert api.API_PREFIX == "/api/v1"
    assert api.__version__.count(".") == 2


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
    assert any(p.endswith("twinflow-api/src/twinflow") for p in paths), paths


def test_every_exported_name_is_defined_here():
    """Doctrine D-09 in miniature, and CI gate IMPORT-3 in full later."""
    import twinflow.api as api

    undefined = [name for name in api.__all__ if not hasattr(api, name)]
    assert undefined == []


def test_the_three_unversioned_paths_stay_outside_the_versioned_prefix():
    """Foundations section 5.13 puts /healthz, /readyz, and /version outside
    /api/v1 so an orchestrator probe survives an API major bump."""
    import twinflow.api as api

    assert not any(path.startswith(api.API_PREFIX) for path in api.UNVERSIONED_PATHS)


def test_every_problem_code_is_unique():
    """The code is what a client branches on. Two problems sharing one code
    would make that branch pick the wrong recovery."""
    import twinflow.api as api

    codes = [problem.code for problem in api.PROBLEMS]
    assert len(codes) == len(set(codes))
    assert codes == sorted(codes)
    assert all(code.startswith("TF-A") for code in codes)
