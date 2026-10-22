"""Contract tests for the download plugin system.

Validates that every DOWNLOADER dict in mal_commonlib.data.loaders follows
the spec in docs/specs/download/spec.md. The modules are discovered (not
listed) so a new loader is covered automatically.
"""
import importlib

from mal_core.download.registry import _loader_module_names

LOADER_MODULES = _loader_module_names()

VALID_AUTH = {"cds", "earthdata", "planetary_computer", "earthengine", "none"}


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


def test_downloader_dict_structure():
    downloaders = _discover_downloaders()
    assert downloaders, "no DOWNLOADER dicts discovered"
    for mod_name, dl in downloaders.items():
        for key in ("name", "description", "requires_auth", "outputs",
                    "manifest_keys"):
            assert key in dl, f"{mod_name}: missing required key '{key}'"
        assert isinstance(dl["name"], str), f"{mod_name}: name must be str"
        assert dl["name"] == dl["name"].lower(), (
            f"{mod_name}: name must be lowercase, got '{dl['name']}'")
        assert " " not in dl["name"], (
            f"{mod_name}: name must have no spaces, got '{dl['name']}'")
        assert isinstance(dl["description"], str) and dl["description"], (
            f"{mod_name}: description must be a non-empty string")
        assert isinstance(dl["requires_auth"], list), (
            f"{mod_name}: requires_auth must be list")
        for auth in dl["requires_auth"]:
            assert auth in VALID_AUTH, (
                f"{mod_name}: invalid auth '{auth}', must be in {VALID_AUTH}")
        assert isinstance(dl["outputs"], dict), f"{mod_name}: outputs must be dict"
        assert isinstance(dl["manifest_keys"], dict), (
            f"{mod_name}: manifest_keys must be dict")


def test_all_outputs_are_callable_with_manifest_key():
    for mod_name, dl in _discover_downloaders().items():
        for name, func in dl["outputs"].items():
            assert callable(func), f"{mod_name}.{name}: output must be callable"
            assert name in dl["manifest_keys"], (
                f"{mod_name}: output '{name}' has no manifest_keys entry")
        for name, key in dl["manifest_keys"].items():
            assert isinstance(key, str) and key, (
                f"{mod_name}.manifest_keys['{name}']: must be non-empty string")


def test_unique_names():
    names = [dl["name"] for dl in _discover_downloaders().values()]
    assert len(names) == len(set(names)), f"Duplicate downloader names: {names}"


def test_manifest_keys_unique_within_downloader():
    # Keys may repeat across downloaders (different AOIs/datasets); within
    # one downloader a duplicate key would make the catalog ambiguous.
    for mod_name, dl in _discover_downloaders().items():
        keys = list(dl["manifest_keys"].values())
        assert len(keys) == len(set(keys)), (
            f"{mod_name}: duplicate manifest keys within downloader: {keys}")


def test_registered_set_matches_contract_v3():
    # Contract v3.0 (+Dynamic World swap): dem is retired, worldcover is
    # replaced by dynamic_world (see docs/specs/download/spec.md).
    found = set(_discover_downloaders())
    expected = {
        "era5", "chirps", "jrc_gsw", "modis", "worldpop",
        "dynamic_world", "glw", "ghsl", "wildlife", "buildings",
        "coastline", "smap",
    }
    assert expected <= found, f"Missing downloaders: {expected - found}"
    assert "dem" not in found, "dem loader must be retired"
    assert "worldcover" not in found, "worldcover must be replaced by dynamic_world"
