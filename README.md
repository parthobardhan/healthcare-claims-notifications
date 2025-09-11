Healthcare Claims Demo

A small end-to-end demo showing a healthcare claims API (FastAPI + MongoDB Atlas) and two lightweight frontends (Adjuster and Customer) built with React over CDN. It also integrates with a companion Web Notification service for push notifications.

Stack
- Backend: Python 3.10+, FastAPI, Motor (MongoDB), Pydantic v2, Uvicorn
- Frontends: Static React (served via python http.server) + Ant Design over CDN
- Notifications: Separate FastAPI service in ../web-notification (same repo)
- Database: MongoDB Atlas

Repository layout
- backend/        FastAPI claims service and tests
- frontend/
  - adjuster-react/  Adjuster portal (static React)
  - customer-react/  Customer portal (static React + Service Worker consumption)
  - claims-portal/   Optional Angular workspace with sample apps (alternative UI)
- start.sh        Convenience script to start claims API, notification API, and both frontends

Prerequisites
- Python 3.10+ installed
- Node.js (only needed if you want to generate VAPID keys for notifications or run the optional Angular UI)
- A MongoDB Atlas connection string with user/password and network access allowed (or a local MongoDB for testing)

Quick start (development)
1) Configure and install the Claims Backend
   - Create an environment file and a virtualenv, then install dependencies:
     cd healthcare-claims/backend
     python -m venv venv
     source venv/bin/activate
     pip install -r requirements.txt
   - Create backend/.env with your MongoDB details:
     MONGODB_URI=mongodb+srv://<user>:<pass>@<cluster>/?retryWrites=true&w=majority
     DB_NAME=uhg_claims

2) Configure and install the Notification Backend (companion service)
   - From repository root:
     cd web-notification/backend
     python -m venv venv
     source venv/bin/activate
     pip install -r requirements.txt
   - Generate VAPID keys (one-time) using web-push (requires Node):
     npx web-push generate-vapid-keys
     # Copy the public/private keys it prints and add them to .env
   - Create web-notification/backend/.env:
     MONGODB_URI=mongodb+srv://<user>:<pass>@<cluster>/?retryWrites=true&w=majority
     DB_NAME=notifications
     VAPID_PUBLIC_KEY=<from generate-vapid-keys>
     VAPID_PRIVATE_KEY=<from generate-vapid-keys>
     # Optional: allow specific origins (comma-separated); localhost is broadly allowed by default
     # CORS_ORIGINS=http://localhost:4200,http://localhost:4201

3) Start everything with one command
   - From healthcare-claims directory:
     ./start.sh
   - This will start:
     - Claims API on http://localhost:8080 (health at /health)
     - Notify API on http://localhost:8000 (health at /health)
     - Adjuster portal (static) on http://localhost:4200
     - Customer portal (static) on http://localhost:4201
   - Press Ctrl+C in that terminal to stop all.

4) Seed sample claims data (optional but recommended)
   - In a separate terminal:
     cd healthcare-claims/backend
     source venv/bin/activate
     python scripts/seed_claims.py --reset --count 20
   - This creates 20 mock claims with realistic statuses and amounts in your DB.

Run services manually (alternative to start.sh)
- Claims API
  cd healthcare-claims/backend
  source venv/bin/activate
  uvicorn app.main:app --reload --host 0.0.0.0 --port 8080

- Notification API (companion)
  cd web-notification/backend
  source venv/bin/activate
  uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

- Frontends (static)
  - Adjuster portal:  cd healthcare-claims/frontend/adjuster-react && python3 -m http.server 4200 --bind 0.0.0.0
  - Customer portal:  cd healthcare-claims/frontend/customer-react && python3 -m http.server 4201 --bind 0.0.0.0

Optional Angular UI (alternative)
- There is an Angular workspace in frontend/claims-portal with sample apps for adjuster and customer.
  cd healthcare-claims/frontend/claims-portal
  npm install
  npm run start_adjuster  # serves the adjuster app
  npm run start_customer  # serves the customer app
- Ports and paths may conflict with the static servers above; run either the static or Angular version, not both on the same port.

Environment variables
- Claims backend (healthcare-claims/backend/.env)
  MONGODB_URI=...
  DB_NAME=uhg_claims

- Notification backend (web-notification/backend/.env)
  MONGODB_URI=...
  DB_NAME=notifications
  VAPID_PUBLIC_KEY=...
  VAPID_PRIVATE_KEY=...
  # Optional: CORS_ORIGINS=...

How to run tests (backend)
- The claims backend includes pytest-based tests.
  cd healthcare-claims/backend
  source venv/bin/activate
  pytest -q
- Notes:
  - Tests expect MONGODB_URI to be set (Atlas or local). They automatically use a test database name (uhg_claims_test) and clean up after running.

API overview (claims backend)
- GET    /health                -> {"status":"ok"}
- POST   /claims                -> create a claim
- GET    /claims                -> list (up to 200, newest first)
- GET    /claims/{id}           -> get by id
- PATCH  /claims/{id}           -> partial update
- DELETE /claims/{id}           -> delete

Troubleshooting
- uvicorn: command not found
  - Activate the correct virtualenv (source venv/bin/activate) where you installed requirements.
- MongoDB connection errors
  - Verify MONGODB_URI in your .env and that your Atlas IP Access List includes your IP. Check DB_NAME.
- CORS issues
  - Dev configs allow localhost origins by default. If needed, set CORS_ORIGINS in the notification backend .env.
- Ports already in use (4200/4201/8000/8080)
  - Stop any other process using those ports or edit the commands to use different ports.

Project status
- This is a demo meant for local exploration. For production hardening, consider:
  - Authn/z, request validation, rate limiting
  - Indexes and schema governance in MongoDB
  - CI for tests and linting
  - Dockerization and a unified compose for all services

License
- For demo purposes only. Replace or add a license file as appropriate for your usage.

