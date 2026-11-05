#!/usr/bin/env bash
# Point the app at the API on this computer, through its LAN IP.
#
# A phone cannot reach "localhost" on the computer, so the API URL must use
# the LAN IP. The IP changes between networks; run this again after a move.
#
#   scripts/use-lan-ip.sh          # port 8000
#   API_PORT=8001 scripts/use-lan-ip.sh
set -euo pipefail

cd "$(dirname "$0")/.."
port="${API_PORT:-8000}"

if command -v ipconfig >/dev/null 2>&1 && ipconfig getifaddr en0 >/dev/null 2>&1; then
  ip="$(ipconfig getifaddr en0)"            # macOS
else
  ip="$(hostname -I 2>/dev/null | awk '{print $1}')"  # Linux
fi
if [ -z "${ip:-}" ]; then
  echo "Could not find a LAN IP. Set EXPO_PUBLIC_API_URL in app/.env by hand." >&2
  exit 1
fi

url="http://${ip}:${port}"
touch .env
if grep -q '^EXPO_PUBLIC_API_URL=' .env; then
  sed -i.bak "s|^EXPO_PUBLIC_API_URL=.*|EXPO_PUBLIC_API_URL=${url}|" .env && rm -f .env.bak
else
  echo "EXPO_PUBLIC_API_URL=${url}" >> .env
fi
echo "EXPO_PUBLIC_API_URL=${url}"
