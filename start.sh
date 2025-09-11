#!/usr/bin/env bash
# Simple startup for healthcare-claims stack
# Starts: claims backend (8080), notify backend (8000), adjuster FE (4200), customer FE (4201)

set -euo pipefail

SCRIPT_DIR="$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"
REPO_ROOT="$( cd -- "${SCRIPT_DIR}/.." &> /dev/null && pwd )"

PIDS=()

cleanup() {
  echo
  echo "Shutting down..."
  for pid in "${PIDS[@]:-}"; do
    if kill -0 "$pid" >/dev/null 2>&1; then
      kill "$pid" >/dev/null 2>&1 || true
    fi
  done
  wait || true
}
trap cleanup EXIT INT TERM

start_claims_backend() {
  echo "[claims-backend] starting on :8080"
  pushd "$SCRIPT_DIR/backend" >/dev/null
  if [[ -f "venv/bin/activate" ]]; then
    # shellcheck disable=SC1091
    source venv/bin/activate
  fi
  if [[ -f ".env" ]]; then
    # export key=value pairs from .env (ignore comments)
    export $(grep -v '^#' .env | xargs) || true
  fi
  uvicorn claims.app:app --reload --host 0.0.0.0 --port 8080 &
  PIDS+=("$!")
  popd >/dev/null
}

start_notify_backend() {
  echo "[notify-backend] starting on :8000"
  pushd "$SCRIPT_DIR/backend" >/dev/null
  if [[ -f "venv/bin/activate" ]]; then
    # shellcheck disable=SC1091
    source venv/bin/activate
  fi
  if [[ -f ".env" ]]; then
    export $(grep -v '^#' .env | xargs) || true
  fi
  uvicorn notify.app:app --reload --host 0.0.0.0 --port 8000 &
  PIDS+=("$!")
  popd >/dev/null
}

start_adjuster_fe() {
  echo "[adjuster-fe] starting static React app on :4200"
  pushd "$SCRIPT_DIR/frontend/adjuster-react" >/dev/null
  python3 -m http.server 4200 --bind 0.0.0.0 &
  PIDS+=("$!")
  popd >/dev/null
}

start_customer_fe() {
  echo "[customer-fe] starting static React app on :4201"
  pushd "$SCRIPT_DIR/frontend/customer-react" >/dev/null
  python3 -m http.server 4201 --bind 0.0.0.0 &
  PIDS+=("$!")
  popd >/dev/null
}

# --- run all ---
start_claims_backend
start_notify_backend
start_adjuster_fe
start_customer_fe

echo
echo "All services started (background)."
echo "- Claims API:      http://localhost:8080/health"
echo "- Notify API:      http://localhost:8000/health"
echo "- Adjuster Portal: http://localhost:4200/"
echo "- Customer Portal: http://localhost:4201/"
echo

# Keep script running while children are alive
wait

