#!/usr/bin/env bash
# hetzner-run — high-level job wrappers (sim-run, train)

# _resolve_repo_name <local-repo-path>
#   Strips trailing slash and returns the basename.
_resolve_repo_name() {
  local p="${1%/}"
  basename "$p"
}

# _ensure_local_path <label> <path>
#   Die with a friendly error if the path doesn't exist locally.
_ensure_local_path() {
  local label="$1" p="$2"
  [[ -e "$p" ]] || die "$label path does not exist: $p"
}

# sim_run <name> <repo> <data> <cmd> <pull-to> <keep-vm>
sim_run() {
  local name="$1" repo="$2" data="$3" cmd="$4" pull_to="$5" keep_vm="$6"

  if [[ "${HETZNER_RUN_DRY_RUN:-0}" == "1" ]]; then
    _ensure_local_path "repo" "$repo"
    _ensure_local_path "data" "$data"
  else
    _ensure_local_path "repo" "$repo"
    _ensure_local_path "data" "$data"
  fi

  local repo_name
  repo_name="$(_resolve_repo_name "$repo")"
  local remote_repo="/work/code/$repo_name"
  local remote_data="/work/data"
  local remote_runs="/work/runs"

  # Cost estimate: assume HETZNER_RUN_ESTIMATE_HOURS worst case. The user
  # can pass --yes to skip the prompt.
  local estimate_rate estimate_hours estimate_cost
  estimate_rate="$(price_for_type ccx33 || echo 0.030)"
  estimate_hours="${HETZNER_RUN_ESTIMATE_HOURS:-1}"
  estimate_cost="$(awk -v r="$estimate_rate" -v h="$estimate_hours" 'BEGIN { printf "%.4f", r*h }')"

  if [[ "${HETZNER_RUN_DRY_RUN:-0}" == "1" ]]; then
    log_info "[dry-run] sim-run plan:"
    log_info "  name=$name"
    log_info "  repo: $repo -> $remote_repo"
    log_info "  data: $data -> $remote_data"
    log_info "  cmd:  $cmd"
    log_info "  pull /work/runs -> $pull_to"
    if [[ "$keep_vm" == "1" ]]; then
      log_info "  end:  stop (--keep-vm)"
    else
      log_info "  end:  destroy"
    fi
    log_info "  estimated cost (ccx33 × $estimate_hours h): $(format_eur "$estimate_cost")"
    return 0
  fi

  log_info "estimated cost: $(format_eur "$estimate_cost") (ccx33 × ${estimate_hours}h)"
  if [[ "${HETZNER_RUN_ASSUME_YES:-0}" != "1" ]]; then
    if [[ -t 0 ]]; then
      printf 'Proceed? [y/N] ' >&2
      local ans
      read -r ans
      [[ "$ans" == "y" || "$ans" == "Y" ]] || { log_info "aborted"; return 2; }
    else
      log_error "non-interactive shell: pass --yes to confirm or set HETZNER_RUN_ASSUME_YES=1"
      return 2
    fi
  fi

  start_vm "$name" "ccx33" "ubuntu-24.04" "fsn1" \
    "$(resolve_ssh_key_name "")"

  push_path "$name" "$repo" "$remote_repo"
  push_path "$name" "$data/" "$remote_data/"

  exec_remote "$name" "bash -lc $(printf %q "$cmd")"

  pull_path "$name" "$remote_runs/" "$pull_to/"

  if [[ "$keep_vm" == "1" ]]; then
    stop_vm "$name"
  else
    destroy_vm "$name"
  fi

  log_info "sim-run done — results: $pull_to"
}

# train_run <name> <repo> <data> <config> <pull-to> <keep-vm>
#   Mirrors sim_run, but the default command runs the training script with
#   the uploaded config.
train_run() {
  local name="$1" repo="$2" data="$3" config="$4" pull_to="$5" keep_vm="$6"

  _ensure_local_path "repo" "$repo"
  _ensure_local_path "data" "$data"
  if [[ -n "$config" ]]; then
    _ensure_local_path "config" "$config"
  fi

  local repo_name
  repo_name="$(_resolve_repo_name "$repo")"
  local remote_repo="/work/code/$repo_name"
  local remote_data="/work/data"
  local remote_runs="/work/runs"
  local remote_config=""
  local config_basename=""
  if [[ -n "$config" ]]; then
    config_basename="$(basename "$config")"
    remote_config="/work/code/$repo_name/$config_basename"
  fi

  local cmd
  if [[ -n "$remote_config" ]]; then
    cmd="cd $remote_repo && uv sync && uv run python scripts/05_train.py --config $remote_config"
  else
    cmd="cd $remote_repo && uv sync && uv run python scripts/05_train.py"
  fi

  if [[ "${HETZNER_RUN_DRY_RUN:-0}" == "1" ]]; then
    log_info "[dry-run] train plan:"
    log_info "  name=$name"
    log_info "  repo: $repo -> $remote_repo"
    log_info "  data: $data -> $remote_data"
    [[ -n "$config" ]] && log_info "  config: $config -> $remote_config"
    log_info "  cmd:  $cmd"
    log_info "  pull /work/runs -> $pull_to"
    if [[ "$keep_vm" == "1" ]]; then
      log_info "  end:  stop (--keep-vm)"
    else
      log_info "  end:  destroy"
    fi
    return 0
  fi

  start_vm "$name" "ccx33" "ubuntu-24.04" "fsn1" \
    "$(resolve_ssh_key_name "")"

  push_path "$name" "$repo" "$remote_repo"
  push_path "$name" "$data/" "$remote_data/"
  if [[ -n "$config" ]]; then
    push_path "$name" "$config" "$remote_config"
  fi

  exec_remote "$name" "bash -lc $(printf %q "$cmd")"

  pull_path "$name" "$remote_runs/" "$pull_to/"

  if [[ "$keep_vm" == "1" ]]; then
    stop_vm "$name"
  else
    destroy_vm "$name"
  fi

  log_info "train done — results: $pull_to"
}
