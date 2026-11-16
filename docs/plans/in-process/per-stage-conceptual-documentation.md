# Per-Stage Conceptual Documentation

*   **Author:** david-fm
*   **Status:** Plan (in process)
*   **Date:** 2026-11-16
*   **Design context:** `docs/designs/per-stage-conceptual-documentation.md`
    (the RFC brief this plan was drafted from).

--------------------------------------------------------------------------------

## Overview

The project documents its pipeline with eight hand-written specs under
`docs/specs/` (2,253 lines). They act as contract documents: they pin band
names, value ranges, invariants and versions, and they declare themselves the
winner when code disagrees. They have become useless — not mainly because
refactors force edits in them, but because nothing ever executed the checks
they claim to run.

This design replaces them with a conceptual layer. Six formal LaTeX documents
live under `docs/concepts/<phase>/` — one per pipeline stage: `download`,
`ingest`, `abm`, `scoring`, `training`, `prediction`. Each document explains how
its stage works internally: the theory, the processes, the algorithms, the
reasoning, and the stage's inputs and outputs as one section among others. Each
document has its own structure. What the six share is a stance — a way of
asking questions that must be settled before writing — not a template. Each
stage's question set is kept beside its document as a template file: the
document and the questions it answers live together, so a writer always finds
both. For the ABM that template is `odd-2010-template.tex`, the official ODD
2010 template that came with the reference document.

Each piece of content is owned by the stage that uses it. There is no shared
substrate document and no ownership matrix. Coherence between the six is
checked at the seams: what one stage produces against what the next stage takes
as input.

The layer rests on two mechanical properties:

1. **Values are generated, semantics are written.** Parameter tables and
   contract tables are emitted at build time from `model_constants.yaml` and a
   contracts file. A renamed or removed key becomes an undefined control
   sequence and fails the LaTeX build. No hand-typed number survives in prose.
2. **The PR coherence review warns, it never blocks.** An advisor reports
   incoherences between the conceptual documents and the implementation. It
   does not reject, does not require a document to change, and does not
   constrain how documents are written.

The ABM stage already has its document: the ODD 2010 description of the model,
which today sits in a gitignored directory. It moves into `docs/concepts/abm/`
as tracked source, builds to PDF unmodified, and is then changed progressively
as the planned refactoring work lands.

PDFs are built in CI and published under a documentation page linked from the
site. In parallel, a pull-request workflow generates technical reference
documentation for the Python and C++ code from polished source comments.

The value of this layer is not "better docs". It is a documentation layer that
survives refactors: a document that describes the model can stay true across a
rename; a spec that pins a symbol cannot. And it is a layer readable by someone
who has never opened the code.

## The Problem

### The specs rotted because nothing executed their checks

Every spec opens with a fenced block reading `# Machine-readable affects block
— parsed by the drift-check agent` and carries a `Last drift check:` date. No
drift-check agent exists. The repository has no `.github/` directory at all.
The invariants have no runner: `tools/run_all_tests.sh` pairs `set -e` with
`pytest || echo "no tests"`, so every failing suite is swallowed and the script
always exits 0.

The drift is in the repository right now, in files the new system is supposed
to depend on (verified 2026-11-16):

| Prose authority | Claim | Reality |
|---|---|---|
| `docs/specs/abm/spec.md:182` | `assert cv.startswith('2.')` | same file INV-12 pins state contract **v4.0** — *not repaired: the file is scheduled for deletion* |
| `docs/README.md` | lists `specs/self_improve/`, `diagrams/`, four presentation/status files | none of those paths exist |
| `AGENTS.md` "Calibration framework conventions" | edit `thresholds.yaml`, `scorers/composite.py::DEFAULT_WEIGHTS`, run `tests/calibration` | `thresholds.yaml` exists only in a stale worktree; `composite.py` does not exist; the pytest harness was deleted in 2026-10 |
| `AGENTS.md` monorepo layout | `mal-ghana-sim/` is one of five packages | no such directory |
| `docs/specs/data/spec.md` INV-11 | env-NC `contract_version: "2.0"` | `model_constants.yaml`: `env_nc: "3.0"` — *not repaired* |
| `docs/specs/commonlib/spec.md` §4.3 | `K_MAX` is public API | `config.py`: "K_MAX retired (2026-10-20)" — *not repaired* |
| `mal-core/.../wire.hpp` | cites `docs/abm-status.md` | file does not exist |

Consequence for this plan: a coherence gate built on this baseline reports the
plan's own debt on its first run. A truth pass has to precede the gate, and it
is the cheapest step in the whole plan.

**Scope of the truth pass (author decision, 2026-11-16).** The three
`docs/specs/*` rows are *not* repaired. The specs are scheduled for deletion
(see "Spec retirement"), the work is on a secondary branch, and the session
that implements this plan is short-lived — so a false spec is cheaper than a
half-updated one. Instead, `AGENTS.md` gains an explicit warning that
`docs/specs/*` is **not authoritative**: during the editing sessions, no agent
may take a spec claim as true. The remaining rows (`docs/README.md`,
`AGENTS.md` ×2, `wire.hpp`, the contract-defining headers) are repaired.

### The specs are written around the code, not around the system

The values the specs carried — band names, the `-9999.0` sentinel,
`contract_version`, sidecar keys — are exactly the class of fact a refactor
renames. Every behaviour-preserving rename forces a noise edit, which is how
the documents became stale: the maintenance cost was real, and nothing paid it.

What a newcomer actually needs — what a stage does, why it behaves as it does,
what question it exists to answer — is not in the specs at all. Today the only
documents that answer it are an ODD in a gitignored directory and the code
itself.

### A formal PDF is trusted more than a spec, so the replacement must not lie

The eight spec files are being deleted, and six formal documents take their
place. A formal PDF with a date is read as authority. Publishing six documents
that are provably false in their core sections would be worse than publishing
none. The plan therefore has to settle, per section, whether it describes what
the code does today or a declared target — and it has to generate every value
so that a document cannot disagree with the configuration file by hand.

### Cost is authoring, not toolchain

`latexmk` and `pdflatex` are already installed; the ODD preamble uses 15
standard packages; builds take seconds. The real cost is 5,400–7,100 LaTeX
lines replacing 2,253 Markdown lines, and an estimated 7.5–20 person-days of
authoring for five documents that currently have no named reader. That cost is
accepted by the author and recorded here so a later reversal is a decision, not
a discovery.

## Goals

*   Retire `docs/specs/` stage by stage as each conceptual equivalent lands,
    with no information loss: semantics move to the conceptual document, values
    move to the generated tables.
*   Publish six conceptual documents under `docs/concepts/<phase>/` (`download`,
    `ingest`, `abm`, `scoring`, `training`, `prediction`), LaTeX source,
    English, each in its own structure, sharing a stance rather than a template.
*   Make hand-typed values impossible: parameter and contract tables generated
    from `model_constants.yaml` and a contracts file at build time, so a
    renamed key fails the LaTeX build on its own.
*   Run a warnings-only coherence review on pull requests: it reports
    incoherences between the documents and the implementation, and blocks
    nothing.
*   Move the ODD source out of the gitignored cache into `docs/concepts/abm/`
    and prove it builds to PDF unmodified.
*   Publish one PDF built in CI and reachable from `malariasentinel.com` under
    a separate documentation page, in ES and EN.
*   Generate a technical reference for Python and C++ from polished source
    comments, namespaced under `docs/reference/cpp/` and
    `docs/reference/python/`.
*   Keep each stage's question set (its template) beside its LaTeX document
    under `docs/concepts/<phase>/` — for `abm`, the `odd-2010-template.tex`.
*   Establish the authoring loop: an agent drafts from a per-stage question
    set, a human annotates, annotations become plans under `docs/plans/`, and
    applying a plan updates the part of the document it invalidates.
*   Untrack `data/` from GitHub while keeping it usable locally: zip `data/`
    to the repository's parent directory first, then `git rm -r --cached
    data`; the next `malariasim download` rebuilds the manifest from nothing.

## Non-Goals

*   **No enforced contracts.** No document is a source of truth. Values come
    from configuration, semantics from prose, and the precedence rule is stated
    once. These documents are a conceptual and theoretical source of truth
    about the system's processes and algorithms, not a technical source of
    truth about its parts.
*   **No automated gating of any kind.** No blocking check, no required status,
    no presence rule, no waiver mechanism. The only automated failure is a
    LaTeX build that cannot find a generated value — a property of the build,
    not a judgement about the document.
*   **No code or test detail in the conceptual documents.** Pseudocode yes;
    call graphs and test names no. A code symbol may be named only if it is
    explained in prose at its first use.
*   **No code snippets as worked examples.** Each document's example is a
    described situation: a reader asks for something, and the document says
    what happens, in order.
*   **No ODD per stage.** Only `abm` gets the ODD; other stages get their own
    question sets.
*   **No shared substrate.** No seventh `shared/` document, no ownership
    matrix, no `\input` fragments between stages. Repetition between stages is
    accepted: it is where drift becomes visible.
*   **No template authored up front.** Per-stage question sets are found per
    stage, by reading that stage's material first.
*   **No retirement of `papers/` in this phase.** It stays until a
    docling-based path proves equivalence, and a generated bibliography lands
    first.
*   **No migration of GitHub Pages away from the legacy `main:/docs` build.**
*   **No `data/` history rewrite** until a blob-size scan proves it is needed.
*   **No decision on experiment packages** (`mal-data-explorer`,
    `social-networks/`): the author's call, tracked as D9.
*   **No ABM modification and no generalisation to other systems** — the
    cycle/DAG gap against Kelly et al. (2012) is recorded, not actioned.

--------------------------------------------------------------------------------

## Technical Plan (Architecture)

### Components

The design has seven components. Four of them are documents, three of them are
machines.

1. **Six conceptual documents** at `docs/concepts/<phase>/` — `download/`,
   `ingest/`, `abm/`, `scoring/`, `training/`, `prediction/`. Each directory
   holds that stage's LaTeX source and, beside it, the stage's question-set
   template — the questions the document must answer. For `abm/` that template
   is `odd-2010-template.tex`, copied out of the gitignored cache together with
   the document. The document's structure is its own; the template records the
   questions it was written to answer.
2. **The stance note** at `docs/concepts/` — one page stating how to ask the
   questions (S1–S10, stated in full in Appendix A of this plan): purpose before
   mechanism, every magnitude named with identity and units, choices named as
   choices, order written with its consequences, every constant given a
   provenance tier, state separated from derived from cache, absences declared,
   outputs given with their consumption contract, an evidence appendix, and a
   claim checkable by a reader who does not trust it. The ODD is the worked
   example. The note fixes a stance, never a section list.
3. **The drafting skill** at `.pi/skills/` — a lightweight skill carrying the
   drafting operation, so that changing the question set itself is a supported
   action rather than an ad-hoc edit.
4. **The value generator** — a script that reads
   `mal-core/config/model_constants.yaml` and a small contracts file, and emits
   LaTeX (`\input{generated/...}`) carrying parameter tables, contract tables
   and per-key macros. The documents never type a number. A key renamed or
   removed in YAML becomes an undefined control sequence and the LaTeX build
   fails. This is the only automatic failure in the whole design, and it is a
   property of the build, not a judgement about the document.
5. **CI: PDF build and publication** — a workflow compiles each document with
   `latexmk -pdf` and commits the PDF back to the same branch (decision I1-A),
   at a stable path such as `docs/concepts/abm/abm.pdf`, which the legacy
   `main:/docs` Pages build then publishes. The documentation page under `docs/`
   links each PDF and carries its own ES/EN dictionaries; one nav entry is
   added to the landing page. Fork PRs cannot receive the bot push, so their
   PDF appears only after merge — accepted under the warnings-only regime.
6. **CI: coherence review (warnings only)** — on each PR, a reviewer compares
   the diff against the conceptual documents of the affected stages and posts a
   comment naming the passage that no longer matches the code, quoting both. It
   never blocks, never rejects, never requires a document to change. Its
   mechanical inputs — the sources it may cite, not checks it must pass — are:
   dotted keys vs `model_constants.yaml`; `\code{...}` identifiers vs Python
   and C++ symbols; contract versions vs `model_constants.yaml:contracts.*`;
   recomputable numbers (grid dimensions from `aois.yaml`); `latexmk -Werror`
   integrity; named `docs/...`, `papers/...`, `scripts/...` paths vs the tree;
   documented output files vs consumer globs; changed path → candidate
   document; `% sources:` freshness. What stays human: process ordering,
   formula-vs-code equivalence, implemented-vs-unimplemented statements,
   blast radius, provenance.
7. **CI: generated technical reference** — after a comment-polish pass scoped
   to the contract-defining headers (`wire.hpp`, `output_contract.hpp`,
   `habitat_availability.hpp`, `habitat_engine.hpp`, `coordinator.hpp`,
   `config.hpp`), Doxygen generates the C++ reference and pdoc the Python one
   (decision I2-A), into the namespaced directories `docs/reference/cpp/` and
   `docs/reference/python/` so neither tool's `index.html` collides with the
   other's. One site entry, "Technical reference", links into both surfaces.
   The flag-and-file contract (CLI flags, YAML keys, input formats, output
   contracts — the interface that actually breaks) is a candidate for a small
   purpose-built generator later (I2-B, still open).

### Data flow

```text
                 mal-core/config/model_constants.yaml
                 contracts file (contract names + versions)
                            │
                            ▼
                   ┌────────────────┐   emits   generated/*.tex
                   │ value generator│ ───────▶  (tables + macros)
                   └────────────────┘                  │
                                                       ▼
 per stage:  question-set template ──▶ agent drafts ──▶ docs/concepts/<phase>/<stage>.tex
 (abm: odd-2010-template.tex)          (stance note)          │
                                                              ▼
                                                    latexmk -pdf  ── fail if a
                                                    │             generated key is
                                                    ▼             missing
                                              <stage>.pdf
                                                    │
                         CI commits PDF to branch ──┤
                                                    ▼
                                    legacy Pages (main:/docs) ──▶ malariasentinel.com
                                                                        ▲
                                    docs/ documentation page (ES/EN) ───┘

 PR opened ──▶ coherence reviewer (warnings only) ──▶ PR comment:
                inputs: diff + affected stage docs   "passage X no longer
                + in-process plans                    matches code Y"
                mechanical signals are cited,        (never blocks the merge)
                never evaluated as pass/fail

 human annotates a document ──▶ annotations become a plan under docs/plans/
                                        │
                                        ▼
                     plan applied ── code change + the document section it
                                     invalidates, in the same commit
```

### Sequencing

The stages below are ordered so that each one's exit condition is checkable
before the next begins. They are the implementation of this design, not a
re-litigation of it.

| Stage | Work | Exit condition |
|---|---|---|
| 0 | **Truth pass**: fix `docs/README.md`, the `AGENTS.md` calibration and monorepo-layout sections (plus a `docs/specs/*` pending-retirement warning), and the contract-defining headers, so no claim in them is contradicted by the tree | no stale claim remains in those files, and `AGENTS.md` marks `docs/specs/*` untrusted |
| 1 | **ODD out of `.cache/`**: copy `odd-2010-malariasentinel.tex` and `odd-2010-template.tex` into `docs/concepts/abm/` (a copy plus `git add` — the source is gitignored, so `git mv` refuses it) and build unmodified | a tracked `.tex` compiles to PDF — verified 2026-11-16, 32 pages |
| 2 | **Two shared artefacts**: the stance note in `docs/concepts/` and the drafting skill in `.pi/skills/` | both exist and are usable by a writer who has never seen the ODD review |
| 3 | **Per-stage question sets**: one subagent per stage reads that stage's material and returns its questions with citations (the ODD's discipline: read before asking) | a question set and a checklist per stage, each traceable to code/notes citations, stored as the stage's template beside its document |
| 4 | **Value generator** + contracts file + first workflow | a build reproduces the generated tables byte-for-byte (`git diff --exit-code`) |
| 5 | **Pilot `download`**: an agent drafts from the question set; a human annotates; annotations become a plan under `docs/plans/`; the plan's application updates the document | one non-ABM document written, read by someone without a code profile, revised once through the full loop |
| 6 | **Publication**: one PDF published and linked once from the site; one "Technical reference" entry | a reader reaches both in ES and EN |
| 7 | **Generated technical reference**: comment polish on the contract-defining headers, then Doxygen + pdoc generation into the namespaced directories | published, linked, and the flag/file contract documented |
| 8 | **Warnings-only coherence review** on PRs; measure its false-positive rate over 20 PRs of history | a first-pass rate is known before anyone relies on it |
| 9 | **`data/` untracking (option B)**: zip `data/` to the repository's parent directory and verify it (`unzip -t`); `git rm -r --cached data` (never `rm`) with a blanket `data/` ignore rule plus `!data/README.md`; update `data/README.md` for the new restore path | backup restores the tree; `git ls-files data/` shows only `data/README.md`; fresh clone → `uv sync` → `download` (manifest rebuilt from nothing) → ingest → `abm --days 1` passes |

### Decisions that shape the architecture

- **D1 — Generate facts, write semantics.** Any number, key, symbol or path in
  a conceptual document is emitted at build time; prose carries only what
  survives a refactor.
- **D2 — Precedence rule, stated once.** Values → `model_constants.yaml` wins.
  Contract values and names → the generated contract table wins. Semantics →
  the concept document wins. On contradiction, the lower authority is the bug.
  Stated in the document that owns the content (D5); there is no shared page.
- **D3 — Warnings only, no gates.** The mechanical signals above are inputs the
  reviewer may cite, not pass/fail tests. No anchor-existence check, no
  presence rule, no waiver trailer, no required status.
- **D4 (superseded by R4) — The document changes as the plans land.** The
  clean ODD is the base for `docs/concepts/abm/`, and each application of a
  plan changes the part of the document it invalidates. No status macros, no
  per-section `\asbuilt{}`/`\target{}` metadata. Accepted cost: staleness
  relative to an in-flight plan is invisible to the reviewer; that signal
  lives in the plan tracker, not in the document.
- **D5 — Ownership by use; no common substrate.** The stage that uses a piece
  of content documents it. Coherence is checked at the seams by adjacency.
  Repetition between stages is accepted: it is where drift becomes visible.
- **D6 — Truth pass before any checker** (Stage 0). A baseline that lies
  produces a gate that reports its own debt. Scope excludes `docs/specs/*`
  (author decision, 2026-11-16): they are marked untrusted instead of
  repaired, because they are scheduled for deletion.
- **D7 — ODD first out of `.cache/`** (Stage 1), as a copy plus `git add`.
- **D8 — `data/` is last** (Stage 9), and its removal is a safety problem
  before it is a git problem. Its pre-work is superseded by the author's
  option B (2026-11-16): one zip in the repository's parent directory, then
  `git rm -r --cached data` — the manifest rebuilds on the next `download`,
  so no relocation, no `MAL_DATA_ROOT`, no restore script.
- **D9 — Experiment packages and any top-level system document remain the
  author's decision.** The cycle/DAG gap against Kelly et al. (2012) is
  recorded, not actioned.

--------------------------------------------------------------------------------

## Alternatives Considered

### Alternative A: Keep the specs and fix them

*   **Pros**: The specs already exist; their invariant IDs and `affects` graph
    are the only machine-readable dependency data in the repo; fixing prose is
    cheaper than authoring 5,400–7,100 LaTeX lines.
*   **Cons**: Too strict and tied to code — a behaviour-preserving refactor
    still forces edits, which is how they became useless. Their checks were
    never executed: no drift-check agent exists, there is no `.github/`
    directory, and `tools/run_all_tests.sh` always exits 0.
*   **Reason for Rejection**: Rejected by author: too strict and tied to code;
    a refactor that preserves behaviour still forces edits, which is how they
    became useless. Lenses add the mechanical reason: keeping them keeps a
    document class with 100% pass rate and 0% enforcement.

### Alternative B: Contract as a generated artefact (machine-readable interface files)

*   **Pros**: The band names, sentinel values and sidecar keys that a prose
    reviewer misses would be caught mechanically by a `grep`; a deterministic
    checker needs structured input.
*   **Cons**: It recreates the spec system under another name — a human-written
    contract document that must be kept in sync, with an executor this time,
    in a repo with no workflows today.
*   **Reason for Rejection**: Rejected by author: it recreates the spec system
    under another name. Kept only as a build-time generator feeding the LaTeX
    (see D1), not as a human document.

### Alternative C: Unit = package or module instead of pipeline stage

*   **Pros**: Packages are where the code lives, so a package map needs no
    inference; ~44 of ~62 non-test modules in `mal-core/src` map to exactly one
    package anyway.
*   **Cons**: Packages do not describe the system. The `mal-core` CLI, the
    manifest catalog and `model_constants.yaml` serve all six stages, so a
    package-unit corpus would put the most shared content in one package's
    document and make the seams invisible.
*   **Reason for Rejection**: Rejected by author: packages do not describe the
    system; stages do. The stage unit matches `docs/specs/` and the `malariasim`
    subcommands 1:1, so the maintainer's mental map survives the reorg.

### Alternative D: An ODD for every stage

*   **Pros**: One external standard (Grimm et al.), one proven review
    discipline, and the ABM document proves the format works at 32 pages.
*   **Cons**: The ODD answers a model-description question. `download` has no
    entities and no time steps; forcing an "Entities" section onto it produces
    empty scaffolding. Eleven of the twelve ODD design concepts are about
    agency, which only `abm` has.
*   **Reason for Rejection**: Rejected by author: the ODD answers a
    model-description question; `download`/`ingest` need a different one (where
    data comes from, in what format, how it is transformed, what it becomes).

### Alternative E: Six per-typology templates authored up front by one subagent per phase

*   **Pros**: Uniform output; one pass instead of six investigations; a
    reviewer could check every document against a fixed shape.
*   **Cons**: A template authored and answered by the same agent, reviewed by
    nobody, is a formatting convention with a 100% pass rate — the spec system
    rebuilt with more pages. A shared template produces a document that
    explains the theory generically instead of explaining it.
*   **Reason for Rejection**: Rejected by author, 2026-11-16, on the stated
    ground that a shared template produces generic explanation. Adopted
    instead: per-stage question sets found per stage, in the ODD's own
    discipline of reading the material before asking, with the shared stance
    (S1–S10) as the common instrument and the section list free.

### Alternative F: A seventh `shared/` substrate document, an ownership matrix, or `\input` fragments

*   **Pros**: The four genuinely cross-cutting obligations (manifest schema,
    spatial frame, habitat theory, parameter provenance) get a single owner;
    `k_habitat` would be described once instead of six times; a fragment
    mechanically guarantees the invariant instead of promising it.
*   **Cons**: A seventh document is a silo that every stage must read and keep
    current; an ownership matrix is a maintenance artefact with no reader; the
    seam between `ingest` (computes H) and `abm` (applies S and K) cuts one
    equation set in half, which the planned packs then change on both sides.
*   **Reason for Rejection**: Rejected by author, 2026-11-16: the owner of each
    piece of content is the stage that uses it, and the coherence check happens
    at the seams by adjacency — a stage's outputs against the next stage's
    inputs. No common artefact, no standard imposed between stages, repetition
    accepted.

### Alternative G: Tier the corpus (formal LaTeX for `abm` only; Markdown for the rest; defer the stages with no named reader)

*   **Pros**: Answers the strongest cost argument in the brief: 7.5–20
    person-days of authoring for five documents that currently have no named
    external reader; the one document with an external standard and audience
    (`abm`, ODD/replication) is the one already written; markdown needs no
    toolchain.
*   **Cons**: Two document classes means two authoring disciplines and two
    review postures; markdown is the class that rotted in the first place;
    deferring three documents leaves their specs as the only description
    until someone volunteers.
*   **Reason for Rejection**: Not adopted — the author chose LaTeX for all six.
    Recorded here because every lens that did the cost arithmetic raised it,
    and because a later reversal should be a decision, not a discovery.

### Alternative H: Committed PDFs in `docs/` as-is

*   **Pros**: The legacy `main:/docs` Pages build publishes whatever is
    committed, so a committed PDF is the only way to get a stable, permanent
    link with no redirects and no workflow.
*   **Cons**: pdfTeX embeds `CreationDate` and a trailer ID, so byte-identical
    rebuilds do not exist without `SOURCE_DATE_EPOCH` and a reproducible TeX
    toolchain; reviewers cannot diff binaries; every documentation change
    produces an opaque blob commit, and a bot push dismisses stale approvals
    under the current ruleset.
*   **Reason for Rejection**: Not adopted as-is; incompatible with "compiled in
    CI" unless CI commits them back to the branch. Resolved as decision I1-A
    (2026-11-16): CI compiles and commits the PDF to the PR branch, with
    equality checked on extracted text (`pdftotext -layout`), not on bytes,
    until determinism is measured. The size of the binary churn in history is
    unmeasured.

### Alternative I: Pages migration to a build workflow

*   **Pros**: The natural home for both PDFs and generated Doxygen/pdoc output;
    no binaries in git, no staleness, one place to enforce "the site always
    builds", and the only option that solves the generated-pages style problem
    structurally.
*   **Cons**: It touches the thing that currently works. `CNAME`, the 200 KB
    hand-written `index.html`, favicons and the web manifest must be
    reproduced by the new pipeline or served from the same tree; a mistake
    takes the public site down, on a repo with zero workflows today.
*   **Reason for Rejection**: Rejected for this phase: it puts the CNAME,
    `index.html` and favicons at risk for a benefit the concept does not
    require. PDFs and generated docs must fit under the legacy build, be
    published as release assets, or be pushed to the branch by the workflow.

### Alternative J: LLM gate as a required check

*   **Pros**: An LLM is the only judge that can read prose and code side by
    side; the author asked for rejection on incoherence, and only an LLM can
    see incoherence in prose.
*   **Cons**: All seven lenses rejected it: it is unfalsifiable, it gives an
    agent merge authority over the maintainer, fork PRs get no secrets so the
    check no-ops exactly where unfamiliar code arrives, and a bot push dismisses
    stale approvals under the current ruleset. The project already answered
    this in the opposite direction: `scoring/spec.md` INV-12 requires the LLM
    verdict to be non-gating, and `AGENTS.md` classifies reviewing subagents as
    `ask`, not `allow`.
*   **Reason for Rejection**: Rejected by all seven lenses; the author adopted
    warnings only (D3): the review system reports incoherences and never
    blocks, never rejects, never imposes structure on the documents.

### Alternative K: Deterministic checker tier (anchor existence, presence rule, `Coherence-Waiver:` trailer)

*   **Pros**: Restricting rejection to absence and anchor checks is the only
    version of the author's "rejection on error" request that survives contact
    with a false positive; a presence rule guarantees a stage change cannot
    merge with no document touch at all.
*   **Cons**: Gating constrains the design of the documents: a presence rule
    forces documents to become checkable shapes, which is the spec system's
    failure mode; a waiver trailer reintroduces the per-spec version policy
    noise. Under D3 there is no gate tier, so the only guaranteed protection
    left is generated values — every other drift class becomes a warning a
    human may or may not read.
*   **Reason for Rejection**: Rejected by author, 2026-11-16: gating constrains
    the design of the documents and forces them to become checkable shapes.
    The mechanical signals survive as inputs the reviewer may cite; the only
    automatic guarantee left is the build-time generation of values. Stated
    plainly: the absence of a presence rule means a stage change can be merged
    with no document touch and no signal; the mitigation left is the reviewer's
    own coverage of the diff.

### Alternative L: `git filter-repo` to purge `data/` from history

*   **Pros**: If any dataset blob is in history, a rewrite removes it for
    good; `data/` is already ~95% untracked (16 tracked files against 4.0 GB).
*   **Cons**: Every SHA changes — the ODD's hand-typed provenance SHAs and
    every commit reference in `docs/plans/` dangle; all branches and tags are
    force-pushed; PR refs break. And if `data/ghana/` was always ignored
    (`.gitignore:20`), there is nothing to purge.
*   **Reason for Rejection**: Deferred behind a blob-size scan: if
    `data/ghana/` was always ignored, there is nothing to purge and the
    rewrite would only break every SHA referenced in `docs/plans/` and in the
    ODD. Run
    `git rev-list --objects --all | git cat-file --batch-check='%(objecttype) %(objectsize) %(rest)' | sort -k2 -n | tail -20`
    first; if the largest blob is under ~5 MB, leave history alone.

### Alternative M: Write the ABM document to the post-pack target design

*   **Pros**: Packs become implementations of the document rather than future
    corrections of it; the document absorbs churn as intent instead of error;
    reviewers can check the packs against it.
*   **Cons**: The document then states, for months, mechanisms the code does
    not have — which is authority over the code, the exact thing the author
    rejected ("coherence, not source of truth"). Seven of thirteen packs touch
    what the ABM document must say, so more than 40% of its mechanism sections
    would be knowingly false on publication day.
*   **Reason for Rejection**: Rejected by author, 2026-11-16 (R4): the clean
    ODD as-built is the base, and each application of a plan changes the part
    of the document it invalidates. The cost is stated: with no status markers
    and a warnings-only review, staleness relative to an in-flight plan is
    invisible to the reviewer; that signal lives in the plan tracker
    (`docs/plans/in-process/`), not in the document.

### Alternative N: Untrack `data/` with a single zip backup (chosen, 2026-11-16)

*   **Pros**: One verified archive in the repository's parent directory
  restores everything, including the four files `download` never regenerates
  (the paper, the seven map renderings, the `eml.xml`/`meta.xml` sidecars).
  No manifest relocation, no `MAL_DATA_ROOT`, no restore script, no offline
  checksum inventory — the plan shrinks from seven entries to four, and the
  last of them is a `git rm --cached` that cannot destroy the working copy.
*   **Cons**: The backup lives outside version control: it is one copy, in one
  place, that nobody will test until the day it is needed. The manifest is
  lost with `data/` — but it is regenerated by the next `malariasim download`,
  because `run_download` selects datasets from the downloader registry and
  re-registers each one through `update_dataset`
  (`mal-core/src/mal_core/download/runner.py:69`, `manifest.py:116`).
*   **Reason for Acceptance**: Author decision (2026-11-16). The manifest
  argument makes the elaborate pre-work unnecessary: the inventory that
  `data/` holds is not the source of truth for *what to download* — the
  registry is — so losing it costs a re-download, not a capability. The
  acceptance test is therefore the zip's `unzip -t` plus a clean-room clone
  that downloads from nothing.

--------------------------------------------------------------------------------

## Detailed Implementation

One unified list, ordered by stage. Every file that the plan touches appears
once, with what changes and why. Two of these files are protected by project
convention and need explicit user approval when edited: `AGENTS.md` and
`.gitignore` — each is flagged below. No code is specified here; signatures and
schemas are described in prose.

### Stage 0 — Truth pass (one commit, no new concepts)

#### 1. `docs/README.md` (Modify)

*   **Type / Scope**: Documentation index.
*   **Proposed Changes**: Remove the six paths that do not exist
    (`specs/self_improve/`, `diagrams/`, and the four presentation/status
    files). The exit condition is that no listed path is absent from the tree.
*   **Rationale**: This file is the entry point of the docs tree; a reader who
    follows it into nothing distrusts everything after it. Cheapest claim in
    the stale-claims table to fix.

#### 2. `AGENTS.md` (Modify — protected file, requires explicit user approval)

*   **Type / Scope**: Agent guide.
*   **Proposed Changes**: Three changes.
    (a) Rewrite the "Calibration framework conventions" section (it currently
    instructs editing `thresholds.yaml`,
    `scorers/composite.py::DEFAULT_WEIGHTS`, and running a deleted pytest
    harness) to describe what actually exists: `COMPOSITE_WEIGHTS` in
    `mal-core/src/mal_core/scoring/registry.py`, `min_score`/`hard_floor` as
    class attributes on `Scorer`, and no calibration pytest harness.
    (b) Remove `mal-ghana-sim/` from the monorepo layout table and correct the
    package count (five `pyproject.toml` files: `mal-commonlib`, `mal-core`,
    `mal-execution`, `mal-data-explorer`, plus the undocumented
    `social-networks/`).
    (c) Add an explicit **untrusted-documents** note: `docs/specs/*` is
    scheduled for deletion and is **not authoritative** — during the editing
    sessions no agent may take a spec claim as true, and must verify any
    spec-derived fact against the code before acting on it.
*   **Rationale**: `AGENTS.md` is the first file every agent reads; today it
    sends agents to edit three files that do not exist. It is also the
    baseline any future coherence review compares against — a lying baseline
    makes the review report the plan's own debt (D6). The untrusted-documents
    note is the author's substitute for repairing the specs (2026-11-16):
    the specs are deleted within this plan, so a warning that outlives them is
    the correct fix, and a half-updated spec is not.

#### 3. `docs/specs/*` (Not modified — marked untrusted instead)

*   **Type / Scope**: Specs (retired later, stage by stage).
*   **Proposed Changes**: None. The three stale claims in
    `docs/specs/abm/spec.md`, `docs/specs/data/spec.md` and
    `docs/specs/commonlib/spec.md` are left in place, and `AGENTS.md` (file 2)
    declares the whole `docs/specs/` tree untrusted and pending deletion.
*   **Rationale**: Author decision (2026-11-16): the work happens on a
    secondary branch in a short-lived session, and the specs are deleted by
    this very plan — repairing them buys nothing that outlives the file, and
    half-repaired specs are worse than clearly-dead ones. The risk of a
    false spec being read as true is covered by the explicit warning, not by
    an edit.

#### 4. `mal-core/src/mal_core/abm/include/mal_abm_fast/wire.hpp` (Modify)

*   **Type / Scope**: C++ header (contract-defining).
*   **Proposed Changes**: Remove or replace the comment citing
    `docs/abm-status.md:79`, a file that does not exist.
*   **Rationale**: A dangling path in a source comment is exactly the class of
    drift the mechanical signals list (signal 6) will later warn about; fixing
    it by hand now keeps Stage 0's exit honest.

#### 5–9. The five remaining contract-defining headers (Modify)

Files: `mal-core/src/mal_core/abm/include/mal_abm_fast/output_contract.hpp`,
`habitat_availability.hpp`, `habitat_engine.hpp`, `coordinator.hpp`,
`config.hpp`.

*   **Type / Scope**: C++ headers (contract-defining; the polish scope for
    Stage 7 starts here too).
*   **Proposed Changes**: Correct the statements the code contradicts:
    `output_contract.hpp:3-5` still says band 1 = `adult_occupancy`, band 2 =
    `host_seeking_pressure` while the code writes
    `{"adult_patch_count","adult_cell_count"}`; the same header says the
    sidecar lists `k_max` (retired at contract 4.0); `:71-73` cites
    `docs/specs/abm/spec.md` as the authority for sidecar key order (the
    authority this design deletes). Full audit of the six headers' prose
    against the code — the "current text of the contract-defining headers is
    not fully audited" open question is settled here.
*   **Rationale**: These six headers are where the contract lives; they are
    also the input to Stage 7's Doxygen build. Fixing content first means the
    generated reference is not structurally complete and semantically false.

### Stage 1 — ODD out of `.cache/`

#### 10. `docs/concepts/abm/odd-2010-malariasentinel.tex` (Create — copy, then `git add`)

*   **Type / Scope**: LaTeX source (the ABM conceptual document).
*   **Proposed Changes**: Byte-for-byte copy of
    `.cache/odd-latex/odd-2010-malariasentinel.tex` (the clean version without
    review comments). Not `git mv`: the source path is gitignored
    (`.gitignore:53`), so `git mv` refuses it. The annotated review copy
    (`odd-2010-malariasentinel-notes.tex`) stays in `.cache/` — personal and
    team material whose content already lives in the plans it produced.
*   **Rationale**: Until a `.tex` is tracked, "PDFs built in CI" has no input
    and reviewers cannot review changes to it. Verified 2026-11-16:
    `latexmk -pdf` on the unmodified file succeeds, 32 pages.

#### 11. `docs/concepts/abm/odd-2010-template.tex` (Create — copy, then `git add`)

*   **Type / Scope**: LaTeX template (the ABM stage's question set).
*   **Proposed Changes**: Byte-for-byte copy of
    `.cache/odd-latex/odd-2010-template.tex`, stored beside the document it
    questions (author's directive, 2026-11-16). This is the ABM stage's
    "template with the questions": the official ODD 2010 element list that
    the document answers.
*   **Rationale**: Document and questions live together, so a writer always
    finds both. For `abm` the question set is the official ODD template — an
    external standard, not something to author.

#### 12. `docs/concepts/abm/` build proof (no new file)

*   **Proposed Changes**: Run `latexmk -pdf odd-2010-malariasentinel.tex`
    unmodified in the tracked location; commit nothing else.
*   **Rationale**: Exit condition of Stage 1 — a tracked `.tex` compiles to
    PDF. Already verified on the unmodified file.

### Stage 2 — The two shared artefacts

#### 13. `docs/concepts/README.md` (Create)

*   **Type / Scope**: Documentation (the stance note).
*   **Proposed Changes**: "How to write a conceptual document": the stance
    S1–S10 stated in full (Appendix A of this plan), the devices
    that transfer (notation table with code-name aliases, schedule pseudocode
    plus consequences list, parameter tables with a provenance column,
    "consequences worth stating", "origin and rationale", data-versus-choice,
    negative purpose list, declaration of absences, evidence appendix), and
    the ODD as the worked example. Explicitly not a template: it fixes a
    stance and a method, never a section list.
*   **Rationale**: The only shared writing instrument of the six documents
    (R1). A writer who has never seen the ODD review reads this page and
    knows how to ask.

#### 14. `.pi/skills/concept-doc/SKILL.md` (Create)

*   **Type / Scope**: pi skill (project-level).
*   **Proposed Changes**: A lightweight skill carrying the drafting
    operation: read the stage's question set, read the stance note, draft the
    document from the material, cite every claim, generate every value. It is
    the supported action for changing the question set itself.
*   **Rationale**: R1: the note fixes the stance, the skill fixes the
    operation; together they are the only two shared artefacts, and neither
    prescribes a section list. Changing the question template becomes a
    supported action rather than an ad-hoc edit.

### Stage 3 — Per-stage question sets and checklists

For each of the five non-ABM stages: one subagent reads that stage's material
(code, specs, plans) and returns the stage's questions with citations, in the
ODD's discipline of reading before asking. The `abm` question set already
exists as `odd-2010-template.tex` (file 11) and is not re-authored.

#### 15–19. `docs/concepts/<phase>/questions.md` (Create ×5)

Files: `docs/concepts/download/questions.md`,
`docs/concepts/ingest/questions.md`, `docs/concepts/scoring/questions.md`,
`docs/concepts/training/questions.md`,
`docs/concepts/prediction/questions.md`.

*   **Type / Scope**: Documentation (question set + done-checklist, Markdown).
*   **Proposed Changes**: Each file holds two parts: (a) the stage's question
    set — the questions its document must answer, every one traceable to a
    code/notes citation; (b) the stage's checklist — what "done" means for
    that document (R5). Kept beside the stage's document, per the author's
    directive that the template with the questions lives with the LaTeX.
    Format is Markdown: these are working inputs to the drafting operation,
    not published artefacts, so they need no LaTeX build.
*   **Rationale**: I5 — no generic template; each stage gets the questions it
    needs, found by reading that stage's material. The checklist is per stage
    and does not generalise the document's structure.

### Stage 4 — Value generator, contracts file, first workflow

#### 20. `docs/concepts/contracts.yaml` (Create)

*   **Type / Scope**: Machine-readable contracts input (not a human document).
*   **Proposed Changes**: A small file describing each output artefact:
    artefact → producer stage → consumer stages → contract version →
    compatibility rule → band/variable names → sentinel value. Content
    sourced from the code (`STATE_BAND_NAMES` in `wire.hpp`, sidecar key
    definitions in `output_contract.hpp`, `contracts.*` in
    `model_constants.yaml`). It is read only by the generator (file 21); no
    prose document cites it as authority — D2 gives the *generated table* the
    authority, not this file.
*   **Rationale**: D1/D2 need a machine-readable source for contract names and
    versions so the generated contract table can win on contradiction. It is
    a generator input, deliberately not a human-maintained spec: the rejected
    alternative B was a *human document*; this is data feeding the build.

#### 21. `tools/gen_concepts_values.py` (Create)

*   **Type / Scope**: Python script (build tool, not pipeline code).
*   **Proposed Changes**: Reads `mal-core/config/model_constants.yaml` (via
    the existing pydantic validation) and `docs/concepts/contracts.yaml`, and
    emits LaTeX into `docs/concepts/generated/`: per-stage parameter tables
    (name, meaning, unit, value, provenance tier), one contract table, and
    per-key macros (`\mskey{<dotted.key>}` expands to the current value).
    Deterministic output — same inputs, byte-identical files.
*   **Rationale**: D1: any number, key or symbol in a document is emitted at
    build time. A key renamed or removed in YAML becomes an undefined control
    sequence and fails `latexmk`. This is the design's only automatic
    failure, and it is a property of the build (see also signal 1: dotted keys
    vs YAML with printed values).

#### 22. `docs/concepts/generated/` (Create — directory of generated `.tex`)

*   **Type / Scope**: Generated LaTeX fragments (`params-<phase>.tex`,
    `contracts.tex`).
*   **Proposed Changes**: Output directory of file 23; committed so local and
    CI builds are identical and reviewable in the PR diff. Documents
    `\input{generated/...}` it; no document types a value by hand.
*   **Rationale**: Stage 4's exit condition — a build reproduces these
    byte-for-byte (`git diff --exit-code` after regeneration).

#### 23. `tools/build_concepts.sh` (Create)

*   **Type / Scope**: Shell script (build entry point).
*   **Proposed Changes**: Runs the generator (file 21), then `latexmk -pdf`
    over every `.tex` under `docs/concepts/`, then regenerates and fails if
    `git diff --exit-code` shows drift in `docs/concepts/generated/`. Same
    command locally and in CI.
*   **Rationale**: One build recipe, no divergence between a developer's
    machine and the workflow; the byte-for-byte exit condition is executable.

#### 24. `.github/workflows/concepts.yml` (Create)

*   **Type / Scope**: GitHub Actions workflow (the repository's first — there
    is no `.github/` directory today).
*   **Proposed Changes**: On pull requests touching `docs/concepts/**`,
    `mal-core/config/model_constants.yaml`, or `docs/concepts/contracts.yaml`:
    run `tools/build_concepts.sh`, then compile each document and (on the PR
    branch, decision I1-A) commit `docs/concepts/<phase>/<phase>.pdf` back to
    the branch. PDF equality is checked on extracted text
    (`pdftotext -layout`), not on bytes, until determinism is measured. The
    bot push dismisses stale approvals under the current ruleset — a workflow
    design constraint, documented in the workflow header, not a blocker.
*   **Rationale**: Stage 4 exit (first green run) and Stage 6 publication
    (I1-A: CI commits the PDF so the legacy `main:/docs` Pages build publishes
    it at a stable path). Fork PRs cannot receive the push; their PDF appears
    after merge — accepted under the warnings-only regime.

### Stage 5 — Pilot `download`

#### 25. `docs/concepts/download/download.tex` (Create)

*   **Type / Scope**: LaTeX source (first non-ABM conceptual document).
*   **Proposed Changes**: Drafted by an agent from
    `docs/concepts/download/questions.md` and the stance note; answers every
    question in the set in the stage's own structure; inputs/outputs are one
    section among others; all values come from `\input{generated/...}`; every
    code symbol glossed at first use (R3); examples are described situations,
    not code snippets (R10). Internal seam kept visible as a section: AOI
    reduction happens after areal-fraction aggregation (R9).
*   **Rationale**: Stage 5 exit — one non-ABM document written, read by
    someone without a code profile, and revised once through the full loop.
    Pilot on the smallest stage, not the largest.

#### 26. `docs/plans/in-process/<plan-name>.md` (Create — as annotations arrive)

*   **Type / Scope**: Plan files (existing directory and mechanism).
*   **Proposed Changes**: Human annotations on the pilot document are
    distilled into plans naming the document section they invalidate and the
    code change required — the same mechanism that produced the 13
    `odd-fixes` packs. Applying a plan updates code and document in the same
    PR.
*   **Rationale**: R2's loop, end to end. This is the main detection
    instrument under D3 (warnings-only): the human annotation step, with the
    annotations as the defect channel.

### Stage 6 — Publication

#### 27. `docs/documentacion.html` (Create)

*   **Type / Scope**: Site page (HTML, legacy Pages build).
*   **Proposed Changes**: A separate documentation page under `docs/`, linked
    from the site navigation, carrying its own ES/EN dictionaries (R6). It
    lists the six conceptual documents with links to their committed PDFs
    (`docs/concepts/<phase>/<phase>.pdf`), the stance note, and later the
    technical reference. Generated docs index — never a hand-maintained one.
*   **Rationale**: The landing page has zero links to any document today; its
    navigation is five in-page anchors. Keeping the new page separate leaves
    the 200 KB `index.html` and its i18n dictionary untouched except for the
    nav entry (file 28).

#### 28. `docs/index.html` (Modify)

*   **Type / Scope**: Site landing page (hand-written, ES-first).
*   **Proposed Changes**: Two changes in one commit: (a) truth pass on its
    three stale claims — "14 evaluadores" (reality: 13 composite dimensions +
    6 gates), "agents/K_MAX" (retired at contract 4.0), "9.466 celdas"
    (reality: 551 × 779 = 429,229 cells per the ODD); (b) add one nav entry
    pointing at `documentacion.html` — desktop nav, mobile drawer, footer
    row, and both `T.es`/`T.en` dictionaries, in the same edit.
*   **Rationale**: The site is the reader's entry point (CUJ 1) and today
    promises "documentación técnica accesible" while linking only GitHub. The
    four-edition rule (nav + drawer + footer + both dictionaries) is a
    property of this file's structure, not a choice.

### Stage 7 — Generated technical reference

#### 29. The six contract-defining headers, comment-polished (Modify)

Files (already touched in Stage 0, content completed here):
`wire.hpp`, `output_contract.hpp`, `habitat_availability.hpp`,
`habitat_engine.hpp`, `coordinator.hpp`, `config.hpp` — all under
`mal-core/src/mal_core/abm/include/mal_abm_fast/`.

*   **Proposed Changes**: Convert file-header prose and trailing `//` member
    comments to forms Doxygen attaches (`///`, `/** */`, `///<`, `//!<`),
    excluding `third_party/`, `font8x8_basic.hpp` and `tests/*.cpp` from the
    build. Content was already corrected in Stage 0; this pass is mechanical
    form conversion on the contract-defining headers only, not all 101 files.
*   **Rationale**: I2-A: polish scoped to where the contract lives, before
    generation. Zero Doxygen directives exist today; trailing `//` is
    invisible to Doxygen; a generated document from current comments would be
    structurally complete and semantically false.

#### 30. Python docstring corrections (Modify)

Files: `mal-core/src/mal_core/scoring/llm_scorer.py` (says "10 deterministic
scorers (D1..D10)"; registry has 13 composite + 6 gates),
`mal-core/src/mal_core/scoring/config.py` (uses `D16_suitability_auc`; real
name `D16_detection_coverage`), `mal-core/src/mal_core/habitat/constants.py`
(documents constants the module raises `AttributeError` for),
`mal-commonlib/src/mal_commonlib/config.py` (`SimParams.r_of()` calls
undefined `temp_suitability`; docstring cites `DESIGN.md`, which does not
exist).

*   **Proposed Changes**: Fix the four statements the code contradicts before
    pdoc publishes them; remove or correct the dead `r_of()` path.
*   **Rationale**: Same as file 31 — generation is cheap, truth is not.
    Publishing autodoc as-is publishes four known-false statements.

#### 31. `docs/reference/Doxyfile` (Create)

*   **Type / Scope**: Doxygen configuration.
*   **Proposed Changes**: `INPUT = mal-core/src/mal_core/abm/include/`,
    `RECURSIVE = YES`, `EXTRACT_ALL = YES`, `HAVE_DOT = NO`,
    `GENERATE_LATEX = NO`, output to `docs/reference/cpp/`, excluding
    `third_party/` and `tests/`.
*   **Rationale**: I2-A. Namespaced output (R7) so Doxygen's `index.html` and
    `_`-prefixed directories cannot collide with pdoc's under the legacy
    Pages build. Greenfield today — no Doxyfile exists, so it will be done
    wrong by default unless specified.

#### 32. `tools/build_reference.sh` (Create)

*   **Type / Scope**: Shell script (reference generation entry point).
*   **Proposed Changes**: Runs Doxygen with file 33, runs pdoc over
    `mal_core` and `mal_commonlib` into `docs/reference/python/`, and emits a
    generated index page linking both surfaces plus the flag/file contract
    (I2-B, if built — see Open Questions; the script stubs it either way).
    Same command locally and in CI.
*   **Rationale**: One recipe for both generators; output lands somewhere
    greppable, which is the condition under which the reference has a real
    consumer (agents, IDE).

#### 33. `.github/workflows/concepts.yml` (Modify — extend)

*   **Proposed Changes**: Add a job on pushes to `main` touching
    `mal-core/src/mal_core/abm/include/**` or `mal-*/src/**/*.py`: run
    `tools/build_reference.sh`, commit `docs/reference/**` back to the branch
    (same I1-A topology and same stale-approval constraint).
*   **Rationale**: Generated reference must be published under the legacy
    Pages build, which compiles nothing; committing is the only topology that
    works without a Pages migration (rejected this phase).

### Stage 8 — Warnings-only coherence review

#### 34. `.github/workflows/coherence-review.yml` (Create)

*   **Type / Scope**: GitHub Actions workflow (PR-triggered).
*   **Proposed Changes**: On pull requests: extract the mechanical signals
    (dotted keys vs `model_constants.yaml` with printed values; `\code{}`
    identifiers vs Python/C++ symbols; contract versions vs
    `model_constants.yaml:contracts.*`; recomputable numbers from
    `aois.yaml`; `latexmk -Werror`; named `docs/…`, `papers/…`, `scripts/…`
    paths vs the tree; documented outputs vs consumer globs; changed path →
    candidate document; `% sources:` freshness), assemble diff + affected
    stage documents + in-process plans, and hand them to an LLM reviewer that
    posts a PR comment naming the passage that no longer matches the code,
    quoting both. `continue-on-error: true`; the check is never required.
    Fork PRs (no secrets): mechanical signals still run, the LLM step reports
    "semantic check skipped (fork)" in the comment. Secret-absence resolves
    as `neutral`, never `failure`. Bot-loop guard: the workflow does not
    trigger on its own comment pushes.
*   **Rationale**: D3: warnings only, no gates — no anchor-existence check,
    no presence rule, no waiver trailer, no required status. The mechanical
    signals are inputs the reviewer may cite, not pass/fail tests. Exit
    condition: false-positive rate measured over 20 PRs of history before
    anyone relies on it.

#### 35. `.github/concepts-review-prompt.md` (Create)

*   **Type / Scope**: Reviewer prompt (workflow input, not a document).
*   **Proposed Changes**: The standing instructions for the LLM reviewer:
    compare the diff against the conceptual documents of the affected stages;
    quote both sides in every finding; report incoherences only; never request
    changes, never approve, never propose document structure; state explicitly
    that the comment is advisory and the merge is unaffected. Carries the
    division of labour: what stays human (process ordering, formula-vs-code
    equivalence, implemented-vs-unimplemented statements, blast radius,
    provenance) is listed as "ask a human", not as a check.
*   **Rationale**: The regime has no deterministic presence rule, so the
    reviewer's own coverage of the diff is the only mitigation for a stage
    change merged with no document touch — the prompt is where that
    responsibility is stated.

### Stage 9 — `data/` untracking (last step, after the backup is proven)

The author's decision (2026-11-16) supersedes the D8 pre-work: the manifest is
rebuilt automatically by the next `malariasim download`, so there is no
manifest relocation, no `MAL_DATA_ROOT`, no restore script and no offline-copy
inventory. The safety net is one zip archive in the repository's parent
directory, written and verified before anything is untracked.

#### 36. `../MalariaSentinel-data-backup-<YYYY-MM-DD>.zip` (Create — outside the repository)

*   **Type / Scope**: Backup archive (parent directory of the repository, never
    inside it — a tracked or ignored in-tree archive is not a backup).
*   **Proposed Changes**: `zip -r` the whole `data/` tree (tracked and ignored
    files alike: the 4 GB of downloaded products and the 16 small tracked
    files), then verify with `unzip -t` and write the archive's `sha256`
    next to it. The archive's path and checksum are recorded in
    `data/README.md` (file 39).
*   **Rationale**: Git is not a backup for the ignored 4 GB — history contains
    none of it — and the tracked 16 files are not recoverable from a
    `git rm --cached` if the working copy is lost. One verified zip is the
    cheapest real safety net: it restores exactly what was there, including
    the files `download` does not regenerate (`moua_2016.pdf`, the seven
    `data/maps/*.png` renderings, the `eml.xml`/`meta.xml` sidecars).

#### 37. `.gitignore` (Modify — protected file, requires explicit user approval)

*   **Type / Scope**: Ignore rules.
*   **Proposed Changes**: Replace the current per-directory `data/` entries
    (`data/ghana/`, `data/accra-coastal-test/`, the `data/**` globs) with one
    blanket `data/` rule plus a `!data/README.md` negation, so the documentation
    stays tracked and everything else under `data/` does not.
*   **Rationale**: The untracking rule itself. Protected file: the change needs
    the user's explicit approval, and it is the step where a mistake loses the
    local copy — which is why the zip exists and is verified first.

#### 38. `git rm -r --cached data` (index operation — not a file)

*   **Type / Scope**: Git index.
*   **Proposed Changes**: `git rm -r --cached data` (never `rm`): the files stay
    in the working tree, they leave the index. After this, `git ls-files data/`
    shows only `data/README.md`.
*   **Rationale**: The index is what makes `data/` travel to GitHub. Removing it
    from the index, with the working tree untouched, is the whole of
    "untracking" — `rm` would destroy the local copy the zip was made from.

#### 39. `data/README.md` (Modify)

*   **Type / Scope**: Data documentation (the only tracked file under `data/`).
*   **Proposed Changes**: Document the backup archive's path and checksum, the
    re-download path (`malariasim download --aoi <aoi>` rebuilds
    `data/<aoi>/manifest.json` from the registry and re-registers every
    dataset), what is *not* regenerated by that command (the paper, the map
    renderings, the sidecars) and therefore depends on the zip, and the licence
    constraints that govern re-hosting (ODbL share-alike on `host_static.nc`,
    `mobility_*.csr`, wildlife proxy; CC BY-NC 4.0 on `guf/` and `colombia_vl/`).
*   **Rationale**: The manifest is rebuilt by the downloader, so the only
    surviving loss is the material the downloader never produced — and the file
    that survives untracking is the one that must say so.

### Spec retirement (distributed across stages, not a stage)

#### 40–47. `docs/specs/<phase>/spec.md` and `docs/specs/_template.md` (Delete — one per stage)

Files: `download/spec.md` (with Stage 5), `data/spec.md` (its manifest schema
lands in the `download` document per D5), `ingest/spec.md`,
`commonlib/spec.md` (spatial frame lands in the stage that first needs
`(H,W)`), `abm/spec.md` (after Stage 1's document is current), `scoring/spec.md`,
`training/spec.md`, `prediction/spec.md`, and `_template.md` with the last
one.

*   **Proposed Changes**: Each spec is deleted in the same commit that lands its
    conceptual equivalent — section-level cut-over: the change that adds §X
    deletes §X. No file-level coexistence window where two authorities
    describe the same contract.
*   **Rationale**: Brief goal — retire stage by stage with no information
    loss: semantics move to the conceptual document, values to the generated
    tables. File-level retirement would guarantee two authorities for months
    (structural F7), so retirement is distributed, not batched.

### Verification Plan

*   **Stage 0**: `find`-based check that every path named in
    `docs/README.md` and `AGENTS.md` exists; `AGENTS.md` states that
    `docs/specs/*` is untrusted and pending deletion (the three spec claims
    above are deliberately left standing — this design does not repair them);
    each of the six headers' contract statements diffed against
    `STATE_BAND_NAMES`/sidecar definitions in code.
*   **Stage 1**: `latexmk -pdf` on the tracked unmodified `.tex` exits 0 and
    produces a 32-page PDF (verified 2026-11-16; re-run after the copy).
*   **Stage 2**: A reader who has never seen the ODD review uses the stance
    note to answer one sample question set (manual, exit condition of Stage
    2).
*   **Stage 3**: Every question in each `questions.md` carries at least one
    `file:line` citation; spot-check 5 per stage against the cited lines.
*   **Stage 4**: Run `tools/build_concepts.sh` twice; second run leaves
    `git diff --exit-code` clean on `docs/concepts/generated/`. Rename one key
    in `model_constants.yaml` in a scratch branch and confirm `latexmk` fails
    with an undefined control sequence — the design's only automatic failure,
    demonstrated on demand.
*   **Stage 5**: `docs/concepts/download/download.tex` compiles; a reader
    without a code profile answers the pilot checklist (CUJ 1); the document
    is revised once through the annotation → plan → PR loop (CUJ 4, CUJ 5).
*   **Stage 6**: From `malariasentinel.com` in both ES and EN, a reader
    reaches the `download` PDF in ≤2 clicks (CUJ 1); the three stale claims in
    `index.html` are gone.
*   **Stage 7**: `tools/build_reference.sh` exits 0; `docs/reference/cpp/`
    and `docs/reference/python/` are both present with their own
    `index.html`; grep confirms no `k_max`/two-band statement remains in the
    six headers; the flag/file contract page lists every CLI flag from
    `_introspect_flags`.
*   **Stage 8**: Run the reviewer over 20 historical PRs; record findings vs
    false positives; exit when a first-pass false-positive rate is known. A
    PR that changes only a comment under `mal_core/<stage>/` must produce no
    required-document signal (there is no presence rule — this asserts the
    absence of one, by design).
*   **Stage 9**: The zip exists in the repository's parent directory and
    passes `unzip -t`; `git ls-files data/` shows only `data/README.md` while
    the working tree still holds every file; clean-room clone → `uv sync
    --all-packages` → `malariasim download` (which rebuilds
    `data/<aoi>/manifest.json` from the registry, from nothing) → ingest →
    `abm --days 1` passes; restoring the zip over the clone reproduces the
    pre-untracking tree.
*   **Static analysis / linting**: unchanged — this design adds no production
    code; the only new Python (file 21) follows the repo's existing
    conventions and is exercised by its own exit conditions above.

--------------------------------------------------------------------------------

## Appendix A — The stance (S1–S10) and the devices that transfer

This appendix is the surviving content of the brief's ODD-method note
(`concepts_brief.odd-method.md`, deleted after this plan was written; the
brief itself remains in git history at commit `75dc50c`). It is reproduced
here so the plan does not depend on a file that is scheduled for removal.

### A.1 — The stance, stated independently of the element list

For a stage with no entities, no state variables and no time step — `download`:
where the data comes from, in what format, how it is transformed, what it
becomes — the ODD's method reduces to this. It is a **stance**, not a section
list: it says what the writer must have worked out, not in what order.

- **S1. Purpose first, mechanism separate.** What question does this stage
  exist to answer, and what would count as it having answered it? What is
  explicitly out of scope? The purpose is a filter, not a description.
- **S2. Name every magnitude with its identity, units, native resolution and
  target resolution.** Not "the population file" but the file, its key, its
  native resolution, the target resolution, the aggregation rule, and what was
  lost in the aggregation.
- **S3. Distinguish what arrives from outside from what is decided here.**
  Each choice — provider, year, AOI, resampling, floor, no-data rule — must be
  *named as a choice*, so a reader can vary it.
- **S4. Write the order of operations at the granularity where order matters,
  and state the consequences.** Pseudocode plus a table of step / actor /
  order / mode, followed by the consequences of that order.
- **S5. Give every constant a provenance tier and make it checkable.** Measured
  / literature-anchored / engineering prior / model definition / scenario
  default — and a number with no evidence behind it says so on its face.
- **S6. Separate what is state from what is derived from what is a cache.** The
  generalised restart test: if the stage were interrupted and restarted, what
  would have to be on disk to resume identically?
- **S7. Declare what is not done.** Unimplemented paths, absent inputs,
  dormant parameters, states the code never enters.
- **S8. State the outputs and their consumption contract.** What is emitted, at
  what resolution, under what naming and version, and who reads it — including
  whether that resolution is the right one to serve the purpose.
- **S9. Keep an evidence appendix.** Implementation notes (behaviours invisible
  from the description) and provenance/versioning/testing status (what is
  verified, what is not, what the artefact must not be used for).
- **S10. The discipline that makes the above bite:** the document must be
  checkable by someone who does not trust it. Every claim should resolve to a
  file, a key, a line or a number a reviewer can verify, and the standing
  reviewer question is "is this number, this behaviour, this file actually
  what you say it is?"

S5, S3, S7, S9 and S10 are the ones the reference document added to the ODD.

### A.2 — The load-bearing devices, and which transfer

| Device | What it buys | Transfers to `download`? |
|---|---|---|
| **Notation table** with the code-name alias in the symbol's parenthesis | Lets a reader hold document and source in one head; makes the Appendix-A defects checkable | Yes — same function, different nouns |
| **Schedule pseudocode + schedule table + consequences list** | The consequences list turns an ordering into falsifiable claims about results | Yes, at pipeline granularity: catalog → resolve → fetch → materialise → aggregate → write, and what each order forecloses |
| **Parameter tables with a Provenance column** | Makes the epistemic status of every number checkable by a third party | Yes, verbatim |
| **"Consequences worth stating" block per submodel** | Turns description into explanation; this is what reviewers hooked into | Yes |
| **"Origin and rationale" block per submodel** | Separates what the mechanism *is* from *why it was chosen* | Yes |
| **"What is data-based and what is a scenario choice"** | Names which numbers are measurements, which are estimates, which are choices | Yes — and it is an *addition* to the ODD, not an element of it |
| **Negative purpose list** ("The model is *not* intended for…") | Gives the reader a filter and the author a scope boundary | Yes |
| **Declaration of absences** ("Not implemented", "Absent from the delivered Ghana product", states the code never enters) | Makes incompleteness visible instead of silent | Yes |
| **Appendix A — implementation notes for replicators** | The place where protocol-level description admits it cannot capture the implementation | Yes |

### A.3 — Why the reference document was worth reading

The ~85 reviewer comments on the ODD split three ways: criticisms of
documentation adequacy (aggregation level, the scale at which randomness and
parameters live, output resolution design, duplicated state and dead
internals, a third provenance tier); the author's own implementation weakness
(priors without evidence, ununified outputs and placeholder hashes, duplicated
state, a species-neutral habitat row, an unused constructor); and model science
(movement, daily-discretisation biology, modelling adequacy).

The decisive observation: the reviewer's most damaging criticisms are all
criticisms of documentation adequacy, not of the model. So the format's value
is not in its sections; it is in the discipline of writing something a hostile
reader can check against the code. The reference document's own Appendix A —
14 numbered implementation notes, each naming a file or function and stating a
fact not visible at protocol level — is the evidence: writing it surfaced
eleven code defects.

---

*Drafted with EGM*
