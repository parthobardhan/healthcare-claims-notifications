output "api_gateway_url" {
  description = "API Gateway URL"
  value       = "https://${aws_api_gateway_rest_api.healthcare_api.id}.execute-api.${var.aws_region}.amazonaws.com/${aws_api_gateway_deployment.healthcare_deployment.stage_name}"
}

output "claims_lambda_function_name" {
  description = "Claims Lambda function name"
  value       = aws_lambda_function.claims_service.function_name
}

output "notify_lambda_function_name" {
  description = "Notifications Lambda function name"
  value       = aws_lambda_function.notify_service.function_name
}

output "claims_service_url" {
  description = "Claims service URL"
  value       = "https://${aws_api_gateway_rest_api.healthcare_api.id}.execute-api.${var.aws_region}.amazonaws.com/${aws_api_gateway_deployment.healthcare_deployment.stage_name}/claims"
}

output "notify_service_url" {
  description = "Notifications service URL"
  value       = "https://${aws_api_gateway_rest_api.healthcare_api.id}.execute-api.${var.aws_region}.amazonaws.com/${aws_api_gateway_deployment.healthcare_deployment.stage_name}/notify"
}
