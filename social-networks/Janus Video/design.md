# Janus — LinkedIn Video 60s

**Format**: 1080 × 1350 (vertical 4:5 LinkedIn) · 60s · 8 scenes · palette slate & sage (parent deck).

## Architecture (real, source of truth)

From `agents/janus/` source code (M10 + M14 + M15):

```
┌─────────────────────────────────────────────────────────────┐
│ SUPERVISOR (opencode primary agent)                         │
│   — talks to the user                                        │
│   — plans and integrates, NEVER edits                        │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│ JANUS (single orchestrator, two entry modes)                │
│   ┌─────────────────┐  handoff  ┌────────────────────────┐  │
│   │ ONBOARDING       │  ───────▶ │ IMPROVEMENT            │  │
│   │ (REPL, read-only)│  ◀─────── │ (goal-driven, edit)    │  │
│   │ 8 onboard tools  │  context  │ 17 orchestrator tools  │  │
│   │ → run, diagnose, │  + KB     │ → gitagent, pipeline,  │  │
│   │   list, route    │           │   kg, improve, search  │  │
│   └─────────────────┘           └────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
                              │
              spawns (gitagent_init → start → spawn)
                              ▼
┌─────────────────────────────────────────────────────────────┐
│ 8 SUBAGENTS + 1 RESEARCH (registry at config/subagents.yaml)│
│  abm · scoring · ingest · download · prediction · training  │
│  data · commonlib · research (read-only)                    │
│  Each: spec, skills, mailbox_inbox, edits_allow, plugins    │
└─────────────────────────────────────────────────────────────┘
                              │
              isolated worktree per subagent
                              ▼
┌─────────────────────────────────────────────────────────────┐
│ 8 WORKTREES (gitagent) — one per subagent, file-fs sandbox  │
│   .gitagent/features/<key>/agents/<id>/worktree/             │
│   deny: /data, /, secrets, .git                            │
│   allow: own worktree                                       │
└─────────────────────────────────────────────────────────────┘
                              │
              propose → review → integrate → finalize
                              ▼
┌─────────────────────────────────────────────────────────────┐
│ GLUE                                                         │
│   MAILBOX        runs/<session>/mailbox/{inbox,outbox}-<n> │
│   PLUGINS        EditPlugin, ReadOnlyPlugin, per-subagent    │
│                  (scoring, download, ingest, training, ...)  │
│   SCOPE VALATOR  plain code, runs after proposals, validates │
│                  edits_allow globs, blocks cross-scope       │
│   SCORER PLUGIN  after_task hook auto-runs score_then_compare │
└─────────────────────────────────────────────────────────────┘
```

## 8 scenes at 60s

| # | Scene | Time | Story | Diagram |
|---|---|---|---|---|
| 1 | HARNESS | 0.0–7.0s | The anti-thesis: stop coding, start planning. JANUS is the harness. | Title card + thesis |
| 2 | SUPERVISOR | 7.0–14.0s | Top of the stack: opencode primary agent. Plans. Never edits. | Vertical card: USER → SUPERVISOR |
| 3 | ORCHESTRATORS | 14.0–22.0s | Janus has TWO entry modes that talk to each other. Onboarding REPL + Improvement goal-driven. | Vertical 4-row: SUPERVISOR → split into ONBOARDING + IMPROVEMENT, with handoff arrow |
| 4 | SUBAGENTS | 22.0–30.0s | 8 specialized subagents in the registry. Each: name, role, edits_allow, plugin. | 4×2 grid of subagent tiles, each with name + role + scope |
| 5 | WORKTREES | 30.0–38.0s | Each subagent works in its isolated gitagent worktree. Sandbox: write only own worktree, deny data/.git/secrets. | Subagent row "drops down" into isolated worktree boxes; mailbox center; proposals go up |
| 6 | METHOD | 38.0–46.0s | Seven phases of a reasoned decision. Orchestrator runs them in order. | Vertical 7-step timeline (RECON → DIAGNOSE → HYPOTHESIZE → CONTEXT → ASK → DELEGATE → VALIDATE) |
| 7 | GLUE | 46.0–52.0s | The integration mechanism: mailbox, plugins, scope validator, ScorerPlugin. | 4 vertical cards: MAILBOX (envelope), PLUGINS (plug), SCOPE (guard), SCORER (auto) |
| 8 | STATE + ANFAIA | 52.0–60.0s | M10/M14/M15 done. M16/M17 pending. ANFAIA credit. Honest close. | 5-row status table + ANFAIA card |

Transitions at 6.55, 13.55, 21.55, 29.55, 37.55, 45.55, 51.55 (subtle fade).

## Design tokens

- `bg`: #2F404F (deep slate)
- `bg-deep`: #283845
- `surface`: #3A4D5C
- `fg`: #F0F1EE (warm off-white)
- `muted`: #C7DAD3 (sage)
- `dim`: #B0BCC2
- `accent`: #3894A1 (decor only)
- `bright`: #6EC8D4 (interactive highlights)
- `rule`: rgba(240,241,238,.12)
- Font: Space Grotesk 300–700 (local copy)
- Mono: system monospace fallback (JetBrains unavailable)

## Motion principles

- Each scene fades in (0.55s power3.out)
- Children stagger from y=34 (0.62s, 0.11s gap)
- Vertical panels use `back.out(1.4)` for snap
- Subagent grid reveals with `expo.out` stagger
- Worktree sandbox boxes drop in with `back.out(1.6)` from below
- Method timeline: sequential reveal with 0.1s gap
- ANFAIA scene: closing fade to bg + bounce on large word

## Honest framing

- M10 orchestrator: skeleton → DONE
- M14 plugin system: DONE
- M15 observability: DONE
- M16 full replay: PENDING
- M17 goal language: PENDING
- "Still in development. Still rough. Plenty to improve."

## LinkedIn copy

- EN: <150 words, hook → what → honest status → ANFAIA → CTA → link → 3–5 hashtags
- ES: same structure, Spanish
- Tone: direct, builder-to-builder, ANFAIA credited

## Deliverables

- `index.html` — HyperFrames composition, 8 scenes, GSAP timeline
- `design.md` — this file
- `render.mp4` — 60s, 1080×1350, 30fps
- `linkedin-post.md` — bilingual EN/ES copy
