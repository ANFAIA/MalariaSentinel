# social-networks — Outreach Content

Deep-agent workspace for generating MalariaSentinel outreach content
(social posts, videos) from project artifacts.

## Layout

| Path | Purpose |
|---|---|
| `agent/` | The content-generation deep agent (`main.py`, `run.py`, `tools.py`, `SKILL.md`) |
| `skills/` | Composable skills: `linkedin-post`, `audio-to-content`, `video-composition` |
| `MalariaSentinel ABM Video/` | ABM explainer video project (assets + composition) |
| `Janus Video/` | Janus agent video project |
| `Carousel Base Idea/` | LinkedIn carousel drafts |
| `assets/`, `fonts/` | Shared media and typography |
| `design.md` | Visual design guide |

## Usage

```bash
uv sync --all-packages
# See agent/SKILL.md and the skill folders for the exact invocation of each flow
```

This package is outreach-only: it never modifies pipeline code or data.
