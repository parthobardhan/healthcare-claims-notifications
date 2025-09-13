#!/bin/bash

set -e

cd terraform
API_URL=$(terraform output -raw api_gateway_url 2>/dev/null || echo "")

if [ -z "$API_URL" ]; then
    echo "❌ Error: Could not get API Gateway URL from Terraform output"
    echo "Make sure you have deployed the infrastructure first with ./deploy/deploy.sh"
    exit 1
fi

echo "🧪 Testing Healthcare Claims and Notifications API"
echo "API URL: $API_URL"
echo ""

echo "=== Testing Claims Service ==="

echo "1. Testing Claims Health Check..."
curl -s -w "\nStatus: %{http_code}\n" "$API_URL/claims/health" || echo "❌ Failed"
echo ""

echo "2. Testing Get All Claims..."
curl -s -w "\nStatus: %{http_code}\n" "$API_URL/claims/claims" || echo "❌ Failed"
echo ""

echo "3. Testing Create Claim..."
CLAIM_DATA='{
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
  "notes": "Test claim from Lambda deployment"
}'

CLAIM_RESPONSE=$(curl -s -X POST "$API_URL/claims/claims" \
  -H "Content-Type: application/json" \
  -d "$CLAIM_DATA" \
  -w "\nStatus: %{http_code}\n")

echo "$CLAIM_RESPONSE"
CLAIM_ID=$(echo "$CLAIM_RESPONSE" | jq -r '.id // empty' 2>/dev/null || echo "")
echo ""

if [ -n "$CLAIM_ID" ]; then
    echo "4. Testing Get Specific Claim..."
    curl -s -w "\nStatus: %{http_code}\n" "$API_URL/claims/claims/$CLAIM_ID" || echo "❌ Failed"
    echo ""

    echo "5. Testing Update Claim..."
    UPDATE_DATA='{"status": "adjudicated", "notes": "Updated from Lambda test"}'
    curl -s -X PATCH "$API_URL/claims/claims/$CLAIM_ID" \
      -H "Content-Type: application/json" \
      -d "$UPDATE_DATA" \
      -w "\nStatus: %{http_code}\n" || echo "❌ Failed"
    echo ""
fi

echo "=== Testing Notifications Service ==="

echo "1. Testing Notifications Health Check..."
curl -s -w "\nStatus: %{http_code}\n" "$API_URL/notify/health" || echo "❌ Failed"
echo ""

echo "2. Testing VAPID Public Key..."
curl -s -w "\nStatus: %{http_code}\n" "$API_URL/notify/vapid-public-key" || echo "❌ Failed"
echo ""

echo "3. Testing Get Users..."
curl -s -w "\nStatus: %{http_code}\n" "$API_URL/notify/users" || echo "❌ Failed"
echo ""

echo "4. Testing Get Notifications..."
curl -s -w "\nStatus: %{http_code}\n" "$API_URL/notify/notifications" || echo "❌ Failed"
echo ""

echo "5. Testing Subscribe (mock subscription)..."
SUBSCRIPTION_DATA='{
  "endpoint": "https://fcm.googleapis.com/fcm/send/test-endpoint",
  "keys": {
    "p256dh": "test-p256dh-key",
    "auth": "test-auth-key"
  }
}'

curl -s -X POST "$API_URL/notify/subscribe?member_id=M123" \
  -H "Content-Type: application/json" \
  -d "$SUBSCRIPTION_DATA" \
  -w "\nStatus: %{http_code}\n" || echo "❌ Failed"
echo ""

echo "6. Testing Send Notification..."
NOTIFICATION_DATA='{
  "title": "Test Notification",
  "body": "This is a test notification from Lambda deployment",
  "icon": "/favicon.ico",
  "url": "https://example.com",
  "member_id": "M123"
}'

curl -s -X POST "$API_URL/notify/notify" \
  -H "Content-Type: application/json" \
  -d "$NOTIFICATION_DATA" \
  -w "\nStatus: %{http_code}\n" || echo "❌ Failed"
echo ""

echo "=== Testing CORS ==="
echo "Testing CORS preflight for Claims..."
curl -s -X OPTIONS "$API_URL/claims/claims" \
  -H "Origin: http://localhost:3000" \
  -H "Access-Control-Request-Method: POST" \
  -H "Access-Control-Request-Headers: Content-Type" \
  -w "\nStatus: %{http_code}\n" || echo "❌ Failed"
echo ""

echo "Testing CORS preflight for Notifications..."
curl -s -X OPTIONS "$API_URL/notify/notify" \
  -H "Origin: http://localhost:3000" \
  -H "Access-Control-Request-Method: POST" \
  -H "Access-Control-Request-Headers: Content-Type" \
  -w "\nStatus: %{http_code}\n" || echo "❌ Failed"
echo ""

echo "✅ API testing complete!"
echo ""
echo "🔗 Your API endpoints:"
echo "  Claims Service: $API_URL/claims"
echo "  Notifications Service: $API_URL/notify"
