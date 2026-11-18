# Mosquito Host Seeking in 3D Using a Versatile Climate-Controlled Wind Tunnel System

**Authors:** André Hinze, J. Lantz, S. R. Hill, R. Ignell
**Journal:** Frontiers in Behavioral Neuroscience | **Year:** 2021 (15:643693) | **DOI:** 10.3389/fnbeh.2021.643693
**File:** papers/anopheles-dynamics/hinze-2021-gambiae-3d-host-seeking-wind-tunnel.md
**Copy read:** Europe PMC full text — https://europepmc.org/article/PMC/PMC7991727

---

## Abstract (summary)

A climate-controlled wind tunnel (air temperature, humidity, precipitation and
elevated CO2 programmable) is used to record **3-D host-seeking flight of
female *Anopheles gambiae* sensu stricto** to human foot odour + CO2 under
tightly controlled conditions, with the experimenter isolated from the arena.
Baseline kinematics (activation, orientation, landing) are quantified.

## Key Results (as used by the model)

### Apparatus and sampling rate  [M]
* Two IR-sensitive GigE cameras (Basler acA1300-60gm), lenses 4.4–11 mm
  (Kowa LMVZ4411), **"at 60 frames s⁻¹"** (Media Recorder 4.0), six 850 nm IR
  illuminators at the downwind end; cameras above the arena covering the
  **upwind 120 cm of the wind tunnel**.
* 2-D positions from **EthoVision XT 14**, 3-D tracks reconstructed with
  **Track3D**; variables: 3-D position, flight speed, heading angle in the
  vertical plane.
* Ambient supply air 20–22 °C; females (non-blood-fed, 4 days post-eclosion)
  sugar-starved 4–16 h (case II) or 15–23 h with water (case I).
* Environment logged with Tinytag data loggers at **1 Hz** (temperature, RH).

### Operational definitions  [M]
* **Volume of interest (VOI)**: a cylindrical region around the upwind screen;
  the fraction of flight spent inside the VOI is the orientation measure.
* **Landing criterion (quantitative):** "Landing was identified by detecting
  the time point at which the **mean speed over 60 frames was below a threshold
  of 50 mm s⁻¹ for three consecutive seconds**", confirmed by visual
  inspection. With 60 fps, 60 frames = 1 s, so the criterion is
  **speed < 5 cm s⁻¹ sustained for 3 s**.
* Recording continues until the mosquito has been on the upwind screen for
  **≥ 5 s**, or up to **10 min** of continuous flight.

### Behavioural results  [P]
* **161 mosquitoes responded** to the treatments; **108 landed** within the
  10-minute maximum (one case study; the second case study: 77 of 101 landed).
* The **proportion landing on the target was significantly affected by CO2 and
  by human foot odour** (Chi-square, p < 0.05).
* **No significant difference in crosswind flight speed between treatments**
  (Kruskal–Wallis).
* With human foot odour + CO2, mosquitoes engaged in **faster crosswind
  flight** and spent more time in the VOI than with control stimuli.

## Relevance to MalariaSentinel (Centinela)

* **Temporal-resolution precedent [M]:** *A. gambiae* s.s. host-seeking
  trajectories were resolved at **60 fps (≈ 17 ms/frame)**. This is the
  closest *Anopheles* primary source with both a 3-D track reconstruction and
  an explicit quantitative landing rule.
* **Landing rule [P→usable]:** a **speed threshold of 50 mm s⁻¹ sustained for
  3 s** is a published, instrument-independent way to declare "landed". This
  is directly usable in the Centinela's terminal-approach gate (replace the
  current "inside the terminal radius" test by "speed below threshold for the
  last 3 s of simulated time"), and it removes the need for a sub-second
  landing animation: the gate is a *persistence* condition, not a geometric
  one.
* **Persistent-bounce behaviour [P]:** the paper explicitly models
  "bouncing at the upwind screen" as a distinct trajectory state — the
  Centinela's movement law needs the same distinction between "approaching
  the host" and "at the host surface", because the second is where the
  terminal-radius rule applies.

**Caveats:** *A. gambiae* s.s. (M form) rather than *A. coluzzii* → **[P]**;
the foot-odour + CO2 stimulus is a partial host cue; laboratory arena.

## License

CC BY 4.0 (Frontiers in Behavioral Neuroscience open access).
