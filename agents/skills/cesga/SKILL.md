---
name: cesga
description: Work with CESGA's FinisTerrae III HPC cluster for MalariaSentinel. Covers connection, VPN, SLURM batch jobs, Python/uv setup, data transfer, and ABM simulation execution. Use when the user asks about CESGA, HPC deployment, batch jobs, SLURM, or running simulations on FinisTerrae III.
---

# CESGA — FinisTerrae III HPC Skill

Everything needed to run MalariaSentinel ABM simulations on CESGA's FinisTerrae III
supercomputer from this project.

## 1. Connection & VPN

### VPN (Checkpoint)

1. Download the Checkpoint VPN client from `portalusuarios.cesga.es`.
2. Server: `secure.cesga.es`
3. Login type: **HPC default**
4. Connect before any SSH.

### SSH

```bash
ssh <user>@ft3.cesga.es
```

**Fingerprint**: `SHA256:2QLXlyJxRDrYBXd8b8kn6J7fvnWKC4W2iheCxOsGch0`

### macOS SSH config

Add to `~/.ssh/config`:

```
Host cesga
  HostName ft3.cesga.es
  User <your-username>
  ServerAliveInterval 60
  ServerAliveCountMax 3
  # Required on older macOS / certain networks
  MACs hmac-sha2-512
```

Then connect with `ssh cesga`.

## 2. FinisTerrae III Overview

| Feature | Value |
|---|---|
| Total nodes | 357 |
| Peak performance | 4.36 PFLOPS |
| Interconnect | Infiniband HDR |

### Node types

| Partition | Nodes | CPU | Cores | RAM | Storage | Use case |
|---|---|---|---|---|---|---|
| **ILK** | 256 | 2× Intel Xeon Ice Lake 8352Y | 64 | 256 GB | 960 GB NVMe | **ABM simulations** |
| **A100 GPU** | 64 | 2× Intel Xeon + 2× NVIDIA A100 80GB | 64 | 512 GB | 960 GB NVMe | U-Net training |
| **SMP** | 16 | Multi-socket | 192+ | 2 TB | 960 GB NVMe | Large memory jobs |
| **CLK** | 94 | 2× Intel Xeon Cascade Lake | 48 | 192 GB | 960 GB NVMe | General workloads |

### For MalariaSentinel

- **ABM runs**: ILK nodes, 16–32 cores per job.
- **U-Net training**: A100 GPU nodes (M3+).
- **Memory**: ABM uses ~10–50 GB depending on grid size and population.

## 3. Storage

| Variable | Quota | Inode limit | Use |
|---|---|---|---|
| `$HOME` | 10 GB | 100k files | Code, configs, dotfiles. **Backed up.** |
| `$STORE` | 500 GB | 300k files | Simulation results, snapshots, `.conda` envs. |
| `$LUSTRE` | 1 TB | 200k files | High-speed scratch for job I/O. |
| `$LOCAL_SCRATCH` | Node-local NVMe | — | Fast per-node scratch. |
| `$TMPDIR` | Node-local NVMe | — | Alias for local scratch. |
| `$TMPSHM` | tmpfs in RAM | — | Very fast, but counts toward memory limit. |

**Rules**:
- Code in `$HOME`, results in `$STORE`, temp in `$LUSTRE` or `$LOCAL_SCRATCH`.
- Never store large datasets in `$HOME`.
- Conda/uv virtualenvs go in `$STORE` to avoid HOME quota exhaustion.

## 4. SLURM Batch System

### Mandatory flags

Every `sbatch` **must** include `--time` and `--mem` (or `--mem-per-cpu`).
Jobs without these are rejected.

### Partitions

| Partition | Max wall time | Notes |
|---|---|---|
| `short` | 6 h | Quick tests, single rollouts |
| `medium` | 3 d | Multi-day runs |
| `long` | 7 d | Full simulation campaigns |
| `ondemand` | 42 d | Long-running or exploratory |
| `requeue` | 1 d | Interruptible, lower priority |

QOS is assigned automatically based on requested resources.

### Key commands

```bash
sbatch job.sh                          # Submit a job
squeue -u $USER                         # Check running/pending jobs
scancel <jobid>                         # Cancel a job
seff <jobid>                            # Efficiency report after completion
sacct -j <jobid> --format=JobID,State,Elapsed,MaxRSS,MaxVMSize  # Accounting
srun --partition=ilk --time=01:00:00 --mem=32G --pty bash        # Interactive
```

### Job arrays

```bash
#SBATCH --array=0-23          # 24 tasks (indices 0–24)
# Inside the script, use $SLURM_ARRAY_TASK_ID to select seed/month
```

### Output files

By default:
- `%x-%j.o` — stdout
- `%x-%j.e` — stderr

### Interactive session

```bash
srun --partition=ilk --time=02:00:00 --mem=64G --cpus-per-task=16 --pty bash
```

## 5. Environment Modules

```bash
module avail                   # List available modules
module spider <name>           # Search for a module
module load cesga/2020         # Base environment (recommended)
module load cesga/system       # Alternative base (includes miniconda)
module list                    # Loaded modules
module purge                   # Remove all loaded modules
```

For Python/uv: use `cesga/system` as base, then install uv manually (see §7).

Conda environments must live in `$STORE/.conda`, **not** `$HOME`.

## 6. Data Transfer

### To/from login nodes (via VPN)

```bash
# From local machine
rsync -avz --progress ./data/ cesga:$STORE/MalariaSentinel/data/
rsync -avz --progress cesga:$STORE/MalariaSentinel/runs/ ./runs/

# Or scp
scp -r ./data/ cesga:$STORE/MalariaSentinel/data/
```

### DTN nodes (for large transfers)

- **DTN host**: `dtn.srv.cesga.es`
- **NOT accessible via VPN** — must be reached from an authorised centre network.
- Use rsync/scp/sftp from the DTN.

## 7. Python/uv Project Workflow

### First-time setup on CESGA

```bash
ssh cesga

# Install uv in $STORE (avoids HOME quota)
mkdir -p $STORE/.local/bin
curl -LsSf https://astral.sh/uv/install.sh | env UV_INSTALL_DIR=$STORE/.local/bin sh
export PATH="$STORE/.local/bin:$PATH"

# Clone or rsync the project
cd $STORE
git clone <repo-url> MalariaSentinel
# Or rsync from local:
rsync -avz --progress /local/path/MalariaSentinel/ cesga:$STORE/MalariaSentinel/
```

### Sync and run

```bash
cd $STORE/MalariaSentinel
uv sync --all-packages
uv run python -m mal_ghana_sim.scripts.build_env --help
uv run python scripts/01_ingest.py --download
```

### Virtualenv location

Set `UV_PROJECT_ENVIRONMENT` to keep the venv in `$STORE`:

```bash
export UV_PROJECT_ENVIRONMENT="$STORE/MalariaSentinel/.venv"
```

Or in `pyproject.toml`:
```toml
[tool.uv]
environment = "/home/<user>/store/MalariaSentinel/.venv"
```

## 8. ABM Execution on CESGA

### Pipeline overview

The ABM runs one month at a time via the `abm_run` CLI. A 2-year simulation = 24 sequential monthly runs.

1. **`build_env`** — generates the environment tensor (COG) + habitat patches (gpkg) for a given AOI, year, month.
2. **`abm_run`** — runs one month of the ABM with a given seed, producing a snapshot.

### Typical workflow

```bash
# Step 1: Build environment for month 1
uv run python -m mal_ghana_sim.scripts.build_env \
    --aoi ghana --year 2024 --month 1 --scale regional \
    --output-dir $STORE/runs/ghana-sim/env/

# Step 2: Run ABM for that month
uv run python -m mal_ghana_sim.abm.run \
    --env-cog $STORE/runs/ghana-sim/env/2024-01/env.tif \
    --habitat-gpkg $STORE/runs/ghana-sim/env/2024-01/habitat.gpkg \
    --seed 42 --days 30 \
    --output $STORE/runs/ghana-sim/snapshots/2024-01/seed42/
```

### Resource recommendations for ILK nodes

| Grid size | Cores | RAM | Notes |
|---|---|---|---|
| Small (regional) | 8–16 | 32 GB | Single-month fast |
| Medium (national) | 16–32 | 64–128 GB | Typical production |
| Large (continental) | 32–64 | 128–256 GB | SMP nodes for extreme cases |

## 9. SLURM Templates

### Single-core test job

```bash
#!/bin/bash
#SBATCH --job-name=abm-test
#SBATCH --partition=short
#SBATCH --time=01:00:00
#SBATCH --mem=4G
#SBATCH --cpus-per-task=1
#SBATCH --output=%x-%j.o
#SBATCH --error=%x-%j.e

cd $STORE/MalariaSentinel
uv run python -m mal_ghana_sim.scripts.build_env --help
echo "Test completed successfully"
```

### Multicore ABM job (16 cores, one month)

```bash
#!/bin/bash
#SBATCH --job-name=abm-monthly
#SBATCH --partition=medium
#SBATCH --time=24:00:00
#SBATCH --mem=64G
#SBATCH --cpus-per-task=16
#SBATCH --output=%x-%j.o
#SBATCH --error=%x-%j.e

export OMP_NUM_THREADS=$SLURM_CPUS_PER_TASK
export UV_PROJECT_ENVIRONMENT="$STORE/MalariaSentinel/.venv"

cd $STORE/MalariaSentinel
uv sync --all-packages

MONTH=${1:-1}
YEAR=${2:-2024}
SEED=${3:-42}

# Build env
uv run python -m mal_ghana_sim.scripts.build_env \
    --aoi ghana --year $YEAR --month $MONTH --scale regional \
    --output-dir $STORE/runs/ghana-sim/env/$YEAR-$(printf '%02d' $MONTH)/

# Run ABM
uv run python -m mal_ghana_sim.abm.run \
    --env-cog $STORE/runs/ghana-sim/env/$YEAR-$(printf '%02d' $MONTH)/env.tif \
    --habitat-gpkg $STORE/runs/ghana-sim/env/$YEAR-$(printf '%02d' $MONTH)/habitat.gpkg \
    --seed $SEED --days 30 \
    --output $STORE/runs/ghana-sim/snapshots/$YEAR-$(printf '%02d' $MONTH)/seed${SEED}/
```

### Job array — multiple rollouts (24 seeds for one month)

```bash
#!/bin/bash
#SBATCH --job-name=abm-rollouts
#SBATCH --partition=medium
#SBATCH --time=06:00:00
#SBATCH --mem=64G
#SBATCH --cpus-per-task=16
#SBATCH --array=1-24
#SBATCH --output=%x-%j_%A_%a.o
#SBATCH --error=%x-%j_%A_%a.e

export OMP_NUM_THREADS=$SLURM_CPUS_PER_TASK
export UV_PROJECT_ENVIRONMENT="$STORE/MalariaSentinel/.venv"

cd $STORE/MalariaSentinel
uv sync --all-packages

MONTH=${MONTH:-1}
YEAR=${YEAR:-2024}
SEED=$SLURM_ARRAY_TASK_ID

uv run python -m mal_ghana_sim.abm.run \
    --env-cog $STORE/runs/ghana-sim/env/$YEAR-$(printf '%02d' $MONTH)/env.tif \
    --habitat-gpkg $STORE/runs/ghana-sim/env/$YEAR-$(printf '%02d' $MONTH)/habitat.gpkg \
    --seed $SEED --days 30 \
    --output $STORE/runs/ghana-sim/snapshots/$YEAR-$(printf '%02d' $MONTH)/seed${SEED}/
```

Submit with:
```bash
MONTH=6 YEAR=2024 sbatch abm-rollouts.sh
```

### Long-running full simulation (7 days, sequential months)

```bash
#!/bin/bash
#SBATCH --job-name=abm-fullsim
#SBATCH --partition=long
#SBATCH --time=168:00:00
#SBATCH --mem=128G
#SBATCH --cpus-per-task=32
#SBATCH --output=%x-%j.o
#SBATCH --error=%x-%j.e

export OMP_NUM_THREADS=$SLURM_CPUS_PER_TASK
export UV_PROJECT_ENVIRONMENT="$STORE/MalariaSentinel/.venv"

cd $STORE/MalariaSentinel
uv sync --all-packages

START_MONTH=${START_MONTH:-1}
START_YEAR=${START_YEAR:-2024}
NUM_MONTHS=${NUM_MONTHS:-24}
N_ROLLOUTS=${N_ROLLOUTS:-100}

for i in $(seq 0 $((NUM_MONTHS - 1))); do
    MONTH=$(( (START_MONTH - 1 + i) % 12 + 1 ))
    YEAR=$(( START_YEAR + (START_MONTH - 1 + i) / 12 ))

    echo "=== Running month $MONTH/$YEAR ==="

    # Build env
    uv run python -m mal_ghana_sim.scripts.build_env \
        --aoi ghana --year $YEAR --month $MONTH --scale regional \
        --output-dir $STORE/runs/ghana-sim/env/$YEAR-$(printf '%02d' $MONTH)/

    # Run rollouts for this month
    for SEED in $(seq 1 $N_ROLLOUTS); do
        uv run python -m mal_ghana_sim.abm.run \
            --env-cog $STORE/runs/ghana-sim/env/$YEAR-$(printf '%02d' $MONTH)/env.tif \
            --habitat-gpkg $STORE/runs/ghana-sim/env/$YEAR-$(printf '%02d' $MONTH)/habitat.gpkg \
            --seed $SEED --days 30 \
            --output $STORE/runs/ghana-sim/snapshots/$YEAR-$(printf '%02d' $MONTH)/seed${SEED}/
    done
done

echo "=== Full simulation complete ==="
```

## 10. Monitoring & Debugging

```bash
# Check your jobs
squeue -u $USER

# Detailed job info
scontrol show job <jobid>

# Efficiency after completion
seff <jobid>

# Accounting (State, Elapsed, MaxRSS)
sacct -j <jobid> --format=JobID,State,Elapsed,MaxRSS,MaxVMSize

# Cancel a job
scancel <jobid>

# Cancel all your jobs
scancel -u $USER

# Check node availability
sinfo -p ilk

# Check GPU availability
sinfo -p gpu

# List loaded modules
module list

# Check disk usage
du -sh $STORE/*
lfs quota -u $USER $LUSTRE
```

### Common errors

| Error | Cause | Fix |
|---|---|---|
| `sbatch: error: Required --time not set` | Missing `--time` flag | Add `--time=HH:MM:SS` |
| `sbatch: error: Requested resources exceed partition limits` | Too much RAM/cores for partition | Reduce `--mem` or `--cpus-per-task` |
| `sbatch: error: Invalid partition` | Partition name misspelled | Use `short`, `medium`, `long`, `ondemand`, `requeue` |
| `No space left on device` | HOME or LUSTRE quota exceeded | Move data to `$STORE`, check `du -sh $HOME/*` |
| `Module not found` | Module not in default search path | Use `module spider <name>` to find exact path |
| Job stuck in `PD` (pending) | Resources unavailable | Check `sinfo` for node availability; try smaller partition |

### Job output files

After a job completes, check:
- `<jobname>-<jobid>.o` — stdout (logs, results)
- `<jobname>-<jobid>.e` — stderr (errors, tracebacks)

If the job crashed, the `.e` file contains the Python traceback.

## 11. Best Practices for MalariaSentinel on CESGA

1. **Always set `--mem` and `--time`** — SLURM requires them.
2. **Use `$STORE` for all persistent data** — `$HOME` is only 10 GB.
3. **Use `$LUSTRE` for temporary I/O** — large intermediate files during runs.
4. **Use `$LOCAL_SCRATCH` for per-node temp** — fastest I/O for large arrays.
5. **Pin the venv to `$STORE`** — avoids HOME quota and re-downloading on each job.
6. **Submit job arrays for rollouts** — one array per month, seeds as task IDs.
7. **Check `seff` after every job** — tune cores/memory for future runs.
8. **Keep logs** — SLURM output files are your debugging lifeline.
9. **rsync results back** — don't leave large files on `$LUSTRE` (it's scratch).
10. **Use `$TMPSHM` for truly ephemeral data** — RAM-speed, but counts toward `--mem`.

## 12. Data transfer back to local

```bash
# After runs complete
rsync -avz --progress cesga:$STORE/runs/ghana-sim/ ./runs/ghana-sim/

# Just the snapshots (skip intermediate env files)
rsync -avz --progress cesga:$STORE/runs/ghana-sim/snapshots/ ./runs/ghana-sim/snapshots/

# Clean up CESGA scratch
rm -rf $LUSTRE/abm-temp-*
```
