"""Model registry — load models from a directory via ``model.yaml`` manifests.

Each model lives in its own subdirectory under the models root (default:
``runs/models/`` or ``runs/``). The manifest declares name, version, input/output
contract, and checkpoint path.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

import numpy as np
import yaml
from pydantic import BaseModel

from mal_commonlib.config import RUNS_DIR


class ModelProtocol(Protocol):
    def predict(self, state: np.ndarray, env: np.ndarray) -> np.ndarray: ...


class ModelManifest(BaseModel):
    name: str
    version: str = "1.0"
    contract_version: str = "1.1"
    in_channels: int = 10
    out_channels: int = 6
    checkpoint: str = ""
    description: str = ""


@dataclass
class RegistryEntry:
    manifest: ModelManifest
    path: Path
    model: ModelProtocol | None = None


class DummyModel:
    def predict(self, state: np.ndarray, env: np.ndarray) -> np.ndarray:
        out_ch = state.shape[0]
        h, w = state.shape[-2:]
        return np.zeros((out_ch, h, w), dtype=np.float32)


class ModelRegistry:
    def __init__(self, models_dir: Path | None = None):
        self.models_dir = models_dir or (RUNS_DIR / "models")
        self._entries: dict[str, RegistryEntry] = {}

    def scan(self) -> list[str]:
        self._entries.clear()
        search_dirs = [self.models_dir, RUNS_DIR]
        found = []

        for base in search_dirs:
            if not base.exists():
                continue
            for manifest_path in sorted(base.rglob("model.yaml")):
                try:
                    raw = yaml.safe_load(manifest_path.read_text())
                    manifest = ModelManifest.model_validate(raw)
                    key = f"{manifest.name}@{manifest.version}"
                    if key not in self._entries:
                        self._entries[key] = RegistryEntry(manifest=manifest, path=manifest_path.parent)
                        found.append(key)
                except Exception:
                    continue

        return found

    def get(self, name: str, version: str | None = None) -> RegistryEntry:
        if not self._entries:
            self.scan()

        if version:
            key = f"{name}@{version}"
        else:
            matches = [k for k in self._entries if k.startswith(f"{name}@")]
            if not matches:
                # Try fallback matching name directly
                if name in self._entries:
                    key = name
                else:
                    raise KeyError(f"Model {name!r} not found in {self.models_dir} or {RUNS_DIR}")
            else:
                key = matches[-1]

        if key not in self._entries:
            raise KeyError(f"Model {key!r} not found in {self.models_dir}")
        return self._entries[key]

    def load(self, name: str, version: str | None = None) -> ModelProtocol:
        if name == "dummy":
            return DummyModel()

        entry = self.get(name, version)
        if entry.model is not None:
            return entry.model

        if entry.manifest.checkpoint:
            from ..training.wrapper import UNetWrapper
            ckpt = entry.path / entry.manifest.checkpoint
            if not ckpt.exists():
                raise FileNotFoundError(
                    f"Checkpoint not found: {ckpt} (model {name}@{entry.manifest.version})"
                )
            entry.model = UNetWrapper(
                ckpt,
                in_channels=entry.manifest.in_channels,
                out_channels=entry.manifest.out_channels,
            )
        else:
            entry.model = DummyModel()
        return entry.model

    def list_models(self) -> list[dict[str, str]]:
        if not self._entries:
            self.scan()
        return [
            {"name": e.manifest.name, "version": e.manifest.version, "path": str(e.path)}
            for e in self._entries.values()
        ]
