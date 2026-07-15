# CESGA Quick Reference Card

Most-used commands for working with FinisTerrae III.

## Connection

```bash
ssh cesga                          # SSH config alias (ft3.cesga.es)
ssh <user>@ft3.cesga.es           # Direct SSH
```

## SLURM

```bash
# Submit / monitor / cancel
sbatch job.sh
squeue -u $USER
scancel <jobid>
scancel -u $USER                   # Cancel all

# After completion
seff <jobid>                       # Efficiency report
sacct -j <jobid> --format=JobID,State,Elapsed,MaxRSS,MaxVMSize

# Interactive session
srun --partition=ilk --time=02:00:00 --mem=64G --cpus-per-task=16 --pty bash

# Node info
sinfo -p ilk
sinfo -p gpu
scontrol show job <jobid>
```

## Mandatory sbatch flags

```bash
#SBATCH --time=HH:MM:SS            # REQUIRED
#SBATCH --mem=64G                   # REQUIRED (or --mem-per-cpu=4G)
#SBATCH --cpus-per-task=16
#SBATCH --partition=medium          # short | medium | long | ondemand | requeue
```

## Partitions

| Name | Max time | Typical use |
|---|---|---|
| `short` | 6h | Tests |
| `medium` | 3d | Multi-day runs |
| `long` | 7d | Full campaigns |
| `ondemand` | 42d | Long/exploratory |
| `requeue` | 1d | Interruptible |

## Storage

| Variable | Quota | Purpose |
|---|---|---|
| `$HOME` | 10 GB | Code only |
| `$STORE` | 500 GB | Results, venvs |
| `$LUSTRE` | 1 TB | Temp scratch |
| `$LOCAL_SCRATCH` | Node NVMe | Fast temp |

## Modules

```bash
module load cesga/2020              # Base environment
module load cesga/system            # With miniconda
module spider <name>                # Search
module list                         # Loaded
module purge                        # Remove all
```

## Python/uv

```bash
# Install uv
mkdir -p $STORE/.local/bin
curl -LsSf https://astral.sh/uv/install.sh | env UV_INSTALL_DIR=$STORE/.local/bin sh
export PATH="$STORE/.local/bin:$PATH"

# Project setup
cd $STORE/MalariaSentinel
uv sync --all-packages
uv run python <script>
```

## Data transfer

```bash
# rsync to CESGA
rsync -avz ./data/ cesga:$STORE/MalariaSentinel/data/

# rsync from CESGA
rsync -avz cesga:$STORE/runs/ ./runs/
```

## Job array example

```bash
#SBATCH --array=1-24               # 24 tasks
# Use $SLURM_ARRAY_TASK_ID inside script
SEED=$SLURM_ARRAY_TASK_ID
```

## Environment for ABM

```bash
export OMP_NUM_THREADS=$SLURM_CPUS_PER_TASK
export UV_PROJECT_ENVIRONMENT="$STORE/MalariaSentinel/.venv"
```

## Troubleshooting

```bash
# Disk usage
du -sh $STORE/*
lfs quota -u $USER $LUSTRE

# Job output
cat <jobname>-<jobid>.o            # stdout
cat <jobname>-<jobid>.e            # stderr
```
