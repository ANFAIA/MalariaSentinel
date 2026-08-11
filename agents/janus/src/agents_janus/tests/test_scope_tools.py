"""Tests for scope_tools.py — edit scope validation + middleware."""
from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any
from unittest.mock import MagicMock

import pytest

from agents_janus.scope_validator import (
    validate_edit_scope,
    validate_single_file,
    _extract_file_path,
    _build_scope_warning,
    _append_warning,
    ScopeValidationMiddleware,
)
from agents_janus.subagents.registry import Registry
from agents_janus.subagents.base import SubagentSpec


def _make_registry():
    specs = {
        "abm": SubagentSpec(
            name="abm", description="", model="", provider="",
            spec_path=None, skills=(), mailbox_inbox="",
            edits_allow=("mal-core/src/mal_core/abm/**",),
        ),
        "scoring": SubagentSpec(
            name="scoring", description="", model="", provider="",
            spec_path=None, skills=(), mailbox_inbox="",
            edits_allow=("mal-core/src/mal_core/abm/tests/calibration/**",),
        ),
        "download": SubagentSpec(
            name="download", description="", model="", provider="",
            spec_path=None, skills=(), mailbox_inbox="",
            edits_allow=("mal-core/src/mal_core/download/**",),
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


class TestValidateSingleFile:
    def test_in_scope(self):
        reg = _make_registry()
        result = validate_single_file(
            "mal-core/src/mal_core/abm/engine.hpp", "abm", reg
        )
        assert result["ok"] is True

    def test_cross_scope(self):
        reg = _make_registry()
        result = validate_single_file(
            "mal-core/src/mal_core/download/runner.py", "abm", reg
        )
        assert result["ok"] is False
        assert result["cross_scope"][0]["owner"] == "download"


class TestExtractFilePath:
    def test_dict_with_file(self):
        assert _extract_file_path({"file": "foo.py"}) == "foo.py"

    def test_dict_with_file_path(self):
        assert _extract_file_path({"file_path": "bar.py"}) == "bar.py"

    def test_dict_with_path(self):
        assert _extract_file_path({"path": "baz.py"}) == "baz.py"

    def test_pydantic_model(self):
        class FakeArgs:
            file = "model.py"
        assert _extract_file_path(FakeArgs()) == "model.py"

    def test_none(self):
        assert _extract_file_path(None) is None

    def test_empty_dict(self):
        assert _extract_file_path({}) is None


class TestBuildScopeWarning:
    def test_cross_scope_warning(self):
        reg = _make_registry()
        result = validate_single_file(
            "mal-core/src/mal_core/download/runner.py", "abm", reg
        )
        warning = _build_scope_warning(
            "mal-core/src/mal_core/download/runner.py", "abm", result, reg
        )
        assert "SCOPE WARNING" in warning
        assert "download" in warning
        assert "mal-core/src/mal_core/download/runner.py" in warning

    def test_unowned_warning(self):
        reg = _make_registry()
        result = validate_single_file("random/file.py", "abm", reg)
        warning = _build_scope_warning("random/file.py", "abm", result, reg)
        assert "No specialist owns this file" in warning

    def test_unknown_role(self):
        reg = _make_registry()
        result = {"ok": False, "error": "bad", "cross_scope": [], "unowned": ["x.py"]}
        warning = _build_scope_warning("x.py", "nonexistent", result, reg)
        assert "unknown role" in warning


class TestAppendWarning:
    def test_str_result(self):
        result = _append_warning("tool output", "⚠️ warning")
        assert result == "tool output\n\n⚠️ warning"

    def test_dict_result(self):
        result = _append_warning({"status": "ok"}, "⚠️ warning")
        parsed = json.loads(result)
        assert parsed["status"] == "ok"
        assert parsed["scope_warning"] == "⚠️ warning"

    def test_other_type(self):
        result = _append_warning(42, "⚠️ warning")
        assert "42" in result
        assert "⚠️ warning" in result


# -- Middleware tests --

@dataclass
class _FakeToolCall:
    name: str
    args: dict


@dataclass
class _FakeRequest:
    tool_call: Any


class _FakeHandler:
    def __init__(self):
        self.called = False

    def __call__(self, request):
        self.called = True
        return "ok"


class TestScopeValidationMiddleware:
    def _make_middleware(self, role="abm"):
        reg = _make_registry()
        return ScopeValidationMiddleware(reg, role)

    def test_in_scope_edit_passes_through(self):
        mw = self._make_middleware("abm")
        req = _FakeRequest(tool_call=_FakeToolCall(
            name="mcp__gitagent__edit_file",
            args={"file": "mal-core/src/mal_core/abm/engine.hpp"},
        ))
        handler = _FakeHandler()
        result = mw.wrap_tool_call(req, handler)
        assert handler.called
        assert result == "ok"

    def test_cross_scope_edit_injects_warning(self):
        mw = self._make_middleware("abm")
        req = _FakeRequest(tool_call=_FakeToolCall(
            name="mcp__gitagent__edit_file",
            args={"file": "mal-core/src/mal_core/download/runner.py"},
        ))
        handler = _FakeHandler()
        result = mw.wrap_tool_call(req, handler)
        assert handler.called
        assert "SCOPE WARNING" in result
        assert "download" in result

    def test_non_edit_tool_not_validated(self):
        mw = self._make_middleware("abm")
        req = _FakeRequest(tool_call=_FakeToolCall(
            name="mcp__gitagent__read_file",
            args={"file": "mal-core/src/mal_core/download/runner.py"},
        ))
        handler = _FakeHandler()
        mw.wrap_tool_call(req, handler)
        assert handler.called

    def test_write_file_injects_warning(self):
        mw = self._make_middleware("ingest")
        req = _FakeRequest(tool_call=_FakeToolCall(
            name="mcp__gitagent__write_file",
            args={"file": "mal-core/src/mal_core/abm/engine.hpp"},
        ))
        handler = _FakeHandler()
        result = mw.wrap_tool_call(req, handler)
        assert "SCOPE WARNING" in result

    def test_delete_file_injects_warning(self):
        mw = self._make_middleware("download")
        req = _FakeRequest(tool_call=_FakeToolCall(
            name="mcp__gitagent__delete_file",
            args={"path": "mal-core/src/mal_core/abm/engine.hpp"},
        ))
        handler = _FakeHandler()
        result = mw.wrap_tool_call(req, handler)
        assert "SCOPE WARNING" in result

    def test_no_tool_call_does_not_crash(self):
        mw = self._make_middleware("abm")
        req = _FakeRequest(tool_call=None)
        handler = _FakeHandler()
        mw.wrap_tool_call(req, handler)
        assert handler.called

    def test_lifecycle_noops(self):
        mw = self._make_middleware("abm")
        mw.before_agent({}, None)
        mw.after_agent({}, None)
        mw.before_model({}, None)
        mw.after_model({}, None)
        result = mw.wrap_model_call("request", lambda r: "response")
        assert result == "response"

    def test_dict_result_gets_scope_warning_key(self):
        mw = self._make_middleware("abm")
        req = _FakeRequest(tool_call=_FakeToolCall(
            name="mcp__gitagent__edit_file",
            args={"file": "mal-core/src/mal_core/download/runner.py"},
        ))

        def dict_handler(r):
            return {"status": "ok", "output": "done"}

        result = mw.wrap_tool_call(req, dict_handler)
        assert isinstance(result, str)  # json.dumps returns str
        assert "scope_warning" in result
        assert "SCOPE WARNING" in result
