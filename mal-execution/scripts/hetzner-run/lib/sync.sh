#!/usr/bin/env bash
# hetzner-run — sync helpers (rsync push/pull, exec)

# resolve_ip <name>
#   Read the IP from cache; fall back to hcloud describe if cache is missing.
resolve_ip() {
  local name="$1"
  local ip
  ip="$(read_cache_field "$name" ip || true)"
  if [[ -n "$ip" && "$ip" != "null" ]]; then
    printf '%s\n' "$ip"
    return 0
  fi
  if [[ "${HETZNER_RUN_DRY_RUN:-0}" == "1" ]]; then
    printf '127.0.0.1\n'
    return 0
  fi
  ensure_hcloud
  ensure_jq
  hcloud server describe "$name" --output json 2>/dev/null \
    | jq -r '.public_net.ipv4.ip // empty' \
    || die "could not resolve IP for '$name'"
}

# push_path <name> <local> <remote>
push_path() {
  local name="$1" local_path="$2" remote_path="$3"
  [[ -e "$local_path" ]] || die "local path does not exist: $local_path"
  local ip
  ip="$(resolve_ip "$name")"
  local ssh_id_args
  ssh_id_args="$(ssh_identity_args)"

  if [[ "${HETZNER_RUN_DRY_RUN:-0}" == "1" ]]; then
    log_info "[dry-run] ssh root@$ip mkdir -p $(dirname "$remote_path")"
    log_info "[dry-run] rsync -avz --progress -e \"ssh -o StrictHostKeyChecking=no ${ssh_id_args}\" $local_path root@$ip:$remote_path"
    return 0
  fi

  # shellcheck disable=SC2086
  ssh -o StrictHostKeyChecking=no $ssh_id_args "root@$ip" "mkdir -p '$(dirname "$remote_path")'" \
    || die "remote mkdir failed: root@$ip:$(dirname "$remote_path")"

  # shellcheck disable=SC2086
  rsync -avz --progress \
    -e "ssh -o StrictHostKeyChecking=no ${ssh_id_args}" \
    "$local_path" "root@$ip:$remote_path" \
    || die "rsync push failed: $local_path -> $ip:$remote_path"
}

# pull_path <name> <remote> <local>
pull_path() {
  local name="$1" remote_path="$2" local_path="$3"
  local ip
  ip="$(resolve_ip "$name")"
  local ssh_id_args
  ssh_id_args="$(ssh_identity_args)"

  if [[ "${HETZNER_RUN_DRY_RUN:-0}" == "1" ]]; then
    log_info "[dry-run] mkdir -p $(dirname "$local_path")"
    log_info "[dry-run] rsync -avz --progress -e \"ssh -o StrictHostKeyChecking=no ${ssh_id_args}\" root@$ip:$remote_path $local_path"
    return 0
  fi

  mkdir -p "$(dirname "$local_path")" || die "local mkdir failed: $(dirname "$local_path")"

  # shellcheck disable=SC2086
  rsync -avz --progress \
    -e "ssh -o StrictHostKeyChecking=no ${ssh_id_args}" \
    "root@$ip:$remote_path" "$local_path" \
    || die "rsync pull failed: $ip:$remote_path -> $local_path"
}

# exec_remote <name> <cmd...>
#   Stream stdout/stderr live; preserve SSH exit code.
exec_remote() {
  local name="$1"; shift
  local ip
  ip="$(resolve_ip "$name")"
  local ssh_id_args
  ssh_id_args="$(ssh_identity_args)"

  if [[ "${HETZNER_RUN_DRY_RUN:-0}" == "1" ]]; then
    log_info "[dry-run] ssh -o StrictHostKeyChecking=no ${ssh_id_args}root@$ip $*"
    return 0
  fi

  # shellcheck disable=SC2086
  ssh -o StrictHostKeyChecking=no $ssh_id_args "root@$ip" "$@"
}
