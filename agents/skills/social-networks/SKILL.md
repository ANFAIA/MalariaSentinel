---
name: social-networks
description: Deep Agent for social networks content generation. Use when generating malaria-related content for social media, creating educational materials, or managing social media presence for the Centinela project.
---

# Social Networks Agent

Deep Agent for generating social networks content related to MalariaSentinel. This agent creates educational and promotional content for social media platforms about malaria surveillance and elimination.

## Overview

The `social-networks` package is a LangGraph-based Deep Agent that generates content for social media platforms. It uses LangChain's agent framework with OpenAI/OpenRouter models.

## Package Location

```
social-networks/
├── agent/              # Main agent code
│   ├── __init__.py
│   ├── main.py         # Agent core logic
│   ├── run.py          # CLI entrypoint
│   ├── tools.py        # Tool definitions
│   └── SKILL.md        # This skill (in-package copy)
├── skills/             # Agent skills directory
├── pyproject.toml      # Package configuration
└── Carousel Base Idea/ # Content templates
```

## Quick Start

```bash
# Install dependencies
cd social-networks
uv sync

# Run the agent
uv run python -m agent.run

# Or via CLI entrypoint
social-agent
```

## Dependencies

| Package | Purpose |
|---|---|
| `deepagents>=0.6` | Deep Agent framework |
| `langgraph>=0.4` | LangGraph for agent orchestration |
| `langchain-core>=0.3` | LangChain core utilities |
| `langchain-openai>=0.3` | OpenAI integration |

### Optional Dependencies

```bash
# OpenRouter support
uv sync --extras openrouter

# Transcription support
uv sync --extras transcribe

# All extras
uv sync --extras all
```

## Configuration

### Environment Variables

| Variable | Required | Description |
|---|---|---|
| `OPENAI_API_KEY` | Yes (or OpenRouter) | OpenAI API key |
| `OPENROUTER_API_KEY` | Optional | OpenRouter API key (if using OpenRouter) |

## Usage

### Content Generation

The agent generates social media content about:
- Malaria prevention and awareness
- Centinela project updates
- Data visualizations and findings
- Educational threads about vector control
- Community engagement posts

### Tools Available

The agent has access to tools defined in `agent/tools.py`:
- Content generation tools
- Image/media handling
- Social media formatting
- Template management

## Agent Architecture

The agent uses LangGraph for state management and tool orchestration:

```python
from agent.main import create_agent

agent = create_agent()
result = agent.invoke({"input": "Generate a thread about malaria prevention"})
```

## Content Templates

Templates are stored in `Carousel Base Idea/` directory:
- Carousel formats for Instagram/LinkedIn
- Thread formats for Twitter/X
- Educational infographic templates
- Video script templates

## Integration with MalariaSentinel

This agent is part of the broader MalariaSentinel ecosystem:
- Uses data from `mal-data-explorer` for visualizations
- References findings from `mal-core` predictions
- Promotes the Centinela SDSS framework
- Supports the Kelly et al. 2012 SDSS methodology

## Related Skills

| Skill | Use when |
|---|---|
| `data-explorer` | Creating visualizations from datasets |
| `mal-core-api` | Accessing prediction data |
| `sdss-reference` | Understanding the domain context |
| `project-setup` | Setting up the workspace |

## Troubleshooting

### Import Errors

```bash
# Ensure workspace is synced
cd /path/to/MalariaSentinel
uv sync --all-packages

# Verify social-networks imports
uv run python -c "import social_networks_agent; print('OK')"
```

### API Key Issues

```bash
# Verify OpenAI key
echo $OPENAI_API_KEY

# Test connection
curl https://api.openai.com/v1/models -H "Authorization: Bearer $OPENAI_API_KEY"
```

### Model Not Found

Ensure you're using a supported model. The agent defaults to `gpt-4` or can be configured to use OpenRouter models via `OPENROUTER_API_KEY`.

## Development

### Adding New Content Types

1. Define new tools in `agent/tools.py`
2. Update the agent prompt in `agent/main.py`
3. Add templates to `Carousel Base Idea/`
4. Test with `uv run python -m agent.run`

### Running Tests

```bash
cd social-networks
uv run pytest
```
