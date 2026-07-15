#!/usr/bin/env bash
# setup_env.sh — install uv + project venv on CESGA FinisTerrae III
# Run interactively on a login node:  bash setup_env.sh
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

# --- 2. Create venv in $STORE -----------------------------------------------
if [[ ! -d "$VENV_DIR" ]]; then
  log "Creating venv at $VENV_DIR …"
  uv venv "$VENV_DIR"
else
  log "Venv already exists at $VENV_DIR"
fi

# --- 3. Sync project dependencies -------------------------------------------
log "Syncing project from $PROJECT_ROOT …"
uv sync --all-packages --python "$VENV_DIR/bin/python" --directory "$PROJECT_ROOT"
log "Sync complete."

# --- 4. Verify installation -------------------------------------------------
log "Verifying imports …"
"$VENV_DIR/bin/python" -c "
import mal_commonlib, mal_ghana_sim
print('mal_commonlib:', mal_commonlib.__file__)
print('mal_ghana_sim:', mal_ghana_sim.__file__)
"
log "Environment ready.  Activate with:  source $VENV_DIR/bin/activate"
