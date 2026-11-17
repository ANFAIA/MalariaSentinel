# Vector bionomics and vectorial capacity as emergent properties of mosquito behaviors and ecology

**Authors:** Shou-Li Wu, Carlos H. M. Sánchez, John M. Henry, David T. Citron, Qi Zhang, Kelly Compton, Bin Liang, Abhishek Verma, David A. T. Cummings, Andrew Le Menach, Thomas W. Scott, Andrew L. Wilson, Steve W. Lindsay, Catherine L. Moyes, Paula A. Hancock, Todd L. Russell, Thomas R. Burkot, John M. Marshall, Salif Kiware, Robert C. Reiner, David L. Smith
**Journal:** PLoS Computational Biology | **Year:** 2020 | **DOI:** 10.1371/journal.pcbi.1007446
**File:** papers/anopheles-dynamics/wu-2020-mbitses-vector-bionomics-emergent-properties.md

---

## Abstract (summary)

MBITES (Mosquito Bout-based and Individual-based Transmission Ecology Simulator) is an
individual-based simulation framework that represents adult mosquitoes as a sequence of
activity bouts with explicit state transitions, plus a companion ODE (Kolmogorov forward
equations) model. The paper shows that the classical Ross–Macdonald bionomic parameters
(including the blood-feeding rate) *emerge* from simple behavioural algorithms interacting
with resource landscapes, rather than being imposed.

## Key Results (as used by the model)

- Ross–Macdonald parameterisation used: "**f** The blood feeding rate, per mosquito, per
  day; **Q** Proportion of blood meals on the pathogens' hosts; **g** The mosquito death
  rate, per mosquito, per day; **n** Extrinsic Incubation Period (EIP), in days", with
  "**S = fQ / g**" = expected number of human blood meals per mosquito over its lifetime.
- "**When a mosquito blood feeds, a random variable is drawn to determine the blood meal
  size, which affects egg maturation and batch size.**" → the canonical way to code the
  redesign: a stochastic meal size, not a binary success flag.
- "**After the blood provision has been fulfilled, which could require multiple blood
  meals, the egg batch is mature and the mosquito will become gravid.**" → the threshold
  is on *cumulative blood provision*, and completing it may take several meals.
- "**A mosquito may take multiple blood meals prior to oviposition**, which lengthens the
  time interval between successive oviposition attempts."
- "**The probability of re-feeding is a function of either the size of the previous blood
  meal or the previous egg batch**, accounting for mosquito propensity to top up the size
  of the egg batch before ovipositing." → the re-feeding probability is explicitly a
  function of the *deficit* in the previous meal.
- Three oogenesis variants are implemented: (i) phenomenological draw of a batch size from
  a Gaussian; (ii) semi-mechanistic, "**the size of the egg batch is linearly proportional
  to the size of the blood meal, in which a new blood meal adds to the egg batch size**";
  (iii) proportional, but "a new blood meal completely replaces a previous egg batch".
- "**Notably, the blood meal could infect a mosquito if the human host is infectious**"
  (infection is evaluated at each meal, not once per cycle).
- "a function has been provided to model **overfeeding**: the physiological stress of
  processing a blood meal can kill a mosquito, so it is possible to model mortality as an
  increasing function of blood meal size."

## Relevance to MalariaSentinel (Centinela)

This is the direct modelling precedent for the redesign and the source of the parameter
*structure* (not the values): a stochastic meal size, an accumulation target, a re-feeding
probability driven by the deficit, and linear egg-batch proportionality to the meal. It
also warns (overfeeding mortality) that accumulating blood without a matching survival
cost would inflate the model.

Caveats: MBITES is a generic multi-species framework with African *Anopheles* as one of
its test cases; the numbers it reports for *An. gambiae* are simulation outputs, not
primary measurements, so they cannot be copied as parameters for a Ghana case.

## License

CC-BY 4.0 (PLoS Computational Biology open access).
