# scoring Spec

> Owns the **post-run scoring pipeline**: running biological/dynamical
> scorers against a finished ABM output directory, computing the
> composite score plus binary gates, an optional LLM qualitative
> judge, and emitting feedback for the next iteration.

---

```yaml
# Machine-readable affects block — parsed by the drift-check agent.
# Bidirectional: if A affects B, B must declare affected_by A.
# `target` is the folder name under docs/specs/ (stable across KG migrations).
affects:
  - target: abm
    direction: upstream
    reason: scoring consumes ABM output artifacts (state COGs, cohort log, aquatic JSONs) after a run
    severity: breaking
  - target: data
    direction: upstream
    reason: scoring resolves per-AOI datasets (occurrence spots, urban class raster) via the data spec naming + catalog
    severity: non-breaking
  - target: commonlib
    direction: upstream
    reason: scoring reads workspace-level helpers (AOI scale, dataset catalog)
    severity: non-breaking
```

## Metadata

| Field | Value |
|---|---|
| Component | `mal-core/src/mal_core/scoring/` |
| Version | `v2.0` (canon runner); composite v2.0 (13 dims weighted geometric mean + 6 gates) |
| Status | `stable` (runner); `stable` (D1-D5, D8, D11, D15, D16, D19, D20, D21); `stable` (D25, manual); `stable` (gates); `draft` (LLM judge) |
| Owner | David Flórez-Mazuera |
| Last drift check | `2026-10-12` |

## 1. Objective

Scoring is the **truth-test** for the ABM. It runs a battery of
biological/dynamical scorers against an ABM output directory to
produce a single composite number that tells the team whether the
simulation is realistic. Without scoring the system would have no
objective way to say "the ABM matches the real world" or "this
parameter change made things worse".

The composite is what gates parameter changes: every ABM change must
beat the previous best composite on the same benchmark before
promoting.

## 2. History

- **v1.x (until 2026-08)**: the pytest calibration harness lived in
  `mal-core/src/mal_core/abm/tests/calibration/` (scores via
  `uv run pytest -m <tier>`, thresholds.yaml, diff/best trackers).
- **2026-08-30 (a0d0d61)**: canonical post-run scoring promoted into
  `mal_core/scoring/` — registry + config + runner architecture;
  engineering invariants split off as **gates** (binary, reported
  apart, never in the composite).
- **2026-10: the old harness was DELETED.** Its unit tests were
  ported to `mal-core/tests/test_scoring_*.py` (against the canon
  scorers). This package is the single scoring system.

## 3. Scope

### In scope

- `run_scoring(run_dir, ...)` + `format_summary(scorecard) -> str`.
- The scorer suite at `mal-core/src/mal_core/scoring/scorers/`
  (`d<id>_<name>.py`, D1-D25) and the gates (`gates.py`, G6-G24).
- The scorer registry: `build_registry()` + `list_scorers()` +
  `COMPOSITE_WEIGHTS` (`registry.py`).
- Scoring config: `ScoringConfig`, `load_config` (only/skip/enable
  filters via CLI flags or YAML).
- The LLM qualitative judge: `llm_scorer.py` + `prompts/llm_verdict.md`
  (attaches `verdict_llm` to the scorecard when OPENROUTER_KEY is
  present and the call succeeds).
- The feedback report (`get_feedback(scorecard, baseline=None) -> str`).

### Out of scope

- ABM output contract → `docs/specs/abm/spec.md`.
- Scorer unit tests → `mal-core/tests/test_scoring_*.py` (they test
  the canon scorers, not this spec's runner).
- The deleted pytest harness (`tests/calibration/`): do not reintroduce;
  unit-test style lives in `mal-core/tests`, run-time scoring is
  `malariasim score`.
- Production tuning of the LLM judge prompt → `llm_scorer.py`
  docstring + `prompts/llm_verdict.md`.

## 4. Public API

| Symbol | Where | Notes |
|---|---|---|
| `run_scoring(run_dir, aoi=None, config_path=None, only=None, skip=None, enable=None, ctx_extras=None) -> dict` | `mal_core.scoring.runner` | Runs every enabled scorer against the run dir; writes `scorecard.json` inside it; attaches `verdict_llm` when the LLM judge succeeds. |
| `format_summary(scorecard: dict) -> str` | `mal_core.scoring.runner` | Compact human-readable summary for the CLI. |
| `build_registry() -> dict[str, ScorerSpec]` | `mal_core.scoring.registry` | Instances of every scorer/gate registered: D1-D25 + G6/G7/G10/G12/G14/G24. |
| `list_scorers() -> list[dict]` | `mal_core.scoring.registry` | Rows for `malariasim score --list` (name, kind, weight, description, manual). |
| `COMPOSITE_WEIGHTS` | `mal_core.scoring.registry` | Per-dimension weights (single source of truth). See §5.3. |
| `GATES` | `mal_core.scoring.registry` | Gate name tuple (never in the composite). |
| `ScoringConfig`, `load_config(...)` | `mal_core.scoring.config` | only/skip/enable resolution + `weight_of(name)`. |
| `get_feedback(scorecard, baseline=None) -> str` | `mal_core.scoring.feedback` | Markdown feedback: weakest dims, failed gates, delta vs baseline. |
| `score_with_llm(report, *, model=..., cache_dir=None, timeout_s=...) -> dict` | `mal_core.scoring.llm_scorer` | LLM-as-judge. `Verdict` pydantic schema (viable/borderline/regressed/collapsed). Content-hash cached under `.cache/llm_verdicts/`. Falls back to `verdict="unknown"` + `fallback` reason on any failure. |
| `Scorer` (ABC), `ScorerResult` | `mal_core.scoring.scorers.base` | `score(run_dir, ctx) -> ScorerResult`; `kind` "composite" \| "gate"; `manual` flag (AOI-dependent, never runs by default). |

## 5. Invariants

### §5.1 Runner

- **INV-1.** `run_scoring` writes `scorecard.json` INSIDE the run dir
  and returns the same dict. It never raises on a single broken scorer:
  a scorer raising an exception becomes a *skipped* entry, not a crash.
- **INV-2.** Skipped scorers (missing artifacts, disabled by config,
  manual) do NOT count in the composite — skipped dimensions are
  excluded from both the score and the weight sum.

### §5.2 Scorer suite (D1..D25 + gates)

- **INV-5.** Composite scorers live at `mal_core/scoring/scorers/d<id>_<name>.py`
  (lowercase module, `Scorer` ABC with `kind="composite"`); gates live
  in `scorers/gates.py` (`G<id>_<name>`, `kind="gate"`).
- **INV-6.** Scorer IDs are stable claims on validation dimensions:
  `D1` habitat occupancy, `D2` survival, `D3` EIP, `D4` stability,
  `D5` Moran's I, `D8` coupling, `D11` aquatic structure,
  `D15` long-horizon persistence, `D16` detection coverage,
  `D19` pool persistence, `D20` washout response, `D21` dispersal
  kernel, `D25` reported cases (Ghana). Gates: `G6` data valid,
  `G7` determinism, `G10` perf, `G12` host input, `G14` mobility,
  `G24` urban ratio. Historical note: old harness D6/D7/D9/D10/D12-D14
  enjoyed different semantics (mass/determinism/activation/perf/
  host-density/mobility) and were consciously NOT promoted — mass,
  determinism, perf, host-input and mobility became gates; the rest
  were culled.
- **INV-6b.** Missing required data ⇒ the scorer returns
  `status="skipped"` (never score 0 for missing data):
  | Scorer | Required data | Source |
  |---|---|---|
  | D16 detection coverage | `--occurrence` TSV or `data/<aoi>/…_occurrence.txt` | `validate-detections` |
  | D25 cases ghana | `data/<aoi>_idit/` case series | `validate-cases` |
  | G12 host input | `host_static.nc` + census totals | `ingest --what hosts` |
  | G14 mobility | `*.csr` OD matrices | `ingest --what mobility` |
- **INV-7.** Adding a scorer = new file in `scorers/` + entry in
  `build_registry()` + weight in `COMPOSITE_WEIGHTS`. Non-breaking (MINOR).
- **INV-8.** Removing a scorer = MAJOR (historical scorecards become
  non-comparable).

### §5.3 Composite

- **INV-9.** Composite = weighted geometric mean over "ok" composite
  dimensions: `exp(Σ wi · log(si) / Σ wi)`; returns 0.0 if any
  `si <= 0.0` (geometric-mean semantics: one collapsed dimension
  collapses the composite).
- **INV-10.** `COMPOSITE_WEIGHTS` is the single source of truth for
  weights: `D16=4.0, D2=4.0, D15=3.0, D3=3.0, D8=2.0, D4=2.0,
  D25=2.0, D19=1.0, D20=1.0, D1=1.0, D5=1.0, D11=1.0, D21=1.0`.
- **INV-11.** Composite handles variable dimension counts via the
  geometric mean (missing/ skipped ⇒ absent from numerator and
  denominator). Adding a scorer does not break historical composites
  — it just narrows what they cover.

### §5.4 LLM judge

- **INV-12.** `scorers/../llm_scorer.py` (`mal_core.scoring.llm_scorer`)
  is the LLM-as-judge component. Status: `draft`. It must not gate
  stable runs: when the key is absent or the call fails, the module
  returns a `fallback` dict and the runner simply omits
  `verdict_llm` from the scorecard.
- **INV-13.** Prompts live at `mal_core/scoring/prompts/`. Prompts are
  versioned alongside the module and must not change without bumping
  the effective spec version (see §7).
- **INV-17.** The judge uses OpenRouter (`https://openrouter.ai/api/v1`)
  via `requests`, not langchain_openai. API key is resolved from the
  `OPENROUTER_KEY` env var or a `.env` file walked up from this
  package. Default model: `minimax/minimax-m3`. Verdicts are
  content-hash cached under `.cache/llm_verdicts/`.

### §5.5 Feedback

- **INV-14.** `get_feedback` takes the canon scorecard shape
  (`composite` / `verdict` / `gates` / `composite_dimensions` /
  `scores` / `skipped`) and returns a markdown string: composite +
  verdict, failed gates, skipped scorers, weakest dimensions, and
  (with baseline) the delta + regressed dimensions list.

### §5.6 Pipeline integration

- **INV-16.** CLI dispatch: `malariasim score --run-dir <dir>` →
  `run_scoring`; `malariasim feedback --run-dir <dir>` →
  `run_scoring + get_feedback`; `malariasim validate-detections`
  and `malariasim validate-cases` are launch-and-measure wrappers
  that run the ABM then `run_scoring` with a specific manual scorer
  enabled (D16 / D25).

## 6. Data contracts

- **Inputs** (per `abm/spec.md` §5): `state*.tif` state COGs (2 bands:
  density + suitability), `*_cohort.json` cohort log,
  `*_day*_aquatic.json` daily aquatic stats, `run_metadata.json`
  (optional: wall time for G10). Discovery helpers live in
  `scorers/base.py` (`find_state_files`, `find_final_state`,
  `find_cohort_file`, `find_aquatic_day_files`, `load_run_metadata`).
- **Optional inputs** (see INV-6b table).
- **Output:** `scorecard.json` inside the run dir:
  `{run_dir, aoi, composite, verdict, scores{name→score/value/target/
  diagnostics/passed/status}, composite_dimensions{name→score,weight},
  gates{name→score,passed}, skipped{name→reason}, timestamp,
  verdict_llm?}`.

## 7. Migration & deprecation

- **Adding a scorer (D<n+1> or G<n+1>)**: bump MINOR. Add the file,
  register it in `build_registry()`, set the weight in
  `COMPOSITE_WEIGHTS`, document the new ID in §5.2 INV-6, add unit
  tests in `mal-core/tests/test_scoring_*.py`.
- **Removing a scorer**: bump MAJOR. The composite changes shape; all
  historical scorecards become non-comparable.
- **Promoting the LLM judge from `draft` to `stable`**: bump MINOR.
- Deprecation policy: 1 MINOR spec version carries the warning;
  removed in the next MAJOR.

## 8. Drift check

```bash
# INV-5/6: registry matches the file set + weights table
uv run python -c "
from mal_core.scoring.registry import build_registry, COMPOSITE_WEIGHTS
r = build_registry()
comps = {n for n, s in r.items() if s.kind == 'composite'}
assert comps == set(COMPOSITE_WEIGHTS), (comps - set(COMPOSITE_WEIGHTS), set(COMPOSITE_WEIGHTS) - comps)
"

# INV-9: composite is weighted geometric mean over ok dims only
uv run python -c "
import math
from mal_core.scoring.registry import COMPOSITE_WEIGHTS
scores = {k: 0.8 for k in COMPOSITE_WEIGHTS}
got = math.exp(sum(w * math.log(scores[k]) for k, w in COMPOSITE_WEIGHTS.items()) / sum(COMPOSITE_WEIGHTS.values()))
assert abs(got - 0.8) < 1e-9, got
"

# INV-12/17: LLM judge uses OpenRouter + key env var
grep -q "run_scoring" mal-core/src/mal_core/scoring/runner.py
grep -q "openrouter.ai" mal-core/src/mal_core/scoring/llm_scorer.py
grep -q "OPENROUTER_KEY" mal-core/src/mal_core/scoring/llm_scorer.py
```

## 9. Examples

```python
from mal_core.scoring import run_scoring, format_summary, get_feedback

# Score a run (13 dims; skipped/gates reported apart; LLM judge auto)
scorecard = run_scoring("runs/abm/ghana-2024-seed0001")
print(format_summary(scorecard))

# Manual scorers (AOI-dependent) must be explicitly enabled
scorecard = run_scoring(
    "runs/abm/ghana-2024-seed0001",
    aoi="ghana",
    enable=["D16_detection_coverage"],
)

# Markdown feedback vs a baseline run
base = run_scoring("runs/abm/ghana-2023-seed0001")
print(get_feedback(scorecard, baseline=base))
```

## 10. References

- KG ADR: `adr-spec-design-2026-07-30`.
- Specs (by folder): `abm`, `data`, `commonlib`.
- Plans: `calibration-test-framework.md` (historical, harness era.
  The harness itself was deleted 2026-10).
