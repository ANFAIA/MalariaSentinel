"""Inline fixtures for the paper-corpus tests. Nothing here reads ``papers/``."""
from __future__ import annotations

from typing import Any

VALID_SHA = "a" * 64


def make_entry(**overrides: Any) -> dict[str, Any]:
    """One manifest entry dict (JSON shape, before validation)."""
    doi = overrides.pop("doi", "10.1186/s12936-000-0001-x")
    base: dict[str, Any] = {
        "id": f"doi:{doi.lower()}" if doi else "local:fixture-paper",
        "class": "A",
        "theme": "abm-geospatial",
        "slug": "fixture-paper-2020",
        "title": "A fixture paper",
        "authors": "Doe J, Roe R",
        "year": 2020,
        "journal": "Malaria Journal",
        "doi": doi,
        "alias_of": None,
        "expected_status": "ok",
        "pdf_sha256": None,
        "resolver": None,
        "licence_as_recorded": "CC BY 4.0",
    }
    base.update(overrides)
    return base


def make_manifest(*entries: dict[str, Any]) -> dict[str, Any]:
    return {"schema_version": 1, "entries": list(entries)}


def two_entry_manifest() -> dict[str, Any]:
    """Two valid entries in different themes, with distinct DOIs and slugs."""
    first = make_entry()
    second = make_entry(
        doi="10.1371/journal.pone.0050464",
        theme="core-hypothesis",
        slug="roe-2012-host-seeking",
        title="Host seeking | a fixture with a pipe",
        authors="Roe R",
        year=2012,
        journal="PLoS ONE",
        licence_as_recorded="CC BY 4.0",
        expected_status="pending_paywalled",
    )
    return make_manifest(first, second)
