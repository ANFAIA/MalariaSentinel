# mal-abm-fast / tests / calibration

Calibration test framework for the **mal-abm-fast** C++ ABM engine. This
package scores ABM rollouts against a 10-dimension scorecard (D1..D10)
plus an LLM judge verdict (see `scorers/llm_scorer.py`).

## Layout

| Path | Purpose |
|---|---|
| `conftest.py` | Pytest fixtures (cpp_binary, ghana_env_path, ghana_habitat_path, tmp_calibration_dir) and marker logic |
| `scorers/__init__.py` | Scorers package init |
| `scorers/llm_scorer.py` | LLM judge (LangChain → OpenCode Zen chat/completions, structured `Verdict` via Pydantic) |
| `scorers/prompts/llm_verdict.md` | System prompt for the LLM judge (reference ranges, verdict scale, output rules) |

## Run

```bash
# From the calibration dir
uv run pytest                # default tier = fast; skips full-marked and llm-marked if no key
CALIBRATION_TIER=full uv run pytest
OPENCODE_API_KEY=sk-... uv run pytest    # enables llm-marked tests
```
