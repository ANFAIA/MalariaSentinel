"""Shared pytest fixtures for the M-perf F1.e parity test.

Locates the C++ ``mal_abm_fast`` binary (building it on demand if it
is not present) and provides a session-scoped temporary directory
for synthetic env COGs / habitat gpkgs. The C++ engine's BTPE-lite
streams and the Python ABM's numpy.BTPE streams sample from the
same Binomial(n, p) distribution but with different random
variates, so the parity test asserts **per-band means** (not
per-pixel equality) and tolerates 1e-3 per-band mean difference.
"""
from __future__ import annotations

import os
import pathlib
import shutil
import subprocess
import sys
from typing import Iterator

import pytest


# ---------------------------------------------------------------------------
# Repo layout helpers
# ---------------------------------------------------------------------------

# This conftest is at mal-ghana-sim/tests/conftest.py — go up two levels
# to reach the monorepo root, where mal-abm-fast/ lives.
THIS_DIR = pathlib.Path(__file__).resolve().parent
REPO_ROOT = THIS_DIR.parent.parent


def _find_cpp_binary() -> pathlib.Path | None:
    """Search the well-known locations for the mal_abm_fast binary.

    The CMake build emits the binary at ``<build>/src/mal_abm_fast``
    (not ``<build>/mal_abm_fast``) because the top-level CMakeLists
    guards ``add_subdirectory(src)`` — the executable target lives
    under the ``src/`` subdir. Search both layouts so a custom build
    directory also works.
    """
    candidates = [
        REPO_ROOT / "mal-abm-fast" / "build" / "src" / "mal_abm_fast",
        REPO_ROOT / "mal-abm-fast" / "build" / "mal_abm_fast",
    ]
    for c in candidates:
        if c.is_file() and os.access(c, os.X_OK):
            return c
    return None


def _build_cpp_binary() -> pathlib.Path:
    """Configure + build the C++ engine from source.

    Uses ``cmake -B build -S mal-abm-fast`` and
    ``cmake --build build`` (no extra ``-DCMAKE_PREFIX_PATH`` — the
    external deps (Eigen, GDAL, CLI11, nlohmann_json, GTest) are
    installed under ``/opt/homebrew`` on this machine and CMake's
    ``find_package`` locates them automatically).

    If the build fails the test session is hard-failed with the
    captured cmake output so the user can debug from the message
    rather than a bare "binary missing" later.
    """
    print(
        "\n[conftest] C++ binary not found; configuring + building "
        "mal-abm-fast with cmake (this is a one-off per worktree)...",
        file=sys.stderr,
    )
    build_dir = REPO_ROOT / "mal-abm-fast" / "build"
    src_dir = REPO_ROOT / "mal-abm-fast"
    configure = subprocess.run(
        ["cmake", "-B", str(build_dir), "-S", str(src_dir),
         "-DCMAKE_BUILD_TYPE=Release"],
        cwd=str(REPO_ROOT),
        capture_output=True, text=True,
    )
    if configure.returncode != 0:
        raise RuntimeError(
            f"cmake configure failed (exit {configure.returncode}).\n"
            f"--- stdout ---\n{configure.stdout}\n"
            f"--- stderr ---\n{configure.stderr}"
        )
    build = subprocess.run(
        ["cmake", "--build", str(build_dir), "-j", "4"],
        cwd=str(REPO_ROOT),
        capture_output=True, text=True,
    )
    if build.returncode != 0:
        raise RuntimeError(
            f"cmake build failed (exit {build.returncode}).\n"
            f"--- stdout ---\n{build.stdout}\n"
            f"--- stderr ---\n{build.stderr}"
        )
    found = _find_cpp_binary()
    if found is None:
        raise RuntimeError(
            "build succeeded but mal_abm_fast binary still not found at "
            f"{build_dir}/src/mal_abm_fast or {build_dir}/mal_abm_fast"
        )
    print(f"[conftest] C++ binary built at {found}", file=sys.stderr)
    return found


# ---------------------------------------------------------------------------
# Session-scoped fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(scope="session")
def mal_abm_fast_binary() -> str:
    """Absolute path to the C++ ABM binary (builds it if missing).

    Returns a ``str`` (not ``pathlib.Path``) so it can be passed
    directly to ``subprocess.run`` without an extra ``str()`` cast
    in every test.
    """
    found = _find_cpp_binary()
    if found is None:
        found = _build_cpp_binary()
    return str(found)


@pytest.fixture(scope="session")
def tmp_parity_dir(tmp_path_factory: pytest.TempPathFactory) -> Iterator[pathlib.Path]:
    """Session-scoped temp directory for the parity harness.

    Cleans the directory before use (so a previous aborted run
    doesn't leave COG/JSON files lying around that would change
    the byte-equal determinism test) and exposes it as a
    :class:`pathlib.Path`.
    """
    base = tmp_path_factory.mktemp("parity")
    if base.exists():
        # Just in case tmp_path_factory returned a pre-existing
        # path on this platform — wipe its contents but keep the
        # directory itself (tmp_path_factory controls lifecycle).
        for child in base.iterdir():
            if child.is_dir():
                shutil.rmtree(child)
            else:
                child.unlink()
    yield base
