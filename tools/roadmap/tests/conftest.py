"""Put this directory on the path so the tests can share one fixture module.

--import-mode=importlib is load-bearing in this workspace, because several
packages carry a tests/test_import.py and the default prepend mode would import
the second one under a name the first already claimed. The cost is that a test
module's own directory is not on sys.path, so a shared fixtures.py beside it
does not import without this.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
