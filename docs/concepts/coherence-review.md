# The coherence review: what it is, and what has been measured

This file is the place to look when deciding whether to trust the coherence
review. It states the review's posture, what has been measured about its
mechanical signals, and — just as important — what has **not** been
measured, and why.

The review lives in two files:

| file | what it is |
|---|---|
| `.github/workflows/coherence-review.yml` | the workflow: signals, one pull-request comment, one artefact |
| `.github/concepts-review-prompt.md` | the reviewer's instructions |
| `.github/concepts-review-measurement.md` | the procedure for measuring the review once a population exists |
| `tools/coherence_signals.py` | the mechanical signals |

## The posture

* **The review is an advisor.** It never blocks, never rejects, never
  requires a document to change, and it is not a required check. Every
  step of the workflow is `continue-on-error`.
* **A signal is a candidate, not a finding.** The mechanical signals are
  inputs the reviewer may cite; the prompt says so, and the reviewer's
  judgement decides what is reported. Most signals are noise, and the
  review is told that a false positive costs the maintainer more than a
  missed defect.
* **A finding is a signal that survived adjudication**: the reviewer
  checked it against the code and a human confirmed it. The two are
  different populations, and the rate in the plan is computed over
  findings.
* **The reviewer can be wrong, and the first measurement of its
  false-positive rate does not exist yet.** It will exist only after the
  conceptual documents land on `main` through a pull request, because only
  then does a merge carry a document for the review to look at. Until
  then, the numbers below are the only ones that exist, and they are not
  the plan's metric.

## The measurement that was possible

### What was measured

The **per-class precision of the mechanical signals**, replayed over the
branch's document-touching commits: for each signal class, how many of its
findings were real errors (a fact the code contradicts) against how many
were noise.

### The population

The commits of the branch `docs/conceptual-documentation-layer` that touch
`docs/concepts/`, between the merge base with `main` and the branch's head:

```bash
git log --reverse --format='%H' $(git merge-base main HEAD)..HEAD -- docs/concepts/
```

That is **13 commits**. Three of them — `7d7fce1`, `79edd03`, `68af39e` —
predate `13a0dfc`, the commit that added the signal tool, so their trees
carry no tool: they are an **empty population**, not a rate of zero. The
measurement therefore covers **10 commits**.

`main` itself has 15 first-parent merges, and **none** of them touches
`docs/concepts/` (`git log --oneline main -- docs/concepts/` is empty): the
documents have never been on `main`. That is why the plan's metric — the
false-positive rate over the last 20 merges — has an empty population and
is **not measurable** (see below).

### The method

For every commit in the population, the tree is materialised with
`git archive`, the signal tool is run **inside that tree** with `--changed`
set to the files the commit changed (the tool resolves its repository root
from `__file__` and shells out to git, so it must run in the archived
tree), and the findings are recorded per class.

```bash
uv run --package mal-core python tools/replay_coherence_signals.py \
    --tool current --json /tmp/replay-current.json
uv run --package mal-core python tools/replay_coherence_signals.py \
    --tool tree   --json /tmp/replay-tree.json
```

* `--tool current` copies the working tree's tool into each archived tree:
  this measures the signals as they exist now, including the adjudication
  checks.
* `--tool tree` runs the tool each commit itself carried: the tool as
  committed at `13a0dfc`.

Both runs are read-only. The measurement was taken on **2026-11-17**, at
the branch head **`f9a5b5a`** (`main`'s merge base `ed679f5`). The tool
that produced the `--tool current` numbers is the working tree's: it is not
committed, and that is stated here so the numbers can be read for what
they are.

### The ground truth

A finding is **real** when the fact it reports is a fact the code
contradicts, and **noise** otherwise. The operational test is the branch's
own history: a real error is one that a later commit on the branch fixed
(rewrote the passage, corrected the path, completed the declaration), and
a finding that a later commit did *not* fix was adjudicated by reading the
passage against the code.

### The numbers

21 distinct findings over the 10 commits (a finding repeated in several
commits is one finding).

| class | findings | real | noise | precision |
|---|---|---|---|---|
| `missing_paths` | 11 | 2 | 9 | 0.18 |
| `out_of_range_citations` | 8 | 8 | 0 | 1.00 |
| `sidecar_key_mismatch` | 2 | 2 | 0 | 1.00 |
| `unknown_model_keys` | 0 | — | — | not computable |
| `unknown_code_constants` | 0 | — | — | not computable |
| `unknown_symbols` | 0 | — | — | not computable |
| `contract_version_errors` | 0 | — | — | not computable |
| `contract_declaration_mismatch` | 0 | — | — | not computable |
| `contract_file_mismatch` | 0 | — | — | not computable |
| `prose_cardinality` | 0 | — | — | not computable |
| **total** | **21** | **12** | **9** | **0.57** |

A class with no findings has no precision: the denominator is zero, so the
number is not computable and is not written down as zero.

`contract_versions` is a bucket of **mentions**, not of defects: 414 of
them across the population. It is the input the adjudicated class
`contract_version_errors` is computed from, and that class produced no
finding at any commit: no document ever stated a contract version the code
does not have.

### The findings, one by one

Real errors (12 findings, in six groups):

| finding | findings | fixed by | still open |
|---|---|---|---|
| `ingest/questions.md` cites `mal-core/src/mal_commonlib/aoi.py:157-170` — the file is `mal-commonlib/src/mal_commonlib/aoi.py` | 1 | — | yes |
| `ingest/questions.md` cites `mal-core/src/mal_core/abm/src/wire.hpp:203-217` — the header is `abm/include/mal_abm_fast/wire.hpp` | 1 | `dc04550` | no |
| the ODD's sidecar bullet lists the keys in prose and omits `abm_params_hash` | 1 | `dc04550` | no |
| `contracts.yaml`'s `state_sidecar` block declares no keys at all | 1 | — | yes (the working tree declares them) |
| `download/questions.md`: `download/__init__.py:1-30` (27 lines), `download/runner.py:69-282`, `:265-282`, `:284-290` (278 lines), `download/writer.py:12-58` (53 lines) | 5 | `052c7b8` | no |
| `training/questions.md` and `training/training.tex`: `training/model.py:86-96` (95 lines), `training/wrapper.py:107` (106 lines) | 3 | `dc04550` | no |

One of these deserves a note about the **signal**, not about the document:
the sidecar finding says the bullet "omits 15 key(s) the writer emits",
because the check compares the keys the bullet writes as `\code{...}`
tokens against the writer's keys — and at that commit the bullet listed the
keys in prose. The finding was real (one key, `abm_params_hash`, was
genuinely absent from the list), but the signal's count overstates it. A
signal that overstates is still a signal, and the reviewer is the one who
decides.

Noise (9 findings, in three groups): every one of them is a path the
document names **on purpose**, which the signal cannot tell from a
citation:

| finding | findings | why it is noise |
|---|---|---|
| `scoring/questions.md` and `training/questions.md`: `abm/tests/calibration` | 2 | the documents state that the path **does not exist** — it is an assertion of absence, quoted as such |
| `ingest`, `prediction`, `scoring`, `training`, `download` `questions.md`: `docs/plans/in-process/spec-retirement-ledger.md` | 5 | the retirement ledger was written later on the branch (`9b3d8b2`); at the commit the citation named a document in flight |
| `prediction/questions.md`: `mal-core/tests/test_spec_retirement_prediction.py` | 1 | the same: the test was written later on the branch (`9b3d8b2`) |
| `prediction/questions.md`: `docs/concepts/prediction/prediction.tex` | 1 | the document itself was written by the next commit (`86c9da0`): the citation named a document in flight |

Two kinds of noise are worth stating as findings about the *signals*, not
about the documents: a path that a document declares absent, and a path to
a file the branch had not written yet. Both are facts the tree does not
contradict, and the `missing_paths` class cannot tell them from a wrong
path. That is the class's noise floor (9 of 11 findings), and it is the
reason the class cannot be used as a gate.

### The tool as it was committed

The `--tool tree` replay (the tool each commit carried: the one committed
at `13a0dfc`) produced **one** distinct finding over the same 10 commits —
`\code{PAD_MULTIPLE}` in the prediction document — and it is noise: the
name is a placeholder the document introduces itself ("`PAD_MULTIPLE`
stands for the wrapper's padding multiple"). The committed tool could not
tell a placeholder from a symbol: it neither skipped the literal blocks
nor recognised a name the document defines. Its precision is **0 of 1**.
Its coverage is also narrower than the current tool's: it scanned only the
`.tex` documents (not the `questions.md` files), it did not exclude the
generated fragments, and it had no citation class.

## What was **not** measurable

* **The false-positive rate over the last 20 merges** — the plan's exit
  condition. The population is empty: `main` has 15 first-parent merges and
  none of them carries `docs/concepts/`, because the documents have never
  been on `main`. There is no run of the review over a merge that carries a
  document, so there is no rate. **No number is reported for it.**
* **The merge-based rate is also not the replay's rate.** The replay
  measures *signals* over *commits*; the plan asks for *findings* over
  *merges*. Different populations: the replay says how often a signal
  class was right about the tree it was run on, not how often a reviewer's
  finding was wrong.
* **The reviewer's own false-positive rate.** It needs a human verdict on
  each finding of a real pull request. There has been no such run: the
  workflow has never executed on a pull request that carries the documents.

## A companion signal, not wired in

`tools/check_d1_purity.py` reports the numbers a conceptual document still
types by hand — the rule D1. It is a **noisy companion** of the coherence
signals and is deliberately **not** part of them: it reports 370 findings
over the six documents (240 of them in the ODD), most of them numbers a
document legitimately owns.

```bash
uv run python tools/check_d1_purity.py
```

Its output is a reviewer's input, in the same posture as the coherence
signals: a signal, never a gate.

## Reproducing every number

```bash
# the population
git log --reverse --format='%H' $(git merge-base main HEAD)..HEAD -- docs/concepts/

# the replay (both tools), with the per-class counts
uv run --package mal-core python tools/replay_coherence_signals.py --tool current
uv run --package mal-core python tools/replay_coherence_signals.py --tool tree

# the signals of the working tree, as the workflow runs them
uv run --package mal-core python tools/coherence_signals.py

# the merge-based population that does not exist
git log --merges --first-parent --oneline main | wc -l     # 15
git log --oneline main -- docs/concepts/ | wc -l           # 0
```

## What comes next

The procedure that will measure the review over real merges is written
down, as a numbered list an agent can follow, in
`.github/concepts-review-measurement.md`: how to enumerate the population,
how to collect each run's findings (from the `coherence-findings`
artefact, not by scraping the comment), how to collect the human verdicts,
how to compute the rate, and how to attribute a finding to a signal class.

The first number it can produce will exist when the conceptual documents
reach `main` through a pull request.
