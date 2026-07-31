"""Tests for the M14 subagent system."""
import json
import tempfile
from pathlib import Path
import pytest


def test_subagent_spec_frozen():
    from agents.janus.subagents.base import SubagentSpec
    spec = SubagentSpec(
        name="test", description="test desc", model="m", provider="p",
        spec_path=None, skills=(), mailbox_inbox="inbox-test",
        edits_allow=(), plugins=()
    )
    assert spec.name == "test"
    # Frozen: cannot mutate
    with pytest.raises(AttributeError):
        spec.name = "other"


def test_resolved_subagent():
    from agents.janus.subagents.base import ResolvedSubagent, SubagentSpec
    spec = SubagentSpec(
        name="test", description="", model="", provider="",
        spec_path=None, skills=(), mailbox_inbox="",
        edits_allow=(), plugins=()
    )
    resolved = ResolvedSubagent(
        spec=spec, tools=(), permissions=(), preamble="hello", hooks={}
    )
    assert resolved.preamble == "hello"


def test_readonly_plugin():
    from agents.janus.plugins.readonly import ReadOnlyPlugin
    from agents.janus.subagents.base import SubagentSpec
    spec = SubagentSpec(
        name="test", description="", model="", provider="",
        spec_path=None, skills=(), mailbox_inbox="",
        edits_allow=(), plugins=()
    )
    ro = ReadOnlyPlugin()
    resolved = ro.apply(spec)
    assert "READ-ONLY" in resolved.preamble
    assert len(resolved.permissions) > 0


def test_edit_plugin():
    from agents.janus.plugins.edit import EditPlugin
    from agents.janus.subagents.base import SubagentSpec
    spec = SubagentSpec(
        name="test", description="", model="", provider="",
        spec_path=None, skills=(), mailbox_inbox="",
        edits_allow=(), plugins=()
    )
    edit = EditPlugin()
    resolved = edit.apply(spec)
    assert "gitagent" in resolved.preamble.lower()
    assert len(resolved.permissions) > 0


def test_builder_chain():
    from agents.janus.subagents.builder import build_resolved
    from agents.janus.plugins.edit import EditPlugin
    from agents.janus.plugins.readonly import ReadOnlyPlugin
    from agents.janus.subagents.base import SubagentSpec
    spec = SubagentSpec(
        name="test", description="", model="", provider="",
        spec_path=None, skills=(), mailbox_inbox="",
        edits_allow=(), plugins=()
    )
    result = build_resolved(spec, [EditPlugin(), ReadOnlyPlugin()])
    assert "gitagent" in result.preamble.lower()
    assert "READ-ONLY" in result.preamble


def test_mailbox_round_trip():
    from agents.janus.mailbox import mailbox_send, mailbox_check_inbox, mailbox_mark_resolved, set_session_dir
    with tempfile.TemporaryDirectory() as td:
        set_session_dir(Path(td))
        result = json.loads(mailbox_send(to="abm", re="test", summary="hello"))
        assert result["status"] == "sent"
        inbox = json.loads(mailbox_check_inbox("abm"))
        assert inbox["count"] == 1
        resolved = json.loads(mailbox_mark_resolved(inbox["messages"][0]["id"], "abm"))
        assert resolved["status"] == "resolved"
        inbox2 = json.loads(mailbox_check_inbox("abm"))
        assert inbox2["count"] == 0


def test_scope_validator():
    from agents.janus.scope_validator import validate_proposal_scope
    from agents.janus.subagents.registry import Registry
    from agents.janus.subagents.base import SubagentSpec
    specs = {
        "abm": SubagentSpec(name="abm", description="", model="", provider="", spec_path=None,
                            skills=(), mailbox_inbox="", edits_allow=("mal-core/src/mal_core/abm/**",), plugins=()),
        "download": SubagentSpec(name="download", description="", model="", provider="", spec_path=None,
                                 skills=(), mailbox_inbox="", edits_allow=("mal-core/src/mal_core/download/**",), plugins=()),
    }
    reg = Registry(specs)
    # In scope
    r = validate_proposal_scope(["mal-core/src/mal_core/abm/engine.hpp"], "abm", reg)
    assert r["ok"] is True
    # Cross scope
    r2 = validate_proposal_scope(["mal-core/src/mal_core/download/runner.py"], "abm", reg)
    assert r2["ok"] is False
    assert len(r2["cross_scope"]) == 1
    # Unowned
    r3 = validate_proposal_scope(["some/random/file.py"], "abm", reg)
    assert r3["ok"] is False
    assert len(r3["unowned"]) == 1


def test_registry_find_owner():
    from agents.janus.subagents.registry import Registry
    from agents.janus.subagents.base import SubagentSpec
    specs = {
        "abm": SubagentSpec(name="abm", description="", model="", provider="", spec_path=None,
                            skills=(), mailbox_inbox="", edits_allow=("mal-core/src/mal_core/abm/**",), plugins=()),
    }
    reg = Registry(specs)
    assert reg.find_owner("mal-core/src/mal_core/abm/engine.hpp") == "abm"
    assert reg.find_owner("other/file.py") is None
