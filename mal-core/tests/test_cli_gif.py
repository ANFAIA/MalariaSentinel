"""Wiring tests for the native `malariasim abm --gif` path (plan 04)."""
from __future__ import annotations

from pathlib import Path

from typer.testing import CliRunner

runner = CliRunner()


def _fake_abm(monkeypatch):
    import mal_core.abm as abm_pkg

    captured: dict = {}

    def fake(**kwargs):
        captured.update(kwargs)
        return {"returncode": 0, "stdout": "", "stderr": "", "output_path": ""}

    monkeypatch.setattr(abm_pkg, "run_abm_from_manifest", fake)
    return captured


def test_cli_forwards_explicit_gif_path(monkeypatch, tmp_path):
    """`--gif <path>` must reach the wrapper as that exact path."""
    from mal_core.cli import app

    captured = _fake_abm(monkeypatch)
    out = tmp_path / "explicit.gif"

    result = runner.invoke(
        app,
        [
            "abm", "--aoi", "ghana", "--days", "2", "--output-dir", str(tmp_path),
            "--gif", str(out), "--gif-every", "2", "--gif-fps", "4",
            "--gif-max-width", "800",
        ],
    )

    assert result.exit_code == 0, result.output
    assert captured["gif"] == str(out)
    assert captured["gif_every"] == 2
    assert captured["gif_fps"] == 4
    assert captured["gif_max_width"] == 800


def test_cli_bare_gif_uses_default_artifact_name(monkeypatch, tmp_path):
    """Bare `--gif` (no value) must still work and request the default name."""
    from mal_core.cli import app

    captured = _fake_abm(monkeypatch)

    result = runner.invoke(
        app, ["abm", "--aoi", "ghana", "--days", "1", "--output-dir", str(tmp_path), "--gif"]
    )

    assert result.exit_code == 0, result.output
    # "" is the wrapper's "use <output_dir>/<aoi>_abm_seedNNNN.gif" marker.
    assert captured["gif"] == ""


def test_cli_no_gif_leaves_it_disabled(monkeypatch, tmp_path):
    from mal_core.cli import app

    captured = _fake_abm(monkeypatch)

    result = runner.invoke(
        app, ["abm", "--aoi", "ghana", "--days", "1", "--output-dir", str(tmp_path)]
    )

    assert result.exit_code == 0, result.output
    assert captured["gif"] is None


def test_wrapper_maps_gif_to_default_artifact_path(monkeypatch, tmp_path):
    """`gif=""` (bare flag) becomes `<output_dir>/<aoi>_abm_seedNNNN.gif`."""
    from mal_core.abm import wrapper as wrapper_mod

    captured: dict = {}

    class FakeWrapper:
        def __init__(self, *args, **kwargs):
            pass

        def run(self, _timeout=None, **flags):
            captured.update(flags)
            return {"stdout": "", "stderr": "", "returncode": 0}

    monkeypatch.setattr(wrapper_mod, "CppAbmWrapper", FakeWrapper)
    # `resolve`/`validate_completeness` are imported inside the function, so
    # patch them on their source modules. The env path must be truthy.
    import mal_core.download.catalog as catalog_mod
    monkeypatch.setattr(
        catalog_mod, "resolve",
        lambda *a, key=None, **k: str(tmp_path / "env.bin"))
    import mal_core.download.manifest as manifest_mod
    monkeypatch.setattr(
        manifest_mod, "validate_completeness", lambda *a, **k: [])

    result = wrapper_mod.run_abm_from_manifest(
        aoi="ghana", year=2024, month=1, days=1, seed=7,
        output_dir=tmp_path, data_root=tmp_path, gif="",
        gif_every=3, gif_fps=5, gif_max_width=720,
    )

    assert result["returncode"] == 0
    assert captured["gif"] == str(tmp_path / "ghana_abm_seed0007.gif")
    assert captured["gif_every"] == 3
    assert captured["gif_fps"] == 5
    assert captured["gif_max_width"] == 720
    assert Path(captured["gif"]).suffix == ".gif"


def test_wrapper_honours_explicit_gif_path(monkeypatch, tmp_path):
    from mal_core.abm import wrapper as wrapper_mod

    captured: dict = {}

    class FakeWrapper:
        def __init__(self, *args, **kwargs):
            pass

        def run(self, _timeout=None, **flags):
            captured.update(flags)
            return {"stdout": "", "stderr": "", "returncode": 0}

    monkeypatch.setattr(wrapper_mod, "CppAbmWrapper", FakeWrapper)
    import mal_core.download.catalog as catalog_mod
    monkeypatch.setattr(
        catalog_mod, "resolve",
        lambda *a, key=None, **k: str(tmp_path / "env.bin"))
    import mal_core.download.manifest as manifest_mod
    monkeypatch.setattr(
        manifest_mod, "validate_completeness", lambda *a, **k: [])

    explicit = tmp_path / "nested" / "run.gif"
    wrapper_mod.run_abm_from_manifest(
        aoi="ghana", year=2024, month=1, days=1, seed=7,
        output_dir=tmp_path, data_root=tmp_path, gif=str(explicit),
    )

    assert captured["gif"] == str(explicit)
