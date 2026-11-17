# Writing a Conceptual Document

This page is the shared instrument of the six conceptual documents under
`docs/concepts/`. It fixes a **stance**, not a section list: a writer who has
never seen the ODD review reads this page and knows how to ask, in what order
of thought, and what a finished answer looks like. It never says what
sections a document must have — each stage's document has its own structure,
and that structure is the writer's decision.

The documents are LaTeX sources under `docs/concepts/<phase>/`, one per
pipeline stage: `download`, `ingest`, `abm`, `scoring`, `training`,
`prediction`. Each stage's question set lives beside its document
(`questions.md`, or for `abm` the official `odd-2010-template.tex`): the
document and the questions it answers live together, so a writer always finds
both.

## What this layer is for

The project documents its pipeline with two kinds of artefact, and this layer
exists because the first kind does not survive change:

* **Specs** (retired) pinned band names, sentinels, contract versions and
  sidecar keys — the class of fact a refactor renames. Every
  behaviour-preserving rename forced a noise edit, and nothing ever executed
  the checks the specs claimed to run, so they rotted.
* **Conceptual documents** (this layer) explain how a stage works: the
  purpose, the processes, the algorithms, the reasoning, and the inputs and
  outputs as one section among others. They name no code, so a rename does not
  invalidate them.

Two mechanical properties hold across all six:

1. **Values are generated, semantics are written.** Parameter and contract
   tables are emitted at build time from `mal-core/config/model_constants.yaml`
   and `docs/concepts/contracts.yaml`. A document never types a number; it
   writes `\mskey{some.dotted.key}` and the generator supplies the value. A
   renamed key becomes an undefined control sequence and fails the LaTeX
   build.
2. **The coherence review warns, it never blocks.** An advisor reports
   incoherences between these documents and the implementation. It does not
   reject, does not require a document to change, and does not constrain how
   documents are written. What has been measured about it so far — and what
   has **not**, because the documents have never reached `main` — is written
   down in `docs/concepts/coherence-review.md`.

## The stance (S1–S10)

For a stage with no entities, no state variables and no time step — `download`:
where the data comes from, in what format, how it is transformed, what it
becomes — the ODD's method reduces to the following. It says what the writer
must have worked out, not in what order.

* **S1. Purpose first, mechanism separate.** What question does this stage
  exist to answer, and what would count as it having answered it? What is
  explicitly out of scope? The purpose is a filter, not a description.
* **S2. Name every magnitude with its identity, units, native resolution and
  target resolution.** Not "the population file" but the file, its key, its
  native resolution, the target resolution, the aggregation rule, and what was
  lost in the aggregation.
* **S3. Distinguish what arrives from outside from what is decided here.**
  Each choice — provider, year, AOI, resampling, floor, no-data rule — must
  be *named as a choice*, so a reader can vary it.
* **S4. Write the order of operations at the granularity where order matters,
  and state the consequences.** Pseudocode plus a table of step / actor /
  order / mode, followed by the consequences of that order.
* **S5. Give every constant a provenance tier and make it checkable.**
  Measured / literature-anchored / engineering prior / model definition /
  scenario default — and a number with no evidence behind it says so on its
  face.
* **S6. Separate what is state from what is derived from what is a cache.**
  The generalised restart test: if the stage were interrupted and restarted,
  what would have to be on disk to resume identically?
* **S7. Declare what is not done.** Unimplemented paths, absent inputs,
  dormant parameters, states the code never enters.
* **S8. State the outputs and their consumption contract.** What is emitted, at
  what resolution, under what naming and version, and who reads it — including
  whether that resolution is the right one to serve the purpose.
* **S9. Keep an evidence appendix.** Implementation notes (behaviours invisible
  from the description) and provenance/versioning/testing status (what is
  verified, what is not, what the artefact must not be used for).
* **S10. The discipline that makes the above bite:** the document must be
  checkable by someone who does not trust it. Every claim should resolve to a
  file, a key, a line or a number a reviewer can verify, and the standing
  reviewer question is "is this number, this behaviour, this file actually
  what you say it is?"

S5, S3, S7, S9 and S10 are the ones the reference document (the ABM ODD) added
to the ODD.

### Precedence, stated once

* **Values** → `model_constants.yaml` wins.
* **Contract values and names** → the generated contract table wins.
* **Semantics** → the conceptual document wins.

On contradiction, the lower authority is the bug. The rule is stated in the
document that owns the content; there is no shared page beyond this one, and
no ownership matrix.

## The devices that transfer

These are the load-bearing devices of the reference document. All of them
transfer to the stages without entities; what changes is the nouns.

| Device | What it buys |
|---|---|
| **Notation table** with the code-name alias in the symbol's parenthesis | Lets a reader hold document and source in one head; makes the implementation notes checkable |
| **Schedule pseudocode + schedule table + consequences list** | The consequences list turns an ordering into falsifiable claims about results |
| **Parameter tables with a Provenance column** | Makes the epistemic status of every number checkable by a third party |
| **"Consequences worth stating" block per submodel** | Turns description into explanation |
| **"Origin and rationale" block per submodel** | Separates what the mechanism *is* from *why* it was chosen |
| **"What is data-based and what is a scenario choice"** | Names which numbers are measurements, which are estimates, which are choices |
| **Negative purpose list** ("The model is *not* intended for…") | Gives the reader a filter and the author a scope boundary |
| **Declaration of absences** ("Not implemented", "Absent from the delivered product", states the code never enters) | Makes incompleteness visible instead of silent |
| **Evidence appendix for replicators** | The place where a protocol-level description admits it cannot capture the implementation |

## Rules the documents follow

* **English**, LaTeX source, one document per stage.
* **No code or test detail.** Pseudocode yes; call graphs and test names no. A
  code symbol may be named only if it is explained in prose at its first use.
* **No code snippets as worked examples.** Each document's example is a
  described situation: a reader asks for something, and the document says what
  happens, in order.
* **No hand-typed numbers.** Every value comes from `\input{generated/...}` or
  from a macro the generator emits. Two macro families carry them: `\mskey{...}`
  for the values in `model_constants.yaml`, and `\codeconst{...}` for the
  values that live in the code (a module constant, a function's default, a
  loader's native grid). Both fail the build when the key is unknown, so a
  value the code changes breaks the document instead of misleading it.
* **Every claim cited.** Where a claim rests on the implementation, the
  document cites the file and line that supports it.
* **The stage's own structure.** A shared outline is not a template here; see
  `docs/plans/completed/per-stage-conceptual-documentation.md`, Alternative E.

## The authoring loop

1. An agent drafts the document from the stage's question set, the stance note
   above, and the stage's material.
2. Someone reads the draft for defects. The instrument is a reader **without a
   code profile** — a domain scientist who has never opened the repository —
   who annotates every place they would have to stop and guess. A human does
   this best; an agent instructed to read without a code profile does it
   adequately, and the first execution is on record: the annotations of the
   `download` document are in `docs/plans/completed/download-concept-review.md`,
   and the plan that came out of them is the pattern the other stages follow.
3. The annotations are distilled into a plan under `docs/plans/`, naming the
   document section the plan invalidates and the code change required.
4. Applying the plan updates the code **and** the document in the same
   commit, so the document never describes a state the code has already left.

The step that matters for the reader is step 2: the reading for defects is
the detection instrument, because the coherence review is advisory only.

## The reference document

`docs/concepts/abm/odd-2010-malariasentinel.tex` is the worked example: the
ODD 2010 description of the vector model, with the official
`odd-2010-template.tex` beside it as its question set. It shows the stance in
practice, and its review history is the evidence that the stance is worth
anything — writing it surfaced eleven code defects, and the reviewer's most
damaging criticisms were criticisms of documentation adequacy rather than of
the model.
