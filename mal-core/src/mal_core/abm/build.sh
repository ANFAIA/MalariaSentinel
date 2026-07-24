#!/bin/bash
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
BUILD_DIR="$SCRIPT_DIR/build"
BIN_DIR="$SCRIPT_DIR/bin"
echo "Building mal_abm_fast..."
cmake -S "$SCRIPT_DIR" -B "$BUILD_DIR" -G Ninja -DCMAKE_BUILD_TYPE=Release
cmake --build "$BUILD_DIR" -j
mkdir -p "$BIN_DIR"
cp "$BUILD_DIR/src/mal_abm_fast" "$BIN_DIR/mal_abm_fast_$(uname -s | tr '[:upper:]' '[:lower:]')"
echo "Binary copied to $BIN_DIR/"
