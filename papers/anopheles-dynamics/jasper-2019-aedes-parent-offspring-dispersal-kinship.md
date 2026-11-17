# A genomic approach to inferring kinship reveals limited intergenerational dispersal in the yellow fever mosquito

**Authors:** M Jasper, TL Schmidt, NW Ahmad, SP Sinkins, AA Hoffmann
**Journal:** Molecular Ecology Resources | **Year:** 2019 (19:729–741) | **DOI:** 10.1111/1755-0998.13043
**File:** papers/anopheles-dynamics/jasper-2019-aedes-parent-offspring-dispersal-kinship.md

---

## Abstract (summary)

Methodological paper: how to estimate **parent→offspring dispersal** (the quantitative
form of natal philopatry) in a mosquito, when direct parent-offspring tracking is
impossible. **162 *Aedes aegypti*** were genotyped with genome-wide **SNPs** and
collected from **eight close-set, high-rise apartment buildings** in Malaysia (high
dengue incidence). Kinship groups were reconstructed across **three orders of kinship**;
the geographical distances between kin pairs were transformed into axial standard
deviations and **decomposed into components representing past dispersal events**; the
parent-offspring component was isolated.

## Key Results (as used by the model)

- **Neighbourhood area: 129 m.** "we isolated the axial standard deviation of
  parent-offspring dispersal and estimated **neighbourhood area (129 m)**, **median
  parent-offspring dispersal distance (75 m)** and **oviposition dispersal radius
  within a gonotrophic cycle (36 m)**."
  → **three directly quotable numbers for natal philopatry and oviposition-site
  spread in a mosquito**: median parent→offspring displacement **75 m**; oviposition
  dispersal radius within one gonotrophic cycle **36 m**; neighbourhood area
  **129 m**.
- **Isolation by distance is present at both scales:** "finding **isolation by distance
  both within and between buildings** and estimating **neighbourhood size at 268
  individuals**."
- **Method transferability:** "Our methodology is readily implementable for studies of
  other species, including pests and species of conservation significance."

## Relevance to MalariaSentinel (Centinela)

Evidence tier **[P]** — *Aedes aegypti* (yellow fever mosquito), **Malaysia**, urban
high-rise; the closest quantitative proxy available for "how far does a mosquito
generation actually spread from its parents", and the only source in this review that
puts a **number on natal philopatry** rather than a qualitative statement.

Consequences for the Centinela:

- These are the numbers a "return to the natal site" model would need, and they are
  **tens of metres, not hundreds**. The **median parent-offspring displacement (75 m)**
  and the **oviposition dispersal radius within a gonotrophic cycle (36 m)** are the
  natural magnitudes to compare any `home_x/home_y`-driven attraction against.
  Under those magnitudes, the **1 km grid cell is already a sufficient statistic**: a
  natal-site attraction with a 36–75 m radius is *invisible* at the cell level.
- The paper provides a **ready-made method** that the Centinela could apply to
  *A. coluzzii* genomic data (e.g. the Obuasi WGS data of Nagi et al. 2025) to obtain
  the first *Anopheles* estimate of natal philopatry. The Centinela should treat that
  as the **experiment to run**, rather than inventing a prior.
- The **nageli caveat** is important: Nagi et al. 2025 found that polymorphic
  chromosomal inversions **confound kinship estimation in *Anopheles gambiae*** and
  produce high variance in relatedness among kin. Applying Jasper's method to
  *A. coluzzii* therefore requires the inversion-aware kinship work of
  Nagi et al. first — i.e. the method is available but not yet applied to the target
  species.

**Caveats:** *Aedes aegypti*, not *Anopheles*; Malaysia, not West Africa;
container-breeding, high-rise — a very different ecology from rural/coastal Ghana;
the parent-offspring decomposition is an **inference from kinship distances**, not an
observation of movement; the oviposition-dispersal-radius figure (36 m) is derived
within a gonotrophic cycle, i.e. per breeding event, not per lifetime.

## License

CC BY 4.0 (Wiley / Molecular Ecology Resources open access). PMID 31125998.
