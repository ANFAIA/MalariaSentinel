# RFC brief — `papers/` as a reconstructible artefact

Status: brief (temporary). Input to the drafting step; deleted when the plan
exists in `docs/plans/in-process/papers-corpus.md`.

Supersedes `docs/plans/in-process/odd-fixes/09-docs-and-papers.md`, which is
deleted in the same change. Its acceptance criterion (lines 44–70 of that file)
is replaced by §5 below and must not be reinstated.

Evidence base: `egm-brainstorm-report.md` (seven Goldfish reviewers, run
2026-11-17), checked by hand against the repository on the same day.

---

## 1. Goal and non-goals

**Goal.** Stop redistributing copyright-restricted material from the repository,
and make the paper corpus rebuildable from a tracked manifest. Every citation in
a tracked document must resolve to a manifest entry, a DOI, or an explicit
"not obtained" record.

**Non-goals.**
- Making the corpus byte-reproducible. Docling output varies by device and model
  version; only identifiers and PDF checksums are contractual.
- Rebuilding the ODD bibliography from the manifest (deferred, §7).
- Rewriting the curated summaries of paywalled works (deferred until §6 is
  decided; see §4).

## 2. Current state (verified 2026-11-17)

- 157 tracked files under `papers/`, in 9 thematic folders plus
  `perplexity-investigations/` and `research-harness/`. No PDFs are tracked.
- `papers/REFERENCES.md` has 113 table rows. Its table is broken at line 57
  (a blank line splits it; the second half has no header).
- DOI declared in the file header (`**DOI:**` line): 147 files mention a DOI;
  the header format is not uniform across files.
- DOI collisions (two files, same DOI), 7 pairs:
  `10.1371/journal.pcbi.1007446` (Wu 2020 ×2),
  `10.1186/1475-2875-3-29` (Depinay 2004 ×2),
  `10.1186/1475-2875-13-424` (Arifin / Greenwood 2014),
  `10.1016/j.sste.2025.100777` (Aduvukha, two folders),
  `10.1371/journal.pcbi.1008121` (Selvaraj 2020 ×2),
  `10.64898/2025.12.14.25342244` (Onimisi, two files),
  `10.1007/s10440-025-00740-y` (Gatore Sinigirira, two folders).
- Non-DOI identifiers: `PMC12888552` (Cambodia), `hal-05382643v1` (Rakotoarison),
  no identifier (Hawkes 2013 thesis), institutional URL (SNT toolbox).
- Copyright-restricted entries in `REFERENCES.md`: rows 8, 9, 12, 14, 15, 18,
  27, 28, 31, 45–50, 52, 91, 95, 97, 105 (restricted licence, of which several
  are abstract-only), plus 71 and 104 (licence unverified / preprint).
- Files shipped code points at under `papers/` (must keep resolving):
  `mal-core/src/mal_core/scoring/registry.py:16`,
  `scoring/scorers/d21_dispersal_kernel.py:19`,
  `scoring/scorers/d1_habitat_occupancy.py:19-20`,
  `scoring/scorers/d11_aquatic_structure.py:8`.
- `papers/MonoRepo.md` (full-text extract of ACM DOI 10.1145/2854146) was
  unrelated to the corpus and had no licence statement.

## 3. Step 1 — legal cleanup (DONE, committed separately)

Done on branch `docs/papers`:

- Deleted `papers/MonoRepo.md`.
- Removed the `## Full Text` block from the two restricted hybrids:
  `papers/spatial-analysis/MalariaEliminationWithSpatialDecisionSupportSystems.md`
  (Elsevier; 926 → 34 lines) and
  `papers/spatial-analysis/SpatialStatisticalApproachToMalaria.md`
  (IEA 2000; 85 → 43 lines). Summary, citation and licence lines kept, so
  `AGENTS.md:9` still resolves.
- Kept the `## Full Text` blocks of the nine remaining hybrid files. Each one's
  DOI has a row in `REFERENCES.md` with an open licence (CC-BY 4.0, CC-BY 2.0,
  or CC BY-NC 4.0). Checked by DOI lookup on 2026-11-17.

**Not done, deliberately:** deleting the curated summaries of paywalled works.
They are paraphrases with a licence line, not reproduced text, and they are the
only surviving copy of values that code and plans cite (§4). Deleting them is
data loss, not legal cleanup.

**History.** Deleting files in a commit does not remove them from git history,
and the repository publishes GitHub Pages from `main:/docs`. Rewriting history is
a separate user-level decision (§6, Q1).

## 4. The curated layer is the only copy of some values

The load-bearing values live in four places, and the curated summaries are the
only documents that record them with their source:

- `mal-core/config/model_constants.yaml` provenance comments
  (for example `adult_sigma_m` → Costantini 1996, 350–650 m/day).
- `mal-core/src/mal_core/scoring/prompts/llm_verdict.md` — the LLM judge's
  embedded reference ranges (0.80–0.88 /day survival, EIP 12–14 d at 26 °C,
  p90 1.0–1.4 km, Moran's I 0.30–0.70), cited author-year only.
- `docs/plans/completed/calibration-test-framework.md:143-232` (D1–D10 targets).
- `docs/plans/completed/dispersal-plans/plan-D-mosquito-search-kernels.md:88-94`
  (anchor table).

Known defects found while checking these (to fix in the same pass, not
deferred): Costantini 1996 is filed as *J. Med. Entomol.* but is *Medical and
Veterinary Entomology*; Depinay 2004 is filed as *J. Med. Entomol.* but is
*Malaria Journal*; "Bissett et al. 2026 (in prep)" is a published Glasgow thesis
(DOI `10.5525/gla.thesis.85988`); the plan cites a judge prompt path
`mal-abm-fast/tests/calibration/scorers/prompts/llm_verdict.md` that does not
exist (the live prompt is `mal-core/src/mal_core/scoring/prompts/llm_verdict.md`).

## 5. Acceptance criterion (replaces plan 09)

The criterion is three cheap assertions over tracked files, not a rebuild diff:

a. Every DOI in `papers/manifest.json` resolves (`HEAD https://doi.org/<doi>`),
   or the entry is `pending_*` with a reason.
b. Every `doi:` token in a tracked document is a manifest entry.
c. Every PDF fetched has a sha256 equal to the manifest value.

"Identity of the set" is removed as a criterion. It cannot be satisfied: about
40 entries are not obtainable, and the set grows during the traceability pass.

## 6. Decisions

### 6.1 Taken by the author

1. Extracted text comes from docling, not from curated summaries.
2. Papers that cannot be obtained are reported in a pending manifest; the tool
   reports and continues, it does not fail the run.
3. Automatic download where obtainable; the rest is left to the user through the
   manifest.
4. Nothing of the paper material goes to GitHub.
5. Each paper is in its own subfolder under its theme folder, with the PDF,
   docling output, `images/` when referenced, and `provenance.yaml`.
6. `REFERENCES.md` and the theme READMEs are generated from the manifest.
7. Secondary documents are deleted only after a traceability pass produces a
   versioned ledger and re-points the live citations.
8. The tool lives in the `malariasim` toolkit; docling is a declared
   dependency, not an implicit PATH dependency.

### 6.2 Changed by review (the reviewers were right; the author accepts these as defaults)

- **Identity is a manifest-assigned id, not the DOI.** DOI is an attribute.
  Ids: `doi:<lower-doi>` when unique; `doi:<doi>#<variant>` for the deliberate
  companion extracts; `pmc:`, `hal:`, `local:` otherwise. Duplicate pairs get a
  canonical/alias relation.
- **Manifest format:** `papers/manifest.json`, hand-authored, tracked. JSON,
  because the repo's manifests (`data/<aoi>/manifest.json`) are JSON. It is
  harvested once from the 157 file headers, not transcribed from
  `REFERENCES.md`.
- **Status vocabulary** (expected state in the manifest; observed state written
  by the tool to `provenance.yaml`): `ok`, `pending_no_source`,
  `pending_paywalled`, `pending_network`, `pending_extraction_failed`,
  `withdrawn`.
- **Layout compatibility.** Paths cited today must keep resolving, so the
  flat addressable unit `papers/<theme>/<slug>.md` stays, with the heavy
  artefacts as siblings — *or* every path citation is re-pointed in the same
  change (§8, step 4). Decision needed: §6.3 Q4.
- **Gitignore:** `papers/*/` plus explicit re-inclusions only:
  ```
  papers/*/
  !papers/README.md
  !papers/REFERENCES.md
  !papers/manifest.json
  ```
  Gitignore does not untrack. The real fail-safe is a test asserting
  `git ls-files papers/` equals the allowlist and that no tracked file under
  `papers/` exceeds 64 KiB.
- **Three object classes, three destinations:**
  - A. Primary paper (has a DOI) → reconstructible; gitignored with its folder.
  - B. Project-authored synthesis cited by shipped code (`dispersal-kernel-calibration.md`,
    `biting-rate-eip-gonotrophic-parameters-reference.md`, the two Gemini
    syntheses) → **tracked**, relocated out of the ignored tree.
  - C. Internal secondary (research-harness ×4, Perplexity ×3, `hypotheses.md`)
    → deleted after traceability.
- **Claims ledger instead of re-reading 140 papers.** Tier 1 (blocking):
  the ~30–60 claims that code or a scoring target reads. Tier 2: everything
  else; an unverifiable claim is recorded `unverified-paywalled` and does not
  block deletion.
- **Per-theme READMEs are dropped.** `REFERENCES.md` is the one generated index,
  with one section per theme. `papers/README.md` keeps only what the corpus is,
  the rebuild command, the vocabulary and the licence pointer — no counts, no
  file lists.
- **Tool location:** `mal-core/src/mal_core/papers/` with a `papers` subcommand in
  `mal-core/src/mal_core/cli.py`. Docling in a `papers` dependency group in
  `mal-core/pyproject.toml`. `mal-execution` is deprecated and gets nothing new.
- **Docling invocation:** the portable `docling` console script, `--tables --ocr`,
  `--enrich-picture-description` off by default, `--device cpu` default with
  `mps` opt-in and the device recorded. The `docling-mps` wrapper is not used.
- **Retire `tools/extract_papers.py`** and its `tools/README.md` row in the
  same change that lands the new tool.

### 6.3 Open — the author must answer

- **Q1. History rewrite.** Do we run `git filter-repo` over the paper paths to
  remove the already-committed extracts, with a force-with-lease push? This
  rewrites shared history and affects the GitHub Pages cache. Default: no. The
  legal cleanup in §3 stands without it.
- **Q2. Non-OA curated summaries (~26 rows).** Keep them as paraphrase with
  licence line (default), or delete the restricted ones and lose the only copy of
  their values? Default: keep until the ledger (§6.2) holds their values.
- **Q3. Licence of the open hybrids.** Recorded as CC in `REFERENCES.md`, but
  the licence line in the file header is not always present. Default: verify
  each against the publisher page during step 2; the `## Full Text` blocks stay
  until then.
- **Q4. Layout: flat path or subfolder?** The reviewers' cheaper option keeps
  `papers/<theme>/<slug>.md` addressable. The subfolder option requires
  re-pointing every path citation (`dispersal-plans/plan-D…:84-99`,
  `m7-4-seir-sei.md:53-62`, `abm-mesa-geo-adaptation.md:135`, `AGENTS.md:9`).
  Default: flat path, heavy artefacts as siblings.
- **Q5. Plan 09.** Deleted with this brief (done in the same change as this
  file). Its decision to make the ODD bibliography an input is reversed here
  (§7).
- **Q6. What replaces the curated layer for the ~40 unobtainable papers.** Default:
  the claims ledger (§6.2) for Tier 1; nothing for Tier 2.
- **Q7. Page-level citations after the switch to docling.** Docling markdown has
  no page anchors by default; the legacy `--- Page N ---` markers come from the
  pdfplumber extractor being retired. Default: a per-page re-extract writing
  `<!-- page: N -->`, or citations are DOI + section/table + quoted string, stated
  as such.
- **Q8. Resolver order and contact.** Unpaywall needs an email; Crossref,
  Europe PMC and publisher OA endpoints cover different subsets. Default:
  Crossref → Unpaywall → Europe PMC, with the email in the config, not the code.
- **Q9. Ledger location and adjudication.** Default: `docs/papers-traceability.md`
  (a sibling of `docs/licenses.md`, English, `|` tables). Who decides `refuted`
  is the author; the tool does not.
- **Q10. Language.** Default: English for the generated index and ledger,
  matching `docs/`. The Spanish notes are deleted in §8 step 6, so the Spanish
  content is migrated into the ledger first.
- **Q11. `AGENTS.md`.** It is a protected file (`AGENTS.md` protected-files
  table). Its `:9` link is the only reference that a fresh clone would break.
  Default: a separately approved one-line edit to point at the manifest entry,
  after step 2.
- **Q12. ODD bibliography.** Deferred. Default: not in this change. It has 19
  `\bibitem`s, of which roughly 11 are data or protocol references (Grimm,
  Macdonald, Zurell, Pekel, Schiavina…) that will never be papers in the
  corpus, and it needs a `kind` field and a LaTeX generator.

## 7. Deferred

- ODD bibliography generation (Q12).
- `git filter-repo` (Q1), until the user decides.
- Byte-reproducible docling output: not a goal (§1).

## 8. Sequence

Each step leaves every citation resolving to something real.

1. **Legal cleanup** — DONE (§3).
2. **Manifest** — harvest `papers/manifest.json` from the 157 headers; read-only;
   deletes and moves nothing. Output: the inventory report the reviewers asked
   for (three inconsistencies, unresolved locators, DOI collisions with the
   canonical choice, class A/B/C for all 157, live path citations, the ~40
   unobtainable entries).
3. **Claims ledger** for the Tier 1 claims; correct the journal attributions,
   the phantom Bissett citation and the judge-prompt path.
4. **Re-point citations** — the named sites (§4, plan 09 references,
   `calibration-test-framework.md:283`, the plan-D table, `m7-3-multi-species.md:39`,
   `m7-7-insecticide-resistance.md:42`, `abm-mesa-geo-adaptation.md:135`) to
   `doi:` form, each paired with a ledger row. Nothing deleted yet. Also fix the
   Perplexity line ranges (the cited file is 325 lines, the citation says 641).
5. **Relocate class B** out of the ignored tree (only needed once step 6 runs).
   Delete `MonoRepo.md` — already done.
6. **The risky commit** — `git rm -r --cached papers/` for class A, the
   `.gitignore` block, delete class C after its claims are in the ledger, add
   the tracked-files test. Alone on its branch.
7. **Generated outputs and CI** — generate `papers/REFERENCES.md` and wire the
   `--check` drift gate.

`AGENTS.md` is edited only with explicit user approval (Q11).

## 9. Known risks carried into the draft

- The verification in §5 depends on DOIs that may not resolve for preprints
  (five of them).
- Re-pointing a citation to a DOI of a paywalled paper sends the reader to a
  paywall. The "not obtained — citation only" form is the honest fallback.
- Step 6 is the only irreversible step; it is not started until steps 2–4 are
  merged.
- Full rebuild cost: several GB and hours; never run in CI.
