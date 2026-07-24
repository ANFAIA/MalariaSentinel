"""Generate feedback from a calibration scorecard."""
from __future__ import annotations

def get_feedback(scorecard: dict, baseline: dict | None = None) -> str:
    lines = ["## Calibration Feedback\n"]
    if scorecard.get("success"):
        lines.append("All calibration tests passed.\n")
    else:
        lines.append("Some calibration tests failed.\n")
        if scorecard.get("stderr"):
            lines.append(f"Errors:\n```\n{scorecard['stderr'][:500]}\n```\n")
    if baseline:
        lines.append("### Delta vs baseline\n")
        if baseline.get("success") and not scorecard.get("success"):
            lines.append("Regression: baseline passed, current run failed.\n")
        elif not baseline.get("success") and scorecard.get("success"):
            lines.append("Improvement: current run passes where baseline failed.\n")
    return "\n".join(lines)
