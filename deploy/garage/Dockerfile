# One image for every twinflow role in the garage tier.
#
# The roles differ by command and by which network they sit on, not by what is
# installed, so one image is built once and started seven times. A per-role
# image would be seven builds of the same workspace.
#
# Pinned by digest. The tag beside it says which version the digest is, and the
# digest is what docker resolves. A tag is a mutable pointer, and a supply chain
# that rests on one is a supply chain nobody has pinned.
FROM python:3.14-slim-bookworm@sha256:23c59390fc717bf09f9336908199a0ae75d9c4264bf296123f94ad772fea3b52

# uv resolves the workspace from uv.lock, so the container installs the versions
# CI locked rather than whatever the index serves today.
COPY --from=ghcr.io/astral-sh/uv:0.5.29@sha256:88d7b48fc9f17462c82b5482e497af250d337f3f14e1ac97c16e68eba49b651e /uv /usr/local/bin/uv

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_FROZEN=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /srv/twinflow

# The lockfile and the manifests first, so a source edit does not re-resolve the
# dependency tree.
COPY pyproject.toml uv.lock ./
COPY packages/ packages/
COPY tools/ tools/
# schemas/ is not optional. The config loader resolves the published schema from
# the repository root beside the installed package, so an image without it
# validates nothing and fails at the first profile it reads.
COPY schemas/ schemas/

# --all-packages is load-bearing, not tidy. This root is a virtual project, so a
# plain sync installs the root's own dependencies and prunes every member, and
# the container then fails on an import that reads as broken code rather than as
# a missing install. WORKSPACE-1 documents the same trap for `uv run`.
#
# `--all-extras` brings in the `mqtt` extra, which is where ADR-0003 puts
# paho-mqtt. Doctrine D-10 keeps it out of the base install so a reader running
# a scenario resolves no client, and this tier is the case that does need one:
# every service here reaches a broker over TLS.
RUN uv sync --frozen --all-packages --all-extras --no-dev

# Run as a non-root user. A device container that is compromised should not be
# root inside the OT segment, which is the segment with the least monitoring.
RUN useradd --system --create-home --uid 10001 twinflow \
    && chown -R twinflow:twinflow /srv/twinflow
USER twinflow

ENV PATH="/srv/twinflow/.venv/bin:${PATH}"

# No default command. Every service in docker-compose.yaml names its own, and an
# image whose default starts something is an image that starts the wrong thing.
