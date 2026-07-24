"""Tests for the pipeline orchestrator."""
from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from mal_core.pipeline.stages import Stage
from mal_core.pipeline.runner import run_pipeline, run_stage


def test_stage_enum():
    assert Stage.INGEST.value == "ingest"
    assert Stage.ABM.value == "abm"
    assert Stage.SCORE.value == "score"
    assert Stage.TRAIN.value == "train"
    assert Stage.PREDICT.value == "predict"


def test_stage_from_string():
    assert Stage("ingest") == Stage.INGEST
    assert Stage("abm") == Stage.ABM


def test_run_pipeline_returns_structure(tmp_path):
    """run_pipeline returns the expected dict structure."""
    with patch("mal_core.pipeline.runner.run_stage") as mock_run:
        mock_run.return_value = {"success": True}
        result = run_pipeline(
            aoi="ghana", year=2024, month=1,
            stages=[Stage.INGEST],
            output_dir=tmp_path / "out",
            resume=False,
        )
    assert "stages_run" in result
    assert "stages_skipped" in result
    assert "artifacts" in result
    assert "errors" in result


def test_run_pipeline_resume_skips(tmp_path):
    """Completed stages are skipped when resume=True."""
    stage_dir = tmp_path / "out" / "ingest"
    stage_dir.mkdir(parents=True)
    (stage_dir / "dummy.txt").write_text("done")

    result = run_pipeline(
        aoi="ghana", year=2024, month=1,
        stages=[Stage.INGEST],
        output_dir=tmp_path / "out",
        resume=True,
    )
    assert "ingest" in result["stages_skipped"]
    assert "ingest" not in result["stages_run"]
