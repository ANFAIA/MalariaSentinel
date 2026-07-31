"""CLI entry point for the MalariaSentinel DeepAgent system."""
from __future__ import annotations

import sys
from pathlib import Path

# Ensure project root is on sys.path
_project_root = Path(__file__).resolve().parent.parent.parent
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))

import typer

app = typer.Typer(
    name="deepagents",
    help="MalariaSentinel DeepAgent System — multi-agent ABM orchestrator. "
         "Single `run` command handles calibration, features, research, and bug fixes.",
    no_args_is_help=True,
)


def _setup_module_flags(no_verify: bool) -> None:
    """Configure module-level flags based on CLI options."""
    import agents.deepagents.agent as agent_mod
    agent_mod.VERIFY_FINALIZE = not no_verify
    agent_mod.VERIFY_INTEGRATE = not no_verify


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
):
    """Run the unified ABM improvement cycle.

    The orchestrator handles all goal types (calibration, features, research, bugs)
    through one methodology. Mode is auto-detected from the goal unless explicitly set.

    Examples:
        deepagents run -g "Población se extingue ~día 90"
        deepagents run -g "Add gonotrophic cycle tracking" --mode feature
        deepagents run -g "Review literature on Anopheles mortality" --mode research
    """
    if not goal:
        goal = typer.prompt("What is your goal?")
    if mode and mode not in ("calibration", "feature", "research", "general"):
        typer.echo(f"Invalid mode: {mode}. Use calibration, feature, research, or general.")
        raise typer.Exit(1)

    _setup_module_flags(no_verify)

    from agents.deepagents.cycles.run_cycle import run_cycle

    result = run_cycle(
        goal=goal,
        max_iterations=max_iterations,
        mode=mode,
        provider=provider,
        model=model,
        thread_id=thread_id,
        dry_run=dry_run,
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
    """DEPRECATED: use `deepagents run --mode calibration` instead."""
    typer.echo("⚠ `calibration` command is deprecated. Use: deepagents run --mode calibration", err=True)
    if not goal:
        goal = typer.prompt("What is the goal for this calibration run?")
    _setup_module_flags(no_verify)
    from agents.deepagents.cycles.run_cycle import run_calibration_cycle
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
    """DEPRECATED: use `deepagents run --mode feature` instead."""
    typer.echo("⚠ `feature` command is deprecated. Use: deepagents run --mode feature", err=True)
    if not goal:
        goal = typer.prompt(f"What is the goal for feature '{name}'?")
    _setup_module_flags(no_verify)
    from agents.deepagents.cycles.run_cycle import run_feature_cycle
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
    """DEPRECATED: use `deepagents run --mode research` instead."""
    typer.echo("⚠ `research` command is deprecated. Use: deepagents run --mode research", err=True)
    if not goal:
        goal = typer.prompt(f"What is the goal for research on '{topic}'?")
    _setup_module_flags(no_verify)
    from agents.deepagents.cycles.run_cycle import run_research_cycle
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
    from agents.deepagents.onboarding import run_onboarding
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
):
    """Run the improvement orchestrator for a goal."""
    if not goal:
        goal = typer.prompt("What is your goal?")
    _setup_module_flags(no_verify)
    from agents.deepagents.improvement import run_improvement
    result = run_improvement(
        goal=goal,
        plan_path=plan,
        provider=provider,
        model=model,
        thread_id=thread_id,
    )
    typer.echo(result)


@app.command()
def status():
    """Show current session status: scorecards, plans, subagents."""
    from agents.deepagents.onboarding import _show_status
    typer.echo(_show_status())


# Subagent group
agents_app = typer.Typer(help="Manage subagents.")
app.add_typer(agents_app, name="agents")


@agents_app.command("list")
def agents_list():
    """List all registered subagents."""
    from agents.deepagents.onboarding import _list_components
    typer.echo(_list_components())


@agents_app.command("show")
def agents_show(name: str = typer.Argument(..., help="Subagent name.")):
    """Show details for a specific subagent."""
    import json as _json
    from agents.deepagents.subagents.registry import load_registry
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