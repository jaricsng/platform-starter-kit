# Security Policy

This file covers the **kit itself** — the templates, scripts, and CI shapes
in this repo. It does not cover security issues in projects built *from*
this kit; report those to the adopting project's own maintainers.

## Reporting a vulnerability

Please report security issues privately via
[GitHub Security Advisories](https://github.com/jaricsng/platform-starter-kit/security/advisories/new)
rather than opening a public issue. Include:

- The affected file(s) (e.g. a specific workflow, Terraform module, or script)
- Why it's a vulnerability, not just a hardening suggestion
- A minimal reproduction or proof of concept if applicable

You should receive a response within 5 business days.

## Scope

In scope:
- The Terraform module (`iac-terraform/gcp-cloud-run/`)
- The CI/CD pipeline shapes (`ci-cd/`)
- The security scripts (`security/`)
- The Claude Code commands (`claude-commands/`)
- This repo's own validation workflow (`.github/workflows/validate-kit.yml`)

Out of scope:
- Placeholder values and `TODO-*` strings — these are intentional and not
  secrets
- Findings that only apply after an adopter fills in their own
  configuration incorrectly
- The known, already-documented metric-name mismatch between
  `observability/recording_rules.yml` and the Grafana dashboard (see
  `docs/ASSET-CATALOG.md`) — this is a tracked issue, not a new report
