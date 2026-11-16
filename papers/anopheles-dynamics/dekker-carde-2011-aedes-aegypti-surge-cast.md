# Moment-to-moment flight manoeuvres of the female yellow fever mosquito (*Aedes aegypti* L.) in response to plumes of carbon dioxide and human skin odour

**Authors:** Teri Dekker, Ring T. Cardé
**Journal:** Journal of Experimental Biology | **Year:** 2011 (214(20):3480–3494) | **DOI:** 10.1242/jeb.055186
**File:** papers/anopheles-dynamics/dekker-carde-2011-aedes-aegypti-surge-cast.md
**Copy read:** **PubMed abstract only** (PMID 21957112) — https://pubmed.ncbi.nlm.nih.gov/21957112/
**Access status:** the article is free-to-read on the publisher site ("bronze"
open access) but the publisher returned HTTP 403 to both plain `curl` and a
headless browser, and OpenAlex/Unpaywall report **no repository full text**.
Everything below is therefore taken from the abstract; the full-text numbers
could not be read. **[NO-VERIFICADO] where marked.**

---

## Abstract (summary)

3-D video analysis of female ***Aedes aegypti*** flying in a wind tunnel in
response to host-odour plumes with different spatial structure and composition.
The paper establishes the **surge-and-cast** mechanism: a brief CO2 encounter
triggers an upwind surge, and when no further CO2 is encountered the mosquito
counterturns and casts across the windline, repeatedly transecting the area
where CO2 was last detected.

## Key Results (as used by the model)

* "Following a brief (**~0.03 s**) encounter with CO2, mosquitoes **surged
  upwind** and, in the absence of further encounters, **counterturned without
  displacing upwind**." **[M]** (abstract, *Aedes aegypti*)
* "CO2 encounters induced a **highly regular pattern of counterturning across
  the windline in the horizontal (crosswind) and vertical planes**, causing the
  mosquito to transect repeatedly the area where CO2 was previously detected."
  **[M]**
* "despite the rapid changes across all three axes following an encounter with
  CO2, the **angular velocities remained remarkably constant**" — suggesting
  stabilisation of flight via halteres and Johnston's organs (Coriolis
  sensing). **[M]**
* "a **brief encounter with a filament of human skin odour did not induce a
  consistent change** in mosquito flight." **[M]** — i.e. the CO2 and skin-odour
  channels are *not* interchangeable; CO2 is the fast trigger.
* "A **broad homogeneous plume of skin odour induced rapid upwind flight and
  source finding**, whereas a **broad filamentous plume of skin odour lowered
  activation rates, kinetic responses and source finding** compared with
  homogeneous plumes." **[M]** — direct evidence that **plume intermittency
  reduces host-finding rate**.
* Species: ***Aedes aegypti*** — **not** *Anopheles*. **[NO-VERIFICADO] as an
  Anopheles parameter.**

### What could NOT be verified  [NO-VERIFICADO]
The synthesis attributes a **"~2 s casting latency after contact with a CO2
filament"** to this paper. **No such number appears in the abstract**, and the
full text could not be accessed. The only latencies traceable to an
accessible primary source are:
* **~0.03 s** CO2 encounter duration (this paper's abstract);
* **300 ms** to orient upwind on plume entry and 300 ms to cast on plume exit
  (Dekker et al. 2005, quoted in Hawkes 2013 PhD thesis, §"Plume following").

## Relevance to MalariaSentinel (Centinela)

* It is the **primary mechanistic source for the surge-and-cast state machine**
  that the movement law implements (upwind surge while a plume filament is
  detected; crosswind casting when it is lost) — but the evidence is
  ***Aedes aegypti***, so it is a **[P] proxy** for *A. coluzzii*.
* It provides the **"broad homogeneous plume vs filamentous plume"** result
  that justifies the model's treatment of an outdoor plume as intermittent:
  the filamentous plume *reduced* activation rates and source finding. **[P]**
* It shows the **fast CO2 trigger vs slow skin-odour trigger** asymmetry:
  in the movement law, CO2 should switch the mosquito into "search" state
  immediately, while host-odour should modulate the *strength* of the
  upwind bias rather than the state transition. **[P]**

**The "~2 s casting latency" parameter must be treated as [EP] until a
primary source is obtained** — it cannot be sourced to this paper.

## License

**[NO-VERIFICADO]** — the publisher page was unreachable (HTTP 403), so the
licence statement could not be read. Crossref/OpenAlex report the article as
"bronze" open access (free to read on the publisher site, no Creative Commons
licence, no repository copy).
