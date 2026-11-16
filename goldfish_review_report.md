# Goldfish Annotated Review Report

**Target:** `docs/plans/in-process/per-stage-conceptual-documentation.md` (lines 456–1461)
**Status:** resolved — 2026-11-16. Every PROPOSE FIX below is applied to the
plan; the ESCALATE (R-B2) was decided by the author as option (b), and the
plan now carries the four stages it implies. The report is a temporary
artefact of the review phase and is deleted once the phase closes; the
findings it contains that still matter live in the plan itself.
**Resolution counts:** 25 applied (24 PROPOSE FIX + 1 ESCALATE resolved as
option (b)) · 0 contested · 0 escalated-outstanding · 0 declined.
**Reviewers:** `egm-implementation-readiness`, `egm-codebase-details`, `egm-style`
**Standard:** `.pi/egm/resources/document_standards/implementation-readiness-standard.md`
**Date:** 2026-11-16

Resolution of the 8 blockers, 17 majors and 21 nits raised by the three
reviewers. Findings are numbered `R-B#` (blockers), `R-M#` (majors), `R-N#`
(nits). One finding is **ESCALATE** (the author's decision, not mine to make);
the rest are `PROPOSE FIX` or `DECLINE`.

Summary: **1 ESCALATE · 24 PROPOSE FIX · 1 DECLINE group (nits, recorded not fixed) ·
2 CONTEST-group items folded into a fix** (see R-M14 and R-N13).

---

## ESCALATE — needs the author's knowledge, not only approval

### R-B2 — The plan produces two of the six documents; the Goal says six
*Affected Scope:* `## Goals` (line ~312) · `## Sequencing` (lines 553–574) ·
files 25–26 (lines 1083–1110) · files 40–48 (lines 1312–1330)
*Description:* The stage table schedules only the ODD (Stage 1) and the
`download` pilot (Stage 5). No stage, file entry, exit condition or
verification item exists for the `ingest`, `scoring`, `training` and
`prediction` documents. Consequences: the Goal ("Publish six conceptual
documents") is unreachable through this plan; file 27 would publish links to
four PDFs that are never built; and the spec-retirement rule ("each spec is
deleted in the same commit that lands its conceptual equivalent") never fires
for those four stages, so their specs cannot be retired inside this plan.
*Rationale:* The plan's own architecture (Component 1) and Goals assume six.
*AI Suggestion:* **ESCALATE**
*Justification:* The critique is accurate; the remedy is an authorial scope
decision that no file in the repository answers. Two coherent resolutions:
**(a)** this plan produces `abm` and `download` only, the Goal is restated to
match, and the other four documents (and their specs) get their own plan;
**(b)** this plan grows four more stages, one per remaining stage, which
roughly doubles its length and its authoring cost. I will not pick between
them: option (a) changes the stated ambition, option (b) changes the plan's
size, and both are the author's call.
*Proposed Edit:* none until the author chooses. Under (a): the Goal becomes
"Publish two conceptual documents (`abm`, `download`) as the layer's first
two; the remaining four stages follow the same recipe in their own plan", and
the spec-retirement entries gain "for the four stages whose document is not
produced by this plan, the spec is retired by that plan, not by this one".

---

## Blockers

### R-B1 — Stage 6's exit condition requires a Stage 7 artefact
*Affected Scope:* `## Sequencing`, Stage 6 row (line 569)
*Description:* Stage 6's exit condition is "a reader reaches **both** in ES and
EN", where "both" is the PDF and the Technical reference. The Technical
reference is generated in Stage 7, and file 27 defers it ("the stance note, and
*later* the technical reference"). The plan's preamble claims each stage's exit
condition is checkable before the next begins; this one is not.
*Rationale:* The implementer must reorder stages, weaken the condition, or skip
the check; the plan decides none of these.
*AI Suggestion:* **PROPOSE FIX**
*Justification:* Unambiguous defect; the fix is the obvious one.
*Proposed Edit:* Location — `## Sequencing`, Stage 6 row, exit condition.
Change — "a reader reaches the PDF from the site in ES and EN (the Technical
reference is verified at Stage 7)".

### R-B3 — `git rm -r --cached data` also removes `data/README.md`
*Affected Scope:* file 38 (lines ~1283–1293) · `## Sequencing`, Stage 9 row
*Description:* The plan states that after the operation "git ls-files data/
shows only `data/README.md`". The pathspec `data` covers `data/README.md`, so
the only tracked file under `data/` leaves the index — and it is the file
file 39 depends on.
*Rationale:* The exit condition as written cannot hold.
*AI Suggestion:* **PROPOSE FIX**
*Justification:* Mechanical and unambiguous.
*Proposed Edit:* Location — file 38 "Proposed Changes" and the Stage 9 exit
condition. Change — the command becomes two steps, `git rm -r --cached --
data` followed by `git add -- data/README.md`, with the rationale noting that
the pathspec covers the README and that it must be re-added.

### R-B4 — the `.gitignore` rule as prescribed cannot re-include `data/README.md`
*Affected Scope:* file 37 (lines ~1270–1281)
*Description:* "one blanket `data/` rule plus a `!data/README.md` negation" does
not work: git does not descend into an excluded directory, so a negation for a
file inside an excluded directory is inert. The working form is `data/*` plus
the negation. The entry also mis-describes the current rules as "the `data/**`
globs": `.gitignore` has `data/**/*.txt` and `data/**/*.zip` (lines 10–11),
`data/pasteur_anopheles.zip` and `data/occurrence.txt` (12–13), `data/ghana/`
(20) and `data/accra-coastal-test/` (22).
*Rationale:* The plan's only protected-file instruction would not do what it
says.
*AI Suggestion:* **PROPOSE FIX**
*Justification:* Mechanical and unambiguous.
*Proposed Edit:* Location — file 37 "Proposed Changes". Change — prescribe
`data/*` + `!data/README.md` (with `data/**` if nested paths must be covered),
enumerate the six current rules with their line numbers, and note that the
negation is inert under a blanket `data/` rule.

### R-B5 — Stage 7's exit condition requires the flag/file contract the plan leaves undecided
*Affected Scope:* `## Sequencing`, Stage 7 row (line 570) · file 32 (lines
~1188–1199) · `## Verification Plan`, Stage 7 (lines ~1355–1360)
*Description:* I2-B is explicitly undecided in Open Questions, in Component 7
and in file 32 ("if built — see Open Questions; the script stubs it either
way"), while Stage 7's exit condition and the Verification Plan both require
the contract to exist. The verification additionally says "every CLI flag from
`_introspect_flags`", but that method scrapes `--help` from the **compiled C++
ABM binary**; the `malariasim` Typer CLI is not covered by it.
*Rationale:* An implementer can satisfy or fail Stage 7 depending on which
copy of the plan they read.
*AI Suggestion:* **PROPOSE FIX**
*Justification:* The scope of I2-B was decided by the author (not decided) — the
defect is that the plan contradicts itself, not that the decision was wrong.
*Proposed Edit:* Location — Stage 7 exit condition, file 32, Verification Plan
Stage 7. Change — make the exit conditional on I2-B and scope the flag list to
the compiled ABM binary, stating that the `malariasim` CLI is out of that
scope.

### R-B6 — the decision labels R1–R10, I5, F7 are used as requirements but never defined
*Affected Scope:* files 13–19, 24–27, 29, 32, 33, 40–48 · `### Decisions that
shape the architecture` (line 578) · Alternative M (line 806)
*Description:* ~15 usages of labels that lived in the deleted RFC brief:
"(R1)", "I5 — no generic template", "every code symbol glossed at first use
(R3)", "Internal seam kept visible as a section (R9)", "examples are described
situations, not code snippets (R10)", "the plan tracker", "decision I1-A",
"I2-A", "I2-B", "structural F7", "(R4)". The plan defines only D1–D9 and
S1–S10. An implementer cannot resolve "R9", "I5" or "F7".
*Rationale:* The plan's own EGM rule ("the draft is the deliverable … must be
self-contained") is violated by labels that only existed in a document that no
longer exists.
*AI Suggestion:* **PROPOSE FIX**
*Justification:* Each usage is followed by the requirement it labels, so the
labels are redundant — deleting them removes the dangling reference without
losing information. I1-A, I2-A and I2-B are different: they name *decisions*
that still exist in substance (PDF topology, reference generation, the open
flag-contract generator) and must be expanded inline, not deleted.
*Proposed Edit:* Locations — files 13–19, 25, 26, 27, 29, 30, 31, 32, 40–48;
`### Decisions that shape the architecture`; Alternative M. Change — remove the
`(R1)`…`(R10)`, `I5` and `F7` parentheticals; expand the surviving I-labels
inline ("decision I1-A: CI compiles the PDF and commits it back to the branch";
"I2-A: Doxygen plus pdoc generation"; "I2-B: the flag-and-file contract
generator — not decided, see Open Questions"); add one line to the decisions
section recording that the brief's round-2 labels are historical and are not
carried into this plan; and resolve D4's "the plan tracker" to
`docs/plans/in-process/`.

### R-B7 — the headline build failure does not happen where the plan says, and cannot be demonstrated at Stage 4
*Affected Scope:* Component 4 (lines ~505–512) · `## Goals` (line ~317) ·
`## Non-Goals` (line ~342) · `## Verification Plan`, Stage 4 (lines ~1343–1348)
*Description:* Two defects. (a) At Stage 4 no document `\input`s the generated
fragments — the only `.tex` files are the unmodified ODD and the ODD template —
so a renamed key cannot surface as an undefined control sequence; `latexmk`
will not fail. (b) In this codebase the pydantic validator fires first:
`mal_core/config_validation.py` is documented as "No defaults. Every key is
required; a missing key is an error. `extra="forbid"` at every level", so
renaming a key makes the generator abort with a `ConfigError` before any
`.tex` is emitted. The failure is a schema error, not a TeX error.
*Rationale:* D1's claim that this is "the only automatic failure in the whole
design" misdescribes the actual failure mode, and the plan's demonstration of
it is not executable where it is placed.
*AI Suggestion:* **PROPOSE FIX**
*Justification:* Both facts are verifiable in the repository (the validator's
docstring; the absence of any `\input` before Stage 5). The fix keeps the
design's guarantee and states it accurately instead of dropping it.
*Proposed Edit:* Locations — Component 4, the Goals bullet, the Non-Goals
bullet, Verification Plan Stage 4. Change — state the two failure modes
precisely (schema error at validation for a schema-checked key; undefined
control sequence at LaTeX for a key the schema tolerates and that a document
actually uses) and move the demonstration to the first stage where a document
uses a generated macro, with the YAML rename shown as the validation failure
and a deleted macro as the LaTeX failure.

### R-B8 — Stage 8's model, secret, corpus, criterion and threshold are all undefined
*Affected Scope:* `## Sequencing`, Stage 8 row (line 571) · file 34 (lines
~1208–1234) · `## Verification Plan`, Stage 8 (lines ~1361–1366) ·
`## Open Questions` (lines ~438–441)
*Description:* Open Questions concede that "the model, a token budget per pull
request and a place to run" are "not set", yet Stage 8 has an exit condition
and a verification step. Missing: model id, secret name, the corpus, what
counts as a false positive, and a threshold. File 34 also keeps gate
vocabulary ("Secret-absence resolves as `neutral`, never `failure`") that D3
abolished, and the corpus assumes "20 PRs of history" in a repository that has
no `.github/` directory.
*Rationale:* The implementer would have to design the whole reviewer.
*AI Suggestion:* **PROPOSE FIX**
*Justification:* The mechanism can be decided from the repository (the
project's LLM path already uses `OPENROUTER_KEY`, per `scoring/llm_scorer.py`),
and the corpus can be made conditional on what history exists. What the plan
must not do is invent a pass/fail threshold for the reviewer: under D3 the
number informs the author's decision to rely on it, and the plan says so —
that is a decision stated, not a decision left open.
*Proposed Edit:* Locations — Stage 8 row, file 34, Verification Plan Stage 8,
Open Questions. Change — name the secret and the repository variable the
workflow reads, make the corpus "the last 20 merges on `main`, or all of them
if fewer exist", define the false-positive criterion (a finding the author
confirms does not correspond to a real incoherence), state that the stage
closes when the measured rate is written down (no threshold is set by design),
and delete the `neutral`/`failure` vocabulary.

---

## Majors

### R-M1 — three file-number cross-references do not resolve
*Affected Scope:* file 22 ("Output directory of file 23") · file 32 ("Runs
Doxygen with file 33") · file 30 ("Same as file 31")
*Description:* The producer of `docs/concepts/generated/` is file 21, not 23;
the Doxyfile is file 31, not 33; and file 30's "same as" points at the
comment-polish entry 29.
*AI Suggestion:* **PROPOSE FIX** — three reference corrections.

### R-M2 — deleting the specs leaves dangling citations in four files, so Stage 0's exit condition cannot hold
*Affected Scope:* file 1 (`docs/README.md`) · file 2 (`AGENTS.md`) ·
files 5–9 (headers) · file 39 (`data/README.md`) · `## Verification Plan`,
Stage 0
*Description:* `docs/README.md` still calls `docs/specs/abm/spec.md` "the
single source of truth for engine data contracts"; `AGENTS.md`'s "How to
build, test, run" block still points at the deleted
`mal-core/src/mal_core/abm/tests/calibration` harness and at
`scorers/composite.py`, which file 2(a) does not touch; and
`mal-core/src/mal_core/abm/src/output_contract.cpp` cites
`docs/specs/abm/spec.md` twice ("The COG profile mirrors the output contract
spec"; "the keys are emitted in the order listed in `docs/specs/abm/spec.md`"),
which Stage 0 does not cover.
*Rationale:* Stage 0's exit condition is "no stale claim remains in those
files"; the prescribed edits cannot deliver it.
*AI Suggestion:* **PROPOSE FIX** — extend Stage 0's scope to those claims and
to `output_contract.cpp`, and state in file 1 that the "single source of
truth" sentence is replaced by a pointer to the conceptual layer.

### R-M3 — the `AGENTS.md` untrusted-documents note already exists
*Affected Scope:* file 2(c) (lines ~862–868) · `## Sequencing`, Stage 0 row
*Description:* `AGENTS.md` already carries an "Untrusted documents" section
stating that `docs/specs/*` is not authoritative and pending deletion. File
2(c) lists it as outstanding work and Stage 0's exit condition depends on it.
*AI Suggestion:* **PROPOSE FIX** — mark 2(c) as already satisfied (verify, do
not add), and drop the clause from the exit condition.

### R-M4 — `data/` is a protected path and the plan mis-states the protected set
*Affected Scope:* preamble of `## Detailed Implementation` (lines ~838–842) ·
file 39
*Description:* The preamble says "Two of these files are protected … `AGENTS.md`
and `.gitignore`"; `AGENTS.md`'s protected table lists three (including
`data/`), and file 39 edits `data/README.md` without flagging it.
*AI Suggestion:* **PROPOSE FIX** — name the three protected paths and flag
file 39.

### R-M5 — the prescribed licence sentence contradicts the repository's licence record
*Affected Scope:* file 39
*Description:* The plan asks for "ODbL share-alike on `host_static.nc`,
`mobility_*.csr`, wildlife proxy; CC BY-NC 4.0 on `guf/` and `colombia_vl/`".
The current `data/README.md` classifies `env / habitat / host_static /
mobility_*` as *derived, inherit compound — see `docs/licenses.md` §3* and
`wildlife_host_proxy` as "CC BY 4.0 + ODbL (via Overture)"; the machine
authority is `mal_commonlib.data.licenses.KNOWN_LICENSES`.
*Rationale:* The implementer would write a licence claim that contradicts the
code.
*AI Suggestion:* **PROPOSE FIX** — file 39 adds the archive path, the
re-download path and the not-regenerated list; it states no new licence claim
and points at `docs/licenses.md` §3 and `KNOWN_LICENSES`.

### R-M6 — "the manifest is rebuilt by the next `download`" is only partly true
*Affected Scope:* `## Goals` (last bullet) · D8 · Stage 9 header · file 39 ·
Alternative N · `## Verification Plan`, Stage 9
*Description:* Ingest-derived products (`host_static`, `mobility_*`, the habitat
gpkg, the env NC) are registered by `ingest/_shared.py::register_dataset`, not
by the downloader registry; and auth-gated datasets are **skipped**, not
failed (`runner.py::_check_auth`: CDS `~/.cdsapirc`, `EARTHDATA_TOKEN`, Earth
Engine credentials), in which path `update_dataset` is never called and the
manifest stays partial.
*Rationale:* Stage 9's exit condition and the clean-room check depend on the
claim.
*AI Suggestion:* **PROPOSE FIX** — one canonical sentence, cross-referenced
from the five places: download rebuilds the upstream half of the manifest from
the registry (datasets whose credentials are absent are skipped, not failed);
`ingest` re-registers the derived products; the clean-room check therefore
requires credentials or proves only the upstream half.

### R-M7 — `.gitignore` still advertises two scripts that do not exist
*Affected Scope:* file 37
*Description:* `.gitignore:8` says the heavy datasets are "re-downloadable via
`scripts/restore_data.py`" and `:19` mentions `scripts/build_2year_nc.py`;
there is no `scripts/` directory in the repository. D8 decides "no restore
script", and Stage 0 does not touch `.gitignore`.
*Rationale:* The plan's own mechanical signal 6 (named paths vs the tree)
would report it.
*AI Suggestion:* **PROPOSE FIX** — file 37 corrects both comments in the same
edit (it already rewrites the `data/` rules).

### R-M8 — the `index.html` truth pass has no replacement copy and would miss the live dictionary
*Affected Scope:* file 28 · `## Verification Plan`, Stage 6
*Description:* The file's `setLang()` overwrites the DOM from the `T.es`/`T.en`
dictionary at runtime, so editing only the inline HTML leaves the false text
live in both languages. The three claims have no replacement copy ("14
evaluadores" — 13 + 6 = 19, not 14; "agents/K_MAX"; "9.466 celdas" — 551 ×
779 = 429,229), the "PR gate" claim inside the same sentence is false under
D3, and a fourth stale claim is not listed at all: the AOI option "Mozambique
(Nacional predefinido)", although `aois.yaml` defines only `ghana` and
`accra-coastal-test`.
*Rationale:* The verification ("the three stale claims in `index.html` are
gone") is satisfiable while the rendered site still shows them.
*AI Suggestion:* **PROPOSE FIX** — give the exact replacement copy for each
claim, require the dictionary edits, add the Mozambique claim, and tighten the
verification to check the rendered page in both languages.

### R-M9 — the generator would re-implement the flat key view the repository already provides
*Affected Scope:* file 21
*Description:* `mal_core.habitat.config.dump_raw()` already produces the flat
dotted-key view of `model_constants.yaml` (`contracts.env_nc`,
`geodesy.metres_per_deg_lat`, …), with a C++ twin in `abm/src/config_dump.cpp`.
Two documented deviations matter for a documentation generator: it omits the
py-only `wildlife` section (to keep the py⇄C++ parity contract) and it
reshapes the species rows (weights as a list in canonical habitat order).
*AI Suggestion:* **PROPOSE FIX** — the generator calls the validated loader
(`load_config()` → `validate_model_config()`) and walks the config, rather
than parsing the YAML a second time; `dump_raw()` is named as the parity
reference, and the entry states the `wildlife` inclusion rule explicitly.

### R-M10 — `contracts.yaml` duplicates contract versions and can drift
*Affected Scope:* file 20 · file 21
*Description:* `model_constants.yaml` already holds `contracts.env_nc: "3.0"`
and `contracts.cogs_state: "4.0"`, and D2 gives the *generated* table
authority — but the generator reads both files, so a disagreement has no
defined winner. Nothing keeps the band names and sidecar keys in sync with
the C++ headers, which Stage 0 and Stage 7 both edit.
*AI Suggestion:* **PROPOSE FIX** — contract versions are not duplicated in
`contracts.yaml` (they come from `model_constants.yaml:contracts.*`), and the
generator cross-checks the band names and sidecar keys against the headers it
parses, failing on a mismatch. No new file entry is needed.

### R-M11 — the generated table asks for metadata with no defined source
*Affected Scope:* file 21
*Description:* The parameter tables must carry "name, meaning, unit, value,
provenance tier". `model_constants.yaml` carries units in a documented
convention (its header states "Unidades entre [ ]", and every parameter's
trailing comment is `# [mm]`, `# [días]`, `# [índice]`), but there is no
provenance convention, and the pydantic validator carries no commentary.
*AI Suggestion:* **PROPOSE FIX** — the generated table carries name, value and
unit (read from the existing `# [...]` convention, which the entry defines as
the contract); meaning and provenance tier are prose in the document, not
generated values. This keeps D1 intact instead of adding a second
hand-maintained source.

### R-M12 — the Doxyfile would publish ~39 headers nobody polished
*Affected Scope:* file 31 · file 29
*Description:* `INPUT = mal-core/src/mal_core/abm/include/`, `RECURSIVE = YES`,
`EXTRACT_ALL = YES` over ~45 headers, while file 29 polishes six and warns
that "a generated document from current comments would be structurally
complete and semantically false". The plan's own Analysis says several
headers still state the retired two-band / `k_max` contract. The exclusions
named (`tests/`) are not under `INPUT`, and `font8x8_basic.hpp` lives inside
`third_party/`, so it is excluded twice.
*AI Suggestion:* **PROPOSE FIX** — narrow `INPUT` to the six contract-defining
headers, `RECURSIVE = NO`, and fix the exclusion patterns.

### R-M13 — the build script would compile the template and the generated fragments
*Affected Scope:* file 23
*Description:* "latexmk -pdf over every `.tex` under `docs/concepts/`" includes
`odd-2010-template.tex` (the question template, file 11) and the fragments in
`docs/concepts/generated/`.
*AI Suggestion:* **PROPOSE FIX** — specify the build set explicitly.

### R-M14 — the published PDF path is undecided and does not follow from the source name
*Affected Scope:* Component 5 · file 24 · file 27
*Description:* Component 5 says "at a stable path **such as**
`docs/concepts/abm/abm.pdf`" while the source is `odd-2010-malariasentinel.tex`,
whose `latexmk` output is `odd-2010-malariasentinel.pdf`; no rename or
`--jobname` step is specified, and files 24 and 27 assume `<phase>.pdf`.
*AI Suggestion:* **PROPOSE FIX** — fix the path and add the rename step.
*Note:* the "such as" hedge is the defect; the path choice itself
(`docs/concepts/<phase>/<phase>.pdf`) is already fixed by files 24 and 27, so
this is a consistency fix, not a new decision.

### R-M15 — an open question contradicts the sequencing table
*Affected Scope:* `## Open Questions` (lines ~449–451)
*Description:* "Whether `data/` untracking lands before or after the first
document exists … is not decided" contradicts a table that fixes Stage 9 last,
and Stage 9 is the destructive git operation.
*AI Suggestion:* **PROPOSE FIX** — delete the question; the table is the single
source of order.

### R-M16 — the specs' runnable checks are discarded without migration
*Affected Scope:* files 40–48
*Description:* `docs/specs/abm/spec.md` contains runnable assertions
(`assert cv.startswith('2.')`, `assert len(dims) == 13 and len(gates) == 6`,
a `H = W = 128` grep) that the reviewer could reuse; the plan deletes the
files without saying where those checks go.
*AI Suggestion:* **PROPOSE FIX** — the entry requires each spec's runnable
assertions to be migrated (into the reviewer's mechanical signals or into
`tests/`) or explicitly recorded as dropped.

### R-M17 — `commonlib/spec.md` has no decided destination
*Affected Scope:* files 40–48
*Description:* "spatial frame lands in the stage that first needs `(H,W)`"
never says which stage that is, and `data`/`commonlib` are not pipeline stages,
so the "one per stage" framing does not fit them.
*AI Suggestion:* **PROPOSE FIX** — name the destinations: the spatial frame →
`ingest` (the first stage that needs `(H,W)`); the AOI product and manifest
schema → `download`.

---

## Nits — recorded, and the cheap ones fixed with the majors above

**Fixed as part of the above:** the `output_contract.hpp` line reference
(`:71-73` → `:75-76`); the download citations that point at `def` lines instead
of the registry selection and the `update_dataset` call site; "not all 101
files" (a number that matches nothing — the tree holds 46 headers, 33
sources, 31 tests); the entry count ("47 numbered file entries" for a range
that covers nine files); "the four known-false statements" (four *files*
carrying more than four statements, and a fifth false statement in
`llm_scorer.py` — "invoked directly via `langchain_openai`", while the code
posts to `LLM_BASE_URL` with `requests`); `scoring/config.py` "uses
`D16_suitability_auc`" (the name appears only in a docstring example; the
runtime name is `D16_detection_coverage`); entry 5–9's "the open question is
settled here" (the audit is proposed work); Stage 1's "verified 2026-11-16"
(attached to the source build, not the tracked copy); the `k_max` grep in the
Verification Plan (it would fail on the legitimate retirement notes in
`wire.hpp`); the Stage 8 comment-only check (it asserts the absence of a
mechanism, so it can never fail); "the four files `download` never regenerates"
(four *kinds* of material, and the map renderings come from the explorer);
the missing `.gitignore` rules for LaTeX build artefacts; the drafting skill's
missing YAML frontmatter; the missing `uv run` in the verification commands;
the unmentioned `tools/audit_comment_constants.py` and
`tools/check_no_constants.sh` (they already implement signal 1 for comments);
`tools/` sitting outside `tools/format.sh`'s lint scope; the Stage 6 page
linking four PDFs that do not exist; "the reviewer" (LLM reviewer vs human
annotator); "the template" (the `.tex` question set vs `questions.md`); file
14's self-contradiction (a drafting skill as "the supported action for
changing the question set"); "the generated tables" (two artefacts); the
archive checksum vs "no offline-copy inventory"; the Stage 9 exit condition's
missing credential precondition.

**DECLINE (recorded, not fixed):** the numbering mismatch between the entry
range 40–47 and the nine files it covers is resolved by the renumbering
proposed in R-M17's edit rather than by a separate change; the remaining
phrasing nits have no cost worth an edit and would only add churn to the plan.

---

## Traceability

| ID | readiness | codebase-details | style |
|---|---|---|---|
| R-B1 | #1 | — | #B4 |
| R-B2 | #2 | — | — |
| R-B3 | #3 | — | #B3 |
| R-B4 | #4 | — | #B3, #N16 |
| R-B5 | #5 | #15 | #B1 |
| R-B6 | #2 | #2 | #M4 |
| R-B7 | #7 | #1 | — |
| R-B8 | #6 | — | #M9, #M10 |
| R-M1 | — | #17 | #B2 |
| R-M2 | #10 | #7, #8, #9 | #M7, #N18 |
| R-M3 | #11 | — | #M6 |
| R-M4 | #14 | — | #B5 |
| R-M5 | #14 | #11 | — |
| R-M6 | #15 | #10 | #N10 |
| R-M7 | #16 | #12 | #N17 |
| R-M8 | #13 | #20 | #M8 |
| R-M9 | — | #3 | — |
| R-M10 | — | #4 | — |
| R-M11 | #8 | — | — |
| R-M12 | — | — | #M3 |
| R-M13 | #17 | — | #M11 |
| R-M14 | — | — | #M12 |
| R-M15 | — | — | #M13 |
| R-M16 | — | #14 | — |
| R-M17 | #21 | — | — |
