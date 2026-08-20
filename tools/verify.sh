#!/usr/bin/env bash
set -e
cd "$(dirname "$0")/.."
uv sync --all-packages
uv run python -c "
from mal_commonlib import config as C
import os, sys
sys.path.insert(0, os.getcwd() + '/mal-execution/src')
import mal_core, mal_cli
print('All workspace packages import OK')
print('  REPO_ROOT:', C.REPO_ROOT)
print('  DATA_DIR:', C.DATA_DIR)
print('  OCCURRENCE:', C.OCCURRENCE)
"