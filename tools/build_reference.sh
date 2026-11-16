#!/usr/bin/env bash
# Generate the technical reference: Doxygen for the contract-defining C++
# headers, pdoc for the Python packages, and an index page that links both.
#
# The two tools write their own index.html and their own underscore-prefixed
# directories, so their outputs live in separate namespaces:
#
#   docs/reference/cpp/      (Doxygen)
#   docs/reference/python/    (pdoc, one directory per package)
#
# The flag-and-file contract (CLI flags, YAML keys, input formats, output
# contracts) is the interface that actually breaks; it is a candidate for a
# small purpose-built generator, which is NOT decided (I2-B). The section is
# stubbed either way, so this script's exit condition holds in both cases.
#
# Requirements: doxygen, and pdoc (`uv run --with pdoc pdoc ...`).
set -euo pipefail

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO"

if ! command -v doxygen >/dev/null 2>&1; then
  echo "build_reference: doxygen is not installed" >&2
  exit 1
fi

echo "==> Doxygen (the contract-defining headers)"
mkdir -p docs/reference/cpp
doxygen docs/reference/Doxyfile

echo "==> pdoc (the Python packages)"
rm -rf docs/reference/python
mkdir -p docs/reference/python
# pdoc writes one page per package (submodules included as sections) plus an
# index and a search bundle. The current CLI has no --html flag: HTML is the
# only output format.
uv run --with pdoc pdoc --output-dir docs/reference/python \
  mal_core mal_commonlib

echo "==> the generated index"
cat > docs/reference/index.html <<'HTML'
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Technical reference — MalariaSentinel</title>
<style>
  body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
         margin: 0 auto; max-width: 48rem; padding: 2rem 1.25rem; line-height: 1.6; }
  h1 { font-size: 1.5rem; }
  li { margin: .35rem 0; }
  p { color: #5b6672; }
</style>
</head>
<body>
<h1>Technical reference</h1>
<p>Generated from the source comments. Do not edit by hand: it is rebuilt by
<code>tools/build_reference.sh</code>.</p>
<ul>
  <li><a href="cpp/index.html">C++ — the contract-defining headers of the ABM engine</a></li>
  <li><a href="python/mal_core.html">Python — mal_core</a></li>
  <li><a href="python/mal_commonlib.html">Python — mal_commonlib</a></li>
</ul>
</body>
</html>
HTML

echo "build_reference: done"
