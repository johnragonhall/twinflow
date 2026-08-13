"""`DashboardConfig`: the dashboard block of `facility.yaml`, as a model.

`docs/design/dashboard-replay.md` section 6.2 declares the block. This model
carries the part the stub uses and refuses the values that section marks as
errors, so a mis-authored config fails at load rather than at first render.

One field is not in that block: `api_base_url`. Requirement R32 says building
the dashboard against internal calls and inserting an API later rewrites every
dashboard test, so the dashboard reads `twinflow-api` over HTTP and needs the
origin to read it from. It is a deployment fact rather than a facility fact,
which is why it defaults to the loopback address the API binds by default and
never to a name that only resolves inside one network.
"""

from __future__ import annotations

import warnings
from datetime import datetime
from typing import Literal
from urllib.parse import urlsplit

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

#: The three legal tick rates, kept as literals rather than imported. Boundary
#: rule A1.4 gives `TickResolution` one owning package, `twinflow-kernel`, and
#: this package's dependency list is the four names section 2.1 of the design
#: fixes: starlette, uvicorn, pydantic, and twinflow-schemas. Taking a
#: dependency on the kernel to read three integers would trade the install-alone
#: claim of D-10 for a constant.
TICK_RESOLUTIONS: tuple[int, int, int] = (1_000, 1_000_000, 1_000_000_000)

#: Characters that end a content security policy directive or a header line.
#: `urlsplit` accepts all of them inside an authority, so the origin check reads
#: them separately rather than trusting the parse.
_FORBIDDEN_IN_ORIGIN: tuple[str, ...] = (";", ",", " ", "\t", "\r", "\n", "\x00", "'", '"')


class DashboardConfig(BaseModel):
    """One dashboard deployment, validated the way section 6.2 asks."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    bind: str = "127.0.0.1"
    port: int = Field(default=8080, ge=1024, le=65535)

    #: Where `twinflow-api` answers. Read by the browser, not by this process.
    api_base_url: str = "http://127.0.0.1:8000"

    mode: Literal["live", "replay"] = "live"

    #: The run this dashboard is attached to, and the sim epoch its commands are
    #: stamped against. Required rather than defaulted to the current instant,
    #: for the reason `StationLineSpec.epoch` gives: a default read from a wall
    #: clock puts a different value into two runs of one seed.
    run_id: str = Field(min_length=1, max_length=128)
    epoch: datetime
    tick_hz: int = 1_000_000

    theme_mode: Literal["system", "light", "dark"] = "system"
    contrast: Literal["normal", "more"] = "normal"
    motion: Literal["system", "full", "reduced"] = "system"

    #: Section 5.7 of the design page: the badge is not dismissible, and it
    #: reads "SYNTHETIC" or "SYNTHETIC + N PHYSICAL". The enum exists because a
    #: badge reading "synthetic" over a tile driven by a real sensor is a false
    #: statement on the most-shared clip this repository will produce.
    provenance: Literal["fully_synthetic", "hybrid_hil"] = "fully_synthetic"
    physical_device_count: int = Field(default=0, ge=0)

    speed_presets: tuple[float, ...] = (0.0, 0.25, 1.0, 4.0, 16.0, 60.0)
    default_speed: float = 1.0
    heartbeat_seconds: int = Field(default=15, ge=1, le=300)

    @field_validator("bind")
    @classmethod
    def _warn_on_a_wide_bind(cls, value: str) -> str:
        if value == "0.0.0.0":  # noqa: S104 - the warning is the point
            warnings.warn(
                "binding 0.0.0.0 exposes the dashboard on every interface; section 6.2 "
                "warns rather than refuses because a container publishes that way on purpose",
                stacklevel=3,
            )
        return value

    @field_validator("api_base_url")
    @classmethod
    def _api_base_url_is_an_origin_and_nothing_else(cls, value: str) -> str:
        """Refuse anything that is not scheme, host, and optional port.

        This value is interpolated into the `connect-src` directive of the
        content security policy the index route serves. A value carrying a
        space, a semicolon, or a newline writes further directives into that
        header, so the policy protecting the page is authored by whoever
        authored the config. Validating the origin here is what keeps
        `CSP_TEMPLATE.format` a substitution rather than a parser.

        The refusal is at construction rather than at render, for the reason
        `UnsPath` gives: a value that passed cannot be dangerous at any of the
        places it is later spelled.
        """
        split = urlsplit(value)
        if split.scheme not in ("http", "https"):
            raise ValueError(
                f"api_base_url must be http or https, got {split.scheme or 'no scheme'!r}"
            )
        if not split.hostname:
            raise ValueError(f"api_base_url names no host: {value!r}")
        if split.path not in ("", "/") or split.query or split.fragment:
            raise ValueError(
                f"api_base_url is an origin, not a URL with a path: {value!r}. "
                f"The dashboard joins its own paths onto it"
            )
        try:
            port = split.port
        except ValueError as exc:  # a non-numeric port never reaches the header
            raise ValueError(f"api_base_url carries an invalid port: {value!r}") from exc
        if port is not None and not 0 < port <= 65535:
            raise ValueError(f"api_base_url names an impossible port: {value!r}")
        if any(char in value for char in _FORBIDDEN_IN_ORIGIN):
            raise ValueError(
                f"api_base_url carries whitespace or a policy separator: {value!r}. "
                f"Either would append a directive to the content security policy"
            )
        return value

    @field_validator("tick_hz")
    @classmethod
    def _tick_hz_is_one_of_three(cls, value: int) -> int:
        if value not in TICK_RESOLUTIONS:
            raise ValueError(f"tick_hz must be one of {TICK_RESOLUTIONS}, got {value}")
        return value

    @field_validator("speed_presets")
    @classmethod
    def _presets_are_sorted_and_carry_the_two_that_matter(
        cls, value: tuple[float, ...]
    ) -> tuple[float, ...]:
        if list(value) != sorted(value):
            raise ValueError(f"speed_presets must ascend, got {value}")
        for required in (0.0, 1.0):
            if required not in value:
                raise ValueError(
                    f"speed_presets must contain {required}: 0 is pause and 1 is real time, "
                    f"and a preset list without them has no way back to either"
                )
        return value

    @model_validator(mode="after")
    def _default_speed_is_a_preset(self) -> DashboardConfig:
        if self.default_speed not in self.speed_presets:
            raise ValueError(
                f"default_speed {self.default_speed} is not in speed_presets "
                f"{self.speed_presets}, so the control would open on a value it cannot return to"
            )
        if self.provenance == "hybrid_hil" and self.physical_device_count < 1:
            raise ValueError(
                "hybrid_hil claims at least one physical device, and the badge renders the "
                "count; zero would print SYNTHETIC + 0 PHYSICAL over a fully synthetic run"
            )
        return self

    @property
    def provenance_badge(self) -> str:
        """The text the non-dismissible badge renders."""
        if self.provenance == "hybrid_hil":
            return f"SYNTHETIC + {self.physical_device_count} PHYSICAL"
        return "SYNTHETIC"

    def bootstrap(self) -> dict[str, object]:
        """What the page fetches on load.

        Served as JSON rather than substituted into the HTML, so the shipped
        `index.html` is byte-identical to the file on disk. Section 5.2 of the
        design page runs the browser unit tier by extracting the shipped
        `<script>` blocks and evaluating them in `node:vm`, and that only works
        while the file under test is the file being served.
        """
        return {
            "api_base_url": self.api_base_url.rstrip("/"),
            "mode": self.mode,
            "run_id": self.run_id,
            "tick_hz": self.tick_hz,
            "theme_mode": self.theme_mode,
            "contrast": self.contrast,
            "motion": self.motion,
            "provenance": self.provenance,
            "provenance_badge": self.provenance_badge,
            "speed_presets": list(self.speed_presets),
            "default_speed": self.default_speed,
            "heartbeat_seconds": self.heartbeat_seconds,
        }
