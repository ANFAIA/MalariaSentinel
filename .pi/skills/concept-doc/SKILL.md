---
name: concept-doc
description: "Draft the conceptual document of one pipeline stage under docs/concepts/<phase>/. Use when asked to write, draft or revise a stage's conceptual document (download, ingest, abm, scoring, training, prediction) as a LaTeX source answering that stage's question set, with every value generated from model_constants.yaml."
---

# Concept Doc — drafting one stage's conceptual document

A conceptual document explains **how a stage works**: its purpose, the
processes it runs, the algorithms, the reasoning, and its inputs and outputs
as one section among others. It is not a specification, not a code reference,
and not a tutorial. It is written for a reader who has never opened the
source tree.

## Inputs you need

| Input | Where |
|---|---|
| The stage's question set | `docs/concepts/<phase>/questions.md` — for `abm`, the official `odd-2010-template.tex` beside the document |
| The stance | `docs/concepts/README.md` (S1–S10, the devices that transfer, the precedence rule) |
| The stage's material | The code, the plans under `docs/plans/`, the config |
| The generated values | `docs/concepts/generated/` — emitted by `tools/gen_concepts_values.py`; **never type a number** |

## The operation

1. **Read before asking.** Read the stage's material first — code, specs,
   plans, config — so the questions are answerable from evidence, not from
   assumption. This is the ODD's own discipline and it is what makes the
   question set worth having.
2. **Answer every question in the question set.** A question with no answer
   in the material is a finding: either the code does something the question
   did not anticipate (say so in the document), or the stage has a gap (say
   so in the document's absences section). Do not silently drop a question.
3. **Write the document in the stage's own structure.** There is no shared
   outline. The stance note fixes how to ask; the document's sections are
   yours.
4. **Generate every value.** Parameter and contract values come from
   `\input{generated/...}` or from `\mskey{<dotted.key>}`. If a value you need
   is not generated yet, extend `tools/gen_concepts_values.py`; do not type
   it into the prose.
5. **Cite every claim.** Where a claim rests on the implementation, cite the
   file (and line, where the line matters). A claim that cannot be resolved to
   a file, a key or a number is either speculation or a defect — mark it as
   such.
6. **Gloss every symbol at first use.** A code symbol may be named only if it
   is explained in prose where it first appears.
7. **Give the examples as described situations.** "A reader asks for the
   rainfall field for 2024 for the Ghana AOI" — and the document says what
   happens, in order. No code snippets as worked examples.
8. **Declare the absences.** Unimplemented paths, absent inputs, dormant
   parameters, states the code never enters. Incompleteness must be visible.

## Build

```bash
uv run python tools/gen_concepts_values.py     # refresh docs/concepts/generated/
latexmk -pdf docs/concepts/<phase>/<phase>.tex # or: tools/build_concepts.sh
```

The build must exit 0. A `\mskey{...}` for a key that does not exist is
undefined control sequence and fails the build — that is the mechanism that
keeps a document from disagreeing with the configuration file.

## The loop after the draft

A human annotates the draft. Annotations become a plan under
`docs/plans/`, naming the document section the plan invalidates and the code
change required. Applying the plan updates the code **and** the document in
the same commit — the document must never describe a state the code has
already left.

## What not to do

* Do not write a specification: no invariant IDs, no `affects` graph, no
  pass/fail rules. The documents are not a source of truth about parts.
* Do not copy a section list from another stage's document.
* Do not gate anything: the coherence review is advisory and warns only.
* Do not write a per-stage ODD. Only `abm` uses the ODD template; the other
  stages answer their own question sets.
