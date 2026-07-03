#!/usr/bin/env bash
set -e
echo "Formatting..."
ruff format mal-commonlib/ mal-core/ mal-execution/ mal-ghana-sim/ mal-data-explorer/
ruff check --fix mal-commonlib/ mal-core/ mal-execution/ mal-ghana-sim/ mal-data-explorer/
echo "DONE"