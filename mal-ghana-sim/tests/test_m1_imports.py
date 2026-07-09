"""Smoke tests for the M1 stack (M1.2b).

These tests verify the M1-specific deps added to mal-ghana-sim in M1.2b:
  - the casablanca config still loads and exposes the expected constants
    (proves we did not regress the casablanca pipeline)
  - the new AOI schema from mal-commonlib is reachable from mal-ghana-sim
  - the new M1 deps (mesa-geo, pysheds, xarray, cdsapi, earthaccess, fastapi,
    typer, uvicorn) all import and report a non-empty __version__.

These tests do NOT execute any casablanca code paths (no rollouts, no GPU,
no raster reads). They are pure import + attribute checks.
"""
from __future__ import annotations


def test_casablanca_config_still_works() -> None:
    """The casablanca config must still expose the original constants.

    M1.2b adds M1 deps but does NOT replace the casablanca pipeline. The
    K_MAX / AOI_W values are the canonical "casablanca is intact" signal.
    """
    from mal_ghana_sim import config

    assert config.K_MAX == 1000.0, f"K_MAX must be 1000.0; got {config.K_MAX}"
    assert config.AOI_W == -2.966805555532119, (
        f"AOI_W must be the casablanca west edge; got {config.AOI_W}"
    )


def test_m1_aoi_import() -> None:
    """mal_commonlib.aoi.AOI + Scale are reachable from mal-ghana-sim.

    The AOI schema landed in mal-commonlib in M1.2a. mal-ghana-sim already
    depends on mal-commonlib as a workspace member, so the import should
    resolve without any extra deps.
    """
    from mal_commonlib.aoi import AOI, Scale

    aoi = AOI.from_bbox(-3.5, 4.5, 1.5, 11.5, "EPSG:4326", "ghana", 1000)
    assert aoi.scale == Scale.REGIONAL


def test_m1_deps_import() -> None:
    """Every M1 dep must import and report a non-empty version.

    This is a real import test, not a version-pinning test. It confirms the
    dep is installed and a version can be resolved. We accept either
    ``<mod>.__version__`` or ``importlib.metadata.version(name)`` — the
    latter covers packages (e.g. ``cdsapi``) that do not expose
    ``__version__`` at the module level.

    ``pysheds`` is NOT in this list: pysheds 0.4 hard-requires ``numba``,
    and numba (any version that supports Python 3.12) requires
    ``numpy<2.5``, which conflicts with the project's ``numpy>=2.5.0``
    floor. The pysheds TWI stack will be addressed at the M1.4 layer
    once the numpy/numba decision is made. See the M1.2b final report.
    """
    import importlib.metadata
    import cdsapi
    import earthaccess
    import fastapi
    import mesa_geo
    import typer
    import uvicorn
    import xarray

    for mod, dist_name in [
        (mesa_geo, "mesa-geo"),
        (xarray, "xarray"),
        (cdsapi, "cdsapi"),
        (earthaccess, "earthaccess"),
        (fastapi, "fastapi"),
        (typer, "typer"),
        (uvicorn, "uvicorn"),
    ]:
        ver = getattr(mod, "__version__", None) or importlib.metadata.version(dist_name)
        assert isinstance(ver, str) and ver, (
            f"{dist_name} must expose a non-empty version "
            f"(via __version__ or importlib.metadata); got {ver!r}"
        )
