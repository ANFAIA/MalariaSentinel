"""License metadata contract test — every DOWNLOADER declares its upstream license.

Stems from the 2026-09-27 licensing audit (docs/licenses.md): `malariasim
download` stamps license/attribution into manifest entries and pipeline
stages warn about usage limits, so every loader module must carry a known
license id and a non-empty literal attribution line.
"""
from __future__ import annotations

import importlib
import json

import pytest

from mal_commonlib.data.licenses import KNOWN_LICENSES, collect_limits

# Same registry order as mal_core.download.registry.LOADER_MODULES
LOADER_MODULES = [
    "era5", "chirps", "dem", "jrc_gsw", "modis",
    "worldpop", "glw", "ghsl", "wildlife", "buildings",
    "coastline", "hydrorivers", "smap",
]

# Attribution substrings that are (legally) literal lines upstream requires.
MANDATORY_ATTRIBUTION_FRAGMENTS = {
    "era5": "Copernicus Climate Change Service",
    "wildlife": "ESA WorldCover project",
    "buildings": "OpenStreetMap contributors",
    "jrc_gsw": "Pekel",
    "chirps": "Funk",
    "dem": "ODbL",
}


@pytest.mark.fast
@pytest.mark.parametrize("mod_name", LOADER_MODULES)
def test_downloader_declares_license(mod_name: str) -> None:
    mod = importlib.import_module(f"mal_commonlib.data.loaders.{mod_name}")
    raw = getattr(mod, "DOWNLOADER", None)
    assert raw is not None, f"{mod_name} must export DOWNLOADER"

    license_id = raw.get("license")
    assert license_id, f"{mod_name}.DOWNLOADER missing 'license'"
    for lid in license_id.split("+"):
        assert lid.strip() in KNOWN_LICENSES, (
            f"{mod_name}: unknown license id {lid!r} — add it to "
            "KNOWN_LICENSES or fix the id (docs/licenses.md)"
        )

    attribution = raw.get("attribution")
    assert attribution and len(attribution) >= 20, (
        f"{mod_name}.DOWNLOADER missing a literal attribution line"
    )


@pytest.mark.fast
@pytest.mark.parametrize("mod_name, fragment", MANDATORY_ATTRIBUTION_FRAGMENTS.items())
def test_attribution_literal_fragments(mod_name: str, fragment: str) -> None:
    mod = importlib.import_module(f"mal_commonlib.data.loaders.{mod_name}")
    assert fragment in mod.DOWNLOADER["attribution"], (
        f"{mod_name} attribution must contain the literal fragment {fragment!r}"
    )


@pytest.mark.fast
def test_collect_limits_dedups_and_aggregates() -> None:
    limits = collect_limits(["ODbL-1.0", "ODbL-1.0", "CC-BY-NC-4.0"])
    assert len(limits) == 2
    assert any("share-alike" in x for x in limits)
    assert any("NON-COMMERCIAL" in x for x in limits)

    # compound derived ids split on '+'
    limits2 = collect_limits(["CC-BY-4.0+WorldPop-harm"])
    assert len(limits2) == 2

    # unrestricted/wiki-nonexistent ids surface as unknown rather than vanish
    limits3 = collect_limits([""])
    assert limits3 == []


@pytest.mark.fast
def test_known_license_system() -> None:
    expected = {
        "CC-BY-4.0", "Copernicus-Cite", "NASA-Cite", "CHIRPS-Cite",
        "LicenseRef-GSHHG-LGPL-3.0", "ODbL-1.0", "CC-BY-NC-4.0",
        "WorldPop-harm",
    }
    assert set(KNOWN_LICENSES) == expected
    for lid, spec in KNOWN_LICENSES.items():
        assert isinstance(spec, dict) and spec.get("attribution"), (
            f"{lid}: every entry must carry the literal attribution line"
        )


@pytest.mark.fast
def test_derived_products_no_nc(tmp_path) -> None:
    """Ingest products must NOT carry CC BY-NC ids (only the explorer does)."""
    from mal_core.ingest._shared import register_dataset

    register_dataset(
        "gx", "host_static", None, "gx_host_static.nc",
        required_for_abm=True, format="nc",
        license="CC-BY-4.0+ODbL-1.0+NASA-Cite",
        attribution="Derived from WorldPop/GLW4/GHS-SMOD (CC BY 4.0), "
                    "Overture buildings (ODbL 1.0) and ESA WorldCover.",
        data_root=tmp_path,
    )
    manifest = json.loads((tmp_path / "gx" / "manifest.json").read_text())
    ds = manifest["datasets"]["host_static"]
    assert ds["license"] == "CC-BY-4.0+ODbL-1.0+NASA-Cite"
    assert "ODbL" in ds["attribution"]
    assert "NC-4" not in ds["license"]
