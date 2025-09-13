resource "aws_api_gateway_rest_api" "healthcare_api" {
  name        = "healthcare-api-${var.environment}"
  description = "Healthcare Claims and Notifications API"

  endpoint_configuration {
    types = ["REGIONAL"]
  }
}

resource "aws_api_gateway_resource" "claims" {
  rest_api_id = aws_api_gateway_rest_api.healthcare_api.id
  parent_id   = aws_api_gateway_rest_api.healthcare_api.root_resource_id
  path_part   = "claims"
}

resource "aws_api_gateway_resource" "claims_proxy" {
  rest_api_id = aws_api_gateway_rest_api.healthcare_api.id
  parent_id   = aws_api_gateway_resource.claims.id
  path_part   = "{proxy+}"
}

resource "aws_api_gateway_method" "claims_proxy" {
  rest_api_id   = aws_api_gateway_rest_api.healthcare_api.id
  resource_id   = aws_api_gateway_resource.claims_proxy.id
  http_method   = "ANY"
  authorization = "NONE"
}

resource "aws_api_gateway_method" "claims_root" {
  rest_api_id   = aws_api_gateway_rest_api.healthcare_api.id
  resource_id   = aws_api_gateway_resource.claims.id
  http_method   = "ANY"
  authorization = "NONE"
}

resource "aws_api_gateway_integration" "claims_proxy" {
  rest_api_id = aws_api_gateway_rest_api.healthcare_api.id
  resource_id = aws_api_gateway_resource.claims_proxy.id
  http_method = aws_api_gateway_method.claims_proxy.http_method

  integration_http_method = "POST"
  type                   = "AWS_PROXY"
  uri                    = aws_lambda_function.claims_service.invoke_arn
}

resource "aws_api_gateway_integration" "claims_root" {
  rest_api_id = aws_api_gateway_rest_api.healthcare_api.id
  resource_id = aws_api_gateway_resource.claims.id
  http_method = aws_api_gateway_method.claims_root.http_method

  integration_http_method = "POST"
  type                   = "AWS_PROXY"
  uri                    = aws_lambda_function.claims_service.invoke_arn
}

resource "aws_api_gateway_resource" "notify" {
  rest_api_id = aws_api_gateway_rest_api.healthcare_api.id
  parent_id   = aws_api_gateway_rest_api.healthcare_api.root_resource_id
  path_part   = "notify"
}

resource "aws_api_gateway_resource" "notify_proxy" {
  rest_api_id = aws_api_gateway_rest_api.healthcare_api.id
  parent_id   = aws_api_gateway_resource.notify.id
  path_part   = "{proxy+}"
}

resource "aws_api_gateway_method" "notify_proxy" {
  rest_api_id   = aws_api_gateway_rest_api.healthcare_api.id
  resource_id   = aws_api_gateway_resource.notify_proxy.id
  http_method   = "ANY"
  authorization = "NONE"
}

resource "aws_api_gateway_method" "notify_root" {
  rest_api_id   = aws_api_gateway_rest_api.healthcare_api.id
  resource_id   = aws_api_gateway_resource.notify.id
  http_method   = "ANY"
  authorization = "NONE"
}

resource "aws_api_gateway_integration" "notify_proxy" {
  rest_api_id = aws_api_gateway_rest_api.healthcare_api.id
  resource_id = aws_api_gateway_resource.notify_proxy.id
  http_method = aws_api_gateway_method.notify_proxy.http_method

  integration_http_method = "POST"
  type                   = "AWS_PROXY"
  uri                    = aws_lambda_function.notify_service.invoke_arn
}

resource "aws_api_gateway_integration" "notify_root" {
  rest_api_id = aws_api_gateway_rest_api.healthcare_api.id
  resource_id = aws_api_gateway_resource.notify.id
  http_method = aws_api_gateway_method.notify_root.http_method

  integration_http_method = "POST"
  type                   = "AWS_PROXY"
  uri                    = aws_lambda_function.notify_service.invoke_arn
}

resource "aws_api_gateway_method" "claims_options" {
  rest_api_id   = aws_api_gateway_rest_api.healthcare_api.id
  resource_id   = aws_api_gateway_resource.claims_proxy.id
  http_method   = "OPTIONS"
  authorization = "NONE"
}

resource "aws_api_gateway_integration" "claims_options" {
  rest_api_id = aws_api_gateway_rest_api.healthcare_api.id
  resource_id = aws_api_gateway_resource.claims_proxy.id
  http_method = aws_api_gateway_method.claims_options.http_method
  type        = "MOCK"

  request_templates = {
    "application/json" = "{\"statusCode\": 200}"
  }
}

resource "aws_api_gateway_method_response" "claims_options" {
  rest_api_id = aws_api_gateway_rest_api.healthcare_api.id
  resource_id = aws_api_gateway_resource.claims_proxy.id
  http_method = aws_api_gateway_method.claims_options.http_method
  status_code = "200"

  response_parameters = {
    "method.response.header.Access-Control-Allow-Headers" = true
    "method.response.header.Access-Control-Allow-Methods" = true
    "method.response.header.Access-Control-Allow-Origin"  = true
  }
}

resource "aws_api_gateway_integration_response" "claims_options" {
  rest_api_id = aws_api_gateway_rest_api.healthcare_api.id
  resource_id = aws_api_gateway_resource.claims_proxy.id
  http_method = aws_api_gateway_method.claims_options.http_method
  status_code = aws_api_gateway_method_response.claims_options.status_code

  response_parameters = {
    "method.response.header.Access-Control-Allow-Headers" = "'Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token'"
    "method.response.header.Access-Control-Allow-Methods" = "'GET,OPTIONS,POST,PUT,PATCH,DELETE'"
    "method.response.header.Access-Control-Allow-Origin"  = "'*'"
  }
}

resource "aws_api_gateway_method" "notify_options" {
  rest_api_id   = aws_api_gateway_rest_api.healthcare_api.id
  resource_id   = aws_api_gateway_resource.notify_proxy.id
  http_method   = "OPTIONS"
  authorization = "NONE"
}

resource "aws_api_gateway_integration" "notify_options" {
  rest_api_id = aws_api_gateway_rest_api.healthcare_api.id
  resource_id = aws_api_gateway_resource.notify_proxy.id
  http_method = aws_api_gateway_method.notify_options.http_method
  type        = "MOCK"

  request_templates = {
    "application/json" = "{\"statusCode\": 200}"
  }
}

resource "aws_api_gateway_method_response" "notify_options" {
  rest_api_id = aws_api_gateway_rest_api.healthcare_api.id
  resource_id = aws_api_gateway_resource.notify_proxy.id
  http_method = aws_api_gateway_method.notify_options.http_method
  status_code = "200"

  response_parameters = {
    "method.response.header.Access-Control-Allow-Headers" = true
    "method.response.header.Access-Control-Allow-Methods" = true
    "method.response.header.Access-Control-Allow-Origin"  = true
  }
}

resource "aws_api_gateway_integration_response" "notify_options" {
  rest_api_id = aws_api_gateway_rest_api.healthcare_api.id
  resource_id = aws_api_gateway_resource.notify_proxy.id
  http_method = aws_api_gateway_method.notify_options.http_method
  status_code = aws_api_gateway_method_response.notify_options.status_code

  response_parameters = {
    "method.response.header.Access-Control-Allow-Headers" = "'Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token'"
    "method.response.header.Access-Control-Allow-Methods" = "'GET,OPTIONS,POST,PUT,PATCH,DELETE'"
    "method.response.header.Access-Control-Allow-Origin"  = "'*'"
  }
}

resource "aws_api_gateway_deployment" "healthcare_deployment" {
  depends_on = [
    aws_api_gateway_integration.claims_proxy,
    aws_api_gateway_integration.claims_root,
    aws_api_gateway_integration.notify_proxy,
    aws_api_gateway_integration.notify_root,
  ]

  rest_api_id = aws_api_gateway_rest_api.healthcare_api.id
  stage_name  = var.environment

  triggers = {
    redeployment = sha1(jsonencode([
      aws_api_gateway_resource.claims.id,
      aws_api_gateway_resource.claims_proxy.id,
      aws_api_gateway_resource.notify.id,
      aws_api_gateway_resource.notify_proxy.id,
      aws_api_gateway_method.claims_root.id,
      aws_api_gateway_method.claims_proxy.id,
      aws_api_gateway_method.notify_root.id,
      aws_api_gateway_method.notify_proxy.id,
      aws_api_gateway_integration.claims_root.id,
      aws_api_gateway_integration.claims_proxy.id,
      aws_api_gateway_integration.notify_root.id,
      aws_api_gateway_integration.notify_proxy.id,
    ]))
  }

  lifecycle {
    create_before_destroy = true
  }
}
