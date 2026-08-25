#!/usr/bin/env python3
"""Build host density NetCDF for the ABM. Thin wrapper over mal_core.ingest.hosts."""
from __future__ import annotations

import argparse
import pathlib


def main() -> None:
    p = argparse.ArgumentParser(description="Build host density NetCDF for the ABM.")
    p.add_argument("--output-dir", type=pathlib.Path, default=pathlib.Path("hosts"))
    p.add_argument("--aoi", type=str, default=None)
    p.add_argument("--bbox", type=str, default=None)
    p.add_argument("--worldpop-year", type=int, default=2019)
    p.add_argument("--cache-dir", type=pathlib.Path, default=None)
    p.add_argument("--skip-buildings", action="store_true")
    p.add_argument("--skip-wildlife", action="store_true")
    args = p.parse_args()

    from mal_core.ingest.hosts import build_host_dataset
    from mal_commonlib.aoi import AOI

    if args.bbox:
        parts = [p.strip() for p in args.bbox.split(",")]
        w, s, e, n = (float(x) for x in parts)
        aoi_obj = AOI.from_bbox(w, s, e, n, "EPSG:4326", "custom", 1000)
    elif args.aoi:
        aoi_obj = AOI.from_slug(args.aoi)
    else:
        aoi_obj = AOI.from_slug("ghana")

    result = build_host_dataset(
        aoi=aoi_obj,
        output_dir=args.output_dir,
        worldpop_year=args.worldpop_year,
        cache_dir=args.cache_dir,
        skip_buildings=args.skip_buildings,
        skip_wildlife=args.skip_wildlife,
    )
    print(f"build_hosts: {result}")


if __name__ == "__main__":
    main()
