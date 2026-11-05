resource "aws_dynamodb_table" "resume_audit" {
  name         = "talentmatch-resume-audit-local"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "upload_id"

  attribute {
    name = "upload_id"
    type = "S"
  }

  tags = {
    Project = "TalentMatch"
    Purpose = "Local learning/demo"
  }
}
