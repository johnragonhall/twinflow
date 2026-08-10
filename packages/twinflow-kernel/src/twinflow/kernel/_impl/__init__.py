"""Private implementation of twinflow.kernel. Not a public import path.

This file is load-bearing rather than ceremonial. Only `twinflow` itself is a
PEP 420 namespace package; every subpackage below it is a regular package. A
missing __init__.py here would make `twinflow.kernel._impl` an implicit
namespace package too, which lets any other installed distribution add a module
into it, and which makes the import graph invisible to the tooling that walks
it: import-linter reported every private-module contract as KEPT while the
modules those contracts name were absent from the graph entirely.

Boundary rule A1.1 keeps this subpackage private. Import from `twinflow.kernel`
instead.
"""

from __future__ import annotations
