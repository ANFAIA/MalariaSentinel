#!/usr/bin/env bash
# hetzner-run — high-level job wrappers (sim-run, train)

# _resolve_repo_name <local-repo-path>
#   Strips trailing slash and returns the basename.
_resolve_repo_name() {
  local p="${1%/}"
  basename "$p"
}

# _resolve_repo_url <repo-path>
#   Returns the git remote URL (origin) of a local checkout, or dies.
_resolve_repo_url() {
  local url
  url="$(git -C "$1" config --get remote.origin.url 2>/dev/null || true)"
  if [[ -z "$url" ]]; then
    die "no git remote 'origin' for repo: $1 (pass --repo-url to override)"
  fi
  printf '%s\n' "$url"
}

# _resolve_branch <repo-path>
#   Returns the current branch of a local checkout (default: main).
_resolve_branch() {
  local b
  b="$(git -C "$1" rev-parse --abbrev-ref HEAD 2>/dev/null || true)"
  [[ -n "$b" ]] || b="main"
  printf '%s\n' "$b"
}

# _ensure_local_path <label> <path>
#   Die with a friendly error if the path doesn't exist locally.
_ensure_local_path() {
  local label="$1" p="$2"
  [[ -e "$p" ]] || die "$label path does not exist: $p"
}

# _build_sim_cmd <repo_name> <aoi> <year> <month> <days> <seed> <n_rollouts> <snapshot_every> <run_name> <gif> <data_ready> <verify_env_bands>
#   Builds the remote command that runs the ABM (and, when the AOI data is
#   not already present, the download+ingest prep). Uses the lightweight
#   uv profile so torch/fastapi are not installed on the VM.
#   verify_env_bands=1: inject a 1-day ABM probe that FAILS unless the
#   binary logs that the env NC static bands (twi / k_capacity_mult /
#   catchment_ratio) were loaded — guards against GDAL driver versions
#   that do not expose plain 2-D NetCDF variables (the netCDF-C fallback
#   in env_reader must also have worked).
_build_sim_cmd() {
  local repo_name="$1" aoi="$2" year="$3" month="$4" days="$5" seed="$6"
  local n_rollouts="$7" snapshot_every="$8" run_name="$9" gif="${10}" data_ready="${11}"
  local verify_env_bands="${12:-0}"

  local sync_args="--package mal-core --group abm"
  local gif_flag=""
  if [[ "$gif" == "1" ]]; then
    gif_flag=" --gif"
  fi

  local verify_cmd=""
  if [[ "$verify_env_bands" == "1" ]]; then
    local bin="mal-core/src/mal_core/abm/bin/mal_abm_fast_$(uname -s | tr '[:upper:]' '[:lower:]')"
    verify_cmd="bash $bin run --aoi $aoi --env data/$aoi/${aoi}_regional_2024_2025_env.nc --habitat data/$aoi/${aoi}_habitat_patches.gpkg --year $year --month $month --days 1 --seed 1 --n-rollouts 1 --snapshot-every 1 --output /tmp/verify_d1.tif --hosts data/$aoi/${aoi}_host_static.nc --seeding-mode host-weighted 2>&1 | tee /work/verify_env_bands.log | grep -aq 'carries static catchment_ratio' && grep -aq 'carries static k_capacity_mult' /work/verify_env_bands.log && grep -aq 'carries static TWI' /work/verify_env_bands.log && echo '[verify-env-bands] OK' && "
  fi

  local cmd="cd /work/code/$repo_name && uv sync $sync_args && bash mal-core/src/mal_core/abm/build.sh && "
  if [[ -n "$verify_cmd" ]]; then
    cmd="$cmd$verify_cmd"
  fi
  if [[ -z "$data_ready" ]]; then
    sync_args="$sync_args --group download --group ingest"
    cmd="cd /work/code/$repo_name && uv sync $sync_args && bash mal-core/src/mal_core/abm/build.sh && uv run malariasim download --aoi $aoi && uv run malariasim ingest --aoi $aoi --year $year --month $month --data-dir data/$aoi --output-dir data/$aoi && "
  fi
  cmd="$cmd uv run malariasim abm --aoi $aoi --year $year --month $month --days $days --seed $seed --n-rollouts $n_rollouts --snapshot-every $snapshot_every --timeout 2000000 --output-dir runs/abm/$run_name$gif_flag"
  printf '%s' "$cmd"
}

# sim_run <name> <repo> <repo_url> <branch> <aoi> <year> <month> <days> <seed> <n_rollouts> <snapshot_every> <run_name> <gif> <data_ready> <cmd> <pull_to> <keep-vm> <vm_type>
sim_run() {
  local name="$1" repo="$2" repo_url="$3" branch="$4" aoi="$5" year="$6" month="$7"
  local days="$8" seed="$9" n_rollouts="${10}" snapshot_every="${11}" run_name="${12}"
  local gif="${13}" data_ready="${14}" cmd="${15}" pull_to="${16}" keep_vm="${17}" vm_type="${18}"
  # Extra flags appended VERBATIM to the remote `malariasim abm` command
  # (arg 19; everything the user put after `--` on the CLI). sim-run does
  # not interpret them.
  local passthrough_args="${19:-}"
  local verify_env_bands="${20:-0}"
  vm_type="${vm_type:-cx33}"

  _ensure_local_path "repo" "$repo"
  if [[ -n "$data_ready" ]]; then
    _ensure_local_path "data-ready" "$data_ready"
    if [[ ! -f "$data_ready/manifest.json" ]]; then
      die "data-ready folder has no manifest.json (is it a downloaded+ingested AOI dir?): $data_ready"
    fi
  fi
  if [[ -z "$repo_url" ]]; then
    repo_url="$(_resolve_repo_url "$repo")"
  fi
  if [[ -z "$branch" ]]; then
    branch="$(_resolve_branch "$repo")"
  fi

  local repo_name
  repo_name="$(_resolve_repo_name "$repo")"
  local remote_repo="/work/code/$repo_name"
  local remote_data_dir="$remote_repo/data/$aoi"
  local remote_run_dir="$remote_repo/runs/abm/$run_name"

  # The VM clones the repo from git (shallow), then optionally receives the
  # ready data via rsync. Build the remote setup command.
  local setup_cmd="rm -rf $remote_repo && git clone --depth 1 --branch '$branch' '$repo_url' '$remote_repo'"

  # Build the command unless the caller overrode it with --cmd.
  if [[ -z "$cmd" ]]; then
    cmd="$(_build_sim_cmd "$repo_name" "$aoi" "$year" "$month" "$days" "$seed" "$n_rollouts" "$snapshot_every" "$run_name" "$gif" "$data_ready" "$verify_env_bands")"
    if [[ -n "$passthrough_args" ]]; then
      cmd="$cmd $passthrough_args"
    fi
  fi

  # Cost estimate: assume HETZNER_RUN_ESTIMATE_HOURS worst case. The user
  # can pass --yes to skip the prompt.
  local estimate_rate estimate_hours estimate_cost
  estimate_rate="$(price_for_type "$vm_type" || echo 0.030)"
  estimate_hours="${HETZNER_RUN_ESTIMATE_HOURS:-1}"
  estimate_cost="$(LC_NUMERIC=C awk -v r="$estimate_rate" -v h="$estimate_hours" 'BEGIN { printf "%.4f", r*h }')"

  if [[ "${HETZNER_RUN_DRY_RUN:-0}" == "1" ]]; then
    log_info "[dry-run] sim-run plan:"
    log_info "  name=$name"
    log_info "  clone: $repo_url (branch: $branch) -> $remote_repo"
    log_info "  aoi:  $aoi  params: year=$year month=$month days=$days seed=$seed n-rollouts=$n_rollouts snapshot-every=$snapshot_every run-name=$run_name gif=$gif"
    if [[ -n "$data_ready" ]]; then
      log_info "  data: READY ($data_ready -> $remote_data_dir/)"
    else
      log_info "  data: NOT ready (download + ingest on VM)"
    fi
    log_info "  setup: $setup_cmd"
    log_info "  cmd:  $cmd"
    log_info "  pull $remote_run_dir/ -> $pull_to"
    if [[ "$keep_vm" == "1" ]]; then
      log_info "  end:  stop (--keep-vm)"
    else
      log_info "  end:  destroy"
    fi
    log_info "  estimated cost ($vm_type × $estimate_hours h): $(format_eur "$estimate_cost")"
    return 0
  fi

  log_info "estimated cost: $(format_eur "$estimate_cost") ($vm_type × ${estimate_hours}h)"
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

  start_vm "$name" "$vm_type" "ubuntu-24.04" "fsn1" \
    "$(resolve_ssh_key_name "")"

  exec_remote "$name" "bash -lc $(printf %q "$setup_cmd")"
  if [[ -n "$data_ready" ]]; then
    push_path "$name" "$data_ready/" "$remote_data_dir/"
  fi

  # Run the job DETACHED on the VM (setsid + nohup) so it survives an ssh
  # disconnect / laptop sleep. It logs to /work/<run>.log and touches
  # /work/<run>.done when finished. We poll for the marker, then pull.
  # If this local process dies overnight, the VM job keeps running and the
  # results stay on the VM — the user can pull them later.
  local done_marker="/work/${run_name}.done"
  local job_log="/work/${run_name}.log"
  local launch="setsid bash -c $(printf %q "$cmd && touch $done_marker") > $job_log 2>&1 < /dev/null &"
  exec_remote "$name" "bash -lc $(printf %q "$launch")"

  # Poll for completion (effectively unlimited: 30 days). If it finishes,
  # break and pull.
  local waited=0
  while (( waited < 2592000 )); do
    if exec_remote "$name" "test -f $done_marker"; then
      break
    fi
    sleep 60
    waited=$(( waited + 60 ))
  done

  pull_path "$name" "$remote_run_dir/" "$pull_to/"

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
    cmd="cd $remote_repo && uv sync && uv run malariasim train --run-dir runs/abm --epochs 50 --output-dir runs/training && cp $remote_config runs/training/config.yaml"
  else
    cmd="cd $remote_repo && uv sync && uv run malariasim train --run-dir runs/abm --epochs 50 --output-dir runs/training"
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
