
resource "aws_sqs_queue" "resume_processing_dlq" {
  name                      = "${var.project_name}-${var.environment}-resume-processing-dlq"
  message_retention_seconds = 1209600

  lifecycle {
    prevent_destroy = true
  }
}

resource "aws_sqs_queue" "resume_processing" {
  name                       = "${var.project_name}-${var.environment}-resume-processing"
  visibility_timeout_seconds = 300
  message_retention_seconds  = 345600
  receive_wait_time_seconds  = 20

  redrive_policy = jsonencode({
    deadLetterTargetArn = aws_sqs_queue.resume_processing_dlq.arn
    maxReceiveCount     = 3
  })

  lifecycle {
    prevent_destroy = true
  }
}
