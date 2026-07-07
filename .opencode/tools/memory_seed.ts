import { tool } from "@opencode-ai/plugin"
import path from "path"

// memory_seed — re-apply the project's seed yaml (and bootstrap
// entries). Idempotent: every MERGE keys on uuid + group_id, so
// re-running converges to the same state. Use after editing
// agents/memory/seed/<project>.yaml or to refresh after a wipe.

export default tool({
  description:
    "Re-apply the project's seed yaml and the bootstrap entries. " +
    "Idempotent — re-running converges to the same state. Use this " +
    "after editing agents/memory/seed/<project>.yaml, or to refresh " +
    "the graph after a wipe, or as part of a cold-start. The project " +
    "slug is read from agents/memory/.project unless you pass an " +
    "explicit value.",
  args: {
    project: tool.schema
      .string()
      .optional()
      .describe(
        "Project slug (the Neo4j group_id). Defaults to the value in " +
          "agents/memory/.project. Override only when testing a " +
          "different project's seed against this checkout.",
      ),
  },
  async execute(args, context) {
    const script = path.join(
      context.worktree,
      "agents/memory/scripts/memory.sh",
    )

    const projectArg = args.project ?? ""
    const result = await Bun.$`bash ${script} seed ${projectArg}`.text()
    return result.trim()
  },
})
