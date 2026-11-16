#!/usr/bin/env bash
# Build every conceptual document: regenerate the values, compile the
# documents, and fail when the generated fragments drift from the tree.
#
# One recipe, used locally and in CI (tools/build_concepts.sh).
#
#   tools/build_concepts.sh              build everything
#   tools/build_concepts.sh abm          build one stage
#
# The document sources are docs/concepts/<phase>/<phase>.tex, except the
# ABM, whose source is the ODD document (odd-2010-malariasentinel.tex) and
# whose PDF is published as abm.pdf. The question sets (questions.md) and the
# official ODD template are not documents: they are not compiled.
set -euo pipefail

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO"

PHASES=(download ingest abm scoring training prediction)

# source .tex -> published PDF name
source_for() {
  case "$1" in
    abm) echo "docs/concepts/abm/odd-2010-malariasentinel.tex" ;;
    *)   echo "docs/concepts/$1/$1.tex" ;;
  esac
}

if [ "$#" -gt 0 ]; then
  PHASES=("$@")
fi

echo "==> regenerating values"
uv run python tools/gen_concepts_values.py

for phase in "${PHASES[@]}"; do
  src="$(source_for "$phase")"
  if [ ! -f "$src" ]; then
    echo "build_concepts: no document for stage '$phase' ($src)" >&2
    continue
  fi
  echo "==> compiling $src"
  dir="$(dirname "$src")"
  # -halt-on-error matters: with -interaction=nonstopmode alone, LaTeX
  # logs an error and still produces a PDF, and latexmk exits 0. The
  # build must FAIL when a document references a value the configuration
  # no longer has.
  (cd "$dir" && latexmk -pdf -interaction=nonstopmode -halt-on-error "$(basename "$src")" >/dev/null)
  out="$(basename "${src%.tex}")"
  if [ "$out" != "$phase" ]; then
    cp "$dir/$out.pdf" "$dir/$phase.pdf"
  fi
  echo "    -> $dir/$phase.pdf"
done

echo "==> checking that the generated fragments match the tree"
uv run python tools/gen_concepts_values.py --check
