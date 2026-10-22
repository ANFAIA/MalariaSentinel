"""LLM judge (canon llm_scorer) — cache/fallback contract + opt-in call.

The real endpoint call is opt-in (``-m full``) because it needs
``OPENROUTER_KEY``. The deterministic parts (cache key, cache round-trip,
no-key fallback) run in the default suite: they are what the scorer does
on every CI run and in production when the key is absent.
"""
from __future__ import annotations

import os
from pathlib import Path

import pytest
from mal_core.scoring.llm_scorer import (
    LLM_MODEL_DEFAULT,
    _cache_path,
    _read_cache,
    _report_hash,
    _write_cache,
    deterministic_fallback,
    score_with_llm,
)


def _report(composite: float = 0.85) -> dict:
    return {
        "experiment": "test-perfect",
        "region": "Ghana 2024-06",
        "rollout_days": 30,
        "scores": {f"D{i}": composite for i in range(1, 11)},
        "composite": composite,
    }


def test_report_hash_is_stable_and_model_scoped():
    report = _report()
    first = _report_hash(report, "model-a")
    assert first == _report_hash(dict(report), "model-a")
    # A different model or a changed score must not reuse the verdict.
    assert first != _report_hash(report, "model-b")
    assert first != _report_hash(_report(0.5), "model-a")


def test_cache_roundtrip_and_corrupt_entry(tmp_path: Path):
    cache_file = _cache_path(tmp_path, "deadbeef")
    _write_cache(cache_file, {"verdict": "viable", "composite_estimate": 0.9})
    assert _read_cache(cache_file)["verdict"] == "viable"

    cache_file.write_text("{not json", encoding="utf-8")
    assert _read_cache(cache_file) is None
    missing = tmp_path / "missing.json"
    assert _read_cache(missing) is None


def test_missing_key_returns_deterministic_fallback(monkeypatch, tmp_path: Path):
    # The repo .env carries a real key; force the no-key branch explicitly.
    import mal_core.scoring.llm_scorer as llm

    monkeypatch.setattr(llm, "_load_api_key", lambda: None)
    result = score_with_llm(_report(0.42), cache_dir=tmp_path / "cache")
    assert result["verdict"] == "unknown"
    assert result["composite_estimate"] == pytest.approx(0.42)
    assert result["fallback"] == "OPENROUTER_KEY not set"
    assert result["concerns"] == []


def test_deterministic_fallback_shape():
    result = deterministic_fallback(_report(0.3), reason="timeout")
    assert result["verdict"] == "unknown"
    assert result["composite_estimate"] == pytest.approx(0.3)
    assert result["fallback"] == "timeout"


@pytest.mark.full
@pytest.mark.skipif(
    not os.environ.get("OPENROUTER_KEY"),
    reason="OPENROUTER_KEY not set (opt-in: -m full)",
)
def test_real_llm_call_returns_valid_verdict(tmp_path: Path) -> None:
    result = score_with_llm(_report(), cache_dir=tmp_path / "cache")
    assert result["verdict"] in {"viable", "borderline", "regressed", "collapsed"}
    assert 0.0 <= result["composite_estimate"] <= 1.0
    assert isinstance(result["concerns"], list)
    assert isinstance(result["recommendations"], list)
    assert isinstance(result["literature_grounding"], list)
    assert result.get("model") == LLM_MODEL_DEFAULT
