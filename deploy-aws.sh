#!/usr/bin/env bash

set -euo pipefail

SCRIPT_DIR="$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"
REGION="us-east-2"

echo "🚀 Deploying Healthcare Claims frontends to AWS..."

echo "📦 Creating S3 buckets..."
aws s3 mb s3://healthcare-claims-adjuster-portal --region $REGION || echo "Bucket may already exist"
aws s3 mb s3://healthcare-claims-patient-portal --region $REGION || echo "Bucket may already exist"

echo "🌐 Configuring static website hosting..."
aws s3 website s3://healthcare-claims-adjuster-portal --index-document index.html --error-document index.html
aws s3 website s3://healthcare-claims-patient-portal --index-document index.html --error-document index.html

echo "🔓 Applying bucket policies..."
aws s3api put-bucket-policy --bucket healthcare-claims-adjuster-portal --policy file://$SCRIPT_DIR/aws/s3-bucket-policy-adjuster.json
aws s3api put-bucket-policy --bucket healthcare-claims-patient-portal --policy file://$SCRIPT_DIR/aws/s3-bucket-policy-patient.json

echo "📤 Uploading adjuster portal..."
aws s3 sync $SCRIPT_DIR/frontend/adjuster/ s3://healthcare-claims-adjuster-portal/ --delete

echo "📤 Uploading patient portal..."
aws s3 sync $SCRIPT_DIR/frontend/patient/ s3://healthcare-claims-patient-portal/ --delete

echo "☁️ Creating CloudFront distributions..."
ADJUSTER_DIST_ID=$(aws cloudfront create-distribution --distribution-config file://$SCRIPT_DIR/aws/cloudfront-distribution-adjuster.json --query 'Distribution.Id' --output text)
PATIENT_DIST_ID=$(aws cloudfront create-distribution --distribution-config file://$SCRIPT_DIR/aws/cloudfront-distribution-patient.json --query 'Distribution.Id' --output text)

echo "✅ Deployment complete!"
echo ""
echo "📋 Deployment Summary:"
echo "  Adjuster Portal S3:        http://healthcare-claims-adjuster-portal.s3-website.us-east-2.amazonaws.com"
echo "  Patient Portal S3:         http://healthcare-claims-patient-portal.s3-website.us-east-2.amazonaws.com"
echo "  Adjuster CloudFront ID:    $ADJUSTER_DIST_ID"
echo "  Patient CloudFront ID:     $PATIENT_DIST_ID"
echo ""
echo "⏳ CloudFront distributions are being deployed (this may take 10-15 minutes)."
echo "   Use 'aws cloudfront get-distribution --id <DIST_ID>' to check status."
echo ""
echo "🔗 Once deployed, access your applications at:"
echo "   Adjuster Portal: https://<adjuster-domain>.cloudfront.net"
echo "   Patient Portal:  https://<patient-domain>.cloudfront.net"
