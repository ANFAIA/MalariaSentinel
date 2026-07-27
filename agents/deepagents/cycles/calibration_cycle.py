"""ABM improvement cycle — understand, plan, spawn, review, improve."""
from __future__ import annotations

import json


CALIBRATION_PROMPT = """\
GOAL: {goal}

Run an ABM improvement cycle (max {max_iterations} iterations).

YOUR METHODOLOGY (follow this for every goal):

═══════════════════════════════════════════════════════════════════════════════
PHASE 1 — RECONNAISSANCE (mandatory, ~5-10 minutes)
═══════════════════════════════════════════════════════════════════════════════

Before forming any hypothesis, EXPLORE the codebase.

Step 1: Explore directory structure.
- glob(pattern="mal-core/src/mal_core/abm/**/*.hpp")
- glob(pattern="mal-core/src/mal_core/abm/**/*.cpp")
- glob(pattern="mal-core/src/mal_core/abm/tests/calibration/**/*.py")

Step 2: Read the key files.
- read_file("mal-core/src/mal_core/abm/params.h") — all parameters
- read_file("mal-core/src/mal_core/abm/engine.hpp") — simulation logic
- read_file("mal-core/src/mal_core/abm/wire.hpp") — parameter initialization
- Read any other files that match your goal's keywords

Step 3: Look at history.
- execute("git log --oneline -30 mal-core/src/mal_core/abm/")
- execute("git log --oneline -20 --grep='calibration'")
- Look for "M7", "M6", "biological calibration" commits

Step 4: Look for comments and TODOs.
- grep(pattern="TODO|FIXME|XXX|HACK|NOTE", path="mal-core/src/mal_core/abm/")
- Often the code itself explains known issues

Step 5: Find recent calibration outputs.
- ls runs/ to see previous rollouts
- ls docs/ for calibration reports

═══════════════════════════════════════════════════════════════════════════════
PHASE 2 — FORM HYPOTHESES (state the problem clearly)
═══════════════════════════════════════════════════════════════════════════════

Before touching ANY code, state:

1. What is the actual symptom?
   - Be specific: "adult population drops from 150 to 0 between day 60 and day 90"
   - NOT: "the simulation doesn't work"

2. Where in the code is this likely happening?
   - Name files, functions, parameters
   - E.g., "oviposition logic in gonotrophic_cycle.hpp:213 calls AquaticCohortBank.add_eggs() but I need to verify it's actually wired"

3. What is your hypothesis?
   - State it as: "Hypothesis: <X> causes <Y> because <Z>"
   - E.g., "Hypothesis: egg batch size (52) is too small to sustain R₀=1 given mortality rate (0.07/day)"

4. What evidence supports this?
   - Cite specific code lines, parameter values, paper references
   - E.g., "wire.hpp:88-91 comment confirms this was a known issue"

5. If you have multiple hypotheses, list them.
   - Rank by likelihood
   - Pick the most likely one to test first

6. If you cannot form a hypothesis, ASK THE USER.
   - Don't guess
   - State what you know and what you don't know

═══════════════════════════════════════════════════════════════════════════════
PHASE 3 — GATHER CONTEXT (KB, papers, web — in this order)
═══════════════════════════════════════════════════════════════════════════════

Step 6: memory_recall_kg(query="<specific question about past failures>", k=5)
  USE FOR:
    - "have we seen this exact problem before?"
    - "is there a pattern for adding a new scorer?"
    - "what was the root cause of past calibration failures?"
  DO NOT USE FOR:
    - "how does the ABM work" — you should have read the code
    - "what parameter causes extinction" — the code tells you

Step 7: Read papers/ IF the goal relates to biological plausibility.
  USE FOR:
    - "is mortality rate 0.07/day biologically reasonable?"
    - "what is the field-measured gonotrophic cycle duration?"
  DO NOT USE FOR:
    - "why does the simulation crash" — that's a code problem

Step 8: opencode_search(query="<specific scientific question>") IF you need field data.
  USE FOR:
    - "what do field studies say about An. gambiae mortality?"
    - "what is the natural egg batch size?"
  DO NOT USE FOR:
    - "why is our simulation crashing" — internet doesn't know our code

Step 9: pipeline_run_calibration(seed=1, days=30, n_rollouts=1) — baseline score.

═══════════════════════════════════════════════════════════════════════════════
PHASE 4 — PLAN & ASK (if needed)
═══════════════════════════════════════════════════════════════════════════════

Step 10: Make a structured plan.
  Phase A: Diagnosis (no code changes)
  Phase B: Minimal fix (smallest change to test hypothesis)
  Phase C: Verify (tests + simulation)
  Phase D: Iterate (refine until score improves)

Step 11: ASK THE USER if:
  - The fix would require non-trivial changes (refactoring, new scorers)
  - Multiple valid approaches exist (e.g., parameter change vs code change)
  - You're uncertain about scientific assumptions
  - The change might affect production code

═══════════════════════════════════════════════════════════════════════════════
PHASE 5 — DELEGATE TO WORKER
═══════════════════════════════════════════════════════════════════════════════

Step 12: gitagent_init()
Step 13: gitagent_start(feature="<descriptive-name>")
Step 14: gitagent_spawn(feature="<descriptive-name>", agent_id="worker-1", role="abm")
Step 15: task(subagent_type="abm-worker", description="<DETAILED TASK>")

The task description MUST include:
- Your reconnaissance findings (specific files, line numbers)
- Your hypothesis (what you think is wrong)
- What files need to change and how
- How to verify the change (specific test command)
- The feature name for gitagent propose

═══════════════════════════════════════════════════════════════════════════════
PHASE 6 — REVIEW & ITERATE
═══════════════════════════════════════════════════════════════════════════════

Step 16: gitagent_proposals(feature="<name>") — if none: STOP
Step 17: gitagent_diff(proposal_id, feature="<name>") — review changes
Step 18: Accept if the change addresses your hypothesis
Step 19: If revision needed: gitagent_revise(feedback="<specific feedback>") → back to step 15
Step 20: Verify: run tests, check simulation, compare scores
Step 21: If improved: gitagent_integrate → gitagent_finalize
Step 22: If not improved: form new hypothesis, try again

RULES:
- RECONNAISSANCE FIRST — always explore before deciding
- HYPOTHESES BEFORE FIXES — always state what you think is wrong before changing code
- SPECIFIC — always name files, line numbers, parameter names
- ASK WHEN UNCERTAIN — don't guess, ask the user
- The KB is for past failures and project structure, not for solving new problems.
- The web is for scientific validation, not for debugging local simulations.
- Papers are for biological plausibility, not for finding code bugs.
- Iterations unlimited — keep going until the goal is achieved."""


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
