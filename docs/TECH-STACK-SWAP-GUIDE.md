# Technology Stack Swap Guide

This kit ships with one concrete stack wired together (Python/FastAPI,
Postgres, GitHub Actions + GHCR, Trivy/bandit/ZAP, Terraform, Jaeger +
Prometheus + Grafana). That's an example, not a requirement — every piece
is swappable. This doc is the **mechanics** of swapping: for each phase,
what single file (or small set of files) is the source of truth for the
current choice, the step-by-step procedure to replace it, and how to
verify the swap didn't silently break something else.

This is different from the other two stack docs, so read this one when
the question is "how do I change X to Y," not "which Y should I pick":

- **`docs/ARCHITECTURE-FIT.md`** — is your project's overall *shape*
  (containers vs Kubernetes vs serverless vs event-driven) compatible
  with this kit at all.
- **`docs/ENTERPRISE-TOOLING.md`** — *which* enterprise vendor to pick for
  a given category, and how to choose between options.
- **This doc** — once you've picked the replacement, what files to touch
  and in what order to actually make the swap.

## How to use the tables below

Each phase lists the **swap point** (the file(s) that encode the current
choice — change these and only these for a clean swap), a **procedure**,
and a **validate** step (what to run to confirm the swap worked, mostly
the same jobs `.github/workflows/validate-kit.yml` already runs).

---

## Plan

| | |
|---|---|
| **Current** | `claude-commands/*.md` — Claude Code slash commands for threat modeling, convention review |
| **Swap point** | The `claude-commands/` directory itself; nothing else in the kit reads these files (no CI job invokes them) |
| **Swap to another AI tool** | Most coding-agent tools (Cursor, Copilot Workspace, Cody) read prompts from their own directory convention (`.cursor/rules/`, etc.) rather than `.claude/commands/`. Copy the *content* (each file's numbered steps and output format are tool-agnostic prose) into the new tool's prompt format — the `$ARGUMENTS` templating syntax is Claude Code-specific and has no direct equivalent in most other tools; you'll hardcode or drop the argument-scoping logic |
| **Swap to none (manual process)** | Move the equivalent checklist (e.g. `threat-model.md`'s STRIDE categories) into a PR template section instead — see `.github/PULL_REQUEST_TEMPLATE.md` for where to add it |
| **Validate** | N/A — nothing automated depends on this phase |

## Code — same-language tool swap

| | |
|---|---|
| **Current** | Python: black, isort, ruff, bandit. Frontend: implied TypeScript + ESLint (`claude-commands/check-frontend.md`) |
| **Swap point** | `ci-cd/pre-commit/.pre-commit-config.yaml` (hooks + `files:` filters) and `ci-cd/github-actions/ci.yml`'s `backend`/`frontend` jobs (toolchain setup + commands) |
| **Procedure** (e.g. ruff → flake8+pylint) | 1. Replace the hook block in `.pre-commit-config.yaml`. 2. Replace the matching step in `ci.yml`'s `backend` job. 3. Keep the `files: ^backend/` filter pattern — that's the part that's actually project-specific, not the tool |
| **Validate** | `pre-commit run --all-files`; the `backend`/`frontend` jobs in `ci.yml` |

Swapping the *language itself* (Python → Go/Rust/Java/Node/.NET) is a bigger,
cross-cutting change — see the dedicated section below.

---

## Language / Runtime Swap (cross-cutting — touches every phase below)

This is the swap most likely to be done wrong, because it looks like a
"Code phase" change but actually touches Code, Build/Release, Test,
Security Gate, and Operate/Monitor — and people who only update the
linter find out the SAST tool, the Dockerfile, and the OTel instrumentation
were all still Python-shaped. The lifecycle impact map below exists so you
can swap each piece deliberately instead of discovering the gaps one CI
failure at a time. It also identifies what should be **independent**: a
phase that requires no change at all reflects the kit's container-image /
OTLP / SARIF interface boundaries doing their job.

### Lifecycle impact map

| Phase | Coupled to language? | What changes | What stays independent |
|---|---|---|---|
| **Plan** | Loosely | `claude-commands/check-python.md` and `fix-python.md` are Python-specific and need replacing with the new language's equivalents (or deleting if you're keeping your own) | `threat-model.md`, `review-conventions.md`, `compliance-check.md`, and the PR/issue templates are all language-agnostic prose — no change |
| **Code** | Fully | Formatter, linter, pre-commit hook block, `ci.yml`'s `backend` job's setup/install/lint/test steps — see the tooling table below | The `files: ^backend/` path-filter *pattern* in pre-commit and the lint→test job *shape* in `ci.yml` carry over unchanged |
| **Build/Release** | Partially | The Dockerfile's `FROM` base image and build stages (multi-stage build layout differs per language — see the runtime-conventions table below); `working-directory`/`cache-dependency-path` in `ci.yml` | The registry, and the entire Trivy → SBOM → SLSA → cosign chain — these operate on the **built container image**, not the language inside it. Zero changes |
| **Test** | Fully (unit/integration) / Independent (load) | Test framework + coverage tool (table below); coverage report format only matters if a vendor coverage tool expects a specific format (cobertura/lcov vs `coverage.xml`) | k6/Locust hit HTTP endpoints — language-blind by construction. Playwright E2E hits the frontend, also language-independent |
| **Security Gate** | Mixed | SAST and the dependency-CVE/SCA tool are language-coupled (table below) — swap in `ci.yml`'s `security` job and in pre-commit | Trivy (container scan), tfsec (IaC scan), `detect-secrets` (secret scan), OWASP ZAP (DAST) all operate on the image/repo/running-endpoint, never the language. **Zero changes needed** |
| **Deploy** | Independent | Nothing | Everything. `publish.yml`'s deploy jobs and the Terraform module deploy a container image; neither has any knowledge of what's inside it. This is the strongest case of phase independence in the kit |
| **Operate/Monitor** | Partially | The OTel SDK/instrumentation package is language-specific (table below); re-implement the *pattern*, not just import a different library | Jaeger/Prometheus/Grafana, the dashboard JSON, and the recording rules all consume OTLP / Prometheus exposition format — agnostic to the source language once data arrives |

The "stays independent" column isn't an accident — it's what the
container-image boundary (Build/Release, Deploy), the OTLP boundary
(Operate/Monitor), and the SARIF boundary (Security Gate) are *for*. If a
future swap finds one of these supposedly-independent phases needs a code
change after all, that's the kit's interface leaking — fix the interface,
not just the one call site (same rule as the footer below).

### Tooling equivalence (Code + Security Gate + Test)

| Language | Formatter | Linter | SAST | SCA / dependency-CVE | Test framework |
|---|---|---|---|---|---|
| **Python** (current) | black | ruff (or flake8+pylint) | bandit | pip-audit | pytest |
| Node.js / TypeScript | prettier | eslint | eslint-plugin-security or Semgrep | npm audit | Jest or Vitest |
| Go | gofmt / goimports | golangci-lint | gosec | govulncheck | go test |
| Rust | rustfmt | clippy | Semgrep (no mature Rust-native SAST) | cargo-audit | cargo test |
| Java / Kotlin | google-java-format / ktlint | Checkstyle / detekt | SpotBugs + find-sec-bugs | OWASP Dependency-Check or Snyk | JUnit |
| .NET / C# | `dotnet format` | Roslyn analyzers | Security Code Scan | `dotnet list package --vulnerable` | xUnit or NUnit |

Semgrep is the one row-spanning option: it covers Python, Node, Go, Java,
and C# from a single rule set, so picking it as your SAST tool *before* a
language swap means the Security Gate row in the impact map above moves
from "coupled" to "independent" for future swaps too.

### Runtime conventions (Build/Release + Operate/Monitor + version control)

| Language | Package manager / lockfile | Config/env access | OTel SDK package | Dockerfile base image pattern |
|---|---|---|---|---|
| **Python** (current) | pip + `requirements.txt` (or poetry/uv + lockfile) | `os.environ` | `opentelemetry-sdk` (see `examples/minimal-service/telemetry.py`) | `python:3.12-slim`, single-stage |
| Node.js / TypeScript | npm + `package-lock.json` (or pnpm/yarn) | `process.env` | `@opentelemetry/sdk-node` | `node:20-slim` build stage → `node:20-slim` (or `-alpine`) runtime stage |
| Go | `go.mod` + `go.sum` | `os.Getenv` | `go.opentelemetry.io/otel` | `golang:1.23` build stage → `scratch`/`distroless` runtime stage (static binary) |
| Rust | `Cargo.toml` + `Cargo.lock` (commit it — this is a service, not a library) | `std::env::var` | `opentelemetry` crate | `rust:1.82` build stage → `debian:slim`/`distroless` runtime stage |
| Java / Kotlin | Maven (`pom.xml`) or Gradle (`build.gradle` + lockfile) | `System.getenv` / Spring `application.yml` | `opentelemetry-java` (often the zero-code java agent) | `eclipse-temurin:21-jdk` build stage → `eclipse-temurin:21-jre` runtime stage |
| .NET / C# | NuGet (`.csproj` + `packages.lock.json`) | `IConfiguration` / `appsettings.json` + user-secrets | OpenTelemetry .NET SDK (already wired in `dotnet/ServiceDefaults/Extensions.cs`) | `mcr.microsoft.com/dotnet/sdk:9.0` build stage → `mcr.microsoft.com/dotnet/aspnet:9.0` runtime stage |

### Version control — `.gitignore` and lockfiles

| Language | Remove from `.gitignore` | Add to `.gitignore` |
|---|---|---|
| **Python** (current, already in this kit's `.gitignore`) | — | `__pycache__/`, `*.pyc`, `.venv/`, `*.egg-info/`, `.pytest_cache/`, `.ruff_cache/`, `.coverage`, `htmlcov/` |
| Node.js / TypeScript | the Python entries above, if no Python remains in the repo | `node_modules/`, `dist/`, `coverage/`, `*.tsbuildinfo` |
| Go | the Python entries above | `*.exe`, `*.test`, `*.out` (leave `vendor/` un-ignored only if you intentionally vendor dependencies) |
| Rust | the Python entries above | `target/` — **do not** ignore `Cargo.lock` for a service/binary (only libraries omit it) |
| Java / Kotlin | the Python entries above | `target/` (Maven) or `build/`, `.gradle/` (Gradle), `*.class` |
| .NET / C# | the Python entries above | nothing new — this kit's `.gitignore` already has `bin/`/`obj/` from the existing `dotnet/` assets |

Lockfiles (`package-lock.json`, `go.sum`, `Cargo.lock`, `packages.lock.json`)
should always be **committed**, never gitignored — they're what `npm audit`
/ `govulncheck` / `cargo-audit` / `dotnet list package --vulnerable` (the
SCA tools in the table above) actually scan. An adopter who gitignores
their lockfile "by habit" from a different project silently disables their
own Security Gate SCA check.

### Validate

1. `pre-commit run --all-files` — new formatter/linter pass clean.
2. `ci.yml`'s `backend` job — new toolchain setup, lint, and test steps all green.
3. `ci.yml`'s `security` job — new SAST/SCA tool runs and produces findings in the expected format (SARIF, if you're keeping the `upload-sarif` step).
4. Build the Dockerfile locally and confirm `/health`, `/ready`, and `/metrics` (or your language's equivalent OTel-exported metrics endpoint) all respond — same check `examples/minimal-service`'s own smoke test runs.
5. Boot the observability overlay and confirm traces still arrive in Jaeger under the expected `service.name` — proves the new language's OTel SDK is wired correctly without needing any change on the Jaeger/Prometheus/Grafana side.

## Build / Release (CI platform, registry)

| | |
|---|---|
| **Current** | GitHub Actions (`ci-cd/github-actions/ci.yml`, `publish.yml`), GHCR |
| **Swap point** | The entire `ci-cd/github-actions/` directory — these are GitHub Actions YAML, not a portable pipeline format. There is no partial swap; plan a rewrite, not a find-replace |
| **Procedure** | 1. Use the existing files as the **job list to replicate**, not as source to translate mechanically — the job graph (lint → test → security → build → Trivy gate → SBOM → SLSA → staged deploy) is the actual asset, the YAML syntax isn't. 2. Translate job-by-job using the equivalence table below. 3. Re-create the OIDC trust relationship for whichever cloud you deploy to — GitLab CI, Jenkins, and Azure Pipelines all support OIDC-based keyless cloud auth, but each configures the trust differently (GitLab uses `id_tokens:`, Jenkins needs a plugin, Azure Pipelines uses a service connection) |
| **GitHub Actions → other CI, job equivalence** | `actions/checkout` → built into every CI platform implicitly. `actions/setup-python`/`setup-node` → GitLab: `image:` + manual install; Jenkins: a tool plugin or Docker agent. `docker/build-push-action` → `docker build && docker push` is universal, GitLab has `docker:dind` service pattern. `aquasecurity/trivy-action` → Trivy ships a CLI; every platform can `trivy image ...` directly. `slsa-framework/slsa-github-generator` → **no direct equivalent outside GitHub Actions** (it's GitHub's own attestation API under the hood) — dropping SLSA provenance or switching to a different supply-chain attestation approach (e.g. in-toto directly) is a real capability loss, not just a syntax change |
| **Registry swap** (GHCR → ECR/ACR/Artifact Registry/Harbor) | Change `REGISTRY` env var + the `docker/login-action` step's `registry:`/credentials in `publish.yml`; everything downstream (`IMAGE_NAME`, Trivy scan, SBOM) references `${{ env.REGISTRY }}` so it follows automatically |
| **Validate** | `.github/workflows/validate-kit.yml`'s `actionlint` job (or the new platform's own lint, e.g. `gitlab-ci-lint`); a full pipeline run against a throwaway branch |

## Test (frameworks, load-testing tools)

| | |
|---|---|
| **Current** | pytest, npm test, Playwright (E2E); k6 + Locust (load) |
| **Swap point** | `ci.yml`'s `backend`/`frontend`/`e2e` jobs for test frameworks; `load-testing/k6/` and `load-testing/locust/` for load tools |
| **Procedure — test framework** | Swap is usually contained to the single command line in `ci.yml` (`pytest ...` → `unittest`/`nose2`; `npm test` already abstracts the actual runner via `package.json`'s `test` script, so changing Jest → Vitest is a `package.json` change with zero `ci.yml` change). Swapping the test framework *as part of* a full language swap — see the "Language / Runtime Swap" section above for the per-language equivalence table |
| **Procedure — load-testing tool** (k6/Locust → Gatling/JMeter/Artillery) | 1. Rewrite the scenario files — there's no automatic translation; k6's JS-based scripting, Locust's Python, Gatling's Scala/Kotlin, and JMeter's XML are all different paradigms. 2. Preserve the **patterns**, not the syntax: staged ramps, weighted user/endpoint mixes, named pass/fail thresholds — these are documented per-file in `load-testing/`'s TODO headers and are what's actually worth carrying over. 3. Update every reference to `load-testing/k6/smoke.js` in `ci.yml`'s `smoke-test` job and `publish.yml`'s deploy jobs' "Smoke test" steps |
| **Validate** | Run the new tool's smoke-equivalent scenario locally against `examples/minimal-service` before wiring it into CI |

## Security Gate (SAST, SCA, container/IaC scanning, DAST)

| | |
|---|---|
| **Current** | Trivy (container), bandit (Python SAST), pip-audit/npm audit (SCA), tfsec (IaC), OWASP ZAP (DAST), `detect-secrets` |
| **Swap point** | `ci-cd/pre-commit/.pre-commit-config.yaml` (bandit, detect-secrets), `ci.yml`'s `security` job (bandit, pip-audit, npm audit), `ci.yml`'s `terraform-plan` job (tfsec), `publish.yml`'s `publish-api`/`publish-frontend` jobs (Trivy) and `zap-baseline-scan` job (ZAP) |
| **Procedure** | Because every one of these tools' GitHub Action emits or reads a standard format (SARIF for SAST/container scanners, the Trivy `severity`/`exit-code` hard-gate pattern), swapping is usually: replace the Action, keep the same `upload-sarif` step pointed at the new SARIF file, keep the same `category:` label if you want history to stay associated. See `docs/ENTERPRISE-TOOLING.md`'s Security Gate table for the specific replacement actions per tool |
| **Within open-source, not just OSS → enterprise** | bandit → Semgrep (`semgrep-action`) is a same-tier OSS swap, not an enterprise one — useful if you want one tool covering multiple languages instead of bandit (Python-only); Trivy → Grype is a same-tier swap if you prefer Anchore's ecosystem. If you're swapping SAST/SCA *because* you're also swapping language, use the "Language / Runtime Swap" section's tooling-equivalence table above instead of picking in isolation |
| **Validate** | Push a branch with a deliberately known-bad dependency/CVE-laden base image and confirm the new tool still gates the build |

## Deploy (cloud target, IaC tool)

| | |
|---|---|
| **Current** | Four cloud deploy jobs in `publish.yml` (Fly.io, Azure, AWS, GCP — all `if: false` until activated), Terraform for GCP Cloud Run only |
| **Swap point** | `publish.yml`'s `deploy-*` jobs (already structured as independent, mutually exclusive jobs — this is the easiest swap in the kit, by design) |
| **Procedure — switch which cloud is active** | Remove `if: false` from the target job, fill its TODOs (see `docs/TODO.md`), leave the other three `if: false` jobs in place or delete them |
| **Procedure — swap IaC tool** (Terraform → Pulumi/CloudFormation/Bicep/CDK) | 1. `iac-terraform/gcp-cloud-run/` is the only IaC in the kit — there's no partial swap, the whole module gets rewritten in the new tool. 2. Carry over the **parameterization** (`project_id`, `region`, `environment`, scale-to-zero vs always-on — see that module's own `README.md`), not the HCL syntax. 3. Update `ci.yml`'s `terraform-plan` job entirely (`hashicorp/setup-terraform` → e.g. `pulumi/actions` for Pulumi) |
| **Validate** | `terraform validate && terraform fmt -check` (or the new tool's equivalent) — this is exactly what `validate-kit.yml`'s `terraform-validate` job runs, update that workflow too if you change tools |

## Operate / Monitor (observability stack, database)

| | |
|---|---|
| **Current** | Jaeger + Prometheus + Grafana (`observability/docker-compose.observability.yml`); Postgres (assumed by `ci.yml`'s CI service container and `claude-commands/check-db.md`) |
| **Swap point — observability backend** | `OTLP_ENDPOINT`/`OTEL_EXPORTER_OTLP_ENDPOINT` env var (already vendor-neutral — see `docs/ENTERPRISE-TOOLING.md`'s Operate/Monitor row for the managed-vendor swap, which needs no code change) |
| **Swap point — self-hosted stack itself** (Jaeger/Prometheus/Grafana → another OSS stack, e.g. SigNoz, Tempo+Loki+Mimir) | `observability/docker-compose.observability.yml`, `observability/prometheus.yml`, `observability/recording_rules.yml`, `observability/grafana/` — these all assume Prometheus's exposition format and Jaeger's OTLP receiver; an alternative OTLP-native backend (Tempo, SigNoz) can usually receive the exact same OTLP traffic with just the endpoint changed, but the Grafana dashboard JSON and recording rules are Prometheus-query-language-specific and need rewriting for a different query language (e.g. SigNoz's ClickHouse-based query builder) |
| **Swap point — database engine** (Postgres → MySQL/MongoDB) | `ci.yml`'s `backend` job's `services: postgres:` block (CI-only test database), and `claude-commands/check-db.md` (hardcoded to SQLAlchemy/Alembic conventions — see that file's own "adapted from" disclaimer). If using .NET/Aspire, also `dotnet/apphost-template/Program.cs`'s database resource wiring |
| **Procedure — database swap** | 1. Replace the CI service container image/health-check in `ci.yml`. 2. Replace `check-db.md`'s entire body — its model/migration/repository conventions are SQLAlchemy/Alembic-specific and don't translate to e.g. Mongoose or EF Core; treat it as a rewrite using the same four-section structure (model conventions, migration hygiene, index coverage, query-layer patterns), not a find-replace. 3. If moving to a non-relational store, drop the "every model needs a migration" check entirely — that section only makes sense for a schema-migration-based engine |
| **Known gotcha when renaming/duplicating the app service** | `examples/minimal-service/telemetry.py` hardcoded its OTel `service.name` resource attribute to the literal string `"app"` instead of reading it from config — meaning if you copy this file for a second service, both report as `service.name: "app"` and become indistinguishable in Jaeger/Grafana. **Fixed** in this kit to read `OTEL_SERVICE_NAME` (the standard OTel env var) with `"app"` as the default, so duplicating the service for a second one is now a config change, not a code edit |
| **Validate** | `minimal-service-smoke` job in `validate-kit.yml` (boots the stack, checks `/health`, `/ready`, `/metrics`, and that Prometheus has registered targets) |

---

## A general rule across all phases

If a swap requires editing application/template *code* rather than an env
var or a config file, that's a signal the kit's swap point for that
choice is weaker than it should be — like the `telemetry.py` hardcoding
above. When you hit one of these, prefer fixing the swap point (make it
config-driven) over working around it, since the next person doing the
same swap hits the identical wall.
