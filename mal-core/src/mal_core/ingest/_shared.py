"""Shared helpers for the ingest stage."""
from __future__ import annotations

from pathlib import Path


def register_dataset(
    aoi_slug: str,
    dataset_name: str,
    year: int | str | None,
    filename: str,
    *,
    type: str = "static",
    required_for_abm: bool = False,
    variables: list[str] | None = None,
    format: str | None = None,
    license: str | None = None,
    attribution: str | None = None,
    data_root: Path | None = None,
) -> None:
    """Register a build output in the central manifest.

    ``license``/``attribution`` follow the same convention as the download
    stage (``mal_commonlib.data.licenses.KNOWN_LICENSES``; '+'-joined ids
    for derived products). See docs/licenses.md for the decision log.

    ``update_dataset`` honours every kwarg (type / required_for_abm /
    variables / format / license / attribution); legacy callers that
    pass only a filename keep working because the extra kwargs default
    to None.
    """
    from mal_core.download.manifest import update_dataset

    update_dataset(aoi_slug, dataset_name, year, filename, type=type, required_for_abm=required_for_abm, variables=variables, format=format, license=license, attribution=attribution, data_root=data_root)
