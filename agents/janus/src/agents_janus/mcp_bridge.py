"""mcp_bridge — Connect deepagents subagents to gawt MCP server.

Uses the mcp 2.0.0 native client SDK to connect to the gawt MCP server
via stdio. Tools are cached as LangChain BaseTool objects.

Architecture:
  OpenCode agents → mcp__gitagent__* (MCP) → gawt MCP server → SQLite
  Janus subagents → mcp__gitagent__* (MCP) → gawt MCP server → SQLite

Both share the same SQLite database (.gitagent/state.db), so session
state is visible across all connections.
"""
from __future__ import annotations

import asyncio
import logging
import os
from pathlib import Path
from typing import Any

from langchain_core.tools import BaseTool

_log = logging.getLogger("agents_janus.mcp_bridge")

# Cache for converted LangChain tools (not the MCP session)
_tools_cache: list[BaseTool] | None = None


def get_gawt_mcp_tools_sync() -> list[BaseTool]:
    """Get gawt MCP tools synchronously.

    Opens a temporary MCP session, lists tools, converts them to
    LangChain BaseTool objects, and closes the session.
    """
    global _tools_cache

    if _tools_cache is not None:
        return _tools_cache

    try:
        from mcp import ClientSession, StdioServerParameters
        from mcp.client.stdio import stdio_client
    except ImportError:
        _log.error("mcp package not installed")
        return []

    repo_root = Path(__file__).resolve().parent.parent.parent.parent.parent
    env = os.environ.copy()
    env["PWD"] = str(repo_root)
    # Suppress MCP server stderr output
    env["MCP_LOG_LEVEL"] = "ERROR"

    server_params = StdioServerParameters(
        command="uv",
        args=["run", "gitagent-mcp"],
        cwd=str(repo_root),
        env=env,
    )

    async def _connect_and_list():
        """Connect to MCP server, list tools, return converted tools."""
        async with stdio_client(server_params) as (read_stream, write_stream):
            async with ClientSession(read_stream, write_stream) as session:
                await session.initialize()
                tools_result = await session.list_tools()
                return tools_result.tools

    try:
        mcp_tools = asyncio.run(_connect_and_list())
        _log.info("Found %d MCP tools from gawt server", len(mcp_tools))

        # Convert MCP tools to LangChain BaseTool objects (no session needed)
        _tools_cache = [_mcp_tool_to_langchain(t) for t in mcp_tools]
        return _tools_cache

    except Exception as e:
        _log.error("Failed to connect to gawt MCP server: %s", e)
        return []


def _mcp_tool_to_langchain(mcp_tool: Any) -> BaseTool:
    """Convert an MCP tool to a LangChain BaseTool.

    The returned tool calls the gawt MCP server via a temporary session.
    """
    from langchain_core.tools import StructuredTool
    from mcp import ClientSession, StdioServerParameters
    from mcp.client.stdio import stdio_client

    tool_name = mcp_tool.name
    tool_description = mcp_tool.description or f"Call {tool_name}"
    input_schema = mcp_tool.input_schema or {"type": "object", "properties": {}}

    repo_root = Path(__file__).resolve().parent.parent.parent.parent.parent
    env = os.environ.copy()
    env["PWD"] = str(repo_root)
    env["MCP_LOG_LEVEL"] = "ERROR"

    server_params = StdioServerParameters(
        command="uv",
        args=["run", "gitagent-mcp"],
        cwd=str(repo_root),
        env=env,
    )

    async def _call_async(**kwargs: Any) -> str:
        """Call the MCP tool via a temporary session."""
        async with stdio_client(server_params) as (read_stream, write_stream):
            async with ClientSession(read_stream, write_stream) as session:
                await session.initialize()
                result = await session.call_tool(tool_name, kwargs)

                # Extract text content from result
                if hasattr(result, "content") and result.content:
                    texts = []
                    for block in result.content:
                        if hasattr(block, "text"):
                            texts.append(block.text)
                    return "\n".join(texts) if texts else str(result)
                return str(result)

    def _run(**kwargs: Any) -> str:
        """Synchronous wrapper for MCP tool call."""
        try:
            result = asyncio.run(_call_async(**kwargs))
            # MCP server returns Python dict repr, not JSON
            # Try JSON first, fall back to ast.literal_eval
            try:
                import json
                return json.dumps(json.loads(result))
            except (json.JSONDecodeError, TypeError):
                import ast
                try:
                    parsed = ast.literal_eval(result)
                    return json.dumps(parsed)
                except (ValueError, SyntaxError):
                    return result
        except Exception as e:
            return f'{{"error": "{e}"}}'

    return StructuredTool(
        name=tool_name,
        description=tool_description,
        func=_run,
        args_schema=_build_args_schema(input_schema),
    )


def _build_args_schema(schema: dict) -> Any:
    """Convert JSON Schema to Pydantic model for LangChain tool args."""
    from pydantic import create_model, Field

    properties = schema.get("properties", {})
    required = set(schema.get("required", []))

    fields = {}
    for prop_name, prop_schema in properties.items():
        prop_type = prop_schema.get("type", "string")
        python_type = _json_type_to_python(prop_type)
        description = prop_schema.get("description", "")
        default = ... if prop_name in required else None
        fields[prop_name] = (python_type, Field(description=description, default=default))

    if not fields:
        fields["unused"] = (str, Field(default="", exclude=True))

    return create_model("ArgsSchema", **fields)


def _json_type_to_python(json_type: str) -> type:
    """Map JSON Schema type to Python type."""
    mapping = {
        "string": str,
        "integer": int,
        "number": float,
        "boolean": bool,
        "array": list,
        "object": dict,
    }
    return mapping.get(json_type, str)


def filter_gawt_tools(tools: list[BaseTool]) -> list[BaseTool]:
    """Filter tools to only include gawt MCP tools."""
    gawt_names = {
        "start_session", "finalize_session", "abort_session", "get_session",
        "register_agent", "unregister_agent", "list_agents",
        "start_intent", "repurpose", "get_current_intent",
        "edit_file", "write_file", "read_file", "delete_file",
        "check_inbox", "send_message", "list_edits", "list_intents",
    }
    return [t for t in tools if t.name in gawt_names]
