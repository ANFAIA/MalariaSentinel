# Review of the `download` conceptual document — the loop, run once

> **Status:** plan (executed) — the reader's 35 annotations were applied to
> the `download` document: 34 fixed in the document, one (A27, the licence
> limits) deferred to `docs/licenses.md`, which is the record of them.
> **Stage:** the pilot of the plan's Stage 5 (CUJ-4 / CUJ-5).
> **Reader:** one reader with no code profile (a domain scientist who has
> never opened the repository). The annotations are theirs, unedited.
> **Date:** 2026-11-16.

## What this is

The plan's Stage 5 demanded that one document be "revised once through the
full loop": read by someone without a code profile → the annotations become a
plan → the plan names the section each item invalidates → the document is
revised in a commit. The loop had not been run for any document. This is that
loop, run on `download`, and it is the pattern the other five documents
follow.

The reader's report had 35 annotations. This plan is the step between the
annotations and the revision: for each annotation, the section it lands in,
what the reader could not do because of it, and the decision — **fix**, with
the sentence the document must carry; **defer**, with the reason and where it
is recorded; or **not a defect**, with why the reader's confusion is theirs.

Two things this plan does not do: it does not change what the code does, and
it does not invent facts. Where an item needs a code fact the document does
not yet carry, the item says so and the revision must verify it against the
code before writing it.

## The reader's three unanswerable questions

These are the reader's summary, and they are the acceptance criterion of the
revision: a reader who has read the revised document must be able to answer
them.

1. **What is the target grid, and how do I compare my inputs to it?** The
   AOI's ground resolution was never stated, the cell shape was never
   stated, and no product's unit was stated.
2. **What do I have to download to make the model run?** The flag that
   claims to say so gates nothing; the default profile was not printed; the
   slot table mixed downloaded and derived keys; the ABM's resolved paths
   were never mapped back to their producers.
3. **Can I trust the numbers that came out?** The stage does not check that
   what it wrote is on the AOI grid; the thresholds were cited by location
   rather than valued; missing components and half-failed products fail
   silently, and the document never says what the reader should check.

## The annotations

Column "Section" names the section of `docs/concepts/download/download.tex`
the item lands in — that is what CUJ-4 requires: the plan names the section
each item invalidates.

| # | Section | What the reader could not do | Decision |
|---|---|---|---|
| A1 | §1.1 "What question the stage answers" | Not know what a CRS or "the shape" is, in the one sentence that says the grid is *not* verified | **Fix.** Define both in place: the CRS is the map projection the grid is defined in; the shape is the (rows, columns) of the array. Add the consequence: a loader could return an array on the wrong grid and nothing would notice. |
| A2 | §1.1 | Not know what the manifest or a manifest key is, at the first mention of either | **Fix.** Gloss both at first mention: the manifest is a JSON file listing, per dataset, the file on disk that holds it, under a unique key; the manifest key is that unique key. |
| A3 | §1.2 "What the stage is *not* for" | Not know what a NetCDF, a GeoPackage, a tensor, `env` or `habitat` is — the negative-purpose argument depends on it | **Fix.** One parenthetical each: NetCDF (a multi-dimensional array file), GeoPackage (a spatial database file); and one line on what `env` holds (daily environmental drivers per cell) and what `habitat` holds (static per-cell habitat classes). |
| A4 | §2 "Entry points" | Not know what `--months` does, for which loaders, or what the resulting file covers | **Fix.** State in §2 which loaders honour `--months` and what the file then covers. The runner passes `months` to every loader it calls (`download/runner.py:128,165,194`); a loader that ignores it is not filtered. Say which ones use it. |
| A5 | §2 → §3.6 | Not know what a bare `malariasim download --aoi ghana` fetches — the answer is 200 lines away, behind the loader machinery | **Fix.** A short paragraph in §2: what a default run fetches, and what it does not, pointing at §3.6 for the derivation. |
| A6 | §3.2 "What a loader declares" | Not know what a "credential family" is, or how many there are | **Fix.** One sentence: the four families are `cds` (Copernicus), `earthdata` (NASA), `earthengine` (Google) and `none`; the family is what a loader declares and what the runner probes. |
| A7 | §3.3 "The registry table" | The description of the generated table's columns and the reading note after it disagree; a reader looking for a manifest key reads the wrong column | **Fix.** Correct the description of the generated table's columns in the document (the table itself is generated; the prose is not). If the column genuinely lists the output names, say so where the table is introduced, not only in a note below it. |
| A8 | §3.4 / §4.2 | Cannot compare any source resolution to the target, so cannot judge whether a reduction is a reduction | **Fix.** State the AOI's ground resolution and cell count in §4.2 (the resolution is `\codeconst{ingest.cell_size_m}`), and put the target resolution in the §3.4 table's caption. |
| A9 | §4.2 "How the grid is derived" | Cannot compute the grid's (height, width), cannot size the env tensor, cannot sanity-check a file | **Fix.** A worked example: the AOI's bounding box, at the stated resolution, gives a grid of H×W cells of R×R metres; state whether the cells are square. The cell count is a reading of the delivered grid, not a model constant — if the document states it, it belongs in the appendix of readings. |
| A10 | §4.2 | Cannot tell what the cells outside the AOI's footprint contain | **Fix.** One sentence: the grid covers the bounding box; the coastline land mask is the artefact that carries the footprint; and say what each product does over the ocean. |
| A11 | §5.1 "Where it lives and who writes it" | Not know where the manifest goes when `--output-dir` points elsewhere, or whether the paths inside it are absolute or relative | **Fix.** State it: the manifest path is derived from the repository root (the directory that contains `.git`), independently of `--output-dir` (`download/manifest.py:18-24,33`), and the paths it records are relative to the AOI directory (`manifest.py:92`). Verify both against the code before writing them. |
| A12 | §5.2 "The dataset entry, field by field" | Not know what `csr` is, and which product uses it | **Fix.** A parenthesis: `csr` is the compressed-sparse-row file the mobility builder writes (`ingest/mobility.py:99-110`), which is a derived product, not a downloaded one. |
| A13 | §5.7 | Not know where the "requested years" come from, or what completeness means when no year list is given | **Fix.** State the signature and the default of the completeness check, and say what it does when no year list is passed. |
| A14 | §5.4 / §5.6 / §5.7 | Not know the three checks (the `expected_files` union, per-entry existence, period coverage) or which one the verdict rests on | **Fix.** One sentence that states all three together. |
| A15 | §5.5 versus §1.2 / §11 | "Product" means the upstream dataset in one place and the output name in another | **Fix.** Reserve two words: "source dataset" for the upstream thing, "output" for what the stage writes. Apply consistently in the places the reader named. |
| A16 | §13.1 versus §5.2 | Cannot tell when a time-series entry is keyed by year and when by dataset key | **Fix.** State the rule in one sentence. |
| A17 | §7.3 consequence 6 versus §14.2 | "Re-fetches what is missing" reads as skip-if-present; the next clause says the opposite | **Fix.** One unambiguous sentence: the runner re-executes every selected loader and overwrites the product; it does not consult the manifest first. Remove the contradictory phrasing. |
| A18 | §9.2 and throughout | No product's unit is stated anywhere: rainfall, salinity, NDVI, livestock density, the JRC fraction, the wildlife proxy | **Fix.** A table — product, variable, unit, temporal resolution, spatial resolution — for the products the stage writes. The native-grid column is already generated; the units come from the loaders' own declarations and must be read from them, not from memory. This is the stance note's S2 and the reader's first unanswerable question. |
| A19 | §9.1 and §5.5 | A file named `_daily.nc` may hold six-hourly data; the correction is 500 lines later | **Fix.** Carry the caveat where the naming patterns and the write paths are defined, and keep the appendix entry. |
| A20 | §10.2 | Not know what the "1 km aggregation" is, or whether it is the AOI cell size | **Fix.** One sentence: the modal-label raster is requested at 100 m and the areal fractions are computed on the AOI's 1 km grid (state the grid's resolution — it is the AOI's, and now it is stated). |
| A21 | §10.3 | The JRC occurrence threshold is cited by location but never valued — a threshold of 10 % and one of 50 % give different wetlands | **Fix.** State it: `\codeconst{ingest.jrc_occurrence_threshold_pct}` per cent occurrence. |
| A22 | §10.2, §12.1 | Not know what the NoData sentinel *is*, whether the engine shares it, or what the epsilon floor does to a cell with one valid pixel | **Fix.** One sentence: the sentinel is a reserved out-of-range value, shared with the simulation engine, that downstream code must treat as missing; the epsilon floor bounds the divisor. |
| A23 | §10.4 | "warper", "fillet", "distance transform" and "sum-preserving rectangle sum" are names, not rules | **Fix.** Plain-language glosses in the table's cells: each destination cell takes the value of the nearest source cell with data; each destination cell sums the overlapping source cells weighted by overlap, so the total is preserved. |
| A24 | §10.4 | "Smooths across the coast" is a systematic temperature bias at the coast, where the population is | **Fix.** One sentence: the coastal cells carry a sea-surface contribution, and say whether anything downstream corrects it (verify against the code before writing). |
| A25 | §13.2 | Cannot tell which of the ingest slots a default download leaves empty: `host_static` is not a download at all, and `salinity` is outside the default profile | **Fix.** A column in the slot table distinguishing "downloaded from an external source" from "derived by ingest", and one sentence naming the optional slots a default run leaves empty. |
| A26 | §13.3 | Cannot answer the question the stage exists for: which datasets does the ABM need? The flag that claims to say so is declared by two loaders and gates nothing | **Fix.** A table: the ABM's resolved path → the manifest key that fills it → the loader that writes it → whether it is in the default profile. Verify the ABM's path list against the code. |
| A27 | §15 "Licensing and attribution" | No limit is stated for any licence, and the reader cannot tell whether any product restricts redistribution | **Defer** to `docs/licenses.md`, which is the record and outside this layer — but the document must say which limits apply to the products in the default profile, and that the warning is advisory. |
| A28 | §4.1, §2 | Cannot check that an AOI entry is valid, and cannot tell a bad AOI from a missing credential | **Fix.** State the required and optional fields of an AOI entry, and the command that lists what the pipeline knows (`malariasim datasets`). If no command validates an AOI, say that, and say what to check by hand. |
| A29 | §3.6, §17.4 | Cannot predict the content of a default run: the profile table is not printed | **Fix.** Print the profile membership in the document — loader by loader, in or out — with the two inconsistent rows (SMAP out, MODIS in) marked and explained. Names, not numbers: this is not a D1 case. |
| A30 | §3.4 and after | The elided paths (`.../chirps.py:6-9`) cannot be decoded without knowing the codebase | **Fix.** Use the full paths, or state the convention once, in the first place a path is elided. |
| A31 | §4.1 | The AOI registry table is printed two chapters before it is explained, and §3's title promises only the dataset registry | **Fix.** Say in §3 that the table carries both registries, or move the reference to §4. |
| A32 | §5.4, §6 | "The catalogue" is used as a table, a module and a lookup, and "a third table" refers to tables never enumerated | **Fix.** One sentence defining the catalogue as the project's lookup structure, and rewriting "a third table" to name the tables it does have. |
| A33 | §12.2 | The generated contract table is called authoritative, but its columns and the meaning of a contract version are never explained | **Fix.** One sentence introducing the table: what each column is, and what a contract version is (a schema version stamped on the artefact). |
| A34 | §11 | The stage's own parameters are listed with no default, no owner and no failure mode | **Fix.** Each parameter with its default and what breaks when it is set wrong — `ERA5_AREA_PAD_DEG` in particular, whose failure is stated 280 lines later. |
| A35 | §17.1 item 11 | A silently substituted component produces a wrong proxy and a successful run; the reader cannot detect it | **Fix.** State whether the substitution is recorded anywhere (log, manifest) and what the reader should check. If it is not recorded, say so plainly. |

## Acceptance

1. Every row above is either fixed in the document or explicitly deferred
   with a reason — and the deferral says where it is recorded.
2. The document compiles: `latexmk -pdf -interaction=nonstopmode -halt-on-error`.
3. The reader's three unanswerable questions are answerable from the
   revised document alone.
4. The revision lands in its own commit, after this plan. The plan is not
   the deliverable; the document is.

## Not in scope

- Anything about the code's behaviour. Where the document and the code
  disagree, the document is corrected — this plan does not change the code.
- The other five documents. This is the pilot; its result is the pattern,
  not a one-off.
