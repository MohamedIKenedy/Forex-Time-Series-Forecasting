output "public_ip" {
  value = aws_instance.forex.public_ip
}

output "security_group_id" {
  value = aws_security_group.forex_sg.id
}
