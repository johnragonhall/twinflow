"""The UHF portal reader, attacked at the four places a real one gets it wrong.

Each of these was a shipped defect somewhere before it was a test here: a
running mean that weighted a batched read as one sample, an empty prefix filter
that silently matched every tag, an accumulation cap that dropped without
saying so, and an unreachable reader reported as a quiet one.
"""

from __future__ import annotations

import pytest

from twinflow.kernel import SimClock, SimInstant
from twinflow.rng import generator_for
from twinflow.sensors import (
    EpcPrefixFilter,
    InventoryAccumulator,
    PortalFault,
    PortalReader,
    ReaderConfig,
    TagRead,
    diagnose_portal,
)

EPC_A = "3034257BF400B78000000001"
EPC_B = "3034257BF400B78000000002"
EPC_OTHER = "3005FB63AC1F3681EC880468"


def read(epc: str = EPC_A, *, antenna: int = 1, rssi: int = -55, count: int = 1) -> TagRead:
    return TagRead(
        epc=epc,
        sim_ts=SimInstant(0),
        antenna_port=antenna,
        rssi_dbm=rssi,
        phase_deg=42.0,
        read_count=count,
    )


# ------------------------------------------------------------- the read record


def test_an_epc_is_ninety_six_bits_written_as_twenty_four_hex_characters():
    assert len(read().epc) == 24


@pytest.mark.parametrize(
    "bad_epc",
    ["", "3034257B", "3034257bf400b78000000001", "3034257BF400B7800000000G", "E" * 25],
)
def test_a_malformed_epc_is_refused(bad_epc):
    with pytest.raises(ValueError, match="epc"):
        read(bad_epc)


def test_the_antenna_port_is_one_based():
    with pytest.raises(ValueError, match="1-based"):
        read(antenna=0)


def test_rssi_is_a_negative_dbm_integer():
    with pytest.raises(ValueError, match="dBm"):
        read(rssi=12)


def test_rf_phase_stays_inside_one_turn():
    with pytest.raises(ValueError, match="phase"):
        TagRead(
            epc=EPC_A,
            sim_ts=SimInstant(0),
            antenna_port=1,
            rssi_dbm=-55,
            phase_deg=360.0,
            read_count=1,
        )


def test_a_read_record_stands_for_at_least_one_read():
    with pytest.raises(ValueError, match="read_count"):
        read(count=0)


# ------------------------------------------------------------ the EPC filter


def test_an_empty_prefix_filter_is_refused_because_it_disables_filtering():
    with pytest.raises(ValueError, match="empty"):
        EpcPrefixFilter("")


def test_a_prefix_filter_keeps_its_own_inventory_and_drops_the_rest():
    zone = EpcPrefixFilter("3034257B")
    assert zone.matches(EPC_A) is True
    assert zone.matches(EPC_B) is True
    assert zone.matches(EPC_OTHER) is False


def test_a_prefix_longer_than_an_epc_is_refused():
    with pytest.raises(ValueError, match="24"):
        EpcPrefixFilter("A" * 25)


def test_a_prefix_that_is_not_hexadecimal_is_refused():
    with pytest.raises(ValueError, match="hex"):
        EpcPrefixFilter("ZZTOP")


# ------------------------------------------------------------ the aggregation


def test_aggregation_is_keyed_by_epc_and_antenna_not_by_epc_alone():
    acc = InventoryAccumulator(max_epcs=8)
    acc.offer(read(antenna=1))
    acc.offer(read(antenna=2))
    assert [(a.epc, a.antenna_port) for a in acc.aggregates()] == [(EPC_A, 1), (EPC_A, 2)]


def test_the_running_mean_weights_the_incoming_sample_by_its_read_count():
    """The bug this catches: weighting an arriving 300-read batch as one sample.

    The batch has to arrive SECOND for this to discriminate. With the batch
    first and a single read second, the naive and the correct arithmetic agree
    to the last bit, and the test would report green against the defect.
    """
    acc = InventoryAccumulator(max_epcs=8)
    acc.offer(read(rssi=-40, count=1))
    acc.offer(read(rssi=-60, count=300))
    aggregate = acc.aggregates()[0]
    assert aggregate.read_count == 301
    # Weighting the incoming batch as one sample gives -50.0 exactly. Weighting
    # it by its 300 reads puts the mean within a whisker of -60.
    assert aggregate.rssi_mean_dbm == pytest.approx((-40 + -60 * 300) / 301)
    assert aggregate.rssi_mean_dbm < -59.0


def test_the_running_mean_is_order_independent():
    """A weighted mean cannot depend on which batch the reader reported first."""
    forward = InventoryAccumulator(max_epcs=8)
    forward.offer(read(rssi=-40, count=7))
    forward.offer(read(rssi=-60, count=300))
    backward = InventoryAccumulator(max_epcs=8)
    backward.offer(read(rssi=-60, count=300))
    backward.offer(read(rssi=-40, count=7))
    assert forward.aggregates()[0].rssi_mean_dbm == pytest.approx(
        backward.aggregates()[0].rssi_mean_dbm
    )


def test_the_aggregate_carries_the_extremes_as_well_as_the_mean():
    acc = InventoryAccumulator(max_epcs=8)
    for rssi in (-52, -67, -44):
        acc.offer(read(rssi=rssi))
    aggregate = acc.aggregates()[0]
    assert (aggregate.rssi_min_dbm, aggregate.rssi_max_dbm) == (-67, -44)


def test_a_filtered_accumulator_ignores_a_tag_outside_its_read_zone():
    acc = InventoryAccumulator(max_epcs=8, epc_filter=EpcPrefixFilter("3034257B"))
    assert acc.offer(read(EPC_A)) is True
    assert acc.offer(read(EPC_OTHER)) is False
    assert [a.epc for a in acc.aggregates()] == [EPC_A]
    assert acc.filtered_reads == 1


# ------------------------------------------------------------ the bounded cap


def test_at_the_cap_a_new_epc_is_dropped_and_a_tracked_one_keeps_updating():
    acc = InventoryAccumulator(max_epcs=1)
    acc.offer(read(EPC_A, rssi=-50))
    assert acc.offer(read(EPC_B)) is False
    assert acc.offer(read(EPC_A, rssi=-60)) is True
    aggregate = acc.aggregates()[0]
    assert aggregate.epc == EPC_A
    assert aggregate.read_count == 2


def test_the_cap_counts_distinct_epcs_not_distinct_keys():
    """One tag on four antennas is one tag, so the cap must not spend four."""
    acc = InventoryAccumulator(max_epcs=1)
    for antenna in (1, 2, 3, 4):
        assert acc.offer(read(EPC_A, antenna=antenna)) is True
    assert acc.dropped_new_epcs == 0
    assert acc.offer(read(EPC_B)) is False


def test_what_the_cap_dropped_is_published_rather_than_lost_silently():
    """Two counters, because they answer two different operator questions.

    How many tags were lost is not how many read records were discarded, and a
    single counter would let a reader that saw one refused tag a hundred times
    report the same loss as one that missed a hundred distinct pallets.
    """
    acc = InventoryAccumulator(max_epcs=1)
    acc.offer(read(EPC_A))
    acc.offer(read(EPC_B))
    acc.offer(read(EPC_OTHER))
    acc.offer(read(EPC_B))
    assert acc.dropped_new_epcs == 2
    assert acc.dropped_reads == 3


def test_a_cap_of_zero_is_refused_because_it_would_drop_everything_quietly():
    with pytest.raises(ValueError, match="max_epcs"):
        InventoryAccumulator(max_epcs=0)


def test_the_aggregate_order_is_deterministic_and_not_insertion_order():
    forward = InventoryAccumulator(max_epcs=8)
    backward = InventoryAccumulator(max_epcs=8)
    for epc in (EPC_A, EPC_B, EPC_OTHER):
        forward.offer(read(epc))
    for epc in (EPC_OTHER, EPC_B, EPC_A):
        backward.offer(read(epc))
    assert [a.epc for a in forward.aggregates()] == [a.epc for a in backward.aggregates()]


# ------------------------------------------------------------ the sensitivity


def test_a_read_weaker_than_the_configured_sensitivity_does_not_happen():
    reader = PortalReader(config=ReaderConfig(sensitivity_dbm=-70, silence_threshold_ticks=5_000))
    with pytest.raises(ValueError, match="sensitivity"):
        reader.observe(read(rssi=-71))


def test_a_read_exactly_at_the_sensitivity_floor_is_accepted():
    reader = PortalReader(config=ReaderConfig(sensitivity_dbm=-70, silence_threshold_ticks=5_000))
    reader.observe(read(rssi=-70))
    assert reader.inventory.aggregates()[0].read_count == 1


# ------------------------------------------------------------------ the faults


def test_unreachable_and_silent_are_two_faults_and_are_never_conflated():
    assert (
        diagnose_portal(reachable=False, ticks_since_last_read=0, silence_threshold_ticks=100)
        is PortalFault.UNREACHABLE
    )
    # Unreachable wins when both could be said: a reader nobody can talk to has
    # of course read nothing, and reporting the silence too sends an operator
    # to the antennas when the fault is the network.
    assert (
        diagnose_portal(reachable=False, ticks_since_last_read=10_000, silence_threshold_ticks=100)
        is PortalFault.UNREACHABLE
    )
    assert (
        diagnose_portal(reachable=True, ticks_since_last_read=101, silence_threshold_ticks=100)
        is PortalFault.SILENT
    )
    assert (
        diagnose_portal(reachable=True, ticks_since_last_read=100, silence_threshold_ticks=100)
        is None
    )


def test_the_silence_threshold_is_a_calibration_knob_rather_than_a_constant():
    reader = PortalReader(config=ReaderConfig(sensitivity_dbm=-70, silence_threshold_ticks=50))
    clock = SimClock(tick_hz=1_000)
    reader.observe(read(), now=clock.now())
    clock.advance_to(SimInstant(51))
    assert reader.fault(now=clock.now(), reachable=True) is PortalFault.SILENT

    patient = PortalReader(config=ReaderConfig(sensitivity_dbm=-70, silence_threshold_ticks=5_000))
    patient.observe(read(), now=SimInstant(0))
    assert patient.fault(now=SimInstant(51), reachable=True) is None


def test_a_silence_threshold_of_zero_is_refused():
    with pytest.raises(ValueError, match="silence_threshold_ticks"):
        ReaderConfig(sensitivity_dbm=-70, silence_threshold_ticks=0)


def test_a_sensitivity_above_zero_dbm_is_refused():
    with pytest.raises(ValueError, match="dBm"):
        ReaderConfig(sensitivity_dbm=5, silence_threshold_ticks=100)


# --------------------------------------------------------------- the telemetry


def test_a_value_that_could_not_be_read_is_omitted_never_published_as_zero():
    reader = PortalReader(config=ReaderConfig(sensitivity_dbm=-70, silence_threshold_ticks=5_000))
    reader.observe(read(), now=SimInstant(0))
    telemetry = reader.telemetry(now=SimInstant(10), read_rate=None, tags_expected=None)
    published = telemetry.metric_values()
    assert "read_rate" not in published
    assert "tags_expected" not in published
    assert published["unique_epcs"] == 1
    assert telemetry.read_rate is None


def test_the_published_metric_names_are_the_uns_parameters_of_the_portal():
    reader = PortalReader(config=ReaderConfig(sensitivity_dbm=-70, silence_threshold_ticks=5_000))
    reader.observe(read(rssi=-51, count=120), now=SimInstant(0))
    published = reader.telemetry(
        now=SimInstant(10), read_rate=0.9861, tags_expected=12
    ).metric_values()
    assert sorted(published) == [
        "dropped_new_epcs",
        "read_rate",
        "reads_total",
        "rssi_mean_dbm",
        "tags_expected",
        "unique_epcs",
    ]
    assert published["reads_total"] == 120
    assert published["rssi_mean_dbm"] == pytest.approx(-51.0)


def test_the_reader_publishes_onto_the_six_level_uns_topics_of_its_equipment():
    reader = PortalReader(
        config=ReaderConfig(sensitivity_dbm=-70, silence_threshold_ticks=5_000),
        uns_prefix=("twinflow", "dc-01", "receiving", "inbound-line-01", "portal-03"),
    )
    reader.observe(read(), now=SimInstant(0))
    topics = [
        path.topic
        for path, _ in reader.publish(now=SimInstant(10), read_rate=0.9861, tags_expected=1)
    ]
    assert "twinflow/dc-01/receiving/inbound-line-01/portal-03/read_rate" in topics
    assert all(topic.count("/") == 5 for topic in topics)


# ------------------------------------------------------------------ the draw


def test_the_read_rate_is_a_scaled_beta_so_it_cannot_leave_its_own_support():
    rng = generator_for("sensor.rfid_read_rate.portal-03.noise", base_seed=7)
    draws = [PortalReader.draw_read_rate(rng) for _ in range(2_000)]
    assert all(0.0 <= value <= 1.0 for value in draws)
    assert 0.95 < sum(draws) / len(draws) < 1.0
    # A clamped normal would pile mass exactly on the boundary. A beta does not.
    assert sum(1 for value in draws if value == 1.0) == 0


def test_two_runs_at_one_seed_draw_the_same_read_rates():
    first = [
        PortalReader.draw_read_rate(generator_for("s.a.portal-03.noise", base_seed=11))
        for _ in range(3)
    ]
    second = [
        PortalReader.draw_read_rate(generator_for("s.a.portal-03.noise", base_seed=11))
        for _ in range(3)
    ]
    assert first == second
