#!/usr/bin/env bash
# Simple startup for healthcare-claims stack
# Starts: claims backend (8080), notify backend (8000), adjuster FE (4200), patient FE (4201)

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
  # Ensure venv and deps
  if [[ ! -f "venv/bin/activate" ]]; then
    python3 -m venv venv
  fi
  # shellcheck disable=SC1091
  source venv/bin/activate
  pip install -q -r requirements.txt || true
  pip install -q cryptography || true
  if [[ -f ".env" ]]; then
    # export key=value pairs from .env (ignore comments)
    export $(grep -v '^#' .env | xargs) || true
  fi
  # Use venv python to run uvicorn
  ./venv/bin/python -m uvicorn claims.app:app --host 127.0.0.1 --port 8080 --log-level warning &
  PIDS+=("$!")
  popd >/dev/null
}

start_notify_backend() {
  echo "[notify-backend] starting on :8000"
  pushd "$SCRIPT_DIR/backend" >/dev/null
  # Ensure venv and deps
  if [[ ! -f "venv/bin/activate" ]]; then
    python3 -m venv venv
  fi
  # shellcheck disable=SC1091
  source venv/bin/activate
  pip install -q -r requirements.txt || true
  pip install -q cryptography || true
  if [[ -f ".env" ]]; then
    export $(grep -v '^#' .env | xargs) || true
  fi
  ./venv/bin/python -m uvicorn notify.app:app --host 127.0.0.1 --port 8000 --log-level warning &
  PIDS+=("$!")
  popd >/dev/null
}

start_adjuster_fe() {
  echo "[adjuster-fe] starting static app on :4200"
  pushd "$SCRIPT_DIR/frontend/adjuster" >/dev/null
  python3 -m http.server 4200 --bind 0.0.0.0 &
  PIDS+=("$!")
  popd >/dev/null
}

start_patient_fe() {
  echo "[patient-fe] starting static app on :4201"
  pushd "$SCRIPT_DIR/frontend/patient" >/dev/null
  python3 -m http.server 4201 --bind 0.0.0.0 &
  PIDS+=("$!")
  popd >/dev/null
}


seed_claims_data() {
  echo "[seed] seeding claims data into MongoDB localhost"
  pushd "$SCRIPT_DIR/backend" >/dev/null
  if [[ ! -f "venv/bin/activate" ]]; then
    python3 -m venv venv
  fi
  # shellcheck disable=SC1091
  source venv/bin/activate
  # Ensure required deps (uvicorn and cryptography) are present
  pip install -q -r requirements.txt || true
  pip install -q cryptography || true
  python scripts/seed_claims.py --reset --count 20 || echo "[seed] WARNING: Seeding failed (is MongoDB running on localhost:27017?)"
  popd >/dev/null
}

# --- run all ---
start_claims_backend
start_notify_backend
seed_claims_data
start_adjuster_fe
start_patient_fe

echo
echo "All services started (background)."
echo "- Claims API:      http://localhost:8080/health"
echo "- Notify API:      http://localhost:8000/health"
echo "- Adjuster Portal: http://localhost:4200/"
echo "- Patient Portal:  http://localhost:4201/"
echo

# Keep script running while children are alive
wait
