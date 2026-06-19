# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

Versioning policy: **major** = breaking layout change, **minor** = new
capability folder added, **patch** = doc/template fixes with no structural
change.

## [Unreleased]

## [2.1.4] - 2026-06-19

Dependabot review fallout. Patch per the kit's versioning policy — no
capability folder was added, moved, or removed.

### Fixed

- `iac-terraform/gcp-cloud-run`: `google_cloud_run_v2_service` now sets
  `deletion_protection` explicitly (`false` for staging, `true` for
  production), matching the existing `google_sql_database_instance` pattern.
  Needed before bumping `hashicorp/google` past v6, which defaults this
  field to `true` for every environment — without the override, `terraform
  destroy`/replace on a staging Cloud Run service would fail until someone
  discovered and manually unprotected it.
- `iac-terraform/gcp-cloud-run`: bumped the `hashicorp/google` provider
  constraint from `~> 5.0` to `~> 7.37` (the change reviewed in Dependabot
  PR #1, applied directly once CI caught that it had to land together with
  the `deletion_protection` fix above — the field doesn't exist on the
  pinned v5 provider).
- `iac-terraform/gcp-cloud-run/main.tf`: re-ran `terraform fmt` against a
  current Terraform release. `validate-kit.yml`'s `terraform-validate` job
  pulls the latest CLI with no version pin, and a newer `fmt` produces
  different comment-spacing/alignment output than whatever last formatted
  this file — this was failing on `main` independently of the provider bump.

## [2.1.3] - 2026-06-18

Multi-developer / team support. Patch per the kit's versioning policy — no
capability folder was added, moved, or removed.

### Added

- **Multi-developer / team support** — closed the gaps that bite once more
  than one person works in a scaffolded repo:
  - `concurrency:` groups on the workflows — `publish.yml` queues deploys so
    two merges landing together can't race the same environment;
    `ci.yml`/`drift-detection.yml` cancel/serialize superseded runs.
  - `.gitattributes` (kit root + scaffolded) normalizes line endings to LF,
    so a mixed-OS team doesn't get CRLF churn (and shell scripts / the
    Makefile stay LF). Verified `git add --renormalize` is a no-op today.
  - `iac-terraform/gcp-cloud-run/backend.tf.example` + a clearer README:
    remote state with locking is **required** for a team (local state has no
    locking and isn't shared — concurrent applies corrupt it).
  - `tools/scaffold.py`'s generated `.github/CODEOWNERS` now ships commented
    per-path team-ownership examples.
  - New "Working as a team" section in `docs/GETTING-STARTED.md` tying
    together consistent environments (devcontainer/.tool-versions), merge
    safety (branch protection + CODEOWNERS), no-racing-deploys, shared
    Terraform state, line-ending normalization, and per-developer secrets.

## [2.1.2] - 2026-06-18

Public-release readiness: removed Fly.io (keeping Azure/AWS/GCP + .NET Aspire
for local orchestration), corrected end-to-end adoption instructions to match
reality, and added the community-health files. Patch per the kit's versioning
policy — no capability folder was added, moved, or removed.

### Added

- `CONTRIBUTING.md` and `CODE_OF_CONDUCT.md` (Contributor Covenant 2.1) —
  community-health files for public release; README now links them alongside
  `SECURITY.md`. Confirmed during a release-readiness audit (LICENSE present
  and MIT, no real secrets in the tree — every detect-secrets hit is an
  intentional placeholder, no broken links across 45 markdown files, no
  tracked build cruft).

### Fixed

- End-to-end adoption-instruction accuracy pass (walked the documented path
  and corrected what didn't actually work):
  - `tools/scaffold.py` now runs `git init` on the generated repo, so the
    documented next step `make setup` (which runs `pre-commit install`) and
    the `.gitignore`/`.secrets.baseline` all work immediately instead of
    failing with "not a git repository".
  - `dev-experience/Makefile`'s `obs-up`/`obs-down` no longer fail with a
    cryptic Docker error in a fresh repo — they print an actionable hint
    ("add your app's `docker-compose.yml`; the overlay layers on top"), and
    `sync` prints a `KIT_PATH=` hint instead of a confusing path error.
  - Docs that claimed `make obs-up`/`make sync` "work immediately" now
    accurately state their prerequisites (`docs/GETTING-STARTED.md`,
    `dev-experience/README.md`).
  - `CLAUDE.md`'s expected `doctor.py` output corrected (the 3 FAILs are
    Dockerfile / health endpoints / tests; OTel is a WARN, not a FAIL).
  - Verified accurate as-is: the `examples/minimal-service` boot + all its
    documented curls/Jaeger/Prometheus/Grafana claims, the branch-protection
    `gh api` contexts (match real job names), and the governance/migration
    fixture commands' documented exit codes.

### Removed

- **Fly.io** as a deploy target, everywhere: the `deploy-fly-staging` /
  `deploy-fly-production` jobs in `ci-cd/github-actions/publish.yml`, the
  `fly` choice in `tools/scaffold.py`'s `--cloud`, the `FLY_API_TOKEN`
  secret + Fly TODO rows, the Fly section of
  `operations/runbooks/rollback.md`, and Fly mentions across the docs. The
  kit now keeps three cloud deploy targets — **Azure Container Apps**
  (the .NET Aspire `azd` path), **AWS ECS**, and **GCP Cloud Run** — and
  `.NET Aspire`'s AppHost remains the local multi-service orchestrator
  (`dotnet/`). `publish.yml`'s `zap-baseline-scan` was repointed off the
  removed Fly staging job to `deploy-azure` with a generic staging-URL TODO.

## [2.1.1] - 2026-06-18

A "governance / shift-left / stay-right by default" pass: validated the kit
against the Start-right / Shift-left / Stay-right model and closed the gaps
where the *default* path left a secure behaviour off or broken (so the easy
way wasn't yet the secure way). Patch per the kit's versioning policy — no
capability folder was added, moved, or removed.

### Added

- `ci-cd/github-actions/drift-detection.yml` — scheduled
  `terraform plan -detailed-exitcode` that opens/updates an `infra-drift`
  GitHub issue when deployed infrastructure diverges from code (stay-right;
  `sync_check.py` covers kit drift, this covers your own infra drift). Ships
  gated like the deploy jobs; copied into scaffolded repos.
- `tools/scaffold.py` now generates a `.gitignore` (copied from the kit, so a
  scaffolded repo can't commit the `.env` it's told to create) and a valid
  `.secrets.baseline` (live `detect-secrets scan`, or an embedded
  default-plugins fallback) so the `detect-secrets` pre-commit hook works on
  the first commit instead of erroring. `make setup` also bootstraps the
  baseline if missing.
- `tools/doctor.py` — new "Gitignore / secrets baseline" check (FAIL if `.env`
  isn't ignored, WARN if no baseline), so the `golden-path-check` CI job
  catches the footgun on every push.

### Changed

- `ci-cd/pre-commit/.pre-commit-config.yaml` shifts IaC + schema checks left:
  added `terraform_fmt`/`terraform_validate`/`terraform_tfsec`
  (antonbabenko/pre-commit-terraform) and a local `check_migrations.py` hook.
  They only run when the relevant files are staged.
- `ci-cd/github-actions/ci.yml`'s Conftest policy gate is now **active in
  report mode by default** (was commented out): it runs and prints
  violations but `continue-on-error: true` keeps it non-blocking; removing
  that one line hard-gates the PR. Per the kit's "report first, enforce when
  you trust your rules" posture.
- `ci-cd/github-actions/publish.yml` — the Azure, AWS, and GCP deploy jobs now
  do a post-deploy health check and **auto-roll-back on failure** (previously
  only Fly.io did), using the per-provider commands documented in
  `operations/runbooks/rollback.md`.

## [2.1.0] - 2026-06-18

Minor per this kit's own versioning policy: three new capability folders
(`governance/`, `dev-experience/`, `operations/`), no breaking layout
change. Two threads of work since 2.0.0 — a governance/policy-enforcement
pass, and a platform-engineering pass closing the gap between "the kit
describes the golden path" and "a developer can focus on app code and ship
to production with confidence."

### Added — developer experience & delivery confidence

- **New capability folder: `dev-experience/`** — the paved inner loop. A
  `Makefile` task interface (`make test`/`run`/`lint`/`fmt`/`scan`/`doctor`/
  `migrations`/`obs-up`/`sync`) so local and CI run the same commands and a
  developer never memorizes per-tool incantations; the kit-tool targets
  work as-is, app targets carry a one-time TODO. Plus a `.devcontainer/`
  (reproducible env), `.tool-versions` (asdf/mise pinning), `.env.example`
  (documents every env var with no real secret), and `.editorconfig`.
  `scaffold.py` copies these to the new repo's root.
- **New capability folder: `operations/`** — the Day-2 procedures behind the
  observability signals: `runbooks/rollback.md`, `runbooks/incident-response.md`,
  `runbooks/postmortem-template.md`, and `SLOs.md` (the reliability targets
  behind `recording_rules.yml`'s burn-rate alerts, and how error budget
  gates risky deploys). Copied into scaffolded repos.
- `observability/alertmanager.yml` + wiring — the SLO-burn alerts already
  defined in `recording_rules.yml` had nowhere to go; Alertmanager now
  routes `severity: critical` → PagerDuty and the rest → Slack, with an
  inhibition rule. `prometheus.yml` gained the top-level `alerting:` block
  and the compose overlay gained the service. Placeholder receiver URLs are
  structurally valid so the stack still boots (re-verified end-to-end).
- `tools/check_migrations.py` + `docs/DATABASE-MIGRATIONS.md` — a schema-
  safety gate flagging backward-incompatible DDL (DROP COLUMN, SET NOT NULL,
  renames, the Alembic equivalents) that breaks the old app version during
  a rolling deploy, with an inline `migration-safety: ack` escape hatch for
  deliberate contract-phase changes. Wired into `ci.yml` as the
  `migration-safety` job; doc explains the expand/contract pattern.
- `docs/FEATURE-FLAGS.md` — the deploy-≠-release pattern (OpenFeature,
  vendor-neutral) that makes shipping to production low-risk and gives the
  rollback runbook a "flag off" first option.

### Added — governance & policy enforcement

- **New capability folder: `governance/`** — `governance/policy-as-code/`
  ships an OSS Conftest/OPA policy-as-code baseline
  (`policy/terraform_guardrails.rego`) for `iac-terraform/gcp-cloud-run`,
  the free starting point `docs/ENTERPRISE-TOOLING.md` previously pointed
  at (Sentinel/OPA) without providing. Checks two config mistakes the
  module's own variable defaults make easy to hit in production (a
  staging-sized `db_tier`, `min_instances: 0` scale-to-zero), plus a
  non-blocking `warn` on the module's intentional public-ingress IAM
  grant. Includes hand-written plan-JSON fixtures
  (`examples/passing-plan.json`/`failing-plan.json`) so the policy can be
  exercised without `terraform` or real GCP credentials. `scaffold.py`
  copies it in whenever `--cloud gcp` is used (new `--no-governance` to
  opt out); `ci-cd/github-actions/ci.yml`'s `terraform-plan` job has a
  commented `conftest test` step ready to uncomment.
- `tools/doctor.py`: new "Catalog ownership" check — flags
  `catalog-info.yaml`'s `owner:` field if it's still a `TODO-*`
  placeholder, so an unresolved ownership record doesn't sit silently
  forever.
- `ci-cd/github-actions/ci.yml`: new `golden-path-check` job runs
  `tools/doctor.py` on every push/PR (no-ops with a message if the repo
  doesn't have it). Previously `doctor.py` only ran when someone
  remembered to invoke it by hand — a repo could drift off the golden
  path indefinitely between manual checks.
- `tools/scaffold.py` now writes a generic `.github/CODEOWNERS` and
  `.github/dependabot.yml` into every new repo (previously neither was
  generated at all, despite the kit modeling both on itself). Both use a
  `TODO-set-your-team-or-handle`-style placeholder, not this kit's own
  `@jaricsng` — copying the kit's literal governance files verbatim would
  have assigned code ownership of every scaffolded repo to this kit's
  maintainer.
- `docs/GETTING-STARTED.md`: new "11. Governance — branch protection &
  policy enforcement" step with a `gh api` snippet for required status
  checks + required reviewers — the CI gates above are unenforceable
  until branch protection actually requires them, which nothing
  previously told adopters to set up.

### Changed

- `docs/ENTERPRISE-TOOLING.md`'s Terraform-governance rows now point at
  `governance/policy-as-code/` as the OSS baseline to extend (Sentinel
  rules largely port from the same Rego logic) instead of implying
  policy-as-code starts from zero at the enterprise tier.

## [2.0.0] - 2026-06-18

Major per this kit's own versioning policy: includes a breaking layout
change (`claude-skills/` → `claude-commands/`).

### Added

- Root `CLAUDE.md` documenting the kit's structure, conventions, and known
  cross-file gotchas for anyone (human or Claude Code) working on the kit
  itself.
- `SECURITY.md` — vulnerability reporting policy for the kit itself.
- `docs/ARCHITECTURE-FIT.md` — the architecture this kit assumes
  (containerized HTTP services, OTel, serverless-container deploy targets),
  what's a poor fit, and a pre-adoption checklist of signals + actions for
  projects that don't match the baseline.
- `docs/ENTERPRISE-TOOLING.md` — maps each free/OSS tool in the kit to
  enterprise-grade alternatives per lifecycle stage, with concrete
  adoption steps tied to the actual files each swap touches, a decision
  framework for choosing among options against an org's existing
  landscape/compliance/governance constraints (not just a vendor list),
  and a suggested staged adoption order.
- `docs/TECH-STACK-SWAP-GUIDE.md` — per-phase mechanics for swapping any
  single piece of the stack (language/runtime, CI platform, registry,
  database engine, IaC tool, observability backend) for a different one:
  the file(s) that are the source of truth for each choice, the swap
  procedure, and how to validate it.
- `.github/dependabot.yml` — weekly updates for GitHub Actions, the
  Terraform module, the minimal-service example's Python deps, and the
  .NET projects' NuGet deps.
- `.github/CODEOWNERS`, issue templates (bug report, asset request), and a
  PR template tying back to the versioning/validation conventions.
- CI status and license badges in `README.md`.
- **New capability folder: `tools/`** — the kit's first move from
  "documented golden path" to "automated self-service":
  - `tools/scaffold.py` — generates a new repo from this kit in one
    command. Resolves the `your-app`/`YourApp`/"Your App" placeholder
    family automatically across whichever capability folders you choose
    (`--cloud`, `--no-observability`/`--no-security`/`--no-load-testing`/
    `--no-claude-commands`), writes a version-stamped `PLATFORM-KIT.md`
    manifest (source kit commit SHA + choices made), a per-service
    `catalog-info.yaml` so the new repo is catalog-discoverable from
    day one (previously only the kit itself was registered — every repo
    scaffolded from it was invisible to a Backstage catalog), and emits a
    `TODO.md` trimmed to only the placeholders that genuinely need a human
    decision (credentials, project IDs) instead of the kit's full ~17-row
    list. Optional `--telemetry` flag (off by default): records an
    anonymized capability-choice event — no app name, no path — either to
    a local `~/.platform-kit/telemetry.jsonl` or, if an org sets
    `PLATFORM_KIT_TELEMETRY_URL`, POSTs it there instead; a failed POST
    never blocks or fails scaffolding.
  - `tools/doctor.py` — scripts `docs/ARCHITECTURE-FIT.md`'s manual
    pre-adoption checklist (containerized? `/health`+`/ready`? OTel
    instrumented? secrets committed? already on Kubernetes? tests
    present?) against a target repo, printing ✅/⚠️/❌ per signal with a
    CI-usable exit code.
  - `tools/sync_check.py` — the re-sync tool `docs/GETTING-STARTED.md` has
    always referenced ("this kit stays as the upstream reference to
    re-sync from later") without ever providing. Reads the commit SHA
    `scaffold.py` stamped into `PLATFORM-KIT.md`, and for every file it
    knows came from the kit, reports whether you've modified it locally
    and/or the kit has changed it upstream since — with a unified diff for
    the latter via `--show-diffs`.
  - `tools/_platform_kit.py` — shared placeholder-substitution (and its
    inverse) and file-mapping logic used by `scaffold.py`, `doctor.py`'s
    copies, and `sync_check.py`, so the three tools can't silently drift
    apart from each other. `scaffold.py` copies `doctor.py`,
    `sync_check.py`, and this module into every repo it generates, so the
    checks stay available going forward.
- `catalog-info.yaml` + `mkdocs.yml` — registers this kit as a discoverable
  `Component` in a Backstage-style software catalog, with a working
  TechDocs reference into `docs/`. Deliberately a lightweight catalog
  registration, not a Backstage Scaffolder `Template` — a Template would
  duplicate `tools/scaffold.py`'s substitution logic in a second,
  Nunjucks-based templating engine for no real gain.

### Changed

- **Breaking:** renamed `claude-skills/` to `claude-commands/` — these are
  Claude Code slash commands (they use `$ARGUMENTS` and are copied into
  `.claude/commands/`), not Skills (`.claude/skills/<name>/SKILL.md` with
  `name`/`description` frontmatter, invoked by relevance rather than by
  argument). The folder name and docs now match how the files are actually
  used. Each command file also gained `description`/`argument-hint`
  frontmatter.
- The Terraform module's hardcoded `task-manager` resource-name prefix is
  now a proper `app_name` input variable (defaults to `"app"`).
- `docs/TECH-STACK-SWAP-GUIDE.md`'s "Code" row treated a full programming-
  language swap as a single bullet point. Replaced with a dedicated
  "Language / Runtime Swap" section: a per-phase lifecycle impact map
  (which of Plan/Code/Build-Release/Test/Security-Gate/Deploy/Operate are
  actually coupled to language choice vs. already independent thanks to
  the kit's container-image/OTLP/SARIF boundaries, and why), a six-language
  tooling-equivalence table (formatter/linter/SAST/SCA/test framework), a
  runtime-conventions table (package manager, config/env access, OTel SDK,
  Dockerfile base-image pattern), and a `.gitignore`/lockfile table per
  language. Cross-referenced from the Test and Security Gate sections so
  the per-language tables stay the single source of truth.

### Fixed

- `examples/minimal-service/telemetry.py` hardcoded its OTel `service.name`
  resource attribute to the literal `"app"` instead of reading the
  standard `OTEL_SERVICE_NAME` env var — copying the file for a second
  service would have made both report as `service.name: "app"` and become
  indistinguishable in Jaeger/Grafana. Now reads `OTEL_SERVICE_NAME` with
  `"app"` as the default (matching `observability/prometheus.yml`'s
  default job name), so renaming/duplicating the service is a config
  change, not a code edit.
- All four Mermaid diagrams (`README.md`, `docs/GETTING-STARTED.md`,
  `docs/ARCHITECTURE-FIT.md`, `docs/ENTERPRISE-TOOLING.md`) now use
  explicit light-theme `classDef`/`style`/`linkStyle` colors instead of
  relying on each renderer's default theme. The README diagram previously
  had dark subgraph fills with no contrasting line color, making the
  connecting arrows invisible against the box background; the other three
  diagrams had no explicit styling at all, which is resilient against
  light-background renderers but not guaranteed across every Markdown
  viewer's default Mermaid theme (including dark-mode ones).
- Removed every reference to `task-manager`/`TaskManager`/"Task Manager"
  (the name of the private lab app this kit was extracted from) across
  `claude-commands/*.md`, `docs/ASSET-CATALOG.md`, `ci-cd/github-actions/publish.yml`,
  and `iac-terraform/gcp-cloud-run/main.tf`. Adopters have no access to
  that repo, so example resource names like `task-manager-database-url` or
  `aspire/TaskManager.AppHost/` read as a real, specific dependency rather
  than a placeholder. Renamed to the kit's existing `your-app`/`YourApp`/
  "Your App" placeholder convention (already used in `publish.yml`'s
  `TODO-your-app-staging`), and to `appuser`/`appdb` to match `ci.yml`'s
  existing generic Postgres convention.
- `claude-commands/check-aspire.md` had two lines with an absolute local
  filesystem path from the original extraction machine (a `~/.../task-manager/...`
  home-directory path) — replaced with relative paths.
- `dotnet/apphost-template/Program.cs` constructed `DATABASE_URL` with a
  bare `postgresql://` scheme — missing the `+asyncpg` prefix that
  `claude-commands/check-aspire.md` section 2c explicitly tells reviewers
  to flag for Python's async SQLAlchemy driver. The kit's own reference
  template was violating its own paired review command.
- `security/manual-checks.sh`: two unquoted variable expansions
  (`$RESP_EXIST`/`$RESP_NOEXIST`) flagged by ShellCheck (SC2086) — quoted.
- `security/zap-scan.sh`: `ls | grep` pattern flagged by ShellCheck (SC2010)
  — replaced with a glob.
- `.github/workflows/validate-kit.yml`: unused loop variable in the
  `wait-for-health` retry loop flagged by ShellCheck (SC2034) — renamed to
  `_`.
- `.gitignore`: added `.pytest_cache/`, `.ruff_cache/`, `.coverage`,
  `htmlcov/` to the Python section.

The coding-practice fixes above were verified via: ShellCheck (both shell
scripts, clean), actionlint (the repo's own active workflow, clean),
`node --check`/`ast.parse` (all k6 scripts and the Locust file, valid),
YAML/JSON parse of every config file, a full `docker compose up` boot of
`examples/minimal-service` + observability stack confirming
`/health`/`/ready`/`/metrics`, Prometheus target health, and Jaeger trace
ingestion all still work end-to-end, and a relative-link check across
every Markdown file (none broken).

## [1.0.0]

### Added

- Initial extraction of reusable DevSecOps platform assets from a
  three-tier reference app lab repo, organized by capability:
  - `claude-skills/` — 19 Claude Code skill prompts
  - `dotnet/` — Aspire `ServiceDefaults` + an `AppHost` template
  - `ci-cd/` — GitHub Actions CI/CD pipeline shape + pre-commit security baseline
  - `observability/` — Jaeger + Prometheus + Grafana Docker Compose overlay
  - `load-testing/` — k6 and Locust scenarios
  - `iac-terraform/gcp-cloud-run/` — parameterized Terraform module
  - `security/` — OWASP manual pen-test script and ZAP scan wrapper
  - `examples/minimal-service/` — a worked example proving the pieces work together
  - `.github/workflows/validate-kit.yml` — the kit's own validation CI
