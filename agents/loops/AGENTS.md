# Rules for specialised loop agents

This file is loaded by OpenCode automatically (via `opencode.json` →
`instructions`). It applies to every subagent in `agents/loops/`. Read it
before invoking or defining one.

## What a loop agent is

A loop agent is a subagent that runs a short, verifiable cycle:

1. Read a brief from the supervisor.
2. Run a check command or a read-only investigation.
3. Inspect the result, take the minimal next action.
4. Repeat until an **exit condition** holds.
5. Return a structured artifact to the supervisor.

A loop is **not** a free-form chat. It is a procedure with an external
truth source — the check command — and a hard exit condition that the
agent cannot bend.

## Exit conditions are not negotiable

If the check command exits 0, the loop is done. If it does not, the loop
is not done. There is no "I think this is good enough" path. Loops that
lie about their exit condition pollute the supervisor's world model and
are worse than a failed loop.

The only legitimate non-success termination is a `blocker` return with:

- The blocker (what is preventing convergence).
- Evidence (the last 3 failure messages, or the last state inspected).
- The safest next action the supervisor could take.

## Briefs are the only context you receive

The supervisor passes you a brief (goal, check command, target paths,
optional context). You do **not** receive the full conversation. If you
need more context:

1. Query the knowledge base first: the `memory_query` custom tool
   (Cypher), `mcp__graphiti-memory__search_nodes` (semantic recall), or
   `bash agents/memory/scripts/memory.sh query "<cypher>"` for a
   human-style invocation.
2. If the KB is empty, ask the supervisor via the `question` tool. Do not
   invent context.
3. As a last resort, use `websearch` / `webfetch` (if your permissions
   allow it). For everything research-shaped, the `doc-researcher` loop
   is the right tool, not you.

## When to use the custom tools vs the MCP tools

- `memory_node` / `memory_rel` / `memory_query` / `memory_audit` custom
  tools — for typed nodes, relations, and audited reads. This is the
  canonical write path. The tools validate the label against the schema
  before any Cypher runs. They delegate to
  `bash agents/memory/scripts/memory.sh` so the same rules apply for
  humans (`make -f agents/memory/scripts/Makefile`).
- `mcp__graphiti-memory__add_memory` with `source: "text"` — for free-form
  episode text only (session summaries, observations). Never use it for
  typed nodes with `source: "json"`; the Graphiti MCP 1.26.0 extractor
  ignores the `type` field and re-classifies from text, producing
  mis-labelled graphs.
- `mcp__graphiti-memory__search_nodes` — for free-form semantic search
  over the knowledge base.

## Returning results

Every loop returns a structured object (JSON-style in the response) with
at minimum:

- `status`: `ok` | `partial` | `blocked`
- `summary`: a short description of what happened
- `evidence_refs`: file paths, UUIDs, or command outputs the supervisor
  can verify independently

The supervisor uses `evidence_refs` to decide whether to trust the
result, to record it in the knowledge base, or to escalate. The brief
is lost when the loop ends; the artifact is what persists.

## Guardrails every loop inherits

- Do not weaken, skip, or comment out tests/checks to force success.
- Do not claim success unless the check command actually passes.
- Do not write to the knowledge base directly unless the supervisor
  explicitly delegated that.
- If you find yourself needing a tool you do not have, return a
  `blocked` result. Do not improvise.
- Loops are stateless. Each invocation is independent. Do not assume
  state from a previous run.
