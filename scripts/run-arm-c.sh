#!/usr/bin/env bash
set -euo pipefail

if [[ ! -f .env ]]; then
  echo "Missing .env. Copy .env.example to .env and add keys."
  exit 1
fi

unset ANTHROPIC_API_KEY

export ANTHROPIC_BASE_URL="https://api.deepseek.com/anthropic"
export ANTHROPIC_AUTH_TOKEN="$(grep '^DEEPSEEK_API_KEY=' .env | cut -d= -f2-)"
export ANTHROPIC_MODEL="deepseek-v4-flash"
export ANTHROPIC_DEFAULT_OPUS_MODEL="deepseek-v4-flash"
export ANTHROPIC_DEFAULT_SONNET_MODEL="deepseek-v4-flash"
export ANTHROPIC_DEFAULT_HAIKU_MODEL="deepseek-v4-flash"
export CLAUDE_CODE_SUBAGENT_MODEL="deepseek-v4-flash"
export CLAUDE_CODE_EFFORT_LEVEL=max
export CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC=1

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
  "${TASK_ARGS[@]}" \
  --n-attempts "${N_ATTEMPTS:-3}" \
  --n-concurrent "${N_CONCURRENT:-4}" \
  --jobs-dir ./results/arm-c-deepseek-flash \
  --yes
