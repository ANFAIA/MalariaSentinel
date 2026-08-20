"""mcp_bridge — Multi-server MCP bridge for Janus.

Loads agents.yaml, connects to configured MCP servers via MCP client
native client, converts tools to LangChain BaseTool objects.

Architecture:
  OpenCode agents → mcp__gitagent__* (MCP) → gawt MCP server → SQLite
  Janus subagents → mcp__gitagent__* (MCP) → gawt MCP server → SQLite
  Janus subagents → codebase_* (MCP) → codebase-memory-mcp → local DB

Session pool: persistent stdio sessions per MCP server, shared across all
tool calls. Avoids cold-start + initialize handshake (~3s) on every call.
"""
from __future__ import annotations

import atexit
import asyncio
import json
import logging
import os
import re
import shutil
import threading
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from langchain_core.tools import BaseTool

from agents_janus.mcp_config_schema import (
    JanusConfig,
    StdioServerConfig,
    HttpServerConfig,
    load_config,
    build_multiserver_dict,
)

_log = logging.getLogger("agents_janus.mcp_bridge")

_CONFIG_PATH = Path(__file__).parent / "config" / "agents.yaml"
_REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent.parent

# Per-config cache: tools_list for each unique config
_tools_cache: dict[frozenset, list[BaseTool]] = {}
_failed_servers: set[str] = set()
_MCP_CONNECT_TIMEOUT = float(os.environ.get("JANUS_MCP_CONNECT_TIMEOUT", "8"))


# ---------------------------------------------------------------------------
# Persistent MCP session pool
# ---------------------------------------------------------------------------

class _BackgroundLoopThread(threading.Thread):
    """Daemon thread running a single asyncio event loop for MCP sessions."""

    def __init__(self) -> None:
        super().__init__(daemon=True, name="mcp-session-loop")
        self.loop: asyncio.AbstractEventLoop = asyncio.new_event_loop()
        self.ready = threading.Event()

    def run(self) -> None:
        asyncio.set_event_loop(self.loop)
        self.ready.set()
        self.loop.run_forever()


@dataclass
class _PooledSession:
    """A persistent MCP session with its stdio transport kept alive."""
    session: Any  # ClientSession
    ctx: Any  # stdio_client context manager (must stay alive)
    server_params: Any  # StdioServerParameters
    lock: asyncio.Lock = field(default_factory=asyncio.Lock)


_loop_thread: _BackgroundLoopThread | None = None
_loop_lock = threading.Lock()
_session_pool: dict[str, _PooledSession] = {}
_pool_lock = threading.Lock()  # protects _session_pool dict (init is async though)

_STALE_ERRORS = (
    "BrokenPipeError", "ConnectionClosed", "EOFError",
    "broken pipe", "connection closed", "StreamReader",
)


def _ensure_loop_thread() -> _BackgroundLoopThread:
    """Return (or create) the singleton background event loop thread."""
    global _loop_thread
    with _loop_lock:
        if _loop_thread is None or not _loop_thread.is_alive():
            _loop_thread = _BackgroundLoopThread()
            _loop_thread.start()
            _loop_thread.ready.wait(timeout=5)
        return _loop_thread


async def _get_or_create_session(
    server_name: str,
    server_params: Any,
) -> _PooledSession:
    """Get a pooled session, or create one lazily via stdio_client."""
    bt = _ensure_loop_thread()
    # We must be on the background loop to reuse sessions
    if asyncio.get_running_loop() is not bt.loop:
        raise RuntimeError("_get_or_create_session called on wrong event loop")

    # Fast path: session exists and is healthy
    if server_name in _session_pool:
        return _session_pool[server_name]

    # Slow path: create session (cold start)
    from mcp import ClientSession
    from mcp.client.stdio import stdio_client

    ctx = stdio_client(server_params)
    read_stream, write_stream = await ctx.__aenter__()
    session = ClientSession(read_stream, write_stream)
    await session.__aenter__()
    await session.initialize()

    pooled = _PooledSession(
        session=session,
        ctx=ctx,
        server_params=server_params,
    )
    _session_pool[server_name] = pooled
    _log.info("MCP session pool: created persistent session for '%s'", server_name)
    return pooled


def _invalidate_session(server_name: str) -> None:
    """Drop a broken session from the pool. Next call will recreate it."""
    pooled = _session_pool.pop(server_name, None)
    if pooled is None:
        return
    _log.warning("MCP session pool: invalidating session for '%s'", server_name)
    # Best-effort close
    try:
        bt = _ensure_loop_thread()
        asyncio.run_coroutine_threadsafe(
            pooled.session.__aexit__(None, None, None), bt.loop
        ).result(timeout=2)
    except Exception:
        pass
    try:
        bt = _ensure_loop_thread()
        asyncio.run_coroutine_threadsafe(
            pooled.ctx.__aexit__(None, None, None), bt.loop
        ).result(timeout=2)
    except Exception:
        pass


def shutdown_all_sessions() -> None:
    """Close all pooled MCP sessions. Called at process exit."""
    for name in list(_session_pool):
        _invalidate_session(name)
    _log.info("MCP session pool: all sessions shut down")


atexit.register(shutdown_all_sessions)


def load_janus_config(path: Path | None = None) -> JanusConfig:
    """Load the MCP section of agents.yaml and fail on invalid configuration."""
    p = path or _CONFIG_PATH
    config = load_config(p)
    if not config.mcp_servers:
        raise ValueError(f"No MCP servers configured in {p}")
    return config


def _skip_disabled(config: JanusConfig) -> dict[str, StdioServerConfig | HttpServerConfig]:
    """Filter to enabled servers, auto-skip if binary not found for stdio servers."""
    active = {}
    for name, server in config.mcp_servers.items():
        if name in _failed_servers:
            _log.info("MCP server '%s' unavailable earlier — skipping for this process", name)
            continue
        if not getattr(server, "enabled", True):
            _log.info("MCP server '%s' disabled — skipping", name)
            continue
        if isinstance(server, StdioServerConfig):
            cmd_path = Path(server.command)
            if cmd_path.is_absolute() and not cmd_path.exists():
                _log.warning(
                    "MCP server '%s': binary '%s' not found — skipping silently",
                    name, server.command,
                )
                continue
            elif not cmd_path.is_absolute() and not shutil.which(server.command):
                _log.info(
                    "MCP server '%s': '%s' not on PATH (may work via uv/npx)",
                    name, server.command,
                )
        active[name] = server
    return active


def get_mcp_tools_sync(
    config: JanusConfig | None = None,
    project_root: Path | None = None,
) -> list[BaseTool]:
    """Get tools from all configured MCP servers (synchronous).

    Caches results per process. Returns LangChain BaseTool objects.
    """
    cfg = config or load_janus_config()
    root = project_root or _REPO_ROOT

    active = _skip_disabled(cfg)
    cache_key = frozenset(
        (k, repr(v.model_dump())) for k, v in active.items()
    )
    if cache_key in _tools_cache:
        return _tools_cache[cache_key]

    if not active:
        _log.info("No active MCP servers configured")
        return []

    ms_dict = build_multiserver_dict(cfg, project_root=root)
    _log.info(
        "Connecting to %d MCP server(s): %s",
        len(ms_dict), list(ms_dict.keys()),
    )

    async def _connect_all():
        """Connect to all servers, list tools, convert to BaseTool."""
        all_tools: list[BaseTool] = []
        for server_name, server_spec in ms_dict.items():
            try:
                # Determine prefix from tool_prefixes config
                prefix = cfg.tool_prefixes.get(server_name, "")
                tools = await _connect_server(server_name, server_spec, prefix=prefix)
                all_tools.extend(tools)
            except Exception as e:
                _failed_servers.add(server_name)
                _log.error("Failed to connect to MCP server '%s': %s", server_name, e)
        return all_tools

    try:
        raw_tools = asyncio.run(_connect_all())
        _log.info("Got %d tools from %d server(s)", len(raw_tools), len(ms_dict))

        # Tools already prefixed during _connect_server — no need for post-processing
        _tools_cache[cache_key] = raw_tools
        return raw_tools

    except Exception as e:
        _log.error("Multi-server MCP connection failed: %s", e)
        return []


async def _connect_server(name: str, spec: dict[str, Any], prefix: str = "") -> list[BaseTool]:
    """Connect to a single MCP server, list tools, convert to BaseTool."""
    try:
        from mcp import ClientSession, StdioServerParameters
        from mcp.client.stdio import stdio_client
    except ImportError:
        _log.error("mcp package not installed")
        return []

    if spec["transport"] == "stdio":
        env = os.environ.copy()
        env["PWD"] = str(spec.get("cwd", os.getcwd()))
        if "env" in spec:
            env.update(spec["env"])

        server_params = StdioServerParameters(
            command=spec["command"],
            args=spec.get("args", []),
            cwd=spec.get("cwd"),
            env=env,
        )

        async def _list_tools():
            async with stdio_client(server_params) as (read_stream, write_stream):
                async with ClientSession(read_stream, write_stream) as session:
                    await session.initialize()
                    result = await session.list_tools()
                    return result.tools

        try:
            mcp_tools = await asyncio.wait_for(_list_tools(), timeout=_MCP_CONNECT_TIMEOUT)
        except asyncio.TimeoutError:
            _failed_servers.add(name)
            _log.warning(
                "MCP server '%s' did not initialize within %.1fs — treating as unavailable",
                name,
                _MCP_CONNECT_TIMEOUT,
            )
            return []
        _log.info("Server '%s': %d tools", name, len(mcp_tools))

        return [_mcp_tool_to_langchain(name, t, server_params, prefix=prefix) for t in mcp_tools]

    raise ValueError(
        f"Server '{name}' transport '{spec['transport']}' is not implemented"
    )


def _mcp_tool_to_langchain(
    server_name: str,
    mcp_tool: Any,
    server_params: Any,
    prefix: str = "",
) -> BaseTool:
    """Convert an MCP tool to a LangChain BaseTool."""
    from langchain_core.tools import StructuredTool

    raw_name = mcp_tool.name
    display_name = f"{prefix}{raw_name}" if prefix else raw_name
    tool_description = mcp_tool.description or f"Call {display_name}"
    input_schema = mcp_tool.input_schema or {"type": "object", "properties": {}}

    async def _call_async(**kwargs: Any) -> str:
        """Call the MCP tool via a persistent pooled session, using the RAW tool name."""
        pooled = await _get_or_create_session(server_name, server_params)

        async def _attempt(p: _PooledSession) -> str:
            result = await p.session.call_tool(raw_name, kwargs)
            structured = getattr(result, "structuredContent", None)
            if structured is not None:
                return json.dumps(structured)
            if hasattr(result, "content") and result.content:
                texts = []
                for block in result.content:
                    if hasattr(block, "text"):
                        texts.append(block.text)
                return "\n".join(texts) if texts else str(result)
            return str(result)

        try:
            async with pooled.lock:
                return await _attempt(pooled)
        except Exception as e:
            err_name = type(e).__name__
            is_stale = any(
                err_name in s or str(e).lower().find(s.lower()) >= 0
                for s in _STALE_ERRORS
            )
            if not is_stale:
                raise
            # Stale session — invalidate and retry once
            _invalidate_session(server_name)
            pooled = await _get_or_create_session(server_name, server_params)
            async with pooled.lock:
                return await _attempt(pooled)

    def _run(**kwargs: Any) -> str:
        """Synchronous wrapper for MCP tool call via background event loop."""
        bt = _ensure_loop_thread()
        coro = _call_async(**kwargs)
        try:
            future = asyncio.run_coroutine_threadsafe(coro, bt.loop)
            result = future.result(timeout=30)
        except Exception as e:
            return f'{{"error": "{e}"}}'

        try:
            return json.dumps(json.loads(result))
        except (json.JSONDecodeError, TypeError):
            import ast
            try:
                parsed = ast.literal_eval(result)
                return json.dumps(parsed)
            except (ValueError, SyntaxError):
                return result

    return StructuredTool(
        name=display_name,
        description=tool_description,
        func=_run,
        args_schema=_build_args_schema(
            input_schema,
            hide_identity=server_name == "gitagent" and raw_name not in {
                "register_agent", "unregister_agent"
            },
        ),
    )


def _build_args_schema(schema: dict, *, hide_identity: bool = False) -> Any:
    """Convert JSON Schema to Pydantic model for LangChain tool args."""
    from pydantic import create_model, Field

    properties = schema.get("properties", {})
    required = set(schema.get("required", []))

    fields = {}
    for prop_name, prop_schema in properties.items():
        prop_type = prop_schema.get("type", "string")
        python_type = _json_type_to_python(prop_type)
        description = prop_schema.get("description", "")
        if hide_identity and prop_name in {"agent_id", "from_agent_id"}:
            python_type = python_type | None
            default = None
        else:
            default = ... if prop_name in required else None
        fields[prop_name] = (python_type, Field(description=description, default=default))

    if not fields:
        fields["unused"] = (str, Field(default="", exclude=True))

    return create_model("ArgsSchema", **fields)


def _json_type_to_python(json_type: str) -> type:
    mapping = {
        "string": str,
        "integer": int,
        "number": float,
        "boolean": bool,
        "array": list,
        "object": dict,
    }
    return mapping.get(json_type, str)


def _apply_prefixes(tools: list[BaseTool], prefixes: dict[str, str]) -> list[BaseTool]:
    """Rename tools: mcp__<server>__<tool> → <prefix><tool>."""
    pattern = re.compile(r"^mcp__([a-z0-9_]+)__(.+)$")
    for t in tools:
        m = pattern.match(t.name)
        if m:
            server_key, tool_name = m.group(1), m.group(2)
            if server_key in prefixes:
                t.name = f"{prefixes[server_key]}{tool_name}"
    return tools


def filter_gawt_tools(tools: list[BaseTool]) -> list[BaseTool]:
    """Filter to gawt v0.6.0 session-lifecycle, snapshot, and agent tools.

    The inbox (check_inbox/send_message) and finalize_session are gone in
    gawt 0.6.0; coordination now flows through the pheromone (edits log),
    per-file locks with informed reads, and partial snapshots.
    """
    gawt_names = {
        "start_session", "abort_session", "get_session", "list_sessions",
        "snapshot_session", "snapshot_status", "list_snapshots",
        "register_agent", "unregister_agent", "list_agents",
        "start_intent", "repurpose", "get_current_intent",
        "list_edits", "list_intents",
    }
    # Match both raw names and prefixed names (mcp__gitagent__<tool>)
    prefixed = {f"mcp__gitagent__{n}" for n in gawt_names}
    all_names = gawt_names | prefixed
    return [t for t in tools if t.name in all_names]


def filter_codebase_tools(tools: list[BaseTool]) -> list[BaseTool]:
    """Filter to codebase-memory-mcp tools (codebase_* prefix)."""
    return [t for t in tools if t.name.startswith("codebase_")]


async def ensure_index_on_startup(config: JanusConfig | None = None, project_root: Path | None = None) -> None:
    """Call index_repository via codebase MCP if index_on_startup.enabled."""
    cfg = config or load_janus_config()
    idx = cfg.index_on_startup
    if not idx.enabled:
        return

    root = project_root or _REPO_ROOT
    repo_path = idx.repo_path.replace("<repo_root>", str(root))

    tools = get_mcp_tools_sync(cfg, root)
    for t in tools:
        if t.name == "codebase_index_repository":
            try:
                _log.info("Indexing %s (project=%s, mode=%s)", repo_path, idx.project, idx.mode)
                t.invoke({
                    "repo_path": repo_path,
                    "project": idx.project,
                    "mode": idx.mode,
                    "force": idx.force,
                })
                _log.info("Index complete (idempotent — no-op if already fresh)")
            except Exception as e:
                _log.warning("index_repository failed (likely already indexed): %s", e)
            return

    _log.info("index_on_startup enabled but no codebase_index_repository tool found — skipping")
