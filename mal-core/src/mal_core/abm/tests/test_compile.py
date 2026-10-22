"""Unit tests for the C++ ABM compilation helper (mal_core.abm.compile)."""
from pathlib import Path
from unittest.mock import MagicMock, patch

from mal_core.abm.compile import (
    _detect_nproc,
    compile_abm,
    get_abm_dirs,
    resolve_abm_dirs,
)


def test_get_abm_dirs():
    src_dir, build_dir, bin_dir = get_abm_dirs()
    assert src_dir.is_dir()
    assert (src_dir / "CMakeLists.txt").is_file()
    assert build_dir.name == "build"
    assert bin_dir.name == "bin"


def test_resolve_abm_dirs_worktree():
    wt_root = Path("/tmp/fake_worktree")
    src_dir, build_dir, bin_dir = resolve_abm_dirs(worktree=wt_root)
    assert src_dir == wt_root.resolve() / "mal-core" / "src" / "mal_core" / "abm"
    assert build_dir == src_dir / "build"
    assert bin_dir == src_dir / "bin"


def test_detect_nproc():
    n = _detect_nproc()
    assert isinstance(n, int)
    assert n >= 1








def test_compile_abm_cmake_missing():
    with patch("shutil.which", return_value=None):
        success, msg = compile_abm()
        assert success is False
        assert "not found" in msg.lower()


def test_compile_abm_configure_failure():
    with (
        patch("shutil.which", return_value="/usr/bin/cmake"),
        patch("pathlib.Path.exists", return_value=False),
        patch("subprocess.run") as mock_run,
    ):
        mock_run.return_value = MagicMock(returncode=1, stdout="", stderr="CMake Error")
        success, msg = compile_abm(clean=True)
        assert success is False
        assert "CMake Error" in msg
