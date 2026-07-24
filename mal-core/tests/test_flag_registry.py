"""Tests for the flag registry."""
from __future__ import annotations

import pytest

from mal_core.pipeline.flag_registry import aggregate_flags, get_stage_flags


def test_aggregate_flags_returns_all_stages():
    flags = aggregate_flags()
    assert "ingest" in flags
    assert "abm" in flags
    assert "scoring" in flags
    assert "training" in flags
    assert "prediction" in flags


def test_abm_flags_schema():
    flags = get_stage_flags("abm")
    assert "aoi" in flags
    assert "days" in flags
    assert "n_rollouts" in flags
    assert flags["aoi"]["type"] is str
    assert flags["days"]["type"] is int


def test_ingest_flags_schema():
    flags = get_stage_flags("ingest")
    assert "aoi" in flags
    assert "year" in flags
    assert "skip_era5" in flags


def test_training_flags_schema():
    flags = get_stage_flags("training")
    assert "epochs" in flags
    assert "batch_size" in flags
    assert "lr" in flags


def test_scoring_flags_schema():
    flags = get_stage_flags("scoring")
    assert "tier" in flags


def test_prediction_flags_schema():
    flags = get_stage_flags("prediction")
    assert "model" in flags


def test_unknown_stage_returns_empty():
    flags = get_stage_flags("nonexistent")
    assert flags == {}
