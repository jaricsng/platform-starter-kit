# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

Versioning policy: **major** = breaking layout change, **minor** = new
capability folder added, **patch** = doc/template fixes with no structural
change.

## [Unreleased]

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
  filesystem path from the original extraction machine
  (`/Users/jaricsng/dev/.../task-manager/...`) — replaced with relative
  paths.
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
