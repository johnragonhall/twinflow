import pytest
from hypothesis import assume, given, settings
from hypothesis import strategies as st

from twinflow.rng import derive_spawn_key, generator_for

pytestmark = pytest.mark.property

# Stream names follow the dotted grammar in variability-and-faults.md A.2. The
# alphabet is written out rather than drawn from Unicode categories, because
# the grammar is ASCII and a generator that is wider than the grammar tests
# names the registry would refuse.
_segment = st.text(
    alphabet="abcdefghijklmnopqrstuvwxyz0123456789_",
    min_size=1,
    max_size=12,
)
stream_names = st.lists(_segment, min_size=2, max_size=4).map(".".join)


@given(a=stream_names, b=stream_names, seed=st.integers(0, 2**64 - 1))
@settings(max_examples=200, deadline=None)
def test_adding_a_stream_never_changes_an_existing_one(a, b, seed):
    """The ordering hazard, stated as a property.

    A stream's draws depend on its name and the run seed. They do not depend on
    which other streams exist, or on the order streams were created in. A
    positional mechanism cannot promise this.

    The first list rebuilds the generator on every draw, so `before` holds the
    first draw of five identical generators. That is deliberate: it is the value
    a caller sees when it asks the registry for the stream, which is the
    quantity the property is about.
    """
    before = [generator_for(a, base_seed=seed).random() for _ in range(5)]

    if b != a:
        noise = generator_for(b, base_seed=seed)
        for _ in range(50):
            noise.random()

    after = [generator_for(a, base_seed=seed).random() for _ in range(5)]
    assert before == after


@given(a=stream_names, b=stream_names)
@settings(max_examples=200, deadline=None)
def test_distinct_names_give_distinct_spawn_keys(a, b):
    """A collision would silently correlate two subsystems.

    This does not prove the hash is collision free. It asserts the property
    that matters at this scale. Section A.1a computes the two birthday bounds
    that govern, and under PCG64DXSM the operative one is a 128-bit collision
    in the spawn key or the SeedSequence pool, which is the quantity this test
    samples. Task 7 pins the ceiling that goes with it.

    assume rather than an if, so an example where the two names are equal is
    reported as filtered rather than counted as a pass with no assertion.
    """
    assume(a != b)
    assert derive_spawn_key(a) != derive_spawn_key(b)


@given(seed=st.integers(0, 2**64 - 1))
@settings(max_examples=100, deadline=None)
def test_draw_order_within_a_stream_is_reproducible(seed):
    name = "twin.receiving.unload_duration"
    first = generator_for(name, base_seed=seed)
    second = generator_for(name, base_seed=seed)
    assert [first.random() for _ in range(20)] == [second.random() for _ in range(20)]
