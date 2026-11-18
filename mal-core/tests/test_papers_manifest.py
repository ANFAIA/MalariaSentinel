"""Manifest schema, status vocabulary, duplicate-DOI rejection (plan §6.2, D27)."""
from __future__ import annotations

import json

import pytest

from _papers_fixtures import VALID_SHA, make_entry, make_manifest, two_entry_manifest
from mal_core.papers.manifest import (
    CLASSES,
    STATUSES,
    ManifestError,
    dump_manifest,
    load_manifest,
    parse_manifest,
    validate_manifest,
)


def test_valid_manifest_parses_and_indexes_dois():
    manifest = parse_manifest(two_entry_manifest())
    assert len(manifest.entries) == 2
    assert manifest.get("doi:10.1186/s12936-000-0001-x").theme == "abm-geospatial"
    assert manifest.doi_index()["10.1371/journal.pone.0050464"] == "doi:10.1371/journal.pone.0050464"
    assert manifest.entries[0].pdf_relpath == "abm-geospatial/fixture-paper-2020/fixture-paper-2020.pdf"


def test_missing_field_is_reported_by_name():
    entry = make_entry()
    del entry["licence_as_recorded"]
    errors = validate_manifest(make_manifest(entry))
    assert any("missing fields" in e and "licence_as_recorded" in e for e in errors)


def test_unknown_field_is_rejected():
    errors = validate_manifest(make_manifest(make_entry(note="free text")))
    assert any("unknown fields" in e and "note" in e for e in errors)


def test_unknown_top_level_key_and_wrong_schema_version():
    data = make_manifest(make_entry())
    data["generator"] = "x"
    data["schema_version"] = 2
    errors = validate_manifest(data)
    assert any("unknown top-level keys" in e for e in errors)
    assert any("schema_version must be 1" in e for e in errors)


@pytest.mark.parametrize("cls", ["D", "a", "", None])
def test_class_must_be_A_B_or_C(cls):
    errors = validate_manifest(make_manifest(make_entry(**{"class": cls})))
    assert any("class must be one of" in e for e in errors)


@pytest.mark.parametrize("cls", CLASSES)
def test_each_declared_class_is_accepted(cls):
    assert validate_manifest(make_manifest(make_entry(**{"class": cls}))) == []


@pytest.mark.parametrize("status", STATUSES)
def test_every_status_in_vocabulary_is_accepted(status):
    doi = None if status.startswith("pending") or status == "withdrawn" else "10.1186/abc.1"
    entry = make_entry(doi=doi, expected_status=status)
    assert validate_manifest(make_manifest(entry)) == []


def test_status_outside_vocabulary_is_rejected():
    errors = validate_manifest(make_manifest(make_entry(expected_status="pending_unknown")))
    assert any("expected_status must be one of" in e for e in errors)


def test_observed_status_is_not_a_manifest_field():
    # Observed status is written by the tool to provenance.yaml (plan 6.2), never to the manifest.
    errors = validate_manifest(make_manifest(make_entry(observed_status="ok")))
    assert any("unknown fields" in e and "observed_status" in e for e in errors)


def test_bibliographic_fields_may_be_null_but_not_malformed():
    entry = make_entry(doi=None, expected_status="pending_no_source", authors=None, year=None, journal=None)
    assert validate_manifest(make_manifest(entry)) == []
    errors = validate_manifest(make_manifest(make_entry(authors=5, journal="  ", year="2020")))
    assert any("authors must be null" in e for e in errors)
    assert any("journal must be null" in e for e in errors)
    assert any("year must be null" in e for e in errors)


def test_licence_must_be_recorded_not_null():
    errors = validate_manifest(make_manifest(make_entry(licence_as_recorded=None)))
    assert any("licence_as_recorded must be a non-empty string" in e for e in errors)
    stated = make_entry(licence_as_recorded="not stated in header")
    assert validate_manifest(make_manifest(stated)) == []


def test_pmc_and_hal_ids_may_stand_without_a_doi_and_be_ok():
    for pid in ("pmc:PMC12888552", "pmc:12888552", "hal:hal-05382643v1"):
        entry = make_entry(doi=None, expected_status="ok")
        entry["id"] = pid
        assert validate_manifest(make_manifest(entry)) == [], pid


def test_ok_without_doi_or_pmc_hal_id_is_rejected():
    entry = make_entry(doi=None, expected_status="ok")
    entry["id"] = "local:thesis-without-doi"
    errors = validate_manifest(make_manifest(entry))
    assert any("needs a DOI or a pmc:/hal: id" in e for e in errors)


def test_superseded_files_is_optional_list_of_file_names():
    base = make_entry()
    assert parse_manifest(make_manifest(base)).entries[0].superseded_files == ()
    merged = dict(base, superseded_files=["other-copy.md"])
    manifest = parse_manifest(make_manifest(merged))
    assert manifest.entries[0].superseded_files == ("other-copy.md",)
    assert '"superseded_files": [' in dump_manifest(manifest)
    assert "superseded_files" not in dump_manifest(parse_manifest(make_manifest(base)))
    errors = validate_manifest(make_manifest(dict(base, superseded_files=["papers/x/other.md"])))
    assert any("superseded_files must be a list of file names" in e for e in errors)


def test_uppercase_slug_is_rejected():
    errors = validate_manifest(make_manifest(make_entry(slug="Mordecai-2013")))
    assert any("slug must match" in e for e in errors)


def test_duplicate_id_is_rejected():
    a = make_entry(slug="one")
    b = make_entry(slug="two")
    b["id"] = a["id"]
    b["doi"] = None
    errors = validate_manifest(make_manifest(a, b))
    assert any("duplicate id" in e for e in errors)


def test_duplicate_doi_is_rejected_not_silently_accepted():
    a = make_entry(slug="published-version")
    b = make_entry(slug="accepted-copy", doi=a["doi"].upper(), id="local:accepted-copy")
    errors = validate_manifest(make_manifest(a, b))
    duplicate = [e for e in errors if "duplicate DOI" in e]
    assert duplicate, errors
    assert "D27" in duplicate[0] and "merged" in duplicate[0]


def test_duplicate_theme_slug_is_rejected():
    a = make_entry()
    b = make_entry(doi="10.1000/other.2", slug=a["slug"])
    errors = validate_manifest(make_manifest(a, b))
    assert any("duplicate theme/slug" in e for e in errors)


def test_doi_id_must_match_the_lower_case_doi():
    entry = make_entry(doi="10.1186/ABC.1")
    entry["id"] = "doi:10.1186/ABC.1"
    errors = validate_manifest(make_manifest(entry))
    assert any("lower-case DOI" in e for e in errors)


def test_doi_id_without_doi_is_rejected():
    entry = make_entry(doi=None, expected_status="pending_no_source")
    entry["id"] = "doi:10.1186/abc.1"
    errors = validate_manifest(make_manifest(entry))
    assert any("doi is null" in e for e in errors)


def test_companion_variant_id_is_accepted():
    entry = make_entry(doi="10.1186/abc.1")
    entry["id"] = "doi:10.1186/abc.1#supplement"
    assert validate_manifest(make_manifest(entry)) == []


def test_alias_of_must_be_null():
    errors = validate_manifest(make_manifest(make_entry(alias_of="doi:10.1000/x")))
    assert any("alias_of must be null" in e for e in errors)


def test_sha256_must_be_64_lower_hex():
    assert validate_manifest(make_manifest(make_entry(pdf_sha256=VALID_SHA))) == []
    errors = validate_manifest(make_manifest(make_entry(pdf_sha256="ABC")))
    assert any("pdf_sha256" in e for e in errors)


def test_resolver_vocabulary():
    assert validate_manifest(make_manifest(make_entry(resolver="unpaywall"))) == []
    errors = validate_manifest(make_manifest(make_entry(resolver="google")))
    assert any("resolver must be" in e for e in errors)


def test_year_range_and_type():
    assert any("year" in e for e in validate_manifest(make_manifest(make_entry(year="2020"))))
    assert any("year" in e for e in validate_manifest(make_manifest(make_entry(year=True))))


def test_all_problems_are_collected_at_once():
    bad = make_entry(**{"class": "Z", "expected_status": "nope", "year": 1})
    with pytest.raises(ManifestError) as info:
        parse_manifest(make_manifest(bad))
    assert len(info.value.errors) >= 3


def test_load_manifest_missing_file_raises(tmp_path):
    with pytest.raises(ManifestError, match="manifest not found"):
        load_manifest(tmp_path / "manifest.json")


def test_load_manifest_invalid_json_raises(tmp_path):
    path = tmp_path / "manifest.json"
    path.write_text("{not json", encoding="utf-8")
    with pytest.raises(ManifestError, match="invalid JSON"):
        load_manifest(path)


def test_dump_is_deterministic_and_round_trips(tmp_path):
    data = two_entry_manifest()
    reversed_data = make_manifest(*reversed(data["entries"]))
    text = dump_manifest(parse_manifest(data))
    assert text == dump_manifest(parse_manifest(reversed_data))
    assert text.endswith("\n")
    path = tmp_path / "manifest.json"
    path.write_text(text, encoding="utf-8")
    again = load_manifest(path)
    assert dump_manifest(again) == text
    assert json.loads(text)["schema_version"] == 1
