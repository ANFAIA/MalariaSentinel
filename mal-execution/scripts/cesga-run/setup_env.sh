#!/usr/bin/env bash
# setup_env.sh — install uv + project venv on CESGA FinisTerrae III
# Run interactively on a login node:  bash setup_env.sh
#
# Creates the venv INSIDE the repo at $PROJECT_ROOT/.venv.
# Uses 'uv run' from the project root — no separate venv activation needed.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=cesga_config.sh
source "$SCRIPT_DIR/cesga_config.sh"

log() { printf '[%s] %s\n' "$(date '+%H:%M:%S')" "$*"; }

# --- 1. Install uv if missing -----------------------------------------------
if [[ ! -x "$HOME/.local/bin/uv" ]]; then
  log "Installing uv to \$HOME/.local/bin …"
  mkdir -p "$HOME/.local/bin"
  curl -LsSf https://astral.sh/uv/install.sh | env INSTALLER_NO_MODIFY_PATH=1 sh -s -- --bin-dir "$HOME/.local/bin"
  log "uv installed: $( "$HOME/.local/bin/uv" --version )"
else
  log "uv already present: $( "$HOME/.local/bin/uv" --version )"
fi
export PATH="$HOME/.local/bin:$PATH"

# --- 2. Move uv cache out of $HOME (quota is only 10GB) ---------------------
UV_CACHE_DIR="${PROJECT_ROOT}/.uv-cache"
mkdir -p "$UV_CACHE_DIR"
export UV_CACHE_DIR
log "uv cache dir: $UV_CACHE_DIR"

# --- 3. Create venv inside the repo ------------------------------------------
if [[ ! -d "$VENV_DIR" ]]; then
  log "Creating venv at $VENV_DIR …"
  uv venv "$VENV_DIR"
else
  log "Venv already exists at $VENV_DIR"
fi

# --- 4. Sync project dependencies -------------------------------------------
log "Syncing project from $PROJECT_ROOT …"
uv sync --all-packages --directory "$PROJECT_ROOT"
log "Sync complete."

# --- 5. Verify installation -------------------------------------------------
log "Verifying imports …"
"$VENV_DIR/bin/python" -c "
import mal_commonlib, mal_ghana_sim
print('mal_commonlib:', mal_commonlib.__file__)
print('mal_ghana_sim:', mal_ghana_sim.__file__)
"
log "Environment ready.  Run jobs with:  uv run python -m mal_ghana_sim.abm.run"
