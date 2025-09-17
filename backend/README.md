# Healthcare Claims Backend Services

## Architecture
This backend contains two integrated FastAPI services:
- **Claims Service** (`claims/`) - Main healthcare claims CRUD API
- **Notification Service** (`notify/`) - Web push notification service

## Technology Stack
- **Framework**: FastAPI 0.112+
- **Database**: MongoDB Atlas (via Motor async driver)
- **Validation**: Pydantic v2
- **Server**: Uvicorn with auto-reload
- **Push Notifications**: pywebpush with VAPID keys
- **Testing**: pytest + pytest-asyncio

## Quick Start
1. **Environment Setup**:
   ```bash
   cp env.example .env
   # Edit .env with your MongoDB URI and VAPID keys
   ```

2. **Install Dependencies**:
   ```bash
   python -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   ```

3. **Start Services**:
   ```bash
   # Claims API (port 8080)
   uvicorn claims.app:app --reload --host 0.0.0.0 --port 8080

   # Notification API (port 8000)
   uvicorn notify.app:app --reload --host 0.0.0.0 --port 8000
   ```

## API Reference

### Claims Service (`:8080`)
- `GET /health` → Service health check
- `POST /claims` → Create new claim
- `GET /claims` → List all claims (newest first, limit 200)
- `GET /claims/{id}` → Get specific claim
- `PATCH /claims/{id}` → Update claim (triggers notifications on status change)
- `DELETE /claims/{id}` → Delete claim

### Notification Service (`:8000`)
- `GET /health` → Service health check
- `GET /vapid-public-key` → Get VAPID public key for frontend
- `POST /subscribe` → Register push notification subscription
- `POST /notify` → Send push notification (supports member targeting)
- `GET /users` → List registered users and subscriptions
- `GET /notifications` → List sent notifications
- `GET /deliveries` → List notification delivery records

## Database Collections
- `claims` - Healthcare claim records
- `users` - User push notification subscriptions
- `notifications` - Notification history
- `deliveries` - Notification delivery tracking

## Configuration
Environment variables are loaded from `.env` file:
- `MONGODB_URI` - MongoDB connection string
- `CLAIMS_DB_NAME` / `NOTIFICATIONS_DB_NAME` - Database names
- `VAPID_PUBLIC_KEY` / `VAPID_PRIVATE_KEY` - Push notification keys
- `VAPID_SUBJECT` - Contact email for push service

See `env.example` and `../ENVIRONMENT_CONFIGURATION.md` for detailed setup.

## Development
- Services auto-reload on code changes with `--reload` flag
- Run tests: `pytest -q`
- Seed sample data: `python scripts/seed_claims.py --reset --count 20`
- All MongoDB ObjectIds are converted to strings in API responses
