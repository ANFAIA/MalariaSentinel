# Tolerance of disease-vector mosquitoes to brackish water and their osmoregulatory ability

**Authors:** Pierre Kengne, Guy Charmantier, Eva Blondeau-Bidet, Carlo Costantini, Diego Ayala
**Journal:** Ecosphere | **Year:** 2019 (10(10):e02783) | **DOI:** 10.1002/ecs2.2783
**File:** papers/anopheles-dynamics/kengne-2019-brackish-water-osmoregulation-mosquitoes.md

---

## Abstract (summary)

Acute salinity bioassays (24-h exposure of 4th-instar larvae) plus hemolymph
osmolality measurements (24 h after transfer) on six multigenerational
laboratory colonies: *Aedes aegypti*, *Ae. albopictus*, *Anopheles coluzzii*,
*An. gambiae*, *Culex pipiens*, *Cx. quinquefasciatus*. Test media were
dilutions of natural seawater (34 ppt, ~1000 mOsm/kg = 100 % SW) at 10, 20, 30,
40 and 50 % SW (3.4, 6.8, 10.2, 13.6, 17 ppt) plus deionized-water controls
with/without food. The *An. coluzzii* colony is the **Yaoundé (Cameroon)
"fresh–polluted water" strain collected in 1988**; the *An. gambiae* colony is
from Kisumu, Kenya (1975). The authors explicitly warn that extrapolation to
natural populations must be done with caution (laboratory maintenance effects,
inbreeding depression).

## Key Results (as used by the model)

- **LC50 (24 h, 4th instar):** *Ae. albopictus* 510 ± 16 mOsm/kg
  (**17.3 ppt**) > **\*An. coluzzii\* 383 ± 9 mOsm/kg (13.0 ppt)** > *Ae.
  aegypti* 381 ± 8 (12.95 ppt) > *Cx. quinquefasciatus* 328 ± 6 (11.2 ppt) >
  **\*An. gambiae\* 304 ± 7 mOsm/kg (10.3 ppt)** > *Cx. pipiens* 248 ± 7
  (8.4 ppt). The ranking *Ae. albopictus* > *An. coluzzii* > *Ae. aegypti* >
  *Cx. quinquefasciatus* > *An. gambiae* > *Cx. pipiens* is the paper's
  headline result.
- **Mortality onset:** no mortality in deionized water; mortality started at
  **200 mOsm/kg (6.8 ppt, 20 % SW)**; with the sole exception of *Ae.
  albopictus*, **100 % mortality between 300 and 500 mOsm/kg (10.2–17 ppt)**.
- **Osmoregulation:** all species were hyper-iso-osmoregulators (hyper-
  regulators in fresh water, osmoconformers at high salinity). *An. coluzzii*
  hemolymph osmolality: **226 ± 13 mOsm/kg** in deionized water, 274 ± 11 at
  100 mOsm/kg, 292 ± 19 at 200, 343 ± 15 at 300, **420 ± 28 at 400 mOsm/kg
  (13.6 ppt)**. Hyper-osmoconformation was reached at **400 mOsm/kg
  (13.6 ppt)** for *An. coluzzii*, *An. gambiae* and both *Aedes*.
- **Cross-species predictor:** hemolymph osmolality in deionized water is
  strongly correlated with salinity tolerance (**Pearson r = 0.87, P < 0.05**),
  and the correlation weakens at higher salinities.
- **Comparison with White et al. (2013):** LC50 of 33–36 % SW for *An.
  coluzzii* and 33–38 % SW for *An. gambiae* (NaCl solutions) vs 38 % and 30 %
  SW in the present study (diluted seawater) — a method-dependent spread of
  roughly ±4 percentage points of sea water.

## Relevance to MalariaSentinel (Centinela)

The most direct measurement of the **relative** salinity tolerance of
*An. coluzzii* vs *An. gambiae* (13.0 vs 10.3 ppt LC50, i.e. a ratio ≈ 1.26),
and hence the justification for the ordering of the YAML `salinity_slope`
(0.08 coluzzii vs 0.12 gambiae s.s.) and for `salinity_hi_tol_ppt` being larger
for coluzzii than for gambiae s.s. It also gives the mechanistic basis for
treating salinity as a *stress gradient* (hyper-iso-osmoregulation → energetic
cost) rather than a binary habitat mask.
**Caveats:** laboratory colonies (Cameroon 1988 for coluzzii), acute 24-h
larval mortality, not a chronic or full-cycle threshold; 13 ppt LC50 is an
order of magnitude below the YAML's `salinity_hi_tol_ppt: 30` (the YAML value
is only defensible if read as ~30 % sea water ≈ 10.5 ppt, i.e. it is
optimistic).

## License

CC BY 3.0 (Wiley / Ecosphere open access). Author accepted manuscript also
deposited at HAL (hal-02434206).
