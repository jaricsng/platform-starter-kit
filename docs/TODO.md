# TODO — placeholders to fill in per adoption

One row per placeholder introduced during extraction. Work through the rows
for whichever folders you've copied into your own repo — you don't need all
of them.

| File | Placeholder | What to set it to |
|---|---|---|
| `dotnet/apphost-template/AppHost.csproj` | `<UserSecretsId>REPLACE-WITH-YOUR-OWN-GUID</UserSecretsId>` | Run `dotnet user-secrets init` in the project and paste the GUID it writes |
| `dotnet/apphost-template/appsettings.Development.json` | `db-password`, `secret-key` values | Your own dev-only dummy values, or set via `dotnet user-secrets set` |
| `dotnet/apphost-template/Program.cs` | `../../path/to/your/api`, `../../path/to/your/frontend` | Relative paths to your actual service projects |
| `ci-cd/pre-commit/.pre-commit-config.yaml` | `files: ^backend/...`-style path filters | Your repo's actual source directories |
| `ci-cd/github-actions/ci.yml` | `working-directory: backend` / `frontend` | Your repo's actual source directories |
| `ci-cd/github-actions/ci.yml` | `iac-terraform/gcp-cloud-run` terraform-plan working directory | Wherever you place your Terraform module |
| `ci-cd/github-actions/ci.yml` | Conftest gate's `continue-on-error: true` | Remove it to hard-gate PRs on a policy violation (it runs in report mode by default) |
| `ci-cd/github-actions/drift-detection.yml` | `if: false`, cloud auth, `working-directory` | Remove `if: false` and configure WIF + remote state to enable scheduled drift detection |
| `.secrets.baseline` | Generated empty by `scaffold.py` / `make setup` | Re-run `detect-secrets scan > .secrets.baseline` after adding code; audit findings with `detect-secrets audit .secrets.baseline` |
| `ci-cd/github-actions/ci.yml` | `services: postgres:` block (image + connection env vars) | Your actual database engine, if not Postgres — see `docs/TECH-STACK-SWAP-GUIDE.md`'s database-swap row |
| `ci-cd/github-actions/publish.yml` | `TODO-your-app-staging`, `TODO-your-app-production` (Fly.io) | Your actual Fly.io app names |
| `ci-cd/github-actions/publish.yml` | `deploy/aws-deploy.sh`, `deploy/gcp-deploy.sh` | Your own deploy scripts, or remove the job if not targeting that cloud |
| `ci-cd/github-actions/publish.yml` | Every cloud deploy job's `if: false` | Remove once the matching GitHub Environment + secrets (below) are configured |
| `observability/prometheus.yml` | `job_name: app`, `targets: ["app:8000"]` | Your Compose service's actual name, if not `app` |
| `observability/recording_rules.yml` | `job: app` labels, `http_server_duration_milliseconds` metric name | Your service's job label; confirm this matches your OTel SDK's semantic-convention version (see `docs/ASSET-CATALOG.md` "Findings worth knowing about") |
| `observability/grafana/dashboards/starter-dashboard.json` | `job="app"` queries | Your service's job label |
| `observability/alertmanager.yml` | Slack `api_url` + PagerDuty `routing_key` (structurally-valid placeholders) | Your real webhook URL / integration key — supply via secret, don't commit |
| `Makefile` | `setup`/`test`/`lint`/`fmt` targets marked `# TODO` | Your stack's actual install/test/lint/format commands (filled in once, inherited by everyone + CI) |
| `dev-experience/.tool-versions` → `.tool-versions` | `python`/`nodejs`/`terraform` versions | Match whatever `ci-cd/github-actions/ci.yml`'s `setup-*` steps pin |
| `load-testing/k6/*.js`, `load-testing/locust/locustfile.py` | Worked-example endpoint paths/payloads (see each file's TODO header) | Your own API's routes and request bodies |
| `iac-terraform/gcp-cloud-run/` | `terraform.tfvars`, GCS backend block | Your GCP project ID, image tag, GitHub repo, and a remote-state bucket (see the module's own `README.md`) |
| `iac-terraform/gcp-cloud-run/variables.tf` | `app_name` (defaults to `"app"`) | Your application's actual name — prefixes every resource the module creates |
| `security/manual-checks.sh` | `ENDPOINTS` configuration block at the top of the file | Your own auth/resource routes; adapt or delete the A04 status-state-machine checks if you don't have a similar workflow |
| `catalog-info.yaml` | `owner: TODO-platform-team` | Your actual Backstage group reference (e.g. `group:default/platform-team`) — only relevant if you run Backstage |
| `.github/CODEOWNERS` | `* @jaricsng` (this kit's own owner) | Your actual GitHub team or handle — required before `docs/GETTING-STARTED.md`'s branch-protection step is meaningful |
| `governance/policy-as-code/policy/terraform_guardrails.rego` | Example Conftest/OPA rules, written against `iac-terraform/gcp-cloud-run`'s specific resources | Adapt the resource checks to your own requirements/cloud, or delete the folder — see `governance/policy-as-code/README.md` |

## Required CI secrets (only for deploy targets you activate)

| Secret | Used by | Required for |
|---|---|---|
| `FLY_API_TOKEN` | `publish.yml` | Fly.io deploy jobs |
| `AZURE_CLIENT_ID`, `AZURE_TENANT_ID`, `AZURE_SUBSCRIPTION_ID` | `publish.yml` | Azure Container Apps deploy job (OIDC) |
| `AWS_DEPLOY_ROLE_ARN` | `publish.yml` | AWS ECS Fargate deploy job (OIDC) |
| `GCP_WORKLOAD_IDENTITY_PROVIDER`, `GCP_SERVICE_ACCOUNT` | `publish.yml` | GCP Cloud Run deploy job (Workload Identity Federation) |
| `SLACK_WEBHOOK_URL` | `publish.yml` | Failure notifications (optional on all targets) |
