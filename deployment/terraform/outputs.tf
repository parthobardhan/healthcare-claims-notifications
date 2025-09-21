output "api_gateway_url" {
  description = "Base URL for API Gateway"
  value       = "https://${aws_api_gateway_rest_api.main.id}.execute-api.${var.aws_region}.amazonaws.com/${var.environment}"
}

output "claims_api_url" {
  description = "Claims API endpoint URL"
  value       = "https://${aws_api_gateway_rest_api.main.id}.execute-api.${var.aws_region}.amazonaws.com/${var.environment}/claims"
}

output "notifications_api_url" {
  description = "Notifications API endpoint URL"
  value       = "https://${aws_api_gateway_rest_api.main.id}.execute-api.${var.aws_region}.amazonaws.com/${var.environment}/notifications"
}

output "claims_lambda_function_name" {
  description = "Claims Lambda function name"
  value       = aws_lambda_function.claims_lambda.function_name
}

output "notifications_lambda_function_name" {
  description = "Notifications Lambda function name"
  value       = aws_lambda_function.notifications_lambda.function_name
}

output "api_gateway_id" {
  description = "API Gateway REST API ID"
  value       = aws_api_gateway_rest_api.main.id
}

output "api_gateway_stage" {
  description = "API Gateway stage name"
  value       = aws_api_gateway_stage.main.stage_name
}
