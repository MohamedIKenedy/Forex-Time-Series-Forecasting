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
    description = "SSH from my IP only"
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

  user_data = base64encode(<<-EOF
#!/bin/bash
set -ex

# Update packages
apt-get update -y
apt-get upgrade -y
apt-get install -y curl git wget

# Install Docker from official repo
curl -fsSL https://get.docker.com -o get-docker.sh
bash get-docker.sh
usermod -aG docker ubuntu
rm get-docker.sh

# Install Docker Compose v2 via curl
mkdir -p /usr/local/lib/docker/cli-plugins
curl -fsSL https://github.com/docker/compose/releases/download/v2.24.0/docker-compose-linux-x86_64 -o /usr/local/lib/docker/cli-plugins/docker-compose
chmod +x /usr/local/lib/docker/cli-plugins/docker-compose

# Start Docker
systemctl enable docker
systemctl start docker
sleep 15

# Clone repo as ubuntu user
sudo -u ubuntu git clone https://github.com/MohamedIKenedy/Forex-Time-Series-Forecasting.git /home/ubuntu/forex-app 2>/dev/null || true

# Fix permissions
chown -R ubuntu:ubuntu /home/ubuntu/forex-app

# Log completion
echo "Infrastructure initialization complete" > /var/log/user-data.log
EOF
  )

  tags = {
    Name = "${var.name}-instance-${random_id.suffix.hex}"
  }
}
