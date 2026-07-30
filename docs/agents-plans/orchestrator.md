# Orchestrator — ABM Dispersal 3-Plan Comparison

| Field | Value |
|---|---|
| **Feature key** | `abm-dispersal-plans` |
| **Sub-features** | `abm-dispersal-plan-a`, `abm-dispersal-plan-b`, `abm-dispersal-plan-c` |
| **Status** | proposed |
| **Goal** | Spawn 3 gitagent worktrees (A, B, C), compare their composite scores + D16 spatial metrics on identical inputs, pick a winner by objective criteria, integrate to `main` as one commit. |
| **Owner** | supervisor (this session) |
| **Pre-req** | The 3 plan files in `docs/agents-plans/plan-{A,B,C}-*.md` exist on `main`. |

---

## 1. Why a 3-plan comparison

The current ABM dispersal produces too-narrow a spatial front against the empirical Thomas 2013 kernel. There are **three distinct, literature-supported mechanisms** that could fix this:

| Plan | File | Mechanism | Sessions | Risk |
|---|---|---|---|---|
| **A** | [`docs/agents-plans/plan-A-windborne.md`](./plan-A-windborne.md) | Tune existing windborne + viability gate | 1.5 | Low |
| **B** | [`docs/agents-plans/plan-B-host-seeking.md`](./plan-B-host-seeking.md) | Wire directed host-seeking flight | 3.0 | Med |
| **C** | [`docs/agents-plans/plan-C-oviposition-seeking.md`](./plan-C-oviposition-seeking.md) | Natal patch fidelity + oviposition walk | 2.0 | Med |

Rather than pick blind, the supervisor spawns 3 isolated worktrees, lets each implement their plan in parallel, then chooses the winner on **measured metrics** (composite score + D16 spread metrics) rather than on **theoretical preference**.

## 2. The 11-step orchestration

### Step 1 — Init the feature

```bash
cd /Users/davidflorezmazuera/Downloads/MalariaSentinel
gitagent init
gitagent start --feature abm-dispersal-plans
```

### Step 2 — Spawn 3 worktrees in ONE message (parallel)

The supervisor sends 3 `gitagent spawn` calls in the same message. Each agent gets a unique `--id` and a brief that points at the corresponding plan file.

```bash
gitagent spawn --feature abm-dispersal-plans --id plan-a \
    --role "Plan A: windborne boost + viability gate" \
    --base main

gitagent spawn --feature abm-dispersal-plans --id plan-b \
    --role "Plan B: host-seeking directed flight" \
    --base main

gitagent spawn --feature abm-dispersal-plans --id plan-c \
    --role "Plan C: oviposition-site-seeking + site fidelity" \
    --base main
```

### Step 3 — Identical brief template (slot-filled per plan)

Each agent receives the same template, with the `<<PLAN>>` slot replaced:

```
You are agent `<<ID>>` in feature `abm-dispersal-plans`.
Your worktree: .gitagent/features/abm-dispersal-plans/agents/<<ID>>/worktree

Read your plan in full: docs/agents-plans/<<PLAN>>.md

Mandatory order of operations:
  1. F1.e parity removal (delete test_abm_fast_parity.py in both
     mal-core and mal-ghana-sim; update README.md and perf-cpp-abm-plan.md
     F1.e language). Run `pytest -m fast` to confirm no other test broke.
  2. Implement your plan's code changes exactly as specified.
  3. Add the new scorers (D16 always; D17 for B; D18 for C).
  4. Update thresholds.yaml and composite.py weights.
  5. Run the 3 verification commands (see Step 4).
  6. Append a JSON block to the bottom of your plan file
     (under a "## Results" heading you create) with the metrics
     described in Step 5.
  7. `gitagent propose --agent <<ID>> --title "..." --summary "..." \
      --confidence 0.8` from the repo root.

Do NOT touch any file outside the lists in your plan's "Files modified" section.
Do NOT modify AGENTS.md, .gitignore, opencode.json, or agents/memory/.project.
Do NOT push. Do NOT finalize. Do NOT accept other agents' proposals.
```

### Step 4 — Each agent runs these 3 commands

```bash
# (1) C++ build + ctest
cd mal-core/src/mal_core/abm && cmake --build build -j && ctest --test-dir build --output-on-failure

# (2) Calibration fast suite (PR gate)
cd mal-core/src/mal_core/abm/tests/calibration && uv run pytest -m fast -v

# (3a) 30-day Ghana sim — captures D1, D13, parity regression
cd mal-ghana-sim && uv run python scripts/03_simulate.py --days 30 --seed 1

# (3b) 180-day Ghana sim — captures D16 spread metrics, D17 host clustering, D18 site fidelity
cd mal-ghana-sim && uv run python scripts/03_simulate.py --days 180 --seed 1
```

### Step 5 — Each agent returns a JSON manifest in its proposal

The proposal's `--summary` field must end with this JSON block (so the supervisor can parse it):

```json
{
  "branch": "common/abm-plan-X",
  "commit_sha": "<sha>",
  "build_pass": true,
  "test_pass": true,
  "test_details": {
    "fast_pytest_pass": true,
    "ctest_pass": true
  },
  "scorer_scores": {
    "D1_expansion": 0.74,
    "D13_host_seeking_distance": 0.81,
    "D16_spread_rate": 0.72,
    "D17_host_clustering": 0.66,
    "D18_site_fidelity": null
  },
  "spread_p90_km": 11.4,
  "spread_median_km": 0.51,
  "spread_n_cells_day180": 184,
  "composite_score": 0.73,
  "files_modified": ["mal-core/src/mal_core/abm/src/wire.hpp", "..."],
  "parity_test_status": "deleted"
}
```

Plans that don't introduce a particular scorer (Plan A: no D17/D18; Plan B: no D18; Plan C: no D17) report `null` for that scorer's score and the implementation must not register it in `composite.py`.

### Step 6 — Supervisor compares in a table

After all 3 proposals arrive, the supervisor builds a comparison table:

| Metric | Plan A | Plan B | Plan C | Winner |
|---|---|---|---|---|
| `composite_score` | ? | ? | ? | ≥ 0.7 + highest |
| `spread_p90_km` | ? | ? | ? | in [5, 20] |
| `spread_median_km` | ? | ? | ? | in [0.3, 0.8] |
| `D1_expansion` | ? | ? | ? | no regression > 0.05 |
| `D13_host_seeking_distance` | ? | ? | ? | no regression > 0.05 |
| `D16_spread_rate` | ? | ? | ? | ≥ 0.7 |
| Plan-specific scorer (D17 or D18) | n/a | ? | ? | ≥ threshold |
| Build + fast pytest | pass? | pass? | pass? | all must pass |
| Sessions used (planned vs actual) | 1.5/? | 3.0/? | 2.0/? | — |

**Selection rule (deterministic):**

1. Hard gate: `composite_score ≥ 0.7` AND `spread_p90_km ∈ [5, 20]` AND no scorer regressed > 0.05 vs the pre-M7 baseline recorded in the calibration history.
2. Tie-breaker #1: highest composite score.
3. Tie-breaker #2: closest `spread_p90_km` to 12.5 km (the centre of the [5, 20] target band, which is the empirical p90 from Thomas 2013: ~1.28 km/day × 14 days is not the right scaling; the target is the *cumulative* p90 at day 180, which is empirically 5–20 km).
4. Tie-breaker #3: smallest diff vs baseline (least disruptive change). Plans that did *more* (i.e. spent more sessions) are penalised because the supervisor has the option of porting only the winning subset of changes.
5. Tie-breaker #4: the plan that produced the fewest `out_of_schema` warnings in the new scorers.

If **no plan** passes the hard gate, the supervisor does **not** finalize. It instead:
- Logs a `Pitfall` node: `pitfall-m7-no-dispersal-plan-passed-gate` summarising all 3 attempts and metrics.
- Writes a `Component` node: `comp-abm-dispersal-M7-blocked` explaining the blocker.
- Returns control to the user with the comparison table; the user decides whether to retry with new parameters, or fall back to the pre-M7 baseline.

### Step 7 — Integrate the winner

```bash
# Accept the winning proposal
gitagent accept <winning_pid> --feature abm-dispersal-plans

# Reject the losers (or leave pending; they will be skipped by integrate)
gitagent reject <losing_pid_1> --feature abm-dispersal-plans --reason "composite below winner"
gitagent reject <losing_pid_2> --feature abm-dispersal-plans --reason "composite below winner"

# Integrate (will apply only the accepted proposal)
gitagent integrate --feature abm-dispersal-plans
```

### Step 8 — Finalize

```bash
gitagent finalize --feature abm-dispersal-plans \
    --message "feat(abm): evolve dispersal per Plan X (winner) — see docs/agents-plans/plan-X-*.md"
```

This produces **one** commit on `main`.

### Step 9 — Push (with `git ps`, force-with-lease)

```bash
cd /Users/davidflorezmazuera/Downloads/MalariaSentinel
git fetch origin
git log --oneline origin/main..HEAD   # confirm only 1 commit
git ps origin main
```

If the remote ref has moved since the last fetch, `git ps` aborts cleanly. Never use `git push --force`.

### Step 10 — Full verification

```bash
# Full fast suite
cd mal-core/src/mal_core/abm/tests/calibration && uv run pytest -m fast -v

# 30-day Ghana run as smoke test
cd mal-ghana-sim && uv run python scripts/03_simulate.py --days 30 --seed 1
```

If anything regresses, the supervisor reverts the commit (`git reset --hard origin/main`) and re-raises the comparison table.

### Step 11 — Knowledge graph housekeeping

The supervisor writes 2 KB nodes:

```bash
# 1. Operational node — what we did
memory_node \
    --uuid comp-abm-dispersal-M7-evolved \
    --name "M7: ABM dispersal evolved (3-plan comparison)" \
    --type Operational \
    --summary "On 2026-XX-XX we ran 3 competing ABM dispersal plans (A=windborne, B=host-seeking, C=oviposition-site). Winner: Plan X with composite=Y.YY, D16=0.7Z, p90=WW km. See docs/agents-plans/orchestrator.md for the comparison table. Code lives in commit <sha>."

memory_rel \
    --src comp-abm-dispersal-M7-evolved \
    --dst obj-centinela-sdss \
    --type PART_OF

# 2. Component node — what shipped
memory_node \
    --uuid comp-abm-dispersal-evolved \
    --name "ABM dispersal (M7 evolved)" \
    --type Component \
    --summary "M7 dispersal model: <one-paragraph description of the winning mechanism and parameter values>. Replaces M7 baseline. Scorers: D1, D13, D16 (+ D17 or D18 if applicable)."

memory_rel \
    --src comp-abm-dispersal-evolved \
    --dst comp-centinela \
    --type PART_OF
```

**Pitfall logging (conditional)**: if any plan caused the F1.e parity-test removal to break a different test, log:

```bash
memory_node \
    --uuid pitfall-m7-parity-removal-cascade \
    --name "F1.e parity removal cascade in M7" \
    --type Pitfall \
    --summary "Removing test_abm_fast_parity.py in M7 caused N other tests to fail because they imported the parity helper. Fix: <description>."
```

### Step 12 — Session end

```bash
make -f agents/memory/scripts/Makefile session-end
```

## 3. Failure modes & recovery

| Failure | Symptom | Recovery |
|---|---|---|
| Agent A proposes with `composite < 0.7` | Plan A fails the hard gate | Supervisor notes in the comparison table, proceeds to B and C. If **all** fail, see "no plan passes" above. |
| Agent B's `HOST_APPROACH` breaks the state machine | `ctest` fails with a state-transition assertion | Agent B re-proposes; supervisor waits; the other agents continue. |
| Agent C's `natal_patch_id` not initialised for adults created in `mosquito_state::init` | SEGV at first emergence | Agent C re-proposes with a zero-init in `init()`. |
| Two agents touch the same file (e.g. `wire.hpp`) | `gitagent integrate` reports `conflict` | The supervisor's selection rule picks only one branch, so only one proposal is `accepted`; the other stays `pending` and is `rejected` before `finalize`. No conflict at integrate. |
| `nearest_viable_cell` is added by both Plan A and Plan C | Duplicate symbol at link time | Plan A's helper is `static inline` in the header; Plan C's is a `HabitatEngine` method (different namespace). No collision. |
| 180-day Ghana run takes > 30 min | Timeout in the agent worktree | Increase `pytest -m fast` timeout in `pyproject.toml`; rerun. |
| All 3 plans regress vs baseline | Comparison shows every composite < baseline | Log `Pitfall`, return to user with table; do not finalize. |

## 4. Cross-plan dependencies

- `nearest_viable_cell` (Plan A) is reused by Plan C's `nearest_viable_patch`. If Plan A is not the winner, the supervisor ports Plan A's helper to the winner's branch before integration.
- `is_viable` (Plan A) is reused by Plan B's `detect_host_cell` filter. Same handling.
- D16 is a common scorer across all 3 plans. If two plans are both accepted (e.g. a B+C hybrid is desired), the supervisor would need to deduplicate D16 in `composite.py` — but Step 6's selection rule accepts only one branch, so this is moot in the standard flow.

## 5. Plan-branch naming

| Plan | Worktree | Branch (per gitagent convention: not used by gitagent, but referenced for the agent's own commits) |
|---|---|---|
| A | `wt/plan-a-windborne` | `common/abm-plan-a` |
| B | `wt/plan-b-host-seeking` | `common/abm-plan-b` |
| C | `wt/plan-c-oviposition-seeking` | `common/abm-plan-c` |

gitagent does **not** create or use these branches. They exist only for the agent's local `git commit` scratch work. The final commit on `main` is created by `gitagent finalize`, not by any agent.

## 6. Effort budget

| Step | Sessions |
|---|---|
| Step 1 (init) | 0.05 |
| Step 2 (spawn 3 agents, parallel) | 0.1 |
| Steps 3–5 (agent work, parallel) | up to 3 (limited by longest plan) |
| Step 6 (compare) | 0.2 |
| Step 7 (integrate) | 0.1 |
| Step 8 (finalize) | 0.05 |
| Step 9 (push) | 0.05 |
| Step 10 (verify) | 0.2 |
| Step 11 (KB writes) | 0.1 |
| Step 12 (session-end) | 0.05 |
| **Total (supervisor)** | **~0.9** |
| **Total (wall-clock, with parallelism)** | **~3.5** (max(plan sessions) + supervisor overhead) |

## 7. Acceptance criteria for the whole orchestration

- [ ] 3 proposals received, all with valid JSON manifests.
- [ ] Comparison table built and posted in this file under §6.
- [ ] Winner selected by the deterministic rule, no human override.
- [ ] `gitagent finalize` produced 1 commit on `main`.
- [ ] `git ps origin main` succeeded.
- [ ] `pytest -m fast` passes on `main` after the push.
- [ ] 30-day Ghana sim runs to completion on `main`.
- [ ] 2 KB nodes written (`comp-abm-dispersal-M7-evolved` + `comp-abm-dispersal-evolved`).
- [ ] KB `audit` passes (no new `unlabeled` / `orphans` / `out_of_schema`).
- [ ] `make session-end` completed without errors.

## 8. References

- [`docs/agents-plans/plan-A-windborne.md`](./plan-A-windborne.md)
- [`docs/agents-plans/plan-B-host-seeking.md`](./plan-B-host-seeking.md)
- [`docs/agents-plans/plan-C-oviposition-seeking.md`](./plan-C-oviposition-seeking.md)
- `docs/perf-cpp-abm-plan.md` (F1.e language, to be updated by every plan)
- `docs/m7-6-wind-dispersal-plan.md` (the M7.6 windborne baseline being evolved)
- `docs/dispersal-kernel-calibration.md` (Yang 2009 94% reduction reference)
- `papers/anopheles-dynamics/costantini-1996-anopheles-density-survival-dispersal.md`
- `papers/anopheles-dynamics/thomas-2013-anopheles-gambiae-gambia-dispersal.md`
- `papers/anopheles-dynamics/depinay-2004-anopheles-simulation-model.md`
- `AGENTS.md` (calibration framework conventions in this repo)
