"""CLI entry point for the MalariaSentinel DeepAgent system."""
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
    help="MalariaSentinel DeepAgent System — multi-agent ABM orchestrator. "
         "Running `janus` with no arguments starts the conversational assistant.",
)


@app.callback(invoke_without_command=True)
def _main(ctx: typer.Context) -> None:
    """Default: start the conversational onboarding assistant."""
    if ctx.invoked_subcommand is None:
        from agents_janus.onboarding import run_onboarding
        run_onboarding()


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
    """Build a langfuse.Langfuse client if tracing=langfuse and env is set."""
    if tracing != "langfuse":
        return None
    try:
        from langfuse import Langfuse
    except ImportError:
        typer.echo(
            "⚠ --tracing langfuse requested but langfuse is not installed. "
            "Install with: uv pip install -e 'agents/janus[observability]'",
            err=True,
        )
        return None

    host = os.environ.get("LANGFUSE_HOST") or os.environ.get("LANGFUSE_BASE_URL")
    public_key = os.environ.get("LANGFUSE_PUBLIC_KEY")
    secret_key = os.environ.get("LANGFUSE_SECRET_KEY")
    if not (host and public_key and secret_key):
        typer.echo(
            "⚠ --tracing langfuse requires LANGFUSE_HOST (or LANGFUSE_BASE_URL), "
            "LANGFUSE_PUBLIC_KEY, LANGFUSE_SECRET_KEY env vars. "
            "Continuing without langfuse.",
            err=True,
        )
        return None

    return Langfuse(
        public_key=public_key,
        secret_key=secret_key,
        host=host,
    )


@app.command()
def run(
    goal: str = typer.Option(None, "--goal", "-g", help="Goal for this run. If not set, you'll be prompted."),
    max_iterations: int = typer.Option(10, "--max-iterations", "-n", help="Maximum improvement iterations."),
    provider: str = typer.Option("openrouter", "--provider", "-p", help="LLM provider."),
    model: str = typer.Option("xiaomi/mimo-v2.5", "--model", help="Model identifier."),
    thread_id: str = typer.Option("centinela-session", "--thread-id", "-t", help="Thread ID for checkpointing."),
    dry_run: bool = typer.Option(False, "--dry-run", help="Print the prompt without executing."),
    no_verify: bool = typer.Option(False, "--no-verify", help="Skip approval prompts before finalize."),
    no_ask: bool = typer.Option(False, "--no-ask", help="Skip user prompts (auto-proceed with defaults)."),
    quiet: bool = typer.Option(False, "--quiet", "-q", help="Disable the live terminal panel."),
    tracing: str = typer.Option("", "--tracing", help="Tracing backend: 'langfuse'."),
):
    """Run the improvement dispatcher.

    The orchestrator decomposes the goal, dispatches specialists via gawt MCP,
    monitors progress, and finalizes the session.

    Examples:
        janus run -g "Population goes extinct around day 90"
        janus run -g "Add gonotrophic cycle tracking"
    """
    if not goal:
        goal = typer.prompt("What is your goal?")

    if no_ask:
        os.environ["JANUS_NO_ASK_USER"] = "1"

    _setup_module_flags(no_verify)
    resolved_tracing = _resolve_tracing(tracing)
    langfuse_client = _build_langfuse_client(resolved_tracing)

    from agents_janus.improvement import run_improvement

    result = run_improvement(
        goal=goal,
        provider=provider,
        model=model,
        thread_id=thread_id,
        quiet=quiet,
        langfuse_client=langfuse_client,
    )
    typer.echo(result)


@app.command()
def onboard(
    provider: str = typer.Option("openrouter", "--provider", "-p", help="LLM provider."),
    model: str = typer.Option("xiaomi/mimo-v2.5", "--model", help="Model identifier."),
    quiet: bool = typer.Option(False, "--quiet", "-q", help="Suppress technical output."),
    tracing: str = typer.Option("", "--tracing", help="Tracing backend: 'langfuse'."),
):
    """Conversational onboarding agent. Ask questions, run tasks, get help."""
    resolved_tracing = _resolve_tracing(tracing)
    langfuse_client = _build_langfuse_client(resolved_tracing)

    from agents_janus.onboarding import run_onboarding
    result = run_onboarding(provider=provider, model=model, quiet=quiet, langfuse_client=langfuse_client)
    typer.echo(result)


@app.command()
def improve(
    goal: str = typer.Option(None, "--goal", "-g", help="Goal for improvement."),
    plan: str = typer.Option(None, "--plan", help="Path to a plan file to use as context."),
    provider: str = typer.Option("openrouter", "--provider", "-p", help="LLM provider."),
    model: str = typer.Option("xiaomi/mimo-v2.5", "--model", help="Model identifier."),
    thread_id: str = typer.Option("improvement-session", "--thread-id", "-t", help="Thread ID."),
    no_verify: bool = typer.Option(False, "--no-verify", help="Skip approval prompts."),
    no_ask: bool = typer.Option(False, "--no-ask", help="Skip user prompts."),
    quiet: bool = typer.Option(False, "--quiet", "-q", help="Disable the live terminal panel."),
    tracing: str = typer.Option("", "--tracing", help="Tracing backend: 'langfuse'."),
):
    """Run the improvement orchestrator for a goal."""
    if not goal:
        goal = typer.prompt("What is your goal?")

    if no_ask:
        os.environ["JANUS_NO_ASK_USER"] = "1"

    _setup_module_flags(no_verify)
    resolved_tracing = _resolve_tracing(tracing)
    langfuse_client = _build_langfuse_client(resolved_tracing)

    from agents_janus.improvement import run_improvement

    result = run_improvement(
        goal=goal,
        plan_path=plan,
        provider=provider,
        model=model,
        thread_id=thread_id,
        quiet=quiet,
        langfuse_client=langfuse_client,
    )
    typer.echo(result)


@app.command()
def status():
    """Show current session status: scorecards, plans, subagents."""
    from agents_janus.onboarding import _show_status
    typer.echo(_show_status())


# Subagent group
agents_app = typer.Typer(help="Manage subagents.")
app.add_typer(agents_app, name="agents")


@agents_app.command("list")
def agents_list():
    """List all registered subagents."""
    from agents_janus.onboarding import _list_components
    typer.echo(_list_components())


@agents_app.command("show")
def agents_show(name: str = typer.Argument(..., help="Subagent name.")):
    """Show details for a specific subagent."""
    import json as _json
    from agents_janus.subagents.registry import load_registry
    try:
        reg = load_registry()
        spec = reg.get(name)
        result = {
            "name": spec.name,
            "description": spec.description,
            "model": f"{spec.provider}/{spec.model}",
            "skills": list(spec.skills),
            "plugins": list(spec.plugins),
            "edits_allow": list(spec.edits_allow),
            "mailbox_inbox": spec.mailbox_inbox,
            "spec": str(spec.spec_path) if spec.spec_path else None,
            "thread_id_prefix": spec.thread_id_prefix,
        }
        typer.echo(_json.dumps(result, indent=2))
    except KeyError as e:
        typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1)


if __name__ == "__main__":
    app()
