# Environment Configuration Guide

This guide explains how to configure all environment variables for the Healthcare Claims application, including database URIs, database names, and VAPID keys.

## 🤔 VAPID Keys with DB Credentials: Combined vs Separate?

### **Recommendation: Combined for Development, Separated for Production**

| Approach | Pros | Cons | Best For |
|----------|------|------|----------|
| **Combined** (single .env) | Simple management, fewer files, easier development setup | Mixed security concerns, harder to rotate individually | Development, small teams, prototypes |
| **Separated** (multiple files) | Better security separation, easier credential rotation, granular access control | More complex setup, multiple files to manage | Production, large teams, enterprise |

## 📁 Available Configuration Approaches

### Option 1: Combined Configuration (Recommended for Development)
```bash
# Use: backend/.env
# Contains: DB credentials + VAPID keys + all settings
cp backend/env.example backend/.env
# Edit .env with your values
```

### Option 2: Separated Configuration (Recommended for Production)
```bash
# Use: backend/env.database + backend/env.vapid
# Load both files in your deployment
cp backend/env.database backend/.env.database
cp backend/env.vapid backend/.env.vapid
# Edit both files with your values
```

## 🚀 Quick Setup (Development)

### 1. Copy the example configuration
```bash
cd healthcare-claims/backend
cp env.example .env
```

### 2. Edit your .env file
```bash
# Required: Update your database connection
MONGODB_URI=mongodb+srv://youruser:yourpass@yourcluster.mongodb.net/

# Required: Generate new VAPID keys
node ../generate-vapid-keys.js
# Copy the generated keys to your .env file
```

### 3. Database Configuration Options

#### Option A: Separate Databases (Recommended)
```bash
# Different databases for each service
CLAIMS_DB_NAME=uhg_claims
NOTIFICATIONS_DB_NAME=web_notifications
```

#### Option B: Single Shared Database (Simpler)
```bash
# Same database for both services
DB_NAME=healthcare_claims
# Comment out or remove CLAIMS_DB_NAME and NOTIFICATIONS_DB_NAME
```

## 🔧 Configuration Reference

### Database Variables
| Variable | Description | Default | Example |
|----------|-------------|---------|---------|
| `MONGODB_URI` | MongoDB connection string | `mongodb://localhost:27017` | `mongodb+srv://user:pass@cluster.net/` |
| `CLAIMS_DB_NAME` | Claims service database | `uhg_claims` | `production_claims` |
| `NOTIFICATIONS_DB_NAME` | Notifications database | `web_notifications` | `production_notifications` |
| `DB_NAME` | Shared database (alternative) | - | `healthcare_claims_unified` |

### VAPID Variables
| Variable | Description | Required | Example |
|----------|-------------|----------|---------|
| `VAPID_PUBLIC_KEY` | Public key for push notifications | Yes | `BJN41H6Gq6uE...` |
| `VAPID_PRIVATE_KEY` | Private key for push notifications | Yes | `OOePSDgeONlU...` |
| `VAPID_SUBJECT` | Contact email for push service | Yes | `mailto:admin@company.com` |

### Optional Variables
| Variable | Description | Default |
|----------|-------------|---------|
| `CORS_ORIGINS` | Allowed CORS origins | Auto-detected |
| `ENVIRONMENT` | Environment name | `development` |
| `LOG_LEVEL` | Logging verbosity | `INFO` |

## 🔐 Security Best Practices

### For Development
- ✅ Use the combined `.env` file for simplicity
- ✅ Use default/test VAPID keys for local development
- ✅ Use localhost MongoDB or Atlas free tier
- ⚠️ Never commit `.env` files to version control

### For Production
- ✅ Separate database and VAPID configurations
- ✅ Use environment-specific VAPID keys
- ✅ Rotate credentials regularly
- ✅ Use secrets management systems (AWS Secrets Manager, Azure Key Vault, etc.)
- ✅ Use different databases per environment
- ✅ Monitor and log configuration access

## 🏗️ Advanced: Production Deployment

### Docker Compose Example
```yaml
version: '3.8'
services:
  claims-api:
    environment:
      - MONGODB_URI=${DB_CONNECTION_STRING}
      - CLAIMS_DB_NAME=${CLAIMS_DATABASE}
    env_file:
      - .env.database

  notifications-api:
    environment:
      - MONGODB_URI=${DB_CONNECTION_STRING}
      - NOTIFICATIONS_DB_NAME=${NOTIFICATIONS_DATABASE}
    env_file:
      - .env.database
      - .env.vapid
```

### Kubernetes ConfigMap + Secret Example
```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: healthcare-claims-config
data:
  CLAIMS_DB_NAME: "production_claims"
  NOTIFICATIONS_DB_NAME: "production_notifications"
  ENVIRONMENT: "production"
---
apiVersion: v1
kind: Secret
metadata:
  name: healthcare-claims-secrets
data:
  MONGODB_URI: <base64-encoded-connection-string>
  VAPID_PUBLIC_KEY: <base64-encoded-public-key>
  VAPID_PRIVATE_KEY: <base64-encoded-private-key>
```

## 🧪 Testing Configuration

### Verify Database Connection
```bash
cd backend
source venv/bin/activate
python -c "
import asyncio
from claims.db import get_db
async def test():
    db = await get_db()
    print(f'Connected to: {db.name}')
asyncio.run(test())
"
```

### Verify VAPID Configuration
```bash
curl http://localhost:8000/vapid-public-key
# Should return your public key
```

## 🔄 Migration from Old Configuration

If you have an existing `.env` file, here's how to migrate:

```bash
# 1. Backup existing configuration
cp backend/.env backend/.env.backup

# 2. Update to new format (your current file has been updated automatically)
# The new .env file now supports both CLAIMS_DB_NAME/NOTIFICATIONS_DB_NAME
# and maintains backward compatibility with DB_NAME

# 3. Test the configuration
./start.sh
```

Your services will now use:
- Claims service: `CLAIMS_DB_NAME` (falls back to `DB_NAME`, then `uhg_claims`)
- Notifications service: `NOTIFICATIONS_DB_NAME` (falls back to `DB_NAME`, then `web_notifications`)

## 📞 Troubleshooting

### Database Connection Issues
- ✅ Check `MONGODB_URI` format and credentials
- ✅ Verify network access (IP whitelist for Atlas)
- ✅ Test connection with MongoDB Compass

### VAPID Key Issues
- ✅ Regenerate keys with `node generate-vapid-keys.js`
- ✅ Clear browser notification subscriptions after changing keys
- ✅ Verify keys are base64url encoded (no padding)

### Environment Loading Issues
- ✅ Check `.env` file is in `backend/` directory
- ✅ Verify no extra spaces around `=` signs
- ✅ Check for proper quote handling in multi-word values
