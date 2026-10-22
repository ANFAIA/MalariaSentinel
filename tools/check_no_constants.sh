#!/bin/sh
# Anti-hardcode check (plan constants-yaml test 8 / §8 / §7 patterns):
# after the migration NO migrated constant may appear as a literal in the
# engine or the model modules — model_constants.yaml is the single source.
# Review-a3 round0 (item INFRA-7): pattern list extended (0.08f/0.05f
# egg/pupa, 111320 geodesy, -9999 outside config, EIP 16/110, 0.76 indoor,
# 0.2 urbanicity) and scan paths widened (scoring + ingest py).
# Usage: tools/check_no_constants.sh [repo-root] ; exit 0 = clean, 1 = hits.
set -eu
ROOT="${1:-$(dirname "$0")/..}"
cd "$ROOT"

fail=0

# forbidden identifiers outside the loader/tests. The trailing filter
# drops pure comment lines (^[^:]*:[0-9]+: *//) so doc mentions don't
# count, but any identifier used in CODE still fails.
for name in K_REF_GHANA HOST_SEEKING_SCALE_M HOST_SEEKING_RADIUS_M \
            kHabitatCandidateMin kActivationMin URBAN_PERSISTENT_BETA \
            RAIN_POOLS_BUIT_DAMAGE RAIN_SCALE_MM DRY_MEMORY_DAYS \
            AQUATIC_DESICCATION_DAILY_RATE AQUATIC_DESICCATION_GRACE_DAYS \
            AQUATIC_RAIN_WASH_MM AQUATIC_WASHOUT_FRACTION_MAX \
            LARVA_DESICCATION_GRACE_DAYS kSentinelSpecies \
            K_REF_DAILY_PER_KM2; do
    hits=$(grep -rn --include='*.cc' --include='*.hpp' --include='*.py' \
        -e "[^_a-zA-Z0-9]$name[^_a-zA-Z0-9]" -e "^$name[^_a-zA-Z0-9]" \
        -e "[^_a-zA-Z0-9]$name\$" -e "^$name\$" mal-core/src/mal_core 2>/dev/null \
        | grep -v "config.cc\|config.hpp\|config_dump.cpp\|test_config.cpp\|__pycache__" \
        | grep -vE ':[0-9]+:( *|\* *|/// *)//' \
        | grep -vE ':[0-9]+: *(\*|///|#|"|"| без )' || true)
    # py quotes in strings still count unless in docstrings — keep simple:
    [ -n "$hits" ] && { echo "HIT [$name]:"; echo "$hits" | head -4; fail=1; }
done

# forbidden numeric literals — engine core sources (review-a3 INFRA-7:
# includes the egg/pupa pair and the removed geodesy constant)
# Numeric literals for the migrated constants. Allowlists with reasons:
#   - transmission.hpp focus_threshold 0.01f / mobility 0.01f: different
#     axes (transmission focus, schedule tolerance) — allowed.
#   - species_params.cpp 0.08f/0.05f/0.02f...: the behavioural v2 block
#     is in-CODE until plan-v2 paso 12 — allowed (tracked).
#   - 50.0f step_size_m (host seeking) is an unrelated 50 — allowed; the
#     k_ref value lives in the YAML only.
for lit in '2\.5f' '0\.72f' '0\.2f' '1\.0e-6' '111320' '16\.0f' '110\.0f'; do
    hits=$(grep -rn --include='*.cpp' --include='*.hpp' -e "$lit" \
        mal-core/src/mal_core/abm/src mal-core/src/mal_core/abm/include 2>/dev/null \
        | grep -v "config.cc\|config.hpp\|config_dump.cpp\|test_config.cpp" \
        | grep -vE 'transmission\.(hpp|cpp)|mobility_schedule|species_params\.cpp|host_seeking|dispersal\.hpp|\*none\*' || true)
    [ -n "$hits" ] && { echo "HIT [$lit]:"; echo "$hits" | head -4; fail=1; }
done
# kRef consts (50.0f k_ref; egg/pupa pair) — same allowlist for the v2
# behaviour block
for lit in '50\.0f' '0\.08f' '0\.05f'; do
    hits=$(grep -rn --include='*.cpp' --include='*.hpp' -e "$lit" \
        mal-core/src/mal_core/abm/src/coordinator.cpp \
        mal-core/src/mal_core/abm/src/habitat_engine.cpp \
        mal-core/src/mal_core/abm/src/aquatic_cohort_bank.cpp \
        mal-core/src/mal_core/abm/src/climate.cpp 2>/dev/null || true)
    [ -n "$hits" ] && { echo "HIT [$lit]:"; echo "$hits" | head -4; fail=1; }
done

# py side: scored/ingest literals for the migrated constants
for lit in '1\.0e-6' '-9999' '9999'; do
    hits=$(grep -rn --include='*.py' -e "$lit" \
        mal-core/src/mal_core/scoring mal-core/src/mal_core/ingest 2>/dev/null \
        | grep -v "__pycache__" | grep -v "^[^:]*:[0-9]*: *#" || true)
    [ -n "$hits" ] && { echo "PY-HIT [$lit]:"; echo "$hits" | head -4; fail=1; }
done

# seeds outside the yaml
hits=$(grep -rn --include='*.cpp' -e '789' -e '\b42\b' -e '\b123\b' \
    mal-core/src/mal_core/abm/src 2>/dev/null \
    | grep -v "config.cc\|config_dump.cpp" || true)
[ -n "$hits" ] && { echo "HIT [seeds outside rng]:"; echo "$hits" | head -4; fail=1; }

# task-07: model literals moved to the YAML must not reappear in the origin
# files. Each pattern targets the exact field/constant that now has a key.
check_absent() {
    _file="$1"; _pattern="$2"; _label="$3"
    _hits=$(grep -nE "$_pattern" "$_file" 2>/dev/null || true)
    [ -n "$_hits" ] && { echo "HIT [$_label]:"; echo "$_hits" | head -4; fail=1; }
    return 0
}
T07_ABM=mal-core/src/mal_core/abm
check_absent "$T07_ABM/include/mal_abm_fast/transmission.hpp" \
    '(beta_hv|beta_vh|human_incubation_days|human_infectious_days|immunity_duration_days|initial_human_prevalence|initial_vector_infected_frac)[[:space:]]*=[[:space:]]*[0-9]|eip_base_temp|eip_threshold_gd' \
    'transmission literals'
check_absent "$T07_ABM/include/mal_abm_fast/birth_rate.hpp" \
    'EFD_(AFD|T0|TM|TOPT)' 'EFD thermal literals'
check_absent "$T07_ABM/include/mal_abm_fast/thermal_responses.hpp" \
    '(EGG|LARVA|PUPA)_(TL|TH|A)[[:space:]]*=' 'stage thermal literals'
check_absent "$T07_ABM/include/mal_abm_fast/gonotrophic_cycle.hpp" \
    '(cycle_duration_days|first_cycle_days|feeding_success_rate|egg_batch_mean|egg_batch_n|egg_batch_min|egg_batch_max|resting_duration_days)[[:space:]]*=[[:space:]]*[0-9]' \
    'gonotrophic literals'
check_absent "$T07_ABM/src/mosquito_submodel.cpp" \
    '2000\.0|500\.0f|50\.0f|current_hour_ >= 18|current_hour_ < 6' \
    'movement kernel literals'
check_absent "$T07_ABM/src/host_seeking.cpp" \
    'detect_host_cell\([^;]*2000\.0|1\.0f \+ 0\.2f' 'host-seeking kernel literals'
check_absent "$T07_ABM/src/oviposition_seeking.cpp" \
    '0\.3f' 'oviposition min_attraction literal'
check_absent "$T07_ABM/src/host_landscape.cpp" \
    'indoor_fraction \* 0\.8f|indoor_fraction \* 0\.8' \
    'residential fraction literal'
check_absent "$T07_ABM/src/engine.cpp" \
    'set_current_hour\([0-9]' 'engine flight hour literal'
hits=$(grep -nE -- '-9999' \
    mal-commonlib/src/mal_commonlib/data/loaders/dynamic_world.py \
    mal-core/src/mal_core/prediction/predictor.py 2>/dev/null || true)
[ -n "$hits" ] && { echo "HIT [nodata literal in origin py]:"; echo "$hits" | head -4; fail=1; }

[ "$fail" -eq 0 ] && echo "check_no_constants: OK" && exit 0
echo "check_no_constants: FAILED — migrate the hits to mal-core/config/model_constants.yaml"
exit 1
