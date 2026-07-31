"""Score-then-compare cycle — runs after any ABM task via ScorerPlugin hook."""
from __future__ import annotations
import json
from datetime import datetime, timezone
from pathlib import Path

def score_then_compare(ctx: dict) -> dict:
    """Run scorers on the ABM run, compare vs best history.
    
    Args:
        ctx: Context dict with keys: worktree_path, run_dir (optional), agent_id
    
    Returns:
        {"composite": float, "delta_vs_best": float, "verdict": str, "scorecard_path": str}
    """
    worktree = Path(ctx.get("worktree_path", "."))
    run_dir = ctx.get("run_dir")
    
    # Find the most recent run if run_dir not specified
    if not run_dir:
        runs_dir = worktree / "runs"
        if runs_dir.exists():
            run_dirs = sorted(runs_dir.iterdir(), key=lambda p: p.stat().st_mtime, reverse=True)
            for d in run_dirs:
                if d.is_dir() and (d / "trajectory.json").exists():
                    run_dir = str(d)
                    break
    
    if not run_dir:
        return {"error": "No run directory found", "status": "no_run"}
    
    try:
        from mal_core.abm.tests.calibration.scorers.score import score_run
        report = score_run(Path(run_dir))
    except Exception as e:
        return {"error": str(e), "status": "scorer_failed"}
    
    composite = report.get("composite", 0.0)
    
    # Compare vs best history
    best_history_path = worktree / "runs" / "scorecards" / "best_history.json"
    delta = 0.0
    verdict = "no_history"
    
    if best_history_path.exists():
        try:
            best = json.loads(best_history_path.read_text())
            best_composite = best.get("composite", 0.0)
            delta = composite - best_composite
            if delta >= 0.05:
                verdict = "candidate-promotion"
            elif delta <= -0.05:
                verdict = "regression"
            else:
                verdict = "candidate-keep"
        except (json.JSONDecodeError, OSError):
            verdict = "history_read_error"
    
    # Write scorecard
    scorecards_dir = worktree / "runs" / "scorecards"
    scorecards_dir.mkdir(parents=True, exist_ok=True)
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    scorecard = {
        "ts": ts,
        "composite": composite,
        "scores": report.get("scores", {}),
        "delta_vs_best": delta,
        "verdict": verdict,
        "run_dir": run_dir,
    }
    scorecard_path = scorecards_dir / f"{ts}.json"
    scorecard_path.write_text(json.dumps(scorecard, indent=2))
    
    # Update best history if this is better
    if verdict == "candidate-promotion":
        best_history_path.write_text(json.dumps(scorecard, indent=2))
    
    return {
        "composite": composite,
        "delta_vs_best": delta,
        "verdict": verdict,
        "scorecard_path": str(scorecard_path),
        "scores": report.get("scores", {}),
    }
