#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

ENV_FILE="${LITELLM_ENV_FILE:-.secrets/litellm.env}"
CONFIG_FILE="${LITELLM_CONFIG_FILE:-configs/router/litellm.config.yaml}"
PORT="${LITELLM_PORT:-4000}"
HOST="${LITELLM_HOST:-127.0.0.1}"

if [[ ! -f "$ENV_FILE" ]]; then
  echo "Missing $ENV_FILE"
  echo "Create it from configs/router/litellm.env.example and add real local keys."
  exit 1
fi

if [[ ! -f "$CONFIG_FILE" ]]; then
  echo "Missing $CONFIG_FILE"
  echo "Create it with:"
  echo "  cp configs/router/litellm.config.yaml.example configs/router/litellm.config.yaml"
  echo "Then verify model slugs before paid canaries."
  exit 1
fi

set -a
source "$ENV_FILE"

# Provider API keys remain in provider-specific secret files.
# LiteLLM config entries use os.environ/<KEY>, so these files are sourced
# into the LiteLLM process environment without duplicating keys into
# .secrets/litellm.env.
PROVIDER_ENV_FILES="${LITELLM_PROVIDER_ENV_FILES:-.secrets/anthropic.env .secrets/deepseek.env .secrets/openai.env .secrets/gemini.env .secrets/xai.env .secrets/kimi.env .secrets/dashscope.env .secrets/zai.env}"

for provider_env in $PROVIDER_ENV_FILES; do
  if [[ -f "$provider_env" ]]; then
    source "$provider_env"
  fi
done

set +a

: "${LITELLM_MASTER_KEY:?LITELLM_MASTER_KEY is required in $ENV_FILE}"

LITELLM_BIN="${LITELLM_BIN:-}"

if [[ -z "$LITELLM_BIN" && -x ".tools/litellm-proxy/bin/litellm" ]]; then
  LITELLM_BIN=".tools/litellm-proxy/bin/litellm"
fi

if [[ -z "$LITELLM_BIN" ]]; then
  LITELLM_BIN="$(command -v litellm || true)"
fi

if [[ -z "$LITELLM_BIN" ]]; then
  echo "litellm command not found."
  echo "Install the proxy in an isolated tool venv with:"
  echo "  uv venv .tools/litellm-proxy --python 3.13"
  echo "  uv pip install --python .tools/litellm-proxy/bin/python 'litellm[proxy]'"
  exit 1
fi

echo "Starting LiteLLM proxy"
echo "  binary: $LITELLM_BIN"
echo "  config: $CONFIG_FILE"
echo "  host:   $HOST"
echo "  port:   $PORT"

exec "$LITELLM_BIN" --config "$CONFIG_FILE" --host "$HOST" --port "$PORT"
