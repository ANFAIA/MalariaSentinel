"""Ingest stage — builds env tensor for an AOI. Thin wrapper over mal_core.ingest.env."""
from __future__ import annotations
from pathlib import Path


def build_environment(
    aoi: str = "ghana",
    year: int = 2024,
    month: int = 6,
    output_dir: str | Path | None = None,
    scale: str = "regional",
    **kwargs,
) -> dict:
    """Build the env tensor via the library function (no subprocess)."""
    from .env import build_env_tensor
    from mal_commonlib.aoi import AOI

    aoi_obj = AOI.from_slug(aoi) if isinstance(aoi, str) else aoi
    return build_env_tensor(
        aoi=aoi_obj,
        year=year,
        month=month,
        output_dir=Path(output_dir) if output_dir else Path("runs/ingest"),
        scale=scale,
        **kwargs,
    )
