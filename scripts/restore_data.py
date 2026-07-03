"""Restore everything that .gitignore keeps out of the repo.

This is the canonical recovery script. From a fresh clone, run:

    uv run --with requests --with rasterio --with matplotlib --with numpy \\
        python scripts/restore_data.py

It will restore, in order:
  1. GBIF DwC-A datasets            -> data/<name>/occurrence.txt (+ .zip copies)
  2. Moua et al. 2016 paper (HAL)   -> data/moua_2016.pdf
  3. SRTM DEM tiles + map PNGs      -> terrain/srtm_maps/, terrain/srtm_guf/
  4. WorldClim + JRC env layers      -> runs/layers/  (+ runs/env_stack.npz)

Steps 3-4 require ``OPENTOPO_API_KEY`` in the environment; if absent, the script
prints the exact commands to run manually.

Step 5 (regenerating ``runs/`` model weights + result PNGs) is NOT done here —
those are reproduced by the Ghana simulation pipeline:

    uv run python mal-ghana-sim/scripts/02_suitability.py
    uv run python mal-ghana-sim/scripts/03_simulate.py
    uv run python mal-ghana-sim/scripts/05_train.py
    uv run python mal-ghana-sim/scripts/06_predict_and_map.py

Idempotent: each step skips files that already exist with non-trivial size.
Selective: pass dataset names to restore only those (e.g. ``restore_data.py guf``).
"""
from __future__ import annotations

import io
import os
import pathlib
import shutil
import subprocess
import sys
import zipfile

import requests

REPO = pathlib.Path(__file__).resolve().parents[1]
DATA = REPO / "data"
TERRAIN = REPO / "terrain"

# GBIF IPT bans nothing but HAL's bot filter serves an interstitial to browser
# UAs while allowing curl's default UA. Switch per-host.
_UA_BROWSER = {"User-Agent": "Mozilla/5.0 (MalariaSentinel restore)"}
_UA_CURL = {"User-Agent": "curl/8.7.1"}


def _ua_for(url: str) -> dict:
    return _UA_CURL if "hal.archives-ouvertes.fr" in url else _UA_BROWSER


# (subdir, zip_alias_inside_data, ipt_url)
GBIF_DATASETS = [
    {
        "name": "ghana_idit",
        "label": "Ghana IDIT — Anopheles phenotypic (larval sites)",
        "url": "https://cloud.gbif.org/africa/archive.do?r=anopheles_phenotypic",
        "zip_alias": "ghana_idit/ghana.zip",
    },
    {
        "name": "react",
        "label": "REACT IRD — Anopheles collections (Burkina Faso + Côte d'Ivoire)",
        "url": "https://ipt.gbif.fr/archive.do?r=anopheles_collections_react_project",
        "zip_alias": "react/react.zip",
    },
    {
        "name": "guf",
        "label": "Institut Pasteur Guyane — Anopheles (French Guiana)",
        "url": "https://ipt.gbif.fr/archive.do?r=pasteur_guyane_anopheles",
        "zip_alias": "pasteur_anopheles.zip",  # historical: lives at data root
    },
    {
        "name": "colombia_vl",
        "label": "Colombia — ins_mosquiteros_malaria (Timbiquí, Guapi, Sta Bárbara)",
        "url": "https://ipt.biodiversidad.co/sib/archive.do?r=ins_mosquiteros_malaria",
        "zip_alias": "colombia_vl/colombia.zip",
    },
]

# Associated paper (open access via HAL)
MOUA_URL = "https://hal.archives-ouvertes.fr/hal-01425541/file/Moua_et_al_2016_pour_diffusion.pdf"


def _get(url: str, timeout: int = 300) -> bytes:
    r = requests.get(url, timeout=timeout, headers=_ua_for(url))
    r.raise_for_status()
    return r.content


def _extract_zip(content: bytes, out_dir: pathlib.Path) -> list[str]:
    out_dir.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(io.BytesIO(content)) as zf:
        zf.extractall(out_dir)
        return zf.namelist()


def _occ_count(path: pathlib.Path) -> tuple[int, int] | None:
    """Return (rows, cols) of occurrence.txt if present."""
    if not path.exists():
        return None
    import csv

    with open(path, encoding="utf-8") as f:
        reader = csv.reader(f, delimiter="\t")
        header = next(reader, None)
        n = sum(1 for _ in reader)
    return n, len(header) if header else 0


# ---------------------------------------------------------------------------
# Step 1+2: GBIF datasets + Moua 2016 paper
# ---------------------------------------------------------------------------

def restore_dataset(ds: dict) -> None:
    name = ds["name"]
    out_dir = DATA / name
    occ_path = out_dir / "occurrence.txt"
    alias = DATA / ds["zip_alias"]
    print(f"\n=== {name} — {ds['label']} ===")

    have_occ = occ_path.exists() and occ_path.stat().st_size > 1024
    have_alias = alias.exists() and alias.stat().st_size > 1024

    if have_occ and have_alias:
        info = _occ_count(occ_path)
        rows = info[0] if info else "?"
        print(f"  already present ({rows} rows, zip alias present) -> skip")
        return

    print(f"  downloading IPT DwC-A: {ds['url']}")
    content = _get(ds["url"])
    print(f"  got {len(content) / 1e6:.2f} MB")
    if not have_occ:
        names = _extract_zip(content, out_dir)
        print(f"  extracted {len(names)} files -> {out_dir}")
    else:
        info = _occ_count(occ_path)
        print(f"  occurrence.txt already present ({info[0] if info else '?'} rows)")

    alias.parent.mkdir(parents=True, exist_ok=True)
    alias.write_bytes(content)
    print(f"  raw zip copy -> {alias}")

    info = _occ_count(occ_path)
    if info:
        print(f"  occurrence.txt: {info[0]} rows, {info[1]} cols")
    else:
        print("  WARNING: no occurrence.txt found in archive")


def restore_moua() -> None:
    out = DATA / "moua_2016.pdf"
    print("\n=== moua_2016.pdf ===")
    if out.exists() and out.stat().st_size > 1024:
        print(f"  already present ({out.stat().st_size / 1e6:.2f} MB) -> skip")
        return
    print(f"  downloading from HAL: {MOUA_URL}")
    content = _get(MOUA_URL, timeout=120)
    out.write_bytes(content)
    print(f"  saved {out.stat().st_size / 1e6:.2f} MB -> {out}")


# ---------------------------------------------------------------------------
# Step 3: SRTM terrain (delegates to terrain/download_srtm*.py)
# ---------------------------------------------------------------------------

def restore_terrain() -> None:
    print("\n=== SRTM terrain ===")
    if not os.environ.get("OPENTOPO_API_KEY"):
        print("  OPENTOPO_API_KEY not set -> skip (run manually):")
        print("    export OPENTOPO_API_KEY=<key>")
        print("    uv run --with rasterio --with matplotlib --with requests --with numpy \\")
        print("        python terrain/download_srtm.py")
        print("    uv run --with rasterio --with matplotlib --with requests --with numpy \\")
        print("        python terrain/download_srtm_guf.py")
        return

    maps = [
        TERRAIN / "download_srtm.py",
        TERRAIN / "download_srtm_guf.py",
    ]
    for script in maps:
        print(f"  running {script.relative_to(REPO)} ...")
        r = subprocess.run(
            [sys.executable, str(script)],
            cwd=str(REPO),
            env=os.environ.copy(),
            capture_output=True,
            text=True,
        )
        if r.returncode != 0:
            print(f"  FAIL ({script.name}): {r.stderr.strip()[:300]}")
        else:
            for line in r.stdout.strip().splitlines()[-3:]:
                print(f"    {line}")


# ---------------------------------------------------------------------------
# Step 4: WorldClim + JRC env layers (delegates to 01_ingest.py --download)
# ---------------------------------------------------------------------------

def restore_env_layers() -> None:
    print("\n=== WorldClim + JRC env layers ===")
    stack = REPO / "runs" / "env_stack.npz"
    if stack.exists() and stack.stat().st_size > 1024:
        print(f"  already present ({stack.stat().st_size / 1e6:.2f} MB) -> skip")
        return
    script = REPO / "mal-ghana-sim" / "scripts" / "01_ingest.py"
    print(f"  running {script.relative_to(REPO)} --download ...")
    r = subprocess.run(
        [sys.executable, str(script), "--download"],
        cwd=str(REPO),
        env=os.environ.copy(),
        capture_output=True,
        text=True,
    )
    if r.returncode != 0:
        print(f"  FAIL: {r.stderr.strip()[:300]}")
    else:
        for line in r.stdout.strip().splitlines()[-6:]:
            print(f"    {line}")


# ---------------------------------------------------------------------------

def main() -> int:
    targets = sys.argv[1:] if len(sys.argv) > 1 else None
    if targets:
        for ds in GBIF_DATASETS:
            if ds["name"] in targets:
                try:
                    restore_dataset(ds)
                except Exception as e:
                    print(f"  ERROR: {e}")
        if "moua" in targets:
            restore_moua()
        if "terrain" in targets:
            restore_terrain()
        if "env" in targets:
            restore_env_layers()
        return 0

    for ds in GBIF_DATASETS:
        try:
            restore_dataset(ds)
        except Exception as e:
            print(f"  ERROR: {e}")
    restore_moua()
    restore_terrain()
    restore_env_layers()

    print("\n--- next: regenerate runs/ (model weights + result PNGs) ---")
    print("  uv run python mal-ghana-sim/scripts/02_suitability.py")
    print("  uv run python mal-ghana-sim/scripts/03_simulate.py")
    print("  uv run python mal-ghana-sim/scripts/05_train.py")
    print("  uv run python mal-ghana-sim/scripts/06_predict_and_map.py")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())