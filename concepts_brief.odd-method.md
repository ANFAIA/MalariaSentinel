# The ODD as a questioning stance — research note

Source: read-only investigation of `.cache/odd-latex/` (the ODD 2010 description of
`mal_abm_fast`, the review copy with ~85 handwritten comments, and the official
2010/2020 templates). Every claim below is cited to file:line. The section map of
the reference document was verified directly against the `.tex` headings
(`Purpose` :132, `Entities` :188, `Process overview` :352, `Design concepts` :477,
`Initialization` :771, `Input data` :953, `Submodels` :1017, `Implementation notes` :1728,
`Provenance, versioning, and testing status` :1857).

## Why this note exists

The author rejected a generic section template shared by all stages: it would
produce "generic documentation of each section" instead of an explanation of the
theory. What the author values in the ODD is not its question list but the
**frame of thought** it imposes on the author — a stance within which asking the
right questions surfaces inconsistencies and improvements.

So the question this note answers: what is that stance, stated independently of
the ODD's element list, and what survives the transfer to stages that are not
simulations?

## Finding 1 — The value of the ODD is the audit discipline it induces, not the section list

The ~85 reviewer comments in `odd-2010-malariasentinel-notes.tex` split three ways:

| Category | Themes | What it means for us |
|---|---|---|
| **Criticisms of documentation adequacy** | T2 aggregation level / agency (`notes:238, 248, 900, 1393, 1472`), T5 where randomness and parameters live (`notes:726, 745, 966, 1841`), T6 output resolution design (`notes:758, 765, 792`), T7 duplicated state and dead internals (`notes:321-322, 1093, 1814, 1851`), T1's third provenance tier (`notes:1140, 1141, 1256, 1533`) | Inherited if we copy the format without its review discipline |
| **Author's implementation weakness** | T1 priors without evidence (`notes:676, 1370, 1877`), T6 ununified outputs and placeholder hashes (`notes:758, 1857, 1866`), T7 duplicated state, species-neutral habitat row, unused constructor (`notes:1730-1819` in the doc's own Appendix A) | Inherited if we copy the ODD *as written* without the discipline that produced it |
| **Model science** | T3 movement (`notes:586, 1387, 1533, 1570`), T4 daily-discretisation biology (`notes:466, 1313, 1325, 1696`), T8 modelling adequacy (`notes:1040, 1211, 1267`) | Would be made about the code anyway |

The decisive observation: **the reviewer's most damaging criticisms are all
criticisms of documentation adequacy, not of the model.** The comments that attack
the science would have been made regardless. So the format's value is not in its
sections; it is in the discipline of writing something that a hostile reader can
check against the code.

The reference document's own Appendix A — 14 numbered implementation notes, each
naming a file or function and stating a fact not visible at protocol level
(`odd-2010-malariasentinel.tex:1728-1855`) — is the evidence. Writing it surfaced
eleven code defects: `feeding_success_rate` loaded but never drawn, two enum states
never entered, a `MultirateDayState` member never advanced, three aquatic mortality
RNGs re-seeded daily with fixed constants, the GeoPackage `dynamics` column read as
int but stored as string, `"sha256:pending"` in the sidecar, `eip_frac` that is not
an EIP fraction, `daily_mort_basal` that is a survival probability.

## Finding 2 — The load-bearing devices, and which transfer

| Device | Where | What it buys | Transfers to `download`? |
|---|---|---|---|
| **Notation table** with the code-name alias in the symbol's parenthesis | `:102-131` | Lets a reader hold document and source in one head; makes the Appendix-A defects checkable | Yes — same function, different nouns |
| **Schedule pseudocode + schedule table + consequences list** | `:367-497` | The consequences list turns an ordering into falsifiable claims about results ("No within-day feedback from adults to habitat"; "Aquatic promotions do not cascade") | Yes, at pipeline granularity: catalog → resolve → fetch → materialise → aggregate → write, and what each order forecloses |
| **Parameter tables with a Provenance column** | `:1086, 1185, 1305, 1360, 1462, 1552, 1600, 1683`; vocabulary at `:1028-1035` | Makes the epistemic status of every number checkable by a third party | Yes, verbatim |
| **"Consequences worth stating" block per submodel** | e.g. `:1236-1243, 1380-1388, 1497-1502` | Turns description into explanation; this is what reviewers hooked into | Yes |
| **"Origin and rationale" block per submodel** | alongside the above | Separates what the mechanism *is* from *why it was chosen* | Yes |
| **§5.5 "What is data-based and what is a scenario choice"** | `:941-951` | Names which numbers are measurements, which are estimates, which are choices | Yes — and it is an **addition to the ODD**, not an element of it |
| **Negative purpose list** ("The model is *not* intended for…") | `:168-177` | Gives the reader a filter and the author a scope boundary | Yes |
| **Declaration of absences** ("Not implemented", "Absent from the delivered Ghana product", states the code never enters) | `:603-620, 719-728, 1002, 1742-1749` | Makes incompleteness visible instead of silent; mandatory in ODD 2020 (`odd-2020-template.tex:191-208`) | Yes |
| **Appendix A — implementation notes for replicators** | `:1728-1855` | The place where protocol-level description admits it cannot capture the implementation | Yes |
| **Appendix B — provenance, versioning, testing status** | `:1857-1900` | States what is verified, what is not, and what the artefact must not be used for | Yes |
| **Element 2 — entities, state variables, scales** | `:188-351` | Forces the level-of-aggregation decision to be explicit | **No** — intrinsic to a simulation. The reviewers attacked this hardest precisely because the ODD assumes entity choice is settled (`notes:238, 248, 900, 1393`) |
| **Element 3 — synchrony / asynchrony, time discretisation** | `:352-476` | The *concern* (order affects results) transfers; the *vocabulary* does not | Partly — as pipeline order, not as simulation scheduling |
| **Element 4 — the eleven design concepts** | `:477-770` | Eleven of the twelve are about agency (emergence, adaptation, objectives, learning, prediction, sensing, interaction, stochasticity, collectives, observation) | Only **stochasticity** (which draws, from what seed) and **observation** (what is emitted, at what resolution, who consumes it) have clean analogues |
| **Element 5 — t=0 seeding as a population question** | `:771-940` | Forces the initial world to be complete | Weakly — the file-level analogue is "what is present before the first call" |
| **Element 7 — each submodel independently calibrated and tested** | `:1017-1727` | Demands evidence per parameter | Partly — the *ordering* (equations → rationale → table) and the evidence demand transfer; the calibration demand presumes a behavioural model |

## Finding 3 — Gaps in the ODD format itself

These are the questions the ODD does *not* ask, which is why the reference
document had to invent answers:

1. **No element asks the level of aggregation** of each represented phenomenon, or
   whether the representation supports it. The reference's "Biological resolution"
   paragraph (`:313-320`) and Appendix A.14 are a workaround; the reviewers still
   pushed (`notes:238, 792, 1393`).
2. **No element asks where randomness comes from or where parameters live.** The
   reference's §5.4 "Randomness and reproducibility" (`:920-940`) exists because
   the reviewers forced it (`notes:726, 745, 966`).
3. **Observation asks what is collected, not at what resolution it should be
   collected to serve the purpose** — the question the review forced (`notes:792`).
4. **No element asks which numbers are measurements, which estimates, which
   choices.** The reference invented §5.5 (`:941-951`) and it is the single most
   attacked section in the review (`notes:322, 373, 563`).
5. **The 2010 parameter table has no Provenance column** (sample table is
   Parameter/Meaning/Unit/Value/Source, `odd-2010-template.tex:330`); the reference
   added the fifth column and the controlled vocabulary itself.

The 2020 delta reinforces rather than changes the stance: "Purpose and patterns"
(declare the criteria by which the thing is judged real enough), optional
rationale subsections in every element, mandatory declaration of unused concepts,
and the TRACE supplements (`odd-2020-template.tex:85-122, 191-208`).

## Finding 4 — The stance, stated independently of the element list

For a stage with no entities, no state variables and no time step — `download`:
where the data comes from, in what format, how it is transformed, what it becomes —
the ODD's method reduces to this. It is a **stance**, not a section list: it says
what the writer must have worked out, not in what order.

- **S1. Purpose first, mechanism separate.** What question does this stage exist to
  answer, and what would count as it having answered it? What is explicitly out of
  scope? The purpose is a filter, not a description.
- **S2. Name every magnitude with its identity, units, native resolution and
  target resolution.** Not "the population file" but the file, its key, its native
  resolution, the target resolution, the aggregation rule, and what was lost in the
  aggregation.
- **S3. Distinguish what arrives from outside from what is decided here.** Each
  choice — provider, year, AOI, resampling, floor, no-data rule — must be *named as
  a choice*, so a reader can vary it.
- **S4. Write the order of operations at the granularity where order matters, and
  state the consequences.** Pseudocode plus a table of step / actor / order / mode,
  followed by the consequences of that order.
- **S5. Give every constant a provenance tier and make it checkable.** Measured /
  literature-anchored / engineering prior / model definition / scenario default — and
  a number with no evidence behind it says so on its face.
- **S6. Separate what is state from what is derived from what is a cache.** The
  generalised restart test: if the stage were interrupted and restarted, what would
  have to be on disk to resume identically?
- **S7. Declare what is not done.** Unimplemented paths, absent inputs, dormant
  parameters, states the code never enters.
- **S8. State the outputs and their consumption contract.** What is emitted, at what
  resolution, under what naming and version, and who reads it — including whether
  that resolution is the right one to serve the purpose.
- **S9. Keep an evidence appendix.** Implementation notes (behaviours invisible from
  the description) and provenance/versioning/testing status (what is verified, what
  is not, what the artefact must not be used for).
- **S10. The discipline that makes the above bite:** the document must be checkable
  by someone who does not trust it. Every claim should resolve to a file, a key, a
  line or a number a reviewer can verify, and the standing reviewer question is
  "is this number, this behaviour, this file actually what you say it is?"

S5, S3, S7, S9 and S10 are the ones the reference document added to the ODD, and
they are the ones that survived the review's hardest scrutiny.
