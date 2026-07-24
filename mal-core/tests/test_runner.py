"""Tests for the pipeline runner (stage dispatch)."""
from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# Ensure submodules are importable for patching
import mal_core.ingest
import mal_core.abm
import mal_core.scoring
import mal_core.training
import mal_core.prediction

from mal_core.pipeline.stages import Stage
from mal_core.pipeline.runner import run_stage


def test_run_stage_ingest(tmp_path):
    with patch.object(mal_core.ingest, "build_environment", return_value={"success": True}):
        result = run_stage(Stage.INGEST, "ghana", 2024, 1, tmp_path)
    assert result["success"] is True


def test_run_stage_abm(tmp_path):
    with patch.object(mal_core.abm, "run_abm", return_value={"stdout": "ok", "returncode": 0}):
        result = run_stage(Stage.ABM, "ghana", 2024, 1, tmp_path, days=7)
    assert result["returncode"] == 0


def test_run_stage_score(tmp_path):
    with patch.object(mal_core.scoring, "run_calibration", return_value={"success": True, "composite": 0.85}):
        result = run_stage(Stage.SCORE, "ghana", 2024, 1, tmp_path)
    assert result["success"] is True


def test_run_stage_train(tmp_path):
    with patch.object(mal_core.training, "train_unet", return_value=0.75):
        result = run_stage(Stage.TRAIN, "ghana", 2024, 1, tmp_path)
    assert result["best_dice"] == 0.75


def test_run_stage_predict(tmp_path):
    with patch.object(mal_core.prediction, "run_prediction", return_value=tmp_path / "pred.tif"):
        result = run_stage(Stage.PREDICT, "ghana", 2024, 1, tmp_path)
    assert "prediction_path" in result


def test_run_stage_unknown(tmp_path):
    with pytest.raises(ValueError, match="Unknown stage"):
        run_stage("invalid", "ghana", 2024, 1, tmp_path)
