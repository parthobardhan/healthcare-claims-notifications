# Healthcare Claims and Notifications - AWS Lambda Deployment

This directory contains the infrastructure and deployment scripts for deploying the Healthcare Claims and Notifications FastAPI applications to AWS Lambda with API Gateway.

## Architecture

- **Claims Service**: FastAPI application deployed as AWS Lambda function
- **Notifications Service**: FastAPI application deployed as AWS Lambda function  
- **API Gateway**: REST API with path-based routing to Lambda functions
- **Path Stripping**: Custom Mangum wrapper strips API Gateway stage prefixes
- **CORS**: Configured for cross-origin requests from frontend applications

## Prerequisites

1. **AWS CLI configured** with appropriate credentials
2. **Terraform** installed (>= 1.0)
3. **Python 3.12** and pip
4. **MongoDB Atlas** connection string
5. **VAPID keys** for push notifications

## Environment Variables

The following environment variables need to be configured:

### Required
- `MONGODB_URI`: MongoDB connection string
- `VAPID_PUBLIC_KEY`: VAPID public key for push notifications
- `VAPID_PRIVATE_KEY`: VAPID private key for push notifications

### Optional
- `CLAIMS_DB_NAME`: Claims database name (default: "uhg_claims")
- `NOTIFICATIONS_DB_NAME`: Notifications database name (default: "web_notifications")
- `VAPID_SUBJECT`: VAPID subject email (default: "mailto:admin@healthcare-claims.com")
- `CORS_ORIGINS`: Comma-separated allowed origins (default: localhost origins)

## Deployment Steps

### 1. Generate VAPID Keys (if needed)

```bash
cd ../../
node generate-vapid-keys.js
```

### 2. Package Lambda Functions

```bash
cd deployment/scripts
chmod +x package_lambda.sh
./package_lambda.sh
```

This creates deployment packages:
- `deployment/build/claims-lambda.zip`
- `deployment/build/notifications-lambda.zip`

### 3. Configure Terraform Variables

```bash
cd deployment/terraform
cp terraform.tfvars.example terraform.tfvars
# Edit terraform.tfvars with your values
```

### 4. Deploy Infrastructure

```bash
cd deployment/terraform
terraform init
terraform plan
terraform apply
```

### 5. Get API Endpoints

```bash
terraform output
```

## API Endpoints

After deployment, the following endpoints will be available:

### Claims Service
- **Base URL**: `https://{api-gateway-id}.execute-api.{region}.amazonaws.com/dev/claims`
- **Health Check**: `GET /dev/claims/health`
- **List Claims**: `GET /dev/claims/claims`
- **Create Claim**: `POST /dev/claims/claims`
- **Get Claim**: `GET /dev/claims/claims/{claim_id}`
- **Update Claim**: `PATCH /dev/claims/claims/{claim_id}`
- **Delete Claim**: `DELETE /dev/claims/claims/{claim_id}`

### Notifications Service
- **Base URL**: `https://{api-gateway-id}.execute-api.{region}.amazonaws.com/dev/notifications`
- **Health Check**: `GET /dev/notifications/health`
- **VAPID Public Key**: `GET /dev/notifications/vapid-public-key`
- **Subscribe**: `POST /dev/notifications/subscribe`
- **Send Notification**: `POST /dev/notifications/notify`
- **List Users**: `GET /dev/notifications/users`
- **List Notifications**: `GET /dev/notifications/notifications`
- **List Deliveries**: `GET /dev/notifications/deliveries`

## Testing with cURL

### Health Checks

```bash
# Claims health check
curl -X GET "https://{api-gateway-id}.execute-api.{region}.amazonaws.com/dev/claims/health"

# Notifications health check  
curl -X GET "https://{api-gateway-id}.execute-api.{region}.amazonaws.com/dev/notifications/health"
```

### Claims CRUD Operations

```bash
# Create a claim
curl -X POST "https://{api-gateway-id}.execute-api.{region}.amazonaws.com/dev/claims/claims" \
  -H "Content-Type: application/json" \
  -d '{
    "member_id": "M123",
    "provider_id": "P456", 
    "service_date": "2025-09-01",
    "received_date": "2025-09-02",
    "diagnosis_codes": ["E11.9"],
    "procedure_codes": ["99213"],
    "amount_billed": 120.0,
    "amount_allowed": 100.0,
    "amount_paid": 80.0,
    "status": "submitted",
    "notes": "Test claim"
  }'

# List claims
curl -X GET "https://{api-gateway-id}.execute-api.{region}.amazonaws.com/dev/claims/claims"

# Update claim status
curl -X PATCH "https://{api-gateway-id}.execute-api.{region}.amazonaws.com/dev/claims/claims/{claim_id}" \
  -H "Content-Type: application/json" \
  -d '{"status": "paid"}'
```

### Notifications Operations

```bash
# Get VAPID public key
curl -X GET "https://{api-gateway-id}.execute-api.{region}.amazonaws.com/dev/notifications/vapid-public-key"

# Subscribe to notifications
curl -X POST "https://{api-gateway-id}.execute-api.{region}.amazonaws.com/dev/notifications/subscribe" \
  -H "Content-Type: application/json" \
  -d '{
    "endpoint": "https://fcm.googleapis.com/fcm/send/...",
    "keys": {
      "p256dh": "key_data",
      "auth": "auth_data"
    }
  }' \
  -G -d "member_id=M123"

# Send notification
curl -X POST "https://{api-gateway-id}.execute-api.{region}.amazonaws.com/dev/notifications/notify" \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Test Notification",
    "body": "This is a test notification",
    "member_id": "M123"
  }'
```

## Path Stripping Implementation

The Lambda handlers implement custom path stripping to handle API Gateway stage prefixes:

- API Gateway receives: `/dev/claims/health`
- Lambda handler strips: `/dev/claims` → `/health`
- FastAPI processes: `/health`

This ensures FastAPI routes work correctly with API Gateway stage paths.

## CORS Configuration

CORS is configured at both levels:
1. **FastAPI Level**: Using CORSMiddleware with environment-based origins
2. **API Gateway Level**: OPTIONS methods with proper CORS headers

## Security Notes

- Terraform state files (`*.tfstate`) are excluded from git commits
- Environment variables containing secrets are marked as sensitive
- VAPID keys should be rotated regularly
- MongoDB connection strings should use strong authentication

## Troubleshooting

### Common Issues

1. **Lambda Import Errors**: Ensure all dependencies are included in deployment package
2. **Path Not Found**: Verify API Gateway routing and Lambda path stripping
3. **CORS Errors**: Check both FastAPI and API Gateway CORS configuration
4. **MongoDB Connection**: Verify connection string and network access
5. **VAPID Errors**: Ensure valid VAPID keys are configured

### Logs

View Lambda function logs:
```bash
aws logs describe-log-groups --log-group-name-prefix "/aws/lambda/healthcare-claims"
aws logs tail "/aws/lambda/healthcare-claims-dev-claims" --follow
aws logs tail "/aws/lambda/healthcare-claims-dev-notifications" --follow
```

## Cleanup

To destroy the infrastructure:

```bash
cd deployment/terraform
terraform destroy
```

## Development vs Production

For production deployments:
- Use separate Terraform workspaces or state files
- Configure proper CORS origins (no wildcards)
- Use AWS Secrets Manager for sensitive variables
- Enable API Gateway logging and monitoring
- Set up proper IAM policies with least privilege
- Configure custom domain names
- Enable AWS WAF for API protection
