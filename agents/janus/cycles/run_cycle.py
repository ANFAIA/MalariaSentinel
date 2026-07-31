"""Single unified ABM improvement cycle.

The orchestrator handles all goal types (calibration, features, research, bugs)
through one methodology. Mode auto-detection adjusts emphasis.
"""
from __future__ import annotations

import json


# Goal keywords that hint at methodology (English + Spanish)
_CALIBRATION_KEYWORDS = [
    # English
    "calibr", "parameter", "extinct", "mortality", "fecundity", "dispersal",
    "simulation crash", "population", "mosquito", "abm",
    # Spanish
    "calibr", "parámet", "extinc", "mortalid", "fecundid", "dispers",
    "poblaci", "simulación", "mosquit",
]
_FEATURE_KEYWORDS = [
    # English
    "add", "implement", "feature", "module", "new", "support", "enable",
    # Spanish
    "añad", "implementa", "funcionalid", "módulo", "nuevo", "nueva",
]
_RESEARCH_KEYWORDS = [
    # English
    "research", "investigate", "paper", "literature", "review", "survey", "compare approaches",
    # Spanish
    "investiga", "literatura", "revisi", "estudio", "papers", "papers/",
]


def _detect_mode(goal: str) -> str:
    """Auto-detect mode from goal text. Returns one of: calibration, feature, research."""
    g = goal.lower()
    cal_score = sum(1 for kw in _CALIBRATION_KEYWORDS if kw in g)
    feat_score = sum(1 for kw in _FEATURE_KEYWORDS if kw in g)
    res_score = sum(1 for kw in _RESEARCH_KEYWORDS if kw in g)
    scores = {"calibration": cal_score, "feature": feat_score, "research": res_score}
    best = max(scores, key=scores.get)
    return best if scores[best] > 0 else "general"


_RUN_PROMPT = """\
GOAL: {goal}
{detected_mode}

Run an ABM improvement cycle (max {max_iterations} iterations).
{mode_focus}

═══════════════════════════════════════════════════════════════════════════════
ASKING THE USER (ask_user tool)
═══════════════════════════════════════════════════════════════════════════════

You have an `ask_user` tool for open-ended questions. USE IT WHENEVER:
- You have multiple hypotheses and want the user to choose priority
- You found a value that conflicts with the user's intent
- The change would have non-trivial tradeoffs
- You're uncertain about scientific assumptions
- You need clarification on the goal itself

For binary decisions (accept/reject at integrate/finalize), the framework handles it.
For open-ended questions, call ask_user(question=..., options=[...]).

Examples:
- ask_user("3 hypotheses for extinction. Which first?",
           options=["Point-source collapse (raise fecundity)",
                    "R₀<1 (lower mortality)",
                    "Missing oviposition transition"])
- ask_user("Field data says mort=0.10/day, local is 0.07. Which?")
- ask_user("Add new scorer D15 or modify D2?")

═══════════════════════════════════════════════════════════════════════════════
PHASE 1 — RECONNAISSANCE (mandatory, ~5-10 minutes)
═══════════════════════════════════════════════════════════════════════════════

Before forming any hypothesis, EXPLORE the codebase.

Step 1: Check git history to know what's already been done.
- execute("git log --oneline -30") — recent commits
- execute("git log --oneline -20 --grep='calibration'") — calibration work
- execute("git log --oneline -20 --grep='M7'") — milestone work

Step 2: Explore directory structure.
- glob(pattern="mal-core/src/mal_core/abm/**/*.hpp")
- glob(pattern="mal-core/src/mal_core/abm/**/*.cpp")
- glob(pattern="mal-core/src/mal_core/abm/tests/calibration/**/*.py")

Step 3: Read the key files.
- read_file("mal-core/src/mal_core/abm/params.h")
- read_file("mal-core/src/mal_core/abm/engine.hpp")
- read_file("mal-core/src/mal_core/abm/wire.hpp")
- Read other files matching your goal's keywords

Step 4: Look for comments and TODOs.
- grep(pattern="TODO|FIXME|XXX|HACK|NOTE", path="mal-core/src/mal_core/abm/")
- Code often documents known issues

Step 5: Check for version mismatches.
- execute("ls -la mal-core/src/mal_core/abm/build/src/mal_abm_fast")
- If binary older than source → rebuild before diagnostics

Step 6: Find recent outputs.
- ls runs/, ls docs/, ls mal-core/src/mal_core/abm/tests/calibration/runs/

═══════════════════════════════════════════════════════════════════════════════
PHASE 2 — RUN DIAGNOSTICS (get the actual data)
═══════════════════════════════════════════════════════════════════════════════

Step 7: Get actual data BEFORE forming hypotheses.
- pipeline_run_calibration(seed=1, days=365, include_trajectory=True)
- Identify when decline starts; exponential collapse vs sudden
- Compare 3 seeds to distinguish structural vs stochastic

Step 8: Check what scorers validate.
- read_file("mal-core/src/mal_core/abm/tests/calibration/thresholds.yaml")
- Are there gaps? (e.g., no 1-year scorer → extinction undetected)

═══════════════════════════════════════════════════════════════════════════════
PHASE 3 — FORM HYPOTHESES (state the problem clearly)
═══════════════════════════════════════════════════════════════════════════════

Before touching ANY code, state:

1. Symptom (specific with numbers): "Adults drop from X to 0 between day 60-90"
2. Location in code (file:line): "mosquito_submodel.cpp:385-458 only handles HOST_SEEKING"
3. Hypothesis: "Hypothesis: <X> causes <Y> because <Z>"
4. Evidence: cite specific lines, parameters, comments
5. If multiple hypotheses, list and rank by likelihood
6. If you cannot form a hypothesis, ASK THE USER

═══════════════════════════════════════════════════════════════════════════════
PHASE 4 — GATHER CONTEXT (KB, papers, web — in this order)
═══════════════════════════════════════════════════════════════════════════════

Step 9: memory_recall_kg(query="<specific question>", k=5)
  USE FOR: "have we seen this before?", "pattern for adding X", "pitfall with Y"
  DO NOT USE FOR: "how does the ABM work" (read code), "what causes extinction" (code)

Step 10: Read papers/ IF biological plausibility is relevant.
Step 11: opencode_search(query="<scientific question>") IF field data needed.

═══════════════════════════════════════════════════════════════════════════════
PHASE 5 — PRESENT DIAGNOSIS & ASK
═══════════════════════════════════════════════════════════════════════════════

Step 12: Present structured diagnosis:
  - Symptom (with trajectory data)
  - Root cause (with file:line citations)
  - Hypothesis ranking
  - Proposed fix(es) with rationale

Step 13: ASK THE USER to confirm or revise before iterating.
  - "Shall I proceed with this fix?"
  - "Is the hypothesis plausible?"

═══════════════════════════════════════════════════════════════════════════════
PHASE 6 — DELEGATE TO WORKERS (parallel when possible)
═══════════════════════════════════════════════════════════════════════════════

Step 14: For independent pieces, spawn workers in PARALLEL.

  WORKTREE ISOLATION (mandatory for every worker):

    1. spawn_result = gitagent_spawn(feature="<name>", agent_id="a_fix", role="abm")
    2. set_worktree_context(agent_id="a_fix", worktree_path=spawn_result["worktree"])
    3. task(subagent_type="abm-worker", description="<task>")
    4. clear_worktree_context()

  Without step 2, the worker compiles/runs from the main repo — defeating isolation.

  For parallel workers: spawn all agents, set all contexts, invoke all tasks, clear all.

  Task description MUST include:
  - Reconnaissance findings (files, line numbers)
  - Hypothesis (what you think is wrong)
  - What files to change and how
  - How to verify (specific test command)
  - Feature name for gitagent propose
  - The worktree path (for shell commands: cd into it first)

Step 15: Review proposals with gitagent_diff, accept/reject/revise.
Step 16: gitagent_integrate(feature="<name>") → gitagent_finalize(feature="<name>", message="...")

═══════════════════════════════════════════════════════════════════════════════
PHASE 7 — VALIDATE END-TO-END
═══════════════════════════════════════════════════════════════════════════════

Step 17: Re-run: pipeline_run_calibration(seed=1, days=365, include_trajectory=True)
Step 18: Compare before/after trajectories — present as table.
Step 19: Report final state: files modified, test results, commit hash, before/after data.

═══════════════════════════════════════════════════════════════════════════════

RULES:
- RECONNAISSANCE FIRST — always git log + read code before deciding
- DIAGNOSTICS BEFORE FIXES — run the simulation, get the actual data
- HYPOTHESES BEFORE FIXES — always state the problem with evidence
- ASK WHEN UNCERTAIN — don't assume, ask the user
- BE SPECIFIC — name files, line numbers, parameter names
- PARALLEL WORKERS — spawn independent fixes in parallel
- KB for past failures, papers for biology, web for field data — never for code debugging
- Iterations unlimited — keep going until the goal is achieved.
"""


_MODE_FOCUS = {
    "calibration": """MODE: CALIBRATION
Focus on parameter values, scorers, and biological plausibility.
Key tools: pipeline_run_calibration (with include_trajectory=True), abm_score.
If a new scorer is needed to validate the fix, add it (D16, D17, ...).""",
    "feature": """MODE: FEATURE DEVELOPMENT
Focus on adding new functionality without breaking existing behavior.
Key tools: read_file/write_file/edit_file for new modules, abm_test for verification.
Maintain backwards compatibility — existing tests must still pass.""",
    "research": """MODE: RESEARCH
Focus on literature review and scientific validation.
Use research-worker for heavy literature work (it is read-only and specialized).
Key tools: opencode_search, read_file (papers/), memory_recall_kg.
Record findings with improve_prompt().""",
    "general": """MODE: GENERAL
Auto-detected — the goal doesn't fit a single category.
Apply the standard methodology and decide based on what you find.""",
}


def run_cycle(
    goal: str,
    max_iterations: int = 10,
    mode: str | None = None,
    provider: str = "openrouter",
    model: str = "xiaomi/mimo-v2.5",
    thread_id: str = "centinela-session",
    dry_run: bool = False,
) -> str:
    """Run a unified ABM improvement cycle.

    The orchestrator handles all goal types (calibration, features, research, bugs)
    through one methodology. If mode is None, it is auto-detected from the goal.

    Args:
        goal: The objective for this run.
        max_iterations: Maximum iterations.
        mode: Explicit mode (calibration, feature, research, general). Auto-detected if None.
        provider: LLM provider.
        model: Model identifier.
        thread_id: Thread ID for checkpointing.
        dry_run: If True, print the prompt without executing.

    Returns:
        The final agent response after the cycle completes.
    """
    detected_mode = mode or _detect_mode(goal)
    mode_focus = _MODE_FOCUS.get(detected_mode, _MODE_FOCUS["general"])
    detected_str = f"Detected mode: {detected_mode}" if not mode else f"Explicit mode: {mode}"

    prompt = _RUN_PROMPT.format(
        goal=goal,
        max_iterations=max_iterations,
        detected_mode=detected_str,
        mode_focus=mode_focus,
    )

    if dry_run:
        return json.dumps({
            "status": "dry_run",
            "prompt": prompt,
            "goal": goal,
            "mode": detected_mode,
            "max_iterations": max_iterations,
        })

    import agents.janus.agent as agent_mod
    from agents.janus.logger import SessionLogger

    logger = SessionLogger()
    agent_mod.SESSION_LOGGER = logger
    logger.log_decision("session_start", f"cycle (mode={detected_mode}), goal={goal}, max_iterations={max_iterations}")

    try:
        agent = agent_mod.create_orchestrator(provider=provider, model=model, thread_id=thread_id)

        # Capture both messages (LLM reasoning) and graph updates (node execution)
        full_messages = []
        graph_steps = []

        for event in agent.stream(
            {"messages": [{"role": "user", "content": prompt}]},
            stream_mode="updates",
        ):
            # stream_mode="updates" yields {node_name: state_delta} dicts
            if isinstance(event, dict):
                for node_name, delta in event.items():
                    graph_steps.append({
                        "node": node_name,
                        "delta_keys": list(delta.keys()) if isinstance(delta, dict) else str(type(delta)),
                    })
                    # Extract messages from the delta
                    if isinstance(delta, dict) and "messages" in delta:
                        for msg in delta["messages"]:
                            if hasattr(msg, "content") and msg.content:
                                full_messages.append({
                                    "type": type(msg).__name__,
                                    "content": msg.content if isinstance(msg.content, str) else str(msg.content),
                                })

        logger.log_graph_steps(graph_steps)
        logger.log_conversation(full_messages)
        final_content = full_messages[-1]["content"] if full_messages else "No response"
        logger.log_summary(final_content)
        return final_content
    finally:
        logger.close()
        agent_mod.SESSION_LOGGER = None


# Backwards-compatible aliases
def run_calibration_cycle(goal, max_iterations=10, mode=None, provider="openrouter", model="xiaomi/mimo-v2.5", thread_id="calibration-session", dry_run=False):
    """Backwards-compatible wrapper — delegates to run_cycle with calibration mode."""
    return run_cycle(
        goal=goal,
        max_iterations=max_iterations,
        mode=mode or "calibration",
        provider=provider,
        model=model,
        thread_id=thread_id,
        dry_run=dry_run,
    )


def run_feature_cycle(name, description, goal, provider="openrouter", model="xiaomi/mimo-v2.5", thread_id="feature-session", dry_run=False):
    """Backwards-compatible wrapper — delegates to run_cycle with feature mode."""
    full_goal = f"Feature '{name}': {description}. {goal}"
    return run_cycle(
        goal=full_goal,
        max_iterations=10,
        mode="feature",
        provider=provider,
        model=model,
        thread_id=thread_id,
        dry_run=dry_run,
    )


def run_research_cycle(topic, goal, cycles=1, provider="openrouter", model="xiaomi/mimo-v2.5", thread_id="research-session", dry_run=False):
    """Backwards-compatible wrapper — delegates to run_cycle with research mode."""
    full_goal = f"Research topic '{topic}': {goal}"
    return run_cycle(
        goal=full_goal,
        max_iterations=cycles,
        mode="research",
        provider=provider,
        model=model,
        thread_id=thread_id,
        dry_run=dry_run,
    )