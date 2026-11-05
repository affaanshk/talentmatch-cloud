resource "aws_s3_bucket" "resumes" {
  bucket        = "talentmatch-resumes-local"
  force_destroy = false
}

resource "aws_s3_bucket_public_access_block" "resumes" {
  bucket                  = aws_s3_bucket.resumes.id
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_s3_bucket_server_side_encryption_configuration" "resumes" {
  bucket = aws_s3_bucket.resumes.id
  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

resource "aws_sqs_queue" "resume_dlq" {
  name                      = "talentmatch-local-resume-processing-dlq"
  message_retention_seconds = 1209600
}


resource "aws_sqs_queue" "resume_processing" {
  name                       = "talentmatch-local-resume-processing"
  visibility_timeout_seconds = 300
  message_retention_seconds  = 345600
  receive_wait_time_seconds  = 20

  redrive_policy = jsonencode({
    deadLetterTargetArn = aws_sqs_queue.resume_dlq.arn
    maxReceiveCount     = 3
  })
}

