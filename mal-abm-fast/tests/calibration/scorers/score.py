"""Run all scorers on a run directory and produce scorecard.json."""
from __future__ import annotations
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

# Add parent to path so scorers can import each other
sys.path.insert(0, str(Path(__file__).parent.parent))

from scorers.base import ScorerResult, ScoringReport
from scorers.composite import geometric_mean
from scorers.mortality import MortalityScorer
from scorers.eip import EIPScorer
from scorers.stability import StabilityScorer
from scorers.expansion import ExpansionScorer
from scorers.spatial import MoransScorer
from scorers.mass import MassScorer
from scorers.determinism import DeterminismScorer
from scorers.coupling import CouplingScorer
from scorers.activation import ActivationScorer
from scorers.performance import PerformanceScorer

ALL_SCORERS = [
    ExpansionScorer(),      # D1
    MortalityScorer(),      # D2
    EIPScorer(),            # D3
    StabilityScorer(),      # D4
    MoransScorer(),         # D5
    MassScorer(),           # D6
    DeterminismScorer(),    # D7
    CouplingScorer(),       # D8
    ActivationScorer(),     # D9
    PerformanceScorer(),    # D10
]

def score_run(run_dir: Path, experiment: dict[str, Any]) -> dict[str, Any]:
    """Run all scorers on a run directory. Returns a scorecard dict."""
    scores: dict[str, ScorerResult] = {}
    for scorer in ALL_SCORERS:
        try:
            result = scorer.score(run_dir, experiment)
        except Exception as e:
            result = ScorerResult(score=0.0, value=0.0, target=scorer.name,
                                  diagnostics={"error": str(e)}, passed=False)
        scores[scorer.name] = result
    
    composite = geometric_mean(scores)
    
    return {
        "experiment": {
            "name": experiment.get("name", "unknown"),
            "params": experiment.get("params", {}),
            "n_days": experiment.get("n_days", 90),
            "n_seeds": experiment.get("n_seeds", 1),
        },
        "scores": {
            name: {
                "score": r.score,
                "value": r.value,
                "target": r.target,
                "diagnostics": r.diagnostics,
                "passed": r.passed,
            }
            for name, r in scores.items()
        },
        "composite": round(composite, 4),
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "run_dir": str(run_dir),
    }

def save_scorecard(scorecard: dict[str, Any], path: Path) -> None:
    """Save scorecard to JSON."""
    path.write_text(json.dumps(scorecard, indent=2, default=str))

def main():
    """CLI entry point: python -m scorers.score --run-dir <path> [--experiment <name>]"""
    import argparse
    parser = argparse.ArgumentParser(description="Score an ABM run")
    parser.add_argument("--run-dir", required=True, type=Path, help="Path to run directory")
    parser.add_argument("--experiment", default="default", help="Experiment name from registry")
    args = parser.parse_args()
    
    if not args.run_dir.is_dir():
        print(f"Error: {args.run_dir} is not a directory", file=sys.stderr)
        sys.exit(1)
    
    # Load experiment from registry or use defaults
    try:
        from experiments.registry import EXPERIMENTS
        experiment = EXPERIMENTS.get(args.experiment, {}).to_dict() if hasattr(EXPERIMENTS.get(args.experiment, {}), 'to_dict') else {"name": args.experiment, "params": {}, "n_days": 90, "n_seeds": 1}
    except Exception:
        experiment = {"name": args.experiment, "params": {}, "n_days": 90, "n_seeds": 1}
    
    scorecard = score_run(args.run_dir, experiment)
    output_path = args.run_dir / "scorecard.json"
    save_scorecard(scorecard, output_path)
    print(f"Scorecard saved to {output_path}")
    print(f"Composite: {scorecard['composite']}")
    for name, s in scorecard["scores"].items():
        status = "✅" if s["passed"] else "❌"
        print(f"  {name}: {s['score']:.3f} {status}")

if __name__ == "__main__":
    main()
