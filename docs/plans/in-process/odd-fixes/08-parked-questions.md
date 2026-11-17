# 08 — Parked design questions

> **Status**: pending (2026-11-17). This document holds **only work that has not been
> done**: the questions that the ODD review parked and that no plan has answered yet.
> The one that *has* been answered — the male/female survival difference — is recorded
> at the end for traceability and is **not** repeated as pending work.
> **Source**: ODD 2010 review notes
> (`.cache/odd-latex/odd-2010-malariasentinel-notes.tex`), pack 13.
> **ODD sections to amend when this is applied**: §4.3 "Adaptation", §4.6
> "Prediction", §6 "Input data" (the asynchronous-loading question).

## Objective

Give each parked question a short, bounded pass — a literature scan and a decision
recorded here: **keep**, **change**, or **defer** — and promote every "change" into a
plan of its own.

## Index

| # | Question | Note |
|---|---|---|
| 8.1 | Is the absence of adaptation acceptable? | p.9 |
| 8.2 | Should there be a prediction phase? | p.9 |
| 8.3 | Should the environment be loaded asynchronously, in chunks? | p.12 |

---

## 8.1 Adaptation

**Note (verbatim)** — **p.9**: "Is this lack of adaptation good?"

**What the question is about.** The model has no learning and no evolution within a
run: the behaviour of the mosquitoes does not change in response to what happens in
the AOI (no insecticide resistance selection, no learning of host preference, no
density-dependent behaviour change).

**Decision needed.** Is that an acceptable property of the model (a scope statement),
or a gap that the elimination programme will hit? If it is a gap, the smallest useful
version of it is a parameter that changes over time (resistance frequency) — and that
raises the question of where the input comes from.

**Done when.** The ODD says, in one paragraph, whether the model represents adaptation
and, if not, what the programme is expected to use instead.

---

## 8.2 A prediction phase

**Note (verbatim)** — **p.9**: "should there be a prediction phase? Studies..."

**What the question is about.** The model simulates one scenario forward. Should it
also *anticipate* (a forecast mode: given a future climate, produce a risk map
earlier than the simulation would), or is the simulation itself the prediction?

**Decision needed.**

1. Is a distinct prediction phase needed, given that the pipeline already has a
   `prediction` stage (the U-Net over the state COG)?
2. If yes, what does the mosquito anticipate: the climate (weather beyond the
   window), the intervention (a coverage map), or the population (density feedback)?
3. Which published work describes the mechanism that would be modelled (the note asks
   for studies).

**Done when.** Either the ODD states that the simulation is the prediction and the
question is closed, or a scoped plan exists.

---

## 8.3 Asynchronous environment loading

**Note (verbatim)** — **p.12**: "What if load asynchronous per frames? weeks / month".

**What the question is about.** The climate and the habitat planes are loaded for the
whole simulation window up front (the environmental NetCDF is read once); the note
asks whether the environment could be loaded progressively (week by week, month by
month), as in a streaming setup.

**Decision needed.** Is the up-front load a real constraint (memory, or the inability
to run a rolling forecast), or an implementation convenience? If it is a constraint,
what is the target horizon and resolution, and does the C++ side need a reader that
fetches blocks on demand?

**Done when.** The answer is recorded, and if streaming is wanted, the reading
interface it requires is named.

## Dependencies / open points

- 8.1 overlaps with the survival question of document 05 (5.8): decide the parameter
  first, then the scope.
- 8.2 overlaps with the `prediction` stage of the pipeline and with the surrogate
  (whose checkpoints are not reusable across contract versions).
- 8.3 overlaps with document 01 (the ingest pipeline) and with the climate reader
  (`env_reader.hpp`, `climate.hpp`).

---

## Closed question (kept for traceability)

- **p.27** (adult survival) — "Review male/female difference." **Answered** in
  `docs/plans/in-process/individualization-and-movement.md` §8.6: the male gets its
  own survival, `male_daily_survival = 0,773 ± 0,094` per day **[M]**, against the
  0.87 shared by the female (a ~12 % over-estimate of males), with the sugar
  dependency as the mechanism **[EP]** (with sugar 3.84–4.94 days of life; without
  sugar 1.94–2.99; Gary et al. 2009 **[P]**).
