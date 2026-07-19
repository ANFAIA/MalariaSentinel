"""M3-M4 — U-Net model wrapper for M5 SDSS shell.

Implements ModelProtocol so the U-Net can be registered in the model registry.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import torch

from mal_core import UNet


class UNetWrapper:
    """Wraps the U-Net to implement ModelProtocol for M5."""

    def __init__(self, checkpoint_path: str | Path, device: str | None = None):
        self.checkpoint_path = Path(checkpoint_path)
        if device is None:
            if torch.cuda.is_available():
                self.device = "cuda"
            elif torch.backends.mps.is_available():
                self.device = "mps"
            else:
                self.device = "cpu"
        else:
            self.device = device

        self.model = UNet().to(self.device)
        self.model.load_state_dict(
            torch.load(self.checkpoint_path, map_location=self.device, weights_only=True)
        )
        self.model.eval()

    @torch.no_grad()
    def predict(self, state: np.ndarray, env: np.ndarray) -> np.ndarray:
        """Predict state_{t+1} from state_t + env.

        Args:
            state: (C=2, H, W) float32
            env: (C_env=4, H, W) float32

        Returns:
            prediction: (C=2, H, W) float32
        """
        x = np.concatenate([state, env], axis=0)
        x_tensor = torch.from_numpy(x).unsqueeze(0).to(self.device)

        pred = self.model(x_tensor)
        return pred.squeeze(0).cpu().numpy()
