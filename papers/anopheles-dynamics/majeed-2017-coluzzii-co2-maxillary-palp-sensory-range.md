# Detection and perception of generic host volatiles by mosquitoes: responses to CO2 constrains host-seeking behaviour

**Authors:** S. Majeed, S. Hill, T. Dekker, R. Ignell
**Journal:** Royal Society Open Science | **Year:** 2017 (4(5):170189) | **DOI:** 10.1098/rsos.170189
**File:** papers/anopheles-dynamics/majeed-2017-coluzzii-co2-maxillary-palp-sensory-range.md
**Copy read:** PMC full text — https://pmc.ncbi.nlm.nih.gov/articles/PMC5451829/

---

## Abstract (summary)

Single-cell recording from the maxillary palp capitate peg sensilla of
***Anopheles coluzzii***, *Aedes aegypti* and *Culex quinquefasciatus*, plus a
flight-tube bioassay, to determine how the dynamic range and coding capacity
of the CO2-sensitive olfactory receptor neurons (ORNs) constrain behavioural
host-seeking responses to CO2.

## Key Results (as used by the model)

### Species and strains  [M]
***Anopheles coluzzii*** (Suakoko strain, previously the *An. gambiae* M
molecular form), *Aedes aegypti* (Rockefeller), *Culex quinquefasciatus*
(Thai). Reared 27 ± 2 °C, 70 ± 2 % RH, 12 h:12 h L:D.

### Electrophysiology (maxillary palp, "A" cell of the capitate peg sensilla)  [M]
* **The threshold of the neuronal response to CO2, in a 0 ppm CO2 background,
  was lowest for *An. coluzzii*.** At **150 ppm and 300 ppm CO2** the ORN
  activity was significantly higher in *A. coluzzii* than in *Ae. aegypti* and
  *Cx. quinquefasciatus* (t = 3.12, df = 8, p < 0.05; t = 4.80, df = 8,
  p < 0.001; t = 3.09, df = 8, p < 0.05).
* Stimulus train: **single CO2 pulses of 1 s with 1 s inter-stimulus
  interval**; concentrations used **150, 300, 600, 1200, 2400 and 4800 ppm**.
* At **600 and 1200 ppm** the A cell of **all three** species detected **and
  tracked** the pulsed stimuli. **At higher concentrations all species still
  detected the pulses, but only *Ae. aegypti* and *An. coluzzii* could track
  them** (fire throughout each pulse); the *Cx. quinquefasciatus* A cell
  adapted to each pulse.
* Discussion statement: "The dynamic range of their CO2-sensitive ORNs is
  wide, with a **threshold at or below ambient concentration (350–400 ppm)**,
  and the neurons **do not reach their maximal response at the highest dose
  tested (4800 ppm)**."
* *Cx. quinquefasciatus* contrast: its CO2-sensitive ORNs "rapidly adapt and
  disadapt more slowly when stimulated with multiple pulses of high CO2
  concentrations (≥ 2400 ppm)", i.e. saturation/adaptation.

### Flight-tube bioassay (pulsed CO2)  [M]
* Flight tube (2.5 cm i.d.); **background CO2 385.4 ± 6.28 ppm**
  (variation 1.3 ± 0.60 ppm over the experiment); charcoal-filtered humidified
  air 25 ± 2 °C, RH 65 ± 2 %, flow **30 cm s⁻¹**; illuminance 280 lux (white
  light) for the diurnal *Ae. aegypti*, **40 lux red light** for the nocturnal
  *An. coluzzii* and *Cx. quinquefasciatus*; pulsed CO2 delivered through a
  pulse generator mixing pure CO2 with pressurised air at **4.5 l min⁻¹**, at
  600, 1200, 2400 or 4800 ppm.
* Time to activation was **increased** in *Cx. quinquefasciatus* relative to
  *Ae. aegypti* and *An. coluzzii* at concentrations above 1200 ppm
  (2400 ppm: t-ratio −4.88 / −8.48, p < 0.0001; 4800 ppm: −3.72 / −7.53,
  p = 0.0035 / < 0.001).
* Time to reach halfway along the tube was significantly shorter for
  *Ae. aegypti* and *An. coluzzii* than for *Cx. quinquefasciatus* above
  600 ppm; **at 4800 ppm *An. coluzzii* took as long as *Cx. quinquefasciatus*
  to reach halfway, significantly slower than *Ae. aegypti* (t-ratio −3.16,
  p = 0.0248)**.
* **93–100 %** of *Ae. aegypti* and *An. coluzzii* reached halfway, and
  **87–100 %** made source contact, at every concentration tested.
* Authors' framing: "the CO2-chemosensory systems of *Ae. aegypti* and
  *An. coluzzii* are equipped to detect a wide range of CO2 emissions, from
  **rare and intermittent CO2 signals at a distance of several metres** from a
  potential host to amounts equivalent to that emitted by a human".

## Relevance to MalariaSentinel (Centinela)

This is the primary source for the **CO2 sensing sub-model**, and it is
*A. coluzzii*-specific:

* `co2_threshold_ppm` — **≤ 350–400 ppm** (i.e. at or below the ambient
  background, 385.4 ± 6.28 ppm in their flight tube; 460 ± 5 ppm in the
  Hawkes & Gibson 2016 tunnel). *A. coluzzii* has the **lowest** ORN
  threshold of the three species tested. **[M]**
* `co2_dynamic_range_ppm` — **600 to 4800 ppm, tracked without saturating**
  (pulse tracking confirmed at all four concentrations tested). **[M]**
* `co2_pulsed_vs_continuous` — the whole design rests on **1 s pulses with 1 s
  gaps**. A continuous-CO2 detector with a saturation ceiling is the wrong
  model; the detector should be a **pulse/fluctuation detector**, matching
  the finding of Gillies (1980) that sustained flight requires an
  intermittent stimulus. **[M]**
* Practical consequence for the movement law: because the *A. coluzzii* ORN
  threshold is at or below ambient, **CO2 cannot be used as a long-range
  "distance sensor"**; it acts as an *activation* trigger when a plume
  filament raises the local concentration above the fluctuating background.
  This is exactly the semantics the "CO2 activation without directional
  orientation" term in Lorenz et al. 2013 needs.

**Caveats:** the 350–400 ppm "threshold" is an inference from an ORN
dose–response in a 0 ppm background, not a behavioural detection distance;
no distance-to-host is measured in this paper.

## License

CC BY 4.0 (Royal Society Open Science open access).
