"""The five entities, as models.

Every rule that can be expressed as a type is expressed as one here rather than
as a check in the loader, because a type refuses the value at construction and a
check only refuses it if somebody remembers to call the check.

The status enums are the clearest case. `WorkPackage.status` has no `canceled`
member and `Requirement` has no status field at all, so "nothing is ever cut" is
a property of the type rather than a promise in a document. A contributor who
wants to cancel a work package has to edit this file, which is a reviewed diff.
"""

from __future__ import annotations

import re
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

#: The closed set of phase identifiers. A closed set rather than a pattern, and
#: the choice is deliberate: a pattern admitting `E\d+` lets a requirement id
#: pass as a phase id, and a validator reading a dependency list then cannot
#: tell which namespace a token belongs to. Adding a phase is an edit here and a
#: reviewed diff, which is the correct cost of adding a release.
PHASE_IDS: tuple[str, ...] = (
    "P0",
    "P1",
    "P2",
    "P3",
    "P3b",
    "P3c",
    "P3d",
    "P3e",
    "P3f",
    "P3g",
    "P3h",
    "P3i",
    "ECON",
    "6a10",
    "6a11",
    "ROST",
    "6a12",
    "RISK",
    "6a13",
    "6a14",
    "OTDRILL",
    "6a15",
    "CAUSAL",
    "6a16",
    "SOE",
    "6a17",
    "P4",
    "P5",
    "P6-W1",
    "P6-W2",
    "P6-W3",
    "P6-W4",
    "P6-W5",
    "P6-W6",
)

#: The alternation exists because the six P6-Wn phases are the only phase ids
#: carrying a hyphen. Their branch is tried first, so `WP-P6-W6-01` parses as
#: phase `P6-W6` and ordinal `01`. No phase id ends in a hyphen followed by two
#: digits, which is what makes the final segment unambiguous.
WORK_PACKAGE_ID = re.compile(r"^WP-(P6-W[1-6]|[A-Za-z0-9]+)-(\d{2})$")

#: Semver as C9 uses it. The tag carries a leading v; the version does not.
RELEASE_TAG = re.compile(r"^v(\d+)\.(\d+)\.(\d+)$")

#: A split label is its requirement id followed by one lower-case letter. E4a
#: belongs to E4 and to nothing else, which is what lets a note be checked
#: against the requirement it sits on.
SPLIT_LABEL = re.compile(r"^([A-Za-z0-9]+?)([a-z])$")

Tier = Literal[
    "component",
    "bleeding_edge",
    "craft",
    "adoption",
    "reference_arch",
    "constraint",
]

#: Four values, and there is no fifth. `canceled` is absent by construction,
#: not by convention, and a test asserts the literal set.
WorkPackageStatus = Literal["planned", "in_progress", "done", "reordered"]

GateKind = Literal["validation", "ground_truth", "invariant", "budget", "policy"]

GateStatus = Literal["declared", "specified", "implemented"]


class Frozen(BaseModel):
    """Every model is frozen and refuses an unknown key.

    `extra="forbid"` is what makes a typo fail the load rather than being
    silently dropped. A misspelled `partal: true` that loads as an absent flag
    is the coverage proof passing over a requirement nobody placed.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")


class Requirement(Frozen):
    """One atom of the source, extracted once and frozen.

    There is no status field. An idea that turns out to belong somewhere else is
    reordered in roadmap.yaml, and the resequencing register records the move.
    """

    id: str
    tier: Tier
    title: str = Field(min_length=1)
    #: The line the clause sits on in the source document, where that document
    #: is available. Absent is legal; zero or negative is not.
    source_line: int | None = Field(default=None, gt=0)
    #: The clause that defines this requirement, verbatim, so the plan cannot
    #: drift from the ask. Absent is legal and empty is not: an empty quote
    #: would pass the append-only diff check while carrying nothing.
    quote: str | None = Field(default=None, min_length=1)
    #: True where this requirement lands in more than one phase under a lettered
    #: label. The labels themselves live in splits.yaml.
    splittable: bool = False
    #: The lettered sub-items the source itself writes, where it writes any.
    #: E26 is the only one: the source carries E26(a) through E26(g), so seven
    #: identifiers are placed against one numbered entry. This is not the same
    #: thing as splittable, which is this repository dividing one source atom
    #: across phases, and the coverage proof prints the two counts separately
    #: because one number could not tell them apart.
    source_sub_items: list[str] = Field(default_factory=list)


class Split(Frozen):
    """One lettered half of a split requirement.

    A split label is never a requirement id. requirements.yaml holds source
    atoms only, and E4a has no source line and no verbatim clause because the
    source has only E4. This is the file that reconciles the two.
    """

    requirement: str
    work_package: str
    title: str = Field(min_length=1)


class Coverage(Frozen):
    """One requirement, covered by one work package.

    A bare string cannot carry `partial`, so a bare string is a load error
    rather than a coverage entry that silently claims to be the last one.
    """

    id: str
    #: True means a later work package also covers this id. The last covering
    #: work package carries false, and that is the invariant the coverage proof
    #: reads.
    partial: bool = False
    #: Required when partial is true. Where the requirement has split labels,
    #: the note opens with the label it lands under.
    note: str | None = Field(default=None, min_length=1)

    @field_validator("id")
    @classmethod
    def _id_is_not_a_split_label(cls, value: str) -> str:
        # A coverage entry names a source atom. E4a reaches a work package
        # through the note and through splits.yaml, never through this field,
        # which is what lets the append-only diff over requirements.yaml stay
        # absolute.
        return value


class WorkPackage(Frozen):
    """The unit of build, the unit of an issue, and the unit of a commit series."""

    id: str
    title: str = Field(min_length=1)
    phase: str
    #: Ordering inside a phase. Equal waves may run in parallel, so a dependency
    #: between two work packages at the same wave is a load error.
    wave: int = Field(ge=1)
    covers: list[Coverage] = Field(default_factory=list)
    depends_on: list[str] = Field(default_factory=list)
    #: Concrete artifacts: a module path, a config key, a command, or a doc
    #: page. Empty is legal only outside the open phase and the next one, where
    #: the work has not been designed yet.
    deliverables: list[str] = Field(default_factory=list)
    gates: list[str] = Field(default_factory=list)
    brick: str | None = None
    release: str
    github_issue: int | None = None
    status: WorkPackageStatus = "planned"
    #: Required when status is reordered, and the only way an item leaves a
    #: phase.
    moved_to: str | None = None
    reason: str | None = None

    @property
    def parsed_id(self) -> tuple[str, int] | None:
        match = WORK_PACKAGE_ID.match(self.id)
        if match is None:
            return None
        return match.group(1), int(match.group(2))


class Phase(Frozen):
    """One release.

    `exit_gates` is absent by design. It is derived from the gate registry, and
    authoring it here is a load error, so the phase table and the registry
    cannot drift apart.
    """

    id: str
    name: str = Field(min_length=1)
    delivers: str = Field(min_length=1)
    #: Phase ids only. Two dependency fields rather than one, because the
    #: ordering arguments mix the two namespaces freely and a single list leaves
    #: the validator guessing which one a token belongs to.
    depends_on_phases: list[str] = Field(default_factory=list)
    #: Requirement ids only.
    requires_requirements: list[str] = Field(default_factory=list)
    release_tag: str
    quickstart_budget_s: int = Field(default=300, ge=1, le=600)
    demo_budget_s: int = Field(default=600, ge=1, le=900)


class Gate(Frozen):
    """One phase-exit assertion.

    The required-field set is scoped by status, because a gate declared at
    Phase 0 has no test on disk and no assertion yet, and a checker that
    demanded both at Phase 0 would make declaring the whole set early
    impossible to satisfy.
    """

    id: str
    kind: GateKind
    status: GateStatus = "declared"
    first_phase: str
    standing: bool = False
    owner_section: str = Field(min_length=1)
    #: A named artifact published outside this repository, with edition and
    #: locator. Required on a validation gate at status specified or better:
    #: this repository is never a reference for itself.
    reference: str | None = None
    reference_url: str | None = None
    #: The generating process and the seed set, for a ground-truth gate.
    truth_source: str | None = None
    #: The null a ground-truth gate must beat. A ground-truth gate with no null
    #: cannot fail honestly.
    null_model: str | None = None
    #: The measured dispersion of a stochastic quantity, and the floor its
    #: tolerance sits above.
    noise_floor: str | None = None
    assertion: str | None = None
    #: The observation that fails this gate, in one sentence.
    falsified_by: str | None = None
    test_path: str | None = None

    def required_fields(self) -> tuple[str, ...]:
        """What this gate owes at its declared status."""
        if self.status == "declared":
            return ()
        common = ("assertion", "falsified_by")
        by_kind = {
            "validation": ("reference", "reference_url"),
            "ground_truth": ("truth_source", "null_model", "noise_floor"),
            "invariant": (),
            "budget": ("noise_floor",),
            "policy": (),
        }
        return common + by_kind[self.kind]


class Release(Frozen):
    """A tag, and the compatibility promises it carries."""

    tag: str
    phase: str
    changelog_section: str
    loads_recorded_runs: list[str] = Field(default_factory=list)
    loads_configs: list[str] = Field(default_factory=list)
    headline_metric: dict = Field(default_factory=dict)


def semver(tag: str) -> tuple[int, int, int] | None:
    match = RELEASE_TAG.match(tag)
    if match is None:
        return None
    return int(match.group(1)), int(match.group(2)), int(match.group(3))
