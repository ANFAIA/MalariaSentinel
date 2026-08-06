#!/usr/bin/env python3
"""Build mobility OD matrices. Thin wrapper over mal_core.ingest.mobility."""
from __future__ import annotations

import argparse
import pathlib


def main() -> None:
    p = argparse.ArgumentParser(description="Build gravity-model mobility OD matrices.")
    p.add_argument("--hosts", type=pathlib.Path, required=True, help="Path to host_static.nc")
    p.add_argument("--output-dir", type=pathlib.Path, default=None)
    p.add_argument("--cell-size-km", type=float, default=1.0)
    p.add_argument("--beta-day", type=float, default=0.05)
    p.add_argument("--beta-night", type=float, default=0.5)
    p.add_argument("--beta-livestock", type=float, default=0.1)
    p.add_argument("--max-distance-km", type=float, default=50.0)
    p.add_argument("--sparsity-threshold", type=float, default=5e-4)
    args = p.parse_args()

    from mal_core.ingest.mobility import build_mobility_dataset
    from mal_commonlib.aoi import AOI

    # Resolve AOI from host file metadata
    import xarray as xr
    ds = xr.open_dataset(str(args.hosts), engine="netcdf4")
    # Assume the AOI slug is derived from the file path or defaults to ghana
    ds.close()

    out_dir = args.output_dir or args.hosts.parent
    result = build_mobility_dataset(
        aoi_slug="ghana",  # TODO: resolve from manifest
        hosts_path=args.hosts,
        output_dir=out_dir,
        cell_size_km=args.cell_size_km,
        beta_day=args.beta_day,
        beta_night=args.beta_night,
        beta_livestock=args.beta_livestock,
        max_distance_km=args.max_distance_km,
    )
    print(f"build_mobility: {result}")


if __name__ == "__main__":
    main()
