"""Cross-layer NoData contract (task-02 P2).

The low-level loaders sit below mal-core and cannot import its validator,
so they read the shared sentinel through
``mal_commonlib.model_constants.model_constant``.  If the YAML sentinel
changes, every loader must follow: this test fails on any module that
goes back to a compiled literal.
"""
from __future__ import annotations

import importlib

import pytest

from mal_commonlib.model_constants import model_constant

_NODATA_FLOAT = float(model_constant("ingest", "nodata_sentinel"))
_NODATA_INT = int(model_constant("ingest", "nodata_sentinel_int"))

_CASES = [
    ("mal_commonlib.data.host_utils", "_NODATA", _NODATA_FLOAT),
    ("mal_commonlib.data.loaders.era5", "ERA5_NODATA", _NODATA_FLOAT),
    ("mal_commonlib.data.loaders.chirps", "CHIRPS_NODATA", _NODATA_FLOAT),
    ("mal_commonlib.data.loaders.modis", "_NODATA_OUT_SCALAR", _NODATA_FLOAT),
    ("mal_commonlib.data.loaders.ghsl", "_NODATA", _NODATA_FLOAT),
    ("mal_commonlib.data.loaders.ghsl", "_NODATA_INT", _NODATA_INT),
    ("mal_commonlib.data.loaders.glw", "_NODATA", _NODATA_FLOAT),
    ("mal_commonlib.data.loaders.jrc_gsw", "_NODATA_OUT_SCALAR", _NODATA_FLOAT),
    ("mal_commonlib.data.loaders.coastline", "_NODATA_OUT_SCALAR", _NODATA_FLOAT),
    ("mal_commonlib.data.loaders.smap", "_NODATA_OUT", _NODATA_FLOAT),
    ("mal_commonlib.data.loaders.worldpop", "_OUT_NODATA", _NODATA_FLOAT),
    ("mal_commonlib.data.loaders.wildlife", "_NODATA_OUT_SCALAR", _NODATA_FLOAT),
    ("mal_commonlib.data.loaders.buildings", "_NODATA", _NODATA_FLOAT),
]


@pytest.mark.parametrize("module_name,attr,expected", _CASES)
def test_loader_nodata_follows_yaml(module_name, attr, expected):
    mod = importlib.import_module(module_name)
    assert getattr(mod, attr) == expected
