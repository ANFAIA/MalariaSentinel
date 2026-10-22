"""Wiring tests for the `malariasim abm --gif` code path."""
from __future__ import annotations

from pathlib import Path

from mal_core import cli
from mal_core.abm.scripts import visualize_state, visualize_transmission


def _record_calls(monkeypatch, module, captured: list[list[str]], gif_name: str | None = None):
    def fake_main(argv: list[str]) -> None:
        captured.append(list(argv))
        if gif_name:
            out = Path(argv[argv.index("--output") + 1])
            out.parent.mkdir(parents=True, exist_ok=True)
            out.write_bytes(b"GIF89a")

    monkeypatch.setattr(module, "main", fake_main)


def test_render_animation_wires_run_dir_output_and_max_width(tmp_path, monkeypatch):
    calls: list[list[str]] = []
    _record_calls(monkeypatch, visualize_state, calls, gif_name="vectors.gif")
    _record_calls(monkeypatch, visualize_transmission, calls, gif_name="transmission.gif")
    (tmp_path / "aoi_abm_seed0007_cohort.json").write_text("{}")
    (tmp_path / "aoi_abm_seed0007_transmission_day001.tif").write_bytes(b"")

    cli._render_animation(
        aoi="aoi",
        seed=7,
        output_dir=tmp_path,
        cohort_log=None,
        enable_transmission=True,
        max_width=1280,
    )

    vector_argv = calls[0]
    assert vector_argv[vector_argv.index("--run-dir") + 1] == str(tmp_path)
    assert vector_argv[vector_argv.index("--output") + 1].endswith("aoi_abm_seed0007_vectors.gif")
    assert vector_argv[vector_argv.index("--cohort-log") + 1] == str(
        tmp_path / "aoi_abm_seed0007_cohort.json"
    )
    assert vector_argv[vector_argv.index("--max-width") + 1] == "1280"
    # --gif also drops a default-named copy next to the vector animation.
    assert (tmp_path / "aoi_abm_seed0007.gif").read_bytes() == b"GIF89a"
    assert calls[1][calls[1].index("--output") + 1].endswith(
        "aoi_abm_seed0007_transmission.gif"
    )
