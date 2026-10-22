"""Guard-script regression tests (task-01, closing task-02 review P2 gaps).

``tools/check_no_constants.sh`` is the mechanical protection of R1 (single
source of model values). These tests run the REAL script against a
synthetic tree, so a future pattern removal cannot pass silently.

Gaps covered (task-02 review §R2.6 items 1 and the ``np.full`` miss):
  * ``np.full((...), -9999.0)`` in the low-level loaders;
  * ``add_option(`` with the option name on the following line.
"""
from __future__ import annotations

import subprocess
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
GUARD = REPO / "tools" / "check_no_constants.sh"


def _run_guard(root: Path) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["sh", str(GUARD), str(root)],
        capture_output=True, text=True, check=False)


def _fake_root(tmp_path: Path) -> Path:
    for sub in (
        "mal-commonlib/src/mal_commonlib/data/loaders",
        "mal-core/src/mal_core/abm/src",
        "mal-core/src/mal_core/abm/include/mal_abm_fast",
        "mal-core/src/mal_core/scoring",
        "mal-core/src/mal_core/ingest",
        "mal-core/src/mal_core/habitat",
        "mal-core/src/mal_core/prediction",
    ):
        (tmp_path / sub).mkdir(parents=True, exist_ok=True)
    return tmp_path


def test_clean_synthetic_tree_passes(tmp_path):
    res = _run_guard(_fake_root(tmp_path))
    assert res.returncode == 0, res.stdout + res.stderr
    assert "check_no_constants: OK" in res.stdout


def test_np_full_nodata_literal_is_caught(tmp_path):
    root = _fake_root(tmp_path)
    loader = (root / "mal-commonlib/src/mal_commonlib/data/loaders"
              / "worldpop.py")
    loader.write_text(
        "def raster_nodata(shape):\n"
        "    return np.full(shape, -9999.0)\n",
        encoding="utf-8")
    res = _run_guard(root)
    assert res.returncode == 1
    assert "worldpop.py" in res.stdout


def test_add_option_name_next_line_is_caught(tmp_path):
    root = _fake_root(tmp_path)
    main = root / "mal-core/src/mal_core/abm/src/main.cpp"
    main.write_text(
        "run->add_option(\n"
        '    "--beta-hv", beta_hv,\n'
        '    "help")\n'
        "    ->default_val(0.40);\n",
        encoding="utf-8")
    res = _run_guard(root)
    assert res.returncode == 1
    assert "default_val" in res.stdout


def test_same_line_resolution_literal_is_caught(tmp_path):
    root = _fake_root(tmp_path)
    main = root / "mal-core/src/mal_core/abm/src/main.cpp"
    main.write_text("double resolution_m = 1000;\n", encoding="utf-8")
    res = _run_guard(root)
    assert res.returncode == 1
    assert "resolution" in res.stdout
