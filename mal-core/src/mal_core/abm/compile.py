"""Compilation helper for the C++ ABM engine (mal_abm_fast).

Enables compiling the C++ simulation engine from any directory via:
    malariasim abm --compile
    malariasim abm --compile --worktree .gitagent/worktree
"""
from __future__ import annotations

import logging
import os
import shutil
import subprocess
import sys
from pathlib import Path

log = logging.getLogger(__name__)

ABM_PKG_DIR = Path(__file__).resolve().parent


def resolve_abm_dirs(worktree: str | Path | None = None) -> tuple[Path, Path, Path]:
    """Resolve (source_dir, build_dir, bin_dir) as absolute Paths.

    If worktree is provided, looks for the ABM package inside the worktree
    (e.g. <worktree>/mal-core/src/mal_core/abm or directly at <worktree>).
    Otherwise defaults to the installed ABM_PKG_DIR.
    """
    if worktree:
        wt = Path(worktree).resolve()
        nested_abm = wt / "mal-core" / "src" / "mal_core" / "abm"
        if (nested_abm / "CMakeLists.txt").is_file():
            src_dir = nested_abm
        elif (wt / "CMakeLists.txt").is_file():
            src_dir = wt
        else:
            src_dir = nested_abm
    else:
        src_dir = ABM_PKG_DIR

    build_dir = src_dir / "build"
    bin_dir = src_dir / "bin"
    return src_dir, build_dir, bin_dir


def get_abm_dirs(worktree: str | Path | None = None) -> tuple[Path, Path, Path]:
    """Return (source_dir, build_dir, bin_dir) as absolute Paths."""
    return resolve_abm_dirs(worktree)


def _detect_nproc() -> int:
    """Detect available CPU cores for parallel compilation."""
    return os.cpu_count() or 1


def _find_macos_prefixes() -> list[str]:
    """Find Homebrew package prefixes on macOS."""
    prefixes: list[str] = []
    brew_opt = Path("/opt/homebrew/opt")
    usr_local_opt = Path("/usr/local/opt")

    for opt_root in (brew_opt, usr_local_opt):
        if not opt_root.is_dir():
            continue
        for pkg in ("gdal", "eigen", "nlohmann-json", "googletest", "cli11", "libomp"):
            pfx = opt_root / pkg
            if pfx.is_dir():
                prefixes.append(str(pfx))
    return prefixes


def compile_abm(
    *,
    worktree: str | Path | None = None,
    clean: bool = False,
    build_type: str = "Release",
    target: str | None = None,
    timeout: int = 600,
    verbose: bool = False,
) -> tuple[bool, str]:
    """Compile the C++ ABM binary (mal_abm_fast).

    Args:
        worktree: Optional path to a gawt worktree root or ABM source directory.
        clean: If True, removes the build directory before configuring.
        build_type: CMake build type ("Release", "Debug", etc.).
        target: Specific CMake target to build (default: all).
        timeout: Subprocess timeout in seconds.
        verbose: If True, enables verbose build output.

    Returns:
        (success, message_or_binary_path)
    """
    src_dir, build_dir, bin_dir = resolve_abm_dirs(worktree)

    if not (src_dir / "CMakeLists.txt").is_file():
        return False, f"CMakeLists.txt not found in {src_dir}"

    cmake_bin = shutil.which("cmake")
    if not cmake_bin:
        return False, "CMake executable not found in PATH. Please install CMake."

    if clean and build_dir.exists():
        try:
            shutil.rmtree(build_dir)
        except OSError as e:
            return False, f"Failed to clean build directory {build_dir}: {e}"

    # Configure step if CMakeCache.txt does not exist
    cache_file = build_dir / "CMakeCache.txt"
    if not cache_file.exists():
        build_dir.mkdir(parents=True, exist_ok=True)
        configure_cmd = [
            cmake_bin,
            "-S", str(src_dir),
            "-B", str(build_dir),
            f"-DCMAKE_BUILD_TYPE={build_type}",
        ]
        if shutil.which("ninja"):
            configure_cmd.extend(["-G", "Ninja"])

        if sys.platform == "darwin":
            prefixes = _find_macos_prefixes()
            if prefixes:
                configure_cmd.append(f"-DCMAKE_PREFIX_PATH={';'.join(prefixes)}")

        try:
            proc = subprocess.run(
                configure_cmd,
                capture_output=True,
                text=True,
                timeout=timeout,
                check=False,
            )
            if proc.returncode != 0:
                err_msg = proc.stderr.strip() or proc.stdout.strip()
                return False, f"CMake configuration failed (exit {proc.returncode}):\n{err_msg}"
        except subprocess.TimeoutExpired:
            return False, f"CMake configuration timed out after {timeout}s."
        except OSError as e:
            return False, f"Failed to execute cmake: {e}"

    # Build step
    jobs = str(_detect_nproc())
    build_cmd = [cmake_bin, "--build", str(build_dir)]
    if target:
        build_cmd.extend(["--target", target])
    if verbose:
        build_cmd.append("--verbose")
    build_cmd.extend(["--", f"-j{jobs}"])

    try:
        proc = subprocess.run(
            build_cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        )
        if proc.returncode != 0:
            err_msg = proc.stderr.strip() or proc.stdout.strip()
            return False, f"Compilation failed (exit {proc.returncode}):\n{err_msg}"
    except subprocess.TimeoutExpired:
        return False, f"Compilation timed out after {timeout}s."
    except OSError as e:
        return False, f"Failed to execute cmake build: {e}"

    # Locate the built binary
    candidate_bins = [
        build_dir / "src" / "mal_abm_fast",
        build_dir / "mal_abm_fast",
    ]
    built_bin: Path | None = None
    for cand in candidate_bins:
        if cand.is_file():
            built_bin = cand
            break

    if not built_bin:
        return False, f"Build succeeded but binary not found in {build_dir / 'src'}"

    # Copy binary to bin/mal_abm_fast_<platform>
    bin_dir.mkdir(parents=True, exist_ok=True)
    dest_bin = bin_dir / f"mal_abm_fast_{sys.platform}"
    try:
        shutil.copy2(built_bin, dest_bin)
        dest_bin.chmod(0o755)
    except OSError as e:
        log.warning("Could not copy binary to %s: %s", dest_bin, e)
        # Fall back to returning the built binary directly
        return True, str(built_bin)

    return True, str(dest_bin)
