# Healthcare Claims - VAPID Keys Configuration

## Generated VAPID Keys (Development)

The following VAPID keys were generated specifically for the Healthcare Claims app:

```
Public Key:  BDMDBW7Xk4LErBOYtpIxdROk7gtr40VIY6r_aWYbjwP3l4Nu04yaBfcABCwYS87PO69sXyLJ1l9oHo6RrqkZNRs
Private Key: m9aQf2oTdusZgFIV9JZtEN8aukNQ4zYOD2tcwQIiBjw
Subject:     mailto:admin@healthcareclaims.com
```

## Environment Variables Setup

For production deployment, set these environment variables:

```bash
export VAPID_PUBLIC_KEY="BDMDBW7Xk4LErBOYtpIxdROk7gtr40VIY6r_aWYbjwP3l4Nu04yaBfcABCwYS87PO69sXyLJ1l9oHo6RrqkZNRs"
export VAPID_PRIVATE_KEY="m9aQf2oTdusZgFIV9JZtEN8aukNQ4zYOD2tcwQIiBjw"
export VAPID_SUBJECT="mailto:admin@healthcareclaims.com"
```

## Docker/Container Setup

If using Docker, add to your Dockerfile or docker-compose.yml:

```yaml
environment:
  - VAPID_PUBLIC_KEY=BDMDBW7Xk4LErBOYtpIxdROk7gtr40VIY6r_aWYbjwP3l4Nu04yaBfcABCwYS87PO69sXyLJ1l9oHo6RrqkZNRs
  - VAPID_PRIVATE_KEY=m9aQf2oTdusZgFIV9JZtEN8aukNQ4zYOD2tcwQIiBjw
  - VAPID_SUBJECT=mailto:admin@healthcareclaims.com
```

## Security Notes

⚠️ **Important**:
- Keep the private key secret and secure
- Use different VAPID keys for different environments (dev, staging, prod)
- Never commit VAPID private keys to version control
- Consider using a secrets management system for production

## Testing

To test the VAPID configuration:

1. **Check Public Key**: `curl http://localhost:8000/vapid-public-key`
2. **Send Test Notification**: Visit http://localhost:4201/ and use the notification test button
3. **Backend Test**: `curl -X POST http://localhost:8000/notify -H "Content-Type: application/json" -d '{"title": "Test", "body": "Hello!"}'`

## Troubleshooting

If notifications aren't working:
1. Verify VAPID keys are set correctly
2. Clear browser subscriptions and re-subscribe
3. Check browser console for Service Worker errors
4. Ensure notification permissions are granted
