"""A failed C++ ABM run must make ``malariasim abm`` exit non-zero.

Before task-09 the CLI printed the result dict and carried on (even rendering
GIFs from stale snapshots), so a crashed engine looked like exit 0.  A run
that "finishes" without simulating 365 days is not a finished run.
"""
from __future__ import annotations

import pytest
from typer.testing import CliRunner

runner = CliRunner()


@pytest.mark.parametrize("returncode", [1, 2, -11])
def test_abm_cli_propagates_engine_failure(monkeypatch, returncode):
    import mal_core.abm as abm_pkg
    from mal_core.cli import app

    def fake(**kwargs):
        return {
            "returncode": returncode,
            "stdout": "",
            "stderr": "abm_run: unknown --aoi slug 'accra-coastal-test'",
        }

    gif_calls: list = []
    monkeypatch.setattr(abm_pkg, "run_abm_from_manifest", fake)
    monkeypatch.setattr(
        "mal_core.cli._render_animation",
        lambda **kwargs: gif_calls.append(kwargs),
    )

    result = runner.invoke(app, ["abm", "--aoi", "ghana", "--days", "1"])

    assert result.exit_code == 1
    assert "ABM engine failed" in result.output
    assert gif_calls == []
