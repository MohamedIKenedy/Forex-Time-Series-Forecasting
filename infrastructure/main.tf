provider "aws" {
  region = var.aws_region
}

resource "random_id" "suffix" {
  byte_length = 4
}

data "aws_ami" "ubuntu" {
  most_recent = true
  owners      = ["099720109477"]
  filter {
    name   = "name"
    values = ["ubuntu/images/hvm-ssd/ubuntu-jammy-22.04-amd64-server-*"]
  }
}

resource "aws_key_pair" "deployer" {
  key_name   = "${var.key_name}-${random_id.suffix.hex}"
  public_key = file(var.public_key_path)
}

resource "aws_security_group" "forex_sg" {
  name        = "${var.name}-sg-${random_id.suffix.hex}"
  description = "Security group for forex app"

  ingress {
    description = "SSH from my IP"
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    cidr_blocks = [var.my_ip_cidr]
  }

  ingress {
    description = "API (optional public)"
    from_port   = var.open_api_port ? var.api_port : 0
    to_port     = var.open_api_port ? var.api_port : 0
    protocol    = "tcp"
    cidr_blocks = var.open_api_port ? ["0.0.0.0/0"] : []
  }

  ingress {
    description = "Frontend HTTP"
    from_port   = 80
    to_port     = 80
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
}

resource "aws_instance" "forex" {
  ami                    = data.aws_ami.ubuntu.id
  instance_type          = var.instance_type
  key_name               = aws_key_pair.deployer.key_name
  vpc_security_group_ids = [aws_security_group.forex_sg.id]

  user_data = <<-EOF
              #!/bin/bash
              set -e
              apt-get update -y
              apt-get install -y apt-transport-https ca-certificates curl gnupg lsb-release git
              curl -fsSL https://get.docker.com -o get-docker.sh
              sh get-docker.sh
              usermod -aG docker ubuntu || true
              mkdir -p /home/ubuntu/.docker/cli-plugins || true
              curl -SL "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/lib/docker/cli-plugins/docker-compose || true
              chmod +x /usr/local/lib/docker/cli-plugins/docker-compose || true
              ln -s /usr/local/lib/docker/cli-plugins/docker-compose /usr/local/bin/docker-compose || true
              systemctl enable docker || true
              systemctl start docker || true
              # Clone repo (if public); adjust for private repos
              if [ ! -d /home/ubuntu/forex-app ]; then
                git clone https://github.com/MohamedIKenedy/Forex-Time-Series-Forecasting.git /home/ubuntu/forex-app || true
              fi
              EOF

  tags = {
    Name = "${var.name}-instance-${random_id.suffix.hex}"
  }
}
