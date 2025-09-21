# AWS Configuration
aws_region = "us-east-2"
environment = "dev"
project_name = "healthcare-claims"

# Database Configuration
mongodb_uri = "mongodb+srv://psb:passw0rd@garage-week.o9q0k.mongodb.net/?retryWrites=true&w=majority&appName=Garage-week"
claims_db_name = "uhg_claims"
notifications_db_name = "web_notifications"

# VAPID Configuration for Push Notifications
vapid_public_key = "BJN41H6Gq6uEkXrs8-zMNtDmdF13IlrtUro861EZJVpCJkrIJUTbjhnHsAvqsS1R2srVtck3rjMnbENgNOPx5JU"
vapid_private_key = "OOePSDgeONlU9txtdoC8hv8tD9EpYzmWbZi-czqFW3I"
vapid_subject = "mailto:you@example.com"

# CORS Configuration
cors_origins = "https://localhost:4200,https://localhost:4201,https://yourdomain.com,https://d2i8inlb41h30r.cloudfront.net,https://d1s8iivd1nt95u.cloudfront.net"

# Lambda Package Paths (relative to terraform directory)
claims_lambda_zip_path = "../build/claims-lambda.zip"
notifications_lambda_zip_path = "../build/notifications-lambda.zip"
