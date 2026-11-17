# The lens: does a structural change have its document?

**You look for a change in the code that the conceptual documents still
describe the old way.**

The repository holds one LaTeX document per pipeline stage
(`docs/concepts/<stage>/`) and one ODD for the agent-based model. Those
documents are the specification the code is written against. When the
code changes shape, the document that states the old shape is a lie,
and the lie is what a reader of the documents will believe.

## What counts as structural

A change is structural when it changes **what the stage is**, not when
it changes how the stage does its work:

* a default, a threshold, a coefficient, a constant's value;
* a contract version, or the meaning of a contract;
* the set of channels, bands, variables, keys, or columns an artefact
  carries — and their order;
* the inputs or the outputs of a stage: a file that is read or written
  that was not before, or one that is not any more;
* the steps of an algorithm, when the steps are the behaviour (the order
  of an update, the rule of a decision, the condition of a branch);
* a CLI flag, a stage's name, a stage's boundary;
* a fallback, a default path, or a silent substitution — the path taken
  when something is missing.

A change is **not** structural when it is: a refactor with the same
behaviour, a performance fix, a test, a typo, a rename of a local
variable, a change of an implementation that the documents do not
mention.

## What is a finding

1. **A structural change with no document change.** The code moved and
   the document that states the moved thing did not. Say which document,
   which section, and which sentence or table cell now says something
   false.

2. **A stale number.** The document writes the value in prose ("0.87",
   "the third channel is the temperature") and the code moved it. The
   generated tables are rewritten from the code and cannot be stale; the
   prose can. The context lists the candidates; verify each one.

3. **A changed contract with an unchanged consumer.** The document
   states a rule that a consumer relies on ("the sidecar carries the
   version of the contract it was written against"), and the change
   breaks the rule for one consumer.

4. **A change the document does not cover.** The code changes
   something for which no document exists. This is a finding about the
   *absence* of a document, and it is worth reporting once, with the
   stage named.

## How to be sure

1. Find the document that covers the changed path. The context's table
   maps each path to its stage and to its document; when the mapping is
   missing, search `docs/concepts/` yourself.
2. Read the section that states the thing that changed. The context
   lists the sections with their line numbers.
3. Check the sentence against the code. Quote both.
4. Only then report.

## What is not a finding

* A change that the documents do not mention because the documents do
  not claim anything about it.
* A value that the document takes from a macro (`\mskey{}`,
  `\codeconst{}`): the table is regenerated, so it is already correct.
* A document that was changed in the same pull request: that is the
  fix, not the finding. Check the diff of the documents before you
  report.
* A plan under `docs/plans/in-process/` that announces the change: a
  change in flight is not an incoherence. The context lists the plans.
* A number in a document that the code never owned (a bibliographic
  value, a threshold from a paper, a figure from a measurement).
