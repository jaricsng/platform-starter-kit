# Asset Catalog

Every asset in this kit, where it came from, what lifecycle stage it serves,
and how much adaptation it needs. Reusability ratings (★ to ★★★★★) reflect
the original source-repo review; the "Extraction notes" column reflects what
actually happened during extraction into this kit.

| Asset | Path here | Lifecycle stage | Reusability | Extraction notes |
|---|---|---|---|---|
| Scaffolding generator | `tools/scaffold.py` | Plan | ★★★★★ | Not extracted from the source lab — built directly for this kit as the self-service mechanism that resolves `docs/TODO.md`'s app-name-shaped placeholders automatically instead of by hand |
| Readiness-check script | `tools/doctor.py` | Plan | ★★★★★ | Not extracted — automates `docs/ARCHITECTURE-FIT.md`'s manual pre-adoption checklist into a script; copied into every repo `scaffold.py` generates so it stays available for ongoing checks |
| Drift/re-sync check | `tools/sync_check.py` | Plan, Operate / Monitor | ★★★★ | Not extracted — diffs a scaffolded repo's kit-sourced files against the kit's current state via the commit SHA `scaffold.py` stamped into `PLATFORM-KIT.md`; informational only, doesn't merge anything |
| Aspire `ServiceDefaults` | `dotnet/ServiceDefaults/` | Deploy | ★★★★★ | Zero app-specific logic — copied verbatim, only the csproj/namespace renamed |
| Claude Code command library | `claude-commands/*.md` (19 files) | Plan, Code, Security Gate | ★★★★★ | Copied verbatim; each file prepended with a note that internal path references (e.g. `backend/app/`) are examples to adjust, and given `description`/`argument-hint` frontmatter |
| Prometheus + Jaeger + Grafana stack | `observability/` | Operate / Monitor | ★★★★★ | Extracted from a Compose `observability` profile into its own standalone overlay file; job/target names genericized (the source app's specific name → `app`) |
| Pre-commit security baseline | `ci-cd/pre-commit/.pre-commit-config.yaml` | Code | ★★★★★ | Copied as-is; `files:` path filters flagged for per-adopter adjustment |
| CI/CD pipeline shape | `ci-cd/github-actions/ci.yml`, `publish.yml` | Build/Release, Test, Deploy | ★★★★ | The *pattern* (lint → test → build → Trivy gate → SBOM → SLSA → staged promotion) is reusable; cloud-specific app/cluster names replaced with `TODO-` placeholders. The `aspire-manifest` publish job was **dropped** — too tightly coupled to a specific Aspire project path; .NET/Aspire adopters wire it back in using `dotnet/apphost-template`. |
| k6 + Locust load-test scenarios | `load-testing/k6/`, `load-testing/locust/` | Test | ★★★★ | Patterns (token-pool setup, staged ramps, weighted user mix, named thresholds) kept intact; each file carries a TODO header identifying which endpoint paths/payloads are worked-example-specific |
| Aspire AppHost wiring pattern | `dotnet/apphost-template/` | Deploy | ★★★★ | `Program.cs` genericized: real service/volume/database names replaced with placeholder paths and a fresh `UserSecretsId` TODO |
| Terraform GCP Cloud Run module | `iac-terraform/gcp-cloud-run/` | Deploy | ★★★★ | Already a cleanly parameterized module (`project_id`, `region`, `environment`, scale-to-zero vs always-on) — copied as-is; added a `README.md` with usage example and backend-config notes |
| OWASP pen-test harness | `security/manual-checks.sh` | Test, Security Gate | ★★★ | Heaviest adaptation: hardcoded endpoint paths wrapped in a top-of-file `ENDPOINTS` configuration block; the A04 status-state-machine checks are flagged as a worked-example shape to adapt or delete per adopter's own domain |
| OWASP ZAP scan wrapper | `security/zap-scan.sh` | Test, Security Gate | ★★★★ | Already generic — copied as-is, only the reports output path changed (`pen-tests/reports` → `security/reports`) |

## Not extracted

- **Application source** (the original repo's `backend/app/`, `frontend/src/`) — business logic, not platform tooling.
- **Curriculum docs** (`docs/modules/*`) — pedagogical content for a teaching lab, not reusable platform assets. The *module structure* (numbered, sequential, building toward a working app) is a reasonable template for an onboarding curriculum, but the content itself is specific to that lab.
- **Raw cloud deploy scripts** (`aws/deploy.sh`, `infra/gcp/deploy.sh` in the source application) — single-account-shaped shell scripts, lower reuse value than the Terraform module already included here, so they weren't carried over. Write your own, scoped to your actual account/cluster names, or use `iac-terraform/gcp-cloud-run/` directly for the GCP path.

## Findings worth knowing about

- The Grafana dashboard (`observability/grafana/dashboards/starter-dashboard.json`) was **already fully generic** RED-method panels (request rate, error rate, latency, traces) when reviewed — no app-specific custom-metric panels needed stripping, contrary to the original assumption that it would.
- `observability/recording_rules.yml` references the OTel HTTP metric name `http_server_duration_milliseconds` (pre-1.23 semantic conventions), while the dashboard JSON queries `http_server_request_duration_seconds` (the newer name). This mismatch existed in the source repo and was carried over unfixed — flagged here so you don't lose time debugging "why are these panels empty." Pick one semantic-convention version and make both files agree before relying on the SLO burn-rate alerts.
- Two real bugs were found and **fixed** while booting `examples/minimal-service` end-to-end (both pre-existed in the source application's observability config, not introduced during extraction): (1) `prometheus.yml` had `rule_files` nested under `global:`, which Prometheus's strict config schema silently rejects — moved to a top-level key; (2) `grafana/provisioning/alerting/rules.yaml` was written in Mimir/Cortex ruler syntax (`alert`/`expr`/`for`), which is not Grafana's own file-provisioning schema (`title`/`uid`/`condition`/`data`) — rewritten so Grafana actually starts instead of crash-looping on `rule has no title set`.
- `examples/minimal-service/docker-compose.yml`'s host port is `${APP_PORT:-8000}` rather than a hardcoded `8000:8000`, so it doesn't collide with another instance already using port 8000 on your machine — override with `APP_PORT=18000 docker compose ...` if needed.
- `tools/doctor.py` initially produced false-positive PASSes when run against a freshly `scaffold.py`-generated repo (no app code yet): its own source matched its `/health`/`opentelemetry` regexes, and the copied `load-testing/`/`security/` scripts matched too (they *reference* those endpoints because they test them, not because an app implements them). Fixed by excluding the doctor/scaffold scripts' own files and the kit's known non-application infrastructure directories from the source scan — caught during the scaffold → doctor → validate end-to-end test, not before.
