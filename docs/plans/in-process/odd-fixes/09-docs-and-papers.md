# 09 — Docs and papers: one source for the bibliography, one tool for the corpus

> **Status**: pending (2026-11-17). This document holds **only work that has not been
> done**. The rest of this pack's subject — keeping the ODD description in sync with
> the code — is **already covered** and is not repeated here: the values and the
> contract tables of the ODD are generated from `model_constants.yaml` and from the
> code that writes them (`tools/gen_concepts_values.py`), so a renamed key breaks the
> LaTeX build; two advisory workflows review every pull request
> (`.github/workflows/coherence-review.yml`, `.github/workflows/agentic-doc-review.yml`);
> and the convention is that the ODD is amended in the commit that applies the plan
> that invalidates it. The action that regenerates and pushes the document on a pull
> request lives in `docs/plans/in-process/docs-pr-agent-and-codebase-memory.md`
> (Part 1).
> **Source**: ODD 2010 review notes
> (`.cache/odd-latex/odd-2010-malariasentinel-notes.tex`), pack 01.
> **ODD sections to amend when this is applied**: none directly — the change is in the
> repository's material, not in the model's description. The ODD's bibliography
> section changes, because the bibliography becomes an input of the tool.

## Objective

Move the `papers/` corpus out of Git and give the repository a tool that can rebuild
it, with the ODD's bibliography as the tool's input.

## Index

| # | Item | Note |
|---|---|---|
| 9.1 | `papers/` out of Git, rebuilt by a tool inside the toolkit | p.32 |

---

## 9.1 The papers corpus as a generated artifact

**Note (verbatim)** — **p.32**: "Remove papers folder from GitHub; keep only
agents/tools to create it with all papers, and keep papers mentioned here as
bibliography + input for tool. For example it can be placed inside the malariasim
toolkit."

**Current state.** `papers/` is versioned in the repository and holds the extracted
literature (the `papers/anopheles-dynamics/` extracts, `papers/REFERENCES.md` with the
citation table, the open-access paper under `papers/spatial-analysis/`). The GitHub
Pages site is built from `main:/docs` (legacy build, `docs/CNAME`), so removing
`papers/` does not touch the site, but the repository's own documentation links into
it (`mal-data-explorer/README.md`, `docs/licenses.md`).

**Decision needed.**

1. **The tool**: a script inside the `malariasim` toolkit that rebuilds `papers/` from
   the sources (PDFs), using **docling** for the extraction, with the ODD's
   bibliography as the manifest of what has to be there.
2. **The equivalence criterion**: the rebuilt corpus must be *equivalent* to the
   current one (same papers, same extracted content). Until that is demonstrated,
   `papers/` stays in Git — the condition the documentation plan already set:
   "It stays until a docling-based path proves equivalence, and a generated
   bibliography lands first."
3. **The bibliography**: `papers/REFERENCES.md` becomes an *output* of the tool (or
   stays a hand-written input and the tool validates against it) — decide which.
4. **The git footprint**: after the equivalence check, `papers/` is untracked; the
   README of the corpus says how to rebuild it.

**Done when.**

1. The tool exists, runs from a clean checkout, and produces the corpus.
2. A diff against the current `papers/` is empty (or the differences are explained and
   accepted).
3. The bibliography is generated and the ODD's references resolve to it.
4. `papers/` is untracked, and the repository's documentation links point to the tool.

## Dependencies / open points

- `papers/` is shared material: verify that no other session or agent depends on it
  before it is untracked (project rule: copy before deleting), and check what
  `docs/licenses.md` and `mal-data-explorer/README.md` point at.
- The docling path is the same one the documentation plan named as the condition for
  retiring `papers/`; the two must not drift.
- The bibliography also feeds document 05 (provenance table): the anchor rows and the
  tool's manifest should be the same artefact.
