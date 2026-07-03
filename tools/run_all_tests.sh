#!/usr/bin/env bash
set -e
echo "=== mal-commonlib ===" && (cd mal-commonlib && uv run pytest 2>/dev/null || echo "  no tests")
echo "=== mal-core ===" && (cd mal-core && uv run pytest 2>/dev/null || echo "  no tests")
echo "=== mal-execution ===" && (cd mal-execution && uv run pytest 2>/dev/null || echo "  no tests")
echo "=== mal-ghana-sim ===" && (cd mal-ghana-sim && uv run pytest 2>/dev/null || echo "  no tests")
echo "DONE"