# Per-Stage Conceptual Documentation

*   **Author:** david-fm
*   **Status:** Plan (executed)
*   **Date:** 2026-11-16
*   **Origin:** the EGM brainstorm's RFC brief
    (`docs/designs/per-stage-conceptual-documentation.md`), deleted when this
    plan was written — its content is absorbed here; the original survives in
    the git history at commit `75dc50c`.

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

## Analysis

The analysis below comes from the EGM brainstorm that produced this plan (7
review lenses, 103 findings). It is the reasoning the plan is built on; the
RFC brief it came from was deleted when this plan was written (git history:
`75dc50c`).

### The four contradictions the lenses shaped the design around

**1. Authority versus maintenance.** A formal PDF with a date and a pinned
commit is trusted *more* than a spec, not less. Nine of the thirteen odd-fixes
packs rewrite what the ABM document must say — pack 10 states the state COG is
"Wrong!! Must be individuals (array) + aquatic cohort", pack 05 says
`update_habitat_day()` applies default species weights instead of the active
species row. Writing the ABM document as-built publishes a document that is
knowingly false in its two most expensive sections; writing it to the post-pack
target makes it an authority over the code, which the author explicitly
rejected ("coherence, not source of truth").
*Resolution adopted, then superseded:* per-section status — `\asbuilt{<sha>}`
versus `\target{PACK-05}` — plus a mandatory dated "Pending decisions"
section. **D4 replaced this** (2026-11-16): no status macros, no per-section
metadata; the clean ODD is the base and each applied plan changes the part of
the document it invalidates. The cost is recorded in D4.

**2. Verifiability versus abstraction.** The prose the author wants carries
semantics. The values the specs carried — band names, the `-9999.0` sentinel,
`contract_version`, sidecar keys — are exactly the class an LLM reviewer
misses and a `grep` catches. Deleting them and replacing them with prose leaves
nothing mechanical.
*Resolution adopted:* generate the facts, write the semantics (D1). Parameter
tables and contract tables are emitted at build time from `model_constants.yaml`
and a small contracts file into `\input{generated/...}`; a renamed or removed
key becomes an undefined control sequence and **fails the LaTeX build**. No LLM
is in that path and it cannot be faked.

**3. Automation versus judgement.** All seven lenses rejected letting an LLM
block a merge on prose judgement: it is unfalsifiable, it gives an agent merge
authority over the maintainer, fork PRs get no secrets so the check no-ops
exactly where unfamiliar code arrives, and a bot push dismisses stale approvals
under the current ruleset. The project already answered this in the opposite
direction for a near-identical design: `scoring/spec.md` INV-12 requires the LLM
verdict to be non-gating, and `AGENTS.md` classifies reviewing subagents as
`ask`, not `allow`.
*Resolution adopted (author's revision, 2026-11-16):* **warnings only, no gates
of any kind** (D3). The review system is an advisor that reports incoherences
between the formal conceptual documents and the implementation; it never blocks,
never rejects, and never imposes structure on the documents. Consequently there
is no deterministic checker tier either: no anchor-existence check, no presence
rule, no `Coherence-Waiver:` trailer, no required status. The mechanical signals
below survive as *warning sources* (inputs the reviewer may cite), not as
pass/fail gates. The single build-time guarantee that survives is the one that
constrains nothing about document design: values and tables are **generated**
from `model_constants.yaml` at build time, so a renamed key fails the LaTeX
build on its own, without any checker deciding what a document may say.

**4. Scope versus cost.** The measured cost is prose, not toolchain: `latexmk`
and `pdflatex` are already installed, the ODD preamble is 15 standard packages,
builds take seconds. The cost is 5,400–7,100 LaTeX lines against 2,253 Markdown
lines today, and an estimated 7.5–20 person-days of authoring for five documents
that currently have no named reader. The site publishes a *different* taxonomy
(three stages: ingestion → ABM → U-Net), and the same quantity is stated three
ways (14 scorers on the site, 10 in `AGENTS.md`, 13 dimensions + 6 gates in
`abm/spec.md`).
*Not resolved here: this is the one request the lenses make to reduce scope.
See Alternatives Considered, "Tier the corpus" (Alternative G).*

### The ideal final result

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

1. Dotted keys cited in a document versus `model_constants.yaml` and their
   printed values.
2. `\code{...}` identifiers versus Python symbols and
   `include/mal_abm_fast/*.hpp`.
3. Contract versions in a document versus `model_constants.yaml:contracts.*`.
4. Derived numbers that recompute — grid dimensions and cell area from
   `aois.yaml` (Ghana bbox `[-3.5, 4.5, 1.5, 11.5]`, 1,000 m) plus the geodesy
   constants. The ODD's 551 × 779 cell count is one such number, and the site's
   "9.466 celdas" is another that does not match it.
5. `latexmk -Werror`: undefined references or citations, unresolved `\eqref`.
6. `docs/...`, `papers/...`, `scripts/...` paths named in a document or comment
   versus the tree. This one alone would have caught the whole stale-claims
   table above.
7. Documented output files for a stage versus the consumer globs that read
   them.
8. Changed path → candidate document, for single-stage paths.
9. Freshness: a document declaring `% sources:` globs whose hashes no longer
   match.

What stays human: process ordering, formula-versus-code equivalence,
implemented-versus-unimplemented statements, blast radius of a shared config
key, and provenance.

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

**Resolved by the author (2026-11-16): no common substrate** (D5). The owner of
each piece of content is the stage that *uses* it; the manifest schema into
`download`, the spatial frame into the stage that first needs `(H, W)`, the
habitat theory into `ingest` (which computes H) and `abm` (which applies S and
K), parameter provenance into the stage whose process each constant drives. The
coherence mechanism is **adjacency**: the ABM document describes what the ABM
produces and the next stage's document describes what it takes as input, so a
discrepancy is visible where the two meet — with no central artefact and no
ownership matrix. Repetition between stages is accepted, not hunted: the same
fact written from two stages' points of view is where the drift shows up.

Two further structural objections, which the plan absorbs silently:

- **`scoring` is not a chain stage.** It consumes the ABM output and produces a
  scorecard for a human or CI; nothing downstream reads it. It is an evaluation
  harness beside the chain.
- **The reference framework is a cycle; the pipeline is a DAG.** Kelly et al.
  (2012) states its key elements verbatim as "(iii) application/intervention
  outcomes re-entered back into the SDSS as a cyclical input; and importantly
  (iv), expert knowledge, integrated throughout all stages of the SDSS process"
  (Kelly et al. 2012, `doi:10.1016/j.pt.2012.04.002`; the section locator was lost when the summary's Full Text was removed).
  Whether the current pipeline closes that loop is a question about the system,
  not about the documentation. The author has ruled that no ABM modification and
  no generalisation to other systems is on the table, so this is recorded, not
  actioned (D9).

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

## Goals

*   Retire `docs/specs/` stage by stage as each conceptual equivalent lands,
    with no information loss: semantics move to the conceptual document, values
    move to the generated tables.
*   Publish six conceptual documents under `docs/concepts/<phase>/` (`download`,
    `ingest`, `abm`, `scoring`, `training`, `prediction`), LaTeX source,
    English, each in its own structure, sharing a stance rather than a template.
*   Make hand-typed values impossible: parameter and contract tables generated
    from `model_constants.yaml` and a contracts file at build time, so a
    renamed key fails the build on its own — at schema validation for a key
    the configuration validator covers, and at the LaTeX build for a key the
    schema tolerates.
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
    to the repository's parent directory first, then `git rm -r --cached --
    data`; the next `malariasim download` rebuilds the upstream half of the
    manifest from the registry, and the next `malariasim ingest` re-registers
    the derived products (D8).

## Non-Goals

*   **No enforced contracts.** No document is a source of truth. Values come
    from configuration, semantics from prose, and the precedence rule is stated
    once. These documents are a conceptual and theoretical source of truth
    about the system's processes and algorithms, not a technical source of
    truth about its parts.
*   **No automated gating of any kind.** No blocking check, no required status,
    no presence rule, no waiver mechanism. The only automated failures are a
    configuration validation error — a renamed or removed key in
    `model_constants.yaml` is rejected before the build starts — and a LaTeX
    build that cannot find a generated value. Both are properties of the
    build, not judgements about the document.
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
* **When**: that plan's commit is pushed.
* **Then**: the part of the document the plan named is updated in the same
  commit, so the document never describes a state the code has already left.

### CUJ 6 — A maintainer retires a spec

* **Given**: a stage whose conceptual document covers what its spec covered.
* **When**: the spec is deleted.
* **Then**: no information is lost — the conceptual document carries the
  semantics and the generated tables carry the values, and the manifest and
  contract versions are checked at build time.

## Open Questions

Carried as open, not as decided:

* **PDF determinism under I1-A.** CI compiles the PDF and commits it back to the
  branch. Byte-identical output needs a fixed `SOURCE_DATE_EPOCH` and a
  reproducible TeX toolchain; until that is measured, the equality check has to
  run on extracted text (`pdftotext -layout`), not on bytes. The size of the
  binary churn in history is unmeasured.
* **The flag-and-file contract generator (I2-B).** Whether it is built before
  or after the Doxygen and pdoc surfaces exist is not decided, and neither is
  whether it earns its maintenance cost.
* **When the author relies on the coherence reviewer.** The regime's mechanics
  are decided in this plan (Stage 12): the workflow reads the model id from a
  repository variable and the key from the `OPENROUTER_KEY` repository secret
  — the path the project's LLM scorer already uses — and the token budget is
  the workflow's own default. What remains open is not the mechanics but the
  decision to rely on the reviewer, which Stage 12 turns into a recorded
  measurement rather than a threshold.
* **The exact content of the Stage 0 truth pass.** The stale claims are
  enumerated; the current text of the contract-defining headers is not fully
  audited, so the size of that change is unknown.
* **The documentation page under `docs/`.** How it is structured, and whether
  its index is generated or hand-written, is undecided — and it needs its own
  ES/EN dictionaries, which is a translation maintenance question, not a
  documentation one.
* **The first document's author.** The loop has an agent drafting and a human
  annotating; whether the first document is written by the author, by an agent,
  or by an agent under review is not stated, and it changes what the first
  review round looks like.

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
   questions it was written to answer. Each of the six has its own stage in the
   sequencing below: Stage 1 for `abm`, Stage 5 for the `download` pilot, and
   Stages 6–9 for `ingest`, `scoring`, `training` and `prediction`.
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
   and per-key macros. The documents never type a number. Two failures follow
   from that, both properties of the build rather than judgements about the
   document: a key renamed or removed in `model_constants.yaml` is rejected by
   the configuration validator
   (`mal_core.config_validation.validate_model_config` — `extra="forbid"` at
   every level, every key required) before the generator emits anything; and
   a key the schema tolerates becomes an undefined control sequence only if a
   document actually references it. The LaTeX-level guarantee is therefore
   reachable for the keys a document uses, and is demonstrated at the first
   stage where a document uses one.
5. **CI: PDF build and publication** — a workflow compiles each document with
   `latexmk -pdf` and commits the PDF back to the same branch (decision I1-A:
   the PDF is compiled in CI and committed back to the branch), at the stable
   path `docs/concepts/<phase>/<phase>.pdf` — the `latexmk` output is renamed
   (`odd-2010-malariasentinel.pdf` becomes `abm.pdf`) — which the legacy
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
   document; `% sources:` freshness. Two of these signals already have
   implementations in the repository — `tools/audit_comment_constants.py`
   (model-constant values echoed inside comments and docstrings) and
   `tools/check_no_constants.sh` (no model-constant literals in migrated
   code) — and the reviewer cites them rather than re-implementing them.
   What stays human: process ordering,
   formula-vs-code equivalence, implemented-vs-unimplemented statements,
   blast radius, provenance.
7. **CI: generated technical reference** — after a comment-polish pass scoped
   to the contract-defining headers (`wire.hpp`, `output_contract.hpp`,
   `habitat_availability.hpp`, `habitat_engine.hpp`, `coordinator.hpp`,
   `config.hpp`), Doxygen generates the C++ reference and pdoc the Python one
   (decision I2-A: Doxygen plus pdoc generation, scoped to the polished
   headers), into the namespaced directories `docs/reference/cpp/` and
   `docs/reference/python/` so neither tool's `index.html` collides with the
   other's. One site entry, "Technical reference", links into both surfaces.
   The flag-and-file contract (CLI flags, YAML keys, input formats, output
   contracts — the interface that actually breaks) is a candidate for a small
   purpose-built generator later (I2-B: the flag-and-file contract generator,
   not decided — see Open Questions).

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
| 6 | **`ingest` document**: the loop of Stage 5 again — an agent drafts from the stage's question set, a human annotates, the annotations become a plan, the plan's application updates the document | the `ingest` document written, read by someone without a code profile, revised once through the full loop |
| 7 | **`scoring` document**: the loop of Stage 5 again | the `scoring` document written, read by someone without a code profile, revised once through the full loop |
| 8 | **`training` document**: the loop of Stage 5 again | the `training` document written, read by someone without a code profile, revised once through the full loop |
| 9 | **`prediction` document**: the loop of Stage 5 again | the `prediction` document written, read by someone without a code profile, revised once through the full loop |
| 10 | **Publication**: one PDF published and linked once from the site | a reader reaches the PDF from the site in ES and EN (the Technical reference is verified at Stage 11) |
| 11 | **Generated technical reference**: comment polish on the contract-defining headers, then Doxygen + pdoc generation into the namespaced directories | published and linked; the flag/file contract documented *if I2-B is built* — if it is not, the stage records I2-B as deferred in the plan tracker and the exit condition holds |
| 12 | **Warnings-only coherence review** on PRs; measure its first-pass false-positive rate over the last 20 merges on `main` (or all of them if fewer exist) | the measured rate is written down — findings versus confirmed false positives — before anyone relies on the reviewer; no threshold is set, by design (D3) |
| 13 | **`data/` untracking (option B)**: zip `data/` to the repository's parent directory and verify it (`unzip -t`); `git rm -r --cached -- data` then `git add -- data/README.md` (never `rm`), with a `data/*` ignore rule plus a `!data/README.md` negation; update `data/README.md` for the new restore path | backup restores the tree; `git ls-files data/` shows only `data/README.md`; clean-room clone (with credentials) → `uv sync --all-packages` → `uv run malariasim download` (upstream half of the manifest rebuilt) → `uv run malariasim ingest` (derived half) → `abm --days 1` passes |

### Decisions that shape the architecture

The labels used by the brainstorm's RFC brief — the `R1`–`R10` round-2
requirements and the `I*`/`F*` open decisions — are historical and are not
carried into this plan: every requirement they marked is stated here in full.
The exception is the three that name decisions this plan still makes — I1-A
(the PDF is compiled in CI and committed back to the branch), I2-A (Doxygen
plus pdoc generation) and I2-B (the flag-and-file contract generator, not
decided) — which are expanded in place wherever they appear.

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
- **D4 — The document changes as the plans land.** The
  clean ODD is the base for `docs/concepts/abm/`, and each application of a
  plan changes the part of the document it invalidates. No status macros, no
  per-section `\asbuilt{}`/`\target{}` metadata. Accepted cost: staleness
  relative to an in-flight plan is invisible to the reviewer; that signal
  lives in the plan tracker (`docs/plans/in-process/`), not in the document.
- **D5 — Ownership by use; no common substrate.** The stage that uses a piece
  of content documents it. Coherence is checked at the seams by adjacency.
  Repetition between stages is accepted: it is where drift becomes visible.
- **D6 — Truth pass before any checker** (Stage 0). A baseline that lies
  produces a gate that reports its own debt. Scope excludes `docs/specs/*`
  (author decision, 2026-11-16): they are marked untrusted instead of
  repaired, because they are scheduled for deletion.
- **D7 — ODD first out of `.cache/`** (Stage 1), as a copy plus `git add`.
- **D8 — `data/` is last** (Stage 13), and its removal is a safety problem
  before it is a git problem. Its pre-work is superseded by the author's
  option B (2026-11-16): one zip in the repository's parent directory, then
  `git rm -r --cached -- data` — so no relocation, no `MAL_DATA_ROOT`, no
  restore script. The manifest rebuilds itself, in two halves: `download`
  re-registers the upstream products from the downloader registry (datasets
  whose credentials are absent are skipped, not failed, and leave the manifest
  partial), and `ingest` re-registers the derived ones (`env_nc`, the habitat
  gpkg, `host_static`, `mobility_*`) through
  `mal-core/src/mal_core/ingest/_shared.py::register_dataset`.
- **D9 — Experiment packages and any top-level system document remain the
  author's decision.** The cycle/DAG gap against Kelly et al. (2012) is
  recorded, not actioned.
- **D10 — One stage per remaining document** (author decision, 2026-11-16).
  This plan produces all six conceptual documents: `abm` (Stage 1) and the
  `download` pilot (Stage 5) were already in it, and `ingest`, `scoring`,
  `training` and `prediction` each get their own stage (Stages 6–9), so that
  every spec's retirement can happen in the same commit that lands its
  conceptual equivalent. The alternative — leaving the four to a later plan —
  was rejected: it would leave the six-document goal unreachable and four
  specs with no retirement path.

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
*   **Reason for Rejection**: Rejected by author, 2026-11-16: the clean
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

One unified list, ordered by stage — fourteen stages, fifty-three entries.
Every file that the plan touches appears once, with what changes and why.
Three of these files are protected by project convention and need explicit
user approval when edited: `AGENTS.md`, `.gitignore` and `data/` — each is
flagged below. No code is specified here; signatures and schemas are described
in prose.

### Deviations from this plan (recorded decisions)

This plan was written before the stages ran. Where the execution departed
from it, the departure is recorded here rather than left for a reader to
discover by diffing the plan against the tree — a plan that lies about its
own state is worse than no plan. Each entry names the stage it changes, the
decision, and why.

| # | Stage | The plan said | What was decided | Why |
|---|---|---|---|---|
| 1 | 1 | The ODD is a byte-for-byte copy of `.cache/odd-latex/odd-2010-malariasentinel.tex` | It is no longer a copy. Stage 4's value machinery rewrote 668 lines to call the generated macros, and a verification pass against the code corrected fourteen substantive claims (the feeding semantics, the one-day prevalence lag, the configured habitat types, the parity-test claim, the two calibration statements, the three patch counts, the coastal band, the binomial rounding, the population comparison, the cohort age, the software-testing paragraph). | The copy was a starting point, not the deliverable: the plan's own goal is a document that matches the code, and the code had moved since the copy was written. The substance is as-built, not as-targeted. |
| 2 | 4 | One macro family (`\mskey`) over `model_constants.yaml` | Two families: `\mskey` for the model constants and `\codeconst{stage.name}` for the values that live in the code (the patch size, the channel counts, the verdict thresholds, the loaders' native grids). | Roughly a hundred values the documents state are readable from the code but are not model constants; a single family could not carry them without a YAML key per value, and a YAML key per value would duplicate the code. |
| 3 | 5–9 | Each document is revised once through the annotation → plan → commit loop (CUJ-4/CUJ-5) | The documents landed in one commit each and the loop did not run while they were written. It runs now, per document, with a plan that names the section each item invalidates. | The loop is a mechanism, not a deadline: the honest record is that it did not happen during authoring, and the remedy is to run it, not to claim it happened. |
| 4 | 10 | The site's stage index is written by hand in `documentacion.html` | It is generated (`docs/concepts/generated/stages.js`), and the page also links the technical reference and the stance note. | The plan's own rule for a hand-maintained index is "never". |
| 5 | 11 | Doxygen writes `docs/reference/cpp/html/index.html` | Doxygen writes `docs/reference/cpp/` itself (`HTML_OUTPUT = .`), so `docs/reference/cpp/index.html` exists and the index page's link resolves. The build clears the directory first, so a page from a previous build cannot survive. | The verification plan of Stage 11 requires both references to carry their own `index.html`; with the old layout the generated index pointed at a 404. |
| 6 | 12 | The reviewer's false-positive rate is measured over the last 20 merges | It cannot be: the documents have never been on `main`, so the population is empty. What was measured instead is written down in `docs/concepts/coherence-review.md`: the per-class precision of the mechanical signals, replayed over the branch's document-touching commits, plus the procedure and the instrumentation that will make the rate measurable once the documents land. | A number that could not be computed must not be printed as a number. The exit condition is met by stating plainly what is measured and what is not. |
| 7 | 13 | `git ls-files data/` ends up showing only `data/README.md` | The index keeps the README, the small XML sidecars, the PNG renderings and the open-access paper (16 files, ≈4.5 MB); every heavy product stays out. | The sidecars, the figures and the paper are the four kinds of material that no command regenerates, and the code and the papers refer to them (`mal-data-explorer/README.md`, `docs/licenses.md`). Untracking them would make the tree depend on the zip for its own documentation. The backup still exists and is verified, so nothing is at risk either way. |

### Stage 0 — Truth pass (one commit, no new concepts)

#### 1. `docs/README.md` (Modify)

*   **Type / Scope**: Documentation index.
*   **Proposed Changes**: Remove the six paths that do not exist
    (`specs/self_improve/`, `diagrams/`, and the four presentation/status
    files), and replace the sentence that names `docs/specs/abm/spec.md` "the
    single source of truth for engine data contracts" — together with the
    instruction to "keep specs current when the contract they describe
    changes" — with a pointer to the conceptual layer (`docs/concepts/<phase>/`).
    The exit condition is that no listed path is absent from the tree.
*   **Rationale**: This file is the entry point of the docs tree; a reader who
    follows it into nothing distrusts everything after it. Cheapest claim in
    the stale-claims table to fix. The "single source of truth" sentence
    cannot survive this plan: the spec it names is deleted by it, so the
    claim would be dangling the moment the plan lands.

#### 2. `AGENTS.md` (Modify — protected file, requires explicit user approval)

*   **Type / Scope**: Agent guide.
*   **Proposed Changes**: Three changes.
    (a) Rewrite the "Calibration framework conventions" section (it currently
    instructs editing `thresholds.yaml`,
    `scorers/composite.py::DEFAULT_WEIGHTS`, and running a deleted pytest
    harness) to describe what actually exists: `COMPOSITE_WEIGHTS` in
    `mal-core/src/mal_core/scoring/registry.py`, `min_score`/`hard_floor` as
    class attributes on `Scorer`, and no calibration pytest harness. The same
    edit fixes the "How to build, test, run" block, which still points at the
    deleted `mal-core/src/mal_core/abm/tests/calibration` directory.
    (b) Remove `mal-ghana-sim/` from the monorepo layout table and correct the
    package count: five packages have a `pyproject.toml` (`mal-commonlib`,
    `mal-core`, `mal-execution`, `mal-data-explorer` and `social-networks/`,
    which the table does not document), and six `pyproject.toml` files exist
    in the tree, the sixth being the workspace root.
    (c) The **untrusted-documents** note already exists: `AGENTS.md` carries a
    section stating that `docs/specs/*` is not authoritative and pending
    deletion. Nothing is added — the stage verifies that the note still names
    this plan's path and that no agent may take a spec claim as true.
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
    Stage 11 starts here too).
*   **Proposed Changes**: Correct the statements the code contradicts:
    `output_contract.hpp:3-5` still says band 1 = `adult_occupancy`, band 2 =
    `host_seeking_pressure` while the code writes
    `{"adult_patch_count","adult_cell_count"}`; the same header says the
    sidecar lists `k_max` (retired at contract 4.0) and later in the same
    file says it no longer does — that internal contradiction is resolved
    here; `:75-76` cites `docs/specs/abm/spec.md` as the authority for sidecar
    key order (the authority this design deletes). Full audit of the six
    headers' prose against the code — the audit is performed by this stage,
    and the open question closes when the stage completes.
*   **Rationale**: These six headers are where the contract lives; they are
    also the input to Stage 11's Doxygen build. Fixing content first means the
    generated reference is not structurally complete and semantically false.

#### 10. `mal-core/src/mal_core/abm/src/output_contract.cpp` (Modify)

*   **Type / Scope**: C++ source (the implementation of the output contract).
*   **Proposed Changes**: Two comments cite `docs/specs/abm/spec.md` as the
    authority — "The COG profile mirrors the output contract spec" and "The
    keys are emitted in the order listed in `docs/specs/abm/spec.md` so the
    byte-equal test is stable across engines". Replace both with the
    authority that survives this plan (the generated contract table,
    `docs/concepts/generated/contracts.tex`) or with the invariant stated
    directly.
*   **Rationale**: The specs this plan deletes are named as an authority in
    the implementation, not only in the headers. Stage 0's exit condition is
    "no stale claim remains in those files", and a claim in a `.cpp` is the
    same class of drift as a claim in a `.hpp` — the coherence reviewer's
    signal 6 (named paths vs the tree) would report it.

### Stage 1 — ODD out of `.cache/`

#### 11. `docs/concepts/abm/odd-2010-malariasentinel.tex` (Create — copy, then `git add`)

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

#### 12. `docs/concepts/abm/odd-2010-template.tex` (Create — copy, then `git add`)

*   **Type / Scope**: LaTeX template (the ABM stage's question set).
*   **Proposed Changes**: Byte-for-byte copy of
    `.cache/odd-latex/odd-2010-template.tex`, stored beside the document it
    questions (author's directive, 2026-11-16). This is the ABM stage's
    "template with the questions": the official ODD 2010 element list that
    the document answers.
*   **Rationale**: Document and questions live together, so a writer always
    finds both. For `abm` the question set is the official ODD template — an
    external standard, not something to author.

#### 13. `docs/concepts/abm/` build proof (no new file)

*   **Proposed Changes**: Run `latexmk -pdf odd-2010-malariasentinel.tex`
    unmodified in the tracked location; commit nothing else.
*   **Rationale**: Exit condition of Stage 1 — a tracked `.tex` compiles to
    PDF. Already verified on the unmodified file.

### Stage 2 — The two shared artefacts

#### 14. `docs/concepts/README.md` (Create)

*   **Type / Scope**: Documentation (the stance note).
*   **Proposed Changes**: "How to write a conceptual document": the stance
    S1–S10 stated in full (Appendix A of this plan), the devices
    that transfer (notation table with code-name aliases, schedule pseudocode
    plus consequences list, parameter tables with a provenance column,
    "consequences worth stating", "origin and rationale", data-versus-choice,
    negative purpose list, declaration of absences, evidence appendix), and
    the ODD as the worked example. Explicitly not a template: it fixes a
    stance and a method, never a section list.
*   **Rationale**: The only shared writing instrument of the six documents.
    A writer who has never seen the ODD review reads this page and knows how
    to ask.

#### 15. `.pi/skills/concept-doc/SKILL.md` (Create)

*   **Type / Scope**: pi skill (project-level).
*   **Proposed Changes**: A lightweight skill carrying the drafting
    operation: read the stage's question set, read the stance note, draft the
    document from the material, cite every claim, generate every value. It
    opens with the YAML frontmatter every other skill in `.pi/skills/` has
    (`name:`, `description:`), so that pi loads it; the description states
    the trigger — drafting the conceptual document of one pipeline stage.
    Changing the question set is a separate, supported operation (Stage 3's
    subagent), not this skill's.
*   **Rationale**: The note fixes the stance, the skill fixes the operation;
    together they are the only two shared artefacts, and neither prescribes
    a section list. The frontmatter is not cosmetic: without `name:` and
    `description:` the skill is not discoverable by pi.

### Stage 3 — Per-stage question sets and checklists

For each of the five non-ABM stages: one subagent reads that stage's material
(code, specs, plans) and returns the stage's questions with citations, in the
ODD's discipline of reading before asking. The `abm` question set already
exists as `odd-2010-template.tex` (file 12) and is not re-authored.

#### 16–20. `docs/concepts/<phase>/questions.md` (Create ×5)

Files: `docs/concepts/download/questions.md`,
`docs/concepts/ingest/questions.md`, `docs/concepts/scoring/questions.md`,
`docs/concepts/training/questions.md`,
`docs/concepts/prediction/questions.md`.

*   **Type / Scope**: Documentation (question set + done-checklist, Markdown).
*   **Proposed Changes**: Each file holds two parts: (a) the stage's question
    set — the questions its document must answer, every one traceable to a
    code/notes citation; (b) the stage's checklist — what "done" means for
    that document. Kept beside the stage's document, per the author's
    directive that the template with the questions lives with the LaTeX.
    Format is Markdown: these are working inputs to the drafting operation,
    not published artefacts, so they need no LaTeX build.
*   **Rationale**: No generic template; each stage gets the questions it
    needs, found by reading that stage's material. The checklist is per stage
    and does not generalise the document's structure.

### Stage 4 — Value generator, contracts file, first workflow

#### 21. `docs/concepts/contracts.yaml` (Create)

*   **Type / Scope**: Machine-readable contracts input (not a human document).
*   **Proposed Changes**: A small file describing each output artefact:
    artefact → producer stage → consumer stages → compatibility rule →
    band/variable names → sentinel value. **Contract versions are not
    duplicated here**: they come from `model_constants.yaml:contracts.*`
    (`env_nc`, `cogs_state`), which D2 makes the authority. The band names
    and sidecar keys are read from the code (`STATE_BAND_NAMES` in
    `wire.hpp`, sidecar key definitions in `output_contract.hpp`), and the
    generator (file 22) cross-checks this file against those headers and
    fails the build on a mismatch, so the file cannot drift silently. It is
    read only by the generator; no prose document cites it as authority — D2
    gives the *generated table* the authority, not this file.
*   **Rationale**: D1/D2 need a machine-readable source for the names the
    generated contract table carries, so that the table can win on
    contradiction. It is a generator input, deliberately not a human-maintained
    spec: the rejected alternative B was a *human document*; this is data
    feeding the build. A version field duplicated from
    `model_constants.yaml` would be a second source of truth with no defined
    winner — the exact drift D2 exists to prevent.

#### 22. `tools/gen_concepts_values.py` (Create)

*   **Type / Scope**: Python script (build tool, not pipeline code).
*   **Proposed Changes**: Reads the configuration through the existing
    validated loader — `mal_core.habitat.config.load_config()`, which runs
    `mal_core.config_validation.validate_model_config` — and walks the
    resulting dict; it does not parse the YAML a second time. The flat
    dotted-key view the generator needs already exists in the repository:
    `mal_core.habitat.config.dump_raw()` (with the C++ twin
    `abm/src/config_dump.cpp`), the parity reference for the py⇄C++ check.
    `dump_raw()` deliberately omits the py-only `wildlife` section and
    reshapes the species rows, so the generator walks the validated config
    directly and includes `wildlife` — the rule is stated here so no
    implementer has to choose. It also reads `docs/concepts/contracts.yaml`
    (file 21) and cross-checks it against the C++ headers, failing the build
    on a mismatch. It emits LaTeX into `docs/concepts/generated/`: per-stage
    parameter tables (name, value and unit), one contract table, and per-key
    macros (`\mskey{<dotted.key>}` expands to the current value). The unit
    is read from the convention the YAML already states in its header —
    "Unidades entre [ ]", so every parameter carries `# [mm]`, `# [días]`,
    `# [índice]` — and this entry makes that convention the generator's
    contract. The *meaning* of a parameter and its provenance tier are prose
    in the document, not generated values: they are judgements, and D1 only
    forbids hand-typed numbers. Deterministic output — same inputs,
    byte-identical files.
*   **Rationale**: D1: any number, key or symbol in a document is emitted at
    build time. Two failures follow: a key renamed or removed in the YAML is
    rejected by the configuration validator before the generator emits
    anything, and a key the schema tolerates becomes an undefined control
    sequence in a document that uses it, failing `latexmk`. Both are
    properties of the build (see also signal 1: dotted keys vs YAML with
    printed values, already implemented by
    `tools/audit_comment_constants.py`).

#### 23. `docs/concepts/generated/` (Create — directory of generated `.tex`)

*   **Type / Scope**: Generated LaTeX fragments (`params-<phase>.tex`,
    `contracts.tex`).
*   **Proposed Changes**: Output directory of file 21; committed so local and
    CI builds are identical and reviewable in the PR diff. Documents
    `\input{generated/...}` it; no document types a value by hand.
*   **Rationale**: Stage 4's exit condition — a build reproduces these
    byte-for-byte (`git diff --exit-code` after regeneration).

#### 24. `tools/build_concepts.sh` (Create)

*   **Type / Scope**: Shell script (build entry point).
*   **Proposed Changes**: Runs the generator (file 22), then `latexmk -pdf`
    over the document sources only — `docs/concepts/<phase>/<phase>.tex`,
    excluding the question templates (`odd-2010-template.tex` and any
    `questions.md` sibling) and the generated fragments in
    `docs/concepts/generated/`, which are `\input`, not documents — then
    regenerates and fails if `git diff --exit-code` shows drift in
    `docs/concepts/generated/`. Same command locally and in CI.
*   **Rationale**: One build recipe, no divergence between a developer's
    machine and the workflow; the byte-for-byte exit condition is executable.

#### 25. `.github/workflows/concepts.yml` (Create)

*   **Type / Scope**: GitHub Actions workflow (the repository's first — there
    is no `.github/` directory today).
*   **Proposed Changes**: On pull requests touching `docs/concepts/**`,
    `mal-core/config/model_constants.yaml`, or `docs/concepts/contracts.yaml`:
    run `tools/build_concepts.sh`, then compile each document and (on the PR
    branch, decision I1-A: the PDF is compiled in CI and committed back to
    the branch) rename the `latexmk` output to
    `docs/concepts/<phase>/<phase>.pdf` and commit it back to the branch. PDF
    equality is checked on extracted text
    (`pdftotext -layout`), not on bytes, until determinism is measured. The
    bot push dismisses stale approvals under the current ruleset — a workflow
    design constraint, documented in the workflow header, not a blocker.
*   **Rationale**: Stage 4 exit (first green run) and Stage 10 publication
    (I1-A: CI commits the PDF so the legacy `main:/docs` Pages build publishes
    it at a stable path). Fork PRs cannot receive the push; their PDF appears
    after merge — accepted under the warnings-only regime.

### Stage 5 — Pilot `download`

#### 26. `docs/concepts/download/download.tex` (Create)

*   **Type / Scope**: LaTeX source (first non-ABM conceptual document).
*   **Proposed Changes**: Drafted by an agent from
    `docs/concepts/download/questions.md` and the stance note; answers every
    question in the set in the stage's own structure; inputs/outputs are one
    section among others; all values come from `\input{generated/...}`; every
    code symbol is glossed at its first use; the examples are described
    situations, not code snippets. The internal seam stays visible as a
    section of the document: AOI reduction happens after areal-fraction
    aggregation.
*   **Rationale**: Stage 5 exit — one non-ABM document written, read by
    someone without a code profile, and revised once through the full loop.
    Pilot on the smallest stage, not the largest.

#### 27. `docs/plans/in-process/<plan-name>.md` (Create — as annotations arrive)

*   **Type / Scope**: Plan files (existing directory and mechanism).
*   **Proposed Changes**: Human annotations on the pilot document are
    distilled into plans naming the document section they invalidate and the
    code change required — the same mechanism that produced the 13
    `odd-fixes` packs. Applying a plan updates code and document in the same
    PR.
*   **Rationale**: The authoring loop, end to end. This is the main detection
    instrument under D3 (warnings-only): the human annotation step, with the
    annotations as the defect channel.

### Stage 6 — The `ingest` document

The loop of Stage 5, one stage per remaining document (D10). Stage 3 already
produced this stage's question set (`docs/concepts/ingest/questions.md`); this
stage drafts the document, takes the human's annotations through the plan
mechanism, and applies the plan's result back into the document.

#### 28. `docs/concepts/ingest/ingest.tex` (Create)

*   **Type / Scope**: LaTeX source (the `ingest` conceptual document).
*   **Proposed Changes**: Drafted by an agent from
    `docs/concepts/ingest/questions.md` and the stance note; answers every
    question in the set in the stage's own structure; inputs and outputs are
    one section among others; all values come from `\input{generated/...}`;
    every code symbol is glossed at its first use; the examples are described
    situations, not code snippets. The stage's internal seam stays visible:
    `ingest` is where the spatial frame `(H,W)` is computed, and the document
    says so where the frame is first used.
*   **Rationale**: Stage 6 exit — the `ingest` document written, read by
    someone without a code profile, and revised once through the full loop.
    The stage also carries the retirement of `docs/specs/ingest/spec.md`, in
    the same commit that lands the document's final form.

### Stage 7 — The `scoring` document

The loop of Stage 5 again, for the stage whose behaviour the scorer registry
describes.

#### 29. `docs/concepts/scoring/scoring.tex` (Create)

*   **Type / Scope**: LaTeX source (the `scoring` conceptual document).
*   **Proposed Changes**: Drafted by an agent from
    `docs/concepts/scoring/questions.md` and the stance note; answers every
    question in the set in the stage's own structure; all values come from
    `\input{generated/...}`; every code symbol is glossed at its first use;
    the examples are described situations. The stage's internal seam stays
    visible: the composite is a geometric mean over its dimensions and the
    gates are evaluated separately — the document says so where the composite
    is first used.
*   **Rationale**: Stage 7 exit — the `scoring` document written, read by
    someone without a code profile, and revised once through the full loop.
    The stage also carries the retirement of `docs/specs/scoring/spec.md`, in
    the same commit that lands the document's final form.

### Stage 8 — The `training` document

The loop of Stage 5 again.

#### 30. `docs/concepts/training/training.tex` (Create)

*   **Type / Scope**: LaTeX source (the `training` conceptual document).
*   **Proposed Changes**: Drafted by an agent from
    `docs/concepts/training/questions.md` and the stance note; answers every
    question in the set in the stage's own structure; all values come from
    `\input{generated/...}`; every code symbol is glossed at its first use;
    the examples are described situations. The stage's internal seam stays
    visible: what the surrogate trains against, and what it cannot represent,
    are stated where the surrogate is first used.
*   **Rationale**: Stage 8 exit — the `training` document written, read by
    someone without a code profile, and revised once through the full loop.
    The stage also carries the retirement of `docs/specs/training/spec.md`, in
    the same commit that lands the document's final form.

### Stage 9 — The `prediction` document

The loop of Stage 5 again, for the last of the six.

#### 31. `docs/concepts/prediction/prediction.tex` (Create)

*   **Type / Scope**: LaTeX source (the `prediction` conceptual document).
*   **Proposed Changes**: Drafted by an agent from
    `docs/concepts/prediction/questions.md` and the stance note; answers every
    question in the set in the stage's own structure; all values come from
    `\input{generated/...}`; every code symbol is glossed at its first use;
    the examples are described situations. The stage's internal seam stays
    visible: the prediction consumes the state bands the `abm` stage writes,
    and the document says so where the consumption is first described.
*   **Rationale**: Stage 9 exit — the `prediction` document written, read by
    someone without a code profile, and revised once through the full loop.
    The stage also carries the retirement of `docs/specs/prediction/spec.md`
    and `docs/specs/_template.md`, in the same commit that lands the
    document's final form.

### Stage 10 — Publication

#### 32. `docs/documentacion.html` (Create)

*   **Type / Scope**: Site page (HTML, legacy Pages build).
*   **Proposed Changes**: A separate documentation page under `docs/`, linked
    from the site navigation, carrying its own ES/EN dictionaries. It lists
    the conceptual documents that exist, with links to their committed PDFs
    (`docs/concepts/<phase>/<phase>.pdf`), plus the stance note; a document is
    linked as it lands, and the technical reference is added at Stage 11.
    Generated docs index — never a hand-maintained one.
*   **Rationale**: The landing page has zero links to any document today; its
    navigation is five in-page anchors. Keeping the new page separate leaves
    the 200 KB `index.html` and its i18n dictionary untouched except for the
    nav entry (file 33).

#### 33. `docs/index.html` (Modify)

*   **Type / Scope**: Site landing page (hand-written, ES-first).
*   **Proposed Changes**: Two changes in one commit: (a) truth pass on the
    stale claims, with the replacement copy fixed here so that no wording is
    left to the implementer:
    *   "Motor ABM en C++ + 14 Scorers", "14 evaluadores de calibración
        automatizados" and "suite of 14 evaluadores de calibración (PR gate)"
        become "19 evaluadores de calibración (13 dimensiones + 6 gates)" and
        "19 calibration scorers (13 dimensions + 6 gates)". The "(PR gate)"
        clause goes with them: the calibration pytest harness does not exist,
        and D3 forbids a gate.
    *   "densidad normalizada de mosquitos (agentes/K_MAX)" becomes "densidad
        de mosquitos (adultos/km²)". `K_MAX` was retired at contract 4.0, and
        the state bands are raw adult counts per 1 km² cell.
    *   "Ghana (Nacional predefinido · 9.466 celdas)" becomes "Ghana (Nacional
        predefinido · 429.229 celdas)" — 551 × 779 cells at 1 km resolution,
        per the ODD.
    *   The AOI option "Mozambique (Nacional predefinido)" is removed:
        `aois.yaml` defines only `ghana` and `accra-coastal-test`.
    Every one of these strings exists in both the inline HTML and the
    `T.es`/`T.en` dictionaries, and `setLang()` overwrites the DOM from the
    dictionaries at runtime — so the edit must touch the dictionaries, not
    only the inline markup, or the rendered site keeps the false text.
    (b) add one nav entry pointing at `documentacion.html` — desktop nav,
    mobile drawer, footer row, and both dictionaries, in the same edit.
*   **Rationale**: The site is the reader's entry point (CUJ 1) and today
    promises "documentación técnica accesible" while linking only GitHub. The
    four-edition rule (nav + drawer + footer + both dictionaries) is a
    property of this file's structure, not a choice.

### Stage 11 — Generated technical reference

#### 34. The six contract-defining headers, comment-polished (Modify)

Files (already touched in Stage 0, content completed here):
`wire.hpp`, `output_contract.hpp`, `habitat_availability.hpp`,
`habitat_engine.hpp`, `coordinator.hpp`, `config.hpp` — all under
`mal-core/src/mal_core/abm/include/mal_abm_fast/`.

*   **Proposed Changes**: Convert file-header prose and trailing `//` member
    comments to forms Doxygen attaches (`///`, `/** */`, `///<`, `//!<`),
    excluding `third_party/` — which contains `font8x8_basic.hpp` — from the
    build. The tests are not under the Doxygen `INPUT` (file 36), so they
    need no exclusion. Content was already corrected in Stage 0; this pass
    is mechanical form conversion on the contract-defining headers only —
    the six headers listed here, not the whole tree.
*   **Rationale**: I2-A: polish scoped to where the contract lives, before
    generation. Zero Doxygen directives exist today; trailing `//` is
    invisible to Doxygen; a generated document from current comments would be
    structurally complete and semantically false.

#### 35. Python docstring corrections (Modify)

Files: `mal-core/src/mal_core/scoring/llm_scorer.py` (says "10 deterministic
scorers (D1..D10)"; registry has 13 composite + 6 gates; and says the LLM is
"invoked directly via `langchain_openai`", while the implementation posts to
`LLM_BASE_URL` with `requests`),
`mal-core/src/mal_core/scoring/config.py` (names `D16_suitability_auc` in a
docstring example; the runtime name is `D16_detection_coverage`),
`mal-core/src/mal_core/habitat/constants.py` (documents constants the module
raises `AttributeError` for),
`mal-commonlib/src/mal_commonlib/config.py` (`SimParams.r_of()` calls
undefined `temp_suitability`; docstring cites `DESIGN.md`, which does not
exist).

*   **Proposed Changes**: Fix the false statements these four files carry
    before pdoc publishes them; remove or correct the dead `r_of()` path.
*   **Rationale**: Same as file 29 — generation is cheap, truth is not.
    Publishing autodoc as-is publishes at least five known-false statements
    across four files.

#### 36. `docs/reference/Doxyfile` (Create)

*   **Type / Scope**: Doxygen configuration.
*   **Proposed Changes**: `INPUT` is the six contract-defining headers only
    (`wire.hpp`, `output_contract.hpp`, `habitat_availability.hpp`,
    `habitat_engine.hpp`, `coordinator.hpp`, `config.hpp`, all under
    `mal-core/src/mal_core/abm/include/mal_abm_fast/`), `RECURSIVE = NO`,
    `EXTRACT_ALL = YES`, `HAVE_DOT = NO`, `GENERATE_LATEX = NO`, output to
    `docs/reference/cpp/`, excluding `third_party/*`. The input is narrowed on
    purpose: the include tree holds about forty-five headers, of which only
    six are polished, and publishing the rest would produce a reference that
    is structurally complete and semantically false — the risk this design
    names for the Python side.
*   **Rationale**: I2-A: Doxygen plus pdoc generation. Namespaced output so
    Doxygen's `index.html` and
    `_`-prefixed directories cannot collide with pdoc's under the legacy
    Pages build. Greenfield today — no Doxyfile exists, so it will be done
    wrong by default unless specified.

#### 37. `tools/build_reference.sh` (Create)

*   **Type / Scope**: Shell script (reference generation entry point).
*   **Proposed Changes**: Runs Doxygen with file 31, runs pdoc over
    `mal_core` and `mal_commonlib` into `docs/reference/python/`, and emits a
    generated index page linking both surfaces. The flag/file contract is
    included only if I2-B is built (see Open Questions); the script stubs
    the section either way, so the stage's exit condition holds in both
    cases. Same command locally and in CI.
*   **Rationale**: One recipe for both generators; output lands somewhere
    greppable, which is the condition under which the reference has a real
    consumer (agents, IDE).

#### 38. `.github/workflows/concepts.yml` (Modify — extend)

*   **Proposed Changes**: Add a job on pushes to `main` touching
    `mal-core/src/mal_core/abm/include/**` or `mal-*/src/**/*.py`: run
    `tools/build_reference.sh`, commit `docs/reference/**` back to the branch
    (same I1-A topology and same stale-approval constraint).
*   **Rationale**: Generated reference must be published under the legacy
    Pages build, which compiles nothing; committing is the only topology that
    works without a Pages migration (rejected this phase).

### Stage 12 — Warnings-only coherence review

#### 39. `.github/workflows/coherence-review.yml` (Create)

*   **Type / Scope**: GitHub Actions workflow (PR-triggered).
*   **Proposed Changes**: On pull requests: extract the mechanical signals
    (dotted keys vs `model_constants.yaml` with printed values; `\code{}`
    identifiers vs Python/C++ symbols; contract versions vs
    `model_constants.yaml:contracts.*`; recomputable numbers from
    `aois.yaml`; `latexmk -Werror`; named `docs/…`, `papers/…`, `scripts/…`
    paths vs the tree; documented outputs vs consumer globs; changed path →
    candidate document; `% sources:` freshness; and the two guards the
    repository already ships — `tools/audit_comment_constants.py` and
    `tools/check_no_constants.sh`), assemble diff + affected stage documents
    + in-process plans, and hand them to an LLM reviewer that posts a PR
    comment naming the passage that no longer matches the code, quoting
    both. The model id comes from a repository variable and the key from the
    `OPENROUTER_KEY` repository secret — the path the project's LLM scorer
    already uses (`mal-core/src/mal_core/scoring/llm_scorer.py`); the
    workflow's own default token budget applies. `continue-on-error: true`;
    the check is never required. Fork PRs (no secrets): the mechanical
    signals still run, the LLM step reports "semantic check skipped (fork)"
    in the comment, and the workflow exits 0 — a missing secret is not a
    failure and not a gate. Bot-loop guard: the workflow does not trigger on
    its own comment pushes.
*   **Rationale**: D3: warnings only, no gates — no anchor-existence check,
    no presence rule, no waiver trailer, no required status. The mechanical
    signals are inputs the reviewer may cite, not pass/fail tests. Exit
    condition: the first-pass false-positive rate is measured over the last
    20 merges on `main` — or all of them if the repository has fewer — and
    written down before anyone relies on the reviewer. A *false positive* is
    a finding the author confirms does not correspond to a real incoherence.
    No threshold is set on that number: under D3 the reviewer never blocks,
    and the number informs the author's decision to rely on it rather than
    gating it.

#### 40. `.github/concepts-review-prompt.md` (Create)

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

### Stage 13 — `data/` untracking (last step, after the backup is proven)

The author's decision (2026-11-16) supersedes the D8 pre-work: the manifest
rebuilds itself, in two halves — `download` re-registers the upstream products
from the downloader registry, `ingest` re-registers the derived ones — so
there is no manifest relocation, no `MAL_DATA_ROOT`, no restore script and no
offline-copy inventory. The safety net is one zip archive in the repository's
parent directory, written and verified before anything is untracked.

#### 41. `../MalariaSentinel-data-backup-<YYYY-MM-DD>.zip` (Create — outside the repository)

*   **Type / Scope**: Backup archive (parent directory of the repository, never
    inside it — a tracked or ignored in-tree archive is not a backup).
*   **Proposed Changes**: `zip -r` the whole `data/` tree (tracked and ignored
    files alike: the 4 GB of downloaded products and the 16 small tracked
    files), then verify with `unzip -t` and write the archive's `sha256` in a
    single file beside it — a checksum for one archive, not an inventory of
    the tree. The archive's path and checksum are recorded in
    `data/README.md` (file 44).
*   **Rationale**: Git is not a backup for the ignored 4 GB — history contains
    none of it — and the tracked 16 files are not recoverable from a
    `git rm --cached` if the working copy is lost. One verified zip is the
    cheapest real safety net: it restores exactly what was there, including
    the four kinds of material that `download` does not regenerate (the
    `moua_2016.pdf` paper, the `data/maps/*.png` renderings — which the
    explorer, not `download`, produces — and the `eml.xml`/`meta.xml`
    sidecars).

#### 42. `.gitignore` (Modify — protected file, requires explicit user approval)

*   **Type / Scope**: Ignore rules.
*   **Proposed Changes**: Replace the six current `data/` rules
    (`data/**/*.txt` and `data/**/*.zip` at `.gitignore:10-11`,
    `data/pasteur_anopheles.zip` and `data/occurrence.txt` at `:12-13`,
    `data/ghana/` at `:20`, `data/accra-coastal-test/` at `:22`) with
    `data/*` plus a `!data/README.md` negation. The form matters: git does
    not descend into an excluded directory, so a `!data/README.md` negation
    under a blanket `data/` rule is inert — `data/*` is what lets the
    negation re-include the file. The same edit corrects the two stale
    comments in the file: `.gitignore:8` advertises
    `scripts/restore_data.py` and `:19` mentions `scripts/build_2year_nc.py`,
    and no `scripts/` directory exists in the repository. It also adds the
    LaTeX build artefacts (`*.aux`, `*.log`, `*.fls`, `*.fdb_latexmk`,
    `*.out`, `*.toc`) under `docs/concepts/` and `docs/reference/` to the
    ignore rules, so the committed tree carries no build noise.
*   **Rationale**: The untracking rule itself. Protected file: the change needs
    the user's explicit approval, and it is the step where a mistake loses the
    local copy — which is why the zip exists and is verified first. The two
    stale comments are corrected here rather than in Stage 0 because this
    entry already rewrites the `data/` rules and `.gitignore` is not in
    Stage 0's scope — and the coherence reviewer's signal 6 (named paths vs
    the tree) would report them.

#### 43. `git rm -r --cached data` (index operation — not a file)

*   **Type / Scope**: Git index.
*   **Proposed Changes**: Two steps, in order: `git rm -r --cached -- data`
    (never `rm`) removes the tree from the index while the working tree is
    untouched; then `git add -- data/README.md` re-adds the one file that
    stays tracked. The second step is not optional: the pathspec `data`
    covers `data/README.md` as well, so without it the README leaves the
    index too, and the exit condition cannot hold. After this,
    `git ls-files data/` shows only `data/README.md`.
*   **Decision (applied 2026-11-16, commit 4e833bf; recorded as deviation 7
    above)**: the index keeps the README, the four `eml.xml`/`meta.xml`
    sidecars, the seven PNG renderings and the open-access paper — sixteen
    files, ≈4.5 MB, of which the paper is 2.6 MB. Every heavy product (the
    env/host rasters, the DwC-A archives, the NetCDFs, the GeoTIFFs) is
    excluded by the format rules in `.gitignore` and stays out of the index.
    The reason is the one this stage itself states: the sidecars, the
    figures and the paper are the material no command regenerates, and the
    repository refers to them (`mal-data-explorer/README.md` points at the
    figures, `docs/licenses.md` at the paper). Untracking them would make
    the tree's own documentation depend on the zip. The backup is verified
    either way, so the choice is about convenience, not about safety.
*   **Rationale**: The index is what makes `data/` travel to GitHub. Removing it
    from the index, with the working tree untouched, is the whole of
    "untracking" — `rm` would destroy the local copy the zip was made from.
    The re-add keeps the documentation that explains the tree inside the
    tree it describes.

#### 44. `data/README.md` (Modify)

*   **Type / Scope**: Data documentation (the only tracked file under `data/`).
*   **Proposed Changes**: Document the backup archive's path and checksum, the
    re-download path (`uv run malariasim download --aoi <aoi>` re-registers
    the upstream datasets from the registry, and `uv run malariasim ingest`
    re-registers the derived products), what is *not* regenerated by those
    commands (the paper, the map renderings, the sidecars) and therefore
    depends on the zip, and the fact that a dataset whose credentials are
    absent is **skipped** rather than failed — so the manifest comes back
    partial until the credentials are in place. The citation
    "(spec: `docs/specs/data/spec.md`)" is removed, because this plan deletes
    that spec. No new licence claim is written: the licence record already in
    this file and in `docs/licenses.md` §3 (with
    `mal_commonlib.data.licenses.KNOWN_LICENSES` as the machine authority)
    stays as it is — `env`, `habitat`, `host_static` and `mobility_*` are
    derived products with compound, inherited licences, not ODbL per se.
*   **Rationale**: The manifest is rebuilt by the downloader and the ingester,
    so the only surviving loss is the material neither produced — and the file
    that survives untracking is the one that must say so. Restating the
    licences here would create a third copy of a record that already has a
    machine authority, which is the drift class this plan exists to remove.

### Spec retirement (distributed across stages, not a stage)

#### 45–53. `docs/specs/<phase>/spec.md` and `docs/specs/_template.md` (Delete — one per stage)

Nine files, one per stage plus the template: `download/spec.md` (with Stage
5), `data/spec.md` (its AOI product and manifest schema land in the
`download` document per D5), `ingest/spec.md` (Stage 6),
`commonlib/spec.md` (the spatial frame — AOI, `Scale`, `cells_per_side`,
grid, CRS — lands in `ingest`, the first stage that needs `(H,W)`), and
`abm/spec.md` (after Stage 1's document is current), `scoring/spec.md` (Stage
7), `training/spec.md` (Stage 8), `prediction/spec.md` (Stage 9), and
`_template.md` with the last one.

*   **Proposed Changes**: Each spec is deleted in the same commit that lands its
    conceptual equivalent — section-level cut-over: the change that adds §X
    deletes §X. No file-level coexistence window where two authorities
    describe the same contract. Before a spec is deleted, its runnable
    assertions are either migrated — into the coherence reviewer's mechanical
    signals or into `tests/` — or explicitly recorded as dropped in the plan
    tracker (`docs/plans/in-process/`); `docs/specs/abm/spec.md` alone
    contains checks such as `assert cv.startswith('2.')`,
    `assert len(dims) == 13 and len(gates) == 6` and a `H = W = 128` grep,
    and deleting them without a decision would lose machine signal.
*   **Rationale**: Brief goal — retire stage by stage with no information
    loss: semantics move to the conceptual document, values to the generated
    tables. File-level retirement would guarantee two authorities for months,
    so retirement is distributed, not batched. D10 gives every stage a
    document, so every spec has the commit in which it can be retired.

### Verification Plan

*   **Stage 0**: `find`-based check that every path named in
    `docs/README.md` and `AGENTS.md` exists; `AGENTS.md` states that
    `docs/specs/*` is untrusted and pending deletion (already true — the
    stage verifies it, and the three spec claims above are deliberately left
    standing — this design does not repair them); each of the six headers'
    contract statements diffed against `STATE_BAND_NAMES`/sidecar
    definitions in code; `output_contract.cpp` cites no deleted spec.
*   **Stage 1**: `latexmk -pdf` on the tracked unmodified `.tex` exits 0 and
    produces a 32-page PDF. The source build was verified on 2026-11-16
    (32 pages, in `.cache/odd-latex/`); the tracked copy is re-verified here.
*   **Stage 2**: A reader who has never seen the ODD review uses the stance
    note to answer one sample question set (manual, exit condition of Stage
    2).
*   **Stage 3**: Every question in each `questions.md` carries at least one
    `file:line` citation; spot-check 5 per stage against the cited lines.
*   **Stage 4**: Run `tools/build_concepts.sh` twice; second run leaves
    `git diff --exit-code` clean on `docs/concepts/generated/`. Then, in a
    scratch branch, rename one key in `model_constants.yaml` and confirm the
    generator fails at configuration validation with a `ConfigError` — the
    schema-level automatic failure. The LaTeX-level failure is demonstrated
    at Stage 5, where a document actually uses a generated macro: delete that
    macro from the generated fragments and confirm `latexmk` fails with an
    undefined control sequence.
*   **Stage 5**: `docs/concepts/download/download.tex` compiles; a reader
    without a code profile answers the pilot checklist (CUJ 1); the document
    is revised once through the annotation → plan → commit loop (CUJ 4,
    CUJ 5); the LaTeX-level automatic failure is demonstrated here (delete a
    generated macro the document uses → `latexmk` fails).
*   **Stages 6–9**: the same three checks per document — the
    `docs/concepts/<phase>/<phase>.tex` of the stage compiles, a reader
    without a code profile answers its checklist, and the document is revised
    once through the annotation → plan → commit loop — and the spec of the
    stage is deleted in the same commit that lands the document's final form.
*   **Stage 10**: From `malariasentinel.com` in both ES and EN, a reader
    reaches the `download` PDF in ≤2 clicks (CUJ 1); the stale claims in
    `index.html` are gone from the rendered page in both languages — the
    inline markup *and* the `T.es`/`T.en` dictionaries, since `setLang()`
    overwrites the DOM from the dictionaries at runtime.
*   **Stage 11**: `tools/build_reference.sh` exits 0; `docs/reference/cpp/`
    and `docs/reference/python/` are both present with their own
    `index.html`; a check over the six headers confirms that no *live*
    `k_max` key and no two-band statement remains — the retirement notes that
    mention the removed `k_max` are legitimate and must not trip the check;
    and, if I2-B is built, the flag/file contract page lists every flag of
    the compiled ABM binary that `_introspect_flags` scrapes
    (`mal-core/src/mal_core/abm/wrapper.py`), stating that the `malariasim`
    Typer CLI is outside that scope.
*   **Stage 12**: The reviewer's false-positive rate over the last 20 merges
    **cannot be measured today** — the documents have never been on `main`,
    so the population is empty; the stage closes instead with the measurable
    substitute written down in `docs/concepts/coherence-review.md`: the
    per-class precision of the mechanical signals, replayed over the
    branch's document-touching commits, the procedure and the instrumentation
    that will make the rate measurable once the documents land, and a
    statement of what was not measured. A PR that changes only a comment
    under `mal_core/<stage>/` must produce no incoherence finding from the
    LLM reviewer (there is no presence rule, so this asserts a behaviour, not
    the absence of a mechanism).
*   **Stage 13**: The zip exists in the repository's parent directory and
    passes `unzip -t`; `git ls-files data/` shows the documented tracked set
    (the README, the XML sidecars, the PNG renderings and the paper — see
    deviation 7) and no heavy product, while the working tree still holds
    every file; clean-room clone →
    `uv sync --all-packages` → `uv run malariasim download` (which rebuilds
    the upstream half of `data/<aoi>/manifest.json` from the registry, from
    nothing) → `uv run malariasim ingest` (the derived half) →
    `abm --days 1` passes; restoring the zip over the clone reproduces the
    pre-untracking tree. The download step requires the dataset credentials
    (`~/.cdsapirc` or `CDSAPI_RC`, `EARTHDATA_TOKEN`, Earth Engine
    credentials): a dataset whose credentials are absent is skipped rather
    than failed, and the manifest comes back partial — so the check runs with
    credentials, or asserts only the upstream half it can reach.
*   **Static analysis / linting**: unchanged — this design adds no production
    code; the only new Python (file 22) follows the repo's existing
    conventions and is exercised by its own exit conditions above. Note that
    `tools/format.sh` covers the four packages only, so the new script under
    `tools/` is outside the repository's own lint scope; it is formatted by
    hand against the same `ruff` rules.

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
