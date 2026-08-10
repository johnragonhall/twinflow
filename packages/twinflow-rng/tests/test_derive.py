import hashlib

import numpy as np

from twinflow.rng import derive_spawn_key, generator_for
from twinflow.rng.derive import PERSON


def test_spawn_key_is_four_little_endian_uint32_from_a_16_byte_blake2b():
    """The derivation restated independently.

    This computes the digest with the standard library rather than calling the
    implementation, so a change to the personalization, the digest size, or the
    word order fails here instead of at replay time.
    """
    name = "twin.receiving.unload_duration"
    digest = hashlib.blake2b(name.encode("utf-8"), digest_size=16, person=b"twinflow-rng").digest()
    expected = tuple(int.from_bytes(digest[i : i + 4], "little") for i in range(0, 16, 4))

    assert derive_spawn_key(name) == expected


def test_personalization_is_padded_not_truncated():
    """The BLAKE2b parameter block fixes personalization at 16 bytes.

    The Python standard library zero-pads a shorter value, which its hashlib
    documentation states, so the 12-byte string and the same string followed by
    four zero bytes are one value. The assertion runs against derive_spawn_key
    rather than against two standard-library calls, so editing PERSON fails
    this test instead of leaving it green while every digest changes.
    """
    name = "twin.receiving.unload_duration"
    padded = hashlib.blake2b(
        name.encode("utf-8"),
        digest_size=16,
        person=PERSON + b"\x00\x00\x00\x00",
    ).digest()
    expected = tuple(int.from_bytes(padded[i : i + 4], "little") for i in range(0, 16, 4))

    assert PERSON == b"twinflow-rng"
    assert derive_spawn_key(name) == expected


def test_entropy_is_exactly_four_uint32_words_for_any_seed():
    """numpy converts a Python int to as many uint32 words as its magnitude
    needs, so a tuple of ints yields two to four words depending on the seed
    and the mixing path changes with it. A fixed-width uint32 array passes
    through unchanged, pinning the entropy at four words. Four is also
    DEFAULT_POOL_SIZE, which makes numpy's zero-fill branch unreachable.
    """
    from twinflow.rng.derive import _entropy

    for seed in (0, 1, 2**31, 2**63 - 1, 2**64 - 1):
        words = _entropy(seed, replication_index=0)
        assert words.dtype == np.uint32
        assert words.shape == (4,)
        assert int(words[0]) == seed & 0xFFFFFFFF
        assert int(words[1]) == seed >> 32


def test_run_entropy_and_spawn_key_are_four_words_each():
    """Four plus four is the eight words numpy's mixing function consumes.

    numpy zero-pads the run entropy up to the pool size when a spawn key is
    present. Fixing the run entropy at four words, which is the default pool
    size, makes that branch unreachable, so its behaviour never enters the
    cross-language contract of A.7.
    """
    from twinflow.rng.derive import _entropy

    seed_seq = np.random.SeedSequence(
        entropy=_entropy(0, 0),
        spawn_key=derive_spawn_key("twinflow.selftest"),
    )
    # Asserting the type as well as the shape is the point rather than a way
    # past the type checker: numpy accepts several entropy forms and coerces
    # most of them, and the contract here is that a uint32 array arrives intact.
    entropy = seed_seq.entropy
    assert isinstance(entropy, np.ndarray)
    assert entropy.dtype == np.uint32
    assert entropy.shape == (4,)
    assert len(seed_seq.spawn_key) == 4


def test_same_name_and_seed_gives_identical_draws():
    a = generator_for("twin.receiving.unload_duration", base_seed=42)
    b = generator_for("twin.receiving.unload_duration", base_seed=42)
    assert [a.random() for _ in range(10)] == [b.random() for _ in range(10)]


def test_different_names_give_different_draws():
    a = generator_for("twin.receiving.unload_duration", base_seed=42)
    b = generator_for("twin.receiving.scan_duration", base_seed=42)
    assert [a.random() for _ in range(10)] != [b.random() for _ in range(10)]


def test_replication_index_gives_an_independent_tree():
    """Replication folds into the root entropy, not the stream name, so a
    stream keeps its name across replications while drawing different values.
    """
    a = generator_for("twin.receiving.unload_duration", base_seed=42, replication_index=0)
    b = generator_for("twin.receiving.unload_duration", base_seed=42, replication_index=1)
    assert [a.random() for _ in range(10)] != [b.random() for _ in range(10)]


def test_known_answer_raw_words_are_stable():
    """The cross-language anchor for one stream, in raw PCG64DXSM output words.

    Task 9 grows this into the 64-name corpus of A.7. Raw words are what A.7
    names, because the Rust crate reproduces PCG64DXSM from the specification
    and has no reason to carry numpy's bounded-integer algorithm as well.

    Regenerating this vector because the implementation changed defeats its
    purpose: a failure means either the derivation moved or numpy did, and both
    need a decision rather than a refreshed expected value.

    These values are frozen. They were generated from this derivation and
    confirmed identical under numpy 2.1.0, 2.2.0, 2.3.0, and 2.4.6, which is
    the whole supported pin range, so they are fixed by the algorithms rather
    than by a release. A failure here means the derivation moved or numpy
    broke its own documented stream stability, and both need a decision.
    """
    gen = generator_for("twinflow.selftest", base_seed=0)
    drawn = [int(gen.bit_generator.random_raw()) for _ in range(4)]
    assert drawn == [
        5611998823145079523,
        4040095332396109674,
        474682057325833967,
        5149392380048760938,
    ]


def test_known_answer_doubles_are_stable():
    """The second half of the anchor, on the NEP 19 stream-stable path.

    NEP 19 names bytes, integers, and random as the methods numpy commits to
    keeping stream-compatible, so the doubles vector rides on Generator.random.
    The draws are taken one at a time because invariant R8 fixes the block size
    at one, and from a generator of their own because raw words and doubles
    both advance the same state.

    These values are frozen. They were generated from this derivation and
    confirmed identical under numpy 2.1.0, 2.2.0, 2.3.0, and 2.4.6, which is
    the whole supported pin range, so they are fixed by the algorithms rather
    than by a release. A failure here means the derivation moved or numpy
    broke its own documented stream stability, and both need a decision.
    """
    gen = generator_for("twinflow.selftest", base_seed=0)
    drawn = [gen.random() for _ in range(4)]
    assert drawn == [
        0.30422706580199943,
        0.2190140068216203,
        0.0257325658896278,
        0.27914912027145844,
    ]
