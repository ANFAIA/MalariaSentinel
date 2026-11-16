#!/usr/bin/env bash
# Prepare the human review of the conceptual documents.
#
# The coherence reviewer is advisory and cannot replace the human reader
# (the stance note, "The authoring loop", step 2). This script makes that
# step concrete: it builds the documents, prints what a reader WITHOUT a
# code profile must be able to answer after reading each one, and prints
# the questions each stage's question set left open.
#
# Usage:
#   tools/review_concepts.sh [stage ...]
#
# The PDFs are left in docs/concepts/<stage>/<stage>.pdf for the reader.
set -euo pipefail

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO"

STAGES=("$@")
if [ "${#STAGES[@]}" -eq 0 ]; then
  STAGES=(download ingest abm scoring training prediction)
fi

echo "==> building the documents"
tools/build_concepts.sh "${STAGES[@]}"

for stage in "${STAGES[@]}"; do
  case "$stage" in
    abm) pdf="docs/concepts/abm/abm.pdf" ;;
    *)   pdf="docs/concepts/$stage/$stage.pdf" ;;
  esac
  echo
  echo "=============================================================="
  echo "  $stage — $pdf"
  echo "=============================================================="
  cat <<'CHECKLIST'
What a reader WITHOUT a code profile must be able to answer after reading:

  1. What does this stage consume, and in what form?
  2. What does it produce, and who consumes each product?
  3. Why does it behave the way it does — which choice is a choice, and
     which is imposed by the data or by the contract?
  4. In what ORDER do its processes run, and what consequence does that
     order have for the result?
  5. Which numbers are measurements, which are estimates, and which are
     engineering priors?
  6. What is NOT implemented, and what does the code never enter?

Mark a defect the way the stance note asks: name the section the defect
invalidates and the code change it would require. Those annotations become
a plan under docs/plans/.
CHECKLIST

  if [ -f "docs/concepts/$stage/questions.md" ]; then
    echo
    echo "Open items in the question set (grep for the markers):"
    grep -n "NOT ANSWERED\|not answered\|NOT IMPLEMENTED\|not implemented\|UNRESOLVED\|unresolved" \
      "docs/concepts/$stage/questions.md" | head -20 || true
  fi
done

echo
echo "The PDFs are in docs/concepts/<stage>/. Delete them before committing"
echo "(the concepts workflow rebuilds and commits them)."
