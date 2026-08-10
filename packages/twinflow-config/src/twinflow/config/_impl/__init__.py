"""Private implementation of twinflow.config. Not a public import path.

Only `twinflow` itself is a PEP 420 namespace package; every subpackage below it
is a regular one. A missing __init__.py here would let another distribution add
modules into this path and would hide the whole subtree from the import graph
the boundary contracts walk.
"""

from __future__ import annotations
