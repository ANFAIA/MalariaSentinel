# Hitting the right note at the right time: Circadian control of audibility in *Anopheles* mosquito mating swarms is mediated by flight tones

**Authors:** Somers J, Georgiades M, Su MP, Bagi J, Andrés M, Alampounti A, Mills G, Ntabaliba W, Moore SJ, Spaccapelo R, Albert JT
**Journal:** Science Advances | **Year:** 2022 (8:eabl4844) | **DOI:** 10.1126/sciadv.abl4844
**File:** papers/anopheles-dynamics/somers-2022-circadian-audibility-mating-swarms.md

---

## Abstract (summary)

Asks how the male and the female, both of whom must find each other in a swarm that
lasts less than 30 min, stay acoustically synchronised. The answer: **males, but not
females, raise their flight-tone frequency at swarm time**, raising it to **1.5 × the
mean female frequency**; the mechanism is driven by the **circadian clock** and is
independent of any female partner (it occurs in males kept individually). The paper also
**deconstructs "harmonic convergence"** — the previously reported acoustic signature of
male–female interaction — showing it is **fully explained by chance**.

## Key Results (as used by the model)

- Swarms are "hundreds or thousands of males congregating at a **fixed location**,
  guided by **visual markers**, and at a **fixed daytime, typically dusk**, to act as
  reproductive mates for a much smaller number (a few dozen) of **sporadically
  entering females**".
- "Mating swarms can form reliably at the **same sites, and same daytimes, for years
  on end**, individual swarms have durations of **sometimes less than 20 min**".
- **Male-specific tone modulation:** at swarm time the male wingbeat frequency rises so
  that the male fundamental reaches **1.5 × the mean female frequency**, exploiting the
  optimality of the mosquito's **distortion-based hearing system** (the Johnston's organ
  is non-linear: the audible signal is a *distortion product* of the male's own tone
  mixed with the female's). The effect is **circadian-clock-driven** and occurs in
  **males kept individually**.
- **Harmonic convergence is a chance artefact:** "All occurring harmonic convergence
  events were indeed **fully explained by chance and did not provide evidence for
  acoustic interaction between the sexes**" — at a fundamental ratio of 1.5 it occurs
  by default.
- **The swarm is described as a "crucial reproductive bottleneck"** in the *An. gambiae*
  complex, and as a prime target for current vector-control efforts.

## Relevance to MalariaSentinel (Centinela)

Evidence tier **[P]** (*A. gambiae* laboratory; the circadian and acoustic results are
generic mosquito physiology) — but the **framing statements are [EP]**-grade priors
that the Centinela can legitimately rely on.

Three things the draft can take from this paper:

1. **"Same sites, same daytimes, for years on end"** is the strongest published
   statement of **swarm-site persistence**, and it is the justification for a
   *static* marker layer in the model (as opposed to a nightly stochastic placement).
2. **The swarm is a reproductive bottleneck with a few dozen sporadically entering
   females per swarm** — this is the published statement of the *female arrival rate*
   that the draft's D5 formula implicitly assumes, and it confirms that the female side
   of the swarm is **rare and sporadic**, i.e. the "competitors(c)" term of the slot
   formula is the small one and the "slots(c)" term is the large one most nights.
3. **The acoustic channel is a within-swarm, centimetre-scale mechanism** (the male
   hears the female through a non-linear distortion product of their overlapping
   tones), consistent with `feugere-2021-mosquito-sound-swarm-attraction-coluzzii.md`:
   sound is **not** a long-range locating mechanism for either sex. It also **kills the
   "harmonic convergence as evidence of interaction" argument** — the Centinela should
   not cite it as support for a male-male or male-female acoustic interaction rule.

**Caveats:** laboratory, single-species and strain details for the flight-tone
measurements are not summarised here (full text read for the passages quoted);
the "few dozen females" figure is a descriptive generalisation, not a measurement in
the quoted passages; the paper concerns audibility physiology, not population dynamics.

## License

CC BY 4.0 (© 2022 Somers et al; Science Advances open access).
Open-access copy: https://pmc.ncbi.nlm.nih.gov/articles/PMC8754303/
