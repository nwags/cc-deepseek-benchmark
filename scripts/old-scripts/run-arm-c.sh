#!/usr/bin/env bash
set -euo pipefail

if [[ ! -f .secrets/deepseek.env ]]; then
  echo "Missing .secrets/deepseek.env. Create it with DEEPSEEK_API_KEY=..."
  exit 1
fi

set -a
source .secrets/deepseek.env
set +a

: "${DEEPSEEK_API_KEY:?DEEPSEEK_API_KEY is required}"

unset ANTHROPIC_API_KEY

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
  --agent-env ANTHROPIC_BASE_URL=https://api.deepseek.com/anthropic \
  --agent-env ANTHROPIC_AUTH_TOKEN="$DEEPSEEK_API_KEY" \
  --agent-env ANTHROPIC_MODEL=deepseek-v4-flash \
  --agent-env ANTHROPIC_DEFAULT_OPUS_MODEL=deepseek-v4-flash \
  --agent-env ANTHROPIC_DEFAULT_SONNET_MODEL=deepseek-v4-flash \
  --agent-env ANTHROPIC_DEFAULT_HAIKU_MODEL=deepseek-v4-flash \
  --agent-env CLAUDE_CODE_SUBAGENT_MODEL=deepseek-v4-flash \
  --agent-env CLAUDE_CODE_EFFORT_LEVEL=max \
  --agent-env CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC=1 \
  "${TASK_ARGS[@]}" \
  --n-attempts "${N_ATTEMPTS:-3}" \
  --n-concurrent "${N_CONCURRENT:-4}" \
  --jobs-dir ./results/arm-c-deepseek-flash \
  --yes
