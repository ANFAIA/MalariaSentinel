# Per-Stage Conceptual Documentation — Concepts Brief

* **Author:** david-fm
* **Date:** 2026-11-16
* **Mode:** brainstorm output (upstream of a formal design document)
* **Raw review:** `concepts_brief.raw.md` — 7 Goldfish lenses, 103 findings, 10 premise corrections

> **Read these three companions before drafting.** This brief is the entry
> point; the details behind it live beside it and are part of the input.
>
> 1. `concepts_brief.decisions.md` — every open decision (I1–I6, R1–R10) with
>    its options, its implications and its residual risk, and the recorded
>    author decision. The summary tables at the end of this brief point here.
> 2. `concepts_brief.odd-method.md` — the investigation of the ODD as a
>    questioning method: the stance (S1–S10) that the new layer shares, the
>    devices that transfer, and the gaps in the ODD format itself, with
>    citations into the reference document.
> 3. `concepts_brief.raw.md` — the 103 raw findings of the 7 review lenses,
>    for anyone who wants to audit what the analysis rests on.
>
> **Intake notes for the drafting step.** This brief is the context file; the
> section "Alternatives Considered" below is the source for the design document's
> own "Alternatives Considered", and "Key Decisions & Staging for Next Steps" is
> the source for its Technical Plan. The decisions table at the end of this file
> points into `concepts_brief.decisions.md` for the options behind each one.
>
> The RFC copy of this brief is published at
> `docs/designs/per-stage-conceptual-documentation.md`, registered in
> `docs/designs/SITEMAP.md`. The formal design document produced by the drafting
> step is written to that same path, replacing the RFC; the RFC remains in the
> git history and in the pull request that published it.

## Overview

The project documents its pipeline with eight hand-written "specs"
(`docs/specs/`, 2,253 lines) that act as contract documents: they pin band names,
value ranges, invariants and versions, and they declare themselves the winner
when code disagrees. The author wants them gone. They are too strict, they are
written around the code instead of around the system, and every refactor forces
noise edits that add no understanding.

The replacement is a conceptual layer, not a contract layer: six formal LaTeX
documents under `docs/concepts/<phase>/` — `download`, `ingest`, `abm`,
`scoring`, `training`, `prediction` — each explaining how that system works
internally: its theory, its processes, its algorithms, its reasoning, and its
inputs and outputs as **one section among others**. The structure of each
document is that stage's own; what they share is a *stance* (how to ask, what
must be decided before writing) rather than a template. The owner of each piece
of content is the stage that uses it, and coherence is checked at the seams:
what one stage produces against what the next one takes as input. The ABM
already has this document: the ODD 2010 description
(`odd-2010-malariasentinel.tex`, 2,011 lines, 21 numbered equations, 32 PDF
pages) that today
exists only in a gitignored directory, and which becomes the base of
`docs/concepts/abm/` — a good representation of the system as it stands, to be
changed progressively as the plans land. PDFs are built in CI and reachable
from the website, and in parallel a pull-request workflow generates technical
reference documentation for the Python and C++ code from source comments and
warns when a change contradicts the conceptual document of the stage it
touches.

The core value is not "better docs". It is a documentation layer that survives
refactors — a document that describes the model can stay true across a rename,
a spec that pins a symbol cannot. And it is a layer that can be read by someone
who has never opened the code.

## Analysis

### What the specs actually were, and why they rotted

The lenses found the specs did not rot because refactors forced noise edits.
They rotted because nothing executed their checks. Every spec opens with a
fenced block reading `# Machine-readable affects block — parsed by the drift-check
agent` and a `Last drift check:` date. No drift-check agent exists; the repo has
no `.github/` directory at all. The invariants have no runner. `tools/run_all_tests.sh`
pairs `set -e` with `pytest || echo "no tests"`, so every failing suite is
swallowed and the script always exits 0.

The drift is in the repo right now, in files the new system is supposed to
depend on (verified 2026-11-16):

| Prose authority | Claim | Reality |
|---|---|---|
| `docs/specs/abm/spec.md:182` | `assert cv.startswith('2.')` | same file INV-12 pins state contract **v4.0** |
| `docs/README.md` | lists `specs/self_improve/`, `diagrams/`, four presentation/status files | none of those paths exist |
| `AGENTS.md` "Calibration framework conventions" | edit `thresholds.yaml`, `scorers/composite.py::DEFAULT_WEIGHTS`, run `tests/calibration` | `thresholds.yaml` exists only in a stale `.gitagent/worktree/`; `composite.py` does not exist; the pytest harness was deleted in 2026-10 |
| `AGENTS.md` monorepo layout | `mal-ghana-sim/` is one of five packages | no such directory; `mal-core/README.md` calls it "former" |
| `docs/specs/data/spec.md` INV-11 | env-NC `contract_version: "2.0"` | `model_constants.yaml`: `env_nc: "3.0"` |
| `docs/specs/commonlib/spec.md` §4.3 | `K_MAX` is public API | `config.py`: "K_MAX retired (2026-10-20)" |
| `mal-core/.../wire.hpp` | cites `docs/abm-status.md` | file does not exist |

Consequence for the plan: a coherence gate built on this baseline reports the
plan's own debt on its first run. A truth pass has to precede the gate, and it
is the cheapest step in the whole plan.

### The four contradictions the lenses shaped the design around

**1. Authority versus maintenance.** A formal PDF with a date and a pinned
commit is trusted *more* than a spec, not less. Nine of the thirteen odd-fixes
packs rewrite what the ABM document must say — pack 10 states the state COG is
"Wrong!! Must be individuals (array) + aquatic cohort", pack 05 says
`update_habitat_day()` applies default species weights instead of the active
species row. Writing the ABM document as-built publishes a document that is
knowingly false in its two most expensive sections. Writing it to the post-pack
target makes it an authority over the code, which the author explicitly
rejected ("coherence, not source of truth").
*Resolution adopted:* per-section status — `\asbuilt{<sha>}` versus
`\target{PACK-05}` — plus a mandatory dated "Pending decisions" section. A
section is either current fact or declared target; the reader is never misled,
and pack churn becomes signal instead of noise.

**2. Verifiability versus abstraction.** The prose the author wants carries
semantics. The values the specs carried — band names, the `-9999.0` sentinel,
`contract_version`, sidecar keys — are exactly the class an LLM reviewer misses
and a `grep` catches. Deleting them and replacing them with prose leaves nothing
mechanical.
*Resolution adopted:* generate the facts, write the semantics. Parameter tables
and contract tables are emitted at build time from `model_constants.yaml` and a
small contracts file into `\input{generated/...}`; a renamed or removed key
becomes an undefined control sequence and **fails the LaTeX build**. No LLM is
in that path and it cannot be faked.

**3. Automation versus judgement.** All seven lenses rejected letting an LLM
block a merge on prose judgement: it is unfalsifiable, it gives an agent merge
authority over the maintainer, fork PRs get no secrets so the check no-ops
exactly where unfamiliar code arrives, and a bot push dismisses stale approvals
under the current ruleset. The project already answered this in the opposite
direction for a near-identical design: `scoring/spec.md` INV-12 requires the LLM
verdict to be non-gating with a `fallback`), and `AGENTS.md` classifies reviewing
subagents as `ask`, not `allow`.
*Resolution adopted (author's revision, 2026-11-16):* **warnings only, no gates
of any kind.** The review system is an advisor that reports incoherences between
the formal conceptual documents and the implementation; it never blocks, never
rejects, and never imposes structure on the documents. Consequently there is no
deterministic checker tier either: no anchor-existence check, no presence rule,
no `Coherence-Waiver:` trailer, no required status. The mechanical signals below
survive as *warning sources* (inputs the reviewer can cite), not as pass/fail
gates. The single build-time guarantee that survives is the one that constrains
nothing about document design: values and tables are **generated** from
`model_constants.yaml` at build time, so a renamed key fails the LaTeX build on
its own, without any checker deciding what a document may say.

**4. Scope versus cost.** The measured cost is prose, not toolchain: `latexmk`
and `pdflatex` are already installed, the ODD preamble is 15 standard packages,
builds take seconds. The cost is 5,400–7,100 LaTeX lines against 2,253 Markdown
lines today, and an estimated 7.5–20 person-days of authoring for five documents
that currently have no named reader. The site publishes a *different* taxonomy
(three stages: ingestion → ABM → U-Net), and the same quantity is stated three
ways (14 scorers on the site, 10 in `AGENTS.md`, 13 dimensions + 6 gates in
`abm/spec.md`).
*Not resolved here: this is the one request the lenses make to reduce scope. See
Alternatives Considered, "Tier the corpus".*

### Ideal final result

State it as a property, not a task: **no number, symbol, key or path in a
conceptual document is typed by hand, and a document that contradicts the
repository cannot compile.** Everything else — the prose describing purpose,
processes, equations and consequences — is written once and survives renames,
because it names no code. Under that rule the maintenance question stops being
"who keeps the docs in sync" and becomes "who writes the prose once".

### Mechanical signals available to the reviewer (advisory inputs, not gates)

Both lenses that built this list independently arrived at the same set. Under
the author's revision these are **sources the reviewer may cite**, not checks
that decide the outcome:

1. Dotted keys cited in a document versus `model_constants.yaml` and their printed values.
2. `\code{...}` identifiers versus Python symbols and `include/mal_abm_fast/*.hpp`.
3. Contract versions in a document versus `model_constants.yaml:contracts.*`.
4. Derived numbers that recompute — grid dimensions and cell area from `aois.yaml`
   (Ghana bbox `[-3.5, 4.5, 1.5, 11.5]`, 1,000 m) plus the geodesy constants. The
   ODD's 551 × 779 cell count is one such number, and the site's "9.466 celdas" is
   another that does not match it.
5. `latexmk -Werror`: undefined references or citations, unresolved `\eqref`.
6. `docs/...`, `papers/...`, `scripts/...` paths named in a document or comment versus the tree. This one alone would have caught the whole stale-claims table above.
7. Documented output files for a stage versus the consumer globs that read them.
8. Changed path → candidate document, for single-stage paths.
9. Freshness: a document declaring `% sources:` globs whose hashes no longer match.

What stays human: process ordering, formula-versus-code equivalence,
implemented-versus-unimplemented statements, blast radius of a shared config key,
and provenance.

Two consequences of dropping the gate tier, stated plainly. First, the only
*guaranteed* protection left is generated values (a key rename breaks the LaTeX
build); every other class of drift becomes a warning a human may or may not
read, so the review must be surfaced where a human actually looks — the PR
comment and, if the reviewer wants persistence, a dated ledger file. Second, the
absence of a presence rule means a stage change can be merged with no document
touch at all and no signal; the only mitigation left is the reviewer's own
coverage of the diff.

### The orphan problem, and where the lenses disagreed

Of ~62 non-test modules in `mal-core/src`, ~44 belong to one stage and ~12 are
cross-cutting. Four obligations have no stage to live in, and today they live in
the specs that are being deleted:

| Obligation | Owner today | Why it cannot be split |
|---|---|---|
| AOI data product — naming, manifest schema, catalog, completeness | `docs/specs/data/spec.md` | read and written by all six stages |
| Spatial frame — AOI, `Scale`, `cells_per_side`, 1 km grid, CRS | `docs/specs/commonlib/spec.md` §4.1 | pins `(H,W)` for every raster in every stage |
| Habitat theory — `S`, `K`, Beverton-Holt, salinity, aquatic stress | `mal_core/habitat/` (Python) mirrored in `habitat_availability.hpp` | computed by ingest, executed by abm, read for parity by scoring |
| Parameter provenance — units, literature anchors, prior status | `model_constants.yaml` + changelog | every document that prints a value becomes another copy |

**Resolved by the author (2026-11-16): no common substrate.** The owner of
each piece of content is the stage that *uses* it; the manifest schema into
`download`, the spatial frame into the stage that first needs `(H, W)`, the
habitat theory into `ingest` (which computes H) and `abm` (which applies S and
K), parameter provenance into the stage whose process each constant drives.
The coherence mechanism is **adjacency**: the ABM document describes what the
ABM produces and the next stage's document describes what it takes as input,
so a discrepancy is visible where the two meet — with no central artefact and
no ownership matrix. Repetition between stages is accepted, not hunted: the
same fact written from two stages' points of view is where the drift shows up.
See Key Decisions D5.

Two further structural objections, which the plan absorbs silently:

- **`scoring` is not a chain stage.** It consumes the ABM output and produces a
  scorecard for a human or CI; nothing downstream reads it. It is an evaluation
  harness beside the chain.
- **The reference framework is a cycle; the pipeline is a DAG.** Kelly et al.
  (2012) states its key elements verbatim as "(iii) application/intervention
  outcomes re-entered back into the SDSS as a cyclical input; and importantly
  (iv), expert knowledge, integrated throughout all stages of the SDSS process"
  (`papers/spatial-analysis/MalariaEliminationWithSpatialDecisionSupportSystems.md:304-307`).
  Whether the current pipeline closes that loop is a question about the system,
  not about the documentation. The author has ruled that no ABM modification and
  no generalisation to other systems is on the table, so this is recorded, not
  actioned.

### The technical-docs half rests on a premise that does not hold

There is no pybind11 in the project (verified: only inside `.venv` third-party
packages). `wrapper.py` shells out to the compiled binary and parses `--help`.
The real Python↔C++ interface is four things: CLI flags, `model_constants.yaml`
keys, input file formats (NetCDF, GeoPackage, CSR) and output contracts (COG +
sidecar). A Doxygen↔Breathe bridge would document ~40 internal headers that no
Python caller touches, and would miss the interface that actually breaks. The
generated reference must document the flag and file contract, not the C++ class
hierarchy.

Comment quality is the other blocker: there are zero Doxygen directives in the
C++ tree, trailing `//` comments are invisible to Doxygen, several headers still
state the retired two-band / `k_max` contract, and the Python docstrings would
publish at least four statements the code contradicts. Generated docs from
current comments would be structurally complete and semantically false.

"Same visual style as the site" is not achievable for generated pages: Doxygen
and Sphinx each ship their own `index.html`, CSS and collision-prone `_`-
directories. The workable target is one site entry ("Technical reference") that
links into a visually separate generated surface, with a generated docs index —
never a hand-maintained one.

## Goals vs. Non-Goals

**In scope**

- Six conceptual documents under `docs/concepts/<phase>/`, LaTeX source, English,
  each describing the internal operation of its stage in its own structure and
  carrying inputs and outputs as one section.
- A shared **stance** rather than a shared template: purpose separate from
  mechanism; magnitudes named with identity, units and resolution; data
  distinguished from choice; every constant carrying a provenance tier; state
  distinguished from derived from cache; absences declared; ordering written
  where order matters, with consequences; outputs given with their consumption
  contract; an evidence appendix. Stated in full in
  `concepts_brief.odd-method.md`.
- Ownership by use: each stage documents what it uses, in its own style;
  coherence checked at the seams by adjacency, between a stage's outputs and
  the next stage's inputs.
- Generated value layer: parameter and contract tables emitted from
  `model_constants.yaml` and a contracts file at build time.
- A **warnings-only** coherence review on pull requests: the reviewer reports
  incoherences between the conceptual documents and the implementation and
  nothing else. It does not block, reject, or constrain the design of the
  documents.
- Generated technical reference for Python and C++ from polished source comments,
  published under `docs/` and linked from the site.
- PDFs built in CI and reachable from `malariasentinel.com`, through a separate
  documentation page linked from the site's navigation.
- Generated reference output namespaced under `docs/reference/cpp/` and
  `docs/reference/python/`.
- Two shared artefacts, and only two: a "how to write a conceptual document"
  note in `docs/concepts/` (the stance, the devices, the reasoning, the ODD as
  worked example) and a lightweight skill carrying the drafting operation, so
  that changing the question set itself is a supported action.
- Per-stage question sets and checklists, each derived from that stage's own
  material by a subagent that reads before asking.
- The authoring loop: an agent drafts the document, a human annotates it, the
  annotations become plans under `docs/plans/`, and applying a plan updates
  the part of the document it invalidates.
- `data/` untracked from GitHub while surviving locally, with a working restore
  path.
- `docs/specs/` retired stage by stage as each conceptual equivalent lands.

**Out of scope / non-goals**

- Enforced contracts. No document is a source of truth; values come from
  configuration, semantics from prose, and precedence is written down once.
  These documents are a conceptual and theoretical source of truth about the
  system's processes and algorithms, not a technical source of truth about its
  parts.
- Automated gating of any kind. No blocking check, no required status, no
  presence rule, no waiver mechanism. The only automated failure is a LaTeX
  build that cannot find a generated value — a property of the build, not a
  judgement about the document.
- Code or test detail inside conceptual documents. Pseudocode yes; call graphs and
  test names no. A code symbol may be named, but only if it is explained in
  prose at its first use.
- Code snippets as worked examples. Each document's example is a described
  situation — a reader asks for something; what happens, in order.
- One ODD per stage. Only `abm` gets the ODD; other typologies get their own
  question sets.
- Retiring `papers/` in this phase. It stays until a docling-based path proves
  equivalence, and a generated bibliography must land before it parks.
- Migrating GitHub Pages away from the legacy `main:/docs` build.
- `data/` history rewrite. Not until a blob-size scan proves it is needed.
- Deciding the fate of experiment packages (`mal-data-explorer`,
  `social-networks/`): author's call, tracked as D9.

## Alternatives Considered

- **Keep the specs and fix them.** Rejected by author: too strict and tied to
  code; a refactor that preserves behaviour still forces edits, which is how they
  became useless. Lenses add the mechanical reason: their checks were never
  executed, so keeping them keeps a document class with 100% pass rate and 0%
  enforcement.
- **Contract as a generated artefact (machine-readable interface files).**
  Rejected by author: it recreates the spec system under another name. Kept only
  as a build-time generator feeding the LaTeX (see D2), not as a human document.
- **Unit = package or module instead of pipeline stage.** Rejected by author:
  packages do not describe the system; stages do.
- **An ODD for every stage.** Rejected by author: the ODD answers a
  model-description question; `download`/`ingest` need a different one (where
  data comes from, in what format, how it is transformed, what it becomes).
- **Six per-typology templates authored up front by one subagent per phase.**
  Rejected by author, 2026-11-16, on the stated ground that a shared template
  produces a document that explains the theory generically instead of
  explaining it. The lenses' independent objection pointed the same way: a
  template authored and answered by the same agent, reviewed by nobody, is a
  formatting convention with a 100% pass rate — the spec system rebuilt with
  more pages. Adopted instead: per-stage question sets found per stage, in the
  ODD's own discipline of reading the material before asking, with the shared
  *stance* (S1-S10, in `concepts_brief.odd-method.md`) as the common instrument
  and the section list free.
- **A seventh `shared/` substrate document, an ownership matrix, or `\input`
  fragments.** Rejected by author, 2026-11-16: the owner of each piece of
  content is the stage that uses it, and the coherence check happens at the
  seams by adjacency — a stage's outputs against the next stage's inputs. No
  common artefact, no standard imposed between stages, repetition accepted.
- **Tier the corpus** (formal LaTeX for `abm` only; Markdown for the rest; defer
  the three stages with no named reader). Proposed by two lenses on the measured
  cost (7.5–20 person-days for five documents without readers). Not adopted —
  the author chose LaTeX for all six; recorded here because every lens that did
  the cost arithmetic raised it, and because a later reversal should be a
  decision, not a discovery.
- **Committed PDFs in `docs/`.** Not adopted as-is; incompatible with "compiled
  in CI" unless CI commits them back to the branch. Remains open as I1.
- **Pages migration to a build workflow.** Rejected for this phase: it puts the
  CNAME, `index.html` and favicons at risk for a benefit the concept does not
  require. PDFs and generated docs must fit under the legacy build, be published
  as release assets, or be pushed to the branch by the workflow.
- **LLM gate as a required check.** Rejected by all seven lenses.
- **Deterministic checker tier (anchor existence, presence rule, waiver
  trailer).** Rejected by author, 2026-11-16: gating constrains the design of
  the documents and forces them to become checkable shapes. The mechanical
  signals survive as inputs the reviewer may cite; the only automatic guarantee
  left is the build-time generation of values.
- **`git filter-repo` to purge `data/` from history.** Deferred behind a
  blob-size scan: if `data/ghana/` was always ignored, there is nothing to purge
  and the rewrite would only break every SHA referenced in `docs/plans/` and in
  the ODD.

## Critical User Journeys

The users of this design are the people who read, write and check these
documents, and the newcomer the documents exist for.

### CUJ 1 — A newcomer understands the pipeline without reading code

* **Given**: someone arrives at `malariasentinel.com` and follows the
  documentation link.
* **When**: they open the conceptual document of one stage.
* **Then**: they can say what that stage consumes, what it produces and why it
  behaves as it does, without opening a source file — every code symbol the
  document names is explained where it is first used.

### CUJ 2 — An agent drafts a stage document

* **Given**: a stage with an agreed question set, and the stance note that
  governs how the questions are asked.
* **When**: the drafting skill runs for that stage.
* **Then**: a LaTeX document exists that answers every question in the set, in
  the stage's own structure, with its values generated from
  `model_constants.yaml` and its code claims cited; and it compiles.

### CUJ 3 — A reviewer finds a divergence

* **Given**: a pull request that changes the behaviour of a stage covered by a
  conceptual document.
* **When**: the pull request is opened.
* **Then**: a comment names the specific passage of the document that no longer
  matches the code, quoting both; the pull request is not blocked.

### CUJ 4 — A defect found while reading a document becomes a plan

* **Given**: a reviewer annotating a draft document with a defect.
* **When**: the annotations are distilled into a plan.
* **Then**: a plan file exists that names the document section it invalidates
  and the code change required — the same mechanism that produced the 13
  `odd-fixes` packs.

### CUJ 5 — A plan lands and the document follows

* **Given**: a plan applied to the code.
* **When**: that plan's pull request is merged.
* **Then**: the part of the document the plan named is updated in the same pull
  request, so the document never describes a state the code has already left.

### CUJ 6 — A maintainer retires a spec

* **Given**: a stage whose conceptual document covers what its spec covered.
* **When**: the spec is deleted.
* **Then**: no information is lost — the conceptual document carries the
  semantics and the generated tables carry the values, and the manifest and
  contract versions are checked at build time.

## Open Questions

Carried into the design document as open, not as decided:

* **PDF determinism under I1-A.** CI compiles the PDF and commits it back to the
  branch. Byte-identical output needs a fixed `SOURCE_DATE_EPOCH` and a
  reproducible TeX toolchain; until that is measured, the equality check has to
  run on extracted text (`pdftotext -layout`), not on bytes. The size of the
  binary churn in history is unmeasured.
* **The flag-and-file contract generator (I2-B).** Whether it is built before
  or after the Doxygen and pdoc surfaces exist is not decided, and neither is
  whether it earns its maintenance cost.
* **Where the coherence reviewer runs, and at what cost.** The warnings-only
  regime needs a model, a token budget per pull request and a place to run; none
  of the three is set, so the regime has no defined cost ceiling.
* **The exact content of the Stage 0 truth pass.** The seven stale claims are
  enumerated; the current text of the contract-defining headers is not fully
  audited, so the size of that pull request is unknown.
* **The documentation page under `docs/`.** How it is structured, and whether
  its index is generated or hand-written, is undecided — and it needs its own
  ES/EN dictionaries, which is a translation maintenance question, not a
  documentation one.
* **Whether `data/` untracking lands before or after the first document
  exists.** The pre-work in D8 (environment override, loud failure, restore
  script, offline copies) is specified in outline; its sequencing against the
  first document is not.
* **The first document's author.** The loop in R2 has an agent drafting and a
  human annotating; whether the first document is written by the author, by an
  agent, or by an agent under review is not stated, and it changes what the
  first review round looks like.

## Key Decisions & Staging for Next Steps

### Decisions taken in this brainstorm

- **D1 — Generate facts, write semantics.** Any number, key, symbol or path in a
  conceptual document is emitted at build time; prose carries only what survives
  a refactor. A value that no longer exists fails the LaTeX build on its own —
  a property of the build, not a check that judges the document.
- **D2 — Precedence rule, stated once.** Values → `model_constants.yaml` wins.
  Contract values and names → the generated contract table wins. Semantics → the
  concept document wins. On contradiction, the lower authority is the bug.
  Stated in the document that owns the content, per D5; there is no shared page.
- **D3 — Warnings only. No gates.** The pull-request reviewer compares the diff
  against the conceptual documents of the affected stages and reports
  incoherences as warnings. It does not block, does not reject, does not require
  a document to change, and does not constrain the shape of the documents. There
  is no deterministic checker tier either. The mechanical signals (keys,
  identifiers, contract versions, recomputable numbers, named paths, output
  globs, `% sources:` freshness) exist as inputs the reviewer can cite, not as
  pass/fail tests.
- **D4 — The document changes as the plans land.** Dropped in favour of a
  simpler rule (2026-11-16): the clean ODD is the base for `docs/concepts/abm/`,
  and each application of a plan changes the part of the document it
  invalidates. No status macros, no per-section `\asbuilt{}` / `\target{}`
  metadata. Cost accepted: with no status markers and a warnings-only review,
  a document's staleness relative to an *in-flight* plan is invisible to the
  reviewer; that signal lives in the plan tracker, not in the document.
- **D5 — Ownership by use; no common substrate.** The stage that uses a piece
  of content documents it, in that stage's own style. The manifest schema
  belongs to `download`; the spatial frame to the stage that first needs
  `(H, W)`; the habitat theory to `ingest` (computing H) and `abm` (applying S
  and K); parameter provenance to the stage whose process each constant drives.
  Coherence is checked at the seams by adjacency — the ABM document's outputs
  against the next stage's inputs — not through a shared artefact. Repetition
  between stages is accepted: it is where drift becomes visible. These
  documents are a conceptual and theoretical source of truth about the system,
  not a technical source of truth about its parts.
- **D6 — Truth pass before any checker.** One PR fixing the seven stale claims
  above, plus the contract-defining source headers. Baseline that lies produces a
  gate that reports its own debt.
- **D7 — ODD first out of `.cache/`.** Copy the clean `.tex` into
  `docs/concepts/abm/` and `git add` it, then prove `latexmk -pdf` builds it
  unmodified. Two mechanical details, both verified: `.cache/` is gitignored
  (`.gitignore:53`), so the source file is untracked and `git mv` will refuse it
  — it is a copy plus `git add`; and `docs/` is *not* ignored, so a `.tex` there
  is trackable without `-f`. The build was checked on 2026-11-16: `latexmk -pdf`
  on the unmodified file succeeds and produces a 32-page PDF. Until a `.tex` is
  tracked, "PDFs built in CI" has no input and reviewers cannot review. The
  annotated review copy stays out of the published tree: it is personal and team
  material whose content already lives in the plans it produced.
- **D8 — `data/` is last, and its removal is a safety problem before it is a git
  problem.** Verified: `data/ghana/manifest.json` is **untracked and ignored**
  (`.gitignore:20`). Untracking `data/` today deletes the inventory that is
  declared the single source of truth. Pre-work, in order: move manifests to a
  tracked path; add `MAL_DATA_ROOT` to `manifest.py` **and** `config.py`; make a
  missing AOI directory raise loudly instead of returning an empty skeleton;
  write and round-trip-prove `scripts/restore_data.py` (does not exist, though
  `.gitignore` claims it does); commit two offline copies with a `sha256sum`
  manifest; then `git rm -r --cached data` in its own PR.
- **D9 — Experiment packages and the top-level document remain the author's
  decision.** The cycle/DAG gap is recorded here so it is not lost.

### Staging

| Stage | Work | Exit condition |
|---|---|---|
| 0 | Truth pass: `docs/README.md`, `AGENTS.md` calibration + layout sections, the seven stale claims, contract-defining headers | no claim in those files contradicted by the tree |
| 1 | Copy the clean ODD into `docs/concepts/abm/` (it is gitignored at the source, so `git mv` will not work) and `git add` it; build unmodified. The annotated review copy stays out of the published tree | a tracked `.tex` compiles to PDF — verified 2026-11-16 on the unmodified file, 32 pages |
| 2 | The two shared artefacts: a "how to write a conceptual document" note in `docs/concepts/` (the stance, the devices, the reasoning, the ODD as worked example) and a lightweight skill for the operation of drafting or changing the question set | both exist and are usable by a writer who has never seen the ODD review |
| 3 | Per-stage question sets and checklists: one subagent per stage investigates the material and returns that stage's questions with citations (the ODD discipline) | a question set and a checklist per stage, each traceable to code/notes citations |
| 4 | Generator for values (parameter/contract tables from `model_constants.yaml`); contracts file; first workflow | a build reproduces the generated tables byte-for-byte (`git diff --exit-code`) |
| 5 | Pilot `download`: agent drafts the document from its question set; human annotates; annotations become a plan under `docs/plans/`; the plan's application updates the document | one non-ABM document written, read by someone without a code profile, and revised once through the full loop |
| 6 | One PDF published and linked once from the site; one "Technical reference" entry | a reader reaches both in ES and EN |
| 7 | Generated technical reference: comment polish pass first, then C++ and Python generation, visually separate surface | published, linked, and the flag/file contract documented |
| 8 | Warnings-only coherence review on PRs; measure its false-positive rate over 20 PRs of history | a first-pass rate is known before anyone relies on it |
| 9 | `data/` untracking with all of D8's pre-work | clean-room clone → `uv sync` → download → ingest → `abm --days 1` passes |

### Open decisions carried into the design document

| # | Decision | Options on the table |
|---|---|---|
| I1 | PDF topology under legacy Pages | **A: CI commits the PDF to the branch** (decided 2026-11-16) / B: publish as release assets / C: migrate Pages to a build workflow |
| I2 | Technical-docs toolchain | **A: Doxygen + pdoc, after a polish pass on the contract-defining headers only** (decided 2026-11-16); B: custom generator for the flag/file contract as a later complement / C: defer |
| I3 | Document skeleton | **Decided 2026-11-16: option C** — free-form per typology, no shared section list; what is shared is the *stance* (S1–S10 in `concepts_brief.odd-method.md`), not a table of contents |
| R1–R10 | The round-2 question set (stance in writing + skill; agent-drafts/human-reviews loop; anchors explained inline; ODD as evolving base; per-stage checklist; separate documentation page; namespaced reference dirs; `scoring` documented in full; six documents with `ingest` sub-stages as sections; examples as described situations) | **All decided 2026-11-16** — see `concepts_brief.decisions.md` |
| I4 | Ownership of shared content | **Decided 2026-11-16: ownership by use** — the stage that uses it documents it; coherence checked at the seams by adjacency; no substrate, no matrix, no seventh document |
| I5 | Six-way template set | **Decided 2026-11-16: no generic template** — each stage gets its own questions; per-stage question sets derived by a subagent that reads the material, in the ODD's own discipline |
| I6 | Owner of the cycle/DAG gap | **Dropped 2026-11-16** — a question about the system, not the documentation; no ABM modification and no generalisation is on the table |
