#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'USAGE'
Usage: scripts/eval_remote_ops.sh <status|find-results|rescue-results|harbor-cache-clean>

Environment:
  EVAL_REMOTE_HOSTS="vps1 vps2"
  EVAL_REMOTE_<KEY>_HOST="user@host"
  EVAL_REMOTE_<KEY>_AS_USER="sudo -iu bench"
  EVAL_REMOTE_<KEY>_RUNNER_DIRS="/path/one /path/two"
  EVAL_REMOTE_RESCUE_DEST="tmp/eval-remote-rescue"
  EVAL_REMOTE_FIND_LIMIT=80
  EVAL_REMOTE_CLEAN_CONFIRM=1
USAGE
}

op="${1:-}"
if [[ -z "$op" || "$op" == "-h" || "$op" == "--help" ]]; then
  usage
  exit 0
fi

case "$op" in
  status|find-results|rescue-results|harbor-cache-clean) ;;
  *)
    usage >&2
    exit 2
    ;;
esac

EVAL_REMOTE_HOSTS="${EVAL_REMOTE_HOSTS:-vps1 vps2}"
EVAL_REMOTE_VPS1_HOST="${EVAL_REMOTE_VPS1_HOST:-bench@51.81.81.176}"
EVAL_REMOTE_VPS1_AS_USER="${EVAL_REMOTE_VPS1_AS_USER:-}"
EVAL_REMOTE_VPS1_RUNNER_DIRS="${EVAL_REMOTE_VPS1_RUNNER_DIRS:-/home/bench/actions-runner /home/bench/actions-runner-slot2 /home/bench/actions-runner-slot3}"
EVAL_REMOTE_VPS2_HOST="${EVAL_REMOTE_VPS2_HOST:-ubuntu@135.148.42.89}"
EVAL_REMOTE_VPS2_AS_USER="${EVAL_REMOTE_VPS2_AS_USER:-sudo -iu bench}"
EVAL_REMOTE_VPS2_RUNNER_DIRS="${EVAL_REMOTE_VPS2_RUNNER_DIRS:-/home/bench/actions-runner-slot4 /home/bench/actions-runner-slot5 /home/bench/actions-runner-slot6}"
EVAL_REMOTE_FIND_LIMIT="${EVAL_REMOTE_FIND_LIMIT:-80}"
EVAL_REMOTE_RESCUE_DEST="${EVAL_REMOTE_RESCUE_DEST:-tmp/eval-remote-rescue}"
EVAL_REMOTE_CLEAN_CONFIRM="${EVAL_REMOTE_CLEAN_CONFIRM:-${CONFIRM:-0}}"

upper_key() {
  printf '%s' "$1" | tr '[:lower:]-' '[:upper:]_'
}

var_value() {
  local name="$1"
  eval "printf '%s' \"\${${name}:-}\""
}

remote_payload() {
  cat <<'REMOTE'
set -euo pipefail

op="$1"
confirm="$2"
find_limit="$3"
shift 3
host_name="$(hostname -f 2>/dev/null || hostname)"

case "$op" in
  status)
    printf 'host\t%s\n' "$host_name"
    for dir in "$@"; do
      printf 'runner_dir\t%s\t%s\n' "$host_name" "$dir"
      if [[ ! -d "$dir" ]]; then
        printf 'missing_runner_dir\t%s\t%s\n' "$host_name" "$dir"
        continue
      fi
      if [[ -x "$dir/svc.sh" ]]; then
        (cd "$dir" && ./svc.sh status) || true
      fi
      if [[ -d "$dir/_diag" ]]; then
        find "$dir/_diag" -maxdepth 1 -type f -printf '%T@ %p\n' 2>/dev/null \
          | sort -nr | head -n 5 | cut -d' ' -f2- || true
      fi
      if [[ -d "$dir/_work" ]]; then
        find "$dir/_work" -maxdepth 4 -type d -name cc-deepseek-bench -print 2>/dev/null \
          | sort | head -n 10 || true
      fi
    done
    pgrep -af 'Runner.Listener|Runner.Worker|harbor|terminal-bench|docker' || true
    df -h /home /tmp 2>/dev/null || df -h .
    ;;

  find-results)
    for dir in "$@"; do
      printf 'runner_dir\t%s\t%s\n' "$host_name" "$dir"
      find "$dir" -path '*/cc-deepseek-bench/results/phase3/*' \
        \( -name result.json -o -name job.log -o -name ingest_manifest.json -o -name lock.json \) \
        -type f -print 2>/dev/null | sort | head -n "$find_limit" || true
    done
    ;;

  rescue-results)
    paths=()
    for dir in "$@"; do
      while IFS= read -r path; do paths+=("$path"); done < <(
        find "$dir" -path '*/cc-deepseek-bench/results/phase3' -type d -print 2>/dev/null
      )
      while IFS= read -r path; do paths+=("$path"); done < <(
        find "$dir" -path '*/cc-deepseek-bench/artifacts/phase3' -type d -print 2>/dev/null
      )
    done
    if ((${#paths[@]} == 0)); then
      printf 'no_phase3_results_found\t%s\n' "$host_name" >&2
      tar -czf - --files-from /dev/null
      exit 0
    fi
    printf 'rescue_paths\t%s\t%s\n' "$host_name" "${#paths[@]}" >&2
    tar -czf - "${paths[@]}"
    ;;

  harbor-cache-clean)
    printf 'host\t%s\n' "$host_name"
    if [[ "$confirm" != "1" && "$confirm" != "true" && "$confirm" != "yes" ]]; then
      printf 'dry_run\tset EVAL_REMOTE_CLEAN_CONFIRM=1 to remove Harbor/Terminal-Bench caches\n'
      for cache in "$HOME/.cache/harbor" "$HOME/.cache/terminal-bench" "$HOME/.cache/uv"; do
        [[ -e "$cache" ]] && du -sh "$cache" 2>/dev/null || true
      done
      docker system df 2>/dev/null || true
      exit 0
    fi
    rm -rf "$HOME/.cache/harbor" "$HOME/.cache/terminal-bench"
    find "$HOME/.cache" -maxdepth 2 -type d \
      \( -name '*harbor*' -o -name '*terminal-bench*' \) \
      -print -exec rm -rf {} + 2>/dev/null || true
    docker builder prune -af 2>/dev/null || true
    docker system prune -af 2>/dev/null || true
    ;;
esac
REMOTE
}

run_host() {
  local key="$1"
  local upper host as_user dirs_string dest
  upper="$(upper_key "$key")"
  host="$(var_value "EVAL_REMOTE_${upper}_HOST")"
  as_user="$(var_value "EVAL_REMOTE_${upper}_AS_USER")"
  dirs_string="$(var_value "EVAL_REMOTE_${upper}_RUNNER_DIRS")"

  if [[ -z "$host" || -z "$dirs_string" ]]; then
    printf 'missing_inventory\t%s\n' "$key" >&2
    return 1
  fi

  ssh_opts=()
  as_user_args=()
  dirs=()
  if [[ -n "${EVAL_REMOTE_SSH_OPTS:-}" ]]; then
    read -r -a ssh_opts <<< "$EVAL_REMOTE_SSH_OPTS"
  fi
  if [[ -n "$as_user" ]]; then
    read -r -a as_user_args <<< "$as_user"
  fi
  read -r -a dirs <<< "$dirs_string"

  printf 'remote_host\t%s\t%s\n' "$key" "$host" >&2
  if [[ "$op" == "rescue-results" ]]; then
    dest="$EVAL_REMOTE_RESCUE_DEST/$key"
    mkdir -p "$dest"
    remote_payload \
      | ssh "${ssh_opts[@]}" "$host" "${as_user_args[@]}" bash -s -- "$op" "$EVAL_REMOTE_CLEAN_CONFIRM" "$EVAL_REMOTE_FIND_LIMIT" "${dirs[@]}" \
      | tar -xzf - -C "$dest"
    printf 'rescued\t%s\t%s\n' "$key" "$dest"
  else
    remote_payload \
      | ssh "${ssh_opts[@]}" "$host" "${as_user_args[@]}" bash -s -- "$op" "$EVAL_REMOTE_CLEAN_CONFIRM" "$EVAL_REMOTE_FIND_LIMIT" "${dirs[@]}"
  fi
}

status=0
for key in $EVAL_REMOTE_HOSTS; do
  run_host "$key" || status=1
done

exit "$status"
