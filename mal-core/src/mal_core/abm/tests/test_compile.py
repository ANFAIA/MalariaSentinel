"""Unit tests for the C++ ABM compilation helper (mal_core.abm.compile)."""
from unittest.mock import MagicMock, patch

from mal_core.abm.compile import (
    _detect_nproc,
    _find_macos_prefixes,
    compile_abm,
    get_abm_dirs,
)


def test_get_abm_dirs():
    src_dir, build_dir, bin_dir = get_abm_dirs()
    assert src_dir.is_dir()
    assert (src_dir / "CMakeLists.txt").is_file()
    assert build_dir.name == "build"
    assert bin_dir.name == "bin"


def test_detect_nproc():
    n = _detect_nproc()
    assert isinstance(n, int)
    assert n >= 1


def test_find_macos_prefixes():
    prefixes = _find_macos_prefixes()
    assert isinstance(prefixes, list)


def test_compile_abm_dry_run_or_mock():
    with (
        patch("shutil.which", return_value="/usr/bin/cmake"),
        patch("subprocess.run") as mock_run,
        patch("shutil.copy2"),
        patch("pathlib.Path.is_file", return_value=True),
    ):
        mock_run.return_value = MagicMock(returncode=0, stdout="OK", stderr="")
        success, _ = compile_abm()
        assert success is True


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
