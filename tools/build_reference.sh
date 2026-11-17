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
# Doxygen's HTML output is the whole directory: a stale file from a
# previous build (a renamed class, a page that no longer exists) would
# otherwise stay published.
find docs/reference/cpp -mindepth 1 -delete
# Doxygen reports an entity without a documentation comment as a
# warning. The reference must not publish an entity it cannot explain,
# so the warning fails the build: the reference's completeness is a
# property the build checks, not a property somebody remembers.
doxygen_log="$(mktemp)"
doxygen docs/reference/Doxyfile 2>"$doxygen_log" || true
if grep -q "warning:" "$doxygen_log"; then
  echo "build_reference: doxygen reported warnings:" >&2
  grep "warning:" "$doxygen_log" >&2
  rm -f "$doxygen_log"
  exit 1
fi
rm -f "$doxygen_log"

echo "==> pdoc (the Python packages)"
rm -rf docs/reference/python
mkdir -p docs/reference/python
# pdoc writes one page per package (submodules included as sections) plus an
# index and a search bundle. The current CLI has no --html flag: HTML is the
# only output format.
#
# The packages are listed one by one on purpose. pdoc honours a package's
# `__all__`, and `mal_core/__init__.py` exports the public API through a
# lazy table of names — so a package given as a single argument renders
# only those names, and its subpackages (the scoring framework, the
# download registry, the ingest writers) are not documented at all. Naming
# each package makes pdoc write a page per package, and the subpackages
# under it follow.
PY_MODULES=(
  mal_core
  mal_core.abm
  mal_core.download
  mal_core.habitat
  mal_core.ingest
  mal_core.prediction
  mal_core.scoring
  mal_core.scoring.scorers
  mal_core.training
  mal_commonlib
  mal_commonlib.data
)
uv run --with pdoc pdoc --output-dir docs/reference/python "${PY_MODULES[@]}"

# The same rule as Doxygen's: an entity the reference would publish
# without an explanation fails the build. The tool counts the entities
# that have no docstring; the public surface is the floor, because that
# is what the published reference renders.
echo "==> checking that every published entity is documented"
uv run python tools/check_docstrings.py --public-only --check

echo "==> the generated index"
# The index lists every page the build produced, from the same list pdoc
# was given: a page the build wrote but the index does not link is a page
# a reader cannot reach.
uv run python - "${PY_MODULES[@]}" <<'PY_INDEX'
import pathlib
import sys

modules = sys.argv[1:]
rows = "\n".join(
    f'  <li><a href="python/{m.replace(".", "/")}.html">Python &mdash; {m}</a></li>'
    for m in modules
)
page = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Technical reference &mdash; MalariaSentinel</title>
<style>
  body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
         margin: 0 auto; max-width: 48rem; padding: 2rem 1.25rem; line-height: 1.6; }}
  h1 {{ font-size: 1.5rem; }}
  li {{ margin: .35rem 0; }}
  p {{ color: #5b6672; }}
</style>
</head>
<body>
<h1>Technical reference</h1>
<p>Generated from the source comments. Do not edit by hand: it is rebuilt by
<code>tools/build_reference.sh</code>.</p>
<ul>
  <li><a href="cpp/index.html">C++ &mdash; the contract-defining headers of the ABM engine</a></li>
{rows}
</ul>
</body>
</html>
"""
pathlib.Path("docs/reference/index.html").write_text(page, encoding="utf-8")
print(f"build_reference: the index lists {len(modules)} Python pages")
PY_INDEX

echo "build_reference: done"
