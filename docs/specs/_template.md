# Spec Template

> Canonical template for every spec under `docs/specs/<component>/spec.md`.
> Every spec **must** follow this structure verbatim. The drift-check agent
> validates against this template.

---

```yaml
# Machine-readable affects block — parsed by the drift-check agent.
# Bidirectional: if A affects B, B must declare affected_by A.
# `target` is the folder name under docs/specs/ (stable across KG migrations).
affects:
  - target: <spec-folder>
    direction: upstream | downstream | bidirectional
    reason: <one-line: what API/data shape change triggers this>
    severity: breaking | non-breaking
# Cross-references to the knowledge graph (names only, no UUIDs — survives KG migrations).
kg_refs:
  adrs: [<adr-name>]
  patterns: [<pattern-name>]
  pitfalls: [<pitfall-name>]
  tools: [<tool-name>]
```

## Metadata

| Field | Value |
|---|---|
| Component | `<package path>` |
| Version | `vMAJOR.MINOR.PATCH` |
| Status | `draft` \| `stable` \| `deprecated` |
| Owner | `<who maintains this>` |
| Last drift check | `YYYY-MM-DD` |

## 1. Objective

> **One paragraph**: what this component contributes to the Centinela,
> what the system would lose without it. Frames *why* the spec exists.

## 2. In scope

- Bullet list of responsibilities this spec pins.
- Each bullet is testable (the drift check can verify it).

## 3. Out of scope

- Bullet list of responsibilities that live elsewhere.
- Cross-references to the spec that owns each one.

## 4. Public API

- Function/class signatures exposed.
- Type hints are binding.
- Breaking changes (signature, name, return shape) bump MAJOR.
- Additive changes (new optional param, new function) bump MINOR.

## 5. Invariants

> Things that **must** be true at all times. The drift check runs first
> against invariants; an invariant violation is a P0 bug.

Number each invariant (`INV-1`, `INV-2`, ...). One sentence each.

## 6. Data contracts

- Input shapes, output shapes, on-disk formats.
- Reference `docs/specs/data/spec.md` for the canonical format.

## 7. Migration & deprecation

- How to evolve without breaking callers.
- Deprecation policy (warning period, removal version).

## 8. Drift check

> **Executable** commands an agent runs to verify the spec still holds.
> Each command exits 0 on pass. Group by invariant.

```bash
# Example pattern — adjust to the component
malariasim <command> --dry-run
uv run pytest mal-core/tests/test_<component>.py -v
rg "<forbidden-pattern>" mal-core/src/mal_core/<component>/
```

## 9. Examples

- Minimal working example for each public function.
- Counter-example for each common misuse.

## 10. References

- KG ADR names (not UUIDs).
- KG pattern/pitfall/tool names.
- Other specs (by folder name under `docs/specs/`).
- External docs (papers, datasets).

---

## Writing rules

1. **Spec is the contract. Code is the implementation.** If they disagree,
   the spec wins; the code is the bug.
2. **Bidirectional affects.** If `abm` says `affects: [prediction]`, then
   `prediction/spec.md` must declare `affects: [..., {target: abm, ...}]`.
3. **No UUIDs in cross-refs.** Use human-readable names. If we migrate the
   KG, the specs survive.
4. **Versioning.** Breaking change → bump MAJOR. Additive → MINOR. Doc
   fix → PATCH. The version in the metadata table is binding.
5. **Drift check must be runnable.** If a human has to read the spec to
   decide pass/fail, it's not a drift check — it's a review.
6. **Objective answers "why".** If you can't write one paragraph justifying
   this component's existence, it shouldn't have a spec.