"""Calibration improvement cycle — recall, plan, spawn, score, improve."""
from __future__ import annotations

import json


CALIBRATION_PROMPT = """\
GOAL: {goal}

Run a calibration improvement cycle (max {max_iterations} iterations).

PHASE 1 — UNDERSTAND THE PROBLEM:
Before doing anything, read the relevant code to understand what you're working with.
1. memory_recall_kg(query="calibration improvement patterns ABM scoring regression", k=5)
2. Use read_file to examine the key C++ parameter file: mal-core/src/mal_core/abm/params.h
   — this contains all tunable parameters (MORT_BASAL, ADULT_SIGMA, DISPERSE_PROB, etc.)
3. Use grep to find where these parameters are used in the engine: grep(pattern="MORT_BASAL|ADULT_SIGMA|DISPERSE_PROB", path="mal-core/src/mal_core/abm/")
4. Use read_file to check the current thresholds: mal-core/src/mal_core/abm/tests/calibration/thresholds.yaml
5. pipeline_run_calibration(seed=1, days=30, n_rollouts=1) — establish baseline

You now have full context: what parameters exist, what values they have, what the thresholds expect, and what the current baseline score is.

PHASE 2 — SPAWN WORKER:
6. gitagent_init()
7. gitagent_start(feature="calibration-<short-id>")  — pick a unique descriptive name
8. gitagent_spawn(feature="calibration-<short-id>", agent_id="abm-worker-1", role="abm")
9. task(subagent_type="abm-worker", description="You are an ABM calibration worker in an isolated worktree.

Your goal: {goal}

Context you have:
- Parameters live in mal-core/src/mal_core/abm/params.h
- Engine logic in mal-core/src/mal_core/abm/engine.hpp and wire.hpp
- Thresholds in mal-core/src/mal_core/abm/tests/calibration/thresholds.yaml
- Run tests with: cd mal-core/src/mal_core/abm/tests/calibration && uv run pytest -m fast -v

Steps:
1. Read params.h to understand current parameter values
2. Read engine.hpp to understand how parameters affect mortality, dispersal, and population dynamics
3. Make targeted changes to params.h based on the goal
4. Compile and test: cd mal-core/src/mal_core/abm/tests/calibration && uv run pytest -m fast -v
5. If tests pass, run: abm_run(aoi='ghana', year=2024, month=1, days=90, n_rollouts=1, seed=1)
6. Score the result: abm_score(run_dir='<output_dir>')
7. When done, propose your changes:
   gitagent propose --feature calibration-<short-id> --agent abm-worker-1 --title '<what you changed>' --summary '<why>' --confidence 0.8

Report back: what parameters you changed, what the test results were, what the score improved to.")

PHASE 3 — REVIEW:
10. gitagent_proposals(feature="calibration-<short-id>") — if none: STOP
11. gitagent_diff(proposal_id, feature="calibration-<short-id>") — review changes carefully
12. Accept if changes make biological sense and improve the score
13. If revision needed: gitagent_revise(feature="calibration-<short-id>", feedback="specific feedback") → back to step 9

PHASE 4 — VERIFY & FINALIZE:
14. pipeline_run_calibration(seed=1, days=30, n_rollouts=1) — verify improvement
15. If improved: gitagent_integrate(feature="calibration-<short-id>") → gitagent_finalize(feature="calibration-<short-id>", message="calibration: <description>")
16. If not improved: record what failed with improve_prompt(), try new approach

IMPORTANT: You must UNDERSTAND the code before delegating. Don't blindly follow steps — read the files, form a hypothesis, then give the worker a specific, informed task."""


def run_calibration_cycle(
    goal: str,
    max_iterations: int = 10,
    provider: str = "openrouter",
    model: str = "xiaomi/mimo-v2.5",
    thread_id: str = "calibration-session",
    dry_run: bool = False,
) -> str:
    """Run the ABM calibration improvement cycle.

    Args:
        goal: The objective for this calibration run.
        max_iterations: Maximum number of improvement iterations.
        provider: LLM provider.
        model: Model identifier.
        thread_id: Thread ID for checkpointing.
        dry_run: If True, print the prompt without executing.

    Returns:
        The final agent response after the cycle completes.
    """
    prompt = CALIBRATION_PROMPT.format(goal=goal, max_iterations=max_iterations)

    if dry_run:
        return json.dumps({
            "status": "dry_run",
            "prompt": prompt,
            "goal": goal,
            "max_iterations": max_iterations,
        })

    import agents.deepagents.agent as agent_mod
    from agents.deepagents.logger import SessionLogger

    # Initialize session logger
    logger = SessionLogger()
    agent_mod.SESSION_LOGGER = logger
    logger.log_decision("session_start", f"calibration cycle, goal={goal}, max_iterations={max_iterations}")

    try:
        agent = agent_mod.create_orchestrator(provider=provider, model=model, thread_id=thread_id)

        # Use stream to capture full conversation including LLM reasoning
        full_messages = []
        for event in agent.stream(
            {"messages": [{"role": "user", "content": prompt}]},
            stream_mode="messages",
        ):
            # event is a tuple: (message, metadata)
            if isinstance(event, tuple) and len(event) == 2:
                msg, metadata = event
                # Log AI messages (reasoning) and tool messages (results)
                if hasattr(msg, "content") and msg.content:
                    msg_type = type(msg).__name__
                    full_messages.append({
                        "type": msg_type,
                        "content": msg.content if isinstance(msg.content, str) else str(msg.content),
                    })

        # Log the full conversation to session.jsonl
        logger.log_conversation(full_messages)

        # Get the final response
        final_content = full_messages[-1]["content"] if full_messages else "No response"
        logger.log_summary(final_content)
        return final_content
    finally:
        logger.close()
        agent_mod.SESSION_LOGGER = None
