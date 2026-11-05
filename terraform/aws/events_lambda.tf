resource "aws_cloudwatch_log_group" "completion_lambda" {
  name              = "/aws/lambda/${var.project_name}-${var.environment}-resume-completed"
  retention_in_days = 14
  tags              = var.tags
}
data "archive_file" "completion_lambda" {
  type        = "zip"
  source_file = "${path.module}/lambda_handler.py"
  output_path = "${path.module}/lambda_handler.zip"
}
resource "aws_iam_role" "lambda" {
  name               = "${var.project_name}-${var.environment}-completion-lambda-role"
  assume_role_policy = jsonencode({ Version = "2012-10-17", Statement = [{ Effect = "Allow", Principal = { Service = "lambda.amazonaws.com" }, Action = "sts:AssumeRole" }] })
  tags               = var.tags
}
resource "aws_iam_role_policy" "lambda_dynamodb" {
  name   = "write-resume-event-records"
  role   = aws_iam_role.lambda.id
  policy = jsonencode({ Version = "2012-10-17", Statement = [{ Effect = "Allow", Action = ["dynamodb:PutItem"], Resource = aws_dynamodb_table.resume_events.arn }] })
}
resource "aws_iam_role_policy" "lambda_logs" {
  name   = "write-own-cloudwatch-logs"
  role   = aws_iam_role.lambda.id
  policy = jsonencode({ Version = "2012-10-17", Statement = [{ Effect = "Allow", Action = ["logs:CreateLogStream", "logs:PutLogEvents"], Resource = "${aws_cloudwatch_log_group.completion_lambda.arn}:*" }] })
}
resource "aws_lambda_function" "resume_completed" {
  function_name    = "${var.project_name}-${var.environment}-resume-completed"
  role             = aws_iam_role.lambda.arn
  runtime          = "python3.12"
  handler          = "lambda_handler.handler"
  filename         = data.archive_file.completion_lambda.output_path
  source_code_hash = data.archive_file.completion_lambda.output_base64sha256
  timeout          = 15
  memory_size      = 128
  environment {
    variables = { DYNAMODB_TABLE_NAME = aws_dynamodb_table.resume_events.name }
  }
  depends_on = [aws_iam_role_policy.lambda_logs, aws_iam_role_policy.lambda_dynamodb, aws_cloudwatch_log_group.completion_lambda]
  tags       = var.tags
}
resource "aws_cloudwatch_event_rule" "resume_completed" {
  name          = "${var.project_name}-${var.environment}-resume-completed"
  description   = "Route TalentMatch resume completion events to Lambda"
  event_pattern = jsonencode({ source = ["talentmatch.resume"], "detail-type" = ["Resume Processing Completed"] })
  tags          = var.tags
}
resource "aws_cloudwatch_event_target" "completion_lambda" {
  rule      = aws_cloudwatch_event_rule.resume_completed.name
  target_id = "resume-completion-handler"
  arn       = aws_lambda_function.resume_completed.arn
}
resource "aws_lambda_permission" "eventbridge_invoke" {
  statement_id  = "AllowEventBridgeResumeCompleted"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.resume_completed.function_name
  principal     = "events.amazonaws.com"
  source_arn    = aws_cloudwatch_event_rule.resume_completed.arn
}
