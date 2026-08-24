"""Tests for the adapted U-Net surrogate training pipeline (M3-M4 & M7.4)."""
from __future__ import annotations

import tempfile
from pathlib import Path

import numpy as np
import pytest
import rasterio
import torch

from mal_core.training import UNet, combined_loss, eval_dice, RolloutDataset, train_unet, UNetWrapper


def _create_synthetic_run_dir(tmp_path: Path, n_days: list[int] = [2, 4, 6], with_trans: bool = True):
    """Create dummy GeoTIFF snapshots for testing."""
    H, W = 256, 256
    profile = {
        "driver": "GTiff",
        "dtype": "float32",
        "height": H,
        "width": W,
        "crs": "EPSG:4326",
        "transform": rasterio.transform.from_bounds(-3.0, 4.0, 1.0, 11.0, W, H),
    }

    for d in n_days:
        state_path = tmp_path / f"ghana_abm_day{d:03d}.tif"
        with rasterio.open(state_path, "w", count=2, **profile) as dst:
            dst.write(np.random.uniform(0.0, 5.0, (2, H, W)).astype(np.float32))

        if with_trans:
            trans_path = tmp_path / f"ghana_abm_transmission_day{d:03d}.tif"
            with rasterio.open(trans_path, "w", count=4, **profile) as dst:
                dst.write(np.random.uniform(0.0, 1.0, (4, H, W)).astype(np.float32))


def test_unet_shapes():
    """UNet forward pass with standard (6->2) and transmission (10->6) channels."""
    # Standard: 2 state + 4 env = 6 in, 2 out
    m_std = UNet(in_channels=6, out_channels=2)
    x_std = torch.randn(2, 6, 128, 128)
    out_std = m_std(x_std)
    assert out_std.shape == (2, 2, 128, 128)

    # Transmission: 6 state + 4 env = 10 in, 6 out
    m_trans = UNet(in_channels=10, out_channels=6)
    x_trans = torch.randn(2, 10, 128, 128)
    out_trans = m_trans(x_trans)
    assert out_trans.shape == (2, 6, 128, 128)


def test_combined_loss():
    pred = torch.tensor([[[[0.5, 0.0], [0.0, 0.8]]]], dtype=torch.float32)
    target = torch.tensor([[[[0.5, 0.0], [0.0, 0.9]]]], dtype=torch.float32)
    loss, mse_val, sd_val = combined_loss(pred, target)
    assert isinstance(loss, torch.Tensor)
    assert mse_val >= 0.0
    assert sd_val >= 0.0


def test_rollout_dataset_paired_loading(tmp_path: Path):
    _create_synthetic_run_dir(tmp_path, n_days=[2, 4, 6], with_trans=True)

    ds = RolloutDataset(tmp_path, split="train", patch_size=128, include_transmission=True)
    assert len(ds) > 0

    x, y = ds[0]
    # Input x: 2 (vector) + 4 (trans) + 4 (env) = 10 channels
    assert x.shape == (10, 128, 128)
    # Target y: 2 (vector) + 4 (trans) = 6 channels
    assert y.shape == (6, 128, 128)


def test_rollout_dataset_no_transmission(tmp_path: Path):
    _create_synthetic_run_dir(tmp_path, n_days=[2, 4, 6], with_trans=False)

    ds = RolloutDataset(tmp_path, split="train", patch_size=128, include_transmission=False)
    assert len(ds) > 0

    x, y = ds[0]
    # Input x: 2 (vector) + 4 (env) = 6 channels
    assert x.shape == (6, 128, 128)
    # Target y: 2 (vector) = 2 channels
    assert y.shape == (2, 128, 128)


def test_train_unet_end_to_end(tmp_path: Path):
    run_dir = tmp_path / "run"
    run_dir.mkdir()
    out_dir = tmp_path / "model_out"
    out_dir.mkdir()

    _create_synthetic_run_dir(run_dir, n_days=[2, 4, 6], with_trans=True)

    best_dice = train_unet(
        run_dir=run_dir,
        output_dir=out_dir,
        epochs=2,
        batch_size=2,
        device="cpu",
        include_transmission=True,
    )

    assert (out_dir / "best_model.pt").exists()
    assert (out_dir / "model.yaml").exists()

    # Test loading into UNetWrapper
    wrapper = UNetWrapper(out_dir / "best_model.pt", device="cpu")
    dummy_state = np.zeros((6, 256, 256), dtype=np.float32)
    dummy_env = np.zeros((4, 256, 256), dtype=np.float32)
    pred = wrapper.predict(dummy_state, dummy_env)

    assert pred.shape == (6, 256, 256)
