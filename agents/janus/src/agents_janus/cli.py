"""CLI entry point for the MalariaSentinel Janus system.

Two entry points:
    janus              — Request router REPL
    janus improve      — Implementation coordinator
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

_project_root = Path(__file__).resolve().parent.parent.parent
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))

import typer

app = typer.Typer(
    name="janus",
    help=(
        "MalariaSentinel Janus — multi-agent decision support system.\n\n"
        "Two entry points:\n"
        "  janus          Request router: routes each request to a coordinator.\n"
        "  janus improve  Implementation coordinator: edits through GAWT,\n"
        "                 manages gawt sessions, and finalizes changes.\n\n"
        "Run with no arguments to start the request router REPL."
    ),
    no_args_is_help=False,
)


@app.callback(invoke_without_command=True)
def _main(
    ctx: typer.Context,
    no_tracing: bool = typer.Option(
        False, "--no-tracing",
        help="Disable Langfuse tracing (enabled by default).",
    ),
    no_codebase_index: bool = typer.Option(
        False, "--no-codebase-index",
        help="Skip codebase-memory-mcp index_repository on startup.",
    ),
    env: str = typer.Option(
        "", "--env",
        help="Environment tag: dev, staging, production.",
    ),
) -> None:
    """Start the request router REPL for the SDSS.

    The research coordinator can:
    - Run ABM simulations and pipeline stages
    - Ask specialists about their domain
    - Investigate issues by dispatching research specialists
    The implementation coordinator handles repository changes.

    Langfuse tracing is ON by default. Each session creates a trace with
    nested spans for LLM calls, tool calls, and specialist dispatches.
    Use --no-tracing to disable.

    Language: responds in the same language you use (Spanish or English).
    """
    import agents_janus.agent as agent_mod
    agent_mod.CODEBASE_INDEX_ON_STARTUP = not no_codebase_index

    if ctx.invoked_subcommand is None:
        from agents_janus.onboarding import run_onboarding

        tracing = "" if no_tracing else "langfuse"
        langfuse_client = _build_langfuse_client(tracing)
        resolved_env = _resolve_env(env)

        run_onboarding(langfuse_client=langfuse_client, env=resolved_env)


def _load_dotenv() -> None:
    """Load .env from cwd or any parent dir into os.environ (no override)."""
    for parent in [Path.cwd(), *Path.cwd().parents]:
        candidate = parent / ".env"
        if candidate.is_file():
            try:
                for raw in candidate.read_text().splitlines():
                    line = raw.strip()
                    if not line or line.startswith("#"):
                        continue
                    if "=" not in line:
                        continue
                    key, _, value = line.partition("=")
                    key = key.strip()
                    value = value.strip().strip('"').strip("'")
                    os.environ.setdefault(key, value)
            except OSError:
                pass
            return


_load_dotenv()


def _setup_module_flags(no_verify: bool) -> None:
    """Configure module-level flags based on CLI options."""
    import agents_janus.agent as agent_mod
    agent_mod.VERIFY_FINALIZE = not no_verify


def _resolve_tracing(tracing: str | None) -> str:
    """Resolve tracing backend from CLI flag or JANUS_TRACING env var."""
    return tracing or os.environ.get("JANUS_TRACING", "")


def _build_langfuse_client(tracing: str):
    """Build a langfuse.Langfuse client.

    By default tracing is enabled. Pass --no-tracing to disable.
    If env vars are missing, tracing degrades gracefully (no crash).
    """
    if tracing != "langfuse":
        return None
    try:
        from langfuse import Langfuse
    except ImportError:
        typer.echo(
            "Warning: langfuse not installed. Tracing disabled. "
            "Install with: uv pip install -e 'agents/janus[observability]'",
            err=True,
        )
        return None

    host = os.environ.get("LANGFUSE_HOST") or os.environ.get("LANGFUSE_BASE_URL")
    public_key = os.environ.get("LANGFUSE_PUBLIC_KEY")
    secret_key = os.environ.get("LANGFUSE_SECRET_KEY")
    if not (host and public_key and secret_key):
        typer.echo(
            "Warning: Langfuse env vars not set (LANGFUSE_HOST, "
            "LANGFUSE_PUBLIC_KEY, LANGFUSE_SECRET_KEY). Tracing disabled.",
            err=True,
        )
        return None

    return Langfuse(
        public_key=public_key,
        secret_key=secret_key,
        host=host,
    )


def _resolve_env(env: str | None) -> str:
    """Resolve environment from CLI flag or JANUS_ENV env var."""
    return env or os.environ.get("JANUS_ENV", "dev")


@app.command()
def improve(
    goal: str = typer.Option(
        None, "--goal", "-g",
        help="Goal for the implementation coordinator to accomplish.",
    ),
    plan: str = typer.Option(
        None, "--plan",
        help="Path to a plan file. The implementation coordinator reads it for task decomposition.",
    ),
    provider: str = typer.Option(
        "openrouter", "--provider", "-p",
        help="LLM provider (openrouter, openai, anthropic).",
    ),
    model: str = typer.Option(
        "xiaomi/mimo-v2.5", "--model",
        help="Model identifier for the LLM.",
    ),
    no_verify: bool = typer.Option(
        False, "--no-verify",
        help="Skip approval prompts before finalizing the session.",
    ),
    no_ask: bool = typer.Option(
        False, "--no-ask",
        help="Auto-proceed without asking the user (for CI/automation).",
    ),
    quiet: bool = typer.Option(
        False, "--quiet", "-q",
        help="Suppress the live terminal panel.",
    ),
    no_tracing: bool = typer.Option(
        False, "--no-tracing",
        help="Disable Langfuse tracing (enabled by default).",
    ),
    env: str = typer.Option(
        "", "--env",
        help="Environment tag: dev, staging, production.",
    ),
):
    """Run the implementation coordinator — goal-driven specialist coordination.

    The implementation coordinator decomposes your goal into subtasks, starts a gawt session,
    dispatches specialists in parallel or sequential, monitors progress, and
    finalizes all changes into a single commit.

    Langfuse tracing is ON by default. Each run creates a trace in the Langfuse
    dashboard with nested spans for LLM calls, tool calls, and specialist
    dispatches. Use --no-tracing to disable.

    Requires env vars: LANGFUSE_HOST, LANGFUSE_PUBLIC_KEY, LANGFUSE_SECRET_KEY.
    If not set, tracing degrades gracefully (no crash, just a warning).

    Examples:

        janus improve -g "Fix population extinction at day 90"

        janus improve -g "Add gonotrophic cycle scorer D15" --plan docs/plans/calibration.md

        janus improve -g "Refactor ingest pipeline" --no-tracing

        janus improve -g "Fix scoring" --env production
    """
    if not goal:
        goal = typer.prompt("What is your goal?")

    if no_ask:
        os.environ["JANUS_NO_ASK_USER"] = "1"

    _setup_module_flags(no_verify)
    tracing = "" if no_tracing else "langfuse"
    resolved_env = _resolve_env(env)
    langfuse_client = _build_langfuse_client(tracing)

    from agents_janus.improvement import run_improvement

    result = run_improvement(
        goal=goal,
        plan_path=plan,
        provider=provider,
        model=model,
        quiet=quiet,
        langfuse_client=langfuse_client,
        env=resolved_env,
    )
    typer.echo(result)


if __name__ == "__main__":
    app()
