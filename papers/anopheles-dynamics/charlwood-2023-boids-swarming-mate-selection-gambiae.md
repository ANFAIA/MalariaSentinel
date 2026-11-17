# Swarming and mate selection in *Anopheles gambiae* mosquitoes (Diptera: Culicidae)

**Authors:** Charlwood JD
**Journal:** Journal of Medical Entomology | **Year:** 2023 (60(5):857–864) | **DOI:** 10.1093/jme/tjad064
**File:** papers/anopheles-dynamics/charlwood-2023-boids-swarming-mate-selection-gambiae.md

---

## Abstract (summary)

A **conceptual/review paper** that states the "boids" interpretation of anopheline
swarming and its consequences for mate selection. It is the reference most often cited
for the claim that anopheline swarms can be treated as **boids** (flocking-style
agents with attraction + alignment + separation), and for the claim that the **swarm
site, not the swarm, is the mate-recognition system**. **Only the abstract was read**
(the article is not open access).

## Key Results (as used by the model)

From the abstract (verbatim content available):
- "Treating both male and female *Anopheles gambiae* as if they are **'boids'** (a
  computer program that mimics flocking in birds) explains much of the swarming and
  mating behavior in this important group of malaria vectors."
- "It is suggested that **species specific swarm sites act as the mate recognition
  system** in anophelines and it is proposed that **virgin females respond to the swarm
  site per se rather than the swarm itself**."
- "Given the **high operational sex ratio** and the **inability of any male to dominate
  all females within the swarm**, it is considered that **chance, rather than sexual
  selection, is the most important determinant of mating**."
- "The **male being in the swarm may be a sufficiently strong signal to the female**."

## Relevance to MalariaSentinel (Centinela)

Evidence tier **[P]** for *A. gambiae*; **[NR]** for anything quantitative (the
abstract reports no numbers) and **only the abstract was read** — the project's rule
forbids presenting unread claims as verified, so this extract records the *claims*, not
verified facts.

Why it still matters:

1. **It is the strongest statement of the "boids" reading**, and therefore the paper
   that a reviewer of the Centinela's male layer would cite to ask "why are the males
   not individual agents?". The answer is now available in the literature itself:
   `cribellier-2026-coluzzii-swarm-behavioural-rules-agent-based-model.md` (coluzzii,
   same-genus, quantitative) shows that the minimal rules that reproduce the swarm are
   **environmentally anchored**, not conspecific-anchored, so the boids reading is not
   needed to reproduce the swarm.
2. **"Virgin females respond to the swarm site per se rather than the swarm itself"**
   is, if true, a *strong* argument for the Centinela's aggregate-plus-marker design:
   the female's decision variable is the **site**, not the swarm's internal structure or
   even its size. This should be cited (as an abstract-level, unverified claim) in the
   draft.
3. **"Chance, rather than sexual selection, is the most important determinant of
   mating"** is the theoretical justification for a **probabilistic slot formula** (the
   D5 formula) rather than a deterministic or trait-based mate choice model: with ~100+
   males and few females per swarm, the pairing outcome is effectively a random draw
   from the available slots.
4. **"The male being in the swarm may be a sufficiently strong signal to the female"**
   is the only published statement that supports a *non-acoustic*, presence-based
   female attraction channel — consistent with the negative acoustic result in
   `feugere-2021-mosquito-sound-swarm-attraction-coluzzii.md`.

**Caveats:** review/conceptual paper, no new measurements; *A. gambiae*, not
*coluzzii*; **not open access — only the abstract was read**; the boids framing is
contradicted-by-later-work in the coluzzii case (see Cribellier 2026) and should be
presented as a hypothesis, not a result.

## License

**Not open access** — Oxford University Press, *Journal of Medical Entomology* 60(5).
Only the abstract was read.
DOI: https://doi.org/10.1093/jme/tjad064
