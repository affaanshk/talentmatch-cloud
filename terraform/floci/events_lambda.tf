data "archive_file" "completion_lambda" {
  type        = "zip"
  source_file = "${path.module}/lambda_handler.py"
  output_path = "${path.module}/completion_lambda.zip"
}

resource "aws_cloudwatch_log_group" "completion_lambda" {
  name              = "/aws/lambda/talentmatch-resume-completed-local"
  retention_in_days = 7
}

resource "aws_iam_role" "completion_lambda" {
  name = "talentmatch-completion-lambda-local-role"
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect    = "Allow"
      Principal = { Service = "lambda.amazonaws.com" }
      Action    = "sts:AssumeRole"
    }]
  })
}

resource "aws_iam_role_policy" "completion_lambda_logs" {
  name = "talentmatch-completion-lambda-logs-local"
  role = aws_iam_role.completion_lambda.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect = "Allow"
      Action = [
        "logs:CreateLogStream",
        "logs:PutLogEvents"
      ]
      Resource = "${aws_cloudwatch_log_group.completion_lambda.arn}:*"
    }]
  })
}


resource "aws_iam_role_policy" "completion_lambda_dynamodb" {
  name = "talentmatch-completion-lambda-dynamodb-local"
  role = aws_iam_role.completion_lambda.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect   = "Allow"
      Action   = ["dynamodb:PutItem"]
      Resource = aws_dynamodb_table.resume_audit.arn
    }]
  })
}

resource "aws_lambda_function" "completion" {
  function_name    = "talentmatch-resume-completed-local"
  role             = aws_iam_role.completion_lambda.arn
  handler          = "lambda_handler.handler"
  runtime          = "python3.11"
  filename         = data.archive_file.completion_lambda.output_path
  source_code_hash = data.archive_file.completion_lambda.output_base64sha256
  depends_on = [
    aws_iam_role_policy.completion_lambda_logs,
    aws_iam_role_policy.completion_lambda_dynamodb
  ]

  environment {
    variables = {
      AUDIT_TABLE_NAME      = aws_dynamodb_table.resume_audit.name
      DYNAMODB_ENDPOINT_URL = "http://host.docker.internal:4566"
      AWS_DEFAULT_REGION    = "us-east-1"
    }
  }

}

resource "aws_cloudwatch_event_rule" "resume_completed" {
  name           = "talentmatch-resume-completed-local"
  description    = "Route completed resume-processing events to the completion Lambda."
  event_bus_name = "default"
  event_pattern = jsonencode({
    source        = ["talentmatch.resume"]
    "detail-type" = ["Resume Processing Completed"]
  })
}

resource "aws_cloudwatch_event_target" "completion_lambda" {
  rule           = aws_cloudwatch_event_rule.resume_completed.name
  event_bus_name = "default"
  target_id      = "talentmatch-completion-lambda"
  arn            = aws_lambda_function.completion.arn
}

resource "aws_lambda_permission" "allow_eventbridge" {
  statement_id  = "AllowExecutionFromEventBridge"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.completion.function_name
  principal     = "events.amazonaws.com"
  source_arn    = aws_cloudwatch_event_rule.resume_completed.arn
}
