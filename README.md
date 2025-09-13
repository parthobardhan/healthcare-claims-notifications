# Healthcare Claims Demo

A small end-to-end demo showing a healthcare claims API (FastAPI + MongoDB Atlas) and two lightweight frontends (Adjuster and Patient) built with React over CDN. It also integrates with a companion Web Notification service for push notifications.

## Stack
- Backend: Python 3.10+, FastAPI, Motor (MongoDB), Pydantic v2, Uvicorn
- Frontends: Static React (served via `python -m http.server`) + Ant Design over CDN
- Notifications: FastAPI service under `backend/notify`
- Database: MongoDB Atlas

## Repository layout
- `backend/` — FastAPI services (claims and notify) and tests
- `frontend/`
  - `adjuster/` — Adjuster portal (static React)
  - `patient/` — Patient portal (static React + Service Worker consumption)
- `generate-vapid-keys.js` — Node.js utility to generate VAPID keys for push notifications
- `package.json` — Node.js dependencies for VAPID key generation
- `start.sh` — Convenience script to start claims API, notification API, and both frontends
- `VAPID_KEYS.md` — Documentation for VAPID key configuration
- `test-claim-update-notification.md` — Testing guide for the notification flow

## Prerequisites
- Python 3.10+ installed
- Node.js (needed to generate VAPID keys for notifications)
- A MongoDB Atlas connection string with user/password and network access allowed (or a local MongoDB for testing)

## Quick start (development)

### 1) Install Node.js dependencies (for VAPID keys)
Install the required Node.js dependencies for VAPID key generation:

```bash
cd healthcare-claims
npm install
```

### 2) Configure and install the Claims Backend
Create a virtualenv, install dependencies, and add a `.env`:

```bash
cd backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

Create `backend/.env` with your MongoDB details:

```bash
MONGODB_URI=mongodb+srv://<user>:<pass>@<cluster>/?retryWrites=true&w=majority
DB_NAME=uhg_claims
```

### 3) Configure the Notification Backend (integrated)
The notification service now lives under `backend/notify` and runs from the same virtualenv as claims. By default, it looks for VAPID PEM keys under `backend/notify/public_key.pem` and `backend/notify/private_key.pem`.

Optionally, you can set environment variables in `backend/.env` instead of PEMs:

```bash
# backend/.env
# Mongo (notify uses the same MONGODB_URI unless overridden)
MONGODB_URI=mongodb+srv://<user>:<pass>@<cluster>/?retryWrites=true&w=majority
DB_NAME=web_notifications

# VAPID (optional if PEMs are present under backend/notify)
VAPID_PUBLIC_KEY=<your-public-key>
VAPID_PRIVATE_KEY=<your-private-key>
# Optional: allow specific origins (comma-separated)
# CORS_ORIGINS=http://localhost:4200,http://localhost:4201
```

#### VAPID Key Generation
This project includes a convenient Node.js utility to generate VAPID keys:

```bash
# Install dependencies (one-time)
npm install

# Generate new VAPID keys
node generate-vapid-keys.js
```

Alternatively, use web-push directly:
```bash
npx web-push generate-vapid-keys
```

See `VAPID_KEYS.md` for detailed configuration instructions.

### 4) Start everything with one command
From `healthcare-claims` directory:

```bash
./start.sh
```

This will start:
- Claims API on http://localhost:8080 (health at `/health`)
- Notify API on http://localhost:8000 (health at `/health`)
- Adjuster portal (static) on http://localhost:4200
- Patient portal (static) on http://localhost:4201

Press Ctrl+C in that terminal to stop all.

### 5) Seed sample claims data (optional but recommended)
In a separate terminal:

```bash
cd healthcare-claims/backend
source venv/bin/activate
python scripts/seed_claims.py --reset --count 20
```

This creates 20 mock claims with realistic statuses and amounts in your DB.

## Run services manually (alternative to start.sh)

### Claims API
```bash
cd healthcare-claims/backend
source venv/bin/activate
uvicorn claims.app:app --reload --host 0.0.0.0 --port 8080
```

### Notification API
```bash
cd healthcare-claims/backend
source venv/bin/activate
uvicorn notify.app:app --reload --host 0.0.0.0 --port 8000
```

### Frontends (static)
- Adjuster portal:
  ```bash
  cd healthcare-claims/frontend/adjuster
  python3 -m http.server 4200 --bind 0.0.0.0
  ```
- Patient portal:
  ```bash
  cd healthcare-claims/frontend/patient
  python3 -m http.server 4201 --bind 0.0.0.0
  ```

## Testing the notification flow
See `test-claim-update-notification.md` for a detailed guide on testing the complete claim update notification workflow between the adjuster and patient portals.

## Environment variables

### Claims backend (`healthcare-claims/backend/.env`)
```bash
MONGODB_URI=...
DB_NAME=uhg_claims
```

### Notification backend (env via `healthcare-claims/backend/.env`)
```bash
MONGODB_URI=...
DB_NAME=web_notifications
# Either set VAPID env vars (below) or place PEMs under backend/notify
VAPID_PUBLIC_KEY=...
VAPID_PRIVATE_KEY=...
# Optional: CORS_ORIGINS=...
```

## How to run tests (backend)
The claims backend includes pytest-based tests.

```bash
cd healthcare-claims/backend
source venv/bin/activate
pytest -q
```

Notes:
- Tests expect `MONGODB_URI` to be set (Atlas or local).
- They automatically use a test database name (`uhg_claims_test`) and clean up after running.

## API overview (claims backend)
- `GET    /health`                → `{ "status": "ok" }`
- `POST   /claims`                → create a claim
- `GET    /claims`                → list (up to 200, newest first)
- `GET    /claims/{id}`           → get by id
- `PATCH  /claims/{id}`           → partial update
- `DELETE /claims/{id}`           → delete

## Troubleshooting
- uvicorn: command not found
  - Activate the correct virtualenv (`source venv/bin/activate`) where you installed requirements.
- MongoDB connection errors
  - Verify `MONGODB_URI` in your `.env` and that your Atlas IP Access List includes your IP. Check `DB_NAME`.
- CORS issues
  - Dev configs allow localhost origins by default. If needed, set `CORS_ORIGINS` in the notification backend `.env`.
- Ports already in use (4200/4201/8000/8080)
  - Stop any other process using those ports or edit the commands to use different ports.

## Project status
This is a demo meant for local exploration. For production hardening, consider:
- Authn/z, request validation, rate limiting
- Indexes and schema governance in MongoDB
- CI for tests and linting
- Dockerization and a unified compose for all services

## License
For demo purposes only. Replace or add a license file as appropriate for your usage.
