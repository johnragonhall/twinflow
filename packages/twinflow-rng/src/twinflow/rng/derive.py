"""The name-addressed derivation, fixed byte for byte.

Doctrine D-06 makes this a cross-language contract rather than a Python
implementation detail, because the Rust device agent derives its streams the
same way. The specification lives in docs/design/variability-and-faults.md
section A.1, and the four load-bearing details are asserted individually in
tests/test_derive.py rather than left as comments.

Why content addressed rather than positional: SeedSequence.spawn(n) extends the
parent key by the child's index, so the child a subsystem receives depends on
how many subsystems spawned before it. Adding subsystem forty would shift
subsystem one, and every recorded run and golden file would break. The name is
the address.
"""

from __future__ import annotations

import hashlib

import numpy as np

#: 12 bytes. The BLAKE2b parameter block fixes personalization at 16, and the
#: Python standard library zero-pads a shorter value. Any second implementation
#: pads the same way or produces a different digest for every stream name.
PERSON = b"twinflow-rng"

DIGEST_SIZE = 16


def derive_spawn_key(stream_name: str) -> tuple[int, int, int, int]:
    """Hash a stream name into four uint32 words.

    The 16-byte digest is read as four little-endian uint32 words. That word
    order is twinflow's own choice, fixed by section A.7, and is not something
    numpy imposes: SeedSequence receives the four words already assembled and
    treats each as one entropy word. A second implementation reads the digest
    the same way or produces a different key for every stream name.
    """
    digest = hashlib.blake2b(
        stream_name.encode("utf-8"), digest_size=DIGEST_SIZE, person=PERSON
    ).digest()
    return (
        int.from_bytes(digest[0:4], "little"),
        int.from_bytes(digest[4:8], "little"),
        int.from_bytes(digest[8:12], "little"),
        int.from_bytes(digest[12:16], "little"),
    )


def _entropy(base_seed: int, replication_index: int) -> np.ndarray:
    """Assemble the root entropy as exactly four uint32 words.

    A fixed-width uint32 array passes through numpy's coercion unchanged. A
    tuple of Python ints does not: numpy emits as many words as each value's
    magnitude needs, so the word count varies with the seed and the mixing path
    varies with it. Four words is also DEFAULT_POOL_SIZE, and numpy pads the
    run entropy up to the pool size only when a spawn key is present, so fixing
    it at four makes that padding branch unreachable and removes a
    version-sensitive behaviour from the contract.
    """
    if not 0 <= base_seed < 2**64:
        raise ValueError(f"base_seed must fit in uint64, got {base_seed}")
    if not 0 <= replication_index < 2**64:
        raise ValueError(f"replication_index must fit in uint64, got {replication_index}")
    return np.array(
        [
            base_seed & 0xFFFFFFFF,
            base_seed >> 32,
            replication_index & 0xFFFFFFFF,
            replication_index >> 32,
        ],
        dtype=np.uint32,
    )


def generator_for(
    stream_name: str, *, base_seed: int, replication_index: int = 0
) -> np.random.Generator:
    """Construct the generator for one stream.

    This is the only place in the workspace that constructs a bit generator,
    which lint rule TWF-RNG-001 enforces from Task 10 onward.
    """
    seed_seq = np.random.SeedSequence(
        entropy=_entropy(base_seed, replication_index),
        spawn_key=derive_spawn_key(stream_name),
    )
    return np.random.Generator(np.random.PCG64DXSM(seed_seq))
