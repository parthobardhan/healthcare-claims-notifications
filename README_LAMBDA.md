# AWS Lambda Deployment

This document describes the AWS Lambda deployment setup for the Healthcare Claims and Notifications services.

## Architecture

The deployment consists of:
- **2 Lambda Functions**: One for Claims service, one for Notifications service
- **API Gateway**: Single API with path-based routing (`/claims/*` and `/notify/*`)
- **Terraform Infrastructure**: Infrastructure as Code for reproducible deployments

## Prerequisites

1. AWS CLI configured with appropriate permissions
2. Terraform installed (>= 1.0)
3. MongoDB Atlas or compatible MongoDB instance
4. Python 3.12

## Environment Variables

### Claims Service
- `MONGODB_URI`: MongoDB connection string
- `DB_NAME`: Database name (default: `uhg_claims`)
- `NOTIFY_SERVICE_URL`: URL of the notifications service (auto-configured)

### Notifications Service
- `MONGODB_URI`: MongoDB connection string
- `DB_NAME`: Database name (default: `web_notifications`)
- `VAPID_PUBLIC_KEY`: VAPID public key for web push notifications
- `VAPID_PRIVATE_KEY`: VAPID private key for web push notifications
- `VAPID_SUBJECT`: VAPID subject (default: `mailto:admin@healthcareclaims.com`)
- `CORS_ORIGINS`: Comma-separated list of allowed CORS origins

## Deployment

1. **Set MongoDB URI**:
   ```bash
   export MONGODB_URI="mongodb+srv://user:pass@cluster.mongodb.net/?retryWrites=true&w=majority"
   ```

2. **Deploy infrastructure**:
   ```bash
   ./deploy/deploy.sh
   ```

3. **Test endpoints**:
   ```bash
   ./test_endpoints.sh
   ```

## API Endpoints

### Claims Service (`/claims`)
- `GET /claims/health` - Health check
- `POST /claims/claims` - Create new claim
- `GET /claims/claims` - List all claims
- `GET /claims/claims/{id}` - Get specific claim
- `PATCH /claims/claims/{id}` - Update claim
- `DELETE /claims/claims/{id}` - Delete claim

### Notifications Service (`/notify`)
- `GET /notify/health` - Health check
- `GET /notify/vapid-public-key` - Get VAPID public key
- `POST /notify/subscribe` - Subscribe to notifications
- `POST /notify/notify` - Send notification
- `GET /notify/users` - List users
- `GET /notify/notifications` - List notifications

## Testing

The `test_endpoints.sh` script provides comprehensive testing of all endpoints:

```bash
# Test all endpoints
./test_endpoints.sh

# Test specific service
curl https://your-api-id.execute-api.us-east-2.amazonaws.com/dev/claims/health
curl https://your-api-id.execute-api.us-east-2.amazonaws.com/dev/notify/health
```

## Monitoring

- CloudWatch logs are automatically created for both Lambda functions
- Log retention is set to 14 days
- Function names:
  - `healthcare-claims-service-dev`
  - `healthcare-notify-service-dev`

## CORS Configuration

CORS is configured at both levels:
1. **FastAPI middleware**: Handles CORS for direct Lambda invocation
2. **API Gateway**: Handles CORS preflight requests

Allowed origins can be configured via the `CORS_ORIGINS` environment variable.

## Cleanup

To destroy the infrastructure:

```bash
cd terraform
terraform destroy
```

## Troubleshooting

1. **Lambda timeout errors**: Increase timeout in `terraform/lambda.tf`
2. **Memory errors**: Increase memory_size in `terraform/lambda.tf`
3. **CORS issues**: Check both FastAPI middleware and API Gateway CORS configuration
4. **Database connection issues**: Verify MongoDB URI and network access
