# M16 — Registry Integration + Sibling Coordination

> **Status**: Draft (2026-08-05). Supersedes the integration gap in M14 (`docs/plans/completed/m14-orchestrator-plugin-system.md`).
>
> **Predecessor**: M14 — Two-Tier Orchestrator + Plugin System (commit `46fadfb`). M14 shipped the registry, builder, 10 plugins, mailbox, scope validator, and 9 subagents in YAML — but the orchestrator never wired them into the runtime. This plan finishes that integration AND adds the cooperative-sibling layer.
>
> **Sibling work**: M15 — Observability (live panel + Langfuse) — already shipped in `agents/janus/src/agents_janus/live_panel.py` and `observability.py`. M16 builds on the trace pipeline so the sibling layer is debuggable.
>
> **Scope**: Finish the M14 dead code AND add the sibling coordination system. No `mal-core` changes. No new `docs/specs/<x>/spec.md`. No new KB labels. The sibling layer is **internal to the orchestrator runtime** — invisible to the user, exercised via a dedicated test prompt + a trace-analyzer agent.

## 0. Why this plan exists now

Three things converged:

1. **M14's dead code**: 9 subagents exist in `agents/janus/src/agents_janus/config/subagents.yaml`, but `agents/janus/src/agents_janus/agent.py::create_orchestrator` still uses two hardcoded `WORKER_DEFINITIONS` (`abm-worker` + `research-worker`). The registry, builder, `spec_loader`, `affects.py`, and `plugin.tools()` are all written but never called. M14 was "completed" structurally; the integration thread was never closed.

2. **The cooperative-worktree problem**: When `abm-worker` needs to invoke `scoring-worker` over the same code change, or `abm-worker` needs `data-worker` to produce inputs first, M14 assumes "one subagent = one worktree = one task". That breaks the moment two specialists need to **share** a worktree and **cooperate** on the same code surface. The user explicitly raised this: "si separas es posible que los que dejes de lado no se lleguen a implementar" — we need all 9 subagents working together, not isolated.

3. **Context drift on sibling wakeups**: When a sibling receives a notification mid-task (new sibling joined, file changed, conflict detected), the injected tokens compete for attention with the original goal. The agent loses focus. The user proposed a "branch of the agent's history and merge it back later" model. Investigation located prior art: conversation forking (forky, Branch Agent, Warp), SCAN protocol output-restoring markers, and Interrupt-Resumable Thought frames. The user picked all three.

**Additionally**, the user specified transparency: the sibling layer is **internal**. No `--siblings` flag, no `--watcher-mode` UI. The orchestrator decides when to spawn siblings. The orchestrator decides which internals tool to expose. The user triggers it via a **test prompt** that asks Janus to run a full system trial, and a **separate trace-analyzer agent** (a janus subagent with trace-reading tools) confirms by reading the Langfuse trace.

## 1. M14 gap × M16 closure

| M14 layer | Shipped | Wired in M16 |
|---|---|---|
| `subagents/registry.py` (9 entries) | Code complete | ✅ Called by `create_orchestrator(tier)` |
| `subagents/builder.py` (`build_resolved`) | Code complete | ✅ Called for every subagent build |
| `plugins/*` (10 plugins) | Code complete | ✅ `plugin.tools()` + `plugin.permissions()` assembled into the subagent |
| `config/subagents.yaml` | 9 entries | ✅ Single source of truth — `agent.py` drops the hardcoded `WORKER_DEFINITIONS` |
| `spec_loader.py` | Code complete | ✅ Wired into `build_subagent_prompt()` as **one of four layers** — specs are behavioral contracts loaded INTO the prompt, not the prompt itself |
| `affects.py` | Code complete | ✅ `compose_affected_notifications()` fires on spec change |
| `mailbox.py` | inbox only | ✅ Extended with `peer_message` (sibling↔sibling within a shared worktree) |
| `scope_validator.py` | pure data | ✅ Wired into `gitagent_propose` hook (was prompt-only) |
| M15: `live_panel.py` + `observability.py` | Code complete | ✅ Provides the trace substrate for the test harness |
| **NEW**: sibling coordination layer | — | ✅ `sibling/coordination.py` (in-process) |
| **NEW**: tree-sitter AST index | — | ✅ `sibling/ast_index.py` (Python v1) |
| **NEW**: fork sub-context | — | ✅ `sibling/fork.py` (forky-style) |
| **NEW**: SCAN markers | — | ✅ `sibling/scan.py` |
| **NEW**: frame stack | — | ✅ `sibling/frame_stack.py` |

## 2. Architecture (mermaid)

```
                    ┌────────────────────────────────────┐
                    │  improvement orchestrator           │
                    │  create_orchestrator(tier='improve') │
                    │  registry.get(name) → resolve       │
                    │  chain(EditPlugin, [subagent-plugins])│
                    │  tools: 17 M14 + 4 M16 (sibling)   │
                    │  + handoff_to_subagent (replaces task) │
                    └──────────────┬─────────────────────┘
                                   │ handoff_to_subagent(name, brief)
                    ┌──────────────▼─────────────────────┐
                    │ primary subagent                   │
                    │  - creates worktree (gitagent)     │
                    │  - registers claim_file in SQLite  │
                    │  - invokes siblings via peer_message│
                    │  - owns coordinate_state.wal        │
                    └──────┬───────────────┬─────────────┘
                           │               │
                  ┌────────▼──────┐  ┌─────▼────────┐
                  │ sibling #1    │  │ sibling #2   │
                  │ (scoring)     │  │ (ingest)     │
                  │ shared WT     │  │ shared WT    │
                  │ claim_file()  │  │ claim_file() │
                  └──────┬────────┘  └──────┬───────┘
                         │                 │
                  ┌──────▼─────────────────▼──────┐
                  │ sibling runtime (in-process)     │
                  │  - watcher (python watchdog)    │
                  │  - ast_index (tree-sitter)      │
                  │  - merge_preflight (git)        │
                  │  - coordination (intent daemon) │
                  │  - fork orchestrator             │
                  │  - sqlite WAL (state)            │
                  └──────┬──────────────────────────┘
                         │
                  ┌──────▼──────────────────────────┐
                  │ peer_message inbox               │
                  │  inbox-<primary>/peer_msg.json  │
                  │  Triggers: Sibling AddEvent      │
                  │   → push_frame, fork_brief,      │
                  │     negotiate, merge_result      │
                  └─────────────────────────────────┘
```

## 3. Registry-driven dispatch (Layer 1)

```python
# agent.py — REPLACE the hardcoded WORKER_DEFINITIONS
def create_orchestrator(*, tier: str, **kwargs) -> CompiledStateGraph:
    if tier not in ("onboarding", "improve"):
        raise ValueError(f"unknown tier: {tier}")

    registry = load_registry(CONFIG_DIR / "subagents.yaml")
    plugins = [ReadOnlyPlugin()] if tier == "onboarding" else [EditPlugin()]
    chain = plugins + [PLUGIN_REGISTRY[name]() for name in registry.all_plugins()]

    prompt = build_orchestrator_prompt(tier, registry)
    tools = build_orchestrator_tools(tier, registry, chain)

    return build_deepagent(
        model=resolve_model(kwargs),
        system_prompt=prompt,
        tools=tools,
        middleware=[
            ObservabilityMiddleware(...),
            ScopeValidatorMiddleware(registry=registry),  # ← NEW
            SiblingCoordinatorMiddleware(registry=registry),  # ← NEW
        ],
    )
```

**What changes**: `subagents.yaml` becomes the source of truth. `agent.py` no longer enumerates workers. The orchestrator's tool list is computed from `(tier, registry, plugin chain)`.

**Backward compat**: `WORKER_DEFINITIONS` becomes a thin alias that lazy-loads from the registry. Existing `task(subagent_type="abm-worker")` calls keep working — the alias resolves "abm-worker" → registry entry "abm".

## 4. Plugin-driven tool assembly (Layer 2)

```python
# subagents/builder.py — already exists, but never called
def build_resolved(spec: SubagentSpec, plugins: list[Plugin]) -> ResolvedSubagent:
    resolved = ResolvedSubagent(spec=spec)
    for plugin in plugins:
        resolved = plugin.apply(resolved)
    return resolved

# M16: ALL tools are contributed by plugins, no global TOOLS constant
def build_subagent(spec: SubagentSpec, *, tier: str) -> CompiledSubagent:
    plugins = [PLUGIN_REGISTRY[name]() for name in spec.plugins]
    if tier == "improve":
        plugins.insert(0, EditPlugin())  # improver always gets edit
    elif tier == "onboarding":
        plugins.insert(0, ReadOnlyPlugin())  # onboarding always read-only

    resolved = build_resolved(spec, plugins)
    return build_deepagent(
        model=resolve_model(spec),
        system_prompt=resolved.spec.system_prompt or build_subagent_prompt(spec),
        tools=list(resolved.tools),
        permissions=list(resolved.permissions),
        middleware=resolved.middleware,
    )
```

**What changes**: `plugin.tools()` returns the per-subagent tool list. The orchestrator's `TOOLS` constant is deleted. Each subagent's toolset is computed at runtime from the plugin chain.

### 4.1 Plugin chain propagation across handoffs

The tier parameter (`onboarding` vs `improve`) only applies to the **top-level orchestrator**. When that orchestrator invokes a subagent, and that subagent invokes another, the capability chain must propagate — but **with constraints** derived from SPEC.rb edits, not from the parent's tier.

```
[user]
   ↓
[onboarding-orchestrator]      tier=onboarding, plugins=[ReadOnly]
   ↓ handoff_to_subagent(improve, goal)
[improvement-orchestrator]     tier=improve, plugins=[Edit, Scorer, Download, ...]
   ↓ handoff_to_subagent(abm, brief)
[abm-worker]                   caller=improve, plugins=[Edit] ∪ spec.plugins
   ↓ handoff_to_subagent(scoring, brief)  ← sibling of abm
[scoring-worker]               caller=abm, plugins=[ReadOnly+Write] ∪ spec.plugins
```

**Rule**: the plugin chain of an invoked subagent is computed as:

```python
def compute_plugins_for_invocation(
    spec: SubagentSpec,
    caller_plugin_chain: list[Plugin],
    *,
    caller_tier: str,
) -> list[Plugin]:
    """Derive the plugin chain for an invoked subagent.

    Constraints:
    1. The tier guard always applies at the TOP level.
       - Top-level onboarding → can ONLY invoke improver (ReadOnly-orchestrator
         cannot invoke editing subagents directly).
       - Top-level improve → can invoke any subagent.

    2. Once you cross to the improver, downstream subagents are NOT automatic
       EditPlugin users. Each subagent gets its own capability chain derived
       from the CALLER's chain (not the original orchestrator's tier):

       - If the caller's chain includes EditPlugin → the subagent inherits
         write capability (EditPlugin remains in its chain).
       - If the caller's chain is ReadOnly-only → the subagent gets
         ReadOnlyPlugin (cannot write, even if improver called it).

    3. Per-subagent plugins (Scoring, Download, etc.) from spec.plugins are
       ALWAYS applied — they are the subagent's domain tooling, not auth.

    4. The sibling layer adds a SiblingPlugin (read+write + peer_message +
       fork_brief) ONLY when the call is a sibling invocation within a
       shared worktree. A non-sibling handoff does NOT get SiblingPlugin.
    """
    chain = []

    # 1. Apply capability based on caller's plugin chain, not original tier.
    caller_has_edit = any(isinstance(p, EditPlugin) for p in caller_plugin_chain)
    if caller_has_edit:
        chain.append(EditPlugin())
    else:
        chain.append(ReadOnlyPlugin())

    # 2. Sibling layer (only on shared-worktree calls — detected by caller
    #    being a sibling of the same primary).
    if is_sibling_invocation(caller_plugin_chain):
        chain.append(SiblingPlugin(shared_worktree_id=current_worktree_id()))

    # 3. Per-subagent domain plugins (from spec.plugins in YAML).
    for name in spec.plugins:
        chain.append(PLUGIN_REGISTRY[name]())

    return chain
```

**Concrete walkthrough**:

| Step | Caller | Callee | Caller chain | Callee chain |
|---|---|---|---|---|
| 1 | user | onboarding | (none) | `[ReadOnly]` |
| 2 | onboarding | improver | `[ReadOnly]` | `[Edit]` (tier bypass) |
| 3 | improver | abm | `[Edit]` | `[Edit, Scorer]` |
| 4 | abm (sibling spawn) | scoring | `[Edit, Scorer]` | `[Edit, Scoring]` (sibling — share worktree) |
| 5 | improver | data | `[Edit]` | `[Edit, Data]` |
| 6 | improver | research | `[Edit]` | `[Edit, Research]` |

**Edge case — onboarding's direct subagent call (bypass)**:

Onboarding's `handoff_to_subagent(name, brief)` is **always overridden** to forward to the improver. Onboarding cannot directly invoke editing subagents. This is enforced in `subagent_invoke.py`:

```python
def handoff_to_subagent(name: str, brief: str) -> ToolResult:
    if current_tier() == "onboarding" and name != "improver":
        return ToolResult(
            error=(
                f"onboarding cannot invoke subagent '{name}' directly. "
                f"Use handoff_to_improver(goal, context) instead."
            )
        )
    ...
```

**Why this matters for the sibling layer**: when improver spawns siblings `abm` + `scoring`, BOTH inherit EditPlugin (caller has it). They share the worktree. The SiblingPlugin is added because they are siblings — not because of the parent's tier. If `abm` (sibling) later invokes `data` to fetch inputs, `data` gets `[Edit, Data, Sibling]` (still a sibling of the same worktree), and **retains write capability** because EditPlugin is in the chain.

**Adding plugins is also propagatable**: if a new plugin `XXXPlugin` is added to the improver's chain via `subagents.yaml`, that plugin is inherited by all subagents the improver invokes — both directly and through siblings. Spec changes propagate.

## 5. Specs as behavioral contracts (Layer 3)

Specs are **NOT** the agent's prompt. They are technical specifications that describe **the expected behavior** of a subagent's surface — inputs, outputs, invariants, side effects, exceptions. They are the **source of truth** for how each subagent should behave, and they are **dynamic** — they evolve over time as the system improves.

The relationship is:

```
docs/specs/<X>/spec.md          ← Behavioral specification (WHAT)
agents/janus/prompts/
  ├── common_role.md.j2          ← Common prompt (WHO you are)
  ├── per_subagent/
  │   ├── abm.md.j2              ← Per-subagent additions (DOMAIN)
  │   └── commonlib.md.j2
  └── sibling_protocol.md.j2     ← Sibling protocol (HOW to interact)
```

### 5.1 Three layers of prompt material

**Layer A — Specs (`docs/specs/<X>/spec.md`)**:
- Behavior contract: what the subagent must do, what inputs it accepts, what outputs it produces, what invariants it must preserve.
- The `affects` block declares which other specs change when this one changes.
- Loaded INTO the prompt at runtime via `spec_loader.load_spec_for_prompt(spec_path)`.
- Function: shape behavior, inform the agent about cross-spec dependencies, alert the agent when it should call sibling specialists.
- Never edited by the agent at runtime. Mutated by the improve loop after each successful run.

**Layer B — Common prompt (`prompts/common_role.md.j2`)**:
- Identical for ALL subagents.
- Explains: who you are in the system, what your capabilities are, what your duties are to make the system work.
- Includes: the cascade-and-handoff protocol, the mailbox protocol, the sibling coordination protocol, the "call brothers when needed" rule.
- Single source of truth for the rules every subagent must follow.

**Layer C — Per-subagent prompt (`prompts/per_subagent/<name>.md.j2`)**:
- Subagent-specific clarifications: domain language, key file paths, common pitfalls from `AGENTS.md`.
- Tool-naming hints, terminology the agent should use.
- Domain-only — does NOT include role/duty boilerplate (that's in Layer B).

### 5.2 How the three layers compose

```python
# subagents/builder.py — REWRITTEN
def build_subagent_prompt(
    spec: SubagentSpec,
    *,
    plugin_chain: list[Plugin],
) -> str:
    """Compose the full system prompt from three layers + plugins."""

    # Layer A: behavioral spec (from docs/specs/<X>/spec.md)
    spec_text = load_spec_for_prompt(spec.spec_path) if spec.spec_path else ""

    # Layer B: common role (identical for all subagents)
    common_text = render_template(
        "prompts/common_role.md.j2",
        subagent_name=spec.name,
        model=spec.model,
        mailbox_inbox=spec.mailbox_inbox,
        edits_allow=list(spec.edits_allow),
        skills=list(spec.skills),
        registry=get_peer_subagent_registry(spec.name),  # ← Section 5.4
    )

    # Layer C: per-subagent domain clarifications
    per_subagent_text = render_template(
        f"prompts/per_subagent/{spec.name}.md.j2",
        spec=spec,
    )

    # Plugin preambles (mailbox rules, scope rules, hook descriptions)
    plugin_text = "\n\n".join(p.preamble() for p in plugin_chain if p.preamble())

    return assemble(
        LayerA=spec_text,
        LayerB=common_text,
        LayerC=per_subagent_text,
        Plugins=plugin_text,
    )
```

**Important distinction from M14**: M14's `spec_loader.build_subagent_prompt()` returned the spec body as the prompt. M16 loads the spec INTO the prompt — it's a section, not the whole thing. The agent reads the spec to understand expected behavior, but the role/duty/protocol framing comes from Layer B.

### 5.3 Specs are dynamic — the improve loop updates them

The improve cycle treats specs as **first-class artifacts**. After a successful run:

1. The improver captures the diff that produced the win.
2. It asks: "Does this diff reveal a behavior that should be codified in the spec?"
3. If yes, the spec is updated (the same `affects` mechanism fires cross-spec notifications).
4. Next run, the updated spec is loaded — the agent's behavior is now governed by the new contract.

**Concrete example**. After a successful run where `abm-worker` correctly chose to invoke `scoring-worker` for a regression test, the improver might update `docs/specs/abm/spec.md` to add:

```markdown
## 6. Data contracts (extended)

### 6.X Cross-agent handoff
abm MUST invoke scoring-worker via handoff_to_subagent when:
- The proposed change affects `scoring/` package.
- The composite score is below the previous best.

abm MUST NOT execute scoring tools directly — it does not own that scope.
```

Now the next run of `abm-worker` reads this and behaves correctly — without re-deriving the rule from conversation history.

### 5.4 Peer visibility — "do I have brothers?"

The common prompt (Layer B) makes every subagent aware of its sibling specialists:

```python
def get_peer_subagent_registry(self_name: str) -> list[PeerSubagentInfo]:
    """Return Metadata about other subagents that this one can invoke.

    Each peer entry contains:
    - name: str
    - description: str  (one-line: what they do)
    - when_to_call: str  (trigger condition)
    - mailbox: str
    - scope: list[str]  (edits_allow glob)
    """
    ...
```

Rendered in the common prompt as:

```markdown
## Your peers in the system

You are `abm-worker`. You can invoke these siblings when needed:

| Specialist | When to call | Scope |
|---|---|---|
| `scoring-worker` | Composite score regression suspected | `mal-core/.../scoring/**` |
| `data-worker` | Manifest/naming ambiguities | `mal-commonlib/.../data/**` |
| `commonlib-worker` | Shared config changes | `mal-commonlib/**` |
| `research-worker` | Literature or external info needed | (read-only) |

Use `handoff_to_subagent(name, brief)`. They share your worktree if you
spawn them as siblings. Each writes to their own scope; the watcher
notifies you if overlaps occur.
```

**This is the "call brothers when needed" rule** made structural — the agent doesn't have to remember which specialists exist; the system tells it.

### 5.5 Common prompt content (sketch)

```markdown
<!-- prompts/common_role.md.j2 -->
# You are {{ subagent_name }} in the MalariaSentinel system

## Your role
You are a specialist subagent in a multi-agent system. You were invoked
by {{ invoker_name }} with a specific brief. Complete your brief; report
back; respect the scope.

## Your capabilities
- Model: {{ model }}
- Mailbox: {{ mailbox_inbox }}
- Edited paths: {{ edits_allow }}
- Skills: {{ skills }}

## Your duties to the system
1. **Check mailbox first**: before any edit, run `mailbox_check_inbox`
   and `peer_message_check_inbox`. If a `block` message targets a file
   you're about to touch, STOP and respond.
2. **Stay in scope**: writes are restricted to `edits_allow`. Cross-scope
   writes fire a block message.
3. **Coordinate with siblings**: if your task touches another specialist's
   domain, call them via `handoff_to_subagent(name, brief)`. Do not
   duplicate their work.
4. **Speak to the user / orchestrator**: when done, emit a structured
   summary: what you did, what you changed, what you observed, what
   you recommend.
5. **Respond to forks**: if a fork is created from your context (peer
   negotiation), execute the fork brief, emit merge_result, and resume
   from frame stack.

## Your peers
{{ peer_registry_table }}

## Sibling protocol
- Claim files before editing: `claim_file(path, description)`.
- If a peer message warns of overlap, run SCAN_1..SCAN_7, then decide
  adapt / counter-propose / block.
- Frame stack caps at depth 5. Older frames auto-expire.

## Failure modes you must avoid
- Editing outside `edits_allow` → scope violation → block.
- Ignoring a `block` peer message → mandatory response.
- Spinning a sibling infinite times → check frame stack depth.
- Forgetting the original goal during a fork → read SCAN markers.

## Your domain behavioral spec
{{ spec_text }}
```

### 5.6 What changes vs M14

| Aspect | M14 | M16 |
|---|---|---|
| `spec.md` role | Becomes the prompt | Loaded INTO the prompt as a behavioral section |
| `prompts/templates/<name>.md` | Source of truth | Fallback only |
| `prompts/common_role.md.j2` | Does not exist | New — shared role + duties for all subagents |
| `prompts/per_subagent/<name>.md.j2` | Does not exist | New — domain clarifications |
| Peer registry | Not exposed | Part of common prompt — every subagent knows its siblings |
| Spec updates | Manual | Automatic via improve loop + affects graph |
| `affects` block | Loads but unused | Cross-spec notifications + improve-loop updates |

### 5.7 Acceptance criteria for this section

- [ ] `prompts/common_role.md.j2` exists and is identical content for all 9 subagents.
- [ ] `prompts/per_subagent/<name>.md.j2` exists for each registered subagent.
- [ ] `build_subagent_prompt(spec, plugin_chain)` returns a 4-layer composition (spec + common + per-sub + plugins).
- [ ] The peer registry table is rendered in every subagent's system prompt.
- [ ] After a successful improve run, the improver can update `docs/specs/<X>/spec.md` and the affects graph fires.
- [ ] `mocks for spec_loader` — when a spec is missing, the per-subagent fallback prompt is used (no crash).

### 15.1 Specs as dynamic contracts (Layer 3 acceptance criteria)

- [ ] `prompts/common_role.md.j2` exists and is identical content for all 9 subagents.
- [ ] `prompts/per_subagent/<name>.md.j2` exists for each registered subagent.
- [ ] `build_subagent_prompt(spec, plugin_chain)` returns a 4-layer composition (spec + common + per-sub + plugins).
- [ ] The peer registry table is rendered in every subagent's system prompt.
- [ ] After a successful improve run, the improver can update `docs/specs/<X>/spec.md` and the affects graph fires.
- [ ] When a spec is missing, the per-subagent fallback prompt is used (no crash).

## 6. Affects graph (Layer 4)

```python
# affects.py — already exists, never called
def compose_affected_notifications(changed_spec: str, registry: Registry) -> list[MailboxMessage]:
    """When docs/specs/X/spec.md changes, find all specs that declare
    affects: [X] and notify them via mailbox."""
    affected = get_affected_specs(changed_spec, registry.all_spec_paths())
    return [
        MailboxMessage(
            to=spec.name,
            from_="affects-watcher",
            re=f"spec {changed_spec} changed",
            severity="non-breaking",
            ask="ack",
        )
        for spec in affected
    ]
```

**What changes**: `affects.py` is wired into the `docs/specs/` file watcher. When a spec is edited, the orchestrator's mailbox receives cross-spec notifications automatically.

## 7. Sibling runtime — the new layer

### 7.1 Design constraints (from user)

- **Internals only**: no `--siblings` flag, no `--watcher-mode` flag. The orchestrator decides when to spawn siblings. The user sees a single goal and a single outcome.
- **Cooperative worktree**: siblings spawned for the same task share the parent subagent's worktree. They don't fork into separate worktrees; they all write to the same branch.
- **No parent arbitration**: when two siblings' edits overlap, **no orchestrator agent decides**. A watcher detects and notifies the affected sibling, who adapts.
- **Visibility**: the test harness (a janus subagent) reads Langfuse traces after the run to confirm behavior.

### 7.2 Components

```
sibling/
├── __init__.py
├── state.py             # SQLite WAL: claims, frame stacks, fork DAG
├── intent.py            # claim_file, release_claim, query_claims
├── ast_index.py         # tree-sitter Python AST index (v1)
├── merge_preflight.py   # git merge-tree --write-tree wrapper
├── watcher.py           # python watchdog + 500ms debounce + 60s polling fallback
├── coordination.py      # orchestrator: claim → preflight → notify → fork → merge
├── fork.py              # fork_brief, ReadOnlyChatContext, merge_result
├── scan.py              # SCAN markers generator (7 markers)
├── frame_stack.py       # Interrupt-Resumable Thought stack
├── peer_message.py      # mailbox extension for sibling↔sibling
└── recovery.py          # watcher hot-restart from WAL
```

### 7.3 Lazy intent generation (Option C from user)

The user pushed back on per-edit intent declarations ("demasiados tokens, mucho ruido"). Resolved design:

```
[Agente edita archivo]        ← NO declara intent
       ↓
[watcher detecta write]       ← python watchdog, 500ms debounce
       ↓
[query_claims(filepath)]      ← ¿quién más ha tocado este path?
       ↓
       ├── no overlap → silent (default, 0 tokens)
       ↓
       └── overlap detectado:
              ├── ast_index.parse(filepath)  ← tree-sitter, solo aquí
              ├── identify conflicting symbols (function/class)
              ├── llm.summarize(other_sibling.last_N_messages)  ← lazy, ~300 tokens
              ├── generate intent payload (path, symbol, sibling_b, summary)
              └── peer_message → inbox-<other_sibling>/
                      ↓
              triggers fork_brief en other_sibling
```

**Token cost**:
- happy path (no conflict): 0 tokens
- conflict path: 300 tokens (LLM summarize) + 200 tokens (intent payload)
- per sibling-wakeup: ~500 tokens total

**AST unit**: tree-sitter parses the file into functions/classes/methods. The granularity is "symbol", not "file" — two siblings editing different functions in the same file are NOT conflicting.

### 7.4 Peer message (sibling ↔ sibling)

`mailbox.py` is extended with a new message type:

```python
@dataclass(frozen=True)
class PeerMessage:
    id: str
    ts: str
    from_sibling: str        # subagent_id of sender
    to_sibling: str          # subagent_id of recipient
    worktree_id: str         # shared worktree marker
    re: str                  # short subject
    severity: Literal["info", "warn", "block"]
    trigger: Literal["file_overlap", "symbol_overlap", "merge_conflict", "completion"]
    context: dict            # {path, symbol, byte_range, summary}
    ask: Literal["adapt", "counter_propose", "block", "ack_only"]
    thread_id: str           # shared with primary subagent's task_id
    ttl_minutes: int = 30
    status: Literal["open", "resolved", "expired"] = "open"
```

Three tools (re-exported from `mailbox.py`):
- `peer_message_send(to_sibling, re, context, ask)` — non-blocking fire-and-forget
- `peer_message_check_inbox(subagent_id)` — synchronous read; returns paginated
- `peer_message_mark_resolved(message_id, resolution)` — moves to archive

### 7.5 Fork sub-context (forky-style)

When a sibling receives a peer message, it does NOT continue in its current session. It creates a fork:

```python
# sibling/fork.py
class ForkContext:
    """A sub-session branched from the parent at a specific message."""
    parent_sibling_id: str
    fork_id: str             # uuid, parent pointer (no copy)
    task_brief: str          # "Adapt to sibling-B's edit on validate_token()"
    instructions: str        # "You are sibling-A negotiating with sibling-B"
    created_at: str

def fork_brief(
    parent_context: SubagentContext,
    instructions: str,
    task_brief: str,
    agent_id: str,
) -> ForkContext:
    """O(1) fork via parent pointer. No message duplication.
    Prefix cache hit on shared prefix → 90% cheaper than fresh subagent."""
    return ForkContext(
        parent_sibling_id=parent_context.sibling_id,
        fork_id=str(uuid4()),
        task_brief=task_brief,
        instructions=instructions,
        created_at=now(),
    )

def merge_result(
    fork: ForkContext,
    result: str,
    *,
    use_summary: bool = False,
) -> str:
    """Returns a 200-500 token summary to inject into the parent context."""
    if use_summary:
        return llm.summarize(result, target_tokens=300)
    return result[:500]  # truncate if cheap merge
```

**ReadOnlyChatContext**: the forked subcontext can **read** the parent sibling's session history (via `parent_context.peek()`) but cannot mutate it. This prevents the negotiation from corrupting the parent's main task.

### 7.6 SCAN markers (output-restoring anchors)

Inside the forked subcontext, the system prompt carries 7 SCAN markers:

```python
# sibling/scan.py
SCAN_MARKERS = """
## CONTEXT SCAN PROTOCOL
This prompt contains markers @@SCAN_1..@@SCAN_7. Before any task,
output answers in CHAT (visible text, not thinking).

### Sibling B's intent
@@SCAN_1: What sibling-B is about to do.

### My original goal
@@SCAN_2: The original task I was given (parent).

### Diff received
@@SCAN_3: What sibling-B changed (file path + symbol + lines).

### Adaptation options
@@SCAN_4: A) Adapt, B) Counter-propose, C) Both adapt.

### Rules at risk
@@SCAN_5: API contract preservation, no new files, no test changes.

### Failure mode
@@SCAN_6: Most likely way to break the parent task.

### Negotiation vocabulary
@@SCAN_7: Terms to use when proposing the common point.

After work, mandatory:
CHECK: <what was verified>
MISSED: <what was not verified> (or "MISSED: none")

Skip CHECK if trivial. Use ANCHOR (!) at start of long tasks.
"""
```

**Token cost per fork**: ~300 tokens (FULL scan) + ~50 tokens (CHECK/MISSED). Negligible vs. the alternative (losing the parent task).

### 7.7 Frame stack (Interrupt-Resumable Thought)

```python
# sibling/frame_stack.py
@dataclass
class Frame:
    goal: str
    steps_completed: list[str]
    next_step: str
    pushed_at: str
    expires_at: str | None  # for cap on stack depth

class FrameStack:
    def __init__(self, sibling_id: str, max_depth: int = 5):
        self.sibling_id = sibling_id
        self.max_depth = max_depth
        self._stack: list[Frame] = []  # also persisted to SQLite

    def push(self, frame: Frame) -> None:
        if len(self._stack) >= self.max_depth:
            raise StackOverflowError("frame stack full")
        self._stack.append(frame)

    def pop(self) -> Frame:
        return self._stack.pop()

    def render_resume(self) -> str:
        """Returns 'back to X — I was at step N/M, doing Y'."""
        top = self._stack[-1]
        return (
            f"[resume] back to '{top.goal}' — "
            f"step {len(top.steps_completed)+1}/{len(top.steps_completed)+1} "
            f"({top.next_step})"
        )
```

**Protocol**: when a peer message arrives, the sibling MUST push its current frame, fork, negotiate, return, then pop the frame and emit `render_resume()` before resuming work.

### 7.8 Watcher (python watchdog + in-process)

```python
# sibling/watcher.py
class Watcher:
    def __init__(self, worktree_id: str, *, debounce_s: float = 0.5):
        self.worktree_id = worktree_id
        self.debounce_s = debounce_s
        self.observer = Observer()
        self._timers: dict[str, Timer] = {}

    def on_file_modified(self, path: str) -> None:
        if path in self._timers:
            self._timers[path].cancel()
        self._timers[path] = Timer(
            self.debounce_s,
            self._handle_change,
            args=[path],
        )
        self._timers[path].start()

    def _handle_change(self, path: str) -> None:
        coordination.on_file_modified(self.worktree_id, path)
        # checks claims, lazy AST parse, optional LLM summarize,
        # fires peer_message if conflict

    def start(self) -> None:
        self.observer.schedule(
            PatternMatchingEventHandler(
                patterns=["*.py", "*.cpp", "*.h", "*.hpp", "*.md", "*.yaml"],
                on_modified=self.on_file_modified,
            ),
            path=get_worktree_path(self.worktree_id),
            recursive=True,
        )
        self.observer.start()

    def stop(self) -> None:
        self.observer.stop()
        self.observer.join()
```

**Fallback**: 60s polling check (AgentMail pattern) when fsnotify fails (NFS, FUSE, descriptor exhaustion).

### 7.9 Refusal-as-protocol

Sibling can refuse peer messages with structured counter-proposal:

```python
peer_message_counter_propose(
    message_id: str,
    to_sibling: str,
    re: str,
    context: dict,
    proposal: str,  # "I propose we split: I take validate_token(), you take refresh_token()"
)
```

Both sides see all proposals in their inbox. After 3 rounds without agreement, the orchestrator's trace analyzer (test harness only) flags the test as failed.

## 8. Recovery (watcher + state)

```python
# sibling/recovery.py
def hot_restart(worktree_id: str) -> Watcher:
    """On janus startup, recover watcher state from SQLite WAL."""
    state = State.load_from_wal(worktree_id)
    if state is None:
        # No previous state — fresh watcher
        return Watcher(worktree_id)

    # Replay unprocessed claims
    for claim in state.unprocessed_claims:
        coordination.process_claim(claim)

    # Re-emit pending peer messages
    for msg in state.pending_peer_messages:
        mailbox.deliver(msg)

    # Re-attach frame stacks
    for sibling_id, stack in state.frame_stacks.items():
        FrameStack.attach(sibling_id, stack)

    return Watcher(worktree_id).start()
```

**RTO**: <1 second (state reload is O(claims × avg_edit_time)).

## 9. Test harness (the only user-facing surface)

The sibling layer is **internal**. To validate it, the user runs:

```bash
janus run -g "TRIAL: run a full e2e test of the sibling coordination system.
Use abm-worker as primary, spawn scoring-worker and ingest-worker as siblings.
Have them edit overlapping files in the shared worktree. Verify the watcher
fires, peer_message is sent, fork_brief is invoked, merge_result is returned.
End when scoring-worker has consumed ingest-worker's output."
```

A **trace-analyzer agent** (a janus subagent with trace-reading tools) then reads the Langfuse trace and produces a verdict:

```json
{
  "verdict": "pass | fail",
  "checks": [
    {"name": "primary spawned worktree", "passed": true, "evidence": "trace span 4"},
    {"name": "sibling join shared worktree", "passed": true, "evidence": "trace span 7"},
    {"name": "claim_file registered", "passed": true, "evidence": "claims table has 2 rows"},
    {"name": "watcher fired on file_overlap", "passed": true, "evidence": "span 12, debounce 500ms"},
    {"name": "peer_message sent", "passed": true, "evidence": "mailbox/inbox-scoring/msg-001"},
    {"name": "fork_brief invoked", "passed": true, "evidence": "span 14, fork_id=abc"},
    {"name": "merge_result returned", "passed": true, "evidence": "span 16, 487 tokens"},
    {"name": "frame_stack push/pop", "passed": true, "evidence": "sqlite/wal frame_stack rows"},
    {"name": "no parent arbitration", "passed": true, "evidence": "no orchestrator.tool_call between siblings"},
    {"name": "SCAN markers emitted", "passed": true, "evidence": "span 15 output contains SCAN_1..SCAN_7"}
  ],
  "failures": [],
  "score": 1.0
}
```

**The test prompt + analyzer is the only way to validate M16**. No unit test alone covers the full pipeline (watcher → fork → merge → resume); it requires an actual LLM-driven trace.

## 10. CLI surface (no new flags)

```bash
janus run -g "TRIAL: ..."         # user runs the trial
janus run -g "ship M12"           # normal use, no sibling internals exposed
janus improve -g "..."            # normal use
janus status                      # inspect past runs
janus status --worktree ./runs/... # inspect a sibling worktree
```

**No new flags**. The orchestrator's prompt template includes a single instruction: "If goal involves multiple subagents that touch the same code, spawn them as siblings and use the shared-worktree runtime. Otherwise, use the standard task() dispatch."

## 11. Promoting trials to test suite

When a trial verdict is `pass`, the trace is stored as `tests/fixtures/trial-<sha>.json`. After 3 consecutive passes with the same shape, the trial is promoted to a pytest that:

1. Mocks the LLM (deterministic responses).
2. Runs the same scenario.
3. Asserts the same 10 checks in the JSON above.

This is how the sibling layer becomes testable without re-running Langfuse.

## 12. File layout (additions + modifications)

```
agents/janus/src/agents_janus/
├── agent.py                    [MODIFY] create_orchestrator(tier) uses registry + builder
├── improvement.py              [MODIFY] sibling lifecycle hooks
├── onboarding.py               [MODIFY] awareness of sibling layer (read-only view)
├── cli.py                      [MODIFY] no new flags; trial prompt on demand
├── subagents/                  [M14, now all wired]
├── plugins/                    [M14, now all wired]
├── config/subagents.yaml       [M14, unchanged]
├── config/onboarding_menu.yaml [NEW] YAML-driven menu (was M14 gap)
├── mailbox.py                  [MODIFY] add PeerMessage + 3 peer tools
├── scope_validator.py          [M14, now wired into middleware]
├── spec_loader.py              [M14, now wired into builder]
├── affects.py                  [M14, now wired into mailbox]
├── sibling/                    [NEW]
│   ├── __init__.py
│   ├── state.py
│   ├── intent.py
│   ├── ast_index.py
│   ├── merge_preflight.py
│   ├── watcher.py
│   ├── coordination.py
│   ├── fork.py
│   ├── scan.py
│   ├── frame_stack.py
│   ├── peer_message.py
│   └── recovery.py
├── tools/                      [MODIFY]
│   ├── subagent_invoke.py      [REPLACE] handoff_to_subagent
│   ├── claim_file.py           [NEW]
│   ├── release_claim.py        [NEW]
│   ├── query_claims.py         [NEW]
│   ├── peer_message_send.py    [NEW]
│   ├── peer_message_check.py   [NEW]
│   ├── peer_message_resolve.py [NEW]
│   ├── fork_brief.py           [NEW]
│   └── merge_result.py         [NEW]
├── prompts/                   [REWRITE — 3-layer composition]
│   ├── common_role.md.j2              [NEW] Shared role + duties for all subagents
│   ├── per_subagent/                  [NEW] One file per registered subagent
│   │   ├── abm.md.j2
│   │   ├── scoring.md.j2
│   │   ├── ingest.md.j2
│   │   ├── download.md.j2
│   │   ├── prediction.md.j2
│   │   ├── training.md.j2
│   │   ├── data.md.j2
│   │   ├── commonlib.md.j2
│   │   └── research.md.j2
│   ├── sibling_protocol.md.j2         [NEW] Sibling coordination rules
│   └── drift/                         [NEW] Fork / SCAN / resume templates
│       ├── fork_negotiation.md.j2
│       ├── scan_markers.md.j2
│       └── resume_protocol.md.j2
├── cycles/                     [MODIFY]
│   ├── improvement_cycle.py    [MODIFY] spawn siblings when needed
│   ├── score_then_compare.py   [M14, unchanged]
│   └── sibling_cycle.py        [NEW]
├── tests/                      [EXTEND]
│   ├── test_sibling_coordination.py [NEW]
│   ├── test_fork_merge.py      [NEW]
│   ├── test_watcher.py         [NEW]
│   ├── test_scan_protocol.py   [NEW]
│   ├── test_intent_daemon.py   [NEW]
│   ├── test_claim_lazy.py      [NEW]
│   └── test_peer_message.py    [NEW]
└── trace_analyzer/             [NEW]
    ├── __init__.py
    ├── analyzer.py             # reads Langfuse trace, produces verdict JSON
    └── checks.py               # 10 named checks (table-driven)
```

## 13. Implementation order (12 steps)

1. `sibling/state.py` — SQLite WAL schema (`claims`, `frame_stacks`, `fork_dag`, `peer_messages`).
2. `sibling/ast_index.py` — tree-sitter Python AST index (functions/classes/methods).
3. `sibling/intent.py` — `claim_file`, `release_claim`, `query_claims` (file-level only, lazy).
4. `sibling/merge_preflight.py` — `git merge-tree --write-tree` wrapper (JSON output).
5. `sibling/peer_message.py` — `PeerMessage` dataclass + 3 tools (re-export through `mailbox.py`).
6. `sibling/watcher.py` — python watchdog + 500ms debounce + 60s polling fallback.
7. `sibling/coordination.py` — orchestrates: claim → preflight → notify → fork → merge.
8. `sibling/fork.py` — `fork_brief`, `ReadOnlyChatContext`, `merge_result`, `merge_with_summary`.
9. `sibling/scan.py` — SCAN markers generator (7 markers, FULL/MINI/ANCHOR levels).
10. `sibling/frame_stack.py` — Interrupt-Resumable Thought stack.
11. `sibling/recovery.py` — hot-restart from WAL.
12. `agent.py` refactor — `create_orchestrator(tier)` uses registry + builder + siblingMiddleware.
13. `tools/` — 8 new tools (subagent_invoke, claim_file, release_claim, query_claims, peer_message_*, fork_brief, merge_result).
14. `prompts/common_role.md.j2` — shared role + duties for all 9 subagents (peer registry table, mailbox rules, sibling protocol).
15. `prompts/per_subagent/<name>.md.j2` — domain clarifications for each subagent.
16. `prompts/sibling_protocol.md.j2` — sibling coordination rules shared with the common prompt.
17. `prompts/drift/*.md.j2` — fork/SCAN/resume templates.
18. `cycles/sibling_cycle.py` — spawn siblings + monitor + recovery.
19. `trace_analyzer/` — runs after a trial, reads Langfuse, produces verdict JSON.
20. `config/onboarding_menu.yaml` — YAML-driven menu (M14 gap).
21. Improve-loop spec updater — codifies new behaviors into `docs/specs/<X>/spec.md` after successful runs.
22. Tests + AGENTS.md updates + KG node.

## 14. Backwards compatibility

- `WORKER_DEFINITIONS` alias: `task(subagent_type="abm-worker")` resolves to registry entry "abm". Existing code keeps working.
- `prompts/templates/abm_worker.md`: fallback when `spec_loader` cannot reach the spec. Real prompts come from `spec.md` + plugin `preamble()`.
- `mailbox.py` inbox: existing `mailbox_send` / `check_inbox` / `mark_resolved` API unchanged. New `peer_message_*` is additive.
- `ScopeValidator` middleware: existing `validate_proposal_scope()` function unchanged. New middleware wraps it as a `wrap_tool_call` hook.
- No `mal-core/` code changes. No new `docs/specs/<x>/spec.md`. No reintroduction of `docs/specs/pipeline/spec.md`.

## 15. Acceptance criteria

- [ ] `create_orchestrator(tier='improve')` loads `subagents.yaml` and uses `build_resolved(spec, plugin_chain)`.
- [ ] All 9 subagents in `subagents.yaml` are invocable via `task(subagent_name=...)` (no hardcoded `WORKER_DEFINITIONS`).
- [ ] `task(subagent_name="download")` returns a subagent with `mal-core/src/mal_core/download/**` permissions + `DownloadPlugin` tools.
- [ ] `spec_loader.build_subagent_prompt()` is called in `build_subagent()` — no longer dead code.
- [ ] `affects.compose_affected_notifications()` fires on spec change — no longer dead code.
- [ ] `agent.py` has zero `WORKER_DEFINITIONS` literals (the constant is a lazy alias).
- [ ] `claim_file` lazily registers intent at file-level (~20 tokens, no AST).
- [ ] Watcher invokes `ast_index.parse()` only when `query_claims(filepath)` returns ≥2 claims.
- [ ] `peer_message_send` triggers `fork_brief` in the recipient sibling.
- [ ] Fork `merge_result` returns ≤500 tokens.
- [ ] Frame stack push/pop logged in SQLite WAL.
- [ ] Trial prompt produces a verdict JSON with all 10 checks passing.
- [ ] Trace analyzer reads Langfuse trace and produces the verdict JSON.
- [ ] `agents/janus/src/agents_janus/tests/test_sibling_coordination.py` — 10 unit tests pass.
- [ ] `agents/janus/src/agents_janus/tests/test_fork_merge.py` — 5 unit tests pass.
- [ ] `agents/janus/src/agents_janus/tests/test_watcher.py` — 5 unit tests pass.
- [ ] `agents/janus/src/agents_janus/tests/test_scan_protocol.py` — 3 unit tests pass.
- [ ] `agents/janus/src/agents_janus/tests/test_intent_daemon.py` — 5 unit tests pass.
- [ ] `agents/janus/src/agents_janus/tests/test_claim_lazy.py` — 5 unit tests pass.
- [ ] `agents/janus/src/agents_janus/tests/test_peer_message.py` — 5 unit tests pass.
- [ ] `make -f agents/memory/scripts/Makefile audit` is clean (no schema violations).
- [ ] KG node `op-m16-registry-integration` recorded with summary + commit SHA.
- [ ] No file under `mal-core/` is modified by this milestone.
- [ ] No new CLI flags in `janus run` / `janus improve` (sibling internals invisible).
- [ ] `create_orchestrator(tier='onboarding')` rejects direct `handoff_to_subagent(name≠'improver')` with explicit error.
- [ ] `compute_plugins_for_invocation(caller_chain)` derives subagent plugin chain from caller's chain, not top-level tier.
- [ ] Sibling invocations (shared worktree) inject `SiblingPlugin` automatically.
- [ ] Plugin added to improver's chain propagates to all downstream subagents (direct + sibling).
- [ ] When onboarding handoff to improver, downstream subagents descend from improver's `[Edit, ...]` chain, not onboarding's `[ReadOnly]`.

## 16. Risks

| # | Risk | Mitigation |
|---|---|---|
| 1 | Two orchestrators drift in capability over time | Both are built from the same `registry.get()` + plugin chain; capability = (registry) + (plugins). Adding a plugin to one does not auto-add it to the other — explicit. |
| 2 | Plugin chain order matters (e.g. `EditPlugin` must run first) | Document order in `plugins/base.py`; `apply()` is `__init__.py`-driven. Add unit test that checks each plugin's invariants. |
| 3 | Onboarding's `handoff_to_subagent` makes the orchestrator a single point of failure | Handoff is synchronous; failure surfaces back to onboarding verbatim; onboarding then offers "retry" or "back to menu". |
| 4 | `docs/plans/in-process/*.md` start being treated as auto-triggers by future contributors | AGENTS.md note + onboarding menu's "Run a plan" entry is the only path that mentions them. |
| 5 | Scope validator gets out of sync with YAML | Validator reads the same `subagents.yaml`; one source of truth. |
| 6 | The 9 subagents × per-subagent plugins → combinatorial test surface | Test each plugin in isolation + one integration test per subagent (abm gets the full score-after chain). |
| 7 | User expectation that the improvement orchestrator auto-picks the next plan from `in-process/` | Explicit `--plan` flag and onboarding menu only; AGENTS.md note. |
| 8 | Sibling layer adds latency due to LLM summary on conflict | Lazy generation only fires on overlap; happy path is 0 tokens. Budget = 500 tokens per conflict. |
| 9 | Frame stack grows unbounded during long sessions | `max_depth=5` cap; expired frames auto-popped. |
| 10 | Watcher dies → siblings blind-write | SQLite WAL + checkpoint recovery on startup. RTO <1s. |
| 11 | Tree-sitter version mismatch | Pin `tree-sitter==0.21.0` and `tree-sitter-python==0.21.0` in `pyproject.toml`. |
| 12 | Fork cache miss prefixes | Prefix cache hit on shared parent messages (forky design). Verify with Langfuse token/cost analysis. |
| 13 | Trial verdict relies on LLM trace noise | 10 named checks are table-driven; trace analyzer asserts on presence of named spans, not LLM output content. |
| 14 | Trace analyzer runs every trial — slow (Langfuse) | Trial mode is opt-in (`-g "TRIAL: ..."`). Production runs skip the analyzer. |
| 15 | Plugin chain propagation across deep handoffs gets tangled | `compute_plugins_for_invocation()` is a pure function from `(caller_chain, spec, sibling?)` → chain. Single source of truth. Unit-test all 4 boundary cases. |
| 16 | Onboarding accidentally grants write capability to a subagent | `handoff_to_subagent` enforces tier-bypass at the top level: onboarding can only call `improver`, never direct subagents. |
| 17 | Sibling loses write capability when not in parent's chain | SiblingPlugin is added OR'd with the caller's `EditPlugin` presence; never demotes a channel write-only to read-only. |
| 18 | Specs drift from actual behavior over many runs | Improve loop post-commit checks: "did this diff reveal a behavior that should be codified in spec.py?" If yes, update spec. Codification is iterative. |
| 19 | Common prompt bloat — every subagent reads the same heavy common prompt | Common prompt is bounded (target ≤800 tokens). Per-subagent clarifications cap at 400 tokens. Plugins add ≤300 tokens each. Total ≤2K tokens of overhead. |
| 20 | Subagent doesn't know it should call a sibling | Peer registry table is in the common prompt — every subagent knows its siblings. Verification: every subagent's prompt contains the table. |
| 21 | Spec changes break sibling assumptions | `affects` graph fires cross-spec notifications BEFORE the change takes effect. Subagents ack the change before proceeding. |

## 17. References

- `docs/plans/completed/m14-orchestrator-plugin-system.md` — M14 plan (predecessor, finishing).
- `agents/janus/src/agents_janus/SKILL.md` — current quick-start (to be updated).
- `agents/janus/src/agents_janus/AGENTS.md` — current conventions (M14 architecture section to be updated).
- `agents/janus/src/agents_janus/live_panel.py` — M15 live panel.
- `agents/janus/src/agents_janus/observability.py` — M15 observability middleware.
- `agents/janus/src/agents_janus/subagents/base.py::SubagentSpec` — dataclass to be wired.
- `agents/janus/src/agents_janus/subagents/builder.py::build_resolved` — function to be called.
- `agents/janus/src/agents_janus/config/subagents.yaml` — source of truth.
- `docs/specs/_template.md` — spec format consumed by `spec_loader.py`.
- `langfuse-python` SDK — `start_as_current_observation` for trace spans.
- `tree-sitter` + `tree-sitter-python` — AST library.
- `watchdog` — Python fsnotify wrapper.
- `git merge-tree --write-tree` — preflight conflict detection.
- KB `Operational` node: `op-m14-orchestrator-plugin-system` (predecessor).
- KB `Pattern` node: `pattern-sibling-coordination` (after recording).
- KB `Pattern` node: `pattern-fork-merge` (after recording).
- KB `Pattern` node: `pattern-scan-protocol` (after recording).
- KB `Pattern` node: `pattern-frame-stack` (after recording).

## 18. Change log

| Date | Author | Change |
|---|---|---|
| 2026-08-05 | supervisor | Plan drafted. Closes M14 integration gap. Adds sibling coordination layer (internals-only, no CLI flags). Designs trace-analyzer test harness as the only user-facing validation surface. Decides lazy intent generation (Option C: 20-token claim + AST only on overlap). Includes fork + SCAN + frame stack for context drift. |
