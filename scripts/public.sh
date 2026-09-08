#!/usr/bin/env bash
# Publish SketchNet from this laptop with Pinggy (SSH on port 443).
# No router port forwarding. Works on networks where ngrok/Cloudflare quick tunnels time out.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

if [[ ! -x "$ROOT/.venv/bin/python" ]]; then
  echo "Missing .venv. Create it and install requirements first." >&2
  exit 1
fi

cleanup() {
  if [[ -n "${DJANGO_PID:-}" ]]; then
    kill "$DJANGO_PID" 2>/dev/null || true
  fi
}
trap cleanup EXIT INT TERM

"$ROOT/.venv/bin/python" manage.py runserver 127.0.0.1:8000 &
DJANGO_PID=$!

echo "Django on http://127.0.0.1:8000/"
echo "Starting Pinggy tunnel (HTTPS URLs printed below)..."
exec ssh -o StrictHostKeyChecking=accept-new -o ExitOnForwardFailure=yes \
  -p 443 -R0:127.0.0.1:8000 a.pinggy.io
