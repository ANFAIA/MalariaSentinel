"""Track the best historical scorecard."""
from __future__ import annotations
import json
from pathlib import Path
from typing import Any

BEST_SCORECARD_NAME = "best_scorecard.json"

def load_best(run_dir: Path) -> dict[str, Any] | None:
    """Load the best scorecard from the run directory's parent."""
    best_path = run_dir.parent / BEST_SCORECARD_NAME
    if not best_path.exists():
        return None
    return json.loads(best_path.read_text())

def save_best(scorecard: dict[str, Any], run_dir: Path) -> None:
    """Save the best scorecard to the run directory's parent."""
    best_path = run_dir.parent / BEST_SCORECARD_NAME
    best_path.parent.mkdir(parents=True, exist_ok=True)
    best_path.write_text(json.dumps(scorecard, indent=2, default=str))

def update_best(current: dict[str, Any], run_dir: Path) -> tuple[bool, dict[str, Any] | None]:
    """Compare current scorecard vs best. Update if current is better.
    
    Returns (updated, previous_best).
    """
    prev_best = load_best(run_dir)
    current_composite = current.get("composite", 0.0)
    
    if prev_best is None or current_composite > prev_best.get("composite", 0.0):
        save_best(current, run_dir)
        return True, prev_best
    
    return False, prev_best
