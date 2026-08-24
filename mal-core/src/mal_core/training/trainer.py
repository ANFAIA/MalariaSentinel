"""M3-M4 & M7.4 — U-Net training loop for ABM transmission surrogates."""
from __future__ import annotations

import yaml
from pathlib import Path

import torch
from torch.optim import Adam

from .model import UNet, combined_loss, eval_dice
from .dataset import get_dataloaders


def train_unet(
    run_dir: str | Path,
    output_dir: str | Path,
    epochs: int = 50,
    batch_size: int = 16,
    lr: float = 1e-3,
    device: str | None = None,
    subsample: float = 1.0,
    preload: bool = False,
    include_transmission: bool = True,
    env_path: str | Path | None = None,
) -> float:
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    if device is None:
        if torch.cuda.is_available():
            device = "cuda"
        elif torch.backends.mps.is_available():
            device = "mps"
        else:
            device = "cpu"

    train_loader, val_loader = get_dataloaders(
        run_dir,
        batch_size=batch_size,
        subsample=subsample,
        preload=preload,
        include_transmission=include_transmission,
        env_path=env_path,
    )

    if len(train_loader.dataset) == 0:
        raise ValueError(f"Train dataset in {run_dir} is empty. Check snapshot file paths.")

    # Determine input / target channels from a sample
    sample_x, sample_y = train_loader.dataset[0]
    in_channels = sample_x.shape[0]
    out_channels = sample_y.shape[0]

    model = UNet(in_channels=in_channels, out_channels=out_channels).to(device)
    optimizer = Adam(model.parameters(), lr=lr)

    best_dice = 0.0
    for epoch in range(epochs):
        model.train()
        train_loss = 0.0
        for x, y in train_loader:
            x, y = x.to(device), y.to(device)
            pred = model(x)
            loss, mse_val, dice_val = combined_loss(pred, y)

            optimizer.zero_grad()
            loss.backward()
            optimizer.step()

            train_loss += loss.item()

        train_loss /= max(1, len(train_loader))

        model.eval()
        val_dice = 0.0
        if len(val_loader) > 0:
            with torch.no_grad():
                for x, y in val_loader:
                    x, y = x.to(device), y.to(device)
                    pred = model(x)
                    val_dice += eval_dice(pred, y)
            val_dice /= len(val_loader)

        print(f"Epoch {epoch+1}/{epochs} - train_loss: {train_loss:.4f} - val_dice: {val_dice:.4f}")

        if val_dice >= best_dice or epoch == 0:
            best_dice = val_dice
            torch.save(model.state_dict(), output_dir / "best_model.pt")

        if (epoch + 1) % 10 == 0:
            torch.save(model.state_dict(), output_dir / f"model_epoch_{epoch+1}.pt")

    torch.save(model.state_dict(), output_dir / "final_model.pt")

    # Generate model.yaml manifest for ModelRegistry compatibility
    model_manifest = {
        "name": output_dir.name or "unet_surrogate",
        "version": "1.0",
        "contract_version": "1.1",
        "in_channels": in_channels,
        "out_channels": out_channels,
        "checkpoint": "best_model.pt",
        "description": f"U-Net surrogate model trained on {run_dir} (in_ch={in_channels}, out_ch={out_channels})",
    }
    with open(output_dir / "model.yaml", "w") as f:
        yaml.safe_dump(model_manifest, f)

    print(f"Training complete. Best val_dice: {best_dice:.4f}. Manifest saved -> {output_dir / 'model.yaml'}")
    return best_dice
