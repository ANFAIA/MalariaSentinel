# Plan: Dual-Mode Orchestrator (Centinela + Dispatcher)

> Status: proposed
> Created: 2026-08-09
> Related: specialist dual-mode (`[MODE:research]` / `[MODE:implementation]`)
> Files: `agents/janus/src/agents_janus/`

## Problem

Two orchestrators exist as completely separate codepaths:

```
janus (bare)                    janus improve -g "..."
     │                                │
     ▼                                ▼
onboarding.py                   improvement.py
_build_agent()                  create_orchestrator()
     │                                │
create_deep_agent(             create_deep_agent(
  tools=onboard_tools,            tools=TOOLS + gawt_mcp,
  subagents=NONE,                 subagents=8,
  prompt=inline string,           prompt=orchestrator.md,
  perms=r/w-deny,                 perms=r/w-deny,
)                               )
     │                                │
REPL loop                      single-shot stream
```

Issues:
1. **Code duplication** — two agent creation paths, two LLM resolvers, two backends
2. **Onboarding has no subagent dispatch** — can't use `task()`. Uses `onboard_ask_subagent()` which does a raw LLM call (no tools, no worktree context)
3. **Blocking delegation** — `onboard_delegate()` → `handoff_to_improver()` → `run_improvement()` runs the entire pipeline synchronously inside the REPL. User sees no output
4. **`ask_user` missing from subagent tool lists** — prompt tells them to use it, but it's not bound
5. **Prompt inconsistency** — onboarding prompt inline, dispatcher prompt on disk

## Solution

Apply the same dual-mode pattern from subagents to orchestrators:
**one shared structure, two modes, conditional sections**.

### Architecture

```
create_orchestrator(mode="centinela")    create_orchestrator(mode="dispatcher")
  │                                        │
  ├─ prompt: orchestrator.md.j2            ├─ prompt: orchestrator.md.j2
  │  (rendered mode=centinela)              │  (rendered mode=dispatcher)
  │                                        │
  ├─ tools: onboard + ask_user             ├─ tools: pipeline + gawt_mcp + ask_user
  │  + memory_kg + delegate_to_disp        │  + memory_kg
  │                                        │
  ├─ subagents: 8 specialists ✅            ├─ subagents: 8 specialists ✅
  │                                        │
  └─ perms: r-all, w-deny                  └─ perms: r-all, w-deny
```

### Prompt Template (`orchestrator.md.j2`)

Jinja2 template with two protocol sections, same pattern as `specialist.md.tmpl`:

```j2
{% if mode == "centinela" %}
## Centinela Protocol
(conversational REPL, explain-then-delegate, onboard tools)
{% endif %}

{% if mode == "dispatcher" %}
## Dispatcher Protocol
(decompose → session → dispatch → monitor → finalize)
{% endif %}
```

### Delegation Model

```
User says "Fix population extinction"
         │
    Centinela (REPL)
         │
         ├─── "I'll investigate first"
         │    task("abm", "[MODE:research] What causes extinction?")
         │    (dispatches research specialist directly, no gawt needed)
         │
         ├─── "Found it. Now I'll fix it."
         │    delegate_to_dispatcher(goal="Fix adult survival calculation in D14")
         │         │
         │         ▼
         │    Dispatcher (one-shot stream)
         │         ├── start_session
         │         ├── task("scoring", "[MODE:implementation] Fix D14...")
         │         ├── monitor
         │         └── finalize → returns summary
         │
         └─── "Fixed. Here's what changed: ..."
              (Centinela explains to user)
```

### Tool Matrix

| Tool | Centinela | Dispatcher | Subagents |
|---|---|---|---|
| `ask_user` | ✅ | ✅ | ✅ (fix) |
| `memory_recall_kg` | ✅ | ✅ | via plugin |
| `onboard_run_*` | ✅ | ❌ | ❌ |
| `onboard_status` | ✅ | ❌ | ❌ |
| `onboard_diagnose` | ✅ | ❌ | ❌ |
| `onboard_ask_subagent` | ✅ | ❌ | ❌ |
| `delegate_to_dispatcher` | ✅ | ❌ | ❌ |
| `pipeline_*` | ❌ | ✅ | via plugin |
| `gawt_mcp_*` | ❌ | ✅ | ✅ |
| `task()` (subagents) | ✅ | ✅ | ❌ |
| `opencode_search` | ❌ | ✅ | ❌ |
| `improve_prompt` | ❌ | ✅ | ❌ |

### Delegation Rules

- **Research tasks**: centinela dispatches directly via `task()` (no session needed, read-only)
- **Implementation tasks**: centinela delegates to dispatcher via `delegate_to_dispatcher(goal)` (dispatcher manages session lifecycle)
- **Quick questions**: centinela uses `onboard_ask_subagent(name, question)` (lightweight, single LLM call)
- **Complex goals**: centinela can chain research + delegation: first investigate, then delegate implementation
- **Plan-guided**: `delegate_to_dispatcher` accepts optional `plan_path` — dispatcher reads the plan file as context for decomposition

## Files to Change

| # | File | Action | Detail |
|---|---|---|---|
| 1 | `prompts/orchestrator.md` | Delete | Replaced by template |
| 2 | `prompts/orchestrator.md.j2` | **Create** | Jinja2 template with centinela + dispatcher protocols |
| 3 | `agent.py` | Modify | `create_orchestrator(mode)`, render template, conditional tools, pass `mode` to middleware |
| 4 | `onboarding.py` | Modify | Remove `_build_agent()`, use `create_orchestrator(mode="centinela")`, keep REPL loop |
| 5 | `improvement.py` | Modify | Use `create_orchestrator(mode="dispatcher")`, keep stream + panel |
| 6 | `tools/onboard_tools.py` | Modify | Remove `onboard_delegate`, add `delegate_to_dispatcher` (with `plan_path` + Langfuse delegation span) |
| 7 | `tools/subagent_invoke.py` | **Delete** | Replaced by `delegate_to_dispatcher` |
| 8 | `cycles/improvement_cycle.py` | **Delete** | Shim → `run_improvement()`, no longer needed |
| 9 | `agent.py` (subagent setup) | Modify | Add `ask_user` to subagent tool lists |
| 10 | `observability.py` | Modify | Add `mode` param, `mode:` tag, `delegate_to_dispatcher` tool category |
| 11 | `cli.py` | Modify | Add `--plan` to centinela mode (passed through `delegate_to_dispatcher`) |
| 12 | `AGENTS.md` | Update | Document dual-mode orchestrator architecture |

## Step-by-Step Execution

### Step 1: Create `prompts/orchestrator.md.j2`

Convert `orchestrator.md` to Jinja2 template. Add centinela protocol section.
Keep dispatcher protocol as-is. Both share: preamble, "you do NOT", subagent access, knowledge graph.

### Step 2: Refactor `create_orchestrator()` in `agent.py`

```python
def create_orchestrator(
    mode: Literal["centinela", "dispatcher"] = "dispatcher",
    ...
):
```

- Render `orchestrator.md.j2` with `mode` kwarg via Jinja2
- Load correct tool set based on mode
- Both modes: build subagent definitions (8 specialists)
- Both modes: `ask_user` + `memory_recall_kg`
- Dispatcher: add gawt MCP + pipeline tools
- Centinela: add onboard tools + `delegate_to_dispatcher`

### Step 3: Simplify `onboarding.py`

Replace `_build_agent()` with call to `create_orchestrator(mode="centinela")`.
Keep the REPL loop (`while True: input → stream → print`).

### Step 4: Simplify `improvement.py`

Use `create_orchestrator(mode="dispatcher")`.
Keep stream loop + `_emit_panel_events()` + LivePanel.

### Step 5: Create `delegate_to_dispatcher` tool

New function in `tools/onboard_tools.py`:
```python
def delegate_to_dispatcher(
    goal: str,
    context: str = "{}",
    plan_path: str = "",
    provider: str = "openrouter",
    model: str = "xiaomi/mimo-v2.5",
) -> str:
    """Delegate implementation work to the dispatcher orchestrator.
    
    Args:
        goal: The objective for the dispatcher.
        context: JSON string with additional context (research findings, etc.).
        plan_path: Optional path to a plan file. If provided, the dispatcher
                   reads it as context for decomposition (equivalent to
                   `janus improve -g "..." --plan <path>`).
        provider: LLM provider (default: openrouter).
        model: Model identifier (default: xiaomi/mimo-v2.5).
    
    Creates a dispatcher orchestrator, streams until done, returns summary.
    Runs in a separate LangGraph invocation (not nested in REPL).
    """
```

Plan path flows: `delegate_to_dispatcher(plan_path="docs/plans/in-process/foo.md")`
→ `run_improvement(plan_path=...)` → prompt includes plan content as context.

This replaces the old `onboard_delegate()` which called `handoff_to_improver()`.

### Step 6: Remove dead code

- Delete `tools/subagent_invoke.py`
- Delete `cycles/improvement_cycle.py`
- Remove `onboard_delegate` from `tools/onboard_tools.py`
- Remove `onboard_delegate` from `_build_agent()` tool list in `onboarding.py` (if still there)

### Step 7: Fix `ask_user` for subagents

In `agent.py`, when building subagent tool lists, include `ask_user`:
```python
all_tools.extend(plugin.tools(spec))
all_tools.extend(gawt_tools)
all_tools.append(ask_user)  # ← add this
```

### Step 8: Update `AGENTS.md`

Document the dual-mode orchestrator architecture, delegation model, tool matrix.

## Verification

```bash
# 1. Import check
cd agents/janus && uv run python -c "from agents_janus.agent import create_orchestrator; print('OK')"

# 2. Template renders
uv run python -c "
from agents_janus.agent import _render_prompt
print(_render_prompt('centinela')[:200])
print('---')
print(_render_prompt('dispatcher')[:200])
"

# 3. Both modes create agents
uv run python -c "
from agents_janus.agent import create_orchestrator
a1 = create_orchestrator(mode='centinela')
a2 = create_orchestrator(mode='dispatcher')
print(f'centinela tools: {len(a1.tools)}')
print(f'dispatcher tools: {len(a2.tools)}')
"

# 4. Langfuse tags include mode
uv run python -c "
from agents_janus.observability import ObservabilityMiddleware
from agents_janus.logger import SessionLogger
obs = ObservabilityMiddleware(SessionLogger(), mode='centinela')
print(obs._build_base_tags())
# Expected: ['agent:orchestrator', 'env:dev', 'mode:centinela']
"

# 5. Tests still pass
uv run pytest tests/ -v --tb=short
```

## Langfuse Integration

### Current State

Langfuse tracing is already functional via `ObservabilityMiddleware` + `SubAgentObservabilityMiddleware`:
- One root span per session (`janus_session`)
- Nested generations for LLM calls (with `agent:<role>`, `stage:`, `tool:` tags)
- Nested spans for tool calls (with category tags)
- Dispatch spans per specialist (nested under root)
- Scores: `latency_s`, `token_efficiency`, `error_rate`
- `--tracing langfuse` CLI flag + `LANGFUSE_HOST`, `LANGFUSE_PUBLIC_KEY`, `LANGFUSE_SECRET_KEY` env vars

### What Changes

**1. Tag: `mode:centinela` / `mode:dispatcher`**

Add `mode` tag to the root span so Langfuse traces are filterable by orchestrator mode.

```python
# In ObservabilityMiddleware.before_agent():
base_tags = [
    f"agent:{self._current_agent_role}",
    f"env:{self._env}",
    f"mode:{self._mode}",          # ← NEW
    "stage:start",
]
```

**2. Delegation span: `delegate:dispatcher`**

When centinela calls `delegate_to_dispatcher()`, the dispatcher's entire trace should nest under a delegation span in the centinela's trace. This gives a tree:

```
Centinela trace (mode:centinela)
├── LLM call: "I'll investigate"
├── task("abm", "[MODE:research] ...")     ← dispatch span
│   └── Specialist abm trace
├── delegate_to_dispatcher("Fix D14")      ← delegation span
│   └── Dispatcher trace (mode:dispatcher)
│       ├── start_session
│       ├── task("scoring", "[MODE:implementation] ...")
│       │   └── Specialist scoring trace
│       └── finalize_session
└── LLM call: "Fixed. Here's what changed."
```

Implementation: `delegate_to_dispatcher` opens a Langfuse span via `SESSION_OBSERVABILITY.start_dispatch_span("dispatcher", task=goal)`, runs the dispatcher, closes the span. The dispatcher's `ObservabilityMiddleware` receives the centinela's `trace_context` as parent.

**3. Pass `langfuse_client` + `trace_context` through delegation**

```python
def delegate_to_dispatcher(goal, context, plan_path, ...):
    # Create dispatcher with shared langfuse client
    from agents_janus.agent import create_orchestrator
    
    dispatcher = create_orchestrator(
        mode="dispatcher",
        langfuse_client=_get_centinela_langfuse_client(),  # reuse same client
        goal=goal,
        env=env,
    )
    # ... stream ...
```

The dispatcher's `ObservabilityMiddleware` opens its own root span, which nests under the centinela's trace because both share the same `langfuse_client` and the langfuse SDK maintains the trace context across calls.

**4. Add `mode` to `create_orchestrator()` parameters passed to middleware**

```python
# In create_orchestrator():
obs = ObservabilityMiddleware(
    SESSION_LOGGER,
    langfuse_client=langfuse_client,
    goal=goal,
    thread_id=thread_id,
    env=env,
    iteration=iteration,
    mode=mode,          # ← NEW: stored for tag building
)
```

**5. Add `delegate_to_dispatcher` to tool category map**

```python
# In observability.py _TOOL_CATEGORIES:
"delegate_to_dispatcher": "dispatch",
```

**6. Dispatcher plan_path in trace metadata**

When `plan_path` is provided, include it in the dispatcher's root span metadata:
```python
root_metadata["plan_path"] = plan_path  # if provided
```

### Files to Change (Langfuse-specific)

| File | Change |
|---|---|
| `observability.py` | Add `mode` param to `__init__`, add `mode:` tag to base tags, add `delegate_to_dispatcher` to tool categories |
| `agent.py` | Pass `mode` to `ObservabilityMiddleware` |
| `tools/onboard_tools.py` | `delegate_to_dispatcher` opens/closes delegation span, passes langfuse_client to dispatcher |

### What Does NOT Change

- `SubAgentObservabilityMiddleware` — unchanged (specialists still get dispatch spans)
- Langfuse SDK version — still `>=4.0`
- Scores — same `latency_s`, `token_efficiency`, `error_rate`
- CLI flags — same `--tracing langfuse`, `--env`
- Env vars — same `LANGFUSE_HOST`, `LANGFUSE_PUBLIC_KEY`, `LANGFUSE_SECRET_KEY`

## CLI Interface

```bash
# Conversational mode (default)
janus                          # starts centinela REPL
janus --tracing langfuse       # with Langfuse tracing
janus --env production         # with environment tag

# Goal-driven mode
janus improve -g "Fix D14"                        # dispatcher, single goal
janus improve -g "Fix D14" --plan docs/plans/foo.md  # with plan context
janus run -g "..." --tracing langfuse             # with Langfuse tracing

# Inside the centinela REPL:
you> Fix the population extinction bug
     → centinela delegates to dispatcher internally
     → dispatcher receives the goal, no plan (decomposes itself)

you> /plan docs/plans/in-process/calibration.md
     → centinela sets plan context for future delegations
you> Fix the scoring issues
     → centinela delegates with plan_path=calibration.md
     → dispatcher reads plan, uses it for decomposition
```

The `--plan` flag on `janus improve` is equivalent to `delegate_to_dispatcher(plan_path=...)` inside the centinela. Both flow into `run_improvement(plan_path=...)`.

## Risk Notes

- **`delegate_to_dispatcher` is still blocking** — it creates a new LangGraph agent and streams until done. The centinela REPL is paused during this. This is acceptable because: (a) the user sees LivePanel output, (b) it's the same as current `run_improvement()`.
- **gawt session singleton** — only one session at a time. If centinela dispatches research specialists while dispatcher has a session open, there's a conflict. Mitigation: centinela doesn't open sessions; only the dispatcher does.
- **Subagent tool overlap** — subagents get both plugin tools AND gawt MCP tools. Research-mode subagents don't need gawt tools. Consider filtering in a future iteration.
- **Langfuse trace nesting** — the centinela and dispatcher share the same `langfuse_client`. The langfuse SDK propagates trace context automatically when using `start_as_current_observation`. The dispatcher's root span nests under the centinela's delegation span. If the SDK version doesn't support this, the traces will appear as separate root traces (degraded but functional).
