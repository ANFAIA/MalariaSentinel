# Open decisions I1–I6 — options and implications

Companion to `concepts_brief.md`. Each decision states the options, what each
one costs, and what it forecloses. Verified facts are cited inline.

## I1 — Where the compiled PDFs live

**Constraint on the ground.** GitHub Pages serves a *legacy build* from
`main:/docs`: `docs/CNAME` = `malariasentinel.com`, `docs/.nojekyll` exists,
and there is no `.github/workflows/` directory in the repo. A legacy build
publishes whatever is committed in `docs/` — it compiles nothing. So "PDFs
compiled in CI" is not a build-time detail of the site; it needs one of three
topologies, and each changes who publishes, when, and what the link looks like.

### Option A — CI compiles and commits the PDF back to the branch

The workflow builds `docs/concepts/<phase>/*.pdf` and pushes it to the same PR
branch; the site link points at a stable path such as
`docs/concepts/abm/abm.pdf`. After merge, the legacy build publishes it.

- *Implication for links:* stable, permanent, no redirects. The site can link a
  phase's PDF with a single fixed URL that never changes.
- *Implication for the repo:* every documentation change produces a binary
  commit. PDFs are not diffable, so the history fills with opaque blobs; each
  rebuild of the same `.tex` produces a different binary unless the build is
  made deterministic (fixed `SOURCE_DATE_EPOCH`, reproducible TeX toolchain).
  `pdftotext -layout` content hashing is the cheap proxy the lenses proposed
  instead of byte hashing.
- *Implication for the ruleset:* the bot commits to the branch, and a push
  dismisses stale reviews under the current ruleset (1 approval, dismiss stale
  reviews on push). A bot push can therefore invalidate a human approval on the
  same PR. This is a workflow design constraint, not a blocker.
- *Implication for forks:* a fork PR cannot push to the upstream branch, so the
  PDF never appears in that PR's preview; the PDF appears after merge. Fine
  under the warnings-only regime.
- *Cost:* one workflow, one commit per doc change, binary churn.

### Option B — Publish PDFs as release assets

CI builds the PDFs and attaches them to a GitHub Release; `docs/` holds only
the `.tex`.

- *Implication for links:* the site must link
  `https://github.com/<org>/<repo>/releases/latest/download/abm.pdf` to get a
  moving "latest" pointer, or a versioned URL for a frozen citation. The
  versioned form is better for citation but breaks a static link on the site
  unless the site is updated per release.
- *Implication for the repo:* clean history, no binaries in git.
- *Implication for freshness:* a PDF exists only if a release was cut. Either
  a release per merge of a documentation change (heavy, and it makes releases
  mean two different things), or releases lag behind `main` and the site's
  "latest" link points at a document that no longer matches the code.
- *Cost:* lowest repo churn, highest "is it current?" risk.

### Option C — Migrate Pages to a build workflow

Replace the legacy build with `.github/workflows/pages.yml`: build LaTeX →
PDF, build the generated technical docs → HTML, assemble the site with the
existing `index.html` and assets, deploy as a Pages artifact.

- *Implication:* the natural home for both PDFs and generated Doxygen/pdoc
  output, with no binaries in git and no staleness. It also gives a single place
  to enforce "the site always builds".
- *Implication:* it touches the thing that currently works. `CNAME`,
  `index.html` (200 KB, hand-written, i18n via `data-i18n`), favicons and the
  web manifest must be reproduced by the new pipeline or served from the same
  tree. A mistake here takes the public site down, and the site is the project's
  public face.
- *Implication:* it is the only option that solves I2's "same visual style"
  problem structurally rather than by convention.
- *Cost:* highest, and it is an infrastructure change the documentation project
  does not strictly require.

### Recommendation

A now, C later if the generated technical documentation lands and the "same
style" requirement becomes real. B only if the PDF is meant to be a frozen
citation artefact rather than a living document.

## I2 — Toolchain for the generated technical reference

**Constraint on the ground.** There is no pybind11 in the project — the Python
side shells out to the compiled binary via `subprocess` and introspects its
`--help` (`mal-core/src/mal_core/abm/wrapper.py`). The real Python↔C++
interface is four things: CLI flags, `model_constants.yaml` keys, input file
formats (NetCDF variables, GeoPackage, CSR) and output contracts (COG band
names + sidecar keys). The C++ tree is 101 files / 25,793 lines, of which the
~40 headers under `include/mal_abm_fast/` are internal and untouched by any
Python caller. There are zero Doxygen directives in the tree today, and trailing
`//` comments are invisible to Doxygen.

### Option A — Doxygen for C++ plus pdoc or Sphinx for Python

Two generators, two output surfaces, linked from one site section.

- *Implication:* standard, well-known, cheap to run. Doxygen gives the C++ side
  a real API reference quickly *if* comments are converted to `///` or `/** */`
  form — that is a large mechanical edit across 25,793 lines, and the existing
  comments also need their *content* fixed, because several headers still
  describe the retired two-band / `k_max` contract and the Python docstrings
  publish at least four statements the code contradicts. A generated document
  that is structurally complete and semantically false is worse than no
  document.
- *Implication:* two HTML surfaces with two different styles, neither matching
  the landing page's hand-written style. "Same visual style" is not achievable
  for generated HTML without re-skinning both tools, which is real work.
- *Implication:* it documents the C++ class hierarchy, which is *not* the
  interface that breaks in practice. Flag renames and file-contract drift go
  undocumented.

### Option B — One purpose-built generator for the flag-and-file contract

A script that reads the CLI definition, `model_constants.yaml`, the input file
schemas and the output contract definitions, and emits one reference page
describing exactly the interface a consumer must respect.

- *Implication:* documents the interface that actually breaks, in one place,
  in one style, and it can be generated with the same build-time machinery as
  the conceptual documents' value tables.
- *Implication:* it is custom code to write and maintain, and it cannot cover
  "what does this internal function do" — which is what a developer usually
  wants from an API reference. It is a contract reference, not a code reference.
- *Cost:* a real piece of engineering, but a small one next to a full Doxygen
  migration.

### Option C — Defer the technical reference

Do Stage 7 later; the conceptual layer and the site come first.

- *Implication:* the comment-polish work still has to happen eventually if the
  reference is wanted, and doing it late means the polish pass is motivated by
  a tool rather than by the code's next reader.
- *Implication:* nothing is lost; the pipeline can absorb it at any point.

### Recommendation

A after a comment-polish pass scoped to the contract-defining headers only
(`wire.hpp`, `output_contract.hpp`, `habitat_availability.hpp`,
`habitat_engine.hpp`, `coordinator.hpp`, `config.hpp`) — i.e. the headers where
the contract actually lives — plus pdoc for Python, where docstrings already
mostly exist. B as a later complement if the flag/file reference proves
necessary. C is the fallback if the polish pass turns out larger than expected.

## I3 — Document skeleton (author's answer: start from option C, with a twist)

**Decision (2026-11-16).** Option C — free-form per typology, no shared
skeleton — with one addition that emerged from the ODD investigation
(`concepts_brief.odd-method.md`): the *section list* is per typology, but the
**stance** is shared.

### What the ODD investigation changed

The ODD's value is not its seven elements. The evidence: of the ~85 reviewer
comments in `odd-2010-malariasentinel-notes.tex`, the most damaging ones are
criticisms of *documentation adequacy*, not of the model — aggregation level
(`notes:238, 248, 900, 1393`), where randomness and parameters live
(`notes:726, 745, 966`), output resolution (`notes:758, 765, 792`), duplicated
state (`notes:321-322`). The comments that attack the science (movement,
discretisation, salinity) would have been made about the code anyway. The
format's contribution is the **discipline of writing something a hostile reader
can check against the code** — which is why the reference document's Appendix A
(14 implementation notes, `odd-2010-malariasentinel.tex:1728-1855`) surfaced
eleven code defects: `feeding_success_rate` loaded but never drawn, a
`MultirateDayState` member never advanced, the GeoPackage `dynamics` column read
as int but stored as string, `"sha256:pending"` in the sidecar, `eip_frac` that
is not an EIP fraction.

So the transferable thing is a **stance**, expressible without any section list:
purpose first and separate from mechanism; every magnitude named with identity,
units, native and target resolution; data-versus-choice stated explicitly;
every constant carrying a provenance tier; state separated from derived from
cache; absences declared; order of operations written at the granularity where
order matters, with its consequences stated; outputs given with their
consumption contract; and an evidence appendix. The full statement with
citations is S1–S10 in `concepts_brief.odd-method.md`.

### What this means concretely

- *Per typology, the document asks its own questions.* `download` has no
  entities and no time steps, so it does not get an "Entities" section; it gets
  questions about provenance of each source, the format each arrives in, the
  transformation applied, and what it becomes. `scoring` gets questions about
  what a score means and what it is for. `abm` keeps the ODD's elements because
  the ODD *is* its document.
- *Shared:* the stance above, the notation convention, the parameter/provenance
  table format, the "consequences worth stating" habit, and the two appendices
  (implementation notes; provenance/versioning/testing status). Those are
  devices, not a table of contents.
- *Consequence for the reviewer:* there is no fixed slot to check. The warnings
  review compares the diff against the document of the affected stage and asks
  whether the document's claims still hold — which is the ODD reviewer's
  posture, not a lint rule's.

### Residual risk

Without a shared skeleton, six documents can drift into six genres. The
mitigation is the shared stance, which is a much weaker instrument than a
template, and the acceptance criterion has to be qualitative: each document
must let a reader without a code profile understand the stage, and must be
checkable by a reader who does not trust it.

## I4 — Ownership: the user is the owner (author's answer)

**Decision (2026-11-16).** The owner of each piece of content is the stage that
uses it. `download` documents everything about downloading in its own style;
`ingest` does the same for its own stage; `abm` already does it in the example
document. No common substrate, no ownership matrix, no `\input` fragments, no
seventh document.

**The mechanism that replaces the substrate.** Adjacency. The ABM document
describes what the ABM produces; the next stage's document describes what it
takes as input. Where the two meet, a discrepancy is visible by reading both —
that is where coherence is checked, and it needs no central artefact.

**What this changes downstream.**

- The four orphan obligations dissolve into the stage that consumes them:
  the manifest schema into `download`; the spatial frame into whichever stage
  first needs `(H, W)`; the habitat theory into `ingest` (which computes H) and
  `abm` (which applies S and K); parameter provenance into the stage whose
  process each constant drives.
- *Repetition is accepted and expected.* The author explicitly does not want
  repetition hunted down or standards imposed between stages. The duplication
  is the mechanism: the same fact written from two stages' points of view is
  where the drift shows up.
- *The documents are not a technical source of truth.* The author's framing:
  they are a conceptual and theoretical source of truth about the system — its
  processes, algorithms and reasoning — not a technical, invariant source of
  truth about the parts. So the value tables remain generated (D1), but the
  prose does not claim to freeze anything the code can change.

**Residual risk.** The adjacency mechanism only works if both sides of a seam
are written and kept. If `abm`'s document stops describing its outputs, the
seam goes dark and nothing else notices. Under the warnings-only regime there
is no presence rule to catch that, so it is a discipline the author carries, not
a mechanism.

## I5 — No generic template (author's answer)

**Decision (2026-11-16).** No shared template across stages. Each stage gets
the questions it needs; generalising produces a document that "explains the
theory in a generic way" instead of explaining the theory.

**What replaces it.** The stance (S1–S10), not a section list, plus one
methodological proposal the author can accept or reject: for each stage, a
**subagent investigates what that stage's questions should be**, in the same
way the ODD investigation above worked — read the code, read the review notes,
identify what questions the typology poses, and hand back a question set with
citations. This is not a template author writing a template to be filled in; it
is the ODD's own discipline (find the questions by reading the material)
applied per typology.

**The ODD's contribution, restated.** The example document was cited not for
its questions but for the *frame of thought* it imposes: the sections are the
visible result of a way of asking, and the way of asking is what generalises.

## I6 — Dropped as a decision (author's answer)

**Decision (2026-11-16).** Removed from the decision set. Two reasons.

1. No modification of the ABM and no generalisation to other systems is on the
   table, so the question cannot be answered in the way it was posed.
2. The framing was wrong on my side. The reference framework in
   `papers/spatial-analysis/MalariaEliminationWithSpatialDecisionSupportSystems.md`
   states its key elements verbatim as "(iii) application/intervention outcomes
   re-entered back into the SDSS as a cyclical input; and importantly (iv),
   expert knowledge, integrated throughout all stages of the SDSS process"
   (lines 304-307). That is the reference the project claims to instantiate, and
   the claim on the site is about the framework. Whether the current pipeline
   closes that loop is a question about the *system*, not about the
   documentation, and it is not the documentation layer's to answer.

So there is no documentation obligation here, and no decision to take. It is
recorded only so the point is not re-opened by a later reader of the brief.

---

# Round 2 — decisions (R1–R10, author, 2026-11-16)

## R1 — The stance is written down: option A, plus a lightweight skill

**Decision.** A written note, "how to write a conceptual document", lives in
`docs/concepts/` and states the stance (S1–S10 from
`concepts_brief.odd-method.md`), the devices, and the reasoning, with the ODD
as the worked example. Alongside it, a lightweight skill in the project's skill
directory (`.pi/skills/`) carries the operation, so that changing the question
template itself — when it must change — is a supported action rather than an
ad-hoc edit.

**Author's reasoning, recorded.** What varies most is the *content of the
answers* to the questions, not the questions themselves; the pipeline stages
will stay the same. So the stable thing is the question set, and the two
artefacts cover the two cases: the note for writing a document, the skill for
changing the questions.

**Implication.** The note and the skill are the only shared artefacts in the
layer. They are explicitly *not* a document template: the note fixes a stance
and a method, and the skill fixes an operation. Neither prescribes a section
list.

## R2 — Authoring loop: agent drafts, human reviews, notes become plans

**Decision.** Option B, and it is the loop already in use for the ODD. The
agent drafts the document in LaTeX; the human reviews it and writes
annotations; those annotations are then drafted into LaTeX for personal and
team use, not published; the published artefact is the document itself. The
annotations are the channel for sharing defects the reader finds, and the way
plans are generated from them.

**The loop this produces, end to end:**

1. Agent drafts the stage document (LaTeX), from that stage's question set.
2. Human reviews and annotates it.
3. Annotations become plans under `docs/plans/` — the existing mechanism, the
   one that produced the 13 `odd-fixes` packs from the ODD's ~85 review
   comments.
4. Applying a plan updates the code *and* the part of the document it
   invalidates.
5. Repeat.

**Implication for the review regime.** This is the same discipline that
produced the ODD's Appendix A and the eleven code defects it surfaced
(`odd-2010-malariasentinel.tex:1728-1855`). Under the warnings-only regime
(D3), the human annotation step is the main detection instrument, and the
annotations are the defect channel rather than something published.

## R3 — Code anchors stay inline, and every one of them is explained

**Decision.** The reader's route into the system is the website's landing page;
from there the documents are navigable and comprehensible. The ODD's practice
of referring to code variable names is kept — because it explains them well
enough that a reader new to the project can follow.

**Implication, stated as a requirement.** An anchor is acceptable only if it
is glossed: the document names the code symbol and explains what it is, in
prose, at the point of first use. The notation table's device of carrying the
code name in the symbol's parenthesis (`odd-2010-malariasentinel.tex:102-131`)
is the model, provided the explanation follows. An unexplained symbol is a
defect.

**Consequence for the document set.** The landing page carries the
non-technical introduction; the documents carry the system. Neither repeats the
other.

## R4 — The ODD is the base, and it changes as the packs land

**Decision.** Option A, with a forward rule. The clean version of the ODD —
the one without the review comments, currently in `.cache/odd-latex/` — is the
base for `docs/concepts/abm/`. It is a good representation of the system as it
stands today. From there, each application of a plan changes its part of the
ODD, progressively.

**What this replaces.** D4's status macros (`\asbuilt{}` / `\target{}`) and the
"Pending decisions" section are dropped: the document is simply kept current as
the packs land, rather than carrying per-section status metadata. That is a
simpler rule and it matches how the packs already work — a plan names the
section it invalidates and changes it.

**What it costs, stated plainly.** With no status markers and a warnings-only
review, a document's staleness relative to an *in-flight* plan is invisible to
the reviewer. The signal exists, but it lives in the plan tracker
(`docs/plans/in-process/`), not in the document. So the reviewer's inputs are:
the diff, the affected document, and the in-process plans.

**What this means for D7.** The ODD moves out of `.cache/` into
`docs/concepts/abm/` as the base, and the annotated review copy stays out of
the published tree — it is personal and team material (R2), whose content
already lives in the plans it produced.

## R5 — "Done" is a per-stage checklist, not a shared template

**Decision.** Option B. Each stage gets a checklist derived from that stage's
own question set, and the checklist is what "done" means for that document.

**Implication.** The checklist is per stage, so it does not generalise the
document's structure; it only states, for that stage, what must be answered.
The risk the lenses named still applies in milder form: a checklist written by
the same agent that answers it is weak. Mitigation is R2's loop — the human
annotation step is what tests the checklist against reality.

## R6 — The documentation lives in its own page

**Decision.** Option B. A separate documentation page under `docs/`, linked
from the site's navigation, rather than a new section inside the existing
200 KB `index.html`.

**Implication.** The landing page keeps its current shape and its i18n
dictionary untouched; the new page carries its own ES/EN dictionaries. The
navigation entry is one link, added to the nav and the footer.

## R7 — Namespaced output directories for the generated reference

**Decision.** Option A. `docs/reference/cpp/` and `docs/reference/python/`, so
Doxygen's and pdoc's own `index.html` files and their `_`-prefixed
directories cannot collide under the legacy Pages build, and the site links
into each.

## R8 — `scoring` gets a full document

**Decision.** Option A. Its own conceptual document, covering what a score
measures, the composite's geometric mean, and the LLM verdict's non-gating
role.

**Implication.** Six documents, one per named stage, `scoring` among them. The
merging the author considered for later (folding `scoring` into the ABM
document once the repo is stable) is deferred, and would be a reconsideration
of I4 rather than a new decision.

## R9 — Six documents; `ingest`'s three sub-stages are three sections of one

**Decision.** Option A. Six documents, one per named stage. `ingest`'s three
sub-stages (`env`, `hosts`, `mobility` — three output directories:
`runs/ingest/`, `runs/hosts/`, `runs/mobility/`) are three sections inside the
`ingest` document.

**Implication.** The `download` document keeps its internal seam visible as a
section — the research on the ODD identified it as a real methodological
boundary: the AOI reduction happens after areal-fraction aggregation, so a
native-resolution count is never produced. That seam is a section in
`download`, not a separate document.

## R10 — Examples are described situations, not code snippets

**Decision.** Option B. The worked example in each document is a situation
described in prose — "a reader asks for the 2024 rainfall for the Ghana AOI;
what happens, in order?" — rather than a code snippet.

**Implication.** The examples double as the test of the document's
understandability without a code profile, which is one of the project's stated
goals. The code-level equivalents live in the generated technical reference
(I2), so nothing is lost and nothing is duplicated.
