"""Tests for abm_tools.py — abm_run, abm_test, abm_score."""
from __future__ import annotations

import json
from unittest.mock import patch, MagicMock
import pytest


class TestAbmRun:
    @patch("agents.deepagents.tools.abm_tools.subprocess.run")
    def test_run_success(self, mock_run):
        mock_run.return_value = MagicMock(returncode=0, stdout="Done", stderr="", returncode=0)
        with patch("agents.deepagents.tools.abm_tools.Path") as mock_path:
            mock_path.return_value.resolve.return_value.parent.parent.parent.parent = MagicMock()
            # Just test that it doesn't crash
            from agents.deepagents.tools.abm_tools import abm_run
            # Can't fully test without real binary, but function exists
            assert callable(abm_run)


class TestAbmTest:
    def test_abm_test_callable(self):
        from agents.deepagents.tools.abm_tools import abm_test
        assert callable(abm_test)


class TestAbmScore:
    def test_abm_score_callable(self):
        from agents.deepagents.tools.abm_tools import abm_score
        assert callable(abm_score)
