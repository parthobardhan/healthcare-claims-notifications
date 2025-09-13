#!/bin/bash

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TERRAFORM_DIR="$SCRIPT_DIR/../terraform"

MONGODB_URI="${MONGODB_URI:-}"
ENVIRONMENT="${ENVIRONMENT:-dev}"

if [ -z "$MONGODB_URI" ]; then
    echo "❌ Error: MONGODB_URI environment variable is required"
    echo "Usage: MONGODB_URI='your-mongodb-uri' ./deploy.sh"
    exit 1
fi

echo "🚀 Deploying Healthcare Claims and Notifications to AWS Lambda..."
echo "   Environment: $ENVIRONMENT"
echo "   Region: us-east-2"

echo "📦 Packaging Lambda functions..."
"$SCRIPT_DIR/package_lambda.sh"

cd "$TERRAFORM_DIR"
if [ ! -d ".terraform" ]; then
    echo "🔧 Initializing Terraform..."
    terraform init
fi

echo "📋 Planning Terraform deployment..."
terraform plan \
    -var="mongodb_uri=$MONGODB_URI" \
    -var="environment=$ENVIRONMENT" \
    -out=tfplan

echo "🚀 Applying Terraform deployment..."
terraform apply tfplan

echo "✅ Deployment complete!"
echo ""
echo "📊 Deployment Information:"
terraform output -json | jq -r '
  "API Gateway URL: " + .api_gateway_url.value,
  "Claims Service URL: " + .claims_service_url.value,
  "Notify Service URL: " + .notify_service_url.value,
  "",
  "Lambda Functions:",
  "  - " + .claims_lambda_function_name.value,
  "  - " + .notify_lambda_function_name.value
'

echo ""
echo "🧪 Test your deployment with:"
echo "curl \$(terraform output -raw api_gateway_url)/claims/health"
echo "curl \$(terraform output -raw api_gateway_url)/notify/health"
