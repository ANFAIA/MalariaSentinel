"""Tests for the scoring feedback module."""
from __future__ import annotations

import pytest

from mal_core.scoring.feedback import get_feedback


def test_feedback_success():
    scorecard = {"success": True, "stdout": "all passed", "stderr": ""}
    fb = get_feedback(scorecard)
    assert "passed" in fb.lower()


def test_feedback_failure():
    scorecard = {"success": False, "stdout": "", "stderr": "test_expansion FAILED"}
    fb = get_feedback(scorecard)
    assert "failed" in fb.lower()
    assert "test_expansion" in fb


def test_feedback_regression():
    scorecard = {"success": False, "stdout": "", "stderr": "err"}
    baseline = {"success": True, "stdout": "", "stderr": ""}
    fb = get_feedback(scorecard, baseline)
    assert "regression" in fb.lower() or "regress" in fb.lower()


def test_feedback_improvement():
    scorecard = {"success": True, "stdout": "", "stderr": ""}
    baseline = {"success": False, "stdout": "", "stderr": "err"}
    fb = get_feedback(scorecard, baseline)
    assert "improvement" in fb.lower()


def test_feedback_no_baseline():
    scorecard = {"success": True, "stdout": "", "stderr": ""}
    fb = get_feedback(scorecard, baseline=None)
    assert "delta" not in fb.lower()
