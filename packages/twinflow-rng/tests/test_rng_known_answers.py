"""The cross-language known-answer gate, VG-VAR-07 and RUST-1."""

import json
from pathlib import Path

from twinflow.rng import generator_for

# packages/twinflow-rng/tests/ -> packages/twinflow-rng/ -> packages/ -> root
_FIXTURE = Path(__file__).resolve().parents[3] / "tests" / "fixtures" / "rng_kat.json"


def _corpus():
    assert _FIXTURE.is_file(), (
        f"known-answer corpus missing at {_FIXTURE}. "
        "Generate it with: uv run python tools/gen_rng_kat.py"
    )
    return json.loads(_FIXTURE.read_text(encoding="utf-8"))


def test_corpus_covers_the_shape_section_a7_specifies():
    """64 stream names, three base seeds, two replication indexes.

    A corpus that shrank would still pass the value comparison below while
    covering less, so the shape is asserted separately from the values.
    """
    corpus = _corpus()
    assert corpus["format"] == 1
    assert corpus["person"] == "twinflow-rng"
    assert corpus["digest_size"] == 16
    assert corpus["bit_generator"] == "PCG64DXSM"
    assert corpus["draws_per_case"] == 16

    streams = sorted({case["stream"] for case in corpus["cases"]})
    seeds = sorted({case["base_seed"] for case in corpus["cases"]})
    replications = sorted({case["replication_index"] for case in corpus["cases"]})
    assert len(streams) == 64
    assert len(seeds) == 3
    assert len(replications) == 2
    assert len(corpus["cases"]) == 384


def test_corpus_spans_every_grammar_form_of_section_a2():
    """Fixed, per-entity, provisioning, and fault-owned names, plus the
    schedule stream. A corpus of 64 fixed names would be 64 copies of one
    case, which is the failure this assertion exists to catch.
    """
    corpus = _corpus()
    streams = sorted({case["stream"] for case in corpus["cases"]})
    assert any(name.count(".") == 2 and "-" not in name for name in streams)
    assert any(name.count(".") == 3 and name.startswith("twin.") for name in streams)
    assert any(name.startswith("provision.") for name in streams)
    assert any(name.startswith("fault.") for name in streams)
    assert "schedule.faults" in streams


def test_rng_known_answers():
    """The cross-language gate itself.

    The Rust crate reads this same file and must produce these values from the
    same stream name, base seed, and replication index. A failure means one of
    the three algorithms of section A.7 moved: BLAKE2b, numpy's SeedSequence
    mixing function, or PCG64DXSM. Regenerating the corpus to make this green
    destroys the only evidence that the two implementations agree.
    """
    corpus = _corpus()
    draws = corpus["draws_per_case"]

    for case in corpus["cases"]:
        raw_gen = generator_for(
            case["stream"],
            base_seed=case["base_seed"],
            replication_index=case["replication_index"],
        )
        raw = [str(int(raw_gen.bit_generator.random_raw())) for _ in range(draws)]
        assert raw == case["raw_uint64"], case["stream"]

        double_gen = generator_for(
            case["stream"],
            base_seed=case["base_seed"],
            replication_index=case["replication_index"],
        )
        doubles = [double_gen.random() for _ in range(draws)]
        assert doubles == case["doubles"], case["stream"]
