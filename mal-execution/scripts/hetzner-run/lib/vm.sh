#!/usr/bin/env bash
# hetzner-run — VM lifecycle (start / stop / destroy / status)

# start_vm <name> <type> <image> <location> <ssh-key>
#   Creates the server, polls until running, waits for SSH, writes cache.
start_vm() {
  local name="$1" type="$2" image="$3" location="$4" ssh_key="$5"
  validate_name "$name"

  local started_at
  started_at="$(iso_now)"

  if [[ "${HETZNER_RUN_DRY_RUN:-0}" == "1" ]]; then
    log_info "[dry-run] would create server: name=$name type=$type image=$image location=$location ssh_key=$ssh_key"
    log_info "[dry-run] cloud-init: $HETZNER_RUN_CLOUD_INIT"
    log_info "[dry-run] hcloud server create --name $name --type $type --image $image --location $location --ssh-key $ssh_key --user-data-from-file $HETZNER_RUN_CLOUD_INIT"
    write_cache "$name" "127.0.0.1" "$type" "$location" "$started_at"
    log_info "[dry-run] synthetic metadata written to $(cache_path_for "$name")"
    return 0
  fi

  ensure_hcloud
  ensure_jq

  log_info "creating server '$name' (type=$type, location=$location)"
  mkdir -p "$HETZNER_RUN_CACHE_DIR"
  if ! hcloud server create \
        --name "$name" \
        --type "$type" \
        --image "$image" \
        --location "$location" \
        --ssh-key "$ssh_key" \
        --user-data-from-file "$HETZNER_RUN_CLOUD_INIT" \
        --output json >/tmp/hetzner-run.$$.create.json 2>>"$HETZNER_RUN_CACHE_DIR/last.log"; then
    die "hcloud server create failed — see /tmp/hetzner-run.$$.create.json or last.log"
  fi
  log_info "create call returned; waiting for status=running…"

  # Poll describe until status is running and we have an IPv4.
  local poll_status_cmd
  poll_status_cmd='hcloud server describe "$1" --output json 2>/dev/null | jq -e ".status == \"running\" and .public_net.ipv4.ip != null and .public_net.ipv4.ip != \"\""'
  if ! wait_until 2 120 "$poll_status_cmd" "$name"; then
    die "server '$name' did not reach status=running within 120s"
  fi

  local ip
  ip="$(hcloud server describe "$name" --output json | jq -r '.public_net.ipv4.ip')"
  [[ -n "$ip" && "$ip" != "null" ]] || die "no IPv4 assigned to '$name'"

  log_info "server '$name' is running at $ip; waiting for SSH…"
  local ssh_id_args
  ssh_id_args="$(ssh_identity_args)"
  local poll_ssh_cmd
  poll_ssh_cmd='ssh -o StrictHostKeyChecking=no -o ConnectTimeout=5 '"$ssh_id_args"'root@"$1" true'
  # shellcheck disable=SC2086
  if ! eval "$poll_ssh_cmd" "$ip" >/dev/null 2>&1; then
    if ! wait_until 2 90 "$poll_ssh_cmd" "$ip"; then
      die "SSH to $ip did not respond within 90s"
    fi
  fi

  write_cache "$name" "$ip" "$type" "$location" "$started_at"

  local cost
  cost="$(cost_since_start "$name" "$started_at" || echo 0.0000)"
  log_info "started: name=$name ip=$ip type=$type location=$location cost-so-far=$(format_eur "$cost")"
  printf 'name=%s\nip=%s\ntype=%s\nlocation=%s\nstarted_at=%s\ncost_so_far=%s\n' \
    "$name" "$ip" "$type" "$location" "$started_at" "$cost"
}

# stop_vm <name>
#   Graceful shutdown, poll until status=off, print cost-so-far.
stop_vm() {
  local name="$1"
  validate_name "$name"

  local started_at
  started_at="$(read_cache_field "$name" started_at || true)"

  if [[ "${HETZNER_RUN_DRY_RUN:-0}" == "1" ]]; then
    log_info "[dry-run] hcloud server shutdown $name"
    log_info "[dry-run] would poll until status=off"
    log_info "[dry-run] cost-so-far (est.): $(format_eur 0)"
    return 0
  fi

  ensure_hcloud
  log_info "shutting down '$name'…"
  hcloud server shutdown "$name" || die "shutdown failed for '$name'"

  local poll_off_cmd
  poll_off_cmd='hcloud server describe "$1" --output json 2>/dev/null | jq -e ".status == \"off\""'
  if ! wait_until 2 180 "$poll_off_cmd" "$name"; then
    die "server '$name' did not reach status=off within 180s"
  fi

  local cost
  cost="$(cost_since_start "$name" "$started_at" || echo 0.0000)"
  log_info "stopped: name=$name cost-so-far=$(format_eur "$cost")"
}

# destroy_vm <name>
#   Permanent delete. Removes local cache. Prints final cost.
destroy_vm() {
  local name="$1"
  validate_name "$name"

  local started_at
  started_at="$(read_cache_field "$name" started_at || true)"

  if [[ "${HETZNER_RUN_DRY_RUN:-0}" == "1" ]]; then
    log_info "[dry-run] hcloud server delete $name"
    log_info "[dry-run] would poll until server is gone"
    log_info "[dry-run] would remove $(cache_path_for "$name")"
    remove_cache "$name"
    return 0
  fi

  ensure_hcloud
  log_info "deleting '$name'…"
  hcloud server delete "$name" || die "delete failed for '$name'"

  if ! wait_until 2 120 '! hcloud server describe "$1" >/dev/null 2>&1' "$name"; then
    log_warn "server '$name' still present after 120s; check hcloud console"
  fi

  remove_cache "$name"
  local cost
  cost="$(cost_since_start "$name" "$started_at" || echo 0.0000)"
  log_info "destroyed: name=$name final-cost=$(format_eur "$cost")"
}

# status_vm <name>
#   Print a single status block. The hcloud describe JSON is the source of
#   truth; the cache is only used for started_at when hcloud doesn't carry it.
status_vm() {
  local name="$1"
  if [[ "${HETZNER_RUN_DRY_RUN:-0}" == "1" ]]; then
    log_info "[dry-run] hcloud server describe $name --output json"
    return 0
  fi

  ensure_hcloud
  ensure_jq

  local json
  if ! json="$(hcloud server describe "$name" --output json 2>/dev/null)"; then
    die "hcloud server describe '$name' failed (does the server exist?)"
  fi

  local status ip type location created
  status=$(printf '%s' "$json" | jq -r '.status // "unknown"')
  ip=$(printf '%s' "$json" | jq -r '.public_net.ipv4.ip // ""')
  type=$(printf '%s' "$json" | jq -r '.server_type.name // ""')
  location=$(printf '%s' "$json" | jq -r '.datacenter.location.name // ""')
  created=$(printf '%s' "$json" | jq -r '.created // ""')

  local started_at
  started_at="$(read_cache_field "$name" started_at || true)"
  [[ -z "$started_at" || "$started_at" == "null" ]] && started_at="$created"

  local cost now_s start_s uptime_s
  cost="$(cost_since_start "$name" "$started_at" 2>/dev/null || echo 0.0000)"
  if [[ -n "$started_at" && "$started_at" != "null" ]]; then
    now_s="$(date +%s)"
    start_s="$(date -j -f '%Y-%m-%dT%H:%M:%S%z' "$started_at" +%s 2>/dev/null || \
               date -d "$started_at" +%s 2>/dev/null || echo 0)"
    uptime_s=$(( now_s - start_s ))
    uptime_s=$(( uptime_s < 0 ? 0 : uptime_s ))
  else
    uptime_s=0
  fi

  printf 'name:        %s\n' "$name"
  printf 'status:      %s\n' "$status"
  printf 'ip:          %s\n' "${ip:-<none>}"
  printf 'type:        %s\n' "$type"
  printf 'location:    %s\n' "$location"
  printf 'started_at:  %s\n' "${started_at:-<unknown>}"
  printf 'uptime:      %s\n' "$(format_uptime "$uptime_s")"
  printf 'cost_so_far: %s\n' "$(format_eur "$cost")"
}

# list_vms
#   Lists all servers whose name starts with "ms-". One line per VM, header
#   printed first. Skips the call in dry-run mode.
list_vms() {
  if [[ "${HETZNER_RUN_DRY_RUN:-0}" == "1" ]]; then
    log_info "[dry-run] hcloud server list --output json (filtered to ms-*)"
    return 0
  fi

  ensure_hcloud
  ensure_jq

  local list
  list="$(hcloud server list --output json)" || die "hcloud server list failed"
  local filtered
  filtered="$(printf '%s' "$list" | jq -c '[.[] | select(.name | startswith("ms-"))]')"
  local count
  count="$(printf '%s' "$filtered" | jq 'length')"
  printf 'NAME                            STATUS    IP              TYPE    LOCATION  STARTED_AT            COST_SO_FAR\n'
  if [[ "$count" == "0" ]]; then
    log_info "no servers matching ms-*"
    return 0
  fi
  # Build the rows by piping a list of "name\tstatus\tip\ttype\tloc\tcreated"
  # into a while loop that computes cost and prints.
  printf '%s' "$filtered" | jq -r '.[] | [.name, .status, ((.public_net.ipv4.ip // "-")|tostring), .server_type.name, .datacenter.location.name, .created] | @tsv' \
    | while IFS=$'\t' read -r n s ip t loc started; do
        local cost
        cost="$(cost_since_start "$n" "$started" 2>/dev/null || echo 0.0000)"
        printf '%-31s %-9s %-15s %-7s %-9s %-19s €%s\n' \
          "$n" "$s" "$ip" "$t" "$loc" "$started" "$cost"
      done
}
