"""Checks migrated from the retired scoring specification.

Every test here corresponds to one runnable assertion of the retired
scoring spec. The spec is gone; the facts live in the code and in this
file. See docs/plans/in-process/spec-retirement-ledger.md for the row
that maps each assertion to this test.
"""
from __future__ import annotations

import json
import math
import re
from pathlib import Path

import pytest

import mal_core.scoring.runner as runner_mod
from mal_core.scoring import llm_scorer
from mal_core.scoring.feedback import get_feedback
from mal_core.scoring.registry import (
    COMPOSITE_WEIGHTS,
    GATES,
    build_registry,
    list_scorers,
)
from mal_core.scoring.scorers.base import Scorer, ScorerResult

SCORING_SRC = Path(__file__).resolve().parents[1] / "src" / "mal_core" / "scoring"

# The exact weight table the retired spec pinned (scoring/spec.md INV-10).
EXPECTED_WEIGHTS = {
    "D16_detection_coverage": 4.0,
    "D2_survival": 4.0,
    "D15_persistence": 3.0,
    "D3_eip": 3.0,
    "D8_coupling": 2.0,
    "D4_stability": 2.0,
    "D25_cases_ghana": 2.0,
    "D19_pool_persistence": 1.0,
    "D20_washout_response": 1.0,
    "D1_habitat_occupancy": 1.0,
    "D5_morans": 1.0,
    "D11_aquatic_structure": 1.0,
    "D21_dispersal_kernel": 1.0,
}

EXPECTED_GATES = (
    "G6_data_valid",
    "G7_determinism",
    "G10_perf",
    "G12_host_input",
    "G24_urban_ratio",
)


# ---------------------------------------------------------------------------
# INV-5 / INV-6: the scorer suite layout and the stable ID set
# ---------------------------------------------------------------------------

def test_registry_has_exactly_the_13_composite_dims_and_5_gates():
    reg = build_registry()
    dims = sorted(n for n, s in reg.items() if s.kind == "composite")
    gates = sorted(n for n, s in reg.items() if s.kind == "gate")
    assert len(dims) == 13, dims
    assert len(gates) == 5, gates
    assert set(dims) == set(COMPOSITE_WEIGHTS)
    assert set(gates) == set(EXPECTED_GATES)


def test_scorer_id_set_is_stable():
    """The retired spec pinned the ID set (D1..D25 + G6..G24)."""
    reg = build_registry()
    ids = {n.split("_")[0] for n in reg}
    assert ids == {
        "D1", "D2", "D3", "D4", "D5", "D8", "D11", "D15", "D16", "D19",
        "D20", "D21", "D25",
        "G6", "G7", "G10", "G12", "G24",
    }


def test_composite_weights_are_exactly_the_pinned_table():
    assert COMPOSITE_WEIGHTS == EXPECTED_WEIGHTS


def test_each_composite_scorer_has_a_d_module_and_gates_live_in_gates_py():
    scorers_dir = SCORING_SRC / "scorers"
    modules = {p.name for p in scorers_dir.glob("d*_*.py")}
    for name in COMPOSITE_WEIGHTS:
        d_id = name.split("_")[0].lower()
        assert any(m.startswith(d_id + "_") for m in modules), (
            f"{name}: no scorers/{d_id}_*.py module")
    gates_source = (scorers_dir / "gates.py").read_text(encoding="utf-8")
    for gate in GATES:
        assert gate in gates_source, f"{gate} is not defined in scorers/gates.py"


def test_list_scorers_reports_kind_weight_and_manual_flag():
    rows = {r["name"]: r for r in list_scorers()}
    assert rows["D1_habitat_occupancy"]["kind"] == "composite"
    assert rows["D1_habitat_occupancy"]["weight"] == 1.0
    assert rows["G6_data_valid"]["kind"] == "gate"
    assert rows["G6_data_valid"]["weight"] == 0.0
    assert rows["D16_detection_coverage"]["manual"] is True


# ---------------------------------------------------------------------------
# INV-1 / INV-2: the runner writes scorecard.json and never crashes
# ---------------------------------------------------------------------------

class _FixedScorer(Scorer):
    """A scorer with a fixed score, used to pin the composite arithmetic."""

    name = "D99_fixed"
    kind = "composite"
    description = "test double"
    manual = False
    score_value = 0.5
    raises = False

    def score(self, run_dir, ctx):  # noqa: ANN001, ANN201
        if self.raises:
            raise RuntimeError("boom")
        return ScorerResult(score=self.score_value, value=self.score_value,
                            target="1.0", passed=True, status="ok")


class _FixedGate(Scorer):
    name = "G99_fixed"
    kind = "gate"
    description = "test double"
    manual = False

    def score(self, run_dir, ctx):  # noqa: ANN001, ANN201
        return ScorerResult(score=1.0, value=1.0, target="1.0",
                            passed=True, status="ok")


def _scorer(score: float, raises: bool = False):
    """A composite scorer class with the given fixed score.

    The runner instantiates scorers with no arguments, so the score has
    to live on the class, not on the instance.
    """
    _FixedScorer.score_value = score
    _FixedScorer.raises = raises
    return _FixedScorer


def _registry_stub(monkeypatch, scorers):
    """Replace the whole scorer registry with the given test doubles."""
    from mal_core.scoring import config as config_mod
    from mal_core.scoring.registry import ScorerSpec

    def _fake_build():
        return {c.name: ScorerSpec(cls=c, kind=c.kind) for c in scorers}

    monkeypatch.setattr(runner_mod, "build_registry", _fake_build)
    monkeypatch.setattr(config_mod, "build_registry", _fake_build)


def test_scorecard_json_is_written_inside_the_run_dir(tmp_path, monkeypatch):
    _registry_stub(monkeypatch, [_scorer(0.8), _FixedGate])
    card = runner_mod.run_scoring(tmp_path)
    written = tmp_path / "scorecard.json"
    assert written.exists()
    on_disk = json.loads(written.read_text())
    assert on_disk["composite"] == card["composite"]
    assert on_disk["run_dir"] == str(tmp_path)


def test_a_raising_scorer_becomes_skipped_not_a_crash(tmp_path, monkeypatch):
    _registry_stub(monkeypatch, [_scorer(0.8, raises=True), _FixedGate])
    card = runner_mod.run_scoring(tmp_path)
    assert "D99_fixed" in card["skipped"]
    assert "scorer raised" in card["skipped"]["D99_fixed"]
    assert card["composite"] == 0.0


def test_composite_is_the_weighted_geometric_mean(tmp_path, monkeypatch):
    _registry_stub(monkeypatch, [_scorer(0.8), _FixedGate])
    card = runner_mod.run_scoring(tmp_path)
    assert card["composite"] == pytest.approx(0.8, abs=1e-4)
    # The composite is exp(sum(w*log s) / sum(w)) over the "ok" dimensions.
    expected = math.exp(
        sum(w * math.log(0.8) for w in COMPOSITE_WEIGHTS.values())
        / sum(COMPOSITE_WEIGHTS.values())
    )
    assert card["composite"] == pytest.approx(expected, abs=1e-4)


def test_a_zero_dimension_collapses_the_composite(tmp_path, monkeypatch):
    _registry_stub(monkeypatch, [_scorer(0.0), _FixedGate])
    card = runner_mod.run_scoring(tmp_path)
    assert card["composite"] == 0.0


def test_skipped_dimensions_are_excluded_from_the_weight_sum(tmp_path, monkeypatch):
    """A dimension that is skipped does not drag the composite to zero."""
    _registry_stub(monkeypatch, [_scorer(0.5), _FixedGate])
    card = runner_mod.run_scoring(tmp_path)
    dims = card["composite_dimensions"]
    assert set(dims) == {"D99_fixed"}
    assert dims["D99_fixed"]["weight"] > 0


# ---------------------------------------------------------------------------
# INV-6b: missing required data => status "skipped", never score 0
# ---------------------------------------------------------------------------

def test_missing_data_yields_a_skipped_status_not_a_zero(tmp_path):
    """D16 needs occurrence data; with none it must report "skipped"."""
    card = runner_mod.run_scoring(tmp_path, enable=["D16_detection_coverage"])
    entry = card["scores"]["D16_detection_coverage"]
    assert entry["status"] == "skipped"
    assert "D16_detection_coverage" in card["skipped"]
    assert "D16_detection_coverage" not in card["composite_dimensions"]


# ---------------------------------------------------------------------------
# INV-12 / INV-13 / INV-17: the LLM judge is non-gating and OpenRouter-based
# ---------------------------------------------------------------------------

def test_llm_judge_is_not_gating_when_the_key_is_absent(tmp_path, monkeypatch):
    monkeypatch.delenv("OPENROUTER_KEY", raising=False)
    card = runner_mod.run_scoring(tmp_path)
    assert "verdict_llm" not in card


def test_llm_judge_uses_openrouter_and_the_pinned_model():
    assert "openrouter.ai" in llm_scorer.LLM_BASE_URL
    assert llm_scorer.LLM_MODEL_DEFAULT == "minimax/minimax-m3"
    source = Path(llm_scorer.__file__).read_text(encoding="utf-8")
    assert "OPENROUTER_KEY" in source


def test_llm_prompt_file_exists():
    prompt = SCORING_SRC / "prompts" / "llm_verdict.md"
    assert prompt.exists(), "scoring/prompts/llm_verdict.md is missing"


# ---------------------------------------------------------------------------
# INV-14: the feedback report
# ---------------------------------------------------------------------------

def test_feedback_reports_composite_verdict_failed_gates_and_regressions():
    card = {
        "composite": 0.42,
        "verdict": "REGRESSED",
        "composite_dimensions": {
            "D1_habitat_occupancy": {"score": 0.9, "weight": 1.0},
            "D2_survival": {"score": 0.2, "weight": 4.0},
        },
        "scores": {
            "D1_habitat_occupancy": {"target": "0.8"},
            "D2_survival": {"target": "0.9"},
        },
        "gates": {"G6_data_valid": {"passed": False}},
        "skipped": {"D25_cases_ghana": "no case data"},
    }
    baseline = {
        "composite": 0.60,
        "composite_dimensions": {
            "D1_habitat_occupancy": {"score": 0.9, "weight": 1.0},
            "D2_survival": {"score": 0.9, "weight": 4.0},
        },
    }
    text = get_feedback(card, baseline=baseline)
    assert "0.4200" in text
    assert "REGRESSED" in text
    assert "G6_data_valid" in text
    assert "D25_cases_ghana" in text
    assert "D2_survival" in text
    assert "Baseline composite" in text


# ---------------------------------------------------------------------------
# INV-16: the CLI dispatch
# ---------------------------------------------------------------------------

def test_cli_exposes_score_feedback_and_the_validation_wrappers():
    cli_src = (Path(__file__).resolve().parents[1] / "src" / "mal_core" /
               "cli.py").read_text(encoding="utf-8")
    assert re.search(r'@app\.command\("score"\)', cli_src)
    assert re.search(r"def feedback\(", cli_src)
    assert re.search(r'@app\.command\("validate-detections"\)', cli_src)
    assert re.search(r'@app\.command\("validate-cases"\)', cli_src)
