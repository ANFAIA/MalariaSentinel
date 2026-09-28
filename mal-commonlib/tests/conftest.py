"""Pytest configuration for mal_commonlib.

Registers custom marks used by the loader tests so that ``-m integration``
works without warnings. Keeps the rest of the test discovery unchanged.
"""
from __future__ import annotations

import pytest


def pytest_configure(config: pytest.Config) -> None:
    config.addinivalue_line(
        "markers",
        "integration: integration tests that hit the real network "
        "(NASA Earthdata, MERIT, WorldCover). Skipped by default unless "
        "the appropriate env var is set.",
    )
