"""M3-M4 & M7.4 — U-Net model wrapper for SDSS prediction and model registry.

Implements ModelProtocol so the U-Net can be registered in the model registry.
Supports dynamic in_channels and out_channels (e.g. 6+4 -> 6, or 2+4 -> 2).
"""
from __future__ import annotations

from pathlib import Path
import yaml

import numpy as np
import torch
import torch.nn.functional as F

from .model import UNet


class UNetWrapper:
    """Wraps the U-Net to implement ModelProtocol for SDSS inference."""

    def __init__(
        self,
        checkpoint_path: str | Path,
        device: str | None = None,
        in_channels: int | None = None,
        out_channels: int | None = None,
    ):
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

        # 1. Try reading manifest model.yaml in the checkpoint directory
        manifest_path = self.checkpoint_path.parent / "model.yaml"
        if manifest_path.exists():
            try:
                with open(manifest_path) as f:
                    meta = yaml.safe_load(f)
                in_channels = in_channels or meta.get("in_channels")
                out_channels = out_channels or meta.get("out_channels")
            except Exception:
                pass

        # 2. Load state dict and infer shapes if not provided
        state_dict = torch.load(self.checkpoint_path, map_location=self.device, weights_only=True)
        if in_channels is None:
            # enc.0.block.0.weight shape: (channels, in_channels, 3, 3)
            first_w = state_dict.get("enc.0.block.0.weight")
            in_channels = first_w.shape[1] if first_w is not None else 6
        if out_channels is None:
            # head.weight shape: (out_channels, channels, 1, 1)
            head_w = state_dict.get("head.weight")
            out_channels = head_w.shape[0] if head_w is not None else 2

        self.in_channels = in_channels
        self.out_channels = out_channels

        self.model = UNet(in_channels=in_channels, out_channels=out_channels).to(self.device)
        self.model.load_state_dict(state_dict)
        self.model.eval()

    @torch.no_grad()
    def predict(self, state: np.ndarray, env: np.ndarray) -> np.ndarray:
        """Predict state_{t+1} from state_t + env.

        Args:
            state: (C_state, H, W) float32
            env: (C_env, H, W) float32

        Returns:
            prediction: (C_out, H, W) float32
        """
        # Ensure correct channel alignment
        total_ch = state.shape[0] + env.shape[0]
        if total_ch < self.in_channels:
            missing = self.in_channels - total_ch
            pad_ch = np.zeros((missing, state.shape[1], state.shape[2]), dtype=np.float32)
            x = np.concatenate([state, env, pad_ch], axis=0)
        elif total_ch > self.in_channels:
            x = np.concatenate([state, env], axis=0)[:self.in_channels]
        else:
            x = np.concatenate([state, env], axis=0)

        orig_h, orig_w = x.shape[-2], x.shape[-1]

        # Pad to multiple of 16 for UNet 4-stage pooling
        pad_h = (16 - (orig_h % 16)) % 16
        pad_w = (16 - (orig_w % 16)) % 16

        x_tensor = torch.from_numpy(x).unsqueeze(0).to(self.device)
        if pad_h > 0 or pad_w > 0:
            x_tensor = F.pad(x_tensor, (0, pad_w, 0, pad_h), mode="replicate")

        pred = self.model(x_tensor)

        # Crop back to original dimensions
        if pad_h > 0 or pad_w > 0:
            pred = pred[:, :, :orig_h, :orig_w]

        return pred.squeeze(0).cpu().numpy().astype(np.float32)
