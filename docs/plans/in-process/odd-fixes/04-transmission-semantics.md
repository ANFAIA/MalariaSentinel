# 04 — Transmission semantics and Ross–Macdonald coherence

> **Status**: pending (2026-11-17). This document holds **only work that has not been
> done**. The bite ledger, the individual transmission events and the human individual
> layer are designed in `docs/plans/in-process/individualization-and-movement.md`
> (§2, §6, §11); what remains here is the **semantics of the transmission layer
> itself**, which that plan does not decide.
> **Source**: ODD 2010 review notes
> (`.cache/odd-latex/odd-2010-malariasentinel-notes.tex`), pack 11.
> **ODD sections to amend when this is applied**: §4.1 "Basic principles", §5.3
> "Humans, transmission, hosts, mobility, and wind", §7.9 "Transmit parasites",
> Appendix A.12.

## Objective

Answer four questions about the transmission layer: do bites recorded on the day a
mosquito dies count; is the extrinsic incubation period (EIP) even survivable with
the current mortality; is the human in `E_H` infectious to mosquitoes; and does the
implementation cohere with the Ross–Macdonald reference it claims to implement.

## Index

| # | Question | Note |
|---|---|---|
| 4.1 | Do mosquitoes that transmit on the day they die affect anything? | p.7 |
| 4.2 | Is the EIP feasible with the current adult survival? | p.27 |
| 4.3 | Is the human infectious to the mosquito during `E_H`? | p.28 |
| 4.4 | Is the implementation coherent with the Ross–Macdonald paper? | p.7, p.10 |
| 4.5 | (Future) Host behavioural response to malaria and to biting | p.10 |

---

## 4.1 Bites on the day of death

**Note (verbatim)** — **p.7** (schedule consequence): "Mosquitoes that transmit the
same day that die, should affect."

**Current state.** The bite ledger survives the mosquito's death (the ledger is
updated by the feeding phase, and the EIP/SEIR block runs **after** mortality), so a
bite recorded earlier in the day does contribute to today's transmission update even
if the mosquito dies that same day.

**Decision needed.** Which semantics?

1. A bite that happened **before** the mosquito dies counts (the event is real);
2. or only bites by mosquitoes that **survive** the day count (the day's
   transmission is computed on the surviving population).

Both are defensible; they are not the same number. Whichever is chosen, the ODD's
daily order (the EIP/SEIR block runs after mortality) and the ledger's semantics have
to say so explicitly, and the scenario harness has a case for it.

**Done when.** The daily order in the ODD and the rule in the code agree, and one of
the synthetic scenarios asserts the difference (it changes the value, so it must be
visible).

---

## 4.2 EIP feasibility

**Note (verbatim)** — **p.27**: "Very unlikely females survive until it gets infectious
with current values → analyze this."

**Current state.** The EIP is a degree-day model: `eip.base_c = 16.0` °C and
`eip.threshold_gd = 110.0` degree-days (`model_constants.yaml:192-193`). At the
optimum (25 °C) that is **12.2 days**; the mean adult lifetime at the current
mortality (`adults.daily_mort_basal = 0.87`, i.e. 1/0.87 ≈ 1.15 d⁻¹, so a mean life
of ≈ 7.2 d) is **shorter than the EIP**: a large fraction of infected females never
become infectious.

**Decision needed.**

1. Quantify it: what fraction of infected females ever become infectious, at the
   temperatures of the AOIs in question? (This is the analysis the note asks for; it
   is a number, and it belongs in the ODD.)
2. If the fraction is very small, is the transmission model still the right one for
   this region (it would mean the observed malaria comes from a different
   mosquito–temperature regime), or is the EIP model wrong?

**Done when.** The fraction is computed, reported, and the ODD states it; if it
contradicts the model's usefulness, that is escalated as a finding, not smoothed over.

---

## 4.3 Is the human in `E_H` infectious to mosquitoes?

**Note (verbatim)** — **p.28**: "is human infectious in E_H phase for mosquito".

**Current state.** The human SEIR block has `transmission.human_incubation_days = 12`
(`E_H`→`I_H`) and `transmission.human_infectious_days = 20`; `beta_vh = 0.50`
per bite is the vector→human probability and `beta_hv = 0.40` the human→vector one.

**Decision needed.** Is `E_H` (exposed, incubating) already infectious to mosquitoes,
or only `I_H`? The malaria biology says the parasite is not transmissible during
incubation, but the ODD and the code must say it in the same terms. Also: with a
12-day incubation and a 20-day infectious period, which human compartment feeds
`beta_hv`?

**Done when.** The ODD and the implementation state which human compartment is
infectious to the vector, and the state machine in `transmission.cpp` matches.

---

## 4.4 Coherence with Ross–Macdonald

**Note (verbatim)** — **p.7** (basic principles): "Ensure truly coherence with the
paper" — **p.10** (vector–host contact): "It should? Effect of malaria on human
behaviour."

**Current state.** The transmission block is described as "SEIR-SEI Ross-Macdonald
(`transmission.hpp`)" in the YAML comment, but the audit has never been done
equation by equation.

**Decision needed.** Audit the implementation against Macdonald (1957) and Smith &
McKenzie (2004), equation by equation, and record the coherence — and, more usefully,
the places where the implementation **deviates deliberately** (the human individual
layer, the bite ledger, the "survival of the vector is set by adult mortality, not by
the transmission block" arrangement). Each deviation needs a reason.

**Done when.** There is a table in the ODD (or an appendix) with one row per equation:
symbol, implementation, agreement or deviation, and the reason for the deviation.

---

## 4.5 Host behavioural response (future)

**Note (verbatim)** — **p.10**: "Effect of malaria on human behaviour."

**Scope note.** The two papers the original note carried
(<https://www.science.org/doi/10.1126/science.aah4563>,
<https://journals.plos.org/plosbiology/article?id=10.1371/journal.pbio.0030298>) are
the starting material. This is explicitly **out of scope** for the current work: the
redesign keeps human mobility out of the model (its N2), and a behavioural response to
malaria is a further step.

**Done when.** (Future work, not now.) A scoped note exists saying what would have to
change in the human layer.

## Dependencies / open points

- The findings may change `beta_hv`, `beta_vh` or the EIP constants → the provenance
  audit (document 05) must be re-run on those keys.
- 4.1 depends on the daily order of the processes (the ODD's §7.9) and on the
  redesign's bite ledger: the semantics are easier to fix once the ledger carries
  individual events.
- 4.2 needs a scenario with a small, well-conditioned population (animals, mosquitoes
  and humans) — the redesign's synthetic harness is the natural place for it.
- 4.4 is a read-only audit; it needs the transmission source and the two references,
  nothing else.
