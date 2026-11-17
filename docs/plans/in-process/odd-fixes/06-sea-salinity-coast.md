# Pack 06 — Sea, salinity, and coastal influence

> Source: ODD 2010 review notes.
**Document sections invalidated (CUJ-4):** `docs/concepts/abm/odd-2010-malariasentinel.tex` → §6 "Input data" (the coastal band), §7.1 "Update habitat availability and capacity".
When this pack is decided and applied, these are the passages that
must change; the document is amended in the commit that applies the
pack, not in the pack itself.
 Status: initial plan — to be detailed later.

## Objective

Stop open-sea cells from being breeding habitat, make the sea influence
neighbouring coastal cells, and give the salinity channel a real effect.

## Notes (verbatim)

- **p.17** (salinity limitation) — "Review that salinity has effect on watters, and that the see is properly identify"
- **p.17** (open-sea limitation) — "Mosquitoes cannot be born on the sea but it must affect near coastal cells."
- **p.30 A.14** — "Remove them from suitability, but affect surrounding."
  *(concrete case: Gulf of Guinea cell row 745, col 275 has `lc_open_plus_water`=1,
  `H_total`=1, `S≈0.40` at z=1 and is a candidate patch; sea temperature is the
  0.0 sentinel so development is zero but adults survive at the 0.60 floor)*

## Initial steps

1. Mask open-sea cells out of the `lc_open_plus_water` plane / candidate
   patch set (e.g. via the `land_frac` plane or a sea mask at ingest).
2. Define the coastal influence mechanism: how the sea affects adjacent
   cells (temperature buffering? salinity gradient?) without making sea
   cells themselves habitat.
3. Verify the salinity channel actually gates habitat activation and
   larval survival end-to-end (absent from the delivered Ghana product →
   everything freshwater today).
4. Regenerate/validate the Ghana product against the row 745, col 275
   example.
5. Test sea detection by generating images reviewed by a partial external
   subagent.

## Dependencies / open points

- Ingest-side change → new env-NC product (contract 3.0 bump?).
- Overlaps pack 05 (habitat planes) — coordinate the ingest change once.
