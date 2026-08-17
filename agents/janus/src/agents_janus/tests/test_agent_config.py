from pathlib import Path

import pytest

from agents_janus.agent_config import load_agent_configuration


def test_single_declarative_config_loads():
    config = load_agent_configuration()
    assert "gitagent" in config.servers
    assert config.agents["abm"].effective_gawt_role == "abm"
    assert "mcp__gitagent__edit_file" in config.agents["abm"].tools


def test_unknown_server_is_rejected(tmp_path: Path):
    path = tmp_path / "agents.yaml"
    path.write_text(
        "version: 1\nservers: {}\nagents:\n  x:\n    kind: specialist\n    servers: [missing]\n"
    )
    with pytest.raises(ValueError, match="unknown MCP servers"):
        load_agent_configuration(path)


def test_coordinator_edit_tool_is_rejected(tmp_path: Path):
    path = tmp_path / "agents.yaml"
    path.write_text(
        "version: 1\nservers: {}\nagents:\n  x:\n    kind: coordinator\n    tools: [mcp__gitagent__write_file]\n"
    )
    with pytest.raises(ValueError, match="cannot receive edit tools"):
        load_agent_configuration(path)
