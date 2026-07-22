"""Minimal markdown report renderer for calibration scoring."""
from __future__ import annotations

from scorers.base import ScorerResult, ScoringReport


def verdict_label(composite: float) -> str:
    """Return verdict based on composite score thresholds."""
    if composite >= 0.70:
        return "VIABLE"
    elif composite >= 0.50:
        return "BORDERLINE"
    elif composite >= 0.30:
        return "REGRESSED"
    else:
        return "COLLAPSED"


def dimension_status(score: float, min_score: float, hard_floor: float) -> str:
    """Return per-dimension status."""
    if score < hard_floor:
        return "COLLAPSED"
    elif score < min_score:
        return "REGRESSED"
    else:
        return "OK"


def render_report(report: ScoringReport, thresholds: dict[str, dict]) -> str:
    """Render a ScoringReport as markdown.

    Args:
        report: The aggregated scoring report.
        thresholds: Per-dimension thresholds from thresholds.yaml.

    Returns:
        Markdown string.
    """
    lines: list[str] = []
    lines.append(f"# Calibration Report: {report.experiment_name}")
    lines.append("")

    # Composite + verdict
    verdict = verdict_label(report.composite)
    lines.append(f"**Composite score:** {report.composite:.4f}")
    lines.append(f"**Verdict:** {verdict}")
    lines.append(f"**Seeds:** {report.n_seeds} | **Days:** {report.n_days}")
    lines.append("")

    # Parameters
    if report.params:
        lines.append("## Parameters")
        lines.append("")
        for k, v in report.params.items():
            lines.append(f"- `{k}`: {v}")
        lines.append("")

    # Per-dimension table
    lines.append("## Dimensions")
    lines.append("")
    lines.append("| Dim | Score | Status | Value | Target |")
    lines.append("|-----|-------|--------|-------|--------|")

    for dim, result in sorted(report.scores.items()):
        th = thresholds.get(dim, {})
        min_sc = th.get("min_score", 0.0)
        hf = th.get("hard_floor", 0.0)
        status = dimension_status(result.score, min_sc, hf)
        lines.append(
            f"| {dim} | {result.score:.4f} | {status} | "
            f"{result.value:.4f} | {result.target} |"
        )
    lines.append("")

    # LLM verdict block
    if report.llm_verdict:
        lines.append("## LLM Verdict")
        lines.append("")
        lines.append(f"```")
        lines.append(str(report.llm_verdict))
        lines.append(f"```")
        lines.append("")

    return "\n".join(lines)
