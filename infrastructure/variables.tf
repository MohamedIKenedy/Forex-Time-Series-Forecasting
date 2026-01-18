variable "aws_region" {
  type    = string
  default = "us-east-1"
}

variable "name" {
  type    = string
  default = "forex-app"
}

variable "instance_type" {
  type    = string
  default = "t3.medium"
}

variable "key_name" {
  type    = string
  default = "forex-deployer-key"
}

variable "public_key_path" {
  type        = string
  description = "Path to your public key file (e.g. ~/.ssh/id_rsa.pub)"
}

variable "my_ip_cidr" {
  type        = string
  description = "Your public IP with /32 CIDR (e.g. 1.2.3.4/32)"
}

variable "open_api_port" {
  type    = bool
  default = true
}

variable "api_port" {
  type    = number
  default = 8000
}
