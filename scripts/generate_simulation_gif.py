"""Generate animation GIF from ABM simulation snapshots."""
from __future__ import annotations
import numpy as np
import rasterio
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from pathlib import Path
from PIL import Image
import io

RUN_DIR = Path(__file__).resolve().parent.parent / "runs" / "ghana"
OUTPUT = Path(__file__).resolve().parent.parent / "runs" / "ghana_simulation.gif"


def load_snapshot(path: Path) -> tuple[np.ndarray, np.ndarray]:
    with rasterio.open(path) as ds:
        b1 = ds.read(1)  # adult_occupancy
        b2 = ds.read(2)  # host_seeking_pressure
    return b1, b2


def make_frame(b1: np.ndarray, b2: np.ndarray, day: int) -> Image.Image:
    fig, axes = plt.subplots(1, 2, figsize=(12, 5))

    im1 = axes[0].imshow(b1, cmap="YlOrRd", vmin=0, vmax=max(b1.max(), 0.01))
    axes[0].set_title(f"Adult Occupancy (day {day})")
    plt.colorbar(im1, ax=axes[0], fraction=0.046)

    im2 = axes[1].imshow(b2, cmap="YlOrRd", vmin=0, vmax=max(b2.max(), 0.01))
    axes[1].set_title(f"Host-Seeking Pressure (day {day})")
    plt.colorbar(im2, ax=axes[1], fraction=0.046)

    fig.tight_layout()
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=100)
    plt.close(fig)
    buf.seek(0)
    return Image.open(buf)


def main():
    tifs = sorted(RUN_DIR.glob("*_day*.tif"))
    if not tifs:
        print("No snapshot TIFs found in", RUN_DIR)
        return

    print(f"Found {len(tifs)} snapshots")
    frames = []
    for tif in tifs:
        # Extract day number
        name = tif.stem
        day_str = name.split("_day")[-1].split("_")[0]
        try:
            day = int(day_str)
        except ValueError:
            day = 0

        b1, b2 = load_snapshot(tif)
        frame = make_frame(b1, b2, day)
        frames.append(frame)
        print(f"  day {day:3d}: occ={b1.sum():.0f} seek={b2.sum():.0f}")

    if not frames:
        print("No frames generated")
        return

    # Save GIF
    frames[0].save(
        OUTPUT,
        save_all=True,
        append_images=frames[1:],
        duration=300,  # ms per frame
        loop=0,
    )
    print(f"\nGIF saved → {OUTPUT} ({len(frames)} frames)")


if __name__ == "__main__":
    main()
