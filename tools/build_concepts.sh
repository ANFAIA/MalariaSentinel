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

# A reproducible PDF. Without this, every build stamps the current time
# into the PDF's /CreationDate and /ID, so the committed PDF changes on
# every run — the working tree is never clean after a build, and CI's
# "rebuild and commit" step would commit a difference that carries no
# information. With it, the PDF depends only on its source.
export SOURCE_DATE_EPOCH=1767225600   # 2026-01-01T00:00:00Z
export FORCE_SOURCE_DATE=1

echo "==> regenerating values"
uv run python tools/gen_concepts_values.py

echo "==> regenerating the site's document index"
uv run python tools/gen_concepts_index.py

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
  # The output is kept, not thrown away: when the build fails, the
  # error is in that output, and a CI log that hides it costs a whole
  # round trip to find. latexmk's exit code alone says "it failed",
  # not why.
  log="$(mktemp)"
  if ! (cd "$dir" && latexmk -pdf -interaction=nonstopmode -halt-on-error "$(basename "$src")" >"$log" 2>&1); then
    echo "build_concepts: $src failed to compile" >&2
    tail -n 60 "$log" >&2
    rm -f "$log"
    exit 12
  fi
  rm -f "$log"
  out="$(basename "${src%.tex}")"
  if [ "$out" != "$phase" ]; then
    cp "$dir/$out.pdf" "$dir/$phase.pdf"
    # Only the published name is kept: two PDFs of the same document in the
    # same directory is one too many for a reader and for git.
    rm -f "$dir/$out.pdf"
  fi
  echo "    -> $dir/$phase.pdf"
done

echo "==> checking that the generated fragments match the tree"
uv run python tools/gen_concepts_values.py --check
uv run python tools/gen_concepts_index.py --check
