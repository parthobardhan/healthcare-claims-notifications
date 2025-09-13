
resource "aws_iam_role" "lambda_execution_role" {
  name = "healthcare-lambda-execution-role-${var.environment}"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "lambda.amazonaws.com"
        }
      }
    ]
  })
}

resource "aws_iam_role_policy_attachment" "lambda_basic_execution" {
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
  role       = aws_iam_role.lambda_execution_role.name
}

resource "aws_lambda_function" "claims_service" {
  filename         = "claims_lambda.zip"
  function_name    = "healthcare-claims-service-${var.environment}"
  role            = aws_iam_role.lambda_execution_role.arn
  handler         = "claims.lambda_handler.lambda_handler"
  source_code_hash = filebase64sha256("claims_lambda.zip")
  runtime         = "python3.12"
  timeout         = 30
  memory_size     = 512

  environment {
    variables = {
      MONGODB_URI         = var.mongodb_uri
      DB_NAME            = "uhg_claims"
      NOTIFY_SERVICE_URL = "https://${aws_api_gateway_rest_api.healthcare_api.id}.execute-api.${var.aws_region}.amazonaws.com/${var.environment}"
    }
  }

  depends_on = [
    aws_iam_role_policy_attachment.lambda_basic_execution,
  ]
}

resource "aws_lambda_function" "notify_service" {
  filename         = "notify_lambda.zip"
  function_name    = "healthcare-notify-service-${var.environment}"
  role            = aws_iam_role.lambda_execution_role.arn
  handler         = "notify.lambda_handler.lambda_handler"
  source_code_hash = filebase64sha256("notify_lambda.zip")
  runtime         = "python3.12"
  timeout         = 30
  memory_size     = 512

  environment {
    variables = {
      MONGODB_URI       = var.mongodb_uri
      DB_NAME          = "web_notifications"
      VAPID_PUBLIC_KEY = var.vapid_public_key
      VAPID_PRIVATE_KEY = var.vapid_private_key
      VAPID_SUBJECT    = var.vapid_subject
      CORS_ORIGINS     = var.cors_origins
    }
  }

  depends_on = [
    aws_iam_role_policy_attachment.lambda_basic_execution,
  ]
}


resource "aws_lambda_permission" "claims_api_gateway" {
  statement_id  = "AllowExecutionFromAPIGateway"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.claims_service.function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${aws_api_gateway_rest_api.healthcare_api.execution_arn}/*/*"
}

resource "aws_lambda_permission" "notify_api_gateway" {
  statement_id  = "AllowExecutionFromAPIGateway"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.notify_service.function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${aws_api_gateway_rest_api.healthcare_api.execution_arn}/*/*"
}
