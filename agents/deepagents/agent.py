"""MalariaSentinel DeepAgent orchestrator — create_orchestrator() factory."""
from __future__ import annotations

import os
import sys
from pathlib import Path

# Add the project root to sys.path for tool imports
_project_root = Path(__file__).resolve().parent.parent.parent
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))

from agents.deepagents.tools import (
    opencode_search,
    gitagent_init,
    gitagent_start,
    gitagent_spawn,
    gitagent_list_agents,
    gitagent_kill,
    gitagent_proposals,
    gitagent_diff,
    gitagent_accept,
    gitagent_reject,
    gitagent_revise,
    gitagent_integrate,
    gitagent_finalize,
    pipeline_run_calibration,
    pipeline_compare_scorecards,
    memory_recall_kg,
    improve_prompt,
    ask_user,
)
from agents.deepagents.logger import SessionLogger
from agents.deepagents.observability import ObservabilityMiddleware

try:
    from deepagents import FilesystemPermission
except ImportError:
    FilesystemPermission = None  # type: ignore[assignment,misc]

# Module-level flags set by CLI before creating the agent
VERIFY_FINALIZE: bool = True
VERIFY_INTEGRATE: bool = True
SESSION_LOGGER: SessionLogger | None = None

AGENT_DIR = Path(__file__).resolve().parent
REPO_ROOT = _project_root
PROJECT_SKILLS = REPO_ROOT / "agents" / "skills"
GLOBAL_SKILLS = Path.home() / ".agents" / "skills"


def _wrap_with_logging(tool_func):
    """Wrap a tool function to add structured logging + error capture."""
    import functools

    @functools.wraps(tool_func)
    def wrapper(*args, **kwargs):
        import time
        start = time.monotonic()
        error = None
        result = None
        try:
            result = tool_func(*args, **kwargs)
        except Exception as e:
            error = e
        elapsed = time.monotonic() - start

        if SESSION_LOGGER is not None:
            import inspect
            sig = inspect.signature(tool_func)
            bound = sig.bind(*args, **kwargs)
            bound.apply_defaults()
            input_dict = {k: v for k, v in bound.arguments.items()}

            if error:
                SESSION_LOGGER._append({
                    "event": "tool_error",
                    "ts": SESSION_LOGGER._now_iso(),
                    "tool": tool_func.__name__,
                    "input": input_dict,
                    "error": str(error),
                    "error_type": type(error).__name__,
                    "latency_s": round(elapsed, 3),
                })
            else:
                SESSION_LOGGER.log_tool(
                    tool_name=tool_func.__name__,
                    tool_input=input_dict,
                    output=result,
                    latency_s=elapsed,
                )

        if error:
            raise error
        return result

    return wrapper


def _import_abm_run():
    """Lazy import of abm_run tool."""
    from agents.deepagents.tools.abm_tools import abm_run
    return abm_run


def _import_abm_test():
    """Lazy import of abm_test tool."""
    from agents.deepagents.tools.abm_tools import abm_test
    return abm_test


def _import_abm_score():
    """Lazy import of abm_score tool."""
    from agents.deepagents.tools.abm_tools import abm_score
    return abm_score

ORCHESTRATOR_PROMPT = """\
You are the MalariaSentinel Centinela orchestrator. You manage ABM development — calibration, new features, bug fixes, behavior changes, code removal, anything the codebase needs.

ASKING THE USER (ask_user tool):
You have an `ask_user` tool that lets you ask the user a question mid-execution.
USE IT WHENEVER:
- You have multiple hypotheses and want the user to choose the priority
- You found a value/parameter that conflicts with the user's intent
- The change would have non-trivial tradeoffs (e.g., breaking backwards compat)
- You're uncertain about scientific assumptions
- You need clarification on the goal itself

Examples:
- ask_user(question="I found 3 hypotheses for the extinction. Which should I test first?",
           options=["1. Point-source collapse (raise BIRTH_FECUNDITY)",
                    "2. R₀<1 (lower mortality)",
                    "3. Missing oviposition transition (implement G14)"])
- ask_user(question="The field data says mortality=0.10/day but local is 0.07/day. Which?")
- ask_user(question="Should I add a new scorer D15 or modify D2?")

For binary decisions at integrate/finalize, the framework already prompts the user.
For open-ended questions, use ask_user.

YOUR METHODOLOGY (follow this for every goal):

═══════════════════════════════════════════════════════════════════════════════
PHASE 1 — RECONNAISSANCE (mandatory, ~5-10 minutes)
═══════════════════════════════════════════════════════════════════════════════

Before forming any hypothesis, EXPLORE the codebase.

Step 1: Check git history to know what's already been done.
- execute("git log --oneline -30") — recent commits
- execute("git log --oneline -20 --grep='calibration'") — calibration-related work
- execute("git log --oneline -20 --grep='M7'") — milestone work
- Look for "biological calibration", "scorer", "D15" — identify what's already optimized

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
- Comments often link to past proposals and docs

Step 5: Check for version mismatches (binary vs source).
- execute("ls -la mal-core/src/mal_core/abm/build/src/mal_abm_fast")
- execute("git log -1 --format='%ai %s' mal-core/src/mal_core/abm/src/main.cpp")
- If binary is older than source → rebuild before any diagnostic run

Step 6: Find recent calibration outputs.
- ls runs/ — previous rollouts
- ls docs/ — calibration reports
- ls mal-core/src/mal_core/abm/tests/calibration/runs/ — test rollouts

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
   - "wire.hpp:88-91 comment confirms this was a known issue"
   - "code inspection shows only HOST_SEEKING branch is implemented in advance_day()"

5. If you have multiple hypotheses, list and rank them.
   - Rank by likelihood
   - Pick the most likely one to test first

6. If you cannot form a hypothesis, ASK THE USER.
   - State what you know and what you don't know

═══════════════════════════════════════════════════════════════════════════════
PHASE 4 — GATHER CONTEXT (KB, papers, web — in this order)
═══════════════════════════════════════════════════════════════════════════════

Step 9: memory_recall_kg(query="<specific question>", k=5)
  USE FOR:
    - "have we seen this exact symptom before?"
    - "is there a pattern for adding scorers?"
    - "what was the root cause of past calibration failures?"
  DO NOT USE FOR:
    - "how does the ABM work" — you should have read the code
    - "what parameter causes extinction" — the code tells you

Step 10: Read papers/ IF the goal relates to biological plausibility.
  USE FOR: validating parameter values, biological mechanisms
  DO NOT USE FOR: code debugging

Step 11: opencode_search(query="<scientific question>") IF you need field data.
  USE FOR: field mortality rates, dispersal distances, gonotrophic cycle durations
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
  - New scorer → another worker
  - Both can run in parallel (independent files)

  workflow:
  - gitagent_init
  - gitagent_start(feature="<name>")
  - gitagent_spawn(feature="<name>", agent_id="a_fix", role="abm")      # C++ fix
  - gitagent_spawn(feature="<name>", agent_id="a_scorer", role="scorer") # scorer
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

CRITICAL RULES:
- RECONNAISSANCE FIRST — always git log + read code before deciding
- HYPOTHESES BEFORE FIXES — always state the problem with evidence
- DIAGNOSTICS BEFORE FIXES — run the simulation, get the actual data
- ASK WHEN UNCERTAIN — use the ask_user tool to get clarification mid-execution
- BE SPECIFIC — name files, line numbers, parameter names
- PARALLEL WORKERS — spawn independent fixes in parallel
- Always pass --feature to every gitagent command
- Iterations unlimited — keep revising until the change is correct
"""

WORKER_DEFINITIONS = [
    {
        "name": "abm-worker",
        "description": (
            "Modifies ABM C++ code: parameters, behaviors, new features, bug fixes. "
            "Can read/write any file, compile, run tests, and score results. "
            "Use for any change to mal-core/src/mal_core/abm/ or related code."
        ),
        "system_prompt": (
            "You are an ABM development worker in an isolated gitagent worktree. "
            "You can modify ANY part of the C++ codebase — parameters, behaviors, "
            "new features, bug fixes, or remove broken code. "
            "You have access to: read_file, write_file, edit_file, glob, grep (file ops), "
            "execute (shell commands), abm_run (compile + simulate), abm_test (pytest), "
            "abm_score (14 scorers + LLM verdict). "
            "Use opencode_search to find scientific literature if you need parameter ranges "
            "or biological context. Use memory_recall_kg to check past patterns and pitfalls. "
            "Read papers in papers/ directory for domain knowledge. "
            "When your work is done, run from the REPO ROOT: "
            "gitagent propose --feature <name> --agent <your-id> --title '...' --summary '...' --confidence 0.8"
        ),
        "tools": [
            _wrap_with_logging(_import_abm_run()),
            _wrap_with_logging(_import_abm_test()),
            _wrap_with_logging(_import_abm_score()),
        ],
        # Permissions are added dynamically in create_orchestrator() if FilesystemPermission is available
    },
    {
        "name": "research-worker",
        "description": (
            "Literature and knowledge specialist — READ-ONLY. "
            "Searches papers, web, and knowledge base for scientific context. "
            "Use for literature reviews, parameter validation, and biological plausibility checks. "
            "Does NOT modify code — produces structured findings reports."
        ),
        "system_prompt": (
            "You are a research worker specialized in literature review and scientific synthesis. "
            "You work in an isolated gitagent worktree but you are READ-ONLY — you do not modify code. "
            "Your job: gather, synthesize, and report scientific findings. "
            "Tools you have: opencode_search (web search), memory_recall_kg (knowledge base), "
            "read_file, glob, grep (read papers, docs, configs). "
            "DO NOT use write_file, edit_file, abm_run, abm_test, or abm_score — that's the abm-worker's job. "
            "When done, report back via: "
            "gitagent propose --feature <name> --agent <your-id> --title '...' --summary '...' --confidence 0.8"
        ),
        "tools": [],  # Read-only — uses only deepagents' default filesystem tools
        # Permissions are added dynamically in create_orchestrator() with strict read-only enforcement
    },
]


def _gitagent_finalize_wrapped(feature: str, message: str) -> str:
    """Wrapper that injects the verify flag from module-level setting."""
    return gitagent_finalize(feature, message, verify=VERIFY_FINALIZE)


def _gitagent_integrate_wrapped(feature: str) -> str:
    """Wrapper that injects the verify flag from module-level setting."""
    return gitagent_integrate(feature, verify=VERIFY_INTEGRATE)


TOOLS = [
    _wrap_with_logging(opencode_search),
    _wrap_with_logging(gitagent_init),
    _wrap_with_logging(gitagent_start),
    _wrap_with_logging(gitagent_spawn),
    _wrap_with_logging(gitagent_list_agents),
    _wrap_with_logging(gitagent_kill),
    _wrap_with_logging(gitagent_proposals),
    _wrap_with_logging(gitagent_diff),
    _wrap_with_logging(gitagent_accept),
    _wrap_with_logging(gitagent_reject),
    _wrap_with_logging(gitagent_revise),
    _wrap_with_logging(_gitagent_integrate_wrapped),
    _wrap_with_logging(_gitagent_finalize_wrapped),
    _wrap_with_logging(pipeline_run_calibration),
    _wrap_with_logging(pipeline_compare_scorecards),
    _wrap_with_logging(memory_recall_kg),
    _wrap_with_logging(improve_prompt),
    _wrap_with_logging(ask_user),
]

MEMORY_FILES = [str(AGENT_DIR / "AGENTS.md")]


def _resolve_provider(provider: str, model: str):
    """Resolve the LLM based on provider and model."""
    if provider == "openrouter":
        try:
            from langchain_openai import ChatOpenAI
        except ImportError:
            raise ImportError(
                "langchain-openai is required for OpenRouter. "
                "Install with: pip install 'mal-deepagents[openrouter]'"
            )
        api_key = os.environ.get("OPENROUTER_API_KEY") or os.environ.get("OPENROUTER_KEY")
        if not api_key:
            raise ValueError("OPENROUTER_API_KEY or OPENROUTER_KEY env var required for OpenRouter provider")
        return ChatOpenAI(
            model=model,
            base_url="https://openrouter.ai/api/v1",
            api_key=api_key,
        )
    else:
        try:
            from langchain.chat_models import init_chat_model
        except ImportError:
            raise ImportError(
                "langchain-core is required. Install with: pip install deepagents"
            )
        return init_chat_model(model=model, model_provider=provider)


def create_orchestrator(
    provider: str = "openrouter",
    model: str = "xiaomi/mimo-v2.5",
    thread_id: str = "centinela-session",
):
    """Create the main orchestrator agent using deepagents.

    Args:
        provider: LLM provider ("openrouter", "anthropic", "openai", "google_genai").
        model: Model identifier.
        thread_id: Thread ID for checkpointing.

    Returns:
        A compiled agent graph ready to invoke.

    Raises:
        ImportError: If required packages are not installed.
    """
    try:
        from deepagents import create_deep_agent, FilesystemPermission
        from deepagents.backends import FilesystemBackend
    except ImportError:
        raise ImportError(
            "The 'deepagents' package is required but not installed. "
            "Install it with: pip install 'mal-deepagents' or pip install deepagents"
        )

    llm = _resolve_provider(provider, model)

    backend = FilesystemBackend(
        root_dir=str(REPO_ROOT),
        virtual_mode=True,
    )

    # Build observability middleware if logger is active
    middleware = []
    if SESSION_LOGGER is not None:
        middleware.append(ObservabilityMiddleware(SESSION_LOGGER))

    skills = []
    if PROJECT_SKILLS.is_dir():
        skills.append("agents/skills/")

    # Add permissions to worker definitions dynamically
    worker_defs = []
    for w in WORKER_DEFINITIONS:
        wd = dict(w)
        if w["name"] == "research-worker":
            # Strict read-only: deny ALL writes, allow reads (except secrets)
            wd["permissions"] = [
                FilesystemPermission(operations=["read"], paths=["/.env", "/**/.env", "/**/*secret*", "/**/*credential*"], mode="deny"),
                FilesystemPermission(operations=["write"], paths=["/**"], mode="deny"),
                FilesystemPermission(operations=["read"], paths=["/**"], mode="allow"),
            ]
        else:
            # abm-worker: deny secrets and data writes, allow writes to code
            wd["permissions"] = [
                FilesystemPermission(operations=["read"], paths=["/.env", "/**/.env", "/**/*secret*", "/**/*credential*"], mode="deny"),
                FilesystemPermission(operations=["write"], paths=["/data/**"], mode="deny"),
                FilesystemPermission(operations=["write"], paths=["/.gitagent/**", "/.git/**"], mode="deny"),
                FilesystemPermission(operations=["read", "write"], paths=["/**"], mode="allow"),
            ]
        worker_defs.append(wd)

    return create_deep_agent(
        model=llm,
        tools=TOOLS,
        subagents=worker_defs,
        system_prompt=ORCHESTRATOR_PROMPT,
        backend=backend,
        skills=skills or None,
        name="centinela-orchestrator",
        middleware=middleware,
        permissions=[
            FilesystemPermission(operations=["read"], paths=["/.env", "/**/.env", "/**/*secret*", "/**/*credential*"], mode="deny"),
            FilesystemPermission(operations=["write"], paths=["/**"], mode="deny"),
            FilesystemPermission(operations=["read"], paths=["/**"], mode="allow"),
        ],
    )

