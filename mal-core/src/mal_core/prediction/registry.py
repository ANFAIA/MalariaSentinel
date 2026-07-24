"""Model registry — load models from a directory via ``model.yaml`` manifests.

Each model lives in its own subdirectory under the models root (default:
``runs/models/``). The manifest declares name, version, input/output
contract, and checkpoint path.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Protocol

import numpy as np
import yaml
from pydantic import BaseModel, Field

from mal_commonlib.config import RUNS_DIR


class ModelProtocol(Protocol):
    def predict(self, state: np.ndarray, env: np.ndarray) -> np.ndarray: ...


class ModelManifest(BaseModel):
    name: str
    version: str
    contract_version: str = "1.1"
    in_channels: int = 5
    out_channels: int = 1
    checkpoint: str = ""
    description: str = ""


@dataclass
class RegistryEntry:
    manifest: ModelManifest
    path: Path
    model: ModelProtocol | None = None


class DummyModel:
    def predict(self, state: np.ndarray, env: np.ndarray) -> np.ndarray:
        h, w = state.shape[-2:]
        return np.zeros((1, h, w), dtype=np.float32)


class ModelRegistry:
    def __init__(self, models_dir: Path | None = None):
        self.models_dir = models_dir or (RUNS_DIR / "models")
        self._entries: dict[str, RegistryEntry] = {}

    def scan(self) -> list[str]:
        self._entries.clear()
        if not self.models_dir.exists():
            return []
        found = []
        for entry_dir in sorted(self.models_dir.iterdir()):
            manifest_path = entry_dir / "model.yaml"
            if manifest_path.exists():
                raw = yaml.safe_load(manifest_path.read_text())
                manifest = ModelManifest.model_validate(raw)
                key = f"{manifest.name}@{manifest.version}"
                self._entries[key] = RegistryEntry(manifest=manifest, path=entry_dir)
                found.append(key)
        return found

    def get(self, name: str, version: str | None = None) -> RegistryEntry:
        if not self._entries:
            self.scan()
        if version:
            key = f"{name}@{version}"
        else:
            matches = [k for k in self._entries if k.startswith(f"{name}@")]
            if not matches:
                raise KeyError(f"Model {name!r} not found in {self.models_dir}")
            key = matches[-1]
        if key not in self._entries:
            raise KeyError(f"Model {key!r} not found in {self.models_dir}")
        return self._entries[key]

    def load(self, name: str, version: str | None = None) -> ModelProtocol:
        entry = self.get(name, version)
        if entry.model is not None:
            return entry.model

        # If the manifest points to a checkpoint, load the U-Net wrapper.
        if entry.manifest.checkpoint:
            from ..training.wrapper import UNetWrapper
            ckpt = entry.path / entry.manifest.checkpoint
            if not ckpt.exists():
                raise FileNotFoundError(
                    f"Checkpoint not found: {ckpt} (model {name}@{entry.manifest.version})"
                )
            entry.model = UNetWrapper(ckpt)
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
