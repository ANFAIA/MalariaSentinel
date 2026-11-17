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
    """Protocol of a runnable prediction model."""
    def predict(self, state: np.ndarray, env: np.ndarray) -> np.ndarray:
        """Predict an output raster from the state stack and the environment stack."""
        ...


class ModelManifest(BaseModel):
    """The contents of a model directory's ``model.yaml``: its identity, its channel counts and the checkpoint it uses."""
    name: str
    version: str = "1.0"
    contract_version: str = "1.1"
    in_channels: int = 10
    out_channels: int = 6
    checkpoint: str = ""
    description: str = ""


@dataclass
class RegistryEntry:
    """One model known to the registry: its manifest, the directory holding it and the loaded model object."""
    manifest: ModelManifest
    path: Path
    model: ModelProtocol | None = None


class DummyModel:
    """Placeholder model used when no trained checkpoint is available."""
    def predict(self, state: np.ndarray, env: np.ndarray) -> np.ndarray:
        """Return an all-zero raster with one band per state channel."""
        out_ch = state.shape[0]
        h, w = state.shape[-2:]
        return np.zeros((out_ch, h, w), dtype=np.float32)


class ModelRegistry:
    """Catalogue of the models available on disk, discovered from the ``model.yaml`` manifests of their directories."""
    def __init__(self, models_dir: Path | None = None):
        """Create a registry over the given models directory, defaulting to the runs directory."""
        self.models_dir = models_dir or (RUNS_DIR / "models")
        self._entries: dict[str, RegistryEntry] = {}

    def scan(self) -> list[str]:
        """Search the model directories for manifests and return the keys found, as ``name@version``."""
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
        """The registry entry for a model name and, optionally, a version; raises ``KeyError`` when no such model is registered."""
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
        """The runnable model for a name and version, loading its checkpoint on first use; raises ``FileNotFoundError`` when the checkpoint is missing."""
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
        """The catalogue as a list of dicts holding each model's name, version and directory."""
        if not self._entries:
            self.scan()
        return [
            {"name": e.manifest.name, "version": e.manifest.version, "path": str(e.path)}
            for e in self._entries.values()
        ]
