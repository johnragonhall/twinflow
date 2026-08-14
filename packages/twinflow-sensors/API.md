---
title: twinflow-sensors API
description: Public symbols of twinflow.sensors, and the precise boundary of what the Sparkplug B implementation claims.
topic_type: reference
audience: contributors
---

# twinflow-sensors API

Everything below is importable from `twinflow.sensors`. Anything not listed
here is private regardless of where it lives, per boundary rule A1.1.

## Addressing

`UnsPath` is not here. The six-level ISA-95 grammar of ARCHITECTURE.md section 5
is owned by `twinflow.config`, because that section makes the namespace a
projection of the facility model and that package owns the model. Import it
from there:

```python
from twinflow.config import UnsPath
```

`PortalReader.publish` and `TemperatureSensor.publish` return `(UnsPath, value)`
pairs, so a caller naming the type imports it from `twinflow.config`, which is
already installed as a dependency of this one. It is not re-exported here:
boundary rule A1.4 gives a public symbol exactly one owning package, and a
second surface carrying the same name is how two spellings of one address get
started. The publish side and the historian in `twinflow.storage` now validate
against one definition, so the two renderings cannot disagree.

## Sparkplug B session (`sparkplug`)

| Symbol                                 | What it is                                                                   |
| -------------------------------------- | ---------------------------------------------------------------------------- |
| `EdgeNodeSession`                      | One MQTT client session for one edge node and the devices below it           |
| `SparkplugIds`                         | `group_id`, `edge_node_id`, `device_id`. Round-trips with `UnsPath`          |
| `GROUP_DELIMITER`                      | `":"`, the character the first three ISA-95 levels are joined with           |
| `mirror_topic_for(path)`               | The plain ISA-95 topic the JSON mirror publishes on                          |
| `MessageType`                          | `NBIRTH NDATA NDEATH DBIRTH DDATA DDEATH NCMD DCMD STATE`                    |
| `DataType`                             | The payload definition's datatype enumeration                                |
| `Quality`                              | `BAD` 0, `GOOD` 192, `STALE` 500                                             |
| `MetricSpec`                           | A metric a device declares at birth: name, datatype, unit, engineering range |
| `Metric`, `Payload`, `Message`         | The payload value objects                                                    |
| `WillRegistration`                     | The NDEATH to register as the MQTT Last Will, with its own QoS and retain    |
| `MirrorRecord`                         | One derived JSON record on the plain ISA-95 path                             |
| `topic_for(ids, type, device_id=None)` | Renders one Sparkplug topic                                                  |
| `state_topic_for(host_id)`             | `spBv1.0/STATE/{host_id}`                                                    |
| `qos_and_retain_for(type)`             | The QoS and retain flag for one topic class                                  |
| `QOS_BY_TOPIC_CLASS`, `QosRow`         | The matrix, with the rule id or the written basis per row                    |
| `NAMESPACE`                            | `"spBv1.0"`                                                                  |
| `SEQUENCE_MODULUS`                     | `256`                                                                        |
| `BDSEQ_METRIC`, `REBIRTH_METRIC`       | `"bdSeq"`, `"Node Control/Rebirth"`                                          |
| `MIRROR_QOS`, `MIRROR_RETAIN`          | The mirror's delivery flags, a repository choice                             |

`SparkplugIds.for_path(path)` maps an ISA-95 address onto the three Sparkplug
identifiers and `ids.to_uns_path(parameter)` maps it back, which is what makes
the claim in ARCHITECTURE.md section 5.1 checkable rather than asserted. The
mapping lives here rather than beside the grammar because it is one protocol's
reading of an address: the six levels are shared with the historian, the
`group_id` join is not, and pushing it down would make the config layer carry a
wire protocol it never speaks.

### Session order

`connect()` must come first and returns the `WillRegistration`. The ordering is
the point: `bdSeq` increments, the NDEATH carrying it is registered as the will,
and only then does the CONNECT happen and the NBIRTH follow. A will registered
after the birth is a will the broker never publishes for the failure it exists
to cover.

```
connect()            -> WillRegistration   bdSeq++, NDEATH, no seq
node_birth()         -> Message            NBIRTH, seq 0
device_birth(id)     -> Message            DBIRTH, alias table
node_data({...})     -> Message            NDATA, by alias
device_data(id, {})  -> Message            DDATA, by alias
device_death(id)     -> Message            DDEATH
rebirth()            -> tuple[Message,...] NBIRTH + every DBIRTH, seq back to 0
handle_node_command({...}) -> tuple[Message, ...]
alias_table()        -> dict[(device_id | None, name), int]
mirror_records(msg)  -> tuple[MirrorRecord, ...]
mirror_tombstones(id)-> tuple[MirrorRecord, ...]
```

Refusals are deliberate and each has a test: publishing before `connect()`,
a DBIRTH before NBIRTH, a DDATA from a device that has not birthed, and a
metric no birth certificate declared.

### Alias assignment

Aliases are unique across the **entire** edge node, node metrics and every
device's metrics together, because that is the scope the specification gives
them. Assignment sorts the keys byte-wise over their UTF-8 encoding and numbers
from 1. Alias 0 is never assigned, so a zero alias is always a bug and is
detectable as one; that last part is a repository rule, not a specification
rule.

Aliases may be reassigned across a birth boundary, so a consumer that caches
them across one is broken. This implementation happens to reproduce the same
table from the same input, which is a property of the sorting rule rather than
a guarantee a consumer may lean on.

### What this package does not claim

Gate **VAL-GATE-SPARK-001** names the Eclipse Sparkplug Technology Compatibility
Kit, edge-node profile, as its arbiter, and is falsified by one failure on that
profile. That suite has not been run against this code. Nothing here can be
read as a conformance claim, and doctrine D-11 rule 1 is why this section is
written at all: this repository is never a reference for itself.

Specifically still owed:

| Owed                                                                 | Why it is not here                                                                                                                                                                   |
| -------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| Protobuf wire encoding and decoding                                  | Needs the vendored EPL-2.0 `sparkplug_b.proto` under `schemas/iot/sparkplug/`, which this work package does not own                                                                  |
| A `DataType` table generated from that `.proto`                      | `sensor-catalog.md` D.3.2 asks for generation with a test that fails on drift. The values here are transcribed from that section by hand                                             |
| `ConformanceMatrix` reading `schemas/iot/sparkplug/conformance.yaml` | The file lives under the contract directory, which this work package does not own. `QOS_BY_TOPIC_CLASS` is the in-code stand-in and will be checked against that file once it exists |
| A committed TCK result under `artifacts/tck/`                        | Requires a Java and Maven job and a real broker                                                                                                                                      |
| The `seq`-discontinuity gap detector on the consumer side            | This package is the producer half                                                                                                                                                    |

The tests here assert the session rules against the normative statements
restated in ARCHITECTURE.md 5.1 and `docs/design/iot-fleet.md` 5.4. No test
compares the encoder against the encoder, and none of them is evidence of
conformance.

## RFID portal (`portal`)

| Symbol                  | What it is                                                                 |
| ----------------------- | -------------------------------------------------------------------------- |
| `PortalReader`          | One portal: its inventory, its faults, its telemetry                       |
| `ReaderConfig`          | Sensitivity floor, silence threshold, cap, optional EPC prefix             |
| `TagRead`               | One read record: EPC, sim timestamp, antenna port, RSSI, phase, read count |
| `InventoryAccumulator`  | Bounded accumulation keyed by (EPC, antenna)                               |
| `ReadAggregate`         | Count, min, max, and read-count-weighted mean RSSI for one key             |
| `EpcPrefixFilter`       | The read zone's inventory filter. Refuses an empty prefix                  |
| `PortalTelemetry`       | One window's published values, absent ones omitted                         |
| `PortalFault`           | `UNREACHABLE`, `SILENT`                                                    |
| `diagnose_portal(...)`  | The decision rule that keeps those two apart                               |
| `beta_scaled(rng, ...)` | `beta_scaled(lo, hi, mean, conc)` from variability-and-faults A            |
| `EPC`, `EPC_LENGTH`     | The 24-character uppercase-hex Gen2 identifier pattern                     |
| `TYPICAL_RSSI_BAND_DBM` | `(-70, -40)`. A repo-defined modeling assumption, not a measurement        |

`InventoryAccumulator` publishes two drop counters and they mean different
things. `dropped_new_epcs` counts **distinct** tags the cap refused and sizes
the loss. `dropped_reads` counts the read records discarded and is larger
whenever a refused tag was seen more than once. A single counter would let a
reader that saw one refused tag a hundred times report the same loss as one
that missed a hundred distinct pallets.

`PortalReader.observe()` raises on a read below the configured sensitivity,
because such a read does not happen: the sensitivity is the floor below which
the reader cannot demodulate a backscatter response at all. Deciding what is
readable belongs to the RF layer.

## Temperature sensor (`temperature`)

| Symbol                               | What it is                                              |
| ------------------------------------ | ------------------------------------------------------- |
| `TemperatureSensor`                  | One motor temperature channel                           |
| `TemperatureSensorConfig`            | Plausibility band and EWMA constant                     |
| `PlausibilityBand`                   | The range outside which a reading is not a measurement  |
| `PlausibilityViolation`              | Which bound was left, its limit, and the observed value |
| `TemperatureReading`                 | Raw and derived together, with quality                  |
| `RAW_PARAMETER`, `DERIVED_PARAMETER` | `"motor_temp_c"`, `"motor_temp_ewma_c"`                 |
| `ABSOLUTE_ZERO_C`                    | `-273.15`                                               |

A `PlausibilityBand` is not an alarm limit and not the engineering range. A
motor above its alarm limit is a real motor in trouble; a motor at -270 C is a
broken sensor. Only the second belongs here, so the band is wide enough to
contain every alarm the twin might raise.

## Package metadata

| Symbol        | What it is                                                             |
| ------------- | ---------------------------------------------------------------------- |
| `__version__` | The distribution version, read by the build so the two cannot disagree |

## Layering

`twinflow.sensors` sits in the `domain` layer. It imports `twinflow.kernel` for
the clock and `twinflow.config` for the namespace grammar, and nothing else from
the workspace. Both are below it. It imports no domain sibling, which
`tests/test_brick_isolated.py` asserts here and the workspace-wide
import-linter contract, so the defect fails in this package's own suite.

Devices return value objects rather than publishing. Wiring them to a transport
belongs above this layer.
