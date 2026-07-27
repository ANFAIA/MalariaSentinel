"""ABM improvement cycle — understand, plan, spawn, review, improve."""
from __future__ import annotations

import json


CALIBRATION_PROMPT = """\
GOAL: {goal}

Run an ABM improvement cycle (max {max_iterations} iterations).

═══════════════════════════════════════════════════════════════════════════════
PHASE 1 — RECONNAISSANCE (mandatory, ~5-10 minutes)
═══════════════════════════════════════════════════════════════════════════════

Before forming any hypothesis, EXPLORE the codebase.

Step 1: Check git history to know what's already been done.
- execute("git log --oneline -30") — recent commits
- execute("git log --oneline -20 --grep='calibration'") — calibration work
- execute("git log --oneline -20 --grep='M7'") — milestone work
- Look for "biological calibration", "scorer", "D15" — what's already optimized

Step 2: Explore directory structure.
- glob(pattern="mal-core/src/mal_core/abm/**/*.hpp")
- glob(pattern="mal-core/src/mal_core/abm/**/*.cpp")
- glob(pattern="mal-core/src/mal_core/abm/tests/calibration/**/*.py")

Step 3: Read the key files.
- read_file("mal-core/src/mal_core/abm/params.h") — all parameters
- read_file("mal-core/src/mal_core/abm/engine.hpp") — simulation logic
- read_file("mal-core/src/mal_core/abm/wire.hpp") — parameter initialization
- Read other files that match your goal's keywords

Step 4: Look for comments and TODOs in the code.
- grep(pattern="TODO|FIXME|XXX|HACK|NOTE", path="mal-core/src/mal_core/abm/")
- Often the code itself documents known issues

Step 5: Check for version mismatches (binary vs source).
- execute("ls -la mal-core/src/mal_core/abm/build/src/mal_abm_fast")
- execute("git log -1 --format='%ai %s' mal-core/src/mal_core/abm/src/main.cpp")
- If binary is older than source → rebuild before any diagnostic run

Step 6: Find recent calibration outputs.
- ls runs/, ls docs/, ls mal-core/src/mal_core/abm/tests/calibration/runs/

═══════════════════════════════════════════════════════════════════════════════
PHASE 2 — RUN DIAGNOSTICS (get the actual data)
═══════════════════════════════════════════════════════════════════════════════

Step 7: Get the actual symptom data BEFORE forming hypotheses.
- pipeline_run_calibration(seed=1, days=365, include_trajectory=True) — full year + trajectory
- Look at the trajectory: day-by-day adults, aquatic, eggs
- Identify: when does the decline start? Is it exponential collapse or sudden?
- Compare 3 seeds to distinguish structural vs stochastic issues

Step 8: Check what the scorers validate.
- read_file("mal-core/src/mal_core/abm/tests/calibration/thresholds.yaml")
- read_file("mal-core/src/mal_core/abm/tests/calibration/scorers/composite.py")
- Are there gaps? (e.g., no 1-year scorer → extinction goes undetected)

═══════════════════════════════════════════════════════════════════════════════
PHASE 3 — FORM HYPOTHESES (state the problem clearly)
═══════════════════════════════════════════════════════════════════════════════

Before touching ANY code, state:

1. What is the actual symptom? (Be specific with numbers)
   - "Adult population drops from 150 to 0 between day 60 and day 90"
   - NOT: "the simulation doesn't work"

2. Where in the code is this likely happening? (Name files, functions, parameters)
   - "oviposition logic in mosquito_submodel.cpp:385-458 calls cohort_bank_.add_eggs() but only for HOST_SEEKING state, not OVIPOSITION_SEEKING"

3. What is your hypothesis?
   - "Hypothesis: female mosquitoes never reach OVIPOSITING state because the OVIPOSITION_SEEKING→OVIPOSITING transition is delegated to caller but not implemented"

4. What evidence supports this?
   - Cite specific code lines, parameters, comments, paper references

5. If you have multiple hypotheses, list and rank them.
   - Pick the most likely one to test first

6. If you cannot form a hypothesis, ASK THE USER.
   - State what you know and what you don't know

═══════════════════════════════════════════════════════════════════════════════
PHASE 4 — GATHER CONTEXT (KB, papers, web — in this order)
═══════════════════════════════════════════════════════════════════════════════

Step 9: memory_recall_kg(query="<specific question about past failures>", k=5)
  USE FOR: "have we seen this symptom before?", "pattern for adding scorers", "pitfall with X"
  DO NOT USE FOR: "how does the ABM work", "what parameter causes extinction"

Step 10: Read papers/ IF the goal relates to biological plausibility.
  USE FOR: validating parameter values
  DO NOT USE FOR: code debugging

Step 11: opencode_search(query="<scientific question>") IF you need field data.
  USE FOR: field mortality rates, dispersal distances, cycle durations
  DO NOT USE FOR: "why our simulation crashes"

═══════════════════════════════════════════════════════════════════════════════
PHASE 5 — PRESENT DIAGNOSIS & ASK
═══════════════════════════════════════════════════════════════════════════════

Step 12: Present a structured diagnosis:
  - Symptom (with data from trajectory)
  - Root cause (with file:line citations)
  - Hypothesis ranking
  - Proposed fix(es) with rationale

Step 13: ASK THE USER to confirm or revise before iterating.
  - "Shall I proceed with this fix?"
  - "Is the hypothesis plausible?"
  - "Which of these N approaches do you prefer?"

═══════════════════════════════════════════════════════════════════════════════
PHASE 6 — DELEGATE TO WORKERS (parallel when possible)
═══════════════════════════════════════════════════════════════════════════════

Step 14: For each independent piece of work, spawn a worker in PARALLEL.
  - C++ fix → one worker
  - New scorer → another worker (if needed)
  - Both can run in parallel (independent files)

  workflow:
  - gitagent_init
  - gitagent_start(feature="<descriptive-name>")
  - gitagent_spawn(feature="<name>", agent_id="a_fix", role="abm")      # C++ fix
  - gitagent_spawn(feature="<name>", agent_id="a_scorer", role="scorer") # scorer (if needed)
  - task(subagent_type="abm-worker", description="<detailed task>") for each

  The task description MUST include:
  - Reconnaissance findings (specific files, line numbers)
  - Hypothesis (what you think is wrong)
  - What files to change and how
  - How to verify (specific test command)
  - Feature name for gitagent propose

Step 15: Wait for proposals, review with gitagent_diff, accept/reject/revise.

Step 16: gitagent_integrate(feature="<name>") → gitagent_finalize(feature="<name>", message="...")

═══════════════════════════════════════════════════════════════════════════════
PHASE 7 — VALIDATE END-TO-END
═══════════════════════════════════════════════════════════════════════════════

Step 17: Re-run the simulation: pipeline_run_calibration(seed=1, days=365, include_trajectory=True)
Step 18: Compare before/after trajectories — present as a table.
Step 19: Report final state: files modified, test results, commit hash, before/after data.

═══════════════════════════════════════════════════════════════════════════════

RULES:
- RECONNAISSANCE FIRST — always git log + read code before deciding
- DIAGNOSTICS BEFORE FIXES — run the simulation, get the actual data
- HYPOTHESES BEFORE FIXES — always state the problem with evidence
- ASK WHEN UNCERTAIN — don't assume, ask the user
- BE SPECIFIC — name files, line numbers, parameter names
- PARALLEL WORKERS — spawn independent fixes in parallel
- The KB is for past failures and project structure, not for solving new problems
- The web is for scientific validation, not for debugging local simulations
- Papers are for biological plausibility, not for finding code bugs
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
