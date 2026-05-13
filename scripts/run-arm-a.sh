#!/usr/bin/env bash
set -euo pipefail

if [[ ! -f .secrets/anthropic.env ]]; then
  echo "Missing .secrets/anthropic.env. Create it with ANTHROPIC_API_KEY=..."
  exit 1
fi

set -a
source .secrets/anthropic.env
set +a

: "${ANTHROPIC_API_KEY:?ANTHROPIC_API_KEY is required}"

unset ANTHROPIC_BASE_URL
unset ANTHROPIC_AUTH_TOKEN
unset ANTHROPIC_MODEL
unset ANTHROPIC_DEFAULT_OPUS_MODEL
unset ANTHROPIC_DEFAULT_SONNET_MODEL
unset ANTHROPIC_DEFAULT_HAIKU_MODEL

TASK_ARGS=()
while IFS= read -r task; do
  [[ -z "$task" ]] && continue
  [[ "$task" =~ ^# ]] && continue
  TASK_ARGS+=(--include-task-name "$task")
done < tasks.txt

uv run harbor run \
  --dataset terminal-bench@2.0 \
  --agent claude-code \
  --model anthropic/claude-sonnet-4-6 \
  --agent-env ANTHROPIC_API_KEY="$ANTHROPIC_API_KEY" \
  "${TASK_ARGS[@]}" \
  --n-attempts "${N_ATTEMPTS:-3}" \
  --n-concurrent "${N_CONCURRENT:-4}" \
  --jobs-dir ./results/arm-a-anthropic \
  --yes
