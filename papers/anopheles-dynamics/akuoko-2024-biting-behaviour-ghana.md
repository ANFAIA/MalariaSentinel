# Biting behaviour, spatio-temporal dynamics, and the insecticide resistance status of malaria vectors in different ecological zones in Ghana

**Authors:** Osei K. Akuoko, Shittu B. Dhikrullahi, Isaac A. Hinne, Abdul R. Mohammed, Christopher M. Owusu-Asenso, Sylvester Coleman, Samuel K. Dadzie, Rosina Kyerematen, et al.
**Journal:** Parasites & Vectors | **Year:** 2024 | **DOI:** 10.1186/s13071-023-06065-9
**File:** papers/anopheles-dynamics/akuoko-2024-biting-behaviour-ghana.md

---

## Abstract (summary)

The study characterised the spatio-temporal dynamics, biting behaviour and
insecticide-resistance status of malaria vectors across different ecological
zones in Ghana, in a context of high LLIN/IRS coverage and widespread
pyrethroid resistance. Hourly human-landing and indoor/outdoor collections
were used to describe when and where the main vectors bite.

## Key Results (as used by the model)

- The paper reports the hourly biting-activity distribution used to justify
  `species.<row>.activity_weights` (`[DAY, EVENING, NIGHT, DAWN]`): most
  biting happens late at night, with a smaller early-morning component.
- It documents differences between ecological zones and vector species, which
  is why the YAML keeps one activity row per species.

## Relevance to MalariaSentinel (Centinela)

Source for the phase-level `activity_weights` in `model_constants.yaml`.
The model does not reproduce the paper's entomological rates; it only uses the
relative hourly activity shape.

## License

CC-BY 4.0 (BMC Open Access).
