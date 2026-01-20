Infrastructure README

Purpose
- Quick instructions to create an EC2 instance using Terraform and AWS.

Prerequisites
- Terraform installed (v1.0+ recommended)
- AWS CLI installed and configured (`aws configure`) or AWS creds in env vars: `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, `AWS_DEFAULT_REGION`
- An SSH keypair in the target region (or create one in the AWS console)

Quick steps
1. Review variables
- Open `variables.tf` / `terraform.tfvars` in `infrastructure/` and set values for:
  - `aws_region` (e.g. `us-east-1`)
  - `instance_type` (e.g. `t3.micro`)
  - `ami` (AMI id for your region)
  - `key_name` (your EC2 key pair name)

2. Initialize Terraform
```bash
cd infrastructure
terraform init
```

3. Validate & plan
```bash
terraform validate
terraform plan -out=tfplan
```

4. Apply (create EC2)
```bash
terraform apply "tfplan"
```
Or directly:
```bash
terraform apply -var='aws_region=us-east-1' -var='instance_type=t3.micro' -var='ami=ami-xxxxxxxx' -var='key_name=my-key'
```

5. Check outputs
- After apply, Terraform will show outputs such as `public_ip` or `instance_id` (if defined in `outputs.tf`).

6. Destroy (clean up)
```bash
terraform destroy
```



