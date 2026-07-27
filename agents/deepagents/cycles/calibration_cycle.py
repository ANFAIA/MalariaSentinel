"""ABM improvement cycle — understand, plan, spawn, review, improve."""
from __future__ import annotations

import json


CALIBRATION_PROMPT = """\
GOAL: {goal}

Run an ABM improvement cycle (max {max_iterations} iterations).

PHASE 1 — READ THE CODE (MANDATORY FIRST STEP):
Before ANYTHING else, read the actual C++ code to understand what's happening.

Step 1: Find the relevant code.
- grep(pattern="<keywords from the goal>", path="mal-core/src/mal_core/abm/")
- glob(pattern="mal-core/src/mal_core/abm/**/*.hpp")
- glob(pattern="mal-core/src/mal_core/abm/**/*.cpp")

Step 2: Read the files you found.
- read_file("mal-core/src/mal_core/abm/params.h") — all parameters and their values
- read_file("mal-core/src/mal_core/abm/engine.hpp") — simulation logic
- Read any other files that are relevant to the goal

Step 3: Understand the problem.
- What does the code actually do?
- Where is the behavior that the goal describes?
- What values do the parameters have?
- What is the expected vs actual behavior?

You CANNOT delegate to a worker if you haven't read the code yourself.
You CANNOT search the web for answers to a local simulation problem.

PHASE 2 — GATHER CONTEXT (only after reading code):
Step 4: memory_recall_kg(query="<specific question about past failures>", k=5)
  — Use this ONLY to check: have we hit this problem before? What was the root cause?
  — Do NOT use this to "understand" the current code. You already read it.

Step 5: Read papers in papers/ directory IF the goal relates to biological plausibility.
  — Use this to validate: is the parameter value biologically reasonable?
  — Do NOT use this to debug the simulation.

Step 6: opencode_search(query="<specific scientific question>") IF you need field data or parameter ranges.
  — Use this to find: what do field studies say about mosquito mortality?
  — Do NOT use this to find "why the simulation crashes" — that's a code problem.

Step 7: pipeline_run_calibration(seed=1, days=30, n_rollouts=1) — establish baseline.

PHASE 3 — PLAN & DELEGATE:
Step 8: Formulate a specific hypothesis:
  "The population crashes because <X parameter/code> does <Y>, which causes <Z>.
   To fix it, I need to change <X> to <new value/behavior> because <scientific reason>."

Step 9: gitagent_init()
Step 10: gitagent_start(feature="<descriptive-name>")
Step 11: gitagent_spawn(feature="<descriptive-name>", agent_id="worker-1", role="abm")
Step 12: task(subagent_type="abm-worker", description="<YOUR DETAILED TASK>")

The task description MUST include:
- What you found by reading the code (specific file, line, parameter)
- Your hypothesis about the problem
- What files need to change and how
- How to verify the change
- The feature name for gitagent propose

PHASE 4 — REVIEW:
Step 13: gitagent_proposals(feature="<descriptive-name>") — if none: STOP
Step 14: gitagent_diff(proposal_id, feature="<descriptive-name>") — review changes
Step 15: Accept if the change addresses the root cause you identified
Step 16: If revision needed: gitagent_revise(feature="<descriptive-name>", feedback="...") → back to step 12

PHASE 5 — VERIFY & FINALIZE:
Step 17: Verify: run tests, check simulation, compare scores
Step 18: If improved: gitagent_integrate → gitagent_finalize
Step 19: If not improved: analyze why, form new hypothesis, try again

RULES:
- READ CODE BEFORE ANYTHING ELSE. No exceptions.
- You are NOT limited to parameter changes. You can modify ANY C++ code.
- The KB is for past failures and project structure, not for solving new problems.
- The web is for scientific validation, not for debugging local simulations.
- Papers are for biological plausibility, not for finding code bugs.
- Always verify: does the change make sense biologically AND technically?"""


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
