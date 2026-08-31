# tools/ — Dev Helpers

Standalone developer scripts. Not part of the runtime pipeline.

| Script | Purpose |
|---|---|
| `verify.sh` | Sync the workspace (`uv sync --all-packages`) and import-check every package |
| `format.sh` | `ruff format` + `ruff check --fix` over `mal-commonlib/`, `mal-core/`, `mal-execution/`, `mal-data-explorer/` |
| `run_all_tests.sh` | Run pytest per package, best-effort |
| `extract_papers.py` | Extract text from every PDF in `papers/` into `.md` equivalents (pdfplumber) |

## Usage

```bash
bash tools/verify.sh          # after cloning or changing deps
bash tools/format.sh          # before committing
bash tools/run_all_tests.sh   # quick smoke across packages
uv run python tools/extract_papers.py
```
