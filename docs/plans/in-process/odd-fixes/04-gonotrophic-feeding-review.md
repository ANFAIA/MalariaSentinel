# Pack 04 — Gonotrophic cycle and feeding realism

> Source: ODD 2010 review notes.
**Document sections invalidated (CUJ-4):** `docs/concepts/abm/odd-2010-malariasentinel.tex` → §2.2 "State variables", §7.4 "Run the gonotrophic cycle", §7.5 "Seek an oviposition site and oviposit", §7.6 "Seek hosts and feed".
When this pack is decided and applied, these are the passages that
must change; the document is amended in the commit that applies the
pack, not in the pack itself.
 Status: initial plan — to be detailed later.

## Objective

Review the gonotrophic state machine against mosquito biology: feeding
frequency, fixed vs. environment-driven timings, real mating, the necessity
of the oviposition-seeking phase, and the phase-weight gating of bites.

## Notes (verbatim)

- **p.6** (schedule table) — "If fed female is skipped in later phases, it only fed once?"
- **p.6** (patch snap) — "Adelts must oviposit near themself"
- **p.4** (`gonotrophic_cycles`) — "why? Possible unnecessary variable (to review)"
- **p.4** (`patch_id`) — "(!) careful patch eggs are leaved where female leaves"
- **p.7** (same-day feeding) — "Feeding must be reviewed, as mosquitoes do not fed only once per day."
- **p.6** (starvation) — "without knowing if hosts are not ABMs" *(also in pack 03)*
- **p.10** (instantaneous mating) — "Implications on mosquito behaviour?"
- **p.21** (OVIPOSITION_SEEKING) — "Does this phase really exist? → studies against → eggs at female position (as approximation to real behaviour)"
- **p.22** (mating) — "should happen when female copulates."
- **p.22** (timings) — "1 fed per day?" / "Review timings, seems fixed dates, when its mortality is based on environment, the rest is not? This behavior limit oviposition and blood feeding." / (resting) "Review this phase as it consumes one day."
- **p.29 A.4** (phase weights) — "Remove this useless weights and change them by some kind of number that balance the number of bites per day or phase of day, based on studies"
- **p.29** (foot of page) — "Biting calculated once per day as an accumulation of bites per day + probability of successful bite in the zone where it is"

## Initial steps

1. Decide feeding semantics: multiple feeds per day vs. one accumulation
   with a success probability (aligns with the p.29-foot note). This must
   be organized with the movement of the mosquitoes, when feeding they must
   feed of the preys in their path of that day (imagine it as two parallel
   lines to the movement of the mosquito, limiting its range of fed, and,
   the nearest to the borders the less probable that the mosquito bites that
   agent (always dependent on species and mosquitoes preferences)).
2. Review the state-machine timings: fixed day counts (RESTING 1 d,
   EGG_MATURING 4/2 d) vs. temperature/environment-driven durations.
   This review must be based on papers and studies on mosquitoes behaviour.
3. Replace instantaneous mating with copulation-triggered mating. This will make
   male mosquitoes to have some relevance.
4. Evaluate removing OVIPOSITION_SEEKING in favour of eggs-at-female-position
   (cross-ref pack 02/03).
5. Replace phase activity weights with bite-balancing weights derived from
   studies (which in practice means what is explained in parenthesis in step 1);
   drop the unused `feeding_success_rate` question into pack 02.
6. Review `gonotrophic_cycles` and `patch_id`-related egg placement
   correctness ("eggs are leaved where female leaves").

## Dependencies / open points

- Depends on pack 03 (movement) for how a female reaches hosts/sites.
- Calibration scorers (M7.4.x) will shift — rerun the calibration suite.
