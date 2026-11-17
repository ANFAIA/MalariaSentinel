# Inhibition of host-seeking response and olfactory responsiveness in *Anopheles gambiae* following blood feeding

**Authors:** W. Takken, J. J. van Loon, W. Adam
**Journal:** Journal of Insect Physiology | **Year:** 2001 | **Volume/Pages:** 47(3): 303–310 | **DOI:** 10.1016/S0022-1910(00)00107-4 | **PMID:** 11119776
**Open access URL:** none (Elsevier, subscription). Abstract read via PubMed: https://pubmed.ncbi.nlm.nih.gov/11119776/
**File:** papers/anopheles-dynamics/takken-2001-inhibition-host-seeking-blood-feeding-gambiae.md

---

## Abstract (summary)

Laboratory study (Wageningen, Netherlands) of the effect of a single blood meal on
host-seeking and olfactory (EAG) responsiveness of *Anopheles gambiae*. Five-day-old
females of one size class were fed on a human arm and tested in an olfactometer at
3, 24, 40, 48 and 72 h post-blood-meal (pbm) against age-matched unfed controls.
This is the classic measurement of the **postprandial host-seeking refractory
window** and of the **ovarian stage (Christophers I–V) at which host seeking
resumes**.

## Key Results (as used by the model)

- Host-seeking response after a blood meal (behavioural bioassay):
  "There was **no host-seeking response at 3 and 24 h pbm**. **Seven percent**
  of the mosquitoes responded to human emanations **40-h pbm, 27% at 48 h and
  68% at 72 h** following a blood meal. The average response of controls to
  host stimuli varied from 35 (at t = 40 h) to 67%."
  → the **host-seeking gate is fully closed for the first 24 h** and re-opens
  progressively between 40 and 72 h (i.e. a ~2–3 day gonotrophic cycle in the
  laboratory).
- Electroantennogram (EAG) to incubated human sweat, hexanoic acid, indole and
  geranyl acetone: "Maximum EAG amplitudes recorded from blood-fed and control
  mosquitoes were **similar for mosquitoes in Christophers' stages I–III**,
  whereas in **stage IV EAG amplitudes recorded from the blood-fed group were
  significantly lower** than those of the corresponding control group in response
  to headspace of incubated human sweat and to indole."
  → the **chemosensory (olfactory) down-regulation is state-dependent and
  appears at Christophers stage IV**, i.e. when oocytes are maturing — it is a
  *behavioural/physiological* gate, not a blood-volume gate.
- Ovarian state at the moment host seeking resumes: "Of the mosquitoes that
  responded to host odour **48 h pbm, 12.5% (n = 5) had ovaries in
  Christophers' stage IV** and the remainder in stage V. Of the mosquitoes that
  responded **72 h pbm, 66.7% (n = 94) had ovaries in stage V and 31.2% (n = 44)
  had recently oviposited**."
  → host seeking resumes **at/after Christophers stage V (gravid)**, i.e.
  essentially when the female is ready to oviposit, not at the start of the
  cycle.
- Conclusion quoted verbatim: "The results show that there was a **strong
  inhibition of host seeking in *An. gambiae* for a period of at least 40 h
  following a blood meal. Host-seeking returned to pre-blood meal levels 72-h
  post feeding and was associated with egg maturation.**"

## Relevance to MalariaSentinel (Centinela)

- The canonical citation for the **`BLOOD_FED` → `RESTING` → `EGG_MATURING`
  ordering** and for a *host-seeking gate that is closed for ~40–72 h after a
  meal*: in the engine, `resting_duration_days` is currently 0.5 d and
  `cycle_duration_days` 2.0 d, i.e. the female becomes host-seeking again
  before the evidence says it can respond to host cues.
- It also ties host-seeking resumption to **Christophers ovarian stage V**
  (gravid) rather than to elapsed days, which is an argument for an explicit
  ovarian/physiological state variable rather than a pure age counter.
- Caveats: laboratory *An. gambiae* (G strain), Netherlands, single blood meal,
  human arm feeding, olfactory responses to sweat and indole only — **not CO₂**,
  and **no visual/opsin measurements**. The paper does not report any CO₂
  sensitivity measurement and no opsin data.

## License

Not open access (Elsevier). Reproduced here as bibliographic record + verbatim
quoted abstract text (PubMed record, PMID 11119776) for academic research.
