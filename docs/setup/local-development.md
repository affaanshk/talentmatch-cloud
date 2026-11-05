# Local Development Setup

This guide explains how to restore and run TalentMatch Cloud on a fresh Windows development machine.

## Prerequisites

Install:

- Git
- Docker Desktop with Docker Compose
- Floci CLI
- Terraform 1.5.0 or later

Verified development environment:
- Windows
- Docker 29.8.0
- Floci CLI 0.2.3
- Floci server 2.1.0
- Terraform 1.16.5

## 1. Clone the repository

```powershell
git clone https://github.com/affaanshk/talentmatch-cloud.git
cd talentmatch-cloud
```

## 2. Configure environment variables

```powershell
Copy-Item .env.example .env
notepad .env
```

Add your own Gemini API key if required.

Never commit `.env` or expose API keys.

## 3. Start Floci

Start Docker Desktop, then run:

```powershell
floci start
floci wait
floci status
```

Floci endpoint: `http://localhost:4566`

Floci UI: `http://localhost:4500`

Floci runs separately from the application Compose stack.

## 4. Provision local infrastructure

```powershell
Copy-Item terraform/floci/terraform.tfvars.example terraform/floci/terraform.tfvars

terraform -chdir="terraform/floci" init
terraform -chdir="terraform/floci" validate
terraform -chdir="terraform/floci" plan
```

Review the plan before applying:

```powershell
terraform -chdir="terraform/floci" apply
```

This configuration targets the local Floci emulator, not a real AWS account.

## 5. Start TalentMatch Cloud

From the repository root:

```powershell
docker compose up --build
```

## 6. Application URLs

| Component | Address |
|---|---|
| Frontend | http://localhost:5173 |
| Backend | http://localhost:8000 |
| API documentation | http://localhost:8000/docs |
| Floci | http://localhost:4566 |
| Floci UI | http://localhost:4500 |

## 7. Run tests

```powershell
pip install -r requirements.txt
python -m pytest
```

Refer to the testing documentation for recorded integration-test results.

## 8. Stop services

```powershell
docker compose down
floci stop
```

The PostgreSQL volume is retained by `docker compose down`.

Use `docker compose down -v` only when you intentionally want to delete local database data.

## Important notes

- `.env` and Terraform variable files are local configuration and must not be committed.
- Terraform state and generated plan files are excluded from Git.
- A fresh clone requires a fresh local Floci environment and Terraform provisioning.
- The AWS Terraform configuration is separate and has not been applied to a real AWS account.
- Local emulator results do not establish production AWS compatibility.