# The complex swarming dynamics of malaria mosquitoes emerge from simple minimally-interactive behavioral rules

**Authors:** Cribellier A, Poda BS, Dabiré RK, Diabaté A, Roux O, Muijres FT
**Journal:** PLoS Computational Biology | **Year:** 2026 (22(8):e1014685) | **DOI:** 10.1371/journal.pcbi.1014685
**File:** papers/anopheles-dynamics/cribellier-2026-coluzzii-swarm-behavioural-rules-agent-based-model.md

---

## Abstract (summary)

The **published swarm-formation rule** for *Anopheles*: the authors re-analyse two
published laboratory 3-D trajectory datasets of swarming **male *A. coluzzii*** (Poda
et al. 2024; Feugère et al. 2022), extract the individual flight kinematics, and then
build a **minimal agent-based model** of the swarm to test which behavioural rules are
actually needed. The claim is that the "boids" reading of mosquito swarms (mutual
attraction + alignment to conspecifics) is **not supported**: the swarm emerges from
each mosquito's response to **environmental cues** (the visual swarm marker and the
sunset axis) plus one very short-range interaction (collision avoidance).

## Key Results (as used by the model)

- **The three candidate behavioural rules tested:** (1) fly straight through the swarm
  centre, where the **marker viewing angle α is maximal**, until α drops below a
  threshold (turn trigger); (2) the turn is a rapid **saccadic** rotation in the
  horizontal plane, biased towards the swarm centre and along the sunset axis;
  (3) **collision avoidance** when the distance to the nearest neighbour drops below
  ~one body length (≈6 mm).
- **Geometry of the swarm volume (Poda dataset, 938 tracks over 18 recordings):**
  mosquitoes remain within the swarm when **24° ≤ α ≤ 55°** and within the lateral
  boundaries when the relative deviation **Rα ≤ 4.5 %**. The swarm is an **inverted
  elliptical cone** above the marker, with the major axis normal to the sunset horizon.
- **Individual kinematics (males, in swarms):** a saccade every **0.66 ± 0.32 s**
  (≈1.5 Hz); mode turn angle **165°** (near-reversal); straight-flight tortuosity
  τ = **0.84 ± 0.14**; mean straight-flight distance **31 ± 14 cm**; straight segments
  mainly horizontal, oriented along the sunset axis (Rayleigh test on axial data,
  **P < 0.001**).
- **Flight speed used in the model: constant 0.5 m/s**, taken from the Poda dataset.
- **Model settings:** 10 simultaneously swarming mosquitoes (matching the Poda
  typical), 50 Hz time step, 2 min per run, 20 replicates per condition, 200 simulated
  tracks per condition; one variant with and one without the collision-avoidance rule.
- **Integration step and its justification [M]:** "The simulations were run at a
  **temporal resolution of 50 Hz, which is the same as the empirical video frame
  rate**"; the neighbour-prediction time step is set equal to it, "**Δt = 0.02 s**".
  The empirical tracks were reconstructed at **50 fps** (Poda: two NIR Basler
  acA2040 cameras, 2048 × 2048 px; Feugère dataset: "at the same 50 Hz recording
  framerate"). The model is **event-triggered**: after each saccade or evasive
  manoeuvre the simulated mosquito "continued to fly in a straight line at a constant
  speed of 0.5 m/s, until the next saccadic turn or evasive maneuver was triggered".
  Saccades are detected as angular-speed peaks with a **minimum prominence of
  300 ° s⁻¹** (the threshold of van Breugel et al. 2022 for Diptera).
  Model implementation: **MATLAB 2022b**, described following the **ODD protocol**;
  code and parameter table archived (Dryad).
- **Result:** the minimal rule set reproduces the observed kinematics **and generates
  emergent properties not encoded in the rules** (density peak at the swarm centre,
  radial acceleration field with maximum acceleration at the edges). Both the
  with- and without-collision-avoidance models reproduce the *positive* acceleration
  towards neighbours above 1.4 cm, so "**synchronized movements in swarms can emerge
  from reaction to environmental cues alone, without direct interactions between
  conspecifics**".
- **Only the collision-avoidance rule requires conspecific interaction**, and it acts
  only at **< 2.5 body lengths** (≈15 mm) and very rarely. The authors state the
  apparent long-distance interactions "might in fact not be interactions, but instead
  the result of simultaneous responses to external environmental cues".
- **Swarm-size independence:** across swarm sizes from 1 to 26 individuals, the
  individual kinematics (turn angle, straight-flight distance, duration) were
  **invariant**; single initiators show the same behaviour as groups.

## Relevance to MalariaSentinel (Centinela)

**This is the single most decision-relevant paper for the male-layer question**, and
it is **coluzzii-specific** → evidence tier **[M]** for the kinematics, **[EP]** for the
modelling conclusion.

Consequences for the Centinela:

1. **The swarm is not an emergent collective that needs individual agents.** Its
   structure is generated by a *shared response to a point landmark and the sunset
   direction*, i.e. by an **environmental field**, not by inter-male interaction. A
   per-cell aggregate of males plus a marker field therefore loses **nothing** that the
   published swarm-formation rule contains: there is no boids interaction term to
   preserve.
2. **The swarm's spatial extent is a fixed geometric object** (inverted elliptical cone,
   α between 24° and 55°, radius of order 0.2–0.6 m — see
   `feugere-2021-mosquito-sound-swarm-attraction-coluzzii.md`), i.e. **tens of
   centimetres, not hundreds of metres**. The Centinela's 1 km cells cannot and need not
   resolve it: the swarm is a *sub-cell marker* with a cell-level density.
3. **The swarm's temporal envelope is fixed and short** (~27 min, centred on sunset),
   and the **saccade-based flight kinematics are invariant with swarm size** → there is
   no size-dependent behavioural feedback to model.
4. It provides the **only defensible male flight speed in the swarm (0.5 m/s)**, and
   hence a *lower* value than the 0.66–0.87 m/s time-averaged value used in
   `vielma-2026-coluzzii-swarm-flight-speed-burkina-faso.md` — the two are not
   contradictory (time-averaged over loops vs instantaneous straight segments), but
   the model should use a value appropriate to its use.

**Caveats:** laboratory, mesh/flight arenas, simulated sunset, black ground marker,
laboratory-reared males 4–6 days old; the dataset is males only; the model is
parameterised by only one fitted component (post-saccade heading/climb distributions);
the paper *contradicts* the earlier claim of male-male alignment
(`shishika-2014-male-motion-coordination-anopheline-swarms.md`), and the reconciliation
is that the correlations there may be by-products of synchronised responses to cues.

## License

CC BY 4.0 (© 2026 Cribellier et al; PLoS Computational Biology open access).
Open-access copy: https://pmc.ncbi.nlm.nih.gov/articles/PMC13529247/
