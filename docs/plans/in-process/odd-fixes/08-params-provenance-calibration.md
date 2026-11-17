# Pack 08 — Parameter provenance and calibration (engineering priors → literature)

> Source: ODD 2010 review notes.
**Document sections invalidated (CUJ-4):** `docs/concepts/abm/odd-2010-malariasentinel.tex` → §"Generated parameter table", Appendix B.3 "Calibration and validation status", Appendix B.4 "Values that are readings of the tree", and the Appendix A items.
When this pack is decided and applied, these are the passages that
must change; the document is amended in the commit that applies the
pack, not in the pack itself.
 Status: initial plan — to be detailed later.
> Note: p.8 "reduce calibration" was clarified to mean *refine `k_ref`* —
> already covered here.

## Objective

Every engineering prior must be backed by papers/studies; audit that all
constants live in `model_constants.yaml`; fix the `k_ref` unit annotation
and the `daily_mort_basal` name.

## Notes (verbatim)

- **p.19** — "Review engineered priors constants" / "K-ref is the most relevant one to review."
- **p.6** (habitat pseudocode) — "calibrate with scientific base k_ref"
- **p.4** (`k_habitat`) — "Must be calibrated correctly, if possible with scientific studies behind supporting the calibration."
- **p.30 A.9** — "parameter to review in detail." *(`k_ref` labelled ind·km⁻²·d⁻¹ but consumed as a standing count)*
- **p.10** (stochasticity list) — "Not in yaml?" *(crossed entries: verify every constant in that section exists in the yaml AND is based on papers)*
- **p.10** (larval competition) — "Must be calibrated."
- **p.21** (Beverton–Holt) — "review theory."
- **p.20** (aquatic parameter brace) — "find papers to support these data"
- **p.22** (gonotrophic table) — "All of them came from papers. Review."
- **p.24** (below host-seeking table) — "All engineered priors must be backed up by paper and studies."
- **p.26** (wind table) — "Review papers behind"
- **p.28** (EIP base/threshold) — "find paper support for it."
- **p.30 A.10** — "rename" *(`daily_mort_basal` is a survival probability, not a mortality)*

## Initial steps

1. Full provenance audit: one table of every key in
   `model_constants.yaml` → value → "literature anchor" (with full
   citation) or "engineering prior" (flagged for future fitting).
   Start with `k_ref` (the most relevant), then aquatic, gonotrophic,
   host-seeking, dispersal/wind, EIP tables. In fact, the table,
   is in the odd document, and the goal here is to try to create a
   temporal table of those that are marked as engineered or calibrated.
   So that we can minimize the number of such variables, and maximize
   those supported by papers.
2. Verify yaml completeness for the stochasticity constants (p.10).
3. Resolve `k_ref`'s unit annotation (A.9: standing capacity vs per-day).
4. Rename `daily_mort_basal` → survival semantics (A.10), Python + C++ + yaml.
5. Review the Beverton–Holt form and its parameters against theory.
6. Complete the bibliography for the author-year anchors cited only in
   comments (Costantini 1996, Thomas 2013, Faiman 2020, Sanogo 2021,
   Okal 2013, Giraldo 2023, Lardeux).

## Dependencies / open points

- This pack is the prerequisite for the future formal calibration cycle;
  packs 03/04/07 change dynamics and will re-open some values.
