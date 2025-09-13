variable "aws_region" {
  description = "AWS region for deployment"
  type        = string
  default     = "us-east-2"
}

variable "environment" {
  description = "Environment name (dev, staging, prod)"
  type        = string
  default     = "dev"
}

variable "project_name" {
  description = "Project name for resource naming"
  type        = string
  default     = "healthcare-claims"
}

variable "mongodb_uri" {
  description = "MongoDB connection URI"
  type        = string
  sensitive   = true
}

variable "claims_db_name" {
  description = "Claims database name"
  type        = string
  default     = "uhg_claims"
}

variable "notifications_db_name" {
  description = "Notifications database name"
  type        = string
  default     = "web_notifications"
}

variable "vapid_public_key" {
  description = "VAPID public key for push notifications"
  type        = string
  sensitive   = true
}

variable "vapid_private_key" {
  description = "VAPID private key for push notifications"
  type        = string
  sensitive   = true
}

variable "vapid_subject" {
  description = "VAPID subject for push notifications"
  type        = string
  default     = "mailto:admin@healthcare-claims.com"
}

variable "cors_origins" {
  description = "Comma-separated list of allowed CORS origins"
  type        = string
  default     = "https://localhost:4200,https://localhost:4201"
}

variable "claims_lambda_zip_path" {
  description = "Path to claims Lambda deployment package"
  type        = string
  default     = "../build/claims-lambda.zip"
}

variable "notifications_lambda_zip_path" {
  description = "Path to notifications Lambda deployment package"
  type        = string
  default     = "../build/notifications-lambda.zip"
}
