"""The `ops.release.tagged.v1` contract, and the two gates that read it.

Step 12 of the release ritual publishes this record. VAL-GATE-RELBUD-001 reads
the ritual duration off it, and step 8 compares the README headline block
against `headline_metric`. Both reads are only as good as the schema's refusals,
so those are what this file pins: a record that publishes a headline number
without the seed and the run id behind it, or that omits the duration the budget
gate measures against, is not a record either gate can use.

The schema is hand-written rather than generated, because no Python model
produces it: the release workflow does, and `tools/gen_schemas.py` generates only
the subjects that have a model. That is why the shape is asserted here instead of
by a round trip through a model.
"""

from __future__ import annotations

import json
from pathlib import Path

import jsonschema
import pytest
import yaml

REPO_ROOT = Path(__file__).resolve().parents[1]
SCHEMAS_DIR = REPO_ROOT / "schemas"
SCHEMA_PATH = SCHEMAS_DIR / "ops" / "release_tagged" / "v1.json"
SUBJECT_KEY = "ops/release_tagged"


def schema() -> dict:
    return json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))


def registry() -> dict:
    return yaml.safe_load((SCHEMAS_DIR / "registry.yaml").read_text(encoding="utf-8"))


def record(**overrides) -> dict:
    base = {
        "schema_version": "1.0",
        "tag": "v0.2.0",
        "phase": "P1",
        "commit": "a" * 40,
        "headline_metric": {
            "name": "historian_stored_bytes_per_sensor_reading",
            "value": 214.5,
            "unit": "byte/reading",
            "seed": 20260813,
            "run_id": "run_c06582847eb755374c6871b6eec595ca",
            "artifact": "artifacts/measured/historian_stored_bytes_per_sensor_reading.json",
        },
        "ritual": {
            "duration_s": 2410.5,
            "ceiling_s": None,
            "margin_ratio": 1.25,
            "noise_floor_s": None,
            "reference_runner": {"label": "ubuntu-24.04", "image_version": None},
            "steps": [
                {"id": "check", "measured_s": 88.0, "budget_s": 90.0},
                {"id": "e1-replay", "measured_s": None, "arrives_with": "P2"},
            ],
        },
        "provenance": {
            "tagged_wall_utc": "2026-08-13T09:00:00Z",
            "workflow_run_url": "https://example.invalid/runs/1",
        },
    }
    base.update(overrides)
    return base


def validate(instance: dict) -> None:
    jsonschema.validate(instance=instance, schema=schema())


def test_the_registry_declares_this_subject():
    entry = registry()["subjects"][SUBJECT_KEY]
    assert entry["versions"][0]["file"] == "ops/release_tagged/v1.json"
    assert entry["versions"][0]["status"] == "current"


def test_the_subject_is_published_from_the_tag_the_gate_that_reads_it_stands_at():
    """VAL-GATE-RELBUD-001 is first standing at P1, which roadmap.yaml tags v0.2.0."""
    gates = yaml.safe_load((REPO_ROOT / "gates.yaml").read_text(encoding="utf-8"))
    relbud = gates["gates"]["VAL-GATE-RELBUD-001"]
    roadmap = yaml.safe_load((REPO_ROOT / "roadmap.yaml").read_text(encoding="utf-8"))
    tag = next(
        phase["release_tag"] for phase in roadmap["phases"] if phase["id"] == relbud["first_phase"]
    )
    assert registry()["subjects"][SUBJECT_KEY]["versions"][0]["since"] == tag.lstrip("v")


def test_the_schema_declares_the_dialect_the_registry_names():
    assert schema()["$schema"] == registry()["dialect"]


def test_the_schema_is_valid_against_its_own_dialect():
    document = schema()
    validator = jsonschema.validators.validator_for(document)
    validator.check_schema(document)


def test_a_well_formed_record_validates():
    """The pass case. Without it every refusal below could be a broken schema."""
    validate(record())


def test_the_ritual_duration_the_budget_gate_reads_is_required():
    """VAL-GATE-RELBUD-001 has nothing to assert against if this may be omitted."""
    broken = record()
    del broken["ritual"]["duration_s"]
    with pytest.raises(jsonschema.ValidationError):
        validate(broken)


def test_a_ritual_duration_of_zero_is_refused():
    """A ritual that took no time did not run, and did not measure itself either."""
    broken = record()
    broken["ritual"]["duration_s"] = 0
    with pytest.raises(jsonschema.ValidationError):
        validate(broken)


def test_a_null_ritual_duration_is_refused():
    """Published whatever it is, per the gate's own assertion. Null is not a value."""
    broken = record()
    broken["ritual"]["duration_s"] = None
    with pytest.raises(jsonschema.ValidationError):
        validate(broken)


def test_an_unmeasured_ceiling_is_allowed_to_be_null():
    """ci_budget.yaml carries ceiling_s null until every step has been measured."""
    validate(record())


@pytest.mark.parametrize("field", ["name", "value", "unit", "seed", "run_id", "artifact"])
def test_the_headline_metric_carries_every_part_of_its_attribution(field):
    """Step 8 compares README against all four of value, unit, seed, and run id."""
    broken = record()
    del broken["headline_metric"][field]
    with pytest.raises(jsonschema.ValidationError):
        validate(broken)


def test_a_headline_value_that_is_a_string_is_refused():
    """A number rendered as text is a number nobody can compare or average."""
    broken = record()
    broken["headline_metric"]["value"] = "214.5"
    with pytest.raises(jsonschema.ValidationError):
        validate(broken)


def test_a_null_headline_value_is_refused():
    """There is no placeholder here. A release with no measured number does not tag."""
    broken = record()
    broken["headline_metric"]["value"] = None
    with pytest.raises(jsonschema.ValidationError):
        validate(broken)


def test_a_headline_metric_name_carrying_dots_is_refused():
    """A marker name is not an entry in the governed-metric identifier space."""
    broken = record()
    broken["headline_metric"]["name"] = "historian.rows.stored_bytes"
    with pytest.raises(jsonschema.ValidationError):
        validate(broken)


def test_a_short_commit_sha_is_refused():
    """A prefix that is unique today collides as the history grows."""
    broken = record()
    broken["commit"] = "a" * 7
    with pytest.raises(jsonschema.ValidationError):
        validate(broken)


def test_a_tag_without_its_leading_v_is_refused():
    """roadmap.yaml writes release_tag with the v, and one spelling is enough."""
    broken = record()
    broken["tag"] = "0.2.0"
    with pytest.raises(jsonschema.ValidationError):
        validate(broken)


def test_an_unknown_field_is_refused():
    """additionalProperties false, so a producer cannot smuggle a field past review."""
    broken = record()
    broken["headline_metric"]["estimate"] = True
    with pytest.raises(jsonschema.ValidationError):
        validate(broken)


def test_a_step_may_report_that_it_did_not_run():
    """Null is not zero. Release-only steps arrive one phase at a time."""
    instance = record()
    instance["ritual"]["steps"] = [{"id": "load-harness", "measured_s": None}]
    validate(instance)


def test_the_step_list_may_not_be_empty():
    """A ritual with no steps cannot name the step that grew."""
    broken = record()
    broken["ritual"]["steps"] = []
    with pytest.raises(jsonschema.ValidationError):
        validate(broken)


def test_the_runner_the_durations_were_measured_on_is_required():
    """A runner change moves every duration at once, so it travels with them."""
    broken = record()
    del broken["ritual"]["reference_runner"]
    with pytest.raises(jsonschema.ValidationError):
        validate(broken)


def test_every_step_id_in_ci_budget_is_expressible_here():
    """The two files name one set of steps, so a record can carry the whole ritual."""
    budget = yaml.safe_load((REPO_ROOT / "ci_budget.yaml").read_text(encoding="utf-8"))
    steps = [
        {"id": step["id"], "measured_s": step["measured_s"]} for step in budget["release"]["steps"]
    ]
    instance = record()
    instance["ritual"]["steps"] = steps
    validate(instance)


def test_the_wall_clock_instant_sits_in_the_provenance_half():
    """Doctrine D-01: wall time and machine identity are gathered, not scattered."""
    document = schema()
    assert "tagged_wall_utc" in document["$defs"]["provenance"]["properties"]
    assert "tagged_wall_utc" not in document["properties"]
