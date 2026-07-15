# M-perf: Issue Checklist (GH Project v2 board)

**Milestone**: M-perf (between M2 "ABM validation" and M3 "U-Net surrogate")
**Board**: ANFAIA/MalariaSentinel Project v2 (`#11`)
**Columns**: Todo → In Progress → Done
**Labels on every issue**: `M-perf`, type (`enhancement` or `investigation`), `blocked` if gated

The `#TBD` placeholders below are replaced with real GH issue numbers by the user when the issues are created. This file is the **plan**, not the issue list — the supervisor will use it to scope the GitHub milestone `M-perf` and the user will create the issues.

**Status legend**: `[ ]` = Todo (not started), `[~]` = In Progress, `[x]` = Done, `[B]` = Blocked.

**Acceptance gating** (repeated from `perf-cpp-abm-plan.md` §6):
- F1 must land before F2/F3.
- F2 must land before F3.
- F3 must hit the M2 target (<5 min wall for 100 rollouts on 1 `ilk` node) before F4 can be unblocked.
- F4 is **gated** on F1-F3 being in production AND a profiling result showing F3 missed by >2×. If F3 hits the target, F4 is **cancelled** (moved to M7+).
- F5 is **gated** on F4-results (success, cancellation, or M7+ biology being added).

---

## F1 — Load-bearing: single-thread C++ engine with bit-compatible output

- [ ] #TBD — F1.a scaffold `mal-abm-fast/` package (CMakeLists + vcpkg.json + uv pyproject) [enhancement, M-perf]
- [ ] #TBD — F1.b implement climate + habitat_engine modules (env.tif + gpkg readers) [enhancement, M-perf]
- [ ] #TBD — F1.c implement mosquito_state SoA + PRNG + day loop (single-thread) [enhancement, M-perf]
- [ ] #TBD — F1.d implement output contract writer (COG + sidecar) bit-compatible with M1.5 [enhancement, M-perf]
- [ ] #TBD — F1.e parity test harness: same seed → same COG within 1e-5 vs Python ABM [investigation, M-perf]
- [ ] #TBD — F1.f determinism test: bit-equal output for repeated runs [investigation, M-perf]
- [ ] #TBD — F1.g benchmark: ≤ 30 s/rollout on workstation (acceptance: M2 target alignment) [investigation, M-perf]
- [ ] #TBD — F1.h SLURM sbatch templates for FT3 ilk partition [enhancement, M-perf]

## F2 — OpenMP parallel rollouts (1 node, 64 cores)

- [ ] #TBD — F2.a `--n-rollouts` flag + per-rollout sub-seed scheme (splitmix64 of seed XOR rollout_idx) [enhancement, M-perf, blocked-by:F1]
- [ ] #TBD — F2.b OpenMP embarrassingly-parallel rollout loop, one rollout per thread [enhancement, M-perf, blocked-by:F1]
- [ ] #TBD — F2.c per-rollout output file naming + directory layout (`*_seed{NNNN}.tif`) [enhancement, M-perf, blocked-by:F1]
- [ ] #TBD — F2.d benchmark: 64 rollouts on 1 `ilk` node ≤ 1 min wall [investigation, M-perf, blocked-by:F1]

## F3 — OpenMP intra-rollout + SIMD on SoA

- [ ] #TBD — F3.a OpenMP `#pragma omp parallel for` on the 5 per-day operations [enhancement, M-perf, blocked-by:F1,F2]
- [ ] #TBD — F3.b SIMD path on the SoA population (Eigen or `std::experimental::simd` guarded by `__INTEL_COMPILER`) [enhancement, M-perf, blocked-by:F1,F2]
- [ ] #TBD — F3.c AVX-512 runtime detection via `__builtin_cpu_supports("avx512f")`; AVX2 fallback on Apple Clang [enhancement, M-perf, blocked-by:F1,F2]
- [ ] #TBD — F3.d re-verify parity test (1e-5 tolerance still holds with SIMD reorderings) [investigation, M-perf, blocked-by:F1,F2]
- [ ] #TBD — F3.e M2 acceptance: 100 rollouts, 1 `ilk` node → **<5 min wall** [investigation, M-perf, blocked-by:F1,F2]

## F4 — MPI multi-node (GATED)

- [ ] #TBD — F4 profiling report: F3 missed M2 target by >2× and per-rollout cost is the bottleneck [investigation, M-perf, blocked]
- [ ] #TBD — F4.a `--mpi` flag + domain decomposition of active patches by `(row, col)` ranges [enhancement, M-perf, blocked]
- [ ] #TBD — F4.b MPI boundary exchange for adult dispersal across patch partitions [enhancement, M-perf, blocked]
- [ ] #TBD — F4.c impi/2021.3.0 + Infiniband HDR 100 transport verification [enhancement, M-perf, blocked]
- [ ] #TBD — F4.d benchmark: 100 rollouts, 4 `ilk` nodes → ≤ 3 min wall [investigation, M-perf, blocked]

**F4 cancellation note**: if F3 hits the M2 target (<5 min wall for 100 rollouts on 1 `ilk` node), F4 is **cancelled** and the work is moved to M7+. The blocked label stays until F3-results are in.

## F5 — SYCL / CUDA stretch (M7+ scope, not in M-perf)

- [ ] #TBD — F5.a port SoA kernels to SYCL (Intel oneAPI DPC++) for FT3 Ponte Vecchio GPUs [enhancement, M-perf, blocked-by:F4-results]
- [ ] #TBD — F5.b CUDA path for an NVIDIA A100 node (alternative backend) [enhancement, M-perf, blocked-by:F4-results]
- [ ] #TBD — F5.c benchmark on GPU: 100 rollouts, 1 GPU node → ≤ 1 min wall [investigation, M-perf, blocked-by:F4-results]

**F5 cancellation note**: if F4 is cancelled (F3 hits the target), F5 is also cancelled. F5 is **explicitly M7+ scope** and is not on the M2/M3 critical path.

---

## Cross-cutting (apply to all phases)

- [ ] #TBD — X.1 record `pitfall-premature-mpi` in the KB (Pitfall label, `project-wisdom` parent) before F1 starts [enhancement, M-perf]
- [ ] #TBD — X.2 record `op-m-perf-abm-cpp` Operational node in the KB (milestone plan, KB anchor) [enhancement, M-perf]
- [ ] #TBD — X.3 update `AGENTS.md` with the M-perf module entry (`mal-abm-fast/`) once F1.a lands [enhancement, M-perf, blocked-by:F1.a]
