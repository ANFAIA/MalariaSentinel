# tools/ — Dev Helpers

Standalone developer scripts. Not part of the runtime pipeline.

| Script | Purpose |
|---|---|
| `verify.sh` | Sync the workspace (`uv sync --all-packages`) and import-check every package |
| `format.sh` | `ruff format` + `ruff check --fix` over `mal-commonlib/`, `mal-core/`, `mal-execution/`, `mal-data-explorer/` |
| `run_all_tests.sh` | Run pytest per package, best-effort |
| `extract_papers.py` | Extract text from every PDF in `papers/` into `.md` equivalents (pdfplumber) |
| `check_no_constants.sh` | Guard: no model-constant literals in migrated code |
| `audit_comment_constants.py` | Audit: model-constant values echoed inside comments/docstrings, plus `name = value` assignments (task-04). Scans the whole repo by default (artifacts excluded by root path, so `mal_commonlib/data/loaders` IS scanned); allowlist in `comment_audit_allowlist.txt` |

## Usage

```bash
bash tools/verify.sh          # after cloning or changing deps
bash tools/format.sh          # before committing
bash tools/run_all_tests.sh   # quick smoke across packages
uv run python tools/extract_papers.py
uv run python tools/audit_comment_constants.py   # exit 1 on residual leaks
```
