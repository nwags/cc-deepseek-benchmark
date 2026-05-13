#!/usr/bin/env bash
set -euo pipefail

TASK_ARGS=()
while IFS= read -r task; do
  [[ -z "$task" ]] && continue
  [[ "$task" =~ ^# ]] && continue
  TASK_ARGS+=(--include-task-name "$task")
done < tasks.txt

uv run harbor run \
  --dataset terminal-bench@2.0 \
  --agent oracle \
  "${TASK_ARGS[@]}" \
  --n-attempts "${N_ATTEMPTS:-1}" \
  --n-concurrent "${N_CONCURRENT:-1}" \
  --jobs-dir ./results/sanity-oracle-subset \
  --yes
