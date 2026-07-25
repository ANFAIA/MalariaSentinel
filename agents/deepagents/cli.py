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
    help="MalariaSentinel DeepAgent System — multi-agent ABM calibration orchestrator.",
    no_args_is_help=True,
)


def _resolve_goal(goal: str | None, prompt_text: str) -> str:
    """Return the goal, or ask interactively if not provided."""
    if goal:
        return goal
    return typer.prompt(prompt_text)


@app.command()
def calibration(
    goal: str = typer.Option(None, "--goal", "-g", help="Goal for this calibration run. If not set, you'll be prompted."),
    max_iterations: int = typer.Option(10, "--max-iterations", "-n", help="Maximum improvement iterations."),
    provider: str = typer.Option("openrouter", "--provider", "-p", help="LLM provider."),
    model: str = typer.Option("xiaomi/mimo-v2.5", "--model", "-m", help="Model identifier."),
    thread_id: str = typer.Option("calibration-session", "--thread-id", "-t", help="Thread ID for checkpointing."),
    dry_run: bool = typer.Option(False, "--dry-run", help="Print the prompt without executing."),
    no_verify: bool = typer.Option(False, "--no-verify", help="Skip approval prompt before gitagent finalize."),
):
    """Run the ABM calibration improvement cycle."""
    goal = _resolve_goal(goal, "What is the goal for this calibration run?")

    import agents.deepagents.agent as agent_mod
    agent_mod.VERIFY_FINALIZE = not no_verify

    from agents.deepagents.cycles.calibration_cycle import run_calibration_cycle

    result = run_calibration_cycle(
        goal=goal,
        max_iterations=max_iterations,
        provider=provider,
        model=model,
        thread_id=thread_id,
        dry_run=dry_run,
    )
    typer.echo(result)


@app.command()
def feature(
    name: str = typer.Argument(..., help="Feature name."),
    description: str = typer.Argument(..., help="Feature description."),
    goal: str = typer.Option(None, "--goal", "-g", help="Goal for this feature run. If not set, you'll be prompted."),
    provider: str = typer.Option("openrouter", "--provider", "-p", help="LLM provider."),
    model: str = typer.Option("xiaomi/mimo-v2.5", "--model", "-m", help="Model identifier."),
    thread_id: str = typer.Option("feature-session", "--thread-id", "-t", help="Thread ID for checkpointing."),
    dry_run: bool = typer.Option(False, "--dry-run", help="Print the prompt without executing."),
    no_verify: bool = typer.Option(False, "--no-verify", help="Skip approval prompt before gitagent finalize."),
):
    """Run a feature development cycle."""
    goal = _resolve_goal(goal, f"What is the goal for feature '{name}'?")

    import agents.deepagents.agent as agent_mod
    agent_mod.VERIFY_FINALIZE = not no_verify

    from agents.deepagents.cycles.feature_cycle import run_feature_cycle

    result = run_feature_cycle(
        name=name,
        description=description,
        goal=goal,
        provider=provider,
        model=model,
        thread_id=thread_id,
        dry_run=dry_run,
    )
    typer.echo(result)


@app.command()
def research(
    topic: str = typer.Argument(..., help="Research topic to investigate."),
    goal: str = typer.Option(None, "--goal", "-g", help="Goal for this research run. If not set, you'll be prompted."),
    cycles: int = typer.Option(1, "--cycles", "-c", help="Number of research cycles."),
    provider: str = typer.Option("openrouter", "--provider", "-p", help="LLM provider."),
    model: str = typer.Option("xiaomi/mimo-v2.5", "--model", "-m", help="Model identifier."),
    thread_id: str = typer.Option("research-session", "--thread-id", "-t", help="Thread ID for checkpointing."),
    dry_run: bool = typer.Option(False, "--dry-run", help="Print the prompt without executing."),
    no_verify: bool = typer.Option(False, "--no-verify", help="Skip approval prompt before gitagent finalize."),
):
    """Run a research + improvement cycle."""
    goal = _resolve_goal(goal, f"What is the goal for research on '{topic}'?")

    import agents.deepagents.agent as agent_mod
    agent_mod.VERIFY_FINALIZE = not no_verify

    from agents.deepagents.cycles.research_cycle import run_research_cycle

    result = run_research_cycle(
        topic=topic,
        goal=goal,
        cycles=cycles,
        provider=provider,
        model=model,
        thread_id=thread_id,
        dry_run=dry_run,
    )
    typer.echo(result)


if __name__ == "__main__":
    app()
