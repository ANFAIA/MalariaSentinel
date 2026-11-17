# The role of grass volatiles on oviposition site selection by *Anopheles arabiensis* and *Anopheles coluzzii*

**Authors:** Y Asmare, SR Hill, RJ Hopkins, H Tekie, R Ignell
**Journal:** Malaria Journal | **Year:** 2017 (16:65) | **DOI:** 10.1186/s12936-017-1717-z
**File:** papers/anopheles-dynamics/asmare-2017-grass-volatiles-oviposition-coluzzii-arabiensis.md

---

## Abstract (summary)

Two-part study of oviposition site selection by gravid malaria vectors:
(1) **field proxy** — the density of *Anopheles* larvae in natural breeding habitats
associated with four wild grasses (*Echinochloa pyramidalis*, *E. stagnina*, *Typha
latifolia*, *Cyperus papyrus*), larvae identified to species; (2) **laboratory** —
headspace volatile extracts of those grasses tested for behavioural attraction and
oviposition stimulation of gravid ***An. arabiensis* and *An. coluzzii*** in wind-tunnel
and two-choice oviposition assays, plus multi-choice tent assays for discrimination
between the four grass extracts.

## Key Results (as used by the model)

- **Spatial scale of the choice is explicit in the paper's framing:** "Mosquitoes
  select oviposition sites at **different spatial scales, starting with selecting a
  habitat in which to search**." The grass-odour mechanism operates at the
  **habitat-identification** scale.
- **Field larval-density hierarchy:** "The larval densities described a **hierarchical
  distribution**, with **Poaceae (*Echinochloa pyramidalis* and *E. stagnina*)-associated
  habitat sites demonstrating higher densities** than that of *Typha*-associated sites,
  and where **larvae were absent from *Cyperus*-associated sites**."
- **Behavioural hierarchy reproduced the field hierarchy:** "This hierarchy was
  **maintained by gravid *An. arabiensis* and *An. coluzzii* mosquitoes in attraction,
  oviposition and multi-choice assays** to grass volatile extracts."
- **Species composition:** "*Anopheles arabiensis* larvae were the most abundant
  species found in the various grass-associated habitats."
- **Methodological caveat stated by the authors:** the field component uses
  "the association of larval abundance in the field with natural breeding habitats
  ... **as a proxy** for oviposition site selection by gravid mosquitoes."

## Relevance to MalariaSentinel (Centinela)

Evidence tier **[M]** for the *A. coluzzii* behavioural assays (the species matches
the Centinela's target); **[P]** for the field larval-density hierarchy (dominant
species was *A. arabiensis*, West African savannah, not Ghanaian coastal *A. coluzzii*).

Consequences for the oviposition model:

- The Centinela's habitat proxies (JRC persistent water, Dynamic-World land-cover
  classes, grass/vegetation affinity weights `w[s,g]`, the `A[i,k,t]` temporal
  responses) are **exactly this mechanism**: a vegetation-odour-driven hierarchy of
  breeding-habitat attractiveness. Asmare et al. give the **published basis for the
  ordering of the vegetation classes** used in the `proxy_habitat_v1` habitat types.
- It is an **odour/habitat-attractiveness mechanism**, evaluated at the level of the
  habitat, and it needs **no memory of where the mosquito came from**. It is, again,
  an argument for a cue-based oviposition kernel, not for an adult-side origin
  coordinate.
- The paper's own framing — "**starting with selecting a habitat in which to search**" —
  is the correct mental model for the engine: the female *searches* for a habitat and
  the habitat decides, not her biography.

**Caveats:** the field component is a **proxy** (larval abundance ≠ oviposition
choice), and the laboratory arm is a volatile-extract assay, not a field oviposition
experiment; species mix in the field data is *A. arabiensis*-dominated; no distances,
no radii, no natal-site test; study area (Uppsala, Sweden) is far outside the target
ecology even for the laboratory arm.

## License

CC BY 4.0 (Malaria Journal / BMC open access). PMID 28173804.
