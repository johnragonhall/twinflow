---
title: "Sensor catalog: schema, 80 implemented types, failure signatures, and evidence rules"
description: The catalog-as-data contract for component 2b, covering the entry schema, every implemented type, failure signatures by class, wire mapping, and the tests that hold the physics claims honest.
topic_type: reference
audience: contributors
---

# Sensor catalog: schema, 80 implemented types, failure signatures, and evidence rules

Status: design spec, implementation contract. Written for TDD. Every capability named here has a
named test or CI gate.

Depends on: UNS topic design (component 2), twin state vector (components 1, 1b, 6a9), LSS engine
findings contract (component 5), Sparkplug B milestone (E3), schema registry (C3), config
validation (C5).

---

## 0. Purpose and thesis

The catalog is the deliverable, not the sensor count.

A sensor type is a row of data describing physics rather than a class in a source tree. The generator engine composes a small set of registered parts: a baseline, a coupling expression, a per-device unit offset, a noise family, a drift family, a response model, a sampler, a quantizer, an encoder, and a failure injector. A catalog entry names those parts and supplies parameters. Adding sensor type number 300 means writing one catalog entry and wiring one capability edge; it means touching no Python, no topic strings, and no twin code.

This section specifies the schema, the 80 implemented types, the failure signature taxonomy, the UNS and Sparkplug B mapping, the README extract, the scaling argument, the phase placement, and the test suite that holds all of it honest.

### 0.1 Four rules that govern every entry

Rule 1 and rule 2 are here because they are the most commonly violated rules in simulated telemetry. Rule 3 and rule 4 are here because they are what stop this section from asserting physics it cannot support.

1. **Support is correct by construction.** A quantity bounded to `[0, 1]` is generated from `beta_scaled`, not from a Normal that is clipped. A duration is generated from `lognormal`, `gamma`, or `weibull`, not from a Normal with negatives thrown away. A count is generated from `poisson` or `negbin`, not from a rounded Gaussian. An angle is generated from a circular family. Clipping is a bug rather than a safety net: it moves the moments of the distribution and flattens the tail the anomaly layer exists to find. `no_clamp_in_sampler` in `docs/design/variability-and-faults.md` section F is the gate.
2. **Tails are not truncated.** Rare extremes are real. A Weibull duration with shape 0.9 will occasionally return forty times its median. A `gp_tail` cargo shock will occasionally return a magnitude far above the trigger threshold. The pipeline must survive those values without clamping, and downstream consumers are tested against them. Physical bounds (relative humidity at or below 100 percent, state of charge in `[0, 1]`, cumulative metal loss monotone non-decreasing) are asserted in the property-based test suite, never enforced by a runtime clamp.
3. **Every published number carries its source.** A parameter in a catalog entry is a factual claim about a class of instrument, and this repository is never a reference for itself (D-11). Each entry carries a `provenance` block naming the publisher, the edition or version, and the locator for every parameter group, plus a confidence tier. Section A.7 defines the tiers and the CI gate. A parameter with no external source cannot ship in an entry marked `implemented`.
4. **Randomness is not defined here.** `docs/design/variability-and-faults.md` is the single source of truth for the RNG architecture, the stream naming grammar, the distribution catalog, and the fault catalog. This section names families and fault ids from those catalogs and never restates their definitions. Where this section needs a family that catalog does not carry, section A.4 records it as a registration request against that catalog rather than as a local primitive.

### 0.2 What this section owns and what it does not

`twinflow-sensors` owns the catalog loader and the signal-model registry. D-09 rules that every public symbol has exactly one owning package, and the same discipline applies to the documents: a contract stated twice is a contract that will drift.

| Surface                                                              | Owner                                   |
|----------------------------------------------------------------------|-----------------------------------------|
| RNG mechanism, stream names, distribution families, fault ids        | `docs/design/variability-and-faults.md` |
| Event envelope, determinism tiers, ports, packaging                  | `docs/design/DOCTRINE.md`               |
| Package boundaries, device runtime, edge tiers, Sparkplug codec      | `docs/design/iot-fleet.md`              |
| Phase graph and milestone sequencing                                 | `docs/design/roadmap.md`                |
| Entry physics, failure-signature taxonomy, evidence tiers, test plan | this section                            |

The catalog entry schema itself is claimed by both this section and `docs/design/iot-fleet.md` section 3.1, and the two claims do not agree on field names, file layout, or the per-category split of the 80 types. That conflict is recorded as OQ-11 with the full field list, because choosing between two designs is a program decision and not a fact this section can settle by assertion.

---

## A. The catalog schema

### A.1 Layout and file convention

```
catalog/
  sensors/
    _schema/
      sensor-type.schema.json      # JSON Schema draft 2020-12, the normative contract
      signal-models.md             # the registered signal-model kinds and their parameters
    industrial_equipment/
      eq.vib.band_spectrum.yaml
      eq.temp.thermocouple_k.yaml
      ...
    warehouse_logistics/
      whs.rfid.portal_read.yaml
      ...
  capabilities/
    capabilities.yaml              # capability ids, owners, consuming subsystems
  provenance/
    sources.yaml                   # one row per cited source: publisher, edition, locator, tier
```

One file per type. The filename is the type id. The directory is the category, and CI asserts the directory matches the declared `category` field so the two cannot drift. The layout is one of the surfaces in dispute with `docs/design/iot-fleet.md` section 3.1, which places one file per category holding a list of entries; OQ-11 records the conflict.

`provenance/sources.yaml` is a leaf file with no dependency on the catalog. Entries reference a source by id, so one standard cited by nine entries is recorded once and its edition cannot drift between them.

### A.2 Annotated example: a continuous, twin-coupled, spectral type

This is the fullest form of an entry. Every field in the schema appears here.

```yaml
# catalog/sensors/industrial_equipment/eq.vib.band_spectrum.yaml
schema_version: "1.0.0" # version of sensor-type.schema.json this entry targets
id: eq.vib.band_spectrum # globally unique, dot-delimited, [a-z0-9_.]+, immutable once published
revision: 1 # bump on any semantic change to this entry; recorded in telemetry
status: implemented # implemented | planned | deprecated
phase: P3 # earliest roadmap phase whose subsystem consumes it; CI checks it exists in ROADMAP.md
name: Order-tracked vibration band spectrum
category: industrial_equipment # one of the eight enumerated categories
summary: >
  Band-limited RMS velocity in shaft-order-referenced frequency bands. Emits a fixed
  vector of band energies (1x, 2x, 3x, BPFO, BPFI, BSF, FTF, broadband residual) computed
  on-device from a high-rate acceleration capture. This is the feature vector a vibration
  analyst reads, not the raw waveform.
tags: [rotating_equipment, bearing, predictive_maintenance, tier0_edge_compute]

# ---------------------------------------------------------------- measurement
measurement:
  quantity: velocity_rms # controlled vocabulary, used for MSA grouping
  unit: mm/s # UCUM code; CI validates against the UCUM table
  unit_display: "mm/s RMS"
  channel_shape: # scalar | vector | matrix; drives the Sparkplug datatype
    kind: vector
    length: 8
    labels: [ord_1x, ord_2x, ord_3x, bpfo, bpfi, bsf, ftf, broadband_residual]
  range_of_interest: [0.0, 45.0] # instrument span, NOT a clamp; values outside are legal and flagged
  resolution: 0.01
  reference_standard: "ISO 20816-3, velocity RMS, 10 Hz to 1000 Hz band"
  limit_source: SRC-ISO-20816-3 # required whenever a numeric alarm limit appears; resolves in sources.yaml
  accuracy_spec:
    linearity_pct_fs: 1.0
    transverse_sensitivity_pct: 5.0
  msa: # variance components the LSS engine's Gage R and R study is scored against
    repeatability_sigma: 0.021 # equipment variation, one appraiser, repeated measures
    reproducibility_sigma: 0.004 # appraiser variation; a fixed-mount sensor has almost none
    msa_source: SRC-REPO-MODEL # a declared modeling assumption, not a gauge study; see A.7

# ---------------------------------------------------------------- signal model
signal_model:
  # 1. Baseline: what the sensor reads when the asset is healthy.
  baseline:
    kind: state_function # constant | profile | state_function | event_process | state_machine
    expression: |
      # Safe, whitelisted expression language. Reads named twin state only.
      # Healthy machine: 1x line dominated by residual unbalance, which scales with speed squared.
      ord_1x            = 0.35 * (shaft_speed_hz / 24.0) ** 2 * (0.6 + 0.4 * load_fraction)
      ord_2x            = 0.30 * ord_1x * (1.0 + 2.5 * coupling_misalignment)
      ord_3x            = 0.12 * ord_1x
      bpfo              = 0.06 + 3.20 * bearing_outer_race_wear ** 1.8
      bpfi              = 0.05 + 2.60 * bearing_inner_race_wear ** 1.8
      bsf               = 0.04 + 1.90 * bearing_element_wear ** 1.8
      ftf               = 0.03 + 0.80 * bearing_cage_wear
      broadband_residual= 0.18 + 0.9 * bearing_stage4_fraction + 0.35 * mount_looseness
  # 2. Physical coupling: which twin state variables the expression may read.
  #    Resolved by the state broker at sample time. CI fails if any name is not a
  #    registered twin state variable with a declared unit.
  coupling:
    reads:
      - motor.shaft_speed_hz          as shaft_speed_hz
      - motor.load_fraction           as load_fraction
      - motor.coupling_misalignment   as coupling_misalignment
      - bearing.outer_race_wear       as bearing_outer_race_wear
      - bearing.inner_race_wear       as bearing_inner_race_wear
      - bearing.element_wear          as bearing_element_wear
      - bearing.cage_wear             as bearing_cage_wear
      - bearing.stage4_fraction       as bearing_stage4_fraction
      - mount.looseness               as mount_looseness
    # Defect-frequency geometry. The band center frequencies are computed from the bearing
    # geometry by the standard rolling-element relations, never stored as recalled numbers,
    # so a different bearing part number changes a config value and nothing else:
    #   BPFO = (n/2) * (1 - (d/D) cos(phi))
    #   BPFI = (n/2) * (1 + (d/D) cos(phi))
    #   BSF  = (D / 2d) * (1 - ((d/D) cos(phi))^2)
    #   FTF  = (1/2)   * (1 - (d/D) cos(phi))
    # with n rolling elements, ball diameter d, pitch diameter D, contact angle phi, and the
    # result expressed as a multiple of shaft rate. For n = 9, d = 7.94 mm, D = 39.04 mm,
    # phi = 0 these give 3.585, 5.415, 2.357, and 0.398. The identity BPFO + BPFI = n is
    # asserted in CI, so a mistyped geometry cannot pass silently.
    derived_constants:
      bearing_geometry_ref: 6205_9ball # resolves in catalog/reference/bearings.yaml
      band_center_hz: "order_multiplier * shaft_speed_hz"
      band_halfwidth_pct: 4.0
  # 3. Unit offset: the fixed per-device error drawn once at provisioning and held for the
  #    life of the device. Without it every device of a type reads identically at zero wear,
  #    which is the tell that separates simulated telemetry from a real fleet. The stream is
  #    provision.sensor.<device_id>.unit_offset, per variability-and-faults A.2.
  unit_offset:
    family: normal # named in the variability-and-faults distribution catalog
    params: { sigma: 0.018 }
    mode: multiplicative
  # 4. Noise: measurement noise on top of the baseline. Support must match the quantity.
  #    Every family below is a row in the variability-and-faults distribution catalog.
  noise:
    - applies_to: [ord_1x, ord_2x, ord_3x, bpfo, bpfi, bsf, ftf]
      family: lognormal # band RMS is strictly positive; multiplicative error is the physical form
      params: { median: 1.0, sigma_log: 0.11 }
      mode: multiplicative
    - applies_to: [broadband_residual]
      family: gamma
      params: { shape: 14.0, mean_from_baseline: true }
    - applies_to: all
      family: ar1 # the catalog's colored-noise family, standing in for amplifier flicker
      params: { phi: 0.94, sigma: 0.004 }
  # 5. Drift: slow, non-stationary error that is NOT the asset degrading.
  drift:
    - family: ou # mean-reverting sensitivity error from mount preload relaxation
      applies_to: all
      params: { mean: 0.0, reversion_per_day: 0.09, sigma_per_sqrt_day: 0.006 }
      mode: multiplicative
    - family: arrhenius_accelerated # REGISTRATION REQUEST against the distribution catalog;
      # see A.4, "families this section needs that the catalog does not yet carry"
      applies_to: all
      params:
        activation_energy_ev: 0.65
        reference_temp_c: 25.0
        rate_at_reference_per_year: -0.012
        temp_source: eq.temp.rtd_pt100@same_equipment
  # 6. Sampling.
  sampling:
    mode: periodic # periodic | on_change | on_event | polled | burst
    interval_s: 60
    jitter:
      family: gamma
      params: { shape: 3.0, mean_s: 0.35 } # positive-support jitter; never a symmetric Normal
    phase_offset_policy: hash_of_device_id # avoids a thundering herd of 500 devices on the same second
    aggregation_window_s: 1.0 # on-device capture length feeding the band computation
    edge_compute_tier: 0 # E36: FFT and banding run on the device
    raw_capture:
      available: true
      sample_rate_hz: 25600
      duration_s: 1.0
      publish_policy: on_demand_or_on_alarm # never streamed; see open question OQ-5
  # 7. Quantization and transport-level effects applied after noise and drift.
  quantization:
    adc_bits: 16
    full_scale: 50.0
    dither: true
  response:
    kind: none # this channel has no thermal lag; see thermocouple entry
  # 8. RNG streams this entry draws from. Names follow the grammar in
  #    variability-and-faults A.2 and are content addressed, so adding a channel to this
  #    entry cannot shift any other entry's draws.
  rng_streams:
    - "provision.sensor.{device_id}.unit_offset"
    - "sensor.{type_id}.{device_id}.noise"
    - "sensor.{type_id}.{device_id}.drift"
    - "sensor.{type_id}.{device_id}.jitter"

# ---------------------------------------------------------------- failure modes
failure_modes:
  # Universal modes are inherited from the class profile and may be overridden here.
  inherits_profile:
    continuous_analog # pulls in drift, stuck_at, dropout, calibration_loss, bias_step,
    # noise_inflation, saturation, clock_skew, crash_loop
  overrides:
    - id: calibration_loss
      catalog_id: F-DEV-CALIB # resolves in the fault catalog, variability-and-faults C.4
      onset:
        family: weibull # time-to-onset; shape < 1 gives infant mortality, > 1 gives wear-out
        params: { shape: 1.6, scale_days: 900 }
      effect:
        {
          kind: gain_error,
          gain_distribution:
            { family: beta_scaled, params: { lo: 0.55, hi: 1.0, mean: 0.86, conc: 8 } },
        }
      detectable_by: [msa_stability_study, spc_ewma_on_residual]
      expected_mttd_hours: 72
      severity: 6 # FMEA S rating, 1 to 10, engineering judgement, recorded not guessed
      pf_interval_hours: 720 # P-F interval; this is what grounds the FMEA D rating
  specific:
    - id: mount_looseness
      catalog_id: F-DEV-DRIFT
      description: >
        Loose sensor mount or a degraded magnetic base. Raises broadband_residual and adds
        a smeared harmonic series, but does NOT raise the defect-frequency bands. That
        asymmetry is how an analyst separates a sensor problem from a bearing problem.
      onset: { family: weibull, params: { shape: 2.2, scale_days: 1400 } }
      effect:
        kind: expression_override
        expression: |
          broadband_residual = broadband_residual * (1.0 + 2.8 * severity_fraction)
          ord_2x = ord_2x * (1.0 + 0.9 * severity_fraction)
        # severity_fraction, not severity: the FMEA S rating above is an integer 1 to 10 and
        # this is a bounded progression variable. One term per concept.
        severity_fraction:
          { family: beta_scaled, params: { lo: 0.0, hi: 1.0, mean: 0.4, conc: 5 } }
      detectable_by: [fleet_health_signature_classifier, pdm_trend_layer]
      expected_mttd_hours: 24
      severity: 5
      pf_interval_hours: 336
      confusable_with: [bearing_outer_race_defect] # drives the MSA and classifier test cases
    - id: speed_reference_loss
      catalog_id: F-DEV-STUCK
      description: >
        The tachometer or encoder reference disappears, so order tracking falls back to a
        fixed assumed speed. Bands drift off the true defect frequencies and every defect
        band collapses toward the noise floor. Reads as a sudden improvement,
        which is the trap: the machine looks healthier the moment the measurement breaks.
      onset: { family: exponential, params: { mean_days: 1111 } }
      effect: { kind: band_decoherence, residual_fraction: 0.15 }
      detectable_by:
        [cross_sensor_consistency, fleet_health_signature_classifier]
      expected_mttd_hours: 6
      severity: 8
      pf_interval_hours: 24
      severity_floor: major
    - id: cable_microphonics
      catalog_id: F-DEV-NOISEUP
      description: >
        Triboelectric noise from a coax cable rubbing on a moving guard. Injects
        low-frequency bursts correlated with machine motion, not with bearing condition.
      onset: { family: weibull, params: { shape: 1.1, scale_days: 600 } }
      effect:
        {
          kind: burst_noise,
          arrival:
            {
              family: hawkes, # REGISTRATION REQUEST; see A.4
              params: { mu_per_hour: 0.4, alpha: 0.6, decay_per_hour: 3.0 },
            },
        }
      detectable_by: [spc_western_electric, alarm_rationalization]
      expected_mttd_hours: 48
      severity: 4
      pf_interval_hours: 168

# ------------------------------------------------------- whole-device faults
# Modes that belong to the device rather than to any one channel. Every id resolves in the
# fault catalog, and the device runtime owns the injection point (iot-fleet section 5).
device_faults: [F-DEV-DROP, F-DEV-CLOCKDRIFT, F-DEV-CRASHLOOP, F-DEV-PROVISION]

# ---------------------------------------------------------------- attachment
attaches_to:
  subsystem: conveyor_drive # primary twin subsystem key
  also_serves: [palletizer_cell, asrs_crane, factory_mixer_drive]
  binding:
    per_equipment # per_site | per_area | per_line | per_equipment | per_asset_instance
    # | per_vehicle | per_lot | per_worker
  cardinality:
    default_per_binding: 1
    max_per_binding: 3 # drive end, non-drive end, gearbox
  instance_naming: "vib-{equipment_id}-{position}"
  positions: [de, nde, gearbox] # optional sub-position vocabulary, appended to the parameter level

# ---------------------------------------------------------------- UNS mapping
# Telemetry is published through the Network port, the MQTT-shaped one, because it needs
# retain, QoS, last will, and wildcard subscribe. It never uses EventBus (D-08).
uns:
  topic_template: "{enterprise}/{site}/{area}/{line}/{equipment}/{parameter}"
  parameter: "vibration/band_spectrum/{position}"
  qos: 1
  retain: false
  payload_encoding: sparkplug_b # sparkplug_b | json_fallback
  legacy_json_topic_suffix: "/json" # published only when the json_fallback profile is enabled

# ---------------------------------------------------------------- Sparkplug B
sparkplug:
  metric_name: "{line}/{equipment}/vibration/band_spectrum/{position}"
  datatype: FloatArray # enum 30; vector-of-8 float. Scalar types use Float (9) or Double (10)
  element_datatype: Float
  alias_policy: deterministic_at_birth # see section D.3
  is_transient: false
  is_historical_on_replay: true
  properties:
    engUnit: "mm/s"
    engLow: 0.0
    engHigh: 45.0
    description: "ISO 20816-3 band RMS velocity, order tracked"
    Quality: 192 # 192 is GOOD; 0 is BAD and 500 is STALE, per the Sparkplug specification
    sensor_type_id: "eq.vib.band_spectrum" # the catalog type. Distinct from failure_modes[].catalog_id,
    # which names a fault. One term per concept.
    sensor_type_revision: 1
    band_labels: "ord_1x,ord_2x,ord_3x,bpfo,bpfi,bsf,ftf,broadband_residual"
  birth_defaults:
    publish_on_dbirth: true
    initial_value_policy: first_real_sample # never a fabricated zero

# ---------------------------------------------------------------- capability wiring
capability:
  unlocks:
    - pdm.bearing_defect_detection
    - pdm.time_to_threshold_estimate
    - lss.spc_on_vibration_bands
    - energy.mechanical_loss_attribution
  consumed_by: # CI cross-checks these against capabilities.yaml
    - predictive_maintenance.trend_engine
    - lss_engine.spc
    - cmms_queue.work_order_generator
  rationale: >
    Broadband RMS alone cannot distinguish a bearing defect from unbalance or looseness.
    Banding at the defect frequencies is what makes "motor 2 bearing trend crosses the
    alarm limit in about 9 days" a defensible statement rather than a guess.

# ---------------------------------------------------------------- validation
validation:
  physical_bounds: # property-test assertions; NEVER runtime clamps
    - "all(v >= 0.0 for v in value)"
    - "broadband_residual <= 8.0 * mean(ord_1x, ord_2x, ord_3x) or bearing_stage4_fraction > 0.6"
  monotonicity: []
  goodness_of_fit:
    - channel: ord_1x
      holding: { shaft_speed_hz: 24.0, load_fraction: 0.7, all_wear: 0.0 }
      declared: { family: lognormal, sigma_log: 0.11 }
      test: anderson_darling
      n_samples: 200000
      alpha: 0.01
    - channel: bpfo
      holding: { bearing_outer_race_wear: 0.35 }
      assertion: "spectral_energy_fraction_in_band(bpfo_center, halfwidth=4%) >= 0.80"
  cross_checks:
    - "eq.vib.velocity_rms on the same equipment must equal quadrature sum of bands within 12 percent"
  # Two determinism tiers, not one (D-05). Byte identity is claimed only on a pinned
  # platform; across platforms the claim is value equivalence within a measured tolerance,
  # and the cross-platform job reports the observed maximum divergence.
  determinism:
    same_platform: byte_identical
    cross_platform: value_equivalent
    cross_platform_tolerance_rel: 1.0e-9 # provisional; replaced by the measured figure at P3
  budget:
    max_generator_cost_us_per_sample: 900
    max_payload_bytes: 96

# ---------------------------------------------------------------- provenance
# One row per parameter group. Every id resolves in catalog/provenance/sources.yaml, which
# carries publisher, title, edition or version, locator, retrieval date, and tier (A.7).
provenance:
  - covers: [measurement.reference_standard, measurement.range_of_interest, validation.cross_checks]
    source: SRC-ISO-20816-3
    tier: C # named standard, body paywalled; the zone values are read at implementation time
  - covers: [signal_model.coupling.derived_constants]
    source: SRC-DERIVED-BEARING-GEOMETRY
    tier: A # arithmetic from the stated relations and the stated geometry, checkable in place
  - covers: [signal_model.noise, signal_model.drift, signal_model.unit_offset, msa]
    source: SRC-REPO-MODEL
    tier: D # a modeling assumption with no external source; blocks status: implemented
```

The last row is the one that matters. It is tier D, so CI refuses `status: implemented` on this entry until either an external source is found for the noise and drift parameters or those parameters are restated as a derivation from something that has one. That is rule 3 of section 0.1 with teeth, and it is why A.7 exists.

### A.3 Two shorter forms, for shape variety

Both forms below omit the `provenance`, `msa`, `rng_streams`, and `determinism` blocks, which are required and identical in shape to A.2. They are dropped here so the structural difference stands out.

#### A.3.1 Probabilistic event type

The RFID portal read, which is not a periodic sample at all.

```yaml
id: whs.rfid.portal_read
category: warehouse_logistics
phase: P1 # the walking skeleton instantiates one portal
measurement:
  quantity: read_event
  unit: "1" # dimensionless event; per-read payload carries RSSI in dBm
  channel_shape: { kind: template } # Sparkplug Template: epc, antenna_port, rssi_dbm, phase_rad, read_count
signal_model:
  baseline:
    kind: event_process
    expression: |
      # Forward-link-limited Friis. Read probability PER INVENTORY ROUND, per tag.
      p_orient   = clamp01(cos_sq(tag_angle_to_antenna) * polarization_match)
      p_range    = sigmoid((eirp_dbm + tag_sensitivity_dbm - path_loss_db(range_m)) / 2.2)
      p_material = material_detune_factor          # per material class; values carry provenance
      p_collide  = 1.0 / (1.0 + population_in_field / q_slots)
      p_round    = p_orient * p_range * p_material * p_collide * (1.0 - vfd_interference_loss)
      rounds     = floor(dwell_s * reader_rounds_per_s)   # dwell = portal_depth_m / pallet_speed_mps
      # Reads per tag over the pass:
      reads      = betabinom(rounds, mean_p=p_round, conc=tag_conc)
  coupling:
    reads:
      - conveyor.pallet_speed_mps  as pallet_speed_mps
      - pallet.tag_population      as population_in_field
      - pallet.material_class      as material_class
      - portal.eirp_dbm            as eirp_dbm
      - portal.antenna_vswr        as antenna_vswr
      - line.vfd_emission_index    as vfd_interference_loss
  # Regulatory ceiling on the forward link, so eirp_dbm cannot be set to a value no real
  # portal is allowed to radiate. 47 CFR 15.247 covers the 902-928 MHz band, caps digital
  # modulation at 1 W conducted, and permits an antenna of up to 6 dBi directional gain with
  # no power reduction, which is 36 dBm EIRP.
  constraints:
    - "eirp_dbm <= 36.0" # source SRC-CFR-47-15-247
  noise:
    - applies_to: [rssi_dbm]
      family: rician # REGISTRATION REQUEST; the catalog carries rayleigh, not rician. See A.4
      params: { k_factor_db: 6.0, sigma_db: 3.2 }
    - applies_to: [tag_angle_to_antenna]
      family: von_mises # REGISTRATION REQUEST; angles need a circular family, not a Normal
      params: { kappa: 2.5 }
sampling:
  mode: on_event
  trigger: "pallet enters read zone geometry"
failure_modes:
  inherits_profile: probabilistic_event # dropout, duplicate_read, clock_skew, crash_loop, degraded_read_rate
  specific:
    - id: antenna_vswr_rise
      catalog_id: F-DEV-READRATE
      description: >
        A corroding N-connector or a crushed coax raises VSWR. The reflected power fraction
        is the square of the reflection coefficient (S-1)/(S+1), which is 1/9 at S = 2 and
        1/4 at S = 3. Range for a forward-link-limited system scales with the square root of
        radiated power, so S = 3 leaves sqrt(0.75) of the range, a loss of 13.4 percent. The
        signature is a read-rate decline on ONE antenna port while its siblings hold, which
        is how it is told apart from a tag or product problem.
      onset: { family: weibull, params: { shape: 2.4, scale_days: 1100 } }
      effect:
        {
          kind: parameter_ramp,
          target: portal.antenna_vswr,
          to: 3.2,
          ramp_days: 40,
        }
      detectable_by:
        [fleet_health_read_rate_control_chart, rf_physics_diagnostic]
      expected_mttd_hours: 96
      severity: 5
      pf_interval_hours: 960
    - id: cross_read
      catalog_id: F-DEV-GHOST
      description: >
        A tag on the adjacent dock is caught by this portal. A FALSE POSITIVE, not a miss.
        Generates a read event on the wrong equipment topic, which the receiving
        reconciliation logic must reject via ASN cross-check or dwell-time plausibility.
      onset: { family: always_on }
      effect:
        {
          kind: spurious_event,
          rate:
            { family: poisson, params: { rate_per_adjacent_pass: 0.035 } },
        }
      detectable_by: [erp_asn_reconciliation, cv_count_cross_check]
      expected_mttd_hours: 2
      severity: 7
      pf_interval_hours: 4
    - id: tag_detune
      catalog_id: F-DEV-READRATE
      description: >
        Liquid or metal load shifts the tag antenna resonance off the 902 to 928 MHz band
        that 47 CFR 15.247 allocates for this service, so the tag stops matching the reader.
      onset: { family: bernoulli, params: { p: 0.06 }, per: pallet }
      effect:
        {
          kind: parameter_set,
          target: material_detune_factor,
          value_distribution:
            { family: beta_scaled, params: { lo: 0.0, hi: 1.0, mean: 0.19, conc: 7.4 } },
        }
      detectable_by: [read_rate_by_sku_class, cv_count_cross_check]
      severity: 4
      pf_interval_hours: 24
device_faults: [F-DEV-DROP, F-DEV-DUPREAD, F-DEV-CLOCKDRIFT, F-DEV-CRASHLOOP]
```

#### A.3.2 Discrete state type

The e-stop, which is a state machine and not a sampled scalar.

```yaml
id: saf.estop.circuit
category: safety_compliance
phase: 6a10 # the safety category lands with component 6a10
measurement:
  quantity: safety_circuit_state
  unit: "1"
  channel_shape: { kind: scalar }
  state_vocabulary:
    [armed, tripped, fault_channel_a, fault_channel_b, cross_fault]
signal_model:
  baseline:
    kind: state_machine
    initial: armed
    transitions:
      - {
          from: armed,
          to: tripped,
          trigger: twin_event,
          event: safety.estop_pressed,
        }
      - {
          from: tripped,
          to: armed,
          trigger: twin_event,
          event: safety.reset_pressed,
          guard: "guard_closed and no_worker_in_zone",
        }
    dwell_time: # durations use positive-support families, always
      tripped:
        { family: lognormal, params: { median_s: 145, sigma_log: 0.85 } }
  noise: [] # a discrete safety circuit has no measurement noise; it has faults
  unit_offset: { family: none, why: "a state has no offset to draw" }
sampling:
  mode: on_change
  heartbeat_s: 30 # a safety input republishes even when unchanged
failure_modes:
  inherits_profile: discrete_state # stuck_at, dropout, clock_skew, crash_loop, chatter
  specific:
    - id: welded_contact
      catalog_id: F-DEV-STUCK
      description: >
        A contact welds closed and the circuit reports armed forever. The dangerous
        failure, because it is silent: the reading is the safe-looking one. Detected only
        by proof testing or by the absence of expected state changes over a window.
      onset: { family: weibull, params: { shape: 1.8, scale_days: 3200 } }
      effect: { kind: stuck_at, value: armed }
      detectable_by: [absence_of_expected_transition, scheduled_proof_test]
      expected_mttd_hours: 720
      severity: 10
      pf_interval_hours: 2160 # the proof-test interval is the only thing that bounds this
      severity_floor: critical
    - id: contact_bounce
      catalog_id: F-DEV-NOISEUP
      description: >
        Contact wear produces a burst of state changes faster than any physical actuation.
      onset: { family: weibull, params: { shape: 1.4, scale_days: 2000 } }
      effect:
        {
          kind: chatter,
          burst_len: { family: poisson, params: { rate: 4 } },
          interval_ms: 12,
        }
      detectable_by: [alarm_rationalization_debounce]
      expected_mttd_hours: 1
      severity: 3
      pf_interval_hours: 8
device_faults: [F-DEV-DROP, F-DEV-CLOCKDRIFT, F-DEV-CRASHLOOP]
```

### A.4 Field-by-field reference

#### A.4.1 Identity block

| Field            | Type          | Required | Meaning and rules                                                                                                                                                                                           |
|------------------|---------------|----------|-------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| `schema_version` | semver string | yes      | Version of `sensor-type.schema.json` this entry targets. Loader refuses a major mismatch.                                                                                                                   |
| `id`             | string        | yes      | Globally unique, `[a-z0-9_.]+`, dot-delimited `category_prefix.family.specific`. Immutable once published. A breaking change is published as a new id, and the superseded id carries a `deprecated` marker. |
| `revision`       | integer       | yes      | Increments on any semantic change. Stamped into every published payload as the `sensor_type_revision` Sparkplug property so a historian row always knows which model produced it.                           |
| `status`         | enum          | yes      | `implemented`, `planned`, `deprecated`. Only `implemented` entries instantiate devices, and A.7 blocks that status while any parameter group is tier D.                                                     |
| `phase`          | enum          | yes      | Earliest roadmap phase whose subsystem consumes the type. CI checks the value exists in ROADMAP.md. Section H holds the assignment.                                                                         |
| `name`           | string        | yes      | Human name for the README table and the dashboard.                                                                                                                                                          |
| `category`       | enum          | yes      | One of the eight categories. Must equal the containing directory.                                                                                                                                           |
| `summary`        | string        | yes      | Two to four sentences. What it measures and what makes the model non-trivial.                                                                                                                               |
| `tags`           | string list   | no       | Free-form facets for filtering (`rotating_equipment`, `cold_chain`, `wearable`, `tier0_edge_compute`).                                                                                                      |

#### A.4.2 Measurement block

| Field                            | Type       | Required | Meaning and rules                                                                                                                                                                                      |
|----------------------------------|------------|----------|--------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| `measurement.quantity`           | enum       | yes      | Controlled vocabulary (`temperature`, `velocity_rms`, `mass`, `read_event`, ...). Groups types for measurement system analysis so a Gage R&R can compare two technologies measuring the same quantity. |
| `measurement.unit`               | UCUM code  | yes      | Machine-checkable. CI validates against the UCUM table and rejects free text.                                                                                                                          |
| `measurement.unit_display`       | string     | no       | What the dashboard prints.                                                                                                                                                                             |
| `measurement.channel_shape`      | object     | yes      | `scalar`, `vector` with `length` and `labels`, `matrix` with `rows`/`cols`, or `template` with a named field list. Drives the Sparkplug datatype selection.                                            |
| `measurement.range_of_interest`  | `[lo, hi]` | yes      | Instrument span. Documentation and dashboard scaling only. **Not a clamp.** Out-of-span values are legal, published, and flagged by the plausibility validator.                                        |
| `measurement.resolution`         | number     | no       | Smallest meaningful increment before quantization is applied.                                                                                                                                          |
| `measurement.reference_standard` | string     | no       | The standard the reading is referenced to (ISO 20816-3, ISO 4406, ASTM E230). Names the standard; it does not reproduce values from it.                                                                |
| `measurement.limit_source`       | source id  | cond.    | Required whenever the entry carries a numeric alarm, warn, or trip limit. Resolves in `provenance/sources.yaml`. A limit with no source fails the build.                                               |
| `measurement.accuracy_spec`      | object     | no       | Datasheet-class error terms carried for the MSA layer to consume as a declared truth. Governed by the entry's `provenance` block.                                                                      |
| `measurement.msa`                | object     | yes      | `repeatability_sigma` and `reproducibility_sigma`, or an `msa_note` excluding the channel. These are the declared variance components the LSS engine's Gage R and R study is scored against.           |

#### A.4.3 Signal model block

| Field                                     | Type   | Required    | Meaning and rules                                                                                                                                                                                                                                                                                                                             |
|-------------------------------------------|--------|-------------|-----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| `signal_model.baseline.kind`              | enum   | yes         | `constant`, `profile` (a named time profile: diurnal, shift-pattern, seasonal), `state_function` (expression over twin state), `event_process` (arrivals), `state_machine` (discrete states with dwell times).                                                                                                                                |
| `signal_model.baseline.expression`        | expr   | conditional | Whitelisted expression language: arithmetic, `min`/`max`/`clamp01`/`exp`/`log`/`sqrt`/`sigmoid`/`cos_sq`, named distribution draws, and registered twin state names only. No attribute access, no imports, no I/O. Parsed to an AST and statically checked at load.                                                                           |
| `signal_model.baseline.profile`           | object | conditional | For `kind: profile`: a named profile plus amplitude and phase. Diurnal profiles use sim-time, never wall-clock.                                                                                                                                                                                                                               |
| `signal_model.coupling.reads`             | list   | conditional | `twin.state.path as local_name`. CI fails if the path is not a registered twin state variable with a declared unit, and fails if the expression references a name not declared here. This is the field that stops a decorative sensor: no coupling means no twin linkage, and the entry then has to justify itself in `capability.rationale`. |
| `signal_model.coupling.derived_constants` | object | no          | Physics constants resolved from a reference table (bearing geometry, pipe diameter, tank cross-section) so the same catalog entry serves different equipment by changing a reference key.                                                                                                                                                     |
| `signal_model.unit_offset`                | object | yes         | The fixed per-device error drawn once at provisioning from `provision.sensor.{device_id}.unit_offset` and held for the device's life. `{family: none, why: ...}` is the only way to omit it, so a fleet of identical readings is always a decision.                                                                                           |
| `signal_model.noise`                      | list   | yes         | Each element names a `family` from the distribution catalog in `docs/design/variability-and-faults.md` section B, an `applies_to` channel list, and params. May be empty only for discrete state types.                                                                                                                                       |
| `signal_model.drift`                      | list   | yes         | Slow, non-stationary sensor error that is not asset degradation. May be an empty list, but the field must be present so the omission is a decision, not an oversight.                                                                                                                                                                         |
| `signal_model.sampling`                   | object | yes         | `mode`, `interval_s` or `trigger`, jitter distribution (positive support only), phase offset policy, aggregation window, edge compute tier.                                                                                                                                                                                                   |
| `signal_model.quantization`               | object | no          | ADC bits, full scale, dither. Applied after noise and drift, in that order, matching the real signal chain.                                                                                                                                                                                                                                   |
| `signal_model.response`                   | object | no          | Sensor dynamics. `first_order_lag` with `tau_s`, `second_order` with `wn`/`zeta`, or `none`. A thermocouple, a pH electrode, and a fuel level float all need this and getting it wrong is the single most common tell in fake telemetry.                                                                                                      |
| `signal_model.rng_streams`                | list   | yes         | Every stream name the entry draws from, in the grammar of `docs/design/variability-and-faults.md` section A.2. Content addressed, so adding a channel to one entry cannot shift another entry's draws. CI checks each name against the stream registry.                                                                                       |

#### A.4.4 Distribution families and where they are defined

`docs/design/variability-and-faults.md` section B is the single source of truth for the distribution catalog. This section names families from it and never redefines them. The mapping below exists because the same physical need is described in two vocabularies, and one term per concept means the catalog's name wins.

| Family in the distribution catalog | Support              | What the sensor catalog uses it for                                                    |
|------------------------------------|----------------------|----------------------------------------------------------------------------------------|
| `normal`                           | real                 | Johnson and amplifier thermal noise on a bipolar channel; the per-device `unit_offset` |
| `lognormal`                        | positive             | Any strictly positive amplitude with proportional error; response and travel durations |
| `shifted_lognormal`                | positive above shift | A duration with a physical floor, such as a door travel time                           |
| `gamma`                            | positive             | Positive energies and sampling jitter                                                  |
| `weibull`                          | positive             | Time-to-onset for wear-out and infant-mortality failures                               |
| `beta_scaled`                      | `[lo, hi]`           | Bounded ratios: state of charge, relative humidity, read rate, water activity          |
| `poisson`                          | non-negative integer | Counts of events in a window                                                           |
| `negbin`                           | non-negative integer | Over-dispersed counts, such as particle counts and scan no-reads                       |
| `betabinom`                        | `{0..n}`             | Over-dispersed bounded counts, such as RFID reads over inventory rounds                |
| `bernoulli`                        | `{0, 1}`             | Per-trial success, such as one barcode presentation                                    |
| `exponential`                      | positive             | Memoryless inter-arrival, and the strictly positive non-line-of-sight range bias       |
| `rayleigh`                         | positive             | Scattered multipath fading on RSSI where no dominant path exists                       |
| `gp_tail`                          | positive tail        | Extreme shock, extreme demand, extreme transit delay. Never truncated.                 |
| `ar1`                              | real, correlated     | The catalog's colored-noise family, standing in for flicker and MEMS bias instability  |
| `wiener`                           | real, correlated     | Unbounded integrator drift, such as coulomb counting error and gyro bias               |
| `ou`                               | real, correlated     | Mean-reverting drift, such as mount preload relaxation and thermal offset              |
| `semi_markov`                      | discrete states      | State machines with per-state holding distributions                                    |
| `nhpp`                             | event times          | Arrival rates that follow a shift or diurnal profile                                   |
| `hierarchical`                     | inherited            | A per-device effect drawn once with per-event noise drawn on top                       |

Six families this section needs are not in that catalog. They are registration requests against it, not local primitives, and each carries the entry that forced it. Until a family is registered there, an entry naming it cannot reach `status: implemented`.

| Requested family        | Support     | Forced by                                                                   |
|-------------------------|-------------|-----------------------------------------------------------------------------|
| `von_mises`             | angle       | Tag orientation, load tilt heading, shaft phase: a Normal cannot wrap       |
| `rician`                | positive    | RSSI fading at a portal, where a dominant path exists and Rayleigh is wrong |
| `hawkes`                | event times | Self-exciting clustered arrivals: acoustic emission bursts, near-misses     |
| `student_t`             | real        | Measurement error where outliers are physical rather than contamination     |
| `arrhenius_accelerated` | monotone    | Temperature-accelerated ageing: piezo sensitivity loss, electrolyte dry-out |
| `linear_ramp`           | monotone    | Slow leaks, cumulative metal loss, battery capacity fade                    |

Registering a family is the one change that needs code. Section F sets out why the set is close to closed.

#### A.4.5 Failure modes block

| Field                            | Type    | Required | Meaning and rules                                                                                                                                                                                                                   |
|----------------------------------|---------|----------|-------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| `failure_modes.inherits_profile` | enum    | yes      | One of the class profiles in section C.1. Pulls in the universal modes with class-appropriate defaults so no entry re-specifies drift and dropout.                                                                                  |
| `failure_modes.overrides`        | list    | no       | Per-entry parameter changes to inherited modes.                                                                                                                                                                                     |
| `failure_modes.specific`         | list    | yes      | Class-specific modes. Each carries `id`, `catalog_id`, `description`, `onset`, `effect`, `detectable_by`, `expected_mttd_hours`, `severity`, `pf_interval_hours`, and optional `severity_floor` and `confusable_with`.              |
| `...catalog_id`                  | id      | yes      | The fault id in `docs/design/variability-and-faults.md` section C.4. CI checks it resolves. A mode with no fault id has no injector and cannot be tested.                                                                           |
| `...onset`                       | object  | yes      | A time-to-onset family from the distribution catalog, or `always_on`, or `bernoulli` with a `per` scope naming the trial (`pallet`, `pass`, `shift`).                                                                               |
| `...effect.kind`                 | enum    | yes      | `gain_error`, `offset_bias`, `stuck_at`, `dropout`, `noise_inflation`, `parameter_ramp`, `parameter_set`, `expression_override`, `spurious_event`, `band_decoherence`, `burst_noise`, `chatter`, `saturation`, `response_slowdown`. |
| `...effect.severity_fraction`    | object  | cond.    | A bounded progression variable on `[0, 1]` that an `expression_override` reads. Named apart from `severity` because they are different quantities.                                                                                  |
| `...detectable_by`               | id list | yes      | Which analysis layer is expected to catch it. CI asserts each id is a registered detector, and the failure-injection test suite asserts that detector fires within `expected_mttd_hours`.                                           |
| `...expected_mttd_hours`         | number  | yes      | The mean-time-to-detect budget. This is the number the fleet-health layer is scored against, so it is a commitment, not a comment.                                                                                                  |
| `...severity`                    | integer | yes      | FMEA severity rating, 1 to 10. Engineering judgement, recorded so it can be argued with rather than left implicit.                                                                                                                  |
| `...pf_interval_hours`           | number  | yes      | The potential-failure to functional-failure interval. This is what grounds the FMEA detection rating, and a detection budget longer than this interval is a defect the fleet-health layer reports.                                  |
| `...severity_floor`              | enum    | no       | Minimum finding severity. Safety class entries set this so a safety finding can never be ranked below a throughput finding.                                                                                                         |
| `...confusable_with`             | id list | no       | Modes with a similar surface signature. Generates the hard cases for the signature classifier test set.                                                                                                                             |
| `device_faults`                  | id list | yes      | Whole-device modes that belong to no single channel: link loss, clock drift, crash loop, misprovisioning. Each id resolves in the fault catalog and the device runtime owns the injection point.                                    |

#### A.4.6 Attachment block

| Field                         | Type        | Required | Meaning and rules                                                                                                                     |
|-------------------------------|-------------|----------|---------------------------------------------------------------------------------------------------------------------------------------|
| `attaches_to.subsystem`       | id          | yes      | Primary twin subsystem key. Must exist in the twin's subsystem registry.                                                              |
| `attaches_to.also_serves`     | id list     | no       | Other subsystems that may instantiate this type.                                                                                      |
| `attaches_to.binding`         | enum        | yes      | The ISA-95 level (or non-ISA-95 asset class) an instance attaches to. Determines which topic levels are filled and which are literal. |
| `attaches_to.cardinality`     | object      | yes      | Default and maximum instances per binding, so `facility.yaml` cannot silently over-instrument.                                        |
| `attaches_to.instance_naming` | template    | yes      | Device id template. Must resolve to a unique string given the binding.                                                                |
| `attaches_to.positions`       | string list | no       | Sub-position vocabulary appended to the parameter level (drive end, non-drive end, per-phase, per-wheel).                             |

#### A.4.7 UNS and Sparkplug blocks

Specified in section D.

#### A.4.8 Capability block

| Field                    | Type    | Required | Meaning and rules                                                                                             |
|--------------------------|---------|----------|---------------------------------------------------------------------------------------------------------------|
| `capability.unlocks`     | id list | yes      | Capability ids this type feeds. Must be non-empty.                                                            |
| `capability.consumed_by` | id list | yes      | Subsystems that declare a dependency on those capabilities. Must be non-empty. This is the anti-orphan field. |
| `capability.rationale`   | string  | yes      | Why this type exists rather than a cheaper one. Reviewed at PR time; this is where padding gets caught.       |

#### A.4.9 Validation block

| Field                        | Type         | Required | Meaning and rules                                                                                                                                                      |
|------------------------------|--------------|----------|------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| `validation.physical_bounds` | expr list    | yes      | Assertions evaluated by the property test suite over large sample counts. Never evaluated at runtime, never used to clamp.                                             |
| `validation.monotonicity`    | channel list | yes      | Channels that must be monotone non-decreasing across a run (kWh totalizers, cumulative metal loss, odometer, engine hours). Empty list is allowed and explicit.        |
| `validation.goodness_of_fit` | list         | yes      | Per-channel declared family plus the conditioning state to hold fixed, the test to run, sample count, and alpha. Section G describes the multiple-comparison handling. |
| `validation.cross_checks`    | string list  | no       | Relationships to other catalog entries (redundant measurement pairs, derived-quantity consistency).                                                                    |
| `validation.determinism`     | object       | yes      | Two tiers, per D-05. `same_platform: byte_identical` and `cross_platform: value_equivalent` with a tolerance. The cross-platform job reports observed divergence.      |
| `validation.budget`          | object       | yes      | Per-sample generator cost ceiling and payload byte ceiling, so the A4 scaling curves stay honest.                                                                      |

#### A.4.10 Provenance block

| Field                 | Type      | Required | Meaning and rules                                                                                                                                       |
|-----------------------|-----------|----------|---------------------------------------------------------------------------------------------------------------------------------------------------------|
| `provenance[].covers` | path list | yes      | The dotted field paths this row accounts for. Every numeric parameter in the entry is covered by exactly one row, and CI reports the ones that are not. |
| `provenance[].source` | source id | yes      | Resolves in `catalog/provenance/sources.yaml`, which carries publisher, title, edition or version, locator, and retrieval date.                         |
| `provenance[].tier`   | enum      | yes      | `A`, `B`, `C`, or `D`, defined in A.7. Tier D blocks `status: implemented`.                                                                             |
| `provenance[].note`   | string    | no       | Why this source and not a closer one, or what was tried and blocked.                                                                                    |

### A.5 How a new type is added

1. Copy `catalog/sensors/_schema/TEMPLATE.yaml` into the right category directory, named for the new id.
2. Fill the entry. If the physics needs a distribution family that `docs/design/variability-and-faults.md` section B does not carry, that is the one case that requires code: register the family there with its own unit tests, then name it here.
3. If the entry couples to a twin state variable that does not exist, register it in the twin state schema first. A coupling to a non-existent variable fails CI, which is deliberate: it forces the sensor and the thing it measures to be added together.
4. Add or reference a capability id in `capabilities/capabilities.yaml`, and declare at least one consuming subsystem.
5. Record every numeric parameter group in the `provenance` block, adding rows to `provenance/sources.yaml` for any source not already cited. An entry whose parameters are all tier D stays `planned`.
6. Set `phase` to the earliest roadmap phase whose subsystem consumes the type, and check that phase exists in ROADMAP.md.
7. Run `just catalog validate` locally, then `just catalog fit --id <new_id>` to run the goodness-of-fit suite for just that entry.
8. Reference the new type from a facility profile (`facility.yaml`) when it must instantiate in a shipped profile. A type can land `implemented` without being instantiated in any shipped profile, but the load test corpus must exercise it.

### A.6 What CI validates about a new type

| Check                                                                                                              | Failure mode it prevents                                   |
|--------------------------------------------------------------------------------------------------------------------|------------------------------------------------------------|
| JSON Schema validation, `additionalProperties: false`                                                              | Typo'd field names silently ignored                        |
| Filename equals `id`, directory equals `category`                                                                  | Catalog drift between filesystem and content               |
| `id` uniqueness across the whole catalog                                                                           | Two types publishing to the same metric                    |
| UCUM unit code resolves                                                                                            | Free-text units that no consumer can convert               |
| Every expression parses, and every referenced name is either a declared local or a declared coupling read          | Silent `NameError` at simulation time; hidden dependencies |
| Every coupling read resolves to a registered twin state variable with a compatible unit                            | Sensors measuring things the twin does not simulate        |
| Every `family` resolves in the distribution catalog, and its support is contained in the channel's declared bounds | A Normal on a `[0, 1]` quantity                            |
| Every `rng_streams` name parses under the stream grammar and is registered                                         | An unregistered stream, which breaks reproducibility       |
| Every `failure_modes[].catalog_id` and every `device_faults` id resolves in the fault catalog                      | A failure mode with no injector, so it cannot be tested    |
| Every `detectable_by` id resolves to a registered detector                                                         | A failure mode nobody is responsible for catching          |
| `pf_interval_hours` is present and `expected_mttd_hours` does not exceed it                                        | A detection budget that admits failure before detection    |
| `capability.unlocks` non-empty, resolves, and each capability has at least one declaring consumer                  | Orphan sensors and orphan capabilities                     |
| `phase` resolves to a phase in ROADMAP.md                                                                          | A type scheduled into a phase that does not exist          |
| Every numeric parameter group is covered by exactly one `provenance` row                                           | A number with no source, which is a claim nobody can check |
| No `implemented` entry carries a tier-D provenance row                                                             | Unverified physics shipping as fact                        |
| Topic template renders and is unique across all instantiated bindings in all shipped facility profiles             | Two devices writing the same UNS address                   |
| Sparkplug datatype matches the golden table for the entry's `channel_shape`                                        | A vector declared as a scalar Float                        |
| Goodness-of-fit suite passes for the entry                                                                         | The generator does not produce what the entry claims       |
| Physical-bounds property suite passes at the declared sample count                                                 | Wrong distribution family chosen                           |
| Stream hash identical across two runs at the same seed on the same platform                                        | Hidden global RNG state                                    |
| Generator cost and payload size within declared budget                                                             | A type that quietly breaks the scaling curve               |
| Additive-only diff against the previous release within a major schema version                                      | Breaking downstream historian schemas                      |

### A.7 Parameter provenance and evidence tiers

D-11 rules that a validation gate names a specific external published reference, that this repository is never a reference for itself, and that a statistic with no valid external reference is recorded as an open question rather than as a passing gate. A catalog of eighty types is several thousand numbers, so that ruling needs machinery rather than good intentions.

Every numeric parameter belongs to exactly one `provenance` row, and every row carries a tier.

| Tier | Meaning                                                                                    | May an `implemented` entry carry it | How it reads in the entry                       |
|------|--------------------------------------------------------------------------------------------|-------------------------------------|-------------------------------------------------|
| A    | Primary text retrieved and quotable, or arithmetic from stated relations and stated inputs | Yes                                 | Plainly, with the source id                     |
| B    | Two independent secondary sources agree                                                    | Yes                                 | Plainly, with both source ids                   |
| C    | One secondary source, or a named standard whose body could not be retrieved                | Yes                                 | With the source named in the text, never bare   |
| D    | Inferred, recalled, or plausible with no source                                            | No                                  | Blocks `implemented`; the entry stays `planned` |

Three consequences follow, and they are the point of the mechanism.

A named standard whose text is paywalled is tier C, not tier A. The entry names the standard, records what the retrieval returned in the source row, and does not reproduce numbers from it. The ISO 20816-3 vibration severity zones are the clearest case: this repository names the standard as the authority for the zone boundaries and reads the values from the purchased document at implementation time, because a boundary recalled rather than read is exactly the failure this rule exists to stop.

Arithmetic counts as tier A when the relation and its inputs are both stated in the entry. The bearing defect multipliers in A.2 are the model: the relations and the geometry are written down, so a reader recomputes 3.585 rather than trusting it. That is why the entry stores the geometry and derives the multipliers instead of storing the multipliers.

A tier-D parameter is not deleted. It is a `planned` entry with an open question attached, which is what rule 1 of the project means by sequencing rather than cutting. Section I carries the standing open question for the parameter backlog.

`sources.yaml` rows have this shape.

```yaml
- id: SRC-CFR-47-15-247
  publisher: "United States Government Publishing Office"
  title: "47 CFR 15.247, Operation within the bands 902-928 MHz, 2400-2483.5 MHz, and 5725-5850 MHz"
  edition: "current as published on eCFR"
  locator: "https://www.ecfr.gov/current/title-47/part-15/section-15.247"
  retrieved: "2026-08-09"
  http_status: 200
  tier: A
- id: SRC-ISO-20816-3
  publisher: "International Organization for Standardization"
  title: "ISO 20816-3, Mechanical vibration, measurement and evaluation of machine vibration, part 3"
  edition: "cited by designation; the body was not retrieved"
  locator: "https://www.iso.org/standard/50611.html"
  retrieved: "2026-08-09"
  http_status: 403
  tier: C
  note: "Standards body blocked automated retrieval. Zone values are read from the purchased document."
```

`http_status` is a required field. A source row that claims retrieval without recording what the server returned is the paper trail equivalent of an untested assertion, and `test_every_source_records_retrieval` fails the build on it.

---

## B. The implemented type table

80 types across the eight categories. Column meanings: the signal model column summarizes baseline, noise, drift, and coupling; the primary failure modes column lists the class-specific ones on top of the inherited universal set; the capability column names what would be impossible without this type.

Numbers in these cells are summaries of the parameters in the entries, and they carry the tier of the entry's `provenance` row (A.7). Where a cell names a standard, this section is naming the authority for a value and not reproducing the value.

### B.1 Industrial equipment (14 types) - feeds predictive maintenance

| #  | id                          | Measures                                                                  | Units                      | Signal model                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                              | Primary failure modes                                                                                                                                                                                                 | Twin subsystem                                                           | Capability unlocked                                                                                                              |
|----|-----------------------------|---------------------------------------------------------------------------|----------------------------|---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|-----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|--------------------------------------------------------------------------|----------------------------------------------------------------------------------------------------------------------------------|
| 1  | `eq.vib.velocity_rms`       | Broadband vibration severity, 10 Hz to 1 kHz                              | mm/s                       | Baseline scales with shaft speed squared and load; lognormal multiplicative noise (strictly positive amplitude); OU drift on mount preload; couples to `bearing.*_wear`, `motor.load_fraction`, `mount.looseness`. ISO 20816 zone boundaries A/B/C/D come from config, not code                                                                                                                                                                                                                                           | Mount looseness (raises broadband only), sensor resonance at the mount, cable microphonics, transverse sensitivity error                                                                                              | `conveyor_drive`, `palletizer_cell`, `asrs_crane`, `factory_mixer_drive` | ISO-referenced severity zones; the top-level PdM alarm limit                                                                     |
| 2  | `eq.vib.band_spectrum`      | Order-tracked band energies at 1x, 2x, 3x, BPFO, BPFI, BSF, FTF, residual | mm/s per band              | Defect band centers are computed from the bearing geometry by the relations written out in A.2, so a 9-ball 6205 geometry yields 3.585x, 5.415x, 2.357x, and 0.398x shaft rate as recomputable arithmetic rather than as recalled constants; band amplitude follows the four-stage bearing progression, so defect lines rise before broadband does and then collapse into a raised noise floor at stage 4; `ar1` noise floor; Arrhenius sensitivity ageing                                                                | Speed-reference loss (bands decohere and the machine looks healthier), mount looseness (broadband up, defect bands flat), band aliasing at VFD speed changes                                                          | `conveyor_drive`, `palletizer_cell`, `asrs_crane`                        | Bearing defect **localization** (outer vs inner vs element vs cage), which is what makes a time-to-threshold estimate defensible |
| 3  | `eq.vib.envelope_gse`       | Demodulated envelope acceleration in the bearing resonance band           | gSE                        | Band-pass 500 Hz to 10 kHz, rectify, low-pass, then FFT of the envelope. Detects stage-2 damage roughly 10x earlier than velocity spectrum. Gamma-distributed hit amplitude; hits arrive as a Hawkes process once a spall exists                                                                                                                                                                                                                                                                                          | Wrong demodulation band chosen for the machine, resonance shift after a rebuild, envelope saturation at high crest factor                                                                                             | `conveyor_drive`, `asrs_crane`                                           | Early bearing detection lead time; the difference between a 9-day warning and a 9-hour one                                       |
| 4  | `eq.accel.triaxial_g`       | Peak and RMS acceleration, three axes, with shock capture                 | g                          | MEMS accelerometer with declared bias instability (Allan variance floor), temperature-dependent bias, vibration rectification error; shock events drawn from a generalized Pareto tail that is not truncated                                                                                                                                                                                                                                                                                                              | Bias instability walk, axis swap on remount, saturation on hard impact, self-test failure                                                                                                                             | `agv_amr_fleet`, `palletizer_cell`, `asrs_crane`                         | AMR collision and hard-stop detection; palletizer jam impact signature                                                           |
| 5  | `eq.strain.bridge_ue`       | Mechanical strain on a structural or drive member                         | microstrain                | Full Wheatstone bridge, gauge factor 2.0, output in mV/V. Apparent strain from thermal output of a few microstrain per degC when the gauge is not matched to the substrate, so the reading is meaningless without the co-located temperature channel; adhesive creep as a slow OU drift                                                                                                                                                                                                                                   | Thermal output error (mistaken for real load), adhesive creep, moisture ingress lowering insulation resistance, lead-wire desensitisation                                                                             | `palletizer_cell`, `asrs_crane`, `conveyor_drive`                        | Load-path verification on the palletizer arm; overload event capture                                                             |
| 6  | `eq.load.shear_beam_kg`     | Force or weight at an equipment mount                                     | kg                         | Shear beam cell of an OIML R60 accuracy class, which is the standard that defines the class and supplies the temperature-effect and creep limits the entry parameterizes. The consequence the model reproduces: a zero temperature coefficient expressed as a fraction of rated output means a large-capacity cell wanders by a visible mass over a diurnal swing with no load change at all, and creep under a sustained load moves the reading in the same direction over tens of minutes; hysteresis on unload         | Temperature-coefficient drift, creep under sustained load, permanent zero shift after overload, mechanical shunt (something touching the platform)                                                                    | `palletizer_cell`, `conveyor_drive`                                      | Pallet mass verification against the ASN; overload protection                                                                    |
| 7  | `eq.torque.rotary_nm`       | Shaft torque on a driven axis                                             | N.m                        | Rotating strain-gauge transducer with telemetry link; baseline torque tracks load fraction and adds a per-revolution ripple from gear mesh; lognormal noise; slip-ring or inductive coupling adds occasional dropouts                                                                                                                                                                                                                                                                                                     | Slip-ring wear (intermittent dropouts), zero drift with temperature, telemetry link loss, mechanical resonance in the coupling                                                                                        | `palletizer_cell`, `asrs_crane`, `factory_mixer_drive`                   | Mechanical power computed independently of electrical power, which turns motor efficiency into a measured quantity               |
| 8  | `eq.encoder.quadrature_rpm` | Rotational speed and position                                             | rpm, counts                | 1024 PPR incremental quadrature with index; speed from counts per interval so resolution degrades at low speed; coupling slip appears as a slowly accumulating position error against the index pulse                                                                                                                                                                                                                                                                                                                     | Missed counts from VFD-induced EMI, index pulse loss, coupling slip (accumulating error), marginal signal at high speed, direction inversion after rewiring                                                           | `conveyor_drive`, `asrs_crane`, `agv_amr_fleet`                          | The speed reference every order-tracked vibration band depends on; belt-slip detection when paired with belt speed               |
| 9  | `eq.temp.thermocouple_k`    | Surface or process temperature, wide range                                | degC                       | Type K, with the Seebeck coefficient taken from the NIST ITS-90 thermocouple reference functions rather than stated here, because a coefficient recalled instead of read is the error this catalog's provenance rule exists to stop. The first-order lag is the load-bearing part: an exposed junction settles in seconds and a grounded sheath in tens of seconds, so a step in process temperature is never a step in the reading; cold-junction compensation error appears as a bias correlated with enclosure ambient | Cold-junction compensation error (ambient-correlated bias, the classic), open circuit driving upscale burnout, wrong TC type wired, extension-wire polarity reversal, loss of thermal contact lengthening tau         | `conveyor_drive`, `factory_oven`, `factory_mixer_drive`                  | Motor and process surface temperature trending; the tau makes lag-compensated trend estimation a real problem worth solving      |
| 10 | `eq.temp.rtd_pt100`         | Precision temperature, narrow range                                       | degC                       | 4-wire Pt100 evaluated by the Callendar-Van Dusen relation, with the temperature coefficient and the polynomial constants taken from IEC 60751, which is the standard that defines them. Self-heating is a real error at practical excitation currents in still air, and drift is far lower than a thermocouple's, which is why this is the reference in a Gage R and R against the thermocouple                                                                                                                          | Lead-resistance error in 3-wire mode, self-heating, insulation resistance fall in high humidity, element strain after thermal cycling                                                                                 | `conveyor_drive`, `factory_reactor`, `env_reference`                     | The reference standard in the measurement system analysis; the temperature source for every temperature-compensated channel      |
| 11 | `eq.acoustic.ae_hits`       | Acoustic emission hit rate and absolute energy                            | hits/s, dB_AE              | Two regimes as a mixture: continuous emission from friction and leakage raises the RMS floor, burst emission from crack initiation and propagation arrives as a self-exciting Hawkes process. Kaiser effect modeled: emissions on reload are suppressed until the previous peak load is exceeded                                                                                                                                                                                                                          | Sensor couplant dry-out (silent sensitivity loss), background noise from adjacent machinery, threshold set wrong so hits are all noise or all missed, waveguide contact loss                                          | `asrs_crane`, `palletizer_cell`, `structural_rack`                       | Crack initiation detected before any dimensional change exists to measure; the earliest signal in the PdM stack                  |
| 12 | `eq.oil.condition`          | Lubricant dielectric constant, water activity, ferrous debris             | rel. permittivity, aw, ppm | Dielectric shifts with oxidation and contamination; **water activity is bounded 0 to 1 so it is drawn from a Beta**, never a clipped Normal; ferrous debris is an over-dispersed count drawn from a negative binomial, coded to ISO 4406 bins; couples to `bearing.*_wear` and to oil temperature                                                                                                                                                                                                                         | Sensor cell coating, water activity saturating during a washdown (real, not a fault), debris sensor magnetic saturation, sampling port drawing from a dead leg                                                        | `conveyor_drive`, `asrs_crane`, `factory_mixer_drive`                    | Lubrication-cause attribution: separates "the bearing is failing" from "the bearing is failing because the oil has water in it"  |
| 13 | `eq.motor.current_mcsa`     | Motor phase current and sideband ratio                                    | A, dB                      | RMS current tracks load; the diagnostic is the **sideband structure**: broken rotor bars produce sidebands at `(1 +/- 2s)f_line` where s is slip, eccentricity at `f_line +/- k*f_rotor`, bearing defects modulate at the defect frequencies. Healthy sideband ratio below -50 dB, degraded -45 to -35 dB. VFD carrier adds harmonics that must be excluded from the analysis band                                                                                                                                        | CT saturation on inrush, phase mis-assignment on install, VFD carrier bleeding into the analysis band, sideband masking at light load (below about 40 percent load MCSA is not diagnostic, which is itself a finding) | `conveyor_drive`, `palletizer_cell`, `agv_amr_fleet`                     | Non-intrusive rotor and eccentricity diagnosis; the energy-per-pallet KPI (E7) also reads this channel                           |
| 14 | `eq.motor.winding_temp`     | Stator winding temperature                                                | degC                       | Embedded RTD in the winding; thermal model is a first-order lag on I-squared-R heating with a time constant of 15 to 45 minutes for a fan-cooled frame, so overload shows in current minutes before it shows in temperature; ambient offset couples to `env.temp.ambient`                                                                                                                                                                                                                                                 | Thermal contact loss (reads ambient, looks fine), open winding RTD, insulation class exceeded without an alarm because the trip point was set for a different frame                                                   | `conveyor_drive`, `palletizer_cell`                                      | Insulation-life consumption estimate; the thermal constraint in every throughput what-if that pushes line speed                  |

### B.2 Environmental and facility (7 types) - feeds facility health and worker comfort

| #  | id                     | Measures                                          | Units                 | Signal model                                                                                                                                                                                                                                                                                                                                                                                                                                    | Primary failure modes                                                                                                                                                                      | Twin subsystem                                        | Capability unlocked                                                                                                                       |
|----|------------------------|---------------------------------------------------|-----------------------|-------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|--------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|-------------------------------------------------------|-------------------------------------------------------------------------------------------------------------------------------------------|
| 15 | `env.temp.ambient`     | Zone dry-bulb air temperature                     | degC                  | Diurnal profile plus a seasonal profile from the shared weather state (E40), modified by dock door open events (an open door pulls the zone toward outside air with a time constant set by zone volume and infiltration rate) and by HVAC control cycling; Gaussian noise plus pink drift                                                                                                                                                       | Solar loading on a badly sited sensor, self-heating in an enclosure, stratification (a sensor at 8 m reads nothing like the pick face), sensor placed in the HVAC discharge                | `facility_zone`, `hvac`                               | Zone thermal map; the ambient reference for every temperature-compensated channel; heat-stress comfort findings when paired with humidity |
| 16 | `env.rh.relative_pct`  | Relative humidity                                 | percent               | **Bounded 0 to 100, so generated from a Beta scaled to the range**, never a clipped Normal. Inversely coupled to zone temperature at constant absolute humidity; dock door events inject outside absolute humidity                                                                                                                                                                                                                              | Capacitive polymer sensor saturation hysteresis after condensation (reads high for hours), contamination drift, filter cap clogged so the response time lengthens by an order of magnitude | `facility_zone`, `hvac`                               | Condensation risk on cold inbound product; corrugated strength derating; the comfort index input                                          |
| 17 | `env.dewpoint.derived` | Dew point temperature                             | degC                  | **Derived channel**, computed from the co-located temperature and humidity pair via the Magnus formula. Carries the schema's derived-entry form: no independent noise, and error propagated analytically from its two sources. Physical bound `dewpoint <= ambient_temp` is a property-test assertion                                                                                                                                           | Inherits both parent failure modes and amplifies them: a 3 percent RH error near saturation moves dew point by roughly 0.5 degC, and a stuck parent silently freezes the derived channel   | `facility_zone`, `hvac`, `cold_chain`                 | Condensation prediction on cold-chain product moved into a warm dock, which is where cold-chain damage actually happens                   |
| 18 | `env.co2.ndir_ppm`     | Carbon dioxide concentration                      | ppm                   | NDIR. The outdoor baseline tracks the NOAA Global Monitoring Laboratory global annual mean, which was 425.62 ppm for 2025, so a hardcoded 400 ppm would be a decade out of date and would bias every ventilation finding low. Indoor concentration rises with occupancy at a configured per-worker generation rate and falls with ventilation rate; the rate couples to the roster from the HR layer, so shift changes are visible in the trace | Automatic baseline calibration drift when the space is never unoccupied (the classic NDIR failure in a 24-hour operation), lamp ageing, pressure sensitivity at altitude                   | `facility_zone`, `hvac`                               | Ventilation adequacy and cognitive-performance findings; an independent occupancy estimate that cross-checks the roster                   |
| 19 | `env.pm.optical_ugm3`  | Particulate mass concentration, PM2.5 and PM10    | ug/m3                 | Optical particle counter. Counts are **Poisson at the detector**, converted to mass by an assumed density and size distribution, which is exactly where the accuracy goes; forklift traffic and dock door events drive spikes; humidity above about 75 percent causes hygroscopic growth that inflates the optical reading                                                                                                                      | Hygroscopic overestimate in high humidity, optical chamber fouling, fan degradation changing the sample flow rate, size-bin miscalibration                                                 | `facility_zone`, `hvac`                               | Air-quality worker comfort findings; a leading indicator for optical sensor fouling elsewhere in the building                             |
| 20 | `env.leak.water_rope`  | Water presence and distance along a sensing cable | boolean, m            | Discrete state machine with a distance-to-leak measurement from cable resistance. Onset is a rare Poisson event coupled to roof load, rainfall from the weather state, and sprinkler system state                                                                                                                                                                                                                                               | Conductive dust bridging the conductors (false positive), cable damage reading as a permanent leak, dried residue leaving the alarm latched, distance calibration off after a cable splice | `facility_zone`, `structural_roof`                    | Water intrusion findings tied to the structural layer; product-damage blast radius through lot genealogy                                  |
| 21 | `env.thermal.ir_array` | Low-resolution thermal image                      | degC per pixel, 32x24 | Microbolometer array. Publishes max, mean, and a per-pixel matrix; scene temperature couples to equipment surface temperatures and to ambient. Emissivity is the dominant error: a shiny bus bar reads far below its true temperature, so the entry carries a per-target emissivity constant                                                                                                                                                    | Emissivity error (systematic and invisible), lens contamination, ambient drift without shutter calibration, reflected apparent temperature from a nearby hot source                        | `electrical_panel`, `conveyor_drive`, `facility_zone` | Non-contact electrical connection hot-spot detection; a thermal cross-check on the contact temperature sensors                            |

### B.3 Warehouse and logistics (15 types) - feeds the DC flows

| #  | id                              | Measures                                                     | Units        | Signal model                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                              | Primary failure modes                                                                                                                                                                                                                                               | Twin subsystem                                       | Capability unlocked                                                                                                                                          |
|----|---------------------------------|--------------------------------------------------------------|--------------|---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|------------------------------------------------------|--------------------------------------------------------------------------------------------------------------------------------------------------------------|
| 22 | `whs.rfid.portal_read`          | UHF RFID tag read events at a fixed portal                   | event, dBm   | Probabilistic rather than deterministic. Per-tag, per-inventory-round read probability is the product of orientation (a dipole pattern, so `cos^2` alignment with polarization match), range (forward-link-limited Friis against tag sensitivity), material detune factor per material class, and slot-collision loss that falls roughly as `1/N` in tag population. Reads over a pass are a bounded count over `rounds = dwell / round_time`, where dwell is portal depth divided by pallet speed, so slowing the conveyor raises the read rate. RSSI is Rician-faded near the portal and Rayleigh in a metal-rich aisle, and 47 CFR 15.247 caps the forward link at 1 W conducted with up to 6 dBi of antenna gain, which is the 36 dBm EIRP ceiling the entry enforces | Antenna VSWR rise on one port (read rate falls on one port while siblings hold), cross-read from the adjacent dock (a false positive, not a miss), tag detune by product, VFD RF interference, reader thermal throttling, duplicate reads from multipath            | `receiving_portal`, `shipping_portal`, `cross_dock`  | Pallet-level identity and the whole genealogy graph; the read-rate control chart per portal; RF physics what-ifs (E46)                                       |
| 23 | `whs.rfid.handheld_read`        | Handheld reader cycle-count reads                            | event, dBm   | Same physical model with operator-controlled geometry: dwell and angle are drawn from operator-specific distributions, and a fatigued operator (from the ergonomics layer) sweeps faster and reads less. This is the **operator variance term** that makes a Gage R&R meaningful                                                                                                                                                                                                                                                                                                                                                                                                                                                                                          | Operator technique variance, battery-driven power reduction as the pack depletes, antenna damage from drops, trigger discipline (a partial sweep counted as complete)                                                                                               | `cycle_count`, `inventory_control`                   | Reproducibility (operator-to-operator) in the Gage R&R against the fixed portal; inventory record accuracy measurement                                       |
| 24 | `whs.smartshelf.rfid_inventory` | Continuous shelf-level tag census                            | count, event | A near-field or low-power shelf antenna running a continuous inventory; the census is a Binomial draw per tag per cycle, and tags at the shelf edge or behind metal are systematically under-read, producing a persistent negative bias rather than random error                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                          | Persistent blind spot from a shelf reorganisation, neighboring shelf cross-read inflating the count, antenna coupling change when the shelf is fully loaded                                                                                                         | `pick_face`, `inventory_control`                     | Real-time on-hand per pick face; the book-versus-physical accuracy KPI the finance layer consumes                                                            |
| 25 | `whs.barcode.scan_event`        | 1D and 2D symbology scan events with no-read tracking        | event        | Read success is Bernoulli per presentation with probability driven by print contrast, label damage, angle, and motion blur at conveyor speed; a laser 1D scanner and a 2D imager have different sensitivity profiles, carried as a `symbology` dimension. **No-reads are counted, not silently dropped**, because the no-read rate is the KPI                                                                                                                                                                                                                                                                                                                                                                                                                             | Lens fouling reducing contrast margin, ambient light saturation near a dock door, label print quality degradation from a failing printer (an upstream cause visible downstream), retro-reflector misalignment, decode of a wrong-but-valid check-digit symbol       | `receiving`, `pick_pack`, `sortation`                | The scan-step compliance audit the CV channel cross-checks; label print quality as a supplier scorecard input                                                |
| 26 | `whs.weight.shelf_load`         | Distributed load on a shelf or flow rack                     | kg           | Array of four cells summed; the sum is accurate but the **individual cell readings reveal load position**, and an off-center load causes corner-load error if the shelf is not properly shimmed. Temperature drift as in the industrial load cell entry, plus creep under a load that sits for weeks                                                                                                                                                                                                                                                                                                                                                                                                                                                                      | Corner-load error from an unshimmed shelf, creep under long-dwell inventory, a cell going open-circuit so the sum silently drops by roughly a quarter, mechanical shunt from a carton wedged against the frame                                                      | `pick_face`, `inventory_control`                     | Weight-based unit count for small parts; a physical cross-check on the RFID census                                                                           |
| 27 | `whs.weight.pallet_scale`       | Pallet gross weight on the conveyor                          | kg           | In-motion weighing: the reading is a filtered average over the time the pallet is fully on the scale deck, so it degrades as speed rises and is invalid if the pallet spans the deck edge. Belt vibration adds noise that the filter length trades against throughput                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                     | Partial-pallet-on-deck reading (invalid, must be rejected not published), vibration coupling from the adjacent drive, zero drift with temperature, debris on the deck offsetting zero                                                                               | `conveyor_transport`, `receiving`                    | Received weight versus ASN expected weight reconciliation; short-ship and over-ship detection at the pallet level                                            |
| 28 | `whs.weight.dock_scale`         | Vehicle or pallet weight at the dock                         | kg           | Static or in-motion floor scale with a much larger capacity and coarser resolution; legal-for-trade class means the quantisation is real and visible in the data (a 30000 kg scale with 10 kg divisions)                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                  | Quantisation mistaken for stability, deck contamination, load cell moisture ingress at a wet dock, unlevel deck after a forklift strike                                                                                                                             | `dock_door`, `yard`                                  | Inbound and outbound weight reconciliation; trailer cube-versus-weight utilization                                                                           |
| 29 | `whs.uwb.tag_position`          | Real-time position of AMRs, forklifts, and high-value assets | m (x, y, z)  | UWB time-difference-of-arrival across anchors. Accuracy 10 to 30 cm in clear line of sight; **non-line-of-sight adds a strictly positive range bias drawn from an exponential**, never a symmetric error, because a blocked path is always longer; geometric dilution of precision from anchor placement is computed from the actual anchor geometry in `facility.yaml`, so a badly placed anchor set produces visibly worse positions                                                                                                                                                                                                                                                                                                                                    | NLOS bias in dense racking, anchor clock sync loss (positions shear in one direction), anchor obstruction after a rack reconfiguration, tag battery depletion lowering the update rate                                                                              | `agv_amr_fleet`, `worker_tracking`, `asset_tracking` | Congestion mapping and AMR traffic analysis; worker-to-AMR proximity for the safety layer; travel-distance measurement for the slotting optimizer            |
| 30 | `whs.ble.beacon_rssi`           | Zone-level presence of low-cost tagged assets                | dBm          | Log-distance path loss `RSSI = A - 10 n log10(d)` with `n` between 2.0 and 3.5 indoors, plus log-normal shadowing of 4 to 8 dB standard deviation. **The honest consequence is that distance from RSSI is unusable and BLE gives zone presence only**, which is why the catalog carries both BLE and UWB rather than pretending one covers both jobs                                                                                                                                                                                                                                                                                                                                                                                                                      | Shadowing from a human body between tag and receiver, battery depletion lowering advertisement rate, 2.4 GHz contention with the Wi-Fi network, beacon MAC randomization breaking identity                                                                          | `asset_tracking`, `tote_tracking`                    | Cheap coverage of the tote and tool population where centimetre accuracy is not worth the anchor cost; the cost-versus-accuracy what-if against UWB          |
| 31 | `whs.door.dock_state`           | Dock door position and travel time                           | state, s     | State machine over closed, opening, open, closing, obstructed. **Travel time is a lognormal duration, and its slow increase is the maintenance signal**: a door that took 11 s new and takes 17 s now has a spring or chain problem. Couples to the inbound and outbound schedule                                                                                                                                                                                                                                                                                                                                                                                                                                                                                         | Limit switch drift (door reports closed while a gap remains, which is a thermal loss and a security finding), obstruction detection failure, chain stretch lengthening travel time, control relay chatter                                                           | `dock_door`, `yard`                                  | Dock utilization and door contention between inbound and outbound; the thermal load event that drives cold-chain and HVAC findings                           |
| 32 | `whs.conveyor.speed_mps`        | Belt surface speed                                           | m/s          | Tach roller on the belt surface, read against the drive encoder. **The diagnostic is the divergence**: motor speed rising while belt speed holds is belt slip, and belt speed drifting slowly downward at constant motor speed is belt stretch. Small Gaussian noise on a smooth setpoint-tracking baseline                                                                                                                                                                                                                                                                                                                                                                                                                                                               | Tach roller slip on a dusty belt, roller bearing seizure (reads zero while the belt runs), encoder EMI, roller wear changing the circumference calibration                                                                                                          | `conveyor_transport`, `sortation`                    | Belt slip detection independent of the motor; the throughput totalizer when integrated with belt load; the dwell time every RFID read probability depends on |
| 33 | `whs.conveyor.load_kgm`         | Carried load per meter of belt                               | kg/m         | Weigh idler under the carry side. Integrated with belt speed to produce a mass throughput totalizer, which is **monotone non-decreasing and property-tested as such**; material buildup on the idler produces a slow positive zero offset that inflates every subsequent total                                                                                                                                                                                                                                                                                                                                                                                                                                                                                            | Idler buildup inflating zero, idler bearing drag adding a load-dependent error, belt tension change altering the weighing geometry, splice passing over the idler causing a periodic spike                                                                          | `conveyor_transport`                                 | Mass throughput independent of unit counts; drive torque demand for the energy KPI                                                                           |
| 34 | `whs.ptl.confirm_event`         | Pick-to-light confirmation events with response time         | event, ms    | Response time is a **lognormal duration** whose median shifts with operator fatigue from the ergonomics layer and with training tenure from the HR layer, so a new hire's response distribution is visibly different and converges along a learning curve                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                 | Button contact wear (double confirms), light module failure (operator picks from an unlit location), confirm-before-pick gaming (a short response time below physical possibility, which is itself the detection), network latency inflating measured response time | `pick_face`, `pick_pack`                             | Operator cycle-time measurement at the task level; the learning curve the HR layer needs; confirm-gaming as an SOP violation finding                         |
| 35 | `whs.photoeye.presence`         | Through-beam occupancy and gap between units                 | boolean, mm  | Response time 1 to 5 ms; the derived quantity is the **gap between consecutive units**, which is what singulation and divert logic depend on. Occupancy dwell exceeding a threshold is a jam                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                              | Lens fouling reducing excess gain until it fails at the first dusty week, alignment drift, ambient IR from sun through an open dock door, reflection from a shiny carton faking a clear beam                                                                        | `conveyor_transport`, `sortation`                    | Jam detection and jam localization; singulation gap measurement that the sorter divert window depends on                                                     |
| 36 | `whs.trailer.presence`          | Trailer at the door, and trailer identity where tagged       | boolean, id  | Ultrasonic ranging to the trailer face plus an inductive loop for metal presence; two independent technologies deliberately, so a disagreement is a diagnosable finding rather than an ambiguity                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                          | Ultrasonic false echo from the dock leveller, loop detuning after a floor repair, snow or ice absorbing the ultrasonic pulse, a trailer parked short so ultrasonic sees it and the loop does not                                                                    | `dock_door`, `yard`                                  | Yard occupancy and detention time measurement; the dock-availability constraint in the scheduling optimizer                                                  |

### B.4 Transportation and fleet (12 types) - enables cold-chain integrity

| #  | id                        | Measures                                                      | Units          | Signal model                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                          | Primary failure modes                                                                                                                                                                                                                                                                                     | Twin subsystem                                | Capability unlocked                                                                                                                                                  |
|----|---------------------------|---------------------------------------------------------------|----------------|-------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|-----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|-----------------------------------------------|----------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| 37 | `veh.gnss.position`       | Vehicle position, speed, and fix quality                      | deg, m/s, HDOP | Position error is a function of satellite geometry (HDOP) plus a multipath term that rises in urban canyon and at the dock; **speed from Doppler is far more accurate than differentiated position**, so the two are separate channels with different error models; a stationary receiver exhibits a bounded random walk of 1 to 3 m, which naive geofencing reads as movement                                                                                                                                                                                                                        | Multipath at the dock, HDOP spike under a bridge or canopy, cold-start time-to-first-fix around 30 s after a power cycle, position hold snapping (a firmware feature that hides real slow movement), jamming                                                                                              | `transport_network`, `yard`                   | Lane transit time measurement; geofence arrival and departure events; the location half of every cold-chain excursion record                                         |
| 38 | `veh.imu.6dof`            | Vehicle acceleration and angular rate                         | g, deg/s       | MEMS with declared bias instability from an Allan variance floor (roughly 0.05 mg accel, 10 deg/hr gyro for automotive grade), temperature-dependent bias, and vibration rectification error that biases the accelerometer in a way the gyro does not; harsh-event thresholds around 0.3 g are config, not code                                                                                                                                                                                                                                                                                       | Bias instability random walk, mounting angle error making every event read on the wrong axis, saturation on a real hard brake, temperature bias shift on a cold start                                                                                                                                     | `transport_network`, `agv_amr_fleet`          | Harsh-driving events for the carrier scorecard; road shock context that explains a cargo shock event                                                                 |
| 39 | `veh.fuel.level_pct`      | Fuel remaining                                                | percent        | **Bounded, so Beta-distributed around the true level.** Raw signal is dominated by slosh, so the honest model is a heavily filtered value with a several-minute effective time constant; refuel events are step increases, and theft is a step decrease while stationary, which is precisely the signature the fraud check looks for                                                                                                                                                                                                                                                                  | Stuck float giving a plateau, tank geometry non-linearity near full and empty, slosh filter masking a genuine fast drop, sender resistance drift                                                                                                                                                          | `transport_network`                           | Fuel economy per lane and the carrier cost model; fuel theft detection                                                                                               |
| 40 | `veh.tire.tpms`           | Tire pressure and temperature per wheel                       | kPa, degC      | Pressure and temperature are physically coupled through Gay-Lussac's law at fixed volume, so the sensitivity is the absolute pressure divided by the absolute temperature and is not a single constant: a passenger tire near 240 kPa gauge moves about 1.2 kPa per degC and a heavy-truck tire near 700 kPa gauge moves about 2.7 kPa per degC. A cold-morning reading is legitimately low and alarming on it is the classic false positive. The catalog carries the temperature-normalized pressure as the alarmable quantity. A slow leak is a linear ramp, a puncture is a fast exponential decay | Sensor battery end-of-life (typically 5 to 7 years, then silent), wheel position mis-learn after a tire rotation, RF dropout at speed, valve stem sensor corrosion                                                                                                                                        | `transport_network`                           | Preventable roadside failure avoidance; the fuel economy penalty of underinflation in the transport cost model                                                       |
| 41 | `veh.engine.coolant_temp` | Engine coolant temperature                                    | degC           | First-order thermal lag with a warm-up ramp from cold start; thermostat opening produces a characteristic plateau then a step, and a stuck-open thermostat shows as a warm-up that never completes, which is a distinct and recognizable trace                                                                                                                                                                                                                                                                                                                                                        | Sensor in the wrong port reading a cooler point, air pocket in the cooling system causing erratic reads, thermostat stuck open (never reaches operating temperature) or closed (overheats), gauge damping hiding a real spike                                                                             | `transport_network`                           | Engine health for the fleet maintenance queue; a cause explanation for a reefer power loss on a diesel-driven unit                                                   |
| 42 | `veh.cargo.temp_probe`    | Cargo temperature at supply air, return air, and product pulp | degC           | Three deliberately different measurement points with different time constants: supply air responds in seconds, return air in minutes, and **pulp temperature in tens of minutes because product thermal mass dominates**. Door-open events drive an exponential approach toward ambient with a time constant set by insulation and load mass. Defrost cycles raise return air by several degC on a schedule, which is **not** an excursion, and discriminating the two is the whole problem                                                                                                           | Probe placed in the air stream instead of the product (reads recovery, misses the real excursion), probe pulled out of the pulp by load shift, ice buildup insulating the probe, calibration drift below zero where it matters most                                                                       | `transport_network`, `cold_chain`             | **Cold-chain integrity**: excursions become findings, traced through lot genealogy to every affected pallet, order, and customer                                     |
| 43 | `veh.cargo.humidity`      | Cargo compartment relative humidity                           | percent        | Beta-bounded as in the facility entry; couples to cargo temperature so that a cooling load approaching its dew point condenses, which is the physical mechanism behind wet-carton damage claims                                                                                                                                                                                                                                                                                                                                                                                                       | Condensation hysteresis after a door-open event, sensor saturation in a produce load, filter fouling                                                                                                                                                                                                      | `transport_network`, `cold_chain`             | Moisture-damage claims (E38); packaging integrity findings on the supplier scorecard                                                                                 |
| 44 | `veh.cargo.shock_event`   | Impact events on the load                                     | g, ms          | Triaxial shock recorder with a trigger threshold. **Peak magnitude is drawn from a generalized Pareto tail that is never truncated**, because the rare 40 g forklift strike is the event that matters and a truncated tail would erase it. Drop height is inferred from the velocity change over the pulse                                                                                                                                                                                                                                                                                            | Threshold set too high (silent misses), sensor mounted on the trailer wall instead of the load (records road input, not load impact), battery depletion mid-transit, timestamp skew placing the event on the wrong lane leg                                                                               | `transport_network`, `cold_chain`             | Damage attribution to a specific carrier and leg; cargo claims generation (E38)                                                                                      |
| 45 | `veh.cargo.tilt`          | Load tilt and roll angle                                      | deg            | **Angles come from a von Mises distribution, not a Normal**, so wraparound is handled correctly. Sustained tilt beyond a threshold indicates load shift; transient tilt correlates with cornering from the IMU, which is how a real shift is separated from a hard turn                                                                                                                                                                                                                                                                                                                               | Sensor mounted on a pallet that itself shifts, gravity vector confusion during sustained acceleration, mounting adhesive failure                                                                                                                                                                          | `transport_network`                           | Load shift detection and load-securing findings; the tip-over risk input to the safety layer                                                                         |
| 46 | `veh.reefer.unit_status`  | Refrigeration unit setpoint, mode, defrost state, run hours   | degC, state, h | State machine over cooling, heating, defrost, null-cycle, off, with dwell distributions per mode. Run hours are **monotone non-decreasing and property-tested as such**. Fuel or power draw couples to mode                                                                                                                                                                                                                                                                                                                                                                                           | Setpoint changed in transit (a human cause of an excursion, and one that only this channel can distinguish from an equipment failure), defrost stuck on, refrigerant charge loss causing longer cooling cycles and a slowly rising return air floor, controller clock drift misaligning defrost schedules | `transport_network`, `cold_chain`             | The **cause** half of a cold-chain finding: equipment failure, door event, or human setpoint change, which is the difference between a claim and a corrective action |
| 47 | `veh.door.trailer_open`   | Trailer door and seal state                                   | boolean, id    | Discrete state with a magnetic reed or hall switch, plus optional seal identity. Open events are the dominant real cause of temperature excursions, and the pairing of this channel with cargo temperature is what makes the excursion diagnosable                                                                                                                                                                                                                                                                                                                                                    | Magnet misalignment after a door repair (reads closed while open), reed switch welding, seal id transposed at a transfer point                                                                                                                                                                            | `transport_network`, `cold_chain`, `security` | Excursion cause attribution; chain-of-custody integrity for the traceability ledger (E35)                                                                            |
| 48 | `veh.telematics.gateway`  | Odometer, engine hours, idle time, fault codes                | km, h, s, code | A gateway aggregating a vehicle bus. Odometer and engine hours are **monotone non-decreasing**; idle time accumulates only when speed is zero and the engine runs; fault codes are discrete events with a code vocabulary. The gateway itself has a store-and-forward buffer, so a cellular outage produces a burst of backdated messages on reconnect, which is the correct behavior and the historian must handle it                                                                                                                                                                                | Store-and-forward replay arriving out of order, odometer rollover, clock drift on a device that has been offline for days, parameter-group misdecoding after a firmware change                                                                                                                            | `transport_network`, `fleet_registry`         | Utilization and idle-waste KPIs; the store-and-forward replay case the historian is tested against                                                                   |

### B.5 Electrical and power (10 types) - feeds energy KPIs and AMR charging physics

| #  | id                             | Measures                                               | Units          | Signal model                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                              | Primary failure modes                                                                                                                                                                                                                                                        | Twin subsystem                                        | Capability unlocked                                                                                                                                                            |
|----|--------------------------------|--------------------------------------------------------|----------------|---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|-------------------------------------------------------|--------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| 49 | `pwr.voltage.three_phase`      | Line and phase voltage RMS, per phase                  | V              | Nominal with slow supply variation plus **event-driven sags**: a large motor start pulls a dip whose depth scales with starting current and source impedance, recovering over hundreds of milliseconds. Phase imbalance is a separate derived channel because a 2 percent voltage imbalance produces roughly a 15 percent current imbalance in an induction motor, which is a real and non-obvious motor-damage mechanism                                                                                                 | PT ratio misconfigured (everything reads by a constant factor), neutral reference loss, aliasing of the sag transient by too slow a sample rate, phase rotation reversed after a panel change                                                                                | `electrical_panel`, `site_power`                      | Power quality findings; sag-induced production stops correlated to the twin's downtime record                                                                                  |
| 50 | `pwr.current.phase_ct`         | Per-phase current                                      | A              | Current transformer with a declared ratio and burden. Baseline tracks mechanical load; inrush on start is 5 to 8 times rated for a few hundred milliseconds, which **saturates a CT sized for running current**, so the recorded inrush is an underestimate and the entry says so                                                                                                                                                                                                                                         | CT saturation on inrush, ratio misconfiguration, secondary open-circuit (a genuine hazard and a hard-fail condition), phase mis-assignment on install                                                                                                                        | `electrical_panel`, `conveyor_drive`, `agv_amr_fleet` | Per-circuit load attribution; the current half of every power and power factor computation                                                                                     |
| 51 | `pwr.meter.active_power`       | Real power and cumulative energy                       | kW, kWh        | Computed from synchronized voltage and current, so it inherits both error models. **kWh is monotone non-decreasing and property-tested**; a rollback is a hard failure. Idle power is a first-class quantity because idle energy is the eighth-waste finding (E7)                                                                                                                                                                                                                                                         | Register rollover mistaken for a reset, energy accumulation gap during a device reboot (the value must resume, not restart), reversed CT giving negative power on a load, sub-metering that does not sum to the site meter                                                   | `electrical_panel`, `conveyor_drive`, `hvac`          | Energy per pallet; idle-energy waste findings; the energy delta reported alongside every what-if throughput delta                                                              |
| 52 | `pwr.meter.power_factor`       | Displacement power factor                              | ratio, -1 to 1 | **Bounded, so Beta-distributed on the magnitude with a sign channel.** The physics that matters: an induction motor at 25 percent load runs a power factor near 0.4 to 0.6 while the same motor at rated load runs near 0.85, so **an oversized conveyor motor running lightly loaded is visible as a poor power factor** and that is a real, actionable, money-saving finding                                                                                                                                            | Sign convention confusion between leading and lagging, harmonic distortion making displacement and true power factor diverge (they are different quantities and conflating them is common), measurement at too coarse an interval to see the load cycle                      | `electrical_panel`, `site_power`                      | Motor right-sizing findings; the reactive power charge in the energy cost model                                                                                                |
| 53 | `pwr.smartmeter.site_interval` | Site import energy and demand, on the utility interval | kWh, kW        | Fixed 15-minute interval aggregation with a demand peak per interval. **The peak, not the total, drives the demand charge**, so the model reproduces the fact that a single coincident start can cost more than an hour of steady running. Sub-meter sum must reconcile to the site meter within a tolerance, and the residual is the unmetered load                                                                                                                                                                      | Interval boundary misalignment against the utility clock, meter clock drift shifting the peak into the wrong interval, missing interval backfill, tariff schedule change not reflected in the cost model                                                                     | `site_power`                                          | Demand-charge optimization what-ifs (staggering AMR charging, shifting the palletizer start); the site-level energy KPI                                                        |
| 54 | `pwr.battery.soc`              | AMR pack state of charge                               | percent        | **Bounded 0 to 1, Beta-distributed around the true value.** LFP chemistry has a **flat open-circuit voltage between roughly 20 and 90 percent SOC**, which is exactly why coulomb counting is used and exactly why the estimate accumulates a random-walk integration error until a full charge resets it. Charging follows constant current to a voltage knee then constant voltage taper, so **the last 15 percent takes disproportionately long** and a fleet charging plan that assumes linear charging will be wrong | Coulomb counting integration drift between full-charge resets, current sensor offset integrating into a large SOC error over a shift, SOC jump at the reset (real, and it looks like a fault), charge acceptance derated below 5 degC and above 45 degC                      | `agv_amr_fleet`, `battery_bank`                       | **Realistic AMR charging physics**: opportunity-charge scheduling, fleet availability under a charging constraint, and the AMR count what-if that must account for charge time |
| 55 | `pwr.battery.soh`              | Pack capacity fade and internal resistance rise        | percent, mOhm  | Capacity fade as a function of equivalent full cycles and depth of discharge, with a calendar ageing term; internal resistance rise is the earlier and more sensitive indicator, and it also **reduces usable capacity at high discharge rates**, so an aged pack fails first under peak load rather than at rest                                                                                                                                                                                                         | Capacity estimate only refreshable on a full discharge cycle that operations never allows, resistance measurement confounded by temperature, cell imbalance hidden by pack-level measurement                                                                                 | `agv_amr_fleet`, `battery_bank`                       | Battery replacement scheduling and its capital cost in the AMR fleet what-if; end-of-life prediction for the CMMS queue                                                        |
| 56 | `pwr.battery.pack_temp`        | Pack cell temperature                                  | degC           | Thermal model driven by I-squared-R heating during charge and discharge with a cooling term; **charge current is derated by the BMS outside 5 to 45 degC**, so a hot pack charges more slowly, which propagates directly into fleet availability. Cell-to-cell spread is a separate channel because a widening spread is the imbalance signal                                                                                                                                                                             | Sensor on the pack case rather than a cell (under-reads the hot cell), single sensor missing the hot spot, thermal runaway precursor masked by averaging                                                                                                                     | `agv_amr_fleet`, `battery_bank`                       | Charge-rate derating in the AMR availability model; a thermal safety finding with a severity floor                                                                             |
| 57 | `pwr.ups.status`               | UPS mode, runtime remaining, self-test result          | state, min     | State machine over on-line, on-battery, bypass, fault, with dwell distributions. Runtime remaining uses a Peukert-derated capacity, so a VRLA string delivers less at high load than a linear estimate suggests, and a naive runtime readout is optimistic in exactly the situation where it matters                                                                                                                                                                                                                      | VRLA end-of-life showing as a runtime estimate that falls faster than the load explains, self-test skipped or failed silently, bypass left engaged after maintenance (no protection, and everything looks normal), battery string open circuit found only at the next outage | `it_infrastructure`, `electrical_panel`               | Ride-through capability for the OT stack during a sag; the recovery-time input to the IT and cyber operations layer                                                            |
| 58 | `pwr.meter.thd`                | Total harmonic distortion, voltage and current         | percent        | Harmonic content dominated by the VFD population; the 5th and 7th current harmonics are the characteristic six-pulse drive signature. Distortion rises as more drives run, so THD is coupled to the count of active drives, which makes it a genuine load-mix indicator rather than a static number                                                                                                                                                                                                                       | Measurement bandwidth too low to capture higher harmonics, aliasing producing phantom harmonics, single-point measurement not representative of the whole panel                                                                                                              | `electrical_panel`, `site_power`                      | Power quality findings tied to drive population; capacitor bank resonance risk when a power factor correction what-if is proposed                                              |

### B.6 Safety and compliance (8 types) - severity floor outranks throughput by definition

Every entry in this category carries a `severity_floor` on its safety-relevant failure modes, and the findings contract enforces that a safety finding cannot be ranked below a throughput finding regardless of computed impact.

| #  | id                          | Measures                                                 | Units             | Signal model                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                               | Primary failure modes                                                                                                                                                                                                                                                                            | Twin subsystem                                  | Capability unlocked                                                                                                                             |
|----|-----------------------------|----------------------------------------------------------|-------------------|----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|--------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|-------------------------------------------------|-------------------------------------------------------------------------------------------------------------------------------------------------|
| 59 | `saf.smoke.photoelectric`   | Smoke obscuration                                        | percent per m     | Photoelectric chambers respond well to smouldering smoke and poorly to fast flaming fires, which is a real and material limitation. Baseline obscuration rises slowly with dust accumulation, which is why the alarm threshold and the chamber contamination trend are separate channels                                                                                                                                                                                                                                                                                   | Dust accumulation raising the baseline until it nuisance-alarms (the dominant real failure in a DC), insect intrusion, chamber contamination sensitivity loss, alarm inhibited during a known dusty operation and never re-enabled                                                               | `fire_safety`, `facility_zone`                  | Fire detection findings; the chamber-contamination trend that predicts a nuisance alarm before it happens                                       |
| 60 | `saf.gas.lel_catalytic`     | Combustible gas concentration                            | percent LEL       | Catalytic bead sensor at the lead-acid charger bank, where hydrogen off-gasses during equalize charge; the PubChem record for hydrogen gives a lower flammable limit of 4.0 percent by volume, which is what percent-LEL is referenced to. Concentration couples to charger state, ventilation rate, and bank size. **The critical physics: catalytic beads are poisoned by silicones and sulphides, and a poisoned bead reads LOW, not high**, so the failure is silent and only bump testing finds it. That is why the entry carries a scheduled bump test as a detector | Silicone or H2S poisoning (silent sensitivity loss), flame arrestor blockage slowing response, zero drift with temperature, saturation above the measuring range reading back down through zero                                                                                                  | `battery_bank`, `facility_zone`                 | Hydrogen accumulation findings at the charge bank; a demonstration of why proof testing exists for fail-silent sensors                          |
| 61 | `saf.gas.co_electrochem`    | Carbon monoxide concentration                            | ppm               | Electrochemical cell. Baseline couples to propane forklift population and run time and inversely to ventilation. Cross-sensitivity to hydrogen is real and means the CO sensor reads high near the charging bank, which is a **cross-sensor artifact the correlation layer must learn rather than a fault**                                                                                                                                                                                                                                                                | Electrolyte dry-out ending sensor life at roughly 2 years, hydrogen cross-sensitivity false positive, baseline shift with humidity, temperature-dependent sensitivity                                                                                                                            | `facility_zone`, `fire_safety`                  | CO exposure findings; forklift fleet electrification business case                                                                              |
| 62 | `saf.estop.circuit`         | Emergency stop circuit state, dual channel               | state             | Dual-channel state machine with cross-monitoring; trip duration is a lognormal, and the reset requires guard-closed and zone-clear guards. Publishes on change with a heartbeat, because a safety input that never republishes is indistinguishable from a dead one                                                                                                                                                                                                                                                                                                        | **Welded contact stuck armed (the dangerous, silent failure)**, contact bounce producing chatter, channel discrepancy latching a fault, reset defeated by a jumper (detectable as a reset that happens faster than a human can walk to the button)                                               | `safety_system`, all machine subsystems         | Machine stop events with cause; the safety severity floor; proof-test scheduling for fail-silent safety devices                                 |
| 63 | `saf.guard.interlock`       | Machine guard door interlock and safety relay state      | state             | Coded magnetic or tongue interlock feeding a safety relay. Opening cycles couple to the twin's maintenance and jam-clearing events, so a guard opened far more often than the jam rate explains means someone is working around it                                                                                                                                                                                                                                                                                                                                         | Interlock defeated by a spare actuator taped to the switch (visible as guard-closed during a period the twin knows the machine was accessed), actuator misalignment causing intermittent faults, relay contact welding, guard opened during motion because the stop time exceeds the access time | `palletizer_cell`, `sortation`, `safety_system` | Guard defeat detection as a compliance finding; the safe-access time calculation feeding the machine layout what-if                             |
| 64 | `saf.proximity.worker_amr`  | Separation distance between a worker and the nearest AMR | m                 | Fused from the UWB tag position and the AMR's own obstacle sensing, so the two sources disagree sometimes and the disagreement is informative. **Near-miss events feed a Heinrich-pyramid ratio into the incident model**, and their arrival is a Hawkes process because near-misses cluster in place and time (a congested aisle produces bursts, not a uniform rate)                                                                                                                                                                                                     | UWB NLOS bias understating distance risk, worker without a tag (invisible to the fused estimate, which is the real gap in every deployment), AMR sensor blind spot behind the payload, latency making the reported separation stale at the moment it matters                                     | `agv_amr_fleet`, `worker_safety`                | Near-miss Pareto by location and cause; the AMR speed-versus-separation what-if with an injury-cost term                                        |
| 65 | `saf.ppe.vision_compliance` | PPE presence per detected worker                         | class, confidence | **From the CV channel on synthetic frames, and labeled as such everywhere.** Detection confidence is a bounded ratio so it is Beta-distributed; the failure modes are model failure modes rather than transducer failure modes, which is why this entry exists in the catalog: it forces the schema to represent an inference channel honestly                                                                                                                                                                                                                             | Occlusion by a pallet or a turned back, motion blur at aisle speed, class confusion (a bump cap read as a hard hat), lighting domain shift near the dock door, confidence calibration drift after a model update                                                                                 | `worker_safety`, `cv_audit`                     | PPE compliance findings citing the specific SOP clause (E8); the measured comparison between the classical CV channel and the VLM channel (E29) |
| 66 | `saf.fall.wearable`         | Worker fall detection from a wearable                    | event, g          | Free-fall detection (sustained near-zero acceleration) followed by an impact peak, then a stillness window. Each stage has its own distribution, and **the three-stage structure is what separates a fall from a dropped device**, which is the entire engineering problem in fall detection                                                                                                                                                                                                                                                                               | Dropped device false positive, sitting down hard false positive, a genuine slow slump that never reaches free fall (the false negative that matters most), battery depletion, worker not wearing the device                                                                                      | `worker_safety`                                 | Fall incidents with location from the co-located UWB tag; the TRIR-style rate the ESG report consumes                                           |

### B.7 Process and chemical (9 types) - feeds batch quality and golden-batch scoring

These attach to the upstream factory (component 6a9), specifically the continuous and batch stage feeding discrete forming.

| #  | id                               | Measures                                 | Units       | Signal model                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                     | Primary failure modes                                                                                                                                                                                                                       | Twin subsystem                                   | Capability unlocked                                                                                                                                                            |
|----|----------------------------------|------------------------------------------|-------------|----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|--------------------------------------------------|--------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| 67 | `prc.ph.glass_electrode`         | Process pH                               | pH          | Nernst response, whose ideal slope is ln(10) RT/F and evaluates to 59.16 mV per pH at 25 degC using the CODATA 2022 gas and Faraday constants, so the number is recomputable rather than recalled. **Slope degrades with electrode age**: a healthy electrode gives 95 to 102 percent of theoretical, and below about 85 percent it is finished. Temperature compensation is mandatory. **Response time lengthens as the glass membrane ages**, modeled as a first-order lag whose tau grows over the electrode life, and that slowing is measurable before the slope failure is | Slope decay (the primary ageing mode), reference junction poisoning shifting the offset, coating slowing the response, dry-out during a shutdown, calibration performed at the wrong temperature                                            | `factory_reactor`, `cip_system`                  | Batch pH profile for golden-batch scoring; electrode replacement prediction from the response-time trend rather than from a fixed calendar                                     |
| 68 | `prc.conductivity.toroidal`      | Solution conductivity                    | mS/cm       | Toroidal (inductive) sensor, so no wetted electrodes to foul. **Temperature coefficient of roughly 2 percent per degC for most aqueous solutions means uncompensated conductivity is nearly meaningless**, and the entry carries the compensation reference explicitly. Cell constant shifts if the sensor is installed too close to a pipe wall                                                                                                                                                                                                                                 | Coating changing the effective cell constant, installation too close to the wall (a systematic error present from day one), temperature compensation applied with the wrong coefficient for the solution, air bubbles in the bore           | `factory_reactor`, `cip_system`                  | CIP rinse endpoint verification; concentration tracking for the batch recipe                                                                                                   |
| 69 | `prc.viscosity.inline_vibrating` | Process viscosity                        | cP          | Vibrating-element viscometer. **Viscosity is strongly temperature dependent by an Arrhenius relation, `ln(mu) = A + B/T`**, so a reading without its temperature is not a measurement, and the golden-batch comparison uses the temperature-corrected value. Shear rate dependence for non-Newtonian product is carried as a declared model type                                                                                                                                                                                                                                 | Temperature correction using the wrong constants for the product, buildup on the vibrating element raising the apparent viscosity, flow-induced error at high line velocity, non-Newtonian shear thinning misread as a formulation change   | `factory_mixer`, `factory_reactor`               | Viscosity profile in the golden-batch score; the cure-stage endpoint that drives batch cycle time                                                                              |
| 70 | `prc.flow.coriolis`              | Mass flow and fluid density              | kg/h, kg/m3 | True mass flow, accuracy 0.1 to 0.5 percent of rate. **Zero drift with temperature is the dominant error and it matters most at low flow**, since a fixed zero offset is a growing percentage error as rate falls. Entrained air is diagnosable: **drive gain spikes and density reads low simultaneously**, and that pair of symptoms together is the signature                                                                                                                                                                                                                 | Zero drift at low flow, two-phase flow (drive gain spike plus low density), coating changing the tube stiffness, external vibration coupling at the tube resonance, mounting stress after a pipe modification                               | `factory_reactor`, `factory_mixer`               | Recipe mass balance and material yield through genealogy; the reference in a redundant-flow measurement comparison                                                             |
| 71 | `prc.flow.magnetic`              | Volumetric flow of a conductive fluid    | m3/h        | No moving parts, no pressure drop, requires conductivity above roughly 5 uS/cm so it works on water-based product and fails silently on a solvent. Electrode coating produces a slow negative drift; an empty pipe reads noise rather than zero, which is why empty-pipe detection is a separate channel                                                                                                                                                                                                                                                                         | Electrode coating (slow negative drift), empty pipe reading noise, conductivity dropping below the sensor's floor during a solvent flush, grounding ring corrosion introducing a common-mode error                                          | `factory_reactor`, `cip_system`, `utility_water` | Volumetric balance cross-check against the Coriolis mass flow, which is a genuine two-technology measurement comparison the MSA layer can run                                  |
| 72 | `prc.level.radar_fmcw`           | Vessel level, non-contact                | m           | FMCW radar. Reflected amplitude depends on the product dielectric constant, so a low-dielectric product returns a weak echo. **Agitator blades produce false echoes that must be mapped out during commissioning**, and a false-echo map that goes stale after an internals change is a real and common failure                                                                                                                                                                                                                                                                  | Agitator false echo after an internals change, condensation or product buildup on the antenna attenuating the signal, low-dielectric product losing the echo entirely, multiple-reflection ghost at exactly twice the true distance         | `factory_reactor`, `bulk_tank`                   | Vessel inventory and batch charge verification; the level reference for the redundancy comparison against ultrasonic                                                           |
| 73 | `prc.level.ultrasonic`           | Vessel or sump level, non-contact        | m           | Time of flight. The speed of sound in air follows c = 331.3 sqrt(1 + T/273.15) m/s, which differentiates to about 0.17 percent per degC near room temperature, so temperature compensation is mandatory and an uncompensated sensor drifts with the diurnal cycle in a way that looks exactly like a slow leak. Foam absorbs the pulse and produces a lost echo rather than a wrong reading, which is at least honest. There is a dead zone near the transducer                                                                                                                  | Foam absorption causing lost echo, temperature compensation missing or using the wrong reference, vapor changing the speed of sound, condensation on the transducer face, target within the blanking distance                               | `bulk_tank`, `sump`, `utility_water`             | The **second technology** in a deliberate redundant level pair; the disagreement between radar and ultrasonic on the same vessel is a first-class MSA and cross-check exercise |
| 74 | `prc.do.optical`                 | Dissolved oxygen                         | mg/L        | Luminescent lifetime measurement, which unlike a Clark cell has no flow dependence and consumes no oxygen. **The luminophore cap has a stated 12 to 24 month life and degrades gradually**, so the failure is a slow sensitivity loss rather than a step. Temperature and salinity compensation are required; solubility falls with temperature, so an uncompensated reading tracks the diurnal cycle                                                                                                                                                                            | Luminophore cap ageing (slow sensitivity loss), cap fouling by biofilm, temperature compensation missing, ambient light leakage through a damaged cap, salinity compensation using a default value                                          | `factory_reactor`, `wastewater`                  | Aerobic process control in the batch stage; an environmental discharge parameter for the ESG report (E39)                                                                      |
| 75 | `prc.corrosion.er_probe`         | Cumulative metal loss and corrosion rate | mils, mpy   | Electrical resistance probe. **The raw signal is cumulative metal loss and is monotone non-decreasing, property-tested as such**; the useful quantity is its derivative, and differentiating a noisy monotone signal is a real estimation problem that the trend layer has to solve properly rather than by first differences. The element has a finite life and must be replaced when consumed. Probe temperature affects resistance directly, so compensation is essential                                                                                                     | Element consumed (end of life, reads flat and looks like the corrosion stopped), temperature compensation error swamping the real signal, probe in a location unrepresentative of the worst corrosion, deposit on the element insulating it | `factory_piping`, `utility_water`, `wastewater`  | Asset integrity trending; the inspection-interval what-if that trades inspection cost against failure risk                                                                     |

### B.8 Structural (5 types) - facility integrity under snow load

| #  | id                       | Measures                                      | Units       | Signal model                                                                                                                                                                                                                                                                                                                                                                                                                                                     | Primary failure modes                                                                                                                                                                                                     | Twin subsystem                      | Capability unlocked                                                                                                     |
|----|--------------------------|-----------------------------------------------|-------------|------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|-------------------------------------|-------------------------------------------------------------------------------------------------------------------------|
| 76 | `str.strain.column_vw`   | Strain in a building column or primary member | microstrain | Vibrating-wire gauge: the measurement is the resonant frequency of a tensioned wire, which is why it is exceptionally stable over years and the technology of choice for structures. A built-in thermistor supplies the thermal correction, and **the uncorrected signal has a large annual thermal cycle that must be removed before any trend claim is made**                                                                                                  | Wire slack after an overload event (permanent zero shift), thermistor failure removing the correction, lead-wire damage, load path change after a facility modification making the historical baseline invalid            | `structural_frame`, `facility_zone` | Structural load trending under snow accumulation; the load path check after a rack or mezzanine change                  |
| 77 | `str.crack.displacement` | Crack width across a monitored crack          | mm          | LVDT or vibrating-wire crackmeter with sub-0.01 mm resolution. **Seasonal thermal cycling produces an annual sine of the same order as a slow real trend**, so the seasonal component must be modeled and removed before a growth rate is estimated, and doing that wrong is how facilities either panic annually or miss a real crack                                                                                                                           | Seasonal cycle mistaken for growth, anchor debonding, sensor spanning a repaired crack so it measures the repair rather than the structure, LVDT core binding                                                             | `structural_frame`                  | Crack growth rate with a confidence interval; structural findings escalated to the safety severity floor                |
| 78 | `str.load.roof_snow`     | Roof load from snow, water, and equipment     | kPa         | Load pad or a snow pillow. Load couples to the shared weather state (E40): accumulation from snowfall, densification from a freeze-thaw cycle (which **raises load without adding depth**, the mechanism behind most roof collapses), and shedding from melt. **Wind scour and drift make the load spatially non-uniform**, so a single sensor systematically under-reads a drift zone, and sensor placement at valleys and behind parapets is part of the model | Single-point measurement missing a drift zone, ice bridging the pad so load transfers around it, drain blockage adding ponded water the pad does not see, thermal expansion of the pad structure                          | `structural_roof`, `facility_zone`  | The snow-load scenario: roof capacity margin, the evacuation and snow-removal decision, and its production cost         |
| 79 | `str.tilt.rack_upright`  | Rack upright inclination                      | deg         | MEMS inclinometer with 0.01 degree resolution. Two mechanisms with different signatures: **a forklift strike produces a step change plus a co-timed shock event**, while **overload creep produces a slow monotone lean**. Separating them is the diagnostic, and it drives different corrective actions                                                                                                                                                         | Sensor mounting drift on the upright, temperature-induced apparent tilt, sensor on a beam rather than an upright measuring deflection instead of lean, a strike below the sensor position that does not register as tilt  | `structural_rack`, `storage`        | Rack damage findings; the aisle-by-aisle damage rate that drives the rack protection investment what-if                 |
| 80 | `str.impact.rack_leg`    | Impact events on a rack leg or column guard   | g, ms       | Threshold-triggered accelerometer. Arrivals are Poisson with a rate **coupled to forklift and AMR traffic density in that aisle from the UWB layer**, so a high-traffic aisle genuinely accumulates more strikes and the model reproduces that rather than assuming a uniform rate. Peak magnitude is generalized-Pareto tailed and not truncated                                                                                                                | Threshold set above the damaging impact level (silent misses), sensor knocked off by the impact it was recording, adjacent rack coupling registering a neighbor's strike, battery depletion in a location nobody inspects | `structural_rack`, `agv_amr_fleet`  | Strike-to-damage correlation with the inclinometer; traffic-pattern findings that feed the slotting and layout what-ifs |

### B.9 Count

Row numbers run continuously from 1 to 80 across the eight tables with no gaps.

One candidate type, a pick-face illuminance sensor, is sequenced rather than dropped. Worker comfort is already served by the temperature and humidity pair through a derived heat index, and the remaining use, correlating pick error with lighting, needs the ergonomics layer before it has a consumer. It is carried in ROADMAP.md against component 6a10 and it is not counted here, because the count in this section is the count of `implemented` entries.

Counts taken directly from the tables above:

| Category                       | Rows in table | Count  |
|--------------------------------|---------------|--------|
| B.1 Industrial equipment       | 1 to 14       | 14     |
| B.2 Environmental and facility | 15 to 21      | 7      |
| B.3 Warehouse and logistics    | 22 to 36      | 15     |
| B.4 Transportation and fleet   | 37 to 48      | 12     |
| B.5 Electrical and power       | 49 to 58      | 10     |
| B.6 Safety and compliance      | 59 to 66      | 8      |
| B.7 Process and chemical       | 67 to 75      | 9      |
| B.8 Structural                 | 76 to 80      | 5      |
| **Total**                      |               | **80** |

The catalog ships 80 implemented types, at the top of the 60 to 80 target range the source sets. `test_category_counts_match_catalog` recomputes every row of this table from the entries on disk and fails on any disagreement, counting only entries with `status: implemented`, so a `planned` entry can never inflate a published number.

`docs/design/iot-fleet.md` section 3.2 publishes a different split of 80 across the same eight categories. Both totals are 80 and neither is arithmetic error; they are two designs for what counts as one type, and OQ-11 records the conflict rather than papering over it.

---

## C. Failure signatures by class

### C.1 Class profiles

Every entry inherits one profile. The profile supplies the universal modes with class-appropriate defaults so no entry restates them.

Each universal mode name below is a shorthand for a fault id in `docs/design/variability-and-faults.md` section C.4, which owns the injectors. The mapping is one to one and CI checks it, so a mode named in a profile always has something that can inject it.

| Universal mode       | Fault id           |
|----------------------|--------------------|
| `drift`              | `F-DEV-DRIFT`      |
| `stuck_at`           | `F-DEV-STUCK`      |
| `dropout`            | `F-DEV-DROP`       |
| `calibration_loss`   | `F-DEV-CALIB`      |
| `noise_inflation`    | `F-DEV-NOISEUP`    |
| `clock_skew`         | `F-DEV-CLOCKDRIFT` |
| `crash_loop`         | `F-DEV-CRASHLOOP`  |
| `duplicate_event`    | `F-DEV-DUPREAD`    |
| `degraded_read_rate` | `F-DEV-READRATE`   |
| `spurious_event`     | `F-DEV-GHOST`      |
| `model_version_skew` | `F-DEV-FIRMWARE`   |

Four profile modes have no fault id yet: `bias_step`, `saturation`, `transition_loss`, and `array_dead_pixel`. Each is a registration request against the fault catalog on the same terms as a distribution family, and an entry whose profile supplies an unregistered mode cannot reach `status: implemented`. OQ-12 tracks them.

| Profile               | Applies to                                                          | Universal modes supplied                                                                                   |
|-----------------------|---------------------------------------------------------------------|------------------------------------------------------------------------------------------------------------|
| `continuous_analog`   | Analog scalars: temperature, pressure, level, current, strain, load | drift, stuck_at, dropout, calibration_loss, bias_step, noise_inflation, saturation, clock_skew, crash_loop |
| `spectral_vector`     | Vibration bands, thermal arrays, spectra                            | all of the above plus band_decoherence, channel_dropout, array_dead_pixel                                  |
| `probabilistic_event` | RFID, barcode, photo eye, scan events                               | dropout, duplicate_event, degraded_read_rate, spurious_event, clock_skew, crash_loop                       |
| `discrete_state`      | E-stop, guard, door, UPS mode, reefer mode                          | stuck_at, chatter, dropout, clock_skew, crash_loop, transition_loss                                        |
| `electrochemical`     | pH, DO, CO, LEL, conductivity                                       | drift, sensitivity_decay, response_slowdown, end_of_life, poisoning, dropout, calibration_loss             |
| `optical`             | PM, DO optical, barcode imager, photo eye, thermal array, CV        | fouling, ambient_saturation, source_ageing, alignment_drift, plus the analog universals                    |
| `rf_positional`       | RFID, UWB, BLE, GNSS                                                | multipath_bias, nlos_bias, interference, antenna_degradation, identity_collision, dropout                  |
| `counter_totalizer`   | kWh, odometer, engine hours, metal loss, mass throughput            | rollover, reset_loss, accumulation_gap, backfill_disorder, plus monotonicity violation as a hard failure   |
| `inference_channel`   | CV-derived channels (PPE compliance)                                | class_confusion, occlusion, domain_shift, confidence_miscalibration, model_version_skew                    |

### C.2 Signature table

| Signature                             | Affected classes                                               | What it looks like in the data                                                                                                                                                                               | Layer expected to catch it                                                                    |
|---------------------------------------|----------------------------------------------------------------|--------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|-----------------------------------------------------------------------------------------------|
| **Drift**                             | all analog, electrochemical, structural                        | Slow monotone or mean-reverting movement of the mean with unchanged variance. Against a redundant sensor, the residual walks                                                                                 | MSA stability study; SPC EWMA on the residual against a reference channel                     |
| **Stuck-at**                          | all                                                            | Variance collapses to zero (or to the quantization step) while the twin state that drives the channel continues to move. The value can be plausible, which is why plausibility checks alone miss it          | Fleet health variance monitor; twin-divergence detector                                       |
| **Dropout**                           | all                                                            | Missing samples against the declared interval; a gap distribution rather than a single gap. Distinguish a device dropout from a broker outage by whether siblings on the same edge node also stopped         | Fleet health heartbeat monitor; broker session tracking                                       |
| **Calibration loss**                  | all analog, electrochemical                                    | Gain error (a proportional divergence that grows with signal magnitude) or offset error (a constant shift). Gain and offset are separable by regressing against a reference over a range                     | MSA linearity and bias study; scheduled calibration audit                                     |
| **Bias step**                         | all analog                                                     | A discontinuity with no corresponding twin state change. Frequently follows a maintenance event, which is why the change log is correlated against the finding                                               | SPC Western Electric rule 1 and Nelson rule 3; change-correlation in the CMMS queue           |
| **Noise inflation**                   | all analog                                                     | Mean unchanged, variance up. Often the first sign of a loose connection or a failing amplifier                                                                                                               | I-MR chart moving-range component; MSA repeatability study                                    |
| **Saturation / rail**                 | analog, spectral                                               | The value pins at a limit and stops responding. Distinguish from a genuine extreme by checking whether the value sits exactly at the ADC full scale                                                          | Plausibility validator at ingest; fleet health signature classifier                           |
| **Clock drift / timestamp skew**      | all                                                            | Samples arrive out of order, or a device's inter-sample interval diverges from sim-time. Cross-device event ordering breaks, which corrupts genealogy                                                        | Historian ingest ordering check; Sparkplug sequence-number gap detection                      |
| **Crash loop**                        | all                                                            | Repeated birth certificates from the same edge node at a high rate; sequence number resets to zero repeatedly                                                                                                | Sparkplug NBIRTH rate monitor; fleet health uptime score                                      |
| **Duplicate reads**                   | probabilistic_event, rf_positional                             | The same identity read twice within a physically impossible interval, or read at two portals at once                                                                                                         | Deduplication at ingest; genealogy consistency check                                          |
| **Degraded read rate**                | probabilistic_event, rf_positional                             | Read rate per pass falls while the tag population and product mix hold constant. Per-antenna decomposition separates a physics cause from a device cause                                                     | Read-rate control chart by portal and by antenna port; RF physics diagnostic (E46)            |
| **Monotonicity violation**            | counter_totalizer                                              | A totalizer decreases. Always a fault, never physical                                                                                                                                                        | Property test in CI; hard ingest rejection with a critical finding at runtime                 |
| **Accumulation gap**                  | counter_totalizer                                              | A totalizer resumes at the right value after an outage but the interval deltas do not sum to the difference                                                                                                  | Historian reconciliation job                                                                  |
| **Sensitivity decay**                 | electrochemical, optical, spectral                             | Response amplitude to a known stimulus falls over months. The fail-silent class: the reading looks fine and is too low                                                                                       | Scheduled bump test or span check; MSA stability study over a long window                     |
| **Response slowdown**                 | electrochemical, thermal                                       | The time constant lengthens. Step responses become sluggish; the reading lags the twin state by a growing interval                                                                                           | Cross-correlation lag estimation against the twin state; the tau trend is its own PdM channel |
| **Poisoning**                         | electrochemical (catalytic bead especially)                    | A permanent, irreversible sensitivity loss with no visible signature at all in normal operation                                                                                                              | Scheduled bump test only. This is the entry that justifies proof testing existing at all      |
| **Fouling**                           | optical, wetted process                                        | Baseline shift plus reduced dynamic range, often with a step recovery after a cleaning event, which makes the cleaning log a valuable label source                                                           | Baseline trend versus cleaning event log; excess gain margin monitor                          |
| **Multipath / NLOS bias**             | rf_positional                                                  | A strictly positive, spatially structured position or range error. Never symmetric                                                                                                                           | Anchor geometry residual analysis; UWB-versus-AMR-odometry cross-check                        |
| **Interference**                      | rf_positional                                                  | Read rate or RSSI degradation correlated in time with an interfering source (VFD switching, a 2.4 GHz load). The correlation is the evidence                                                                 | Cross-correlation of read rate against drive state; spectrum occupancy trend                  |
| **Antenna degradation**               | rf_positional                                                  | VSWR rise on one port; read range falls as the fourth root of nothing simple, and specifically as the square root of radiated power for a forward-link-limited system. One port declines while siblings hold | Per-antenna read-rate control chart; VSWR trend where the reader reports it                   |
| **Chatter**                           | discrete_state                                                 | Rapid state oscillation faster than any physical process. Floods the findings stream if unhandled, which is exactly what alarm rationalization exists to prevent                                             | Alarm rationalization debounce and shelving; chatter-rate metric per device                   |
| **Transition loss**                   | discrete_state                                                 | An expected state change never appears; the device reports the same state for longer than the twin says is possible                                                                                          | Absence-of-expected-transition detector; scheduled proof test                                 |
| **Welded contact**                    | discrete_state, safety                                         | Stuck-at in the **safe-looking** direction. The reading is the good one, which is why it is only detectable by proof testing or by the absence of expected transitions                                       | Scheduled proof test; absence-of-expected-transition detector. Severity floor: critical       |
| **Cross-read / false positive**       | probabilistic_event, rf_positional                             | An event appears on the wrong equipment topic. The identity is real; the location is wrong                                                                                                                   | ASN reconciliation; CV count cross-check; dwell-time plausibility                             |
| **Cross-sensitivity artifact**        | electrochemical                                                | One sensor responds to a species it is not measuring (a CO cell responding to hydrogen). **Not a fault**, and treating it as one is the error                                                                | Multi-sensor correlation model; documented in the entry so the correlation layer expects it   |
| **Emissivity / compensation error**   | thermal array, conductivity, ultrasonic level, viscosity, TPMS | A systematic error introduced by a missing or wrong compensation constant. Invisible without a reference, and constant so it does not trend                                                                  | Two-technology cross-check; MSA bias study against a reference                                |
| **Array dead pixel**                  | spectral_vector, thermal array                                 | One element of a vector holds constant while its neighbors move                                                                                                                                              | Per-element variance monitor; array health score                                              |
| **Band decoherence**                  | spectral_vector                                                | Every defect band collapses toward the noise floor simultaneously and the machine appears to improve overnight. **Sudden improvement across all bands is a measurement failure, not a repair**               | Fleet health signature classifier; speed-reference availability check                         |
| **Class confusion / domain shift**    | inference_channel                                              | Detection distribution shifts after a lighting or layout change with no corresponding physical change; confidence calibration degrades                                                                       | Model drift monitor in the MLOps layer (E43); CV-versus-RFID count disagreement               |
| **Model version skew**                | inference_channel                                              | Two devices running different model versions produce systematically different rates for the same scene                                                                                                       | Fleet configuration compliance audit (E48)                                                    |
| **Store-and-forward replay disorder** | all, especially telematics                                     | A burst of backdated messages after a reconnect, out of order and with historical timestamps                                                                                                                 | Historian ingest ordering; Sparkplug `is_historical` flag handling                            |

### C.3 Detection responsibility

Each signature names its owning layer so no signature is unowned:

| Layer                                      | Owns                                                                                                                                    |
|--------------------------------------------|-----------------------------------------------------------------------------------------------------------------------------------------|
| Ingest plausibility validator              | Range violations, monotonicity violations, saturation at exact full scale, timestamp ordering                                           |
| Fleet health and device registry           | Dropout, crash loop, heartbeat loss, uptime scoring, variance collapse, per-device health score with FMEA severity-occurrence-detection |
| Measurement system analysis (Gage R&R)     | Bias, repeatability, reproducibility, linearity, stability. Owns drift, calibration loss, and sensitivity decay over long windows       |
| SPC (LSS engine)                           | Bias steps, noise inflation, trends, and every Western Electric and Nelson rule violation on any channel or residual                    |
| Predictive maintenance trend layer         | Time-to-threshold on degrading assets; distinguishes asset degradation from sensor degradation using the entry's `confusable_with` list |
| Cross-sensor consistency                   | Redundant pairs (radar versus ultrasonic level, Coriolis versus magmeter, RFID versus CV count, UWB versus AMR odometry)                |
| Twin divergence detector                   | Stuck-at where the value stays plausible; any channel that stops tracking the twin state it is coupled to                               |
| Alarm rationalization                      | Chatter, flapping, duplicate findings, severity ranking, shelving                                                                       |
| Scheduled proof and bump testing           | Fail-silent modes: welded contacts, catalytic bead poisoning, transition loss. **The only detector for these, which is the point**      |
| Fleet configuration compliance audit (E48) | Model version skew, config drift, firmware inconsistency                                                                                |

---

## D. UNS and Sparkplug B mapping

### D.1 The ISA-95 topic hierarchy

```
{enterprise}/{site}/{area}/{line}/{equipment}/{parameter}
```

| Level        | Source                                     | Example                                       | Rules                                                                              |
|--------------|--------------------------------------------|-----------------------------------------------|------------------------------------------------------------------------------------|
| `enterprise` | Fixed per deployment, from `facility.yaml` | `twinflow`                                    | Single literal, lowercase                                                          |
| `site`       | Facility profile                           | `site-a`                                      | One per facility; multi-site (E13) bridges across this level                       |
| `area`       | Facility profile                           | `receiving`, `storage`, `outbound`, `factory` | ISA-95 area                                                                        |
| `line`       | Facility profile                           | `line-1`, `dock-bank-a`                       | ISA-95 work center                                                                 |
| `equipment`  | Device instance binding                    | `conv-drive-02`                               | Resolved from `attaches_to.instance_naming`                                        |
| `parameter`  | Catalog entry `uns.parameter`              | `vibration/band_spectrum/de`                  | May contain additional slashes; this is the only level allowed to be multi-segment |

Charset for every level: `[a-z0-9-]+`, plus `/` in the parameter level only. No wildcards, no empty levels, no leading or trailing slash, no `+` or `#`. Maximum total topic length 512 bytes, asserted in CI.

Every topic in this section is published through the `Network` port, the MQTT-shaped one that carries retain, quality of service, last will, and wildcard subscribe. D-08 separates that port from `EventBus`, which is subject-addressed fan-out with none of those, and the device fleet never uses `EventBus`. At the enterprise tier the broker bridges MQTT at the operational edge into the partitioned log at the information layer, so a catalog entry's `uns.qos` and `uns.retain` fields keep their meaning at every tier.

#### D.1.1 Mobile assets do not fit ISA-95 cleanly

Trucks, trailers, and AMRs are not in an area or on a line. The catalog resolves this by binding mobile assets to a dedicated area under the site they are dispatched from:

```
twinflow/site-a/fleet/{fleet_group}/{asset_id}/{parameter}
twinflow/site-a/fleet/tractors/tractor-114/cargo/temperature/pulp
twinflow/site-a/fleet/amr/amr-07/battery/soc
```

This keeps the six-level shape intact while being honest that `fleet` is an area only by convention. It is flagged as OQ-3 because a defensible alternative exists.

### D.2 Worked example: one catalog entry to N topics

Catalog entry `eq.vib.band_spectrum` with `binding: per_equipment`, `positions: [de, nde]`, `cardinality.default_per_binding: 2`.

Facility profile declares three conveyor drives in `receiving/line-1`. The instantiator produces:

```
twinflow/site-a/receiving/line-1/conv-drive-01/vibration/band_spectrum/de
twinflow/site-a/receiving/line-1/conv-drive-01/vibration/band_spectrum/nde
twinflow/site-a/receiving/line-1/conv-drive-02/vibration/band_spectrum/de
twinflow/site-a/receiving/line-1/conv-drive-02/vibration/band_spectrum/nde
twinflow/site-a/receiving/line-1/conv-drive-03/vibration/band_spectrum/de
twinflow/site-a/receiving/line-1/conv-drive-03/vibration/band_spectrum/nde
```

Six topics from one catalog entry, zero lines of code, and the same entry produces different topics in a different facility profile without modification.

### D.3 Sparkplug B mapping

The UNS topic above is the semantic address and is what a human or a subscriber reasons about. Sparkplug B has its own topic namespace, and both are published: the Sparkplug payload carries the UNS path as the metric name, so the two views stay reconciled.

Everything this subsection states about Sparkplug is read from the Eclipse Sparkplug Specification, version 3.0.0, dated 2022-11-16, which is a freely published specification under the Eclipse Public License. Section references below point into that document. It is a tier-A source under A.7, recorded as `SRC-SPARKPLUG-3-0-0`.

#### D.3.1 Sparkplug topic namespace

```
spBv1.0/{group_id}/{message_type}/{edge_node_id}[/{device_id}]
```

| Element        | Derivation                                                               | Example                     |
|----------------|--------------------------------------------------------------------------|-----------------------------|
| `group_id`     | `{enterprise}:{site}:{area}`                                             | `twinflow:site-a:receiving` |
| `message_type` | `NBIRTH`, `NDATA`, `NDEATH`, `DBIRTH`, `DDATA`, `DDEATH`, `NCMD`, `DCMD` | `DDATA`                     |
| `edge_node_id` | The gateway serving the line; tier 1 in the E36 compute placement model  | `gw-line-1`                 |
| `device_id`    | The physical device instance                                             | `vib-conv-drive-02`         |

Metric name inside the payload is the UNS remainder below the group:

```
line-1/conv-drive-02/vibration/band_spectrum/de
```

#### D.3.2 Datatype selection

The datatype is derived from `measurement.channel_shape` and the value semantics, not chosen per entry by hand. Enum values are those of the `DataType` enumeration in the specification's payload definition.

| Channel shape and semantics                                                                            | Sparkplug datatype                                                                       | Enum               |
|--------------------------------------------------------------------------------------------------------|------------------------------------------------------------------------------------------|--------------------|
| Scalar physical quantity where single precision is enough                                              | `Float`                                                                                  | 9                  |
| Scalar physical quantity needing double precision (GNSS latitude and longitude, cumulative totalizers) | `Double`                                                                                 | 10                 |
| Boolean state                                                                                          | `Boolean`                                                                                | 11                 |
| Enumerated state (reefer mode, UPS mode, e-stop state)                                                 | `String`                                                                                 | 12                 |
| Monotone counter                                                                                       | `UInt64`                                                                                 | 8                  |
| Discrete count in a window                                                                             | `UInt32`                                                                                 | 7                  |
| Fixed-length vector (vibration bands)                                                                  | `FloatArray`                                                                             | 30                 |
| Matrix (thermal array)                                                                                 | `FloatArray` flattened with `rows` and `cols` carried as metric properties, or `DataSet` | 30 or 16, see OQ-1 |
| Composite event (an RFID read with EPC, port, RSSI, phase)                                             | `Template`                                                                               | 19                 |
| Timestamped instant                                                                                    | `DateTime`                                                                               | 13                 |

The full enumeration runs `Unknown` at 0, `Int8` through `Text` at 1 to 14, `UUID` at 15, `DataSet` at 16, `Bytes` at 17, `File` at 18, `Template` at 19, `PropertySet` at 20, `PropertySetList` at 21, and the array types at 22 to 34, of which `FloatArray` is 30, `DoubleArray` 31, `BooleanArray` 32, `StringArray` 33, and `DateTimeArray` 34. The code refers to these by name through a table generated from the specification's protobuf definition, never by a literal written by hand, and `test_datatype_enum_matches_generated_table` fails if the two disagree.

#### D.3.3 Alias assignment at birth

Sparkplug aliases exist so a `DDATA` message can omit the metric name and send a small integer instead. The specification makes an alias, where used, unique across the edge node's entire set of metrics, requires a birth message to carry both name and alias, and requires `NDATA`, `DDATA`, `NCMD`, and `DCMD` to carry the alias with the name excluded. The policy below is what this repository adds on top so that a replayed run reproduces the same payloads:

1. At `DBIRTH`, collect every metric this device will publish during the session.
2. Sort metric names with a stable byte-wise ordering over their UTF-8 encoding. The sort is explicit rather than incidental, because a set iterated in hash order would produce a different alias map in a second process (D-03).
3. Assign aliases starting at 1, in sorted order. Alias 0 is never assigned, so a zero alias is always a bug and is detectable as one. That is a repository rule, not a specification rule.
4. The `DBIRTH` payload carries every metric with both its name and its alias, plus its full property set (`engUnit`, `engLow`, `engHigh`, `description`, `sensor_type_id`, `sensor_type_revision`, `Quality`).
5. Every subsequent `DDATA` carries the alias only.
6. Aliases are valid for the life of the session. A rebirth, whether after `DDEATH`, a reconnect, or a `Node Control/Rebirth` command, may reassign, so a consumer that caches aliases across a birth boundary is broken. The historian ingest path is tested against a rebirth with a changed metric set.

The payload byte identity this produces is a same-platform claim only, per D-05. Alias assignment and metric ordering are integer and string operations and are identical everywhere; the floating-point values inside the payload are not, so the cross-platform claim is value equivalence within the tolerance the cross-platform job measures.

#### D.3.4 Sequence, session, and quality

`bdSeq` in `NBIRTH` and `NDEATH` ties a session together, and the specification requires the will-message `bdSeq` to increment on each connect and wrap to 0 after 255.

An `NBIRTH` payload must carry a `seq` between 0 and 255 inclusive, and that value becomes the starting number for the session; every following message carries one more than the previous, wrapping back to zero after 255. An edge node is not required to start a session at zero, so a consumer that assumes `seq` 0 in `NBIRTH` is reading a rule the specification does not state. The historian anchors on the `NBIRTH` value it receives rather than on an assumed origin, and `test_nbirth_seq_is_not_assumed_zero` runs a session that starts at a non-zero `seq` and asserts the gap detector stays quiet.

A gap in `seq` is a data-loss signature and feeds the fleet health layer directly.

Metric quality rides in the property set under the key `Quality`, whose value is a signed 32-bit integer and must be one of three codes: 0 for BAD, 192 for GOOD, and 500 for STALE. The property is optional and is required only when quality is not GOOD. This catalog writes it on every metric anyway, because an absent property and a GOOD property are indistinguishable to a consumer that has to decide whether the producer knows about quality at all.

#### D.3.5 Worked payload sketch

For `DBIRTH` of `vib-conv-drive-02`:

```
topic: spBv1.0/twinflow:site-a:receiving/DBIRTH/gw-line-1/vib-conv-drive-02
payload:
  timestamp: <sim-time ms since epoch>
  seq: 3
  metrics:
    - name:  "line-1/conv-drive-02/vibration/band_spectrum/de"
      alias: 1
      datatype: FloatArray   # enum 30
      value: [0.42, 0.13, 0.05, 0.07, 0.06, 0.04, 0.03, 0.19]
      properties:
        engUnit: "mm/s"
        engLow: 0.0
        engHigh: 45.0
        Quality: 192
        sensor_type_id: "eq.vib.band_spectrum"
        sensor_type_revision: 1
        band_labels: "ord_1x,ord_2x,ord_3x,bpfo,bpfi,bsf,ftf,broadband_residual"
        uns_path: "twinflow/site-a/receiving/line-1/conv-drive-02/vibration/band_spectrum/de"
    - name:  "line-1/conv-drive-02/vibration/band_spectrum/nde"
      alias: 2
      ...
```

The `seq` of 3 is not special. It is one more than whatever the previous message in this session carried, and the session's origin was set by the `NBIRTH`.

Subsequent `DDATA` for the same metric carries `alias: 1` and the value, and nothing else.

### D.4 The JSON fallback profile

Sparkplug B is the default payload encoding, and the repository also ships a `json_fallback` profile that publishes a plain JSON payload on `{uns_topic}/json`. Two reasons: the walking skeleton in Phase 1 comes before the Sparkplug milestone (E3), and a reader browsing an MQTT client for ninety seconds must be able to read a payload without a protobuf decoder. The profile is a config switch, and the catalog entry does not change. CI runs the topic-uniqueness and round-trip tests under both profiles.

### D.5 Events this section publishes

D-07 settles the envelope before Phase 0 freezes schemas, and every section that declares an event carries it. Sensor telemetry is not an event log entry, but the catalog layer does publish events, and those events are subject to the envelope.

Every event below carries `run_id`, `producer_id`, `seq`, `sim_ts`, `schema_version`, and the payload. The sequence number is dense per `(run_id, producer_id)` and never global, because the garage tier already runs several containers plus the Rust agent and no allocator for a global counter exists. The canonical total order is `(sim_ts, producer_id, seq)`, and the replay reader and the pagination cursor both use it.

| Subject                        | Producer            | Payload                                                                                               | Consumed by                              |
|--------------------------------|---------------------|-------------------------------------------------------------------------------------------------------|------------------------------------------|
| `sensor.catalog.loaded`        | catalog loader      | Entry count by status and category, catalog content hash, schema version, the sorted list of type ids | Run manifest hashed core, fleet registry |
| `sensor.device.provisioned`    | device instantiator | `device_id`, `type_id`, `type_revision`, UNS path, edge node, the drawn `unit_offset`                 | Fleet registry, MSA layer                |
| `sensor.type.deprecated`       | catalog loader      | `type_id`, superseding `type_id`, the run in which the deprecation takes effect                       | Historian schema migration               |
| `sensor.fault.injected`        | fault injector      | `catalog_id`, `instance_id`, `device_id`, onset `sim_ts`, effect parameters                           | Ground-truth writer, scoring harness     |
| `sensor.plausibility.violated` | ingest validator    | `device_id`, channel, observed value, the span it left, and which bound                               | Findings stream, fleet health            |
| `sensor.provenance.degraded`   | catalog loader      | `type_id`, the parameter group, its tier, and the source id                                           | Release gate; blocks a release on tier D |

`sensor.catalog.loaded` carries the sorted type id list rather than a set, because that payload reaches the log hash and set iteration order is not stable across processes (D-03). The catalog content hash is computed over entries sorted by `type_id`, and `test_catalog_hash_is_load_order_independent` loads the same catalog from a shuffled directory listing and asserts the hash is unchanged.

No event on this list carries a wall-clock value. The provenance sidecar carries `started_wall_utc` and the platform fingerprint, and the hashed core carries the catalog content hash instead (D-01). The catalog loader is not one of the four places allowed to read a wall clock (D-02).

### D.6 The Rust agent draws from the same streams

A Rust agent that generated its own randomness would put a hole at exactly the boundary this project is proudest of. D-06 rules that the agent derives its stream from the run seed and its device id using the same name-addressed derivation the Python side uses, specified byte for byte in `docs/design/variability-and-faults.md` section A.1 in terms of a named hash function and a named bit generator rather than in terms of whichever library either language happens to have.

For the catalog that means three things. The agent reads the same entry, so the stream names in `signal_model.rng_streams` are the agent's stream names too. The agent's `unit_offset` for a device comes from `provision.sensor.{device_id}.unit_offset`, which is drawn at provisioning on the Python side, so an agent restart does not redraw it. A cross-language conformance test asserts that the two implementations produce identical draws for the same stream name and seed, and the catalog entry for whichever type the Rust agent serves is the fixture that test uses.

---

## E. README table

Compact form for the repository README, with counts.

```markdown
## Implemented sensor types

80 physics-modeled sensor types, defined as data in `catalog/sensors/`. Each entry
declares its signal model, failure modes, UNS topic, Sparkplug metric, twin attachment,
and the capability it unlocks. Adding a type is a YAML file, not a code change.

| Category                   | Types  | Examples                                                                                           | What it unlocks                                               |
| -------------------------- | ------ | -------------------------------------------------------------------------------------------------- | ------------------------------------------------------------- |
| Industrial equipment       | 14     | Order-tracked vibration bands, acoustic emission, motor current signature, oil condition           | Predictive maintenance with time-to-threshold estimates       |
| Environmental and facility | 7      | Ambient temperature, humidity, dew point, CO2, particulate, water leak, thermal array              | Facility health and worker comfort findings                   |
| Warehouse and logistics    | 15     | RFID portals and handhelds, scan events, shelf and dock scales, UWB, BLE, conveyor speed and load  | The DC material flows and lot genealogy                       |
| Transportation and fleet   | 12     | GNSS, IMU, TPMS, reefer status, cargo temperature, shock, tilt, telematics gateway                 | Cold-chain integrity, excursions traced through genealogy     |
| Electrical and power       | 10     | Three-phase voltage and current, power and power factor, smart meter, battery SOC/SOH, UPS         | Energy KPIs and AMR charging physics                          |
| Safety and compliance      | 8      | Smoke, LEL, CO, e-stop, guard interlock, worker proximity, PPE vision, fall detection              | Worker-safety findings with a severity floor above throughput |
| Process and chemical       | 9      | pH, conductivity, viscosity, Coriolis and magnetic flow, radar and ultrasonic level, DO, corrosion | Batch quality and golden-batch scoring                        |
| Structural                 | 5      | Column strain, crack width, roof load, rack tilt, rack impact                                      | Facility integrity under snow load                            |
| **Total**                  | **80** |                                                                                                    |                                                               |

The design pattern scales to the full 500-type industrial sensor landscape, and the
schema is the argument. See `docs/design/sensor-catalog.md` for the schema, the
scaling argument, and the limits that argument runs into.

Parameter values come from published standards, datasheets, and derivations, each
recorded with its source in `catalog/provenance/sources.yaml`. No parameter is
fitted to any real installed base, and no client data is in this repository.
```

CI regenerates the counts column from the catalog directory and fails if the README drifts. It counts only entries with `status: implemented`, so the published number is the implemented number and a `planned` entry cannot inflate it.

---

## F. The scaling argument

### F.1 Why type 300 is a config entry

Seven properties of the schema, each the reason a specific kind of code change is unnecessary.

#### F.1.1 The generator composes registered parts rather than subclassing

There is no `VibrationSensor` class. A generator engine reads `signal_model` and assembles a pipeline in a fixed order: resolve the coupling reads from the twin state broker, evaluate the baseline expression, add the per-device unit offset, apply each noise family, apply each drift family, apply the response dynamics, apply quantization, apply any active failure effects, then emit. A new type names parts and supplies parameters. The engine does not know what a bearing is.

#### F.1.2 The family catalog is small and close to closed

The nineteen families the distribution catalog already carries, plus the six this section requests in A.4.4, cover the physics of all eighty types. They are not sensor-specific: they are standard distributions and stochastic processes. A 500-type catalog does not need 500 families, because a pH electrode's slope decay and a battery's capacity fade are both `linear_ramp` with different parameters, and a piezoelectric sensitivity loss and an electrolyte dry-out are both `arrhenius_accelerated`. The families are the physics vocabulary and the entries are sentences in it.

#### F.1.3 Topic and metric mapping are derived, never written

A catalog entry declares a binding level and a parameter suffix. The instantiator walks `facility.yaml`, resolves the ISA-95 levels, and produces topics. The Sparkplug datatype is derived from the channel shape. The alias is derived from the sorted metric set at birth. Nobody types a topic string, so nobody can typo one, and adding a type cannot collide with an existing topic without CI catching it.

#### F.1.4 Twin coupling is declarative and validated

The `coupling.reads` list is the entire interface between a sensor and the simulation. The twin exposes a registered state vector with names and units; the sensor names what it reads. The twin has no knowledge of sensors at all. Adding a sensor never edits the twin, and the CI check that every coupling read resolves means the two cannot drift apart silently.

#### F.1.5 Failure modes inherit from class profiles

A new type gets drift, stuck-at, dropout, calibration loss, clock skew, and crash loop by naming its profile. It only writes the modes that are specific to its physics, which is typically two to four. That is the difference between a 200-line entry and a 40-line one, and it is why the marginal cost of a type falls as the catalog grows rather than rising.

#### F.1.6 Capability wiring is a checked graph edge

`unlocks` and `consumed_by` form a bipartite graph between types and subsystems. CI walks it. A type with no consumer fails the build, and a capability with no producer fails the build. This is the mechanism that keeps a 500-type catalog from becoming 430 types of padding: a type that unlocks nothing cannot be merged.

#### F.1.7 Validation is generated from the declaration

The entry declares its distribution families, its bounds, and its budget. The test suite reads those declarations and generates the goodness-of-fit test, the property-based bounds test, the topic uniqueness case, and the budget assertion. Writing a new type writes its own tests. Nobody has to remember to add them, which is the only reason a large catalog stays trustworthy.

### F.2 The honest limits

#### F.2.1 A new stochastic family needs code

The Hawkes family is requested once for acoustic emission and then reused for near-misses and cable microphonics. The next novel physics, whether hysteresis with memory, a coupled multi-body resonance, or a spatially correlated random field for a distributed fiber sensor, needs a family registered in the distribution catalog with its own unit tests. The claim is that the marginal rate of new-family requests falls sharply after the first fifty or so types, not that it reaches zero, and the six requests in A.4.4 against a catalog of eighty types are the measurement of that rate so far.

#### F.2.2 Array and image channels do not scale like scalars

A 32x24 thermal array at 1 Hz is 768 floats per second per device. Five hundred of those does not run on a laptop, and the load-test curve (A4) will show exactly where the knee is. The catalog handles this by making the sampling rate and the publish policy config, and by supporting on-demand raw capture rather than continuous streaming, but the underlying constraint is real and stated rather than hidden.

#### F.2.3 The real ceiling is the twin state vector, not the catalog

A sensor can only be coupled to a phenomenon the twin simulates. Adding a dissolved-ozone sensor to a twin that does not model ozone chemistry produces a sensor with no `coupling.reads`, which means an uncoupled random-number generator wearing a sensor's name. The schema makes this visible (an empty coupling list is legal but must be justified in `capability.rationale` and is flagged in review) but it cannot make it untrue. Scaling the catalog to 500 types means scaling the twin, and the twin is the expensive half. That is the version of the scaling claim the README carries.

#### F.2.4 Test suite cost grows linearly and statistical power does not come free

Eighty types with a goodness-of-fit test each, at 200000 samples per test, is already a meaningful CI budget, and G.8 does that arithmetic against the job budget rather than assuming it fits. At 500 types one of three things gives: the sample counts fall and with them the power to detect a wrong distribution, the wall-time budget grows, or the fit suite moves to a nightly job with a fast smoke subset on every pull request. The third is the plan, and the price is that a wrong distribution can merge and be caught within 24 hours rather than within the pull request.

#### F.2.5 Parameters are sourced, and sourcing is the slowest part

Every numeric parameter is covered by a `provenance` row naming a publisher, an edition, and a locator, and A.7 blocks `status: implemented` while any group sits at tier D. That is the strongest form of the claim this catalog can make: not that the numbers are measured on an installed base, which they are not and never will be because no client data is in this repository, but that each one names a source a reader can go and check. The generators produce data with the right structure, the right coupling, and the right failure signatures. They do not reproduce any particular real machine.

The cost of that rule is the honest limit. Sourcing a parameter group takes longer than writing one, several standards bodies paywall the documents this catalog cites, and a paywalled standard caps a group at tier C no matter how much effort goes into it. OQ-13 carries the backlog of groups still at tier D, and the number of them is a published figure rather than a private one.

#### F.2.6 Birth certificate size grows with metric count

The alias field is a 64-bit unsigned integer, so the alias space is not the constraint. The constraint is that a single edge node with several hundred metrics produces a large `NBIRTH`, and every rebirth republishes all of it. Sharding devices across more edge nodes rather than growing metrics per node is what production deployments do, and the load test measures the rebirth storm cost directly rather than assuming it.

#### F.2.7 The determinism claim has two tiers, and only one of them is byte identity

D-05 scopes the determinism claim honestly, and this catalog is the part of the system where the scoping bites hardest. Distributions sample floats and round to ticks, which makes a stream sensitive to a one-unit-in-last-place difference in `log`, `exp`, or the inverse error function across platforms and SIMD dispatch. Eighty types drawing from nineteen families is a large surface for that sensitivity.

So the catalog claims byte identity only for the same seed, the same config, the same platform, and the same pinned dependency set, checked by hash equality. Across platforms it claims value equivalence: the business events are identical, and continuous fields agree within a tolerance derived from measured divergence. The cross-platform job reports the observed maximum divergence rather than asserting a number chosen in advance, and when the observed figure exceeds the tolerance the gate names which of the two possibilities it is, a wrong tolerance or a real defect.

The `validation.determinism` block in every entry carries both tiers, and the provisional cross-platform tolerance in A.2 is marked provisional because no divergence has been measured yet. Replacing it with the measured figure is a Phase 3 deliverable, not an editorial pass.

---

## G. Testing

Test tiers map onto the repository's C4 tiering: fast unit, property-based invariants, and seeded end-to-end scenarios.

Every test below states the observation that would fail it, because a test whose failure condition cannot be described is not a test (D-12).

### G.1 Schema validation tests

| Test                                       | Assertion                                                                                                                                              |
|--------------------------------------------|--------------------------------------------------------------------------------------------------------------------------------------------------------|
| `test_all_entries_validate`                | Every file in `catalog/sensors/**` validates against `sensor-type.schema.json`                                                                         |
| `test_no_additional_properties`            | Schema has `additionalProperties: false` at every object level; a fixture with a typo'd field fails validation                                         |
| `test_filename_matches_id`                 | Filename stem equals `id` for every entry                                                                                                              |
| `test_directory_matches_category`          | Containing directory equals `category` for every entry                                                                                                 |
| `test_ids_unique`                          | No duplicate ids across the catalog                                                                                                                    |
| `test_units_resolve`                       | Every `measurement.unit` is a valid UCUM code                                                                                                          |
| `test_expressions_parse`                   | Every expression parses to the restricted AST, contains no disallowed node type, and references only declared names                                    |
| `test_coupling_reads_resolve`              | Every `coupling.reads` path exists in the twin state registry with a compatible unit                                                                   |
| `test_families_registered`                 | Every `family` name resolves in the distribution catalog of `docs/design/variability-and-faults.md` section B                                          |
| `test_distribution_support_matches_bounds` | For every channel with declared bounds, the noise family's support is contained in those bounds. A Normal on a bounded channel fails here              |
| `test_fault_ids_resolve`                   | Every `failure_modes[].catalog_id` and every `device_faults` id resolves in the fault catalog                                                          |
| `test_rng_streams_registered`              | Every name in `signal_model.rng_streams` parses under the stream grammar and is present in the stream registry                                         |
| `test_detectors_registered`                | Every `detectable_by` id resolves to a registered detector                                                                                             |
| `test_mttd_within_pf_interval`             | For every mode, `expected_mttd_hours` does not exceed `pf_interval_hours`. A budget that admits failure before detection fails here                    |
| `test_phase_resolves`                      | Every `phase` value names a phase that exists in ROADMAP.md                                                                                            |
| `test_every_parameter_has_provenance`      | Every numeric leaf under `measurement`, `signal_model`, and `failure_modes` is covered by exactly one `provenance` row, and uncovered leaves are named |
| `test_no_tier_d_in_implemented`            | No entry with `status: implemented` carries a `provenance` row at tier D                                                                               |
| `test_every_source_records_retrieval`      | Every row in `sources.yaml` carries `retrieved` and `http_status`. A source claiming retrieval without a status fails                                  |
| `test_bearing_frequency_identity`          | For every bearing geometry in the reference table, the computed BPFO and BPFI sum to the rolling-element count. A mistyped geometry fails here         |
| `test_schema_backward_compatible`          | Diff against the previous released schema is additive-only within a major version                                                                      |
| `test_config_errors_are_helpful`           | A fixture catalog with six seeded errors produces six line-numbered messages, each naming the field and suggesting a fix (requirement C5)              |

### G.2 Per-type goodness-of-fit tests

Each entry declares what its generator must produce. The suite checks that it does.

| Test                      | Method                                                                                                                                                                                                                                                                            |
|---------------------------|-----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| Continuous family fit     | Hold the declared conditioning state fixed, draw `n_samples`, run Anderson-Darling (preferred over Kolmogorov-Smirnov because the tails are the part that matters and A-D weights them) against the declared family with parameters estimated from the entry, not from the sample |
| Count family fit          | Chi-square goodness of fit against the declared Poisson or negative binomial, with a dispersion test to confirm the choice between them                                                                                                                                           |
| Bounded family fit        | Anderson-Darling against the declared Beta, plus a boundary-mass test asserting no point mass at either bound (a point mass is the signature of a clip)                                                                                                                           |
| Duration family fit       | Anderson-Darling against lognormal, gamma, or Weibull as declared, plus a tail test on the upper decile                                                                                                                                                                           |
| Moment agreement          | Sample mean, variance, skewness, and excess kurtosis within a bootstrap confidence interval of the declared values                                                                                                                                                                |
| Autocorrelation structure | For the correlated families (`ou`, `ar1`, `wiener`), the sample autocorrelation matches the declared family. An `ou` with `reversion_per_day: 0.09` shows the corresponding decay, and a white-noise generator wearing an `ou` label fails here                                   |
| Allan variance            | For declared bias-instability channels (MEMS IMU, accelerometer), the Allan deviation curve shows the declared bias-instability floor at the declared averaging time                                                                                                              |
| Spectral content          | For `spectral_vector` types, a Welch power spectral density of the raw capture places at least the declared fraction of band energy within the declared halfwidth of the derived defect frequency. This is what turns "vibration is not white noise" into a checked claim         |
| Coupling sensitivity      | Sweep each coupled twin state variable across its range and assert the channel responds with the declared sign and approximate magnitude. Catches an expression that compiles but ignores its input                                                                               |
| Response dynamics         | Apply a step to the coupled twin state and fit the observed time constant; assert it matches the declared `tau_s` within tolerance. Catches a thermocouple with no lag                                                                                                            |

#### G.2.1 Multiple comparisons

Eighty types with several channels each produce several hundred hypothesis tests per CI run. At alpha 0.01 uncorrected, roughly three fail by chance every run and the suite is ignored within a week.

The suite applies a Benjamini-Hochberg false discovery rate control across the whole family at q = 0.01, reports the achieved power per test at the configured sample size, and fails the build only on a discovery. Individual test alphas and sample counts are declared per entry so a channel needing more power can ask for it. The fit suite runs in full nightly and as a fast subset, with reduced `n_samples` and smoke-level power, on every pull request.

#### G.2.2 The noise floor of each gate, and what falsifies it

D-11 requires a gate over a stochastic quantity to state its noise floor, to set its tolerance above that floor, and to state what result would falsify it. A goodness-of-fit test at a fixed sample count has a measurable noise floor, so the suite measures it rather than assuming it.

Before a gate is admitted, a calibration job draws the declared sample count from the declared family a thousand times and records the empirical distribution of the test statistic under the null. That distribution is the noise floor. Three things come out of it and all three are published in the gate's record.

| Quantity                | How it is obtained                                                                          | What it is used for                                                                        |
|-------------------------|---------------------------------------------------------------------------------------------|--------------------------------------------------------------------------------------------|
| Null distribution       | 1000 draws of `n_samples` from the declared family, statistic recorded each time            | The critical value, taken as an empirical quantile rather than an asymptotic approximation |
| Achieved power          | The same draws with a stated departure injected: a 10 percent shift in the family parameter | The gate states what size of error it catches at this sample count                         |
| Falsification condition | Stated per gate as the observation that fails it                                            | A gate with no describable failure is deleted and replaced (D-12)                          |

The falsification conditions for the ten methods above are the same in shape: the gate fails when the test statistic exceeds the empirical critical value of its own calibrated null after false discovery rate control. Two gates are worth stating separately because their falsification is not a p-value.

The spectral content gate fails when less than the declared fraction of band energy falls within the declared halfwidth of the computed defect frequency. The declared fraction is a repository-set threshold and not an external statistic, so it is recorded as a design parameter with a `SRC-REPO-MODEL` provenance row rather than presented as a validated figure, and OQ-14 carries the question of what external reference could ground it.

The response dynamics gate fails when the fitted time constant falls outside the tolerance around the declared `tau_s`. The tolerance is never tighter than the precision of the declared value: a `tau_s` written to two significant figures is checked to two significant figures, which is D-11's second condition applied to a parameter rather than to a published constant.

#### G.2.3 Seeding

Every fit test runs at a fixed seed recorded in the test output, so a failure is reproducible exactly. A separate scheduled job runs the same suite across a rotating seed set to catch a generator that is correct at one seed and wrong at others.

### G.3 Failure-mode injection tests

| Test                                     | Assertion                                                                                                                                                                                                                                                                                                                                                                    |
|------------------------------------------|------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| `test_every_mode_injectable`             | Every declared failure mode across every entry can be injected by id and produces an observable change in the stream. A mode that cannot be injected is dead config                                                                                                                                                                                                          |
| `test_mode_detected_within_mttd`         | Inject each mode by its `catalog_id` in a seeded scenario and assert the named `detectable_by` layer emits a finding within `expected_mttd_hours` of sim-time. This is what makes `expected_mttd_hours` a commitment rather than a comment                                                                                                                                   |
| `test_clean_run_false_positive_budget`   | A clean run of the same length with no injected mode produces findings below a declared false-positive budget per detector. Without this test the previous one is trivially satisfiable by a detector that always fires                                                                                                                                                      |
| `test_confusable_modes_separable`        | For each `confusable_with` pair, the signature classifier's confusion matrix on a labeled set meets a declared minimum. Where it does not, and mount looseness against an early outer race defect on broadband alone is the case that does not, the test asserts the classifier abstains rather than guessing, and asserts that adding the band spectrum channel resolves it |
| `test_fail_silent_modes_need_proof_test` | For every mode whose detector is only a scheduled proof test, assert that no other detector fires. This is a negative test that protects an honest claim: the repo must not accidentally imply it can detect a poisoned catalytic bead from the data stream                                                                                                                  |
| `test_severity_floor_enforced`           | Any finding originating from an entry with a `severity_floor` is ranked at or above that floor in the findings stream, and above every throughput finding present in the same window. The scenario seeds a throughput finding with a higher computed impact than the safety finding, so a ranking that merely sorts by impact fails                                          |
| `test_no_runtime_clamping`               | Inject a mode that drives a channel outside `range_of_interest` and assert the published value is the true out-of-range value and that a plausibility finding is raised. Complements `no_clamp_in_sampler`, which is a static check on the sampling path; this one is dynamic and catches a clamp added downstream of the sampler                                            |
| `test_tails_not_truncated`               | For every `gp_tail` channel, draw 10^7 samples and assert the count of exceedances above the declared extreme quantile falls inside the Poisson interval its rate implies. A truncating implementation produces zero exceedances and fails; an inflated tail produces too many and also fails                                                                                |

### G.4 Topic and payload tests

| Test                                    | Assertion                                                                                                                                                                                                                                                                                                                                   |
|-----------------------------------------|---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| `test_topic_uniqueness`                 | Instantiate every shipped facility profile; assert every rendered UNS topic is unique across all devices and all catalog entries. Fails on collision with both colliding entries named                                                                                                                                                      |
| `test_topic_well_formed`                | Every rendered topic matches the level regex, has exactly six levels (with the parameter level allowed to be multi-segment), contains no MQTT wildcard, has no empty level, no leading or trailing slash, and is under 512 bytes                                                                                                            |
| `test_sparkplug_topic_well_formed`      | Every Sparkplug topic matches `spBv1.0/{group}/{type}/{node}[/{device}]` with a valid message type                                                                                                                                                                                                                                          |
| `test_alias_uniqueness_and_determinism` | Within an edge node session, aliases are unique across the node's whole metric set, start at 1, and never include 0. Two runs at the same seed on the same platform produce identical alias assignments, and a third run under a different `PYTHONHASHSEED` produces the same assignments, which is what proves the sort is explicit (D-03) |
| `test_alias_reassignment_on_rebirth`    | A rebirth with a changed metric set is handled by the consumer; a consumer caching aliases across the birth boundary is shown to break, and the historian does not                                                                                                                                                                          |
| `test_datatype_matches_shape`           | For every entry, the datatype the derivation function produces equals the datatype recorded in a hand-written golden table checked into the test fixtures. Comparing the derivation against itself would pass whatever the function did (D-12), so the expected value is written by a person and reviewed                                   |
| `test_payload_roundtrip`                | Encode a sample, decode it, and assert the value, datatype, unit property, `Quality`, `sensor_type_id`, and `sensor_type_revision` survive intact under both the Sparkplug and JSON fallback profiles                                                                                                                                       |
| `test_payload_within_budget`            | Encoded payload size is within `validation.budget.max_payload_bytes` for every entry                                                                                                                                                                                                                                                        |
| `test_sequence_gap_detected`            | Drop a message from a stream and assert the Sparkplug `seq` gap detector raises a data-loss finding, including across the 255 to 0 wrap, where a naive comparison sees a gap of 254                                                                                                                                                         |

### G.5 Capability wiring tests

| Test                               | Assertion                                                                                                                                                                                                                                                  |
|------------------------------------|------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| `test_no_orphan_sensors`           | Every entry's `capability.unlocks` is non-empty, every id resolves in `capabilities.yaml`, and every capability is declared as a dependency by at least one subsystem in the subsystem registry. A sensor whose capability nobody consumes fails the build |
| `test_no_orphan_capabilities`      | Every capability in `capabilities.yaml` has at least one producing sensor type. A capability nothing feeds fails the build                                                                                                                                 |
| `test_consumed_by_is_truthful`     | Each subsystem named in `consumed_by` declares the capability in its own manifest. Catches a one-directional claim                                                                                                                                         |
| `test_capability_graph_acyclic`    | The type-to-capability-to-subsystem graph has no cycles                                                                                                                                                                                                    |
| `test_every_subsystem_has_sensors` | Every twin subsystem that declares sensor dependencies has at least one instantiated type serving it in at least one shipped facility profile                                                                                                              |

### G.6 Property-based invariants

Run under Hypothesis-class generation, at high sample counts, in the C4 property tier.

| Invariant                                                                                                       | Scope                                                                                                                         |
|-----------------------------------------------------------------------------------------------------------------|-------------------------------------------------------------------------------------------------------------------------------|
| Declared physical bounds hold                                                                                   | Every entry's `validation.physical_bounds` expressions, over 10^6 samples per entry per shift of the conditioning state       |
| Monotone channels never decrease                                                                                | Every `counter_totalizer` channel across a full simulated run including a device restart                                      |
| Dew point never exceeds ambient                                                                                 | The derived channel and its two parents                                                                                       |
| State of charge stays in `[0, 1]` and the pack energy balance closes                                            | Battery entries, across charge and discharge cycles                                                                           |
| Relative humidity stays in `[0, 100]`                                                                           | All humidity channels                                                                                                         |
| Read counts never exceed inventory rounds, and never fall below zero                                            | RFID entries; a bounded count family cannot leave [0, n]                                                                      |
| Angles wrap correctly                                                                                           | All circular channels, across the wraparound boundary                                                                         |
| Sim-time is monotone per device                                                                                 | All entries; requirement C2                                                                                                   |
| Same seed on the same platform yields an identical stream hash                                                  | All entries; the byte-identical tier of C1 under D-05                                                                         |
| Same seed across platforms yields identical business events and continuous fields inside the measured tolerance | All entries; the value-equivalent tier of C1 under D-05. The job reports observed maximum divergence rather than asserting it |

### G.7 Budget and scaling tests

| Test                          | Assertion                                                                                                                                                                                                                   |
|-------------------------------|-----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| `test_generator_cost`         | Per-sample generator cost within `validation.budget.max_generator_cost_us_per_sample` on the stated reference hardware, measured over a warm loop                                                                           |
| `test_full_fleet_fits_budget` | The full shipped enterprise profile's aggregate event rate and byte rate are within the declared A4 load-test envelope                                                                                                      |
| `test_ci_walltime`            | The pull-request-tier catalog suite completes within the declared CI budget                                                                                                                                                 |
| `test_ci_budget_arithmetic`   | The declared per-test sample counts, multiplied out across the shipped catalog, produce a projected wall time inside the job budget. A catalog that grows past its budget fails as a defect rather than as a timeout (D-13) |

### G.8 The CI budget arithmetic

D-13 rules that a timing test is scoped to fit its budget, that the clamp lives in the generator rather than only in the config validator, and that a budget test asserts the arithmetic so a suite that grows past its job budget fails as a defect rather than as a timeout. The fit suite is the part of this section that can outgrow its budget, so the arithmetic is written down.

| Quantity                   | Pull-request tier | Nightly tier | Where it comes from                                      |
|----------------------------|-------------------|--------------|----------------------------------------------------------|
| Entries exercised          | 80                | 80           | The implemented count, recomputed from disk              |
| Fit gates per entry, mean  | 3                 | 3            | Counted from `validation.goodness_of_fit` across entries |
| Samples per gate           | 5000              | 200000       | `n_samples`, with the pull-request tier scaled down      |
| Calibration draws per gate | 0                 | 1000         | G.2.2; the null distribution is recalibrated nightly     |
| Total draws                | 1.2e6             | 4.8e10       | Entries times gates times samples times draws            |

The pull-request tier is a smoke tier and its power is stated rather than implied: at 5000 samples a gate detects a 10 percent parameter shift at the power the calibration job measures and publishes, and it does not detect smaller shifts. A defect smaller than that reaches the nightly tier and is caught within 24 hours. That is the trade F.2.4 describes, made numeric.

Two clamps hold the arithmetic. `n_samples` has a generator-side ceiling in the pull-request tier, so an entry cannot request a sample count that blows the job budget by writing a large number in its own file. And `test_ci_budget_arithmetic` recomputes the table above from the shipped catalog and fails when the projection exceeds the job budget, which makes catalog growth a reviewable event rather than a slow slide into a timing-out job.

The nightly draw count is large because calibration is expensive, which is why it is nightly. The calibrated null distributions are cached by (family, parameter set, sample count) and recomputed only when one of those three changes, so the steady-state nightly cost is far below the figure above and the figure above is the cold-cache worst case.

---

## H. Phase placement

Sensor categories grow with the subsystems that consume them. A category that lands before its consumer is a fleet of devices publishing into nothing, which is the specific failure this table exists to stop. The phase ids are those of `docs/design/roadmap.md` and `test_phase_resolves` checks each one against it.

| Category                                 | Phase | The subsystem that makes it consumable                                              |
|------------------------------------------|-------|-------------------------------------------------------------------------------------|
| Warehouse and logistics, first two types | P1    | The walking skeleton: one RFID portal and one temperature probe on UNS topics       |
| Industrial equipment                     | P3    | Component 3 fleet management and predictive maintenance                             |
| Environmental and facility               | P3    | Facility health findings, and the ambient reference every compensated channel needs |
| Warehouse and logistics, rest            | P3b   | Component 1b: AMR fleet, palletizer, ASRS, sortation, slotting                      |
| Electrical and power                     | P3b   | The same, plus the energy KPIs that E7 puts ahead of it                             |
| Transportation and fleet                 | P3h   | Component 6a7 transportation network and the cold-chain capability                  |
| Process and chemical                     | P3i   | The upstream factory's continuous and batch stage                                   |
| Safety and compliance                    | 6a10  | Component 6a10 safety and ergonomics, which owns the severity floor                 |
| Structural                               | 6a10  | The same, plus the snow-load scenario that the roof load type serves                |

Three consequences of that ordering are worth stating, because each is a dependency that would otherwise be discovered late.

The schema itself lands at P3 with the first two categories, but the two P1 types are instantiated before the schema exists as a loader. They are hand-written in the walking skeleton and migrated onto the loader when it arrives, and the migration is a work package rather than an afterthought: `test_p1_types_survive_migration` asserts the two types publish the same topics and the same payload fields before and after.

The safety category is the last to land and it carries the severity floor, which several earlier layers reference. The floor is a findings-contract feature from component 5 onward, not a safety-category feature, and the safety entries set a field the contract already understands.

Every entry's `phase` field is the phase of the earliest subsystem that consumes it, not the phase of its category. `rtd_pt100` is an industrial-equipment type with `phase: P1`, because the walking skeleton's temperature probe is one, and the category it belongs to lands at P3 around it.

### H.1 When the fleet reaches fifty devices

The source requires at least fifty simulated edge devices, and that count is a product of this section rather than a number set somewhere else: a device exists because a catalog entry's `attaches_to.binding` and `attaches_to.cardinality` cause a facility profile to instantiate one.

`test_shipped_profile_device_count` instantiates each shipped facility profile and asserts the device count. The micro-fulfillment profile at P1 is below fifty on purpose, because a walking skeleton with fifty devices is not a walking skeleton. The growth-tier profile crosses fifty at P3b, once the warehouse and electrical categories have landed and component 1b has the subsystems for them to attach to, and the test asserts the floor from that phase onward rather than from the start.

The count is asserted per profile and per phase, so a profile that quietly loses devices when a category is re-binned fails the build instead of drifting under the requirement.

---

## I. Open questions

These are genuinely undecided. Each has at least two defensible answers and none is resolved by asserting a preference here.

### OQ-1. Matrix representation for the thermal array

The numeric half of this question is settled. The array datatype enum values are read from the Sparkplug Specification 3.0.0 payload definition and recorded in D.3.2: `FloatArray` is 30, `DataSet` is 16, and the scalar assignments this section already used were correct.

The modeling half is open. For the 32x24 thermal array, a flattened `FloatArray` with `rows` and `cols` in the metric properties is compact and simple. A `DataSet` is self-describing and idiomatic for tabular data and heavier on the wire. A third option publishes only the derived scalars, maximum, mean, and hot-spot coordinates, on the UNS and keeps the full frame in the historian as a side channel, which is the only one of the three that changes the payload budget by an order of magnitude rather than a percentage.

The decision belongs to the E3 milestone and it moves `max_payload_bytes` for the thermal entry, so the budget test is written against whichever option is chosen rather than against a number picked first.

### OQ-2. Are derived channels catalog entries or historian computations

`env.dewpoint.derived` is computed from a temperature and humidity pair. Publishing it as a first-class UNS topic makes it visible to any subscriber and keeps the semantic layer uniform, at the cost of publishing redundant information and of two sources of truth if a consumer computes it independently. Computing it in the historian keeps the wire clean but means the dashboard and the agent have to know a derivation rule that is not in the catalog. The current draft publishes it as a catalog entry with a `derived` marker, which is a defensible default and not a settled one. The same question applies to power (derived from voltage and current), dew point, temperature-normalized tire pressure, and corrosion rate.

### OQ-3. UNS placement of mobile assets

Section D.1 places trucks, trailers, and AMRs under a `fleet` pseudo-area within the dispatching site. This preserves the six-level shape at the cost of calling something an area that is not one, and it means a trailer's topic changes when it is reassigned between sites. The alternative is a parallel top-level branch (`twinflow/fleet/...`) that is honest about being outside the ISA-95 hierarchy but breaks the uniform six-level structure every subscriber and every wildcard subscription depends on. A third option follows the asset (topic changes as it moves), which is the most physically accurate and the worst for historians. This is a modeling decision with no clean answer, and reviewers who run industrial IoT will have a view on it.

### OQ-4. Is a vision-derived channel a sensor

`saf.ppe.vision_compliance` publishes like a sensor and attaches to the twin like a sensor, but its failure modes are model failure modes (class confusion, domain shift, calibration drift) rather than transducer failure modes, and its "calibration" is a training run. Putting it in the catalog keeps one uniform representation and lets the same machinery handle it. Keeping it out draws a cleaner line between measurement and inference. The current draft includes it with an `inference_channel` profile, and flags that this decision determines whether the MLOps layer (E43) or the fleet health layer owns its lifecycle.

### OQ-5. Raw waveform capture policy for vibration

Genuine bearing analysis needs sampling in the tens of kilohertz. Streaming that from even fifty devices is not laptop-scale, so the catalog computes band features on-device (tier 0 in the E36 model) and publishes those at 1/60 Hz, with raw capture available on demand or on alarm. Three things are unresolved: whether the on-demand capture is published to the UNS at all or fetched over the REST API, whether the tier-0 FFT claim is honest given that the simulated device is a Python process rather than a constrained MCU, and whether the ESP32 hardware-in-the-loop device (E47) can do the same computation, because if it cannot then the tier-0 claim is aspirational for the one device that would prove it.

### OQ-6. Independent or correlated failure onset

Failure onset is currently drawn per device independently. Real fleets fail in correlated ways: a bad batch of sensors, a firmware regression, a humid summer, a single contractor who mounted forty gauges the same wrong way. Modeling a shared latent health state would be markedly more realistic and would give the fleet-health layer genuinely hard work. It would also break the independence assumption the goodness-of-fit tests rely on, requiring the fit suite to condition on the latent state or to test the joint distribution instead. The realism gain is large and the test-complexity cost is real.

### OQ-7. Unit representation

UCUM codes are machine-checkable and support automatic conversion, which is what makes the cross-check and MSA layers possible without hand-written conversions. They are also verbose and unfamiliar (`mm/s` is fine, `ug/m3` and `mS/cm` less so, and dimensionless quantities are genuinely awkward). The alternative is a small curated unit enum with a hand-maintained conversion table, which is friendlier to read and requires maintenance. The current draft uses UCUM.

### OQ-8. Device profile layer above the catalog

A Type K thermocouple from vendor A and one from vendor B have the same physics and different tolerance classes, drift rates, and time constants. The current schema puts those numbers in the type entry, which means a facility cannot model a mixed-vendor fleet without duplicating the type. A separate `device_profile` layer (type plus vendor-specific parameter overrides) solves it and roughly doubles the config surface. Eighty types do not need it. Three hundred might, and the decision costs less now than after three hundred entries carry vendor numbers inline.

### OQ-9. Where calibration state lives

Calibration due dates, last-calibration values, and as-found and as-left readings are instance properties, not type properties. They belong somewhere, and the candidates are the device registry (which is where a fleet manager would look), the catalog instance binding in `facility.yaml`, or a separate calibration record store that the MSA layer owns. This matters because the MSA stability study needs the calibration history to interpret a drift finding, and because a calibration event is exactly the kind of change the SPC layer needs correlated against a bias step.

### OQ-10. Whether planned entries belong in the catalog

The schema allows `status: planned` so the roadmap for later sensor categories lives beside the implemented ones. This is good for the "system under construction with a known destination" story that the repository is deliberately telling. It also means the catalog directory count is not the implemented count, which makes the README count assertion slightly more complex and creates a way for the catalog to look larger than it is. The current draft permits it and makes CI count only `implemented` entries for every published number.

### OQ-11. Which section owns the catalog entry schema

`docs/design/iot-fleet.md` section 3.1 and this section both specify the catalog entry, and they do not agree. Neither is wrong on its own terms and only one can ship.

| Surface          | This section                                      | iot-fleet 3.1                                        |
|------------------|---------------------------------------------------|------------------------------------------------------|
| File layout      | One file per type under a category directory      | One file per category holding a list of entries      |
| Identifier field | `id`, dot-delimited, lowercase with dots          | `type_id`, snake case, no dots                       |
| Unit of a type   | One measurement, with `measurement.channel_shape` | One device, with a `channels` list                   |
| Capability field | `capability.unlocks` and `capability.consumed_by` | `capability_unlocks`                                 |
| Attachment       | `attaches_to.subsystem` plus a binding level      | `attaches_to` as a single resource-selector string   |
| Category split   | 14, 7, 15, 12, 10, 8, 9, 5                        | 12, 8, 18, 10, 8, 9, 10, 5                           |
| Model vocabulary | Distribution families per channel                 | Twelve named signal-model kinds, capped by INV-CAT-3 |

The two category splits both total 80 and both cover the categories the source requires, so the disagreement is not arithmetic. It is the third row: whether a type is a measurement or a device. Every other row follows from that one.

Three ways to settle it. Adopt the device-shaped entry, which matches the package that owns the loader and gives a multi-channel device one identity, at the cost of re-binning this section's eighty rows and folding three vibration measurements into one type's channels. Adopt the measurement-shaped entry, which keeps the per-measurement physics intact, at the cost of contradicting the section that owns the package boundaries. Or keep both, with the device-shaped entry as the file format and the measurement-shaped entry as a generated view, which costs a generator and a round-trip test.

This is a program decision. It is recorded rather than settled by assertion, because choosing between two designed schemas on no evidence is how a contradiction turns into a silent drift. It belongs in DOCTRINE.md as a ruling, since it is the class of defect that document exists to settle: one contract stated twice in different words.

### OQ-12. Four failure modes have no fault id

`bias_step`, `saturation`, `transition_loss`, and `array_dead_pixel` appear in the class profiles of C.1 and have no entry in the fault catalog of `docs/design/variability-and-faults.md` section C.4, so nothing can inject them and no test can score them.

Each is a registration request against that catalog, and each carries a design question. A bias step and a calibration loss differ only in whether the change is a step or a ramp, so one parameterized fault may cover both. Saturation is arguably an effect of an existing fault at extreme parameters rather than a fault of its own. Transition loss on a discrete state is the same observation as stuck-at seen through a different detector, and whether it earns a separate id depends on whether the scoring harness needs to tell the two apart. An array dead pixel has no analog in the current catalog at all.

Until they are registered, an entry whose profile supplies one of them cannot reach `status: implemented`, which is the rule A.7 applies to parameters, applied here for the same reason.

### OQ-13. The tier-D parameter backlog

A.7 blocks `status: implemented` on any entry carrying a tier-D parameter group, and at the time of writing most entries carry one. The noise and drift parameters across the catalog are modeling assumptions with no external source, and the annotated entry in A.2 says so in its own provenance block rather than hiding it.

That backlog is large and it is the real cost of rule 3. Three questions are open. Whether a modeling assumption with a stated derivation from a sourced quantity counts as tier B or stays tier D, which decides how much of the backlog closes by writing derivations rather than by finding sources. Whether a vendor datasheet, a primary text but a commercial one that can be withdrawn, is tier A or tier C. And what the release gate does when one category is fully sourced and another is not, since a release that ships half the catalog as `planned` is honest and awkward at once.

The count of tier-D groups goes in the release notes rather than staying private, so the backlog shrinking is visible and the backlog not shrinking is visible too.

### OQ-14. What external reference grounds the spectral energy threshold

The spectral content gate in G.2 asserts that at least a declared fraction of band energy falls within a declared halfwidth of the computed defect frequency. That threshold is a repository-set design parameter. D-11 permits a design parameter to be recorded as one and does not permit it to be presented as a validated figure.

So the question is what would ground it. A published vibration-analysis reference stating the expected energy concentration at a defect frequency for a given bearing condition would do it. A measured figure from an open bearing-fault dataset with labeled conditions would also do it, and would give the signature classifier a real external benchmark as well, which is worth more than the threshold itself. Absent either, the gate stays a design parameter with a `SRC-REPO-MODEL` provenance row, and G.2.2 says so where the gate is defined.
