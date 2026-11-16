# Concepts Brief (raw, consolidated) — Per-stage conceptual docs in LaTeX, generated technical docs, PR coherence gate

**Mode:** BRAINSTORM (upstream concept ideation). Read-only: no commits, no pushes.
**Repo:** `/Users/davidflorezmazuera/Downloads/MalariaSentinel` @ `main`.
**Concept under review:** retire `docs/specs/` stage by stage; replace with one formal LaTeX conceptual document per pipeline stage under `docs/concepts/<phase>/` (download, ingest, abm, scoring, training, prediction); per-typology question sets; PDFs built in CI and linked from the site; a PR workflow that (a) generates Python and C++ API docs and (b) checks change-vs-concept coherence; `data/` leaves GitHub (local only); `papers/` parked.
**Decisions treated as fixed** (not re-litigated): specs die; unit = pipeline stage; LaTeX source + PDF CI output; English; docs written before packs 03/05/10/11 stabilise; experiment/top-level-system-doc scope is the author's; `data/` survives locally; `papers/` parked.

This file is the raw synthesis. It is organised by threat, not by lens. Every finding carries the lens that raised it and the original finding ID so the final brief can trace back.

---

## Reviewer status

| Lens | Agent | Status | Findings |
| --- | --- | --- | --- |
| Design / architecture | `egm-design` | completed | 12 (B1–B12) + 3 nits |
| Codebase details | `egm-codebase-details` | completed | 16 (F1–F16) + premise corrections + module/anchor inventories |
| Zoom-out / systems | `egm-zoom-out` | completed | 10 (F1–F10) |
| Comprehension / reader | `egm-comprehension` | completed | 16 (F1–F16) |
| Implementation readiness | `egm-implementation-readiness` | completed | 21 (F1–F21) + effort table + ordered sequence |
| Structural / IA | `egm-structural` | completed | 25 (F1–F25) + slot skeleton + layout |
| Inventive catalyst | `egm-inventive-catalyst` | completed | 13 (F1–F13) + minimal-week plan |

All seven ran. No lens returned empty. Verification boundary: two lenses had `read`+`find` only (no shell) and said so; claims about installed binaries (`pdflatex`, `doxygen`, `sphinx-build`) are unverified assumptions, and one lens could not confirm LOC counts. Everything about repo content is file-cited by at least one lens.

---

# Part 0 — Premise corrections that change the shape of the plan

These are not opinions. They are places where the concept's stated facts are wrong, and each one moves work.

**P1. The repo has four packages, not five, and one undocumented fifth.** `mal-ghana-sim` is gone — `mal-core/README.md:3` calls it the "former `mal-ghana-sim`". `find */pyproject.toml` returns five hits: `mal-commonlib`, `mal-core`, `mal-execution`, `mal-data-explorer`, and an **undocumented `social-networks/`** (a marketing-content agent with its own `pyproject.toml`). Consequence: the "stage × package" mental model in the concept does not hold, and the repo's own descriptions already drift. *(codebase-details)*

**P2. `mal-execution` contains no CLI.** `mal-execution/src/mal_cli/` holds only `__init__.py`. The 808-line CLI lives at `mal-core/src/mal_core/cli.py`. The "mal-execution is orchestration only" assumption is closer to "mal-execution is mostly shell scripts plus five helper `.py` files". *(codebase-details)*

**P3. `thresholds.yaml` does not exist, `scorers/composite.py` does not exist, `max_delta` does not exist, and the calibration pytest harness was deleted.** `min_score` and `hard_floor` are class attributes on `Scorer` (`mal-core/src/mal_core/scoring/scorers/base.py:84-85`); weights live in `COMPOSITE_WEIGHTS` (`scoring/registry.py:52-68`); `scorers/base.py:1-7` records that the old pytest calibration harness and its duplicated scorers were deleted in 2026-10. `AGENTS.md`'s "Calibration framework conventions" section therefore tells any agent to edit three files that do not exist and to run a directory that returns "not a directory". *(codebase-details, zoom-out)*

**P4. The C++ engine is not pybind11.** There is no pybind11 in the tree; `mal-core/src/mal_core/abm/wrapper.py` shells out to the compiled binary via `subprocess` and parses `--help` via `_introspect_flags`. The real Python↔C++ interface is CLI flags, `model_constants.yaml` keys, NetCDF/GPKG/CSR inputs, and COG+sidecar outputs. "Cross-language API docs" has no object to link; a Doxygen↔Breathe bridge would document 40 internal headers no Python caller touches and would miss the thing that actually breaks (flag and file-contract drift). *(implementation-readiness)*

**P5. `codebase-memory` is not available to CI.** `.codebase-memory/` does not exist in the repo, so Part 2 of `docs/plans/in-process/docs-pr-agent-and-codebase-memory.md` is unexecuted. Any gate that relies on `search_graph`/`trace_path` is unreproducible for a fresh clone or a runner. *(inventive)*

**P6. The drift the concept wants to cure is already in the repo, in three artefacts the concept depends on.** Verifiable now:

| Prose authority | Claim | Reality |
| --- | --- | --- |
| `docs/specs/abm/spec.md` §8 | `assert cv.startswith('2.')` | INV-15 pins contract v4.0 |
| `docs/specs/abm/spec.md` INV-1 | bands `["density","suitability"]` | INV-12: `["adult_patch_count","adult_cell_count"]` |
| `docs/specs/data/spec.md` INV-11 | env-NC `contract_version: "2.0"` | `model_constants.yaml:8`: `env_nc: "3.0"` |
| `docs/specs/commonlib/spec.md` §4.3 | `K_MAX` is public API | `mal-core/../config.py:63-66`: "K_MAX retired (2026-10-20)" |
| `docs/specs/commonlib/spec.md` §2 vs §4.2 | TWI "exists only in git history" vs `compute_twi` documented as live | self-contradiction in one file |
| `docs/specs/abm/spec.md` §6, §10 | cites `docs/specs/pipeline/spec.md` | no `pipeline/` directory exists |
| `wire.hpp:~119` | cites `docs/abm-status.md:79` | file does not exist |
| `mal_commonlib/config.py:3` | "All values come from DESIGN.md (rev 4, APPROVED)" | no `DESIGN.md` anywhere |
| `docs/README.md:11-25` | lists 6 paths | `specs/self_improve/`, `diagrams/`, `presentacion-10-minutos.md`, `guion-presentacion-10-minutos.md`, `system-status.md`, `agent-selection-guide.md` — none exist |
| `docs/index.html` | "14 evaluadores"; "agents/K_MAX"; Ghana "9.466 celdas" | spec pins 13 dims + 6 gates; K_MAX retired at 4.0; ODD says 551×779 = 429,229 cells |

This single table is the most important input to the brief: the specs did **not** rot because refactors forced noise edits. They rotted because nothing executed their checks. *(codebase-details F4, zoom-out F3/F6, comprehension F12, structural F1/F2, implementation-readiness F7/F21)*

**P7. The "authoritative example" is in a gitignored directory.** `.cache/` is ignored (`.gitignore:53-54`). `odd-2010-malariasentinel.tex`, the 85-comment notes copy, and both ODD templates have never been committed. CI cannot build them, a fresh clone cannot copy them, a PR cannot review changes to them. Items 2, 3 and 4 of the concept all assume a repo-resident `.tex` corpus that does not exist. *(codebase-details F1, design N2, inventive F1)*

---

# Part 1 — Blockers (threat-ordered, deduplicated)

## 1. The coherence gate is asked to verify the one class of claim that cannot be verified, and the only machine-readable anchors left are being deleted with the specs

**Lenses in agreement:** design (B2, B4), codebase-details (F3, §(c)), zoom-out (F3, F9, F10), comprehension (F12, F14), implementation-readiness (F9, F10, F11, F12), structural (F9, F12, F25), inventive (F5).

**Strongest concrete objection (design, B2):** whatever else `docs/specs/abm/spec.md` got wrong, §5 and §8 gave the state contract a numbered, greppable form — band names, the `-9999.0` sentinel, required sidecar keys, the `contract_version` refusal rule. The replacement puts those into the I/O section of prose that an LLM is asked to check. Numeric and name drift (`adult_patch_count` → `density`, `-9999` → `-9999.0`, `k_max` reintroduced in a sidecar) is exactly the class a prose reviewer misses and a `grep` catches. The artefact that catches silent numeric drift is deleted, and nothing mechanical takes its place.

**Second, independent mechanism (codebase-details, F3):** every spec already opens with a fenced block reading `# Machine-readable affects block — parsed by the drift-check agent` and carries `Last drift check: 2026-08-05`. No drift-check agent exists — there is no `.github/` directory at all. The bidirectional `affects` graph was never parsed; the `INV-1..INV-16` invariants had no runner. Item 6 re-proposes the same contract under a new name and adds no executor. Corroborating: `tools/run_all_tests.sh` pairs `set -e` with `pytest || echo "no tests"`, so every failing suite is swallowed and the script always exits 0 — there is no trustworthy gate to hook onto.

**Third, governance (zoom-out, F9):** a blocking prose judgement gives an agent merge authority over the maintainer, on grounds that cannot be falsified. The project has already answered this in the opposite direction for a near-identical design: `docs/specs/scoring/spec.md` INV-12 requires the LLM verdict to be non-gating ("when the key is absent or the call fails, the module returns a `fallback`"), and `AGENTS.md` classifies reviewing subagents as `ask`, not `allow`. There is also an existing human-invoked mechanism for this exact job — `.pi/egm/skills/egm-drift-report/SKILL.md` — which the proposed bot reimplements with merge authority added.

**Fourth, operability (implementation-readiness, F10–F12):** the gate needs a path→stage table that does not exist; the only structured dependency data in the repo is the `affects:` YAML being deleted. Fork PRs get no secrets, so an LLM gate no-ops exactly where unfamiliar code enters. Making the check "required" interacts badly with the protection ruleset: a bot push dismisses stale approvals, and a fresh head SHA carries no checks. Bot-authored "request changes" reviews cannot approve and collide with the dismiss-stale rule.

**What is mechanically checkable today, with zero false positives** (codebase-details §(c), implementation-readiness F10 — the two lists agree):
1. Every dotted key cited in a doc exists in `model_constants.yaml` with the printed value.
2. Every `\code{...}` identifier resolves (Python import/getattr; C++ symbol present in `include/mal_abm_fast/*.hpp`). The ODD already wraps identifiers in `\code{}`/`\bcode{}`, so this is structured.
3. Contract versions in a doc equal `model_constants.yaml:contracts.*`.
4. Recomputed derived numbers (e.g. 551×779 from `aois.yaml` + `geodesy` constants — verified exactly by one lens).
5. LaTeX integrity: `latexmk -Werror` → no undefined refs/citations; `\eqref` resolves.
6. Every `docs/…`, `papers/…`, `scripts/…` path named in a doc or source comment exists. Would have caught all of P6's dangling references.
7. Each output layout documented for the ABM appears in at least one consumer glob.
8. Changed path → candidate doc by directory, for single-stage paths only.
9. Freshness: doc declares `% sources:` globs + hashes; mismatch means "regenerate".

**What is inherently judgement** (both lenses agree): process *ordering* claims; semantic claims where every symbol exists (the 4-of-7 channel gap passes every name check); formula-vs-code equivalence (nothing links LaTeX to source); implemented-vs-unimplemented statements; cross-stage blast radius from a shared config change; provenance.

**Defusing change (converged):** two tiers with different authority.
- **Blocking, deterministic, no LLM, no secrets:** checks 1–9 above; plus a presence rule (a change under `mal_core/<stage>/` must touch the stage doc, or carry a `Coherence-Waiver: <reason>` commit trailer). Fail on *absence*, never on phrasing.
- **Advisory, LLM:** contradiction review posted as a PR comment, `continue-on-error`, never a required check; scoped to the diff plus the mapped doc sections, not the whole corpus.

Note the asymmetry the lenses expose and the author should see stated plainly: the rejection/error the author asked for is deliverable **only** by the deterministic tier. Every lens that examined LLM-blocking concluded it should not block. Restricting "rejection" to absence and anchor checks is not a softening of the request — it is the only version of the request that survives contact with a false positive.

---

## 2. The ABM document will be published known-false, and a PDF is trusted more than a spec

**Lenses in agreement:** design (B3), codebase-details (F12, and the ODD's own Appendix A), comprehension (F7, F13), implementation-readiness (F20), structural (F22).

**Strongest concrete objection (design, B3 / implementation-readiness, F20):** the churn is not scattered sentences. It lands precisely on the ODD elements the packs redefine. Pack 10 states the state COG is "Wrong!! Must be individuals (array) + aquatic cohort" — so the state-variable table and the output section are knowingly wrong on the day they are written. Pack 05 says `update_habitat_day()` uses `default_species_weights()` instead of the active species row, i.e. transcribing the S/K equations from the C++ mirror documents a bug. Seven of thirteen packs touch what the ABM doc must say (02 entities, 03 movement, 04 gonotrophic, 05 habitat/H, 07 aquatic stressors, 08 renames and `k_ref` units, 09 seed, 10 output, 12 dead paths). For ABM alone that is >40% of the mechanism sections.

**Why "churn accepted" understates it (comprehension, F7):** a formal PDF with a pinned commit and date is *more* trusted than a spec, not less. Publishing six formal documents that are provably false in their core is worse than publishing none, because the format asserts authority.

**The existing ODD already demonstrates the failure mode (comprehension, F13; codebase-details F7):** four of its fifteen Appendix A notes say the described mechanism is not what the code does — `feeding_success_rate` is stored but never drawn; `HOST_APPROACH`/`PROBING` are never entered; the 12 nightly hourly sub-steps are never advanced; the round-robin constructor is unused. Element 3's pseudocode shows one `SEEK HOSTS AND FEED` call while §7.6 describes a four-phase loop with a 500 m step, a 1,500 m re-scan, a roulette and a dominance rule — a reader cannot reconstruct §7.6 from Element 3.

**Two competing remedies — this is a genuine clash, see Part 3.2.**

---

## 3. "Pipeline stage" does not partition the content, and 25% of the retiring corpus has no destination

**Lenses in agreement:** design (B5, B9), codebase-details (F5, F6, and the module inventory in §(a)), zoom-out (F2), comprehension (F11), implementation-readiness (F17), structural (F3, F4, F5).

**Strongest concrete objection (codebase-details, F5 — with a count):** of ~62 non-test modules in `mal-core/src`, ~44 map to exactly one of the six stages; ~12 are cross-cutting; 1 is dead. Of ~26 in `mal-commonlib/src`, ~21 are download-ish, 4 cross-cutting, 3 suspect-dead. Outside the packages, `social-networks/agent/*` (4 files), `tools/*.py` (2), and `mal-data-explorer/*.py` (14) belong to no stage. The cross-cutting set is the load-bearing one: `habitat/{potential,availability,capacity,aquatic_stress,config}.py`, `model_constants.yaml` + `config_validation.py` (gated by `cli.py:82-95` for *every* command), `mal-commonlib/model_constants.py`, `aoi.py` + `aois.yaml`, `download/manifest.py`, `cli.py`, `server.py` + `scenario.py`.

**The four specific orphans, with their evidence:**

| Obligation | Owner today | What breaks if unowned |
| --- | --- | --- |
| **AOI data product** — file naming, manifest v3.1, catalog, `validate_completeness` | `docs/specs/data/spec.md` | Restated in six input sections, no owner. The manifest schema is read/written by download, ingest, abm, training, prediction. Six copies of the one thing that breaks on a key rename. |
| **Spatial frame** — AOI, `Scale`, `cells_per_side`, 1 km grid, CRS | `docs/specs/commonlib/spec.md` §4.1 | Pins `(H,W)` for state and env rasters, every stage. `commonlib/spec.md` is ~90% API listing that generated docs would replace verbatim; its conceptual residue is one subsection. |
| **Habitat theory** — `S`, `K`, Beverton-Holt, salinity, aquatic stress | Python `mal-core/src/mal_core/habitat/` mirrored in `habitat_availability.hpp` + `aquatic_stress.hpp` | Computed for ingest, consumed by abm, read for parity diagnostics by scoring D11/D19/D20. Splitting it across ingest's output section and abm's submodel section cuts one equation set along a seam that pack 05 then changes on both sides. |
| **Parameter provenance** — units, literature anchors, "engineering prior" status, changelog | `mal-core/config/model_constants.yaml` + `model_constants-CHANGELOG.md` (comments in Spanish) | Every doc that prints a value becomes a third copy in a second language. See Part 1.8. |

**Additional structural objections the same cluster raised:**
- **`scoring` is not a chain stage** (design, B9): it produces a scorecard consumed by a human or CI, not by another stage. It is an evaluation harness sitting beside the chain. Meanwhile `mal-core/README.md:9-21` lists **8** subcommands, not 6 (`validate-detections` D16, `validate-cases` D25 each have their own output dirs), and ingest is **three** sub-stages (`--stage env|hosts|mobility`, outputs `runs/ingest/`, `runs/hosts/`, `runs/mobility/`). "One doc per stage" is 6, 8, or 11 documents depending on granularity, and that choice silently determines what stays undocumented.
- **The site already publishes a different taxonomy** (design, B9; structural, F16): `docs/index.html` tells a three-stage story (`01 Ingesta & Tensores → 02 Generador ABM → 03 Emulador U-Net`). And the same quantity is stated three ways: site "14 Scorers", `AGENTS.md` "10 scorers", `docs/specs/abm/spec.md` §8 "13 composite dims + 6 gates". A documentation system whose first act is a coherence gate would fail on day one on facts that predate it.
- **The declared purpose is a cycle, and the six phases are a DAG** (zoom-out, F5): the Kelly et al. framework the repo claims to realise has four elements including cyclical re-entry of intervention outcomes and expert knowledge at every stage. No phase consumes a decision, an intervention, or a reported case; the only thing touching real cases is `D25_cases_ghana`, a scorer *inside* the scoring phase. A LaTeX-per-phase set will be internally coherent and externally non-responsive, and the gap will be invisible because no document owns the loop.

**Two competing remedies — Part 3.1.**

---

## 4. The cost is prose, not toolchain; five of six documents have no named reader, and the template being cloned is defective

**Lenses in agreement:** design (B7, B8), codebase-details (F7), zoom-out (F4), comprehension (F1, F4, F5), implementation-readiness (F4, effort table), structural (F19).

**Quantified (codebase-details, F7 — measured from the actual file):** the reference is 2,012 lines / 110,568 B, ~32 pp., with **0 figures**, 12 captioned longtables + 1 notation tabular, 1 pseudocode listing, **21 numbered equations**, 18 bibitems. Scaling by number of formula-bearing processes:

| Phase | Est. LaTeX lines | Tables | Equations | Figures |
| --- | --- | --- | --- | --- |
| abm (exists) | 2,012 | 13 | 21 | 0 |
| scoring | 1,200–1,800 | 19+ | 13–19 | 0 |
| ingest | 800–1,200 | 6–8 | 6–8 | 0–2 |
| training | 500–800 | 3–4 | 3–5 | 1 |
| prediction | 500–700 | 3–4 | 0–2 | 1 |
| download | 400–600 | 3–5 | 0 | 1 flow |

Total ≈ **5,400–7,100 LaTeX lines** versus 2,253 Markdown lines today — **2.4–3.1× the surface**. Effort (implementation-readiness): full concept ~25.5–53 person-days (mid ~38), of which writing the five docs is 7.5–20 days and is the long pole; minimal version ~5.5–10 days. Second-longest tail: tuning the LLM contradiction check, which is unbounded because every false positive costs a review cycle.

**Toolchain is not the problem (implementation-readiness, F4):** the ODD preamble uses 15 packages, all standard (`inputenc, fontenc, babel, geometry, xcolor, booktabs, longtable, array, amsmath, amssymb, listings, fancyhdr, microtype, etoolbox, hyperref`). No `fontspec`, no `unicode-math`, no `minted` (no shell-escape), no `tikz`, no `biblatex`/`biber`. TinyTeX (~120 MB + ~40 MB) suffices; full TeX Live (~5–7 GB) is unnecessary; build is 2 passes, ~2–5 s/doc. This kills the "LaTeX is expensive to build" objection and relocates cost to authoring — which is where every other lens puts it too.

**The template itself is defective (codebase-details F2 and comprehension F4, independently, same three errors):**
- §4.4 cites "the attraction $A_j$ of a cell **(Equation~17)**" — attraction is equation 13.
- §4.4 cites "the attraction $H^{total}_p e^{-d_p/50}$ of an active patch **(Equation~16)**" — oviposition is equation 12.
- §4.7 cites "Beverton–Holt function **(Equation~9)**" — `eq:BH` is equation 7.
- No `\tableofcontents`; not one `\begin{figure}` in 32 pages, for a spatially explicit ABM whose daily order spans four phases.
- Three numbering conventions in one file: `\subsection*{2.1 Entities}` (starred + hand number) vs `\subsection{Basic principles}` (auto) vs `\subsection*{B.1 …}`.
- Zero `\input`/`\include`. Six copies of this file means six divergent 60-line preambles and six copies of a 17-item `thebibliography`.

**Eighteen symbols appear in equations but not in the notation table** (comprehension, F15): `\sigma_{opt}`, `\sigma_{hi}`, `b`, `S_0`, `\alpha`, `p_L`, `s_s`, `\rho`, `\tau`, `a_i`, `k_ref`. Two units are stated wrong *in the table* and corrected only in Appendix A (A.9 `k_ref`, A.10 `daily_mort_basal`). Archetype case: `eq:eggs` is `Binomial(240, 0.5·m_EFD(T))` and the table gives `efd_max_eggs_per_day = 0.5` described as "calibration scale, not absolute EFD" — a reader cannot tell whether 0.5 is eggs·female⁻¹·d⁻¹ or a multiplier.

**Reader misalignment (comprehension, F5/F6; zoom-out, F4):** 20–40 pages is wrong for four of six stages. Download's reader value is one table (15 loaders × fields) plus failure modes; scoring is a formula plus 25 scorer rows. No named external reader exists for download, ingest, training, prediction — the one document with an external standard and an external audience (ODD / Grimm et al., replication) is the one already written. Meanwhile the ABM doc is not 2010-conformant by choice: the repo already ships `odd-2020-template.tex`, and `README.md` lists the 2020 upgrades (Purpose *and patterns*, optional rationale subsections, mandatory "not implemented" declarations, **delta-ODD guidance for modified models** — precisely what packs 03/05/10/11 need). Choosing 2010 is a regression against the project's own notes.

---

## 5. The publishing topology is undecided, "same visual style" is unsatisfiable by construction, and the site has no documentation surface at all

**Lenses in agreement:** design (B7), comprehension (F8, F9), implementation-readiness (F1, F2, F3, F5, F8), structural (F13, F14, F15, F16, F17, F18).

**Strongest concrete objection (structural, F13 / comprehension, F9 — both verified the same thing):** the premise "one landing page links specs" is false. `docs/index.html` navigation has five in-page anchors (`#metodologia`, `#arquitectura`, `#configurador-abm`, `#hoja-de-ruta`, `#colaborar`; footer adds `#avances`, `#emulador-unet`) and **zero links to any document**, while the closing CTA promises "documentación técnica accesibles para toda la comunidad" and links only GitHub. The six-PDF plan builds a docs surface from zero; it does not extend one. Adding one link requires four edits per section: desktop nav, mobile drawer (`#mobileDrawer`), footer row, and both `T.es` / `T.en` dictionaries in the inline JS.

**The style constraint cannot be met by generated HTML (design, B7):** `index.html` is a hand-written ~3,000-line / 200 KB page whose style is 100% inline `<style>` (oklch tokens, `--font-display: 'Iowan Old Style'`), whose i18n is a hand-maintained JS dictionary applied via `innerHTML` in `setLang()`, and which contains an interactive ABM configurator. Sphinx and Doxygen each generate their own `index.html` and CSS. There is no injection mechanism. You will publish three visual languages and call it one site.

**Two artifact topologies with opposite failure modes (design B7 vs implementation-readiness F1 — a real clash, Part 3.3):**
- **Commit PDFs to `docs/`** (required by the legacy `main:/docs` build): pdfTeX embeds `CreationDate` and a trailer ID, so byte-identical rebuilds do not exist without `SOURCE_DATE_EPOCH` + `FORCE_SOURCE_DATE` + a digest-pinned image; ~0.3–0.6 MB × 6 per rebuild, PDFs delta poorly (~2–4 MB per edit); reviewers cannot diff binaries, so a stale PDF after merge is invisible.
- **Pages Actions artifact:** removes binary churn and the bot-push loop guard entirely, but must reproduce `index.html`, the favicons, `site.webmanifest`, `CNAME` and `.nojekyll` or `malariasentinel.com` breaks — a one-shot outage risk on a repo with zero workflows today.

**Additional verified breakages:**
- **8 live URLs 404 on spec retirement** with no redirect mechanism in the repo (no `_config.yml`, no `jekyll-redirect-from`). `docs/specs/abm/spec.md` is currently a live URL serving raw Markdown because `.nojekyll` is present.
- **A CI job cannot write `docs/` on `main`** (implementation-readiness, F2): `main` is protected with 1 approval, dismiss stale reviews, no force-push, no deletion. `GITHUB_TOKEN` is not the maintainer and will be rejected by the ruleset; a bypass PAT turns every doc build into an unreviewed push to `main`. Pushes made with `GITHUB_TOKEN` do not re-trigger workflows, so there is no loop — but a bot push **dismisses existing approvals**, forcing re-approval on every docs sync.
- **Generated trees collide** (structural, F17): Doxygen and Sphinx both emit `index.html` and `search/`; Sphinx emits `_static/`, `_sources/`, `_modules/` (which is why `.nojekyll` must stay). No Doxyfile, no `conf.py`, no `mkdocs.yml` exist, so this is greenfield and will be done wrong by default.
- **ES-first site, English-only artefacts** (comprehension, F15/F16; zoom-out, F4): `<html lang="es">`, ES hero, ES CTAs, ES institutions. An ES reader clicks "Documentación" and lands in English with no switcher and no path to the other five stages. Separately, the bilingual split is itself evidence that this is internal scaffolding rather than a publication programme: two artefacts, two languages, one maintainer, no written rule about which audience sees which.
- **The 200 KB page is already a shadow spec that has drifted three times** (structural, F16): the configurator comments call itself a mirror of `cli.py::abm` (~45 keys × 5 presets), yet its help text still says "(agents/K_MAX)" after contract 4.0 retired `K_max`, says "14 scorers", and says Ghana has "9.466 celdas" against the ODD's 429,229 cells. Add a PDF beside this and the PDF becomes the *fourth* authority — and readers will believe the interactive tool.

---

## 6. Generated technical docs would be structurally complete and semantically empty, and one lens invalidates the cross-language premise entirely

**Lenses in agreement:** codebase-details (F10, F11), implementation-readiness (F6, F7, F8), design (B8).

**C++ (codebase-details, F10 — sampled six headers):** zero Doxygen directives anywhere: no `\param`, `@param`, `\brief`, `\file`, `\return`. The knowledge sits in file-header prose essays (`wire.hpp:1-20`, `habitat_availability.hpp:1-20`, `config.hpp:1-19`, `engine.hpp:1-18`), which Doxygen will not attach to symbols without `\file`. `///` appears before some structs/functions. **Trailing `//` member comments** — which Doxygen ignores (it needs `///<` or `//!<`) — cover `output_contract.hpp:39-55` (`StateCogMetadata`, all 15 fields) and `config.hpp:40-60` (`ContractsCfg`, `HabitatCfg`, `PluvialCfg`, `AquaticStressCfg`). `wire.hpp:150-160` (`AOI`), `:176-186` (`PatchState`), `:196-206` (`HabitatPatch`) have uncommented members. With `EXTRACT_ALL`, expect 1 namespace, ~50 structs, ~150 signatures, **zero parameter docs**, plus `third_party/gif.h` and `font8x8_basic.hpp` and 30 `tests/*.cpp` to exclude.

**And the comments are wrong where it matters (codebase-details F10, implementation-readiness F7 — both found the same three):**
- `output_contract.hpp:3-5` says "band 1 = adult_occupancy, band 2 = host_seeking_pressure"; the code writes `{"adult_patch_count","adult_cell_count"}` (`wire.hpp` `STATE_BAND_NAMES`), and `output_contract.cpp:6-9` says so correctly. Header and implementation disagree inside one module.
- Same header says the sidecar lists `k_max` — retired at contract 4.0.
- `output_contract.hpp:71-73` says the sidecar "must emit them in the order listed in `docs/specs/abm/spec.md`" — a code comment whose authority the concept deletes.
- `tests/test_state_cog.cpp:6-8` says "band 1 description == density / contract_version == 1.1"; assertions actually compare `STATE_BAND_NAMES` at contract 4.0.

**Python (codebase-details, F11):** quality is above average — `from __future__ import annotations`, full annotations, module docstrings everywhere, both Google `Args:` and NumPy `Parameters\n----------` dialects (Sphinx `napoleon` handles both). The obstacle is content: `scoring/llm_scorer.py:3-4` says "the 10 deterministic scorers (D1..D10)" while the registry has 13 composite + 6 gates; `scoring/config.py:11-15` uses `D16_suitability_auc` where the real name is `D16_detection_coverage`; `habitat/constants.py:1-6` documents constants that the module raises `AttributeError` for (`:17-24`); `mal_commonlib/config.py:77-84` `SimParams.r_of()` calls an undefined, unimported `temp_suitability` (`NameError` on call, and the file is 108 lines whose imports are `pathlib`, `dataclass`, `field`). Publishing autodoc as-is publishes four known-false statements.

**Sphinx cost (design, B8):** `autodoc` on `mal_core` needs the scientific stack importable (rasterio, xarray, torch, mesa-geo), making the docs job the heaviest job in the repo, for documentation. `autodoc_mock_imports` is the escape hatch and degrades output to signature soup.

**Premise invalidation (implementation-readiness, F6):** there is no pybind11, so "cross-language linking" has no object (see P4). Scope API docs to the *boundary* — generated CLI reference from `--help`, the `model_constants.yaml` key table, the sidecar key table — plus Doxygen over `include/mal_abm_fast/` only, `EXTRACT_ALL=YES`, `HAVE_DOT=NO`, `GENERATE_LATEX=NO`, `INPUT=include/`, `RECURSIVE=YES`. Drop Breathe/Exhale. Fallback (implementation-readiness F8): skip HTML for v1, publish one generated `docs/api/reference.pdf` from the same LaTeX pipeline — zero new styling, zero second toolchain, 0.5 day instead of 1–2.

**One voice disagrees on value (zoom-out, keep-list):** "Technical API docs generated from source comments … is the one part of the plan that produces an artefact with a real consumer (agents and IDE), provided output lands somewhere greppable and not only in a PDF-adjacent HTML under `docs/`." The disagreement is about *form*, not about whether to do it.

---

## 7. Retiring specs without triage deletes the only executable checks and the only dependency graph, and the fallback manual is already fiction

**Lenses in agreement:** zoom-out (F1, F6), codebase-details (F3, and the anchor table §(b)), comprehension (F12), structural (F9, F12, F24), implementation-readiness (F18), inventive (F3, F4).

**Strongest concrete objection (zoom-out, F1):** the noise comes from ~4 specific sections per spec (the `affects` block, the Metadata version row, the migration section, the narrated contract-version history). The value comes from a *different* section: `§8 Drift check`, which contains actual failing-on-error programs. `docs/specs/download/spec.md` §8 has `discover_downloaders()` key assertions, an `rg`-based loader-signature lint, and a disk-set-vs-registry-set equality check. `docs/specs/abm/spec.md` §8 invokes `mal-core/tests/test_abm_wrapper.py`, which exists — the invariant content is already executable independently of the spec prose. "Specs die, prose replaces them" deletes both halves. Prediction: the four noise sources vanish, the checks vanish with them, and the next contract break lands in code with nothing asserting the downstream readers.

**The thing actually lost is not prose, it is two machine-readable structures** (codebase-details §(b)): `INV-1..INV-16` invariant IDs (cited *from code*: `output_contract.hpp:71-73`, `manifest.py:3`) and the `affects` bidirectional graph — the only place "abm → training/prediction/scoring/data" was declared breaking.

**Sequencing matters more than the decision (zoom-out, F6):** `AGENTS.md`'s calibration section is stale (P3). If `scoring/spec.md` is retired first, the repo's only *correct* description of scoring disappears while its only *surviving* description is fiction. The live package (`mal-core/src/mal_core/scoring/`) matches the spec, not `AGENTS.md`.

**File-level retirement guarantees two authorities for a year (structural, F7):** `abm/spec.md` §5 can migrate in month 1 while §4/§7/§8 stay for months. During that window both files describe the state contract, and `_template.md` Writing-rule 1 ("if they disagree, the spec wins") points the wrong way — so the coherence gate has two conflicting authorities and emits noise, not findings. Required: section-level cut-over (the PR that adds §X deletes §X), a precedence banner on every surviving spec, and a `retire_by:` date per file that CI enforces.

---

## 8. Parameter provenance has no durable home once specs die and `papers/` parks — and hand-typed parameter tables recreate the exact defect the repo already banned

**Lenses in agreement:** design (B5, B12), codebase-details (F8, F9, F16), zoom-out (F8), comprehension (F15), inventive (F2), structural (F3).

**Strongest concrete objection (codebase-details, F8 — a policy contradiction):** `tools/audit_comment_constants.py:1-25` enforces that "a model value is explained in ONE place: its comment in `mal-core/config/model_constants.yaml` … Migrated code must not restate values, units-with-values, provenance strings or `NAME = value` literals in comments." The ODD types **~90 (name, unit, value, provenance) triples by hand** across `tab:habparams`, `tab:aquaparams`, `tab:gonoparams`, `tab:oviparams`, `tab:hostparams`, `tab:dispparams`, `tab:survparams`, `tab:txparams`. Six documents doing this is a second authoritative copy of every constant, unvalidated — and `.tex` is explicitly excluded from the auditor (`EXCLUDE_TOP`, `:60-63`), so the new layer is exempt from R3 while being the most value-dense artefact in the repo. The duplication has no gate *by construction*.

**The `papers/` condition is being relaxed, not satisfied (zoom-out, F8):** `docs/plans/in-process/odd-fixes/01-odd-doc-and-papers.md` step 3 gates removal on docling regeneration "equivalent to the actual papers folder, till this is not achieved the folder can not be removed." `papers/README.md` documents a post-2026-07-03 loss and a per-folder re-download table with `REFERENCES.md` for attribution — the recovery path depends on the folder staying legible in-repo. `scoring/registry.py:8-24` anchors every dimension to a file under `papers/`. The ODD's bibliography has 18 entries, several of which are author-year labels without full records (Costantini 1996, Thomas 2013, Faiman 2020, Okal 2013, Giraldo 2023, Lardeux). `model_constants.yaml` already admits two unbacked priors ("engineering prior sin fuente documentada").

**Defusing change (converged):** (a) generate parameter tables from `model_constants.yaml` at build time into `\input{generated/params-<stage>.tex}`, forbidding hand-typed values — a renamed or removed key becomes an undefined control sequence and **fails the LaTeX build**, which is the "rejection/error" the author wanted at zero LLM cost and impossible to fake; (b) commit a generated `references.bib` / `references.yaml` (key, DOI, one-line relevance) **before** `papers/` parks, so every citation resolves to an identifier; (c) add an explicit "provenance class" column (literature anchor / engineering prior / model definition / scenario default — the ODD's taxonomy, which every lens that saw it called the highest value-per-line artefact in the repo) so unbacked priors are visible rather than buried in YAML comments.

**Language note (design, B5):** `model_constants.yaml` comments, `model_constants-CHANGELOG.md`, and the unbacked-prior notes are in Spanish. Every concept doc that prints a value becomes a third copy in a second language.

---

## 9. `data/` removal is the highest-risk action in the plan and its safety net is fictional — plus two discoveries that make it worse

**Lenses in agreement:** design (B11), codebase-details (F14), implementation-readiness (F13, F14, F15, F16), inventive (F13).

**Strongest concrete objection (design, B11):** the repo's declared recovery path does not exist. `.gitignore:8` says heavy datasets are "re-downloadable via `scripts/restore_data.py`" — `find` returns nothing; the only matches for `restore_data` are in the ignore file's own comment. Tracked content under `data/` is small but **not** re-downloadable by script (`data/moua_2016.pdf`, `data/react/eml.xml`, `data/react/meta.xml`), so "leaves GitHub, kept locally" makes those irrecoverable if the local copy is lost. Three more frictions: `AGENTS.md` lists `data/` as protected and standing project memory says datasets must never be lost; `.gitignore` is also protected, so the ignore changes need explicit interactive approval and an automated stage-by-stage retirement cannot complete unattended; and any `filter-repo` rewrite invalidates the ODD's hand-typed provenance SHA and every commit reference in `docs/plans/`.

**Discovery that raises severity (implementation-readiness, F13):** the manifest — declared the single source of truth by both `data/README.md` and `AGENTS.md` — may itself sit inside a gitignored directory. `.gitignore:20` ignores `data/ghana/` wholesale, and `manifest.py` resolves `DATA_ROOT / aoi / "manifest.json"`. If the manifest was never force-added, "remove data/ from GitHub" removes the inventory too, and a fresh machine has no list of what to re-download. This is checkable in one command each: `git ls-files data/ghana/manifest.json` and `git check-ignore -v data/ghana/manifest.json`.

**Discovery that raises severity (codebase-details, F14):** removal fails *silently*. `manifest.py:20-22` sets `DATA_ROOT = _REPO_ROOT / "data"` as a module constant with **no env override** (unlike `MAL_MODEL_CONSTANTS` in `model_constants.py:29` and `MAL_GADM_PATH` in `aoi.py`). `read_manifest` (`:35-40`) returns `{"aoi":…, "datasets": {}, "expected_files": []}` when the file is missing, so `resolve_dataset_file` returns `None` (`:76-77`) and callers "fall back to conventional-filename discovery". Deleting `data/` therefore produces no error at the manifest boundary, only a confusing failure three stages later. `mal-commonlib/config.py:12-17` adds `RUNS_DIR.mkdir(exist_ok=True)` **at import** (a side effect in a config module) and `:29-31` hardcodes `SRTM_DEM` and `OCCURRENCE` paths. Tests survive (`mal-core/tests/test_manifest.py:18-30` monkeypatches `DATA_ROOT` to `tmp_path`), so CI would not notice.

**Licence blocker (implementation-readiness, F14):** `data/README.md` + `docs/licenses.md` record ODbL 1.0 share-alike on `host_static.nc`, `mobility_*.csr`, `wildlife_host_proxy` (Overture-derived) and CC BY-NC 4.0 on `guf/` and `colombia_vl/`. Public re-hosting is not free; a Zenodo dump is a licensing decision, not a backup. Git is not a backup: `data/ghana/` is ignored, so history contains none of it.

**History rewrite is probably unnecessary — verify before paying for it (implementation-readiness, F16):** if `data/` was always ignored, no 4 GB blob is in history and `git filter-repo` would be pure cost (every SHA changes, every commit reference in `docs/plans/**` and the ODD's "HEAD 5e28644" dangles, all branches/tags force-pushed, PR refs broken). Size-scan first: `git rev-list --objects --all | git cat-file --batch-check='%(objecttype) %(objectsize) %(rest)' | sort -k2 -n | tail -20`. If the largest blob is under ~5 MB, leave history alone.

**Required pre-work before untracking anything (merged from all four lenses):** `MAL_DATA_ROOT` env override in `manifest.py` **and** `config.py`; a loud, actionable `FileNotFoundError` at the manifest boundary when the AOI dir is absent; `git ls-files`/`check-ignore` verification that manifests are tracked (and moving them to `data/manifests/<aoi>.json` if not); `scripts/restore_data.py` written and round-trip-proven on `ghana`; a clean-room script (fresh clone → `uv sync --all-packages` → download → ingest → `abm --days 1`) executed in a container; skip guards for checks that read `data/` or `runs/`; two offline copies with a `sha256sum` manifest committed; `git rm -r --cached data` (never `rm`) in a dedicated PR, with a `!data/README.md` negation so the pointer survives.

---

# Part 2 — Converged themes where the lenses agree (usable as design constraints)

**T1. Generate facts, write semantics.** Every lens that looked at the template independently concluded that the churn is a *template bug*: `docs/specs/_template.md` spends ~80% of its surface on numbers, names, shapes, versions, API signatures and invariants (classes 1–3) and ~5% on why / non-goals / failure modes / equations (the class that survives a refactor). The doctrine to adopt, in the words of one lens: *values and contracts must be machine-checkable and generated; prose may only carry semantics that survive a refactor untouched — everything else is the old spec system with more LaTeX.*

**T2. The blocking tier must be deterministic; the LLM tier must be advisory.** No lens argued for LLM-blocking. Design's formulation is the crispest: "You keep the rejection/error the author asked for, restricted to the cases where rejection is defensible." Zoom-out's formulation is the governance version: "an AI can inform, not veto; a human can violate, but leaves a trace" — implemented as a `Coherence-Waiver:` commit trailer so silent drift becomes chosen drift.

**T3. Move the ODD out of `.cache/` before anything else.** Three lenses independently made this the first step, and it is the only step that can be verified in one command: `git mv` the `.tex` + templates into `docs/concepts/`, then prove `latexmk -pdf` builds them untouched. Until a `.tex` is tracked, "PDFs compiled in CI" has no input.

**T4. Write before the packs, but tag the half-life.** Every lens that examined the sequencing said "yes, but" — and the "but" is a mechanism, not a retreat: a per-section status macro (`\asbuilt{<sha>}` vs `\target{PACK-05}`), a mandatory dated "Pending decisions" paragraph in the scope section, and a rule that a pack PR *must* touch the section it redefines. This converts pack churn from noise into signal and gives the gate a mismatch budget.

**T5. Ownership matrix before a seventh document.** Every lens that mapped the code found the same five orphans. All of them proposed *some* single-owner mechanism; two proposed a `shared/` document, one proposed a `\input` fragment set, two proposed an ownership matrix with no new file. See Part 3.1.

**T6. The repo needs a truth pass before it needs a checker.** Six lenses independently found stale claims in `AGENTS.md`, `README.md`, `docs/README.md`, `docs/index.html`, `wire.hpp`, `output_contract.hpp`, `tests/test_state_cog.cpp`, and `docs/specs/*`. Building a gate on top of a baseline that already lies produces a gate whose first act is to report the plan's own debt. Implementation-readiness puts it most sharply: make the first docs PR a pure "truth pass" with no new concepts.

**T7. Every shared text is an `\input`, never a copy.** The determinism argument is mechanical: one copy of the spatial frame and the contract matrix, `\input` into six PDFs, so the six repeat them *verbatim from one file* and any document can still be read alone.

**T8. The ODD's parameter-table-with-provenance-class is the single highest-value artefact in the repo and must survive.** All six lenses that read the ODD said this in different words. The taxonomy — literature anchor / engineering prior / model definition / scenario default — is the thing the spec system never had.

---

# Part 3 — Clashes between lenses (do not smooth these over)

## 3.1 How to house the orphans: seventh document vs `\input` fragments vs ownership matrix

- **codebase-details (F5):** "add a seventh document, `docs/concepts/shared/`, for the substrate (AOI, model constants, habitat theory, manifest). Without it, six documents will each re-describe `k_habitat` and each will drift."
- **implementation-readiness (F17):** "add a seventh document `docs/concepts/data-model/` (owner: the manifest/naming contract) and fold `commonlib` into a short appendix of it. Otherwise the decision 'specs die' silently deletes the one contract the agent guide points at."
- **structural (F3):** reject the seventh silo: "**ownership matrix, no seventh document.** … For the two genuinely cross-cutting items (spatial frame, contract matrix), do **not** create a document — create an `\input` fragment. A fragment is not a silo, and it mechanically guarantees the invariant instead of promising it."
- **inventive (F7):** similar, via `\input{docs/concepts/shared/lineage/<artifact>.tex}` per produced/consumed artefact plus one lineage chapter in the ABM doc.

**Why it matters:** this determines whether the concept has six documents or seven-plus, and whether "one document per stage" stays literally true. Both sides agree on the failure (habitat restated six times); they disagree on whether the fix is a new unit or a mechanical include. A defensible synthesis exists — the ownership matrix *is* the authority, and the fragments are its rendering — but it must be chosen explicitly, because the two options have different review surfaces (a `shared/` doc gets reviewed as a document; a fragment gets reviewed inside six documents).

## 3.2 Write-to-target vs write-as-built-with-provisional-tags

- **design (B3):** "Invert leadership for the ABM document only. Write it against the *post-pack target* design and treat packs 02/03/05/10/11/12 as the implementation of the document, not as its future corrections. The document then absorbs churn as *intent* rather than as *error*, and you get a second benefit: the doc becomes the thing reviewers check the packs against."
- **inventive (F8):** "**Write from the packs, not from the code** — the pack files already contain the intended mechanics verbatim; the doc's Processes section for those areas should describe the *target* mechanism and carry `% status: provisional (pack 03)`, rendered as a visibly coloured box." — closer to design, but with the mechanism being the *pack files* as source, not the author's intent.
- **comprehension (F7):** "mandatory per-document **'Pending decisions'** section listing the packs and the exact sections they will invalidate; mark those sections in the body." — as-built plus explicit debt.
- **implementation-readiness (F20):** "add a per-section status macro now — `\asbuilt{5e28644}` vs `\target{PACK-05}` — and only freeze sections no pack touches (Purpose, Process overview, Input data, Initialization are largely stable; Entities, Design concepts, Submodels are not)."

**Why it matters:** writing to target makes the document an authority over the code for months, which the author explicitly disclaimed ("coherence verification, not a source of truth"). Writing as-built publishes something knowingly false. The four prescriptions occupy different points on that line and the author must pick one; the status-macro mechanism (implementation-readiness, F20) is the only one compatible with both, because it lets a section be *either* and says which.

## 3.3 Committed PDFs vs Pages artifact vs releases

- **design (B7):** "Decide (b) now: add one Pages workflow that builds PDFs + a single static-site generator into one artifact and deploys it. Publish PDFs as site artifacts, never as committed binaries."
- **implementation-readiness (F1):** "decide now — releases for versioned PDFs, `docs/concepts/` only for a small 'latest' copy per stage (≤ 3 MB total). Do **not** migrate Pages source in this project; it is an unrelated, riskier migration that the concept does not require."
- **structural (F14):** states the constraint both are reacting to: "PDFs must be **committed** to `docs/` to be servable — the 'PDFs from CI' plan silently requires a Pages workflow that replaces the legacy build." Then leaves the choice to the author with the redirect-stub requirement.
- **comprehension (F8):** adds a fourth option — "`.tex` **is** the canonical in-repo artifact; CI emits PDF *and* a generated Markdown/plaintext twin; the site links both; only the twin is greppable-by-default for agents."

**Why it matters:** these have incompatible consequences for the workflow count, the git history, the site's uptime risk, and whether the docs are readable by an agent at all. Implementation-readiness is the only lens that separates "PDF versioning" from "PDF publishing" and that flags the site-migration risk as out of scope; design is the only lens that treats the topology as a prerequisite rather than a downstream detail. This is the single largest unresolved infrastructure decision.

## 3.4 One formal document per stage vs tiering the corpus

- **design (B8):** "Tier the corpus explicitly. Tier A (formal LaTeX + PDF + ODD + gate coverage): `abm` only. Tier B (in-repo markdown, no PDF, no gate): `ingest`, `scoring`. Tier C (defer until a second contributor exists): `download`, `training`, `prediction`. … Files that should be **dropped** rather than deferred: the six-way template set."
- **zoom-out (F4):** "Invert the default: markdown-first under `docs/concepts/<phase>/` with the same question set, and keep LaTeX+PDF only where an external consumer is *named* … Each doc declares `audience: internal | external` in front matter, and CI publishes only `external`."
- **comprehension (F5):** "size is a consequence of the question set; state an expected range per typology (download 6–8, ingest 8–12, abm 25–40, scoring 10–15, training 8–12, prediction 6–8) and treat overrun as a smell."
- **Against, from the decisions:** LaTeX for all six is taken. Also **implementation-readiness** treats the six-way split as sound ("Six docs for six stages is not arbitrary") and **structural** treats it as sound ("Stage as the unit is right").
- **The author's own hedge:** the scope of experiments and of any top-level system document is the author's call. Tiering is adjacent to that, not a re-litigation: it changes *how many documents get the full treatment*, not *what a document is*.

**Why it matters:** this is the only clash where a lens asks the author to *reduce scope* rather than change mechanism, and it is backed by the strongest cost number in the brief (7.5–20 person-days of authoring, for 5 documents with no named reader). If it is rejected, the rejection should be explicit and recorded, because every lens that did the cost arithmetic raised it.

## 3.5 Is the ODD a good template at all?

- **comprehension (F3):** "The ODD solves a different problem than the one named. It answers 'is this model complete and credible?' for a scientific reader, and explicitly refuses the other three questions the specs did answer. Its own words: *'It describes the model, not its command-line interface'*. … The ODD has **zero runnable examples** and no module map."
- **codebase-details (F7):** quantified: §3 (process overview + pseudocode + scheduling table) and §7 (equation → parameter table → rationale → consequences) transfer; §2 (entities/restart test) and §4 (9 of 11 design concepts) do not; §6 is *demoted* by the concept's own decision even though it is the one section every stage could use verbatim.
- **Against, from several lenses:** comprehension (F2) calls the protocol/transcription separation "the real fix"; structural (F19/F20) treats the ODD as a structural asset while insisting it be refactored into a `.sty` + slots; inventive (F9) argues the *rules* matter more than the section list.

**Why it matters:** "the ODD is the authoritative example" is doing two different jobs — *this is what good looks like* (all lenses agree) and *this is the template for six documents* (comprehension, zoom-out, and codebase-details all object, with measurements). The resolution the lenses converge on without saying so identically: a universal spine plus an ODD overlay used only for `abm`.

---

# Part 4 — Sound, keep it (consensus)

1. **Killing the `affects` block, the per-spec version policy, the migration section, and the "the spec wins over code" doctrine.** Four lenses independently identified these as the actual noise generators. `_template.md` writing-rule 1 ("Spec is the contract. Code is the implementation. If they disagree, the spec wins; the code is the bug") is the doctrine that produced the pain; killing it is the fix, independent of format.
2. **I/O as one section among others, never the skeleton.** This is already ODD element 6's precedent and the exemplar's own scope statement. Keep it — but let the generated contract artefact carry the values so the I/O section stays a page.
3. **ODD 2010/2020 for the ABM specifically.** Right document, right reason: an external standard, an official guidance checklist, an external audience (replication), and no official LaTeX template — owning one is an asset rather than a duplication.
4. **LaTeX + PDF for the ABM.** A PDF is the correct distribution medium for a citable model description; notation tables and pseudocode are genuinely better in print; the preamble is all-standard, so the build really is cheap.
5. **"Not every stage gets an ODD."** Correct, and the most important half of item 3 — ODD is model-specific and would produce empty scaffolding elsewhere.
6. **Framing the gate as coherence verification, not source of truth.** Right instinct, and it is what makes the two-tier design possible. It needs a written precedence rule to be operational: values → `model_constants.yaml` wins; contracts → the generated contract artefact wins; semantics → the concept doc wins; on contradiction the lower authority is the bug.
7. **Unit = pipeline stage.** It matches `docs/specs/` and the `malariasim` subcommands 1:1, so the maintainer's mental map survives the reorg. It documents the build graph rather than the decision loop, but it is the cheapest correct granularity.
8. **Writing before the four packs.** Defensible *if* the stable zone is separated from an explicitly labelled implementation snapshot — see T4.
9. **`data/` out of GitHub.** Already ~95% true (16 tracked files against 4.0 GB). The intent is right; the sequencing and the missing restore path are wrong.
10. **Generated technical API docs from source comments.** Sound and cheap, and it is the part of the plan with a real consumer (agents, IDE) — provided the output lands somewhere greppable, the C++ comment truth is fixed first, and the stale-claim files are blocklisted.
11. **The "consequences worth stating" discipline and the non-goals section.** Called out as the single most durable paragraph type in the document — it is what turns description into understanding, and the ODD does it well.

---

# Part 5 — Minimal viable path (synthesized; disagreements noted)

Ordered, each step verifiable before the next. This is a synthesis of five lenses' minimal versions; they agree on the first four and diverge afterwards.

1. **Truth pass, no new concepts.** Fix `docs/README.md`, `README.md`'s `mal-ghana-sim` claim, and the six contract-defining source headers (`wire.hpp`, `output_contract.hpp`, `habitat_availability.hpp`, `habitat_engine.hpp`, `coordinator.hpp`, `config.hpp`). One PR. Exit: no claim in these files is contradicted by the tree. *(T6; implementation-readiness F21, F7)*
2. **`git mv` the ODD out of `.cache/`.** `.tex` + templates into `docs/concepts/`; prove `latexmk -pdf` builds them unmodified. One commit. Exit: a tracked `.tex` compiles. *(T3; three lenses)*
3. **One shared page before six documents.** A 7–9 slot skeleton (Purpose/scope + provenance; Notation; Entities & state variables; Process overview & scheduling; Design constraints; Initialization; Input data; Submodels incl. "Observation and outputs"; Appendices A implementation notes, B provenance/versioning, C executable checks) plus per-stage `required_extra` inventories. **The ABM doc maps its 7 ODD elements onto this skeleton in a table** — it does not abandon ODD. Exit: one page exists and the ODD's mapping is written. *(design B1, structural F20/F21, codebase-details F7)*
4. **One generated artefact + one checker, green on an empty doc set.** `docs/concepts/_contracts.yaml` (artifact → producer → consumers → version → compatibility rule → band/variable names → sentinel) and a small `tools/check_concepts.py` implementing deterministic checks 1–7 from Part 1.1, run by the repo's first workflow. Also: a generator emitting parameter longtables and per-key macros from `model_constants.yaml` via the existing pydantic models, with `git diff --exit-code` on regeneration. Exit: `git log` shows a green run before any document exists. *(design B2/B4, inventive F2, implementation-readiness F10)*
5. **Pilot on the smallest stage, not the largest.** Comprehension and inventive both insist on this independently: derive the question set from what the existing spec already answered, apply it to `download` (or `download` + `ingest`), and generalise the shared template only if the pilots agree on ≥70% of headings. This contradicts the author's stated "one subagent per phase proposing the question set" before any document exists — see Part 6. Exit: one non-ABM document, reviewed, with its typology derived rather than invented. *(inventive F6, zoom-out F10, comprehension F5)*
6. **One PDF build for `abm` only, published, linked once.** Decide the topology first (Part 3.3). Add one `#documentacion` section to `index.html` with a stage table; add the anchor to nav + drawer + footer + both i18n dictionaries in the same commit. Exit: a reader can reach a PDF from the landing page in both languages. *(design B7, implementation-readiness F1/F5, structural F13)*
7. **Advisory contradiction review.** `continue-on-error`, bot-loop guard, fork-PR degradation stated in the comment ("semantic check skipped (fork)"), and secret-absence handled as `neutral`, not `failure`. Exit: 20 PRs of history with a measured false-positive rate before anyone considers making it required. *(implementation-readiness F11/F12, zoom-out F9)*
8. **`data/` last, and separately.** All the pre-work in Part 1.9, then `git rm --cached` in a dedicated PR. Do not rewrite history until a size scan proves it is needed. *(design B11, implementation-readiness F13–F16)*

**What to defer:** the five other conceptual documents; the per-typology template set beyond inventory lists; Doxygen/Sphinx HTML; the coherence gate as a required check; PDF determinism (use a `pdftotext -layout` content hash, not a byte hash).
**What to drop:** committed PDFs (pick artifacts or releases); `affects`-style cross-references in any form; the goal of a uniform visual style across hand-written and generated pages; hand-editing the docs index (generate it).

---

# Part 6 — Where the reviewers contradict the author's stated next steps

Flagging these separately because they are the only places where the concept's *process* (not its target) is challenged. All are stated once; none is re-litigated.

1. **"One subagent per phase proposing the question set" is premature generalisation.** Inventive (F6) and zoom-out (F10) independently: the ABM typology already exists and is answered; `docs/specs/_template.md` already records the questions this project found useful (§1 Objective, §2 In-scope, §3 Out-of-scope, §9 Examples survive; §7 Migration, §8 Drift check die; the rest migrate); the sidecar contract already enumerates what a stage must declare. Derive, do not invent. Decision rule offered: generalise only if two pilots agree on ≥70% of headings.
2. **"Rejection/error on the PR" is only achievable deterministically.** Every lens that examined LLM-blocking rejected it. The request survives intact if "rejection" means *absence and anchor* checks, and if semantic contradictions are advisory with a recorded waiver.
3. **"Write the ABM doc first, before the packs" needs a mechanism, not acceptance.** See Part 3.2. Without a status macro or a pending-decisions section, the document is wrong on day one in its two most expensive sections.
4. **"Not every stage gets an ODD" is right, but the six-way template set should be dropped, not deferred.** Design (B8) is explicit: the templates are the artefact most likely to reproduce the spec system's failure, because a template authored and answered by the same agent, reviewed by nobody, is a formatting convention with 100% pass rate.
5. **`papers/` "parked" relaxes a recorded gate.** `01-odd-doc-and-papers.md` step 3 conditions removal on docling equivalence. If parked anyway, a generated `references.bib` must land first (Part 1.8).

---

# Part 7 — Falsifiable predictions (cheap tests of this brief)

From the lenses, deduplicated. Each is a measurement someone can run.

1. **If a rename-only PR after the reorg still forces doc edits, the triage/generation step failed.** Measure with `git diff --stat` on such a PR. (zoom-out)
2. **If six months of pack churn produces zero detected contradictions under the deterministic scheme, then "prose rots silently" is false for this repo.** (zoom-out)
3. **If the drift-check scripts had been run once, they would already have failed** — `abm/spec.md` §8 asserts `startswith('2.')` against a v4.0 contract. The claim "the specs were maintained" is falsifiable in one command. (codebase-details, comprehension)
4. **A Doxygen build on `include/mal_abm_fast/` today emits zero parameter docs.** Count `\param`/`@param` occurrences: predicted 0. (codebase-details)
5. **A name-presence checker passes on the training/prediction contradiction** (4-of-7 env channels) because all seven names exist. If a semantic gate is claimed to catch it, test that exact diff. (codebase-details)
6. **If a named external reader (funder, ministry, journal reviewer) materialises, the markdown-first default should flip for that document — and only that one.** (zoom-out)
7. **The site's own content will fail the first coherence gate**: "14 scorers" vs 13+6, "agents/K_MAX" vs contract 4.0, "9.466 celdas" vs 429,229. (design, structural)

---

# Part 8 — Finding index (one line each, traceable to the final brief)

| Lens | ID | Sev | One-line |
| --- | --- | --- | --- |
| design | B1 | blocker | Six docs authored before a shared skeleton exists; ODD's 7 elements do not apply to five of six |
| design | B2 | blocker | Killing specs converts the only machine-checkable artefact into prose at the boundary whose failure is silent |
| design | B3 | blocker | Writing before packs lands makes the two most expensive sections doubly wrong |
| design | B4 | blocker | A blocking, nondeterministic gate on a one-person repo will be turned off (3 independent mechanisms) |
| design | B5 | major | Four content classes homeless: manifest, commonlib, habitat theory, parameter provenance |
| design | B6 | major | Template authored and answered by the same agent, reviewed by nobody, is a formatting convention |
| design | B7 | major | Publishing topology undecided; "same visual style" unmet by construction; inline-CSS single page |
| design | B8 | major | ~70 k tokens of corpus, 6 docs + 6 templates + 2 generators + gate, one maintainer, no reader |
| design | B9 | major | Stage taxonomy does not describe the system; site publishes a different one; 14/10/13 scorer disagreement |
| design | B10 | major | No versioning/immutability; PDFs assert a commit SHA typed into prose |
| design | B11 | major | `data/` removal highest-risk, under-specified, safety net fictional |
| design | B12 | nit/major | Parking `papers/` de-cites the documents |
| design | N1–N3 | nit | `docs/README.md` already stale; ODD not in repo; dangling refs already the norm |
| codebase | F1 | blocker | Authoritative example is gitignored |
| codebase | F2 | blocker | ODD cross-refs wrong (Eq 17→13, 16→12, 9→7), literal numbers not `\eqref` |
| codebase | F3 | blocker | Coherence gate is the same unbuilt mechanism the specs died of; no drift agent, no workflows, `run_all_tests.sh` always exits 0 |
| codebase | F4 | blocker | The artifact class being kept is the one that decays; 7 live examples of prose rot |
| codebase | F5 | blocker | ~1/5 of production modules belong to no stage or several; habitat/constants/AOI/manifest homeless |
| codebase | F6 | major | ODD template poor for five of six stages; only §3 and §7 (and App A/B) transfer |
| codebase | F7 | blocker | Training/prediction contradict themselves today: 4 of 7 env channels, NoData→0.0, band-index reads, no contract check |
| codebase | F8 | major | Hand-typed parameter tables recreate the defect R3 banned; `.tex` exempt from the auditor |
| codebase | F10/F11 | major | C++ has zero Doxygen directives, trailing `//` invisible, stale header prose; Python docstrings would publish 4 false statements |
| codebase | F13 | major | Output "contract" is four glob heuristics across three consumers |
| codebase | F14 | major | `data/` removal fails silently (no env override, manifest returns empty skeleton); restore script absent |
| codebase | F15 | major | First-of-its-kind CI asked to do four jobs; 8 spec URLs 404 with no redirect mechanism |
| zoom-out | F1 | blocker | Swapping doc types instead of triaging section types loses the only runtime-enforced parts |
| zoom-out | F2 | blocker | Six I/O sections re-create N-way duplication of the one contract that must stay single-owner |
| zoom-out | F3 | blocker | Prose drifts silently; the only detector is prose judgement; `docs/README.md` already lies |
| zoom-out | F4 | major | Publication costume unless a reader is named; one PDF justified, five not |
| zoom-out | F5 | major | Six phases describe the build graph, not the SDSS cycle; the decision loop has no home |
| zoom-out | F6 | major | Killing scoring spec first leaves `AGENTS.md` fiction as the only surviving description |
| zoom-out | F7 | major | Reproducibility is not a documentation problem; the artefact that would answer it is scheduled for deletion |
| zoom-out | F8 | major | Provenance has no durable home; parking `papers/` contradicts a recorded gate |
| zoom-out | F9 | blocker | Gate inverts the project's own non-gating-LLM rule and creates an agent veto over the only human |
| comprehension | F1 | blocker | ODD multiplies the code-coupled surface 5×; Appendix A is as code-coupled as any invariant |
| comprehension | F3 | major | ODD answers a different question; no runnable examples, no module map |
| comprehension | F4 | blocker | Flagship example has three wrong equation refs, no TOC, zero figures |
| comprehension | F5 | blocker | 20–40 pages per phase wrong for 4 of 6 stages; uniform targets produce padding |
| comprehension | F7 | blocker | Publishing known-false formal PDFs; >40% of ABM mechanism sections affected |
| comprehension | F8 | major | Honest losses: table extraction mush (tables are half the ODD's content), no runnable blocks, no anchors, LaTeX needed to edit a sentence |
| comprehension | F9 | blocker | Landing page links zero documents; nav is anchors-only |
| comprehension | F11 | blocker | Six-stage list drops `data`; two contradictory coastal-buffer numbers already live |
| comprehension | F13 | blocker | Pseudocode drift proven: 4 of 15 Appendix A notes say the mechanism is not what the code does |
| comprehension | F14 | blocker | Gate has nothing falsifiable without anchors |
| comprehension | F15/F16 | major | 18 symbols missing from notation, 2 units wrong in-table; ES-first site breaks at conversion |
| impl-ready | F1 | blocker | Artifact home undecided; three topologies with opposite failure modes |
| impl-ready | F2 | major | CI cannot write `docs/` on main; bot push dismisses approvals |
| impl-ready | F6 | blocker | No pybind11 — cross-language linking has no object; scope to the boundary |
| impl-ready | F9 | blocker | No path→doc table exists; the only source is the `affects` block being deleted |
| impl-ready | F10–F12 | major | Two tiers required; secrets/fork/dependabot degradation; making it required breaks forks and bot commits |
| impl-ready | F13–F16 | blocker | Manifest may sit inside a gitignored dir; 4 GB single-laptop + licence block; restore untested; rewrite probably unnecessary |
| impl-ready | F17 | blocker | `data` and `commonlib` specs have no successor document |
| impl-ready | F18 | major | Prose dies cleanly, checks do not; ordered retirement with per-PR exits |
| impl-ready | F19 | major | No verification loop catches a wrong equation; propose numeric anchor tests |
| impl-ready | F20 | blocker | As-built snapshot + pre-pack authoring = wrong on day one and again per pack |
| structural | F1 | blocker | Same fact asserted three times with three values; no home is authoritative |
| structural | F3 | blocker | Five obligations homeless; proposes ownership matrix + `\input` fragments, no seventh doc |
| structural | F6 | blocker | Five documentation surfaces coexist, none indexed; five in-code documents unlisted |
| structural | F7 | blocker | File-level retirement guarantees two authorities for a year |
| structural | F9 | major | `affects` blocks are dead metadata with no successor; blast radius uncomputable afterwards |
| structural | F10/F11 | blocker | No path→doc rule; proposes `map.yaml` with 10 rules + totality + dead-glob checks |
| structural | F13–F17 | blocker | Nav anchors-only; legacy Pages 404s and raw sources; three visual languages; index.html is a drifted shadow spec; generated trees collide |
| structural | F19–F22 | blocker | ODD is a 1,830-line monolith with no `\input`; needs `.sty` + slot spec + pending-redesign register |
| structural | F23–F25 | major | Packs cite PDF page numbers; `plans/` is a third authority; workflow `paths:` is a second drifting map |
| inventive | F1 | blocker | Authoritative example gitignored; move it before designing templates |
| inventive | F2 | blocker | Generate LaTeX macros from `model_constants.yaml`; undefined control sequence = the rejection the author wants |
| inventive | F3/F4 | major | Salvage `affects` → `lineage.yaml`; salvage `INV-<n>` as labels |
| inventive | F5 | major | Three gate designs, none "LLM reads the PDF": anchor ledger, generated no-op gate, LLM as narrator only |
| inventive | F6 | major | Question set derivable from existing artefacts; apply to `download` first |
| inventive | F8/F9 | major | Write from the packs with provisional boxes; five binding template rules |
| inventive | F10–F13 | nit | Scope API docs to public surface; one publication row; don't depend on the memory graph; two stale facts |
