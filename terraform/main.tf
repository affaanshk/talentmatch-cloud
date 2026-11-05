
resource "aws_s3_bucket" "resumes" {
  bucket = var.resume_bucket_name

  # Prevent accidental deletion of the resume-storage bucket.
  lifecycle {
    prevent_destroy = true
  }
}
