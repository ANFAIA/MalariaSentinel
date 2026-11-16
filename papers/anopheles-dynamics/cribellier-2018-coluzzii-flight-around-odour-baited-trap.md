# Flight behaviour of malaria mosquitoes around odour-baited traps: capture and escape dynamics

**Authors:** Anne Cribellier, J. A. van Erp, A. Hiscox, M. J. Lankheet, J. L. van Leeuwen, J. Spitzen, F. T. Muijres
**Journal:** Royal Society Open Science | **Year:** 2018 (5:180246) | **DOI:** 10.1098/rsos.180246
**File:** papers/anopheles-dynamics/cribellier-2018-coluzzii-flight-around-odour-baited-trap.md
**Copy read:** PMC full text — https://pmc.ncbi.nlm.nih.gov/articles/PMC6124112/

---

## Abstract (summary)

3-D flight tracking (> 2500 tracks) of female ***Anopheles coluzzii*** in the
immediate vicinity of a commercial odour-baited trap (Suna) presented in
hanging and standing orientation, in a large field wind tunnel. Identifies two
stereotyped behaviours (downward approach; upward acceleration when close to
the trap) that produce contrasting capture dynamics.

## Key Results (as used by the model)

### Setup  [M]
* Colony: *An. coluzzii* (Suakoko, Liberia, 1987), reared at Wageningen
  University & Research, 27 °C, 70 % RH, 12 L:12 D.
* Counter-flow trap emitting a human-odour-mimicking **MB5 blend** and
  **CO2 at 5 % (200 ml min⁻¹)** from a pipe; trap entrance height 81 cm
  (hanging) — the airflow field around the entry tube reached
  **up to 3 m s⁻¹**, dropping rapidly away from the entrance (the region
  with airspeed > 1.5 m s⁻¹ was only 3 cm high × 10 cm wide).

### *A. coluzzii* flight kinematics near a strong odour source  [M]
* "Mosquitoes had their **highest mean ground speeds (up to 0.5 m s⁻¹) near
  the trap entrance**, whereas in both trap orientations they had their
  **lowest mean speeds at a radial distance of 10–20 cm from the entry tube**."
* At both the high-speed and low-speed regions the **angular speeds were
  high**; mosquitoes around the *standing* trap flew faster, had higher turn
  rates and produced higher body accelerations than around the hanging trap
  (p < 0.001).
* Mosquitoes close to the entry tube **accelerated upwards** regardless of the
  trap's orientation — for the standing trap this means escape (acceleration
  opposite to the capture airflow); for the hanging trap it means capture.
* Escaping mosquitoes flew up ~20 cm on average before turning back down,
  producing a circulating flight loop.

## Relevance to MalariaSentinel (Centinela)

The **only** primary source found that measures *A. coluzzii* flight speed in a
**real strong-odour field with CO2** rather than in a bare tunnel:

* `flight_speed_high_odour` — **up to 0.5 m s⁻¹ ground speed** near the
  odour/CO2 source, with a **speed minimum at 10–20 cm** from the source
  (a slowdown zone, not a speed-up zone). **[M]**
* This brackets the Hawkes & Gibson (2016) host-seeking ground speeds
  (0.225–0.451 m s⁻¹) from above and from a different context, and it is
  **consistent** with them: the two independent *A. coluzzii* studies give
  overlapping speed ranges (≈ 0.2–0.5 m s⁻¹) for females in a host-odour
  context. That overlap is the strongest available basis for the
  host-seeking speed of *A. coluzzii*.
* The **slow-down at 10–20 cm** is an independently measured terminal-zone
  behaviour (matching Spitzen et al. 2013's < 15 cm speed drop for
  *A. gambiae* s.s.), so the terminal-slowdown term of the movement law has
  *A. coluzzii* support as well as a proxy.

**Caveats:** the odour source is a trap (artificial MB5 blend + 5 % CO2),
not a human; the trap's own fan makes the flow field strongly non-laminar and
radially convergent, so "ground speed up to 0.5 m s⁻¹" includes wind-driven
advection and must not be read as a free-flight airspeed.

## License

CC BY 4.0 (Royal Society Open Science open access).
