import re

import pytest

from twinflow.rng import STREAM_COUNT_CEILING, StreamRegistry, derive_spawn_key, generator_for


@pytest.fixture
def registry():
    reg = StreamRegistry(base_seed=42)
    reg.register("twin.receiving.unload_duration")
    reg.register("twin.amr.{amr_id}.task_travel")
    return reg


def test_get_returns_the_generator_the_derivation_produces(registry):
    """The registry adds bookkeeping, never a second derivation.

    This fails if the registry ever resolves a name differently from
    generator_for, which is the way a registry quietly forks a contract.
    """
    direct = generator_for("twin.receiving.unload_duration", base_seed=42)
    through = registry.get("twin.receiving.unload_duration")
    assert [through.random() for _ in range(5)] == [direct.random() for _ in range(5)]


def test_get_refuses_an_unregistered_name(registry):
    """An undeclared draw is randomness nobody reviewed."""
    with pytest.raises(KeyError, match="not registered"):
        registry.get("twin.receiving.invented_on_the_spot")


def test_templated_name_requires_its_arguments(registry):
    with pytest.raises(ValueError, match="amr_id"):
        registry.get("twin.amr.{amr_id}.task_travel")


def test_templated_name_rejects_an_unexpected_argument(registry):
    """A typo in a keyword would otherwise resolve to the unfilled template."""
    with pytest.raises(ValueError, match="takes no template argument"):
        registry.get("twin.amr.{amr_id}.task_travel", amr_id="AMR-014", amrid="AMR-014")


def test_templated_name_rejects_an_entity_id_that_could_forge_another_stream(registry):
    """A device name is attacker-controlled in any real fleet.

    An id carrying a dot would insert a segment and address a different
    stream; an id carrying a brace would leave a placeholder in place. Both
    are silent, so the value is validated rather than trusted.
    """
    for hostile in ("AMR-014.task_travel", "{amr_id}", "AMR 014", ""):
        with pytest.raises(ValueError, match="entity id"):
            registry.get("twin.amr.{amr_id}.task_travel", amr_id=hostile)


def test_templated_name_resolves_with_arguments(registry):
    a = registry.get("twin.amr.{amr_id}.task_travel", amr_id="AMR-014")
    b = registry.get("twin.amr.{amr_id}.task_travel", amr_id="AMR-015")
    assert [a.random() for _ in range(5)] != [b.random() for _ in range(5)]


def test_entity_stream_is_stable_regardless_of_creation_order(registry):
    """Creating entity 501 must not perturb entity 47."""
    first = [
        registry.get("twin.amr.{amr_id}.task_travel", amr_id="AMR-047").random() for _ in range(5)
    ]
    noise = registry.get("twin.amr.{amr_id}.task_travel", amr_id="AMR-501")
    for _ in range(50):
        noise.random()
    again = [
        registry.get("twin.amr.{amr_id}.task_travel", amr_id="AMR-047").random() for _ in range(5)
    ]
    assert first == again


def test_registration_is_append_only(registry):
    with pytest.raises(ValueError, match="already registered"):
        registry.register("twin.receiving.unload_duration")


def test_name_grammar_rejects_uppercase(registry):
    with pytest.raises(ValueError, match="grammar"):
        registry.register("Twin.Receiving.UnloadDuration")


def test_name_grammar_requires_at_least_two_segments(registry):
    with pytest.raises(ValueError, match="grammar"):
        registry.register("unload_duration")


def test_name_grammar_accepts_the_draw_order_version_suffix(registry):
    """Section A.3 makes an unavoidable draw-order break loud and dated.

    The superseded name keeps its address and gains a retirement marker, and
    the new draw order gets a new address. The two must draw differently, or
    the suffix would be decoration rather than a new address.
    """
    registry.register("twin.receiving.unload_duration@v2")
    assert "twin.receiving.unload_duration@v2" in registry.declared_names()

    v1 = registry.get("twin.receiving.unload_duration")
    v2 = registry.get("twin.receiving.unload_duration@v2")
    assert [v1.random() for _ in range(5)] != [v2.random() for _ in range(5)]


def test_a_retired_name_cannot_be_drawn_from(registry):
    """A retired name stays in the registry so it can never be reused.

    Removing it would free an address a recorded run still refers to, and the
    next registration of that address would point an old log at new numbers.
    """
    registry.register("twin.receiving.legacy_duration", retired_at="v0.4.0")
    with pytest.raises(KeyError, match="retired at v0.4.0"):
        registry.get("twin.receiving.legacy_duration")


def test_handout_counts_report_per_stream_usage(registry):
    """Generators handed out, not values drawn.

    The draw counter that A.6 hashes counts calls through
    twinflow.kernel.numeric and lands with that module. Asserting three draws
    against a count of one is the mistake this naming exists to prevent.
    """
    generator = registry.get("twin.receiving.unload_duration")
    for _ in range(3):
        generator.random()
    assert registry.handout_counts() == {"twin.receiving.unload_duration": 1}


def test_declared_stream_names_do_not_collide(registry):
    """The A.1a spawn-key check over the declared names.

    Task 6 states the property over generated names. This runs it over the
    registry's own contents with every template expanded, which is the form
    A.1a asks for, and it fails when any two expanded names share a key.
    """
    entity_ids = ("AMR-014", "AMR-047", "AMR-501")
    expanded = []
    for name in registry.declared_names():
        placeholders = sorted(set(re.findall(r"\{([a-z0-9_]+)\}", name)))
        if not placeholders:
            expanded.append(name)
            continue
        for entity_id in entity_ids:
            resolved = name
            for key in placeholders:
                resolved = resolved.replace("{" + key + "}", entity_id)
            expanded.append(resolved)

    keys = [derive_spawn_key(name) for name in expanded]
    assert len(keys) == 4
    assert len(set(keys)) == len(keys)


#: The largest stream count any shipped scenario declares, which section E.1
#: carries in its worked run manifest. A.1a's headroom rule is stated against
#: this number, so it lives next to the assertion that uses it. When real
#: scenarios ship, this becomes a computed maximum over them rather than a
#: literal, and the assertion below does not change.
LARGEST_DECLARED_SCENARIO_STREAMS = 61_402


def test_stream_count_ceiling_has_the_basis_a1a_states():
    """Section A.1a gives the ceiling a basis, and it is an operating one.

    Two things are pinned, because A.1a rests on both and they are different
    kinds of claim.

    First, the collision arithmetic that governs under PCG64DXSM: a 128-bit
    SeedSequence pool collision, n squared over 2 to the 129, which A.1a
    computes as 8.3e-28 at the ceiling. That is a bound, and it is not the
    reason for the number. It is asserted so an edit to the constant has to
    redo the arithmetic A.1a prints.

    Second, the rule that fixes the value. No published figure sets it,
    because none binds at this scale: A.1a computes the PCG project's own
    2017 overlap relation at the ceiling and gets about 6.0e26 draws per
    stream, so a statistical ceiling would never fire. The ceiling is an
    operating limit on catalog size, set at about twelve times the largest
    stream count a shipped scenario declares. Ten times is the floor the rule
    promises, twenty times is the point where the number stops meaning what
    A.1a says it means, and the constant sits between them.

    G.14 records that no PCG64DXSM bound is published by numpy or by the PCG
    project, G.15 carries the narrowed residual, and G.11 records the
    bit-generator decision of 2026-08-09.
    """
    expected_colliding_pairs = STREAM_COUNT_CEILING**2 / 2**129

    assert 8.0e-28 < expected_colliding_pairs < 8.6e-28

    assert STREAM_COUNT_CEILING >= 10 * LARGEST_DECLARED_SCENARIO_STREAMS
    assert STREAM_COUNT_CEILING < 20 * LARGEST_DECLARED_SCENARIO_STREAMS
