resource "aws_dynamodb_table" "resume_events" {
  name         = "${var.project_name}-${var.environment}-resume-events"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "upload_id"
  attribute {
    name = "upload_id"
    type = "S"
  }
  point_in_time_recovery { enabled = true }
  server_side_encryption { enabled = true }
  tags = var.tags
}
