---
name: social-networks-agent
description: Deep Agent for social networks content generation. Generates LinkedIn posts, video scripts, carousels, transcribes audio, renders HyperFrames compositions. Primary communication point for all social content.
---

# Social Networks Agent

A specialised Deep Agent that handles all social media content creation for MalariaSentinel and future projects.

## Capabilities

- **LinkedIn posts** — Bilingual (EN + ES) posts with honest tone, no hype
- **Video compositions** — HyperFrames HTML/GSAP animations rendered to MP4
- **PDF carousels** — Extract hero frames and build LinkedIn carousel PDFs
- **Audio transcription** — Local Parakeet v3 via sherpa-onnx (no cloud APIs)
- **Content from audio** — Generate social content from transcribed recordings

## When to use

- User wants to create social media content for a project
- User says "write a LinkedIn post", "make a video", "transcribe this audio"
- User needs to generate content from a recording or project description
- User wants to render a HyperFrames composition

## How to invoke

From another agent or script:

```python
from social_networks.agent.main import create_agent

agent = create_agent(model="anthropic:claude-sonnet-4-5-20250929")
result = agent.invoke(
    {"messages": [{"role": "user", "content": "Write a LinkedIn post about MalariaSentinel"}]},
    config={"configurable": {"thread_id": "my-session"}},
)
```

Or run the CLI directly:

```bash
cd social-networks/agent && python run.py
```

## Skills loaded

The agent automatically loads skills from:
- `social-networks/skills/` — project-specific skills (linkedin-post, video-composition, audio-to-content)
- `~/.agents/skills/` — global skills (hyperframes, etc.)

## Files

- `__init__.py` — package marker
- `main.py` — agent definition and `create_agent()` function
- `tools.py` — custom tools (transcribe, render, check, LinkedIn post)
- `run.py` — interactive CLI entrypoint
- `SKILL.md` — this file (for discovery by other agents)
