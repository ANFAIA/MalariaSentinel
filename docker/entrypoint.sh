#!/usr/bin/env bash
# Idle-by-default wrapper. No malariasim / pipeline on start.
#
#   docker compose up -d                         # sleep infinity
#   docker exec -it malariasim malariasim --help
#   docker exec -it malariasim bash
#   docker run --rm -it malariasim:local malariasim ingest --aoi ghana --year 2024 --month 6
set -euo pipefail

if [ "$#" -eq 0 ]; then
    exec sleep infinity
fi

if [ "$1" = "pipeline" ]; then
    shift
    exec /usr/local/bin/malaria-pipeline "$@"
fi

exec "$@"
