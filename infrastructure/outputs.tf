output "public_ip" {
  value = aws_instance.forex.public_ip
}

output "security_group_id" {
  value = aws_security_group.forex_sg.id
}

output "instance_id" {
  value = aws_instance.forex.id
}

output "instance_ready" {
  value = "Wait 60s after apply for instance initialization"
}
