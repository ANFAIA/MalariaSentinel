# Taxis assays measure directional movement of mosquitoes to olfactory cues

**Authors:** Lena M. Lorenz, A. Keane, J. Moore, C. Munk, L. Seeholzer, A. Mseka, E. Simfukwe, J. Ligamba, E. Turner, L. Biswaro, F. Okumu, G. Killeen, W. Mukabana, S. Moore
**Journal:** Parasites & Vectors | **Year:** 2013 (6:131) | **DOI:** 10.1186/1756-3305-6-131
**File:** papers/anopheles-dynamics/lorenz-2013-taxis-assays-range-attraction-100m.md
**Copy read:** publisher PDF (version of record) via Edinburgh Research Explorer — https://www.pure.ed.ac.uk/ws/portalfiles/portal/17177302/Lorenz2013.pdf

---

## Abstract (summary)

Two experiments in Tanzania with three-chambered "taxis boxes" that quantify
*activation* (leaving the central chamber) and *taxis* (directional movement
towards vs away from the stimulus) separately. Experiment 1 (semi-field tunnel,
SFT) used nulliparous female ***Anopheles gambiae* s.s.**; Experiment 2 (open
field) used female ***Anopheles arabiensis***. Stimuli: whole human odour, a
synthetic carboxylic-acid blend + CO2, and CO2 alone, at four distances up to
100 m.

## Key Results (as used by the model)

### Experiment 1 — semi-field tunnel (SFT), *A. gambiae* s.s.  [P]

Setup: 110 m × 2 m × 2.5 m screened semi-field tunnel at Ifakara; directional
airflow **0–2 m min⁻¹ (0–0.033 m s⁻¹)**; nulliparous females 3–8 d old,
sugar-starved 4 h; 50 females per box; stimulus at point 0; taxis boxes at
**20, 50, 70 and 100 m**; 16 nights (n = 4 per treatment/control). Stimuli
dispensed under an untreated bed net (visual control): **CO2 500 ml min⁻¹**;
blend + 500 ml min⁻¹ CO2 (blend = ammonia 2.5 %, L-lactic acid 85 %,
propionic 0.1 %, butanoic 1 %, pentanoic 0.01 %, 3-methylbutanoic 0.001 %,
heptanoic 0.01 %, octanoic 0.01 %, tetradecanoic 0.01 %); one human volunteer
(12 h without bathing).

*Activation* (proportion of all mosquitoes leaving the centre chamber):

| Distance | Control | CO2 | Blend | Whole human |
|---|---|---|---|---|
| 20 m | 25 % (53/215) | 45 % (96/212) | 49 % (99/203) | 46 % (96/211) |
| 50 m | 30 % (59/200) | 39 % (77/198) | 47 % (91/192) | 43 % (86/202) |
| 70 m | 36 % (72/199) | 44 % (89/201) | 40 % (84/210) | 52 % (110/210) |
| 100 m | 39 % (80/203) | **53 % (106/199)** | 34 % (67/200) | 44 % (87/198) |

*Attraction* (taxis, % of activated moving towards): control 31–36 % at all
distances.

* 20 m — **all three stimuli significantly more attractive than control**:
  CO2 58 %, blend 63 %, whole human 56 % vs control 36 %. All three were
  "> 20 % more attractive than the control at 20 metres".
* 50 m — **CO2 65 %** and **blend 63 %** still significant (control 36 %);
  whole human odour at 50 m was **only activated, not attracted**.
* 70 m — **only the synthetic blend still attracted** (51 % vs 31 % control);
  CO2 and whole human only activated.
* 100 m — **no stimulus attracted**; only CO2 still *activated* more than
  control (53 % vs 39 %).

Abstract wording: "blended synthetic human odours attracted 20 % more
*A. gambiae* in the semi-field tunnel up to 70 metres"; "CO2 … attractive to
*A. gambiae* up to 50 metres (65 % attraction compared to 36 % in controls)".

### Experiment 2 — open field, *A. arabiensis*  [P]

100 m-long open strip at Ifakara; taxis boxes at **10, 30, 70 and 100 m**; 4
nights per treatment; 4 human volunteers. **Wind during the 18:00–22:00 window
was 0.16–0.45 km/h (0.04–0.13 m s⁻¹)**, with gusts 0.51–2.77 km/h — i.e.
near-calm, so this is a *low-turbulence* open field, not a windy one.
Activation 41–57 % with **no significant effect of stimulus or distance**.

* 10 m — whole human odour **68 %** and blend **65 %** attracted vs control
  **50 %** (significant). **CO2 alone gave no directional response.**
* 30 m — whole human odour **57 %** vs control **51 %** (significant);
  **CO2 and blend gave no response**.
* **Beyond 30 m — no stimulus had any effect.**

Abstract: "Significantly more (6-18 %) *A. arabiensis* mosquitoes were attracted
to natural human odour in the field up to 30 metres compared to controls …
Whereas CO2 elicited no response in *A. arabiensis* in the open field."

### Background reading cited by the paper
Cummins et al. (2012) cites Gillies & Wilkes (1972, *Bull. Entomol. Res.* 61:
389–404, "The range of attraction of animal baits and carbon dioxide for
mosquitoes") for the statement that "the distances at which various species of
mosquitoes responded to baits by initiating orientation toward them was **30
meters or less**".

## Relevance to MalariaSentinel (Centinela)

This is the **only source found that measures a maximum host-detection /
attraction range at all**, and it is the origin of the "30 m in the open field,
50–70 m in semi-field" numbers used in the movement-law design. It supplies
three directly usable parameters for the `perception_radius` key, all of them
**proxy values from sister taxa, never from *A. coluzzii***:

1. `co2_activation_radius` — **100 m** (activation only, no directional
   orientation) in *A. gambiae* s.s., SFT. **[P]**
2. `olfactory_orientation_radius` — **70 m** (synthetic blend + CO2) / **50 m**
   (CO2 alone) in *A. gambiae* s.s., SFT; **30 m** (whole human odour) in
   *A. arabiensis*, open field. **[P]**
3. The **open-field vs semi-field collapse** is confirmed: 30 m in the open
   field vs 70 m in the SFT. **[P]**

**Caveats that must be carried into the plan:** (a) neither species is
*A. coluzzii* — *A. arabiensis* is deliberately the more outdoor-adapted of the
two, so the 30 m field value is if anything generous for *A. coluzzii*;
(b) the field experiment ran in near-calm air (≤ 0.13 m s⁻¹), so the 30 m
value is an upper bound for a calm night, not for a breezy one; (c) "attraction"
here is a coarse binary (entered the towards-chamber vs the away-chamber of a
1 m taxis box), not a continuous orientation strength.

## License

CC BY 2.0 (BioMed Central / Parasites & Vectors open access).
