"""Pytest configuration and shared fixtures for the calibration tests.

The calibration test framework exercises the mal-abm-fast C++ ABM engine
against a 10-dimension scorecard (D1..D10) plus an LLM judge verdict
(see ``scorers/llm_scorer.py``). This file provides the shared fixtures
that every test in the suite needs:

- ``tmp_calibration_dir`` — a session-scoped temporary directory for
  the entire test run. Holds the run root (with subdirs ``rollouts/``,
  ``reports/``, ``.cache/``).
- ``cpp_binary`` — the path to the compiled mal-abm-fast CLI. Built
  once at session start; tests skip if the binary is missing.
- ``ghana_env_path`` / ``ghana_habitat_path`` — the Ghana 2024-06
  fixtures (env GeoTIFF and habitat GeoPackage). These live in
  ``data/runs/ghana/`` and are reused across all tests.
- ``markers`` — auto-applied based on the ``CALIBRATION_TIER`` env
  var (``fast`` or ``full``) and the presence of ``OPENCODE_API_KEY``
  (``llm``).
"""

from __future__ import annotations

import os
import shutil
import tempfile
from pathlib import Path

import pytest

# ---------------------------------------------------------------------------
# Constants — paths into the project tree
# ---------------------------------------------------------------------------

_REPO_ROOT = Path(__file__).resolve().parents[6]
"""Repo root. The calibration package sits at
``<repo>/mal-core/src/mal_core/abm/tests/calibration/``; six ``..`` from this file
takes us back to the repo root."""

MAL_ABM_FAST_DIR = _REPO_ROOT / "mal-core" / "src" / "mal_core" / "abm"
CPP_BINARY_DEFAULT = MAL_ABM_FAST_DIR / "build" / "src" / "mal_abm_fast"
GHANA_ENV_PATH = _REPO_ROOT / "data" / "runs" / "ghana" / "ghana_regional_2024_06_env.tif"
GHANA_HABITAT_PATH = _REPO_ROOT / "data" / "runs" / "ghana" / "ghana_regional_2024_06_habitat_patches.gpkg"

CALIBRATION_TIER_ENV = "CALIBRATION_TIER"
"""Env var selecting the test tier: ``fast`` (default) or ``full``."""

OPENCODE_API_KEY_ENV = "OPENCODE_API_KEY"
"""Env var holding the OpenCode Zen API key. Required for ``llm``-marked
tests; they are skipped if unset."""


# ---------------------------------------------------------------------------
# Session-scoped fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(scope="session")
def tmp_calibration_dir() -> Path:
    """A temporary directory for the entire test run.

    Yields a :class:`pathlib.Path` to a per-session tempdir with the
    subdirs the scorers expect (``rollouts/``, ``reports/``,
    ``.cache/llm_verdicts/``). Cleaned up at session teardown.
    """
    root = Path(tempfile.mkdtemp(prefix="mal_calibration_"))
    (root / "rollouts").mkdir()
    (root / "reports").mkdir()
    (root / ".cache" / "llm_verdicts").mkdir(parents=True)
    try:
        yield root
    finally:
        shutil.rmtree(root, ignore_errors=True)


@pytest.fixture(scope="session")
def cpp_binary() -> Path:
    """Path to the compiled mal-abm-fast CLI.

    If the binary is missing, the test is skipped with a clear message
    pointing at the build instructions in ``mal-abm-fast/README.md``.
    """
    if not CPP_BINARY_DEFAULT.is_file():
        pytest.skip(
            f"mal-abm-fast binary not built at {CPP_BINARY_DEFAULT}. "
            "Build it with: cmake -S mal-abm-fast -B mal-abm-fast/build -G Ninja "
            "-DCMAKE_BUILD_TYPE=Release && cmake --build mal-abm-fast/build -j"
        )
    return CPP_BINARY_DEFAULT


@pytest.fixture(scope="session")
def ghana_env_path() -> Path:
    """Path to the Ghana 2024-06 4-band env GeoTIFF (or skip if missing)."""
    if not GHANA_ENV_PATH.is_file():
        pytest.skip(f"Ghana env fixture not found at {GHANA_ENV_PATH}")
    return GHANA_ENV_PATH


@pytest.fixture(scope="session")
def ghana_habitat_path() -> Path:
    """Path to the Ghana 2024-06 habitat patches GeoPackage (or skip)."""
    if not GHANA_HABITAT_PATH.is_file():
        pytest.skip(f"Ghana habitat fixture not found at {GHANA_HABITAT_PATH}")
    return GHANA_HABITAT_PATH


@pytest.fixture(scope="session")
def cohort_log_path(tmp_calibration_dir: Path) -> Path:
    """Path for the cohort log JSON (populated by --emit-cohort-log)."""
    return tmp_calibration_dir / "cohort.json"


# ---------------------------------------------------------------------------
# Markers
# ---------------------------------------------------------------------------


def pytest_collection_modifyitems(config: pytest.Config, items: list[pytest.Item]) -> None:
    """Apply the ``fast`` / ``full`` / ``llm`` markers based on env.

    - ``CALIBRATION_TIER=fast`` (default): every test that is not
      explicitly marked ``full`` is selected; ``full``-marked tests are
      deselected unless ``CALIBRATION_TIER=full``.
    - ``CALIBRATION_TIER=full``: every test is selected.
    - Tests marked ``llm`` are deselected if ``OPENCODE_API_KEY`` is
      unset.
    """
    tier = os.environ.get(CALIBRATION_TIER_ENV, "fast").lower()
    api_key_present = bool(os.environ.get(OPENCODE_API_KEY_ENV))

    for item in items:
        markers = {m.name for m in item.iter_markers()}

        if "llm" in markers and not api_key_present:
            item.add_marker(pytest.mark.skip(reason=f"{OPENCODE_API_KEY_ENV} not set"))

        if tier == "fast" and "full" in markers:
            item.add_marker(pytest.mark.skip(reason=f"{CALIBRATION_TIER_ENV}!=full"))
