#!/usr/bin/env bash
# =============================================================================
# HireShield-AI — start the backend and frontend together, then wait until both
# are actually answering.  Exists because "NetworkError" in the UI almost always
# means *nothing is listening*, not a broken request: the backend died on
# session/terminal restart and the Vite server was never restarted with it.
#
# Usage:
#   ./scripts/dev.sh            # start both, wait for readiness
#   ./scripts/dev.sh --stop     # stop both
#   ./scripts/dev.sh --status   # report what is listening
#
# Logs: /tmp/hireshield-backend.log and /tmp/hireshield-frontend.log
# =============================================================================
set -uo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BACKEND_PORT="${BACKEND_PORT:-8000}"
FRONTEND_PORT="${FRONTEND_PORT:-3000}"
BACKEND_LOG="/tmp/hireshield-backend.log"
FRONTEND_LOG="/tmp/hireshield-frontend.log"
PYTHON="$ROOT/backend/.venv/bin/python"

# --- port helpers -----------------------------------------------------------
# `lsof` is not always installed; `ss` is.  Fall back to a plain HTTP probe.
pid_on_port() {
  ss -tlnp 2>/dev/null | grep -o "pid=[0-9]*" | head -1 | cut -d= -f2
}
pid_on_port_for() {
  ss -tlnp 2>/dev/null | grep ":$1 " | grep -o "pid=[0-9]*" | head -1 | cut -d= -f2
}
port_open() { curl -s -o /dev/null --max-time 3 "$1"; }

stop_all() {
  for port in "$BACKEND_PORT" "$FRONTEND_PORT"; do
    pid="$(pid_on_port_for "$port")"
    if [ -n "$pid" ]; then
      echo "  stopping PID $pid on :$port"
      kill "$pid" 2>/dev/null || true
    fi
  done
  sleep 1
}

status() {
  if port_open "http://127.0.0.1:$BACKEND_PORT/health"; then
    echo "  backend  :$BACKEND_PORT  UP    $(curl -s --max-time 3 "http://127.0.0.1:$BACKEND_PORT/health")"
  else
    echo "  backend  :$BACKEND_PORT  DOWN"
  fi
  if port_open "http://127.0.0.1:$FRONTEND_PORT/"; then
    echo "  frontend :$FRONTEND_PORT UP"
  else
    echo "  frontend :$FRONTEND_PORT DOWN"
  fi
}

case "${1:-}" in
  --stop)
    echo "Stopping HireShield-AI dev servers..."
    stop_all
    status
    exit 0
    ;;
  --status)
    status
    exit 0
    ;;
esac

# --- preflight --------------------------------------------------------------
if [ ! -x "$PYTHON" ]; then
  echo "ERROR: backend virtualenv not found at $PYTHON"
  echo "       run: cd backend && python3 -m venv .venv && .venv/bin/pip install -r requirements.txt"
  exit 1
fi

echo "Starting HireShield-AI..."
stop_all

# --- backend ----------------------------------------------------------------
cd "$ROOT/backend"
nohup "$PYTHON" -u -m uvicorn app.main:app --host 0.0.0.0 --port "$BACKEND_PORT" \
  > "$BACKEND_LOG" 2>&1 &
BACKEND_PID=$!

# --- frontend ---------------------------------------------------------------
cd "$ROOT/frontend"
[ -d node_modules ] || { echo "ERROR: frontend/node_modules missing — run: cd frontend && npm install"; exit 1; }
nohup npm run dev -- --port "$FRONTEND_PORT" > "$FRONTEND_LOG" 2>&1 &
FRONTEND_PID=$!

# --- readiness --------------------------------------------------------------
# The backend loads spaCy, ONNX artifacts and MongoDB on startup; it is NOT ready
# the moment the port opens.  Poll /health rather than sleeping a fixed amount.
echo "Waiting for the backend to finish loading models..."
BACKEND_OK=0
for _ in $(seq 1 90); do
  if port_open "http://127.0.0.1:$BACKEND_PORT/health"; then BACKEND_OK=1; break; fi
  if ! kill -0 "$BACKEND_PID" 2>/dev/null; then
    echo "ERROR: backend exited during startup. Last 20 log lines:"
    tail -20 "$BACKEND_LOG"
    exit 1
  fi
  sleep 1
done

echo "Waiting for the frontend dev server..."
FRONTEND_OK=0
for _ in $(seq 1 60); do
  if port_open "http://127.0.0.1:$FRONTEND_PORT/"; then FRONTEND_OK=1; break; fi
  sleep 1
done

echo
status
echo
echo "  logs: $BACKEND_LOG"
echo "        $FRONTEND_LOG"
echo "  stop: ./scripts/dev.sh --stop"
echo

if [ "$BACKEND_OK" -ne 1 ]; then
  echo "The backend did not become healthy on :$BACKEND_PORT."
  echo "A 'NetworkError' in the UI is this problem, not a frontend bug."
  tail -20 "$BACKEND_LOG"
  exit 1
fi
if [ "$FRONTEND_OK" -ne 1 ]; then
  echo "The frontend did not answer on :$FRONTEND_PORT."
  tail -20 "$FRONTEND_LOG"
  exit 1
fi

echo "Both services are up. Open http://localhost:$FRONTEND_PORT/analyze"