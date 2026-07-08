import { tool } from "@opencode-ai/plugin"
import path from "path"
import { existsSync } from "fs"

// memory_init — check the project's memory-module installation state.
// Read-only. Returns a structured report with what's in place, what's
// missing, and the recommended next step. Use this when you land in a
// project that may or may not have the memory module wired up. The
// tool will not modify any file.

type Check = { name: string; ok: boolean; detail: string }
type Report = {
  project_root: string
  project_slug: string | null
  checks: Check[]
  next_step: string
  ready: boolean
}

export default tool({
  description:
    "Check the memory module's installation state in this project. " +
    "Read-only: reports what's in place (project slug, opencode stubs, " +
    "skill, runtime config, docker stack health) and returns the " +
    "recommended next step. Call this when you land in a project that " +
    "may or may not have the memory module wired up. Does not modify " +
    "any file. The result is a JSON-like string the agent can parse.",
  args: {
    verbose: tool.schema
      .boolean()
      .optional()
      .describe(
        "If true, also probe Neo4j and Graphiti MCP via the runtime " +
          "scripts (slower). Default: false (just file checks).",
      ),
  },
  async execute(args, context) {
    const root = context.worktree
    const checks: Check[] = []
    const push = (name: string, ok: boolean, detail: string) =>
      checks.push({ name, ok, detail })

    // 1. Project slug file
    const projectFile = path.join(root, "agents/memory/.project")
    let slug: string | null = null
    if (existsSync(projectFile)) {
      slug = (await Bun.file(projectFile).text()).trim() || null
      push(
        ".project",
        slug !== null,
        slug ? `slug='${slug}'` : "file is empty",
      )
    } else {
      push(".project", false, `missing: ${projectFile}`)
    }

    // 2. OpenCode stubs (tools)
    const toolsDir = path.join(root, ".opencode/tools")
    const expectedTools = [
      "memory_node.ts",
      "memory_rel.ts",
      "memory_query.ts",
      "memory_audit.ts",
      "memory_seed.ts",
      "memory_status.ts",
      "memory_init.ts",
    ]
    for (const t of expectedTools) {
      const p = path.join(toolsDir, t)
      push(`opencode tool: ${t}`, existsSync(p), existsSync(p) ? "installed" : `missing: ${p}`)
    }

    // 3. Skill
    const skillFile = path.join(root, ".agents/skills/project-memory/SKILL.md")
    push(
      "skill: project-memory",
      existsSync(skillFile),
      existsSync(skillFile) ? "installed" : `missing: ${skillFile}`,
    )

    // 4. Runtime .env
    const envFile = path.join(root, "agents/memory/runtime/.env")
    push(
      "runtime .env",
      existsSync(envFile),
      existsSync(envFile) ? "present" : `missing: ${envFile}`,
    )

    // 5. opencode.json permission rules
    const opencodeJson = path.join(root, "opencode.json")
    let permOk = false
    let permDetail = ""
    if (existsSync(opencodeJson)) {
      try {
        const txt = await Bun.file(opencodeJson).text()
        const data = JSON.parse(txt) as {
          permission?: {
            edit?: Record<string, string>
            bash?: Record<string, string>
            memory_node?: string
            memory_rel?: string
            memory_query?: string
            memory_audit?: string
            memory_seed?: string
            memory_status?: string
          }
        }
        const p = data.permission ?? {}
        const editOk = p.edit?.["agents/memory/.project"] === "ask"
        const bashDenyOk =
          p.bash?.["make -f agents/memory/scripts/Makefile wipe *"] === "deny" &&
          p.bash?.["make -f agents/memory/scripts/Makefile set-project *"] === "deny"
        const toolsOk =
          p.memory_node === "ask" &&
          p.memory_rel === "ask" &&
          p.memory_query === "allow" &&
          p.memory_audit === "allow" &&
          p.memory_seed === "ask" &&
          p.memory_status === "allow"
        permOk = editOk && bashDenyOk && toolsOk
        const parts: string[] = []
        parts.push(`edit(.project)=${editOk ? "ok" : "missing"}`)
        parts.push(`bash-deny=${bashDenyOk ? "ok" : "missing"}`)
        parts.push(`memory-tools=${toolsOk ? "ok" : "missing"}`)
        permDetail = parts.join(", ")
      } catch (e) {
        permDetail = `opencode.json parse error: ${(e as Error).message}`
      }
    } else {
      permDetail = `missing: ${opencodeJson}`
    }
    push("opencode.json perms", permOk, permDetail)

    // 6. Optional: stack health (docker / neo4j-cli / graphiti)
    let stackDetail = "skipped (verbose=false)"
    let stackOk = true
    if (args.verbose) {
      const script = path.join(root, "agents/memory/scripts/memory.sh")
      try {
        const out = await Bun.$`bash ${script} status`.text()
        const healthy =
          out.includes("ok") && !out.includes("\"ok\": false") && !out.includes("unhealthy")
        stackOk = healthy
        stackDetail = healthy ? "all green" : "one or more checks failed — see status output"
      } catch (e) {
        stackOk = false
        stackDetail = `status script error: ${(e as Error).message}`
      }
    }
    push("stack health (verbose)", stackOk, stackDetail)

    // Decide next step
    const requiredOk = checks
      .filter((c) => !c.name.startsWith("stack health"))
      .every((c) => c.ok)
    const ready = requiredOk && stackOk
    let next_step: string
    if (!slug) {
      next_step =
        "Project slug missing. Run the install script: " +
        "`bash agents/memory/install.sh --project <slug> --openai-key sk-... --neo4j-password ...` " +
        "(or set the slug manually with `make -f agents/memory/scripts/Makefile set-project PROJECT=<slug>`)."
    } else if (!requiredOk) {
      next_step =
        "Memory module is partially installed. Re-run the installer (it's idempotent): " +
        "`bash agents/memory/install.sh` (will use existing values). " +
        "If you don't have an installer available, the install steps are documented in `agents/memory/README.md`."
    } else if (args.verbose && !stackOk) {
      next_step =
        "Files are in place but the stack is not healthy. " +
        "Run `make -f agents/memory/scripts/Makefile status` to see what's down, " +
        "then `make -f agents/memory/scripts/Makefile up` to bring it back."
    } else {
      next_step =
        "Memory module is fully wired up. Use `memory_seed` to apply your project seed, " +
        "or `make -f agents/memory/scripts/Makefile seed` if you prefer the CLI."
    }

    const report: Report = {
      project_root: root,
      project_slug: slug,
      checks,
      next_step,
      ready,
    }
    return JSON.stringify(report, null, 2)
  },
})
