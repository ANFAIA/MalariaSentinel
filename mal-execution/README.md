# mal-execution — Batch Jobs & Cloud Automation

Thin wrappers and automation around the `malariasim` pipeline (which lives in
`mal-core`). Nothing here implements pipeline logic — scripts import
`mal_core` / `mal_commonlib` and orchestrate runs. This is the top of the
promotion flow: when research code stabilises, it is promoted into `mal-core`
or `mal-commonlib` and the scripts here are updated to call it.

> Note: the `malariasim` CLI entry point itself lives in `mal-core`
> (`mal_core.cli`); `src/mal_cli/` is kept as a namespace placeholder.

## `scripts/`

| Script | Purpose |
|---|---|
| `build_environment.py` | Build environmental tensors for an AOI (thin wrapper over `mal_core.ingest.env`) |
| `build_hosts.py` | Build host-density NetCDF (thin wrapper over `mal_core.ingest.hosts`) |
| `build_mobility.py` | Build mobility OD matrices (thin wrapper over `mal_core.ingest.mobility`) |
| `train_unet.py` | Train the U-Net surrogate on ABM rollouts (M3-M4) |
| `train_unet_subsample.py` | Same, on a spatial subsample |
| `validate_unet.py` | Validate the U-Net on a held-out region |
| `cesga-run/` | CESGA FT3 HPC automation (SLURM job submission helpers) |
| `hetzner-run/` | Hetzner Cloud ephemeral-VM job runner — see its [README](scripts/hetzner-run/README.md) |

## Usage

Scripts are runnable with the workspace venv:

```bash
uv run python mal-execution/scripts/build_environment.py --help
uv run python mal-execution/scripts/train_unet.py --help
```

Prefer the `malariasim` CLI for normal pipeline work; reach for these
scripts when you need batch/chained or cloud execution.

## Related

- `mal-core/README.md` — pipeline stage order, scoring, modules
- `mal-core/src/mal_core/abm/slurm/` — SLURM templates for the C++ engine
- `tools/` — local dev helpers (verify, format, tests)
