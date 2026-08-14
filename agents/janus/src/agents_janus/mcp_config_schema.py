"""Pydantic models for janus.json MCP server configuration."""
from __future__ import annotations

from pathlib import Path
from typing import Any, Literal
from pydantic import BaseModel, Field


class StdioServerConfig(BaseModel):
    transport: Literal["stdio"]
    command: str = Field(..., description="Command to run (e.g. 'uv', '/path/to/binary')")
    args: list[str] = Field(default_factory=list)
    cwd: str | None = Field(default=None, description="Working directory")
    env: dict[str, str] = Field(default_factory=dict)
    enabled: bool = True


class HttpServerConfig(BaseModel):
    transport: Literal["http"]
    url: str = Field(..., description="HTTP endpoint (e.g. http://localhost:8000/mcp)")
    headers: dict[str, str] = Field(default_factory=dict)
    enabled: bool = True


McpServerConfig = StdioServerConfig | HttpServerConfig


class ToolPrefix(BaseModel):
    server: str = Field(..., description="Server key in mcp_servers")
    prefix: str = Field(..., description="Tool name prefix (e.g. 'codebase_')")


class IndexOnStartupConfig(BaseModel):
    enabled: bool = True
    project: str = Field(default="MalariaSentinel", description="Project name for index_repository")
    repo_path: str = Field(default="<repo_root>", description="Repo path (resolve <repo_root> at runtime)")
    mode: Literal["full", "moderate", "fast"] = Field(default="moderate")
    force: bool = False


class JanusConfig(BaseModel):
    mcp_servers: dict[str, StdioServerConfig | HttpServerConfig] = Field(default_factory=dict)
    index_on_startup: IndexOnStartupConfig = Field(default_factory=IndexOnStartupConfig)
    tool_prefixes: dict[str, str] = Field(
        default_factory=lambda: {
            "codebase_memory": "codebase_",
            "gitagent": "mcp__gitagent__",
        },
        description="Map server_key → tool_prefix. Renames mcp__<server>__<tool> → <prefix><tool>",
    )


def load_config(path: str | Path) -> JanusConfig:
    """Load and validate janus.json."""
    import json
    from pathlib import Path

    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"Config not found: {p}")
    return JanusConfig.model_validate_json(p.read_text())


def build_multiserver_dict(config: JanusConfig, *, project_root: str | Path | None = None) -> dict[str, dict[str, Any]]:
    """Build the dict that MultiServerMCPClient expects, resolving <repo_root> and filtering disabled."""
    result: dict[str, dict[str, Any]] = {}
    for name, server in config.mcp_servers.items():
        if not getattr(server, "enabled", True):
            continue
        spec: dict[str, Any] = {"transport": server.transport}
        if isinstance(server, StdioServerConfig):
            spec["command"] = server.command
            spec["args"] = list(server.args)
            if server.cwd:
                spec["cwd"] = server.cwd.replace("<repo_root>", str(project_root or ""))
            if server.env:
                spec["env"] = dict(server.env)
        elif isinstance(server, HttpServerConfig):
            spec["url"] = server.url
            if server.headers:
                spec["headers"] = dict(server.headers)
        result[name] = spec
    return result
