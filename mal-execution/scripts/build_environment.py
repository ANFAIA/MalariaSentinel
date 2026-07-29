#!/usr/bin/env python3
"""Build environmental tensors for an AOI. Thin wrapper over mal_core.ingest.env."""
from __future__ import annotations

import argparse
import pathlib
import sys


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(
        prog="build_environment",
        description="Build the env tensor + habitat patches for an AOI + month.",
    )
    parser.add_argument("--aoi", default="ghana")
    parser.add_argument("--bbox", default=None)
    parser.add_argument("--crs", default="EPSG:4326")
    parser.add_argument("--resolution-m", type=int, default=1000)
    parser.add_argument("--year", type=int, required=True)
    parser.add_argument("--month", type=int, required=True, choices=range(1, 13))
    parser.add_argument("--output-dir", type=pathlib.Path, required=True)
    parser.add_argument("--scale", default="regional")
    parser.add_argument("--name", default=None)
    parser.add_argument("--twi-threshold", type=float, default=8.0)
    parser.add_argument("--skip-era5", action="store_true")
    parser.add_argument("--skip-modis", action="store_true")
    parser.add_argument("--skip-jrc-gsw", action="store_true")
    parser.add_argument("--skip-worldcover", action="store_true")
    parser.add_argument("--format", dest="output_format", default="tif", choices=["tif", "nc"])
    args = parser.parse_args(argv)

    from mal_core.ingest.env import build_env_tensor
    from mal_commonlib.aoi import AOI, Scale

    # Resolve AOI
    if args.bbox:
        parts = [p.strip() for p in args.bbox.split(",")]
        w, s, e, n = (float(x) for x in parts)
        aoi_obj = AOI.from_bbox(w, s, e, n, args.crs, args.aoi or "custom", args.resolution_m)
    elif args.aoi:
        from mal_core.ingest._shared import resolve_aoi
        aoi_obj = resolve_aoi(args.aoi, None, args.crs, args.resolution_m, Scale(args.scale), args.name)
    else:
        parser.error("either --aoi or --bbox is required")
        return

    result = build_env_tensor(
        aoi=aoi_obj,
        year=args.year,
        month=args.month,
        output_dir=args.output_dir,
        scale=args.scale,
        skip_era5=args.skip_era5,
        skip_modis=args.skip_modis,
        skip_jrc_gsw=args.skip_jrc_gsw or args.skip_worldcover,
        output_format=args.output_format,
        twi_threshold=args.twi_threshold,
    )
    print(f"build_env: {result}")


if __name__ == "__main__":
    main()
