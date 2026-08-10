"""Print one digest over the registry, for the two-hash-seed comparison.

    uv run python tools/rng_digest.py

The digest covers the declared names, their spawn keys, the first draws of each
stream, and the sorted handout map. Every one of those is a place where a set
iteration order could reach a hash, so a digest that differs between two
PYTHONHASHSEED values names a real defect rather than a flake.
"""

from __future__ import annotations

import hashlib

from twinflow.rng import StreamRegistry, derive_spawn_key

STREAMS = (
    "twin.receiving.unload_duration",
    "twin.receiving.scan_duration",
    "twin.amr.{amr_id}.task_travel",
    "provision.workforce.{worker_id}.productivity_effect",
    "schedule.faults",
)
AMR_IDS = ("AMR-014", "AMR-047", "AMR-501")
WORKER_IDS = ("W-0001", "W-0231")


def main() -> int:
    registry = StreamRegistry(base_seed=42, replication_index=1)
    for name in STREAMS:
        registry.register(name)

    digest = hashlib.blake2b(digest_size=32)

    for name in registry.declared_names():
        digest.update(name.encode("utf-8"))
        for word in derive_spawn_key(name):
            digest.update(word.to_bytes(4, "little"))

    for name in ("twin.receiving.unload_duration", "twin.receiving.scan_duration"):
        generator = registry.get(name)
        for _ in range(8):
            digest.update(repr(generator.random()).encode("utf-8"))

    for amr_id in AMR_IDS:
        generator = registry.get("twin.amr.{amr_id}.task_travel", amr_id=amr_id)
        for _ in range(8):
            digest.update(repr(generator.random()).encode("utf-8"))

    for worker_id in WORKER_IDS:
        generator = registry.get(
            "provision.workforce.{worker_id}.productivity_effect", worker_id=worker_id
        )
        for _ in range(8):
            digest.update(repr(generator.random()).encode("utf-8"))

    for name, count in registry.handout_counts().items():
        digest.update(f"{name}={count}".encode())

    print(digest.hexdigest())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
