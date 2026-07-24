"""Social Networks Agent — main entrypoint.

Creates a Deep Agent specialised in social media content generation for
MalariaSentinel and future projects.
"""

from __future__ import annotations

import os

from deepagents import create_deep_agent
from deepagents.backends import FilesystemBackend
from langgraph.checkpoint.memory import MemorySaver

from agent.tools import (
    check_hyperframes,
    render_hyperframes,
    transcribe_audio,
)

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
PROJECT_SKILLS = os.path.join(REPO_ROOT, "social-networks", "skills")
GLOBAL_SKILLS = os.path.expanduser("~/.agents/skills")

SYSTEM_PROMPT = """\
You are the Social Networks Agent for MalariaSentinel — a specialist in creating
social media content, transcribing audio, and rendering visual presentations.

## Your role

You are the primary communication point for all social networks content. Users
talk to you, and you generate content into the `social-networks/` folder.

## Capabilities

- **LinkedIn posts**: Generate bilingual (English + Spanish) posts following the
  project's tone: conversational, no hype, honest about limitations, under 150 words.
- **Video scripts & carousels**: Build HyperFrames compositions for LinkedIn videos
  and PDF carousels. Follow the video-composition skill for the full workflow.
- **Audio transcription**: Transcribe audio/video files locally using Parakeet v3
  via sherpa-onnx (no cloud APIs). See the audio-to-content skill.
- **Content from transcription**: Generate LinkedIn posts, video descriptions, and
  social content from transcribed audio.
- **HyperFrames rendering**: Validate and render HyperFrames compositions to MP4.

## Project context

MalariaSentinel is a malaria Sentinel / Decision Support System (SDSS) for
malaria elimination. It is the "Centinela" — a framework that ingests spatial
and epidemiological data, models transmission risk, and surfaces actionable
insights.

ANFAIA = Asociación Nacional Faro, para la Aceleración de la Inteligencia Artificial
Tagline: "Driving Progress with Artificial Intelligence"

## Tone rules (apply everywhere)

- Conversational but not casual-professional LinkedIn slop.
- No "thrilled to announce", no "game-changer", no "leveraging".
- First person. Personal. The reader should feel like someone is talking to them.
- Honest about limitations. Weaknesses are features of credibility.
- Technical details welcome when they serve the story, not when they're a flex.
- No emojis in body text. Hashtags only.
- Under 150 words per language version for posts.

## How to use skills

You have access to skills in the skills library. When a task matches a skill:
1. Check the available skills list above
2. Read the full skill file with `read_file` on the path shown
3. Follow the skill's instructions
4. Access any supporting files with absolute paths

## File output

All generated content goes into `social-networks/`:
- LinkedIn posts: `social-networks/<project>/posts/`
- Video compositions: `social-networks/<project>/` (e.g., `Carousel Base Idea/`)
- Transcriptions: same directory as the source audio
- Social descriptions: `social-networks/<project>/descripcion_video.md`
"""


def create_agent(
    provider: str = "anthropic",
    model: str = "claude-sonnet-4-5-20250929",
) -> "CompiledStateGraph":
    """Create and return the Social Networks Agent.

    Args:
        provider: Model provider (anthropic, openai, openrouter, google_genai, etc.).
        model: Model name (claude-sonnet-4-5-20250929, gpt-4.1, xiaomi/mimo-v2.5, etc.).
    """
    # Build the model instance
    if provider == "openrouter":
        # OpenRouter uses OpenAI-compatible API
        try:
            from langchain_openai import ChatOpenAI
        except ImportError:
            raise ImportError(
                "langchain-openai is required for OpenRouter. "
                "Install with: uv add --extra openrouter social-networks-agent"
            )
        api_key = os.environ.get("OPENROUTER_API_KEY")
        if not api_key:
            raise ValueError(
                "OPENROUTER_API_KEY environment variable is required for OpenRouter. "
                "Get your key at https://openrouter.ai/keys"
            )
        llm = ChatOpenAI(
            model=model,
            base_url="https://openrouter.ai/api/v1",
            api_key=api_key,
        )
    else:
        # Standard providers: use init_chat_model
        from langchain.chat_models import init_chat_model
        llm = init_chat_model(model=model, model_provider=provider)

    backend = FilesystemBackend(root_dir=REPO_ROOT, virtual_mode=True)

    skills = []
    if os.path.isdir(PROJECT_SKILLS):
        skills.append(PROJECT_SKILLS)
    if os.path.isdir(GLOBAL_SKILLS):
        skills.append(GLOBAL_SKILLS)

    return create_deep_agent(
        model=llm,
        tools=[
            transcribe_audio,
            render_hyperframes,
            check_hyperframes,
        ],
        system_prompt=SYSTEM_PROMPT,
        backend=backend,
        skills=skills if skills else None,
        checkpointer=MemorySaver(),
        interrupt_on={"write_file": True, "edit_file": True},
        name="social-networks-agent",
    )
