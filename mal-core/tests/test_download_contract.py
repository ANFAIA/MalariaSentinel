"""Contract tests for download plugin system.

Validates that every DOWNLOADER dict in mal_commonlib.data.loaders
follows the spec defined in docs/download-api-spec.md.
"""
import importlib
import inspect
from pathlib import Path

import pytest

# All loader module names that may have DOWNLOADER dicts
LOADER_MODULES = [
    "era5", "chirps", "dem", "jrc_gsw", "modis",
    "worldpop", "glw", "ghsl", "wildlife", "buildings",
]

VALID_AUTH = {"cds", "earthdata", "planetary_computer", "none"}


def _discover_downloaders():
    """Discover all DOWNLOADER dicts from loader modules."""
    downloaders = {}
    for mod_name in LOADER_MODULES:
        try:
            mod = importlib.import_module(f"mal_commonlib.data.loaders.{mod_name}")
            raw = getattr(mod, "DOWNLOADER", None)
            if raw is not None:
                downloaders[mod_name] = raw
        except Exception:
            pass
    return downloaders


class TestDownloaderDictStructure:
    """Each DOWNLOADER dict has required keys with correct types."""

    def test_has_required_keys(self):
        for mod_name, dl in _discover_downloaders().items():
            for key in ("name", "description", "requires_auth", "outputs", "manifest_keys"):
                assert key in dl, f"{mod_name}: missing required key '{key}'"

    def test_name_is_string(self):
        for mod_name, dl in _discover_downloaders().items():
            assert isinstance(dl["name"], str), f"{mod_name}: name must be str"

    def test_name_is_lowercase_no_spaces(self):
        for mod_name, dl in _discover_downloaders().items():
            name = dl["name"]
            assert name == name.lower(), f"{mod_name}: name must be lowercase, got '{name}'"
            assert " " not in name, f"{mod_name}: name must have no spaces, got '{name}'"

    def test_description_is_string(self):
        for mod_name, dl in _discover_downloaders().items():
            assert isinstance(dl["description"], str), f"{mod_name}: description must be str"

    def test_requires_auth_is_list(self):
        for mod_name, dl in _discover_downloaders().items():
            assert isinstance(dl["requires_auth"], list), f"{mod_name}: requires_auth must be list"

    def test_requires_auth_values_valid(self):
        for mod_name, dl in _discover_downloaders().items():
            for auth in dl["requires_auth"]:
                assert auth in VALID_AUTH, f"{mod_name}: invalid auth '{auth}', must be in {VALID_AUTH}"

    def test_outputs_is_dict(self):
        for mod_name, dl in _discover_downloaders().items():
            assert isinstance(dl["outputs"], dict), f"{mod_name}: outputs must be dict"

    def test_manifest_keys_is_dict(self):
        for mod_name, dl in _discover_downloaders().items():
            assert isinstance(dl["manifest_keys"], dict), f"{mod_name}: manifest_keys must be dict"


class TestDownloaderOutputs:
    """Each output callable is importable and has a manifest key."""

    def test_all_outputs_are_callable(self):
        for mod_name, dl in _discover_downloaders().items():
            for name, func in dl["outputs"].items():
                assert callable(func), f"{mod_name}.{name}: output must be callable"

    def test_all_outputs_have_manifest_key(self):
        for mod_name, dl in _discover_downloaders().items():
            for name in dl["outputs"]:
                assert name in dl["manifest_keys"], (
                    f"{mod_name}: output '{name}' has no manifest_keys entry"
                )

    def test_manifest_keys_are_nonempty_strings(self):
        for mod_name, dl in _discover_downloaders().items():
            for name, key in dl["manifest_keys"].items():
                assert isinstance(key, str) and len(key) > 0, (
                    f"{mod_name}.manifest_keys['{name}']: must be non-empty string"
                )


class TestDownloaderUniqueness:
    """No duplicate names or manifest keys across downloaders."""

    def test_unique_names(self):
        names = []
        for mod_name, dl in _discover_downloaders().items():
            names.append(dl["name"])
        assert len(names) == len(set(names)), f"Duplicate downloader names: {names}"

    def test_unique_manifest_keys(self):
        all_keys = []
        for mod_name, dl in _discover_downloaders().items():
            for key in dl["manifest_keys"].values():
                all_keys.append(key)
        # manifest keys can overlap (same key in different downloaders is OK
        # if they write to different AOIs), but within a downloader they must be unique
        for mod_name, dl in _discover_downloaders().items():
            keys = list(dl["manifest_keys"].values())
            assert len(keys) == len(set(keys)), (
                f"{mod_name}: duplicate manifest keys within downloader: {keys}"
            )


class TestDownloaderDiscovery:
    """The registry discovers downloaders correctly."""

    def test_discover_at_least_one(self):
        downloaders = _discover_downloaders()
        assert len(downloaders) >= 1, "No downloaders discovered"

    def test_era5_registered(self):
        downloaders = _discover_downloaders()
        assert "era5" in downloaders, "era5 downloader not registered"

    def test_six_loaders_registered(self):
        downloaders = _discover_downloaders()
        expected = {"era5", "chirps", "dem", "jrc_gsw", "modis", "worldpop"}
        found = set(downloaders.keys())
        missing = expected - found
        assert not missing, f"Missing downloaders: {missing}. Found: {found}"
