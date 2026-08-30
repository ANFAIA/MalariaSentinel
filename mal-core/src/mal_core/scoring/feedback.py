"""Human-readable feedback from a post-run scorecard."""
from __future__ import annotations

from typing import Any


def _lowest(scorecard: dict[str, Any], n: int = 3) -> list[tuple[str, float]]:
    dims = scorecard.get("composite_dimensions", {})
    ranked = sorted(
        ((name, info["score"]) for name, info in dims.items()),
        key=lambda kv: kv[1],
    )
    return ranked[:n]


def get_feedback(scorecard: dict[str, Any], baseline: dict[str, Any] | None = None) -> str:
    lines = ["## Scoring Feedback", ""]
    composite = scorecard.get("composite", 0.0)
    verdict = scorecard.get("verdict", "?")
    lines.append(f"Composite: {composite:.4f} ({verdict})")

    failed_gates = [
        name for name, g in scorecard.get("gates", {}).items() if not g.get("passed")
    ]
    if failed_gates:
        lines.append(f"Failed gates: {', '.join(failed_gates)}")
    skipped = scorecard.get("skipped", {})
    if skipped:
        lines.append(f"Skipped scorers: {', '.join(sorted(skipped))}")
    lines.append("")

    if baseline is not None:
        base = baseline.get("composite", 0.0)
        delta = composite - base
        lines.append("### Delta vs baseline")
        lines.append(f"Baseline composite: {base:.4f} -> {delta:+.4f}")
        base_dims = baseline.get("composite_dimensions", {})
        cur_dims = scorecard.get("composite_dimensions", {})
        regressions = []
        for name, info in cur_dims.items():
            if name in base_dims:
                d = info["score"] - base_dims[name]["score"]
                if d < -0.05:
                    regressions.append(f"{name} ({d:+.3f})")
        if regressions:
            lines.append(f"Regressed dimensions: {', '.join(regressions)}")
        lines.append("")

    lines.append("### Weakest dimensions")
    for name, score in _lowest(scorecard):
        target = scorecard.get("scores", {}).get(name, {}).get("target", "")
        lines.append(f"- {name}: {score:.3f} (target {target})")
    return "\n".join(lines)
