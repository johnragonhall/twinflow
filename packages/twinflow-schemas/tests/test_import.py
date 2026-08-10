import re


def test_package_imports_and_declares_a_release_version():
    """The version is a release number, not merely a string with two dots.

    `count(".") == 2` passed for "a.b.c" and for "..", which is no assertion at
    all. The build reads this same attribute through tool.hatch.version, so a
    value that is not a version produces a distribution nobody can resolve.
    """
    import twinflow.schemas as schemas

    assert re.fullmatch(r"\d+\.\d+\.\d+", schemas.__version__), schemas.__version__


def test_namespace_package_has_no_init_at_the_twinflow_level():
    """PEP 420 is what lets two distributions install into twinflow/.

    A twinflow/__init__.py in either distribution would shadow the namespace
    and make the second install invisible. This is the cheap version that fails
    during the task that could introduce it; test_packaging.py asserts the same
    thing against the built wheel, which is what actually ships.
    """
    import twinflow

    assert getattr(twinflow, "__file__", None) is None


def test_every_exported_name_is_defined_here():
    """Doctrine D-09 in miniature, and CI gate IMPORT-3 in full later.

    A name in __all__ that the module does not define raises ImportError for
    every consumer that writes a star import, and leaves a hole in the
    declared surface that no other check looks at.
    """
    import twinflow.schemas as schemas

    undefined = [name for name in schemas.__all__ if not hasattr(schemas, name)]
    assert undefined == []
