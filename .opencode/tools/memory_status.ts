import { tool } from "@opencode-ai/plugin"
import path from "path"

// memory_status — quick health check for the three runtime pieces:
// docker (Neo4j + Graphiti MCP containers), neo4j-cli (a RETURN 1
// query against the bolt endpoint), and the Graphiti MCP HTTP health
// probe. Returns a human-readable summary.

export default tool({
  description:
    "Check the health of the three runtime pieces: docker (Neo4j + " +
    "Graphiti MCP containers), neo4j-cli (a RETURN 1 query against " +
    "the bolt endpoint), and the Graphiti MCP HTTP health probe on " +
    ":8000. Returns a human-readable summary. Use this at the start " +
    "of a session to confirm the stack is up before running queries, " +
    "or when a query fails unexpectedly to rule out a stack issue.",
  args: {},
  async execute(_args, context) {
    const script = path.join(
      context.worktree,
      "agents/memory/scripts/memory.sh",
    )

    const result = await Bun.$`bash ${script} status`.text()
    return result.trim()
  },
})
