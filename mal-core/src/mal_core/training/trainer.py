"""M3-M4 — U-Net training loop."""
from __future__ import annotations

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
):
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    if device is None:
        if torch.cuda.is_available():
            device = "cuda"
        elif torch.backends.mps.is_available():
            device = "mps"
        else:
            device = "cpu"

    train_loader, val_loader = get_dataloaders(run_dir, batch_size=batch_size, subsample=subsample, preload=preload)

    model = UNet().to(device)
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

        train_loss /= len(train_loader)

        model.eval()
        val_dice = 0.0
        with torch.no_grad():
            for x, y in val_loader:
                x, y = x.to(device), y.to(device)
                pred = model(x)
                val_dice += eval_dice(pred, y)

        val_dice /= len(val_loader)

        print(f"Epoch {epoch+1}/{epochs} - train_loss: {train_loss:.4f} - val_dice: {val_dice:.4f}")

        if val_dice > best_dice:
            best_dice = val_dice
            torch.save(model.state_dict(), output_dir / "best_model.pt")

        if (epoch + 1) % 10 == 0:
            torch.save(model.state_dict(), output_dir / f"model_epoch_{epoch+1}.pt")

    torch.save(model.state_dict(), output_dir / "final_model.pt")
    print(f"Training complete. Best val_dice: {best_dice:.4f}")
    return best_dice
