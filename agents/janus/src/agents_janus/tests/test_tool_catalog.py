from types import SimpleNamespace

import pytest

from agents_janus.agent_config import AgentSpec, load_agent_configuration
from agents_janus.tool_catalog import resolve_tools


def test_resolver_returns_only_declared_tools():
    config = load_agent_configuration()
    spec = AgentSpec(
        name="scoring",
        kind="specialist",
        tools=("mcp__gitagent__read_file", "mcp__gitagent__edit_file"),
    )
    tools = [
        SimpleNamespace(name="mcp__gitagent__read_file"),
        SimpleNamespace(name="mcp__gitagent__edit_file"),
        SimpleNamespace(name="execute"),
    ]
    resolved = resolve_tools(tools, spec, config)
    assert {tool.name for tool in resolved} == {
        "mcp__gitagent__read_file",
        "mcp__gitagent__edit_file",
    }


def test_resolver_fails_on_missing_declared_tool():
    config = load_agent_configuration()
    spec = AgentSpec(
        name="x",
        kind="specialist",
        tools=("missing_tool",),
    )
    with pytest.raises(LookupError, match="missing_tool"):
        resolve_tools([], spec, config)


def test_resolver_recognizes_plain_function_tools():
    config = load_agent_configuration()
    spec = AgentSpec(name="x", kind="specialist", tools=("ask_user",))

    def ask_user(question: str) -> str:
        return question

    assert resolve_tools([ask_user], spec, config) == [ask_user]


def test_resolver_allows_missing_codebase_tools():
    config = load_agent_configuration()
    spec = AgentSpec(
        name="x",
        kind="specialist",
        tools=("codebase_search_graph",),
    )

    assert resolve_tools([], spec, config) == []
