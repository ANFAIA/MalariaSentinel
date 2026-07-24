---
name: deep-agent-scaffold
description: Scaffold a new Deep Agent with skills, CLI, and provider/model selection. Use when creating a new deep agent, setting up agent tools, configuring skills loading, or building agent CLIs.
---

# Deep Agent Scaffold

Step-by-step to create a Deep Agent (`deepagents` v0.6+).

## Directory structure

```
<project-dir>/
├── pyproject.toml
├── <agent-pkg>/
│   ├── __init__.py
│   ├── main.py        # create_agent() + system prompt
│   ├── tools.py       # custom @tool functions
│   ├── run.py         # CLI entrypoint
│   └── SKILL.md       # discovery metadata
└── skills/            # project-specific skills (subdirs with SKILL.md)
```

## pyproject.toml

```toml
[project]
name = "<agent-name>"
version = "0.1.0"
requires-python = ">=3.12"
dependencies = [
    "deepagents>=0.6",
    "langgraph>=0.4",
    "langchain-core>=0.3",
]

[project.optional-dependencies]
openrouter = ["langchain-openai>=0.3"]

[project.scripts]
<cmd> = "<pkg>.run:main"

[tool.hatch.build.targets.wheel]
packages = ["<pkg>"]

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"
```

Add to root pyproject.toml workspace members.

## main.py

```python
from __future__ import annotations
import os
from deepagents import create_deep_agent
from deepagents.backends import FilesystemBackend
from langgraph.checkpoint.memory import MemorySaver

AGENT_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.abspath(os.path.join(AGENT_DIR, "..", ".."))
PROJECT_SKILLS = os.path.join(REPO_ROOT, "<project>", "skills")
GLOBAL_SKILLS = os.path.expanduser("~/.agents/skills")

SYSTEM_PROMPT = """You are..."""

def create_agent(provider: str = "anthropic", model: str = "..."):
    if provider == "openrouter":
        from langchain_openai import ChatOpenAI
        api_key = os.environ.get("OPENROUTER_API_KEY")
        if not api_key:
            raise ValueError("OPENROUTER_API_KEY env var required")
        llm = ChatOpenAI(model=model, base_url="https://openrouter.ai/api/v1", api_key=api_key)
    else:
        from langchain.chat_models import init_chat_model
        llm = init_chat_model(model=model, model_provider=provider)

    backend = FilesystemBackend(root_dir=REPO_ROOT, virtual_mode=False)

    skills = []
    if os.path.isdir(PROJECT_SKILLS): skills.append(PROJECT_SKILLS)
    if os.path.isdir(GLOBAL_SKILLS): skills.append(GLOBAL_SKILLS)

    return create_deep_agent(
        model=llm, tools=[...], system_prompt=SYSTEM_PROMPT,
        backend=backend, skills=skills or None,
        checkpointer=MemorySaver(),
        interrupt_on={"write_file": True, "edit_file": True},
        name="<agent-name>",
    )
```

## run.py

```python
#!/usr/bin/env python3
from __future__ import annotations
import argparse

def main():
    parser = argparse.ArgumentParser(description="...")
    parser.add_argument("--provider", default="anthropic")
    parser.add_argument("--model", default="...")
    parser.add_argument("--thread-id", default="cli-session")
    args = parser.parse_args()

    from <pkg>.main import create_agent
    agent = create_agent(provider=args.provider, model=args.model)
    config = {"configurable": {"thread_id": args.thread_id}}

    try:
        while True:
            user_input = input("You: ").strip()
            if not user_input: continue
            if user_input.lower() in ("quit", "exit", "q"): break
            result = agent.invoke({"messages": [{"role": "user", "content": user_input}]}, config=config)
            if result and "messages" in result:
                msg = result["messages"][-1]
                content = getattr(msg, "content", None)
                if content: print(f"\nAgent: {content}\n")
    except KeyboardInterrupt:
        print("\n\nExiting.")

if __name__ == "__main__":
    main()
```

## Tools

```python
from langchain_core.tools import tool

@tool
def my_tool(param: str) -> str:
    """Description for the LLM."""
    return result
```

## Skills format

Each skill = subdirectory with SKILL.md:
```
skills/<name>/SKILL.md    # Required: YAML frontmatter + instructions
skills/<name>/helper.py   # Optional
```

Frontmatter:
```yaml
---
name: my-skill
description: What it does. When to trigger.
---
```

## Gotchas

1. **virtual_mode=True blocks absolute paths and ~** — Global skills at ~/.agents/skills need `virtual_mode=False`.

2. **Flat .md files don't load** — SkillsMiddleware scans subdirs for SKILL.md. Use `skills/<name>/SKILL.md`.

3. **YAML colons in description break parsing** — Wrap in quotes: `description: 'text with: colons'`

4. **OpenRouter ≠ standard provider** — Use `ChatOpenAI(base_url="https://openrouter.ai/api/v1")`. Standard providers use `init_chat_model`.

5. **Hyphenated dirs break Python imports** — Use `[tool.hatch.build.targets.wheel] packages = ["<pkg>"]`.

6. **Relative imports break in CLI** — `from .main import` fails with `python run.py`. Use absolute imports after package install.

## Provider reference

| Provider | Package | Example model |
|---|---|---|
| anthropic | langchain-anthropic | claude-sonnet-4-5-20250929 |
| openai | langchain-openai | gpt-4.1 |
| openrouter | langchain-openai | xiaomi/mimo-v2.5 |
| google_genai | langchain-google-genai | gemini-2.5-flash |
