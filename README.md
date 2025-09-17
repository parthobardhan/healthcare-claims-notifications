# Healthcare Claims Demo

A comprehensive end-to-end healthcare claims management system featuring a FastAPI backend with MongoDB Atlas and two lightweight React frontends. The system includes real-time push notifications for claim status updates.

## Architecture Overview
- **Backend Services**: Claims API + Notification API (integrated FastAPI services)
- **Frontend Portals**: Adjuster Portal (claim management) + Patient Portal (claim viewing)
- **Real-time Notifications**: Web Push notifications for claim status updates
- **Database**: MongoDB Atlas with separate collections for claims and notifications

## Technology Stack
- **Backend**: Python 3.11+, FastAPI 0.112+, Motor (MongoDB), Pydantic v2, Uvicorn
- **Frontend**: React 18 (CDN) + Ant Design 5.19+ (static serving via Python HTTP server)
- **Database**: MongoDB Atlas (or local MongoDB)
- **Notifications**: Web Push API with VAPID keys, pywebpush
- **Testing**: pytest + pytest-asyncio

## Project Structure
```
healthcare-claims/
├── backend/                     # Backend services
│   ├── claims/                  # Claims API service
│   ├── notify/                  # Push notification service
│   ├── scripts/                 # Utility scripts (data seeding)
│   ├── tests/                   # Test suite
│   ├── requirements.txt         # Python dependencies
│   └── env.example             # Environment configuration template
├── frontend/                    # Frontend applications
│   ├── adjuster/               # Adjuster portal (static React)
│   └── patient/                # Patient portal (static React + Service Worker)
├── start.sh                    # One-command startup script
├── generate-vapid-keys.js      # VAPID key generation utility
├── package.json               # Node.js dependencies (VAPID keys)
├── ENVIRONMENT_CONFIGURATION.md # Comprehensive environment setup guide
└── test-claim-update-notification.md # Notification testing guide
```

## Prerequisites
- **Python 3.11+** installed with pip
- **Node.js** (for VAPID key generation)
- **MongoDB Atlas** account with connection string OR local MongoDB instance
- **Modern web browser** with push notification support

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

Create `backend/.env` with your configuration:

```bash
# Copy from template and customize
cp backend/env.example backend/.env

# Edit .env with your MongoDB details:
MONGODB_URI=mongodb+srv://<user>:<pass>@<cluster>/?retryWrites=true&w=majority
CLAIMS_DB_NAME=uhg_claims
NOTIFICATIONS_DB_NAME=web_notifications
```

📋 **See [ENVIRONMENT_CONFIGURATION.md](ENVIRONMENT_CONFIGURATION.md) for detailed environment setup options including VAPID keys management.**

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

### Environment Configuration (`healthcare-claims/backend/.env`)
```bash
# Database configuration
MONGODB_URI=mongodb+srv://<user>:<pass>@<cluster>/?retryWrites=true&w=majority
CLAIMS_DB_NAME=uhg_claims
NOTIFICATIONS_DB_NAME=web_notifications

# VAPID keys for push notifications
VAPID_PUBLIC_KEY=your_public_key
VAPID_PRIVATE_KEY=your_private_key
VAPID_SUBJECT=mailto:admin@yourcompany.com

# Optional: CORS_ORIGINS=http://localhost:4200,http://localhost:4201
```

📋 **For complete configuration options, security best practices, and production deployment guidance, see [ENVIRONMENT_CONFIGURATION.md](ENVIRONMENT_CONFIGURATION.md).**

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

### Common Issues

**Command not found errors:**
- `uvicorn: command not found` → Activate virtualenv: `source backend/venv/bin/activate`
- `node: command not found` → Install Node.js for VAPID key generation

**Database Connection:**
- Connection timeout → Check `MONGODB_URI` format and network access
- Authentication failed → Verify username/password in connection string
- IP access denied → Add your IP to Atlas IP Access List
- Wrong database → Verify `CLAIMS_DB_NAME` and `NOTIFICATIONS_DB_NAME` settings

**Service Startup:**
- Ports in use (4200/4201/8000/8080) → Kill existing processes or change ports
- Dependencies missing → Run `pip install -r requirements.txt` in activated venv
- Environment variables → Check `.env` file exists and has correct format

**Push Notifications:**
- Notifications not working → Regenerate VAPID keys with `node generate-vapid-keys.js`
- CORS errors → Update `CORS_ORIGINS` in `.env` file
- Service worker issues → Clear browser cache and re-register

**Frontend Issues:**
- UI not loading → Check browser console for CDN errors (antd, React)
- API calls failing → Verify backend services are running on correct ports
- Static files not served → Ensure `python -m http.server` is running in correct directories

### Debug Commands
```bash
# Check service health
curl http://localhost:8080/health  # Claims API
curl http://localhost:8000/health  # Notify API

# Test database connection
cd backend && source venv/bin/activate
python -c "import asyncio; from claims.db import get_db; print('DB OK')"

# Verify VAPID configuration
curl http://localhost:8000/vapid-public-key
```

## Project Status & Roadmap

### Current Status
This is a **development-ready demo** suitable for:
- Local development and testing
- Learning healthcare claims workflow patterns
- Prototyping push notification features
- Demonstrating full-stack integration

### Production Considerations
For production deployment, consider implementing:
- **Security**: Authentication/authorization, input validation, rate limiting
- **Database**: Proper indexing, schema governance, connection pooling
- **Infrastructure**: Docker containerization, load balancing, monitoring
- **CI/CD**: Automated testing, code quality checks, deployment pipelines
- **Compliance**: HIPAA compliance measures, audit logging, data encryption

## Development Guidelines

### Code Quality
```bash
# Run linting (if ruff is installed)
ruff check .
ruff format --check .

# Run tests
cd backend && source venv/bin/activate && pytest -q
```

### Development Workflow
1. Make changes to backend code
2. Services auto-reload with `--reload` flag
3. Test API changes via frontend portals
4. Use browser dev tools to debug notification flow
5. Check `backend/backend.log` for service logs

## License
For demo purposes only. Replace or add a license file as appropriate for your usage.
