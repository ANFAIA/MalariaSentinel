# Pack 12 — Engine simplifications and strictness (remove dead paths)

> Source: ODD 2010 review notes. Status: initial plan — to be detailed later.

## Objective

Remove or strictly gate code paths that are dead, misleading, or
scientifically meaningless: the no-host fallback, empty-population runs,
unused constructors/modes, and the unexplained day limit.

## Notes (verbatim)

- **p.25** (fallback feeding) — "eliminate this option, there must be humans, if no, there is no meaning for the simulation of malaria."
- **p.14** (host landscape) — "Host landscape must be compulsory without host no malaria."
- **p.13** (zero-vector outcome) — "Without population simulation must stop."
- **p.5** (1 to 731 daily steps) — "why limit?"
- **p.13** (host-weighted seeding) — "review the usefulness of this last mode."
- **p.30 A.11** (round-robin constructor) — "Is the movement of mosquito? if so remove and change by new mosquito movement submodel"
- Cross-ref **p.25** (wind) — "this keeps the same" → wind formula kept (pack 03).

## Initial steps

1. Make the host landscape compulsory when transmission is enabled —
   error out if absent (removes the deterministic no-host feeding fallback).
2. Abort with a clear error when the initial population is empty (no
   silent zero-vector runs).
3. Revisit the 731-day cap: remove or justify.
4. Evaluate removing the `host-weighted` seeding mode.
5. Delete the round-robin submodel constructor (replace per the new
   movement submodel from pack 03).

## Dependencies / open points

- Removing the fallback couples to pack 02 (hosts as individuals) and
  pack 03 (movement submodel replacement).
- CLI/UX: decide error messages and exit codes for the new hard failures.
