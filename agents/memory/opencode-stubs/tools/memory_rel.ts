import { tool } from "@opencode-ai/plugin"
import path from "path"

// memory_rel — create or update one typed relation between two
// existing nodes. Fails loudly if either endpoint uuid does not exist.

export default tool({
  description:
    "Create or update one typed relation between two existing nodes. " +
    "Both endpoint uuids must already exist in the graph; the call " +
    "fails with a clear error if either is missing. Use this after " +
    "memory_node calls for both endpoints. Re-running with the same " +
    "src/type/dst updates the existing relation (idempotent).",
  args: {
    type: tool.schema
      .string()
      .describe(
        "Relation type, e.g. 'TESTS', 'INCLUDES', 'PART_OF', 'USES'. " +
          "UPPERCASE_WITH_UNDERSCORES convention.",
      ),
    src: tool.schema
      .string()
      .describe("UUID of the source node. Must exist."),
    dst: tool.schema
      .string()
      .describe("UUID of the destination node. Must exist."),
    props: tool.schema
      .record(tool.schema.string(), tool.schema.string())
      .optional()
      .describe(
        "Optional relation properties as key=value strings, e.g. " +
          "{ role: 'anchor', weight: '3' }.",
      ),
  },
  async execute(args, context) {
    const script = path.join(
      context.worktree,
      "agents/memory/scripts/memory.sh",
    )

    const propArgs: string[] = []
    if (args.props) {
      for (const [k, v] of Object.entries(args.props)) {
        propArgs.push(`--prop ${k}=${v}`)
      }
    }

    const result = await Bun.$`bash ${script} rel --type ${args.type} --src ${args.src} --dst ${args.dst}${propArgs.length ? ` ${propArgs.join(" ")}` : ""}`.text()
    return result.trim()
  },
})
