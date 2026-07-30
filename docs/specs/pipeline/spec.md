# pipeline Spec

> Owns the **orchestration**: the ordered list of stages, the CLI
> dispatch, the resume semantics, and the flag aggregation across
> stages. Sits on top of every other spec; does not own any data
> format itself.

---

```yaml
# Machine-readable affects block — parsed by the drift-check agent.
# Bidirectional: if A affects B, B must declare affected_by A.
# `target` is the folder name under docs/specs/ (stable across KG migrations).
affects:
  - target: download
    direction: bidirectional
    reason: pipeline dispatches Stage.DOWNLOAD → run_download
    severity: breaking
  - target: ingest
    direction: bidirectional
    reason: pipeline dispatches Stage.INGEST/BUILD_HOSTS/BUILD_MOBILITY → ingest builders
    severity: breaking
  - target: abm
    direction: bidirectional
    reason: pipeline dispatches Stage.ABM → run_abm_from_manifest
    severity: breaking
  - target: scoring
    direction: bidirectional
    reason: pipeline dispatches Stage.SCORING → run_calibration
    severity: breaking
  - target: training
    direction: bidirectional
    reason: pipeline dispatches Stage.TRAINING → train_unet
    severity: breaking
  - target: prediction
    direction: bidirectional
    reason: pipeline dispatches Stage.PREDICTION → run_prediction
    severity: breaking
  - target: data
    direction: upstream
    reason: pipeline reads manifest to validate completeness before ABM stage
    severity: non-breaking
  - target: commonlib
    direction: upstream
    reason: pipeline uses Scale from commonlib in PREDICTION dispatch
    severity: non-breaking
# Cross-references to the knowledge graph (names only, no UUIDs — survives KG migrations).
kg_refs:
  adrs: [adr-spec-design-2026-07-30]
  patterns: []
  pitfalls: []
  tools: []
```

## Metadata

| Field | Value |
|---|---|
| Component | `mal-core/src/mal_core/pipeline/` + `mal-core/src/mal_core/cli.py` |
| Version | `v1.0` |
| Status | `stable` |
| Owner | David Flórez-Mazuera |
| Last drift check | `2026-07-30` |

## 1. Objective

The pipeline is the **only sanctioned way to run the system end-to-end**.
It exists to:

1. Order the stages so each consumer sees valid inputs (download → ingest → ingest-hosts → ingest-mobility → ABM → scoring → training → prediction).
2. Provide a single CLI surface (`malariasim run`) with a single set of flags.
3. Aggregate per-stage flag schemas into a unified schema without each stage having to know about the others.
4. Offer idempotent resume (`output_dir/<stage>/` non-empty ⇒ skip).

Without the pipeline, every consumer would reimplement stage
sequencing, resume semantics, and flag forwarding. Bugs would scatter.

## 2. In scope

- `Stage` enum (ordered list of stages).
- `run_pipeline(aoi, year, month, *, seed, days, n_rollouts, stages=None, output_dir, resume=True, stage_flags=None, **kwargs) -> dict`.
- `run_stage(stage, aoi, year, month, output_dir, *, seed, days, n_rollouts, stage_flags=None, **kwargs) -> dict`.
- `aggregate_flags() -> dict[stage_name, flag_schema]` (auto-discovery from `mal_core.<stage>.flags` modules).
- Flag forwarding rules (`_global` keys apply to every stage; per-stage keys override).
- The CLI: `malariasim run --stages <csv> --aoi <slug> --year Y --month M [--seed N] [--days N] [--n-rollouts N] [--no-resume] [--output-dir DIR]`.
- The CLI: `malariasim download --aoi <slug> [--datasets ...] [--outputs ...] [--years ...] [--months ...]`.
- Output directory layout: `output_dir/<stage>/...`.

## 3. Out of scope

- Anything each stage owns → the matching spec (`download`, `ingest`, `abm`, `scoring`, `training`, `prediction`).
- Persisted run manifests (planned, not present) → future spec.
- Remote execution / SLURM dispatch → future spec.

## 4. Public API

| Symbol | Where | Notes |
|---|---|---|
| `Stage` | `mal_core.pipeline.stages` | `str, Enum`. Members in order: `DOWNLOAD, INGEST, BUILD_HOSTS, BUILD_MOBILITY, ABM, SCORING, TRAINING, PREDICTION`. |
| `run_pipeline(...)` | `mal_core.pipeline.runner` | Runs the full (or partial) pipeline. Returns `{"stages_run", "stages_skipped", "artifacts", "errors"}`. |
| `run_stage(...)` | `mal_core.pipeline.runner` | Runs one stage. Returns the stage's dict. |
| `aggregate_flags()` | `mal_core.pipeline.flag_registry` | Returns `dict[stage_name, {flag_name: {type, default, help}}]`. |
| `get_stage_flags(stage_name)` | `mal_core.pipeline.flag_registry` | Returns the flag dict for one stage. |

## 5. Invariants

### §5.1 Stage order

- **INV-1.** The stage order is the order of the `Stage` enum members: `download → ingest → build_hosts → build_mobility → abm → scoring → training → prediction`.
- **INV-2.** `run_pipeline(stages=None)` runs **all** stages in `Stage` order.
- **INV-3.** `run_pipeline(stages=[...])` runs only the listed stages, in the order given. The pipeline **does not** auto-insert dependencies. The caller is responsible for ordering.

### §5.2 Resume

- **INV-4.** If `resume=True` (default) and `output_dir/<stage>/` exists and is non-empty, the stage is skipped and recorded in `stages_skipped`.
- **INV-5.** If `resume=False`, every requested stage runs regardless of existing artefacts. Errors in any stage abort (no swallowing).
- **INV-6.** A stage that errors out under `resume=True` is recorded in `errors[stage]` and the pipeline continues with the next stage (the error is reported at the end).

### §5.3 Flag forwarding

- **INV-7.** `stage_flags={"_global": {...}, "abm": {...}}` merges in this order: kwargs → `_global` → per-stage. **Per-stage wins.**
- **INV-8.** Unknown kwargs to a stage are passed through. The stage decides what to do with them (the ABM wrapper passes them to the C++ binary; ingest builders pass them as keyword arguments).
- **INV-9.** The `DOWNLOAD` stage receives comma-separated `datasets`/`outputs`/`years`/`months` strings parsed into lists before dispatch. Empty strings ⇒ fall back to the pipeline's `year`/`month`.
- **INV-10.** The `PREDICTION` stage always sets `scale=Scale.REGIONAL` (today's pinned default; see §7).

### §5.4 Output layout

- **INV-11.** `output_dir` is created at the top of `run_pipeline`. Each stage creates its own `<output_dir>/<stage>/` subdirectory before writing.
- **INV-12.** The `run_pipeline` result is a JSON-serialisable dict with keys `stages_run: list[str]`, `stages_skipped: list[str]`, `artifacts: dict[str, dict]`, `errors: dict[str, str]`.

### §5.5 Flag schema aggregation

- **INV-13.** `aggregate_flags()` imports `mal_core.<stage>.flags` for each stage and reads the first attribute ending in `_FLAGS_SCHEMA`. If the module or attribute is missing, the stage is omitted from the result (no error).
- **INV-14.** Adding a new stage to the `Stage` enum automatically picks up its flags via §5.5 INV-13, **provided** the stage ships a `mal_core/<stage>/flags.py` module with a `*_FLAGS_SCHEMA` dict.

## 6. Data contracts

- The pipeline does **not** own any data format. All outputs are produced by the underlying stage (see `data/spec.md` §5 for naming + manifest rules, `abm/spec.md` §5 for state/env tensor contracts).
- The CLI surfaces the unified flag schema (auto-aggregated per §5.5).

## 7. Migration & deprecation

- **Adding a stage**: bump MINOR. Add a `Stage` enum member, a `mal_core/<stage>/__init__.py`, and a `mal_core/<stage>/flags.py` with a `*_FLAGS_SCHEMA` dict. Update `run_stage` dispatch.
- **Removing a stage**: bump MAJOR. Document the replacement.
- **Reordering stages**: bump MAJOR. Reordering silently breaks any caller that lists stages by name and assumes the dependency order from §5.1.
- **Default `Scale.REGIONAL` for PREDICTION** (§5.3 INV-10): this is a hardcoded default. Changing it requires both this spec and `prediction/spec.md` to bump MINOR in lockstep.
- Deprecation policy: 1 MINOR spec version carries the warning; removed in the next MAJOR.

## 8. Drift check

```bash
# INV-1: Stage order matches the enum declaration order
uv run python -c "
from mal_core.pipeline.stages import Stage
expected = ['download','ingest','build_hosts','build_mobility','abm','scoring','training','prediction']
assert [s.value for s in Stage] == expected, f'Stage order drift: {[s.value for s in Stage]}'
"

# INV-13/14: every stage has a flags module with _FLAGS_SCHEMA
uv run python -c "
from mal_core.pipeline.flag_registry import aggregate_flags
from mal_core.pipeline.stages import Stage
flags = aggregate_flags()
for s in Stage:
    assert s.value in flags, f'Stage {s.value} has no _FLAGS_SCHEMA'
    assert 'aoi' in flags[s.value], f'Stage {s.value} missing required `aoi` flag'
"

# INV-2/3: run_pipeline honours stages=None and explicit list
uv run python -c "
from mal_core.pipeline.stages import Stage
from mal_core.pipeline.runner import run_pipeline
from pathlib import Path
import tempfile
with tempfile.TemporaryDirectory() as tmp:
    res = run_pipeline('ghana', 2024, 7, stages=[Stage.ABM], output_dir=Path(tmp))
    assert res['stages_run'] == ['abm'], f'unexpected: {res}'
"

# INV-4: resume skips existing outputs
uv run python -c "
from mal_core.pipeline.runner import run_pipeline
from pathlib import Path
import tempfile, os
with tempfile.TemporaryDirectory() as tmp:
    (Path(tmp) / 'abm').mkdir()
    (Path(tmp) / 'abm' / 'marker').touch()
    res = run_pipeline('ghana', 2024, 7, stages=['abm'], output_dir=Path(tmp))
    assert res['stages_skipped'] == ['abm']
"

# INV-12: result shape
uv run python -c "
from mal_core.pipeline.runner import run_pipeline
from mal_core.pipeline.stages import Stage
from pathlib import Path
import tempfile
with tempfile.TemporaryDirectory() as tmp:
    res = run_pipeline('ghana', 2024, 7, stages=[Stage.ABM], output_dir=Path(tmp))
    assert set(res) >= {'stages_run','stages_skipped','artifacts','errors'}
"
```

## 9. Examples

```bash
# Full pipeline
malariasim run --aoi ghana --year 2024 --month 7

# Just ABM + scoring
malariasim run --stages abm,scoring --aoi ghana --year 2024 --month 7

# Force re-run (no resume)
malariasim run --no-resume --aoi ghana --year 2024 --month 7

# Download only
malariasim download --aoi ghana --datasets era5,chirps --years 2024
```

```python
from pathlib import Path
from mal_core.pipeline.runner import run_pipeline
from mal_core.pipeline.stages import Stage

result = run_pipeline(
    "ghana", year=2024, month=7,
    stages=[Stage.INGEST, Stage.BUILD_HOSTS, Stage.BUILD_MOBILITY, Stage.ABM, Stage.SCORING],
    output_dir=Path("runs/exp-2024-07"),
    n_rollouts=10,
    seed=42,
)
print(result["stages_run"], result["errors"])
```

## 10. References

- KG ADR: `adr-spec-design-2026-07-30`.
- Specs (by folder): all other `docs/specs/<component>/spec.md` — pipeline is the conductor.
- External: `typer` (CLI framework, pinned in `mal-core/pyproject.toml`).