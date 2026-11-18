# Plan: `papers/` as a reconstructible artefact

Status: **executed 2026-11-18 (steps 1–7); PR pending. Execution record in §13.**
Date: 2026-11-17. Branch: `docs/papers`. Author: david-fm.
Companions: none. This document is self-contained.

---

## 1. The problem

The repository versions 156 files under `papers/` (verified with
`git ls-files papers/`, 2026-11-17): full-text extracts of copyrighted articles,
curated summaries, project-authored syntheses, and internal research notes.
This causes three concrete failures:

- **Redistribution.** Extracted article text is committed. Some of it is
  under restrictive licences (`papers/REFERENCES.md`: 20 rows restricted, 2
  unverified: rows 71 and 104), and one open-licence file (BMJ Global Health 2020, CC BY-NC 4.0)
  holds an unreadable OCR extract.
- **Unverifiable citations.** `papers/REFERENCES.md` has 113 rows and a table
  broken at line 57 (a blank line splits it; the second half has no header).
  The header format of the 147 files that declare a DOI is not uniform.
  Seven DOIs are shared by two files each (e.g. `10.1371/journal.pcbi.1007446`,
  Wu 2020 ×2). No mechanism checks that a citation in a tracked document points
  at a real entry.
- **Unrebuildable corpus.** Nothing records how each PDF was obtained or what
  its checksum is, so the corpus cannot be recreated on another machine.

## 2. Overview

Move the corpus from "tracked files" to "tracked manifest plus a rebuild
tool":

1. `papers/manifest.json` (tracked, hand-authored) is the inventory: one entry
   per paper, with an identifier, a DOI when one exists, a status, and a
   checksum when the PDF was fetched.
2. A tool in `mal-core` (`mal_core/papers/`, exposed as `malariasim papers`)
   reads the manifest, downloads every obtainable PDF into its paper folder,
   runs docling on it, and writes `provenance.yaml` beside the output. Papers
   that cannot be obtained are written to the manifest as `pending_*` and the
   run continues.
3. Paper folders are gitignored. Only the manifest, the generated
   `REFERENCES.md`, the README, and the tracked class B documents are versioned.
4. A small set of assertions over tracked files replaces "the corpus is
   byte-identical" as the acceptance test.

Byte-reproducible docling output is not a goal. Docling output varies by device
and model version, so only identifiers and PDF checksums are contractual.

## 3. Goals and non-goals

**Goals**

- No copyrighted article text is versioned after the change. Text exists only
  in local, gitignored paper folders, generated on each user's machine.
- Every citation in a tracked document resolves to a manifest entry, a DOI, or
  an explicit "not obtained" record.
- The corpus is rebuildable with one command, using the manifest as the single
  source of truth.

**Non-goals**

- Byte-reproducible docling output.
- Rebuilding the ODD bibliography from the manifest. Deferred (§10).
- Rewriting the curated summaries of paywalled works. Deferred until the
  claims ledger covers their values (see §5 OPEN-1 and §6.4).
- Rewriting git history. Decided separately (§6.1, Q1), not part of this change.

## 4. Decisions

Taken by the author (recorded 2026-11-17):

| # | Decision |
|---|---|
| D1 | Extracted text comes from docling, not from curated summaries. |
| D2 | Unobtainable papers are recorded in a pending manifest; the tool reports and continues, it does not fail the run. |
| D3 | Automatic download where obtainable. The rest is left to each user through the manifest. |
| D4 | No paper material goes to GitHub. |
| D5 | Each paper lives in its own subfolder under its theme folder, with the PDF, the docling output, `images/` when referenced, and `provenance.yaml`. |
| D6 | `papers/REFERENCES.md` is generated from the manifest. Per-theme READMEs are not generated. |
| D7 | Secondary documents (class C, §6.3) are deleted only after a traceability pass produces a versioned ledger and re-points the live citations. |
| D8 | The tool lives in `mal-core` (the `malariasim` toolkit). Docling is a declared dependency, not a PATH dependency. |
| D9 | Git history rewrite (`git filter-repo`) is a separate user-level decision. Default: no. The legal cleanup stands without it. |
| D10 | ~~Non-OA curated summaries are kept until the ledger holds their values.~~ Superseded by D20. |
| D20 | All curated summaries of papers (the ~130 files with a DOI line, §5) are deleted. Nothing replaces them as a text source. |
| D21 | Citations point to the **paper** (DOI or manifest id, plus section, table, or figure), never to a Markdown file in the repository. Where a value is quoted, the quote is kept short (limit in §6.4). |
| D22 | Docling Markdown is a local working file. It is not a citation target and not a source of truth; the PDF checksum is the contractual artefact. |
| D11 | Layout: one subfolder per paper (`papers/<theme>/<slug>/`). Citations to paths are re-pointed to the folder in the same commit that moves the files. |
| D12 | `AGENTS.md:9` is edited (one line, to point at the manifest entry), as a separately approved change in step 4. |
| D13 | ~~Q3: the `## Full Text` blocks of the nine hybrids are removed; licence verification is not needed.~~ Superseded by D23. |
| D23 | The nine hybrid files are deleted entirely, summary and `## Full Text` alike, in step 4 (§9). Their papers stay in the manifest and are rebuilt locally like any class A paper. Licence values in `REFERENCES.md` are informational and gate nothing. |
| D24 | Tier 1 claims that cite one of the ~40 unobtainable papers are recorded `unverified-paywalled`. They do not block anything, and this plan does not verify them. |
| D25 | The two Gemini-generated texts (`synthesis-gemini-2026-host-seeking-navigation-coluzzii.md`, `audit-gemini-synthesis-host-seeking-numeric-claims.md`) are class C, not class B. They are deleted once every value they use has a ledger row citing its primary source. This supersedes OPEN-2 for these two files. |
| D26 | `papers/README.md`, `papers/REFERENCES.md`, and the per-theme READMEs are indexes, not papers. They are not in `manifest.json`. |
| D27 | One manifest entry is one paper, identified by DOI. Two files with the same DOI are the same paper and merge into one entry. Two files with different DOIs stay separate entries. |
| D14 | Q6: for the ~40 unobtainable papers, nothing replaces the curated layer in Tier 2. Their summaries are deleted only as part of OPEN-1 (§5). **Consequence accepted by the author:** values that exist only in those summaries are lost. |
| D15 | Q7: page-level citations are not produced after the switch to docling. Citations use DOI plus section or table plus a quoted string, and say so explicitly. Existing page citations are re-pointed in step 4. |
| D16 | Q8: resolver order is Crossref → Unpaywall → Europe PMC. The contact email lives in configuration (`mal-core/config/papers.yaml`), not in code. |
| D17 | Q9: the claims ledger is `docs/papers-traceability.md` (English, `|` tables). The author decides `refuted`; the tool does not. |
| D18 | Q10: the generated index and the ledger are in English, matching `docs/`. Spanish notes are migrated into the ledger before they are deleted in step 6. |
| D19 | Q12: the ODD bibliography is not part of this change. |

## 5. OPEN decisions (block execution of steps 4–6)

**OPEN-1. RESOLVED 2026-11-17: the curated summaries are deleted (D20), and
citations point to the papers (D21).**

What was decided, and why it works:

- The ~130 summaries are hand-written. No tool generates them, so they cannot
  be rebuilt. They are deleted, not moved.
- Their values stay recoverable through the citations: each value used by code
  or a plan cites the paper's DOI and locator, and the claims ledger (§6.4)
  records the Tier 1 ones with a verdict. Tier 2 values are lost with the
  summaries (D14, accepted).
- The docling Markdown is not needed as a citation target (D22). It stays a
  local working file, so the question of whether it is versioned no longer
  arises.

Open consequences of this decision are recorded in §11.

**OPEN-2. Destination of class B.**
Class B (the project-authored syntheses cited by shipped code:
`dispersal-kernel-calibration.md`, `biting-rate-eip-gonotrophic-parameters-reference.md`)
must stay tracked. The two Gemini texts are class C (D25). The gitignore excludes the
paper folders, so class B files must sit **outside** any ignored path. The brief
does not name the destination. Candidate: `docs/papers-syntheses/`. This also
requires re-pointing the code references listed in §8, step 5.

**OPEN-3. Gitignore pattern.** The brief's pattern `papers/*/` ignores every
file directly under each theme folder, not only paper subfolders. The correct
pattern for per-paper folders is `papers/*/*/`. This draft uses `papers/*/*/`.
The author confirms this correction. (It is a correction of the brief, not a
new policy; it follows from D5.)

## 6. Technical plan

### 6.1 Classes of object

| Class | Definition | Destination |
|---|---|---|
| A | Primary paper with a DOI | `papers/<theme>/<slug>/` — gitignored (PDF, docling, images, provenance). No curated summary (D20). |
| B | Project-authored synthesis cited by shipped code | Tracked, outside any gitignored path (OPEN-2). |
| C | Internal secondary: research-harness (4 files), Perplexity investigations (3), `hypotheses.md` | Deleted in step 6, after their claims are in the ledger. |

### 6.2 Identity and manifest

- **Identity is a manifest-assigned id, not the DOI.** DOI is an attribute.
  Id forms: `doi:<lower-doi>` when the DOI is unique; `doi:<doi>#<variant>` for
  deliberate companion extracts; `pmc:<id>`, `hal:<id>`, `local:<slug>`
  otherwise.
- Duplicate-DOI pairs are the same paper and merge into one entry (D27). Seven
  pairs are known. The merge rule and the choice of surviving file are
  recorded per pair before step 2 is closed. No `alias_of` field is used.
- **File:** `papers/manifest.json`, hand-authored, tracked. JSON, because the
  repository's other manifests (`data/<aoi>/manifest.json`) are JSON.
- **Harvest:** the initial manifest is harvested from the 156 file headers, not
  transcribed from `REFERENCES.md`. The harvest is read-only.

Entry schema (one object per paper):

```
id, class (A|B|C), theme, slug, title, authors, year, journal,
doi | null, alias_of | null, expected_status, observed_status,
pdf_sha256 | null, resolver | null, licence_as_recorded
```

- `expected_status` (hand-authored) and `observed_status` (written by the tool
  to `provenance.yaml`) use one vocabulary: `ok`, `pending_no_source`,
  `pending_paywalled`, `pending_network`, `pending_extraction_failed`,
  `withdrawn`.
- `licence_as_recorded` is informational. Nothing gates on it (D13).

### 6.3 Layout and gitignore

```
papers/
  README.md            tracked (what the corpus is, rebuild command, vocabulary)
  REFERENCES.md        tracked, generated from manifest.json
  manifest.json        tracked
  <theme>/<slug>/      gitignored: <slug>.pdf, <slug>.md (docling), images/, provenance.yaml
```

`.gitignore` addition:

```
papers/*/*/
!papers/README.md
!papers/REFERENCES.md
!papers/manifest.json
```

Gitignore does not untrack files. Untracking is done explicitly (step 6). The
real fail-safe is a test (§7) asserting that `git ls-files papers/` equals an
allowlist and that no tracked file under `papers/` exceeds 64 KiB.

### 6.4 The claims ledger

- **Location:** `docs/papers-traceability.md`.
- **Tier 1 (blocking):** the 30–60 claims that code or a scoring target reads
  (examples: `adult_sigma_m` → Costantini 1996, 350–650 m/day; the 0.80–0.88
  daily survival range in `llm_verdict.md`; D1–D10 targets in
  `docs/plans/completed/calibration-test-framework.md:143-232`; the anchor table
  in `docs/plans/completed/dispersal-plans/plan-D-mosquito-search-kernels.md:88-94`).
  Each row: the claim as used (value and unit), the paper's DOI or manifest id,
  the locator (section, table, or figure number), an optional quoted string of
  at most 25 words (D21), and a verdict (`verified`, `refuted`,
  `unverified-paywalled`). `refuted` is set by the author only. The ledger has
  no link to any Markdown file (D22).
- **Tier 2:** everything else. An unverifiable claim is recorded
  `unverified-paywalled` and does not block deletion.

### 6.5 The rebuild tool

- **Location:** `mal-core/src/mal_core/papers/` with modules `manifest.py`
  (load and validate), `harvest.py` (one-shot header harvest), `resolve.py`
  (Crossref → Unpaywall → Europe PMC), `fetch.py` (download with sha256
  check), `extract.py` (docling wrapper), `generate.py` (`REFERENCES.md`),
  `check.py` (the §7 assertions).
- **CLI:** `malariasim papers {fetch,extract,generate,check}` registered in
  `mal-core/src/mal_core/cli.py`.
- **Docling:** the portable `docling` console script, invoked with `--tables
  --ocr`, `--enrich-picture-description` off by default, `--device cpu` by
  default with `mps` as opt-in. The device and the docling version are
  recorded in `provenance.yaml`. The project's `docling-mps` wrapper is not used.
- **Dependency:** a `papers` group in `mal-core/pyproject.toml` containing
  `docling`. Current groups are `abm`, `scoring`, `download`, `ingest`, `train`,
  `serve`.
- **Config:** `mal-core/config/papers.yaml` holds the contact email for
  Unpaywall and the output root. No credentials are stored.
- **`mal-execution`** is deprecated for this work and receives nothing new.
- **Retired in the same change as the tool lands:** `tools/extract_papers.py`
  and its row in `tools/README.md`. The extractor uses pdfplumber and writes
  `--- Page N ---` markers, which are not produced by docling.

### 6.6 Page citations

Docling Markdown has no page anchors by default. After this change, citations
use the paper's DOI + section/table/figure, with an optional quoted string
(D15, D21). Citations never point to a Markdown file (D22). Existing page-level citations
are re-pointed in step 4. Example: `dispersal-plans/plan-D…:84-99` becomes a
DOI citation with the section name and the quoted value.

## 7. Acceptance criteria

The criterion is three cheap assertions over tracked files, plus one file-set
test. It is not a rebuild diff. "Identity of the set" is removed as a
criterion: about 40 entries are not obtainable and the set grows during the
traceability pass.

a. Every DOI in `papers/manifest.json` resolves (`HEAD https://doi.org/<doi>`),
   or the entry is `pending_*` with a reason. This is a **local** command, not a
   CI gate: DOI resolution depends on the network and on publishers.
b. Every `doi:` token in a tracked document corresponds to a manifest entry.
c. Every fetched PDF has a sha256 equal to the manifest value.
d. `git ls-files papers/` equals the allowlist (§6.3); no tracked file under
   `papers/` exceeds 64 KiB. This test runs in CI.

Unit tests (`mal-core/tests/test_papers_*.py`): manifest schema validation,
duplicate-DOI alias handling, status vocabulary, `REFERENCES.md` generation
(including the table header regression at line 57), and the `check` assertions
against a fixture manifest.

## 8. Alternatives considered

- **Keep the versioned corpus and only add a licence file.** Rejected: copyrighted
  text stays in git history and in the working tree of every clone. It does not
  address rebuildability.
- **Flat layout `papers/<theme>/<slug>.md`, heavy artefacts as siblings.**
  Rejected by the author (Q4). The reviewers' cheaper option keeps the citation
  path stable, but images and extracts scatter, and gitignore patterns become
  per-extension. The subfolder layout makes the folder the citation target.
- **Use the DOI as the identity.** Rejected: DOIs collide (seven pairs), some
  papers have none (Hawkes 2013 thesis), and preprints have DOIs that may not
  resolve (five cases).
- **Byte-reproducible rebuild as the acceptance test.** Rejected: docling output
  depends on device and model version. Checksums of the PDFs are the contractual
  part.
- **Generate per-theme READMEs.** Rejected: they duplicate `REFERENCES.md` and
  drift. `papers/README.md` keeps only the corpus description and the vocabulary.
- **Delete the curated layer now.** Rejected: it is the only copy of values that
  code and plans cite (§6.4). Deleting it before the ledger holds those values
  loses data.
- **Rewrite git history now.** Rejected for this change: it rewrites shared
  history, needs a force push that the `main` ruleset blocks, and affects GitHub
  Pages caches. Decided separately (D9). Note: deleting files does not remove
  them from history, so until D9 is executed, the content remains recoverable
  from git.
- **Keep the nine hybrids' `## Full Text` blocks and verify their licences.**
  Rejected by the author (D13): with local regeneration, the blocks are not
  needed, and the OCR in at least one of them is unreadable.

## 9. Detailed implementation

Each step leaves every citation resolving to something real. Steps 4 and 6 are
the only ones that move or delete tracked files.

**Step 1 — Legal cleanup. DONE.** Committed on `docs/papers`:

- Deleted `papers/MonoRepo.md` (ACM DOI 10.1145/2854146, full-text extract,
  unrelated to the corpus, no licence statement).
- Removed `## Full Text` from `papers/spatial-analysis/MalariaEliminationWithSpatialDecisionSupportSystems.md`
  (Elsevier; 926 → 34 lines) and
  `papers/spatial-analysis/SpatialStatisticalApproachToMalaria.md` (IEA 2000;
  85 → 43 lines). Summary, citation, and licence lines kept, so `AGENTS.md:9`
  still resolves.

**Step 2 — Manifest (read-only).** Harvest `papers/manifest.json` from the 156
headers. Deletes and moves nothing. Output: an inventory report with (i) the
three header inconsistencies, (ii) unresolved locators, (iii) the seven DOI
collision pairs with the canonical choice for each, (iv) class A/B/C for all
156 files, (v) live path citations, (vi) the ~40 unobtainable entries.

**Step 3 — Claims ledger, Tier 1.** Create `docs/papers-traceability.md`. Correct:

- Costantini 1996: journal filed as *J. Med. Entomol.*, actually *Medical and
  Veterinary Entomology*.
- Depinay 2004: filed as *J. Med. Entomol.*, actually *Malaria Journal*.
- "Bissett et al. 2026 (in prep)": a published Glasgow thesis, DOI
  `10.5525/gla.thesis.85988`.
- The plan cites a judge prompt at
  `mal-abm-fast/tests/calibration/scorers/prompts/llm_verdict.md`, which does not
  exist. The live prompt is `mal-core/src/mal_core/scoring/prompts/llm_verdict.md`.
- Migrate the Spanish notes into the ledger (D18) before their deletion in step 6.

**Step 4 — Move and re-point, one commit.** Requires OPEN-1, OPEN-2, OPEN-3
resolved.

- `git mv` each class A file into `papers/<theme>/<slug>/`, with its PDF and
  docling output when available. Nothing is deleted in this step.
- Delete the nine hybrid files entirely (D23). Files:
  `papers/spatial-analysis/Spatial&SpatioTemporalMethodsForMappingMalariaRisk.md`,
  `papers/spatial-analysis/Spatial–temporal clustering of malaria using routinely collected health facility data on the Kenyan Coast .md`,
  `papers/spatial-analysis/SpatialAnalysisOfMalariaInChina .md`,
  `papers/spatial-analysis/SpatialTemporalCouplingOfMalariaVectorHabitatSuitability&BitingProbability.md`,
  `papers/spatial-analysis/MalariaData2014.md`,
  `papers/spatial-analysis/gwitira-et-al-2020-spatial-and-spatio-temporal-analysis-of-malaria-cases-in-zimbabwe.md`,
  `papers/core-hypothesis/Mathematical Modelling of Malaria Integrating Temperature, Rainfall, and Vegetation Index .md`,
  `papers/core-hypothesis/Integrating DHS:MIS Biomarkers with 34 Years of CHIRPS-NDVI Climate Data for Malaria Risk Prediction in Nigeria- A Machine Learning and Spatial Mapping Approach.md`,
  `papers/core-hypothesis/Associations between environmental covariates and temporal changes in malaria incidence in high transmission settings of Uganda- a distributed lag nonlinear analysis .md`.
  The Odhiambo 2020 (BMJ Global Health) file is one of them; its `## Full Text`
  is unreadable OCR, so removal costs nothing.
- Re-point path citations from the summary files to the paper's DOI, each
  paired with a ledger row (D21). No citation points to a file under `papers/`. Named sites: `papers/…/dispersal-plans/plan-D…:84-99` (re-pointed to
  DOI form), `m7-4-seir-sei.md:53-62`, `abm-mesa-geo-adaptation.md:135`,
  `AGENTS.md:9` (protected; one-line edit, approved as Q11), `calibration-test-framework.md:283`,
  the plan-D table, `m7-3-multi-species.md:39`, `m7-7-insecticide-resistance.md:42`,
  and the four code references below.
- Code references to update (all in `mal-core/src/mal_core/scoring/`):
  `registry.py:16`, `scorers/d21_dispersal_kernel.py:19`,
  `scorers/d1_habitat_occupancy.py:19-20`, `scorers/d11_aquatic_structure.py:8`.
  Each is re-pointed to the class B destination (OPEN-2) or to the DOI form.
- Fix the Perplexity line range: the cited file is 325 lines, the citation says 641.
- `.gitignore`: add the block in §6.3.
- Add `papers/README.md` (rewritten) and `papers/manifest.json` (from step 2).

**Step 5 — Relocate class B.** Move the four class B documents to the OPEN-2
destination and update the code references in step 4. Delete nothing.
Relocation is needed only before step 6 runs.

**Step 6 — The irreversible commit (alone, on its own branch).**

- `git rm -r --cached papers/<theme>/` for class A folders. This untracks the
  paper folders; files stay on disk.
- Delete class C files, only after their claims are in the ledger (D7).
- Delete the ~130 curated summaries (D20), after the Tier 1 ledger rows exist (step 3).
- Delete `tools/extract_papers.py` and its `tools/README.md` row.
- Delete the stale brief reference: `docs/designs/papers-corpus.md` is removed
  per the EGM rule once this plan exists (see §11).
- Add the tracked-files test (§7, d).

Step 6 does not rewrite history (D9). Blobs of class A files remain in git
history until D9 is executed.

**Step 7 — Generated outputs and CI.** Add the `malariasim papers generate`
command and wire `generate --check` as a drift gate in CI, so that
`papers/REFERENCES.md` fails CI when it differs from the manifest.

**Tool build order (can run in parallel with steps 2–3):** `manifest.py`,
`harvest.py`, `resolve.py`, `fetch.py`, `extract.py`, `generate.py`,
`check.py`, the CLI registration, the `papers` dependency group, and the unit
tests in §7.

**Files touched (with rationale):**

| File | Change | Why |
|---|---|---|
| `papers/manifest.json` | create | Single source of truth for the inventory (§6.2). |
| `papers/REFERENCES.md` | regenerate | Generated index, one section per theme (D6). Fixes the broken table at line 57. |
| `papers/README.md` | rewrite | Keeps only corpus description, rebuild command, vocabulary, licence pointer (no counts, no file lists). |
| `papers/<theme>/<slug>/` (≈140 folders) | create (move) | Per-paper folder (D5). Gitignored for class A. |
| the nine hybrid files listed in §9 step 4 | delete | Summary and `## Full Text` both removed (D23). |
| `papers/spatial-analysis/MalariaElimination…md`, `SpatialStatisticalApproach…md` | already edited (step 1) | Legal cleanup, done. |
| `papers/MonoRepo.md` | deleted (step 1) | Unrelated full-text extract. |
| `papers/perplexity-investigations/`, `papers/research-harness/`, `papers/hypotheses.md` | delete (step 6) | Class C, after ledger (D7). |
| `papers/<theme>/*.md` (~130 curated summaries) | delete (step 6) | Hand-written, not reproducible (D20). Deleted only after the Tier 1 ledger rows exist (§9 step 3). |
| `.gitignore` | edit | Add `papers/*/*/` block (§6.3). |
| `docs/papers-traceability.md` | create | Claims ledger (D17, §6.4). |
| `mal-core/src/mal_core/papers/*.py` | create | Rebuild tool (§6.5). |
| `mal-core/src/mal_core/cli.py` | edit | Register the `papers` subcommand. |
| `mal-core/pyproject.toml` | edit | Add `papers` dependency group with `docling`. |
| `mal-core/config/papers.yaml` | create | Output root and contact email for Unpaywall (D16). |
| `mal-core/tests/test_papers_*.py` | create | Unit tests (§7). |
| `mal-core/src/mal_core/scoring/registry.py` | edit (line 16) | Re-point citation (§9 step 4). |
| `mal-core/src/mal_core/scoring/scorers/d21_dispersal_kernel.py` | edit (line 19) | Re-point citation. |
| `mal-core/src/mal_core/scoring/scorers/d1_habitat_occupancy.py` | edit (lines 19–20) | Re-point citation. |
| `mal-core/src/mal_core/scoring/scorers/d11_aquatic_structure.py` | edit (line 8) | Re-point citation. |
| `mal-core/src/mal_core/scoring/prompts/llm_verdict.md` | edit | Cite by author-year with ledger row; the judge's reference ranges are the Tier 1 claims. |
| `docs/plans/completed/calibration-test-framework.md`, `docs/plans/completed/dispersal-plans/plan-D-mosquito-search-kernels.md`, `m7-3-multi-species.md`, `m7-7-insecticide-resistance.md`, `m7-4-seir-sei.md`, `abm-mesa-geo-adaptation.md` | edit (citation lines only) | Re-point path citations (§9 step 4). |
| `docs/plans/in-process/odd-fixes/09-docs-and-papers.md` | **not present** on disk (verified 2026-11-17); nothing to delete. Confirm with `git log`. | Superseded by this plan. |
| `AGENTS.md` | edit (line 9), with explicit user approval | Protected file; the only link a fresh clone would break (D12). |
| `tools/extract_papers.py`, `tools/README.md` | delete row and file (step 6) | Retired extractor (§6.5). |
| `docs/designs/SITEMAP.md` | edit (line 16) | Register this plan as a drafted plan, not a design (§11). |
| `docs/designs/papers-corpus.md` | delete after review (§11) | Temporary brief; the plan replaces it. |

**Plan-doc paths referenced in §9 step 4 that the author must check** (by
`grep` at execution time, not at draft time): the exact lines of
`m7-4-seir-sei.md`, `abm-mesa-geo-adaptation.md`, and the plan-D table. They
were checked in the brief, not in this draft.

## 10. Deferred

- ODD bibliography generation (19 `\bibitem`s, of which about 11 are data or
  protocol references that will never be corpus papers; needs a `kind` field and
  a LaTeX generator).
- `git filter-repo` (D9), until the author decides.
- Byte-reproducible docling output: not a goal (§3).

## 11. Contradictions reconciled with the brief and open items

Reported at drafting time and resolved by the author on 2026-11-17:

- **Brief §3 and §6.1 (#4) said the nine hybrids keep their `## Full Text`
  until the licence is verified.** Replaced by D13: the blocks are removed in
  step 4.
- **Brief §6.1 (#5) and §6.2 said class A is ignored, and brief Q3 said licences
  are verified in step 2.** Replaced by D13; licence verification no longer gates.
- **Brief Q6 default ("nothing for Tier 2") conflicted with brief §4 and Q2.**
  Resolved as D14, with the data loss stated explicitly. The author accepted it.
- **Brief Q7 default (per-page re-extract) was not chosen.** Resolved as D15.

Open after this draft:

- Resolved: nine hybrid files deleted entirely (D23); Tier 1 claims on
  unobtainable papers recorded `unverified-paywalled` (D24).
- OPEN-2 (class B destination) and OPEN-3 (`papers/*/*/`) accepted; to be
  written into §6.1 and §6.3 on the next revision.
- **Brief deletion.** AGENTS.md says the brief is deleted once the draft is
  written. Not done here: it is `docs/designs/papers-corpus.md`, the SITEMAP
  row at `docs/designs/SITEMAP.md:16` must be updated to point at this plan,
  and the deletion needs the author's go-ahead.
- Count discrepancy: 156 tracked files now; the brief said 157. Resolved by the
  step 2 harvest.

## 12. Handoff to the implementing session

The design is closed (D1–D27). The items below are implementation defaults, so the
implementing session does not need to ask the author.

**State on disk at handoff (2026-11-17)**

- `papers/manifest.json` is **untracked and stale**. It was produced before D25–D27.
  Regenerate it; do not use it as is. It has the two Gemini texts as class B, the
  three READMEs and `REFERENCES.md` as class A, and the seven duplicate-DOI pairs
  as separate entries with `alias_of`.
- A tester approved the DOI check on the 137 DOI entries (after five Markdown-residue
  fixes). The Midega 2007 DOI contains brackets (`[923:EDASOA]`); that is correct and
  must not be "cleaned".
- `docs/designs/papers-corpus.md` (the brief) still exists. Its deletion needs the
  author's explicit confirmation (AGENTS.md).

**Defaults for the implementing session**

- Duplicate-DOI pairs (D27): keep the file in the theme folder that matches the
  paper's subject; delete the other. Do not merge file contents.
- Greenwood 2014 (`greenwood-et-al-2014-…`): its header names the wrong first
  author for DOI 10.1186/1475-2875-13-424. Keep the Arifin file as the entry; the
  Greenwood file is deleted only after its content is confirmed against the paper.
- Aduvukha (DOI 10.1016/j.sste.2025.100777): the two files disagree on year (2025 vs
  2026). Use the year on the publisher's landing page; record it in the manifest.
- Expected counts change. Recount after D25–D27 instead of reusing the 156 figure.
- The "~40 unobtainable" figure is replaced by the resolver's measured count (step 3).

**Order for the new session:** regenerate the manifest (step 2) → tester approval
→ ledger (step 3) → steps 4–7 as written in §9, each with its own tester gate.

## 13. Execution record (2026-11-18)

Steps executed in the order of §9, on branch `docs/papers`. Deviations from
the text of the plan, each decided by the author's instruction to finish the
work coherently with the plan:

- **Step 2.** `papers/manifest.json` uses the schema of §6.2 with these
  changes: `observed_status` is not a manifest field (it lives in each paper's
  `provenance.yaml`); `path`, `header_notes`, `hybrid_full_text`,
  `year_candidates` are dropped; `superseded_files` records the D27 merges;
  `authors`, `journal`, `year` may be null when the source has no value.
  Fifteen DOIs cited by documents were added as entries (check (b)).
- **Step 3.** The ledger's `verified` means "quoted from the abstract in the
  local summary", not "checked against the paper text" (stated in its
  Purpose). Nine rows are candidates for `refuted`, decided by the author.
- **Step 4.** Class B: two files, not four (`dispersal-kernel-calibration`,
  `biting-rate-eip-gonotrophic-parameters-reference`), moved to
  `docs/papers-syntheses/` (OPEN-2 default). Hybrids deleted per D23; seven
  entries lost their only survivor file and stay in the manifest (D23).
  AGENTS.md:9 changed as Q11 approved, to `doi:10.1016/j.pt.2012.04.002`.
- **Step 6.** Class A summaries and class C files deleted from the working
  tree and the index; class C entries removed from the manifest (they are not
  papers). `tools/extract_papers.py` and the brief `docs/designs/papers-corpus.md`
  deleted; `docs/designs/SITEMAP.md` row points at this plan.
  The DOI of Bockarie 1995 in the class B synthesis returned 404 and was
  replaced by its PMID with the DOI marked "not verified".
  Recovery: commit `9172430` holds every deleted file (`git show 9172430:<path>`);
  a local archive of the working tree before deletion is at
  `~/.local/share/malariasim-backups/papers-pre-step6-9172430.tar.gz`.
- **Step 7.** Assertion (d) exempts `papers/manifest.json` from the 64 KiB
  limit: the 64 KiB rule guards against copied article text, and the manifest
  is metadata (about 110 KB, one object per paper). Assertion (b) reads
  documents only (tests are excluded). `REFERENCES.md` is generated;
  `.github/workflows/papers.yml` runs the drift gate, `papers check`, and the
  papers tests on pull requests.

Open after execution:

- `docs/concepts/scoring/scoring.tex:1198,1204` and `docs/concepts/scoring/questions.md:471`
  describe the earlier state (anchors pointing into `papers/`). They belong to the
  concept-document process and were not edited.
- Seven class A entries have no survivor file; rebuild with `malariasim papers fetch`
  or from git history.
- Three slug/author mismatches against Crossref (Alemayehu 2024, Slimani 2026,
  Nkemka 2021) were reported and not changed.
- D9 (history rewrite) not executed; blobs of the removed files remain in history.

