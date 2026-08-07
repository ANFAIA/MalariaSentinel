"""Tests for manifest.py — session manifest CRUD."""
from __future__ import annotations

import json
import tempfile
from pathlib import Path

import pytest

from agents_janus.manifest import (
    write_manifest,
    read_manifest,
    append_agent,
    update_agent_status,
    find_agent,
    get_manifest_path,
)


class TestWriteManifest:
    def test_write_creates_file(self, tmp_path):
        manifest_path = write_manifest(
            feature="test_feature",
            agents=[
                {"requested_id": "a_abm", "role": "abm", "task": "fix engine"},
                {"requested_id": "a_scoring", "role": "scoring", "task": "add D15"},
            ],
            worktree_root=tmp_path,
        )
        assert manifest_path.exists()
        data = json.loads(manifest_path.read_text())
        assert data["feature"] == "test_feature"
        assert len(data["agents"]) == 2

    def test_write_sets_defaults(self, tmp_path):
        write_manifest(
            feature="test",
            agents=[{"requested_id": "a_1"}],
            worktree_root=tmp_path,
        )
        manifest = read_manifest(get_manifest_path("test", tmp_path))
        agent = manifest["agents"][0]
        assert agent["role"] == "unknown"
        assert agent["task"] == ""
        assert agent["owns"] == []
        assert agent["depends_on"] == []
        assert agent["spawned_by"] == "orchestrator"
        assert agent["status"] == "pending"

    def test_write_custom_params(self, tmp_path):
        write_manifest(
            feature="test",
            agents=[],
            target_branch="develop",
            base_sha="abc123",
            conflict_window_seconds=60,
            specialist_spawns_allowed=False,
            worktree_root=tmp_path,
        )
        manifest = read_manifest(get_manifest_path("test", tmp_path))
        assert manifest["target_branch"] == "develop"
        assert manifest["base_sha"] == "abc123"
        assert manifest["conflict_window_seconds"] == 60
        assert manifest["specialist_spawns_allowed"] is False


class TestReadManifest:
    def test_read_existing(self, tmp_path):
        write_manifest(feature="test", agents=[], worktree_root=tmp_path)
        manifest = read_manifest(get_manifest_path("test", tmp_path))
        assert manifest["feature"] == "test"

    def test_read_nonexistent_raises(self):
        with pytest.raises(FileNotFoundError):
            read_manifest("/nonexistent/path/plan.json")


class TestAppendAgent:
    def test_append_adds_entry(self, tmp_path):
        write_manifest(feature="test", agents=[], worktree_root=tmp_path)
        manifest_path = get_manifest_path("test", tmp_path)
        append_agent(manifest_path, {
            "requested_id": "a_new",
            "role": "scoring",
            "task": "add scorer",
        })
        manifest = read_manifest(manifest_path)
        assert len(manifest["agents"]) == 1
        assert manifest["agents"][0]["requested_id"] == "a_new"
        assert manifest["agents"][0]["status"] == "spawned"
        assert manifest["agents"][0]["spawned_by"] == "subagent"


class TestUpdateAgentStatus:
    def test_update_status(self, tmp_path):
        write_manifest(
            feature="test",
            agents=[{"requested_id": "a_1", "role": "abm", "task": "fix"}],
            worktree_root=tmp_path,
        )
        manifest_path = get_manifest_path("test", tmp_path)
        update_agent_status(manifest_path, "a_1", "completed", agent_id="a_real_123")
        manifest = read_manifest(manifest_path)
        agent = manifest["agents"][0]
        assert agent["status"] == "completed"
        assert agent["agent_id"] == "a_real_123"

    def test_update_nonexistent_agent_noop(self, tmp_path):
        write_manifest(feature="test", agents=[], worktree_root=tmp_path)
        manifest_path = get_manifest_path("test", tmp_path)
        # Should not raise
        update_agent_status(manifest_path, "nonexistent", "completed")


class TestFindAgent:
    def test_find_existing(self, tmp_path):
        write_manifest(
            feature="test",
            agents=[{"requested_id": "a_1", "role": "abm"}],
            worktree_root=tmp_path,
        )
        agent = find_agent(get_manifest_path("test", tmp_path), "a_1")
        assert agent is not None
        assert agent["role"] == "abm"

    def test_find_nonexistent_returns_none(self, tmp_path):
        write_manifest(feature="test", agents=[], worktree_root=tmp_path)
        agent = find_agent(get_manifest_path("test", tmp_path), "missing")
        assert agent is None
