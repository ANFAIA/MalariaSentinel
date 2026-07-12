import { tool } from "@opencode-ai/plugin"
import path from "path"

// memory_recall — semantic search over the project knowledge graph.
// Embeds the query, runs a vector search against entity_name_embedding,
// and for each hit attaches the chain to the root (via PART_OF edges)
// plus the depth-1 lateral neighbourhood (any other verb, both
// directions). All reads — no writes. Idempotent.

export default tool({
  description:
    "Semantic recall over the project knowledge graph. Takes a " +
    "natural-language query, embeds it, and returns the top-k most " +
    "similar nodes (default k=5). For each hit, the result includes: " +
    "(1) the node's uuid, name, summary and labels; (2) the score; " +
    "(3) chain_to_root — the path from the node up to its tree root " +
    "via PART_OF edges; (4) connected — the depth-1 lateral " +
    "neighbourhood (other verbs, both directions, excluding PART_OF " +
    "which is already in the chain). This is the canonical recall " +
    "path — use it instead of mcp__graphiti-memory__search_nodes, " +
    "which is broken on our wrapper-written nodes (DateTime " +
    "serialization bug).",
  args: {
    query: tool.schema
      .string()
      .describe(
        "Natural-language query. Will be embedded with text-embedding-3-small " +
          "(1536d) and matched against the entity_name_embedding index.",
      ),
    k: tool.schema
      .number()
      .int()
      .positive()
      .max(50)
      .optional()
      .describe("Number of hits to return (default 5, max 50)."),
    gid: tool.schema
      .string()
      .optional()
      .describe(
        "Override the project group_id (default: read from " +
          "agents/memory/.project).",
      ),
  },
  async execute(args, context) {
    const script = path.join(
      context.worktree,
      "agents/memory/scripts/recall.sh",
    )
    const k = args.k !== undefined ? String(args.k) : ""
    const gid = args.gid !== undefined ? args.gid : ""
    const result = await Bun.$`bash ${script} ${args.query} ${k} 1 ${gid}`.text()
    return result.trim()
  },
})
