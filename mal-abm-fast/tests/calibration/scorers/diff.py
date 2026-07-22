"""Diff two scorecards and render a dual-delta markdown table."""
from __future__ import annotations
import json
import sys
from pathlib import Path
from typing import Any


def diff_scorecards(a: dict[str, Any], b: dict[str, Any], best: dict[str, Any] | None = None) -> str:
    """Compare two scorecards. Returns a markdown string.
    
    - a: the previous scorecard
    - b: the current scorecard
    - best: the best historical scorecard (optional)
    """
    lines = []
    lines.append(f"# Delta Report: {a['experiment']['name']} → {b['experiment']['name']}")
    lines.append("")
    
    # Header
    if best:
        header = "| Dim | Prev | Current | Best | Δ prev | Δ best | Status |"
        sep = "|---|---|---|---|---|---|---|"
    else:
        header = "| Dim | Prev | Current | Δ prev | Status |"
        sep = "|---|---|---|---|---|"
    lines.append(header)
    lines.append(sep)
    
    # Rows
    all_dims = sorted(set(list(a.get("scores", {}).keys()) + list(b.get("scores", {}).keys())))
    for dim in all_dims:
        sa = a.get("scores", {}).get(dim, {}).get("score", 0.0)
        sb = b.get("scores", {}).get(dim, {}).get("score", 0.0)
        delta = sb - sa
        
        if best:
            sbest = best.get("scores", {}).get(dim, {}).get("score", 0.0)
            delta_best = sb - sbest
            status_parts = []
            status_parts.append("✅" if delta >= 0 else "❌")
            status_parts.append("✅" if delta_best >= 0 else "⚠️")
            status = " / ".join(status_parts)
            lines.append(f"| {dim} | {sa:.3f} | {sb:.3f} | {sbest:.3f} | {delta:+.3f} | {delta_best:+.3f} | {status} |")
        else:
            status = "✅" if delta >= 0 else "❌"
            lines.append(f"| {dim} | {sa:.3f} | {sb:.3f} | {delta:+.3f} | {status} |")
    
    # Composite
    ca = a.get("composite", 0.0)
    cb = b.get("composite", 0.0)
    delta_c = cb - ca
    if best:
        cbest = best.get("composite", 0.0)
        delta_best_c = cb - cbest
        status_c = f"{'✅' if delta_c >= 0 else '❌'} / {'✅' if delta_best_c >= 0 else '⚠️'}"
        lines.append(f"| **Composite** | {ca:.3f} | {cb:.3f} | {cbest:.3f} | {delta_c:+.3f} | {delta_best_c:+.3f} | {status_c} |")
    else:
        status_c = "✅" if delta_c >= 0 else "❌"
        lines.append(f"| **Composite** | {ca:.3f} | {cb:.3f} | {delta_c:+.3f} | {status_c} |")
    
    return "\n".join(lines)


def main():
    """CLI: python -m scorers.diff <scorecard_a.json> <scorecard_b.json> [--best <best.json>]"""
    import argparse
    parser = argparse.ArgumentParser(description="Diff two scorecards")
    parser.add_argument("scorecard_a", type=Path, help="Previous scorecard")
    parser.add_argument("scorecard_b", type=Path, help="Current scorecard")
    parser.add_argument("--best", type=Path, default=None, help="Best historical scorecard")
    args = parser.parse_args()
    
    a = json.loads(args.scorecard_a.read_text())
    b = json.loads(args.scorecard_b.read_text())
    best = json.loads(args.best.read_text()) if args.best and args.best.exists() else None
    
    print(diff_scorecards(a, b, best))

if __name__ == "__main__":
    main()
