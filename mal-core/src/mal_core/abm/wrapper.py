"""CppAbmWrapper — thin Python wrapper around the compiled C++ ABM binary."""
from __future__ import annotations
import logging
import re
import subprocess
import sys
from pathlib import Path
from typing import Any

log = logging.getLogger(__name__)

class CppAbmWrapper:
    def __init__(
        self,
        binary_path: Path | None = None,
        worktree: str | Path | None = None,
    ):
        self.worktree = Path(worktree).resolve() if worktree else None
        self.binary = binary_path or self._resolve_binary()
        self._flags_schema: dict[str, dict[str, Any]] | None = None

    def _resolve_binary(self) -> Path:
        candidate_dirs: list[Path] = []
        worktree = getattr(self, "worktree", None)
        if worktree:
            wt_abm = worktree / "mal-core" / "src" / "mal_core" / "abm"
            if wt_abm.is_dir():
                candidate_dirs.append(wt_abm)
            elif (worktree / "CMakeLists.txt").is_file():
                candidate_dirs.append(worktree)
            else:
                candidate_dirs.append(wt_abm)
        pkg_dir = Path(__file__).parent
        candidate_dirs.append(pkg_dir)

        for base in candidate_dirs:
            bin_path = base / "bin" / f"mal_abm_fast_{sys.platform}"
            if bin_path.exists():
                return bin_path
            build_path = base / "build" / "src" / "mal_abm_fast"
            if build_path.exists():
                return build_path

        err_hint = "malariasim abm --compile"
        if worktree:
            err_hint += f" --worktree {worktree}"
        raise FileNotFoundError(
            f"ABM binary not found. Run: {err_hint} (or bash {pkg_dir / 'build.sh'})"
        )

    def _introspect_flags(self) -> dict[str, dict[str, Any]]:
        try:
            result = subprocess.run([str(self.binary), "--help"], capture_output=True, text=True)
            output = result.stdout + result.stderr
        except (subprocess.TimeoutExpired, FileNotFoundError):
            return {}
        flags: dict[str, dict[str, Any]] = {}
        for match in re.finditer(r"--([\w-]+)\s+(?:<(\w+)>)?\s*(.*)", output):
            name = match.group(1).replace("-", "_")
            ftype = match.group(2) or "bool"
            desc = match.group(3).strip()
            tmap = {"int": int, "float": float, "str": str, "string": str, "bool": bool}
            flags[name] = {"type": tmap.get(ftype, str), "default": None, "help": desc}
        return flags

    def run(self, _timeout: int | None = None, **flags) -> dict[str, Any]:
        if self._flags_schema is None:
            self._flags_schema = self._introspect_flags()
        cmd = [str(self.binary), "run"]
        for name, value in flags.items():
            if value is None:
                continue
            cli = f"--{name.replace('_', '-')}"
            if isinstance(value, bool):
                if value:
                    cmd.append(cli)
            else:
                cmd.extend([cli, str(value)])
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=_timeout, check=False)
        return {"stdout": result.stdout, "stderr": result.stderr, "returncode": result.returncode}

    def get_flags_schema(self) -> dict[str, dict[str, Any]]:
        if self._flags_schema is None:
            self._flags_schema = self._introspect_flags()
        return self._flags_schema


def run_abm_from_manifest(
    aoi: str,
    year: int = 2024,
    month: int = 1,
    days: int = 30,
    seed: int = 1,
    n_rollouts: int = 1,
    output_dir: str | Path | None = None,
    data_root: str | Path | None = None,
    timeout: int | None = None,
    worktree: str | Path | None = None,
    **kwargs,
) -> dict[str, Any]:
    """Run ABM using manifest to resolve data paths.

    Reads manifest, validates completeness, resolves paths,
    then calls the C++ binary via CppAbmWrapper.
    """
    from mal_core.download.manifest import read_manifest, validate_completeness

    data_root = Path(data_root) if data_root else None
    complete = validate_completeness(aoi, data_root=data_root)
    if complete:  # non-empty list = missing files
        raise FileNotFoundError(
            f"Missing required ABM data for AOI '{aoi}': {complete}. "
            f"Run: malariasim download --aoi {aoi} --all"
        )

    manifest = read_manifest(aoi, data_root)
    data_dir = (data_root or Path("data")) / aoi

    env_path = None
    habitat_path = None
    hosts_path = None
    wind_path = None
    mobility_day_path = None
    mobility_night_path = None
    livestock_mobility_path = None

    for ds_name, ds in manifest.get("datasets", {}).items():
        files = ds.get("files", {})
        if ds_name == "env":
            fname = files.get("env") or files.get(str(year)) or next(iter(files.values()), None)
            if fname:
                env_path = str(data_dir / fname)
        elif ds_name == "habitat":
            fname = next(iter(files.values()), None)
            if fname:
                habitat_path = str(data_dir / fname)
        elif ds_name == "host_static":
            fname = next(iter(files.values()), None)
            if fname:
                hosts_path = str(data_dir / fname)
        elif ds_name == "wind":
            fname = files.get("wind") or files.get(str(year)) or next(iter(files.values()), None)
            if fname:
                wind_path = str(data_dir / fname)
        elif ds_name == "mobility_day":
            fname = files.get("mobility_day")
            if fname:
                mobility_day_path = str(data_dir / fname)
        elif ds_name == "mobility_night":
            fname = files.get("mobility_night")
            if fname:
                mobility_night_path = str(data_dir / fname)
        elif ds_name == "livestock_mobility":
            fname = files.get("livestock_mobility")
            if fname:
                livestock_mobility_path = str(data_dir / fname)

    if not env_path:
        raise FileNotFoundError(f"No env data found for AOI '{aoi}', year {year}")
    if not habitat_path:
        raise FileNotFoundError(f"No habitat data found for AOI '{aoi}'")

    if output_dir is None:
        output_dir = Path("runs") / aoi
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / f"{aoi}_abm_seed{seed:04d}.tif"

    flags: dict[str, Any] = {
        "aoi": aoi,
        "env": env_path,
        "habitat": habitat_path,
        "year": year,
        "month": month,
        "days": days,
        "seed": seed,
        "n_rollouts": n_rollouts,
        "snapshot_every": kwargs.pop("snapshot_every", 1),  # default daily
        "output": str(output_path),
    }
    cohort_log = kwargs.pop("cohort_log", None)
    if cohort_log is None:
        cohort_log = output_dir / f"{aoi}_abm_seed{seed:04d}_cohort.json"
    flags["emit_cohort_log"] = str(cohort_log)

    if kwargs.get("enable_transmission") or kwargs.get("enable-transmission"):
        trans_log = kwargs.pop("emit_transmission_log", None) or kwargs.pop("transmission_log", None)
        if trans_log is None:
            trans_log = output_dir / f"{aoi}_abm_seed{seed:04d}_transmission_daily.json"
        flags["emit_transmission_log"] = str(trans_log)

    if hosts_path:
        flags["hosts"] = hosts_path
    if mobility_day_path:
        flags["human_mobility_day"] = mobility_day_path
    if mobility_night_path:
        flags["human_mobility_night"] = mobility_night_path
    if livestock_mobility_path:
        flags["livestock_mobility"] = livestock_mobility_path
    if wind_path:
        flags["wind_field"] = wind_path
    flags.update(kwargs)

    log.info("Running ABM for %s (year=%d, seed=%d)", aoi, year, seed)
    wrapper = CppAbmWrapper(worktree=worktree)
    result = wrapper.run(**flags, _timeout=timeout)

    return {"output_path": str(output_path), **result}
