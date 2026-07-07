import { tool } from "@opencode-ai/plugin"
import path from "path"

// memory_audit — run the three schema invariants. Returns the counts
// of unlabeled nodes, orphan relations, and out-of-schema labels.
// All three should be 0; any non-zero is a schema violation that the
// seed pipeline must not produce.

export default tool({
  description:
    "Run the three schema invariants on the project knowledge graph. " +
    "Returns counts of (1) unlabeled Entity-only nodes, (2) orphan " +
    "relations whose endpoints don't exist, (3) labels outside the 8-label " +
    "schema. All three should be 0; a non-zero value is a schema " +
    "violation worth recording as a Pitfall. Run at the start of every " +
    "session and after every seed/wipe.",
  args: {},
  async execute(_args, context) {
    const script = path.join(
      context.worktree,
      "agents/memory/scripts/memory.sh",
    )

    const result = await Bun.$`bash ${script} audit`.text()
    return result.trim()
  },
})
