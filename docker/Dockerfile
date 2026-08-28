# syntax=docker/dockerfile:1
# MalariaSentinel — idle CLI image. Does NOT compile the C++ ABM at build.
# Compile later inside the box:
#   docker exec -it malariasim malariasim abm --compile
#
# Build (from repo root):
#   docker build -f docker/Dockerfile -t malariasim:local .
#
# Idle:
#   docker compose -f docker/docker-compose.yml up -d
#   docker exec -it malariasim malariasim --help

FROM ghcr.io/astral-sh/uv:0.12.5 AS uv

FROM python:3.12-slim
COPY --from=uv /uv /usr/local/bin/uv
ENV UV_LINK_MODE=copy \
    UV_COMPILE_BYTECODE=0 \
    UV_PYTHON_DOWNLOADS=never \
    PATH="/app/.venv/bin:$PATH" \
    PYTHONUNBUFFERED=1
RUN apt-get update && apt-get install -y --no-install-recommends \
        build-essential \
        cmake \
        ninja-build \
        libgdal-dev \
        libeigen3-dev \
        libcli11-dev \
        nlohmann-json3-dev \
        libomp-dev \
        libgtest-dev \
        libnetcdf-dev \
        ca-certificates \
    && rm -rf /var/lib/apt/lists/*
WORKDIR /app
COPY . .
RUN uv sync --package mal-core --frozen
COPY docker/entrypoint.sh /usr/local/bin/malaria-entrypoint
COPY docker/pipeline.sh /usr/local/bin/malaria-pipeline
RUN chmod +x /usr/local/bin/malaria-entrypoint /usr/local/bin/malaria-pipeline
ENTRYPOINT ["/usr/local/bin/malaria-entrypoint"]
CMD []
