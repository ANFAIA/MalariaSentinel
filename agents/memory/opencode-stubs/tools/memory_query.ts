import { tool } from "@opencode-ai/plugin"
import path from "path"

// memory_query — run an arbitrary Cypher query against the project
// knowledge graph. Read by default; pass rw=true for writes (use
// sparingly — most writes should go through memory_node / memory_rel).

export default tool({
  description:
    "Run an arbitrary Cypher query against the project knowledge graph. " +
    "Read-only by default; pass rw=true for writes. Use this for " +
    "known-shape queries (by uuid, by label, by cypher). For fuzzy " +
    "semantic recall, use mcp__graphiti-memory__search_nodes instead.",
  args: {
    cypher: tool.schema
      .string()
      .describe(
        "The Cypher query. Multi-line is fine. Use $param placeholders " +
          "for any user-supplied strings; do not interpolate them into " +
          "the query string.",
      ),
    rw: tool.schema
      .boolean()
      .optional()
      .describe(
        "Set true to allow writes. Default false. Prefer memory_node " +
          "and memory_rel for typed writes; only use rw=true for bulk " +
          "operations that the typed tools don't cover.",
      ),
  },
  async execute(args, context) {
    const script = path.join(
      context.worktree,
      "agents/memory/scripts/memory.sh",
    )

    const rwFlag = args.rw ? "--rw" : ""
    const result = await Bun.$`bash ${script} query ${args.cypher} ${rwFlag}`.text()
    return result.trim()
  },
})
