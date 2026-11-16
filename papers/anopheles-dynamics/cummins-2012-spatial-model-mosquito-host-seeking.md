# A Spatial Model of Mosquito Host-Seeking Behavior

**Authors:** B. Cummins, R. Cortez, I. Foppa, J. Walbeck, J. Hyman
**Journal:** PLoS Computational Biology | **Year:** 2012 (8(5):e1002500) | **DOI:** 10.1371/journal.pcbi.1002500
**File:** papers/anopheles-dynamics/cummins-2012-spatial-model-mosquito-host-seeking.md
**Copy read:** PMC full text — https://pmc.ncbi.nlm.nih.gov/articles/PMC3355069/

---

## Abstract (summary)

An agent-based model of mosquito host-seeking in a 2-D advection–diffusion
odour-plume field. Nine stationary hosts emit a single attractant; mosquito
agents use one of three plume-finding strategies (upwind, downwind, crosswind)
and, once inside the plume, one of two plume-tracking mechanisms (spatial
gradient / temporal sampling). The paper compares the strategies and shows
crosswind plume-finding is the most reliable but the most time-expensive.

## Key Results (as used by the model)

### Scope — read this before citing  [EP for our purposes]
The model is **species-generic** and is written for "the intermediate range
flights of night-active mosquitoes **such as *Culex quinquefasciatus* feeding
on roosting birds**". It is **not** an *Anopheles* model and **not** an
*Aedes* model; it is a generic mosquito whose parameters are chosen for a
*Culex*-like system. The paper is the source of the *threshold-based hybrid
agent architecture* (plume-finding vs plume-tracking) that the Centinela
movement law borrows structurally, but it is **not** a source of
*Anopheles*/*Aedes* parameter values.

### Parameter table (Table 1)  [EP]
* **Minimum mosquito flight speed 0.4 m s⁻¹; maximum 1.5 m s⁻¹** — with
  *orthokinesis*: the speed is a deterministic function of the local
  concentration (slow near the source, faster away from it). **There is no
  "constant 0.3 m s⁻¹" flight speed in this paper**; 0.3 m is the *host
  spacing* (nine hosts on a 1 ft grid), not a speed.
* Sensing threshold **40 ppm**; sensing saturation **4000 ppm** (no ambient
  background assumed).
* Gradient method: minimum detectable gradient **40 ppm m⁻¹**, maximum
  **7900 ppm m⁻¹**.
* Minimum / maximum interval half-widths for the direction-choice window;
  minimum / maximum wind-sensing window half-widths.
* Wind-sensing threshold 0 m s⁻¹; wind-sensing saturation 0.5 m s⁻¹.
* **Duration of one crosswind flight segment: uniformly sampled from
  [0.5, 0.9] s.**
* **Critical radius for mosquito–host contact: 0.5 m.**
* Large-scale wind 0.2 m s⁻¹; superposed stochastic small-scale wind
  0.15 m s⁻¹; Gaussian variables resampled every 2 s.
* Diffusion coefficient for CO2 in air; **host release rate 1680 ppm s⁻¹**.
* Simulation domain 10 m per side; simulation length up to 500 s;
  200 mosquitoes per simulation.

### Behavioural rules encoded  [EP]
* Below the sensing threshold, mosquitoes navigate only by wind, using a
  pre-assigned upwind / downwind / crosswind pattern ("plume finding").
* Above the threshold, they switch to plume tracking: upwind + up-gradient
  (tropotaxis) or upwind + up-concentration with memory (klinotaxis).
* On entering the plume, downwind/crosswind searchers begin to fly upwind.
* The mosquito direction is chosen at random from a **precision window**
  around the ideal direction; the window is wider when the sensory input is
  weaker (i.e. uncertainty grows with distance from the source).

### Findings quoted from the literature by this paper  [P]
* "A typical mosquito flight speed is **1 m s⁻¹**."
* "mosquitoes fly faster than the wind speed when they are in the low velocity
  boundary layer that forms adjacent to the ground"; they can be swept up and
  transported passively at higher elevation.
* "**Wind speeds as low as 0.8 m s⁻¹ (3 km/h)** have been reported to
  drastically reduce the number of mosquito host-seeking flights, but no
  reduction in mosquito flight was documented in other situations for speeds
  as high as 3–8 m s⁻¹."
* "Laboratory wind tunnel experiments indicate that **sustained flight only
  occurs in the presence of an intermittent signal and not in uniform
  concentrations**."
* "the distances at which various species of mosquitoes responded to baits by
  initiating orientation toward them was **30 meters or less**" (citing Gillies
  & Wilkes 1972).
* "crosswind plume finding most reliably led mosquitoes to a blood meal
  source … accompanied by a high cost in time"; if host location had to occur
  within 35 s of release, crosswind was superior only in a straight plume, and
  in a meandering plume up- and downwind searching were better.
* "Many existing models use the popular Keller–Segel approach that assumes
  knowledge of the concentration gradient."

## Relevance to MalariaSentinel (Centinela)

This paper is the origin of the **hybrid, threshold-based agent architecture**
that the movement law adopts, and it is also the origin of the "gradient
thresholds of 40 ppm/m and 7900 ppm/m" numbers quoted in the synthesis.
Those two thresholds are **verified exactly** — but they are parameters of a
**simulation calibrated for a generic mosquito in a 10 m laminar indoor
domain**, not measured values. The paper itself warns that gradient-following
produces artificially direct trajectories in turbulent outdoor plumes, and the
Centinela's outdoor setting is exactly that case.

**Correction to the synthesis:** the "0.3 m/s constant flight speed" attributed
to this paper does not exist in it. The paper uses **0.4–1.5 m s⁻¹** with
concentration-dependent (orthokinetic) speed, and it quotes a *typical*
mosquito flight speed of **1 m s⁻¹** from the literature. The 0.3 m s⁻¹ figure
in the synthesis appears to be a misreading of the **0.3 m host spacing**.

## License

CC BY 4.0 (PLOS Computational Biology open access).
