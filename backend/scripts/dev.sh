#!/usr/bin/env bash
# Run the full local stack for testing on a phone.
#
#   Docker: Postgres, MinIO, Redis, LiveKit, Egress
#   API:    uvicorn with reload on $API_PORT (default 8000)
#   Agent:  LiveKit agent worker, once scripts/run_agent.py exists
#
# Usage: make practice   (or ./scripts/dev.sh from backend/)
# Ctrl-C stops the API and agent. Docker keeps running; `make down` stops it.

set -euo pipefail

cd "$(dirname "$0")/.."
BACKEND_DIR="$(pwd)"
APP_DIR="$(cd .. && pwd)/app"
API_PORT="${API_PORT:-8000}"

# Export KEY=VALUE lines from .env without running them as shell.
if [[ -f .env ]]; then
  while IFS= read -r line || [[ -n "$line" ]]; do
    [[ -z "$line" || "$line" =~ ^[[:space:]]*# || "$line" != *=* ]] && continue
    key="${line%%=*}"
    value="${line#*=}"
    value="${value%\"}"; value="${value#\"}"
    value="${value%\'}"; value="${value#\'}"
    export "$key=$value"
  done < .env
fi

# The phone cannot reach "localhost", so every URL handed to it uses the LAN IP.
# Server-to-server traffic keeps using localhost.
detect_lan_ip() {
  if [[ "$(uname)" == "Darwin" ]]; then
    for iface in en0 en1 en2; do
      ipconfig getifaddr "$iface" 2>/dev/null && return
    done
  fi
  if command -v ip >/dev/null 2>&1; then
    ip -4 -o addr show scope global 2>/dev/null \
      | awk '!/docker|br-|veth|virbr/ {split($4, a, "/"); print a[1]; exit}'
    return
  fi
  hostname -I 2>/dev/null | awk '{print $1}'
}

LAN_IP="${LAN_IP:-$(detect_lan_ip || true)}"
LAN_IP="${LAN_IP:-127.0.0.1}"
export LAN_IP MINIO_HOST="$LAN_IP"
export LIVEKIT_PUBLIC_URL="ws://${LAN_IP}:7880"
export S3_PUBLIC_ENDPOINT="http://${LAN_IP}:9000"

# Point the app at this machine.
if [[ -d "$APP_DIR" ]]; then
  app_env="$APP_DIR/.env"
  touch "$app_env"
  if grep -q '^EXPO_PUBLIC_API_URL=' "$app_env"; then
    sed -i.bak "s|^EXPO_PUBLIC_API_URL=.*|EXPO_PUBLIC_API_URL=http://${LAN_IP}:${API_PORT}|" "$app_env"
    rm -f "$app_env.bak"
  else
    echo "EXPO_PUBLIC_API_URL=http://${LAN_IP}:${API_PORT}" >> "$app_env"
  fi
fi

pids=()
cleanup() {
  echo
  echo "==> Stopping API and agent (Docker keeps running; 'make down' stops it)"
  for pid in "${pids[@]:-}"; do kill "$pid" 2>/dev/null || true; done
  wait 2>/dev/null || true
}
trap cleanup EXIT INT TERM

echo "==> LAN IP: ${LAN_IP}"
echo "==> Starting Docker services"
docker compose up -d

echo "==> Waiting for Postgres"
until docker compose exec -T postgres pg_isready -U "${POSTGRES_USER:-pitchme}" >/dev/null 2>&1; do
  sleep 1
done

if [[ -f alembic.ini ]]; then
  echo "==> Applying migrations"
  uv run --all-extras alembic upgrade head
fi

echo "==> API on http://0.0.0.0:${API_PORT}"
uv run --all-extras uvicorn server.main:app --reload --host 0.0.0.0 --port "$API_PORT" &
pids+=($!)

if [[ -f scripts/run_agent.py ]]; then
  echo "==> LiveKit agent worker"
  uv run --all-extras python scripts/run_agent.py start &
  pids+=($!)
fi

cat <<EOF

  API docs       http://localhost:${API_PORT}/docs
  Phone API      http://${LAN_IP}:${API_PORT}
  LiveKit        ws://localhost:7880 (phone: ${LIVEKIT_PUBLIC_URL})
  MinIO console  http://localhost:9001

  Ctrl-C to stop.
EOF

cd "$BACKEND_DIR"
wait
