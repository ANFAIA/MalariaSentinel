#!/usr/bin/env bash
set -e
cd "$(dirname "$0")/.."
uv sync --all-packages
uv run python -c "
from mal_commonlib import config as C
from mal_ghana_sim import config as GC
import mal_core, mal_cli
import mal_data_explorer
import mal_abm_fast
print('All 6 workspace packages import OK')
print('  REPO_ROOT:', C.REPO_ROOT)
print('  DATA_DIR:', C.DATA_DIR)
print('  OCCURRENCE:', GC.OCCURRENCE)
"