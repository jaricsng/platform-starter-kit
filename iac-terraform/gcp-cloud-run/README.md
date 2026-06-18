# GCP Cloud Run module

Parameterized Terraform module: Cloud SQL (Postgres 16) + Secret Manager +
a service account + a Cloud Run v2 service wired together, with
staging/production-aware defaults (scale-to-zero vs always-on, backup
retention, deletion protection).

## Usage

Create an `environments/<name>/main.tf` that calls this module:

```hcl
module "api" {
  source = "../../../iac-terraform/gcp-cloud-run"

  project_id         = var.project_id
  app_name           = "your-app"          # prefixes every resource this module creates
  region             = "us-central1"
  environment        = "staging"          # or "production"
  image_tag          = var.image_tag      # e.g. sha-abc1234
  github_repository  = "your-org/your-repo"
  secret_key         = var.secret_key

  db_tier       = "db-f1-micro"  # staging; use db-n1-standard-1+ for production
  min_instances = 0              # staging; use 1+ for production (avoid cold starts)
  max_instances = 10
}
```

And an `environments/<name>/terraform.tfvars`:

```hcl
project_id = "your-gcp-project-id"
image_tag  = "sha-abc1234"
# secret_key should come from a secure source (CI secret, `terraform.tfvars.local`
# gitignored, or `TF_VAR_secret_key` env var) — never commit it.
```

## Required backend configuration

This module doesn't configure remote state itself. Add a `backend "gcs"` block
in your environment's `main.tf` (or `backend.tf`) pointing at your own GCS bucket:

```hcl
terraform {
  backend "gcs" {
    bucket = "your-tfstate-bucket"
    prefix = "cloud-run/staging"
  }
}
```

## What this module assumes

- `image_tag` refers to an image already pushed to
  `ghcr.io/<github_repository>/api:<image_tag>` (see `ci-cd/github-actions/publish.yml`).
- Your API exposes `/health` (startup probe) and `/ready` (liveness probe) endpoints.
- Your API reads `DATABASE_URL` and `SECRET_KEY` from environment variables.

Adjust `main.tf` directly if your service's image path, probe paths, or env
var names differ.
