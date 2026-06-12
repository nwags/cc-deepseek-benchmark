#!/usr/bin/env bash
set -euo pipefail

PORT="${PHASE3_LITELLM_PORT:-4000}"
HOST_IP="${PHASE3_LITELLM_HOST_IP:-172.17.0.1}"
TMP_DIR="$(mktemp -d)"
SERVER_PID=""
NET_NAME="phase3-firewall-probe-$$"

cleanup() {
  set +e
  if [[ -n "${SERVER_PID}" ]]; then
    kill "${SERVER_PID}" 2>/dev/null || true
    wait "${SERVER_PID}" 2>/dev/null || true
  fi
  docker network rm "${NET_NAME}" >/dev/null 2>&1 || true
  rm -rf "${TMP_DIR}"
}
trap cleanup EXIT

if ss -ltn 2>/dev/null | grep -q ":${PORT} "; then
  echo "Port ${PORT} is already in use; stop LiteLLM before running the firewall doctor." >&2
  echo "This doctor intentionally starts a temporary host server on port ${PORT}." >&2
  exit 1
fi

printf 'phase3-firewall-ok\n' > "${TMP_DIR}/phase3-firewall-ok.txt"

(
  cd "${TMP_DIR}"
  python3 -m http.server "${PORT}" --bind 0.0.0.0 >/tmp/phase3-firewall-http.log 2>&1
) &
SERVER_PID="$!"

sleep 2

echo "Checking default Docker bridge access to host ${HOST_IP}:${PORT}"
docker run --rm curlimages/curl:latest \
  -fsS -m 20 \
  "http://${HOST_IP}:${PORT}/phase3-firewall-ok.txt" \
  | grep -q 'phase3-firewall-ok'

echo "Checking user-defined Docker bridge access to host ${HOST_IP}:${PORT}"
docker network create "${NET_NAME}" >/dev/null

docker run --rm --network "${NET_NAME}" curlimages/curl:latest \
  -fsS -m 20 \
  "http://${HOST_IP}:${PORT}/phase3-firewall-ok.txt" \
  | grep -q 'phase3-firewall-ok'

echo "Phase 3 Docker-to-host firewall check passed for port ${PORT}."
