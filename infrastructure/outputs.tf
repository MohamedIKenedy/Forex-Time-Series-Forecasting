output "ec2_public_ip" {
  description = "Public IP of the EC2 instance"
  value       = aws_instance.forex_ec2.public_ip
}

output "ssh_command" {
  description = "Command to SSH into the EC2 instance"
  value       = "ssh -i C:/Users/Karim/.ssh/forex_deploy ec2-user@${aws_instance.forex_ec2.public_ip}"
}
