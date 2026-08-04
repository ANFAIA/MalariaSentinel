"""CLI entry point for the MalariaSentinel DeepAgent system."""
from __future__ import annotations

import os
import sys
from pathlib import Path

# Ensure project root is on sys.path
_project_root = Path(__file__).resolve().parent.parent.parent
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))

import typer

app = typer.Typer(
    name="janus",
    help="MalariaSentinel DeepAgent System — multi-agent ABM orchestrator. "
         "Single `run` command handles calibration, features, research, and bug fixes.",
    no_args_is_help=True,
)


def _load_dotenv() -> None:
    """Load .env from cwd or any parent dir into os.environ (no override).

    Searches upward from cwd, stopping at the first .env found. Does not
    overwrite already-set env vars (existing shell exports win).
    """
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
    agent_mod.VERIFY_INTEGRATE = not no_verify


def _resolve_tracing(tracing: str | None) -> str:
    """Resolve tracing backend from CLI flag or JANUS_TRACING env var."""
    return tracing or os.environ.get("JANUS_TRACING", "")


def _build_langfuse_client(tracing: str):
    """Build a langfuse.Langfuse client if tracing=langfuse and env is set.

    Returns None for any other value, missing env vars, or import errors.
    Logs a warning to stderr if langfuse is requested but unavailable.
    """
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
    mode: str = typer.Option(None, "--mode", "-m", help="Explicit mode: calibration, feature, research, general. Auto-detected from goal if not set."),
    max_iterations: int = typer.Option(10, "--max-iterations", "-n", help="Maximum improvement iterations."),
    provider: str = typer.Option("openrouter", "--provider", "-p", help="LLM provider."),
    model: str = typer.Option("xiaomi/mimo-v2.5", "--model", help="Model identifier."),
    thread_id: str = typer.Option("centinela-session", "--thread-id", "-t", help="Thread ID for checkpointing."),
    dry_run: bool = typer.Option(False, "--dry-run", help="Print the prompt without executing."),
    no_verify: bool = typer.Option(False, "--no-verify", help="Skip approval prompts before integrate/finalize."),
    no_ask: bool = typer.Option(False, "--no-ask", help="Skip user prompts (auto-proceed with defaults)."),
    quiet: bool = typer.Option(False, "--quiet", "-q", help="Disable the live terminal panel. JSONL + langfuse still emit."),
    tracing: str = typer.Option("", "--tracing", help="Tracing backend: 'langfuse' (requires langfuse SDK + env vars)."),
):
    """Run the unified ABM improvement cycle.

    The orchestrator handles all goal types (calibration, features, research, bugs)
    through one methodology. Mode is auto-detected from the goal unless explicitly set.

    Examples:
        janus run -g "Población se extingue ~día 90"
        janus run -g "Add gonotrophic cycle tracking" --mode feature
        janus run -g "Review literature on Anopheles mortality" --mode research
    """
    if not goal:
        goal = typer.prompt("What is your goal?")
    if mode and mode not in ("calibration", "feature", "research", "general"):
        typer.echo(f"Invalid mode: {mode}. Use calibration, feature, research, or general.")
        raise typer.Exit(1)

    if no_ask:
        os.environ["JANUS_NO_ASK_USER"] = "1"

    _setup_module_flags(no_verify)
    resolved_tracing = _resolve_tracing(tracing)
    langfuse_client = _build_langfuse_client(resolved_tracing)

    from agents_janus.cycles.run_cycle import run_cycle

    result = run_cycle(
        goal=goal,
        max_iterations=max_iterations,
        mode=mode,
        provider=provider,
        model=model,
        thread_id=thread_id,
        dry_run=dry_run,
        quiet=quiet,
        langfuse_client=langfuse_client,
    )
    typer.echo(result)


# Backwards-compat aliases (deprecated — use `run` with --mode instead)
@app.command(deprecated=True, hidden=True)
def calibration(
    goal: str = typer.Option(None, "--goal", "-g"),
    max_iterations: int = typer.Option(10, "--max-iterations", "-n"),
    provider: str = typer.Option("openrouter", "--provider", "-p"),
    model: str = typer.Option("xiaomi/mimo-v2.5", "--model", "-m"),
    thread_id: str = typer.Option("calibration-session", "--thread-id", "-t"),
    dry_run: bool = typer.Option(False, "--dry-run"),
    no_verify: bool = typer.Option(False, "--no-verify"),
):
    """DEPRECATED: use `janus run --mode calibration` instead."""
    typer.echo("⚠ `calibration` command is deprecated. Use: janus run --mode calibration", err=True)
    if not goal:
        goal = typer.prompt("What is the goal for this calibration run?")
    _setup_module_flags(no_verify)
    from agents_janus.cycles.run_cycle import run_calibration_cycle
    result = run_calibration_cycle(
        goal=goal, max_iterations=max_iterations,
        provider=provider, model=model, thread_id=thread_id, dry_run=dry_run,
    )
    typer.echo(result)


@app.command(deprecated=True, hidden=True)
def feature(
    name: str = typer.Argument(...),
    description: str = typer.Argument(...),
    goal: str = typer.Option(None, "--goal", "-g"),
    provider: str = typer.Option("openrouter", "--provider", "-p"),
    model: str = typer.Option("xiaomi/mimo-v2.5", "--model", "-m"),
    thread_id: str = typer.Option("feature-session", "--thread-id", "-t"),
    dry_run: bool = typer.Option(False, "--dry-run"),
    no_verify: bool = typer.Option(False, "--no-verify"),
):
    """DEPRECATED: use `janus run --mode feature` instead."""
    typer.echo("⚠ `feature` command is deprecated. Use: janus run --mode feature", err=True)
    if not goal:
        goal = typer.prompt(f"What is the goal for feature '{name}'?")
    _setup_module_flags(no_verify)
    from agents_janus.cycles.run_cycle import run_feature_cycle
    result = run_feature_cycle(
        name=name, description=description, goal=goal,
        provider=provider, model=model, thread_id=thread_id, dry_run=dry_run,
    )
    typer.echo(result)


@app.command(deprecated=True, hidden=True)
def research(
    topic: str = typer.Argument(...),
    goal: str = typer.Option(None, "--goal", "-g"),
    cycles: int = typer.Option(1, "--cycles", "-c"),
    provider: str = typer.Option("openrouter", "--provider", "-p"),
    model: str = typer.Option("xiaomi/mimo-v2.5", "--model", "-m"),
    thread_id: str = typer.Option("research-session", "--thread-id", "-t"),
    dry_run: bool = typer.Option(False, "--dry-run"),
    no_verify: bool = typer.Option(False, "--no-verify"),
):
    """DEPRECATED: use `janus run --mode research` instead."""
    typer.echo("⚠ `research` command is deprecated. Use: janus run --mode research", err=True)
    if not goal:
        goal = typer.prompt(f"What is the goal for research on '{topic}'?")
    _setup_module_flags(no_verify)
    from agents_janus.cycles.run_cycle import run_research_cycle
    result = run_research_cycle(
        topic=topic, goal=goal, cycles=cycles,
        provider=provider, model=model, thread_id=thread_id, dry_run=dry_run,
    )
    typer.echo(result)


@app.command()
def onboard(
    provider: str = typer.Option("openrouter", "--provider", "-p", help="LLM provider."),
    model: str = typer.Option("xiaomi/mimo-v2.5", "--model", help="Model identifier."),
):
    """Interactive onboarding menu. Walks you through common tasks."""
    from agents_janus.onboarding import run_onboarding
    result = run_onboarding(provider=provider, model=model)
    typer.echo(result)


@app.command()
def improve(
    goal: str = typer.Option(None, "--goal", "-g", help="Goal for improvement."),
    plan: str = typer.Option(None, "--plan", help="Path to a plan file to use as context."),
    provider: str = typer.Option("openrouter", "--provider", "-p", help="LLM provider."),
    model: str = typer.Option("xiaomi/mimo-v2.5", "--model", help="Model identifier."),
    thread_id: str = typer.Option("improvement-session", "--thread-id", "-t", help="Thread ID."),
    no_verify: bool = typer.Option(False, "--no-verify", help="Skip approval prompts."),
    no_ask: bool = typer.Option(False, "--no-ask", help="Skip user prompts (auto-proceed with defaults)."),
    quiet: bool = typer.Option(False, "--quiet", "-q", help="Disable the live terminal panel. JSONL + langfuse still emit."),
    tracing: str = typer.Option("", "--tracing", help="Tracing backend: 'langfuse' (requires langfuse SDK + env vars)."),
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