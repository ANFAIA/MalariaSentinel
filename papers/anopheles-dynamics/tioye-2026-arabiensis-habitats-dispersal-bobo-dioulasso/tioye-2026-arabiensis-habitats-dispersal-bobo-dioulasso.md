# Habitats and dispersal of *Anopheles arabiensis* in the urban area of Bobo-Dioulasso, Burkina Faso

**Authors:** DJJ Tioyé, PS Sawadogo, NSB Somda, BS Poda, F Sankara, KR Dabiré
**Journal:** Acta Tropica | **Year:** 2026 (vol. 278, art. 108107) | **DOI:** 10.1016/j.actatropica.2026.108107
**File:** papers/anopheles-dynamics/tioye-2026-arabiensis-habitats-dispersal-bobo-dioulasso.md

---

## Abstract (summary)

Urban entomology study in **Dioulassoba, Bobo-Dioulasso, Burkina Faso**, a locality
implicated in urban malaria transmission. Two components: (i) characterisation of
**adult resting habitats** (outdoor structures aspirated; positive habitats described by
contrast, luminosity, temperature and mosquito density); (ii) **post-emergence
dispersal**, measured by collecting adults at increasing distances from the **Houet
river**, the primary larval site.

## Key Results (as used by the model)

- **Post-emergence dispersal is SHORT: "Dispersal following emergence was limited,
  with fewer than 60 % of adults moved beyond 50 meters from the larval site, with
  females dispersing farther than males."** Read literally: **> 40 % of newly emerged
  adults stayed within 50 m of the larval site**, and **< 60 % moved further than 50 m**.
  This is the closest published measurement in *Anopheles* of the (c) phenomenon —
  dispersal of newly emerged adults away from the natal site.
- **Density decays with distance from the larval source:** "Mosquito density declined
  progressively with increasing distance from the Houet river."
- **Resting-habitat association:** "*Anopheles arabiensis* exploited a wide range of
  habitats that were generally **warm and shaded with heterogeneous illumination**.
  There was a strong positive correlation between mosquito density, habitat type and
  environmental parameters."
- **Operational implication stated by the authors:** "interventions targeting resting
  habitats or sterile males' releases **concentrated near larval sites** may improve
  vector control by reducing local *An. arabiensis* population."

## Relevance to MalariaSentinel (Centinela)

This is the **only direct field measurement of the adult→natal-site distance
distribution** found in the literature review for this question. Evidence tier **[P]**
— *A. arabiensis*, not *A. coluzzii*; urban Burkina Faso, not coastal Ghana.

What it licenses for the Centinela:

- A **post-emergence dispersal scale of tens of metres**, i.e. **not** the
  350–650 m/day adult dispersal kernel of Costantini 1996 / Thomas 2013 (which is a
  population-level, mark-release-recapture quantity dominated by host-seeking
  displacement). The engine should distinguish the two: a **short natal-site-bound
  phase** immediately after emergence, and a **long-range dispersal phase** later.
  The Centinela currently has only the latter.
- It provides an **upper bound on any "home" concept**: whatever the adult's origin
  coordinate, the mosquito's realistic position shortly after emergence is within a few
  tens of metres of it. A per-mosquito `home_x/home_y` field would therefore only ever
  be consulted inside a ~50 m neighbourhood — which is exactly the regime where the
  1 km grid cell (or, in the new design, the aquatic cohort's own cell) is already
  a sufficient statistic.
- It **supports** the "concentrated near larval sites" deployment logic the Centinela
  already encodes (habitat proxies drive adult abundance) and it warns that the
  dispersal kernel should not be applied at emergence with a 450 m sigma.

**Caveats:** *A. arabiensis*; a single urban district of Burkina Faso; the larval
source is assumed to be the Houet river, not measured per-individual; the
"fewer than 60 %" figure is quoted from the abstract and the underlying distance bands
and sample sizes were not read (see below).

## License

**Not open access** (Elsevier / Acta Tropica). **Only the abstract was read** — no
claim in this extract goes beyond the abstract text.
