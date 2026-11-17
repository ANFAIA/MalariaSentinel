# Measuring the coherence review

The procedure for the measurement the plan asks for: the false-positive rate
of the coherence review, over the merges that carry the conceptual
documents.

Read `docs/concepts/coherence-review.md` first: it states what has been
measured so far, and why most of this is not measurable yet.

## The two populations (read this before counting anything)

* A **signal** is a candidate: one entry of a bucket of
  `tools/coherence_signals.py`, or a candidate the reviewer produced on its
  own. A signal is not a defect; most signals are noise, and the reviewer is
  told so.
* A **finding** is a signal that **survived adjudication**: the reviewer
  checked it against the code and judged it an incoherence, and a human
  confirmed it (or the adjudication was reproduced mechanically).

The rate is computed over **findings**, not over signals. The signal classes
are the labels used to attribute each finding (step 5). A number computed
over signals is the *signal yield*, not the false-positive rate, and the two
must never be reported as the same number.

A finding that has not been adjudicated is neither true nor false. It stays
out of the denominator and is counted separately as *unadjudicated*. It is
never silently counted as a true positive.

## The procedure

1. **Enumerate the population.** The population is the merge commits on
   `main` that carry the conceptual documents:

   ```bash
   git log --merges --first-parent --format='%H %s' main
   ```

   Keep only the merges whose diff touches `docs/concepts/`; that is the
   population the review can speak about. For each merge, find the pull
   request it came from (the merge commit's subject carries the PR number,
   and `gh pr view <number>` gives the rest).

   If that list is empty, the population is **empty** and the rate is
   **not measurable**. Say so; do not report a number.

2. **Collect each run's findings.** Every review run uploads its findings
   array as the run artefact `coherence-findings` (`findings.json`). Fetch it
   with:

   ```bash
   gh run download <run-id> --name coherence-findings --dir findings/
   ```

   The same array is the last fenced `json` block of the pull request's
   comment (marker `<!-- coherence-review -->`). The artefact is the
   preferred source: it does not require scraping a comment. A run that was
   skipped for lack of a secret has an empty array — record it as *skipped*,
   not as *no findings*.

3. **Collect the verdicts.** For each finding, a verdict from a human:
   *false positive*, *true positive*, or *unadjudicated*. The verdicts live
   in the pull request's thread (a maintainer's reply that names the finding
   `id`). If no human has adjudicated a finding, it is *unadjudicated* — it
   does not enter the denominator.

   An agent may adjudicate mechanically when the finding is a mechanical
   check (a wrong contract version, a sidecar key the writer does not
   emit, a cardinality the code contradicts): re-run the check against the
   merge commit's tree and record whether it still fires. A mechanical
   adjudication is reproducible; a judgement one is not, and must be
   labelled as a human verdict.

4. **Compute the rate**, per signal class and overall:

   ```
   false-positive rate = (# findings adjudicated false positive)
                         / (# findings adjudicated)
   ```

   Report the numerator, the denominator, and the number of unadjudicated
   findings next to it. A rate without its denominator is not a measurement.

5. **Attribute each finding to a signal class.** The classes are the buckets
   of `tools/coherence_signals.py`:

   | class | what it means |
   |---|---|
   | `unknown_model_keys` | a `\mskey{...}` key the model constants no longer have |
   | `unknown_code_constants` | a `\codeconst{...}` key the code no longer has |
   | `unknown_symbols` | a `\code{...}` symbol nothing defines |
   | `missing_paths` | a path the document names that the tree does not have |
   | `contract_version_errors` | a version the document states that the code does not have |
   | `contract_declaration_mismatch` | a declaration in `contracts.yaml` that the code contradicts |
   | `sidecar_key_mismatch` | a sidecar key list that differs from the writer's |
   | `prose_cardinality` | a count the document states that the code contradicts |
   | `out_of_range_citations` | a citation that points past the end of the file it names |
   | `model judgement` | the reviewer found it alone, with no signal behind it |

   A finding with no mechanical signal behind it is attributed to
   `model judgement` — that class measures the reviewer's own value, and it
   must not be merged with any other class.

6. **Write the result down** in `docs/concepts/coherence-review.md`: the
   population, the date, the commit the measurement was taken at, the
   per-class numbers with their denominators, and what was **not**
   measurable. A number that could not be computed must not appear as a
   number.

## What makes the measurement impossible before the documents land

The conceptual documents have never been on `main` (`git log --oneline main
-- docs/concepts/` is empty), so the review has never run on a merge that
carries them. The population in step 1 is empty, and the rate is therefore
not measurable today. The replay of the mechanical signals over the branch's
document-touching commits (described in `docs/concepts/coherence-review.md`)
measures the **signals**, on a population of commits that is not the one step
1 asks for; it is a different measurement, and it does not stand in for the
merge-based rate.
