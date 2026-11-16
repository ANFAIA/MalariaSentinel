# Question set — `scoring` stage

This file is the question set for the conceptual document of the **scoring**
stage of the MalariaSentinel pipeline: the post-run stage that turns the
artifacts of a finished agent-based-model execution into a *scorecard* — a
single composite number, a set of binary gates, and a list of what could not be
evaluated. It was written after reading the stage's material: the whole of
`mal-core/src/mal_core/scoring/` (registry, config, runner, feedback, the
`Scorer` base class, the thirteen composite scorers, the six gates, the LLM
judge and its prompt), the `score` / `validate-detections` / `validate-cases` /
`feedback` CLI commands, the state-COG writer in the C++ engine, the
`docs/concepts/README.md` stance note, and the (retired, non-authoritative)
`docs/specs/scoring/spec.md`. Every question below carries a `path:line`
citation a reviewer can open; where the code answers the question
unambiguously, the answer is recorded so the drafter can check the document
against the code instead of re-deriving it. Where the code does **not** answer
clearly, the question is marked **open** and repeated in part (c). Claims that
could not be verified are stated as such.

---

## (a) Question set

### A. What the stage is for

**Q1. What question does the scoring stage exist to answer, and what counts as
having answered it?**
Citation: `mal-core/src/mal_core/scoring/registry.py:1-18`; `mal-core/src/mal_core/scoring/scorers/base.py:1-10`; `docs/specs/scoring/spec.md:39-50`.
Answer: it exists to answer "is this simulation behaving like the malaria
literature it is meant to emulate, and did my change make it better or worse?"
The registry docstring states the weights reflect validation value for the
question *"is the system good?"*, and external validation plus core biology
dominate the weights while engineering invariants are demoted to gates. A
"scorecard" is the answer object: one composite number plus per-dimension
scores, gates, and skipped entries.

**Q2. What is explicitly out of scope for the stage?**
Citation: `mal-core/src/mal_core/scoring/runner.py:54-146`; `mal-core/src/mal_core/scoring/scorers/base.py:78-79`.
Answer: the stage neither re-runs nor re-parameterises the model. It reads
artifacts of a *finished* run; its only contract with the model is the
`score(run_dir, ctx) -> ScorerResult` method of each scorer
(`base.py:78-79`). Producing the run is the ABM stage's job; consuming the
scorecard downstream (feedback, iteration) is a separate stage.

**Q3. What are the stage's inputs and outputs, and where does the output
live?**
Citation: `mal-core/src/mal_core/scoring/runner.py:3-7`, `runner.py:120-146`; `mal-core/src/mal_core/cli.py:409-463`.
Answer: the input is one ABM output *directory* (plus optional AOI slug,
config file and scorer filters); the output is a single JSON file
`scorecard.json` written **inside** the run directory, whose keys are
`run_dir, aoi, composite, verdict, scores, composite_dimensions, gates,
skipped, timestamp` plus optional `verdict_llm` (`runner.py:120-133`,
`runner.py:144-146`).

### B. The registry: how scorers are declared

**Q4. What is the registry, and what does an entry contain?**
Citation: `mal-core/src/mal_core/scoring/registry.py:47-51`, `registry.py:79-104`.
Answer: `build_registry()` instantiates every scorer and gate and returns a
dict `name -> ScorerSpec(cls=..., kind=...)`, where `kind` is either
`"composite"` or `"gate"`. The registry is rebuilt on every call, so it is
always in sync with the code — there is no registry file to drift.

**Q5. How is a scorer written — what must a new scorer provide?**
Citation: `mal-core/src/mal_core/scoring/scorers/base.py:56-79`; `mal-core/src/mal_core/scoring/scorers/__init__.py:1-46`.
Answer: subclass `Scorer` and implement `score(run_dir, ctx) -> ScorerResult`;
declare class attributes `name`, `kind`, `description`, and optionally
`min_score`, `hard_floor`, `manual`. The file is then exported in
`scorers/__init__.py`, instantiated in `build_registry()`
(`registry.py:80-100`), and — if it is a composite dimension — given a weight
in `COMPOSITE_WEIGHTS` (`registry.py:53-67`).

**Q6. Which scorers exist, and what does each one measure?**
Citation: `mal-core/src/mal_core/scoring/registry.py:53-100`; the per-scorer
modules `d1_habitat_occupancy.py`, `d2_survival.py`, `d3_eip.py`,
`d4_stability.py`, `d5_morans.py`, `d8_coupling.py`,
`d11_aquatic_structure.py`, `d15_persistence.py`, `d16_detection_coverage.py`,
`d19_pool_persistence.py`, `d20_washout_response.py`, `d21_dispersal_kernel.py`,
`d25_cases_ghana.py`, `gates.py`.
Answer: thirteen composite dimensions — D1 habitat occupancy, D2 adult
survival, D3 EIP completion, D4 population stability, D5 Moran's I, D8
density–suitability coupling, D11 aquatic stage structure, D15 long-horizon
persistence, D16 detection coverage, D19 pluvial habitat persistence, D20
washout response, D21 dispersal kernel, D25 reported cases (Ghana) — and six
gates — G6 data validity, G7 determinism, G10 performance, G12 host input,
G14 mobility, G24 urban/rural ratio (`registry.py:69-76`).

**Q7. What are the weights, and where do they come from?**
Citation: `mal-core/src/mal_core/scoring/registry.py:53-67`; `mal-core/src/mal_core/scoring/config.py:30-31`.
Answer: `COMPOSITE_WEIGHTS` is the single source of truth: D16 = 4.0, D2 =
4.0, D15 = 3.0, D3 = 3.0, D8 = 2.0, D4 = 2.0, D25 = 2.0, and D1, D5, D11,
D19, D20, D21 = 1.0 each. The runner never reads a scorer's own `weight`
attribute; it asks the configuration, whose `weight_of()` falls back to
`COMPOSITE_WEIGHTS` and then to 1.0 (`config.py:30-31`).

**Q8. Does a scorer declare its own weight, and is that declaration used?**
Citation: `mal-core/src/mal_core/scoring/scorers/base.py:68`;
`mal-core/src/mal_core/scoring/scorers/d2_survival.py:23`;
`mal-core/src/mal_core/scoring/runner.py:112-118`; `registry.py:116`.
Answer: the base class declares `weight = 1.0` and each scorer overrides it
(e.g. D2 = 4.0), but the composite path never reads it — `runner.py:112` calls
`cfg.weight_of(name)`, and `list_scorers()` also reads `COMPOSITE_WEIGHTS`
(`registry.py:116`). The class attribute is currently redundant; the values
happen to agree with the table. **Open** (see part c): whether the class
attribute or the table should be the canonical one.

**Q9. How are scorers enabled, disabled and filtered?**
Citation: `mal-core/src/mal_core/scoring/config.py:34-48`, `config.py:51-95`;
`mal-core/src/mal_core/cli.py:414-418`, `cli.py:452-462`.
Answer: by default every scorer that is **not** `manual` is enabled
(`config.py:34-48`). A YAML config may enable/disable a scorer and override a
weight; the CLI `--enable` (manual scorers), `--only` (intersect) and `--skip`
(difference) are applied in that order and win over the file
(`config.py:75-95`). Unknown names raise `ValueError` (`config.py:68-72`).
CLI flags are comma-separated strings (`cli.py:452-454`).

**Q10. What does the `manual` flag mean and which scorers carry it?**
Citation: `mal-core/src/mal_core/scoring/scorers/base.py:72-76`;
`config.py:34-48`; `runner.py:87-93`;
`scorers/d16_detection_coverage.py:60`, `scorers/d25_cases_ghana.py:184`,
`scorers/gates.py:259`.
Answer: `manual = True` marks an AOI-dependent scorer that never runs by
default: it needs per-AOI data (occurrence table, urban raster, case series).
Such scorers are activated explicitly via `--enable` or a YAML
`enabled: true`, by an operator who knows the AOI has the data. Manual
scorers: D16, D25, G24.

**Q11. How does the AOI slug reach a scorer, and why is it never inferred?**
Citation: `mal-core/src/mal_core/scoring/scorers/base.py:164-172`;
`runner.py:34-40`; `cli.py:413`.
Answer: the AOI comes only from an explicit `--aoi` on the command line
(`cli.py:413` → `runner.py:34-40`). `require_aoi()` returns `None` rather than
guessing, because run directories may live anywhere and the convention is to
never infer the AOI from paths or run metadata (`base.py:164-172`).
**Open**: the CLI help text says the AOI is "auto-detected from run metadata
if omitted" (`cli.py:413`) while the code forbids inference
(`base.py:164-172`) — the help string contradicts the implementation.

### C. The composite

**Q12. How is the composite computed?**
Citation: `mal-core/src/mal_core/scoring/runner.py:108-118`.
Answer: a **weighted geometric mean** over the composite dimensions that
produced an `ok` result: `exp(Σ wᵢ·log(sᵢ) / Σ wᵢ)`. The weight sum runs over
the same dimensions that contributed a score, so skipped dimensions leave
both numerator and denominator.

**Q13. What happens to the composite when one dimension scores zero, or when
every dimension is skipped?**
Citation: `mal-core/src/mal_core/scoring/runner.py:110-118`.
Answer: the composite is computed only if **all** contributing scores are
strictly positive; if any dimension scores 0 the composite is 0.0 — one
collapsed dimension collapses the whole (geometric-mean semantics). With no
contributing dimension the composite is also 0.0.

**Q14. How does the composite handle a variable number of dimensions?**
Citation: `mal-core/src/mal_core/scoring/runner.py:112-118`;
`mal-core/src/mal_core/scoring/scorers/base.py:29-34`.
Answer: skipped dimensions are excluded from both the score and the weight
sum (`base.py:29-34` states this explicitly), so adding a scorer narrows what
a composite covers without invalidating historical composites.

**Q15. Does a dimension that fails its `min_score` still enter the composite?**
Citation: `mal-core/src/mal_core/scoring/runner.py:100-106`;
`mal-core/src/mal_core/scoring/scorers/d2_survival.py:64`.
Answer: yes — the runner puts a dimension into the composite whenever its
status is `ok`, regardless of `passed`. `passed` is only a per-dimension flag
that the CLI summary prints as `LOW` (`runner.py:157-163`); the composite is
driven by the numeric score alone.

**Q16. What is `min_score` and what is `hard_floor`, and are both actually
used?**
Citation: `mal-core/src/mal_core/scoring/scorers/base.py:70-71`;
`mal-core/src/mal_core/scoring/scorers/d2_survival.py:25-26,64`;
`mal-core/src/mal_core/scoring/scorers/d19_pool_persistence.py:49,144`;
`mal-core/src/mal_core/scoring/scorers/d20_washout_response.py:39,83`.
Answer: `min_score` is the threshold a scorer compares its own score against
to set `passed` (e.g. D2: `passed = score >= self.min_score`). `hard_floor` is
**declared but never read** anywhere in the package — a search of
`mal-core/src/mal_core/` finds it only in the class declarations. Two scorers
(D19, D20) even hard-code `passed = score >= 0.70` instead of using
`self.min_score`, though the value coincides. **Open**: the intended role of
`hard_floor` in the current architecture.

**Q17. What verdict does the composite produce, and what are the thresholds?**
Citation: `mal-core/src/mal_core/scoring/runner.py:24-31`, `runner.py:124`.
Answer: `VERDICTS = ((0.70, "VIABLE"), (0.50, "BORDERLINE"), (0.30,
"REGRESSED"))`, and below 0.30 the verdict is `COLLAPSED`. The verdict is a
label attached to the composite; it is not a gate.

### D. The gates

**Q18. What is a gate, and how does it differ from a composite dimension?**
Citation: `mal-core/src/mal_core/scoring/scorers/base.py:56-64`;
`mal-core/src/mal_core/scoring/scorers/gates.py:1-7`;
`mal-core/src/mal_core/scoring/runner.py:103-106`, `runner.py:166-169`.
Answer: a gate is a binary engineering or input invariant, `kind = "gate"`,
reported in its own `gates` section of the scorecard and **never** in the
composite. A failed gate is a visible warning that does not change the
composite number (`gates.py:3-5`). Gates also carry `weight = 0.0`
(`gates.py:44`, `:85`, `:121`, `:150`, `:201`, `:257`).

**Q19. What does each gate check?**
Citation: `mal-core/src/mal_core/scoring/scorers/gates.py:35-303`.
Answer: G6 — every state-COG band value finite and ≥ 0 (sampled to 48 files
if more than 48 exist, `gates.py:52-54`); G7 — per-seed state files
byte-identical by MD5 (`gates.py:89-113`); G10 — wall time ≤ 30 s from
`run_metadata.json` (`gates.py:116-144`); G12 — the input human grid total
within ±20 % of a census reference (`gates.py:147-194`); G14 — mobility OD
matrix rows sum to 1.0 for ≥ 99 % of rows (`gates.py:197-245`); G24 — urban
mean adult density ≤ 0.7 × rural mean (`gates.py:248-303`).

**Q20. How does a gate treat missing data — fail or skip?**
Citation: `mal-core/src/mal_core/scoring/scorers/gates.py:5-6`, `:50-51`,
`:91-95`, `:127-131`, `:158-169`, `:213-216`, `:266-273`.
Answer: gates skip rather than fail when their artifacts are absent — "missing
data is not a data-integrity failure" (`gates.py:5-6`). A skipped gate is
recorded in the `skipped` map, not in `gates`.

**Q21. Why is G6's validity rule "finite and ≥ 0" rather than "in [0, 1]"?**
Citation: `mal-core/src/mal_core/scoring/scorers/gates.py:35-40`, `:65-66`;
`mal-core/src/mal_core/abm/src/main.cpp:387-390`;
`mal-core/src/mal_core/abm/src/output_contract.cpp:5-9`.
Answer: because the state COG changed contract: under contract 4.0 the bands
are **raw per-cell adult counts** (`adult_patch_count`, `adult_cell_count`),
not normalised fractions, so values above 1 are expected and the old [0, 1]
envelope no longer applies (`gates.py:36-40`).

### E. The scorers' measurement of the run

**Q22. How are the run's artifacts discovered?**
Citation: `mal-core/src/mal_core/scoring/scorers/base.py:82-161`.
Answer: by glob over the run directory: state COGs `*_day*.tif` (excluding
names containing "transmission"), falling back to `state_day*.tif`,
`state_seed*.tif`, then `state.tif` (`base.py:89-102`); the cohort log
`*_cohort.json` (`base.py:116-125`); per-day aquatic JSONs
`*_day*_aquatic.json` (`base.py:128-139`); and the run summary JSON, searched
among `*.json` files that carry `contract_version` or `aoi_slug`
(`base.py:142-161`).

**Q23. What is the state-COG band layout the scorers read, and does it match
what the engine writes?**
Citation: `mal-core/src/mal_core/scoring/scorers/d1_habitat_occupancy.py:51-53`;
`mal-core/src/mal_core/scoring/scorers/d5_morans.py:70-71`;
`mal-core/src/mal_core/scoring/scorers/d8_coupling.py:32-34`;
`mal-core/src/mal_core/abm/src/main.cpp:387-390`.
Answer: **open and important.** The engine writes band 1 =
`adult_patch_count` (adults associated via their patch, post-dispersal) and
band 2 = `adult_cell_count` (adults at their current position) — both raw
counts (`main.cpp:387-390`). But D1 reads band 2 as "habitat cells the engine
treats as aquatic-capable habitat" (`d1_habitat_occupancy.py:3-5`, `:53`),
D5's docstring calls band 2 "host-seeking pressure" while computing on band 1
(`d5_morans.py:1-4`, `:71`), and D8 correlates band 1 against band 2 as
"density vs host-seeking pressure" (`d8_coupling.py:1-6`). Under contract 4.0
both bands are adult counts, so the habitat/suitability reading no longer
matches the artifact. The document must state what is actually measured today
and flag the mismatch.

**Q24. How does each composite dimension turn a measurement into a score?**
Citation: the per-scorer modules; representative: `d1_habitat_occupancy.py:62-66`
(band plateau + Gaussian falloff), `d2_survival.py:53-55` (Gaussian on mean
lifespan), `d4_stability.py:56-68` (mean of two sub-scores),
`d11_aquatic_structure.py:88-105` (mean of two sub-scores),
`d15_persistence.py:123-126` (geometric mean of three sub-scores),
`d21_dispersal_kernel.py:115-126` (mean of two sub-scores).
Answer: every scorer returns a number in [0, 1] with an explicit target
string, computed by either a plateau-and-falloff shape around a literature
band or a weighted sum of boolean checks. The pattern differs per scorer and
must be stated per dimension, not generalised.

**Q25. Which dimensions are measured from which artifact?**
Citation: `d1_habitat_occupancy.py:48-53` (state COG), `d2_survival.py:29-43`
(cohort log), `d3_eip.py:31-52` (cohort log), `d4_stability.py:29-48` (cohort
log), `d5_morans.py:67-71` (state COG), `d8_coupling.py:29-34` (state COG),
`d11_aquatic_structure.py:59-68` (aquatic JSONs), `d15_persistence.py:71-106`
(aquatic JSONs + state COGs), `d16_detection_coverage.py:76-87` (state COG +
occurrence table), `d21_dispersal_kernel.py:68-90` (state COGs), `d25_cases_ghana.py:135-145`
(transmission daily log + DHIMS CSV).
Answer: as listed — the cohort log carries adults, the aquatic JSONs carry
larval stages (`d11_aquatic_structure.py:1-6`), the state COGs carry spatial
patterns, and the transmission log carries incidence.

**Q26. Which dimensions do not read the run at all?**
Citation: `mal-core/src/mal_core/scoring/scorers/d19_pool_persistence.py:51-71`;
`mal-core/src/mal_core/scoring/scorers/d20_washout_response.py:41-63`.
Answer: D19 and D20 take `run_dir` and `ctx` but never use them: they
re-implement, in the scorer, the pluvial recursion and the washout fraction
of the habitat contract and check them against thresholds
(`d19_pool_persistence.py:65-71`, `d20_washout_response.py:46-63`). They
therefore test the *model contract*, not the executed run — a distinction the
document must make explicit.

**Q27. Where do the D19/D20 thresholds come from?**
Citation: `mal-core/src/mal_core/scoring/scorers/d19_pool_persistence.py:28-29`;
`d20_washout_response.py:24-25`; `mal-core/config/model_constants.yaml:29-30`,
`:38-39`; `mal-core/src/mal_core/habitat/config.py` (CONFIG loader).
Answer: from the shared configuration, not from literals: `pluvial.rain_scale_mm`
= 2.5 mm, `pluvial.dry_memory_days` = 5.0 d, `aquatic_stress.wash_threshold_mm`
= 40.0 mm, `aquatic_stress.wash_fraction_max` = 0.60. The 0.05 activation
floor and the 30 mm pulse used by D19 are literals inside the scorer
(`d19_pool_persistence.py:81`).

**Q28. How is the AOI never inferred but external datasets still resolved?**
Citation: `mal-core/src/mal_core/scoring/scorers/base.py:204-223`;
`d16_detection_coverage.py:47-50`, `:69-75`; `d25_cases_ghana.py:39-52`;
`gates.py:162-164`, `:263-265`.
Answer: the AOI slug is explicit; the *path* to that AOI's data is resolved by
convention — repository-relative glob patterns with `{aoi}` substituted, first
existing hit wins (`base.py:204-223`), e.g. `data/{aoi}/{aoi}_occurrence.txt`.
D25 instead downloads a pinned DHIMS-II CSV (URL + SHA-256) into
`data/ghana/scoring/` if absent (`d25_cases_ghana.py:39-77`).

**Q29. How is the pixel-to-lon/lat transform recovered, and why is it
non-trivial?**
Citation: `mal-core/src/mal_core/scoring/scorers/base.py:175-201`.
Answer: the engine's state COGs historically carried a garbled affine (GDAL
order fed to an `Affine` constructor). The helper trusts the GeoTIFF
transform when the grid is north-up (`b == d == 0`), otherwise it falls back
to the `transform` field of the run summary JSON (`base.py:175-201`). Two
dimensions (D16, D21) depend on it and skip if no usable transform exists
(`d16_detection_coverage.py:79-81`, `d21_dispersal_kernel.py:71-73`).

**Q30. What is the seeding origin used by the dispersal dimension?**
Citation: `mal-core/src/mal_core/scoring/scorers/d21_dispersal_kernel.py:83-92`.
Answer: the centroid of the occupied cells of the **first** snapshot is taken
as the origin, and displacement is measured at the nearest available snapshot
at or before day 30 (`d21_dispersal_kernel.py:83-99`). It is a population
displacement distribution, not an individual trajectory.

**Q31. What counts as "skipped", and what happens to a scorer that raises?**
Citation: `mal-core/src/mal_core/scoring/scorers/base.py:25-53`;
`mal-core/src/mal_core/scoring/runner.py:95-102`.
Answer: `ScorerResult.skipped(reason)` marks the result with status
`"skipped"`, score 0.0 and the reason in `diagnostics.skipped_reason`
(`base.py:44-53`). A scorer that raises an exception is caught by the runner
and converted into a skipped entry — "a broken scorer must not sink the run"
(`runner.py:97-98`). Skipped dimensions are excluded from the composite
(`base.py:29-34`).

**Q32. When is the EIP dimension skipped, and why?**
Citation: `mal-core/src/mal_core/scoring/scorers/d3_eip.py:44-50`.
Answer: when `eip_frac` is constant across the cohort log — the degenerate
case of a run without the transmission module — the dimension reports skipped
rather than punishing the run (`d3_eip.py:44-50`).

### F. The LLM judge

**Q33. What does the LLM component do?**
Citation: `mal-core/src/mal_core/scoring/llm_scorer.py:74-95`, `:254-348`;
`mal-core/src/mal_core/scoring/prompts/llm_verdict.md:1-13`.
Answer: it is a qualitative judge. The finished scorecard JSON is sent to a
model on OpenRouter with a bundled system prompt, and the reply is validated
against a pydantic schema `Verdict` with fields `verdict`
(viable/borderline/regressed/collapsed), `composite_estimate`, `concerns`,
`recommendations`, `literature_grounding` (`llm_scorer.py:74-95`).

**Q34. What is the LLM component NOT allowed to do — can it gate a run?**
Citation: `mal-core/src/mal_core/scoring/runner.py:135-142`;
`mal-core/src/mal_core/scoring/llm_scorer.py:222-246`;
`docs/specs/scoring/spec.md:164-168`.
Answer: it cannot gate anything. The runner calls it after the composite and
the verdict are already computed, and only attaches its result under the
optional key `verdict_llm`; if the call fails, the module returns a fallback
dict and the runner omits the key entirely (`runner.py:135-142`). The
deterministic composite and verdict are unaffected by the LLM in every path.
The retired spec states the same intent as INV-12
(`docs/specs/scoring/spec.md:164-168`); the code confirms it.

**Q35. How does the LLM component behave when it cannot be used?**
Citation: `mal-core/src/mal_core/scoring/llm_scorer.py:126-166`, `:222-246`,
`:298-299`, `:350-359`.
Answer: three fallback paths — no API key (environment or `.env` file walked
up from the package directory), a Pydantic validation failure, or any
transport/other exception — all return `deterministic_fallback` with
`verdict = "unknown"` and a human-readable `fallback` reason
(`llm_scorer.py:239-246`). No exception escapes to the caller.

**Q36. How is the LLM component kept cheap and reproducible?**
Citation: `mal-core/src/mal_core/scoring/llm_scorer.py:103-123`, `:169-214`,
`:286-294`, `:36-49`.
Answer: the request payload is hashed (report + model id) and the verdict is
cached on disk under `.cache/llm_verdicts/<sha256>.json`; a cache hit returns
immediately and is flagged `cache_hit: True`. The request is sent at
temperature 0 with a per-request timeout (default 180 s), default model
`minimax/minimax-m3`, base URL `https://openrouter.ai/api/v1`
(`llm_scorer.py:36-49`, `:103-123`).

**Q37. Is the LLM prompt consistent with the current system?**
Citation: `mal-core/src/mal_core/scoring/prompts/llm_verdict.md:1-13`,
`:71-79`; `mal-core/src/mal_core/abm/src/main.cpp:387-390`;
`mal-core/src/mal_core/scoring/registry.py:53-67`.
Answer: **open.** The prompt still describes "the 10-dimension deterministic
scorecard" (`prompts/llm_verdict.md:3-4`) while the registry now holds
thirteen composite dimensions, and its "Density band means" table describes
band 1 as "Larval habitat (1)" saturated at 1.0 and band 2 as "Adult density
(2)" normalised 0–0.5 (`prompts/llm_verdict.md:71-79`), which contradicts
contract 4.0's raw adult counts (`main.cpp:387-390`). The judge is therefore
prompted against a stale description of the scorecard it is judging.

### G. What is NOT implemented (declaration of absences)

**Q38. Is there a pytest calibration harness in the tree?**
Citation: `mal-core/src/mal_core/scoring/scorers/base.py:1-6`;
`docs/specs/scoring/spec.md:54-63`, `:86-88`; directory listing — the path
`mal-core/src/mal_core/abm/tests/calibration/` **does not exist**; the unit
tests live in `mal-core/tests/test_scoring_state.py`,
`test_scoring_cohort.py`, `test_scoring_pools.py`, `test_scoring_llm.py`,
`test_feedback.py`.
Answer: **no.** The harness (with its `thresholds.yaml`, diff/best trackers
and pytest tiers) was deleted; the base module states "the old pytest
calibration harness and its duplicated scorers were deleted"
(`base.py:3-5`), and the retired spec says the same
(`docs/specs/scoring/spec.md:61-63`). There is no `thresholds.yaml` anywhere in
the working tree and no `calibration/` directory. The threshold values that
used to live there are now inlined in each scorer module and, where they
derive from the model, read from `model_constants.yaml`.

**Q39. Which declared attributes and code paths are dormant?**
Citation: `mal-core/src/mal_core/scoring/scorers/base.py:66-76`;
`mal-core/src/mal_core/scoring/scorers/gates.py:46`;
`mal-core/src/mal_core/scoring/llm_scorer.py:257-285`.
Answer: three declarations are inert — the base `weight` attribute (never
read by the runner, see Q8), `hard_floor` (declared by eleven scorers, never
read), and `aoi_generalizable` (declared by all six gates, never read
anywhere). Also, the `score_with_llm` docstring still describes a
`langchain_openai` call with `with_structured_output` (`llm_scorer.py:266-269`,
`:277`) while the implementation posts directly with `requests` and parses
the JSON reply (`llm_scorer.py:301-341`).

**Q40. Is the scorecard a decision gate for the pipeline?**
Citation: `mal-core/src/mal_core/scoring/runner.py:24-31`, `:110-118`;
`mal-core/src/mal_core/cli.py:409-463`.
Answer: no. The `score` command computes and writes the scorecard and prints
a summary; it does not fail the run, exit non-zero, or block anything
downstream. The verdict label is a human-readable summary of the number, and
the only mechanical consequence anywhere is the LLM verdict's non-gating
status (Q34). **Open**: whether some external process is meant to consume
the verdict as a promotion criterion — the retired spec claims the composite
"gates parameter changes" (`docs/specs/scoring/spec.md:48-50`) but no code
in the tree enforces that.

**Q41. What is the feedback step, and is it part of the scoring stage?**
Citation: `mal-core/src/mal_core/scoring/feedback.py:16-53`;
`mal-core/src/mal_core/cli.py:841-861`.
Answer: `get_feedback(scorecard, baseline)` renders a Markdown report:
composite and verdict, failed gates, skipped scorers, the three weakest
dimensions, and — with a baseline — the composite delta and the dimensions
that regressed by more than 0.05 (`feedback.py:32-46`). The `feedback` CLI
command re-runs scoring on the run directory and on an optional baseline
directory and prints the report (`cli.py:856-861`).

**Q42. What are the launch-and-measure commands, and why do they exist?**
Citation: `mal-core/src/mal_core/cli.py:466-556`, `cli.py:559-639`.
Answer: two commands run a *simulation* and then score it with one manual
dimension enabled: `validate-detections` seeds mosquitoes at the AOI's real
detection points and then scores D16 (`cli.py:485-491`, `:551-555`);
`validate-cases` runs a multi-year, fully infected, uniformly seeded run with
transmission enabled and then scores D25 (`cli.py:575-581`, `:633-638`).
They are the only entry points that produce a run before scoring.

### H. Evidence and provenance

**Q43. How is each dimension's literature anchor recorded?**
Citation: `mal-core/src/mal_core/scoring/registry.py:7-18`;
per-scorer docstrings, e.g. `d1_habitat_occupancy.py:8-20`,
`d2_survival.py:6-8`, `d3_eip.py:9-10`, `d11_aquatic_structure.py:8-15`,
`d16_detection_coverage.py:1-22`, `d21_dispersal_kernel.py:8-19`,
`d25_cases_ghana.py:1-24`.
Answer: in the registry module docstring (one anchor line per dimension with
author and year, pointing into `papers/`) and in each scorer's own docstring,
which states the reference value and the source. The bands themselves are
literals in the scorer modules (`OCC_BAND`, `LARVA_BAND`, `P50_BAND`, …).

**Q44. What is the provenance tier of each number in the stage?**
Citation: `mal-core/src/mal_core/scoring/scorers/d19_pool_persistence.py:28-29`;
`d20_washout_response.py:24-25`; `mal-core/config/model_constants.yaml:29-30`,
`:38-39`; `mal-core/src/mal_core/scoring/scorers/base.py:21-22`;
`mal-core/config/model_constants.yaml:137`.
Answer: mixed, and the document must tier them explicitly — model-definition
constants read from `model_constants.yaml` (rain scale, dry memory, washout
threshold and cap, the NoData sentinel −9999 read via
`mal_core.habitat.config.CONFIG["ingest"]["nodata_sentinel"]`, `base.py:21-22`);
literature-anchored bands with the source named in the docstring; and
engineering literals written directly in the scorer (e.g. the 0.05 activation
floor in D19, the 30 mm pulse, the 48-file sampling cap in G6, the 30 s
performance target in G10).

**Q45. What is the AUC helper used for, and is it used?**
Citation: `mal-core/src/mal_core/scoring/scorers/base.py:257-285`;
`mal-core/src/mal_core/scoring/registry.py:53-100`.
Answer: `auc_rank` is a sklearn-free Mann–Whitney AUC helper, and
`load_occurrence_spots` reads a deduplicated GBIF-style occurrence table
(`base.py:233-254`). Neither is used by any of the thirteen current
dimensions — D16 uses radius coverage instead of an AUC
(`d16_detection_coverage.py:119-143`). They are leftovers from the retired
occurrence-AUC scorers. **Open** (part c).

---

## (b) Done-checklist

The `scoring` conceptual document is done when:

- [ ] The purpose of the stage is stated first, with the question it answers
      and an explicit out-of-scope list (Q1, Q2).
- [ ] The scorecard is defined as an object: its input (one run directory) and
      its output (`scorecard.json` inside that directory), with the full key
      list and the fact that it is written inside the run dir (Q3).
- [ ] The registry is explained as code-built, not a data file, and the three
      steps to add a scorer (module, registration, weight) are stated (Q5, Q6).
- [ ] A table states every scorer's identity, what it measures, which artifact
      it reads, its units, its target band, its `min_score`, and its weight —
      all thirteen composite dimensions and all six gates (Q6, Q19, Q24, Q25).
- [ ] The composite and the gates are distinguished **where the composite is
      first used**: the composite is a weighted geometric mean over `ok`
      composite dimensions; gates are binary, reported apart, and never enter
      the composite (Q12, Q13, Q18).
- [ ] The variable-dimension-count behaviour is stated: skipped dimensions
      leave both numerator and weight sum, so adding a scorer narrows
      coverage without invalidating history (Q14).
- [ ] The failure semantics are stated: one zero dimension collapses the
      composite, a failing-but-nonzero dimension still contributes its score,
      and a skipped dimension contributes nothing (Q13, Q15, Q31).
- [ ] The verdict labels and their thresholds are stated, and the verdict is
      described as a label on the composite, not a gate (Q17).
- [ ] The LLM scorer's role is stated (qualitative judge over the finished
      scorecard, cached, temperature 0, fallback on any failure) **and** its
      non-gating status is stated explicitly: it can only add an optional
      `verdict_llm` key and can never change the composite or the verdict
      (Q33, Q34, Q35, Q36).
- [ ] The state-COG band semantics as the scorers read them are stated, with
      the mismatch against the contract-4.0 artifact flagged rather than
      silently reproduced (Q23).
- [ ] The declaration of absences lists: no pytest calibration harness in the
      tree (no `calibration/` directory, no `thresholds.yaml`), the dormant
      attributes (`weight`, `hard_floor`, `aoi_generalizable`), the unused
      AUC helper, the D19/D20 dimensions that score the model contract rather
      than the run, and the stale LLM prompt (Q38, Q39, Q26, Q45, Q37).
- [ ] The absence of any mechanical gating of the pipeline by the composite is
      stated (Q40).
- [ ] The feedback step and the two launch-and-measure commands are described
      (Q41, Q42).
- [ ] Every parameter table carries a provenance tier (model definition /
      literature-anchored / engineering prior / scenario default) and every
      number is either generated from `model_constants.yaml` or written in the
      document with its tier stated (Q44).
- [ ] Every claim about behaviour resolves to a `path:line` a reviewer can
      open, and the document states where the code does not answer the
      question (the stance note's S10).

---

## (c) Open questions

1. **Band semantics (Q23).** D1, D5 and D8 describe bands as
   habitat/suitability and adult density, but the engine now writes raw adult
   counts on both bands (contract 4.0). Are these three dimensions measuring
   something the document can honestly describe today, or are they measuring
   a retired contract? A reviewer needs to know what each of them actually
   computes on a current run.
2. **`hard_floor` (Q16).** Declared by eleven scorers, never read. Is it
   meant to be a hard rejection threshold (a dimension below the floor should
   invalidate the run), a reporting band, or is it dead weight from the
   deleted harness?
3. **Class `weight` versus `COMPOSITE_WEIGHTS` (Q8).** Two sources of truth
   that currently agree. Which one is canonical, and what should happen when
   they disagree?
4. **The `--aoi` help text (Q11).** `cli.py:413` says the AOI is
   "auto-detected from run metadata if omitted"; `base.py:164-172` forbids
   inference. One of the two is wrong.
5. **The composite as a promotion criterion (Q40).** The retired spec says the
   composite gates parameter changes; nothing in the tree enforces it. Is
   there an intended consumer outside the code, and should the document
   describe one?
6. **The stale LLM prompt (Q37).** It tells the judge about ten dimensions
   and pre-contract band semantics. Should the judge be documented as
   operating on a stale description of the scorecard, or is the prompt an
   in-flight fix?
7. **Unused AUC helper and occurrence loader (Q45).** `auc_rank` and
   `load_occurrence_spots` are used only by `validate-detections`'s CLI
   seeding path, not by any dimension. Are they part of the stage's contract
   or leftovers to be removed?
8. **D19/D20 identity (Q26).** Two of the thirteen "composite dimensions" do
   not inspect the run at all; they test the habitat contract in isolation.
   Should they be described as contract tests rather than as dimensions of
   this run's scorecard — and if so, does their presence in the weighted
   composite distort what the composite means?
9. **Verbatim `min_score` in D19/D20.** These two scorers hard-code
   `passed = score >= 0.70` instead of using `self.min_score` (which is also
   0.70). Cosmetic, but it breaks the uniform pattern; worth a note so a
   reader does not infer two different thresholds.
