output "s3_bucket_name" {
  value = aws_s3_bucket.resumes.bucket
}

output "sqs_queue_url" {
  value = aws_sqs_queue.resume_processing.url
}

output "sqs_dlq_url" {
  value = aws_sqs_queue.resume_dlq.url
}

output "dynamodb_table_name" {
  value = aws_dynamodb_table.resume_audit.name
}

output "completion_lambda_name" {
  value = aws_lambda_function.completion.function_name
}

output "eventbridge_rule_name" {
  value = aws_cloudwatch_event_rule.resume_completed.name
}

output "vpc_id" {
  value = aws_vpc.demo.id
}

output "security_group_id" {
  value = aws_security_group.demo.id
}

output "ec2_instance_id" {
  value       = try(aws_instance.demo[0].id, null)
  description = "Null unless ec2_ami_id is configured and the emulator accepts the AMI."
}
