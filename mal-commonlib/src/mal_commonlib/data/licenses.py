"""Dataset license registry + restriction warnings (upstream licensing audit).

Every loader module (``mal_commonlib.data.loaders.*``) declares ``license``
(an identifier in :data:`KNOWN_LICENSES`) and ``attribution`` (the literal
credit line to reproduce in publications/maps) in its ``DOWNLOADER`` dict.
The download runner stamps both into the manifest entry; ingest registers
derived products with a ``+``-joined compound license id derived from its
inputs.  Scr: docs/licenses.md — the human-readable audit + decision log
(e.g. MERIT DEM: ODbL branch elected 2026-09-27).

Pipeline stages that produce or consume datasets call :func:`warn_limits`
once per process; it aggregates which usage restrictions apply.
"""
from __future__ import annotations

import warnings
from collections.abc import Iterable

__all__ = ["KNOWN_LICENSES", "collect_limits", "warn_limits", "warn_manifest_limits"]

# ---------------------------------------------------------------------------
# 8 upstream licenses cover every dataset the pipeline integrates.
# ---------------------------------------------------------------------------
#: license_id -> restriction spec (None = unrestricted, attribution-only)
KNOWN_LICENSES: dict[str, dict | None] = {
    # CC BY 4.0 — attribution required, derivatives free (incl. commercial)
    "CC-BY-4.0": {
        "attribution": (
            "This work incorporates data licensed under CC BY 4.0 "
            "(WorldPop / FAO GLW4 / GHS-SMOD © European Union / JRC GSW / "
            "CHIRPS—not applicable)"
        ),
        "limit": (
            "Attribution required for each CC BY 4.0 source "
            "(WorldPop, FAO GLW4, GHS-SMOD, JRC GSW, ESA WorldCover)."
        ),
    },
    # Copernicus: CC BY 4.0 since 2025-07 but attribution had the same
    # literal sentence under the earlier Copernicus licence
    "Copernicus-Cite": {
        "attribution": (
            "Contains modified Copernicus Climate Change Service information "
            "[Year]. Neither the European Commission nor ECMWF is responsible "
            "for any use that may be made of the Copernicus information or "
            "data it contains."
        ),
        "limit": (
            "Literal 'Contains modified Copernicus Climate Change Service "
            "information [Year]' line required in any distribution/publication."
        ),
    },
    # IdealSentinel-2-like — NASA Earthdata products: free, cite the DOI
    "NASA-Cite": {
        "attribution": "NASA (MODIS MOD13A3, https://doi.org/10.5067/MODIS/MOD13A3.061; SMAP RSS L3 SSS, https://doi.org/10.5067/SMP60-3SMCS)",
        "limit": "Cite the LP DAAC / PO.DAAC dataset DOI.",
    },
    # CHIRPS v2.0: free, must cite Funk et al. 2014 (USGS DS832)
    "CHIRPS-Cite": {
        "attribution": (
            "Funk, C.C., Peterson, P.J., Landsfeld, M.F., et al., 2014, "
            "A quasi-global precipitation time series for drought "
            "monitoring: U.S. Geological Survey Data Series 832, 4 p."
        ),
        "limit": "Cite Funk et al. 2014 (USGS DS832).",
    },
    # GSHHG: LGPL v3 data + Wessel & Smith 1996 citation
    "LicenseRef-GSHHG-LGPL-3.0": {
        "attribution": (
            "Wessel, P., & Smith, W. H. F. (1996), A global, self-consistent, "
            "hierarchical, high-resolution shoreline database, JGR 101, "
            "8741-8743. GSHHG is distributed under LGPL v3+."
        ),
        "limit": (
            "LGPL v3 (data): notify Wessel/Smith if the dataset itself is "
            "modified for commercial use; cite Wessel & Smith 1996."
        ),
    },
    # ODbL 1.0 — share-alike for derived databases
    "ODbL-1.0": {
        "attribution": "© OpenStreetMap contributors, Overture Maps Foundation (ODbL 1.0)",
        "limit": (
            "ODbL share-alike: any DERIVED DATABASE (host_static.nc, "
            "mobility_*.csr, wildlife_host_proxy — via Overture buildings) "
            "redistribution requires ODbL + this attribution. MERIT DEM: "
            "ODbL branch elected 2026-09-27 in docs/licenses.md."
        ),
    },
    # CC BY-NC 4.0 — non-commercial only (mal-data-explorer reference sets)
    "CC-BY-NC-4.0": {
        "attribution": "Institut Pasteur / PMI VectorLink — CC BY-NC 4.0 (GBIF-mediated)",
        "limit": (
            "NON-COMMERCIAL: guf/ (Institut Pasteur) and colombia_vl/ "
            "(PMI VectorLink) occurrence datasets — isolate to "
            "mal-data-explorer; never import into mal-core/ABM/training; "
            "no commercial use of derivatives."
        ),
    },
    # WorldPop responsible-use disclaimer (stacks on CC BY 4.0 for worldpop)
    "WorldPop-harm": {
        "attribution": "WorldPop 2019 (CC BY 4.0), www.worldpop.org",
        "limit": (
            "WorldPop responsibly-use disclaimer: not for purposes that "
            "discriminate/exploit/harm individuals or vulnerable groups; "
            "assess risk when combined with other datasets."
        ),
    },
}


def collect_limits(license_ids: Iterable[str]) -> list[str]:
    """Aggregate usage-limit sentences for a set of license ids.

    Compound derived ids are '+'-joined (e.g. ``CC-BY-4.0+ODbL-1.0``); in
    that case every component id is kept only if it adds a restriction.
    """
    seen: dict[str, str] = {}
    for raw in license_ids:
        if not raw:
            continue
        for lid in raw.split("+"):
            lid = lid.strip()
            spec = KNOWN_LICENSES.get(lid)
            if spec is None:
                seen.setdefault(
                    lid, f"Unknown license id {lid!r} — check docs/licenses.md"
                )
            elif spec.get("limit"):
                seen.setdefault(lid, spec["limit"])
    return list(seen.values())


def warn_limits(license_ids: Iterable[str], *, stacklevel: int = 2) -> None:
    """Emit a single aggregated UserWarning listing all usage limits."""
    limits = collect_limits(license_ids)
    if not limits:
        return
    body = "\n  - ".join(limits)
    warnings.warn(
        f"Upstream dataset licenses limit some uses:\n  - {body}\n"
        f"  Full audit: docs/licenses.md",
        UserWarning,
        stacklevel=stacklevel,
    )


def warn_manifest_limits(aoi: str, data_root=None) -> None:
    """Read an AOI manifest and warn once about its aggregate limits.

    Called by download / ingest stages after registration.
    """
    from mal_core.download.manifest import read_manifest

    manifest = read_manifest(aoi, data_root)
    ids = [
        (ds.get("license") or "")
        for ds in manifest.get("datasets", {}).values()
    ]
    warn_limits([i for i in ids if i], stacklevel=3)
