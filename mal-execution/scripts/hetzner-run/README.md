# hetzner-run

A bash CLI wrapper around `hcloud` (Hetzner Cloud CLI) for running
**ephemeral** CPU/RAM-heavy MalariaSentinel jobs on Hetzner Cloud VMs.

> **One-liner**: `hetzner-run sim-run` boots a `ccx33`, rsyncs the repo +
> data, runs a simulation, pulls the results, and destroys the VM —
> typically costing **€0.5–2 per run**.

The script lives in `mal-execution/scripts/hetzner-run/`. It is pure bash
(no Python dependency), uses only `hcloud`, `ssh`, `rsync`, and `jq` (all
already on macOS or installable via cloud-init), and is offline-testable
through `tests/test_hetzner_run.sh`.

---

## Quickstart — the 6 commands you need

```bash
# 1. See what a run would do (no API call, no spend).
hetzner-run --dry-run sim-run

# 2. Actually run it. The CLI will ask for confirmation.
hetzner-run sim-run

# 3. List the VMs you've started (ms-* prefix).
hetzner-run status

# 4. Get a quick cost-and-status snapshot.
hetzner-run status ms-1734567890-12345

# 5. Inspect a running VM (also works in --dry-run).
hetzner-run exec ms-1734567890-12345 'nproc && free -h && df -h /work'

# 6. Destroy anything you started (safe; prompts only if VMs exist).
hetzner-run destroy ms-1734567890-12345
```

If `sim-run` ever fails or you want to keep state, add `--keep-vm` to leave
the server **stopped** instead of destroyed (cheap: ~€0.011/h for the
disk). You can later start a fresh VM from a snapshot of that disk (see
"Snapshot strategy" below).

---

## Phase 0 prerequisites

These are one-time setup steps. The CLI itself is read-only on the Hetzner
config; it calls `hcloud`, which reads the token from
`~/.config/hcloud/cli.toml`.

1. **Hetzner account + project**: <https://console.hetzner.cloud>
2. **API token** scoped to the project:
   ```bash
   hcloud context create malariasentinel
   # paste token when prompted
   hcloud context use malariasentinel
   ```
3. **SSH key registered with Hetzner** (the one matching your local
   `~/.ssh/id_ed25519` or `~/.ssh/id_rsa`):
   ```bash
   hcloud ssh-key create \
     --name "$(whoami)@$(hostname)" \
     --public-key-from-file ~/.ssh/id_ed25519.pub
   ```
   The default name the CLI looks for is
   `davidflorezmazuera@gmail.com`. Pass `--ssh-key <name>` to `start` to
   override.
4. **Local tools** (macOS, all preinstalled):
   ```bash
   which hcloud jq ssh rsync
   ```
5. **Project knowledge graph stays on your Mac** — do **not** put the
   Neo4j container on the VM. The VM is compute-only; it never sees
   `agents/`.

> **Budget alert** — set a **€5/month** alert in the Hetzner console
> (Project → Settings → Alerts). The CLI cannot set this for you. The
> default `sim-run` cycle of "boot, run, destroy" should never trip a
> €5/month budget under normal use; the alert is a safety net for
> forgotten `start`-without-destroy cycles.

---

## Commands

| Command | What it does |
|---|---|
| `hetzner-run start [--type T] [--name N] [--location L] [--image I] [--ssh-key K]` | Create a VM, wait until SSH responds (~2–3 min), write metadata to `~/.cache/hetzner-run/<name>.json`. |
| `hetzner-run stop <name>` | Graceful `hcloud server shutdown`. |
| `hetzner-run destroy <name>` | `hcloud server delete` + remove local cache. |
| `hetzner-run status [<name>]` | One VM's status block, or a table of all `ms-*` servers. |
| `hetzner-run exec <name> <cmd...>` | `ssh root@<ip> <cmd>` with streaming output. |
| `hetzner-run push <name> <local> <remote>` | `rsync -avz` local → VM. |
| `hetzner-run pull <name> <remote> <local>` | `rsync -avz` VM → local. |
| `hetzner-run sim-run [--repo R] [--data D] [--cmd C] [--keep-vm] [--yes]` | High-level: start, push repo+data, run `cmd`, pull `/work/runs`, destroy. |
| `hetzner-run train [--config Cfg] [--keep-vm]` | High-level: like `sim-run` but default cmd is `uv run python scripts/05_train.py`. |
| `hetzner-run cost --type T --hours H` | Print the cost: e.g. `ccx33 × 2h = €0.060`. |
| `hetzner-run cost --list` | Full per-hour price table. |
| `hetzner-run --help` / `<sub> --help` | Usage text. |

### Global flags

- `--dry-run` — print the `hcloud` / `rsync` / `ssh` commands that would
  run; do not actually run them. **Always test a new command with
  `--dry-run` first.**
- `--debug` — verbose logging to stderr.

### Environment variables

| Var | Default | Effect |
|---|---|---|
| `HETZNER_RUN_DRY_RUN=1` | unset | Same as `--dry-run`. |
| `HETZNER_RUN_DEBUG=1` | unset | Same as `--debug`. |
| `HETZNER_RUN_CACHE_DIR` | `~/.cache/hetzner-run` | Where per-VM JSON metadata lives. |
| `HETZNER_RUN_SSH_KEY_NAME` | `davidflorezmazuera@gmail.com` | Default `--ssh-key`. |
| `HETZNER_RUN_SSH_KEY_PATH` | `~/.ssh/id_ed25519` | Local private key path. |
| `HETZNER_RUN_ESTIMATE_HOURS` | `1` | Worst-case hours used in the `sim-run` cost estimate. |
| `HETZNER_RUN_ASSUME_YES=1` | unset | Skip the `sim-run` confirmation prompt. |

---

## Snapshot strategy

The default flow **destroys** every VM at the end of a job — no persistent
state, no per-hour cost once the run finishes. When you want to keep state
across runs, three options in increasing cost:

| Strategy | Cost | Use when |
|---|---|---|
| `--keep-vm` | €0.011/h (stopped disk) | You want to `start` the same VM again within a day or two. |
| `hcloud server create --image <snapshot-id>` | €0.011/h storage | You pre-baked a snapshot with all the heavy datasets. |
| Re-push every run | bandwidth (free ingress) | Datasets are small or change often. Default. |

To make a snapshot of a stopped VM:

```bash
hcloud server shutdown ms-12345
hcloud image create --server ms-12345 --description "ms-baseline-2026-07-13"
# Note the returned image id, then use it as a base for new servers:
hetzner-run start --type ccx33 --name ms-fresh --image <image-id>
```

Snapshots are out of scope for the CLI's default flow on purpose — they
add a permanent disk cost and a manual lifecycle the user should
explicitly own.

---

## Cost reference (€ per hour, on-demand)

| Type | vCPU | RAM | SSD | €/h | typical 1 h run | typical 4 h run |
|---|---|---|---|---|---|---|
| `cx22` | 2 (shared) | 4 GB | 40 GB | 0.011 | €0.011 | €0.044 |
| `cx32` | 4 (shared) | 8 GB | 80 GB | 0.018 | €0.018 | €0.072 |
| `cpx22` | 2 (dedicated) | 4 GB | 80 GB | 0.020 | €0.020 | €0.080 |
| `cpx32` | 4 (dedicated) | 8 GB | 160 GB | 0.040 | €0.040 | €0.160 |
| `cpx52` | 8 (dedicated) | 16 GB | 240 GB | 0.125 | €0.125 | €0.500 |
| `cpx62` | 16 (dedicated) | 32 GB | 360 GB | 0.252 | €0.252 | €1.008 |
| `ccx13` | 2 (dedicated, Intel) | 8 GB | 80 GB | 0.018 | €0.018 | €0.072 |
| `ccx23` | 4 (dedicated, Intel) | 16 GB | 160 GB | 0.030 | €0.030 | €0.120 |
| **`ccx33`** | **8 (dedicated, AMD EPYC)** | **32 GB** | **240 GB** | **0.030** | **€0.030** | **€0.120** |
| `ccx43` | 16 (dedicated, Intel) | 64 GB | 360 GB | 0.060 | €0.060 | €0.240 |
| `ccx53` | 32 (dedicated, Intel) | 128 GB | 600 GB | 0.090 | €0.090 | €0.360 |
| `ccx63` | 48 (dedicated, Intel) | 192 GB | 960 GB | 0.126 | €0.126 | €0.504 |

The default for `sim-run` and `train` is `ccx33`: 8 dedicated AMD EPYC
cores for the price of a 2-core Intel instance. Update the table at
`lib/common.sh:PRICE_TABLE_EUR_PER_HOUR` when Hetzner adjusts prices.

---

## Troubleshooting

| Symptom | Cause | Fix |
|---|---|---|
| `hcloud: unauthorized` | Token missing or wrong project | `hcloud context list` and `hcloud context use <name>`. |
| `required command not found: jq` | jq not on `PATH` (Linux); macOS has it from 10.15+ | `brew install jq` (Linux) or update macOS. |
| `SSH to <ip> did not respond within 90s` | Cloud-init still running | Wait 60 s and retry `exec`; first boot is slow (~3 min). |
| `Server not found: <name>` in `stop`/`destroy` | Name typo or already destroyed | `hetzner-run status` to see what's live. |
| `invalid server name: <name>` | Name has spaces, slashes, or >62 chars | Use the `ms-<timestamp>-<pid>` default. |
| `non-interactive shell: pass --yes` | `sim-run` is trying to prompt but stdin is not a TTY | Pass `--yes` or set `HETZNER_RUN_ASSUME_YES=1`. |
| VM was started but I forgot to destroy it | Server is accruing cost at `ccx33` rate (€0.030/h ≈ €22/mo) | `hetzner-run destroy <name>` ASAP. The Hetzner budget alert should also fire within hours. |
| `rsync push failed: …` | SSH host key changed (e.g. server was recreated) | `ssh-keygen -R "<ip>"` to clear the known-hosts entry. |
| Tests hang | Real `hcloud` call slipping through `dry-run` | The test suite has a per-test timeout (`HETZNER_RUN_TEST_TIMEOUT=20`). The `--dry-run` tests should never call `hcloud`. |

---

## Layout

```
mal-execution/scripts/hetzner-run/
├── hetzner-run          # main dispatcher
├── lib/
│   ├── common.sh        # logging, hcloud wrapper, error handling, cost calc
│   ├── vm.sh            # start / stop / destroy / status
│   ├── sync.sh          # push / pull / exec
│   └── jobs.sh          # sim-run / train
├── cloud-init.yaml      # baseline VM image
├── tests/
│   └── test_hetzner_run.sh
└── README.md
```

All scripts use `set -euo pipefail` (or are sourced from a script that
does). No Python, no new dependencies, no edits outside this directory.

---

## Development

```bash
# Syntax check everything
find mal-execution/scripts/hetzner-run -name '*.sh' -o -name hetzner-run \
  | xargs -I {} bash -n {}

# Run the offline test suite (no hcloud, no network)
bash mal-execution/scripts/hetzner-run/tests/test_hetzner_run.sh

# Manually exercise the dispatcher
hetzner-run --help
hetzner-run --dry-run start --type ccx33 --name test
hetzner-run cost --type ccx33 --hours 2   # → €0.060
hetzner-run cost --list
```
