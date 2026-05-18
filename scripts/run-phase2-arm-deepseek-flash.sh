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

if [[ -z "$DEEPSEEK_API_KEY" ]]; then
  echo "DEEPSEEK_API_KEY is empty."
  exit 1
fi

# Clean DeepSeek-routed Claude Code run.
# Do not allow a host Anthropic key to override provider routing.
unset ANTHROPIC_API_KEY

export ANTHROPIC_BASE_URL="https://api.deepseek.com/anthropic"
export ANTHROPIC_AUTH_TOKEN="$DEEPSEEK_API_KEY"
export ANTHROPIC_MODEL="deepseek-v4-flash"
export ANTHROPIC_DEFAULT_OPUS_MODEL="deepseek-v4-flash"
export ANTHROPIC_DEFAULT_SONNET_MODEL="deepseek-v4-flash"
export ANTHROPIC_DEFAULT_HAIKU_MODEL="deepseek-v4-flash"
export CLAUDE_CODE_SUBAGENT_MODEL="deepseek-v4-flash"
export CLAUDE_CODE_EFFORT_LEVEL=max
export CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC=1

TASK_FILE="${TASK_FILE:-tasks.txt}"

TASK_ARGS=()
while IFS= read -r task; do
  [[ -z "$task" ]] && continue
  [[ "$task" =~ ^# ]] && continue
  TASK_ARGS+=(--include-task-name "$task")
done < "$TASK_FILE"

# Harbor/Claude Code still receives a Claude model selector, but the actual
# provider/model is routed by the Anthropic-compatible DeepSeek env vars.
uv run harbor run \
  --dataset terminal-bench@2.0 \
  --agent claude-code \
  --model anthropic/claude-sonnet-4-6 \
  --agent-env ANTHROPIC_BASE_URL="$ANTHROPIC_BASE_URL" \
  --agent-env ANTHROPIC_AUTH_TOKEN="$ANTHROPIC_AUTH_TOKEN" \
  --agent-env ANTHROPIC_MODEL="$ANTHROPIC_MODEL" \
  --agent-env ANTHROPIC_DEFAULT_OPUS_MODEL="$ANTHROPIC_DEFAULT_OPUS_MODEL" \
  --agent-env ANTHROPIC_DEFAULT_SONNET_MODEL="$ANTHROPIC_DEFAULT_SONNET_MODEL" \
  --agent-env ANTHROPIC_DEFAULT_HAIKU_MODEL="$ANTHROPIC_DEFAULT_HAIKU_MODEL" \
  --agent-env CLAUDE_CODE_SUBAGENT_MODEL="$CLAUDE_CODE_SUBAGENT_MODEL" \
  --agent-env CLAUDE_CODE_EFFORT_LEVEL="$CLAUDE_CODE_EFFORT_LEVEL" \
  --agent-env CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC="$CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC" \
  "${TASK_ARGS[@]}" \
  --n-attempts "${N_ATTEMPTS:-3}" \
  --n-concurrent "${N_CONCURRENT:-4}" \
  --jobs-dir ./results/phase2/arm-deepseek-flash \
  --yes
