"""Checks migrated from the retired abm specification.

The spec is gone; the facts live in the code, in the C++ tests and in
this file. See docs/plans/in-process/spec-retirement-ledger.md for the
row that maps each assertion to this test.
"""
from __future__ import annotations

import re
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
ABM_SRC = REPO / "mal-core" / "src" / "mal_core" / "abm"
CPP_SRC = ABM_SRC / "src"
CPP_INCLUDE = ABM_SRC / "include" / "mal_abm_fast"
CPP_TESTS = ABM_SRC / "tests"

# The sidecar keys the C++ writer emits (the retired spec's INV-8/INV-9).
REQUIRED_SIDECAR_KEYS = (
    "crs", "transform", "aoi_slug", "scale", "year", "month", "seed",
    "generator_version", "abm_params_hash", "contract_version",
)

# The exact key order the writer emits (the order is part of the contract).
FROZEN_SIDECAR_KEY_ORDER = (
    "crs", "transform", "aoi_slug", "scale", "year", "month", "seed",
    "n_rollouts", "rollout_index", "generator_version", "abm_params_hash",
    "contract_version", "band_names", "nodata", "shape",
)


def _cpp_sidecar_keys() -> list[str]:
    text = (CPP_SRC / "output_contract.cpp").read_text(encoding="utf-8")
    return re.findall(r'j\["([^"]+)"\]\s*=', text)


def test_the_sidecar_carries_every_required_key():
    keys = set(_cpp_sidecar_keys())
    missing = [k for k in REQUIRED_SIDECAR_KEYS if k not in keys]
    assert not missing, f"the state sidecar is missing the keys {missing}"


def test_the_retired_k_max_key_is_gone_from_the_sidecar():
    assert "k_max" not in set(_cpp_sidecar_keys())


def test_the_sidecar_key_order_is_frozen():
    """The key order is part of the contract (two engines, byte-equal files)."""
    keys = _cpp_sidecar_keys()
    assert keys == list(FROZEN_SIDECAR_KEY_ORDER)


def test_the_state_cog_has_exactly_two_bands_and_the_pinned_names():
    header = (CPP_INCLUDE / "wire.hpp").read_text(encoding="utf-8")
    match = re.search(r"STATE_BAND_NAMES\[2\]\s*=\s*\{([^}]*)\}", header)
    assert match, "STATE_BAND_NAMES not found in wire.hpp"
    names = re.findall(r'"([^"]+)"', match.group(1))
    assert names == ["adult_patch_count", "adult_cell_count"]


def test_the_contract_version_is_4_0():
    from mal_core.habitat.config import CONFIG

    assert CONFIG["contracts"]["cogs_state"] == "4.0"
    assert CONFIG["contracts"]["env_nc"] == "3.0"


def test_the_state_file_naming_follows_the_engine_convention():
    """The final state file and the per-day snapshots."""
    wrapper = (ABM_SRC / "wrapper.py").read_text(encoding="utf-8")
    assert 'f"{aoi}_abm_seed{seed:04d}.tif"' in wrapper
    main = (CPP_SRC / "main.cpp").read_text(encoding="utf-8")
    assert '"_day"' in main and "std::setw(3)" in main
    # The retired spec's name ({aoi}_{scale}_{year}_{month}_seedNNNN.tif) is
    # not the one the engine writes.
    assert "_abm_seed" in wrapper


def test_the_state_nodata_sentinel_is_minus_9999():
    from mal_core.habitat.config import CONFIG

    assert float(CONFIG["ingest"]["nodata_sentinel"]) == -9999.0


def test_no_code_outside_commonlib_hardcodes_a_128_grid():
    """AOI.cells_per_side() is the only source of (H, W)."""
    pattern = re.compile(r"H\s*=\s*W\s*=\s*128|H\s*=\s*128\b|W\s*=\s*128\b")
    roots = [
        REPO / "mal-core" / "src" / "mal_core" / "abm",
        REPO / "mal-core" / "src" / "mal_core" / "training",
        REPO / "mal-core" / "src" / "mal_core" / "prediction",
        REPO / "mal-execution" / "src",
    ]
    offenders = []
    for root in roots:
        if not root.exists():
            continue
        for path in root.rglob("*"):
            if path.suffix not in (".py", ".cpp", ".hpp"):
                continue
            if "__pycache__" in path.parts:
                continue
            if pattern.search(path.read_text(encoding="utf-8", errors="ignore")):
                offenders.append(str(path.relative_to(REPO)))
    assert not offenders, f"a hardcoded 128 grid found in {offenders}"


def test_the_cpp_state_cog_test_pins_the_band_descriptions_and_the_transform():
    """The C++ test already pins what the retired spec claimed."""
    text = (CPP_TESTS / "test_state_cog.cpp").read_text(encoding="utf-8")
    assert "STATE_BAND_NAMES[0]" in text
    assert "STATE_BAND_NAMES[1]" in text
    assert "j[\"transform\"].size(), 6u" in text
    assert "k_max" in text  # the removal of k_max is asserted there


def test_the_env_nc_is_the_only_accepted_env_format():
    """A non-.nc env path is refused by the engine."""
    main = (CPP_SRC / "main.cpp").read_text(encoding="utf-8")
    assert "read_env_nc" in main or "read_env_nc" in \
        (CPP_SRC / "env_reader.cpp").read_text(encoding="utf-8")
    assert "read_env_tif" not in main
    assert "load_from_env_tif" not in main
