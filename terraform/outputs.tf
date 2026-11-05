
output "resume_processing_queue_url" {
  description = "URL of the resume-processing SQS queue"
  value       = aws_sqs_queue.resume_processing.url
}

output "resume_processing_dlq_url" {
  description = "URL of the resume-processing dead-letter queue"
  value       = aws_sqs_queue.resume_processing_dlq.url
}
