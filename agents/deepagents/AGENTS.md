# MalariaSentinel DeepAgent — Memory File

## Project conventions
- ABM C++ code lives in `mal-core/src/mal_core/abm/` (headers: `params.h`, `wire.hpp`, `engine.hpp`)
- Calibration scorers live in `mal-abm-fast/tests/calibration/scorers/`
- Thresholds are in `mal-abm-fast/tests/calibration/thresholds.yaml`
- Composite scorer is `mal-abm-fast/tests/calibration/scorers/composite.py`
- Tests run with: `cd mal-abm-fast/tests/calibration && uv run pytest -m fast -v`
- Python modules are in `mal-core/src/mal_core/`
- The monorepo uses `uv` for dependency management

## Known pitfalls
- Don't weaken tests or skip scorers to force a pass
- Always compare against the best historical composite score
- Maximum 3 parallel workers at a time
- Workers must run in isolated gitagent worktrees
- Never edit files directly from the orchestrator — always spawn a worker

## Scorer naming convention
Scorers follow the pattern `D<id>_<name>.py` where `<id>` is the next number (D1, D2, ... D10 currently).
Each scorer must be registered in `thresholds.yaml` with `min_score`, `max_delta`, and `hard_floor`.
