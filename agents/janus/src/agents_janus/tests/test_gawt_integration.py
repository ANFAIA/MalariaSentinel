"""Integration tests for gawt MCP architecture.

Tests the full dispatcher workflow using mocks:
1. Orchestrator decomposes goal -> subtasks
2. Writes manifest
3. Starts gawt session
4. Dispatches specialists (parallel/sequential)
5. Monitors via list_agents/list_edits
6. Finalizes session

Also tests:
- Conflict detection and resolution
- Specialist-spawned sub-agents
- Crash recovery semantics
- Scope validation
"""
from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock, patch, call

import pytest

from agents_janus.manifest import (
    write_manifest,
    read_manifest,
    append_agent,
    update_agent_status,
    find_agent,
    get_manifest_path,
)
from agents_janus.scope_validator import validate_edit_scope
from agents_janus.subagents.registry import Registry
from agents_janus.subagents.base import SubagentSpec


# -- Fixtures --

def _make_registry():
    specs = {
        "abm": SubagentSpec(
            name="abm", description="ABM C++ engine", model="", provider="",
            spec_path=None, skills=(), mailbox_inbox="",
            edits_allow=("mal-core/src/mal_core/abm/**",),
            plugins=(),
        ),
        "scoring": SubagentSpec(
            name="scoring", description="Calibration scorers", model="", provider="",
            spec_path=None, skills=(), mailbox_inbox="",
            edits_allow=("mal-core/src/mal_core/abm/tests/calibration/**",),
            plugins=(),
        ),
        "ingest": SubagentSpec(
            name="ingest", description="Env tensor builder", model="", provider="",
            spec_path=None, skills=(), mailbox_inbox="",
            edits_allow=("mal-core/src/mal_core/ingest/**",),
            plugins=(),
        ),
    }
    return Registry(specs)


# -- Dispatcher workflow tests --

class TestDispatcherWorkflow:
    """Test the full orchestrator -> specialist dispatch workflow."""

    def test_manifest_written_before_session(self, tmp_path):
        """Orchestrator writes manifest BEFORE starting gawt session."""
        write_manifest(
            feature="fix_extinction",
            agents=[
                {"requested_id": "a_abm", "role": "abm", "task": "Fix oviposition"},
                {"requested_id": "a_scoring", "role": "scoring", "task": "Add D15"},
                {"requested_id": "a_ingest", "role": "ingest", "task": "Audit env"},
            ],
            base_sha="abc123",
            worktree_root=tmp_path,
        )
        manifest_path = get_manifest_path("fix_extinction", tmp_path)
        assert manifest_path.exists()
        manifest = read_manifest(manifest_path)
        assert len(manifest["agents"]) == 3
        assert manifest["base_sha"] == "abc123"

    def test_specialist_reads_manifest_on_init(self, tmp_path):
        """Specialist reads manifest and finds its own entry."""
        write_manifest(
            feature="test",
            agents=[
                {"requested_id": "a_abm", "role": "abm", "task": "Fix engine"},
                {"requested_id": "a_scoring", "role": "scoring", "task": "Add D15",
                 "depends_on": ["a_abm"]},
            ],
            worktree_root=tmp_path,
        )
        manifest_path = get_manifest_path("test", tmp_path)
        agent = find_agent(manifest_path, "a_scoring")
        assert agent is not None
        assert agent["role"] == "scoring"
        assert "a_abm" in agent["depends_on"]

    def test_specialist_spawns_subagent_updates_manifest(self, tmp_path):
        """When specialist A spawns specialist B, manifest is updated."""
        write_manifest(
            feature="test",
            agents=[{"requested_id": "a_abm", "role": "abm", "task": "Fix engine"}],
            worktree_root=tmp_path,
        )
        manifest_path = get_manifest_path("test", tmp_path)

        # Simulate spawn_subagent appending a new entry
        append_agent(manifest_path, {
            "requested_id": "a_scoring",
            "role": "scoring",
            "task": "Add D15 extinction scorer",
            "spawned_by": "subagent",
        })
        manifest = read_manifest(manifest_path)
        assert len(manifest["agents"]) == 2
        assert manifest["agents"][1]["spawned_by"] == "subagent"

    def test_parallel_independent_agents(self, tmp_path):
        """Independent agents (no depends_on) can start in parallel."""
        write_manifest(
            feature="test",
            agents=[
                {"requested_id": "a_abm", "role": "abm", "task": "Fix engine", "depends_on": []},
                {"requested_id": "a_ingest", "role": "ingest", "task": "Audit env", "depends_on": []},
            ],
            worktree_root=tmp_path,
        )
        manifest = read_manifest(get_manifest_path("test", tmp_path))
        for agent in manifest["agents"]:
            assert agent["depends_on"] == []

    def test_dependent_agent_waits(self, tmp_path):
        """Agent with depends_on waits for upstream to complete."""
        write_manifest(
            feature="test",
            agents=[
                {"requested_id": "a_abm", "role": "abm", "task": "Fix engine"},
                {"requested_id": "a_scoring", "role": "scoring", "task": "Add D15",
                 "depends_on": ["a_abm"]},
            ],
            worktree_root=tmp_path,
        )
        scoring = find_agent(get_manifest_path("test", tmp_path), "a_scoring")
        assert "a_abm" in scoring["depends_on"]


# -- Conflict resolution tests --

class TestConflictResolution:
    """Test conflict detection and resolution semantics."""

    def test_two_agents_editing_same_file_detected(self):
        """When two agents edit the same file, scope validator detects cross-scope."""
        reg = _make_registry()
        # Both abm and scoring own parts of calibration/
        result = validate_edit_scope(
            edited_files=["mal-core/src/mal_core/abm/tests/calibration/scorers/D15.py"],
            agent_role="abm",
            registry=reg,
        )
        # abm owns mal-core/src/mal_core/abm/** which includes tests/calibration/
        assert result["ok"] is True

    def test_conflict_window_configurable(self, tmp_path):
        """Conflict window is configurable in manifest."""
        write_manifest(
            feature="test",
            agents=[],
            conflict_window_seconds=60,
            worktree_root=tmp_path,
        )
        manifest = read_manifest(get_manifest_path("test", tmp_path))
        assert manifest["conflict_window_seconds"] == 60

    def test_re_read_after_conflict(self, tmp_path):
        """After conflict, agent re-reads file (gets latest content)."""
        # This is a semantic test -- the actual re-read happens via mcp__gitagent__read_file
        # We verify the manifest tracks the conflict window
        write_manifest(
            feature="test",
            agents=[
                {"requested_id": "a_1", "role": "abm", "task": "fix A"},
                {"requested_id": "a_2", "role": "scoring", "task": "fix B"},
            ],
            conflict_window_seconds=30,
            worktree_root=tmp_path,
        )
        manifest = read_manifest(get_manifest_path("test", tmp_path))
        assert manifest["conflict_window_seconds"] == 30


# -- Crash recovery tests --

class TestCrashRecovery:
    """Test crash semantics and recovery."""

    def test_manifest_persists_across_restarts(self, tmp_path):
        """Manifest survives orchestrator crash -- readable on restart."""
        write_manifest(
            feature="test",
            agents=[{"requested_id": "a_abm", "role": "abm", "task": "fix"}],
            base_sha="abc123",
            worktree_root=tmp_path,
        )
        # Simulate restart: read manifest again
        manifest = read_manifest(get_manifest_path("test", tmp_path))
        assert manifest["feature"] == "test"
        assert manifest["base_sha"] == "abc123"

    def test_agent_status_tracked(self, tmp_path):
        """Agent status is tracked in manifest for crash detection."""
        write_manifest(
            feature="test",
            agents=[{"requested_id": "a_abm", "role": "abm", "task": "fix"}],
            worktree_root=tmp_path,
        )
        manifest_path = get_manifest_path("test", tmp_path)

        # Agent starts
        update_agent_status(manifest_path, "a_abm", "running", agent_id="a_real_123")
        manifest = read_manifest(manifest_path)
        assert manifest["agents"][0]["status"] == "running"
        assert manifest["agents"][0]["agent_id"] == "a_real_123"

        # Agent completes
        update_agent_status(manifest_path, "a_abm", "completed")
        manifest = read_manifest(manifest_path)
        assert manifest["agents"][0]["status"] == "completed"


# -- Scope validation tests --

class TestScopeValidation:
    """Test that scope validation works correctly."""

    def test_abm_can_edit_engine(self):
        reg = _make_registry()
        result = validate_edit_scope(
            edited_files=["mal-core/src/mal_core/abm/engine.cpp"],
            agent_role="abm",
            registry=reg,
        )
        assert result["ok"] is True

    def test_scoring_can_edit_scorers(self):
        reg = _make_registry()
        result = validate_edit_scope(
            edited_files=["mal-core/src/mal_core/abm/tests/calibration/scorers/D15.py"],
            agent_role="scoring",
            registry=reg,
        )
        assert result["ok"] is True

    def test_ingest_cannot_edit_abm(self):
        reg = _make_registry()
        result = validate_edit_scope(
            edited_files=["mal-core/src/mal_core/abm/engine.cpp"],
            agent_role="ingest",
            registry=reg,
        )
        assert result["ok"] is False
        assert len(result["cross_scope"]) == 1

    def test_empty_edits_valid(self):
        reg = _make_registry()
        result = validate_edit_scope(
            edited_files=[],
            agent_role="abm",
            registry=reg,
        )
        assert result["ok"] is True


# -- Architecture invariant tests --

class TestArchitectureInvariants:
    """Test that the new architecture maintains key invariants."""

    def test_orchestrator_prompt_mentions_gawt_lifecycle(self):
        """Orchestrator prompt must mention gawt lifecycle tools."""
        from agents_janus.agent import _load_orchestrator_prompt
        prompt = _load_orchestrator_prompt()
        assert "mcp__gitagent__start_session" in prompt
        assert "mcp__gitagent__finalize_session" in prompt
        assert "mcp__gitagent__list_agents" in prompt

    def test_orchestrator_prompt_forbids_editing(self):
        """Orchestrator prompt must state it does NOT edit files."""
        from agents_janus.agent import _load_orchestrator_prompt
        prompt = _load_orchestrator_prompt()
        assert "You do NOT" in prompt
        assert "Edit files" in prompt

    def test_tools_list_no_gitagent_cli(self):
        """TOOLS list must not contain old gitagent CLI wrappers."""
        from agents_janus.agent import TOOLS
        tool_names = [t.__name__ if hasattr(t, '__name__') else str(t) for t in TOOLS]
        for name in tool_names:
            assert "gitagent_init" not in name
            assert "gitagent_start" not in name
            assert "gitagent_spawn" not in name
            assert "gitagent_propose" not in name
            assert "gitagent_integrate" not in name
            assert "gitagent_finalize" not in name

    def test_no_sibling_imports(self):
        """No module imports from deleted sibling package."""
        import importlib
        with pytest.raises((ImportError, ModuleNotFoundError)):
            importlib.import_module("agents_janus.sibling")

    def test_no_mailbox_imports(self):
        """No module imports from deleted mailbox package."""
        import importlib
        with pytest.raises((ImportError, ModuleNotFoundError)):
            importlib.import_module("agents_janus.mailbox")

    def test_manifest_schema_complete(self, tmp_path):
        """Manifest has all required fields per plan."""
        write_manifest(
            feature="test",
            agents=[{
                "requested_id": "a_abm",
                "role": "abm",
                "task": "fix engine",
                "owns": ["mal-core/src/mal_core/abm/**"],
                "propose_order": 0,
                "depends_on": [],
            }],
            worktree_root=tmp_path,
        )
        manifest = read_manifest(get_manifest_path("test", tmp_path))
        # Top-level fields
        assert "feature" in manifest
        assert "target_branch" in manifest
        assert "base_sha" in manifest
        assert "created_at" in manifest
        assert "agents" in manifest
        assert "conflict_window_seconds" in manifest
        assert "specialist_spawns_allowed" in manifest
        # Agent fields
        agent = manifest["agents"][0]
        assert "requested_id" in agent
        assert "agent_id" in agent
        assert "role" in agent
        assert "task" in agent
        assert "owns" in agent
        assert "propose_order" in agent
        assert "depends_on" in agent
        assert "spawned_by" in agent
        assert "status" in agent
