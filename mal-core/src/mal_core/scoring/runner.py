"""Run all configured scorers against one ABM output directory.

Writes ``scorecard.json`` INSIDE the run directory with:
- composite: weighted geometric mean over "ok" composite dimensions
  (skipped dimensions are excluded from both the score and the weight sum)
- gates: binary invariants reported apart (never in the composite)
- skipped: dimensions with missing artifacts/dependencies and why

Usage from the CLI: ``malariasim score --run-dir <dir> [--only ...]
[--skip ...] [--config <yaml>]``.
"""
from __future__ import annotations

import json
import math
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .config import ScoringConfig, load_config
from .registry import build_registry
from .scorers.base import Scorer, ScorerResult, load_run_metadata

VERDICTS = ((0.70, "VIABLE"), (0.50, "BORDERLINE"), (0.30, "REGRESSED"))


def _verdict(composite: float) -> str:
    for threshold, label in VERDICTS:
        if composite >= threshold:
            return label
    return "COLLAPSED"


def _build_ctx(run_dir: Path, aoi: str | None) -> dict[str, Any]:
    run_meta = load_run_metadata(run_dir)
    return {
        "aoi": aoi,
        "run_meta": run_meta,
        "run_dir": str(run_dir),
    }


def _result_to_dict(r: ScorerResult) -> dict[str, Any]:
    return {
        "score": r.score,
        "value": r.value,
        "target": r.target,
        "diagnostics": r.diagnostics,
        "passed": r.passed,
        "status": r.status,
    }


def run_scoring(
    run_dir: str | Path,
    aoi: str | None = None,
    config_path: str | Path | None = None,
    only: list[str] | None = None,
    skip: list[str] | None = None,
    enable: list[str] | None = None,
    ctx_extras: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Score one ABM run directory and save ``scorecard.json`` inside it."""
    run_dir = Path(run_dir)
    if not run_dir.is_dir():
        raise NotADirectoryError(f"run dir not found: {run_dir}")

    cfg: ScoringConfig = load_config(
        config_path=Path(config_path) if config_path else None,
        only=only,
        skip=skip,
        enable=enable,
    )
    registry = build_registry()
    ctx = _build_ctx(run_dir, aoi)
    if ctx_extras:
        ctx.update(ctx_extras)

    composite_scores: dict[str, float] = {}
    gates: dict[str, dict[str, Any]] = {}
    skipped: dict[str, str] = {}
    details: dict[str, dict[str, Any]] = {}

    for name, spec in sorted(registry.items()):
        if name not in cfg.enabled:
            scorer = spec.cls()
            reason = (
                "manual (AOI-dependent) — activate with --enable or scoring YAML"
                if scorer.manual
                else "disabled by config"
            )
            skipped[name] = reason
            continue
        scorer: Scorer = spec.cls()
        try:
            result = scorer.score(run_dir, ctx)
        except Exception as e:  # a broken scorer must not sink the run
            result = ScorerResult.skipped(f"scorer raised: {e}", target=scorer.name)
        details[name] = _result_to_dict(result)
        if result.status == "skipped":
            skipped[name] = result.diagnostics.get("skipped_reason", "unknown")
            continue
        if spec.kind == "composite":
            composite_scores[name] = result.score
        else:
            gates[name] = _result_to_dict(result)

    # weighted geometric mean over available dimensions only;
    # any zero dimension collapses the composite (geometric-mean semantics)
    composite = 0.0
    if composite_scores and all(s > 0 for s in composite_scores.values()):
        total_weight = sum(cfg.weight_of(n) for n in composite_scores)
        if total_weight > 0:
            log_sum = sum(
                cfg.weight_of(n) * math.log(s)
                for n, s in composite_scores.items()
            )
            composite = math.exp(log_sum / total_weight)

    scorecard: dict[str, Any] = {
        "run_dir": str(run_dir),
        "aoi": ctx.get("aoi"),
        "composite": round(composite, 4),
        "verdict": _verdict(composite),
        "scores": details,
        "composite_dimensions": {
            name: {"score": s, "weight": cfg.weight_of(name)}
            for name, s in sorted(composite_scores.items())
        },
        "gates": gates,
        "skipped": skipped,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }

    out_path = run_dir / "scorecard.json"
    out_path.write_text(json.dumps(scorecard, indent=2, default=str))
    return scorecard


def format_summary(scorecard: dict[str, Any]) -> str:
    """Compact human-readable summary for the CLI."""
    lines = [
        f"Composite: {scorecard['composite']:.4f}  "
        f"Verdict: {scorecard['verdict']}",
        "",
        "Composite dimensions:",
    ]
    for name, info in scorecard.get("composite_dimensions", {}).items():
        s = scorecard["scores"][name]
        marker = "ok " if s["passed"] else "LOW"
        lines.append(
            f"  [{marker}] {name:28s} {s['score']:.3f} "
            f"(w={info['weight']}) value={s['value']} target={s['target']}"
        )
    if scorecard.get("gates"):
        lines.append("")
        lines.append("Gates (binary, outside composite):")
        for name, g in scorecard["gates"].items():
            marker = "PASS" if g["passed"] else "FAIL"
            lines.append(f"  [{marker}] {name:28s} {g['score']:.3f}")
    if scorecard.get("skipped"):
        lines.append("")
        lines.append("Skipped:")
        for name, reason in scorecard["skipped"].items():
            lines.append(f"  [SKIP] {name:28s} {reason}")
    lines.append("")
    lines.append(f"Scorecard saved: {Path(scorecard['run_dir']) / 'scorecard.json'}")
    return "\n".join(lines)
