"""Stage 5 — U-Net transition surrogate + loss.

Input: (D_t_norm + env channels) -> Target: D_{t+T}_norm.
Small U-Net (4 down/up blocks, 32-64-128-256, BN+ReLU, concat skips).
Loss: MSE + soft-Dice (differentiable; hard threshold only for eval).
"""
from __future__ import annotations

import torch
import torch.nn as nn
import torch.nn.functional as F

from . import config as C


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
    def __init__(self, in_channels=5, channels=C.UNET_CHANNELS):
        super().__init__()
        c = channels  # (32, 64, 128, 256)
        self.enc = nn.ModuleList()
        prev = in_channels
        for ch in c:
            self.enc.append(DoubleConv(prev, ch)); prev = ch
        self.pool = nn.MaxPool2d(2)
        self.bottleneck = DoubleConv(c[-1], c[-1] * 2)
        self.upconvs = nn.ModuleList()
        self.dec = nn.ModuleList()
        prev = c[-1] * 2
        for ch in reversed(c):                      # 256, 128, 64, 32
            self.upconvs.append(nn.ConvTranspose2d(prev, ch, 2, stride=2))
            self.dec.append(DoubleConv(ch * 2, ch))  # upsampled ch + skip ch -> ch
            prev = ch
        self.head = nn.Conv2d(c[0], 1, 1)

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
        return torch.relu(self.head(x))  # density is non-negative


def soft_dice_loss(pred, target, tau=C.LOSS_DICE_TAU, thresh=C.PRESENCE_THRESH):
    """Differentiable Dice, BATCH-AGGREGATED (sum inter / sum union over the whole batch).

    Per-sample Dice would give 1.0 on empty patches via the epsilon and reward the model
    for predicting nothing on the (many) empty patches in sparse spread data. Aggregating
    over the batch makes empty patches contribute zero to both inter and union -> no free reward.
    """
    p = torch.sigmoid((pred - thresh) / tau)
    t = torch.sigmoid((target - thresh) / tau)
    inter = (p * t).sum()
    union = p.sum() + t.sum()
    dice = (2 * inter + 1e-6) / (union + 1e-6)
    return 1 - dice


def combined_loss(pred, target):
    mse = F.mse_loss(pred, target)
    sd = soft_dice_loss(pred, target)
    return mse + C.LOSS_DICE_WEIGHT * sd, mse.item(), sd.item()


@torch.no_grad()
def eval_dice(pred, target, thresh=C.PRESENCE_THRESH):
    """Batch-aggregated front-overlap Dice (honest: empty patches don't inflate the score)."""
    p = (pred > thresh).float()
    t = (target > thresh).float()
    inter = (p * t).sum()
    union = p.sum() + t.sum()
    return float((2 * inter + 1e-6) / (union + 1e-6))
