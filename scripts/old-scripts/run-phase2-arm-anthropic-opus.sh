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

if [[ "$ANTHROPIC_API_KEY" != sk-ant-* ]]; then
  echo "ANTHROPIC_API_KEY does not look like an Anthropic key."
  echo "Expected prefix: sk-ant-"
  echo "Actual prefix: ${ANTHROPIC_API_KEY:0:8}"
  echo "Actual suffix: ${ANTHROPIC_API_KEY: -4}"
  exit 1
fi

# Clean Anthropic run. Do not route through DeepSeek or any prior provider override.
unset ANTHROPIC_BASE_URL
unset ANTHROPIC_AUTH_TOKEN
unset ANTHROPIC_MODEL
unset ANTHROPIC_DEFAULT_OPUS_MODEL
unset ANTHROPIC_DEFAULT_SONNET_MODEL
unset ANTHROPIC_DEFAULT_HAIKU_MODEL
unset CLAUDE_CODE_SUBAGENT_MODEL
unset CLAUDE_CODE_EFFORT_LEVEL
unset CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC

TASK_FILE="${TASK_FILE:-tasks.txt}"

TASK_ARGS=()
while IFS= read -r task; do
  [[ -z "$task" ]] && continue
  [[ "$task" =~ ^# ]] && continue
  TASK_ARGS+=(--include-task-name "$task")
done < "$TASK_FILE"

# Explicit Opus arm.
# This tests Claude Code's named Opus model selection separately from
# account-dependent default behavior.
uv run harbor run \
  --dataset terminal-bench@2.0 \
  --agent claude-code \
  --model opus \
  --agent-env ANTHROPIC_API_KEY="$ANTHROPIC_API_KEY" \
  "${TASK_ARGS[@]}" \
  --n-attempts "${N_ATTEMPTS:-3}" \
  --n-concurrent "${N_CONCURRENT:-4}" \
  --jobs-dir ./results/phase2/arm-anthropic-opus \
  --yes
