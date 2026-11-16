# Visualizing non infectious and infectious *Anopheles gambiae* blood feedings in naive and saliva-immunized mice

**Authors:** V. Choumet, T. Attout, L. Chartier, H. Khun, J. Sautereau, A. Robbe-Vincent, P. Brey, M. Huerre, O. Bain
**Journal:** PLoS ONE | **Year:** 2012 | **DOI:** 10.1371/journal.pone.0050464
**File:** papers/anopheles-dynamics/choumet-2012-visualizing-anopheles-gambiae-blood-feedings-mice.md

---

## Abstract (summary)

Intravital video microscopy of *Anopheles gambiae* blood feeding on mice, plus histology of
the bite site. The paper characterises the probing and engorgement phases, including the
fraction of females that never engorge and the cases in which the female feeds on
several vessels ("pool feeding").

## Key Results (as used by the model)

- "Blood meal: **Only 46.5 % of the 200 mosquitoes observed were able to feed on blood,
  and 10 % of those able to feed were unable to feed to repletion.**"
  → (i) a per-attempt feeding-success probability well below 1, and (ii) even among
  successful feeders ~10 % stop short of repletion, i.e. a *partial* meal that does not
  switch on the gonotrophic cycle.
- "**Pool feeding was observed in 7.5 % of the engorgements.**" "However, **pool feeding
  was never sufficient for complete repletion** of the female." → the physiological
  mechanism for interrupted feeding: the female moves between vessels and does not reach
  repletion.
- "Repletion was achieved by **capillary feeding**." (i.e. feeding from a vessel, not
  pool feeding, is what produces a full meal.)
- "infected females tending to **probe more than uninfected females (86 % versus 44 %)**"
  (sporozoite-infected females probe more; also quoted in
  `takken-2024-adult-anopheles-gambiae-behaviour-review.md`).
- "…the **number of hosts bitten by the *Plasmodium*-infected mosquito to achieve
  complete repletion**" is noted as a mechanism whereby infection alters feeding
  behaviour (infection → more hosts per meal).
- "These observations contrast with those for blood feeding by *Aedes aegypti*, which can
  become fully engorged after pool feeding."

## Relevance to MalariaSentinel (Centinela)

Directly supports three engine elements: (1) `feeding_success_rate` is a real probability
< 1 applied per attempt; (2) a successful attempt does **not** imply a full meal — a
partial meal must be modelled and the female must keep seeking; (3) the "blood meal"
event can involve more than one host contact, so the ledger must accept several events per
female per night.

Caveats: laboratory colony of *An. gambiae* (strain not stated as coluzzii), mouse host
(haematocrit and vessel depth differ from human skin), 2012; the paper does **not**
report the ingested volume in µL — the "3–4 µL" figure that cites this paper was not
found in the full text of this article, so it should not be attributed here with
confidence.

## License

CC-BY 4.0 (PLoS ONE open access).
