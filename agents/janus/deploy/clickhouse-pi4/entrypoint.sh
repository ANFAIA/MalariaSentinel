#!/bin/bash

set -eo pipefail
shopt -s nullglob

DO_CHOWN=1
if [ "${CLICKHOUSE_DO_NOT_CHOWN:-0}" = "1" ]; then
    DO_CHOWN=0
fi

CLICKHOUSE_UID="${CLICKHOUSE_UID:-"$(id -u clickhouse)"}"
CLICKHOUSE_GID="${CLICKHOUSE_GID:-"$(id -g clickhouse)"}"

if [ "$(id -u)" = "0" ]; then
    USER=$CLICKHOUSE_UID
    GROUP=$CLICKHOUSE_GID
else
    USER="$(id -u)"
    GROUP="$(id -g)"
    DO_CHOWN=0
fi

CLICKHOUSE_CONFIG="${CLICKHOUSE_CONFIG:-/etc/clickhouse-server/config.xml}"

DATA_DIR="$(clickhouse extract-from-config --config-file "$CLICKHOUSE_CONFIG" --key=path || true)"
TMP_DIR="$(clickhouse extract-from-config --config-file "$CLICKHOUSE_CONFIG" --key=tmp_path || true)"
USER_PATH="$(clickhouse extract-from-config --config-file "$CLICKHOUSE_CONFIG" --key=user_files_path || true)"
LOG_PATH="$(clickhouse extract-from-config --config-file "$CLICKHOUSE_CONFIG" --key=logger.log || true)"
LOG_DIR=""
if [ -n "$LOG_PATH" ]; then LOG_DIR="$(dirname "$LOG_PATH")"; fi
ERROR_LOG_PATH="$(clickhouse extract-from-config --config-file "$CLICKHOUSE_CONFIG" --key=logger.errorlog || true)"
ERROR_LOG_DIR=""
if [ -n "$ERROR_LOG_PATH" ]; then ERROR_LOG_DIR="$(dirname "$ERROR_LOG_PATH")"; fi
FORMAT_SCHEMA_PATH="$(clickhouse extract-from-config --config-file "$CLICKHOUSE_CONFIG" --key=format_schema_path || true)"

readarray -t DISKS_PATHS < <(clickhouse extract-from-config --config-file "$CLICKHOUSE_CONFIG" --key='storage_configuration.disks.*.path' || true)
readarray -t DISKS_METADATA_PATHS < <(clickhouse extract-from-config --config-file "$CLICKHOUSE_CONFIG" --key='storage_configuration.disks.*.metadata_path' || true)

CLICKHOUSE_USER="${CLICKHOUSE_USER:-default}"
CLICKHOUSE_PASSWORD_FILE="${CLICKHOUSE_PASSWORD_FILE:-}"
if [[ -n "${CLICKHOUSE_PASSWORD_FILE}" && -f "${CLICKHOUSE_PASSWORD_FILE}" ]]; then
  CLICKHOUSE_PASSWORD="$(cat "${CLICKHOUSE_PASSWORD_FILE}")"
fi
CLICKHOUSE_PASSWORD="${CLICKHOUSE_PASSWORD:-}"
CLICKHOUSE_DB="${CLICKHOUSE_DB:-}"
CLICKHOUSE_ACCESS_MANAGEMENT="${CLICKHOUSE_DEFAULT_ACCESS_MANAGEMENT:-0}"

function create_directory_and_do_chown() {
    local dir=$1
    [ -z "$dir" ] && return
    if [ "$DO_CHOWN" = "1" ]; then
        mkdir="mkdir"
    else
        mkdir="/usr/bin/clickhouse su "${USER}:${GROUP}" mkdir"
    fi
    if ! $mkdir -p "$dir"; then
        echo "Couldn't create necessary directory: $dir"
        exit 1
    fi
    if [ "$DO_CHOWN" = "1" ]; then
        if [ "$(stat -c %u "$dir")" != "$USER" ] || [ "$(stat -c %g "$dir")" != "$GROUP" ]; then
            chown -R "$USER:$GROUP" "$dir"
        fi
    fi
}

create_directory_and_do_chown "$DATA_DIR"
cd "$DATA_DIR"

for dir in "$ERROR_LOG_DIR" "$LOG_DIR" "$TMP_DIR" "$USER_PATH" "$FORMAT_SCHEMA_PATH" "${DISKS_PATHS[@]}" "${DISKS_METADATA_PATHS[@]}"; do
    create_directory_and_do_chown "$dir"
done

if [ -n "$CLICKHOUSE_USER" ] && [ "$CLICKHOUSE_USER" != "default" ] || [ -n "$CLICKHOUSE_PASSWORD" ] || [ "$CLICKHOUSE_ACCESS_MANAGEMENT" != "0" ]; then
    echo "$0: create new user '$CLICKHOUSE_USER' instead 'default'"
    cat <<EOT > /etc/clickhouse-server/users.d/default-user.xml
    <clickhouse>
      <users>
        <default remove="remove">
        </default>
        <${CLICKHOUSE_USER}>
          <profile>default</profile>
          <networks>
            <ip>::/0</ip>
          </networks>
          <password>${CLICKHOUSE_PASSWORD}</password>
          <quota>default</quota>
          <access_management>${CLICKHOUSE_ACCESS_MANAGEMENT}</access_management>
        </${CLICKHOUSE_USER}>
      </users>
    </clickhouse>
EOT
fi

CLICKHOUSE_ALWAYS_RUN_INITDB_SCRIPTS="${CLICKHOUSE_ALWAYS_RUN_INITDB_SCRIPTS:-}"
if [ -d "${DATA_DIR%/}/data" ]; then
    DATABASE_ALREADY_EXISTS='true'
fi
if [[ -n "${CLICKHOUSE_ALWAYS_RUN_INITDB_SCRIPTS}" || -z "${DATABASE_ALREADY_EXISTS}" ]]; then
  RUN_INITDB_SCRIPTS='true'
fi

if [ -n "${RUN_INITDB_SCRIPTS}" ]; then
    if [ -n "$(ls /docker-entrypoint-initdb.d/)" ] || [ -n "$CLICKHOUSE_DB" ]; then
        HTTP_PORT="$(clickhouse extract-from-config --config-file "$CLICKHOUSE_CONFIG" --key=http_port --try)"
        HTTPS_PORT="$(clickhouse extract-from-config --config-file "$CLICKHOUSE_CONFIG" --key=https_port --try)"
        if [ -n "$HTTP_PORT" ]; then
            URL="http://127.0.0.1:$HTTP_PORT/ping"
        else
            URL="https://127.0.0.1:$HTTPS_PORT/ping"
        fi
        /usr/bin/clickhouse su "${USER}:${GROUP}" /usr/bin/clickhouse server --config-file="$CLICKHOUSE_CONFIG" -- --listen_host=127.0.0.1 &
        pid="$!"
        tries=${CLICKHOUSE_INIT_TIMEOUT:-1000}
        while ! wget --spider --no-check-certificate -T 1 -q "$URL" 2>/dev/null; do
            if [ "$tries" -le "0" ]; then
                echo >&2 'ClickHouse init process failed.'
                exit 1
            fi
            tries=$(( tries-1 ))
            sleep 1
        done
        clickhouseclient=( clickhouse client --multiquery --host "127.0.0.1" -u "$CLICKHOUSE_USER" --password "$CLICKHOUSE_PASSWORD" )
        if [ -n "$CLICKHOUSE_DB" ]; then
            echo "$0: create database '$CLICKHOUSE_DB'"
            "${clickhouseclient[@]}" -q "CREATE DATABASE IF NOT EXISTS $CLICKHOUSE_DB";
        fi
        for f in /docker-entrypoint-initdb.d/*; do
            case "$f" in
                *.sh) if [ -x "$f" ]; then echo "$0: running $f"; "$f"; else echo "$0: sourcing $f"; . "$f"; fi ;;
                *.sql) echo "$0: running $f"; "${clickhouseclient[@]}" < "$f" ; echo ;;
                *.sql.gz) echo "$0: running $f"; gunzip -c "$f" | "${clickhouseclient[@]}"; echo ;;
                *) echo "$0: ignoring $f" ;;
            esac
        done
        if ! kill -s TERM "$pid" || ! wait "$pid"; then
            echo >&2 'Finishing of ClickHouse init process failed.'
            exit 1
        fi
    fi
else
    echo "ClickHouse Database directory appears to contain a database; Skipping initialization"
fi

if [[ $# -lt 1 ]] || [[ "$1" == "--"* ]]; then
    CLICKHOUSE_WATCHDOG_ENABLE=${CLICKHOUSE_WATCHDOG_ENABLE:-0}
    export CLICKHOUSE_WATCHDOG_ENABLE
    if [[ "${CLICKHOUSE_DOCKER_RESTART_ON_EXIT:-0}" -eq "1" ]]; then
        while true; do
            /usr/bin/clickhouse su "${USER}:${GROUP}" /usr/bin/clickhouse server --config-file="$CLICKHOUSE_CONFIG" "$@" ||:
            echo >&2 'ClickHouse Server exited, and the environment variable CLICKHOUSE_DOCKER_RESTART_ON_EXIT is set to 1. Restarting the server.'
        done
    else
        exec /usr/bin/clickhouse su "${USER}:${GROUP}" /usr/bin/clickhouse server --config-file="$CLICKHOUSE_CONFIG" "$@"
    fi
fi

exec "$@"