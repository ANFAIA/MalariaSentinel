"""Tests for scope_tools.py — edit scope validation."""
from __future__ import annotations

import json

import pytest

from agents_janus.scope_validator import validate_edit_scope
from agents_janus.subagents.registry import Registry
from agents_janus.subagents.base import SubagentSpec


def _make_registry():
    specs = {
        "abm": SubagentSpec(
            name="abm", description="", model="", provider="",
            spec_path=None, skills=(), mailbox_inbox="",
            edits_allow=("mal-core/src/mal_core/abm/**",),
            plugins=(),
        ),
        "scoring": SubagentSpec(
            name="scoring", description="", model="", provider="",
            spec_path=None, skills=(), mailbox_inbox="",
            edits_allow=("mal-core/src/mal_core/abm/tests/calibration/**",),
            plugins=(),
        ),
        "download": SubagentSpec(
            name="download", description="", model="", provider="",
            spec_path=None, skills=(), mailbox_inbox="",
            edits_allow=("mal-core/src/mal_core/download/**",),
            plugins=(),
        ),
    }
    return Registry(specs)


class TestValidateEditScope:
    def test_in_scope(self):
        reg = _make_registry()
        result = validate_edit_scope(
            edited_files=["mal-core/src/mal_core/abm/engine.hpp"],
            agent_role="abm",
            registry=reg,
        )
        assert result["ok"] is True
        assert len(result["in_scope"]) == 1
        assert len(result["cross_scope"]) == 0
        assert len(result["unowned"]) == 0

    def test_cross_scope(self):
        reg = _make_registry()
        result = validate_edit_scope(
            edited_files=["mal-core/src/mal_core/download/runner.py"],
            agent_role="abm",
            registry=reg,
        )
        assert result["ok"] is False
        assert len(result["cross_scope"]) == 1
        assert result["cross_scope"][0]["owner"] == "download"

    def test_unowned(self):
        reg = _make_registry()
        result = validate_edit_scope(
            edited_files=["some/random/file.py"],
            agent_role="abm",
            registry=reg,
        )
        assert result["ok"] is False
        assert len(result["unowned"]) == 1

    def test_mixed_scope(self):
        reg = _make_registry()
        result = validate_edit_scope(
            edited_files=[
                "mal-core/src/mal_core/abm/engine.hpp",  # in scope
                "mal-core/src/mal_core/download/runner.py",  # cross scope
                "some/random/file.py",  # unowned
            ],
            agent_role="abm",
            registry=reg,
        )
        assert result["ok"] is False
        assert len(result["in_scope"]) == 1
        assert len(result["cross_scope"]) == 1
        assert len(result["unowned"]) == 1

    def test_unknown_role(self):
        reg = _make_registry()
        result = validate_edit_scope(
            edited_files=["mal-core/src/mal_core/abm/engine.hpp"],
            agent_role="nonexistent",
            registry=reg,
        )
        assert result["ok"] is False
        assert "error" in result

    def test_empty_files(self):
        reg = _make_registry()
        result = validate_edit_scope(
            edited_files=[],
            agent_role="abm",
            registry=reg,
        )
        assert result["ok"] is True
