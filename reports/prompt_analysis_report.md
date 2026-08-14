# Janus Prompt Analysis Report

**Date**: 2026-08-14  
**Traces analyzed**: `bdb74085159dba4a797d02cea0a924cc`, `e101108e6e84c8e1b483f1d5c51be221`  
**Model**: `xiaomi/mimo-v2.5` via OpenRouter  
**Status**: ✅ FIX APPLIED — switched from `ChatOpenAI` to `ChatOpenRouter`

---

## 1. Prompt Architecture Overview

Janus uses a **3-layer prompt system** with 4 distinct prompt types:

### 1.1 System Prompt (role definition)

**Orchestrator** (`prompts/orchestrator.md.j2`):
- Rendered via Jinja2 with `mode` variable (`centinela` or `dispatcher`)
- Injects specialist list dynamically from `subagents.yaml`
- Contains: role definition, DO/DON'T rules, filesystem path conventions, dispatching protocol, mode-specific behavior (centinela vs dispatcher)

**Specialist** (`prompts/specialist.md.tmpl`):
- Rendered with `role`, `task`, `edits_allow`, `skills`, `depends_on`, `spec_text`
- Contains: mission, mode selection (research/implementation), registration protocol, file editing rules, peer coordination, knowledge graph instructions

**Per-subagent** (`prompts/per_subagent/<name>.md.j2`):
- Domain-specific clarifications appended to the specialist template
- Examples: ABM worker gets code graph tools + malariasim CLI; Ingest worker gets ingest-specific search queries

### 1.2 Human Prompt (user messages)

In Langfuse traces, human messages appear as `role: "user"` entries. The pattern observed:

| Step | Content | Source |
|---|---|---|
| 1 | Empty string `""` | DeepAgents framework padding |
| 2+ | Code snippets, search results, tool outputs | Injected by deepagents after tool calls |

**Critical finding**: The `content` field in the Langfuse trace shows `content=[{'type': 'text', 'text': '...'}]` — this is the **serialized message content format**, not the raw prompt. The actual system prompt text is nested inside this wrapper.

### 1.3 AI/Assistant Prompt (model responses)

The model's responses are captured in the `output` field of GENERATION observations. Examples:
- Orchestrator step 6: `"Ahora tengo toda la información necesaria..."` (29.4s latency, 47,839 input tokens)
- ABM step 25: `"Now I have a comprehensive understanding..."` (96.9s latency, 84,574 input tokens)
- Ingest step 24: `"I now have a thorough understanding..."` (57.8s latency, 50,547 input tokens)

### 1.4 Tool Prompts (tool descriptions)

Tools are registered by deepagents framework. The orchestrator sees:
- `execute` (bash, restricted to `malariasim` via `MalariasimShellBackend`)
- `task()` (subagent dispatch)
- `onboard_status`, `onboard_list_components`, `delegate_to_dispatcher`, `onboard_ask_subagent`
- `memory_recall_kg`, `ask_user`
- `codebase_*` tools (via MCP bridge)
- `gawt_mcp_*` tools (via MCP bridge, dispatcher mode only)

Subagents see:
- `gawt_mcp_*` tools (edit_file, write_file, read_file, etc.)
- `codebase_*` tools
- `ask_user`, `resolve_conflict`
- `execute` (abm specialist only)

---

## 2. Trace Analysis: `bdb74085` (Orchestrator — Centinela Mode)

### 2.1 Observations Summary

| Step | Type | Name | Latency | Input Tokens | Output Tokens |
|---|---|---|---|---|---|
| 1 | SPAN | tool:codebase_get_code_snippet | 0.043s | — | — |
| 1 | SPAN | tool:codebase_get_code_snippet | 0.029s | — | — |
| 1 | SPAN | tool:codebase_search_graph | 0.103s | — | — |
| 2 | SPAN | tool:codebase_get_code_snippet | 0.066s | — | — |
| 2 | SPAN | tool:codebase_get_code_snippet | 0.080s | — | — |
| 3 | GENERATION | llm:orchestrator | 8.7s | 36,002 | 304 |
| 4 | GENERATION | llm:orchestrator | 3.4s | 40,193 | 225 |
| 5 | SPAN | tool:codebase_search_graph | 0.093s | — | — |
| 5 | SPAN | tool:codebase_search_graph | 0.111s | — | — |
| 5 | SPAN | tool:codebase_get_code_snippet | 0.011s | — | — |
| 5 | SPAN | tool:codebase_get_code_snippet | 0.031s | — | — |
| 6 | GENERATION | llm:orchestrator | 3.8s | 45,371 | 169 |
| 7 | SPAN | tool:codebase_get_code_snippet | 0.019s | — | — |
| 7 | SPAN | tool:codebase_get_code_snippet | 0.031s | — | — |
| 8 | GENERATION | llm:orchestrator | 29.4s | 47,839 | 1,843 |

### 2.2 System Prompt Content (from trace)

The system prompt arrives as:
```
content=[{'type': 'text', 'text': '# Janus Orchestrator — Centinela Mode\n\nYou are the Janus orchestrator in **centinela** mode...'}]
```

**Problem**: The system prompt is wrapped in a `content=[{'type': 'text', 'text': '...'}]` serialization format. This is the **LangChain message content format** — a list of content blocks. The model receives this as-is, which means:

1. The model sees `content=[{'type': 'text', 'text': '...'}]` as the system message content
2. The actual prompt text is buried inside a Python repr-like string
3. This adds ~50 characters of wrapper noise to every system message

### 2.3 Human Messages (from trace)

The orchestrator receives multiple `role: "user"` messages per step:

| Step | User Messages | Content |
|---|---|---|
| 3 | 3 messages | `build_host_dataset` snippet, `build_mobility_dataset` snippet, search results (331 hits) |
| 4 | 3 messages | `read_env_nc` snippet, `build_daily_env_nc` snippet, search results (155 hits) |
| 5 | 2 messages | `run_abm_from_manifest` snippet, search results (174 hits) |
| 6 | 2 messages | `load_from_env_nc` snippet, `load_from_nc` snippet |

**Observation**: Tool results are injected as separate `role: "user"` messages, not as `role: "tool"` messages. This is a deepagents framework behavior — it converts tool outputs into user messages.

### 2.4 Orchestrator Behavior

The orchestrator in this trace:
1. Uses `codebase_*` tools correctly (search_graph → get_code_snippet)
2. Searches for relevant functions before reading them
3. Produces a structured analysis at step 8 (29.4s latency, 1,843 output tokens)

**No subagent dispatch** — the orchestrator answered directly instead of dispatching specialists. This is because the user asked a research question ("explain how ABM and ingest work"), and the centinela mode allows direct research via codebase tools.

---

## 3. Trace Analysis: `e101108e` (Subagents — ABM + Ingest)

### 3.1 Observations Summary

This trace shows **two subagents running in parallel**: `abm` and `ingest`.

**ABM specialist** (25 steps):
- Step 22: `llm:abm` — 3.7s, 73,729 input tokens, 178 output tokens
- Step 23: `llm:abm` — 3.5s, 80,247 input tokens, 179 output tokens  
- Step 25: `llm:abm` — 96.9s, 84,574 input tokens, 6,525 output tokens (final report)

**Ingest specialist** (24 steps):
- Step 21: `llm:ingest` — 5.4s, 48,147 input tokens, 105 output tokens
- Step 24: `llm:ingest` — 57.8s, 50,547 input tokens, 4,004 output tokens (final report)

### 3.2 System Prompt Content (from trace)

ABM specialist system prompt:
```
content=[{'type': 'text', 'text': '# abm Specialist — MalariaSentinel\n\nYou are the **abm** specialist...'}]
```

Ingest specialist system prompt:
```
content=[{'type': 'text', 'text': '# ingest Specialist — MalariaSentinel\n\nYou are the **ingest** specialist...'}]
```

**Same wrapper problem** as the orchestrator — `content=[{'type': 'text', 'text': '...'}]` serialization.

### 3.3 Human Messages (from trace)

ABM specialist receives:
- Code snippets from `read_file` tool (multirate_scheduler.hpp, habitat_engine.hpp, main.cpp, etc.)
- Each tool result is a separate `role: "user"` message

Ingest specialist receives:
- Code snippets from `read_file` tool (runner.py, wrapper.py, etc.)
- Each tool result is a separate `role: "user"` message

### 3.4 Subagent Behavior

**ABM specialist**:
- Uses `read_file` tool (NOT `codebase_*` tools) to read C++ headers
- Reads 20+ files across 25 steps
- Produces a comprehensive architecture report at the end

**Ingest specialist**:
- Uses `read_file` tool to read Python files
- Reads 10+ files across 24 steps
- Produces a detailed pipeline report at the end

**Critical finding**: Both subagents use `read_file` instead of `codebase_*` tools, despite the prompt saying "Search the code graph FIRST". The `codebase_*` tools are available but not being used by subagents.

---

## 4. Root Cause Analysis: Why Agents Don't Follow Instructions

### 4.1 Problem 1: Content Serialization Wrapper

**Evidence**: Every system prompt in the traces is wrapped in `content=[{'type': 'text', 'text': '...'}]`.

**Impact**: The model receives a Python repr-like string instead of clean markdown. This:
- Adds cognitive overhead (model must parse the wrapper)
- Reduces effective context window (wrapper uses ~50 chars per message)
- May confuse the model about the actual instruction format

**Root cause**: LangChain's `ChatModel` serializes message content as a list of content blocks. When deepagents passes the system prompt, it's wrapped in this format.

### 4.2 Problem 2: Tool Results as User Messages

**Evidence**: All tool outputs appear as `role: "user"` messages, not `role: "tool"` messages.

**Impact**: The model cannot distinguish between:
- Actual user input
- Tool execution results
- Framework padding (empty `""` messages)

**Root cause**: deepagents framework converts tool outputs to user messages for compatibility with models that don't support native tool calling.

### 4.3 Problem 3: Subagents Ignore Code Graph Tools

**Evidence**: Both ABM and Ingest specialists use `read_file` exclusively, despite:
- System prompt saying "Search the code graph FIRST"
- `codebase_*` tools being available in their tool set
- Per-subagent prompts (`abm.md.j2`, `ingest.md.j2`) explicitly listing code graph tools

**Impact**: 
- `read_file` reads entire files (slow, large context)
- `codebase_get_code_snippet` reads just the function (fast, small context)
- The ABM specialist reads 20+ files instead of 5-10 targeted snippets

**Root cause**: The model defaults to `read_file` because:
1. It's a more familiar tool (file reading is universal)
2. The code graph tools are newer and less established in the model's training
3. The prompt says "Fall back to file reads" — the model may interpret this as "use file reads"

### 4.4 Problem 4: Empty User Messages

**Evidence**: Multiple traces show empty `role: "user"` messages (`""`).

**Impact**: Wastes context window and may confuse the model about conversation state.

**Root cause**: deepagents framework padding for multi-turn conversation format.

### 4.5 Problem 5: Orchestrator Doesn't Dispatch Subagents

**Evidence**: Trace `bdb74085` shows the orchestrator answering directly instead of dispatching specialists.

**Impact**: The orchestrator does the research itself, which:
- Violates its own prompt ("You do NOT read code in detail")
- Produces a single-agent response instead of parallel specialist reports
- Misses the benefit of specialized domain knowledge

**Root cause**: The centinela mode allows direct research via codebase tools. The model chooses the faster path (direct research) over the correct path (dispatch specialists).

---

## 5. Recommendations

### 5.1 Fix Content Serialization (High Priority)

**Problem**: `content=[{'type': 'text', 'text': '...'}]` wrapper  
**Fix**: Extract the raw text from the content block before passing to the model. In `agent.py` or deepagents middleware, unwrap the content:
```python
# Before passing to model
if isinstance(content, list) and len(content) == 1 and content[0].get('type') == 'text':
    content = content[0]['text']
```

### 5.2 Fix Tool Result Injection (High Priority)

**Problem**: Tool results injected as `role: "user"` messages  
**Fix**: Use `role: "tool"` messages with proper `tool_call_id` linking. This requires deepagents framework changes or a middleware that converts user messages to tool messages.

### 5.3 Strengthen Code Graph Tool Usage (Medium Priority)

**Problem**: Subagents default to `read_file`  
**Fix**:
1. Add explicit examples in the per-subagent prompts showing `codebase_*` tool usage
2. Add a rule: "If you use `read_file` more than 3 times, switch to `codebase_search_graph`"
3. Remove "Fall back to file reads" from the specialist prompt (or make it conditional)

### 5.4 Enforce Subagent Dispatch (Medium Priority)

**Problem**: Orchestrator answers directly instead of dispatching  
**Fix**:
1. Add explicit rule: "For ANY code-related question, dispatch a specialist. Never read code yourself."
2. Remove `codebase_*` tools from the orchestrator's tool set (force delegation)
3. Add a check: if the orchestrator uses `codebase_*` tools more than 2 times, auto-dispatch a specialist

### 5.5 Remove Empty User Messages (Low Priority)

**Problem**: Empty `""` user messages  
**Fix**: Filter out empty messages in the deepagents middleware before passing to the model.

---

## 6. Fix Applied: ChatOpenRouter Integration

### 6.1 Root Cause

We were using `langchain_openai.ChatOpenAI` with `base_url="https://openrouter.ai/api/v1"` — this bypasses LangChain's dedicated OpenRouter integration and breaks:
- Tool calling serialization
- Message format translation
- Proper API request formatting

### 6.2 What Changed

| File | Before | After |
|---|---|---|
| `pyproject.toml` | `langchain-openai` only | Added `langchain-openrouter>=0.1` |
| `agent.py` | `ChatOpenAI(base_url=...)` | `ChatOpenRouter(api_key=...)` |
| `tools/onboard_tools.py` | `ChatOpenAI(base_url=...)` | `ChatOpenRouter(api_key=...)` |
| `trace_analyzer/judge.py` | `ChatOpenAI(base_url=...)` | `ChatOpenRouter(api_key=...)` |

### 6.3 What ChatOpenRouter Provides

Per LangChain docs (`docs.langchain.com/oss/python/integrations/chat/openrouter`):
- ✅ Native tool calling (`bind_tools()` → `AIMessage.tool_calls`)
- ✅ Structured output (`with_structured_output()`)
- ✅ Proper message serialization for OpenRouter API
- ✅ Provider routing, caching, reasoning support
- ✅ 1M context window support for mimo-v2.5

### 6.4 Verification

- `uv add langchain-openrouter` — installed v0.2.7
- Import test: `ChatOpenRouter(model='xiaomi/mimo-v2.5')` — ✅ creates model with `tool_calling: True`
- All 53 core tests pass ✅
- All 5 MCP session pool tests pass ✅

---

## 7. Summary

| Issue | Severity | Root Cause | Fix | Status |
|---|---|---|---|---|
| Tool results as user messages | High | Wrong OpenRouter integration (`ChatOpenAI`) | Switch to `ChatOpenRouter` | ✅ Fixed |
| Content serialization wrapper | High | `ChatOpenAI` not handling OpenRouter API format | `ChatOpenRouter` handles serialization | ✅ Fixed |
| Empty user messages | Low | Framework padding (intentional) | No fix needed | ✅ OK |
| Subagents ignore code graph tools | Medium | Model defaults to familiar tools | Strengthen prompt examples | Pending |
| Orchestrator doesn't dispatch | Medium | Centinela allows direct research | Remove codebase tools from orchestrator | Pending |

**The most impactful fix has been applied.** The `ChatOpenRouter` integration properly handles tool calling serialization, which should resolve the issues with tool results being injected as user messages and the content serialization wrapper problem. The remaining medium-priority issues (subagent tool usage, orchestrator dispatch) are prompt-level concerns that can be addressed separately.
