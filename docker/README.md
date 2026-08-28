# MalariaSentinel en Docker

Contenedor **idle**: arranca y no corre nada. `malariasim` queda en PATH.
Tú lanzas los comandos.

## Arranque

```bash
docker compose -f docker/docker-compose.yml up -d --build
docker exec -it malariasim malariasim --help
docker exec -it malariasim bash
```

Repo entero montado en `/app`. Volumen `malariasim-venv` conserva el venv
Linux de la imagen (el `.venv` macOS del host rompería el contenedor).
La imagen **no** compila el ABM; cmake + toolchain van en PATH.

## Comandos

```bash
docker exec -it malariasim malariasim download --aoi ghana --datasets era5
docker exec -it malariasim malariasim ingest --aoi ghana --year 2024 --month 6
docker exec -it malariasim malariasim abm --compile
docker exec -it malariasim malariasim abm --aoi ghana --days 30
```

Pipeline (explícito, nunca al arrancar):

```bash
docker exec -it malariasim pipeline
```

## One-shot (sin compose)

```bash
docker build -f docker/Dockerfile -t malariasim:local .
docker run --rm -it -v "$PWD:/app" \
  -v malariasim-venv:/app/.venv \
  malariasim:local malariasim --help
```

Helper: `./docker/malariasim malariasim ingest --aoi ghana --year 2024 --month 6`

## Credenciales (opcionales)

```bash
export CDSAPI_URL=... CDSAPI_KEY=... EARTHDATA_TOKEN=...
docker compose -f docker/docker-compose.yml up -d
```

## Notas

- `up -d` = `sleep infinity`. Cero pipeline / CLI / compile al start.
- C++ ABM: `docker exec -it malariasim malariasim abm --compile` (no se borra `build/`).
- Rebuild tras cambiar deps Python: `docker compose -f docker/docker-compose.yml up -d --build`
- Venv viejo: `docker volume rm malariasim-venv` y vuelve a `up`.
