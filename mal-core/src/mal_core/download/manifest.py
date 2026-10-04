"""Auto-managed AOI manifest — updates data/<aoi>/manifest.json after downloads.

Single schema: the v3.1 datasets block (per docs/specs/data/spec.md §5.2).
Writes always produce v3.1. (The legacy v1 flat-files migration was removed
on 2026-09-27 — no v1 manifests exist on disk.)
"""

from __future__ import annotations
import json
import logging
from pathlib import Path

log = logging.getLogger(__name__)


def _find_repo_root() -> Path:
    """Walk up from this file to find the repo root (has opencode.json or .git)."""
    p = Path(__file__).resolve().parent
    for _ in range(10):
        if (p / "opencode.json").exists() or (p / ".git").exists():
            return p
        p = p.parent
    return Path(__file__).resolve().parents[4]


_REPO_ROOT = _find_repo_root()
DATA_ROOT = _REPO_ROOT / "data"


def read_manifest(aoi: str, data_root: Path | None = None) -> dict:
    """Read the v3.1 datasets-block manifest. Empty skeleton if file missing."""
    path = (data_root or DATA_ROOT) / aoi / "manifest.json"
    if not path.exists():
        return {"aoi": aoi, "datasets": {}, "expected_files": []}
    with open(path) as f:
        return json.load(f)


def resolve_dataset_file(
    aoi: str,
    dataset_name: str,
    *,
    year: int | str | None = None,
    data_dir: Path | None = None,
    data_root: Path | None = None,
    manifest: dict | None = None,
    strict: bool = True,
) -> Path | None:
    """Resolve a dataset's file path from the manifest — the single source of truth.

    Selection inside the entry's ``files`` dict:
      1. ``files[str(year)]`` when ``year`` is given and present (per-year
         datasets: era5_water_temp, modis_ndvi, env...);
      2. ``files[dataset_name]`` (single-file datasets where the key repeats
         the dataset name: chirps_rainfall_daily, host_static...);
      3. first declared file, otherwise.

    Resolution semantics:

    * No manifest entry for ``dataset_name`` → ``None``. The caller should
      fall back to conventional-filename discovery (legacy tmp dirs,
      sandboxes, downloads not yet registered).
    * Entry exists but the declared file is missing on disk →
      ``FileNotFoundError`` (``strict=True``, default). A stale manifest is
      an error, never a silent fallback. ``strict=False`` returns the
      missing path instead (attempted writes / diagnostics).

    Args:
        aoi: AOI slug.
        dataset_name: manifest datasets key (e.g. ``"host_static"``).
        year: optional per-year file key.
        data_dir: directory holding the actual files. Defaults to
            ``(data_root or DATA_ROOT) / aoi``.
        data_root: parent of the AOI dir (default ``DATA_ROOT``); only used
            to locate the manifest and the default ``data_dir``.
        manifest: optional pre-loaded manifest dict (avoids re-reading; also
            lets tmp-dir tests resolve against a locally written manifest).
    """
    if manifest is None:
        manifest = read_manifest(aoi, data_root)
    entry = manifest.get("datasets", {}).get(dataset_name)
    if entry is None:
        return None
    files: dict = entry.get("files", {})
    fname: str | None = None
    if year is not None:
        if str(year) in files:
            fname = files[str(year)]
        elif any(str(k).isdigit() for k in files):
            # Per-year keyed entry without the requested year: selecting
            # another year's file silently would be a data-integrity bug.
            raise FileNotFoundError(
                f"Manifest entry '{dataset_name}' is per-year keyed "
                f"{sorted(files)} but declares nothing for {year}. "
                f"Download year {year} or fix the manifest."
            )
    if not fname:
        fname = files.get(dataset_name) or (
            next(iter(files.values()), None) if files else None
        )
    if not fname:
        return None
    if data_dir is None:
        data_dir = (data_root or DATA_ROOT) / aoi
    path = Path(data_dir) / fname
    if strict and not path.exists():
        raise FileNotFoundError(
            f"Manifest entry '{dataset_name}' exists but declares a file that "
            f"is missing on disk: {path}. Re-download it "
            f"(malariasim download --aoi {aoi} ...), or fix "
            f"{Path(data_dir) / 'manifest.json'}."
        )
    return path


def update_dataset(
    aoi: str,
    dataset_name: str,
    year: int | str | None,
    filename: str,
    *,
    type: str = "time-series",
    required_for_abm: bool = False,
    variables: list[str] | None = None,
    format: str | None = None,
    period: dict[str, str] | None = None,
    license: str | None = None,
    attribution: str | None = None,
    data_root: Path | None = None,
) -> Path:
    """Update a specific dataset entry in the manifest.

    Args:
        aoi: AOI slug.
        dataset_name: dataset key (e.g. "chirps_rainfall_daily").
        year: year for per-year entries, or None for multi-year NC.
        filename: output filename.
        type: "static" | "time-series".
        required_for_abm: whether this dataset is required for ABM runs.
        variables: list of variable names in the file.
        format: file format ("tif" | "nc" | "gpkg" | "csr").
        period: for multi-year NC, {"start": "YYYY-MM-DD", "end": "YYYY-MM-DD"}.
        license: upstream license id(s) from
            ``mal_commonlib.data.licenses.KNOWN_LICENSES`` ('+'-joined for
            derived products). None leaves the existing value untouched.
        attribution: literal credit line (docs/licenses.md). None leaves
            the existing value untouched.
    """
    root = data_root or DATA_ROOT
    path = root / aoi / "manifest.json"
    manifest = read_manifest(aoi, root)
    if dataset_name not in manifest.get("datasets", {}):
        manifest.setdefault("datasets", {})[dataset_name] = {
            "type": type,
            "format": format or filename.rsplit(".", 1)[-1],
            "required_for_abm": required_for_abm,
            "files": {},
        }
    ds = manifest["datasets"][dataset_name]
    # Update metadata fields
    ds["type"] = type
    if format:
        ds["format"] = format
    ds["required_for_abm"] = required_for_abm
    if variables:
        ds["variables"] = variables
    if period:
        ds["period"] = period
    if license:
        ds["license"] = license
    if attribution:
        ds["attribution"] = attribution

    if year:
        ds.setdefault("files", {})[str(year)] = filename
    else:
        ds.setdefault("files", {})[dataset_name] = filename

    all_files = []
    for d in manifest.get("datasets", {}).values():
        all_files.extend(d.get("files", {}).values())
    manifest["expected_files"] = sorted(set(all_files))
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w") as f:
        json.dump(manifest, f, indent=2)
    log.info("Manifest updated: %s[%s] = %s", aoi, dataset_name, filename)
    return path


def validate_completeness(
    aoi: str, *, years: list[int] | None = None, data_root: Path | None = None
) -> list[str]:
    """Return list of missing expected files. Empty = complete.

    For daily NC entries with a ``period`` field, checks that the
    period covers the requested years rather than individual file existence.
    """
    root = data_root or DATA_ROOT
    manifest = read_manifest(aoi, root)
    data_dir = root / aoi
    missing = []

    for ds_name, ds in manifest.get("datasets", {}).items():
        period = ds.get("period")
        if period and years:
            # Daily NC entry: check period covers requested years
            period_start = period.get("start", "")
            period_end = period.get("end", "")
            if period_start and period_end:
                start_year = int(period_start[:4])
                end_year = int(period_end[:4])
                for y in years:
                    if y < start_year or y > end_year:
                        missing.append(
                            f"{ds_name}: period {period_start}..{period_end} "
                            f"does not cover year {y}"
                        )
                # Also check that at least one file exists
                files = ds.get("files", {})
                if not any((data_dir / f).exists() for f in files.values()):
                    for f in files.values():
                        if not (data_dir / f).exists():
                            missing.append(f)
            else:
                # Incomplete period metadata
                for f in ds.get("files", {}).values():
                    if not (data_dir / f).exists():
                        missing.append(f)
        else:
            # Standard per-file check
            for f in ds.get("files", {}).values():
                if not (data_dir / f).exists():
                    missing.append(f)

    # Also check the top-level expected_files union
    for f in manifest.get("expected_files", []):
        if f not in missing and not (data_dir / f).exists():
            missing.append(f)

    return sorted(set(missing))


def get_dataset_files(
    aoi: str, dataset_name: str, year: int | str | None = None
) -> list[Path]:
    """Get file paths for a dataset, optionally filtered by year."""
    manifest = read_manifest(aoi)
    ds = manifest.get("datasets", {}).get(dataset_name)
    if not ds:
        return []
    data_dir = DATA_ROOT / aoi
    if year:
        fname = ds.get("files", {}).get(str(year))
        return [data_dir / fname] if fname else []
    return [data_dir / f for f in ds.get("files", {}).values()]
