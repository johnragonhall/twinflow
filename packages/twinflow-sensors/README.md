---
title: twinflow-sensors
description: A UHF RFID portal, a temperature sensor, and the Sparkplug B session that publishes them onto an ISA-95 unified namespace.
topic_type: concept
audience: contributors
---

# twinflow-sensors

Two simulated field devices and the Sparkplug B session that carries them.
Every topic string is generated from the facility model, every payload is
derived from one metric model, and nothing here reads a wall clock or draws
unseeded randomness.

The six-level addressing itself lives in `twinflow-config`, which owns the
facility model that ARCHITECTURE.md section 5 makes the namespace a projection
of. `PortalReader.publish` and `TemperatureSensor.publish` return
`(UnsPath, value)` pairs built from that grammar, and `SparkplugIds` here maps
one of those addresses onto `group_id`, `edge_node_id`, and `device_id`.

## Install

```bash
pip install twinflow-sensors
```

## Use

One portal, one temperature sensor, one edge node, and the messages a
subscriber would actually see:

```python
from twinflow.kernel import SimClock, SimInstant
from twinflow.sensors import (
    DataType,
    EdgeNodeSession,
    MetricSpec,
    PortalReader,
    ReaderConfig,
    TagRead,
)

clock = SimClock(tick_hz=1_000)
portal = PortalReader(
    config=ReaderConfig(sensitivity_dbm=-70, silence_threshold_ticks=30_000, epc_prefix="3034257B"),
    uns_prefix=("twinflow", "dc-01", "receiving", "inbound-line-01", "portal-03"),
)

portal.observe(
    TagRead(
        epc="3034257BF400B78000000001",
        sim_ts=SimInstant(0),
        antenna_port=2,
        rssi_dbm=-54,
        phase_deg=131.5,
        read_count=284,
    ),
    now=SimInstant(0),
)

session = EdgeNodeSession(
    group_id="twinflow:dc-01:receiving",
    edge_node_id="inbound-line-01",
    clock=clock,
    devices={
        "portal-03": tuple(
            MetricSpec(name=name, datatype=DataType.Float, unit="1")
            for name in portal.metric_specs()
        )
    },
)

will = session.connect()      # register this as the MQTT Last Will, then CONNECT
session.node_birth()          # NBIRTH, seq 0
session.device_birth("portal-03")  # DBIRTH, the alias table
ddata = session.device_data("portal-03", {"read_rate": 0.9861})
```

`ddata` carries the alias and the value and no metric name. The mirror is
derived from that same message, so the two namespaces cannot disagree:

```python
session.mirror_records(ddata)[0].topic
# 'twinflow/dc-01/receiving/inbound-line-01/portal-03/read_rate'
```

## The portal is an inventory, not an event stream

A UHF portal reader speaking EPC Gen2 does not hand you one event per tag. It
hands you an inventory of reads, and one tag sitting in a read zone produces
hundreds of them per interval across several antennas. Modeling it as one
event per tag is not a simplification of the same device, it is a different
device, and every read-rate statistic computed downstream is then wrong.

So `TagRead` carries a `read_count`, aggregation is keyed by **(EPC, antenna)**,
and four rules follow that were each a shipped defect before they were code:

| Rule                                                                                                  | The defect it prevents                                                                                   |
| ----------------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------- |
| The running mean weights an arriving sample by its `read_count`, not by one                           | A 300-read batch counted as one observation drags the mean toward whichever antenna reported least often |
| An empty EPC prefix filter is refused at construction                                                 | An empty prefix matches every tag, so it silently disables filtering and nothing fails at the time       |
| At the cap only **new** EPCs are dropped, tracked ones keep updating, and the drop count is published | Silent data loss. The loss is not the defect; the silence is                                             |
| Unreachable and silent are two faults, never one                                                      | A reader that answers every health check while reading nothing looks perfect on a dashboard              |

The silence threshold is a constructor argument with no default. How long a
portal may legitimately read nothing is a property of the dock it hangs over: a
receiving door that sees four trailers a shift is quiet for hours with nothing
wrong, and a sortation induct quiet for thirty seconds has already stopped the
line. A default here would be a number pretending to be a fact.

## Absent is not zero

A value that could not be read is omitted from the published payload. It is
never published as a zero.

That distinction is load-bearing downstream. A read rate of `0.0` means every
expected tag was missed. A read rate of `None` means nothing passed the portal,
so the ratio has no denominator at all. Written as the same number, a p-chart
cannot tell a broken portal from a quiet hour, and the second will eventually
be investigated as the first.

## The temperature sensor refuses rather than clamps

The raw reading is published beside anything derived from it, the unit lives in
the parameter name (`motor_temp_c` cannot be misread as Fahrenheit), and a
reading outside the physical plausibility band is refused instead of clamped.

Refused means something specific here. The raw value is still published
unmodified, because a thermocouple reading -270 C after a junction failure _is_
the signature a detector has to catch, and clamping it produces a number
indistinguishable from a warm motor. What is refused is its use: the reading is
marked bad, produces no derived value, and never enters the EWMA state. A
detector reading the raw stream sees the excursion; a KPI reading the derived
stream is not quietly poisoned by it.

## Determinism

Two runs at one seed are byte-identical, and the properties that make that true
are structural rather than conventions:

- The clock is injected. `SimClock` is passed in and read through `now()`;
  nothing here can reach a wall clock.
- The bit generator is injected. `twinflow.rng.generator_for` is the only
  sanctioned way to build one, and this package only ever receives it.
- No collection whose iteration order reaches an emitted value is a set. Alias
  assignment sorts metric names byte-wise over their UTF-8 encoding, and
  inventory aggregates are emitted in sorted order, so a second process with a
  different `PYTHONHASHSEED` produces the same alias table and the same payload.
- The read rate is drawn from a **scaled beta**, whose support already is
  `[0, 1]`. A clamped normal would pile probability mass exactly on 1.0, and a
  portal that reads every tag on a measurable fraction of windows would be an
  artifact of the sampler rather than a property of the dock.

## Sparkplug B

The session implements the v3.0.0 statements ARCHITECTURE.md section 5.1 and
`docs/design/iot-fleet.md` 5.4 restate: the topic form, NBIRTH with `bdSeq` at
`seq` 0, DBIRTH establishing the alias table, NDATA and DDATA by alias with the
name excluded, NDEATH registered as the will at CONNECT, DDEATH below a live
node, and `seq` wrapping to zero after 255.

It does **not** encode protobuf, and it is not certified. Gate
VAL-GATE-SPARK-001 names the Eclipse Technology Compatibility Kit as its
arbiter and that suite has not been run against this code. [API.md](API.md)
states exactly what is claimed and what is still owed, because a package that
implies conformance it has not demonstrated is worse than one that claims
nothing.

The public symbols are listed in [API.md](API.md).
