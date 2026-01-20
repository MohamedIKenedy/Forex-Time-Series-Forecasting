variable "aws_region" {
  description = "AWS region to deploy resources in"
  type        = string
}

variable "instance_type" {
  description = "EC2 instance type"
  type        = string
}

variable "ami_id" {
  description = "AMI ID for the EC2 instance"
  type        = string
}

variable "key_name" {
  description = "Name of the SSH key pair in AWS"
  type        = string
}

variable "public_key_path" {
  description = "Path to your public SSH key"
  type        = string
}
