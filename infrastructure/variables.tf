variable "aws_region" {
  type    = string
  default = "eu-west-3"
}

variable "name" {
  type    = string
  default = "forex-app-2026"
}

variable "instance_type" {
  type    = string
  default = "t3.micro" 
}

variable "key_name" {
  type    = string
  default = "forex-deployer-key-2026"
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
