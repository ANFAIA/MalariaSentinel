"""DEPRECATED — use scripts/restore_data.py instead.

This file originally used the GBIF occurrence/search API, which was discarded
because it drops many DwC columns (eventRemarks, typeStatus, individualCount,
habitat, waterBody, ...) used by the mal-data-explorer scripts. The IPT DwC-A
archives preserve all columns and require no authentication.

Canonical restore script: scripts/restore_data.py
"""
import sys

print("fetch_gbif.py is deprecated. Run instead:\n")
print("    uv run --with requests python scripts/restore_data.py\n")
print("See scripts/restore_data.py for details.")
sys.exit(1)