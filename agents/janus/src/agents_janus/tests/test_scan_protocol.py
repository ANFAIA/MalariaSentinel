"""Tests for SCAN markers protocol."""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "src"))


def test_scan_full_has_7_markers():
    """FULL scan markers contain all 7 markers."""
    from agents_janus.sibling.scan import get_scan_markers, ScanLevel

    markers = get_scan_markers(ScanLevel.FULL)
    for i in range(1, 8):
        assert f"@@SCAN_{i}" in markers


def test_scan_mini_has_3_markers():
    """MINI scan markers contain 3 markers."""
    from agents_janus.sibling.scan import get_scan_markers, ScanLevel

    markers = get_scan_markers(ScanLevel.MINI)
    for i in range(1, 4):
        assert f"@@SCAN_{i}" in markers
    assert "@@SCAN_4" not in markers


def test_scan_anchor():
    """ANCHOR scan markers contain focus instruction."""
    from agents_janus.sibling.scan import get_scan_markers, ScanLevel

    markers = get_scan_markers(ScanLevel.ANCHOR)
    assert "ANCHOR" in markers
    assert "Focus on the original goal" in markers
