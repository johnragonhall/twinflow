"""Schema compatibility rules: the section 5.5 table as code.

These live in the package rather than in a script because they are part of the
schemas contract. A consumer deciding whether it can read a newer version asks
the same question CI asks, and both should get the answer from one place.

Two rows are worth restating, because both are counter-intuitive and both are
deliberate.

Making a required property optional is rejected. That reads like a loosening,
and it is, for the producer. For a consumer that assumed the field was always
present it is a break, and a silent one.

Widening a numeric range is rejected unless the field carries
x-twinflow-open-range. A consumer that read divert_rate as a value in [0, 1] and
sized a fixed-point field to match breaks when the producer starts publishing
1.4, in exactly the way narrowing breaks a producer. The distinction is declared
by the producer at the field level, the same way x-twinflow-open-enum declares
it for enums.
"""

from __future__ import annotations

from typing import Any

OPEN_ENUM = "x-twinflow-open-enum"
OPEN_RANGE = "x-twinflow-open-range"

_LOWER_BOUNDS = ("minimum", "exclusiveMinimum", "minLength", "minItems")
_UPPER_BOUNDS = ("maximum", "exclusiveMaximum", "maxLength", "maxItems")


def _properties(schema: dict) -> dict[str, dict]:
    return schema.get("properties", {}) or {}


def _required(schema: dict) -> set[str]:
    return set(schema.get("required", []) or [])


def _type_of(prop: dict) -> Any:
    value = prop.get("type")
    if isinstance(value, list):
        return tuple(sorted(value))
    return value


def compare_schemas(old: dict, new: dict) -> list[str]:
    """Every incompatible change from old to new, as one line each."""
    findings: list[str] = []

    old_props, new_props = _properties(old), _properties(new)
    old_required, new_required = _required(old), _required(new)

    for name in sorted(old_props):
        if name not in new_props:
            findings.append(f"{name}: removed. Deprecate it and remove at the next major instead")
            continue

        before, after = old_props[name], new_props[name]

        if _type_of(before) != _type_of(after):
            findings.append(
                f"{name}: type changed from {_type_of(before)!r} to {_type_of(after)!r}"
            )

        # Enum membership. Losing a member always breaks a consumer; gaining one
        # breaks any consumer that did not opt into tolerating unknown members.
        old_enum, new_enum = before.get("enum"), after.get("enum")
        if old_enum is not None and new_enum is not None:
            removed = [member for member in old_enum if member not in new_enum]
            added = [member for member in new_enum if member not in old_enum]
            if removed:
                findings.append(f"{name}: enum members removed: {removed}")
            if added and not before.get(OPEN_ENUM, False):
                findings.append(
                    f"{name}: enum members added: {added}. Only a field carrying "
                    f"{OPEN_ENUM}: true may gain members within a major"
                )

        open_range = bool(before.get(OPEN_RANGE, False))
        for keyword in _LOWER_BOUNDS:
            if keyword in before and keyword in after:
                if after[keyword] > before[keyword]:
                    findings.append(
                        f"{name}: {keyword} narrowed from {before[keyword]} to {after[keyword]}"
                    )
                elif after[keyword] < before[keyword] and not open_range:
                    findings.append(
                        f"{name}: {keyword} widened from {before[keyword]} to {after[keyword]}. "
                        f"Only a field carrying {OPEN_RANGE}: true may widen"
                    )
            elif keyword in before and keyword not in after and not open_range:
                findings.append(f"{name}: {keyword} dropped, which widens the accepted range")

        for keyword in _UPPER_BOUNDS:
            if keyword in before and keyword in after:
                if after[keyword] < before[keyword]:
                    findings.append(
                        f"{name}: {keyword} narrowed from {before[keyword]} to {after[keyword]}"
                    )
                elif after[keyword] > before[keyword] and not open_range:
                    findings.append(
                        f"{name}: {keyword} widened from {before[keyword]} to {after[keyword]}. "
                        f"Only a field carrying {OPEN_RANGE}: true may widen"
                    )
            elif keyword in before and keyword not in after and not open_range:
                findings.append(f"{name}: {keyword} dropped, which widens the accepted range")

        if "pattern" in before and before.get("pattern") != after.get("pattern"):
            findings.append(
                f"{name}: pattern changed from {before.get('pattern')!r} to "
                f"{after.get('pattern')!r}. A pattern change is a type change to every consumer"
            )

        if name in old_required and name not in new_required:
            findings.append(
                f"{name}: was required and is now optional, which breaks every consumer "
                f"that assumed it was present"
            )

        if name not in old_required and name in new_required:
            findings.append(
                f"{name}: was optional and is now required, which rejects every event "
                f"an existing producer publishes without it"
            )

    for name in sorted(new_props):
        if name in old_props:
            continue
        if name in new_required:
            findings.append(f"{name}: added as required. Add it optional with a default instead")
        elif "default" not in new_props[name] and not _nullable(new_props[name]):
            findings.append(
                f"{name}: added without a default, so an old producer publishes an event "
                f"a new consumer cannot fill in"
            )

    return findings


def _nullable(prop: dict) -> bool:
    if prop.get("type") == "null":
        return True
    return any(option.get("type") == "null" for option in prop.get("anyOf", []) or [])
