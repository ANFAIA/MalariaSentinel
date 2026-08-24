"""M3-M4 — U-Net transition surrogate.

Input: (state_t + env) = (6, 128, 128) -> Target: state_{t+1} = (2, 128, 128).
4 down/up blocks, 32-64-128-256, BN+ReLU, concat skips.
Loss: MSE + soft-Dice.
"""
from __future__ import annotations

import torch
import torch.nn as nn
import torch.nn.functional as F


class DoubleConv(nn.Module):
    def __init__(self, in_ch, out_ch):
        super().__init__()
        self.block = nn.Sequential(
            nn.Conv2d(in_ch, out_ch, 3, padding=1, bias=False),
            nn.BatchNorm2d(out_ch), nn.ReLU(inplace=True),
            nn.Conv2d(out_ch, out_ch, 3, padding=1, bias=False),
            nn.BatchNorm2d(out_ch), nn.ReLU(inplace=True),
        )

    def forward(self, x):
        return self.block(x)


class UNet(nn.Module):
    def __init__(self, in_channels=6, out_channels=2,
                 channels=(32, 64, 128, 256)):
        super().__init__()
        c = channels
        self.enc = nn.ModuleList()
        prev = in_channels
        for ch in c:
            self.enc.append(DoubleConv(prev, ch)); prev = ch
        self.pool = nn.MaxPool2d(2)
        self.bottleneck = DoubleConv(c[-1], c[-1] * 2)
        self.upconvs = nn.ModuleList()
        self.dec = nn.ModuleList()
        prev = c[-1] * 2
        for ch in reversed(c):
            self.upconvs.append(nn.ConvTranspose2d(prev, ch, 2, stride=2))
            self.dec.append(DoubleConv(ch * 2, ch))
            prev = ch
        self.head = nn.Conv2d(c[0], out_channels, 1)

    def forward(self, x):
        skips = []
        for enc in self.enc:
            x = enc(x); skips.append(x); x = self.pool(x)
        x = self.bottleneck(x)
        for upc, dec in zip(self.upconvs, self.dec):
            x = upc(x)
            skip = skips.pop()
            if x.shape[-1] != skip.shape[-1]:
                x = F.interpolate(x, size=skip.shape[-2:], mode="bilinear", align_corners=False)
            x = torch.cat([x, skip], dim=1)
            x = dec(x)
        return self.head(x)


def soft_dice_loss(pred: torch.Tensor, target: torch.Tensor, tau: float = 0.1, thresh: float = 0.01) -> torch.Tensor:
    """Soft Dice loss computed across batch and spatial dims."""
    p = torch.sigmoid((pred - thresh) / tau)
    t = torch.sigmoid((target - thresh) / tau)
    inter = (p * t).sum()
    union = p.sum() + t.sum()
    dice = (2 * inter + 1e-6) / (union + 1e-6)
    return 1.0 - dice


def combined_loss(pred: torch.Tensor, target: torch.Tensor) -> tuple[torch.Tensor, float, float]:
    """Combined MSE + Soft-Dice loss for multi-channel epidemiological state."""
    mse = F.mse_loss(pred, target)
    sd = soft_dice_loss(pred[:, :1], target[:, :1])  # focus Dice on density/sparse channel
    loss = mse + 0.5 * sd
    return loss, float(mse.item()), float(sd.item())


@torch.no_grad()
def eval_dice(pred: torch.Tensor, target: torch.Tensor, thresh: float = 0.01) -> float:
    """Evaluate hard Dice score on the primary channel (vector density)."""
    p = (pred[:, :1] > thresh).float()
    t = (target[:, :1] > thresh).float()
    inter = (p * t).sum()
    union = p.sum() + t.sum()
    return float((2 * inter + 1e-6) / (union + 1e-6))
