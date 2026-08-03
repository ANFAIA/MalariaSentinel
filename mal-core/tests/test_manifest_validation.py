"""Tests for M13 Phase 3: manifest period coverage validation."""
import json
from pathlib import Path

import pytest


@pytest.fixture
def aoi_dir(tmp_path, monkeypatch):
    """Create a minimal AOI data directory and monkeypatch DATA_ROOT."""
    import mal_core.download.manifest as manifest_mod
    data_root = tmp_path / "data"
    monkeypatch.setattr(manifest_mod, "DATA_ROOT", data_root)
    return data_root / "ghana"


class TestValidateCompleteness:
    """Test suite for validate_completeness with period coverage."""

    def test_validate_completeness_file_missing(self, aoi_dir, monkeypatch):
        """Basic file-missing detection (existing behavior)."""
        import mal_core.download.manifest as manifest_mod
        # Write a minimal manifest with one expected file
        manifest = {
            "aoi": "ghana",
            "datasets": {},
            "expected_files": ["ghana_rainfall_2024.tif"],
        }
        aoi_dir.mkdir(parents=True, exist_ok=True)
        (aoi_dir / "manifest.json").write_text(json.dumps(manifest))

        missing = manifest_mod.validate_completeness("ghana")
        assert missing == ["ghana_rainfall_2024.tif"]

    def test_validate_completeness_period_covers_range(self, aoi_dir, monkeypatch):
        """Period covers requested years → no period error."""
        import mal_core.download.manifest as manifest_mod
        # Write manifest with a dataset that covers 2024-2025
        manifest = {
            "aoi": "ghana",
            "datasets": {
                "chirps_rainfall_daily": {
                    "type": "time-series",
                    "format": "tif",
                    "files": {"chirps_rainfall_daily": "ghana_rainfall_daily_2024_2025_env.nc"},
                    "period": {"start": "2024-01-01", "end": "2025-12-31"},
                }
            },
            "expected_files": ["ghana_rainfall_daily_2024_2025_env.nc"],
        }
        aoi_dir.mkdir(parents=True, exist_ok=True)
        (aoi_dir / "manifest.json").write_text(json.dumps(manifest))
        # Create the file so it exists
        (aoi_dir / "ghana_rainfall_daily_2024_2025_env.nc").touch()

        missing = manifest_mod.validate_completeness("ghana", years=[2024, 2025])
        assert missing == []

    def test_validate_completeness_period_does_not_cover(self, aoi_dir, monkeypatch):
        """Period doesn't cover requested years → period error in missing list."""
        import mal_core.download.manifest as manifest_mod
        # Period covers only 2023-2024, but we request 2024-2025
        manifest = {
            "aoi": "ghana",
            "datasets": {
                "chirps_rainfall_daily": {
                    "type": "time-series",
                    "format": "tif",
                    "files": {"chirps_rainfall_daily": "ghana_rainfall_daily_2023_2024_env.nc"},
                    "period": {"start": "2023-01-01", "end": "2024-12-31"},
                }
            },
            "expected_files": ["ghana_rainfall_daily_2023_2024_env.nc"],
        }
        aoi_dir.mkdir(parents=True, exist_ok=True)
        (aoi_dir / "manifest.json").write_text(json.dumps(manifest))
        (aoi_dir / "ghana_rainfall_daily_2023_2024_env.nc").touch()

        missing = manifest_mod.validate_completeness("ghana", years=[2024, 2025])
        assert len(missing) == 1
        assert missing[0].startswith("period_coverage:chirps_rainfall_daily")
        assert "does not cover 2024-2025" in missing[0]

    def test_validate_completeness_period_not_checked_without_years(self, aoi_dir, monkeypatch):
        """When years=None, period mismatches are ignored."""
        import mal_core.download.manifest as manifest_mod
        # Period covers only 2023-2024, but we don't request any years
        manifest = {
            "aoi": "ghana",
            "datasets": {
                "chirps_rainfall_daily": {
                    "type": "time-series",
                    "format": "tif",
                    "files": {"chirps_rainfall_daily": "ghana_rainfall_daily_2023_2024_env.nc"},
                    "period": {"start": "2023-01-01", "end": "2024-12-31"},
                }
            },
            "expected_files": ["ghana_rainfall_daily_2023_2024_env.nc"],
        }
        aoi_dir.mkdir(parents=True, exist_ok=True)
        (aoi_dir / "manifest.json").write_text(json.dumps(manifest))
        (aoi_dir / "ghana_rainfall_daily_2023_2024_env.nc").touch()

        # years=None (default) should skip period checks
        missing = manifest_mod.validate_completeness("ghana")
        assert missing == []

    def test_validate_completeness_period_partial_coverage(self, aoi_dir, monkeypatch):
        """Period covers some but not all requested years."""
        import mal_core.download.manifest as manifest_mod
        # Period covers 2024 only, but we request 2024-2025
        manifest = {
            "aoi": "ghana",
            "datasets": {
                "chirps_rainfall_daily": {
                    "type": "time-series",
                    "format": "tif",
                    "files": {"chirps_rainfall_daily": "ghana_rainfall_daily_2024_env.nc"},
                    "period": {"start": "2024-01-01", "end": "2024-12-31"},
                }
            },
            "expected_files": ["ghana_rainfall_daily_2024_env.nc"],
        }
        aoi_dir.mkdir(parents=True, exist_ok=True)
        (aoi_dir / "manifest.json").write_text(json.dumps(manifest))
        (aoi_dir / "ghana_rainfall_daily_2024_env.nc").touch()

        missing = manifest_mod.validate_completeness("ghana", years=[2024, 2025])
        assert len(missing) == 1
        assert missing[0].startswith("period_coverage:chirps_rainfall_daily")
        assert "does not cover 2024-2025" in missing[0]

    def test_validate_completeness_empty_years(self, aoi_dir, monkeypatch):
        """years=[] treated as no years (skip period check)."""
        import mal_core.download.manifest as manifest_mod
        # Period covers only 2023-2024, but we pass empty years list
        manifest = {
            "aoi": "ghana",
            "datasets": {
                "chirps_rainfall_daily": {
                    "type": "time-series",
                    "format": "tif",
                    "files": {"chirps_rainfall_daily": "ghana_rainfall_daily_2023_2024_env.nc"},
                    "period": {"start": "2023-01-01", "end": "2024-12-31"},
                }
            },
            "expected_files": ["ghana_rainfall_daily_2023_2024_env.nc"],
        }
        aoi_dir.mkdir(parents=True, exist_ok=True)
        (aoi_dir / "manifest.json").write_text(json.dumps(manifest))
        (aoi_dir / "ghana_rainfall_daily_2023_2024_env.nc").touch()

        # Empty years list should skip period checks (same as years=None)
        missing = manifest_mod.validate_completeness("ghana", years=[])
        assert missing == []