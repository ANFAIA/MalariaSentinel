# Implementation Readiness Report — per-stage conceptual documentation

**Target**: `docs/plans/in-process/per-stage-conceptual-documentation.md` (1,461 lines)
**Scope audited**: lines 456–1461 (`## Technical Plan (Architecture)` → end)
**Mode / Step**: REVIEW / Stage 9 (Implementation Readiness Test)
**Standard**: `.pi/egm/resources/document_standards/implementation-readiness-standard.md`
**Reviewers**: `egm-implementation-readiness`, `egm-codebase-details`, `egm-style` (spawned as parallel subagents, fresh context, read-only)
**Date**: 2026-11-16
**Status**: resolved — 2026-11-16. Every blocker and major below is fixed in
the plan; the nits are fixed where they were cheap and recorded where they
were not. The report is a temporary artefact of the review phase.
**Resolution counts**: 8 blockers fixed · 17 majors fixed · nits fixed with
the majors or recorded as declined (see `goldfish_review_report.md`).

| Severity | Count |
|---|---|
| 🔴 Blocker | 8 |
| 🟡 Major | 17 |
| 🟢 Nit | 21 (grouped in §4) |

---

## 1. Blockers — the plan cannot be executed as written

### B1 — Stage 6's exit condition requires a Stage 7 artefact
*Source: readiness #1, style #B4, style #N20*
The Stage 6 row requires "a reader reaches **both** in ES and EN" (the PDF and
the *Technical reference*). The technical reference is produced in Stage 7
(files 31–33), and file 27 itself defers it ("the stance note, and *later* the
technical reference"). The implementer must reorder stages, weaken the exit
condition, or skip the check — the plan decides none of these, while its own
preamble claims each stage's exit condition is checkable before the next begins.
*Fix:* drop "Technical reference" from the Stage 6 row and move that clause to
Stage 7's exit condition.

### B2 — Four of the six conceptual documents are never produced by any stage
*Source: readiness #2*
The stage table schedules only the ODD (Stage 1) and the `download` pilot
(Stage 5). There is no stage, file entry, exit condition or verification item
for `ingest`, `scoring`, `training` or `prediction`. Consequences inside the
plan: file 27 would publish links to four PDFs that are never built; the
spec-retirement entries require each spec to be deleted "in the same commit
that lands its conceptual equivalent" — a commit that never comes for those
four stages; and the Goal ("Publish six conceptual documents") is unreachable
through the plan as written.
*Fix:* either add stages for the four documents, or state explicitly that the
six-document goal is out of scope for this plan and that only `abm` and
`download` are produced by it.

### B3 — `git rm -r --cached data` also removes `data/README.md` from the index
*Source: readiness #3*
The plan asserts that after the operation "git ls-files data/ shows only
`data/README.md`". The pathspec `data` covers `data/README.md`, so the only
tracked file under `data/` leaves the index — and it is the file file 39
depends on. *Fix:* specify the correction explicitly (e.g. `git rm -r --cached
data ':!data/README.md'`, or `git rm --cached` followed by `git add
data/README.md`).

### B4 — the `.gitignore` rule as prescribed cannot re-include `data/README.md`
*Source: readiness #4, style #B3, style #N16*
"one blanket `data/` rule plus a `!data/README.md` negation" does not work: git
does not descend into an excluded directory, so a negation for a file inside an
excluded directory is inert. The working form is `data/*` (+ `!data/README.md`)
or `data/**` with the directory un-ignored. The rule only appears to work
because `data/README.md` is already tracked. The entry also mis-describes the
current rules as "the `data/**` globs": `.gitignore` has `data/**/*.txt`,
`data/**/*.zip` (lines 10–11), `data/pasteur_anopheles.zip`,
`data/occurrence.txt` (12–13), `data/ghana/` (20), `data/accra-coastal-test/`
(22).
*Fix:* prescribe the `data/*` + negation form and enumerate the current rules.

### B5 — Stage 7's exit condition requires the flag/file contract the plan leaves undecided
*Source: readiness #5, style #B1*
The Stage 7 exit says "the flag/file contract documented", and the Verification
Plan says "the flag/file contract page lists every CLI flag from
`_introspect_flags`" — but I2-B is explicitly undecided in Open Questions, in
Component 7 and in file 32 ("if built — see Open Questions; the script stubs it
either way"). *Fix:* make the exit condition conditional on I2-B, or drop I2-B
from the plan's scope.

### B6 — the decision labels R1–R10, I1-A/I1-B, I2-A/I2-B, I5, F7, R4 are used but never defined
*Source: readiness #2 (major), style #M4, codebase-details #2 (blocker)*
They appear ~15 times as requirements — "(R1)", "I5 — no generic template",
"every code symbol glossed at first use (R3)", "Internal seam kept visible as a
section (R9)", "examples are described situations, not code snippets (R10)",
"the plan tracker", "decision I1-A", "I2-A", "I2-B", "structural F7", "R4" —
but the plan defines only D1–D9 and S1–S10. The labels lived in the RFC brief,
which was deleted. The plan's own rule ("the draft is the deliverable … must be
self-contained") is violated: an implementer cannot resolve R3, R7, I5 or F7.
*Fix:* add a legend table mapping each label to its requirement, or replace the
labels with their text.

### B7 — Stage 4's key verification cannot execute at Stage 4, and its stated failure mode is wrong
*Source: readiness #7, codebase-details #1 (blocker)*
The plan's headline guarantee — "a renamed key becomes an undefined control
sequence and fails the LaTeX build" — has two problems. (a) At Stage 4 no
document `\input`s the generated fragments (the only `.tex` files are the
unmodified ODD and the ODD template), so a renamed key cannot surface as an
undefined control sequence; `latexmk` will not fail. (b) In this codebase the
pydantic validator (`mal_core/config_validation.py`, `extra="forbid"`,
"No defaults. Every key is required") fires **first**: the generator crashes
with a `ConfigError` before any `.tex` is emitted. The failure is a schema
error, not a TeX error.
*Fix:* state that the YAML-level rename fails at validation, define what the
LaTeX-level guarantee actually is (reachable only for keys the schema tolerates
and that a document actually uses), and move the demonstration to the first
stage where a document uses a generated macro.

### B8 — Stage 8 is a stage whose model, secret, cost and threshold are all undefined
*Source: readiness #6, style #M9, style #M10*
Open Questions concede that "the model, a token budget per pull request and a
place to run" are "not set", yet Stage 8 has an exit condition ("a first-pass
rate is known") and a verification step ("Run the reviewer over 20 historical
PRs"). Missing: model id, provider, secret name (the project's LLM path is
`OPENROUTER_KEY`, per `scoring/llm_scorer.py`), fork handling, a definition of
"false positive", a pass threshold, who decides to rely on the reviewer, and
whether 20 PRs of history exist (the repo has no `.github/` directory at all).
Entry 34 also retains gate vocabulary ("Secret-absence resolves as `neutral`,
never `failure`") that D3 abolished.
*Fix:* decide model/provider/secret/budget in file 34 (the step that writes the
workflow), define the false-positive criterion and the threshold, delete the
`neutral`/`failure` wording, and condition the "20 PRs" check on the history
that exists.

---

## 2. Majors

| ID | Finding | Source | Fix |
|---|---|---|---|
| M1 | **Cross-references to file numbers do not resolve** — entry 22 says "Output directory of file 23" (producer is 21); entry 32 says "Runs Doxygen with file 33" (the Doxyfile is 31); entry 30 says "Same as file 31" (meant 29). Artefacts of the recent renumbering. | style #B2, codebase #17 | fix the three references |
| M2 | **Dangling citations to the deleted specs are left behind** — `docs/README.md` still calls `docs/specs/abm/spec.md` "the single source of truth for engine data contracts"; `AGENTS.md`'s "How to build" block still points at `mal-core/src/mal_core/abm/tests/calibration` (deleted) and `scorers/composite.py`; `abm/src/output_contract.cpp` cites the abm spec twice; `data/README.md` cites `docs/specs/data/spec.md`. Stage 0's exit condition ("no stale claim remains in those files") cannot hold. | readiness #10, codebase #7/#8/#9, style #M7/#N18 | add these files and claims to Stage 0's scope |
| M3 | **The `AGENTS.md` untrusted-specs note already exists** (added when the EGM rule was written). Entry 2(c) lists it as outstanding work and Stage 0's exit condition depends on it. | readiness #11, style #M6 | mark 2(c) as satisfied, or state the delta |
| M4 | **`data/` is a protected path and the plan mis-states the protected set** — the preamble says "Two of these files are protected … `AGENTS.md` and `.gitignore`"; `AGENTS.md`'s protected table lists three (including `data/`), and file 39 edits `data/README.md` without flagging it. | readiness #14, style #B5 | name three protected paths; flag file 39 |
| M5 | **The prescribed licence statement misattributes ODbL** — the plan asks for "ODbL share-alike on `host_static.nc`, `mobility_*.csr`, wildlife proxy"; the current `data/README.md` classifies `env / habitat / host_static / mobility_*` as *derived, inherit compound — see `docs/licenses.md` §3*, and `wildlife_host_proxy` as "CC BY 4.0 + ODbL (via Overture)". The implementer would write a claim that contradicts `mal_commonlib.data.licenses.KNOWN_LICENSES`. | readiness #14, codebase #11 | point file 39 at `KNOWN_LICENSES` / `docs/licenses.md` instead of restating licences |
| M6 | **"The manifest is rebuilt by the next `download`" is only partly true** — ingest-derived products (`host_static`, `mobility_*`, habitat gpkg, env NC) are registered by `ingest/_shared.py::register_dataset`, not by the downloader registry; and auth-gated datasets are **skipped**, not failed (`runner.py::_check_auth`: CDS `~/.cdsapirc`, `EARTHDATA_TOKEN`, Earth Engine), in which path `update_dataset` is never called and the manifest stays partial. | codebase #10, readiness #15, style #N10 | restate the claim: download rebuilds the upstream half, ingest the derived half; state the credential precondition in Stage 9's verification |
| M7 | **`.gitignore` still advertises `scripts/restore_data.py`** (line 8) and `scripts/build_2year_nc.py` (line 19) — neither exists — while D8 explicitly decides "no restore script". `.gitignore` is not in Stage 0's scope and file 37 only rewrites the `data/` rules. | readiness #16, codebase #12, style #N17 | fix both comments in file 37 (or in Stage 0) |
| M8 | **The `index.html` truth pass is under-specified and its verification can pass while the site still lies** — the file's `setLang()` overwrites the DOM from the `T.es`/`T.en` dictionary at runtime, so editing inline HTML leaves the false text live in both languages; the "14 evaluadores" claim has no stated replacement (13 + 6 = 19 ≠ 14); "9.466 celdas" and "agentes/K_MAX" also lack replacement copy; and `docs/index.html` offers "Mozambique (Nacional predefinido)" although `aois.yaml` defines only `ghana` and `accra-coastal-test`. | readiness #13, style #M8, codebase #20 | give the exact replacement copy per claim, specify the dictionary edits, and add the Mozambique claim |
| M9 | **The generator reinvents existing machinery** — `mal_core.habitat.config.dump_raw()` already produces the flat dotted-key view of `model_constants.yaml` (`contracts.env_nc`, `geodesy.metres_per_deg_lat`, …), with a C++ twin in `abm/src/config_dump.cpp`; the prescribed `\mskey{<dotted.key>}` expansion is exactly its output. Note it deliberately omits the `wildlife` (py-only) section, which needs an explicit rule. | codebase #3 | specify reuse of `dump_raw()` + `validate_model_config`; state the py-only rule |
| M10 | **`contracts.yaml` creates a second source of truth with no precedence rule** — `model_constants.yaml` already holds `contracts.env_nc: "3.0"` / `contracts.cogs_state: "4.0"`, and the plan says contracts.yaml's content is "sourced from" the code; but D2 gives the *generated* table authority, and the generator reads both files, so a disagreement has no defined winner. Nothing keeps it in sync (Stage 0 edits `wire.hpp`, Stage 7 re-polishes it). | codebase #4 | drop contract versions from contracts.yaml, or name the winner |
| M11 | **The generator is asked for metadata with no defined source** — parameter tables must carry "name, meaning, unit, value, provenance tier", but `model_constants.yaml` carries units and provenance only as trailing `#` comments, the pydantic validator carries no commentary, and `contracts.yaml` is defined as contract metadata only. The implementer must invent comment scraping or a new hand-maintained file — the class of drift D1 exists to remove. | readiness #8 | decide the mechanism in file 21 |
| M12 | **The Doxyfile publishes headers the plan never polished** — `INPUT = …/abm/include/`, `RECURSIVE = YES`, `EXTRACT_ALL = YES` over ~45 headers, while entry 29 polishes only six; the plan's own Analysis warns that "several headers still state the retired two-band / `k_max` contract". | style #M3 | narrow `INPUT` to the six polished headers, or extend the polish scope |
| M13 | **The build script would compile non-documents** — "latexmk -pdf over every `.tex` under `docs/concepts/`" includes `odd-2010-template.tex` and the generated fragments in `docs/concepts/generated/`. | readiness #17, style #M11 | specify the build set explicitly |
| M14 | **The published PDF path is undecided and inconsistent** — the plan says "at a stable path *such as* `docs/concepts/abm/abm.pdf`" while the source is `odd-2010-malariasentinel.tex`, whose `latexmk` output is `odd-2010-malariasentinel.pdf`; no rename or `--jobname` step is specified. | style #M12 | fix the path and add the rename step |
| M15 | **Open Questions contradict the sequencing table** — the open question "whether `data/` untracking lands before or after the first document exists … is not decided" contradicts a table that fixes Stage 9 as last. | style #M13 | delete or re-scope the question |
| M16 | **Executable checks inside the specs are discarded without migration** — e.g. `assert cv.startswith('2.')`, `assert len(dims) == 13 and len(gates) == 6`, the `H = W = 128` grep; the reviewer's signal list only partially overlaps. | codebase #14 | state which checks migrate into the reviewer |
| M17 | **`commonlib/spec.md` has no decided destination** — "spatial frame lands in the stage that first needs `(H,W)`" never says which stage that is, and `data`/`commonlib` are not pipeline stages, so the "one per stage" framing does not fit them. | readiness #21 | name the destination stage, or reframe the entry |

---

## 3. Facts the reviewers verified as TRUE (recorded so they are not re-litigated)

`STATE_BAND_NAMES` = {`adult_patch_count`, `adult_cell_count`} vs the stale two-band
claim in `output_contract.hpp:3-5`; the `k_max` sidecar claim; `docs/specs/abm/spec.md:182`
`assert cv.startswith('2.')`; `wire.hpp:87` citing `docs/abm-status.md:79`;
`model_constants.yaml` `env_nc: "3.0"` / `cogs_state: "4.0"`; `registry.py` = 13
composite + 6 gates; `Scorer.min_score`/`hard_floor` as class attributes;
`llm_scorer.py` "10 deterministic scorers (D1..D10)"; `habitat/constants.py` raising
for every attribute; `commonlib/config.py` `SimParams.r_of()` → undefined
`temp_suitability` and its `DESIGN.md` citation; Ghana bbox `[-3.5,4.5,1.5,11.5]`
@1000 m ⇒ 551 × 779 = 429,229; `docs/index.html` "14 evaluadores" / "9.466 celdas" /
"agentes/K_MAX"; `docs/README.md`'s six absent paths; `.gitignore:20` = `data/ghana/`,
`.gitignore:53` = `.cache/`; the ODD sources exist in `.cache/odd-latex/`;
`runner.py:69` = `def run_download(`, `manifest.py:116` = `def update_dataset(`;
`tools/run_all_tests.sh` swallows failures; no `.github/` directory; no
`scripts/restore_data.py`; `docs/specs/` holds exactly 9 files (8 specs + `_template.md`);
`docs/plans/in-process/odd-fixes/` holds the 13 packs.

---

## 4. Nits (grouped)

**Cross-references and numbers.** Entry 22's "file 23" → 21; entry 32's "file 33" →
31; entry 30's "file 31" → 29 (in M1). `output_contract.hpp:71-73` → the cited text
is at 75–76. The download citations point at `def` lines, not the selection line
(≈91–95) and the `update_dataset` call site. The stage-0 entry says "not all 101
files" — the ABM tree holds 46 headers, 33 sources, 31 tests; 101 matches none of
them. "47 numbered file entries" is asserted while the range 40–47 covers nine files
(8 specs + `_template.md`). "Four known-false statements" vs four *files* carrying
more than four statements. "Four files `download` never regenerates" is four *kinds*,
~14 files, and the map renderings are regenerated by the explorer, not by `download`.

**Unverifiable or misplaced claims.** Entry 5–9 asserts the header audit "is settled
here" — the audit is proposed work, and the same question is still open in Open
Questions. Stage 1's exit carries "verified 2026-11-16", but what was verified was
the *untracked source* build, not the tracked copy. Entry 30's claim that
`scoring/config.py` "uses `D16_suitability_auc`" overstates it: the string appears
only in a docstring example; the real name is `D16_detection_coverage`. `llm_scorer.py`
carries a *fifth* false statement ("invoked directly via `langchain_openai`"; the
code uses `requests.post`). The "k_max" grep in the Verification Plan would fail on
the legitimate retirement notes in `wire.hpp`. The Stage 8 comment-only check asserts
the absence of a mechanism, so it can never fail. "20 PRs of history" is unverified.
"The manifest is rebuilt" is stated four times in four different scopes. "The plan
tracker" (D4) is an unresolved pointer; Alternative M resolves it as
`docs/plans/in-process/`. "The reviewer" is ambiguous between the LLM reviewer and the
human annotator. "The template" covers two artefact kinds (`odd-2010-template.tex` vs
`questions.md`). Entry 14's sentence is self-contradictory (a drafting skill as "the
supported action for changing the question set"). "The generated tables" names two
artefacts. Stage 9's "no offline-copy inventory" reads as contradicting the archive's
sha256 file. The Stage 6 page would ship dead links to four PDFs.

**Missing small things.** No `.gitignore` rules for LaTeX build artefacts
(`.aux`, `.log`, `.fls`, `.fdb_latexmk`, `.out`, `.toc`) under `docs/concepts/` and
`docs/reference/`; Stage 4's `git diff --exit-code` check would be polluted by the
first local build. The drafting skill's YAML frontmatter is unspecified — every
existing skill in `.pi/skills/` has `name:`/`description:`; without it the skill may
not load. `tools/format.sh` covers the four packages only, so `tools/gen_concepts_values.py`
is outside the repo's own lint scope. `tools/audit_comment_constants.py` and
`tools/check_no_constants.sh` already implement the plan's signal 1 and the "no
hand-typed number" rule for comments; the plan never names them. The Stage 9
verification omits `uv run` (the repo always uses `uv run malariasim …`). The Doxyfile
excludes `tests/` which is not under `INPUT`, and double-excludes `font8x8_basic.hpp`
(which lives inside `third_party/`).

---

## 5. Traceability matrix

| Consolidated | readiness | codebase-details | style |
|---|---|---|---|
| B1 | #1 | — | #B4, #N20 |
| B2 | #2 | — | — |
| B3 | #3 | — | #B3 |
| B4 | #4 | — | #B3, #N16 |
| B5 | #5 | #15 | #B1 |
| B6 | #2 (major) | #2 | #M4 |
| B7 | #7 | #1 | — |
| B8 | #6 | — | #M9, #M10 |
| M1 | — | #17 | #B2 |
| M2 | #10 | #7, #8, #9 | #M7, #N18 |
| M3 | #11 | — | #M6 |
| M4 | #14 | — | #B5 |
| M5 | #14 | #11 | — |
| M6 | #15 | #10 | #N10 |
| M7 | #16 | #12 | #N17 |
| M8 | #13 | #20 | #M8 |
| M9 | — | #3 | — |
| M10 | — | #4 | — |
| M11 | #8 | — | — |
| M12 | — | — | #M3 |
| M13 | #17 | — | #M11 |
| M14 | — | — | #M12 |
| M15 | — | — | #M13 |
| M16 | — | #14 | — |
| M17 | #21 | — | — |

Raw findings not carried as separate items: readiness #16 (merged M7), #19 (nit),
#22 (nit), #23 (nit); codebase #5, #6, #13, #19, #22, #23 (nits); style #N1–N19
(nits, grouped in §4).

---

## 6. Recommendation

The plan's architecture and its non-EIP decisions hold up under review: the
reviewers confirmed the plan's claims about the codebase wherever they could be
checked, and the stage sequencing is coherent except for the two ordering
defects (B1, B8). The blockers cluster in three places: **the sequencing table and
its exit conditions** (B1, B2, B8), **Stage 9's git mechanics** (B3, B4, M5, M7),
and **the plan's self-containment** (B6, plus the label references in M1).

Fixing them is editing the plan, not implementing it: eight blockers and seventeen
majors are all inside `docs/plans/in-process/per-stage-conceptual-documentation.md`.

*This report is a temporary artefact of the EGM review; per the EGM rules it is
deleted when the phase ends. Its content that matters belongs in the plan or in the
git history.*
