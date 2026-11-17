"""Checks migrated from the retired training specification.

The spec is gone; the facts live in the code and in this file. See
docs/plans/in-process/spec-retirement-ledger.md for the row that maps
each assertion to this test.
"""
from __future__ import annotations

import inspect
from pathlib import Path

import numpy as np
import pytest
import rasterio
import torch
import xarray as xr

from mal_core.training.dataset import (
    ENV_CHANNELS,
    PATCH_SIZE,
    RolloutDataset,
    get_dataloaders,
)
from mal_core.training.model import UNet, combined_loss, eval_dice
from mal_core.training.trainer import train_unet
from mal_core.training.wrapper import UNetWrapper

TRAINING_SRC = Path(__file__).resolve().parents[1] / "src" / "mal_core" / "training"


# ---------------------------------------------------------------------------
# INV-2 / INV-3: the architecture and the patch size
# ---------------------------------------------------------------------------

def test_unet_channel_widths_are_frozen():
    model = UNet()
    widths = [m.block[0].out_channels for m in model.enc]
    assert widths == [32, 64, 128, 256]
    assert PATCH_SIZE == 128


def test_unet_forward_keeps_the_spatial_shape():
    model = UNet(in_channels=6, out_channels=2)
    out = model(torch.zeros(1, 6, 128, 128))
    assert out.shape == (1, 2, 128, 128)


# ---------------------------------------------------------------------------
# INV-4: the loss
# ---------------------------------------------------------------------------

def test_combined_loss_is_mse_plus_half_the_soft_dice():
    pred = torch.randn(2, 2, 16, 16)
    target = torch.randn(2, 2, 16, 16)
    loss, mse, dice = combined_loss(pred, target)
    assert torch.isclose(loss, torch.tensor(mse) + 0.5 * torch.tensor(dice), atol=1e-5)


def test_soft_dice_thresholds_are_the_contract_4_ones():
    """tau/thresh are 0.5/0.5 (adult counts), not the retired 0.1/0.01."""
    from mal_core.training import model as model_mod

    sig = inspect.signature(model_mod.soft_dice_loss)
    assert sig.parameters["tau"].default == 0.5
    assert sig.parameters["thresh"].default == 0.5
    sig = inspect.signature(eval_dice)
    assert sig.parameters["thresh"].default == 0.5


# ---------------------------------------------------------------------------
# INV-7 / INV-8 / INV-9: the dataset
# ---------------------------------------------------------------------------

def _write_state(path, day, h=128, w=256, bands=2):
    profile = {
        "driver": "GTiff", "height": h, "width": w, "count": bands,
        "dtype": "float32", "crs": "EPSG:4326",
        "transform": rasterio.transform.from_bounds(0, 0, 1, 1, w, h),
    }
    with rasterio.open(path, "w", **profile) as dst:
        dst.write(np.full((bands, h, w), float(day), dtype=np.float32))


@pytest.fixture
def rollout_dir(tmp_path):
    for day in (1, 2, 3):
        _write_state(tmp_path / f"ghana_abm_seed0001_day{day:03d}.tif", day)
    return tmp_path


def test_state_snapshots_are_discovered_by_the_day_infix(rollout_dir):
    ds = RolloutDataset(rollout_dir, split="train")
    assert len(ds.patches) > 0
    assert all("_day" in p["state_path"].name for p in ds.patches)


def test_pairs_are_consecutive_days(rollout_dir):
    ds = RolloutDataset(rollout_dir, split="train")
    for p in ds.patches:
        cur = int(p["state_path"].stem.split("_day")[1])
        nxt = int(p["next_path"].stem.split("_day")[1])
        assert nxt == cur + 1, "the dataset pairs consecutive days"


def test_train_and_val_split_on_the_mid_column(rollout_dir):
    train = RolloutDataset(rollout_dir, split="train")
    val = RolloutDataset(rollout_dir, split="val")
    train_cols = {p["col"] for p in train.patches}
    val_cols = {p["col"] for p in val.patches}
    assert train_cols == {0}
    assert val_cols == {128}
    assert not (train_cols & val_cols)


def test_subsampling_is_reproducible(rollout_dir):
    a = RolloutDataset(rollout_dir, split="train", subsample=0.5)
    b = RolloutDataset(rollout_dir, split="train", subsample=0.5)
    assert [p["row"] for p in a.patches] == [p["row"] for p in b.patches]
    assert [p["col"] for p in a.patches] == [p["col"] for p in b.patches]


def test_dataloaders_return_a_train_and_a_val_loader(rollout_dir):
    train_loader, val_loader = get_dataloaders(rollout_dir, batch_size=2)
    assert len(train_loader.dataset) > 0
    assert len(val_loader.dataset) > 0


# ---------------------------------------------------------------------------
# The env is loaded, not zero-filled (the retired spec called this a
# known limitation).
# ---------------------------------------------------------------------------

def test_the_env_tensor_is_loaded_into_the_input(rollout_dir):
    h, w = 128, 256
    env_path = rollout_dir / "env.nc"
    xr.Dataset({
        name: (("y", "x"), np.full((h, w), 7.0, dtype=np.float32))
        for name in ("rainfall", "air_temp_c", "jrc_persistent", "lc_built")
    }).to_netcdf(env_path)

    ds = RolloutDataset(rollout_dir, split="train", env_path=env_path)
    x, y = ds[0]
    assert x.shape == (2 + ENV_CHANNELS, PATCH_SIZE, PATCH_SIZE)
    assert y.shape == (2, PATCH_SIZE, PATCH_SIZE)
    assert float(x[2:].mean()) == pytest.approx(7.0)


# ---------------------------------------------------------------------------
# INV-10 / INV-11 / INV-12: the training loop
# ---------------------------------------------------------------------------

def test_training_defaults():
    sig = inspect.signature(train_unet)
    assert sig.parameters["epochs"].default == 50
    assert sig.parameters["batch_size"].default == 16
    assert sig.parameters["lr"].default == 1e-3


def test_the_optimizer_is_adam_and_the_device_order_is_cuda_mps_cpu():
    source = (TRAINING_SRC / "trainer.py").read_text(encoding="utf-8")
    assert "Adam(model.parameters(), lr=lr)" in source
    assert source.index("cuda.is_available()") < source.index("mps.is_available()")
    assert source.index("mps.is_available()") < source.index('device = "cpu"')


def test_the_checkpoint_cadence_and_file_names():
    source = (TRAINING_SRC / "trainer.py").read_text(encoding="utf-8")
    assert '"best_model.pt"' in source
    assert '"final_model.pt"' in source
    assert 'f"model_epoch_{epoch+1}.pt"' in source
    # every 10 epochs
    assert "epoch + 1) % 10 == 0" in source or "(epoch + 1) % 10 == 0" in source


# ---------------------------------------------------------------------------
# INV-15: the wrapper loads eagerly
# ---------------------------------------------------------------------------

def test_the_wrapper_raises_file_not_found_at_construction(tmp_path):
    with pytest.raises(FileNotFoundError):
        UNetWrapper(tmp_path / "nonexistent_model.pt")


def test_the_wrapper_is_generic_in_the_channel_count(tmp_path):
    model = UNet(in_channels=10, out_channels=6)
    ckpt = tmp_path / "model.pt"
    torch.save(model.state_dict(), ckpt)
    wrapper = UNetWrapper(ckpt)
    assert wrapper.in_channels == 10
    assert wrapper.out_channels == 6
    state = np.zeros((6, 32, 32), dtype=np.float32)
    env = np.zeros((4, 32, 32), dtype=np.float32)
    out = wrapper.predict(state, env)
    assert out.shape == (6, 32, 32)
