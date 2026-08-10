"""The schema differ CLI, and the engine behind gate SCH-001.

    uv run python tools/schema_diff.py OLD.json NEW.json

Exits 0 when every change between the two is allowed within a major version,
and 1 with a reason per finding otherwise.

The rules themselves live in `twinflow.schemas.compat`, not here. They are part
of the schemas contract rather than a property of this script: a consumer
deciding whether it can read a newer version asks the same question CI asks, and
both should get the answer from one place.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from twinflow.schemas import compare_schemas


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("old", type=Path)
    parser.add_argument("new", type=Path)
    args = parser.parse_args()

    old = json.loads(args.old.read_text(encoding="utf-8"))
    new = json.loads(args.new.read_text(encoding="utf-8"))

    findings = compare_schemas(old, new)
    if findings:
        sys.stderr.write(
            f"\n\033[31mBLOCKED: {args.new} is not compatible with {args.old} "
            f"within a major version\033[0m\n"
        )
        for finding in findings:
            sys.stderr.write(f"  {finding}\n")
        sys.stderr.write(
            "\nThe compatibility table is in docs/design/foundations.md section 5.5.\n"
            "A breaking change needs a new major: a new vN.0.json, an upcaster from\n"
            "every prior major, and both versions publishing in parallel.\n"
        )
        return 1

    print(f"[schema] {args.new.name} is compatible with {args.old.name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
