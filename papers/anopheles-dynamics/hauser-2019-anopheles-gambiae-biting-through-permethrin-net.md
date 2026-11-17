# The ability of *Anopheles gambiae* mosquitoes to bite through a permethrin-treated net and the consequences for their fitness

**Authors:** Gerd Hauser, Karine Thiévent, Jacob C. Koella
**Journal:** Scientific Reports | **Year:** 2019 | **DOI:** 10.1038/s41598-019-44679-1
**File:** papers/anopheles-dynamics/hauser-2019-anopheles-gambiae-biting-through-permethrin-net.md

---

## Abstract (summary)

Laboratory assay of *Anopheles gambiae* (insecticide-sensitive strain) biting through a
permethrin-treated vs untreated net, measuring survival, fecundity and **blood-meal size**
by haematin quantification of the faeces (Briegel's method). The paper decomposes the
"bite" outcome into distinct measurable components.

## Key Results (as used by the model)

- "Despite the irritancy of permethrin, **71 % of the mosquitoes took blood through the ITN
  (vs. 99 % through the untreated net)**." → the two-level structure the redesign needs:
  *biting success* (88 % tried to bite) and *feeding success* (71 % engorged).
- "**The ITN reduced the time spent biting, the blood-meal size and the fecundity**, and it
  killed about 15 % of the mosquitoes within 24 hours of feeding (vs. 5 % on the untreated
  net)."
  → a partial/smaller meal reduces fecundity: the link between *meal size* and *egg batch*
  is empirical here.
- Blood-meal size measured as: "(1) the proportion of mosquitoes that tried to bite at
  least once (**biting success**), (2) the proportion that succeeded to take blood during
  the 8 minutes they were allowed to (**feeding success**), (3) the time required for the
  mosquitoes to start biting through the net (**time to bite**), (4) the time they spent
  feeding until they detached or until the end of the allocated time (**feeding time**),
  and (5) the **quantity of haematin in the faeces, used as a proxy for the quantity of
  blood ingested (haematin level)**."
- "a blood meal helped mosquitoes to survive their exposure to permethrin through a
  physiological mechanism" (dietary/ROS protection conferred by the blood meal).

## Relevance to MalariaSentinel (Centinela)

Two uses. (1) **Method**: the haematin-proxy quantification of blood-meal size is the
standard way to measure the quantity of blood a mosquito actually ingested, and it is the
measurement that any empirical validation of `blood_meal_size_ul` would have to make.
(2) **Parameter structure**: `biting success` and `feeding success` are separate
probabilities, and the *amount* of blood ingested is a third, continuous quantity — three
things the current engine collapses into one boolean.

Caveats: laboratory colony, insecticide-sensitive strain, mouse/armature host (no Ghana
population); the abstract reports relative changes, not absolute µL values.

## License

CC-BY 4.0 (Scientific Reports / Nature Portfolio open access).
