"""Scoring configuration: enable/disable scorers and override weights.

Defaults live in ``registry.py``. A YAML config (optional) can disable
scorers or change weights; CLI ``--only``/``--skip`` win over the file.

YAML shape::

    scorers:
      D5_morans:
        enabled: false
      D16_suitability_auc:
        weight: 5.0
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

from .registry import COMPOSITE_WEIGHTS, build_registry


@dataclass
class ScoringConfig:
    enabled: set[str] = field(default_factory=set)
    weights: dict[str, float] = field(default_factory=dict)

    def weight_of(self, name: str) -> float:
        return self.weights.get(name, COMPOSITE_WEIGHTS.get(name, 1.0))


def default_config() -> ScoringConfig:
    """Default: every scorer EXCEPT manual (AOI-dependent) ones.

    Manual scorers — occurrence AUCs, urban ratio, future case-data
    scorers — require per-AOI datasets and are only activated
    explicitly (``--enable`` or YAML).
    """
    registry = build_registry()
    auto = {
        name for name, spec in registry.items() if not spec.cls().manual
    }
    return ScoringConfig(
        enabled=auto,
        weights=dict(COMPOSITE_WEIGHTS),
    )


def load_config(
    config_path: Path | None = None,
    only: list[str] | None = None,
    skip: list[str] | None = None,
    enable: list[str] | None = None,
) -> ScoringConfig:
    cfg = default_config()
    registry = build_registry()
    canonical = {name.lower(): name for name in registry}

    def _resolve(names: list[str]) -> list[str]:
        resolved = []
        for raw in names:
            name = raw.strip()
            if not name:
                continue
            canon = canonical.get(name.lower())
            if canon is None:
                raise ValueError(
                    f"unknown scorer '{name}' (see: malariasim score --list)"
                )
            resolved.append(canon)
        return resolved

    if enable:
        cfg.enabled.update(_resolve(enable))
    if config_path is not None:
        if not config_path.exists():
            raise FileNotFoundError(f"scoring config not found: {config_path}")
        raw: dict[str, Any] = yaml.safe_load(config_path.read_text()) or {}
        for name, spec in (raw.get("scorers") or {}).items():
            if not isinstance(spec, dict) or name not in registry:
                continue
            if spec.get("enabled") is True:
                cfg.enabled.add(name)
            elif spec.get("enabled") is False:
                cfg.enabled.discard(name)
            if "weight" in spec:
                cfg.weights[name] = float(spec["weight"])
    if only:
        keep = set(_resolve(only))
        cfg.enabled &= keep
    if skip:
        cfg.enabled -= set(_resolve(skip))
    return cfg
