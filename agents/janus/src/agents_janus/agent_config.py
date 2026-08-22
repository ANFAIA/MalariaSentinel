"""Strict declarative configuration for Janus agents and MCP servers."""
from __future__ import annotations

from pathlib import Path
from typing import Any, Literal

import yaml
from pydantic import BaseModel, ConfigDict, Field, model_validator

from agents_janus.mcp_config_schema import JanusConfig


class AgentDefaults(BaseModel):
    model_config = ConfigDict(extra="forbid")

    provider: str = "openrouter"
    model: str = "xiaomi/mimo-v2.5"
    thread_id_prefix: str = "sub-"
    tool_name_prefix: bool = True
    default_deny: bool = True
    fail_on_missing_tools: bool = True
    global_deny_tools: list[str] = Field(default_factory=list)


class AgentSpec(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str
    kind: Literal["coordinator", "specialist"]
    description: str = ""
    model: str | None = None
    provider: str | None = None
    spec: Path | None = None
    skills: tuple[str, ...] = ()
    gawt_role: str = ""
    servers: tuple[str, ...] = ()
    tools: tuple[str, ...] = ()
    deny_tools: tuple[str, ...] = ()
    edits_allow: tuple[str, ...] = ()
    edits_deny: tuple[str, ...] = ()
    middleware: tuple[str, ...] = ()
    thread_id_prefix: str | None = None

    @property
    def effective_gawt_role(self) -> str:
        return self.gawt_role or self.name


class AgentConfiguration(BaseModel):
    model_config = ConfigDict(extra="forbid")

    version: int = Field(ge=1)
    defaults: AgentDefaults = Field(default_factory=AgentDefaults)
    servers: dict[str, dict[str, Any]]
    agents: dict[str, AgentSpec]
    index_on_startup: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_references(self) -> "AgentConfiguration":
        server_names = set(self.servers)
        for name, spec in self.agents.items():
            if set(spec.servers) - server_names:
                missing = sorted(set(spec.servers) - server_names)
                raise ValueError(f"{name}: unknown MCP servers: {missing}")
            if spec.kind == "coordinator" and any(
                "write_file" in tool or "edit_file" in tool or "delete_file" in tool
                for tool in spec.tools
            ):
                raise ValueError(f"{name}: coordinator cannot receive edit tools")
        return self


def load_agent_configuration(path: str | Path | None = None) -> AgentConfiguration:
    config_path = Path(path) if path else Path(__file__).parent / "config" / "agents.yaml"
    if not config_path.exists():
        raise FileNotFoundError(f"Janus agent config not found: {config_path}")
    raw = yaml.safe_load(config_path.read_text()) or {}
    raw_agents = raw.get("agents", {})
    defaults = raw.get("defaults", {})
    agents: dict[str, AgentSpec] = {}
    for name, entry in raw_agents.items():
        entry = dict(entry or {})
        entry.setdefault("name", name)
        entry.setdefault("model", defaults.get("model"))
        entry.setdefault("provider", defaults.get("provider"))
        entry.setdefault("thread_id_prefix", defaults.get("thread_id_prefix"))
        agents[name] = AgentSpec.model_validate(entry)

    configuration = AgentConfiguration.model_validate({**raw, "agents": agents})
    # Validate MCP server models with the existing transport schema.
    JanusConfig.model_validate({"mcp_servers": configuration.servers})
    return configuration
