import { tool } from "@opencode-ai/plugin"
import path from "path"

// memory_node — create or update one typed node in the project
// knowledge graph. Validates the label against the schema before any
// Cypher runs. Re-running with the same uuid updates the visible
// properties; does not duplicate.

export default tool({
  description:
    "Create or update one typed node in the project knowledge graph. " +
    "Validates the label against the 8-label schema before any write. " +
    "Re-running with the same uuid updates the existing node (idempotent). " +
    "Use this for any node that belongs to a structural class (Component, " +
    "Investigation, Architecture, Pattern, Pitfall, Tool, Operational, " +
    "Preference). For free-form text observations use mcp__graphiti-memory__" +
    "add_memory with source text instead.",
  args: {
    type: tool.schema
      .enum([
        "Component",
        "Investigation",
        "Architecture",
        "Pattern",
        "Pitfall",
        "Tool",
        "Operational",
        "Preference",
      ])
      .describe("Schema label. Must be one of the 8 valid types."),
    uuid: tool.schema
      .string()
      .describe(
        "Stable UUID. Use a kebab-case slug (e.g. 'pkg-mal-core', " +
          "'inv-graphiti-mcp-json-bug'). The MERGE keys on uuid+group_id.",
      ),
    name: tool.schema
      .string()
      .describe(
        "Short, dated if session-like (e.g. 'ADR-2026-07-04: Neo4j as " +
          "memory backend').",
      ),
    summary: tool.schema
      .string()
      .describe("One-paragraph description. Multi-line is fine."),
    path: tool.schema
      .string()
      .optional()
      .describe("Optional filesystem path inside the project (e.g. 'mal-core/')."),
  },
  async execute(args, context) {
    const script = path.join(
      context.worktree,
      "agents/memory/scripts/memory.sh",
    )
    const cmd = [
      "bash",
      script,
      "node",
      "--type",
      args.type,
      "--uuid",
      args.uuid,
      "--name",
      args.name,
      "--summary",
      args.summary,
    ]
    if (args.path) cmd.push("--path", args.path)

    const result = await Bun.$`bash ${script} node --type ${args.type} --uuid ${args.uuid} --name ${args.name} --summary ${args.summary}${args.path ? ` --path ${args.path}` : ""}`.text()
    return result.trim()
  },
})
