variable "aws_region" {
  description = "AWS region for deployment"
  type        = string
  default     = "us-east-2"
}

variable "mongodb_uri" {
  description = "MongoDB connection URI"
  type        = string
  sensitive   = true
}

variable "vapid_public_key" {
  description = "VAPID public key for web push notifications"
  type        = string
  default     = "BDMDBW7Xk4LErBOYtpIxdROk7gtr40VIY6r_aWYbjwP3l4Nu04yaBfcABCwYS87PO69sXyLJ1l9oHo6RrqkZNRs"
}

variable "vapid_private_key" {
  description = "VAPID private key for web push notifications"
  type        = string
  sensitive   = true
  default     = "m9aQf2oTdusZgFIV9JZtEN8aukNQ4zYOD2tcwQIiBjw"
}

variable "vapid_subject" {
  description = "VAPID subject for web push notifications"
  type        = string
  default     = "mailto:admin@healthcareclaims.com"
}

variable "cors_origins" {
  description = "CORS allowed origins"
  type        = string
  default     = "http://localhost:4300,http://127.0.0.1:4300,http://localhost:4400,http://127.0.0.1:4400,http://localhost:5173,http://127.0.0.1:5173,http://localhost:8000"
}

variable "environment" {
  description = "Environment name"
  type        = string
  default     = "dev"
}
