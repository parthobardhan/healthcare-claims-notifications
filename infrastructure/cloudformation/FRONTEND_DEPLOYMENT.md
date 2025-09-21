# Frontend Deployment to AWS

This document describes the AWS deployment setup for the Healthcare Claims frontend applications.

## Architecture

- **S3 Buckets**: Static hosting for both adjuster and patient portals
- **CloudFront**: CDN distributions for global content delivery and HTTPS
- **API Gateway**: Backend APIs (already deployed via Terraform)

## Deployment

Run the deployment script from the project root:

```bash
./deploy-aws.sh
```

This script will:
1. Create S3 buckets for both frontends
2. Configure static website hosting
3. Apply public read bucket policies
4. Upload frontend files
5. Create CloudFront distributions

## Manual Deployment Steps

If you prefer to deploy manually:

### 1. Create S3 Buckets
```bash
aws s3 mb s3://healthcare-claims-adjuster-portal --region us-east-2
aws s3 mb s3://healthcare-claims-patient-portal --region us-east-2
```

### 2. Configure Static Website Hosting
```bash
aws s3 website s3://healthcare-claims-adjuster-portal --index-document index.html --error-document index.html
aws s3 website s3://healthcare-claims-patient-portal --index-document index.html --error-document index.html
```

### 3. Apply Bucket Policies
```bash
aws s3api put-bucket-policy --bucket healthcare-claims-adjuster-portal --policy file://aws/s3-bucket-policy-adjuster.json
aws s3api put-bucket-policy --bucket healthcare-claims-patient-portal --policy file://aws/s3-bucket-policy-patient.json
```

### 4. Upload Files
```bash
aws s3 sync frontend/adjuster/ s3://healthcare-claims-adjuster-portal/ --delete
aws s3 sync frontend/patient/ s3://healthcare-claims-patient-portal/ --delete
```

### 5. Create CloudFront Distributions
```bash
aws cloudfront create-distribution --distribution-config file://aws/cloudfront-distribution-adjuster.json
aws cloudfront create-distribution --distribution-config file://aws/cloudfront-distribution-patient.json
```

## Configuration Files

- `s3-bucket-policy-adjuster.json` - Public read policy for adjuster portal bucket
- `s3-bucket-policy-patient.json` - Public read policy for patient portal bucket
- `cloudfront-distribution-adjuster.json` - CloudFront configuration for adjuster portal
- `cloudfront-distribution-patient.json` - CloudFront configuration for patient portal

## API Endpoints

The frontends are configured to use the following API Gateway endpoints:
- Claims API: `https://0uxz97szlj.execute-api.us-east-2.amazonaws.com/dev/claims`
- Notification API: `https://0uxz97szlj.execute-api.us-east-2.amazonaws.com/dev/notify`

**Note**: Currently the API endpoints return 404 errors for the main endpoints (health checks work). This suggests the Lambda functions may not be deployed with the correct route paths. The frontend deployment is complete but API connectivity needs to be resolved.

## PWA Support

The patient portal includes PWA functionality with a service worker (`sw.js`) that supports:
- Push notifications
- Offline capability
- App installation

The service worker is deployed to the root of the patient portal bucket to ensure proper PWA functionality.

## Monitoring

Use AWS CloudWatch to monitor:
- S3 bucket access logs
- CloudFront distribution metrics
- API Gateway request metrics

## Cleanup

To remove all AWS resources:
```bash
# Delete CloudFront distributions (get IDs first)
aws cloudfront list-distributions
aws cloudfront delete-distribution --id <DISTRIBUTION_ID> --if-match <ETAG>

# Empty and delete S3 buckets
aws s3 rm s3://healthcare-claims-adjuster-portal --recursive
aws s3 rm s3://healthcare-claims-patient-portal --recursive
aws s3 rb s3://healthcare-claims-adjuster-portal
aws s3 rb s3://healthcare-claims-patient-portal
```
