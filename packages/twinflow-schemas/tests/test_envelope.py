import re

import pytest
from pydantic import ValidationError

from twinflow.schemas import MAX_ATTRIBUTE_NAME_LENGTH, PRODUCER_IDS, Envelope


def _base():
    return {
        "specversion": "1.0",
        "id": "01J0000000000000000000000A",
        "source": "/twinflow/sim/receiving",
        "type": "twinflow.twin.pallet_scanned",
        "time": "2026-08-09T00:00:00Z",
        "datacontenttype": "application/json",
        "dataschema": "twinflow:schemas/twin/pallet_scanned/v1.0.json",
        "twinflowsimts": "0",
        "twinflowrunid": "run_01J0000000000000000000000A",
        "twinflowproducerid": "sim",
        "twinflowseq": "0",
        "data": {},
    }


def _envelope(**overrides):
    fields = _base()
    fields.update(overrides)
    return Envelope(**fields)


def test_attribute_names_are_lowercase_alphanumeric_and_fit_the_length_cap():
    """CloudEvents 1.0.2 attribute naming, asserted rather than reviewed.

    The specification MUSTs the character set: lower-case ASCII letters or
    digits, with extension attributes following the same convention. The
    20-character limit is a SHOULD NOT rather than a MUST, and twinflow adopts
    it as a hard rule by choice. An underscore in a field name is the defect
    this test exists to catch, and it has to be caught here: renaming an
    envelope field after Phase 0 is a major version bump on every subject.
    """
    for name in Envelope.model_fields:
        assert re.fullmatch(r"[a-z0-9]+", name), name
        assert len(name) <= MAX_ATTRIBUTE_NAME_LENGTH, name


def test_sim_ts_and_seq_are_strings_not_ints():
    """A 32-bit integer overflows in normal use.

    One simulated day at the default tick rate is 8.64e10 ticks, and 2**31 is
    2.15e9. CloudEvents fixes its Integer type at 32 bits signed, so both
    fields carry a decimal string instead.
    """
    env = _envelope(twinflowsimts="86400000000000", twinflowseq="5184000000")
    assert env.twinflowsimts == "86400000000000"
    assert env.twinflowseq == "5184000000"


def test_sim_ts_rejects_a_non_decimal_string():
    with pytest.raises(ValidationError):
        _envelope(twinflowsimts="12.5")


def test_seq_starts_at_zero_because_run_started_sits_at_sequence_zero():
    """Invariant E3 fixes the first sequence value at 0.

    INV-K18 asserts that a completed producer's sequence is exactly 0..n-1, so
    a validator rejecting "0" would make the first event of every run invalid
    and the invariant unsatisfiable.
    """
    assert _envelope(twinflowseq="0").twinflowseq == "0"


def test_seq_rejects_a_leading_zero():
    """Two spellings of one number would sort as two values in the total order."""
    with pytest.raises(ValidationError):
        _envelope(twinflowseq="01")


def test_producer_id_is_required():
    """D-07: the sequence is dense per producer, never globally.

    Garage tier already runs several containers plus the Rust agent, so a
    global counter has no allocator. Without twinflowproducerid the total
    order cannot be reconstructed.
    """
    fields = _base()
    del fields["twinflowproducerid"]
    with pytest.raises(ValidationError):
        Envelope(**fields)


def test_producer_id_rejects_an_undeclared_role():
    """Invariant E3 draws the producer id from a closed set of process roles.

    The id is inside the deterministic event id of E2, so a free string would
    let two processes mint the same event id and would put an unreviewed value
    into every hash.
    """
    with pytest.raises(ValidationError):
        _envelope(twinflowproducerid="sim-0")
    for role in PRODUCER_IDS:
        assert _envelope(twinflowproducerid=role).twinflowproducerid == role


def test_time_is_required_because_cloudevents_readers_expect_it():
    """time is wall time under CloudEvents, so twinflowsimts carries authority.

    The envelope keeps both: an off-the-shelf CloudEvents tool reads time, and
    the replay reader reads twinflowsimts. Dropping time would fail the
    CloudEvents JSON format schema that gate VAL-F12 checks.
    """
    assert _envelope().time.year == 2026
    fields = _base()
    del fields["time"]
    with pytest.raises(ValidationError):
        Envelope(**fields)


def test_source_must_be_a_twinflow_uri_reference():
    """Section 3.4 fixes the form as /twinflow/<package>/<component>."""
    assert _envelope(source="/twinflow/rng/registry").source == "/twinflow/rng/registry"
    with pytest.raises(ValidationError):
        _envelope(source="twinflow/sim/receiving")


def test_total_order_key_is_sim_ts_then_producer_then_seq():
    a = _envelope(twinflowsimts="10", twinflowproducerid="sim", twinflowseq="2")
    b = _envelope(twinflowsimts="10", twinflowproducerid="sim", twinflowseq="10")
    c = _envelope(twinflowsimts="10", twinflowproducerid="agent", twinflowseq="1")
    d = _envelope(twinflowsimts="9", twinflowproducerid="cli", twinflowseq="99")

    ordered = sorted([a, b, c, d], key=Envelope.total_order_key)

    assert [e.twinflowsimts for e in ordered] == ["9", "10", "10", "10"]
    assert [(e.twinflowproducerid, e.twinflowseq) for e in ordered[1:]] == [
        ("agent", "1"),
        ("sim", "2"),
        ("sim", "10"),
    ]


def test_seq_orders_numerically_not_lexically():
    """The regression this guards: "10" sorts before "2" as strings."""
    a = _envelope(twinflowseq="2")
    b = _envelope(twinflowseq="10")
    assert Envelope.total_order_key(a) < Envelope.total_order_key(b)


def test_producer_id_orders_as_a_byte_string():
    """Invariant E4 compares the producer id as bytes, not as text.

    Every declared role is ASCII today, so byte order and code-point order
    agree. The key returns bytes anyway, because a role added later outside
    ASCII would otherwise reorder already-recorded logs without failing a
    single test.
    """
    assert Envelope.total_order_key(_envelope(twinflowproducerid="agent"))[1] == b"agent"


def test_envelope_rejects_an_unknown_field():
    """The envelope is a contract. A typo must fail, not pass quietly."""
    with pytest.raises(ValidationError):
        _envelope(twinflowproducer="sim")


def test_envelope_is_immutable_but_is_not_hashable():
    """frozen=True buys immutability. It does not buy hashability.

    Pydantic generates __hash__ for a frozen model, but data is a dict and a
    dict is unhashable, so hash() raises TypeError. That is pinned here rather
    than left to be discovered in a consumer: deduplicating events by dropping
    them in a set is the obvious first thing to reach for, and it fails on the
    envelope. Key on the event id instead.

    If data ever becomes a hashable type this test fails, which is the point:
    gaining hashability changes the published API and should be a decision.
    """
    env = _envelope()

    with pytest.raises(ValidationError):
        env.twinflowseq = "5"

    with pytest.raises(TypeError):
        hash(env)
