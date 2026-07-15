#!/usr/bin/env bash
# manage_jobs.sh — submit, monitor, and manage MalariaSentinel ABM jobs on CESGA
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=cesga_config.sh
source "$SCRIPT_DIR/cesga_config.sh"

log() { printf '[%s] %s\n' "$(date '+%H:%M:%S')" "$*"; }

# --- Commands ----------------------------------------------------------------

cmd_submit() {
  local seed="${ABM_SEED:-1}"
  local start_month="${ABM_START_MONTH:-1}"
  local start_year="${ABM_START_YEAR:-2024}"
  local num_months="${ABM_NUM_MONTHS:-24}"

  log "Submitting ABM run: seed=$seed months=$num_months from $start_year-$start_month"
  sbatch \
    --job-name="malaria-abm-s${seed}" \
    --export="ABM_SEED=${seed},ABM_START_MONTH=${start_month},ABM_START_YEAR=${start_year},ABM_NUM_MONTHS=${num_months}" \
    "$SCRIPT_DIR/run_abm.sh"
}

cmd_status() {
  log "Active MalariaSentinel jobs:"
  squeue -u "$CESGA_USER" -o "%.10i %.9P %.50j %.8T %.10M %.6D %R" 2>/dev/null || echo "No jobs found."
}

cmd_cancel() {
  local job_id="${1:-}"
  if [[ -z "$job_id" ]]; then
    log "Usage: $(basename "$0") cancel <JOB_ID>"
    exit 1
  fi
  log "Cancelling job $job_id …"
  scancel "$job_id"
  log "Done."
}

cmd_efficiency() {
  log "Completed MalariaSentinel jobs (last 30):"
  sacct -u "$CESGA_USER" \
    --name="malaria-abm*" \
    --format="JobID,JobName,State,Elapsed,MaxRSS,AllocCPUS,MaxVMSize" \
    --starttime="$(date -d '30 days ago' '+%Y-%m-%d' 2>/dev/null || date -v-30d '+%Y-%m-%d')" \
    2>/dev/null || echo "No completed jobs found."
}

cmd_submit_array() {
  local start_seed="${1:-1}"
  local count="${2:-10}"
  local start_month="${ABM_START_MONTH:-1}"
  local start_year="${ABM_START_YEAR:-2024}"
  local num_months="${ABM_NUM_MONTHS:-24}"

  local end_seed=$(( start_seed + count - 1 ))
  log "Submitting array: seeds $start_seed..$end_seed ($count jobs)"

  local script="$SCRIPT_DIR/run_abm.sh"
  local tmp_script
  tmp_script=$(mktemp)
  cp "$script" "$tmp_script"

  # Replace the sequential loop with a single-month runner for array jobs
  sed -i.bak 's/^#SBATCH -J .*/#SBATCH -J malaria-abm-array/' "$tmp_script"

  sbatch \
    --job-name="malaria-abm-array" \
    --array="${start_seed}-${end_seed}" \
    --export="ABM_START_MONTH=${start_month},ABM_START_YEAR=${start_year},ABM_NUM_MONTHS=${num_months}" \
    "$tmp_script"

  rm -f "$tmp_script" "${tmp_script}.bak"
  log "Array submitted: ${start_seed}-${end_seed}"
}

cmd_logs() {
  local job_id="${1:-}"
  if [[ -z "$job_id" ]]; then
    log "Usage: $(basename "$0") logs <JOB_ID>"
    exit 1
  fi
  local log_dir="${LOGS_DIR:-${STORE}/malaria-sentinel/logs}"
  echo "--- stdout ---"
  cat "${log_dir}/malaria-abm-${job_id}.o" 2>/dev/null || echo "(not found)"
  echo ""
  echo "--- stderr ---"
  cat "${log_dir}/malaria-abm-${job_id}.e" 2>/dev/null || echo "(not found)"
}

cmd_help() {
  cat <<EOF
MalariaSentinel ABM — CESGA job management

Usage: $(basename "$0") <command> [args]

Commands:
  submit              Submit a single ABM run (uses env vars / defaults)
  status              Show running MalariaSentinel jobs
  cancel <JOB_ID>     Cancel a job
  efficiency          Show efficiency stats for completed jobs
  submit_array S N    Submit array of N jobs starting at seed S
  logs <JOB_ID>       Show stdout/stderr for a job
  help                Show this help

Environment overrides (set before calling, or via --export on sbatch):
  ABM_SEED            Starting seed (default: 1)
  ABM_START_MONTH     Start month  (default: 1)
  ABM_START_YEAR      Start year   (default: 2024)
  ABM_NUM_MONTHS      Months to run (default: 24)
EOF
}

# --- Dispatch ----------------------------------------------------------------
case "${1:-help}" in
  submit)       shift; cmd_submit "$@";;
  status)       shift; cmd_status "$@";;
  cancel)       shift; cmd_cancel "$@";;
  efficiency)   shift; cmd_efficiency "$@";;
  submit_array) shift; cmd_submit_array "$@";;
  logs)         shift; cmd_logs "$@";;
  help|-h|--help) cmd_help;;
  *) echo "Unknown command: $1"; cmd_help; exit 1;;
esac
