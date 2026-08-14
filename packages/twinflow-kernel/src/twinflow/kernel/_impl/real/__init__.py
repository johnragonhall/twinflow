"""Production adapters: the implementations that touch the outside world.

`docs/design/foundations.md` declares this path in `adapter_paths` with the
reason "production adapters", which exempts it from the determinism lint. That
exemption is the whole reason the directory exists as its own package: a socket,
a thread, and a wall clock are all legal here and illegal one level up, and a
reader can tell which they are looking at from the path alone.

Nothing here is imported by `twinflow.kernel.__init__`. Each adapter carries a
dependency behind an extra, and importing the kernel must not resolve any of
them.
"""

from __future__ import annotations
